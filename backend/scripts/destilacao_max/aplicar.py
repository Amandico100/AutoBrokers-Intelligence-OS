"""Grava o que o subagente destilou. Direto no banco, fora do contexto de todos.

Por que isto substituiu o `aplicar_sql.py` no fluxo normal
----------------------------------------------------------
Medido em 29/07/2026: cada subagente gastou ~250 mil tokens para destilar ~90
conversas. O trabalho em si — ler a conversa e escrever o conhecimento — custa
uns 85 mil. O resto era **transporte**: gerar um arquivo .sql, lê-lo de volta,
fatiá-lo em blocos que coubessem numa chamada, executar bloco a bloco e
conferir. Um terço do esforço do modelo mais caro do sistema empurrando texto.

Agora o subagente destila e para. Quem grava é este script, que fala com o
banco pela mesma conexão do exportador. O modelo pensa; o script carrega.

`aplicar_sql.py` continua existindo para quando não houver credencial de banco
à mão — é o caminho que só depende do MCP.

As regras de gravação são as de `_store_card_sync`, sem inventar nada:
md5 do texto em minúsculas, 15 a 400 caracteres, `rejected_pii` quando o
templatize mudaria o texto, `insurer_key` normalizada. A carta entra como
`pending_review`; quem publica no RAG é o publicador de `distill_once`.

Uso
---
    python aplicar.py lotes/lote_011.destilado.jsonl [outro.jsonl ...]
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from exportar import _credenciais  # noqa: E402
from mascarar import normalize_insurer_key, templatize  # noqa: E402

MARCA = "destilacao_max_29_07_2026"
UUID = re.compile(r"[0-9a-fA-F-]{36}")


def _distilled(d: dict) -> dict:
    return {
        "tipo": d.get("tipo"), "ramo": d.get("ramo"),
        "servico": d.get("servico"), "seguradora": d.get("seguradora"),
        "resumo_conduta": d.get("resumo_conduta") or [],
        "perguntas_na_ordem": d.get("perguntas_na_ordem") or [],
        "score": d.get("score"), "flags": d.get("flags") or [],
        "at": None, "por": MARCA,
    }


def _cartas_de(d: dict) -> list:
    ramo = str(d.get("ramo") or "outro")
    seg = normalize_insurer_key(str(d.get("seguradora") or "")) or None
    if seg and not re.fullmatch(r"[a-z0-9_-]{2,40}", seg):
        seg = None
    saida = []
    for fato in (d.get("fatos_reutilizaveis") or [])[:8]:
        texto = " ".join(str(fato or "").split())
        if len(texto) < 15 or len(texto) > 400:
            continue
        limpo = templatize(texto) == texto
        saida.append({
            "card_hash": hashlib.md5(texto.lower().encode("utf-8")).hexdigest(),
            "card_text": texto, "category": "processo", "ramo": ramo,
            "insurer_key": seg,
            "status": "pending_review" if limpo else "rejected_pii",
            "pii_check": {"deterministic": limpo, "llm_instructed": True, "por": MARCA},
        })
    return saida


def main() -> int:
    if len(sys.argv) < 2:
        print("uso: aplicar.py <destilado.jsonl> [...]", file=sys.stderr)
        return 2

    url, key = _credenciais()
    from supabase import create_client

    db = create_client(url, key)
    total_s = total_c = puladas = 0

    for caminho in sys.argv[1:]:
        sessoes = 0
        cartas: dict = {}          # hash -> linha (dedup dentro do arquivo)
        with open(caminho, encoding="utf-8") as fh:
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
                if not UUID.fullmatch(sid):
                    puladas += 1
                    continue

                # Lê o resumo atual para PRESERVAR `marker` e `source`, e para
                # nunca sobrescrever uma destilação que já existe — o mesmo
                # `WHERE summary->'distilled' IS NULL` do caminho por SQL.
                atual = (db.table("attendance_sessions").select("summary")
                         .eq("id", sid).limit(1).execute().data or [])
                resumo = dict((atual[0] if atual else {}).get("summary") or {})
                if resumo.get("distilled"):
                    continue
                resumo["distilled"] = _distilled(d)
                db.table("attendance_sessions").update({"summary": resumo}).eq("id", sid).execute()
                sessoes += 1
                for c in _cartas_de(d):
                    cartas.setdefault(c["card_hash"], c)

        linhas = list(cartas.values())
        for i in range(0, len(linhas), 200):
            db.table("knowledge_cards").upsert(
                linhas[i:i + 200], on_conflict="card_hash", ignore_duplicates=True).execute()
        total_s += sessoes
        total_c += len(linhas)
        print(f"[aplicar] {os.path.basename(caminho)}: {sessoes} sessões · "
              f"{len(linhas)} cartas", file=sys.stderr)

    print(f"[aplicar] TOTAL {total_s} sessões · {total_c} cartas · "
          f"{puladas} linhas inválidas", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
