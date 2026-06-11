"""
Fundação de escopo de conhecimento (SPEC-003) — apenas helpers PUROS.

NÃO cria motor RAG; reaproveita o RAG do Smith (Qdrant/embeddings/search).
Responsabilidades:
- normalizar o escopo de um documento (tenant/agent/global/...);
- preparar os campos de conhecimento que viajam no payload do Qdrant;
- montar os kwargs de busca de conhecimento GLOBAL (OPT-IN; default desligado).

Regras: global é curado/read-only; segredos/PII NUNCA entram aqui;
documentos antigos sem scope são tratados como 'tenant'. Defaults sempre seguros.
"""
from typing import Any, Dict, List, Optional

# ── Escopos canônicos (SPEC-003 §1) ───────────────────────────────────────────
SCOPE_TENANT = "tenant"
SCOPE_AGENT = "agent"
SCOPE_GLOBAL_AUTOBROKERS = "global_autobrokers"
SCOPE_GLOBAL_CARRIER = "global_carrier"
SCOPE_WORKFLOW = "workflow"
SCOPE_CONNECTOR = "connector"

VALID_SCOPES = {
    SCOPE_TENANT,
    SCOPE_AGENT,
    SCOPE_GLOBAL_AUTOBROKERS,
    SCOPE_GLOBAL_CARRIER,
    SCOPE_WORKFLOW,
    SCOPE_CONNECTOR,
}
GLOBAL_SCOPES = [SCOPE_GLOBAL_AUTOBROKERS, SCOPE_GLOBAL_CARRIER]

# ── Coleções Qdrant ───────────────────────────────────────────────────────────
# A coleção global AINDA NÃO é criada neste batch (ver 41C.2B report §8).
GLOBAL_COLLECTION = "autobrokers_global"


def company_collection(company_id: str) -> str:
    """Mesmo padrão do QdrantService._get_collection_name (mantido por consistência)."""
    return f"company_{str(company_id).replace('-', '_')}"


def normalize_document_scope(agent_id: Optional[str], requested_scope: Optional[str] = None) -> str:
    """Default seguro: 'agent' se houver agent_id; senão 'tenant'. requested_scope só se válido."""
    if requested_scope and requested_scope in VALID_SCOPES:
        return requested_scope
    return SCOPE_AGENT if agent_id else SCOPE_TENANT


# Campos de conhecimento que podem viajar no payload do Qdrant (todos opcionais).
PAYLOAD_KNOWLEDGE_KEYS = [
    "scope",
    "knowledge_class",
    "namespace",
    "version",
    "curation_status",
    "visibility",
    "valid_until",
    "source_hash",
    "carrier_slug",
    "product_slug",
]


def extract_payload_extras(
    source: Optional[Dict[str, Any]], agent_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extrai campos de conhecimento de um dict (metadata do doc ou linha de documents)
    para o payload do Qdrant. Tolerante a vazio. NUNCA inclui conteúdo/segredo/PII.
    `scope` é sempre definido (default tenant/agent).
    """
    src = source or {}
    extras: Dict[str, Any] = {}
    for k in PAYLOAD_KNOWLEDGE_KEYS:
        v = src.get(k)
        if v not in (None, ""):
            extras[k] = v
    if "scope" not in extras:
        extras["scope"] = normalize_document_scope(agent_id, None)
    return extras


def build_global_search_kwargs(
    namespace: Optional[str] = None,
    version: Optional[str] = None,
    carrier_slug: Optional[str] = None,
) -> Dict[str, Any]:
    """
    kwargs para buscar conhecimento GLOBAL via QdrantService.search_similar.
    Coleção global dedicada, sem agent_id, somente curadoria publicada.
    (namespace/version/carrier reservados para filtragem fina no 41C.2C.)
    """
    return {
        "collection_name": GLOBAL_COLLECTION,
        "agent_id": None,
        "include_tenant_wide": False,
        "scope_match": list(GLOBAL_SCOPES),
        "curation_published_only": True,
    }


def merge_rag_results(
    primary: List[Dict[str, Any]], extra: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Une resultados (ex.: tenant/agent + global), dedupe por (document_id, chunk_index),
    mantendo o de maior score. Não loga conteúdo.
    """
    by_key: Dict[str, Dict[str, Any]] = {}
    for r in list(primary or []) + list(extra or []):
        key = f"{r.get('document_id')}::{r.get('chunk_index')}"
        cur = by_key.get(key)
        if cur is None or (r.get("score") or 0) > (cur.get("score") or 0):
            by_key[key] = r
    merged = list(by_key.values())
    merged.sort(key=lambda x: (x.get("rerank_score") or x.get("score") or 0), reverse=True)
    return merged
