"""
Cost Callback Handler for LangChain

Automatically captures token usage from LLM calls and logs to UsageService.
Inject this callback into any ChatOpenAI instance to track costs.
🔥 CORREÇÃO: Suporte a Reasoning Tokens (GPT-5/o1) e usage_metadata
"""

import logging
from typing import Any, Dict, Optional
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

logger = logging.getLogger(__name__)


class CostCallbackHandler(BaseCallbackHandler):
    """
    LangChain callback handler that tracks token usage and costs.
    Now supports standard 'usage_metadata' from LangChain core (GPT-5/o1 ready).
    """

    def __init__(
        self,
        service_type: str,
        company_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        model_name: str = None,  # <--- NOVO PARÂMETRO
    ):
        """
        Initialize the cost callback handler.
        """
        super().__init__()
        self.service_type = service_type
        self.company_id = company_id
        self.agent_id = agent_id
        self.details = details or {}
        self.model_name = model_name  # <--- Armazena

        # Import here to avoid circular imports
        from ...services.usage_service import get_usage_service

        self.usage_service = get_usage_service()

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """
        Called when LLM call completes. Extract token usage and log.
        """
        try:
            if not response:
                return

            input_tokens = 0
            output_tokens = 0
            reasoning_tokens = 0
            model = "unknown"

            # Blindagem: Usa getattr para evitar AttributeError em None
            llm_output = getattr(response, "llm_output", None) or {}

            # Tenta pegar do output do LLM, se falhar, usa o que guardamos no init
            model = llm_output.get("model_name", self.model_name)

            # Se ainda for unknown (ou llm_output for None), usa o forçado
            if model == "unknown" or not model:
                model = self.model_name or "unknown"

            # === ESTRATÉGIA 1: usage_metadata (Padrão Novo - GPT-5/o1/LangChain Moderno) ===
            # Cache tokens para billing correto
            cache_creation_tokens = 0  # Anthropic cache write
            cache_read_tokens = 0      # Anthropic cache read
            cached_tokens = 0          # OpenAI cached input

            generations = getattr(response, "generations", None)
            if generations and len(generations) > 0 and len(generations[0]) > 0:
                generation = generations[0][0]

                if hasattr(generation, "message") and hasattr(generation.message, "usage_metadata"):
                    meta = generation.message.usage_metadata
                    if meta:
                        input_tokens = meta.get("input_tokens", 0)
                        output_tokens = meta.get("output_tokens", 0)

                        # Extrair Reasoning Tokens
                        output_details = meta.get("output_token_details") or {}
                        reasoning_tokens = output_details.get("reasoning_tokens", 0)

                        # === CACHE TOKENS ===
                        input_details = meta.get("input_token_details") or {}

                        # Anthropic: cache_creation e cache_read (dentro de input_token_details)
                        # LangChain usa esses nomes, não cache_creation_input_tokens
                        cache_creation_tokens = (
                            input_details.get("cache_creation", 0) or
                            meta.get("cache_creation_input_tokens", 0)  # fallback legado
                        )
                        cache_read_tokens = (
                            input_details.get("cache_read", 0) or
                            meta.get("cache_read_input_tokens", 0)  # fallback legado
                        )

                        # OpenAI: cached_tokens (já incluídos em input_tokens)
                        cached_tokens = input_details.get("cached_tokens", 0) or meta.get("cached_tokens", 0)

            # === ESTRATÉGIA 2: llm_output (Padrão Antigo / Legacy OpenAI) ===
            if input_tokens == 0 and output_tokens == 0:
                token_usage = llm_output.get("token_usage") or {}

                if token_usage:
                    input_tokens = token_usage.get("prompt_tokens", 0)
                    output_tokens = token_usage.get("completion_tokens", 0)

                    # Tenta achar reasoning no padrão antigo (raro)
                    details = token_usage.get("completion_tokens_details") or {}
                    reasoning_tokens = details.get("reasoning_tokens", 0)

                    # Cache tokens no padrão antigo
                    prompt_details = token_usage.get("prompt_tokens_details") or {}
                    cached_tokens = prompt_details.get("cached_tokens", 0)

            # Se ainda assim estiver zerado, desiste (provavelmente stream ou erro)
            if input_tokens == 0 and output_tokens == 0:
                logger.debug(f"[CostCallback] No token usage found for model {model}")
                return

            # Prepara detalhes do log
            log_details = {
                **self.details,
                "run_id": str(run_id),
                "reasoning_tokens": reasoning_tokens,  # 🧠 Salva o reasoning para análise futura
            }
            if parent_run_id:
                log_details["parent_run_id"] = str(parent_run_id)

            # SPEC-044: atribuição POR USUÁRIO lida do contexto da requisição
            # (o callback é construído junto com o grafo CACHEADO — a identidade
            # nunca pode vir do construtor, senão atribui ao usuário errado).
            if "user_id" not in log_details:
                try:
                    from app.core.request_context import get_current_user_id

                    _uid = get_current_user_id()
                    if _uid:
                        log_details["user_id"] = _uid
                except Exception:  # noqa: BLE001
                    pass

            # Log Síncrono (pois estamos dentro de um callback)
            self.usage_service.track_cost_sync(
                service_type=self.service_type,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                company_id=self.company_id,
                agent_id=self.agent_id,
                details=log_details,
                cache_creation_tokens=cache_creation_tokens,
                cache_read_tokens=cache_read_tokens,
                cached_tokens=cached_tokens,
            )

            # SPEC-062 §21 — o mesmo consumo, no ledger que a SPEC-062 usa.
            self._registrar_no_ledger(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_creation_tokens=cache_creation_tokens,
                cache_read_tokens=cache_read_tokens,
                cached_tokens=cached_tokens,
                run_id=run_id,
                parent_run_id=parent_run_id,
            )

        except Exception as e:
            # Nunca falha a chamada do LLM por erro de log
            logger.error(f"[CostCallback] Error logging usage: {e}")

    # ------------------------------------------------------------------
    # SPEC-062 §21 — Usage Ledger
    # ------------------------------------------------------------------
    #
    # `usage_events` existe com a forma da §21.1 desde a SPEC-055 e estava com
    # ZERO linhas: tabela sem escritor. O único que chamava o `UsageService`
    # dela era o Firecrawl. Todo o consumo de LLM ia só para
    # `token_usage_logs` (1.239 linhas), que é o ledger legado — ele registra
    # token por modelo, mas não sabe dizer de qual skill, tool, work run ou
    # artifact aquele gasto veio.
    #
    # Sem isso, a SPEC-062 §26 (unit economics) não tem de onde tirar número, e
    # o preço do produto seria adivinhado. Medir é o que produz o preço.
    #
    # Por que AQUI e não em cada lugar que chama LLM: este callback é o
    # gargalo único — ele é injetado em toda instância de chat model do
    # sistema. Um escritor num gargalo é um escritor; cinco escritores
    # espalhados são cinco lugares para esquecer.
    #
    # O ledger legado continua intacto. Isto é um segundo registro do mesmo
    # fato, não uma substituição — trocar de ledger com o produto no ar é
    # como trocar o pneu andando.

    _PROVEDOR_POR_PREFIXO = (
        ("claude", "anthropic"),
        ("gpt", "openai"),
        ("o1", "openai"),
        ("o3", "openai"),
        ("gemini", "google"),
        ("llama", "meta"),
        ("mistral", "mistral"),
        ("deepseek", "deepseek"),
        ("grok", "xai"),
    )

    @classmethod
    def _provedor_do_modelo(cls, modelo: str) -> Optional[str]:
        nome = (modelo or "").lower()
        for prefixo, provedor in cls._PROVEDOR_POR_PREFIXO:
            if prefixo in nome:
                return provedor
        return None

    def _registrar_no_ledger(
        self,
        *,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_creation_tokens: int,
        cache_read_tokens: int,
        cached_tokens: int,
        run_id: UUID,
        parent_run_id: Optional[UUID],
    ) -> None:
        # `usage_events.company_id` é NOT NULL. Consumo sem empresa (tarefa
        # global, script) não vira linha órfã: fica de fora e o ledger legado
        # continua tendo o registro técnico.
        if not self.company_id:
            return

        try:
            from ...services.work.usage import UsageService as LedgerDaSpec062

            custo = self.usage_service.calculate_cost(
                model, input_tokens, output_tokens,
                cache_creation_tokens, cache_read_tokens, cached_tokens,
            )

            LedgerDaSpec062(self.usage_service.supabase).registrar(
                company_id=str(self.company_id),
                source=self.service_type,
                # `run_id` é único por chamada de LLM e vem do LangChain. Isso
                # torna o registro exatamente-uma-vez de graça: se o callback
                # disparar duas vezes, o índice único
                # `(company_id, idempotency_key)` recusa a segunda e o
                # `UsageService` trata isso como sucesso.
                idempotency_key=f"llm:{run_id}",
                correlation_id=str(parent_run_id or run_id),
                provider=self._provedor_do_modelo(model),
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                units=int(input_tokens or 0) + int(output_tokens or 0),
                unit_kind="token",
                provider_cost_usd=float(custo or 0),
            )
        except Exception as exc:  # noqa: BLE001
            # Perder uma medição é ruim; derrubar a resposta do corretor por
            # causa dela é pior. O ledger legado já guardou o fato.
            logger.warning(
                "[CostCallback] usage_event não registrado: %s", type(exc).__name__
            )

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """
        Called when LLM call fails. Log the error but don't track cost.
        """
        logger.warning(f"[CostCallback] LLM error for {self.service_type}: {error}")
