# -*- coding: utf-8 -*-
"""🔴 O TESTE DO FIO — SPEC-131-0 parte A (§1 "O FIO", §6), a costura (F5).

A afirmação-título: "o cálculo da renovação sai no Agger da PESSOA que é a dona da apólice — e no de mais ninguém".
Este arquivo mede o ELO (protocolo §0.3), do primeiro byte ao último, com as peças REAIS:

    a InfoCap NA REDE (dublê SÓ do `urlopen`, com a forma REAL de `/renovacoes` e do `/prod_docs` AVULSO —
    BLOCO0-INFOCAP §4: `codpro`, `nome_produtor`, `ordem`, `indireto`, `perpart`…; valores FICTÍCIOS)
      → `FonteInfocap.renovacoes_cruas` / `prod_docs_avulso` REAIS (`_get`, `_linhas`, a chave de cache REAL)
      → `dono.dono_da_apolice` REAL (a regra: a linha da corretora em `regras_de_dono`, senão o padrão do SISTEMA)
      → `membro_produtores` → `company_members`/`users_v2` (só membro ATIVO desta corretora)
      → `porta.calcular(servico='renovacao', dono_user_id=…)` REAL → `qual_agger.decidir` REAL
      → `multicalculo_calculos.conta_exigida_id` + `conta_regra` + `conta_fallback` + `conta_motivo`
      → o MOTOR real (`motor.uma_volta` → `robos.escolher(somente=conta exigida)`) → a sessão aberta no Agger
        (o robô e as sessões são o dublê de borda do `test_spec129b_o_motor`)

O banco é o dublê com as travas REAIS das migrations 20261005_01 + 20261011_03 (`BancoF2`) + 20261011_04 (`BancoU1`).
A fonte da corretora nasce com o MESMO rótulo de cache que `infocap_analytics_provider._abrir` dá
(`chave_de_cache(company_id, connection_id)`); que `dono.abrir_fonte` passa pelo `_abrir(company_id)` é o ⑩ da F2.

O que cada teste guarda:
    (o fio) a apólice cujo dono (`indireto="F"`) está na ORDEM 3 e é o código de membro_a → o Agger de membro_a,
            com regra/motivo gravados → o motor abre sessão SÓ nele
    (b) a apólice de outro dono (membro_b, sem Agger) → o Agger da corretora + aviso; nunca o de membro_a
    (c) o Quem Cobra Menos, com o Agger de membro_a na corretora → SÓ o Agger da corretora
    (d) a cotação pedida por membro_c (sem Agger próprio) → o Agger da corretora, com o porquê
    (e) corretora_b com o MESMO `codpro` e o MESMO `nosnum` nunca usa o vínculo nem a conta da corretora_a
        (+ CONTROLE: com a corretora fora da chave de cache, o dono CRUZARIA — o guarda consegue falhar)
    (f) a mutação "o dono é o `ordem 1`" (regra injetada na corretora) leva à conta ERRADA → o guarda fica VERMELHO
    (g) os dois routers da parte A estão no `main.py` e exigem a chave interna

⛔ Nenhum nome real (CLAUDE.md §13.9): corretora_a/corretora_b, membro_a/membro_b/membro_c. Senhas: texto fictício óbvio.
"""
from __future__ import annotations

import asyncio
import re
import sys
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

RAIZ = Path(__file__).resolve().parents[1]
for _p in (str(RAIZ), str(RAIZ / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import dubles_do_work_os as D  # noqa: E402
import test_spec129b_o_motor as TM  # noqa: E402
import test_spec1310_f2_dono as F2  # noqa: E402
import test_spec1310_f3_contas as F3  # noqa: E402
from dubles.banco_multicalculo import BancoU1, instalar_esquema  # noqa: E402
from app.services.sistema_de_gestao import dono as DONO  # noqa: E402
from portal_worker.multicalculo import robos as ROB  # noqa: E402

NOSNUM = F2.NOSNUM_COMUM          # 📊 o MESMO nosnum existe nos dois bancos medidos (BLOCO0-INFOCAP §2)
NOSNUM_DE_B = NOSNUM + 1          # uma segunda apólice da corretora_a, de outro dono
COD_A, COD_B, COD_ORDEM_1 = "247", "248", "11"
REGRA_ORDEM_1 = {"campo": "ordem", "igual": 1, "codigo": "codpro", "nome": "nome_produtor", "papel_no_nome": True}


class BancoDoFio(BancoU1, F2.BancoF2):
    """As travas das TRÊS migrations juntas: o motor e a porta (20261005_01 + 20261011_04) e o dono (20261011_03)."""


# =====================================================================================================================
# o mundo: duas corretoras, três pessoas, a InfoCap de cada uma
# =====================================================================================================================
@pytest.fixture
def fio(monkeypatch):
    from cryptography.fernet import Fernet
    from portal_worker import leases

    instalar_esquema(monkeypatch, com_porta=True)
    for tabela, cols in F2.ESQUEMA_F2.items():
        monkeypatch.setitem(D.ESQUEMA, tabela, cols)
    # o `membro()` da F3 semeia `is_owner` (a coluna existe no banco real)
    monkeypatch.setitem(D.ESQUEMA, "company_members",
                        {**F2.ESQUEMA_F2["company_members"], "is_owner": ("bool", True, None)})
    monkeypatch.setenv("PORTAL_VAULT_KEY", Fernet.generate_key().decode())
    monkeypatch.delenv("PORTAL_VAULT_KEY_ANTERIOR", raising=False)
    for nome in ("MULTICALCULO_TETO_CORRETORA_HORA", "MULTICALCULO_TETO_GERAL_HORA", "AUTOBROKERS_CANARIO"):
        monkeypatch.delenv(nome, raising=False)
    monkeypatch.setattr(leases, "redis_disponivel", lambda *a, **k: False)
    DONO._padrao_bruto.cache_clear()

    relogio = D.Relogio(TM.T0)
    amb = SimpleNamespace(banco=BancoDoFio(relogio), relogio=relogio, mundo=TM.MundoAgger())
    a, b = TM.empresa(amb), TM.empresa(amb)
    ga, gb = F3.conta_global(amb, a), F3.conta_global(amb, b)
    membro_a, membro_b, membro_c = F3.membro(amb, a), F3.membro(amb, a), F3.membro(amb, a)
    pa = F3.conta_da_pessoa(amb, a, membro_a)        # batida mais antiga: a PRIMEIRA do rodízio se o filtro cair

    # a InfoCap de cada corretora: o MESMO nosnum, o MESMO codpro dono — bancos diferentes (tokens diferentes)
    rede = F2.InfocapNaRede(monkeypatch)
    fontes = {a: rede.fonte(a, "token-a"), b: rede.fonte(b, "token-b")}

    async def abrir_fonte(_db, company_id):      # o `_abrir(company_id)` da corretora (⑩ da F2)
        return fontes[str(company_id)]

    monkeypatch.setattr(DONO, "abrir_fonte", abrir_fonte)
    for token, banco in (("token-a", rede.bancos["token-a"]), ("token-b", rede.bancos["token-b"])):
        banco["renov"] = [F2.renov(NOSNUM)] + ([F2.renov(NOSNUM_DE_B)] if token == "token-a" else [])
        banco["prod_docs"][(1, NOSNUM)] = F2._quatro_produtores(NOSNUM, dono_codpro=int(COD_A), dono_ordem=3)
    rede.bancos["token-a"]["prod_docs"][(1, NOSNUM_DE_B)] = F2._quatro_produtores(
        NOSNUM_DE_B, dono_codpro=int(COD_B), dono_ordem=2, dono_nome="248 - PESSOA B FECHADOR")

    db = amb.banco.visao("smith-api")
    DONO.vincular(db, a, user_id=membro_a, sistema="infocap", codfil=1, codigo_produtor=COD_A)
    DONO.vincular(db, a, user_id=membro_b, sistema="infocap", codfil=1, codigo_produtor=COD_B)
    yield SimpleNamespace(amb=amb, db=db, a=a, b=b, ga=ga, gb=gb, pa=pa, membro_a=membro_a, membro_b=membro_b,
                          membro_c=membro_c, rede=rede, fontes=fontes)
    DONO._padrao_bruto.cache_clear()


def _vence_em_dias(linha: dict) -> int:
    return (datetime.strptime(linha["fimvig"], "%d/%m/%Y").date() - TM.T0.date()).days


def _renovacoes(f, corretora) -> list:
    """O 1º byte: as apólices a renovar da InfoCap DESTA corretora (`/renovacoes`, a forma real)."""
    return f.fontes[corretora].renovacoes_cruas(date(2026, 10, 6), date(2026, 11, 5))


def _pela_renovacao(f, corretora, nosnum, *, codfil=1):
    """O fio, elo a elo, sem atalho: a apólice → o dono → a pessoa → a porta → o cálculo gravado."""
    linha = next(r for r in _renovacoes(f, corretora) if int(r["nosnum"]) == int(nosnum))
    dono = TM.rodar(DONO.dono_da_apolice(f.db, corretora, codfil=codfil, nosnum=linha["nosnum"]))
    aberto = F3.calcular(f.amb, corretora, servico="renovacao", dono_user_id=dono.user_id,
                         vence_em_dias=_vence_em_dias(linha))
    [calculo] = F3.calculos(f.amb, aberto.pedido_id)
    return dono, calculo


def _guarda_do_fio(f, dono, calculo, *, dono_esperado, conta_esperada):
    """O que o fio PROMETE: o dono certo chega à porta, e a conta gravada é a do Agger dele."""
    assert dono.status == "ok" and dono.user_id == dono_esperado, f"o dono chegou errado à porta: {dono}"
    assert calculo["conta_exigida_id"] == conta_esperada, "o cálculo da renovação não exige o Agger do dono"
    assert (calculo["conta_regra"], calculo["conta_fallback"]) == ("renovacao_do_dono", False)
    assert calculo["conta_motivo"] == "Calculada no Agger do dono da apólice."


def _rodar_o_motor(f) -> set:
    TM.rodar(TM.motor(f.amb, "m1").uma_volta())
    return F3.obtidas(f.amb)


# =====================================================================================================================
# 🔴 O FIO — a apólice cujo dono está na ordem 3 e é o código de membro_a chega ao motor com o Agger de membro_a
# =====================================================================================================================
def test_o_fio_a_renovacao_sai_no_agger_da_pessoa_dona_e_so_nele(fio):
    f = fio
    # o 1º byte: a InfoCap da corretora_a lista a apólice; o `/renovacoes` traz o prod_docs REDUZIDO (sem `indireto`),
    # e o produtor de ordem 1 dele NÃO é o dono (📊 o `produtor` de /renovacoes acerta o dono em 38/99 e 25/217)
    [linha] = [r for r in _renovacoes(f, f.a) if r["nosnum"] == NOSNUM]
    assert "indireto" not in linha["prod_docs"][0] and str(linha["prod_docs"][0]["cod_pro"]) == COD_ORDEM_1

    dono, calculo = _pela_renovacao(f, f.a, NOSNUM)
    # o elo dono: o `/prod_docs` AVULSO desta apólice foi lido na InfoCap DESTA corretora
    assert ("token-a", "/prod_docs", {"codfil": "1", "nosnum": str(NOSNUM)}) in f.rede.chamadas
    assert (dono.codigo_produtor, dono.regra_origem, dono.papel_cru) == (COD_A, DONO.ORIGEM_PADRAO, "FECHADORA")
    _guarda_do_fio(f, dono, calculo, dono_esperado=f.membro_a, conta_esperada=f.pa)
    pedido = next(p for p in f.amb.banco.linhas("multicalculo_pedidos") if p["id"] == calculo["pedido_id"])
    assert (pedido["servico"], pedido["origem"], pedido["solicitante_user_id"]) == ("renovacao", "auxiliar", None)

    # o elo motor: o rodízio NÃO vê o Agger da pessoa; só a conta exigida o abre
    assert [c["id"] for c in ROB.candidatos(f.db, f.a)] == [f.ga]
    assert _rodar_o_motor(f) == {f.pa}, "o motor abriu sessão noutro Agger que não o da dona"
    assert {p[0] for p in f.amb.mundo.posts} == {f.pa}
    c = next(x for x in f.amb.banco.linhas("multicalculo_calculos") if x["id"] == calculo["id"])
    assert (c["status"], c["account_id"]) == ("fechado", f.pa)


# =====================================================================================================================
# (b) a apólice de OUTRO dono (membro_b, sem Agger) → o da corretora, com aviso — nunca o de membro_a
# =====================================================================================================================
def test_b_a_apolice_de_outro_dono_sem_agger_vai_pela_corretora_nunca_pela_de_membro_a(fio):
    f = fio
    dono, calculo = _pela_renovacao(f, f.a, NOSNUM_DE_B)
    assert (dono.status, dono.codigo_produtor, dono.user_id) == ("ok", COD_B, f.membro_b)
    assert calculo["conta_exigida_id"] is None
    assert (calculo["conta_regra"], calculo["conta_fallback"]) == ("renovacao_da_corretora", True)
    assert "ainda não tem o próprio Agger" in calculo["conta_motivo"]
    assert "Agger da corretora" in calculo["conta_motivo"], "o aviso não ficou gravado"
    obtidas = _rodar_o_motor(f)
    assert obtidas == {f.ga} and f.pa not in obtidas, "a renovação de membro_b usou o Agger de membro_a"


# =====================================================================================================================
# (c) o Quem Cobra Menos, com um Agger de pessoa na corretora → SÓ o Agger da corretora
# =====================================================================================================================
def test_c_qcm_com_agger_de_membro_na_corretora_usa_so_o_da_corretora(fio):
    f = fio
    canal = TM.empresa(f.amb)
    TM._canal_com_adesao(f.amb, canal, [f.a])
    aberto = F3.calcular(f.amb, canal, corretoras=[f.a], servico="qcm")
    [calculo] = F3.calculos(f.amb, aberto.pedido_id)
    assert (calculo["conta_exigida_id"], calculo["conta_regra"], calculo["conta_fallback"]) == (None, "qcm_global",
                                                                                                False)
    assert _rodar_o_motor(f) == {f.ga}, "o Quem Cobra Menos abriu sessão no Agger de uma pessoa"


# =====================================================================================================================
# (d) a cotação pedida por membro_c, sem Agger próprio → o da corretora, com o porquê
# =====================================================================================================================
def test_d_cotacao_de_quem_nao_tem_agger_vai_pela_corretora_com_o_porque(fio):
    f = fio
    aberto = F3.calcular(f.amb, f.a, servico="cotacao", solicitante_user_id=f.membro_c)
    [calculo] = F3.calculos(f.amb, aberto.pedido_id)
    assert (calculo["conta_exigida_id"], calculo["conta_regra"], calculo["conta_fallback"]) == (
        None, "cotacao_da_corretora", True)
    assert "ainda não tem o próprio Agger" in calculo["conta_motivo"]
    pedido = next(p for p in f.amb.banco.linhas("multicalculo_pedidos") if p["id"] == aberto.pedido_id)
    assert pedido["solicitante_user_id"] == f.membro_c
    obtidas = _rodar_o_motor(f)
    assert obtidas == {f.ga} and f.pa not in obtidas


# =====================================================================================================================
# (e) corretora_b: o MESMO codpro, o MESMO nosnum — nem o cache, nem o vínculo, nem a conta da corretora_a
# =====================================================================================================================
def test_e_corretora_b_com_o_mesmo_codpro_e_nosnum_nunca_usa_o_vinculo_nem_a_conta_da_a(fio):
    f = fio
    _guarda_do_fio(f, *_pela_renovacao(f, f.a, NOSNUM), dono_esperado=f.membro_a, conta_esperada=f.pa)  # cache quente
    # membro_a TAMBÉM é da equipe da corretora_b — e ainda assim o código 247 da B não é dela (o vínculo é da A)
    F3.vincular(f.amb, f.b, f.membro_a)

    dono_b, calc_b = _pela_renovacao(f, f.b, NOSNUM)
    assert ("token-b", "/prod_docs", {"codfil": "1", "nosnum": str(NOSNUM)}) in f.rede.chamadas, \
        "a corretora_b leu o dono do cache da corretora_a"
    assert (dono_b.status, dono_b.codigo_produtor, dono_b.user_id) == ("sem_membro", COD_A, None)
    assert calc_b["company_id"] == f.b and calc_b["conta_exigida_id"] is None
    assert calc_b["conta_regra"] == "renovacao_da_corretora" and "não tem dono definido" in calc_b["conta_motivo"]

    # a B liga o MESMO código a uma pessoa DELA, com Agger: a B usa o dela; a A continua no de membro_a
    pessoa_b = F3.membro(f.amb, f.b)
    pb_b = F3.conta_da_pessoa(f.amb, f.b, pessoa_b)
    DONO.vincular(f.db, f.b, user_id=pessoa_b, sistema="infocap", codfil=1, codigo_produtor=COD_A)
    dono_b2, calc_b2 = _pela_renovacao(f, f.b, NOSNUM)
    _guarda_do_fio(f, dono_b2, calc_b2, dono_esperado=pessoa_b, conta_esperada=pb_b)
    _guarda_do_fio(f, *_pela_renovacao(f, f.a, NOSNUM), dono_esperado=f.membro_a, conta_esperada=f.pa)

    obtidas = _rodar_o_motor(f)
    assert f.pa in obtidas and pb_b in obtidas
    for c in f.amb.banco.linhas("multicalculo_calculos"):
        if c["status"] == "fechado":
            assert (c["company_id"], c["account_id"]) in {(f.a, f.pa), (f.b, pb_b), (f.b, f.gb)}, \
                "um cálculo de uma corretora saiu na conta da outra"

    # CONTROLE (o guarda consegue falhar): a fonte da B com o rótulo de cache da A lê o dono da A — é isso que a
    # chave `company_id:connection_id` impede
    vazada = F2.FI.FonteInfocap(login="token-b@exemplo.invalid", senha=F2.SENHA, rotulo=f.fontes[f.a]._rotulo)
    vazada._token = "token-b"
    f.rede.bancos["token-b"]["prod_docs"][(1, NOSNUM)] = []          # a B, na rede, já não tem produtores…
    assert vazada.prod_docs_avulso(1, NOSNUM), "…mas o cache com o rótulo da A devolve os da A"


# =====================================================================================================================
# (f) a MUTAÇÃO "o dono é o ordem 1": a conta sai ERRADA — e o guarda do fio fica VERMELHO
# =====================================================================================================================
def test_f_a_regra_ordem_1_leva_a_conta_errada_e_o_guarda_detecta(fio):
    f = fio
    # o ordem 1 desta apólice (código 11, INDICADOR) é de membro_b, que TEM Agger — o erro teria para onde ir
    DONO.vincular(f.db, f.a, user_id=f.membro_b, sistema="infocap", codfil=1, codigo_produtor=COD_ORDEM_1)
    pb = F3.conta_da_pessoa(f.amb, f.a, f.membro_b)

    _guarda_do_fio(f, *_pela_renovacao(f, f.a, NOSNUM), dono_esperado=f.membro_a, conta_esperada=f.pa)  # CONTROLE

    DONO.gravar_regra(f.db, f.a, "infocap", REGRA_ORDEM_1)          # a regra injetada na corretora
    dono, calculo = _pela_renovacao(f, f.a, NOSNUM)
    assert (dono.codigo_produtor, dono.regra_origem) == (COD_ORDEM_1, DONO.ORIGEM_CORRETORA), \
        "a auditoria não diz que foi a regra da corretora que decidiu"
    assert calculo["conta_exigida_id"] == pb != f.pa, "com a regra ordem 1 a conta deveria sair ERRADA"
    with pytest.raises(AssertionError):
        _guarda_do_fio(f, dono, calculo, dono_esperado=f.membro_a, conta_esperada=f.pa)

    DONO.apagar_regra(f.db, f.a, "infocap")                          # voltar ao padrão do sistema conserta
    _guarda_do_fio(f, *_pela_renovacao(f, f.a, NOSNUM), dono_esperado=f.membro_a, conta_esperada=f.pa)


# =====================================================================================================================
# (g) os dois routers da parte A estão no main.py e exigem a chave interna
# =====================================================================================================================
def test_g_os_routers_da_parte_a_estao_no_main_e_exigem_a_chave(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api import contas_da_corretora as CONTAS
    from app.api import servicos_da_corretora as SERV

    main = (RAIZ / "app" / "main.py").read_text(encoding="utf-8")
    for modulo, nome in (("contas_da_corretora", "contas_da_corretora_router"),
                         ("servicos_da_corretora", "servicos_da_corretora_router")):
        assert re.search(rf"^from app\.api\.{modulo} import router as {nome}", main, re.M), modulo
        assert re.search(rf"^app\.include_router\({nome}\)", main, re.M), f"{nome} não está registrado"

    monkeypatch.setenv("BACKEND_INTERNAL_API_KEY", "chave-interna-de-teste")
    app = FastAPI()
    app.include_router(CONTAS.router)
    app.include_router(SERV.router)
    c = TestClient(app)
    cid = "00000000-0000-4000-8000-000000000000"
    pedidos = [("get", f"/api/servicos-da-corretora?company_id={cid}"),
               ("get", f"/api/servicos-da-corretora/prontidao?company_id={cid}"),
               ("put", "/api/servicos-da-corretora"),
               ("get", f"/api/contas-da-corretora/sistema-de-gestao/vinculos?company_id={cid}"),
               ("get", f"/api/contas-da-corretora/sistema-de-gestao/regra?company_id={cid}"),
               ("put", "/api/contas-da-corretora/sistema-de-gestao/regra"),
               ("post", "/api/contas-da-corretora/sistema-de-gestao/medir")]
    for metodo, url in pedidos:
        assert getattr(c, metodo)(url).status_code == 401, url
        assert getattr(c, metodo)(url, headers={"X-AutoBrokers-Internal-Key": "outra"}).status_code == 401, url
    # CONTROLE: com a chave certa a porta abre (a recusa seguinte é do corpo/uuid, não da chave)
    certa = {"X-AutoBrokers-Internal-Key": "chave-interna-de-teste"}
    assert c.get("/api/servicos-da-corretora?company_id=nao-e-uuid", headers=certa).status_code == 400
    assert c.put("/api/contas-da-corretora/sistema-de-gestao/regra", headers=certa, content=b"[]").status_code == 400
