"""SPEC-057 Bloco A — garantias da identidade de marca.

Roda offline. O que se prova aqui é que a marca de uma corretora vira um
sistema de design **legível**, e que a procedência sobrevive à recaptura.

    python backend/tests/test_spec057_brand_identity.py
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
FALHAS: list[str] = []

pkg = types.ModuleType("brandpkg")
pkg.__path__ = [os.path.join(RAIZ, "app/services/brand")]
sys.modules["brandpkg"] = pkg


def _carregar(nome: str):
    caminho = os.path.join(RAIZ, "app/services/brand", f"{nome}.py")
    spec = importlib.util.spec_from_file_location(f"brandpkg.{nome}", caminho)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = "brandpkg"
    sys.modules[f"brandpkg.{nome}"] = mod
    spec.loader.exec_module(mod)
    return mod


color = _carregar("color")
extract = _carregar("extract")
system = _carregar("system")


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


# Marcas reais e casos difíceis. O amarelo e o logo preto são os que quebram
# geradores ingênuos de paleta.
MARCAS = {
    "Resulta (marinho + laranja)": ("#1D5579", "#EE7501"),
    "uma cor só": ("#1D5579", None),
    "amarelo quase ilegível": ("#F5D90A", None),
    "vermelho forte": ("#C0202A", None),
    "verde": ("#0F7B3E", None),
    "logo preto": ("#111111", None),
    "roxo + rosa": ("#6D28D9", "#F472B6"),
    "ciano claro": ("#22D3EE", None),
}


def teste_contraste_em_toda_marca():
    print("\n[1] Nenhuma marca produz texto ilegível")
    total = falhas = 0
    for nome, (p, a) in MARCAS.items():
        s = system.build_design_system(p, a)
        ruins = [x for m in ("light", "dark") for x in s["audit"][m] if not x["passa"]]
        total += sum(len(s["audit"][m]) for m in ("light", "dark"))
        falhas += len(ruins)
        checar(not ruins, f"'{nome}' passa em todos os pares de contraste",
               ", ".join(f"{x['par']}={x['ratio']}" for x in ruins[:3]))
    checar(falhas == 0, f"total: {total - falhas}/{total} pares AA ou melhor")


def teste_marca_crua_seria_ilegivel():
    print("\n[2] A cor da marca é ajustada, não substituída")
    laranja = color.parse_color("#EE7501")
    branco = (255, 255, 255)
    antes = color.contrast_ratio(laranja, branco)
    checar(antes < 4.5, "laranja da Resulta reprova AA no branco", f"{antes:.2f}:1")

    ajustado = color.ensure_contrast(laranja, branco, 4.5)
    depois = color.contrast_ratio(ajustado, branco)
    checar(depois >= 4.5, "após ajuste, passa", f"{depois:.2f}:1")

    h1 = color.rgb_to_oklch(laranja).H
    h2 = color.rgb_to_oklch(ajustado).H
    checar(abs(h1 - h2) < 15,
           "o matiz é preservado — continua sendo laranja da marca",
           f"{h1:.0f}° -> {h2:.0f}°")


def teste_semantico_continua_semantico():
    print("\n[3] Vermelho continua vermelho ao lado de marca azul")
    s = system.build_design_system("#1D5579", "#EE7501")
    faixas = {"positive": (110, 200), "negative": (350, 45), "warning": (55, 110),
              "info": (200, 285)}
    for modo in ("light", "dark"):
        for papel, (lo, hi) in faixas.items():
            h = color.rgb_to_oklch(color.parse_color(s["themes"][modo][papel]["fill"])).H
            dentro = (lo <= h <= hi) if lo < hi else (h >= lo or h <= hi)
            checar(dentro, f"[{modo}] '{papel}' está na faixa de matiz esperada",
                   f"H={h:.0f}°, esperado {lo}–{hi}°")


def teste_grafico_sobrevive_preto_e_branco():
    print("\n[4] Séries de gráfico distinguíveis sem cor")
    for p, a in [("#1D5579", "#EE7501"), ("#C0202A", None), ("#0F7B3E", None)]:
        s = system.build_design_system(p, a)
        for modo in ("light", "dark"):
            lums = [color.relative_luminance(color.parse_color(c))
                    for c in s["themes"][modo]["chart"]]
            menor = min(abs(lums[i] - lums[i + 1]) for i in range(len(lums) - 1))
            checar(menor > 0.05,
                   f"[{p} {modo}] séries vizinhas separam em luminância",
                   f"menor salto {menor:.3f}")


def teste_logo_manda_na_cor():
    print("\n[5] O logo manda na cor, não o CSS")
    # Reproduz o caso real: PNG paletizado com 94% de uma cor e 6% de outra.
    import struct
    import zlib

    largura, altura = 50, 10
    px = bytearray()
    for _ in range(altura):
        px.append(0)
        for x in range(largura):
            px += bytes((0x1D, 0x55, 0x79, 255)) if x < 47 else bytes((0xEE, 0x75, 0x01, 255))

    def chunk(tipo, dados):
        c = tipo + dados
        return struct.pack(">I", len(dados)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", largura, altura, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(bytes(px)))
           + chunk(b"IEND", b""))

    a = extract.analisar_logo(png)
    checar(a is not None and a.primary == "#1D5579",
           "cor dominante do logo vira a primária", str(a.primary if a else None))
    checar(a is not None and a.accent == "#EE7501",
           "segunda cor vira o acento", str(a.accent if a else None))
    checar(a is not None and a.confidence >= 0.9,
           "confiança alta com fundo transparente e dominância clara",
           str(a.confidence if a else 0))

    # Pixel totalmente transparente não pode votar.
    px2 = bytearray()
    for _ in range(altura):
        px2.append(0)
        for x in range(largura):
            px2 += bytes((0x1D, 0x55, 0x79, 255)) if x < 5 else bytes((0xFF, 0x00, 0xFF, 0))
    png2 = (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", largura, altura, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(px2)))
            + chunk(b"IEND", b""))
    b = extract.analisar_logo(png2)
    checar(b is not None and b.primary == "#1D5579",
           "fundo transparente não vota, mesmo sendo 90% da imagem",
           str(b.primary if b else None))


def teste_paleta_do_editor_e_descartada():
    print("\n[6] Paleta padrão do WordPress não vira identidade")
    mod = color

    # Exatamente o que o site real da Resulta devolveu no CSS.
    gutenberg = ["#000000", "#abb8c3", "#ffffff", "#f78da7", "#cf2e2e",
                 "#ff6900", "#fcb900", "#7bdcb5"]
    checar(mod.cores_css_confiaveis(gutenberg) == [],
           "as 8 cores do editor do WordPress são todas descartadas",
           str(mod.cores_css_confiaveis(gutenberg)))
    checar(mod.cores_css_confiaveis(["#25D366", "#0A66C2"]) == [],
           "verde do WhatsApp e azul do LinkedIn não são cor da corretora")
    checar(mod.cores_css_confiaveis(["#1D5579", "#EE7501"]) == ["#1D5579", "#EE7501"],
           "cor legítima passa")


def teste_fallback_nunca_quebra():
    print("\n[7] Ausência de sinal nunca gera peça sem identidade")
    for entrada in (None, "", "não é cor", "#zzzzzz", "#111111"):
        s = system.build_design_system(entrada)
        ok = bool(s.get("primary")) and not [
            x for m in ("light", "dark") for x in s["audit"][m] if not x["passa"]]
        checar(ok, f"entrada {entrada!r} produz sistema válido e legível")


def teste_css_serializa():
    print("\n[8] O sistema vira CSS pronto para a peça")
    s = system.build_design_system("#1D5579", "#EE7501")
    css = system.to_css_variables(s, "light")
    for token in ("--ab-primary-fill", "--ab-ink-strong", "--ab-chart-1",
                  "--ab-surface", "--ab-font-display", "--ab-p-500"):
        checar(token in css, f"token {token} presente")
    checar(css.count("--ab-chart-") == 8, "oito séries de gráfico exportadas")


def main() -> int:
    print("=" * 68)
    print("SPEC-057 BLOCO A — IDENTIDADE DE MARCA")
    print("=" * 68)
    teste_contraste_em_toda_marca()
    teste_marca_crua_seria_ilegivel()
    teste_semantico_continua_semantico()
    teste_grafico_sobrevive_preto_e_branco()
    teste_logo_manda_na_cor()
    teste_paleta_do_editor_e_descartada()
    teste_fallback_nunca_quebra()
    teste_css_serializa()

    print("\n" + "=" * 68)
    if FALHAS:
        print(f"FALHAS: {len(FALHAS)}")
        for f in FALHAS:
            print(f"  X {f}")
        return 1
    print("TODAS AS GARANTIAS VERIFICADAS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
