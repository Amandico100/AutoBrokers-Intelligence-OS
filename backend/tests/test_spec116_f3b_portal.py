# -*- coding: utf-8 -*-
"""SPEC-116 F3b (U9) — o cérebro do PORTAL pede a rota `portal_decisao`.

🔴 CHAMA O MOTOR (CLAUDE.md §9.4): `adaptive.decide_next_action` — a função que o
laço do portal chama a cada tela — com o `modelo_do_portal` real. Dublês SÓ na borda:
  · o REST do Supabase (`httpx.MockTransport`): responde `llm_papeis` e
    `llm_pricing` com as linhas do snapshot e GUARDA o POST em `token_usage_logs`;
  · a REDE do provedor: um `httpx` de mentira no `import httpx` da hora da
    chamada (o mesmo ponto que a bancada desvia), que GUARDA cada pedido.

Gates:
  · a rota decide (gpt-4o hoje) e `PORTAL_VISION_MODEL` fica ignorado;
  · 🔴 500 do provedor NÃO vira chamada ao gpt-4o-mini: UMA chamada, e o laço
    recebe `ask_human` com o motivo (mutação: restaurar a reserva calada ⇒ VERMELHO);
  · o uso é GRAVADO no ledger (service_type='portal', company_id do job, papel);
  · reserva só se a rota declarar, com motivo no ledger;
  · o leitor do portal e o `model_policy.resolver` concordam caso a caso;
  · o custo é a mesma conta do `usage_service`.

Rodar (de backend/):  .venv/Scripts/python -m pytest -q tests/test_spec116_f3b_portal.py
"""
from __future__ import annotations

import asyncio
import copy
import json
import sys
import types
from pathlib import Path
from urllib.parse import unquote

import httpx
import pytest

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.factories import model_policy as MP  # noqa: E402
from portal_worker import adaptive as AD  # noqa: E402
from portal_worker import modelo_do_portal as PM  # noqa: E402

SNAP = json.loads(MP.SNAPSHOT_PATH.read_text(encoding="utf-8"))
EMPRESA_A = "11111111-1111-4111-8111-111111111111"
TELA = {"heading": "Dados do veiculo", "text": "Informe a placa", "fields": [{"label": "Placa"}]}
DADOS = {"placa": "ABC1D23"}
ACAO_OK = {"action": "fill", "target": "Placa", "value": "ABC1D23", "reason": "tela pede placa"}


# ---------------------------------------------------------------------------
# Borda 1 — o REST do Supabase
# ---------------------------------------------------------------------------
class SupabaseRest:
    def __init__(self):
        self.cat = copy.deepcopy(SNAP["catalogo"])
        self.pap = copy.deepcopy(SNAP["papeis"])
        self.ledger = []
        self.fora = False
        self.leituras = 0

    def __call__(self, req: httpx.Request) -> httpx.Response:
        if self.fora:
            return httpx.Response(503, json={"message": "fora"})
        caminho = req.url.path
        if req.method == "GET" and caminho.endswith("/llm_papeis"):
            self.leituras += 1
            papel = unquote(req.url.params.get("papel", "")).removeprefix("eq.")
            return httpx.Response(200, json=[r for k, r in self.pap.items() if k == papel])
        if req.method == "GET" and caminho.endswith("/llm_pricing"):
            nomes = unquote(req.url.params.get("model_name", ""))
            nomes = [n.strip('"') for n in nomes.removeprefix("in.(").removesuffix(")").split(",")]
            return httpx.Response(200, json=[self.cat[n] for n in nomes if n in self.cat])
        if req.method == "POST" and caminho.endswith("/token_usage_logs"):
            self.ledger.append(json.loads(req.content))
            return httpx.Response(201)
        return httpx.Response(404)


# ---------------------------------------------------------------------------
# Borda 2 — a rede do provedor (o `import httpx` da hora da chamada)
# ---------------------------------------------------------------------------
class Provedor:
    def __init__(self):
        self.pedidos = []
        self.status = [200]

    def resposta(self, corpo):
        if "messages" in corpo and "system" in corpo:  # anthropic
            return {"model": corpo["model"] + "-20260101", "content": [
                {"type": "text", "text": json.dumps(ACAO_OK)}],
                "usage": {"input_tokens": 1500, "output_tokens": 60,
                          "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}}
        return {"model": corpo["model"] + "-2024-08-06",
                "choices": [{"message": {"content": json.dumps(ACAO_OK)}}],
                "usage": {"prompt_tokens": 1500, "completion_tokens": 60}}

    def cliente(self):
        prov = self

        class _Resp:
            def __init__(self, status, corpo):
                self.status_code, self._corpo = status, corpo

            def json(self):
                return self._corpo

        class _Cliente:
            def __init__(self, *a, **k):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *e):
                return False

            async def post(self, url, headers=None, json=None, **_k):  # noqa: A002
                prov.pedidos.append({"url": str(url), "corpo": json, "headers": dict(headers or {})})
                st = prov.status[min(len(prov.pedidos), len(prov.status)) - 1]
                if st >= 400:
                    return _Resp(st, {"error": {"message": "falha injetada"}})
                return _Resp(200, prov.resposta(json))

        return _Cliente

    @property
    def modelos(self):
        return [p["corpo"]["model"] for p in self.pedidos]


@pytest.fixture
def borda(monkeypatch):
    rest = SupabaseRest()
    prov = Provedor()
    monkeypatch.setattr(PM, "transporte_do_supabase", httpx.MockTransport(rest))
    monkeypatch.setenv("SUPABASE_URL", "https://banco-de-teste.invalid")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "chave-de-servico-falsa")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-teste-falsa")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-teste-falsa")
    monkeypatch.delenv("PORTAL_VISION_MODEL", raising=False)
    proxy = types.ModuleType("httpx")
    proxy.__dict__.update(httpx.__dict__)
    proxy.AsyncClient = prov.cliente()
    monkeypatch.setitem(sys.modules, "httpx", proxy)
    PM.limpar_cache()
    yield types.SimpleNamespace(rest=rest, prov=prov)
    PM.limpar_cache()


def _decidir(**kw):
    async def _vai():
        AD._JOB_EM_CURSO.set({"company_id": EMPRESA_A, "job_id": "job-1"})
        return await AD.decide_next_action(TELA, "abrir vidros", DADOS, [], **kw)
    return asyncio.run(_vai())


# ---------------------------------------------------------------------------
# A rota decide; o env é ignorado; o uso é gravado
# ---------------------------------------------------------------------------
def test_a_rota_decide_e_o_uso_vai_para_o_ledger(borda, monkeypatch):
    monkeypatch.setenv("PORTAL_VISION_MODEL", "gpt-4o-mini")   # o env de antes: IGNORADO
    acao = _decidir()
    assert acao == ACAO_OK
    assert borda.prov.modelos == [borda.rest.pap["portal_decisao"]["modelo_primario"]] == ["gpt-4o"]
    corpo = borda.prov.pedidos[0]["corpo"]
    assert corpo["temperature"] == 0 and corpo["response_format"] == {"type": "json_object"}
    assert borda.rest.leituras == 1, "a rota veio do BANCO"

    assert len(borda.rest.ledger) == 1, "o portal agora deixa linha no ledger"
    linha = borda.rest.ledger[0]
    assert linha["service_type"] == "portal" and linha["company_id"] == EMPRESA_A
    d = linha["details"]
    assert (d["papel"], d["modelo_resolvido"], d["modelo_real"]) == (
        "portal_decisao", "gpt-4o", "gpt-4o-2024-08-06")
    assert d["reserva_usada"] is False and d["job_id"] == "job-1" and d["origem_da_rota"] == "rota"
    assert (linha["input_tokens"], linha["output_tokens"]) == (1500, 60)
    assert linha["total_cost_usd"] == pytest.approx(1500 / 1e6 * 2.5 + 60 / 1e6 * 10)


def test_trocar_a_rota_troca_o_modelo_sem_deploy(borda):
    borda.rest.pap["portal_decisao"].update(provider="anthropic", modelo_primario="claude-opus-5",
                                            esforco="high")
    assert _decidir() == ACAO_OK
    ped = borda.prov.pedidos[0]
    assert ped["url"].endswith("/v1/messages") and ped["corpo"]["model"] == "claude-opus-5"
    assert "temperature" not in ped["corpo"], "Claude 5 recusa sampling (400) — o catálogo manda"
    assert ped["corpo"]["output_config"] == {"effort": "high"}
    assert ped["headers"]["x-api-key"] and ped["headers"]["anthropic-version"]
    assert borda.rest.ledger[0]["details"]["modelo_resolvido"] == "claude-opus-5"


# ---------------------------------------------------------------------------
# 🔴 O defeito: 500 → gpt-4o-mini calado. Agora: UMA chamada, erro com motivo.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("status", [429, 500, 503, 404])
def test_erro_do_provedor_nao_vira_chamada_ao_mini(borda, status):
    borda.prov.status = [status, 200]
    acao = _decidir()
    assert borda.prov.modelos == ["gpt-4o"], (
        f"depois do {status} saiu outra chamada: {borda.prov.modelos} — rebaixamento calado")
    assert acao["action"] == "ask_human" and acao["reason"] == "llm error"
    assert f"HTTP {status}" in acao["value"], "o motivo chega ao laço (vira o needs_human)"
    assert borda.rest.ledger == [], "sem resposta, sem tokens — nada inventado no ledger"


def test_reserva_so_quando_a_rota_declara_e_com_motivo(borda):
    borda.rest.pap["portal_decisao"].update(provider_reserva="anthropic",
                                            modelo_reserva="claude-sonnet-5")
    borda.prov.status = [500, 200]
    assert _decidir() == ACAO_OK
    assert borda.prov.modelos == ["gpt-4o", "claude-sonnet-5"]
    d = borda.rest.ledger[0]["details"]
    assert d["reserva_usada"] is True and "HTTP 500" in d["motivo_reserva"]
    assert borda.rest.ledger[0]["model_name"] == "claude-sonnet-5"


def test_rota_para_modelo_bloqueado_e_recusada_sem_chamada(borda):
    borda.rest.pap["portal_decisao"].update(provider="anthropic",
                                            modelo_primario="claude-3-5-sonnet-20241022")
    acao = _decidir()
    assert acao["action"] == "ask_human" and "lifecycle" in acao["value"]
    assert borda.prov.pedidos == []


# ---------------------------------------------------------------------------
# Banco fora → snapshot · sem snapshot → erro explícito
# ---------------------------------------------------------------------------
def test_banco_fora_usa_o_snapshot(borda):
    borda.rest.fora = True
    assert _decidir() == ACAO_OK
    assert borda.prov.modelos == [SNAP["papeis"]["portal_decisao"]["modelo_primario"]]


def test_sem_banco_e_sem_snapshot_e_erro_explicito(borda, monkeypatch, tmp_path):
    borda.rest.fora = True
    monkeypatch.setattr(PM, "caminhos_do_snapshot", lambda: [tmp_path / "nao-existe.json"])
    acao = _decidir()
    assert acao["action"] == "ask_human" and "snapshot" in acao["value"]
    assert borda.prov.pedidos == [], "nenhum modelo escolhido por conta própria"


def test_a_imagem_do_portal_leva_o_snapshot():
    """A FORMA da declaração (§9.4 exceção): o Dockerfile copia o snapshot para
    o caminho que `caminhos_do_snapshot()` procura primeiro na imagem."""
    docker = (BACKEND / "portal_worker" / "Dockerfile").read_text(encoding="utf-8")
    assert ("COPY backend/app/factories/modelos_snapshot.json "
            "/app/portal_worker/modelos_snapshot.json") in docker
    assert PM.caminhos_do_snapshot()[0].name == "modelos_snapshot.json"


# ---------------------------------------------------------------------------
# A injeção da bancada
# ---------------------------------------------------------------------------
def test_chamar_modelo_recebe_o_pedido_e_nao_escreve_no_ledger(borda):
    vistos = []

    async def _braco(pedido):
        vistos.append(pedido)
        return {"choices": [{"message": {"content": json.dumps(ACAO_OK)}}]}

    assert _decidir(chamar_modelo=_braco) == ACAO_OK
    assert vistos[0]["papel"] == "portal_decisao" and vistos[0]["model"] == "gpt-4o"
    assert "headers" not in vistos[0], "o pedido entregue à bancada não carrega segredo"
    assert borda.prov.pedidos == [] and borda.rest.ledger == []

    def _braco_que_falha(pedido):
        raise RuntimeError("429")

    acao = _decidir(chamar_modelo=_braco_que_falha)
    assert acao["action"] == "ask_human"


# ---------------------------------------------------------------------------
# Uma fonte de verdade: o leitor do portal concorda com o Model Router
# ---------------------------------------------------------------------------
MUTACOES_DA_ROTA = [
    ("como está", {}),
    ("outro primário", {"provider": "anthropic", "modelo_primario": "claude-sonnet-5"}),
    ("bloqueado", {"provider": "anthropic", "modelo_primario": "claude-3-5-sonnet-20241022"}),
    ("sem pii", {"provider": "xiaomi", "modelo_primario": "mimo-v2.6-pro"}),
    ("fora do catálogo", {"provider": "openai", "modelo_primario": "gpt-4.5-preview"}),
    ("provedor divergente", {"provider": "anthropic", "modelo_primario": "gpt-4o"}),
    ("esforço inválido", {"provider": "anthropic", "modelo_primario": "claude-opus-5",
                          "esforco": "turbo"}),
    ("reserva histórica", {"provider_reserva": "openai", "modelo_reserva": "gpt-5.1"}),
]


@pytest.mark.parametrize("nome,mudanca", MUTACOES_DA_ROTA, ids=[m[0] for m in MUTACOES_DA_ROTA])
def test_o_portal_e_o_model_router_decidem_igual(nome, mudanca, monkeypatch):
    cat = copy.deepcopy(SNAP["catalogo"])
    pap = copy.deepcopy(SNAP["papeis"])
    pap["portal_decisao"].update(mudanca)
    monkeypatch.setattr(MP, "leitor_do_banco", lambda: (cat, pap))
    MP.limpar_cache()

    async def _ler():
        return cat, pap

    monkeypatch.setattr(PM, "leitor_do_banco", _ler)
    PM.limpar_cache()
    try:
        esperado = MP.resolver("portal_decisao")
    except MP.ModeloNaoResolvido:
        esperado = None
    try:
        obtido = asyncio.run(PM.resolver_rota())
    except PM.ModeloDoPortalIndisponivel:
        obtido = None
    finally:
        MP.limpar_cache()
        PM.limpar_cache()
    if esperado is None:
        assert obtido is None, f"{nome}: o Model Router RECUSA e o portal aceitou {obtido}"
        return
    assert obtido is not None, f"{nome}: o Model Router aceita e o portal recusou"
    assert (obtido.provider, obtido.model, obtido.effort, obtido.api_surface, obtido.classe_de_dado) == (
        esperado.provider, esperado.model, esperado.effort, esperado.api_surface,
        esperado.classe_de_dado)
    assert (obtido.reserva and obtido.reserva.model) == (esperado.reserva and esperado.reserva.model)


def test_as_listas_de_regra_sao_as_do_model_router():
    assert PM.LIFECYCLES_USAVEIS == MP.LIFECYCLES_USAVEIS
    assert PM.CLASSES_DE_DADO == MP.CLASSES_DE_DADO
    assert PM.NIVEIS_DE_ESFORCO == MP.NIVEIS_DE_ESFORCO


@pytest.mark.parametrize("modelo,uso", [
    ("gpt-4o", {"input": 1500, "output": 60, "cached": 500, "cache_read": 0, "cache_write": 0}),
    ("claude-opus-5", {"input": 3000, "output": 400, "cached": 0, "cache_read": 1000, "cache_write": 200}),
    ("gpt-6-sol", {"input": 300_000, "output": 1000, "cached": 0, "cache_read": 0, "cache_write": 0}),
])
def test_o_custo_e_a_mesma_conta_do_usage_service(modelo, uso, monkeypatch):
    import app.services.usage_service as U

    monkeypatch.setattr(U, "_pricing_cache", U._precos_do_snapshot())
    monkeypatch.setattr(U, "_cache_loaded_at", 10 ** 12)
    svc = U.UsageService.__new__(U.UsageService)
    esperado = svc.calculate_cost(modelo, uso["input"], uso["output"], uso["cache_write"],
                                  uso["cache_read"], uso["cached"])
    obtido = PM.custo_usd(SNAP["catalogo"][modelo], dict(uso, reasoning=0))
    assert obtido == pytest.approx(esperado) and esperado > 0


# ---------------------------------------------------------------------------
# SPEC-116 F6 — a ROTA INJETADA (só a bancada passa): o corpo é o do BRAÇO
# ---------------------------------------------------------------------------
def _rota_injetada(provider, model, effort):
    """O `ModeloDoPortal` que a bancada injeta, montado pelo MESMO resolvedor."""
    from app.services.evals.bancada import Braco, rota_do_portal_para

    r = MP.resolver("portal_decisao", override={"provider": provider, "model": model, "effort": effort})
    return rota_do_portal_para(Braco(provider, model, effort), r)


def test_sem_rota_injetada_nada_muda(borda):
    """Controle: sem `rota=`, o pedido é o da rota do banco (gpt-4o, JSON mode, temperature 0)."""
    assert _decidir() == ACAO_OK
    assert borda.prov.modelos == ["gpt-4o"] and borda.rest.leituras == 1
    corpo = borda.prov.pedidos[0]["corpo"]
    assert corpo["temperature"] == 0 and corpo["response_format"] == {"type": "json_object"}


@pytest.mark.parametrize("provider,model,effort,url,sem_temperatura", [
    ("anthropic", "claude-sonnet-5", "low", "/v1/messages", True),
    ("openai", "gpt-6-sol", "medium", "/v1/responses", True),
    ("openai", "gpt-4o-mini", None, "/v1/chat/completions", False),
])
def test_rota_injetada_monta_o_corpo_do_provedor_do_braco(borda, provider, model, effort, url,
                                                          sem_temperatura):
    rota = _rota_injetada(provider, model, effort)
    assert _decidir(rota=rota) == ACAO_OK
    ped = borda.prov.pedidos[0]
    assert ped["url"].endswith(url) and ped["corpo"]["model"] == model
    assert borda.rest.leituras == 0, "com a rota injetada o banco NÃO é lido"
    assert ("temperature" not in ped["corpo"]) is sem_temperatura, (
        f"{model}: temperature só onde o catálogo permite (sampling_ok)")
    if provider == "anthropic" and effort:
        assert ped["corpo"]["output_config"] == {"effort": effort}
    if url.endswith("/responses"):
        assert ped["corpo"]["reasoning"] == {"effort": effort} and ped["corpo"]["store"] is False
        assert ped["corpo"]["text"] == {"format": {"type": "json_object"}}
