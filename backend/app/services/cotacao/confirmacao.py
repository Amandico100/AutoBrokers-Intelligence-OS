# -*- coding: utf-8 -*-
"""O `confirmacao_id` — SPEC-132-B D-132B-03: confirmação EXPLÍCITA, de USO ÚNICO, que vale 30 min.

    guardar(company_id=, user_id=, conversation_id=, conteudo=) -> confirmacao_id
    consumir(company_id=, user_id=, conversation_id=, confirmacao_id=) -> conteudo   (ou ConfirmacaoRecusada)

ONDE MORA (decisão do builder B1, nota 85 · `work_runs` "aguardando" 60 · `messages.payload` 40): no REDIS, que o
CLAUDE.md §6 dá como a casa do TRANSITÓRIO (fila, lock, lease, cache) — e um "sim, pode calcular" de 30 minutos é
transitório por natureza: some sozinho (TTL), não precisa de tabela nova (§3 da SPEC) e não vira trabalho que o worker
pegaria (um `work_run` na fila RODA; um em estado próprio de "aguardando confirmação" não existe na máquina de estados).
Redis fora → a confirmação NÃO é guardada e o corretor ouve uma frase honesta (fail-closed: nada calcula sem o "sim").

🔴 USO ÚNICO: quem consome APAGA a chave e só segue se o `DEL` apagou (1). Duas chamadas ao mesmo tempo → só uma apaga.
   Depois de usada fica uma marca (`…:usada`, 30 min) para a segunda chamada ouvir "já foi" em vez de "expirou".
🔴 DONO: a chave tem o `company_id` (o id de A não existe em B) e o conteúdo tem quem preparou e em qual conversa —
   outra pessoa, ou a mesma noutra conversa, é recusada SEM consumir.
🔴 O conteúdo leva o PEDIDO (CPF, nome…): vai CIFRADO (`portal_vault`, o mesmo cofre do `pedido_cifrado` e do contato
   do canal). Nada disto vai a log.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import secrets
from typing import Any, Dict, Mapping, Optional

logger = logging.getLogger(__name__)

VALIDADE_S = 30 * 60
PREFIXO = "autobrokers:cotacao:confirmacao"
_ID = re.compile(r"^[0-9a-f]{16}$")

FRASES = {
    "inexistente": "Essa confirmação não vale mais (passou de 30 minutos ou não é desta conversa). Eu preparo de novo: "
                   "me diga \"prepara a cotação\" e confira o resumo.",
    "ja_usada": "Essa cotação já foi disparada — o resultado volta aqui nesta conversa. Para calcular de novo, peça "
                "uma cotação nova.",
    "de_outra_pessoa": "Essa confirmação é de outra conversa ou de outra pessoa da equipe — não posso usá-la aqui.",
    "sem_redis": "Não consegui guardar a confirmação agora (problema do nosso lado). Tente de novo em instantes.",
}


class ConfirmacaoRecusada(Exception):
    def __init__(self, motivo: str):
        self.motivo = motivo
        self.frase = FRASES.get(motivo, FRASES["inexistente"])
        super().__init__(motivo)


async def _redis_padrao() -> Any:
    from app.core.redis import get_async_redis_client

    return await asyncio.wait_for(get_async_redis_client(), timeout=2.0)


#: o provedor do cliente Redis (os testes trocam por um dublê em memória)
obter_redis = _redis_padrao


def _chave(company_id: str, confirmacao_id: str) -> str:
    return f"{PREFIXO}:{company_id}:{confirmacao_id}"


def _cifrar(conteudo: Mapping[str, Any]) -> str:
    from app.services import portal_vault

    return portal_vault.encrypt(json.dumps(dict(conteudo), ensure_ascii=False, sort_keys=True))


def _decifrar(token: str) -> Dict[str, Any]:
    from app.services import portal_vault

    return json.loads(portal_vault.decrypt(token))


async def guardar(*, company_id: str, user_id: str, conversation_id: str, conteudo: Mapping[str, Any],
                  redis: Any = None) -> str:
    """Guarda o pedido preparado e devolve o `confirmacao_id` (16 hex, imprevisível). Redis fora → `sem_redis`."""
    if not company_id or not user_id or not conversation_id:
        raise ConfirmacaoRecusada("de_outra_pessoa")
    cid = secrets.token_hex(8)
    corpo = {"company_id": str(company_id), "user_id": str(user_id), "conversation_id": str(conversation_id),
             "conteudo": dict(conteudo)}
    try:
        r = redis or await obter_redis()
        ok = await r.set(_chave(company_id, cid), _cifrar(corpo), ex=VALIDADE_S, nx=True)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[COTACAO] confirmação não guardada (%s)", type(exc).__name__)
        raise ConfirmacaoRecusada("sem_redis") from None
    if not ok:
        raise ConfirmacaoRecusada("sem_redis")
    return cid


async def consumir(*, company_id: str, user_id: str, conversation_id: str, confirmacao_id: Any,
                   redis: Any = None) -> Dict[str, Any]:
    """O conteúdo guardado — UMA vez. Recusas: `inexistente` · `ja_usada` · `de_outra_pessoa` · `sem_redis`."""
    cid = str(confirmacao_id or "").strip().lower()
    if not _ID.match(cid) or not company_id:
        raise ConfirmacaoRecusada("inexistente")
    chave = _chave(company_id, cid)
    try:
        r = redis or await obter_redis()
        bruto = await r.get(chave)
        if bruto is None:
            raise ConfirmacaoRecusada("ja_usada" if await r.get(chave + ":usada") else "inexistente")
        try:
            corpo = _decifrar(bruto)
        except Exception:  # noqa: BLE001 — chave trocada ou conteúdo estranho: não vale
            raise ConfirmacaoRecusada("inexistente") from None
        if (str(corpo.get("company_id")) != str(company_id) or str(corpo.get("user_id")) != str(user_id)
                or str(corpo.get("conversation_id")) != str(conversation_id)):
            raise ConfirmacaoRecusada("de_outra_pessoa")
        if int(await r.delete(chave) or 0) != 1:     # 🔴 só quem APAGOU segue (a outra chamada perdeu a corrida)
            raise ConfirmacaoRecusada("ja_usada")
        try:
            await r.set(chave + ":usada", "1", ex=VALIDADE_S)
        except Exception as exc:  # noqa: BLE001 — a marca é cortesia (a frase); o uso único já valeu pelo DEL
            logger.warning("[COTACAO] marca de 'já usada' não gravada (%s)", type(exc).__name__)
    except ConfirmacaoRecusada:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning("[COTACAO] confirmação ilegível (%s)", type(exc).__name__)
        raise ConfirmacaoRecusada("sem_redis") from None
    return dict(corpo.get("conteudo") or {})
