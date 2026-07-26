"""Recomendacoes governadas. SPEC-059 §14, §22.

A regra que define este modulo e §14.2: **so mostrar "Resolver" quando existe
caminho real**. Botao que promete resolver e nao resolve custa mais caro que
nenhum botao — o corretor clica, nao acontece nada, e ele para de clicar em
tudo.

Por isso `montar_opcoes` verifica o caminho antes de oferecer, e quando o
caminho nao existe a recomendacao diz o que falta em vez de fingir.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from .dedupe_service import chave_de_finding
from .redaction_service import redigir
from .signal_service import registrar_evento

logger = logging.getLogger(__name__)

VALIDADE_PADRAO_DIAS = 7


@dataclass
class Opcao:
    """Uma opcao de acao apresentada ao corretor — §14.1."""

    key: str
    label: str
    kind: str                 # abrir | conversar | work_run | rotina | auxiliar | aprovar | artefato
    destino: Optional[str] = None
    payload: dict = field(default_factory=dict)
    requer_aprovacao: bool = False
    executavel: bool = False  # o AutoBrokers consegue fazer sozinho?

    def como_dict(self) -> dict:
        return {"key": self.key, "label": self.label, "kind": self.kind,
                "destino": self.destino, "payload": self.payload,
                "requer_aprovacao": self.requer_aprovacao,
                "executavel": self.executavel}


# As opcoes que SEMPRE existem, porque nao dependem de capacidade nenhuma.
def _opcoes_basicas(finding_id: str) -> list[Opcao]:
    return [
        Opcao("detalhes", "Ver detalhes", "abrir", destino=f"/dashboard/briefing?finding={finding_id}"),
        Opcao("explicar", "Por que estou vendo isso?", "conversar",
              payload={"pergunta": "Por que você está me mostrando isso?"}),
        Opcao("adiar", "Me lembre amanhã", "abrir", payload={"acao": "snooze", "dias": 1}),
        Opcao("dispensar", "Não é relevante", "abrir", payload={"acao": "not_relevant"}),
    ]


# Caminho de execucao por tipo de recomendacao. `workflow` None significa que
# nao ha execucao automatica — so navegacao.
CAMINHOS: dict[str, dict] = {
    "revisar_aprovacoes": {
        "label": "Revisar aprovações", "kind": "abrir",
        "destino": "/dashboard/auxiliares/execucoes", "workflow": None,
        "risco": "low",
    },
    "investigar_falha": {
        "label": "Investigar as falhas", "kind": "work_run",
        "workflow": "intelligence.investigate_failures", "risco": "low",
    },
    "investigar_qualidade": {
        "label": "Investigar a queda de qualidade", "kind": "work_run",
        "workflow": "intelligence.investigate_quality", "risco": "low",
    },
    "reconectar": {
        "label": "Reconectar agora", "kind": "abrir",
        "destino": "/dashboard/personalizacao?aba=conectores", "workflow": None,
        "risco": "low",
    },
    "reduzir_fila": {
        "label": "Abrir a fila", "kind": "abrir",
        "destino": "/dashboard/atendimentos", "workflow": None, "risco": "low",
    },
    "revisar_custo": {
        "label": "Ver o que mais consome", "kind": "abrir",
        "destino": "/dashboard/configuracoes?aba=uso", "workflow": None, "risco": "low",
    },
    "propor_automacao": {
        "label": "Deixar isso automático", "kind": "rotina",
        "workflow": None, "risco": "low",
    },
    "destravar_portal": {
        "label": "Destravar o acesso", "kind": "abrir",
        "destino": "/dashboard/auxiliares/execucoes", "workflow": None, "risco": "medium",
    },
}


def montar_opcoes(finding: dict, tipo_recomendacao: Optional[str], *,
                  caminho_disponivel: bool = True,
                  o_que_falta: Optional[str] = None) -> tuple[list[Opcao], Optional[str]]:
    """(opcoes, chave recomendada). Puro.

    Quando `caminho_disponivel` e falso, a acao principal NAO entra na lista.
    §14.2 e explicito: sem Skill publicada, capability, conexao, dado minimo,
    orcamento e policy, nao ha CTA de resolver — ha explicacao do que falta.
    """
    finding_id = str(finding.get("id") or "")
    opcoes = list(_opcoes_basicas(finding_id))

    caminho = CAMINHOS.get(tipo_recomendacao or "")
    if not caminho:
        return opcoes, None

    if not caminho_disponivel:
        opcoes.insert(0, Opcao(
            "indisponivel",
            f"Ainda não dá para fazer isso automaticamente{(': ' + o_que_falta) if o_que_falta else ''}",
            "abrir", executavel=False))
        return opcoes, None

    principal = Opcao(
        key=tipo_recomendacao or "resolver",
        label=caminho["label"],
        kind=caminho["kind"],
        destino=caminho.get("destino"),
        payload={"workflow_key": caminho["workflow"]} if caminho.get("workflow") else {},
        requer_aprovacao=caminho.get("risco") in ("high", "critical"),
        executavel=bool(caminho.get("workflow")) or caminho["kind"] == "abrir",
    )
    opcoes.insert(0, principal)
    return opcoes, principal.key


def plano_de_medicao(tipo_recomendacao: Optional[str], finding: dict) -> dict:
    """§20.2 — o que sera medido, definido ANTES de executar.

    Definir depois e o que produz "melhorou" sem baseline. Aqui a linha de
    base e capturada no momento em que a recomendacao nasce, junto com a
    janela e o metodo.
    """
    meta = finding.get("metadata") or {}
    base = {
        "metrica": None, "baseline": None, "fonte": None,
        "janela_horas": 72, "metodo": "comparação direta antes/depois",
        "limitacoes": "medição automática; sem confirmação humana o resultado é inconclusivo",
        "automation_level": "automated",
    }
    if tipo_recomendacao == "revisar_aprovacoes":
        return {**base, "metrica": "aprovacoes_pendentes",
                "baseline": meta.get("quantidade"), "fonte": "approval_requests",
                "janela_horas": 48}
    if tipo_recomendacao in ("investigar_falha",):
        return {**base, "metrica": "falhas_na_janela",
                "baseline": meta.get("quantidade"), "fonte": "work_runs"}
    if tipo_recomendacao == "reduzir_fila":
        return {**base, "metrica": "atendimentos_parados",
                "baseline": meta.get("quantidade"), "fonte": "conversations"}
    if tipo_recomendacao == "reconectar":
        return {**base, "metrica": "conexao_saudavel", "baseline": 0,
                "fonte": "tenant_connections", "janela_horas": 24}
    if tipo_recomendacao == "investigar_qualidade":
        return {**base, "metrica": "nota_media_24h",
                "baseline": meta.get("recent_avg"), "fonte": "conversation_scorecards",
                "janela_horas": 168}
    if tipo_recomendacao == "propor_automacao":
        return {**base, "metrica": "pedidos_manuais_repetidos",
                "baseline": meta.get("vezes"), "fonte": "auxiliary_requests",
                "janela_horas": 336,
                "limitacoes": "tempo economizado é estimativa, nunca fato financeiro",
                "automation_level": "estimated"}
    return base


class RecommendationService:
    def __init__(self, supabase_client: Any):
        self.db = getattr(supabase_client, "client", supabase_client)

    # ------------------------------------------------------------------

    def a_partir_do_finding(self, finding: dict, *,
                            tipo_recomendacao: Optional[str] = None) -> Optional[dict]:
        """Cria a recomendacao de um Finding. Idempotente por dedupe."""
        tipo = tipo_recomendacao or finding.get("_tipo_recomendacao")
        if not tipo:
            return None  # nem todo Finding merece recomendacao

        company_id = str(finding["company_id"])
        disponivel, falta = self._caminho_disponivel(company_id, tipo)
        opcoes, recomendada = montar_opcoes(finding, tipo,
                                            caminho_disponivel=disponivel,
                                            o_que_falta=falta)
        caminho = CAMINHOS.get(tipo) or {}
        risco = str(caminho.get("risco") or "low")

        dedupe = chave_de_finding(
            company_id=company_id, finding_type=f"rec:{tipo}",
            subject=str(finding.get("dedupe_key") or finding.get("id")))

        existente = self._viva(company_id, dedupe)
        if existente:
            return existente

        linha = {
            "company_id": company_id,
            "user_id": finding.get("user_id"),
            "finding_id": finding.get("id"),
            "recommendation_type": tipo,
            "title": redigir(str(finding.get("title") or "Recomendação"), limite=200),
            "summary": redigir(str(finding.get("summary") or ""), limite=600),
            "rationale": self._racional(finding, disponivel, falta),
            "confidence": float(finding.get("confidence") or 0.7),
            "risk_level": risco,
            "priority_score": float(finding.get("priority_score") or 0),
            "status": "eligible" if disponivel else "draft",
            "action_options": [o.como_dict() for o in opcoes],
            "recommended_action_key": recomendada,
            # §14.3 — risco alto nasce exigindo aprovacao. O CHECK do banco
            # recusaria o contrario, e isso e proposital: a garantia mora no
            # schema, nao na disciplina de quem escreve o servico.
            "approval_required": risco in ("high", "critical"),
            "measurement_plan": plano_de_medicao(tipo, finding),
            "dedupe_key": dedupe,
            "expires_at": (datetime.now(timezone.utc)
                           + timedelta(days=VALIDADE_PADRAO_DIAS)).isoformat(),
        }
        try:
            r = self.db.table("recommendations").insert(linha).execute()
            criada = (r.data or [{}])[0]
        except Exception as exc:  # noqa: BLE001
            if "duplicate" in str(exc).lower() or "unique" in str(exc).lower():
                return self._viva(company_id, dedupe)
            logger.error("[Recommendation] criacao falhou: %s", type(exc).__name__)
            return None

        registrar_evento(self.db, company_id=company_id,
                         tipo="recommendation.created", subject_type="recommendation",
                         subject_id=criada.get("id"), mensagem=linha["title"],
                         detalhe={"tipo": tipo, "executavel": disponivel})
        return criada

    def _racional(self, finding: dict, disponivel: bool, falta: Optional[str]) -> str:
        """As 10 perguntas de §14 respondidas em texto, sem numero novo.

        Todo numero que aparece aqui vem de campo ja gravado no Finding. O
        racional NUNCA calcula nada — se calculasse, existiriam dois numeros
        para o mesmo fato e um deles estaria errado em algum momento.
        """
        partes = []
        if finding.get("fact_statement"):
            partes.append(f"O que aconteceu: {finding['fact_statement']}")
        partes.append(f"Por que importa agora: {finding.get('why_now') or '—'}")
        if finding.get("inference_statement"):
            partes.append(f"Leitura (não confirmada): {finding['inference_statement']}")
        if finding.get("missing_data"):
            partes.append(f"O que ainda não se sabe: {finding['missing_data']}")
        if not disponivel and falta:
            partes.append(f"O AutoBrokers ainda não consegue resolver sozinho: {falta}")
        return redigir("\n".join(partes), limite=1500)

    def _caminho_disponivel(self, company_id: str,
                            tipo: str) -> tuple[bool, Optional[str]]:
        """§14.2 — existe caminho real para esta acao nesta corretora?

        Navegacao sempre existe. Execucao automatica exige workflow registrado
        no Work OS — e a verificacao e feita contra o registro real, nao
        contra uma lista de intencao.
        """
        caminho = CAMINHOS.get(tipo)
        if not caminho:
            return False, "não há caminho definido para esta ação"
        if caminho.get("kind") == "abrir":
            return True, None
        workflow = caminho.get("workflow")
        if not workflow:
            return True, None
        try:
            from ..work.workflows import resolver_workflow

            if resolver_workflow(workflow) is None:
                return False, "a rotina de investigação ainda não está publicada"
        except Exception:  # noqa: BLE001
            return False, "o motor de execução não está disponível agora"
        return True, None

    def _viva(self, company_id: str, dedupe_key: str) -> Optional[dict]:
        try:
            r = (self.db.table("recommendations").select("*")
                 .eq("company_id", company_id).eq("dedupe_key", dedupe_key)
                 .in_("status", ["draft", "eligible", "delivered", "viewed",
                                 "accepted", "executing"])
                 .limit(1).execute())
            return (r.data or [None])[0]
        except Exception:  # noqa: BLE001
            return None

    # ------------------------------------------------------------------

    def elegiveis(self, company_id: str, *, user_id: Optional[str] = None,
                  limite: int = 30) -> list[dict]:
        try:
            r = (self.db.table("recommendations").select("*")
                 .eq("company_id", company_id)
                 .in_("status", ["eligible", "delivered", "viewed"])
                 .order("priority_score", desc=True).limit(limite).execute())
        except Exception as exc:  # noqa: BLE001
            logger.error("[Recommendation] leitura falhou: %s", type(exc).__name__)
            return []
        agora = datetime.now(timezone.utc)
        saida = []
        for rec in r.data or []:
            if rec.get("expires_at"):
                try:
                    ate = datetime.fromisoformat(str(rec["expires_at"]).replace("Z", "+00:00"))
                    if (ate if ate.tzinfo else ate.replace(tzinfo=timezone.utc)) <= agora:
                        continue
                except Exception:  # noqa: BLE001
                    pass
            if user_id and rec.get("user_id") and str(rec["user_id"]) != str(user_id):
                continue
            saida.append(rec)
        return saida

    def marcar_entregue(self, company_id: str, ids: list[str]) -> None:
        if not ids:
            return
        try:
            self.db.table("recommendations").update({
                "status": "delivered",
                "delivered_at": datetime.now(timezone.utc).isoformat(),
            }).eq("company_id", company_id).in_("id", ids) \
                .in_("status", ["eligible"]).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Recommendation] marcacao de entrega falhou: %s",
                           type(exc).__name__)

    def expirar_vencidas(self, *, limite: int = 300) -> int:
        try:
            agora = datetime.now(timezone.utc).isoformat()
            r = (self.db.table("recommendations").select("id")
                 .in_("status", ["draft", "eligible", "delivered", "viewed"])
                 .lt("expires_at", agora).limit(limite).execute())
            ids = [x["id"] for x in (r.data or [])]
            if not ids:
                return 0
            self.db.table("recommendations").update({"status": "expired"}) \
                .in_("id", ids).execute()
            return len(ids)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Recommendation] expiracao falhou: %s", type(exc).__name__)
            return 0
