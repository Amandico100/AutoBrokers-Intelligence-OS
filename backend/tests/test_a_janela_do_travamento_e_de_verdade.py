# -*- coding: utf-8 -*-
"""🔴 O `dias` da régua tem de FILTRAR, e não só existir na assinatura.

📊 Achado em 26/08/2026 por auditoria externa da SPEC-089:

    travamentos_por_rota(dias: int = 30)

O parâmetro estava declarado, documentado, e **não aparecia uma única vez no
corpo da função**. Nenhuma das três consultas tinha filtro de data.

## ⚠️ Por que era silencioso — e essa é a gravidade

📊 Os dois `work_steps needs_human` do banco são de 18/08 — dentro de qualquer
janela. **A nota de hoje sai igual com ou sem o conserto**, então nenhum teste
de valor pegaria isto.

🔴 **O que mudava era o futuro:** a janela real era o **histórico inteiro**, e
por isso uma rota que travasse na primeira semana do piloto **nunca mais
recuperaria os 6 pontos do eixo F**, por melhor que passasse a se comportar. O
eixo era monotônico e só piorava.

E isso torna impossível a recomendação de **reler o eixo F depois da primeira
semana**: não haveria o que reler, porque nada sairia da janela.

## É a §12.1 aplicada à régua

> *"Se o nome de um campo mente sobre o que ele guarda, conserte o campo — não
> só o texto."*

O nome dizia "últimos N dias". O corpo dizia "sempre". **O texto errado era o
sintoma; o parâmetro morto era a causa.**

## O que este arquivo guarda

Três coisas, e a terceira é a que faltava:

  1. `_corte_de_dias` calcula a data certa
  2. `dias` menor sempre dá corte MAIS RECENTE que `dias` maior
  3. 🔴 **a consulta USA o corte** — sem isto, 1 e 2 passam com o parâmetro
     de volta ao limbo
"""
from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timedelta, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

import regua_motor as RM  # noqa: E402

FONTE = os.path.join(RAIZ, "scripts", "regua_motor.py")


def _corpo_da_funcao() -> str:
    """O corpo de `travamentos_por_rota`, SEM comentários nem docstring.

    🔴 O cortador existe porque a prosa desta função CITA o defeito — ela
    explica que o `dias` era ignorado. Um guarda que lesse o texto acharia a
    palavra `dias` no comentário e passaria com o código de volta ao errado.
    ⚠️ É a doença que derrubou oito guardas em 26/08: **a asserção lia a
    prosa que explica por que o código deveria existir.**
    """
    fonte = open(FONTE, encoding="utf-8").read()
    inicio = fonte.index("def travamentos_por_rota(")
    resto = fonte[inicio:]
    # a próxima definição de nível zero encerra o corpo
    fim = re.search(r"\n(?:def |class )", resto[1:])
    corpo = resto[: fim.start() + 1] if fim else resto
    corpo = re.sub(r'"""[\s\S]*?"""', "", corpo)      # docstrings
    corpo = re.sub(r"#[^\n]*", "", corpo)              # comentários
    return corpo


def test_o_corte_e_a_data_certa():
    corte = RM._corte_de_dias(30)
    quando = datetime.fromisoformat(corte)
    esperado = datetime.now(timezone.utc) - timedelta(days=30)
    assert abs((quando - esperado).total_seconds()) < 120, (
        f"`_corte_de_dias(30)` devolveu {corte}, que não é 30 dias atrás."
    )


def test_janela_menor_da_corte_mais_recente():
    """Uma janela de 1 dia tem de cortar DEPOIS de uma de 90."""
    assert RM._corte_de_dias(1) > RM._corte_de_dias(90)


def test_zero_vira_UM_dia_e_nao_o_historico_inteiro():
    """⚠️ Quem passa 0 quase sempre quer "hoje".

    🔴 Devolver o histórico inteiro por causa de um zero é **exatamente o
    defeito que este conserto mata**, entrando pela porta dos fundos.
    """
    # ⚠️ Compara o DIA, não o instante: `_corte_de_dias` chama `now()`, e duas
    # chamadas seguidas diferem em microssegundos. A primeira versão deste
    # teste comparava igualdade exata e reprovava o código CERTO — um guarda
    # que acusa o inocente é pior que guarda nenhum.
    assert RM._corte_de_dias(0)[:10] == RM._corte_de_dias(1)[:10]
    assert RM._corte_de_dias(-5)[:10] == RM._corte_de_dias(1)[:10]


def test_lixo_no_parametro_nao_derruba_a_regua():
    """⛔ A régua não pode quebrar por causa do tipo do argumento."""
    assert RM._corte_de_dias("trinta")[:10] == RM._corte_de_dias(30)[:10]  # type: ignore[arg-type]
    assert RM._corte_de_dias(None)[:10] == RM._corte_de_dias(30)[:10]      # type: ignore[arg-type]


def test_A_CONSULTA_USA_O_CORTE():
    """🔴 O teste que faltava — e sem ele os de cima passam por vacuidade.

    ⚠️ `_corte_de_dias` pode estar perfeito e não ser chamado por ninguém. Foi
    literalmente o que aconteceu com o `dias`: declarado, documentado, morto.
    """
    corpo = _corpo_da_funcao()
    assert "_corte_de_dias(dias)" in corpo, (
        "🔴 `travamentos_por_rota` não chama `_corte_de_dias(dias)`. O "
        "parâmetro voltou a ser decoração."
    )
    assert 'gte("created_at"' in corpo or "gte('created_at'" in corpo, (
        "🔴 a consulta não filtra por `created_at`. A janela voltou a ser o "
        "histórico inteiro, e uma rota que travar hoje nunca mais se recupera."
    )


def test_CONTROLE_o_cortador_de_prosa_realmente_corta():
    """⚠️ A LINHA DE CONTROLE do cortador.

    🔴 Se ele não cortasse, o teste acima acharia `_corte_de_dias(dias)` no
    comentário que EXPLICA o conserto — e passaria com o código desfeito.
    """
    fonte = open(FONTE, encoding="utf-8").read()
    inicio = fonte.index("def travamentos_por_rota(")
    bruto = fonte[inicio:inicio + 4000]
    corpo = _corpo_da_funcao()

    assert len(corpo) < len(bruto), "o cortador não tirou nada"
    assert "ERA DECLARADO E NUNCA USADO" in bruto, (
        "a frase-isca sumiu do fonte; troque a isca deste controle"
    )
    assert "ERA DECLARADO E NUNCA USADO" not in corpo, (
        "🔴 o cortador NÃO corta comentário — e então o teste de cima lê a "
        "prosa em vez do código (CLAUDE.md §9.3)"
    )
    # e não corta demais: a linha de código real sobrevive
    assert "_corte_de_dias(dias)" in corpo, (
        "🔴 o cortador comeu código junto com a prosa"
    )
