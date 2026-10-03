# -*- coding: utf-8 -*-
r"""SPEC-126 U5 · (b) da U3-B — o bloco de acionamento do prompt com o ESCOPO do caso.

📊 T6 (bancada U1, Luna, 02/10/2026): num chaveiro de CARRO o agente disse a senha da assistência
RESIDENCIAL de uma seguradora — o bloco do prompt juntava o "AVISE TAMBÉM" de todos os corredores. A U3-B
deu escopo ao gerador (`conhecimento_de_assistencia(refs, *, seguradora, ramo, servico)`); `graph.py` o
chamava SEM escopo. Agora, com seguradora + ramo na ficha do assunto CORRENTE, o grafo passa o escopo.

O que se afirma é o MOTOR (§9.4): o turno inteiro pela bancada N3 (o `_build_initial_state` REAL lendo a
ficha do banco-dublê) e o prompt de sistema que o modelo-dublê RECEBEU. Controles: sem ficha → o bloco
de antes (só o que vale para todo corredor); assunto novo/caso resolvido → sem escopo.

    cd backend && PYTHONIOENCODING=utf-8 .venv/Scripts/python -m pytest tests/test_spec126_u5_escopo_do_acionamento.py -q -p no:cacheprovider
"""
from __future__ import annotations

import os
import sys

import pytest

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
for _c in (RAIZ, AQUI):
    if _c not in sys.path:
        sys.path.insert(0, _c)

from app.agents.graph import escopo_do_acionamento  # noqa: E402
from app.services import corridor_playbooks as CP  # noqa: E402

SENHA = "4 últimos"            # o trecho das instruções de senha da assistência RESIDENCIAL (U3-B)
UNIVERSAL = "18 anos"          # a instrução que vale para TODO corredor (U3-B, controle)


def _avise(prompt: str) -> str:
    i = prompt.find("AVISE TAMBÉM")
    return prompt[i:prompt.find("COMO TERMINA", i)] if i >= 0 else ""


def _prompt_do_turno(ficha):
    """O prompt de sistema que o modelo RECEBEU num turno da bancada N3, com esta ficha no banco."""
    from test_spec125_endurecimento import CEN_C1, _caso, _rodar

    cen = {**CEN_C1, "chave": "conv-teste-u5-escopo", "ficha": ficha,
           "roteiro": {"falas_fixas": [["oi, preciso de ajuda com a assistência"]], "max_turnos": 1}}
    _r, vistos = _rodar(_caso(cen), lambda msgs, vistos: ("Certo, me conta o que aconteceu?", []))
    assert vistos.get("sistemas"), "o modelo-dublê não foi chamado"
    return vistos["sistemas"][0]


@pytest.mark.parametrize("seguradora", ["allianz", "yelum"])
def test_pelo_grafo_o_caso_residencial_da_seguradora_dona_recebe_a_instrucao_dela(seguradora):
    """🔴 (vermelho antes: o grafo chamava SEM escopo) a ficha diz residencial desta seguradora → o
    prompt REAL leva a instrução do corredor DELA."""
    avise = _avise(_prompt_do_turno({"seguradora": seguradora, "ramo": "residencial", "servico": "encanador"}))
    assert SENHA in avise, avise[:600]


@pytest.mark.parametrize("seguradora,servico", [("allianz", "chaveiro"), ("yelum", "guincho")])
def test_pelo_grafo_o_caso_de_carro_nao_ouve_a_instrucao_da_casa(seguradora, servico):
    avise = _avise(_prompt_do_turno({"seguradora": seguradora, "ramo": "auto", "servico": servico}))
    assert avise and SENHA not in avise and "senha" not in avise.lower(), avise[:600]


def test_controle_sem_ficha_o_bloco_de_antes():
    """CONTROLE: sem seguradora na ficha, a chamada SEM escopo — byte a byte o gerador de antes."""
    prompt = _prompt_do_turno(None)
    sem_escopo = CP.conhecimento_de_assistencia(sorted(CP._PLAYBOOKS))
    assert sem_escopo in prompt
    avise = _avise(prompt)
    assert UNIVERSAL in avise and SENHA not in avise


def test_o_escopo_vem_so_do_caso_vivo():
    viva = {"seguradora": "Allianz", "ramo": "residencial", "servico": "encanador"}
    assert escopo_do_acionamento(viva) == {"seguradora": "allianz", "ramo": "residencial", "servico": "encanador"}
    assert escopo_do_acionamento(viva, assunto_novo=True) == {}, "a ficha aditiva traz o caso ANTERIOR"
    assert escopo_do_acionamento({**viva, "resolvido_em": "2026-10-01T10:00:00+00:00"}) == {}
    assert escopo_do_acionamento({"seguradora": "allianz"}) == {} == escopo_do_acionamento({"ramo": "auto"})
    assert escopo_do_acionamento(None) == {} == escopo_do_acionamento("lixo")
    assert escopo_do_acionamento({"seguradora": "porto", "ramo": "auto"}) == {"seguradora": "porto", "ramo": "auto"}
