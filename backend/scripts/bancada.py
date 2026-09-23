# -*- coding: utf-8 -*-
"""SPEC-116 U11 — a BANCADA E2E pela linha de comando.

Roda o MOTOR REAL de um papel com um ou mais BRAÇOS (provider:model[:effort])
sobre o corpus mascarado (`tests/corpus/bancada/<papel>/casos.jsonl`), k vezes,
e imprime por braço: pass@1 · pass^k · pass^k do subconjunto crítico · custo por
sucesso · p50/p95 · acerto de tool/args · efeitos duplicados · recuperação após
falha · BLOCKED_BY_INFRA.

    cd backend
    # linha de controle (CLAUDE.md §9.2): o relatório TEM de separar os dois
    python scripts/bancada.py --papel atendimento --braco dublê:perfeito --braco dublê:burro --k 3 --nivel N1 --ensaio
    # braço real (depois da costura F5b), só o subconjunto crítico, com teto
    python scripts/bancada.py --papel atendimento --braco anthropic:claude-sonnet-5:medium --critico --k 3 --teto-usd 5 --gravar
    # ler de novo um relatório
    python scripts/bancada.py --relatorio <grupo_bancada | arquivo.json>
    # carregar o corpus na Eval Fabric (datasets/versões/casos; idempotente)
    python scripts/bancada.py --carregar-corpus --gravar

`--ensaio` (padrão) NÃO toca o banco: grava só um JSON local e diz onde.
`--gravar` escreve em `eval_runs`/`eval_case_results` (exige a migration
20260923_03 aplicada). O teto em US$ vem de `--teto-usd` ou de BANCADA_TETO_USD
(padrão 100) e é conferido ANTES de cada chamada ao modelo; braço sem preço no
catálogo é RECUSADO (a bancada não inventa preço).
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Bancada E2E da SPEC-116 (Eval Fabric estendida).")
    p.add_argument("--papel", help="atendimento · chat_principal · cobranca · portal_decisao · dispatch · "
                                   "memoria · visao · hyde · extrator_planos · juiz · transcricao")
    p.add_argument("--braco", action="append", default=[],
                   help="provider:model[:effort] (repetível). `dublê:perfeito` e `dublê:burro` = linha de controle")
    p.add_argument("--k", type=int, default=3, help="tentativas por caso (pass^k)")
    p.add_argument("--nivel", default="N1", choices=("N1", "N2"))
    p.add_argument("--casos", default=None, help="filtro por trecho da chave do caso")
    p.add_argument("--critico", action="store_true", help="só o subconjunto crítico")
    p.add_argument("--teto-usd", type=float, default=None, help="teto de gasto da rodada (padrão: env BANCADA_TETO_USD ou 100)")
    modo = p.add_mutually_exclusive_group()
    modo.add_argument("--gravar", action="store_true", help="grava em eval_runs/eval_case_results")
    modo.add_argument("--ensaio", action="store_true", help="(padrão) nada no banco; só relatório local em JSON")
    p.add_argument("--saida", default=None, help="caminho do JSON local (modo ensaio)")
    p.add_argument("--relatorio", default=None, help="reimprime a tabela de um grupo_bancada ou de um arquivo .json")
    p.add_argument("--carregar-corpus", action="store_true", help="corpus → eval_datasets/versions/cases")
    p.add_argument("--verboso", action="store_true")
    a = p.parse_args(argv)

    logging.basicConfig(level=logging.INFO if a.verboso else logging.CRITICAL)
    if not a.verboso:
        logging.disable(logging.WARNING)

    from app.services.evals import bancada as B

    if a.relatorio:
        if os.path.exists(a.relatorio):
            print(B.relatorio_de_arquivo(a.relatorio))
        else:
            print(B.relatorio_do_banco(a.relatorio))
        return 0

    if a.carregar_corpus:
        info = B.carregar_corpus(gravar=bool(a.gravar))
        for papel, i in info.items():
            print(f"{papel:<16} v{i['versao']}  casos={i['casos']:<3} novos={i['novos']:<3} "
                  f"divergentes={i['divergentes']}" + ("" if a.gravar else "  (ensaio: nada gravado)"))
        return 0

    if not a.papel or not a.braco:
        p.error("--papel e ao menos um --braco são obrigatórios (ou use --relatorio / --carregar-corpus)")

    rel = B.rodar_bancada(a.papel, a.braco, k=a.k, nivel=a.nivel, gravar=bool(a.gravar),
                          teto_usd=a.teto_usd, filtro=a.casos, critico=a.critico)
    print(rel.tabela())
    print(f"\ngrupo_bancada: {rel.grupo_bancada} · casos: {len({r.chave for r in rel.resultados})} "
          f"· tentativas: {len(rel.resultados)}")
    if a.gravar:
        print(f"gravado: {len(rel.runs)} eval_run(s) — releia com --relatorio {rel.grupo_bancada}")
    else:
        print(f"ensaio (nada no banco) · relatório local: {rel.salvar(a.saida)}")
    return 2 if rel.parada and rel.parada.startswith("teto_usd") else 0


if __name__ == "__main__":
    sys.exit(main())
