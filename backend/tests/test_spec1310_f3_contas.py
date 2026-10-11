# -*- coding: utf-8 -*-
"""SPEC-131-0 parte A · F3 — as CONTAS: o Agger da corretora × o Agger de cada pessoa, e QUAL deles calcula.

O FIO: a PORTA real (`porta.calcular(servico=…)`) → `qual_agger.decidir` REAL → `multicalculo_calculos.conta_exigida_id`
+ regra + fallback + motivo → o MOTOR real (`motor.uma_volta` → `robos.escolher(somente=…)`) → a sessão do Agger
(dublê de borda do `test_spec129b_o_motor`). O banco é o dublê com as travas da migration 20261011_04
(`dubles.banco_multicalculo.BancoU1`). Nenhum nome de corretora nem de pessoa (CLAUDE.md §13.9): `corretora_a/b`,
`membro_a/b`. Nenhuma senha real.

O que cada teste guarda (o pedido da fatia, (a)–(h)):
    (a) o Quem Cobra Menos com um Agger de pessoa na corretora → SÓ o da corretora      (mutação: filtro de uso)
    (b) a cotação de membro_a sai no Agger de membro_a, nunca no de membro_b            (mutação: filtro do dono)
    (c) quem pediu não tem Agger → o da corretora, com fallback e aviso
    (d) renovação: o Agger do dono; sem conta / inativo → o da corretora + aviso; senha recusada → recusa, e o da
        corretora só se vence em < 5 dias
    (e) Agger de pessoa que saiu da equipe, ou de OUTRA corretora → nunca escolhido      (mutação: membro_ativo)
    (f) a retomada de um cálculo no Agger de uma pessoa fica na MESMA conta             (mutação: `somente` na retomada)
    (g) login de pessoa: logout sempre; ocupada 3× → falha com o motivo; senha recusada → falha na 1ª
    (h) duas corretoras: cada uma vê e grava só as suas pessoas e contas
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

RAIZ = Path(__file__).resolve().parents[1]
for _p in (str(RAIZ), str(RAIZ / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import test_spec129b_o_motor as TM  # noqa: E402
from test_spec129b_o_motor import ambiente  # noqa: E402,F401  (fixture)
from app.services.multicalculo import qual_agger as QA  # noqa: E402
from app.services.multicalculo.pedido import PedidoDeCalculo  # noqa: E402
from app.services.multicalculo.porta import ContaRecusada, MulticalculoProvider  # noqa: E402
from app.services.multicalculo.repositorio import RepositorioMulticalculo  # noqa: E402
from portal_worker.multicalculo import conta_do_robo as CR  # noqa: E402
from portal_worker.multicalculo import motor as MOT  # noqa: E402
from portal_worker.multicalculo import robos as ROB  # noqa: E402

CHAVE_HMAC = "chave-hmac-ficticia-da-f3-0123456789"
SENHA_A = "senha-de-teste-1"
SENHA_B = "senha-de-teste-2"


# =====================================================================================================================
# a semeadura
# =====================================================================================================================
def membro(amb, corretora: str, *, papel: str = "member", ativo: bool = True, usuario_ativo: bool = True,
           nome: str = "Pessoa Ficticia") -> str:
    uid = str(uuid4())
    if not [u for u in amb.banco.linhas("users_v2") if u.get("id") == uid]:
        amb.banco.semear("users_v2", {"id": uid, "status": "active" if usuario_ativo else "lead",
                                      "first_name": nome, "last_name": uid[:4], "deleted_at": None})
    amb.banco.semear("company_members", {"id": str(uuid4()), "user_id": uid, "company_id": corretora, "role": papel,
                                         "is_owner": False, "status": "active" if ativo else "inactive"})
    return uid


def vincular(amb, corretora: str, uid: str, *, papel: str = "member") -> None:
    amb.banco.semear("company_members", {"id": str(uuid4()), "user_id": uid, "company_id": corretora, "role": papel,
                                         "is_owner": False, "status": "active"})


def conta_global(amb, corretora: str) -> str:
    return TM.robo(amb, corretora, rotulo=CR.ROTULO_DA_CORRETORA)


def conta_da_pessoa(amb, corretora: str, dono: str, *, estado: str = "ativo", batida_antiga: bool = True) -> str:
    """O Agger de uma pessoa. `batida_antiga`: ela fica PRIMEIRO na ordem do rodízio (`robo_batida_em` mais antiga) — se
    o filtro de uso cair, é ELA que o motor pega (o guarda consegue falhar)."""
    from portal_worker import vault

    rid = str(uuid4())
    amb.banco.semear("portal_accounts", {
        "id": rid, "company_id": corretora, "portal_key": "agger", "account_label": f"agger-da-pessoa-{dono}",
        "username": f"pessoa-{rid[:6]}@exemplo.invalid", "secret_encrypted": vault.encrypt(TM.SENHA),
        "robo_estado": estado, "robo_janela": None, "uso": "membro", "dono_user_id": dono,
        "robo_batida_em": (TM.T0 - timedelta(days=30)).isoformat() if batida_antiga else None,
    })
    return rid


def dados_do_pedido() -> dict:
    return {
        "segurado": {"cpf_cnpj": TM.CPF, "nome": TM.NOME, "nascimento": "1980-01-01", "sexo": "F", "estado_civil": 2,
                     "cep": "88000000"},
        "veiculo": {"placa": "ABC1D23", "fipe": "0013277", "ano_fabricacao": 2011, "ano_modelo": 2012,
                    "combustivel": "flex", "uso": 1},
        "pernoite": {"cep_pernoite": "88000000", "garagem_residencia": "2"},
        "condutor": {"cpf": TM.CPF, "nome": TM.NOME, "nascimento": "1980-01-01", "sexo": "F", "estado_civil": 2,
                     "tempo_habilitacao": 11, "relacao_com_segurado": "proprio", "jovem_condutor": False},
        "questionario": {"km_mensal": 500},
    }


def porta(amb) -> MulticalculoProvider:
    # as coberturas levam a marca `preset` que o robô dublê do motor lê (`test_spec129b_o_motor.RoboDuble`)
    return MulticalculoProvider(RepositorioMulticalculo(amb.banco.visao("smith-api")),
                                ambiente={"MULTICALCULO_HMAC_KEY": CHAVE_HMAC}, agora=amb.relogio.agora,
                                presets=lambda o: {"preset": o})


def calcular(amb, company_id: str, **kw):
    kw.setdefault("opcoes", ("padrao",))
    return TM.rodar(porta(amb).calcular(company_id=company_id, pedido=PedidoDeCalculo.de_dict(dados_do_pedido()),
                                        **kw))


def calculos(amb, pedido_id: str) -> list:
    return [c for c in amb.banco.linhas("multicalculo_calculos") if c["pedido_id"] == pedido_id]


def obtidas(amb) -> set:
    """As contas em que o motor ABRIU sessão no Agger."""
    return {cid for (_proc, cid) in amb.mundo.obter}


def supa(amb):
    return amb.banco.visao("smith-api")


# =====================================================================================================================
# (a) o Quem Cobra Menos nunca usa o Agger de uma pessoa
# =====================================================================================================================
def test_a_qcm_com_agger_de_pessoa_na_corretora_calcula_so_no_da_corretora(ambiente):
    amb = ambiente
    canal, a = TM.empresa(amb), TM.empresa(amb)
    g = conta_global(amb, a)
    ma = membro(amb, a)
    pa = conta_da_pessoa(amb, a, ma)          # PRIMEIRA na ordem do rodízio (batida mais antiga)
    TM._canal_com_adesao(amb, canal, [a])

    # o rodízio do motor NÃO vê o Agger da pessoa — só o da corretora
    assert [c["id"] for c in ROB.candidatos(supa(amb), a)] == [g]
    assert [c["id"] for c in ROB.candidatos(supa(amb), a, somente=pa)] == [g, pa] or \
        {c["id"] for c in ROB.candidatos(supa(amb), a, somente=pa)} == {g, pa}
    # e mesmo forçado (`somente`), o QCM não serve no Agger de uma pessoa
    conta_pa = next(c for c in ROB.candidatos(supa(amb), a, somente=pa) if c["id"] == pa)
    ok, porque = ROB.conta_elegivel(conta_pa, "canal", TM.T0, canario=False, servico="qcm", somente=pa, dono_ativo=True)
    assert not ok and "não atende" in porque

    aberto = calcular(amb, canal, corretoras=[a], opcoes=("padrao", "economica"), servico="qcm")
    pedido = next(p for p in amb.banco.linhas("multicalculo_pedidos") if p["id"] == aberto.pedido_id)
    assert (pedido["servico"], pedido["origem"], pedido["solicitante_user_id"]) == ("qcm", "canal", None)
    for c in calculos(amb, aberto.pedido_id):
        assert (c["conta_exigida_id"], c["conta_regra"], c["conta_fallback"]) == (None, "qcm_global", False)

    TM.rodar(TM.motor(amb, "m1").uma_volta())
    assert obtidas(amb) == {g}, "o Quem Cobra Menos abriu sessão no Agger de uma pessoa"
    assert {p[0] for p in amb.mundo.posts} == {g}
    assert {c["status"] for c in calculos(amb, aberto.pedido_id)} == {"fechado"}


# =====================================================================================================================
# (b) a cotação de membro_a sai no Agger de membro_a — nunca no de membro_b
# =====================================================================================================================
def test_b_cotacao_de_membro_a_usa_o_agger_de_membro_a_nunca_o_de_membro_b(ambiente):
    amb = ambiente
    a = TM.empresa(amb)
    g = conta_global(amb, a)
    ma, mb = membro(amb, a), membro(amb, a)
    pb = conta_da_pessoa(amb, a, mb)          # a de membro_b nasce PRIMEIRO (se o filtro do dono cair, sai ela)
    pa = conta_da_pessoa(amb, a, ma)

    aberto = calcular(amb, a, servico="cotacao", solicitante_user_id=ma)
    pedido = next(p for p in amb.banco.linhas("multicalculo_pedidos") if p["id"] == aberto.pedido_id)
    assert (pedido["servico"], pedido["origem"], pedido["solicitante_user_id"]) == ("cotacao", "auxiliar", ma)
    [c] = calculos(amb, aberto.pedido_id)
    assert (c["conta_exigida_id"], c["conta_regra"], c["conta_fallback"]) == (pa, "cotacao_da_pessoa", False)
    assert c["conta_motivo"] == "Calculada no Agger de quem pediu."

    TM.rodar(TM.motor(amb, "m1").uma_volta())
    assert obtidas(amb) == {pa}, "a cotação de membro_a abriu sessão noutra conta"
    assert pb not in obtidas(amb) and g not in obtidas(amb)
    c = next(x for x in amb.banco.linhas("multicalculo_calculos") if x["id"] == c["id"])
    assert (c["status"], c["account_id"]) == ("fechado", pa)


# =====================================================================================================================
# (c) quem pediu não tem Agger próprio → o da corretora, com fallback e aviso
# =====================================================================================================================
def test_c_sem_agger_proprio_vai_pelo_da_corretora_com_aviso(ambiente):
    amb = ambiente
    a = TM.empresa(amb)
    g = conta_global(amb, a)
    ma = membro(amb, a)

    aberto = calcular(amb, a, servico="cotacao", solicitante_user_id=ma)
    [c] = calculos(amb, aberto.pedido_id)
    assert (c["conta_exigida_id"], c["conta_regra"], c["conta_fallback"]) == (None, "cotacao_da_corretora", True)
    assert "ainda não tem o próprio Agger" in c["conta_motivo"] and "Agger da corretora" in c["conta_motivo"]
    TM.rodar(TM.motor(amb, "m1").uma_volta())
    assert obtidas(amb) == {g}

    # CONTROLE do aviso: sem o Agger da corretora conectado, o aviso diz isso também
    b = TM.empresa(amb)
    mb = membro(amb, b)
    d = QA.decidir(supa(amb), company_id=b, servico="cotacao", solicitante_user_id=mb)
    assert d.fallback and d.conta_id is None and "também não está conectado" in (d.aviso or "")


# =====================================================================================================================
# (d) a renovação: o Agger do dono
# =====================================================================================================================
def test_d_renovacao_no_agger_do_dono_e_os_desvios(ambiente):
    amb = ambiente
    a = TM.empresa(amb)
    conta_global(amb, a)
    dono, sem_conta, inativo = membro(amb, a), membro(amb, a), membro(amb, a, ativo=False)
    pd = conta_da_pessoa(amb, a, dono)
    conta_da_pessoa(amb, a, inativo)

    aberto = calcular(amb, a, servico="renovacao", dono_user_id=dono)
    [c] = calculos(amb, aberto.pedido_id)
    assert (c["conta_exigida_id"], c["conta_regra"], c["conta_fallback"]) == (pd, "renovacao_do_dono", False)
    pedido = next(p for p in amb.banco.linhas("multicalculo_pedidos") if p["id"] == aberto.pedido_id)
    assert (pedido["servico"], pedido["origem"]) == ("renovacao", "auxiliar")
    assert c["prioridade"] == 5, "a renovação tem prioridade menor que o canal"

    for quem, regra, trecho in ((sem_conta, "renovacao_da_corretora", "ainda não tem o próprio Agger"),
                                (inativo, "renovacao_da_corretora", "não está ativo na equipe"),
                                (None, "renovacao_da_corretora", "não tem dono definido")):
        d = QA.decidir(supa(amb), company_id=a, servico="renovacao", dono_user_id=quem)
        assert (d.conta_id, d.regra, d.fallback, d.recusa) == (None, regra, True, None), quem
        assert trecho in d.motivo and d.aviso

    # senha recusada no Agger do dono → RECUSA (nada gravado); o da corretora só se vence em < 5 dias
    next(x for x in amb.banco.linhas("portal_accounts") if x["id"] == pd).update(robo_estado="bloqueado")
    antes = len(amb.banco.linhas("multicalculo_pedidos"))
    with pytest.raises(ContaRecusada, match="recusou a senha"):
        calcular(amb, a, servico="renovacao", dono_user_id=dono, vence_em_dias=10)
    assert len(amb.banco.linhas("multicalculo_pedidos")) == antes, "a recusa gravou um pedido"
    d = QA.decidir(supa(amb), company_id=a, servico="renovacao", dono_user_id=dono, vence_em_dias=5)
    assert d.recusa and d.regra == "renovacao_recusada", "5 dias NÃO é menos que 5"
    urgente = calcular(amb, a, servico="renovacao", dono_user_id=dono, vence_em_dias=4)
    [c] = calculos(amb, urgente.pedido_id)
    assert (c["conta_exigida_id"], c["conta_regra"], c["conta_fallback"]) == (None, "renovacao_da_corretora_urgente",
                                                                              True)
    # a corretora configura o prazo (a chave que a F4 põe no padrão do produto)
    cfg = {"servicos": {"renovacao": {"conta_global_se_vence_em_dias": 15}}}
    d = QA.decidir(supa(amb), company_id=a, servico="renovacao", dono_user_id=dono, vence_em_dias=10, cfg=cfg)
    assert d.recusa is None and d.regra == "renovacao_da_corretora_urgente"


# =====================================================================================================================
# (e) Agger de quem saiu da equipe, ou de OUTRA corretora → nunca escolhido (fail-closed)
# =====================================================================================================================
def test_e_agger_de_quem_saiu_ou_de_outra_corretora_nunca_e_escolhido(ambiente):
    amb = ambiente
    a, b = TM.empresa(amb), TM.empresa(amb)
    g = conta_global(amb, a)
    ma = membro(amb, a)
    pa = conta_da_pessoa(amb, a, ma)

    # o cálculo foi pedido enquanto ela era da equipe (a conta foi EXIGIDA)…
    aberto = calcular(amb, a, servico="cotacao", solicitante_user_id=ma)
    [c] = calculos(amb, aberto.pedido_id)
    assert c["conta_exigida_id"] == pa
    # …e ela saiu antes do disparo: o motor reconfere e NÃO usa a conta — nem cai calado no Agger da corretora
    next(v for v in amb.banco.linhas("company_members") if v["user_id"] == ma).update(status="inactive")
    assert ROB.membro_ativo(supa(amb), a, ma) is False
    assert TM.rodar(TM.motor(amb, "m1").uma_volta()) == 0
    assert obtidas(amb) == set() and amb.mundo.posts == []
    assert next(x for x in amb.banco.linhas("multicalculo_calculos") if x["id"] == c["id"])["status"] == "na_fila"
    # um pedido NOVO dela vai pelo da corretora, com o porquê
    d = QA.decidir(supa(amb), company_id=a, servico="cotacao", solicitante_user_id=ma)
    assert (d.conta_id, d.fallback) == (None, True) and "não está ativo" in d.motivo
    # usuário desativado (o vínculo ainda ativo) também derruba a conta
    mu = membro(amb, a, usuario_ativo=False)
    assert ROB.membro_ativo(supa(amb), a, mu) is False

    # OUTRA corretora: a pessoa é da equipe de A e de B, mas o Agger dela é de B → numa cotação de A, nunca o de B
    mx = membro(amb, b)
    vincular(amb, a, mx)
    px_b = conta_da_pessoa(amb, b, mx)
    d = QA.decidir(supa(amb), company_id=a, servico="cotacao", solicitante_user_id=mx)
    assert d.conta_id is None and d.fallback, "a cotação de A pegou o Agger que a pessoa tem em B"
    assert px_b not in {x["id"] for x in ROB.candidatos(supa(amb), a, somente=px_b)}
    # e o banco recusa um cálculo de A que exija uma conta de B (FK composta)
    with pytest.raises(Exception, match="fk_mc_calculos_conta_exigida"):
        amb.banco.visao("x").table("multicalculo_calculos").update({"conta_exigida_id": px_b}).eq(
            "id", c["id"]).eq("company_id", a).execute()
    assert g not in obtidas(amb)


# =====================================================================================================================
# (f) a retomada: o negócio de uma pessoa é lido no Agger DELA
# =====================================================================================================================
def _calculando_no(amb, corretora, conta, *, servico="cotacao", exigida=True) -> str:
    pid, [cid] = TM.pedido(amb, corretora, [corretora], opcoes=("padrao",), origem="auxiliar", expira_min=120)
    next(p for p in amb.banco.linhas("multicalculo_pedidos") if p["id"] == pid).update(servico=servico)
    next(x for x in amb.banco.linhas("multicalculo_calculos") if x["id"] == cid).update(
        status="calculando", account_id=conta, conta_exigida_id=conta if exigida else None, negocio_ref="NEG-R",
        versao=1, dono="motor-morto", batida_em=(TM.T0 - timedelta(minutes=10)).isoformat(),
        disparado_em=(TM.T0 - timedelta(minutes=10)).isoformat(), tentativas=1)
    amb.mundo.versoes["NEG-R"] = 1
    amb.mundo.servir[("NEG-R", 1)] = 0
    return cid


@pytest.mark.parametrize("exigida", [True, False], ids=["com_conta_exigida", "so_a_conta_do_negocio"])
def test_f_retomada_de_calculo_no_agger_de_pessoa_fica_na_mesma_conta(ambiente, exigida):
    amb = ambiente
    a = TM.empresa(amb)
    g = conta_global(amb, a)
    ma = membro(amb, a)
    pa = conta_da_pessoa(amb, a, ma, batida_antiga=False)
    cid = _calculando_no(amb, a, pa, exigida=exigida)

    TM.rodar(TM.motor(amb, "m2").uma_volta())
    assert obtidas(amb) == {pa}, "a retomada leu o negócio da pessoa noutro login"
    assert g not in obtidas(amb) and amb.mundo.posts == [], "retomada nunca reposta"
    c = next(x for x in amb.banco.linhas("multicalculo_calculos") if x["id"] == cid)
    assert (c["status"], c["account_id"]) == ("fechado", pa)


# =====================================================================================================================
# (g) login de PESSOA: logout sempre · ocupada 3× → falha com o motivo · senha recusada → falha na 1ª
# =====================================================================================================================
def test_g_login_de_pessoa_sai_sempre_e_a_corretora_segura_a_sessao(ambiente):
    amb = ambiente
    a = TM.empresa(amb)
    g = conta_global(amb, a)
    ma = membro(amb, a)
    pa = conta_da_pessoa(amb, a, ma)
    calcular(amb, a, servico="cotacao", solicitante_user_id=ma)
    m = TM.motor(amb, "m1")
    TM.rodar(m.uma_volta())
    assert amb.mundo.abertas.get(pa) == set(), "a sessão da pessoa ficou aberta (o robô não saiu)"
    assert TM.conta(amb, pa)["robo_dono"] is None
    # CONTROLE: o Agger da corretora (robô dedicado) segura a sessão ociosa
    calcular(amb, a, servico="cotacao", solicitante_user_id=membro(amb, a))
    TM.rodar(m.uma_volta())
    assert amb.mundo.abertas.get(g) == {"m1"} and TM.conta(amb, g)["robo_dono"] == "m1"
    TM.rodar(m.desligar())


def test_g_pessoa_no_proprio_agger_tres_vezes_o_calculo_falha_com_o_motivo(ambiente):
    amb = ambiente
    a = TM.empresa(amb)
    g = conta_global(amb, a)
    ma = membro(amb, a)
    pa = conta_da_pessoa(amb, a, ma)
    aberto = TM.rodar(porta(amb).calcular(company_id=a, pedido=PedidoDeCalculo.de_dict(dados_do_pedido()),
                                          opcoes=("padrao",), servico="cotacao", solicitante_user_id=ma))
    [cid] = [c["id"] for c in calculos(amb, aberto.pedido_id)]
    amb.mundo.login[pa] = TM.SessaoOcupada
    for vez in (1, 2, 3):
        TM.rodar(TM.motor(amb, f"m{vez}").uma_volta())
        c = next(x for x in amb.banco.linhas("multicalculo_calculos") if x["id"] == cid)
        assert TM.conta(amb, pa)["robo_estado"] == "ocupada"
        if vez < 3:
            assert (c["status"], c["tentativas"]) == ("na_fila", vez), vez
        amb.relogio.avancar(MOT.OCUPADA_MIN * 60 + 1)
    assert c["status"] == "falhou" and c["erro"].startswith("agger_da_pessoa_em_uso"), c["erro"]
    assert obtidas(amb) == {pa} and amb.mundo.posts == [], "caiu no Agger da corretora"
    assert g not in obtidas(amb)


def test_g_senha_recusada_no_agger_de_pessoa_bloqueia_e_falha_na_primeira(ambiente):
    amb = ambiente
    a = TM.empresa(amb)
    g = conta_global(amb, a)
    ma = membro(amb, a)
    pa = conta_da_pessoa(amb, a, ma)
    aberto = calcular(amb, a, servico="cotacao", solicitante_user_id=ma)
    amb.mundo.login[pa] = TM.CredencialRecusada
    TM.rodar(TM.motor(amb, "m1").uma_volta())
    TM.rodar(TM.motor(amb, "m2").uma_volta())
    assert TM.conta(amb, pa)["robo_estado"] == "bloqueado"
    assert len([x for x in amb.mundo.obter if x[1] == pa]) == 1, "insistiu no login da pessoa"
    [c] = calculos(amb, aberto.pedido_id)
    assert c["status"] == "falhou" and "recusou a senha" in c["erro"]
    assert g not in obtidas(amb)


# =====================================================================================================================
# (h) duas corretoras — e o cadastro, a tela e o desligar
# =====================================================================================================================
@pytest.fixture
def api(ambiente, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api import portal as API

    monkeypatch.setenv("BACKEND_INTERNAL_API_KEY", "chave-interna-de-teste")
    visao = ambiente.banco.visao("smith-api")
    monkeypatch.setattr(API, "get_supabase_client", lambda: SimpleNamespace(client=visao))
    app = FastAPI()
    app.include_router(API.router)
    return TestClient(app, raise_server_exceptions=False)


def _post(cli, rota, **corpo):
    return cli.post(f"/api/portal/{rota}", headers={"X-AutoBrokers-Internal-Key": "chave-interna-de-teste"}, json=corpo)


def test_h_duas_corretoras_cada_uma_com_as_suas_pessoas_e_contas(ambiente, api, caplog):
    amb = ambiente
    caplog.set_level(logging.DEBUG)
    a, b = TM.empresa(amb), TM.empresa(amb)
    conta_global(amb, a), conta_global(amb, b)
    adm_a = membro(amb, a, papel="admin_company")
    ma, mb = membro(amb, a), membro(amb, b)

    # a própria pessoa conecta o Agger dela; o admin de A conecta o de outra pessoa de A
    r = _post(api, "aggers-da-equipe", company_id=a, acao="conectar", dono_user_id=ma, por_user_id=ma,
              usuario="pessoa-a@exemplo.invalid", senha=SENHA_A)
    assert r.status_code == 200, r.text
    outra_a = membro(amb, a)
    assert _post(api, "aggers-da-equipe", company_id=a, acao="conectar", dono_user_id=outra_a, por_user_id=adm_a,
                 usuario="pessoa-a2@exemplo.invalid", senha=SENHA_A).status_code == 200
    # um membro comum NÃO mexe no Agger de outra pessoa · o admin de A NÃO cadastra pessoa de B
    r = _post(api, "aggers-da-equipe", company_id=a, acao="pausar", dono_user_id=outra_a, por_user_id=ma)
    assert r.status_code == 409 and "administrador" in r.json()["detail"]
    r = _post(api, "aggers-da-equipe", company_id=a, acao="conectar", dono_user_id=mb, por_user_id=adm_a,
              usuario="pessoa-b@exemplo.invalid", senha=SENHA_B)
    assert r.status_code == 409 and "não está ativa na equipe" in r.json()["detail"]
    assert _post(api, "aggers-da-equipe", company_id=b, acao="conectar", dono_user_id=mb, por_user_id=mb,
                 usuario="pessoa-b@exemplo.invalid", senha=SENHA_B).status_code == 200
    # um login nunca em duas contas da mesma corretora
    r = _post(api, "aggers-da-equipe", company_id=a, acao="conectar", dono_user_id=adm_a, por_user_id=adm_a,
              usuario="PESSOA-A@exemplo.invalid", senha=SENHA_A)
    assert r.status_code == 409 and "outra conta" in r.json()["detail"]

    contas = [c for c in amb.banco.linhas("portal_accounts") if c.get("uso") == "membro"]
    assert {(c["company_id"], c["dono_user_id"]) for c in contas} == {(a, ma), (a, outra_a), (b, mb)}
    assert all(c["robo_estado"] == "ativo" and c["robo_janela"] is None for c in contas)

    # o retrato de A: só as pessoas de A, login mascarado, nenhuma senha
    r = api.get("/api/portal/aggers-da-equipe", params={"company_id": a},
                headers={"X-AutoBrokers-Internal-Key": "chave-interna-de-teste"})
    assert r.status_code == 200
    pessoas = {p["user_id"]: p for p in r.json()["pessoas"]}
    assert set(pessoas) == {adm_a, ma, outra_a} and mb not in pessoas
    assert pessoas[ma]["agger"]["situacao"] == "conectado" and "•" in pessoas[ma]["agger"]["usuario"]
    assert pessoas[adm_a]["agger"]["situacao"] == "nao_conectado"

    # a cotação em A de ma → a conta de ma em A; a renovação em B de mb → a conta de mb em B
    pa = next(c["id"] for c in contas if c["dono_user_id"] == ma)
    pb = next(c["id"] for c in contas if c["dono_user_id"] == mb)
    assert QA.decidir(supa(amb), company_id=a, servico="cotacao", solicitante_user_id=ma).conta_id == pa
    assert QA.decidir(supa(amb), company_id=b, servico="renovacao", dono_user_id=mb).conta_id == pb
    assert QA.decidir(supa(amb), company_id=b, servico="cotacao", solicitante_user_id=ma).conta_id is None

    # desligar: a saída da equipe (o DELETE da tela, F1) pausa e apaga a senha SÓ da conta dela, SÓ naquela corretora
    r = _post(api, "aggers-da-equipe/desligar-membro", company_id=b, user_id=ma)
    assert r.status_code == 200 and r.json()["tinha_agger"] is False
    assert TM.conta(amb, pa)["secret_encrypted"]
    r = _post(api, "aggers-da-equipe/desligar-membro", company_id=a, user_id=ma)
    assert r.status_code == 200 and r.json()["desligado"] is True
    assert TM.conta(amb, pa)["secret_encrypted"] is None and TM.conta(amb, pa)["robo_estado"] == "pausado"
    assert TM.conta(amb, pb)["secret_encrypted"] and TM.conta(amb, pb)["robo_estado"] == "ativo"

    # nenhuma senha em resposta, log ou banco (cifrada)
    tudo = json.dumps({t: amb.banco.linhas(t) for t in list(amb.banco.tabelas)}, default=str)
    for s in (SENHA_A, SENHA_B):
        assert s not in tudo and s not in caplog.text and s not in r.text


def test_o_legado_sem_servico_nao_escreve_coluna_nova_e_nunca_usa_agger_de_pessoa(ambiente):
    """`servico=None` (canário, testes): o pedido e os cálculos saem byte a byte como antes — e o motor nunca pega o
    Agger de uma pessoa para eles, nem quando ele é o único."""
    amb = ambiente
    a = TM.empresa(amb)
    ma = membro(amb, a)
    pa = conta_da_pessoa(amb, a, ma)
    aberto = calcular(amb, a, origem="auxiliar")
    pedido = next(p for p in amb.banco.linhas("multicalculo_pedidos") if p["id"] == aberto.pedido_id)
    assert pedido["servico"] is None and pedido["solicitante_user_id"] is None
    [c] = calculos(amb, aberto.pedido_id)
    assert (c["conta_exigida_id"], c["conta_regra"], c["conta_fallback"], c["conta_motivo"]) == (None, None, False,
                                                                                                 None)
    assert TM.rodar(TM.motor(amb, "m1").uma_volta()) == 0 and pa not in obtidas(amb)
    with pytest.raises(ValueError, match="só valem com o serviço"):
        calcular(amb, a, origem="auxiliar", solicitante_user_id=ma)
    with pytest.raises(ValueError, match="sai pela origem"):
        calcular(amb, a, origem="canal", servico="cotacao")


def test_o_recalculo_herda_a_conta_de_origem(ambiente):
    amb = ambiente
    a = TM.empresa(amb)
    conta_global(amb, a)
    ma = membro(amb, a)
    pa = conta_da_pessoa(amb, a, ma)
    aberto = calcular(amb, a, servico="cotacao", solicitante_user_id=ma)
    [c] = calculos(amb, aberto.pedido_id)
    c.update(status="fechado", account_id=pa, negocio_ref="NEG-H", versao=1, fechado_em=TM.T0.isoformat())
    novo = TM.rodar(porta(amb).recalcular(company_id=a, calculo_id=c["id"],
                                          ajuste={"tipo": "franquia", "valor": "reduzida"}))
    aj = next(x for x in amb.banco.linhas("multicalculo_calculos") if x["id"] == novo["id"])
    assert (aj["conta_exigida_id"], aj["conta_regra"]) == (pa, "recalculo_mesma_conta")
    # a pessoa saiu: o recálculo é RECUSADO (o negócio está no Agger dela) — nunca vai para outro login
    next(v for v in amb.banco.linhas("company_members") if v["user_id"] == ma).update(status="inactive")
    with pytest.raises(ContaRecusada, match="saiu da equipe"):
        TM.rodar(porta(amb).recalcular(company_id=a, calculo_id=c["id"],
                                       ajuste={"tipo": "franquia", "valor": "normal"}))
