"""Detectores de automacao e resultado. SPEC-059 §23.10, §23.11, §23.12.

Estes tres sao os que mais mudam a percepcao do produto. Os de operacao dizem
"algo quebrou"; estes dizem "isto pode parar de dar trabalho" e "isto deu
certo". Um sistema proativo que so avisa de problema vira uma fonte de mau
humor — e o corretor desliga.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from .. import priority_service as prio
from ..dedupe_service import assinatura_semantica, chave_de_sinal
from ..redaction_service import resumo_seguro
from ..schemas import (TIER_ANALISE, TIER_DADO_VIVO, TIER_DECLARACAO,
                       SignalDraft, evidencia)
from . import ContextoDeDeteccao, plural, registrar

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# §23.10 — tarefa repetida
# ---------------------------------------------------------------------------


def agrupar_repeticoes(pedidos: list[dict], *, minimo: int = 3) -> list[dict]:
    """Agrupa pedidos por assinatura. Puro.

    A assinatura vem da Auxiliary Factory, entao "me manda o relatorio de
    comissoes", "gera o relatorio de comissao" e "quero o relatorio das
    comissoes" contam como o MESMO pedido. Sem isso o detector so pegaria
    quem repete a frase exata — praticamente ninguem.
    """
    grupos: dict[str, dict] = {}
    for p in pedidos or []:
        texto = str(p.get("texto") or "").strip()
        if len(texto) < 12:
            continue
        chave = assinatura_semantica(texto)
        g = grupos.setdefault(chave, {"assinatura": chave, "exemplo": texto,
                                      "vezes": 0, "quando": []})
        g["vezes"] += 1
        if p.get("quando"):
            g["quando"].append(p["quando"])
    return [g for g in grupos.values() if g["vezes"] >= minimo]


@registrar("automacao.tarefa_repetida")
def tarefa_repetida(ctx: ContextoDeDeteccao) -> list[SignalDraft]:
    minimo = int(ctx.cfg("minimo_repeticoes", 3))
    dias = int(ctx.cfg("janela_dias", 14))
    desde = (ctx.agora - timedelta(days=dias)).isoformat()

    pedidos: list[dict] = []
    try:
        reqs = (ctx.db.table("auxiliary_requests")
                .select("requested_outcome, request_text_redacted, created_at")
                .eq("company_id", ctx.company_id)
                .gte("created_at", desde).limit(300).execute()).data or []
        pedidos += [{"texto": r.get("requested_outcome") or r.get("request_text_redacted"),
                     "quando": r.get("created_at")} for r in reqs]
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Detector] auxiliary_requests: %s", type(exc).__name__)

    grupos = agrupar_repeticoes(pedidos, minimo=minimo)
    saida: list[SignalDraft] = []
    for g in grupos:
        n = g["vezes"]
        exemplo = resumo_seguro(g["exemplo"], 140)
        saida.append(SignalDraft(
            company_id=ctx.company_id,
            signal_type="repeated_task",
            subject_type="request_signature", subject_id=g["assinatura"],
            summary_redacted=(
                f"O mesmo pedido apareceu {n} vezes em {dias} dias: “{exemplo}”. "
                f"Dá para deixar isso rodando sozinho."),
            dedupe_key=chave_de_sinal(
                company_id=ctx.company_id, signal_type="repeated_task",
                subject_type="request_signature", subject_id=g["assinatura"],
                rule_key=ctx.rule_key, rule_version=ctx.rule_version,
                parametros={"faixa": "3-5" if n <= 5 else "6+"}),
            trust_tier=TIER_ANALISE,
            rule_key=ctx.rule_key, rule_version=ctx.rule_version,
            severity="low", confidence=0.8,
            impact_score=min(100.0, 30.0 + 8.0 * n),
            urgency_score=25.0,          # oportunidade nao e urgencia
            actionability_score=90.0,    # a Factory sabe propor o formato
            recurrence_score=prio.recorrencia_por_contagem(n),
            freshness_score=90.0,
            metadata={"assinatura": g["assinatura"], "vezes": n,
                      "exemplo": exemplo, "janela_dias": dias},
            evidencias=[evidencia(
                tipo="contagem", sistema="auxiliary_requests",
                ref=f"assinatura:{g['assinatura']}",
                resumo=f"{n} pedidos com a mesma assinatura em {dias} dias",
                tier=TIER_DADO_VIVO, valores={"vezes": n, "janela_dias": dias})],
        ))
    return saida


# ---------------------------------------------------------------------------
# §23.11 — lacuna de capacidade recorrente
# ---------------------------------------------------------------------------


@registrar("automacao.lacuna_recorrente")
def lacuna_recorrente(ctx: ContextoDeDeteccao) -> list[SignalDraft]:
    """Lacunas que a corretora ja esbarrou mais de uma vez.

    O sinal existe para o CORRETOR, nao para o roadmap: ele merece saber que
    o sistema entendeu o pedido e nao consegue atender ainda, com a
    alternativa disponivel — em vez de o pedido sumir na conversa (§19.5).
    """
    minimo = int(ctx.cfg("minimo_ocorrencias", 2))
    try:
        lacunas = (ctx.db.table("capability_gaps")
                   .select("id, gap_type, capability_key, description_redacted, "
                           "frequency_count, first_seen_at, last_seen_at, status")
                   .eq("company_id", ctx.company_id).eq("status", "open")
                   .gte("frequency_count", minimo).limit(30).execute()).data or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Detector] capability_gaps: %s", type(exc).__name__)
        return []

    saida: list[SignalDraft] = []
    for l in lacunas:
        n = int(l.get("frequency_count") or 1)
        desc = resumo_seguro(str(l.get("description_redacted") or ""), 160)
        saida.append(SignalDraft(
            company_id=ctx.company_id, signal_type="capability_gap",
            subject_type="capability_gap", subject_id=str(l["id"]),
            summary_redacted=(
                f"Você pediu {n} vezes algo que o AutoBrokers ainda não faz: “{desc}”. "
                f"O pedido está registrado."),
            dedupe_key=chave_de_sinal(
                company_id=ctx.company_id, signal_type="capability_gap",
                subject_type="capability_gap", subject_id=str(l["id"]),
                rule_key=ctx.rule_key, rule_version=ctx.rule_version,
                parametros={"faixa": "2-4" if n <= 4 else "5+"}),
            trust_tier=TIER_DADO_VIVO, rule_key=ctx.rule_key,
            rule_version=ctx.rule_version, severity="low", confidence=1.0,
            impact_score=min(100.0, 25.0 + 6.0 * n), urgency_score=20.0,
            # A acionabilidade e baixa de proposito: nao HA acao para oferecer.
            # Inflar isto colocaria a lacuna acima de coisas que o corretor
            # pode resolver hoje.
            actionability_score=20.0,
            recurrence_score=prio.recorrencia_por_contagem(n), freshness_score=70.0,
            metadata={"gap_id": str(l["id"]), "gap_type": l.get("gap_type"),
                      "vezes": n},
            evidencias=[evidencia(
                tipo="contador", sistema="capability_gaps",
                ref=f"capability_gap:{l['id']}",
                resumo=f"frequency_count={n}, tipo={l.get('gap_type')}",
                tier=TIER_DADO_VIVO, valores={"vezes": n})],
        ))
    return saida


# ---------------------------------------------------------------------------
# §23.12 — resultado positivo
# ---------------------------------------------------------------------------


@registrar("automacao.resultado_positivo")
def resultado_positivo(ctx: ContextoDeDeteccao) -> list[SignalDraft]:
    """Trabalho concluido no periodo. Vira linha de RESULTADO no briefing.

    Um sinal por periodo, com contagem — nunca um por trabalho. §23.12 e
    explicito: "sem spam de congratulacao a cada acao pequena". Elogio
    repetido a cada micro-tarefa e a forma mais rapida de o corretor parar de
    ler o briefing inteiro, inclusive a parte que importa.
    """
    janela_h = int(ctx.cfg("janela_horas", 24))
    corte = (ctx.agora - timedelta(hours=janela_h)).isoformat()
    try:
        runs = (ctx.db.table("work_runs")
                .select("id, outcome_title, outcome_type, finished_at, result_summary")
                .eq("company_id", ctx.company_id).eq("status", "completed")
                .gte("finished_at", corte).limit(200).execute()).data or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Detector] work_runs concluidos: %s", type(exc).__name__)
        return []

    n = len(runs)
    if n < int(ctx.cfg("minimo", 1)):
        return []

    titulos = [str(r.get("outcome_title") or "").strip() for r in runs]
    destaques = [t for t in dict.fromkeys(titulos) if t][:4]
    return [SignalDraft(
        company_id=ctx.company_id, signal_type="positive_outcome",
        subject_type="work_window", subject_id=ctx.agora.strftime("%Y-%m-%d"),
        summary_redacted=(
            f"{plural(n, 'trabalho foi concluído', 'trabalhos foram concluídos')} "
            f"nas últimas {janela_h}h."),
        dedupe_key=chave_de_sinal(
            company_id=ctx.company_id, signal_type="positive_outcome",
            subject_type="work_window", subject_id=ctx.agora.strftime("%Y-%m-%d"),
            rule_key=ctx.rule_key, rule_version=ctx.rule_version,
            janela=ctx.agora.strftime("%Y-%m-%d")),
        trust_tier=TIER_DADO_VIVO, rule_key=ctx.rule_key,
        rule_version=ctx.rule_version, severity="info", confidence=1.0,
        impact_score=20.0, urgency_score=5.0, actionability_score=10.0,
        freshness_score=100.0,
        metadata={"quantidade": n, "destaques": destaques,
                  "run_ids": [str(r["id"]) for r in runs[:10]]},
        evidencias=[evidencia(
            tipo="contagem", sistema="work_runs",
            ref=f"company:{ctx.company_id}:completed:{janela_h}h",
            resumo=f"{n} execução(ões) com status 'completed' nas últimas {janela_h}h",
            tier=TIER_DADO_VIVO, valores={"quantidade": n})],
    )]


# ---------------------------------------------------------------------------
# Voz do corretor — ponte para o Garimpo v3 (§18)
# ---------------------------------------------------------------------------


def sinal_de_voz(company_id: str, *, tipo: str, texto: str, conversa_id=None,
                 user_id=None, rule_key: str = "garimpo.v3",
                 rule_version: str = "3.0.0") -> SignalDraft:
    """Monta o sinal de uma declaracao do corretor. Tier 4 sempre.

    Tier 4 significa: sustenta "o corretor declarou", nao "isto e verdade"
    (§8.2). E por isso que uma reclamacao nunca vira alerta critico sozinha,
    por mais forte que seja a frase.
    """
    limpo = resumo_seguro(texto, 200)
    return SignalDraft(
        company_id=company_id, signal_type=tipo,
        subject_type="broker_voice",
        subject_id=assinatura_semantica(texto),
        summary_redacted=limpo,
        dedupe_key=chave_de_sinal(
            company_id=company_id, signal_type=tipo,
            subject_type="broker_voice", subject_id=assinatura_semantica(texto),
            rule_key=rule_key, rule_version=rule_version),
        trust_tier=TIER_DECLARACAO,
        source_type="garimpo", source_ref=str(conversa_id or "") or None,
        rule_key=rule_key, rule_version=rule_version,
        user_id=str(user_id) if user_id else None,
        severity="medium" if tipo == "churn_risk" else "low",
        confidence=0.7,
        impact_score=55.0 if tipo == "churn_risk" else 35.0,
        urgency_score=45.0 if tipo == "churn_risk" else 20.0,
        actionability_score=40.0, freshness_score=100.0,
        conversation_id=str(conversa_id) if conversa_id else None,
        metadata={"origem": "garimpo_v3"},
        evidencias=[evidencia(
            tipo="declaracao", sistema="conversations",
            ref=f"conversation:{conversa_id}" if conversa_id else "conversation:-",
            resumo=limpo, tier=TIER_DECLARACAO, sensibilidade="restricted")],
    )
