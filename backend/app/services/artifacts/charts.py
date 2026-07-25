"""Gráficos em SVG para as peças. SPEC-057 §Bloco C.

Por que SVG gerado no servidor
------------------------------
Uma biblioteca de gráfico em JavaScript resolveria isto em menos linhas e
custaria três coisas que não podemos pagar: o PDF sairia com o espaço em
branco onde o gráfico deveria estar, a peça pararia de funcionar no e-mail e no
WhatsApp Web, e o visual passaria a depender de um CDN que a CSP do produto
bloqueia. SVG gerado aqui é nítido em qualquer zoom, imprime perfeito e é o
mesmo arquivo na tela, no PDF e no link compartilhado.

Honestidade antes de beleza
---------------------------
Um gráfico bonito com escala truncada é pior do que nenhum gráfico: ele
convence sem ser verdadeiro, e do outro lado tem um corretor decidindo o que
falar para o cliente. Então:

* eixo de barra sempre começa em zero — não há parâmetro para desligar;
* série vazia vira um estado explícito de "sem dado", nunca uma linha reta que
  parece estabilidade;
* toda variação mostra o período de comparação junto;
* cor nunca é o único canal: rótulo e posição carregam a mesma informação.
"""

from __future__ import annotations

import html
import math
from dataclasses import dataclass, field
from typing import Optional, Sequence


def esc(v) -> str:
    return html.escape(str(v), quote=True)


def _n(v: float, casas: int = 0) -> str:
    """Número no formato brasileiro."""
    if v is None:
        return "—"
    try:
        s = f"{float(v):,.{casas}f}"
    except (TypeError, ValueError):
        return "—"
    return s.replace(",", " ").replace(".", ",").replace(" ", ".")


def fmt_valor(v: float, tipo: str = "number", casas: Optional[int] = None) -> str:
    if v is None:
        return "—"
    if tipo == "currency":
        return "R$ " + _n(v, 2 if casas is None else casas)
    if tipo == "currency_short":
        for limite, sufixo in ((1e9, "bi"), (1e6, "mi"), (1e3, "mil")):
            if abs(v) >= limite:
                return f"R$ {_n(v / limite, 1)} {sufixo}"
        return "R$ " + _n(v, 0)
    if tipo == "percent":
        return _n(v, 1 if casas is None else casas) + "%"
    if tipo == "short":
        for limite, sufixo in ((1e9, "bi"), (1e6, "mi"), (1e3, "mil")):
            if abs(v) >= limite:
                return f"{_n(v / limite, 1)} {sufixo}"
        return _n(v, 0)
    return _n(v, 0 if casas is None else casas)


@dataclass
class Serie:
    nome: str
    valores: Sequence[float]
    cor: Optional[str] = None


@dataclass
class Eixo:
    rotulos: Sequence[str] = field(default_factory=list)


SEM_DADO = (
    '<div class="ab-nodata" role="status">'
    '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">'
    '<path d="M3 3v18h18" fill="none" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round"/><path d="M7 14l3-3 3 3 4-5" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round" opacity=".45" stroke-dasharray="2 3"/></svg>'
    "<span>Sem dado no período</span></div>"
)


def _sem_dado(motivo: str = "") -> str:
    if not motivo:
        return SEM_DADO
    return SEM_DADO.replace("Sem dado no período", esc(motivo))


# --------------------------------------------------------------------------
# Escalas
# --------------------------------------------------------------------------

def _passo_bonito(bruto: float) -> float:
    """Arredonda o passo do eixo para 1, 2, 2.5 ou 5 vezes uma potência de 10.

    Eixo com passo 3.7 é tecnicamente correto e ilegível. Quem lê o relatório
    precisa conseguir estimar valores sem conferir o rótulo de cada marca.
    """
    if bruto <= 0:
        return 1.0
    exp = math.floor(math.log10(bruto))
    base = bruto / (10 ** exp)
    for corte, escolha in ((1.0, 1.0), (2.0, 2.0), (2.5, 2.5), (5.0, 5.0)):
        if base <= corte:
            return escolha * (10 ** exp)
    return 10.0 ** (exp + 1)


def escala(minimo: float, maximo: float, marcas: int = 4,
           zero_obrigatorio: bool = True) -> tuple[float, float, list[float]]:
    """Devolve (base, topo, marcas). Base zero por padrão, e sem opção contrária
    nas barras — truncar o eixo de barra exagera diferença e induz a erro."""
    if zero_obrigatorio:
        minimo = min(0.0, minimo)
        maximo = max(0.0, maximo)
    if maximo == minimo:
        maximo = minimo + 1.0
    passo = _passo_bonito((maximo - minimo) / max(1, marcas))
    base = math.floor(minimo / passo) * passo
    topo = math.ceil(maximo / passo) * passo
    ticks, atual = [], base
    while atual <= topo + passo * 0.001 and len(ticks) < 24:
        ticks.append(round(atual, 10))
        atual += passo
    return base, topo, ticks


def _caminho_suave(pontos: list[tuple[float, float]], tensao: float = 0.32) -> str:
    """Curva de Catmull-Rom convertida em Bézier cúbica.

    Tensão baixa de propósito: curva muito solta inventa máximos e mínimos que
    não existem no dado. Aqui ela só tira o serrilhado.
    """
    if len(pontos) < 2:
        return ""
    if len(pontos) == 2:
        return f"M{pontos[0][0]:.2f},{pontos[0][1]:.2f} L{pontos[1][0]:.2f},{pontos[1][1]:.2f}"

    d = [f"M{pontos[0][0]:.2f},{pontos[0][1]:.2f}"]
    for i in range(len(pontos) - 1):
        p0 = pontos[max(0, i - 1)]
        p1, p2 = pontos[i], pontos[i + 1]
        p3 = pontos[min(len(pontos) - 1, i + 2)]
        c1 = (p1[0] + (p2[0] - p0[0]) * tensao / 2, p1[1] + (p2[1] - p0[1]) * tensao / 2)
        c2 = (p2[0] - (p3[0] - p1[0]) * tensao / 2, p2[1] - (p3[1] - p1[1]) * tensao / 2)
        d.append(f"C{c1[0]:.2f},{c1[1]:.2f} {c2[0]:.2f},{c2[1]:.2f} {p2[0]:.2f},{p2[1]:.2f}")
    return " ".join(d)


# --------------------------------------------------------------------------
# Linha / área
# --------------------------------------------------------------------------

def linha(series: list[Serie], eixo: Eixo, *, altura: int = 260,
          largura: int = 720, tipo_valor: str = "number",
          area: bool = True, uid: str = "l1") -> str:
    series = [s for s in series if s.valores]
    if not series or not eixo.rotulos:
        return _sem_dado()

    ml, mr, mt, mb = 52, 16, 18, 34
    w, h = largura - ml - mr, altura - mt - mb

    todos = [v for s in series for v in s.valores if v is not None]
    if not todos:
        return _sem_dado()
    base, topo, ticks = escala(min(todos), max(todos), 4, zero_obrigatorio=min(todos) >= 0)

    n = max(len(eixo.rotulos), max(len(s.valores) for s in series))
    px = lambda i: ml + (w * i / max(1, n - 1))            # noqa: E731
    py = lambda v: mt + h - ((v - base) / (topo - base or 1)) * h   # noqa: E731

    partes = [f'<svg class="ab-chart" viewBox="0 0 {largura} {altura}" '
              f'role="img" preserveAspectRatio="xMidYMid meet">']

    partes.append("<defs>")
    for i, s in enumerate(series):
        cor = s.cor or f"var(--ab-chart-{i + 1})"
        partes.append(
            f'<linearGradient id="g{uid}{i}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0%" stop-color="{cor}" stop-opacity=".26"/>'
            f'<stop offset="100%" stop-color="{cor}" stop-opacity="0"/></linearGradient>')
    partes.append("</defs>")

    # grade horizontal apenas — a vertical compete com os dados
    for t in ticks:
        y = py(t)
        partes.append(f'<line x1="{ml}" y1="{y:.1f}" x2="{ml + w}" y2="{y:.1f}" '
                      f'class="ab-grid"/>')
        partes.append(f'<text x="{ml - 10}" y="{y + 4:.1f}" class="ab-axis" '
                      f'text-anchor="end">{esc(fmt_valor(t, tipo_valor))}</text>')

    for i, s in enumerate(series):
        cor = s.cor or f"var(--ab-chart-{i + 1})"
        pts = [(px(j), py(v)) for j, v in enumerate(s.valores) if v is not None]
        if not pts:
            continue
        d = _caminho_suave(pts)
        if area and len(pts) > 1:
            fecho = (f"{d} L{pts[-1][0]:.2f},{mt + h} L{pts[0][0]:.2f},{mt + h} Z")
            partes.append(f'<path d="{fecho}" fill="url(#g{uid}{i})"/>')
        partes.append(
            f'<path d="{d}" fill="none" stroke="{cor}" stroke-width="2.5" '
            f'stroke-linecap="round" stroke-linejoin="round" class="ab-line"/>')
        # ponto final destacado: é o número que o leitor procura primeiro
        ux, uy = pts[-1]
        partes.append(f'<circle cx="{ux:.2f}" cy="{uy:.2f}" r="4.5" fill="{cor}" '
                      f'class="ab-dot"/>')
        partes.append(f'<circle cx="{ux:.2f}" cy="{uy:.2f}" r="8.5" fill="{cor}" '
                      f'opacity=".18" class="ab-dot"/>')

    passo_rotulo = max(1, n // 8)
    for i, r in enumerate(eixo.rotulos[:n]):
        if i % passo_rotulo and i != n - 1:
            continue
        partes.append(f'<text x="{px(i):.1f}" y="{altura - 10}" class="ab-axis" '
                      f'text-anchor="middle">{esc(r)}</text>')

    partes.append("</svg>")
    if len(series) > 1:
        partes.append(legenda(series))
    return "".join(partes)


# --------------------------------------------------------------------------
# Barras horizontais (ranking)
# --------------------------------------------------------------------------

def barras_ranking(itens: list[dict], *, tipo_valor: str = "number",
                   largura: int = 720, max_itens: int = 10,
                   destaque: int = 0) -> str:
    """`itens`: [{rotulo, valor, nota?}] — já ordenados ou não."""
    itens = [i for i in (itens or []) if i.get("valor") is not None]
    if not itens:
        return _sem_dado()

    itens = sorted(itens, key=lambda x: float(x["valor"]), reverse=True)[:max_itens]
    maximo = max(float(i["valor"]) for i in itens) or 1.0

    linhas = []
    for pos, item in enumerate(itens):
        v = float(item["valor"])
        largura_pct = max(1.2, (v / maximo) * 100)
        classe = "ab-rank-row is-lead" if pos < destaque else "ab-rank-row"
        cor = item.get("cor") or ("var(--ab-primary-fill)" if pos < max(1, destaque)
                                  else "var(--ab-chart-1)")
        nota = (f'<span class="ab-rank-note">{esc(item["nota"])}</span>'
                if item.get("nota") else "")
        linhas.append(
            f'<div class="{classe}">'
            f'<span class="ab-rank-pos">{pos + 1}</span>'
            f'<span class="ab-rank-label" title="{esc(item["rotulo"])}">{esc(item["rotulo"])}</span>'
            f'<span class="ab-rank-track">'
            f'<span class="ab-rank-fill" style="--w:{largura_pct:.1f}%;background:{cor}"></span>'
            f"</span>"
            f'<span class="ab-rank-value">{esc(fmt_valor(v, tipo_valor))}{nota}</span>'
            f"</div>")
    return f'<div class="ab-rank">{"".join(linhas)}</div>'


# --------------------------------------------------------------------------
# Rosca
# --------------------------------------------------------------------------

def rosca(fatias: list[dict], *, tipo_valor: str = "number", tamanho: int = 220,
          rotulo_centro: str = "", valor_centro: str = "") -> str:
    fatias = [f for f in (fatias or []) if (f.get("valor") or 0) > 0]
    if not fatias:
        return _sem_dado()

    total = sum(float(f["valor"]) for f in fatias)
    if total <= 0:
        return _sem_dado()

    r, espessura = tamanho / 2 - 12, 26
    cx = cy = tamanho / 2
    raio = r - espessura / 2
    circunferencia = 2 * math.pi * raio

    arcos, legendas, offset = [], [], 0.0
    for i, f in enumerate(fatias):
        parte = float(f["valor"]) / total
        cor = f.get("cor") or f"var(--ab-chart-{i + 1})"
        comprimento = circunferencia * parte
        arcos.append(
            f'<circle cx="{cx}" cy="{cy}" r="{raio:.2f}" fill="none" stroke="{cor}" '
            f'stroke-width="{espessura}" stroke-linecap="butt" '
            f'stroke-dasharray="{comprimento:.2f} {circunferencia - comprimento:.2f}" '
            f'stroke-dashoffset="{-offset:.2f}" class="ab-arc" '
            f'transform="rotate(-90 {cx} {cy})"/>')
        offset += comprimento
        legendas.append(
            f'<li><i style="background:{cor}"></i>'
            f'<span class="ab-leg-name">{esc(f["rotulo"])}</span>'
            f'<span class="ab-leg-val">{esc(fmt_valor(float(f["valor"]), tipo_valor))}'
            f'<em>{parte * 100:.1f}%</em></span></li>')

    centro = ""
    if valor_centro or rotulo_centro:
        centro = (f'<text x="{cx}" y="{cy - 2}" text-anchor="middle" '
                  f'class="ab-donut-value">{esc(valor_centro)}</text>'
                  f'<text x="{cx}" y="{cy + 18}" text-anchor="middle" '
                  f'class="ab-donut-label">{esc(rotulo_centro)}</text>')

    return (f'<div class="ab-donut">'
            f'<svg viewBox="0 0 {tamanho} {tamanho}" role="img" class="ab-chart">'
            f'{"".join(arcos)}{centro}</svg>'
            f'<ul class="ab-legend">{"".join(legendas)}</ul></div>')


# --------------------------------------------------------------------------
# Cascata (ponte financeira)
# --------------------------------------------------------------------------

def cascata(passos: list[dict], *, tipo_valor: str = "currency_short",
            largura: int = 720, altura: int = 300) -> str:
    """`passos`: [{rotulo, valor, tipo: 'inicial'|'delta'|'final'}]

    A ponte é a forma certa de mostrar "de onde para onde": em vez de dois
    números e uma diferença, ela mostra cada parcela que produziu a diferença.
    """
    passos = passos or []
    if not passos:
        return _sem_dado()

    acumulado, faixas, corrente = [], [], 0.0
    for p in passos:
        v = float(p.get("valor") or 0)
        tipo = p.get("tipo", "delta")
        if tipo in ("inicial", "final"):
            faixas.append((0.0, v if tipo == "inicial" else corrente, tipo))
            corrente = v if tipo == "inicial" else corrente
        else:
            faixas.append((corrente, corrente + v, "delta"))
            corrente += v
        acumulado.append(corrente)

    todos = [x for faixa in faixas for x in faixa[:2]]
    base, topo, ticks = escala(min(todos), max(todos), 4)

    ml, mr, mt, mb = 62, 12, 16, 46
    w, h = largura - ml - mr, altura - mt - mb
    n = len(passos)
    largura_barra = min(64, (w / n) * 0.62)
    px = lambda i: ml + (w * (i + 0.5) / n)                       # noqa: E731
    py = lambda v: mt + h - ((v - base) / (topo - base or 1)) * h  # noqa: E731

    partes = [f'<svg class="ab-chart" viewBox="0 0 {largura} {altura}" role="img">']
    for t in ticks:
        y = py(t)
        partes.append(f'<line x1="{ml}" y1="{y:.1f}" x2="{ml + w}" y2="{y:.1f}" class="ab-grid"/>')
        partes.append(f'<text x="{ml - 10}" y="{y + 4:.1f}" class="ab-axis" '
                      f'text-anchor="end">{esc(fmt_valor(t, tipo_valor))}</text>')

    for i, (p, (de, ate, tipo)) in enumerate(zip(passos, faixas)):
        y0, y1 = py(max(de, ate)), py(min(de, ate))
        x = px(i) - largura_barra / 2
        if tipo in ("inicial", "final"):
            cor = "var(--ab-primary-fill)"
        else:
            cor = ("var(--ab-positive-fill)" if float(p.get("valor") or 0) >= 0
                   else "var(--ab-negative-fill)")
        altura_barra = max(2.0, y1 - y0)
        partes.append(f'<rect x="{x:.1f}" y="{y0:.1f}" width="{largura_barra:.1f}" '
                      f'height="{altura_barra:.1f}" rx="3" fill="{cor}" class="ab-bar"/>')
        if i < n - 1:
            partes.append(f'<line x1="{x + largura_barra:.1f}" y1="{py(ate):.1f}" '
                          f'x2="{px(i + 1) - largura_barra / 2:.1f}" y2="{py(ate):.1f}" '
                          f'class="ab-bridge"/>')
        sinal = "+" if tipo == "delta" and float(p.get("valor") or 0) > 0 else ""
        partes.append(f'<text x="{px(i):.1f}" y="{y0 - 7:.1f}" class="ab-bar-value" '
                      f'text-anchor="middle">{sinal}'
                      f'{esc(fmt_valor(float(p.get("valor") or 0), tipo_valor))}</text>')
        partes.append(f'<text x="{px(i):.1f}" y="{altura - 26}" class="ab-axis" '
                      f'text-anchor="middle">{esc(p.get("rotulo", ""))}</text>')

    partes.append("</svg>")
    return "".join(partes)


# --------------------------------------------------------------------------
# Funil
# --------------------------------------------------------------------------

def funil(etapas: list[dict], *, tipo_valor: str = "number") -> str:
    """`etapas`: [{rotulo, valor}] — do topo para a base."""
    etapas = [e for e in (etapas or []) if e.get("valor") is not None]
    if len(etapas) < 2:
        return _sem_dado("Funil precisa de ao menos duas etapas")

    topo = float(etapas[0]["valor"]) or 1.0
    linhas = []
    for i, e in enumerate(etapas):
        v = float(e["valor"])
        pct_total = v / topo * 100
        anterior = float(etapas[i - 1]["valor"]) if i else v
        conv = (v / anterior * 100) if anterior else 0.0
        perda = anterior - v if i else 0

        queda = ""
        if i:
            # A conversão entre etapas é a informação que o funil existe para
            # dar. Mostrar só o total de cada etapa esconde onde se perde.
            queda = (f'<span class="ab-funnel-conv">{conv:.0f}% da anterior'
                     f'<em>−{esc(fmt_valor(perda, tipo_valor))}</em></span>')

        linhas.append(
            f'<div class="ab-funnel-step">'
            f'<div class="ab-funnel-head"><span>{esc(e["rotulo"])}</span>'
            f'<strong>{esc(fmt_valor(v, tipo_valor))}</strong></div>'
            f'<div class="ab-funnel-bar" style="--w:{max(6.0, pct_total):.1f}%">'
            f'<span style="background:var(--ab-chart-{(i % 8) + 1})"></span></div>'
            f"{queda}</div>")
    return f'<div class="ab-funnel">{"".join(linhas)}</div>'


# --------------------------------------------------------------------------
# Minigráfico e anel de progresso
# --------------------------------------------------------------------------

def sparkline(valores: Sequence[float], *, largura: int = 132, altura: int = 36,
              cor: str = "var(--ab-primary-fill)") -> str:
    vals = [v for v in (valores or []) if v is not None]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    faixa = (hi - lo) or 1.0
    pontos = [(2 + (largura - 4) * i / (len(vals) - 1),
               altura - 3 - (altura - 6) * (v - lo) / faixa) for i, v in enumerate(vals)]
    d = _caminho_suave(pontos, 0.28)
    return (f'<svg class="ab-spark" viewBox="0 0 {largura} {altura}" aria-hidden="true">'
            f'<path d="{d}" fill="none" stroke="{cor}" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
            f'<circle cx="{pontos[-1][0]:.1f}" cy="{pontos[-1][1]:.1f}" r="2.6" fill="{cor}"/>'
            f"</svg>")


def anel(pct: float, *, tamanho: int = 116, rotulo: str = "",
         cor: str = "var(--ab-primary-fill)") -> str:
    pct = max(0.0, min(100.0, float(pct or 0)))
    r = tamanho / 2 - 9
    c = 2 * math.pi * r
    cheio = c * pct / 100
    return (f'<div class="ab-ring">'
            f'<svg viewBox="0 0 {tamanho} {tamanho}" role="img" class="ab-chart">'
            f'<circle cx="{tamanho/2}" cy="{tamanho/2}" r="{r:.1f}" fill="none" '
            f'stroke="var(--ab-border-hairline)" stroke-width="9"/>'
            f'<circle cx="{tamanho/2}" cy="{tamanho/2}" r="{r:.1f}" fill="none" '
            f'stroke="{cor}" stroke-width="9" stroke-linecap="round" '
            f'stroke-dasharray="{cheio:.2f} {c - cheio:.2f}" '
            f'transform="rotate(-90 {tamanho/2} {tamanho/2})" class="ab-arc"/>'
            f'<text x="{tamanho/2}" y="{tamanho/2 + 6}" text-anchor="middle" '
            f'class="ab-ring-value">{pct:.0f}%</text></svg>'
            + (f'<span class="ab-ring-label">{esc(rotulo)}</span>' if rotulo else "")
            + "</div>")


def legenda(series: list[Serie]) -> str:
    itens = "".join(
        f'<li><i style="background:{s.cor or f"var(--ab-chart-{i+1})"}"></i>'
        f"<span>{esc(s.nome)}</span></li>"
        for i, s in enumerate(series))
    return f'<ul class="ab-legend ab-legend--row">{itens}</ul>'


def barras_empilhadas(categorias: list[str], series: list[Serie], *,
                      tipo_valor: str = "number", largura: int = 720,
                      altura: int = 280) -> str:
    if not categorias or not series:
        return _sem_dado()

    ml, mr, mt, mb = 56, 12, 16, 42
    w, h = largura - ml - mr, altura - mt - mb
    totais = [sum((s.valores[i] if i < len(s.valores) else 0) or 0 for s in series)
              for i in range(len(categorias))]
    if not any(totais):
        return _sem_dado()
    base, topo, ticks = escala(0, max(totais), 4)

    largura_barra = min(56, (w / len(categorias)) * 0.58)
    px = lambda i: ml + (w * (i + 0.5) / len(categorias))            # noqa: E731
    py = lambda v: mt + h - ((v - base) / (topo - base or 1)) * h    # noqa: E731

    partes = [f'<svg class="ab-chart" viewBox="0 0 {largura} {altura}" role="img">']
    for t in ticks:
        y = py(t)
        partes.append(f'<line x1="{ml}" y1="{y:.1f}" x2="{ml+w}" y2="{y:.1f}" class="ab-grid"/>')
        partes.append(f'<text x="{ml-10}" y="{y+4:.1f}" class="ab-axis" text-anchor="end">'
                      f'{esc(fmt_valor(t, tipo_valor))}</text>')

    for i, cat in enumerate(categorias):
        acumulado = 0.0
        x = px(i) - largura_barra / 2
        for j, s in enumerate(series):
            v = (s.valores[i] if i < len(s.valores) else 0) or 0
            if v <= 0:
                continue
            y0, y1 = py(acumulado + v), py(acumulado)
            partes.append(
                f'<rect x="{x:.1f}" y="{y0:.1f}" width="{largura_barra:.1f}" '
                f'height="{max(1.5, y1-y0):.1f}" fill="{s.cor or f"var(--ab-chart-{j+1})"}" '
                f'class="ab-bar"/>')
            acumulado += v
        partes.append(f'<text x="{px(i):.1f}" y="{altura-24}" class="ab-axis" '
                      f'text-anchor="middle">{esc(cat)}</text>')
    partes.append("</svg>")
    return "".join(partes) + legenda(series)
