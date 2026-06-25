"""Official policy document evidence orchestration.

R1C.1: this module does not create a parallel RAG/parser/storage. It
coordinates the existing DocumentService/MinIO extraction path and the existing
ingestion path for InfoCap official policy PDFs, then builds short page-based
evidence snippets for the Smith runtime.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import tempfile
import unicodedata
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)


POLICY_DOCUMENT_STATES = {
    "source_available",
    "fetching",
    "fetched",
    "direct_extracting",
    "docling_pending",
    "parsed",
    "evidence_ready",
    "source_unavailable",
    "source_fetch_failed",
    "document_not_policy_evidence",
    "low_confidence",
    "conflict_requires_human",
}

OFFICIAL_POLICY_DOCUMENT_TYPE = "official_policy_document"
OFFICIAL_POLICY_DOCUMENT_SOURCE = "official_policy_document"
OFFICIAL_POLICY_PROVIDER = "infocap"
MAX_EVIDENCE_TEXT_CHARS = 700

_INTENT_TERMS = (
    "cobertura",
    "coberturas",
    "cobre",
    "coberto",
    "garantia",
    "garantias",
    "assistencia",
    "assistencia residencial",
    "eletricista",
    "encanador",
    "chaveiro",
    "franquia",
    "lmi",
    "limite",
    "importancia segurada",
    "clausula",
    "clausulas",
    "exclusao",
    "exclusoes",
    "condicao",
    "condicoes",
    "riscos cobertos",
    "danos eletricos",
)

_EVIDENCE_PATTERNS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("coverage", ("cobertura", "coberturas", "garantia", "garantias", "riscos cobertos", "danos eletricos")),
    ("assistance", ("assistencia", "servicos emergenciais", "eletricista", "chaveiro", "encanador")),
    ("deductible", ("franquia", "dedutivel")),
    ("premium", ("premio", "premios", "custo do seguro")),
    ("installment", ("parcela", "parcelas", "vencimento", "quitacao")),
    ("lmi", ("lmi", "limite maximo", "importancia segurada", "limite de indenizacao")),
    ("clause", ("clausula", "clausulas", "condicoes particulares", "condicoes gerais")),
    ("exclusion", ("exclusao", "exclusoes", "nao coberto", "riscos excluidos")),
    ("insured_object", ("objeto segurado", "bem segurado", "imovel segurado", "endereco do risco")),
)

_FORBIDDEN_OUTPUT_TERMS = (
    "authorization",
    "bearer ",
    "cookie",
    "set-cookie",
    "token",
    "%pdf",
    "http://",
    "https://",
)


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def _short_hash(value: str, length: int = 24) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:length]


def policy_locator_hash(policy_locator: Dict[str, Any]) -> str:
    provider = str(policy_locator.get("provider") or OFFICIAL_POLICY_PROVIDER).strip().lower()
    codfil = str(policy_locator.get("codfil") or "").strip()
    nosnum = str(policy_locator.get("nosnum") or "").strip()
    if not codfil or not nosnum:
        raise ValueError("PolicyLocator requires codfil and nosnum")
    return _short_hash(f"{provider}:{codfil}:{nosnum}", 24)


def policy_document_cache_key(company_id: str, policy_locator: Dict[str, Any], content_hash: str) -> str:
    company_hash = _short_hash(company_id, 16)
    locator_hash = policy_locator_hash(policy_locator)
    return f"policydoc:{company_hash}:infocap:{locator_hash}:{str(content_hash or '')[:24]}"


def policy_document_evidence_requested(question: Optional[str], explicit: bool = False) -> bool:
    if explicit:
        return True
    normalized = _strip_accents(question or "")
    return any(term in normalized for term in _INTENT_TERMS)


def _redact_short_text(value: str) -> str:
    text = str(value or "")
    text = re.sub(r"https?://\S+", "[url-redigida]", text, flags=re.IGNORECASE)
    text = re.sub(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", "[documento-redigido]", text)
    text = re.sub(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b", "[documento-redigido]", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:MAX_EVIDENCE_TEXT_CHARS]


def _split_page_fragments(text: str) -> List[str]:
    raw = str(text or "").replace("\r", "\n")
    fragments: List[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if len(line) <= MAX_EVIDENCE_TEXT_CHARS:
            fragments.append(line)
            continue
        parts = re.split(r"(?<=[.;:])\s+", line)
        fragments.extend(part.strip() for part in parts if part.strip())
    return fragments


def _classify_fragment(fragment: str) -> List[str]:
    normalized = _strip_accents(fragment)
    if re.search(r"\b(sem|nao|não)\s+(cobertura|coberturas|garantia|garantias|assistencia|franquia)\b", normalized):
        return []
    found: List[str] = []
    for evidence_type, terms in _EVIDENCE_PATTERNS:
        if any(term in normalized for term in terms):
            found.append(evidence_type)
    return found


def _confidence_for_evidence(items: List[Dict[str, Any]]) -> str:
    types_found = {item.get("evidence_type") for item in items}
    if {"coverage", "assistance", "deductible", "lmi"} & types_found:
        return "high"
    if items:
        return "medium"
    return "low"


def extract_policy_document_evidence(
    pages: Iterable[Dict[str, Any]],
    *,
    question: str,
    document_id: str,
    company_id: str,
    policy_locator: Dict[str, Any],
    content_hash: str,
    extraction_method: str = "direct_text",
) -> List[Dict[str, Any]]:
    locator_hash = policy_locator_hash(policy_locator)
    evidence: List[Dict[str, Any]] = []
    seen: set[Tuple[int, str, str]] = set()

    for page in pages or []:
        try:
            page_number = int(page.get("page_number") or 0) or 1
        except (TypeError, ValueError):
            page_number = 1
        content = page.get("content") or page.get("text") or ""
        for fragment in _split_page_fragments(content):
            types_found = _classify_fragment(fragment)
            if not types_found:
                continue
            snippet = _redact_short_text(fragment)
            for evidence_type in types_found:
                key = (page_number, evidence_type, snippet)
                if key in seen:
                    continue
                seen.add(key)
                evidence.append(
                    {
                        "document_id": document_id,
                        "company_id": company_id,
                        "policy_locator_hash": locator_hash,
                        "page_number": page_number,
                        "chunk_id": f"{document_id}:p{page_number}:{len(evidence) + 1}",
                        "evidence_type": evidence_type,
                        "evidence_text": snippet,
                        "source_document": OFFICIAL_POLICY_DOCUMENT_SOURCE,
                        "extraction_method": extraction_method,
                        "confidence": "high" if evidence_type in {"coverage", "assistance", "deductible", "lmi"} else "medium",
                        "content_hash": content_hash,
                        "conflict_status": "none",
                    }
                )
            if len(evidence) >= 40:
                return evidence
    return evidence


def _safe_filename(policy_locator: Dict[str, Any], content_hash: str) -> str:
    return f"infocap-policy-{policy_locator_hash(policy_locator)}-{str(content_hash or '')[:16]}.pdf"


def _sanitize_pipeline_output(value: Any) -> Any:
    if isinstance(value, list):
        return [_sanitize_pipeline_output(item) for item in value]
    if isinstance(value, dict):
        clean: Dict[str, Any] = {}
        for key, child in value.items():
            key_norm = _strip_accents(str(key))
            if key_norm in {"url", "source_url", "final_url", "authorization", "cookie", "token", "body", "raw", "payload", "codfil", "nosnum", "policy_locator"}:
                continue
            cleaned = _sanitize_pipeline_output(child)
            if cleaned is not None:
                clean[key] = cleaned
        return clean
    if isinstance(value, bytes):
        return None
    if isinstance(value, str):
        lowered = value.lower()
        if any(term in lowered for term in _FORBIDDEN_OUTPUT_TERMS):
            return None
    return value


def _empty_result(
    *,
    status: str,
    cache_status: str,
    blockers: Optional[List[str]] = None,
    policy_locator: Optional[Dict[str, Any]] = None,
    company_id: Optional[str] = None,
) -> Dict[str, Any]:
    locator_hash = policy_locator_hash(policy_locator) if policy_locator else None
    return {
        "ok": False,
        "provider": OFFICIAL_POLICY_PROVIDER,
        "document_type": OFFICIAL_POLICY_DOCUMENT_TYPE,
        "document_status": status,
        "cache_status": cache_status,
        "policy_locator_hash": locator_hash,
        "company_id": company_id,
        "evidence_items": [],
        "evidence_count": 0,
        "source_fetch_blocker": blockers or [],
        "source_transport": "unavailable",
        "source_document": OFFICIAL_POLICY_DOCUMENT_SOURCE,
    }


class PolicyDocumentEvidenceService:
    """Coordinates official policy document retrieval, cache and snippets."""

    def __init__(
        self,
        *,
        document_service: Any = None,
        ingestion_service: Any = None,
        docling_parser: Optional[Callable[..., List[Dict[str, Any]]]] = None,
    ) -> None:
        self.document_service = document_service
        self.ingestion_service = ingestion_service
        self.docling_parser = docling_parser

    @staticmethod
    def _docling_fallback_parser(*, file_bytes: bytes, policy_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Use the existing Sanitization/Docling service when configured; never a parallel parser."""
        try:
            from app.core.config import settings

            if not getattr(settings, "DOCLING_SERVICE_URL", None):
                return []
            from app.services.sanitization_service import SanitizationService
        except Exception:  # noqa: BLE001
            return []

        tmp_path = ""
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name
            service = SanitizationService()
            markdown, metadata = service._docling_parse(tmp_path, extract_images=False)
            cleaned = service.post_process_markdown(markdown or "")
            if not cleaned:
                return []
            page_count = metadata.get("pages_count") if isinstance(metadata, dict) else None
            return [
                {
                    "page_number": 1,
                    "content": cleaned,
                    "parser_metadata": {
                        "parser": "docling",
                        "pages_count": page_count,
                        "policy_locator_hash": (policy_metadata or {}).get("policy_locator_hash"),
                    },
                }
            ]
        except Exception as exc:  # noqa: BLE001
            logger.warning("[PolicyDocumentEvidence] existing Docling fallback unavailable: %s", type(exc).__name__)
            return []
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def _document_service(self) -> Any:
        if self.document_service is not None:
            return self.document_service
        from .document_service import get_document_service

        self.document_service = get_document_service()
        return self.document_service

    def _ingestion_service(self) -> Any:
        if self.ingestion_service is not None:
            return self.ingestion_service
        from .ingestion_service import get_ingestion_service

        self.ingestion_service = get_ingestion_service()
        return self.ingestion_service

    async def ensure_official_policy_evidence(
        self,
        *,
        company_id: str,
        policy_locator: Dict[str, Any],
        official_document_candidate: Optional[Dict[str, Any]],
        question: str,
        fetcher: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]],
        agent_id: Optional[str] = None,
        force_refresh: bool = False,
        case_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not policy_locator:
            return _empty_result(status="source_unavailable", cache_status="unavailable", blockers=["policy_locator_required"], company_id=company_id)

        locator_hash = policy_locator_hash(policy_locator)
        doc_service = self._document_service()

        if not force_refresh and hasattr(doc_service, "find_official_policy_document"):
            cached = doc_service.find_official_policy_document(company_id, locator_hash)
            if cached:
                pages = doc_service.load_raw_pages(cached.get("id"), company_id) if hasattr(doc_service, "load_raw_pages") else []
                content_hash = cached.get("content_hash") or (cached.get("metadata") or {}).get("content_hash") or ""
                evidence = extract_policy_document_evidence(
                    pages,
                    question=question,
                    document_id=str(cached.get("id")),
                    company_id=company_id,
                    policy_locator=policy_locator,
                    content_hash=content_hash,
                )
                return self._result(
                    company_id=company_id,
                    policy_locator=policy_locator,
                    document_id=str(cached.get("id")),
                    content_hash=content_hash,
                    cache_status="hit",
                    document_status="evidence_ready" if evidence else "low_confidence",
                    source_transport=(cached.get("metadata") or {}).get("source_transport") or "cache",
                    evidence=evidence,
                    parser_used=(cached.get("metadata") or {}).get("parser_used") or "direct_text",
                    page_count=len(pages) or (cached.get("metadata") or {}).get("page_count"),
                    qdrant_ingested=True,
                    case_id=case_id,
                )

        if not official_document_candidate or not official_document_candidate.get("url"):
            return _empty_result(
                status="source_unavailable",
                cache_status="unavailable",
                blockers=["official_document_url_absent"],
                policy_locator=policy_locator,
                company_id=company_id,
            )

        fetched = await fetcher(official_document_candidate)
        if not fetched or not fetched.get("ok"):
            return _empty_result(
                status="source_fetch_failed",
                cache_status="miss",
                blockers=list(fetched.get("blockers") or fetched.get("source_fetch_blocker") or ["source_fetch_failed"]) if isinstance(fetched, dict) else ["source_fetch_failed"],
                policy_locator=policy_locator,
                company_id=company_id,
            )

        body = fetched.get("body")
        if not isinstance(body, (bytes, bytearray)) or not body:
            return _empty_result(
                status="source_fetch_failed",
                cache_status="miss",
                blockers=["empty_document_body"],
                policy_locator=policy_locator,
                company_id=company_id,
            )
        body_bytes = bytes(body)
        content_hash = hashlib.sha256(body_bytes).hexdigest()
        filename = _safe_filename(policy_locator, content_hash)
        metadata = {
            "provider": OFFICIAL_POLICY_PROVIDER,
            "document_type": OFFICIAL_POLICY_DOCUMENT_TYPE,
            "source_document": OFFICIAL_POLICY_DOCUMENT_SOURCE,
            "source_kind": fetched.get("source_kind") or official_document_candidate.get("source_kind") or "policy_pdf",
            "source_transport": fetched.get("source_transport") or fetched.get("recommended_r1c_transport") or "signed_url_fetch",
            "content_hash": content_hash,
            "policy_locator_hash": locator_hash,
            "sensitivity": "high",
            "scope": "connector",
            "case_id": case_id,
            "parser_used": "direct_text",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        document_id, pages = doc_service.store_official_policy_document(
            file_data=body_bytes,
            filename=filename,
            company_id=company_id,
            file_size=len(body_bytes),
            content_type=fetched.get("content_type") or "application/pdf",
            policy_metadata=metadata,
            agent_id=agent_id,
        )
        evidence = extract_policy_document_evidence(
            pages,
            question=question,
            document_id=str(document_id),
            company_id=company_id,
            policy_locator=policy_locator,
            content_hash=content_hash,
        )
        parser_used = "direct_text"
        document_status = "evidence_ready" if evidence else "low_confidence"

        fallback_parser = self.docling_parser or self._docling_fallback_parser
        if not evidence and fallback_parser:
            document_status = "docling_pending"
            try:
                docling_pages = fallback_parser(file_bytes=body_bytes, policy_metadata=metadata) or []
                evidence = extract_policy_document_evidence(
                    docling_pages,
                    question=question,
                    document_id=str(document_id),
                    company_id=company_id,
                    policy_locator=policy_locator,
                    content_hash=content_hash,
                    extraction_method="docling",
                )
                parser_used = "docling"
                document_status = "evidence_ready" if evidence else "document_not_policy_evidence"
            except Exception as exc:  # noqa: BLE001
                logger.warning("[PolicyDocumentEvidence] Docling fallback failed: %s", type(exc).__name__)
                document_status = "low_confidence"

        qdrant_ingested = False
        try:
            ingestion = self._ingestion_service()
            qdrant_ingested = bool(
                ingestion.process_document(
                    document_id=str(document_id),
                    company_id=company_id,
                    strategy="page",
                    agent_id=agent_id,
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[PolicyDocumentEvidence] ingestion failed: %s", type(exc).__name__)

        cache_status = "refreshed" if force_refresh else "miss"
        return self._result(
            company_id=company_id,
            policy_locator=policy_locator,
            document_id=str(document_id),
            content_hash=content_hash,
            cache_status=cache_status,
            document_status=document_status,
            source_transport=metadata["source_transport"],
            evidence=evidence,
            parser_used=parser_used,
            page_count=len(pages),
            qdrant_ingested=qdrant_ingested,
            case_id=case_id,
        )

    def _result(
        self,
        *,
        company_id: str,
        policy_locator: Dict[str, Any],
        document_id: str,
        content_hash: str,
        cache_status: str,
        document_status: str,
        source_transport: str,
        evidence: List[Dict[str, Any]],
        parser_used: str,
        page_count: Any,
        qdrant_ingested: bool,
        case_id: Optional[str],
    ) -> Dict[str, Any]:
        confidence = _confidence_for_evidence(evidence)
        result = {
            "ok": document_status == "evidence_ready",
            "provider": OFFICIAL_POLICY_PROVIDER,
            "document_type": OFFICIAL_POLICY_DOCUMENT_TYPE,
            "document_status": document_status,
            "cache_status": cache_status,
            "cache_key": policy_document_cache_key(company_id, policy_locator, content_hash),
            "company_id": company_id,
            "policy_locator_hash": policy_locator_hash(policy_locator),
            "document_id": document_id,
            "source_document": OFFICIAL_POLICY_DOCUMENT_SOURCE,
            "source_transport": source_transport,
            "content_hash": content_hash,
            "content_hash_present": bool(content_hash),
            "page_count": page_count,
            "parser_used": parser_used,
            "extraction_confidence": confidence,
            "evidence_items": evidence[:20],
            "evidence_count": len(evidence),
            "qdrant_ingested": qdrant_ingested,
            "case_id": case_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return _sanitize_pipeline_output(result)


def policy_document_evidence_role_view(
    evidence_result: Dict[str, Any],
    *,
    role: str,
    case_id: Optional[str] = None,
    capability_allowed: bool = True,
) -> Dict[str, Any]:
    """Return the allowed DTO for Core, Even or future auxiliaries."""
    if not isinstance(evidence_result, dict):
        return {}
    role_norm = str(role or "").strip().lower()
    if role_norm == "core":
        return dict(evidence_result)
    if role_norm == "even":
        if not case_id:
            return {
                "provider": evidence_result.get("provider"),
                "document_status": evidence_result.get("document_status"),
                "evidence_items": [],
                "reason": "case_id_required",
            }
        items = [
            {
                "page_number": item.get("page_number"),
                "evidence_type": item.get("evidence_type"),
                "evidence_text": item.get("evidence_text"),
                "confidence": item.get("confidence"),
                "source_document": item.get("source_document"),
            }
            for item in evidence_result.get("evidence_items") or []
        ]
        return {
            "provider": evidence_result.get("provider"),
            "document_status": evidence_result.get("document_status"),
            "evidence_items": items,
            "evidence_count": len(items),
            "case_id": case_id,
        }
    if not capability_allowed:
        return {
            "provider": evidence_result.get("provider"),
            "document_status": evidence_result.get("document_status"),
            "evidence_items": [],
            "reason": "capability_required",
        }
    return dict(evidence_result)


_policy_document_evidence_service: Optional[PolicyDocumentEvidenceService] = None


def get_policy_document_evidence_service() -> PolicyDocumentEvidenceService:
    global _policy_document_evidence_service
    if _policy_document_evidence_service is None:
        _policy_document_evidence_service = PolicyDocumentEvidenceService()
    return _policy_document_evidence_service
