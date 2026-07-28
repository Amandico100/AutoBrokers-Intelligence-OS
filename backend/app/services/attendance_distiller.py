"""SPEC-040 Onda 3 — Destilador do Espelho de Atendimento.

Transforma os transcripts capturados (Parte 1: equipe da corretora <-> segurado)
em INTELIGÊNCIA GLOBAL da AutoBrokers, em lote, fora do caminho quente:

ESTÁGIO 1 (modelo braçal, env DISTILLER_LLM_MODEL, default claude-sonnet-5):
  cada sessão encerrada é MASCARADA (templatize — a LLM nunca vê PII) e vira um
  resumo estruturado: tipo/ramo/serviço, conduta da atendente (ordem de
  perguntas), fatos reutilizáveis SEM dado pessoal, nota 0-100 (baseline
  humano — INTERNO, só admin; nunca no dashboard da corretora).

ESTÁGIO 2 (modelo FORTE, env DISTILLER_STRONG_MODEL, default claude-opus-5):
  síntese dos playbooks de conduta por (ramo, serviço) — baixo volume, alto
  valor estrutural (decisão do founder 19/07: o estrutural merece o modelo
  mais forte; o braçal fica no Sonnet). Playbook nasce como DRAFT versionado —
  nada auto-aplica antes do gate (Onda 4) / aprovação.

CARDS: fatos reutilizáveis passam pelo filtro de PII em 2 camadas
  (determinístico via templatize + instrução da LLM); resíduo de PII =
  rejected_pii (auditável). Card limpo = pending_review; aprovação (admin)
  publica no RAG global (coleção autobrokers_global) como chunk atômico —
  card JÁ É o formato ideal de RAG, sem chunking pesado.

CUSTO: roda 1x/dia na madrugada (janela UTC 03-09h), teto de sessões por
  rodada (DISTILLER_MAX_SESSIONS_PER_RUN), zero LLM quando não há sessão nova.
  Custo rastreado no FinOps via LLMFactory (company_id da sessão).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_MARKER = "distiller:last_run"
_RUN_WINDOW_UTC = range(3, 10)          # madrugada BRT
_TRANSCRIPT_CAP = 7000                  # chars por sessão enviados à LLM
_MIN_SESSIONS_DEFAULT = 3               # mínimo p/ sintetizar playbook


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def _provider_model(strong: bool) -> Tuple[str, str]:
    provider = os.getenv("DISTILLER_PROVIDER") or "anthropic"
    if strong:
        return provider, os.getenv("DISTILLER_STRONG_MODEL") or "claude-opus-5"
    return provider, os.getenv("DISTILLER_LLM_MODEL") or "claude-sonnet-5"


async def _call_llm(system: str, user: str, company_id: str = "", strong: bool = False) -> Optional[str]:
    """Chamada única de LLM (padrão da casa: LLMFactory + FinOps por company)."""
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        from app.core.utils import get_api_key_for_provider
        from app.factories.llm_factory import LLMFactory

        provider, model = _provider_model(strong)
        llm = LLMFactory.create_llm(
            company_config={}, agent_data={"llm_provider": provider, "llm_model": model},
            api_key=get_api_key_for_provider(provider, model),
            company_id=str(company_id or os.getenv("GLOBAL_KNOWLEDGE_COMPANY_ID") or ""),
            agent_id=None,
        )
        result = await llm.ainvoke([SystemMessage(content=system), HumanMessage(content=user)])
        return str(getattr(result, "content", "") or "").strip() or None
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[DESTILADOR] LLM falhou ({'forte' if strong else 'padrão'}): {type(e).__name__}")
        return None


def _parse_json(text: Optional[str]) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    s = text.strip()
    if s.startswith("```"):
        s = s.strip("`")
        s = s[4:] if s.lower().startswith("json") else s
    try:
        start, end = s.find("{"), s.rfind("}")
        if start >= 0 and end > start:
            return json.loads(s[start:end + 1])
    except Exception:  # noqa: BLE001
        pass
    return None


# ------------------------------------------------------------------ #
# Estágio 1 — extração por sessão (braçal)
# ------------------------------------------------------------------ #
_STAGE1_SYSTEM = (
    "Você analisa uma conversa de ATENDIMENTO de corretora de seguros no WhatsApp "
    "(equipe da corretora falando com o segurado). A conversa já está MASCARADA "
    "({CPF}, {PLACA}, {TELEFONE}, {VALOR}...). Extraia APENAS JSON válido:\n"
    "{\"tipo\": \"assistencia|sinistro|apolice|renovacao|cobranca|outro\", "
    "\"ramo\": \"auto|residencial|vida|outro\", \"servico\": \"guincho|bateria|pneu|chaveiro|"
    "vidros|eletricista|encanador|consulta|sinistro|outro\", \"seguradora\": \"nome ou vazio\", "
    "\"resumo_conduta\": [\"passo 1 de como a atendente conduziu\", \"...\"], "
    "\"perguntas_na_ordem\": [\"pergunta 1\", \"...\"], "
    "\"fatos_reutilizaveis\": [\"fato GERAL de processo/seguradora, reutilizável em qualquer "
    "corretora, SEM NENHUM dado pessoal, nome, endereço ou número específico do cliente\"], "
    "\"score\": 0-100, \"flags\": [\"problema observado, se houver\"]}\n"
    "score = qualidade do atendimento HUMANO (empatia, ordem certa, sem repetição, resolveu). "
    "fatos_reutilizaveis: só o que ensina PROCESSO (ex.: 'Porto exige boletim de ocorrência "
    "para roubo'); NUNCA fatos sobre um cliente. Sem comentários fora do JSON."
)


def _load_undistilled_sync(max_sessions: int) -> List[Dict[str, Any]]:
    """As próximas sessões a destilar, buscando ALÉM das já destiladas.

    Isto era `limit(max_sessions * 4)` e teria travado a recuperação no meio do
    caminho — de um jeito silencioso, que é o pior.

    A conta: o PostgREST corta em 1.000 linhas. Depois de destilar as primeiras
    mil, a consulta continuaria devolvendo essas mesmas mil — todas já
    marcadas — e o filtro encontraria **zero** pendentes. O Destilador
    concluiria "não há trabalho" com 5.000 sessões na fila, e o painel diria
    que estava tudo em dia.

    Agora ele avança pelas páginas até juntar o lote pedido ou a fonte secar.
    """
    from app.core.database import get_supabase_client

    db = get_supabase_client()
    pendentes: List[Dict[str, Any]] = []
    inicio = 0
    while len(pendentes) < max_sessions:
        lote = (db.client.table("attendance_sessions")
                .select("id, company_id, observer_number, counterparty, "
                        "started_at, summary")
                .eq("status", "closed")
                # Mais antigas primeiro na recuperação: o histórico entrou de
                # uma vez, e processar do fim para o começo deixaria as
                # conversas mais velhas para sempre no fim da fila.
                .order("started_at", desc=False)
                .range(inicio, inicio + 999).execute().data) or []
        pendentes.extend(r for r in lote
                         if not ((r.get("summary") or {}).get("distilled")))
        if len(lote) < 1000:
            break
        inicio += 1000
        if inicio > 200_000:
            break
    return pendentes[:max_sessions]


def _load_session_text_sync(session_id: str) -> str:
    """Transcript cronológico MASCARADO (PII nunca chega à LLM).

    As cópias do history_sync entravam aqui inteiras. Medido em 28/07/2026:
    116.877 linhas para 58.786 mensagens reais (1,99x). Cada conversa chegava
    à LLM com **toda mensagem escrita duas vezes** — média de 15,1 linhas para
    7,4 mensagens.

    Não era só o dobro do custo. O transcript é cortado em 7.000 caracteres:
    **56 sessões estouravam o teto, e só 9 estourariam sem as cópias.** As 47
    do meio são as conversas mais longas — as que mais tinham a ensinar — e
    perdiam o fim, que é justamente onde o atendimento se resolve.

    Corrigir isto baixa o custo pela metade e AUMENTA a qualidade. Não é troca.
    """
    from app.core.database import get_supabase_client
    from app.services.atlas.templater import templatize
    from app.services.atlas.weaver import _sem_copias

    db = get_supabase_client()
    events = (db.client.table("attendance_transcripts")
              .select("session_id, direction, msg_type, text, wa_timestamp")
              .eq("session_id", session_id)
              .order("wa_timestamp", desc=False).limit(400).execute().data or [])
    events = _sem_copias(events)
    lines = []
    for e in events:
        who = "ATENDENTE" if e.get("direction") == "out" else "CLIENTE"
        txt = str(e.get("text") or "").strip()
        if not txt:
            txt = f"[{e.get('msg_type') or 'midia'}]"
        lines.append(f"{who}: {templatize(txt)}")
    return "\n".join(lines)[:_TRANSCRIPT_CAP]


def _save_session_summary_sync(session_id: str, summary: Dict[str, Any]) -> None:
    from app.core.database import get_supabase_client

    db = get_supabase_client()
    db.client.table("attendance_sessions").update({"summary": summary}).eq("id", session_id).execute()


# ------------------------------------------------------------------ #
# Knowledge cards — filtro de PII em 2 camadas + fila de aprovação
# ------------------------------------------------------------------ #
def _card_pii_clean(text: str) -> bool:
    """Camada determinística: se o templatize mudaria o texto, tem PII."""
    from app.services.atlas.templater import templatize

    return templatize(text) == text


def _store_card_sync(fato: str, meta: Dict[str, Any]) -> Optional[str]:
    from app.core.database import get_supabase_client

    db = get_supabase_client()
    text = " ".join(str(fato or "").split())
    if len(text) < 15 or len(text) > 400:
        return None
    clean = _card_pii_clean(text)
    row = {
        "card_hash": hashlib.md5(text.lower().encode("utf-8")).hexdigest(),
        "card_text": text,
        "category": meta.get("category") or "processo",
        "ramo": meta.get("ramo"),
        "insurer_key": (str(meta.get("seguradora") or "").strip().lower() or None),
        "status": "pending_review" if clean else "rejected_pii",
        "pii_check": {"deterministic": clean, "llm_instructed": True},
    }
    try:
        res = db.client.table("knowledge_cards").upsert(
            row, on_conflict="card_hash", ignore_duplicates=True).execute()
        return (res.data or [{}])[0].get("id")
    except Exception:  # noqa: BLE001
        return None


def publish_card_sync(card: Dict[str, Any]) -> bool:
    """Card aprovado -> RAG global como chunk atômico (o card JÁ É o chunk)."""
    from langchain_openai import OpenAIEmbeddings

    from app.core.config import settings
    from app.services.knowledge_scope import GLOBAL_COLLECTION, SCOPE_GLOBAL_AUTOBROKERS
    from app.services.qdrant_service import get_qdrant_service

    text = str(card.get("card_text") or "").strip()
    if not text or not _card_pii_clean(text):
        return False
    prefix_bits = [b for b in (card.get("insurer_key"), card.get("ramo")) if b]
    chunk = (f"({' / '.join(str(b) for b in prefix_bits)}) " if prefix_bits else "") + text
    dense = OpenAIEmbeddings(model="text-embedding-3-small",
                             api_key=settings.OPENAI_API_KEY).embed_documents([chunk])
    qdrant = get_qdrant_service()
    company = (os.getenv("GLOBAL_KNOWLEDGE_COMPANY_ID") or "").strip() or "autobrokers-global"
    return bool(qdrant.insert_embeddings(
        company_id=company, document_id=f"card-{card.get('id')}",
        embeddings=dense, chunks=[chunk],
        metadata={"document_name": "Knowledge Card (Espelho de Atendimento)",
                  "source": "attendance_distiller", "chunk_type": "knowledge_card"},
        sparse_embeddings=None, collection_name=GLOBAL_COLLECTION, agent_id=None,
        knowledge_extras={"scope": SCOPE_GLOBAL_AUTOBROKERS, "curation_status": "published",
                          "namespace": "cards"},
    ))


# ------------------------------------------------------------------ #
# Estágio 2 — síntese de playbook de conduta (modelo FORTE)
# ------------------------------------------------------------------ #
_STAGE2_SYSTEM = (
    "Você é o melhor treinador de atendimento de corretoras de seguros do Brasil. "
    "Receberá resumos de conduta de VÁRIOS atendimentos humanos reais (mascarados) do mesmo "
    "tipo de serviço. Sintetize o MELHOR playbook de conduta — o padrão-ouro que um atendente "
    "deve seguir nesse serviço. Responda APENAS JSON válido:\n"
    "{\"objetivo\": \"...\", \"acolhimento\": \"como abrir com empatia\", "
    "\"ficha_coleta\": [{\"campo\": \"...\", \"como_pedir\": \"frase natural\", "
    "\"quando\": \"antes/depois de quê\", \"ja_temos_na_apolice\": true|false}], "
    "\"pre_checks\": [\"verificação útil antes de acionar\"], "
    "\"sensibilidade\": \"cuidados de tom para este serviço\", "
    "\"encerramento\": \"como fechar bem\", \"frases_exemplo\": [\"frase natural sem dado pessoal\"]}\n"
    "Regras: campo com ja_temos_na_apolice=true NUNCA deve ser perguntado — só confirmado; "
    "uma pergunta por vez; nada de dado pessoal nas frases; português natural de WhatsApp."
)


def _load_group_summaries_sync(ramo: str, servico: str, limit: int = 30) -> List[Dict[str, Any]]:
    from app.core.database import get_supabase_client

    db = get_supabase_client()
    rows = (db.client.table("attendance_sessions")
            .select("summary").eq("status", "closed")
            .order("started_at", desc=True).limit(300).execute().data or [])
    out = []
    for r in rows:
        d = ((r.get("summary") or {}).get("distilled")) or {}
        if d and str(d.get("ramo")) == ramo and str(d.get("servico")) == servico:
            out.append(d)
        if len(out) >= limit:
            break
    return out


def _save_playbook_draft_sync(ramo: str, servico: str, content: Dict[str, Any],
                              sessions: int, model: str) -> Optional[str]:
    from app.core.database import get_supabase_client

    db = get_supabase_client()
    try:
        existing = (db.client.table("conduct_playbooks").select("version")
                    .eq("ramo", ramo).eq("servico", servico)
                    .order("version", desc=True).limit(1).execute().data or [])
        version = (existing[0]["version"] + 1) if existing else 1
        res = db.client.table("conduct_playbooks").insert({
            "ramo": ramo, "servico": servico, "version": version, "status": "draft",
            "content": content, "model_used": model,
            "source_stats": {"sessions": sessions,
                             "generated_at": datetime.now(timezone.utc).isoformat()},
        }).execute()
        return (res.data or [{}])[0].get("id")
    except Exception as e:  # noqa: BLE001
        logger.error(f"[DESTILADOR] salvar playbook falhou: {type(e).__name__}")
        return None


# ------------------------------------------------------------------ #
# Orquestração
# ------------------------------------------------------------------ #
async def distill_once(force: bool = False, *, atrasado: bool = False) -> Dict[str, int]:
    """Uma rodada completa: estágio 1 -> cards -> estágio 2. Retorna contadores.

    `atrasado=True` usa o lote de recuperação — maior, para dar conta do
    histórico que entra de uma vez no pareamento.
    """
    stats = {"sessions": 0, "cards_new": 0, "cards_rejected_pii": 0, "playbooks": 0}
    max_sessions = _env_int(
        "DISTILLER_BACKLOG_SESSIONS_PER_RUN" if atrasado
        else "DISTILLER_MAX_SESSIONS_PER_RUN",
        400 if atrasado else 40)
    min_group = _env_int("DISTILLER_MIN_SESSIONS", _MIN_SESSIONS_DEFAULT)

    sessions = await asyncio.to_thread(_load_undistilled_sync, max_sessions)
    if not sessions:
        return stats

    touched_groups: Dict[Tuple[str, str], int] = {}

    # As sessoes sao destiladas EM PARALELO, com teto.
    #
    # Medido em 28/07/2026 numa rodada real: 30 sessoes em 9min55s — ~20s cada,
    # quase tudo esperando o modelo responder. Em fila, as 6.125 sessoes que o
    # pareamento trouxe levariam 34 HORAS.
    #
    # E cada sessao e independente da outra: nada no estagio 1 depende do
    # resultado da anterior. Esperar uma para comecar a proxima nao comprava
    # qualidade nenhuma — comprava so tempo.
    #
    # O teto existe por tres motivos concretos, e nao por prudencia vaga:
    #   1. limite de requisicoes por minuto do provedor;
    #   2. o Supabase tambem e chamado por sessao (ler transcript, gravar
    #      resumo, gravar cards);
    #   3. custo concentrado: paralelizar nao gasta mais, gasta ANTES — e um
    #      erro sistematico queimaria o saldo mais rapido do que alguem nota.
    teto = _env_int("DISTILLER_CONCURRENCY", 6)
    vagas = asyncio.Semaphore(teto)
    trava_stats = asyncio.Lock()

    async def _uma_sessao(sess: Dict[str, Any]) -> None:
        async with vagas:
            await _destilar_sessao(sess, stats, touched_groups, trava_stats)

    await asyncio.gather(*[_uma_sessao(s) for s in sessions],
                         return_exceptions=True)

    # Estagio 2 — playbooks dos grupos tocados nesta rodada (modelo FORTE)
    for (ramo, servico), _n in touched_groups.items():
        try:
            if servico in ("outro", "") or ramo in ("",):
                continue
            summaries = await asyncio.to_thread(_load_group_summaries_sync, ramo, servico)
            if len(summaries) < min_group:
                continue
            user = json.dumps({"servico": servico, "ramo": ramo,
                               "atendimentos": summaries[:20]}, ensure_ascii=False)[:12000]
            raw = await _call_llm(_STAGE2_SYSTEM, user, strong=True)
            content = _parse_json(raw)
            if content and content.get("ficha_coleta"):
                _prov, model = _provider_model(strong=True)
                pid = await asyncio.to_thread(
                    _save_playbook_draft_sync, ramo, servico, content, len(summaries), model)
                if pid:
                    stats["playbooks"] += 1
        except Exception as e:  # noqa: BLE001
            logger.error(f"[DESTILADOR] playbook {ramo}/{servico} falhou: {type(e).__name__}")

    # Pulso na Central de Agentes: é o que mostra o Destilador VIVO. Sem ele, a
    # tela diz "sem sinal" e ninguém distingue "parado" de "sem trabalho".
    try:
        from app.core.heartbeat import beat

        await beat("espelho_atendimento", stats["sessions"])
    except Exception:  # noqa: BLE001
        pass

    logger.info("[DESTILADOR] rodada: %s", stats)
    return stats


async def _destilar_sessao(sess: Dict[str, Any], stats: Dict[str, int],
                           touched_groups: Dict[Tuple[str, str], int],
                           trava: "asyncio.Lock") -> None:
    """Uma sessao, do transcript ao resumo e aos cards.

    Extraida do laco para poder rodar em paralelo. A logica e a mesma de antes,
    linha por linha; o que mudou foi so QUEM chama e quantas ao mesmo tempo.

    Os contadores sao incrementados sob trava: `+=` em dicionario compartilhado
    por corrotinas concorrentes perde incremento, e um relatorio que diz "28"
    quando foram 30 e pior que um que nao diz nada.
    """
    try:
        text = await asyncio.to_thread(_load_session_text_sync, sess["id"])
        if len(text) < 80:  # sessão sem conteúdo útil (só mídia/1 msg)
            summary = dict(sess.get("summary") or {})
            summary["distilled"] = {"skipped": "curta"}
            await asyncio.to_thread(_save_session_summary_sync, sess["id"], summary)
            return
        raw = await _call_llm(_STAGE1_SYSTEM, text,
                              company_id=str(sess.get("company_id") or ""))
        data = _parse_json(raw)
        if not data:
            return
        summary = dict(sess.get("summary") or {})
        summary["distilled"] = {
            "tipo": data.get("tipo"), "ramo": data.get("ramo"),
            "servico": data.get("servico"), "seguradora": data.get("seguradora"),
            "resumo_conduta": data.get("resumo_conduta") or [],
            "perguntas_na_ordem": data.get("perguntas_na_ordem") or [],
            "score": data.get("score"), "flags": data.get("flags") or [],
            "at": datetime.now(timezone.utc).isoformat(),
        }
        await asyncio.to_thread(_save_session_summary_sync, sess["id"], summary)

        novos = rejeitados = 0
        for fato in (data.get("fatos_reutilizaveis") or [])[:8]:
            card_meta = {"ramo": data.get("ramo"), "seguradora": data.get("seguradora")}
            cid = await asyncio.to_thread(_store_card_sync, str(fato), card_meta)
            if cid:
                if _card_pii_clean(" ".join(str(fato).split())):
                    novos += 1
                else:
                    rejeitados += 1

        ramo = str(data.get("ramo") or "outro")
        servico = str(data.get("servico") or "outro")

        async with trava:
            stats["sessions"] += 1
            stats["cards_new"] += novos
            stats["cards_rejected_pii"] += rejeitados
            touched_groups[(ramo, servico)] = touched_groups.get((ramo, servico), 0) + 1
    except Exception as e:  # noqa: BLE001
        # Uma sessão que falha não derruba as outras cinco em voo, e a próxima
        # rodada a pega de novo: ela continua sem a marca `distilled`.
        logger.error("[DESTILADOR] sessão %s falhou: %s",
                     sess.get("id"), type(e).__name__)


def _fila_pendente() -> int:
    """Quantas sessões esperam destilação. Zero LLM — só contagem."""
    from app.core.database import get_supabase_client

    try:
        db = get_supabase_client()
        # PAGINADO. `limit(20_000)` era ilusão: o PostgREST corta em 1.000 sem
        # avisar, e a fila apareceria como 1.000 para sempre — o modo de
        # recuperação nunca desligaria, ou pior, nunca ligaria se o corte
        # ficasse abaixo do limiar.
        pendentes = 0
        inicio = 0
        while True:
            lote = (db.client.table("attendance_sessions").select("summary")
                    .eq("status", "closed")
                    .order("started_at", desc=True)
                    .range(inicio, inicio + 999).execute().data) or []
            pendentes += sum(1 for r in lote
                             if not ((r.get("summary") or {}).get("distilled")))
            if len(lote) < 1000:
                return pendentes
            inicio += 1000
            if inicio > 200_000:
                return pendentes
    except Exception:  # noqa: BLE001
        return 0


async def check_attendance_distiller() -> int:
    """Task periódica (horária): 1x/dia na madrugada — ou de hora em hora
    enquanto houver ATRASO grande.

    Por que existe o modo de atraso
    -------------------------------
    O ritmo de uma vez por noite, 40 sessões, foi desenhado para o regime
    normal: a corretora conversa, algumas dezenas de atendimentos por dia, e a
    madrugada dá conta.

    O pareamento quebra essa premissa. Quando a Resulta conectou o WhatsApp em
    28/07/2026, o `HISTORY_SYNC` despejou **6.105 sessões de uma vez**. A 40 por
    noite, o Espelho levaria **cinco meses** para processar o que chegou numa
    tarde — e o agente de atendimento seria ligado no dia 8 sem quase nada do
    que a equipe humana ensinou.

    A regra: enquanto a fila for grande, roda de hora em hora com lote maior.
    Voltando ao normal, volta para uma vez por noite. O custo continua limitado
    pelo lote — o que muda é a frequência, não o gasto por rodada.
    """
    atrasado = False
    try:
        now = datetime.now(timezone.utc)
        pendentes = await asyncio.to_thread(_fila_pendente)
        atrasado = pendentes >= _env_int("DISTILLER_BACKLOG_THRESHOLD", 200)

        if not atrasado:
            if now.hour not in _RUN_WINDOW_UTC:
                return 0
            from app.core.redis import get_async_redis_client

            r = await get_async_redis_client()
            today = now.date().isoformat()
            marker = await r.get(_MARKER)
            marker = marker.decode() if isinstance(marker, (bytes, bytearray)) else marker
            if marker == today:
                return 0
            await r.set(_MARKER, today, ex=3 * 86400)
        else:
            # Modo atraso: uma rodada por hora, com trava para duas instâncias
            # da API não processarem a mesma fila e pagarem duas vezes.
            from app.core.redis import get_async_redis_client

            r = await get_async_redis_client()
            janela = now.strftime("%Y-%m-%dT%H") + ("a" if now.minute < 30 else "b")
            if not await r.set(f"{_MARKER}:atraso:{janela}", "1", ex=2700, nx=True):
                return 0
            logger.info("[DESTILADOR] %d sessões na fila — modo de recuperação",
                        pendentes)
    except Exception:  # noqa: BLE001
        pass
    try:
        stats = await distill_once(atrasado=atrasado)
        return stats.get("sessions", 0)
    except Exception as e:  # noqa: BLE001
        logger.error(f"[DESTILADOR] check falhou: {type(e).__name__}")
        return 0
