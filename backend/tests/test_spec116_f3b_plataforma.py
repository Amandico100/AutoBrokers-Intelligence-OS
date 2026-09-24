# -*- coding: utf-8 -*-
"""SPEC-116 F3b (U8 plataforma) — cada trabalho de plataforma pede o seu PAPEL.

🔴 CHAMA O MOTOR (CLAUDE.md §9.4). Cada teste chama a FUNÇÃO DE PRODUÇÃO do call
site (o cérebro do acionamento, o Atlas, o destilador, o lapidador, o juiz do
playbook, o extrator, a marca, o garimpo, as sugestões, o conselho, o juiz de
eval, o faturamento) com a FÁBRICA real, o Model Router real e o callback de
custo real. Dublês SÓ na borda:
  · o BANCO das rotas (`model_policy.leitor_do_banco` → o snapshot, copiado);
  · o BANCO do ledger (`get_supabase_client` → um gravador de `insert`);
  · a REDE do provedor (`_agenerate` dos clientes governados → devolve uma
    resposta pronta e GUARDA o payload que teria saído: modelo, sampling).

O que se prova (gates da F3b):
  · dispatch ×2 pela rota `dispatch` — env `DISPATCH_LLM_*` ignorado; trocar a
    rota troca o modelo sem deploy;
  · Atlas GRAVA no ledger (company_id nulo, não "atlas") e o preço vem do catálogo;
  · destilador grava como `plataforma` com o papel no `details`;
  · conselho PULA membro que o catálogo não governa (nunca o mini);
  · juiz de eval chama a fábrica com a assinatura certa; erro = NÃO AVALIADO;
  · faturamento sem preço inventado.

Rodar (de backend/):  .venv/Scripts/python -m pytest -q tests/test_spec116_f3b_plataforma.py
"""
from __future__ import annotations

import asyncio
import copy
import json
import os
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from langchain_core.messages import AIMessage  # noqa: E402
from langchain_core.outputs import ChatGeneration, ChatResult  # noqa: E402

import app.core.database as _db  # noqa: E402
import app.services.usage_service as _uso  # noqa: E402
from app.factories import llm_factory as LF  # noqa: E402
from app.factories import model_policy as MP  # noqa: E402

SNAP = json.loads(MP.SNAPSHOT_PATH.read_text(encoding="utf-8"))

#: 🔴 (24/09/2026 — conclusão da Onda A) PRODUÇÃO só aceita APPROVED. Estes testes
#: provam a MECÂNICA de trocar a rota (provedor, adaptador, temperatura, ledger)
#: usando modelos LEGADOS como dublês de "outro modelo" — no dublê eles são
#: promovidos a APPROVED. A regra de lifecycle (e o mínimo de esforço) é provada
#: em `test_nenhum_modelo_fora_do_catalogo.py` (§9.3: a lição migra, não morre).
MODELOS_LEGADOS_DUBLES = ("claude-sonnet-5", "claude-opus-5", "claude-haiku-4-5",
                          "claude-haiku-4-5-20251001", "gpt-4o", "gpt-4o-mini",
                          "gpt-4o-mini-2024-07-18", "whisper-1")


def _legados_como_dubles(cat):
    for m in MODELOS_LEGADOS_DUBLES:
        if m in cat:
            cat[m]["lifecycle"] = "APPROVED"
    return cat

EMPRESA_A = "11111111-1111-4111-8111-111111111111"
EMPRESA_B = "22222222-2222-4222-8222-222222222222"


# ---------------------------------------------------------------------------
# Bordas
# ---------------------------------------------------------------------------
class _Consulta:
    def __init__(self, banco, nome):
        self.banco, self.nome = banco, nome
        self._ler = False

    def select(self, *a, **k):
        if self.nome == "llm_pricing":
            raise ConnectionError("banco de preço fora (o UsageService cai no snapshot)")
        self._ler = True
        return self

    def insert(self, linha):
        self.banco.inseridos.append((self.nome, linha))
        return self

    def upsert(self, linha, *a, **k):
        return self.insert(linha)

    def __getattr__(self, _nome):
        return lambda *a, **k: self

    def execute(self):
        if self._ler:
            return type("R", (), {"data": list(self.banco.dados.get(self.nome, []))})()
        return type("R", (), {"data": [{"ok": 1}]})()


class BancoDoLedger:
    """`get_supabase_client()` dublado: guarda cada insert por tabela; `dados`
    responde os SELECTs (o de `llm_pricing` falha → snapshot)."""

    def __init__(self):
        self.inseridos = []
        self.dados = {}
        self.client = self

    def table(self, nome):
        return _Consulta(self, nome)

    def linhas(self, tabela="token_usage_logs"):
        return [l for (t, l) in self.inseridos if t == tabela]


class Provedor:
    """A rede do provedor, dublada NO ÚLTIMO PASSO: o payload é o que sairia."""

    def __init__(self):
        self.payloads = []
        self.resposta = "{}"
        self.falhar = None

    async def _agenerate(self, llm, messages, stop=None, run_manager=None, **kw):
        payload = llm._get_request_payload(messages, stop=stop, **kw)
        self.payloads.append(payload)
        if self.falhar:
            raise self.falhar
        msg = AIMessage(content=self.resposta,
                        response_metadata={"model_name": payload.get("model")},
                        usage_metadata={"input_tokens": 1000, "output_tokens": 100,
                                        "total_tokens": 1100})
        return ChatResult(generations=[ChatGeneration(message=msg)])

    @property
    def modelos(self):
        return [p.get("model") for p in self.payloads]


@pytest.fixture
def borda(monkeypatch):
    cat = _legados_como_dubles(copy.deepcopy(SNAP["catalogo"]))
    pap = copy.deepcopy(SNAP["papeis"])
    monkeypatch.setattr(MP, "leitor_do_banco", lambda: (cat, pap))
    MP.limpar_cache()

    banco = BancoDoLedger()
    monkeypatch.setattr(_db, "get_supabase_client", lambda: banco)
    monkeypatch.setattr(_uso, "get_supabase_client", lambda: banco)
    monkeypatch.setattr(_uso, "_usage_service", None)
    monkeypatch.setattr(_uso, "_pricing_cache", {})
    monkeypatch.setattr(_uso, "_cache_loaded_at", 0)

    prov = Provedor()

    async def _agen(self, messages, stop=None, run_manager=None, **kw):
        return await prov._agenerate(self, messages, stop=stop, run_manager=run_manager, **kw)

    for cls in (LF.ChatAnthropicGovernado, LF.ChatOpenAIGovernado):
        monkeypatch.setattr(cls, "_agenerate", _agen)
        monkeypatch.setattr(cls, "_should_stream", lambda self, *a, **k: False)

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-teste-falsa")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-teste-falsa")
    yield type("Borda", (), {"cat": cat, "pap": pap, "banco": banco, "prov": prov})
    MP.limpar_cache()


def _rodar(coro):
    return asyncio.run(coro)


def _ultima_linha(borda):
    linhas = borda.banco.linhas()
    assert linhas, "NENHUMA linha no ledger — a chamada ficou invisível"
    return linhas[-1]


# ---------------------------------------------------------------------------
# DISPATCH ×2 — a rota `dispatch`, env ignorado
# ---------------------------------------------------------------------------
def test_dispatch_do_sentinela_pede_o_papel_e_ignora_o_env(borda, monkeypatch):
    from app.tasks import dispatch_watchdog as W

    monkeypatch.setenv("DISPATCH_LLM_PROVIDER", "openai")
    monkeypatch.setenv("DISPATCH_LLM_MODEL", "gpt-4o")   # o env de antes: tem de ser IGNORADO
    borda.prov.resposta = "2"
    sessao = {"playbook_ref": "", "company_id": EMPRESA_A, "slots": {}, "history": []}
    r = _rodar(W._adaptive_reply(EMPRESA_A, sessao, "Digite 1 para guincho, 2 para chaveiro"))
    assert r == "2"
    assert borda.prov.modelos == [borda.pap["dispatch"]["modelo_primario"]] == ["claude-opus-5-5"]
    assert "temperature" not in borda.prov.payloads[0], "Claude 5 recusa sampling (400)"
    linha = _ultima_linha(borda)
    assert linha["details"]["papel"] == "dispatch" and linha["company_id"] == EMPRESA_A

    # trocar a ROTA (banco) troca o modelo — sem deploy, sem env
    borda.pap["dispatch"]["modelo_primario"] = "claude-sonnet-5"
    MP.limpar_cache()
    _rodar(W._adaptive_reply(EMPRESA_A, sessao, "Digite 1 para guincho"))
    assert borda.prov.modelos[-1] == "claude-sonnet-5"


def test_dispatch_do_cerebro_antes_do_segurado_pede_o_papel(borda, monkeypatch):
    from app.services import dispatch_router as R

    monkeypatch.setenv("CEREBRO_ANTES_DO_SEGURADO", "1")
    monkeypatch.setenv("DISPATCH_LLM_MODEL", "gpt-4o")

    async def _fontes(company_id, session):
        return [("ficha", "ponto de referencia: em frente a padaria azul")]

    monkeypatch.setattr(R, "fontes_do_que_ja_existe", _fontes)
    borda.prov.resposta = "em frente a padaria azul"
    valor, origem = _rodar(R.o_cerebro_ja_sabe(EMPRESA_B, {"company_id": EMPRESA_B}, slot="ponto",
                                               rotulo="ponto de referencia", tela="Informe o ponto"))
    assert (valor, origem) == ("em frente a padaria azul", "ficha")
    assert borda.prov.modelos == ["claude-opus-5-5"]  # a rota `dispatch` (24/09/2026)
    linha = _ultima_linha(borda)
    assert linha["details"]["papel"] == "dispatch" and linha["company_id"] == EMPRESA_B


def test_dispatch_sem_rota_nao_cai_em_modelo_nenhum(borda):
    from app.tasks import dispatch_watchdog as W

    del borda.pap["dispatch"]
    MP.limpar_cache()
    r = _rodar(W._adaptive_reply(EMPRESA_A, {"playbook_ref": ""}, "tela"))
    assert r is None and borda.prov.payloads == [], "sem rota = sem chamada (nunca gpt-4o)"


# ---------------------------------------------------------------------------
# ATLAS — grava no ledger; preço do catálogo
# ---------------------------------------------------------------------------
def _mapa_com_uma_ambiguidade():
    return {"nodes": {"a": {"kind": "menu", "text": "O que precisa? 1 Guincho 2 Chaveiro",
                            "options": [{"label": "Guincho"}, {"label": "Chaveiro"}]},
                      "b": {"kind": "informativo", "text": "Enviaremos o chaveiro."}},
            "edges": {"a|→": {"src": "a", "label": "→", "to": "b", "inferred": True}}}


def test_atlas_grava_no_ledger_como_plataforma(borda, monkeypatch):
    from app.services.atlas import atlas_parser as A

    monkeypatch.setenv("ATLAS_PARSER_ENABLED", "1")
    monkeypatch.setenv("ATLAS_PARSER_MODEL", "gpt-5.1")   # env de antes: IGNORADO
    borda.prov.resposta = json.dumps({"answers": ["Chaveiro"]})
    mapa = _mapa_com_uma_ambiguidade()
    import app.services.atlas.weaver as WV
    monkeypatch.setattr(WV, "compute_coverage", lambda m: None)
    n = _rodar(A.resolve_typed_choices(mapa, "seguradora-x"))
    assert n == 1 and "a|Chaveiro" in mapa["edges"]
    assert borda.prov.modelos == [borda.pap["atlas_parser"]["modelo_primario"]]
    linha = _ultima_linha(borda)
    # 🔴 o defeito: company_id="atlas" numa coluna uuid → o insert falhava calado
    assert "company_id" not in linha, linha.get("company_id")
    assert linha["service_type"] == "plataforma"
    assert linha["details"]["papel"] == "atlas_parser"
    assert linha["total_cost_usd"] > 0, "preço do catálogo, não zero"


def test_atlas_estimativa_usa_o_preco_do_catalogo(borda):
    from app.services.atlas import atlas_parser as A

    est = A.estimate_cost(nodes=30, ambiguous_edges=12)
    assert est["model"] == borda.pap["atlas_parser"]["modelo_primario"]
    svc = _uso.get_usage_service()
    esperado = svc.calculate_cost(est["model"], est["input_tokens"], est["output_tokens"])
    assert est["usd_per_insurer"] == round(esperado, 4) and esperado > 0
    # modelo sem preço no catálogo → 0 + sinal, nunca um preço inventado
    borda.pap["atlas_parser"]["modelo_primario"] = "claude-opus-5-5"
    MP.limpar_cache()
    _uso._pricing_cache = {k: v for k, v in _uso._precos_do_snapshot().items() if k != "claude-opus-5-5"}
    _uso._cache_loaded_at = 10 ** 12
    est = A.estimate_cost(nodes=30, ambiguous_edges=12)
    assert est.get("preco_desconhecido") is True and est["usd_per_insurer"] == 0.0


# ---------------------------------------------------------------------------
# DESTILADOR / LAPIDADOR / JUIZ DO PLAYBOOK / EXTRATOR — plataforma + papel
# ---------------------------------------------------------------------------
def test_destilador_grava_no_ledger_como_plataforma_com_o_papel(borda):
    from app.services import attendance_distiller as D

    borda.prov.resposta = '{"ok": 1}'
    assert _rodar(D._call_llm("sys", "user", strong=True)) == '{"ok": 1}'
    forte = _ultima_linha(borda)
    assert forte["service_type"] == "plataforma" and "company_id" not in forte
    assert forte["details"]["papel"] == "distiller_forte"
    assert forte["model_name"] == borda.pap["distiller_forte"]["modelo_primario"]

    _rodar(D._call_llm("sys", "user", company_id=EMPRESA_A))
    padrao = _ultima_linha(borda)
    assert padrao["details"]["papel"] == "distiller" and padrao["company_id"] == EMPRESA_A
    assert padrao["service_type"] == "plataforma"
    assert padrao["model_name"] == borda.pap["distiller"]["modelo_primario"]
    assert D._provider_model(True)[1] == borda.pap["distiller_forte"]["modelo_primario"]


def test_lapidador_e_juiz_do_playbook_pedem_o_proprio_papel(borda, monkeypatch):
    from app.services import attendance_distiller as D
    from app.services import playbook_gate as G

    # papéis distintos: trocar o do destilador NÃO troca o do juiz
    borda.pap["juiz_playbook"]["modelo_primario"] = "claude-sonnet-5"
    borda.pap["distiller_forte"]["modelo_primario"] = "claude-opus-5"
    MP.limpar_cache()
    borda.prov.resposta = json.dumps({"nota_candidato": 90, "veredito": "aprovar"})
    v = _rodar(G._judge({"ficha_coleta": []}, None, []))
    assert v["veredito"] == "aprovar"
    linha = _ultima_linha(borda)
    assert (linha["details"]["papel"], linha["model_name"]) == ("juiz_playbook", "claude-sonnet-5")

    _rodar(D._call_llm("sys", "user", papel="prompt_optimizer"))
    assert _ultima_linha(borda)["details"]["papel"] == "prompt_optimizer"


def test_extrator_de_planos_pede_o_papel(borda, monkeypatch):
    from app.services.knowledge import assistance_plans_extractor as X

    monkeypatch.setenv("EXTRATOR_PLANOS_MODEL", "gpt-4o-mini")   # IGNORADO
    llm = X.montar_modelo()
    assert llm is not None and llm.model == borda.pap["extrator_planos"]["modelo_primario"]
    assert llm.callbacks[0].details["papel"] == "extrator_planos"
    assert llm.callbacks[0].service_type == "plataforma" and llm.callbacks[0].company_id is None


def test_marca_pede_o_papel(borda, monkeypatch):
    from app.services.brand import capture as C

    monkeypatch.setenv("BRAND_CAPTURE_MODEL", "gpt-4o")   # IGNORADO
    llm = C.BrandCaptureService._llm_de_marca(object.__new__(C.BrandCaptureService), EMPRESA_A)
    assert llm.model == borda.pap["brand_capture"]["modelo_primario"]
    assert llm.callbacks[0].details["papel"] == "brand_capture"
    assert llm.callbacks[0].service_type == C.SERVICE_TYPE_MARCA
    assert llm.callbacks[0].company_id == EMPRESA_A


def test_garimpo_desligado_nao_chama_e_ligado_chama_pela_rota(borda, monkeypatch):
    from app.services import broker_insights as BI

    monkeypatch.delenv("GARIMPO_LLM", raising=False)
    assert _rodar(BI._llm_refine_company(EMPRESA_A, ["c1"])) == 0
    assert borda.prov.payloads == [], "desligado = zero chamada (o interruptor continua)"

    monkeypatch.setenv("GARIMPO_LLM", "1")
    monkeypatch.setenv("GARIMPO_LLM_MODEL", "gpt-4o-mini")   # IGNORADO
    borda.banco.dados["messages"] = [
        {"role": "user", "content": "queria cotar seguro de vida para meus clientes"},
        {"role": "user", "content": "o portal da seguradora caiu de novo hoje cedo"}]
    borda.prov.resposta = json.dumps({"insights": [
        {"kind": "desejo", "summary": "quer cotar vida", "quote": "cotar seguro de vida"}]})
    assert _rodar(BI._llm_refine_company(EMPRESA_A, ["c1"])) == 1
    assert borda.prov.modelos == [borda.pap["garimpo"]["modelo_primario"]]
    assert _ultima_linha(borda)["details"]["papel"] == "garimpo"


def test_sugestoes_ligadas_chamam_pela_rota(borda, monkeypatch):
    from app.services import proactive_suggestions as PS

    monkeypatch.delenv("SUGESTOES_LLM", raising=False)
    assert _rodar(PS._llm_message(EMPRESA_A, {"system": "s", "user": "u"})) is None
    assert borda.prov.payloads == [], "desligado = zero chamada (o interruptor continua)"

    monkeypatch.setenv("SUGESTOES_LLM", "1")
    monkeypatch.setenv("SUGESTOES_LLM_MODEL", "gpt-4o")   # IGNORADO
    borda.prov.resposta = "Sugestão da semana"
    assert _rodar(PS._llm_message(EMPRESA_A, {"system": "s", "user": "u"})) == "Sugestão da semana"
    assert borda.prov.modelos == [borda.pap["sugestoes"]["modelo_primario"]]
    linha = _ultima_linha(borda)
    assert linha["details"]["papel"] == "sugestoes" and linha["company_id"] == EMPRESA_A


# ---------------------------------------------------------------------------
# CONSELHO — membro não governado é PULADO; nunca o mini
# ---------------------------------------------------------------------------
def test_conselho_pula_membro_que_o_catalogo_nao_governa(borda, monkeypatch):
    from app.services import agent_council as CO

    monkeypatch.setenv("COUNCIL_ENABLED", "1")
    monkeypatch.setenv("COUNCIL_MEMBERS",
                       "openai:gpt-5.5,anthropic:claude-opus-5,moonshot:kimi-k3,"
                       "xai:grok-4.5,anthropic:claude-3-5-sonnet-20241022,openai:gpt-4o")
    borda.prov.resposta = "VEREDITO: aprovar"

    async def _sem_redis():
        raise ConnectionError("sem redis no teste")

    import app.core.redis as RD
    monkeypatch.setattr(RD, "get_async_redis_client", _sem_redis)
    r = _rodar(CO.convene_council("Ativar playbook?", "ctx"))
    por = {o["member"]: o for o in r["opinions"]}
    assert por["anthropic:claude-opus-5"]["ok"] and por["openai:gpt-4o"]["ok"]
    for pulado in ("openai:gpt-5.5", "moonshot:kimi-k3", "xai:grok-4.5",
                   "anthropic:claude-3-5-sonnet-20241022"):
        assert por[pulado]["ok"] is False and por[pulado]["skipped"] == "fora_do_catalogo_ou_proibido"
    # 🔴 ninguém virou o mini: só saíram os 2 membros governados + o líder da rota
    assert "gpt-4o-mini" not in borda.prov.modelos
    assert sorted(borda.prov.modelos) == sorted(["claude-opus-5", "gpt-4o",
                                                 borda.pap["conselho_lider"]["modelo_primario"]])
    papeis = [l["details"]["papel"] for l in borda.banco.linhas()]
    assert papeis.count("conselho_membro") == 2 and papeis.count("conselho_lider") == 1


def test_conselho_continua_desligado_por_padrao(borda, monkeypatch):
    from app.services import agent_council as CO

    monkeypatch.delenv("COUNCIL_ENABLED", raising=False)
    assert _rodar(CO.convene_council("x", "y"))["enabled"] is False
    assert borda.prov.payloads == []


# ---------------------------------------------------------------------------
# JUIZ DE EVAL — a fábrica com a assinatura certa; erro = NÃO AVALIADO
# ---------------------------------------------------------------------------
def test_juiz_de_eval_chama_a_fabrica_e_julga(borda):
    from app.services.evals import juiz_llm as J

    borda.prov.resposta = json.dumps({"vereditos": [
        {"rubrica": "responde_a_pergunta", "passou": True, "confianca": 0.9, "motivo": "ok"}]})
    v = _rodar(J.julgar_com_llm({"p": "qual a franquia?"}, "R$ 1.000",
                                rubricas=["responde_a_pergunta"]))
    assert v[0]["resultado"] == "PASS" and v[0]["passou"] is True and v[0]["avaliado"] is True
    assert borda.prov.modelos == [borda.pap["juiz_eval"]["modelo_primario"]]
    assert _ultima_linha(borda)["details"]["papel"] == "juiz_eval"


def test_juiz_de_eval_que_falha_diz_nao_avaliado(borda):
    from app.services.evals import juiz_llm as J

    borda.prov.falhar = RuntimeError("provedor fora")
    v = _rodar(J.julgar_com_llm({"p": "x"}, "y", rubricas=["sem_invencao"]))
    assert v[0]["resultado"] == J.NAO_AVALIADO
    assert v[0]["passou"] is None and v[0]["nota"] is None, "nem aprovado nem reprovado"
    assert v[0]["precisa_revisao_humana"] is True
    # sem rota → indisponível, sem chamada
    borda.prov.payloads.clear()
    del borda.pap["juiz_eval"]
    MP.limpar_cache()
    v = _rodar(J.julgar_com_llm({"p": "x"}, "y", rubricas=["sem_invencao"]))
    assert v[0]["resultado"] == J.NAO_AVALIADO and borda.prov.payloads == []


# ---------------------------------------------------------------------------
# FATURAMENTO — preço do catálogo, nunca inventado
# ---------------------------------------------------------------------------
class _SupabaseDoFaturamento:
    def __init__(self, precos):
        self.precos = precos
        self.atualizados = []

    def table(self, nome):
        sb = self

        class _Q:
            def __init__(self):
                self.filtros = {}

            def select(self, *a, **k):
                return self

            def eq(self, col, val):
                self.filtros[col] = val
                return self

            def limit(self, *a):
                return self

            def single(self):
                raise AssertionError("`.single()` levanta em 0 linhas — era por onde o default entrava")

            def execute(self):
                if nome == "llm_pricing":
                    linha = sb.precos.get(self.filtros.get("model_name"))
                    return type("R", (), {"data": [linha] if linha else []})()
                return type("R", (), {"data": []})()

        return _Q()


def test_faturamento_nao_inventa_preco():
    from app.workers import billing_tasks as BT

    sb = _SupabaseDoFaturamento({"claude-opus-5": {
        "model_name": "claude-opus-5", "input_price_per_million": 5,
        "output_price_per_million": 25, "sell_multiplier": 2.68}})
    p = BT.get_pricing_for_model(sb, "claude-opus-5")
    assert p is not None and str(p["sell_multiplier"]) == "2.68"
    assert BT.get_pricing_for_model(sb, "claude-opus-5-20260101") is not None, "id datado"
    # 🔴 o defeito: modelo ausente virava 1,00/3,00 × 2,68 inventados
    assert BT.get_pricing_for_model(sb, "modelo-que-nao-existe") is None
