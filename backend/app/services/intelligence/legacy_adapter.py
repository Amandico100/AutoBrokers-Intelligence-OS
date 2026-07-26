"""Adapters do legado proativo. SPEC-059 §29.

Quatro motores proativos existiam antes desta SPEC, cada um com seu horario,
seu marcador em Redis e seu envio direto de WhatsApp:

    broker_insights.check_garimpo        → mineração diária
    proactive_suggestions.check_suggestions → 1 mensagem fixa por semana
    weekly_report.check_weekly_report    → relatório de sábado
    regression_sentinel.check_regression → alerta de queda de qualidade

O que **se preserva** deles: a regex do Garimpo, a contagem determinística do
relatório e o algoritmo de regressão. São peças calibradas, e reescrevê-las
seria jogar fora trabalho que funciona.

O que **muda**: o destino. Nenhum deles volta a enviar direto. Todos passam a
alimentar o pipeline, que decide com evidência, dedupe, cooldown e quiet
hours se aquilo vira mensagem — e por qual canal.

O corte é governado por `INTELLIGENCE_CUTOVER` (padrão LIGADO). A flag existe
para rollback, não para manter o caminho canônico desligado: §0.1 é explícita
de que a entrega não termina enquanto o canônico estiver inativo.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


def cutover_ligado() -> bool:
    """`True` quando o pipeline canônico é a autoridade da proatividade."""
    return str(os.getenv("INTELLIGENCE_CUTOVER", "1")).strip().lower() \
        in ("1", "true", "yes", "on")


def _avisar_uma_vez(chave: str, mensagem: str) -> None:
    """Loga o desvio uma vez por processo. Repetir a cada tick vira ruído."""
    if chave in _JA_AVISADOS:
        return
    _JA_AVISADOS.add(chave)
    logger.info("[SPEC-059] %s", mensagem)


_JA_AVISADOS: set[str] = set()


# ---------------------------------------------------------------------------
# §29.1 — Garimpo
# ---------------------------------------------------------------------------


async def garimpo(supabase_client: Any, *, horas: int = 24) -> int:
    """Executa o Garimpo v3. Devolve quantos sinais de voz foram criados."""
    from .garimpo_v3 import GarimpoV3

    r = GarimpoV3(supabase_client).minerar_recentes(horas=horas)
    return int(r.get("sinais") or 0)


# ---------------------------------------------------------------------------
# §29.3 — contagens do relatório semanal, preservadas como FONTE
# ---------------------------------------------------------------------------


def contagens_de_atividade(supabase_client: Any, company_id: str,
                           *, dias: int = 7) -> dict:
    """As contagens determinísticas que o relatório de sábado já fazia.

    Continuam existindo porque são Tier 0 e custam zero. O que sai de cena é
    a mensagem pronta com fecho comercial — no briefing executivo elas viram
    indicador com fonte e período declarados.
    """
    db = getattr(supabase_client, "client", supabase_client)
    corte = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
    try:
        atividades = (db.table("agent_activities")
                      .select("category, title, created_at")
                      .eq("company_id", company_id)
                      .gte("created_at", corte).limit(1000).execute()).data or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("[LegacyAdapter] agent_activities: %s", type(exc).__name__)
        return {"total": 0, "por_categoria": {}, "destaques": [], "dias": dias}

    por_categoria: dict[str, int] = {}
    destaques: list[str] = []
    for a in atividades:
        cat = str(a.get("category") or "outros")
        por_categoria[cat] = por_categoria.get(cat, 0) + 1
        titulo = str(a.get("title") or "")
        if titulo and titulo not in destaques and len(destaques) < 4:
            destaques.append(titulo)

    return {"total": len(atividades), "por_categoria": por_categoria,
            "destaques": destaques, "dias": dias,
            "fonte": "agent_activities"}


ROTULOS_DE_CATEGORIA = {
    "atendimentos": "atendimentos aos seus clientes",
    "acionamentos": "acionamentos de assistência conduzidos",
    "qualidade": "verificações de qualidade",
    "conhecimento": "conhecimento processado",
    "inteligencia": "análises de negócio",
    "auxiliares": "execuções de Auxiliares e Rotinas",
}


def indicadores_da_semana(contagens: dict) -> list[dict]:
    """Transforma as contagens em indicadores com período e fonte — §24.1.

    Todo número carrega de onde veio e de quando. "+12%" sem base de
    comparação é ruído; contagem sem período é pior, porque parece precisa.
    """
    dias = int(contagens.get("dias") or 7)
    saida = []
    for chave, n in sorted(contagens.get("por_categoria", {}).items(),
                           key=lambda x: -x[1]):
        saida.append({
            "rotulo": ROTULOS_DE_CATEGORIA.get(chave, chave),
            "valor": n,
            "periodo": f"últimos {dias} dias",
            "fonte": contagens.get("fonte") or "agent_activities",
        })
    return saida


# ---------------------------------------------------------------------------
# §29.2 e §29.4 — o que deixou de enviar direto
# ---------------------------------------------------------------------------


def sugestoes_desativadas() -> int:
    """A mensagem semanal fixa deixou de ser autoridade de proatividade.

    Ela mandava três blocos iguais toda segunda, independentemente de haver
    ou não algo relevante — o oposto de §15.2 ("mensagens sem ação clara não
    geram push") e de §0.1 ("nenhuma pergunta semanal genérica obrigatória").
    """
    _avisar_uma_vez(
        "sugestoes",
        "IA de Sugestões desligada: a proatividade agora passa por Findings, "
        "recomendações e Briefing (SPEC-059 §29.2).")
    return 0


def relatorio_semanal_desativado() -> int:
    """O relatório de sábado virou o Briefing Executivo Semanal."""
    _avisar_uma_vez(
        "relatorio",
        "Relatório de sábado desligado: substituído pelo Briefing Executivo "
        "Semanal, com evidência e link (SPEC-059 §29.3).")
    return 0


def regressao_delegada() -> int:
    """A Sentinela de Regressão continua detectando — e parou de enviar.

    O algoritmo é o mesmo, chamado agora pelo detector
    `qualidade.regressao_atendimento`. O que deixou de existir é o WhatsApp
    disparado direto de dentro do detector, sem cooldown e sem quiet hours.
    """
    _avisar_uma_vez(
        "regressao",
        "Sentinela de Regressão passou a emitir Signal em vez de enviar "
        "WhatsApp direto (SPEC-059 §29.4).")
    return 0
