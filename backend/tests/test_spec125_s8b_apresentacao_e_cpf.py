# -*- coding: utf-8 -*-
"""SPEC-125 S8b — a apresentação que ATENDE o pedido + o CPF que parecia celular.

Motor REAL (CLAUDE.md §9.4): `o_fim_do_atendimento.bloco_de_quem_fala` /
`linha_da_apresentacao` / `so_cumprimentou` / `a_resposta_se_apresenta`,
`quem_e_o_segurado.documentos_ditos` / `montar` / `bloco_para_o_prompt` e
`attendance_ficha.bloco_para_o_prompt`. Cada regra tem LINHA DE CONTROLE e
MUTAÇÃO que deixa o guarda vermelho (§9.3/§9.5). Dados 100% fictícios: o CPF
é gerado (DV válido), a corretora e o agente são sintéticos (§13.9).

📊 Linha de base (`docs/canon/reports/SPEC-125-LINHA-DE-BASE.md`): 24 de 36
primeiras respostas com "Como posso ajudar?" a quem já disse o pedido; a causa
era a linha "apresente-se assim: '… Como posso ajudar?' — e só".
"""
from __future__ import annotations

import pytest

from app.agents import quem_e_o_segurado as Q
from app.agents.tools.insurer_dispatch_tool import documento_br_valido
from app.services import attendance_ficha as FI
from app.services import o_fim_do_atendimento as F

AGENTE = "Aurora"
CORRETORA = "Corretora Sintetica"
CPF = "52998224725"            # fictício, DV válido, 3º dígito 9 (cara de celular)
CELULAR_SEM_DV = "47999990000"  # celular fictício, DV de CPF inválido


def _linha(mensagem):
    bloco, ident = F.bloco_de_quem_fala(
        assunto_novo=True, identidade={}, agent_name=AGENTE, corretora=CORRETORA,
        mensagem_do_segurado=mensagem)
    linha = next(l for l in bloco.splitlines() if l.startswith("APRESENTAÇÃO:"))
    return linha, ident


# ============================ 1 · a apresentação ============================ #
def test_com_pedido_na_primeira_mensagem_a_instrucao_segue_para_o_pedido():
    linha, ident = _linha("oi, bati o carro e preciso de guincho")
    assert "e só" not in linha, linha
    assert "Como posso ajudar" not in linha, linha          # nenhum exemplo com a pergunta
    assert "NA MESMA mensagem" in linha and "NÃO pergunte" in linha, linha
    # T23 intacto: continua se apresentando, com a marca que o motor procura de volta
    assert "assistente virtual da %s" % CORRETORA in linha, linha
    assert ident.get("apresentacao_pendente_em"), ident


def test_CONTROLE_oi_pergunta_como_ajudar():
    linha, ident = _linha("oi")
    assert 'Como posso ajudar?"' in linha, linha
    assert "NÃO pergunte" not in linha and "e só" not in linha, linha
    assert ident.get("apresentacao_pendente_em"), ident
    # as duas CONSEGUEM ser diferentes (§9.3)
    assert linha != _linha("oi, preciso de guincho")[0]


def test_sem_a_mensagem_a_instrucao_e_condicional_e_nunca_e_so():
    linha, _ = _linha(None)
    assert "e só" not in linha, linha
    assert "Se ele já disse o que precisa" in linha and "só se ele" in linha, linha


@pytest.mark.parametrize("msg,esperado", [
    ("oi", True), ("Oiii", True), ("Bom dia!", True), ("boa tarde, tudo bem?", True),
    ("Olá 👋", True), ("e aí, tudo certo?", True),
    ("bom dia, meu carro quebrou", False), ("preciso de guincho", False),
    ("oi, quero a segunda via do boleto", False), ("Bom dia! Chaveiro, por favor", False),
    (None, None), ("", None), ("📷", None), ("   ", None),
])
def test_so_cumprimentou_o_motor(msg, esperado):
    assert F.so_cumprimentou(msg) is esperado


def test_T23_quem_e_quando_nao_mudam_ja_apresentado_fica_calado_mesmo_com_pedido():
    ident = {"apresentado_em": "2026-10-01T10:00:00+00:00", "nome_da_apresentacao": AGENTE}
    bloco, _ = F.bloco_de_quem_fala(assunto_novo=False, identidade=ident, agent_name=AGENTE,
                                    corretora=CORRETORA, mensagem_do_segurado="preciso de guincho")
    assert "NÃO se apresente" in bloco, bloco
    ident["nome_da_apresentacao"] = "Outro Nome"
    bloco2, _ = F.bloco_de_quem_fala(assunto_novo=True, identidade=ident, agent_name=AGENTE,
                                     corretora=CORRETORA, mensagem_do_segurado="preciso de guincho")
    assert "mudou de nome" in bloco2, bloco2


def test_a_resposta_que_segue_a_nova_instrucao_ainda_marca_a_apresentacao():
    resposta = ("Oi! Aqui é a %s, assistente virtual da %s. Já vou ver o guincho "
                "para você — o carro está num lugar seguro?" % (AGENTE, CORRETORA))
    assert F.a_resposta_se_apresenta(resposta, agent_name=AGENTE)


def test_MUTACAO_a_regua_que_sempre_diz_cumprimento_deixa_o_guarda_vermelho(monkeypatch):
    monkeypatch.setattr(F, "so_cumprimentou", lambda _m: True)
    linha, _ = _linha("oi, bati o carro e preciso de guincho")
    assert "Como posso ajudar" in linha     # o guarda de cima ficaria VERMELHO


# ====================== 2 · o CPF que parecia celular ======================= #
def test_os_dados_ficticios_conseguem_ser_diferentes():
    assert documento_br_valido(CPF) and CPF[2] == "9"
    assert not documento_br_valido(CELULAR_SEM_DV)


@pytest.mark.parametrize("texto", [
    CPF, "segue: %s" % CPF, "meu cpf é %s" % CPF, "%s, celular %s" % (CPF, CELULAR_SEM_DV),
    "meu celular %s e o documento %s" % (CELULAR_SEM_DV, CPF),
])
def test_onze_digitos_com_dv_valido_e_cpf_mesmo_com_cara_de_celular(texto):
    assert Q.documentos_ditos(texto) == [CPF]


@pytest.mark.parametrize("texto", [
    "meu celular é %s" % CPF, "zap %s" % CPF, "%s é meu whatsapp" % CPF,
    "telefone: %s" % CPF,
])
def test_ambiguo_de_verdade_dito_como_telefone_nao_e_cpf(texto):
    assert Q.documentos_ditos(texto) == []


def test_CONTROLE_celular_sem_dv_continua_fora():
    assert Q.documentos_ditos(CELULAR_SEM_DV) == []
    assert Q.documentos_ditos("meu cpf %s" % CELULAR_SEM_DV) == []


def test_o_fio_o_cpf_solto_vira_confirmacao_no_bloco():
    quem = Q.montar(historico=[{"role": "user", "content": CPF,
                                "created_at": "2026-10-01T10:00:00+00:00"}])
    assert quem["cpf"] == CPF and quem["perguntar_cpf"] is False


def test_MUTACAO_voltar_a_regra_da_cara_de_celular_deixa_o_guarda_vermelho(monkeypatch):
    monkeypatch.setattr(Q, "_dito_como_telefone", lambda s, i, f: s[i + 2] == "9")
    assert Q.documentos_ditos(CPF) == []     # o guarda de cima ficaria VERMELHO


# ================= 3 · T19 — inteiro ao modelo, mascarado a ele ============== #
def test_o_bloco_da_s3_manda_mostrar_so_o_final():
    texto = Q.bloco_para_o_prompt({"cpf": CPF, "cpfs_distintos": 1})
    assert CPF in texto                                  # as ferramentas precisam dele
    assert 'a ele, só "final 4725"' in texto, texto


def test_a_ficha_com_cpf_cru_manda_mostrar_so_o_final_e_a_placa_nao():
    ficha = {"fase": FI.FASE_COLETA,
             "confirmados": {"titular_cpf": CPF, "veiculo_placa": "ABC1D23"}}
    texto = FI.bloco_para_o_prompt(ficha)
    linha_cpf = next(l for l in texto.splitlines() if CPF in l)
    linha_placa = next(l for l in texto.splitlines() if "ABC1D23" in l)
    assert 'a ele, só "final 4725"' in linha_cpf, texto
    assert "final" not in linha_placa, texto            # CONTROLE: só documento ganha a regra
