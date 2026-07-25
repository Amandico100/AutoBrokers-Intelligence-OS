"""Artifact Hub — o resultado como objeto de primeira classe. SPEC-057.

Texto some no scroll. Um artefato tem dono, versão, marca congelada,
procedência e validade — e pode ser aberto por quem nunca entrou no produto.
"""

from .render import render_html, render_texto_whatsapp
from .styles import ESTILOS, css_do_estilo, tema_do_estilo
from .templates import CATALOGO, POR_CHAVE, Template, escolher

__all__ = [
    "render_html", "render_texto_whatsapp",
    "css_do_estilo", "tema_do_estilo", "ESTILOS",
    "CATALOGO", "POR_CHAVE", "Template", "escolher",
]
