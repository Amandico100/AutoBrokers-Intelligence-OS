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
    """Qual versão está no ar — e, desde a P-189, de um jeito que dá para conferir.

    📊 `build_sha` vinha `"unknown"` em produção: o estágio `gitinfo` do
    Dockerfile lê `.git/HEAD`, e o EasyPanel exporta a árvore de arquivos **sem
    o `.git`**. O campo continua aqui porque ele funciona em construtores que
    mandam o `.git` — mas ele não podia seguir sendo a única resposta.

    `code_fingerprint` é a resposta que não depende do construtor: o hash dos
    `.py` que ESTE processo tem em disco. Rode `impressao_do_diretorio()` sobre
    `backend/portal_worker` no repositório e compare — se bater, o código no ar é
    o código que você escreveu; se não bater, o deploy não trocou, por mais verde
    que o painel esteja.
    """
    info = {}
    here = Path(__file__).resolve().parent
    for key, fname in (("build_sha", "build_sha.txt"), ("build_time", "build_time.txt")):
        try:
            info[key] = (here / fname).read_text(encoding="ascii").strip() or "unknown"
        except Exception:  # noqa: BLE001
            info[key] = "unknown"

    from portal_worker.impressao import impressao_do_processo

    digital, quantos = impressao_do_processo()
    info["code_fingerprint"] = digital
    info["code_files"] = quantos
    return info


def _concorrencia_configurada() -> int:
    """O que a variável pediu. Nunca levanta — `/health` não pode cair."""
    try:
        from portal_worker.leases import concorrencia_configurada

        return concorrencia_configurada()
    except Exception:  # noqa: BLE001
        return 1


def _redis_para_lease() -> bool:
    try:
        from portal_worker.leases import redis_disponivel

        return bool(redis_disponivel())
    except Exception:  # noqa: BLE001
        return False


def _concorrencia_efetiva() -> int:
    """O que o processo REALMENTE vai fazer.

    🔴 Pode ser menor que a configurada, e a diferença é o que importa: sem
    Redis não há lease, e sem lease a mesma conta poderia rodar duas vezes em
    paralelo — uma sessão de navegador sobrescrevendo a outra. Nesse caso a
    concorrência cai para 1 sozinha. Quem olha só a variável de ambiente
    concluiria que há paralelismo onde não há.
    """
    pedida = _concorrencia_configurada()
    if pedida <= 1:
        return 1
    try:
        from portal_worker.leases import politica_com_redis_fora, redis_disponivel

        if redis_disponivel():
            return pedida
        efetiva, _ = politica_com_redis_fora(pedida)
        return efetiva
    except Exception:  # noqa: BLE001
        return 1


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
        # SPEC-075 Bloco Q. A pergunta que este endpoint responde numa
        # emergência é "quantos jobs esta imagem consegue rodar ao mesmo
        # tempo, AGORA?" — e ela não tem resposta em lugar nenhum hoje. O
        # painel do EasyPanel diz o que foi CONFIGURADO; aqui diz o que o
        # processo leu, que é outra coisa quando a variável tem erro de
        # digitação ou quando o Redis está fora.
        "concurrency": _concorrencia_efetiva(),
        "concurrency_configurada": _concorrencia_configurada(),
        "redis_para_lease": _redis_para_lease(),
        # Prova de que a imagem no ar tem as journeys que o banco vai pedir.
        # 📊 P-149 existe justamente porque a MAPFRE estava no código e não na
        # imagem: um job dela terminava em "journey desconhecida" com todos os
        # testes verdes. Contar aqui torna isso conferível por uma requisição.
        "registry_entries": len(JOURNEYS),
        "portais_com_cobranca": portais_com_cobranca(),
        **build_info(),
    }
