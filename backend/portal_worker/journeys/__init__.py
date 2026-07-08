"""Contrato das journeys do portal-worker (SPEC-020).

Journey = função async `run(page, params, evidence) -> JourneyResult`, código
versionado por portal. O worker só executa a journey determinística; a DECISÃO
de negócio fica no Smith (cérebro único, regra inviolável).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

VALID_STATUS = ("done", "needs_human", "failed")


@dataclass
class JourneyResult:
    status: str  # done | needs_human | failed
    captured: Dict[str, Any] = field(default_factory=dict)
    screenshots: List[str] = field(default_factory=list)
    message: str = ""


def get_journey(portal_key: str, journey: str) -> Optional[Callable[..., Awaitable["JourneyResult"]]]:
    """Resolve a journey por 'portal_key.journey' (import tardio p/ não puxar Playwright à toa)."""
    key = f"{portal_key}.{journey}"
    if key == "allianz_corretor.login_check":
        from portal_worker.journeys.allianz_corretor import login_check

        return login_check
    if key == "vidros_lanternas.login_check":
        from portal_worker.journeys.vidros_lanternas import login_check

        return login_check
    if key == "vidros_lanternas.abrir_atendimento":
        from portal_worker.journeys.vidros_lanternas import abrir_atendimento

        return abrir_atendimento
    return None
