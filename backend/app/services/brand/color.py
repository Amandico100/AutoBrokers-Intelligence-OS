"""Ciência de cor para identidade de marca. SPEC-057 §Bloco A.

Por que OKLab e não HSL
-----------------------
HSL é barato e mente. Em HSL, amarelo e azul com o mesmo `L` têm brilho
percebido completamente diferente — clarear uma paleta em HSL produz degraus
que parecem irregulares mesmo estando matematicamente equidistantes. OKLab é
perceptualmente uniforme: mover L de 0.5 para 0.6 muda o brilho aparente na
mesma medida em qualquer matiz.

É essa diferença que separa uma escala que **parece desenhada** de uma que
parece calculada. Como toda peça que entregamos nasce de uma cor que o corretor
não escolheu para ser usada assim, a escala precisa ser boa sozinha.

E há um problema concreto que só aparece com marca real: o laranja da Resulta
(#EE7501) tem contraste 2.92:1 no branco. Reprova AA. Usar a cor da marca crua
como texto entregaria relatório ilegível — com a desculpa de "respeitar a
marca". A marca se respeita mantendo o matiz e ajustando a luminosidade até o
texto poder ser lido.

Sem dependências: matriz e cbrt bastam.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Iterable, Optional

# --------------------------------------------------------------------------
# sRGB ↔ linear
# --------------------------------------------------------------------------

def _srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(c: float) -> float:
    return c * 12.92 if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if v < lo else (hi if v > hi else v)


# --------------------------------------------------------------------------
# Parsing / formatação
# --------------------------------------------------------------------------

_HEX_RE = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_RGB_RE = re.compile(
    r"rgba?\(\s*(\d{1,3})\s*[, ]\s*(\d{1,3})\s*[, ]\s*(\d{1,3})", re.I
)


def parse_color(value: str) -> Optional[tuple[int, int, int]]:
    """Aceita `#abc`, `#aabbcc`, `#aabbccdd`, `rgb(...)`, `rgba(...)`.

    Devolve `None` no que não reconhece — cor inválida vinda de CSS de terceiro
    é o caso comum, não a exceção, e adivinhar aqui contamina a paleta.
    """
    if not value:
        return None
    v = value.strip()

    m = _RGB_RE.search(v)
    if m:
        r, g, b = (int(m.group(i)) for i in (1, 2, 3))
        if max(r, g, b) > 255:
            return None
        return r, g, b

    m = _HEX_RE.match(v)
    if not m:
        return None
    h = m.group(1)
    if len(h) in (3, 4):
        h = "".join(c * 2 for c in h[:3])
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*(max(0, min(255, int(round(c)))) for c in rgb))


# --------------------------------------------------------------------------
# OKLab / OKLCH
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class OKLCH:
    L: float   # 0..1  luminosidade percebida
    C: float   # 0..~0.4 croma
    H: float   # 0..360 matiz

    def with_L(self, L: float) -> "OKLCH":
        return OKLCH(_clamp(L), self.C, self.H)

    def with_C(self, C: float) -> "OKLCH":
        return OKLCH(self.L, max(0.0, C), self.H)


def rgb_to_oklch(rgb: tuple[int, int, int]) -> OKLCH:
    r, g, b = (_srgb_to_linear(c / 255.0) for c in rgb)

    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b

    l_, m_, s_ = (math.copysign(abs(v) ** (1 / 3), v) for v in (l, m, s))

    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_

    C = math.hypot(a, bb)
    H = math.degrees(math.atan2(bb, a)) % 360.0
    return OKLCH(L, C, H)


def oklch_to_rgb(c: OKLCH) -> tuple[int, int, int]:
    a = c.C * math.cos(math.radians(c.H))
    b = c.C * math.sin(math.radians(c.H))

    l_ = c.L + 0.3963377774 * a + 0.2158037573 * b
    m_ = c.L - 0.1055613458 * a - 0.0638541728 * b
    s_ = c.L - 0.0894841775 * a - 1.2914855480 * b

    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3

    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bl = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s

    return tuple(  # type: ignore[return-value]
        int(round(_clamp(_linear_to_srgb(_clamp(v, -1.0, 2.0))) * 255))
        for v in (r, g, bl)
    )


def in_gamut(c: OKLCH) -> bool:
    """Se a conversão de volta não bate, a cor não existe em sRGB."""
    rgb = oklch_to_rgb(c)
    back = rgb_to_oklch(rgb)
    return abs(back.C - c.C) < 0.012 and abs(back.L - c.L) < 0.012


def fit_gamut(c: OKLCH) -> OKLCH:
    """Reduz croma até a cor caber em sRGB, preservando L e matiz.

    Preserva luminosidade porque é ela que carrega a legibilidade; croma é o que
    se pode ceder sem quebrar o texto.
    """
    if in_gamut(c):
        return c
    lo, hi = 0.0, c.C
    for _ in range(20):
        mid = (lo + hi) / 2
        if in_gamut(c.with_C(mid)):
            lo = mid
        else:
            hi = mid
    return c.with_C(lo)


# --------------------------------------------------------------------------
# Contraste WCAG
# --------------------------------------------------------------------------

def relative_luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = (_srgb_to_linear(c / 255.0) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    la, lb = relative_luminance(a), relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


AA_TEXT = 4.5
AA_LARGE = 3.0
AAA_TEXT = 7.0


def ensure_contrast(
    color: tuple[int, int, int],
    background: tuple[int, int, int],
    target: float = AA_TEXT,
) -> tuple[int, int, int]:
    """Ajusta a luminosidade até atingir o contraste alvo. Matiz preservado.

    Este é o método que torna seguro usar cor de marca em texto. O laranja da
    Resulta continua laranja da Resulta — só escurece o suficiente para ser
    lido. É o oposto de trocar a cor por uma "acessível" genérica, que
    descaracteriza a marca para resolver o problema.
    """
    if contrast_ratio(color, background) >= target:
        return color

    c = rgb_to_oklch(color)
    bg_lum = relative_luminance(background)
    escurecer = bg_lum > 0.35   # fundo claro → texto precisa ir para baixo

    lo, hi = (0.0, c.L) if escurecer else (c.L, 1.0)
    melhor = oklch_to_rgb(fit_gamut(c.with_L(0.0 if escurecer else 1.0)))

    for _ in range(24):
        mid = (lo + hi) / 2
        cand = oklch_to_rgb(fit_gamut(c.with_L(mid)))
        if contrast_ratio(cand, background) >= target:
            melhor = cand
            # aproxima do original mantendo o alvo: menos distorção de marca
            if escurecer:
                lo = mid
            else:
                hi = mid
        else:
            if escurecer:
                hi = mid
            else:
                lo = mid

    return melhor


def readable_on(background: tuple[int, int, int]) -> tuple[int, int, int]:
    """Preto ou branco — o que ler melhor sobre este fundo."""
    return (0, 0, 0) if contrast_ratio((0, 0, 0), background) >= contrast_ratio((255, 255, 255), background) else (255, 255, 255)


# --------------------------------------------------------------------------
# Escala tonal
# --------------------------------------------------------------------------

# Luminosidades-alvo. Não é linear de propósito: o olho enxerga mais degraus na
# faixa clara, então os passos abrem conforme escurece.
_ESCALA_L = {
    50: 0.972, 100: 0.940, 200: 0.882, 300: 0.812, 400: 0.724,
    500: 0.638, 600: 0.556, 700: 0.472, 800: 0.386, 900: 0.302, 950: 0.226,
}

# Croma cai nos extremos. Croma cheio em tom muito claro ou muito escuro fica
# fluorescente — nenhum sistema de design sério mantém.
_ESCALA_C = {
    50: 0.22, 100: 0.36, 200: 0.56, 300: 0.76, 400: 0.92,
    500: 1.00, 600: 0.98, 700: 0.90, 800: 0.78, 900: 0.64, 950: 0.50,
}


def tonal_scale(base: tuple[int, int, int]) -> dict[int, str]:
    """Escala 50–950 a partir de uma cor, em OKLCH."""
    c = rgb_to_oklch(base)
    croma_ref = max(c.C, 0.02)
    saida: dict[int, str] = {}
    for passo, L in _ESCALA_L.items():
        alvo = OKLCH(L, croma_ref * _ESCALA_C[passo], c.H)
        saida[passo] = to_hex(oklch_to_rgb(fit_gamut(alvo)))
    return saida


def nearest_step(base: tuple[int, int, int]) -> int:
    """Onde a cor original cai na própria escala — usado para não duplicar tom."""
    L = rgb_to_oklch(base).L
    return min(_ESCALA_L, key=lambda k: abs(_ESCALA_L[k] - L))


# --------------------------------------------------------------------------
# Harmonia
# --------------------------------------------------------------------------

MAX_DESVIO_SEMANTICO = 12.0


def nudge_hue(alvo_h: float, marca_h: float, forca: float = 0.30,
              limite: float = MAX_DESVIO_SEMANTICO) -> float:
    """Aproxima um matiz canônico do matiz da marca — com teto.

    O teto não é detalhe de acabamento, é o que mantém o significado. Sem ele,
    uma marca azul (H≈250) puxando o vermelho de erro (H=27) pelo caminho mais
    curto atravessa o **magenta**: sai um malva que ninguém lê como perigo.
    Vermelho tem de continuar vermelho; a harmonização é um empurrão para o
    conjunto parecer da mesma família, não uma mistura de verdade.
    """
    delta = ((marca_h - alvo_h + 180) % 360) - 180
    deslocamento = max(-limite, min(limite, delta * forca))
    return (alvo_h + deslocamento) % 360


def semantic_color(alvo_h: float, marca_h: float, *, L: float, C: float,
                   forca: float = 0.30) -> tuple[int, int, int]:
    """Cor semântica com luminosidade e croma próprios, matiz levemente da casa.

    A luminosidade **não** pode ser herdada da marca: com um marinho escuro, o
    verde de "positivo" sairia quase preto e deixaria de comunicar. O que a
    marca empresta é o matiz; o resto é função da legibilidade.
    """
    return oklch_to_rgb(fit_gamut(OKLCH(L, C, nudge_hue(alvo_h, marca_h, forca))))


def harmonize(base: tuple[int, int, int], alvo_h: float, forca: float = 0.35) -> str:
    """Compatibilidade: matiz aproximado da marca, preservando L e C da base."""
    b = rgb_to_oklch(base)
    return to_hex(oklch_to_rgb(fit_gamut(OKLCH(b.L, b.C, nudge_hue(alvo_h, b.H, forca)))))


def is_neutral(rgb: tuple[int, int, int], limiar: float = 0.045) -> bool:
    """Cinza, preto e branco não são cor de marca — são fundo e tinta."""
    return rgb_to_oklch(rgb).C < limiar


def distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    """Distância perceptual em OKLab. Usada para deduplicar cores parecidas."""
    ca, cb = rgb_to_oklch(a), rgb_to_oklch(b)
    aa = ca.C * math.cos(math.radians(ca.H)), ca.C * math.sin(math.radians(ca.H))
    ab = cb.C * math.cos(math.radians(cb.H)), cb.C * math.sin(math.radians(cb.H))
    return math.sqrt((ca.L - cb.L) ** 2 + (aa[0] - ab[0]) ** 2 + (aa[1] - ab[1]) ** 2)


def dedupe(cores: Iterable[tuple[int, int, int]], limiar: float = 0.06
           ) -> list[tuple[int, int, int]]:
    """Remove cores perceptualmente iguais, preservando a ordem de entrada."""
    saida: list[tuple[int, int, int]] = []
    for c in cores:
        if all(distance(c, j) > limiar for j in saida):
            saida.append(c)
    return saida


# --------------------------------------------------------------------------
# Cores que parecem de marca e não são
# --------------------------------------------------------------------------

# Paleta padrão do editor de blocos do WordPress. Está em milhares de sites que
# nunca a usaram — é cor do editor, não da corretora. O site real da Resulta
# devolveu exatamente estas oito no CSS, e nenhuma cor da marca. Sem esta lista,
# toda corretora em WordPress ganharia a mesma identidade rosa-e-âmbar.
PALETA_EDITOR_WORDPRESS = frozenset({
    "#F78DA7", "#CF2E2E", "#FF6900", "#FCB900", "#7BDCB5", "#00D084",
    "#8ED1FC", "#0693E3", "#ABB8C3", "#EEEEEE", "#313131", "#9B51E0",
})

# Cores de botão de rede social. Aparecem em quase todo site e pertencem à
# plataforma, não a quem hospeda o botão.
CORES_DE_TERCEIROS = frozenset({
    "#25D366", "#128C7E",              # WhatsApp
    "#1877F2", "#4267B2",              # Facebook
    "#E4405F", "#C13584",              # Instagram
    "#0A66C2", "#0077B5",              # LinkedIn
    "#FF0000",                          # YouTube
    "#1DA1F2", "#000000",              # X/Twitter
})


def cores_css_confiaveis(brutas: Iterable[str]) -> list[str]:
    """Filtra o que é cor de editor, de rede social ou neutro.

    O que sobra ainda é sinal fraco — CSS de tema pronto raramente carrega a
    marca — mas deixa de ser ruidoso a ponto de inventar uma identidade.
    """
    saida: list[str] = []
    for bruta in brutas or []:
        rgb = parse_color(bruta)
        if not rgb:
            continue
        hexa = to_hex(rgb)
        if hexa in PALETA_EDITOR_WORDPRESS or hexa in CORES_DE_TERCEIROS:
            continue
        if is_neutral(rgb):
            continue
        if hexa not in saida:
            saida.append(hexa)
    return saida
