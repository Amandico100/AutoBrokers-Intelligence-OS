import logging
from typing import Any, Dict, List

import cohere

from ..core.config import settings

logger = logging.getLogger(__name__)


class RerankService:
    """
    Serviço de Re-Ranking usando Cohere (SOTA).
    Refina a precisão da busca vetorial usando modelos Cross-Encoder.
    """

    #: O papel do Model Router que reordena o RAG (SPEC-116 U8).
    PAPEL = "rerank"

    def __init__(self, *, modelo: str = None, cliente=None):
        """PONTO DE INJEÇÃO: `modelo` fixa o braço; `cliente` é qualquer objeto
        com `.rerank(model=, query=, documents=, top_n=)` (dublê da bancada)."""
        self.api_key = getattr(settings, "COHERE_API_KEY", None)
        self.client = cliente
        self._modelo_fixo = modelo

        if self.client is None and self.api_key:
            try:
                self.client = cohere.Client(self.api_key)
                logger.info("✅ RerankService conectado ao Cohere (papel rerank)")
            except Exception as e:
                logger.error(f"❌ Erro ao inicializar Cohere Client: {e}")
        elif self.client is None:
            logger.warning(
                "⚠️ COHERE_API_KEY não configurada. Reranking será ignorado (Bypass)."
            )

    @property
    def model(self) -> str:
        """O id da ROTA do papel `rerank` (lido a cada uso: a troca vale sem
        reiniciar). 🔴 SPEC-116 U8: era literal. ⛔ Sem rota → ModeloNaoResolvido."""
        if self._modelo_fixo:
            return self._modelo_fixo
        from app.factories.model_policy import resolver

        return resolver(self.PAPEL).model

    def _registrar_uso(self, response, modelo: str, *, n_docs: int, company_id=None,
                       agent_id=None) -> None:
        """Ledger do rerank (📊 23/09/2026: ZERO registro — EVIDENCIAS/01 (e)#5).

        Cohere cobra por "search unit" (`meta.billed_units.search_units`). O
        catálogo tem o rerank com preço 0/0 = DESCONHECIDO: a linha sai com custo
        nulo e `preco_desconhecido`, nunca como se fosse de graça.
        """
        try:
            unidades = None
            meta = getattr(response, "meta", None)
            cobradas = getattr(meta, "billed_units", None) if meta is not None else None
            if cobradas is not None:
                unidades = getattr(cobradas, "search_units", None)
            from .usage_service import get_usage_service

            get_usage_service().track_cost_sync(
                service_type="rerank",
                model=modelo,
                input_tokens=int(unidades or 1),
                output_tokens=0,
                company_id=company_id,
                agent_id=agent_id,
                details={"papel": self.PAPEL, "modelo_resolvido": modelo,
                         "search_units": unidades, "documentos": n_docs},
            )
        except Exception as e:  # noqa: BLE001 — o ledger nunca derruba a busca
            logger.warning(f"[Rerank] uso não registrado: {type(e).__name__}")

    def is_available(self) -> bool:
        """True se o cliente Cohere está pronto (sem chamada pesada)."""
        return self.client is not None

    def health(self) -> Dict[str, Any]:
        """
        Status leve do reranker (sem expor chave, sem chamada à API).
        safe_to_run é sempre True: o SearchService tem fallback de score do
        Qdrant + lexical rescue, então a ausência do reranker não quebra o RAG.
        """
        if not self.api_key:
            return {
                "configured": False,
                "provider": "none",
                "status": "missing_key",
                "safe_to_run": True,
            }
        if self.client is None:
            return {
                "configured": True,
                "provider": "fallback",
                "status": "error",
                "safe_to_run": True,
            }
        return {
            "configured": True,
            "provider": "cohere",
            "status": "ok",
            "safe_to_run": True,
        }

    def rerank(
        self, query: str, docs: List[Dict[str, Any]], top_k: int = 3,
        *, company_id: str = None, agent_id: str = None,
    ) -> List[Dict[str, Any]]:
        """
        Reordena os documentos baseados na relevância semântica real.

        Args:
            query: Pergunta do usuário.
            docs: Lista de chunks retornados pelo Qdrant (deve conter 'content').
            top_k: Número de documentos para retornar após o filtro.
        """
        if not self.client or not docs:
            return docs[:top_k]  # Fallback (Pass-through)

        # Prepara documentos para o formato do Cohere (Lista de strings)
        # Mapeamos o índice para recuperar o metadado original depois
        docs_content = [d.get("content", "") for d in docs]

        try:
            # Chamada API Cohere
            modelo = self.model
            response = self.client.rerank(
                model=modelo, query=query, documents=docs_content, top_n=top_k
            )
            self._registrar_uso(response, modelo, n_docs=len(docs_content),
                                company_id=company_id, agent_id=agent_id)

            # Reconstrói a lista ordenada com os scores de relevância
            final_docs = []
            for result in response.results:
                # result.index aponta para a posição na lista original 'docs'
                original_doc = docs[result.index]

                # Injetamos o score de relevância do Cohere (muito mais preciso que o cosseno)
                original_doc["rerank_score"] = result.relevance_score
                final_docs.append(original_doc)

            return final_docs

        except Exception as e:
            logger.error(f"⚠️ Falha no Reranking Cohere: {e}. Usando ordem original.")
            return docs[:top_k]  # Fallback em caso de erro de API


# Singleton
_rerank_service = None


def get_rerank_service():
    global _rerank_service
    if _rerank_service is None:
        _rerank_service = RerankService()
    return _rerank_service
