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
# Quantos atendimentos HUMANOS (score > 0 e com conduta — ver
# `_load_group_summaries_sync`) um grupo precisa para virar playbook.
#
# Era 3, e 3 nao e evidencia: e anedota com plural. 📊 07/08/2026, atendimentos
# uteis por grupo, e o degrau que o proprio acervo desenha:
#
#     auto/chaveiro          2   <- playbook com placeholder no meio
#     auto/bateria           5   <- 8 dos 13 sem atendimento humano
#     outro/vidros           8   <- "a seguradora cobre a diferenca"
#     vida/consulta          8
#   ----------------------------- piso 12
#     residencial/chaveiro  12       auto/vidros           201
#     residencial/vidros    17       auto/consulta         220
#     auto/pneu             19       residencial/sinistro  720
#     residencial/eletric.  26       auto/sinistro         899
#
# 12 e onde o acervo tem um degrau (8 -> 12 -> 17), nao onde eu queria que
# estivesse. Barra EXATAMENTE os tres rascunhos que a auditoria reprovou por
# defeito nomeado, e nao barra nenhum bom: 13 dos 18 grupos seguem produzindo.
#
# NADA E APAGADO: playbook que existe continua onde esta. O piso so decide quem
# GERA versao nova. O custo honesto e `vida/consulta`, hoje ativo com 8 uteis —
# ele congela na v1 ate chegar material. Registrado, nao acidental.
_MIN_SESSIONS_DEFAULT = 12              # minimo de atendimentos HUMANOS


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def _teto_de_gasto() -> int:
    """Quantas conversas UMA rodada pode ler. Zero é resposta válida.

    Não usa `_env_int` de propósito: aquele faz `max(1, ...)`, porque
    concorrência ou tamanho de lote em zero travaria o sistema. Aqui zero é
    exatamente o que se quer dizer — **não gaste nada** — e passar por
    `_env_int` transformaria o teto travado em "uma conversa e um playbook por
    rodada". O playbook é a chamada mais cara do sistema; a trava vazaria
    justamente pelo cano mais largo, e em silêncio.
    """
    try:
        return max(0, int(str(os.getenv("DESTILADOR_TETO_POR_RODADA", "0")).strip() or 0))
    except ValueError:
        return 0


def _provider_model(strong: bool) -> Tuple[str, str]:
    provider = os.getenv("DISTILLER_PROVIDER") or "anthropic"
    if strong:
        return provider, os.getenv("DISTILLER_STRONG_MODEL") or "claude-opus-5"
    return provider, os.getenv("DISTILLER_LLM_MODEL") or "claude-sonnet-5"


def _texto_da_resposta(result: Any) -> Optional[str]:
    """O TEXTO da resposta — não a representação da lista de blocos.

    Isto era `str(getattr(result, "content", ""))`. Quando o modelo PENSA, o
    LangChain devolve `content` como uma LISTA de blocos:

        [{"type": "thinking", ...}, {"type": "text", "text": "{...json...}"}]

    `str()` numa lista devolve a repr da lista. O leitor de JSON procura a
    primeira `{` e a última `}` e encaixa tudo que está no meio — inclusive o
    bloco de pensamento — então `json.loads` falha e a rodada não salva nada.
    O modelo respondeu, o token foi pago, e o resultado foi jogado fora.

    Medido em 29/07/2026: 11 chamadas ao Opus 5 na síntese de playbook,
    3.395 tokens de saída cada, US$ 0,45 gastos, ZERO playbooks salvos.

    A causa é uma mudança de padrão do modelo: o Claude Opus 5 pensa por
    padrão (o Opus 4.8 não pensava se ninguém pedisse). O código funcionava
    com o modelo antigo e passou a jogar dinheiro fora com o novo, sem
    nenhum erro aparecer em lugar nenhum.
    """
    bruto = getattr(result, "content", None)
    if isinstance(bruto, str):
        return bruto.strip() or None
    if isinstance(bruto, list):
        partes = []
        for bloco in bruto:
            if isinstance(bloco, dict):
                if bloco.get("type") == "text" and bloco.get("text"):
                    partes.append(str(bloco["text"]))
            elif isinstance(bloco, str):
                partes.append(bloco)
        return ("\n".join(partes)).strip() or None
    return str(bruto or "").strip() or None


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
        return _texto_da_resposta(result)
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
# Quantas vezes vale a pena insistir numa sessão cuja resposta não foi lida.
# Três: uma falha pode ser instabilidade do modelo, três é defeito — e a partir
# daí cada tentativa é dinheiro comprando o mesmo erro.
LIMITE_DE_FALHAS = 3

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


def _fechar_sessoes_vencidas_sync() -> int:
    """Fecha a sessão que acabou e ninguém fechou. Custo zero, sem modelo.

    A sessão só fechava quando chegava mensagem NOVA da mesma pessoa depois do
    intervalo de duas horas (`observer_intake._SESSION_GAP`). Se o segurado
    nunca escreve de novo — que é o caso normal quando o atendimento resolveu —
    a sessão fica `open` **para sempre**, e `_load_undistilled_sync` só olha
    `status='closed'`.

    Medido em 29/07/2026: 43 sessões da Resulta abertas, uma desde 21/07 —
    oito dias — com 423 mensagens paradas. Conversa completa, conhecimento
    dentro, invisível para o Destilador. Nenhuma delas era de seguradora, o que
    salvou o material que não pode ser perdido; mas nada garantia isso.

    A margem é generosa de propósito: **seis horas** sem nenhuma mensagem, três
    vezes o intervalo de sessão. Fechar cedo partiria uma conversa em duas e
    ensinaria conduta pela metade — pior que esperar. Fechar tarde só atrasa.

    Roda em toda rodada, INCLUSIVE com o teto de gasto em zero: não chama
    modelo, e é justamente o que destrava material para quando houver crédito.
    """
    from datetime import timedelta

    from app.core.database import get_supabase_client

    limite = (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()
    db = get_supabase_client()
    try:
        alvo = (db.client.table("attendance_sessions")
                .select("id")
                .eq("status", "open")
                .lt("last_event_at", limite)
                .limit(1000).execute().data) or []
        for i in range(0, len(alvo), 100):
            ids = [r["id"] for r in alvo[i:i + 100]]
            db.client.table("attendance_sessions").update(
                {"status": "closed"}).in_("id", ids).execute()
        if alvo:
            logger.info("[DESTILADOR] %d sessões vencidas fechadas — entram na fila",
                        len(alvo))
        return len(alvo)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[DESTILADOR] varredura de sessões abertas falhou: %s",
                       type(exc).__name__)
        return 0


def _corretoras_excluidas() -> frozenset:
    """Corretoras cujas conversas NÃO viram conhecimento. Ninguém, por padrão.

    🔴 POR QUE ISTO EXISTE — 07/08/2026, decisão do Founder.

    A Amandus Seguros é a corretora de TESTE. As conversas dela são ensaios,
    respostas erradas de propósito e perguntas que ninguém faria — 📊 34.099
    mensagens e 1.921 sessões que foram apagadas neste dia justamente por isso.

    Apagar resolveu o passado. Sem esta lista, o futuro voltaria a poluir: a
    linha continua pareada e capturando, e na próxima rodada o destilador
    encontraria as conversas de teste na fila como se fossem trabalho real.

    **Isto não desliga a captura.** A corretora de teste continua servindo para
    testar, e o chat dela continua funcionando. O que ela deixa de fazer é
    ensinar o RAG que todas as outras leem — porque conhecimento errado é pior
    que conhecimento nenhum: ele não fica parado, ele responde.

    Lista por variável de ambiente, `company_id` separados por vírgula, para
    incluir ou tirar uma corretora sem deploy.
    """
    bruto = os.getenv("DESTILACAO_CORRETORAS_EXCLUIDAS", "") or ""
    return frozenset(p.strip() for p in bruto.split(",") if p.strip())


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
        excluidas = _corretoras_excluidas()
        for r in lote:
            resumo = r.get("summary") or {}
            if resumo.get("distilled"):
                continue
            # Sessão que já recusou três vezes sai da fila. Sem isto, ela volta
            # em TODA rodada e cobra de novo pelo mesmo erro — foi assim que
            # 2.334 chamadas repetidas custaram US$ 15 em 28/07/2026.
            if int(resumo.get("distill_falhas") or 0) >= LIMITE_DE_FALHAS:
                continue
            if str(r.get("company_id") or "") in excluidas:
                continue
            pendentes.append(r)
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
    from app.services.atlas.mensagem import sem_copias

    db = get_supabase_client()
    events = (db.client.table("attendance_transcripts")
              .select("session_id, direction, msg_type, text, wa_timestamp")
              .eq("session_id", session_id)
              .order("wa_timestamp", desc=False).limit(400).execute().data or [])
    events = sem_copias(events)
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


# `_chave_da_seguradora` vivia aqui e normalizava o nome da seguradora da
# sessão para gravar direto em `insurer_key`. Ela saiu em 05/08/2026: quem
# decide de quem é a regra passou a ser `curadoria_cartas.seguradora_do_fato`,
# que normaliza pela MESMA `normalize_insurer_key` e ainda exige que o texto do
# fato nomeie a companhia. Deixar as duas de pé seria manter dois caminhos para
# a mesma pergunta, e o que ninguém chama é o que envelhece errado (§5).


def _store_card_sync(fato: str, meta: Dict[str, Any]) -> Optional[str]:
    from app.core.database import get_supabase_client
    from app.services.curadoria_cartas import assunto_da_carta, seguradora_do_fato

    db = get_supabase_client()
    text = " ".join(str(fato or "").split())
    if len(text) < 15 or len(text) > 400:
        return None
    clean = _card_pii_clean(text)
    # A SEGURADORA É DO FATO, NÃO DA CONVERSA.
    #
    # Aqui chegava `meta["seguradora"]` — a companhia da SESSÃO INTEIRA — e ela
    # era carimbada nos até oito fatos que a sessão produzia, inclusive nos
    # genéricos. 📊 Medido em 05/08/2026 sobre as 3.354 published etiquetadas:
    # só 32,3% citavam a própria seguradora no texto. Numa amostra de seis
    # cartas `allianz` que não citam a Allianz, seis eram fato de mercado — uma
    # delas de seguro PET, gravada como `allianz` / `auto`.
    #
    # O campo guardava "apareceu numa conversa sobre a Allianz" com o nome de
    # "é regra da Allianz". A decisão inteira mora em `curadoria_cartas` e é a
    # mesma para o destilador, para o script de consenso e para a limpeza do
    # acervo — um caminho só.
    chave, prestadora = seguradora_do_fato(
        text, meta.get("seguradora_candidata") or meta.get("seguradora"))
    marcas: Dict[str, Any] = {"deterministic": clean, "llm_instructed": True}
    if prestadora:
        # Prestadora atende VÁRIAS seguradoras. Em `insurer_key` ela faria o
        # filtro devolver a companhia errada; jogada fora, some um fato real.
        marcas["prestadora"] = prestadora
    row = {
        "card_hash": hashlib.md5(text.lower().encode("utf-8")).hexdigest(),
        "card_text": text,
        # O ASSUNTO É CALCULADO, não herdado. `meta.get("category") or
        # "processo"` gravava a mesma palavra em 100% das 11.640 cartas — uma
        # coluna que existia, custava linha e não respondia nada.
        "category": assunto_da_carta(text),
        "ramo": meta.get("ramo"),
        "insurer_key": chave,
        "status": "pending_review" if clean else "rejected_pii",
        "pii_check": marcas,
    }
    try:
        res = db.client.table("knowledge_cards").upsert(
            row, on_conflict="card_hash", ignore_duplicates=True).execute()
        return (res.data or [{}])[0].get("id")
    except Exception:  # noqa: BLE001
        return None


def despublicar_carta_sync(card_id: str, motivo: str = "superseded") -> bool:
    """Tira a carta do RAG de verdade — do índice, não só do banco.

    Rejeitar uma carta mudava só o `status` na tabela. O vetor continuava no
    Qdrant, e a busca continuava entregando a carta ao agente para sempre.
    Quem rejeitava acreditava ter removido conhecimento errado e não removia
    nada: o pior formato possível, porque a tela dizia que estava resolvido.

    Achado em 30/07/2026 por um subagente destilando o lote 011: a Porto DEIXOU
    de emitir boleto atualizado, e havia SEIS cartas publicadas afirmando que
    emite. Sem este caminho, as seis ficariam no índice contradizendo a nova —
    e o agente responderia uma ou outra por sorte da busca.

    Conhecimento de seguro tem prazo de validade. Uma base que só sabe crescer
    fica errada com o tempo, e o erro fica invisível porque a carta velha
    parece tão boa quanto a nova.

    O ponto é gravado como `card-<id>` em `publish_card_sync`; é por esse nome
    que ele sai.
    """
    from app.core.config import settings
    from app.services.knowledge_scope import GLOBAL_COLLECTION
    from app.services.qdrant_service import get_qdrant_service

    from app.core.database import get_supabase_client

    company = str(getattr(settings, "GLOBAL_KNOWLEDGE_COMPANY_ID", "")
                  or os.getenv("GLOBAL_KNOWLEDGE_COMPANY_ID") or "")
    try:
        get_qdrant_service().delete_document(
            company_id=company, document_id=f"card-{card_id}",
            collection_name=GLOBAL_COLLECTION)
    except Exception as exc:  # noqa: BLE001
        # Falhar aqui e marcar no banco seria voltar ao defeito: o banco diria
        # removido e o índice continuaria entregando. Melhor não marcar.
        logger.error("[CARTAS] não consegui tirar %s do índice: %s — status "
                     "NÃO alterado, a carta continua marcada como publicada",
                     card_id, type(exc).__name__)
        return False

    get_supabase_client().client.table("knowledge_cards").update(
        {"status": motivo}).eq("id", card_id).execute()
    logger.info("[CARTAS] %s saiu do RAG (%s)", card_id, motivo)
    return True


def publish_card_sync(card: Dict[str, Any]) -> bool:
    """Card aprovado -> RAG global como chunk atômico (o card JÁ É o chunk)."""
    from langchain_openai import OpenAIEmbeddings

    from app.core.config import settings
    from app.services.knowledge_scope import GLOBAL_COLLECTION, SCOPE_GLOBAL_AUTOBROKERS
    from app.services.qdrant_service import get_qdrant_service

    text = str(card.get("card_text") or "").strip()
    if not text or not _card_pii_clean(text):
        return False
    # O ASSUNTO ENTRA NO TEXTO, de propósito.
    #
    # A busca é híbrida e o BM25 casa por palavra exata. Sem "cobrança" escrito
    # no chunk, uma pergunta sobre boleto disputa espaço em igualdade com uma
    # carta de vistoria que por acaso menciona pagamento — e boleto é pedido de
    # muitas formas ("não recebi", "segunda via", "venceu", "manda o código").
    from app.services.curadoria_cartas import assunto_da_carta

    prefix_bits = [b for b in (card.get("insurer_key"), card.get("ramo"),
                               assunto_da_carta(text)) if b]
    chunk = (f"({' / '.join(str(b) for b in prefix_bits)}) " if prefix_bits else "") + text
    dense = OpenAIEmbeddings(model="text-embedding-3-small",
                             api_key=settings.OPENAI_API_KEY).embed_documents([chunk])

    # A BUSCA E HIBRIDA — E A CARTA ENTRAVA SO COM METADE.
    #
    # `search_service` consulta denso E esparso (BM25) e combina. Todo caminho
    # de ingestao manda os dois: o seed do canon, a ingestao de documentos, o
    # corpus de seguros. So a carta ia com `sparse_embeddings=None`.
    #
    # O denso acha por SIGNIFICADO e o BM25 acha por TERMO EXATO. Sem o
    # esparso, procurar "CVV", "carta verde", "endosso" ou "DDA" — palavras
    # que o corretor digita exatamente assim — nao encontrava carta nenhuma.
    # Metade do RAG estava desligada justamente para o conhecimento novo.
    sparse = None
    try:
        from fastembed import SparseTextEmbedding

        sparse = list(SparseTextEmbedding(model_name="Qdrant/bm25").embed([chunk]))
    except Exception as exc:  # noqa: BLE001 — sem esparso ainda publica, so acha menos
        logger.warning("[DESTILADOR] vetor esparso indisponivel: %s", type(exc).__name__)

    qdrant = get_qdrant_service()
    company = (os.getenv("GLOBAL_KNOWLEDGE_COMPANY_ID") or "").strip() or "autobrokers-global"
    return bool(qdrant.insert_embeddings(
        company_id=company, document_id=f"card-{card.get('id')}",
        embeddings=dense, chunks=[chunk],
        metadata={"document_name": "Knowledge Card (Espelho de Atendimento)",
                  "source": "attendance_distiller", "chunk_type": "knowledge_card"},
        sparse_embeddings=sparse, collection_name=GLOBAL_COLLECTION, agent_id=None,
        # 🔴 A CLASSIFICAÇÃO PRECISA CHEGAR AO ÍNDICE, NÃO SÓ AO BANCO.
        #
        # O sistema etiqueta as cartas muito bem — 📊 07/08/2026: `ramo` e
        # `category` com ZERO nulos em 12.071 cartas publicadas, 20 seguradoras
        # identificadas. E jogava tudo fora aqui: só `scope`, `curation_status`
        # e `namespace` iam para o Qdrant.
        #
        # Sem `insurer_key` no payload não existe como filtrar na busca. A
        # única defesa era o BM25 casar a palavra "porto" no prefixo do texto —
        # probabilístico, não filtro. 📊 As 608 cartas da Allianz disputavam em
        # igualdade qualquer pergunta sobre a Porto, e nada registrava a troca.
        #
        # O Founder disse a frase que descreve o defeito antes de ele ser
        # achado: *"regras da Porto podem não servir para Bradesco ou HDI"*.
        # A etiqueta existia; faltava ela viajar junto.
        knowledge_extras={"scope": SCOPE_GLOBAL_AUTOBROKERS, "curation_status": "published",
                          "namespace": "cards",
                          # `insurer_key` ausente = fato GENÉRICO de mercado, e
                          # isso é 📊 80,6% do acervo. Ele não vira string vazia
                          # de propósito: a busca precisa distinguir "sem
                          # seguradora" de "seguradora desconhecida".
                          **({"insurer_key": card["insurer_key"]}
                             if card.get("insurer_key") else {}),
                          **({"ramo": card["ramo"]} if card.get("ramo") else {}),
                          **({"card_category": card["category"]}
                             if card.get("category") else {})},
    ))


# ------------------------------------------------------------------ #
# Estágio 2 — síntese de playbook de conduta (modelo FORTE)
# ------------------------------------------------------------------ #
# 🔴 ESTE PROMPT PEDIA O IDEAL. AGORA ELE PEDE O OBSERVADO.
#
# A versao anterior abria com "Voce e o melhor treinador de atendimento de
# corretoras de seguros do Brasil... Sintetize o MELHOR playbook — o
# padrao-ouro". Um pedido assim nao e neutro: CONVIDA o modelo a completar com
# conhecimento de mundo tudo o que as conversas nao ensinaram.
#
# 📊 Medido em 07/08/2026 sobre os 18 playbooks do banco:
#
#   15 frases de `como_pedir` trazem espaco em branco literal (`[modelo]`,
#      `[xxxx]`, `R$ [valor]`, `valor X`) — e `como_pedir` NAO fica no banco:
#      `graph._conduta_do_caso` (linha 806) injeta a ficha inteira no prompt do
#      agente de atendimento. A pior esta em `auto/vidros`, status ATIVO:
#        "So informar, nunca perguntar: 'Confirmei aqui: voce tem cobertura de
#         vidros, com participacao de R$ [valor] para esse item.'"
#      Cobertura afirmada + valor + colchete vazio + a instrucao de NAO
#      conferir. E o `sensibilidade` do MESMO playbook manda nunca prometer
#      valor. O sistema nao guarda as condicoes gerais de apolice nenhuma.
#
#   30 campos marcados `ja_temos_na_apolice=true` sao PERGUNTADOS em vez de
#      confirmados, em 17 dos 18 playbooks — 20 deles ATIVOS. A regra existia,
#      solta na ultima linha, longe do campo que ela governa.
#
#   `auto/bateria` foi escrito com 13 sessoes das quais OITO tem score 0. Score
#      0 nao e nota baixa: e "nao houve atendimento humano" (robo da
#      seguradora, central de prestadora, fragmento). O modelo aprendeu conduta
#      de um bot, e nao tinha como saber — o prompt nunca mencionou `score`.
#
# A regua que fecha isso JA EXISTE na casa e nao tinha chegado aqui:
# `scripts/destilacao_max/PROMPT-DESTILADOR.md` (teste do leitor cego,
# "seguradora so quando esta escrita", "regra que e por apolice: ensine onde
# ler", "score 0 != score baixo", guarda antifraude) e
# `PROMPT-DESTILADOR-SEGURADORA.md` (lastro obrigatorio, teste da cauda).
# 📊 Nenhuma das 11 regras tinha chegado ao Estagio 2. Este prompt e aquela
# regua chegando aqui — nao uma regua nova.
#
# As sete chaves lidas pelo codigo nao mudaram (`playbook_gate`,
# `prompt_optimizer`, `graph._conduta_do_caso`). As tres novas sao ignoradas
# por quem nao as conhece.
_STAGE2_SYSTEM = (
    "Voce le atendimentos humanos REAIS (ja mascarados) de um mesmo (ramo, "
    "servico) numa corretora de seguros brasileira, e escreve o playbook de "
    "conduta que ESSES atendimentos ensinam.\n"
    "Voce e um observador, nao um treinador. O que voce sabe sobre seguros "
    "fora destas conversas serve para ENTENDER o que leu — nunca para "
    "preencher o que faltou. Onde o material nao ensina, o playbook DIZ que "
    "nao ensina; ele nao completa.\n"
    "\n"
    "## A regua do score — leia antes de qualquer outra coisa\n"
    "Cada atendimento traz resumo_conduta, perguntas_na_ordem, score (0-100), "
    "flags, seguradora e tipo.\n"
    "- 0 = NAO HOUVE atendimento humano: robo da seguradora, central de "
    "prestadora, fragmento sem resposta. Nao conte, nao avalie, nao aprenda "
    "conduta dele. Para este playbook ele nao existe.\n"
    "- 1-39 = atendimento ruim. NUNCA vira regra: vai para o_que_evitar.\n"
    "- 40-69 = mediano. Confirma o que os bons mostram; sozinho nao sustenta "
    "regra.\n"
    "- 70-100 = bom. E daqui que a conduta sai.\n"
    "\n"
    "## As dez regras\n"
    "\n"
    "1. O TESTE DO LASTRO. Antes de escrever qualquer linha, aponte quantos "
    "atendimentos a sustentam. O que aparece em 1 de 12 e 'pode acontecer'; "
    "nunca 'sempre', 'o certo e', 'o padrao e'. O que nao aparece em nenhum "
    "nao entra.\n"
    "\n"
    "2. O TESTE DA CAUDA. Leia a ULTIMA oracao de cada frase que escreveu e "
    "pergunte: qual atendimento diz isto? Se a resposta for 'nenhum, mas faz "
    "sentido', apague a oracao. O defeito que mais machuca nao e a frase "
    "errada de ponta a ponta — e o corpo fiel com a cauda inventada.\n"
    "\n"
    "3. VOCE NAO TEM AS CONDICOES GERAIS. DE APOLICE NENHUMA. E PROIBIDO "
    "afirmar, em qualquer campo, o que a seguradora cobre, quanto paga, qual e "
    "a franquia, em quantos dias reembolsa ou o que esta excluido — mesmo que "
    "UMA conversa mostre um caso assim, porque isso e CONTRATADO e varia por "
    "apolice. Onde couber cobertura, remeta a leitura.\n"
    "   Errado: 'Confirmei aqui: voce tem cobertura de vidros' / 'a seguradora "
    "cobre a diferenca' / 'o prazo e de 30 dias'.\n"
    "   Certo: 'Vou confirmar na sua apolice se esse item entra e ja te "
    "retorno — nao te dou resposta no chute.'\n"
    "\n"
    "4. NENHUMA FRASE PRONTA PODE TER ESPACO EM BRANCO. Tudo em como_pedir, "
    "frases_exemplo, acolhimento e encerramento sai para o segurado COMO ESTA. "
    "[modelo], [xxxx], R$ [valor], valor X — o segurado recebe os colchetes.\n"
    "   Errado: 'E pro [modelo] de placa final [xxxx], confirma?'\n"
    "   Certo: 'E do carro que esta na sua apolice, confirma?'\n"
    "\n"
    "5. SEGURADORA SO QUANDO ESTA ESCRITA. Nunca infira a companhia pelo "
    "assunto. Uma regra da Porto atribuida a Allianz faz o agente mentir para "
    "o segurado com confianca.\n"
    "\n"
    "6. NENHUM DADO PESSOAL, EM CAMPO NENHUM — e o validador reprova o "
    "playbook INTEIRO. Sem nome, telefone, CPF/CNPJ, placa, endereco, e-mail, "
    "protocolo, valor em reais, data ou numero com mais de quatro digitos. "
    "Escreva a categoria: 'o numero da apolice'. Um unico desses derruba tudo "
    "no gate.\n"
    "\n"
    "7. O QUE A CORRETORA JA TEM NAO SE PERGUNTA. A regra mora dentro da "
    "definicao de ja_temos_na_apolice, abaixo.\n"
    "\n"
    "8. VOCE LEU NO MAXIMO 20 ATENDIMENTOS DE UMA CORRETORA. Nao escreva 'no "
    "Brasil', 'o padrao do mercado', 'toda seguradora', 'padrao-ouro'. E se "
    "dois atendimentos discordarem sem nenhum estar errado, isso e sinal de "
    "que a coisa VARIA — diga que varia, nao escolha uma.\n"
    "\n"
    "9. CONDUTA QUE SO SERVE PARA BURLAR NAO VIRA PLAYBOOK. Antedatar, omitir "
    "documento de proposito, ajustar o relato para encaixar na cobertura: vai "
    "para o_que_evitar, descrito, sem a receita.\n"
    "\n"
    "10. PREFIRA A FICHA CURTA. Campo que um atendimento pediu e nenhum outro "
    "usou nao entra. No maximo 12 campos — cada campo a mais e uma pergunta a "
    "mais na cara de quem esta parado na chuva.\n"
    "\n"
    "## A resposta\n"
    "APENAS JSON valido, sem uma palavra fora dele, cabendo em 10.000 chars:\n"
    "{\"objetivo\": \"...\", \"acolhimento\": \"...\", \"pre_checks\": [\"...\"], "
    "\"ficha_coleta\": [{\"campo\": \"...\", \"como_pedir\": \"...\", "
    "\"quando\": \"...\", \"ja_temos_na_apolice\": true}], "
    "\"sensibilidade\": \"...\", \"encerramento\": \"...\", "
    "\"frases_exemplo\": [\"...\"], \"o_que_evitar\": [\"...\"], "
    "\"fora_do_escopo\": [\"...\"], \"lastro\": {\"atendimentos_lidos\": 0, "
    "\"com_atendimento_humano\": 0, \"nota_media\": 0, \"observado\": [\"...\"], "
    "\"inferido\": [\"...\"]}}\n"
    "\n"
    "### Campo por campo\n"
    "- pre_checks: o que se confere ANTES de prometer. E aqui que mora tudo que "
    "depende da apolice (regra 3). Ate 7.\n"
    "- ficha_coleta: ate 12 itens, na ordem em que os bons atendimentos pedem.\n"
    "  . como_pedir: a FRASE EXATA que vai ao segurado. Portugues natural de "
    "WhatsApp, uma pergunta por vez, sem espaco em branco (regra 4), sem "
    "afirmar cobertura (regra 3).\n"
    "  . ja_temos_na_apolice: TRUE quando a corretora JA TEM o dado — nome, "
    "apolice, seguradora, placa, modelo, telefone de cadastro. Sendo true, "
    "como_pedir NAO PODE SER PERGUNTA: tem de ser confirmacao que se responde "
    "com sim ou nao.\n"
    "      Errado: 'Qual a placa do veiculo?' / 'E o modelo, qual e?'\n"
    "      Certo: 'E do carro da sua apolice, confirma?' / 'O prestador te liga "
    "nesse numero mesmo, ou tem outro melhor agora?'\n"
    "      Perguntar o que ja se tem faz o segurado repetir para a maquina o "
    "que a corretora ja sabe, e e a primeira coisa que ele percebe.\n"
    "      FALSE so quando o dado nasce do caso: o que aconteceu, onde o "
    "veiculo esta, se ha alguem dentro.\n"
    "- sensibilidade: o cuidado humano que ESTE servico pede, tirado do que as "
    "conversas mostram. Nao escreva aqui nada que os outros campos "
    "contradigam.\n"
    "- o_que_evitar: o que os atendimentos de nota BAIXA ensinam a nao fazer. "
    "Sem atendimento ruim no material, lista vazia.\n"
    "- fora_do_escopo: o que estas conversas NAO ensinam e que quem ler nao "
    "deve supor que esta aqui. E o campo que impede o proximo leitor de "
    "confundir silencio com ausencia de problema. Vazio quase nunca e "
    "honesto.\n"
    "- lastro: com_atendimento_humano = quantos tem score maior que 0; "
    "observado = afirmacoes amarradas ao material, com a contagem ('confirmar "
    "a placa antes de abrir: visto em 9 de 14'); inferido = o que voce escreveu "
    "e NAO esta nos atendimentos. TUDO em inferido e proibido aparecer como "
    "afirmacao nos outros campos: se for indispensavel, vire pre_check.\n"
    "\n"
    "Se o material for pouco para sustentar um playbook, diga isso em "
    "fora_do_escopo e escreva so a ficha que ele sustenta. Playbook curto e "
    "verdadeiro vale mais que completo e inventado — e e o unico que sobrevive "
    "ao primeiro segurado que perguntar."
)


# O nome público das mesmas regras. O Lapidador (`prompt_optimizer`) reescreve
# playbooks ATIVOS de hora em hora e escrevia com um esquema PRÓPRIO, mais
# antigo: sem `o_que_evitar`, `fora_do_escopo` e `lastro`, e sem nenhuma das
# proibições. Ele apagaria os três campos e reintroduziria os defeitos — em uma
# hora, sobre os playbooks que estão no ar.
#
# Duas cópias de uma regra divergem: foi exatamente o que aconteceu aqui. Quem
# lapida importa daqui, e a próxima regra escrita neste texto já nasce valendo
# para os dois.
REGRAS_DO_PLAYBOOK = _STAGE2_SYSTEM


# Os valores de `tipo` que servem de SERVIÇO quando o serviço veio "outro".
#
# `assistencia` está fora de propósito: quem procura o playbook em runtime
# sempre nomeia o subserviço (guincho, encanador...), nunca "assistencia" — um
# grupo com esse nome nasceria mudo. E `outro` está fora porque é o único que
# de fato não diz nada: 📊 `outro/outro` tem 381 sessões com nota média 52,4,
# contra 76,2 de `auto/cobranca`.
_TIPOS_QUE_SAO_SERVICO = ("cobranca", "apolice", "renovacao", "sinistro")


def chave_do_grupo(destilado: Dict[str, Any]) -> Tuple[str, str]:
    """O `(ramo, servico)` do playbook que este atendimento alimenta.

    `("", "")` quando ele não alimenta nenhum.

    🔴 07/08/2026 — `servico == "outro"` ERA DESCARTADO, E LEVAVA O MELHOR JUNTO
    ==========================================================================
    Duas linhas jogavam fora todo atendimento cujo serviço viesse "outro". 📊 O
    que elas jogavam fora:

        auto/outro          2.219 sessões úteis   nota 74,4   ← maior E melhor
        outro/outro         1.468                 nota 67,2
        residencial/outro     166                 nota 76,3
        vida/outro             24                 nota 72,9
                            -----
                            3.877 — mais da metade do material aproveitável

    A regra era defensável na origem: um playbook chamado "outro" seria vago
    demais para servir. Só que ela foi escrita quando "outro" era resto. Virou
    o maior balde do acervo — e **a informação para desfazê-lo já estava
    gravada ao lado**: o Estágio 1 escreve `tipo` E `servico`, e só o segundo
    era lido.

        dentro de servico='outro', o que o `tipo` diz:
            auto/cobranca   1.904 úteis   nota 76,2   ← melhor grupo do acervo
            outro/cobranca    986         nota 72,7
            outro/outro       381         nota 52,4   ← o único que é ruído
            auto/apolice       64         nota 71,8

    📊 E cobrança é 2.915 das 12.063 cartas do RAG (24%): o maior bloco de
    trabalho da corretora, sem uma linha de conduta escrita sobre ele.
    """
    ramo = str(destilado.get("ramo") or "").strip()
    if not ramo:
        return ("", "")
    servico = str(destilado.get("servico") or "").strip()
    if servico and servico != "outro":
        return (ramo, servico)
    tipo = str(destilado.get("tipo") or "").strip()
    return (ramo, tipo) if tipo in _TIPOS_QUE_SAO_SERVICO else ("", "")


def _load_group_summaries_sync(ramo: str, servico: str, limit: int = 30) -> List[Dict[str, Any]]:
    """Os atendimentos JÁ DESTILADOS de um (ramo, serviço).

    Isto lia as 300 sessões mais RECENTES e filtrava em Python. E a recuperação
    do histórico processa da mais ANTIGA para a mais nova — as duas funções
    olhavam para pontas opostas da linha do tempo.

    O efeito, medido em 28/07/2026: **zero playbooks** com 7.620 sessões
    destiladas. Enquanto o histórico era processado, as 300 mais recentes ainda
    não tinham `distilled`, o filtro devolvia lista vazia e a síntese era
    pulada em toda rodada. Existem grupos com 152, 72 e 69 atendimentos.

    Agora o filtro é do banco: pede as sessões DAQUELE grupo, mais recentes
    primeiro, e para quando tem o bastante.

    🔴 E ENTREGA OS MELHORES, NÃO OS MAIS RECENTES — 07/08/2026.
    ===========================================================
    A recência escolhia mal. 📊 Medido nas 30 sessões que esta função entregava:

        auto/vidros    14 das 30 com score 0   média 37,8
        auto/guincho   12 das 30 com score 0   média 45,5
        auto/sinistro  10 das 30 com score 0   média 47,2

    E `auto/vidros` tem **148 sessões com nota ≥ 70** no acervo. O modelo mais
    caro do sistema recebia uma amostra de média 37,8 quando existia material
    de 69,3 ali do lado.

    **Score 0 não é nota baixa: é "não houve atendimento humano"** — robô da
    seguradora, central de prestadora, fragmento sem resposta. Essas linhas não
    têm conduta para ensinar e ocupavam metade da amostra. 📊 `auto/bateria`
    foi escrito com 13 sessões das quais **8 tinham score 0**: o playbook
    aprendeu conduta de um bot, e o prompt nunca soube.

    A janela continua sendo de recência — conduta de um ano atrás pode estar
    vencida —, mas a ESCOLHA dentro dela é por nota.

    E isto tem três leitores: o `playbook_gate` chama o resultado de
    `padrao_ouro_humano` e o Lapidador de `condutas_douradas`. Os dois julgavam
    o candidato contra uma amostra em que metade não era atendimento.
    """
    from app.core.database import get_supabase_client

    db = get_supabase_client()
    # ⚠️ A ordenação NÃO pode ser feita no banco: `->>` devolve TEXTO, e "9" é
    # maior que "70" em ordem lexicográfica. Seria uma ordenação que parece
    # funcionar e entrega o inverso do pedido.
    janela = max(limit * 6, 180)

    def _pagina(filtros) -> List[Dict[str, Any]]:
        q = (db.client.table("attendance_sessions")
             .select("summary").eq("status", "closed")
             .eq("summary->distilled->>ramo", ramo))
        for campo, valor in filtros:
            q = q.eq(f"summary->distilled->>{campo}", valor)
        rows = q.order("started_at", desc=True).limit(janela).execute().data or []
        return [d for d in ((r.get("summary") or {}).get("distilled") for r in rows) if d]

    destilados = _pagina([("servico", servico)])
    # O MESMO GRUPO MORA EM DOIS FORMATOS NO BANCO — 07/08/2026.
    #
    # `chave_do_grupo` passou a aceitar `tipo` no lugar de `servico` quando o
    # serviço veio "outro". Mas no banco esse material continua gravado como
    # `servico='outro'` + `tipo='cobranca'` — pedir `servico='cobranca'` acha
    # zero linha. 📊 `auto/cobranca`: 0 pela primeira consulta, 1.904 pela
    # segunda.
    #
    # Nenhuma linha é reescrita: destilar de novo 9.196 sessões para arrumar um
    # rótulo custaria o acervo inteiro no modelo caro. A leitura entende os dois
    # formatos, e o formato novo nasce sozinho na próxima destilação.
    #
    # As duas consultas não se sobrepõem (`servico=X` contra `servico=outro`),
    # então não há o que deduplicar — mas a concatenação embaralha a ordem de
    # recência de que o desempate por nota depende, e por isso ela é refeita.
    if servico in _TIPOS_QUE_SAO_SERVICO:
        destilados.extend(_pagina([("servico", "outro"), ("tipo", servico)]))
        destilados.sort(key=lambda d: str(d.get("at") or ""), reverse=True)

    def _nota(d: Dict[str, Any]) -> int:
        try:
            return int(d.get("score") or 0)
        except (TypeError, ValueError):
            return 0

    # As DUAS condições, não uma: 📊 `auto/vidros` tem 155 sessões com score 0 e
    # 193 com `resumo_conduta` vazio — os conjuntos se sobrepõem e não coincidem.
    com_humano = [d for d in destilados
                  if _nota(d) > 0 and (d.get("resumo_conduta") or [])]
    # `sort` estável + entrada já em ordem de recência: empate de nota preserva
    # o mais recente, sem precisar de chave secundária.
    com_humano.sort(key=_nota, reverse=True)
    return com_humano[:limit]


def _grupos_sem_playbook_sync(limite: int) -> List[Tuple[str, str]]:
    """Grupos que já têm material suficiente e nenhum playbook ainda.

    A síntese só olhava os grupos TOCADOS na rodada. Com o histórico inteiro já
    destilado, quase nenhuma rodada toca grupo nenhum — e os playbooks nunca
    apareceriam, por mais conversa que houvesse no banco.

    Os maiores primeiro: é onde está a conduta que mais se repete, e portanto o
    padrão mais confiável de aprender.
    """
    from app.core.database import get_supabase_client

    db = get_supabase_client()
    try:
        # 🔴 O QUE DESTRAVA A VERSÃO 2 É MATERIAL NOVO — não a ausência de
        # playbook, e não o status dele.
        #
        # A regra era: existe playbook nesse par? então nunca mais sintetize.
        # 📊 07/08/2026, o preço disso: `auto/sinistro` foi escrito com **30
        # conversas** e existem **1.405** destiladas. Ele usa 2,1% do material e
        # nunca usaria mais. O `playbook_gate` tem versão, juiz que não deixa
        # regredir e rollback — faltava alguém **gerar a versão 2**.
        #
        # A primeira tentativa de conserto foi "só ATIVO bloqueia". Um teste
        # existente reprovou na hora, e com razão: um rascunho que ninguém
        # aprova faria o grupo ser re-sintetizado a CADA RODADA, no modelo mais
        # caro, para sempre. Trocaria conhecimento congelado por dinheiro
        # queimado.
        #
        # A regra certa não é sobre status, é sobre APRENDIZADO DISPONÍVEL:
        # o grupo volta para a fila quando chegou material suficiente **depois**
        # do último playbook. Enquanto não chegou, não há o que aprender de
        # novo, e refazer seria pagar para reescrever a mesma coisa.
        ultimo_playbook: Dict[Tuple[str, str], str] = {}
        for r in (db.client.table("conduct_playbooks")
                  .select("ramo, servico, created_at")
                  .order("created_at", desc=True)
                  .limit(1000).execute().data or []):
            chave = (r.get("ramo"), r.get("servico"))
            # Ordenado do mais novo para o mais antigo: o primeiro de cada par
            # é o mais recente, qualquer que seja o status dele.
            ultimo_playbook.setdefault(chave, str(r.get("created_at") or ""))

        minimo_para_refazer = _env_int("DISTILLER_PLAYBOOK_REFRESH_MIN", 25)

        # Conta, por grupo, o material TOTAL e o que chegou depois do playbook.
        contagem: Dict[Tuple[str, str], int] = {}
        novas_desde: Dict[Tuple[str, str], int] = {}
        inicio = 0
        while inicio < 20000:
            lote = (db.client.table("attendance_sessions")
                    .select("summary, started_at")
                    .eq("status", "closed")
                    .range(inicio, inicio + 999).execute().data) or []
            for r in lote:
                d = ((r.get("summary") or {}).get("distilled")) or {}
                chave = chave_do_grupo(d)
                if chave == ("", ""):
                    continue
                contagem[chave] = contagem.get(chave, 0) + 1
                marco = ultimo_playbook.get(chave)
                # `distilled.at` é quando o FATO foi extraído; é ele que diz se
                # o material é novo para o playbook, não quando a conversa
                # aconteceu — o pareamento traz passado.
                quando = str(d.get("at") or r.get("started_at") or "")
                if marco and quando > marco:
                    novas_desde[chave] = novas_desde.get(chave, 0) + 1
            if len(lote) < 1000:
                break
            inicio += 1000

        def _entra(grupo: Tuple[str, str], total: int) -> bool:
            if total < _MIN_SESSIONS_DEFAULT:
                return False
            if grupo not in ultimo_playbook:
                return True                      # nunca teve playbook
            return novas_desde.get(grupo, 0) >= minimo_para_refazer

        faltando = [g for g, n in sorted(contagem.items(), key=lambda x: -x[1])
                    if _entra(g, n)]
        return faltando[:limite]
    except Exception as e:  # noqa: BLE001
        logger.warning("[DESTILADOR] varredura de grupos falhou: %s", type(e).__name__)
        return []


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

    # ------------------------------------------------------------------ #
    # TETO DE GASTO — o ponto único por onde todo custo de modelo passa
    # ------------------------------------------------------------------ #
    # O botão "Processar aprendizado" e a rodada agendada chamam esta mesma
    # função. Sem teto, um clique com 6.118 conversas na fila gasta todo o
    # saldo disponível — foi o que aconteceu em 29/07/2026: a estimativa era
    # de US$ 1 e a rodada consumiu US$ 6, porque ela não processa "um lote",
    # processa até a fila secar ou o crédito acabar.
    #
    # Enquanto a destilação pelo plano Max estiver rodando por fora, este teto
    # fica em 0 e NENHUMA chamada de modelo acontece. Uma corretora nova pode
    # ser pareada com segurança: ela captura tudo, e nada é cobrado.
    #
    # O teto NÃO desliga curar e publicar. Essas duas etapas não chamam modelo
    # de linguagem — só o embedding, que custa centavos — e são justamente o
    # caminho por onde as cartas escritas por fora chegam ao RAG. Travar o
    # gasto não pode significar travar o conhecimento.
    # ANTES DE TUDO, e independente do teto: a conversa que acabou tem de ser
    # marcada como acabada. Não chama modelo, não custa nada, e sem isto o
    # material fica invisível — ver `_fechar_sessoes_vencidas_sync`.
    stats["sessoes_fechadas"] = await asyncio.to_thread(_fechar_sessoes_vencidas_sync)

    teto = _teto_de_gasto()
    if teto <= 0:
        logger.info("[DESTILADOR] teto em 0: nenhuma chamada de modelo nesta "
                    "rodada. Curadoria e publicação seguem normalmente. "
                    "Para religar, DESTILADOR_TETO_POR_RODADA=<n> sessões.")

    max_sessions = min(teto, _env_int(
        "DISTILLER_BACKLOG_SESSIONS_PER_RUN" if atrasado
        else "DISTILLER_MAX_SESSIONS_PER_RUN",
        400 if atrasado else 40))
    min_group = _env_int("DISTILLER_MIN_SESSIONS", _MIN_SESSIONS_DEFAULT)

    # Sem `return` antecipado quando não há sessão: antes, fila vazia abortava
    # a rodada inteira e as cartas prontas ficavam sem publicar. Com a
    # destilação externa isso passou a ser o caso NORMAL, não a exceção.
    sessions = (await asyncio.to_thread(_load_undistilled_sync, max_sessions)
                if max_sessions > 0 else [])
    stats["teto"] = teto

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
    # 🔴 ESTA VARIÁVEL NÃO PODE SE CHAMAR `teto`.
    #
    # Ela se chamava. E como `teto` já guardava o TETO DE GASTO desde a linha
    # 622, esta atribuição o apagava — sem erro, sem aviso. Lá embaixo,
    # `min(teto, DISTILLER_PLAYBOOKS_PER_RUN)` deixava de ser `min(0, 3) = 0` e
    # virava `min(6, 3) = 3`.
    #
    # 📊 Medido em produção, 05/08/2026, com linha de controle — a mesma rodada:
    #
    #     estágio 1 (Sonnet, barato)   0 sessões destiladas   ← teto obedecido
    #     estágio 2 (Opus 5, caro)     2 playbooks gerados    ← teto furado
    #
    # O freio de gasto travava o cano estreito e deixava o largo aberto: o
    # modelo MAIS CARO do sistema seguia rodando com o freio puxado, três vezes
    # por rodada, a cada 30 minutos. É exatamente o risco que o docstring de
    # `_teto_de_gasto()` diz ter fechado — "a trava vazaria justamente pelo cano
    # mais largo, e em silêncio".
    #
    # Nome próprio, e o teto de gasto sobrevive à sua própria função.
    concorrencia = _env_int("DISTILLER_CONCURRENCY", 6)
    vagas = asyncio.Semaphore(concorrencia)
    trava_stats = asyncio.Lock()

    async def _uma_sessao(sess: Dict[str, Any]) -> None:
        async with vagas:
            await _destilar_sessao(sess, stats, touched_groups, trava_stats)

    await asyncio.gather(*[_uma_sessao(s) for s in sessions],
                         return_exceptions=True)

    # Estagio 2 — playbooks (modelo FORTE)
    #
    # Alem dos grupos tocados nesta rodada, entram os que JA TEM material e
    # nenhum playbook. Sem isso, com o historico inteiro ja destilado, nenhuma
    # rodada toca grupo nenhum e a sintese nunca acontece.
    #
    # TETO POR RODADA: cada playbook e uma chamada ao modelo mais caro. Sem
    # teto, a primeira rodada depois deste conserto tentaria sintetizar todos
    # os grupos de uma vez. Com teto, eles saem aos poucos e o custo por
    # rodada e previsivel.
    # O playbook é a chamada mais cara do sistema (modelo forte, resposta
    # longa). Com o teto de GASTO em 0 nenhum é sintetizado — `grupos[:0]` é
    # vazio. Isto voltou a ser verdade quando a concorrência ganhou nome
    # próprio: por oito dias o comentário afirmou isto e o código fazia o
    # contrário (ver a nota acima).
    por_rodada = min(teto, _env_int("DISTILLER_PLAYBOOKS_PER_RUN", 3))
    grupos = list(touched_groups.keys())
    for g in _grupos_sem_playbook_sync(por_rodada):
        if g not in grupos:
            grupos.append(g)
    for (ramo, servico) in grupos[:por_rodada]:
        try:
            # As chaves já vêm de `chave_do_grupo`, que nunca devolve "outro"
            # como serviço nem vazio como ramo. A guarda fica como cinto: uma
            # chave malformada aqui viraria um playbook chamado "auto/outro".
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

    # CURAR E PUBLICAR FAZEM PARTE DA RODADA.
    #
    # Antes isso dependia de alguém abrir uma tela e apertar um botão que nem
    # existia direito. Com 1.274 cartas prontas e centenas chegando a cada
    # corretora pareada, "alguém lembra" não é um plano — e carta não publicada
    # é conhecimento que o agente não tem na hora de atender.
    #
    # A revisão de PII é determinística e roda em três camadas (`templatize` na
    # extração, instrução à LLM, `_card_pii_clean` no instante da publicação).
    # O que sobra para o humano é rejeitar um fato errado, e isso continua em
    # /admin/espelho — rejeitar tira do RAG.
    #
    # Curar ANTES de publicar: senão as quase-cópias entram no Qdrant e tirá-las
    # de lá depois é bem mais caro do que não colocar.
    try:
        from app.services.curadoria_cartas import curar_sync, publicar_lote_sync

        cur = await asyncio.to_thread(curar_sync, True)
        # 1.000 e nao 300. Com 914 cartas na fila e UMA rodada por noite, um
        # teto de 300 levaria QUATRO NOITES para o agente ter o que a equipe
        # ensinou. Publicar e barato — um embedding pequeno por carta, menos de
        # dois centavos pelas 914 — e a rodada agora roda em segundo plano,
        # entao demorar alguns minutos nao trava tela nenhuma.
        pub = await asyncio.to_thread(
            publicar_lote_sync, _env_int("CARDS_PUBLISH_PER_RUN", 1000))
        stats["cards_juntados"] = cur.get("juntadas", 0)
        stats["cards_publicados"] = pub.get("publicadas", 0)
        logger.info("[DESTILADOR] cartas: %d juntadas, %d publicadas no RAG",
                    cur.get("juntadas", 0), pub.get("publicadas", 0))
    except Exception as e:  # noqa: BLE001 — publicar nunca derruba a destilação
        logger.error("[DESTILADOR] curadoria/publicação falhou: %s", type(e).__name__)

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
        if not data and not raw:
            # A CHAMADA NEM RESPONDEU. Não é defeito desta sessão: é crédito
            # acabado, rede caída, provedor sobrecarregado (529). `_call_llm`
            # devolve None nos dois casos, e contar isso como recusa da sessão
            # foi o defeito da minha própria trava.
            #
            # Medido em 30/07/2026: 350 sessões chegaram a três "falhas" e
            # ficaram PARADAS PARA SEMPRE porque a conta ficou sem crédito no
            # meio de uma rodada. Perdi 350 conversas com um guarda que existia
            # justamente para não perder dinheiro — e sem que ninguém veja, que
            # é o pior formato.
            #
            # Sem marca: a sessão volta na fila e será tentada quando houver
            # crédito. O gasto repetido que a trava evita é outro — resposta
            # ILEGÍVEL, que é defeito real e não passa daqui.
            logger.info("[DESTILADOR] sessão %s: modelo não respondeu (crédito "
                        "ou rede) — segue na fila, sem contar recusa",
                        sess.get("id"))
            return
        if not data:
            # O MODELO JA RESPONDEU E JA FOI COBRADO. Sem marca nenhuma, esta
            # sessao volta na fila da proxima rodada, paga de novo, falha de
            # novo — para sempre, e em silencio.
            #
            # Foi exatamente isso em 28/07/2026: o Sonnet 5 passou a PENSAR por
            # padrao, a resposta virou lista de blocos, `_parse_json` recusou, e
            # 3.445 chamadas produziram 1.111 destilacoes. As outras 2.334 foram
            # a MESMA sessao tentada varias vezes — US$ 15 dos US$ 22 gastos.
            #
            # A causa esta corrigida em `_texto_da_resposta`. Este contador e o
            # que impede a proxima causa, ainda desconhecida, de custar o mesmo:
            # depois de tres recusas a sessao para de ser tentada e aparece no
            # painel como parada. Perder uma sessao e barato; pagar por ela
            # indefinidamente sem ninguem ver, nao.
            summary = dict(sess.get("summary") or {})
            falhas = int(summary.get("distill_falhas") or 0) + 1
            summary["distill_falhas"] = falhas
            # 🔴 GRAVAR O MOTIVO, e não só o contador.
            #
            # 📊 07/08/2026: 342 sessões estavam paradas com 3 falhas e **zero**
            # tinham motivo gravado. Todas do dia 28/07 — o dia do bug do
            # "modelo pensa por padrão", já corrigido. Só deu para saber disso
            # pela DATA; o registro não dizia nada.
            #
            # Sem o motivo, quem olha a fila parada não consegue distinguir
            # "causa já resolvida, é só destravar" de "causa viva, destravar vai
            # queimar dinheiro de novo". As duas exigem ações opostas.
            summary["distill_erro"] = "resposta ilegivel do modelo"
            summary["distill_erro_em"] = datetime.now(timezone.utc).isoformat()
            await asyncio.to_thread(_save_session_summary_sync, sess["id"], summary)
            async with trava:
                stats["falhas_de_leitura"] = stats.get("falhas_de_leitura", 0) + 1
                if falhas >= LIMITE_DE_FALHAS:
                    stats["paradas"] = stats.get("paradas", 0) + 1
            logger.warning("[DESTILADOR] sessão %s: resposta ilegível (%dª vez%s)",
                           sess.get("id"), falhas,
                           ", parada" if falhas >= LIMITE_DE_FALHAS else "")
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
            # `seguradora` aqui é CANDIDATA, não veredito: é a companhia da
            # sessão, e a sessão produz até oito fatos, a maioria genérica.
            # Quem decide se ela vale para ESTE fato é `_store_card_sync`, pelo
            # texto do próprio fato. Passar o candidato é certo; gravá-lo
            # direto era o defeito.
            card_meta = {"ramo": data.get("ramo"),
                         "seguradora_candidata": data.get("seguradora")}
            cid = await asyncio.to_thread(_store_card_sync, str(fato), card_meta)
            if cid:
                if _card_pii_clean(" ".join(str(fato).split())):
                    novos += 1
                else:
                    rejeitados += 1

        # A MESMA regra de chave que `_grupos_sem_playbook_sync` usa. Enquanto
        # eram duas contas, a fila de trás contava um grupo que a da frente
        # descartava.
        chave = chave_do_grupo(data)

        async with trava:
            stats["sessions"] += 1
            stats["cards_new"] += novos
            stats["cards_rejected_pii"] += rejeitados
            if chave != ("", ""):
                touched_groups[chave] = touched_groups.get(chave, 0) + 1
    except Exception as e:  # noqa: BLE001
        # Uma sessão que falha não derruba as outras cinco em voo, e a próxima
        # rodada a pega de novo: ela continua sem a marca `distilled`.
        # O nome da exceção sozinho não conserta nada. Em 28/07/2026 um
        # `ModuleNotFoundError` derrubou TODAS as sessões e a linha de log não
        # dizia qual módulo faltava — a mesma cegueira do "HTTPStatusError" da
        # mídia. Para erro de import, o nome do módulo é a informação inteira,
        # e não é dado de ninguém.
        faltou = getattr(e, "name", "") or ""
        logger.error("[DESTILADOR] sessão %s falhou: %s%s",
                     sess.get("id"), type(e).__name__,
                     f" ({faltou})" if faltou else "")


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
