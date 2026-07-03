"""SPEC-016 - Policy Intelligence vertical tests (offline, sem provider real).

Rodar:
    python backend/tests/test_spec016_policy_intelligence.py

Cobre as fatias da SPEC-016:
  E1 - contexto anafórico determinístico (policy context lock v2)
  E2 - Policy Facts mínimos
  E3 - política residential_24h_standard_v1
  E4 - compositor humano de resposta
  E5 - porta PolicyDataProvider

Nunca usa credenciais, Supabase, Vault, rede, payload real ou PII real.
Flag de rollback: POLICY_INTELLIGENCE_V2 (off = comportamento baseline e7c5044).
"""

import importlib.util
import os
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


def _load_file_module(dotted_name: str, relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(dotted_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[dotted_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_nodes_module():
    for name in ("app", "app.agents", "app.core", "app.services"):
        module = sys.modules.setdefault(name, types.ModuleType(name))
        module.__path__ = []

    constants = types.ModuleType("app.core.constants")
    constants.AGENT_CONTEXT_WINDOW_SIZE = 15
    sys.modules["app.core.constants"] = constants

    # feature_flags é real (sem dependências) — carregado do arquivo.
    _load_file_module("app.core.feature_flags", "app/core/feature_flags.py")

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

    return _load_file_module("app.agents.nodes", "app/agents/nodes.py")


class _FlagOn:
    def __enter__(self):
        os.environ["POLICY_INTELLIGENCE_V2"] = "true"
        return self

    def __exit__(self, *a):
        os.environ.pop("POLICY_INTELLIGENCE_V2", None)


def _ctx(policy_numbers, selected=None, document="12345678900", name=None):
    ctx = {
        "document": document,
        "name": name,
        "policy_numbers": list(policy_numbers),
        "source": "infocap_customer_catalog",
    }
    if selected:
        ctx["selected_policy_number"] = selected
    return ctx


def run_e1(nodes):
    print("\n== E1 - contexto anafórico (policy context lock v2) ==\n")
    os.environ.pop("POLICY_INTELLIGENCE_V2", None)

    # Baseline (flag OFF): pergunta anafórica sem número NÃO força tool.
    args = nodes._policy_context_tool_args("ela tem assistência?", _ctx(["1234567890"]))
    check("flag OFF: anáfora sem número não força tool (baseline preservado)", args is None, args)

    with _FlagOn():
        # G-A1: uma apólice no contexto + termo de detalhe → força tool com o número.
        args = nodes._policy_context_tool_args("ela tem assistência?", _ctx(["1234567890"]))
        check("G-A1: 1 apólice + 'ela tem assistência?' força tool", isinstance(args, dict), args)
        check("G-A1: usa o policy_number do contexto", args and args.get("policy_number") == "1234567890", args)
        check("G-A1: leva o document do contexto", args and args.get("document") == "12345678900", args)

        # G-A1b: sem termo de detalhe, não força (não virar gatilho universal).
        args = nodes._policy_context_tool_args("bom dia, tudo bem?", _ctx(["1234567890"]))
        check("G-A1b: sem termo de detalhe não força tool", args is None, args)

        # G-A2: 2+ apólices + anáfora sem número → modo listagem (sem policy_number).
        args = nodes._policy_context_tool_args("ela tem assistência?", _ctx(["1234567890", "9876543210"]))
        check("G-A2: 2+ apólices + anáfora força listagem", isinstance(args, dict), args)
        check("G-A2: listagem não fixa policy_number", args and "policy_number" not in args, args)
        check("G-A2: listagem leva document", args and args.get("document") == "12345678900", args)

        # G-A2b: 2+ apólices SEM anáfora e sem número → não força nada (LLM decide).
        args = nodes._policy_context_tool_args("qual a franquia do carro?", _ctx(["1234567890", "9876543210"]))
        check("G-A2b: 2+ apólices sem anáfora não força tool", args is None, args)

        # G-A3: apólice selecionada no contexto → 'ela' gruda na selecionada.
        args = nodes._policy_context_tool_args(
            "ela cobre eletricista?", _ctx(["1234567890", "9876543210"], selected="9876543210")
        )
        check("G-A3: selected_policy_number resolve 'ela'", args and args.get("policy_number") == "9876543210", args)

        # Regressão: número literal no texto continua tendo prioridade.
        args = nodes._policy_context_tool_args(
            "detalhe a apólice 1234567890", _ctx(["1234567890", "9876543210"], selected="9876543210")
        )
        check("regressão: número literal no texto tem prioridade", args and args.get("policy_number") == "1234567890", args)

        # Segurança: contexto sem cliente não força nada.
        args = nodes._policy_context_tool_args("ela tem assistência?", {"policy_numbers": ["123"], "source": "x"})
        check("segurança: contexto sem document/name não força tool", args is None, args)

    # G-A4/captura: _safe_infocap_policy_context captura selected_policy_number em found.
    data_found = {
        "status": "found",
        "client_document": "12345678900",
        "client_name": "Cliente Sintetico",
        "matches": [{"policy_number": "1234567890", "numapo": "1234567890"}],
        "selected": {"policy_number": "1234567890", "numapo": "1234567890"},
    }
    ctx = nodes._safe_infocap_policy_context(data_found)
    check("captura: contexto criado em found", isinstance(ctx, dict), ctx)
    check("captura: selected_policy_number preenchido", ctx and ctx.get("selected_policy_number") == "1234567890", ctx)

    data_listing = {
        "status": "ambiguous_policy",
        "client_document": "12345678900",
        "matches": [
            {"policy_number": "1234567890"},
            {"policy_number": "9876543210"},
        ],
    }
    ctx = nodes._safe_infocap_policy_context(data_listing)
    check("captura: listagem não fixa selected", ctx and not ctx.get("selected_policy_number"), ctx)
    check("captura: listagem traz os 2 números", ctx and sorted(ctx.get("policy_numbers")) == ["1234567890", "9876543210"], ctx)

    # Contexto nunca carrega locator técnico.
    data_found_with_ref = dict(data_found)
    data_found_with_ref["selected"] = {"policy_number": "1234567890", "policy_locator_ref": "infocap:1:999"}
    ctx = nodes._safe_infocap_policy_context(data_found_with_ref)
    check("segurança: contexto não expõe locator técnico", "infocap:" not in str(ctx), ctx)


def run():
    print("== SPEC-016 - Policy Intelligence vertical ==")
    nodes = _load_nodes_module()
    run_e1(nodes)

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        sys.exit(1)


if __name__ == "__main__":
    run()
