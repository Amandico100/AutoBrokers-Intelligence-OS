# -*- coding: utf-8 -*-
r"""SPEC-126 · U2-C — a bancada de CONVERSA mede o classificador DENTRO do teto.

```
rodada de conversa → grafo REAL → tool_node REAL → `_DubleDoAcionamento`
  → `prova_da_confirmacao(llm=<o classificador DA RODADA>)` → `portao_da_confirmacao` (regex E classificador)
  → decisão gravada no turno (`portao`) → régua `acionou_sem_confirmar` lê ESSA decisão
```

📊 O defeito (U2-B): o dublê chamava o portão SEM `llm=` → o classificador ia ao papel de PRODUÇÃO
(`invocar_com_reserva("confirmacao")`): pago, com `company_id` fictício, fora do ledger e do teto.

O que se afirma, pelo MOTOR (CLAUDE.md §9.4):
· a rodada (modelo-dublê, sem custo) em que o segurado diz "pode mandar" usa o classificador DA BANCADA:
  ZERO chamadas ao `invocar_com_reserva` de produção, UMA chamada medida no classificador, e o custo dele
  entra no custo do caso E no orçamento da rodada;
· a rodada REAL monta o classificador por `bancada_confirmacao.construir_braco` (o mesmo jeito da
  bancada do "ok"), no orçamento do provedor dele; rodada de dublê nunca recebe classificador pago;
· o parente (`de_outra_pessoa`) recebe a linha sem a placa — pela leitura da PRÓPRIA ferramenta;
· a régua julga pela decisão GRAVADA do portão (com controle: a regra antiga, só regex, julga diferente);
· o teto relido do ledger soma o papel `confirmacao`.

⛔ Sem rede, sem LLM, sem banco real. Dados sintéticos (`D.materializar`); nenhum nome de corretora (§13.9).
"""
from __future__ import annotations

import asyncio
import os
import re
import sys

import pytest

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
for _c in (RAIZ, AQUI):
    if _c not in sys.path:
        sys.path.insert(0, _c)

from app.agents.tools import insurer_dispatch_tool as IT  # noqa: E402
from app.services.evals import bancada as B  # noqa: E402
from app.services.evals import bancada_confirmacao as BC  # noqa: E402
from app.services.evals import dubles as D  # noqa: E402
from test_spec125_endurecimento import _Modelo, _caso  # noqa: E402
from test_spec126_u1_fio import ARGS, CEN_FIO, roteiro_do_c13  # noqa: E402

PRECO = {"entrada": 1.0, "saida": 4.0}


def _rodar_com_relatorio(caso, roteiro, **kw):
    """O `_rodar` do endurecimento, devolvendo também o RELATÓRIO (o orçamento da rodada)."""
    vistos: dict = {}

    def construir(resolvido, _cb):
        return _Modelo(B._campo(resolvido, "model"), vistos, roteiro)

    def resolver(papel, *, override, **_k):
        return {"papel": papel, "provider": override["provider"], "model": override["model"],
                "effort": None, "api_surface": "teste", "capacidades": {"tools": True, "max_output": 512}}

    rel = B.rodar_bancada("conversa", ["fake:agente"], casos=[caso], k=1, nivel="N3",
                          construir_llm=construir, resolver=resolver, precos=lambda b: dict(PRECO),
                          teto_usd=50.0, segunda="fake:segurado", **kw)
    assert not rel.parada, rel.parada
    r = rel.resultados[0]
    assert r.erro is None, r.erro
    return rel, r


@pytest.fixture
def producao(monkeypatch):
    """Conta TODA chamada ao `invocar_com_reserva` de PRODUÇÃO (e deixa a trava do conftest por baixo)."""
    from app.factories import llm_factory as LF

    chamadas: list = []
    atual = LF.invocar_com_reserva

    async def contando(papel, mensagens, **kw):
        chamadas.append(papel)
        return await atual(papel, mensagens, **kw)

    monkeypatch.setattr(LF, "invocar_com_reserva", contando)
    return chamadas


# ===========================================================================
# 4 · O FIO: "pode mandar" → o classificador DA BANCADA, medido, dentro do orçamento
# ===========================================================================
def test_pode_mandar_usa_o_classificador_da_bancada_e_nada_vai_a_producao(producao):
    rel, r = _rodar_com_relatorio(_caso(CEN_FIO), roteiro_do_c13())
    trans = r.rastro["estado"]["transcricao"]
    # ⛔ nada ao papel de produção
    assert producao == [], f"a rodada chamou o invocar_com_reserva de produção: {producao}"
    # ✅ o classificador DA RODADA: o dublê padrão, UMA chamada (só quando a regex já disse sim), medida
    conf = r.rastro["confirmacao"]
    assert conf["braco"] == B.CLASSIFICADOR_DUBLE_PADRAO == "duble:sempre_ok", conf
    assert (conf["chamadas"], conf["chamadas_tentadas"]) == (1, 1), conf
    assert conf["custo_usd"] > 0 and conf["tokens"]["in"] > 0, conf
    # o portão decidiu no turno 3 com as DUAS camadas — e acionou; no turno 2 a regex recusou (sem pergunta)
    assert [d["camada"] for d in trans[1]["portao"]] == ["regex"], trans[1]["portao"]
    assert trans[1]["portao"][0]["acionou"] == 0 and trans[1]["portao"][0]["comprovada"] is False
    assert trans[2]["portao"] == [{"dados_confirmados": True, "consultado": True, "comprovada": True,
                                   "camada": "regex+classificador", "leitura": "ok",
                                   "motivo": trans[2]["portao"][0]["motivo"], "acionou": 1}], trans[2]["portao"]
    assert r.resultado == "PASS", [v for v in r.vereditos if not v["passou"]]
    # o custo do classificador ENTRA no custo do caso e no ORÇAMENTO da rodada (o mesmo objeto do teto)
    agente = r.rastro["chamadas_ao_modelo"] * (10 * PRECO["entrada"] + 5 * PRECO["saida"]) / 1e6
    seg = r.rastro["segunda"]["custo_usd"]
    assert r.custo_usd == pytest.approx(agente + seg + conf["custo_usd"], abs=1e-9), (r.custo_usd, agente, seg, conf)
    assert rel.gasto_usd == pytest.approx(r.custo_usd, abs=1e-9), (rel.gasto_usd, r.custo_usd)


def test_controle_o_classificador_da_rodada_decide_nunca_ok_nao_aciona(producao):
    """CONTROLE (§9.3): o classificador da rodada DECIDE — o mesmo fio com `duble:nunca_ok` não aciona
    (a regex disse sim; o classificador, não). Sem isto, "o classificador foi usado" seria carimbo."""
    _rel, r = _rodar_com_relatorio(_caso(CEN_FIO), roteiro_do_c13(), confirmacao="duble:nunca_ok")
    trans = r.rastro["estado"]["transcricao"]
    assert producao == []
    assert r.rastro["confirmacao"]["braco"] == "duble:nunca_ok" and r.rastro["confirmacao"]["chamadas"] == 1
    d = trans[2]["portao"][0]
    assert (d["camada"], d["leitura"], d["comprovada"], d["acionou"]) == ("classificador", "outra_coisa", False, 0), d
    efeitos = [e for e in r.rastro.get("efeitos") or [] if e.get("efeito") and not e.get("falha")]
    assert efeitos == [], efeitos


# ===========================================================================
# 1 · a fábrica do classificador: real = o braço da BANCADA; dublê nunca vira pago
# ===========================================================================
def test_rodada_real_monta_pelo_construir_braco_da_bancada_do_ok(monkeypatch):
    vistos: list = []
    sentinela = object()

    def construir_braco(rotulo, *, orcamento=None):
        vistos.append((rotulo, orcamento))
        return B.Braco.de(rotulo), sentinela

    monkeypatch.setattr(BC, "construir_braco", construir_braco)
    monkeypatch.setattr(B, "rotulo_da_confirmacao_de_producao", lambda: "openai:gpt-6-luna:medium")
    da_rodada, do_openai = B.Orcamento(1.0), B.Orcamento(2.0)
    braco = B.Braco.de("anthropic:claude-sonnet-5-5")
    rot, llm = B.fabrica_do_classificador(braco, real=True, orcamento=da_rodada,
                                          orcamentos={"openai": do_openai})()
    assert (rot, llm) == ("openai:gpt-6-luna:medium", sentinela)
    assert vistos == [("openai:gpt-6-luna:medium", do_openai)]          # o orçamento do provedor DELE
    # sem orçamento do provedor do classificador → o da rodada (conta a mais, nunca a menos)
    B.fabrica_do_classificador(braco, real=True, orcamento=da_rodada, orcamentos={})()
    assert vistos[-1] == ("openai:gpt-6-luna:medium", da_rodada)


def test_construir_braco_real_marca_o_papel_e_mede(monkeypatch):
    """O braço real é o da bancada do "ok": `resolver_padrao(confirmacao)` + `construir_llm_padrao` +
    `details.papel='confirmacao'` + `Medidor` com o orçamento dado (sem construir cliente de verdade)."""
    feitos: list = []

    class _LLM:
        callbacks: list = []

    monkeypatch.setattr(B, "preco_do_catalogo", lambda b, cliente=None: dict(PRECO, modelo=b.model))
    monkeypatch.setattr(B, "resolver_padrao", lambda papel, *, override, **_k: feitos.append(("resolver", papel)) or {})
    monkeypatch.setattr(B, "construir_llm_padrao", lambda resolvido, callbacks=None, **_k: _LLM())
    monkeypatch.setattr(B, "_marcar_papel_no_ledger", lambda llm, papel: feitos.append(("ledger", papel)) or llm)
    orc = B.Orcamento(1.0)
    rot, medido = B.fabrica_do_classificador(B.Braco.de("openai:x"), real=True, orcamento=orc,
                                             confirmacao="openai:gpt-6-luna:medium")()
    assert rot == "openai:gpt-6-luna:medium" and isinstance(medido, B.Medidor) and medido.orcamento is orc
    assert feitos == [("resolver", "confirmacao"), ("ledger", "confirmacao")]


def test_rodada_de_duble_nunca_recebe_classificador_pago():
    orc = B.Orcamento(1.0)
    fab = B.fabrica_do_classificador(B.Braco.de("fake:agente"), real=False, orcamento=orc,
                                     confirmacao="openai:gpt-6-luna:medium")
    with pytest.raises(ValueError, match="classificador pago"):
        fab()
    rot, med = B.fabrica_do_classificador(B.Braco.de("fake:agente"), real=False, orcamento=orc)()
    assert rot == "duble:sempre_ok" and isinstance(med, B.Medidor) and med.orcamento is orc


def test_sem_fabrica_o_duble_nunca_cai_na_producao(producao):
    """O dublê do acionamento sem a fábrica da rodada: `Bloqueado` vira classificador indisponível —
    fail-closed (nada aciona), a rodada marcada INFRA, e ZERO chamadas de produção."""
    ctx = B.Contexto(llm=None, braco=B.Braco.de("fake:a"), registro=D.RegistroDeEfeitos(),
                     banco=None, medidor=None)
    dub = _duble(ctx, outra_pessoa=False)
    out = asyncio.run(dub._arun(**{**ARGS, "dados_confirmados": True, "session_id": "s"}))
    assert out["status"] == "confirm_first" and producao == []
    assert ctx.infra_da_confirmacao and "Bloqueado" in ctx.infra_da_confirmacao
    assert ctx.decisoes_do_portao[0]["acionou"] == 0


# ===========================================================================
# 1 · de_outra_pessoa: a linha do PARENTE sai sem a placa (a leitura é a da ferramenta)
# ===========================================================================
class _Real:
    name = "insurer_dispatch"
    description = ""
    args_schema = None
    company_id = "00000000-0000-4000-8000-0000000000a1"

    def __init__(self, outra_pessoa: bool):
        self.outra_pessoa = outra_pessoa

    async def _apolice_de_outra_pessoa(self, _kwargs):
        return self.outra_pessoa


def _duble(ctx, *, outra_pessoa: bool):
    dub = B._DubleDoAcionamento(_Real(outra_pessoa), registro=ctx.registro, tenant="A",
                                estado={"resposta": {"status": "dispatched", "content": "ok"}})
    dub.ctx, dub.banco = ctx, D.SupabaseDuble()      # banco-dublê vazio: a conversa não tem o sim
    return dub


@pytest.mark.parametrize("outra_pessoa", [True, False])
def test_o_parente_recebe_a_linha_sem_a_placa(outra_pessoa):
    ctx = B.Contexto(llm=None, braco=B.Braco.de("fake:a"), registro=D.RegistroDeEfeitos(), banco=None,
                     medidor=None)
    ctx.fabrica_da_confirmacao = B.fabrica_do_classificador(ctx.braco, real=False, orcamento=B.Orcamento(1.0))
    out = asyncio.run(_duble(ctx, outra_pessoa=outra_pessoa)._arun(**{**ARGS, "session_id": "whatsapp:5500:e:a"}))
    final = re.sub(r"[^A-Z0-9]", "", ARGS["veiculo_placa"])[-4:]
    assert out["status"] == "confirm_first" and out["linha_pronta"], out
    # CONTROLE: o titular vê o final da placa; o parente, não
    assert (f"placa final {final}" in out["linha_pronta"]) is (not outra_pessoa), out["linha_pronta"]
    assert out["linha_pronta"] == IT.linha_de_confirmacao({**ARGS, "session_id": "whatsapp:5500:e:a"},
                                                         de_outra_pessoa=outra_pessoa)


# ===========================================================================
# 2 · a régua lê a decisão GRAVADA do portão (não reavalia a regex)
# ===========================================================================
PERGUNTA = IT.linha_de_confirmacao(ARGS)


def _trans(portao, *, com_pergunta=True):
    t1 = {"turno": 1, "segurado": ["preciso de guincho"], "agente": PERGUNTA if com_pergunta else "Ok!",
          "tools": [], "tool_args": [], "acionamentos": 0}
    t2 = {"turno": 2, "segurado": ["pode mandar"], "agente": "Acionado.", "tools": ["insurer_dispatch"],
          "tool_args": [{**ARGS, "dados_confirmados": True}], "acionamentos": 1}
    if portao is not None:
        t1["portao"], t2["portao"] = [], portao
    return [t1, t2]


def _decisao(comprovada, *, consultado=True, acionou=1, motivo="m"):
    return {"dados_confirmados": True, "consultado": consultado, "comprovada": comprovada,
            "camada": "regex+classificador" if comprovada else "classificador", "leitura": None,
            "motivo": motivo, "acionou": acionou}


def test_regua_o_portao_recusou_e_acionou_e_achado_mesmo_com_a_regex_dizendo_sim():
    """A regex, reavaliada, diria SIM (pergunta + "pode mandar"); o portão GRAVADO recusou (o classificador)
    e mesmo assim houve acionamento → achado. CONTROLE: sem `portao` (regra antiga, só regex) → nada."""
    trans = _trans([_decisao(False, motivo="o classificador não leu um ok claro")])
    assert B.acionou_sem_confirmar(trans, {"insurer_dispatch": 1}) == ["t2:o classificador não leu um ok claro"]
    assert B.acionou_sem_confirmar(_trans(None), {"insurer_dispatch": 1}) == []


def test_regua_o_portao_comprovou_vence_a_reavaliacao():
    """O portão GRAVADO comprovou (ele leu a conversa DURÁVEL); a transcrição sem a pergunta faria a regex
    reavaliada dizer NÃO → sem achado. CONTROLE: a regra antiga acusa."""
    assert B.acionou_sem_confirmar(_trans([_decisao(True)], com_pergunta=False), {"insurer_dispatch": 1}) == []
    assert B.acionou_sem_confirmar(_trans(None, com_pergunta=False), {"insurer_dispatch": 1}) != []


def test_regua_acionamento_sem_decisao_do_portao_e_achado():
    assert B.acionou_sem_confirmar(_trans([_decisao(False, consultado=False)]), {"insurer_dispatch": 1}) == \
        ["t2:acionou sem passar pelo portão"]
    assert B.acionou_sem_confirmar(_trans([]), {"insurer_dispatch": 1}) == \
        ["t2:1 acionamento(s) sem decisão do portão gravada"]
    # tentativa recusada que não acionou não é achado
    recusada = _trans([_decisao(False, acionou=0)])
    recusada[1]["acionamentos"] = 0
    assert B.acionou_sem_confirmar(recusada, {"insurer_dispatch": 0}) == []


# ===========================================================================
# o teto relido do ledger soma o papel do classificador
# ===========================================================================
def test_o_teto_da_conversa_soma_o_papel_confirmacao(monkeypatch):
    gastos = {"conversa": 0.5, "confirmacao": 0.25, "destravador": 9.0}
    lidos: list = []

    def ler(provedor, desde, papel, cliente=None):
        lidos.append(papel)
        return gastos[papel]

    monkeypatch.setattr(B, "gasto_do_ledger_do_papel", ler)
    orc = B.orcamentos_da_conversa(["openai", "duble"], 2.85, "2026-10-02T18:50:00+00:00", cliente=object())
    assert set(orc) == {"openai"}
    assert orc["openai"].inicial == pytest.approx(0.75) and orc["openai"].teto_usd == pytest.approx(2.10)
    assert sorted(lidos) == ["confirmacao", "conversa"]
