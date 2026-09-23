"""F1 — Visão e documentos GLOBAIS (SPEC em docs/canon; pedido central do founder).

Qualquer agente (Chat Principal, atendente externo, auxiliares) passa a:
- VER imagens: `describe_image` gera contexto visual com o modelo da ROTA do
  papel `visao` (SPEC-116) — nunca mais "não consigo visualizar".
- LER documentos (PDF/DOCX...): `extract_document_text` baixa, parseia via
  docling (mesmo parser da base de conhecimento) e devolve texto truncado.

Fail-safe em tudo: sem chave/modelo/parse → None e o fluxo segue só com texto.
"""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# 🔴 SPEC-116 U8 (F3a) — A VISÃO PEDE UM PAPEL, NÃO UM MODELO.
#
# 📊 23/09/2026 (EVIDENCIAS/01 F2): toda foto do segurado era lida por
# `gpt-4o-mini`, qualquer que fosse o agente — `webhook.py` chamava
# `describe_image` sem agente e aqui morava o default literal; o fallback era
# o Claude 3.5 Sonnet RETIRADO (404 desde 28/10/2025); e `temperature=0.3` ia a
# `ChatAnthropic` — Claude 5 devolve 400 e o agente ficava cego calado.
#
# Agora: `LLMFactory.create_llm(..., papel="visao")`. Quem decide o modelo é a
# ROTA do papel (`llm_papeis`, D-116-17: a rota vence o `vision_model` do
# agente); o `vision_model` gravado vale só se o papel ficar SEM rota, e só se
# estiver no catálogo. Sampling segue o catálogo (a fábrica tira `temperature`
# de quem a recusa). Gemini entra pelo ramo `google` da fábrica; modelo fora do
# catálogo ou sem adaptador é `ModeloNaoResolvido` — erro EXPLÍCITO no log,
# nunca um mini por omissão. Toda chamada entra no ledger (service_type=vision,
# com papel · pedido · resolvido).

#: A marca que o texto do turno leva quando a imagem JÁ foi descrita. O webhook
#: descreve a foto do segurado antes do grafo e grava esta marca no texto;
#: `process_message` a encontra e NÃO descreve de novo (📊 23/09/2026: 2
#: chamadas de visão por foto e o contexto visual DUPLICADO no prompt).
MARCA_DO_CONTEXTO_VISUAL = "[CONTEXTO VISUAL"

TEMPERATURA_DA_VISAO = 0.3

_SUPPORTED_DOC_EXTENSIONS = (".pdf", ".docx", ".pptx", ".xlsx", ".html", ".md", ".txt", ".csv")

_MAX_DOC_CHARS = 20000


def imagem_ja_descrita(texto: Optional[str]) -> bool:
    """O texto do turno já carrega a descrição da imagem (a marca do webhook)?"""
    return MARCA_DO_CONTEXTO_VISUAL in str(texto or "")


def criar_llm_de_visao(
    *,
    company_id: Optional[str],
    agent_id: Optional[str] = None,
    agent_data: Optional[Dict[str, Any]] = None,
    temperature: float = TEMPERATURA_DA_VISAO,
):
    """O modelo do papel `visao`, construído PELA FÁBRICA (ledger incluso).

    ⛔ Levanta `ModeloNaoResolvido` (papel sem rota e sem modelo governado) ou
    `ValueError` (chave ausente) — nunca devolve um modelo por omissão.
    """
    from app.factories.llm_factory import LLMFactory

    pedido = str((agent_data or {}).get("vision_model") or "").strip() or None
    return LLMFactory.create_llm(
        {},
        {"llm_model": pedido, "llm_temperature": temperature},
        company_id=str(company_id) if company_id else None,
        agent_id=str(agent_id) if agent_id else None,
        service_type="vision",
        papel="visao",
    )


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
    llm=None,
) -> Optional[str]:
    """Analisa a imagem e devolve descrição técnica p/ virar contexto do agente.

    Modelo: papel `visao` pela fábrica (ver o topo do módulo). `llm=` é o PONTO
    DE INJEÇÃO da bancada (SPEC-116 F5b) e dos testes: quando vem, é usado como
    está. Falha → None (o fluxo segue só com o texto), com o motivo no log.
    """
    if not image_url:
        return None
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        modelo = llm if llm is not None else criar_llm_de_visao(
            company_id=company_id, agent_id=agent_id, agent_data=agent_data)
        result = await modelo.ainvoke([
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
        content = _texto_da_resposta(getattr(result, "content", None))
        return content or None
    except Exception as e:  # noqa: BLE001
        # ⛔ Nunca o conteúdo da imagem nem a URL no log — só o motivo.
        from app.factories.model_policy import ModeloNaoResolvido

        if isinstance(e, ModeloNaoResolvido):
            logger.error("[VISION] papel 'visao' sem modelo governado: %s", e)
        else:
            logger.error(f"[VISION] describe_image falhou: {type(e).__name__}")
        return None


def _texto_da_resposta(content: Any) -> str:
    """O texto da resposta — Claude 5 com raciocínio devolve LISTA de blocos."""
    if isinstance(content, list):
        partes = []
        for bloco in content:
            if isinstance(bloco, dict):
                if bloco.get("type") in (None, "text"):
                    partes.append(str(bloco.get("text") or ""))
            else:
                partes.append(str(bloco))
        content = "".join(partes)
    return str(content or "").strip()


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
