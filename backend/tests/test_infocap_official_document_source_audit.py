"""R1C.0 - InfoCap official document source audit tests (offline).

Rodar:
    python backend/tests/test_infocap_official_document_source_audit.py

Estes testes cobrem apenas helpers puros do modo de auditoria. Eles nunca usam
credenciais, Supabase, Vault, rede, payload real, URL real ou PII real.
"""

import importlib.util
import json
import sys
import types
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def _load_module():
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
    spec = importlib.util.spec_from_file_location("infocap_connector_doc_audit", path)
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


def _pdf_bytes(*, text=True, encrypted=False, pages=1):
    body = b"%PDF-1.4\n"
    if encrypted:
        body += b"1 0 obj << /Encrypt 2 0 R >> endobj\n"
    for page in range(pages):
        body += f"{page + 1} 0 obj << /Type /Page >> endobj\n".encode("ascii")
    if text:
        body += b"BT /F1 12 Tf (Coberturas Assistencia Franquia Premio LMI Apolice) Tj ET\n"
    return body + b"%%EOF"


def _safe_json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def run():
    print("== R1C.0 - InfoCap official document source audit helpers ==\n")

    connector_source = (ROOT / "app" / "api" / "infocap_connector.py").read_text(encoding="utf-8")
    route_source = (ROOT.parent / "app" / "api" / "attendance" / "connectors" / "infocap" / "probe" / "route.ts").read_text(encoding="utf-8")
    admin_page_source = (ROOT.parent / "app" / "admin" / "companies" / "[companyId]" / "agents" / "page.tsx").read_text(encoding="utf-8")
    check("backend exposes official_document_source_audit mode", "official_document_source_audit" in connector_source)
    check("Next probe route forwards official_document_source_audit mode", "official_document_source_audit" in route_source)
    check("backend has master-only guard helper", "_require_probe_master_authorization" in connector_source)
    check("Next route sends backend master audit header", "X-AutoBrokers-Master-Admin" in route_source)
    check("Next route requires master admin for audit modes", "requireMasterAdmin()" in route_source)
    check("Next route requires same-origin for audit modes", "assertSameOrigin(req)" in route_source)
    probe_start = connector_source.find("async def infocap_probe")
    guard_at = connector_source.find("_require_probe_master_authorization", probe_start)
    resolver_at = connector_source.find("_resolve_infocap_connection(", probe_start)
    check("backend guard runs before connection resolution", probe_start >= 0 and guard_at >= 0 and resolver_at >= 0 and guard_at < resolver_at, "guard order")
    check("admin card has audit mode selector", "Auditar fonte oficial da apolice" in admin_page_source)
    check("admin card does not render manual company_id input", 'name="company_id"' not in admin_page_source and "company_id_da_url" not in admin_page_source)
    check("document fetch uses Range header", '"Range": f"bytes=0-' in connector_source)

    for header_value, expected in ((None, False), ("false", False), ("company_admin", False), ("true", True)):
        try:
            mod._require_probe_master_authorization("official_document_source_audit", header_value)
            allowed = True
        except Exception:
            allowed = False
        check(f"backend master-only header={header_value!r}", allowed is expected)
    try:
        mod._require_probe_master_authorization("endpoint_probe", None)
        regular_mode_allowed = True
    except Exception:
        regular_mode_allowed = False
    check("non-master regular probe remains allowed by backend guard", regular_mode_allowed is True)

    candidates = mod._extract_official_document_candidates({})
    check("url_apolice ausente retorna lista vazia", candidates == [], candidates)

    unsafe_urls = [
        "http://docs.example.invalid/policy.pdf",
        "https://user:pass@docs.example.invalid/policy.pdf",
        "https://localhost/policy.pdf",
        "https://127.0.0.1/policy.pdf",
        "https://0.0.0.0/policy.pdf",
        "https://[::1]/policy.pdf",
        "https://10.0.0.1/policy.pdf",
        "https://172.16.0.1/policy.pdf",
        "https://192.168.0.1/policy.pdf",
        "https://169.254.169.254/latest/meta-data",
    ]
    for unsafe_url in unsafe_urls:
        ok, reason = mod._is_safe_official_document_url(unsafe_url)
        check(f"SSRF bloqueia {unsafe_url}", ok is False, reason)
    ok, reason = mod._is_safe_official_document_url("https://docs.example.invalid/policy.pdf")
    check("HTTPS sem credencial embutida e permitido pelo validador sintetico", ok is True, reason)

    envelope = {
        "acompanhamento": {
            "emissao": {"url_apolice": "https://docs.example.invalid/policy.pdf?secret=abc"},
            "proposta": {"url_proposta": "https://docs.example.invalid/proposal.pdf"},
        }
    }
    candidates = mod._extract_official_document_candidates(envelope)
    check("url_apolice presente vira candidato policy_pdf", candidates[0]["source_kind"] == "policy_pdf", candidates)
    check("url_proposta fica atras da apolice", candidates[1]["source_kind"] == "proposal", candidates)

    pdf = mod._classify_official_document_response(
        source_kind="policy_pdf",
        status_code=200,
        headers={"content-type": "application/pdf", "content-disposition": "inline; filename=policy.pdf"},
        body=_pdf_bytes(text=True, pages=2),
        redirect_count=0,
        source_url="https://docs.example.invalid/policy.pdf?secret=abc",
        final_url="https://docs.example.invalid/policy.pdf?secret=abc",
        successful_auth_mode="authorization_header",
    )
    check("PDF valido classifica retrieved", pdf["retrieval_status"] == "retrieved", pdf)
    check("PDF valido detecta magic pdf", pdf["file_magic"] == "pdf", pdf)
    check("PDF valido detecta paginas", pdf["pdf_page_count"] == 2, pdf)
    check("PDF valido detecta camada texto", pdf["text_layer_status"] == "present", pdf)
    check("PDF valido detecta ancora cobertura", pdf["document_anchor_detection"]["coverage_anchor_present"] is True, pdf)
    check("PDF valido recomenda fetch autenticado direto", pdf["recommended_r1c_transport"] == "direct_authenticated_fetch", pdf)

    html_login = mod._classify_official_document_response(
        source_kind="policy_pdf",
        status_code=200,
        headers={"content-type": "text/html"},
        body=b"<html><form><input name='senha' /></form>login</html>",
        redirect_count=0,
        source_url="https://docs.example.invalid/policy.pdf",
        final_url="https://docs.example.invalid/login",
        successful_auth_mode=None,
    )
    check("HTML login classifica html_login", html_login["retrieval_status"] == "html_login", html_login)
    check("HTML login recomenda portal_required", html_login["recommended_r1c_transport"] == "portal_required", html_login)

    auth = mod._classify_official_document_response(
        source_kind="policy_pdf",
        status_code=200,
        headers={"content-type": "application/pdf"},
        body=_pdf_bytes(),
        redirect_count=0,
        source_url="https://docs.example.invalid/policy.pdf",
        final_url="https://docs.example.invalid/policy.pdf",
        successful_auth_mode="authorization_header",
    )
    cookie = mod._classify_official_document_response(
        source_kind="policy_pdf",
        status_code=200,
        headers={"content-type": "application/pdf"},
        body=_pdf_bytes(),
        redirect_count=0,
        source_url="https://docs.example.invalid/policy.pdf",
        final_url="https://docs.example.invalid/policy.pdf",
        successful_auth_mode="session_cookie",
    )
    both = mod._classify_official_document_response(
        source_kind="policy_pdf",
        status_code=200,
        headers={"content-type": "application/pdf"},
        body=_pdf_bytes(),
        redirect_count=0,
        source_url="https://docs.example.invalid/policy.pdf",
        final_url="https://docs.example.invalid/policy.pdf",
        successful_auth_mode="both",
    )
    check("Authorization detectado como auth_mode_required", auth["auth_mode_required"] == "authorization_header", auth)
    check("Cookie detectado como auth_mode_required", cookie["auth_mode_required"] == "session_cookie", cookie)
    check("Authorization+cookie detectado como both", both["auth_mode_required"] == "both", both)

    redirected = mod._classify_official_document_response(
        source_kind="policy_pdf",
        status_code=200,
        headers={"content-type": "application/pdf"},
        body=_pdf_bytes(),
        redirect_count=1,
        source_url="https://docs.example.invalid/policy.pdf",
        final_url="https://cdn.example.invalid/policy.pdf",
        successful_auth_mode="none",
    )
    check("redirect HTTPS externo classifica external_https", redirected["final_origin_class"] == "external_https", redirected)
    check("redirect HTTPS com none recomenda signed_url_fetch", redirected["recommended_r1c_transport"] == "signed_url_fetch", redirected)
    check("redirect cross-origin strips credential marker helper", mod._should_send_document_credentials("https://a.example/p.pdf", "https://b.example/p.pdf") is False)
    check("same-origin can keep credential marker helper", mod._should_send_document_credentials("https://a.example/p.pdf", "https://a.example/next.pdf") is True)

    http_redirect = mod._validate_official_document_redirect("https://docs.example.invalid/policy.pdf", "http://docs.example.invalid/policy.pdf")
    check("redirect HTTP bloqueado", http_redirect[0] is False and http_redirect[1] == "unsafe_redirect", http_redirect)

    oversized = mod._classify_official_document_response(
        source_kind="policy_pdf",
        status_code=200,
        headers={"content-type": "application/pdf", "content-length": str(mod.OFFICIAL_DOCUMENT_AUDIT_MAX_BYTES + 1)},
        body=b"",
        redirect_count=0,
        source_url="https://docs.example.invalid/policy.pdf",
        final_url="https://docs.example.invalid/policy.pdf",
        successful_auth_mode="authorization_header",
    )
    check("resposta oversized bloqueia", oversized["retrieval_status"] == "unsupported", oversized)
    check("resposta oversized marca blocker", "document_too_large" in oversized["source_fetch_blocker"], oversized)

    encrypted = mod._classify_official_document_response(
        source_kind="policy_pdf",
        status_code=200,
        headers={"content-type": "application/pdf"},
        body=_pdf_bytes(encrypted=True),
        redirect_count=0,
        source_url="https://docs.example.invalid/policy.pdf",
        final_url="https://docs.example.invalid/policy.pdf",
        successful_auth_mode="authorization_header",
    )
    check("PDF criptografado detectado", encrypted["pdf_encrypted"] is True, encrypted)
    check("PDF criptografado nao e seguro para R1C", encrypted["source_fetch_safe_for_r1c"] is False, encrypted)

    scanned = mod._classify_official_document_response(
        source_kind="policy_pdf",
        status_code=200,
        headers={"content-type": "application/pdf"},
        body=_pdf_bytes(text=False),
        redirect_count=0,
        source_url="https://docs.example.invalid/policy.pdf",
        final_url="https://docs.example.invalid/policy.pdf",
        successful_auth_mode="authorization_header",
    )
    check("PDF sem texto detecta camada ausente", scanned["text_layer_status"] == "absent", scanned)
    check("PDF sem texto continua candidato para Docling/OCR futuro", scanned["source_fetch_safe_for_r1c"] is True, scanned)

    forbidden = {
        "url": "https://docs.example.invalid/policy.pdf?token=segredo",
        "Authorization": "Bearer segredo",
        "cookie": "session=segredo",
        "cpf_cnpj": "03074327936",
        "nome": "RAFAEL LACAU DA SILVEIRA",
        "numapo": "202623140269972",
        "codfil": "1",
        "nosnum": "99599",
        "payload": "%PDF conteudo bruto",
        "safe": "ok",
    }
    safe = mod._safe_official_document_audit_output(forbidden)
    safe_raw = _safe_json(safe)
    for bad in (
        "docs.example.invalid",
        "segredo",
        "03074327936",
        "RAFAEL",
        "202623140269972",
        "99599",
        "%PDF",
    ):
        check(f"saida segura nao vaza {bad}", bad not in safe_raw, safe_raw)
    check("saida segura preserva chave inocua", safe.get("safe") == "ok", safe)

    with mod._temporary_official_document_audit_file(b"temporary-bytes") as temp_path:
        temp = Path(temp_path)
        exists_inside = temp.exists()
    check("arquivo temporario existe apenas dentro do contexto", exists_inside is True)
    check("arquivo temporario apagado ao sair", temp.exists() is False, str(temp))

    no_writes = _safe_json(pdf)
    for forbidden_call in ("minio", "qdrant", "documentservice", "supabase", "docling"):
        check(f"resultado de auditoria nao referencia escrita em {forbidden_call}", forbidden_call not in no_writes.lower(), no_writes)

    with patch("socket.getaddrinfo", return_value=[(None, None, None, None, ("10.0.0.10", 443))]):
        ok, reason = mod._is_safe_official_document_url("https://tenant-provider.example.invalid/policy.pdf")
        check("DNS resolving to private IP is blocked", ok is False and reason == "private_network", reason)


if __name__ == "__main__":
    run()
    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAIL:
        for name, detail in FAILURES:
            print(f"  - {name}{': ' + str(detail) if detail else ''}")
        sys.exit(1)
    sys.exit(0)
