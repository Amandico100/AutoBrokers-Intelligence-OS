"""O que o subagente escreveu -> SQL idempotente, idêntico ao caminho de produção.

Este script não inventa regra nenhuma. Ele espelha `_store_card_sync` linha por
linha, de propósito:

  * `card_hash` = md5 do texto em minúsculas  → a mesma carta nunca duplica
  * texto entre 15 e 400 caracteres           → o mesmo corte
  * `status` = pending_review, ou rejected_pii se o templatize mudaria o texto
  * `insurer_key` em minúsculas, vazio vira NULL

Se alguma dessas regras mudar em produção, ela precisa mudar aqui no mesmo
commit. É o preço de escrever por fora — e é por isso que o script é curto e
declara isso em voz alta em vez de esconder.

A carta entra como `pending_review`, NÃO como `published`. Quem publica é o
publicador automático que já roda em `distill_once`: ele gera o embedding e
manda para o Qdrant com vetor denso e esparso. Não existe segundo publicador.

Uso
---
    python aplicar_sql.py destilado.jsonl > aplicar.sql

Entrada: uma linha JSON por sessão, no formato que o subagente produz:
    {"id": "...", "tipo": "...", "ramo": "auto", "servico": "sinistro",
     "seguradora": "hdi", "resumo_conduta": [...], "perguntas_na_ordem": [...],
     "fatos_reutilizaveis": [...], "score": 8, "flags": [...]}
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mascarar import normalize_insurer_key, templatize  # noqa: E402

# O Windows redireciona `>` na codepage ANSI (cp1252), não em UTF-8. Sem esta
# linha, "apólice" e "ocorrência" saem corrompidos no arquivo .sql e entram
# corrompidos no banco — em silêncio, porque o SQL continua válido.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

MARCA = "destilacao_max_29_07_2026"


def _citar(txt: str) -> str:
    """Texto -> literal SQL com aspas em dólar, sem chance de escapar errado.

    Carta de seguro tem apóstrofo ("apólice do cliente'"), acento e aspas. Um
    `replace("'", "''")` funciona até o dia em que não funciona, e o estrago é
    SQL executando o que não devia. O delimitador é escolhido para não existir
    dentro do texto.
    """
    tag = "c"
    while f"${tag}$" in txt:
        tag += "x"
    return f"${tag}${txt}${tag}$"


def main() -> int:
    if len(sys.argv) < 2:
        print("uso: aplicar_sql.py destilado.jsonl", file=sys.stderr)
        return 2

    sessoes = cartas = puladas = 0
    vistas: set = set()
    print("-- Gerado por scripts/destilacao_max/aplicar_sql.py")
    print("BEGIN;")

    with open(sys.argv[1], encoding="utf-8") as fh:
        for linha in fh:
            linha = linha.strip()
            if not linha:
                continue
            try:
                d = json.loads(linha)
            except json.JSONDecodeError:
                puladas += 1
                continue
            sid = str(d.get("id") or "").strip()
            if not re.fullmatch(r"[0-9a-fA-F-]{36}", sid):
                puladas += 1
                continue

            distilled = {
                "tipo": d.get("tipo"), "ramo": d.get("ramo"),
                "servico": d.get("servico"), "seguradora": d.get("seguradora"),
                "resumo_conduta": d.get("resumo_conduta") or [],
                "perguntas_na_ordem": d.get("perguntas_na_ordem") or [],
                "score": d.get("score"), "flags": d.get("flags") or [],
                "at": None, "por": MARCA,
            }
            j = _citar(json.dumps(distilled, ensure_ascii=False))
            # `||` preserva o `marker` e o `source` que já estavam no resumo, e
            # `summary->'distilled' is null` faz a linha ser inofensiva se rodar
            # duas vezes — nunca sobrescreve destilação existente.
            print(f"UPDATE attendance_sessions SET summary = coalesce(summary,'{{}}'::jsonb) "
                  f"|| jsonb_build_object('distilled', {j}::jsonb) "
                  f"WHERE id = '{sid}' AND summary->'distilled' IS NULL;")
            sessoes += 1

            ramo = str(d.get("ramo") or "outro")
            # Mesma normalização de `_store_card_sync`: "Tokio", "Tokio Marine"
            # e "Tókio Marine" são UMA seguradora. Sem isto o subagente que
            # escreve "tokio marine" cria uma pasta que o filtro por seguradora
            # nunca encontra.
            seg = normalize_insurer_key(str(d.get("seguradora") or "")) or None
            for fato in (d.get("fatos_reutilizaveis") or [])[:8]:
                texto = " ".join(str(fato or "").split())
                if len(texto) < 15 or len(texto) > 400:
                    continue
                h = hashlib.md5(texto.lower().encode("utf-8")).hexdigest()
                if h in vistas:
                    continue
                vistas.add(h)
                limpo = templatize(texto) == texto
                status = "pending_review" if limpo else "rejected_pii"
                seg_sql = f"'{seg}'" if seg and re.fullmatch(r"[a-z0-9_-]{2,40}", seg) else "NULL"
                print(f"INSERT INTO knowledge_cards "
                      f"(card_hash, card_text, category, ramo, insurer_key, status, pii_check) "
                      f"VALUES ('{h}', {_citar(texto)}, 'processo', "
                      f"{_citar(ramo)}, {seg_sql}, '{status}', "
                      f"'{{\"deterministic\": {str(limpo).lower()}, \"llm_instructed\": true, "
                      f"\"por\": \"{MARCA}\"}}'::jsonb) "
                      f"ON CONFLICT (card_hash) DO NOTHING;")
                cartas += 1

    print("COMMIT;")
    print(f"[aplicar_sql] {sessoes} sessões · {cartas} cartas · {puladas} linhas inválidas",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
