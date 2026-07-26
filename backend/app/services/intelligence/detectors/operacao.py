"""Detectores de operacao. SPEC-059 §23.1, §23.2, §23.3, §23.7, §23.9.

Todos deterministicos e Tier 0/1: leem estado persistido, contam e comparam
com limiar. Nenhum consulta modelo — §31.5 proibe usar LLM onde uma regra
resolve, e todos estes sao contagem e prazo.
"""

from __future__ import annotations

import logging
from typing import Any

from .. import priority_service as prio
from ..dedupe_service import chave_de_sinal
from ..schemas import (TIER_DADO_VIVO, TIER_EVENTO_SISTEMA, SignalDraft,
                       evidencia)
from . import ContextoDeDeteccao, horas_desde, plural, registrar

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# §23.1 — aprovacao parada
# ---------------------------------------------------------------------------


def analisar_aprovacoes(pendentes: list[dict], agora, *,
                        horas_minimas: float = 24.0) -> list[dict]:
    """Puro: quais aprovacoes passaram da janela e ainda sao validas.

    Aprovacao ja expirada NAO entra. Cobrar decisao sobre algo que perdeu a
    validade gasta a atencao do corretor num item que nao tem mais acao —
    e ensina que a fila de aprovacoes tem lixo.
    """
    saida = []
    for a in pendentes or []:
        idade = horas_desde(a.get("requested_at") or a.get("created_at"), agora)
        if idade is None or idade < horas_minimas:
            continue
        restantes = None
        if a.get("expires_at"):
            h = horas_desde(a["expires_at"], agora)
            restantes = None if h is None else -h
            if restantes is not None and restantes <= 0:
                continue  # ja expirou: nao e mais decisao pendente
        saida.append({**a, "idade_horas": round(idade, 1),
                      "horas_restantes": restantes})
    return sorted(saida, key=lambda x: -(x["idade_horas"]))


@registrar("operacao.aprovacao_parada")
def aprovacao_parada(ctx: ContextoDeDeteccao) -> list[SignalDraft]:
    horas = float(ctx.cfg("horas_minimas", 24))
    try:
        r = (ctx.db.table("approval_requests")
             .select("id, status, action_type, risk_level, requested_at, "
                     "created_at, expires_at, work_run_id, subject_type")
             .eq("company_id", ctx.company_id).eq("status", "pending")
             .limit(200).execute())
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Detector] aprovacoes: %s", type(exc).__name__)
        return []

    paradas = analisar_aprovacoes(r.data or [], ctx.agora, horas_minimas=horas)
    if not paradas:
        return []

    mais_antiga = paradas[0]
    urgencia = prio.urgencia_por_prazo(mais_antiga.get("horas_restantes"))
    n = len(paradas)
    resumo = (
        f"{plural(n, 'aprovação aguarda', 'aprovações aguardam')} decisão "
        f"há mais de {int(horas)}h — a mais antiga há {mais_antiga['idade_horas']:.0f}h.")

    return [SignalDraft(
        company_id=ctx.company_id,
        signal_type="approval_pending",
        subject_type="approval_queue",
        subject_id=None,
        summary_redacted=resumo,
        dedupe_key=chave_de_sinal(
            company_id=ctx.company_id, signal_type="approval_pending",
            subject_type="approval_queue", subject_id=None,
            rule_key=ctx.rule_key, rule_version=ctx.rule_version,
            parametros={"faixa": _faixa(n)}),
        trust_tier=TIER_DADO_VIVO,
        rule_key=ctx.rule_key, rule_version=ctx.rule_version,
        severity="high" if (n >= 3 or urgencia >= 90) else "medium",
        confidence=1.0,
        impact_score=min(100.0, 40.0 + 12.0 * n),
        urgency_score=urgencia,
        actionability_score=95.0,   # existe botao: revisar a aprovacao
        recurrence_score=prio.recorrencia_por_contagem(n),
        freshness_score=100.0,
        metadata={"quantidade": n,
                  "ids": [str(a["id"]) for a in paradas[:10]],
                  "mais_antiga_horas": mais_antiga["idade_horas"]},
        evidencias=[
            evidencia(tipo="contagem", sistema="approval_requests",
                      ref=f"company:{ctx.company_id}:pending",
                      resumo=f"{n} aprovação(ões) com status 'pending' há mais de {int(horas)}h",
                      tier=TIER_DADO_VIVO,
                      valores={"quantidade": n,
                               "mais_antiga_horas": mais_antiga["idade_horas"]}),
        ],
    )]


def _faixa(n: int) -> str:
    """Faixa de quantidade para o dedupe.

    Sem faixa, cada aprovacao nova criaria um sinal novo e o corretor receberia
    o mesmo aviso a cada item. Com faixa, ele so volta a ser avisado quando o
    problema MUDA DE TAMANHO — que e quando faz diferenca.
    """
    if n <= 2:
        return "1-2"
    if n <= 5:
        return "3-5"
    if n <= 10:
        return "6-10"
    return "10+"


# ---------------------------------------------------------------------------
# §23.2 — Work Run falhando repetidamente
# ---------------------------------------------------------------------------


def analisar_falhas(runs: list[dict], *, minimo: int = 3) -> list[dict]:
    """Agrupa falhas por causa provavel. Cancelamento intencional fica fora.

    Agrupar por `error_code` e o que transforma "sete trabalhos falharam" em
    "sete trabalhos falharam pelo MESMO motivo" — a segunda frase tem uma
    acao, a primeira nao.

    Trabalho que a PRÓPRIA plataforma disparou (tick, monitor, recomendação)
    também fica fora: quando o ciclo de inteligência falha, o problema é
    nosso, não da corretora — e cobrar dela seria pedir que resolvesse algo
    que ela não controla. Isso aparece no painel do Admin, não no briefing.
    """
    from ..origem import filtrar_externos

    grupos: dict[str, list[dict]] = {}
    for r in filtrar_externos("work_run", runs or []):
        if r.get("status") != "failed":
            continue
        causa = str(r.get("error_code") or "desconhecida")
        grupos.setdefault(causa, []).append(r)
    return [{"causa": c, "quantidade": len(v),
             "workflow_keys": sorted({str(x.get("workflow_key") or "?") for x in v}),
             "run_ids": [str(x["id"]) for x in v[:10]]}
            for c, v in grupos.items() if len(v) >= minimo]


@registrar("operacao.work_run_falhando")
def work_run_falhando(ctx: ContextoDeDeteccao) -> list[SignalDraft]:
    minimo = int(ctx.cfg("minimo_falhas", 3))
    janela_h = int(ctx.cfg("janela_horas", 24))
    corte = _iso_menos_horas(ctx.agora, janela_h)
    try:
        r = (ctx.db.table("work_runs")
             .select("id, status, error_code, error_message, workflow_key, finished_at, source_type")
             .eq("company_id", ctx.company_id).eq("status", "failed")
             .gte("finished_at", corte).limit(300).execute())
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Detector] work_runs: %s", type(exc).__name__)
        return []

    saida: list[SignalDraft] = []
    for grupo in analisar_falhas(r.data or [], minimo=minimo):
        n = grupo["quantidade"]
        resumo = (
            f"{plural(n, 'trabalho falhou', 'trabalhos falharam')} nas últimas "
            f"{janela_h}h pelo mesmo motivo ({grupo['causa']}).")
        saida.append(SignalDraft(
            company_id=ctx.company_id,
            signal_type="work_failure",
            subject_type="work_run_group",
            subject_id=grupo["causa"],
            summary_redacted=resumo,
            dedupe_key=chave_de_sinal(
                company_id=ctx.company_id, signal_type="work_failure",
                subject_type="work_run_group", subject_id=grupo["causa"],
                rule_key=ctx.rule_key, rule_version=ctx.rule_version,
                janela=f"{janela_h}h", parametros={"faixa": _faixa(n)}),
            trust_tier=TIER_EVENTO_SISTEMA,
            rule_key=ctx.rule_key, rule_version=ctx.rule_version,
            severity="high" if n >= minimo * 2 else "medium",
            confidence=1.0,
            impact_score=min(100.0, 45.0 + 8.0 * n),
            urgency_score=70.0,
            actionability_score=70.0,
            recurrence_score=prio.recorrencia_por_contagem(n),
            freshness_score=100.0,
            window_end=ctx.agora.isoformat(),
            metadata={"causa": grupo["causa"], "quantidade": n,
                      "workflows": grupo["workflow_keys"],
                      "run_ids": grupo["run_ids"]},
            evidencias=[
                evidencia(tipo="contagem", sistema="work_runs",
                          ref=f"company:{ctx.company_id}:failed:{grupo['causa']}",
                          resumo=f"{n} execuções com status 'failed' e error_code '{grupo['causa']}'",
                          tier=TIER_EVENTO_SISTEMA,
                          valores={"quantidade": n, "janela_horas": janela_h,
                                   "workflows": grupo["workflow_keys"][:5]}),
            ],
        ))
    return saida


# ---------------------------------------------------------------------------
# §23.3 — Work Run travado (lease vencida)
# ---------------------------------------------------------------------------


@registrar("operacao.work_run_travado")
def work_run_travado(ctx: ContextoDeDeteccao) -> list[SignalDraft]:
    """So alerta quando a recuperacao automatica da SPEC-055 NAO resolveu.

    O Work OS ja recupera lease vencida sozinho. Alertar na primeira
    ocorrencia seria avisar sobre algo que o proprio sistema conserta em
    segundos — ruido puro. O limiar alto existe para isso.
    """
    horas = float(ctx.cfg("horas_travado", 2))
    try:
        r = (ctx.db.table("work_runs")
             .select("id, status, outcome_title, heartbeat_at, started_at, current_step_key, source_type")
             .eq("company_id", ctx.company_id)
             .in_("status", ["running", "planning"]).limit(100).execute())
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Detector] work_runs travados: %s", type(exc).__name__)
        return []

    travados = []
    for run in r.data or []:
        idade = horas_desde(run.get("heartbeat_at") or run.get("started_at"), ctx.agora)
        if idade is not None and idade >= horas:
            travados.append({**run, "idade_horas": round(idade, 1)})
    if not travados:
        return []

    n = len(travados)
    resumo = (f"{plural(n, 'trabalho está', 'trabalhos estão')} sem sinal de vida "
              f"há mais de {int(horas)}h e a recuperação automática não concluiu.")
    return [SignalDraft(
        company_id=ctx.company_id,
        signal_type="work_stale",
        subject_type="work_run_group",
        subject_id="stale",
        summary_redacted=resumo,
        dedupe_key=chave_de_sinal(
            company_id=ctx.company_id, signal_type="work_stale",
            subject_type="work_run_group", subject_id="stale",
            rule_key=ctx.rule_key, rule_version=ctx.rule_version,
            parametros={"faixa": _faixa(n)}),
        trust_tier=TIER_DADO_VIVO,
        rule_key=ctx.rule_key, rule_version=ctx.rule_version,
        severity="high", confidence=1.0,
        impact_score=60.0, urgency_score=75.0, actionability_score=60.0,
        recurrence_score=prio.recorrencia_por_contagem(n), freshness_score=100.0,
        metadata={"quantidade": n, "run_ids": [str(t["id"]) for t in travados[:10]]},
        evidencias=[
            evidencia(tipo="estado", sistema="work_runs",
                      ref=f"company:{ctx.company_id}:stale",
                      resumo=f"{n} execução(ões) ativas sem heartbeat há mais de {int(horas)}h",
                      tier=TIER_DADO_VIVO,
                      valores={"quantidade": n,
                               "mais_antigo_horas": max(t["idade_horas"] for t in travados)}),
        ],
    )]


# ---------------------------------------------------------------------------
# §23.7 — Auxiliar ou Rotina degradado
# ---------------------------------------------------------------------------


@registrar("operacao.auxiliar_degradado")
def auxiliar_degradado(ctx: ContextoDeDeteccao) -> list[SignalDraft]:
    saida: list[SignalDraft] = []
    try:
        aux = (ctx.db.table("tenant_auxiliaries")
               .select("id, name, status, health, health_reason, last_run_at")
               .eq("company_id", ctx.company_id)
               .in_("health", ["degraded", "error"]).limit(50).execute()).data or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Detector] auxiliares: %s", type(exc).__name__)
        aux = []
    try:
        min_falhas = int(ctx.cfg("falhas_consecutivas", 2))
        rot = (ctx.db.table("routines")
               .select("id, name, is_active, consecutive_failures, last_run_at")
               .eq("company_id", ctx.company_id)
               .gte("consecutive_failures", min_falhas).limit(50).execute()).data or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Detector] rotinas: %s", type(exc).__name__)
        rot = []

    for a in aux:
        motivo = str(a.get("health_reason") or "sem detalhe registrado")
        saida.append(SignalDraft(
            company_id=ctx.company_id, signal_type="operational_backlog",
            subject_type="tenant_auxiliary", subject_id=str(a["id"]),
            summary_redacted=(f"O Auxiliar '{a.get('name')}' está com a saúde "
                              f"{a.get('health')}: {motivo}."),
            dedupe_key=chave_de_sinal(
                company_id=ctx.company_id, signal_type="operational_backlog",
                subject_type="tenant_auxiliary", subject_id=str(a["id"]),
                rule_key=ctx.rule_key, rule_version=ctx.rule_version,
                parametros={"health": a.get("health")}),
            trust_tier=TIER_DADO_VIVO, rule_key=ctx.rule_key,
            rule_version=ctx.rule_version,
            severity="high" if a.get("health") == "error" else "medium",
            confidence=1.0, impact_score=55.0, urgency_score=60.0,
            actionability_score=75.0, freshness_score=100.0,
            metadata={"auxiliary_id": str(a["id"]), "health": a.get("health")},
            evidencias=[evidencia(
                tipo="estado", sistema="tenant_auxiliaries",
                ref=f"tenant_auxiliary:{a['id']}",
                resumo=f"health='{a.get('health')}' — {motivo}",
                tier=TIER_DADO_VIVO,
                valores={"health": a.get("health"), "last_run_at": a.get("last_run_at")})],
        ))

    for r in rot:
        n = int(r.get("consecutive_failures") or 0)
        ativa = bool(r.get("is_active"))
        saida.append(SignalDraft(
            company_id=ctx.company_id, signal_type="operational_backlog",
            subject_type="routine", subject_id=str(r["id"]),
            summary_redacted=(
                f"A rotina '{r.get('name')}' falhou {n} vez(es) seguidas"
                + ("." if ativa else " e foi desligada automaticamente para não gastar à toa.")),
            dedupe_key=chave_de_sinal(
                company_id=ctx.company_id, signal_type="operational_backlog",
                subject_type="routine", subject_id=str(r["id"]),
                rule_key=ctx.rule_key, rule_version=ctx.rule_version,
                parametros={"faixa": _faixa(n)}),
            trust_tier=TIER_DADO_VIVO, rule_key=ctx.rule_key,
            rule_version=ctx.rule_version,
            severity="high" if not ativa else "medium",
            confidence=1.0, impact_score=50.0, urgency_score=55.0,
            actionability_score=80.0,
            recurrence_score=prio.recorrencia_por_contagem(n), freshness_score=100.0,
            metadata={"routine_id": str(r["id"]), "falhas": n, "ativa": ativa},
            evidencias=[evidencia(
                tipo="contador", sistema="routines", ref=f"routine:{r['id']}",
                resumo=f"consecutive_failures={n}, is_active={ativa}",
                tier=TIER_DADO_VIVO, valores={"falhas": n, "ativa": ativa})],
        ))
    return saida


# ---------------------------------------------------------------------------
# §23.9 — peca pronta e nao entregue
# ---------------------------------------------------------------------------


@registrar("operacao.artifact_nao_entregue")
def artifact_nao_entregue(ctx: ContextoDeDeteccao) -> list[SignalDraft]:
    """Peca publicada que ninguem abriu nem compartilhou.

    Relatorio pronto que o corretor nao viu e trabalho jogado fora: custou
    modelo, custou tempo e nao virou nada. E o tipo de perda que nao aparece
    em nenhum painel de erro, porque tecnicamente deu tudo certo.
    """
    horas = float(ctx.cfg("horas_sem_leitura", 24))
    corte = _iso_menos_horas(ctx.agora, 24 * 14)
    try:
        arts = (ctx.db.table("artifacts")
                .select("id, title, status, created_at, origin")
                .eq("company_id", ctx.company_id).eq("status", "ready")
                .gte("created_at", corte).limit(60).execute()).data or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Detector] artifacts: %s", type(exc).__name__)
        return []
    if not arts:
        return []

    ids = [a["id"] for a in arts]
    vistos: set[str] = set()
    try:
        ev = (ctx.db.table("artifact_events")
              .select("artifact_id, event_type")
              .eq("company_id", ctx.company_id).in_("artifact_id", ids)
              .in_("event_type", ["share.viewed", "share.created", "artifact.viewed"])
              .limit(500).execute()).data or []
        vistos = {str(e["artifact_id"]) for e in ev}
    except Exception:  # noqa: BLE001
        pass

    # Peça gerada por rotina ou monitor sem ninguém pedir não é "peça pronta
    # e não entregue" — é bookkeeping. O briefing em PDF que a corretora não
    # abriu é outro assunto, e cobrar isso todo dia vira ruído.
    from ..origem import filtrar_externos

    parados = [a for a in filtrar_externos("artifact", arts)
               if str(a["id"]) not in vistos
               and (horas_desde(a.get("created_at"), ctx.agora) or 0) >= horas]
    if not parados:
        return []

    n = len(parados)
    return [SignalDraft(
        company_id=ctx.company_id, signal_type="operational_backlog",
        subject_type="artifact_group", subject_id="nao_entregue",
        summary_redacted=(
            f"{plural(n, 'peça pronta ainda não foi', 'peças prontas ainda não foram')} "
            f"aberta nem compartilhada."),
        dedupe_key=chave_de_sinal(
            company_id=ctx.company_id, signal_type="operational_backlog",
            subject_type="artifact_group", subject_id="nao_entregue",
            rule_key=ctx.rule_key, rule_version=ctx.rule_version,
            parametros={"faixa": _faixa(n)}),
        trust_tier=TIER_DADO_VIVO, rule_key=ctx.rule_key,
        rule_version=ctx.rule_version, severity="low", confidence=1.0,
        impact_score=35.0, urgency_score=30.0, actionability_score=85.0,
        freshness_score=80.0,
        metadata={"quantidade": n, "artifact_ids": [str(a["id"]) for a in parados[:10]],
                  "titulos": [str(a.get("title") or "") for a in parados[:5]]},
        evidencias=[evidencia(
            tipo="contagem", sistema="artifacts",
            ref=f"company:{ctx.company_id}:ready_sem_leitura",
            resumo=f"{n} peça(s) com status 'ready' sem evento de abertura ou compartilhamento",
            tier=TIER_DADO_VIVO, valores={"quantidade": n, "janela_horas": horas})],
    )]


def _iso_menos_horas(agora, horas: float) -> str:
    from datetime import timedelta

    return (agora - timedelta(hours=horas)).isoformat()
