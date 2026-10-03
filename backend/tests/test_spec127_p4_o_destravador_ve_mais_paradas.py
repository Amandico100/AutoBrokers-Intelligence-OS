# -*- coding: utf-8 -*-
"""SPEC-127 P4 + P8 — o destravador do portal VÊ MAIS PARADAS e LÊ A TELA. Puro: nenhum banco, nenhum modelo.

O que se prova aqui (o fio pelo motor real está em `test_spec127_p4_o_fio_do_destravador_no_replay.py`):

P4-a  as paradas que o P1 (antes da fronteira) e o P2 (DOM) criaram têm CLASSE na tabela; `faltou_*`, a cidade,
      o perímetro e o relato são do SEGURADO (pergunta); oferta e reparo são NUNCA (`aceite_de_custo` → pergunta).
P4-b  `tipo_de_telefone_desconhecido` é CONDUZIDO pelo CÓDIGO (a opção que é o contrato), nunca pelo modelo; o
      tipo de OUTRO dono nunca; sem opção que seja o contrato → PESSOA (o segurado não sabe o código do portal).
P4-c  RESPONDER COM DADO sob OUTRA chave: a peça que `especificos` desambigua (com o veto de FAMÍLIA do worker) e a
      resposta do 80 % já dada (chave própria, igualdade, unanimidade; a etiquetada dele manda).
P4-d  P-124-15: `pergunta_<codigo>` aceita `_` e `-`. P-124-07: "Não sabe" nunca sai do destravador; a regex de
      cancelar é UMA (reusa a do WhatsApp).
P4-e  a CLASSE vem da TABELA — o modelo não promove uma parada (nem a NUNCA cuja chave a mutação tirou).
P8    a parada leva a TELA (título, campo, rótulos, opções reais, obrigatórios) nos dois caminhos, e o texto que o
      destravador lê a contém.

💭 Todos os dados abaixo são fictícios; as opções e os rótulos são os REAIS do portal (`tests/fixtures/vidros/`).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from app.agents.tools import portal_params as PP  # noqa: E402
from app.services import destravador as DT  # noqa: E402
from fixtures.vidros.maxpar_catalogos import TIPOS_TELEFONE  # noqa: E402
from fixtures.vidros.telas_dom import TELAS  # noqa: E402
from portal_worker.journeys import vidros_apifirst as AF  # noqa: E402
from portal_worker.journeys import vidros_estado as ST  # noqa: E402

#: 📊 o catálogo REAL de itens de uma apólice Yelum (a tela `TELA 50%` do intake, 30 itens)
CATALOGO = TELAS["yelum_parabrisa_50_peca_causa"]["mdselects"][0]["options"]
LANTERNAS = [o for o in CATALOGO if o.startswith("LANTERNA")]
#: 📊 as perguntas REAIS do 80 % (as telas do intake)
QUESTOES = {q["pergunta"].split(") ", 1)[-1]: q["opcoes"]
            for t in TELAS.values() for q in (t.get("questoes") or [])}
SENSOR = "O veiculo possui sensor de direção/mudança de faixa?"
LADO = "Qual o lado do item danificado?"

CASO = {"insurer_name": "LIBERTY SEGUROS S/A", "cpf_cnpj": "00000000000", "placa": "AAA0A00",
        "dano": {"peca": "lanterna", "como": "pedra", "onde": "urbano"},
        "local": {"estado": "SC", "cidade_servico": {"uf": "SC", "cidade": "Cidade Exemplo"}},
        "contato": {"tipo_telefone": "segurado"},
        "especificos": {"lanterna_posicao": "da frente"}}
OUTRA = {"provedor": "anthropic", "acao": "RESPONDER"}


def P(valor, classe="deduzir", nota=100, acao="RESPONDER"):
    return DT.Proposta(classe=classe, acao=acao, valor=valor, nota=nota, motivo="m")


def parada(stage, slot, opcoes, **k):
    return {"stage": stage, "operacao": "responder", "slot": slot, "opcoes": list(opcoes),
            "pergunta": k.get("pergunta", ""), "mensagem": "", "tela": k.get("tela", {}),
            "contrato": k.get("contrato", "")}


def decide(prop, par, caso=CASO, **k):
    return DT.decidir_parada_do_portal(prop, par, caso, **k)


# ═════════════════════════════════════════════════════════════════════════════
# P4-a — as paradas novas têm classe; o dado do segurado é dele; custo nunca
# ═════════════════════════════════════════════════════════════════════════════
NOVAS_DO_SEGURADO = ("faltou_peca", "faltou_como", "faltou_onde", "faltou_cidade_servico", "faltou_descricao",
                     "falta_cidade_servico", "perimetro_desconhecido", "descricao_curta")


def test_toda_parada_do_P1_e_do_P2_tem_classe_na_TABELA():
    from portal_worker import adaptive as AD

    do_p1 = [s for s, (_e, a) in ST.ETAPA_ANTES_DA_FRONTEIRA.items() if a.startswith("responder:")]
    do_dom = [st for st, acao in AD._PARADA_DO_SLOT.values()] + ["falta_cidade_servico"]
    faltam = [s for s in do_p1 + do_dom + list(PP.ESTAGIOS_ANTES_DA_FRONTEIRA)
              if s not in DT.CLASSE_DA_PARADA_DO_PORTAL]
    assert faltam == []
    for st, cl in DT.CLASSE_DA_PARADA_DO_PORTAL.items():
        assert cl in DT.CLASSES
        if cl == "nunca_sozinho":
            assert DT.NUNCA_DA_PARADA_DO_PORTAL[st][0] in DT.NUNCA_SOZINHO   # a MESMA lista do WhatsApp


@pytest.mark.parametrize("stage", NOVAS_DO_SEGURADO)
def test_o_dado_que_falta_e_do_SEGURADO_o_codigo_pergunta_sem_o_modelo(stage):
    par = parada(stage, "x", ["Urbano (Cidade)", "Rodoviário", "Não Sabe"])
    d = decide(None, par)
    assert (d.acao, d.classe, d.proibicao) == ("PERGUNTAR_AO_SEGURADO", "perguntar_ao_segurado", "so_o_segurado_sabe")
    # e a proposta mais agressiva do modelo não muda nada
    d2 = decide(P("Urbano (Cidade)", classe="conduzir"), par, provedor="openai",
                segunda_opiniao={**OUTRA, "valor": "Urbano (Cidade)"})
    assert d2.acao == "PERGUNTAR_AO_SEGURADO"


@pytest.mark.parametrize("stage,opcoes", [
    ("decidir_reparo", ["Sim, quero tentar o reparo", "Não, prefiro seguir com a troca"]),   # 📊 HTML TELA 5
    ("decidir_oferta", ["Quero o polimento do farol"])])
def test_reparo_e_oferta_NUNCA_sozinhos_vao_ao_segurado(stage, opcoes):
    d = decide(None, parada(stage, "aceita_reparo", opcoes))
    assert (d.acao, d.classe, d.proibicao) == ("PERGUNTAR_AO_SEGURADO", "nunca_sozinho", "aceite_de_custo")


@pytest.mark.parametrize("stage", ["cobertura_nao_marcada", "atendimento_aberto_existente"])
def test_cobertura_e_outro_atendimento_aberto_vao_a_PESSOA(stage):
    d = decide(None, {**parada(stage, "x", ["Vidros", "Roda"]), "operacao": "reler"})
    assert d.acao == "PESSOA" and d.classe == "nunca_sozinho"


# ═════════════════════════════════════════════════════════════════════════════
# P4-b — o tipo de telefone: CONDUZIR pelo código
# ═════════════════════════════════════════════════════════════════════════════
TIPOS_REAIS = [t["Descricao"] for t in TIPOS_TELEFONE]
TIPOS_RENOMEADOS = ["COMERCIAL", "RECADO", "CELULAR DO SEGURADO", "CELULAR CORRETOR", "RESIDENCIA SEGURADO"]


def test_tipo_de_telefone_vai_ao_destravador_e_nao_mais_ao_reler():
    assert ST.etapa_da_parada("tipo_de_telefone_desconhecido") == (ST.ETAPA_CONTATO, "responder:tipo_telefone")
    assert DT.CLASSE_DA_PARADA_DO_PORTAL["tipo_de_telefone_desconhecido"] == "conduzir"


def test_CONDUZIR_o_codigo_escolhe_a_opcao_do_CONTRATO_e_o_modelo_nem_e_chamado():
    par = parada("tipo_de_telefone_desconhecido", "tipo_telefone", TIPOS_RENOMEADOS)
    d = decide(None, par)
    assert (d.acao, d.classe, d.valor) == ("RESPONDER", "conduzir", "CELULAR DO SEGURADO")
    assert d.acao_do_modelo == "" and d.nota is None
    # o modelo propondo o tipo de OUTRO dono, com nota 100 e a 2ª opinião concordando: vale o do código
    d2 = decide(P("CELULAR CORRETOR", classe="conduzir"), par, provedor="openai",
                segunda_opiniao={**OUTRA, "valor": "CELULAR CORRETOR"})
    assert d2.valor == "CELULAR DO SEGURADO"
    assert DT.resposta_do_portal("tipo_de_telefone_desconhecido", "tipo_telefone", d.valor, CASO,
                                 opcoes=TIPOS_RENOMEADOS) == {"tipo_telefone": "CELULAR DO SEGURADO"}


def test_CONDUZIR_o_dono_corretora_e_outro_e_o_contrato_vem_do_CASO():
    caso = {**CASO, "contato": {"tipo_telefone": "corretora"}}
    par = parada("tipo_de_telefone_desconhecido", "tipo_telefone",
                 ["COMERCIAL", "CELULAR DO SEGURADO", "CELULAR DA CORRETORA (CORRETOR)"])
    assert decide(None, par, caso).valor == "CELULAR DA CORRETORA (CORRETOR)"


@pytest.mark.parametrize("opcoes", [
    ["COMERCIAL", "RECADO", "CELULAR CORRETOR"],                         # o contrato sumiu da lista
    ["CELULAR DO SEGURADO", "CELULAR SEGURADO WHATSAPP", "COMERCIAL"],   # duas candidatas
    []])
def test_CONDUZIR_sem_UMA_opcao_do_contrato_e_PESSOA_nunca_pergunta_ao_segurado(opcoes, monkeypatch):
    par = parada("tipo_de_telefone_desconhecido", "tipo_telefone", opcoes)
    d = decide(None, par)
    assert d.acao == "PESSOA" and d.proibicao == "o_codigo_nao_conduziu"
    # nem calibrado: o modelo + a 2ª opinião escolhendo o celular de OUTRO dono não passam
    monkeypatch.setattr(DT, "DEDUZIR_AUTONOMO_CALIBRADO", True)
    d2 = decide(P("CELULAR CORRETOR", classe="conduzir", nota=99), par, provedor="openai",
                segunda_opiniao={**OUTRA, "valor": "CELULAR CORRETOR"})
    assert d2.acao == "PESSOA"
    # ⚠️ o worker aplica a escolha só pela MESMA regra: o tipo de outro dono não passa nem lá
    tipos = [{"Codigo": i, "Descricao": o} for i, o in enumerate(opcoes)]
    assert AF._codigo_do_tipo_escolhido(tipos, "CELULAR CORRETOR", "CELULAR SEGURADO") is None


# ═════════════════════════════════════════════════════════════════════════════
# P4-c — RESPONDER COM DADO sob outra chave
# ═════════════════════════════════════════════════════════════════════════════
def test_a_peca_que_especificos_DESAMBIGUA_e_dado_do_caso():
    par = parada("peca_ambigua", "peca", LANTERNAS)
    d = decide(None, par)
    assert (d.acao, d.classe, d.valor) == ("RESPONDER", "responder_com_dado", "LANTERNA DIANTEIRA CONVENCIONAL")
    assert DT.resposta_do_portal("peca_ambigua", "peca", d.valor, CASO, opcoes=LANTERNAS) == \
        {"peca": "LANTERNA DIANTEIRA CONVENCIONAL"}
    # CONTROLE: sem a resposta que desambigua, o MESMO código não prova nada → a régua de sempre (pergunta)
    sem = {**CASO, "especificos": {}}
    d0 = decide(None, par, sem)
    assert (d0.acao, d0.classe, d0.proibicao) == ("PERGUNTAR_AO_SEGURADO", "deduzir", "deduzir_sem_calibracao")


@pytest.mark.parametrize("especificos,peca", [
    ({"tipo": "xenon"}, "vidro"),                                   # "vidro" sozinho não nomeia UMA família
    ({"tipo": "xenon"}, "lanterna"),                                # o veto de FAMÍLIA: lanterna nunca vira farol
    ({"tipo": "traseira"}, "lanterna"),                             # ainda sobram 2: não é único
    ({"relato": "a lanterna da frente quebrou quando bati no poste"}, "lanterna"),  # relato não é atributo
    ({"aceita_reparo": "dianteira"}, "lanterna"),                   # chave de outra decisão
    ({"pergunta_5": "EM FRENTE AO CARONA"}, "lanterna")])           # a resposta de OUTRA pergunta
def test_a_peca_so_e_dado_quando_UMA_sobra_na_familia(especificos, peca):
    caso = {**CASO, "dano": {**CASO["dano"], "peca": peca}, "especificos": especificos}
    assert DT.dado_do_caso_no_portal(parada("peca_ambigua", "peca", CATALOGO), caso) == ""


def test_o_80_ja_respondido_sob_a_chave_PROPRIA_e_dado_do_caso():
    opcoes = QUESTOES[SENSOR]
    sim = next(o for o in opcoes if o.startswith("Sim"))
    caso = {**CASO, "especificos": {"sensor_de_direcao_ou_faixa": sim}}
    par = parada("questionario_incompleto", "pergunta_140", opcoes, pergunta=SENSOR)
    d = decide(None, par, caso)
    assert (d.acao, d.classe, d.valor) == ("RESPONDER", "responder_com_dado", sim)
    assert DT.resposta_do_portal("questionario_incompleto", "pergunta_140", d.valor, caso, opcoes=opcoes) == \
        {"pergunta_140": sim}


@pytest.mark.parametrize("especificos", [
    {"adas": "Sim ( mantém a estabilidade do veículo na estrada)"},     # a chave não nomeia a pergunta
    {"sensor_de_faixa": "sim"},                                          # parecido não é igual
    {"sensor_de_faixa": "NÃO", "sensor": "Sim ( mantém a estabilidade do veículo na estrada)"},  # discordam
    {"sensor_de_faixa": "Não sabe"},                                     # "Não sabe" é DELE, nunca daqui
    {"pergunta_140": "acho que tem", "sensor": "NÃO"}])                  # a etiquetada dele manda
def test_o_80_nao_e_dado_sem_chave_propria_igualdade_e_unanimidade(especificos):
    caso = {**CASO, "especificos": especificos}
    par = parada("questionario_incompleto", "pergunta_140", QUESTOES[SENSOR], pergunta=SENSOR)
    d = decide(None, par, caso)
    assert d.acao != "RESPONDER", d


# ═════════════════════════════════════════════════════════════════════════════
# P4-d — P-124-15 e P-124-07
# ═════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("slot", ["pergunta_140", "pergunta_14_b", "pergunta_A-7", "pergunta_x_1-2"])
def test_P124_15_o_codigo_da_pergunta_aceita_sublinhado_e_hifen(slot):
    assert DT.slot_da_parada_confere("questionario_incompleto", slot)
    assert DT.resposta_do_portal("questionario_incompleto", slot, "SIM", CASO) == {slot: "SIM"}


@pytest.mark.parametrize("slot", ["pergunta", "pergunta_", "pergunta_-1", "pergunta__", "pergunta_1 2"])
def test_P124_15_CONTROLE_sem_codigo_continua_recusado(slot):
    assert not DT.slot_da_parada_confere("questionario_incompleto", slot)


@pytest.mark.parametrize("nao_sabe", ["Não sabe", "NÃO SABE", "Não Sabe"])
def test_P124_07_NAO_SABE_nunca_sai_do_destravador_nem_calibrado(monkeypatch, nao_sabe):
    monkeypatch.setattr(DT, "DEDUZIR_AUTONOMO_CALIBRADO", True)
    opcoes = ["Lado do carona", "Lado do motorista", nao_sabe]
    par = parada("questionario_incompleto", "pergunta_35", opcoes, pergunta=LADO)
    d = decide(P(nao_sabe, nota=99), par, provedor="openai", segunda_opiniao={**OUTRA, "valor": nao_sabe})
    assert d.acao == "PERGUNTAR_AO_SEGURADO" and d.proibicao == "nao_sabe_e_do_segurado"
    # CONTROLE: a MESMA régua, calibrada, responde uma opção que não é "Não sabe"
    ok = decide(P("Lado do motorista", nota=99), par, provedor="openai",
                segunda_opiniao={**OUTRA, "valor": "Lado do motorista"})
    assert (ok.acao, ok.valor) == ("RESPONDER", "Lado do motorista")


def test_P124_07_a_regex_de_cancelar_e_UMA_e_reusa_a_do_whatsapp():
    assert DT._RX_CANCELA.pattern in DT._RX_CANCELA_NO_PORTAL.pattern
    for v in ("cancelar o pedido", "desistir", "encerrar"):
        assert DT._RX_CANCELA_NO_PORTAL.search(DT._n(v))


# ═════════════════════════════════════════════════════════════════════════════
# P4-e — a CLASSE é da TABELA, nunca do modelo
# ═════════════════════════════════════════════════════════════════════════════
def test_o_modelo_nao_promove_a_parada_NUNCA_mesmo_com_a_chave_tirada():
    """A mutação `nunca=` tira `aceite_de_custo`: o código deixa o modelo propor — e a classe da TABELA
    (nunca_sozinho) não vira o `conduzir` que o modelo disse (antes: `classe = p.classe` → RESPONDIA)."""
    sem = tuple(k for k in DT.NUNCA_SOZINHO if k != "aceite_de_custo")
    par = parada("decidir_reparo", "aceita_reparo", ["tentar o reparo", "trocar a peca"])
    assert decide(None, par, nunca=sem) is None
    d = decide(P("tentar o reparo", classe="conduzir"), par, nunca=sem)
    assert d.acao == "PESSOA" and d.classe == "nunca_sozinho"


# ═════════════════════════════════════════════════════════════════════════════
# P8 — a parada leva a TELA, e o destravador a lê
# ═════════════════════════════════════════════════════════════════════════════
def test_P8_a_parada_do_API_first_leva_a_tela_com_os_rotulos_REAIS():
    t = ST.tela_da_parada("motivo_ambiguo", opcoes=["CHUVA DE GRANIZO", "CHOQUE TERMICO"])
    real = TELAS["yelum_parabrisa_50_peca_causa"]
    rotulos_reais = [m["label"] for m in real["mdselects"]] + [i["label"] for i in real["inputs"]]
    assert t["campo"] == "Como ocorreu o dano ao veículo?" and t["campo"] in rotulos_reais
    assert set(t["rotulos"]) == set(rotulos_reais) and t["heading"] == real["heading"]
    assert t["opcoes"] == ["CHUVA DE GRANIZO", "CHOQUE TERMICO"] and t["pending_required"] == [t["campo"]]
    contato = TELAS["yelum_contato_20"]
    assert ST.tela_da_parada("tipo_de_telefone_desconhecido")["campo"] in [m["label"] for m in contato["mdselects"]]
    q = ST.tela_da_parada("questionario_incompleto", pergunta=SENSOR, opcoes=QUESTOES[SENSOR])
    assert q["campo"] == SENSOR and q["opcoes"] == QUESTOES[SENSOR]


def test_P8_o_destravador_le_a_TELA_do_API_first_e_a_do_DOM():
    ev_api = {"stage": "motivo_ambiguo", "opcoes": ["CHUVA DE GRANIZO", "CHOQUE TERMICO"],
              "tela_da_parada": ST.tela_da_parada("motivo_ambiguo", opcoes=["CHUVA DE GRANIZO", "CHOQUE TERMICO"]),
              "continuacao": {"possivel": True, "acao_esperada": "responder:como", "etapa": "causa"}}
    texto = DT.texto_da_parada(DT.parada_do_portal(ev_api))
    assert "O campo que pede a resposta: Como ocorreu o dano ao veículo?" in texto
    assert "Campos desta tela:" in texto and "Onde ocorreu o dano ao veículo?" in texto
    assert "Tela do portal: Dados da apólice" in texto
    # o DOM (`adaptive.resultado_da_parada` + `_augment_hitl_evidence`): passo, campo, opções, parada_do_dom
    ev_dom = {"stage": "perimetro_desconhecido", "acao_esperada": "responder:onde",
              "campo": "Onde ocorreu o dano ao veículo?", "opcoes": ["Urbano (Cidade)", "Rodoviário", "Não Sabe"],
              "passo": {"titulo": "Dados da apólice",
                        "obrigatorios_vazios": [{"tipo": "select", "label": "Onde ocorreu o dano ao veículo?"}]},
              "parada_do_dom": {"stage": "perimetro_desconhecido", "acao_esperada": "responder:onde",
                                "slot": "onde", "opcoes": ["Urbano (Cidade)", "Rodoviário", "Não Sabe"]}}
    par = DT.parada_do_portal(ev_dom)
    assert (par["stage"], par["operacao"], par["slot"]) == ("perimetro_desconhecido", "responder", "onde")
    assert par["tela"]["pending_required"] == ["Onde ocorreu o dano ao veículo?"]
    assert "Ainda obrigatórios nesta tela: Onde ocorreu o dano ao veículo?" in DT.texto_da_parada(par)
    assert decide(None, par).acao == "PERGUNTAR_AO_SEGURADO"
    # o prompt ao modelo leva a TELA (a parte variável, depois do prefixo fixo)
    msgs = DT.compor_mensagens_do_portal(DT.parada_do_portal(ev_api), CASO, ev_api)
    assert "O campo que pede a resposta: Como ocorreu o dano ao veículo?" in msgs["user"]
    assert "00000000000" not in msgs["user"] and "AAA0A00" not in msgs["user"]
