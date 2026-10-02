# -*- coding: utf-8 -*-
r"""SPEC-125 · AJUSTE ZN — os quatro defeitos que o laudo de confirmação nº 2 achou no conserto Z.

```
Z-N1  o "sim" com complemento NEUTRO aciona ("Sim, vou esperar aqui", "Sim, o endereço não
      mudou", "sim, depois me passa a previsão", "Sim, amanhã de manhã" quando a pergunta disse
      amanhã); só a OBJEÇÃO ao pedido e o ADIAMENTO do próprio acionamento recusam
Z-N2  a máscara T19: o rótulo DEPOIS do número não desmascara o CPF de um resumo em lista; e o
      documento do CASO mascara sempre, mesmo chamado de "protocolo"
Z-N3  o dado que faltava + "pode mandar" em dois balões é confirmação
Z-N4  "Quer que eu confirme se cobre guincho?" → "sim" não é o ok do acionamento
```

Cada bloco: REPRODUÇÃO (vermelha em `fd52568`) e LINHA DE CONTROLE (§9.2). O que se afirma é o
MOTOR (`confirmacao_comprovada`, `mascarar_documentos_na_saida`, `nodes._sem_documento_inteiro`)
sobre o texto do laudo e das conversas gravadas da RODADA FINAL (§9.4).

⛔ Sem rede, sem banco, sem LLM. CPF de teste `52998224725` (sintético); nenhum nome de corretora.

Rodar (de `backend/`):
    PYTHONIOENCODING=utf-8 .venv/Scripts/python -m pytest tests/test_spec125_ajuste_zn.py -q -p no:cacheprovider
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

from langchain_core.messages import AIMessage, HumanMessage  # noqa: E402

import app.agents.tools.insurer_dispatch_tool as IT  # noqa: E402
from app.agents.quem_e_o_segurado import documentos_do_caso, mascarar_documentos_na_saida  # noqa: E402
from test_spec125_conserto_z import _ate_o_acionamento, _falas_do_c4, _gravada  # noqa: E402

CPF = "52998224725"                      # DV válido (sintético)
CPF_QUE_E_PROTOCOLO = "12345678909"      # fecha o DV de CPF — o protocolo do laudo
RESUMO = "Guincho para a placa final 0A91, da Rua Um, 100 até a Oficina Dois, contato neste número."
PEDIDO = {"subservice": "guincho", "local_atual": "Rua Um, 100, Florianopolis",
          "local_destino": "Oficina Dois", "veiculo_placa": "AAA0A91"}
ENCANADOR = "Encanador para a Rua das Flores, 50, amanhã de manhã. Confirma?"
PEDIDO_ENCANADOR = {"subservice": "encanador", "local_rua": "Rua das Flores", "endereco_numero": "50"}


def _ok(falas, pedido=PEDIDO) -> bool:
    return IT.confirmacao_comprovada(falas, pedido)["comprovada"]


# ===========================================================================
# Z-N1 · o complemento neutro não pesa
# ===========================================================================
@pytest.mark.parametrize("sim", [
    "Sim, vou esperar aqui na frente", "Pode mandar, vou esperar no carro",
    "Sim, o endereço não mudou", "sim, depois me passa a previsão",
    "Sim, pode sim, mas o carro é automático", "sim, nada mudou", "Pode sim, mas rápido por favor"])
def test_zn1_reproducao_o_sim_com_complemento_neutro_aciona(sim):
    """🔴 (vermelho em fd52568: `_RX_OBJECAO_DO_SEGURADO` casava esperar/mudou/depois/mas)."""
    assert _ok([("agente", RESUMO + " Posso acionar?"), ("segurado", sim)]), sim


def test_zn1_reproducao_residencial_agendado_a_data_repetida_e_a_resposta():
    """🔴 (vermelho em fd52568) o segurado que repete o horário da pergunta não acionava nunca."""
    falas = [("agente", ENCANADOR), ("segurado", "Sim, amanhã de manhã")]
    assert _ok(falas, PEDIDO_ENCANADOR)
    # CONTROLE: o "sim" seco sempre passou
    assert _ok([("agente", ENCANADOR), ("segurado", "Sim")], PEDIDO_ENCANADOR)


@pytest.mark.parametrize("respostas", [
    ["ta bom, depois eu peço"], ["sim, mas o destino é outro"], ["sim, mas não é guincho"],
    ["agora não"], ["Sim, amanhã"], ["sim, depois"], ["sim, mas leva pra concessionária"],
    ["sim, mas vou pagar alguma coisa?"], ["sim, mas a rua é a Nove"], ["mudou o endereço"],
    ["depois vejo isso", "sim"], ["vou pensar"], ["espera"], ["sim, deixa pra depois"],
    ["ok", "na verdade a rua é outra"], ["Sim, na sexta"]])
def test_zn1_controle_objecao_e_adiamento_continuam_recusados(respostas):
    """CONTROLE: os do conserto Z (C4: "ta bom, depois eu peço") e a data que a pergunta NÃO disse."""
    falas = [("agente", RESUMO + " Posso acionar?")] + [("segurado", r) for r in respostas]
    assert not _ok(falas), respostas


def test_zn1_controle_amanha_que_a_pergunta_nao_disse_e_adiamento():
    """A MESMA resposta, "Sim, amanhã de manhã", vira adiamento quando a pergunta é de AGORA."""
    falas = [("agente", "Encanador para a Rua das Flores, 50, agora. Confirma?"),
             ("segurado", "Sim, amanhã de manhã")]
    assert not _ok(falas, PEDIDO_ENCANADOR)


def test_zn1_controle_o_c4_real_continua_recusado():
    _cen, falas, args = _falas_do_c4()
    assert not _ok(falas, args) and not _ok(falas, None)


# ===========================================================================
# Z-N3 · dois balões
# ===========================================================================
@pytest.mark.parametrize("balões", [["Oficina do Ze", "pode mandar"], ["João", "sim pode"],
                                    ["Oficina do Ze", "Rua Um, 100", "ok"]])
def test_zn3_reproducao_o_dado_e_o_sim_em_dois_baloes_acionam(balões):
    """🔴 (vermelho em fd52568: "a resposta seguinte não foi o sim")."""
    falas = [("agente", RESUMO + " Para onde levamos o carro? Posso acionar?")]
    falas += [("segurado", b) for b in balões]
    assert _ok(falas), balões


@pytest.mark.parametrize("balões", [["Oficina do Ze"], ["Oficina do Ze", "obrigado kkk"],
                                    ["Oficina do Ze", "não"], ["pode mandar", "espera, a rua é outra"]])
def test_zn3_controle_sem_sim_ou_com_nao_nao_aciona(balões):
    falas = [("agente", RESUMO + " Posso acionar?")] + [("segurado", b) for b in balões]
    assert not _ok(falas), balões


# ===========================================================================
# Z-N4 · pergunta de OUTRA coisa
# ===========================================================================
def test_zn4_reproducao_a_pergunta_de_cobertura_nao_e_ok_de_acionar():
    """🔴 (vermelho em fd52568) o "sim" a "quer que eu confirme se cobre guincho?" acionava."""
    pedido = {"subservice": "guincho", "local_atual": "Rua Sete, 100"}
    falas = [("agente", "Quer que eu confirme se a sua apólice cobre guincho?"), ("segurado", "sim"),
             ("agente", "Cobre! Para acionar me diga onde está o carro."),
             ("segurado", "na Rua Sete, 100")]
    assert not _ok(falas, pedido)


def test_zn4_reproducao_confirmar_so_a_placa_nao_e_ok_de_acionar():
    assert not _ok([("agente", "Confirma que é o carro de placa final 0A91?"), ("segurado", "isso")])


@pytest.mark.parametrize("pergunta", [
    "Confirma o guincho da Rua Um, 100 para a Oficina Dois?",           # fraca + 2 partes
    "Quer que eu acione o guincho agora?",                               # forte + 1 parte
    "Confirma o guincho para a placa final 0A91?",                       # fraca + serviço + placa
    "Vou solicitar o guincho agora. Está tudo certo? Responda sim para eu seguir.",
    RESUMO + " Seguimos?"])
def test_zn4_controle_o_resumo_do_acionamento_continua_valendo(pergunta):
    assert _ok([("agente", pergunta), ("segurado", "sim")]), pergunta


def test_zn4_controle_lugar_de_4_letras_e_numero_da_casa_contam():
    """📊 C8 do corpus: "Confirma: guincho da Rua Sete 100 para a Rua Nove 20?" — com a régua
    das duas partes, "sete"/"nove" (4 letras) e "100" precisam contar como o lugar."""
    pedido = {"subservice": "guincho", "local_atual": "Rua Sete 100", "local_destino": "Rua Nove 20"}
    assert _ok([("agente", "Confirma: guincho da Rua Sete 100 para a Rua Nove 20?"), ("segurado", "sim")],
               pedido)


def test_zn4_controle_pedido_so_com_o_servico_basta_o_servico():
    """O pedido que só traz o serviço (sem lugar nem placa) não pode exigir duas partes."""
    assert _ok([("agente", "Confirma o chaveiro na Rua das Acácias 120, Centro?"), ("segurado", "sim")],
               {"subservice": "chaveiro"})
    # e sem o serviço a placa sozinha continua não valendo
    assert not _ok([("agente", "Confirma que é o carro de placa final 0A91?"), ("segurado", "isso")], None)


# ===========================================================================
# replay da RODADA FINAL — os 11 acionamentos com dados_confirmados=true
# ===========================================================================
@pytest.mark.parametrize("chave,tentativa,esperado", [
    ("conv-c2-dado-da-apolice", 1, True), ("conv-c2-dado-da-apolice", 2, True),
    ("conv-c3-repeticao-endereco-cidade", 2, True),
    ("conv-c11-telefone-conhecido", 1, True), ("conv-c11-telefone-conhecido", 2, True),
    ("conv-c13-acionamento-confirmado", 1, False),    # o 2º "sim velho" do laudo nº 2
    ("conv-c13-acionamento-confirmado", 2, True),
    ("conv-r1-rajada-5-frases", 1, True), ("conv-r1-rajada-5-frases", 2, True),
    ("conv-c4-conversa-longa", 1, False), ("conv-c4-conversa-longa", 2, False)])
def test_replay_da_rodada_final_separa_os_falsos_dos_legitimos(chave, tentativa, esperado):
    falas, args = _ate_o_acionamento(_gravada(chave, tentativa))
    assert _ok(falas, args) is esperado, (chave, tentativa, falas[-3:])


# ===========================================================================
# Z-N2 · a máscara do CPF no resumo
# ===========================================================================
@pytest.mark.parametrize("frase", [
    f"Confirma os dados: {CPF}, apólice 1234567, placa ABC1D23?",
    f"Dados: {CPF} (pedido de guincho)",
    f"o titular {CPF}, pedido de guincho para a Rua X",
    f"Confirma os dados do pedido: {CPF}?",
    f"Guincho para a Rua Um, contato neste número, titular {CPF}. Posso acionar?",
    f"{CPF}, apólice 1234567"])
def test_zn2_reproducao_o_cpf_do_resumo_em_lista_sai_mascarado(frase):
    """🔴 (vermelho em fd52568: o rótulo DEPOIS da vírgula e o artigo "os" desmascaravam)."""
    saida = mascarar_documentos_na_saida(frase)
    assert CPF not in saida and "final 4725" in saida, saida


@pytest.mark.parametrize("frase", [
    f"protocolo {CPF_QUE_E_PROTOCOLO}", f"O número {CPF_QUE_E_PROTOCOLO} é o seu protocolo.",
    f"{CPF_QUE_E_PROTOCOLO} (protocolo da seguradora)", f"Protocolo: {CPF_QUE_E_PROTOCOLO}",
    f"Anote: **{CPF_QUE_E_PROTOCOLO}** é o número do atendimento.",
    f"Seu protocolo é {CPF_QUE_E_PROTOCOLO}", f"OS {CPF_QUE_E_PROTOCOLO}",
    f"me liga no {CPF_QUE_E_PROTOCOLO}"])
def test_zn2_controle_o_protocolo_rotulado_continua_exato(frase):
    """CONTROLE (T6): o número rotulado como protocolo/atendimento sai EXATO."""
    assert mascarar_documentos_na_saida(frase) == frase


@pytest.mark.parametrize("frase", [
    f"protocolo {CPF}", f"O número {CPF} é o seu protocolo.", f"{CPF} (protocolo da seguradora)"])
def test_zn2_o_cpf_do_caso_mascara_mesmo_rotulado_de_protocolo(frase):
    """Se o número FOR o CPF do caso, o rótulo não o salva."""
    assert mascarar_documentos_na_saida(frase) == frase                   # sem a lista: regra do texto
    saida = mascarar_documentos_na_saida(frase, [CPF])
    assert CPF not in saida and "final 4725" in saida, saida
    # CONTROLE: outro número rotulado continua exato com a lista do caso
    outro = frase.replace(CPF, CPF_QUE_E_PROTOCOLO)
    assert mascarar_documentos_na_saida(outro, [CPF]) == outro


def test_zn2_documentos_do_caso_nao_conta_o_que_ele_disse_ser_protocolo():
    assert documentos_do_caso([f"meu cpf é {CPF}", f"o protocolo é {CPF_QUE_E_PROTOCOLO}"]) == [CPF]


def test_zn2_pelo_no_de_saida_o_cpf_dito_pelo_segurado_nao_sai_como_protocolo():
    """O MOTOR do nó (`nodes._sem_documento_inteiro`): o CPF que o segurado ditou (e o dos
    argumentos da ferramenta) mascara mesmo quando o modelo o chama de "protocolo"."""
    import app.agents.nodes as N

    estado = {"agent_data": {"agent_role": "attendance"},
              "messages": [HumanMessage(content=f"meu cpf é {CPF}"),
                           AIMessage(content="", tool_calls=[{"name": "insurer_dispatch", "id": "t1",
                                                              "args": {"titular_cpf": "11144477735"}}])]}
    saida = N._sem_documento_inteiro(f"Seu protocolo é {CPF}.", estado)
    assert CPF not in saida and "final 4725" in saida, saida
    saida = N._sem_documento_inteiro("O número 11144477735 é o seu protocolo.", estado)
    assert "11144477735" not in saida and "final 7735" in saida, saida
    # CONTROLE: o protocolo de verdade (não é documento do caso) sai exato pelo mesmo nó
    frase = f"Seu protocolo é {CPF_QUE_E_PROTOCOLO}."
    assert N._sem_documento_inteiro(frase, estado) == frase
    # e ao CORRETOR nada muda
    corretor = {"agent_data": {"agent_role": "core"}, "messages": estado["messages"]}
    assert N._sem_documento_inteiro(f"Seu protocolo é {CPF}.", corretor) == f"Seu protocolo é {CPF}."
