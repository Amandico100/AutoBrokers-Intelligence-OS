"""Fila durável de Work Runs — Redis Streams + outbox. SPEC-055 §10.

Por que outbox e não publicar direto no Redis:

    INSERT no Postgres  →  crash  →  Redis nunca soube do trabalho
    publish no Redis    →  crash  →  trabalho executado sem registro

O outbox elimina os dois: a linha do run e a linha do outbox nascem na **mesma
transação** (RPC `work_run_create`). Um dispatcher separado lê o outbox e
publica. Se o publish falhar, a linha continua `pending` e é retentada. Redis
vira transporte, nunca fonte de verdade — que é a lei da SPEC-053 §2.5.

Consumer group garante que N workers dividam a carga sem processar o mesmo run
duas vezes, e que uma mensagem não confirmada volte para outro worker.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

STREAM_KEY = "autobrokers:work:stream"
CONSUMER_GROUP = "autobrokers-smith-worker"
MAX_STREAM_LEN = 50_000  # aparado aproximado; o Postgres é a verdade
CLAIM_MIN_IDLE_MS = 120_000  # 2 min sem ack → outro worker pode reivindicar


class WorkQueue:
    """Transporte. Toda decisão durável vive no Postgres."""

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    # -- setup --------------------------------------------------------------

    async def ensure_group(self) -> None:
        """Cria o consumer group se ainda não existir. Idempotente."""
        try:
            await self.redis.xgroup_create(STREAM_KEY, CONSUMER_GROUP, id="0", mkstream=True)
            logger.info("[WorkQueue] consumer group '%s' criado", CONSUMER_GROUP)
        except Exception as exc:  # noqa: BLE001
            if "BUSYGROUP" in str(exc):
                return  # já existe — caminho normal
            logger.error("[WorkQueue] falha ao criar consumer group: %s", type(exc).__name__)
            raise

    # -- publicação (usada pelo dispatcher do outbox) -----------------------

    async def publish(self, payload: dict) -> Optional[str]:
        """Publica e devolve o id da entrada. `None` em falha — o outbox retenta."""
        try:
            entry_id = await self.redis.xadd(
                STREAM_KEY,
                {"payload": json.dumps(payload, ensure_ascii=False, default=str)},
                maxlen=MAX_STREAM_LEN,
                approximate=True,
            )
            return entry_id.decode() if isinstance(entry_id, bytes) else str(entry_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("[WorkQueue] publish falhou: %s", type(exc).__name__)
            return None

    # -- consumo ------------------------------------------------------------

    async def consume(self, consumer_name: str, count: int = 1, block_ms: int = 5000) -> list[tuple[str, dict]]:
        """Lê mensagens novas do grupo. Retorna [(entry_id, payload)].

        Fila vazia é o estado NORMAL de um worker saudável. O `block` expira
        e o cliente Redis levanta `TimeoutError` — que não é falha, é ausência
        de trabalho. Registrar isso como erro produzia ruído contínuo no log e,
        pior, mascararia uma falha real de conexão no meio do barulho.
        """
        try:
            resposta = await self.redis.xreadgroup(
                CONSUMER_GROUP, consumer_name, {STREAM_KEY: ">"}, count=count, block=block_ms
            )
        except (asyncio.TimeoutError, TimeoutError):
            return []  # fila vazia — comportamento esperado
        except Exception as exc:  # noqa: BLE001
            # Alguns clientes envolvem o timeout de socket numa exceção própria.
            if type(exc).__name__ in ("TimeoutError", "ConnectionError") and "timeout" in str(exc).lower():
                return []
            logger.error("[WorkQueue] consume falhou: %s: %s", type(exc).__name__, exc)
            return []

        return self._parse(resposta)

    async def claim_abandonadas(self, consumer_name: str, count: int = 10) -> list[tuple[str, dict]]:
        """Reivindica mensagens que outro worker pegou e não confirmou.

        É o que evita trabalho preso quando um worker morre entre o consume e
        o ack. Sem isso, a mensagem ficaria eternamente na PEL daquele consumer.
        """
        try:
            resposta = await self.redis.xautoclaim(
                STREAM_KEY, CONSUMER_GROUP, consumer_name,
                min_idle_time=CLAIM_MIN_IDLE_MS, start_id="0-0", count=count,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[WorkQueue] xautoclaim indisponível: %s", type(exc).__name__)
            return []

        # xautoclaim devolve (próximo_cursor, mensagens, [ids_removidos])
        try:
            mensagens = resposta[1] if isinstance(resposta, (list, tuple)) and len(resposta) > 1 else []
            return self._parse_mensagens(mensagens)
        except Exception:  # noqa: BLE001
            return []

    async def ack(self, entry_id: str) -> None:
        try:
            await self.redis.xack(STREAM_KEY, CONSUMER_GROUP, entry_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[WorkQueue] ack falhou para %s: %s", entry_id, type(exc).__name__)

    async def profundidade(self) -> dict:
        """Métrica operacional: tamanho da fila e pendências não confirmadas."""
        try:
            tamanho = await self.redis.xlen(STREAM_KEY)
            try:
                pend = await self.redis.xpending(STREAM_KEY, CONSUMER_GROUP)
                pendentes = pend.get("pending", 0) if isinstance(pend, dict) else (pend[0] if pend else 0)
            except Exception:  # noqa: BLE001
                pendentes = 0
            return {"stream_len": tamanho, "pending": pendentes}
        except Exception as exc:  # noqa: BLE001
            return {"erro": type(exc).__name__}

    # -- parsing ------------------------------------------------------------

    def _parse(self, resposta: Any) -> list[tuple[str, dict]]:
        if not resposta:
            return []
        saida: list[tuple[str, dict]] = []
        for _stream, mensagens in resposta:
            saida.extend(self._parse_mensagens(mensagens))
        return saida

    def _parse_mensagens(self, mensagens: Any) -> list[tuple[str, dict]]:
        saida: list[tuple[str, dict]] = []
        for entry_id, campos in mensagens or []:
            eid = entry_id.decode() if isinstance(entry_id, bytes) else str(entry_id)
            bruto = campos.get(b"payload") or campos.get("payload")
            if isinstance(bruto, bytes):
                bruto = bruto.decode()
            try:
                saida.append((eid, json.loads(bruto)))
            except Exception:  # noqa: BLE001
                logger.warning("[WorkQueue] payload ilegível em %s — descartando entrada", eid)
        return saida


class OutboxDispatcher:
    """Move o outbox do Postgres para o Redis.

    Roda em laço curto. Falha de publish não perde trabalho: a linha continua
    `pending` com backoff. Depois de muitas tentativas vai para `abandoned` e
    o run é recuperado pelo varredor de órfãos, não pela fila.
    """

    MAX_TENTATIVAS = 10

    def __init__(self, supabase_client: Any, queue: WorkQueue):
        self.db = getattr(supabase_client, "client", supabase_client)
        self.queue = queue

    async def despachar_lote(self, limite: int = 50) -> int:
        from datetime import datetime, timedelta, timezone

        agora = datetime.now(timezone.utc)
        try:
            res = (
                self.db.table("work_queue_outbox")
                .select("*")
                .eq("status", "pending")
                .lte("next_attempt_at", agora.isoformat())
                .order("created_at")
                .limit(limite)
                .execute()
            )
            linhas = res.data or []
        except Exception as exc:  # noqa: BLE001
            logger.error("[Outbox] falha ao ler pendências: %s", type(exc).__name__)
            return 0

        publicadas = 0
        for linha in linhas:
            entry_id = await self.queue.publish({
                "outbox_id": linha["id"],
                "company_id": linha["company_id"],
                "work_run_id": linha["work_run_id"],
                "event_kind": linha["event_kind"],
                **(linha.get("payload_minimal") or {}),
            })

            if entry_id:
                self._atualizar(linha["id"], {
                    "status": "published",
                    "published_at": agora.isoformat(),
                    "redis_entry_id": entry_id,
                })
                publicadas += 1
            else:
                tentativas = int(linha.get("attempts") or 0) + 1
                if tentativas >= self.MAX_TENTATIVAS:
                    self._atualizar(linha["id"], {
                        "status": "abandoned",
                        "attempts": tentativas,
                        "last_error": "limite de tentativas de publicação atingido",
                    })
                    logger.error(
                        "[Outbox] run %s abandonado na fila após %d tentativas — "
                        "será recuperado pelo varredor de órfãos",
                        linha["work_run_id"], tentativas,
                    )
                else:
                    # backoff exponencial com teto de 5 minutos
                    espera = min(2 ** tentativas, 300)
                    self._atualizar(linha["id"], {
                        "attempts": tentativas,
                        "next_attempt_at": (agora + timedelta(seconds=espera)).isoformat(),
                        "last_error": "publish falhou",
                    })

        if publicadas:
            logger.info("[Outbox] %d trabalho(s) publicado(s) na fila", publicadas)
        return publicadas

    def _atualizar(self, outbox_id: str, campos: dict) -> None:
        from datetime import datetime, timezone

        campos["updated_at"] = datetime.now(timezone.utc).isoformat()
        try:
            self.db.table("work_queue_outbox").update(campos).eq("id", outbox_id).execute()
        except Exception as exc:  # noqa: BLE001
            logger.error("[Outbox] falha ao atualizar %s: %s", outbox_id, type(exc).__name__)
