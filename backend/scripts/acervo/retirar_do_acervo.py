"""Tira do acervo o documento que entrou e não devia. Ensaio seco por padrão.

    NO CONTEINER, so mostra o que faria:
        cd /app && python scripts/acervo/retirar_do_acervo.py --seguradora bradesco --ramo vida

    NO CONTEINER, retira de verdade:
        cd /app && python scripts/acervo/retirar_do_acervo.py --seguradora bradesco --ramo vida --aplicar

⚠️ O caminho no conteiner NAO tem `backend/` — o Dockerfile faz `WORKDIR /app`
+ `COPY . .` a partir de `backend/`.

POR QUE ISTO PRECISOU EXISTIR
-----------------------------
📊 11/08/2026. O comando de coleta rodou sem `--ramo` em quatro seguradoras e
trouxe **89 documentos de vida, 17.710 pedacos** — mais do que o acervo
conferido inteiro tinha (6.797). Para atender, medido no mesmo dia:

    cartas de conversa reais do Bradesco ....... 132
    dessas, que falam de vida .................    3

A regra ja estava escrita em `PLACAR-DO-ACERVO.md` §3 desde 08/08 — *"de vida,
entra o produto que o acervo de conversas mostra que os clientes perguntam"* —
e o comando nao a aplicou. Faltava, dos dois lados, a forma de desfazer.

> **Todo caminho que ESCREVE no acervo precisa de um que RETIRE.** Sem isso,
> um comando errado nao tem conserto, e a unica saida vira "deixa la".

O QUE ELE FAZ, NESTA ORDEM
--------------------------
1. retira os pontos do Qdrant (a busca para de ver na hora)
2. fecha a versao no Supabase com `superseded_at` (fato NOSSO: retiramos)
3. marca o documento como `archived`

O PDF continua no MinIO e a linha continua no banco. **Nada e apagado** — e a
mesma decisao D-Acervo-02 que vale para versao substituida: documento fora da
busca vai para o arquivo morto, nao para o lixo. Voltar e re-coletar.

A ORDEM IMPORTA: Qdrant primeiro. Ao contrario, uma falha no meio deixaria o
banco dizendo "arquivado" com os pedacos ainda respondendo — o pior estado
possivel, porque e invisivel.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

COLECAO_GLOBAL = "autobrokers_global"


def _agora() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def alvos(db, seguradora: str, ramo: str, manter: int) -> List[Dict[str, Any]]:
    """Os documentos que sairiam. Puro select — nao escreve nada.

    `manter` guarda os N com MAIOR vigencia (os mais atuais), porque quando se
    corta um ramo inteiro o que sobra tem de ser o que responde hoje.
    """
    q = (db.table("normative_documents")
         .select("id, insurer_key, product_line, title, status")
         .eq("insurer_key", seguradora).eq("status", "ingested"))
    if ramo:
        q = q.eq("product_line", ramo)
    docs = q.execute().data or []
    if not docs:
        return []

    versoes = (db.table("normative_document_versions")
               .select("document_id, version, qdrant_doc_id, chunk_count, "
                       "effective_from")
               .in_("document_id", [d["id"] for d in docs])
               .is_("superseded_at", "null").execute().data or [])
    por_doc = {v["document_id"]: v for v in versoes}

    saida = []
    for d in docs:
        v = por_doc.get(d["id"])
        if not v:
            continue
        saida.append({**d, **{k: v.get(k) for k in
                              ("version", "qdrant_doc_id", "chunk_count",
                               "effective_from")}})

    # os mais atuais primeiro; `manter` corta do topo
    saida.sort(key=lambda x: (x.get("effective_from") or "", x.get("chunk_count") or 0),
               reverse=True)
    if manter > 0:
        guardados = saida[:manter]
        print("  MANTIDOS (%d mais atuais):" % len(guardados))
        for g in guardados:
            print("    · %-46s %s · %d pedacos"
                  % ((g.get("title") or "")[:46], g.get("effective_from") or "?",
                     g.get("chunk_count") or 0))
        print()
        saida = saida[manter:]
    return saida


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seguradora", required=True)
    ap.add_argument("--ramo", default="", help="so este product_line (ex.: vida)")
    ap.add_argument("--manter", type=int, default=0,
                    help="guarda os N documentos de vigencia mais recente")
    ap.add_argument("--aplicar", action="store_true",
                    help="sem isto, so mostra o que faria")
    args = ap.parse_args()

    try:
        from app.core.database import get_supabase_client
        from app.services.qdrant_service import QdrantService
    except Exception as exc:  # noqa: BLE001
        print("Nao consegui carregar o app (%s: %s)." % (type(exc).__name__, exc))
        print("Este comando roda DENTRO do conteiner: cd /app && python "
              "scripts/acervo/retirar_do_acervo.py ...")
        return 1

    db = get_supabase_client()
    lista = alvos(db, args.seguradora, args.ramo, args.manter)
    if not lista:
        print("Nada a retirar para %s%s."
              % (args.seguradora, (" / " + args.ramo) if args.ramo else ""))
        return 0

    total = sum(d.get("chunk_count") or 0 for d in lista)
    print("=" * 74)
    print("RETIRAR DO ACERVO — %s%s"
          % (args.seguradora, (" / " + args.ramo) if args.ramo else ""))
    print("=" * 74)
    for d in lista:
        print("  %-48s %s · %d pedacos"
              % ((d.get("title") or "")[:48], d.get("effective_from") or "sem data",
                 d.get("chunk_count") or 0))
    print("-" * 74)
    print("%d documento(s) · %d pedacos" % (len(lista), total))

    if not args.aplicar:
        print()
        print("ENSAIO SECO — nada foi tocado. Para valer, repita com --aplicar")
        return 0

    company = (os.getenv("GLOBAL_KNOWLEDGE_COMPANY_ID") or "").strip() \
        or "autobrokers-global"
    qdrant = QdrantService()
    saiu = falhou = 0
    for d in lista:
        doc_id = d.get("qdrant_doc_id")
        # 1) Qdrant PRIMEIRO — ver o cabecalho deste arquivo
        if doc_id:
            try:
                qdrant.delete_document(company, doc_id,
                                       collection_name=COLECAO_GLOBAL)
            except Exception as exc:  # noqa: BLE001
                # o tipo E a mensagem: `except` que engole motivo ja custou
                # oito dias de silencio neste repositorio
                print("  ⛔ %s NAO saiu do indice (%s: %s) — documento NAO "
                      "arquivado, os pedacos continuam respondendo"
                      % (doc_id, type(exc).__name__, exc))
                falhou += 1
                continue
        # 2) fecha a versao  3) arquiva o documento
        agora = _agora()
        db.table("normative_document_versions").update(
            {"superseded_at": agora}).eq("document_id", d["id"]) \
            .is_("superseded_at", "null").execute()
        db.table("normative_documents").update(
            {"status": "archived", "updated_at": agora}) \
            .eq("id", d["id"]).execute()
        saiu += 1
        print("  ✅ %-44s retirado" % (d.get("title") or "")[:44])

    print("-" * 74)
    print("retirados: %d · falharam: %d" % (saiu, falhou))
    print("O PDF continua no MinIO e a linha continua no banco (status "
          "`archived`). Voltar = re-coletar.")
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(main())
