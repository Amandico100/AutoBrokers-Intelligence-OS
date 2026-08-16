"""
Qdrant Service - Gerenciamento de vector store para RAG
VERSÃO CORRIGIDA: Suporte a filtro por agent_id (Multi-Agent) + get_chunks_by_document + Qdrant Cloud + Índices
"""

import hashlib
import logging
import os
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    Fusion,
    FusionQuery,
    MatchAny,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    Prefetch,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

# Tenant-wide (agent_id ausente) é opcional e degrada com segurança se o client não tiver IsEmptyCondition.
try:
    from qdrant_client.models import IsEmptyCondition, PayloadField

    _HAS_IS_EMPTY = True
except Exception:  # pragma: no cover
    IsEmptyCondition = None  # type: ignore
    PayloadField = None  # type: ignore
    _HAS_IS_EMPTY = False

# Cosseno dos pontos já escolhidos pela fusão (ver _dense_cosine_for_points).
# Degrada com segurança: sem HasIdCondition, a busca híbrida continua devolvendo
# só o score de RRF — exatamente como antes deste conserto.
try:
    from qdrant_client.models import HasIdCondition

    _HAS_HAS_ID = True
except Exception:  # pragma: no cover
    HasIdCondition = None  # type: ignore
    _HAS_HAS_ID = False

# === UNIDADE DO SCORE (P0 05/08/2026) ===
# O campo `score` deste serviço NÃO tem uma unidade só, e isso derrubou o RAG:
#
#   - busca dense-only  → `score` é COSSENO (0..1), comparável a um threshold;
#   - busca híbrida     → `score` é RRF (Σ 1/(k+posição)), que em produção
#                         mede ~0,016 a ~0,033 e NÃO é comparável a nada em 0..1.
#
# Quem lia `score` rio abaixo não tinha como saber qual dos dois recebeu, e
# aplicou o corte de 0,40 (calibrado para o reranker da Cohere) sobre um número
# que nunca passa de ~0,033. Todo resultado era descartado.
#
# O nome do campo mentia sobre o que ele guardava (CLAUDE.md §12.1: conserte o
# campo, não o texto). Agora todo resultado diz a própria unidade em
# `score_scale`, e carrega `dense_score` (cosseno) sempre que ele for conhecido.
SCALE_COSINE = "cosine"  # similaridade real 0..1 — mede RELEVÂNCIA
SCALE_RRF = "rrf"  # concordância de posição — mede ORDEM, não relevância

logger = logging.getLogger(__name__)

# === ÍNDICES DE PAYLOAD (SPEC-070 LOTE 0, item 10) ===
#
# 📊 Até 08/08/2026 existiam TRÊS: `document_id`, `agent_id` e
# `metadata.file_type`. E **nenhum** dos campos por onde a busca global filtra:
#
#   scope             `search_similar(scope_match=...)`         — todo caminho global
#   curation_status   `search_similar(curation_published_only)` — todo caminho global
#   insurer_key       `_filtro_de_seguradora`                   — desde 07/08/2026
#   namespace         `_filtro_de_namespace`                    — desde 08/08/2026
#
# Filtro sem índice sobre 📊 23.478 pontos não é filtro: é varredura. O Qdrant
# aceita a consulta e responde certo — só que lendo o payload de tudo. Não dá
# erro, não aparece no log, aparece na latência.
#
# `vigente` e `faceta` ainda não têm escritor (SPEC-070 LOTE 0 itens 3 e 6, com
# outro dono). O índice entra agora de propósito: criar índice de campo que
# ainda não existe é barato e idempotente, e evita que a primeira busca
# filtrada por vigência varra a coleção enquanto ninguém está olhando.
_BOOL = getattr(PayloadSchemaType, "BOOL", None)  # qdrant-client antigo pode não ter

_INDICES_DE_PAYLOAD = (
    ("document_id", PayloadSchemaType.KEYWORD),      # delete e search por documento
    ("agent_id", PayloadSchemaType.KEYWORD),         # isolamento multi-agent
    ("metadata.file_type", PayloadSchemaType.KEYWORD),  # scroll_by_payload / CSV
    ("scope", PayloadSchemaType.KEYWORD),            # SPEC-003 / SPEC-044
    ("curation_status", PayloadSchemaType.KEYWORD),  # só curadoria publicada
    ("namespace", PayloadSchemaType.KEYWORD),        # SPEC-070 §6 — contrato × carta
    ("insurer_key", PayloadSchemaType.KEYWORD),      # a regra de uma não vale pela outra
    ("faceta", PayloadSchemaType.KEYWORD),           # SPEC-070 §5.1
    ("temas", PayloadSchemaType.KEYWORD),            # SPEC-072 §Bloco 1 — P-177
    ("vigente", _BOOL),                              # SPEC-070 §6 — documento revogado sai
)


class QdrantService:
    """
    Serviço para gerenciar embeddings no Qdrant Vector Database

    Estrutura:
    - Uma collection por empresa: company_{company_id}
    - Cada point contém: vector (1536 dims) + payload (document_id, agent_id, chunk_index, content, metadata)

    MULTI-AGENT:
    - Documentos são isolados por agent_id
    - Busca filtra por company_id (collection) + agent_id (payload filter)
    """

    def __init__(self):
        self.host = os.getenv("QDRANT_HOST", "localhost")
        self.port = int(os.getenv("QDRANT_PORT", "6333"))
        self.api_key = os.getenv("QDRANT_API_KEY")
        self.vector_size = int(
            os.getenv("EMBEDDING_DIMENSION", "1536")
        )  # text-embedding-3-small

        # Se tiver API key, usa Qdrant Cloud (HTTPS)
        if self.api_key:
            url = f"https://{self.host}:{self.port}"
            self.client = QdrantClient(url=url, api_key=self.api_key)
            logger.info(f"Qdrant Cloud conectado em {url}")
        else:
            # Local (Docker)
            self.client = QdrantClient(host=self.host, port=self.port)
            logger.info(f"Qdrant local conectado em {self.host}:{self.port}")

    def _get_collection_name(self, company_id: str) -> str:
        """Retorna nome da collection para uma empresa (multi-tenant)"""
        return f"company_{company_id.replace('-', '_')}"

    def _create_indexes(self, collection_name: str) -> None:
        """
        Cria índices nos campos de payload para permitir filtros eficientes
        Necessário para Qdrant Cloud funcionar corretamente com delete/search por filtro

        ⚠️ ESTA FUNÇÃO ENGOLE EXCEÇÃO DE PROPÓSITO — e por isso NÃO é prova.
        ==================================================================
        Índice que já existe devolve erro, e reaplicar em todo startup é o
        comportamento desejado (idempotência). O efeito colateral é que uma
        falha REAL (campo inexistente, permissão, tipo errado) desce pelo mesmo
        ralo do "já existe" e o log diz a mesma coisa.

        Quem responde "o índice existe?" é `indices_existentes()`, que lê o
        `payload_schema` da coleção no servidor. Acrescentar campo aqui sem
        conferir lá é repetir o padrão que fez `insurer_key`, `namespace`,
        `scope` e `curation_status` ficarem 📊 sem índice enquanto a busca
        global filtrava por todos eles sobre 23.478 pontos — varredura, não
        filtro.
        """
        for campo, esquema in _INDICES_DE_PAYLOAD:
            if esquema is None:
                logger.warning(
                    f"[Qdrant] cliente sem tipo de índice para '{campo}' — "
                    f"índice NÃO criado em '{collection_name}'"
                )
                continue
            try:
                self.client.create_payload_index(
                    collection_name=collection_name,
                    field_name=campo,
                    field_schema=esquema,
                )
                logger.info(f"Índice '{campo}' criado em '{collection_name}'")
            except Exception as e:
                # Quase sempre é "já existe". Não dá para distinguir com
                # segurança pela mensagem — a prova está em indices_existentes().
                logger.debug(f"Índice '{campo}' já existe ou erro: {e}")

    def indices_existentes(self, collection_name: str) -> Dict[str, str]:
        """Os índices de payload que EXISTEM no servidor. Medição, não log.

        Lê `payload_schema` da coleção — a mesma coisa que o Qdrant consulta
        para decidir se um filtro usa índice ou varre a coleção inteira.
        Coleção ausente ou erro devolve `{}`, e quem chama trata como "não sei",
        nunca como "não tem".
        """
        try:
            info = self.client.get_collection(collection_name=collection_name)
            esquema = getattr(info, "payload_schema", None) or {}
            return {
                str(campo): str(getattr(tipo, "data_type", tipo))
                for campo, tipo in dict(esquema).items()
            }
        except Exception as e:  # noqa: BLE001
            logger.warning(
                f"[Qdrant] payload_schema de '{collection_name}' indisponível "
                f"({type(e).__name__})"
            )
            return {}

    def verificar_indices(self, collection_name: str) -> Dict[str, Any]:
        """VERIFY dos índices: o que era para existir × o que existe de fato."""
        presentes = self.indices_existentes(collection_name)
        esperados = [campo for campo, _ in _INDICES_DE_PAYLOAD]
        faltando = [campo for campo in esperados if campo not in presentes]
        return {
            "collection": collection_name,
            "esperados": esperados,
            "presentes": sorted(presentes.keys()),
            "faltando": faltando,
            "completo": not faltando,
        }

    def create_collection(
        self, company_id: str, collection_name: Optional[str] = None
    ) -> bool:
        """
        Cria collection para uma empresa (se não existir)

        Args:
            company_id: ID da empresa
            collection_name: Nome customizado da collection (opcional, para benchmarks)

        Returns:
            True se criado com sucesso ou já existir
        """
        if collection_name is None:
            collection_name = self._get_collection_name(company_id)

        try:
            # Verificar se collection já existe
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]

            if collection_name in collection_names:
                logger.info(f"Collection '{collection_name}' já existe")
                # Garantir que índices existem mesmo em collection existente
                self._create_indexes(collection_name)
                return True

            # Criar collection com suporte a Hybrid Search (Dense + Sparse)
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config={
                    "dense": VectorParams(
                        size=self.vector_size, distance=Distance.COSINE
                    )
                },
                sparse_vectors_config={"bm25": SparseVectorParams()},
            )

            logger.info(f"Collection '{collection_name}' criada com sucesso")

            # Criar índices para filtros (necessário no Qdrant Cloud)
            self._create_indexes(collection_name)

            return True

        except Exception as e:
            logger.error(f"Erro ao criar collection: {e}")
            return False

    def insert_embeddings(
        self,
        company_id: str,
        document_id: str,
        embeddings: List[List[float]],
        chunks: List[str],
        metadata: Optional[Any] = None,
        sparse_embeddings: Optional[List[Any]] = None,
        collection_name: Optional[str] = None,
        agent_id: Optional[
            str
        ] = None,  # 🔥 NOVO: agent_id obrigatório para multi-agent
        knowledge_extras: Optional[Any] = None,  # scope/knowledge_class/... (SPEC-003)
    ) -> bool:
        """
        Insere embeddings no Qdrant (batch insert)

        Args:
            company_id: ID da empresa
            document_id: ID do documento
            embeddings: Lista de vetores (embeddings)
            chunks: Lista de textos dos chunks
            metadata: Metadata adicional (dict ou List[dict])
            sparse_embeddings: Vetores esparsos BM25
            collection_name: Nome customizado (opcional, para benchmarks)
            agent_id: ID do agente dono do documento (OBRIGATÓRIO para isolamento)

        Returns:
            True se inserido com sucesso
        """
        if collection_name is None:
            collection_name = self._get_collection_name(company_id)

        # Garantir que a collection existe (também cria índices)
        self.create_collection(company_id, collection_name=collection_name)

        try:
            points = []
            for idx, (embedding, chunk_text) in enumerate(zip(embeddings, chunks, strict=False)):
                # Suportar metadata como lista ou dict
                if isinstance(metadata, list):
                    chunk_metadata = metadata[idx] if idx < len(metadata) else {}
                elif isinstance(metadata, dict):
                    chunk_metadata = metadata.copy()
                else:
                    chunk_metadata = {}

                # 🔥 CRÍTICO: Sempre incluir agent_id no payload para filtro posterior
                payload = {
                    "document_id": document_id,
                    "agent_id": agent_id,  # 🔥 NOVO: Salvo no nível raiz do payload
                    "chunk_index": idx,
                    "content": chunk_text,
                    "metadata": chunk_metadata,
                }
                # Campos de conhecimento (scope/knowledge_class/...) — SPEC-003. Sem segredo/PII.
                #
                # Aceita dict (mesmo valor para todos os chunks) OU lista, um
                # por chunk — a mesma simetria que `metadata` já tinha logo
                # acima. A lista existe porque a SPEC-070 §5.3 pede na RAIZ do
                # payload dois campos que MUDAM de pedaço para pedaço:
                # `unit_id`, que é como a carta destilada volta ao trecho de
                # origem, e `faceta`. Sem isto eles só caberiam em `metadata`,
                # que o filtro não lê — que é exatamente o defeito que custou
                # 📊 11.211 chunks de contrato atravessando como genéricos.
                if isinstance(knowledge_extras, list):
                    _extras = (knowledge_extras[idx]
                               if idx < len(knowledge_extras) else {}) or {}
                else:
                    _extras = knowledge_extras or {}
                for _k, _v in _extras.items():
                    if _k not in payload and _v not in (None, ""):
                        payload[_k] = _v

                # ID único: hash do document_id + chunk_index
                point_id_str = f"{document_id}_{idx}"
                point_id = int(
                    hashlib.sha256(point_id_str.encode()).hexdigest()[:16], 16
                )

                # Preparar dicionário de vetores
                vector_dict = {"dense": embedding}

                # Adiciona sparse vector se disponível
                if sparse_embeddings and idx < len(sparse_embeddings):
                    sparse_item = sparse_embeddings[idx]
                    if hasattr(sparse_item, "indices") and hasattr(
                        sparse_item, "values"
                    ):
                        vector_dict["bm25"] = SparseVector(
                            indices=sparse_item.indices.tolist(),
                            values=sparse_item.values.tolist(),
                        )
                    else:
                        vector_dict["bm25"] = sparse_item

                points.append(
                    PointStruct(id=point_id, vector=vector_dict, payload=payload)
                )

            # Inserir em batch
            self.client.upsert(collection_name=collection_name, points=points)

            logger.info(
                f"Inseridos {len(points)} embeddings para documento {document_id} (agent: {agent_id})"
            )
            return True

        except Exception as e:
            logger.error(f"Erro ao inserir embeddings: {e}", exc_info=True)
            return False

    def _dense_cosine_for_points(
        self,
        collection_name: str,
        query_embedding: List[float],
        point_ids: List[Any],
        base_filter: Optional[Any] = None,
    ) -> Dict[Any, float]:
        """
        Cosseno (0..1) entre a query e CADA ponto que a fusão já escolheu.

        Por que existe: `query_points` com `FusionQuery` devolve só o score de
        RRF — o cosseno de cada ramo morre dentro do servidor. Sem ele não há
        NENHUM sinal de relevância quando o reranker está ausente, e o corte
        de threshold vira loteria (foi o P0 de 05/08/2026).

        Por que é barato: os ids já vieram da fusão, então isto é um lookup
        filtrado por id — sem embedding novo, sem payload, sem vetor de volta.
        Uma ida ao Qdrant, sobre no máximo `top_k` pontos.

        Por que é seguro: reaproveita o MESMO `base_filter` da busca original
        (agent_id, scope, curadoria, must_not) e só ACRESCENTA a restrição por
        id. Nenhum ponto novo pode entrar por aqui — no máximo saem.

        Falha fechada em observabilidade, não em produto: qualquer erro devolve
        {} e a busca segue com o RRF puro, como antes.
        """
        if not point_ids or not _HAS_HAS_ID:
            return {}

        try:
            id_condition = HasIdCondition(has_id=list(point_ids))

            if base_filter is not None:
                must = list(getattr(base_filter, "must", None) or [])
                must.append(id_condition)
                scoped_filter = Filter(
                    must=must,
                    should=getattr(base_filter, "should", None),
                    must_not=getattr(base_filter, "must_not", None),
                )
            else:
                scoped_filter = Filter(must=[id_condition])

            points = self.client.query_points(
                collection_name=collection_name,
                query=query_embedding,
                using="dense",
                limit=len(point_ids),
                query_filter=scoped_filter,
                with_payload=False,
                with_vectors=False,
            ).points

            return {p.id: float(p.score) for p in points if p.score is not None}

        except Exception as e:  # noqa: BLE001
            # Não derruba a busca: sem cosseno o serviço volta ao estado anterior.
            logger.warning(
                f"[Qdrant] cosseno denso indisponível ({type(e).__name__}); "
                f"resultados seguem só com score de RRF"
            )
            return {}

    def _filtro_de_seguradora(self, carrier_slug: Optional[str]):
        """"Desta seguradora **OU** sem seguradora" — a regra que salva o RAG.

        Devolve um `Filter` para entrar no `must`, ou `None` quando não há
        seguradora no assunto (aí tudo responde, como sempre foi).

        POR QUE OS DOIS BRAÇOS
        ======================
        📊 07/08/2026: das 12.071 cartas publicadas, **9.727 (80,6%) não têm
        seguradora**. Não é falha de etiquetagem — é fato genérico de mercado, e
        ele vale para qualquer companhia. Um filtro de um braço só
        (`insurer_key = porto`) cortaria 80,6% do acervo e deixaria o agente
        quase sem conhecimento: seria trocar "responde a seguradora errada" por
        "não responde nada".

        DEGRADAÇÃO SEGURA
        =================
        O braço "sem seguradora" precisa de `IsEmptyCondition`. Se a versão do
        cliente não tiver, **o filtro inteiro é abandonado** em vez de virar um
        filtro de um braço só. Abandonar volta ao comportamento antigo (ruim,
        conhecido); manter um braço só criaria um comportamento novo e pior,
        justamente na hora em que ninguém está olhando.
        """
        slug = (carrier_slug or "").strip().lower()
        if not slug:
            return None
        if IsEmptyCondition is None or PayloadField is None:
            logger.warning(
                "[Qdrant] cliente sem IsEmptyCondition — filtro de seguradora "
                "NÃO aplicado (as cartas genéricas não podem ser cortadas)"
            )
            return None
        return Filter(should=[
            FieldCondition(key="insurer_key", match=MatchValue(value=slug)),
            IsEmptyCondition(is_empty=PayloadField(key="insurer_key")),
        ])

    def _filtro_de_namespace(self, namespace: Optional[Any]):
        """"Desta faixa **OU** sem faixa" — SPEC-070 §6.

        Devolve um `Filter` para entrar no `must`, ou `None` quando não há faixa
        pedida (aí a busca é sobre o índice inteiro, como sempre foi).

        POR QUE ISTO EXISTE
        ===================
        📊 08/08/2026, `autobrokers_global`, 23.478 pontos: 12.063 cartas
        destiladas e 11.409 trechos de condição geral disputavam as MESMAS
        vagas finais. E o BM25 normaliza por comprimento — uma carta de 186
        caracteres vence um trecho de contrato de 1.000 quase toda vez que o
        termo casa nos dois. O contrato, que é a autoridade sobre *o que está
        escrito*, vivia estruturalmente suprimido.

        O conserto não é escolher um: é dar orçamento próprio a cada faixa. Um
        embedding, duas buscas, dois filtros.

        POR QUE OS DOIS BRAÇOS — a mesma lição de `_filtro_de_seguradora`
        ================================================================
        Um `must` puro (`namespace == "normative"`) apagaria todo ponto que não
        tem a chave. Hoje quase tudo tem, mas "quase" não é argumento: ponto
        antigo, ponto de outro caminho de ingestão e qualquer coisa gravada
        antes de a chave existir sumiriam da busca sem levantar erro. O braço
        `IsEmptyCondition` é o que garante que "sem faixa declarada" continue
        respondendo, em vez de desaparecer.

        DEGRADAÇÃO SEGURA
        =================
        Sem `IsEmptyCondition` no cliente, o filtro INTEIRO é abandonado — as
        duas buscas voltam a ver o índice todo e o `merge` dedupe. Isso é o
        comportamento antigo (ruim, conhecido). Manter um braço só criaria um
        comportamento novo e pior, escondendo pontos justamente quando ninguém
        está olhando.
        """
        faixa = [
            str(n or "").strip().lower()
            for n in ([namespace] if isinstance(namespace, str) else list(namespace or []))
        ]
        faixa = [n for n in faixa if n]
        if not faixa:
            return None
        if IsEmptyCondition is None or PayloadField is None:
            logger.warning(
                "[Qdrant] cliente sem IsEmptyCondition — filtro de namespace "
                "NÃO aplicado (ponto sem faixa declarada não pode sumir)"
            )
            return None
        casa = (
            FieldCondition(key="namespace", match=MatchValue(value=faixa[0]))
            if len(faixa) == 1
            else FieldCondition(key="namespace", match=MatchAny(any=faixa))
        )
        return Filter(should=[
            casa,
            IsEmptyCondition(is_empty=PayloadField(key="namespace")),
        ])

    def _filtro_de_faceta(self, faceta: Optional[str]):
        """"Desta faceta **OU** sem faceta" — SPEC-072 Bloco 1, fecha a P-142.

        Devolve um `Filter` para entrar no `must`, ou `None` quando a pergunta
        não pede faceta nenhuma (aí tudo responde, como sempre foi).

        POR QUE ISTO EXISTE
        ===================
        📊 A `faceta` tem escritor desde 08/08/2026 (`insurance_corpus.py:1169`,
        `attendance_distiller.py:686`) e **índice de payload** desde antes
        (`_INDICES_DE_PAYLOAD`, KEYWORD). O que faltava era o LEITOR: não havia
        como pedir "só as cartas de documento desta seguradora", e a busca
        dependia de o BM25 casar a palavra por sorte.

        POR QUE OS DOIS BRAÇOS — e aqui o custo de errar é o maior dos três
        ==================================================================
        📊 Medido em 15/08/2026: **12.534 das 17.928 cartas publicadas** nascem
        de conversa e **nunca terão faceta** — a chave é omitida de propósito
        quando não há rótulo. E **1.139 dos 6.797 pedaços de contrato (16,8%)**
        têm `faceta=None`, também omitida (`insurance_corpus.py:1167`).

        Um `must` puro (`faceta == "documento"`) apagaria os dois conjuntos de
        uma vez: **70% do índice**. A P-142 já tinha escrito o aviso para o
        campo irmão — *"sem o segundo braço ele apaga as 12.063 cartas, que não
        têm essa chave e nunca terão"* — e ele vale igual aqui.

        DEGRADAÇÃO SEGURA
        =================
        Sem `IsEmptyCondition` no cliente, o filtro INTEIRO é abandonado. Voltar
        ao comportamento antigo é ruim e conhecido; um braço só seria novo e
        pior, escondendo 70% do acervo sem levantar erro.
        """
        alvo = str(faceta or "").strip().lower()
        if not alvo:
            return None
        if IsEmptyCondition is None or PayloadField is None:
            logger.warning(
                "[Qdrant] cliente sem IsEmptyCondition — filtro de faceta "
                "NÃO aplicado (carta sem faceta não pode sumir)"
            )
            return None
        return Filter(should=[
            FieldCondition(key="faceta", match=MatchValue(value=alvo)),
            IsEmptyCondition(is_empty=PayloadField(key="faceta")),
        ])

    def _filtro_de_temas(self, temas: Optional[Any]):
        """"Com este tema **OU** sem tema" — SPEC-072 Bloco 1, fecha a P-177.

        Devolve um `Filter` para entrar no `must`, ou `None` quando a pergunta
        não pede tema nenhum.

        POR QUE ISTO EXISTE
        ===================
        📊 O commit `3f6d1b4` rotulou **14.264 cartas** com tema e a migration
        `20260815_02` criou a coluna `temas text[]` com índice GIN no Postgres.
        E o índice de busca não sabia de nada disso: até 15/08/2026 `temas` não
        aparecia em `knowledge_extras`, em select de republicador nenhum, nem
        como índice de payload. **O rótulo existia no banco e a busca nunca o
        lia** — que é o mesmo defeito da `faceta`, uma camada antes.

        POR QUE OS DOIS BRAÇOS
        ======================
        📊 **4.083 das 17.928 cartas publicadas (22,8%) têm `temas` nulo.** Um
        braço só apagaria um quinto do índice.

        POR QUE `MatchAny` E NÃO `MatchValue`
        =====================================
        ⚠️ **Não é porque `MatchValue` não casaria com lista** — casaria: o Qdrant
        compara valor contra campo-array elemento a elemento, e é por isso que os
        filtros irmãos usam `MatchValue` sem se preocupar. O motivo é o outro
        lado: quem PERGUNTA pode pedir mais de um tema ("documentos e prazo"), e
        `temas_da_pergunta` devolve LISTA. `MatchAny` cobre um e vários com o
        mesmo código; `MatchValue` precisaria do `if len(...) == 1` que
        `_filtro_de_namespace` carrega — e ali ele existe porque `namespace` é
        escalar dos dois lados, o que não é o caso aqui.

        ⚠️ A chave fica AUSENTE quando não há tema, e não `[]` — mas **não** pelo
        motivo que este comentário dizia até 15/08/2026. A versão anterior
        afirmava que *"o braço `IsEmptyCondition` não alcançaria uma lista
        vazia"*, e isso é **falso**: a doc do Qdrant diz que `is_empty` casa
        quando o campo não existe, é `null` **ou é `[]`**. Um juiz crítico pegou
        a afirmação, e o próprio teste deste repositório já a contradizia.
        O motivo real de omitir é mais simples: `[]` no payload é ruído — ocupa
        espaço, aparece no diagnóstico e não significa nada que a ausência já não
        signifique. Quem escreve usa `if card.get("temas")`, que é falso para
        `[]`, e assim os dois casos viram um só.

        DEGRADAÇÃO SEGURA
        =================
        A mesma dos irmãos: sem `IsEmptyCondition`, o filtro inteiro cai.
        """
        pedidos = [
            str(t or "").strip().lower()
            for t in ([temas] if isinstance(temas, str) else list(temas or []))
        ]
        pedidos = [t for t in pedidos if t]
        if not pedidos:
            return None
        if IsEmptyCondition is None or PayloadField is None:
            logger.warning(
                "[Qdrant] cliente sem IsEmptyCondition — filtro de temas "
                "NÃO aplicado (carta sem tema não pode sumir)"
            )
            return None
        return Filter(should=[
            FieldCondition(key="temas", match=MatchAny(any=pedidos)),
            IsEmptyCondition(is_empty=PayloadField(key="temas")),
        ])

    def search_similar(
        self,
        company_id: str,
        query_embedding: List[float],
        top_k: int = 5,
        document_id: Optional[str] = None,
        agent_id: Optional[str] = None,  # 🔥 Filtro por agente (isolamento multi-agent)
        include_tenant_wide: bool = False,  # também inclui docs sem agent_id (tenant-wide)
        scope_match: Optional[List[str]] = None,  # filtra por scope (ex.: global) — SPEC-003
        curation_published_only: bool = False,  # só conhecimento curado/publicado (global)
        exclude_metadata_document_types: Optional[List[str]] = None,
        exclude_scopes: Optional[List[str]] = None,  # SPEC-044: ex. ['personal'] na busca padrão
        owner_user_id: Optional[str] = None,  # SPEC-044: docs pessoais SÓ do dono
        # Seguradora do assunto. Ver `_filtro_de_seguradora` para a regra —
        # "desta seguradora OU sem seguradora", nunca "só desta".
        carrier_slug: Optional[str] = None,
        # Faixa de conhecimento (SPEC-070 §6): 'normative', 'cards', 'canon' —
        # str ou lista. Ver `_filtro_de_namespace`: "desta faixa OU sem faixa".
        namespace: Optional[Any] = None,
        # Qual das 8 perguntas do contrato (SPEC-072 Bloco 1 / P-142). Ver
        # `_filtro_de_faceta`: "desta faceta OU sem faceta", jamais "só desta".
        faceta: Optional[str] = None,
        # Assunto do atendimento (SPEC-072 Bloco 1 / P-177) — str ou lista. Ver
        # `_filtro_de_temas`: "com este tema OU sem tema".
        temas: Optional[Any] = None,
        score_threshold: float = 0.0,
        sparse_embedding: Optional[Any] = None,
        collection_name: Optional[str] = None,
        with_dense_score: bool = True,  # colhe o cosseno na busca híbrida (P0 05/08/2026)
    ) -> List[Dict[str, Any]]:
        """
        Busca chunks similares por embedding COM FILTRO POR AGENTE

        Args:
            company_id: ID da empresa
            query_embedding: Embedding da query
            top_k: Número de resultados
            document_id: Filtrar por documento específico (opcional)
            agent_id: Filtrar por agente específico (OBRIGATÓRIO para multi-agent)
            score_threshold: Score mínimo (0.0 a 1.0)
            sparse_embedding: Vetor esparso para busca híbrida
            collection_name: Nome customizado (opcional, para benchmarks)

        Returns:
            Lista de resultados com score, content e metadata
        """
        if collection_name is None:
            collection_name = self._get_collection_name(company_id)

        try:
            # Verificar se collection existe
            if not self.client.collection_exists(collection_name):
                logger.warning(f"[Qdrant] Collection '{collection_name}' não existe.")
                return []

            logger.debug(
                f"[Qdrant] Collection '{collection_name}' exists, proceeding with search"
            )

            # Filtro de isolamento: agente específico (+ opcional tenant-wide agent_id ausente).
            must_conditions = []
            must_not_conditions = []
            should_conditions = None

            if document_id:
                must_conditions.append(
                    FieldCondition(key="document_id", match=MatchValue(value=document_id))
                )

            if agent_id:
                if include_tenant_wide and _HAS_IS_EMPTY:
                    # Documentos DESTE agente OU tenant-wide (agent_id ausente) — nunca de outro agente.
                    should_conditions = [
                        FieldCondition(key="agent_id", match=MatchValue(value=str(agent_id))),
                        IsEmptyCondition(is_empty=PayloadField(key="agent_id")),
                    ]
                else:
                    must_conditions.append(
                        FieldCondition(key="agent_id", match=MatchValue(value=str(agent_id)))
                    )
                logger.debug(
                    f"[Qdrant] agent_id filter (tenant_wide={include_tenant_wide and _HAS_IS_EMPTY})"
                )

            # Filtros de conhecimento (scope/curadoria) — SPEC-003 (global é opt-in).
            if scope_match:
                if len(scope_match) == 1:
                    must_conditions.append(
                        FieldCondition(key="scope", match=MatchValue(value=scope_match[0]))
                    )
                else:
                    must_conditions.append(
                        FieldCondition(key="scope", match=MatchAny(any=list(scope_match)))
                    )
            if curation_published_only:
                must_conditions.append(
                    FieldCondition(key="curation_status", match=MatchValue(value="published"))
                )
            if exclude_metadata_document_types:
                must_not_conditions.append(
                    FieldCondition(
                        key="metadata.document_type",
                        match=MatchAny(any=list(exclude_metadata_document_types)),
                    )
                )
            # SPEC-044: a busca PADRÃO exclui escopos privados (ex.: 'personal')
            # — documento pessoal de um usuário JAMAIS aparece para outro.
            if exclude_scopes:
                must_not_conditions.append(
                    FieldCondition(key="scope", match=MatchAny(any=list(exclude_scopes)))
                )
            # SPEC-044: busca pessoal — trava no DONO (junto com scope_match=['personal']).
            if owner_user_id:
                must_conditions.append(
                    FieldCondition(key="owner_user_id", match=MatchValue(value=str(owner_user_id)))
                )

            # 🔴 A REGRA DA SEGURADORA — "esta OU nenhuma", jamais "só esta".
            #
            # 📊 07/08/2026: 9.727 das 12.071 cartas publicadas (80,6%) NÃO têm
            # seguradora, e isso está certo: são fato genérico de mercado
            # ("vistoria complementar antes de liberar o complemento"). Elas
            # respondem qualquer pergunta, de qualquer companhia.
            #
            # O que não podia continuar acontecendo é a carta da Allianz
            # aparecer numa pergunta sobre a Porto. Sem filtro, as 608 da
            # Allianz disputavam em igualdade com as 361 da Porto, e nada
            # registrava a troca.
            #
            # Por isso o filtro é um `should` de dois braços dentro de um
            # `must`: ou a carta é DESTA seguradora, ou ela não tem seguradora
            # nenhuma. Um filtro `must` simples cortaria os 80,6% e o RAG
            # perderia quase todo o conhecimento útil — seria trocar um defeito
            # por outro pior.
            filtro_seguradora = self._filtro_de_seguradora(carrier_slug)
            if filtro_seguradora is not None:
                must_conditions.append(filtro_seguradora)

            # 🔴 A FAIXA DE CONHECIMENTO — "desta OU sem faixa", jamais "só desta".
            #
            # 📊 08/08/2026: 12.063 cartas e 11.409 trechos de contrato dividiam
            # as mesmas vagas, e o BM25 (que normaliza por comprimento) fazia a
            # carta de 186 caracteres vencer o trecho de 1.000. Cada faixa passa
            # a ter orçamento próprio — mesma busca, filtro diferente.
            #
            # O braço `IsEmptyCondition` existe pelo mesmo motivo do filtro de
            # seguradora: ponto sem a chave não pode desaparecer do índice
            # porque alguém acrescentou um filtro.
            filtro_namespace = self._filtro_de_namespace(namespace)
            if filtro_namespace is not None:
                must_conditions.append(filtro_namespace)

            # 🔴 A PERGUNTA QUE A CARTA RESPONDE, E O ASSUNTO DELA — SPEC-072.
            #
            # Os dois rótulos existiam, tinham escritor e não tinham leitor:
            # 📊 `faceta` classificava 380 cartas de documento e 6.797 pedaços de
            # contrato; `temas` rotulava 14.264 cartas. Nenhum dos dois filtrava
            # nada — P-142 e P-177.
            #
            # Os dois braços aqui não são zelo: um `must` puro apagaria 12.534
            # cartas de conversa (sem faceta) e 4.083 (sem tema).
            filtro_faceta = self._filtro_de_faceta(faceta)
            if filtro_faceta is not None:
                must_conditions.append(filtro_faceta)

            filtro_temas = self._filtro_de_temas(temas)
            if filtro_temas is not None:
                must_conditions.append(filtro_temas)

            if must_conditions or should_conditions or must_not_conditions:
                query_filter = Filter(
                    must=must_conditions or None,
                    should=should_conditions,
                    must_not=must_not_conditions or None,
                )
            else:
                query_filter = None

            # Log do filtro aplicado
            logger.debug(
                f"[Qdrant] Searching with filter: agent_id={agent_id}, document_id={document_id}, threshold={score_threshold}, top_k={top_k}, hybrid={sparse_embedding is not None}"
            )

            # Montar query: Híbrida (dense+sparse) ou Dense-only
            if sparse_embedding is not None:
                # Conversão de compatibilidade para FastEmbed -> Qdrant
                if hasattr(sparse_embedding, "indices") and hasattr(
                    sparse_embedding, "values"
                ):
                    sparse_embedding = SparseVector(
                        indices=sparse_embedding.indices.tolist(),
                        values=sparse_embedding.values.tolist(),
                    )

                # BUSCA HÍBRIDA: RRF Fusion (Dense + Sparse)
                logger.debug("[Qdrant] Using HYBRID search (Dense + Sparse BM25)")
                search_results = self.client.query_points(
                    collection_name=collection_name,
                    prefetch=[
                        Prefetch(
                            query=sparse_embedding,
                            using="bm25",
                            limit=top_k * 2,
                            filter=query_filter,  # 🔥 Filtro aplicado no prefetch também
                        ),
                        Prefetch(
                            query=query_embedding,
                            using="dense",
                            limit=top_k * 2,
                            filter=query_filter,  # 🔥 Filtro aplicado no prefetch também
                        ),
                    ],
                    query=FusionQuery(fusion=Fusion.RRF),
                    limit=top_k,
                    query_filter=query_filter,
                ).points
            else:
                # BUSCA DENSE-ONLY
                search_results = self.client.query_points(
                    collection_name=collection_name,
                    query=query_embedding,
                    using="dense",
                    limit=top_k,
                    query_filter=query_filter,
                    score_threshold=score_threshold,
                ).points

            # Qual unidade este ramo produziu? (ver bloco UNIDADE DO SCORE no topo)
            is_hybrid = sparse_embedding is not None
            score_scale = SCALE_RRF if is_hybrid else SCALE_COSINE

            # Na busca híbrida o `score` é RRF e não serve de relevância: buscamos
            # o cosseno dos MESMOS pontos numa segunda ida barata ao Qdrant.
            dense_by_id: Dict[Any, float] = {}
            if is_hybrid and with_dense_score and search_results:
                dense_by_id = self._dense_cosine_for_points(
                    collection_name=collection_name,
                    query_embedding=query_embedding,
                    point_ids=[r.id for r in search_results],
                    base_filter=query_filter,
                )

            # Formatar resultados
            results = []
            for result in search_results:
                # dense_score = relevância comparável a um threshold em 0..1.
                # Na busca dense-only o próprio `score` já é o cosseno.
                if is_hybrid:
                    dense_score = dense_by_id.get(result.id)
                else:
                    dense_score = result.score

                item = {
                    "score": result.score,
                    "score_scale": score_scale,  # a unidade de `score`, explícita
                    "content": result.payload.get("content", ""),
                    "document_id": result.payload.get("document_id", ""),
                    "agent_id": result.payload.get(
                        "agent_id", ""
                    ),  # 🔥 Retorna agent_id
                    "chunk_index": result.payload.get("chunk_index", 0),
                    "metadata": result.payload.get("metadata", {}),
                    # A faixa viaja de volta: é ela que dá o orçamento no corte
                    # final (`knowledge_scope.selecionar_com_cota`). Sem isto,
                    # separar as buscas e juntar tudo na hora de cortar
                    # devolveria o problema inteiro.
                    "namespace": result.payload.get("namespace"),
                }
                if dense_score is not None:
                    item["dense_score"] = float(dense_score)
                results.append(item)

            _com_cosseno = sum(1 for r in results if "dense_score" in r)
            logger.info(
                f"[Qdrant] Found {len(results)} results for agent {agent_id} "
                f"| score_scale={score_scale} | com cosseno={_com_cosseno}/{len(results)}"
            )
            return results

        except Exception as e:
            logger.error(f"[Qdrant] Error searching: {e}", exc_info=True)
            return []

    def delete_document(
        self, company_id: str, document_id: str, collection_name: Optional[str] = None
    ) -> bool:
        """
        Deleta todos os chunks de um documento

        Args:
            company_id: ID da empresa
            document_id: ID do documento
            collection_name: Nome customizado (opcional)

        Returns:
            True se deletado com sucesso
        """
        if collection_name is None:
            collection_name = self._get_collection_name(company_id)

        try:
            # Garantir que índices existem antes de deletar
            self._create_indexes(collection_name)

            self.client.delete(
                collection_name=collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="document_id", match=MatchValue(value=document_id)
                        )
                    ]
                ),
            )

            logger.info(f"Documento {document_id} deletado do Qdrant")
            return True

        except Exception as e:
            logger.error(f"Erro ao deletar documento: {e}")
            return False

    def delete_by_agent(
        self, company_id: str, agent_id: str, collection_name: Optional[str] = None
    ) -> bool:
        """
        🔥 NOVO: Deleta todos os chunks de um agente específico

        Args:
            company_id: ID da empresa
            agent_id: ID do agente
            collection_name: Nome customizado (opcional)

        Returns:
            True se deletado com sucesso
        """
        if collection_name is None:
            collection_name = self._get_collection_name(company_id)

        try:
            # Garantir que índices existem antes de deletar
            self._create_indexes(collection_name)

            self.client.delete(
                collection_name=collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(key="agent_id", match=MatchValue(value=agent_id))
                    ]
                ),
            )

            logger.info(f"Todos os chunks do agente {agent_id} deletados do Qdrant")
            return True

        except Exception as e:
            logger.error(f"Erro ao deletar chunks do agente: {e}")
            return False

    def delete_collection(
        self, company_id: str, collection_name: Optional[str] = None
    ) -> bool:
        """
        Deleta collection inteira de uma empresa

        Args:
            company_id: ID da empresa
            collection_name: Nome customizado (opcional, para benchmarks)

        Returns:
            True se deletado com sucesso
        """
        if collection_name is None:
            collection_name = self._get_collection_name(company_id)

        try:
            self.client.delete_collection(collection_name=collection_name)
            logger.info(f"Collection '{collection_name}' deletada")
            return True

        except Exception as e:
            logger.error(f"Erro ao deletar collection: {e}")
            return False

    def get_collection_info(self, company_id: str) -> Optional[Dict[str, Any]]:
        """
        Retorna informações sobre a collection

        Args:
            company_id: ID da empresa

        Returns:
            Dict com informações ou None se não existir
        """
        collection_name = self._get_collection_name(company_id)

        try:
            info = self.client.get_collection(collection_name=collection_name)
            return {
                "name": collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status,
            }

        except Exception as e:
            logger.warning(f"Collection não encontrada: {e}")
            return None

    def count_by_agent(
        self, company_id: str, agent_id: str, collection_name: Optional[str] = None
    ) -> int:
        """
        🔥 NOVO: Conta quantos chunks um agente tem

        Args:
            company_id: ID da empresa
            agent_id: ID do agente

        Returns:
            Número de chunks do agente
        """
        if collection_name is None:
            collection_name = self._get_collection_name(company_id)

        try:
            result = self.client.count(
                collection_name=collection_name,
                count_filter=Filter(
                    must=[
                        FieldCondition(key="agent_id", match=MatchValue(value=agent_id))
                    ]
                ),
            )
            return result.count
        except Exception as e:
            logger.error(f"Erro ao contar chunks do agente: {e}")
            return 0

    def get_chunks_by_document(
        self,
        company_id: str,
        document_id: str,
        limit: int = 500,
        collection_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        🔥 NOVO: Retorna todos os chunks de um documento específico

        Args:
            company_id: ID da empresa
            document_id: ID do documento
            limit: Máximo de chunks a retornar (default 500)
            collection_name: Nome customizado (opcional)

        Returns:
            Lista de chunks com content, metadata, chunk_index
        """
        if collection_name is None:
            collection_name = self._get_collection_name(company_id)

        try:
            # Verificar se collection existe
            if not self.client.collection_exists(collection_name):
                logger.warning(f"Collection '{collection_name}' não existe")
                return []

            # Scroll para pegar todos os pontos do documento
            results, _ = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="document_id", match=MatchValue(value=document_id)
                        )
                    ]
                ),
                limit=limit,
                with_payload=True,
                with_vectors=False,  # Não precisa dos vetores, só payload
            )

            # Formatar resultados
            chunks = []
            for point in results:
                chunks.append(
                    {
                        "id": point.id,
                        "chunk_index": point.payload.get("chunk_index", 0),
                        "content": point.payload.get("content", ""),
                        "document_id": point.payload.get("document_id", ""),
                        "agent_id": point.payload.get("agent_id", ""),
                        "metadata": point.payload.get("metadata", {}),
                    }
                )

            # Ordenar por chunk_index
            chunks.sort(key=lambda x: x["chunk_index"])

            logger.info(f"Retornados {len(chunks)} chunks do documento {document_id}")
            return chunks

        except Exception as e:
            logger.error(f"Erro ao buscar chunks do documento: {e}", exc_info=True)
            return []

    def scroll_by_payload(
        self,
        company_id: str,
        agent_id: str,
        file_type: str = "csv",
        metadata_filters: Optional[Dict[str, str]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        🔥 NOVO: Busca estruturada por metadados (sem vetor).
        Usado pela CSVAnalyticsTool para ordenação, filtros e rankings.

        Args:
            company_id: ID da empresa
            agent_id: ID do agente (isolamento multi-tenant)
            file_type: Tipo de arquivo a filtrar (default: "csv")
            metadata_filters: Filtros adicionais {coluna: valor}
            limit: Máximo de resultados (default: 100)

        Returns:
            Lista de pontos com content e metadata
        """
        collection_name = self._get_collection_name(company_id)

        try:
            # Verificar se collection existe
            if not self.client.collection_exists(collection_name):
                logger.warning(f"Collection '{collection_name}' não existe")
                return []

            # Filtro base: agent_id (obrigatório para isolamento)
            must_conditions = [
                FieldCondition(key="agent_id", match=MatchValue(value=str(agent_id)))
            ]

            # Filtro por tipo de arquivo (dentro de metadata)
            if file_type:
                must_conditions.append(
                    FieldCondition(
                        key="metadata.file_type", match=MatchValue(value=file_type)
                    )
                )

            # Filtros dinâmicos de metadados
            if metadata_filters:
                for key, value in metadata_filters.items():
                    # Normaliza chave para buscar dentro de metadata
                    search_key = key if key.startswith("metadata.") else f"metadata.{key}"
                    must_conditions.append(
                        FieldCondition(key=search_key, match=MatchValue(value=value))
                    )

            # Scroll no Qdrant (apenas Payload, sem Vetores)
            results, _ = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=Filter(must=must_conditions),
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )

            items = [
                {
                    "content": point.payload.get("content", ""),
                    "metadata": point.payload.get("metadata", {}),
                    "chunk_index": point.payload.get("chunk_index", 0),
                }
                for point in results
            ]

            logger.info(
                f"[Qdrant] scroll_by_payload: {len(items)} itens | "
                f"agent={agent_id} | file_type={file_type}"
            )
            return items

        except Exception as e:
            logger.error(f"Erro no scroll_by_payload: {e}", exc_info=True)
            return []

    def ensure_all_indexes(self) -> None:
        """
        Garante que índices existem em TODAS as collections existentes.
        Chamado uma vez no startup (singleton init).

        🔴 "Verificados" passou a significar MEDIDOS.
        ============================================
        A versão anterior chamava `_create_indexes` e logava
        *"✅ Índices verificados em N collections"* — sem nunca ter perguntado
        ao servidor se algum índice existia. `_create_indexes` engole toda
        exceção, então a linha verde era emitida com a mesma confiança tendo o
        índice sido criado, já existido, ou falhado.

        Agora o log diz o que `payload_schema` respondeu. Quando falta algo, o
        nome do campo aparece — é a diferença entre "parece feito" e "está".
        """
        try:
            collections = self.client.get_collections().collections
            if not collections:
                logger.info("[Qdrant] Nenhuma collection encontrada para indexar")
                return

            incompletas = []
            for col in collections:
                try:
                    self._create_indexes(col.name)
                except Exception as e:
                    logger.warning(f"[Qdrant] Erro ao criar índices em '{col.name}': {e}")
                verificacao = self.verificar_indices(col.name)
                if not verificacao["completo"]:
                    incompletas.append((col.name, verificacao["faltando"]))

            if incompletas:
                for nome, faltando in incompletas[:10]:
                    logger.warning(
                        f"[Qdrant] ⚠️ '{nome}' sem índice em: {', '.join(faltando)} "
                        f"(filtro por esses campos vira varredura)"
                    )
                logger.warning(
                    f"[Qdrant] {len(incompletas)}/{len(collections)} collections com "
                    f"índice faltando — medido em payload_schema, não no log de criação"
                )
            else:
                logger.info(
                    f"[Qdrant] ✅ Índices CONFERIDOS em {len(collections)} collections "
                    f"({len(_INDICES_DE_PAYLOAD)} campos, lidos do payload_schema)"
                )
        except Exception as e:
            logger.error(f"[Qdrant] Erro ao verificar índices: {e}")


# Singleton instance
_qdrant_service: Optional[QdrantService] = None


def get_qdrant_service() -> QdrantService:
    """Retorna instância singleton do QdrantService"""
    global _qdrant_service
    if _qdrant_service is None:
        _qdrant_service = QdrantService()
        # Garantir índices em todas as collections existentes (startup)
        _qdrant_service.ensure_all_indexes()
    return _qdrant_service
