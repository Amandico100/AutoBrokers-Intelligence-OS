"""A IMAGEM da prévia do link da proposta (og:image, 1200×630 PNG). SPEC-130-A · U5 · D-MC-74.

🔴 Os textos vêm SÓ de `proposta_html.previa_do_modelo` — a mesma função que
escreve og:title/og:description. O modelo inteiro nunca chega ao desenho: o que
não está na prévia (primeiro nome, veículo, CPF, placa) não tem como virar pixel.
O teste prova por bytes: dois modelos que só diferem no dado pessoal geram o
MESMO PNG.

Por que PNG, e por que PyMuPDF (e não Pillow)
---------------------------------------------
O robô do WhatsApp não desenha SVG na prévia, então SVG→PNG não serve. 📊 A 1ª
versão usou Pillow (chega ao contêiner pela `fastembed`) com a fonte embutida
dele — e 📊 medido em 06/10/2026 a fonte padrão do Pillow NÃO tem acento: "opção"
saía "op□□o". O contêiner (`python:3.11-slim`) não tem fonte de sistema, e o
repositório não versiona nenhuma (`git ls-files | grep -iE '\\.(ttf|otf)$'` → 0).
O PyMuPDF está fixado em `backend/requirements.txt` (`PyMuPDF==1.28.0`), traz a
Helvetica do MuPDF (com acento, regular e negrito) e rasteriza a página em PNG
de forma determinística (mesma entrada → mesmos bytes, medido). Ausente → None
(a rota responde 404 e o link continua com título e descrição).

PROVISÓRIO no desenho: a F2b pode trocar cores, tamanhos e posições.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from .proposta_html import PREVIA_ALTURA, PREVIA_LARGURA, previa_do_modelo

logger = logging.getLogger(__name__)

_FUNDO_NEUTRO = (24, 30, 37)
_TINTA_NEUTRA = (255, 255, 255)
_MARGEM = 72
_REGULAR, _NEGRITO = "helv", "hebo"


def _cor(hexa: object) -> Optional[tuple[int, int, int]]:
    m = re.fullmatch(r"#?([0-9a-fA-F]{6})", str(hexa or "").strip())
    if not m:
        return None
    h = m.group(1)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _cores_da_marca(modelo: dict) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    """Fundo e tinta do tema CLARO auditado da anfitriã (`primary.fill`/`primary.on`); senão o neutro."""
    tema = ((modelo or {}).get("anfitria") or {}).get("tema_claro") or {}
    primaria = tema.get("primary") if isinstance(tema, dict) else None
    if isinstance(primaria, dict):
        fundo, tinta = _cor(primaria.get("fill")), _cor(primaria.get("on"))
        if fundo and tinta:
            return fundo, tinta
    return _FUNDO_NEUTRO, _TINTA_NEUTRA


def _rgb01(c: tuple[int, int, int]) -> tuple[float, float, float]:
    return tuple(v / 255 for v in c)  # type: ignore[return-value]


def render_previa_png(modelo: dict) -> Optional[bytes]:
    """O PNG 1200×630 da prévia, ou None se o PyMuPDF não estiver disponível."""
    try:
        import pymupdf
    except Exception:  # noqa: BLE001
        logger.info("[PROPOSTA] PyMuPDF ausente — prévia sem imagem")
        return None

    p = previa_do_modelo(modelo)
    fundo, tinta = _cores_da_marca(modelo)
    suave = tuple(int(t * 0.78 + f * 0.22) for t, f in zip(tinta, fundo))
    util = PREVIA_LARGURA - 2 * _MARGEM
    fontes = {_REGULAR: pymupdf.Font(_REGULAR), _NEGRITO: pymupdf.Font(_NEGRITO)}

    doc = pymupdf.open()
    try:
        pg = doc.new_page(width=PREVIA_LARGURA, height=PREVIA_ALTURA)
        pg.draw_rect(pg.rect, color=None, fill=_rgb01(fundo))

        def escrever(y: float, texto: str, tamanho: float, cor, fonte: str = _REGULAR) -> None:
            # a maior fonte ≤ `tamanho` em que o texto cabe na largura útil
            while tamanho > 20 and fontes[fonte].text_length(texto, fontsize=tamanho) > util:
                tamanho -= 2
            pg.insert_text((_MARGEM, y), texto, fontsize=tamanho, fontname=fonte, color=_rgb01(cor))

        escrever(104, p["marca"] or "Sua cotação de seguro", 44, tinta, _NEGRITO)
        if p["preco"]:
            escrever(236, "A opção recomendada", 36, suave)
            escrever(350, p["preco"], 112, tinta, _NEGRITO)
            escrever(424, f"por ano · {p['seguradora']}" if p["seguradora"] else "por ano", 48, tinta)
        else:
            escrever(330, "Sua cotação de seguro", 72, tinta, _NEGRITO)
        if p["comparadas"]:
            n = p["comparadas"]
            rodape = f"{n} seguradora{'s' if n > 1 else ''} comparada{'s' if n > 1 else ''}"
            if p["validade"]:
                rodape += f" · válida até {p['validade']}"
            escrever(566, rodape, 36, suave)
        return pg.get_pixmap(alpha=False).tobytes("png")
    finally:
        doc.close()
