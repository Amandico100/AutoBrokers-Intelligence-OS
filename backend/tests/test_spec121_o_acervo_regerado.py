"""SPEC-121 F3 · o ACERVO VERSIONADO regerado diz a verdade — o gate G5/G4 da F3.

🔴 Este arquivo lê `tests/corpus/telas_reais/` como está. Ele fica VERMELHO no
acervo de 28/09 (antes da F3) e VERDE no acervo regerado pela F3 — é o guarda de
que a cópia do acervo novo foi feita, e de que a próxima regeneração não desfaz
o que a F3 consertou. O desfecho é decidido pelo MOTOR (`sessao_chegou_ao_fim`).

📊 Números medidos no acervo regerado em 29/09/2026 (worktree `-f3`,
`scratchpad/f3/rotas_acervo.py`):
  · allianz residencial: o robô que recomeça depois da pessoa traz 1 máquina de
    lavar inteira até o protocolo (`8ad1d251+2`). A consulta de desentupimento
    (`8ad1d251+1`, "Ver detalhes" → resumo do pedido ANTIGO) NÃO entra mais
    (SPEC-121 F3b, `Z.consulta_de_pedido_existente`): 📊 no acervo regerado em
    29/09 pela F3b, 25 atendimentos da Allianz consultaram (211 eventos fora;
    15 ficaram sem etiqueta pelo motivo da consulta) e ZERO resumos de pedido
    antigo ficaram no acervo (eram 26 telas no acervo da F3, 16 no de 28/09);
  · yelum auto: bateria 5 de 5 com protocolo; chaveiro 2 (`56bd78f7`, `e6a07317`);
  · hdi residencial: nenhuma sessão de fogão na rota do eletricista.
"""

from __future__ import annotations

import collections
import json
import os
import re
import sys
from typing import Dict, List

import pytest

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "scripts"))

import regua_motor as M                 # noqa: E402
import gerar_corpus_de_telas as G       # noqa: E402

CORPUS = os.path.join(AQUI, "corpus", "telas_reais")


def _por_sessao(arquivo: str, servico: str) -> Dict[str, List[str]]:
    caminho = os.path.join(CORPUS, arquivo)
    if not os.path.exists(caminho):
        pytest.skip("acervo versionado ausente")
    por: Dict[str, List[str]] = collections.defaultdict(list)
    for l in open(caminho, encoding="utf-8"):
        if l.strip():
            d = json.loads(l)
            if d.get("servico") == servico:
                por[d["session_id"]].append(d["text"])
    return por


def _com_fim(arquivo: str, servico: str) -> List[str]:
    seg, ramo = arquivo[:-len(".jsonl")].split("-", 1)
    pb = M.get_playbook(M.resolve_playbook_ref(seg, ramo))
    return sorted(s for s, t in _por_sessao(arquivo, servico).items()
                  if G.sessao_chegou_ao_fim(pb, t))


def test_o_robo_que_recomeca_traz_a_maquina_de_lavar_ate_o_protocolo():
    recomecos = [s for s in _com_fim("allianz-residencial.jsonl", "maquina_de_lavar") if "+" in s]
    assert recomecos, ("nenhum atendimento em que o robô RECOMEÇOU depois da pessoa chegou "
                       "ao protocolo — o acervo é o de antes da F3")


def test_a_recarga_de_bateria_da_yelum_e_bateria_e_chega_ao_fim():
    assert len(_com_fim("yelum-auto.jsonl", "bateria")) >= 5
    assert not _por_sessao("yelum-auto.jsonl", "socorro_mecanico").keys() & {
        "86769bd5", "ba475989", "927d8cea", "8ac461dc", "935c4076"}


def test_a_chave_perdida_e_chaveiro_e_nao_guincho():
    assert "56bd78f7" in _por_sessao("yelum-auto.jsonl", "chaveiro")
    assert "56bd78f7" not in _por_sessao("yelum-auto.jsonl", "guincho")


def test_o_fogao_e_a_exploracao_sairam_do_eletricista_da_hdi():
    eletricista = _por_sessao("hdi-residencial.jsonl", "eletricista")
    assert not eletricista.keys() & {"834cc238", "13379965"}
    # 🔴 F3b: e o fogão também não é etiqueta de eletrodoméstico (as telas são do
    #    caminho do eletricista)
    fogoes = {"834cc238", "ed46a953", "b638adcd", "1c8d0849"}
    assert not _por_sessao("hdi-residencial.jsonl", "eletrodomesticos").keys() & fogoes


# 📊 a FORMA do resumo de um pedido que JÁ EXISTIA na Allianz: "*RESUMO*" e o
#    protocolo ANTES do serviço (auto: "Protocolo Nrº:"; residencial: "Protocolo N").
#    A abertura tem o resumo SEM protocolo e o protocolo numa tela depois.
_RESUMO_DE_PEDIDO_ANTIGO = re.compile(r"^\*RESUMO\*\s*\*Protocolo", re.IGNORECASE)


def test_nenhum_resumo_de_pedido_antigo_ficou_no_acervo_da_allianz():
    """🔴 SPEC-121 F3b. É inspeção da FORMA do dado (CLAUDE.md §9.4, a exceção);
    o comportamento está em `test_spec121_consulta_nao_e_abertura` pelo motor."""
    achados = []
    for arquivo in ("allianz-auto.jsonl", "allianz-residencial.jsonl"):
        for l in open(os.path.join(CORPUS, arquivo), encoding="utf-8"):
            if l.strip() and _RESUMO_DE_PEDIDO_ANTIGO.search(json.loads(l)["text"]):
                achados.append((arquivo, json.loads(l)["session_id"]))
    assert not achados, achados


def test_CONTROLE_a_forma_do_resumo_antigo_casa_o_texto_real():
    antigo = ("*RESUMO*\n\n*Protocolo 50000001\n*Serviço:* *DESENTUPIMENTO*;\n"
              "*Endereço:* {ENDERECO}")
    abertura = ("*RESUMO*\n\n*Serviço:* Conserto de Eletrodoméstico\n"
                "*Problema:* Máquina de Lavar roupas")
    assert _RESUMO_DE_PEDIDO_ANTIGO.search(antigo)
    assert not _RESUMO_DE_PEDIDO_ANTIGO.search(abertura)


def test_a_consulta_de_desentupimento_nao_e_desentupimento_com_fim():
    assert "8ad1d251+1" not in _por_sessao("allianz-residencial.jsonl", "desentupimento")
    assert "8ad1d251+1" not in _com_fim("allianz-residencial.jsonl", "desentupimento")


# ─────────────────────────────────────────────────────────────────────────────
# 🔴 F3b · a sessão SEM desfecho também é prova (`G.PISO_DE_DIVERSIDADE`)
# ─────────────────────────────────────────────────────────────────────────────
def _cand(sid, ts, telas, fim, servico="bateria"):
    return (sid, ts, set(telas), fim, servico)


def _rota_cheia_de_desfecho():
    com = [_cand("d%d" % i, "2026-09-%02d" % (20 + i), {"t", "protocolo"}, True)
           for i in range(5)]
    sem = [_cand("s1", "2026-06-19", {"amperes", "consultora"}, False),
           _cand("s2", "2026-06-01", {"t", "x"}, False),
           _cand("s3", "2026-05-01", {"t", "protocolo"}, False)]
    return com + sem


def test_rota_cheia_de_desfecho_ainda_guarda_as_sessoes_sem_desfecho_mais_diferentes():
    escolhidas, _n = G.escolher_sessoes(_rota_cheia_de_desfecho())
    assert {"s1", "s2"} <= set(escolhidas) and "s3" not in escolhidas, escolhidas


def test_CONTROLE_sem_o_piso_de_diversidade_a_prova_do_que_falta_sai():
    """UM fator: `piso_de_diversidade=0` é o gerador de antes da F3b."""
    escolhidas, _n = G.escolher_sessoes(_rota_cheia_de_desfecho(), piso_de_diversidade=0)
    assert not {"s1", "s2", "s3"} & set(escolhidas)


def test_a_consultora_da_porto_continua_no_acervo():
    """📊 `4830574a` é a ÚNICA sessão de porto/bateria com as telas da consultora
    e dos amperes. Fora dela, o simulador punha a rota em ATENDE SOZINHO por
    falta de prova, não por mérito."""
    assert "4830574a" in _por_sessao("porto-auto.jsonl", "bateria")
