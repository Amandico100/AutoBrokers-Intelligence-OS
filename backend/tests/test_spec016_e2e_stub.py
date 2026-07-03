"""SPEC-016 E6 - E2E da cadeia canônica contra um InfoCap STUB local.

Rodar:
    python backend/tests/test_spec016_e2e_stub.py

O que este harness prova (offline, somente localhost, fixtures 100% sintéticas):
  - cadeia canônica real: /login -> /cliente_cpf -> /cliente -> /cliente_ligacoes
    -> /documento com httpx REAL contra servidor HTTP local;
  - conversa multi-turno com anáfora ("ela tem assistência?") resolvida pelo
    contexto seguro + política residential_24h_standard_v1 + compositor humano;
  - P0 continua fail-closed neste caminho (colisão numapo/nosnum e mismatch);
  - nenhum segredo/token/base_url vaza no resultado.

Requisito: httpx instalado (dependência real do backend). Nenhuma outra
dependência pesada é usada (fastapi/pydantic/app.* são stubs mínimos).
"""

import importlib.util
import asyncio
import json
import os
import sys
import threading
import types
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

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


# ---------------------------------------------------------------------------
# Fixtures sintéticas (NUNCA dados reais)
# ---------------------------------------------------------------------------

CPF_SINT = "98765432100"
CLIENTE_SINT = "Cliente Sintetico Spec"
CODIGO_SINT = "777"

CAT_RES = {
    "codfil": 1,
    "nosnum": "555001",
    "numapo": "1234567890",
    "seguradora_abrev": "ALLIANZ",
    "ramo": "RESIDENCIAL",
    "inivig": "01/01/2026",
    "fimvig": "01/01/2027",
    "cliente": CLIENTE_SINT,
}
CAT_AUTO = {
    "codfil": 1,
    "nosnum": "555002",
    "numapo": "9876543210",
    "seguradora_abrev": "PORTO",
    "ramo": "AUTOMOVEL",
    "inivig": "01/03/2026",
    "fimvig": "01/03/2027",
    "cliente": CLIENTE_SINT,
}
# Colisão P0: numapo de um documento colide com nosnum de outro (G105/G114).
CAT_TRAP = {
    "codfil": 1,
    "nosnum": "888999",
    "numapo": "111222333",
    "seguradora_abrev": "TRAP",
    "ramo": "VIDA",
    "inivig": "01/01/2026",
    "fimvig": "01/01/2027",
    "cliente": "Outro Cliente Sintetico",
}

DOC_RES = {
    **CAT_RES,
    "cpf_cnpj": CPF_SINT,
    "itens": [
        {"descricao": "Incendio, Raio e Explosao", "importancia_segurada": "R$ 200.000,00"},
        {"descricao": "Danos Eletricos", "importancia_segurada": "R$ 15.000,00"},
        {"descricao": "Assistencia Residencial 24h"},
    ],
    "parcelas": [
        {"datvenc": "10/01/2026", "vlvenc": "120,00", "datquit": "09/01/2026"},
    ],
}
DOC_AUTO = {
    **CAT_AUTO,
    "cpf_cnpj": CPF_SINT,
    "itens": [{"descricao": "Colisao e Incendio do Veiculo", "importancia_segurada": "R$ 80.000,00"}],
}
# Detalhe divergente para o cenário de identity_mismatch (numapo diferente).
DOC_TRAP_DIVERGENTE = {
    **CAT_TRAP,
    "numapo": "999888777",  # diverge do numapo do catálogo -> mismatch
    "cpf_cnpj": "11122233344",
    "itens": [{"descricao": "Cobertura Que Nao Pode Vazar"}],
}


class _StubInfocapHandler(BaseHTTPRequestHandler):
    # HTTP/1.1 com Content-Length explícito: keep-alive correto para o httpx
    # (HTTP/1.0 fecha a conexão e cria corrida de reuso no Windows).
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):  # silêncio no teste
        pass

    def _json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _drain_body(self):
        # Keep-alive exige consumir o corpo do request antes de responder,
        # senão os bytes não lidos corrompem o próximo request da conexão.
        length = int(self.headers.get("Content-Length") or 0)
        if length > 0:
            self.rfile.read(length)

    def do_POST(self):
        self._drain_body()
        if urlparse(self.path).path == "/login":
            self._json({"token": "tok-sintetico-e2e"})
        else:
            self._json({"erro": "rota desconhecida"}, status=404)

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        path = parsed.path
        if path == "/cliente_cpf":
            if qs.get("cpf_cnpj") == CPF_SINT:
                self._json({"cliente": [{"codigo": CODIGO_SINT, "codfil": 1, "cliente": CLIENTE_SINT}]})
            else:
                self._json({"cliente": []}, status=404)
        elif path == "/cliente":
            if qs.get("codigo") == CODIGO_SINT:
                self._json({"cliente": [{"codigo": CODIGO_SINT, "codfil": 1, "cliente": CLIENTE_SINT, "cpf_cnpj": CPF_SINT}]})
            else:
                self._json({"cliente": []}, status=404)
        elif path == "/cliente_ligacoes":
            self._json({"documentos": [CAT_RES, CAT_AUTO]})
        elif path == "/documentos":
            texto = qs.get("texto", "")
            docs = [d for d in (CAT_RES, CAT_AUTO, CAT_TRAP) if texto in (d["numapo"], d["nosnum"])]
            self._json({"documentos": docs})
        elif path == "/documento":
            nosnum = qs.get("nosnum", "")
            mapping = {"555001": DOC_RES, "555002": DOC_AUTO, "888999": DOC_TRAP_DIVERGENTE}
            doc = mapping.get(nosnum)
            if doc:
                self._json({"documento": [doc]})
            else:
                self._json({"documento": []}, status=404)
        else:
            self._json({"erro": "rota desconhecida"}, status=404)


# ---------------------------------------------------------------------------
# Carregamento dos módulos reais com stubs mínimos (sem app completa)
# ---------------------------------------------------------------------------

def _load_file_module(dotted_name, relative_path):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(dotted_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[dotted_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _install_stubs():
    fastapi = types.ModuleType("fastapi")
    route_decorator = lambda *pa, **pk: (lambda fn: fn)
    fastapi.APIRouter = lambda *a, **k: types.SimpleNamespace(post=route_decorator, get=route_decorator)
    fastapi.Depends = lambda *a, **k: None
    fastapi.Header = lambda *a, **k: None
    fastapi.HTTPException = type(
        "HTTPException",
        (Exception,),
        {"__init__": lambda self, status_code=500, detail=None: (
            setattr(self, "status_code", status_code), setattr(self, "detail", detail), Exception.__init__(self, detail))[-1]},
    )
    sys.modules["fastapi"] = fastapi

    pydantic = types.ModuleType("pydantic")

    class BaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

        def __getattr__(self, name):  # campos não informados -> None (como Optional)
            return None

    pydantic.BaseModel = BaseModel
    pydantic.Field = lambda *a, **k: None
    sys.modules["pydantic"] = pydantic

    for name in ("app", "app.core", "app.api", "app.services", "app.providers", "app.agents"):
        module = sys.modules.setdefault(name, types.ModuleType(name))
        module.__path__ = []

    config = types.ModuleType("app.core.config")
    config.settings = types.SimpleNamespace(INFOCAP_BASE_URL="", DOCLING_SERVICE_URL=None)
    sys.modules["app.core.config"] = config

    database = types.ModuleType("app.core.database")
    database.AsyncSupabaseClient = object
    database.get_async_db = lambda: None
    sys.modules["app.core.database"] = database

    enc = types.ModuleType("app.services.encryption_service")
    enc.get_encryption_service = lambda: types.SimpleNamespace(decrypt=lambda v: v, encrypt=lambda v: v)
    sys.modules["app.services.encryption_service"] = enc

    # Módulos REAIS da SPEC-016 (puros): flags, evidence service, facts, política, compositor.
    _load_file_module("app.core.feature_flags", "app/core/feature_flags.py")
    _load_file_module("app.services.policy_document_evidence_service", "app/services/policy_document_evidence_service.py")
    _load_file_module("app.services.policy_facts", "app/services/policy_facts.py")
    _load_file_module("app.services.assistance_policy", "app/services/assistance_policy.py")
    composer = _load_file_module("app.services.policy_answer_composer", "app/services/policy_answer_composer.py")

    connector = _load_file_module("app.api.infocap_connector", "app/api/infocap_connector.py")
    port = _load_file_module("app.providers.policy_data_provider", "app/providers/policy_data_provider.py")
    return connector, port, composer


def _load_nodes():
    constants = types.ModuleType("app.core.constants")
    constants.AGENT_CONTEXT_WINDOW_SIZE = 15
    sys.modules["app.core.constants"] = constants
    state = types.ModuleType("app.agents.state")
    state.AgentState = dict
    sys.modules["app.agents.state"] = state
    utils = types.ModuleType("app.agents.utils")
    utils.extract_text_from_content = lambda c: c if isinstance(c, str) else str(c or "")
    utils.sanitize_ai_message = lambda m: m
    sys.modules["app.agents.utils"] = utils
    ctx = types.ModuleType("app.agents.context")
    ctx.build_task_context = lambda state, max_chars=2000: ""
    sys.modules["app.agents.context"] = ctx
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


def run():
    print("== SPEC-016 E6 - E2E cadeia canonica com InfoCap stub local ==\n")
    try:
        import httpx  # noqa: F401 — precisa ser o httpx REAL
    except ImportError:
        check("httpx real instalado (pip install httpx)", False, "httpx ausente")
        print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
        sys.exit(1)

    os.environ["POLICY_INTELLIGENCE_V2"] = "true"
    os.environ["BACKEND_INTERNAL_API_KEY"] = "spec016-e2e-key"

    connector, port, composer = _install_stubs()
    nodes = _load_nodes()

    server = ThreadingHTTPServer(("127.0.0.1", 0), _StubInfocapHandler)
    port_no = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    async def fake_resolver(db, *, company_id, requested_connection_id=None):
        return {
            "selected_connection": {
                "id": "conn-sintetica",
                "connection_config": {"base_url": f"http://127.0.0.1:{port_no}"},
                "encrypted_secret_ref": json.dumps({"username": "user-sintetico", "password": "senha-sintetica"}),
            }
        }

    connector._resolve_infocap_connection = fake_resolver
    provider = port.get_policy_data_provider("infocap")

    def lookup(**kwargs):
        return asyncio.run(
            provider.lookup(
                company_id="company-sintetica",
                db=object(),
                internal_key="spec016-e2e-key",
                unmasked=True,
                **kwargs,
            )
        )

    try:
        # ---- Turno 1: CPF -> cliente canônico + 2 apólices -> ambiguidade ----
        r1 = lookup(document=CPF_SINT, user_query="quais apolices o cliente tem?")
        check("T1: cadeia real executada (ambiguous_policy)", r1.get("status") == "ambiguous_policy", r1.get("status"))
        check("T1: cliente canônico veio de /cliente", r1.get("client_document") == CPF_SINT, r1.get("client_document"))
        check("T1: 2 opções listadas", len(r1.get("matches") or []) == 2, r1.get("matches"))
        check("T1: token não vaza no resultado", "tok-sintetico-e2e" not in str(r1))
        check("T1: base_url não vaza no resultado", f"127.0.0.1:{port_no}" not in str(r1))

        ctx1 = nodes._safe_infocap_policy_context(r1)
        check("T1: contexto seguro capturado", ctx1 and sorted(ctx1["policy_numbers"]) == ["1234567890", "9876543210"], ctx1)

        # ---- Turno 2: anáfora com 2 apólices -> força listagem (não escolhe) ----
        args2 = nodes._policy_context_tool_args("ela tem assistência?", ctx1)
        check("T2: anáfora com 2 apólices -> modo listagem", isinstance(args2, dict) and "policy_number" not in args2, args2)

        # ---- Turno 3: corretor escolhe o número humano -> detalhe canônico ----
        args3 = nodes._policy_context_tool_args("detalhe a apólice 1234567890", ctx1)
        check("T3: número literal trava a apólice", args3 and args3.get("policy_number") == "1234567890", args3)
        r3 = lookup(document=args3.get("document"), policy_number=args3.get("policy_number"), user_query="ela tem assistência?")
        check("T3: detalhe encontrado pela cadeia canônica", r3.get("status") == "found", r3.get("status"))
        check("T3: identidade verificada (P0)", r3.get("identity_status") == "identity_verified", r3.get("identity_status"))
        pack3 = r3.get("policy_evidence_pack") or {}
        check("T3: coberturas estruturadas extraídas do envelope", len(pack3.get("coverage_sections") or []) == 3, pack3.get("coverage_sections"))

        meta3 = composer.compose_policy_answer_with_meta(question="ela tem assistência?", result=r3)
        low3 = meta3["text"].lower()
        check("T3: política residencial aplicada", (meta3.get("assistance_policy") or {}).get("applied") is True, meta3.get("assistance_policy"))
        check("T3: resposta humana afirma com os 3 serviços", low3.strip().startswith("sim") and "eletricista" in low3 and "chaveiro" in low3, meta3["text"])
        check("T3: resposta sem jargão técnico", not any(j in low3 for j in ("nosnum", "locator", "codfil", "evidence")), meta3["text"])

        # ---- Turno 4: contexto trava na selecionada; "ela" gruda sem repetir número ----
        ctx3 = nodes._safe_infocap_policy_context(r3)
        check("T4: contexto fixa apólice selecionada", ctx3 and ctx3.get("selected_policy_number") == "1234567890", ctx3)
        args4 = nodes._policy_context_tool_args("ela cobre eletricista?", ctx3)
        check("T4: anáfora resolve direto para a selecionada", args4 and args4.get("policy_number") == "1234567890", args4)

        # ---- Turno 5: busca global por número humano ----
        r5 = lookup(policy_number="9876543210", user_query="qual a vigência dessa apólice?")
        check("T5: número humano global resolve por numapo", r5.get("status") == "found" and r5.get("matched_by") == "policy_number", {"status": r5.get("status"), "matched_by": r5.get("matched_by")})

        # ---- Turno 6 (P0): número que só existe como nosnum NUNCA abre apólice ----
        r6 = lookup(policy_number="555002", user_query="detalhe a apólice 555002")
        check("T6: colisão numapo/nosnum fail-closed (P0)", r6.get("status") == "policy_number_not_found", r6.get("status"))

        # ---- Turno 7 (P0): detalhe divergente -> identity_mismatch sem vazar dados ----
        r7 = lookup(policy_number="111222333", user_query="detalhe a apólice 111222333")
        check("T7: detalhe divergente -> identity_mismatch", r7.get("status") == "identity_mismatch", r7.get("status"))
        check("T7: mismatch não vaza cobertura/segurado", "Cobertura Que Nao Pode Vazar" not in str(r7) and "11122233344" not in str(r7), r7)
        text7 = composer.compose_policy_answer(question="detalhe a apólice 111222333", result=r7)
        check("T7: compositor mantém fail-closed", "identidade" in text7.lower() and "999888777" not in text7, text7)
    finally:
        server.shutdown()
        server.server_close()
        os.environ.pop("POLICY_INTELLIGENCE_V2", None)
        os.environ.pop("BACKEND_INTERNAL_API_KEY", None)

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        sys.exit(1)


if __name__ == "__main__":
    run()
