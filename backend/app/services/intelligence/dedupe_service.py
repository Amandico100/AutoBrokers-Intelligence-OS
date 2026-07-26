"""Dedupe, cooldown, escalonamento e expiracao. SPEC-059 §11.

Este modulo e o que separa um produto proativo de um produto irritante.

Lei central 14: **alert fatigue e falha de produto**. Um sistema que repete o
mesmo aviso todo dia nao esta sendo diligente — esta ensinando o corretor a
ignorar avisos, inclusive o que importa.

Tudo aqui e puro. As decisoes de repetir, suprimir e escalar precisam ser
testaveis sem banco: sao elas que mais mudam com calibragem, e regra de
calibragem sem teste vira ajuste no escuro.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from .schemas import chave_dedupe

# §11.3 — janela padrao de silencio por assunto.
COOLDOWN_PADRAO_SEGUNDOS = 86_400          # 24h
COOLDOWN_APOS_DISPENSA_SEGUNDOS = 604_800  # 7 dias

# §11.4 — o quanto a prioridade precisa subir para furar o cooldown.
DELTA_MINIMO_DE_ESCALONAMENTO = 15.0

# §11.5 — validade padrao por familia de sinal, em horas.
VALIDADE_HORAS: dict[str, int] = {
    "approval_pending": 72,
    "work_failure": 48,
    "work_stale": 24,
    "connection_health": 24,
    "provider_health": 12,
    "budget_risk": 168,
    "attendance_quality": 168,
    "operational_backlog": 48,
    "repeated_task": 336,
    "process_automation_opportunity": 336,
    "commercial_opportunity": 336,
    "broker_pain": 720,
    "broker_desire": 720,
    "feature_request": 720,
    "capability_gap": 720,
    "churn_risk": 336,
    "positive_outcome": 168,
    "portal_blocker": 48,
    "compliance_risk": 168,
    "security_risk": 48,
}
VALIDADE_HORAS_PADRAO = 72


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _dt(valor) -> Optional[datetime]:
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)
    try:
        d = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# §11.1 — dedupe deterministico
# ---------------------------------------------------------------------------


def chave_de_sinal(*, company_id: str, signal_type: str, subject_type: str,
                   subject_id: Optional[str], rule_key: Optional[str] = None,
                   rule_version: Optional[str] = None,
                   janela: Optional[str] = None,
                   parametros: Optional[dict] = None) -> str:
    """Chave do §11.1: empresa + tipo + sujeito + regra/versao + janela + params.

    A versao da regra entra de proposito. Quando o limiar muda, o sinal
    ANTIGO nao pode calar o novo: sao observacoes diferentes, feitas com
    reguas diferentes, e tratar como a mesma esconde o efeito da calibragem.
    """
    normalizados = sorted(
        f"{k}={v}" for k, v in (parametros or {}).items() if v is not None)
    return chave_dedupe(
        company_id, signal_type, subject_type, subject_id or "-",
        f"{rule_key or '-'}@{rule_version or '-'}", janela or "-",
        ",".join(normalizados) or "-")


def chave_de_finding(*, company_id: str, finding_type: str,
                     subject: Optional[str] = None,
                     periodo: Optional[str] = None) -> str:
    return chave_dedupe(company_id, finding_type, subject or "-", periodo or "-")


def validade_de(signal_type: str, *, base: Optional[datetime] = None) -> datetime:
    horas = VALIDADE_HORAS.get(signal_type, VALIDADE_HORAS_PADRAO)
    return (base or _agora()) + timedelta(hours=horas)


def expirou(valid_until, *, agora: Optional[datetime] = None) -> bool:
    fim = _dt(valid_until)
    if fim is None:
        return False
    return fim <= (agora or _agora())


# ---------------------------------------------------------------------------
# §11.2 — dedupe semantico (voz do corretor)
# ---------------------------------------------------------------------------


def assinatura_semantica(texto: str) -> str:
    """Assinatura de PEDIDO, nao de texto.

    Reaproveita o `fingerprint` da Auxiliary Factory (SPEC-058), que ja
    resolve radical de verbo e descarte de nome proprio. Criar uma segunda
    normalizacao aqui faria o mesmo pedido receber duas assinaturas — e o
    funil de demanda so funciona se as duas pontas concordarem.
    """
    from ..auxiliaries.factory import fingerprint

    return fingerprint(texto or "")


# ---------------------------------------------------------------------------
# §11.3 e §11.4 — cooldown e escalonamento
# ---------------------------------------------------------------------------


@dataclass
class EstadoDeEntrega:
    """O que ja aconteceu com este assunto para este destinatario."""

    ultima_entrega_em: Optional[datetime] = None
    prioridade_na_ultima_entrega: float = 0.0
    dispensado_em: Optional[datetime] = None
    acao_em_andamento: bool = False
    resolvido: bool = False
    entregas_hoje: int = 0
    evidencias_novas: int = 0


@dataclass
class DecisaoDeRepeticao:
    repetir: bool
    motivo: str
    escalonamento: bool = False
    detalhes: dict = field(default_factory=dict)


def pode_repetir(
    estado: EstadoDeEntrega,
    *,
    prioridade_atual: float,
    severidade_subiu: bool = False,
    prazo_critico_novo: bool = False,
    aprovacao_expirando: bool = False,
    acao_anterior_falhou: bool = False,
    provider_voltou_a_falhar: bool = False,
    cooldown_segundos: int = COOLDOWN_PADRAO_SEGUNDOS,
    agora: Optional[datetime] = None,
) -> DecisaoDeRepeticao:
    """Decide se um Finding ja entregue pode aparecer de novo.

    A ordem das checagens **e** o desenho, e ela custou um teste para acertar:

    1. **Resolvido e acao em andamento sao absolutos.** Nada os fura. Cobrar
       de novo algo que ja esta sendo tratado nao e diligencia — e o sintoma
       classico de sistema que nao sabe o que ja pediu.

    2. **Escalonamento de EVENTO (§11.4) fura o silencio.** Provider que voltou
       a cair, prazo novo, aprovacao expirando: sao fatos novos, e calar por
       24h e justamente quando o corretor mais precisa saber.

    3. **Salto de prioridade NAO fura uma dispensa.** O corretor disse "nao
       agora"; um score que subiu nao e informacao nova para ele. E so vale
       como escalonamento se houve entrega anterior — sem ela, `delta` compara
       contra zero e QUALQUER item pareceria escalonamento.
    """
    agora = agora or _agora()

    # 1. Absolutos.
    if estado.resolvido:
        return DecisaoDeRepeticao(False, "o problema já foi resolvido")
    if estado.acao_em_andamento:
        return DecisaoDeRepeticao(False, "já existe uma ação em andamento")

    eventos = {
        "severidade_subiu": severidade_subiu,
        "prazo_critico_novo": prazo_critico_novo,
        "aprovacao_expirando": aprovacao_expirando,
        "acao_anterior_falhou": acao_anterior_falhou,
        "provider_voltou_a_falhar": provider_voltou_a_falhar,
    }
    escalonou_por_evento = any(eventos.values())

    delta = (prioridade_atual - estado.prioridade_na_ultima_entrega
             if estado.ultima_entrega_em else 0.0)
    escalonou_por_prioridade = (
        estado.ultima_entrega_em is not None
        and delta >= DELTA_MINIMO_DE_ESCALONAMENTO)

    detalhes = {**eventos, "delta_prioridade": round(delta, 2)}

    # 2. Dispensa: só evento fura.
    if estado.dispensado_em:
        limite = estado.dispensado_em + timedelta(seconds=COOLDOWN_APOS_DISPENSA_SEGUNDOS)
        if agora < limite:
            if escalonou_por_evento:
                return DecisaoDeRepeticao(
                    True, "escalonamento legítimo mesmo após dispensa",
                    escalonamento=True, detalhes=detalhes)
            return DecisaoDeRepeticao(
                False, "o corretor dispensou este assunto recentemente",
                detalhes={"silencio_ate": limite.isoformat()})

    # 3. Janela de silêncio: evento OU salto grande de prioridade furam.
    if estado.ultima_entrega_em:
        limite = estado.ultima_entrega_em + timedelta(seconds=cooldown_segundos)
        if agora < limite:
            if escalonou_por_evento or escalonou_por_prioridade:
                return DecisaoDeRepeticao(True, "escalonamento legítimo",
                                          escalonamento=True, detalhes=detalhes)
            return DecisaoDeRepeticao(
                False, "dentro da janela de silêncio deste assunto",
                detalhes={"silencio_ate": limite.isoformat()})
        if not estado.evidencias_novas and not escalonou_por_evento:
            return DecisaoDeRepeticao(False, "nada mudou desde a última vez")

    return DecisaoDeRepeticao(True, "primeira entrega ou janela vencida com novidade")


# ---------------------------------------------------------------------------
# Agrupamento
# ---------------------------------------------------------------------------


def agrupar_por_assunto(sinais: list[dict]) -> dict[str, list[dict]]:
    """Agrupa sinais que o corretor leria como o mesmo problema.

    Cinco falhas do mesmo conector sao UM item de briefing com contagem, nao
    cinco linhas. §15.2 exige exatamente isso para P2/P3.
    """
    grupos: dict[str, list[dict]] = {}
    for s in sinais or []:
        chave = f"{s.get('signal_type')}|{s.get('subject_type')}|{s.get('subject_id') or '-'}"
        grupos.setdefault(chave, []).append(s)
    return grupos


def mesclar_preservando_linhagem(existente: dict, novo: dict) -> dict:
    """Merge de dois sinais equivalentes. §11.2 exige preservar linhagem.

    O que sobe: contagem, `last_seen_at`, a maior severidade e a maior
    confianca. O que NAO se perde: a primeira observacao. Sobrescrever
    `created_at` apagaria "desde quando isto acontece", que costuma ser a
    informacao mais util do item inteiro.
    """
    ordem = ["info", "low", "medium", "high", "critical"]
    sev_a = existente.get("severity") or "info"
    sev_b = novo.get("severity") or "info"
    return {
        **existente,
        "occurrence_count": int(existente.get("occurrence_count") or 1) + 1,
        "last_seen_at": novo.get("last_seen_at") or _agora().isoformat(),
        "severity": sev_a if ordem.index(sev_a) >= ordem.index(sev_b) else sev_b,
        "confidence": max(float(existente.get("confidence") or 0),
                          float(novo.get("confidence") or 0)),
        "metadata": {**(existente.get("metadata") or {}),
                     "linhagem": [*(existente.get("metadata") or {}).get("linhagem", []),
                                  novo.get("fingerprint")][-20:]},
    }
