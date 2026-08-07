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

# ── Escopos canônicos (SPEC-003 §1 + SPEC-044 pessoal) ────────────────────────
SCOPE_TENANT = "tenant"
SCOPE_AGENT = "agent"
SCOPE_PERSONAL = "personal"  # SPEC-044: documento do USUÁRIO — só o dono vê
SCOPE_GLOBAL_AUTOBROKERS = "global_autobrokers"
SCOPE_GLOBAL_CARRIER = "global_carrier"
SCOPE_WORKFLOW = "workflow"
SCOPE_CONNECTOR = "connector"

VALID_SCOPES = {
    SCOPE_TENANT,
    SCOPE_AGENT,
    SCOPE_PERSONAL,
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
    "owner_user_id",  # SPEC-044: dono do documento pessoal (scope=personal)
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


def build_personal_search_kwargs(user_id: str) -> Dict[str, Any]:
    """SPEC-044 — kwargs p/ buscar SÓ os documentos pessoais do usuário da
    sessão (scope=personal + owner_user_id). Sem user_id não há busca pessoal
    (o runtime de atendimento nunca passa user → nunca vê doc pessoal)."""
    return {
        "agent_id": None,
        "include_tenant_wide": False,
        "scope_match": [SCOPE_PERSONAL],
        "owner_user_id": str(user_id),
    }


def seguradora_da_pergunta(texto: str) -> Optional[str]:
    """De qual seguradora esta pergunta fala? `None` quando não fala de nenhuma.

    🔴 REUSA O DICIONÁRIO QUE JÁ EXISTE — de propósito.
    ==================================================
    `corridor_playbooks._INSURER_ALIASES` é a única lista de apelidos de
    seguradora do sistema, e `normalize_insurer_key` é a única tradução. Um
    segundo dicionário aqui daria, no dia em que alguém acrescentasse uma
    companhia num só deles, uma pergunta reconhecida na indexação e ignorada na
    busca — o pior tipo de divergência, porque não dá erro.

    `None` é resposta comum e correta: *"como funciona vistoria complementar?"*
    não fala de companhia nenhuma, e aí TODA carta responde, como sempre foi.

    Conservador por escolha: na dúvida, devolve `None`. Errar para "não filtrar"
    devolve o comportamento antigo; errar para "filtrar pela companhia errada"
    esconde a resposta certa e o agente responde com a carta de outra.
    """
    alvo = str(texto or "").strip().lower()
    if not alvo:
        return None
    try:
        from app.services.corridor_playbooks import _INSURER_ALIASES
    except Exception:  # noqa: BLE001 — sem o dicionário, não filtra
        return None

    achadas = set()
    for apelido, chave in _INSURER_ALIASES.items():
        apelido = str(apelido or "").strip().lower()
        # Apelido curto ("azul", "alfa") precisa de fronteira de palavra, senão
        # "azulejo" viraria a seguradora Azul e a pergunta sobre vidro
        # residencial passaria a ser filtrada por uma companhia de auto.
        if len(apelido) < 6:
            import re as _re
            if _re.search(rf"\b{_re.escape(apelido)}\b", alvo):
                achadas.add(chave)
        elif apelido in alvo:
            achadas.add(chave)

    # Duas companhias na mesma pergunta ("a Porto cobre como a HDI?") é
    # comparação: filtrar por uma esconderia a outra. Sem filtro, as duas
    # respondem — que é o que a pergunta pede.
    return achadas.pop() if len(achadas) == 1 else None


def build_global_search_kwargs(
    namespace: Optional[str] = None,
    version: Optional[str] = None,
    carrier_slug: Optional[str] = None,
) -> Dict[str, Any]:
    """
    kwargs para buscar conhecimento GLOBAL via QdrantService.search_similar.
    Coleção global dedicada, sem agent_id, somente curadoria publicada.

    🔴 `carrier_slug` ERA ACEITO E JOGADO FORA.
    ==========================================
    Por muito tempo esta função declarou os três parâmetros e devolveu um dict
    sem nenhum deles — o docstring dizia *"reservados para filtragem fina"*, e
    quem lia a assinatura concluía que a filtragem existia.

    O preço, medido em 07/08/2026: as cartas guardam `insurer_key` com 📊 zero
    nulos em `ramo` e `category`, e a busca não usava nada disso. Uma pergunta
    sobre a Porto podia ser respondida com a regra da Allianz — 608 cartas
    dela disputando com 361 da Porto, sem nada registrar a troca.

    Agora `carrier_slug` viaja. `namespace` e `version` continuam reservados, e
    isso está dito aqui em vez de prometido na assinatura.
    """
    kwargs = {
        "collection_name": GLOBAL_COLLECTION,
        "agent_id": None,
        "include_tenant_wide": False,
        "scope_match": list(GLOBAL_SCOPES),
        "curation_published_only": True,
    }
    if (carrier_slug or "").strip():
        kwargs["carrier_slug"] = str(carrier_slug).strip().lower()
    return kwargs


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
