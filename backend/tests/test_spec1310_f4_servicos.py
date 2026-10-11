# -*- coding: utf-8 -*-
"""SPEC-131-0 parte A · F4 — o manual de CADA serviço (D-131-0-07/08/10/12).

O Founder (10/10): *"o manual de regras para renovação, como pensar, como cotar, deve ser diferente de Quem Cobra Menos
e da cotação… se eu falar que é para todas a mesma regra, aí ajusta em tudo"* · *"a corretora deve poder escolher se
quer que o agente faça só o cálculo… ou ligar a negociação… etapas separadas dentro do mesmo serviço"*.

O que se prova aqui, sempre pelo MOTOR (CLAUDE.md §9.4 — `config.carregar`/`mesclar`, a proposta real, o router real):
  · a SEPARAÇÃO: mudar `servicos.renovacao` não muda o que o QCM lê; mudar `servicos.qcm` muda — no `carregar` E no
    HTML servido da proposta do canal (o caminho da proposta, §5.3)
  · o modo e as exceções (a mais contida vence) · o reajuste número OU mapa
  · o PUT grava SÓ `servicos.*` + preferências, recusa chave fora da lista, nunca toca outra corretora
  · a prontidão dos 4 passos com DUAS corretoras (§7), só leitura
⛔ Nomes fictícios (§13.9): corretora_a/corretora_b, membro_a/membro_b. Senha nenhuma.
"""
from __future__ import annotations

import asyncio
import copy
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from app.services.multicalculo import config as CFG  # noqa: E402
from app.services.multicalculo.config import PADRAO_DO_PRODUTO, carregar, mesclar  # noqa: E402

A = "a1310000-0000-4000-8000-00000000000a"     # corretora_a
B = "b1310000-0000-4000-8000-00000000000b"     # corretora_b
CANAL = "c1310000-0000-4000-8000-0000000000ca"
MEMBRO_A1 = "a1310000-0000-4000-8000-0000000000a1"
MEMBRO_A2 = "a1310000-0000-4000-8000-0000000000a2"
MEMBRO_B1 = "b1310000-0000-4000-8000-0000000000b1"


# =====================================================================================================================
# o banco dublê — PostgREST mínimo: select/eq/not_.is_/limit/upsert, com o registro do filtro pedido
# =====================================================================================================================
class _Resp:
    def __init__(self, data):
        self.data = data


class _Consulta:
    def __init__(self, banco, tabela):
        self.banco, self.tabela, self.filtros, self.nao_nulos, self.lim = banco, tabela, [], [], None
        self.colunas, self._upsert, self._insert, self._update = None, None, None, None

    @property
    def not_(self):
        return self

    def is_(self, coluna, valor):
        assert valor == "null"
        self.nao_nulos.append(coluna)
        return self

    def select(self, colunas="*"):
        self.colunas = colunas
        faltam = self.banco.colunas_ausentes.get(self.tabela, set())
        if any(c.strip() in faltam for c in colunas.split(",")):
            raise RuntimeError(f"column {self.tabela}.x does not exist")
        if self.tabela in self.banco.tabelas_ausentes:
            raise RuntimeError(f"relation {self.tabela} does not exist")
        return self

    def eq(self, coluna, valor):
        if coluna in self.banco.colunas_ausentes.get(self.tabela, set()):
            raise RuntimeError(f"column {self.tabela}.{coluna} does not exist")
        self.filtros.append((coluna, valor))
        return self

    def limit(self, n):
        self.lim = n
        return self

    def upsert(self, linha, on_conflict=None):
        self._upsert = (dict(linha), on_conflict)
        return self

    def insert(self, linha):
        self._insert = dict(linha)
        return self

    def update(self, patch):
        self._update = dict(patch)
        return self

    def execute(self):
        if self.banco.quebrado:
            raise RuntimeError("banco fora")
        linhas = self.banco.tabelas.setdefault(self.tabela, [])
        if self._insert is not None:     # a chave primária company_id: duplicada → o erro do Postgres (23505)
            nova = self._insert
            if any(l.get("company_id") == nova.get("company_id") for l in linhas):
                raise RuntimeError("23505 duplicate key value violates unique constraint")
            self.banco.escritas.append((self.tabela, copy.deepcopy(nova)))
            linhas.append(copy.deepcopy(nova))
            return _Resp([nova])
        if self._update is not None:     # só as linhas que casam TODOS os filtros (o CAS do atualizado_em)
            alvo = [l for l in linhas if all(l.get(c) == v for c, v in self.filtros)]
            for l in alvo:
                l.update(copy.deepcopy(self._update))
                self.banco.escritas.append((self.tabela, copy.deepcopy(l)))
            return _Resp(copy.deepcopy(alvo))
        if self._upsert is not None:
            nova, chave = self._upsert
            self.banco.escritas.append((self.tabela, copy.deepcopy(nova)))
            for l in linhas:
                if l.get(chave) == nova.get(chave):
                    l.clear()
                    l.update(copy.deepcopy(nova))
                    return _Resp([nova])
            linhas.append(copy.deepcopy(nova))
            return _Resp([nova])
        self.banco.consultas.append((self.tabela, tuple(self.filtros)))
        saida = [l for l in linhas if all(l.get(c) == v for c, v in self.filtros)
                 and all(l.get(c) is not None for c in self.nao_nulos)]
        return _Resp(copy.deepcopy(saida[: self.lim] if self.lim else saida))


class Banco:
    def __init__(self, **tabelas):
        self.tabelas = {k: [dict(l) for l in v] for k, v in tabelas.items()}
        self.consultas, self.escritas, self.quebrado = [], [], False
        self.colunas_ausentes, self.tabelas_ausentes = {}, set()

    def table(self, nome):
        return _Consulta(self, nome)


def _cfg_linha(**config):
    return {"company_id": A, "config": config}


# =====================================================================================================================
# o padrão: três serviços, três modos — o QCM é o canal inteiro
# =====================================================================================================================
def test_o_padrao_tem_os_tres_servicos_e_o_qcm_e_calcular_entregar_negociar():
    s = PADRAO_DO_PRODUTO["servicos"]
    assert set(s) == set(CFG.SERVICOS) == {"qcm", "cotacao", "renovacao"}
    assert s["qcm"]["modo"] == "calcular_entregar_negociar"
    assert s["cotacao"]["modo"] == "calcular" and s["renovacao"]["modo"] == "calcular"
    assert s["renovacao"]["conta_global_se_vence_em_dias"] == 5
    assert CFG.conta_global_se_vence_em_dias(mesclar(None)) == 5
    # sem linha: o padrão, em qualquer serviço (nada mudou para quem não configurou)
    db = Banco()
    assert carregar(A, db=db) == PADRAO_DO_PRODUTO
    for servico in CFG.SERVICOS:
        c = carregar(A, db=db, servico=servico)
        # a config de UM serviço leva só o bloco dele; o resto é o padrão inteiro
        assert c["servicos"] == {servico: PADRAO_DO_PRODUTO["servicos"][servico]}
        assert {k: v for k, v in c.items() if k != "servicos"} == {
            k: v for k, v in PADRAO_DO_PRODUTO.items() if k != "servicos"}
        # perguntar a uma config o modo de OUTRO serviço é recusado (nunca o padrão adivinhado)
        outro = next(s for s in CFG.SERVICOS if s != servico)
        with pytest.raises(ValueError):
            CFG.modo_do_servico(c, outro)
    with pytest.raises(ValueError):
        carregar(A, db=db, servico="inventado")


# =====================================================================================================================
# 🔴 A SEPARAÇÃO — o guarda da F4 (mutação registrada no handoff: aplicar todos os blocos → VERMELHO)
# =====================================================================================================================
def test_mudar_a_renovacao_nao_muda_o_qcm_e_mudar_o_qcm_muda():
    base = {"validade": {"padrao_dias": 4}, "preferencias_de_seguradoras": {"16": ["porto"]}}
    db = Banco(multicalculo_config=[_cfg_linha(**copy.deepcopy(base))])
    qcm_antes = carregar(A, db=db, servico="qcm")
    assert qcm_antes["validade"]["padrao_dias"] == 4                       # a base da corretora vale no QCM

    # a Renovação ganha o manual dela: outra validade, outras preferidas, outro reajuste
    db.tabelas["multicalculo_config"][0]["config"]["servicos"] = {"renovacao": {
        "validade": {"padrao_dias": 9}, "preferencias_de_seguradoras": {"16": ["tokio", "allianz"]},
        "renovacao": {"reajuste_basica_pct": {"16": 10.0}}, "modo": "calcular_entregar"}}
    assert carregar(A, db=db, servico="qcm") == qcm_antes                   # 🔴 o QCM NÃO mudou
    assert carregar(A, db=db, servico="cotacao")["validade"]["padrao_dias"] == 4
    ren = carregar(A, db=db, servico="renovacao")
    assert ren["validade"]["padrao_dias"] == 9 and CFG.preferencias_do_ramo(ren, 16) == ["tokio", "allianz"]
    assert CFG.reajuste_basica_pct(ren, 16) == 10.0 and CFG.reajuste_basica_pct(ren, 2) == 15.0
    assert CFG.modo_do_servico(ren, "renovacao") == "calcular_entregar"
    # a base (servico=None) é a de antes da 131-0: o manual de um serviço não sobe para ela
    assert carregar(A, db=db)["validade"]["padrao_dias"] == 4

    # o QCM ganha o dele → o QCM muda (o guarda PODE falhar — §9.3 corolário)
    db.tabelas["multicalculo_config"][0]["config"]["servicos"]["qcm"] = {"validade": {"padrao_dias": 7}}
    qcm_depois = carregar(A, db=db, servico="qcm")
    assert qcm_depois != qcm_antes and qcm_depois["validade"]["padrao_dias"] == 7
    assert carregar(A, db=db, servico="renovacao")["validade"]["padrao_dias"] == 9


def test_mesma_regra_para_todos_e_a_base_e_o_servico_so_sobrepoe_o_que_escreveu():
    """"se eu falar que é para todas a mesma regra, aí ajusta em tudo": a BASE vale para os três."""
    db = Banco(multicalculo_config=[_cfg_linha(preferencias_de_seguradoras={"31": ["porto", "azul"]},
                                               servicos={"cotacao": {"modo": "calcular_entregar"}})])
    for s in CFG.SERVICOS:
        assert CFG.preferencias_do_ramo(carregar(A, db=db, servico=s), 31) == ["porto", "azul"]
    assert CFG.modo_do_servico(carregar(A, db=db, servico="cotacao"), "cotacao") == "calcular_entregar"


def test_dois_tenants_o_manual_de_uma_nunca_e_o_da_outra():
    db = Banco(multicalculo_config=[
        {"company_id": A, "config": {"servicos": {"renovacao": {"modo": "calcular_entregar_negociar",
                                                                "validade": {"padrao_dias": 8}}}}},
        {"company_id": B, "config": {"validade": {"padrao_dias": 3}}}])
    ra, rb = carregar(A, db=db, servico="renovacao"), carregar(B, db=db, servico="renovacao")
    assert ra["validade"]["padrao_dias"] == 8 and CFG.modo_do_servico(ra, "renovacao") == "calcular_entregar_negociar"
    assert rb["validade"]["padrao_dias"] == 3 and CFG.modo_do_servico(rb, "renovacao") == "calcular"
    assert db.consultas == [("multicalculo_config", (("company_id", A),)),
                            ("multicalculo_config", (("company_id", B),))]


def test_a_regua_quebrada_num_servico_volta_para_a_base_da_corretora_nunca_para_o_padrao():
    linha = {"comissao": {"piso": 11.0}, "servicos": {"cotacao": {"comissao": {"piso": 14.0}},   # piso > autônomo
                                                      "renovacao": {"comissao": {"entrada": 16.0}}}}
    assert mesclar(linha, "cotacao")["comissao"]["piso"] == 11.0                 # a regra DA CORRETORA
    assert mesclar(linha, "renovacao")["comissao"]["entrada"] == 16.0
    assert mesclar(linha, "renovacao")["comissao"]["piso"] == 11.0
    # o piso do PRODUTO vale sempre: nenhum serviço desce abaixo dele
    assert mesclar({"servicos": {"cotacao": {"comissao": {"piso": 9.0}}}}, "cotacao")["comissao"]["piso"] == 10.0


def test_chave_desconhecida_e_formato_errado_sao_ignorados_na_leitura():
    linha = {"servicos": {"inventado": {"modo": "calcular"},
                          "cotacao": {"modo": "vender_sozinho", "chave_inventada": 1,
                                      "excecoes_do_modo": [{"modo": "calcular"},                  # sem condição
                                                           {"ramo": "16", "modo": "calcular_entregar"},
                                                           {"ramo": True, "modo": "calcular"},
                                                           {"valor_acima_de": -1, "modo": "calcular"}]}}}
    c = mesclar(linha, "cotacao")
    assert "inventado" not in c["servicos"] and "chave_inventada" not in c
    assert c["servicos"]["cotacao"]["modo"] == "calcular"                     # modo fora da lista → o padrão
    assert c["servicos"]["cotacao"]["excecoes_do_modo"] == [{"modo": "calcular_entregar", "ramo": "16"}]
    assert mesclar({"servicos": "lixo"})["servicos"] == PADRAO_DO_PRODUTO["servicos"]


# =====================================================================================================================
# o MODO e as exceções
# =====================================================================================================================
def test_o_modo_e_as_excecoes_a_mais_contida_vence():
    cfg = mesclar({"servicos": {"cotacao": {"modo": "calcular_entregar_negociar", "excecoes_do_modo": [
        {"valor_acima_de": 8000, "modo": "calcular_entregar"},
        {"ramo": 16, "modo": "calcular"},                                   # "Condomínio: só calcular"
    ]}}})
    m = lambda **kw: CFG.modo_do_servico(cfg, "cotacao", **kw)  # noqa: E731
    assert m() == "calcular_entregar_negociar"
    assert m(ramo=31, valor=2000) == "calcular_entregar_negociar"
    assert m(ramo=31, valor=9000) == "calcular_entregar"
    assert m(ramo=16) == "calcular" and m(ramo="16", valor=9000) == "calcular"      # as duas casam: a mais contida
    assert m(valor=8000) == "calcular_entregar_negociar"                             # "acima de" é estrito
    assert CFG.pode_entregar(cfg, "cotacao", ramo=31) and CFG.pode_negociar(cfg, "cotacao", ramo=31)
    assert CFG.pode_entregar(cfg, "cotacao", valor=9000) and not CFG.pode_negociar(cfg, "cotacao", valor=9000)
    assert not CFG.pode_entregar(cfg, "cotacao", ramo=16) and not CFG.pode_negociar(cfg, "cotacao", ramo=16)
    # a ordem em que foram escritas não decide (controle: invertida, o mesmo)
    inv = mesclar({"servicos": {"cotacao": {"modo": "calcular_entregar_negociar", "excecoes_do_modo": list(reversed(
        cfg["servicos"]["cotacao"]["excecoes_do_modo"]))}}})
    assert CFG.modo_do_servico(inv, "cotacao", ramo=16, valor=9000) == "calcular"
    # o padrão do produto: cotação e renovação só calculam; o QCM faz tudo
    p = mesclar(None)
    assert not CFG.pode_entregar(p, "cotacao") and not CFG.pode_entregar(p, "renovacao")
    assert CFG.pode_negociar(p, "qcm")
    with pytest.raises(ValueError):
        CFG.modo_do_servico(p, "outro")


def test_o_reajuste_da_basica_aceita_numero_ou_mapa_sem_quebrar_o_que_existia():
    um = mesclar({"renovacao": {"reajuste_basica_pct": 12}})
    assert {r: CFG.reajuste_basica_pct(um, r) for r in (16, 2, 18)} == {16: 12.0, 2: 12.0, 18: 12.0}
    assert CFG.reajuste_basica_pct(um, 31) is None                            # o auto continua sem a regra
    assert CFG.basica_renovada(um, 16, 1000) == 1120.0
    mapa = mesclar({"renovacao": {"reajuste_basica_pct": {"16": 10, "2": 130}}})   # 130 fora da faixa
    assert (CFG.reajuste_basica_pct(mapa, 16), CFG.reajuste_basica_pct(mapa, 2)) == (10.0, 15.0)
    # o atalho também vale no manual da Renovação, e só nele
    linha = {"servicos": {"renovacao": {"renovacao": {"reajuste_basica_pct": 8}}}}
    assert CFG.reajuste_basica_pct(mesclar(linha, "renovacao"), 18) == 8.0
    assert CFG.reajuste_basica_pct(mesclar(linha, "qcm"), 18) == 15.0
    # a função lida direto sobre um número cru (quem passar a config sem mesclar)
    assert CFG.reajuste_basica_pct({"renovacao": {"reajuste_basica_pct": 7}}, 2) == 7.0


# =====================================================================================================================
# a ESCRITA — o router real, com a chave interna
# =====================================================================================================================
@pytest.fixture
def cliente(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api import servicos_da_corretora as S

    monkeypatch.setenv("BACKEND_INTERNAL_API_KEY", "chave-de-teste")
    banco = _mundo()
    monkeypatch.setattr(S, "_db", lambda: banco)
    app = FastAPI()
    app.include_router(S.router)
    c = TestClient(app)
    c.banco = banco
    c.cab = {"X-AutoBrokers-Internal-Key": "chave-de-teste"}
    return c


def _mundo() -> Banco:
    """corretora_a: tudo configurado + aderida ao QCM; corretora_b: nada. Linhas de B com cara de A para pegar vazamento."""
    return Banco(
        multicalculo_config=[{"company_id": A, "config": {"comissao": {"piso": 11.0}, "google_confirmado": None,
                                                          "servicos": {"renovacao": {"modo": "calcular_entregar"}}},
                              "atualizado_em": "2026-10-10T12:00:00+00:00"},
                             {"company_id": B, "config": {"validade": {"padrao_dias": 3}},
                              "atualizado_em": "2026-10-09T12:00:00+00:00"}],
        multicalculo_adesoes=[{"canal_company_id": CANAL, "corretora_company_id": A, "ativa": True}],
        tenant_connections=[
            {"id": "t-a", "company_id": A, "status": "connected", "connector_templates": {"slug": "infocap"}},
            {"id": "t-b", "company_id": B, "status": "connected", "connector_templates": {"slug": "google-drive"}},
            {"id": "t-b2", "company_id": B, "status": "invalid", "connector_templates": {"slug": "infocap"}}],
        portal_accounts=[
            {"id": "p-a", "company_id": A, "portal_key": "agger", "account_label": "agger-da-corretora",
             "uso": "global", "robo_estado": "ativo", "secret_encrypted": "cifrado-ficticio"},
            {"id": "p-a1", "company_id": A, "portal_key": "agger", "account_label": "agger-membro-a1",
             "uso": "membro", "dono_user_id": MEMBRO_A1, "robo_estado": "ativo", "secret_encrypted": "cifrado-ficticio"},
            # conta de PESSOA em B cujo dono é membro de A: nunca conta para A, nem para B (não é membro de B)
            {"id": "p-b1", "company_id": B, "portal_key": "agger", "account_label": "agger-membro-x",
             "uso": "membro", "dono_user_id": MEMBRO_A2, "robo_estado": "ativo", "secret_encrypted": "cifrado-ficticio"}],
        company_members=[
            {"user_id": MEMBRO_A1, "company_id": A, "status": "active", "funcoes": ["comercial"]},
            {"user_id": MEMBRO_A2, "company_id": A, "status": "active", "funcoes": ["comercial", "negociador"]},
            {"user_id": MEMBRO_B1, "company_id": B, "status": "active", "funcoes": []}],
        membro_produtores=[{"company_id": A, "user_id": MEMBRO_A1, "sistema": "infocap", "codigo": "p-1"}],
    )


def test_get_devolve_o_sobreposto_e_o_efetivo_e_o_qcm_so_com_adesao(cliente):
    ra = cliente.get(f"/api/servicos-da-corretora?company_id={A}", headers=cliente.cab).json()
    rb = cliente.get(f"/api/servicos-da-corretora?company_id={B}", headers=cliente.cab).json()
    assert ra["qcm_aderido"] is True and ra["servicos"] == ["cotacao", "renovacao", "qcm"]
    assert rb["qcm_aderido"] is False and rb["servicos"] == ["cotacao", "renovacao"] and "qcm" not in rb["efetivo"]
    assert ra["sobreposto"]["servicos"] == {"renovacao": {"modo": "calcular_entregar"}}
    assert ra["efetivo"]["renovacao"]["modo"] == "calcular_entregar" and ra["efetivo"]["cotacao"]["modo"] == "calcular"
    assert ra["padrao"]["renovacao"]["reajuste_basica_pct"]["16"] == 15.0
    assert ra["efetivo"]["renovacao"]["conta_global_se_vence_em_dias"] == 5
    assert rb["sobreposto"]["servicos"] == {} and rb["configurado"] is False
    assert cliente.get(f"/api/servicos-da-corretora?company_id={A}").status_code == 401        # sem a chave


def test_put_grava_so_servicos_e_preferencias_e_recusa_chave_fora_da_lista(cliente):
    url, cab = "/api/servicos-da-corretora", cliente.cab
    versao = cliente.get(f"{url}?company_id={A}", headers=cab).json()["versao"]       # a versão que a tela leu
    assert versao == "2026-10-10T12:00:00+00:00"
    bom = {"company_id": A, "atualizado_por": MEMBRO_A1, "versao": versao,
           "servicos": {"cotacao": {"modo": "calcular_entregar",
                                    "excecoes_do_modo": [{"ramo": "16", "modo": "calcular"}],
                                    "preferencias_de_seguradoras": {"31": ["porto"]}},
                        "renovacao": {"modo": "calcular", "conta_global_se_vence_em_dias": 3,
                                      "renovacao": {"antecedencia_dias": 20, "reajuste_basica_pct": {"16": 12}}}},
           "preferencias_de_seguradoras": {"16": ["tokio"]}}
    recusas = [
        {**bom, "chave_inventada": 1},                                                    # fora do corpo
        {**bom, "servicos": {"cotacao": {"comissao": {"piso": 10.0}}}},                    # base fora da lista
        {**bom, "servicos": {"qcm": {"modo": "calcular"}}},                                # o QCM não se edita aqui
        {**bom, "servicos": {"cotacao": {"modo": "vender_sozinho"}}},
        {**bom, "servicos": {"cotacao": {"excecoes_do_modo": [{"modo": "calcular"}]}}},      # exceção sem condição
        {**bom, "servicos": {"renovacao": {"renovacao": {"comissao_a_mais_pp": 1}}}},
        {**bom, "servicos": {"renovacao": {"renovacao": {"reajuste_basica_pct": {"31": 10}}}}},
        {**bom, "servicos": {"renovacao": {"conta_global_se_vence_em_dias": -1}}},
        {**bom, "preferencias_de_seguradoras": {"99": ["porto"]}},
        {"company_id": A, "versao": versao},                                               # nada para gravar
        {k: v for k, v in bom.items() if k != "versao"},                                   # sem a versão lida
    ]
    for corpo in recusas:
        r = cliente.put(url, json=corpo, headers=cab)
        assert r.status_code == 422, corpo
    assert cliente.banco.escritas == []                                                   # nada gravado
    assert cliente.put(url, json={**bom, "company_id": "nao-e-uuid"}, headers=cab).status_code == 400

    r = cliente.put(url, json=bom, headers=cab)
    assert r.status_code == 200, r.text
    (tabela, escrita), = cliente.banco.escritas
    assert tabela == "multicalculo_config" and escrita["company_id"] == A and escrita["atualizado_por"] == MEMBRO_A1
    cfg = escrita["config"]
    assert cfg["comissao"] == {"piso": 11.0} and "google_confirmado" in cfg                # o resto da linha FICA
    assert cfg["servicos"]["cotacao"]["modo"] == "calcular_entregar"
    assert cfg["preferencias_de_seguradoras"] == {"16": ["tokio"]}
    efe = r.json()["efetivo"]
    assert efe["renovacao"]["antecedencia_dias"] == 20 and efe["renovacao"]["reajuste_basica_pct"]["16"] == 12.0
    assert efe["renovacao"]["conta_global_se_vence_em_dias"] == 3
    assert efe["cotacao"]["preferencias_de_seguradoras"]["31"] == ["porto"]
    assert efe["renovacao"]["preferencias_de_seguradoras"]["16"] == ["tokio"]              # a comum vale nos outros
    # 🔴 a outra corretora: a linha dela intacta
    linha_b = next(l for l in cliente.banco.tabelas["multicalculo_config"] if l["company_id"] == B)
    assert linha_b["config"] == {"validade": {"padrao_dias": 3}}
    # um serviço enviado substitui SÓ o bloco dele (o da renovação continua)
    r = cliente.put(url, json={"company_id": A, "versao": r.json()["versao"],
                               "servicos": {"cotacao": {"modo": "calcular"}}}, headers=cab)
    linha_a = next(l for l in cliente.banco.tabelas["multicalculo_config"] if l["company_id"] == A)
    assert linha_a["config"]["servicos"]["renovacao"]["conta_global_se_vence_em_dias"] == 3
    assert linha_a["config"]["servicos"]["cotacao"] == {"modo": "calcular"} and linha_a["atualizado_por"] is None
    # o que a tela não edita (escrito por outro caminho) sobrevive à gravação da tela
    linha_a["config"]["servicos"]["cotacao"]["validade"] = {"padrao_dias": 4}
    cliente.put(url, json={"company_id": A, "versao": linha_a["atualizado_em"],
                           "servicos": {"cotacao": {"modo": "calcular_entregar"}}}, headers=cab)
    assert linha_a["config"]["servicos"]["cotacao"] == {"validade": {"padrao_dias": 4}, "modo": "calcular_entregar"}


def test_put_numa_corretora_sem_linha_cria_a_linha_dela(cliente):
    cliente.banco.tabelas["multicalculo_config"] = [l for l in cliente.banco.tabelas["multicalculo_config"]
                                                   if l["company_id"] != B]
    assert cliente.get(f"/api/servicos-da-corretora?company_id={B}", headers=cliente.cab).json()["versao"] is None
    r = cliente.put("/api/servicos-da-corretora", headers=cliente.cab,
                    json={"company_id": B, "versao": None, "servicos": {"renovacao": {"modo": "calcular_entregar"}}})
    assert r.status_code == 200 and r.json()["efetivo"]["renovacao"]["modo"] == "calcular_entregar"
    assert [l["company_id"] for l in cliente.banco.tabelas["multicalculo_config"]] == [A, B]
    assert r.json()["versao"]                                                     # a linha nova já tem versão


def test_conserto_p2_dois_admins_ao_mesmo_tempo_o_segundo_recebe_conflito_e_nada_se_perde(cliente):
    """🔴 conserto 131-0 A (juiz P1 · red P2, a reprodução `rt_put.py`): os dois admins abrem a tela (a MESMA versão);
    um salva a Cotação, o outro a Renovação. Antes: o segundo apagava o primeiro. Agora: o segundo recebe 409 com a
    frase, nada dele é gravado, e a Cotação do primeiro fica. Controle: o segundo, depois de recarregar, salva."""
    from app.api import servicos_da_corretora as S

    url, cab = "/api/servicos-da-corretora", cliente.cab
    lida = cliente.get(f"{url}?company_id={A}", headers=cab).json()["versao"]
    um = cliente.put(url, headers=cab, json={"company_id": A, "versao": lida,
                                             "servicos": {"cotacao": {"modo": "calcular_entregar"}}})
    assert um.status_code == 200 and um.json()["versao"] != lida
    escritas = len(cliente.banco.escritas)
    dois = cliente.put(url, headers=cab, json={"company_id": A, "versao": lida,
                                               "servicos": {"renovacao": {"modo": "calcular_entregar_negociar"}}})
    assert dois.status_code == 409 and dois.json()["detail"] == S.FRASE_DO_CONFLITO
    assert len(cliente.banco.escritas) == escritas                                   # nada do segundo foi gravado
    linha_a = next(l for l in cliente.banco.tabelas["multicalculo_config"] if l["company_id"] == A)
    assert linha_a["config"]["servicos"]["cotacao"] == {"modo": "calcular_entregar"}   # a edição do 1º ficou
    # a corrida que a leitura não pega (a linha muda ENTRE a leitura e o update): o CAS do update recusa
    banco = cliente.banco
    original = S._linha

    def lida_e_logo_mudada(db, cid):
        linha = original(db, cid)
        next(l for l in banco.tabelas["multicalculo_config"] if l["company_id"] == cid)["atualizado_em"] = "outra"
        return linha

    S._linha = lida_e_logo_mudada
    try:
        with pytest.raises(S.Conflito):
            S.gravar(banco, A, versao=linha_a["atualizado_em"], servicos={"renovacao": {"modo": "calcular"}})
    finally:
        S._linha = original
    # e a corretora SEM linha: duas telas criando ao mesmo tempo — a segunda recebe o conflito, não um erro 500
    cliente.banco.tabelas["multicalculo_config"] = [l for l in banco.tabelas["multicalculo_config"]
                                                   if l["company_id"] != B]
    novo = {"company_id": B, "versao": None, "servicos": {"cotacao": {"modo": "calcular"}}}
    assert cliente.put(url, headers=cab, json=novo).status_code == 200
    assert cliente.put(url, headers=cab, json=novo).status_code == 409
    # CONTROLE: o segundo admin recarrega (versão nova) e salva — a Renovação dele entra e a Cotação do 1º fica
    nova = cliente.get(f"{url}?company_id={A}", headers=cab).json()["versao"]
    tres = cliente.put(url, headers=cab, json={"company_id": A, "versao": nova,
                                               "servicos": {"renovacao": {"modo": "calcular_entregar_negociar"}}})
    assert tres.status_code == 200, tres.text
    linha_a = next(l for l in cliente.banco.tabelas["multicalculo_config"] if l["company_id"] == A)
    assert set(linha_a["config"]["servicos"]) == {"cotacao", "renovacao"}


# =====================================================================================================================
# a PRONTIDÃO — 4 passos, DUAS corretoras, só leitura
# =====================================================================================================================
def test_prontidao_duas_corretoras_cada_uma_ve_o_seu(cliente):
    def passos(cid):
        r = cliente.get(f"/api/servicos-da-corretora/prontidao?company_id={cid}", headers=cliente.cab)
        assert r.status_code == 200
        return {p["chave"]: p for p in r.json()["passos"]}

    pa, pb = passos(A), passos(B)
    assert list(pa) == ["sistema_de_gestao", "agger_da_corretora", "equipe", "servicos"]
    assert {k: p["estado"] for k, p in pa.items()} == {"sistema_de_gestao": "pronto", "agger_da_corretora": "pronto",
                                                     "equipe": "em_parte", "servicos": "pronto"}
    assert pa["equipe"]["numeros"] == {"pessoas_ativas": 2, "comerciais": 2, "comerciais_com_agger": 1,
                                       "com_agger_proprio": 1, "vinculos_de_produtor": 1}
    # B: a InfoCap dela está cadastrada e NÃO conectada (a conectada de A nunca conta); sem Agger; ninguém comercial;
    # a conta de pessoa em B cujo dono não é membro de B não conta
    assert {k: p["estado"] for k, p in pb.items()} == {"sistema_de_gestao": "atencao", "agger_da_corretora": "falta",
                                                     "equipe": "falta", "servicos": "falta"}
    assert pb["equipe"]["numeros"] == {"pessoas_ativas": 1, "comerciais": 0, "comerciais_com_agger": 0,
                                       "com_agger_proprio": 0, "vinculos_de_produtor": 0}
    assert all(p["link"].startswith("/dashboard/personalizacao/") for p in pa.values())
    # 🔴 toda leitura pediu o filtro da corretora ao banco
    for tabela, filtros in cliente.banco.consultas:
        assert ("company_id", A) in filtros or ("company_id", B) in filtros or ("corretora_company_id", A) in filtros \
            or ("corretora_company_id", B) in filtros, (tabela, filtros)
    assert cliente.banco.escritas == []                                                   # só leitura
    # nada de segredo na resposta
    r = cliente.get(f"/api/servicos-da-corretora/prontidao?company_id={A}", headers=cliente.cab)
    assert "cifrado" not in r.text


def test_prontidao_antes_das_colunas_das_outras_fatias_nao_quebra(cliente):
    """`funcoes` (F1), `uso` (F3) e `membro_produtores` (F2) chegam por migration: antes delas, o passo 3 diz 'falta'."""
    cliente.banco.colunas_ausentes = {"company_members": {"funcoes"}, "portal_accounts": {"uso"}}
    cliente.banco.tabelas_ausentes = {"membro_produtores"}
    r = cliente.get(f"/api/servicos-da-corretora/prontidao?company_id={A}", headers=cliente.cab)
    assert r.status_code == 200
    eq = {p["chave"]: p for p in r.json()["passos"]}["equipe"]
    assert eq["estado"] == "falta" and eq["numeros"]["pessoas_ativas"] == 2 and eq["numeros"]["comerciais"] == 0


# =====================================================================================================================
# 🔴 O CAMINHO DA PROPOSTA (§5.3): o HTML servido do QCM lê o manual do QCM, e só ele
# =====================================================================================================================
BASE_URL = "https://app.exemplo.test"
CHROME = ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/129.0.0.0 Mobile Safari/537.36")


def _html_do_canal(m):
    from app.services.artifacts.service import ArtifactService
    from app.services.multicalculo.proposta import publicar_proposta

    r = asyncio.run(publicar_proposta(company_id=m.dono, pedido_id=m.pedido_id, situacao="novo_sem_apolice",
                                      primeiro_nome="Cliente", db=m.db, base_url=BASE_URL))
    servido = ArtifactService(m.banco.visao("rota-publica")).abrir_compartilhado(r["token"], user_agent=CHROME)
    doc = servido["html"]
    # o que muda de uma publicação para outra sem ser config (token, id, carimbo) sai da comparação
    return re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|/r/[A-Za-z0-9_-]+|"
                  r"sha256-[A-Za-z0-9+/=]+|nonce-[A-Za-z0-9+/=]+", "·", doc)


def _config_de(m, company_id):
    for l in m.banco.linhas("multicalculo_config"):
        if l["company_id"] == company_id:
            return l["config"]
    m.banco.semear("multicalculo_config", {"company_id": company_id, "config": {}})
    return _config_de(m, company_id)


def test_o_caminho_da_proposta_a_renovacao_nao_muda_o_html_do_qcm_e_o_qcm_muda(monkeypatch):
    from dubles import mundo_da_proposta as M

    monkeypatch.setenv("PUBLIC_APP_URL", BASE_URL)
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    antes = _html_do_canal(m)
    nome_novo = "Comparador Do Manual Do QCM"

    # a RENOVAÇÃO do canal e da anfitriã ganham manual próprio: nome do canal e validade — o HTML do QCM não muda
    _config_de(m, m.canal)["servicos"] = {"renovacao": {"canal": {"nome": "Nome Da Renovacao Que Nao Pode Vazar"}}}
    _config_de(m, m.alfa)["servicos"] = {"renovacao": {"validade": {"padrao_dias": 9}},
                                         "cotacao": {"validade": {"padrao_dias": 8}}}
    depois_da_renovacao = _html_do_canal(m)
    assert depois_da_renovacao == antes
    assert "Nome Da Renovacao Que Nao Pode Vazar" not in depois_da_renovacao

    # controle: o QCM ganha o dele — no CANAL (cfg_sol: o nome) e na ANFITRIÃ (cfg_anf: a validade) → o HTML muda
    _config_de(m, m.canal)["servicos"]["qcm"] = {"canal": {"nome": nome_novo}}
    _config_de(m, m.alfa)["servicos"]["qcm"] = {"validade": {"padrao_dias": 2}}
    depois_do_qcm = _html_do_canal(m)
    assert depois_do_qcm != antes
    assert nome_novo in depois_do_qcm                                     # o manual do QCM do canal chegou à página
    # a validade da ANFITRIÃ (cfg_anf), no modelo gravado de cada versão: padrão (5 dias) → a do QCM (2 dias)
    versoes = sorted(m.banco.linhas("artifact_versions"), key=lambda x: x["version"])
    datas = [datetime.fromisoformat(v["payload"]["validade_ate"]) for v in versoes]
    assert len(datas) == 3 and datas[0] == datas[1]                                   # a renovação não mexeu
    padrao = PADRAO_DO_PRODUTO["validade"]["padrao_dias"]
    assert (datas[0] - datas[2]).days == padrao - 2                                   # o QCM da anfitriã mexeu


def test_conserto_p1_a_proposta_da_corretora_le_o_manual_do_servico_do_pedido(monkeypatch):
    """🔴 conserto 131-0 A (red P1): o pedido DA PRÓPRIA corretora com `servico='renovacao'` → a proposta lê o manual da
    RENOVAÇÃO (aqui: a validade). Antes, `repo.pedido` não selecionava `servico` e a proposta caía sempre na base.
    Controle: o MESMO pedido sem serviço (legado) usa a base — a diferença é só o serviço do pedido."""
    from dubles import mundo_da_proposta as M
    from app.services.multicalculo.proposta import montar_proposta

    monkeypatch.setenv("PUBLIC_APP_URL", BASE_URL)
    m = M.montar_mundo(monkeypatch, solicitante="beta")
    _config_de(m, m.beta)["servicos"] = {"renovacao": {"validade": {"padrao_dias": 9}},
                                         "cotacao": {"validade": {"padrao_dias": 8}}}

    def validade():
        modelo = asyncio.run(montar_proposta(m.dono, m.pedido_id, "novo_sem_apolice", None, primeiro_nome="Cliente",
                                             db=m.db, agora=m.relogio.agora()))
        return datetime.fromisoformat(modelo["validade_ate"]).date()

    [ped] = [p for p in m.banco.linhas("multicalculo_pedidos") if p["id"] == m.pedido_id]
    base = validade()                                                    # controle: sem serviço → a base
    ped["servico"] = "renovacao"
    renov = validade()
    ped["servico"] = "cotacao"
    cot = validade()
    padrao = PADRAO_DO_PRODUTO["validade"]["padrao_dias"]
    hoje = m.relogio.agora().date()
    assert (base - hoje).days == padrao
    assert (renov - hoje).days == 9, "a proposta da corretora não leu o manual da renovação"
    assert (cot - hoje).days == 8


# =====================================================================================================================
# G8 — nenhum número comercial no router novo
# =====================================================================================================================
def test_g8_o_router_dos_servicos_nao_escreve_numero_comercial():
    from test_spec130a_a_config import proibidos, varrer

    fonte = (BACKEND / "app" / "api" / "servicos_da_corretora.py").read_text(encoding="utf-8")
    assert varrer(fonte, "servicos_da_corretora.py") == []
    # controle: o padrão da antecedência escrito à mão é achado
    n = PADRAO_DO_PRODUTO["renovacao"]["antecedencia_dias"]
    assert float(n) in proibidos()
    assert varrer(fonte + f"\nANTECEDENCIA = {n}\n", "x.py") != []
