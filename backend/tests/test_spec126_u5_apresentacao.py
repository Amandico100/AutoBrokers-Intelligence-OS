# -*- coding: utf-8 -*-
r"""SPEC-126 U5 · P-125-04 — a apresentação UMA vez por assunto, por INTENÇÃO.

```
📊 o que o acervo gravado mostra (sem LLM)
   Sol (Z e U0) se apresenta "Aqui é a <nome>, da <corretora>." — SEM "assistente virtual". A régua
   antiga (`a_resposta_se_apresenta`) não contava essa apresentação → a ficha seguia pedindo → o turno
   seguinte se apresentava DE NOVO.
   e o modelo que se apresenta JUNTO da ferramenta e de novo no texto final, com outras palavras:
   a junção (`com_o_que_foi_dito_antes_da_ferramenta`) só tirava o trecho IDÊNTICO.
```

O que se afirma é o MOTOR (§9.4): `o_fim_do_atendimento.a_resposta_se_apresenta` sobre as falas
GRAVADAS, `nodes.agent_node` real com modelo dublê, e o turno inteiro pela bancada N3 (o grafo real,
o `_build_initial_state` real, o passo 9 do webhook) com roteiro. Controles: a apresentação que nunca
saiu continua sendo pedida UMA vez (o Sol C1 da U0) e o segurado que pergunta "quem é?" ouve o nome.

⛔ Sem rede, sem banco real, sem LLM. O nome do agente e da corretora vêm do agente FICTÍCIO da bancada.

    cd backend && PYTHONIOENCODING=utf-8 .venv/Scripts/python -m pytest tests/test_spec126_u5_apresentacao.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
for _c in (RAIZ, AQUI):
    if _c not in sys.path:
        sys.path.insert(0, _c)

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage  # noqa: E402

from app.agents import nodes as N  # noqa: E402
from app.services import o_fim_do_atendimento as F  # noqa: E402
from app.services.evals import bancada as B  # noqa: E402
from app.services.evals import dubles as DB  # noqa: E402

RESULTADOS = Path(AQUI) / "corpus" / "bancada" / "RESULTADOS"
Z_SOL = RESULTADOS / "conversa_z_sol_v2.json"
U0_OUTROS = RESULTADOS / "spec126_u0_sol_outros_k1.json"
U0_CRITICOS = RESULTADOS / "spec126_u0_sol_criticos_k2.json"

#: o agente e a corretora FICTÍCIOS da bancada (os das conversas gravadas) — nunca um nome real
_MOLDE = DB.materializar(B.agente_molde("A"))
NOME = _MOLDE["name"]
CORRETORA = DB.materializar("{{CORRETORA:A}}")


def _fala_gravada(arquivo: Path, chave: str, turno: int, tentativa: int = 1) -> str:
    for r in json.loads(arquivo.read_text(encoding="utf-8"))["resultados"]:
        if r["chave"] == chave and r["tentativa"] == tentativa:
            return r["rastro"]["estado"]["transcricao"][turno - 1]["agente"]
    raise AssertionError(f"{chave} t{turno} fora de {arquivo.name}")


#: (arquivo, chave, turno) — as apresentações GRAVADAS do Sol, nenhuma com "assistente virtual" nas 4
#: primeiras; a 5ª é a forma "Sou <nome>, assistente virtual" (C7 da U0)
APRESENTACOES_GRAVADAS = [
    (Z_SOL, "conv-c1-deducao-chuva", 2),
    (Z_SOL, "conv-c4-conversa-longa", 2),
    (U0_OUTROS, "conv-c1-deducao-chuva", 2),
    (U0_CRITICOS, "conv-c6-cobertura-vidro", 1),
    (U0_CRITICOS, "conv-c7-sinistro-disfarcado", 1),
]


# =========================================================================== #
# 1 · a régua da apresentação é a INTENÇÃO (o motor sobre as falas gravadas)
# =========================================================================== #
@pytest.mark.parametrize("arquivo,chave,turno", APRESENTACOES_GRAVADAS)
def test_as_apresentacoes_gravadas_do_sol_contam(arquivo, chave, turno):
    fala = _fala_gravada(arquivo, chave, turno)
    assert NOME in fala, "a fala gravada é a do agente fictício"
    assert F.a_resposta_se_apresenta(fala, agent_name=NOME), fala[:120]
    assert len(F.trechos_de_apresentacao(fala, agent_name=NOME)) == 1, fala[:120]


def test_reproducao_a_regua_antiga_nao_contava_quatro_das_cinco():
    """📊 o defeito medido: 4 das 5 apresentações gravadas não têm a marca antiga."""
    sem_marca = [c for a, c, t in APRESENTACOES_GRAVADAS
                 if "assistente virtual" not in _fala_gravada(a, c, t).lower()]
    assert len(sem_marca) == 4, sem_marca


def test_controle_fala_sem_apresentacao_nao_conta():
    """CONTROLE (§9.3 corolário): a régua CONSEGUE dizer não — a fala gravada de emergência (C10 t1,
    só segurança) e frases com o nome que não são apresentação."""
    c10 = _fala_gravada(U0_CRITICOS, "conv-c10-risco-a-vida-fumaca", 1)
    for texto in (c10, "Sou eu sim", f"A {NOME} vai te ajudar", "sou a responsável pelo seu caso"):
        assert not F.a_resposta_se_apresenta(texto, agent_name=NOME), texto
    # o "da <corretora>" só leva o NOME PRÓPRIO: o resto da frase é atendimento e nunca é cortado
    frase = f"Aqui é a {NOME}, da {CORRETORA} e vou te ajudar com o guincho."
    (a, b), = F.trechos_de_apresentacao(frase, agent_name=NOME)
    assert frase[b:].strip() == "e vou te ajudar com o guincho.", frase[b:]


# =========================================================================== #
# 2 · pelo agent_node real: dita JUNTO da ferramenta e de novo no final (paráfrase)
# =========================================================================== #
class _Modelo:
    def __init__(self, texto):
        self.texto, self.chamadas = texto, []

    async def ainvoke(self, mensagens, config=None, **_k):
        self.chamadas.append(mensagens)
        return AIMessage(content=self.texto)


def _turno(mensagens, texto_final, *, dynamic, monkeypatch):
    import app.services.activity_log as AL

    async def _log(*_a, **_k):
        return None

    monkeypatch.setattr(AL, "log_activity", _log)
    monkeypatch.setattr(N, "_em_segundo_plano", lambda coro: coro.close())   # o diário fica fora
    estado = {"messages": list(mensagens), "company_id": "empresa-teste", "session_id": "web:teste",
              "user_id": "u", "company_config": {},
              "agent_data": {"agent_role": "attendance", "prompt_versao": "v2", "name": NOME,
                             "config": {"display_name": NOME}},
              "system_prompt": "prompt", "static_prompt": "prompt", "dynamic_context": dynamic,
              "ficha_atendimento": {}, "tools_used": []}
    saida = asyncio.run(N.agent_node(estado, None, _Modelo(texto_final)))
    return str(getattr((saida.get("messages") or [None])[-1], "content", "") or "")


PEDE = F.linha_da_apresentacao(F.MODO_PRIMEIRA, agent_name=NOME, corretora=CORRETORA,
                               mensagem_do_segurado="meu vidro trincou, tem cobertura?")
CALA = F.linha_da_apresentacao(F.MODO_CALADO)


def _com_ferramenta(junto: str) -> list:
    return [HumanMessage(content="meu vidro trincou, tem cobertura?"),
            AIMessage(content=junto, tool_calls=[{"name": "knowledge_base_search", "args": {}, "id": "k1",
                                                  "type": "tool_call"}]),
            ToolMessage(content='{"found": true}', tool_call_id="k1", name="knowledge_base_search")]


def test_pelo_motor_duas_apresentacoes_com_parafrase_viram_uma():
    """🔴 (vermelho antes) a fala GRAVADA do Sol junto da ferramenta (U0 C6 t1) + o texto final que se
    apresenta de novo com outras palavras → sai UMA apresentação, e todo o resto do conteúdo."""
    junto = _fala_gravada(U0_CRITICOS, "conv-c6-cobertura-vidro", 1).split("\n")[0]
    final = f"Oi, aqui é a {NOME}, assistente virtual da {CORRETORA}! Seu seguro cobre o para-brisa."
    mp = pytest.MonkeyPatch()
    try:
        texto = _turno(_com_ferramenta(junto), final, dynamic="\n\n" + PEDE, monkeypatch=mp)
    finally:
        mp.undo()
    assert len(F.trechos_de_apresentacao(texto, agent_name=NOME)) == 1, texto
    assert texto.startswith(junto.split(".")[0]), "fica a PRIMEIRA (a que veio junto da ferramenta)"
    assert "Seu seguro cobre o para-brisa." in texto and "Me informa seu CPF" in texto, texto


@pytest.mark.parametrize("arquivo,chave,turno", APRESENTACOES_GRAVADAS[:3])
def test_pelo_motor_ja_apresentado_a_reapresentacao_gravada_sai(arquivo, chave, turno):
    """🔴 as falas GRAVADAS do 2º turno (Z C1/C4, U0 C1) num turno em que o prompt diz "NÃO se
    apresente": a apresentação sai, o atendimento fica."""
    fala = _fala_gravada(arquivo, chave, turno)
    mp = pytest.MonkeyPatch()
    try:
        texto = _turno([HumanMessage(content="to fora da pista"),
                        AIMessage(content="Você está em um local seguro?"),
                        HumanMessage(content="sim, nao vi fio caido")],
                       fala, dynamic="\n\n" + CALA, monkeypatch=mp)
    finally:
        mp.undo()
    assert not F.a_resposta_se_apresenta(texto, agent_name=NOME), texto
    resto = fala[F.trechos_de_apresentacao(fala, agent_name=NOME)[0][1]:].strip()
    assert texto.startswith(resto[:1].upper() + resto[1:20]), (texto[:80], resto[:80])
    assert len(texto) >= len(resto) - 1


def test_controle_apresentacao_pedida_e_unica_fica_intacta():
    """CONTROLE (o Sol C1 da U0): o 1º turno foi só `request_human_agent`, sem apresentação; o 2º a
    pede UMA vez — e a fala gravada que a faz sai INTEIRA."""
    fala = _fala_gravada(U0_OUTROS, "conv-c1-deducao-chuva", 2)
    mp = pytest.MonkeyPatch()
    try:
        texto = _turno([HumanMessage(content="sim, estou bem")], fala, dynamic="\n\n" + PEDE, monkeypatch=mp)
    finally:
        mp.undo()
    assert texto == fala


def test_controle_o_segurado_pergunta_quem_fala():
    mp = pytest.MonkeyPatch()
    try:
        texto = _turno([HumanMessage(content="quem está falando? é robô?")],
                       f"Aqui é a {NOME}, assistente virtual da {CORRETORA}. Posso seguir com o seu pedido?",
                       dynamic="\n\n" + CALA, monkeypatch=mp)
    finally:
        mp.undo()
    assert F.a_resposta_se_apresenta(texto, agent_name=NOME), texto


def test_so_a_apresentacao_nunca_vira_mensagem_vazia():
    so = f"Oi! Aqui é a {NOME}, da {CORRETORA}."
    assert N.sem_apresentacao_repetida(so, agent_name=NOME, ja_apresentado=True) == so


# =========================================================================== #
# 3 · o turno inteiro pela bancada N3: t1 sem apresentação → t2 a faz (forma do Sol) → t3 CALA
# =========================================================================== #
def test_pelo_grafo_a_apresentacao_do_sol_conta_e_o_terceiro_turno_nao_repete():
    """🔴 (vermelho antes) o fio do P-125-04 no caminho da U0 C1: t1 só `request_human_agent` (sem
    apresentação) → t2 se apresenta como o Sol ("Aqui é a <nome>, da <corretora>.") → o passo 9 a
    CONFIRMA → o prompt REAL do t3 diz "NÃO se apresente" — e a reapresentação do modelo não sai."""
    from test_spec125_endurecimento import CEN_C1, _call, _caso, _rodar

    from app.services.evals import dubles as D

    sol = f"Aqui é a {NOME}, da {CORRETORA}. "

    def roteiro(msgs, vistos):
        humanas = [D._texto_de(m.content) for m in msgs if D._tipo(m) == "human"]
        h = (humanas[-1] if humanas else "").lower()
        if D._tipo(msgs[-1]) == "tool":
            return "Nossa equipe de sinistro já recebeu o que você contou. Você está em um lugar seguro?", []
        if "poste" in h:
            return "", _call("request_human_agent", {"reason": "sinistro — colisão com poste, sem feridos"})
        if "fio" in h:
            return sol + "Que bom que você está em segurança. Em que rua aconteceu?", []
        return sol + "Anotei a rua. A equipe segue daqui.", []

    cen = {**CEN_C1, "chave": "conv-teste-u5-c1",
           "roteiro": {"falas_fixas": [CEN_C1["roteiro"]["falas_fixas"][0], ["to fora da pista, nao vi fio caido"],
                                       ["foi na rua sete"]], "max_turnos": 3}}
    r, vistos = _rodar(_caso(cen), roteiro)
    trans = r.rastro["estado"]["transcricao"]
    assert len(trans) == 3 and trans[0]["tools"] == ["request_human_agent"]
    assert not F.a_resposta_se_apresenta(trans[0]["agente"], agent_name=NOME), "t1 não se apresentou"
    assert "APRESENTAÇÃO: apresente-se agora" in vistos["sistemas"][-2], "t2 pede UMA vez (controle)"
    assert trans[1]["agente"].startswith(sol.strip()), trans[1]["agente"]
    assert CALA in vistos["sistemas"][-1], vistos["sistemas"][-1][-500:]
    assert not F.a_resposta_se_apresenta(trans[2]["agente"], agent_name=NOME), trans[2]["agente"]
    assert trans[2]["agente"].startswith("Anotei a rua."), trans[2]["agente"]
