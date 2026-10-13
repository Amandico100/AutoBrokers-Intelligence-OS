# -*- coding: utf-8 -*-
"""SPEC-131-A · F3 — A MADRUGADA NO AGGER: a porta (prioridade 7, política, item), qual Agger (ausência e desvio), o
motor (Prosseguir 1× por conta por noite, a pessoa que voltou, teto de sessões, a sessão da pessoa mantida, a licença) e a
guarda (a exceção ESTREITA do Prosseguir).

O FIO desta fatia: `porta.calcular(servico='renovacao', prioridade=7, politica_de_sessao='madrugada', renovacao_id=…)` REAL
→ `qual_agger.decidir` REAL → `multicalculo_pedidos/_calculos` → `motor.uma_volta` REAL → a sessão (dublê de BORDA que
obedece à interface de `agger_sessao.Sessoes.obter`, agora com `prosseguir=`) → `multicalculo_eventos`. A guarda e o
leitor da resposta do login são PUROS e testados com as respostas medidas no BLOCO 0 A1 (sem login real).

O banco é o dublê `dubles.banco_multicalculo.BancoU1` + as colunas/tabelas da migration 20261013_01 (F1). Nenhum nome de
corretora nem de pessoa real (CLAUDE.md §13.9): `corretora_a/b`, primeiros nomes fictícios. Nenhum login real.

As mutações da SPEC §6 que esta fatia guarda (cada uma provada VERMELHA uma vez, restauradas por cópia):
    (4) Prosseguir fora da janela ou em conta `global` → `test_m4_*`
    (5) renovação com prioridade 5                     → `test_m5_*`
    (F3) a guarda aceitando `derrubaSessao` diferente do id do aviso → `test_mf3_*`
"""
from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

RAIZ = Path(__file__).resolve().parents[1]
for _p in (str(RAIZ), str(RAIZ / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import dubles_do_work_os as D  # noqa: E402
import test_spec129b_o_motor as TM  # noqa: E402
import test_spec1310_f3_contas as F3  # noqa: E402
from dubles import banco_multicalculo as BM  # noqa: E402
from test_spec129b_o_motor import ambiente  # noqa: E402,F401  (fixture)
from app.services.multicalculo import porta as PORTA  # noqa: E402
from app.services.multicalculo import qual_agger as QA  # noqa: E402
from app.services.multicalculo.pedido import PedidoDeCalculo  # noqa: E402
from portal_worker.multicalculo import agger_guarda as G  # noqa: E402
from portal_worker.multicalculo import agger_sessao as S  # noqa: E402
from portal_worker.multicalculo import motor as MOT  # noqa: E402
from portal_worker.multicalculo import presets as P  # noqa: E402
from portal_worker.multicalculo import robos as ROB  # noqa: E402

BRT = timezone(timedelta(hours=-3))
#: 03:00 de Brasília do dia seguinte ao T0 dos testes do motor (T0 = 10:00 BRT de 06/10) — dentro do Prosseguir
TRES_DA_MANHA = datetime(2026, 10, 7, 3, 0, tzinfo=BRT)
NOITE = "2026-10-07"
TOKEN_DA_OUTRA = "TOKEN-DA-OUTRA-SESSAO-0f9e8d7c"
ID_DO_AVISO = "7339eaec-de01-4c3b-9a1f-000000000001"
API = "https://api-prod.aggilizador.com.br"
RENOV3 = ("anterior", "franquia_reduzida", "completa_mais")


# =====================================================================================================================
# o banco da 131-A (F1): as colunas novas, as tabelas novas e a CHECK de opção alargada
# =====================================================================================================================
@pytest.fixture
def amb(ambiente, monkeypatch):
    TN, UN, U = ("text", True, None), ("uuid", True, None), ("uuid", False, None)
    monkeypatch.setitem(D.ESQUEMA, "multicalculo_pedidos",
                        {**D.ESQUEMA["multicalculo_pedidos"], "politica_de_sessao": TN, "renovacao_id": UN})
    monkeypatch.setitem(D.ESQUEMA, "multicalculo_eventos", {**D.ESQUEMA["multicalculo_eventos"], "motivo": TN})
    monkeypatch.setitem(D.ESQUEMA, "multicalculo_config", {"company_id": U, "config": ("jsonb", True, None)})
    monkeypatch.setitem(D.ESQUEMA, "membro_ausencias", {
        "id": ("uuid", False, "UUID"), "company_id": U, "user_id": U, "substituto_user_id": U, "de": TN, "ate": TN})
    monkeypatch.setitem(D.ESQUEMA, "briefing_profiles", {"id": ("uuid", False, "UUID"), "company_id": U,
                                                         "timezone": TN})
    original = BM.BancoU1._travas

    def travas(self, tabela, nova, velha):
        if tabela == "multicalculo_calculos" and nova.get("opcao") in ("anterior", "franquia_reduzida"):
            nova = {**nova, "opcao": "padrao"}          # a CHECK alargada da 20261013_01 (F1)
        if tabela == "multicalculo_pedidos":
            self._check("ck_mc_pedidos_politica_de_sessao", nova.get("politica_de_sessao") in (None, "madrugada"))
        return original(self, tabela, nova, velha)

    monkeypatch.setattr(BM.BancoU1, "_travas", travas)
    for nome in ("MULTICALCULO_TETO_SESSOES",):
        monkeypatch.delenv(nome, raising=False)
    return ambiente


def na_madrugada(amb, quando: datetime = TRES_DA_MANHA) -> None:
    amb.relogio.avancar((quando - amb.relogio.agora()).total_seconds())


def aceite(amb, corretora: str, *contas: str, **extra) -> None:
    """O ACEITE da madrugada (T-156) por conta — o sinal explícito que liga a política (sem ele, DESLIGADA)."""
    bloco = {"prosseguir_aceites": list(contas), **extra}
    linhas = [x for x in amb.banco.linhas("multicalculo_config") if x["company_id"] == corretora]
    if linhas:
        linhas[0]["config"] = {"servicos": {"renovacao": bloco}}
    else:
        amb.banco.semear("multicalculo_config", {"company_id": corretora, "config": {"servicos": {"renovacao": bloco}}})


def porta(amb, presets=None) -> PORTA.MulticalculoProvider:
    return PORTA.MulticalculoProvider(F3.RepositorioMulticalculo(amb.banco.visao("smith-api")),
                                      ambiente={"MULTICALCULO_HMAC_KEY": F3.CHAVE_HMAC}, agora=amb.relogio.agora,
                                      presets=presets or (lambda o: {"preset": o}))


def renovar(amb, corretora: str, dono: str, *, opcoes=RENOV3, politica="madrugada", **kw):
    return TM.rodar(porta(amb).calcular(company_id=corretora, pedido=PedidoDeCalculo.de_dict(F3.dados_do_pedido()),
                                        opcoes=opcoes, servico="renovacao", dono_user_id=dono,
                                        politica_de_sessao=politica, **kw))


def pedido_linha(amb, pid: str) -> dict:
    return next(p for p in amb.banco.linhas("multicalculo_pedidos") if p["id"] == pid)


def eventos(amb, tipo: str) -> list:
    return [e for e in amb.banco.linhas("multicalculo_eventos") if e.get("tipo") == tipo]


# =====================================================================================================================
# A sessão de BORDA com o Prosseguir (a interface de `agger_sessao.Sessoes.obter`, agora com `prosseguir=`)
# =====================================================================================================================
class SessoesDaMadrugada(TM.SessoesDuble):
    """`aberta_pela_pessoa` = contas em que a dona está logada: sem `prosseguir`, o aviso → SessaoOcupada; com ele, a
    sessão dela é derrubada (por id — o BLOCO 0 A1) e o robô entra. `licencas` = o que o login devolve."""

    def __init__(self, mundo, processo, **kw):
        super().__init__(mundo, processo, **kw)
        mundo.__dict__.setdefault("aberta_pela_pessoa", set())
        mundo.__dict__.setdefault("prosseguir_pedido", [])
        mundo.__dict__.setdefault("logins_criados", [])
        mundo.__dict__.setdefault("licencas", {})

    async def obter(self, conta, *, senha, negocios_do_robo, **kw):
        assert set(kw) <= {"prosseguir"}, kw
        self.m.prosseguir_pedido.append((conta["id"], bool(kw.get("prosseguir"))))
        if conta["id"] not in self._s:
            if conta["id"] in self.m.aberta_pela_pessoa:
                if not kw.get("prosseguir"):
                    self.m.obter.append((self.processo, conta["id"]))
                    raise TM.SessaoOcupada()
                self.m.aberta_pela_pessoa.discard(conta["id"])
                prosseguiu = True
            else:
                prosseguiu = False
            s = await super().obter(conta, senha=senha, negocios_do_robo=negocios_do_robo)
            s.prosseguiu = prosseguiu
            s.licenca = dict(self.m.licencas.get(conta["id"], {}))
            self.m.logins_criados.append(conta["id"])
            return s
        return await super().obter(conta, senha=senha, negocios_do_robo=negocios_do_robo)


def motor(amb, nome: str) -> MOT.Motor:
    visao = amb.banco.visao(nome)

    async def upload(supa, caminho, blob, content_type="application/pdf"):
        return caminho

    return MOT.Motor(visao, sessoes=SessoesDaMadrugada(amb.mundo, nome), robo=TM.RoboDuble(amb.mundo, visao),
                     sessao_mod=TM.SESSAO_MOD, dono=nome, agora=amb.relogio.agora, batida_s=0.02, upload=upload,
                     freio=lambda: False, canario=False)


def calc_do(amb, pedido_id: str) -> list:
    return F3.calculos(amb, pedido_id)


def montar_dono(amb, corretora: str, *, com_aceite: bool = True):
    dono = F3.membro(amb, corretora, nome="Ana")
    conta = F3.conta_da_pessoa(amb, corretora, dono)
    if com_aceite:
        aceite(amb, corretora, conta)
    return dono, conta


# =====================================================================================================================
# 1 · A PORTA — o contrato §5
# =====================================================================================================================
def test_porta_renovacao_sai_com_prioridade_7_a_politica_e_o_item(amb):
    a = TM.empresa(amb)
    F3.conta_global(amb, a)
    dono, conta = montar_dono(amb, a)
    item = str(uuid4())
    aberto = renovar(amb, a, dono, renovacao_id=item)
    ped = pedido_linha(amb, aberto.pedido_id)
    assert (ped["servico"], ped["politica_de_sessao"], ped["renovacao_id"]) == ("renovacao", "madrugada", item)
    calcs = calc_do(amb, aberto.pedido_id)
    assert sorted(c["prioridade"] for c in calcs) == [7, 7, 7]
    assert [c["opcao"] for c in sorted(calcs, key=lambda c: RENOV3.index(c["opcao"]))] == list(RENOV3)
    assert {c["conta_exigida_id"] for c in calcs} == {conta}
    # sem `prioridade=`: a renovação é 7 do mesmo jeito (a prioridade é do SERVIÇO, não de quem chama)
    sem = renovar(amb, a, dono, politica=None)
    assert {c["prioridade"] for c in calc_do(amb, sem.pedido_id)} == {7}
    # CONTROLES: a cotação segue 5 e o canal (QCM) 0 — nada mudou para eles
    cot = TM.rodar(porta(amb).calcular(company_id=a, pedido=PedidoDeCalculo.de_dict(F3.dados_do_pedido()),
                                       opcoes=("padrao",), servico="cotacao", solicitante_user_id=dono))
    assert {c["prioridade"] for c in calc_do(amb, cot.pedido_id)} == {5}
    assert "politica_de_sessao" not in pedido_linha(amb, cot.pedido_id) or \
        pedido_linha(amb, cot.pedido_id)["politica_de_sessao"] is None
    canal = TM.empresa(amb)
    TM._canal_com_adesao(amb, canal, [a])
    qcm = TM.rodar(porta(amb).calcular(company_id=canal, corretoras=[a],
                                       pedido=PedidoDeCalculo.de_dict(F3.dados_do_pedido()),
                                       opcoes=("padrao",), servico="qcm"))
    assert {c["prioridade"] for c in calc_do(amb, qcm.pedido_id)} == {0}


def test_m5_renovacao_nunca_passa_na_frente_da_cotacao(amb):
    """MUTAÇÃO 5 da SPEC: renovação com prioridade 5 → VERMELHO. A porta recusa < 7 e o banco recebe 7."""
    a = TM.empresa(amb)
    F3.conta_global(amb, a)
    dono, _ = montar_dono(amb, a)
    antes = len(amb.banco.linhas("multicalculo_pedidos"))
    for p in (5, 0, 6):
        with pytest.raises(ValueError, match="prioridade"):
            renovar(amb, a, dono, prioridade=p)
    assert len(amb.banco.linhas("multicalculo_pedidos")) == antes, "a recusa gravou um pedido"
    ok = renovar(amb, a, dono, prioridade=7)
    assert {c["prioridade"] for c in calc_do(amb, ok.pedido_id)} == {7}
    assert PORTA.PRIORIDADE_DO_SERVICO["renovacao"] > PORTA.PRIORIDADE["auxiliar"], "a renovação ficou na frente"
    # na FILA do motor a cotação (5) sai antes da renovação (7), mesmo pedida depois
    cot = TM.rodar(porta(amb).calcular(company_id=a, pedido=PedidoDeCalculo.de_dict(F3.dados_do_pedido()),
                                       opcoes=("padrao",), servico="cotacao", solicitante_user_id=dono))
    fila = sorted(amb.banco.linhas("multicalculo_calculos"), key=lambda c: (c["prioridade"], c["criado_em"]))
    assert fila[0]["pedido_id"] == cot.pedido_id


def test_porta_recusas_da_madrugada_e_o_legado_byte_a_byte(amb):
    a = TM.empresa(amb)
    F3.conta_global(amb, a)
    dono, _ = montar_dono(amb, a)
    antes = len(amb.banco.linhas("multicalculo_pedidos"))
    with pytest.raises(ValueError, match="política"):
        renovar(amb, a, dono, politica="sempre")
    with pytest.raises(ValueError, match="só vale na renovação"):
        TM.rodar(porta(amb).calcular(company_id=a, pedido=PedidoDeCalculo.de_dict(F3.dados_do_pedido()),
                                     opcoes=("padrao",), servico="cotacao", solicitante_user_id=dono,
                                     politica_de_sessao="madrugada"))
    # ⛔ econômica e mínima NUNCA numa renovação (a mutação 7 é da F2/F4; a porta recusa também)
    for proibida in ("economica", "minima"):
        with pytest.raises(ValueError, match="proibida"):
            renovar(amb, a, dono, opcoes=("anterior", proibida))
    assert len(amb.banco.linhas("multicalculo_pedidos")) == antes
    # o legado (servico=None) não escreve nenhuma coluna nova
    pid, _ids = TM.pedido(amb, a, [a], opcoes=("padrao",), origem="auxiliar")
    assert "politica_de_sessao" not in {k for k, v in pedido_linha(amb, pid).items() if v is not None}
    leg = TM.rodar(porta(amb).calcular(company_id=a, pedido=PedidoDeCalculo.de_dict(F3.dados_do_pedido()),
                                       opcoes=("padrao",), origem="auxiliar"))
    linha = pedido_linha(amb, leg.pedido_id)
    assert linha.get("politica_de_sessao") is None and linha.get("renovacao_id") is None
    assert {c["prioridade"] for c in calc_do(amb, leg.pedido_id)} == {5}


def test_porta_opcoes_coerentes_com_os_presets(amb):
    """A porta, os presets e a CHECK continuam dizendo o mesmo (OPCOES = ORDEM); a renovação tem a SUA lista."""
    assert PORTA.OPCOES == P.ORDEM and set(P.PRESETS) == set(PORTA.OPCOES)
    assert PORTA.OPCOES_DA_RENOVACAO == P.OPCOES_DA_RENOVACAO == RENOV3
    assert set(PORTA.TODAS_AS_OPCOES) == set(P.ORDEM) | set(RENOV3)
    assert set(PORTA.PROIBIDAS_NA_RENOVACAO) == set(P.PROIBIDAS_NA_RENOVACAO)
    assert MOT._ordem_do_grupo([{"opcao": o} for o in RENOV3])["anterior"] == 0, "o anterior ABRE o negócio"


def test_porta_usa_as_coberturas_que_o_pedido_montou_e_a_opcao_cedida_nao_sai(amb):
    a = TM.empresa(amb)
    F3.conta_global(amb, a)
    dono, _ = montar_dono(amb, a)
    ped = PedidoDeCalculo.de_dict(F3.dados_do_pedido())
    ped = dataclasses.replace(ped, opcoes=("anterior", "completa_mais"),
                              coberturas_por_opcao={"anterior": {"preset": "anterior", "vidros": 2},
                                                    "completa_mais": {"preset": "completa_mais"}})

    def sem_preset(o):
        raise AssertionError(f"usou o preset fixo de {o} no lugar da ficha")

    aberto = TM.rodar(porta(amb, presets=sem_preset).calcular(company_id=a, pedido=ped, opcoes=RENOV3,
                                                              servico="renovacao", dono_user_id=dono))
    calcs = calc_do(amb, aberto.pedido_id)
    assert sorted(c["opcao"] for c in calcs) == ["anterior", "completa_mais"], "a franquia cedida saiu"
    assert next(c for c in calcs if c["opcao"] == "anterior")["coberturas"]["vidros"] == 2


def test_conta_recusada_traduzida_em_status_e_frase(amb):
    """P-1310-04: a recusa vira status + frase (a renovação grava o status; uma rota devolve 409), nunca 500."""
    a = TM.empresa(amb)
    F3.conta_global(amb, a)
    dono, conta = montar_dono(amb, a)
    TM.conta(amb, conta).update(robo_estado="bloqueado")
    with pytest.raises(PORTA.ContaRecusada) as erro:
        renovar(amb, a, dono, vence_em_dias=9)
    d = erro.value.para_dict()
    assert d["status"] == "conta_recusada" and "recusou a senha" in d["frase"] and d["regra"] == "renovacao_recusada"
    assert erro.value.HTTP == 409 and str(erro.value) == d["frase"]


# =====================================================================================================================
# 2 · QUAL AGGER — a ausência (substituto) e o desvio das 06:15, sempre NOMEADOS
# =====================================================================================================================
def test_ausencia_calcula_no_agger_do_dono_e_o_aviso_nomeia_o_substituto(amb):
    a, b = TM.empresa(amb), TM.empresa(amb)
    F3.conta_global(amb, a)
    dono, conta = montar_dono(amb, a)
    sub = F3.membro(amb, a, nome="Bia")
    hoje = date(2026, 10, 7)
    amb.banco.semear("membro_ausencias", {"company_id": a, "user_id": dono, "substituto_user_id": sub,
                                          "de": "2026-10-01", "ate": "2026-10-10"})
    supa = amb.banco.visao("x")
    d = QA.decidir(supa, company_id=a, servico="renovacao", dono_user_id=dono, hoje=hoje)
    assert (d.conta_id, d.regra, d.fallback) == (conta, "renovacao_do_dono", False), "a ausência trocou o Agger"
    assert d.avisar_user_id == sub and "Bia" in d.aviso and "Ana" in d.aviso, d.aviso
    # CONTROLE: a ausência acabou ontem → nenhum aviso, nenhum substituto
    d2 = QA.decidir(supa, company_id=a, servico="renovacao", dono_user_id=dono, hoje=date(2026, 10, 11))
    assert d2.avisar_user_id is None and not d2.aviso
    # ISOLAMENTO: a mesma pessoa ausente na corretora B não muda nada na A
    F3.vincular(amb, b, dono)
    sub_b = F3.membro(amb, b, nome="Cris")
    amb.banco.semear("membro_ausencias", {"company_id": b, "user_id": dono, "substituto_user_id": sub_b,
                                          "de": "2026-10-11", "ate": "2026-10-20"})
    d3 = QA.decidir(supa, company_id=a, servico="renovacao", dono_user_id=dono, hoje=date(2026, 10, 12))
    assert d3.avisar_user_id is None and "Cris" not in (d3.aviso or "")
    # o substituto passado por quem já leu vale igual; numa cotação, recusado
    d4 = QA.decidir(supa, company_id=a, servico="renovacao", dono_user_id=dono, substituto_user_id=sub,
                    hoje=date(2026, 10, 20))
    assert d4.avisar_user_id == sub
    with pytest.raises(ValueError):
        QA.decidir(supa, company_id=a, servico="cotacao", solicitante_user_id=dono, substituto_user_id=sub)


def test_desvio_das_0615_vai_para_a_corretora_com_aviso_nomeado(amb):
    a = TM.empresa(amb)
    F3.conta_global(amb, a)
    dono, conta = montar_dono(amb, a)
    supa = amb.banco.visao("x")
    d = QA.decidir(supa, company_id=a, servico="renovacao", dono_user_id=dono,
                   forcar_corretora_motivo="renovacao_desvio_0615")
    assert (d.conta_id, d.fallback, d.recusa) == (None, True, None) and d.regra == "renovacao_desvio_da_corretora"
    assert "Ana" in d.motivo and "Agger da corretora" in d.motivo and "CORRETORA" in d.aviso, (d.motivo, d.aviso)
    with pytest.raises(ValueError, match="motivo"):
        QA.decidir(supa, company_id=a, servico="renovacao", dono_user_id=dono, forcar_corretora_motivo=" ")
    with pytest.raises(ValueError):
        QA.decidir(supa, company_id=a, servico="cotacao", forcar_corretora_motivo="x")
    # pela PORTA (o caminho da madrugada F1): o cálculo NÃO exige a conta da pessoa e o porquê fica no banco
    aberto = renovar(amb, a, dono, politica=None, forcar_corretora_motivo="renovacao_desvio_0615")
    for c in calc_do(amb, aberto.pedido_id):
        assert c["conta_exigida_id"] is None and c["conta_fallback"] is True and "Ana" in c["conta_motivo"]
        assert c["prioridade"] == 7
    with pytest.raises(ValueError):          # o desvio não leva a política da madrugada (nunca Prosseguir nele)
        renovar(amb, a, dono, forcar_corretora_motivo="renovacao_desvio_0615")


# =====================================================================================================================
# 3 · A GUARDA — a exceção ESTREITA do Prosseguir (pura)
# =====================================================================================================================
def _estado(**kw) -> G.EstadoDaGuarda:
    e = G.EstadoDaGuarda(host_api="api-prod.aggilizador.com.br", **kw)
    return e


def _prosseguir(alvo=ID_DO_AVISO, **extra) -> str:
    return json.dumps({"email": "x@exemplo.invalid", "senha": "s", "derrubaSessao": alvo, **extra})


def test_guarda_sem_a_politica_barra_o_prosseguir_como_sempre():
    e = _estado()
    e.registrar_sessao_ativa(ID_DO_AVISO)              # sem a política, nada é guardado
    e.logins = 1
    assert e.sessao_ativa_id == ""
    assert G.decidir("POST", API + "/usuario/login", _prosseguir(), e) == (False, "derruba_sessao")
    assert G.decidir("POST", API + "/usuario/login", '{"email":"x","senha":"y"}', e) == (False, "segundo_login")


def test_guarda_com_a_politica_libera_so_o_post_que_derruba_a_sessao_do_aviso():
    e = _estado(prosseguir_permitido=True)
    assert G.decidir("POST", API + "/usuario/login", '{"email":"x","senha":"y"}', e) == (True, "login")
    e.logins = 1
    # antes de a resposta do aviso chegar, não há alvo: barra
    assert G.decidir("POST", API + "/usuario/login", _prosseguir(), e)[0] is False
    e.registrar_sessao_ativa(ID_DO_AVISO.upper())
    e.registrar_sessao_ativa("outro-id-que-chegou-depois")      # só o 1º vale
    assert G.decidir("POST", API + "/usuario/login", _prosseguir(), e) == (True, "prosseguir")
    assert G.decidir("POST", API + "/usuario/login", _prosseguir(forcarLogin=True), e)[0] is False   # chave a mais
    e.prosseguiu = 1
    assert G.decidir("POST", API + "/usuario/login", _prosseguir(), e)[0] is False, "2º Prosseguir no contexto"


def test_mf3_a_guarda_recusa_derrubar_outra_sessao_que_nao_a_do_aviso():
    """MUTAÇÃO da F3: a guarda aceitando `derrubaSessao` diferente do `data.id` do aviso → VERMELHO."""
    e = _estado(prosseguir_permitido=True)
    e.logins = 1
    e.registrar_sessao_ativa(ID_DO_AVISO)
    for alvo in ("7339eaec-de01-4c3b-9a1f-000000000002", "", "*", ID_DO_AVISO + "0"):
        assert G.decidir("POST", API + "/usuario/login", _prosseguir(alvo), e) == (False, "derruba_sessao"), alvo
    assert G.decidir("POST", API + "/usuario/login", json.dumps({"email": "x", "senha": "s",
                                                                 "derrubaSessao": 123}), e)[0] is False
    assert G.decidir("POST", API + "/usuario/login", _prosseguir(), e) == (True, "prosseguir")   # CONTROLE


def test_a_resposta_do_login_so_entrega_o_id_do_aviso_e_as_datas_da_licenca():
    """🔴 BLOCO 0 A1: a resposta "Já existe uma sessão ativa" traz `data.token` = o token da OUTRA sessão. Só o `data.id`
    sai do leitor; da resposta de sucesso, só as datas/números da licença."""
    aviso = {"message": "Já existe uma sessão ativa com esse usuário.",
             "data": {"id": ID_DO_AVISO, "token": TOKEN_DA_OUTRA, "usuarioId": "u-1", "status": True}}
    assert S.id_da_sessao_ativa(aviso) == ID_DO_AVISO
    assert S.id_da_sessao_ativa({"message": "ok", "data": {"id": "x"}}) is None            # CONTROLE
    ok = {"token": "TOKEN-NOVO-1", "idSessao": "s-2", "usuario": {"email": "x@exemplo.invalid",
                                                                    "licenca": "2026-10-20T00:00:00.000Z",
                                                                    "dataLimiteCalculo": "2026-10-27",
                                                                    "diasParaExpirarSenha": 115,
                                                                    "senha": "SEGREDO-1"}}
    lic = S.extrair_licenca(ok)
    assert lic == {"licenca": "2026-10-20", "dataLimiteCalculo": "2026-10-27", "diasParaExpirarSenha": 115}
    assert TOKEN_DA_OUTRA not in json.dumps(S.extrair_licenca(aviso)) and "TOKEN" not in json.dumps(lic)


# =====================================================================================================================
# 4 · O MOTOR — o Prosseguir 1× por conta por noite, a pessoa que voltou, de hora em hora até o desvio
# =====================================================================================================================
def test_madrugada_prossegue_uma_vez_e_depois_espera_de_hora_em_hora_ate_o_desvio(amb, caplog):
    caplog.set_level(logging.DEBUG)
    a = TM.empresa(amb)
    g = F3.conta_global(amb, a)
    dono, conta = montar_dono(amb, a)
    na_madrugada(amb)
    amb.mundo.aberta_pela_pessoa = {conta}                         # a sessão esquecida da dona (a fantasma de horas)
    p1 = renovar(amb, a, dono)
    TM.rodar(motor(amb, "m1").uma_volta())
    assert (conta, True) in amb.mundo.prosseguir_pedido, "não prosseguiu dentro de todas as travas"
    assert {c["status"] for c in calc_do(amb, p1.pedido_id)} == {"fechado"}
    [ev] = eventos(amb, MOT.TIPO_PROSSEGUIU)
    assert ev["chave"] == f"{MOT.TIPO_PROSSEGUIU}|{conta}|{NOITE}" and ev["company_id"] == a
    assert g not in {cid for (_p, cid) in amb.mundo.obter}, "caiu no Agger da corretora"

    # a dona VOLTOU (03:20): o 2º pedido da noite NÃO prossegue de novo — cancela e espera 1 h, sem falhar
    amb.relogio.avancar(20 * 60)
    amb.mundo.aberta_pela_pessoa = {conta}
    p2 = renovar(amb, a, dono)
    TM.rodar(motor(amb, "m2").uma_volta())
    assert amb.mundo.prosseguir_pedido[-1] == (conta, False)
    calcs = calc_do(amb, p2.pedido_id)
    assert {c["status"] for c in calcs} == {"na_fila"}, "a volta da dona virou falha"
    agora = amb.relogio.agora()
    assert {c["disponivel_em"] for c in calcs} == {(agora + timedelta(minutes=60)).isoformat()}
    assert len(eventos(amb, MOT.TIPO_PROSSEGUIU)) == 1, "prosseguiu 2× na mesma noite"
    assert eventos(amb, MOT.TIPO_PESSOA_EM_USO), "o item não fica `aguardando_agger` (F1 lê este evento)"
    # de hora em hora: 04:20 e 05:20 continuam esperando; a das 05:20 cairia às 06:20 > 06:15 → falha PASSAGEIRA agora
    for vez in range(3):
        amb.relogio.avancar(60 * 60 + 1)
        TM.rodar(motor(amb, f"m3{vez}").uma_volta())
    calcs = calc_do(amb, p2.pedido_id)
    assert {c["status"] for c in calcs} == {"falhou"}, [c["status"] for c in calcs]
    assert all(c["erro"].startswith("agger_da_pessoa_em_uso") for c in calcs), "o desvio das 06:15 não reconhece"
    assert len(eventos(amb, MOT.TIPO_PROSSEGUIU)) == 1 and amb.mundo.posts and \
        all(cid == conta for (cid, *_r) in amb.mundo.posts)
    # ⛔ nenhum token / corpo de login em log nem em evento
    texto = repr([r.getMessage() for r in caplog.records]) + repr(amb.banco.linhas("multicalculo_eventos"))
    assert "TOKEN" not in texto and F3.SENHA_A not in texto


def test_m4_fora_da_janela_nao_prossegue(amb):
    """MUTAÇÃO 4 da SPEC (a janela): às 10:00 o mesmo pedido da madrugada NÃO prossegue → como hoje (Cancelar)."""
    a = TM.empresa(amb)
    F3.conta_global(amb, a)
    dono, conta = montar_dono(amb, a)
    amb.mundo.__dict__["aberta_pela_pessoa"] = {conta}
    p = renovar(amb, a, dono)                      # T0 = 10:00 de Brasília
    TM.rodar(motor(amb, "m1").uma_volta())
    assert amb.mundo.prosseguir_pedido == [(conta, False)]
    assert eventos(amb, MOT.TIPO_PROSSEGUIU) == []
    assert TM.conta(amb, conta)["robo_estado"] == "ocupada"
    assert {c["status"] for c in calc_do(amb, p.pedido_id)} == {"na_fila"}
    # e às 06:30 em ponto a janela já fechou (06:29 ainda abre — CONTROLE pela função pura)
    janela = MOT.janela_da_madrugada(None)
    assert MOT.dentro_do_prosseguir(datetime(2026, 10, 7, 6, 29, tzinfo=BRT), janela, BRT)
    assert not MOT.dentro_do_prosseguir(datetime(2026, 10, 7, 6, 30, tzinfo=BRT), janela, BRT)
    assert not MOT.dentro_do_prosseguir(datetime(2026, 10, 7, 0, 59, tzinfo=BRT), janela, BRT)


def test_m4_conta_da_corretora_nunca_prossegue(amb):
    """MUTAÇÃO 4 da SPEC (a conta): dono sem Agger próprio → a renovação vai pelo Agger da CORRETORA, e nele NUNCA se
    prossegue — nem com a política, nem na janela, nem com o "aceite" escrito para ela."""
    a = TM.empresa(amb)
    g = F3.conta_global(amb, a)
    dono = F3.membro(amb, a, nome="Ana")
    aceite(amb, a, g)
    na_madrugada(amb)
    amb.mundo.__dict__["aberta_pela_pessoa"] = {g}
    p = renovar(amb, a, dono)
    assert {c["conta_exigida_id"] for c in calc_do(amb, p.pedido_id)} == {None}
    TM.rodar(motor(amb, "m1").uma_volta())
    assert amb.mundo.prosseguir_pedido == [(g, False)], "prosseguiu no Agger da corretora"
    assert eventos(amb, MOT.TIPO_PROSSEGUIU) == []
    # a trava do USO sozinha: mesmo com um grupo FORJADO que exige a conta da corretora pela regra do dono, não prossegue
    forjado = MOT.Grupo(str(uuid4()), a, a, [{"id": "c1", "conta_exigida_id": g, "conta_regra": MOT.REGRA_DO_DONO}],
                        "auxiliar", servico="renovacao", politica=MOT.POLITICA_MADRUGADA)
    for uso, estado in (("global", "ativo"), ("teste", "ativo"), ("membro", "teste")):
        conta_forjada = {**TM.conta(amb, g), "uso": uso, "robo_estado": estado, "dono_user_id": dono}
        ok, porque = TM.rodar(motor(amb, "m9")._pode_prosseguir(forjado, conta_forjada))
        assert not ok and "pessoa" in porque, (uso, estado, porque)
    # CONTROLE: a mesma forja como `membro` ativo passa por todas as travas (a do uso é a que segura acima)
    ok, _ = TM.rodar(motor(amb, "m9")._pode_prosseguir(forjado, {**TM.conta(amb, g), "uso": "membro",
                                                                   "dono_user_id": dono}))
    assert ok


def test_sem_o_aceite_a_politica_fica_desligada(amb):
    a = TM.empresa(amb)
    F3.conta_global(amb, a)
    dono, conta = montar_dono(amb, a, com_aceite=False)
    na_madrugada(amb)
    amb.mundo.__dict__["aberta_pela_pessoa"] = {conta}
    renovar(amb, a, dono)
    TM.rodar(motor(amb, "m1").uma_volta())
    assert amb.mundo.prosseguir_pedido == [(conta, False)]
    # CONTROLE: com o aceite, a mesma conta prossegue
    aceite(amb, a, conta)
    amb.relogio.avancar(31 * 60)
    TM.rodar(motor(amb, "m2").uma_volta())
    assert amb.mundo.prosseguir_pedido[-1] == (conta, True)


def test_cotacao_nunca_prossegue_nem_de_madrugada(amb):
    a = TM.empresa(amb)
    F3.conta_global(amb, a)
    dono, conta = montar_dono(amb, a)
    na_madrugada(amb)
    amb.mundo.__dict__["aberta_pela_pessoa"] = {conta}
    TM.rodar(porta(amb).calcular(company_id=a, pedido=PedidoDeCalculo.de_dict(F3.dados_do_pedido()),
                                 opcoes=("padrao",), servico="cotacao", solicitante_user_id=dono))
    TM.rodar(motor(amb, "m1").uma_volta())
    assert amb.mundo.prosseguir_pedido == [(conta, False)]


# =====================================================================================================================
# 5 · A FILA — teto de sessões (processo e corretora) e a sessão da pessoa mantida de madrugada
# =====================================================================================================================
def test_teto_de_sessoes_do_processo_o_excedente_espera_sem_falhar(amb, monkeypatch):
    monkeypatch.setenv("MULTICALCULO_TETO_SESSOES", "1")
    a, b = TM.empresa(amb), TM.empresa(amb)
    ga, gb = F3.conta_global(amb, a), F3.conta_global(amb, b)
    pa, _ = TM.pedido(amb, a, [a], opcoes=("padrao",), origem="auxiliar", expira_min=120)
    pb, _ = TM.pedido(amb, b, [b], opcoes=("padrao",), origem="auxiliar", expira_min=120)
    m = motor(amb, "m1")
    assert TM.rodar(m.uma_volta()) == 1, "abriu duas sessões com teto 1"
    estados = {pid: {c["status"] for c in calc_do(amb, pid)} for pid in (pa, pb)}
    assert sorted(map(sorted, estados.values())) == [["fechado"], ["na_fila"]], estados
    assert TM.rodar(m.uma_volta()) == 1                 # a ociosa da 1ª é fechada para dar a vaga
    assert {c["status"] for pid in (pa, pb) for c in calc_do(amb, pid)} == {"fechado"}
    assert len(m._contas_com_sessao) <= 1
    # CONTROLE: com o padrão (6) as duas saem na mesma volta
    monkeypatch.delenv("MULTICALCULO_TETO_SESSOES")
    c, d = TM.empresa(amb), TM.empresa(amb)
    F3.conta_global(amb, c), F3.conta_global(amb, d)
    TM.pedido(amb, c, [c], opcoes=("padrao",), origem="auxiliar", expira_min=120)
    TM.pedido(amb, d, [d], opcoes=("padrao",), origem="auxiliar", expira_min=120)
    assert TM.rodar(motor(amb, "m9").uma_volta()) == 2


def test_teto_por_corretora_na_renovacao_e_a_prioridade(amb):
    a = TM.empresa(amb)
    F3.conta_global(amb, a)
    ana, conta_ana = montar_dono(amb, a)
    bia = F3.membro(amb, a, nome="Bia")
    conta_bia = F3.conta_da_pessoa(amb, a, bia)
    aceite(amb, a, conta_ana, conta_bia)
    na_madrugada(amb)
    r1 = renovar(amb, a, ana)
    r2 = renovar(amb, a, bia)
    m = motor(amb, "m1")
    assert TM.rodar(m.uma_volta()) == 1, "duas sessões da MESMA corretora na renovação (teto 1)"
    assert TM.rodar(m.uma_volta()) == 1
    assert {c["status"] for pid in (r1.pedido_id, r2.pedido_id) for c in calc_do(amb, pid)} == {"fechado"}
    # CONTROLE: o teto da corretora vem da config (2 → as duas juntas)
    b = TM.empresa(amb)
    F3.conta_global(amb, b)
    x = F3.membro(amb, b, nome="Ciro")
    y = F3.membro(amb, b, nome="Duda")
    cx, cy = F3.conta_da_pessoa(amb, b, x), F3.conta_da_pessoa(amb, b, y)
    aceite(amb, b, cx, cy, teto_sessoes_corretora=2)
    renovar(amb, b, x)
    renovar(amb, b, y)
    assert TM.rodar(motor(amb, "m2").uma_volta()) == 2


def test_a_sessao_da_pessoa_fica_aberta_entre_os_pedidos_dela_de_madrugada(amb):
    a = TM.empresa(amb)
    F3.conta_global(amb, a)
    dono, conta = montar_dono(amb, a)
    na_madrugada(amb)
    p1, p2 = renovar(amb, a, dono), renovar(amb, a, dono)
    m = motor(amb, "m1")
    TM.rodar(m.uma_volta())
    assert amb.mundo.abertas.get(conta) == {"m1"}, "fez logout com mais pedido dela na fila"
    assert m._ociosas[conta].get("madrugada") is True
    TM.rodar(m.uma_volta())
    assert {c["status"] for pid in (p1.pedido_id, p2.pedido_id) for c in calc_do(amb, pid)} == {"fechado"}
    assert amb.mundo.logins_criados.count(conta) == 1, "um login por pedido (a sessão não foi mantida)"
    TM.rodar(m.uma_volta())                             # o fim da fila dela: logout
    assert amb.mundo.abertas.get(conta) == set() and conta not in m._ociosas
    assert TM.conta(amb, conta)["robo_dono"] is None
    # CONTROLE: de DIA (sem a madrugada) é logout por pedido, como sempre
    b = TM.empresa(amb)
    F3.conta_global(amb, b)
    db_, cb = montar_dono(amb, b)
    amb.relogio.avancar(7 * 3600)                       # 10:00
    renovar(amb, b, db_, politica=None), renovar(amb, b, db_, politica=None)
    m2 = motor(amb, "m2")
    TM.rodar(m2.uma_volta())
    TM.rodar(m2.uma_volta())
    assert amb.mundo.logins_criados.count(cb) == 2 and amb.mundo.abertas.get(cb) == set()


def test_a_sessao_mantida_sai_as_0630(amb):
    a = TM.empresa(amb)
    F3.conta_global(amb, a)
    dono, conta = montar_dono(amb, a)
    na_madrugada(amb, datetime(2026, 10, 7, 6, 28, tzinfo=BRT))
    renovar(amb, a, dono), renovar(amb, a, dono)
    m = motor(amb, "m1")
    TM.rodar(m.uma_volta())
    assert conta in m._ociosas
    amb.relogio.avancar(3 * 60)                         # 06:31
    m._cfg_da_madrugada.clear()
    TM.rodar(m._cuidar_das_ociosas())
    assert conta not in m._ociosas and amb.mundo.abertas.get(conta) == set(), "segurou a sessão da pessoa depois das 06:30"


# =====================================================================================================================
# 6 · A LICENÇA do Agger — um evento por conta por dia, só datas; vencida → falha com o motivo
# =====================================================================================================================
def test_licenca_vira_um_evento_por_dia_sem_token_e_vencida_falha(amb, caplog):
    caplog.set_level(logging.DEBUG)
    a = TM.empresa(amb)
    g = F3.conta_global(amb, a)
    amb.mundo.__dict__.setdefault("licencas", {})[g] = {
        "licenca": "2026-10-20", "dataLimiteCalculo": "2026-10-27", "diasParaExpirarSenha": 115,
        "token": TOKEN_DA_OUTRA, "email": "x@exemplo.invalid"}
    pid, _ = TM.pedido(amb, a, [a], opcoes=("padrao",), origem="auxiliar", expira_min=600)
    m = motor(amb, "m1")
    TM.rodar(m.uma_volta())
    [ev] = eventos(amb, MOT.TIPO_LICENCA)
    assert ev["chave"] == f"{MOT.TIPO_LICENCA}|{g}|2026-10-06"
    assert "dataLimiteCalculo=2026-10-27" in ev["motivo"] and "diasParaExpirarSenha=115" in ev["motivo"]
    assert TOKEN_DA_OUTRA not in json.dumps(amb.banco.linhas("multicalculo_eventos"), default=str)
    assert TOKEN_DA_OUTRA not in repr([r.getMessage() for r in caplog.records])
    assert {c["status"] for c in calc_do(amb, pid)} == {"fechado"}
    # 2º login no MESMO dia: nenhum evento a mais
    TM.rodar(m.desligar())
    TM.pedido(amb, a, [a], opcoes=("padrao",), origem="auxiliar", expira_min=600)
    TM.rodar(motor(amb, "m2").uma_volta())
    assert len(eventos(amb, MOT.TIPO_LICENCA)) == 1
    # vencida (o limite é HOJE: ≤ 0 dia) → o cálculo FALHA com o motivo, nada sai
    b = TM.empresa(amb)
    gb = F3.conta_global(amb, b)
    amb.mundo.licencas[gb] = {"licenca": "2026-09-30", "dataLimiteCalculo": "2026-10-06"}
    posts = len(amb.mundo.posts)
    pb, _ = TM.pedido(amb, b, [b], opcoes=("padrao",), origem="auxiliar", expira_min=600)
    TM.rodar(motor(amb, "m3").uma_volta())
    [cb] = calc_do(amb, pb)
    assert cb["status"] == "falhou" and cb["erro"].startswith("licenca_agger_vencida"), cb
    assert len(amb.mundo.posts) == posts, "calculou com a licença vencida"


# =====================================================================================================================
# 7 · A SESSÃO REAL (Chromium + Agger dublê): o Prosseguir pela tela, a guarda e a REDAÇÃO do corpo do login
# =====================================================================================================================
HTML_LOGIN_A1 = """<!doctype html><html><head><meta charset="utf-8"><title>Agger dublê A1</title></head><body>
<form onsubmit="return false"><input type="email" id="e"><input type="password" id="s">
<button type="button" id="entrar">Entrar</button></form><div id="msg"></div>
<div id="aviso" role="dialog" style="display:none"><p>Caro usuário do Aggilizador, identificamos que já há uma sessão
ativa com este mesmo usuário. Deseja encerrá-la e prosseguir com o login?</p>
<button type="button" id="cancelar">Cancelar</button><button type="button" id="prosseguir">Prosseguir</button></div>
<script>
const API = location.protocol + '//api-prod.' + location.host;
let idDaSessao = null;
async function entrar(derruba) {
  const corpo = {email: document.getElementById('e').value, senha: document.getElementById('s').value};
  if (derruba) corpo.derrubaSessao = derruba;
  const r = await fetch(API + '/usuario/login', {method: 'POST', headers: {'Content-Type': 'application/json'},
                                                  body: JSON.stringify(corpo)}).catch(() => null);
  if (!r) { document.getElementById('msg').innerText = 'falha de rede'; return; }
  const d = await r.json().catch(() => ({}));
  if (r.status >= 400) { document.getElementById('msg').innerText = 'Login ou senha inválidos'; return; }
  if (d.message && d.data) { idDaSessao = d.data.id; document.getElementById('aviso').style.display = 'block'; return; }
  const p = await fetch(API + '/usuario/login/pdocs', {method: 'POST', headers: {Authorization: d.token}});
  const dp = await p.json();
  sessionStorage.setItem('tApi', d.token); sessionStorage.setItem('tPdocs', dp.token);
  location.href = '/cotacoes';
}
document.getElementById('entrar').onclick = () => entrar(null);
document.getElementById('prosseguir').onclick = () => { document.getElementById('aviso').style.display = 'none';
                                                       entrar(window.__alvo || idDaSessao); };
document.getElementById('cancelar').onclick = () => { document.getElementById('aviso').style.display = 'none'; };
</script></body></html>"""


def _agger_a1():
    from aiohttp import web
    from dubles.agger_duble import EMAIL, SENHA, AggerDuble, HTML_COTACOES

    class AggerA1(AggerDuble):
        """O login MEDIDO no BLOCO 0 A1: 1ª tentativa 201 "Já existe…" com `data.id` e `data.token` (o da OUTRA sessão);
        o Prosseguir reenvia `{email, senha, derrubaSessao}`; o sucesso devolve a licença."""

        def __init__(self):
            super().__init__(modo_login="sessao_ativa")
            self.derrubadas = []

        async def _tratar(self, req):
            host = (req.host or "").split(":")[0]
            if host == "agg.localhost" and req.path == "/login":
                return web.Response(text=HTML_LOGIN_A1, content_type="text/html")
            if host == "agg.localhost" and req.path == "/cotacoes":
                return web.Response(text=HTML_COTACOES, content_type="text/html")
            return await super()._tratar(req)

        async def _api(self, req, caminho):
            if caminho == "/usuario/login" and req.method == "POST":
                d = await req.json()
                self.logins.append({"forcar": "derrubaSessao" in d})
                if d.get("email") != EMAIL or d.get("senha") != SENHA:
                    return self._json(req, {"message": "Login ou senha inválidos"}, 401)
                if "derrubaSessao" not in d:
                    return self._json(req, {"message": "Já existe uma sessão ativa com esse usuário.",
                                            "data": {"id": ID_DO_AVISO, "token": TOKEN_DA_OUTRA, "usuarioId": "u-1",
                                                     "status": True, "dispositivo": None}, "assinaturaId": 9}, 201)
                self.derrubadas.append(d["derrubaSessao"])
                return self._json(req, {"token": "TOKEN-API-NOVO", "idSessao": "sessao-2",
                                        "usuario": {"licenca": "2026-10-20", "dataLimiteCalculo": "2026-10-27",
                                                    "diasParaExpirarSenha": 115}}, 201)
            return await super()._api(req, caminho)

    return AggerA1


def _com_agger_a1(fn):
    pw_api = pytest.importorskip("playwright.async_api")

    async def tudo():
        d = await _agger_a1()().iniciar()
        try:
            async with pw_api.async_playwright() as pw:
                nav = await pw.chromium.launch(headless=True)
                try:
                    return await fn(d, S.Sessoes(nav, url_base=d.base))
                finally:
                    await nav.close()
        finally:
            await d.parar()

    return asyncio.run(tudo())


def test_sessao_real_prossegue_so_com_a_politica_e_nunca_grava_o_token_da_outra_sessao(caplog):
    caplog.set_level(logging.DEBUG)
    from dubles.agger_duble import EMAIL, SENHA

    pessoa = {"id": "conta-da-pessoa-1", "username": EMAIL, "robo_estado": "ativo", "uso": "membro"}

    async def corpo(d, sessoes):
        # sem a política: o aviso → Cancelar (como sempre); 1 login, nenhum derrubaSessao
        with pytest.raises(S.SessaoOcupada):
            await sessoes.obter(pessoa, senha=SENHA, negocios_do_robo=set())
        assert d.logins == [{"forcar": False}] and d.derrubadas == []
        # a conta da CORRETORA com prosseguir=True: a sessão ignora o pedido (nunca prossegue)
        with pytest.raises(S.SessaoOcupada):
            await sessoes.obter({**pessoa, "id": "conta-global", "uso": "global"}, senha=SENHA,
                                negocios_do_robo=set(), prosseguir=True)
        assert d.derrubadas == []
        # a política da madrugada: Prosseguir pela tela, a guarda deixa passar SÓ o POST com o id do aviso
        s = await sessoes.obter(pessoa, senha=SENHA, negocios_do_robo=set(), prosseguir=True)
        assert d.derrubadas == [ID_DO_AVISO] and s.prosseguiu is True
        assert s.estado_da_guarda.prosseguiu == 1 and s.contagem_de_escritas()["prosseguir"] == 1
        assert s.licenca == {"licenca": "2026-10-20", "dataLimiteCalculo": "2026-10-27", "diasParaExpirarSenha": 115}
        assert TOKEN_DA_OUTRA not in (s._tokens.get("api"), s._tokens.get("pdocs"))
        await sessoes.fechar(pessoa["id"])
        return s

    _com_agger_a1(corpo)
    assert TOKEN_DA_OUTRA not in repr([r.getMessage() for r in caplog.records] + [repr(r.args) for r in caplog.records])
