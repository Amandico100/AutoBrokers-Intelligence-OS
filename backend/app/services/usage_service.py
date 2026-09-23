"""
Usage Service - Token Usage and Cost Tracking for FinOps

Centralizes pricing calculations and logging to Supabase.
Pricing comes from the governed catalog (`llm_pricing`, SPEC-116) with an
in-memory cache; the offline fallback is the catalog SNAPSHOT.
"""

import json
import logging
import re
import time
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional

from ..core.config import settings
from ..core.database import get_supabase_client

logger = logging.getLogger(__name__)


# ============================================================================
# CACHE GLOBAL (TTL 5 minutos)
# ============================================================================
_pricing_cache: Dict[str, dict] = {}
_cache_loaded_at: float = 0
CACHE_TTL_SECONDS = 300  # 5 minutos


# ============================================================================
# 🔴 SPEC-116 U3 — O PREÇO VEM DO CATÁLOGO, E SÓ DELE
# ============================================================================
# Aqui morava `PRICING_TABLE`: 60 linhas escritas à mão, sem Claude 5, com
# modelos retirados — um 11º catálogo (EVIDENCIAS/01 §d). Saiu. Com o banco fora,
# o fallback é o SNAPSHOT gerado do próprio catálogo
# (`app/factories/modelos_snapshot.json`, `scripts/gerar_snapshot_de_modelos.py`).
#
# ⛔ E o preço de modelo DESCONHECIDO deixou de ser o do mini barato
# (📊 era `usage_service.py:163-165`): Opus 5 cobrado assim sai ~33x menor.
# Agora: custo 0 + `details.preco_desconhecido=true` + log de alerta.
# ⚠️ Por que 0 e não NULL: 📊 `token_usage_logs.total_cost_usd` ACEITA NULL
# (is_nullable=YES, default 0 — medido 23/09/2026 em information_schema), mas
# `workers/billing_tasks.py:220` e `:351` fazem
# `Decimal(str(log.get("total_cost_usd", 0)))`: com NULL a chave existe, vira
# `Decimal("None")` e o faturamento quebra. A flag é o que separa "custou zero"
# de "não sabemos".
_SNAPSHOT_PATH = Path(__file__).resolve().parent.parent / "factories" / "modelos_snapshot.json"

_COLUNAS_DE_PRECO = (
    "model_name, input_price_per_million, output_price_per_million, unit, sell_multiplier, "
    "cache_write_multiplier, cache_read_multiplier, cached_input_multiplier, "
    "input_price_long, output_price_long, limiar_contexto_longo"
)
#: enquanto a migration 20260923_01 não estiver aplicada, as colunas novas não existem
_COLUNAS_DE_PRECO_ANTIGAS = (
    "model_name, input_price_per_million, output_price_per_million, unit, sell_multiplier, "
    "cache_write_multiplier, cache_read_multiplier, cached_input_multiplier"
)

_SUFIXO_DE_DATA = re.compile(r"-(\d{4}-\d{2}-\d{2}|\d{8})$")


def _f(v) -> Optional[float]:
    return None if v is None else float(v)


def _linha_de_preco(row: dict) -> Optional[dict]:
    """Uma linha do catálogo no formato do cache. None = preço DESCONHECIDO."""
    entrada = _f(row.get("input_price_per_million"))
    saida = _f(row.get("output_price_per_million"))
    # 0/0 é como o catálogo marca "sem preço verificado" (ex.: rerank da Cohere)
    if entrada is None or saida is None or (entrada == 0 and saida == 0):
        return None
    limiar = row.get("limiar_contexto_longo")
    return {
        "input": entrada,
        "output": saida,
        "unit": row.get("unit") or "token",
        "sell_multiplier": float(row.get("sell_multiplier") or 2.68),
        # Multiplicadores de cache podem ser NULL
        "cache_write_multiplier": _f(row.get("cache_write_multiplier")),
        "cache_read_multiplier": _f(row.get("cache_read_multiplier")),
        "cached_input_multiplier": _f(row.get("cached_input_multiplier")),
        "input_long": _f(row.get("input_price_long")),
        "output_long": _f(row.get("output_price_long")),
        "limiar_longo": int(limiar) if limiar else None,
    }


def _precos_do_snapshot() -> Dict[str, dict]:
    """Preços do snapshot do catálogo (fallback sem banco)."""
    try:
        doc = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        logger.error(f"[UsageService] ❌ snapshot de modelos ilegível: {e}")
        return {}
    out: Dict[str, dict] = {}
    for nome, row in (doc.get("catalogo") or {}).items():
        if row.get("is_active") is False:
            continue
        linha = _linha_de_preco(row)
        if linha:
            out[nome] = linha
    return out


class UsageService:
    """
    Centralized service for tracking token usage and costs.
    Uses database-backed pricing with in-memory cache.
    """

    def __init__(self):
        self.supabase = get_supabase_client()
        self._ensure_cache_loaded()

    def _ensure_cache_loaded(self):
        """Carrega cache do banco se expirado ou vazio."""
        global _pricing_cache, _cache_loaded_at

        now = time.time()

        # Cache ainda válido
        if _pricing_cache and (now - _cache_loaded_at) < CACHE_TTL_SECONDS:
            return

        try:
            tabela = self.supabase.client.table
            try:
                result = tabela("llm_pricing").select(_COLUNAS_DE_PRECO) \
                    .eq("is_active", True).execute()
            except Exception:  # noqa: BLE001 — colunas da SPEC-116 ainda não aplicadas
                result = tabela("llm_pricing").select(_COLUNAS_DE_PRECO_ANTIGAS) \
                    .eq("is_active", True).execute()

            if result.data and len(result.data) > 0:
                cache: Dict[str, dict] = {}
                for row in result.data:
                    linha = _linha_de_preco(row)
                    if linha:
                        cache[row["model_name"]] = linha
                _pricing_cache = cache
                _cache_loaded_at = now
                logger.info(f"[UsageService] ✅ Pricing cache loaded from DB: {len(_pricing_cache)} models")
            else:
                # Banco vazio - usa o snapshot do catálogo
                _pricing_cache = _precos_do_snapshot()
                _cache_loaded_at = now
                logger.warning("[UsageService] ⚠️ No pricing in DB, using the models snapshot")

        except Exception as e:
            # Erro de conexão/tabela - usa o snapshot do catálogo
            logger.error(f"[UsageService] ❌ Failed to load pricing from DB: {e}")
            if not _pricing_cache:
                _pricing_cache = _precos_do_snapshot()
                _cache_loaded_at = now
                logger.info("[UsageService] Using the models snapshot due to DB error")

    def reload_cache(self):
        """Força reload do cache (chamar via API admin)."""
        global _cache_loaded_at
        _cache_loaded_at = 0  # Invalida cache
        self._ensure_cache_loaded()
        return len(_pricing_cache)

    def get_pricing(self, model: str) -> Optional[dict]:
        """Preço do catálogo para um modelo. None = DESCONHECIDO.

        ⛔ Nunca devolve o preço de OUTRO modelo. Aceita o id DATADO que o
        provedor devolve (sufixo -AAAA-MM-DD ou -AAAAMMDD) quando só a forma
        sem data está no catálogo.
        """
        pricing = self._buscar_preco(model)
        if pricing is None:
            logger.warning(
                f"[UsageService] ⚠️ PRECO DESCONHECIDO para o modelo {model!r}: custo gravado 0 "
                f"com details.preco_desconhecido=true (SPEC-116). Cadastre-o em llm_pricing."
            )
        return pricing

    def _buscar_preco(self, model: str) -> Optional[dict]:
        self._ensure_cache_loaded()
        pricing = _pricing_cache.get(model) if model else None
        if pricing is None and model:
            sem_data = _SUFIXO_DE_DATA.sub("", model)
            if sem_data != model:
                pricing = _pricing_cache.get(sem_data)
        return pricing

    def preco_conhecido(self, model: str) -> bool:
        """Sem log: quem avisa é `get_pricing`, uma vez por chamada."""
        return self._buscar_preco(model) is not None

    def calculate_cost(
        self, model: str, input_tokens: int, output_tokens: int = 0,
        cache_creation_tokens: int = 0, cache_read_tokens: int = 0, cached_tokens: int = 0
    ) -> float:
        """
        Calculate cost in USD for a given model and token count.

        Supports cache tokens:
        - cache_creation_tokens: Anthropic cache write (catalog cache_write_multiplier)
        - cache_read_tokens: Anthropic cache read (catalog cache_read_multiplier)
        - cached_tokens: OpenAI cached (catalog cached_input_multiplier, already in input_tokens)

        Unknown model → 0.0 (the writer flags `preco_desconhecido`; never another model's price).
        """
        pricing = self.get_pricing(model)
        if pricing is None:
            return 0.0

        # Check if this is audio (per-minute pricing)
        if pricing.get("unit") == "minute":
            minutes = input_tokens / 60.0
            return minutes * pricing["input"]

        input_price = pricing["input"]
        output_price = pricing["output"]
        # Contexto longo (ex.: GPT-6 > 272K, Grok 4.7 > 200K): a chamada INTEIRA
        # passa ao preço longo, como a página do provedor descreve.
        limiar = pricing.get("limiar_longo")
        if limiar and input_tokens > limiar:
            input_price = pricing.get("input_long") or input_price
            output_price = pricing.get("output_long") or output_price

        # Multiplicadores POR MODELO, do catálogo (📊 23/09 eram iguais para as 50
        # linhas). Os padrões abaixo só valem para linha antiga sem multiplicador.
        def _m(chave: str, padrao: float) -> float:
            v = pricing.get(chave)
            return padrao if v is None else v

        cache_write_mult = _m("cache_write_multiplier", 1.25)
        cache_read_mult = _m("cache_read_multiplier", 0.10)
        cached_input_mult = _m("cached_input_multiplier", 0.50)

        # Tokens cacheados JÁ estão incluídos em input_tokens, subtrair para não cobrar 2x
        # - OpenAI: cached_tokens
        # - Anthropic: cache_read_tokens (lidos) + cache_creation_tokens (escritos)
        # SAFETY: max(0, ...) previne valores negativos se API retornar dados inconsistentes
        regular_input_tokens = max(0, input_tokens - cached_tokens - cache_read_tokens - cache_creation_tokens)

        # Input normal (preço cheio) - tokens que não são de cache
        input_cost = (regular_input_tokens / 1_000_000) * input_price

        # OpenAI cache (usa multiplier do catálogo)
        openai_cache_cost = (cached_tokens / 1_000_000) * input_price * cached_input_mult

        # Anthropic cache write (usa multiplier do catálogo)
        cache_write_cost = (cache_creation_tokens / 1_000_000) * input_price * cache_write_mult

        # Anthropic cache read (usa multiplier do catálogo)
        cache_read_cost = (cache_read_tokens / 1_000_000) * input_price * cache_read_mult

        # Output
        output_cost = (output_tokens / 1_000_000) * output_price

        return input_cost + openai_cache_cost + cache_write_cost + cache_read_cost + output_cost

    def track_cost_sync(
        self,
        service_type: str,
        model: str,
        input_tokens: int,
        output_tokens: int = 0,
        company_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cache_creation_tokens: int = 0,
        cache_read_tokens: int = 0,
        cached_tokens: int = 0,
    ) -> bool:
        """
        Synchronous version of track_cost for non-async contexts.
        Now supports cache token tracking.
        """
        try:
            cost = self.calculate_cost(
                model, input_tokens, output_tokens,
                cache_creation_tokens, cache_read_tokens, cached_tokens
            )

            # Convert UUIDs to strings if passed as UUID objects
            if company_id and hasattr(company_id, 'hex'):
                company_id = str(company_id)
            if agent_id and hasattr(agent_id, 'hex'):
                agent_id = str(agent_id)

            detalhes = dict(details or {})
            if not self.preco_conhecido(model):
                detalhes["preco_desconhecido"] = True

            log_entry = {
                "service_type": service_type,
                "model_name": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_cost_usd": cost,
                "details": detalhes,
                "created_at": datetime.utcnow().isoformat(),
                "cache_creation_tokens": cache_creation_tokens,
                "cache_read_tokens": cache_read_tokens,
                "cached_tokens": cached_tokens,
            }

            if company_id:
                log_entry["company_id"] = company_id
            if agent_id:
                log_entry["agent_id"] = agent_id

            result = (
                self.supabase.client.table("token_usage_logs")
                .insert(log_entry)
                .execute()
            )

            if result.data:
                cache_info = ""
                if cache_creation_tokens or cache_read_tokens:
                    cache_info = f" | cache_w={cache_creation_tokens} cache_r={cache_read_tokens}"
                elif cached_tokens:
                    cache_info = f" | cached={cached_tokens}"

                logger.info(
                    f"[UsageService] ✅ Logged {service_type} | {model} | "
                    f"in={input_tokens} out={output_tokens}{cache_info} | ${cost:.6f}"
                )
                return True
            return False

        except Exception as e:
            logger.error(f"[UsageService] ❌ Failed to log usage: {e}")
            return False

    def calculate_and_debit_client(
        self,
        company_id: str,
        agent_id: Optional[str],
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        Calcula custo para o cliente (com multiplicador) e debita do saldo.

        Fórmula: custo_cliente_brl = custo_real_usd × DOLAR × sell_multiplier

        Args:
            company_id: ID da empresa
            agent_id: ID do agente (opcional)
            model: Nome do modelo LLM
            input_tokens: Tokens de entrada
            output_tokens: Tokens de saída

        Returns:
            Valor debitado em BRL (float)
        """
        from .billing_service import get_billing_service

        DOLLAR_RATE = settings.DOLLAR_RATE

        # Custo real em USD
        cost_usd = Decimal(str(self.calculate_cost(model, input_tokens, output_tokens)))

        # Busca multiplicador do modelo (desconhecido: o custo já é 0)
        pricing = self.get_pricing(model) or {}
        multiplier = Decimal(str(pricing.get("sell_multiplier", 2.68)))

        # Custo para o cliente em BRL
        cost_client_brl = cost_usd * DOLLAR_RATE * multiplier

        # Debita do saldo
        billing_service = get_billing_service()
        billing_service.debit_credits(
            company_id=company_id,
            agent_id=agent_id,
            amount_brl=cost_client_brl,
            model_name=model,
            tokens_input=input_tokens,
            tokens_output=output_tokens
        )

        logger.debug(
            f"[UsageService] Client debit: {model} | "
            f"USD ${cost_usd:.6f} → BRL R${cost_client_brl:.4f} (×{multiplier})"
        )

        return float(cost_client_brl)


# Singleton instance
_usage_service: Optional[UsageService] = None


def get_usage_service() -> UsageService:
    """Get or create singleton UsageService instance."""
    global _usage_service
    if _usage_service is None:
        _usage_service = UsageService()
    return _usage_service


def preload_pricing_cache():
    """
    Preload pricing cache on app startup.
    Call this in main.py lifespan to avoid cold start delay.
    """
    service = get_usage_service()
    count = service.reload_cache()
    logger.info(f"[UsageService] Preloaded {count} pricing entries")
    return count
