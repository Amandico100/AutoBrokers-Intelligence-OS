"""Extração de cor de marca a partir do arquivo do logo. SPEC-057 §Bloco A.

Por que o logo e não o CSS
--------------------------
Site de corretora é quase sempre WordPress, Wix ou construtor equivalente. A
folha de estilo desses temas é dominada por cores do **tema**, não da marca:
azuis de botão padrão, cinzas de moldura, o verde do plugin de WhatsApp. Ler
cor de marca do CSS produz, na prática, a cor de quem fez o template.

O logo não mente. Ele foi desenhado pela marca, para a marca. E há uma medida
melhor que "cor mais frequente": **área de tinta opaca**. O fundo transparente
não vota, o antialiasing das bordas não vota, e a proporção entre o que sobra
diz sozinha quem é primária e quem é acento — na Resulta deu 94% / 6%, que é a
assinatura clássica de uma marca de uma cor dominante com um destaque.

Sem dependência nova. PNG é decodificado aqui (é o formato de logo por causa da
transparência) e SVG é lido como texto. Pillow entra só se já existir no
ambiente, para JPEG e WebP.
"""

from __future__ import annotations

import logging
import re
import struct
import zlib
from collections import Counter
from dataclasses import dataclass
from typing import Optional

from .color import dedupe, is_neutral, parse_color, rgb_to_oklch, to_hex

logger = logging.getLogger(__name__)

MAX_PIXELS = 1_600_000      # logo maior que isso é banner; amostrar basta
MIN_ALPHA = 200             # abaixo disso é borda/sombra, não tinta
MIN_PARTICIPACAO = 0.015    # cor com menos de 1,5% da tinta é ruído de compressão


@dataclass
class InkColor:
    hex: str
    ink_share: float
    saturation: float
    luminance: float

    def as_dict(self) -> dict:
        return {
            "hex": self.hex,
            "ink_share": round(self.ink_share, 4),
            "saturation": round(self.saturation, 3),
            "luminance": round(self.luminance, 3),
        }


@dataclass
class LogoAnalysis:
    width: int
    height: int
    has_transparency: bool
    ink_colors: list[InkColor]
    format: str
    confidence: float
    note: str = ""

    @property
    def primary(self) -> Optional[str]:
        cromaticas = [c for c in self.ink_colors if not is_neutral(parse_color(c.hex) or (0, 0, 0))]
        return cromaticas[0].hex if cromaticas else (self.ink_colors[0].hex if self.ink_colors else None)

    @property
    def accent(self) -> Optional[str]:
        cromaticas = [c for c in self.ink_colors if not is_neutral(parse_color(c.hex) or (0, 0, 0))]
        return cromaticas[1].hex if len(cromaticas) > 1 else None


# ==========================================================================
# PNG
# ==========================================================================

_CANAIS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}


def _png_chunks(data: bytes) -> tuple[dict, bytes]:
    i, meta, idat = 8, {}, bytearray()
    while i + 8 <= len(data):
        (ln,) = struct.unpack(">I", data[i:i + 4])
        tipo = data[i + 4:i + 8]
        corpo = data[i + 8:i + 8 + ln]
        if tipo == b"IDAT":
            idat += corpo
        elif tipo == b"IEND":
            break
        else:
            meta.setdefault(tipo, corpo)
        i += 12 + ln
    return meta, bytes(idat)


def _unfilter(raw: bytes, largura: int, altura: int, bpp: int, stride: int) -> list[bytes]:
    linhas: list[bytes] = []
    anterior = bytearray(stride)
    pos = 0
    for _ in range(altura):
        if pos >= len(raw):
            break
        filtro = raw[pos]
        pos += 1
        linha = bytearray(raw[pos:pos + stride])
        if len(linha) < stride:
            linha.extend(b"\x00" * (stride - len(linha)))
        pos += stride

        if filtro == 1:
            for x in range(bpp, stride):
                linha[x] = (linha[x] + linha[x - bpp]) & 0xFF
        elif filtro == 2:
            for x in range(stride):
                linha[x] = (linha[x] + anterior[x]) & 0xFF
        elif filtro == 3:
            for x in range(stride):
                a = linha[x - bpp] if x >= bpp else 0
                linha[x] = (linha[x] + ((a + anterior[x]) >> 1)) & 0xFF
        elif filtro == 4:
            for x in range(stride):
                a = linha[x - bpp] if x >= bpp else 0
                b = anterior[x]
                c = anterior[x - bpp] if x >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                linha[x] = (linha[x] + pr) & 0xFF

        linhas.append(bytes(linha))
        anterior = linha
    return linhas


def analisar_png(data: bytes) -> Optional[LogoAnalysis]:
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return None
    try:
        meta, idat = _png_chunks(data)
        largura, altura, prof, tipo_cor, _, _, entrelacado = struct.unpack(
            ">IIBBBBB", meta[b"IHDR"][:13])
    except Exception:  # noqa: BLE001
        return None

    if entrelacado:
        # Adam7 é raro em logo. Decodificar errado é pior do que não decodificar:
        # devolveria cores plausíveis e falsas.
        return LogoAnalysis(largura, altura, True, [], "png", 0.0,
                            "PNG entrelaçado — extração de cor não aplicada")
    if largura * altura > MAX_PIXELS:
        return LogoAnalysis(largura, altura, True, [], "png", 0.0,
                            "imagem grande demais para análise de tinta")

    canais = _CANAIS.get(tipo_cor)
    if canais is None:
        return None

    try:
        raw = zlib.decompress(idat)
    except Exception:  # noqa: BLE001
        return None

    bits_por_pixel = canais * prof
    stride = (largura * bits_por_pixel + 7) // 8
    bpp = max(1, bits_por_pixel // 8)
    linhas = _unfilter(raw, largura, altura, bpp, stride)

    plte = meta.get(b"PLTE", b"")
    trns = meta.get(b"tRNS", b"")
    paleta = [(plte[i], plte[i + 1], plte[i + 2]) for i in range(0, len(plte) - 2, 3)]

    contagem: Counter = Counter()
    tem_alfa = tipo_cor in (4, 6) or bool(trns)

    if tipo_cor == 3:
        por_byte = 8 // prof
        mascara = (1 << prof) - 1
        for linha in linhas:
            for x in range(largura):
                idx = (linha[x // por_byte] >> ((por_byte - 1 - (x % por_byte)) * prof)) & mascara
                if idx >= len(paleta):
                    continue
                alfa = trns[idx] if idx < len(trns) else 255
                if alfa >= MIN_ALPHA:
                    contagem[paleta[idx]] += 1
    elif prof == 8:
        for linha in linhas:
            for x in range(largura):
                base = x * canais
                if base + canais > len(linha):
                    break
                if tipo_cor == 0:
                    v = linha[base]
                    contagem[(v, v, v)] += 1
                elif tipo_cor == 4:
                    if linha[base + 1] >= MIN_ALPHA:
                        v = linha[base]
                        contagem[(v, v, v)] += 1
                elif tipo_cor == 2:
                    contagem[(linha[base], linha[base + 1], linha[base + 2])] += 1
                elif tipo_cor == 6:
                    if linha[base + 3] >= MIN_ALPHA:
                        contagem[(linha[base], linha[base + 1], linha[base + 2])] += 1
    elif prof == 16:
        passo = canais * 2
        for linha in linhas:
            for x in range(largura):
                base = x * passo
                if base + passo > len(linha):
                    break
                if tipo_cor == 6 and linha[base + 6] < MIN_ALPHA:
                    continue
                contagem[(linha[base], linha[base + 2], linha[base + 4])] += 1
    else:
        return LogoAnalysis(largura, altura, tem_alfa, [], "png", 0.0,
                            f"profundidade {prof} bits não suportada")

    cores = _consolidar(contagem)
    return LogoAnalysis(largura, altura, tem_alfa, cores, "png",
                        _confianca(cores, tem_alfa))


# ==========================================================================
# SVG
# ==========================================================================

_SVG_COR = re.compile(
    r'(?:fill|stop-color|stroke)\s*[:=]\s*["\']?\s*(#[0-9a-fA-F]{3,8}|rgba?\([^)]*\))', re.I)
_SVG_VIEWBOX = re.compile(r'viewBox\s*=\s*["\']([\d.\-\s]+)["\']', re.I)


def analisar_svg(data: bytes) -> Optional[LogoAnalysis]:
    try:
        texto = data.decode("utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return None
    if "<svg" not in texto.lower():
        return None

    largura = altura = 0
    vb = _SVG_VIEWBOX.search(texto)
    if vb:
        partes = vb.group(1).replace(",", " ").split()
        if len(partes) == 4:
            try:
                largura, altura = int(float(partes[2])), int(float(partes[3]))
            except ValueError:
                pass

    # Em SVG não há pixels para pesar. A ordem de aparição é o melhor sinal:
    # o desenho começa pelo elemento dominante. Peso decrescente por posição.
    brutas: list[tuple[int, int, int]] = []
    for m in _SVG_COR.finditer(texto):
        rgb = parse_color(m.group(1))
        if rgb:
            brutas.append(rgb)

    if not brutas:
        return LogoAnalysis(largura, altura, True, [], "svg", 0.0, "SVG sem cor declarada")

    pesos: Counter = Counter()
    for i, rgb in enumerate(brutas):
        pesos[rgb] += max(1, len(brutas) - i)

    cores = _consolidar(pesos)
    # Menos confiável que pixel: `currentColor`, gradiente e CSS externo podem
    # mudar o que de fato aparece na tela.
    return LogoAnalysis(largura, altura, True, cores, "svg",
                        min(0.72, _confianca(cores, True)))


# ==========================================================================
# JPEG / WebP — só se Pillow existir
# ==========================================================================

def analisar_com_pillow(data: bytes) -> Optional[LogoAnalysis]:
    try:
        import io

        from PIL import Image  # type: ignore
    except Exception:  # noqa: BLE001
        return None
    try:
        img = Image.open(io.BytesIO(data))
        largura, altura = img.size
        if largura * altura > MAX_PIXELS:
            escala = (MAX_PIXELS / (largura * altura)) ** 0.5
            img = img.resize((max(1, int(largura * escala)), max(1, int(altura * escala))))
        tem_alfa = img.mode in ("RGBA", "LA") or "transparency" in img.info
        img = img.convert("RGBA")
        contagem: Counter = Counter()
        for r, g, b, a in img.getdata():
            if a >= MIN_ALPHA:
                contagem[(r, g, b)] += 1
        cores = _consolidar(contagem)
        return LogoAnalysis(largura, altura, tem_alfa, cores, img.format or "raster",
                            _confianca(cores, tem_alfa) * 0.9)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[brand] Pillow falhou: %s", type(exc).__name__)
        return None


# ==========================================================================
# Consolidação
# ==========================================================================

def _consolidar(contagem: Counter) -> list[InkColor]:
    """Agrupa tons perceptualmente iguais e ordena por área de tinta.

    JPEG e antialiasing produzem dezenas de variações de um mesmo azul. Sem
    agrupar, a cor real da marca aparece fatiada em vinte entradas de 4% e
    perde para um cinza de borda.
    """
    if not contagem:
        return []
    total = sum(contagem.values())
    if not total:
        return []

    grupos: list[tuple[tuple[int, int, int], int]] = []
    for cor, n in contagem.most_common(400):
        for i, (rep, acumulado) in enumerate(grupos):
            if not dedupe([rep, cor], 0.055)[1:]:   # colapsaram → mesma família
                grupos[i] = (rep, acumulado + n)
                break
        else:
            grupos.append((cor, n))

    grupos.sort(key=lambda g: g[1], reverse=True)

    saida: list[InkColor] = []
    for cor, n in grupos:
        parte = n / total
        if parte < MIN_PARTICIPACAO and saida:
            continue
        c = rgb_to_oklch(cor)
        mx, mn = max(cor) / 255, min(cor) / 255
        saida.append(InkColor(
            hex=to_hex(cor), ink_share=parte,
            saturation=0.0 if mx == 0 else (mx - mn) / mx,
            luminance=c.L,
        ))
        if len(saida) >= 8:
            break
    return saida


def _confianca(cores: list[InkColor], tem_alfa: bool) -> float:
    """Quanto se pode confiar nesta leitura.

    Alta quando há uma cor cromática claramente dominante sobre fundo
    transparente — o retrato de um logo bem-feito. Baixa quando tudo é cinza ou
    quando nenhuma cor se destaca.
    """
    if not cores:
        return 0.0
    cromaticas = [c for c in cores if not is_neutral(parse_color(c.hex) or (0, 0, 0))]
    if not cromaticas:
        return 0.25
    conf = 0.45
    if tem_alfa:
        conf += 0.20                     # fundo removido: só tinta votou
    if cromaticas[0].ink_share >= 0.35:
        conf += 0.25                     # dominância inequívoca
    elif cromaticas[0].ink_share >= 0.15:
        conf += 0.12
    if len(cromaticas) >= 2 and cromaticas[0].ink_share > cromaticas[1].ink_share * 2.5:
        conf += 0.10                     # primária e acento bem separados
    return round(min(conf, 0.98), 2)


def analisar_logo(data: bytes, mime: str = "") -> Optional[LogoAnalysis]:
    """Ponto de entrada: escolhe o decodificador pelo conteúdo, não pelo MIME.

    Servidor de site erra `Content-Type` com frequência; o cabeçalho do arquivo
    não erra.
    """
    if not data:
        return None
    if data.startswith(b"\x89PNG"):
        return analisar_png(data)
    if data.lstrip()[:5].lower().startswith(b"<svg") or b"<svg" in data[:512].lower():
        return analisar_svg(data)
    if data.startswith(b"\xff\xd8\xff") or data[8:12] == b"WEBP" or data.startswith(b"GIF8"):
        r = analisar_com_pillow(data)
        if r:
            return r
        return LogoAnalysis(0, 0, False, [], "raster", 0.0,
                            "JPEG/WebP requer Pillow — cor não extraída do logo")
    return None
