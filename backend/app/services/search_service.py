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


# === SCORE FALLBACK (41C.1.4) + CONSERTO DE UNIDADE (P0 05/08/2026) ===
#
# A AUTÓPSIA
# ----------
# O 41C.1.4 corrigiu o "zero falso" (sem Cohere, `rerank_score` sumia e o score
# virava 0) mandando usar "o primeiro score numérico disponível". A intenção,
# escrita no próprio relatório 41C.1.3 §8, era usar o score DENSO do Qdrant.
# O que o código passou a pegar foi o campo `score` — que na busca híbrida NÃO
# é o denso: é o score de RRF da fusão.
#
# 📊 medido em produção (05/08/2026, GET /documents/rag-health + leitura de
#    search_service/qdrant_service):
#      reranker: {"configured": false, "provider": "none", "status": "missing_key"}
#      busca:    FusionQuery(fusion=Fusion.RRF)  → score = Σ 1/(k + posição)
#      melhor caso aritmético com k=60: 1/61 + 1/61 = 0,0328
#      observado no topo das buscas reais:      ~0,02
#      cortes aplicados a esse número:  0,50 / 0,40 / 0,30
#
# 0,0328 nunca alcança 0,40. O gate reprovava TUDO, sempre, e 10.818 cartas
# ficaram intactas e invisíveis. Erro de UNIDADE, não de calibragem: os cortes
# estavam certos para a escala da Cohere (0..1) e foram aplicados à escala do
# RRF (0..0,033) — comparar metro com quilômetro.
#
# O CONSERTO QUE **NÃO** SERVIA
# -----------------------------
# Baixar o corte para 0,02, ou normalizar o RRF por 2/(k+1) e cortar em 0..1.
# Os dois fazem o mesmo estrago: **o RRF não mede relevância, mede concordância
# de posição.** Quem está em 1º nas duas listas tira ~0,0328 sendo a resposta
# perfeita OU sendo lixo — porque alguém sempre está em 1º, mesmo quando o
# acervo não tem a resposta. Um corte nessa escala aprova sempre, e um guarda
# que não tem como falhar não guarda nada (CLAUDE.md §9.3).
#
# O CONSERTO
# ----------
# Separar duas perguntas que o código tratava como uma só:
#
#   ORDEM      — "qual vem primeiro?"  → RRF (ou o reranker). É o que a fusão
#                faz bem: junta denso e BM25 sem precisar de unidade comum.
#   RELEVÂNCIA — "isto responde?"      → COSSENO (ou o reranker). Escala 0..1
#                absoluta: não depende de quem mais está na lista, então um
#                chunk ruim continua ruim mesmo sendo o melhor da rodada.
#
# O cosseno já existia — morria dentro do servidor, porque a FusionQuery só
# devolve o score fundido. `qdrant_service._dense_cosine_for_points` agora o
# traz de volta em `dense_score`, e cada resultado declara sua unidade em
# `score_scale`. Os cortes passaram a ser POR ESCALA: nenhum número é mais
# comparado com outro de unidade diferente.
_SCORE_KEYS = ("rerank_score", "dense_score", "score", "similarity", "qdrant_score")

# Unidades possíveis de um score. Só as duas primeiras decidem relevância.
SCALE_RERANK = "rerank"  # Cohere cross-encoder, 0..1
SCALE_COSINE = "cosine"  # similaridade densa, 0..1
SCALE_RRF = "rrf"  # rank fusion, ~0..0,033 — ordena, não afere
SCALE_NONE = "none"  # nada pontuou

# Confiabilidade da escala como medida de RELEVÂNCIA (maior = mais confiável).
# Serve para escolher entre dois candidatos sem comparar unidades diferentes.
_SCALE_RANK = {SCALE_RERANK: 3, SCALE_COSINE: 2, SCALE_RRF: 1, SCALE_NONE: 0}


def _env_float(name: str, default: float) -> float:
    """Corte calibrável por ambiente, sem deploy de código. Valor inválido → default."""
    import os as _os

    raw = (_os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw.replace(",", "."))
    except (TypeError, ValueError):
        logger.warning(f"[Search] {name} inválido; usando default {default}")
        return default


# Cortes POR ESCALA. Cada linha só é aplicada a números da sua própria unidade.
#
# rerank (0..1): 📊 valores originais, calibrados para rerank-multilingual-v3.0.
#   Preservados byte a byte — quando a COHERE_API_KEY entrar, o caminho dela
#   volta a valer exatamente como antes, sem regressão.
#
# cosine (0..1): 💭 ilustrativo/inferido, NÃO medido neste acervo. Base:
#   text-embedding-3-small devolve vetores normalizados e uma distribuição
#   comprimida — pares sem relação ficam bem abaixo de ~0,15 e pergunta/trecho
#   que responde costuma passar de ~0,30. 0,28 cai na banda de separação, com
#   viés deliberado a favor de responder: o falso negativo é o P0 que estamos
#   consertando, e o falso positivo ainda tem duas redes depois dele (o AVISO
#   DE SISTEMA de baixa relevância e o próprio modelo, que pode recusar).
#   ⚠️ Calibrar com dado real via POST /documents/rag-debug, que agora devolve
#   `score_source=dense_cosine` e o cosseno em `effective_score`: rode ~10
#   perguntas com resposta e ~10 sem, e ajuste pelas envs abaixo.
#
# rrf: os cortes antigos, DE PROPÓSITO. Nesta escala nada os alcança, e é o que
#   queremos: sem cosseno e sem reranker o sistema não tem como aferir
#   relevância, então ele NÃO afirma que achou — delega ao lexical rescue
#   (41C.1.3), que é o comportamento que segura o produto hoje. Abstenção
#   declarada, não guarda quebrado.
_THRESHOLDS_BY_SCALE = {
    SCALE_RERANK: {"hyde": 0.50, "min": 0.40, "relevance": 0.30},
    SCALE_COSINE: {
        "hyde": _env_float("RAG_COSINE_THRESH_HYDE", 0.45),
        "min": _env_float("RAG_COSINE_THRESH_MIN", 0.28),
        "relevance": _env_float("RAG_COSINE_MIN_RELEVANCE", 0.28),
    },
    SCALE_RRF: {"hyde": 0.50, "min": 0.40, "relevance": 0.30},
    SCALE_NONE: {"hyde": 0.50, "min": 0.40, "relevance": 0.30},
}


# Faixas do rótulo de qualidade (alta, média) que vai NO PROMPT do modelo.
# Também são por escala: um cosseno de 0,35 é resultado bom, mas seria rotulado
# "🔴 Baixa" pela régua da Cohere — e o modelo recusaria responder por causa do
# rótulo, não do conteúdo. A linha do rerank é a original, intocada.
_QUALITY_BANDS = {
    SCALE_RERANK: (0.70, 0.40),
    SCALE_COSINE: (0.50, 0.28),
    SCALE_RRF: (0.70, 0.40),
    SCALE_NONE: (0.70, 0.40),
}


def _get_score_scale(result: Dict) -> str:
    """
    A unidade do score que vamos usar como RELEVÂNCIA — na mesma ordem de
    preferência de `_get_effective_score`. Puro.
    """
    if not result:
        return SCALE_NONE
    if result.get("rerank_score") is not None:
        return SCALE_RERANK
    if result.get("dense_score") is not None:
        return SCALE_COSINE
    for key in ("score", "similarity", "qdrant_score"):
        if result.get(key) is not None:
            # Sem `score_scale` declarado, o histórico é busca densa (cosseno).
            return SCALE_RRF if result.get("score_scale") == SCALE_RRF else SCALE_COSINE
    return SCALE_NONE


def _thresholds_for(scale: str) -> Dict[str, float]:
    """Os cortes da unidade certa. Escala desconhecida → os cortes antigos."""
    return _THRESHOLDS_BY_SCALE.get(scale, _THRESHOLDS_BY_SCALE[SCALE_NONE])


def _get_effective_score(result: Dict) -> float:
    """
    Score de RELEVÂNCIA: rerank > cosseno denso > score bruto > 0. Puro.

    Sempre leia junto com `_get_score_scale()`: o número só significa alguma
    coisa dentro da sua unidade. Comparar dois destes sem conferir a escala foi
    exatamente o defeito de 05/08/2026.
    """
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


def _get_ranking_score(result: Dict) -> float:
    """
    Score de ORDEM: rerank > score bruto (RRF na híbrida). Puro.

    Separado de propósito do de relevância. Ordenar pelo cosseno jogaria fora o
    BM25 que a fusão embutiu no RRF — e é o BM25 quem acha código de protocolo,
    número de apólice e nome próprio, justo o que o denso erra.
    """
    if not result:
        return 0.0
    for key in ("rerank_score", "score", "dense_score", "similarity", "qdrant_score"):
        val = result.get(key)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                continue
    return 0.0


def _get_score_source(result: Dict) -> str:
    """
    Origem do score efetivo — agora diz também a ESCALA usada, que é o que
    faltava para enxergar o defeito no log:
    'rerank' | 'dense_cosine' | 'qdrant_cosine' | 'qdrant_rrf' | 'fallback_zero'.
    """
    if not result:
        return "fallback_zero"
    if result.get("rerank_score") is not None:
        return "rerank"
    if result.get("dense_score") is not None:
        return "dense_cosine"
    for key in ("score", "similarity", "qdrant_score"):
        if result.get(key) is not None:
            return "qdrant_rrf" if result.get("score_scale") == SCALE_RRF else "qdrant_cosine"
    return "fallback_zero"


def _contar_por_faixa(results: List[Dict]) -> Dict[str, int]:
    """Quantos resultados de cada namespace — só para o log. Puro."""
    contagem: Dict[str, int] = {}
    for r in results or []:
        faixa = str((r or {}).get("namespace") or "local")
        contagem[faixa] = contagem.get(faixa, 0) + 1
    return contagem


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
        user_id: Optional[str] = None,  # SPEC-044: habilita a busca PESSOAL do usuário
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
        # SPEC-044: a busca padrão EXCLUI docs pessoais (scope=personal) —
        # documento pessoal de um usuário jamais aparece para outro/atendimento.
        initial_results = self.qdrant.search_similar(
            company_id=company_id,
            query_embedding=dense_vector,
            sparse_embedding=sparse_vector,
            agent_id=agent_id,
            include_tenant_wide=True,  # vê docs do agente + tenant-wide (nunca de outro agente)
            exclude_metadata_document_types=["official_policy_document"],
            exclude_scopes=["personal"],
            top_k=20,
            score_threshold=0.0,
        )

        # SPEC-044: busca PESSOAL — só quando há usuário de dashboard na
        # requisição (atendimento nunca passa user_id → nunca vê doc pessoal).
        if user_id:
            try:
                from .knowledge_scope import build_personal_search_kwargs, merge_rag_results

                personal_results = self.qdrant.search_similar(
                    company_id=company_id,
                    query_embedding=dense_vector,
                    sparse_embedding=sparse_vector,
                    top_k=10,
                    score_threshold=0.0,
                    **build_personal_search_kwargs(user_id),
                )
                initial_results = merge_rag_results(initial_results, personal_results)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[Search] personal retrieval ignorado: {type(e).__name__}")

        # Conhecimento GLOBAL (opt-in, SPEC-003): coleção dedicada, só curadoria publicada.
        # SPEC-034 Onda 3: KNOWLEDGE_GLOBAL_SEARCH=1 liga a busca global para todos
        # os agentes (fail-safe: coleção ausente/erro é ignorado sem derrubar a busca).
        import os as _os

        # SPEC-040 Onda 2: default LIGADO — a coleção global agora é populada
        # pelo seed automático (global_knowledge_seed). Desligável via env =0.
        if include_global or _os.getenv("KNOWLEDGE_GLOBAL_SEARCH", "1").strip() == "1":
            try:
                from .knowledge_scope import (
                    ORCAMENTO_GLOBAL,
                    build_global_search_kwargs,
                    faceta_da_pergunta,
                    merge_rag_results,
                    seguradora_da_pergunta,
                    temas_da_pergunta,
                )

                # A pergunta diz de qual companhia se trata? Então a regra de
                # OUTRA companhia não pode responder por ela. Ver
                # `_filtro_de_seguradora`: "desta OU sem seguradora", nunca "só
                # desta" — 📊 80,6% das cartas são fato genérico de mercado e
                # continuam respondendo tudo.
                da_pergunta = seguradora_da_pergunta(original_query)

                # E a pergunta pede uma FACETA ou um TEMA? SPEC-072 Bloco 1,
                # fechando P-142 e P-177: os dois rótulos tinham escritor e
                # nenhum leitor. Mesma regra de dois braços — 📊 12.534 cartas
                # não têm faceta e 4.083 não têm tema, e nenhuma pode sumir.
                #
                # ⚠️ As duas são conservadoras de propósito e reconhecem UM valor
                # cada (`documento` / `documentacao`). O porquê está em
                # `knowledge_scope._APELIDOS_DE_FACETA`, e resume-se a isto:
                # `escopo` e `exclusao` são um PAR, e filtrar por um esconde o
                # outro — que é o oposto do que a faceta existe para fazer.
                faceta_pedida = faceta_da_pergunta(original_query)
                temas_pedidos = temas_da_pergunta(original_query)

                # 🔴 UMA BUSCA POR FAIXA — SPEC-070 §6.
                #
                # Era UMA busca de top_k=20 sobre o índice global inteiro. 📊 Em
                # 08/08/2026 esse índice tem 12.063 cartas destiladas e 11.409
                # trechos de condição geral, e as duas populações disputavam as
                # mesmas vagas. A disputa não era justa: o BM25 normaliza por
                # comprimento, e uma carta de 186 caracteres vence um trecho de
                # contrato de 1.000 quase toda vez que o termo casa nos dois.
                #
                # Agora cada faixa tem orçamento próprio. É o MESMO embedding
                # (gerado uma vez, acima) e o MESMO `search_similar` — só o
                # filtro muda. Não há segundo caminho de busca: CLAUDE.md §5.
                for rotulo, faixa, cota in ORCAMENTO_GLOBAL:
                    faixa_results = self.qdrant.search_similar(
                        company_id=company_id,
                        query_embedding=dense_vector,
                        sparse_embedding=sparse_vector,
                        top_k=cota,
                        score_threshold=0.0,
                        **build_global_search_kwargs(
                            carrier_slug=da_pergunta, namespace=faixa,
                            faceta=faceta_pedida, temas=temas_pedidos),
                    )
                    logger.info(
                        f"[Search] faixa global '{rotulo}' ({'+'.join(faixa)}): "
                        f"{len(faixa_results)}/{cota} candidatos"
                    )
                    initial_results = merge_rag_results(initial_results, faixa_results)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[Search] global retrieval ignorado: {type(e).__name__}")

            # SPEC-054 Bloco B / SPEC-052 Lote 1 — CAMINHO GLOBAL ÚNICO.
            #
            # Existia aqui um SEGUNDO caminho de recuperação global que lia a
            # coleção `company_<GLOBAL_KNOWLEDGE_COMPANY_ID>` com
            # `include_tenant_wide=True` e SEM os filtros de curadoria,
            # validade, namespace, audience e visibility aplicados por
            # `build_global_search_kwargs()`.
            #
            # Na prática isso permitia que conteúdo NÃO publicado entrasse no
            # runtime por uma porta lateral. A SPEC-052 §7.1 determina que
            # `autobrokers_global` é a ÚNICA coleção global recuperável.
            #
            # A empresa técnica "AutoBrokers Global Knowledge" permanece como
            # sala administrativa da biblioteca (upload e curadoria pela mesma
            # UI). Ela NÃO é um segundo RAG. O que ela publica chega ao runtime
            # exclusivamente por `autobrokers_global`.
            #
            # `GLOBAL_KNOWLEDGE_COMPANY_ID` continua válido para ESCRITA/rótulo
            # (global_knowledge_seed, attendance_distiller, agent_council).
            # Proibido reintroduzir leitura por essa via.

        if not initial_results:
            logger.info(
                f"[Search] Nenhum resultado encontrado para agent_id={agent_id}"
            )
            return []

        # 3. Reranking (ORDEM) + orçamento por faixa (VAGAS) — SPEC-070 §6.
        #
        # 🔴 POR QUE O `top_k=3` SAIU DAQUI.
        # =================================
        # A linha era `top_k=3,  # Reduzido para economizar tokens` — e fazia
        # DUAS coisas ao mesmo tempo: ordenar e cortar. Com a chave da Cohere
        # ausente (📊 é o estado de hoje), `rerank()` vira `docs[:top_k]`:
        # nenhuma reordenação, só truncagem dos 3 primeiros de uma fusão RRF
        # que — como este mesmo arquivo documenta 400 linhas acima — "não mede
        # relevância, mede concordância de posição".
        #
        # Então separar as buscas por namespace e continuar cortando os 3
        # melhores de uma lista só devolveria o problema inteiro: o RRF de duas
        # buscas distintas não é comparável, e a carta curta voltaria a ganhar
        # todas as vagas. O orçamento tem de sobreviver ATÉ a vaga final.
        #
        # Agora são dois passos com nomes distintos:
        #   rerank    ORDENA a lista inteira (com Cohere: relevância real;
        #             sem ela: pass-through, a ordem que já veio do merge)
        #   cota      escolhe as VAGAS respeitando o orçamento de cada faixa
        #
        # 📊 A CONTA DAS VAGAS (08/08/2026)
        # --------------------------------
        #   carta publicada  186 chars de média (n=12.063, mediana 186, p90 260)
        #   trecho normativo até 1.000 chars (insurance_corpus.py:213)
        #   3 vagas, pior caso (tudo carta):                    ~810 chars
        #   `context_assembly.ORCAMENTO_TOTAL` declarado:      14.000 chars
        #   `TETO_POR_FONTE["normativo"]` sozinho:              5.500 chars
        #
        # O sistema orçava 14.000 e entregava 810. As cotas atuais entregam, no
        # pior caso, ~6.060 chars — ainda abaixo do teto declarado, e com o
        # contrato garantido na mesa. Ajustável em `knowledge_scope.COTA_FINAL`.
        #
        # ⚠️ Cota governa CANDIDATURA, não inclusão: `_format_response` continua
        # medindo cada chunk pelo corte de relevância da sua escala. Vaga
        # reservada não promove chunk ruim — só impede que chunk bom seja
        # espremido para fora antes de ser medido.
        from .knowledge_scope import selecionar_com_cota

        ordenados = self.reranker.rerank(
            query=original_query,
            docs=initial_results,
            top_k=len(initial_results),  # ORDENAR tudo; quem corta é a cota
        )
        escolhidos = selecionar_com_cota(ordenados)
        logger.info(
            f"[Search] corte final: {len(initial_results)} candidatos → "
            f"{len(escolhidos)} vagas | faixas="
            + ", ".join(
                f"{k}:{v}" for k, v in sorted(_contar_por_faixa(escolhidos).items())
            )
        )
        return escolhidos

    def smart_search(
        self,
        company_id: str,
        query: str,
        agent_id: Optional[str] = None,
        is_hyde_enabled: bool = True,
        include_global: bool = False,
        user_id: Optional[str] = None,  # SPEC-044: busca pessoal do usuário da sessão
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

        # --- TENTATIVA 1: Hybrid Search ---
        logger.info(f"[Search] Tentativa 1: Híbrida para '{query}'")
        results_std = self._execute_search(company_id, query, query, agent_id=agent_id, include_global=include_global, user_id=user_id)

        best_score_std = _get_effective_score(results_std[0]) if results_std else 0

        # Os cortes vêm DEPOIS da busca porque dependem da UNIDADE do que voltou
        # (P0 05/08/2026). Antes eram duas constantes fixas aplicadas a qualquer
        # número que aparecesse — inclusive ao RRF, que nunca passa de ~0,033.
        scale_std = _get_score_scale(results_std[0]) if results_std else SCALE_NONE
        _th_std = _thresholds_for(scale_std)
        THRESH_HYDE = _th_std["hyde"]
        THRESH_MIN = _th_std["min"]

        if results_std:
            logger.info(
                f"[Search] Effective score source={_get_score_source(results_std[0])} "
                f"score={best_score_std:.3f} | scale={scale_std} "
                f"| cortes hyde={THRESH_HYDE:.2f} min={THRESH_MIN:.2f}"
            )
            if scale_std == SCALE_RRF:
                # Sem reranker E sem cosseno: não há como aferir relevância.
                # O sistema se abstém e deixa o lexical rescue decidir.
                logger.warning(
                    "[Search] Sem sinal de relevância (só RRF): cosseno denso ausente. "
                    "Decisão delegada ao lexical rescue."
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
                    "score_scale": scale_std,
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
            company_id, hyde_doc, query, agent_id=agent_id, include_global=include_global, user_id=user_id
        )

        best_score_hyde = _get_effective_score(results_hyde[0]) if results_hyde else 0
        scale_hyde = _get_score_scale(results_hyde[0]) if results_hyde else SCALE_NONE

        # Comparação: quem ganhou?
        # 0,45 de cosseno NÃO é maior que 0,50 de reranker nem menor que 0,02 de
        # RRF — são unidades diferentes. Só comparamos números quando a escala é
        # a mesma; escalas distintas se decidem pela CONFIABILIDADE da medida.
        # (Na prática as duas tentativas passam pelo mesmo pipeline e caem na
        # mesma escala; este ramo existe para que a regra não dependa disso.)
        if scale_std == scale_hyde:
            hyde_venceu = best_score_hyde > best_score_std
        else:
            hyde_venceu = _SCALE_RANK.get(scale_hyde, 0) > _SCALE_RANK.get(scale_std, 0)

        final_results = results_hyde if hyde_venceu else results_std
        final_score = best_score_hyde if hyde_venceu else best_score_std
        final_scale = scale_hyde if hyde_venceu else scale_std
        final_strategy = "hyde_hybrid" if hyde_venceu else "hybrid_fallback"

        # O corte final é o da escala VENCEDORA.
        THRESH_MIN = _thresholds_for(final_scale)["min"]

        logger.info(
            f"[Search] Comparação: Direct={best_score_std:.3f} ({scale_std}) vs "
            f"HyDE={best_score_hyde:.3f} ({scale_hyde}) → Vencedor: {final_strategy} "
            f"| corte min={THRESH_MIN:.2f} na escala {final_scale}"
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
                "score_scale": final_scale,
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
                "score_scale": _get_score_scale(res),  # a unidade do número acima
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

        # Ordem pelo RANKING (reranker ou RRF), não pela relevância: o RRF já
        # embute o BM25, que é quem acha código de protocolo e número de apólice.
        # Reordenar pelo cosseno jogaria esse sinal fora.
        results.sort(key=_get_ranking_score, reverse=True)

        top_scale = _get_score_scale(results[0]) if results else SCALE_NONE
        MIN_RELEVANCE = _thresholds_for(top_scale)["relevance"]
        top_score_source = _get_score_source(results[0]) if results else "fallback_zero"

        valid_chunks_count = 0
        for i, res in enumerate(results):
            score = _get_effective_score(res)
            score_source = _get_score_source(res)
            # Cada chunk é medido com o corte da SUA unidade. Um único
            # MIN_RELEVANCE para a lista inteira só funciona enquanto todos os
            # resultados vierem da mesma escala — e não é garantido (merge de
            # coleções, reranker parcial). A lição do P0 aplicada aqui também.
            scale = _get_score_scale(res)
            min_rel = _thresholds_for(scale)["relevance"]
            doc_name = res.get("metadata", {}).get("document_name", "Doc")
            content = res.get("content", "")

            is_relevant = score >= min_rel
            is_fallback = i == 0 and top_score < MIN_RELEVANCE
            force_rescue = rescue_used and i == 0  # garante o top result no contexto

            include_in_context = is_relevant or is_fallback or force_rescue

            if include_in_context:
                _alta, _media = _QUALITY_BANDS.get(scale, _QUALITY_BANDS[SCALE_NONE])
                quality_tag = (
                    "🟢 Alta"
                    if score > _alta
                    else "🟡 Média"
                    if score > _media
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
                "score_scale": scale,  # a unidade do número acima
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
            "score_scale": top_scale,
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
