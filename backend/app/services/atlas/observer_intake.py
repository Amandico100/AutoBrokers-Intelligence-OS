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

# O que permite buscar e descriptografar uma mídia no WhatsApp.
#
# Fica numa constante só, e não espalhado em literais, porque a lista tem dois
# usos que precisam andar juntos: quem GRAVA (a captura, logo abaixo) e quem
# ESCONDE (`sem_coordenadas`, usado por toda leitura que sai do backend).
# Separadas, acrescentar uma chave nova no gravador e esquecer do escondedor
# publicaria um segredo — e é exatamente o tipo de esquecimento que ninguém
# percebe, porque o dado continua funcionando.
COORDENADAS_DE_MIDIA = ("directPath", "mediaKey", "fileEncSha256", "fileSha256",
                        "mediaKeyTimestamp", "url")


def sem_coordenadas(meta: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Troca as coordenadas de download por presença/ausência.

    `mediaKey` é chave de descriptografia. Ela precisa existir no banco para a
    mídia ser recuperável, e não pode aparecer em resposta de API, log ou
    relatório — CLAUDE.md §13.3: mostrar presença, nunca o valor.
    """
    if not isinstance(meta, dict):
        return meta
    limpo = {k: v for k, v in meta.items() if k not in COORDENADAS_DE_MIDIA}
    achadas = [k for k in COORDENADAS_DE_MIDIA if meta.get(k) not in (None, "")]
    if achadas:
        limpo["download"] = "recuperavel"
    elif str(meta.get("kind") or "") in ("audio", "image", "video", "document"):
        limpo["download"] = "sem coordenadas"
    return limpo

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
# O CLIQUE DO HUMANO — extração tolerante à grafia
# ------------------------------------------------------------------ #
# 📊 Medido em 03/08/2026 (`observed_events`, projeto de produção
# `dcajcvlzcjbmyapmklil`): dos 947 cliques de botão vindos do histórico, 937
# chegaram na forma ["Response", "contextInfo", "selectedButtonID", "type"] e o
# extrator procurava exatamente `title`, `singleSelectReply.selectedRowId` e
# `selectedDisplayText` — nenhuma das três está aí. **98,9% dos cliques de botão
# da corretora foram apagados na leitura.** Os 23 `flow_reply`
# (["InteractiveResponseMessage", "body", "contextInfo"]) também, porque
# ninguém olhava `body`.
#
# P-56 — a busca tolerante que resolveu isso MUDOU DE CASA: mora em
# `app/services/whatsapp/evolution_inbound.py`, o parser canônico de mensagem
# do WhatsApp, que este módulo já importa. O motivo é que o MESMO defeito
# estava vivo lá (`_text_from_message` lia `selectedButtonId`, d minúsculo) e
# aprender uma grafia nova em dois arquivos separados é como o segundo deles
# fica para trás — foi assim que este durou três semanas a mais que o primeiro.
#
# O que continua sendo decisão DESTE módulo está logo abaixo, em
# `_extract_content`: o rótulo não se inventa a partir do id, e o id vai para
# `interactive["selected"]`, que é onde o Tecelão procura.


# ------------------------------------------------------------------ #
# Extração da mensagem (reusa o parser canônico do inbound)
# ------------------------------------------------------------------ #
def _extract_content(message: Dict[str, Any]) -> Tuple[str, Optional[str], Optional[Dict], Optional[Dict]]:
    """(msg_type, text, interactive, media_meta) a partir do dict waE2E."""
    from app.services.whatsapp.evolution_inbound import (
        _CHAVES_DE_ID, _CHAVES_DE_ROTULO, _INVOLUCROS_DE_RESPOSTA,
        _interactive_from_message, _niveis_de, _primeiro_valor, _unwrap_message,
    )

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
                    "filename": m.get("fileName") or m.get("title"),
                    "caption": m.get("caption")}
            # DURAÇÃO E TAMANHO — o WhatsApp já manda, e nós jogávamos fora.
            #
            # Sem isso, estimar o custo de transcrever 2.631 áudios virou um
            # palpite entre US$ 7,89 e US$ 31,57: uma diferença de quatro vezes
            # em cima de uma suposição sobre quantos segundos as pessoas falam.
            #
            # Com o número gravado, o custo passa a ser CONTA, e um áudio de
            # doze minutos pode ser reconhecido e recusado antes de virar
            # dinheiro.
            for origem, destino in (("seconds", "segundos"), ("fileLength", "bytes"),
                                    ("pageCount", "paginas")):
                valor = m.get(origem)
                if valor is not None:
                    try:
                        meta[destino] = int(valor)
                    except (TypeError, ValueError):
                        pass

            # AS COORDENADAS DE DOWNLOAD — sem elas a mídia é irrecuperável.
            #
            # Medido em 30/07/2026: 3.653 áudios capturados, ZERO com bytes
            # guardados e ZERO com chave de download. Dentro deles estava o
            # treinamento de emissão de seis seguradoras, que só existe em
            # áudio. Não é material perdido por descuido de ninguém: a captura
            # guardava a FICHA (duração, tamanho, formato) e descartava o que
            # permite buscar o conteúdo.
            #
            # O worker de mídia recebia o payload inteiro pela fila do Redis e
            # funcionava — enquanto a fila existisse. Ela expira em 3 dias.
            # Depois disso, ninguém no sistema sabia mais onde estava o áudio,
            # porque a única cópia das coordenadas era a que tinha evaporado.
            #
            # Guardar aqui torna a mídia recuperável enquanto o WhatsApp a
            # mantiver no servidor, mesmo que a fila caia, o worker falhe ou o
            # processamento só aconteça semanas depois.
            for chave in COORDENADAS_DE_MIDIA:
                valor = m.get(chave)
                if valor not in (None, ""):
                    meta[chave] = valor if isinstance(valor, (str, int)) else str(valor)
            return kind, str(m.get("caption") or ""), None, meta

    # Respostas estruturadas que o humano ENVIA (clique de lista/botão/flow).
    # A chave externa também é procurada normalizada: foi a grafia Go que
    # produziu o defeito, e ela pode chegar no invólucro tanto quanto no miolo.
    normalizadas = {str(k).lower().replace("_", ""): k for k in msg}
    for alvo, kind in _INVOLUCROS_DE_RESPOSTA:
        if alvo not in normalizadas:
            continue
        m = msg.get(normalizadas[alvo])
        if not isinstance(m, dict):
            continue
        niveis = _niveis_de(m)
        rotulo = _primeiro_valor(niveis, _CHAVES_DE_ROTULO)
        ident = _primeiro_valor(niveis, _CHAVES_DE_ID)
        interactive: Dict[str, Any] = {"kind": kind, "raw_keys": sorted(m.keys())}
        if rotulo:
            interactive["title"] = rotulo
        if ident:
            # `id` é o registro. `selected` é ONDE O TECELÃO PROCURA:
            # `weaver._choice_label` lê "title" e depois "selected" — e nada no
            # sistema escrevia "selected". Sem isso, o clique sem rótulo vira
            # aresta "→", e como a chave da aresta é `origem|rótulo`, TODOS os
            # cliques sem rótulo de um mesmo menu colapsam numa aresta só.
            # 📊 03/08/2026: 1.805 das 4.999 arestas dos mapas atuais (36,1%)
            # são exatamente isso — Porto 44,6%, HDI 45,3%, Tokio 63,6%.
            interactive["id"] = ident
            interactive["selected"] = ident
        # RÓTULO NÃO SE INVENTA. Sem texto legível, `text` fica vazio e quem
        # distingue a aresta é o id opaco. Escrever o id no lugar do texto faria
        # o Atlas mostrar `btn_3a9f` ao corretor como se a seguradora tivesse
        # escrito isso — um id não é um rótulo, e mentir aqui é pior que calar.
        return kind, rotulo, interactive, None

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


def _store_event_sync(record: Dict[str, Any], events_table: str = "observed_events",
                      sessions_table: str = "observed_sessions") -> None:
    """Grava evento + sessão por janela de 2h. Parametrizado por tabela (SPEC-040):
    a MESMA mecânica serve o Atlas (observed_*) e o Espelho de Atendimento
    (attendance_*) — lógica única, tabelas isoladas."""
    from app.core.database import get_supabase_client

    supabase = get_supabase_client()
    obs, cp = record["observer_number"], record["counterparty"]
    now_iso = datetime.now(timezone.utc).isoformat()

    # Sessão pré-atribuída (correlação do ButtonClick): só atualiza o relógio.
    if record.get("session_id"):
        try:
            supabase.client.table(sessions_table).update(
                {"last_event_at": now_iso}).eq("id", record["session_id"]).execute()
            supabase.client.table(events_table).upsert(
                record, on_conflict="observer_number,message_id", ignore_duplicates=True
            ).execute()
        except Exception as e:  # noqa: BLE001
            logger.error(f"[ATLAS] evento (sessão pré-atribuída) não gravado: {type(e).__name__}")
        return

    session_id = None
    try:
        res = (supabase.client.table(sessions_table).select("id, last_event_at")
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
                supabase.client.table(sessions_table).update(
                    {"last_event_at": now_iso}).eq("id", session_id).execute()
            else:
                supabase.client.table(sessions_table).update(
                    {"status": "closed"}).eq("id", last["id"]).execute()
        if session_id is None:
            created = supabase.client.table(sessions_table).insert({
                "company_id": record["company_id"], "observer_number": obs,
                "counterparty": cp, "insurer_key": record.get("insurer_key"),
                "started_at": now_iso, "last_event_at": now_iso, "status": "open",
            }).execute()
            session_id = created.data[0]["id"] if created.data else None
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ATLAS] sessão falhou (evento segue sem sessão): {type(e).__name__}")

    record["session_id"] = session_id
    try:
        supabase.client.table(events_table).upsert(
            record, on_conflict="observer_number,message_id", ignore_duplicates=True
        ).execute()
    except Exception:  # noqa: BLE001
        # fallback: insert simples (índice único ainda protege contra dupe)
        try:
            supabase.client.table(events_table).insert(record).execute()
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

    # `is_observer` governa a CAPTURA, e não muda nunca. Esta é a regra do
    # Founder, e ela é absoluta: **o Observador não desliga.** Pareou, observa —
    # com o agente ligado ou desligado, hoje e daqui a um ano.
    is_observer = purpose == "observer"

    # `consumed` governa outra coisa: se o evento PARA aqui.
    #
    # As duas coisas estavam coladas, e isso quebrava o dia em que o Founder
    # liga o agente. O dashboard pareia com `purpose='observer'`; o webhook faz
    # `if _observed is not None: return _observed`. Com as duas grudadas, TODA
    # mensagem morria aqui — inclusive depois de o botão "Ligar agente" ser
    # clicado. O botão viraria verde, a tela diria "Atendendo os segurados", e o
    # agente ficaria mudo para sempre. O pior tipo de defeito: tudo parece
    # certo.
    #
    # Separadas:
    #   agente CALADO   → captura e o evento para aqui (ninguém mais tem o que
    #                     fazer com ele; quem responde é a atendente humana,
    #                     pelo celular).
    #   agente LIGADO   → captura e o evento SEGUE para o pipeline, que entrega
    #                     ao agente. É a promessa da tela: "assume as respostas
    #                     NESTE MESMO número — sem re-parear nada".
    #
    # A pergunta é positiva ("o agente está ligado?") e falha para o lado do
    # silêncio: não conseguir confirmar que está ligado faz o evento parar aqui.
    _agente_ligado = False
    if is_observer:
        try:
            from app.services.atlas.attendance_capture import attendance_agent_active

            _agente_ligado = await attendance_agent_active(
                str((integration or {}).get("company_id") or ""))
        except Exception:  # noqa: BLE001
            _agente_ligado = False
    consumed = {"status": "observed"} if (is_observer and not _agente_ligado) else None

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

        from app.services.whatsapp.evolution_go_events import go_event_to_v2_envelope

        env = go_event_to_v2_envelope(body if isinstance(body, dict) else {})
        if env.get("event") == "connection.update":
            connection = env.get("data") if isinstance(env.get("data"), dict) else {}
            state = str(connection.get("reason") or connection.get("state") or "unknown")
            if is_observer and integration.get("id"):
                def _update_connection() -> None:
                    from app.core.database import get_supabase_client

                    db = get_supabase_client()
                    from app.services.whatsapp.channel_state import normalizar_estado

                    db.client.table("integrations").update({
                        # Vocabulario unico: o Evolution fala "open"/"close" e
                        # as telas leem "connected". Traduzir na escrita e o
                        # que impede o Admin de mostrar `unknown` para um
                        # WhatsApp que esta funcionando.
                        "channel_status": normalizar_estado(state),
                        "last_seen_at": datetime.now(timezone.utc).isoformat(),
                    }).eq("id", integration["id"]).eq(
                        "company_id", integration.get("company_id")
                    ).execute()

                await asyncio.to_thread(_update_connection)
            return consumed if is_observer else None
        if env.get("event") != "messages.upsert":
            return consumed if is_observer else None
        data = env.get("data") or {}
        key = data.get("key") or {}
        message = data.get("message")
        if not isinstance(message, dict):
            return consumed if is_observer else None

        remote = str(key.get("remoteJid") or "")
        remote_alt = str(
            key.get("remoteJidAlt")
            or key.get("remoteJidPn")
            or data.get("remoteJidAlt")
            or data.get("senderAlt")
            or ""
        )
        observer_number = _observer_number_of(integration)

        # ---------- FILTRO DE BORDA (privacidade — primeira linha) ----------
        if remote.endswith(("@g.us", "@broadcast", "@newsletter", "@call")):
            await _count_drop(observer_number, "group_or_status")
            return consumed if is_observer else None
        counterparty_source = remote_alt if remote.endswith("@lid") else remote
        counterparty = _digits(counterparty_source.split("@", 1)[0].split(":", 1)[0])
        allow = insurer_allowlist()
        insurer_key = None
        for v in _br_variants(counterparty):
            if v in allow:
                insurer_key = allow[v]
                break
        if not insurer_key:
            # SPEC-040 Onda 1 — 2º destino (Espelho de Atendimento): conversa
            # com SEGURADO da corretora vai p/ attendance_transcripts quando a
            # integração observer tem escopo 'insurers_and_clients'. O resto
            # continua descartado na borda (privacidade, como hoje).
            if is_observer:
                try:
                    from app.services.atlas.attendance_capture import (
                        SCOPE_FULL, capture_client_message, client_chat_allowed,
                        observer_scope,
                    )

                    if (
                        observer_scope(integration) == SCOPE_FULL
                        and client_chat_allowed(
                            integration, observer_number, remote, counterparty, remote_alt,
                        )
                    ):
                        stored = await capture_client_message(
                            integration,
                            counterparty,
                            key,
                            message,
                            data,
                            remote_jid=remote,
                            alternate_jid=remote_alt,
                        )
                        if stored:
                            return consumed
                except Exception:  # noqa: BLE001 — Espelho NUNCA quebra a borda
                    pass
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
        if media_meta:
            media_meta.update({
                "message_id": record["message_id"],
                "wa_timestamp": wa_ts,
                "company_id": record["company_id"],
                "enrichment_status": "pending",
            })
            record["media_meta"] = media_meta
        await asyncio.to_thread(_store_event_sync, record)
        if media_meta:
            try:
                from app.services.atlas.observer_media import enqueue_observer_media

                await enqueue_observer_media(integration, "observed_events", message, record)
            except Exception as exc:  # noqa: BLE001 - fila nunca invalida a captura
                logger.warning("[ATLAS] fila de mídia indisponível: %s", type(exc).__name__)
        await _beat()
        logger.info(f"[ATLAS] observado {record['direction']} {insurer_key} tipo={msg_type}")
    except Exception as e:  # noqa: BLE001 — o TAP JAMAIS derruba o pipeline
        logger.error(f"[ATLAS] observer tap falhou: {type(e).__name__}")

    return consumed
