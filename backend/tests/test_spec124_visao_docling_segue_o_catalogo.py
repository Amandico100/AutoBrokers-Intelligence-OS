# -*- coding: utf-8 -*-
"""SPEC-124 F2 · D4 · G5 — o docling OBEDECE AO CATÁLOGO (P-122-01).

🔴 O TESTE DO FIO. Atravessa o fio INTEIRO com o MOTOR real, dublê só na borda:

    smith-api  SanitizationService._docling_parse(extract_images=True, company_id=)
      → model_policy.resolver("visao_documento")          (o resolvedor REAL; o BANCO é o dublê)
      → POST /parse  (form: vision_provider/vision_model/vision_effort)
    docling    main.submit_parse  (o app FastAPI REAL, por TestClient)
      → tasks.parse_document  (a task Celery REAL, executada por `apply`)
      → tasks._docling_parse → PictureDescriptionApiOptions(params=…)   ← o que iria ao provedor
      → resultado com metadata.visao {modelo usado, imagens descritas, uso real de tokens}
    smith-api  → GET /status → o LEDGER (`token_usage_logs` via UsageService.track_cost_sync)

Bordas dubladas: a biblioteca `docling` (não instalada aqui; o conversor devolve 2 imagens descritas com
o `usage` que o docling 2.130 grava em `meta.description` — 📊 lido no wheel docling-slim 2.130.0,
`picture_description_base_model.py:107-128`), o MinIO, o broker do Celery, o banco do catálogo e o ledger.

G5: trocar a ROTA no catálogo muda o modelo enviado ao docling SEM mexer em env; sem o campo (chamador
antigo) vale o paraquedas `VISION_MODEL`.

Rodar (de backend/):  python -m pytest -q tests/test_spec124_visao_docling_segue_o_catalogo.py
"""
from __future__ import annotations

import copy
import importlib
import importlib.util
import json
import os
import sys
import types
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
DOCLING_APP = BACKEND.parent / "docling-service" / "app"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.factories import model_policy as MP  # noqa: E402
# importados AQUI (cwd = backend/): o fixture do docling troca o cwd e o Settings do backend lê o `.env` dele
from app.services import sanitization_service as SS  # noqa: E402
from app.services import usage_service as US  # noqa: E402

EMPRESA_A = "00000000-0000-4000-8000-0000000000a1"
EMPRESA_B = "00000000-0000-4000-8000-0000000000b2"
SNAP = json.loads(MP.SNAPSHOT_PATH.read_text(encoding="utf-8"))

#: O `usage` que a OpenAI devolve no Chat Completions (o docling o guarda por imagem).
USO_POR_IMAGEM = {"prompt_tokens": 1200, "completion_tokens": 300, "total_tokens": 1500,
                  "prompt_tokens_details": {"cached_tokens": 0},
                  "completion_tokens_details": {"reasoning_tokens": 120}}


# ---------------------------------------------------------------------------
# A borda: a biblioteca docling (dublê que registra o que o serviço lhe passa)
# ---------------------------------------------------------------------------
class _Registro:
    opcoes_de_visao: list = []
    pipelines: list = []


def _instalar_docling_duble(monkeypatch, imagens: int = 2):
    _Registro.opcoes_de_visao = []
    _Registro.pipelines = []

    class PictureDescriptionApiOptions:
        def __init__(self, **kw):
            self.kw = kw
            _Registro.opcoes_de_visao.append(kw)

    class PdfPipelineOptions:
        def __init__(self):
            _Registro.pipelines.append(self)

    class _Desc:
        def __init__(self, texto, uso):
            self.text = texto
            self._extra = {"docling__usage": uso} if uso is not None else {}

        def get_custom_part(self):
            return self._extra

    class _Pic:
        def __init__(self, desc):
            self.meta = types.SimpleNamespace(description=desc)
            self.annotations = []

    class _Doc:
        def __init__(self, descrever: bool):
            self.pages = {1: object()}
            self.tables = []
            self.pictures = [_Pic(_Desc("[INFORMACIONAL] tabela de coberturas", copy.deepcopy(USO_POR_IMAGEM))
                                  if descrever else None) for _ in range(imagens)]

        def export_to_markdown(self):
            return "# Documento\n\ntexto"

    class DocumentConverter:
        def __init__(self, format_options):
            po = list(format_options.values())[0].pipeline_options
            self.descrever = bool(getattr(po, "do_picture_description", False))

        def convert(self, _caminho):
            return types.SimpleNamespace(document=_Doc(self.descrever))

    class PdfFormatOption:
        def __init__(self, pipeline_options):
            self.pipeline_options = pipeline_options

    base = types.ModuleType("docling.datamodel.base_models")
    base.InputFormat = types.SimpleNamespace(PDF="pdf")
    po = types.ModuleType("docling.datamodel.pipeline_options")
    po.PdfPipelineOptions = PdfPipelineOptions
    po.PictureDescriptionApiOptions = PictureDescriptionApiOptions
    conv = types.ModuleType("docling.document_converter")
    conv.DocumentConverter = DocumentConverter
    conv.PdfFormatOption = PdfFormatOption
    for nome, mod in {"docling": types.ModuleType("docling"),
                      "docling.datamodel": types.ModuleType("docling.datamodel"),
                      "docling.datamodel.base_models": base,
                      "docling.datamodel.pipeline_options": po,
                      "docling.document_converter": conv}.items():
        monkeypatch.setitem(sys.modules, nome, mod)


# ---------------------------------------------------------------------------
# O serviço docling REAL (pacote `app` dele carregado sob outro nome: o `app` daqui é o backend)
# ---------------------------------------------------------------------------
class _Minio:
    guardado: dict = {}

    def put_object(self, bucket_name, object_name, data, length, content_type):
        _Minio.guardado[object_name] = data.read()

    def fget_object(self, bucket_name, object_name, file_path):
        assert object_name in _Minio.guardado

    def remove_object(self, bucket_name, object_name):
        _Minio.guardado.pop(object_name, None)


@pytest.fixture
def docling(monkeypatch, tmp_path):
    """O app FastAPI + a task Celery do docling-service, com a biblioteca/MinIO/broker dublados."""
    _instalar_docling_duble(monkeypatch)
    monkeypatch.chdir(tmp_path)            # o Settings do docling lê `.env` do cwd — não o do backend
    monkeypatch.setenv("ENV", "test")
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("VISION_MODEL", raising=False)
    monkeypatch.delenv("VISION_REASONING_EFFORT", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-duble-do-teste")
    monkeypatch.setenv("SERVICE_KEY", "")
    for nome in [n for n in sys.modules if n == "docling_svc" or n.startswith("docling_svc.")]:
        monkeypatch.delitem(sys.modules, nome)
    spec = importlib.util.spec_from_file_location("docling_svc", DOCLING_APP / "__init__.py",
                                                  submodule_search_locations=[str(DOCLING_APP)])
    pacote = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "docling_svc", pacote)
    spec.loader.exec_module(pacote)
    main = importlib.import_module("docling_svc.main")
    tasks = importlib.import_module("docling_svc.tasks")
    monkeypatch.setattr(main, "get_minio_client", lambda: _Minio())
    monkeypatch.setattr(tasks, "_get_minio_client", lambda: _Minio())
    resultados: dict = {}

    def _apply_async(args=None, kwargs=None, task_id=None, queue=None):
        # a task REAL, executada no processo (o broker é a borda)
        resultados[task_id] = main.parse_document.apply(args=args, kwargs=kwargs or {}, task_id=task_id)
        return resultados[task_id]

    monkeypatch.setattr(main.parse_document, "apply_async", _apply_async)
    monkeypatch.setattr(main.celery_app, "AsyncResult", lambda tid: resultados[tid])
    from fastapi.testclient import TestClient

    cliente = TestClient(main.app)
    yield types.SimpleNamespace(main=main, tasks=tasks, cliente=cliente, resultados=resultados)
    for nome in [n for n in sys.modules if n == "docling_svc" or n.startswith("docling_svc.")]:
        sys.modules.pop(nome, None)


@pytest.fixture
def catalogo(monkeypatch):
    """O BANCO do catálogo (borda) — a rota `visao_documento` é o que o teste manda."""
    estado = {"rota": copy.deepcopy(SNAP["papeis"]["visao_documento"])}

    def _leitor():
        papeis = copy.deepcopy(SNAP["papeis"])
        papeis["visao_documento"] = copy.deepcopy(estado["rota"])
        return copy.deepcopy(SNAP["catalogo"]), papeis

    monkeypatch.setattr(MP, "leitor_do_banco", _leitor)
    MP.limpar_cache()
    yield estado
    MP.limpar_cache()


class _Ledger:
    def __init__(self):
        self.linhas = []

    def track_cost_sync(self, **kw):
        self.linhas.append(kw)
        return True


@pytest.fixture
def smith(monkeypatch, docling):
    """O chamador REAL (`SanitizationService._docling_parse`) falando HTTP com o app REAL do docling."""
    ledger = _Ledger()
    monkeypatch.setattr(US, "get_usage_service", lambda: ledger)
    monkeypatch.setattr(SS.settings, "DOCLING_SERVICE_URL", "http://docling.invalid")
    monkeypatch.setattr(SS.settings, "DOCLING_SERVICE_KEY", "")
    monkeypatch.setattr(SS.settings, "DOCLING_POLL_INTERVAL", 1)
    monkeypatch.setattr(SS.settings, "DOCLING_MAX_WAIT", 5)
    import httpx
    import time as _time

    enviados: list = []

    def _post(url, files=None, data=None, headers=None, timeout=None):
        enviados.append(dict(data or {}))
        caminho = url.split("docling.invalid", 1)[1]
        return docling.cliente.post(caminho, files=files, data=data, headers=headers)

    def _get(url, headers=None, timeout=None):
        return docling.cliente.get(url.split("docling.invalid", 1)[1], headers=headers)

    monkeypatch.setattr(httpx, "post", _post)
    monkeypatch.setattr(httpx, "get", _get)
    monkeypatch.setattr(_time, "sleep", lambda _s: None)
    servico = object.__new__(SS.SanitizationService)
    return types.SimpleNamespace(servico=servico, ledger=ledger, enviados=enviados, SS=SS)


def _pdf(tmp_path) -> str:
    p = tmp_path / "documento.pdf"
    p.write_bytes(b"%PDF-1.4 duble")
    return str(p)


def _params_enviados_ao_provedor() -> dict:
    assert _Registro.opcoes_de_visao, "o docling não montou o pedido de visão"
    return _Registro.opcoes_de_visao[-1]["params"]


# ===========================================================================
# O FIO — a rota do catálogo chega ao pedido do docling, e o custo ao ledger
# ===========================================================================
def test_o_fio_a_rota_do_catalogo_chega_ao_docling_e_o_custo_ao_ledger(smith, docling, catalogo, tmp_path):
    md, meta = smith.servico._docling_parse(_pdf(tmp_path), extract_images=True, company_id=EMPRESA_A)
    rota = SNAP["papeis"]["visao_documento"]
    params = _params_enviados_ao_provedor()
    assert params["model"] == rota["modelo_primario"]
    assert params.get("reasoning_effort") == rota["esforco"]
    assert smith.enviados[-1]["vision_model"] == rota["modelo_primario"]
    assert smith.enviados[-1]["vision_provider"] == "openai"
    visao = meta["visao"]
    assert visao["origem"] == "chamador" and visao["modelo"] == rota["modelo_primario"]
    assert visao["imagens_descritas"] == 2
    # o LEDGER: uso REAL somado das 2 imagens, na corretora que pediu, com o papel
    assert len(smith.ledger.linhas) == 1
    linha = smith.ledger.linhas[0]
    assert linha["model"] == rota["modelo_primario"] and linha["company_id"] == EMPRESA_A
    assert linha["input_tokens"] == 2 * USO_POR_IMAGEM["prompt_tokens"]
    assert linha["output_tokens"] == 2 * USO_POR_IMAGEM["completion_tokens"]
    assert linha["details"]["papel"] == "visao_documento"
    assert linha["details"]["estimativa"] is False
    assert linha["details"]["imagens_descritas"] == 2


def test_g5_trocar_a_rota_no_catalogo_muda_o_modelo_do_docling_sem_mexer_em_env(smith, docling, catalogo,
                                                                                tmp_path):
    env_antes = (docling.main.settings.VISION_MODEL, os.environ.get("VISION_MODEL"))
    catalogo["rota"] = {**catalogo["rota"], "modelo_primario": "gpt-6-luna", "esforco": "medium"}
    MP.limpar_cache()
    smith.servico._docling_parse(_pdf(tmp_path), extract_images=True, company_id=EMPRESA_B)
    params = _params_enviados_ao_provedor()
    assert params["model"] == "gpt-6-luna", params
    assert params.get("reasoning_effort") == "medium"
    assert (docling.main.settings.VISION_MODEL, os.environ.get("VISION_MODEL")) == env_antes, "env mexida"
    assert params["model"] != docling.main.settings.VISION_MODEL, "a prova exige rota ≠ paraquedas"
    linha = smith.ledger.linhas[-1]
    assert linha["model"] == "gpt-6-luna" and linha["company_id"] == EMPRESA_B


def test_paraquedas_chamador_antigo_sem_o_campo_continua_funcionando(docling, tmp_path):
    """Contrato compatível: o POST de antes (só file + extract_images) roda com `VISION_MODEL`."""
    r = docling.cliente.post("/parse", files={"file": ("a.pdf", b"%PDF-1.4")},
                             data={"extract_images": "true"})
    assert r.status_code == 202, r.text
    st = docling.cliente.get(f"/status/{r.json()['task_id']}").json()
    assert st["status"] == "completed"
    params = _params_enviados_ao_provedor()
    assert params["model"] == docling.main.settings.VISION_MODEL
    assert params.get("reasoning_effort") == docling.main.settings.VISION_REASONING_EFFORT
    assert st["metadata"]["visao"]["origem"] == "paraquedas"
    # e a task chamada com a assinatura ANTIGA (4 args posicionais, mensagem já na fila) também roda
    _Minio.guardado["docling-temp/x/a.pdf"] = b"x"
    antigo = docling.main.parse_document.apply(args=["t-antigo", "docling-temp/x/a.pdf", "a.pdf", True])
    assert antigo.result["metadata"]["visao"]["origem"] == "paraquedas"


def test_provedor_que_o_docling_nao_fala_e_recusado_com_400(docling):
    r = docling.cliente.post("/parse", files={"file": ("a.pdf", b"%PDF-1.4")},
                             data={"extract_images": "true", "vision_provider": "anthropic",
                                   "vision_model": "claude-sonnet-5-5"})
    assert r.status_code == 400 and "anthropic" in r.text
    r = docling.cliente.post("/parse", files={"file": ("a.pdf", b"%PDF-1.4")},
                             data={"extract_images": "true", "vision_provider": "openai",
                                   "vision_model": "gpt-6-luna", "vision_effort": "turbo"})
    assert r.status_code == 400 and "turbo" in r.text


def test_rota_anthropic_cai_na_reserva_openai_e_sem_reserva_falante_vai_ao_paraquedas(smith, docling, catalogo,
                                                                                    tmp_path):
    catalogo["rota"] = {**catalogo["rota"], "provider": "anthropic", "modelo_primario": "claude-sonnet-5-5",
                        "esforco": "low", "provider_reserva": "openai", "modelo_reserva": "gpt-6.1-sol",
                        "esforco_reserva": "medium"}
    MP.limpar_cache()
    _, meta = smith.servico._docling_parse(_pdf(tmp_path), extract_images=True, company_id=EMPRESA_A)
    assert _params_enviados_ao_provedor()["model"] == "gpt-6.1-sol"
    assert meta["visao"]["origem"] == "chamador"
    catalogo["rota"] = {**catalogo["rota"], "provider_reserva": None, "modelo_reserva": None,
                        "esforco_reserva": None}
    MP.limpar_cache()
    _, meta = smith.servico._docling_parse(_pdf(tmp_path), extract_images=True, company_id=EMPRESA_A)
    assert "vision_model" not in smith.enviados[-1]
    assert meta["visao"]["origem"] == "paraquedas"


def test_sem_extract_images_nada_de_visao_nem_ledger(smith, docling, catalogo, tmp_path):
    _, meta = smith.servico._docling_parse(_pdf(tmp_path), extract_images=False, company_id=EMPRESA_A)
    assert "vision_model" not in smith.enviados[-1]
    assert not _Registro.opcoes_de_visao
    assert meta["visao"]["origem"] == "desligada" and meta["visao"]["imagens_descritas"] == 0
    assert smith.ledger.linhas == []
