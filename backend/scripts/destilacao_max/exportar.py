"""Puxa as conversas pendentes do banco e escreve lotes MASCARADOS em disco.

Por que este script existe
--------------------------
Na prova de 29/07/2026 um subagente destilou 25 conversas sem custo de API. O
gargalo não foi ler nem escrever: foi **transportar** o JSON do banco até o
disco pelo canal de ferramentas, com o texto passando três vezes pelo contexto
(vem da consulta, é reescrito no arquivo, é lido de volta). A 6.118 conversas
isso não escala.

Aqui o transporte é uma conexão direta: o texto sai do banco, é mascarado e cai
no disco sem passar pelo contexto de ninguém. O subagente abre um arquivo já
pronto e faz só o que só ele sabe fazer — ler a conversa e escrever o
conhecimento.

Credenciais
-----------
Lê `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY` do ambiente ou de um `.env` ao
lado. A chave nunca é impressa: o script informa apenas presença e o host.

Uso
---
    python exportar.py --lotes 60 --por-lote 100 --saida ../../../lotes

Gera `lote_001.jsonl` … e um `INDICE.md` com o que cada lote contém.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mascarar import transcript  # noqa: E402  — o mesmo portão de PII

AQUI = os.path.dirname(os.path.abspath(__file__))


def _credenciais() -> tuple:
    for nome in (".env", "../../.env", "../../../.env"):
        caminho = os.path.join(AQUI, nome)
        if not os.path.isfile(caminho):
            continue
        with open(caminho, encoding="utf-8") as fh:
            for linha in fh:
                linha = linha.strip()
                if not linha or linha.startswith("#") or "=" not in linha:
                    continue
                k, v = linha.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        print("FALTA credencial. Defina SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY\n"
              "no ambiente ou num .env ao lado deste script.", file=sys.stderr)
        raise SystemExit(2)
    # Presença e host — nunca o valor.
    print(f"[exportar] banco {url.split('//')[-1].split('.')[0]}… · chave presente "
          f"({len(key)} caracteres)", file=sys.stderr)
    return url, key


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--lotes", type=int, default=60)
    p.add_argument("--por-lote", type=int, default=100)
    p.add_argument("--saida", default=os.path.join(AQUI, "lotes"))
    p.add_argument("--empresa", default="", help="company_id; vazio = todas")
    args = p.parse_args()

    url, key = _credenciais()
    from supabase import create_client

    db = create_client(url, key)
    os.makedirs(args.saida, exist_ok=True)

    # Sessões pendentes, mais antigas primeiro — a mesma ordem do destilador,
    # para que os dois caminhos nunca disputem a mesma conversa em ordens
    # diferentes.
    alvo = args.lotes * args.por_lote
    pendentes: list = []
    inicio = 0
    while len(pendentes) < alvo:
        q = db.table("attendance_sessions").select("id, summary").eq("status", "closed")
        if args.empresa:
            q = q.eq("company_id", args.empresa)
        lote = q.order("started_at", desc=False).range(inicio, inicio + 999).execute().data or []
        for r in lote:
            resumo = r.get("summary") or {}
            if resumo.get("distilled") or int(resumo.get("distill_falhas") or 0) >= 3:
                continue
            pendentes.append(r["id"])
        if len(lote) < 1000:
            break
        inicio += 1000
    pendentes = pendentes[:alvo]
    print(f"[exportar] {len(pendentes)} sessões pendentes", file=sys.stderr)

    indice = ["# Lotes para destilação pelo plano Max", ""]
    numero = escritas = 0
    for i in range(0, len(pendentes), args.por_lote):
        ids = pendentes[i:i + args.por_lote]
        # O transcript vem de uma consulta por lote, não uma por sessão: 100
        # idas ao banco por lote seria o gargalo de volta, só que em outro lugar.
        eventos = (db.table("attendance_transcripts")
                   .select("session_id, direction, msg_type, text, wa_timestamp")
                   .in_("session_id", ids)
                   .order("wa_timestamp", desc=False)
                   .limit(400 * len(ids)).execute().data) or []
        por_sessao: dict = {}
        for e in eventos:
            por_sessao.setdefault(str(e.get("session_id")), []).append(e)

        numero += 1
        caminho = os.path.join(args.saida, f"lote_{numero:03d}.jsonl")
        n = 0
        with open(caminho, "w", encoding="utf-8") as fh:
            for sid in ids:
                texto = transcript(por_sessao.get(sid) or [])
                if len(texto) < 80:      # mesma regra do destilador
                    continue
                fh.write(json.dumps({"id": sid, "conversa": texto}, ensure_ascii=False) + "\n")
                n += 1
        escritas += n
        indice.append(f"- `lote_{numero:03d}.jsonl` — {n} conversas")
        print(f"[exportar] lote_{numero:03d}.jsonl · {n} conversas", file=sys.stderr)

    with open(os.path.join(args.saida, "INDICE.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(indice) + "\n")
    print(f"[exportar] pronto: {numero} lotes · {escritas} conversas mascaradas",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
