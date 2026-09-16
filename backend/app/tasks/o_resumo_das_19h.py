"""BLOCO D.4 — o resumo das 19h, uma vez por dia, por corretora.

⛔ **NENHUM SCHEDULER NOVO** (CLAUDE.md §5). Este job entra como mais um no
APScheduler que `buffer_processor` já registra, no padrão de
`relatorio_semanal_check` (`buffer_processor.py:294-300`): intervalo curto +
checagem interna de *"já é hora / já saiu hoje"*.

🔴 **As 19h são LOCAIS da corretora** — `platform_outbound.fuso_da_corretora`.
Uma corretora em Manaus recebe às 19h de Manaus.

⛔ **Dia sem movimento não manda mensagem dizendo que não houve nada.**

⚠️ Módulo LEVE: todo import pesado acontece dentro da função, sob `try`. Um
ImportError aqui derrubaria o agendador inteiro no startup (CLAUDE.md §9.1).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

#: `RESUMO_DIARIO_HORA` — a hora local. `RESUMO_DIARIO_ATIVO` — liga/desliga o
#: resumo **sem deploy**. 🔴 Ele existe porque esta SPEC CALA coisas, e o modo
#: de falha mais perigoso dela é calar demais: o rollback tem de ser um clique.
_ENV_HORA = "RESUMO_DIARIO_HORA"
_ENV_ATIVO = "RESUMO_DIARIO_ATIVO"
_HORA_PADRAO = 19

#: Marcador de "já saiu hoje", por corretora e por dia local.
_CHAVE_DO_DIA = "resumo_19h:{empresa}:{dia}"
_TTL_DO_MARCADOR = 36 * 3600


def resumo_ligado() -> bool:
    return str(os.getenv(_ENV_ATIVO, "true")).strip().lower() not in (
        "0", "false", "nao", "não", "off")


def hora_do_resumo() -> int:
    try:
        h = int(str(os.getenv(_ENV_HORA, str(_HORA_PADRAO))).strip())
        return h if 0 <= h <= 23 else _HORA_PADRAO
    except (TypeError, ValueError):
        return _HORA_PADRAO


def ja_e_hora(agora_local: datetime, hora: int) -> bool:
    """🔴 `>=`, não `==`. **PURA.**

    ⚠️ O job roda a cada 30 min; um `==` perderia o dia inteiro se a passada
    das 19h caísse em 18:59 e a seguinte em 19:31. O marcador do dia é o que
    impede o `>=` de mandar duas vezes.
    """
    return agora_local.hour >= int(hora)


async def _ja_saiu_hoje(empresa: str, dia: str) -> bool:
    """`True` = já mandei. Reserva atômica; Redis mudo devolve `False`.

    ⚠️ Aqui o fail-open custa uma mensagem repetida por dia, no máximo — e o
    silêncio custaria o dia inteiro de números.
    """
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        gravou = await r.set(_CHAVE_DO_DIA.format(empresa=empresa, dia=dia), "1",
                             ex=_TTL_DO_MARCADOR, nx=True)
        return not gravou
    except Exception as exc:  # noqa: BLE001
        logger.warning("[RESUMO 19h] marcador indisponível (%s)", type(exc).__name__)
        return False


async def check_resumo_das_19h() -> int:
    """Uma passada. Devolve quantos resumos saíram. ⛔ Nunca levanta."""
    if not resumo_ligado():
        return 0
    enviados = 0
    try:
        from app.core.database import get_supabase_client
        from app.services.o_grupo_so_o_que_importa import (
            TIPO_RESUMO_DIARIO, enviar_ao_grupo,
        )
        from app.services.os_modelos_do_grupo import montar_o_resumo
        from app.services.platform_outbound import fuso_da_corretora

        db = get_supabase_client()
        # Só corretoras com o agente de atendimento LIGADO: o resumo é sobre o
        # dia do agente, e um dia sem agente não tem o que resumir.
        ligadas = (db.client.table("agents").select("company_id")
                   .eq("agent_role", "attendance").eq("is_active", True)
                   .limit(200).execute().data or [])
        empresas = []
        for linha in ligadas:
            cid = str((linha or {}).get("company_id") or "").strip()
            if cid and cid not in empresas:
                empresas.append(cid)
    except Exception as exc:  # noqa: BLE001
        logger.error("[RESUMO 19h] não consegui listar as corretoras (%s)",
                     type(exc).__name__)
        return 0

    hora = hora_do_resumo()
    agora = datetime.now(timezone.utc)
    for empresa in empresas:
        try:
            local = agora.astimezone(fuso_da_corretora())
            if not ja_e_hora(local, hora):
                continue
            dia = local.strftime("%Y-%m-%d")
            if await _ja_saiu_hoje(empresa, dia):
                continue

            texto, contagens = await montar_o_resumo(db, empresa, agora=agora)
            if not texto:
                # ⛔ Dia sem movimento: não manda nada. O marcador já foi
                #    reservado, então também não tenta de novo hoje.
                logger.info("[RESUMO 19h] empresa=%s sem movimento — nada a dizer",
                            empresa)
                continue

            saida = await enviar_ao_grupo(
                db, company_id=empresa, tipo=TIPO_RESUMO_DIARIO, texto=texto,
                conversation_id="", dedup=False,
                resumo="resumo do dia %s" % dia, motivo="resumo_diario")
            if saida.get("enviado"):
                enviados += 1
                logger.info("[RESUMO 19h] empresa=%s | %s", empresa, contagens)
            else:
                logger.error("[RESUMO 19h] ❌ empresa=%s NÃO recebeu o resumo: %s",
                             empresa, saida.get("motivo"))
        except Exception as exc:  # noqa: BLE001
            logger.error("[RESUMO 19h] falha em empresa=%s (%s)", empresa,
                         type(exc).__name__)
    return enviados
