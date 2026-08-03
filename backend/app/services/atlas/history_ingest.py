"""SPEC-038 ATLAS — Ingestão do HistorySync (Bloco C+ / pré-requisito de segunda).

Quando o WhatsApp de uma atendente é pareado, o WhatsApp empurra o HISTÓRICO
recente (HistorySync). Este módulo transforma esse histórico em observed_events
— MAS com duas regras que o founder cravou (18/07):

1. RECÊNCIA PRIMEIRO: conversas processadas da MAIS RECENTE para a mais antiga.
   A rota mais nova de cada seguradora vale mais; a antiga pode ter menus
   obsoletos. O Tecelão (weaver) usa `last_seen` para o recente prevalecer.
2. FILTRO DE BORDA: só conversas com números de SEGURADORA entram; o resto do
   histórico pessoal da atendente é DESCARTADO na borda (privacidade).

Shape do HistorySync (whatsmeow, tolerante — confirmável só no 1º pareamento):
o GO manda {event:"HistorySync", data:{Conversations|conversations:[{ID|id,
Messages|messages:[{Message|message:{key, message, messageTimestamp}}]}]}}.
Guardamos o payload BRUTO do 1º sync no Redis p/ inspeção e ajuste fino.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

def _find_conversations(data: Any) -> List[Dict[str, Any]]:
    """Localiza a lista de conversas no payload (tolerante a casing/aninhamento)."""
    if isinstance(data, dict):
        for key in ("Conversations", "conversations", "Data", "data", "history", "History"):
            v = data.get(key)
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
            if isinstance(v, dict):
                found = _find_conversations(v)
                if found:
                    return found
    return []


def _conv_jid(conv: Dict[str, Any]) -> str:
    for k in ("ID", "id", "Jid", "jid", "chatJid", "ChatJid"):
        val = conv.get(k)
        if isinstance(val, str) and val:
            return val
        if isinstance(val, dict):  # JID estruturado {User, Server}
            u, s = val.get("User") or val.get("user"), val.get("Server") or val.get("server")
            if u:
                return f"{u}@{s or 's.whatsapp.net'}"
    return ""


def _conv_messages(conv: Dict[str, Any]) -> List[Dict[str, Any]]:
    for k in ("Messages", "messages", "msgs"):
        v = conv.get(k)
        if isinstance(v, list):
            return v
    return []


def _unwrap_hist_msg(m: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], bool, Optional[int]]:
    """(waE2E message dict, from_me, timestamp) de um item de histórico."""
    inner = m.get("Message") or m.get("message") or m
    if isinstance(inner, dict) and (inner.get("message") or inner.get("Message")):
        # WebMessageInfo: {key:{fromMe}, message:{...}, messageTimestamp}
        key = inner.get("key") or inner.get("Key") or {}
        from_me = bool(key.get("fromMe") or key.get("FromMe"))
        ts = inner.get("messageTimestamp") or inner.get("MessageTimestamp")
        try:
            ts = int(ts) if ts is not None else None
        except (TypeError, ValueError):
            ts = None
        msg = inner.get("message") or inner.get("Message")
        return (msg if isinstance(msg, dict) else None), from_me, ts
    return None, False, None


async def ingest_history_sync(integration: dict, body: dict) -> Dict[str, Any]:
    """Processa um evento HistorySync → observed_events (recência-primeiro).
    Retorna {conversations, insurer_conversations, events_stored}."""
    from app.services.atlas.observer_intake import (
        _br_variants, _extract_content, _observer_number_of, insurer_allowlist,
    )

    data = body.get("data") if isinstance(body.get("data"), dict) else {}

    # guarda o 1º payload bruto p/ inspeção (uma vez; TTL 7d) — sem PII em log
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        if not await r.get("atlas:history_sync:raw_sample"):
            await r.set("atlas:history_sync:raw_sample", json.dumps(body, default=str)[:200000], ex=7 * 86400)
    except Exception:  # noqa: BLE001
        pass

    convs = _find_conversations(data) or _find_conversations(body)
    if not convs:
        logger.info("[ATLAS HISTORY] sync sem conversas reconhecíveis (só estrutura)")
        return {"conversations": 0, "insurer_conversations": 0, "events_stored": 0}

    allow = insurer_allowlist()
    observer_number = _observer_number_of(integration)
    company_id = str(integration.get("company_id") or "")


    # SPEC-040 Onda 1: escopo da integração decide se as conversas com os
    # SEGURADOS entram no Espelho de Atendimento (Parte 1) ou são descartadas.
    try:
        from app.services.atlas.attendance_capture import SCOPE_FULL, observer_scope

        capture_clients = observer_scope(integration) == SCOPE_FULL
    except Exception:  # noqa: BLE001 — Espelho nunca bloqueia a ingestão do Atlas
        capture_clients = False

    # (a) resolve seguradora por conversa; (b) segurado → Espelho (se escopo);
    # (c) descarta o resto na borda (grupos/status: sempre fora)
    insurer_convs: List[Tuple[str, str, List[Dict[str, Any]]]] = []
    client_convs: List[Tuple[str, List[Dict[str, Any]]]] = []
    for conv in convs:
        jid = _conv_jid(conv)
        if not jid or jid.endswith(("@g.us", "@broadcast", "@newsletter")):
            continue
        counterparty = "".join(ch for ch in jid.split("@", 1)[0].split(":", 1)[0] if ch.isdigit())
        insurer_key = None
        for v in _br_variants(counterparty):
            if v in allow:
                insurer_key = allow[v]
                break
        if insurer_key:
            insurer_convs.append((insurer_key, counterparty, _conv_messages(conv)))
        elif capture_clients and counterparty:
            client_convs.append((counterparty, _conv_messages(conv)))

    # RECÊNCIA: ordena as conversas pela mensagem mais recente (desc)
    def _conv_latest_ts(msgs: List[Dict[str, Any]]) -> int:
        best = 0
        for m in msgs:
            _, _, ts = _unwrap_hist_msg(m)
            if ts and ts > best:
                best = ts
        return best

    insurer_convs.sort(key=lambda c: _conv_latest_ts(c[2]), reverse=True)

    stored = 0
    for insurer_key, counterparty, msgs in insurer_convs:
        stored += await _ingest_conversation(
            company_id, observer_number, counterparty, insurer_key, msgs,
            events_table="observed_events", sessions_table="observed_sessions",
            integration_id=str(integration.get("id") or ""))

    # SPEC-040 Onda 1 — Parte 1 (segurados) → Espelho de Atendimento.
    # Recência-primeiro também aqui; cap de segurança p/ históricos gigantes.
    client_stored = 0
    if client_convs:
        try:
            max_events = int(os.getenv("ATTENDANCE_HISTORY_MAX_EVENTS", "50000"))
        except ValueError:
            max_events = 50000
        client_convs.sort(key=lambda c: _conv_latest_ts(c[1]), reverse=True)
        for counterparty, msgs in client_convs:
            if client_stored >= max_events:
                logger.warning(f"[ESPELHO ATENDIMENTO] cap de histórico atingido ({max_events})")
                break
            client_stored += await _ingest_conversation(
                company_id, observer_number, counterparty, None, msgs,
                events_table="attendance_transcripts", sessions_table="attendance_sessions",
                integration_id=str(integration.get("id") or ""))
        try:
            from app.core.heartbeat import beat

            await beat("espelho_atendimento", client_stored)
        except Exception:  # noqa: BLE001
            pass

    # pulso do Observador (histórico também é observação)
    try:
        from app.core.heartbeat import beat

        await beat("observador", stored)
    except Exception:  # noqa: BLE001
        pass
    logger.info(
        f"[ATLAS HISTORY] {len(convs)} conversas, {len(insurer_convs)} de seguradora "
        f"({stored} eventos), {len(client_convs)} de segurado ({client_stored} eventos)")
    return {"conversations": len(convs), "insurer_conversations": len(insurer_convs),
            "events_stored": stored, "client_conversations": len(client_convs),
            "client_events_stored": client_stored}


_SESSION_GAP_S = 2 * 3600


def _history_message_id(counterparty: str, ts: Optional[int], i: int, from_me: bool,
                        msg_type: str, text: Optional[str], ident: str = "") -> str:
    """A identidade de uma mensagem histórica. A MESMA mensagem tem de gerar o
    MESMO id em qualquer execução.

    O id anterior terminava em `abs(hash(texto[:60])) % 10**7`. `hash()` de
    string em Python é **aleatorizado a cada processo** (PYTHONHASHSEED): a
    mesma mensagem ganhava um id novo a cada reimportação, e o
    `on_conflict="observer_number,message_id"` — que existe justamente para
    isso — nunca disparava.

    Medido em 28/07/2026: a Allianz tinha 14.203 linhas para 5.330 mensagens
    reais (2,66x), com os três history_sync do dia às 14:01, 15:02 e 15:43
    gravando cópias. Não era o WhatsApp mandando de novo — era o id.

    O estrago não era só custo. O Tecelão casa cada tela com a resposta que vem
    LOGO DEPOIS; com as cópias intercaladas, a sequência vira tela-tela-tela-
    resposta e a escolha se perde. Nas telas de lista e botão da Porto, 70%
    ficaram sem resposta casada.

    Entram na identidade também a direção e o tipo: a mesma palavra ("Ok") pode
    ser dita pelos dois lados no mesmo segundo, e são duas mensagens.

    E entra o **ID DO CLIQUE**, quando existe.

    📊 Medido em 03/08/2026: 937 dos 947 cliques de botão do histórico tinham
    `text` vazio — o extrator não conhecia a grafia `selectedButtonID`. Com o
    texto vazio, dois cliques DIFERENTES no mesmo segundo produziam a MESMA
    identidade, e o `ignore_duplicates=True` do upsert descartava o segundo em
    silêncio: o defeito de leitura virava perda de linha. Que segundos com
    mensagens distintas existem neste histórico está medido — 367 grupos
    (counterparty, segundo, direção, tipo) com textos diferentes, 738 linhas.

    Só muda o id de quem TEM interativo: 947 button_reply, 633 list_reply e 23
    flow_reply. Mensagem de texto não tem `ident`, mantém o id de sempre, e a
    reingestão continua deduplicando as 13.659 sem criar cópia.

    O índice `i` continua fora quando há timestamp, e continua de propósito: ele
    depende da ORDEM em que o WhatsApp mandou as mensagens, que muda entre
    syncs — era assim que nascia a duplicação de 2,66x.
    """
    # O trecho do id SÓ é acrescentado quando existe. Um `|` a mais no fim, com
    # `ident` vazio, mudaria o hash de TODA mensagem de texto — 13.659 delas — e
    # a próxima sincronização gravaria uma cópia de cada uma. É a diferença
    # entre reingerir 1.603 linhas de propósito e 15.262 por descuido.
    corpo = (f"{from_me}|{msg_type}|{text or ''}" + (f"|{ident}" if ident else "")
             ).encode("utf-8", "replace")
    marca = hashlib.sha1(corpo).hexdigest()[:12]
    return f"hist-{counterparty}-{ts or f'i{i}'}-{marca}"


async def _ingest_conversation(company_id: str, observer_number: str, counterparty: str,
                               insurer_key: Optional[str], msgs: List[Dict[str, Any]],
                               events_table: str, sessions_table: str,
                               integration_id: str = "") -> int:
    """Uma conversa do histórico → sessões por janela de 2h + eventos dedupe.
    Mesma mecânica p/ seguradora (Atlas) e segurado (Espelho de Atendimento)."""
    from app.services.atlas.observer_intake import _extract_content

    ordered = sorted(
        ((*_unwrap_hist_msg(m), i) for i, m in enumerate(msgs)),
        key=lambda x: (x[2] or 0),
    )
    bursts: List[List[tuple]] = []
    last_ts = None
    for msg, from_me, ts, i in ordered:
        if not isinstance(msg, dict):
            continue
        if last_ts is not None and ts and (ts - last_ts) > _SESSION_GAP_S:
            bursts.append([])
        if not bursts:
            bursts.append([])
        bursts[-1].append((msg, from_me, ts, i))
        last_ts = ts or last_ts

    stored = 0
    for burst in bursts:
        if not burst:
            continue
        first_ts = next((b[2] for b in burst if b[2]), None)
        last_bts = next((b[2] for b in reversed(burst) if b[2]), first_ts)
        session_id = await _ensure_history_session(
            company_id, observer_number, counterparty, insurer_key, first_ts, last_bts,
            sessions_table=sessions_table)
        for msg, from_me, ts, i in burst:
            msg_type, text, interactive, media_meta = _extract_content(msg)
            if not text and not media_meta and not interactive:
                continue
            wa_ts = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else None
            mid = _history_message_id(counterparty, ts, i, from_me, msg_type, text,
                                      str((interactive or {}).get("id") or ""))
            record = {
                "company_id": company_id, "observer_number": observer_number,
                "counterparty": counterparty, "insurer_key": insurer_key,
                "direction": "out" if from_me else "in", "msg_type": msg_type,
                "text": (text or None),
                "interactive": (dict(interactive) if interactive else None),
                "media_meta": media_meta or None, "message_id": mid,
                "wa_timestamp": wa_ts, "source": "history_sync", "session_id": session_id,
            }
            try:
                await _store_history_event(record, events_table=events_table)
                stored += 1
            except Exception:  # noqa: BLE001
                pass

            # A MÍDIA ANTIGA SÓ EXISTE AQUI, NESTE INSTANTE.
            #
            # `/message/downloadmedia` do Evolution GO exige o `waE2E.Message`
            # inteiro — `mediaKey`, `directPath`, `fileEncSha256`. Nada disso é
            # gravado no banco: `media_meta` guarda tipo, nome e legenda. Uma
            # foto do histórico, depois que esta função retorna, é
            # inalcançável para sempre.
            #
            # São 9.002 mídias no Espelho (3.572 documentos, 2.685 imagens,
            # 2.631 áudios, 114 vídeos), nenhuma lida. Em seguro o áudio é
            # onde o cliente explica o sinistro e o documento é a apólice.
            #
            # FECHADO POR PADRÃO. `limite_midia` vem do Founder por chamada:
            # a instrução de 28/07/2026 foi explícita — "NÃO FAÇA A ANÁLISE
            # DAS 9565 MÍDIAS VIA API NUNCA. APENAS AS 20". Zero significa
            # zero: nenhuma transcrição é disparada sem alguém pedir.
            # Sem `if` de orçamento aqui: quem decide é `enqueue_observer_media`,
            # o portão único. Checar nos dois lugares gastaria dois créditos
            # por mídia e o teto de 20 viraria 10.
            if media_meta:
                try:
                    from app.services.atlas.observer_media import enqueue_observer_media

                    await enqueue_observer_media(
                        {"id": integration_id, "company_id": company_id},
                        events_table, msg, record)
                except Exception as exc:  # noqa: BLE001 — mídia nunca derruba a ingestão
                    logger.warning("[HISTORY] fila de mídia indisponível: %s", type(exc).__name__)
    return stored


def _ensure_history_session_sync(company_id: str, observer_number: str, counterparty: str,
                                 insurer_key: Optional[str], first_ts: Optional[int],
                                 last_ts: Optional[int],
                                 sessions_table: str = "observed_sessions") -> Optional[str]:
    """Cria (idempotente) uma sessão para uma janela histórica. Chave lógica:
    (observer, counterparty, first_ts) — reingestão reusa a mesma sessão."""
    from app.core.database import get_supabase_client

    supabase = get_supabase_client()
    started = datetime.fromtimestamp(first_ts, tz=timezone.utc).isoformat() if first_ts else \
        datetime.now(timezone.utc).isoformat()
    last = datetime.fromtimestamp(last_ts, tz=timezone.utc).isoformat() if last_ts else started
    marker = f"hist:{observer_number}:{counterparty}:{first_ts or 0}"
    try:
        existing = (supabase.client.table(sessions_table).select("id")
                    .eq("observer_number", observer_number).eq("counterparty", counterparty)
                    .eq("started_at", started).limit(1).execute())
        if existing.data:
            return existing.data[0]["id"]
        created = supabase.client.table(sessions_table).insert({
            "company_id": company_id, "observer_number": observer_number,
            "counterparty": counterparty, "insurer_key": insurer_key,
            "started_at": started, "last_event_at": last, "status": "closed",
            "summary": {"source": "history_sync", "marker": marker},
        }).execute()
        return created.data[0]["id"] if created.data else None
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ATLAS HISTORY] sessão falhou: {type(e).__name__}")
        return None


async def _ensure_history_session(company_id: str, observer_number: str, counterparty: str,
                                  insurer_key: Optional[str], first_ts: Optional[int],
                                  last_ts: Optional[int],
                                  sessions_table: str = "observed_sessions") -> Optional[str]:
    return await asyncio.to_thread(_ensure_history_session_sync, company_id, observer_number,
                                   counterparty, insurer_key, first_ts, last_ts, sessions_table)


def _store_history_event_sync(record: Dict[str, Any], events_table: str = "observed_events") -> None:
    from app.core.database import get_supabase_client

    supabase = get_supabase_client()
    # dedupe por (observer_number, message_id) — reingestão não duplica
    supabase.client.table(events_table).upsert(
        record, on_conflict="observer_number,message_id", ignore_duplicates=True
    ).execute()


async def _store_history_event(record: Dict[str, Any], events_table: str = "observed_events") -> None:
    await asyncio.to_thread(_store_history_event_sync, record, events_table)
