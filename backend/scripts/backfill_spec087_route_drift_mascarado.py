# -*- coding: utf-8 -*-
"""Remascara as linhas de `route_drift` que já existem — SPEC-087, BLOCO C ④.

```
APPLY     lê `summary` e `detail` de cada linha, passa pelo mascarador ÚNICO
          (`redaction_service.redigir`) e regrava APENAS o que mudou.
VERIFY    o SQL do fim deste arquivo: nenhuma linha casa CPF/telefone/placa.
ROLLBACK  ⛔ IMPOSSÍVEL POR NATUREZA — e é o objetivo. Não existe desmascarar.
```

## 📊 O que foi medido antes de rodar, em 26/08/2026

```
route_drift ................................ 16 linhas
  com CPF ou telefone no `detail` ..........  1   (2ab5352e…)
  com CPF/telefone/placa no `summary` ......  0
company_id nesta tabela ................... A COLUNA NÃO EXISTE
```

⚠️ **As outras 15 estão limpas por sorte, não por guarda.** O `summary` é curto
e genérico; o `detail` guarda o texto das telas, e foi ali que a PII entrou.
O escritor foi consertado neste mesmo bloco — este script só cuida do passado.

## 🔴 Por que um script e não SQL

O mascarador é uma lista de regex em Python (`PADROES_PII`). Reescrevê-la em
`regexp_replace` criaria **uma segunda lista** — e duas listas que precisam
concordar divergem, sendo que a que fica para trás é justamente a que deixa
passar o CPF (`CLAUDE.md` §5).

📊 E há precedente na casa: `backfill_spec085_output_redacted.py`.

## ⛔ Idempotente

Rodar duas vezes não muda nada na segunda: texto já mascarado passa pelo
mascarador e sai igual. O script **só grava o que mudou**, e conta os dois.

Uso::

    python backend/scripts/backfill_spec087_route_drift_mascarado.py --dry-run
    python backend/scripts/backfill_spec087_route_drift_mascarado.py --aplicar
"""
from __future__ import annotations

import argparse
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from app.services.intelligence.redaction_service import (  # noqa: E402
    contem_pii, redigir,
)


#: 🔴 AS CHAVES QUE NÃO SÃO TEXTO — e este script é quem já causou o dano.
#:
#: 📊 Medido: `redigir` sobre 50.000 sha256 destrói **18,0%** deles — o padrão de
#: telefone não tem `\b` e come qualquer corrida de 10–11 dígitos dentro do hex.
#: A linha `2ab5352e…` de `route_drift` está com 58 caracteres em vez de 64 por
#: causa desta função, na primeira passada (P-262).
#:
#: ⚠️ O escritor (`route_sentinel._mascarar_fundo`) ganhou a exclusão no conserto
#: do painel. **Este script não ganhou** — e a docstring dele dizia "é a mesma
#: função do escritor, pelo mesmo motivo". Deixou de ser, e o cabeçalho promete
#: idempotência: rodar de novo mutilaria as signatures futuras em silêncio.
_CHAVES_QUE_NAO_SAO_TEXTO = ("signature", "hash", "digest", "fingerprint",
                             "id", "message_id", "checksum")


def _mascarar_fundo(valor, chave: str = ""):
    """Recursivo — `detail` é um `jsonb` com listas de telas dentro.

    ⚠️ Mascarar só o topo deixaria `detail.added[0]` cru, que é exatamente onde
    o texto da tela mora.

    ⛔ **E digest NÃO É texto.** É a mesma função do escritor — e agora é mesmo:
    ver `_CHAVES_QUE_NAO_SAO_TEXTO`.
    """
    if str(chave).lower() in _CHAVES_QUE_NAO_SAO_TEXTO:
        return valor
    if isinstance(valor, str):
        return redigir(valor)
    if isinstance(valor, list):
        return [_mascarar_fundo(v, chave) for v in valor]
    if isinstance(valor, dict):
        return {k: _mascarar_fundo(v, str(k)) for k, v in valor.items()}
    return valor


def _tem_pii(valor) -> bool:
    if isinstance(valor, str):
        return contem_pii(valor)
    if isinstance(valor, list):
        return any(_tem_pii(v) for v in valor)
    if isinstance(valor, dict):
        return any(_tem_pii(v) for v in valor.values())
    return False


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--aplicar", action="store_true",
                   help="grava. Sem isto, só mede (dry-run).")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    aplicar = bool(a.aplicar) and not a.dry_run

    from app.core.database import get_supabase_client

    db = get_supabase_client()
    linhas = (db.client.table("route_drift")
              .select("id, summary, detail").limit(5000).execute().data or [])

    print(f"📊 linhas em route_drift ......... {len(linhas)}")
    mudadas = com_pii_antes = 0
    for linha in linhas:
        summary = linha.get("summary") or ""
        detail = linha.get("detail")
        if isinstance(detail, str):
            try:
                detail = json.loads(detail)
            except Exception:  # noqa: BLE001
                pass

        tinha = _tem_pii(summary) or _tem_pii(detail)
        if tinha:
            com_pii_antes += 1

        novo_summary = redigir(summary) if summary else summary
        novo_detail = _mascarar_fundo(detail)
        if novo_summary == summary and novo_detail == detail:
            continue
        mudadas += 1
        # ⛔ NUNCA imprime o texto — só o id e o veredito.
        print(f"   {'REGRAVA' if aplicar else 'MUDARIA'} {str(linha['id'])[:8]}…"
              f"  tinha_pii={tinha}")
        if aplicar:
            (db.client.table("route_drift")
             .update({"summary": novo_summary, "detail": novo_detail})
             .eq("id", linha["id"]).execute())

    print()
    print(f"📊 com PII detectável ANTES ...... {com_pii_antes}")
    print(f"📊 linhas que mudam .............. {mudadas}")
    if not aplicar:
        print()
        print("⚠️ DRY-RUN. Nada foi gravado. Use `--aplicar`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# =============================================================================
# VERIFY (read-only, rodar DEPOIS)
# =============================================================================
# select count(*) filter (where summary ~ '\d{3}\.?\d{3}\.?\d{3}-?\d{2}'
#                            or detail::text ~ '\d{3}\.?\d{3}\.?\d{3}-?\d{2}') cpf,
#        count(*) filter (where summary ~ '\(?\d{2}\)?[\s.\-]?\d{4,5}[\s.\-]?\d{4}'
#                            or detail::text ~ '\(?\d{2}\)?[\s.\-]?\d{4,5}[\s.\-]?\d{4}') tel,
#        count(*) filter (where summary ~ '[A-Z]{3}-?\d[A-Z\d]\d{2}'
#                            or detail::text ~ '[A-Z]{3}-?\d[A-Z\d]\d{2}') placa,
#        count(*) total
#   from route_drift;
#  -- esperado: cpf=0, tel=0, placa=0, total=16
