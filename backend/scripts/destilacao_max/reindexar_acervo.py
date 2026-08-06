"""Reescreve no Qdrant as cartas cujo rotulo mudou no banco.

    python backend/scripts/destilacao_max/reindexar_acervo.py            # so mostra
    python backend/scripts/destilacao_max/reindexar_acervo.py --aplicar  # escreve

POR QUE ISTO PRECISA EXISTIR
----------------------------
Em 05/08/2026 o acervo foi corrigido no banco: `insurer_key` caiu de 3.760 para
1.158 (o campo guardava "apareceu numa conversa sobre a Allianz" e prometia "e
regra da Allianz"), e `category` saiu de um valor morto para cinco momentos.

**O banco nao e onde a busca le.** `publish_card_sync` grava o rotulo DENTRO do
texto do chunk — `"(allianz / auto / cobranca) <a carta>"` — porque o BM25 casa
palavra exata e nao enxerga metadado. Enquanto o indice nao for reescrito, uma
pergunta sobre "boleto da Allianz" continua casando lexicalmente com as cartas
genericas que perderam o rotulo no banco.

    o banco esta limpo    ✅
    o indice, nao         ❌   ← e a busca le o indice

POR QUE E SEGURO
----------------
`publish_card_sync` grava com `document_id = f"card-{id}"`. Reescrever a mesma
carta SOBRESCREVE o mesmo ponto — nao duplica, nao apaga o vizinho, e rodar duas
vezes da o mesmo resultado. Se o processo cair no meio, e so rodar de novo: o
arquivo de progresso pula o que ja foi.

Nao ha exclusao em lugar nenhum deste script. O pior caso e um ponto reescrito
identico ao que ja estava la.

ONDE RODAR
----------
No contêiner de producao (`smith-worker` ou `smith-api`) — e o unico lugar onde
Qdrant e a chave da OpenAI existem. Numa maquina de desenvolvimento sem `.env`
o script recusa e diz por que, em vez de gravar pela metade.

CUSTO
-----
Embedding de ~10.800 cartas curtas com `text-embedding-3-small`.
💭 ~1,3 milhao de tokens a US$ 0,02/milhao = **~US$ 0,03**. O `--aplicar` imprime
a estimativa e espera confirmacao antes de gastar.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve()
BACKEND = AQUI.parents[2]
sys.path.insert(0, str(BACKEND))

PROGRESSO = AQUI.parent / ".reindexacao_feita.txt"
CUSTO_POR_MILHAO = 0.02
TOKENS_POR_CARTA = 120  # 💭 estimativa: carta curta + prefixo de rotulo


def _banco():
    """O MESMO caminho que `aplicar.py` e `exportar.py` usam — não um segundo.

    A primeira versão deste script importava `app.services.supabase_service`,
    que **não existe**: o nome foi inventado por analogia. Morreu em produção com
    `ModuleNotFoundError` antes de imprimir uma linha sequer. Os scripts vizinhos
    desta pasta sempre leram a credencial do ambiente e montaram o cliente com o
    SDK — é esse o caminho, e ele agora é reusado em vez de reescrito.
    """
    sys.path.insert(0, str(AQUI.parent))
    from exportar import _credenciais  # noqa: E402 — vizinho, não pacote

    url, key = _credenciais()
    from supabase import create_client

    return create_client(url, key)


def _diagnostico() -> int:
    """As três portas, ANTES de gastar qualquer coisa.

    Pedido certo: em produção não se descobre que falta uma variável de
    ambiente no meio de 10.800 embeddings pagos.
    """
    print("== diagnóstico: as três portas ==\n")
    falhou = False

    try:
        db = _banco()
        n = (db.table("knowledge_cards").select("id", count="exact")
             .eq("status", "published").limit(1).execute()).count
        print(f"  [ok] Supabase ....... {n:,} cartas publicadas")
    except Exception as exc:  # noqa: BLE001
        print(f"  [X]  Supabase ....... {type(exc).__name__}: {exc}")
        falhou = True

    try:
        from app.services.qdrant_service import get_qdrant_service

        cols = get_qdrant_service().client.get_collections()
        nomes = [c.name for c in cols.collections]
        tem = "autobrokers_global" in nomes
        print(f"  [{'ok' if tem else 'X'}] Qdrant ......... {len(nomes)} coleções"
              f"{' · autobrokers_global presente' if tem else ' · SEM autobrokers_global'}")
        falhou = falhou or not tem
    except Exception as exc:  # noqa: BLE001
        print(f"  [X]  Qdrant ......... {type(exc).__name__}: {exc}")
        falhou = True

    try:
        from langchain_openai import OpenAIEmbeddings

        from app.core.config import settings

        v = OpenAIEmbeddings(model="text-embedding-3-small",
                             api_key=settings.OPENAI_API_KEY).embed_documents(["teste"])
        print(f"  [ok] OpenAI ......... embedding de {len(v[0])} dimensões")
    except Exception as exc:  # noqa: BLE001
        print(f"  [X]  OpenAI ......... {type(exc).__name__}: {exc}")
        falhou = True

    try:
        from app.services.attendance_distiller import publish_card_sync  # noqa: F401

        print("  [ok] publish_card_sync importa")
    except Exception as exc:  # noqa: BLE001
        print(f"  [X]  publish_card_sync . {type(exc).__name__}: {exc}")
        falhou = True

    print("\n" + ("ALGUMA PORTA FECHADA — não rode --aplicar." if falhou
                  else "As três portas abertas. Pode seguir para a simulação."))
    return 1 if falhou else 0


def _ler_publicadas(db) -> list:
    """Todas as cartas publicadas, paginadas por `id`.

    Por `id` e nao por `created_at`: paginar por data perdia linha quando
    varias cartas nasciam no mesmo instante — 11.640 lidas, 11.628 distintas.
    Uma carta que a varredura nao ve e a que fica no indice com o rotulo velho
    para sempre, que e justamente o que este script existe para impedir.
    """
    todas, ultimo, pagina = [], "", 1000
    while True:
        q = (db.table("knowledge_cards")
             .select("id, card_text, insurer_key, ramo, category")
             .eq("status", "published").order("id").limit(pagina))
        if ultimo:
            q = q.gt("id", ultimo)
        linhas = (q.execute().data) or []
        if not linhas:
            break
        todas.extend(linhas)
        ultimo = linhas[-1]["id"]
        if len(linhas) < pagina:
            break
    return todas


def _ja_feitas() -> set:
    if not PROGRESSO.exists():
        return set()
    return {l.strip() for l in PROGRESSO.read_text(encoding="utf-8").splitlines() if l.strip()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--diagnostico", action="store_true",
                    help="so confere Supabase, Qdrant e OpenAI e sai")
    ap.add_argument("--aplicar", action="store_true", help="escreve no Qdrant")
    ap.add_argument("--sim", action="store_true", help="nao pergunta antes de gastar")
    ap.add_argument("--limite", type=int, default=0, help="para depois de N cartas (teste)")
    args = ap.parse_args()

    if args.diagnostico:
        return _diagnostico()

    # A recusa e deliberada: gravar metade do acervo e pior que nao gravar nada,
    # porque o indice fica com dois criterios convivendo e ninguem sabe qual
    # carta esta em qual.
    if args.aplicar and not (os.getenv("QDRANT_HOST") and os.getenv("OPENAI_API_KEY")):
        print("RECUSADO: QDRANT_HOST e OPENAI_API_KEY precisam existir.")
        print("Rode isto DENTRO do contêiner de producao (smith-worker/smith-api).")
        return 2

    db = _banco()
    cartas = _ler_publicadas(db)
    feitas = _ja_feitas()
    faltam = [c for c in cartas if str(c["id"]) not in feitas]
    if args.limite:
        faltam = faltam[:args.limite]

    tokens = len(faltam) * TOKENS_POR_CARTA
    print(f"publicadas no banco ....... {len(cartas):,}")
    print(f"ja reindexadas ............ {len(feitas):,}")
    print(f"a reindexar ............... {len(faltam):,}")
    print(f"custo estimado ............ US$ {tokens / 1_000_000 * CUSTO_POR_MILHAO:.3f}  (💭 estimativa)")

    com_rotulo = sum(1 for c in faltam if c.get("insurer_key"))
    print(f"  dessas, com seguradora .. {com_rotulo:,}")
    print(f"  sem seguradora .......... {len(faltam) - com_rotulo:,}  (viram fundo comum)")

    if not args.aplicar:
        print("\n(nada foi escrito — use --aplicar)")
        return 0
    if not faltam:
        print("\nnada a fazer.")
        return 0
    if not args.sim:
        print("\nEscrever no Qdrant agora? [s/N] ", end="")
        if (input().strip().lower() or "n") != "s":
            print("cancelado.")
            return 0

    from app.services.attendance_distiller import publish_card_sync

    ok = falhou = 0
    t0 = time.time()
    with PROGRESSO.open("a", encoding="utf-8") as reg:
        for i, carta in enumerate(faltam, 1):
            try:
                if publish_card_sync(carta):
                    ok += 1
                    # O registro sai ANTES do proximo passo, nao no fim do laco:
                    # se o processo morrer aqui, a carta ja gravada nao volta a
                    # ser cobrada da OpenAI na retomada.
                    reg.write(f"{carta['id']}\n")
                    reg.flush()
                else:
                    falhou += 1
            except Exception as exc:  # noqa: BLE001 — uma carta ruim nao para o acervo
                falhou += 1
                print(f"  [X] {carta['id']}: {type(exc).__name__}")
            if i % 250 == 0:
                print(f"  {i:,}/{len(faltam):,}  ok={ok:,} falhou={falhou:,}  "
                      f"{time.time() - t0:.0f}s")

    print(f"\nreindexadas {ok:,} · falhas {falhou:,} · {time.time() - t0:.0f}s")
    if falhou:
        print("Rode de novo: o progresso pula o que ja foi e retenta o resto.")
    return 1 if falhou and not ok else 0


if __name__ == "__main__":
    sys.exit(main())
