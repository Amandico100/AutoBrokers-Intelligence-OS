"""SPEC-018 S1 - Prompt Efetivo (diagnóstico read-only de autoridade).

Rodar: python backend/tests/test_spec018_authority.py
Offline, dados sintéticos, sem banco/rede.
"""

import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASS = 0
FAIL = 0
FAILURES = []


def check(name, cond, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [ok] {name}")
    else:
        FAIL += 1
        FAILURES.append((name, detail))
        print(f"  [X] {name}{': ' + str(detail) if detail else ''}")


for name in ("app", "app.services"):
    m = sys.modules.setdefault(name, types.ModuleType(name))
    m.__path__ = []

spec = importlib.util.spec_from_file_location(
    "app.services.prompt_effective_service", ROOT / "app/services/prompt_effective_service.py"
)
pe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pe)


def run():
    print("== SPEC-018 S1 - Prompt Efetivo ==\n")
    agent = {
        "id": "ag-1",
        "agent_role": "core",
        "agent_system_prompt": "Instruções secretas do cliente com detalhes.",
        "allow_web_search": True,
        "tools_config": {"human_handoff": {"enabled": True}, "csv_analytics": {"enabled": False}},
    }
    caps = {
        "platform.web.search": {"status": "active", "reason": "ok"},
        "operational.infocap.policy_lookup.read": {"status": "active", "reason": "ok"},
        "tenant.google_drive.read": {"status": "needs_connection", "reason": "aguardando conexão"},
    }
    out = pe.build_prompt_effective(
        agent=agent, company_config={}, resolved_capabilities=caps,
        http_tools=[{"name": "cotador", "is_active": True}], mcp_tools=[{"tool_name": "drive_read"}],
        delegations_count=2,
    )
    check("S1: read_only sempre", out["read_only"] is True)
    check("S1: prompt do cliente REDIGIDO (nunca cru)", "Instruções secretas" not in str(out) and out["prompt_layers"][1]["present"] is True and out["prompt_layers"][1]["chars"] > 0, out["prompt_layers"][1])
    tools = {t["tool"]: t for t in out["bound_tools"]}
    check("S1: web ativa por capability", tools["web_search"]["active"] is True)
    check("S1: infocap com exposição por papel", tools["infocap_policy_lookup"]["role_exposure"] == "completo")
    check("S1: handoff marcado como autorização LEGADA", "LEGADO" in tools["request_human_agent"]["authority"] and tools["request_human_agent"]["active"] is True)
    check("S1: http/mcp marcados sem capability", tools["http_api"]["divergence"] and tools["mcp_tools"]["divergence"])
    check("S1: divergência de capability sem conexão listada", any("google_drive" in d for d in out["divergences"]), out["divergences"])
    check("S1: subagentes contados", tools["delegate_to_subagent"]["count"] == 2)

    # Papel attendance: dispatch ativo, infocap mascarado, RAG global incluso.
    out2 = pe.build_prompt_effective(
        agent={"id": "ag-2", "agent_role": "attendance", "tools_config": {}},
        company_config={}, resolved_capabilities={}, http_tools=[], mcp_tools=[],
    )
    t2 = {t["tool"]: t for t in out2["bound_tools"]}
    check("S1: attendance tem insurer_dispatch", t2["insurer_dispatch"]["active"] is True)
    check("S1: attendance infocap mascarado", t2["infocap_policy_lookup"]["role_exposure"] == "mascarado")
    check("S1: attendance RAG privado+global", out2["rag_scope"] == "privado + global curado")
    check("S1: camada 1 = ATTENDANCE_BASE_PROMPT", "ATTENDANCE" in out2["prompt_layers"][0]["source"])

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        sys.exit(1)


if __name__ == "__main__":
    run()
