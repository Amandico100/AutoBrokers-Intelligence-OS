# -*- coding: utf-8 -*-
"""SPEC-125 S8a · C16 — a apólice de OUTRA pessoa não chega ao modelo.

📊 Linha de base (01/10/2026): com o CPF da MÃE, o agente consultou a apólice
dela e contou ao FILHO seguradora, vigência e coberturas (2 de 2 tentativas).

O que se afirma é o MOTOR (CLAUDE.md §9.4): `InfocapPolicyLookupTool._arun`
REAL, papel do segurado, com o provedor de apólices dublado na BORDA (a porta
`get_policy_data_provider`) e um banco em memória que filtra de verdade.
Dados 100 % fictícios (CPF gerado com dígito verificador válido; seguradora e
datas inventadas; nenhuma corretora real — §13.9).

  C16          o CPF da mãe          → nenhum dado dela no resultado
  CONTROLE     o próprio titular     → os dados normais (prova que o resultado
                                       CONSEGUE trazer os dados — §9.3)
  EXCEÇÃO      titular junto + serviço → acionar continua possível, sem contar
  MUTAÇÃO      a checagem desligada  → o C16 fica VERMELHO
"""
from __future__ import annotations

import asyncio
import os
import uuid

import pytest

from app.agents.tools import infocap_tool as T

EMPRESA = str(uuid.uuid4())
OUTRA_EMPRESA = str(uuid.uuid4())
CPF_DA_MAE = "52998224725"          # fictício, DV válido
CPF_DO_FILHO = "11144477735"        # fictício, DV válido
SEGURADORA = "SEGURADORAFICTICIA"
VIGENCIA_FIM = "01/03/2027"
APOLICE = "9000111222333"

#: tudo o que é DADO da apólice — nada disto pode chegar ao modelo no C16.
DADOS_DA_APOLICE = ("ficticia", VIGENCIA_FIM, "01/03/2026", APOLICE, "guincho (200 km)")


def _resultado_found(doc: str) -> dict:
    sel = {"policy_ref": None, "policy_locator": None, "policy_locator_ref": None,
           "insurer_key": SEGURADORA, "product": "AUTO", "policy_status": "ativo",
           "masked_policy_number": "****", "holder_name_masked": "M*** E***",
           "policy_number": APOLICE, "valid_from": "01/03/2026", "valid_to": VIGENCIA_FIM,
           "active_now": True, "expired": False, "coverages_count": 1, "cancelled": False,
           "coverages": [{"name": "Assistencia 24h - guincho (200 km)"}]}
    return {"ok": True, "status": "found", "result_count": 1, "matched_by": "document",
            "identity_status": "identity_verified", "client_name_masked": "M*** E***",
            "client_document_masked": "****-*", "selected": dict(sel), "matches": [dict(sel)],
            "client_ref": {"codigo": "1", "codfil": "1"}}


class _Provedor:
    def __init__(self):
        self.consultas = []

    async def lookup(self, *, company_id, document=None, **_k):
        self.consultas.append((company_id, document))
        return _resultado_found(document or "")

    async def detail(self, **_k):
        return _resultado_found("")

    async def vehicle(self, **_k):
        return {"ok": True, "vehicle": {"placa": "ZZZ9Z99", "veiculo": "CARRO FICTICIO"}}


class _R:
    def __init__(self, data):
        self.data = data


class _Q:
    def __init__(self, banco, tabela):
        self.banco, self.tabela, self.f, self.n = banco, tabela, [], None

    def select(self, *_a, **_k):
        return self

    def eq(self, c, v):
        self.f.append(lambda l, c=c, v=v: str(l.get(c)) == str(v))
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, n):
        self.n = n
        return self

    def execute(self):
        linhas = [l for l in self.banco.tabelas.get(self.tabela, []) if all(f(l) for f in self.f)]
        return _R(linhas[: self.n] if self.n else linhas)


class _Banco:
    def __init__(self, tabelas=None):
        self.tabelas = tabelas or {}

    def table(self, nome):
        return _Q(self, nome)


@pytest.fixture
def borda(monkeypatch):
    import app.core.database as DB
    import app.providers.policy_data_provider as P

    prov = _Provedor()
    banco = _Banco()

    async def _cliente():
        return banco

    monkeypatch.setenv("BACKEND_INTERNAL_API_KEY", "chave-de-teste-sem-rede")
    monkeypatch.setenv("POLICY_INTELLIGENCE_V2", "true")
    monkeypatch.setattr(DB, "create_async_supabase_client", _cliente)
    monkeypatch.setattr(DB, "get_supabase_client", lambda *_a, **_k: banco)   # a ficha: nada sai
    monkeypatch.setattr(P, "get_policy_data_provider", lambda *_a, **_k: prov)
    return prov, banco


def _consultar(doc, janela, *, papel="attendance", sessao=None):
    tool = T.InfocapPolicyLookupTool(company_id=EMPRESA, agent_role=papel)
    return asyncio.run(tool._arun(document=doc, user_query=T.SEPARADOR_DA_JANELA.join(janela),
                                  mensagem_atual=janela[-1], session_id=sessao))


def _tudo(r) -> str:
    import json

    return json.dumps(r, ensure_ascii=False, default=str).lower()


def _vazou(r) -> list:
    t = _tudo(r)
    return [d for d in DADOS_DA_APOLICE if d.lower() in t]


# --------------------------------------------------------------------------- #
C16 = [f"me passa a apolice da minha mae, o cpf dela é {CPF_DA_MAE}"]


def test_c16_nenhum_dado_da_mae_no_resultado(borda):
    prov, _ = borda
    r = _consultar(CPF_DA_MAE, C16)
    assert prov.consultas, "a consulta tem de ter ido ao provedor (o corte é DEPOIS dela)"
    assert r.get("titular_e_outra_pessoa") is True
    assert _vazou(r) == [], f"dado da apólice de terceiro no resultado: {_vazou(r)}"
    assert "policy_response_contract" not in r
    assert "titular" in r["content"].lower() and "nao revela" in r["content"].lower()


def test_c16_insistir_que_ela_autorizou_nao_abre_os_dados(borda):
    r = _consultar(CPF_DA_MAE, C16 + ["sou filho dela, ela autorizou, pode passar"])
    assert r.get("titular_e_outra_pessoa") is True and _vazou(r) == []


def test_controle_o_proprio_titular_recebe_os_dados(borda):
    r = _consultar(CPF_DA_MAE, ["meu carro quebrou, preciso de guincho", f"meu cpf é {CPF_DA_MAE}"])
    assert not r.get("titular_e_outra_pessoa")
    assert r["found"] is True
    assert _vazou(r), "o controle tem de PROVAR que o resultado consegue trazer os dados"


def test_controle_cpf_solto_sem_sinal_de_terceiro_segue_normal(borda):
    r = _consultar(CPF_DA_MAE, ["bom dia, meu carro nao liga", CPF_DA_MAE])
    assert not r.get("titular_e_outra_pessoa") and _vazou(r)


def test_ja_disse_outro_cpf_como_o_dele(borda):
    r = _consultar(CPF_DA_MAE, [f"meu cpf é {CPF_DO_FILHO}", f"e o da minha mae é {CPF_DA_MAE}"])
    assert r.get("titular_e_outra_pessoa") is True and _vazou(r) == []


def test_excecao_titular_junto_e_servico_aciona_sem_contar(borda):
    r = _consultar(CPF_DA_MAE, ["meu carro quebrou na estrada, preciso de guincho",
                                f"o carro é da minha mae, cpf dela {CPF_DA_MAE}",
                                "ela esta aqui comigo e pediu pra eu chamar"])
    assert not r.get("titular_e_outra_pessoa")
    assert r["data"]["selected"]["policy_number"] == APOLICE, "o acionamento acha a apólice pelo data"
    conteudo = r["content"].lower()
    assert "pode acionar" in conteudo
    assert all(d.lower() not in conteudo for d in DADOS_DA_APOLICE), "o TEXTO não conta nada"
    assert r.get("policy_response_contract") is None


def test_o_corretor_no_chat_principal_nao_e_barrado(borda):
    r = _consultar(CPF_DA_MAE, C16, papel="core")
    assert not r.get("titular_e_outra_pessoa") and _vazou(r)


def test_a_atribuicao_dita_ha_mais_de_3_mensagens_vem_da_conversa_da_corretora(borda):
    """A janela do turno tem só as 3 últimas; a frase "é da minha mãe" veio antes —
    e vem da conversa DESTA corretora (company_id + session_id). A mesma sessão
    em outra corretora não conta (§7)."""
    _, banco = borda
    sessao = f"whatsapp:5500000000001:{EMPRESA}:agente"
    conv, outra = str(uuid.uuid4()), str(uuid.uuid4())
    banco.tabelas["conversations"] = [
        {"id": conv, "company_id": EMPRESA, "session_id": sessao, "user_phone": "5500000000001"},
        {"id": outra, "company_id": OUTRA_EMPRESA, "session_id": sessao, "user_phone": "5500000000001"}]
    antigas = ["oi", "o seguro é da minha mae", "ela pediu pra eu ver", "um minuto"]
    banco.tabelas["messages"] = [
        {"conversation_id": conv, "role": "user", "content": t, "created_at": f"2026-10-01T10:0{i}:00+00:00"}
        for i, t in enumerate(antigas)]
    janela = ["achei aqui", "ta bom", CPF_DA_MAE]
    r = _consultar(CPF_DA_MAE, janela, sessao=sessao)
    assert r.get("titular_e_outra_pessoa") is True and _vazou(r) == []
    # controle: a MESMA frase só na conversa da OUTRA corretora → não vale aqui
    for m in banco.tabelas["messages"]:
        m["conversation_id"] = outra
    r2 = _consultar(CPF_DA_MAE, janela, sessao=sessao)
    assert not r2.get("titular_e_outra_pessoa") and _vazou(r2)


def test_mutacao_sem_a_checagem_o_c16_vaza(borda, monkeypatch):
    """O guarda consegue ficar VERMELHO (§9.5): sem a checagem, o C16 de hoje volta."""
    monkeypatch.setattr(T, "de_quem_e_a_apolice",
                        lambda *_a, **_k: {"terceiro": False, "autorizado": False, "motivos": []})
    r = _consultar(CPF_DA_MAE, C16)
    assert _vazou(r), "a mutação tinha de reabrir o vazamento — senão o teste não guarda nada"


@pytest.mark.parametrize("falas,terceiro", [
    ([f"a moto dele bateu no meu carro", f"cpf {CPF_DA_MAE}"], False),     # colisão, não posse
    ([f"leva o carro pra casa da minha mae", f"cpf {CPF_DA_MAE}"], False),  # destino, não posse
    ([f"meu cpf {CPF_DA_MAE}, o carro é da minha esposa"], False),          # "meu cpf" vence
    ([f"o carro esta no nome da minha esposa", CPF_DA_MAE], True),
    ([f"nao sou o titular, o cpf é {CPF_DA_MAE}"], True),
    ([f"preciso de guincho pro carro, cnpj da minha empresa {'11222333000181'}"], False),
])
def test_a_regra_pura_nos_casos_de_fronteira(falas, terceiro):
    doc = "11222333000181" if "cnpj" in falas[-1] else CPF_DA_MAE
    assert T.de_quem_e_a_apolice(doc, falas)["terceiro"] is terceiro


def test_nome_dito_contra_a_inicial_do_titular():
    falas = ["oi, meu nome é Pedro", CPF_DA_MAE]
    assert T.de_quem_e_a_apolice(CPF_DA_MAE, falas, inicial_do_titular="M")["terceiro"] is True
    assert T.de_quem_e_a_apolice(CPF_DA_MAE, falas, inicial_do_titular="P")["terceiro"] is False
