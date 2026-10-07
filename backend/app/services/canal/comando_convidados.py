# -*- coding: utf-8 -*-
"""Os convidados do canal de cotação (piloto FECHADO) — SPEC-133-A F1, D-133A-04.

O Founder põe e tira os testadores por aqui (ou pelo admin), nunca no código (§13.9). A empresa do canal vem do BANCO
(`company_kind='platform_canal'`); o telefone nunca sai inteiro na tela nem no log (só os 4 últimos).

    python -m app.services.canal.comando_convidados --adicionar 5547999999999 --apelido "Teste 1" [--limite 3]
    python -m app.services.canal.comando_convidados --listar
    python -m app.services.canal.comando_convidados --remover 5547999999999

`--remover` DESATIVA (o histórico do consentimento continua apontando para alguém); `--adicionar` de novo reativa.
Saída: 0 ok · 1 nada mudou · 2 entrada inválida · 3 banco/empresa do canal indisponível.
"""
from __future__ import annotations

import argparse
import sys
from typing import Any, List, Optional

from app.services.canal import repositorio as repo


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m app.services.canal.comando_convidados",
                                description="Convidados do canal de cotação (piloto fechado).")
    acao = p.add_mutually_exclusive_group(required=True)
    acao.add_argument("--adicionar", metavar="TELEFONE", help="E.164 só dígitos, ex.: 5547999999999")
    acao.add_argument("--remover", metavar="TELEFONE")
    acao.add_argument("--listar", action="store_true")
    p.add_argument("--apelido", default=None, help="até 60 caracteres (só com --adicionar)")
    p.add_argument("--limite", type=int, default=None, help="cotações por dia deste número (0–100; padrão: o da config)")
    p.add_argument("--company", default=None, help="id da empresa do canal (só se houver mais de uma)")
    return p


def main(argv: Optional[List[str]] = None, *, db: Any = None) -> int:
    args = _parser().parse_args(argv)
    try:  # 📊 07/10: no console do Windows (cp1252) o "❌" derrubava o próprio aviso de erro
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 — stdout capturado (teste) não tem reconfigure
        pass
    try:
        return _rodar(args, db)
    except Exception as erro:  # noqa: BLE001 — banco fora / tabela ainda não aplicada: diz o quê, sem traceback
        print(f"❌ banco indisponível ({type(erro).__name__}) — a migration 20261007_01 já foi aplicada?")
        return 3


def _rodar(args: argparse.Namespace, db: Any) -> int:
    if db is None:
        from app.core.database import get_supabase_client

        db = get_supabase_client().client
    try:
        company_id = args.company or repo.empresa_do_canal(db)
    except Exception as erro:  # noqa: BLE001
        print(f"❌ empresa do canal indisponível ({type(erro).__name__}: {erro})")
        return 3
    if args.listar:
        linhas = repo.listar_convidados(db, company_id)
        print(f"Convidados do canal ({len(linhas)}):")
        for x in linhas:
            limite = x.get("limite_dia") if x.get("limite_dia") is not None else "padrão"
            print(f"  {repo.mascarar(x.get('telefone'))}  {'ativo' if x.get('ativo') else 'inativo':8} "
                  f"limite/dia={limite}  {x.get('apelido') or ''}")
        return 0
    alvo = args.adicionar or args.remover
    tel = repo.canonico(alvo)
    if not tel:
        print("❌ telefone inválido: use o E.164 só com dígitos (ex.: 5547999999999)")
        return 2
    if args.adicionar:
        try:
            repo.adicionar_convidado(db, company_id, tel, apelido=args.apelido, limite_dia=args.limite)
        except ValueError as erro:
            print(f"❌ {erro}")
            return 2
        print(f"✅ convidado {repo.mascarar(tel)} ativo no canal")
        return 0
    n = repo.remover_convidado(db, company_id, tel)
    print(f"{'✅' if n else '⚠️'} {repo.mascarar(tel)}: {'desativado' if n else 'não estava na lista'}")
    return 0 if n else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
