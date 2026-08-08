"""O contrato e a carta pararam de disputar as mesmas tres vagas.

A HISTORIA
==========
📊 08/08/2026, colecao `autobrokers_global`, 23.478 pontos:

    cards ..... 12.063   carta destilada de atendimento real
    normative . 11.409   trecho de condicao geral — o CONTRATO
    canon ..... 6

As duas populacoes chegavam ao agente pelas MESMAS tres vagas. E a disputa nao
era justa por dois motivos somados:

  1. o BM25 normaliza por comprimento. 📊 A carta publicada tem 186 caracteres
     de media (n=12.063, mediana 186, p90 260); o trecho normativo vai ate 1.000
     (`insurance_corpus.py:213`, chunk_size=1000). Casando o mesmo termo, a
     carta curta vence quase sempre.
  2. o corte final era `rerank(..., top_k=3)`. Sem `COHERE_API_KEY` — 📊 o estado
     de hoje — `rerank()` vira `docs[:3]`: nao reordena nada, so trunca os tres
     primeiros de uma fusao RRF que, como o proprio `search_service` documenta,
     *"nao mede relevancia, mede concordancia de posicao"*.

O material contratual estava estruturalmente suprimido. E ele e a autoridade
sobre *o que esta escrito* (SPEC-070 §6): a carta manda no *como se faz*, o
contrato manda no *que e*.

O CONSERTO — E O MEIO CONSERTO QUE NAO SERVIA
=============================================
O campo `namespace` ja viajava na raiz do payload desde sempre. Faltava ele ser
usado: `build_global_search_kwargs` o declarava na assinatura e o jogava fora,
com o docstring dizendo "reservado".

Mas so separar as BUSCAS nao resolveria. Recuperar 12 trechos e 12 cartas e
depois cortar os 3 melhores de uma lista so devolve o problema inteiro — o RRF
de duas buscas distintas nao e comparavel entre si, e a carta curta volta a
ganhar todas as vagas. **O orcamento tem de sobreviver ate a vaga final.**

Por isso sao dois passos com nomes distintos:

    rerank                 ORDENA (com Cohere: relevancia real; sem ela:
                           pass-through, a ordem que ja veio)
    selecionar_com_cota    escolhe as VAGAS respeitando o orcamento de cada faixa

O QUE ESTE TESTE GUARDA
=======================
1. a cota funciona de verdade — nao e comentario
2. e o CONTROLE prova que sem ela o contrato sumiria da mesma lista
3. vaga reservada e nao usada nao e desperdicada
4. o filtro de namespace tem dois bracos, como o de seguradora
5. nenhum namespace escrito pelo sistema fica fora de alguma faixa de busca
6. os indices de payload existem — e sao CONFERIDOS, nao presumidos
7. o reranker se comporta nos DOIS estados: com chave e sem chave
8. e o valor da chave nunca aparece em lugar nenhum
"""

from __future__ import annotations

import ast
import importlib.util
import os
import re
import sys
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
_PROBLEMAS: list = []


def checar(condicao: bool, o_que: str, evidencia: str = "") -> None:
    if condicao:
        print(f"  OK  {o_que}" + (f"  ({evidencia})" if evidencia else ""))
    else:
        print(f"  X   {o_que}" + (f"  ({evidencia})" if evidencia else ""))
        _PROBLEMAS.append(o_que)


def _fonte(rel: str) -> str:
    return (RAIZ / rel).read_text(encoding="utf-8")


def _carregar(dotted: str, rel: str):
    spec = importlib.util.spec_from_file_location(dotted, RAIZ / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Duplos das bordas pesadas. A maquina de teste nao tem qdrant_client nem
# cohere — e nao precisa: o que esta sob teste e a DECISAO, que e codigo nosso.
# ---------------------------------------------------------------------------
for _nome in ("app", "app.core", "app.services"):
    _m = sys.modules.setdefault(_nome, types.ModuleType(_nome))
    _m.__path__ = []


class _Obj:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)

    def __getattr__(self, item):
        return None


def _stub(nome, **atributos):
    mod = types.ModuleType(nome)
    for k, v in atributos.items():
        setattr(mod, k, v)
    sys.modules[nome] = mod
    return mod


_stub("qdrant_client", QdrantClient=lambda *a, **k: _Obj()).__path__ = []
_modelos = {
    n: type(n, (_Obj,), {})
    for n in ("Distance", "FieldCondition", "Filter", "Fusion", "FusionQuery",
              "MatchAny", "MatchValue", "PayloadSchemaType", "PointStruct",
              "Prefetch", "SparseVector", "SparseVectorParams", "VectorParams",
              "IsEmptyCondition", "PayloadField", "HasIdCondition")
}
_modelos["PayloadSchemaType"].KEYWORD = "keyword"
_modelos["PayloadSchemaType"].BOOL = "bool"
_modelos["Distance"].COSINE = "Cosine"
_modelos["Fusion"].RRF = "rrf"
_stub("qdrant_client.models", **_modelos)

# `settings` e um objeto MUTAVEL de proposito: o bloco do reranker troca a
# chave entre as duas construcoes para medir os dois estados no mesmo processo.
_SETTINGS = _Obj(OPENAI_API_KEY="sk-teste", COHERE_API_KEY=None)
_cfg = _stub("app.core.config", settings=_SETTINGS)
sys.modules["app.core"].config = _cfg

KS = _carregar("app.services.knowledge_scope", "app/services/knowledge_scope.py")
QS = _carregar("app.services.qdrant_service", "app/services/qdrant_service.py")


# ---------------------------------------------------------------------------
def _resultado(ns, i, rrf):
    """O formato exato que `qdrant_service.search_similar` devolve."""
    return {
        "score": rrf, "score_scale": "rrf", "namespace": ns,
        "content": f"trecho {ns} {i}", "document_id": f"{ns}-{i}",
        "chunk_index": 0, "agent_id": None, "metadata": {},
    }


def teste_a_cota_poe_o_contrato_na_mesa():
    print("\n[1] A carta curta ganha o RRF — e o contrato entra assim mesmo")

    # O acervo, na ordem em que o RRF entrega hoje: as cartas primeiro (sao
    # 12.063, curtas, e o BM25 as favorece), o contrato depois.
    lista = ([_resultado("cards", i, 0.033 - i * 0.001) for i in range(12)]
             + [_resultado("normative", i, 0.018 - i * 0.001) for i in range(6)]
             + [_resultado(None, i, 0.016) for i in range(3)])

    escolhidos = KS.selecionar_com_cota(lista)
    faixas = [str(r.get("namespace") or "local") for r in escolhidos]

    checar(faixas.count("normative") == KS.COTA_FINAL[KS.NAMESPACE_NORMATIVE],
           "o contrato ocupa a cota inteira dele",
           f"{faixas.count('normative')} vagas de contrato em {len(escolhidos)}")
    checar(faixas.count("cards") == KS.COTA_FINAL[KS.NAMESPACE_CARDS],
           "e a carta ocupa a dela — nem mais, nem menos",
           f"{faixas.count('cards')} de {len([r for r in lista if r['namespace'] == 'cards'])} candidatas")
    checar(faixas.count("local") == KS.COTA_FINAL_OUTROS,
           "e o documento da propria corretora nao e espremido para fora",
           "ele nao tem namespace, e e o material mais especifico que existe")

    # 🔴 A LINHA DE CONTROLE. Sem cota por faixa — uma vaga so, do tamanho que
    # o sistema usava — a MESMA lista devolve tres cartas e zero contrato. E a
    # prova de que o merito e da cota, e nao do acervo de mentira: se este
    # `checar` passasse com contrato dentro, o teste nao estaria medindo nada.
    antigo = KS.selecionar_com_cota(lista, cotas={}, cota_outros=3)
    checar(len(antigo) == 3 and all(r["namespace"] == "cards" for r in antigo),
           "CONTROLE — sem cota, as 3 vagas sao todas da carta curta",
           "e exatamente o comportamento de ontem, reproduzido na mesma lista")

    # CONTROLE — a ordem de ranking e preservada. Reordenar aqui apagaria o
    # trabalho do reranker (ou o BM25 embutido no RRF).
    checar([r["document_id"] for r in escolhidos]
           == [r["document_id"] for r in lista if r in escolhidos],
           "CONTROLE — a ordem recebida e preservada")


def teste_vaga_reservada_e_nao_usada_nao_e_desperdicada():
    print("\n[2] Pergunta sem contrato que responda continua respondida")

    # "Como funciona a vistoria complementar?" nao tem clausula que responda —
    # e a maioria das perguntas de procedimento. A cota do normativo fica vazia.
    so_cartas = [_resultado("cards", i, 0.033 - i * 0.001) for i in range(20)]
    escolhidos = KS.selecionar_com_cota(so_cartas)

    total = sum(KS.COTA_FINAL.values()) + KS.COTA_FINAL_OUTROS
    checar(len(escolhidos) == total,
           "a sobra da faixa vazia vira vaga de quem tem candidato",
           f"{len(escolhidos)} de {total} vagas preenchidas, todas por carta")
    checar(all(r["namespace"] == "cards" for r in escolhidos),
           "e nenhuma vaga fica reservada para o vazio",
           "cota que nao redistribui e conhecimento jogado fora")

    # CONTROLE — o teste consegue reprovar: acervo menor que a cota nao inventa
    # resultado do nada.
    checar(len(KS.selecionar_com_cota(so_cartas[:2])) == 2,
           "CONTROLE — duas cartas no acervo devolvem duas, nao oito")
    checar(KS.selecionar_com_cota([]) == [],
           "CONTROLE — acervo vazio devolve vazio")


def teste_o_filtro_de_namespace_tem_dois_bracos():
    print("\n[3] 'Desta faixa OU sem faixa' — nunca 'so desta'")
    fonte = _fonte("app/services/qdrant_service.py")
    arvore = ast.parse(fonte)
    corpo = ""
    assinatura: list = []
    corpo_busca = ""
    for no in ast.walk(arvore):
        if isinstance(no, ast.FunctionDef) and no.name == "_filtro_de_namespace":
            corpo = ast.get_source_segment(fonte, no) or ""
        if isinstance(no, ast.FunctionDef) and no.name == "search_similar":
            assinatura = [a.arg for a in no.args.args] + [a.arg for a in no.args.kwonlyargs]
            corpo_busca = ast.get_source_segment(fonte, no) or ""

    checar("should=[" in corpo,
           "os dois bracos sao um `should` (OU), nao um `must` (E)",
           "um `must` puro apagaria todo ponto sem a chave")
    checar("IsEmptyCondition" in corpo and 'key="namespace"' in corpo,
           "e o segundo braco e 'sem faixa declarada'")
    checar("IsEmptyCondition is None" in corpo and corpo.count("return None") >= 2,
           "sem IsEmptyCondition, abandona o filtro inteiro",
           "voltar ao defeito conhecido e melhor que inventar um pior")

    checar("namespace" in assinatura,
           "`search_similar` aceita `namespace`",
           "sem isto, passar o argumento levantaria TypeError em producao")
    checar("_filtro_de_namespace(namespace)" in corpo_busca
           and "must_conditions.append(filtro_namespace)" in corpo_busca,
           "CONTROLE — e o filtro entra nas condicoes da busca",
           "parametro recebido e ignorado foi o defeito de origem do `carrier_slug`")
    checar('"namespace": result.payload.get("namespace")' in corpo_busca,
           "e a faixa volta no resultado",
           "sem ela, `selecionar_com_cota` nao tem como distribuir vaga nenhuma")

    ks = _fonte("app/services/knowledge_scope.py")
    checar('kwargs["namespace"] = faixa' in ks,
           "`build_global_search_kwargs` PASSA o namespace em vez de reserva-lo",
           "ficou 'reservado para filtragem fina' por mais de um ciclo")


def teste_nenhuma_faixa_fica_sem_ser_procurada():
    print("\n[4] Todo namespace que o sistema ESCREVE tem uma busca que o LE")

    # A busca global passou a ser feita por faixa. Um namespace que nao apareca
    # em faixa nenhuma nao e filtrado errado — ele simplesmente NAO E PROCURADO,
    # e some do RAG sem erro nenhum. Este guarda le os escritores de verdade.
    escritos = set()
    for caminho in (RAIZ / "app").rglob("*.py"):
        for achado in re.findall(r'"namespace":\s*"([a-z_]+)"',
                                 caminho.read_text(encoding="utf-8")):
            escritos.add(achado)

    cobertos = {n for _rotulo, faixa, _cota in KS.ORCAMENTO_GLOBAL for n in faixa}
    descobertos = sorted(escritos - cobertos)

    checar(len(escritos) >= 3,
           "os escritores de namespace foram encontrados na fonte",
           f"{sorted(escritos)}")
    checar(not descobertos,
           "todo namespace escrito e procurado por alguma faixa",
           f"cobertos: {sorted(cobertos)}")
    checar(escritos <= set(KS.NAMESPACES_CONHECIDOS),
           "e a lista canonica de namespaces esta completa",
           f"{sorted(KS.NAMESPACES_CONHECIDOS)}")

    # 🔴 CONTROLE — o guarda consegue reprovar. Um namespace inventado, que
    # nenhuma faixa procura, tem de ser apontado. Sem esta linha, o `checar`
    # acima passaria tambem num sistema onde `ORCAMENTO_GLOBAL` fosse vazio e
    # `escritos` tambem — e nao guardaria nada.
    checar(bool({"faceta_nova"} - cobertos),
           "CONTROLE — um namespace fora das faixas E detectado",
           "e a diferenca entre um guarda e um comentario")


def teste_os_indices_existem_e_sao_conferidos():
    print("\n[5] Indice de payload: medido no servidor, nao no log")

    esperados = {campo for campo, _ in QS._INDICES_DE_PAYLOAD}
    for campo in ("insurer_key", "namespace", "scope", "curation_status",
                  "vigente", "faceta"):
        checar(campo in esperados, f"`{campo}` entrou na tabela de indices",
               "filtro sem indice sobre 23.478 pontos e varredura")
    for campo in ("document_id", "agent_id", "metadata.file_type"):
        checar(campo in esperados, f"CONTROLE — `{campo}` continua indexado",
               "os tres antigos nao podem ter sumido no caminho")

    # `verificar_indices` de VERDADE, contra um servidor de mentira que declara
    # o que tem. E a medicao que `_create_indexes` nao sabe fazer.
    svc = QS.QdrantService.__new__(QS.QdrantService)

    class _ClienteCompleto:
        def get_collection(self, collection_name):
            return _Obj(payload_schema={c: _Obj(data_type="keyword")
                                        for c in esperados})

    class _ClienteIncompleto:
        def get_collection(self, collection_name):
            return _Obj(payload_schema={"document_id": _Obj(data_type="keyword")})

    class _ClienteQuebrado:
        def get_collection(self, collection_name):
            raise RuntimeError("colecao inacessivel")

    svc.client = _ClienteCompleto()
    completo = svc.verificar_indices("autobrokers_global")
    checar(completo["completo"] and not completo["faltando"],
           "servidor com tudo indexado responde `completo`")

    svc.client = _ClienteIncompleto()
    parcial = svc.verificar_indices("autobrokers_global")
    checar(not parcial["completo"] and "namespace" in parcial["faltando"],
           "CONTROLE — servidor sem os indices NOVOS reprova, e diz quais",
           f"faltando: {len(parcial['faltando'])} campos")

    # 🔴 CONTROLE DO MECANISMO. Erro ao ler o schema nao pode virar "completo":
    # seria a mesma mentira do `logger.debug` que engole tudo, com outra roupa.
    svc.client = _ClienteQuebrado()
    quebrado = svc.verificar_indices("autobrokers_global")
    checar(not quebrado["completo"] and quebrado["presentes"] == [],
           "CONTROLE — erro de leitura vira 'nao sei', nunca 'esta tudo la'")

    # E a razao de `verificar_indices` existir continua verdadeira: quem cria
    # engole a excecao e nao tem como distinguir "ja existe" de "falhou".
    fonte = _fonte("app/services/qdrant_service.py")
    criador = fonte[fonte.index("def _create_indexes"):fonte.index("def indices_existentes")]
    checar("logger.debug" in criador and "except Exception" in criador,
           "CONTROLE — `_create_indexes` continua engolindo excecao",
           "e por isso que a prova tem de vir do payload_schema")


def _rerank_serv(chave, resposta=None, explode=False):
    """Um RerankService real, com a chave e o Cohere que este caso pede."""
    class _ClienteCohere:
        def __init__(self, *a, **k):
            self.recebido = None

        def rerank(self, model, query, documents, top_n):
            if explode:
                raise RuntimeError("429 rate limit")
            self.recebido = {"model": model, "n_docs": len(documents), "top_n": top_n}
            return _Obj(results=resposta or [])

    _stub("cohere", Client=_ClienteCohere)
    _SETTINGS.COHERE_API_KEY = chave
    rs = _carregar("app.services.rerank_service", "app/services/rerank_service.py")
    return rs.RerankService()


def teste_o_reranker_se_comporta_nos_dois_estados():
    print("\n[6] Com chave e sem chave — os dois estados sao testados")

    docs = [{"content": "trecho A", "namespace": "cards"},
            {"content": "trecho B", "namespace": "normative"},
            {"content": "trecho C", "namespace": "cards"}]

    # ---- ESTADO A: sem chave. E o estado de producao hoje. -----------------
    sem = _rerank_serv(None)
    checar(sem.is_available() is False, "sem chave, o reranker se declara ausente")
    saude_sem = sem.health()
    checar(saude_sem["configured"] is False and saude_sem["status"] == "missing_key",
           "e o health diz `missing_key`")
    checar(saude_sem["safe_to_run"] is True,
           "mas `safe_to_run` continua True — o RAG nao depende dele",
           "ha cosseno denso, corte por escala e lexical rescue depois")

    saida_sem = sem.rerank("pergunta", [dict(d) for d in docs], top_k=len(docs))
    checar([d["content"] for d in saida_sem] == [d["content"] for d in docs],
           "e a ordem recebida atravessa intacta (pass-through)")
    checar(all("rerank_score" not in d for d in saida_sem),
           "sem inventar `rerank_score`",
           "score falso mandaria o corte para a escala errada — o P0 de 05/08")

    # ---- ESTADO B: com chave. E o estado quando a variavel entrar. ---------
    # Cohere devolve os indices REORDENADOS: o trecho normativo (indice 1) em
    # primeiro. E isto que a chave compra.
    com = _rerank_serv("chave-de-mentira-nunca-impressa",
                       resposta=[_Obj(index=1, relevance_score=0.91),
                                 _Obj(index=0, relevance_score=0.44),
                                 _Obj(index=2, relevance_score=0.12)])
    checar(com.is_available() is True, "com chave, o reranker fica disponivel")
    checar(com.health()["status"] == "ok" and com.health()["provider"] == "cohere",
           "e o health diz `ok`")

    saida_com = com.rerank("pergunta", [dict(d) for d in docs], top_k=len(docs))
    checar([d["content"] for d in saida_com] == ["trecho B", "trecho A", "trecho C"],
           "e a lista sai REORDENADA por relevancia",
           "sem a chave, `docs[:3]` nao reordena nada")
    checar(all(0.0 <= d["rerank_score"] <= 1.0 for d in saida_com),
           "com `rerank_score` na escala 0..1",
           "e a escala para a qual os cortes 0,50/0,40/0,30 foram calibrados")

    # 🔴 CONTROLE — as duas saidas TEM de ser diferentes. Um guarda que compara
    # duas coisas incapazes de divergir nao guarda nada (CLAUDE.md §9.3).
    checar([d["content"] for d in saida_sem] != [d["content"] for d in saida_com],
           "CONTROLE — os dois estados produzem resultados diferentes",
           "se fossem iguais, este teste passaria sem medir a chave")

    # ---- ESTADO C: chave presente, API caindo. -----------------------------
    caindo = _rerank_serv("chave-de-mentira-nunca-impressa", explode=True)
    saida_caindo = caindo.rerank("pergunta", [dict(d) for d in docs], top_k=2)
    checar(len(saida_caindo) == 2 and saida_caindo[0]["content"] == "trecho A",
           "API caindo volta ao pass-through sem derrubar a busca",
           "falha de terceiro nao pode virar pergunta sem resposta")

    # ---- 🔴 O SEGREDO NUNCA APARECE (CLAUDE.md §13.3) ---------------------
    segredo = "chave-de-mentira-nunca-impressa"
    checar(segredo not in repr(com.health()),
           "o health NAO devolve o valor da chave — so presenca/ausencia")
    fonte_rr = _fonte("app/services/rerank_service.py")
    checar("api_key" not in fonte_rr.split("logger.info")[1][:200]
           if "logger.info" in fonte_rr else True,
           "e nenhum log imprime a chave")
    checar("self.api_key" in fonte_rr and f'"{segredo}"' not in fonte_rr,
           "CONTROLE — a chave e lida de `settings`, nunca escrita no codigo")

    # A borda esta pronta: o pacote e declarado, o campo existe, o .env
    # documenta. Falta a VARIAVEL no ambiente — e um restart, porque o servico
    # e singleton e le `settings` uma vez.
    checar("cohere" in _fonte("requirements.txt"),
           "o pacote `cohere` esta declarado em requirements.txt")
    checar("COHERE_API_KEY" in _fonte("app/core/config.py"),
           "e o campo existe em `Settings`")
    checar("COHERE_API_KEY" in _fonte(".env.example"),
           "e o .env.example documenta a variavel")
    checar("_rerank_service is None" in _fonte("app/services/rerank_service.py"),
           "CONTROLE — o servico e singleton: a chave so entra com restart",
           "trocar a env sem reiniciar nao liga o reranker")


def teste_a_busca_global_faz_uma_ida_por_faixa():
    print("\n[7] Um embedding, duas buscas — e nenhum motor paralelo")
    ss = _fonte("app/services/search_service.py")
    codigo = "\n".join(l for l in ss.split("\n") if not l.lstrip().startswith("#"))

    checar("for rotulo, faixa, cota in ORCAMENTO_GLOBAL:" in codigo,
           "a busca global percorre as faixas do orcamento")
    checar(codigo.count("dense_vector = self.embeddings.embed_query") == 1,
           "CONTROLE — o embedding e gerado UMA vez",
           "duas buscas nao podem custar dois embeddings")
    checar(codigo.count("self.qdrant.search_similar(") >= 2
           and "class QdrantService" not in ss,
           "CONTROLE — e as duas idas usam o MESMO `search_similar`",
           "CLAUDE.md §5: evolucao do motor que existe, nunca um segundo")
    # Lido no CODIGO, nao na fonte crua: a linha antiga sobrevive de proposito
    # dentro do comentario que conta por que ela saiu.
    checar("top_k=3," not in codigo and "selecionar_com_cota(ordenados)" in codigo,
           "o corte final passou de `top_k=3` para o orcamento por faixa")
    checar("top_k=len(initial_results)" in codigo,
           "e o reranker passou a ORDENAR a lista inteira",
           "ordenar e cortar eram a mesma linha; agora sao dois passos")

    lc = _fonte("app/services/langchain_service.py")
    checar("ORCAMENTO_GLOBAL" in lc,
           "e o segundo caminho global recebeu a mesma regra",
           "consertar metade deixaria o defeito onde ninguem olha")


def main() -> int:
    print("=" * 74)
    print("O CONTRATO E A CARTA NAO DISPUTAM A MESMA VAGA")
    print("=" * 74)
    teste_a_cota_poe_o_contrato_na_mesa()
    teste_vaga_reservada_e_nao_usada_nao_e_desperdicada()
    teste_o_filtro_de_namespace_tem_dois_bracos()
    teste_nenhuma_faixa_fica_sem_ser_procurada()
    teste_os_indices_existem_e_sao_conferidos()
    teste_o_reranker_se_comporta_nos_dois_estados()
    teste_a_busca_global_faz_uma_ida_por_faixa()

    print("\n" + "=" * 74)
    if _PROBLEMAS:
        print(f"{len(_PROBLEMAS)} PROBLEMA(S):")
        for p in _PROBLEMAS:
            print(f"  - {p}")
        return 1
    print("TUDO VERDE — cada faixa tem o proprio orcamento, ate a vaga final.")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sys.exit(main())
