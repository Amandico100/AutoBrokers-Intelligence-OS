"""Garimpo v3 — a voz do corretor. SPEC-059 §18.

O que muda da v1/v2 para a v3
-----------------------------
A regex deterministica de `broker_insights.py` **e preservada** e continua
sendo a camada A: ela custa zero e pega o obvio. A camada LLM tambem
continua, com o mesmo teto de custo.

O que muda e o destino e a fronteira:

* o resultado vira `intelligence_signal` (Tier 4 — "o corretor declarou",
  nunca "isto e verdade");
* pedido de automacao vai para a **Auxiliary Factory** da SPEC-058, que
  decide o formato — em vez de virar um texto solto;
* a citacao literal fica **dentro do tenant**; o que sobe para o agregado
  global e resumo redigido e anonimizado (§18.5);
* `broker_insights` continua sendo escrita como PROJECAO de compatibilidade,
  mas deixa de ser autoridade (§10.15).

O que o Garimpo continua nao podendo fazer (§18.6): publicar template global,
criar Skill, alterar RAG, alterar prompt de producao, enviar campanha ou
executar qualquer efeito.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from .detectors.automacao import sinal_de_voz
from .redaction_service import redigir, resumo_seguro
from .signal_service import SignalService, registrar_evento

logger = logging.getLogger(__name__)

# Traducao dos `kind` historicos do Garimpo para a taxonomia da SPEC-059 §9.
# Manter os nomes antigos e o que permite reaproveitar a regex ja calibrada.
KIND_PARA_SINAL: dict[str, str] = {
    "dor": "broker_pain",
    "desejo": "broker_desire",
    "pedido_feature": "feature_request",
    "necessidade": "broker_desire",
    "duvida_seguros": "knowledge_gap",
    "risco_churn": "churn_risk",
    "elogio": "positive_outcome",
}

# Os que viram pedido de automacao na Factory. Elogio e duvida nao entram:
# elogio nao e pedido, e duvida de seguros e conhecimento, nao automacao.
KINDS_QUE_VIRAM_PEDIDO = ("desejo", "pedido_feature", "necessidade")

MIN_CARACTERES = 15


def classificar(texto: str) -> list[dict]:
    """Camada A — reaproveita a regex de `broker_insights`. Pura.

    Importada em vez de recopiada: a lista de padroes ja passou por
    calibragem real e duplica-la criaria duas verdades sobre o que e uma dor.
    """
    from ..broker_insights import extract_candidates

    return extract_candidates([{"role": "user", "content": texto or ""}])


class GarimpoV3:
    def __init__(self, supabase_client: Any):
        self.db = getattr(supabase_client, "client", supabase_client)
        self.sinais = SignalService(supabase_client)

    # ------------------------------------------------------------------

    def minerar_conversa(self, *, company_id: str, conversation_id: str,
                         user_id: Optional[str] = None) -> dict:
        """Minera UMA conversa. Devolve o que foi criado."""
        try:
            msgs = (self.db.table("messages").select("role, content")
                    .eq("conversation_id", conversation_id)
                    .order("created_at", desc=True).limit(200).execute()).data or []
        except Exception as exc:  # noqa: BLE001
            logger.warning("[GarimpoV3] leitura de mensagens: %s", type(exc).__name__)
            return {"sinais": 0, "pedidos": 0}

        criados, pedidos = 0, 0
        vistos: set[str] = set()
        for m in reversed(msgs):
            if str(m.get("role") or "") != "user":
                continue
            texto = str(m.get("content") or "").strip()
            if len(texto) < MIN_CARACTERES:
                continue
            for c in classificar(texto):
                kind = str(c.get("kind") or "")
                tipo = KIND_PARA_SINAL.get(kind)
                if not tipo:
                    continue
                chave = f"{kind}:{c.get('quote','')[:60].lower()}"
                if chave in vistos:
                    continue
                vistos.add(chave)

                rascunho = sinal_de_voz(
                    company_id, tipo=tipo, texto=str(c.get("quote") or texto),
                    conversa_id=conversation_id, user_id=user_id)
                if self.sinais.registrar(rascunho):
                    criados += 1
                    self._projetar_legado(company_id, conversation_id, user_id, c)
                if kind in KINDS_QUE_VIRAM_PEDIDO:
                    if self._encaminhar_para_factory(company_id, texto, user_id):
                        pedidos += 1
        return {"sinais": criados, "pedidos": pedidos}

    def minerar_recentes(self, *, horas: int = 24, limite: int = 300) -> dict:
        """Varredura periodica. Espelho de seguradora fica de fora (§18.2)."""
        corte = (datetime.now(timezone.utc) - timedelta(hours=horas)).isoformat()
        try:
            convs = (self.db.table("conversations")
                     .select("id, company_id, user_id, session_id")
                     .gte("last_message_at", corte)
                     .order("last_message_at", desc=True).limit(limite).execute()).data or []
        except Exception as exc:  # noqa: BLE001
            logger.warning("[GarimpoV3] varredura falhou: %s", type(exc).__name__)
            return {"conversas": 0, "sinais": 0, "pedidos": 0}

        total = {"conversas": 0, "sinais": 0, "pedidos": 0}
        for c in convs:
            # A conversa com a SEGURADORA nao e a voz do corretor. Misturar as
            # duas encheria o funil de demanda com o que a seguradora escreve.
            if str(c.get("session_id") or "").startswith("dispatch:"):
                continue
            r = self.minerar_conversa(
                company_id=str(c["company_id"]), conversation_id=str(c["id"]),
                user_id=c.get("user_id"))
            total["conversas"] += 1
            total["sinais"] += r["sinais"]
            total["pedidos"] += r["pedidos"]
        if total["sinais"]:
            logger.info("[GarimpoV3] %s sinal(is) de voz em %s conversa(s)",
                        total["sinais"], total["conversas"])
        return total

    # ------------------------------------------------------------------

    def _encaminhar_para_factory(self, company_id: str, texto: str,
                                 user_id: Optional[str]) -> bool:
        """Pedido de automacao vai para a Factory da SPEC-058.

        A Factory decide o formato (trabalho unico, Rotina, Auxiliar) e
        registra a lacuna quando nao da. Recriar essa decisao aqui seria a
        segunda Factory que o CLAUDE.md §5 proibe.
        """
        try:
            from ..auxiliaries.factory import AuxiliaryFactory

            AuxiliaryFactory(self.db).avaliar(
                company_id=company_id, texto=texto, user_id=user_id,
                source="garimpo")
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("[GarimpoV3] encaminhamento à Factory: %s", type(exc).__name__)
            return False

    def _projetar_legado(self, company_id: str, conversation_id: str,
                         user_id: Optional[str], c: dict) -> None:
        """Espelha em `broker_insights` para nao apagar superficie existente.

        §10.15: a tabela vira PROJECAO, nao autoridade. A escrita continua
        para que painel e relatorio historicos nao fiquem vazios durante a
        transicao — e falhar aqui nunca pode derrubar o sinal, que e o que
        vale.
        """
        try:
            self.db.table("broker_insights").insert({
                "company_id": company_id,
                "conversation_id": conversation_id,
                "user_id": str(user_id) if user_id else None,
                "kind": c.get("kind"),
                "summary": resumo_seguro(str(c.get("summary") or ""), 160),
                "quote": redigir(str(c.get("quote") or ""), limite=220),
                "source": "garimpo_v3",
            }).execute()
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------

    def registrar_feedback_explicito(self, *, company_id: str, texto: str,
                                     user_id: Optional[str] = None,
                                     origem: str = "feedback") -> Optional[dict]:
        """Feedback dado de proposito pelo corretor. §18.2.

        Entra com confianca maior que o minerado: ele nao foi inferido de uma
        conversa, foi escrito para ser lido.
        """
        rascunho = sinal_de_voz(company_id, tipo="broker_desire", texto=texto,
                                user_id=user_id, rule_key="garimpo.feedback",
                                rule_version="3.0.0")
        rascunho.confidence = 0.95
        rascunho.source_type = origem
        criado = self.sinais.registrar(rascunho)
        if criado:
            registrar_evento(self.db, company_id=company_id,
                             tipo="broker.request_detected", subject_type="signal",
                             subject_id=criado.get("id"),
                             mensagem="O corretor deixou um pedido explícito.",
                             actor_kind="user", actor_id=user_id)
        return criado

    def voz_do_periodo(self, company_id: str, *, dias: int = 30) -> dict:
        """O que a corretora andou dizendo. Agregado, para o painel dela."""
        desde = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
        try:
            r = (self.db.table("intelligence_signals")
                 .select("signal_type, summary_redacted, occurrence_count, created_at")
                 .eq("company_id", company_id).eq("source_type", "garimpo")
                 .gte("created_at", desde).limit(300).execute()).data or []
        except Exception:  # noqa: BLE001
            return {"total": 0, "por_tipo": {}, "itens": []}
        por_tipo: dict[str, int] = {}
        for s in r:
            por_tipo[s["signal_type"]] = por_tipo.get(s["signal_type"], 0) + 1
        return {"total": len(r), "por_tipo": por_tipo,
                "itens": sorted(r, key=lambda x: -(x.get("occurrence_count") or 1))[:20]}
