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

#: SPEC-130-C (U4) — os códigos de RAMO do Agger. São os MESMOS de `portal_worker.multicalculo.contrato` (o guarda
#: `test_spec130c_as_paginas.test_os_ramos_sao_os_do_contrato` confere): aqui como constantes porque este módulo é PURO
#: (sem import do motor) e a página só precisa saber de que seguro fala.
RAMO_AUTO, RAMO_RESIDENCIAL, RAMO_CONDOMINIO, RAMO_EMPRESARIAL, RAMO_VIDA = 31, 2, 16, 18, 91

#: Como a página chama o seguro de cada ramo — completa "a cotação/a renovação {…} está pronta". Por que estes textos:
#: são as palavras do Founder (16/10, abertura da SPEC-130-C) para cada ramo; o auto com apelido usa o apelido ("do seu
#: Compass"), como sempre. `seguro` é o nome do seguro numa frase ("o seu seguro residencial").
FALA_DO_RAMO = {
    RAMO_AUTO: {"do_seguro": "do seu seguro", "seguro": "seguro"},
    RAMO_RESIDENCIAL: {"do_seguro": "do seu seguro residencial", "seguro": "seguro residencial"},
    RAMO_CONDOMINIO: {"do_seguro": "do seguro do condomínio", "seguro": "seguro do condomínio"},
    RAMO_EMPRESARIAL: {"do_seguro": "do seguro da sua empresa", "seguro": "seguro da sua empresa"},
    RAMO_VIDA: {"do_seguro": "do seu seguro de vida", "seguro": "seguro de vida"},
}


def ramo_do_modelo(modelo: Any) -> int:
    """O ramo do modelo (`ramo`, inteiro); ausente ou desconhecido → o auto (o contrato da 130-A nasceu auto)."""
    r = modelo.get("ramo") if isinstance(modelo, dict) else None
    return r if numero_inteiro(r) is not None and r in FALA_DO_RAMO else RAMO_AUTO


def e_do_auto(modelo: Any) -> bool:
    return ramo_do_modelo(modelo) == RAMO_AUTO


def do_seguro(modelo: dict) -> str:
    """ "do seu Compass" (auto com apelido) · "do seu seguro" · "do seu seguro residencial" · "do seguro do condomínio" ·
    "do seguro da sua empresa" · "do seu seguro de vida". Sem dado pessoal além do apelido do auto (como sempre)."""
    r = ramo_do_modelo(modelo)
    apelido = o_bem(modelo)["apelido"] if r == RAMO_AUTO else ""
    return f"do seu {apelido}" if apelido else FALA_DO_RAMO[r]["do_seguro"]


#: 🔴 As palavras do AUTO que NUNCA aparecem numa página de RE ou de vida (SPEC-130-C, mutação 3). Um texto do modelo ou
#: da config que as traga (o padrão "Se ela pedir vistoria do carro…", uma dúvida "E se eu bater o carro?") sai da página
#: desses ramos — antes errar por omissão do que falar de carro com quem segura a casa.
PALAVRAS_DO_AUTO = re.compile(r"\b(carros?|guinchos?|fipe|b[ôo]nus|bat(?:er|eu|ida)|oficinas?|ve[íi]culos?|placa)\b",
                              re.I)


def sem_palavra_do_auto(textos: Iterable[str], modelo: dict) -> list[str]:
    """Os textos como vieram no AUTO; nos outros ramos, sem o "do carro" do padrão ("vistoria do carro" → "vistoria") e
    sem os textos que ainda falam de carro."""
    lista = [t for t in textos if isinstance(t, str)]
    if e_do_auto(modelo):
        return lista
    limpos = [re.sub(r"\s+do\s+carro\b", "", t) for t in lista]
    return [t for t in limpos if not PALAVRAS_DO_AUTO.search(t)]


#: SPEC-130-C (U4) — as coberturas de VIDA com o nome que o CLIENTE entende. As chaves são as cruas do Agger (📊 a
#: fixture `tests/fixtures/agger_ramos/vida_resultado.json`, 16/10: isAppMorte, isAppMorteAcidental, isAppInvalidez,
#: isInvalidezDoenca, isDespesasMedicasHospitalares, isDoencasGravesGrupo); `comparacao.coberturas_publicas` as entrega
#: com `nome` = a chave. Chave nova que não esteja aqui vira um nome legível (`nome_legivel`) — NUNCA a chave crua.
NOME_DA_COBERTURA_VIDA = {
    "isAppMorte": "Morte",
    "isAppMorteAcidental": "Morte acidental",
    "isAppInvalidez": "Invalidez por acidente",
    "isInvalidezDoenca": "Invalidez por doença",
    "isDespesasMedicasHospitalares": "Despesas médicas e hospitalares",
    "isDoencasGravesGrupo": "Doenças graves",
    "isDiariaIncapacidade": "Diária por incapacidade",
    "isFuneral": "Assistência funeral",
}
#: SPEC-130-C (F4, a leitura das páginas) — as coberturas de RE que são SIM/NÃO, não valor em R$: o Agger devolve
#: `valorDeNovo` como 1 ou "Sim" (📊 `tests/fixtures/agger_ramos/gravacao_residencial_3.json`) e a comparação o escreve
#: "R$ 1" (`comparacao.coberturas_publicas` formata todo número do RE em reais). Na tela: o nome do seguro e "Incluída";
#: zero/"Não" = não contratada, a linha some. (A comparação não muda — SPEC §1; a tradução é da página.)
COBERTURAS_SIM_NAO_DO_RE = {"valorDeNovo": "Reposição pelo valor de novo"}
_SIM_DO_RE = re.compile(r"^\s*(?:R\$\s*)?(?:1|1,00|1\.0|sim|s|true)\s*$", re.I)
_NAO_DO_RE = re.compile(r"^\s*(?:R\$\s*)?(?:0|0,00|0\.0|n[ãa]o|n|false)?\s*$", re.I)
_RE_CHAVE_CRUA = re.compile(r"^(?:is)?[a-z]+(?:[A-Z][a-z0-9]*)+$|^is[A-Z]")


def nome_legivel(chave: Any) -> str:
    """ "isDespesasExtras" → "Despesas extras" (a chave crua nunca chega à tela)."""
    s = re.sub(r"^is(?=[A-Z])", "", str(chave or "").strip())
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", s).replace("_", " ").strip().lower()
    return s[:1].upper() + s[1:]


def coberturas_para_o_cliente(ops: list[dict], modelo: dict) -> list[dict]:
    """VENDA e RENOVAÇÃO fora do auto: cada cobertura com o nome do cliente (vida pelo dicionário; nome cru → legível) e,
    na vida, o capital em R$ ("100000" → "R$ 100.000"; zero = não contratada, a linha some). Cópias: o modelo de quem
    chama não muda. O auto volta como veio (a página dele não muda um byte)."""
    r = ramo_do_modelo(modelo)
    if r == RAMO_AUTO:
        return ops
    saida = []
    for o in ops:
        linhas = []
        for c in o.get("coberturas") or []:
            if not isinstance(c, dict):
                continue
            chave, nome, valor = str(c.get("chave") or ""), str(c.get("nome") or "").strip(), c.get("valor")
            # conserto KA: o "capital_pedido" (o marcador do leitor quando a seguradora não ecoou o capital) não é uma
            # cobertura — com o `capital_segurado` na opção, o hero e o cartão já dizem "Capital segurado R$ X"
            if r == RAMO_VIDA and chave == "capital_pedido" and capital_da_opcao(o):
                continue
            if r != RAMO_VIDA and chave in COBERTURAS_SIM_NAO_DO_RE:
                if _NAO_DO_RE.match(str(valor if valor is not None else "")):
                    continue
                nome = COBERTURAS_SIM_NAO_DO_RE[chave]
                if _SIM_DO_RE.match(str(valor)):
                    valor = "Incluída"
            elif r == RAMO_VIDA and chave in NOME_DA_COBERTURA_VIDA:
                nome = NOME_DA_COBERTURA_VIDA[chave]
            elif not nome or nome == chave or _RE_CHAVE_CRUA.match(nome):
                nome = nome_legivel(chave or nome)
            if r == RAMO_VIDA and re.fullmatch(r"\s*\d+(?:\.\d+)?\s*", str(valor or "")):
                if dec(valor) is None or dec(valor) <= 0:
                    continue
                valor = brl(valor, False)
            linhas.append(dict(c, nome=nome, valor=valor))
        # conserto K2 (laudo de design R2, pendência 4): no RE a Básica primeiro e a assistência por último — no cartão
        # e no "Comparar" (os dois seguem a ordem da 1ª opção)
        saida.append(dict(o, coberturas=_ordem_do_re(linhas) if r != RAMO_VIDA else linhas))
    return saida


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
    e_veiculo = rotulo.lower() in VEICULOS or (ramo == RAMO_AUTO and not rotulo)
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


def valor_para_o_cliente(chave: Any, valor: str) -> str:
    """Na VENDA e na RENOVAÇÃO (quem lê é o cliente — laudo de design 132-B, D4): os terceiros dizem o que é cada parte
    ("R$ 200 mil + R$ 200 mil" → "R$ 200 mil para danos materiais e R$ 200 mil para danos corporais"; a ordem é a de
    `comparacao.coberturas_publicas`: materiais + corporais). A carteira e o canal seguem com o texto curto."""
    if chave == "terceiros":
        m = re.fullmatch(r"\s*(R\$.+?)\s*\+\s*(R\$.+?)\s*", str(valor or ""))
        if m:
            return f"{m.group(1)} para danos materiais e {m.group(2)} para danos corporais"
    return valor


def nota_para_o_cliente(nota: str) -> str:
    """A frase de `FRASE_SEM_ORDEM` é recado para o CORRETOR conferir; ao cliente ela diz "nem a corretora sabe o que
    cobre" (laudo de design 132-B, D4) — na venda e na renovação ela não aparece."""
    return "" if nota == FRASE_SEM_ORDEM else nota


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
    if not any(k in ("casco", "terceiros") for k in chaves):
        # SPEC-130-C (U4): RE e vida não têm batida/terceiros — o cartão mostra o que MUDA e as primeiras da lista (a
        # básica do RE, a morte da vida), até 4; o resto em "Mais N coberturas". O auto não passa por aqui.
        for k in chaves:
            if len(topo) < 4 and k not in topo:
                topo.append(k)
    for k in ("reserva", "assistencia", "vidros"):
        if len(topo) < 5 and k in chaves and k not in topo:
            topo.append(k)
    topo = [k for k in chaves if k in topo]
    resto = [k for k in chaves if k not in topo]
    return topo, resto, all(not muda(k) for k in resto)


def com_as_a_mais(ops: list[dict]) -> list[dict]:
    """VENDA e RENOVAÇÃO (quem lê é o cliente — confirmação de design 132-B, R6/(e)): as opções com os adicionais do
    modelo (`coberturas_a_mais`: pequenos reparos e afins, `comparacao.coberturas_a_mais`) somados às `coberturas` —
    assim o que só uma opção tem vira LINHA com "a mais" (`proposta_html.so_nas_outras`) no cartão e no "Comparar".
    Cópias: o modelo de quem chama não muda. A carteira e o canal nunca chamam isto (seguem byte a byte)."""
    saida = []
    for o in ops:
        extras = [c for c in o.get("coberturas_a_mais") or []
                  if isinstance(c, dict) and cobertura({"coberturas": [c]}, c.get("chave")) is not None]
        tem = {c.get("chave") for c in o.get("coberturas") or [] if isinstance(c, dict)}
        novas = [c for c in extras if c.get("chave") not in tem]
        saida.append(dict(o, coberturas=list(o.get("coberturas") or []) + novas) if novas else o)
    return saida


def iguais_em_tudo(ops: list[dict]) -> bool:
    """"iguais nas três" só quando as opções são iguais em TUDO o que o modelo sabe das coberturas (confirmação de
    design 132-B, R6/(e)): as mesmas linhas, com os mesmos valores, em todas. E nunca quando uma opção custa mais sem
    diferença conhecida — a "Mais completa" (calculada PEDINDO mais) ou a mesma seguradora, com a mesma franquia, por
    outro preço: a diferença existe e a página não sabe dizer qual, então não afirma igualdade."""
    if len(ops) < 2:
        return True

    def assinatura(o: dict) -> tuple:
        return tuple(sorted((str(c.get("chave")), _chave_txt(valor_da_cobertura(c)))
                            for c in o.get("coberturas") or [] if isinstance(c, dict) and cobertura(o, c.get("chave"))))

    if len({assinatura(o) for o in ops}) > 1:
        return False
    if any(o.get("id") == "mais_completa" for o in ops):
        return False

    def franquia(o: dict) -> Optional[Decimal]:
        f = o.get("franquia") if isinstance(o.get("franquia"), dict) else {}
        return dec(f.get("valor"))

    for i, a in enumerate(ops):
        for b in ops[i + 1:]:
            pa, pb = dec(a.get("premio_anual")), dec(b.get("premio_anual"))
            if (tidy(a.get("seguradora")).lower() == tidy(b.get("seguradora")).lower() and franquia(a) == franquia(b)
                    and pa is not None and pb is not None and reais(abs(pa - pb)) >= 1):
                return False
    return True


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


# =====================================================================================================================
# SPEC-130-C · conserto KA — o que só existe em ALGUNS ramos (laudo de design B2/B4, red team B2)
# =====================================================================================================================
def _positivo(valor: Any) -> bool:
    d = dec(valor)
    return d is not None and d > 0


def sem_franquia_que_nao_existe(modelo: Any) -> Any:
    """Fora do AUTO, franquia 0 ou ausente = SEM franquia: o leitor de RE grava 0 quando a seguradora NÃO informou
    (📊 `leitor_agger.py:585` — 0 em 38 resultados, ausente em 22) e "Franquia R$ 0" afirmaria o que ninguém disse
    (num condomínio que quase sempre tem franquia de vendaval e danos elétricos). As opções perdem a chave `franquia` e
    o ranking fica com `franquia=None` — assim somem o hero, o cartão, o comparar e a lista de seguradoras de uma vez.
    Cópia rasa: o modelo de quem chama não muda; o AUTO volta o MESMO objeto (a página dele não muda um byte)."""
    if not isinstance(modelo, dict) or e_do_auto(modelo):
        return modelo
    m = dict(modelo)
    if isinstance(modelo.get("opcoes"), list):
        m["opcoes"] = [({k: v for k, v in o.items() if k != "franquia"}
                        if isinstance(o, dict) and "franquia" in o
                        and not (isinstance(o.get("franquia"), dict) and _positivo(o["franquia"].get("valor")))
                        else o) for o in modelo["opcoes"]]
    if isinstance(modelo.get("ranking"), list):
        m["ranking"] = [(dict(x, franquia=None) if isinstance(x, dict) and x.get("franquia") is not None
                         and not _positivo(x.get("franquia")) else x) for x in modelo["ranking"]]
    return m


def tem_franquia(modelo: Any, ops: Optional[list] = None) -> bool:
    """A régua pode dizer que "pesa a franquia"? No AUTO sempre (a frase de sempre); fora dele, só quando alguma opção
    TEM franquia (> 0)."""
    if e_do_auto(modelo):
        return True
    lista = ops if ops is not None else (modelo.get("opcoes") if isinstance(modelo, dict) else None) or []
    return any(isinstance(o, dict) and isinstance(o.get("franquia"), dict) and _positivo(o["franquia"].get("valor"))
               for o in lista)


def o_que_a_nota_pesa(modelo: Any, ops: Optional[list] = None) -> str:
    """ "preço, franquia e coberturas" (LEGENDA_DA_NOTA) — ou "preço e coberturas" quando nenhuma opção tem franquia.
    SPEC-130-C (conserto K2, laudo de design R2 B1): fora do auto, sem cobertura detalhada em opção nenhuma (a vida
    cujo cálculo só devolveu o preço), a nota não pesou cobertura — "preço" (ou "preço e franquia"). O auto, como era."""
    lista = ops if ops is not None else (modelo.get("opcoes") if isinstance(modelo, dict) else None) or []
    if not e_do_auto(modelo) and sem_cobertura_detalhada(lista):
        return "preço e franquia" if tem_franquia(modelo, ops) else "preço"
    return LEGENDA_DA_NOTA if tem_franquia(modelo, ops) else "preço e coberturas"


#: o marcador do leitor do robô quando a seguradora NÃO ecoou o capital da vida (`leitor_agger.CAPITAL_PEDIDO` — o
#: guarda `test_spec130c_as_paginas` confere que é o mesmo): não é cobertura, é o capital que o pedido levou
CAPITAL_PEDIDO = "capital_pedido"


def _cobertura_que_conta(c: Any) -> bool:
    """Uma cobertura DETALHADA: não é o marcador do capital pedido e não é um valor zerado (zero = não contratada)."""
    if not isinstance(c, dict) or not str(c.get("chave") or "").strip() or c.get("chave") == CAPITAL_PEDIDO:
        return False
    v = c.get("valor")
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return v > 0
    if isinstance(v, str) and re.fullmatch(r"\s*\d+(?:\.\d+)?\s*", v):
        return float(v) > 0
    return True


def sem_cobertura_detalhada(ops: Any) -> bool:
    """SPEC-130-C (conserto K2, laudo de design R2 B1): nenhuma opção traz cobertura detalhada — 📊 a vida do canário
    (16/10): a seguradora devolve só o preço e o capital (`capital_pedido`). Sem opção nenhuma → False (nada a dizer).
    A MESMA regra no modelo (`multicalculo/proposta.py`) e na página."""
    lista = [o for o in ops or [] if isinstance(o, dict)]
    return bool(lista) and not any(_cobertura_que_conta(c) for o in lista for c in o.get("coberturas") or [])


def vida_sem_coberturas(modelo: Any, ops: Optional[list] = None) -> bool:
    """A página de VIDA cujas opções não detalham cobertura: nela nada diz "cobertura completa" (a página não sabe)."""
    lista = ops if ops is not None else (modelo.get("opcoes") if isinstance(modelo, dict) else None) or []
    return ramo_do_modelo(modelo) == RAMO_VIDA and sem_cobertura_detalhada(lista)


def susep_limpa(anf: Any) -> str:
    """O número da SUSEP da corretora, sem o prefixo que às vezes vem no cadastro ("SUSEP nº: 202031234" → "202031234").
    🔴 UMA regra só (conserto K2, item 7): o topo, o cartão da corretora, o compromisso "o número está no topo" e o
    rodapé leem daqui — dois recortes diferentes fariam o compromisso apontar um número que o topo não mostra."""
    s = str((anf or {}).get("susep") or "") if isinstance(anf, dict) else ""
    # confirmação 2 (17/10): "SUSEP: nº 202031234" e "nº 202031234" também limpam (antes sobrava "nº" → "SUSEP nº nº …")
    return re.sub(r"(?i)^\s*(?:susep\b)?[\s:#.\-]*(?:(?:n[úu]mero|n\s*[º°o]\.?|n\.)\s*)?[\s:#.\-]*", "", s).strip()


#: SPEC-130-C (conserto K2, laudo de design R2 pendência 4) — a ordem das coberturas de RE na tela: a BÁSICA (incêndio,
#: raio e explosão — o coração do seguro de imóvel) primeiro, depois o conteúdo e os vidros; a assistência por último.
#: As chaves são as do motor (`multicalculo.pedido.CHAVE_DA_BASICA` e `comparacao.NOME_DA_COBERTURA_RE`; o guarda
#: confere): aqui como texto porque este módulo é PURO.
CHAVE_DA_BASICA_RE = "isDanosIncendioRaioExplosao"
ORDEM_DO_RE_PRIMEIRO = (CHAVE_DA_BASICA_RE, "isDanosIncendioRaioExplosaoCond", "vidros")
ORDEM_DO_RE_POR_ULTIMO = ("assist24hs",)


def _ordem_do_re(linhas: list[dict]) -> list[dict]:
    def peso(c: dict) -> int:
        k = str(c.get("chave") or "")
        if k in ORDEM_DO_RE_PRIMEIRO:
            return ORDEM_DO_RE_PRIMEIRO.index(k)
        return len(ORDEM_DO_RE_PRIMEIRO) + (1 if k in ORDEM_DO_RE_POR_ULTIMO else 0)
    return sorted(linhas, key=peso)                 # estável: o resto fica na ordem em que veio


def aviso_do_ramo(texto: Any, susep: Any, modelo: Any) -> str:
    """O aviso legal (`aviso_legal`) com o que vale para o RAMO: na VIDA não há vistoria (a seguradora pede a declaração
    de saúde) — "e da vistoria, se houver" sai. O RE fica com a vistoria (do imóvel, real); o auto, como sempre."""
    t = aviso_legal(texto, susep)
    if ramo_do_modelo(modelo) == RAMO_VIDA:
        t = re.sub(r"\s+e da vistoria(?:,\s*se houver)?", "", t)
    return t


def capital_da_opcao(o: Any) -> Optional[dict]:
    """{valor (R$ inteiro, texto), pedido (bool)} do capital segurado da opção de VIDA — `o["capital_segurado"] = {valor,
    origem: "pedido"|"seguradora"}` (gravado por `multicalculo/proposta.py`). Sem o campo ou sem valor > 0 → None (a
    página nunca inventa um capital)."""
    c = o.get("capital_segurado") if isinstance(o, dict) else None
    if not isinstance(c, dict) or not _positivo(c.get("valor")):
        return None
    return {"valor": brl(c["valor"], False), "pedido": str(c.get("origem") or "").strip().lower() == "pedido"}
