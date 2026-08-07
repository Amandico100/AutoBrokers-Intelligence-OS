"""Memory & Learning Fabric — SPEC-052 Lote 4, executado na SPEC-059 Bloco A.

NAO e um segundo motor de memoria
---------------------------------
`MemoryService` continua sendo quem extrai fato, gera resumo e grava em
`user_memories` e `session_summaries`. Este modulo e o que faltava em volta
dele: **o gatilho, o escopo e a governanca**.

O defeito que ele corrige (FATO, medido em 26/07/2026)
------------------------------------------------------
`user_memories = 0` e `session_summaries = 0` com 144 conversas. A SPEC-054
Bloco B encontrou a causa (`session_end` inalcancavel) e corrigiu o
`should_summarize`. Mas a correcao continuou inerte, e da para provar em uma
linha: `graph.py:1052` chama o gatilho com

    last_message_at=datetime.now()

Ou seja, no instante do turno a inatividade e sempre ZERO. A condicao
"passou do timeout" nunca e satisfeita durante a conversa — por construcao.
E as seis linhas de `memory_settings` estao todas em `session_end`.

A conclusao importa: **o gatilho nao pode viver dentro do turno**. Ninguem
sabe, no meio da conversa, que ela acabou. Quem sabe e o relogio, depois.

Por isso o fechamento roda como varredura, no laco de manutencao do Smith
Worker que ja existe — sem agendador novo (CLAUDE.md §5).
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

# A lista de formas de negar mora em `curadoria_cartas` — o modulo que cura
# TEXTO e o dono natural do conceito. Aqui ela e so consumida.
#
# Uma lista so, dois usos: contradicao entre memorias da corretora (aqui) e a
# que aposenta carta vencida no RAG (`achar_contradicoes`). Duas listas dariam,
# no dia em que alguem acrescentasse uma forma num lado so, uma contradicao
# detectada num lugar e invisivel no outro — e a invisivel e a que continua
# sendo respondida ao segurado.
#
# A dependencia aponta para o modulo LEVE: `curadoria_cartas` importa so
# logging/re/unicodedata/typing. O contrario quebraria os testes que carregam
# a curadoria isolada — foi o que aconteceu ao escrever isto.
from .curadoria_cartas import tem_negacao

logger = logging.getLogger(__name__)

TIMEOUT_PADRAO_MIN = 30
MAX_MENSAGENS_POR_SESSAO = 200
MIN_MENSAGENS_PARA_RESUMIR = 4


@dataclass
class MensagemSimples:
    """Forma minima que o `MemoryService` sabe ler (`.type` e `.content`)."""

    type: str
    content: str


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _dt(valor) -> Optional[datetime]:
    if not valor:
        return None
    try:
        d = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:  # noqa: BLE001
        return None


def sessoes_encerradas(conversas: list[dict], agora: datetime,
                       *, timeout_min: int = TIMEOUT_PADRAO_MIN) -> list[dict]:
    """Puro: quais conversas ja podem ser consideradas encerradas.

    "Encerrada" aqui e logica, nao declarada: passou o tempo de inatividade
    configurado. E o mesmo criterio que o modo `inactivity` usa — a diferenca
    e que agora ele e avaliado por quem tem o relogio na mao.
    """
    saida = []
    for c in conversas or []:
        ultima = _dt(c.get("last_message_at") or c.get("updated_at"))
        if ultima is None:
            continue
        minutos = (agora - ultima).total_seconds() / 60.0
        if minutos >= timeout_min:
            saida.append({**c, "inativa_min": round(minutos, 1)})
    return sorted(saida, key=lambda x: -x["inativa_min"])


def chave_de_memoria(texto: str) -> str:
    """Chave estavel de um fato da corretora, para deduplicar."""
    normalizado = " ".join(str(texto or "").lower().split())[:300]
    return hashlib.sha256(normalizado.encode("utf-8")).hexdigest()[:32]


def contradiz(fato_a: str, fato_b: str) -> bool:
    """Deteccao lexica de contradicao. Conservadora de proposito.

    Compara o conjunto de termos longos e a presenca de negacao. Nao pretende
    ser semantica: pretende nunca deixar passar em silencio o caso obvio —
    "atende sabado" contra "nao atende sabado" — marcando para revisao em vez
    de sobrescrever.

    ⚠️ O corte de 0,6 e alto DE PROPOSITO para memoria de corretora, onde os
    fatos sao curtos e parecidos. 📊 Ele nao serve para carta de conhecimento:
    no caso real da Porto (07/08/2026) a sobreposicao deu 0,30, porque a carta
    que nega traz a explicacao inteira e a que afirma nao. Por isso
    `curadoria_cartas` usa CONTENCAO com regua propria e reaproveita daqui so a
    polaridade (`tem_negacao`) — a parte que e a mesma nos dois dominios.
    """
    a, b = str(fato_a or "").lower(), str(fato_b or "").lower()
    termos_a = {t for t in a.split() if len(t) > 4}
    termos_b = {t for t in b.split() if len(t) > 4}
    if not termos_a or not termos_b:
        return False
    sobreposicao = len(termos_a & termos_b) / max(1, min(len(termos_a), len(termos_b)))
    if sobreposicao < 0.6:
        return False
    return tem_negacao(a) != tem_negacao(b)


class MemoryFabric:
    def __init__(self, supabase_client: Any):
        self.db = getattr(supabase_client, "client", supabase_client)

    # ------------------------------------------------------------------
    # Fechamento de sessao — o gatilho que faltava
    # ------------------------------------------------------------------

    async def fechar_sessoes_inativas(self, *, limite: int = 10,
                                      timeout_min: Optional[int] = None) -> dict:
        """Fecha sessoes paradas e produz resumo + memoria. Devolve o que fez."""
        from .memory_service import MemoryService

        agora = _agora()
        timeout = int(timeout_min or TIMEOUT_PADRAO_MIN)

        try:
            corte = (agora - timedelta(minutes=timeout)).isoformat()
            limite_inferior = (agora - timedelta(days=7)).isoformat()
            conversas = (self.db.table("conversations")
                         .select("id, company_id, user_id, session_id, channel, "
                                 "last_message_at, updated_at")
                         .lt("last_message_at", corte)
                         .gte("last_message_at", limite_inferior)
                         .order("last_message_at", desc=True)
                         .limit(limite * 6).execute()).data or []
        except Exception as exc:  # noqa: BLE001
            logger.warning("[MemoryFabric] leitura de conversas: %s", type(exc).__name__)
            return {"avaliadas": 0, "resumidas": 0, "puladas": 0}

        candidatas = sessoes_encerradas(conversas, agora, timeout_min=timeout)
        servico = MemoryService(self.db)

        resumidas, puladas = 0, 0
        for conversa in candidatas:
            if resumidas >= limite:
                break
            session_id = str(conversa.get("session_id") or conversa.get("id"))
            company_id = str(conversa.get("company_id") or "")
            user_id = str(conversa.get("user_id") or "")
            if not company_id or not user_id:
                puladas += 1
                continue
            if self._ja_resumida(session_id, company_id):
                puladas += 1
                continue

            mensagens = self._mensagens(str(conversa["id"]))
            if len(mensagens) < MIN_MENSAGENS_PARA_RESUMIR:
                # Conversa de duas linhas nao produz memoria util e gastaria
                # uma chamada de modelo para descobrir isso.
                puladas += 1
                continue

            try:
                settings = await servico.get_memory_settings_async(None)
                # `session_ended=True` e a diferenca desta chamada para a do
                # turno: aqui quem chama SABE que a sessao acabou, porque
                # esperou o timeout para descobrir.
                await servico.process_summarization_async(
                    session_id=session_id, user_id=user_id, company_id=company_id,
                    messages=mensagens,
                    channel=str(conversa.get("channel") or "web"),
                    settings=settings)
                resumidas += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("[MemoryFabric] resumo da sessão %s falhou: %s",
                               session_id[:12], type(exc).__name__)
                puladas += 1

        if resumidas:
            logger.info("[MemoryFabric] %d sessão(ões) encerrada(s) e resumida(s)", resumidas)
        return {"avaliadas": len(candidatas), "resumidas": resumidas, "puladas": puladas}

    def _ja_resumida(self, session_id: str, company_id: str) -> bool:
        try:
            r = (self.db.table("session_summaries").select("id")
                 .eq("session_id", session_id).eq("company_id", company_id)
                 .limit(1).execute())
            return bool(r.data)
        except Exception:  # noqa: BLE001
            return False

    def _mensagens(self, conversation_id: str) -> list[MensagemSimples]:
        try:
            linhas = (self.db.table("messages").select("role, content, created_at")
                      .eq("conversation_id", conversation_id)
                      .order("created_at", desc=False)
                      .limit(MAX_MENSAGENS_POR_SESSAO).execute()).data or []
        except Exception as exc:  # noqa: BLE001
            logger.warning("[MemoryFabric] leitura de mensagens: %s", type(exc).__name__)
            return []
        saida = []
        for m in linhas:
            papel = str(m.get("role") or "")
            texto = str(m.get("content") or "").strip()
            if not texto:
                continue
            saida.append(MensagemSimples(
                type="human" if papel in ("user", "human") else "ai", content=texto))
        return saida

    # ------------------------------------------------------------------
    # Memoria da corretora — o escopo que nao existia
    # ------------------------------------------------------------------

    def registrar_fato_da_corretora(
        self, *, company_id: str, statement: str, categoria: str = "operacao",
        source_kind: str = "conversation", source_ref: Optional[str] = None,
        trust_tier: int = 4, confirmado_por: Optional[str] = None,
    ) -> Optional[dict]:
        """Grava um fato da EMPRESA, com dedupe e checagem de contradicao.

        Lei central 13: preferencia pessoal nao vira verdade da corretora sem
        confirmacao. Por isso o fato nasce `candidate` e so vira `active` com
        confirmacao humana ou com a segunda ocorrencia — e o CHECK
        `company_memories_promocao_exige_prova_ck` no banco garante isso mesmo
        se este codigo errar.
        """
        from .intelligence.redaction_service import contem_pii, redigir

        texto = redigir(statement, limite=800)
        if not texto or len(texto) < 12:
            return None
        if contem_pii(texto):
            # Fato da corretora e lido por outros usuarios dela. Um fato que
            # carrega dado de segurado atravessa uma fronteira que ninguem
            # pediu para atravessar.
            logger.info("[MemoryFabric] fato descartado por conter dado pessoal")
            return None

        chave = chave_de_memoria(texto)
        existente = self._fato_existente(company_id, chave)
        if existente:
            return self._reforcar_fato(existente, confirmado_por)

        conflito = self._procurar_contradicao(company_id, texto)
        linha = {
            "company_id": company_id,
            "memory_key": chave,
            "category": categoria,
            "statement": texto,
            "source_kind": source_kind,
            "source_refs": [source_ref] if source_ref else [],
            "trust_tier": int(trust_tier),
            "confidence": 0.6 if trust_tier <= 3 else 0.45,
            "status": "conflicted" if conflito else (
                "active" if confirmado_por else "candidate"),
            "confirmed_by_user_id": confirmado_por,
            "confirmed_at": _agora().isoformat() if confirmado_por else None,
        }
        try:
            r = self.db.table("company_memories").insert(linha).execute()
            criado = (r.data or [{}])[0]
        except Exception as exc:  # noqa: BLE001
            logger.warning("[MemoryFabric] fato não gravado: %s", type(exc).__name__)
            return None

        if conflito:
            logger.warning("[MemoryFabric] fato em conflito com memória existente %s",
                           str(conflito.get("id"))[:8])
        return criado

    def _fato_existente(self, company_id: str, chave: str) -> Optional[dict]:
        try:
            r = (self.db.table("company_memories")
                 .select("id, occurrences, confidence, status, statement")
                 .eq("company_id", company_id).eq("memory_key", chave)
                 .in_("status", ["candidate", "active", "conflicted"])
                 .limit(1).execute())
            return (r.data or [None])[0]
        except Exception:  # noqa: BLE001
            return None

    def _reforcar_fato(self, existente: dict, confirmado_por: Optional[str]) -> dict:
        """Segunda ocorrencia promove `candidate` para `active`."""
        n = int(existente.get("occurrences") or 1) + 1
        campos: dict[str, Any] = {
            "occurrences": n,
            "last_seen_at": _agora().isoformat(),
            "confidence": min(0.95, float(existente.get("confidence") or 0.5) + 0.15),
        }
        if existente.get("status") == "candidate" and (n >= 2 or confirmado_por):
            campos["status"] = "active"
        if confirmado_por:
            campos["confirmed_by_user_id"] = confirmado_por
            campos["confirmed_at"] = _agora().isoformat()
        try:
            self.db.table("company_memories").update(campos) \
                .eq("id", existente["id"]).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[MemoryFabric] reforço não gravado: %s", type(exc).__name__)
        return {**existente, **campos}

    def _procurar_contradicao(self, company_id: str, texto: str) -> Optional[dict]:
        try:
            ativos = (self.db.table("company_memories")
                      .select("id, statement").eq("company_id", company_id)
                      .eq("status", "active").limit(200).execute()).data or []
        except Exception:  # noqa: BLE001
            return None
        for f in ativos:
            if contradiz(texto, str(f.get("statement") or "")):
                try:
                    self.db.table("company_memories").update(
                        {"status": "conflicted"}).eq("id", f["id"]).execute()
                except Exception:  # noqa: BLE001
                    pass
                return f
        return None

    def fatos_da_corretora(self, company_id: str, *, limite: int = 40) -> list[dict]:
        try:
            r = (self.db.table("company_memories")
                 .select("id, memory_key, category, statement, confidence, status, "
                         "occurrences, last_seen_at, trust_tier")
                 .eq("company_id", company_id)
                 .in_("status", ["active", "conflicted"])
                 .order("last_seen_at", desc=True).limit(limite).execute())
            return r.data or []
        except Exception:  # noqa: BLE001
            return []

    def confirmar(self, company_id: str, memory_id: str, user_id: str,
                  *, valido: bool = True) -> bool:
        campos = ({"status": "active", "confirmed_by_user_id": user_id,
                   "confirmed_at": _agora().isoformat(), "confidence": 0.99}
                  if valido else {"status": "revoked"})
        try:
            self.db.table("company_memories").update(campos) \
                .eq("id", memory_id).eq("company_id", company_id).execute()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("[MemoryFabric] confirmação falhou: %s", type(exc).__name__)
            return False

    # ------------------------------------------------------------------
    # Aprendizado — a ponte para o Knowledge Candidate
    # ------------------------------------------------------------------

    def propor_aprendizado(self, *, company_id: str, titulo: str, texto: str,
                           origem: str, trust_tier: int = 3,
                           fontes: int = 1,
                           source_ref: Optional[str] = None) -> Optional[dict]:
        """Encaminha um aprendizado para a fila de curadoria da SPEC-052.

        Nunca publica. Nao existe caminho daqui para o RAG — e nao deve
        existir: o que entra no conhecimento global e repetido para todas as
        corretoras com cara de fonte oficial.
        """
        from .intelligence.knowledge_candidate_adapter import KnowledgeCandidateAdapter

        adaptador = KnowledgeCandidateAdapter(self.db)
        candidato = adaptador.propor(
            origem=origem, titulo=titulo, texto=texto, company_id=company_id,
            escopo="company", trust_tier=trust_tier, fontes=fontes,
            source_ref=source_ref)
        if candidato and candidato.get("id"):
            adaptador.checar_contradicao(candidato)
        return candidato

    # ------------------------------------------------------------------
    # Diagnostico — para o painel e para o relatorio
    # ------------------------------------------------------------------

    def diagnostico(self, *, company_id: Optional[str] = None) -> dict:
        """Estado real da memoria. Existe para que zero nunca mais passe despercebido.

        O defeito original ficou dois meses invisivel porque nenhuma tela
        mostrava a contagem. Agora ela e consultavel.
        """
        def _contar(tabela: str, filtro_empresa: bool = True) -> int:
            try:
                q = self.db.table(tabela).select("id", count="exact")
                if filtro_empresa and company_id:
                    q = q.eq("company_id", company_id)
                r = q.execute()
                return int(getattr(r, "count", None) or len(r.data or []))
            except Exception:  # noqa: BLE001
                return -1

        conversas = _contar("conversations")
        resumos = _contar("session_summaries")
        return {
            "conversas": conversas,
            "session_summaries": resumos,
            "user_memories": _contar("user_memories"),
            "company_memories": _contar("company_memories"),
            "knowledge_candidates": _contar("knowledge_candidates"),
            "saudavel": resumos > 0 or conversas == 0,
            "observacao": (
                "memória produzindo registros" if resumos > 0
                else "nenhum resumo de sessão gravado — verificar o laço de manutenção do worker"),
        }


async def fechar_sessoes(supabase_client: Any, *, limite: int = 10) -> dict:
    """Atalho para o laco de manutencao do Smith Worker."""
    return await MemoryFabric(supabase_client).fechar_sessoes_inativas(limite=limite)
