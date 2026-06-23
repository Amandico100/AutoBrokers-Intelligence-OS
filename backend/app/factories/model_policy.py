"""SPEC-013 FB-1 — política de modelo do Chat Principal (Core).

O Chat Principal (Core) é o braço direito do corretor: NÃO deve ser engessado por um
modelo econômico. Esta política SOBE o teto do Core para um modelo mais forte (temporário,
configurável via env CORE_CHAT_MODEL) quando o agente está no perfil econômico. Atendimento
(Even) e Auxiliares mantêm o modelo configurado — só o Core é promovido.

Puro (sem deps externas) para ser testável offline.
"""
import os

# Perfis econômicos que devem ser promovidos para o Core.
ECONOMY_MODELS = {
    "gpt-4o-mini",
    "gpt-4o-mini-2024-07-18",
    "gpt-3.5-turbo",
    "gpt-4.1-mini",
}

# Modelo forte com bom custo-benefício (default temporário; trocável por env).
DEFAULT_CORE_MODEL = "gpt-4o"


def is_core_chat_role(agent_role) -> bool:
    """Core = role 'core' ou legado/sem papel (chat principal interno)."""
    return str(agent_role or "").strip().lower() in ("", "core")


def resolve_chat_model(agent_role, configured_model):
    """Retorna o modelo efetivo. Promove o Core quando estiver no perfil econômico.
    Demais papéis mantêm o modelo configurado (sem alteração, sem engessar)."""
    if is_core_chat_role(agent_role):
        if (not configured_model) or configured_model in ECONOMY_MODELS:
            return os.getenv("CORE_CHAT_MODEL", DEFAULT_CORE_MODEL)
    return configured_model
