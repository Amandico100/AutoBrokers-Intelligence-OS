"""O que faz duas linhas serem a MESMA mensagem. SPEC-038/040.

Esta pergunta aparece em dois lugares muito diferentes — o Tecelão montando o
mapa da URA e o Destilador montando o transcript que vai para a LLM — e
precisa ter UMA resposta só. Duas implementações divergiriam com o tempo, e
uma delas voltaria a contar cópia como conversa.

Por que o módulo é separado
---------------------------
A função morava dentro do Tecelão. O Destilador passou a importá-la, e o
Tecelão carrega templater, cartógrafo e o resto do Atlas atrás. Em 28/07/2026
isso derrubou a destilação inteira com um `ModuleNotFoundError` — **todas** as
sessões falhando por causa de um import pesado para uma função de quinze
linhas.

Aqui não há dependência nenhuma. Só a regra.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def sem_copias(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Uma mensagem gravada três vezes é uma mensagem.

    Reimportações do histórico gravaram a mesma mensagem várias vezes (2,66x
    na Allianz, 1,99x no Espelho, medido em 28/07/2026). A causa foi corrigida
    em `history_ingest._history_message_id` e as cópias foram removidas do
    banco na migration 20260728_01 — mas o filtro fica, porque o custo de
    ler uma cópia é alto e o de checar é zero.

    A identidade é (sessão, direção, instante, tipo, texto). Duas mensagens
    iguais, no mesmo segundo, na mesma direção, dentro da mesma sessão, são a
    mesma mensagem — não um cliente que disse "Ok" duas vezes no mesmo segundo.

    Sem instante ou sem texto (foto, áudio, documento) não há identidade
    segura: **a mensagem FICA**. Perder é irreversível; sobrar não.

    Nada é apagado: isto é leitura.
    """
    vistos: set = set()
    saida: List[Dict[str, Any]] = []
    for e in events:
        instante, texto = e.get("wa_timestamp"), e.get("text")
        if not instante or not texto:
            saida.append(e)
            continue
        chave = (e.get("session_id"), e.get("direction"), instante,
                 e.get("msg_type"), texto)
        if chave in vistos:
            continue
        vistos.add(chave)
        saida.append(e)
    if len(saida) != len(events):
        logger.info("atlas: %d eventos lidos, %d únicos (%d cópias ignoradas)",
                    len(events), len(saida), len(events) - len(saida))
    return saida
