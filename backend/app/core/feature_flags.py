"""Feature flags da plataforma (somente leitura de ambiente, sem dependências).

POLICY_INTELLIGENCE_V2 — SPEC-016. OFF (default) = comportamento do baseline
e7c5044; ON = contexto anafórico v2 + Policy Facts + política de assistência +
compositor humano. Flag única de rollback da Onda 1.
"""

import os

_TRUTHY = {"1", "true", "yes", "on"}


def policy_intelligence_v2_enabled() -> bool:
    return str(os.getenv("POLICY_INTELLIGENCE_V2", "")).strip().lower() in _TRUTHY
