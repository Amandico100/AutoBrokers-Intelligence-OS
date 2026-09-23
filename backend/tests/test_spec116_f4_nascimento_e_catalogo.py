# -*- coding: utf-8 -*-
"""SPEC-116 U10 (F4) — a tela escolhe no CATÁLOGO, e nada nasce com modelo velho.

🔴 CHAMA O MOTOR (CLAUDE.md §9.4): os endpoints REAIS de `app/api/agent_config.py`
rodam num FastAPI de teste; o `model_policy` real resolve; o banco é a única
borda dublada (o catálogo e as rotas vêm do snapshot gerado do banco).

O que se afirma:
  1. gravar modelo RETIRADO (Claude 3.5 Sonnet 20240620) → 400 com frase de gente;
     gravar o mini (em saída) como escolha NOVA → 400; manter o mini que JÁ estava
     gravado → aceito (legado não é arrancado); Opus 5.5 → aceito e gravado.
  2. `/providers` lista o catálogo: nenhum retirado/bloqueado, legado marcado,
     Opus 5.5 escolhível, `models_count` = só os escolhíveis.
  3. `/rotas` devolve o modelo EFETIVO de cada papel — o MESMO que o resolvedor.
  4. `papel_do_agente` = a mesma tabela de casos do lado TS
     (`scripts/spec116-f4-nascimento.test.mjs`, `lib/admin/agent-health.ts`).
  5. OpenRouter: UMA fonte (o catálogo); o script de sync lê a mesma função; só
     entra modelo com ciclo de vida escolhível.
  6. os arquivos de NASCIMENTO não têm literal de modelo nenhum (nem DEPRECATED) —
     medido pelo mesmo checador do legacy gate.

Rodar (de backend/):  python -m pytest -q tests/test_spec116_f4_nascimento_e_catalogo.py
"""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
RAIZ = BACKEND.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.factories import model_policy as MP  # noqa: E402

SNAP = json.loads(MP.SNAPSHOT_PATH.read_text(encoding="utf-8"))
EMPRESA = "33333333-3333-4333-8333-333333333333"


# ---------------------------------------------------------------------------
# Borda: banco do catálogo (snapshot) + banco da empresa (dublê que grava)
# ---------------------------------------------------------------------------
@pytest.fixture
def catalogo():
    cat = copy.deepcopy(SNAP["catalogo"])
    pap = copy.deepcopy(SNAP["papeis"])
    original = MP.leitor_do_banco
    MP.leitor_do_banco = lambda: (cat, pap)
    MP.limpar_cache()
    yield cat, pap
    MP.leitor_do_banco = original
    MP.limpar_cache()


class _Resultado:
    def __init__(self, data):
        self.data = data


class _Tabela:
    def __init__(self, banco, nome):
        self.banco, self.nome, self._patch = banco, nome, None

    def select(self, *_a, **_k):
        if self.nome == "llm_pricing":
            raise ConnectionError("sem banco de exibição: cai no snapshot")
        return self

    def update(self, patch):
        self._patch = patch
        return self

    def eq(self, *_a):
        return self

    def execute(self):
        if self._patch is not None:
            self.banco.updates.append((self.nome, dict(self._patch)))
            return _Resultado([{"id": EMPRESA, **self._patch}])
        return _Resultado([])


class _BancoDaEmpresa:
    def __init__(self, llm_model):
        self.empresa = {"id": EMPRESA, "llm_provider": "openai", "llm_model": llm_model}
        self.updates = []
        self.client = self

    def get_company(self, company_id):
        return self.empresa if company_id == EMPRESA else None

    def table(self, nome):
        return _Tabela(self, nome)


@pytest.fixture
def api(catalogo, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api import agent_config
    from app.core.auth import require_internal_key

    banco = {"atual": _BancoDaEmpresa("gpt-4o")}
    monkeypatch.setattr(agent_config, "get_supabase_client", lambda: banco["atual"])
    app = FastAPI()
    app.include_router(agent_config.router, prefix="/api/agent")
    app.dependency_overrides[require_internal_key] = lambda: None
    return TestClient(app), banco


def _salvar(cliente, provider, model, **extra):
    corpo = {"llm_provider": provider, "llm_model": model, "llm_api_key": "UNCHANGED", **extra}
    return cliente.put(f"/api/agent/config/{EMPRESA}", json=corpo)


# ---------------------------------------------------------------------------
# 1. validação de config — contra o catálogo
# ---------------------------------------------------------------------------
def test_modelo_retirado_e_recusado_com_frase_de_gente(api):
    cliente, banco = api
    r = _salvar(cliente, "anthropic", "claude-3-5-sonnet-20240620")
    assert r.status_code == 400, r.text
    assert "não pode ser usado" in r.json()["detail"]
    assert not banco["atual"].updates, "recusado não pode gravar nada"


def test_mini_como_escolha_nova_e_recusado(api):
    cliente, banco = api
    r = _salvar(cliente, "openai", "gpt-4o-mini")
    assert r.status_code == 400, r.text
    assert "em saída" in r.json()["detail"]
    assert not banco["atual"].updates


def test_modelo_fora_do_catalogo_e_recusado(api):
    cliente, _ = api
    r = _salvar(cliente, "openai", "gpt-4.5-preview")
    assert r.status_code == 400 and "catálogo" in r.json()["detail"], r.text


def test_legado_que_ja_estava_gravado_pode_permanecer(api):
    """Linha de controle da regra do legado: o MESMO mini, já gravado, passa."""
    cliente, banco = api
    banco["atual"] = _BancoDaEmpresa("gpt-4o-mini")
    r = _salvar(cliente, "openai", "gpt-4o-mini")
    assert r.status_code == 200, r.text


def test_opus_5_5_e_aceito_e_gravado(api):
    cliente, banco = api
    r = _salvar(cliente, "anthropic", "claude-opus-5-5")
    assert r.status_code == 200, r.text
    (_, patch), = banco["atual"].updates
    assert (patch["llm_provider"], patch["llm_model"]) == ("anthropic", "claude-opus-5-5")


def test_visao_retirada_e_recusada(api):
    cliente, banco = api
    r = _salvar(cliente, "anthropic", "claude-opus-5-5", vision_model="claude-3-5-sonnet-20240620")
    assert r.status_code == 400, r.text
    assert not banco["atual"].updates


def test_provedor_divergente_e_recusado(api):
    cliente, _ = api
    r = _salvar(cliente, "openai", "claude-opus-5-5")
    assert r.status_code == 400 and "provedor" in r.json()["detail"], r.text


# ---------------------------------------------------------------------------
# 2. /providers — o catálogo, com ciclo de vida
# ---------------------------------------------------------------------------
def test_providers_lista_o_catalogo_sem_retirados(api, catalogo):
    cliente, _ = api
    r = cliente.get("/api/agent/providers")
    assert r.status_code == 200, r.text
    provs = {p["name"]: p for p in r.json()}
    todos = {m["id"]: m for p in provs.values() for m in p["modelos"]}
    cat, _ = catalogo
    assert all(cat[i]["lifecycle"] not in MP.LIFECYCLES_PROIBIDOS for i in todos), "retirado/bloqueado na tela"
    assert "claude-3-5-sonnet-20240620" not in todos
    assert todos["claude-opus-5-5"]["escolhivel"] is True
    assert todos["gpt-4o-mini"]["legado"] is True and todos["gpt-4o-mini"]["escolhivel"] is False
    assert todos["claude-sonnet-5"]["sem_temperatura"] is True
    for p in provs.values():
        assert p["models_count"] == sum(1 for m in p["modelos"] if m["escolhivel"])
    # linha de controle: o catálogo TEM retirados — a tela é que os tira
    assert any(v["lifecycle"] in MP.LIFECYCLES_PROIBIDOS and v.get("tipo") == "chat" for v in cat.values())


def test_models_por_provedor_so_escolhiveis(api):
    cliente, _ = api
    ids = cliente.get("/api/agent/models/anthropic").json()
    assert "claude-opus-5-5" in ids and "claude-3-5-sonnet-20240620" not in ids
    assert cliente.get("/api/agent/models/provedor-inventado").status_code == 404


# ---------------------------------------------------------------------------
# 3. /rotas — o efetivo, pelo MESMO resolvedor
# ---------------------------------------------------------------------------
def test_rotas_devolvem_o_modelo_do_resolvedor(api, catalogo):
    cliente, _ = api
    corpo = cliente.get("/api/agent/rotas").json()
    for papel in ("chat_principal", "atendimento", "subagente", "visao"):
        assert corpo["papeis"][papel]["model"] == MP.resolver(papel).model, papel
    assert corpo["papel_por_funcao"] == {
        "core": "chat_principal", "attendance": "atendimento", "subagent": "subagente"}
    # trocar a ROTA (banco) muda o que a tela mostra — sem deploy
    _, pap = catalogo
    pap["atendimento"].update(provider="anthropic", modelo_primario="claude-opus-5-5")
    MP.limpar_cache()
    assert cliente.get("/api/agent/rotas").json()["papeis"]["atendimento"]["model"] == "claude-opus-5-5"


# ---------------------------------------------------------------------------
# 4. função do agente → papel (a mesma tabela do lado TS)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("funcao,papel", [
    ("core", "chat_principal"), ("", "chat_principal"), (None, "chat_principal"),
    ("attendance", "atendimento"), ("insured_external", "atendimento"),
    ("subagent", "subagente"), ("qualquer_outra", "subagente"), (" CORE ", "chat_principal"),
])
def test_papel_do_agente_igual_ao_ts(funcao, papel):
    assert MP.papel_do_agente(funcao) == papel


# ---------------------------------------------------------------------------
# 5. OpenRouter — uma fonte só, e só o que o catálogo governa
# ---------------------------------------------------------------------------
def _script_de_sync():
    caminho = BACKEND / "scripts" / "sync_openrouter_models.py"
    spec = importlib.util.spec_from_file_location("sync_openrouter_models", caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_openrouter_vem_do_catalogo_e_o_script_le_a_mesma_fonte(catalogo):
    from app.api.pricing import modelos_openrouter_do_catalogo

    cat, _ = catalogo
    assert modelos_openrouter_do_catalogo() == []  # hoje o catálogo não tem OpenRouter
    cat["x-ai/grok-lab"] = {"provider": "openrouter", "lifecycle": "CANDIDATE", "classes_de_dado": ["publico"]}
    cat["x-ai/sem-ciclo"] = {"provider": "openrouter", "lifecycle": None, "classes_de_dado": ["publico"]}
    cat["x-ai/retirado"] = {"provider": "openrouter", "lifecycle": "HISTORICAL", "classes_de_dado": ["publico"]}
    MP.limpar_cache()
    assert modelos_openrouter_do_catalogo() == ["x-ai/grok-lab"]
    script = _script_de_sync()
    assert script.modelos_para_sincronizar() == ["x-ai/grok-lab"], "o script tem outra fonte"
    assert not hasattr(script, "CURATED_MODELS"), "a lista copiada voltou ao script"


# ---------------------------------------------------------------------------
# 6. nascimento sem literal de modelo — o checador do legacy gate
# ---------------------------------------------------------------------------
ARQUIVOS_DE_NASCIMENTO = (
    "lib/admin/agent-blueprints-canonical.ts",
    "lib/admin/agent-blueprints.ts",
    "lib/admin/blueprint-release.ts",
    "lib/admin/provision-tenant.ts",
    "lib/admin/agent-health.ts",
    "app/api/admin/sandbox/bootstrap-tenant/route.ts",
    "app/admin/auxiliares/page.tsx",
    "app/api/admin/auxiliaries/templates/[templateId]/install/route.ts",
    "components/admin/AgentConfigModal.tsx",
    "backend/app/api/pricing.py",
)


def _checador():
    caminho = BACKEND / "tests" / "test_nenhum_modelo_fora_do_catalogo.py"
    spec = importlib.util.spec_from_file_location("legacy_gate", caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_arquivos_de_nascimento_sem_literal_de_modelo():
    """Mais estrito que o legacy gate: aqui nem DEPRECATED (o mini) pode nascer."""
    gate = _checador()
    achados = {a: gate.literais_do_texto((RAIZ / a).read_text(encoding="utf-8"))
               for a in ARQUIVOS_DE_NASCIMENTO}
    achados = {a: v for a, v in achados.items() if v}
    assert not achados, f"literal de modelo num arquivo de nascimento/UI: {achados}"
    # linha de controle: o mesmo checador ACHA o mini num blueprint
    assert gate.literais_do_texto("default_llm_model: 'gpt-4o-mini',") == {"gpt-4o-mini"}
