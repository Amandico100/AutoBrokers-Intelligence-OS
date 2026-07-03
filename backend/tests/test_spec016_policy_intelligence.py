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


def _sample_pack(**overrides):
    pack = {
        "source": "infocap",
        "policy_locator": {"provider": "infocap", "codfil": "1", "nosnum": "999001"},
        "policy_ref": "999001",
        "insurer_detected": "allianz",
        "product_detected": "Residencial Total",
        "line_kind_detected": "residencial",
        "policy_status": "ativa",
        "active_now": True,
        "valid_from": "2026-01-01",
        "valid_to": "2027-01-01",
        "coverage_sections": [],
        "structured_coverage_available": False,
        "structured_coverage_absent": True,
        "infocap_financial_fields": [],
        "installments": [],
        "limitations": [],
    }
    pack.update(overrides)
    return pack


def run_e2(policy_facts):
    print("\n== E2 - Policy Facts mínimos ==\n")

    # Cobertura estruturada vira fact coverage com fonte infocap_structured.
    pack = _sample_pack(
        coverage_sections=[
            {"label": "Incêndio", "amount": "R$ 200.000,00"},
            {"label": "Danos Elétricos", "amount": "R$ 15.000,00"},
        ],
        structured_coverage_available=True,
        structured_coverage_absent=False,
    )
    facts = policy_facts.extract_policy_facts(pack)
    cov = [f for f in facts if f["fact_type"] == "coverage"]
    check("G-F1: seções estruturadas viram facts coverage", len(cov) == 2, facts)
    check("G-F1: fonte é infocap_structured", all(f["source"] == "infocap_structured" for f in cov), cov)
    check("G-F1: valor preservado", any(f["value"] == "R$ 15.000,00" for f in cov), cov)

    # Seção com label de assistência vira fact assistance.
    pack = _sample_pack(
        coverage_sections=[{"label": "Assistência Residencial 24h", "amount": None}],
        structured_coverage_available=True,
        structured_coverage_absent=False,
    )
    facts = policy_facts.extract_policy_facts(pack)
    assist = [f for f in facts if f["fact_type"] == "assistance"]
    check("G-F2: label de assistência vira fact assistance", len(assist) == 1, facts)
    check("G-F2: confiança alta para estruturado", assist and assist[0]["confidence"] == "high", assist)

    # Código curto nunca vira fact (guarda dupla além do connector).
    pack = _sample_pack(
        coverage_sections=[{"label": "P", "amount": None}, {"label": "A1", "amount": None}],
        structured_coverage_available=True,
        structured_coverage_absent=False,
    )
    facts = policy_facts.extract_policy_facts(pack)
    check("G-F3: código curto não vira fact", not [f for f in facts if f["fact_type"] in ("coverage", "assistance")], facts)

    # Campo financeiro sem semântica não vira fact.
    pack = _sample_pack(
        infocap_financial_fields=[{"provider_field": "preliq", "value": "123.45", "semantic_status": "provider_field_unclassified"}],
    )
    facts = policy_facts.extract_policy_facts(pack)
    check("G-F4: financeiro sem semântica não vira fact", not [f for f in facts if f["fact_type"] == "premium"], facts)

    # Evidência documental vira fact com página; sem página é descartada.
    pack = _sample_pack(
        official_policy_document_evidence={
            "ok": True,
            "document_status": "evidence_ready",
            "evidence_items": [
                {
                    "page_number": 3,
                    "evidence_type": "assistance",
                    "evidence_text": "Assistencia 24 horas: eletricista, chaveiro e encanador inclusos.",
                    "confidence": "high",
                    "source_document": "official_policy_document",
                },
                {
                    "page_number": None,
                    "evidence_type": "coverage",
                    "evidence_text": "trecho sem pagina",
                    "confidence": "medium",
                    "source_document": "official_policy_document",
                },
            ],
        },
    )
    facts = policy_facts.extract_policy_facts(pack)
    doc_facts = [f for f in facts if f["source"] == "official_document"]
    check("G-F5: evidência documental vira fact", len(doc_facts) == 1, facts)
    check("G-F5: fact documental exige página", doc_facts and doc_facts[0]["source_detail"].get("page") == 3, doc_facts)
    check("G-F5: trecho preservado no source_detail", doc_facts and "eletricista" in doc_facts[0]["source_detail"].get("snippet", ""), doc_facts)

    # Vigência vira fact validity.
    facts = policy_facts.extract_policy_facts(_sample_pack())
    validity = [f for f in facts if f["fact_type"] == "validity"]
    check("G-F6: vigência vira fact validity", len(validity) == 1 and "2026-01-01" in str(validity[0]["value"]), validity)

    # Pack vazio → sem facts inventados (além da vigência quando presente).
    facts = policy_facts.extract_policy_facts(_sample_pack(valid_from=None, valid_to=None))
    check("G-F7: pack sem dados não inventa facts", facts == [], facts)

    # Nunca vazar PII no fact.
    pack = _sample_pack(
        holder_name="Cliente Sintetico",
        document="12345678900",
        coverage_sections=[{"label": "Incêndio", "amount": "R$ 1,00"}],
    )
    facts = policy_facts.extract_policy_facts(pack)
    blob = str(facts)
    check("G-F8: facts não carregam CPF/nome do titular", "12345678900" not in blob and "Cliente Sintetico" not in blob, facts)

    # has_confirmed_assistance: helper usado pela política E3.
    pack = _sample_pack(
        coverage_sections=[{"label": "Assistência Residencial 24h", "amount": None}],
        structured_coverage_available=True,
        structured_coverage_absent=False,
    )
    facts = policy_facts.extract_policy_facts(pack)
    check("G-F9: assistência confirmada detectada", policy_facts.has_confirmed_assistance(facts) is True, facts)
    check("G-F9b: sem facts, assistência NÃO confirmada", policy_facts.has_confirmed_assistance([]) is False)


_ASSIST_SECTION = {"label": "Assistência Residencial 24h", "amount": None}


def run_e3(policy_facts, assistance_policy):
    print("\n== E3 - política residential_24h_standard_v1 ==\n")

    def _facts_for(pack):
        return policy_facts.extract_policy_facts(pack)

    # G-P1: residencial + assistência confirmada → política aplica os 3 serviços.
    pack = _sample_pack(
        coverage_sections=[_ASSIST_SECTION],
        structured_coverage_available=True,
        structured_coverage_absent=False,
    )
    result = assistance_policy.apply_residential_assistance_policy(pack, _facts_for(pack))
    check("G-P1: política aplicada", result.get("applied") is True, result)
    check(
        "G-P1: serviços padrão = eletricista/chaveiro/hidráulica",
        sorted(result.get("services") or []) == ["chaveiro", "eletricista", "hidraulica_encanador"],
        result,
    )
    check("G-P1: rule_id/version corretos", result.get("rule_id") == "residential_24h_standard_v1" and result.get("version") == 1, result)
    check("G-P1: statement humano presente", "eletricista" in str(result.get("statement") or "").lower(), result)

    # G-P2 (G37/G72): só o ramo residencial NÃO dispara a política.
    pack = _sample_pack()  # residencial, sem nenhuma seção/fact de assistência
    result = assistance_policy.apply_residential_assistance_policy(pack, _facts_for(pack))
    check("G-P2: ramo sozinho não dispara política", result.get("applied") is False, result)
    check("G-P2: razão explica falta de confirmação", "assist" in str(result.get("reason") or "").lower(), result)

    # G-P3: assistência confirmada mas ramo NÃO residencial → não aplica.
    pack = _sample_pack(
        line_kind_detected="auto",
        product_detected="Auto Perfil",
        coverage_sections=[{"label": "Assistência 24h Auto", "amount": None}],
        structured_coverage_available=True,
        structured_coverage_absent=False,
    )
    result = assistance_policy.apply_residential_assistance_policy(pack, _facts_for(pack))
    check("G-P3: apólice não residencial não aplica política residencial", result.get("applied") is False, result)

    # G-P4: apólice cancelada/não vigente → não aplica (fail-safe).
    pack = _sample_pack(
        cancelled=True,
        active_now=False,
        coverage_sections=[_ASSIST_SECTION],
        structured_coverage_available=True,
        structured_coverage_absent=False,
    )
    result = assistance_policy.apply_residential_assistance_policy(pack, _facts_for(pack))
    check("G-P4: apólice cancelada não aplica política", result.get("applied") is False, result)

    # G-P5: trace auditável com facts usados.
    pack = _sample_pack(
        coverage_sections=[_ASSIST_SECTION],
        structured_coverage_available=True,
        structured_coverage_absent=False,
    )
    result = assistance_policy.apply_residential_assistance_policy(pack, _facts_for(pack))
    trace = result.get("trace") or {}
    check("G-P5: trace tem rule_id e version", trace.get("rule_id") == "residential_24h_standard_v1" and trace.get("version") == 1, trace)
    check("G-P5: trace lista facts usados", isinstance(trace.get("facts_used"), list) and len(trace["facts_used"]) >= 1, trace)
    check("G-P5: trace sem PII", "12345678900" not in str(trace), trace)

    # G-P6: resultado gera fact policy_rule para o compositor citar.
    rule_facts = assistance_policy.policy_rule_facts(result)
    check("G-P6: política aplicada gera facts policy_rule", len(rule_facts) == 3 and all(f["source"] == "policy_rule" for f in rule_facts), rule_facts)
    not_applied = assistance_policy.apply_residential_assistance_policy(_sample_pack(), [])
    check("G-P6b: política não aplicada não gera facts", assistance_policy.policy_rule_facts(not_applied) == [], not_applied)


_JARGON = ("nosnum", "locator", "evidence_pack", "policy_ref", "codfil", "pack", "dto")


def _found_result(pack, question_client=True):
    result = {
        "ok": True,
        "status": "found",
        "selected": {
            "insurer_key": pack.get("insurer_detected"),
            "product": pack.get("product_detected"),
            "policy_number": "1234567890",
            "numapo": "1234567890",
            "holder_name": "Cliente Sintetico",
            "policy_status": pack.get("policy_status"),
            "active_now": pack.get("active_now"),
            "valid_from": pack.get("valid_from"),
            "valid_to": pack.get("valid_to"),
        },
        "matches": [],
        "policy_evidence_pack": pack,
    }
    if question_client:
        result["client_name"] = "Cliente Sintetico"
        result["client_document"] = "12345678900"
    return result


def run_e4(composer):
    print("\n== E4 - compositor humano de resposta ==\n")

    # G-C1: pergunta de assistência + política aplicada → resposta direta com os 3 serviços.
    pack = _sample_pack(
        coverage_sections=[_ASSIST_SECTION],
        structured_coverage_available=True,
        structured_coverage_absent=False,
    )
    text = composer.compose_policy_answer(question="ela tem assistência?", result=_found_result(pack))
    low = text.lower()
    check("G-C1: resposta direta afirmativa primeiro", low.strip().startswith("sim"), text)
    check("G-C1: cita os 3 serviços padrão", all(s in low for s in ("eletricista", "chaveiro", "encanador")) or ("hidráulica" in low and "eletricista" in low and "chaveiro" in low), text)
    check("G-C1: cita a fonte estruturada", "assistência residencial 24h" in low, text)
    check("G-C1: sem jargão técnico", not any(j in low for j in _JARGON), text)

    # G-C2: pergunta de assistência sem confirmação → ausência honesta, sem inventar.
    pack = _sample_pack()  # residencial, nada estruturado
    text = composer.compose_policy_answer(question="ela cobre eletricista?", result=_found_result(pack))
    low = text.lower()
    check("G-C2: não afirma assistência sem evidência", "sim" != low.strip()[:3], text)
    check("G-C2: declara ausência de confirmação na fonte", ("não" in low and ("confirm" in low or "não retornou" in low or "nao retornou" in low)), text)
    check("G-C2: não cita serviços como cobertos", "chaveiro" not in low, text)

    # G-C3: evidência documental pronta → cita página.
    pack = _sample_pack(
        document_evidence_ready=True,
        official_policy_document_evidence={
            "ok": True,
            "document_status": "evidence_ready",
            "evidence_items": [
                {
                    "page_number": 5,
                    "evidence_type": "assistance",
                    "evidence_text": "Assistencia 24 horas inclui eletricista, chaveiro e encanador.",
                    "confidence": "high",
                    "source_document": "official_policy_document",
                }
            ],
        },
    )
    text = composer.compose_policy_answer(question="ela tem assistência?", result=_found_result(pack))
    low = text.lower()
    check("G-C3: cita página do documento oficial", ("página 5" in low or "pagina 5" in low), text)
    check("G-C3: resposta afirmativa com fonte documental", low.strip().startswith("sim"), text)

    # G-C4: ambiguidade → opções numeradas com número humano, sem locator.
    result = {
        "ok": False,
        "status": "ambiguous_policy",
        "client_name": "Cliente Sintetico",
        "matches": [
            {"policy_number": "1234567890", "insurer_key": "allianz", "product": "Residencial", "valid_from": "2026-01-01", "valid_to": "2027-01-01", "policy_status": "ativa"},
            {"policy_number": "9876543210", "insurer_key": "porto", "product": "Auto", "valid_from": "2025-05-01", "valid_to": "2026-05-01", "policy_status": "ativa"},
        ],
    }
    text = composer.compose_policy_answer(question="ela tem assistência?", result=result)
    low = text.lower()
    check("G-C4: opções numeradas", "1." in text and "2." in text, text)
    check("G-C4: mostra número humano e seguradora", "1234567890" in text and "allianz" in low, text)
    check("G-C4: sem jargão técnico", not any(j in low for j in _JARGON), text)

    # G-C5: identity_mismatch → fail-closed, nada de dados.
    text = composer.compose_policy_answer(question="detalhe", result={"ok": False, "status": "identity_mismatch"})
    low = text.lower()
    check("G-C5: mismatch mantém fail-closed", "identidade" in low and "1234567890" not in text, text)

    # G-C6: cobertura estruturada listada de forma humana.
    pack = _sample_pack(
        coverage_sections=[
            {"label": "Incêndio", "amount": "R$ 200.000,00"},
            {"label": "Danos Elétricos", "amount": "R$ 15.000,00"},
        ],
        structured_coverage_available=True,
        structured_coverage_absent=False,
    )
    text = composer.compose_policy_answer(question="quais são as coberturas?", result=_found_result(pack))
    low = text.lower()
    check("G-C6: lista coberturas com valores", "incêndio" in low and "r$ 15.000,00" in low, text)
    check("G-C6: sem jargão técnico", not any(j in low for j in _JARGON), text)

    # G-C7: not_found claro.
    text = composer.compose_policy_answer(question="apólice 111", result={"ok": False, "status": "policy_number_not_found"})
    check("G-C7: not_found honesto", "não localizei" in text.lower() or "nao localizei" in text.lower(), text)

    # G-C8: variante com metadados para o contrato da tool.
    pack = _sample_pack(
        coverage_sections=[_ASSIST_SECTION],
        structured_coverage_available=True,
        structured_coverage_absent=False,
    )
    meta = composer.compose_policy_answer_with_meta(question="ela tem assistência?", result=_found_result(pack))
    check("G-C8: meta traz texto e política", isinstance(meta, dict) and meta.get("text") and (meta.get("assistance_policy") or {}).get("applied") is True, meta)
    meta2 = composer.compose_policy_answer_with_meta(question="ela tem assistência?", result=_found_result(_sample_pack()))
    check("G-C8b: política não aplicada no meta quando não confirmada", (meta2.get("assistance_policy") or {}).get("applied") is False, meta2)


def run_e4_integration(nodes):
    print("\n== E4b - integração tool + output guard ==\n")

    # Guard: required assistance_policy_applied → LLM não pode omitir os serviços.
    rendered = (
        "Sim — esta apólice residencial tem assistência confirmada.\n"
        "Pela política padrão de Assistência 24h residencial, os serviços incluídos são: eletricista, chaveiro, hidráulica/encanador."
    )
    contract = {
        "provider": "infocap",
        "result_kind": "found",
        "rendered_safe_answer": rendered,
        "required_facts": ["assistance_policy_applied"],
    }
    out = nodes._guard_infocap_policy_final_response("A apólice tem assistência sim!", contract)
    check("guard: candidata sem os serviços é substituída", out == rendered, out)
    good = "Sim! Ela tem assistência 24h: eletricista, chaveiro e hidráulica/encanador estão incluídos."
    out = nodes._guard_infocap_policy_final_response(good, contract)
    check("guard: candidata completa é mantida", out == good, out)

    # Integração estrutural: tool usa o compositor sob a flag v2.
    tool_src = (ROOT / "app" / "agents" / "tools" / "infocap_tool.py").read_text(encoding="utf-8")
    check("tool: usa compose_policy_answer_with_meta", "compose_policy_answer_with_meta" in tool_src)
    check("tool: gated pela flag POLICY_INTELLIGENCE_V2", "policy_intelligence_v2_enabled" in tool_src)
    check("tool: contrato ganha assistance_policy_applied", "assistance_policy_applied" in tool_src)


def run():
    print("== SPEC-016 - Policy Intelligence vertical ==")
    nodes = _load_nodes_module()
    run_e1(nodes)

    try:
        policy_facts = _load_file_module("app.services.policy_facts", "app/services/policy_facts.py")
    except FileNotFoundError:
        check("E2: módulo app/services/policy_facts.py existe", False, "arquivo ausente")
        policy_facts = None
    if policy_facts:
        run_e2(policy_facts)

    assistance_policy = None
    if policy_facts:
        try:
            assistance_policy = _load_file_module("app.services.assistance_policy", "app/services/assistance_policy.py")
        except FileNotFoundError:
            check("E3: módulo app/services/assistance_policy.py existe", False, "arquivo ausente")
    if assistance_policy:
        run_e3(policy_facts, assistance_policy)

    composer = None
    if assistance_policy:
        try:
            composer = _load_file_module("app.services.policy_answer_composer", "app/services/policy_answer_composer.py")
        except FileNotFoundError:
            check("E4: módulo app/services/policy_answer_composer.py existe", False, "arquivo ausente")
    if composer:
        run_e4(composer)
        run_e4_integration(nodes)

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        sys.exit(1)


if __name__ == "__main__":
    run()
