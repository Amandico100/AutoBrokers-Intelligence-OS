"""Sistema de design derivado da marca da corretora. SPEC-057 §Bloco A.

Entra: uma ou duas cores extraídas do logo.
Sai: o conjunto completo de tokens que qualquer peça precisa — superfícies,
tinta, bordas, semânticos, séries de gráfico — em tema claro e escuro, com
contraste conferido.

O que este módulo protege
-------------------------
Um relatório é lido em tela, impresso, projetado e reencaminhado por WhatsApp.
Uma paleta que só funciona na tela do autor é uma paleta que falha na reunião.
Por isso três regras entram no cálculo, não na revisão:

1. Todo par tinta/fundo passa por `ensure_contrast`. Nenhum texto sai abaixo de
   AA. A cor da marca é preservada no matiz e ajustada na luminosidade.

2. As séries de gráfico variam em matiz **e** em luminosidade. Duas séries
   vizinhas nunca têm o mesmo tom — então o gráfico continua legível impresso
   em preto e branco e para quem não distingue vermelho de verde. Cor sozinha
   nunca é o único canal de informação.

3. Verde e vermelho são puxados na direção da marca. Semântico genérico ao lado
   de marca forte parece adesivo colado.
"""

from __future__ import annotations

from typing import Optional

from .color import (
    AA_LARGE,
    AA_TEXT,
    AAA_TEXT,
    OKLCH,
    contrast_ratio,
    ensure_contrast,
    fit_gamut,
    is_neutral,
    nearest_step,
    oklch_to_rgb,
    parse_color,
    readable_on,
    relative_luminance,
    rgb_to_oklch,
    semantic_color,
    to_hex,
    tonal_scale,
)

# Matizes-âncora dos semânticos, em OKLCH. Reconhecíveis universalmente.
_H_POSITIVO = 148.0
_H_NEGATIVO = 27.0
_H_ATENCAO = 75.0
_H_INFO = 245.0

# Fundos de referência
_BRANCO = (255, 255, 255)
_PRETO = (10, 11, 13)

FALLBACK_PRIMARIA = "#2C6E8F"   # azul-petróleo sóbrio: neutro para seguros,
FALLBACK_ACENTO = "#D98324"     # e um âmbar que não compete com ele.


def _rgb(v: str | tuple[int, int, int] | None, padrao: tuple[int, int, int]) -> tuple[int, int, int]:
    if isinstance(v, tuple):
        return v
    return parse_color(v or "") or padrao


def _serie_grafico(base: tuple[int, int, int], n: int, escuro: bool) -> list[str]:
    """Séries distinguíveis por matiz E por luminosidade.

    O passo de matiz é irregular de propósito: 360/n distribui bonito num
    círculo cromático e péssimo num gráfico, porque joga séries em faixas de
    matiz onde o olho humano discrimina mal (a região amarelo-verde). O passo
    aqui abre mais onde a discriminação é boa.
    """
    b = rgb_to_oklch(base)
    croma = max(b.C, 0.09)

    # Deslocamentos escolhidos a mão: análogos primeiro (parecem da mesma
    # família), depois saltos maiores conforme precisa de mais séries.
    saltos = [0, 195, 42, 258, 96, 150, 312, 21, 225, 69, 285, 126]
    # Luminosidade alterna alto/baixo — é o que sobrevive à impressão P&B.
    if escuro:
        niveis = [0.72, 0.58, 0.80, 0.50, 0.66, 0.86]
    else:
        niveis = [0.56, 0.70, 0.44, 0.78, 0.62, 0.36]

    saida: list[str] = []
    for i in range(n):
        h = (b.H + saltos[i % len(saltos)]) % 360
        L = niveis[i % len(niveis)]
        # Primeira série é a marca quase pura: o gráfico abre na cor da casa.
        c = croma if i else max(croma, b.C)
        saida.append(to_hex(oklch_to_rgb(fit_gamut(OKLCH(L, c, h)))))
    return saida


def _tema(
    primaria: tuple[int, int, int],
    acento: tuple[int, int, int],
    *,
    escuro: bool,
) -> dict:
    """Um tema completo (claro ou escuro) a partir das duas cores da marca."""
    p = rgb_to_oklch(primaria)

    if escuro:
        # Superfícies escuras levemente tingidas com o matiz da marca. Cinza
        # neutro puro em tema escuro parece morto; 0.012 de croma é o
        # suficiente para o preto "pertencer" à marca sem virar colorido.
        canvas = oklch_to_rgb(fit_gamut(OKLCH(0.155, 0.012, p.H)))
        surface = oklch_to_rgb(fit_gamut(OKLCH(0.205, 0.014, p.H)))
        surface_2 = oklch_to_rgb(fit_gamut(OKLCH(0.253, 0.016, p.H)))
        elevated = oklch_to_rgb(fit_gamut(OKLCH(0.300, 0.018, p.H)))
        ink_forte = oklch_to_rgb(fit_gamut(OKLCH(0.972, 0.006, p.H)))
        ink_base = oklch_to_rgb(fit_gamut(OKLCH(0.900, 0.008, p.H)))
        ink_suave = oklch_to_rgb(fit_gamut(OKLCH(0.735, 0.012, p.H)))
        ink_tenue = oklch_to_rgb(fit_gamut(OKLCH(0.590, 0.012, p.H)))
        borda = oklch_to_rgb(fit_gamut(OKLCH(0.320, 0.016, p.H)))
        borda_forte = oklch_to_rgb(fit_gamut(OKLCH(0.420, 0.020, p.H)))
    else:
        canvas = oklch_to_rgb(fit_gamut(OKLCH(0.994, 0.003, p.H)))
        surface = _BRANCO
        surface_2 = oklch_to_rgb(fit_gamut(OKLCH(0.972, 0.008, p.H)))
        elevated = _BRANCO
        ink_forte = oklch_to_rgb(fit_gamut(OKLCH(0.225, 0.022, p.H)))
        ink_base = oklch_to_rgb(fit_gamut(OKLCH(0.330, 0.018, p.H)))
        ink_suave = oklch_to_rgb(fit_gamut(OKLCH(0.520, 0.014, p.H)))
        ink_tenue = oklch_to_rgb(fit_gamut(OKLCH(0.645, 0.012, p.H)))
        borda = oklch_to_rgb(fit_gamut(OKLCH(0.912, 0.010, p.H)))
        borda_forte = oklch_to_rgb(fit_gamut(OKLCH(0.845, 0.014, p.H)))

    # O texto não vive num fundo só: ele cai em canvas, em card e em painel
    # elevado. Ajustar o contraste contra o fundo médio produz texto que passa
    # na auditoria e falha justamente no card, onde ele de fato aparece.
    # Referência = o PIOR caso, ou seja, o fundo mais próximo do texto em
    # luminância: o mais claro no tema escuro, o mais escuro no tema claro.
    candidatos = [canvas, surface, surface_2, elevated]
    fundo_ref = (max if escuro else min)(candidatos, key=relative_luminance)

    # Marca aplicada a texto e a preenchimento são coisas diferentes. O
    # preenchimento pode usar a cor crua; o texto tem de passar no contraste.
    primaria_fill = primaria
    primaria_texto = ensure_contrast(primaria, fundo_ref, AA_TEXT)
    acento_fill = acento
    acento_texto = ensure_contrast(acento, fundo_ref, AA_TEXT)

    def _sem(h: float) -> dict:
        # L e C próprios do papel semântico — nunca herdados da marca.
        cor = semantic_color(h, p.H, L=0.62 if escuro else 0.55, C=0.135)
        return {
            "fill": to_hex(cor),
            "text": to_hex(ensure_contrast(cor, fundo_ref, AA_TEXT)),
            "on": to_hex(readable_on(cor)),
            "soft": to_hex(oklch_to_rgb(fit_gamut(
                OKLCH(0.255 if escuro else 0.955, rgb_to_oklch(cor).C * 0.42, rgb_to_oklch(cor).H)))),
        }

    return {
        "mode": "dark" if escuro else "light",
        "canvas": to_hex(canvas),
        "surface": to_hex(surface),
        "surface_2": to_hex(surface_2),
        "elevated": to_hex(elevated),
        "ink": {
            "strong": to_hex(ink_forte),
            "base": to_hex(ink_base),
            "muted": to_hex(ink_suave),
            "faint": to_hex(ink_tenue),
        },
        "border": {"hairline": to_hex(borda), "strong": to_hex(borda_forte)},
        "primary": {
            "fill": to_hex(primaria_fill),
            "text": to_hex(primaria_texto),
            "on": to_hex(readable_on(primaria_fill)),
            "soft": to_hex(oklch_to_rgb(fit_gamut(
                OKLCH(0.262 if escuro else 0.955, p.C * 0.40, p.H)))),
        },
        "accent": {
            "fill": to_hex(acento_fill),
            "text": to_hex(acento_texto),
            "on": to_hex(readable_on(acento_fill)),
            "soft": to_hex(oklch_to_rgb(fit_gamut(OKLCH(
                0.262 if escuro else 0.955,
                rgb_to_oklch(acento).C * 0.40, rgb_to_oklch(acento).H)))),
        },
        "positive": _sem(_H_POSITIVO),
        "negative": _sem(_H_NEGATIVO),
        "warning": _sem(_H_ATENCAO),
        "info": _sem(_H_INFO),
        "chart": _serie_grafico(primaria, 8, escuro),
        # Grade de gráfico quase invisível: a linha de apoio não pode competir
        # com o dado.
        "grid": to_hex(oklch_to_rgb(fit_gamut(
            OKLCH(0.290 if escuro else 0.930, 0.008, p.H)))),
    }


def _auditar(tema: dict) -> list[dict]:
    """Confere os pares que de fato aparecem em texto. Vira dado de tela."""
    fundo = parse_color(tema["surface"]) or _BRANCO
    canvas = parse_color(tema["canvas"]) or _BRANCO
    pares = [
        ("ink.strong / surface", tema["ink"]["strong"], tema["surface"], AAA_TEXT),
        ("ink.base / surface", tema["ink"]["base"], tema["surface"], AA_TEXT),
        ("ink.muted / surface", tema["ink"]["muted"], tema["surface"], AA_TEXT),
        ("ink.faint / surface", tema["ink"]["faint"], tema["surface"], AA_LARGE),
        ("primary.text / surface", tema["primary"]["text"], tema["surface"], AA_TEXT),
        ("accent.text / surface", tema["accent"]["text"], tema["surface"], AA_TEXT),
        ("primary.on / primary.fill", tema["primary"]["on"], tema["primary"]["fill"], AA_TEXT),
        ("accent.on / accent.fill", tema["accent"]["on"], tema["accent"]["fill"], AA_TEXT),
        ("ink.base / canvas", tema["ink"]["base"], tema["canvas"], AA_TEXT),
        ("positive.text / surface", tema["positive"]["text"], tema["surface"], AA_TEXT),
        ("negative.text / surface", tema["negative"]["text"], tema["surface"], AA_TEXT),
    ]
    saida = []
    for nome, fg, bg, alvo in pares:
        r = contrast_ratio(parse_color(fg) or (0, 0, 0), parse_color(bg) or _BRANCO)
        saida.append({
            "par": nome, "ratio": round(r, 2), "alvo": alvo, "passa": r >= alvo,
        })
    return saida


def build_design_system(
    primary: str | tuple[int, int, int] | None,
    accent: str | tuple[int, int, int] | None = None,
    *,
    typography: Optional[dict] = None,
) -> dict:
    """Sistema completo a partir da(s) cor(es) da marca.

    `accent` ausente não é problema: a maioria das marcas de corretora tem uma
    cor só. Deriva-se um acento análogo — mesmo matiz-família, luminosidade e
    croma diferentes — que parece escolhido junto em vez de sorteado.
    """
    p = _rgb(primary, _rgb(FALLBACK_PRIMARIA, (44, 110, 143)))

    if is_neutral(p):
        # Logo preto/cinza é comum e não dá cor nenhuma. Vale mais assumir o
        # fallback da casa do que gerar um sistema inteiro sobre cinza morto.
        p = _rgb(FALLBACK_PRIMARIA, (44, 110, 143))

    if accent:
        a = _rgb(accent, p)
    else:
        po = rgb_to_oklch(p)
        a = oklch_to_rgb(fit_gamut(OKLCH(
            min(0.78, po.L + 0.20), max(po.C * 1.45, 0.13), (po.H + 34) % 360)))

    escala_p = tonal_scale(p)
    escala_a = tonal_scale(a)

    claro = _tema(p, a, escuro=False)
    escuro = _tema(p, a, escuro=True)

    tipo = typography or {}
    return {
        "version": 1,
        "primary": to_hex(p),
        "accent": to_hex(a),
        "primary_step": nearest_step(p),
        "scales": {"primary": escala_p, "accent": escala_a},
        "themes": {"light": claro, "dark": escuro},
        "typography": {
            "display": tipo.get("display") or "'Fraunces', 'Playfair Display', Georgia, serif",
            "body": tipo.get("body") or "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
            "mono": tipo.get("mono") or "'JetBrains Mono', 'SF Mono', ui-monospace, monospace",
            "source": tipo.get("source") or "default",
        },
        "audit": {"light": _auditar(claro), "dark": _auditar(escuro)},
    }


def to_css_variables(sistema: dict, tema: str = "light", prefixo: str = "--ab") -> str:
    """Serializa um tema como custom properties, prontas para o `<style>`."""
    t = sistema["themes"][tema]
    linhas: list[str] = []

    def _por(caminho: str, valor):
        linhas.append(f"  {prefixo}-{caminho}: {valor};")

    for chave in ("canvas", "surface", "surface_2", "elevated", "grid"):
        _por(chave.replace("_", "-"), t[chave])
    for k, v in t["ink"].items():
        _por(f"ink-{k}", v)
    for k, v in t["border"].items():
        _por(f"border-{k}", v)
    for grupo in ("primary", "accent", "positive", "negative", "warning", "info"):
        for k, v in t[grupo].items():
            _por(f"{grupo}-{k}", v)
    for i, cor in enumerate(t["chart"], start=1):
        _por(f"chart-{i}", cor)
    for passo, cor in sistema["scales"]["primary"].items():
        _por(f"p-{passo}", cor)
    for chave, valor in sistema["typography"].items():
        if chave != "source":
            _por(f"font-{chave}", valor)

    return ":root {\n" + "\n".join(linhas) + "\n}"
