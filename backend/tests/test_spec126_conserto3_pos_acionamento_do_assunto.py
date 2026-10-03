# -*- coding: utf-8 -*-
r"""SPEC-126 · CONSERTO 3 — o acionamento de um atendimento ANTERIOR não faz o caso NOVO "pós-acionamento".

📊 O defeito (gerente, 03/10): o conserto Y passou a gravar `acionamento.enviado_em` na ficha — uma por
conversa (= por telefone), aditiva (`attendance_ficha.fundir`: `acionamento` nunca sai). O conserto 2 cortou
a leitura no `insurer_dispatch_tool`; faltavam (1) `human_handoff._e_pos_acionamento`, que lia o fato
sem o assunto — o "cancela" do caso NOVO do mesmo telefone ia a pessoa com dossiê de pós-acionamento —, e
(2) `attendance_ficha.derivar_fase`, que deixava a fase `acionado` para sempre.

O conserto: a MESMA régua do conserto 2, agora num lugar só (`attendance_ficha.de_um_assunto_anterior` +
`inicio_do_assunto_em_aberto` → `historico_do_atendimento` → `Historico.inicio`: N dias de silêncio +
`resolvido_em`). O `HumanHandoffTool._arun` decide sobre `ficha_do_assunto` (cópia de leitura) e grava a
partir da linha lida (o fato antigo nunca é apagado).

Pelo MOTOR (§9.4): `HumanHandoffTool._arun` REAL → `historico_da_conversa` REAL → `attendance_ficha` REAL →
`por_que_vai_direto_a_pessoa`/R9 REAIS → `enviar_ao_grupo` REAL. Dublês só na BORDA da SPEC-123/U4 (banco
em memória que filtra, Redis, WhatsApp, destino do grupo, feed). Ficha gravada pelo escritor real (`fundir`).

🔴 MUTAÇÃO (rodada uma vez, por cópia): `ficha_do_assunto` devolvendo a ficha sem corte → (a) VERMELHO.

Rodar (de backend/):
    PYTHONIOENCODING=utf-8 python -m pytest tests/test_spec126_conserto3_pos_acionamento_do_assunto.py -q -p no:cacheprovider
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
for _c in (RAIZ, AQUI):
    if _c not in sys.path:
        sys.path.insert(0, _c)

# ⚠️ os pacotes REAIS antes do módulo da SPEC-123 (a mesma ordem de `test_spec126_conserto_x_*`)
from app.agents import nodes as _N  # noqa: E402,F401

from test_spec123_atendimento_segunda_chance import (  # noqa: E402,F401
    ENVIOS, X, _banco, _conversa, _diario, _linha, _pedir, borda, iso)

MIN, DIA = timedelta(minutes=1), timedelta(days=1)
OUTRA = "22222222-2222-4222-8222-222222222222"
PERGUNTA = "Guincho para o carro de placa AAA0A00, na Rua Teste, 10. Posso acionar?"
MOTIVO = "o segurado pediu para cancelar o guincho"


def _ficha_acionada(ha):
    """A ficha como o PRODUTO a grava: o escritor real (`fundir`, chamado por `attendance_ficha.gravar`
    em `InsurerDispatchTool._marcar_o_acionamento`), com o `enviado_em` do instante do efeito."""
    from app.services.attendance_ficha import ficha_vazia, fundir

    f = fundir(ficha_vazia(), {"servico": "guincho", "seguradora": "seguradora exemplo",
                               "confirmados": {"local_atual": "Rua Teste 10"}})
    em = (datetime.now(timezone.utc) - ha).isoformat()
    return fundir(f, {"acionamento": {"enviado_em": em, "servico": "guincho",
                                      "seguradora": "seguradora exemplo"}})


def _caso(cid, falas, *, enviado_ha, resolvido_ha=None):
    """`falas` = [(quem, texto, há_quanto)] gravadas em `messages` como o webhook as grava."""
    ultima = falas[-1][1]
    conversa = _conversa(cid, preview=ultima, ficha=_ficha_acionada(enviado_ha))
    agora = datetime.now(timezone.utc)
    if resolvido_ha is not None:
        conversa["resolvido_em"] = iso(agora - resolvido_ha)
    b = _banco(conversa)
    for k, (quem, texto, ha) in enumerate(falas):
        b.tabelas["messages"].append({
            "id": "m-%s-%02d" % (cid, k), "conversation_id": cid, "payload": {},
            "role": "user" if quem == "segurado" else "assistant", "content": texto,
            "created_at": iso(agora - ha)})
    return b


# ─── (a) o caso NOVO, 30 dias depois, mesmo telefone: "cancela" antes de acionar ──────────────────────
@pytest.mark.parametrize("falas", [
    # a conversa guarda o caso velho inteiro, e o novo chega depois do silêncio de N dias
    [("segurado", "meu carro morreu, preciso de guincho", 30 * DIA + 10 * MIN),
     ("agente", PERGUNTA, 30 * DIA + 8 * MIN), ("segurado", "sim", 30 * DIA + 7 * MIN),
     ("agente", "Pronto! O guincho já está a caminho.", 30 * DIA - 1 * MIN),
     ("segurado", "oi, meu carro quebrou de novo, preciso de guincho", 6 * MIN),
     ("agente", PERGUNTA, 5 * MIN), ("segurado", "cancela o guincho", 1 * MIN)],
    # só o caso novo na conversa (a antiga foi arquivada/ilegível antes dele)
    [("segurado", "oi, meu carro quebrou de novo, preciso de guincho", 6 * MIN),
     ("agente", PERGUNTA, 5 * MIN), ("segurado", "cancela o guincho", 1 * MIN)],
], ids=["caso-velho-na-conversa", "so-o-caso-novo"])
def test_a_acionamento_de_30_dias_nao_faz_o_caso_novo_pos_acionamento(borda, falas):
    import app.agents.tools.human_handoff as H

    cid = "c-c3-a"
    b = _caso(cid, falas, enviado_ha=30 * DIA)
    r = _pedir(H, b, cid, MOTIVO)
    assert r == H.SEGUNDA_CHANCE_DO_HANDOFF, r              # como ANTES de acionar (U4, controle)
    assert ENVIOS == [] and _linha(b, cid)["status"] == "open"
    assert [l["acao"] for l in _diario(b, cid)] == ["perguntou_segurado"]
    # ⛔ o fato antigo continua gravado (história): o corte é só da LEITURA
    assert (_linha(b, cid)["ficha_atendimento"].get("acionamento") or {}).get("enviado_em")


def test_a_resolvido_em_tambem_separa_o_acionamento_de_2_horas(borda):
    """A outra metade da MESMA régua: o atendimento ENCERRADO há 1 h separa o acionamento de 2 h atrás."""
    import app.agents.tools.human_handoff as H

    cid = "c-c3-a2"
    b = _caso(cid, [("segurado", "preciso de guincho", 130 * MIN), ("agente", PERGUNTA, 128 * MIN),
                    ("segurado", "sim", 127 * MIN), ("segurado", "cancela o guincho", 1 * MIN)],
              enviado_ha=120 * MIN, resolvido_ha=60 * MIN)
    assert _pedir(H, b, cid, MOTIVO) == H.SEGUNDA_CHANCE_DO_HANDOFF and ENVIOS == []


# ─── (b) CONTROLE: acionado há 5 min, MESMO assunto → pessoa com o dossiê de cancelamento (fio da U4) ──
def test_b_controle_acionado_ha_5_min_no_mesmo_assunto_vai_a_pessoa_com_o_dossie(borda):
    import app.agents.tools.human_handoff as H
    from app.agents.honestidade_do_handoff import SUCESSO_DO_HANDOFF

    cid = "c-c3-b"
    b = _caso(cid, [("segurado", "meu carro morreu, preciso de guincho", 20 * MIN),
                    ("agente", PERGUNTA, 15 * MIN), ("segurado", "sim", 14 * MIN),
                    ("agente", "Pronto! O guincho já está a caminho.", 4 * MIN),
                    ("segurado", "cancela o guincho", 1 * MIN)], enviado_ha=5 * MIN)
    r = _pedir(H, b, cid, MOTIVO)
    assert r == SUCESSO_DO_HANDOFF, r
    assert _linha(b, cid)["status"] == "HUMAN_REQUESTED" and len(ENVIOS) == 1, ENVIOS
    dossie = ENVIOS[0][1]
    assert "CANCELAR" in dossie and "NÃO cancelou" in dossie and "cancela o guincho" in dossie
    assert "Acionado em" in dossie and "GUINCHO" in dossie
    d = _diario(b, cid)
    assert [l["acao"] for l in d] == ["chamou_pessoa"] and d[0]["classe"] == "nunca_sozinho", d


def test_b_controle_resolvido_ANTES_do_acionamento_nao_separa(borda):
    import app.agents.tools.human_handoff as H
    from app.agents.honestidade_do_handoff import SUCESSO_DO_HANDOFF

    cid = "c-c3-b2"
    b = _caso(cid, [("segurado", "preciso de guincho", 20 * MIN), ("agente", PERGUNTA, 15 * MIN),
                    ("segurado", "sim", 14 * MIN), ("segurado", "cancela o guincho", 1 * MIN)],
              enviado_ha=5 * MIN, resolvido_ha=3 * DIA)
    assert _pedir(H, b, cid, MOTIVO) == SUCESSO_DO_HANDOFF and len(ENVIOS) == 1


def test_b_dois_tenants_a_conversa_de_outra_corretora_nao_define_o_assunto(borda):
    """§7: a MESMA sessão em OUTRA corretora com uma fala de 1 min atrás não abre "assunto novo" aqui —
    o começo do assunto é lido com o `company_id` da chamada (sem o filtro, o corte cairia e o
    cancelamento iria à segunda chance)."""
    import app.agents.tools.human_handoff as H
    from app.agents.honestidade_do_handoff import SUCESSO_DO_HANDOFF

    cid = "c-c3-b3"
    b = _caso(cid, [("segurado", "preciso de guincho", 20 * MIN), ("agente", PERGUNTA, 15 * MIN),
                    ("segurado", "sim", 14 * MIN), ("segurado", "cancela o guincho", 1 * MIN)],
              enviado_ha=5 * MIN)
    agora = datetime.now(timezone.utc)
    outra = {**_conversa("c-c3-b3-outra", ficha=None), "company_id": OUTRA, "session_id": "ses-" + cid,
             "updated_at": iso(agora), "last_message_at": iso(agora)}
    b.tabelas["conversations"].append(outra)
    b.tabelas["messages"].append({"id": "m-outra", "conversation_id": "c-c3-b3-outra", "payload": {},
                                  "role": "user", "content": "oi", "created_at": iso(agora - 10 * DIA)})
    b.tabelas["messages"].append({"id": "m-outra2", "conversation_id": "c-c3-b3-outra", "payload": {},
                                  "role": "user", "content": "oi de novo", "created_at": iso(agora - MIN)})
    assert _pedir(H, b, cid, MOTIVO) == SUCESSO_DO_HANDOFF and len(ENVIOS) == 1


# ─── (c) derivar_fase / ficha_do_assunto — a MESMA régua, pura ───────────────────────────────────────
def test_c_derivar_fase_com_o_comeco_do_assunto():
    from app.services import attendance_ficha as F

    ficha = _ficha_acionada(30 * DIA)
    assert ficha["fase"] == F.FASE_ACIONADO                         # o escritor real (sem o começo): como antes
    agora = datetime.now(timezone.utc)
    assert F.derivar_fase(ficha, inicio_do_assunto=agora - 6 * MIN) == F.FASE_COLETA
    assert F.derivar_fase(ficha, inicio_do_assunto=agora - 31 * DIA) == F.FASE_ACIONADO   # controle
    assert F.derivar_fase(ficha) == F.FASE_ACIONADO                                      # controle
    recente = _ficha_acionada(5 * MIN)
    assert F.derivar_fase(recente, inicio_do_assunto=agora - 20 * MIN) == F.FASE_ACIONADO


def test_c_ficha_do_assunto_e_copia_e_o_pos_acionamento_le_a_copia():
    from app.agents.tools.human_handoff import _e_pos_acionamento
    from app.services import attendance_ficha as F

    agora = datetime.now(timezone.utc)
    ficha = _ficha_acionada(30 * DIA)
    vista = F.ficha_do_assunto(ficha, agora - 6 * MIN)
    assert vista is not ficha and vista["acionamento"] == {} and vista["fase"] == F.FASE_COLETA
    assert ficha["acionamento"].get("enviado_em")                   # a gravada não muda
    assert _e_pos_acionamento({"ficha_atendimento": ficha})         # controle: a régua consegue dizer sim
    assert not _e_pos_acionamento({"ficha_atendimento": vista})
    # sem o começo do assunto: a janela de N dias contada de agora (a do conserto 2)
    assert F.ficha_do_assunto(ficha, None)["acionamento"] == {}
    assert F.ficha_do_assunto(_ficha_acionada(1 * DIA), None)["acionamento"].get("enviado_em")


def test_c_o_protocolo_sem_carimbo_e_datado_pela_fase():
    """O protocolo que `nodes` grava sozinho não tem `enviado_em`: a hora é a da fase (`historico`)."""
    from app.services import attendance_ficha as F

    f = F.fundir(F.ficha_vazia(), {"servico": "guincho"})
    f = F.fundir(f, {"acionamento": {"protocolo": "PR123"}})
    velha = dict(f, historico=[dict(p, em=(datetime.now(timezone.utc) - 30 * DIA).isoformat())
                               for p in f["historico"]])
    agora = datetime.now(timezone.utc)
    assert F.instante_do_acionamento(velha) < agora - 29 * DIA
    assert F.derivar_fase(velha, inicio_do_assunto=agora - MIN) == F.FASE_COLETA
    assert F.derivar_fase(f, inicio_do_assunto=agora - MIN) == F.FASE_ACOMPANHANDO       # controle
    assert F.instante_do_acionamento(F.ficha_vazia()) is None
