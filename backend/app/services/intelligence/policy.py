"""Gates de dominio. SPEC-059 §12.4, §30.5 e §8.3.

Score alto nao autoriza nada sozinho. Estes gates existem porque algumas
decisoes tem consequencia que nenhuma priorizacao compensa: cobertura
securitaria, obrigacao legal, seguranca e vazamento de dado.

Puro, por design. Um gate que precisa de banco para responder "isto pode
executar sozinho?" e um gate que falha aberto quando o banco oscila.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .schemas import TIERS_QUE_SUSTENTAM_ALERTA_CRITICO, TIPOS_COM_GATE_PROPRIO

# §30.5 — assuntos que nunca executam por conta propria.
ASSUNTOS_DE_ALTO_RISCO = frozenset({
    "cobertura", "indenizacao", "sinistro", "juridico", "compliance",
    "regulatorio", "susep", "cancelamento_de_apolice", "endosso",
})

# Efeitos que sempre passam por aprovacao, independentemente do score.
EFEITOS_QUE_EXIGEM_APROVACAO = frozenset({
    "communication", "write_irreversible", "financial", "external_commitment",
})


@dataclass
class DecisaoDePolicy:
    permitido: bool
    exige_aprovacao: bool
    exige_humano_responsavel: bool
    motivo: str


def pode_alertar_como_critico(*, trust_tier: int, evidencias: int,
                              signal_type: str) -> DecisaoDePolicy:
    """§8.2 — alerta critico exige Tier 0/1/2 e evidencia.

    Nao ha excecao configuravel de proposito. Se houvesse, seria usada no
    primeiro dia em que alguem quisesse um alerta "mais esperto", e a partir
    dai o corretor passa a ser acordado por palpite.
    """
    if trust_tier not in TIERS_QUE_SUSTENTAM_ALERTA_CRITICO:
        return DecisaoDePolicy(
            False, False, False,
            f"alerta crítico exige dado vivo, evento do sistema ou documento; "
            f"este sinal é Tier {trust_tier}")
    if evidencias < 1:
        return DecisaoDePolicy(False, False, False,
                               "alerta crítico sem evidência anexada")
    return DecisaoDePolicy(True, False, False, "evidência suficiente para alerta crítico")


def pode_executar_sem_humano(*, assunto: str, side_effect_class: str,
                             signal_type: Optional[str] = None,
                             confianca: float = 0.0) -> DecisaoDePolicy:
    """§30.5 e §14.3 — o que a recomendacao aceita ainda NAO autoriza."""
    alvo = (assunto or "").lower()
    if any(p in alvo for p in ASSUNTOS_DE_ALTO_RISCO):
        return DecisaoDePolicy(
            True, True, True,
            "assunto de cobertura, indenização ou obrigação legal — exige fonte "
            "oficial e uma pessoa responsável")
    if side_effect_class in EFEITOS_QUE_EXIGEM_APROVACAO:
        return DecisaoDePolicy(
            True, True, False,
            "a ação sai da plataforma ou mexe em dinheiro — passa por aprovação")
    if signal_type in TIPOS_COM_GATE_PROPRIO:
        return DecisaoDePolicy(
            True, True, False,
            "conformidade, segurança e qualidade de dado têm gate próprio")
    if confianca < 0.5:
        return DecisaoDePolicy(
            True, True, False,
            "confiança baixa demais para agir sem confirmação")
    return DecisaoDePolicy(True, False, False, "ação de leitura ou reversível")


def deve_marcar_conflito(tiers_das_fontes: list[int],
                         concordam: bool) -> DecisaoDePolicy:
    """§8.3 — fontes relevantes que se contradizem bloqueiam acao sensivel.

    A regra vale quando a divergencia e entre fontes FORTES. Um dado vivo
    contra a hipotese de um modelo nao e contradicao: e o modelo errado.
    """
    fortes = [t for t in tiers_das_fontes if t <= 2]
    if concordam or len(fortes) < 2:
        return DecisaoDePolicy(True, False, False, "sem contradição entre fontes fortes")
    return DecisaoDePolicy(
        False, True, True,
        "duas fontes confiáveis discordam — mostrar a divergência e pedir validação "
        "antes de qualquer ação")


def sensibilidade_permitida(politica_do_perfil: str, papel: str) -> bool:
    """§30.3 — dado sensivel so aparece quando o perfil E o papel permitem."""
    if politica_do_perfil == "never":
        return False
    if politica_do_perfil == "allowed_for_role":
        return papel in ("owner", "admin", "gestor", "master")
    return False  # 'redacted' e o padrao: nunca mostra bruto
