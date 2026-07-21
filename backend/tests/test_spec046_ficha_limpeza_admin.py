# -*- coding: utf-8 -*-
"""SPEC-046 - Ficha do Atendimento, limpeza do legado e Admin completo.

Cobre: ficha (rota Next agrega dispatch/espelho/InfoCap/dossie, sem score),
endpoint do dossie no backend, slots/reason no resumo de sessoes (funcional),
bug .sessions corrigido, entradas Fila/Historico/Segurados abrindo a ficha,
limpeza provada (rotas cases/whatsapp, runtime TS, bridge, agent_reply),
migracao graveyard e fixes do portal admin. Standalone (stubs, sem pytest).
"""

import asyncio
import importlib.util
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT.parent
PASS = FAIL = 0
FAILURES = []


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  [ok] {name}")
    else:
        FAIL += 1
        FAILURES.append((name, detail))
        print(f"  [X] {name}{': ' + str(detail) if detail else ''}")


def _load(dotted, rel):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(dotted, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = mod
    spec.loader.exec_module(mod)
    return mod


def _src(rel, base=None):
    return ((base or WEB) / rel).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
print("\n[1] Backend - slots/reason no resumo de sessoes (funcional)")

for name in ("app", "app.core", "app.services"):
    if name not in sys.modules:
        sys.modules[name] = types.ModuleType(name)

_ids = types.ModuleType("app.services.insurer_dispatch_service")
for fn in ("build_handoff_dossier", "client_summary_from_capture", "guard_human_phase_reply",
           "handle_insurer_message", "new_dispatch_session", "reply_human_phase", "start_dispatch"):
    setattr(_ids, fn, lambda *a, **k: None)
sys.modules["app.services.insurer_dispatch_service"] = _ids

_redis_mod = types.ModuleType("app.core.redis")


def _no_redis():
    raise RuntimeError("offline")


_redis_mod.get_async_redis_client = _no_redis
sys.modules["app.core.redis"] = _redis_mod

router_mod = _load("spec046_dispatch_router", "app/services/dispatch_router.py")
router_mod._memory_store.clear()
_session = {
    "case_id": "caso-1", "state": "needs_human", "subservice": "guincho",
    "playbook_ref": "allianz-assist", "client_phone": "5544999990000",
    "captured": {"protocol": "ABC123"}, "slots": {"titular_cpf": "12345678901", "veiculo_placa": "ABC1D23"},
    "reason": "ura_travou", "transcript": [], "created_at": "2026-07-20T10:00:00+00:00",
}
router_mod._memory_store["dispatch:active:comp-1:5511888887777"] = json.dumps(_session)
_sessions = asyncio.run(router_mod.list_active_dispatches("comp-1"))
check("list_active_dispatches retorna a sessao", len(_sessions) == 1, _sessions)
check("resumo inclui slots (CPF p/ InfoCap da ficha)",
      _sessions and _sessions[0].get("slots", {}).get("titular_cpf") == "12345678901")
check("resumo inclui reason (motivo do handoff)",
      _sessions and _sessions[0].get("reason") == "ura_travou")

# ---------------------------------------------------------------------------
print("\n[2] Backend - endpoint do dossie + limpeza do bridge")

_monitor = _src("app/api/dispatch_monitor.py", ROOT)
check("GET /api/dispatch/dossier existe", "/api/dispatch/dossier" in _monitor)
check("dossie usa build_handoff_dossier real (nada paralelo)",
      "build_handoff_dossier" in _monitor and "load_active_dispatch" in _monitor)
check("dossier exige chave interna", _monitor.count("_require_internal_key") >= 2)

_webhook = _src("app/api/webhook.py", ROOT)
check("bridge TS removido do webhook", "_forward_to_attendance_bridge" not in _webhook)
check("check de agente do bridge removido", "_is_attendance_agent" not in _webhook)
_config = _src("app/core/config.py", ROOT)
check("ATTENDANCE_BRIDGE_URL fora do config", "ATTENDANCE_BRIDGE_URL" not in _config)
_main = _src("app/main.py", ROOT)
check("attendance_agent_reply fora do main", "attendance_agent_reply_router" not in _main)
check("attendance_agent_reply.py apagado", not (ROOT / "app/api/attendance_agent_reply.py").exists())

# ---------------------------------------------------------------------------
print("\n[3] Ficha - rota Next agregadora")

_ficha_api = _src("app/api/dashboard/atendimentos/ficha/[id]/route.ts")
check("ficha escopa por company (sessao)", "resolveSessionCompany" in _ficha_api)
check("ficha le a chave certa do backend (.dispatches)", "?.dispatches ||" in _ficha_api)
check("ficha consulta InfoCap read-only por CPF identificado",
      "infocap/lookup" in _ficha_api and "titular_cpf" in _ficha_api)
check("ficha busca o dossie real", "/api/dispatch/dossier" in _ficha_api)
check("ficha monta linha do tempo e anexos",
      "timeline" in _ficha_api and "anexos" in _ficha_api)
check("ficha linka o espelho do acionamento", "espelho_conversa_id" in _ficha_api)
check("ficha NAO expoe score interno",
      "scorecard" not in _ficha_api and "nota_media" not in _ficha_api)

_pipeline = _src("app/api/dashboard/atendimentos/route.ts")
check("pipeline da Fila corrigido p/ .dispatches", "?.dispatches ||" in _pipeline)

# ---------------------------------------------------------------------------
print("\n[4] Ficha - pagina e entradas")

check("pagina da ficha existe",
      (WEB / "app/dashboard/atendimentos/ficha/[conversaId]/FichaClient.tsx").exists())
_ficha_ui = _src("app/dashboard/atendimentos/ficha/[conversaId]/FichaClient.tsx")
check("ficha tem acoes (conversa/assumir/dossie)",
      "Assumir atendimento" in _ficha_ui and "Copiar doss" in _ficha_ui)
_fila = _src("app/dashboard/atendimentos/fila/AttendanceQueueClient.tsx")
check("Fila abre a ficha", "/dashboard/atendimentos/ficha/" in _fila)
_hist = _src("app/dashboard/atendimentos/casos/HistoricoClient.tsx")
check("Historico abre a ficha", "/dashboard/atendimentos/ficha/" in _hist)
_seg = _src("app/dashboard/atendimentos/segurados/SeguradosClient.tsx")
check("Segurados vira perfil leve com historico -> fichas",
      "historico" in _seg and "/dashboard/atendimentos/ficha/" in _seg)
_seg_api = _src("app/api/dashboard/atendimentos/segurados/route.ts")
check("API segurados carrega historico por cliente", "historico" in _seg_api)
_mods = _src("lib/mock/tenant-modules.ts")
_atend_block = _mods.split("atendimentoAreas")[1].split("];")[0]
check("cards de Atendimentos sem selo MVP/Em breve",
      "MVP ativo" not in _atend_block and "Em breve" not in _atend_block)
check("card Historico no lugar do sandbox de Casos", "Hist" in _atend_block)

# ---------------------------------------------------------------------------
print("\n[5] Limpeza - codigo morto fora do repositorio")

_dead_paths = [
    "app/dashboard/atendimentos/casos/[caseId]",
    "app/dashboard/atendimentos/casos/CasesIndexClient.tsx",
    "app/api/attendance/cases",
    "app/api/attendance/whatsapp",
    "lib/attendance/action-engine.ts",
    "lib/attendance/corridor-runtime.ts",
    "lib/attendance/whatsapp-inbound.ts",
    "lib/attendance/runtime-llm-fallback.ts",
    "lib/attendance/handoff-dossier.ts",
    "lib/attendance/policy-qa.ts",
    "scripts/attendance-action-engine.test.mjs",
    "scripts/whatsapp-inbound.test.mjs",
    "scripts/attendance-golden-tests.mjs",
]
for p in _dead_paths:
    check(f"morto removido: {p}", not (WEB / p).exists())

_alive_paths = [
    "app/api/attendance/support-destinations/route.ts",
    "app/api/attendance/connectors/infocap/secret/route.ts",
    "lib/attendance/support-destinations.ts",
    "lib/attendance/portal-skill-runner.ts",
    "lib/attendance/portal-intake-importer.ts",
    "lib/attendance/connectors/infocap-policy-lookup.ts",
    "app/dashboard/atendimentos/casos/HistoricoClient.tsx",
]
for p in _alive_paths:
    check(f"vivo preservado: {p}", (WEB / p).exists())

_pkg = _src("package.json")
for dead_script in ("attendance-action-engine.test.mjs", "whatsapp-inbound.test.mjs",
                    "policy-qa.test.mjs", "attendance-golden-tests.mjs"):
    check(f"package.json sem {dead_script}", dead_script not in _pkg)

# ---------------------------------------------------------------------------
print("\n[6] Banco - graveyard reversivel")

_mig = _src("supabase/migrations/20260720_03_spec046_graveyard_mvp_tables.sql", ROOT)
check("migracao move attendance_cases p/ graveyard",
      "attendance_cases SET SCHEMA graveyard" in _mig)
check("migracao move corridor_runs e dispatch_packets",
      "corridor_runs SET SCHEMA graveyard" in _mig and "dispatch_packets SET SCHEMA graveyard" in _mig)
check("corridor_templates/tenant_corridors FICAM (vivas)",
      "corridor_templates SET SCHEMA" not in _mig and "tenant_corridors SET SCHEMA" not in _mig)

# ---------------------------------------------------------------------------
print("\n[7] Portal Admin - navegacao devolvida")

_layout = _src("app/admin/layout.tsx")
check("item-pai com submenu NAVEGA (Link + seta separada)",
      "flex flex-1 items-center gap-3 px-4 py-3" in _layout and "Expandir ${item.label}" in _layout)
check("subitem Empresas & Agentes -> /admin/companies",
      "Empresas & Agentes" in _layout)
_cockpit = _src("app/admin/corretoras/page.tsx")
check("Cockpit tem Configuracao completa -> companies/[id]/agents",
      "Configura" in _cockpit and "/agents" in _cockpit)
_agents_page = _src("app/admin/companies/[companyId]/agents/page.tsx")
check("tela de agentes com titulo claro de configuracao completa",
      "Configura" in _agents_page and "corretora" in _agents_page)

# ---------------------------------------------------------------------------
print(f"\n{'=' * 60}")
print(f"RESULTADO: {PASS} ok, {FAIL} falhas")
for name, detail in FAILURES:
    print(f"  FALHOU: {name} {detail}")
sys.exit(1 if FAIL else 0)
