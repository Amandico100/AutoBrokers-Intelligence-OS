#!/usr/bin/env python3
"""
Sync curated OpenRouter models into llm_pricing table.

Usage:
    cd backend
    python scripts/sync_openrouter_models.py

SPEC-116: only the OpenRouter models the governed catalog already has
(provider='openrouter', lifecycle APPROVED/CANDIDATE) get their prices
refreshed. Nothing is inserted. Prices are fetched live from OpenRouter API.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    from supabase import create_client
    import requests
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    sys.exit(1)

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# SPEC-116 U10 — UMA fonte só. A whitelist escrita à mão (cópia da de
# `app/api/pricing.py`) saiu: os ids vêm do CATÁLOGO governado, pela mesma
# função que o endpoint `/api/admin/pricing/sync-openrouter` usa. Só atualiza
# preço de modelo que o catálogo já tem; NUNCA insere linha nova em llm_pricing
# (modelo novo entra pela migration do catálogo, com ciclo de vida e classe de
# dado — D-116-06: OpenRouter é laboratório).


def modelos_para_sincronizar():
    from app.api.pricing import modelos_openrouter_do_catalogo

    return modelos_openrouter_do_catalogo()


def fetch_openrouter_models():
    """Fetch model list from OpenRouter API."""
    url = f"{OPENROUTER_BASE_URL}/models"
    headers = {}
    if OPENROUTER_API_KEY:
        headers["Authorization"] = f"Bearer {OPENROUTER_API_KEY}"

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json().get("data", [])


def sync_models():
    """Sync curated OpenRouter models with llm_pricing table."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ SUPABASE_URL and SUPABASE_KEY must be set in .env")
        sys.exit(1)

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    print("\n" + "=" * 60)
    print("🔄 Syncing curated OpenRouter models...")
    curated = modelos_para_sincronizar()
    print(f"📋 {len(curated)} OpenRouter models in the governed catalog")
    print("=" * 60 + "\n")

    try:
        all_models = fetch_openrouter_models()
        print(f"📡 {len(all_models)} total models on OpenRouter\n")
    except Exception as e:
        print(f"❌ Error fetching models: {e}")
        sys.exit(1)

    # Index by model ID for fast lookup
    models_by_id = {m["id"]: m for m in all_models}

    success_count = 0
    not_found_count = 0
    error_count = 0

    for model_id in curated:
        model = models_by_id.get(model_id)
        if not model:
            print(f"  ⚠️  {model_id} — not found on OpenRouter")
            not_found_count += 1
            continue

        pricing = model.get("pricing", {})
        prompt_price = float(pricing.get("prompt", "0") or "0")
        completion_price = float(pricing.get("completion", "0") or "0")

        # Convert from per-token to per-million-tokens
        input_per_million = round(prompt_price * 1_000_000, 4)
        output_per_million = round(completion_price * 1_000_000, 4)

        try:
            # Check if model already exists
            existing = (
                supabase.table("llm_pricing")
                .select("id")
                .eq("model_name", model_id)
                .execute()
            )

            if not existing.data:
                # ⛔ nunca insere: modelo novo entra pelo catálogo (SPEC-116 U10)
                print(f"  ⚠️  {model_id} — not in llm_pricing, skipped")
                not_found_count += 1
                continue
            # UPDATE: only prices; preserve sell_multiplier, is_active, lifecycle
            supabase.table("llm_pricing").update({
                "input_price_per_million": input_per_million,
                "output_price_per_million": output_per_million,
            }).eq("model_name", model_id).execute()

            print(f"  ✅ {model_id} (${input_per_million:.2f}/${output_per_million:.2f} per MTok)")
            success_count += 1

        except Exception as e:
            print(f"  ❌ {model_id}: {e}")
            error_count += 1

    print("\n" + "=" * 60)
    print(f"📊 Result: {success_count} synced, {not_found_count} not found, {error_count} errors")
    print("=" * 60 + "\n")

    if success_count > 0:
        print("✅ Sync complete! Next steps:")
        print("   1. Restart backend to reload pricing cache")
        print("   2. Go to /admin/finops/pricing to review OpenRouter models")
        print("   3. Adjust sell_multiplier per model if needed")


if __name__ == "__main__":
    sync_models()
