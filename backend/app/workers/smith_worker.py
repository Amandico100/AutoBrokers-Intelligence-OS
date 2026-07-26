"""Smith Worker — execução durável de Work Runs. SPEC-055 §11.

**Não é outro cérebro.** Usa o mesmo Smith, o mesmo grafo, o mesmo Context
Assembly. A diferença é onde roda e quanto tempo pode durar.

O que ele substitui: hoje o scheduler de rotinas roda com
`asyncio.create_task` dentro do processo do FastAPI (`main.py:83`). Isso
significa que um deploy no meio de uma rotina mata a rotina, e que uma tarefa
longa compete com requisições web pelo mesmo event loop.

Ciclo:

    outbox → Redis Stream → consume → lease → executar → heartbeat
           → concluir/falhar → ack → liberar lease

Laços paralelos:
  · dispatcher do outbox
  · varredor de órfãos (lease vencida)
  · expiração de aprovações
  · reconciliação de efeitos sem confirmação

Executar como serviço separado:

    python -m app.workers.smith_worker
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
from typing import Any, Optional

logger = logging.getLogger(__name__)

INTERVALO_DISPATCHER_S = float(os.getenv("WORK_OUTBOX_INTERVAL_S", "2"))
INTERVALO_ORFAOS_S = float(os.getenv("WORK_ORPHAN_SCAN_INTERVAL_S", "60"))
INTERVALO_MANUTENCAO_S = float(os.getenv("WORK_MAINTENANCE_INTERVAL_S", "300"))
CONCORRENCIA = int(os.getenv("WORK_WORKER_CONCURRENCY", "3"))
CONCORRENCIA_POR_TENANT = int(os.getenv("WORK_TENANT_CONCURRENCY", "2"))


class SmithWorker:
    """Consome a fila e executa Work Runs com lease e heartbeat."""

    def __init__(self) -> None:
        self.parar = asyncio.Event()
        self.worker_id: str = ""
        self.db: Any = None
        self.redis: Any = None
        self.queue: Any = None
        self.dispatcher: Any = None
        self.runs: Any = None
        self.approvals: Any = None
        self.effects: Any = None
        self._em_execucao: dict[str, asyncio.Task] = {}
        self._por_tenant: dict[str, int] = {}

    # ------------------------------------------------------------------

    async def iniciar(self) -> None:
        from app.core.database import get_supabase_client
        from app.core.redis import get_async_redis_client
        from app.services.work.approvals import WorkApprovalService
        from app.services.work.effects import WorkEffectService
        from app.services.work.queue import OutboxDispatcher, WorkQueue
        from app.services.work.runs import WorkRunService, worker_id

        self.worker_id = worker_id()
        self.db = get_supabase_client()
        self.redis = await get_async_redis_client()

        self.queue = WorkQueue(self.redis)
        await self.queue.ensure_group()

        self.dispatcher = OutboxDispatcher(self.db, self.queue)
        self.runs = WorkRunService(self.db)
        self.approvals = WorkApprovalService(self.db)
        self.effects = WorkEffectService(self.db)

        logger.info("[SmithWorker] iniciado id=%s concorrencia=%d", self.worker_id, CONCORRENCIA)

        # Painel de subsistemas: o worker roda sozinho num container proprio, e
        # sem isto a unica forma de saber se ele tem o que precisa e esperar
        # nada acontecer e adivinhar por que.
        try:
            import os as _os

            from app.services.knowledge.insurance_corpus import InsuranceCorpusService
            from app.services.research.firecrawl import configurado as _fc

            _pend = len(InsuranceCorpusService(self.db).vencidos(limite=50))
            logger.info(
                "[SmithWorker] firecrawl=%s | corpus normativo: %d documento(s) "
                "aprovado(s) aguardando | manutencao a cada %ss",
                "configurado" if _fc() else "SEM CHAVE NESTE SERVICO",
                _pend, INTERVALO_MANUTENCAO_S)
        except Exception as _e:  # noqa: BLE001
            logger.warning("[SmithWorker] painel indisponivel: %s", type(_e).__name__)

    async def executar(self) -> None:
        await self.iniciar()
        tarefas = [
            asyncio.create_task(self._laco_dispatcher(), name="outbox"),
            asyncio.create_task(self._laco_consumo(), name="consumo"),
            asyncio.create_task(self._laco_orfaos(), name="orfaos"),
            asyncio.create_task(self._laco_manutencao(), name="manutencao"),
        ]
        try:
            await self.parar.wait()
        finally:
            logger.info("[SmithWorker] encerrando — aguardando runs em voo")
            for t in tarefas:
                t.cancel()
            if self._em_execucao:
                await asyncio.gather(*self._em_execucao.values(), return_exceptions=True)
            logger.info("[SmithWorker] encerrado")

    # ------------------------------------------------------------------
    # Laços
    # ------------------------------------------------------------------

    async def _laco_dispatcher(self) -> None:
        while not self.parar.is_set():
            try:
                await self.dispatcher.despachar_lote()
            except Exception as exc:  # noqa: BLE001
                logger.error("[SmithWorker] dispatcher: %s", type(exc).__name__)
            await self._dormir(INTERVALO_DISPATCHER_S)

    async def _laco_consumo(self) -> None:
        while not self.parar.is_set():
            try:
                if len(self._em_execucao) >= CONCORRENCIA:
                    await self._dormir(1)
                    continue

                mensagens = await self.queue.consume(self.worker_id, count=1, block_ms=5000)
                if not mensagens:
                    # sem trabalho novo: tenta recuperar mensagem abandonada
                    mensagens = await self.queue.claim_abandonadas(self.worker_id, count=1)
                for entry_id, payload in mensagens:
                    await self._agendar(entry_id, payload)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.error("[SmithWorker] consumo: %s", type(exc).__name__)
                await self._dormir(2)

    async def _laco_orfaos(self) -> None:
        while not self.parar.is_set():
            await self._dormir(INTERVALO_ORFAOS_S)
            try:
                orfaos = self.runs.recuperar_orfaos()
                if orfaos:
                    logger.warning("[SmithWorker] %d run(s) órfão(s) recuperado(s)", len(orfaos))
            except Exception as exc:  # noqa: BLE001
                logger.error("[SmithWorker] varredura de órfãos: %s", type(exc).__name__)

    async def _laco_manutencao(self) -> None:
        while not self.parar.is_set():
            await self._dormir(INTERVALO_MANUTENCAO_S)
            try:
                self.approvals.expirar_vencidas()
                pendentes = self.effects.pendentes_de_reconciliacao()
                if pendentes:
                    # Não repetimos automaticamente: efeito sem confirmação
                    # exige decisão. Repetir por conta própria é justamente o
                    # que produz cobrança e envio duplicados.
                    logger.warning(
                        "[SmithWorker] %d efeito(s) aguardando reconciliação — nenhum repetido automaticamente",
                        len(pendentes),
                    )
                # SPEC-057 H — reconferencia do corpus normativo. Entra no laco
                # que JA existe: criar um agendador proprio para isto seria o
                # motor paralelo que o CLAUDE.md 5 proibe.
                await self._reconferir_corpus()

                # SPEC-059 — o Intelligence Fabric usa o MESMO laco. Ele so
                # ENFILEIRA Work Runs; quem executa continua sendo o ciclo de
                # consumo deste worker, com lease e retomada.
                await self._tick_de_inteligencia()

                # SPEC-052 Lote 4 — fechar sessoes paradas e produzir memoria.
                # O gatilho nao pode viver dentro do turno: ninguem sabe, no
                # meio da conversa, que ela acabou. Quem sabe e o relogio.
                await self._varrer_memoria()
            except Exception as exc:  # noqa: BLE001
                logger.error("[SmithWorker] manutenção: %s", type(exc).__name__)

    async def _tick_de_inteligencia(self) -> None:
        try:
            from app.services.intelligence.tick import rodar

            r = await asyncio.to_thread(rodar, self.db)
            if any(v for k, v in r.items() if isinstance(v, int) and v):
                logger.info("[SmithWorker] inteligência: %s", r)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[SmithWorker] tick de inteligência: %s", type(exc).__name__)

    async def _varrer_memoria(self) -> None:
        try:
            from app.services.memory_fabric import fechar_sessoes

            r = await fechar_sessoes(self.db, limite=10)
            if r.get("resumidas"):
                logger.info("[SmithWorker] memória: %s sessão(ões) resumida(s) "
                            "de %s avaliada(s)", r["resumidas"], r["avaliadas"])
        except Exception as exc:  # noqa: BLE001
            logger.warning("[SmithWorker] varredura de memória: %s", type(exc).__name__)

    async def _reconferir_corpus(self) -> None:
        """Passa nos documentos normativos vencidos, poucos por ciclo.

        Trabalho de fundo nao pode competir com o trabalho que o corretor esta
        esperando — por isso o limite e baixo e a falha e silenciosa aqui.
        """
        try:
            from app.services.knowledge.insurance_corpus import InsuranceCorpusService
            from app.services.research.firecrawl import configurado

            if not configurado():
                # Pular em SILENCIO aqui era indistinguivel de "nao havia nada a
                # fazer". O corpus ficaria parado para sempre e o log nao diria
                # por que. Avisa uma vez por processo — repetir a cada ciclo
                # viraria ruido que se aprende a ignorar.
                if not getattr(self, "_avisou_sem_firecrawl", False):
                    self._avisou_sem_firecrawl = True
                    pendentes = InsuranceCorpusService(self.db).vencidos(limite=1)
                    logger.warning(
                        "[SmithWorker] corpus normativo PARADO: FIRECRAWL_API_KEY nao "
                        "configurada NESTE servico%s. A chave precisa estar tambem no "
                        "worker, nao so na API.",
                        f" — ha documento(s) aprovado(s) aguardando" if pendentes else "")
                return
            r = await InsuranceCorpusService(self.db).reconferir_pendentes(limite=3)
            if r.get("mudaram"):
                logger.warning(
                    "[SmithWorker] corpus normativo: %d documento(s) MUDARAM na origem",
                    r["mudaram"])
            elif r.get("conferidos"):
                logger.info("[SmithWorker] corpus normativo: %d conferido(s), sem mudanca",
                            r["conferidos"])
        except Exception as exc:  # noqa: BLE001
            logger.warning("[SmithWorker] reconferencia do corpus: %s", type(exc).__name__)

    # ------------------------------------------------------------------
    # Execução
    # ------------------------------------------------------------------

    async def _agendar(self, entry_id: str, payload: dict) -> None:
        run_id = payload.get("work_run_id")
        company_id = payload.get("company_id")
        if not run_id or not company_id:
            await self.queue.ack(entry_id)
            return

        if run_id in self._em_execucao:
            await self.queue.ack(entry_id)
            return

        # Limite por tenant: uma corretora não monopoliza o worker.
        if self._por_tenant.get(company_id, 0) >= CONCORRENCIA_POR_TENANT:
            return  # sem ack: a mensagem volta para outro worker ou para depois

        tarefa = asyncio.create_task(self._executar_run(entry_id, run_id, company_id, payload))
        self._em_execucao[run_id] = tarefa
        self._por_tenant[company_id] = self._por_tenant.get(company_id, 0) + 1
        tarefa.add_done_callback(lambda _t: self._liberar_slot(run_id, company_id))

    def _liberar_slot(self, run_id: str, company_id: str) -> None:
        self._em_execucao.pop(run_id, None)
        atual = self._por_tenant.get(company_id, 1) - 1
        if atual <= 0:
            self._por_tenant.pop(company_id, None)
        else:
            self._por_tenant[company_id] = atual

    async def _executar_run(self, entry_id: str, run_id: str, company_id: str, payload: dict) -> None:
        lease = self.runs.adquirir_lease(run_id, self.worker_id)
        if not lease:
            # Outro worker já assumiu, ou o run terminou. Ack e segue.
            await self.queue.ack(entry_id)
            return

        heartbeat = asyncio.create_task(self._heartbeat(run_id, lease["lease_token"]))
        try:
            await self._processar(run_id, company_id, payload)
        except asyncio.CancelledError:
            self.runs.falhar(run_id, company_id, "worker_shutdown",
                             "O processador foi encerrado. O trabalho será retomado automaticamente.",
                             retryable=True, proxima_tentativa_em=30)
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("[SmithWorker] run %s falhou", run_id)
            self.runs.falhar(run_id, company_id, type(exc).__name__,
                             "Não consegui concluir este trabalho. A equipe foi notificada.",
                             retryable=False)
        finally:
            heartbeat.cancel()
            self.runs.liberar_lease(run_id, lease["lease_token"])
            await self.queue.ack(entry_id)

    async def _heartbeat(self, run_id: str, lease_token: str) -> None:
        from app.services.work.runs import HEARTBEAT_INTERVALO_SEGUNDOS

        while True:
            await asyncio.sleep(HEARTBEAT_INTERVALO_SEGUNDOS)
            if not self.runs.heartbeat(run_id, lease_token):
                # Perdemos a lease — outro worker assumiu. Parar de bater.
                logger.warning("[SmithWorker] lease perdida no run %s", run_id)
                return

    async def _processar(self, run_id: str, company_id: str, payload: dict) -> None:
        """Executa o workflow do run.

        O registro de workflows é da SPEC-056 (Skill Registry). Aqui fica o
        contrato de execução: um handler recebe o contexto e devolve o
        resumo. Enquanto o registro não existe, workflows conhecidos são
        resolvidos por chave.
        """
        from app.services.work.workflows import resolver_workflow

        self.runs.evento(company_id, run_id, "run.started", "Trabalho iniciado", actor_type="worker",
                         actor_id=self.worker_id)

        workflow_key = payload.get("workflow_key")
        if not workflow_key:
            try:
                res = (self.db.client.table("work_runs").select("workflow_key, input_payload")
                       .eq("id", run_id).maybe_single().execute())
                workflow_key = (res.data or {}).get("workflow_key")
                payload = {**payload, **((res.data or {}).get("input_payload") or {})}
            except Exception:  # noqa: BLE001
                pass

        handler = resolver_workflow(workflow_key)
        if handler is None:
            self.runs.falhar(run_id, company_id, "workflow_desconhecido",
                             f"Não sei executar este tipo de trabalho ainda ({workflow_key}).",
                             retryable=False)
            return

        contexto = {
            "run_id": run_id,
            "company_id": company_id,
            "payload": payload,
            "db": self.db,
            "runs": self.runs,
            "approvals": self.approvals,
            "effects": self.effects,
            "worker_id": self.worker_id,
            "cancelado": lambda: self.runs.cancelamento_pedido(run_id),
        }

        resumo = await handler(contexto)

        if self.runs.cancelamento_pedido(run_id):
            self.runs._transicionar(run_id, "cancelled", {"cancelled_at": None})
            self.runs.evento(company_id, run_id, "run.cancelled",
                             "Trabalho cancelado. Etapas já concluídas foram preservadas.")
            return

        self.runs.concluir(run_id, company_id, resumo or "Trabalho concluído")

    # ------------------------------------------------------------------

    async def _dormir(self, segundos: float) -> None:
        try:
            await asyncio.wait_for(self.parar.wait(), timeout=segundos)
        except asyncio.TimeoutError:
            pass


async def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    worker = SmithWorker()

    laco = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            laco.add_signal_handler(sig, worker.parar.set)
        except NotImplementedError:
            pass  # Windows

    await worker.executar()


if __name__ == "__main__":
    asyncio.run(main())
