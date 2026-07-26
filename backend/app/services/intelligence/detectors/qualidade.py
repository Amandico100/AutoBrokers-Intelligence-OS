"""Detectores de qualidade e atendimento. SPEC-059 §23.5 e §23.6.

O detector de regressao **preserva** o algoritmo deterministico do
`regression_sentinel.py` (SPEC-040 Onda 4). O que muda e o destino: antes ele
mandava WhatsApp direto; agora emite Signal e o pipeline decide se, quando e
por qual canal isso chega a alguem (§29.4). O calculo e o mesmo — reescreve-lo
seria jogar fora um detector que ja funciona e ja foi calibrado.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from .. import priority_service as prio
from ..dedupe_service import chave_de_sinal
from ..schemas import TIER_ANALISE, TIER_DADO_VIVO, SignalDraft, evidencia
from . import ContextoDeDeteccao, horas_desde, plural, registrar

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# §23.5 — regressao de qualidade
# ---------------------------------------------------------------------------


@registrar("qualidade.regressao_atendimento")
def regressao_atendimento(ctx: ContextoDeDeteccao) -> list[SignalDraft]:
    """Nota media das ultimas 24h contra a media dos 7 dias anteriores."""
    min_amostras = int(ctx.cfg("minimo_amostras", 5))
    queda_pontos = float(ctx.cfg("queda_pontos", 10))

    desde = (ctx.agora - timedelta(days=8)).isoformat()
    try:
        rows = (ctx.db.table("conversation_scorecards")
                .select("company_id, score, flags, created_at")
                .eq("company_id", ctx.company_id)
                .gte("created_at", desde).limit(2000).execute()).data or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Detector] scorecards: %s", type(exc).__name__)
        return []

    # Reaproveita o algoritmo ja existente, sem reimplementar.
    try:
        from ...regression_sentinel import analyze_regressions
    except Exception:  # noqa: BLE001 — carga isolada em teste
        return []

    achados = analyze_regressions(rows, ctx.agora, min_amostras, int(queda_pontos))
    saida: list[SignalDraft] = []
    for f in achados:
        if str(f.get("company_id")) != str(ctx.company_id):
            continue  # o algoritmo agrupa por empresa; aqui e uma so
        flags = ", ".join(f.get("top_flags") or []) or "sem padrão dominante"
        resumo = (
            f"A nota média do atendimento caiu de {f['baseline_avg']} para "
            f"{f['recent_avg']} nas últimas 24h ({f['samples']} conversas "
            f"auditadas). Padrões mais comuns: {flags}.")
        saida.append(SignalDraft(
            company_id=ctx.company_id,
            signal_type="attendance_quality",
            subject_type="quality_window", subject_id="24h",
            summary_redacted=resumo,
            dedupe_key=chave_de_sinal(
                company_id=ctx.company_id, signal_type="attendance_quality",
                subject_type="quality_window", subject_id="24h",
                rule_key=ctx.rule_key, rule_version=ctx.rule_version,
                janela=ctx.agora.strftime("%Y-%m-%d"),
                parametros={"queda": _faixa_queda(f["drop"])}),
            # Tier 3: e media e variacao — analise derivada reproduzivel, nao
            # dado vivo. Por isso NUNCA vira alerta critico sozinha (§8.2).
            trust_tier=TIER_ANALISE,
            rule_key=ctx.rule_key, rule_version=ctx.rule_version,
            severity="high" if f["drop"] >= queda_pontos * 2 else "medium",
            confidence=0.85,
            impact_score=min(100.0, 40.0 + 3.0 * float(f["drop"])),
            urgency_score=65.0, actionability_score=55.0,
            freshness_score=100.0,
            window_start=(ctx.agora - timedelta(hours=24)).isoformat(),
            window_end=ctx.agora.isoformat(),
            metadata={"recent_avg": f["recent_avg"], "baseline_avg": f["baseline_avg"],
                      "drop": f["drop"], "samples": f["samples"],
                      "top_flags": f.get("top_flags") or []},
            evidencias=[
                evidencia(tipo="media", sistema="conversation_scorecards",
                          ref=f"company:{ctx.company_id}:24h",
                          resumo=(f"média {f['recent_avg']} em {f['samples']} conversas "
                                  f"nas últimas 24h"),
                          tier=TIER_DADO_VIVO,
                          valores={"media": f["recent_avg"], "amostras": f["samples"]}),
                evidencia(tipo="media", sistema="conversation_scorecards",
                          ref=f"company:{ctx.company_id}:baseline_7d",
                          resumo=f"média {f['baseline_avg']} nos 7 dias anteriores",
                          tier=TIER_DADO_VIVO,
                          valores={"media": f["baseline_avg"]}),
                evidencia(tipo="variacao", sistema="intelligence",
                          ref="queda_calculada",
                          resumo=f"queda de {f['drop']} pontos entre as duas janelas",
                          tier=TIER_ANALISE, valores={"drop": f["drop"]}),
            ],
        ))
    return saida


def _faixa_queda(drop: float) -> str:
    d = float(drop or 0)
    if d < 15:
        return "10-15"
    if d < 25:
        return "15-25"
    return "25+"


# ---------------------------------------------------------------------------
# §23.6 — atendimentos parados
# ---------------------------------------------------------------------------


# §23.6 — "parado" precisa de definição por ESTADO **e por CANAL**.
#
# O canal é a metade que quase ficou de fora, e o canário com dado real pegou:
# a Resulta tinha 20 conversas que casavam com "não encerrada e sem mensagem há
# mais de 24h" — e 18 delas eram o chat do PRÓPRIO CORRETOR com o AutoBrokers
# no dashboard, que fica `active` para sempre porque ninguém "encerra" um chat.
#
# O primeiro briefing dela abriria com "18 atendimentos parados", falando das
# conversas dele com o assistente. Atendimento é o que envolve um segurado do
# outro lado; conversa do corretor com a plataforma não é fila de atendimento.
CANAIS_DE_ATENDIMENTO = ("whatsapp", "whatsapp_business", "telegram",
                         "instagram", "sms", "voice", "email")

# Exceção legítima ao filtro de canal: alguém pediu uma pessoa e ninguém veio.
# Isso é atendimento parado em qualquer canal, inclusive no web.
ESTADOS_DE_ESPERA_HUMANA = ("human_requested", "waiting_human",
                            "aguardando_humano", "handoff")

ESTADOS_ENCERRADOS = ("closed", "resolved", "encerrada", "finalizada",
                      "arquivada", "resolvida")


def analisar_paradas(conversas: list[dict], agora, *, horas: float = 24.0,
                     considerar_horario_comercial: bool = True) -> list[dict]:
    """Puro: quais conversas estao paradas de verdade.

    Encerradas ficam de fora, e o chat do proprio corretor tambem. O desconto
    de horario comercial existe porque sem ele TODA conversa de sexta a tarde
    aparece como "parada" na segunda — e o corretor recebe uma lista de
    problemas que nao sao problemas.
    """
    saida = []
    for c in conversas or []:
        estado = str(c.get("status") or "").lower()
        if estado in ESTADOS_ENCERRADOS:
            continue
        canal = str(c.get("channel") or "").lower()
        espera_humana = estado in ESTADOS_DE_ESPERA_HUMANA
        if canal not in CANAIS_DE_ATENDIMENTO and not espera_humana:
            continue
        idade = horas_desde(c.get("last_message_at") or c.get("updated_at"), agora)
        if idade is None:
            continue
        efetiva = idade
        if considerar_horario_comercial:
            efetiva = _descontar_fim_de_semana(
                c.get("last_message_at") or c.get("updated_at"), agora, idade)
        if efetiva >= horas:
            saida.append({"id": str(c.get("id")), "horas": round(efetiva, 1),
                          "canal": canal, "status": estado,
                          "espera_humana": espera_humana})
    return sorted(saida, key=lambda x: -x["horas"])


def _descontar_fim_de_semana(inicio, agora, idade_horas: float) -> float:
    """Tira sabado e domingo da conta. Aproximacao deliberadamente simples."""
    try:
        from datetime import datetime, timezone as _tz

        d = datetime.fromisoformat(str(inicio).replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=_tz.utc)
    except Exception:  # noqa: BLE001
        return idade_horas
    horas_fds = 0.0
    cursor = d
    while cursor < agora:
        if cursor.weekday() >= 5:
            horas_fds += min(24.0, (agora - cursor).total_seconds() / 3600.0)
        cursor += timedelta(days=1)
    return max(0.0, idade_horas - horas_fds)


@registrar("qualidade.atendimento_parado")
def atendimento_parado(ctx: ContextoDeDeteccao) -> list[SignalDraft]:
    horas = float(ctx.cfg("horas_parado", 24))
    desde = (ctx.agora - timedelta(days=30)).isoformat()
    try:
        conversas = (ctx.db.table("conversations")
                     .select("id, status, channel, last_message_at, updated_at, session_id")
                     .eq("company_id", ctx.company_id)
                     .gte("last_message_at", desde).limit(400).execute()).data or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Detector] conversas: %s", type(exc).__name__)
        return []

    # Espelho de seguradora nao e atendimento do segurado.
    conversas = [c for c in conversas
                 if not str(c.get("session_id") or "").startswith("dispatch:")]
    paradas = analisar_paradas(conversas, ctx.agora, horas=horas)
    if not paradas:
        return []

    n = len(paradas)
    # §23.6: nao revelar PII no briefing geral. O sinal carrega a CONTAGEM e os
    # ids; nome e telefone do segurado ficam na conversa, atras da permissao
    # que ja governa a conversa.
    resumo = (f"{plural(n, 'atendimento está parado', 'atendimentos estão parados')} "
              f"há mais de {int(horas)}h em horário útil "
              f"(o mais antigo há {paradas[0]['horas']:.0f}h).")
    return [SignalDraft(
        company_id=ctx.company_id, signal_type="operational_backlog",
        subject_type="attendance_queue", subject_id="parados",
        summary_redacted=resumo,
        dedupe_key=chave_de_sinal(
            company_id=ctx.company_id, signal_type="operational_backlog",
            subject_type="attendance_queue", subject_id="parados",
            rule_key=ctx.rule_key, rule_version=ctx.rule_version,
            janela=ctx.agora.strftime("%Y-%m-%d"),
            parametros={"faixa": _faixa_qtd(n)}),
        trust_tier=TIER_DADO_VIVO, rule_key=ctx.rule_key,
        rule_version=ctx.rule_version,
        severity="high" if n >= 10 else "medium", confidence=1.0,
        impact_score=min(100.0, 35.0 + 5.0 * n), urgency_score=60.0,
        actionability_score=80.0,
        recurrence_score=prio.recorrencia_por_contagem(n), freshness_score=100.0,
        metadata={"quantidade": n,
                  "conversation_ids": [p["id"] for p in paradas[:15]],
                  "mais_antigo_horas": paradas[0]["horas"]},
        evidencias=[evidencia(
            tipo="contagem", sistema="conversations",
            ref=f"company:{ctx.company_id}:parados",
            resumo=(f"{n} conversa(s) não encerradas sem mensagem há mais de "
                    f"{int(horas)}h úteis"),
            tier=TIER_DADO_VIVO,
            valores={"quantidade": n, "mais_antigo_horas": paradas[0]["horas"]},
            sensibilidade="restricted")],
    )]


def _faixa_qtd(n: int) -> str:
    if n <= 2:
        return "1-2"
    if n <= 5:
        return "3-5"
    if n <= 10:
        return "6-10"
    if n <= 25:
        return "11-25"
    return "25+"
