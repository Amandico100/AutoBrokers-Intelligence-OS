"""
Nós do grafo LangGraph.
Cada função representa um nó que processa o estado.

🔥 VERSÃO FINAL CORRIGIDA:
- Limpeza de Reasoning no histórico (Evita erro 400)
- Debug de Tokens (Loga usage_metadata)
- Janela Deslizante (Performance)
- Injeção de Agent ID nas Tools
"""

import asyncio
import contextvars
import json
import logging
import re
import time
import unicodedata
from typing import Any, Dict, Literal, Optional, Tuple

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from .state import AgentState
from .utils import extract_text_from_content, sanitize_ai_message
from .context import build_task_context

logger = logging.getLogger(__name__)


# ===========================================================================
# SPEC-116 U6 — o TURNO sabe se já executou ferramenta
# ===========================================================================
#
# 🔴 A regra (D-116-07): o turno só pode ser REFEITO — pela reserva da rota ou
# pelo retry do serviço — ANTES da 1ª ferramenta. Depois dela, retém e sinaliza.
#
# ⚠️ "Ferramenta com efeito": o Tool Gateway marca `side_effect_class` em
# `tool_definitions` (📊 `services/skills/gateway.py:49`), mas o objeto que o
# `tool_node` executa é a tool do LangChain, sem essa marca, e o nó não lê o
# banco por ferramenta. 📊 `grep -rn "side_effect" app/agents/tools` → 0. Não
# existe marcação utilizável no ponto de execução → CONSERVADOR: TODA
# ferramenta conta como ferramenta com efeito. (Lista paralela seria o motor
# paralelo do CLAUDE.md §5.)
class MarcadorDoTurno:
    """Quantas ferramentas o turno JÁ COMEÇOU a executar (anotado ANTES de rodar)."""

    __slots__ = ("tools_iniciadas",)

    def __init__(self) -> None:
        self.tools_iniciadas = 0


#: O marcador do turno corrente. É um OBJETO mutável dentro da ContextVar de
#: propósito: o LangGraph roda cada nó numa tarefa filha com CÓPIA do contexto —
#: um `.set()` lá dentro não voltaria; a mutação do mesmo objeto volta.
_MARCADOR_DO_TURNO: contextvars.ContextVar = contextvars.ContextVar(
    "marcador_do_turno", default=None)


def abrir_marcador_do_turno() -> Tuple[MarcadorDoTurno, Any]:
    marcador = MarcadorDoTurno()
    return marcador, _MARCADOR_DO_TURNO.set(marcador)


def fechar_marcador_do_turno(ficha: Any) -> None:
    try:
        _MARCADOR_DO_TURNO.reset(ficha)
    except (ValueError, RuntimeError):  # outra tarefa/contexto: só esquece
        pass


def _anotar_tool_iniciada() -> None:
    marcador = _MARCADOR_DO_TURNO.get()
    if marcador is not None:
        marcador.tools_iniciadas += 1


def turno_ja_executou_tool(state: dict) -> bool:
    """O turno corrente já passou por alguma ferramenta? (conservador: qualquer uma)

    Três testemunhas, qualquer uma basta: `tools_used` do turno (📊 zerado a cada
    invocação em `graph._build_initial_state`), uma ToolMessage DEPOIS da última
    mensagem humana, ou o marcador do turno (anotado ANTES de executar — pega
    também a ferramenta que começou e caiu no meio).
    """
    if state.get("tools_used"):
        return True
    for msg in reversed(state.get("messages") or []):
        if isinstance(msg, HumanMessage) or getattr(msg, "type", None) == "human":
            break
        if isinstance(msg, ToolMessage) or getattr(msg, "type", None) == "tool":
            return True
    marcador = _MARCADOR_DO_TURNO.get()
    return bool(marcador is not None and marcador.tools_iniciadas)


# ===========================================================================
# SPEC-116 U6a — o histórico devolve o RACIOCÍNIO a quem o produziu
# ===========================================================================
def _origem_da_mensagem(msg) -> Tuple[Optional[str], Optional[str]]:
    """(provedor, modelo) que produziram esta AIMessage, pelo `response_metadata`."""
    meta = getattr(msg, "response_metadata", None) or {}
    modelo = meta.get("model_name") or meta.get("model")
    # ⚠️ O CATÁLOGO vence o `model_provider` do LangChain: todo cliente
    # OpenAI-compatível (DeepSeek, xAI…) é um `ChatOpenAI` e se declara "openai".
    provedor = None
    if modelo:
        try:
            from app.core.callbacks.cost_callback import provedor_pelo_catalogo

            provedor = provedor_pelo_catalogo(modelo)
        except Exception:  # noqa: BLE001
            provedor = None
    return provedor or meta.get("model_provider"), modelo


def _mesmo_modelo(real: Optional[str], atual: Optional[str]) -> bool:
    if not real or not atual:
        return False
    return real == atual or real.startswith(atual) or atual.startswith(real)


def mensagem_do_assistente_para(msg, provedor_atual: Optional[str],
                                modelo_atual: Optional[str]):
    """A AIMessage como vai ao modelo DESTE turno.

    🔴 Mesmo provedor e mesmo modelo → a mensagem INTEIRA volta: blocos de
    `thinking` com assinatura (Anthropic), itens de raciocínio (Responses),
    `reasoning_content` (compatíveis). Opus 5.5/Fable/DeepSeek dão 400 sem eles
    num laço de ferramentas; os outros degradam (EVIDENCIAS/03 F9, /05 §3).
    ⚠️ Provedor ou modelo DIFERENTE (a rota trocou; a reserva entrou) → sanitiza,
    como era: o raciocínio é preso ao modelo que o gerou e o outro o recusa.
    Origem desconhecida (mensagem antiga no checkpoint) → sanitiza.
    """
    if provedor_atual and modelo_atual:
        provedor, modelo = _origem_da_mensagem(msg)
        if provedor == provedor_atual and _mesmo_modelo(modelo, modelo_atual):
            return msg
    return sanitize_ai_message(msg)


def _historico_para_outro_provedor(mensagens: list) -> list:
    """O mesmo histórico, sem nada que prenda ao provedor anterior (a reserva).

    Blocos de sistema com `cache_control` viram texto; assistentes perdem o
    raciocínio (é do outro modelo).
    """
    saida = []
    for m in mensagens:
        if isinstance(m, SystemMessage) and isinstance(m.content, list):
            texto = "\n\n".join(b.get("text", "") if isinstance(b, dict) else str(b)
                                for b in m.content)
            saida.append(SystemMessage(content=texto))
        elif isinstance(m, AIMessage):
            saida.append(sanitize_ai_message(m))
        else:
            saida.append(m)
    return saida


#: O rótulo que separa a instrução do FISCAL da fala do cliente.
ROTULO_DA_CORRECAO_INTERNA = "[INSTRUÇÃO INTERNA DO SISTEMA — não é mensagem do cliente]"


def mensagens_com_correcao(llm_messages: list, instrucao: str) -> list:
    """As mensagens do turno + a instrução de REESCRITA dos fiscais.

    🔴 SPEC-116 U8 (F3a) — defeito medido pela F2: os fiscais (pergunta
    repetida, tamanho) punham um `SystemMessage` no FIM da conversa. A
    langchain-anthropic recusa ("Received multiple non-consecutive system
    messages") ANTES de chamar a API — em Claude a regeneração NUNCA rodou, e o
    erro era engolido: a resposta que repergunta/estoura saía assim mesmo.

    A instrução vai como a ÚLTIMA mensagem do lado do usuário (rotulada como
    interna): válida em todo provedor — a Anthropic funde turnos de usuário
    consecutivos (inclusive depois de um `tool_result`) — e o prefixo do prompt
    fica intacto, então o cache do bloco estático continua valendo.
    """
    return list(llm_messages) + [
        HumanMessage(content=f"{ROTULO_DA_CORRECAO_INTERNA}\n{instrucao}")]


async def _invocar_o_modelo(llm_with_tools, llm_messages: list, config, state: dict, *,
                            llm_reserva=None, tools_do_turno=None, rota: Optional[dict] = None):
    """A chamada ao modelo do turno, com a RESERVA da rota (SPEC-116 U6c, D-116-07).

    Devolve `(resposta, llm_usado, mensagens_usadas)` — quem regenera depois
    (os fiscais) fala com o MESMO modelo que respondeu.

      · breaker do primário ABERTO e nenhuma ferramenta no turno → reserva;
      · 429 / 5xx / timeout / conexão ANTES da 1ª ferramenta → reserva;
      · DEPOIS da 1ª ferramenta → o erro sobe (a mensagem fica retida por quem
        chamou, como hoje). ⛔ Nunca refaz um turno que já teve ferramenta.
      · sem reserva declarada na rota → exatamente o comportamento de antes.
    """
    tem_reserva = llm_reserva is not None and bool(rota)
    if tem_reserva and not turno_ja_executou_tool(state):
        try:
            from app.core.relogio_do_modelo import estado_do_breaker

            estado = (await estado_do_breaker(rota.get("provedor"))).get("estado")
        except Exception:  # noqa: BLE001 — fail-open: sem breaker, tenta o primário
            estado = None
        if estado == "aberto":
            return await _pela_reserva(llm_reserva, tools_do_turno, llm_messages, config,
                                       rota, "breaker_aberto")
    try:
        resposta = await llm_with_tools.ainvoke(llm_messages, config=config)
        return resposta, llm_with_tools, llm_messages
    except Exception as exc:
        if not tem_reserva:
            raise
        from app.core.relogio_do_modelo import motivo_de_reserva

        motivo = motivo_de_reserva(exc)
        if motivo is None:
            raise
        if turno_ja_executou_tool(state):
            logger.error(
                "[Agent Node] ⛔ %s (%s) no provedor %s DEPOIS de ferramenta no turno — "
                "a reserva NÃO refaz; o erro sobe e a mensagem fica retida",
                type(exc).__name__, motivo, rota.get("provedor"))
            raise
        return await _pela_reserva(llm_reserva, tools_do_turno, llm_messages, config,
                                   rota, motivo)


async def _pela_reserva(llm_reserva, tools_do_turno, llm_messages, config, rota, motivo):
    ligado = llm_reserva.bind_tools(tools_do_turno) if tools_do_turno else llm_reserva
    mensagens = _historico_para_outro_provedor(llm_messages)
    cfg = dict(config or {})
    cfg["metadata"] = {**(cfg.get("metadata") or {}), "motivo_reserva": motivo}
    logger.warning("[Agent Node] 🔁 RESERVA da rota: %s → %s (motivo=%s)",
                   rota.get("provedor"), rota.get("provedor_reserva"), motivo)
    resposta = await ligado.ainvoke(mensagens, config=cfg)
    return resposta, ligado, mensagens

from app.core.constants import AGENT_CONTEXT_WINDOW_SIZE


from app.agents.honestidade_do_handoff import (
    FALHA_DO_HANDOFF,
    _TOOLS_DE_HANDOFF,
    guardar_a_verdade_do_handoff,
)

# As async-only de antes da declaracao `exige_async`. Nao viram uma lista
# nova: sao as que ainda nao declararam, e a lista nao cresce mais.
_TOOLS_SEMPRE_ASYNC = ("delegate_to_subagent", "infocap_policy_lookup",
                       "insurer_dispatch", "portal_action")

_INFOCAP_GENERIC_ERROR_MARKERS = (
    "erro tecnico",
    "erro técnico",
    "nao consegui obter",
    "não consegui obter",
    "tente novamente mais tarde",
    "suporte tecnico",
    "suporte técnico",
    "envie o pdf",
    "enviar pdf",
)


_POLICY_DETAIL_TERMS = (
    "apolice",
    "apólice",
    "detalhe",
    "cobertura",
    "coberturas",
    "assistencia",
    "assistência",
    "franquia",
    "limite",
    "lmi",
    "parcela",
    "parcelas",
    "premio",
    "prêmio",
    "exclusao",
    "exclusão",
)


# SPEC-016 E1: termos extras de detalhe válidos apenas no contexto v2 (perguntas
# de assistência do corretor como "ela cobre eletricista?").
_POLICY_DETAIL_TERMS_V2 = (
    "cobre",
    "coberto",
    "coberta",
    "eletricista",
    "chaveiro",
    "encanador",
    "hidraulica",
    "hidráulica",
)

# Referência anafórica à apólice em contexto ("ela tem assistência?").
_POLICY_ANAPHORA_RE = re.compile(
    r"\b(ela|nela|dela|essa|dessa|nessa|esta|desta|nesta|aquela|daquela)\b", re.IGNORECASE
)

# Pergunta CONCEITUAL (definição/explicação) não deve virar consulta operacional
# forçada — o Core responde com conhecimento geral (SPEC-016 G-A5).
_CONCEPTUAL_QUESTION_RE = re.compile(
    r"^\s*(o\s*que\s*(é|e|significa)|oq\s|como\s+funciona|explique|explica|defin|qual\s+a\s+diferen)",
    re.IGNORECASE,
)

# CPF/CNPJ explícito na pergunta = novo lookup por documento; o lock de contexto
# não pode disparar (o final do CPF não é número de apólice — SPEC-016.1 D8).
_DOCUMENT_IN_TEXT_RE = re.compile(
    r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b|\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b|\b\d{11}\b|\b\d{14}\b"
)


def _policy_intelligence_v2() -> bool:
    try:
        from app.core.feature_flags import policy_intelligence_v2_enabled
    except Exception:  # noqa: BLE001 — fallback direto ao ambiente
        import os

        return str(os.getenv("POLICY_INTELLIGENCE_V2", "")).strip().lower() in ("1", "true", "yes", "on")
    return policy_intelligence_v2_enabled()


def _has_policy_detail_term(lowered: str) -> bool:
    if any(term in lowered for term in _POLICY_DETAIL_TERMS):
        return True
    if _policy_intelligence_v2() and any(term in lowered for term in _POLICY_DETAIL_TERMS_V2):
        return True
    return False


def _extract_context_policy_number(question: str, context: Optional[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(context, dict):
        return None
    text = str(question or "")
    lowered = text.lower()
    if not _has_policy_detail_term(lowered):
        return None
    candidates = [str(item or "").strip() for item in context.get("policy_numbers") or [] if str(item or "").strip()]
    for number in sorted(candidates, key=len, reverse=True):
        if number and number in text:
            return number
    match = re.search(r"\b[A-Za-z]?\d[A-Za-z0-9-]{4,}\b", text)
    if match:
        return match.group(0)
    if _policy_intelligence_v2() and not _CONCEPTUAL_QUESTION_RE.search(text):
        # E1: sem número no texto, o contexto resolve a anáfora de forma segura.
        # Perguntas conceituais ("o que é franquia?") ficam com o LLM (G-A5).
        selected = str(context.get("selected_policy_number") or "").strip()
        if selected:
            return selected
        if len(candidates) == 1:
            return candidates[0]
    return None


#: prefixo do id da chamada que o nó FORÇA (ver `agent_node`) — é por ele que o
#: turno sabe que a consulta forçada já aconteceu.
_ID_DA_CONSULTA_FORCADA = "infocap_policy_context_"


def _consulta_forcada_ja_feita_no_turno(mensagens: list) -> bool:
    """Desde a última mensagem do usuário, o nó já forçou `infocap_policy_lookup`?"""
    for msg in reversed(mensagens or []):
        if isinstance(msg, HumanMessage) or getattr(msg, "type", None) == "human":
            return False
        for tc in (getattr(msg, "tool_calls", None) or []):
            tc_id = tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", None)
            if str(tc_id or "").startswith(_ID_DA_CONSULTA_FORCADA):
                return True
    return False


def _policy_context_tool_args(question: str, context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(context, dict):
        return None
    if _DOCUMENT_IN_TEXT_RE.search(str(question or "")):
        # D8: CPF/CNPJ na pergunta → a LLM chama a tool com o documento novo;
        # o contexto antigo não pode sequestrar a consulta.
        return None
    identity: Dict[str, Any] = {}
    if context.get("document"):
        identity["document"] = context.get("document")
    elif context.get("name"):
        identity["name"] = context.get("name")

    # ═══════════════════════════════════════════════════════════════════════
    # 🔴 SPEC-117 F3.5 — SEM IDENTIDADE CRUA, A TRAVA VAI PELO NÚMERO HUMANO
    # ═══════════════════════════════════════════════════════════════════════
    #
    # Acima havia `else: return None`: sem `document` nem `name` CRUS a trava de
    # anáfora não existia. 📊 No atendimento pelo WhatsApp o `data` nunca traz
    # identidade crua (`infocap_connector._canonical_customer_identity`,
    # `unmasked=False`), então esta função nunca travou nada no canal que fala
    # com o SEGURADO — *"e a franquia dela?"* ia ao modelo sem consulta canônica.
    #
    # A consulta forçada passa a poder ir só pelo NÚMERO HUMANO da apólice
    # selecionada, que a própria tool aceita (`InfocapLookupInput.policy_number`).
    # ⚠️ E o GATILHO não mudou: quem decide se há anáfora de apólice continua
    # sendo `_extract_context_policy_number` (termo de detalhe + anáfora + não
    # conceitual + `POLICY_INTELLIGENCE_V2`). Sem esse gatilho, TODA mensagem do
    # atendimento forçaria uma consulta — o oposto do G6 da SPEC-117.
    # ⛔ Nada de argumento novo na tool, e ⛔ nada de `policy_ref`/locator cru: a
    # `AIMessage` com os `tool_calls` FICA no histórico e volta ao modelo no turno
    # seguinte — mandar locator técnico por ali seria vazá-lo ao modelo.
    #
    # 🔴 E A TRAVA DE SEGURANÇA CONTINUA, SÓ MUDOU DE FORMA: "há cliente?" deixou
    # de ser "há CPF/nome CRUS aqui" e passou a ser "este contexto NASCEU de um
    # cliente identificado" — o que o `cliente_ref` (pseudônimo HMAC, presente em
    # TODO contexto que a porta de `policy_context` deixa nascer) atesta sem
    # carregar dado pessoal. Um dicionário sem nenhum dos dois não é PolicyContext
    # e não força consulta nenhuma.
    if not identity and not str(context.get("cliente_ref") or "").strip():
        return None

    policy_number = _extract_context_policy_number(question, context)

    if policy_number:
        return {"policy_number": policy_number, "user_query": str(question or ""), **identity}

    if _policy_intelligence_v2():
        # E1 (G-A2): 2+ apólices no contexto + anáfora sem número → força a
        # LISTAGEM canônica (o contrato ambiguous_policy pede a escolha ao
        # corretor). Nunca escolhe silenciosamente.
        lowered = str(question or "").lower()
        candidates = [str(item or "").strip() for item in context.get("policy_numbers") or [] if str(item or "").strip()]
        if (
            # 🔴 SPEC-117 F3.5: a LISTAGEM continua exigindo identidade. Sem ela
            # (papel mascarado, 2+ apólices, nenhuma selecionada) a consulta iria
            # à fonte com `user_query` e mais nada — pedir dado de contrato sem
            # dizer de quem. ⚠️ Fica registrado como PENDÊNCIA da SPEC-117: o
            # caso "2+ apólices + anáfora + papel mascarado" segue SEM trava, e
            # não travar é melhor que consultar sem identidade.
            identity
            and len(candidates) > 1
            and _has_policy_detail_term(lowered)
            and _POLICY_ANAPHORA_RE.search(lowered)
            and not _CONCEPTUAL_QUESTION_RE.search(lowered)
        ):
            return {"user_query": str(question or ""), **identity}
    return None


def _papel_do_agente(state: Dict[str, Any]) -> str:
    """O papel com que a ferramenta do turno foi montada.

    ⚠️ É a MESMA régua de `graph.py:473` (`agent_role=str(_agent_role or "core")`)
    — e ela decide se o `data` traz identidade CRUA (`infocap_tool._unmasked`:
    `agent_role in ("", "core")`). Duas réguas para o mesmo papel divergem no
    dia em que uma muda, e a divergência aqui é "o contexto carrega CPF ou não".
    """
    return str((state.get("agent_data") or {}).get("agent_role") or "core")


def _safe_infocap_policy_context(
    data: Dict[str, Any],
    *,
    company_id: Optional[str] = None,
    papel: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """ADAPTADOR FINO de `policy_context.construir_policy_context` (SPEC-117 F2.1).

    🔴 **Nenhuma regra mora aqui.** Esta função tinha a PORTA do contexto da
    apólice, e a porta estava quebrada: ela exigia `client_document` ou
    `client_name` CRUS, que no papel do segurado (`attendance`) o conector nunca
    devolve (📊 `nodes.py:423-425` em 26/09/2026, HEAD `79c9e80`). Resultado:
    `None` no WhatsApp, e toda regra pendurada no contexto morta em silêncio.
    A autoridade passou a ser `app/services/policy_context.py`, e o que sobra
    aqui é só resolver `company_id` e `papel` — 📊 as duas coisas que o `data`
    não carrega. ⛔ Não recriar aqui, nem em nenhum outro lugar, as chaves
    legadas (`policy_numbers`, `selected_policy_*`, `source`): quem as monta é
    `policy_context._derivar_chaves_legadas`, e só ele (CLAUDE.md §5).

    🔴 **Sem `company_id`, NÃO nasce contexto** (CLAUDE.md §7). O padrão `None`
    existe para os chamadores antigos que não passam tenant; ele devolve `None`,
    nunca um contexto com tenant adivinhado. E o padrão de `papel` é
    `attendance` — o papel MENOS privilegiado, o que não copia identidade crua:
    errar para o lado de não vazar.
    """
    from app.services.policy_context import construir_policy_context

    return construir_policy_context(
        data,
        company_id=str(company_id or ""),
        papel=str(papel if papel is not None else "attendance"),
    )


def _merge_infocap_policy_context(
    prev: Optional[Dict[str, Any]], new: Optional[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """SPEC-016.1 D6, agora sobre identidade OPACA — e a regra mora num lugar só.

    Uma consulta falha do MESMO cliente não pode apagar a apólice selecionada na
    conversa; cliente novo substitui o contexto inteiro; corretora diferente
    nunca mistura (CLAUDE.md §7). ⛔ A regra é de `policy_context.fundir`
    (SPEC-117 F2.2) — aqui não fica cópia nenhuma dela.

    ⚠️ O que MUDOU de verdade: "é o mesmo cliente?" deixou de ser comparação de
    CPF/nome e passou a ser o `cliente_ref` (HMAC de `company_id:codfil:codigo`,
    decisão D3). Sem `cliente_ref` a resposta é "não sei" — e não se herda
    apólice de quem não se sabe se é a mesma pessoa.
    """
    from app.services.policy_context import fundir

    return fundir(prev, new)


#: 🔴 A família de ramo que o PORTAL atende (SPEC-117 F3.2). O portal ligado ao
#: `portal_action` é o de VIDROS/LANTERNAS, que só existe na linha de automóvel
#: (📊 `portal_tool.PortalActionInput.policy_number`: *"Numero da apolice AUTO
#: escolhida"*). ⛔ Qualquer outra família e o número NÃO é injetado: mandar o
#: portal de vidros abrir pedido contra uma apólice residencial não trava — sai
#: da corretora como pedido válido, contra o contrato errado (CLAUDE.md §9.5).
FAMILIA_DO_PORTAL = "auto"


def _familia_do_ramo(ramo: Any) -> str:
    """A família (`auto`/`resi`/`cond`/…) de um ramo qualquer, pela régua única.

    ⛔ Não é uma segunda tabela de ramo: é `policy_data_provider.familia_de_ramo`.
    `""` quando não se sabe — e "não sei" nunca é "não é".
    """
    try:
        from app.providers.policy_data_provider import familia_de_ramo

        return str(familia_de_ramo(ramo) or "")
    except Exception:  # noqa: BLE001
        return ""


def _chave_da_seguradora(seguradora: Any) -> str:
    """A chave canônica da seguradora — pela régua que já existe.

    ⛔ Delega a `attendance_ficha.chave_da_seguradora`, que delega a
    `corridor_playbooks.normalize_insurer_key`. 📊 O corpus da bancada usa
    `"allianz"` minúsculo e o conector devolve `"ALLIANZ"`: sem a normalização,
    a comparação modelo × sistema acusaria divergência em toda chamada.
    """
    try:
        from app.services.attendance_ficha import chave_da_seguradora

        return chave_da_seguradora(seguradora)
    except Exception:  # noqa: BLE001
        return str(seguradora or "").strip().lower()


async def _contexto_da_apolice_do_turno(state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """O PolicyContext deste turno: o ESTADO manda, a FICHA é a RETOMADA.

    🔴 SPEC-117 G8. O checkpointer de fallback é um `MemorySaver`
    (📊 `graph.py:50`): ele mora na memória do processo e **some no reinício**.
    Sem esta leitura, o segurado que volta depois de um deploy perde a apólice
    que o produto já tinha encontrado — e o ramo oficial, a seguradora e o
    número que iriam ao acionamento voltam a ser o palpite do modelo.

    ⚠️ O SELECT só acontece quando o checkpoint NÃO tem o contexto. Um SELECT por
    turno em todo atendimento seria custo sem retorno, e a ficha já é lida uma
    vez por turno na montagem do prompt (`graph.py:1649`).
    🔴 E o tenant é conferido na volta: contexto gravado sob outra corretora é
    descartado, nunca usado (CLAUDE.md §7).
    """
    do_estado = state.get("infocap_policy_context")
    if isinstance(do_estado, dict) and do_estado.get("apolices"):
        return do_estado

    company_id = str(state.get("company_id") or "")
    session_id = str(state.get("session_id") or "")
    if not (company_id and session_id):
        return do_estado if isinstance(do_estado, dict) else None
    try:
        from app.core.database import get_supabase_client
        from app.services.attendance_ficha import carregar, contexto_da_apolice

        ficha = await carregar(get_supabase_client().client, company_id, session_id)
        da_ficha = contexto_da_apolice(ficha=ficha)
        if isinstance(da_ficha, dict) and str(da_ficha.get("company_id") or "") == company_id:
            logger.info("[APOLICE] contexto retomado da ficha durável (empresa=%s)",
                        company_id)
            return da_ficha
    except Exception as exc:  # noqa: BLE001 — a retomada nunca derruba o turno
        logger.warning("[APOLICE] contexto não relido da ficha (%s)", type(exc).__name__)
    return do_estado if isinstance(do_estado, dict) else None


async def _apolice_do_caso_do_turno(state: Dict[str, Any],
                                    memo: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """🔴 A LEITURA ÚNICA da apólice do caso dentro do `tool_node`.

    Delega a `attendance_ficha.apolice_do_caso`, que delega a
    `policy_context.apolice_selecionada`. ⛔ Nenhum consumidor varre `apolices[]`
    nem lê `selected_policy_*` por conta própria (SPEC-117 F3).

    O `memo` é do TURNO: o dispatch, o portal, a consulta e a ficha leem o mesmo
    contexto, resolvido uma vez — inclusive o SELECT da retomada.
    """
    if "apolice" not in memo:
        from app.services.attendance_ficha import apolice_do_caso

        memo["contexto"] = await _contexto_da_apolice_do_turno(state)
        memo["apolice"] = apolice_do_caso(contexto=memo["contexto"])
    return memo["apolice"]


async def _gravar_apolice_do_caso(state: Dict[str, Any],
                                  contexto: Optional[Dict[str, Any]]) -> None:
    """A apólice do caso vai para a ficha DURÁVEL (SPEC-117 F2.3 · decisão D1).

    `conversations.ficha_atendimento` é a coluna `jsonb` que já existe
    (📊 B0.4 da SPEC-117 — **nenhuma migration**). O estado continua sendo o
    espelho; a verdade durável é o Supabase (CLAUDE.md §6).

    ⚠️ Nunca levanta: uma falha aqui custa a retomada deste caso, e deixar a
    exceção subir custaria a resposta ao segurado. É a mesma regra do resto do
    arquivo da ficha.
    """
    company_id = str(state.get("company_id") or "")
    session_id = str(state.get("session_id") or "")
    if not (company_id and session_id) or not isinstance(contexto, dict):
        return
    if str(contexto.get("company_id") or "") != company_id:
        # Contexto de outra corretora não se grava nesta conversa (CLAUDE.md §7).
        logger.error("[APOLICE] contexto de outra corretora NÃO gravado")
        return
    try:
        from app.core.database import get_supabase_client
        from app.services.attendance_ficha import gravar, novidades_da_apolice

        novidades = novidades_da_apolice(contexto)
        if not novidades:
            return
        await gravar(get_supabase_client().client, company_id, session_id, novidades)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[APOLICE] apólice do caso não gravada (%s) — o estado "
                       "deste processo continua com ela", type(exc).__name__)


def _normalize_money_amount(value: Any) -> str:
    """Normaliza 'R$ 45.000,00' / '45.000,00' / 'R$ 45.000' para comparação."""
    text = re.sub(r"[^\d,]", "", str(value or "")).strip(",")
    if text.endswith(",00"):
        text = text[:-3]
    return text.strip(",")


#: A negação, em português de gente. 🔴 O guarda de `assistencia_da_base` usa
#: isto para separar "o plano dele NÃO tem carro reserva" de um texto que
#: menciona carro reserva e não nega nada — o "sim" silencioso de CLAUDE.md
#: §9.5, que não trava e chega ao cliente.
#
# 🔴 18/09/2026 — A NEGAÇÃO PRECISA SER *DO SERVIÇO*, NÃO QUALQUER "SEM".
#
# 📊 A versão anterior era `\bnão\b|\bnenhum\b|\bsem\b|\bfora\b|\bexclu`. A frase
#
#     "Tem carro reserva, sem custo adicional."
#
# atravessava o guarda: `\bsem\b` casa em "sem custo", e o guarda concluía que a
# resposta negava — quando ela AFIRMA o oposto do que a base publicada diz. É o
# "sim" silencioso de CLAUDE.md §9.5 passando pela porta do próprio guarda que
# existe para pegá-lo. Uma negação avulsa ("sem custo", "fora do horário
# comercial", "sem franquia") é qualificação da cobertura, não a recusa dela.
_NEGATIVA_RE = re.compile(
    r"\bn[ãa]o\s+(?:tem|t[êe]m|inclui|inclu[íi]d|cobre|cobert|possui|contempla|"
    r"h[áa]|dispon|oferece|est[áa]\s+(?:inclu|contratad|cobert))|"
    r"\bsem\s+(?:direito|cobertura|o\s+servi[çc]o|esse\s+servi[çc]o|"
    r"este\s+servi[çc]o|assist[êe]ncia)|"
    r"\bn[ãa]o\s+(?:faz|fazem)\s+parte|\bfora\s+d[oa]\s+(?:plano|cobertura|contrato)|"
    r"\bnenhum[ao]?\s+(?:cobertura|assist[êe]ncia|servi[çc]o)|"
    r"\bexclu[íi]d[oa]s?\s+(?:d[oa]|deste|desse)|\bn[ãa]o\s+est[áa]\s+(?:inclu|contratad)",
    re.IGNORECASE,
)


#: 🔴 As tools que MUDAM ALGUMA COISA FORA do produto. Se uma delas rodou
#: depois da consulta de apolice, a resposta do turno e sobre a ACAO, e nenhum
#: rascunho de cobertura pode tomar o lugar dela (RODADA 2, N1 item 4).
#: As réguas que uma AÇÃO posterior consome (RODADA 3, B3).
_REGUAS_DE_COBERTURA = frozenset({"encerrar_com_o_rascunho", "assistencia_da_base"})

_TOOLS_DE_ACAO = frozenset({
    "insurer_dispatch", "portal_action", "request_human_agent",
    "create_routine", "manage_routine",
})


def _normalizar_para_guarda(valor: Any) -> str:
    """Minúsculas sem acento — a MESMA dos dois lados da comparação.

    ⚠️ CLAUDE.md §9.4 (dialeto): comparar "hidráulica" da base com "hidraulica"
    do texto daria zero casamento em silêncio, e o guarda ficaria verde por não
    enxergar nada. Normalizar UM lado só é o mesmo defeito.
    """
    bruto = unicodedata.normalize("NFKD", str(valor or ""))
    return "".join(c for c in bruto if not unicodedata.combining(c)).lower().strip()


#: O fim de frase, para o espelho da negação (FECHO DA RODADA 2).
_FIM_DE_FRASE_RE = re.compile(r"[.!?\n]+")

#: 🔴 RODADA 4 (P4) — A MARCA DE QUE A COBERTURA TEM CONDIÇÃO.
#:
#: 📊 Medido no banco em 19/09/2026, nas 25 linhas marcadas PUBLICAR e ainda em
#: `proposto`: **17 são `condicionado`** e 8 são `sim`. A maioria absoluta do
#: que o produto passa a saber é condicionada — e o juiz mediu que, com a base
#: dizendo `condicionado`, *"Sim! Seu plano tem vidros"* passava INTEIRO: a
#: condição sumia e o segurado ouvia um "sim" liso sobre uma cobertura que só
#: vale *"se contratada a cobertura adicional de Vendaval, Furacão, Ciclone,
#: Tornado e Granizo"*. É o "sim silencioso" do CLAUDE.md §9.5 — na linha que a
#: corretora está publicando hoje.
_CONDICAO_RE = re.compile(
    # 🔴 RODADA 5 (pendência 3) — OS MARCADORES SOLTOS EXIGEM CONSTRUÇÃO.
    #
    # 📊 Medido pelo juiz final: 5 de 8 "sim liso" realistas ESCAPAVAM porque
    # `se`, `caso` e `apenas` apareciam em sentido NÃO condicional —
    # *"é só SE dirigir a uma oficina"*, *"pode SE tranquilizar"*,
    # *"APENAS me confirme o endereço"*, *"CASO queira eu já abro o chamado"*.
    # Um marcador que casa em qualquer frase não guarda nada.
    r"(?<![a-zà-ú])("
    r"se\s+contratad\w*|se\s+(?:o\s+|a\s+)?adicional|se\s+\w+\s+constar|"
    r"caso\s+(?:tenha|tenham|haja|exista|esteja|estejam|possua|conste)\w*|"
    r"caso\s+\w+\s+contratad\w*|"
    # ⚠️ `somente` / `apenas` / `só` passam a exigir o que vem DEPOIS: a
    # preposição que liga à restrição, ou um `se` de condição de verdade.
    # 🔴 O CONTROLE que o juiz fixou vive aqui: *"Tem vidros, somente para o
    # para-brisa."* continua passando, por `somente\s+para`.
    r"(?:somente|apenas|s[óo])\s+(?:se\s+(?:contratad\w*|tiver|houver|"
    r"estiver|constar|for|fosse|o\s|a\s)|para|no|na|em|com|at[ée]|quando|"
    r"mediante|dentro|nos\s+casos)|"
    # E estes ficam NUS, porque não têm outro sentido numa frase de cobertura.
    r"desde\s+que|exceto|salvo|"
    r"com\s+a\s+condi[çc][ãa]o|sob\s+a\s+condi[çc][ãa]o|"
    r"condi[çc][ãa]o|condi[çc][õo]es|mediante|"
    # 🔴 RODADA 5 (pendência 2): STEMS, não formas fixas. 📊 O `(?![a-zà-ú])`
    # final matava TODA flexão — `contratada`, `contratados`, `sujeita`,
    # `dependendo`, `constantes` eram alternativas MORTAS, e
    # *"Tem vidros, sujeito a contratação do adicional."* era ANULADA. É a
    # mesma forma que `_PEDIDO_DE_SERVICO_RE` já usa.
    r"contratad\w*|contrata[çc][ãa]o|constar|constante\w*|depend\w*|sujeit\w*|"
    r"inclu[íi]d[oa]s?\s+n[ao]\s+ap[óo]lice|limitad\w*|at[ée]\s+(?:r\$|\d)"
    r")",
    re.IGNORECASE)


def _afirma_sem_condicao(candidato: str, rotulo: str) -> bool:
    """A frase que nomeia o serviço AFIRMA ele **sem nenhuma marca de condição**?

    🔴 RODADA 4 (P4). A régua é a MESMA do espelho (`_nega_o_servico`): a frase
    que fala do serviço é a que conta. Aqui a pergunta é a inversa — a base
    disse `condicionado`, e o texto final não pode dizer um "sim" liso.

    ⚠️ **A marca tem de estar NA FRASE DO SERVIÇO**, e é isso que evita o falso
    positivo do "se" avulso: *"Tem vidros. Se precisar, é só chamar."* tem um
    "se", mas ele mora na frase seguinte e não qualifica a cobertura.

    ⛔ `False` quando o serviço não é nomeado em frase nenhuma: a omissão já é
    pega pela regra de cima (`rotulo not in candidate` → `rendered`), e repetir
    o veredito aqui só duplicaria a decisão.
    """
    alvo = _normalizar_para_guarda(rotulo)
    if not alvo:
        return False
    for frase in _FIM_DE_FRASE_RE.split(str(candidato or "")):
        if alvo not in _normalizar_para_guarda(frase):
            continue
        if _NEGATIVA_RE.search(frase):
            # A frase NEGA o serviço — quem trata disso é o espelho.
            continue
        if not _CONDICAO_RE.search(frase):
            return True
    return False


def _consumir_regua_apos_acao(contrato: Any, tools_usadas: Any) -> Any:
    """Consome as réguas de cobertura quando uma tool de AÇÃO rodou depois.

    🔴 RODADA 3 (B3) — POR ESTADO, NUNCA POR CHAMADA.
    ==============================================
    📊 O grafo é `agent ⇄ tools` (`graph.py:683-695`): `infocap_policy_lookup` e
    `insurer_dispatch` caem em **invocações diferentes** do `tool_node`. A
    versão anterior olhava uma lista LOCAL da invocação, então na segunda
    passada não havia o que comparar — e o contrato sobrevive no `state`. O
    resultado medido: *"Pronto! Já acionei a assistência, o prestador chega em
    40 minutos."* era TROCADO por *"Tem sim… Quer que eu já solicite?"*, e o
    cliente entendia que nada tinha sido feito.

    O mecanismo é um SNAPSHOT: o contrato guarda, ao nascer, as tools que já
    tinham rodado no turno. Em qualquer ponto posterior — mesma invocação ou a
    seguinte — basta comparar com `tools_used` do estado.

    ⚠️ Comparação por CONTAGEM, não por conjunto: `insurer_dispatch` pode ter
    rodado antes e de novo depois, e um `set` esconderia a segunda.
    """
    if not isinstance(contrato, dict):
        return contrato
    fatos = list(contrato.get("required_facts") or [])
    if not (set(fatos) & _REGUAS_DE_COBERTURA):
        return contrato
    from collections import Counter  # noqa: PLC0415

    antes = Counter(str(t) for t in (contrato.get("tools_ja_usadas") or []))
    agora = Counter(str(t) for t in (tools_usadas or []))
    novas = agora - antes
    if not (set(novas) & _TOOLS_DE_ACAO):
        return contrato
    logger.info("[Contrato] réguas de cobertura consumidas — uma ação rodou "
                "depois da consulta de apólice")
    return dict(contrato,
                required_facts=[f for f in fatos if f not in _REGUAS_DE_COBERTURA])


def _nega_o_servico(candidato: str, rotulo: str) -> bool:
    """A negação está NA FRASE que nomeia o serviço? — **PURA.**

    🔴 📊 `_NEGATIVA_RE` casa "não tem" em *"você não tem parcelas em atraso"*.
    Perguntada a cobertura de guincho com a base dizendo `sim`, a resposta
    *"Tem guincho sim! E você não tem parcelas em atraso."* era trocada inteira
    — o guarda via uma negação que não era sobre o serviço.

    ⛔ Isto vale SÓ para o espelho (`sim`/`condicionado`). A direção `nao` — a
    regra da 001.5, guardada por M-B5 — **fica como está**: lá a pergunta é
    *"este texto nega em ALGUM lugar?"*, e restringi-la à frase do serviço
    trocaria respostas legítimas como *"Carro reserva. Não está incluído no seu
    plano."*, em que a negação mora na frase seguinte. Apertar uma régua que
    protege o segurado, num ponto que nenhuma medição pediu, é o tipo de
    mudança que só se descobre errada em produção.
    """
    alvo = _normalizar_para_guarda(rotulo)
    if not alvo:
        return False
    for frase in _FIM_DE_FRASE_RE.split(str(candidato or "")):
        if alvo in _normalizar_para_guarda(frase) and _NEGATIVA_RE.search(frase):
            return True
    return False


def _guard_infocap_policy_final_response(candidate_text: str, contract: Optional[Dict[str, Any]]) -> str:
    """R1B.2: InfoCap policy answers are operational contracts, not free-form summaries.

    🔴 SPEC-EXTRA-001.5.1 (C2) — ESTA FUNÇÃO CONTINUA SEM SABER O CANAL, E É
    POR ISSO QUE ELA PASSOU A ESTAR CERTA.
    ==========================================================================
    Até 19/09/2026 ela devolvia `rendered_safe_answer` quando a LLM fugia do
    veredito — e `rendered` era SEMPRE o texto do corretor. No WhatsApp, o
    segurado recebia *"No plano **dele**, não… (Condições gerais da HDI, p.
    23.)"*, e o defeito era invisível: o guarda tinha feito o trabalho dele.

    ⚠️ A correção NÃO foi ensinar canal a este guarda. Foi fazer o CONTRATO
    chegar já com o texto do canal certo (`infocap_tool._render_content` →
    `compose_policy_answer_with_meta(client_facing=…)`). Um `if client_facing`
    aqui seria a MESMA regra em dois lugares, e o segundo envelheceria sozinho.

    ⛔ E o que este guarda exige NÃO muda entre canais: `assistencia_da_base`
    (nomear os serviços que a base nomeou) e `_NEGATIVA_RE` (negar quando a base
    nega) valem no WhatsApp exatamente como no chat — "não afirmar o que a base
    nega" não é formatação.
    """
    if not isinstance(contract, dict) or contract.get("provider") != "infocap":
        return candidate_text or ""
    rendered = str(contract.get("rendered_safe_answer") or "").strip()
    if not rendered:
        return candidate_text or ""
    candidate = str(candidate_text or "").strip()
    lower = candidate.lower()
    required = set(contract.get("required_facts") or [])
    result_kind = contract.get("result_kind")

    if not candidate:
        return rendered
    if any(marker in lower for marker in _INFOCAP_GENERIC_ERROR_MARKERS):
        return rendered
    if "encerrar_com_o_rascunho" in required:
        # 🔴 SPEC-EXTRA-001.5.1 · CONSERTO B1 (ii) — UMA condição, channel-blind.
        #
        # O contrato marca este fato quando o veredito é `nao_sabemos_ainda` ou
        # `fonte_indisponivel`: não há linha publicada, ou a consulta falhou.
        # 📊 Medido pelo juiz em 19/09/2026: nesses dois estados o contrato saía
        # com `required_facts=[]`, e um candidato "Sim, tem esse serviço sim"
        # chegava INTEIRO ao segurado — o guarda não tinha o que conferir.
        #
        # ⚠️ Aqui não se compara texto, e é de propósito: qualquer régua ("o
        # candidato diz que vai confirmar?") seria uma régua sobre prosa, e
        # prosa tem infinitas formas de dizer "sim" por acidente. Tudo o que é
        # VERDADE já está em `rendered` — e `rendered` é o texto do canal certo.
        return rendered
    if "policy_options" in required:
        # SPEC-016.1 D7: a LLM pode formatar como quiser, mas TODOS os números
        # humanos das opções precisam aparecer na resposta (nunca omitir opção).
        #
        # 🔴 SPEC-EXTRA-001.1 §7.3 — o guarda NÃO morre, ele passa a guardar a
        # regra certa. `required_facts` só carrega `policy_options` quando a
        # PORTA devolveu ambiguidade legítima (2+ apólices VIGENTES do MESMO
        # ramo). Nos demais casos a lista vem vazia, e o guarda deixa de
        # OBRIGAR a listagem — continua impedindo o modelo de ESCONDER uma
        # opção, que é a razão de ele existir.
        options = contract.get("policy_options") or []
        for option in options[:10]:
            if not isinstance(option, dict):
                continue
            number = str(option.get("policy_number") or option.get("numapo") or "").strip()
            if number and number.lower() not in {"0", "none", "null", "-"} and number not in candidate:
                return rendered
        if not options:
            # 📊 MEDIDO em 14/09/2026 ANTES de tocar nesta linha (protocolo
            # §0.4), porque a precedência do `and`/`or` original mudava o
            # significado conforme quem lesse. O comportamento real era
            # `A and (B or (C and D))`, e as quatro combinações medidas foram:
            #     só "seguradora" ...... ANULA     só "numero" .......... ANULA
            #     nenhum dos dois ...... ANULA     os dois .............. ACEITA
            # Os parênteses abaixo escrevem isso, sem mudar o veredito.
            #
            # 🔴 A linha FICA porque guarda um caso REAL: a fonte devolveu a
            # ambiguidade sem número humano, e `ATTENDANCE_BASE_PROMPT` manda
            # pedir a escolha "pela POSIÇÃO". Sem ela o modelo responde
            # "escolha uma" sem dizer nem a seguradora, e o segurado não tem
            # como escolher.
            cita_seguradora = "seguradora" in lower
            cita_numero = ("numero" in lower) or ("número" in lower)
            if not (cita_seguradora and cita_numero):
                return rendered
    if "coverage_absent" in required:
        absence_markers = (
            "nao retornou", "não retornou", "nao constam", "não constam",
            "sem itens estruturados", "nao veio", "não veio", "nao encontrei",
            "não encontrei", "nao ha itens", "não há itens", "documento oficial",
        )
        if not any(marker in lower for marker in absence_markers):
            return rendered
    allowed_amounts = contract.get("allowed_amounts")
    if isinstance(allowed_amounts, list) and allowed_amounts:
        # SPEC-016.1 D7: anti-invenção — todo valor R$ citado pela LLM precisa
        # existir nos dados retornados pela fonte.
        allowed_norm = {_normalize_money_amount(a) for a in allowed_amounts}
        allowed_norm.discard("")
        for match in re.findall(r"R\$\s*[\d.][\d.,]*", candidate):
            if _normalize_money_amount(match) not in allowed_norm:
                return rendered
    if "document_evidence" in required:
        # SPEC-016.1: a LLM precisa CITAR a fonte documental (nome ou página
        # válida) — mas não precisa repetir todas as páginas do rascunho.
        candidate_norm = lower.replace("página", "pagina")
        rendered_norm = rendered.lower().replace("página", "pagina")
        required_pages = set(re.findall(r"pagina\s+\d+", rendered_norm))
        candidate_pages = set(re.findall(r"pagina\s+\d+", candidate_norm))
        cites_valid_page = bool(candidate_pages & required_pages) if required_pages else bool(candidate_pages)
        cites_document = "documento oficial" in candidate_norm or "apolice oficial" in candidate_norm or "apólice oficial" in lower
        if not cites_valid_page and not cites_document:
            return rendered
        if required_pages and candidate_pages and not candidate_pages.issubset(required_pages):
            return rendered  # página inventada
    if "source_limited" in required and "erro" in lower:
        return rendered
    if "assistencia_da_base" in required:
        # 🔴 SPEC-EXTRA-001.5 §6.4 — O GUARDA MUDOU DE REGRA, NÃO MORREU.
        #
        # Com a base de planos no ar, exigir "eletricista + chaveiro +
        # encanador" de TODA resposta de assistência passou a ser errado: a
        # resposta certa sobre carro reserva numa apólice de AUTO não tem
        # encanador nenhum. O que o guarda passa a exigir é o que a BASE
        # afirmou sobre ESTA apólice — nem mais, nem menos.
        #
        # ⚠️ Quem apagar este bloco "porque a base substituiu a regra" reabre o
        # defeito que ele fechou: a LLM reescrevendo por cima do veredito
        # determinístico e devolvendo ao segurado um "sim" que o contrato dele
        # não dá. Guarda M-B5.
        da_base = contract.get("assistencia_da_base")
        if isinstance(da_base, list) and da_base:
            for item in da_base:
                if not isinstance(item, dict):
                    continue
                rotulo = _normalizar_para_guarda(item.get("rotulo") or item.get("servico"))
                if not rotulo or rotulo not in _normalizar_para_guarda(candidate):
                    return rendered  # omitiu um serviço que a base nomeou
                if str(item.get("coberto")) == "nao" and not _NEGATIVA_RE.search(candidate):
                    # A base disse NÃO e o texto não nega em lugar nenhum: é o
                    # "sim" silencioso de §9.5, que não trava e chega ao cliente.
                    return rendered
                if (str(item.get("coberto")) == "condicionado"
                        and _afirma_sem_condicao(candidate, rotulo)):
                    # 🔴 RODADA 4 (P4) — O "SIM" LISO SOBRE UMA COBERTURA
                    # CONDICIONADA.
                    #
                    # 📊 17 das 25 linhas que entram em produção hoje são
                    # `condicionado`. Com a base dizendo isso, *"Sim! Seu plano
                    # tem vidros, pode acionar."* passava inteiro — e o segurado
                    # acionava uma cobertura que talvez não tenha contratado.
                    # O `rendered` do canal JÁ traz a condição; o que faltava era
                    # impedir a LLM de reescrevê-la para fora.
                    return rendered
                if (str(item.get("coberto")) in ("sim", "condicionado")
                        and _nega_o_servico(candidate, rotulo)):
                    # 🔴 RODADA 2 — O ESPELHO DA REGRA ACIMA, e ele faltava.
                    #
                    # 📊 Medido em 19/09/2026: com a base dizendo `sim` para
                    # guincho, o candidato "Não, seu plano não tem guincho"
                    # PASSAVA — o guarda só olhava a direção `nao`. Com 23 linhas
                    # publicadas isso deixa de ser teórico: é o segurado ouvindo
                    # que não tem direito ao que ele tem.
                    #
                    # 🔴 FECHO DA RODADA 2 — E ELE OLHA A FRASE, NÃO O TEXTO.
                    # 📊 `_NEGATIVA_RE` casa "não tem" em *"você não tem
                    # parcelas em atraso"*: uma resposta CERTA sobre guincho que
                    # trouxesse essa frase ao lado era trocada inteira, à toa.
                    # A negação só conta quando está NA FRASE que nomeia o
                    # serviço — é lá que ela fala dele.
                    return rendered
    if "assistance_policy_applied" in required:
        # SPEC-016 E4b: política de assistência aplicada → a resposta final não
        # pode omitir os serviços padrão garantidos pela política governada.
        #
        # ⚠️ Continua VALENDO — é a regra do FALLBACK (§6.4): quando quem
        # respondeu foi `assistance_policy.py`, e não a base, os três serviços
        # são o que se afirmou, e é o que a resposta tem de citar.
        services_present = (
            "eletricista" in lower
            and "chaveiro" in lower
            and ("hidraulica" in lower or "hidráulica" in lower or "encanador" in lower)
        )
        if not services_present:
            return rendered
    if "identity_mismatch" in required:
        forbidden = ("seguradora", "produto", "cobertura", "parcela", "pdf", "documento oficial")
        if any(term in lower for term in forbidden) or "identidade da apolice" not in lower:
            return rendered
    return candidate


def should_continue_after_tools(state: AgentState) -> Literal["agent", "end"]:
    """Roteia contratos de apólice dentro do grafo Smith existente.

    SPEC-016.1 D7: com a flag v2 ligada, a LLM VOLTA a redigir a resposta final
    (qualidade/formatação de copiloto) e o contrato vira fiscal via output
    guard pós-LLM. Só identity_mismatch continua fail-closed sem LLM.
    Flag desligada: comportamento legado (R1B.2) preservado.
    """
    contract = state.get("policy_response_contract")
    final_response = state.get("final_response")
    if not (isinstance(contract, dict) and contract.get("provider") == "infocap" and final_response):
        return "agent"
    if _policy_intelligence_v2():
        if contract.get("result_kind") == "identity_mismatch":
            logger.info("[Router] InfoCap identity_mismatch fail-closed (sem LLM)")
            return "end"
        return "agent"
    logger.info("[Router] InfoCap policy contract finalized without LLM rewrite")
    return "end"


def sanitize_history(messages: list) -> list:
    """
    Sanitiza o histórico para compatibilidade com todos os providers (OpenAI, Gemini, Anthropic).
    
    Corrige:
    1. ToolMessages órfãs (sem AIMessage com tool_calls correspondente)
    2. AIMessages com tool_calls órfãos (sem ToolMessages correspondentes)
       → Gemini exige que tool_calls sejam imediatamente seguidos por ToolMessages
    3. Mensagens AI consecutivas (Gemini rejeita)
    """
    if not messages:
        return messages

    # === PASSO 1: Coletar todos os tool_call_ids e tool_response_ids ===
    all_tool_call_ids = set()
    all_tool_response_ids = set()

    for msg in messages:
        if isinstance(msg, AIMessage) or (hasattr(msg, "type") and msg.type == "ai"):
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tc_id = tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", None)
                    if tc_id:
                        all_tool_call_ids.add(tc_id)

        elif isinstance(msg, ToolMessage) or (hasattr(msg, "type") and msg.type == "tool"):
            tool_call_id = getattr(msg, "tool_call_id", None)
            if tool_call_id:
                all_tool_response_ids.add(tool_call_id)

    # IDs com par completo (AIMessage + ToolMessage)
    paired_ids = all_tool_call_ids & all_tool_response_ids
    # IDs de tool_calls que NÃO têm ToolMessage correspondente
    orphan_call_ids = all_tool_call_ids - all_tool_response_ids

    # === PASSO 2: Filtrar mensagens ===
    sanitized = []
    for msg in messages:
        if isinstance(msg, AIMessage) or (hasattr(msg, "type") and msg.type == "ai"):
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                # Verificar se TODOS os tool_calls têm ToolMessages correspondentes
                msg_call_ids = set()
                for tc in msg.tool_calls:
                    tc_id = tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", None)
                    if tc_id:
                        msg_call_ids.add(tc_id)

                if msg_call_ids.issubset(paired_ids):
                    # Todos os tool_calls têm respostas — manter intacto
                    sanitized.append(msg)
                else:
                    # Remover tool_calls órfãos — manter apenas o texto
                    text_content = extract_text_from_content(msg.content) if msg.content else ""
                    if text_content.strip():
                        sanitized.append(AIMessage(content=text_content))
                        logger.debug(
                            f"[sanitize_history] AIMessage com tool_calls órfãos convertida para texto"
                        )
                    else:
                        logger.debug(
                            f"[sanitize_history] AIMessage com tool_calls órfãos removida (sem texto)"
                        )
            else:
                sanitized.append(msg)

        elif isinstance(msg, ToolMessage) or (hasattr(msg, "type") and msg.type == "tool"):
            tool_call_id = getattr(msg, "tool_call_id", None)
            if tool_call_id in paired_ids:
                sanitized.append(msg)
            else:
                logger.debug(
                    f"[sanitize_history] ToolMessage órfã removida (tool_call_id={tool_call_id})"
                )

        else:
            sanitized.append(msg)

    # === PASSO 3: Merge de AIMessages consecutivas (Gemini não aceita) ===
    final = []
    for msg in sanitized:
        if (
            final
            and isinstance(msg, AIMessage)
            and isinstance(final[-1], AIMessage)
            and not (hasattr(final[-1], "tool_calls") and final[-1].tool_calls)
            and not (hasattr(msg, "tool_calls") and msg.tool_calls)
        ):
            # Merge texto de AIMessages consecutivas sem tool_calls
            prev_text = extract_text_from_content(final[-1].content)
            curr_text = extract_text_from_content(msg.content)
            merged = f"{prev_text}\n{curr_text}".strip()
            final[-1] = AIMessage(content=merged)
            logger.debug("[sanitize_history] Merged consecutive AIMessages")
        else:
            final.append(msg)

    return final


def build_system_prompt(company_config: dict, rag_context: str = None) -> str:
    """
    Monta o system prompt baseado na config da empresa.
    """
    base_prompt = (
        company_config.get("agent_system_prompt")
        or """
Você é um assistente inteligente e prestativo.
Seja profissional, claro e objetivo nas suas respostas.
Se não souber a resposta, diga que não sabe.
Sempre responda em português brasileiro.
"""
    )

    company_name = company_config.get("company_name", "")
    if company_name:
        base_prompt += f"\n\nVocê está atendendo a empresa: {company_name}."

    base_prompt += """

🔍 FERRAMENTA DISPONÍVEL - BUSCA NA BASE DE CONHECIMENTO:
Você tem acesso à ferramenta 'knowledge_base_search' que busca informações nos documentos da empresa.

QUANDO USAR:
- Sempre que o usuário perguntar sobre a empresa, produtos, serviços, processos, políticas
- Quando o usuário mencionar nomes específicos (produtos, projetos, pessoas, departamentos)
- Quando precisar de informações específicas que podem estar documentadas
- SEMPRE use esta ferramenta ANTES de responder perguntas sobre a empresa

COMO USAR:
- Passe a pergunta do usuário como query
- Exemplo: se o usuário perguntar "O que é Flux Pay?", use knowledge_base_search(query="Flux Pay")
- A ferramenta retorna trechos relevantes dos documentos

IMPORTANTE: Use SEMPRE que possível! Não responda "não sei" sem antes buscar nos documentos.
"""

    if rag_context:
        base_prompt += f"""

=== CONTEXTO DOS DOCUMENTOS DA EMPRESA ===
{rag_context}
=== FIM DO CONTEXTO ===

INSTRUÇÕES IMPORTANTES:
- Use as informações acima para responder às perguntas do usuário
- Se a resposta estiver nos documentos, baseie-se neles
- Se não encontrar nos documentos, responda com seu conhecimento geral
- Seja preciso e cite os documentos quando relevante
"""

    return base_prompt


from langchain_core.runnables import RunnableConfig


#: Papéis que falam com o SEGURADO. O copiloto interno do corretor não tem
#: ficha de atendimento — fiscalizá-lo custaria uma leitura por turno e não
#: protegeria ninguém. Mesma condição de `graph._build_initial_state`.
_PAPEIS_DE_ATENDIMENTO = ("attendance", "insured_external")


def _valor_da_ficha(ficha: dict, slot: str) -> str:
    """O que o cliente respondeu para aquele slot — para dizer ao modelo."""
    from app.services.attendance_ficha import valor_de

    return str(valor_de(((ficha or {}).get("confirmados") or {}).get(slot)) or "")


async def _ficha_do_turno(state: dict) -> dict:
    """A ficha deste atendimento — a que o turno já carregou, ou o banco.

    ⚠️ O `_build_initial_state` já leu a ficha para montar o prompt. Quando ela
    viaja no state, o fiscal não paga uma segunda leitura; quando não viaja,
    ele lê — e uma falha de leitura devolve ficha vazia, que só faz o fiscal
    ficar calado. Nunca derruba o turno.
    """
    pronta = state.get("ficha_atendimento")
    if isinstance(pronta, dict) and pronta:
        return pronta
    try:
        from app.core.database import get_supabase_client
        from app.services.attendance_ficha import carregar, ficha_vazia

        company_id = str(state.get("company_id") or "")
        session_id = str(state.get("session_id") or "")
        if not (company_id and session_id):
            return ficha_vazia()
        cli = get_supabase_client()
        return await carregar(getattr(cli, "client", cli), company_id, session_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[PERGUNTA REPETIDA] ficha indisponível (%s)", type(exc).__name__)
        return {}


def mesma_mensagem_com_texto(original, texto: str):
    """Uma `AIMessage` nova com OUTRO texto — e os MESMOS metadados.

    🔴 **O defeito, achado em 14/09/2026 (J8).** Cada fiscal substituía a
    resposta por `AIMessage(content=...)` cru. Isso **descartava**
    `response_metadata`, `usage_metadata` e o `id` da mensagem original — que
    é de onde saem os tokens cobrados, o modelo que respondeu e a correlação
    do rastro. ⚠️ Um turno regenerado ficava, para a telemetria, como um
    turno sem custo e sem modelo.

    ⛔ Nunca levanta: se a mensagem original não tiver os campos (um dublê de
    teste, por exemplo), sai uma `AIMessage` simples — que é o comportamento
    de antes, nunca pior.
    """
    extras = {}
    for campo in ("response_metadata", "usage_metadata", "additional_kwargs",
                  "id", "name"):
        try:
            valor = getattr(original, campo, None)
        except Exception:  # noqa: BLE001
            valor = None
        if valor:
            extras[campo] = valor
    try:
        return AIMessage(content=texto, **extras)
    except Exception:  # noqa: BLE001
        return AIMessage(content=texto)


async def _resposta_sem_pergunta_repetida(texto: str, state: dict, *, regenerar):
    """O fiscal da pergunta repetida. UMA regeneração — e depois ENVIA.

    SPEC-EXTRA-001.2 §7.3. Terceira instância do mesmo padrão que o produto já
    tem (o fiscal do InfoCap e o da transferência, logo acima): determinístico,
    DEPOIS do modelo, e só reescreve quando a resposta extrapola o que o caso
    autoriza. ⛔ Nenhum motor novo.

    🔴 **Nunca trava a resposta.** Se o modelo insistir, a mensagem SAI assim
    mesmo e o defeito vira linha no feed: travar o segurado para proteger uma
    regra de estilo trocaria um defeito silencioso por um barulhento
    (CLAUDE.md §9.5).

    Devolve `(texto_final, slots_que_persistiram)`.
    """
    from app.services.attendance_ficha import slots_reperguntados

    papel = str((state.get("agent_data") or {}).get("agent_role") or "").lower()
    if papel and papel not in _PAPEIS_DE_ATENDIMENTO:
        return texto, []

    ficha = await _ficha_do_turno(state)
    corredor = str((ficha or {}).get("servico") or "")
    repetidos = slots_reperguntados(texto, ficha, corredor=corredor)
    if not repetidos:
        return texto, []

    logger.warning("[PERGUNTA REPETIDA] a resposta volta a perguntar %s — "
                   "regenerando UMA vez", repetidos)
    novo = ""
    try:
        novo = await regenerar(repetidos, ficha)
    except Exception as exc:  # noqa: BLE001
        logger.error("[PERGUNTA REPETIDA] regeneração falhou (%s) — segue a "
                     "resposta original", type(exc).__name__)

    ainda = slots_reperguntados(novo, ficha, corredor=corredor) if novo else repetidos
    final = novo or texto
    if not ainda:
        return final, []

    # Persistiu: envia, e o feed fica com o registro do defeito.
    try:
        from app.services.activity_log import log_activity
        from app.services.attendance_ficha import rotulo

        company_id = str(state.get("company_id") or "")
        if company_id:
            nomes = ", ".join(rotulo(s) for s in ainda)
            await log_activity(
                company_id, "qualidade",
                "Pergunta repetida na conversa (pergunta_repetida)",
                "A resposta voltou a perguntar o que o cliente já tinha "
                "respondido: %s. Slots: %s. A mensagem foi enviada assim mesmo."
                % (nomes, ", ".join(ainda)))
    except Exception as exc:  # noqa: BLE001
        logger.debug("[PERGUNTA REPETIDA] feed indisponível: %s", type(exc).__name__)
    return final, ainda


async def _registrar_tamanho_no_feed(state: dict, classe: str, unidades: int,
                                     teto: int, texto: str = "") -> None:
    """A linha do feed quando a resposta sai fora da classe. **Nunca levanta.**

    ⚠️ Escrita UMA vez, chamada de dois lugares (J8): quando a reescrita não
    resolveu e quando o turno já tinha gasto a sua única regeneração. Duas
    cópias da mesma frase seriam duas frases, e uma delas envelheceria.
    """
    try:
        from app.services.activity_log import log_activity

        company_id = str(state.get("company_id") or "")
        if not company_id:
            return
        await log_activity(
            company_id, "qualidade",
            "Resposta longa demais na conversa (tamanho_fora_da_classe)",
            "A resposta ficou fora da classe `%s` (%d de no máximo %d; %d "
            "caracteres). A mensagem foi enviada assim mesmo."
            % (classe, unidades, teto, len(str(texto or "").strip())))
    except Exception as exc:  # noqa: BLE001
        logger.debug("[TAMANHO] feed indisponível: %s", type(exc).__name__)


async def _resposta_no_tamanho_da_classe(texto: str, state: dict, *, regenerar,
                                         ja_regenerou: bool = False):
    """O fiscal do TAMANHO. UMA regeneração — e depois ENVIA.

    SPEC-EXTRA-001.2 §8.2. Quarta instância do mesmo padrão dos fiscais acima
    (InfoCap, transferência, pergunta repetida): determinístico, DEPOIS do
    modelo, e só reescreve quando a resposta sai da classe que o caso autoriza.
    ⛔ Nenhum motor novo: a régua é `classe_do_tamanho`, pura, em
    `o_fim_do_atendimento`.

    📊 As regras JÁ estavam escritas em `prompts.py` ("1 a 3 frases", "máximo 4
    itens", a exceção documental) — e o piloto de 10/09 mediu **760
    caracteres** numa conversa comum. Prosa no prompt não conserta prosa do
    modelo.

    ⚠️ **`lista_documental` nunca estoura** (teto 0): meia lista de documentos
    é pior que lista nenhuma. ⛔ E balão não é a régua — `balloons.py` fatia
    para humanizar; o que se mede aqui é UM TURNO.

    🔴 **Nunca trava a resposta.** Persistiu, a mensagem SAI assim mesmo e o
    defeito vira linha no feed (CLAUDE.md §9.5).

    Devolve `(texto_final, classe_que_persistiu_ou_vazio)`.
    """
    from app.services.o_fim_do_atendimento import fora_da_classe, regua_do_tamanho

    papel = str((state.get("agent_data") or {}).get("agent_role") or "").lower()
    if papel and papel not in _PAPEIS_DE_ATENDIMENTO:
        return texto, ""

    estourou, classe, unidades, teto = fora_da_classe(texto or "")
    if not estourou:
        return texto, ""

    # =====================================================================
    # 🔴 UMA REGENERAÇÃO POR TURNO, ENTRE OS DOIS FISCAIS (J8, 14/09/2026)
    # =====================================================================
    #
    # 📊 O defeito: o fiscal da pergunta repetida podia regenerar e, logo
    # depois, este regenerava DE NOVO — duas chamadas extras ao modelo num
    # turno só, dobrando a latência enquanto o segurado espera e arriscando
    # que a segunda reescrita desfaça o conserto da primeira (a régua de
    # tamanho não sabe nada sobre pergunta repetida).
    #
    # ⚠️ Quando o primeiro já regenerou, este NÃO regenera: registra no feed
    # e a mensagem sai. É a mesma direção dos outros fiscais — nunca travar a
    # resposta por uma régua de estilo (CLAUDE.md §9.5).
    if ja_regenerou:
        logger.warning("[TAMANHO] fora da classe %s, mas o turno JÁ regenerou "
                       "uma vez — a mensagem SAI e o defeito vai ao feed", classe)
        await _registrar_tamanho_no_feed(state, classe, unidades, teto, texto)
        return texto, classe

    logger.warning("[TAMANHO] resposta fora da classe %s (%d unidades, teto %d; "
                   "%d chars) — regenerando UMA vez", classe, unidades, teto,
                   len((texto or "").strip()))
    novo = ""
    try:
        novo = await regenerar(regua_do_tamanho(classe))
    except Exception as exc:  # noqa: BLE001
        logger.error("[TAMANHO] regeneração falhou (%s) — segue a resposta "
                     "original", type(exc).__name__)

    if novo:
        ainda, classe2, unidades2, teto2 = fora_da_classe(novo)
    else:
        ainda, classe2, unidades2, teto2 = True, classe, unidades, teto
    final = novo or texto
    if not ainda:
        return final, ""

    await _registrar_tamanho_no_feed(state, classe2, unidades2, teto2, final)
    return final, classe2


async def agent_node(state: AgentState, config: RunnableConfig, llm_with_tools,
                     llm_base=None, tools_base=None, cutover_ctx=None,
                     llm_reserva=None, rota: Optional[dict] = None) -> dict:
    """
    Nó do Agente - Decide se usa uma tool ou responde diretamente.
    INCLUI CORREÇÃO PARA ERRO DE REASONING (OpenAI 400).

    Aceita 'config' para propagar callbacks de streaming.

    SPEC-057 §I: é aqui que o Tool Gateway entra, e não na montagem do grafo.
    O grafo é cacheado por (empresa, agente) e reusado em muitas conversas —
    escolher ferramenta lá fixaria a mesma lista para todas, que é o oposto do
    progressive disclosure. Só aqui existe a pergunta do corretor, e sem ela
    não há Skill a resolver.
    """
    logger.info("[Agent Node] Processando...")

    # === ✂️ JANELA DESLIZANTE (SLIDING WINDOW) ===
    # Mantém apenas as últimas 15 mensagens para o contexto imediato
    all_messages = state["messages"]
    JANELA_CONTEXTO = AGENT_CONTEXT_WINDOW_SIZE

    if len(all_messages) > JANELA_CONTEXTO:
        messages_to_process = all_messages[-JANELA_CONTEXTO:]
        logger.info(
            f"[Agent Node] Trimming ativo: Enviando {len(messages_to_process)} msgs (de um total de {len(all_messages)})"
        )
    else:
        messages_to_process = all_messages

    # === 🛡️ SANITIZAÇÃO PÓS-TRIMMING ===
    # Remove ToolMessages órfãs que perderam suas AIMessages com tool_calls
    messages_to_process = sanitize_history(messages_to_process)
    logger.debug(f"[Agent Node] Após sanitização: {len(messages_to_process)} msgs")

    current_user_query = ""
    for msg in reversed(messages_to_process):
        if isinstance(msg, HumanMessage) or (hasattr(msg, "type") and msg.type == "human"):
            current_user_query = extract_text_from_content(getattr(msg, "content", ""))
            break
    # === SPEC-057 §I — Tool Gateway por turno ===
    # Roda depois de conhecer a pergunta e antes de qualquer chamada ao modelo.
    # Em `shadow` só grava o diff; em `on` re-liga o modelo com a lista que o
    # Gateway autorizou — e ele só consegue REMOVER ferramenta, nunca somar.
    tools_do_turno = tools_base
    if cutover_ctx and llm_base is not None and tools_base:
        try:
            from .gateway_cutover import aplicar as _cutover_aplicar
            from .gateway_cutover import avaliar as _cutover_avaliar

            _veredito = _cutover_avaliar(
                tools_legado=tools_base,
                supabase_client=cutover_ctx.get("supabase_client"),
                company_id=cutover_ctx.get("company_id"),
                agent_role=cutover_ctx.get("agent_role") or "core",
                texto_usuario=current_user_query or "",
                active_capabilities=cutover_ctx.get("active_capabilities"),
            )
            if _veredito.aplicar:
                _filtradas = _cutover_aplicar(tools_base, _veredito)
                if len(_filtradas) != len(tools_base):
                    llm_with_tools = llm_base.bind_tools(_filtradas)
                    tools_do_turno = _filtradas
        except Exception as exc:  # noqa: BLE001
            # Falha do Gateway nunca derruba o atendimento: o corretor continua
            # sendo respondido pelo caminho antigo e o erro vira registro.
            logger.warning("[Agent Node] cutover ignorado: %s", type(exc).__name__)

    context_tool_args = _policy_context_tool_args(current_user_query, state.get("infocap_policy_context"))
    if context_tool_args and _consulta_forcada_ja_feita_no_turno(all_messages):
        # 🔴 SPEC-116 (conserto, relatório 06 §1 / juiz P6): a consulta FORÇADA
        # roda UMA vez por pergunta. 📊 Com POLICY_INTELLIGENCE_V2 ligada, a
        # volta `tools → agent` (should_continue_after_tools) chegava aqui com a
        # MESMA pergunta e forçava de novo — 7 consultas num turno na bancada.
        # Já consultado: o modelo redige com o resultado que está no histórico.
        logger.info("[Agent Node] InfoCap policy context lock: já consultado neste turno — segue ao modelo")
        context_tool_args = None
    if context_tool_args:
        tool_call_id = f"{_ID_DA_CONSULTA_FORCADA}{int(time.time() * 1000)}"
        logger.info("[Agent Node] InfoCap policy context lock: resolving human number inside customer catalog")
        return {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "infocap_policy_lookup",
                            "args": context_tool_args,
                            "id": tool_call_id,
                        }
                    ],
                )
            ],
            "rag_chunks": state.get("rag_chunks", []),
            "tools_used": state.get("tools_used", []),
            "llm_response_time_ms": state.get("llm_response_time_ms", 0),
            "tokens_input": state.get("tokens_input", 0),
            "tokens_output": state.get("tokens_output", 0),
            "tokens_total": state.get("tokens_total", 0),
        }

    # === Preparação do System Prompt ===
    system_prompt = state.get("system_prompt")
    static_prompt = state.get("static_prompt")  # Parte cacheável
    dynamic_context = state.get("dynamic_context", "")  # Parte dinâmica

    if not system_prompt:
        # Fallback se não vier no state
        company_config = state["company_config"]
        agent_data = state.get("agent_data")

        if agent_data and agent_data.get("agent_system_prompt"):
            company_config["agent_system_prompt"] = agent_data["agent_system_prompt"]

        rag_context = state.get("rag_context", "")
        system_prompt = build_system_prompt(company_config, rag_context)
        static_prompt = system_prompt  # Sem separação no fallback

    # === 🔥 ANTHROPIC PROMPT CACHING ===
    # Detecta provider para ativar cache (economia de até 90% em inputs repetidos)
    agent_data = state.get("agent_data") or {}
    company_config = state.get("company_config") or {}
    # 🔴 SPEC-116 (conserto, red team B1): quem decide o formato do system é o
    # provedor da ROTA — o que a fábrica RESOLVEU e para onde a chamada vai —,
    # nunca o `llm_provider` gravado. 📊 Agente nascido NULO (F4) indo à
    # Anthropic pela rota ficava SEM cache_control: input cheio (2,00 × 0,20
    # US$/M no Sonnet 5) a cada turno. O gravado só vale sem rota (chamador
    # antigo que não passa `rota`).
    llm_provider = _provedor_do_turno(rota, agent_data, company_config)

    if llm_provider == "anthropic" and static_prompt:
        # Anthropic: 2 blocos - estático (cacheado) + dinâmico (não cacheado)
        content_blocks = [
            {
                "type": "text",
                "text": static_prompt,
                "cache_control": {"type": "ephemeral"}  # TTL 5 minutos
            }
        ]
        # Adiciona contexto dinâmico SEM cache (memória pode mudar)
        if dynamic_context:
            content_blocks.append({
                "type": "text",
                "text": dynamic_context
                # SEM cache_control - muda a cada request
            })
        system_message = SystemMessage(content=content_blocks)
        logger.info(f"[Agent Node] 🔥 Anthropic cache: static={len(static_prompt)} chars (~{len(static_prompt)//4} tokens), dynamic={len(dynamic_context)} chars")
    else:
        # OpenAI/Google: Content simples (cache automático na OpenAI)
        system_message = SystemMessage(content=system_prompt)

    llm_messages = [system_message]

    # === 🔥 Identificar ToolMessages da rodada ATUAL (para compressão) ===
    pending_tool_call_ids = set()
    for msg in reversed(messages_to_process):
        if isinstance(msg, AIMessage) or (hasattr(msg, "type") and msg.type == "ai"):
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    if isinstance(tc, dict):
                        pending_tool_call_ids.add(tc.get("id"))
                    else:
                        pending_tool_call_ids.add(getattr(tc, "id", None))
            break

    # === 🛡️ Montagem do Histórico BLINDADA (Sanitização) ===
    for msg in messages_to_process:
        if isinstance(msg, HumanMessage):
            llm_messages.append(msg)

        elif isinstance(msg, AIMessage):
            # 🔴 SPEC-116 U6a: o raciocínio VOLTA a quem o produziu (mesmo
            # provedor e modelo); só sanitiza quando o provedor/modelo mudou.
            llm_messages.append(mensagem_do_assistente_para(
                msg, (rota or {}).get("provedor"), (rota or {}).get("modelo")))

        elif isinstance(msg, ToolMessage):
            # Lógica de compressão de tools antigas
            if msg.tool_call_id in pending_tool_call_ids:
                if msg.name == "knowledge_base_search":
                    try:
                        # Tenta limpar JSON de search para economizar tokens
                        result_dict = json.loads(msg.content)
                        readable_content = result_dict.get("content", msg.content)
                    except Exception:
                        readable_content = msg.content

                    llm_messages.append(
                        ToolMessage(
                            content=readable_content,
                            tool_call_id=msg.tool_call_id,
                            name=msg.name,
                        )
                    )
                else:
                    llm_messages.append(msg)
            else:
                # Comprime tools antigas
                llm_messages.append(
                    ToolMessage(
                        content="[🔍 RAG: Conteúdo bruto removido para otimização. As informações relevantes já constam na resposta anterior da Assistente.]",
                        tool_call_id=msg.tool_call_id,
                        name=msg.name,
                    )
                )

        # Fallback para tipos genéricos
        elif hasattr(msg, "type"):
            if msg.type == "human":
                llm_messages.append(HumanMessage(content=msg.content))
            elif msg.type == "ai":
                llm_messages.append(AIMessage(content=str(msg.content)))  # Força string
            elif msg.type == "tool":
                # Aplica compressão simples
                llm_messages.append(
                    ToolMessage(
                        content="[Conteúdo Otimizado]",
                        tool_call_id=getattr(msg, "tool_call_id", ""),
                        name=getattr(msg, "name", ""),
                    )
                )

    logger.info(f"[Agent Node] Enviando {len(llm_messages)} mensagens ao LLM")

    start_time = time.time()
    # Executa o LLM (com streaming ativo nas configs) — e a RESERVA da rota,
    # só antes da 1ª ferramenta do turno (SPEC-116 U6c).
    response, llm_with_tools, llm_messages = await _invocar_o_modelo(
        llm_with_tools, llm_messages, config, state,
        llm_reserva=llm_reserva, tools_do_turno=tools_do_turno, rota=rota)
    response_time = int((time.time() - start_time) * 1000)

    logger.info(f"[Agent Node] LLM respondeu em {response_time}ms")

    # 🔴 CORREÇÃO: Extração de Tokens
    usage = getattr(response, "usage_metadata", {}) or {}
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    total_tokens = usage.get("total_tokens", 0)

    # Nota: Normalização de tokens Anthropic foi removida (desnecessária desde Claude 4.5, Dec/2025)

    # Log para validação
    if total_tokens > 0:
        logger.info(f"[Agent Node] 💰 Tokens Capturados: In={input_tokens}, Out={output_tokens}, Total={total_tokens}")
    else:
        logger.warning("[Agent Node] ⚠️ Tokens ainda não encontrados (verifique stream_options).")

    # === SPEC-016.1 D7: guard pós-LLM do contrato de apólice ===
    # A LLM redige a resposta final; o contrato fiscaliza (opções completas,
    # sem valores inventados, ausência honesta). Violação → texto seguro.
    guarded_final: Optional[str] = None
    contract = state.get("policy_response_contract")
    has_tool_calls = bool(getattr(response, "tool_calls", None))
    if (
        _policy_intelligence_v2()
        and isinstance(contract, dict)
        and contract.get("provider") == "infocap"
        and not has_tool_calls
    ):
        # 🔴 RODADA 3 (B3): é AQUI que a segunda passada acontece — a consulta
        #    rodou numa invocação, o acionamento noutra, e o contrato veio do
        #    `state`. Sem esta linha, "Pronto! Já acionei a assistência" era
        #    trocado pelo veredito de cobertura.
        contract = _consumir_regua_apos_acao(contract, state.get("tools_used") or [])
        candidate = extract_text_from_content(getattr(response, "content", "") or "")
        guarded = _guard_infocap_policy_final_response(candidate, contract)
        if guarded and guarded.strip() != (candidate or "").strip():
            logger.info("[Agent Node] 🛡️ Output guard substituiu resposta de apólice fora do contrato")
            response = mesma_mensagem_com_texto(response, guarded)
        guarded_final = guarded or candidate

    # 🔴 O FISCAL DA TRANSFERÊNCIA — 18/08/2026.
    #
    # Mesmo ponto e mesma forma do fiscal do InfoCap logo acima: determinístico,
    # depois do modelo, só reescreve quando a resposta extrapola o que a
    # ferramenta autorizou. Não é motor novo — é a segunda instância de um
    # padrão que o produto já tem.
    #
    # 📊 Em 17/08 a atendente disse QUATRO vezes que tinha encaminhado o caso.
    # Nenhuma vez encaminhou. `prompts.py:203` já proibia isso em português e
    # já tinha falhado — prosa não conserta prosa. A frase agora só sobrevive
    # se existir um `HANDOFF_OK` vindo da própria ferramenta.
    if not has_tool_calls:
        _texto_final = extract_text_from_content(getattr(response, "content", "") or "")
        _honesto = guardar_a_verdade_do_handoff(_texto_final, state.get("messages") or [])
        if _honesto.strip() != (_texto_final or "").strip():
            logger.error("[Agent Node] 🛡️ resposta afirmava transferência sem handoff "
                         "confirmado — reescrita")
            response = mesma_mensagem_com_texto(response, _honesto)
            if guarded_final:
                guarded_final = _honesto

    # 🔴 O FISCAL DA PERGUNTA REPETIDA — SPEC-EXTRA-001.2 §7.3.
    #
    # 📊 10/09: a ficha tinha `agua_escorrendo` respondido ("não, fechei o
    # registro") e a atendente perguntou pela TERCEIRA vez. O bloco do prompt
    # já dizia "não pergunte de novo" — prosa no prompt não conserta prosa do
    # modelo (mesma lição do fiscal da transferência, logo acima).
    _ja_regenerou = False
    if not has_tool_calls:
        _texto_gerado = extract_text_from_content(getattr(response, "content", "") or "")

        async def _regenerar(_slots, _ficha):
            from app.services.attendance_ficha import rotulo

            _lista = "\n".join("  · %s: %s" % (rotulo(s), _valor_da_ficha(_ficha, s))
                               for s in _slots)
            _aviso = (
                "⛔ A resposta que você acabou de escrever PERGUNTA DE NOVO o "
                "que o cliente já respondeu nesta conversa:\n" + _lista +
                "\n\nReescreva a resposta USANDO esses dados como verdade já "
                "confirmada. Não peça confirmação deles e não os mencione como "
                "dúvida. Siga do ponto em que o atendimento parou.")
            # 🔴 SPEC-116 U8: nunca um SystemMessage no fim (Claude recusa).
            _resp = await llm_with_tools.ainvoke(
                mensagens_com_correcao(llm_messages, _aviso), config=config)
            return extract_text_from_content(getattr(_resp, "content", "") or "")

        _final, _persistiu = await _resposta_sem_pergunta_repetida(
            _texto_gerado, state, regenerar=_regenerar)
        # 🔴 J8: "regenerou" é exatamente "o texto mudou". ⚠️ Não há bandeira
        # nova a carregar — a evidência é o próprio texto, e ela não pode
        # divergir de si mesma.
        _ja_regenerou = bool(_final and _final.strip() != (_texto_gerado or "").strip())
        if _ja_regenerou:
            response = mesma_mensagem_com_texto(response, _final)
            if guarded_final:
                guarded_final = _final
        if _persistiu:
            logger.error("[Agent Node] 🛡️ resposta ainda repergunta %s — enviada "
                         "assim mesmo e registrada no feed", _persistiu)

    # 🔴 O FISCAL DO TAMANHO — SPEC-EXTRA-001.2 §8.2.
    #
    # ⚠️ Ele roda POR ÚLTIMO, e é de propósito: a regeneração do fiscal da
    # pergunta repetida produz um texto NOVO, e é esse texto que vai ao
    # segurado. Medir o tamanho antes dela mediria uma resposta que não sai.
    if not has_tool_calls:
        _texto_atual = extract_text_from_content(getattr(response, "content", "") or "")

        async def _encurtar(_regua):
            _aviso = (
                "⛔ A resposta que você acabou de escrever está FORA do tamanho "
                "que este momento do atendimento permite.\n" + _regua +
                "\n\nReescreva a MESMA resposta dentro dessa régua, sem perder "
                "nenhuma informação que o cliente precisa para agir. Corte "
                "explicação, não conteúdo.")
            # 🔴 SPEC-116 U8: nunca um SystemMessage no fim (Claude recusa).
            _resp = await llm_with_tools.ainvoke(
                mensagens_com_correcao(llm_messages, _aviso), config=config)
            return extract_text_from_content(getattr(_resp, "content", "") or "")

        _curto, _classe_fora = await _resposta_no_tamanho_da_classe(
            _texto_atual, state, regenerar=_encurtar,
            ja_regenerou=_ja_regenerou)
        if _curto and _curto.strip() != (_texto_atual or "").strip():
            response = mesma_mensagem_com_texto(response, _curto)
            if guarded_final:
                guarded_final = _curto
        if _classe_fora:
            logger.error("[Agent Node] 🛡️ resposta ainda fora da classe %s — "
                         "enviada assim mesmo e registrada no feed", _classe_fora)

    result_update = {
        "messages": [response],
        "rag_chunks": state.get("rag_chunks", []),
        "tools_used": state.get("tools_used", []),
        # Acumula manualmente (sem reducer no AgentState)
        # O initial_state reseta para 0, então só soma dentro desta execução
        "llm_response_time_ms": state.get("llm_response_time_ms", 0) + response_time,
        "tokens_input": state.get("tokens_input", 0) + input_tokens,
        "tokens_output": state.get("tokens_output", 0) + output_tokens,
        "tokens_total": state.get("tokens_total", 0) + total_tokens
    }
    if guarded_final:
        result_update["final_response"] = guarded_final
    return result_update


def _abrir_registro_de_invocacao(state: AgentState, *, tool_name: str,
                                 tool_args: dict):
    """Contexto de registro da invocação, ou um nulo que não faz nada.

    Devolver um objeto inerte em vez de `None` mantém o `with` do chamador com
    uma forma só. Se a auditoria estiver indisponível — sem cliente, sem
    empresa, import quebrado — a ferramenta roda igual: perder o registro é
    ruim, perder o trabalho do corretor é pior.

    🔴 O `trace_id` LIGA A INVOCAÇÃO AO TURNO (P-PILOTO-18, reescrita). Ele
    deixa de ser só o `session_id` e passa a ser `"<session_id>|<turno>"`,
    montado por `chave_de_rastro` — a MESMA função que o `/chat/stream` usa
    para ler de volta. ⛔ Uma segunda montagem do formato, escrita em outro
    arquivo, divergiria e a junção voltaria vazia sem ninguém ver.
    ⚠️ Fora de um turno de chat (Rotina, Work Run, worker) o turno é `None` e o
    rastro continua sendo a sessão, exatamente como era.
    """
    try:
        from app.core.database import get_supabase_client
        from app.services.skills.invocation_recorder import (
            RegistroDeInvocacao, chave_de_rastro,
        )

        company_id = state.get("company_id")
        if not company_id:
            agente = state.get("agent_data") or {}
            company_id = agente.get("company_id")
        if not company_id:
            return _RegistroInerte(motivo="sem_company_id")

        return RegistroDeInvocacao(
            get_supabase_client(), company_id=str(company_id),
            nome_da_tool=str(tool_name), argumentos=tool_args or {},
            trace_id=chave_de_rastro(state.get("session_id")))
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Tool Node] registro de invocação indisponível: %s",
                       type(exc).__name__)
        return _RegistroInerte(motivo=type(exc).__name__)


#: 🔴 QUANTAS VEZES A AUDITORIA FICOU MUDA — P-PILOTO-18, o 2º item.
#:
#: O `_RegistroInerte` está CERTO como desenho: perder o registro é melhor que
#: perder o trabalho do corretor. Ele estava ERRADO sem contador — engolir em
#: silêncio é como `tool_invocations` ficou em ZERO com o produto em uso, e
#: ninguém soube (SPEC-061, Bloco 0). Um número que ninguém mede é um número
#: que ninguém conserta.
#:
#: ⚠️ É contador de PROCESSO (some no restart), não métrica de produto: serve
#: ao guarda e ao log. Quem quiser série temporal lê o `warning`.
_REGISTROS_INERTES = 0
_MOTIVOS_INERTES: Dict[str, int] = {}


def registros_inertes() -> int:
    """Quantas invocações rodaram SEM auditoria neste processo."""
    return _REGISTROS_INERTES


def motivos_inertes() -> Dict[str, int]:
    """Por que elas ficaram mudas — `{motivo: quantas}`."""
    return dict(_MOTIVOS_INERTES)


def zerar_registros_inertes() -> None:
    """Só para o guarda: cada caso começa do zero."""
    global _REGISTROS_INERTES
    _REGISTROS_INERTES = 0
    _MOTIVOS_INERTES.clear()


class _RegistroInerte:
    """Nulo com a mesma forma. Nunca falha, nunca grava — e SE CONTA."""

    def __init__(self, motivo: str = "desconhecido"):
        global _REGISTROS_INERTES
        _REGISTROS_INERTES += 1
        _MOTIVOS_INERTES[motivo] = _MOTIVOS_INERTES.get(motivo, 0) + 1
        self.motivo = motivo
        logger.warning(
            "[Tool Node] invocação SEM auditoria (motivo=%s; %d neste processo)",
            motivo, _REGISTROS_INERTES)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def ok(self, *_a, **_k):
        return None

    def erro(self, **_k):
        return None

    def negada(self, **_k):
        return None



# 🔴 A LISTA ESCRITA À MÃO MORREU — SPEC-EXTRA-001.2 BLOCO C (§7.1).
#
# Aqui havia uma tupla literal de **15** nomes. `ROTULOS` tinha 35 e os 14
# corredores exigiam 54 — 📊 medido pelo motor em 14/09/2026. `agua_escorrendo`
# não estava em nenhuma das duas listas, e o segurado do encanador ouviu a mesma
# pergunta pela terceira vez. Duas listas escritas à mão divergem no dia em que
# alguém acrescenta um slot num lado só; estas já tinham divergido.
#
# Quem responde agora é `attendance_ficha.slots_do_atendimento()`, DERIVADO de
# `ROTULOS ∪ required_slots dos corredores − CAMPOS_DE_CONTROLE`.

#: Slots que, quando a InfoCap já resolveu a apólice deste caso, vieram do
#: SISTEMA DE GESTÃO e não da boca do segurado.
#:
#: 📊 `infocap_tool.py:455` e `:1025` — *"para apólice AUTO, placa/veículo vêm
#: da fonte; o atendente NUNCA pede placa ao cliente"*. O CPF fica de fora de
#: propósito: é POR ELE que a consulta acha a apólice, então quem o disse foi o
#: cliente. Sem contexto de InfoCap no turno, tudo é do cliente.
_DO_SISTEMA_DE_GESTAO = ("veiculo_placa", "veiculo_descricao")


async def _gravar_ficha_do_turno(state: dict, tool_name: str,
                                 tool_args: dict, result,
                                 contexto_da_apolice: Optional[dict] = None) -> None:
    """Guarda o que este turno apurou, para o próximo não reperguntar.

    SPEC-063 Bloco S. É o lado da ESCRITA do laço que fecha o buraco: o modelo
    declara os slots na tool, a ficha grava, e o turno seguinte mostra de volta.

    🔴 SPEC-117 F3.3: `contexto_da_apolice` é o PolicyContext do turno, resolvido
    UMA vez pelo `tool_node` (estado → ficha durável). **Havendo apólice do
    sistema de gestão, é a do sistema que vai para a ficha** — o `insurer_key` e
    o `line_kind` que o MODELO escreveu ficam só como sinal de divergência, e a
    divergência vira log. Sem apólice do sistema, segue como antes: o modelo.

    Nunca levanta para fora: uma falha aqui custa a memória de um turno; deixar
    a exceção subir custaria a resposta ao segurado.
    """
    from app.core.database import get_supabase_client
    from app.services.attendance_ficha import (
        FASE_COM_HUMANO,
        ORIGEM_CLIENTE,
        ORIGEM_SISTEMA_DE_GESTAO,
        apolice_do_caso,
        confirmacao,
        gravar,
        linha_do_corredor,
        novidades_da_apolice,
        slots_do_atendimento,
    )

    company_id = str(state.get("company_id") or "")
    session_id = str(state.get("session_id") or "")
    if not (company_id and session_id):
        return

    novidades: dict = {}

    # 🔴 SPEC-117 F3.3 — a LEITURA ÚNICA da apólice do caso. `contexto_da_apolice`
    #    já vem resolvido pelo `tool_node` (estado → ficha); o `state` fica como
    #    caminho de quem chama esta função de fora do nó.
    apolice = apolice_do_caso(contexto=contexto_da_apolice, state=state)

    # 🔴 A apólice do caso vai para a ficha DURÁVEL no mesmo ato, e com os dois
    #    tipos certos: `apolice` STRING (o número humano, que é o que o aviso à
    #    atendente humana imprime) e `apolice_do_caso` DICT (a estrutura).
    #    📊 Até 26/09/2026 ninguém escrevia `ficha["apolice"]`, e por isso o
    #    aviso ao humano saía sem o número (`human_handoff.py:607`).
    novidades.update(novidades_da_apolice(contexto_da_apolice))

    if tool_name == "request_human_agent":
        # Devolvido a uma pessoa. A fase trava aqui: só um humano tira daqui.
        novidades["fase"] = FASE_COM_HUMANO
    else:
        # Cada confirmação carrega a ORIGEM: o bloco do prompt diz ao modelo o
        # que ele NÃO pode perguntar de novo (o cliente disse) e o que ele pode
        # só CONFIRMAR numa frase (veio do sistema de gestão).
        # 🔴 SPEC-117 F3.3: "tem InfoCap" passou a ser "HÁ APÓLICE DO CASO" — pela
        #    leitura única, não por "existe um dicionário no estado". Duas
        #    candidatas sem escolha não são a apólice do caso, e marcar a placa
        #    como vinda do sistema nesse ponto seria marcar origem de um contrato
        #    que ninguém escolheu ainda.
        tem_infocap = bool(apolice)
        confirmados = {}
        for chave in slots_do_atendimento():
            valor = tool_args.get(chave)
            if valor in (None, ""):
                continue
            origem = (ORIGEM_SISTEMA_DE_GESTAO
                      if tem_infocap and chave in _DO_SISTEMA_DE_GESTAO
                      else ORIGEM_CLIENTE)
            confirmados[chave] = confirmacao(valor, origem)
        # 🔴 Decisão do Founder (17/09): com o RAMO DA APÓLICE conhecido, a tecla
        #    "qual seguro" está resolvida — a ficha diz isso ao modelo, para ele
        #    não perguntar de novo. A origem é o sistema quando o ramo veio dele.
        _ramo = tool_args.get("ramo_da_apolice")
        if _ramo and "qual_seguro_opcao" in slots_do_atendimento():
            try:
                from app.providers.policy_data_provider import NOME_DA_FAMILIA, familia_de_ramo

                _familia = familia_de_ramo(_ramo)
                # 🔴 SPEC-117 F3.3: a comparação é com a apólice do caso, pela
                #    leitura única — a regra do ramo não se duplica aqui.
                _do_sistema = bool(_familia) and _familia == str(
                    (apolice or {}).get("ramo") or "")
                if _familia in ("resi", "cond", "empr"):
                    confirmados["qual_seguro_opcao"] = confirmacao(
                        NOME_DA_FAMILIA[_familia],
                        ORIGEM_SISTEMA_DE_GESTAO if _do_sistema else ORIGEM_CLIENTE)
            except Exception:  # noqa: BLE001 — a ficha nunca derruba o turno
                pass
        if confirmados:
            novidades["confirmados"] = confirmados
        for origem, destino in (("insurer_key", "seguradora"),
                                ("line_kind", "ramo"),
                                ("subservice", "servico"),
                                ("servico", "servico")):
            if not tool_args.get(origem):
                continue
            # ═══════════════════════════════════════════════════════════════
            # 🔴 SPEC-117 F3.3 — HAVENDO APÓLICE DO SISTEMA, A DO SISTEMA VENCE
            # ═══════════════════════════════════════════════════════════════
            #
            # Estas duas linhas copiavam `insurer_key` e `line_kind` dos
            # `tool_args` — isto é, do que o MODELO escreveu — direto para a
            # ficha durável. A ficha é lida depois por
            # `graph._slots_obrigatorios_do_caso` (que resolve o CORREDOR) e por
            # `human_handoff._linha_da_apolice` (o aviso à atendente). Um palpite
            # do modelo virava o corredor do caso e o texto que o humano lê, sem
            # nada travar (CLAUDE.md §9.5).
            _do_sistema = ""
            if destino == "seguradora":
                _do_sistema = _chave_da_seguradora((apolice or {}).get("seguradora"))
            elif destino == "ramo":
                # ⚠️ A LINHA do corredor, não a família crua: `graph.py:798`
                # entrega `ficha["ramo"]` a `resolve_playbook_ref` como
                # `line_kind`, e ele não conhece `"resi"` (ver
                # `attendance_ficha.LINHA_DO_CORREDOR_POR_FAMILIA`).
                _do_sistema = linha_do_corredor((apolice or {}).get("ramo"))
            if _do_sistema:
                _do_modelo = str(tool_args[origem] or "").strip().lower()
                if _do_modelo and _do_modelo != _do_sistema:
                    # 📊 A métrica de divergência modelo × sistema na FICHA.
                    logger.warning("[APOLICE] %s DIVERGENTE na ficha: modelo=%r "
                                   "sistema=%r — vale o sistema",
                                   destino, _do_modelo, _do_sistema)
                novidades[destino] = _do_sistema
                continue
            novidades[destino] = tool_args[origem]
        # A placa resolvida pela InfoCap é prova de apólice localizada; o
        # modelo não pode marcar isso sozinho.
        if tool_args.get("dados_confirmados") is True and tool_args.get("veiculo_placa"):
            novidades["apolice_confirmada"] = True

        texto = str(result if isinstance(result, str) else (result or {}))
        # Protocolo só entra se veio do RESULTADO da tool — nunca de algo que o
        # modelo tenha escrito. Protocolo inventado é o defeito que o guardrail
        # `no_fake_protocol` existe para impedir.
        import re as _re
        m = _re.search(r"protocolo[^0-9A-Za-z]{0,12}([A-Za-z0-9-]{5,})", texto, _re.I)
        if m:
            novidades["acionamento"] = {"protocolo": m.group(1)}

    if not novidades:
        return

    try:
        from app.services.attendance_ficha import ficha_vazia
        from app.agents.graph import _slots_obrigatorios_do_caso

        obrig = _slots_obrigatorios_do_caso({**ficha_vazia(), **novidades})
    except Exception:  # noqa: BLE001
        obrig = []

    await gravar(get_supabase_client().client, company_id, session_id,
                 novidades, obrig)


async def tool_node(state: AgentState, tools: list) -> dict:
    """
    Nó de Tools - Executa as tools chamadas pelo agente.
    Async para permitir chamadas _arun em tools que suportam (ex: SubAgentTool).
    """
    logger.info("[Tool Node] Executando tools...")

    messages = state["messages"]
    last_message = messages[-1]

    tool_results = []
    tools_used = state.get("tools_used", [])
    rag_chunks = state.get("rag_chunks", [])
    rag_search_time = state.get("rag_search_time_ms", 0)
    policy_response_contract = None
    policy_final_response = None
    infocap_policy_context = None
    # 🔴 SPEC-117 F3: a apólice do caso é resolvida UMA vez por turno, e todos os
    #    consumidores (consulta, acionamento, portal, ficha) leem a MESMA.
    memo_da_apolice: Dict[str, Any] = {}

    # Extrair agent_id do state
    agent_data = state.get("agent_data")
    raw_agent_id = agent_data.get("id") if agent_data else None
    agent_id = str(raw_agent_id) if raw_agent_id else None

    # SPEC-044: usuário da REQUISIÇÃO (o grafo é cacheado/compartilhado — a
    # identidade viaja no state e é injetada por execução, nunca no construtor).
    raw_user_id = state.get("user_id")
    request_user_id = str(raw_user_id) if raw_user_id else None

    # 🔥 Extrair is_hyde_enabled (default True para retrocompatibilidade)
    is_hyde_enabled = agent_data.get("is_hyde_enabled", True) if agent_data else True
    current_user_query = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage) or (hasattr(msg, "type") and msg.type == "human"):
            current_user_query = extract_text_from_content(getattr(msg, "content", ""))
            break

    tool_map = {tool.name: tool for tool in tools}

    # Tracking para SubAgent delegation
    delegation_tokens_input = 0
    delegation_tokens_output = 0
    delegation_tokens_total = 0
    internal_steps = state.get("internal_steps", []) or []

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            if isinstance(tool_call, dict):
                tool_name = tool_call.get("name")
                tool_args = tool_call.get("args", {})
                tool_call_id = tool_call.get("id")
            else:
                tool_name = getattr(tool_call, "name", None)
                tool_args = getattr(tool_call, "args", {})
                tool_call_id = getattr(tool_call, "id", None)

            logger.info(f"[Tool Node] Chamando: {tool_name}")

            if tool_name in tool_map:
                tool = tool_map[tool_name]

                try:
                    # Injeção de Dependências Dinâmicas (invisível para a LLM)
                    if tool_name == "knowledge_base_search":
                        # 🔥 Injeta agent_id, is_hyde_enabled e (SPEC-044) o usuário
                        # da requisição — habilita a busca nos docs PESSOAIS dele.
                        tool_args = {**tool_args, "agent_id": agent_id, "is_hyde_enabled": is_hyde_enabled,
                                     "user_id": request_user_id}
                    elif tool_name in ("create_routine", "list_routines", "manage_routine"):
                        # SPEC-044: rotinas com dono — visibilidade pessoal/corretora
                        tool_args = {**tool_args, "user_id": request_user_id}
                    elif tool_name == "csv_analytics":
                        # 🔥 Injeta agent_id para isolamento multi-tenant
                        tool_args = {**tool_args, "agent_id": agent_id}
                    elif tool_name in (
                        "filesystem_get_outline",
                        "filesystem_read_section",
                        "filesystem_search",
                        "filesystem_get_metadata",
                    ):
                        # 📂 File System Search: injeta agent_id
                        tool_args = {**tool_args, "agent_id": agent_id}
                    elif tool_name == "request_human_agent":
                        # SPEC-063 Bloco B — `company_id` passa a viajar junto.
                        # Sem ele o UPDATE da conversa filtrava só por session_id
                        # (viola CLAUDE.md §7) e o aviso ao suporte não tinha
                        # como saber de QUEM é o destino.
                        session_id = state.get("session_id")
                        tool_args = {**tool_args, "session_id": session_id,
                                     "company_id": state.get("company_id")}
                    elif tool_name == "http_api":
                        allowed_http_tools = state.get("allowed_http_tools", [])
                        tool_args = {**tool_args, "allowed_tools": allowed_http_tools}
                    elif tool_name == "infocap_policy_lookup":
                        # O pedido real ("preciso de guincho") costuma vir ANTES do
                        # CPF — enviar só a última mensagem escondia a intenção e a
                        # tool não conseguia escolher a apólice AUTO sozinha
                        # (incidente 2026-07-12: picker com opções inventadas).
                        #
                        # 🔴 SPEC-EXTRA-001.1 §6.3: a janela das 3 últimas humanas
                        # passou a valer para TODOS OS PAPÉIS. 📊 Medido em
                        # 14/09/2026: a condição era `if _role in ("attendance",
                        # "insured_external")`, e fora dela `_query_for_tool` era a
                        # ÚLTIMA humana. Era por isso que, no Chat Principal
                        # (`core`), "meu carro quebrou" duas mensagens antes do CPF
                        # não chegava à tool — e a pergunta "só o CPF" ficava sem
                        # ramo nenhum. O conserto é ESTENDER a condição; a janela
                        # não é reescrita.
                        _recent_humans = [
                            extract_text_from_content(getattr(m, "content", ""))
                            for m in messages
                            if isinstance(m, HumanMessage) or (hasattr(m, "type") and getattr(m, "type", "") == "human")
                        ]
                        # 🔴 RODADA 5 (pendência 6): o separador vem da tool,
                        #    que é quem FATIA a janela de volta. Duas literais
                        #    independentes em pontas opostas é o tipo de coisa
                        #    que só se descobre quebrada quando uma muda.
                        from .tools.infocap_tool import SEPARADOR_DA_JANELA

                        _query_for_tool = SEPARADOR_DA_JANELA.join(
                            [t for t in _recent_humans[-3:] if t]) or current_user_query
                        # ② A FICHA do atendimento: a apólice já confirmada no caso
                        #    vence a dedução por texto — e impede a segunda pergunta.
                        # 🔴 SPEC-117 F3: pela LEITURA ÚNICA, e a partir da ficha
                        #    durável quando o processo reiniciou (G8). Antes isto
                        #    lia `selected_policy_number` do estado — que no
                        #    WhatsApp nunca existia (📊 `nodes.py:423-425`).
                        _apolice_do_caso = await _apolice_do_caso_do_turno(
                            state, memo_da_apolice)
                        _ja_escolhida = str((_apolice_do_caso or {}).get("numapo") or "").strip()
                        # 🔴 SPEC-EXTRA-001.5.1 · CONSERTO B2 — a CONVERSA viaja
                        #    junto, pelo MESMO caminho de `insurer_dispatch`
                        #    (abaixo) e de `request_human_agent` (acima): o
                        #    `session_id` sai do ESTADO, nunca da LLM.
                        #
                        #    📊 Sem ele, o 🆘 da lacuna de cobertura saía sem
                        #    conversa — e a guarda da 001.3 PULA as perguntas 3 e
                        #    4 ("conversa assumida?", "humano falou há pouco?")
                        #    quando não há conversa. O grupo era avisado por cima
                        #    da atendente, e o aviso dizia "responda ao cliente"
                        #    sem dizer qual.
                        tool_args = {**tool_args, "user_query": _query_for_tool,
                                     "selected_policy_number": _ja_escolhida or None,
                                     "session_id": str(state.get("session_id") or ""),
                                     # 🔴 RODADA 2 (N1): a ULTIMA humana, separada
                                     #    da janela. A janela acha a APOLICE; a
                                     #    intencao (perguntou x pediu) tem de ser
                                     #    lida so do que o cliente acabou de dizer.
                                     "mensagem_atual": str(current_user_query or "")}
                    elif tool_name == "insurer_dispatch":
                        # SPEC-017 live-path: telefone do cliente vem da sessão
                        # WhatsApp (whatsapp:{phone}:...) — nunca da LLM.
                        tool_args = {**tool_args, "session_id": str(state.get("session_id") or "")}
                        # 🔴 Decisão do Founder (17/09): o RAMO DA APÓLICE localizada
                        #    vence o que o modelo tenha escrito — o sistema de gestão
                        #    é a fonte de verdade do ramo (D-PILOTO-11).
                        #
                        # 🔴 SPEC-117 F3.1: o ramo passa a sair da LEITURA ÚNICA da
                        #    apólice do caso, e a SEGURADORA vem com ele. Uma tecla
                        #    de URA na seguradora errada não trava: ela chega ao
                        #    segurado como "sua assistência foi aberta" e nada foi
                        #    aberto (CLAUDE.md §9.5).
                        _apolice_do_caso = await _apolice_do_caso_do_turno(
                            state, memo_da_apolice)
                        _ramo_do_sistema = str((_apolice_do_caso or {}).get("ramo") or "").strip()
                        if _ramo_do_sistema:
                            _ramo_do_modelo = str(tool_args.get("ramo_da_apolice") or "").strip()
                            if _ramo_do_modelo and _familia_do_ramo(_ramo_do_modelo) != _ramo_do_sistema:
                                # 📊 A métrica de divergência modelo × sistema.
                                logger.warning(
                                    "[APOLICE] ramo DIVERGENTE no acionamento: "
                                    "modelo=%r sistema=%r — vale o sistema",
                                    _ramo_do_modelo, _ramo_do_sistema)
                            tool_args = {**tool_args, "ramo_da_apolice": _ramo_do_sistema}
                        _seguradora_do_sistema = _chave_da_seguradora(
                            (_apolice_do_caso or {}).get("seguradora"))
                        if _seguradora_do_sistema:
                            _seguradora_do_modelo = _chave_da_seguradora(
                                tool_args.get("insurer_key"))
                            if (_seguradora_do_modelo
                                    and _seguradora_do_modelo != _seguradora_do_sistema):
                                logger.warning(
                                    "[APOLICE] seguradora DIVERGENTE no acionamento: "
                                    "modelo=%r sistema=%r — vale o sistema",
                                    _seguradora_do_modelo, _seguradora_do_sistema)
                            tool_args = {**tool_args,
                                         "insurer_key": _seguradora_do_sistema}
                    elif tool_name == "portal_action":
                        # SPEC-020: telefone do segurado vem da sessão WhatsApp
                        # (ack imediato "tô abrindo agora" antes do portal rodar).
                        tool_args = {**tool_args, "session_id": str(state.get("session_id") or "")}
                        # ═══════════════════════════════════════════════════════
                        # 🔴 SPEC-117 F3.2 — O PORTAL É DE VIDROS/AUTO, E SÓ.
                        # ═══════════════════════════════════════════════════════
                        #
                        # O número da apólice do caso passa a ir ao portal (o
                        # schema aceita: 📊 `portal_tool.py:131`,
                        # `policy_number: Optional[str]`), porque sem ele um
                        # segurado com duas apólices auto vigentes vira uma
                        # pergunta que o produto já sabia responder.
                        #
                        # ⚠️ MAS SÓ QUANDO A FAMÍLIA É `auto`. Injetar o número de
                        # uma apólice `resi`/`cond`/`empr`/`vida` faria o portal de
                        # VIDROS abrir pedido contra uma apólice RESIDENCIAL — e
                        # isso não trava: sai da corretora como pedido válido, com
                        # o contrato errado (CLAUDE.md §9.5). A constante abaixo
                        # DECIDE entre conteúdos, então a razão fica ao lado dela:
                        # o portal atendido aqui é o de vidros/lanternas, que só
                        # existe na linha de automóvel.
                        _apolice_do_caso = await _apolice_do_caso_do_turno(
                            state, memo_da_apolice)
                        _numero_da_apolice = str((_apolice_do_caso or {}).get("numapo") or "").strip()
                        _familia_da_apolice = str((_apolice_do_caso or {}).get("ramo") or "").strip()
                        if _numero_da_apolice and _familia_da_apolice == FAMILIA_DO_PORTAL:
                            _numero_do_modelo = str(tool_args.get("policy_number") or "").strip()
                            if _numero_do_modelo and _numero_do_modelo != _numero_da_apolice:
                                logger.warning(
                                    "[APOLICE] apólice DIVERGENTE no portal: "
                                    "modelo=%r sistema=%r — vale o sistema",
                                    _numero_do_modelo, _numero_da_apolice)
                            tool_args = {**tool_args, "policy_number": _numero_da_apolice}
                        elif _numero_da_apolice:
                            logger.info(
                                "[APOLICE] portal SEM número: a apólice do caso é "
                                "da família %r e o portal é de %r",
                                _familia_da_apolice, FAMILIA_DO_PORTAL)
                    elif tool_name == "delegate_to_subagent":
                        # 🤖 SubAgent: injeta contexto do orquestrador
                        delegation_config = None
                        sub_id = tool_args.get("subagent_id", "")
                        if hasattr(tool, "available_subagents"):
                            delegation_config = tool.available_subagents.get(sub_id, {})
                        max_context_chars = (
                            delegation_config.get("max_context_chars", 2000)
                            if delegation_config else 2000
                        )
                        tool_args = {
                            **tool_args,
                            "context": build_task_context(state, max_chars=max_context_chars),
                            "user_id": str(state.get("user_id", "")),
                            "session_id": str(state.get("session_id", "")),
                        }


                    # Executa a tool — REGISTRANDO a invocação no Tool Gateway.
                    #
                    # Este `with` é o elo que faltava entre o Gateway e a
                    # execução: ele decidia QUAIS ferramentas o agente recebia
                    # e depois perdia a chamada de vista. `tool_invocations`
                    # ficou em zero com o produto em uso — ver SPEC-056 e o
                    # Bloco 0 da SPEC-061.
                    #
                    # Registrar aqui, e não dentro de cada tool, é o que impede
                    # que a próxima ferramenta nasça sem auditoria: quem
                    # esquecer de instrumentar continua registrado, porque o
                    # ponto de execução é um só.
                    # 🔴 SPEC-116 U6b: anotado ANTES de executar — um turno
                    # que caiu no meio de uma ferramenta não é refeito.
                    _anotar_tool_iniciada()
                    registro = _abrir_registro_de_invocacao(
                        state, tool_name=tool_name, tool_args=tool_args)
                    with registro:
                        # Tools async-only (caminho assíncrono real). InfoCap (SPEC-014 C-FIX-1)
                        # precisa do _arun: o _run é apenas um stub que sinaliza uso async.
                        #
                        # 🔴 A LISTA ERA O DEFEITO — 18/08/2026.
                        #
                        # `request_human_agent` não estava nela. Caía no `else`,
                        # chamava `_run`, e o `_run` da HumanHandoffTool levanta
                        # RuntimeError de propósito — com uma docstring que
                        # afirmava "o tool_node já força _arun". Nenhuma linha
                        # de código fazia isso. Era um invariante escrito em
                        # comentário e nunca implementado.
                        #
                        # 📊 Custou quatro transferências falsas numa tarde: a
                        # atendente disse ao segurado "já encaminhei seu caso"
                        # quatro vezes, e o suporte nunca foi avisado. A exceção
                        # voltava ao modelo como `Erro: … o tool_node já força
                        # _arun.` — jargão de encanamento, que o modelo descarta
                        # antes de narrar o que o prompt mandou fazer.
                        #
                        # A autoridade agora é da FERRAMENTA, não desta lista: a
                        # tool declara `exige_async` e o executor obedece. Uma
                        # lista literal já esqueceu uma; ia esquecer a próxima.
                        #
                        # `hasattr(tool, "_arun")` NÃO serve de critério: o
                        # `BaseTool` do LangChain sempre tem `_arun` (o default
                        # delega para `_run` numa thread), então a condição
                        # seria sempre verdadeira e mudaria todas as tools de
                        # uma vez.
                        if (getattr(tool, "exige_async", False)
                                or tool_name in _TOOLS_SEMPRE_ASYNC) and hasattr(tool, "_arun"):
                            result = await tool._arun(**tool_args)
                        else:
                            # Execução via executor para não bloquear o event loop do FastAPI
                            loop = asyncio.get_running_loop()
                            result = await loop.run_in_executor(
                                None, lambda: tool._run(**tool_args)
                            )
                        registro.ok(result)
                    tools_used.append(tool_name)

                    # SPEC-063 Bloco S — o turno deixa MEMÓRIA.
                    #
                    # A tool de acionamento obriga o modelo a declarar 15+ campos
                    # que ele reconstrói do texto da conversa. Esses campos eram
                    # usados uma vez e jogados fora: na chamada seguinte, tudo de
                    # novo, a partir de um histórico que pode já ter perdido o
                    # começo (janela de 60 mensagens).
                    #
                    # Aqui o que o modelo declarou vira ficha. No próximo turno o
                    # grafo mostra de volta, e o cliente para de ouvir a mesma
                    # pergunta. Grava DEPOIS da execução: o que o modelo alegou
                    # numa chamada que estourou não é dado confirmado.
                    if tool_name in ("insurer_dispatch", "request_human_agent"):
                        try:
                            # 🔴 SPEC-117 F3.3/F3.4: a apólice do caso vai junto —
                            #    é ela que grava `ficha["apolice"]`, e é daí que
                            #    `human_handoff._linha_da_apolice` tira o número
                            #    que a atendente humana lê no aviso.
                            await _apolice_do_caso_do_turno(state, memo_da_apolice)
                            await _gravar_ficha_do_turno(
                                state, tool_name, tool_args, result,
                                contexto_da_apolice=memo_da_apolice.get("contexto"))
                        except Exception as _e:  # noqa: BLE001
                            logger.warning("[FICHA] turno sem memória (%s)",
                                           type(_e).__name__)

                    # Processamento de Resultado
                    if tool_name == "knowledge_base_search":
                        if isinstance(result, dict):
                            if result.get("chunks"):
                                rag_chunks.extend(result["chunks"])
                            rag_search_time += result.get("search_time_ms", 0)
                            content = json.dumps(result)
                        else:
                            content = str(result)
                    elif tool_name == "delegate_to_subagent":
                        # 🤖 SubAgent: parseia JSON, agrega tokens, captura steps
                        try:
                            sub_result = json.loads(result) if isinstance(result, str) else result
                            sub_tokens = sub_result.get("tokens_used", {})
                            delegation_tokens_input += sub_tokens.get("input", 0)
                            delegation_tokens_output += sub_tokens.get("output", 0)
                            delegation_tokens_total += sub_tokens.get("total", 0)
                            # Captura trace para internal_steps (auditoria/debug)
                            steps_log = sub_result.get("steps_log")
                            if steps_log:
                                internal_steps.append(steps_log)
                            # Retorna texto limpo para o LLM do orquestrador
                            content = sub_result.get("response", str(result))
                        except (json.JSONDecodeError, AttributeError, TypeError) as parse_err:
                            logger.warning(f"[Tool Node] SubAgent JSON parse error: {parse_err}")
                            content = str(result)
                    elif tool_name == "infocap_policy_lookup":
                        if isinstance(result, dict):
                            policy_response_contract = result.get("policy_response_contract")
                            if isinstance(policy_response_contract, dict):
                                # 🔴 RODADA 3 (B3): o SNAPSHOT das tools do
                                # turno, no instante em que o contrato nasce.
                                # É o que permite decidir por ESTADO, na
                                # invocação seguinte do grafo.
                                policy_response_contract = dict(
                                    policy_response_contract,
                                    tools_ja_usadas=[str(t) for t in tools_used])
                                policy_final_response = _guard_infocap_policy_final_response(
                                    str(result.get("content") or ""),
                                    policy_response_contract,
                                )
                            data = result.get("data") if isinstance(result.get("data"), dict) else {}
                            # 🔴 SPEC-117 F2.1: o contexto nasce com o TENANT e o
                            #    PAPEL do turno — sem tenant não nasce (§7), e o
                            #    papel decide se identidade crua pode existir nele.
                            infocap_policy_context = _safe_infocap_policy_context(
                                data,
                                company_id=str(state.get("company_id") or ""),
                                papel=_papel_do_agente(state),
                            )
                            if _policy_intelligence_v2() and str(result.get("content") or "").strip():
                                # infocap_briefing_only (SPEC-016.1 D10): a LLM recebe
                                # SÓ o briefing humanizado — nunca o JSON cru com
                                # abreviações/termos internos da fonte.
                                content = str(result.get("content"))
                            else:
                                content = json.dumps(result, ensure_ascii=False, default=str)
                        else:
                            content = str(result)
                    else:
                        content = str(result)

                    tool_results.append(
                        ToolMessage(
                            content=content, tool_call_id=tool_call_id, name=tool_name
                        )
                    )

                except Exception as e:
                    logger.error(f"[Tool Node] Erro na tool {tool_name}: {e}")
                    # 🔴 Erro de ferramenta que o segurado ESTÁ ESPERANDO tem de
                    # falar a língua do atendimento, não a do encanamento.
                    #
                    # `Erro: HumanHandoffTool exige execução assíncrona (_arun)`
                    # foi o texto que o modelo recebeu quatro vezes em 17/08 —
                    # e quatro vezes ele o descartou e disse ao cliente que
                    # tinha encaminhado. Uma mensagem que não diz o que NÃO
                    # aconteceu vira permissão para inventar que aconteceu.
                    conteudo_do_erro = (
                        FALHA_DO_HANDOFF.format(motivo=str(e)[:200])
                        if tool_name in _TOOLS_DE_HANDOFF
                        else f"Erro: {str(e)}"
                    )
                    tool_results.append(
                        ToolMessage(
                            content=conteudo_do_erro,
                            tool_call_id=tool_call_id,
                            name=tool_name,
                        )
                    )

    return_dict = {
        "messages": tool_results,
        "tools_used": tools_used,
        "rag_chunks": rag_chunks,
        "rag_search_time_ms": rag_search_time,
    }

    # SubAgent tokens são logados separadamente no conversation_logs do SubAgent
    # (billing independente). Apenas log informativo.
    if delegation_tokens_total > 0:
        logger.info(
            f"[Tool Node] 🤖 SubAgent tokens (logados separadamente): "
            f"+{delegation_tokens_total} total"
        )

    # Persist internal_steps se houve delegação
    if internal_steps:
        return_dict["internal_steps"] = internal_steps

    # 🔴 RODADA 3 (B3): o consumo é por ESTADO — ver `_consumir_regua_apos_acao`.
    #    Aqui ele cobre a MESMA invocação (a ação que rodou depois da consulta
    #    no mesmo `tool_node`); a invocação SEGUINTE é coberta no `agent_node`,
    #    onde o guarda pós-LLM é aplicado.
    if isinstance(policy_response_contract, dict):
        _antes = policy_response_contract
        policy_response_contract = _consumir_regua_apos_acao(
            policy_response_contract, tools_used)
        if policy_response_contract is not _antes:
            policy_final_response = _guard_infocap_policy_final_response(
                str(policy_final_response or ""), policy_response_contract)

    if policy_response_contract and policy_final_response:
        return_dict["policy_response_contract"] = policy_response_contract
        # SPEC-016.1 D7: com v2, a LLM redige a resposta final (o guard pós-LLM
        # fiscaliza). Só identity_mismatch encerra direto com o texto seguro.
        if not _policy_intelligence_v2() or policy_response_contract.get("result_kind") == "identity_mismatch":
            return_dict["final_response"] = policy_final_response
    merged_context = _merge_infocap_policy_context(
        memo_da_apolice.get("contexto", state.get("infocap_policy_context")),
        infocap_policy_context)
    if merged_context:
        return_dict["infocap_policy_context"] = merged_context
        if infocap_policy_context:
            # 🔴 SPEC-117 F2.3/G8: a apólice que este turno ENCONTROU vira memória
            #    durável. Só quando nasceu contexto novo — gravar a cada turno
            #    seria um UPDATE por mensagem, sem nenhum fato novo.
            await _gravar_apolice_do_caso(state, merged_context)

    return return_dict




def log_node(state: AgentState, supabase_client, rota: Optional[dict] = None) -> dict:
    """
    Nó de Logging - Salva métricas na tabela conversation_logs.
    """
    logger.info("[Log Node] Salvando métricas...")

    try:
        user_question = ""
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage) or (
                hasattr(msg, "type") and msg.type == "human"
            ):
                user_question = msg.content
                break

        final_response = state.get("final_response", "")
        # Tenta extrair da última mensagem se não estiver no state
        if not final_response:
            for msg in reversed(state["messages"]):
                if isinstance(msg, AIMessage) or (
                    hasattr(msg, "type") and msg.type == "ai"
                ):
                    final_response = extract_text_from_content(msg.content)
                    break

        rag_chunks = state.get("rag_chunks", [])

        # Tenta extrair métricas de busca das tool messages
        search_strategy = None
        retrieval_score = None
        for msg in state["messages"]:
            if hasattr(msg, "type") and msg.type == "tool":
                try:
                    c = json.loads(msg.content)
                    if isinstance(c, dict):
                        if "strategy" in c:
                            search_strategy = c["strategy"]
                        if "max_score" in c:
                            retrieval_score = float(c["max_score"])
                except Exception:
                    continue

        # Fallback (41C.1.2): sem tool_call, usa as métricas do RAG prefetch.
        if search_strategy is None:
            search_strategy = state.get("search_strategy")
        if retrieval_score is None and state.get("retrieval_score") is not None:
            try:
                retrieval_score = float(state.get("retrieval_score"))
            except (TypeError, ValueError):
                pass

        agent_data = state.get("agent_data") or {}
        agent_id = agent_data.get("id") if agent_data else None
        company_config = state.get("company_config") or {}

        # 🔴 SPEC-116 (conserto, red team P4 — CLAUDE.md §12.1): o provedor que
        # RESPONDEU (`response_metadata.model_provider`), senão o da ROTA
        # resolvida; o gravado só sem rota. Era `gravado or "openai"`: agente
        # NULO falando com a Anthropic ficava registrado como OpenAI.
        llm_provider = _provedor_que_respondeu(state.get("messages") or []) or \
            _provedor_do_turno(rota, agent_data, company_config, padrao="desconhecido")
        # 🔴 SPEC-116 U7 (CLAUDE.md §12.1, o corolário do campo que mente): o
        # rótulo era o CONFIGURADO, com um default inventado quando faltava. Agora
        # é o modelo que RESPONDEU, lido da última resposta; sem ela, o
        # configurado; sem nenhum, "desconhecido" (📊 `conversation_logs.llm_model`
        # é NOT NULL) — nunca um nome de modelo que não rodou.
        llm_model = _modelo_que_respondeu(state.get("messages") or []) or \
            agent_data.get("llm_model") or company_config.get("llm_model") or "desconhecido"
        llm_temperature = agent_data.get("llm_temperature") or company_config.get("llm_temperature") or 0.7

        # Convert UUIDs to strings for JSON serialization
        company_id_str = str(state["company_id"]) if state.get("company_id") else None
        user_id_str = str(state["user_id"]) if state.get("user_id") else None
        session_id_str = str(state["session_id"]) if state.get("session_id") else None

        log_data = {
            "company_id": company_id_str,
            "user_id": user_id_str,
            "session_id": session_id_str,
            "agent_id": str(agent_id) if agent_id else None,
            "user_question": user_question,
            "assistant_response": str(final_response),
            "rag_chunks": rag_chunks,
            "rag_chunks_count": len(rag_chunks),
            "tokens_input": state.get("tokens_input", 0),
            "tokens_output": state.get("tokens_output", 0),
            "tokens_total": state.get("tokens_total", 0),
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "llm_temperature": float(llm_temperature),
            "response_time_ms": state.get("llm_response_time_ms", 0),
            "rag_search_time_ms": state.get("rag_search_time_ms", 0),
            "search_strategy": search_strategy,
            "retrieval_score": retrieval_score,
            "status": "success",
        }

        # SubAgent delegation logs (se houve)
        internal_steps = state.get("internal_steps")
        if internal_steps:
            log_data["internal_steps"] = internal_steps

        # Unwrap: get real client if wrapper is passed
        real_client = supabase_client.client if hasattr(supabase_client, "client") else supabase_client
        real_client.table("conversation_logs").insert(log_data).execute()
        logger.info("[Log Node] Log salvo com sucesso")

    except Exception as e:
        logger.error(f"[Log Node] Erro ao salvar log: {e}")

    return {}


def _provedor_do_turno(rota: Optional[dict], agent_data: dict, company_config: dict,
                       padrao: str = "openai") -> str:
    """O provedor para onde a chamada do turno VAI: o da rota resolvida.

    O gravado (agente → corretora) só vale para chamador que não passa `rota`.
    """
    return ((rota or {}).get("provedor") or (agent_data or {}).get("llm_provider")
            or (company_config or {}).get("llm_provider") or padrao)


def _provedor_que_respondeu(mensagens: list) -> Optional[str]:
    for msg in reversed(mensagens):
        if isinstance(msg, AIMessage) or getattr(msg, "type", None) == "ai":
            meta = getattr(msg, "response_metadata", None) or {}
            if meta.get("model_provider"):
                return str(meta["model_provider"])
            if meta.get("model_name") or meta.get("model"):
                return None  # respondeu sem dizer o provedor: vale a rota
    return None


def _modelo_que_respondeu(mensagens: list) -> Optional[str]:
    for msg in reversed(mensagens):
        if isinstance(msg, AIMessage) or getattr(msg, "type", None) == "ai":
            meta = getattr(msg, "response_metadata", None) or {}
            modelo = meta.get("model_name") or meta.get("model")
            if modelo:
                return str(modelo)
    return None


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """Função de roteamento"""
    messages = state["messages"]
    last_message = messages[-1]

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        logger.info("[Router] Direcionando para TOOLS")
        return "tools"

    logger.info("[Router] Direcionando para END")
    return "end"
