"""
Funções utilitárias para o agente LangGraph.
Extrai lógica de sanitização e processamento de mensagens.
"""

import logging
from typing import Any, Dict

from langchain_core.messages import AIMessage

logger = logging.getLogger(__name__)

#: Os tipos de bloco que CARREGAM TEXTO PARA O USUÁRIO.
#:
#: 📊 `output_text` é a forma da Responses API da OpenAI, e ela devolvia `""`
#:    aqui — medido em 28/09/2026. Blocos de `reasoning`, `tool_use`,
#:    `thinking` e afins continuam FORA de propósito: eles não são resposta.
_TIPOS_DE_TEXTO = ("text", "output_text")


def extract_text_from_content(content: Any) -> str:
    """Extrai o texto limpo de um conteúdo que pode ser string ou lista de blocos.

    Modelos de reasoning (o1, o3, GPT-5, Claude) devolvem lista com blocos de
    tipos diferentes. Esta função devolve só o texto final.

    ═══════════════════════════════════════════════════════════════════════════
    🔴 O `str(content)` FINAL ERA O DEFEITO — SPEC-119, conserto B, item 7
    ═══════════════════════════════════════════════════════════════════════════

    📊 Medido em 28/09/2026, antes do conserto::

        bloco sem `type`          [{"text": "1"}]                     -> ""
        Responses API da OpenAI   [{"type":"output_text","text":"1"}] -> ""
        bloco `text` sem `text`   [{"type":"text"}]                   -> ""
        🔴 um DICT, não lista     {"type":"text","text":"1"}
                                  -> "{'type': 'text', 'text': '1'}"

    A última linha é a cara: o `repr` é CURTO, então o fiscal da fase humana
    (`guard_human_phase_reply`) o aprovava, e o `repr` de um objeto Python ia
    para a URA da seguradora no lugar da resposta.

    🔴 **Nunca serializar objeto para a URA.** O caminho desconhecido devolve
    `""` e GRITA no log: string vazia o fiscal recusa (falha fechada); `repr`
    ele aceita (falha aberta), e a falha aberta chega ao segurado.
    """
    if content is None:
        return ""

    if isinstance(content, str):
        return content

    if isinstance(content, dict):
        content = [content]

    if isinstance(content, list):
        text_parts = []
        for block in content:
            if isinstance(block, str):
                text_parts.append(block)
                continue
            if not isinstance(block, dict):
                continue
            tipo = block.get("type")
            # ⚠️ Bloco SEM `type` mas COM `text` é texto: é a forma que alguns
            #    adaptadores devolvem, e devolvia "" (medido em 28/09/2026).
            if tipo in _TIPOS_DE_TEXTO or (tipo is None and "text" in block):
                texto = block.get("text")
                if isinstance(texto, str):
                    text_parts.append(texto)
        return "".join(text_parts)

    logger.error("[AGENTS] conteúdo de tipo %s não é texto e NÃO será "
                 "serializado — a resposta sai vazia de propósito",
                 type(content).__name__)
    return ""


def extract_token_usage(response: AIMessage) -> Dict[str, int]:
    """
    Extrai informações de uso de tokens da resposta do LLM.

    Suporta múltiplos formatos:
    - usage_metadata (LangChain moderno / GPT-5 / o1)
    - response_metadata.token_usage (formato antigo)
    - response_metadata.usage (alternativo)

    Args:
        response: Mensagem de resposta do LLM

    Returns:
        Dict com tokens_input, tokens_output, tokens_total, reasoning_tokens
    """
    tokens = {
        "tokens_input": 0,
        "tokens_output": 0,
        "tokens_total": 0,
        "reasoning_tokens": 0,
    }

    # Tenta usage_metadata (Padrão Novo - GPT-5/o1/LangChain Moderno)
    usage_meta = getattr(response, "usage_metadata", {}) or {}
    if usage_meta:
        tokens["tokens_input"] = usage_meta.get("input_tokens", 0)
        tokens["tokens_output"] = usage_meta.get("output_tokens", 0)
        tokens["tokens_total"] = usage_meta.get(
            "total_tokens", tokens["tokens_input"] + tokens["tokens_output"]
        )

        # Reasoning tokens (modelos o1/o3/GPT-5)
        out_details = usage_meta.get("output_token_details") or {}
        tokens["reasoning_tokens"] = out_details.get("reasoning_tokens", 0)
        return tokens

    # Fallback para response_metadata (Padrão Antigo)
    raw_meta = getattr(response, "response_metadata", {}) or {}
    if raw_meta:
        usage = raw_meta.get("token_usage") or raw_meta.get("usage") or {}
        if usage:
            tokens["tokens_input"] = usage.get("prompt_tokens", 0)
            tokens["tokens_output"] = usage.get("completion_tokens", 0)
            tokens["tokens_total"] = usage.get(
                "total_tokens", tokens["tokens_input"] + tokens["tokens_output"]
            )

            # Reasoning tokens (formato antigo)
            details = usage.get("completion_tokens_details") or {}
            tokens["reasoning_tokens"] = details.get("reasoning_tokens", 0)

    return tokens


def sanitize_ai_message(msg: AIMessage) -> AIMessage:
    """
    Sanitiza uma AIMessage removendo blocos de reasoning.

    Necessário porque a API OpenAI retorna erro 400 se enviarmos
    blocos de reasoning de volta no histórico.

    Args:
        msg: Mensagem AI original (pode ter content como lista)

    Returns:
        Nova AIMessage com content como string limpa
    """
    clean_content = extract_text_from_content(msg.content)
    clean_msg = AIMessage(content=clean_content)

    # Preserva tool_calls (necessário para o fluxo)
    if hasattr(msg, "tool_calls") and msg.tool_calls:
        clean_msg.tool_calls = msg.tool_calls

    return clean_msg
