"""Ler o acervo inteiro quando o número precisa estar certo.

POR QUE MORA EM `app/`, E NÃO EM `app/core/`
============================================
`app/core/__init__.py` importa `config` e `database` — a cadeia inteira de
configuração do backend. Este módulo não precisa de nada disso: são vinte linhas
de laço, sem I/O próprio e sem estado.

Guardá-lo lá dentro obrigaria todo mundo que o usasse a arrastar a configuração
junto — inclusive o worker de cobrança, que existe justamente para NÃO depender
dela (`billing_core.py` foi separado pelo mesmo motivo), e os testes que
carregam um módulo isolado para exercitá-lo sem subir o mundo.

📊 Foi medido, e não suposto: com o import em `app.core`, quatro testes que
passavam viraram `ModuleNotFoundError: pydantic_settings`. Uma peça de
infraestrutura que só funciona com o mundo inteiro de pé não é infraestrutura.

O PROBLEMA QUE ESTA PEÇA RESOLVE
================================
O PostgREST devolve no máximo **1.000 linhas por resposta** e o `.limit(N)` que
se pede acima disso é simplesmente ignorado. Não há erro, não há aviso, não há
log: o código recebe 1.000 linhas e não tem como distinguir "só existem 1.000"
de "existem 5.000 e você recebeu um quinto".

📊 06/08/2026, medido no projeto de produção `dcajcvlzcjbmyapmklil`:

    o que a leitura enfrenta                    linhas    o que chegava
    ────────────────────────────────────────────────────────────────────
    token_usage_logs 30 d (Resulta)              4.648            1.000
    usage_events 30 d (todas as corretoras)      4.406            1.000
    token_usage_logs por cobrar                  5.646            1.000
    attendance_sessions 30 d                     1.577            1.000

Onde o resultado é uma LISTA de tela, isso não dói — ninguém rola mil linhas.
Onde o resultado é uma SOMA, corrompe a resposta em silêncio: 📊 o custo de 30
dias da Resulta (US$ 9,55) chegava à tela do cliente como uma fração disso, e o
relatório de custo unitário declarava ativamente que tinha lido tudo.

POR QUE PAGINAR, E NÃO SOMAR NO BANCO
=====================================
Somar dentro do Postgres é tecnicamente melhor: uma ida, resposta exata, sem
memória. Mas exige função SQL nova, e função SQL nova é migration — que é
justamente onde nascem os bugs que atrasam tudo.

📊 O custo real de paginar aqui é pequeno: 4.648 linhas são 5 idas ao banco,
num relatório que roda sob demanda. A escolha é deliberada e o registro fica:
**segurança de execução ganhou de elegância**, porque o preço da elegância
seria SQL novo em produção no meio de um lançamento.

Se um dia alguma dessas leituras passar de ~20 mil linhas, a conta se inverte e
aí vale a função SQL. O teto abaixo avisa quando esse dia chegar — em vez de
truncar calado, que é o defeito que esta peça existe para matar.

A ARMADILHA QUE JÁ CUSTOU CARO NESTE REPOSITÓRIO
================================================
📊 `curadoria_cartas.py` documenta um caso medido: uma paginação ordenada por
`created_at` perdeu 12 linhas e repetiu outras 12 em 11.640. Datas EMPATAM, e
duas linhas empatadas podem trocar de posição entre uma página e a próxima —
uma aparece duas vezes, a outra nunca aparece.

Por isso `chave_unica` é **obrigatória** e não tem valor padrão adivinhado: quem
chama precisa dizer qual coluna nunca empata. É a diferença entre paginar e
parecer que paginou.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, List, Tuple

logger = logging.getLogger(__name__)

# Quantas linhas o servidor entrega por resposta. Não é escolha nossa: é o teto
# do PostgREST, e pedir mais não muda nada. Páginas do tamanho exato do teto
# tornam "página curta = acabou" verdadeiro.
TAMANHO_DA_PAGINA = 1000

# Teto de segurança da leitura inteira. Existe para uma leitura distraída sobre
# uma tabela enorme não puxar a tabela para dentro do processo — 📊
# `attendance_transcripts` tem 135 mil linhas e 96 MB; paginá-la sem filtro
# derrubaria o contêiner, e o sintoma pareceria outra coisa (CLAUDE.md §9.1).
#
# Quando ele morde, quem chama FICA SABENDO (segundo item da tupla). Esse é o
# ponto inteiro desta peça: um teto que avisa não é o mesmo defeito de novo.
TETO_DE_SEGURANCA = 50_000


def ler_paginado(
    montar_consulta: Callable[[], Any],
    *,
    chave_unica: str,
    teto: int = TETO_DE_SEGURANCA,
    rotulo: str = "",
) -> Tuple[List[dict], bool]:
    """Lê TODAS as linhas da consulta. Devolve ``(linhas, truncou)``.

    ``montar_consulta`` é chamada uma vez por página e deve devolver a consulta
    JÁ filtrada (``.table(...).select(...).eq(...)``), **sem** `order`, `limit`
    ou `range` — a paginação é aplicada aqui. Ela é uma função, e não uma
    consulta pronta, porque o cliente do Supabase acumula estado: reaproveitar
    o mesmo objeto empilharia `range` sobre `range`.

    ``chave_unica`` é obrigatória e deve ser uma coluna que NUNCA empata
    (normalmente ``id``). Ver a nota sobre as 12 cartas no topo do módulo.

    ``truncou`` é ``True`` quando a leitura parou no teto de segurança — ou
    seja, quando ainda havia linhas. Quem mostra número para gente PRECISA
    olhar esse valor: era exatamente ele que faltava.
    """
    linhas: List[dict] = []
    while True:
        inicio = len(linhas)
        try:
            lote = (montar_consulta()
                    .order(chave_unica, desc=False)
                    .range(inicio, inicio + TAMANHO_DA_PAGINA - 1)
                    .execute().data) or []
        except Exception as erro:  # noqa: BLE001
            # Uma página que falha no meio não pode virar "li tudo": o que já
            # veio é devolvido COM o aviso de incompleto, e quem chama decide.
            logger.warning("[LEITURA] %s: página a partir de %s falhou (%s)",
                           rotulo or "consulta", inicio, type(erro).__name__)
            return linhas, True

        linhas.extend(lote)
        # Página curta = acabou. É a única forma de "acabou" que não depende de
        # adivinhar o teto do servidor.
        if len(lote) < TAMANHO_DA_PAGINA:
            return linhas, False
        if len(linhas) >= teto:
            logger.warning(
                "[LEITURA] %s parou no teto de %s linhas — o resultado está "
                "INCOMPLETO e quem chamou foi avisado",
                rotulo or "consulta", teto)
            return linhas, True


async def ler_paginado_async(
    montar_consulta: Callable[[], Any],
    *,
    chave_unica: str,
    teto: int = TETO_DE_SEGURANCA,
    rotulo: str = "",
) -> Tuple[List[dict], bool]:
    """Igual a :func:`ler_paginado`, para o cliente assíncrono.

    Duplicar as dez linhas do laço é mais honesto do que embrulhar o cliente
    síncrono em ``asyncio.to_thread``: as rotas assíncronas usam um cliente
    diferente, e fingir que são o mesmo esconderia justamente o tipo de engano
    que este módulo existe para acabar.
    """
    linhas: List[dict] = []
    while True:
        inicio = len(linhas)
        try:
            resposta = await (montar_consulta()
                              .order(chave_unica, desc=False)
                              .range(inicio, inicio + TAMANHO_DA_PAGINA - 1)
                              .execute())
            lote = resposta.data or []
        except Exception as erro:  # noqa: BLE001
            logger.warning("[LEITURA] %s: página a partir de %s falhou (%s)",
                           rotulo or "consulta", inicio, type(erro).__name__)
            return linhas, True

        linhas.extend(lote)
        if len(lote) < TAMANHO_DA_PAGINA:
            return linhas, False
        if len(linhas) >= teto:
            logger.warning(
                "[LEITURA] %s parou no teto de %s linhas — o resultado está "
                "INCOMPLETO e quem chamou foi avisado",
                rotulo or "consulta", teto)
            return linhas, True


__all__ = ["ler_paginado", "ler_paginado_async",
           "TAMANHO_DA_PAGINA", "TETO_DE_SEGURANCA"]
