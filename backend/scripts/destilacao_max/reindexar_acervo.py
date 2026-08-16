"""Reescreve no Qdrant as cartas cujo rotulo mudou no banco.

    NA SUA MAQUINA (so mostra, e recusa gravar sem .env):
        python backend/scripts/destilacao_max/reindexar_acervo.py

    NO CONTEINER de producao, que e o unico lugar onde isto grava:
        cd /app && python scripts/destilacao_max/reindexar_acervo.py
        cd /app && python scripts/destilacao_max/reindexar_acervo.py --aplicar

⚠️ O caminho MUDA entre os dois, e a diferenca ja custou uma ida ao terminal em
08/08/2026. `backend/Dockerfile` faz `WORKDIR /app` + `COPY . .` a partir de
`backend/`: o conteudo de `backend/` **vira** o `/app`, e la dentro nao existe
pasta chamada `backend`. Um comando com `backend/` no meio devolve
`No such file or directory` — que parece deploy faltando e nao e.

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

    🔴 O SELECT E A LISTA DO QUE SOBREVIVE — 15/08/2026 (SPEC-072)
    ==============================================================
    Ate hoje ele pedia `id, card_text, insurer_key, ramo, category`, e o que
    nao entra no select some do indice, porque `insert_embeddings` faz `upsert`
    de PONTO INTEIRO (`qdrant_service.py:355`), nao `set_payload`. Reescrever
    uma carta com menos payload nao acrescenta: substitui.

    Duas colunas faltavam, e cada uma causava um dano diferente:

      source_unit_id   `publish_card_sync:571` faz
                       `documento_publico=bool(card.get("source_unit_id"))`.
                       Ausente => False => a rede de PII roda APERTADA numa
                       carta de condicao geral publica. 📊 Medido sobre as
                       5.394 cartas de acervo: **57 seriam RECUSADAS**, todas
                       da HDI, todas por `{CNPJ}` — e o `{CNPJ}` e o numero de
                       processo SUSEP (`15414.900228/2017-63`), que so parece
                       CNPJ para quem nao sabe que o documento e publico. O
                       script conta isso como `falhou` e segue: regressao de
                       PII silenciosa, com o nome errado.

      pii_check        e onde a `faceta` mora, porque `knowledge_cards` nao tem
                       coluna para ela. Sem ela no select, as 5.337 cartas
                       restantes voltam ao indice sem faceta e sem unit_id.

    📊 Alvo de um `--aplicar` antes do conserto: 100% das 5.394 cartas de acervo
    — 5.337 reescritas sem lastro + 57 falhas silenciosas.

    ⚠️ **O comando que produz estes numeros esta versionado ao lado**, porque
    numero medido sem base de prova preservada vira folclore no lote seguinte
    (`pedacos/README.md`) e a CLAUDE.md §12.1 exige a query junto:

        python backend/scripts/destilacao_max/medir_o_lastro.py
    """
    todas, ultimo, pagina = [], "", 1000
    while True:
        q = (db.table("knowledge_cards")
             .select("id, card_text, insurer_key, ramo, category, "
                     "source_unit_id, pii_check")
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


def _ja_feitas(db=None) -> set:
    """Quem ja foi reindexado — lendo o BANCO, e o arquivo so como reforco.

    🔴 08/08/2026 — O PROGRESSO MORRIA NO DEPLOY, E CUSTOU 109 MINUTOS
    ==================================================================
    O arquivo `.reindexacao_feita.txt` mora no filesystem do contêiner. O
    EasyPanel **recria o contêiner a cada deploy** — e o arquivo vai junto.

    📊 O que aconteceu: uma rodada completa reindexou 12.058 de 12.063 cartas
    em 6.560 segundos. Houve um deploy. A rodada seguinte, que devia retomar
    nas 5 que faltavam, imprimiu `ja reindexadas ...... 0` e refez as 12.063
    inteiras.

    Nao foi defeito do script: ele fez exatamente o que sabia fazer. Foi o
    lugar errado para guardar a memoria — **um arquivo dentro de algo que e
    apagado por desenho.**

    Agora a marca vive em `knowledge_cards.pii_check.reindexado_em`, no
    Postgres, que nenhum deploy toca. O arquivo continua sendo escrito porque
    e mais rapido de ler no meio de uma rodada, mas ele deixou de ser a
    verdade: se sumir, o banco responde.
    """
    do_arquivo = set()
    if PROGRESSO.exists():
        do_arquivo = {l.strip() for l in
                      PROGRESSO.read_text(encoding="utf-8").splitlines() if l.strip()}
    if db is None:
        return do_arquivo

    do_banco, ultimo, pagina = set(), None, 1000
    while True:
        q = (db.table("knowledge_cards").select("id")
             .eq("status", "published")
             .not_.is_("pii_check->>reindexado_em", "null")
             .order("id").limit(pagina))
        if ultimo:
            q = q.gt("id", ultimo)
        linhas = q.execute().data or []
        if not linhas:
            break
        do_banco.update(str(l["id"]) for l in linhas)
        ultimo = linhas[-1]["id"]
        if len(linhas) < pagina:
            break
    return do_arquivo | do_banco


def _hoje() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).date().isoformat()


def _marcar_no_banco(db, ids: list, quando: str) -> None:
    """Grava `pii_check.reindexado_em` — a memoria que sobrevive ao deploy.

    Le e reescreve `pii_check` de cada carta porque ele guarda outras marcas
    (`deterministic`, `prestadora`, `substituida_por`) que nao podem ser
    perdidas. Uma falha aqui nao derruba a rodada: o pior caso e reindexar
    essas cartas de novo, que custa embedding e nao estraga nada.
    """
    try:
        atuais = (db.table("knowledge_cards").select("id, pii_check")
                  .in_("id", ids).execute().data or [])
        for linha in atuais:
            marca = dict(linha.get("pii_check") or {})
            marca["reindexado_em"] = quando
            db.table("knowledge_cards").update(
                {"pii_check": marca}).eq("id", linha["id"]).execute()
    except Exception as exc:  # noqa: BLE001
        print(f"  [!] nao consegui marcar {len(ids)} no banco: {type(exc).__name__}"
              " — elas serao reindexadas de novo na proxima rodada")


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
    feitas = _ja_feitas(db)
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
    pendentes: list = []
    hoje = _hoje()
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
                    # E TAMBEM NO BANCO, que o deploy nao apaga. Em lote de 50
                    # para nao dobrar o numero de idas ao Postgres: perder ate
                    # 50 marcas numa queda custa 50 embeddings na retomada, e
                    # perder 12.058 custou 109 minutos.
                    pendentes.append(str(carta["id"]))
                    if len(pendentes) >= 50:
                        _marcar_no_banco(db, pendentes, hoje)
                        pendentes = []
                else:
                    falhou += 1
            except Exception as exc:  # noqa: BLE001 — uma carta ruim nao para o acervo
                falhou += 1
                print(f"  [X] {carta['id']}: {type(exc).__name__}")
            if i % 250 == 0:
                print(f"  {i:,}/{len(faltam):,}  ok={ok:,} falhou={falhou:,}  "
                      f"{time.time() - t0:.0f}s")
    if pendentes:
        _marcar_no_banco(db, pendentes, hoje)

    print(f"\nreindexadas {ok:,} · falhas {falhou:,} · {time.time() - t0:.0f}s")
    if falhou:
        print("Rode de novo: o progresso pula o que ja foi e retenta o resto.")
    return 1 if falhou and not ok else 0


if __name__ == "__main__":
    sys.exit(main())
