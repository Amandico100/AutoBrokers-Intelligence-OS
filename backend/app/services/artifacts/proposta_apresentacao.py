"""A APRESENTAÇÃO da proposta — o que a página DERIVA dos fatos do modelo. SPEC-130-A · U5 (F2b).

O modelo (CONTRATO §5, `backend/tests/fixtures/proposta/modelo_contrato.json`) traz FATOS:
preços, parcelas, franquias, coberturas, a anfitriã. Tudo o que a página diz A MAIS — "com
juros · total R$ 5.558", "Franquia R$ 376 menor", "melhor"/"mais simples", os rótulos da régua
— nasce aqui, puro (sem I/O, sem banco), a partir do protótipo aprovado pelo Founder (D-130A-11,
"carteira" v4, `gerar.py`). `proposta_html.py` só monta o HTML com estes valores.

Regras que valem em TODA derivação:

```
dinheiro derivado   arredondamento ÚNICO em reais inteiros, meio para cima (Decimal, nunca float):
                    5.170,54 − 4.795,00 = 375,54 → "R$ 376"; e é o mesmo 376 no cartão, no comparar e na FAQ
"sem juros"         só quando vezes × parcela bate com o prêmio (± R$ 1); senão "com juros" e o total
etiquetas           "melhor"/"mais simples" só com fato que ordena (nível, dias, km, itens); o que não
                    ordena ganha a frase "a corretora confirma o que cobre" e etiqueta nenhuma
ausente             não aparece. Nunca "—" inventado
```
"""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Iterable, Optional

NB = " "

# =====================================================================================================================
# números
# =====================================================================================================================
_CENTAVO = Decimal("0.01")
_REAL = Decimal("1")


def dec(valor: Any) -> Optional[Decimal]:
    """O valor como Decimal de centavos. Não-número, NaN, infinito, bool → None."""
    if isinstance(valor, bool) or valor is None:
        return None
    try:
        d = Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError):
        return None
    if not d.is_finite():
        return None
    return d.quantize(_CENTAVO, rounding=ROUND_HALF_UP)


def reais(valor: Any) -> Optional[int]:
    """Reais inteiros, meio para cima (a regra ÚNICA de todo valor derivado). −0,5 → −1 (simétrico)."""
    d = dec(valor)
    if d is None:
        return None
    return int(d.quantize(_REAL, rounding=ROUND_HALF_UP))


def _milhar(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def brl(valor: Any, centavos: bool = True) -> str:
    """`R$ 4.784,27` (centavos) ou `R$ 4.784` (inteiro, arredondado pela regra única). Com espaço
    INSEPARÁVEL depois do R$. Não-número → "" (ausente não aparece)."""
    d = dec(valor)
    if d is None:
        return ""
    if centavos:
        inteiro, _, cent = f"{abs(d):,.2f}".partition(".")
        s = f"{inteiro.replace(',', '.')},{cent}"
        return ("-" if d < 0 else "") + "R$" + NB + s
    r = reais(d)
    return ("-" if r < 0 else "") + "R$" + NB + _milhar(abs(r))


def numero_inteiro(valor: Any) -> Optional[int]:
    """Um inteiro de verdade (não bool). Senão None."""
    if isinstance(valor, bool) or not isinstance(valor, int):
        return None
    return valor


def nbsp(texto: str) -> str:
    """Valores nunca se partem: "R$ 200 mil", "15 dias", "24 h"."""
    s = re.sub(r"R\$\s+", "R$" + NB, str(texto))
    return re.sub(r"(\d)\s+(mil|h|km|dias|diárias|anos)\b", lambda m: m.group(1) + NB + m.group(2), s)


def tidy(texto: Any) -> str:
    """Tira o código da seguradora ("(024)") e espaços repetidos."""
    return re.sub(r"\s+", " ", re.sub(r"\s*\(\d{3}\)\s*", " ", str(texto or ""))).strip()


def sem_seguradora(produto: Any, seguradora: Any) -> str:
    """ "Azul Auto Roubo" da Azul → "Auto Roubo". Com a 1ª letra maiúscula."""
    p, seg = tidy(produto), str(seguradora or "").strip()
    if seg and p.lower().startswith(seg.lower() + " "):
        p = p[len(seg):].strip()
    return p[:1].upper() + p[1:]


def data_br(iso: Any) -> str:
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", str(iso or ""))
    return f"{m.group(3)}/{m.group(2)}/{m.group(1)}" if m else ""


def data_curta(iso: Any) -> str:
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", str(iso or ""))
    return f"{m.group(3)}/{m.group(2)}" if m else ""


def aspas_tipograficas(texto: Any) -> str:
    """`ficha 'RESULTA'` → `ficha “RESULTA”` (aspas retas em pares viram curvas)."""
    s = str(texto or "")
    s = re.sub(r"'([^'\n]+)'", "“\\1”", s)
    return re.sub(r'"([^"\n]+)"', "“\\1”", s)


def monograma(nome: Any) -> str:
    """ "AutoFleet" → "AF"; "Corretora Exemplo" → "CE". Só letras/dígitos."""
    partes = re.sub(r"([a-z])([A-Z])", r"\1 \2", str(nome or "")).split()
    letras = "".join(p[0] for p in partes if p[:1].isalnum())
    return letras[:2].upper()


# =====================================================================================================================
# o bem (veículo ou outro ramo)
# =====================================================================================================================
VEICULOS = {"carro", "moto", "caminhão", "caminhao", "caminhonete", "van", "utilitário", "utilitario", "veículo",
            "veiculo"}


def o_bem(modelo: dict) -> dict:
    """{rotulo, descricao, ano, apelido, e_veiculo} de `bem` (qualquer ramo) ou `veiculo` (auto)."""
    bem = modelo.get("bem") if isinstance(modelo.get("bem"), dict) else None
    vei = modelo.get("veiculo") if isinstance(modelo.get("veiculo"), dict) else None
    if bem:
        rotulo = str(bem.get("rotulo") or "").strip()
        descricao = str(bem.get("descricao") or "").strip()
        ano = str(bem.get("ano") or "").strip()
        apelido = str(bem.get("apelido") or "").strip()
    elif vei:
        rotulo = "carro"
        descricao = str(vei.get("modelo") or "").strip()
        ano = str(vei.get("ano") or "").strip()
        apelido = str(vei.get("apelido") or "").strip()
        if not apelido and descricao:
            pal = descricao.split(" ")
            apelido = pal[1] if pal[0].lower() == "jeep" and len(pal) > 1 else pal[0]
    else:
        rotulo = descricao = ano = apelido = ""
    ramo = modelo.get("ramo")
    e_veiculo = rotulo.lower() in VEICULOS or (ramo == 31 and not rotulo)
    return {"rotulo": rotulo, "descricao": descricao, "ano": ano, "apelido": apelido, "e_veiculo": e_veiculo}


# =====================================================================================================================
# tema (claro/escuro) — o cadastro auditado da anfitriã, ou o neutro digno
# =====================================================================================================================
NEUTRO_CLARO = {
    "ink": {"strong": "#15191D", "base": "#2C3238", "muted": "#5A626A"}, "canvas": "#F7F8F9", "surface": "#FFFFFF",
    "surface_2": "#EEF1F3", "elevated": "#FFFFFF", "border": {"hairline": "#E0E4E7", "strong": "#C3C9CE"},
    "primary": {"fill": "#2E3740", "soft": "#E9EDF0", "text": "#2E3740"}, "accent": {"fill": "#2E3740"},
    "positive": {"text": "#00824F"}, "negative": {"text": "#B24B58"},
}
NEUTRO_ESCURO = {
    "ink": {"strong": "#F3F5F7", "base": "#D6DADE", "muted": "#A2A9AF"}, "canvas": "#0C0F12", "surface": "#15191D",
    "surface_2": "#1D2227", "elevated": "#252B31", "border": {"hairline": "#2A3036", "strong": "#3F474F"},
    "primary": {"fill": "#3A4652", "soft": "#1F262C", "text": "#C2CBD3"}, "accent": {"fill": "#C9D1D8"},
    "positive": {"text": "#29A873"}, "negative": {"text": "#E0747F"},
}
NEUTRO_ESCALA = {"100": "#E6EAED", "950": "#0F1317"}

_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _cor_ok(c: Any) -> bool:
    return isinstance(c, str) and bool(_HEX.match(c))


def _fundir(base: dict, extra: Any) -> dict:
    """O tema do cadastro POR CIMA do neutro, só com cores válidas (#RRGGBB). Chave ausente: a do neutro."""
    saida = {}
    for k, v in base.items():
        x = extra.get(k) if isinstance(extra, dict) else None
        if isinstance(v, dict):
            saida[k] = _fundir(v, x)
        else:
            saida[k] = x if _cor_ok(x) else v
    return saida


def hex_rgb(h: str) -> list[int]:
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def lum(h: str) -> float:
    def ch(v: float) -> float:
        v /= 255
        return v / 12.92 if v <= .03928 else ((v + .055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in hex_rgb(h))
    return .2126 * r + .7152 * g + .0722 * b


def contraste(a: str, b: str) -> float:
    x, y = lum(a), lum(b)
    return (max(x, y) + .05) / (min(x, y) + .05)


def sobre(fundo: str, escura: str) -> str:
    """Branco ou a tinta escura — a que tiver mais contraste sobre o fundo."""
    return "#FFFFFF" if contraste(fundo, "#FFFFFF") >= contraste(fundo, escura) else escura


def mistura(a: str, b: str, t: float) -> str:
    A, B = hex_rgb(a), hex_rgb(b)
    return "#" + "".join(f"{round(x * t + y * (1 - t)):02X}" for x, y in zip(A, B))


def legivel(cor: str, fundo: str, alvo: float = 4.6) -> str:
    """Escurece (ou clareia) a cor até ter contraste AA sobre o fundo. Selos nunca abaixo de 4,5:1."""
    rumo = "#000000" if lum(fundo) > .4 else "#FFFFFF"
    passos = 0
    while contraste(cor, fundo) < alvo and passos < 60:
        cor = mistura(cor, rumo, .95)
        passos += 1
    return cor


def temas(anfitria: dict) -> tuple[dict, dict, dict]:
    """(claro, escuro, escala). Só com marca CADASTRADA o tema dela vale; senão o neutro (D-130A-11)."""
    a = anfitria if isinstance(anfitria, dict) else {}
    if a.get("marca_cadastrada") is True and isinstance(a.get("tema_claro"), dict):
        claro = _fundir(NEUTRO_CLARO, a["tema_claro"])
        escuro = _fundir(NEUTRO_ESCURO, a.get("tema_escuro") if isinstance(a.get("tema_escuro"), dict)
                         else a["tema_claro"])
        esc_in = ((a.get("escalas") or {}).get("primary") or {}) if isinstance(a.get("escalas"), dict) else {}
        escala = {
            "100": esc_in.get("100") if _cor_ok(esc_in.get("100")) else claro["primary"]["soft"],
            "950": esc_in.get("950") if _cor_ok(esc_in.get("950")) else claro["ink"]["strong"],
        }
        return claro, escuro, escala
    return _fundir(NEUTRO_CLARO, {}), _fundir(NEUTRO_ESCURO, {}), dict(NEUTRO_ESCALA)


def _vars(t: dict, esc: dict, escuro: bool) -> str:
    p, a = t["primary"]["fill"], t["accent"]["fill"]
    funda, tinta = esc["950"], t["ink"]["strong"]
    v1 = p
    v2 = t["surface_2"] if escuro else esc["100"]
    v3 = t["elevated"] if escuro else t["surface"]
    selo = a if contraste(a, v1) >= 1.8 else "#FFFFFF"
    # "Quero fechar" tem ênfase máxima: se a cor da marca some no fundo (grafite no escuro), vira tinta clara.
    cta = p if contraste(p, t["canvas"]) >= 2.2 else tinta
    sup = t["surface"]
    pos_bg = mistura(t["positive"]["text"], sup, .10)
    neg_bg = mistura(t["negative"]["text"], sup, .10)
    pos, neg = legivel(t["positive"]["text"], pos_bg), legivel(t["negative"]["text"], neg_bg)
    sombra = " ".join(map(str, hex_rgb("#000000" if escuro else funda)))
    return (f"--canvas:{t['canvas']};--surface:{sup};--surface-2:{t['surface_2']};--elevated:{t['elevated']};"
            f"--ink-strong:{tinta};--ink:{t['ink']['base']};--ink-muted:{t['ink']['muted']};"
            f"--line:{t['border']['hairline']};--line-strong:{t['border']['strong']};"
            f"--p:{p};--p-on:{sobre(p, funda)};--p-soft:{t['primary']['soft']};--p-text:{t['primary']['text']};"
            f"--a:{a};--pos:{pos};--neg:{neg};--pos-bg:{pos_bg};--neg-bg:{neg_bg};"
            f"--cta:{cta};--cta-on:{sobre(cta, funda if not escuro else t['canvas'])};"
            f"--pass1:{v1};--pass1-on:{sobre(v1, funda)};--pass2:{v2};--pass2-on:{sobre(v2, tinta if escuro else funda)};"
            f"--pass3:{v3};--pass3-on:{sobre(v3, tinta if escuro else funda)};--badge:{selo};"
            f"--badge-on:{sobre(selo, '#000000')};--shadow-tint:{sombra};")


def css_do_tema(anfitria: dict) -> str:
    """As variáveis de cor, claro e escuro (o escuro também por `data-theme`)."""
    claro, escuro, esc = temas(anfitria)
    c, d = _vars(claro, esc, False), _vars(escuro, esc, True)
    return (f":root{{{c}color-scheme:light}}\n"
            f"@media (prefers-color-scheme: dark){{:root:not([data-theme=\"light\"]){{{d}color-scheme:dark}}}}\n"
            f":root[data-theme=\"dark\"]{{{d}color-scheme:dark}}")


# =====================================================================================================================
# coberturas — valor amigável e comparação com a recomendada
# =====================================================================================================================
INF = 10 ** 9


def _dias(t: str) -> Optional[int]:
    m = re.search(r"(\d+)\s*(dias|diárias|dia)", t, re.I)
    return int(m.group(1)) if m else None


def _km(t: str) -> Optional[int]:
    if re.search(r"ilimitad", t, re.I):
        return INF
    m = re.search(r"([\d.]+)\s*km", t, re.I)
    if not m:
        return None
    try:
        return int(m.group(1).replace(".", ""))
    except ValueError:
        return None


def cobertura(o: dict, chave: str) -> Optional[dict]:
    for c in o.get("coberturas") or []:
        if isinstance(c, dict) and c.get("chave") == chave and str(c.get("nome") or "").strip() \
                and str(c.get("valor") or "").strip():
            return c
    return None


def valor_da_cobertura(c: dict) -> str:
    """O texto amigável: "Auto Reserva 15 dias (111)" → "15 dias"; "Ilimitado" → "Guincho sem limite de km"."""
    bruto = tidy(c.get("valor"))
    k = c.get("chave")
    if k == "reserva" and _dias(bruto) is not None:
        return f"{_dias(bruto)} dias"
    if k == "assistencia" and _km(bruto) is not None:
        km = _km(bruto)
        base = "Guincho sem limite de km" if km == INF else f"Guincho até {_milhar(km)} km"
        return base + (", VIP" if "vip" in bruto.lower() else "")
    if k == "vidros":
        return re.sub(r"^Vidros\s*-\s*", "", bruto)
    return bruto


def _chave_txt(v: str) -> str:
    return re.sub(r"[^a-z0-9à-ú]", "", v.lower())


def _itens(v: str) -> set[str]:
    return {_chave_txt(x) for x in re.split(r",|\+|\s+e\s+|/", v.lower()) if _chave_txt(x)}


def _palavras(v: str) -> list[str]:
    return re.findall(r"[a-zà-ú0-9]+", v.lower())


FRASE_SEM_ORDEM = "nome próprio desta seguradora: a corretora confirma o que cobre"


def comparar_cobertura(chave: str, o: dict, rec: dict) -> tuple[Optional[str], str]:
    """('melhor' | 'mais simples' | None, nota). Só duas etiquetas; o que não se ordena ganha uma frase.

    1º o `nivel` do modelo (ordinal, maior = melhor) quando os DOIS lados têm; senão os fatos do texto
    (dias, km, VIP, itens a mais/a menos); sem fato que ordene → nenhuma etiqueta e a frase.
    """
    co, cr = cobertura(o, chave), cobertura(rec, chave)
    if co is None or cr is None or o is rec:
        return None, ""
    vo, vr = valor_da_cobertura(co), valor_da_cobertura(cr)
    no, nr = numero_inteiro(co.get("nivel")), numero_inteiro(cr.get("nivel"))
    if no is not None and nr is not None:
        if no == nr:
            return None, ""
        return ("melhor" if no > nr else "mais simples"), ""
    if _chave_txt(vo) == _chave_txt(vr):
        return None, ""
    ro, rr = str(co.get("valor")), str(cr.get("valor"))
    if chave == "reserva":
        a, b = _dias(ro), _dias(rr)
        if a and b and a != b:
            return ("melhor" if a > b else "mais simples"), ""
    if chave == "assistencia":
        a, b = _km(ro), _km(rr)
        if a and b and a != b:
            return ("melhor" if a > b else "mais simples"), ""
        if a == b and ("vip" in ro.lower()) != ("vip" in rr.lower()):
            return ("melhor", "com guincho adicional") if "vip" in ro.lower() else ("mais simples",
                                                                                  "sem o atendimento VIP")
    io, ir = _itens(vo), _itens(vr)
    if len(io) > 1 or len(ir) > 1:
        if io < ir:
            falta = [x.strip().lower() for x in re.split(r",|\+|\s+e\s+", vr) if x.strip()
                     and _chave_txt(x) not in io]
            if falta:
                return "mais simples", "sem " + (", ".join(falta[:-1]) + " e " + falta[-1] if len(falta) > 1
                                                 else falta[0])
        if io > ir:
            return "melhor", ""
    po, pr = _palavras(vo), _palavras(vr)
    if len(po) < len(pr) and pr[:len(po)] == po:
        return "mais simples", "sem o " + " ".join(pr[len(po):]).title()
    if len(po) > len(pr) and po[:len(pr)] == pr:
        return "melhor", ""
    return None, FRASE_SEM_ORDEM


def escolher_coberturas(ops: list[dict]) -> tuple[list[str], list[str], bool]:
    """(as do cartão, as de "Mais N coberturas", resto igual nas três?). Batida/roubo e terceiros sempre
    no cartão (as dúvidas nº 1 de quem nunca teve seguro); depois o que MUDA; até 5."""
    rec = ops[0]
    chaves = [c.get("chave") for c in rec.get("coberturas") or [] if isinstance(c, dict) and cobertura(rec, c.get("chave"))]

    def muda(k: str) -> bool:
        vals = set()
        for o in ops:
            c = cobertura(o, k)
            vals.add(_chave_txt(valor_da_cobertura(c)) if c else None)
        return len(vals) > 1

    topo = [k for k in chaves if k in ("casco", "terceiros") or muda(k)]
    for k in ("reserva", "assistencia", "vidros"):
        if len(topo) < 5 and k in chaves and k not in topo:
            topo.append(k)
    topo = [k for k in chaves if k in topo]
    resto = [k for k in chaves if k not in topo]
    return topo, resto, all(not muda(k) for k in resto)


# =====================================================================================================================
# parcelas — "sem juros" só quando a soma bate
# =====================================================================================================================
def _plano(p: Any) -> Optional[tuple[int, Decimal]]:
    if not isinstance(p, dict):
        return None
    v, val = numero_inteiro(p.get("vezes")), dec(p.get("valor"))
    if v is None or v < 1 or val is None or val <= 0:
        return None
    return v, val


def parcelas(o: dict) -> dict:
    """{'sem_juros': (vezes, valor)|None, 'com_juros': (vezes, valor, total, a_mais)|None}.

    `parcelas` é o maior parcelamento; `parcelas_sem_juros` (opcional) o maior sem juros. "Sem juros"
    só se vezes × valor bate com o prêmio (± R$ 1) — o que não bate vira "com juros" com o total."""
    premio = dec(o.get("premio_anual"))
    saida: dict = {"sem_juros": None, "com_juros": None}
    if premio is None:
        return saida
    for chave in ("parcelas_sem_juros", "parcelas"):
        pl = _plano(o.get(chave))
        if pl is None:
            continue
        v, val = pl
        total = val * v
        if abs(total - premio) < 1:
            if saida["sem_juros"] is None or v > saida["sem_juros"][0]:
                saida["sem_juros"] = (v, val)
        elif chave == "parcelas" and total > premio:
            saida["com_juros"] = (v, val, total, total - premio)
    if saida["com_juros"] and saida["sem_juros"] and saida["sem_juros"][0] >= saida["com_juros"][0]:
        saida["com_juros"] = None
    return saida


def parcelas_em_texto(o: dict) -> str:
    """Para a mensagem do WhatsApp: "10x de R$ 555,83 com juros, total R$ 5.558" (sem o "ou")."""
    pc = parcelas(o)
    partes = []
    if pc["sem_juros"]:
        v, val = pc["sem_juros"]
        partes.append(f"{v}x de {brl(val)} sem juros")
    if pc["com_juros"]:
        v, val, total, _ = pc["com_juros"]
        partes.append(f"{v}x de {brl(val)} com juros, total {brl(total, False)}")
    return " ou ".join(partes).replace(NB, " ")


# =====================================================================================================================
# a régua — só as completas; rótulos escolhidos pela LARGURA medida
# =====================================================================================================================
#: Avanço dos glifos da Instrument Sans (por 1000 de corpo), medidos com a fonte da página
#: (📊 06/10/2026, PyMuPDF `Font.text_length` sobre o corte 500 — mais largo que o 400 dos rótulos, então
#: conservador). Os algarismos usam o MAIOR (tabulares). Caractere fora da tabela: 700 (largo).
_AVANCO = {"R": 660, "$": 623, " ": 197, NB: 197, "m": 931, "i": 250, "l": 250, ",": 265, ".": 265}
_DIGITO = 671
#: O corpo do rótulo (CSS `.tick{font-size:13px}`) e a folga mínima entre dois rótulos.
TICK_PX = 13
FOLGA_MIN_PX = 8
#: A largura ÚTIL da régua nos dois desenhos: o estreito vale do menor celular (320 px − 2×16 de margem
#: − 2×10 da régua) até 599 px; o largo, de 600 px (600 − 2×16 − 2×10) em diante.
LARGURA_ESTREITA_PX = 268
LARGURA_LARGA_PX = 548


def largura_do_rotulo(texto: str, px: float = TICK_PX) -> float:
    return sum(_DIGITO if ch.isdigit() else _AVANCO.get(ch, 700) for ch in texto) * px / 1000


def rotulo_do_tick(v: int) -> str:
    if v >= 1000 and v % 1000 == 0:
        return f"R${NB}{v // 1000}{NB}mil"
    if v >= 1000 and v % 100 == 0:
        return f"R${NB}{v // 1000},{(v % 1000) // 100}{NB}mil"
    return f"R${NB}{_milhar(v)}"


def caixas(ticks: list[int], lo: int, hi: int, largura: float) -> list[tuple[float, float]]:
    """A caixa (x0, x1) de cada rótulo, como a página o desenha: na ponta ESQUERDA do eixo (o valor `lo`) ancorado à
    esquerda, na ponta DIREITA (o valor `hi`) à direita, e todo o resto CENTRADO no valor — inclusive o último rótulo
    quando ele não cai na ponta (crítico final, 06/10: o "R$ 8 mil" a 80 % ancorado à direita se lia como 7,6 mil)."""
    out = []
    for t in ticks:
        x = (t - lo) / (hi - lo) * largura
        w = largura_do_rotulo(rotulo_do_tick(t))
        if t == lo:
            out.append((x, x + w))
        elif t == hi:
            out.append((x - w, x))
        else:
            out.append((x - w / 2, x + w / 2))
    return out


def cabem(ticks: list[int], lo: int, hi: int, largura: float, folga: Optional[float] = None) -> bool:
    folga = FOLGA_MIN_PX if folga is None else folga
    cx = caixas(ticks, lo, hi, largura)
    return all(b[0] - a[1] >= folga for a, b in zip(cx, cx[1:])) and all(a[0] >= -0.5 and a[1] <= largura + 0.5
                                                                        for a in cx)


def _passo_base(vmin: int, vmax: int) -> int:
    """O menor passo "redondo" (1, 2, 2,5, 5 × 10^k) com no máximo 8 intervalos entre o piso e o teto."""
    k = 1
    while True:
        for passo in (k, 2 * k, 25 * k // 10 if k >= 10 else 0, 5 * k):
            if passo and -(-vmax // passo) - vmin // passo <= 8:
                return passo
        k *= 10


def eixo_da_regua(valores: Iterable[Any]) -> Optional[dict]:
    """{lo, hi, estreito: [ticks], largo: [ticks]} — os rótulos de cada desenho já sem colisão.

    O passo dos rótulos é o MENOR múltiplo do passo base em que todas as caixas guardam ≥ 8 px entre si
    na largura daquele desenho (a medida dos glifos, não um palpite). Nada cabe? Só as duas pontas."""
    vs = [reais(v) for v in valores]
    vs = [v for v in vs if v is not None and v > 0]
    if len(vs) < 2 or min(vs) == max(vs):
        return None
    base = _passo_base(min(vs), max(vs))
    lo, hi = (min(vs) // base) * base, -(-max(vs) // base) * base

    def escolher(largura: float) -> list[int]:
        for mult in range(1, 9):
            passo = base * mult
            ts = list(range(lo, hi + 1, passo))
            if len(ts) >= 2 and cabem(ts, lo, hi, largura):
                return ts
        return [lo, hi] if cabem([lo, hi], lo, hi, largura) else [lo]

    return {"lo": lo, "hi": hi, "estreito": escolher(LARGURA_ESTREITA_PX), "largo": escolher(LARGURA_LARGA_PX)}


# =====================================================================================================================
# textos que dependem da origem
# =====================================================================================================================
#: A legenda curta da nota, ao lado dela no cartão (crítico final, 06/10: "nossa nota 91/100" só se explicava no
#: rodapé). Os PESOS são da config; o que a nota olha é fixo do produto.
LEGENDA_DA_NOTA = "preço, franquia e coberturas"


def nome_do_canal(modelo: dict) -> str:
    """O nome do canal comparador (o PRODUTO, não uma corretora): o do modelo (`canal.nome`, que a proposta grava da
    config); sem ele, o padrão do produto na config (RT-10: configuração, nunca constante desta página)."""
    canal = modelo.get("canal") if isinstance(modelo.get("canal"), dict) else {}
    nome = str(canal.get("nome") or "").strip()
    if nome:
        return nome
    from app.services.multicalculo.config import PADRAO_DO_PRODUTO

    return str((PADRAO_DO_PRODUTO.get("canal") or {}).get("nome") or "").strip() or "o comparador"


def voz(modelo: dict) -> dict:
    if modelo.get("origem") == "canal":
        return {"nota": "nota do comparador", "porque": "Por que o comparador recomenda",
                "nota_longa": f"A nota do {nome_do_canal(modelo)}, de 0 a 100,"}
    return {"nota": "nossa nota", "porque": "Por que recomendamos", "nota_longa": "Nossa nota, de 0 a 100,"}


def aviso_legal(texto: Any, susep: Any) -> str:
    """Com o nº da SUSEP no cadastro, a frase o cita; sem ele, a afirmação sai (só dado verdadeiro)."""
    t = str(texto or "").strip()
    s = str(susep or "").strip()
    if s:
        return t.replace("registrada na SUSEP", f"registrada na SUSEP sob o nº {s}")
    return re.sub(r",\s*registrada na SUSEP", "", t)
