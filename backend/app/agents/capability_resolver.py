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
    # SPEC-064 Bloco H — quem entra no portal da seguradora é o `portal_worker`.
    # `portal_browser` continua aqui de propósito: expand-first. O código aceita
    # os dois enquanto a migration 064_07 não roda, e o rollback dela não
    # quebra nada. O simulador some do repositório; o mapa some depois.
    "portal_worker": ["insurance_portal"],
    "portal_browser": ["insurance_portal", "browserbase"],
}

_HEALTHY_CONN = {"connected", "active", "healthy"}

# Providers cuja conexão NÃO mora em `tenant_connections`.
#
# 📊 Medido em 02/08/2026: `tenant_connections` nunca teve uma linha de portal.
# A única conta de portal do sistema é a da Resulta na Allianz — e ela vive em
# `portal_accounts`, com credencial, desde 08/07.
#
# Sem esta ponte, as cinco capabilities de portal resolviam `needs_connection`
# para TODAS as corretoras, inclusive a que tem o portal funcionando e baixando
# boleto. O registro dizia "bloqueado" sobre uma coisa que estava rodando — o
# que não protege nada e ainda garante que, no dia em que alguém ligar a
# checagem, o Cobrador para sem ninguém entender por quê.
CONEXAO_EM_PORTAL_ACCOUNTS = {"portal_worker", "portal_browser"}


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
        # SPEC-054 Bloco C: o `scope` passa a ser LIDO. Antes o campo existia,
        # estava vazio em todos os 46 bindings e era ignorado pelo resolver —
        # ou seja, "capability ligada" significava acesso irrestrito.
        bindings = (c.table("capability_bindings").select("capability_key, enabled, scope").eq("agent_role", role).execute().data) or []
        allowed = {b["capability_key"] for b in bindings if b.get("enabled", True)}
        scopes: Dict[str, Dict[str, Any]] = {
            b["capability_key"]: (b.get("scope") or {})
            for b in bindings if b.get("enabled", True)
        }
        if not allowed:
            return {}
        caps = (c.table("capabilities").select("capability_key, is_active, owner, requires_connection, provider, risk").in_("capability_key", list(allowed)).execute().data) or []
        ents = (c.table("tenant_capability_entitlements").select("capability_key, enabled").eq("company_id", company_id).execute().data) or []
        conns = (c.table("tenant_connections").select("status, connector_templates(slug)").eq("company_id", company_id).execute().data) or []
        # SPEC-064 Bloco H — a conexão de portal mora aqui, não em
        # `tenant_connections`. Ver CONEXAO_EM_PORTAL_ACCOUNTS.
        portais = (c.table("portal_accounts").select("portal_key, health").eq("company_id", company_id).execute().data) or []
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

    # Uma conta de portal com credencial satisfaz `insurance_portal`.
    #
    # `health` nasce 'unknown' e só vira 'failing' depois de uma falha real —
    # tratar 'unknown' como desconectado negaria a capacidade justamente da
    # corretora que acabou de cadastrar a conta e ainda não rodou nada.
    if any(str(p.get("health") or "").lower() != "failing" for p in portais):
        connected.add("insurance_portal")

    out: Dict[str, Dict[str, Any]] = {}
    for cap in caps:
        key = cap["capability_key"]
        scope = scopes.get(key) or {}
        if not cap.get("is_active", True):
            out[key] = {"status": "disabled", "reason": "capability inativa", "scope": scope}; continue
        if key in ent_disabled:
            out[key] = {"status": "disabled", "reason": "desligada pela corretora", "scope": scope}; continue
        if cap.get("requires_connection"):
            slugs = PROVIDER_SLUGS.get(cap.get("provider") or "", [])
            if not any(s in connected for s in slugs):
                out[key] = {"status": "needs_connection", "reason": "aguardando conexão da corretora", "scope": scope}; continue
        health = _provider_healthy(cap.get("provider"))
        if health is False:
            out[key] = {"status": "provider_unavailable", "reason": "provider indisponível (config ausente)", "scope": scope}; continue

        # SPEC-054 Bloco C — scope vazio em capability sensível NÃO é liberado.
        # A ausência de escopo declarado passa a ser tratada como configuração
        # incompleta, não como permissão total. Fail-closed por design.
        if str(cap.get("risk") or "").lower() == "high" and not scope:
            logger.warning("[CapabilityResolver] scope ausente em capability HIGH '%s' — negando", key)
            out[key] = {"status": "scope_missing", "reason": "escopo não declarado para capability de alto risco", "scope": {}}
            continue

        out[key] = {"status": "active", "reason": "ok", "scope": scope}
    return out


def active_keys(resolved: Dict[str, Dict[str, Any]]) -> Set[str]:
    return {k for k, v in resolved.items() if v.get("status") == "active"}


def scope_of(resolved: Dict[str, Dict[str, Any]], capability_key: str) -> Dict[str, Any]:
    """Escopo declarado de uma capability ativa. `{}` quando ausente."""
    entry = resolved.get(capability_key) or {}
    return entry.get("scope") or {}


def requires_approval(resolved: Dict[str, Dict[str, Any]], capability_key: str) -> bool:
    """True quando o escopo declara aprovação humana obrigatória.

    É o contrato que a SPEC-055 vai consumir para transformar approval em gate
    executável. Aqui ele já fica disponível e auditável.
    """
    return bool(scope_of(resolved, capability_key).get("requires_approval"))


def has_side_effect(resolved: Dict[str, Dict[str, Any]], capability_key: str) -> bool:
    """True quando a capability produz efeito externo — exige idempotência."""
    return bool(scope_of(resolved, capability_key).get("side_effect"))


def max_calls_per_run(resolved: Dict[str, Dict[str, Any]], capability_key: str, default: int = 20) -> int:
    try:
        return int(scope_of(resolved, capability_key).get("max_calls_per_run") or default)
    except (TypeError, ValueError):
        return default
