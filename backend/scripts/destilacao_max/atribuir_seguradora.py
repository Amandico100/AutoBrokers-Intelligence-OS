"""Devolve a seguradora às cartas que nasceram sem ela.

O problema
----------
65% das cartas do acervo (5.725 de 8.800) estão sem `insurer_key`. Não é
descuido: a instrução aos subagentes é `seguradora` só quando ela aparece
EXPLÍCITA na conversa, e ser conservador aqui é certo — atribuir a seguradora
errada é o pior erro possível no RAG, e já aconteceu três vezes (o prazo da Azul
que virou Porto, o PIX da Youse que virou Yelum, o Itaú arquivado como Porto).

Mas há um caso em que a informação existe e se perdeu por acidente: a conversa
dizia a seguradora no campo `seguradora` da sessão, e o subagente, escrevendo o
fato de forma geral, deixou o campo da carta vazio. `knowledge_cards` não guarda
de qual sessão a carta veio, então nada no banco liga uma coisa à outra.

O que liga são os arquivos `*.destilado.jsonl` em disco: cada linha tem o `id`
da sessão, a `seguradora` e os `fatos_reutilizaveis`. Do fato sai o `card_hash`
pela mesma regra do `_store_card_sync`, e o hash acha a carta.

A regra de atribuição, e por que ela é estreita
-----------------------------------------------
Só atribui quando **TODAS** as sessões que produziram aquela carta nomeiam a
MESMA seguradora.

Se duas seguradoras diferentes geraram o mesmo fato, o fato é geral **de
verdade** — foi observado em duas companhias — e transformá-lo em regra de uma
delas seria inventar exclusividade que não existe. Nesse caso a carta fica como
está, que é a resposta correta.

Uso
---
    python atribuir_seguradora.py            # relatório, não grava
    python atribuir_seguradora.py --aplicar  # grava
"""

from __future__ import annotations

import collections
import glob
import hashlib
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from exportar import _credenciais  # noqa: E402
from mascarar import normalize_insurer_key  # noqa: E402


def main() -> int:
    aplicar = "--aplicar" in sys.argv

    # hash da carta -> conjunto de seguradoras que a produziram
    de_quem: dict = collections.defaultdict(set)
    linhas = 0
    for pasta in ("lotes", "lotes_autofleet"):
        for caminho in sorted(glob.glob(os.path.join(AQUI, pasta, "*.destilado.jsonl"))):
            with open(caminho, encoding="utf-8") as fh:
                for linha in fh:
                    linha = linha.strip()
                    if not linha:
                        continue
                    try:
                        d = json.loads(linha)
                    except json.JSONDecodeError:
                        continue
                    linhas += 1
                    seg = normalize_insurer_key(
                        str(d.get("seguradora") or ""), para="conhecimento")
                    if not seg:
                        continue
                    for fato in (d.get("fatos_reutilizaveis") or [])[:8]:
                        texto = " ".join(str(fato or "").split())
                        if len(texto) < 15 or len(texto) > 400:
                            continue
                        h = hashlib.md5(texto.lower().encode("utf-8")).hexdigest()
                        de_quem[h].add(seg)

    unicas = {h: list(s)[0] for h, s in de_quem.items() if len(s) == 1}
    ambiguas = sum(1 for s in de_quem.values() if len(s) > 1)
    print(f"  {linhas} sessões lidas em disco")
    print(f"  {len(de_quem)} cartas com seguradora rastreável")
    print(f"  {len(unicas)} com seguradora ÚNICA · {ambiguas} vistas em mais de uma "
          f"(ficam gerais, e é o certo)")

    url, key = _credenciais()
    from supabase import create_client

    db = create_client(url, key)
    alvos = list(unicas.items())
    atribuidas = ja_tinham = nao_achadas = 0
    for i in range(0, len(alvos), 100):
        lote = alvos[i:i + 100]
        atual = (db.table("knowledge_cards").select("id, card_hash, insurer_key")
                 .in_("card_hash", [h for h, _ in lote]).execute().data) or []
        por_hash = {r["card_hash"]: r for r in atual}
        for h, seg in lote:
            r = por_hash.get(h)
            if not r:
                nao_achadas += 1
                continue
            if r.get("insurer_key"):
                ja_tinham += 1
                continue
            if aplicar:
                db.table("knowledge_cards").update(
                    {"insurer_key": seg}).eq("id", r["id"]).execute()
            atribuidas += 1

    print(f"\n  {atribuidas} cartas {'ATRIBUÍDAS' if aplicar else 'atribuíveis'} "
          f"· {ja_tinham} já tinham · {nao_achadas} não estão no banco")
    if not aplicar:
        print("\n  (nada gravado — rode com --aplicar)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
