"""Identidade de marca da corretora — SPEC-057 Bloco A.

Toda peça que a AutoBrokers entrega em nome de uma corretora precisa parecer
propriedade dela. Este pacote transforma "o site da minha corretora" em um
sistema de design completo, conferido e com procedência.
"""

from .capture import BrandCaptureService
from .color import contrast_ratio, ensure_contrast, parse_color, to_hex, tonal_scale
from .extract import LogoAnalysis, analisar_logo
from .system import FALLBACK_ACENTO, FALLBACK_PRIMARIA, build_design_system, to_css_variables

__all__ = [
    "BrandCaptureService",
    "LogoAnalysis",
    "analisar_logo",
    "build_design_system",
    "to_css_variables",
    "contrast_ratio",
    "ensure_contrast",
    "parse_color",
    "to_hex",
    "tonal_scale",
    "FALLBACK_PRIMARIA",
    "FALLBACK_ACENTO",
]
