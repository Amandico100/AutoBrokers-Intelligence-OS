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


def mcp_capability_key(server_name: str) -> str:
    """Capability formal de um servidor MCP: tenant.mcp.<server> (hífen vira _)."""
    return f"tenant.mcp.{str(server_name or '').strip().lower().replace('-', '_')}"


def filter_mcp_tools_by_capability(
    mcp_tools_config: list,
    active_capabilities: Iterable[str],
    *,
    strict: bool,
) -> list:
    """SPEC-018 S3: em modo estrito, só passam tools de servidores MCP cuja
    capability tenant.mcp.<server> está ativa. Flag OFF = lista intacta."""
    if not strict:
        return list(mcp_tools_config or [])
    active = set(active_capabilities or [])
    allowed = []
    for row in mcp_tools_config or []:
        server = (row or {}).get("mcp_server_name")
        if server and mcp_capability_key(server) in active:
            allowed.append(row)
    return allowed


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
