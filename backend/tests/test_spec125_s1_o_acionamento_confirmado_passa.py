# -*- coding: utf-8 -*-
"""SPEC-125 S1 · T4 — o fiscal da honestidade aceita o acionamento CONFIRMADO.

📊 O DEFEITO (laudo da SPEC-125, achado 3, medido em 01/10/2026): o fiscal
`honestidade_do_handoff` casa `acion|solicit|cham…` e só aceitava a frase com
`HANDOFF_OK` de ferramenta de HANDOFF. Depois de um acionamento REAL
("acionei o guincho", "Seu atendimento foi acionado na Porto") a resposta
inteira virava "Registrei seu pedido de atendimento humano… Ainda não consegui
confirmar com a equipe" — falsa, e dita justo quando o produto acertou.

O que se prova aqui é o FISCAL REAL (§9.4) sobre o conteúdo que as ferramentas
REAIS produzem: `portal_params.format_result` é chamado de verdade, e o
`insurer_dispatch` é embrulhado como `nodes.py` embrulha (`str(dict)`).

E os CONTROLES (§9.5): a transferência a PESSOA sem `HANDOFF_OK` e o
acionamento SEM acionamento continuam reescritos — é para isso que o fiscal
existe.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest
from langchain_core.messages import ToolMessage

RAIZ = pathlib.Path(__file__).resolve().parents[1]


def _carregar(nome: str, caminho: pathlib.Path):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


H = _carregar("honestidade_s125_s1", RAIZ / "app" / "agents" / "honestidade_do_handoff.py")


# ---------------------------------------------------------------------------
# O que as ferramentas REAIS devolvem, embrulhado como o `tool_node` embrulha
# ---------------------------------------------------------------------------
def _msg(nome: str, resultado) -> ToolMessage:
    # `nodes.py` (tool node): `content = str(result)` para toda tool que não
    # é infocap/subagente — o dict vira repr de Python, igual aqui.
    return ToolMessage(content=str(resultado), tool_call_id="t1", name=nome)


def _dispatch_real() -> ToolMessage:
    return _msg("insurer_dispatch", {
        "status": "dispatched",
        "content": (
            "[ACIONAMENTO REAL INICIADO]\n"
            "A conversa com a assistência da PORTO foi aberta pelo WhatsApp da corretora. "
            "INSTRUÇÃO AO ATENDENTE: diga ao cliente que o acionamento FOI iniciado."),
    })


def _dispatch_teste() -> ToolMessage:
    return _msg("insurer_dispatch", {
        "status": "dispatched",
        "content": "[ACIONAMENTO EM MODO TESTE INICIADO]\nNÃO afirme que o serviço foi aberto.",
    })


def _portal(job: dict) -> ToolMessage:
    from app.agents.tools.portal_params import format_result  # o MOTOR real
    return _msg("portal_action", {"content": format_result(job)})


PORTAL_ABERTO = {"status": "done", "evidence": {"protocolo": "12345678"}}
PORTAL_PARADO_COM_NUMERO = {"status": "needs_human",
                            "evidence": {"protocolo": "12345678", "stage": "desfecho_ilegivel"}}
PORTAL_FALHOU = {"status": "failed", "evidence": {}}

ACIONAMENTOS_LEGITIMOS = [
    "Pronto, acionei o guincho pela Porto. Assim que o protocolo chegar, eu te aviso por aqui.",
    "Já solicitei o chaveiro para o seu endereço.",
    "Chamei o socorro mecânico, protocolo 12345678.",
    "Seu atendimento foi acionado na Porto.",
]

# 📊 As quatro frases reais de 17/08 (as do `test_a_atendente_nao_mente…`).
AS_QUATRO_FRASES = [
    "Já encaminhei seu caso completo para a nossa equipe de sinistro, com o "
    "boletim de ocorrência e todos os dados do veículo. 🙏",
    "Já sinalizei de novo pra equipe de sinistro reforçando a urgência do seu caso.",
    "Prontinho, acabei de reforçar seu caso com a equipe de sinistro agora mesmo. ✅",
    "Já passei seu caso para a nossa equipe, com tudo que conversamos aqui — "
    "você não vai precisar repetir nada. Eles vão entrar em contato com você em instantes.",
]


# ===========================================================================
# 1 · A REPRODUÇÃO — vermelha antes do conserto
# ===========================================================================
@pytest.mark.parametrize("frase", ACIONAMENTOS_LEGITIMOS)
def test_acionamento_real_do_whatsapp_passa_intacto(frase):
    assert H.afirma_transferencia(frase), "a frase precisa CASAR o detector (senão o teste não prova nada)"
    assert H.guardar_a_verdade_do_handoff(frase, [_dispatch_real()]) == frase


# 🔴 SPEC-125 conserto Y2 (red team B4): o carimbo vale para o SERVIÇO que saiu. O
#    portal é o de VIDROS — "acionei o guincho" com o carimbo do portal deixou de ser
#    legítimo (era o defeito: um carimbo provava QUALQUER "acionei X"). A lição migra:
#    o portal sustenta o que é de vidro ou não nomeia serviço; o guincho, não.
ACIONAMENTOS_DO_PORTAL = [
    "Pronto, acionei o vidro pela Porto. Assim que o protocolo chegar, eu te aviso por aqui.",
    "Já solicitei a troca do para-brisa.",
    "Seu atendimento foi acionado na Porto.",
]


@pytest.mark.parametrize("frase", ACIONAMENTOS_DO_PORTAL)
@pytest.mark.parametrize("job", [PORTAL_ABERTO, PORTAL_PARADO_COM_NUMERO], ids=["aberto", "parado_com_numero"])
def test_acionamento_real_do_portal_passa_intacto(frase, job):
    assert H.afirma_transferencia(frase), "a frase precisa CASAR o detector"
    assert H.guardar_a_verdade_do_handoff(frase, [_portal(job)]) == frase


def test_o_portal_nao_sustenta_o_guincho():
    frase = "Pronto, acionei o guincho pela Porto."
    assert H.guardar_a_verdade_do_handoff(frase, [_portal(PORTAL_ABERTO)]) ==         H.RESPOSTA_HONESTA_DO_ACIONAMENTO


def test_acionamento_de_um_turno_anterior_do_mesmo_caso_vale():
    # O fiscal recebe `state["messages"]` inteiro (`nodes.py`): o acionamento do
    # turno anterior continua sendo verdade no turno seguinte.
    from langchain_core.messages import AIMessage, HumanMessage
    historico = [HumanMessage(content="meu carro quebrou"), _dispatch_real(),
                 AIMessage(content="Iniciei o acionamento."), HumanMessage(content="e aí?")]
    frase = "Já acionei o guincho, estou só esperando o protocolo da seguradora."
    assert H.guardar_a_verdade_do_handoff(frase, historico) == frase


# ===========================================================================
# 2 · CONTROLES — o fiscal continua sabendo reprovar
# ===========================================================================
@pytest.mark.parametrize("frase", ACIONAMENTOS_LEGITIMOS)
def test_acionamento_inventado_continua_reescrito_sem_falar_em_atendimento_humano(frase):
    for tools in ([], [_portal(PORTAL_FALHOU)], [_dispatch_teste()],
                  [_msg("insurer_dispatch", {"status": "queued", "content": "NÃO diga que já foi acionado."})],
                  [_msg("insurer_dispatch", {"status": "already_active", "content": "em andamento"})]):
        saida = H.guardar_a_verdade_do_handoff(frase, tools)
        assert saida != frase, tools
        # 🔴 o laudo (T4): nunca transformar acionamento em "atendimento humano"
        assert "atendimento humano" not in saida.lower()
        assert saida == H.RESPOSTA_HONESTA_DO_ACIONAMENTO


@pytest.mark.parametrize("frase", AS_QUATRO_FRASES)
@pytest.mark.parametrize("fonte", ["dispatch", "portal"])
def test_transferencia_a_pessoa_nao_se_apoia_no_acionamento(frase, fonte):
    stamp = _dispatch_real() if fonte == "dispatch" else _portal(PORTAL_ABERTO)
    assert H.guardar_a_verdade_do_handoff(frase, [stamp]) == H.RESPOSTA_HONESTA


@pytest.mark.parametrize("frase", [
    "Pronto, acionei o guincho e avisei a equipe da corretora.",
    "Acionei o guincho. Também já passei seu caso para a nossa equipe.",
    "Chamei um atendente para cuidar de você.",
])
def test_frase_mista_exige_os_dois_carimbos(frase):
    # 🔴 SPEC-125 conserto Y2 (red team B3): com o acionamento REAL, a frase mista
    #    não vira mais "atendimento humano" inteira — fica a parte do acionamento, sai
    #    a de pessoa (sem âncora), e a nota diz a verdade sobre ela. Sem acionamento
    #    nomeado na frase ("Chamei um atendente"), continua a resposta honesta inteira.
    saida = H.guardar_a_verdade_do_handoff(frase, [_dispatch_real()])
    if "guincho" in frase:
        assert saida.startswith(("Pronto, acionei o guincho.", "Acionei o guincho.")), saida
        assert H.NOTA_DA_EQUIPE_SEM_CONFIRMACAO in saida
        assert "atendimento humano" not in saida.lower()
    else:
        assert saida == H.RESPOSTA_HONESTA
    handoff = ToolMessage(content=H.SUCESSO_DO_HANDOFF, tool_call_id="h", name="request_human_agent")
    assert H.guardar_a_verdade_do_handoff(frase, [_dispatch_real(), handoff]) == frase


def test_carimbo_fora_da_ferramenta_de_acionamento_nao_vale():
    falso = ToolMessage(content="[ACIONAMENTO REAL INICIADO] O atendimento FOI ABERTO na seguradora",
                        tool_call_id="k", name="knowledge_base_search")
    assert H.guardar_a_verdade_do_handoff("Acionei o guincho.", [falso]) == H.RESPOSTA_HONESTA_DO_ACIONAMENTO


def test_handoff_confirmado_continua_aceitando_a_transferencia():
    handoff = ToolMessage(content=H.SUCESSO_DO_HANDOFF, tool_call_id="h", name="request_human_agent")
    for frase in AS_QUATRO_FRASES:
        assert H.guardar_a_verdade_do_handoff(frase, [handoff]) == frase


def test_as_respostas_honestas_nao_se_auto_reescrevem():
    assert not H.afirma_transferencia(H.RESPOSTA_HONESTA_DO_ACIONAMENTO)
    assert not H.afirma_transferencia(H.RESPOSTA_HONESTA)


# ===========================================================================
# 3 · O CARIMBO MORA NO PRODUTOR — se ele mudar lá, este guarda fica vermelho
# ===========================================================================
def test_os_carimbos_existem_nos_produtores_reais():
    fonte = (RAIZ / "app" / "agents" / "tools" / "insurer_dispatch_tool.py").read_text(encoding="utf-8")
    for carimbo in H.CARIMBOS_DE_ACIONAMENTO["insurer_dispatch"]:
        assert carimbo in fonte, carimbo
    from app.agents.tools.portal_params import format_result
    aberto = format_result(PORTAL_ABERTO)
    parado = format_result(PORTAL_PARADO_COM_NUMERO)
    assert any(c in aberto for c in H.CARIMBOS_DE_ACIONAMENTO["portal_action"])
    assert any(c in parado for c in H.CARIMBOS_DE_ACIONAMENTO["portal_action"])
    # e o caminho que NÃO abriu nada não carrega carimbo nenhum
    assert not any(c in format_result(PORTAL_FALHOU) for c in H.CARIMBOS_DE_ACIONAMENTO["portal_action"])
