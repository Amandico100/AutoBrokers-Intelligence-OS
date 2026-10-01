# -*- coding: utf-8 -*-
"""SPEC-123 · CONSERTO ÚNICO · parte Y — a segunda chance lê o SEGURADO, e o "já existe" não adota outro serviço.

Y1 (juiz B3 · red team B6) — `request_human_agent` (o `HumanHandoffTool._arun` REAL) lê as últimas falas do
   segurado em `messages` (a conversa achada por `company_id`) → `por_que_vai_direto_a_pessoa` (REAL) → o
   detector de pedido de pessoa do produto (`pos_acionamento.pediu_pessoa`, a MESMA régua do rótulo `P`) e o
   de sinistro (`claims_shadow.detectar_sinistro`, estendido com o vocabulário que passava) → pessoa NA 1ª.
Y2 (juiz B4 · red team B5) — na RETOMADA, a tela "já existe pedido" só vira o protocolo do caso quando NOMEIA
   exatamente UM serviço que é o do caso (`_PALAVRAS_DE_SERVICO`, a tabela da conferência); e a retomada só é
   marcada "o anterior pode ter aberto" quando o "sim" da confirmação SAIU (o transcript, não a tela).

Telas REAIS do acervo (`tests/corpus/telas_reais`, mascaradas). Dublê só na borda (banco, Redis, WhatsApp).
🔴 MUTAÇÕES (rodadas uma vez, por cópia, cada uma → VERMELHO aqui): Y1(a) sem `pediu_pessoa` sobre as falas ·
Y1(b) sem `_RE_EVENTO_NOMEADO`/vocabulário novo no detector · Y2(a) adotar sem conferir o serviço ·
Y2(b) `anterior_pode_ter_aberto` volta a `conferencia or confirmacoes`.
⛔ Nenhum dado pessoal: telas mascaradas, números e ids inventados.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import pytest

# a borda e o fio dos dois arquivos que já provam estas peças — nada reimplementado
from tests.test_spec123_atendimento_segunda_chance import (  # noqa: F401  (borda é fixture)
    ENVIOS, X, _banco, _conversa, _diario, _linha, _pedir, borda, iso,
)
from tests.test_spec123_ida_e_volta_retomada import (  # noqa: F401  (amb é fixture)
    D, EMPRESA_A, JA_ABERTA_HDI, JA_ABERTA_YELUM_72H, REF_HDI, REF_PORTO, REF_YELUM, R,
    SERVICO_ABERTO_PORTO, _pergunta_allianz_e_ura_encerra, amb, carregar, responder, salvar, sessao,
    tela_real, turno,
)
from tests.test_spec123_ida_e_volta_retomada import JA_ABERTA_YELUM_UM_GUINCHO


# =============================================================================
# Y1 · o que o SEGURADO disse
# =============================================================================
PEDE_PESSOA = ["quero falar com um atendente humano agora", "me passa pra uma pessoa por favor",
               "quero uma pessoa", "quero um atendente de verdade", "posso falar com o corretor?",
               "não quero falar com robô", "queria conversar com alguém"]
SINISTRO = ["caiu um raio e queimou a TV", "danos elétricos na geladeira", "alagou a casa toda",
            "a enchente levou o carro", "vendaval destelhou a casa", "quebrou o vidro do carro em batida",
            "bati o carro", "tive uma colisão na rodovia", "roubaram o carro", "sofri um furto",
            "curto circuito queimou o portão", "o raio queimou o portão"]
#: CONTROLE — o falso positivo que cada extensão poderia trazer, com o motivo ao lado
CONTROLE = ["ok, obrigado",
            "a bateria do carro arriou",                     # bateria ≠ bati
            "minha bateria descarregou",
            "fiz um raio-x do joelho",                       # raio-x ≠ raio
            "quanto custa a cobertura de danos elétricos?",  # venda
            "o seguro cobre enchente?",                      # risco nomeado, sem evento
            "a previsão é de vendaval amanhã",
            "a pessoa que vai estar no local sou eu",        # "pessoa" sozinha não é pedido
            "o atendente da seguradora disse que vem amanhã",
            "vou falar com a corretora depois",              # conta o que VAI fazer
            "a batida do motor está estranha",               # batida sem o evento
            "bati um papo com o vizinho",
            "qual o telefone do guincho?", "tem cobertura pra raio?", "quero falar com o guincho"]


def _decide(fala):
    import app.agents.tools.human_handoff as H

    return H.por_que_vai_direto_a_pessoa("dúvida do segurado",
                                         caso={"last_message_preview": "ok", "mensagens": [fala]})


@pytest.mark.parametrize("fala", PEDE_PESSOA)
def test_Y1a_o_segurado_que_pede_pessoa_com_as_palavras_dele_vai_direto(fala):
    assert _decide(fala) == "o segurado pediu para falar com uma pessoa", fala


@pytest.mark.parametrize("fala", SINISTRO)
def test_Y1b_o_sinistro_na_fala_do_segurado_vai_direto(fala):
    assert _decide(fala) == "é sinistro, e sinistro sempre vai para uma pessoa", fala


@pytest.mark.parametrize("fala", CONTROLE)
def test_Y1_CONTROLE_a_fala_comum_continua_com_a_segunda_chance(fala):
    assert _decide(fala) == "", fala


def test_Y1_o_motivo_tambem_e_lido_pelo_mesmo_detector():
    """📊 red team B6: "quer conversar com um humano de verdade" no MOTIVO ganhava a segunda chance."""
    import app.agents.tools.human_handoff as H

    for motivo in ("quer conversar com um humano de verdade", "cliente insiste em falar com gente"):
        assert H.por_que_vai_direto_a_pessoa(motivo, caso={"last_message_preview": "ok"}) \
            == "o segurado pediu para falar com uma pessoa", motivo


def test_Y1_um_detector_so_o_rotulo_P_do_pos_acionamento_e_a_segunda_chance_concordam():
    """CLAUDE.md §5: o pedido de pessoa é UMA régua. O rótulo `P` (R9) e a segunda chance leem a mesma."""
    from app.atendimento.pos_acionamento import _URGENCIA, _PEDE_PESSOA, classificar_turno, pediu_pessoa

    assert _PEDE_PESSOA.pattern in _URGENCIA.pattern
    for fala in PEDE_PESSOA:
        assert pediu_pessoa(fala) and classificar_turno([fala]) == "P", fala
    for fala in ("a pessoa que vai estar no local sou eu", "vou falar com a corretora depois"):
        assert not pediu_pessoa(fala), fala


def test_Y1b_o_detector_de_sinistro_do_produto_abre_e_a_venda_continua_trancando():
    from app.services.claims_shadow import detectar_sinistro

    for fala in SINISTRO:
        assert detectar_sinistro(fala)[0], fala
    for fala in CONTROLE:
        assert not detectar_sinistro(fala)[0], fala


# ---------------------------------------------------------------- Y1 · O FIO (a ferramenta REAL + o banco)
def _fala(cid, texto, segundos_atras):
    return {"conversation_id": cid, "role": "user", "content": texto,
            "created_at": iso(datetime.now(timezone.utc) - timedelta(seconds=segundos_atras))}


@pytest.mark.parametrize("fala_do_segurado", ["quero falar com um atendente humano agora",
                                              "caiu um raio e queimou a TV"])
def test_Y1_O_FIO_a_ferramenta_le_as_falas_do_segurado_e_chama_pessoa_na_primeira(borda, fala_do_segurado):
    """O motivo do modelo é "dúvida"; a PRÉVIA é um "ok"; o pedido do segurado está nas falas do turno."""
    import app.agents.tools.human_handoff as H
    from app.agents.honestidade_do_handoff import SUCESSO_DO_HANDOFF

    cid = "c-y1-fio-01"
    b = _banco(_conversa(cid, preview="ok"))
    b.tabelas["messages"] = [_fala(cid, "boa tarde", 90), _fala(cid, fala_do_segurado, 60),
                             _fala(cid, "ok", 30),
                             {"conversation_id": cid, "role": "assistant", "content": "posso ajudar?",
                              "created_at": iso(datetime.now(timezone.utc))}]
    r = _pedir(H, b, cid, "dúvida sobre a franquia")
    assert r == SUCESSO_DO_HANDOFF and not H.foi_segunda_chance(r), r
    assert _linha(b, cid)["status"] == "HUMAN_REQUESTED"
    assert len(ENVIOS) == 1, "o grupo é avisado na PRIMEIRA chamada"
    [d] = _diario(b, cid)
    assert d["acao"] == "chamou_pessoa" and d["classe"] == "nunca_sozinho", d


def test_Y1_FIO_CONTROLE_a_mesma_conversa_sem_o_pedido_ganha_a_segunda_chance(borda):
    import app.agents.tools.human_handoff as H

    cid = "c-y1-ctrl-1"
    b = _banco(_conversa(cid, preview="ok"))
    b.tabelas["messages"] = [_fala(cid, "boa tarde", 90), _fala(cid, "qual o valor da franquia?", 60),
                             _fala(cid, "ok", 30)]
    assert _pedir(H, b, cid, "dúvida sobre a franquia") == H.SEGUNDA_CHANCE_DO_HANDOFF
    assert ENVIOS == []


def test_Y1_FIO_a_fala_de_OUTRA_conversa_nao_conta(borda):
    """§7: as falas são da conversa achada por `company_id` — a de outra conversa/corretora não decide."""
    import app.agents.tools.human_handoff as H

    cid = "c-y1-iso-01"
    b = _banco(_conversa(cid, preview="ok"))
    b.tabelas["messages"] = [_fala("c-de-outra-corretora", "quero falar com um atendente humano agora", 10),
                             _fala(cid, "qual o valor da franquia?", 60)]
    assert _pedir(H, b, cid, "dúvida sobre a franquia") == H.SEGUNDA_CHANCE_DO_HANDOFF


def test_Y1_FIO_falas_ilegiveis_caem_na_previa(borda):
    """`messages` fora do ar → a decisão usa a prévia, como antes (e ela ainda segura o pedido de pessoa)."""
    import app.agents.tools.human_handoff as H

    cid = "c-y1-prev-1"
    b = _banco(_conversa(cid, preview="me passa pra uma pessoa por favor"))
    b.quebrada = "messages"
    r = _pedir(H, b, cid, "dúvida sobre a franquia")
    assert not H.foi_segunda_chance(r), r


# =============================================================================
# Y2 · "JÁ EXISTE PEDIDO" na retomada
# =============================================================================
def _retomada(ref, sub, **extra):
    return sessao(ref, sub, retry_count=1,
                  retomada={"n": 1, "porque": "seguradora_encerrou", "anterior_pode_ter_aberto": True}, **extra)


#: 📊 as telas REAIS: porto-auto 193c5ad6+1 (GUINCHO PESADO) · hdi-auto 4b2d0c2a+1 (não nomeia) ·
#: yelum-auto 30b3219e (DOIS guinchos) · Yelum MTA na forma real da lista de 72 h.
YELUM_MTA = re.sub(r"GUINCHO\nSolicita\S+ \{VALOR\}\nGUINCHO", "MTA - MEIO DE TRANSPORTE", JA_ABERTA_YELUM_72H)


@pytest.mark.parametrize("ref,sub,tela,porque", [
    (REF_PORTO, "chaveiro", SERVICO_ABERTO_PORTO, "chaveiro × 1-N-GUINCHO PESADO (juiz B4)"),
    (REF_HDI, "socorro_mecanico", JA_ABERTA_HDI, "hdi 4b2d0c2a+1: a tela não nomeia o serviço (red team B5)"),
    (REF_HDI, "guincho", JA_ABERTA_HDI, "não nomeia → nem o mesmo serviço adota às cegas"),
    (REF_YELUM, "guincho", YELUM_MTA, "guincho × MTA - MEIO DE TRANSPORTE (red team B5)"),
    (REF_YELUM, "guincho", JA_ABERTA_YELUM_72H, "dois guinchos: qual é o nosso? (yelum 30b3219e)"),
])
def test_Y2a_o_pedido_que_ja_existe_de_outro_servico_nao_vira_o_do_caso(amb, ref, sub, tela, porque):
    assert YELUM_MTA != JA_ABERTA_YELUM_72H and "MTA" in YELUM_MTA
    salvar(EMPRESA_A, _retomada(ref, sub))
    s = turno(amb, tela)
    assert s["state"] == "needs_human" and s["reason"] == "ja_existe_solicitacao", (porque, s["state"], s.get("captured"))
    assert not (s.get("captured") or {}).get("protocol"), porque
    assert not any("Prontinho" in t for t in amb.ao_cliente()), "o segurado ouviu um protocolo que não é dele"
    assert amb.a_seguradora() == [], "a tela de pedido aberto foi respondida (abre outro)"


@pytest.mark.parametrize("ref,sub,tela", [
    (REF_PORTO, "guincho", SERVICO_ABERTO_PORTO),
    (REF_YELUM, "guincho", JA_ABERTA_YELUM_UM_GUINCHO),
    (REF_YELUM, "pane_seca", JA_ABERTA_YELUM_UM_GUINCHO),   # pane seca é guincho (canonical_subservice)
])
def test_Y2a_CONTROLE_o_mesmo_servico_com_o_sim_enviado_adota_como_hoje(amb, ref, sub, tela):
    assert JA_ABERTA_YELUM_UM_GUINCHO.count("GUINCHO") == 1
    salvar(EMPRESA_A, _retomada(ref, sub))
    s = turno(amb, tela)
    assert s["captured"].get("ja_existia") is True and s["state"] == "monitoring", (s["state"], s.get("reason"))
    assert str(s["captured"]["protocol"]).lower() in D._norm_text(tela)


def test_Y2a_o_numero_adotado_e_o_da_linha_do_servico_do_caso():
    """Lista com dois serviços diferentes: o número é o da linha que casa, não o do cabeçalho."""
    tela = ("{NOME} - {CORRETORA}, identifiquei que a assistência *111* foi aberta dentro das últimas 72h. "
            "Selecione abaixo sobre qual solicitação você quer falar:\nMTA - MEIO DE TRANSPORTE\n"
            "Solicitação: 111\nGUINCHO\nSolicitação: 222")
    s = sessao(REF_YELUM, "guincho")
    ja = D.solicitacao_ja_existente(REF_YELUM, tela)
    assert [x["numero"] for x in ja["servicos"]] == ["111", "222"]
    assert D.seguir_com_a_solicitacao_existente(s, ja)["captured"]["protocol"] == "222"


# ---------------------------------------------------------------- Y2(b) · o "sim" que SAIU
TELA_CONF = "Podemos confirmar o atendimento?\n1 - Sim\n2 - Não"


def _anterior(**extra):
    base = {"conferencia": {"ok": False, "divergencias": [{"campo": "origem"}]},
            "transcript": [{"direction": "in", "text": TELA_CONF}]}
    base.update(extra)
    return base


def test_Y2b_so_a_confirmacao_cujo_sim_saiu_marca_que_o_anterior_pode_ter_aberto():
    c = {"digest": "d", "tela": TELA_CONF, "saida_em": 1}
    correcao = {"direction": "out", "text": "Antes de confirmar: o endereço de origem é outro",
                "step": "correcao:origem"}
    assert D.anterior_pode_ter_aberto(_anterior()) is False, "o resumo APARECEU (e divergiu); nada saiu"
    assert D.anterior_pode_ter_aberto(_anterior(confirmacoes=[c])) is False, "registrada, mas o sim não saiu"
    assert D.anterior_pode_ter_aberto(_anterior(
        confirmacoes=[c], transcript=_anterior()["transcript"] + [correcao])) is False, "saiu a CORREÇÃO"
    # CONTROLE: o "1" (Sim) saiu depois da confirmação registrada
    assert D.anterior_pode_ter_aberto(_anterior(
        confirmacoes=[c], transcript=_anterior()["transcript"] + [
            {"direction": "out", "text": "1", "step": "confirmar"}])) is True


def test_Y2b_O_FIO_a_retomada_pelo_roteador_so_marca_quando_o_sim_saiu(amb):
    """O roteador REAL: a URA fecha com a pergunta no ar → a resposta tardia reabre → a marca da retomada."""
    s = _pergunta_allianz_e_ura_encerra(amb)
    s["conferencia"] = {"ok": False, "divergencias": [{"campo": "origem"}], "at": "x"}
    salvar(EMPRESA_A, s)
    assert responder(amb, "88010-400") is True
    assert (carregar().get("retomada") or {}).get("anterior_pode_ter_aberto") is False


def test_Y2b_FIO_CONTROLE_com_o_sim_enviado_a_retomada_marca(amb):
    s = _pergunta_allianz_e_ura_encerra(amb)
    n = len(s.get("transcript") or [])
    s["transcript"] = list(s.get("transcript") or []) + [
        {"direction": "in", "text": TELA_CONF}, {"direction": "out", "text": "1", "step": "confirmar"}]
    s["confirmacoes"] = [{"digest": "d", "tela": TELA_CONF, "saida_em": n + 1}]
    salvar(EMPRESA_A, s)
    assert responder(amb, "88010-400") is True
    assert (carregar().get("retomada") or {}).get("anterior_pode_ter_aberto") is True
