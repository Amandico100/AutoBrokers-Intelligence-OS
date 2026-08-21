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
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

logger = logging.getLogger(__name__)

_ESPERA_ALERTA_MIN_PADRAO = 30      # espera que já constrange
_REALERTA_HORAS_PADRAO = 6          # e a cadência do lembrete depois disso
_MAX_POR_PASSADA = 50               # trabalho limitado por varredura


# 🔴 UMA DEFINIÇÃO, DOIS DONOS — 19/08/2026.
#
# `_env_int` e o marcador de Redis moram agora em `human_handoff`, e este
# módulo os importa. Antes o marcador era uma cópia literal daqui, e a partir
# de 18/08 passaram a existir DOIS avisadores da mesma conversa: esta
# varredura e a própria ferramenta (que até então nunca rodava). Duas cópias
# do marcador seriam duas chaves diferentes no Redis, cada uma silenciando só
# a si mesma — e o grupo receberia o dobro dos alertas, que é exatamente o
# problema que o marcador existe para resolver.
#
# A direção do import já existia: este arquivo importa `HumanHandoffTool`
# daquele módulo desde que foi escrito.
#
# ⚠️ TARDIO, e não no topo. `human_handoff` puxa `langchain_core.tools`; um
# import de módulo aqui carregaria o LangChain no boot de uma tarefa de
# varredura e abriria caminho para ciclo de import. O resto deste arquivo já
# importa daquele módulo dentro da função, pelo mesmo motivo.
def _env_int(nome: str, padrao: int, minimo: int = 1) -> int:
    from app.agents.tools.human_handoff import _env_int as _impl

    return _impl(nome, padrao, minimo)


async def _ja_avisado_recentemente(conversa_id: str, horas: int) -> bool:
    from app.agents.tools.human_handoff import reivindicar_o_aviso

    return await reivindicar_o_aviso(conversa_id, horas)


async def _devolver_a_vez(conversa_id: str) -> None:
    from app.agents.tools.human_handoff import devolver_a_vez

    await devolver_a_vez(conversa_id)


async def _contar_lembrete(conversa_id: str) -> int:
    from app.agents.tools.human_handoff import contar_lembrete

    return await contar_lembrete(conversa_id)


def _max_lembretes() -> int:
    from app.agents.tools.human_handoff import MAX_LEMBRETES_POR_CONVERSA

    return _env_int("HANDOFF_MAX_LEMBRETES", MAX_LEMBRETES_POR_CONVERSA)


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
    _MAX_LEMBRETES = _max_lembretes()
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

    # =====================================================================
    # 🔴 SÓ AVISA QUEM TEM ALGUÉM ESPERANDO — 21/08/2026
    # =====================================================================
    #
    # 📊 O Founder recebeu DEZENAS de "ATENDIMENTO PRECISA DE VOCÊ" no grupo
    # da Resulta, e a frase dele foi: *"não tem coisa pra resolver"*. Tinha
    # razão. As quatro conversas em `HUMAN_REQUESTED` naquele dia terminavam
    # assim:
    #
    #     "Tá bom, obrigado"
    #     "Olha o site desse vídeo. Vai rolando e o carro vai andando."
    #     "Vixi... tô indo então"
    #     "Tem muito passo que ainda não é feito pelo agente"
    #
    # São conversas da própria equipe, capturadas pelo observador. Em TODAS a
    # última mensagem era do lado da corretora — ninguém aguardava resposta.
    #
    # `status = HUMAN_REQUESTED` diz que alguém PEDIU um humano em algum
    # momento. Não diz que alguém ainda espera. A marca é do passado; a
    # pergunta é do presente, e é outra: **a última palavra foi do cliente?**
    #
    # Se foi da corretora, o caso está com a gente, não com ele. Cobrar a
    # equipe nesse estado é o que ensina a ignorar o grupo — e aí, no dia em
    # que um segurado de verdade esperar, ninguém olha. É esse o custo real:
    # não é incômodo, é o alarme perdendo o significado.
    ids = [str(c.get("id")) for c in paradas if c.get("id")]
    esperando: set = set(ids)  # sem leitura possível, mantém o comportamento antigo
    try:
        ultimas = (db.table("messages")
                   .select("conversation_id, role, created_at")
                   .in_("conversation_id", ids)
                   .order("created_at", desc=True)
                   .limit(max(200, len(ids) * 30)).execute().data or [])
        vista: Dict[str, str] = {}
        for m in ultimas:  # já vem do mais novo para o mais antigo
            cid = str(m.get("conversation_id") or "")
            if cid and cid not in vista:
                vista[cid] = str(m.get("role") or "")
        if vista:
            # Conversa sem mensagem nenhuma continua elegível: não há motivo
            # para calar sobre um caso que nunca chegou a ter transcrição.
            esperando = {c for c in ids
                         if vista.get(c, "user") == "user"}
    except Exception as exc:  # noqa: BLE001
        # Falha de leitura NÃO pode virar silêncio. Sem saber quem espera,
        # avisa todos — é o comportamento de antes, e o defeito grave aqui
        # sempre foi calar, nunca repetir.
        logger.warning("[HandoffWatchdog] não li quem está esperando (%s) — "
                       "vou tratar todas como pendentes", type(exc).__name__)

    calados = [c for c in paradas if str(c.get("id")) not in esperando]
    if calados:
        logger.info("[HandoffWatchdog] %d conversa(s) em HUMAN_REQUESTED sem "
                    "ninguém esperando (última palavra foi da corretora) — "
                    "não vou cobrar a equipe por elas", len(calados))
    paradas = [c for c in paradas if str(c.get("id")) in esperando]
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

        # 🔴 O TETO — e ele avisa que vai calar, em vez de sumir.
        #
        # Quatro lembretes a cada 6h cobrem 24 horas. Passado isso, mais
        # mensagem não resolve: o que falta é gente, não aviso. E repetir para
        # sempre é o jeito mais rápido de a equipe aprender a rolar o grupo
        # sem ler — que é o defeito que este vigia existe para evitar.
        #
        # A ÚLTIMA mensagem diz que é a última. Parar em silêncio seria
        # trocar um defeito por outro pior.
        _n = await _contar_lembrete(conversa_id)
        if _n > _MAX_LEMBRETES:
            continue
        _ultimo = _n == _MAX_LEMBRETES

        horas = parada_ms / 3_600_000
        espera = f"{horas:.0f}h" if horas >= 1 else f"{parada_ms / 60000:.0f}min"
        motivo = (f"⏳ AINDA SEM ATENDIMENTO há {espera} — "
                  f"{conversa.get('human_handoff_reason') or 'motivo não registrado'}")
        if _ultimo:
            motivo += ("\n\n🔕 Este é o ÚLTIMO lembrete automático desta "
                       "conversa. Ela continua na Fila do painel — de lá "
                       "ninguém a tira sozinho.")
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
                # 🔴 DEVOLVE A VEZ. A linha acima reservou o direito de avisar
                # e o aviso não saiu; manter a reserva calaria a próxima
                # varredura pelas horas inteiras do marcador, justamente no
                # caso em que ninguém ficou sabendo.
                await _devolver_a_vez(conversa_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("[HandoffWatchdog] falha ao re-alertar (%s) | empresa=%s",
                         type(exc).__name__, company_id)
            await _devolver_a_vez(conversa_id)
