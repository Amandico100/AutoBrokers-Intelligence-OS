"""
LLM Factory — a ÚNICA fábrica de modelos de conversa (CLAUDE.md §5).

SPEC-116 F2 (U5): a fábrica deixou de escolher modelo. Quem escolhe é o Model
Router (`app/factories/model_policy.py:resolver`), por PAPEL; a fábrica recebe
um `ModeloResolvido` e traduz as CAPACIDADES do catálogo (`llm_pricing`) em
kwargs do provedor — o jeito que CADA provedor exige:

  Anthropic   esforço → `reasoning_effort` (langchain-anthropic ≥ 1.7.3 manda
              `output_config.effort`); `sampling_ok=false` → nenhum
              temperature/top_p/top_k sai (Claude 5 e Opus 4.7/4.8 dão 400);
              `tool_choice_forcado_ok=false` → nunca `tool_choice` any/tool nem
              `thinking` disabled/enabled (Opus 5.5 dá 400).
  OpenAI      `api_surface=responses` → Responses API, `reasoning.effort`,
              `store=False` (o estado é o NOSSO checkpointer), sem temperature
              quando `sampling_ok=false`; `chat_completions` segue como antes.
  Google      esforço → `thinking_level`.
  compatível  provedor OpenAI-compatível (xAI, DeepSeek, Z.ai, MiMo…) entra
              por UMA linha do catálogo (`base_url` + `api_key_env`) e o
              raciocínio (`reasoning_content`) VAI e VOLTA entre rodadas.

⛔ Nada cai no mini. Provedor, modelo ou superfície sem adaptador →
`ModeloNaoResolvido`. O antigo `else → gpt-4o-mini` e o `or "gpt-4o"` morreram.
"""
import logging
import os
from typing import Any, Dict, List, Optional

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from app.core.callbacks.cost_callback import CostCallbackHandler
from app.core.config import settings
from app.core.relogio_do_modelo import (
    RelogioDoModeloCallback,
    kwargs_de_relogio,
)
from app.factories import model_policy as MP
from app.factories.model_policy import ModeloNaoResolvido, ModeloResolvido, papel_do_agente

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

#: 🔴 O PAPEL DE QUEM AINDA NÃO DECLARA PAPEL (SPEC-116 F2 → F3).
#:
#: Os chamadores de plataforma (despacho, destilador, atlas, marca, conselho…)
#: passam um `agent_data` montado na hora — `{"llm_provider", "llm_model"}`, SEM
#: a chave `agent_role`. Tratá-los como `chat_principal` (o que `papel_do_agente("")`
#: devolve) trocaria o modelo DELES pela rota do chat: 📊 o despacho de produção
#: roda `claude-opus-5` (EVIDENCIAS/02) e passaria a rodar `claude-sonnet-5` sem
#: ninguém pedir. Então: sem `agent_role` no dicionário = papel SEM rota → o
#: resolvedor aceita o modelo do chamador SÓ se ele estiver no catálogo com
#: lifecycle usável (senão, ERRO). A F3 troca cada um pelo `papel=` dele.
PAPEL_SEM_PAPEL = "sem_papel"

#: Provedores cujo cliente é o `ChatOpenAI` NATIVO (sem base_url própria).
_SUPERFICIES_OPENAI = ("chat_completions", "responses")


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


def _provedores_conhecidos() -> set:
    try:
        do_catalogo = {str(l.get("provider") or "") for l in MP.catalogo().values()}
    except Exception:  # noqa: BLE001 — o conjunto fixo do resolvedor ainda vale
        do_catalogo = set()
    return set(MP.PROVEDORES_CONHECIDOS) | {p for p in do_catalogo if p}


# ===========================================================================
# ADAPTADORES — subclasses finas, DENTRO da fábrica (nada paralelo)
# ===========================================================================
def _sem_parametros_proibidos(payload: dict, capacidades: dict) -> dict:
    """Tira do payload o que o catálogo diz que o modelo RECUSA (400).

    ⚠️ Roda sobre o payload FINAL — é a última porta antes da rede. A
    langchain-anthropic 1.7.3 move `temperature` para `extra_body` quando acha
    que o modelo não aceita; a API recebe do mesmo jeito (📊 EVIDENCIAS/03 §2).
    """
    if capacidades.get("sampling_ok") is False:
        for chave in ("temperature", "top_p", "top_k"):
            payload.pop(chave, None)
            if isinstance(payload.get("extra_body"), dict):
                payload["extra_body"].pop(chave, None)
        if payload.get("extra_body") == {}:
            payload.pop("extra_body")
    return payload


class ChatAnthropicGovernado(ChatAnthropic):
    """`ChatAnthropic` que obedece às capacidades do catálogo NO PAYLOAD.

    Opus 5.5 (whats-new-opus-5-5): `tool_choice` any/tool → 400 e `thinking`
    disabled/enabled → 400. O app não força hoje (📊 `grep -rn tool_choice app`
    = 0), mas `with_structured_output()` e `bind_tools(tool_choice=…)` forçam
    — e o próximo que usar não vai ler esta docstring. A porta é o payload.
    """

    capacidades_do_catalogo: Dict[str, Any] = {}

    def _get_request_payload(self, input_, *, stop=None, **kwargs):  # noqa: ANN001
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)
        caps = self.capacidades_do_catalogo or {}
        if caps.get("tool_choice_forcado_ok") is False:
            escolha = payload.get("tool_choice")
            if isinstance(escolha, dict) and escolha.get("type") in ("any", "tool"):
                novo = {"type": "auto"}
                if "disable_parallel_tool_use" in escolha:
                    novo["disable_parallel_tool_use"] = escolha["disable_parallel_tool_use"]
                logger.warning("[Factory] %s recusa tool_choice forçado (%s) — enviado 'auto'",
                               payload.get("model"), escolha.get("type"))
                payload["tool_choice"] = novo
            pensamento = payload.get("thinking")
            if isinstance(pensamento, dict) and pensamento.get("type") in ("disabled", "enabled"):
                payload.pop("thinking")
        return _sem_parametros_proibidos(payload, caps)


class ChatOpenAIGovernado(ChatOpenAI):
    """`ChatOpenAI` que tira do payload o que o catálogo diz que o modelo recusa."""

    capacidades_do_catalogo: Dict[str, Any] = {}

    def _get_request_payload(self, input_, *, stop=None, **kwargs):  # noqa: ANN001
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)
        return _sem_parametros_proibidos(payload, self.capacidades_do_catalogo or {})


#: O campo em que os provedores compatíveis devolvem o raciocínio
#: (DeepSeek, Kimi, MiMo, GLM — EVIDENCIAS/05 §3). DeepSeek dá 400 se ele não volta.
CAMPO_DE_RACIOCINIO_PADRAO = "reasoning_content"


class ChatOpenAICompativel(ChatOpenAIGovernado):
    """Provedor OpenAI-compatível com o RACIOCÍNIO indo e voltando.

    📊 langchain#40219 (aberta, 05/09/2026): `_get_request_payload` descarta
    `reasoning_content` → 400 em tool call no DeepSeek. Aqui: (1) na RESPOSTA,
    o campo vai para `additional_kwargs[campo]` (streaming e não-streaming);
    (2) no PEDIDO, cada mensagem de assistente que o trouxe o devolve.
    """

    campo_de_raciocinio: str = CAMPO_DE_RACIOCINIO_PADRAO

    def _create_chat_result(self, response, generation_info=None):  # noqa: ANN001
        resultado = super()._create_chat_result(response, generation_info)
        try:
            dados = response if isinstance(response, dict) else response.model_dump()
            for escolha, geracao in zip(dados.get("choices") or [], resultado.generations):
                valor = (escolha.get("message") or {}).get(self.campo_de_raciocinio)
                if valor:
                    geracao.message.additional_kwargs[self.campo_de_raciocinio] = valor
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Factory] raciocínio não extraído da resposta: %s", type(exc).__name__)
        return resultado

    def _convert_chunk_to_generation_chunk(self, chunk, default_chunk_class, base_generation_info):  # noqa: ANN001
        gen = super()._convert_chunk_to_generation_chunk(chunk, default_chunk_class, base_generation_info)
        try:
            escolhas = chunk.get("choices") or []
            delta = (escolhas[0] or {}).get("delta") or {} if escolhas else {}
            valor = delta.get(self.campo_de_raciocinio)
            if gen is not None and valor:
                gen.message.additional_kwargs[self.campo_de_raciocinio] = valor
        except Exception as exc:  # noqa: BLE001
            logger.debug("[Factory] raciocínio do chunk não lido: %s", type(exc).__name__)
        return gen

    def _get_request_payload(self, input_, *, stop=None, **kwargs):  # noqa: ANN001
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)
        try:
            mensagens = self._convert_input(input_).to_messages()
            saida = payload.get("messages") or []
            if len(mensagens) == len(saida):
                for original, convertida in zip(mensagens, saida):
                    valor = (getattr(original, "additional_kwargs", None) or {}).get(
                        self.campo_de_raciocinio)
                    if valor and convertida.get("role") == "assistant":
                        convertida[self.campo_de_raciocinio] = valor
            else:  # nunca adivinhar o par: melhor um 400 visível que raciocínio no lugar errado
                logger.warning("[Factory] %d mensagens → %d no payload: raciocínio não reenviado",
                               len(mensagens), len(saida))
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Factory] raciocínio não reenviado: %s", type(exc).__name__)
        return payload


class LLMFactory:
    # ------------------------------------------------------------------
    # O papel e o modelo — perguntados ao Model Router, nunca decididos aqui
    # ------------------------------------------------------------------
    @staticmethod
    def resolver_para(company_config: Optional[Dict[str, Any]], agent_data: Optional[Dict[str, Any]],
                      *, papel: Optional[str] = None,
                      classe_de_dado: Optional[str] = None) -> ModeloResolvido:
        """O `ModeloResolvido` que a fábrica vai construir para este chamador.

        Papel: o explícito; senão o do agente (`agent_role` presente no
        dicionário — agente do banco); senão `sem_papel` (chamador de
        plataforma, ver `PAPEL_SEM_PAPEL`). ⛔ Provedor declarado que ninguém
        conhece é ERRO — não vira openai, nem a rota.
        """
        agente = dict(agent_data or {})
        corretora = dict(company_config or {})
        declarado = agente.get("llm_provider") or corretora.get("llm_provider")
        if declarado and str(declarado).strip().lower() not in _provedores_conhecidos():
            raise ModeloNaoResolvido(f"provedor desconhecido {declarado!r}")
        if papel is None:
            papel = papel_do_agente(agente.get("agent_role")) if "agent_role" in agente \
                else PAPEL_SEM_PAPEL
        return MP.resolver(papel, agente=agente or None, corretora=corretora or None,
                           classe_de_dado=classe_de_dado)

    @staticmethod
    def chave_para(resolvido: ModeloResolvido, api_key: Optional[str] = None,
                   provedor_da_chave: Optional[str] = None) -> str:
        """A chave do provedor RESOLVIDO.

        A chave que o chamador trouxe só vale se foi escolhida para o MESMO
        provedor (a rota pode ter mudado o provedor do agente). Senão, a do
        catálogo (`api_key_env`), lida do ambiente. ⛔ Nunca exibida.
        """
        if api_key and (provedor_da_chave is None or provedor_da_chave == resolvido.provider):
            return api_key
        from app.core.utils import get_api_key_for_provider

        return get_api_key_for_provider(resolvido.provider, resolvido.model)

    # ------------------------------------------------------------------
    @staticmethod
    def create_llm(
        company_config: Dict[str, Any],
        agent_data: Optional[Dict[str, Any]],
        api_key: Optional[str] = None,
        company_id: str = None,
        agent_id: str = None,
        service_type: Optional[str] = None,
        *,
        papel: Optional[str] = None,
        modelo_resolvido: Optional[ModeloResolvido] = None,
        classe_de_dado: Optional[str] = None,
        reserva_usada: bool = False,
    ):
        """Constrói o modelo do PAPEL.

        `papel=` — o trabalho (a F3 passa: "memoria", "visao", "dispatch"…).
        `modelo_resolvido=` — quem já resolveu (o grafo, a bancada, a reserva).
        Sem nenhum dos dois: papel do agente (`agent_role`) ou `sem_papel`.
        ⛔ Levanta `ModeloNaoResolvido` — nunca devolve um modelo por omissão.
        """
        company_config = company_config or {}
        resolvido = modelo_resolvido or LLMFactory.resolver_para(
            company_config, agent_data, papel=papel, classe_de_dado=classe_de_dado)

        source = agent_data if agent_data else company_config
        provedor_da_chave = source.get("llm_provider") or company_config.get("llm_provider")
        chave = LLMFactory.chave_para(resolvido, api_key, provedor_da_chave)
        if not chave:
            raise ValueError(f"CRITICAL: API Key missing for agent {agent_id or 'Unknown'}.")

        temp_val = source.get("llm_temperature")
        if temp_val is None:
            temp_val = company_config.get("llm_temperature", 0.7)
        temperature = float(temp_val)

        max_tokens = source.get("llm_max_tokens") or company_config.get("llm_max_tokens", 8192)
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

        logger.info("[Factory] papel=%s → %s/%s esforço=%s (%s, rota v%s)",
                    resolvido.papel, resolvido.provider, resolvido.model, resolvido.effort,
                    resolvido.origem, resolvido.versao_da_rota)

        # O callback de custo é SEMPRE anexado (📊 28/07/2026: plataforma sem
        # `company_id` ficava invisível no ledger). `service_type` distingue
        # consumo de corretora ("chat") do da plataforma; SPEC-098 R12: quem sabe
        # o que está fazendo passa `service_type`.
        # SPEC-116 U7: o ledger grava QUEM pediu o quê e o que RESPONDEU —
        # papel · pedido · resolvido · real · esforço · rota · reserva.
        callbacks = [
            CostCallbackHandler(
                service_type=service_type or ("chat" if company_id else "plataforma"),
                company_id=company_id,
                agent_id=agent_id,
                model_name=resolvido.model,
                details=LLMFactory.detalhes_do_ledger(
                    resolvido, modelo_pedido=(source or {}).get("llm_model"),
                    reserva_usada=reserva_usada),
                provider=resolvido.provider,
            ),
            # 🔴 QUEM DESCOBRE QUE O PROVEDOR CAIU (SPEC-EXTRA-001.8 §7.4): o
            # sensor mora no gargalo. ⚠️ O Cost continua sendo `callbacks[0]`:
            # há guarda que lê por índice (`tests/test_098_builder_a_unit.py:325`).
            RelogioDoModeloCallback(resolvido.provider),
        ]
        return LLMFactory.construir(resolvido, chave, max_tokens=max_tokens,
                                    temperature=temperature, callbacks=callbacks)

    @staticmethod
    def criar_de_resolvido(resolvido: ModeloResolvido, *, callbacks: Optional[List[Any]] = None,
                           api_key: Optional[str] = None, company_id: Optional[str] = None,
                           agent_id: Optional[str] = None, service_type: Optional[str] = None,
                           max_tokens: int = 8192, temperature: float = 0.7):
        """Para a BANCADA e para quem já tem o `ModeloResolvido` na mão.

        ⛔ O ledger continua: os callbacks do chamador ENTRAM junto dos dois de
        sempre (custo + relógio), nunca no lugar deles.
        """
        llm = LLMFactory.create_llm(
            {}, {"llm_max_tokens": max_tokens, "llm_temperature": temperature},
            api_key=api_key, company_id=company_id, agent_id=agent_id,
            service_type=service_type, modelo_resolvido=resolvido)
        if callbacks:
            llm.callbacks = list(llm.callbacks or []) + list(callbacks)
        return llm

    @staticmethod
    def detalhes_do_ledger(resolvido: ModeloResolvido, *, modelo_pedido: Optional[str],
                           reserva_usada: bool) -> Dict[str, Any]:
        return {
            "papel": resolvido.papel,
            "modelo_pedido": modelo_pedido,
            "modelo_resolvido": resolvido.model,
            "provedor_resolvido": resolvido.provider,
            "esforco": resolvido.effort,
            "origem_da_rota": resolvido.origem,
            "versao_da_rota": resolvido.versao_da_rota,
            "reserva_usada": bool(reserva_usada),
        }

    # ------------------------------------------------------------------
    # capacidades → kwargs
    # ------------------------------------------------------------------
    @staticmethod
    def construir(resolvido: ModeloResolvido, api_key: str, *, max_tokens, temperature: float,
                  callbacks: list):
        prov, sup = resolvido.provider, resolvido.api_surface
        if prov == "anthropic" and sup == "messages":
            return LLMFactory._create_anthropic(resolvido, api_key, max_tokens, temperature, callbacks)
        if prov == "openai" and sup in _SUPERFICIES_OPENAI:
            return LLMFactory._create_openai(resolvido, api_key, max_tokens, temperature, callbacks)
        if prov == "google" and sup == "generate_content":
            return LLMFactory._create_google(resolvido, api_key, max_tokens, temperature, callbacks)
        if prov == "openrouter":
            return LLMFactory._create_openrouter(resolvido, api_key, max_tokens, temperature, callbacks)
        if sup == "openai_compat":
            return LLMFactory._create_openai_compat(resolvido, api_key, max_tokens, temperature,
                                                    callbacks)
        # ⛔ O `else → gpt-4o-mini` morreu aqui (SPEC-116 G1).
        raise ModeloNaoResolvido(
            f"papel {resolvido.papel!r}: sem adaptador de conversa para "
            f"{prov!r}/{sup!r} ({resolvido.model!r})")

    @staticmethod
    def _esforco(resolvido: ModeloResolvido) -> Optional[str]:
        e = resolvido.effort
        return e if e and e in MP.NIVEIS_DE_ESFORCO else None

    @staticmethod
    def _create_openai(resolvido: ModeloResolvido, api_key, max_tokens, temperature, callbacks):
        caps = resolvido.capacidades or {}
        esforco = LLMFactory._esforco(resolvido)
        llm_params: Dict[str, Any] = {
            "model": resolvido.model,
            "max_tokens": max_tokens,
            "openai_api_key": api_key,
            "callbacks": callbacks,
            "streaming": True,
            "capacidades_do_catalogo": caps,
        }
        if caps.get("sampling_ok") is not False:
            llm_params["temperature"] = temperature

        if resolvido.api_surface == "responses":
            # GPT-6: tools + raciocínio SÓ na Responses (📊 doc gpt-6-sol;
            # langchain#40346). `store=False`: nada fica no servidor alheio — o
            # estado é o checkpointer. Sem `store`, o raciocínio só volta pelo
            # `encrypted_content`, por isso o `include`.
            llm_params["use_responses_api"] = True
            llm_params["store"] = False
            if esforco:
                llm_params["reasoning"] = {"effort": esforco}
                llm_params["include"] = ["reasoning.encrypted_content"]
            # Responses conta o uso sozinha — sem `stream_options.include_usage`.
        else:
            if esforco and caps.get("reasoning_param") in ("reasoning.effort", "reasoning_effort"):
                llm_params["reasoning_effort"] = esforco
            llm_params["model_kwargs"] = {"stream_options": {"include_usage": True}}

        # 🔴 O RELÓGIO (SPEC-EXTRA-001.8 §7.1) — campo `request_timeout`, alias `timeout`.
        llm_params.update(kwargs_de_relogio())
        return ChatOpenAIGovernado(**llm_params)

    @staticmethod
    def _create_anthropic(resolvido: ModeloResolvido, api_key, max_tokens, temperature, callbacks):
        caps = resolvido.capacidades or {}
        params: Dict[str, Any] = {
            "model": resolvido.model,
            "max_tokens": max_tokens,
            "anthropic_api_key": api_key,
            "callbacks": callbacks,
            "streaming": True,
            "capacidades_do_catalogo": caps,
            # ⚠️ o header beta `prompt-caching-2024-07-31` saiu: o cache é GA e o
            # `cache_control` do bloco estático (`nodes.py`) é o que liga.
        }
        # Claude 5 e Opus 4.7/4.8 REJEITAM sampling (400) — decidido pelo
        # CATÁLOGO, não por prefixo de nome (EVIDENCIAS/03 F5).
        if caps.get("sampling_ok") is not False:
            params["temperature"] = temperature
        esforco = LLMFactory._esforco(resolvido)
        if esforco and caps.get("reasoning_param") == "output_config.effort":
            params["reasoning_effort"] = esforco
        # 🔴 O RELÓGIO — Anthropic. Campo `default_request_timeout`, alias `timeout`.
        params.update(kwargs_de_relogio())
        return ChatAnthropicGovernado(**params)

    @staticmethod
    def _create_google(resolvido: ModeloResolvido, api_key, max_tokens, temperature, callbacks):
        # 🔴 O RELÓGIO — Google. ⚠️ `max_retries` importa mais aqui: o SDK repete
        # `Unauthenticated` (📊 `langchain_google_genai/chat_models.py:176-205`).
        caps = resolvido.capacidades or {}
        params: Dict[str, Any] = {
            "model": resolvido.model,
            "max_output_tokens": max_tokens,
            "google_api_key": api_key,
            "callbacks": callbacks,
            "streaming": True,
        }
        if caps.get("sampling_ok") is not False:
            params["temperature"] = temperature
        esforco = LLMFactory._esforco(resolvido)
        if esforco and caps.get("reasoning_param") == "thinking_level":
            params["thinking_level"] = esforco
        params.update(kwargs_de_relogio())
        return ChatGoogleGenerativeAI(**params)

    @staticmethod
    def _create_openrouter(resolvido: ModeloResolvido, api_key, max_tokens, temperature, callbacks):
        """OpenRouter: `ChatOpenAI` com a base_url dele. Ids "provedor/modelo"."""
        caps = resolvido.capacidades or {}
        llm_params: Dict[str, Any] = {
            "model": resolvido.model,
            "max_tokens": max_tokens,
            "openai_api_key": api_key,
            "base_url": resolvido.base_url or settings.OPENROUTER_BASE_URL,
            "callbacks": callbacks,
            "streaming": True,
            "capacidades_do_catalogo": caps,
            "default_headers": {
                "HTTP-Referer": settings.FRONTEND_URL,
                "X-Title": "AutoBrokers",
            },
            "model_kwargs": {"stream_options": {"include_usage": True}},
        }
        if caps.get("sampling_ok") is not False:
            llm_params["temperature"] = temperature
        # 🔴 O RELÓGIO — OpenRouter soma a espera DELE à do destino; o teto é único.
        llm_params.update(kwargs_de_relogio())
        return ChatOpenAIGovernado(**llm_params)

    @staticmethod
    def _create_openai_compat(resolvido: ModeloResolvido, api_key, max_tokens, temperature,
                              callbacks):
        """Provedor OpenAI-compatível NOVO = uma linha do catálogo (base_url + api_key_env)."""
        if not resolvido.base_url:
            raise ModeloNaoResolvido(
                f"{resolvido.provider}/{resolvido.model}: linha do catálogo sem base_url")
        caps = resolvido.capacidades or {}
        esforco = LLMFactory._esforco(resolvido)
        llm_params: Dict[str, Any] = {
            "model": resolvido.model,
            "max_tokens": max_tokens,
            "openai_api_key": api_key,
            "base_url": resolvido.base_url,
            "callbacks": callbacks,
            "streaming": True,
            "stream_usage": True,
            "capacidades_do_catalogo": caps,
            "campo_de_raciocinio": caps.get("campo_de_raciocinio") or CAMPO_DE_RACIOCINIO_PADRAO,
        }
        if caps.get("sampling_ok") is not False:
            llm_params["temperature"] = temperature
        param = caps.get("reasoning_param")
        if esforco and param in ("reasoning_effort", "reasoning.effort"):
            llm_params["reasoning_effort"] = esforco
        elif esforco and param == "thinking":  # MiMo: none | high
            llm_params["extra_body"] = {
                "thinking": {"type": "disabled" if esforco == "none" else "enabled"}}
        llm_params.update(kwargs_de_relogio())
        return ChatOpenAICompativel(**llm_params)
