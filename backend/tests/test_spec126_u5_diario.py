# -*- coding: utf-8 -*-
r"""SPEC-126 U5 · P-125-06 — o D7 da SPEC-125 INTEIRO: os 4 momentos e os 4 sinais escritos.

```
momento            quem escreve (o ponto)                                       antes da U5
deduziu            nodes.agent_node, fim do turno — o insurer_dispatch DECLARA  ponto marcado
                   `slots_deduzidos` (dito × deduzido)
respondeu_regra    nodes.agent_node, fim do turno (SPEC-125)                    escrito
nao_chamou_pessoa  human_handoff._segunda_chance — a MESMA linha do contador     ponto marcado
chamou_pessoa      human_handoff._registrar_chamou_pessoa — a mesma linha       escrito, sem `momento`
sinal              quem fecha
agente_repetiu_pergunta  o fiscal da pergunta repetida (SPEC-125)               escrito
segurado_corrigiu · segurado_repetiu · segurado_pediu_pessoa
                   nodes.agent_node, 1ª passada do turno — a fala NOVA fecha a   nunca escritos
                   última pendente criada ANTES do turno, na janela
```

O MOTOR é o real: `nodes.agent_node` com modelo dublê, `diario_de_decisoes` (máscara, listas, idempotência)
sobre o banco em memória da SPEC-123 com as COLUNAS do banco real e DUAS corretoras reais (ids por SELECT
read-only, sem nome — `test_spec123_diario_fio.banco`), e `HumanHandoffTool._arun` com a borda da SPEC-123.

    cd backend && PYTHONIOENCODING=utf-8 .venv/Scripts/python -m pytest tests/test_spec126_u5_diario.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

import pytest

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
for _c in (RAIZ, AQUI):
    if _c not in sys.path:
        sys.path.insert(0, _c)

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage  # noqa: E402

from app.agents import nodes as N  # noqa: E402
from app.services import diario_de_decisoes as D  # noqa: E402
from test_spec123_diario_fio import Banco, Mundo, banco  # noqa: E402,F401  (fixture: 2 corretoras reais)
from test_spec123_atendimento_segunda_chance import (  # noqa: E402,F401
    _banco, _conversa, _diario, _pedir, borda)


# =========================================================================== #
# 1 · os sinais do segurado — o motor puro, com as falas do acervo (mascaradas)
# =========================================================================== #
def _conversa_com(*falas_e_respostas):
    msgs = []
    for i, t in enumerate(falas_e_respostas):
        msgs.append(HumanMessage(content=t) if i % 2 == 0 else AIMessage(content=t))
    return msgs


@pytest.mark.parametrize("fala,sinal", [
    ("quero falar com um atendente", "segurado_pediu_pessoa"),
    ("me passa pra uma pessoa por favor", "segurado_pediu_pessoa"),
    ("não, é na rua de cima do posto", "segurado_corrigiu"),
    ("nao e o meu carro, e o da minha esposa", "segurado_corrigiu"),
    ("bradesco na verdade", "segurado_corrigiu"),
    ("Na verdade o vidro estourou sozinho", "segurado_corrigiu"),
    ("tá errado o endereço", "segurado_corrigiu"),
    ("já te falei que é na rua sete", "segurado_repetiu"),
    ("terceira vez que escrevo, cade o guincho??", "segurado_repetiu"),
])
def test_o_sinal_da_fala_nova(fala, sinal):
    msgs = _conversa_com("meu carro morreu na rua sete", "Onde o carro está agora?", fala)
    assert N.sinal_do_segurado(msgs) == sinal, fala


def test_a_mesma_fala_depois_da_resposta_do_agente_e_repeticao():
    msgs = _conversa_com("o carro está na rua sete 100", "Para onde levo o carro?", "o carro está na rua sete 100")
    assert N.sinal_do_segurado(msgs) == "segurado_repetiu"


@pytest.mark.parametrize("msgs", [
    _conversa_com("meu carro morreu", "Onde ele está?", "não é possível que demore tanto"),
    _conversa_com("meu carro morreu", "Onde ele está?", "estou na verdade perdida aqui, não sei a rua"),
    _conversa_com("sim", "Posso acionar?", "sim"),                                   # "sim" 2× responde 2 perguntas
    [HumanMessage(content="o carro está na rua sete 100"), HumanMessage(content="o carro está na rua sete 100")],
    _conversa_com("meu carro morreu", "Onde ele está?", "na rua sete 100"),
])
def test_controle_fala_comum_nao_e_sinal(msgs):
    """CONTROLE (§9.3): a régua CONSEGUE dizer não — "não é possível", "na verdade" no meio da fala,
    "sim" repetido, a mesma fala sem resposta do agente entre elas (rajada), a resposta comum."""
    assert N.sinal_do_segurado(msgs) is None


def test_so_a_primeira_passada_do_turno():
    assert N.e_a_primeira_passada_do_turno(_conversa_com("a", "b", "c"))
    meio = _conversa_com("a", "b", "c") + [
        AIMessage(content="", tool_calls=[{"name": "x", "args": {}, "id": "1", "type": "tool_call"}]),
        ToolMessage(content="ok", tool_call_id="1", name="x")]
    assert not N.e_a_primeira_passada_do_turno(meio)


# =========================================================================== #
# 2 · pelo agent_node real → o diário real (banco em memória com as colunas reais, 2 corretoras)
# =========================================================================== #
class _Modelo:
    def __init__(self, texto):
        self.texto = texto

    async def ainvoke(self, mensagens, config=None, **_k):
        return AIMessage(content=self.texto)


def _no(mensagens, final, *, company_id, conversa, monkeypatch):
    """Roda o `agent_node` REAL e devolve as tarefas do diário que ele agendou (fora do caminho da
    resposta, como no produto) — para rodá-las depois contra o banco-dublê."""
    import app.services.activity_log as AL

    async def _log(*_a, **_k):
        return None

    async def _conv(state):                       # a conversa DESTA sessão NESTA corretora
        return conversa if str(state.get("company_id")) == company_id else ""

    tarefas = []
    monkeypatch.setattr(AL, "log_activity", _log)
    monkeypatch.setattr(N, "_em_segundo_plano", tarefas.append)
    monkeypatch.setattr(N, "_id_da_conversa_do_turno", _conv)
    estado = {"messages": list(mensagens), "company_id": company_id, "session_id": "web:u5",
              "user_id": "u", "company_config": {},
              "agent_data": {"agent_role": "attendance", "prompt_versao": "v2"},
              "system_prompt": "p", "static_prompt": "p", "dynamic_context": "", "ficha_atendimento": {},
              "tools_used": []}
    asyncio.run(N.agent_node(estado, None, _Modelo(final)))
    return tarefas


def _rodar_tarefas(tarefas, mundo, monkeypatch):
    banco_async = Banco(mundo, assincrono=True)

    async def _cliente():
        return banco_async

    monkeypatch.setattr(D, "_cliente", _cliente)
    for t in tarefas:
        asyncio.run(t)


#: o turno do acionamento: o modelo DECLARA que deduziu a rodovia (ele escreveu "BR-101")
ARGS_DEDUZIDOS = {"subservice": "guincho", "line_kind": "auto", "local_atual": "BR-101, km 30",
                  "via_ou_rodovia_opcao": "rodovia", "slots_deduzidos": ["via_ou_rodovia_opcao"]}


def _turno_do_acionamento(args=None):
    return [HumanMessage(content="bati no barranco na BR-101 km 30, preciso de guincho"),
            AIMessage(content="", tool_calls=[{"name": "insurer_dispatch", "args": dict(args or ARGS_DEDUZIDOS),
                                               "id": "d1", "type": "tool_call"}]),
            ToolMessage(content="confirm_first · NADA foi acionado. Confirme com o segurado.",
                        tool_call_id="d1", name="insurer_dispatch")]


FINAL_1 = "Antes de acionar, me confirma: guincho na rodovia, BR-101 km 30?"


def _agora(delta_min=0.0):
    return (datetime.now(timezone.utc) + timedelta(minutes=delta_min)).isoformat()


def test_deduziu_e_escrito_no_fim_do_turno_e_nao_dobra(banco, monkeypatch):
    A, conv = banco["A"], str(uuid.uuid4())
    mundo = Mundo(banco["colunas"])
    for _ in range(2):                                   # a MESMA dedução numa nova tentativa
        _rodar_tarefas(_no(_turno_do_acionamento(), FINAL_1, company_id=A, conversa=conv,
                           monkeypatch=monkeypatch), mundo, monkeypatch)
    linhas = mundo.rows("diario_de_decisoes")
    assert len(linhas) == 1, linhas
    l = linhas[0]
    assert (l["company_id"], l["conversation_id"], l["origem"], l["momento"], l["classe"], l["resultado"]) == \
        (A, conv, "atendimento", "deduziu", "deduzir", "pendente")
    assert "rodovia" in l["valor_completo"] and "BR-101" in l["tela_completa"]
    assert "_" not in l["explicacao_para_gente"], l["explicacao_para_gente"]          # D7: língua de gente
    assert "entendeu que" in l["explicacao_para_gente"]


def test_controle_sem_declaracao_nada_e_escrito(banco, monkeypatch):
    """CONTROLE: o mesmo turno SEM `slots_deduzidos` (o que o modelo disse) — zero linhas; e o slot
    declarado mas vazio também não conta."""
    mundo = Mundo(banco["colunas"])
    for args in ({k: v for k, v in ARGS_DEDUZIDOS.items() if k != "slots_deduzidos"},
                 {**ARGS_DEDUZIDOS, "via_ou_rodovia_opcao": ""}):
        _rodar_tarefas(_no(_turno_do_acionamento(args), FINAL_1, company_id=banco["A"], conversa="c-x",
                           monkeypatch=monkeypatch), mundo, monkeypatch)
    assert mundo.rows("diario_de_decisoes") == []


def _semear(mundo, cid, conv, *, minutos, momento="deduziu"):
    linha = {"id": str(uuid.uuid4()), "company_id": cid, "conversation_id": conv, "origem": "atendimento",
             "momento": momento, "classe": "deduzir", "acao": "respondeu_segurado", "modo": "on",
             "resultado": "pendente", "chave_idempotencia": "u5:%s" % uuid.uuid4().hex,
             "explicacao_para_gente": "linha semeada pelo teste", "created_at": _agora(minutos)}
    mundo.rows("diario_de_decisoes").append(linha)
    return linha


@pytest.mark.parametrize("fala,sinal", [
    ("não, é na rua de cima do posto", "segurado_corrigiu"),
    ("já te falei que é na BR-101", "segurado_repetiu"),
    ("quero falar com um atendente", "segurado_pediu_pessoa"),
])
def test_a_fala_nova_fecha_a_linha_do_julgamento_anterior_so_desta_corretora(banco, monkeypatch, fala, sinal):
    """🔴 a 1ª passada do turno fecha a última pendente criada ANTES dele, na janela, DESTA corretora:
    nem a da outra corretora (mesma conversa, mais nova), nem a que o próprio turno grava (depois),
    nem a de 2 horas atrás."""
    A, Bc, conv = banco["A"], banco["B"], str(uuid.uuid4())
    mundo = Mundo(banco["colunas"])
    velha = _semear(mundo, A, conv, minutos=-120)
    alvo = _semear(mundo, A, conv, minutos=-5)
    outra = _semear(mundo, Bc, conv, minutos=-1)          # 🔴 outra corretora, mais nova
    do_turno = _semear(mundo, A, conv, minutos=+1, momento="chamou_pessoa")
    msgs = _turno_do_acionamento() + [AIMessage(content=FINAL_1), HumanMessage(content=fala)]
    _rodar_tarefas(_no(msgs, "Certo, anotei.", company_id=A, conversa=conv, monkeypatch=monkeypatch),
                   mundo, monkeypatch)
    estado = {l["id"]: l["resultado"] for l in mundo.rows("diario_de_decisoes")}
    assert estado[alvo["id"]] == sinal, estado
    assert estado[outra["id"]] == estado[velha["id"]] == estado[do_turno["id"]] == "pendente", estado
    for q in mundo.registro:
        if q.nome == "diario_de_decisoes" and q.op in ("select", "update"):
            assert any(p[0] == "eq" and p[1] == "company_id" for p in q.pred), (q.op, q.pred)


def test_controle_sem_julgamento_na_janela_nada_fecha(banco, monkeypatch):
    mundo = Mundo(banco["colunas"])
    conv = str(uuid.uuid4())
    velha = _semear(mundo, banco["A"], conv, minutos=-120)
    msgs = [HumanMessage(content="oi"), AIMessage(content="Oi!"), HumanMessage(content="não, é na rua de cima")]
    _rodar_tarefas(_no(msgs, "Certo.", company_id=banco["A"], conversa=conv, monkeypatch=monkeypatch),
                   mundo, monkeypatch)
    assert velha["resultado"] == "pendente"


def test_a_volta_da_ferramenta_nao_repete_o_sinal(banco, monkeypatch):
    """O nó roda de novo depois de cada ferramenta: o sinal é UM por turno (só a 1ª passada)."""
    mundo = Mundo(banco["colunas"])
    conv = str(uuid.uuid4())
    alvo = _semear(mundo, banco["A"], conv, minutos=-5)
    msgs = [HumanMessage(content="não, é na rua de cima"),
            AIMessage(content="", tool_calls=[{"name": "knowledge_base_search", "args": {}, "id": "k",
                                               "type": "tool_call"}]),
            ToolMessage(content="{}", tool_call_id="k", name="knowledge_base_search")]
    _rodar_tarefas(_no(msgs, "Certo.", company_id=banco["A"], conversa=conv, monkeypatch=monkeypatch),
                   mundo, monkeypatch)
    assert alvo["resultado"] == "pendente"


# =========================================================================== #
# 3 · nao_chamou_pessoa e chamou_pessoa: a MESMA linha do handoff ganha o momento (nunca dobrada)
# =========================================================================== #
def test_a_segunda_chance_e_o_nao_chamou_pessoa_e_a_passagem_e_o_chamou_pessoa(borda):
    import app.agents.tools.human_handoff as H

    cid = "c-u5-0001"
    b = _banco(_conversa(cid))
    assert _pedir(H, b, cid, "não sei responder a dúvida do cliente") == H.SEGUNDA_CHANCE_DO_HANDOFF
    _pedir(H, b, cid, "o cliente quer saber se a franquia muda e eu não achei")
    linhas = _diario(b, cid)
    assert [l.get("momento") for l in linhas] == ["nao_chamou_pessoa", "chamou_pessoa"], linhas
    assert [l["acao"] for l in linhas] == ["perguntou_segurado", "chamou_pessoa"]      # o que já era, igual
    assert len(linhas) == 2, "uma linha por fato — o momento não dobra a linha"


def test_registrar_decisao_recusa_momento_fora_da_conversa(banco, monkeypatch):
    mundo = Mundo(banco["colunas"])
    _rodar_tarefas([D.registrar_decisao(
        company_id=banco["A"], origem="acionamento", work_run_id=None, conversation_id=None, seguradora="x",
        ramo="auto", rota="r", servico="s", tela="t", classe="responder_com_dado", acao="respondeu_ura",
        valor="1", nota=None, limiar=None, motivo="", explicacao_para_gente="", modelo="", segunda_opiniao=None,
        modo="on", gatilho="g", chave_idempotencia="u5:momento:fora", momento="deduziu")], mundo, monkeypatch)
    assert mundo.rows("diario_de_decisoes") == []
