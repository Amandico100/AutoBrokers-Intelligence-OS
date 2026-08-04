"""VIGIA DO HANDOFF HUMANO — `HUMAN_REQUESTED` deixa de ser estado sem saída.

📊 03/08/2026, banco de produção: UMA conversa presa em `HUMAN_REQUESTED` há
~730 horas. Trinta dias. A causa não foi a marcação — foi que **nenhum job no
produto olhava `conversations.status`.** O aviso ao suporte sai uma vez, no
instante do pedido; se ninguém viu aquela mensagem, ninguém veria nunca mais, e
o segurado ficou esperando um humano para sempre.

É a MESMA fragilidade que o gatilho da reconciliação de acionamento órfão tinha
(SPEC-063 Bloco E): **um estado que só é observado quando nasce não é
observado.** Este vigia dá a ele um piso — o atraso máximo para alguém ser
lembrado deixa de ser "para sempre" e passa a ser um número.

NADA DE ESCALONAMENTO NOVO
--------------------------
O destino sai de `resolver_destino_de_suporte` — o mesmo resolvedor que recusa
destino compartilhado entre corretoras, porque o dossiê leva CPF do segurado
(CLAUDE.md §7). O texto é o dossiê que `HumanHandoffTool` já monta. O que muda
aqui é só a PERIODICIDADE do lembrete.

POR QUE ESTE ARQUIVO EXISTE, E NÃO UMA FUNÇÃO EM `human_handoff.py`
--------------------------------------------------------------------
`human_handoff.py` mora em `app/agents/tools/`, e importar dali arrasta
`app.agents.__init__` → `graph.py` → `langgraph`. O agendador é registrado por
`start_buffer_scheduler()`, que `main.py` chama **sem `try`** no startup: um
ImportError ali derruba a aplicação inteira, não só este job (CLAUDE.md §9.1 —
"build verde não é prova de que a aplicação sobe").

Então o módulo é leve, e o import pesado acontece DENTRO da função, por
execução, sob `try`. Roda no APScheduler do buffer. Falhas nunca derrubam o
agendador.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

logger = logging.getLogger(__name__)

_ESPERA_ALERTA_MIN_PADRAO = 30      # espera que já constrange
_REALERTA_HORAS_PADRAO = 6          # e a cadência do lembrete depois disso
_MAX_POR_PASSADA = 50               # trabalho limitado por varredura


def _env_int(nome: str, padrao: int, minimo: int = 1) -> int:
    try:
        return max(minimo, int(os.getenv(nome, str(padrao))))
    except (TypeError, ValueError):
        return padrao


async def _ja_avisado_recentemente(conversa_id: str, horas: int) -> bool:
    """Marcador em Redis: o lembrete é periódico, não uma metralhadora.

    Sem ele, uma conversa esquecida geraria um WhatsApp ao suporte a cada
    passada — e alerta que chega demais é alerta que se aprende a ignorar, que é
    exatamente como este estado ficou 730 horas sem ninguém olhar.

    Redis fora do ar devolve False: **avisar de novo é melhor que calar.** O
    defeito que se está consertando aqui é o silêncio, não a repetição.
    """
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        # `nx=True` é o próprio teste-e-marca, atômico: quem consegue gravar é
        # quem manda o aviso. Dois workers na mesma passada não avisam em dobro.
        gravou = await r.set(f"handoff_realerta:{conversa_id}", "1",
                             ex=horas * 3600, nx=True)
        return not gravou
    except Exception as exc:  # noqa: BLE001
        logger.warning("[HandoffWatchdog] marcador indisponível (%s) — vai avisar",
                       type(exc).__name__)
        return False


def _parado_ha_ms(conversa: Dict[str, Any], agora: datetime) -> float:
    try:
        visto = datetime.fromisoformat(
            str(conversa.get("last_message_at") or "").replace("Z", "+00:00"))
        if visto.tzinfo is None:
            visto = visto.replace(tzinfo=timezone.utc)
        return max(0.0, (agora - visto).total_seconds() * 1000)
    except (TypeError, ValueError):
        return 0.0


async def varrer_handoffs_parados() -> None:
    """Conversa parada em `HUMAN_REQUESTED` → re-alerta o suporte + telemetria."""
    espera_min = _env_int("HANDOFF_ALERTA_MINUTOS", _ESPERA_ALERTA_MIN_PADRAO)
    realerta_h = _env_int("HANDOFF_REALERTA_HORAS", _REALERTA_HORAS_PADRAO)
    agora = datetime.now(timezone.utc)
    limite = (agora - timedelta(minutes=espera_min)).isoformat()

    try:
        from app.core.database import get_supabase_client

        bruto = get_supabase_client()
        db = getattr(bruto, "client", bruto)
        if db is None:
            return
        paradas = (db.table("conversations")
                   .select("id, company_id, session_id, user_name, user_phone, "
                           "last_message_at, human_handoff_reason")
                   .eq("status", "HUMAN_REQUESTED")
                   .lt("last_message_at", limite)
                   .order("last_message_at", desc=False)
                   .limit(_MAX_POR_PASSADA).execute().data or [])
    except Exception as exc:  # noqa: BLE001
        logger.error("[HandoffWatchdog] não consegui ler as conversas (%s)",
                     type(exc).__name__)
        return

    if not paradas:
        return
    logger.info("[HandoffWatchdog] %d conversa(s) em HUMAN_REQUESTED há mais de %dmin",
                len(paradas), espera_min)

    try:
        from app.agents.tools.human_handoff import HumanHandoffTool
    except Exception as exc:  # noqa: BLE001
        logger.error("[HandoffWatchdog] ferramenta de handoff indisponível (%s)",
                     type(exc).__name__)
        return

    for conversa in paradas:
        company_id = str(conversa.get("company_id") or "")
        conversa_id = str(conversa.get("id") or "")
        # Sem company_id não há destino de suporte que se possa resolver com
        # segurança, e mandar o dossiê "para alguém" é vazamento (CLAUDE.md §7).
        if not company_id or not conversa_id:
            logger.error("[HandoffWatchdog] conversa sem company_id — ignorada")
            continue

        parada_ms = _parado_ha_ms(conversa, agora)

        # A TELEMETRIA VEM ANTES DO MARCADOR, e de propósito: ela mede a espera
        # de TODA conversa parada, inclusive as que o marcador vai silenciar. Se
        # dependesse do envio, o número sumiria justamente quando a fila
        # estivesse pior — e o gráfico melhoraria quanto mais gente esperasse.
        try:
            from app.services.observability import sli

            sli.registrar(sli.HANDOFF_ESPERA, parada_ms, company_id=company_id,
                          contexto={"minutos": round(parada_ms / 60000)})
        except Exception:  # noqa: BLE001
            pass

        if await _ja_avisado_recentemente(conversa_id, realerta_h):
            continue

        horas = parada_ms / 3_600_000
        espera = f"{horas:.0f}h" if horas >= 1 else f"{parada_ms / 60000:.0f}min"
        motivo = (f"⏳ AINDA SEM ATENDIMENTO há {espera} — "
                  f"{conversa.get('human_handoff_reason') or 'motivo não registrado'}")
        try:
            aviso = await HumanHandoffTool(db)._avisar_suporte(company_id, conversa, motivo)
            if aviso.get("avisado"):
                logger.info("[HandoffWatchdog] re-alerta enviado | empresa=%s | espera=%s",
                            company_id, espera)
            else:
                # Ninguém foi avisado, de novo. Isto é o incidente — e agora ele
                # tem uma linha de log com o motivo, em vez de nenhuma.
                logger.error("[HandoffWatchdog] ❌ conversa parada há %s e o suporte "
                             "NÃO foi avisado | empresa=%s | motivo=%s",
                             espera, company_id, aviso.get("motivo"))
        except Exception as exc:  # noqa: BLE001
            logger.error("[HandoffWatchdog] falha ao re-alertar (%s) | empresa=%s",
                         type(exc).__name__, company_id)
