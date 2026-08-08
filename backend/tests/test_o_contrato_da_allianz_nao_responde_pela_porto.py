"""O filtro de seguradora cobria 10% do índice. Os 90% eram o material mais específico.

A HISTÓRIA
==========
Em 06/08/2026 o RAG ganhou um filtro por seguradora: uma pergunta sobre a Porto
deixou de receber a regra da Allianz. O filtro tem dois braços:

    insurer_key == "porto"        o que é da Porto
    insurer_key ausente           fato genérico de mercado, vale para todas

O segundo braço é necessário — 📊 9.723 das 12.063 cartas são fato de mercado, e
sem ele o agente perderia 80% do acervo em qualquer pergunta com seguradora.

**Mas "ausente" é uma afirmação sobre a RAIZ do payload.** E o corpus normativo
— condições gerais, manuais do segurado — grava a etiqueta dentro de
`metadata`:

    metadata={..., "insurer_key": doc["insurer_key"], ...}   ← aninhado
    knowledge_extras={"scope": ..., "curation_status": ...}  ← só isto sobe

`qdrant_service.insert_embeddings` promove à raiz **apenas** o que vem por
`knowledge_extras`. Então, para o filtro, todo chunk de condições gerais tinha
`insurer_key` ausente — ou seja, **genérico** — e passava em toda pergunta.

📊 Medido em 07/08/2026:

    índice global                   ~23.472 pontos
    com etiqueta filtrável           2.340   (10,0%)
    condições gerais escapando      11.211   Porto 3.089 · Bradesco 2.632 ·
                                             Allianz 1.694 · Mapfre 1.430 ·
                                             Tokio 1.299 · Azul 1.067

**E é o pior material possível para escapar.** Uma carta genérica é fato de
mercado, escrito com hesitação. Uma condição geral é o **contrato** de uma
companhia, escrito com a autoridade de documento oficial. A pergunta *"a Porto
cobre alagamento?"* recebia de volta a cláusula da Allianz — e o agente não
tinha como desconfiar.

O CUIDADO QUE O CONSERTO EXIGIU
===============================
`susep` ocupa a coluna `insurer_key`, mas 📊 esses 5 documentos e 198 chunks são
Resoluções CNSP e Circular SUSEP: valem para TODAS as companhias. Etiquetá-los
junto com as seguradoras trocaria um vazamento por um **apagão** — a norma do
regulador sumiria de toda pergunta sobre qualquer seguradora. E o apagão é pior,
porque é silencioso: ninguém percebe a resposta que não veio.

O SEGUNDO DEFEITO — `pane_seca`
===============================
`infer_ramo_servico` devolve `pane_seca`. `corridor_playbooks` declara
`pane_seca` como ALIAS de `guincho` e nunca cria subserviço com esse nome. O
caminho do corredor normaliza; a busca do playbook consultava com o valor cru.

`auto/guincho` está ATIVO e nunca era lido numa pane seca — o mesmo string, dois
tratamentos opostos, no mesmo chamador.
"""

from __future__ import annotations

import ast
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CORPUS = os.path.join(RAIZ, "backend", "app", "services", "knowledge", "insurance_corpus.py")
QDRANT = os.path.join(RAIZ, "backend", "app", "services", "qdrant_service.py")
GRAPH = os.path.join(RAIZ, "backend", "app", "agents", "graph.py")
CORREDOR = os.path.join(RAIZ, "backend", "app", "services", "corridor_playbooks.py")
_PROBLEMAS: list = []


def checar(condicao: bool, o_que: str, evidencia: str = "") -> None:
    if condicao:
        print(f"  OK  {o_que}" + (f"  ({evidencia})" if evidencia else ""))
    else:
        print(f"  X   {o_que}" + (f"  ({evidencia})" if evidencia else ""))
        _PROBLEMAS.append(o_que)


def _ler(caminho: str) -> str:
    with open(caminho, encoding="utf-8") as arquivo:
        return arquivo.read()


def _chamada_de_insert() -> str:
    """O trecho da chamada a `insert_embeddings` no corpus normativo."""
    fonte = _ler(CORPUS)
    i = fonte.index("qdrant.insert_embeddings(")
    return fonte[i:fonte.index("\n    return len(chunks)", i)]


# ---------------------------------------------------------------------------
def teste_a_etiqueta_fica_onde_o_filtro_procura():
    print("\n[1] A condição geral deixa de passar como genérica")
    chamada = _chamada_de_insert()

    i_extras = chamada.index("knowledge_extras=")
    depois = chamada[i_extras:]
    checar('"insurer_key": doc["insurer_key"]' in depois,
           "`insurer_key` entra por `knowledge_extras`",
           "📊 11.211 chunks de condições gerais passavam como genéricos")
    checar('"product_line": doc["product_line"]' in depois,
           "e `product_line` também",
           "é o `ramo` do corpus — 8 valores contra 4 das cartas")

    # 🔴 CONTROLE DO MECANISMO — o teste só vale se `knowledge_extras` for MESMO
    # o que sobe para a raiz. Se `insert_embeddings` mudar, este conserto vira
    # decoração e ninguém percebe.
    q = _ler(QDRANT)
    checar("if knowledge_extras:" in q and "payload[_k] = _v" in q,
           "CONTROLE — e é `knowledge_extras` que vai para a RAIZ do payload",
           "qdrant_service: metadata fica aninhado, extras sobe")
    checar('"metadata": chunk_metadata,' in q,
           "CONTROLE — enquanto `metadata` continua aninhado",
           "era por isso que a etiqueta não era vista")

    # E o filtro procura na raiz, com o braço que deixa passar o ausente.
    checar('FieldCondition(key="insurer_key"' in q
           and 'IsEmptyCondition(is_empty=PayloadField(key="insurer_key"))' in q,
           "CONTROLE — o filtro casa na raiz e deixa passar o ausente",
           "'ausente' significa genérico: é o braço que era explorado sem querer")


def teste_o_regulador_nao_e_uma_seguradora():
    print("\n[2] A norma da SUSEP vale para todas — e continua valendo")
    fonte = _ler(CORPUS)
    chamada = _chamada_de_insert()

    checar('_REGULADOR = "susep"' in fonte,
           "o regulador tem nome próprio no código")
    checar('doc["insurer_key"] != _REGULADOR' in chamada,
           "e NÃO recebe etiqueta de seguradora",
           "📊 5 documentos, 198 chunks: Resoluções CNSP e Circular SUSEP")

    # CONTROLE — é uma exceção de UM valor, não uma lista que vai crescer sem
    # dono. Se virar lista, cada nome novo nela some do filtro em silêncio.
    checar(fonte.count("_REGULADOR") <= 4,
           "CONTROLE — é uma exceção de um valor só",
           "lista de exceções cresce e cada item some do filtro calado")


def teste_pane_seca_encontra_o_playbook_do_guincho():
    print("\n[3] `pane_seca` chega em `auto/guincho`")
    g = _ler(GRAPH)

    checar("from app.services.corridor_playbooks import canonical_subservice" in g
           and "servico = canonical_subservice(servico) if servico else servico" in g,
           "a busca do playbook normaliza o subserviço",
           "`auto/guincho` está ATIVO e não era lido numa pane seca")

    # A tradução é REUSADA, não copiada. Um dicionário novo aqui seria a
    # segunda descrição da mesma coisa — a doença do dia.
    checar('"pane_seca": "guincho"' not in g,
           "e NÃO copia o dicionário de tradução",
           "duas descrições da mesma coisa divergem — a lição do Lapidador")

    # CONTROLE — a tradução existe do outro lado e faz o que se espera.
    c = _ler(CORREDOR)
    checar('"pane_seca": "guincho"' in c and "def canonical_subservice(" in c,
           "CONTROLE — e a tradução existe e é dela que se importa")

    # CONTROLE — nome desconhecido passa inalterado. Se `canonical_subservice`
    # chutasse, `cobranca` (que não é subserviço de corredor) viraria outra
    # coisa e a busca do playbook quebraria no caminho que consertamos hoje.
    fonte_c = c[c.index("def canonical_subservice("):]
    fim = fonte_c.index("\n\n\n") if "\n\n\n" in fonte_c else len(fonte_c)
    checar(".get(" in fonte_c[:fim],
           "CONTROLE — e nome desconhecido passa inalterado",
           "se ela chutasse, `cobranca` viraria outra coisa")


def main() -> int:
    print("=" * 70)
    print("O CONTRATO DA ALLIANZ NÃO RESPONDE PELA PORTO")
    print("=" * 70)
    teste_a_etiqueta_fica_onde_o_filtro_procura()
    teste_o_regulador_nao_e_uma_seguradora()
    teste_pane_seca_encontra_o_playbook_do_guincho()

    print("\n" + "=" * 70)
    if _PROBLEMAS:
        print(f"{len(_PROBLEMAS)} PROBLEMA(S):")
        for p in _PROBLEMAS:
            print(f"  - {p}")
        return 1
    print("TUDO VERDE — a etiqueta está onde o filtro procura.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
