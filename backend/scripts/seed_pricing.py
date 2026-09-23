#!/usr/bin/env python3
"""LEGADO SEM ESCRITA (SPEC-116 U3) — este script NÃO semeia mais `llm_pricing`.

Ele era o 6º catálogo do repositório (EVIDENCIAS/01 §d): 60 preços escritos à mão,
sem Claude 5, com modelos retirados, e um `upsert` que sobrescrevia o banco com
esse preço velho a cada execução. 📊 23/09/2026: Sonnet 5 cobrado 3/15 (oficial
2/10) e o mesmo multiplicador de cache para as 50 linhas.

A fonte de verdade do catálogo agora é a MIGRATION
`backend/supabase/migrations/20260923_01_spec116_catalogo_e_papeis.sql` (preço com
`fonte_preco_url` + `preco_verificado_em`) e, depois dela, o próprio banco. O
snapshot versionado é gerado por `scripts/gerar_snapshot_de_modelos.py`.

Escolha (e por quê): ler do snapshot e continuar gravando manteria DOIS escritores
do mesmo preço — o defeito que a SPEC-116 fecha. Então este script só CONFERE:
compara o banco com o snapshot e lista a divergência. Trocar preço = migration nova
ou edição governada em `/admin/finops/pricing`; nunca este arquivo.

Uso (de backend/):  python scripts/seed_pricing.py        # só leitura
"""
import json
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
SNAPSHOT = BACKEND / "app" / "factories" / "modelos_snapshot.json"
CAMPOS = ("input_price_per_million", "output_price_per_million", "cache_read_multiplier",
          "cache_write_multiplier", "cached_input_multiplier", "lifecycle")


def conferir() -> int:
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))["catalogo"]
    try:
        from dotenv import load_dotenv
        from supabase import create_client
    except ImportError as e:
        print(f"❌ Dependência não encontrada: {e}")
        return 1
    load_dotenv(BACKEND / ".env")
    url, chave = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY")
    if not url or not chave:
        print("❌ SUPABASE_URL e SUPABASE_KEY devem estar definidos no .env")
        return 1
    linhas = create_client(url, chave).table("llm_pricing").select("*").execute().data or []
    banco = {r["model_name"]: r for r in linhas}
    divergencias = 0
    for nome in sorted(set(snap) | set(banco)):
        s, b = snap.get(nome), banco.get(nome)
        if s is None or b is None:
            print(f"  ≠ {nome}: {'só no banco' if s is None else 'só no snapshot'}")
            divergencias += 1
            continue
        for c in CAMPOS:
            vs, vb = s.get(c), b.get(c)
            if vs is None:
                continue  # a migration não precifica esta linha: o banco manda
            if (float(vs) != float(vb or 0)) if c != "lifecycle" else (vs != vb):
                print(f"  ≠ {nome}.{c}: snapshot={vs} banco={vb}")
                divergencias += 1
    print(f"\n{'✅ banco = snapshot' if not divergencias else f'⚠️ {divergencias} divergência(s)'} "
          f"— nada foi escrito (script legado, SPEC-116).")
    return 0 if not divergencias else 2


if __name__ == "__main__":
    sys.exit(conferir())
