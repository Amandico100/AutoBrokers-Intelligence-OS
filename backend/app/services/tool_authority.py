"""Autoridade de tools legadas do tools_config (Onda 3 / SPEC-018 S5).

Regra: `agents.tools_config` vira toggle VISUAL por agente; a autoridade real
migra para o Registry. Com AUTHORITY_STRICT_MODE desligado (default) nada muda
(tools_config decide sozinho, comportamento legado). Ligado, a tool só anexa se
o toggle estiver ligado E a capability correspondente estiver ativa no Registry.

Puro (sem IO) para ser testável offline — o graph injeta strict/capabilities.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable

# tools_config key -> capability formal no Registry (seeds na migration 20260703_03)
LEGACY_TOOL_CAPABILITIES: Dict[str, str] = {
    "human_handoff": "platform.human_handoff",
    "csv_analytics": "platform.csv_analytics",
}


def legacy_tool_allowed(
    tool_key: str,
    tools_config: Dict[str, Any],
    active_capabilities: Iterable[str],
    *,
    strict: bool,
    capability_key: str,
) -> bool:
    entry = (tools_config or {}).get(tool_key) or {}
    enabled = bool(entry.get("enabled")) if isinstance(entry, dict) else False
    if not enabled:
        return False
    if not strict:
        return True
    return capability_key in set(active_capabilities or [])
