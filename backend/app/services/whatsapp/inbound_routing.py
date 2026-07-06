"""Precedencia de conteudo inbound do WhatsApp (ZAPI/Evolution unificados).

Bug de campo (founder 2026-07-05): imagem enviada COM legenda tinha a legenda
tratada como texto e o branch de imagem era pulado -> o atendente perdia a
imagem (final_image_url None, describe_image nunca rodava, image_url null no
banco). A imagem tem que vencer o texto/legenda.

Puro de proposito (sem imports) para teste house-style isolado.
"""

from __future__ import annotations


def pick_inbound_branch(
    *, has_combined: bool, has_audio: bool, has_image: bool, has_text: bool
) -> str:
    """Qual tipo de conteudo processar no webhook. Ordem de precedencia:
    combined > audio > image > text.

    Image ANTES de text de proposito: a legenda de uma imagem NAO pode esconder
    a imagem (senao o atendente fica cego a foto/documento do segurado). audio
    fica antes de image por comportamento historico (audio raramente vem junto
    com imagem no mesmo evento).
    """
    if has_combined:
        return "combined"
    if has_audio:
        return "audio"
    if has_image:
        return "image"
    if has_text:
        return "text"
    return "none"
