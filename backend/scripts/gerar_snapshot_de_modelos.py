#!/usr/bin/env python3
"""SPEC-116 U3 — gera `backend/app/factories/modelos_snapshot.json`.

O snapshot é o CATÁLOGO (`llm_pricing`) + as ROTAS (`llm_papeis`) congelados num
arquivo versionado. Serve a três leitores:
  1. o resolvedor (`app/factories/model_policy.py`) quando o banco não responde;
  2. o legacy gate do CI (`tests/test_nenhum_modelo_fora_do_catalogo.py`);
  3. o TypeScript que precisar listar modelos sem ir ao banco (F4).

🔴 UMA fonte, nunca duas listas à mão. Há dois modos, e os dois leem a MESMA
   verdade por caminhos diferentes:
     --banco      lê `llm_pricing` + `llm_papeis` do Supabase (depois que a
                  migration foi aplicada — é o modo normal do gerente)
     (default)    lê os blocos `$catalogo$` e `$papeis$` DENTRO da migration
                  `20260923_01_spec116_catalogo_e_papeis.sql` — o mesmo texto
                  que o Postgres aplica.

Uso (de backend/):
    python scripts/gerar_snapshot_de_modelos.py            # da migration
    python scripts/gerar_snapshot_de_modelos.py --banco    # do banco
    python scripts/gerar_snapshot_de_modelos.py --conferir # só compara, não grava

⚠️ No modo migration, linha que a migration não precifica (HISTORICAL antiga) sai
com preço `null` — no banco ela mantém o preço velho. Para o UsageService os
dois significam o mesmo: modelo fora de uso, preço não verificado.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Tuple

BACKEND = Path(__file__).resolve().parent.parent
MIGRATION = BACKEND / "supabase" / "migrations" / "20260923_01_spec116_catalogo_e_papeis.sql"
SNAPSHOT = BACKEND / "app" / "factories" / "modelos_snapshot.json"

#: As colunas do catálogo que o snapshot carrega — a mesma lista nos dois modos.
COLUNAS_CATALOGO = (
    "model_name", "provider", "tipo", "api_surface", "lifecycle", "classes_de_dado",
    "capacidades", "input_price_per_million", "output_price_per_million",
    "cache_read_multiplier", "cache_write_multiplier", "cached_input_multiplier",
    "input_price_long", "output_price_long", "limiar_contexto_longo", "unit",
    "is_active", "substituido_por", "retirada_em", "base_url", "api_key_env",
    "preco_verificado_em", "fonte_preco_url", "notas",
)
COLUNAS_PAPEIS = (
    "papel", "descricao", "provider", "modelo_primario", "esforco",
    "provider_reserva", "modelo_reserva", "esforco_reserva", "classe_de_dado",
    "risco", "versao", "motivo",
)
_NUMERICAS = {
    "input_price_per_million", "output_price_per_million", "cache_read_multiplier",
    "cache_write_multiplier", "cached_input_multiplier", "input_price_long",
    "output_price_long",
}


def _num(v: Any):
    if v is None:
        return None
    if isinstance(v, (int, float, Decimal, str)):
        f = float(v)
        return int(f) if f.is_integer() else round(f, 6)
    return v


def _normalizar_catalogo(linha: Dict[str, Any], *, default_ativo: bool) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for c in COLUNAS_CATALOGO:
        v = linha.get(c)
        if c in _NUMERICAS:
            v = _num(v)
        elif c == "limiar_contexto_longo" and v is not None:
            v = int(v)
        elif c in ("retirada_em", "preco_verificado_em") and v is not None:
            v = str(v)[:10]
        elif c == "classes_de_dado":
            v = sorted(v) if v else []
        elif c == "capacidades":
            v = v or {}
        elif c == "is_active":
            v = default_ativo if v is None else bool(v)
        elif c == "unit":
            v = v or "token"
        out[c] = v
    return out


def _normalizar_papel(linha: Dict[str, Any]) -> Dict[str, Any]:
    out = {c: linha.get(c) for c in COLUNAS_PAPEIS}
    out["versao"] = int(out.get("versao") or 1)
    return out


def _bloco(sql: str, marca: str) -> str:
    # o bloco é o JSON entre as marcas — `$marca$ [ ... ] $marca$` (a marca
    # também aparece no cabeçalho em prosa; o `[` logo depois dela a separa).
    m = re.search(r"\$%s\$\s*(\[.*?\])\s*\$%s\$" % (marca, marca), sql, re.S)
    if not m:
        raise SystemExit(f"bloco ${marca}$ não encontrado em {MIGRATION.name}")
    return m.group(1)


def ler_da_migration(caminho: Path = MIGRATION) -> Tuple[Dict[str, dict], Dict[str, dict]]:
    """Catálogo e rotas exatamente como a migration os declara."""
    sql = caminho.read_text(encoding="utf-8")
    catalogo_bruto = json.loads(_bloco(sql, "catalogo"))
    papeis_bruto = json.loads(_bloco(sql, "papeis"))
    m = re.search(r"'(seed SPEC-116:[^']*)'", sql)
    motivo_seed = m.group(1) if m else None
    catalogo = {
        r["model_name"]: _normalizar_catalogo(r, default_ativo=True) for r in catalogo_bruto
    }
    papeis = {}
    for r in papeis_bruto:
        r = dict(r)
        r.setdefault("motivo", motivo_seed)
        r.setdefault("versao", 1)
        papeis[r["papel"]] = _normalizar_papel(r)
    return catalogo, papeis


def ler_do_banco() -> Tuple[Dict[str, dict], Dict[str, dict]]:
    """Catálogo e rotas do Supabase — o MESMO cliente do UsageService."""
    sys.path.insert(0, str(BACKEND))
    try:
        from dotenv import load_dotenv
        load_dotenv(BACKEND / ".env")
    except Exception:  # noqa: BLE001
        pass
    from app.core.database import get_supabase_client

    cli = get_supabase_client().client
    cat = cli.table("llm_pricing").select(",".join(COLUNAS_CATALOGO)).execute().data or []
    pap = cli.table("llm_papeis").select(",".join(COLUNAS_PAPEIS)).execute().data or []
    catalogo = {r["model_name"]: _normalizar_catalogo(r, default_ativo=True) for r in cat}
    papeis = {r["papel"]: _normalizar_papel(r) for r in pap}
    return catalogo, papeis


def montar(catalogo: dict, papeis: dict, origem: str, fonte: str) -> dict:
    return {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "origem": origem,
        "fonte": fonte,
        "aviso": "GERADO por backend/scripts/gerar_snapshot_de_modelos.py — não edite à mão.",
        "catalogo": {k: catalogo[k] for k in sorted(catalogo)},
        "papeis": {k: papeis[k] for k in sorted(papeis)},
    }


def gravar(doc: dict, destino: Path = SNAPSHOT) -> None:
    destino.write_text(
        json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--banco", action="store_true", help="lê do Supabase em vez da migration")
    ap.add_argument("--conferir", action="store_true", help="compara com o snapshot atual e não grava")
    a = ap.parse_args(argv)

    if a.banco:
        catalogo, papeis = ler_do_banco()
        origem, fonte = "banco", "llm_pricing + llm_papeis"
    else:
        catalogo, papeis = ler_da_migration()
        origem, fonte = "migration", f"backend/supabase/migrations/{MIGRATION.name}"

    if not catalogo or not papeis:
        print("❌ fonte vazia — nada gravado (migration não aplicada?)")
        return 2

    doc = montar(catalogo, papeis, origem, fonte)
    if a.conferir:
        atual = json.loads(SNAPSHOT.read_text(encoding="utf-8")) if SNAPSHOT.exists() else {}
        igual = (atual.get("catalogo") == doc["catalogo"] and atual.get("papeis") == doc["papeis"])
        print(("✅ snapshot em dia com " if igual else "❌ snapshot DIVERGE de ") + origem)
        return 0 if igual else 1

    gravar(doc)
    ciclos: Dict[str, int] = {}
    for r in catalogo.values():
        ciclos[r["lifecycle"] or "<NULO>"] = ciclos.get(r["lifecycle"] or "<NULO>", 0) + 1
    print(f"✅ {SNAPSHOT.relative_to(BACKEND)} ← {origem}: {len(catalogo)} modelos · "
          f"{len(papeis)} papéis · {dict(sorted(ciclos.items()))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
