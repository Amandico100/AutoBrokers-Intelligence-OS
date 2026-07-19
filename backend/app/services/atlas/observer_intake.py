"""SPEC-038 ATLAS — Observador: captura passiva (Bloco A).

Princípios INEGOCIÁVEIS (decisões do founder 18/07):
1. MUDO POR CONSTRUÇÃO: este módulo NÃO importa nenhum cliente de envio.
   Não existe caminho de resposta — é ausência de código, não uma flag.
2. FILTRO DE BORDA: só conversas com números de SEGURADORA (registry + envs
   INSURER_CONTACT_*) são processadas. Qualquer outra conversa (amigos, grupos,
   status) é DESCARTADA na primeira linha — sem armazenar, sem logar conteúdo;
   apenas contadores agregados no Redis.
3. Dois modos:
   - purpose="observer"  → consome o evento (integração dedicada, ex.: celular
     de atendente humana). Resposta do webhook e FIM.
   - purpose="attendance" → TAP: captura o que for de seguradora e devolve None
     para o pipeline normal seguir intacto (Even/dispatch/cartógrafo).
4. Mídia: só METADADOS (mimetype/filename/kind) — nunca bytes/base64.
5. fromMe (o que o humano digitou/clicou) é o LADO DE OURO: para direction=out
   guardamos também o payload bruto da mensagem (cap 50KB) — é a referência
   real de cliques de lista/botão e, um dia, do nfm_reply do app nativo.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Set, Tuple

logger = logging.getLogger(__name__)

_SESSION_GAP = timedelta(hours=2)
_RAW_CAP_BYTES = 50_000


# ------------------------------------------------------------------ #
# Filtro de borda — allowlist de números de seguradora
# ------------------------------------------------------------------ #
def _digits(value: Any) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _br_variants(number: str) -> Set[str]:
    """Variantes com/sem o nono dígito (mesma regra do channel_security)."""
    d = _digits(number)
    if not d:
        return set()
    forms = {d}
    if d.startswith("55"):
        rest = d[2:]
        if len(rest) == 11 and rest[2] == "9":
            forms.add("55" + rest[:2] + rest[3:])
        elif len(rest) == 10:
            forms.add("55" + rest[:2] + "9" + rest[2:])
    return forms


def insurer_allowlist() -> Dict[str, str]:
    """{variante_de_numero: insurer_key} — registry (ativo+alternativo) + envs
    INSURER_CONTACT_{KEY}_ASSISTENCIA (env tem prioridade na atribuição)."""
    from app.services.insurer_registry import INSURER_REGISTRY

    mapping: Dict[str, str] = {}
    for key, info in INSURER_REGISTRY.items():
        for field in ("whatsapp", "whatsapp_alternativo"):
            for v in _br_variants(str(info.get(field) or "")):
                mapping.setdefault(v, key)
    for env_key, env_val in os.environ.items():
        if env_key.startswith("INSURER_CONTACT_") and env_val.strip():
            key = env_key.removeprefix("INSURER_CONTACT_").removesuffix("_ASSISTENCIA")
            key = key.removesuffix("_ASSISTENCIA_24H").lower().split("_")[0]
            for v in _br_variants(env_val):
                mapping[v] = key
    return mapping


async def _beat() -> None:
    """Pulso do Observador na Central de Agentes (best-effort)."""
    try:
        from app.core.heartbeat import beat

        await beat("observador", 1)
    except Exception:  # noqa: BLE001
        pass


async def _count_drop(observer_number: str, reason: str) -> None:
    """Contador agregado de descartes — NUNCA conteúdo (privacidade)."""
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        await r.hincrby(f"atlas:drops:{_digits(observer_number)}", reason, 1)
    except Exception:  # noqa: BLE001
        pass


# ------------------------------------------------------------------ #
# Extração da mensagem (reusa o parser canônico do inbound)
# ------------------------------------------------------------------ #
def _extract_content(message: Dict[str, Any]) -> Tuple[str, Optional[str], Optional[Dict], Optional[Dict]]:
    """(msg_type, text, interactive, media_meta) a partir do dict waE2E."""
    from app.services.whatsapp.evolution_inbound import _interactive_from_message, _unwrap_message

    msg = _unwrap_message(message if isinstance(message, dict) else {})
    text = msg.get("conversation") or (msg.get("extendedTextMessage") or {}).get("text")
    if text:
        return "text", str(text), None, None

    rendered = _interactive_from_message(msg)
    if rendered:
        r_text, meta = rendered
        kind = str((meta or {}).get("kind") or "interactive")
        return kind, r_text, meta, None

    for media_key, kind in (("imageMessage", "image"), ("documentMessage", "document"),
                            ("documentWithCaptionMessage", "document"), ("audioMessage", "audio"),
                            ("videoMessage", "video"), ("stickerMessage", "sticker")):
        m = msg.get(media_key)
        if media_key == "documentWithCaptionMessage" and isinstance(m, dict):
            m = ((m.get("message") or {}).get("documentMessage")) or m
        if isinstance(m, dict):
            meta = {"kind": kind, "mimetype": m.get("mimetype"),
                    "file_name": m.get("fileName") or m.get("title"),
                    "caption": m.get("caption")}
            return kind, str(m.get("caption") or ""), None, meta

    # Respostas estruturadas que o humano ENVIA (clique de lista/botão/flow):
    for resp_key, kind in (("listResponseMessage", "list_reply"),
                           ("buttonsResponseMessage", "button_reply"),
                           ("templateButtonReplyMessage", "button_reply"),
                           ("interactiveResponseMessage", "flow_reply")):
        m = msg.get(resp_key)
        if isinstance(m, dict):
            title = (m.get("title") or (m.get("singleSelectReply") or {}).get("selectedRowId")
                     or (m.get("selectedDisplayText")) or "")
            return kind, str(title), {"kind": kind, "raw_keys": sorted(m.keys())}, None

    return "unknown", None, None, None


def _raw_capped(message: Any) -> Optional[Dict[str, Any]]:
    try:
        blob = json.dumps(message, ensure_ascii=False, default=str)
        if len(blob.encode("utf-8")) > _RAW_CAP_BYTES:
            return {"_truncated": True, "keys": sorted(message.keys()) if isinstance(message, dict) else []}
        return message if isinstance(message, dict) else None
    except Exception:  # noqa: BLE001
        return None


# ------------------------------------------------------------------ #
# Persistência (supabase service-role; sessão por janela de 2h)
# ------------------------------------------------------------------ #
_CLICK_WINDOW_S = 180  # clique chega segundos após a tela; 3 min é folga segura


def _parse_native_form(extra: Any) -> Optional[Dict[str, Any]]:
    """Extrai do native_flow_response (galaxy_message) o SCHEMA do formulário
    (telas, perguntas) + as RESPOSTAS do humano — a referência p/ replicar por
    código. flow_token é volátil (não guardar); guardamos flow_id/name + campos.
    Sem PII de cliente (são respostas situacionais: "em garagem? 1")."""
    try:
        if not isinstance(extra, dict):
            return None
        raw = extra.get("paramsJSON")
        if not raw:
            return None
        params = json.loads(raw) if isinstance(raw, str) else raw
        wa = params.get("wa_flow_response_params") or {}
        # respostas do humano = todo rb_/ckb_/txt_ do params (fora os meta)
        answers = {k: v for k, v in params.items()
                   if k not in ("flow_token", "wa_flow_response_params") and not k.startswith("_")}
        schema = None
        rm = wa.get("response_message")
        if isinstance(rm, str):
            try:
                schema = json.loads(rm)
            except Exception:  # noqa: BLE001
                schema = None
        fields = []
        for scr in ((schema or {}).get("screens") or []):
            for comp in scr.get("components") or []:
                name = comp.get("name")
                if name:
                    fields.append({"screen": scr.get("title"), "name": name,
                                   "label": comp.get("label"), "answer": answers.get(name)})
        return {
            "flow_id": wa.get("flow_id"),
            "flow_name": wa.get("flow_name") or wa.get("title"),
            "fields": fields or [{"name": k, "answer": v} for k, v in answers.items()],
            "answers": answers,
        }
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ATLAS] parse native form falhou: {type(e).__name__}")
        return None


def _observer_number_of(integration: dict) -> str:
    """Identidade do número observado — MESMA computação em captura e correlação
    (fix 18/07: identifier pode ser o NOME da instância → dígitos vazios)."""
    return _digits((integration or {}).get("identifier") or (integration or {}).get("instance_id") or "") or "unknown"


def _correlate_open_session(observer_number: str, company_id: str = ""):
    """Fallback p/ ButtonClick sem chat (bug do GO): a sessão de seguradora
    ABERTA com atividade nos últimos 3 min. Duas ativas na janela = ambíguo →
    None (privacidade > completude). Retorna (session_id, counterparty, insurer_key)."""
    try:
        from app.core.database import get_supabase_client

        supabase = get_supabase_client()
        q = (supabase.client.table("observed_sessions")
             .select("id, counterparty, insurer_key, last_event_at")
             .eq("observer_number", observer_number).eq("status", "open"))
        if company_id:
            q = q.eq("company_id", company_id)
        res = q.order("last_event_at", desc=True).limit(2).execute()
        rows = res.data or []

        def _fresh(row) -> bool:
            try:
                last = datetime.fromisoformat(str(row["last_event_at"]).replace("Z", "+00:00"))
                return (datetime.now(timezone.utc) - last).total_seconds() <= _CLICK_WINDOW_S
            except ValueError:
                return False

        fresh = [r for r in rows if _fresh(r)]
        if len(fresh) == 1 and fresh[0].get("insurer_key"):
            r = fresh[0]
            return r["id"], str(r.get("counterparty") or ""), str(r["insurer_key"])
        return None
    except Exception:  # noqa: BLE001
        return None


def _store_event_sync(record: Dict[str, Any]) -> None:
    from app.core.database import get_supabase_client

    supabase = get_supabase_client()
    obs, cp = record["observer_number"], record["counterparty"]
    now_iso = datetime.now(timezone.utc).isoformat()

    # Sessão pré-atribuída (correlação do ButtonClick): só atualiza o relógio.
    if record.get("session_id"):
        try:
            supabase.client.table("observed_sessions").update(
                {"last_event_at": now_iso}).eq("id", record["session_id"]).execute()
            supabase.client.table("observed_events").upsert(
                record, on_conflict="observer_number,message_id", ignore_duplicates=True
            ).execute()
        except Exception as e:  # noqa: BLE001
            logger.error(f"[ATLAS] evento (sessão pré-atribuída) não gravado: {type(e).__name__}")
        return

    session_id = None
    try:
        res = (supabase.client.table("observed_sessions").select("id, last_event_at")
               .eq("observer_number", obs).eq("counterparty", cp)
               .eq("status", "open").order("last_event_at", desc=True).limit(1).execute())
        if res.data:
            last = res.data[0]
            try:
                last_at = datetime.fromisoformat(str(last["last_event_at"]).replace("Z", "+00:00"))
            except ValueError:
                last_at = datetime.now(timezone.utc)
            if datetime.now(timezone.utc) - last_at <= _SESSION_GAP:
                session_id = last["id"]
                supabase.client.table("observed_sessions").update(
                    {"last_event_at": now_iso}).eq("id", session_id).execute()
            else:
                supabase.client.table("observed_sessions").update(
                    {"status": "closed"}).eq("id", last["id"]).execute()
        if session_id is None:
            created = supabase.client.table("observed_sessions").insert({
                "company_id": record["company_id"], "observer_number": obs,
                "counterparty": cp, "insurer_key": record.get("insurer_key"),
                "started_at": now_iso, "last_event_at": now_iso, "status": "open",
            }).execute()
            session_id = created.data[0]["id"] if created.data else None
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ATLAS] sessão falhou (evento segue sem sessão): {type(e).__name__}")

    record["session_id"] = session_id
    try:
        supabase.client.table("observed_events").upsert(
            record, on_conflict="observer_number,message_id", ignore_duplicates=True
        ).execute()
    except Exception:  # noqa: BLE001
        # fallback: insert simples (índice único ainda protege contra dupe)
        try:
            supabase.client.table("observed_events").insert(record).execute()
        except Exception as e2:  # noqa: BLE001
            logger.error(f"[ATLAS] evento NÃO gravado: {type(e2).__name__}")


# ------------------------------------------------------------------ #
# Entrada principal — chamada pelo webhook evolution-go
# ------------------------------------------------------------------ #
async def observer_tap(integration: dict, body: dict) -> Optional[dict]:
    """Captura passiva. Retorna dict (resposta ao webhook) quando a integração é
    purpose='observer' (consome SEMPRE); retorna None em modo TAP (attendance)
    para o pipeline normal seguir. NUNCA envia nada — por construção."""
    purpose = str((integration or {}).get("purpose") or "").strip().lower()
    is_observer = purpose == "observer"
    consumed = {"status": "observed"} if is_observer else None

    try:
        ev_name = str((body or {}).get("event") or "").strip().lower().replace("_", ".")

        # HISTORY SYNC (D2): shape ainda não confirmado ao vivo — NUNCA armazenar
        # conteúdo sem entender; só a ESTRUTURA (chaves/contagens) p/ o relatório.
        if ev_name in ("historysync", "history.sync"):
            data = body.get("data") if isinstance(body.get("data"), dict) else {}
            structure = {k: (len(v) if isinstance(v, list) else type(v).__name__)
                         for k, v in list(data.items())[:20]}
            logger.info(f"[ATLAS] HISTORY_SYNC recebido — estrutura: {json.dumps(structure, default=str)[:400]}")
            try:
                from app.core.redis import get_async_redis_client

                r = await get_async_redis_client()
                await r.set("atlas:history_sync:last_structure",
                            json.dumps(structure, default=str), ex=7 * 24 * 3600)
                await r.hincrby("atlas:history_sync:count", "events", 1)
            except Exception:  # noqa: BLE001
                pass
            # INGESTÃO REAL (pré-requisito de segunda): converte o histórico em
            # rotas, recência-primeiro, só de seguradoras. Nunca derruba o webhook.
            try:
                from app.services.atlas.history_ingest import ingest_history_sync

                res = await ingest_history_sync(integration, body if isinstance(body, dict) else {})
                logger.info(f"[ATLAS] history ingest: {res}")
            except Exception as e:  # noqa: BLE001
                logger.error(f"[ATLAS] history ingest falhou: {type(e).__name__}")
            return consumed or {"status": "observed", "event": "history_sync"}

        if ev_name in ("connection", "connection.update"):
            return consumed if is_observer else None

        # BUTTONCLICK (SPEC-038 — o LADO DE OURO): o GO emite um evento próprio
        # quando o humano CLICA num botão/lista OU preenche o FORMULÁRIO NATIVO
        # (InteractiveResponseMessage/NativeFlow — a travessia do app HDI/Yelum!).
        # AUDITORIA FABLE 18/07: no fonte do GO, chat/jid/phone/messageId são
        # lidos de um dataMap ANINHADO (chegam NULOS). Só buttonId/buttonText/
        # type/timestamp vêm preenchidos. Resolução do destinatário: (1) chat se
        # vier; (2) CORRELAÇÃO com a sessão de seguradora ABERTA nos últimos
        # 3 min (o clique chega segundos após a tela da URA). Ambíguo = descarta
        # com contador (privacidade > completude). Consome SEMPRE (o pipeline
        # normal não conhece ButtonClick — evita log de payload desconhecido).
        if ev_name in ("buttonclick", "button.click"):
            data = body.get("data") if isinstance(body.get("data"), dict) else {}
            observer_number = _observer_number_of(integration)
            always = consumed or {"status": "observed", "event": "button_click"}

            insurer_key = None
            counterparty = ""
            session_id = None
            chat = str(data.get("chat") or data.get("jid") or data.get("phone") or "")
            if chat:
                if chat.endswith(("@g.us", "@broadcast", "@newsletter")):
                    await _count_drop(observer_number, "group_or_status")
                    return always
                counterparty = _digits(chat.split("@", 1)[0].split(":", 1)[0])
                allow = insurer_allowlist()
                for v in _br_variants(counterparty):
                    if v in allow:
                        insurer_key = allow[v]
                        break
            if not insurer_key:
                # Fallback: sessão de seguradora ativa na janela (bug do GO: chat nulo)
                corr = await asyncio.to_thread(_correlate_open_session, observer_number,
                                               str(integration.get("company_id") or ""))
                if corr:
                    session_id, counterparty, insurer_key = corr
            if not insurer_key:
                await _count_drop(observer_number, "buttonclick_unresolved")
                return always

            btype = str(data.get("type") or "button_reply")
            kind = "flow_reply" if "interactive" in btype or "nativeflow" in btype.replace("_", "") else \
                   "list_reply" if "list" in btype else "button_reply"
            ts = data.get("timestamp")
            wa_ts = None
            if isinstance(ts, (int, float)) and ts > 0:
                wa_ts = datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
            btn_text = str(data.get("buttonText") or "").strip()
            native_form = None
            if kind == "flow_reply":
                # PEDRA DE ROSETA (app nativo HDI/Yelum): extrai o schema do
                # formulário e as respostas do humano — ensina a Even a atravessar.
                native_form = _parse_native_form(data.get("extraData"))
                if native_form:
                    btn_text = f"[APP NATIVO] {native_form.get('flow_name') or 'formulário preenchido'}"
            # messageId vem nulo (bug do GO): id determinístico p/ dedupe
            msg_id = str(data.get("messageId") or "") or \
                f"bc-{_digits(str(ts))}-{abs(hash((btn_text, str(data.get('buttonId')))))%10**8}"
            record = {
                "company_id": str(integration.get("company_id") or ""),
                "observer_number": observer_number or "unknown",
                "counterparty": counterparty or "unknown",
                "insurer_key": insurer_key,
                "direction": "out",  # é a escolha do humano
                "msg_type": kind,
                "text": btn_text or None,
                "interactive": {"kind": kind, "id": data.get("buttonId"),
                                "title": btn_text, "go_type": btype,
                                "native_form": native_form,
                                "extra": data.get("extraData") if not native_form else None},
                "media_meta": None,
                "message_id": msg_id,
                "wa_timestamp": wa_ts,
                "source": "live",
            }
            if session_id:
                record["session_id"] = session_id
            await asyncio.to_thread(_store_event_sync, record)
            await _beat()
            logger.info(f"[ATLAS] CLIQUE humano {insurer_key} '{btn_text}' ({kind})")
            return always

        from app.services.whatsapp.providers.evolution_go import go_event_to_v2_envelope

        env = go_event_to_v2_envelope(body if isinstance(body, dict) else {})
        if env.get("event") != "messages.upsert":
            return consumed if is_observer else None
        data = env.get("data") or {}
        key = data.get("key") or {}
        message = data.get("message")
        if not isinstance(message, dict):
            return consumed if is_observer else None

        remote = str(key.get("remoteJid") or "")
        observer_number = _observer_number_of(integration)

        # ---------- FILTRO DE BORDA (privacidade — primeira linha) ----------
        if remote.endswith(("@g.us", "@broadcast", "@newsletter", "@call")):
            await _count_drop(observer_number, "group_or_status")
            return consumed if is_observer else None
        counterparty = _digits(remote.split("@", 1)[0].split(":", 1)[0])
        allow = insurer_allowlist()
        insurer_key = None
        for v in _br_variants(counterparty):
            if v in allow:
                insurer_key = allow[v]
                break
        if not insurer_key:
            await _count_drop(observer_number, "non_insurer")
            return consumed if is_observer else None
        # --------------------------------------------------------------------

        from_me = bool(key.get("fromMe"))
        msg_type, text, interactive, media_meta = _extract_content(message)
        if from_me:
            raw = _raw_capped(message)
            interactive = dict(interactive or {})
            if raw is not None:
                interactive["raw_out"] = raw  # o clique/resposta REAL do humano

        ts = data.get("messageTimestamp")
        wa_ts = None
        if isinstance(ts, (int, float)) and ts > 0:
            wa_ts = datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()

        record = {
            "company_id": str(integration.get("company_id") or ""),
            "observer_number": observer_number or "unknown",
            "counterparty": counterparty,
            "insurer_key": insurer_key,
            "direction": "out" if from_me else "in",
            "msg_type": msg_type,
            "text": (text or None),
            "interactive": interactive or None,
            "media_meta": media_meta or None,
            "message_id": str(key.get("id") or "") or None,
            "wa_timestamp": wa_ts,
            "source": "live",
        }
        await asyncio.to_thread(_store_event_sync, record)
        await _beat()
        logger.info(f"[ATLAS] observado {record['direction']} {insurer_key} tipo={msg_type}")
    except Exception as e:  # noqa: BLE001 — o TAP JAMAIS derruba o pipeline
        logger.error(f"[ATLAS] observer tap falhou: {type(e).__name__}")

    return consumed
