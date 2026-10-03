# -*- coding: utf-8 -*-
r"""SPEC-126 · CONSERTO 2 · BN-1 da confirmação — o acionamento de um caso ANTIGO não trava o caso NOVO.

📊 Sonda do juiz de confirmação (02/10, HEAD 8ddba57, `scratchpad/confirm126/test_conf126_sondas.py`):
ficha com `acionamento.enviado_em` de 30 dias atrás e o caso novo do mesmo telefone ("meu carro quebrou de
novo na estrada, preciso de guincho") → `already_dispatched` + "diga ao cliente que o pedido já está com a
seguradora" — com NADA enviado. A ficha é por conversa (= por telefone) e aditiva; `acionamento` nunca sai.

O conserto (`InsurerDispatchTool._acionamento_desta_conversa` → `_do_assunto_em_aberto`): o acionamento
anterior ao COMEÇO DO ASSUNTO EM ABERTO não conta — a régua é a que o produto já tem
(`historico_do_atendimento` → `inicio_do_assunto`: a regra dos N dias de silêncio + `resolvido_em`).

Pelo MOTOR (§9.4): `nodes.tool_node` REAL → `InsurerDispatchTool._arun` REAL → portão REAL →
`attendance_ficha` REAL → `historico_da_conversa` REAL. Dublês só na BORDA: o banco em memória
(`test_spec126_u3_d1_parente_aciona.borda`), o canal com a seguradora (`test_spec125_conserto_y.ao_vivo`) e
o modelo do classificador (`llm_factory.invocar_com_reserva`). Nenhuma rede, nada pago, nada enviado.

Rodar (de backend/):
    PYTHONIOENCODING=utf-8 python -m pytest tests/test_spec126_conserto2_assunto.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from langchain_core.messages import AIMessage, HumanMessage

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
for _c in (RAIZ, AQUI):
    if _c not in sys.path:
        sys.path.insert(0, _c)

import app.agents.tools.insurer_dispatch_tool as IT  # noqa: E402
from app.agents import nodes as N  # noqa: E402
from test_spec125_conserto_y import CASO_AUTO, PERGUNTA, ao_vivo  # noqa: E402,F401
from test_spec126_u3_d1_parente_aciona import EMPRESA_A, SESSAO_A, borda, estado  # noqa: E402,F401

#: o que o texto do `already_dispatched` manda o modelo dizer — nunca num caso NOVO
DIZ_QUE_JA_ESTA = ("NADA FOI ENVIADO DE NOVO", "já está com a seguradora")
PEDIDO_NOVO = "oi, meu carro quebrou de novo na estrada, preciso de guincho"


@pytest.fixture
def classificador_ok():
    from app.services.evals import bancada_confirmacao as BC

    with BC.classificador_duble_na_borda() as chamadas:      # diz OK: quem decide é a rede + o fato
        yield chamadas


@pytest.fixture
def classificador_fora_do_ar():
    """A BORDA do modelo do papel `confirmacao` levanta (a chave não resolve, o provedor caiu)."""
    from app.factories import llm_factory as LF
    from app.services.evals.bancada_confirmacao import PAPEL

    original = LF.invocar_com_reserva

    async def _caiu(papel, mensagens, **kw):
        if papel != PAPEL:
            return await original(papel, mensagens, **kw)
        raise RuntimeError("ChaveNaoResolvida")

    LF.invocar_com_reserva = _caiu
    try:
        yield
    finally:
        LF.invocar_com_reserva = original


def _mundo(borda, *, enviado_ha=None, resolvido_ha=None):
    banco, _prov = borda
    rot = sys.modules["app.services.dispatch_router"]
    efeitos: list = []

    async def _start(**kw):
        efeitos.append(("START", kw.get("subservice")))
        return {"ok": True, "session": {"client_phone": kw.get("client_phone"),
                                        "subservice": kw.get("subservice")}}

    async def _enq(*a, **k):
        efeitos.append(("FILA",))
        return 1

    rot.start_live_dispatch, rot.enqueue_dispatch = _start, _enq
    agora = datetime.now(timezone.utc)
    ficha = None
    if enviado_ha is not None:
        ficha = {"acionamento": {"enviado_em": (agora - enviado_ha).isoformat(),
                                 "servico": CASO_AUTO["subservice"], "seguradora": "allianz"}}
    conversa = {"id": "conv-y", "company_id": EMPRESA_A, "session_id": SESSAO_A, "channel": "whatsapp",
                "ficha_atendimento": ficha}
    if resolvido_ha is not None:
        conversa["resolvido_em"] = (agora - resolvido_ha).isoformat()
    banco.tabelas.setdefault("conversations", []).append(conversa)
    return banco, efeitos


def _falas(banco, falas):
    """`[(quem, texto, há_quanto)]` gravadas em `messages`, como o webhook as grava."""
    agora = datetime.now(timezone.utc)
    for quem, texto, ha in falas:
        banco.tabelas.setdefault("messages", []).append({
            "id": "m-%s" % uuid.uuid4().hex[:8], "conversation_id": "conv-y",
            "role": "user" if quem == "segurado" else "assistant", "content": texto, "payload": {},
            "created_at": (agora - ha).isoformat()})


def _turno(banco, ultima):
    tool = IT.InsurerDispatchTool(company_id=EMPRESA_A, supabase_client=banco)
    calls = [{"name": "insurer_dispatch", "id": "c-%s" % uuid.uuid4().hex[:6],
              "args": {**CASO_AUTO, "dados_confirmados": True}}]
    st = estado([HumanMessage(content=ultima), AIMessage(content="", tool_calls=calls)])
    saida = asyncio.run(N.tool_node(st, tools=[tool]))
    return "\n".join(str(m.content) for m in saida["messages"])


def _status(lido: str) -> str:
    for s in ("already_dispatched", "confirm_first", "dispatched"):
        if "'status': '%s'" % s in lido:
            return s
    return lido[:200]


MIN, DIA = timedelta(minutes=1), timedelta(days=1)


# ─── o caso NOVO, semanas depois, mesmo telefone ──────────────────────────────────────────────
def test_bn1_caso_novo_30_dias_depois_nao_e_ja_acionado(borda, ao_vivo, classificador_ok):
    """A sonda do juiz, pelo motor: nasce VERMELHA (already_dispatched) sem o corte por assunto."""
    banco, efeitos = _mundo(borda, enviado_ha=30 * DIA)
    _falas(banco, [("segurado", PEDIDO_NOVO, 2 * MIN)])
    lido = _turno(banco, PEDIDO_NOVO)
    assert _status(lido) == "confirm_first", lido[:400]
    assert not any(t in lido for t in DIZ_QUE_JA_ESTA), lido[:400]
    assert efeitos == []


def test_bn1_controle_a_mesma_conversa_sem_o_fato_antigo(borda, ao_vivo, classificador_ok):
    """§9.2 — a linha de controle: SEM o acionamento antigo na ficha, o MESMO turno dá o MESMO
    `confirm_first`. A única diferença entre os dois é o fato antigo — e ele deixou de pesar."""
    banco, efeitos = _mundo(borda, enviado_ha=None)
    _falas(banco, [("segurado", PEDIDO_NOVO, 2 * MIN)])
    assert _status(_turno(banco, PEDIDO_NOVO)) == "confirm_first"
    assert efeitos == []


def test_bn1_o_caso_antigo_inteiro_na_conversa_e_o_novo_depois_do_silencio(borda, ao_vivo, classificador_ok):
    """O cenário real: a conversa guarda o caso de 30 dias atrás (pergunta + sim + anúncio) e o novo
    chega depois do silêncio — a regra dos N dias abre o assunto novo, e o sim velho não vale nada."""
    banco, efeitos = _mundo(borda, enviado_ha=30 * DIA - 5 * MIN)
    _falas(banco, [("segurado", "meu carro morreu, preciso de guincho", 30 * DIA),
                   ("agente", PERGUNTA, 30 * DIA - 2 * MIN), ("segurado", "sim", 30 * DIA - 3 * MIN),
                   ("agente", "Pronto! O guincho já está a caminho.", 30 * DIA - 6 * MIN),
                   ("segurado", PEDIDO_NOVO, 2 * MIN)])
    lido = _turno(banco, PEDIDO_NOVO)
    assert _status(lido) == "confirm_first", lido[:400]
    assert not any(t in lido for t in DIZ_QUE_JA_ESTA) and efeitos == []


def test_bn1_caso_novo_com_pergunta_e_sim_novos_aciona(borda, ao_vivo, classificador_ok):
    banco, efeitos = _mundo(borda, enviado_ha=30 * DIA)
    _falas(banco, [("segurado", PEDIDO_NOVO, 5 * MIN), ("agente", PERGUNTA, 4 * MIN), ("segurado", "sim", 3 * MIN)])
    _turno(banco, "sim")
    assert efeitos == [("START", "guincho")], efeitos


def test_bn1_resolvido_em_tambem_fecha_o_assunto(borda, ao_vivo, classificador_ok):
    """A outra metade da MESMA régua: `conversations.resolvido_em` (o atendimento encerrado há 1 h)
    separa o acionamento de 2 h atrás do pedido novo de agora — sem silêncio de N dias no meio."""
    banco, efeitos = _mundo(borda, enviado_ha=120 * MIN, resolvido_ha=60 * MIN)
    _falas(banco, [("segurado", "preciso de guincho", 130 * MIN), ("agente", PERGUNTA, 128 * MIN),
                   ("segurado", "sim", 127 * MIN), ("segurado", PEDIDO_NOVO, 2 * MIN)])
    lido = _turno(banco, PEDIDO_NOVO)
    assert _status(lido) == "confirm_first" and efeitos == [], lido[:400]


# ─── os CONTROLES: o MESMO assunto continua idempotente ───────────────────────────────────────
def test_bn1_controle_acionado_ha_5_min_no_mesmo_assunto_e_ja_acionado(borda, ao_vivo, classificador_ok):
    banco, efeitos = _mundo(borda, enviado_ha=5 * MIN)
    _falas(banco, [("segurado", "preciso de guincho", 20 * MIN), ("agente", PERGUNTA, 15 * MIN),
                   ("segurado", "sim", 14 * MIN), ("agente", "Pronto! O guincho já está a caminho.", 4 * MIN),
                   ("segurado", "valeu", 1 * MIN)])
    lido = _turno(banco, "valeu")
    assert _status(lido) == "already_dispatched", lido[:400]
    assert efeitos == []


def test_bn1_controle_resolvido_ANTES_do_acionamento_nao_separa(borda, ao_vivo, classificador_ok):
    """`resolvido_em` de um atendimento anterior AO acionamento não o tira do assunto em aberto."""
    banco, efeitos = _mundo(borda, enviado_ha=5 * MIN, resolvido_ha=3 * DIA)
    _falas(banco, [("segurado", "preciso de guincho", 20 * MIN), ("agente", PERGUNTA, 15 * MIN),
                   ("segurado", "sim", 14 * MIN), ("segurado", "valeu", 1 * MIN)])
    assert _status(_turno(banco, "valeu")) == "already_dispatched" and efeitos == []


# ─── o classificador fora do ar ───────────────────────────────────────────────────────────────
def test_bn1_classificador_fora_do_ar_com_fato_antigo_pede_de_novo(borda, ao_vivo, classificador_fora_do_ar):
    """Antes do conserto 2: "já está com a seguradora" (a prova falha pelo classificador e o fato antigo
    do mesmo serviço virava `already_dispatched`). Agora: o pedido de confirmação, e nada sai."""
    banco, efeitos = _mundo(borda, enviado_ha=30 * DIA)
    _falas(banco, [("segurado", "meu carro quebrou de novo", 5 * MIN), ("agente", PERGUNTA, 4 * MIN),
                   ("segurado", "sim", 3 * MIN)])
    lido = _turno(banco, "sim")
    assert _status(lido) == "confirm_first", lido[:400]
    assert "classificador" in lido and not any(t in lido for t in DIZ_QUE_JA_ESTA), lido[:400]
    assert efeitos == []


def test_bn1_controle_classificador_fora_do_ar_no_mesmo_assunto_continua_ja_acionado(
        borda, ao_vivo, classificador_fora_do_ar):
    banco, efeitos = _mundo(borda, enviado_ha=2 * MIN)
    _falas(banco, [("segurado", "meu carro quebrou", 5 * MIN), ("agente", PERGUNTA, 4 * MIN),
                   ("segurado", "sim", 3 * MIN)])
    assert _status(_turno(banco, "sim")) == "already_dispatched" and efeitos == []


# ─── a conversa ilegível: a MESMA janela de N dias, contada de agora ──────────────────────────
@pytest.mark.parametrize("ha, conta", [(30 * DIA, False), (8 * DIA, False), (1 * DIA, True), (5 * MIN, True)])
def test_bn1_conversa_ilegivel_usa_a_janela_de_n_dias(monkeypatch, ha, conta):
    from app.agents import historico_da_conversa as HC

    async def _ilegivel(*a, **k):
        return HC.Historico(erro="TimeoutError")

    monkeypatch.setattr(HC, "historico_do_atendimento", _ilegivel)
    monkeypatch.delenv("JANELA_SILENCIO_HUMANO_DIAS", raising=False)
    tool = IT.InsurerDispatchTool(company_id=EMPRESA_A, supabase_client=object())
    em = datetime.now(timezone.utc) - ha
    assert asyncio.run(tool._do_assunto_em_aberto(object(), SESSAO_A, em)) is conta
