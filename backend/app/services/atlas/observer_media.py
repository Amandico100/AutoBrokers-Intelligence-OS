"""Asynchronous media enrichment for the silent Atlas observer.

The webhook stores metadata and returns immediately. This worker downloads the
encrypted WhatsApp attachment through Evolution Go, archives it in private
MinIO storage and derives text when supported. It has no outbound-message
dependency and every failure is isolated to the media record.
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import mimetypes
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

QUEUE_KEY = "atlas:observer:media:queue"
QUEUE_TTL_SECONDS = 3 * 24 * 3600
ALLOWED_TABLES = frozenset({"observed_events", "attendance_transcripts"})


def _max_bytes() -> int:
    try:
        return max(1, min(50, int(os.getenv("OBSERVER_MEDIA_MAX_MB", "15")))) * 1024 * 1024
    except ValueError:
        return 15 * 1024 * 1024


def _safe_filename(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "")).strip(".-")
    return clean[:120] or "attachment"


def _message_for_download(value: Any) -> Any:
    """Remove embedded previews; keep media keys/direct paths required by Go."""
    if isinstance(value, dict):
        return {
            key: _message_for_download(item)
            for key, item in value.items()
            if key not in {"jpegThumbnail", "thumbnail", "thumbnailSha256"}
        }
    if isinstance(value, list):
        return [_message_for_download(item) for item in value]
    return value


# Quantas mídias do histórico ainda podem ser enfileiradas. O contador vive no
# REDIS porque o teto atravessa requisições: quem autoriza é o Admin, e quem
# gasta é o webhook do HistorySync, que chega depois e várias vezes.
#
# Fechado por padrão. A instrução do Founder em 28/07/2026 foi explícita —
# "NÃO FAÇA A ANÁLISE DAS 9565 MÍDIAS VIA API NUNCA. APENAS AS 20". Quem abre
# é uma ação humana, nunca o código.
_ORCAMENTO_MIDIA = "atlas:history:media_budget"


async def _pode_gastar_midia() -> bool:
    """Consome uma unidade do orçamento. Sem orçamento aberto, responde não.

    `DECR` numa chave inexistente cria em -1 e devolve -1 — então a ausência
    de autorização já é uma recusa, sem precisar de nenhum `if` extra. É a
    falha fechada saindo de graça do próprio Redis.
    """
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        return int(await r.decr(_ORCAMENTO_MIDIA)) >= 0
    except Exception:  # noqa: BLE001 — Redis fora = nada é gasto
        return False


async def abrir_orcamento_de_midia(quantas: int, validade_s: int = 7200) -> int:
    """Autoriza N mídias do histórico a serem baixadas e lidas. Ação humana."""
    quantas = max(0, min(int(quantas or 0), 500))
    from app.core.redis import get_async_redis_client

    r = await get_async_redis_client()
    if quantas <= 0:
        await r.delete(_ORCAMENTO_MIDIA)
        return 0
    await r.set(_ORCAMENTO_MIDIA, quantas, ex=validade_s)
    return quantas


async def enqueue_observer_media(
    integration: Dict[str, Any],
    table: str,
    message: Dict[str, Any],
    record: Dict[str, Any],
) -> bool:
    """Queue raw message shape without credentials; Redis is transient."""
    if table not in ALLOWED_TABLES or not record.get("message_id") or not message:
        return False

    # SALVAR É DE GRAÇA. LER É QUE CUSTA. — SPEC-065, 04/08/2026.
    #
    # Aqui ficava `if not await _pode_gastar_midia(): return False`, e o
    # comentário ao lado prometia que "sem orçamento aberto a mídia só é
    # ARQUIVADA — ela não se perde". **A promessa não era verdade.** O portão
    # estava no ENFILEIRAMENTO, então sem orçamento nada era baixado, nada era
    # arquivado, e o áudio ficava só como uma coordenada num campo JSON.
    #
    # 📊 Medido em 04/08/2026: 2.849 mídias com coordenada de download,
    # **ZERO arquivadas**. E 3.654 áudios anteriores ao conserto das
    # coordenadas já estão perdidos para sempre — não têm nem a coordenada.
    #
    # As duas operações têm custos que não se parecem em nada:
    #
    #   BAIXAR + ARQUIVAR   dinheiro nenhum. Os bytes vêm do WhatsApp pela
    #                       sessão já pareada e vão para o MinIO, que roda no
    #                       servidor da própria casa. 📊 488 MB no total, dos
    #                       quais 80 MB de áudio.
    #
    #   TRANSCREVER/LER     Whisper cobra por minuto. É o que precisa de
    #                       orçamento, e continua tendo.
    #
    # E a assimetria decide: uma coordenada de mídia do WhatsApp EXPIRA. Não
    # arquivar hoje é escolher perder o áudio; transcrever depois é sempre
    # possível, porque o arquivo estará no nosso disco.
    #
    # Então o enfileiramento é livre, e o portão desceu para o único lugar onde
    # há conta a pagar: `_derive_text`, no processamento.
    payload = {
        "table": table,
        "company_id": str(record.get("company_id") or ""),
        "message_id": str(record.get("message_id") or ""),
        "integration_id": str((integration or {}).get("id") or ""),
        "message": _message_for_download(message),
        "media_meta": record.get("media_meta") or {},
    }
    try:
        from app.core.redis import get_async_redis_client

        redis = await get_async_redis_client()
        dedupe_key = (
            f"atlas:observer:media:queued:{payload['company_id']}:{payload['message_id']}"
        )
        if not await redis.set(dedupe_key, "1", ex=QUEUE_TTL_SECONDS, nx=True):
            return False
        try:
            await redis.rpush(QUEUE_KEY, json.dumps(payload, ensure_ascii=False, default=str))
        except Exception:
            await redis.delete(dedupe_key)
            raise
        await redis.expire(QUEUE_KEY, QUEUE_TTL_SECONDS)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("[OBSERVER MEDIA] enqueue failed: %s", type(exc).__name__)
        return False


def _load_integration_sync(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    from app.core.database import get_supabase_client
    from app.services.whatsapp.integration_secrets import prepare_integration_for_runtime

    db = get_supabase_client()
    query = db.client.table("integrations").select("*")
    if payload.get("integration_id"):
        query = query.eq("id", payload["integration_id"])
    else:
        query = (
            query.eq("company_id", payload.get("company_id"))
            .eq("provider", "evolution-go")
            .eq("purpose", "observer")
            .eq("is_active", True)
        )
    rows = query.limit(1).execute().data or []
    if not rows or str(rows[0].get("company_id") or "") != str(payload.get("company_id") or ""):
        return None

    # NUNCA BAIXAR POR UM CANAL QUE NÃO ESTÁ DE PÉ. — SPEC-065, 04/08/2026.
    #
    # O caminho por `integration_id` acima não conferia nada disso, e é o
    # caminho normal (o payload sempre traz o id). Uma linha aposentada seguia
    # servindo download.
    #
    # E o risco não é acadêmico: baixar mídia em rajada por uma sessão que está
    # caindo e voltando é justamente o padrão que faz o WhatsApp desconfiar do
    # número. O Founder pediu essa garantia com todas as letras — *"precisa se
    # precaver no fato de baixar os áudios não vá bloquear o número"*.
    #
    # Fila não se perde: o item volta a ser tentado quando o canal voltar, e a
    # coordenada continua no banco. Adiar é barato; ser bloqueado, não.
    linha = rows[0]
    if not linha.get("is_active"):
        raise RuntimeError("canal_aposentado")
    from app.services.whatsapp.channel_state import esta_conectado, normalizar_estado

    estado = normalizar_estado(linha.get("channel_status"))
    if not (esta_conectado(estado) or estado == "connecting"):
        raise RuntimeError(f"canal_{estado}")

    return prepare_integration_for_runtime(linha)


def _motivo_da_falha(exc: BaseException) -> str:
    """O nome da exceção não conserta nada; o status HTTP sim.

    Em 28/07/2026 havia 23 mídias marcadas `failed` no Espelho, todas com o
    mesmo texto: "HTTPStatusError". Não dá para saber se é token errado (401),
    mídia expirada no WhatsApp (404) ou servidor fora (5xx) — e são três
    consertos completamente diferentes.

    Sondado sem token, `/message/downloadmedia` responde 401 e as rotas
    alternativas respondem 404: a rota está certa. Falta saber o status real
    da chamada autenticada, e é isso que este campo passa a guardar.

    Só o status e a rota. Nunca o corpo da resposta nem o token: o corpo pode
    trazer dado de cliente, e o token nunca aparece em log.
    """
    resposta = getattr(exc, "response", None)
    codigo = getattr(resposta, "status_code", None)
    if codigo:
        pedido = getattr(exc, "request", None)
        caminho = ""
        try:
            caminho = urlparse(str(getattr(pedido, "url", "") or "")).path
        except Exception:  # noqa: BLE001
            caminho = ""
        return f"HTTP {codigo}{(' ' + caminho) if caminho else ''}"
    return type(exc).__name__


async def _download_media(
    integration: Dict[str, Any], message: Dict[str, Any]
) -> Tuple[bytes, str]:
    base_url = str(integration.get("base_url") or "").rstrip("/")
    token = str(integration.get("token") or "")
    parsed = urlparse(base_url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or not token:
        raise RuntimeError("invalid_provider_configuration")
    async with httpx.AsyncClient(timeout=45.0, follow_redirects=False) as client:
        response = await client.post(
            f"{base_url}/message/downloadmedia",
            headers={"apikey": token, "Content-Type": "application/json"},
            json={"message": message},
        )
        response.raise_for_status()
        body = response.json() if response.content else {}
    data = body.get("data") if isinstance(body.get("data"), dict) else body
    encoded = str(data.get("base64") or "")
    mimetype = ""
    if encoded.startswith("data:") and "," in encoded:
        header, encoded = encoded.split(",", 1)
        mimetype = header[5:].split(";", 1)[0]
    if len(encoded) > ((_max_bytes() * 4) // 3) + 16_384:
        raise RuntimeError("media_too_large")
    blob = base64.b64decode(encoded)
    if not blob:
        raise RuntimeError("empty_media")
    if len(blob) > _max_bytes():
        raise RuntimeError("media_too_large")
    return blob, mimetype


def _archive_private_sync(
    company_id: str,
    message_id: str,
    blob: bytes,
    mimetype: str,
    filename: str,
) -> str:
    from app.services.minio_service import get_minio_service

    guessed = mimetypes.guess_extension(mimetype or "") or Path(filename).suffix or ".bin"
    object_name = (
        f"observer-media/{_safe_filename(company_id)}/"
        f"{_safe_filename(message_id)}{guessed[:10]}"
    )
    storage = get_minio_service()
    storage.client.put_object(
        bucket_name=storage.bucket_name,
        object_name=object_name,
        data=io.BytesIO(blob),
        length=len(blob),
        content_type=mimetype or "application/octet-stream",
    )
    return object_name


def _extract_document_sync(blob: bytes, mimetype: str, filename: str) -> Optional[str]:
    from app.services.document_service import get_document_service

    lower = str(filename or "").lower()
    file_type = "pdf" if mimetype == "application/pdf" or lower.endswith(".pdf") else None
    if not file_type and ("word" in mimetype or lower.endswith((".doc", ".docx"))):
        file_type = "docx"
    if not file_type and (mimetype.startswith("text/") or lower.endswith((".txt", ".md", ".csv"))):
        file_type = lower.rsplit(".", 1)[-1] if "." in lower else "txt"
    if not file_type:
        return None
    text, _pages = get_document_service().extract_text_internal(io.BytesIO(blob), file_type)
    clean = str(text or "").strip()
    return clean[:20_000] if clean else None


def _teto_de_audio_s() -> int:
    """Quantos segundos de áudio vale a pena transcrever.

    Whisper cobra por minuto. Um áudio de doze minutos custa US$ 0,072 — mais
    de 5% do saldo que a plataforma tinha em 28/07/2026, numa mensagem só. E
    em atendimento de seguro, o que decide o caso está nos primeiros minutos:
    o resto costuma ser espera, ruído ou a pessoa repetindo.

    Três minutos cobrem o áudio real de um segurado explicando um sinistro e
    custam US$ 0,018. Acima disso o áudio é ARQUIVADO e fica sem transcrição —
    visível, recuperável, e não vira conta.
    """
    try:
        return max(15, min(1800, int(os.getenv("MEDIA_MAX_AUDIO_SECONDS", "180"))))
    except ValueError:
        return 180


async def _derive_text(
    blob: bytes,
    mimetype: str,
    filename: str,
    company_id: str,
    segundos: Optional[int] = None,
) -> Optional[str]:
    if mimetype.startswith("audio/"):
        from app.core.config import settings
        from app.services.audio_service import AudioService

        if not settings.OPENAI_API_KEY:
            return None
        teto = _teto_de_audio_s()
        if segundos and segundos > teto:
            logger.info("[OBSERVER MEDIA] áudio de %ds acima do teto de %ds: arquivado sem transcrição",
                        segundos, teto)
            return None
        return await AudioService(settings.OPENAI_API_KEY).transcribe_audio(
            base64.b64encode(blob).decode("ascii"), company_id=company_id, agent_id=None
        )
    if mimetype.startswith("image/"):
        from app.services.vision_service import describe_image

        data_uri = f"data:{mimetype};base64,{base64.b64encode(blob).decode('ascii')}"
        return await describe_image(
            data_uri,
            company_id=company_id,
            agent_id=None,
            purpose_hint="Observador silencioso de uma corretora de seguros",
        )
    if mimetype.startswith("text/") or mimetype in {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }:
        return await asyncio.to_thread(_extract_document_sync, blob, mimetype, filename)
    return None


def _update_record_sync(payload: Dict[str, Any], changes: Dict[str, Any]) -> None:
    from app.core.database import get_supabase_client

    table = str(payload.get("table") or "")
    if table not in ALLOWED_TABLES:
        return
    db = get_supabase_client()
    rows = (
        db.client.table(table)
        .select("id,media_meta")
        .eq("company_id", payload.get("company_id"))
        .eq("message_id", payload.get("message_id"))
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        return
    media_meta = rows[0].get("media_meta") if isinstance(rows[0].get("media_meta"), dict) else {}
    media_meta = {**media_meta, **changes}
    db.client.table(table).update({"media_meta": media_meta}).eq("id", rows[0]["id"]).execute()


async def _process_payload(payload: Dict[str, Any]) -> None:
    integration = await asyncio.to_thread(_load_integration_sync, payload)
    if not integration:
        raise RuntimeError("integration_not_found")
    blob, downloaded_mimetype = await _download_media(integration, payload.get("message") or {})
    meta = payload.get("media_meta") if isinstance(payload.get("media_meta"), dict) else {}
    mimetype = downloaded_mimetype or str(meta.get("mimetype") or "application/octet-stream")
    filename = str(meta.get("filename") or f"{payload.get('message_id')}.bin")
    temp_path: Optional[str] = None
    try:
        suffix = Path(filename).suffix or mimetypes.guess_extension(mimetype) or ".bin"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix[:10]) as tmp:
            tmp.write(blob)
            temp_path = tmp.name
        private_object = await asyncio.to_thread(
            _archive_private_sync,
            str(payload.get("company_id") or ""),
            str(payload.get("message_id") or ""),
            blob,
            mimetype,
            filename,
        )
        # O ARQUIVO JÁ ESTÁ SALVO. A leitura é a parte que pode esperar.
        #
        # `_pode_gastar_midia` desceu do enfileiramento para cá (SPEC-065): sem
        # orçamento aberto, o áudio fica **arquivado e sem transcrição** — que é
        # exatamente o que o comentário lá em cima sempre prometeu e o código
        # não fazia. Transcrever depois é sempre possível; recuperar um áudio
        # cuja coordenada expirou, não.
        pode_ler = await _pode_gastar_midia()
        derived_text = None
        if pode_ler:
            derived_text = await _derive_text(
                blob, mimetype, filename, str(payload.get("company_id") or ""),
                segundos=(meta or {}).get("segundos"),
            )
        mudancas = {
            "mimetype": mimetype,
            "filename": filename,
            "private_object": private_object,
            # `arquivado` diz "os bytes estão no nosso disco, o texto não foi
            # lido". É um estado diferente de `processed`, e a diferença é o
            # que permite achar depois o que ainda falta transcrever.
            "enrichment_status": "processed" if pode_ler else "arquivado",
        }
        if pode_ler:
            mudancas["derived_text"] = derived_text
        await asyncio.to_thread(_update_record_sync, payload, mudancas)
    finally:
        if temp_path:
            try:
                Path(temp_path).unlink(missing_ok=True)
            except OSError:
                logger.warning("[OBSERVER MEDIA] temporary file cleanup failed")


async def check_observer_media(batch_size: int = 3) -> int:
    """APScheduler entrypoint. Processes a small bounded batch, fail-soft."""
    try:
        from app.core.redis import get_async_redis_client

        redis = await get_async_redis_client()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[OBSERVER MEDIA] Redis unavailable: %s", type(exc).__name__)
        return 0
    processed = 0
    for _ in range(max(1, min(10, batch_size))):
        raw = await redis.lpop(QUEUE_KEY)
        if not raw:
            break
        payload: Dict[str, Any] = {}
        try:
            payload = json.loads(raw.decode() if isinstance(raw, (bytes, bytearray)) else raw)
            lock_key = f"atlas:observer:media:lock:{payload.get('company_id')}:{payload.get('message_id')}"
            if not await redis.set(lock_key, "1", ex=300, nx=True):
                continue
            try:
                await _process_payload(payload)
                processed += 1
            finally:
                await redis.delete(lock_key)
        except Exception as exc:  # noqa: BLE001
            motivo = _motivo_da_falha(exc)
            logger.error("[OBSERVER MEDIA] enrichment failed: %s", motivo)
            try:
                await asyncio.to_thread(
                    _update_record_sync,
                    payload,
                    {"enrichment_status": "failed", "enrichment_error": motivo},
                )
            except Exception:  # noqa: BLE001
                pass
    return processed


async def observer_media_check() -> int:
    """Stable scheduler alias used by diagnostics and tests."""
    return await check_observer_media()
