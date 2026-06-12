"""
Context Package (SPEC-004 / 42A6) — camada declarativa de papel do agente.

Funções puras e seguras que leem campos declarativos do agente
(agent_role, agent_audience, blueprint_version, context_package) e montam um
bloco COMPACTO para complementar o Context Assembly do Smith.

Garantias:
- Não substitui agent_system_prompt — apenas complementa.
- Nunca gera prompt gigante (cap por campo e cap total).
- Só renderiza chaves de política conhecidas (whitelist) → nunca inclui
  documentos, chunks, tokens, segredos ou PII que estejam em chaves arbitrárias.
- Backward-compatible: agente sem context_package → bloco vazio, nada muda.
- Sem I/O, sem dependências do runtime.
"""

from typing import Any, Dict

# Chaves de política renderizáveis (SPEC-004 §4.2 / 42A2 §4). Ordem estável.
# Qualquer chave fora desta whitelist é IGNORADA (segurança anti-bloat/anti-vazamento).
_POLICY_KEYS = (
    "mission",
    "non_goals",
    "rag_policy",
    "memory_policy",
    "tools_policy",
    "handoff_policy",
    "approval_policy",
    "output_contract",
)

_MAX_FIELD_CHARS = 400   # cap por campo
_MAX_BLOCK_CHARS = 2400  # cap total do bloco (robustez anti prompt-gigante)


def get_agent_field(agent: Any, field: str, default: Any = None) -> Any:
    """Lê um campo do agente seja ele dict (model_dump) ou objeto pydantic."""
    if agent is None:
        return default
    if isinstance(agent, dict):
        val = agent.get(field, default)
    else:
        val = getattr(agent, field, default)
    return val if val is not None else default


def normalize_context_package(agent: Any) -> Dict[str, Any]:
    """Retorna o context_package como dict; {} se ausente ou tipo inválido."""
    cp = get_agent_field(agent, "context_package", None)
    if isinstance(cp, dict):
        return cp
    return {}


def _compact_scalar(value: Any) -> str:
    """Colapsa espaços/quebras e trunca para manter o bloco compacto."""
    text = " ".join(str(value).split())
    if len(text) > _MAX_FIELD_CHARS:
        text = text[:_MAX_FIELD_CHARS].rstrip() + "…"
    return text


def _compact_value(value: Any) -> str:
    """Renderiza str/list/dict de política de forma compacta e em uma linha."""
    if isinstance(value, (list, tuple)):
        parts = [" ".join(str(v).split()) for v in value if v is not None and str(v).strip()]
        return _compact_scalar("; ".join(parts))
    if isinstance(value, dict):
        parts = [
            f"{k}={' '.join(str(v).split())}"
            for k, v in value.items()
            if v is not None and str(v).strip()
        ]
        return _compact_scalar("; ".join(parts))
    return _compact_scalar(value)


def should_render_context_package(agent: Any) -> bool:
    """True se há algo declarativo para renderizar (papel ou pacote)."""
    if get_agent_field(agent, "agent_role"):
        return True
    if get_agent_field(agent, "agent_audience"):
        return True
    if get_agent_field(agent, "blueprint_version"):
        return True
    return bool(normalize_context_package(agent))


def render_context_package_block(agent: Any) -> str:
    """
    Monta o bloco [CONTEXT PACKAGE] compacto. Retorna "" quando não há nada
    para renderizar (agente sem campos declarativos).
    """
    if not should_render_context_package(agent):
        return ""

    role = get_agent_field(agent, "agent_role")
    audience = get_agent_field(agent, "agent_audience")
    version = get_agent_field(agent, "blueprint_version")
    cp = normalize_context_package(agent)

    lines = ["[CONTEXT PACKAGE]"]
    if role:
        lines.append(f"role: {_compact_scalar(role)}")
    if audience:
        lines.append(f"audience: {_compact_scalar(audience)}")
    if version:
        lines.append(f"blueprint_version: {_compact_scalar(version)}")

    for key in _POLICY_KEYS:
        value = cp.get(key)
        if value is not None and str(value).strip():
            lines.append(f"{key}: {_compact_value(value)}")

    block = "\n".join(lines)
    if len(block) > _MAX_BLOCK_CHARS:
        block = block[:_MAX_BLOCK_CHARS].rstrip() + "…"
    return block
