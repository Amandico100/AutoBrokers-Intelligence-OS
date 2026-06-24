"""R1A - InfoCap contract capture tests (offline, sem provider real).

Rodar:
    python backend/tests/test_infocap_contract_capture.py

Estes testes cobrem apenas helpers puros do probe seguro. Eles nunca usam
credenciais, Supabase, Vault, rede, payload real ou PII real.
"""

import importlib.util
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


if __name__ == "__main__":
    run()
    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAIL:
        for name, detail in FAILURES:
            print(f"  - {name}{': ' + str(detail) if detail else ''}")
        sys.exit(1)
    sys.exit(0)
