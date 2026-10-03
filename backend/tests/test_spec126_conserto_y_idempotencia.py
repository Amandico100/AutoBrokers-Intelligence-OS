# -*- coding: utf-8 -*-
r"""SPEC-126 · CONSERTO Y · itens 2 e 3 — o MESMO "sim" nunca aciona duas vezes, e o caso acionado
não some até o protocolo chegar.

📊 red team B3 (02/10, HEAD f44526c, `scratchpad/test_rt126_idempotencia.py`): duas chamadas no mesmo
turno → `dispatched` + `queued` (um 2º guincho na fila); e no turno seguinte o anúncio natural do
agente ("Pronto! O guincho já está a caminho 🚗") NÃO gastava o sim — a confirmação era gasta pela
PROSA (`_RX_ACIONAMENTO_ANUNCIADO`), não pelo fato.
📊 juiz pendência 1: 1.176 fichas, 0 com `acionamento.enviado_em` — nenhum escritor; o caso acionado
só era "pós-acionamento" para a R9 depois do protocolo.

O conserto: o FATO vai para a ficha DURÁVEL no instante do efeito (`InsurerDispatchTool.
_marcar_o_acionamento` → `attendance_ficha.gravar` → `fundir`), e a ficha gasta a confirmação que veio
antes dele (`confirmacao_comprovada(acionado_em=…)`); o mesmo serviço sem pergunta + ok NOVOS devolve
`already_dispatched` — nada sai, nada entra na fila.

Pelo MOTOR (§9.4): `nodes.tool_node` REAL → `InsurerDispatchTool._arun` REAL → portão REAL →
`attendance_ficha` REAL → `human_handoff._e_pos_acionamento` REAL. Dublês só na BORDA: o banco em
memória que filtra de verdade (`test_spec126_u3_d1_parente_aciona.borda`), o canal com a seguradora
(`dispatch_router`, a integração, o WhatsApp — `test_spec125_conserto_y.ao_vivo`) e o classificador
(`llm_factory.invocar_com_reserva`, dizendo ok). Nenhuma rede, nenhum modelo pago, nada enviado.

Rodar (de backend/):
    PYTHONIOENCODING=utf-8 python -m pytest tests/test_spec126_conserto_y_idempotencia.py -q -p no:cacheprovider
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

PERGUNTA_CHAVEIRO = "Chaveiro para o carro de placa AAA0A91, na Rua Um, 100. Posso acionar?"
CASO_CHAVEIRO = {**CASO_AUTO, "subservice": "chaveiro", "problema_descricao": "a chave ficou trancada dentro"}


@pytest.fixture(autouse=True)
def _classificador_na_borda():
    from app.services.evals import bancada_confirmacao as BC

    with BC.classificador_duble_na_borda() as chamadas:   # diz OK: quem decide é a rede + o fato
        yield chamadas


@pytest.fixture
def mundo(borda, ao_vivo):
    """O banco com a conversa e o canal com a seguradora que CONTA (start e fila)."""
    banco, _prov = borda
    rot = sys.modules["app.services.dispatch_router"]
    efeitos: list = []

    async def _start(**kw):
        efeitos.append(("START", kw.get("subservice")))
        return {"ok": True, "session": {"client_phone": kw.get("client_phone"),
                                        "subservice": kw.get("subservice")}}

    async def _enq(company_id, insurer_phone, req):
        efeitos.append(("FILA", req.get("subservice")))
        return 1

    rot.start_live_dispatch, rot.enqueue_dispatch = _start, _enq
    banco.tabelas.setdefault("conversations", []).append(
        {"id": "conv-y", "company_id": EMPRESA_A, "session_id": SESSAO_A, "channel": "whatsapp",
         "ficha_atendimento": None})
    return banco, efeitos


def _falas(banco, falas, *, depois=False):
    """As falas gravadas em `messages` (o webhook grava antes do turno): as de ANTES do acionamento,
    uma por minuto até ~agora; as de DEPOIS (`depois=True`), segundos depois de agora — isto é,
    depois do `enviado_em` que o turno anterior gravou."""
    agora = datetime.now(timezone.utc)
    for k, (quem, texto) in enumerate(falas):
        quando = agora + timedelta(seconds=k + 1) if depois else agora - timedelta(minutes=30 - k)
        banco.tabelas.setdefault("messages", []).append({
            "id": "m-%s" % uuid.uuid4().hex[:8], "conversation_id": "conv-y",
            "role": "user" if quem == "segurado" else "assistant", "content": texto, "payload": {},
            "created_at": quando.isoformat()})


def _turno(banco, *chamadas, ultima="sim"):
    """UM turno do `tool_node` REAL com a ferramenta REAL: o modelo chama `insurer_dispatch` n vezes."""
    tool = IT.InsurerDispatchTool(company_id=EMPRESA_A, supabase_client=banco)
    calls = [{"name": "insurer_dispatch", "id": "call-%s" % uuid.uuid4().hex[:6],
              "args": {**caso, "dados_confirmados": True}} for caso in chamadas]
    st = estado([HumanMessage(content=ultima), AIMessage(content="", tool_calls=calls)])
    return asyncio.run(N.tool_node(st, tools=[tool]))


def _ficha(banco) -> dict:
    return next(c for c in banco.tabelas["conversations"] if c["id"] == "conv-y").get("ficha_atendimento") or {}


def _starts(efeitos, servico="guincho"):
    return [e for e in efeitos if e == ("START", servico)]


# ─── (a) duas chamadas no MESMO turno ─────────────────────────────────────────────────────────
def test_b3a_duas_chamadas_no_mesmo_turno_acionam_uma_vez(mundo):
    banco, efeitos = mundo
    _falas(banco, [("segurado", "meu carro morreu, preciso de guincho"), ("agente", PERGUNTA), ("segurado", "sim")])
    saida = _turno(banco, CASO_AUTO, CASO_AUTO)
    assert len(_starts(efeitos)) == 1 and not [e for e in efeitos if e[0] == "FILA"], efeitos
    lido = "\n".join(str(m.content) for m in saida["messages"])
    assert "[ACIONAMENTO REAL INICIADO]" in lido and "NADA FOI ENVIADO DE NOVO" in lido, lido


def test_b3a_a_sessao_viva_do_mesmo_cliente_nao_vai_para_a_fila(mundo):
    """Defesa em profundidade (duas mensagens ao MESMO tempo, antes de a ficha ser lida): o roteador diz
    'número ocupado' com a sessão DESTE cliente e serviço → nada entra na fila."""
    banco, efeitos = mundo
    rot = sys.modules["app.services.dispatch_router"]

    async def _ocupado(**kw):
        efeitos.append(("OCUPADO", kw.get("subservice")))
        return {"ok": False, "error": "dispatch_already_active",
                "session": {"client_phone": kw.get("client_phone"), "subservice": kw.get("subservice")}}

    rot.start_live_dispatch = _ocupado
    _falas(banco, [("segurado", "preciso de guincho"), ("agente", PERGUNTA), ("segurado", "sim")])
    _turno(banco, CASO_AUTO)
    assert not [e for e in efeitos if e[0] == "FILA"], efeitos


def test_b3a_controle_numero_ocupado_por_OUTRO_cliente_vai_para_a_fila(mundo):
    banco, efeitos = mundo
    rot = sys.modules["app.services.dispatch_router"]

    async def _ocupado(**kw):
        return {"ok": False, "error": "dispatch_already_active",
                "session": {"client_phone": "5511900000000", "subservice": "guincho"}}

    rot.start_live_dispatch = _ocupado
    _falas(banco, [("segurado", "preciso de guincho"), ("agente", PERGUNTA), ("segurado", "sim")])
    _turno(banco, CASO_AUTO, CASO_AUTO)
    assert [e for e in efeitos if e[0] == "FILA"] == [("FILA", "guincho")], efeitos   # UMA vez, não duas
    assert (_ficha(banco).get("acionamento") or {}).get("enfileirado_em")


# ─── (b) o turno seguinte: o FATO gasta o sim, não a prosa ────────────────────────────────────
ANUNCIOS = ["Pronto! O guincho já está a caminho 🚗",
            "Prontinho, guincho a caminho! Te aviso quando a seguradora mandar a previsão.",
            "Tudo certo! A seguradora já recebeu seu pedido."]


@pytest.mark.parametrize("anuncio", ANUNCIOS)
def test_b3b_o_turno_seguinte_nao_reusa_o_sim(mundo, anuncio):
    banco, efeitos = mundo
    _falas(banco, [("segurado", "preciso de guincho"), ("agente", PERGUNTA), ("segurado", "sim")])
    _turno(banco, CASO_AUTO)                                       # o 1º sai
    assert len(_starts(efeitos)) == 1
    _falas(banco, [("agente", anuncio), ("segurado", "valeu")], depois=True)
    saida = _turno(banco, CASO_AUTO, ultima="valeu")                # o modelo chama de novo
    assert len(_starts(efeitos)) == 1, "o mesmo sim acionou DUAS vezes: %s" % efeitos
    assert "NADA FOI ENVIADO DE NOVO" in "\n".join(str(m.content) for m in saida["messages"])


def test_b3b_controle_sem_o_fato_na_ficha_a_prosa_nao_gastava(mundo):
    """§9.2 — a linha de controle: as MESMAS falas, sem acionamento na ficha → aciona. Quem gasta o sim
    é o FATO durável (o anúncio "Pronto! O guincho já está a caminho" não casa a regex da prosa)."""
    banco, efeitos = mundo
    _falas(banco, [("segurado", "preciso de guincho"), ("agente", PERGUNTA), ("segurado", "sim"),
                   ("agente", ANUNCIOS[0]), ("segurado", "valeu")])
    _turno(banco, CASO_AUTO, ultima="valeu")
    assert len(_starts(efeitos)) == 1, efeitos


def test_b3b_webhook_duplicado_a_mesma_mensagem_duas_vezes_um_acionamento(mundo):
    banco, efeitos = mundo
    _falas(banco, [("segurado", "preciso de guincho"), ("agente", PERGUNTA), ("segurado", "sim")])
    _turno(banco, CASO_AUTO)
    _turno(banco, CASO_AUTO)                                       # o mesmo "sim" processado de novo
    assert len(_starts(efeitos)) == 1 and not [e for e in efeitos if e[0] == "FILA"], efeitos


def test_b3b_controle_servico_diferente_com_o_seu_ok_aciona(mundo):
    banco, efeitos = mundo
    _falas(banco, [("segurado", "preciso de guincho"), ("agente", PERGUNTA), ("segurado", "sim")])
    _turno(banco, CASO_AUTO)
    _falas(banco, [("agente", ANUNCIOS[0]), ("segurado", "e a chave ficou trancada, preciso de chaveiro"),
                   ("agente", PERGUNTA_CHAVEIRO), ("segurado", "pode mandar")], depois=True)
    _turno(banco, CASO_CHAVEIRO, ultima="pode mandar")
    assert len(_starts(efeitos)) == 1 and _starts(efeitos, "chaveiro") == [("START", "chaveiro")], efeitos


def test_b3b_controle_o_mesmo_servico_com_pergunta_e_ok_NOVOS_aciona(mundo):
    """"Um 2º acionamento do MESMO serviço só com NOVA pergunta + NOVO ok" — e com eles, sai."""
    banco, efeitos = mundo
    _falas(banco, [("segurado", "preciso de guincho"), ("agente", PERGUNTA), ("segurado", "sim")])
    _turno(banco, CASO_AUTO)
    _falas(banco, [("agente", ANUNCIOS[0]), ("segurado", "preciso de OUTRO guincho, pro carro da frente"),
                   ("agente", PERGUNTA), ("segurado", "sim, pode")], depois=True)
    _turno(banco, CASO_AUTO, ultima="sim, pode")
    assert len(_starts(efeitos)) == 2, efeitos


# ─── item 3: o caso acionado é PÓS-ACIONAMENTO já no turno seguinte ──────────────────────────
def test_item3_dispatched_grava_enviado_em_e_a_r9_reconhece_o_pos_acionamento(mundo):
    from app.agents.tools.human_handoff import _e_pos_acionamento

    banco, efeitos = mundo
    _falas(banco, [("segurado", "preciso de guincho"), ("agente", PERGUNTA), ("segurado", "sim")])
    conversa = next(c for c in banco.tabelas["conversations"] if c["id"] == "conv-y")
    assert not _e_pos_acionamento(dict(conversa)), "controle: ANTES do acionamento não é pós"
    _turno(banco, CASO_AUTO)
    acion = _ficha(banco).get("acionamento") or {}
    assert acion.get("enviado_em") and acion.get("servico") == "guincho", acion
    assert acion.get("seguradora") == "allianz" and not acion.get("protocolo"), acion
    # a próxima fala ("cancela") lê a MESMA conversa durável: o protocolo ainda não veio
    assert _e_pos_acionamento(dict(conversa)), "o caso acionado sumiu até o protocolo chegar"


def test_item3_controle_o_que_nao_saiu_nao_marca(mundo):
    banco, efeitos = mundo
    _falas(banco, [("segurado", "preciso de guincho"), ("agente", PERGUNTA), ("segurado", "pode deixar")])
    _turno(banco, CASO_AUTO, ultima="pode deixar")
    assert not efeitos and not (_ficha(banco).get("acionamento") or {}).get("enviado_em")


def test_item3_dois_tenants_a_marca_de_A_nao_vale_para_B(mundo):
    """§7: a ficha é lida com `company_id` — o acionamento de A não gasta o sim de B no mesmo telefone."""
    from test_spec126_u3_d1_parente_aciona import EMPRESA_B, SESSAO_B

    banco, efeitos = mundo
    _falas(banco, [("segurado", "preciso de guincho"), ("agente", PERGUNTA), ("segurado", "sim")])
    _turno(banco, CASO_AUTO)
    banco.tabelas["conversations"].append({"id": "conv-b", "company_id": EMPRESA_B, "session_id": SESSAO_B,
                                           "channel": "whatsapp", "ficha_atendimento": None})
    agora = datetime.now(timezone.utc)
    for k, (quem, texto) in enumerate([("segurado", "preciso de guincho"), ("agente", PERGUNTA), ("segurado", "sim")]):
        banco.tabelas["messages"].append({"id": "mb%d" % k, "conversation_id": "conv-b",
                                          "role": "user" if quem == "segurado" else "assistant",
                                          "content": texto, "payload": {},
                                          "created_at": (agora - timedelta(minutes=50 - k)).isoformat()})
    tool = IT.InsurerDispatchTool(company_id=EMPRESA_B, supabase_client=banco)
    st = estado([HumanMessage(content="sim"), AIMessage(content="", tool_calls=[{
        "name": "insurer_dispatch", "id": "call-b", "args": {**CASO_AUTO, "dados_confirmados": True}}])],
        empresa=EMPRESA_B, sessao=SESSAO_B)
    asyncio.run(N.tool_node(st, tools=[tool]))
    assert len(_starts(efeitos)) == 2, efeitos
