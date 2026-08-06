"""Passa o templatize de HOJE por cima de todo o acervo já publicado.

Por que isto precisa existir
----------------------------
Cada carta foi filtrada pelo `templatize` que existia no momento em que ela
entrou. Só que o `templatize` levou dezesseis correções ao longo da campanha:
CPF com espaço, placa em minúscula, linha digitável, PIX copia-e-cola, segredo
em URL, dado bancário rotulado, cartão com os quatro dígitos finais.

Uma carta que entrou no dia 1 passou por um filtro que não conhecia nenhum
desses formatos. Ela está publicada, está no Qdrant, e ninguém nunca a
reexaminou. Este script é essa reexaminação: aplica a régua atual sobre o
acervo inteiro e mostra o que a régua antiga deixou passar.

O que ele NÃO faz sozinho
-------------------------
Não apaga nada sem `--aplicar`. E quando aplica, faz a coisa completa:
marca `rejected_pii` no banco E remove o ponto do Qdrant. Carta despublicada
que continua no índice vetorial é pior que carta errada — é carta invisível
que ainda responde.

Uso
---
    python varrer_pii.py             # relatório, não grava
    python varrer_pii.py --aplicar   # marca e despublica
"""

from __future__ import annotations

import collections
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from exportar import _credenciais  # noqa: E402
from mascarar import templatize  # noqa: E402

PAGINA = 1000


def _o_que_mudou(antes: str, depois: str) -> str:
    """Qual marcador o templatize colocou. É o nome do vazamento."""
    for marca in ("{CPF}", "{CNPJ}", "{TELEFONE}", "{EMAIL}", "{PLACA}",
                  "{CARTAO}", "{LINHA_DIGITAVEL}", "{PIX_FIM}", "{SEGREDO}",
                  "{CAMINHO}", "{VALOR_RS}", "{VALOR}", "{NUMERO}", "{DATA}",
                  # {ENDERECO} e {NOME} entraram em 06/08/2026 com as regras de
                  # logradouro em prosa e de vocativo. Sem estarem nesta lista,
                  # o vazamento que elas pegam sairia do relatório como
                  # "(outro)" — e o nome do vazamento é metade do achado.
                  "{ENDERECO}", "{NOME}",
                  "{CEP}", "{APOLICE}", "{PROTOCOLO}"):
        if marca in depois and marca not in antes:
            return marca
    return "(outro)"


def main() -> int:
    aplicar = "--aplicar" in sys.argv
    url, key = _credenciais()
    from supabase import create_client

    db = create_client(url, key)

    suspeitas = []
    lidas = 0
    de = 0
    while True:
        pagina = (db.table("knowledge_cards")
                  .select("id, card_text, insurer_key, ramo, status")
                  .eq("status", "published")
                  .order("id").range(de, de + PAGINA - 1).execute().data) or []
        if not pagina:
            break
        for c in pagina:
            lidas += 1
            texto = c["card_text"] or ""
            limpo = templatize(texto)
            if limpo != texto:
                suspeitas.append((c, texto, limpo, _o_que_mudou(texto, limpo)))
        de += PAGINA

    print(f"  {lidas} cartas publicadas examinadas com a régua de hoje")
    print(f"  {len(suspeitas)} mudam quando o templatize atual passa nelas\n")

    if not suspeitas:
        print("  o acervo está limpo pela régua atual.")
        return 0

    por_tipo = collections.Counter(s[3] for s in suspeitas)
    print("  por tipo de vazamento:")
    for marca, n in por_tipo.most_common():
        print(f"    {marca:<18} {n}")

    print("\n  amostra (texto ORIGINAL truncado — não copie para relatório):")
    for c, texto, limpo, marca in suspeitas[:12]:
        print(f"    [{marca}] {texto[:96]}")

    if not aplicar:
        print(f"\n  (nada gravado — rode com --aplicar para marcar as {len(suspeitas)})")
        return 0

    # Despublica: marca no banco e tira do índice vetorial.
    from app.services.attendance_distiller import despublicar_carta_sync

    marcadas = removidas = 0
    for c, _t, _l, _m in suspeitas:
        db.table("knowledge_cards").update(
            {"status": "rejected_pii"}).eq("id", c["id"]).execute()
        marcadas += 1
        try:
            if despublicar_carta_sync(str(c["id"])):
                removidas += 1
        except Exception as exc:  # noqa: BLE001
            print(f"    aviso: ponto {c['id']} não saiu do Qdrant: {exc}")

    print(f"\n  {marcadas} marcadas rejected_pii · {removidas} pontos removidos do Qdrant")
    return 0


if __name__ == "__main__":
    sys.exit(main())
