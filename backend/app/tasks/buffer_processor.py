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
                phone = key.split(":")[-1]

                if await buffer_service.should_process(phone):
                    buffer = await buffer_service.get_and_clear_buffer(phone)

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
            seconds=3600,
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
