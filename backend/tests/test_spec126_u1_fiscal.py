# -*- coding: utf-8 -*-
r"""SPEC-126 · U1 — dois consertos na região dos fiscais de `nodes.py`.

1. **pend. 4 do juiz final da 125:** "Vou acionar o guincho agora" + `confirm_first` no MESMO turno, no
   texto FINAL, saía inteiro (📊 BLOCO 0, `scratchpad/pend4.py`: 2 de 3 formas). Agora sai como "Antes de
   acionar, me confirma…"; sobrou só o anúncio → a LINHA PRONTA. Controle: acionou DE VERDADE → "acionei"
   passa; turno sem acionamento → nada muda.
2. **o protocolo da ficha** (pedido da U4): "…o protocolo/agendamento sair" gravava "agendamento" como
   protocolo (📊 a única ficha acionada do banco). Protocolo exige ≥ 1 dígito.

Pelo MOTOR: a função pura e o caminho de `nodes` na bancada N3 (grafo real, modelo-dublê).
"""
from __future__ import annotations

import asyncio
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
for _c in (RAIZ, AQUI):
    if _c not in sys.path:
        sys.path.insert(0, _c)

import pytest  # noqa: E402
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage  # noqa: E402

from app.agents import nodes as N  # noqa: E402
from app.agents.honestidade_do_handoff import guardar_a_verdade_do_handoff  # noqa: E402
from app.agents.tools.insurer_dispatch_tool import pedido_de_confirmacao  # noqa: E402
from app.services.evals import dubles as D  # noqa: E402

PEDIDO = {"subservice": "guincho", "local_atual": "Rua Sete 100", "local_destino": "Oficina do Zé",
          "veiculo_placa": "ABC1D23"}
F = "Antes de acionar, me confirma: guincho da Rua Sete 100 para a Oficina do Zé?"
RECUSA = str(pedido_de_confirmacao("sem sim", pedido=PEDIDO)["content"])
LINHA = pedido_de_confirmacao("sem sim", pedido=PEDIDO)["linha_pronta"]
ACIONOU = "[ACIONAMENTO REAL INICIADO]\nACIONAMENTO REGISTRADO na seguradora. Protocolo 900000001."


def _turno(final, retorno=RECUSA, pre=""):
    msgs = [HumanMessage(content="pode mandar o guincho"),
            AIMessage(content=pre, tool_calls=[{"id": "c1", "name": "insurer_dispatch", "args": {}}]),
            ToolMessage(content=retorno, tool_call_id="c1", name="insurer_dispatch")]
    junto = N.com_o_que_foi_dito_antes_da_ferramenta(final, msgs)
    return guardar_a_verdade_do_handoff(N.sem_anuncio_antes_da_confirmacao(junto, msgs), msgs)


@pytest.mark.parametrize("final,esperado", [
    ("Vou acionar o guincho agora. " + F, F),                                        # o probe do BLOCO 0
    ("Vou acionar o guincho agora! Me confirma o endereço?", "Antes de acionar, me confirma o endereço?"),
    ("Já vou solicitar o socorro. Confirma a placa final 1D23?",
     "Antes de acionar, confirma a placa final 1D23?"),
    ("Certo, vou acionar o guincho agora.", LINHA),                                  # só o anúncio → a linha
])
def test_pend4_o_anuncio_nao_sai_junto_do_pedido_de_ok(final, esperado):
    assert _turno(final) == esperado


def test_pend4_o_anuncio_dito_junto_da_ferramenta_continua_fora():
    """O caminho que o `83dc4b9` já fechava (a fala JUNTO da ferramenta que não fez) — sem teste próprio
    até aqui (BLOCO 0 item 10)."""
    assert _turno(F, pre="Vou acionar o guincho agora.") == F


def test_pend4_controle_acionou_de_verdade_o_acionei_passa():
    texto = "Acionei o guincho ✅ Protocolo 900000001."
    assert N.sem_anuncio_antes_da_confirmacao(texto, [
        HumanMessage(content="pode mandar"),
        AIMessage(content="", tool_calls=[{"id": "c1", "name": "insurer_dispatch", "args": {}}]),
        ToolMessage(content=ACIONOU, tool_call_id="c1", name="insurer_dispatch")]) == texto


def test_pend4_controle_o_ultimo_acionamento_do_turno_decide():
    """Recusado e depois ACIONADO no mesmo turno → o texto sai como veio."""
    msgs = [HumanMessage(content="pode mandar"),
            AIMessage(content="", tool_calls=[{"id": "c1", "name": "insurer_dispatch", "args": {}}]),
            ToolMessage(content=RECUSA, tool_call_id="c1", name="insurer_dispatch"),
            AIMessage(content="", tool_calls=[{"id": "c2", "name": "insurer_dispatch", "args": {}}]),
            ToolMessage(content=ACIONOU, tool_call_id="c2", name="insurer_dispatch")]
    assert N.sem_anuncio_antes_da_confirmacao("Vou acionar e já acionei ✅", msgs) == "Vou acionar e já acionei ✅"


def test_pend4_controle_sem_acionamento_no_turno_e_frase_que_nao_anuncia():
    msgs = [HumanMessage(content="oi")]
    assert N.sem_anuncio_antes_da_confirmacao("Vou acionar o guincho agora.", msgs) == "Vou acionar o guincho agora."
    # "vou chamar a equipe" não é anúncio de ACIONAMENTO
    assert _turno("Vou chamar a equipe se precisar. " + F) == "Vou chamar a equipe se precisar. " + F


def test_pend4_pelo_motor_o_texto_que_sai_ao_segurado():
    """Bancada N3: o modelo-dublê escreve "Vou acionar o guincho agora. <linha>" depois da recusa; o
    que SAI no turno é a linha sem o anúncio — e o fio segue até o acionamento (o "acionei" passa)."""
    from test_spec125_endurecimento import _caso, _rodar
    from test_spec126_u1_fio import CEN_FIO, _linha_do_retorno, roteiro_do_c13

    r, vistos = _rodar(_caso(CEN_FIO), roteiro_do_c13(anuncia_antes="Vou acionar o guincho agora. "))
    trans = r.rastro["estado"]["transcricao"]
    linha = _linha_do_retorno(vistos["retornos"][0])
    assert trans[1]["agente"].strip() == linha, trans[1]["agente"]
    assert "Vou acionar" not in trans[1]["agente"]
    assert trans[2]["agente"].startswith("Guincho acionado ✅"), trans[2]["agente"]


# ===========================================================================
# 2. o protocolo da FICHA exige dígito
# ===========================================================================
@pytest.mark.parametrize("texto,esperado", [
    ("Plano preparado; assim que o protocolo/agendamento sair, eu aviso.", ""),
    ("ACIONAMENTO REGISTRADO. Protocolo 2026ABC123.", "2026ABC123"),
    ("protocolo: 900000001", "900000001"),
    ("Protocolo AB-1234 gerado", "AB-1234"),
    ("protocolo do atendimento ainda não saiu", ""),
])
def test_protocolo_do_retorno(texto, esperado):
    assert N.protocolo_do_retorno(texto) == esperado


def test_protocolo_pela_ficha_do_turno(monkeypatch):
    """`_gravar_ficha_do_turno` (o caminho real): "protocolo/agendamento" não vira protocolo; o número
    do retorno vira."""
    import app.core.database as DB
    import app.services.attendance_ficha as AF

    gravados = []

    async def _gravar(_cli, _emp, _ses, novidades, _obrig):
        gravados.append(novidades)

    monkeypatch.setattr(AF, "gravar", _gravar)
    monkeypatch.setattr(DB, "get_supabase_client", lambda: type("C", (), {"client": object()})())
    estado = {"company_id": "00000000-0000-4000-8000-0000000000a1", "session_id": "whatsapp:1:e:a"}
    args = {"subservice": "guincho", "insurer_key": "allianz", "line_kind": "auto"}
    asyncio.run(N._gravar_ficha_do_turno(estado, "insurer_dispatch", args,
                                         {"content": "assim que o protocolo/agendamento sair, aviso"}))
    asyncio.run(N._gravar_ficha_do_turno(estado, "insurer_dispatch", args,
                                         {"content": "ACIONAMENTO REGISTRADO. Protocolo 2026ABC123."}))
    protos = [(g.get("acionamento") or {}).get("protocolo") for g in gravados]
    assert protos[-1] == "2026ABC123" and "agendamento" not in protos, gravados
