"""O RAG voltou a medir relevancia — e na unidade certa.

Rodar: python backend/tests/test_o_rag_mede_relevancia_na_unidade_certa.py

A HISTORIA
----------
Em 05/08/2026 o produto respondia "nao encontrei informacoes" para quase toda
pergunta, com 10.818 cartas intactas e invisiveis no indice.

  medido em producao, GET /documents/rag-health
  reranker: {"configured": false, "provider": "none", "status": "missing_key"}

Sem a Cohere, `rerank_score` nao existe, e o score efetivo caia no campo `score`
do Qdrant. So que na busca hibrida esse campo NAO e similaridade: e o score da
fusao RRF, `soma de 1/(k + posicao)`. Com k=60, o melhor caso ARITMETICO e

  1/61 + 1/61 = 0,0328     (primeiro lugar nas duas listas ao mesmo tempo)

e os cortes aplicados a ele eram 0,50 / 0,40 / 0,30 — calibrados para a escala
do reranker da Cohere, que vai de 0 a 1. 0,0328 nunca alcanca 0,40. O gate
reprovava tudo, sempre. Erro de UNIDADE, nao de calibragem: metro contra
quilometro.

O CONSERTO QUE **NAO** SERVIA
-----------------------------
Baixar o corte para 0,02, ou normalizar o RRF por 2/(k+1) e cortar em 0..1.

O RRF nao mede relevancia — mede concordancia de posicao. Alguem SEMPRE esta em
primeiro lugar, inclusive quando o acervo nao tem a resposta. Os dois caminhos
aprovam tudo, e um guarda que nao tem como falhar nao guarda nada (CLAUDE.md
9.3). O bloco 6 mede esse contraste em numeros, em vez de argumentar.

O CONSERTO
----------
Separar duas perguntas que o codigo tratava como uma so:

  ORDEM      "qual vem primeiro?"  -> RRF (ou o reranker)
  RELEVANCIA "isto responde?"      -> COSSENO (ou o reranker)

O cosseno ja existia: morria dentro do servidor, porque a FusionQuery so
devolve o score fundido. `_dense_cosine_for_points` traz de volta o cosseno dos
MESMOS pontos que a fusao escolheu, numa segunda ida barata, e cada resultado
passa a declarar sua unidade em `score_scale`.

A LINHA DE CONTROLE (CLAUDE.md 9.2)
-----------------------------------
Um teste que so mostrasse "a pergunta boa agora acha" seria indistinguivel de
ter desligado o guarda. Por isso os blocos 2 e 3 rodam com os scores de RRF
**identicos** — [0,0328 · 0,0280 · 0,0164] nos dois — e com o lexical rescue
comprovadamente INATIVO nos dois. O unico fator que muda entre eles e o
cosseno. Um acha; o outro tem de continuar dizendo "nao encontrei".

Qualquer conserto baseado em RRF (baixar o corte, normalizar a escala) daria o
MESMO veredito para os dois blocos. E o que da direito a conclusao.
"""

import importlib.util
import logging
import os
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASS = 0
FAIL = 0
FAILURES = []


def checar(nome, condicao, detalhe=None):
    global PASS, FAIL
    if condicao:
        PASS += 1
        print(f"  [ok] {nome}")
    else:
        FAIL += 1
        FAILURES.append((nome, detalhe))
        print(f"  [X] {nome}{': ' + str(detalhe) if detalhe else ''}")


def _load(dotted, rel):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(dotted, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = mod
    spec.loader.exec_module(mod)
    return mod


# ─────────────────────────────────────────────────────────────────────────────
# Duplos das dependencias pesadas. A maquina de teste nao tem openai, cohere,
# qdrant_client nem fastembed — e nao precisa: o que esta sob teste e a DECISAO
# de relevancia, que e codigo puro nossa.
# ─────────────────────────────────────────────────────────────────────────────

for _nome in ("app", "app.core", "app.services"):
    _m = sys.modules.setdefault(_nome, types.ModuleType(_nome))
    _m.__path__ = []


class _Obj:
    """Objeto generico: guarda os kwargs recebidos como atributos."""

    def __init__(self, *args, **kw):
        self._args = args
        for k, v in kw.items():
            setattr(self, k, v)

    def __getattr__(self, item):  # atributo nao informado -> None
        return None


def _stub_module(nome, **atributos):
    mod = types.ModuleType(nome)
    for k, v in atributos.items():
        setattr(mod, k, v)
    sys.modules[nome] = mod
    return mod


# --- qdrant_client -----------------------------------------------------------
class _FakeQdrantClient:
    def __init__(self, *a, **kw):
        pass


_qc = _stub_module("qdrant_client", QdrantClient=_FakeQdrantClient)
_qc.__path__ = []
_modelos = {
    n: type(n, (_Obj,), {})
    for n in (
        "Distance", "FieldCondition", "Filter", "Fusion", "FusionQuery",
        "MatchAny", "MatchValue", "PayloadSchemaType", "PointStruct",
        "Prefetch", "SparseVector", "SparseVectorParams", "VectorParams",
        "IsEmptyCondition", "PayloadField", "HasIdCondition",
    )
}
_modelos["Fusion"].RRF = "rrf"  # constantes lidas na CLASSE, nao na instancia
_modelos["Distance"].COSINE = "Cosine"
_modelos["PayloadSchemaType"].KEYWORD = "keyword"
_stub_module("qdrant_client.models", **_modelos)

# --- cohere / openai / fastembed / settings ----------------------------------
_stub_module("cohere", Client=lambda *a, **k: _Obj())
_stub_module("fastembed", SparseTextEmbedding=lambda **k: _Obj(embed=lambda x: iter([_Obj()])))
_stub_module(
    "langchain_openai",
    ChatOpenAI=lambda **k: _Obj(),
    OpenAIEmbeddings=lambda **k: _Obj(embed_query=lambda t: [0.1] * 8),
)
_cfg = _stub_module("app.core.config", settings=_Obj(OPENAI_API_KEY="sk-teste", COHERE_API_KEY=None))
sys.modules["app.core"].config = _cfg

# A busca global e outro caminho; desligada para isolar o fator sob teste.
os.environ["KNOWLEDGE_GLOBAL_SEARCH"] = "0"

qdrant_service = _load("app.services.qdrant_service", "app/services/qdrant_service.py")
rerank_service = _load("app.services.rerank_service", "app/services/rerank_service.py")
# `knowledge_scope` e puro (so `typing`) e desde 08/08/2026 o corte final da
# busca passa por ele: `selecionar_com_cota` da orcamento proprio a cada
# namespace, para o trecho de contrato nao ser espremido pela carta curta
# (SPEC-067 §6). Sem carrega-lo aqui, `_execute_search` levanta ModuleNotFound —
# o FATO mudou, entao o duplo muda com ele.
knowledge_scope = _load("app.services.knowledge_scope", "app/services/knowledge_scope.py")
search_service = _load("app.services.search_service", "app/services/search_service.py")


# ─────────────────────────────────────────────────────────────────────────────
# O acervo de mentira. Duas historias, com o MESMO formato de resultado.
# ─────────────────────────────────────────────────────────────────────────────

# Scores de RRF REAIS: primeiro lugar nas duas listas, segundo/terceiro depois.
RRF = [1 / 61 + 1 / 61, 1 / 61 + 1 / 62, 1 / 61]  # 0,0328 · 0,0280 · 0,0164

# Caso COM resposta: parafrase. O denso acha; o lexico nao tem uma palavra em
# comum — que e exatamente a pergunta que o produto perde hoje.
PERGUNTA_COM_RESPOSTA = "Meu carro quebrou na estrada, o que faco?"
TRECHOS_COM_RESPOSTA = [
    "Assistencia 24h: em caso de pane ou avaria do veiculo, acione o guincho pelo 0800 traz.",
    "O reboque cobre ate 200 km contados do ponto de parada informado pelo condutor.",
    "Havendo espera superior a 60 minutos, ha reembolso do taxi ate o limite previsto.",
]
COSSENO_ALTO = [0.55, 0.47, 0.41]

# Caso SEM resposta: o acervo nao fala disso. Os RRF sao os MESMOS de cima.
PERGUNTA_SEM_RESPOSTA = "Quantos gols o Brasil fez na final de 1970?"
TRECHOS_SEM_RESPOSTA = [
    "Modo de preparo do pudim: bata os ovos com leite condensado e leve ao forno.",
    "Deixe em banho-maria por 40 minutos e espere esfriar antes de desenformar.",
    "Guarde a sobra na geladeira, coberta, e consuma em ate tres dias.",
]
COSSENO_BAIXO = [0.11, 0.09, 0.07]


def _resultados(trechos, rrf=RRF, cosseno=None, escala="rrf", rerank=None):
    """Monta o que o qdrant_service devolve, no formato exato do codigo real."""
    saida = []
    for i, texto in enumerate(trechos):
        item = {
            "score": rrf[i],
            "score_scale": escala,
            "content": texto,
            "document_id": f"doc-{i}",
            "agent_id": "agente-1",
            "chunk_index": i,
            "metadata": {"document_name": f"Documento {i}"},
        }
        if cosseno is not None:
            item["dense_score"] = cosseno[i]
        if rerank is not None:
            item["rerank_score"] = rerank[i]
        saida.append(item)
    return saida


class _QdrantDuplo:
    """Devolve sempre a mesma lista, seja qual for o filtro. Nao e o objeto sob
    teste no bloco de decisao — o que importa e o que a decisao FAZ com ela."""

    def __init__(self, resultados):
        self.resultados = resultados
        self.chamadas = 0

    def search_similar(self, **kw):
        self.chamadas += 1
        return [dict(r) for r in self.resultados]


class _RerankDuplo:
    def __init__(self, disponivel):
        self.disponivel = disponivel

    def is_available(self):
        return self.disponivel

    def health(self):
        return {
            "configured": self.disponivel,
            "provider": "cohere" if self.disponivel else "none",
            "status": "ok" if self.disponivel else "missing_key",
            "safe_to_run": True,
        }

    def rerank(self, query, docs, top_k=3):
        return docs[:top_k]


def _servico(resultados, reranker_disponivel=False):
    """SearchService real, com as bordas trocadas por duplos."""
    svc = search_service.SearchService.__new__(search_service.SearchService)
    svc.qdrant = _QdrantDuplo(resultados)
    svc.reranker = _RerankDuplo(reranker_disponivel)
    svc.embeddings = _Obj(embed_query=lambda t: [0.1] * 8)
    svc.sparse_model = _Obj(embed=lambda x: iter([_Obj()]))
    return svc


class _CapturaLog(logging.Handler):
    def __init__(self):
        super().__init__()
        self.linhas = []

    def emit(self, record):
        try:
            self.linhas.append(record.getMessage())
        except Exception:
            pass


def _buscar(svc, pergunta):
    """Roda a busca capturando o log, e devolve (resposta, linhas de log)."""
    captura = _CapturaLog()
    log = logging.getLogger("app.services.search_service")
    nivel = log.level
    log.setLevel(logging.INFO)
    log.addHandler(captura)
    try:
        resposta = svc.smart_search(
            company_id="empresa-1", query=pergunta, agent_id="agente-1",
            is_hyde_enabled=False,
        )
    finally:
        log.removeHandler(captura)
        log.setLevel(nivel)
    return resposta, captura.linhas


NAO_ENCONTREI = "Não encontrei informações suficientes"


# ═════════════════════════════════════════════════════════════════════════════
def bloco_1_a_autopsia():
    """A regua errada reprovava tudo — e a aritmetica prova sozinha."""
    print("\n== 1. a autopsia: 0,0328 nunca alcanca 0,40 ==")

    melhor_rrf_possivel = 1 / 61 + 1 / 61
    corte_antigo = search_service._THRESHOLDS_BY_SCALE[search_service.SCALE_RERANK]["min"]

    checar("o melhor RRF aritmeticamente possivel e ~0,0328",
           abs(melhor_rrf_possivel - 0.0328) < 0.0005, f"{melhor_rrf_possivel:.4f}")
    checar("o corte da escala do reranker continua 0,40 (intocado)",
           corte_antigo == 0.40, corte_antigo)
    checar("nenhum RRF possivel passa no corte do reranker",
           melhor_rrf_possivel < corte_antigo,
           f"{melhor_rrf_possivel:.4f} < {corte_antigo}")

    # E o codigo sabe distinguir as unidades.
    so_rrf = _resultados(TRECHOS_COM_RESPOSTA)[0]
    com_cosseno = _resultados(TRECHOS_COM_RESPOSTA, cosseno=COSSENO_ALTO)[0]
    com_rerank = _resultados(TRECHOS_COM_RESPOSTA, rerank=[0.62, 0.4, 0.3])[0]

    checar("resultado so com RRF e reconhecido como escala rrf",
           search_service._get_score_scale(so_rrf) == search_service.SCALE_RRF)
    checar("resultado com cosseno e reconhecido como escala cosine",
           search_service._get_score_scale(com_cosseno) == search_service.SCALE_COSINE)
    checar("resultado com rerank e reconhecido como escala rerank",
           search_service._get_score_scale(com_rerank) == search_service.SCALE_RERANK)
    checar("o score de relevancia passa a ser o cosseno, nao o RRF",
           abs(search_service._get_effective_score(com_cosseno) - 0.55) < 1e-9,
           search_service._get_effective_score(com_cosseno))
    checar("a ORDEM continua vindo do RRF, nao do cosseno",
           abs(search_service._get_ranking_score(com_cosseno) - RRF[0]) < 1e-9,
           search_service._get_ranking_score(com_cosseno))

    # `score_scale` viaja de um modulo para o outro dentro do dict: se as duas
    # pontas escreverem grafias diferentes, o gate volta a ler a unidade errada
    # em silencio — o mesmo tipo de falha, so que mais dificil de ver.
    checar("os dois modulos concordam na grafia da escala",
           search_service.SCALE_RRF == qdrant_service.SCALE_RRF
           and search_service.SCALE_COSINE == qdrant_service.SCALE_COSINE,
           f"{search_service.SCALE_RRF}/{qdrant_service.SCALE_RRF}")


def bloco_2_pergunta_com_resposta_acha():
    """Cosseno alto, RRF baixo, rescue inativo -> tem de ACHAR."""
    print("\n== 2. pergunta COM resposta no acervo ==")

    resultados = _resultados(TRECHOS_COM_RESPOSTA, cosseno=COSSENO_ALTO)

    # Pre-condicao do experimento: o rescue lexical NAO pode ser quem salva,
    # senao o teste mediria outra coisa (CLAUDE.md 9.2, um fator por vez).
    checar("o lexical rescue esta INATIVO neste caso (parafrase, zero palavra em comum)",
           search_service._lexical_rescue_match(PERGUNTA_COM_RESPOSTA, resultados) is False)

    svc = _servico(resultados)
    r, linhas = _buscar(svc, PERGUNTA_COM_RESPOSTA)

    checar("found=True", r["found"] is True, r.get("content", "")[:60])
    checar("nao devolve a frase de desistencia", NAO_ENCONTREI not in r["content"])
    checar("a resposta traz o texto do documento", "guincho" in r["content"])
    checar("score_source=dense_cosine", r["score_source"] == "dense_cosine", r["score_source"])
    checar("score_scale=cosine", r["score_scale"] == "cosine", r["score_scale"])
    checar("o score reportado e o cosseno (0,55), nao o RRF (0,033)",
           abs(r["effective_score"] - 0.55) < 1e-9, r["effective_score"])
    checar("nao usou o rescue", r.get("rescue_used") is not True)

    # O top_k=3 volta a valer: com is_relevant sempre falso, so o top-1 entrava.
    usados = [c for c in r["chunks"] if c["used_in_context"]]
    checar("os 3 chunks entram no contexto (o top_k=3 deixou de virar 1)",
           len(usados) == 3, f"{len(usados)} de {len(r['chunks'])}")
    checar("valid_chunks_count=3", r["valid_chunks_count"] == 3, r["valid_chunks_count"])
    checar("sem AVISO DE SISTEMA de baixa relevancia", "AVISO DE SISTEMA" not in r["content"])

    # Observabilidade exigida: o log diz QUAL escala foi usada.
    checar("o log declara a escala usada", any("scale=cosine" in ln for ln in linhas),
           [ln for ln in linhas if "scale=" in ln][:1])
    checar("o log declara os cortes aplicados",
           any("cortes hyde=" in ln and "min=" in ln for ln in linhas))

    # --- a ORDEM continua vindo da fusao, nao do cosseno -------------------
    # Este caso so existe porque as duas ordens PRECISAM poder discordar: se
    # ordenassemos pelo cosseno, o BM25 embutido no RRF seria descartado — e e
    # o BM25 quem acha codigo de protocolo, placa e numero de apolice, justo o
    # que o denso erra. Aqui o chunk do codigo ganha no RRF e PERDE no cosseno.
    codigo_primeiro = [
        {"score": RRF[0], "score_scale": "rrf", "dense_score": 0.42,
         "content": "Protocolo NEVOA-791 autoriza o reboque imediato.",
         "document_id": "d-codigo", "agent_id": "agente-1", "chunk_index": 0,
         "metadata": {"document_name": "Protocolos"}},
        {"score": RRF[2], "score_scale": "rrf", "dense_score": 0.55,
         "content": "O atendimento rodoviario cobre pane seca e troca de pneu.",
         "document_id": "d-generico", "agent_id": "agente-1", "chunk_index": 1,
         "metadata": {"document_name": "Gerais"}},
    ]
    checar("as duas ordens CONSEGUEM discordar neste caso",
           (codigo_primeiro[0]["score"] > codigo_primeiro[1]["score"])
           and (codigo_primeiro[0]["dense_score"] < codigo_primeiro[1]["dense_score"]))

    svc2 = _servico(codigo_primeiro)
    r2, _ = _buscar(svc2, PERGUNTA_COM_RESPOSTA)
    checar("o chunk que o BM25 trouxe continua em primeiro",
           r2["chunks"][0]["chunk_id"] == "d-codigo",
           [c["chunk_id"] for c in r2["chunks"]])
    checar("e o topo do contexto e o dele", r2["content"].index("NEVOA-791")
           < r2["content"].index("pane seca"))


def bloco_3_linha_de_controle():
    """MESMO RRF, rescue inativo, cosseno baixo -> tem de CONTINUAR recusando."""
    print("\n== 3. LINHA DE CONTROLE: pergunta SEM resposta no acervo ==")

    resultados = _resultados(TRECHOS_SEM_RESPOSTA, cosseno=COSSENO_BAIXO)

    checar("o lexical rescue esta INATIVO tambem aqui",
           search_service._lexical_rescue_match(PERGUNTA_SEM_RESPOSTA, resultados) is False)

    svc = _servico(resultados)
    r, linhas = _buscar(svc, PERGUNTA_SEM_RESPOSTA)

    checar("found=False", r["found"] is False, r.get("content", "")[:60])
    checar("devolve a frase de desistencia", NAO_ENCONTREI in r["content"])
    checar("nenhum chunk foi usado no contexto",
           all(c["used_in_context"] is False for c in r["chunks"]))
    checar("o motivo fica registrado", r["chunks"][0]["filtered_reason"] == "below_threshold")
    checar("score_scale=cosine mesmo na recusa", r["score_scale"] == "cosine", r["score_scale"])

    # O QUE DA DIREITO A CONCLUSAO: o fator que mudou foi so o cosseno.
    aprovado = _resultados(TRECHOS_COM_RESPOSTA, cosseno=COSSENO_ALTO)
    reprovado = resultados
    mesmos_rrf = all(
        abs(a["score"] - b["score"]) < 1e-12 for a, b in zip(aprovado, reprovado)
    )
    checar("o bloco 2 e o bloco 3 rodaram com RRF IDENTICOS",
           mesmos_rrf, [round(x["score"], 4) for x in reprovado])
    checar("os dois vieram da mesma escala declarada",
           aprovado[0]["score_scale"] == reprovado[0]["score_scale"] == "rrf")


def bloco_4_o_fail_safe_de_hoje_continua():
    """Sem cosseno o sistema se ABSTEM e devolve a decisao ao rescue."""
    print("\n== 4. sem cosseno: abstencao declarada, rescue intacto ==")

    # Cenario: a segunda ida ao Qdrant falhou -> nao ha dense_score.
    sem_cosseno = _resultados(TRECHOS_SEM_RESPOSTA)
    svc = _servico(sem_cosseno)
    r, linhas = _buscar(svc, PERGUNTA_SEM_RESPOSTA)

    checar("sem cosseno e sem rescue -> continua recusando", r["found"] is False)
    checar("score_scale=rrf", r["score_scale"] == "rrf", r["score_scale"])
    checar("score_source=qdrant_rrf", r["score_source"] == "qdrant_rrf", r["score_source"])
    checar("o log avisa que nao ha sinal de relevancia",
           any("Sem sinal de relevância" in ln for ln in linhas))

    # E o rescue (41C.1.3) continua sendo quem segura o produto de pe.
    texto = "A palavra-chave de validacao do RAG local esta no documento NEVOA-791."
    resgataveis = _resultados([texto, texto, texto])
    pergunta = "Qual e a palavra-chave de validacao do RAG local?"
    checar("o rescue lexical continua ativavel",
           search_service._lexical_rescue_match(pergunta, resgataveis) is True)

    svc2 = _servico(resgataveis)
    r2, _ = _buscar(svc2, pergunta)
    checar("com rescue, o RAG responde mesmo sem cosseno", r2["found"] is True)
    checar("e fica marcado como rescue", r2.get("rescue_used") is True)
    checar("a estrategia diz que foi rescue", "rescue" in r2["strategy"], r2["strategy"])

    # O conserto tem de ser MONOTONICO: o corte novo nao pode roubar um resgate
    # que ja acontecia. Se o gate do cosseno reprovasse ANTES de tentar o
    # rescue, esta pergunta pararia de ser respondida — uma regressao silenciosa
    # que ninguem veria, porque o produto ja vive de rescue hoje.
    com_cosseno_baixo = _resultados([texto, texto, texto], cosseno=[0.10, 0.09, 0.08])
    svc3 = _servico(com_cosseno_baixo)
    r3, _ = _buscar(svc3, pergunta)
    checar("cosseno baixo NAO cancela o rescue lexical", r3["found"] is True,
           r3.get("content", "")[:60])
    checar("e continua marcado como rescue", r3.get("rescue_used") is True)


def bloco_5_o_caminho_da_cohere_nao_regrediu():
    """Com a chave, a escala do reranker manda — nas duas direcoes."""
    print("\n== 5. com Cohere: escala do reranker, sem regressao ==")

    bom = _resultados(TRECHOS_COM_RESPOSTA, cosseno=COSSENO_BAIXO, rerank=[0.62, 0.55, 0.44])
    svc = _servico(bom, reranker_disponivel=True)
    r, linhas = _buscar(svc, PERGUNTA_COM_RESPOSTA)

    checar("rerank alto -> found=True", r["found"] is True)
    checar("score_source=rerank", r["score_source"] == "rerank", r["score_source"])
    checar("score_scale=rerank", r["score_scale"] == "rerank", r["score_scale"])
    checar("o rerank tem precedencia sobre o cosseno",
           abs(r["effective_score"] - 0.62) < 1e-9, r["effective_score"])
    checar("o corte aplicado foi o do reranker (0,40)",
           any("min=0.40" in ln for ln in linhas), [ln for ln in linhas if "cortes" in ln][:1])

    # A outra direcao: reranker reprova, e reprovar continua possivel.
    ruim = _resultados(TRECHOS_SEM_RESPOSTA, cosseno=COSSENO_BAIXO, rerank=[0.21, 0.18, 0.10])
    svc2 = _servico(ruim, reranker_disponivel=True)
    r2, _ = _buscar(svc2, PERGUNTA_SEM_RESPOSTA)
    checar("rerank baixo -> found=False", r2["found"] is False)
    checar("a recusa veio da escala do reranker", r2["score_scale"] == "rerank")

    # Um cosseno alto NAO pode ressuscitar o que o reranker reprovou, nem o
    # contrario: a precedencia tem de ser estavel.
    misto = _resultados(TRECHOS_SEM_RESPOSTA, cosseno=COSSENO_ALTO, rerank=[0.21, 0.18, 0.10])
    svc3 = _servico(misto, reranker_disponivel=True)
    r3, _ = _buscar(svc3, PERGUNTA_SEM_RESPOSTA)
    checar("cosseno alto nao passa por cima do reranker", r3["found"] is False,
           f"{r3['score_source']}={r3['effective_score']}")


def bloco_6_por_que_nao_normalizar_o_rrf():
    """A alternativa tentadora, medida em vez de argumentada."""
    print("\n== 6. contraste: o RRF normalizado nao distingue os dois casos ==")

    k = 60
    maximo_teorico = 2 / (k + 1)
    norm_com_resposta = RRF[0] / maximo_teorico
    norm_sem_resposta = RRF[0] / maximo_teorico  # e o MESMO topo nos dois casos

    checar("normalizado, o caso COM resposta da 1,00",
           abs(norm_com_resposta - 1.0) < 1e-9, norm_com_resposta)
    checar("normalizado, o caso SEM resposta da 1,00 tambem",
           abs(norm_sem_resposta - 1.0) < 1e-9, norm_sem_resposta)
    checar("logo: RRF normalizado NAO consegue separar os dois",
           abs(norm_com_resposta - norm_sem_resposta) < 1e-12)

    # O cosseno consegue. E essa e a unica razao de ele ter sido escolhido.
    checar("o cosseno separa os dois casos",
           COSSENO_ALTO[0] - COSSENO_BAIXO[0] > 0.4,
           f"{COSSENO_ALTO[0]} vs {COSSENO_BAIXO[0]}")

    corte = search_service._THRESHOLDS_BY_SCALE[search_service.SCALE_COSINE]["min"]
    checar("o corte do cosseno fica ENTRE os dois (o guarda consegue reprovar)",
           COSSENO_BAIXO[0] < corte < COSSENO_ALTO[0],
           f"{COSSENO_BAIXO[0]} < {corte} < {COSSENO_ALTO[0]}")


def bloco_7_o_qdrant_declara_a_unidade():
    """Onde o cosseno e colhido: a segunda ida, o filtro e o fail-safe."""
    print("\n== 7. qdrant_service: colhe o cosseno e declara a unidade ==")

    svc = qdrant_service.QdrantService.__new__(qdrant_service.QdrantService)

    pontos_fusao = [_Obj(id=10 + i, score=RRF[i],
                         payload={"content": t, "document_id": f"d{i}",
                                  "agent_id": "agente-1", "chunk_index": i, "metadata": {}})
                    for i, t in enumerate(TRECHOS_COM_RESPOSTA)]
    # O lookup de cosseno vem SEM payload (with_payload=False), de proposito.
    pontos_lookup = [_Obj(id=10 + i, score=COSSENO_ALTO[i]) for i in range(3)]
    # A busca dense-only e outra coisa: traz payload, e o score ja e o cosseno.
    pontos_dense_only = [_Obj(id=10 + i, score=COSSENO_ALTO[i], payload=p.payload)
                         for i, p in enumerate(pontos_fusao)]

    chamadas = []

    class _Client:
        def collection_exists(self, *a, **k):
            return True

        def query_points(self, **kw):
            chamadas.append(kw)
            if "prefetch" in kw:
                return _Obj(points=pontos_fusao)  # a fusao
            if kw.get("with_payload") is False:
                return _Obj(points=pontos_lookup)  # o lookup de cosseno
            return _Obj(points=pontos_dense_only)  # busca dense-only

    svc.client = _Client()

    saida = svc.search_similar(
        company_id="empresa-1", query_embedding=[0.1] * 8,
        sparse_embedding=_Obj(indices=_Obj(tolist=lambda: [1]), values=_Obj(tolist=lambda: [1.0])),
        agent_id="agente-1", top_k=3,
    )

    # Ancora antes dos `all(...)`: sobre lista vazia, `all()` e verdadeiro — um
    # check que nao tem como falhar (a mesma armadilha do CLAUDE.md 9.3, agora
    # dentro do teste). Sem esta linha, uma busca quebrada passaria batido.
    checar("a busca devolveu os 3 resultados", len(saida) == 3, len(saida))
    checar("a busca hibrida faz a segunda ida para colher o cosseno",
           len(chamadas) == 2, f"{len(chamadas)} chamadas")
    checar("todo resultado declara score_scale=rrf",
           bool(saida) and all(r["score_scale"] == "rrf" for r in saida))
    checar("todo resultado carrega o cosseno em dense_score",
           bool(saida) and all("dense_score" in r for r in saida))
    checar("o cosseno casa por id com o ponto certo",
           [r["dense_score"] for r in saida] == COSSENO_ALTO,
           [r.get("dense_score") for r in saida])
    checar("o `score` continua sendo o da fusao (a ordem nao mudou)",
           [round(r["score"], 4) for r in saida] == [round(x, 4) for x in RRF])

    # A segunda ida nao pode abrir porta: reaproveita o filtro e so restringe.
    segunda = chamadas[1]
    checar("a segunda ida nao pede payload nem vetor",
           segunda.get("with_payload") is False and segunda.get("with_vectors") is False)
    checar("a segunda ida usa o vetor denso", segunda.get("using") == "dense")
    must = list(getattr(segunda.get("query_filter"), "must", None) or [])
    primeira_must = list(getattr(chamadas[0].get("query_filter"), "must", None) or [])
    tem_has_id = any(isinstance(c, _modelos["HasIdCondition"]) for c in must)
    checar("a segunda ida ACRESCENTA a restricao por id", tem_has_id)
    checar("e preserva todas as condicoes do filtro original",
           all(c in must for c in primeira_must),
           f"{len(primeira_must)} originais, {len(must)} no lookup")

    # Fail-safe: se o cosseno falhar, a busca sobrevive sem ele.
    class _ClientQuebrado(_Client):
        def query_points(self, **kw):
            if "prefetch" in kw:
                return _Obj(points=pontos_fusao)
            raise RuntimeError("timeout no lookup de cosseno")

    svc.client = _ClientQuebrado()
    saida2 = svc.search_similar(
        company_id="empresa-1", query_embedding=[0.1] * 8,
        sparse_embedding=_Obj(indices=_Obj(tolist=lambda: [1]), values=_Obj(tolist=lambda: [1.0])),
        agent_id="agente-1", top_k=3,
    )
    checar("cosseno indisponivel nao derruba a busca", len(saida2) == 3)
    checar("e o resultado fica honesto: sem dense_score",
           bool(saida2) and all("dense_score" not in r for r in saida2))

    # Busca dense-only: ali o proprio score JA e o cosseno.
    svc.client = _Client()
    saida3 = svc.search_similar(company_id="empresa-1", query_embedding=[0.1] * 8, top_k=3)
    checar("a busca dense-only devolveu resultados", len(saida3) == 3, len(saida3))
    checar("dense-only declara score_scale=cosine",
           bool(saida3) and all(r["score_scale"] == "cosine" for r in saida3))
    checar("dense-only usa o proprio score como cosseno",
           bool(saida3) and all(r["dense_score"] == r["score"] for r in saida3))


def main():
    print("\n" + "=" * 74)
    print("  O RAG mede relevancia na unidade certa (P0 de 05/08/2026)")
    print("=" * 74)

    bloco_1_a_autopsia()
    bloco_2_pergunta_com_resposta_acha()
    bloco_3_linha_de_controle()
    bloco_4_o_fail_safe_de_hoje_continua()
    bloco_5_o_caminho_da_cohere_nao_regrediu()
    bloco_6_por_que_nao_normalizar_o_rrf()
    bloco_7_o_qdrant_declara_a_unidade()

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  FALHOU: {n} -> {d}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
