"""
Capability Resolver (SPEC-014 C-FIX-1) — fonte ÚNICA de verdade no runtime.

Resolve, a partir do banco (capabilities / capability_bindings / tenant_capability_entitlements)
+ papel do agente + estado de conexão + saúde do provider, QUAIS capabilities estão realmente
ATIVAS para um agente daquela corretora. O graph.py usa isto para anexar/bloquear tools —
nada de flag solta, nada de "ligado" que o runtime não executa.

Regras canônicas:
  - platform-owned (sem conexão): ativa se capability.is_active + binding(role).enabled + provider saudável.
  - tenant-owned / operational: exige também conexão saudável da corretora (e entitlement não desligado).
  - agent_role vazio/inválido NÃO recebe nenhuma capability privilegiada.
Defensivo: erro de banco => fail-closed (sem capability privilegiada), logado.
"""

import logging
from typing import Any, Dict, Optional, Set

from app.core.config import settings

logger = logging.getLogger(__name__)

VALID_ROLES = {"core", "attendance", "auxiliary", "subagent"}

# provider da capability -> slug(s) de connector_template (Vault). Mesmo mapa do cockpit (TS).
PROVIDER_SLUGS: Dict[str, list] = {
    "infocap": ["infocap"],
    "zapi": ["zapi", "whatsapp"],
    "mcp:google-drive": ["google_drive"],
    "mcp:google-calendar": ["google_calendar"],
    "mcp:slack": ["slack"],
    "notion": ["notion"],
    "portal_browser": ["insurance_portal", "browserbase"],
}

_HEALTHY_CONN = {"connected", "active", "healthy"}


def _provider_healthy(provider: Optional[str]) -> Optional[bool]:
    """Saúde de provider platform-owned (env). None = não aplicável (não bloqueia)."""
    if provider == "tavily":
        return bool(getattr(settings, "TAVILY_API_KEY", None))
    if provider == "docling":
        return bool(getattr(settings, "DOCLING_SERVICE_URL", None))
    return None


def resolve_active_capabilities(supabase_client: Any, company_id: str, agent_role: Optional[str]) -> Dict[str, Dict[str, str]]:
    """Retorna {capability_key: {status, reason}} para o papel/corretora. Só keys do papel."""
    role = str(agent_role or "").strip().lower()
    if role not in VALID_ROLES:
        return {}  # papel vazio/inválido: nenhuma capability privilegiada

    c = getattr(supabase_client, "client", supabase_client)
    try:
        bindings = (c.table("capability_bindings").select("capability_key, enabled").eq("agent_role", role).execute().data) or []
        allowed = {b["capability_key"] for b in bindings if b.get("enabled", True)}
        if not allowed:
            return {}
        caps = (c.table("capabilities").select("capability_key, is_active, owner, requires_connection, provider").in_("capability_key", list(allowed)).execute().data) or []
        ents = (c.table("tenant_capability_entitlements").select("capability_key, enabled").eq("company_id", company_id).execute().data) or []
        conns = (c.table("tenant_connections").select("status, connector_templates(slug)").eq("company_id", company_id).execute().data) or []
    except Exception as e:  # noqa: BLE001 — fail-closed
        logger.warning(f"[CapabilityResolver] fail-closed (erro de banco): {type(e).__name__}: {e}")
        return {}

    ent_disabled = {e["capability_key"] for e in ents if e.get("enabled") is False}
    connected: Set[str] = set()
    for cn in conns:
        rel = cn.get("connector_templates")
        slug = (rel or {}).get("slug") if isinstance(rel, dict) else None
        if slug and str(cn.get("status", "")).lower() in _HEALTHY_CONN:
            connected.add(str(slug))

    out: Dict[str, Dict[str, str]] = {}
    for cap in caps:
        key = cap["capability_key"]
        if not cap.get("is_active", True):
            out[key] = {"status": "disabled", "reason": "capability inativa"}; continue
        if key in ent_disabled:
            out[key] = {"status": "disabled", "reason": "desligada pela corretora"}; continue
        if cap.get("requires_connection"):
            slugs = PROVIDER_SLUGS.get(cap.get("provider") or "", [])
            if not any(s in connected for s in slugs):
                out[key] = {"status": "needs_connection", "reason": "aguardando conexão da corretora"}; continue
        health = _provider_healthy(cap.get("provider"))
        if health is False:
            out[key] = {"status": "provider_unavailable", "reason": "provider indisponível (config ausente)"}; continue
        out[key] = {"status": "active", "reason": "ok"}
    return out


def active_keys(resolved: Dict[str, Dict[str, str]]) -> Set[str]:
    return {k for k, v in resolved.items() if v.get("status") == "active"}
