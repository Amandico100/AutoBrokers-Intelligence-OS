"""SPEC-044 — Contexto da requisição (ContextVar async-safe).

O grafo do agente é CACHEADO por (company, agent) e compartilhado entre os
usuários da corretora — por isso NADA de identidade de usuário pode ser
"assado" na construção do grafo/LLM/tools (atribuiria custo e conhecimento
pessoal ao usuário errado). A identidade viaja POR REQUISIÇÃO:

- via state do grafo (tool_node injeta em cada execução de tool), e
- via este ContextVar (o CostCallbackHandler lê no momento do tracking).

ContextVar é seguro em asyncio: cada task de request enxerga só o próprio
valor. Setado no início do processamento do chat; nunca vaza entre requests.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Optional

_current_user_id: ContextVar[Optional[str]] = ContextVar("ab_current_user_id", default=None)


def set_current_user_id(user_id: Optional[str]) -> None:
    _current_user_id.set(str(user_id) if user_id else None)


def get_current_user_id() -> Optional[str]:
    try:
        return _current_user_id.get()
    except LookupError:
        return None
