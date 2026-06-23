"""SPEC-014 C-FIX-1 — testes do capability_resolver (offline, sem deps externas).

Carrega o módulo por caminho, com app.core.config stubado (evita pydantic_settings).
Usa um cliente Supabase fake (cadeia table().select().eq()/in_().execute()).
"""
import importlib.util
import sys
import types
from pathlib import Path

# --- stub app.core.config.settings antes de carregar o módulo ---
_settings = types.SimpleNamespace(TAVILY_API_KEY="tvly-test", DOCLING_SERVICE_URL="http://docling:8001")
for name in ("app", "app.core", "app.core.config"):
    if name not in sys.modules:
        sys.modules[name] = types.ModuleType(name)
sys.modules["app.core.config"].settings = _settings

_path = Path(__file__).resolve().parents[1] / "app" / "agents" / "capability_resolver.py"
_spec = importlib.util.spec_from_file_location("capability_resolver", _path)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

resolve_active_capabilities = mod.resolve_active_capabilities
active_keys = mod.active_keys


# --- fake supabase client ---
class _Resp:
    def __init__(self, data): self.data = data

class _Table:
    def __init__(self, store, name): self.store, self.name, self.f = store, name, {}
    def select(self, *a, **k): return self
    def eq(self, k, v): self.f[k] = ("eq", v); return self
    def in_(self, k, v): self.f[k] = ("in", v); return self
    def execute(self):
        out = []
        for r in self.store.get(self.name, []):
            ok = True
            for fk, (op, fv) in self.f.items():
                if op == "in" and r.get(fk) not in fv: ok = False
                if op == "eq" and r.get(fk) != fv: ok = False
            if ok: out.append(r)
        return _Resp(out)

class _Client:
    def __init__(self, store): self.store = store
    def table(self, name): return _Table(self.store, name)


def _store(*, infocap_connected=True, web_disabled=False):
    caps = [
        {"capability_key": "platform.web.search", "is_active": True, "owner": "platform", "requires_connection": False, "provider": "tavily"},
        {"capability_key": "control_plane.read", "is_active": True, "owner": "platform", "requires_connection": False, "provider": None},
        {"capability_key": "knowledge.global.search", "is_active": True, "owner": "platform", "requires_connection": False, "provider": "rag"},
        {"capability_key": "operational.infocap.policy_lookup.read", "is_active": True, "owner": "operational", "requires_connection": True, "provider": "infocap"},
    ]
    bindings = [
        {"capability_key": "platform.web.search", "agent_role": "core", "enabled": True},
        {"capability_key": "control_plane.read", "agent_role": "core", "enabled": True},
        {"capability_key": "knowledge.global.search", "agent_role": "core", "enabled": True},
        {"capability_key": "operational.infocap.policy_lookup.read", "agent_role": "core", "enabled": True},
        # attendance: SEM web search
        {"capability_key": "operational.infocap.policy_lookup.read", "agent_role": "attendance", "enabled": True},
        {"capability_key": "control_plane.read", "agent_role": "attendance", "enabled": True},
    ]
    ents = []
    if web_disabled:
        ents.append({"company_id": "c1", "capability_key": "platform.web.search", "enabled": False})
    conns = []
    if infocap_connected:
        conns.append({"company_id": "c1", "status": "connected", "connector_templates": {"slug": "infocap"}})
    return {"capabilities": caps, "capability_bindings": bindings, "tenant_capability_entitlements": ents, "tenant_connections": conns}


p = 0; f = 0; fails = []
def chk(n, c):
    global p, f
    if c: p += 1; print(f"  [ok] {n}")
    else: f += 1; fails.append(n); print(f"  [X] {n}")

print("== SPEC-014 C-FIX-1 - capability_resolver ==\n")
_settings.TAVILY_API_KEY = "tvly-test"

# Core completo
r = resolve_active_capabilities(_Client(_store()), "c1", "core")
ak = active_keys(r)
chk("core: web.search ativa (binding+tavily)", "platform.web.search" in ak)
chk("core: control_plane ativa", "control_plane.read" in ak)
chk("core: infocap ativa quando conectado", "operational.infocap.policy_lookup.read" in ak)

# Core sem conexão infocap
r2 = resolve_active_capabilities(_Client(_store(infocap_connected=False)), "c1", "core")
chk("core: infocap needs_connection sem conexão", r2["operational.infocap.policy_lookup.read"]["status"] == "needs_connection")
chk("core: infocap NÃO ativa sem conexão", "operational.infocap.policy_lookup.read" not in active_keys(r2))

# Papel vazio/inválido => nada
chk("role vazio => {} (sem privilégio)", resolve_active_capabilities(_Client(_store()), "c1", "") == {})
chk("role inválido => {}", resolve_active_capabilities(_Client(_store()), "c1", "qualquer") == {})

# Attendance NÃO tem web search
ra = resolve_active_capabilities(_Client(_store()), "c1", "attendance")
chk("attendance: sem web.search (fora do binding)", "platform.web.search" not in ra)
chk("attendance: infocap ativa quando conectado", "operational.infocap.policy_lookup.read" in active_keys(ra))

# Entitlement desligado
rd = resolve_active_capabilities(_Client(_store(web_disabled=True)), "c1", "core")
chk("core: web.search disabled por entitlement", rd["platform.web.search"]["status"] == "disabled")

# Tavily ausente => provider_unavailable
_settings.TAVILY_API_KEY = None
rn = resolve_active_capabilities(_Client(_store()), "c1", "core")
chk("core: web.search provider_unavailable sem TAVILY", rn["platform.web.search"]["status"] == "provider_unavailable")
_settings.TAVILY_API_KEY = "tvly-test"

print(f"\n== Resumo: {p} passaram, {f} falharam ==")
if f: [print(f"  - {x}") for x in fails]; sys.exit(1)
sys.exit(0)
