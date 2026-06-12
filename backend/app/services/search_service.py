"""
Search Service - Orquestrador de Busca Inteligente (Hybrid RAG Cascade)
VERSÃO CORRIGIDA: Suporte a filtro por agent_id (Multi-Agent)
"""

import logging
import re
import time
import unicodedata
from typing import Any, Dict, List, Optional

from fastembed import SparseTextEmbedding
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from ..core.config import settings
from .qdrant_service import get_qdrant_service
from .rerank_service import get_rerank_service

logger = logging.getLogger(__name__)


# === LEXICAL RESCUE (41C.1.3) ===
# Resgata chunks claramente relevantes que o reranker descartou (ex.: Cohere em
# bypass/erro → sem rerank_score → score=0 → abaixo do THRESH_MIN). Puro, sem I/O,
# sem hardcode de documento/empresa/agente.

# Termos de intenção de base/validação/seguro (sinal forte quando presentes
# tanto na pergunta quanto no conteúdo recuperado).
_RESCUE_INTENT_TERMS = (
    "palavra-chave", "palavra chave", "validacao", "rag", "base",
    "documento", "procedimento", "politica", "apolice", "cobertura",
    "sinistro", "assistencia", "seguradora",
)

# Stopwords PT-BR comuns (descartadas na tokenização do rescue).
_RESCUE_STOPWORDS = {
    "a", "o", "os", "as", "de", "da", "do", "das", "dos", "e", "em",
    "um", "uma", "uns", "umas", "que", "qual", "quais", "com", "para",
    "por", "no", "na", "nos", "nas", "ao", "aos", "se", "sua", "seu",
    "suas", "seus", "meu", "minha", "como", "onde", "quando", "sobre",
    "ser", "tem", "ha", "essa", "esse", "isso", "ja", "the", "of",
    "local", "qual_e",
}


def _rescue_strip_accents(text: str) -> str:
    """Normaliza para minúsculas sem acentos (tolerante)."""
    norm = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(ch for ch in norm if not unicodedata.combining(ch))


def _rescue_tokenize(text: str) -> List[str]:
    """Tokens >=3 chars, sem stopwords, normalizados (mantém hífen/dígitos)."""
    norm = _rescue_strip_accents(text)
    raw = re.findall(r"[a-z0-9][a-z0-9\-]*", norm)
    return [t for t in raw if len(t) >= 3 and t not in _RESCUE_STOPWORDS]


# === SCORE FALLBACK (41C.1.4) ===
# Quando o reranker (Cohere) está ausente/bypass, os resultados não trazem
# 'rerank_score'. Antes isso virava 0 e descartava bons resultados. Aqui usamos
# o score bruto do Qdrant como fallback observável (não inventa relevância).
_SCORE_KEYS = ("rerank_score", "score", "similarity", "qdrant_score")


def _get_effective_score(result: Dict) -> float:
    """Primeiro score numérico disponível (rerank > qdrant > 0). Puro."""
    if not result:
        return 0.0
    for key in _SCORE_KEYS:
        val = result.get(key)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                continue
    return 0.0


def _get_score_source(result: Dict) -> str:
    """Origem do score efetivo: 'rerank' | 'qdrant' | 'fallback_zero'."""
    if not result:
        return "fallback_zero"
    if result.get("rerank_score") is not None:
        return "rerank"
    for key in ("score", "similarity", "qdrant_score"):
        if result.get(key) is not None:
            return "qdrant"
    return "fallback_zero"


def _lexical_rescue_match(query: str, results: List[Dict]) -> bool:
    """
    True quando há correspondência lexical forte entre a pergunta e o conteúdo
    recuperado — usado APENAS quando já existem resultados brutos/rerankeados
    e o score caiu abaixo do threshold. Nunca transforma resultado vazio em match.
    """
    if not results:
        return False

    combined = " ".join(_rescue_strip_accents(r.get("content") or "") for r in results)
    if not combined.strip():
        return False

    q_norm = _rescue_strip_accents(query)
    intent_terms_norm = [_rescue_strip_accents(t) for t in _RESCUE_INTENT_TERMS]

    # 1) Pergunta sobre "palavra-chave de validação" e o chunk contém a mesma expressão.
    if "palavra-chave de validacao" in q_norm and "palavra-chave de validacao" in combined:
        return True

    q_tokens = _rescue_tokenize(query)
    if not q_tokens:
        return False

    matched = [t for t in set(q_tokens) if t in combined]

    # 2) Pelo menos 2 tokens relevantes da pergunta aparecem no conteúdo.
    if len(matched) >= 2:
        return True

    # 3) Termo de intenção presente na pergunta E no conteúdo + ao menos 1 token compartilhado.
    intent_in_query = any(t in q_norm for t in intent_terms_norm)
    intent_in_chunk = any(t in combined for t in intent_terms_norm)
    if intent_in_query and intent_in_chunk and len(matched) >= 1:
        return True

    # 4) Token de código/protocolo/palavra-chave (com dígito, hífen ou longo) presente em ambos.
    code_tokens = [
        t for t in q_tokens
        if any(ch.isdigit() for ch in t) or "-" in t or len(t) >= 8
    ]
    if any(t in combined for t in code_tokens):
        return True

    return False


class SearchService:
    """
    Orquestrador de Busca Inteligente (Hybrid RAG Cascade).
    Fluxo: Hybrid Search (Dense+Sparse) -> Rerank -> Check Score -> (se < 0.80) -> HyDE -> Rerank -> Final Check.

    MULTI-AGENT:
    - Todas as buscas são filtradas por agent_id
    - Cada agente só vê seus próprios documentos
    """

    def __init__(self):

        self.qdrant = get_qdrant_service()
        self.reranker = get_rerank_service()

        # Embeddings para busca vetorial (Dense)
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small", api_key=settings.OPENAI_API_KEY
        )

        # Modelo para busca lexical (Sparse BM25) - Rodando Local
        logger.info("[SearchService] Carregando modelo BM25 local...")
        self.sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
        logger.info("[SearchService] Modelo BM25 carregado.")

    def _track_query_embedding_cost(
        self, query: str, company_id: str = None, agent_id: str = None
    ):
        """Track the cost of embedding a search query."""
        try:
            import tiktoken

            encoder = tiktoken.encoding_for_model("text-embedding-3-small")
            tokens = len(encoder.encode(query))

            from .usage_service import get_usage_service

            usage_service = get_usage_service()
            usage_service.track_cost_sync(
                service_type="rag_query",
                model="text-embedding-3-small",
                input_tokens=tokens,
                output_tokens=0,
                company_id=company_id,
                agent_id=agent_id,
                details={"query_preview": query[:100]},
            )
        except Exception as e:
            logger.warning(f"[Search] Cost tracking failed: {e}")

    def _generate_hyde_doc(self, query: str, company_id: str = None, agent_id: str = None) -> str:
        """Gera documento hipotético para expansão semântica."""
        from ..core.callbacks.cost_callback import CostCallbackHandler

        try:
            # 🔥 Cria callback dinamicamente com IDs para billing correto
            callbacks = []
            if company_id:
                callbacks.append(CostCallbackHandler(
                    service_type="rag_query",
                    company_id=company_id,
                    agent_id=agent_id
                ))

            hyde_llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.7,
                api_key=settings.OPENAI_API_KEY,
                callbacks=callbacks,
            )

            prompt = f"""Você é um especialista técnico. Escreva um parágrafo curto e denso que seria a resposta PERFEITA para a pergunta: "{query}".
            Use terminologia técnica correta. Não responda a pergunta, simule o trecho do documento que conteria a resposta."""
            response = hyde_llm.invoke([HumanMessage(content=prompt)])
            return response.content
        except Exception as e:
            logger.warning(f"[Search] HyDE generation failed: {e}")
            return query

    def _execute_search(
        self,
        company_id: str,
        search_text: str,
        original_query: str,
        agent_id: Optional[str] = None,
        include_global: bool = False,
    ) -> List[Dict]:
        """
        Executa Busca HÍBRIDA (Dense + Sparse) + Rerank Preciso (Top 5).

        Args:
            company_id: ID da empresa
            search_text: Texto para gerar embeddings (pode ser query ou HyDE doc)
            original_query: Query original do usuário (para reranking)
            agent_id: ID do agente para filtrar resultados
        """
        # Track embedding cost
        self._track_query_embedding_cost(search_text, company_id, agent_id)

        # 1. Geração de Vetores (Paralelo)
        dense_vector = self.embeddings.embed_query(search_text)

        try:
            sparse_vector = list(self.sparse_model.embed([search_text]))[0]
        except Exception as e:
            logger.error(f"[Search] Erro ao gerar vetor BM25: {e}")
            sparse_vector = None

        # 2. Busca Híbrida no Qdrant (Recall) - COM FILTRO DE AGENTE
        initial_results = self.qdrant.search_similar(
            company_id=company_id,
            query_embedding=dense_vector,
            sparse_embedding=sparse_vector,
            agent_id=agent_id,
            include_tenant_wide=True,  # vê docs do agente + tenant-wide (nunca de outro agente)
            top_k=20,
            score_threshold=0.0,
        )

        # Conhecimento GLOBAL (opt-in, SPEC-003): coleção dedicada, só curadoria publicada.
        if include_global:
            try:
                from .knowledge_scope import build_global_search_kwargs, merge_rag_results

                global_results = self.qdrant.search_similar(
                    company_id=company_id,
                    query_embedding=dense_vector,
                    sparse_embedding=sparse_vector,
                    top_k=20,
                    score_threshold=0.0,
                    **build_global_search_kwargs(),
                )
                initial_results = merge_rag_results(initial_results, global_results)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[Search] global retrieval ignorado: {type(e).__name__}")

        if not initial_results:
            logger.info(
                f"[Search] Nenhum resultado encontrado para agent_id={agent_id}"
            )
            return []

        # 3. Reranking (Precision)
        reranked = self.reranker.rerank(
            query=original_query,
            docs=initial_results,
            top_k=3,  # Reduzido para economizar tokens
        )
        return reranked

    def smart_search(
        self,
        company_id: str,
        query: str,
        agent_id: Optional[str] = None,
        is_hyde_enabled: bool = True,
        include_global: bool = False,
    ) -> Dict[str, Any]:
        """
        Executa a estratégia de busca em cascata com Híbrido como padrão.

        Args:
            company_id: ID da empresa
            query: Pergunta do usuário
            agent_id: ID do agente para filtrar documentos (OBRIGATÓRIO para multi-agent)
            is_hyde_enabled: Se True, tenta HyDE quando score < threshold. Se False, retorna busca direta.

        Returns:
            Dict com content, chunks, found, search_time_ms, strategy, max_score
        """
        start_time = time.time()

        # Log do contexto de busca
        logger.info(
            f"[Search] smart_search iniciado | company={company_id} | agent={agent_id} | hyde={is_hyde_enabled} | query='{query[:50]}...'"
        )

        # Status do reranker (sem expor chave) — habilita fallback observável.
        reranker_available = self.reranker.is_available()
        _rr_health = self.reranker.health()
        logger.info(
            f"[Search] Reranker status: configured={_rr_health['configured']} "
            f"provider={_rr_health['provider']} status={_rr_health['status']}"
        )
        if not reranker_available:
            logger.info("[Search] Reranker bypass detected; using Qdrant score fallback")

        # Configuração de Thresholds
        THRESH_HYDE = 0.50  # Novo threshold para ativar HyDE (era 0.80)
        THRESH_MIN = 0.40   # Threshold mínimo para considerar resultado válido

        # --- TENTATIVA 1: Hybrid Search ---
        logger.info(f"[Search] Tentativa 1: Híbrida para '{query}'")
        results_std = self._execute_search(company_id, query, query, agent_id=agent_id, include_global=include_global)

        best_score_std = _get_effective_score(results_std[0]) if results_std else 0
        if results_std:
            logger.info(
                f"[Search] Effective score source={_get_score_source(results_std[0])} "
                f"score={best_score_std:.3f}"
            )

        # Se score já é bom OU HyDE está desativado, retorna direto
        if best_score_std >= THRESH_HYDE or not is_hyde_enabled:
            if not is_hyde_enabled:
                logger.info(
                    f"[Search] 🚀 HyDE desativado. Retornando busca direta (score={best_score_std:.3f})"
                )
            else:
                logger.info(
                    f"[Search] ✅ Híbrido score bom ({best_score_std:.3f} >= {THRESH_HYDE}). Retornando direto."
                )

            # Verificar threshold mínimo
            if best_score_std < THRESH_MIN:
                logger.warning(
                    f"[Search] ⚠️ Score ({best_score_std:.3f}) abaixo do mínimo ({THRESH_MIN})."
                )
                # Lexical rescue: chunk claramente relevante descartado por score baixo.
                if _lexical_rescue_match(query, results_std):
                    logger.info(
                        f"[Search] Lexical rescue activated | strategy=hybrid_lexical_rescue | "
                        f"results={len(results_std)} | score={best_score_std:.3f}"
                    )
                    return self._format_response(
                        results_std,
                        time.time() - start_time,
                        "hybrid_lexical_rescue",
                        best_score_std,
                        agent_id,
                        rescue_used=True,
                        reranker_available=reranker_available,
                    )
                logger.info(f"[Search] Lexical rescue not activated | score={best_score_std:.3f}")
                return {
                    "content": "Não encontrei informações suficientes nos documentos internos para responder sua pergunta com segurança.",
                    "chunks": self._build_chunks_metadata(
                        results_std,
                        filtered_reason="below_threshold",
                        reranker_available=reranker_available,
                    ),
                    "found": False,
                    "search_time_ms": int((time.time() - start_time) * 1000),
                    "agent_id": agent_id,
                    "strategy": "hybrid_only",
                    "max_score": best_score_std,
                    "effective_score": best_score_std,
                    "score_source": _get_score_source(results_std[0]) if results_std else "fallback_zero",
                    "reranker_available": reranker_available,
                }

            return self._format_response(
                results_std,
                time.time() - start_time,
                "hybrid_direct",
                best_score_std,
                agent_id,
                reranker_available=reranker_available,
            )

        # --- TENTATIVA 2: HyDE (apenas se habilitado e score baixo) ---
        logger.info(
            f"[Search] Score insuficiente ({best_score_std:.3f} < {THRESH_HYDE}). Tentando HyDE..."
        )
        hyde_doc = self._generate_hyde_doc(query, company_id, agent_id)

        results_hyde = self._execute_search(
            company_id, hyde_doc, query, agent_id=agent_id, include_global=include_global
        )

        best_score_hyde = _get_effective_score(results_hyde[0]) if results_hyde else 0

        # Comparação: Quem ganhou?
        final_results = (
            results_hyde if best_score_hyde > best_score_std else results_std
        )
        final_score = max(best_score_hyde, best_score_std)
        final_strategy = (
            "hyde_hybrid" if best_score_hyde > best_score_std else "hybrid_fallback"
        )

        logger.info(
            f"[Search] Comparação: Direct={best_score_std:.3f} vs HyDE={best_score_hyde:.3f} → Vencedor: {final_strategy}"
        )

        # --- FILTRO FINAL ---
        if final_score < THRESH_MIN:
            logger.warning(
                f"[Search] ⚠️ Falha total. Melhor score ({final_score:.3f}) abaixo do mínimo ({THRESH_MIN})."
            )
            # Lexical rescue: chunk claramente relevante descartado por score baixo.
            if _lexical_rescue_match(query, final_results):
                rescue_strategy = (
                    "hyde_lexical_rescue" if "hyde" in final_strategy else "hybrid_lexical_rescue"
                )
                logger.info(
                    f"[Search] Lexical rescue activated | strategy={rescue_strategy} | "
                    f"results={len(final_results)} | score={final_score:.3f}"
                )
                return self._format_response(
                    final_results,
                    time.time() - start_time,
                    rescue_strategy,
                    final_score,
                    agent_id,
                    rescue_used=True,
                    reranker_available=reranker_available,
                )
            logger.info(f"[Search] Lexical rescue not activated | score={final_score:.3f}")
            return {
                "content": "Não encontrei informações suficientes nos documentos internos para responder sua pergunta com segurança.",
                "chunks": self._build_chunks_metadata(
                    final_results,
                    filtered_reason="below_threshold",
                    reranker_available=reranker_available,
                ),
                "found": False,
                "search_time_ms": int((time.time() - start_time) * 1000),
                "agent_id": agent_id,
                "strategy": final_strategy,
                "max_score": final_score,
                "effective_score": final_score,
                "score_source": _get_score_source(final_results[0]) if final_results else "fallback_zero",
                "reranker_available": reranker_available,
            }

        return self._format_response(
            final_results,
            time.time() - start_time,
            final_strategy,
            final_score,
            agent_id,
            reranker_available=reranker_available,
        )

    def _build_chunks_metadata(
        self,
        results: List[Dict],
        filtered_reason: str = None,
        reranker_available: bool = True,
    ) -> List[Dict]:
        """
        Constrói metadados dos chunks para logging/debug.
        Sempre retorna os chunks, mesmo quando filtrados por threshold.
        Isso garante que os conversation_logs contenham os chunks para diagnóstico.
        """
        chunks = []
        for res in results:
            score = _get_effective_score(res)
            chunks.append({
                "chunk_id": res.get("document_id"),
                "agent_id": res.get("agent_id"),
                "score": round(score, 3),
                "score_source": _get_score_source(res),
                "reranker_available": reranker_available,
                "content_preview": res.get("content", "")[:200] + "...",
                "metadata": res.get("metadata", {}),
                "used_in_context": False,
                "filtered_reason": filtered_reason,
            })
        return chunks

    def _format_response(
        self,
        results: List[Dict],
        duration: float,
        strategy: str,
        top_score: float,
        agent_id: Optional[str] = None,
        rescue_used: bool = False,
        reranker_available: bool = True,
    ) -> Dict:
        """
        Formata a resposta aplicando Filtro Dinâmico Rigoroso.

        rescue_used: quando True (lexical rescue, 41C.1.3), força a inclusão do
        top result no contexto mesmo com score abaixo do mínimo, e marca o chunk.
        reranker_available / score_source: observabilidade do fallback (41C.1.4).
        """
        chunks_metadata = []
        content_parts = []

        MIN_RELEVANCE = 0.30

        results.sort(key=_get_effective_score, reverse=True)

        top_score_source = _get_score_source(results[0]) if results else "fallback_zero"

        valid_chunks_count = 0
        for i, res in enumerate(results):
            score = _get_effective_score(res)
            score_source = _get_score_source(res)
            doc_name = res.get("metadata", {}).get("document_name", "Doc")
            content = res.get("content", "")

            is_relevant = score >= MIN_RELEVANCE
            is_fallback = i == 0 and top_score < MIN_RELEVANCE
            force_rescue = rescue_used and i == 0  # garante o top result no contexto

            include_in_context = is_relevant or is_fallback or force_rescue

            if include_in_context:
                quality_tag = (
                    "🟢 Alta"
                    if score > 0.7
                    else "🟡 Média"
                    if score > 0.4
                    else "🔴 Baixa"
                )

                header = f"[{doc_name} | Score: {score:.2f} ({quality_tag})]"
                content_parts.append(f"{header}:\n{content}")

                if is_relevant:
                    valid_chunks_count += 1

            chunk_meta = {
                "chunk_id": res.get("document_id"),
                "agent_id": res.get("agent_id"),
                "score": round(score, 3),
                "score_source": score_source,
                "reranker_available": reranker_available,
                "content_preview": content[:100] + "...",
                "metadata": res.get("metadata", {}),
                "used_in_context": include_in_context,
            }
            if force_rescue:
                chunk_meta["rescue_used"] = True
                chunk_meta["rescue_reason"] = "lexical_match_below_threshold"
            chunks_metadata.append(chunk_meta)

        final_content = "\n\n---\n\n".join(content_parts)

        if valid_chunks_count == 0 and results:
            final_content = (
                f"⚠️ **AVISO DE SISTEMA:** Os documentos encontrados têm baixa relevância (Score < {MIN_RELEVANCE}). Use com cautela.\n\n"
                + final_content
            )

        response = {
            "content": final_content,
            "chunks": chunks_metadata,
            "found": True,
            "search_time_ms": int(duration * 1000),
            "strategy": strategy,
            "max_score": top_score,
            "effective_score": top_score,
            "score_source": top_score_source,
            "reranker_available": reranker_available,
            "valid_chunks_count": valid_chunks_count,
            "agent_id": agent_id,
        }
        if rescue_used:
            response["rescue_used"] = True
        return response


# Singleton
_search_service = None


def get_search_service():
    global _search_service
    if _search_service is None:
        _search_service = SearchService()
    return _search_service
