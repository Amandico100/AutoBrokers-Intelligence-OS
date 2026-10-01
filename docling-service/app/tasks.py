"""
Celery tasks for Docling document parsing
"""

import logging
import os
import time
from typing import Any, Dict, Optional, Tuple

from minio import Minio

from .celery_app import celery_app
from .config import settings

logger = logging.getLogger("docling-worker")


#: Os provedores cujo formato o `PictureDescriptionApiOptions` do Docling fala (só Chat Completions
#: OpenAI — 📊 docling-slim 2.130.0 `utils/api_image_request.py`, lido em 01/10/2026). O `/parse`
#: recusa outro com 400; o smith-api escolhe, na rota, o primeiro de (primário, reserva) daqui.
PROVEDORES_DA_VISAO = frozenset({"openai"})

#: A escala canônica de esforço (`model_policy.NIVEIS_DE_ESFORCO` do backend). Fora dela → 400.
NIVEIS_DE_ESFORCO = ("none", "low", "medium", "high", "xhigh", "max")


def visao_pedida(vision: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """O modelo que VALE neste pedido: o do chamador (catálogo) ou o PARAQUEDAS (env).

    `vision` = {"provider", "model", "effort"} vindo do POST /parse, ou None (chamador antigo).
    """
    v = vision or {}
    modelo = str(v.get("model") or "").strip()
    if modelo:
        esforco = str(v.get("effort") or "").strip().lower() or None
        return {"provider": str(v.get("provider") or "openai").strip().lower(), "modelo": modelo,
                "esforco": esforco, "origem": "chamador"}
    esforco = (settings.VISION_REASONING_EFFORT or "").strip().lower() or None
    return {"provider": "openai", "modelo": settings.VISION_MODEL, "esforco": esforco,
            "origem": "paraquedas"}


def _params_da_visao(vision: Optional[Dict[str, Any]] = None) -> dict:
    """O corpo extra do pedido de visão (Chat Completions): modelo, teto e esforço.

    🔴 SPEC-124 D4: o modelo é o do CHAMADOR (rota `visao_documento` do catálogo); sem ele,
    o paraquedas `VISION_MODEL`. ⛔ Nada de sampling (`temperature`/`seed`): o GPT-6 não o
    aceita (catálogo: sampling_ok=false). `reasoning_effort` só quando há esforço.
    """
    escolha = visao_pedida(vision)
    params = dict(model=escolha["modelo"],
                  max_completion_tokens=settings.VISION_MAX_COMPLETION_TOKENS)
    if escolha["esforco"]:
        params["reasoning_effort"] = escolha["esforco"]
    return params


def _uso_da_visao(doc: Any) -> Dict[str, int]:
    """Imagens descritas e o USO REAL somado. O Docling 2.130 grava o `usage` da resposta em
    `picture.meta.description` (campo custom `docling__usage` — 📊 `picture_description_base_model.py`
    :107-128 e `docling_core/types/doc/common/meta.py:60`). Imagem com texto vazio = pedido que
    falhou: não conta."""
    total = {"imagens_descritas": 0, "imagens_com_uso": 0, "entrada": 0, "saida": 0,
             "cache": 0, "raciocinio": 0}
    for pic in getattr(doc, "pictures", None) or []:
        meta = getattr(pic, "meta", None)
        desc = getattr(meta, "description", None) if meta is not None else None
        if desc is None or not str(getattr(desc, "text", "") or "").strip():
            continue
        total["imagens_descritas"] += 1
        try:
            uso = (desc.get_custom_part() or {}).get("docling__usage")
        except Exception:  # noqa: BLE001
            uso = None
        if isinstance(uso, dict):
            total["imagens_com_uso"] += 1
            total["entrada"] += int(uso.get("prompt_tokens") or 0)
            total["saida"] += int(uso.get("completion_tokens") or 0)
            total["cache"] += int((uso.get("prompt_tokens_details") or {}).get("cached_tokens") or 0)
            total["raciocinio"] += int((uso.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0)
    return total


def _get_minio_client() -> Minio:
    """Create MinIO client."""
    return Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )


@celery_app.task(
    bind=True,
    name="app.tasks.parse_document",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_kwargs={"max_retries": 2},
)
def parse_document(self, task_id: str, minio_path: str, filename: str, extract_images: bool = False,
                   vision: Optional[Dict[str, Any]] = None):
    """
    Parse a document using Docling.

    Args:
        task_id: Unique task identifier
        minio_path: Path to file in MinIO (docling-temp/{task_id}/{filename})
        filename: Original filename (for extension detection)
        extract_images: If True, enable Vision API for image description
        vision: SPEC-124 D4 — {"provider", "model", "effort"} da rota `visao_documento` do
            catálogo (o smith-api resolve). None = paraquedas VISION_MODEL (chamador antigo).

    Returns:
        Dict with markdown, metadata, and processing_time
    """
    logger.info(f"[Task {task_id}] Starting: download from MinIO → Docling parse (extract_images={extract_images})")
    start_time = time.time()

    local_path = None

    try:
        # Download from MinIO to local /tmp
        minio_client = _get_minio_client()

        ext = os.path.splitext(filename)[1].lower()
        local_path = f"/tmp/{task_id}{ext}"

        minio_client.fget_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=minio_path,
            file_path=local_path,
        )

        logger.info(f"[Task {task_id}] Downloaded from MinIO to {local_path}")

        # Parse with Docling
        markdown, metadata = _docling_parse(local_path, extract_images, vision)

        elapsed = time.time() - start_time

        logger.info(
            f"[Task {task_id}] Completed in {elapsed:.1f}s. "
            f"Output: {len(markdown)} chars"
        )

        return {
            "status": "completed",
            "markdown": markdown,
            "metadata": metadata,
            "processing_time_seconds": round(elapsed, 2),
        }

    except Exception as e:
        logger.error(f"[Task {task_id}] Failed: {e}", exc_info=True)
        raise

    finally:
        # Cleanup: delete local temp file
        if local_path and os.path.exists(local_path):
            try:
                os.unlink(local_path)
            except Exception:
                pass

        # Cleanup: delete from MinIO (temp file no longer needed)
        try:
            minio_client = _get_minio_client()
            minio_client.remove_object(
                bucket_name=settings.MINIO_BUCKET,
                object_name=minio_path,
            )
            logger.debug(f"[Task {task_id}] Cleaned up MinIO temp: {minio_path}")
        except Exception:
            pass


def _docling_parse(file_path: str, extract_images: bool = False,
                   vision: Optional[Dict[str, Any]] = None) -> Tuple[str, Dict[str, Any]]:
    """
    Parse document using IBM Docling.

    Args:
        file_path: Path to the local file
        extract_images: If True, enable Vision API with classifier prompt

    Returns:
        Tuple of (markdown_string, metadata_dict)
    """
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import (  # 📌 docling==2.130.0 (requirements.txt)
        PdfPipelineOptions,
        PictureDescriptionApiOptions,
    )
    from docling.document_converter import DocumentConverter, PdfFormatOption

    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True

    # Conditionally enable Vision API for image analysis
    if extract_images:
        _escolha = visao_pedida(vision)
        logger.info("[Docling] Vision API ENABLED — model=%s effort=%s origem=%s",
                    _escolha["modelo"], _escolha["esforco"], _escolha["origem"])
        pipeline_options.generate_picture_images = True
        pipeline_options.do_picture_description = True
        pipeline_options.enable_remote_services = True

        # Prompt with INFORMACIONAL/DECORATIVA classifier
        pipeline_options.picture_description_options = PictureDescriptionApiOptions(
            url=settings.VISION_API_URL,
            # 🔴 SPEC-116 (24/09/2026): sem `seed`/`temperature` — GPT-6 Sol tem
            # sampling_ok=false no catálogo (EVIDENCIAS/04); o Docling 2.130.0
            # manda SÓ `messages` + estes params (utils/api_image_request.py).
            params=_params_da_visao(vision),
            timeout=settings.VISION_TIMEOUT_SECONDS,
            prompt=(
                "Primeiro classifique esta imagem: "
                "[INFORMACIONAL] se contém dados, gráficos, tabelas, fluxogramas, "
                "diagramas, textos relevantes ou qualquer informação útil ao documento. "
                "[DECORATIVA] se é logotipo, ícone, foto genérica, marca d'água, "
                "borda decorativa ou elemento visual sem conteúdo informativo. "
                "Comece sua resposta OBRIGATORIAMENTE com a classificação entre colchetes. "
                "Se [INFORMACIONAL], descreva de forma COMPLETA e EXAUSTIVA todos os dados visíveis: "
                "textos, rótulos, legendas, números, valores, etapas e conexões. "
                "Se [DECORATIVA], escreva APENAS: [DECORATIVA] Elemento visual decorativo. "
                "Responda em português brasileiro."
            ),
            headers={
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            },
        )
    else:
        logger.info("[Docling] Vision API DISABLED — skipping image analysis")
        pipeline_options.generate_picture_images = True
        pipeline_options.do_picture_description = False

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        }
    )

    logger.info(f"[Docling] Starting parse: {file_path}")
    result = converter.convert(file_path)

    markdown_output = result.document.export_to_markdown()

    # Extract metadata
    metadata: Dict[str, Any] = {
        "pages_count": None,
        "images_count": None,
        "tables_count": None,
    }

    try:
        doc = result.document
        if hasattr(doc, "pages") and doc.pages:
            metadata["pages_count"] = len(doc.pages)
        if hasattr(doc, "tables") and doc.tables:
            metadata["tables_count"] = len(doc.tables)
        if hasattr(doc, "pictures") and doc.pictures:
            metadata["images_count"] = len(doc.pictures)
    except Exception as e:
        logger.warning(f"[Docling] Could not extract metadata: {e}")

    # SPEC-124 D4: o resultado DIZ qual modelo leu as imagens e quanto usou — o smith-api grava
    # o custo no ledger da corretora (este serviço não tem banco).
    escolha = visao_pedida(vision) if extract_images else {
        "provider": None, "modelo": None, "esforco": None, "origem": "desligada"}
    uso = _uso_da_visao(result.document) if extract_images else _uso_da_visao(None)
    metadata["visao"] = {"provider": escolha["provider"], "modelo": escolha["modelo"],
                         "esforco": escolha["esforco"], "origem": escolha["origem"], **uso}

    return markdown_output, metadata

