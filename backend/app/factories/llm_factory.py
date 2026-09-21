"""
LLM Factory to decouple LLM creation from Graph logic.
"""
import logging
import os
from typing import Any, Dict, Optional

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from app.core.callbacks.cost_callback import CostCallbackHandler
from app.core.config import settings
from app.core.relogio_do_modelo import (
    RelogioDoModeloCallback,
    kwargs_de_relogio,
    provedor_normalizado,
)
from app.factories.model_policy import resolve_chat_model

logger = logging.getLogger(__name__)

#: 🔴 O PISO DE SAÍDA DA CONVERSA — a resposta do corretor não cabe em 1200.
#:
#: 📊 09/09/2026, Resulta Seguros (`agents.llm_max_tokens` do agente core,
#: `20845996`): **1200**. Em `token_usage_logs` desde 08/09, **10 de 95**
#: chamadas bateram `output_tokens = 1200` EXATO — e as mesmas 10 respostas
#: estão gravadas em `messages` terminando no meio de uma palavra
#: ("...com valores individuais e fran"). O corretor digitava "continue".
#:
#: Uma apólice lida item a item — coberturas, limites, franquias — não cabe em
#: 1200 tokens, e o campo do banco foi preenchido uma vez, há muito tempo, para
#: outro modelo e outro custo. ⚠️ O piso NÃO engessa: quem configurou MAIS que
#: o piso continua mandando; ele só impede que um número velho corte a resposta
#: pela metade. E vale só para quem CONVERSA (core e atendimento) — auxiliar e
#: subagente, que devolvem um campo ou um JSON curto, mantêm o que está gravado.
PISO_DE_SAIDA_DA_CONVERSA = int(os.getenv("PISO_DE_SAIDA_DA_CONVERSA", "8192"))

#: Papéis que falam com gente e por isso têm piso.
#:
#: 🔴 `insured_external` ENTROU EM 14/09/2026 (SPEC-EXTRA-001.1, BLOCO E).
#: É o papel de quem fala com o SEGURADO (GLOSSARIO). Ele nasceu FORA desta
#: tupla e ninguém percebeu, porque:
#:   📊 medido em 13 e 14/09/2026 — `select agent_role, count(*) from agents
#:      group by 1` devolve 4 `core` + 4 `attendance` e **ZERO**
#:      `insured_external`. Não há vítima medida: nenhum segurado foi cortado
#:      por isto.
#: ⚠️ Classificação honesta (protocolo §2): ESSENCIAL LATENTE, não blocker. O
#: defeito acontece no dia em que a primeira corretora instalar um agente
#: desse papel — ele nasceria com o teto do banco (📊 hoje 1200 ou 2000) e a
#: resposta ao segurado sairia cortada, como saíram 10 das 95 do corretor em
#: 10/09. O guarda que impede a palavra de sumir de novo é
#: `test_quem_fala_com_o_segurado_tambem_tem_piso.py` (M-E2).
#:
#: ⛔ O que continua FORA, de propósito: `auxiliary` e `subagent`. Eles
#: devolvem um campo ou um JSON curto; elevar o teto deles só aumentaria custo
#: sem mudar um byte do que chega a alguém.
PAPEIS_QUE_CONVERSAM = ("", "core", "attendance", "insured_external")


def piso_de_saida(agent_role, max_tokens):
    """Devolve o teto de saída efetivo — nunca abaixo do piso, para quem conversa."""
    papel = str(agent_role or "").strip().lower()
    if papel not in PAPEIS_QUE_CONVERSAM:
        return max_tokens
    try:
        atual = int(max_tokens)
    except (TypeError, ValueError):
        return PISO_DE_SAIDA_DA_CONVERSA
    return max(atual, PISO_DE_SAIDA_DA_CONVERSA)


class LLMFactory:
    @staticmethod
    def create_llm(
        company_config: Dict[str, Any],
        agent_data: Optional[Dict[str, Any]],
        api_key: str,
        company_id: str = None,
        agent_id: str = None,
        service_type: Optional[str] = None,
    ):
        """
        Create LLM with hierarchy: Agent Config > Company Config.
        """
        if not api_key:
            raise ValueError(
                f"CRITICAL: API Key missing for agent {agent_id or 'Unknown'}."
            )

        source = agent_data if agent_data else company_config

        provider = source.get("llm_provider") or company_config.get(
            "llm_provider", "openai"
        )
        model = (source.get("llm_model") or company_config.get("llm_model")) or "gpt-4o"

        # SPEC-013 FB-1: promove o Chat Principal (Core) a um modelo mais forte (temporário,
        # CORE_CHAT_MODEL). Não engessa; Even/Auxiliares mantêm o modelo configurado.
        model = resolve_chat_model((agent_data or {}).get("agent_role"), model)

        temp_val = source.get("llm_temperature")
        if temp_val is None:
            temp_val = company_config.get("llm_temperature", 0.7)
        temperature = float(temp_val)

        max_tokens = source.get("llm_max_tokens") or company_config.get(
            "llm_max_tokens", 8192
        )
        # 🔴 Um número velho no banco não corta a resposta pela metade.
        max_tokens_gravado = max_tokens
        max_tokens = piso_de_saida((agent_data or {}).get("agent_role"), max_tokens)
        if max_tokens != max_tokens_gravado:
            logger.info(
                "[Factory] teto de saida elevado ao piso da conversa: %s -> %s "
                "(papel=%s, agente=%s)",
                max_tokens_gravado, max_tokens,
                (agent_data or {}).get("agent_role"), agent_id or "-",
            )

        reasoning_effort = source.get("reasoning_effort") or "medium"

        # Logic for reasoning models (fixed temperature)
        use_temperature = True
        if model.startswith("o1") or model.startswith("o3") or model.startswith("gpt-5"):
            use_temperature = False

        logger.info(
            f"[Factory] Creating LLM: provider={provider}, model={model}, "
            f"temp={temperature if use_temperature else 'fixed'}"
        )

        # O callback de custo é SEMPRE anexado.
        #
        # Antes ele só entrava quando havia `company_id`, e isso abria um buraco
        # grande: todo trabalho de PLATAFORMA — o Tecelão resolvendo rotas
        # ambíguas com Opus 5, o Destilador do Espelho, o Cartógrafo — roda sem
        # corretora dona e ficava **invisível no ledger**.
        #
        # Medido em 28/07/2026: `token_usage_logs` com ZERO chamadas em três
        # horas, enquanto o console da Anthropic mostrava US$ 0,54 gastos. O
        # dinheiro saía e o sistema não sabia dizer em quê.
        #
        # `service_type` distingue: consumo de corretora é "chat"; o que a
        # plataforma gasta por conta própria é "plataforma", e some do custo por
        # corretora sem sumir do total.
        #
        # SPEC-098 R12 — "custo com nome": um trabalho que NÃO é conversa não
        # pode entrar no ledger como se fosse. A leitura do site da corretora
        # tem `company_id` (é dela o gasto) e cairia em "chat" pela regra antiga,
        # somando ao custo de atendimento uma linha que nunca foi atendimento.
        # Quem sabe o que está fazendo passa `service_type`; os 11 chamadores de
        # hoje não passam nada e continuam decididos pela mesma regra.
        callbacks = [
            CostCallbackHandler(
                service_type=service_type or ("chat" if company_id else "plataforma"),
                company_id=company_id,
                agent_id=agent_id,
                model_name=model,
            ),
            # 🔴 QUEM DESCOBRE QUE O PROVEDOR CAIU (SPEC-EXTRA-001.8 §7.4).
            # Aqui é o único lugar por onde TODA chamada de modelo do sistema
            # passa — os 15 chamadores de `create_llm`, o nó `agent`, os
            # subagentes e o streaming. Um sensor num gargalo é um sensor;
            # quinze espalhados são quinze lugares para esquecer.
            # ⛔ O callback ALIMENTA; quem BLOQUEIA é quem pergunta
            # `provedor_disponivel()` ANTES de consumir a mensagem — quando este
            # roda, a chamada já saiu.
            # ⚠️ O Cost continua sendo `callbacks[0]`: há guarda que lê por
            # índice (`tests/test_098_builder_a_unit.py:325`).
            RelogioDoModeloCallback(provedor_normalizado(provider)),
        ]

        if provider == "openai":
            return LLMFactory._create_openai(
                model, api_key, max_tokens, temperature, use_temperature,
                reasoning_effort, callbacks
            )
        elif provider == "anthropic":
            return LLMFactory._create_anthropic(
                model, api_key, max_tokens, temperature, callbacks
            )
        elif provider == "google":
            return LLMFactory._create_google(
                model, api_key, max_tokens, temperature, callbacks
            )
        elif provider == "openrouter":
            return LLMFactory._create_openrouter(
                model, api_key, max_tokens, temperature, callbacks
            )
        else:
            logger.warning(f"Unknown provider '{provider}', using OpenAI fallback")
            return LLMFactory._create_openai(
                "gpt-4o-mini", api_key, max_tokens, temperature, True, "medium", callbacks
            )

    @staticmethod
    def _create_openai(model, api_key, max_tokens, temperature, use_temp, reasoning_effort, callbacks):
        model_kwargs = {}
        if model.startswith("o1") or model.startswith("o3"):
            model_kwargs["reasoning_effort"] = reasoning_effort

        llm_params = {
            "model": model,
            "max_tokens": max_tokens,
            "openai_api_key": api_key,
            "callbacks": callbacks,
            "streaming": True,
        }

        if use_temp:
            llm_params["temperature"] = temperature

        if model_kwargs:
            llm_params["model_kwargs"] = model_kwargs

        # Force usage metadata
        if "model_kwargs" not in llm_params:
            llm_params["model_kwargs"] = {}
        llm_params["model_kwargs"]["stream_options"] = {"include_usage": True}

        # 🔴 O RELÓGIO (SPEC-EXTRA-001.8 §7.1) — OpenAI. Campo `request_timeout`,
        # alias `timeout`; é ele que o guarda lê no objeto.
        llm_params.update(kwargs_de_relogio())

        return ChatOpenAI(**llm_params)

    @staticmethod
    def _anthropic_supports_temperature(model: str) -> bool:
        """A família Claude 5 (Sonnet/Opus/Haiku 5, Mythos, Fable) REJEITA o
        parâmetro `temperature` (API 400: 'temperature is deprecated for this
        model'). Modelos 3.x/4.x ainda aceitam."""
        m = (model or "").lower()
        blocked = ("claude-sonnet-5", "claude-opus-5", "claude-haiku-5", "claude-mythos", "claude-fable")
        return not any(m.startswith(p) for p in blocked)

    @staticmethod
    def _create_anthropic(model, api_key, max_tokens, temperature, callbacks):
        params = {
            "model": model,
            "max_tokens": max_tokens,
            "anthropic_api_key": api_key,
            "callbacks": callbacks,
            "streaming": True,
            "model_kwargs": {
                "extra_headers": {
                    "anthropic-beta": "prompt-caching-2024-07-31"
                }
            },
        }
        # Só envia temperature quando o modelo aceita (Claude 5 a rejeita → 400).
        if LLMFactory._anthropic_supports_temperature(model):
            params["temperature"] = temperature
        # 🔴 O RELÓGIO — Anthropic. Campo `default_request_timeout`, alias
        # `timeout`. `max_retries` já vinha 2 por default do SDK; agora o número
        # é NOSSO e muda por env junto com os outros três.
        params.update(kwargs_de_relogio())
        return ChatAnthropic(**params)

    @staticmethod
    def _create_google(model, api_key, max_tokens, temperature, callbacks):
        # 🔴 O RELÓGIO — Google. Campo `timeout`, alias `request_timeout`.
        # ⚠️ Aqui o `max_retries` importa MAIS que nos outros: o default do SDK é
        # 6 e o retry dele repete `GoogleAPIError`, do qual `Unauthenticated`
        # herda (📊 `langchain_google_genai/chat_models.py:176-205`) — isto é,
        # ele repete credencial recusada. Baixar para 2 corta o estrago; a
        # classificação errada do SDK fica registrada como pendência.
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            max_output_tokens=max_tokens,
            google_api_key=api_key,
            callbacks=callbacks,
            streaming=True,
            **kwargs_de_relogio(),
        )

    @staticmethod
    def _create_openrouter(model, api_key, max_tokens, temperature, callbacks):
        """
        Cria LLM via OpenRouter usando ChatOpenAI com base_url customizada.
        OpenRouter é 100% compatível com a API OpenAI.
        Model IDs usam formato "provider/model" (ex: "meta-llama/llama-3.1-405b").
        """
        llm_params = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "openai_api_key": api_key,
            "base_url": settings.OPENROUTER_BASE_URL,
            "callbacks": callbacks,
            "streaming": True,
            "default_headers": {
                "HTTP-Referer": settings.FRONTEND_URL,
                "X-Title": "AutoBrokers",
            },
            "model_kwargs": {
                "stream_options": {"include_usage": True},
            },
        }

        # 🔴 O RELÓGIO — OpenRouter. É `ChatOpenAI` com outra `base_url`, então o
        # campo lido é o mesmo `request_timeout`. ⚠️ O roteador acrescenta a
        # espera DELE por cima da do provedor de destino; o teto único é o que
        # impede essa soma de ficar sem fim.
        llm_params.update(kwargs_de_relogio())

        return ChatOpenAI(**llm_params)
