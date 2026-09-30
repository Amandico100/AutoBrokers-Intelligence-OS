# -*- coding: utf-8 -*-
"""SPEC-122 F0 — o GPT-6.1 Sol sucede o Sol 6 em TODA rota que usava Sol.

Ordem do Founder (30/09/2026): o GPT-6.1 Sol no lugar do Sol 6 onde usamos Sol,
se real, com id correto, preço equivalente e compatível. Regra do gerente: troca
de GERAÇÃO, não de esforço — cada papel mantém o esforço que tinha. Luna, Astra,
Opus 5.5 e Sonnet 5.5 não mudam; o dispatch continua Opus 5.5 primário e só a
RESERVA dele vira o 6.1. O Sol 6 fica DEPRECATED (a bancada ainda o mede).

🔴 CHAMA O MOTOR (CLAUDE.md §9.4): `model_policy.resolver` e `LLMFactory` reais →
`ChatOpenAIGovernado._get_request_payload` (o corpo que SAIRIA) → `CostCallbackHandler`
→ `UsageService.calculate_cost` real (preço do snapshot). Dublês SÓ na borda, os da
F3b (`test_spec116_f3b_plataforma.borda`): o banco das rotas (o snapshot versionado,
sem promover o Sol 6), o banco do ledger (guarda o INSERT) e a rede do provedor.

  (i)   cada papel que era Sol resolve para `gpt-6.1-sol` com o MESMO esforço de antes
        — e é esse o corpo que sai (model + reasoning.effort);
  (ii)  nenhum pedido ao 6.1 sai com effort `none` (a API dá 400, 📊 canário 30/09):
        o resolvedor recusa ANTES da rede. CONTROLE: o Sol 6 com `none` ainda passa
        pela validação dele (a porta é o catálogo, não o nome);
  (iii) a reserva do dispatch é o 6.1 em high, o primário continua Opus 5.5, e a falha
        transitória do Opus leva à reserva 6.1 com `reserva_usada=true` no ledger;
        as reservas Opus 5.5 dos papéis P0 ficam intactas;
  (iv)  o snapshot e a migration 20260930_01 (o texto que o Postgres aplicou) concordam;
  (v)   o cache do 6.1 custa 0,05 × entrada (US$ 0,10/MTok) no ledger — não 0,10 ×.

Rodar (de backend/):  .venv/Scripts/python -m pytest -q tests/test_o_sol_6_1_sucede_o_sol_6.py
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

import anthropic
import httpx
import pytest

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
TESTS = Path(__file__).resolve().parent
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

from langchain_core.messages import AIMessage, HumanMessage  # noqa: E402
from langchain_core.outputs import ChatGeneration, ChatResult  # noqa: E402

from app.factories import model_policy as MP  # noqa: E402
from app.factories.llm_factory import LLMFactory, invocar_com_reserva  # noqa: E402
from app.factories.model_policy import ModeloNaoResolvido  # noqa: E402
from test_spec116_f3b_plataforma import EMPRESA_A, borda  # noqa: E402,F401

NOVO = "gpt-6.1-sol"
VELHO = "gpt-6-sol"
OPUS = "claude-opus-5-5"
MIGRATION = BACKEND / "supabase" / "migrations" / "20260930_01_spec122_gpt_6_1_sol.sql"
SNAP = json.loads(MP.SNAPSHOT_PATH.read_text(encoding="utf-8"))

#: 📊 30/09/2026, SELECT em llm_papeis ANTES da migration (SET TRANSACTION READ ONLY):
#: papel → (esforço do primário Sol 6, reserva que o papel tinha).
ANTES_PRIMARIO = {
    "atendimento": ("high", OPUS),
    "chat_principal": ("medium", OPUS),
    "juiz_eval": ("medium", None),
    "portal_decisao": ("medium", OPUS),
    "subagente": ("medium", None),
    "visao": ("medium", None),
    "visao_documento": ("medium", None),
}
#: o dispatch: Opus 5.5 primário (esforço NULO), reserva Sol 6 em high.
ANTES_RESERVA = {"dispatch": (OPUS, "high")}
#: Os papéis que NASCERAM depois da 20260930_01 já no 6.1 (primário) — SPEC-123 F1a, 20260930_03.
NASCIDOS_NO_6_1 = {"destravador"}


def _req():
    return httpx.Request("POST", "https://api.invalid/v1")


def _invocar(papel):
    llm = LLMFactory.create_llm({}, {}, company_id=EMPRESA_A, papel=papel)
    return asyncio.run(llm.ainvoke([HumanMessage(content="oi")]))


# ---------------------------------------------------------------------------
# (i) cada papel que era Sol → 6.1, o MESMO esforço, e é isso que sai
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("papel", sorted(ANTES_PRIMARIO))
def test_papel_que_era_sol_resolve_para_o_6_1_com_o_mesmo_esforco(borda, papel):
    esforco, reserva = ANTES_PRIMARIO[papel]
    r = MP.resolver(papel)
    assert (r.provider, r.model, r.effort, r.lifecycle) == ("openai", NOVO, esforco, "APPROVED"), r
    assert (r.reserva.model if r.reserva else None) == reserva, f"{papel}: a reserva não muda"
    _invocar(papel)
    corpo = borda.prov.payloads[-1]
    assert corpo["model"] == NOVO
    assert corpo.get("reasoning") == {"effort": esforco}, corpo.get("reasoning")
    assert not {"temperature", "top_p"} & set(corpo), "sampling_ok=false no 6.1"


def test_nenhuma_rota_de_producao_usa_mais_o_sol_6(borda):
    usando = {p: r for p, r in borda.pap.items() if VELHO in (r.get("modelo_primario"),
                                                             r.get("modelo_reserva"))}
    assert usando == {}, usando
    sol = sorted(p for p, r in borda.pap.items() if r.get("modelo_primario") == NOVO)
    # §9.3 — SPEC-123 F1a (migration 20260930_03): o papel `destravador` NASCEU depois, já no 6.1.
    #    A lição fica: os 7 que ERAM Sol 6 são 6.1, e nenhum outro papel antigo virou 6.1 por engano.
    assert sorted(set(sol) - NASCIDOS_NO_6_1) == sorted(ANTES_PRIMARIO), "exatamente os 7 papéis que eram Sol 6"


def test_controle_luna_e_opus_nao_mudaram(borda):
    """LINHA DE CONTROLE: o que não era Sol continua onde estava (troca de GERAÇÃO)."""
    assert MP.resolver("memoria").model == "gpt-6-luna"
    assert MP.resolver("auxiliar").model == "gpt-6-luna"
    assert MP.resolver("juiz_playbook").model == OPUS
    assert MP.resolver("dispatch").model == OPUS


# ---------------------------------------------------------------------------
# (ii) effort `none` no 6.1 é recusado ANTES da rede
# ---------------------------------------------------------------------------
def test_o_6_1_com_effort_none_e_recusado_antes_da_rede_pela_rota(borda):
    borda.pap["juiz_eval"].update(esforco="none")
    MP.limpar_cache()
    with pytest.raises(ModeloNaoResolvido, match=r"gpt-6\.1-sol'.*esforço 'none'"):
        _invocar("juiz_eval")
    assert borda.prov.payloads == [], "nada pode ter saído"


def test_o_6_1_com_effort_none_e_recusado_ate_na_bancada(borda):
    with pytest.raises(ModeloNaoResolvido, match="esforço 'none'"):
        MP.resolver("juiz_eval", override={"provider": "openai", "model": NOVO, "effort": "none"})
    assert "none" not in borda.cat[NOVO]["capacidades"]["niveis_de_esforco"]


def test_controle_o_sol_6_com_none_ainda_passa_pela_validacao_dele(borda):
    """LINHA DE CONTROLE: o Sol 6 declara `none` no catálogo → a MESMA porta o deixa
    passar (bancada: DEPRECATED ainda é medível) e o corpo leva `none`. A recusa do
    6.1 vem do CATÁLOGO dele, não de um nome no código."""
    r = MP.resolver("juiz_eval", override={"provider": "openai", "model": VELHO, "effort": "none"})
    assert (r.model, r.effort, r.lifecycle, r.origem) == (VELHO, "none", "DEPRECATED", "bancada")
    llm = LLMFactory.create_llm({}, {}, company_id=EMPRESA_A, modelo_resolvido=r)
    asyncio.run(llm.ainvoke([HumanMessage(content="oi")]))
    assert borda.prov.payloads[-1].get("reasoning") == {"effort": "none"}


def test_o_sol_6_nao_roda_mais_em_producao(borda):
    borda.pap["juiz_eval"].update(modelo_primario=VELHO)
    MP.limpar_cache()
    with pytest.raises(ModeloNaoResolvido, match="DEPRECATED"):
        MP.resolver("juiz_eval")


# ---------------------------------------------------------------------------
# (iii) o dispatch: Opus 5.5 primário, 6.1 high de reserva — e o failover
# ---------------------------------------------------------------------------
def test_a_reserva_do_dispatch_e_o_6_1_high_e_as_reservas_opus_ficam(borda):
    r = MP.resolver("dispatch")
    assert (r.provider, r.model) == ("anthropic", ANTES_RESERVA["dispatch"][0])
    assert (r.reserva.provider, r.reserva.model, r.reserva.effort) == (
        "openai", NOVO, ANTES_RESERVA["dispatch"][1])
    for papel in ("atendimento", "chat_principal", "portal_decisao"):
        rr = MP.resolver(papel).reserva
        assert (rr.provider, rr.model, rr.effort) == ("anthropic", OPUS, None), papel


def test_dispatch_opus_inalcancavel_a_reserva_6_1_responde_e_o_ledger_marca(borda):
    original = borda.prov._agenerate

    async def _agen(llm, messages, stop=None, run_manager=None, **kw):
        payload = llm._get_request_payload(messages, stop=stop, **kw)
        if payload.get("model") == OPUS:
            borda.prov.payloads.append(payload)
            raise anthropic.APIConnectionError(request=_req())
        return await original(llm, messages, stop=stop, run_manager=run_manager, **kw)

    borda.prov._agenerate = _agen
    borda.prov.resposta = "2"
    resp = asyncio.run(invocar_com_reserva("dispatch", [HumanMessage(content="Digite 1 ou 2")],
                                           company_id=EMPRESA_A))
    assert resp.content == "2"
    assert borda.prov.modelos == [OPUS, NOVO], "UMA reserva, sem repetir"
    assert borda.prov.payloads[1].get("reasoning") == {"effort": "high"}
    linhas = borda.banco.linhas()
    assert len(linhas) == 1, "só quem respondeu grava tokens"
    d = linhas[0]["details"]
    assert (d["papel"], d["modelo_resolvido"], d["reserva_usada"], d["motivo_reserva"]) == (
        "dispatch", NOVO, True, "conexao"), d


# ---------------------------------------------------------------------------
# (iv) snapshot × migration
# ---------------------------------------------------------------------------
def _capacidades_da_migration() -> dict:
    sql = MIGRATION.read_text(encoding="utf-8")
    bloco = sql.split("insert into public.llm_pricing", 1)[1]
    return json.loads(re.search(r"'(\{.*?\})'::jsonb", bloco, re.S).group(1))


def test_o_snapshot_e_a_migration_concordam():
    cat = SNAP["catalogo"]
    novo, velho = cat[NOVO], cat[VELHO]
    assert (velho["lifecycle"], velho["substituido_por"]) == ("DEPRECATED", NOVO), velho
    assert (novo["lifecycle"], novo["provider"], novo["api_surface"], novo["tipo"]) == (
        "APPROVED", "openai", "responses", "chat")
    assert (novo["input_price_per_million"], novo["output_price_per_million"],
            novo["cached_input_multiplier"], novo["cache_write_multiplier"],
            novo["input_price_long"], novo["output_price_long"], novo["limiar_contexto_longo"]) == (
        2, 10, 0.05, 1.25, 4, 15, 272000)
    assert novo["preco_verificado_em"] == "2026-09-30"
    assert novo["capacidades"] == _capacidades_da_migration(), "snapshot ≠ migration"
    caps = novo["capacidades"]
    assert caps["niveis_de_esforco"] == ["low", "medium", "high", "xhigh", "max"]
    assert (caps["tool_choice_forcado_ok"], caps["sampling_ok"],
            caps["responses_obrigatoria_com_tools"], caps["vision"], caps["pdf"]) == (
        True, False, True, True, False)
    assert sorted(novo["classes_de_dado"]) == ["interno", "pii", "publico"]


def test_a_migration_nao_mexe_em_esforco():
    """FORMA da declaração (§9.4 exceção): os UPDATEs de rota trocam o MODELO e só."""
    sql = MIGRATION.read_text(encoding="utf-8")
    corpo = sql.split("-- B. toda rota", 1)[1].split("-- C.", 1)[0]
    assert "modelo_primario = 'gpt-6.1-sol'" in corpo and "modelo_reserva = 'gpt-6.1-sol'" in corpo
    assert "esforco" not in corpo, "troca de GERAÇÃO, não de esforço"


# ---------------------------------------------------------------------------
# (v) o cache do 6.1 custa 0,05 × entrada no ledger
# ---------------------------------------------------------------------------
def _custo_no_ledger(borda, resolvido, *, entrada=1000, cache=800, saida=100):
    async def _agen(llm, messages, stop=None, run_manager=None, **kw):
        payload = llm._get_request_payload(messages, stop=stop, **kw)
        borda.prov.payloads.append(payload)
        msg = AIMessage(content="ok", response_metadata={"model_name": payload["model"]},
                        usage_metadata={"input_tokens": entrada, "output_tokens": saida,
                                        "total_tokens": entrada + saida,
                                        "input_token_details": {"cache_read": cache}})
        return ChatResult(generations=[ChatGeneration(message=msg)])

    borda.prov._agenerate = _agen
    llm = LLMFactory.create_llm({}, {}, company_id=EMPRESA_A, modelo_resolvido=resolvido)
    asyncio.run(llm.ainvoke([HumanMessage(content="oi")]))
    linha = borda.banco.linhas()[-1]
    assert (linha["model_name"], linha["cached_tokens"], linha["cache_read_tokens"]) == (
        resolvido.model, cache, 0), "OpenAI: o cache vai para o balde da OpenAI"
    return linha["total_cost_usd"]


def test_o_cache_do_6_1_custa_0_05_da_entrada(borda):
    custo = _custo_no_ledger(borda, MP.resolver("atendimento"))
    # 200 × 2 + 800 × 2 × 0,05 + 100 × 10  (por MTok)
    assert custo == pytest.approx((200 * 2 + 800 * 0.10 + 100 * 10) / 1e6), custo


def test_controle_o_cache_do_sol_6_custa_0_10_da_entrada(borda):
    """LINHA DE CONTROLE: o MESMO uso no Sol 6 custa mais — as duas linhas do catálogo
    CONSEGUEM divergir (§9.3), e é o multiplicador que decide."""
    r6 = MP.resolver("juiz_eval", override={"provider": "openai", "model": VELHO, "effort": "medium"})
    custo6 = _custo_no_ledger(borda, r6)
    assert custo6 == pytest.approx((200 * 2 + 800 * 0.20 + 100 * 10) / 1e6), custo6
    custo61 = _custo_no_ledger(borda, MP.resolver("atendimento"))
    assert custo6 - custo61 == pytest.approx(800 * 0.10 / 1e6)
