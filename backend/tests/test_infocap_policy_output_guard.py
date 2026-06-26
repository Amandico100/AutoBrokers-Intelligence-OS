"""R1B.2 - Policy Response Contract / Smith output guard tests.

Offline only. No provider, no Supabase, no Vault, no payload real.
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


def _load_nodes_module():
    for name in ("app", "app.agents", "app.core"):
        module = sys.modules.setdefault(name, types.ModuleType(name))
        if name in ("app", "app.agents"):
            module.__path__ = []  # mark as package for relative imports

    constants = types.ModuleType("app.core.constants")
    constants.AGENT_CONTEXT_WINDOW_SIZE = 15
    sys.modules["app.core.constants"] = constants

    state = types.ModuleType("app.agents.state")
    state.AgentState = dict
    sys.modules["app.agents.state"] = state

    utils = types.ModuleType("app.agents.utils")
    utils.extract_text_from_content = lambda content: content if isinstance(content, str) else str(content or "")
    utils.sanitize_ai_message = lambda msg: msg
    sys.modules["app.agents.utils"] = utils

    context = types.ModuleType("app.agents.context")
    context.build_task_context = lambda state, max_chars=2000: ""
    sys.modules["app.agents.context"] = context

    runnables = types.ModuleType("langchain_core.runnables")
    runnables.RunnableConfig = dict
    sys.modules["langchain_core.runnables"] = runnables

    messages = types.ModuleType("langchain_core.messages")

    class _Msg:
        def __init__(self, content="", **kwargs):
            self.content = content
            for key, value in kwargs.items():
                setattr(self, key, value)

    messages.AIMessage = _Msg
    messages.HumanMessage = _Msg
    messages.SystemMessage = _Msg
    messages.ToolMessage = _Msg
    sys.modules["langchain_core.messages"] = messages

    path = ROOT / "app" / "agents" / "nodes.py"
    spec = importlib.util.spec_from_file_location("app.agents.nodes", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run():
    print("== R1B.2 - InfoCap policy output guard ==\n")
    nodes = _load_nodes_module()

    guard = getattr(nodes, "_guard_infocap_policy_final_response", None)
    route = getattr(nodes, "should_continue_after_tools", None)
    check("output guard helper exists", callable(guard))
    check("tool-to-final routing helper exists", callable(route))
    if not callable(guard) or not callable(route):
        return

    ambiguous_contract = {
        "provider": "infocap",
        "result_kind": "ambiguous_policy",
        "rendered_safe_answer": (
            "Encontrei mais de uma apolice para esse segurado.\n"
            "1. Seguradora: ALLI; Produto/ramo: RESI; Vigencia: 05/06/2026 a 05/06/2027; "
            "Status: ativo; Numero: POL-2026-0001.\n"
            "Escolha pelo numero humano da apolice."
        ),
        "required_facts": ["policy_options"],
    }
    bad_text = "Nao consegui obter os detalhes das coberturas por um erro tecnico."
    guarded = guard(bad_text, ambiguous_contract)
    check("LLM cannot erase ambiguous policy options", "POL-2026-0001" in guarded and "erro tecnico" not in guarded.lower(), guarded)

    source_contract = {
        "provider": "infocap",
        "result_kind": "found",
        "coverage_evidence_status": "structured_coverage_absent",
        "rendered_safe_answer": (
            "A InfoCap confirmou a apolice e seus dados operacionais, mas nao retornou itens estruturados "
            "de cobertura, franquia ou assistencia nesta consulta. Nao vou concluir cobertura sem essa evidencia."
        ),
        "required_facts": ["coverage_absent"],
    }
    guarded = guard("Houve erro tecnico, tente de novo mais tarde.", source_contract)
    check("LLM cannot turn coverage absence into technical error", "nao retornou itens estruturados" in guarded.lower() and "erro tecnico" not in guarded.lower(), guarded)

    document_contract = {
        "provider": "infocap",
        "result_kind": "found",
        "coverage_evidence_status": "official_document_evidence_available",
        "rendered_safe_answer": (
            "A apolice oficial foi processada e trouxe evidencia documental.\n"
            "Pagina 3 [coverage]: Cobertura Danos Eletricos - Limite R$ 5.000."
        ),
        "required_facts": ["document_evidence"],
    }
    guarded = guard("A apolice possui cobertura, mas nao sei a pagina.", document_contract)
    check(
        "LLM cannot erase document evidence pages",
        "Pagina 3" in guarded and "Danos Eletricos" in guarded,
        guarded,
    )

    mismatch_contract = {
        "provider": "infocap",
        "result_kind": "identity_mismatch",
        "rendered_safe_answer": "A identidade da apolice nao foi confirmada. Por seguranca, nao vou exibir detalhes, cobertura, parcelas ou documento dessa consulta.",
        "required_facts": ["identity_mismatch"],
    }
    guarded = guard("Seguradora: Alfa. Produto: Condominio. Cobertura...", mismatch_contract)
    check("LLM cannot expose details after identity_mismatch", "identidade da apolice" in guarded.lower() and "Alfa" not in guarded, guarded)

    context_builder = getattr(nodes, "_safe_infocap_policy_context", None)
    context_args = getattr(nodes, "_policy_context_tool_args", None)
    check("safe InfoCap policy context helper exists", callable(context_builder))
    check("policy context tool args helper exists", callable(context_args))
    if callable(context_builder) and callable(context_args):
        context = context_builder({
            "client_document": "11122233344",
            "client_name": "Cliente Teste",
            "matches": [
                {"policy_number": "202623140269982", "policy_locator_ref": "infocap:1:N1"},
                {"policy_number": "0", "policy_locator_ref": "infocap:1:N0"},
            ],
        })
        raw_context = str(context)
        check("safe context stores human number", context and "202623140269982" in context.get("policy_numbers", []), context)
        check("safe context does not store locator", "infocap:" not in raw_context and "N1" not in raw_context, context)
        args = context_args("Detalhe a apolice 202623140269982", context)
        raw_args = str(args)
        check("policy context routes follow-up with customer and number", args and args.get("policy_number") == "202623140269982" and args.get("document") == "11122233344", args)
        check("policy context args do not expose locator", "infocap:" not in raw_args and "N1" not in raw_args, args)

    check("tool final response routes directly to end", route({"final_response": "ok", "policy_response_contract": source_contract}) == "end")
    check("non-policy tools still return to agent", route({"final_response": "", "policy_response_contract": None}) == "agent")


if __name__ == "__main__":
    run()
    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAIL:
        for name, detail in FAILURES:
            print(f"  - {name}{': ' + str(detail) if detail else ''}")
        sys.exit(1)
    sys.exit(0)
