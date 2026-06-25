"""R1A - InfoCap contract capture tests (offline, sem provider real).

Rodar:
    python backend/tests/test_infocap_contract_capture.py

Estes testes cobrem apenas helpers puros do probe seguro. Eles nunca usam
credenciais, Supabase, Vault, rede, payload real ou PII real.
"""

import importlib.util
import ast
import json
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    # Stubs pequenos para carregar infocap_connector.py sem inicializar a app.
    sys.modules.setdefault(
        "httpx",
        types.SimpleNamespace(
            TimeoutException=TimeoutError,
            HTTPError=Exception,
            AsyncClient=object,
        ),
    )
    if "fastapi" not in sys.modules:
        fastapi = types.ModuleType("fastapi")
        route_decorator = lambda *pa, **pk: (lambda fn: fn)
        fastapi.APIRouter = lambda *a, **k: types.SimpleNamespace(
            post=route_decorator,
            get=route_decorator,
        )
        fastapi.Depends = lambda *a, **k: None
        fastapi.Header = lambda *a, **k: None
        fastapi.HTTPException = type(
            "HTTPException",
            (Exception,),
            {
                "__init__": lambda self, status_code=500, detail=None: (
                    setattr(self, "status_code", status_code),
                    setattr(self, "detail", detail),
                    Exception.__init__(self, detail),
                )[-1]
            },
        )
        sys.modules["fastapi"] = fastapi
    if "pydantic" not in sys.modules:
        pydantic = types.ModuleType("pydantic")

        class BaseModel:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)

        pydantic.BaseModel = BaseModel
        sys.modules["pydantic"] = pydantic

    for name in (
        "app",
        "app.core",
        "app.core.config",
        "app.core.database",
        "app.services",
        "app.services.encryption_service",
    ):
        sys.modules.setdefault(name, types.ModuleType(name))

    sys.modules["app.core.config"].settings = types.SimpleNamespace(
        INFOCAP_BASE_URL="",
    )
    sys.modules["app.core.database"].AsyncSupabaseClient = object
    sys.modules["app.core.database"].get_async_db = lambda: None
    sys.modules["app.services.encryption_service"].get_encryption_service = (
        lambda: types.SimpleNamespace(decrypt=lambda value: value, encrypt=lambda value: value)
    )

    path = ROOT / "app" / "api" / "infocap_connector.py"
    spec = importlib.util.spec_from_file_location("infocap_connector_contract", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load_module()
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


def run():
    print("== R1A - InfoCap contract capture helpers ==\n")

    connector_source = (ROOT / "app" / "api" / "infocap_connector.py").read_text(encoding="utf-8")
    tool_source = (ROOT / "app" / "agents" / "tools" / "infocap_tool.py").read_text(encoding="utf-8")
    route_source = (ROOT.parent / "app" / "api" / "attendance" / "connectors" / "infocap" / "probe" / "route.ts").read_text(encoding="utf-8")
    connector_ast = ast.parse(connector_source)
    tool_ast = ast.parse(tool_source)

    def top_level_count(tree, name):
        return sum(isinstance(node, ast.FunctionDef) and node.name == name for node in tree.body)

    def class_method_count(tree, class_name, method_name):
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                return sum(isinstance(child, ast.FunctionDef) and child.name == method_name for child in node.body)
        return 0

    check("single _build_evidence_pack definition", top_level_count(connector_ast, "_build_evidence_pack") == 1)
    check("single _coverage_sections definition", top_level_count(connector_ast, "_coverage_sections") == 1)
    check("single _summarize definition", class_method_count(tool_ast, "InfocapPolicyLookupTool", "_summarize") == 1)
    check("single _summarize_detail definition", class_method_count(tool_ast, "InfocapPolicyLookupTool", "_summarize_detail") == 1)
    check("tool does not keep local connection selector", class_method_count(tool_ast, "InfocapPolicyLookupTool", "_find_conn_id") == 0)
    input_class = next((node for node in tool_ast.body if isinstance(node, ast.ClassDef) and node.name == "InfocapLookupInput"), None)
    input_fields = {
        node.target.id
        for node in (input_class.body if input_class else [])
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    }
    arun_args = set()
    for node in tool_ast.body:
        if isinstance(node, ast.ClassDef) and node.name == "InfocapPolicyLookupTool":
            for child in node.body:
                if isinstance(child, ast.AsyncFunctionDef) and child.name == "_arun":
                    arun_args = {arg.arg for arg in child.args.args}
    check("tool schema accepts policy_number", "policy_number" in input_fields, input_fields)
    check("tool runtime accepts policy_number", "policy_number" in arun_args, arun_args)
    check("probe route delegates connection resolution to backend", "infocap-connection-resolution" not in route_source)

    payload = {
        "documento": [
            {
                "cpf_cnpj": "11122233344",
                "cliente": "Pessoa Teste",
                "numapo": "POL-123",
            }
        ],
        "itens": [{"descricao": "Cobertura X", "valor": "999"}],
        "parcelas": [{"valor": "123"}],
        "nested": {"level2": {"secret": "nao-pode-sair"}},
    }
    out = mod._safe_contract_shape(payload)
    raw = str(out)
    check("safe shape raw_type object", out["raw_type"] == "object")
    check("safe shape top_level_keys", "documento" in out["top_level_keys"])
    check("safe shape nested path", "documento[]" in out["nested_key_paths"])
    check("safe shape count documento", out["counts"]["documento"] == 1)
    check("safe shape count itens", out["counts"]["itens"] == 1)
    check("detect cpf_cnpj key", out["detected_policy_fields"]["cpf_cnpj_present"] is True)
    check("detect items", out["detected_policy_fields"]["items_present"] is True)
    check("detect installments", out["detected_policy_fields"]["installments_present"] is True)
    check("does not leak cpf", "11122233344" not in raw)
    check("does not leak name", "Pessoa Teste" not in raw)
    check("does not leak policy number", "POL-123" not in raw)
    check("does not leak amount", "999" not in raw)
    check("shape hash present", bool(out["shape_hash"]))

    candidates = [{"codigo": "1", "codfil": "1"}, {"codigo": "2", "codfil": "1"}]
    selected, status = mod._select_unique_contract_candidate(candidates)
    check("ambiguous customer has no selection", selected is None)
    check("ambiguous customer status", status == "ambiguous_customer", status)

    docs = [
        {"nosnum": "N1", "numapo": "A1", "codfil": "1"},
        {"nosnum": "N2", "numapo": "A2", "codfil": "1"},
    ]
    locator, status = mod._select_policy_locator(docs, codfil="1", requested_policy_ref=None)
    check("ambiguous policy has no locator", locator is None)
    check("ambiguous policy status", status == "ambiguous_policy", status)
    locator, status = mod._select_policy_locator(docs, codfil="1", requested_policy_ref="N2")
    check("explicit nosnum status found", status == "found", status)
    check(
        "explicit nosnum locator includes codfil+nosnum internally",
        locator == {"provider": "infocap", "codfil": "1", "nosnum": "N2"},
        locator,
    )

    bad_docs = [{"codigo": "CLIENTE-1", "codcli": "CLIENTE-2", "numapo": "A1"}]
    locator, status = mod._select_policy_locator(bad_docs, codfil="1", requested_policy_ref=None)
    check("codigo/codcli never become locator", locator is None)
    check("missing nosnum status source_limited", status == "source_limited", status)

    unsafe = {
        "ok": True,
        "customer": {"codigo": "CLIENTE-1", "cpf_cnpj": "11122233344"},
        "policy_locator": {"provider": "infocap", "codfil": "1", "nosnum": "N1"},
        "shape": {"top_level_keys": ["documento"], "shape_hash": "abc"},
        "notes": ["safe"],
    }
    safe = mod._sanitize_contract_output(unsafe)
    raw = str(safe)
    check("policy locator exposed only by provider", safe["policy_locator"] == {"provider": "infocap"}, safe)
    check("sanitize removes codigo", "CLIENTE-1" not in raw)
    check("sanitize removes cpf", "11122233344" not in raw)
    check("sanitize removes nosnum", "N1" not in raw)
    check("sanitize removes codfil value", "'codfil': '1'" not in raw)
    check("sanitize keeps structural keys", safe["shape"]["top_level_keys"] == ["documento"])

    fixture_path = ROOT / "tests" / "fixtures" / "infocap_contract_shapes" / "policy_chain_top_level_lists.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    fixture_shape = mod._safe_contract_shape(fixture)
    fixture_raw = str(fixture_shape)
    check("fixture detects sibling coberturas", fixture_shape["detected_policy_fields"]["coverages_present"] is True)
    check("fixture detects sibling history", fixture_shape["detected_policy_fields"]["history_present"] is True)
    check("fixture detects sibling installments", fixture_shape["detected_policy_fields"]["installments_present"] is True)
    check("fixture does not leak synthetic policy", "APOLICE-SINTETICA" not in fixture_raw)

    catalog_shape = mod._safe_contract_shape({"documentos": {"documentos": [{"nosnum": "N1"}, {"nosnum": "N2"}]}})
    check("nested documentos.documentos result_count", catalog_shape["result_count"] == 2, catalog_shape)

    identity_fn = getattr(mod, "_canonical_customer_identity", None)
    check("canonical customer identity helper exists", callable(identity_fn))
    if callable(identity_fn):
        ident = identity_fn(
            {"cpf": "99999999999", "cliente": "Busca Sintetica", "codigo": "C1", "codfil": "1"},
            {"cpf_cnpj": "11122233344", "cliente": "Detalhe Canonico", "codigo": "C1", "codfil": "1"},
            unmasked=True,
        )
        check("canonical identity uses cpf_cnpj from /cliente", ident.get("client_document") == "11122233344", ident)
        check("canonical identity uses name from /cliente", ident.get("client_name") == "Detalhe Canonico", ident)

    policy = mod._sanitize_policy({"codigo": "CLIENTE-1", "codcli": "CLIENTE-2", "numapo": "AP-1"}, True)
    check("codigo/codcli never become policy_ref", not policy.get("policy_ref"), policy)
    policy = mod._sanitize_policy({"nosnum": "N1", "codfil": "2", "numapo": "AP-1"}, True)
    check("policy_ref derives from nosnum", policy.get("policy_ref") == "N1", policy)
    check(
        "policy locator carries codfil+nosnum",
        policy.get("policy_locator") == {"provider": "infocap", "codfil": "2", "nosnum": "N1"},
        policy,
    )

    locator, status = mod._select_policy_locator(
        [{"nosnum": "N1", "numapo": "AP-11", "codfil": "1"}, {"nosnum": "N2", "numapo": "AP-22", "codfil": "2"}],
        codfil="1",
        requested_policy_ref="AP-22",
    )
    check("numapo resolves to nosnum locator", locator == {"provider": "infocap", "codfil": "2", "nosnum": "N2"}, locator)
    check("numapo resolution status found", status == "found", status)
    locator, status = mod._select_policy_locator(
        [{"nosnum": "N1", "numapo": "AP-22", "codfil": "1"}, {"nosnum": "N2", "numapo": "AP-22", "codfil": "2"}],
        codfil="1",
        requested_policy_ref="AP-22",
    )
    check("policy_number with multiple exact matches is ambiguous", locator is None and status == "ambiguous_policy", (locator, status))
    policy = mod._sanitize_policy({"nosnum": "N0", "codfil": "1", "numapo": "0"}, True)
    check("policy number zero is not exposed as valid", not policy.get("policy_number") and not policy.get("masked_policy_number"), policy)
    display_number = getattr(mod, "_display_policy_number", None)
    check("display helper for invalid policy number exists", callable(display_number))
    if callable(display_number):
        check("display helper does not show zero", display_number({"policy_number": "0"}) == "numero nao retornado pela InfoCap")
    raw_codfil, raw_ref = mod._parse_policy_ref_input("N2")
    locator_codfil, locator_ref = mod._parse_policy_ref_input("infocap:2:N2")
    check("raw nosnum has no codfil", raw_codfil is None and raw_ref == "N2", (raw_codfil, raw_ref))
    check("policy locator ref carries codfil", locator_codfil == "2" and locator_ref == "N2", (locator_codfil, locator_ref))

    code_only_sections = mod._coverage_sections({"itens": [{"item": "P", "tipo": "A"}]})
    check("short codes do not become coverage labels", code_only_sections == [], code_only_sections)

    envelope = {
        "documento": [{
            "nosnum": "N1",
            "codfil": "1",
            "numapo": "AP-1",
            "cpf_cnpj": "11122233344",
            "cliente": "Pessoa Sintetica",
            "tabela_itens": "P",
            "preliq": "100.00",
            "pretot": "110.00",
            "parcelas": [{
                "parc": "1",
                "datvenc": "10/01/2026",
                "datquit": "11/01/2026",
                "vlvenc": "110.00",
                "vlquit": "110.00",
                "forma_pagamento": "boleto",
            }],
            "prod_docs": [{"tipo": "apolice"}],
        }],
        "historico": [{"evento": "emitida"}],
        "acompanhamento": {"emissao": {"url_apolice": "https://docs.example.test/apolice.pdf"}},
    }
    try:
        pack = mod._build_evidence_pack(envelope["documento"][0], None, None, True, envelope=envelope)
    except TypeError as exc:
        pack = {"error": str(exc)}
    raw_pack = str(pack)
    check("evidence pack preserves envelope keys structurally", {"documento", "historico", "acompanhamento"}.issubset(set((pack.get("evidence_envelope") or {}).keys())), pack)
    check("installments normalized with source fields", (pack.get("installments") or [{}])[0].get("source_fields", {}).get("due_date") == "datvenc", pack.get("installments"))
    check("unknown financial fields keep provider_field", any(f.get("provider_field") == "preliq" for f in pack.get("infocap_financial_fields") or []), pack.get("infocap_financial_fields"))
    check("tabela_itens is unknown table field", pack.get("unknown_table_field_present") is True, pack)
    check("coverage absent is explicit", pack.get("coverage_evidence_status") == "structured_coverage_absent", pack)
    check("official document source is flag only", pack.get("official_document_source_available") is True and "docs.example.test" not in raw_pack, pack)
    check("document evidence required when structured coverage absent and source exists", pack.get("document_evidence_required") is True, pack)

    expected_statuses = {
        "found",
        "ambiguous_customer",
        "ambiguous_policy",
        "source_limited",
        "provider_auth_error",
        "provider_timeout",
        "unknown_shape",
        "document_evidence_required",
        "conflict_requires_human",
    }
    check("contract status enum complete", expected_statuses.issubset(mod.CONTRACT_STATUSES))
    endpoint = mod._shape_probe_endpoint("policy_detail.documento", 200, fixture)
    check("contract endpoint metadata uses GET", endpoint["method"] == "GET")
    safe_endpoint = mod._sanitize_contract_output({"endpoint": endpoint})
    check("sanitizer preserves structural documento count", safe_endpoint["endpoint"]["counts"]["documento"] == 1)
    check("sanitizer preserves structural documento sample keys", "documento" in safe_endpoint["endpoint"]["sample_keys"])

    resolver = getattr(mod, "_resolve_infocap_connection_candidates", None)
    check("canonical backend connection resolver exists", callable(resolver))
    if callable(resolver):
        def conn(**overrides):
            row = {
                "id": "conn-valid",
                "company_id": "company-1",
                "status": "connected",
                "health_status": "healthy",
                "encrypted_secret_ref": "vault-ref",
                "connection_config": {"base_url": "https://infocap.example.test"},
                "connector_templates": {"slug": "infocap"},
            }
            row.update(overrides)
            return row

        decision = resolver([
            conn(id="new-missing-secret", encrypted_secret_ref=""),
            conn(id="older-valid"),
        ], company_id="company-1", requested_connection_id=None, provider_default_base_url="")
        check("resolver chooses only eligible connection", (decision.get("selected_connection") or {}).get("id") == "older-valid", decision)
        check("resolver summary omits connection id", "older-valid" not in str(decision.get("summary")), decision.get("summary"))

        decision = resolver([conn(id="a"), conn(id="b")], company_id="company-1", requested_connection_id=None, provider_default_base_url="")
        check("two eligible connections become ambiguous", decision.get("status") == "ambiguous_connection", decision)
        check("ambiguous resolver chooses no connection", decision.get("selected_connection") is None, decision)

        decision = resolver([conn(id="archived", status="archived"), conn(id="missing-secret", encrypted_secret_ref="")], company_id="company-1", requested_connection_id=None, provider_default_base_url="")
        check("zero eligible connections request reconnect", decision.get("status") == "blocked_missing_credentials", decision)
        check("zero eligible selection status reconnect", (decision.get("summary") or {}).get("selection_status") == "reconnect_required", decision)

    ramo_pack = mod._build_evidence_pack(
        {"nosnum": "N1", "codfil": "1", "numapo": "AP-1", "ramo": "Residencial", "produto": "Residencial Completo"},
        None,
        None,
        True,
        envelope={"documento": [{"nosnum": "N1", "codfil": "1"}]},
    )
    check("ramo/produto residencial does not create assistance signal", not any(v is True for v in (ramo_pack.get("assistance_signals") or {}).values()), ramo_pack.get("assistance_signals"))
    check("ramo/produto residencial keeps coverage absent", ramo_pack.get("coverage_sections") == [] and ramo_pack.get("structured_coverage_absent") is True, ramo_pack)

    auto_pack = mod._build_evidence_pack(
        {"nosnum": "N2", "codfil": "1", "numapo": "AP-2", "ramo": "Auto", "produto": "Auto eletrico"},
        None,
        None,
        True,
        envelope={"documento": [{"nosnum": "N2", "codfil": "1"}]},
    )
    check("produto auto/eletrico does not create electrician signal", (auto_pack.get("assistance_signals") or {}).get("electrician") is not True, auto_pack.get("assistance_signals"))

    option_formatter = getattr(mod, "_format_policy_options_for_summary", None)
    check("deterministic policy option formatter exists", callable(option_formatter))
    if callable(option_formatter):
        options_text = option_formatter([
            {
                "insurer_key": "SEG-A",
                "product": "Residencial",
                "valid_from": "01/01/2026",
                "valid_to": "01/01/2027",
                "policy_status": "ativo",
                "policy_number": "AP-1",
                "policy_locator_ref": "infocap:1:N1",
            }
        ])
        check("ambiguous option lists insurer/product", "SEG-A" in options_text and "Residencial" in options_text, options_text)
        check("ambiguous option uses human policy number", "AP-1" in options_text, options_text)
        check("ambiguous option does not require technical locator by default", "infocap:1:N1" not in options_text, options_text)
        debug_options_text = option_formatter([
            {
                "insurer_key": "SEG-A",
                "product": "Residencial",
                "valid_from": "01/01/2026",
                "valid_to": "01/01/2027",
                "policy_status": "ativo",
                "policy_number": "AP-1",
                "policy_locator_ref": "infocap:1:N1",
            }
        ], include_internal_ref=True)
        check("ambiguous option can include locator for debug", "infocap:1:N1" in debug_options_text, debug_options_text)


if __name__ == "__main__":
    run()
    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAIL:
        for name, detail in FAILURES:
            print(f"  - {name}{': ' + str(detail) if detail else ''}")
        sys.exit(1)
    sys.exit(0)
