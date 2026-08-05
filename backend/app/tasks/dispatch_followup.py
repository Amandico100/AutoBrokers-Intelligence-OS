"""Follow-up proativo pós-acionamento (SPEC-031 Faixa 6).

Sessões em MONITORING ganham timers quando o protocolo é capturado:
- followup_at (~45min): "o prestador já chegou? tá tudo certo?"
- closing_at  (~3h):    encerramento carinhoso do atendimento.

Roda no MESMO APScheduler do buffer (job a cada 60s). Nunca reenvia (flags na
sessão); nunca fala com a seguradora — só com o CLIENTE, pela integração da
corretora. Falhas nunca derrubam o scheduler.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

FOLLOWUP_TEXT = (
    "Oi! Passando pra saber: o prestador já chegou aí? Tá tudo certo? 🙂\n"
    "Se ainda não chegou ou algo estiver estranho, me fala que eu resolvo."
)
# O ENCERRAMENTO NÃO AFIRMA O QUE NINGUÉM CONFERIU.
#
# 📊 Achado em 05/08/2026, e era o pior defeito de confiança do produto: este
# texto saía SÓ PELO RELÓGIO. Um segurado que tinha acabado de responder "não
# chegou ninguém ainda" recebia, 2h30 depois, "Espero que tenha dado tudo
# certo!" — e a sessão era marcada `resolvido` e liberada logo abaixo.
#
# O caso morria em silêncio dizendo que deu certo. É o único ponto do sistema
# onde ele afirmava ao cliente um fato que o próprio cliente havia contradito
# minutos antes.
#
# Agora este texto só alcança quem NÃO respondeu — e mesmo aí ele não afirma
# nada: reconhece que não sabe e deixa a porta aberta. É o que a atendente faz.
# 📊 Do acervo: "Sr, nao lhe retornei ainda porque ainda nao foi resolvido ta,
# quero dar so a noticia boa... gentileza aguardar."
CLOSING_TEXT = (
    "Vou deixar seu atendimento registrado aqui comigo 🙂\n"
    "Se ficou alguma coisa pendente com o serviço, é só me chamar que eu retomo na hora."
)


def _quando_perguntamos(session: dict) -> str:
    """A hora em que o follow-up saiu, lida do próprio transcript da sessão.

    Não inventa campo novo: a entrada `[AO CLIENTE]` já é gravada com `at` e
    `step="followup_sent"` no envio, logo abaixo. Ler dali é o que faz esta
    verificação funcionar para as sessões que já estão no ar agora, sem
    backfill.
    """
    for entrada in reversed(session.get("transcript") or []):
        if isinstance(entrada, dict) and entrada.get("step") == "followup_sent":
            return str(entrada.get("at") or "")
    return ""


async def _cliente_respondeu_ao_followup(company_id: str, client_phone: str,
                                         session: dict) -> bool:
    """O cliente falou depois de a gente perguntar?

    FALHA ABERTA, de propósito, e é o contrário do costume desta casa.
    ------------------------------------------------------------------
    Em toda outra trava do produto a dúvida vira recusa. Aqui não: se esta
    função não conseguir ler o banco, ela responde **True** — ou seja, NÃO
    encerra.

    O motivo é a assimetria do dano. Não encerrar um caso já resolvido custa
    uma sessão viva a mais até o TTL, que ninguém sente. Encerrar um caso NÃO
    resolvido custa um segurado parado na estrada ouvindo "espero que tenha
    dado tudo certo" — e a corretora descobrindo pelo cliente.

    📊 O dano da direção errada foi medido: era exatamente isso que acontecia.
    """
    quando = _quando_perguntamos(session)
    if not quando:
        # Sem rastro da pergunta, não há como saber se houve resposta.
        return True
    try:
        from app.core.database import get_supabase_client

        db = get_supabase_client()
        alvo = "".join(ch for ch in str(client_phone or "") if ch.isdigit())
        if not alvo:
            return True
        # Os últimos 8 dígitos evitam o problema do 9º dígito e do DDI, que é
        # a mesma armadilha que o `channel_security` já documenta.
        r = (db.client.table("attendance_transcripts")
             .select("id, counterparty, direction, wa_timestamp")
             .eq("company_id", company_id)
             .gt("wa_timestamp", quando)
             .limit(200).execute())
        for linha in (r.data or []):
            contraparte = "".join(ch for ch in str(linha.get("counterparty") or "")
                                  if ch.isdigit())
            if not contraparte or contraparte[-8:] != alvo[-8:]:
                continue
            if str(linha.get("direction") or "").lower() in ("in", "inbound", "received"):
                return True
        return False
    except Exception as exc:  # noqa: BLE001
        logger.warning("[FOLLOWUP] nao consegui conferir a resposta do cliente "
                       "(%s) — NAO encerrando, que e o lado seguro",
                       type(exc).__name__)
        return True


def _due(ts: str) -> bool:
    try:
        when = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) >= when
    except Exception:  # noqa: BLE001
        return False


async def check_dispatch_followups() -> int:
    """Varre as sessões de dispatch em monitoring e envia follow-ups vencidos."""
    sent = 0
    try:
        from app.core.redis import get_async_redis_client
        from app.services.dispatch_router import save_active_dispatch
        from app.services.integration_service import get_integration_service
        from app.services.whatsapp_service import get_whatsapp_service

        redis = await get_async_redis_client()
        wa = get_whatsapp_service()
        integrations = get_integration_service()

        async for key in redis.scan_iter(match="dispatch:active:*"):
            k = key.decode() if isinstance(key, (bytes, bytearray)) else str(key)
            raw = await redis.get(k)
            if not raw:
                continue
            try:
                session = json.loads(raw.decode() if isinstance(raw, (bytes, bytearray)) else raw)
            except Exception:  # noqa: BLE001
                continue
            if str(session.get("state") or "") != "monitoring":
                continue
            client_phone = str(session.get("client_phone") or "").strip()
            if not client_phone:
                continue
            todo = None
            if not session.get("followup_sent") and session.get("followup_at") and _due(session["followup_at"]):
                todo = ("followup_sent", FOLLOWUP_TEXT)
            elif not session.get("closing_sent") and session.get("closing_at") and _due(session["closing_at"]):
                # QUEM RESPONDEU NÃO É ENCERRADO PELO RELÓGIO.
                #
                # 📊 Este `elif` só olhava a hora. Um segurado que respondia
                # "não chegou ninguém ainda" recebia, 2h30 depois, "Espero que
                # tenha dado tudo certo!" — e a sessão virava `resolvido` logo
                # abaixo. O caso morria em silêncio afirmando o contrário do
                # que o próprio cliente tinha acabado de dizer.
                #
                # Quem respondeu está sendo conduzido pelo agente de
                # atendimento. Encerrar por cima é declarar resolvido o que
                # ninguém conferiu — e é o único ponto do produto onde ele
                # contradizia o cliente.
                if await _cliente_respondeu_ao_followup(company_id, client_phone, session):
                    session["followup_respondido"] = True
                    session["closing_sent"] = True   # não insiste no relógio
                    await save_active_dispatch(company_id, insurer_phone, session)
                    logger.info("[FOLLOWUP] case=%s o cliente respondeu — encerramento "
                                "por relogio cancelado, o agente conduz",
                                session.get("case_id"))
                    continue
                todo = ("closing_sent", CLOSING_TEXT)
            if not todo:
                continue
            # dispatch:active:{company}:{insurer_phone}
            parts = k.split(":")
            company_id = parts[2] if len(parts) >= 4 else ""
            insurer_phone = parts[3] if len(parts) >= 4 else ""
            integration = integrations.get_platform_whatsapp_integration(company_id) if company_id else None
            if not integration:
                continue
            try:
                # PELO CANAL GOVERNADO — com a exceção que o torna possível.
                #
                # 📊 Era o único envio frio a segurado que furava o governador:
                # não respeitava a parada de emergência, não contava nos tetos e
                # não entrava em `platform_sends`.
                #
                # Plugar aqui exigiu a exceção de `monitoring` em `client_busy`
                # (ver platform_outbound). Sem ela, o follow-up seria adiado para
                # sempre: ele só roda em `monitoring`, e `monitoring` o marcaria
                # como ocupado. Consertar um lado sem o outro teria trocado
                # "manda sem governo" por "nunca manda" — e o segundo é pior,
                # porque não deixa rastro nenhum.
                try:
                    from app.services.platform_outbound import send_to_client_guarded

                    resultado = await send_to_client_guarded(
                        company_id, client_phone, todo[1],
                        kind="acionamento_followup" if todo[0] == "followup_sent"
                        else "acionamento_encerramento",
                        summary=todo[1][:180],
                    )
                    r = resultado or {}
                    # `queued` é SUCESSO, e essa distinção importa.
                    #
                    # O governador tem fila própria com backoff: quando ele
                    # enfileira, a mensagem VAI sair — só não agora. Tratar isso
                    # como falha faria este laço reenviar a cada 60s e empilhar
                    # cópias da mesma pergunta.
                    #
                    # O que é falha de verdade é `ok: False` (governador negou
                    # de vez). Aí não marcamos nada e a próxima varredura tenta.
                    if not r.get("ok"):
                        logger.info("[FOLLOWUP] governador negou case=%s motivo=%s",
                                    session.get("case_id"), r.get("reason"))
                        continue
                except ImportError:
                    wa.send_message(client_phone, todo[1], integration)
                session[todo[0]] = True

                # A PERGUNTA PASSA A EXISTIR NA CONVERSA.
                #
                # 📊 Ate 03/08 esta mensagem saia e nao deixava rastro nenhum: o
                # cliente respondia "nao chegou ainda" e caia no agente de
                # atendimento, que **nao sabia que uma pergunta tinha sido
                # feita**. A resposta chegava sem contexto e o ciclo nunca
                # fechava.
                #
                # Nao e preciso um agente novo para ler a resposta: basta o
                # agente da entrada SABER o que foi perguntado. `platform_sends`
                # e exatamente a tabela que alimenta a nota de contexto dele.
                try:
                    from app.services.platform_outbound import record_platform_send

                    await record_platform_send(
                        company_id, client_phone,
                        "acionamento_followup" if todo[0] == "followup_sent" else "acionamento_encerramento",
                        todo[1][:180])
                except Exception:  # noqa: BLE001
                    logger.warning("[FOLLOWUP] rastro do envio nao registrado")

                # E entra no transcript, como o Vigia ja faz — sem isto o
                # Espelho, a linha do tempo e o dossie omitem o que foi dito.
                session.setdefault("transcript", []).append(
                    {"direction": "out", "text": f"[AO CLIENTE] {todo[1]}",
                     "at": datetime.now(timezone.utc).isoformat(),
                     "step": todo[0]})

                # E O ENCERRAMENTO PASSA A ENCERRAR.
                #
                # 📊 `closing_sent` so mandava texto: a sessao ficava viva em
                # `monitoring` ate o TTL de 24h. Nada marcava resolvido, nada
                # liberava a corretora, e o Vigia e cego a `monitoring` — uma
                # sessao que silencia para sempre nao era vista por ninguem.
                if todo[0] == "closing_sent":
                    session["state"] = "resolvido"
                    session["resolved_at"] = datetime.now(timezone.utc).isoformat()

                await save_active_dispatch(company_id, insurer_phone, session)
                if todo[0] == "closing_sent":
                    try:
                        from app.services.dispatch_router import clear_active_dispatch

                        await clear_active_dispatch(company_id, insurer_phone)
                    except Exception:  # noqa: BLE001
                        logger.warning("[FOLLOWUP] sessao encerrada nao foi liberada")
                sent += 1
                logger.info(f"[FOLLOWUP] {todo[0]} enviado case={session.get('case_id')}")
                # SPEC-050 (auditoria): a ação vira linha no feed de Atividades.
                try:
                    from app.services.activity_log import log_activity

                    await log_activity(company_id, "acionamentos",
                                       "Cliente acompanhado após o acionamento"
                                       if todo[0] == "followup_sent" else "Atendimento encerrado com carinho",
                                       "Conferimos com o cliente se o prestador chegou e se está tudo certo.")
                except Exception:  # noqa: BLE001
                    pass
            except Exception as e:  # noqa: BLE001
                logger.error(f"[FOLLOWUP] envio falhou: {type(e).__name__}")
    except Exception as e:  # noqa: BLE001 — nunca derruba o scheduler
        logger.error(f"[FOLLOWUP] varredura falhou: {type(e).__name__}")
    try:
        from app.core.heartbeat import beat

        await beat("followup", sent)
    except Exception:  # noqa: BLE001
        pass
    return sent
