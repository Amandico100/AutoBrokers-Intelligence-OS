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
  · varredor de órfãos (lease vencida) + DESPERTADOR + RE-DESPACHO (SPEC-129-A)
  · expiração de aprovações · máscara dos retratos vencidos (SPEC-129-A `_03`)
  · reconciliação de efeitos sem confirmação

A espera durável (SPEC-129-A): um handler que precisa esperar (o portal, um
humano) chama `runs.dormir(...)` e devolve `ESPERANDO` — o run fica
`waiting_input` SEM dono, e o despertador o devolve à fila quando o relógio
`wake_at` vence. O worker nunca conclui por cima de uma espera.

Executar como serviço separado:

    python -m app.workers.smith_worker
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
from typing import Any, Optional

from app.services.work.runs import (CODIGO_EFEITO_INCERTO, CODIGO_ETAPA_NAO_VERIFICADA,
                                    ETAPA_NAO_VERIFICADA_VOLTA_EM_S, CancelamentoPedido,
                                    EfeitoIncerto, EtapaNaoVerificada, Esperando)

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
        """Órfãos, DESPERTADOR e RE-DESPACHO — o mesmo laço de 60 s (D-129A-2: nenhum laço novo).

        Cada varredura tem o seu `try`: uma que falha não impede as outras.
        """
        while not self.parar.is_set():
            await self._dormir(INTERVALO_ORFAOS_S)
            try:
                orfaos = self.runs.recuperar_orfaos()
                if orfaos:
                    logger.warning("[SmithWorker] %d run(s) órfão(s) recuperado(s)", len(orfaos))
            except Exception as exc:  # noqa: BLE001
                logger.error("[SmithWorker] varredura de órfãos: %s", type(exc).__name__)
            registro = self._registro_de_workflows()
            try:
                acordados = self.runs.despertar_vencidos(registro)
                if acordados:
                    logger.info("[SmithWorker] %d run(s) acordado(s)", len(acordados))
            except Exception as exc:  # noqa: BLE001
                logger.error("[SmithWorker] despertador: %s", type(exc).__name__)
            try:
                parados = self.runs.redespachar_parados(registro)
                if parados:
                    logger.warning("[SmithWorker] %d run(s) parado(s) re-despachado(s)", len(parados))
            except Exception as exc:  # noqa: BLE001
                logger.error("[SmithWorker] re-despacho: %s", type(exc).__name__)

    @staticmethod
    def _registro_de_workflows() -> dict:
        """`{chave: handler}` do registro da SPEC-055/056 — o despertador só toca o que sabe rodar.

        O handler pode declarar `idade_maxima_s` (D-129A-5) e `ao_desistir(db, run, motivo)`.
        Registro ilegível → `{}`: nada é acordado nem expirado (falha fechada, nunca o contrário).
        """
        try:
            from app.services.work.workflows import resolver_workflow, workflows_registrados

            return {k: resolver_workflow(k) for k in workflows_registrados()}
        except Exception as exc:  # noqa: BLE001
            logger.error("[SmithWorker] registro de workflows indisponível: %s", type(exc).__name__)
            return {}

    async def _laco_manutencao(self) -> None:
        while not self.parar.is_set():
            await self._dormir(INTERVALO_MANUTENCAO_S)
            try:
                self.approvals.expirar_vencidas()
                # SPEC-129-A `_03` (P-223) — o retrato cru do acionamento só existe
                # enquanto pode ser restaurado (`monitoring` ≤ 24 h). O que venceu é
                # mascarado no banco; aqui só se dá a hora.
                self._mascarar_retratos_vencidos()
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

    def _mascarar_retratos_vencidos(self) -> None:
        try:
            cli = getattr(self.db, "client", self.db)
            res = cli.rpc("work_steps_mascarar_vencidos", {"p_horas": 24}).execute()
            n = res.data if isinstance(getattr(res, "data", None), int) else 0
            if n:
                logger.info("[SmithWorker] %d retrato(s) de acionamento mascarado(s)", n)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[SmithWorker] máscara dos retratos: %s", type(exc).__name__)

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
        # 🔴 CAS (SPEC-129-A): só `smith`, só desta corretora, só de `queued`/lease vencida.
        lease = self.runs.adquirir_lease(run_id, self.worker_id, company_id=company_id)
        if not lease:
            # Outro worker já assumiu, o run está dormindo/terminou, ou não é da fila. Ack e segue.
            await self.queue.ack(entry_id)
            return

        token = lease["lease_token"]
        heartbeat = asyncio.create_task(self._heartbeat(run_id, token))
        try:
            await self._processar(run_id, company_id, payload, lease_token=token)
        except asyncio.CancelledError:
            # 📊 Antes: prometia "será retomado" num `retry_scheduled` que ninguém relia.
            # Agora a promessa é verdade: o `wake_at` põe o despertador para buscá-lo.
            self.runs.falhar(run_id, company_id, "worker_shutdown",
                             "O processador foi reiniciado no meio deste trabalho. Ele volta para a "
                             "fila em instantes e retoma do último passo seguro; uma etapa com efeito "
                             "externo interrompida não é repetida — vai para revisão.",
                             retryable=True, proxima_tentativa_em=30, lease_token=token)
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("[SmithWorker] run %s falhou", run_id)
            self.runs.falhar(run_id, company_id, type(exc).__name__,
                             "Não consegui concluir este trabalho. A equipe foi notificada.",
                             retryable=False, lease_token=token)
        finally:
            heartbeat.cancel()
            self.runs.liberar_lease(run_id, token)
            await self.queue.ack(entry_id)

    async def _heartbeat(self, run_id: str, lease_token: str) -> None:
        from app.services.work.runs import HEARTBEAT_INTERVALO_SEGUNDOS

        while True:
            await asyncio.sleep(HEARTBEAT_INTERVALO_SEGUNDOS)
            if not self.runs.heartbeat(run_id, lease_token):
                # Perdemos a lease — outro worker assumiu. Parar de bater.
                logger.warning("[SmithWorker] lease perdida no run %s", run_id)
                return

    async def _processar(self, run_id: str, company_id: str, payload: dict,
                         lease_token: Optional[str] = None) -> None:
        """Executa o workflow do run.

        O registro de workflows é da SPEC-056 (Skill Registry). Aqui fica o
        contrato de execução: um handler recebe o contexto e devolve o
        resumo. Enquanto o registro não existe, workflows conhecidos são
        resolvidos por chave.
        """
        from app.services.work.workflows import resolver_workflow

        self.runs.evento(company_id, run_id, "run.started", "Trabalho iniciado", actor_type="worker",
                         actor_id=self.worker_id)

        # 🔴 O `input_payload` do banco é lido SEMPRE, não só quando falta o
        # `workflow_key`.
        #
        # 📊 MEDIDO EM 17/08/2026, e este foi o defeito que impediu a Cobrança
        # de rodar. A mensagem que o outbox publica na fila é MÍNIMA por
        # desenho (`work_queue_outbox.payload_minimal`, `queue.py:191-197`):
        #
        #     {"run_id": …, "company_id": …, "workflow_key": "bridge.routine.execute"}
        #
        # O `routine_id` NÃO vai nela — ele mora em `work_runs.input_payload`.
        # E a leitura do banco estava dentro de `if not workflow_key:`, um ramo
        # que nunca executa quando a chave vem na mensagem (ou seja: sempre).
        #
        # Resultado medido no Work Run `ca6bb47e`: o handler recebeu um pacote
        # sem identificador, devolveu "Rotina sem identificador — nada a
        # executar" e o run terminou `completed` em 1 segundo. Verde no painel,
        # zero trabalho feito — o pior tipo de falha, porque nem parece falha.
        #
        # A ordem do merge importa: o do BANCO por baixo, o da FILA por cima.
        # A fila carrega o roteamento (prioridade, run_id) e é a mais recente;
        # o banco carrega a entrada do trabalho.
        workflow_key = payload.get("workflow_key")
        try:
            res = (self.db.client.table("work_runs").select("workflow_key, input_payload")
                   .eq("id", run_id).maybe_single().execute())
            linha = res.data or {}
            workflow_key = workflow_key or linha.get("workflow_key")
            payload = {**(linha.get("input_payload") or {}), **payload}
        except Exception as exc:  # noqa: BLE001
            # Sem a entrada do banco, o handler quase certamente não tem o que
            # precisa. Falhar aqui é melhor que rodar vazio e reportar sucesso.
            logger.error("[SmithWorker] nao consegui ler input_payload de %s: %s",
                         run_id, type(exc).__name__)
            self.runs.falhar(run_id, company_id, "entrada_indisponivel",
                             "Não consegui ler a entrada deste trabalho no banco. Tento de novo em 1 min.",
                             retryable=True, proxima_tentativa_em=60, lease_token=lease_token)
            return

        handler = resolver_workflow(workflow_key)
        if handler is None:
            self.runs.falhar(run_id, company_id, "workflow_desconhecido",
                             f"Não sei executar este tipo de trabalho ainda ({workflow_key}).",
                             retryable=False, lease_token=lease_token)
            return

        # A espera em curso (SPEC-129-A): quantas vezes acordou, o prazo, o passo.
        # Leitura à parte e best-effort: sem a coluna (antes da `_02`) o run roda igual.
        espera: dict = {}
        try:
            res_espera = (self.db.client.table("work_runs").select("wait_for")
                          .eq("id", run_id).eq("company_id", company_id).maybe_single().execute())
            bruto = ((res_espera.data if res_espera is not None else None) or {}).get("wait_for")
            espera = dict(bruto) if isinstance(bruto, dict) else {}
        except Exception as exc:  # noqa: BLE001
            logger.warning("[SmithWorker] espera de %s ilegível: %s", run_id, type(exc).__name__)

        contexto = {
            "run_id": run_id,
            "company_id": company_id,
            "payload": payload,
            "db": self.db,
            "runs": self.runs,
            "approvals": self.approvals,
            "effects": self.effects,
            "worker_id": self.worker_id,
            # 🔴 SPEC-129-A: o token da lease viaja até o handler — `runs.dormir` e
            # `_transicionar` só escrevem com ele (CAS `running`(meu token) → …).
            "lease_token": lease_token,
            "espera": espera,
            "cancelado": lambda: self.runs.cancelamento_pedido(run_id),
        }

        try:
            resumo = await handler(contexto)
        except CancelamentoPedido:
            # 🔴 SPEC-129-A, conserto B2/Q3: o corretor pediu CANCELAR e o handler parou entre
            # etapas. NÃO é desligamento: fecha `cancelled` com o token — nunca `retry_scheduled`
            # "o processador foi reiniciado" (📊 juiz: laço de 4 voltas; red team A4b: 13 voltas,
            # 57 eventos e `expired`). O desligamento de verdade é o `CancelledError` PURO, que
            # continua subindo até `_executar_run`.
            self._fechar_cancelado(run_id, company_id, lease_token)
            return
        except EtapaNaoVerificada as exc:
            # 🔴 SPEC-129-A, conserto B1/Q1/Q2: uma etapa EXTERNA não pôde ser conferida no banco
            # e por isso NÃO rodou (nada saiu do prédio). Volta pelo despertador; a idade do
            # workflow a encerra se o banco não voltar.
            logger.warning("[SmithWorker] run %s: %s", run_id, str(exc)[:200])
            self.runs.falhar(run_id, company_id, CODIGO_ETAPA_NAO_VERIFICADA,
                             "Não consegui conferir no banco se uma etapa com efeito externo já "
                             "tinha rodado — por segurança ela NÃO rodou. Nova conferência em 1 min.",
                             retryable=True, proxima_tentativa_em=ETAPA_NAO_VERIFICADA_VOLTA_EM_S,
                             lease_token=lease_token)
            return
        except EfeitoIncerto as exc:
            # D-129A-4: um passo de efeito EXTERNO interrompido não se repete. Para aqui
            # e chama gente — o Reprocessar recusa este run (409) até alguém reconciliar.
            motivo = ("Uma etapa com efeito externo foi interrompida no meio e PODE ter "
                      "acontecido. Reconcilie antes de qualquer nova tentativa.")
            self.runs.falhar(run_id, company_id, CODIGO_EFEITO_INCERTO, motivo,
                             retryable=False, lease_token=lease_token)
            self.runs.evento(company_id, run_id, "effect.uncertain",
                             f"{motivo} ({str(exc)[:160] or type(exc).__name__})", severity="warning")
            gancho = getattr(handler, "ao_desistir", None)
            if callable(gancho):
                try:
                    gancho(self.db, {"id": run_id, "company_id": company_id,
                                     "workflow_key": workflow_key, "status": "failed"}, motivo)
                except Exception as exc_g:  # noqa: BLE001
                    logger.warning("[SmithWorker] ao_desistir de %s: %s", run_id, type(exc_g).__name__)
            return

        if self.runs.cancelamento_pedido(run_id):
            self._fechar_cancelado(run_id, company_id, lease_token)
            return

        # 🔴 SPEC-129-A (problema 2): o handler DORMIU (portal, humano) → NÃO concluir.
        # O run está `waiting_input`/`waiting_approval`, sem dono; quem o retoma é o
        # despertador. Concluir aqui era o worker escrevendo `completed` por cima da espera.
        if isinstance(resumo, Esperando):
            return

        self.runs.concluir(run_id, company_id, resumo or "Trabalho concluído", lease_token=lease_token)

    def _fechar_cancelado(self, run_id: str, company_id: str, lease_token: Optional[str]) -> bool:
        """`running|cancelling|planning`(meu token) → `cancelled`, com o evento na linha do tempo."""
        if self.runs._transicionar(run_id, "cancelled", {
            "cancelled_at": _agora_iso(), "finished_at": _agora_iso(),
            "lease_owner": None, "lease_token": None, "lease_expires_at": None,
        }, de=("running", "cancelling", "planning"), lease_token=lease_token,
                company_id=company_id, perda_esperada=True):
            # perda_esperada (SPEC-129-A F5): o handler pode ter FECHADO o próprio run
            # (`falhar` aceita `cancelling`) e devolvido ESPERANDO — perder aqui não é corrida.
            self.runs.evento(company_id, run_id, "run.cancelled",
                             "Trabalho cancelado. Etapas já concluídas foram preservadas.")
            return True
        return False

    # ------------------------------------------------------------------

    async def _dormir(self, segundos: float) -> None:
        try:
            await asyncio.wait_for(self.parar.wait(), timeout=segundos)
        except asyncio.TimeoutError:
            pass


def _agora_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


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
