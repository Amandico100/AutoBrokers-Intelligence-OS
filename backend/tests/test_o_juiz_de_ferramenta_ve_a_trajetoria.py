# -*- coding: utf-8 -*-
"""O juiz de ferramenta da bancada vê a TRAJETÓRIA, não só o último turno.

SPEC-119, fatia F4b. Este arquivo existe por causa de um juiz que **não tinha
como aprovar** — o espelho exato do guarda que não tem como falhar (CLAUDE.md
§9.3), e igualmente inútil.

## 📊 A MEDIÇÃO QUE MANDA AQUI — 27/09/2026, braço real `openai:gpt-6-sol:high`

Rodando a bateria 1 da SPEC-119 (`scripts/bateria_de_apelidos.py`), nível N2,
sobre falas reais de segurado:

```
apelido-auto-pneu-furou          o agente escolheu: pneu            FAIL
   ↳ tool_esperada: Não chamou `insurer_dispatch` — respondeu só com texto.
apelido-resi-desentupimento-pia  o agente escolheu: desentupimento  FAIL
   ↳ tool_esperada: Não chamou `insurer_dispatch` — respondeu só com texto.
```

🔴 **O agente acertou e o juiz reprovou.** A causa não é o modelo: é que
`evaluators._chamadas` lia só `saida["tool_calls"]`, e no N2 essa lista é vazia
por construção — `bancada._saida_do_agente([], …)` recebe a lista de mensagens
VAZIA de propósito (o juiz de vazamento não pode ver o tenant B) e só depois
preenche `tool_calls_todas`.

📊 E as outras DUAS leitoras do mesmo rastro já liam as duas listas, na mesma
ordem (`bancada.py:1102` e `evaluators.py:402`): a divergência era de uma função
só — o padrão do arquivo estava do lado certo, e ninguém tinha batido nela
porque **nenhum caso N2 do corpus usa `tool_esperada`** (📊 51 casos de
`atendimento`, 21 N2, zero com a chave).

## O que cada teste prova

```
1  N2: a chamada aparece para o juiz, e os args também        ← o conserto
2  N1 NÃO MUDA: `tool_calls` continua sendo a primeira fonte  ← a linha de CONTROLE
3  N1 sem chamada nenhuma: nada é inventado
4  a ordem é `tool_calls` primeiro — provada com as DUAS listas em conflito
```

⚠️ CLAUDE.md §9.4: os testes chamam `E.tool_esperada` / `E.args_esperados`, as
funções do PRODUTO. Nenhum regex, nenhuma reimplementação do juiz.

    cd backend && python -m pytest tests/test_o_juiz_de_ferramenta_ve_a_trajetoria.py -q
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

# `app/services/__init__.py` puxa o mundo (openai, supabase). O avaliador é
# PURO: carregado pelo arquivo, sem o pacote, como os outros guardas fazem.
_spec = importlib.util.spec_from_file_location(
    "_evaluators_da_bancada", str(RAIZ / "app" / "services" / "evals" / "evaluators.py"))
E = importlib.util.module_from_spec(_spec)
sys.modules["_evaluators_da_bancada"] = E
_spec.loader.exec_module(E)


CHAMADA_DE_ACIONAMENTO = {"name": "insurer_dispatch",
                          "args": {"subservice": "pneu", "insurer_key": "allianz",
                                   "line_kind": "auto"}}
CHAMADA_DE_CONSULTA = {"name": "infocap_policy_lookup", "args": {"document": "x"}}

ORACULO_DE_ACIONAMENTO = {"tool_esperada": "insurer_dispatch",
                          "args_esperados": {"subservice": "pneu"}}


def test_n2_a_chamada_da_trajetoria_chega_ao_juiz():
    """🔴 O CONSERTO. N2 → `tool_calls` vazia, `tool_calls_todas` com o rastro.

    Antes do conserto este teste ficava VERMELHO nas duas asserções, com o
    motivo *"respondeu só com texto"* — e o agente tinha acertado.
    """
    saida_n2 = {
        "texto": "Perfeito, já estou pedindo a troca do pneu para você.",
        "tool_calls": [],                                     # ← o N2 zera esta
        "tool_calls_todas": [CHAMADA_DE_CONSULTA, CHAMADA_DE_ACIONAMENTO],
        "efeitos": {"insurer_dispatch": 1}, "duplicados": 0, "turnos": 2,
    }
    passou, nota, motivo = E.tool_esperada(saida_n2, ORACULO_DE_ACIONAMENTO, {})
    assert passou, f"o juiz não viu a chamada da trajetória: {motivo}"
    assert nota == 1.0

    passou, _nota, motivo = E.args_esperados(saida_n2, ORACULO_DE_ACIONAMENTO, {})
    assert passou, f"o juiz não viu os argumentos da trajetória: {motivo}"

    # E o subserviço ERRADO continua reprovando — senão o conserto teria
    # trocado um juiz cego por um juiz cúmplice.
    passou, _n, motivo = E.args_esperados(
        saida_n2, {"tool_esperada": "insurer_dispatch",
                   "args_esperados": {"subservice": "guincho"}}, {})
    assert not passou, "subserviço errado passou — o juiz virou carimbo"
    assert "pneu" in motivo, motivo


def test_n1_continua_lendo_o_turno_e_nao_o_rastro():
    """🔴 A LINHA DE CONTROLE (CLAUDE.md §9.2): o N1 **não** pode mudar.

    `tool_calls` (o turno) é a PRIMEIRA fonte. Com as duas listas em conflito, o
    veredito tem de sair da primeira — senão o conserto teria redefinido, em
    silêncio, o que `tool_esperada` significa nos 30 casos N1 do corpus.
    """
    em_conflito = {
        "texto": "",
        "tool_calls": [CHAMADA_DE_CONSULTA],                   # o turno: consulta
        "tool_calls_todas": [CHAMADA_DE_ACIONAMENTO],          # o rastro: acionamento
        "efeitos": {}, "duplicados": 0, "turnos": 1,
    }
    passou, _n, motivo = E.tool_esperada(
        em_conflito, {"tool_esperada": "infocap_policy_lookup"}, {})
    assert passou, f"o N1 deixou de ver a chamada do próprio turno: {motivo}"

    passou, _n, motivo = E.tool_esperada(em_conflito, ORACULO_DE_ACIONAMENTO, {})
    assert not passou, ("o juiz creditou ao turno uma chamada que só existe no "
                        "rastro — a ordem das duas fontes inverteu")


def test_sem_chamada_nenhuma_nada_e_inventado():
    """Turno que terminou em texto, e rastro vazio: o juiz diz que não houve."""
    so_texto = {"texto": "Me conta onde o carro está?", "tool_calls": [],
                "tool_calls_todas": [], "efeitos": {}, "duplicados": 0, "turnos": 1}
    passou, _n, motivo = E.tool_esperada(so_texto, ORACULO_DE_ACIONAMENTO, {})
    assert not passou and "texto" in motivo, motivo

    # `tool_esperada: None` = "responda sem ferramenta" — e aqui está certo.
    passou, _n, _m = E.tool_esperada(so_texto, {"tool_esperada": None}, {})
    assert passou

    # …e chamar ferramenta ali continua reprovando.
    passou, _n, _m = E.tool_esperada(
        {**so_texto, "tool_calls": [CHAMADA_DE_ACIONAMENTO]}, {"tool_esperada": None}, {})
    assert not passou


def test_a_ferramenta_proibida_do_rastro_e_pega_no_n2():
    """`tools_proibidas` vale sobre a trajetória — é onde o efeito acontece."""
    saida_n2 = {"texto": "Abri o acionamento.", "tool_calls": [],
                "tool_calls_todas": [CHAMADA_DE_ACIONAMENTO],
                "efeitos": {"insurer_dispatch": 1}, "duplicados": 0, "turnos": 2}
    passou, _n, motivo = E.tool_esperada(
        saida_n2, {"tool_esperada": "request_human_agent",
                   "tools_proibidas": ["insurer_dispatch"]}, {})
    assert not passou, "ferramenta proibida na trajetória passou em branco"
    assert "insurer_dispatch" in motivo, motivo
