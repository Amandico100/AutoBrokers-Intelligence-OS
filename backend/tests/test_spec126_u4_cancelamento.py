# -*- coding: utf-8 -*-
r"""SPEC-126 · U4 — O CANCELAMENTO depois de acionar vai a uma PESSOA, e a R9 com as falhas do laudo.

O FIO (dublê só na borda: banco, Redis, WhatsApp, destino do grupo, feed — a borda da SPEC-123)
================================================================================================
segurado num caso JÁ ACIONADO escreve "cancela o guincho"
→ `pos_acionamento.classificar_turno` → K3
→ `HumanHandoffTool._arun` REAL → `por_que_vai_direto_a_pessoa` → a entrada `cancelamento_pos_acionamento`
  de `_SEMPRE_DE_GENTE` (NUNCA a segunda chance — D4 do Founder, 02/10/2026)
→ `_avisar_suporte` → `o_grupo_so_o_que_importa.enviar_ao_grupo` (REAL) → o grupo DA corretora, com o dossiê:
  protocolo, seguradora, serviço, hora do acionamento e a frase dele.
E o texto ao segurado nunca diz "cancelei / está cancelado": nenhuma ferramenta cancela (o fiscal reescreve).

📊 VERMELHO ANTES (main fbdecec): "cancela o guincho" → `N` → segunda chance; e a ficha que o PRODUTO grava
(`attendance_ficha.fundir`: `acionamento.protocolo`, fase `acompanhando`) não era reconhecida como acionada
— `_e_pos_acionamento` só lia `dispatch_state`/`protocolo` no topo, chaves que nenhum escritor grava
(📊 02/10, 1.174 conversas: 0 com `dispatch_state`, 0 com `protocolo` no topo, 1 com `acionamento.protocolo`).

🔴 MUTAÇÃO (rodada uma vez, por cópia): tirar a entrada do `_SEMPRE_DE_GENTE` → o fio com o motivo em
prosa volta à segunda chance → VERMELHO.

⛔ Sem rede, sem banco real, sem LLM. Nomes/telefones/protocolos inventados; nenhum nome de corretora (§13.9).
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

from test_spec123_atendimento_segunda_chance import (  # noqa: E402,F401
    ENVIOS, X, _banco, _conversa, _diario, _linha, _pedir, borda)

from app.atendimento.pos_acionamento import classificar_turno  # noqa: E402

PROTOCOLO = "PR20261002"


def _ficha_do_produto():
    """A ficha como o PRODUTO a grava depois de um acionamento com protocolo — pelo escritor real
    (`attendance_ficha.fundir`, chamado por `nodes._gravar_ficha_do_turno`), nunca à mão."""
    from app.services.attendance_ficha import ficha_vazia, fundir

    f = fundir(ficha_vazia(), {"servico": "guincho", "seguradora": "seguradora exemplo",
                               "confirmados": {"local_atual": "Rua Teste 10"}})
    return fundir(f, {"acionamento": {"protocolo": PROTOCOLO}})


#: A ficha da BANCADA (o corpus N3 e os testes da 125) — a forma antiga continua valendo.
FICHA_DA_BANCADA = {"fase": "acionado", "subservice": "guincho", "dispatch_state": "monitoring",
                    "protocolo": "900000001", "seguradora": "seguradora exemplo"}


def _caso_acionado(cid, fala, ficha=None):
    b = _banco(_conversa(cid, preview=fala, ficha=ficha or _ficha_do_produto()))
    b.tabelas["messages"].append({"conversation_id": cid, "role": "user", "content": fala,
                                  "created_at": "2026-10-02T10:00:00+00:00"})
    return b


# ===========================================================================
# ① O TESTE DO FIO
# ===========================================================================
@pytest.mark.parametrize("motivo", [
    "o segurado pediu para cancelar o guincho",       # o que um modelo escreve (prosa)
    "cancelamento_pos_acionamento",                   # o código que o prompt v2 vai pedir
])
def test_o_fio_cancela_o_guincho_num_caso_acionado_vai_a_pessoa_com_o_dossie(borda, motivo):
    import app.agents.tools.human_handoff as H
    from app.agents.honestidade_do_handoff import SUCESSO_DO_HANDOFF

    fala = "cancela o guincho"
    assert classificar_turno([fala]) == "K3"
    cid = "c-u4-fio-01"
    b = _caso_acionado(cid, fala)

    r = _pedir(H, b, cid, motivo)
    assert r == SUCESSO_DO_HANDOFF, r                       # NUNCA a segunda chance
    assert not H.foi_segunda_chance(r)
    assert _linha(b, cid)["status"] == "HUMAN_REQUESTED"
    assert len(ENVIOS) == 1, ENVIOS
    alvo, dossie = ENVIOS[0]
    assert alvo == "grupo-de-teste@g.us"                    # o grupo DA corretora (o destino resolvido)
    assert PROTOCOLO in dossie
    assert "Seguradora Exemplo" in dossie
    assert "GUINCHO" in dossie
    assert "Acionado em" in dossie and "às" in dossie       # a hora do acionamento, no fuso da corretora
    assert "cancela o guincho" in dossie                    # a frase dele
    assert "CANCELAR" in dossie and "NÃO cancelou" in dossie
    d = _diario(b, cid)
    assert [l["acao"] for l in d] == ["chamou_pessoa"], d
    assert d[0]["classe"] == "nunca_sozinho"
    assert "cancelar" in d[0]["explicacao_para_gente"]


def test_o_fio_tambem_na_ficha_da_bancada(borda):
    import app.agents.tools.human_handoff as H
    from app.agents.honestidade_do_handoff import SUCESSO_DO_HANDOFF

    cid = "c-u4-fio-02"
    b = _caso_acionado(cid, "pode cancelar, ja resolvi", ficha=dict(FICHA_DA_BANCADA))
    assert _pedir(H, b, cid, "segurado não quer mais o serviço") == SUCESSO_DO_HANDOFF
    assert "900000001" in ENVIOS[0][1]
    assert "Acionado em: não registrado" in ENVIOS[0][1]     # sem hora escrita, não se inventa


def test_controle_antes_de_acionar_o_cancela_ganha_a_segunda_chance(borda):
    """CONTROLE: sem acionamento não há o que cancelar na seguradora — o agente resolve com o segurado
    (não aciona). Prova que o fio CONSEGUE dar diferente (§9.3)."""
    import app.agents.tools.human_handoff as H

    cid = "c-u4-fio-03"
    b = _caso_acionado(cid, "cancela o guincho", ficha={"fase": "coleta", "servico": "guincho"})
    assert _pedir(H, b, cid, "o segurado pediu para cancelar o guincho") == H.SEGUNDA_CHANCE_DO_HANDOFF
    assert ENVIOS == []


def test_controle_cancelar_a_vistoria_num_caso_acionado_nao_e_cancelamento(borda):
    import app.agents.tools.human_handoff as H

    cid = "c-u4-fio-04"
    b = _caso_acionado(cid, "preciso cancelar a vistoria e remarcar")
    assert classificar_turno(["preciso cancelar a vistoria e remarcar"]) == "C"
    assert _pedir(H, b, cid, "remarcar a vistoria") == H.SEGUNDA_CHANCE_DO_HANDOFF


# ===========================================================================
# ①b SPEC-126 U1 (2ª metade, P-125-02) — protocolo PENDENTE num caso acionado: a segunda chance
#     devolve o ESTADO, nunca a pessoa. Pela ferramenta real, na forma de ficha que o PRODUTO grava
#     hoje (📊 02/10: a única ficha acionada do banco tem `acionamento.protocolo = "agendamento"`).
# ===========================================================================
def _ficha_acionada_sem_protocolo():
    from app.services.attendance_ficha import ficha_vazia, fundir

    f = fundir(ficha_vazia(), {"servico": "guincho", "seguradora": "seguradora exemplo"})
    return fundir(f, {"acionamento": {"protocolo": "agendamento"}})


@pytest.mark.parametrize("motivo", [
    "ainda não tenho o protocolo",
    "aguardando o número do chamado da seguradora",
    "não sei quando o guincho chega",
    "aguardando o número do sinistro que a seguradora vai mandar",
    "o portal ainda não devolveu o protocolo",
])
def test_protocolo_pendente_num_caso_acionado_devolve_o_estado(borda, motivo):
    import app.agents.tools.human_handoff as H
    from app.agents.honestidade_do_handoff import afirma_transferencia

    cid = "c-u4-c13-01"
    b = _caso_acionado(cid, "e o protocolo?", ficha=_ficha_acionada_sem_protocolo())
    r = _pedir(H, b, cid, motivo)
    assert H.foi_segunda_chance(r), r
    assert "ESTADO ESCRITO" in r and "protocolo ainda não informado pela seguradora" in r
    assert "agendamento" not in r                      # a palavra não é protocolo
    assert "serviço guincho" in r and "Seguradora Exemplo" in r and "acionado em" in r
    assert "HANDOFF_OK" not in r and not afirma_transferencia(r)
    assert _linha(b, cid)["status"] == "open" and ENVIOS == []


@pytest.mark.parametrize("fala", [
    "to no acostamento e o guincho nao chegou",        # K1
    "isso é um absurdo",                               # K2
    "cancela o guincho",                               # K3 (o cancelamento novo)
    "quero falar com uma pessoa",                      # P
])
def test_controle_protocolo_pendente_com_r9_de_pessoa_vai_direto(borda, fala):
    import app.agents.tools.human_handoff as H
    from app.agents.honestidade_do_handoff import SUCESSO_DO_HANDOFF

    cid = "c-u4-c13-02"
    b = _caso_acionado(cid, fala, ficha=_ficha_acionada_sem_protocolo())
    assert _pedir(H, b, cid, "ainda não tenho o protocolo") == SUCESSO_DO_HANDOFF, fala


def test_controle_protocolo_pendente_antes_de_acionar_e_a_segunda_chance_de_sempre(borda):
    import app.agents.tools.human_handoff as H

    cid = "c-u4-c13-03"
    b = _caso_acionado(cid, "e o protocolo?", ficha={"fase": "coleta", "servico": "guincho"})
    assert _pedir(H, b, cid, "ainda não tenho o protocolo") == H.SEGUNDA_CHANCE_DO_HANDOFF


@pytest.mark.parametrize("motivo,esperado", [
    ("ainda não tenho o protocolo", True), ("aguardando previsão de chegada", True),
    ("sem corredor para esta seguradora", False), ("a URA travou antes do protocolo", False),
    ("o cliente quer falar com o corretor", False), ("dúvida sobre a franquia", False),
])
def test_o_que_e_so_andamento_pendente(motivo, esperado):
    from app.agents.tools.human_handoff import motivo_e_so_andamento_pendente

    assert motivo_e_so_andamento_pendente(motivo) is esperado, motivo


# ===========================================================================
# ② K3 — toda forma de cancelar o SERVIÇO, e o que NÃO pode pegar
# ===========================================================================
@pytest.mark.parametrize("fala", [
    "cancela o guincho", "Cancela!", "pode cancelar", "pode cancelar o chamado",
    "cancelem por favor", "cancele o pedido", "quero cancelar o guincho", "desiste", "desisto do guincho",
    "pode desistir", "não precisa mais do guincho", "nao preciso mais", "não vou mais precisar do reboque",
    "já resolvi, não manda", "ja consegui resolver aqui, nao precisa mandar ninguem",
    "nao manda mais o guincho", "não mande o prestador", "cancela a vistoria e o guincho tb",
    "quero o cancelamento do guincho", "desisti. demorou muito",
])
def test_k3_casa_toda_forma_de_cancelar_o_servico(fala):
    assert classificar_turno([fala]) == "K3", fala


@pytest.mark.parametrize("fala,esperado", [
    ("quero cancelar a vistoria", "C"),
    ("cancela a vistoria, prefiro outro dia", "C"),
    ("gostaria de cancelar o agendamento", "C"),
    ("preciso remarcar a vistoria", "C"),
    ("não precisa se preocupar", "N"),
    ("não cancela não, já chegou", "N"),
    ("não precisa cancelar", "N"),
    ("nao quero mais esperar, ja faz 3 horas", "K2"),
    ("eles nao mandaram o guincho ainda", "N"),
    ("o cancelamento da apolice ja saiu?", "N"),        # status, não pedido (📊 acervo 02/10)
    ("a apolice ja cancelou mesmo entao?", "N"),
    ("pode ser que entre em processo de cancelamento", "N"),
    ("entao eu nao preciso mais me preocupar, certo?", "N"),
    ("o prazo para nao cancelar o atendimento", "H"),
])
def test_k3_nao_come_o_que_nao_e_cancelar_o_servico(fala, esperado):
    assert classificar_turno([fala]) == esperado, fala


# ===========================================================================
# ③ AS FALHAS DO LAUDO DO JUIZ FINAL DA 125 (pend. 1 e 2) — cada uma com o par que não pode pegar
# ===========================================================================
@pytest.mark.parametrize("fala,esperado", [
    ("o guincheiro amassou meu carro", "K2"),
    ("o prestador amassou a porta do carro", "K2"),
    ("o prestador me cobrou 300 por fora", "K2"),
    ("o rapaz do guincho pediu 150 por fora pra levar", "K2"),
    ("vou processar a seguradora", "K2"),
    ("vou no procon", "K2"),
    ("já registrei uma reclamação no reclame aqui", "K2"),
    ("tô sozinha na rodovia à noite com duas crianças", "K1"),
    ("estou sozinho na estrada", "K1"),
    ("to com as criancas no acostamento", "K1"),
    ("preciso remarcar a vistoria e saber da indenização", "L"),
    ("meu filho tá passando mal", "P"),
])
def test_as_falhas_do_laudo_viram_o_rotulo_certo(fala, esperado):
    assert classificar_turno([fala]) == esperado, fala


@pytest.mark.parametrize("fala,esperado", [
    ("o guincho chegou, amassou nada nao, tudo certo", "N"),   # "amassou" sem o prestador como agente
    ("a franquia eu pago por fora?", "E"),                     # "por fora" sem cobrança do prestador
    ("vou mandar os documentos a noite", "B"),                 # "à noite" sem rodovia
    ("a vistoria e na rodovia, perto do posto", "C"),          # rodovia sem estar parado nela
    ("quero remarcar a vistoria", "C"),                        # C sozinho continua C
    ("meu filho vai levar o carro na oficina", "G"),           # "filho" sem urgência
    ("estamos concorrendo ao premio reclame aqui, vota?", "N"),  # 📊 acervo: o prêmio, não a queixa
    ("ele cuida de processos e procon", "N"),                  # 📊 acervo: lista, não ameaça
])
def test_controle_as_regras_novas_nao_pegam_o_vizinho(fala, esperado):
    assert classificar_turno([fala]) == esperado, fala


def test_a_urgencia_nas_falas_vai_direto_mesmo_antes_de_acionar():
    """'meu filho tá passando mal' só pesava no MOTIVO (`_MOTIVOS_DE_REGRA.vitima`); dito pelo segurado
    num caso sem acionamento, ganhava a segunda chance."""
    from app.agents.tools.human_handoff import por_que_vai_direto_a_pessoa

    caso = {"ficha_atendimento": {"fase": "coleta"}, "mensagens": ["meu filho tá passando mal"]}
    assert por_que_vai_direto_a_pessoa("o segurado tem uma dúvida", caso=caso)
    controle = {"ficha_atendimento": {"fase": "coleta"}, "mensagens": ["meu filho vai levar o carro"]}
    assert por_que_vai_direto_a_pessoa("o segurado tem uma dúvida", caso=controle) == ""


# ===========================================================================
# ④ O FISCAL DA HONESTIDADE — "cancelei" é AÇÃO, e nenhuma ferramenta cancela (T5)
# ===========================================================================
@pytest.mark.parametrize("frase", [
    "Pronto, cancelei o guincho.", "Já cancelei o pedido para você.", "O guincho está cancelado.",
    "Seu atendimento foi cancelado com sucesso!", "Prontinho, já está cancelado ✅",
    "Acabei de cancelar o chamado.", "Cancelamos o guincho, tudo certo.",
])
def test_o_fiscal_reescreve_quem_diz_que_cancelou(frase):
    from app.agents import honestidade_do_handoff as H

    saida = H.guardar_a_verdade_do_handoff(frase, [])
    assert saida != frase
    assert H.afirma_cancelamento(saida) is False, saida
    assert "não está cancelado" in saida.lower()


@pytest.mark.parametrize("frase", [
    "Ainda não está cancelado: vou chamar agora a pessoa da corretora para cancelar com a seguradora.",
    "O guincho só para quando ela confirmar.",
    "Quer que eu peça o cancelamento à equipe?",
    "Não cancelei nada, fique tranquilo.",
    "Se quiser cancelar, me avise.",
])
def test_controle_o_fiscal_nao_toca_o_que_nao_afirma_cancelamento(frase):
    from app.agents import honestidade_do_handoff as H

    assert H.guardar_a_verdade_do_handoff(frase, []) == frase


def test_o_fiscal_mantem_a_passagem_confirmada_e_tira_so_o_cancelamento():
    from langchain_core.messages import ToolMessage

    from app.agents import honestidade_do_handoff as H

    ok = ToolMessage(content=H.SUCESSO_DO_HANDOFF, tool_call_id="c1", name="request_human_agent")
    frase = "Já passei seu caso para a equipe. Também já cancelei o guincho."
    saida = H.guardar_a_verdade_do_handoff(frase, [ok])
    assert saida.startswith("Já passei seu caso para a equipe.")
    assert "cancelei" not in saida and "não está cancelado" in saida.lower()
