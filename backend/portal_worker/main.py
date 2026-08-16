"""portal-worker (SPEC-020 P1): FastAPI fino (health) + poll loop no startup.
Serviço próprio no EasyPanel (mesmo repo; Dockerfile em backend/portal_worker/).
Gate PORTAL_REAL_ENABLED off por padrão: sobe, responde /health, não age."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI

from portal_worker.worker import poll_loop, portal_real_enabled

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="AutoBrokers Portal Worker")


def build_info() -> dict:
    """SHA/hora gravados no build (Dockerfile stage gitinfo) — prova qual versão
    está no ar. Sem os arquivos (ex.: dev local) devolve 'unknown', nunca quebra."""
    info = {}
    here = Path(__file__).resolve().parent
    for key, fname in (("build_sha", "build_sha.txt"), ("build_time", "build_time.txt")):
        try:
            info[key] = (here / fname).read_text(encoding="ascii").strip() or "unknown"
        except Exception:  # noqa: BLE001
            info[key] = "unknown"
    return info


@app.on_event("startup")
async def _startup() -> None:
    asyncio.create_task(poll_loop())


@app.get("/health")
async def health() -> dict:
    """Estado operacional NÃO sensível — SPEC-073 Bloco I.

    A pergunta que este endpoint precisa responder numa emergência é *"o que
    está ligado agora?"*, e ela não pode custar um deploy para ser respondida.
    📊 Antes desta SPEC, a única forma de saber se o discovery estava ligado era
    ler o painel do EasyPanel — e o painel diz o que foi CONFIGURADO, não o que
    o processo no ar realmente leu.

    Nunca expõe credencial, proxy completo, conta ou chave. Só presença e modo.
    """
    from portal_worker.journeys import JOURNEYS, portais_com_cobranca
    from portal_worker.runtime import (
        discovery_mode, kill_switch_ativo, profiler_enabled, raw_trace_enabled,
    )
    from portal_worker.perception import visao_habilitada, provider_de_visao
    from portal_worker.worker import JOB_TIMEOUT_SECONDS, POLL_SECONDS

    return {
        "status": "healthy",
        "portal_real_enabled": portal_real_enabled(),
        # 🔴 O kill switch aparece aqui de propósito: ele passou a alcançar este
        # processo nesta SPEC, e quem aperta o freio precisa conseguir CONFERIR
        # que ele pegou, sem abrir log de contêiner.
        "kill_switch_ativo": kill_switch_ativo(),
        "discovery_mode": discovery_mode(),
        "profiler_enabled": profiler_enabled(),
        "raw_trace_enabled": raw_trace_enabled(),
        "vision_enabled": visao_habilitada(),
        "vision_provider": provider_de_visao() if visao_habilitada() else None,
        "job_timeout_seconds": JOB_TIMEOUT_SECONDS,
        "poll_seconds": POLL_SECONDS,
        # Prova de que a imagem no ar tem as journeys que o banco vai pedir.
        # 📊 P-149 existe justamente porque a MAPFRE estava no código e não na
        # imagem: um job dela terminava em "journey desconhecida" com todos os
        # testes verdes. Contar aqui torna isso conferível por uma requisição.
        "registry_entries": len(JOURNEYS),
        "portais_com_cobranca": portais_com_cobranca(),
        **build_info(),
    }
