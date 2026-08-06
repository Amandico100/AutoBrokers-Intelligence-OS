"""Devolve a verdade aos dois rótulos das 11.640 cartas que já estão no banco.

O que estava errado
-------------------
**`category` valia `processo` em 100% das cartas.** Não era engano de uma
rodada: `_store_card_sync` gravava `meta.get("category") or "processo"` e
ninguém nunca passou `category`. Uma coluna que responde a mesma coisa para
todo mundo não responde nada.

**`insurer_key` guardava a seguradora da CONVERSA, não a do FATO.** O
destilador carimbava a companhia da sessão nos até oito fatos que ela produzia,
inclusive nos genéricos. 📊 Das 3.354 cartas etiquetadas, só 1.083 (32,3%)
citavam a própria seguradora no texto.

Por que rebaixar é seguro, e por que é urgente mesmo assim
----------------------------------------------------------
`build_global_search_kwargs` aceita `carrier_slug` e o descarta — não existe
filtro por seguradora hoje. Uma carta SEM rótulo se comporta exatamente como
hoje, então o rebaixamento não pode piorar nada. Ligar o filtro em cima do
acervo velho, sim: dois terços das cartas responderiam sob a bandeira errada.

Como isto não repete a decisão
------------------------------
Quem decide é `curadoria_cartas.seguradora_do_fato` e `assunto_da_carta` — as
MESMAS funções do destilador, do `aplicar.py` e do `aplicar_sql.py`. Este script
não tem regra própria: ele só percorre o que já está gravado e reaplica a
decisão única. Um segundo critério aqui faria o acervo antigo divergir do novo
sem ninguém saber qual dos dois está certo (§5).

O caminho de volta
------------------
Cada carta que muda de seguradora leva o valor anterior em
`pii_check.insurer_key_anterior`, com `rebaixado_em` e `motivo` — o mesmo
formato de marcação que `corrigir.py` usa. É por ele que se desfaz carta a
carta. O backup completo por `card_hash` é responsabilidade de quem roda, e o
script recusa a aplicar sem que o arquivo exista.

Uso
---
    python rotular_acervo.py --backup backup.jsonl              # só mostra
    python rotular_acervo.py --backup backup.jsonl --aplicar    # grava
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from exportar import _credenciais  # noqa: E402
from mascarar import _carregar_servico  # noqa: E402

_CURADORIA = _carregar_servico("curadoria_cartas")
assunto_da_carta = _CURADORIA.assunto_da_carta
seguradora_do_fato = _CURADORIA.seguradora_do_fato

HOJE = "2026-08-05"
MOTIVO = "rotulo_da_sessao_nao_confirmado_pelo_texto"


def _ler_tudo(db) -> list:
    """O acervo inteiro, paginado por `id`.

    📊 Paginar por `created_at` perde linha: a destilação grava as até oito
    cartas de uma sessão no mesmo instante e o Postgres não promete ordem entre
    iguais. Medido em 05/08/2026: 11.640 lidas, 11.628 hashes distintos — 12
    repetidas, 12 invisíveis. Num script que REESCREVE o acervo, a linha
    invisível é a que fica com o rótulo velho para sempre.
    """
    linhas: list = []
    inicio = 0
    while True:
        lote = (db.table("knowledge_cards")
                .select("id, card_hash, card_text, insurer_key, ramo, category, "
                        "status, pii_check")
                .order("id", desc=False)
                .range(inicio, inicio + 999).execute().data) or []
        linhas.extend(lote)
        if len(lote) < 1000:
            return linhas
        inicio += 1000


def _plano(cartas: list) -> list:
    """O que muda em cada carta. Nada é gravado aqui."""
    saida = []
    for c in cartas:
        antigo = c.get("insurer_key")
        novo, prestadora = (seguradora_do_fato(c.get("card_text") or "", antigo)
                            if antigo else (None, None))
        assunto = assunto_da_carta(c.get("card_text") or "")
        if novo == antigo and assunto == (c.get("category") or ""):
            continue
        saida.append({**c, "_insurer_novo": novo, "_prestadora": prestadora,
                      "_category_nova": assunto})
    return saida


def _mostrar(cartas: list, plano: list) -> None:
    mant = Counter()
    reb = Counter()
    pres = Counter()
    for c in cartas:
        if not c.get("insurer_key"):
            continue
        novo, prestadora = seguradora_do_fato(c.get("card_text") or "", c["insurer_key"])
        if novo == c["insurer_key"]:
            mant[novo] += 1
        elif prestadora:
            pres[prestadora] += 1
        else:
            reb[c["insurer_key"]] += 1

    print(f"\n  {len(cartas)} cartas no acervo · {len(plano)} mudam alguma coisa")
    print("\n  SEGURADORA")
    print(f"    com rótulo hoje ............ {sum(1 for c in cartas if c.get('insurer_key'))}")
    print(f"    MANTIDAS (o texto nomeia) .. {sum(mant.values())}")
    print(f"    viram prestadora ........... {sum(pres.values())}  {dict(pres)}")
    print(f"    REBAIXADAS para NULL ....... {sum(reb.values())}")
    print("\n    as dez mais rebaixadas:")
    for k, n in reb.most_common(10):
        total = sum(1 for c in cartas if c.get("insurer_key") == k)
        print(f"      {k:32} {n:5} de {total:5}")

    print("\n  ASSUNTO")
    de = Counter(str(c.get("category") or "") for c in cartas)
    para = Counter(assunto_da_carta(c.get("card_text") or "") for c in cartas)
    print(f"    de:   {dict(de)}")
    print("    para:")
    for k, n in para.most_common():
        print(f"      {k:14} {n:6}  {100 * n / max(1, len(cartas)):5.1f}%")

    # AMOSTRA — só cartas `published`, que passaram no `templatize` e não têm
    # PII por construção. As `rejected_pii` nunca são impressas.
    #
    # Nas DUAS direções, de propósito. Uma amostra só de rebaixamentos não
    # prova nada: uma regra que apaga tudo produziria exatamente essa lista. O
    # que dá direito à conclusão é ver, lado a lado, o rótulo que FICA.
    vistas = [p for p in plano if p.get("status") == "published"]
    caem = [p for p in vistas if p.get("insurer_key") and not p["_insurer_novo"]
            and not p["_prestadora"]]
    ficam = [p for p in vistas if p["_insurer_novo"]]
    prest = [p for p in vistas if p["_prestadora"]]

    def _linhas(titulo, grupo, quantas):
        print(f"\n  {titulo} ({len(grupo)} no total, {min(quantas, len(grupo))} mostradas):")
        passo = max(1, len(grupo) // max(1, quantas))
        for p in grupo[::passo][:quantas]:
            seg = f"{p.get('insurer_key') or '-'} -> {p['_insurer_novo'] or p['_prestadora'] or 'NULL'}"
            print(f"    {seg:26} {p['_category_nova']:12} {(p.get('card_text') or '')[:62]}")

    _linhas("REBAIXADAS — o texto não nomeia a companhia", caem, 10)
    _linhas("MANTIDAS — o texto nomeia (a linha de controle)", ficam, 6)
    _linhas("PRESTADORAS — saem de insurer_key, viram `prestadora`", prest, 4)


def _aplicar(db, plano: list) -> dict:
    """Grava. Individual quando a seguradora muda (a marca é por carta),
    agrupado quando só o assunto muda."""
    trocam_seg = [p for p in plano if p["_insurer_novo"] != p.get("insurer_key")]
    so_assunto = [p for p in plano if p["_insurer_novo"] == p.get("insurer_key")]

    feitas = falhas = 0
    t0 = time.time()
    for i, p in enumerate(trocam_seg, 1):
        marca = dict(p.get("pii_check") or {})
        marca["insurer_key_anterior"] = p.get("insurer_key")
        marca["rebaixado_em"] = HOJE
        marca["motivo"] = MOTIVO
        if p["_prestadora"]:
            marca["prestadora"] = p["_prestadora"]
        try:
            db.table("knowledge_cards").update(
                {"insurer_key": p["_insurer_novo"], "category": p["_category_nova"],
                 "pii_check": marca}).eq("id", p["id"]).execute()
            feitas += 1
        except Exception as exc:  # noqa: BLE001 — uma carta ruim não trava o lote
            falhas += 1
            print(f"    falhou em {p['card_hash'][:8]}: {type(exc).__name__}")
        if i % 250 == 0:
            print(f"    {i}/{len(trocam_seg)} rótulos de seguradora · "
                  f"{time.time() - t0:.0f}s")

    por_assunto: dict = {}
    for p in so_assunto:
        por_assunto.setdefault(p["_category_nova"], []).append(p["card_hash"])
    for assunto, hashes in por_assunto.items():
        for i in range(0, len(hashes), 100):
            try:
                db.table("knowledge_cards").update({"category": assunto}) \
                    .in_("card_hash", hashes[i:i + 100]).execute()
                feitas += len(hashes[i:i + 100])
            except Exception as exc:  # noqa: BLE001
                falhas += len(hashes[i:i + 100])
                print(f"    falhou no lote {assunto}[{i}]: {type(exc).__name__}")
        print(f"    {assunto:14} {len(hashes):6} cartas")
    return {"gravadas": feitas, "falhas": falhas, "segundos": round(time.time() - t0)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--aplicar", action="store_true")
    ap.add_argument("--backup", default="",
                    help="arquivo com o backup por card_hash; obrigatório para aplicar")
    args = ap.parse_args()

    if args.aplicar and not (args.backup and os.path.isfile(args.backup)):
        print("SEM BACKUP, SEM UPDATE.\n"
              "  Esta tabela não tem histórico nenhum no repositório: o arquivo por\n"
              "  `card_hash` é o único caminho de volta em massa. Gere-o antes\n"
              "  (SELECT card_hash, insurer_key, ramo, category, status) e passe\n"
              "  o caminho em --backup.", file=sys.stderr)
        return 2

    url, key = _credenciais()
    from supabase import create_client

    db = create_client(url, key)
    cartas = _ler_tudo(db)
    hashes = {c["card_hash"] for c in cartas}
    if len(hashes) != len(cartas):
        print(f"LEITURA INCONSISTENTE: {len(cartas)} linhas, {len(hashes)} hashes "
              f"distintos — a paginação perdeu linha. Nada foi gravado.", file=sys.stderr)
        return 3

    plano = _plano(cartas)
    _mostrar(cartas, plano)

    if not args.aplicar:
        print("\n  (nada gravado — rode com --aplicar)")
        return 0

    print(f"\n  aplicando em {len(plano)} cartas...")
    r = _aplicar(db, plano)
    print(f"\n  {r['gravadas']} gravadas · {r['falhas']} falhas · {r['segundos']}s")
    return 1 if r["falhas"] else 0


if __name__ == "__main__":
    sys.exit(main())
