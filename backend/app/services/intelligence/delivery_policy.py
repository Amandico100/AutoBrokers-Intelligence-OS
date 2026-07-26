"""Politica de proatividade: horario, frequencia, canal e papel. SPEC-059 §15.

Puro. Recebe o perfil e o estado, devolve a decisao e o motivo em portugues.

O motivo importa tanto quanto a decisao. §15.5 exige que toda mensagem
proativa diga por que apareceu — e a unica forma de isso ser verdade e a
politica devolver a frase junto, em vez de alguem escrever depois um texto
plausivel que nao corresponde ao que o codigo fez.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from typing import Optional

QUIET_HOURS_PADRAO = {"start": "20:00", "end": "08:00"}
MAX_PUSHES_PADRAO = 3

# §15.1 — o que atravessa quiet hours. A lista e curta de proposito: cada
# excecao nova e um passivo, porque o corretor nao pode desligar o telefone
# seletivamente.
SEVERIDADES_QUE_FURAM_SILENCIO = ("critical",)
CATEGORIAS_QUE_FURAM_SILENCIO = ("security_risk", "compliance_risk")

ORDEM_SEVERIDADE = ("info", "low", "medium", "high", "critical")


def _hora(texto: str, padrao: time) -> time:
    try:
        h, m = str(texto).split(":")[:2]
        return time(int(h), int(m))
    except Exception:  # noqa: BLE001
        return padrao


def _tz(nome: str):
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(nome or "America/Sao_Paulo")
    except Exception:  # noqa: BLE001 — container sem tzdata
        return timezone(timedelta(hours=-3))


def em_quiet_hours(agora_utc: datetime, *, timezone_nome: str = "America/Sao_Paulo",
                   quiet_hours: Optional[dict] = None) -> bool:
    """`True` se estamos dentro da janela de silencio do perfil.

    A janela cruza a meia-noite no caso padrao (20:00–08:00), entao a
    comparacao nao pode ser um simples `inicio <= agora <= fim`.
    """
    qh = quiet_hours or QUIET_HOURS_PADRAO
    local = agora_utc.astimezone(_tz(timezone_nome))
    inicio = _hora(qh.get("start", "20:00"), time(20, 0))
    fim = _hora(qh.get("end", "08:00"), time(8, 0))
    atual = local.time()
    if inicio <= fim:
        return inicio <= atual < fim
    return atual >= inicio or atual < fim


@dataclass
class ContextoDeEntrega:
    severidade: str = "medium"
    categoria: str = ""
    tem_acao_clara: bool = False
    pushes_hoje: int = 0
    usuario_opt_in_fora_de_horario: bool = False
    operacao_24h: bool = False


@dataclass
class DecisaoDeEntrega:
    push: bool
    canais: list[str] = field(default_factory=list)
    motivo: str = ""
    adiar_para: Optional[str] = None
    incluir_no_briefing: bool = True


def decidir(
    ctx: ContextoDeEntrega,
    *,
    agora_utc: Optional[datetime] = None,
    perfil: Optional[dict] = None,
) -> DecisaoDeEntrega:
    """Decide se isto vira push agora, entra no briefing ou espera.

    Note a ordem: **acao clara antes de tudo**. §15.2 proibe push de mensagem
    sem acao — e essa e a regra mais violada por sistemas proativos, porque
    "avisar" parece util e custa nada para quem envia.
    """
    perfil = perfil or {}
    agora_utc = agora_utc or datetime.now(timezone.utc)
    tz_nome = perfil.get("timezone") or "America/Sao_Paulo"
    limite = int(perfil.get("max_pushes_per_day") or MAX_PUSHES_PADRAO)
    canais = list(perfil.get("channels") or ["dashboard"])
    threshold = perfil.get("severity_threshold") or "medium"

    critico = (
        ctx.severidade in SEVERIDADES_QUE_FURAM_SILENCIO
        or ctx.categoria in CATEGORIAS_QUE_FURAM_SILENCIO
    )

    # Abaixo do limiar do perfil: entra no briefing e pronto.
    try:
        abaixo = ORDEM_SEVERIDADE.index(ctx.severidade) < ORDEM_SEVERIDADE.index(threshold)
    except ValueError:
        abaixo = False
    if abaixo and not critico:
        return DecisaoDeEntrega(
            False, ["dashboard"],
            "abaixo do nível de severidade que este perfil pede em tempo real")

    if not ctx.tem_acao_clara and not critico:
        return DecisaoDeEntrega(
            False, ["dashboard"],
            "não há uma ação clara a oferecer — entra no briefing, sem interromper")

    if ctx.pushes_hoje >= limite and not critico:
        return DecisaoDeEntrega(
            False, ["dashboard"],
            f"o limite de {limite} avisos por dia já foi atingido")

    silencio = em_quiet_hours(agora_utc, timezone_nome=tz_nome,
                              quiet_hours=perfil.get("quiet_hours"))
    if silencio and not critico and not ctx.operacao_24h and not ctx.usuario_opt_in_fora_de_horario:
        return DecisaoDeEntrega(
            False, ["dashboard"], "fora do horário combinado — guardado para o próximo briefing",
            adiar_para=proximo_horario_util(agora_utc, tz_nome, perfil.get("quiet_hours")).isoformat())

    motivo = "crítico: entrega imediata mesmo fora do horário" if (silencio and critico) \
        else "dentro do horário, abaixo do limite diário e com ação disponível"
    return DecisaoDeEntrega(True, canais, motivo)


def proximo_horario_util(agora_utc: datetime, timezone_nome: str = "America/Sao_Paulo",
                         quiet_hours: Optional[dict] = None) -> datetime:
    """Quando o silencio termina. Usado para adiar em vez de descartar."""
    qh = quiet_hours or QUIET_HOURS_PADRAO
    tz = _tz(timezone_nome)
    local = agora_utc.astimezone(tz)
    fim = _hora(qh.get("end", "08:00"), time(8, 0))
    candidato = local.replace(hour=fim.hour, minute=fim.minute, second=0, microsecond=0)
    if candidato <= local:
        candidato += timedelta(days=1)
    return candidato.astimezone(timezone.utc)


def frase_de_transparencia(motivo_tecnico: str, evidencia_curta: str) -> str:
    """§15.5 — "mostrei isso porque…", em portugues, com o numero junto."""
    base = (evidencia_curta or "").strip().rstrip(".")
    if not base:
        return "Mostrei isso porque foi o item mais relevante do período."
    return f"Mostrei isso porque {base}."


def ajustar_cooldown_por_feedback(cooldown_atual: int, acao: str) -> int:
    """§15.4 — feedback negativo aumenta o silencio, sem apagar evidencia.

    `wrong_data` recebe o MENOR aumento de proposito: o corretor esta dizendo
    que o dado esta errado, nao que o assunto e irrelevante. Calar por sete
    dias um problema real porque o numero saiu torto seria trocar um defeito
    por outro pior.
    """
    fatores = {
        "not_relevant": 4.0,
        "dismiss": 2.0,
        "already_solved": 3.0,
        "wrong_data": 1.5,
        "snooze": 1.0,
    }
    fator = fatores.get(acao, 1.0)
    return int(min(cooldown_atual * fator, 30 * 86_400))
