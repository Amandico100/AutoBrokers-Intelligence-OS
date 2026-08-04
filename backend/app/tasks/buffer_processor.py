"""
Buffer Processor - Periodic task to check and process WhatsApp message buffers.
ASYNC VERSION: Redis operations are non-blocking.
"""

import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.redis import get_async_redis_client
from app.services.message_buffer_service import get_message_buffer_service

logger = logging.getLogger(__name__)

logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("apscheduler.scheduler").setLevel(logging.WARNING)
logging.getLogger("apscheduler.executors").setLevel(logging.WARNING)
logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)

scheduler = AsyncIOScheduler()


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    try:
        return max(minimum, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


async def check_buffers():
    """
    Periodic job - scans Redis for ready buffers (async, non-blocking).
    """
    redis = await get_async_redis_client()
    buffer_service = await get_message_buffer_service()

    from app.api.webhook import process_whatsapp_message_background

    try:
        cursor = 0
        processed_count = 0

        while True:
            cursor, keys = await redis.scan(
                cursor=cursor, match="whatsapp_buffer:*", count=100
            )

            for key in keys:
                # SPEC-063 Bloco H — a chave agora tem tenant
                # (`whatsapp_buffer:{integracao}:{telefone}`) e o varredor passa
                # a chave INTEIRA. Extrair o telefone e remontar a chave era o
                # que prendia o buffer ao formato antigo de uma parte só.
                chave = key.decode() if isinstance(key, (bytes, bytearray)) else str(key)
                phone = chave.rsplit(":", 1)[-1]

                if await buffer_service.should_process(chave):
                    buffer = await buffer_service.get_and_clear_buffer(chave)

                    if buffer:
                        combined_msg = buffer_service.get_combined_message(buffer)
                        msg_count = len(buffer["messages"])

                        logger.info(
                            f"[BUFFER] Processing buffer for {phone}: {msg_count} messages"
                        )

                        await process_whatsapp_message_background(
                            payload_dict=buffer["payload"],
                            combined_message=combined_msg,
                            buffered_messages=list(buffer.get("messages") or []),
                        )

                        logger.info(
                            f"[BUFFER] ✅ Processed {phone}: combined {msg_count} msgs"
                        )
                        processed_count += 1

            if cursor == 0:
                break

    except Exception as e:
        logger.error(f"[BUFFER] ❌ Error in check_buffers: {e}", exc_info=True)


def start_buffer_scheduler():
    """Start the APScheduler for buffer processing."""
    if not scheduler.running:
        scheduler.add_job(
            check_buffers,
            "interval",
            seconds=1,
            id="whatsapp_buffer_check",
            max_instances=10,
        )
        # Follow-up pós-acionamento (SPEC-031 Faixa 6): "o guincho chegou?" e
        # encerramento carinhoso — varre sessões monitoring a cada 60s.
        from app.tasks.dispatch_followup import check_dispatch_followups

        scheduler.add_job(
            check_dispatch_followups,
            "interval",
            seconds=60,
            id="dispatch_followup_check",
            max_instances=1,
        )
        # VIGIA + SENTINELA (SPEC-034 Onda 1): vigilância de desfecho e
        # recuperação de travas nos acionamentos — varredura a cada 20s.
        from app.tasks.dispatch_watchdog import check_dispatch_watchdog

        scheduler.add_job(
            check_dispatch_watchdog,
            "interval",
            seconds=20,
            id="dispatch_watchdog_check",
            max_instances=1,
        )
        # GARIMPO (SPEC-034 Onda 3): minera desejos/dores dos corretores 1x/dia
        # (marcador em Redis; captura determinística, custo zero de LLM).
        from app.services.broker_insights import check_garimpo

        scheduler.add_job(
            check_garimpo,
            "interval",
            seconds=3600,
            id="garimpo_check",
            max_instances=1,
        )
        # AUDITOR + overlays do ALFAIATE (SPEC-034 Onda 4): scorecards 1x/dia
        # (marcador Redis) e cache de overlays atualizado a cada varredura.
        from app.services.conversation_auditor import check_auditor

        scheduler.add_job(
            check_auditor,
            "interval",
            seconds=1800,
            id="auditor_check",
            max_instances=1,
        )
        # IA DE SUGESTÕES (SPEC-034 Onda 5): auxiliar global ON por padrão —
        # 1 msg/semana por corretora (segunda, horário comercial, marcador Redis).
        from app.services.proactive_suggestions import check_suggestions

        scheduler.add_job(
            check_suggestions,
            "interval",
            seconds=1800,
            id="sugestoes_check",
            max_instances=1,
        )
        # RELATÓRIO DE SÁBADO (SPEC-036): resumo semanal das Atividades por
        # corretora ("olha quanta coisa fizemos") — sábado de manhã, 1x/semana.
        from app.services.weekly_report import check_weekly_report

        scheduler.add_job(
            check_weekly_report,
            "interval",
            seconds=1800,
            id="relatorio_semanal_check",
            max_instances=1,
        )
        # SENTINELA DE ROTAS (SPEC-038/039 F1): tece TODAS as seguradoras e
        # detecta mudança de menu — 1x/dia (marcador Redis). Dá vida própria ao
        # Atlas: os mapas se atualizam sozinhos e o drift é detectado.
        from app.services.atlas.route_sentinel import check_atlas_sentinela

        scheduler.add_job(
            check_atlas_sentinela,
            "interval",
            minutes=_env_int("ATLAS_INCREMENTAL_INTERVAL_MINUTES", 15),
            id="atlas_sentinela_check",
            max_instances=1,
        )

        # SPEC-051: mídias do Observador nunca bloqueiam o webhook. Um lote
        # pequeno é enriquecido separadamente e armazenado apenas em cofre.
        from app.services.atlas.observer_media import observer_media_check

        scheduler.add_job(
            observer_media_check,
            "interval",
            seconds=_env_int("OBSERVER_MEDIA_INTERVAL_SECONDS", 10, minimum=5),
            id="observer_media_check",
            max_instances=1,
        )

        # SPEC-062 §30.3 — BACKUP DO STORAGE, de hora em hora.
        #
        # O Supabase faz backup do Postgres pelo plano. O MinIO nao tinha
        # rotina nenhuma — e e ele que guarda a UNICA copia de cada documento
        # que a corretora enviou. O Postgres guarda o ponteiro, nao o arquivo.
        #
        # A rotina e incremental (so copia o que falta) e NUNCA apaga no
        # destino: um espelho que replica exclusao e inutil justamente no caso
        # que mais importa — alguem apaga por engano e o backup apaga junto.
        from app.services.backup.minio_backup import rodar_periodicamente as _backup

        scheduler.add_job(
            _backup,
            "interval",
            minutes=_env_int("MINIO_BACKUP_INTERVAL_MINUTES", 60),
            id="minio_backup",
            max_instances=1,
        )

        # SPEC-040 Onda 1: retenção do Espelho de Atendimento — o transcript
        # cru (com PII) expira; purge 1x/dia (marcador Redis, gate na task).
        from app.services.atlas.attendance_capture import check_attendance_purge

        scheduler.add_job(
            check_attendance_purge,
            "interval",
            seconds=3600,
            id="attendance_purge_check",
            max_instances=1,
        )

        # SPEC-040 Onda 2: seed do conhecimento global (idempotente por hash) —
        # 1ª rodada ~2min após o boot, depois checagem horária (custo zero se
        # nada mudou). É o que popula a coleção autobrokers_global sozinho.
        from datetime import datetime as _dt, timedelta as _td, timezone as _tz

        from app.services.global_knowledge_seed import check_global_seed

        scheduler.add_job(
            check_global_seed,
            "interval",
            seconds=3600,
            id="global_seed_check",
            max_instances=1,
            next_run_time=_dt.now(_tz.utc) + _td(seconds=120),
        )

        # SPEC-040 Onda 3: Destilador do Espelho de Atendimento — 1x/dia na
        # madrugada (janela + marcador dentro da task). Sonnet no braçal,
        # modelo forte na síntese de playbook. Zero LLM sem sessão nova.
        from app.services.attendance_distiller import check_attendance_distiller

        scheduler.add_job(
            check_attendance_distiller,
            "interval",
            # A cada 30 min. No regime normal a task sai em milissegundos (fora
            # da janela da madrugada ou marcador do dia ja gravado); o intervalo
            # curto so importa no MODO DE RECUPERACAO, depois de um pareamento.
            seconds=_env_int("DISTILLER_CHECK_SECONDS", 1800),
            id="attendance_distiller_check",
            max_instances=1,
        )

        # SPEC-040 Onda 4: Sentinela de Regressão — nota média 24h vs 7 dias,
        # por corretora; queda relevante = alerta ANTES do cliente sentir.
        # Determinístico, zero LLM, 1x/dia (marcador na task).
        from app.services.regression_sentinel import check_regression

        scheduler.add_job(
            check_regression,
            "interval",
            seconds=3600,
            id="regression_sentinel_check",
            max_instances=1,
        )

        # SPEC-040 Onda 5: memória por agente — blocos reescritos 1x/dia a
        # partir dos dados reais (determinístico, zero LLM). A Central mostra
        # "o que cada agente sabe".
        from app.services.agent_memory import check_agent_memories

        scheduler.add_job(
            check_agent_memories,
            "interval",
            hours=_env_int("AGENT_MEMORY_INTERVAL_HOURS", 6),
            id="agent_memory_check",
            max_instances=1,
        )

        # SPEC-042: Lapidador — otimização reflexiva SEMANAL dos playbooks
        # ativos com feedback novo (padrão GEPA); draft passa pelo gate.
        from app.services.prompt_optimizer import check_lapidador

        scheduler.add_job(
            check_lapidador,
            "interval",
            seconds=3600,
            id="lapidador_check",
            max_instances=1,
        )

        # SPEC-045: fila de cortesia — envios de plataforma adiados (cliente
        # estava em atendimento) são re-tentados a cada 10 min.
        from app.services.platform_outbound import check_platform_queue

        scheduler.add_job(
            check_platform_queue,
            "interval",
            seconds=600,
            id="platform_queue_check",
            max_instances=1,
        )

        # SPEC-063 Bloco E / P-34 — VARREDURA DE ACIONAMENTO ÓRFÃO, periódica.
        #
        # A varredura existia e era boa; o GATILHO é que era frágil.
        # `_agendar_reconciliacao_uma_vez()` dispara no primeiro cache-miss do
        # processo, uma vez só. Isso tem duas falhas, e a segunda é a que dói:
        #
        #   1. uma vez por processo — depois disso, um Redis esvaziado às 3h da
        #      manhã só é notado no próximo deploy;
        #   2. e ela depende de TRÁFEGO. Se o cache cair e nenhuma mensagem
        #      chegar, `load_active_dispatch` nunca é chamado, o cache-miss
        #      nunca acontece, e o segurado com o guincho a caminho fica órfão
        #      **em silêncio** — exatamente o caso que a varredura existe para
        #      cobrir. O único sintoma é uma conversa que não anda.
        #
        # 5 minutos é folgado contra a janela real: a sessão vive 6h no Redis
        # (24h em `monitoring`). O que muda é o piso — o atraso máximo para
        # perceber um órfão deixa de ser "até alguém mandar uma mensagem" e
        # passa a ser um número.
        #
        # A varredura é idempotente por construção (órfão já sinalizado não
        # vira alarme de novo) e limitada a 50 runs em voo por passada.
        from app.services.dispatch_router import reconciliar_acionamentos_orfaos

        scheduler.add_job(
            reconciliar_acionamentos_orfaos,
            "interval",
            minutes=_env_int("DISPATCH_RECONCILE_INTERVAL_MINUTES", 5),
            id="dispatch_reconcile_check",
            max_instances=1,
            # Depois de um deploy, o cache está vazio e a verdade durável não.
            # Este é o momento de maior chance de órfão no dia inteiro.
            next_run_time=_dt.now(_tz.utc) + _td(seconds=60),
        )

        # SPEC-063 Bloco V — HEARTBEAT DO CANAL: o vigia que desmente.
        #
        # 📊 03/08/2026, banco de produção: três integrações ATIVAS afirmando
        # `connected`/`connecting` com `last_seen_at` congelado em 28-29/07 —
        # quatro e cinco dias de estado que ninguém confirmava. A causa era que
        # NADA renovava a coluna: ela só é escrita quando chega um
        # `connection.update`, e evento de transição não chega em canal parado.
        #
        # O heartbeat pergunta ao provedor e grava a resposta. Confirmou →
        # renova `last_seen_at` (é o que faz a idade da coluna significar algo).
        # Não confirmou por mais de 15 min → o estado vira `unknown` e a tela
        # para de prometer atendimento. A lógica inteira mora em
        # `channel_state.py`, o dono declarado do estado do canal; aqui só se
        # registra o job no agendador que já existe.
        from app.services.whatsapp.channel_state import verificar_canais

        scheduler.add_job(
            verificar_canais,
            "interval",
            minutes=_env_int("CHANNEL_HEARTBEAT_INTERVAL_MINUTES", 5),
            id="channel_heartbeat_check",
            max_instances=1,
            # Primeira passada logo após o boot: depois de um deploy a verdade
            # é restaurada em ~90s, não no fim do primeiro intervalo.
            next_run_time=_dt.now(_tz.utc) + _td(seconds=90),
        )
        # SPEC-063 — VIGIA DO HANDOFF HUMANO: `HUMAN_REQUESTED` deixa de ser
        # estado sem saída.
        #
        # 📊 03/08/2026, banco de produção: UMA conversa presa em
        # `HUMAN_REQUESTED` há ~730 horas. Trinta dias. A causa não foi a
        # marcação — foi que NENHUM job olhava `conversations.status`. O aviso
        # ao suporte saía uma vez, no instante do pedido; se ninguém viu aquela
        # mensagem, ninguém veria nunca mais.
        #
        # É a MESMA fragilidade do gatilho de reconciliação de acionamento
        # órfão, logo acima: um estado que só é observado quando nasce não é
        # observado. Este job dá a ele um piso — o atraso máximo para alguém
        # ser lembrado deixa de ser "para sempre" e passa a ser um número.
        #
        # A lógica mora em `app/tasks/handoff_watchdog.py`, ao lado dos outros
        # vigias, e o import da FERRAMENTA de handoff (que arrasta `langgraph`)
        # acontece dentro da função, por execução. `main.py` chama
        # `start_buffer_scheduler()` sem `try`: um ImportError aqui derrubaria a
        # aplicação inteira, não só este job (CLAUDE.md §9.1).
        from app.tasks.handoff_watchdog import varrer_handoffs_parados

        scheduler.add_job(
            varrer_handoffs_parados,
            "interval",
            minutes=_env_int("HANDOFF_WATCHDOG_INTERVAL_MINUTES", 10),
            id="handoff_watchdog_check",
            max_instances=1,
            # Depois de um deploy, quem já estava esperando continua esperando.
            next_run_time=_dt.now(_tz.utc) + _td(seconds=120),
        )

        scheduler.start()
        logger.info("✅ [BUFFER SCHEDULER] Started (interval: 1s, max_instances: 10)")
    else:
        logger.warning("[BUFFER SCHEDULER] Already running")


def shutdown_buffer_scheduler():
    """Shutdown the APScheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("🛑 [BUFFER SCHEDULER] Stopped")
    else:
        logger.warning("[BUFFER SCHEDULER] Not running")
