# -*- coding: utf-8 -*-
"""Backfill do gêmeo mascarado — SPEC-085 §F1.3.

    python backend/scripts/backfill_spec085_output_redacted.py --conferir
    python backend/scripts/backfill_spec085_output_redacted.py --aplicar

Preenche `work_steps.output_redacted` das etapas de acionamento que ainda estão
com a coluna nula, usando `app/services/pii_da_sessao.retrato_para_humano`.

## 🔴 Ele NUNCA toca em `output_summary`

Aquela coluna é o **payload de restauração** da sessão:

    output_summary → _ultimo_retrato → sessao_restaurada → render_reply → a URA

Mascarar ali faz um acionamento restaurado responder `...4725` à seguradora.
Este script só ESCREVE na coluna nova, e só onde ela está nula.

## 🔴 E ele não imprime valor nenhum

📊 As 12 linhas de hoje guardam `titular_cpf`, `telefone_contato` e
`client_phone` em claro (P-223). Um backfill que ecoasse o que leu resolveria o
problema no banco e o criaria no terminal, no log e no histórico de quem rodou.
**A saída daqui é contagem e id — nunca conteúdo.**

⚠️ `--aplicar` é a única forma de escrever. Sem ele, o script mede e sai.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

WORKFLOW = "acionamento.seguradora"


def _cliente():
    from supabase import create_client

    url = os.getenv("SUPABASE_URL", "").strip()
    chave = (os.getenv("SUPABASE_SERVICE_KEY")
             or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
             or os.getenv("SUPABASE_KEY") or "").strip()
    if not url or not chave:
        print("ERRO: faltam SUPABASE_URL e SUPABASE_SERVICE_KEY no ambiente.")
        print("      (presenca, nunca o valor — CLAUDE.md §13.3)")
        raise SystemExit(2)
    return create_client(url, chave)


def _mascarador():
    """Importa o mascarador sem passar por `app.services.__init__`, que puxa
    `fastembed` — dependência que este script não precisa ter em pé."""
    import importlib.util
    import types

    for nome in ("app", "app.services"):
        if nome not in sys.modules:
            m = types.ModuleType(nome)
            m.__path__ = [str(RAIZ / Path(*nome.split(".")))]
            sys.modules[nome] = m
    spec = importlib.util.spec_from_file_location(
        "_backfill_pii", str(RAIZ / "app" / "services" / "pii_da_sessao.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--aplicar", action="store_true",
                    help="escreve de verdade; sem isto, so mede")
    ap.add_argument("--conferir", action="store_true",
                    help="so mede (padrao)")
    ap.add_argument("--reescrever", action="store_true",
                    help="refaz TODOS os gemeos, nao so os nulos. 🔴 Necessario "
                         "quando a regra de mascaramento muda: um gemeo escrito "
                         "pela regra antiga continua vazando o que ela deixava "
                         "passar, e o filtro de nulo nunca o alcanca.")
    args = ap.parse_args()

    db = _cliente()
    pii = _mascarador()

    runs = (db.table("work_runs").select("id")
            .eq("workflow_key", WORKFLOW).execute().data or [])
    ids = [r["id"] for r in runs]
    print(f"runs de acionamento .................. {len(ids)}")
    if not ids:
        return 0

    etapas = (db.table("work_steps")
              .select("id, work_run_id, step_key, output_summary, output_redacted")
              .in_("work_run_id", ids).execute().data or [])
    print(f"etapas duraveis ...................... {len(etapas)}")

    pendentes = ([e for e in etapas] if args.reescrever
                 else [e for e in etapas if e.get("output_redacted") is None])
    rotulo = "a REESCREVER (regra nova)" if args.reescrever else "sem o gemeo mascarado"
    print(f"{rotulo:<36} {len(pendentes)}")

    if not args.aplicar:
        print("\n(modo conferencia — nada foi escrito. use --aplicar)")
        return 0

    escritas = falhas = 0
    for etapa in pendentes:
        retrato = pii.retrato_para_humano(etapa.get("output_summary") or {})
        try:
            db.table("work_steps").update(
                {"output_redacted": retrato}).eq("id", etapa["id"]).execute()
            escritas += 1
        except Exception as exc:  # noqa: BLE001
            falhas += 1
            # 🔴 So o TIPO do erro. A mensagem do PostgREST pode ecoar a linha.
            print(f"  FALHOU etapa {etapa['id']}: {type(exc).__name__}")

    print(f"\ngemeos escritos ...................... {escritas}")
    print(f"falhas ............................... {falhas}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
