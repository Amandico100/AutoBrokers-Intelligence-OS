# -*- coding: utf-8 -*-
r"""SPEC-127 CONSERTO ÚNICO — item 3 (juiz B2): duas respostas DIFERENTES à MESMA parada antes da fronteira
nunca viram dois `POST /atendimentos`.

```
origem `faltou_cidade_servico` (etapa "abertura", 0 POST)
  → duas chamadas da tool em paralelo leem o MESMO estado e trazem respostas DIFERENTES
  → `montar_job_de_continuacao` (a chave) → `enfileirar_continuacao` (o ÚNICO escritor; o índice único)
  → o worker (serial por conta) roda o que nasceu → POST /atendimentos no total: 1   (era 2)
```
📊 A sonda que nasceu vermelha: `scratchpad/jz127_corrida.py` (POST total = 2). Motor real (journey sobre o
HAR, o escritor da fila), dublê só na borda (o banco do P1, que imita o índice único). Rodar (de backend/):
python -m pytest -q tests/test_spec127_conserto_a_corrida_da_abertura.py
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _c in (str(ROOT), str(ROOT / "tests")):
    if _c not in sys.path:
        sys.path.insert(0, _c)

import test_spec127_p1_o_fio_do_pedido_de_vidro as T  # noqa: E402 — o MESMO dublê de borda do P1

PP, PT = T.PP, T.PT


@pytest.fixture(autouse=True)
def _flag(monkeypatch):
    monkeypatch.setenv("PORTAL_VIDROS_API_FIRST", "1")


def _origem_parada():
    banco = T.Banco([], sem_no_job="local.cidade_servico")
    banco.table("portal_jobs").insert({
        "company_id": T.EMPRESA, "portal_key": "vidros_lanternas", "journey": "abrir_atendimento",
        "params": T._params_completos(confirm=True), "status": "queued", "idempotency_key": "k-origem",
        "session_id": T.SESSAO}).execute()
    banco.table("portal_jobs").select("*").eq("id", "job-1").execute()        # o worker roda a origem
    origem = banco.jobs[0]
    assert origem["evidence"]["stage"] == T.ST.PARADA_FALTOU_CIDADE and banco.posts() == 0
    return banco, origem


def _continuacao(origem, resposta, *, extra="job-1"):
    return PP.montar_job_de_continuacao(
        company_id=T.EMPRESA, job_origem=copy.deepcopy(origem), operacao="responder", pedido_key="k-origem",
        protocolo="k-origem", confirm=True, respostas={"cidade_servico": resposta}, extra=extra)


def _rodar_o_que_nasceu(banco):
    for j in list(banco.jobs):
        if j["status"] == "queued":
            banco.table("portal_jobs").select("*").eq("id", j["id"]).execute()


def test_duas_respostas_DIFERENTES_a_mesma_parada_da_abertura_fazem_UM_POST():
    banco, origem = _origem_parada()
    cid, uf = T.INFOCAP["client"]["cidade"], T.INFOCAP["client"]["estado"]
    # as duas chamadas leram o MESMO estado (a origem parada) antes de qualquer uma inserir
    l1 = _continuacao(origem, {"uf": uf, "cidade": cid})
    l2 = _continuacao(origem, {"uf": uf, "cidade": cid + " "})
    id1, ja1 = PT.enfileirar_continuacao(banco, l1)
    id2, ja2 = PT.enfileirar_continuacao(banco, l2)
    assert id1 and ja1 is None
    assert id2 is None and ja2 is not None and ja2.get("id") == id1          # a 2ª se ANEXA à 1ª
    _rodar_o_que_nasceu(banco)
    assert [j["journey"] for j in banco.jobs] == ["abrir_atendimento", "continuar_atendimento"]
    assert banco.posts() == 1, banco.posts()


def test_CONTROLE_a_cadeia_de_duas_faltas_continua_andando():
    """A próxima parada da abertura é OUTRO job de origem (`extra` muda): a 2ª continuação nasce."""
    banco = T.Banco([], sem_no_job="dano.peca|local.cidade_servico")
    banco.table("portal_jobs").insert({
        "company_id": T.EMPRESA, "portal_key": "vidros_lanternas", "journey": "abrir_atendimento",
        "params": T._params_completos(confirm=True), "status": "queued", "idempotency_key": "k-origem",
        "session_id": T.SESSAO}).execute()
    banco.table("portal_jobs").select("*").eq("id", "job-1").execute()
    assert banco.jobs[0]["evidence"]["stage"] == T.ST.PARADA_FALTOU_PECA
    l1 = PP.montar_job_de_continuacao(company_id=T.EMPRESA, job_origem=copy.deepcopy(banco.jobs[0]),
                                      operacao="responder", pedido_key="k-origem", protocolo="k-origem",
                                      confirm=True, respostas={"peca": "para-brisa"}, extra="job-1")
    assert PT.enfileirar_continuacao(banco, l1)[0]
    _rodar_o_que_nasceu(banco)
    assert banco.jobs[1]["evidence"]["stage"] == T.ST.PARADA_FALTOU_CIDADE and banco.posts() == 0
    cid, uf = T.INFOCAP["client"]["cidade"], T.INFOCAP["client"]["estado"]
    l2 = _continuacao(banco.jobs[1], {"uf": uf, "cidade": cid}, extra="job-2")
    assert PT.enfileirar_continuacao(banco, l2)[0]
    _rodar_o_que_nasceu(banco)
    assert banco.jobs[2]["status"] == "done" and banco.posts() == 1


def test_CONTROLE_depois_da_fronteira_resposta_diferente_e_tentativa_nova():
    """A regra de sempre (G7) não muda onde o pedido JÁ existe: respostas diferentes → chaves diferentes; a
    mesma resposta → a mesma chave."""
    origem = {"id": "job-9", "params": {"cpf_cnpj": "x"}, "session_id": "s",
              "evidence": {"stage": "peca_ambigua", "continuacao": {
                  "possivel": True, "etapa": "peca", "acao_esperada": "responder:peca",
                  "sessao_guardada": True, "sessao_cifrada": "c", "protocolo": "123"}}}

    def chave(resp):
        return PP.montar_job_de_continuacao(company_id=T.EMPRESA, job_origem=origem, operacao="responder",
                                            pedido_key="k", protocolo="123", confirm=True,
                                            respostas={"peca": resp}, extra="job-9")["idempotency_key"]

    assert chave("vidro da porta traseira esquerda") != chave("vidro da porta traseira direita")
    assert chave("vidro da porta traseira esquerda") == chave("vidro da porta traseira esquerda")
