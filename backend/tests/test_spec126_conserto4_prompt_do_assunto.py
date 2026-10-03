# -*- coding: utf-8 -*-
r"""SPEC-126 CONSERTO 4 — o bloco da FICHA que vai ao prompt é o do ASSUNTO EM ABERTO.

O DEFEITO: o conserto 3 criou a régua única do assunto (`attendance_ficha.ficha_do_assunto`, a cópia
só-leitura sem o acionamento de um atendimento ANTERIOR), e o dispatch, a R9 e o dossiê a leem. Mas o
bloco da ficha que vai ao MODELO (`graph._build_initial_state` → `bloco_para_o_prompt`) ainda recebia a
ficha aditiva inteira: num caso NOVO do mesmo telefone, o protocolo de 30 dias atrás saía como
"Protocolo já obtido: X — acompanhe, não acione de novo" — o modelo era mandado NÃO acionar o guincho.

O que se afirma é o MOTOR (§9.4): o turno inteiro pela bancada N3 (o `_build_initial_state` REAL lendo a
ficha e a conversa do banco-dublê) e o prompt de sistema que o modelo-dublê RECEBEU.
CONTROLE: acionado há 5 min no MESMO assunto → o prompt segue com "Protocolo já obtido" (o fio da 125).

    cd backend && PYTHONIOENCODING=utf-8 .venv/Scripts/python -m pytest tests/test_spec126_conserto4_prompt_do_assunto.py -q -p no:cacheprovider
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
for _c in (RAIZ, AQUI):
    if _c not in sys.path:
        sys.path.insert(0, _c)

PROTOCOLO = "PROTO-TESTE-0426"           # fictício
LINHA_DO_FIO = "Protocolo já obtido"
NAO_ACIONE = "não acione de novo"


def _iso(**delta) -> str:
    return (datetime.now(timezone.utc) - timedelta(**delta)).isoformat()


def _ficha_acionada(ha: dict) -> dict:
    em = _iso(**ha)
    return {"fase": "acompanhando", "ramo": "auto", "servico": "chaveiro",
            "acionamento": {"protocolo": PROTOCOLO, "enviado_em": em},
            "historico": [{"fase": "acionado", "em": em}]}


def _prompt_do_turno(chave: str, ficha: dict, historico: list, fala: str) -> str:
    """O prompt de sistema que o modelo RECEBEU num turno da bancada N3 (ficha + conversa no banco)."""
    from test_spec125_endurecimento import CEN_C1, _caso, _rodar

    cen = {**CEN_C1, "chave": chave, "ficha": ficha, "historico": historico,
           "roteiro": {"falas_fixas": [[fala]], "max_turnos": 1}}
    _r, vistos = _rodar(_caso(cen), lambda msgs, vistos: ("Entendi. Onde o carro está agora?", []))
    assert vistos.get("sistemas"), "o modelo-dublê não foi chamado"
    return vistos["sistemas"][0]


def test_caso_novo_do_mesmo_telefone_nao_herda_o_protocolo_de_30_dias():
    """🔴 (vermelho antes: o bloco da ficha mandava 'acompanhe, não acione de novo')."""
    historico = [
        {"de": "segurado", "texto": "fiquei trancado fora do carro", "dias_atras": 30, "min_atras": 20},
        {"de": "agente", "texto": "Acionei o chaveiro para você.", "dias_atras": 30},
    ]
    prompt = _prompt_do_turno("conv-teste-c4-novo", _ficha_acionada({"days": 30}), historico,
                              "meu carro quebrou, preciso de guincho")
    assert "FICHA DESTE ATENDIMENTO" in prompt, "a ficha deixou de ir ao prompt (o teste não guarda nada)"
    assert PROTOCOLO not in prompt, prompt[prompt.find("FICHA DESTE"):][:600]
    assert NAO_ACIONE not in prompt
    assert LINHA_DO_FIO not in prompt
    ficha_no_prompt = prompt[prompt.find("FICHA DESTE"):].split("\n\n")[0]
    assert "Fase: acompanhando" not in ficha_no_prompt and "Fase: acionado" not in ficha_no_prompt, ficha_no_prompt


def test_controle_acionado_ha_5_min_no_mesmo_assunto_segue_com_o_protocolo():
    """CONTROLE: o mesmo assunto (começou há 20 min, acionado há 5) → o fio da 125 continua."""
    historico = [
        {"de": "segurado", "texto": "meu carro quebrou, preciso de guincho", "min_atras": 20},
        {"de": "agente", "texto": "Acionei o guincho para você.", "min_atras": 5},
    ]
    prompt = _prompt_do_turno("conv-teste-c4-mesmo", _ficha_acionada({"minutes": 5}), historico,
                              "e o guincho, já saiu?")
    assert f"{LINHA_DO_FIO}: {PROTOCOLO}" in prompt, prompt[prompt.find("FICHA DESTE"):][:600]
    assert NAO_ACIONE in prompt
