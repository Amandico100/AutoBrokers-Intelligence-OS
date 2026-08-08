"""Conta o que existe DENTRO do Qdrant. Nao escreve nada, em lugar nenhum.

    python backend/scripts/destilacao_max/conferir_indice.py

POR QUE ISTO PRECISA EXISTIR
----------------------------
Em 07/08/2026, tudo o que o projeto sabia sobre o proprio indice era LEITURA DE
CODIGO. Ninguem nunca contou os pontos. Duas perguntas ficaram sem resposta:

  1. A reindexacao ja foi feita com a etiqueta nova?
     📊 `insurer_key` so entrou no payload das cartas hoje as 18:04 (628ebe7).
     A reindexacao que rodou em 06/08 e ANTERIOR — ela reescreveu 10.818 cartas
     sem a etiqueta. Mas isso e deducao pelo horario do commit, nao medicao.
     Este script conta quantos pontos tem a etiqueta na RAIZ do payload.

  2. As cartas aposentadas sairam mesmo do indice?
     📊 `despublicar_carta_sync` respondia "removi" com o Qdrant fora do ar (o
     retorno era descartado — corrigido em 3dae2a6). As 11 cartas `superseded`,
     entre elas 7 da Porto sobre boleto atualizado, podem estar la ate hoje
     respondendo ao segurado. O banco nao tem como dizer.

SEGURANCA
---------
So `count`, `scroll` e `retrieve`. Nenhum `upsert`, `delete` ou `set_payload`.
Rodar dez vezes nao muda nada — e cada rodada custa zero: nao chama a OpenAI,
so conversa com o Qdrant.

ONDE RODAR
----------
No contêiner de producao (`smith-worker` ou `smith-api`), que e o unico lugar
onde o Qdrant existe. Numa maquina sem `.env` ele recusa e diz por que.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

AQUI = Path(__file__).resolve()
BACKEND = AQUI.parents[2]
sys.path.insert(0, str(BACKEND))


def _titulo(texto: str) -> None:
    print("\n" + "=" * 68)
    print(texto)
    print("=" * 68)


def main() -> int:
    _titulo("CONFERENCIA DO INDICE — so leitura, nada e escrito")

    # ------------------------------------------------------------------ portas
    host = os.getenv("QDRANT_HOST") or os.getenv("QDRANT_URL") or ""
    if not host:
        print("\n  X  QDRANT_HOST/QDRANT_URL ausente.")
        print("     Este script so faz sentido no contêiner de producao.")
        print("     Numa maquina de desenvolvimento nao ha indice para contar.")
        return 2
    print(f"\n  Qdrant configurado: sim  (host presente, valor nao exibido)")

    try:
        from app.services.knowledge_scope import GLOBAL_COLLECTION
        from app.services.qdrant_service import get_qdrant_service
    except Exception as exc:  # noqa: BLE001
        print(f"\n  X  nao consegui carregar o servico: {type(exc).__name__}: {exc}")
        return 2

    q = get_qdrant_service()
    cli = q.client
    from qdrant_client.models import (FieldCondition, Filter, IsEmptyCondition,
                                      MatchValue, PayloadField)

    def conta(filtro=None) -> int:
        return cli.count(collection_name=GLOBAL_COLLECTION,
                         count_filter=filtro, exact=True).count

    # ------------------------------------------------------- 1. o tamanho real
    _titulo("1. QUANTOS PONTOS EXISTEM")
    try:
        total = conta()
    except Exception as exc:  # noqa: BLE001
        print(f"  X  a colecao '{GLOBAL_COLLECTION}' nao respondeu: "
              f"{type(exc).__name__}: {exc}")
        return 2
    print(f"  colecao {GLOBAL_COLLECTION}: {total} pontos")

    for ns in ("cards", "canon", "normative"):
        n = conta(Filter(must=[FieldCondition(key="namespace",
                                              match=MatchValue(value=ns))]))
        print(f"    namespace {ns:>10}: {n}")

    # ------------------------------------------- 2. a etiqueta esta na raiz?
    _titulo("2. A ETIQUETA DE SEGURADORA ESTA ONDE O FILTRO PROCURA?")
    print("  O filtro casa `insurer_key` na RAIZ do payload. Chave ausente")
    print("  significa 'fato generico' e PASSA em qualquer pergunta.\n")

    com_etiqueta = conta(Filter(must_not=[
        IsEmptyCondition(is_empty=PayloadField(key="insurer_key"))]))
    print(f"  pontos com `insurer_key` na raiz: {com_etiqueta}")
    print(f"  pontos sem (tratados como genericos): {total - com_etiqueta}")

    for slug in ("allianz", "porto", "bradesco", "tokio", "yelum", "hdi", "mapfre"):
        n = conta(Filter(must=[FieldCondition(key="insurer_key",
                                              match=MatchValue(value=slug))]))
        if n:
            print(f"    {slug:>10}: {n}")

    print("\n  COMO LER ISTO:")
    print("    ~0 com etiqueta ....... a reindexacao NOVA nao rodou. Rodar.")
    print("    ~2.300 com etiqueta ... as CARTAS ja foram reindexadas;")
    print("                            falta o corpus normativo (11.409 chunks).")
    print("    >11.000 com etiqueta .. cartas E corpus ja etiquetados. Nada a fazer.")

    # ------------------------------------------ 3. as aposentadas sairam?
    _titulo("3. AS CARTAS APOSENTADAS SAIRAM DO INDICE?")
    try:
        from app.core.database import get_supabase_client
        linhas = (get_supabase_client().client.table("knowledge_cards")
                  .select("id, insurer_key")
                  .eq("status", "superseded").not_.is_("published_at", "null")
                  .limit(200).execute().data or [])
    except Exception as exc:  # noqa: BLE001
        print(f"  X  nao consegui ler o banco: {type(exc).__name__}")
        linhas = []

    if not linhas:
        print("  (nenhuma carta aposentada que ja tinha sido publicada)")
    else:
        print(f"  {len(linhas)} cartas aposentadas que JA estiveram publicadas.\n")
        fantasmas = []
        for linha in linhas:
            doc = f"card-{linha['id']}"
            n = conta(Filter(must=[FieldCondition(key="document_id",
                                                  match=MatchValue(value=doc))]))
            if n:
                fantasmas.append((linha["id"], linha.get("insurer_key") or "-", n))

        if not fantasmas:
            print("  ✅ NENHUMA continua no indice. O removedor funcionou.")
        else:
            print(f"  🔴 {len(fantasmas)} CONTINUAM NO INDICE, respondendo ao agente:")
            for cid, slug, n in fantasmas:
                print(f"     {cid}  ({slug})  {n} ponto(s)")
            print("\n  Estas sao as cartas que a auditoria mostra REMOVIDAS e a")
            print("  busca continua entregando. E o pior estado possivel.")

    _titulo("FIM — nada foi escrito")
    print("Copie esta saida inteira e devolva para a analise.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
