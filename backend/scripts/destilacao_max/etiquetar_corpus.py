"""Poe a etiqueta de seguradora nos 11.409 trechos de condicoes gerais.

    NO CONTEINER, so mostra o que faria:
        cd /app && python scripts/destilacao_max/etiquetar_corpus.py

    NO CONTEINER, grava:
        cd /app && python scripts/destilacao_max/etiquetar_corpus.py --aplicar

⚠️ O caminho no conteiner NAO tem `backend/` — `backend/Dockerfile` faz
`WORKDIR /app` + `COPY . .` a partir de `backend/`.

POR QUE ISTO EXISTE, E POR QUE NAO E UMA REINDEXACAO
----------------------------------------------------
📊 Medido no indice em 08/08/2026:

    autobrokers_global .......... 23.478 pontos
      namespace normative ....... 11.409   ← condicoes gerais e manuais
    com `insurer_key` na raiz ...      0

O filtro de seguradora casa `insurer_key` na RAIZ do payload e tem um braco
`IsEmpty` que significa "fato generico de mercado, vale para todas". Com a
etiqueta ausente, **todo trecho de condicoes gerais passava em qualquer
pergunta**: "a Porto cobre alagamento?" recebia a clausula da Allianz.

E e o pior material possivel para escapar. Uma carta generica e fato de
mercado, escrito com hesitacao; uma condicao geral e o **contrato** de uma
companhia, escrito com a autoridade de documento oficial.

**O texto e o vetor estao certos — so o rotulo esta no lugar errado.**
`insurance_corpus` gravava `insurer_key` dentro de `metadata`, e
`insert_embeddings` so promove `knowledge_extras` a raiz (corrigido em
3dae2a6, mas a correcao so vale para ingestao NOVA).

Por isso aqui se usa `set_payload`, nao re-ingestao: 📊 re-ingerir 11.409
chunks pagaria 11.409 embeddings de novo, sem mudar um bit do vetor. O
`set_payload` mexe so no rotulo, nao chama a OpenAI, e custa **zero**.

O QUE ELE NAO FAZ
-----------------
Nao apaga ponto, nao cria ponto, nao toca no texto nem no vetor. Acrescenta
duas chaves ao payload de pontos que ja existem. Rodar duas vezes escreve o
mesmo valor por cima — e o mesmo resultado.

E NAO ETIQUETA A SUSEP. 📊 5 documentos, 198 chunks — Resolucoes CNSP e
Circular SUSEP — valem para TODAS as companhias. Etiqueta-los trocaria um
vazamento por um APAGAO: a norma do regulador sumiria de toda pergunta sobre
qualquer seguradora. E o apagao e pior, porque ninguem percebe a resposta que
nao veio.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

AQUI = Path(__file__).resolve()
BACKEND = AQUI.parents[2]
sys.path.insert(0, str(BACKEND))

REGULADOR = "susep"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--aplicar", action="store_true", help="escreve no Qdrant")
    args = ap.parse_args()

    print("=" * 68)
    print("ETIQUETAR O CORPUS NORMATIVO" + ("  [APLICANDO]" if args.aplicar
                                            else "  [so mostrando]"))
    print("=" * 68)

    if not (os.getenv("QDRANT_HOST") or os.getenv("QDRANT_URL")):
        print("\n  X  QDRANT_HOST ausente — rode no conteiner de producao.")
        return 2

    from qdrant_client.models import FieldCondition, Filter, MatchValue

    from app.core.database import get_supabase_client
    from app.services.knowledge_scope import GLOBAL_COLLECTION
    from app.services.qdrant_service import get_qdrant_service

    cli = get_qdrant_service().client
    db = get_supabase_client().client

    docs = (db.table("normative_documents")
            .select("id, title, insurer_key, product_line, chunk_count")
            .eq("status", "ingested").limit(500).execute().data or [])
    print(f"\n  {len(docs)} documentos ingeridos no banco\n")

    tocados = pulados = pontos = 0
    for d in docs:
        slug = (d.get("insurer_key") or "").strip().lower()
        ramo = (d.get("product_line") or "").strip().lower()
        nome = (d.get("title") or "")[:52]

        if not slug or slug == REGULADOR:
            print(f"  -- pula  {nome:<52} ({slug or 'sem seguradora'})")
            pulados += 1
            continue

        alvo = Filter(must=[FieldCondition(key="document_id",
                                           match=MatchValue(value=f"norm-{d['id']}"))])
        n = cli.count(collection_name=GLOBAL_COLLECTION,
                      count_filter=alvo, exact=True).count
        if not n:
            print(f"  !! ZERO  {nome:<52} — nenhum ponto no indice")
            continue

        etiqueta = {"insurer_key": slug}
        if ramo:
            etiqueta["product_line"] = ramo

        if args.aplicar:
            cli.set_payload(collection_name=GLOBAL_COLLECTION,
                            payload=etiqueta, points_selector=alvo, wait=True)
        print(f"  ok {n:>5}  {nome:<52} -> {slug}" + (f" / {ramo}" if ramo else ""))
        tocados += 1
        pontos += n

    print("\n" + "=" * 68)
    print(f"  documentos etiquetados: {tocados}   pontos: {pontos}")
    print(f"  pulados (SUSEP/sem seguradora): {pulados}")
    if not args.aplicar:
        print("\n  NADA FOI ESCRITO. Para gravar, rode de novo com --aplicar")
    else:
        print("\n  Confira com: python scripts/destilacao_max/conferir_indice.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
