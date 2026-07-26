"""Findings — diagnostico com fato e inferencia separados. SPEC-059 §13.

O que este modulo recusa a fazer
--------------------------------
Nao pede ao modelo para "resumir os sinais". Se pedisse, o resumo traria
numeros — e numero produzido por modelo a partir de texto e a origem mais
comum de dado errado com aparencia de dado certo.

Aqui o Finding e montado por **composicao deterministica**: o fato vem da
evidencia, a inferencia vem de uma frase declarada pelo tipo de sinal, e o
dado faltante vem do que o detector nao conseguiu observar. O modelo, quando
entra, entra depois e so para melhorar a redacao — nunca para produzir numero.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from . import priority_service as prio
from .dedupe_service import chave_de_finding, validade_de
from .evidence_service import (EvidenceService, resumo_para_humano, tier_de,
                               tier_dominante)
from .redaction_service import redigir
from .schemas import TIERS_QUE_SUSTENTAM_FATO
from .signal_service import registrar_evento

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Narrativa por tipo de sinal
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Narrativa:
    """Os quatro blocos de §13 declarados por tipo, nao improvisados."""

    finding_type: str
    titulo: str
    porque_agora: str
    inferencia: Optional[str] = None
    dado_faltante: Optional[str] = None
    proximo_passo: str = ""
    tipo_recomendacao: Optional[str] = None


NARRATIVAS: dict[str, Narrativa] = {
    "approval_pending": Narrativa(
        finding_type="aprovacao_parada",
        titulo="Aprovações esperando por você",
        porque_agora="Enquanto a decisão não sai, o trabalho ligado a ela fica parado.",
        proximo_passo="Revisar a fila de aprovações e decidir as mais antigas.",
        tipo_recomendacao="revisar_aprovacoes",
    ),
    "work_failure": Narrativa(
        finding_type="falha_recorrente",
        titulo="Trabalhos falhando pelo mesmo motivo",
        porque_agora="Falhas repetidas com a mesma causa costumam ter uma origem única.",
        inferencia="A causa provável é comum a todas — conexão, credencial ou limite do provedor.",
        dado_faltante="Ainda não há confirmação do provedor sobre incidente.",
        proximo_passo="Investigar a causa e pausar o que depende dela até estabilizar.",
        tipo_recomendacao="investigar_falha",
    ),
    "work_stale": Narrativa(
        finding_type="trabalho_travado",
        titulo="Trabalhos sem sinal de vida",
        porque_agora="A recuperação automática não concluiu, então é preciso olhar.",
        inferencia="Pode haver dependência externa travando a execução.",
        proximo_passo="Verificar os trabalhos travados e reiniciar ou cancelar.",
        tipo_recomendacao="investigar_falha",
    ),
    "connection_health": Narrativa(
        finding_type="conexao_indisponivel",
        titulo="Conexão indisponível",
        porque_agora="O que depende dessa conexão não roda até ela voltar.",
        proximo_passo="Reconectar em Personalização → Conectores.",
        tipo_recomendacao="reconectar",
    ),
    "attendance_quality": Narrativa(
        finding_type="queda_de_qualidade",
        titulo="Qualidade do atendimento em queda",
        porque_agora="A queda aparece antes de o cliente reclamar — dá tempo de corrigir.",
        inferencia="A queda pode vir de um padrão específico de conversa, não do sistema.",
        dado_faltante="Ainda não se sabe se a queda vem de um atendente, de um canal ou de um assunto.",
        proximo_passo="Abrir a investigação de qualidade das últimas 24h.",
        tipo_recomendacao="investigar_qualidade",
    ),
    "operational_backlog": Narrativa(
        finding_type="fila_acumulada",
        titulo="Fila acumulada",
        porque_agora="Fila que cresce sem alguém olhar vira problema com o cliente.",
        proximo_passo="Abrir a fila e priorizar os itens mais antigos.",
        tipo_recomendacao="reduzir_fila",
    ),
    "budget_risk": Narrativa(
        finding_type="custo_no_limite",
        titulo="Consumo perto do limite",
        porque_agora="Dá para ajustar antes de estourar, não depois.",
        inferencia="No ritmo atual o mês fecha acima do limite configurado.",
        dado_faltante="A projeção é linear e não considera sazonalidade.",
        proximo_passo="Revisar o que mais consome e ajustar limites.",
        tipo_recomendacao="revisar_custo",
    ),
    "repeated_task": Narrativa(
        finding_type="tarefa_repetida",
        titulo="Você pede a mesma coisa toda semana",
        porque_agora="Isso pode virar automático e parar de consumir seu tempo.",
        proximo_passo="Transformar o pedido em rotina automática.",
        tipo_recomendacao="propor_automacao",
    ),
    "capability_gap": Narrativa(
        finding_type="pedido_nao_atendido",
        titulo="Um pedido seu ainda não pode ser atendido",
        porque_agora="Vale saber que o pedido foi registrado e não se perdeu.",
        dado_faltante="Ainda não existe capacidade publicada que atenda a isso.",
        proximo_passo="Ver a alternativa disponível hoje.",
    ),
    "portal_blocker": Narrativa(
        finding_type="portal_bloqueado",
        titulo="Um acesso a portal precisa de você",
        porque_agora="O portal parou esperando uma ação humana.",
        proximo_passo="Abrir o acesso pendente e destravar.",
        tipo_recomendacao="destravar_portal",
    ),
    "positive_outcome": Narrativa(
        finding_type="resultado_do_periodo",
        titulo="O que ficou pronto",
        porque_agora="Fecha o ciclo: o que foi pedido, foi entregue.",
        proximo_passo="",
    ),
    "broker_pain": Narrativa(
        finding_type="dor_declarada",
        titulo="Uma dificuldade que você mencionou",
        porque_agora="Ficou registrada para virar melhoria.",
        proximo_passo="",
    ),
    "churn_risk": Narrativa(
        finding_type="risco_relacionamento",
        titulo="Sinal de insatisfação",
        porque_agora="Vale tratar antes de virar cancelamento.",
        inferencia="A frase sugere insatisfação; não confirma intenção de sair.",
        dado_faltante="Não houve confirmação direta do corretor.",
        proximo_passo="Conversar com a corretora.",
    ),
}

NARRATIVA_PADRAO = Narrativa(
    finding_type="observacao",
    titulo="Ponto de atenção",
    porque_agora="Apareceu no período e ainda não foi tratado.",
    proximo_passo="Abrir os detalhes.",
)


# ---------------------------------------------------------------------------
# Composicao
# ---------------------------------------------------------------------------


@dataclass
class FindingComposto:
    company_id: str
    finding_type: str
    title: str
    summary: str
    why_now: str
    dedupe_key: str
    fact_statement: Optional[str] = None
    inference_statement: Optional[str] = None
    missing_data: Optional[str] = None
    next_step: Optional[str] = None
    severity: str = "medium"
    confidence: float = 0.7
    priority_score: float = 0.0
    user_id: Optional[str] = None
    valid_until: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    sinais: list[dict] = field(default_factory=list)
    tipo_recomendacao: Optional[str] = None


def compor(sinais: list[dict], evidencias_por_sinal: dict[str, list[dict]],
           *, company_id: str) -> Optional[FindingComposto]:
    """Monta UM Finding a partir de sinais do mesmo assunto. Puro.

    A regra que faz este codigo valer: o `fact_statement` **so** e preenchido
    com evidencia de Tier 0–3. Quando so ha declaracao (Tier 4) ou inferencia
    (Tier 5), o bloco de fato fica vazio e a frase vai para inferencia — e o
    CHECK do banco recusa inferencia sem fato, entao o Finding simplesmente
    nao nasce. E o comportamento certo: nao ha diagnostico ali, ha um relato.
    """
    if not sinais:
        return None

    principal = max(sinais, key=lambda s: float(s.get("priority_score") or 0))
    tipo = str(principal.get("signal_type") or "")
    narrativa = NARRATIVAS.get(tipo, NARRATIVA_PADRAO)

    todas_evidencias: list[dict] = []
    for s in sinais:
        todas_evidencias.extend(evidencias_por_sinal.get(str(s.get("id")), []))

    factuais = [e for e in todas_evidencias
                if tier_de(e) in TIERS_QUE_SUSTENTAM_FATO]
    fato = resumo_para_humano(factuais) or None
    if not fato:
        # §13: sem evidencia factual nao ha diagnostico. Nao se promove
        # declaracao a fato para "ter alguma coisa" no briefing.
        return None

    ocorrencias = sum(int(s.get("occurrence_count") or 1) for s in sinais)
    severidade = _maior_severidade(sinais)
    confianca = max(float(s.get("confidence") or 0) for s in sinais)
    tier = tier_dominante(todas_evidencias)

    dim = prio.Dimensoes(
        impacto=_media(sinais, "impact_score", 50.0),
        urgencia=_media(sinais, "urgency_score", 40.0),
        confianca=confianca * 100.0,
        actionability=_media(sinais, "actionability_score", 50.0),
        recorrencia=prio.recorrencia_por_contagem(ocorrencias),
        freshness=_media(sinais, "freshness_score", 100.0),
    )
    penalidades: list[str] = []
    if tier >= 4:
        penalidades.append("evidencia_insuficiente")
    if len(factuais) < 1:
        penalidades.append("evidencia_insuficiente")
    score = prio.calcular(dim, penalidades)

    resumo = str(principal.get("summary_redacted") or narrativa.titulo)
    if len(sinais) > 1:
        resumo = f"{resumo} (+{len(sinais) - 1} relacionado(s) no mesmo assunto)"

    return FindingComposto(
        company_id=company_id,
        finding_type=narrativa.finding_type,
        title=narrativa.titulo,
        summary=redigir(resumo, limite=600),
        why_now=narrativa.porque_agora,
        dedupe_key=chave_de_finding(
            company_id=company_id, finding_type=narrativa.finding_type,
            subject=f"{principal.get('subject_type')}:{principal.get('subject_id') or '-'}"),
        fact_statement=fato,
        inference_statement=narrativa.inferencia,
        missing_data=narrativa.dado_faltante,
        next_step=narrativa.proximo_passo or None,
        severity=severidade,
        confidence=round(confianca, 3),
        priority_score=score,
        user_id=principal.get("user_id"),
        valid_until=validade_de(tipo).isoformat(),
        metadata={
            "signal_type": tipo,
            "ocorrencias": ocorrencias,
            "trust_tier": tier,
            "explicacao": prio.resumo_explicavel(dim, penalidades, score),
            "subject": f"{principal.get('subject_type')}:{principal.get('subject_id') or '-'}",
            **{k: v for k, v in (principal.get("metadata") or {}).items()
               if k in ("quantidade", "ids", "run_ids", "conversation_ids",
                        "artifact_ids", "vezes", "destaques", "conexao",
                        "gasto_usd", "limite_usd", "projecao_usd", "assinatura",
                        "recent_avg", "baseline_avg", "drop", "samples")},
        },
        sinais=sinais,
        tipo_recomendacao=narrativa.tipo_recomendacao,
    )


def _media(sinais: list[dict], campo: str, padrao: float) -> float:
    valores = [float(s[campo]) for s in sinais if s.get(campo) is not None]
    return round(sum(valores) / len(valores), 2) if valores else padrao


def _maior_severidade(sinais: list[dict]) -> str:
    ordem = ["info", "low", "medium", "high", "critical"]
    maior = "info"
    for s in sinais:
        atual = str(s.get("severity") or "info")
        if atual in ordem and ordem.index(atual) > ordem.index(maior):
            maior = atual
    return maior


# ---------------------------------------------------------------------------
# Servico
# ---------------------------------------------------------------------------


class FindingEngine:
    def __init__(self, supabase_client: Any):
        self.db = getattr(supabase_client, "client", supabase_client)
        self.evidencias = EvidenceService(supabase_client)

    def consolidar(self, company_id: str, *, limite_sinais: int = 200) -> list[dict]:
        """Agrupa sinais vivos por assunto e grava/atualiza os Findings."""
        from .dedupe_service import agrupar_por_assunto
        from .signal_service import SignalService

        sinais = SignalService(self.db).ativos(company_id, limite=limite_sinais)
        if not sinais:
            return []

        evidencias = self.evidencias.dos_sinais(
            company_id, [str(s["id"]) for s in sinais])

        criados: list[dict] = []
        for _, grupo in agrupar_por_assunto(sinais).items():
            composto = compor(grupo, evidencias, company_id=company_id)
            if composto is None:
                continue
            linha = self._gravar(composto)
            if linha:
                criados.append(linha)
        return criados

    def _gravar(self, f: FindingComposto) -> Optional[dict]:
        existente = self._vivo(f.company_id, f.dedupe_key)
        campos = {
            "company_id": f.company_id,
            "user_id": f.user_id,
            "finding_type": f.finding_type,
            "title": f.title,
            "summary": f.summary,
            "fact_statement": f.fact_statement,
            "inference_statement": f.inference_statement,
            "missing_data": f.missing_data,
            "next_step": f.next_step,
            "severity": f.severity,
            "confidence": f.confidence,
            "priority_score": f.priority_score,
            "why_now": f.why_now,
            "valid_until": f.valid_until,
            "dedupe_key": f.dedupe_key,
            "metadata": f.metadata,
        }
        try:
            if existente:
                # Um Finding reconhecido, adiado ou dispensado NAO volta para
                # 'active' so porque o sinal continua existindo. Isso e a
                # diferenca entre "o problema persiste" e "o corretor precisa
                # ser incomodado de novo" — quem decide a segunda e o cooldown.
                self.db.table("intelligence_findings").update({
                    "summary": campos["summary"],
                    "fact_statement": campos["fact_statement"],
                    "severity": campos["severity"],
                    "confidence": campos["confidence"],
                    "priority_score": campos["priority_score"],
                    "valid_until": campos["valid_until"],
                    "metadata": campos["metadata"],
                }).eq("id", existente["id"]).execute()
                linha = {**existente, **campos}
            else:
                r = self.db.table("intelligence_findings").insert(
                    {**campos, "status": "active"}).execute()
                linha = (r.data or [{}])[0]
                registrar_evento(self.db, company_id=f.company_id,
                                 tipo="finding.created", subject_type="finding",
                                 subject_id=linha.get("id"), mensagem=f.title,
                                 detalhe={"finding_type": f.finding_type,
                                          "priority_score": f.priority_score})
        except Exception as exc:  # noqa: BLE001
            logger.error("[FindingEngine] gravacao falhou: %s", type(exc).__name__)
            return None

        self._ligar_sinais(linha.get("id"), f)
        linha["_tipo_recomendacao"] = f.tipo_recomendacao
        return linha

    def _vivo(self, company_id: str, dedupe_key: str) -> Optional[dict]:
        try:
            r = (self.db.table("intelligence_findings")
                 .select("id, status, priority_score, delivery_count, last_delivered_at")
                 .eq("company_id", company_id).eq("dedupe_key", dedupe_key)
                 .in_("status", ["draft", "active", "acknowledged", "snoozed", "conflicted"])
                 .limit(1).execute())
            return (r.data or [None])[0]
        except Exception:  # noqa: BLE001
            return None

    def _ligar_sinais(self, finding_id: Optional[str], f: FindingComposto) -> None:
        if not finding_id:
            return
        linhas = []
        principal = max(f.sinais, key=lambda s: float(s.get("priority_score") or 0))
        for s in f.sinais:
            linhas.append({
                "finding_id": finding_id, "signal_id": s["id"],
                "company_id": f.company_id,
                "role": "primary" if s["id"] == principal["id"] else "supporting",
                "weight": 1.0,
            })
        try:
            self.db.table("intelligence_finding_signals").upsert(
                linhas, on_conflict="finding_id,signal_id").execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[FindingEngine] vínculo sinal/finding: %s", type(exc).__name__)

    # ------------------------------------------------------------------

    def ativos(self, company_id: str, *, user_id: Optional[str] = None,
               limite: int = 50) -> list[dict]:
        try:
            q = (self.db.table("intelligence_findings").select("*")
                 .eq("company_id", company_id)
                 .in_("status", ["active", "acknowledged", "conflicted"]))
            r = q.order("priority_score", desc=True).limit(limite).execute()
        except Exception as exc:  # noqa: BLE001
            logger.error("[FindingEngine] leitura falhou: %s", type(exc).__name__)
            return []
        agora = datetime.now(timezone.utc)
        saida = []
        for f in r.data or []:
            if f.get("snoozed_until"):
                try:
                    ate = datetime.fromisoformat(str(f["snoozed_until"]).replace("Z", "+00:00"))
                    if ate.tzinfo is None:
                        ate = ate.replace(tzinfo=timezone.utc)
                    if ate > agora:
                        continue
                except Exception:  # noqa: BLE001
                    pass
            # Finding pessoal so aparece para o dono. Company-level aparece
            # para todos com acesso — a permissao fina e da SPEC-061.
            if user_id and f.get("user_id") and str(f["user_id"]) != str(user_id):
                continue
            saida.append(f)
        return saida

    def responder(self, company_id: str, finding_id: str, acao: str, *,
                  user_id: Optional[str] = None, dias_adiar: int = 1) -> bool:
        """acknowledge · snooze · dismiss · resolve."""
        agora = datetime.now(timezone.utc)
        campos: dict[str, Any] = {}
        if acao == "acknowledge":
            campos = {"status": "acknowledged", "acknowledged_at": agora.isoformat(),
                      "owner_user_id": user_id}
        elif acao == "snooze":
            campos = {"status": "snoozed",
                      "snoozed_until": (agora + timedelta(days=max(1, dias_adiar))).isoformat()}
        elif acao == "dismiss":
            campos = {"status": "dismissed", "dismissed_at": agora.isoformat()}
        elif acao == "resolve":
            campos = {"status": "resolved", "resolved_at": agora.isoformat()}
        else:
            return False
        try:
            self.db.table("intelligence_findings").update(campos) \
                .eq("id", finding_id).eq("company_id", company_id).execute()
        except Exception as exc:  # noqa: BLE001
            logger.error("[FindingEngine] resposta falhou: %s", type(exc).__name__)
            return False
        registrar_evento(self.db, company_id=company_id,
                         tipo=f"finding.{acao}", subject_type="finding",
                         subject_id=finding_id, actor_kind="user", actor_id=user_id,
                         mensagem=_frase_de_resposta(acao))
        return True

    def expirar_vencidos(self, *, limite: int = 300) -> int:
        try:
            agora = datetime.now(timezone.utc).isoformat()
            r = (self.db.table("intelligence_findings").select("id")
                 .in_("status", ["active", "acknowledged", "snoozed"])
                 .lt("valid_until", agora).limit(limite).execute())
            ids = [x["id"] for x in (r.data or [])]
            if not ids:
                return 0
            self.db.table("intelligence_findings").update(
                {"status": "expired"}).in_("id", ids).execute()
            return len(ids)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[FindingEngine] expiracao falhou: %s", type(exc).__name__)
            return 0


def _frase_de_resposta(acao: str) -> str:
    return {
        "acknowledge": "O corretor marcou que viu este ponto.",
        "snooze": "O corretor pediu para ser lembrado depois.",
        "dismiss": "O corretor dispensou este ponto.",
        "resolve": "O ponto foi marcado como resolvido.",
    }.get(acao, acao)
