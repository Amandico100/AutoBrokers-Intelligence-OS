# -*- coding: utf-8 -*-
"""SPEC-124 F1 — a POLÍTICA do destravador no portal: a MESMA régua do WhatsApp (D1) e o NUNCA (D2).

Puro: nenhum banco, nenhum modelo. As opções das paradas são as REAIS do API-first (as 27 UFs que o
portal devolve; as duas opções do reparo escritas pelo motor em `vidros_apifirst._fase_materializar`).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.agents.tools import portal_params as PP  # noqa: E402
from app.services import destravador as DT  # noqa: E402
from portal_worker.journeys import vidros_estado as ST  # noqa: E402

UFS = sorted(["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB",
              "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"])
# 💭 caso fictício (nenhum dado real)
CASO = {"insurer_name": "LIBERTY SEGUROS S/A", "cpf_cnpj": "00000000000", "placa": "AAA0A00",
        "dano": {"peca": "para-brisa", "como": "pedra na estrada", "onde": "urbano"},
        "local": {"estado": "SC", "cidade_servico": {"uf": "ZZ", "cidade": "Cidade Exemplo"}},
        "especificos": {}, "contato": {"telefone": "4800000000"}}
PARADA_UF = {"stage": "uf_desconhecida", "operacao": "responder", "slot": "cidade_servico",
             "opcoes": UFS, "pergunta": "", "mensagem": ""}
PARADA_REPARO = {"stage": "decidir_reparo", "operacao": "responder", "slot": "aceita_reparo",
                 "opcoes": ["tentar o reparo", "trocar a peca"], "pergunta": "", "mensagem": ""}


def P(valor, classe="responder_com_dado", acao="RESPONDER", nota=95):
    return DT.Proposta(classe=classe, acao=acao, valor=valor, nota=nota, motivo="m")


def decide(prop, parada=PARADA_UF, **k):
    return DT.decidir_parada_do_portal(prop, parada, CASO, **k)


# ── a tabela cobre o mapa fechado ────────────────────────────────────────────────
def test_toda_parada_que_o_segurado_responde_tem_classe_na_tabela():
    faltam = [s for s in PP.ESTAGIOS_QUE_O_SEGURADO_RESPONDE if s not in DT.CLASSE_DA_PARADA_DO_PORTAL]
    assert faltam == []
    for st, (etapa, acao) in ST.ETAPA_DA_PARADA.items():
        if acao.startswith("responder"):
            assert st in DT.CLASSE_DA_PARADA_DO_PORTAL, st
    for st, cl in DT.CLASSE_DA_PARADA_DO_PORTAL.items():
        assert cl in DT.CLASSES
        if cl == "nunca_sozinho":
            assert DT.NUNCA_DA_PARADA_DO_PORTAL[st][0] in DT.NUNCA_SOZINHO   # a MESMA lista do WhatsApp


# ── RESPONDER COM DADO: só o dado do caso, e só se está na lista do portal ─────────
def test_uf_do_caso_na_lista_responde():
    d = decide(P("sc"))
    assert (d.acao, d.classe, d.valor) == ("RESPONDER", "responder_com_dado", "SC")
    assert DT.resposta_do_portal("uf_desconhecida", "cidade_servico", d.valor, CASO) == {
        "cidade_servico": {"uf": "SC", "cidade": "Cidade Exemplo"}}


def test_uf_da_lista_que_nao_e_do_caso_vira_pergunta():
    d = decide(P("PR"))
    assert d.acao == "PERGUNTAR_AO_SEGURADO" and d.proibicao == "deduzir_sem_calibracao"


def test_valor_fora_da_lista_nunca_vai_ao_portal():
    d = decide(P("Santa Catarina"))
    assert d.acao != "RESPONDER"


def test_a_mesma_resposta_com_que_o_portal_parou_nao_age():
    caso = {**CASO, "local": {"estado": "SC", "cidade_servico": {"uf": "SC", "cidade": "Cidade Exemplo"}}}
    d = DT.decidir_parada_do_portal(P("SC"), PARADA_UF, caso)
    assert d.acao == "PERGUNTAR_AO_SEGURADO" and d.proibicao == "resposta_sem_formato_ou_repetida"


# ── NUNCA (D2) ───────────────────────────────────────────────────────────────────
def test_NUNCA_decidir_reparo_pelo_codigo_sem_modelo():
    d = decide(None, PARADA_REPARO)
    assert d is not None and d.acao == "PERGUNTAR_AO_SEGURADO" and d.proibicao == "aceite_de_custo"
    # e com a proposta mais agressiva possível, a mesma coisa
    d2 = decide(P("tentar o reparo", classe="conduzir", nota=100), PARADA_REPARO)
    assert d2.acao == "PERGUNTAR_AO_SEGURADO" and d2.proibicao == "aceite_de_custo"


@pytest.mark.parametrize("stage,acao", [("pronto_para_agendar", "PERGUNTAR_AO_SEGURADO"),
                                        ("horario_indisponivel", "PERGUNTAR_AO_SEGURADO"),
                                        ("coverage_absent", "PESSOA"), ("maybe_committed", "PESSOA"),
                                        ("pronto_para_materializar", "PESSOA"),
                                        ("prioridade_nao_medida", "PESSOA")])
def test_NUNCA_da_tabela(stage, acao):
    d = decide(None, {"stage": stage, "operacao": "responder", "slot": "x", "opcoes": []})
    assert d.acao == acao and d.classe == "nunca_sozinho"


@pytest.mark.parametrize("valor,proibicao", [("aceito a franquia", "aceite_de_custo"),
                                             ("pode cobrar R$ 300", "aceite_de_custo"),
                                             ("cancelar o pedido", "cancelar_pedido"),
                                             ("desistir", "cancelar_pedido"),
                                             ("abrir sinistro", "abrir_sinistro"),
                                             ("SC 88123456", "inventar_dado")])
def test_NUNCA_sobre_o_valor(valor, proibicao):
    d = decide(P(valor))
    assert d.acao in ("PESSOA", "PERGUNTAR_AO_SEGURADO") and d.proibicao == proibicao


def test_NUNCA_mutacao_tirar_a_chave_solta_o_reparo_para_o_modelo():
    """`nunca=` é a MESMA alavanca do WhatsApp: sem `aceite_de_custo`, o código não decide mais sozinho."""
    sem = tuple(k for k in DT.NUNCA_SOZINHO if k != "aceite_de_custo")
    assert decide(None, PARADA_REPARO, nunca=sem) is None


# ── a parada técnica e o "só o segurado sabe" ───────────────────────────────────
def test_tecnica_nao_destrava_e_perguntar_e_do_segurado():
    assert decide(None, {"stage": "catalogo_indisponivel", "operacao": "reler", "slot": "", "opcoes": []}
                  ).acao == "PESSOA"
    d = decide(None, {"stage": "cidade_sem_rede", "operacao": "responder", "slot": "cidade_servico",
                      "opcoes": []})
    assert d.acao == "PERGUNTAR_AO_SEGURADO" and d.classe == "perguntar_ao_segurado"


def test_saida_invalida_e_pessoa():
    assert decide(DT.ler_destravamento("isto não é json")).acao == "PESSOA"


# ── D1: o MESMO núcleo nos dois canais ───────────────────────────────────────────
def test_os_dois_canais_passam_pelo_mesmo_nucleo(monkeypatch):
    chamadas = []
    real = DT.regua_do_nucleo

    def espia(*a, **k):
        chamadas.append(k.get("tem_opcoes"))
        return real(*a, **k)

    monkeypatch.setattr(DT, "regua_do_nucleo", espia)
    decide(P("SC"))
    n_portal = len(chamadas)
    assert n_portal == 1
    # o WhatsApp: uma tela de menu real do acervo (o fio da SPEC-123) chega à régua pelo mesmo nome
    from tests.test_spec123_destravador_fio import TELA_SERVICOS, REF_YELUM_RES

    sessao = {"playbook_ref": REF_YELUM_RES, "subservice": "", "slots": {}, "client_phone": "5500000000000",
              "transcript": []}
    DT.decidir_destravamento(P("Encanador", classe="deduzir"), sessao, TELA_SERVICOS)
    assert len(chamadas) == n_portal + 1


def test_deduzir_calibrado_exige_segunda_opiniao_de_OUTRO_provedor(monkeypatch):
    """Quando a calibração religar (`DEDUZIR_AUTONOMO_CALIBRADO`), o portal herda a régua inteira."""
    monkeypatch.setattr(DT, "DEDUZIR_AUTONOMO_CALIBRADO", True)
    parada = {"stage": "motivo_ambiguo", "operacao": "responder", "slot": "como",
              "opcoes": ["Pedra", "Vandalismo"], "pergunta": "", "mensagem": ""}
    prop = P("Pedra", classe="deduzir", nota=90)
    assert decide(None, parada) is None                       # agora o modelo propõe
    d = decide(prop, parada, provedor="openai", pedir_segunda=True)
    assert d.proibicao == "precisa_segunda_opiniao"
    mesma = {"provedor": "openai", "acao": "RESPONDER", "valor": "Pedra"}
    assert decide(prop, parada, provedor="openai", segunda_opiniao=mesma).proibicao == \
        "segunda_opiniao_do_mesmo_provedor"
    outra = {"provedor": "anthropic", "acao": "RESPONDER", "valor": "Vandalismo"}
    assert decide(prop, parada, provedor="openai", segunda_opiniao=outra).proibicao == "segunda_opiniao_discordou"
    ok = {"provedor": "anthropic", "acao": "RESPONDER", "valor": "pedra"}
    d = decide(prop, parada, provedor="openai", segunda_opiniao=ok)
    assert (d.acao, d.valor, ok["concordou"]) == ("RESPONDER", "Pedra", True)
    assert decide(P("Pedra", classe="deduzir", nota=69), parada, provedor="openai").proibicao == \
        "nota_abaixo_do_limiar"


def test_a_frase_do_diario_fala_de_portal_e_sem_nome_de_variavel():
    d = decide(P("SC"))
    frase = DT._frase_do_portal("yelum", PARADA_UF, d)
    assert frase.startswith("No portal da loja de vidros") and "estado (UF)" in frase
    assert "_" not in frase.split("(", 1)[0]
    assert DT.ACAO_NO_DIARIO_DO_PORTAL["RESPONDER"] == "respondeu_portal"
    from app.services.diario_de_decisoes import ACOES

    assert "respondeu_portal" in ACOES and "respondeu_ura" in ACOES
