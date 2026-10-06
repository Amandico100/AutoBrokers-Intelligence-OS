"""A IMAGEM da prévia do link da proposta (og:image, 1200×630 PNG). SPEC-130-A · U5 · D-MC-74.

O desenho é o do protótipo aprovado (D-130A-11, `previa.html`): à esquerda a marca da anfitriã (logo,
ou monograma + nome sem marca cadastrada), a manchete e quantas seguradoras foram comparadas (e o selo
do comparador quando a origem é o canal); à direita o BILHETE da opção recomendada, inclinado, com o
picote — rótulo, seguradora, preço por ano e a franquia.

🔴 Os textos vêm SÓ de `proposta_html.previa_do_modelo` (a mesma função que escreve og:title/og:
description); do resto do modelo só entra o TEMA da anfitriã (cor não é dado pessoal). O que não está
na prévia (primeiro nome, veículo, CPF, placa) não tem como virar pixel. O teste prova por bytes: dois
modelos que só diferem no dado pessoal geram o MESMO PNG.

Por que PNG, e por que PyMuPDF (e não Pillow, nem o navegador)
-------------------------------------------------------------
O robô do WhatsApp não desenha SVG na prévia. O contêiner (`python:3.11-slim`) não tem navegador nem
fonte de sistema; 📊 06/10/2026 a fonte padrão do Pillow não tem acento ("op□□o"). O PyMuPDF
(`PyMuPDF==1.28.0`, `backend/requirements.txt`) desenha formas e texto e rasteriza de forma
determinística. A fonte é a da página — Instrument Sans (SIL OFL 1.1, `fontes/`), em cortes ESTÁTICOS
TTF (o MuPDF não lê woff2 nem instancia fonte variável; 📊 medido: "unknown file format"). Sem os
arquivos, cai na Helvetica do MuPDF. Sem PyMuPDF → None (a rota responde 404 e o link continua com
título e descrição).
"""

from __future__ import annotations

import base64
import logging
import re
from typing import Optional

from . import proposta_apresentacao as AP
from .proposta_estilo import PASTA_DAS_FONTES
from .proposta_html import PREVIA_ALTURA, PREVIA_LARGURA, previa_do_modelo

logger = logging.getLogger(__name__)

#: os cortes estáticos (nome interno → arquivo, e o substituto do MuPDF se faltar o arquivo)
_FONTES = {
    "is5": ("instrument-sans-500.ttf", "helv"),
    "is6": ("instrument-sans-600.ttf", "hebo"),
    "is6c": ("instrument-sans-600-semicondensada.ttf", "hebo"),
}
_INCLINACAO = 3.0          # graus, sentido anti-horário (o `rotate(-3deg)` do protótipo)


def _rgb(hexa: str) -> tuple[float, float, float]:
    r, g, b = AP.hex_rgb(hexa)
    return (r / 255, g / 255, b / 255)


def _cores(modelo: dict) -> dict:
    """As cores do tema CLARO da anfitriã (a prévia é sempre clara: o WhatsApp a mostra igual nos dois)."""
    claro, _escuro, esc = AP.temas((modelo or {}).get("anfitria") if isinstance((modelo or {}).get("anfitria"), dict) else {})
    p, a = claro["primary"]["fill"], claro["accent"]["fill"]
    selo = a if AP.contraste(a, p) >= 1.8 else "#FFFFFF"
    return {
        "p": p, "p_on": AP.sobre(p, esc["950"]), "suave": AP.mistura(claro["primary"]["soft"], "#FFFFFF", .75),
        "selo": selo, "selo_on": AP.sobre(selo, "#000000"),
        "tinta": "#121D25", "tinta2": "#3E4850", "tinta3": "#4F5A62", "linha": "#C4CED5",
    }


def _imagem_do_logo(data_url: Optional[str]) -> Optional[bytes]:
    m = re.match(r"^data:image/(png|jpeg|webp|gif);base64,([A-Za-z0-9+/=]+)$", data_url or "")
    if not m:
        return None
    try:
        return base64.b64decode(m.group(2), validate=True)
    except Exception:  # noqa: BLE001
        return None


def render_previa_png(modelo: dict) -> Optional[bytes]:
    """O PNG 1200×630 da prévia, ou None se o PyMuPDF não estiver disponível."""
    try:
        import pymupdf
    except Exception:  # noqa: BLE001
        logger.info("[PROPOSTA] PyMuPDF ausente — prévia sem imagem")
        return None

    p = previa_do_modelo(modelo)
    c = _cores(modelo)
    doc = pymupdf.open()
    try:
        pg = doc.new_page(width=PREVIA_LARGURA, height=PREVIA_ALTURA)
        fontes: dict = {}
        for nome, (arquivo, reserva) in _FONTES.items():
            caminho = PASTA_DAS_FONTES / arquivo
            try:
                pg.insert_font(fontname=nome, fontfile=str(caminho))
                fontes[nome] = (nome, pymupdf.Font(fontfile=str(caminho)))
            except Exception:  # noqa: BLE001
                fontes[nome] = (reserva, pymupdf.Font(reserva))

        def larg(texto: str, tam: float, f: str) -> float:
            return fontes[f][1].text_length(texto, fontsize=tam)

        def txt(ponto, texto: str, tam: float, cor: str, f: str, morph=None) -> None:
            pg.insert_text(ponto, texto, fontsize=tam, fontname=fontes[f][0], color=_rgb(cor), morph=morph)

        # ---- fundo: branco + o círculo suave da marca à direita
        pg.draw_rect(pg.rect, color=None, fill=(1, 1, 1))
        pg.draw_oval(pymupdf.Rect(560, -160, 1320, 790), color=None, fill=_rgb(c["suave"]))

        # ---- coluna da esquerda
        x0, util = 68, 520
        linhas_t1 = _quebrar(p["manchete"], 70, util, lambda s, t: larg(s, t, "is6c"))
        t2 = (f"{p['comparadas']} seguradoras comparadas por {p['corretoras']} corretoras" if p["comparadas"] and p["corretoras"]
              else f"{p['comparadas']} seguradoras comparadas com a mesma cobertura completa" if p["comparadas"] else "")
        linhas_t2 = _quebrar(t2, 36, 490, lambda s, t: larg(s, t, "is5")) if t2 else []
        alt_marca = 78
        altura = alt_marca + 26 + len(linhas_t1) * 71 + (18 + len(linhas_t2) * 43 if linhas_t2 else 0) + (64 if p["canal"] else 0)
        y = max(40, (PREVIA_ALTURA - altura) / 2)
        logo = _imagem_do_logo(p["logo"])
        desenhou_logo = False
        if logo:
            try:
                info = pymupdf.Pixmap(logo)
                w = alt_marca * info.width / max(info.height, 1)
                pg.insert_image(pymupdf.Rect(x0, y, x0 + min(w, 420), y + alt_marca), stream=logo, keep_proportion=True)
                desenhou_logo = True
            except Exception:  # noqa: BLE001
                desenhou_logo = False
        if not desenhou_logo and p["marca"]:
            pg.draw_rect(pymupdf.Rect(x0, y, x0 + 78, y + 78), color=None, fill=_rgb(c["p"]), radius=0.26)
            mono = AP.monograma(p["marca"])
            txt((x0 + 39 - larg(mono, 30, "is6") / 2, y + 50), mono, 30, c["p_on"], "is6")
            nome = p["marca"]
            while larg(nome, 40, "is6") > 400 and len(nome) > 4:
                nome = nome[:-2].rstrip() + "…"
            txt((x0 + 96, y + 53), nome, 40, c["tinta"], "is6")
        y += alt_marca + 26
        for ln in linhas_t1:
            y += 71
            txt((x0, y - 12), ln, 70, c["tinta"], "is6c")
        if linhas_t2:
            y += 18
            for ln in linhas_t2:
                y += 43
                txt((x0, y - 8), ln, 36, c["tinta2"], "is5")
        if p["canal"]:
            selo = f"Comparação independente · {p['canal']}"
            w = larg(selo, 22, "is5") + 36
            y += 18
            pg.draw_rect(pymupdf.Rect(x0, y, x0 + w, y + 42), color=_rgb("#C3C9CE"), fill=(1, 1, 1), width=2, radius=0.5)
            txt((x0 + 18, y + 29), selo, 22, c["tinta2"], "is5")

        # ---- o bilhete (inclinado), só se houver preço
        if p["preco"]:
            bx, by, bw, bh, cabeca = 628, 112, 520, 430, 300
            centro = pymupdf.Point(bx + bw / 2, by + bh / 2)
            giro = (centro, pymupdf.Matrix(_INCLINACAO))
            sh = pg.new_shape()
            # corpo branco + borda fina
            sh.draw_rect(pymupdf.Rect(bx, by, bx + bw, by + bh), radius=0.07)
            sh.finish(color=_rgb("#DDE3E8"), fill=(1, 1, 1), width=1.5, morph=giro)
            # cabeça na cor da marca (cantos de cima arredondados, base reta)
            sh.draw_rect(pymupdf.Rect(bx, by, bx + bw, by + cabeca + 40), radius=0.07)
            sh.finish(color=None, fill=_rgb(c["p"]), morph=giro)
            sh.draw_rect(pymupdf.Rect(bx + 0.75, by + cabeca, bx + bw - 0.75, by + cabeca + 41))
            sh.finish(color=None, fill=(1, 1, 1), morph=giro)
            # picote: linha tracejada e os dois furos
            sh.draw_line(pymupdf.Point(bx + 24, by + cabeca + 1), pymupdf.Point(bx + bw - 24, by + cabeca + 1))
            sh.finish(color=_rgb(c["linha"]), width=2.5, dashes="[8 6] 0", morph=giro)
            for cx in (bx, bx + bw):
                sh.draw_circle(pymupdf.Point(cx, by + cabeca), 17)
                sh.finish(color=None, fill=_rgb(c["suave"]), morph=giro)
            sh.commit()

            # selo (rótulo)
            if p["rotulo"]:
                wb = larg(p["rotulo"], 27, "is6") + 36
                sh = pg.new_shape()
                sh.draw_rect(pymupdf.Rect(bx + 34, by + 30, bx + 34 + wb, by + 78), radius=0.5)
                sh.finish(color=None, fill=_rgb(c["selo"]), morph=giro)
                sh.commit()
                txt((bx + 52, by + 64), p["rotulo"], 27, c["selo_on"], "is6", morph=giro)
            if p["seguradora"]:
                seg = p["seguradora"]
                while larg(seg, 42, "is6") > bw - 68 and len(seg) > 4:
                    seg = seg[:-2].rstrip() + "…"
                txt((bx + 34, by + 136), seg, 42, c["p_on"], "is6", morph=giro)
            # preço: R$ · inteiro · ,centavos · por ano (todos na mesma linha de base)
            inteiro, _, cent = p["preco"].replace("R$ ", "").partition(",")
            tam_int = 104
            while larg(inteiro, tam_int, "is6c") + larg("," + cent, 42, "is6c") + larg("por ano", 30, "is5") + 90 > bw - 40 \
                    and tam_int > 60:
                tam_int -= 4
            base = by + 262
            x = bx + 34
            txt((x, base - tam_int * 0.56), "R$", 30, c["p_on"], "is6", morph=giro)
            x += larg("R$", 30, "is6") + 8
            txt((x, base), inteiro, tam_int, c["p_on"], "is6c", morph=giro)
            x += larg(inteiro, tam_int, "is6c")
            txt((x, base), "," + cent, 42, c["p_on"], "is6c", morph=giro)
            x += larg("," + cent, 42, "is6c") + 14
            txt((x, base), "por ano", 30, c["p_on"], "is5", morph=giro)
            # a faixa de baixo: a franquia
            if p["franquia"]:
                rot = f"Franquia {p['franquia_tipo'].lower()}".strip()
                txt((bx + 34, by + cabeca + 78), rot, 28, c["tinta3"], "is5", morph=giro)
                txt((bx + bw - 34 - larg(p["franquia"], 34, "is6"), by + cabeca + 78), p["franquia"], 34, c["tinta"],
                    "is6", morph=giro)
        return pg.get_pixmap(alpha=False).tobytes("png")
    finally:
        doc.close()


def _quebrar(texto: str, tamanho: float, largura: float, medir) -> list[str]:
    """Quebra por palavras na largura dada (a mais longa que couber em cada linha)."""
    linhas: list[str] = []
    atual = ""
    for palavra in texto.split():
        tentativa = f"{atual} {palavra}".strip()
        if atual and medir(tentativa, tamanho) > largura:
            linhas.append(atual)
            atual = palavra
        else:
            atual = tentativa
    if atual:
        linhas.append(atual)
    return linhas
