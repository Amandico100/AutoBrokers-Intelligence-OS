"""F1 — Visão e documentos GLOBAIS (SPEC em docs/canon; pedido central do founder).

Qualquer agente (Chat Principal, atendente externo, auxiliares) passa a:
- VER imagens: `describe_image` gera contexto visual com o vision_model do
  agente OU o default da plataforma — nunca mais "não consigo visualizar".
- LER documentos (PDF/DOCX...): `extract_document_text` baixa, parseia via
  docling (mesmo parser da base de conhecimento) e devolve texto truncado.

Fail-safe em tudo: sem chave/modelo/parse → None e o fluxo segue só com texto.
"""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Default da plataforma quando o agente não tem vision_model configurado.
_DEFAULT_OPENAI_VISION = "gpt-4o-mini"
_DEFAULT_ANTHROPIC_VISION = "claude-3-5-sonnet-20241022"

_SUPPORTED_DOC_EXTENSIONS = (".pdf", ".docx", ".pptx", ".xlsx", ".html", ".md", ".txt", ".csv")

_MAX_DOC_CHARS = 20000


def resolve_vision_model(agent_data: Optional[Dict[str, Any]]) -> Optional[Tuple[str, str]]:
    """(modelo, api_key) para visão: agente primeiro, depois default da
    plataforma (OpenAI → Anthropic). None = nenhum caminho disponível."""
    configured = str((agent_data or {}).get("vision_model") or "").strip()
    openai_key = os.getenv("OPENAI_API_KEY") or ""
    anthropic_key = os.getenv("ANTHROPIC_API_KEY") or ""

    if configured:
        if configured.startswith("gpt-") and openai_key:
            return configured, openai_key
        if configured.startswith("claude") and anthropic_key:
            return configured, anthropic_key
        # Modelo configurado mas sem chave correspondente → tenta o default.
    if openai_key:
        return _DEFAULT_OPENAI_VISION, openai_key
    if anthropic_key:
        return _DEFAULT_ANTHROPIC_VISION, anthropic_key
    return None


def truncate_document_text(text: str, max_chars: int = _MAX_DOC_CHARS) -> str:
    t = str(text or "")
    if len(t) <= max_chars:
        return t
    return t[:max_chars] + "\n\n[DOCUMENTO TRUNCADO — conteúdo acima cobre o início do arquivo]"


def is_supported_document(file_name: str) -> bool:
    return str(file_name or "").lower().endswith(_SUPPORTED_DOC_EXTENSIONS)


async def describe_image(
    image_url: str,
    *,
    company_id: str,
    agent_id: Optional[str] = None,
    agent_data: Optional[Dict[str, Any]] = None,
    purpose_hint: str = "Agente de Suporte",
) -> Optional[str]:
    """Analisa a imagem e devolve descrição técnica p/ virar contexto do agente.
    Custo registrado no billing (service_type=vision). Falha → None."""
    resolved = resolve_vision_model(agent_data)
    if not resolved or not image_url:
        if image_url:
            logger.warning("[VISION] sem modelo/chave de visão disponível")
        return None
    model, key = resolved
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        from app.core.callbacks.cost_callback import CostCallbackHandler

        callbacks = [
            CostCallbackHandler(
                service_type="vision",
                company_id=str(company_id),
                agent_id=str(agent_id) if agent_id else None,
                model_name=model,
            )
        ]
        if model.startswith("claude"):
            from langchain_anthropic import ChatAnthropic

            llm = ChatAnthropic(model=model, api_key=key, temperature=0.3, callbacks=callbacks)
        else:
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(model=model, api_key=key, temperature=0.3, callbacks=callbacks)

        result = await llm.ainvoke([
            SystemMessage(content=(
                f"Descreva a imagem para um {purpose_hint} de corretora de seguros. "
                "Seja objetivo e completo: o que aparece, textos legíveis, números, danos visíveis, "
                "documentos identificáveis. Sem opinião, só o que está na imagem."
            )),
            HumanMessage(content=[
                {"type": "text", "text": "Descreva:"},
                {"type": "image_url", "image_url": {"url": image_url}},
            ]),
        ])
        content = getattr(result, "content", None)
        return str(content).strip() if content else None
    except Exception as e:  # noqa: BLE001
        logger.error(f"[VISION] describe_image falhou: {type(e).__name__}")
        return None


async def extract_document_text(file_url: str, file_name: str = "") -> Optional[str]:
    """Baixa o documento e extrai texto via docling (mesmo parser da KB).
    Devolve markdown truncado ou None (fail-safe)."""
    if not file_url or not is_supported_document(file_name or file_url):
        return None
    suffix = os.path.splitext((file_name or file_url).split("?")[0])[1].lower() or ".pdf"
    tmp_path = None
    try:
        import httpx

        async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
            res = await client.get(file_url)
            res.raise_for_status()
            data = res.content
        if not data:
            return None

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        import asyncio

        def _parse() -> str:
            # Texto puro não precisa de parser.
            if suffix in (".txt", ".csv", ".md"):
                return data.decode("utf-8", errors="replace")
            # 1º: docling (microserviço — melhor qualidade, se configurado).
            try:
                from app.services.sanitization_service import SanitizationService

                markdown, _meta = SanitizationService()._docling_parse(tmp_path, extract_images=False)  # noqa: SLF001
                if markdown and markdown.strip():
                    return markdown
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[VISION] docling indisponível ({type(e).__name__}) — fallback PyPDF2")
            # 2º: fallback local p/ PDF (PyPDF2 já é dependência da casa).
            if suffix == ".pdf":
                from PyPDF2 import PdfReader

                reader = PdfReader(tmp_path)
                pages = []
                for i, page in enumerate(reader.pages[:40]):
                    try:
                        pages.append(f"[página {i + 1}]\n{page.extract_text() or ''}")
                    except Exception:  # noqa: BLE001
                        continue
                return "\n\n".join(pages)
            return ""

        markdown = await asyncio.to_thread(_parse)
        text = truncate_document_text(markdown)
        return text if text.strip() else None
    except Exception as e:  # noqa: BLE001
        logger.error(f"[VISION] extract_document_text falhou: {type(e).__name__}")
        return None
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
