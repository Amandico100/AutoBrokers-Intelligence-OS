"""SPEC-040 Onda 2 — Seed do CONHECIMENTO GLOBAL (a inteligência AutoBrokers).

Ingestão idempotente dos documentos canônicos embarcados no repo
(`app/data/global_knowledge/*.md`) na coleção Qdrant `autobrokers_global`.
É o encanamento que faltava: a BUSCA global já existia (search_service);
agora o conteúdo entra sozinho a cada deploy, sem passo manual.

Regras (POLITICA-SEGURANCA-CONHECIMENTO-GLOBAL):
- Só conteúdo curado SEM dado de cliente/segredo (os seeds são docs de
  ESTRUTURA: mapas de navegação, processos). Os agentes USAM; ninguém de
  fora VÊ, LISTA ou BAIXA.
- Idempotente por hash de conteúdo (marcador Redis): mesmo arquivo não
  re-ingere; arquivo alterado re-ingere e substitui os chunks antigos.
- Fail-soft: falha de um arquivo não derruba os outros nem o scheduler.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_MARKER = "global_seed:{stem}"


def _seed_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "global_knowledge"


def _global_company_id() -> str:
    return (os.getenv("GLOBAL_KNOWLEDGE_COMPANY_ID") or "").strip() or "autobrokers-global"


def _ingest_seed_sync(stem: str, title: str, content: str, content_hash: str) -> int:
    """Chunk -> embeddings (dense + sparse) -> Qdrant autobrokers_global."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    from app.core.config import settings
    from app.services.knowledge_scope import GLOBAL_COLLECTION, SCOPE_GLOBAL_AUTOBROKERS
    from app.services.qdrant_service import get_qdrant_service

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200,
        separators=["\n## ", "\n### ", "\n#### ", "\n\n", "\n", ". ", " "],
    )
    chunks = [d.page_content for d in splitter.create_documents([content])]
    if not chunks:
        return 0

    from langchain_openai import OpenAIEmbeddings

    dense = OpenAIEmbeddings(
        model="text-embedding-3-small", api_key=settings.OPENAI_API_KEY
    ).embed_documents(chunks)

    sparse = None
    try:  # BM25 é bônus (busca híbrida); dense-only já funciona
        from fastembed import SparseTextEmbedding

        sparse = list(SparseTextEmbedding(model_name="Qdrant/bm25").embed(chunks))
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[SEED GLOBAL] sparse indisponível ({type(e).__name__}) — seguindo dense-only")

    qdrant = get_qdrant_service()
    doc_id = f"seed-{stem}"
    company = _global_company_id()
    try:  # substitui a versão anterior do mesmo seed
        qdrant.delete_document(company, doc_id, collection_name=GLOBAL_COLLECTION)
    except Exception:  # noqa: BLE001
        pass
    ok = qdrant.insert_embeddings(
        company_id=company,
        document_id=doc_id,
        embeddings=dense,
        chunks=chunks,
        metadata={"document_name": title, "source": "canon_seed", "chunk_type": "markdown"},
        sparse_embeddings=sparse,
        collection_name=GLOBAL_COLLECTION,
        agent_id=None,
        knowledge_extras={
            "scope": SCOPE_GLOBAL_AUTOBROKERS,
            "curation_status": "published",
            "namespace": "canon",
            "version": content_hash[:12],
        },
    )
    return len(chunks) if ok else 0


async def check_global_seed() -> int:
    """Task periódica (APScheduler): ingere/atualiza os seeds cujo conteúdo
    mudou desde a última ingestão (hash no Redis). Custo zero quando nada
    mudou. Nunca derruba o scheduler."""
    total = 0
    try:
        seed_dir = _seed_dir()
        if not seed_dir.is_dir():
            return 0
        try:
            from app.core.redis import get_async_redis_client

            redis = await get_async_redis_client()
        except Exception:  # noqa: BLE001
            redis = None

        for path in sorted(seed_dir.glob("*.md")):
            try:
                content = path.read_text(encoding="utf-8")
                h = hashlib.sha256(content.encode("utf-8")).hexdigest()
                marker_key = _MARKER.format(stem=path.stem)
                if redis is not None:
                    cur = await redis.get(marker_key)
                    cur = cur.decode() if isinstance(cur, (bytes, bytearray)) else cur
                    if cur == h:
                        continue  # já ingerido nesta versão
                title = content.splitlines()[0].lstrip("# ").strip() if content else path.stem
                n = await asyncio.to_thread(_ingest_seed_sync, path.stem, title, content, h)
                if n:
                    total += n
                    if redis is not None:
                        await redis.set(marker_key, h)
                    logger.info(f"[SEED GLOBAL] '{path.stem}' ingerido: {n} chunks")
            except Exception as e:  # noqa: BLE001
                logger.error(f"[SEED GLOBAL] '{path.name}' falhou: {type(e).__name__}")
    except Exception as e:  # noqa: BLE001
        logger.error(f"[SEED GLOBAL] check falhou: {type(e).__name__}")
    return total
