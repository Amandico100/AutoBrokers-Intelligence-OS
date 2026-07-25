"""Blocos de composição das peças. SPEC-057 §Bloco C.

Um relatório não é um template rígido — é uma **composição de blocos**. O
agente escolhe quais blocos usar e em que ordem, conforme o dado que tem em
mãos; o que ele não faz é escrever CSS. Qualidade visual não pode depender do
humor do modelo, e nada envelhece pior do que HTML gerado por LLM solto.

Cada bloco recebe `props` (dados) e devolve HTML. Bloco sem dado suficiente
devolve estado explícito de vazio, nunca um esqueleto bonito que sugere
informação que não existe.
"""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from . import charts as ch

esc = ch.esc


def _seta(direcao: str) -> str:
    if direcao == "up":
        d = "M3 8.5L6 5l3 3.5"
    elif direcao == "down":
        d = "M3 3.5L6 7l3-3.5"
    else:
        d = "M3 6h6"
    return (f'<svg viewBox="0 0 12 12" fill="none" aria-hidden="true">'
            f'<path d="{d}" stroke="currentColor" stroke-width="1.9" '
            f'stroke-linecap="round" stroke-linejoin="round"/></svg>')


def _direcao(delta: Optional[float], melhor: str = "up") -> str:
    """Direção visual do delta. `melhor='down'` inverte a leitura de cor.

    Sinistralidade caindo é boa notícia; receita caindo não é. Sem este
    parâmetro, todo indicador que melhora ao diminuir apareceria em vermelho —
    e o relatório passaria a mentir com cor.
    """
    if delta is None or abs(delta) < 1e-9:
        return "flat"
    subiu = delta > 0
    bom = subiu if melhor == "up" else not subiu
    return "up" if bom else "down"


def _prosa(texto: str) -> str:
    """Markdown mínimo: negrito, itálico, código e parágrafo.

    Deliberadamente mínimo. Um conversor completo aceitaria HTML embutido e
    abriria injeção num documento que é compartilhado por link público.
    """
    if not texto:
        return ""
    t = esc(texto)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t, flags=re.S)
    t = re.sub(r"(?<![\w*])\*([^*\n]+?)\*(?![\w*])", r"<em>\1</em>", t)
    t = re.sub(r"`([^`]+?)`", r'<code class="ab-num">\1</code>', t)
    paragrafos = [p.strip() for p in re.split(r"\n\s*\n", t) if p.strip()]
    return "".join(f"<p>{p.replace(chr(10), '<br>')}</p>" for p in paragrafos)


def _cabecalho(props: dict) -> str:
    partes = []
    if props.get("eyebrow"):
        partes.append(f'<p class="ab-eyebrow">{esc(props["eyebrow"])}</p>')
    if props.get("title"):
        partes.append(f'<h2 class="ab-h2">{esc(props["title"])}</h2>')
    if props.get("lede"):
        partes.append(f'<p class="ab-lede">{esc(props["lede"])}</p>')
    return "".join(partes)


# ==========================================================================
# Blocos
# ==========================================================================

def cover(props: dict, ctx: dict) -> str:
    """A capa. Cinco segundos para o leitor saber de que se trata e se é bom.

    Logo da corretora, título, um número que importa e uma frase de veredito.
    Nada mais — capa que tenta contar o relatório inteiro não é capa.
    """
    marca = ctx.get("brand") or {}
    logo = ""
    if marca.get("logo_url"):
        logo = (f'<img src="{esc(marca["logo_url"])}" alt="{esc(marca.get("name",""))}" '
                f'class="ab-cover-logo">')
    elif marca.get("name"):
        logo = f'<span class="ab-cover-wordmark">{esc(marca["name"])}</span>'

    destaque = ""
    if props.get("headline_value"):
        rot = props.get("headline_label", "")
        delta = props.get("headline_delta")
        chip = ""
        if delta is not None:
            d = _direcao(delta, props.get("headline_better", "up"))
            chip = (f'<span class="ab-delta" data-dir="{d}">{_seta(d)}'
                    f'{abs(float(delta)):.1f}%</span>')
        destaque = (f'<div class="ab-cover-figure">'
                    f'<span class="ab-cover-figure-label">{esc(rot)}</span>'
                    f'<span class="ab-cover-figure-value ab-num">'
                    f'{esc(props["headline_value"])}</span>{chip}</div>')

    periodo = ""
    if props.get("period"):
        periodo = f'<span class="ab-cover-period">{esc(props["period"])}</span>'

    veredito = ""
    if props.get("verdict"):
        veredito = f'<p class="ab-cover-verdict">{esc(props["verdict"])}</p>'

    return (
        f'<header class="ab-block ab-cover ab-reveal">'
        f'<div class="ab-cover-top">{logo}{periodo}</div>'
        f'<div class="ab-cover-main">'
        f'<p class="ab-eyebrow">{esc(props.get("eyebrow", "Relatório"))}</p>'
        f'<h1 class="ab-cover-title">{esc(props.get("title", ""))}</h1>'
        + (f'<p class="ab-cover-sub">{esc(props["subtitle"])}</p>'
           if props.get("subtitle") else "")
        + f"{veredito}</div>{destaque}</header>")


def kpis(props: dict, ctx: dict) -> str:
    itens = props.get("items") or []
    if not itens:
        return ""
    cartoes = []
    for i, k in enumerate(itens[:6]):
        delta = k.get("delta")
        rodape = ""
        if delta is not None:
            d = _direcao(delta, k.get("better", "up"))
            desde = (f'<span class="ab-kpi-since">{esc(k["since"])}</span>'
                     if k.get("since") else "")
            rodape = (f'<div class="ab-kpi-foot">'
                      f'<span class="ab-delta" data-dir="{d}">{_seta(d)}'
                      f'{abs(float(delta)):.1f}%</span>{desde}</div>')
        elif k.get("since"):
            rodape = f'<div class="ab-kpi-foot"><span class="ab-kpi-since">{esc(k["since"])}</span></div>'

        if k.get("spark"):
            cor = f"var(--ab-chart-{(i % 8) + 1})"
            rodape = (f'<div class="ab-kpi-foot">'
                      + (rodape.replace('<div class="ab-kpi-foot">', "").replace("</div>", "")
                         if rodape else "")
                      + ch.sparkline(k["spark"], cor=cor) + "</div>")

        unidade = (f'<span class="ab-kpi-unit">{esc(k["unit"])}</span>'
                   if k.get("unit") else "")
        cartoes.append(
            f'<div class="ab-kpi ab-reveal" style="--i:{i};'
            f'--kpi-accent:var(--ab-chart-{(i % 8) + 1})">'
            f'<p class="ab-kpi-label">{esc(k.get("label", ""))}</p>'
            f'<span class="ab-kpi-value">{esc(k.get("value", "—"))}{unidade}</span>'
            f"{rodape}</div>")

    return (f'<section class="ab-block">{_cabecalho(props)}'
            f'<div class="ab-kpis">{"".join(cartoes)}</div></section>')


def verdict(props: dict, ctx: dict) -> str:
    if not props.get("text"):
        return ""
    nota = (f'<p class="ab-verdict-note">{esc(props["note"])}</p>'
            if props.get("note") else "")
    return (f'<section class="ab-block ab-reveal"><div class="ab-verdict">'
            f'<p class="ab-verdict-text">{esc(props["text"])}</p>{nota}</div></section>')


def chart(props: dict, ctx: dict) -> str:
    series = [ch.Serie(s.get("name", ""), s.get("values") or [], s.get("color"))
              for s in (props.get("series") or [])]
    corpo = ch.linha(series, ch.Eixo(props.get("labels") or []),
                     tipo_valor=props.get("value_type", "number"),
                     area=props.get("area", True),
                     uid=props.get("uid", "c"))
    return (f'<section class="ab-block ab-reveal">{_cabecalho(props)}'
            f'<div class="ab-card">{corpo}</div></section>')


def ranking(props: dict, ctx: dict) -> str:
    corpo = ch.barras_ranking(props.get("items") or [],
                              tipo_valor=props.get("value_type", "number"),
                              max_itens=props.get("max", 10),
                              destaque=props.get("highlight", 3))
    return (f'<section class="ab-block ab-reveal">{_cabecalho(props)}'
            f'<div class="ab-card">{corpo}</div></section>')


def donut(props: dict, ctx: dict) -> str:
    corpo = ch.rosca(props.get("slices") or [],
                     tipo_valor=props.get("value_type", "number"),
                     rotulo_centro=props.get("center_label", ""),
                     valor_centro=props.get("center_value", ""))
    return (f'<section class="ab-block ab-reveal">{_cabecalho(props)}'
            f'<div class="ab-card">{corpo}</div></section>')


def waterfall(props: dict, ctx: dict) -> str:
    corpo = ch.cascata(props.get("steps") or [],
                       tipo_valor=props.get("value_type", "currency_short"))
    return (f'<section class="ab-block ab-reveal">{_cabecalho(props)}'
            f'<div class="ab-card">{corpo}</div></section>')


def funnel(props: dict, ctx: dict) -> str:
    corpo = ch.funil(props.get("stages") or [],
                     tipo_valor=props.get("value_type", "number"))
    return (f'<section class="ab-block ab-reveal">{_cabecalho(props)}'
            f'<div class="ab-card">{corpo}</div></section>')


def stacked(props: dict, ctx: dict) -> str:
    series = [ch.Serie(s.get("name", ""), s.get("values") or [], s.get("color"))
              for s in (props.get("series") or [])]
    corpo = ch.barras_empilhadas(props.get("categories") or [], series,
                                 tipo_valor=props.get("value_type", "number"))
    return (f'<section class="ab-block ab-reveal">{_cabecalho(props)}'
            f'<div class="ab-card">{corpo}</div></section>')


def table(props: dict, ctx: dict) -> str:
    colunas = props.get("columns") or []
    linhas = props.get("rows") or []
    if not colunas or not linhas:
        return (f'<section class="ab-block">{_cabecalho(props)}'
                f'{ch._sem_dado("Sem linhas para exibir")}</section>')

    cabecalho = "".join(
        f'<th{" class=num" if c.get("align") == "right" else ""}>{esc(c.get("label",""))}</th>'
        for c in colunas)

    corpo = []
    for linha in linhas:
        celulas = []
        for c in colunas:
            v = linha.get(c.get("key", ""))
            classe = " class=num" if c.get("align") == "right" else ""
            if c.get("format"):
                v = ch.fmt_valor(v, c["format"]) if v is not None else "—"
            elif isinstance(v, (int, float)):
                v = ch.fmt_valor(v, "number")
            if c.get("pill") and v not in (None, "", "—"):
                tom = (linha.get(c["key"] + "_tone") or "info")
                v = (f'<span class="ab-pill" style="background:var(--ab-{tom}-soft);'
                     f'color:var(--ab-{tom}-text)">{esc(v)}</span>')
                celulas.append(f"<td{classe}>{v}</td>")
                continue
            celulas.append(f"<td{classe}>{esc(v if v is not None else '—')}</td>")
        corpo.append(f"<tr>{''.join(celulas)}</tr>")

    rodape = ""
    if props.get("total"):
        t = props["total"]
        celulas = []
        for c in colunas:
            v = t.get(c.get("key", ""))
            classe = " class=num" if c.get("align") == "right" else ""
            if v is not None and c.get("format"):
                v = ch.fmt_valor(v, c["format"])
            celulas.append(f"<td{classe}>{esc(v) if v is not None else ''}</td>")
        rodape = f"<tfoot><tr>{''.join(celulas)}</tr></tfoot>"

    return (f'<section class="ab-block ab-reveal">{_cabecalho(props)}'
            f'<div class="ab-table-wrap"><table class="ab-table">'
            f"<thead><tr>{cabecalho}</tr></thead><tbody>{''.join(corpo)}</tbody>"
            f"{rodape}</table></div></section>")


_ICONE_CALLOUT = {
    "info": "M12 16v-5m0-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
    "warning": "M12 9v4m0 4h.01M10.3 3.9L2 18a2 2 0 001.7 3h16.6a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z",
    "positive": "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z",
    "negative": "M12 9v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
}


def callout(props: dict, ctx: dict) -> str:
    if not props.get("text") and not props.get("title"):
        return ""
    tom = props.get("tone", "info")
    icone = (f'<svg class="ab-callout-icon" viewBox="0 0 24 24" fill="none" '
             f'aria-hidden="true"><path d="{_ICONE_CALLOUT.get(tom, _ICONE_CALLOUT["info"])}" '
             f'stroke="currentColor" stroke-width="1.7" stroke-linecap="round" '
             f'stroke-linejoin="round"/></svg>')
    titulo = f'<h4>{esc(props["title"])}</h4>' if props.get("title") else ""
    return (f'<section class="ab-block ab-reveal">'
            f'<div class="ab-callout" data-tone="{esc(tom)}">{icone}'
            f'<div>{titulo}{_prosa(props.get("text", ""))}</div></div></section>')


def actions(props: dict, ctx: dict) -> str:
    itens = props.get("items") or []
    if not itens:
        return ""
    linhas = []
    for i, a in enumerate(itens[:8]):
        meta = []
        if a.get("owner"):
            meta.append(f'<span>{esc(a["owner"])}</span>')
        if a.get("due"):
            meta.append(f'<span><b>{esc(a["due"])}</b></span>')
        if a.get("impact"):
            meta.append(f'<span class="ab-pill" style="background:var(--ab-primary-soft);'
                        f'color:var(--ab-primary-text)">{esc(a["impact"])}</span>')
        linhas.append(
            f'<div class="ab-action ab-reveal" style="--i:{i}">'
            f'<div><h4>{esc(a.get("title", ""))}</h4>'
            + (f'<p>{esc(a["detail"])}</p>' if a.get("detail") else "")
            + f'</div><div class="ab-action-meta">{"".join(meta)}</div></div>')
    return (f'<section class="ab-block">{_cabecalho(props)}'
            f'<div class="ab-actions">{"".join(linhas)}</div></section>')


def prose(props: dict, ctx: dict) -> str:
    if not props.get("text"):
        return ""
    return (f'<section class="ab-block ab-reveal ab-prose">{_cabecalho(props)}'
            f'{_prosa(props["text"])}</section>')


def ring(props: dict, ctx: dict) -> str:
    itens = props.get("items") or []
    if not itens:
        return ""
    aneis = "".join(ch.anel(a.get("value", 0), rotulo=a.get("label", ""))
                    for a in itens[:4])
    return (f'<section class="ab-block ab-reveal">{_cabecalho(props)}'
            f'<div class="ab-card" style="display:flex;gap:36px;justify-content:'
            f'space-around;flex-wrap:wrap">{aneis}</div></section>')


def split(props: dict, ctx: dict) -> str:
    """Dois blocos lado a lado. Usado quando o gráfico precisa da leitura junto."""
    esquerda = render_blocks(props.get("left") or [], ctx)
    direita = render_blocks(props.get("right") or [], ctx)
    classe = "ab-split ab-split--sidebar" if props.get("sidebar") else "ab-split"
    return (f'<section class="ab-block">{_cabecalho(props)}'
            f'<div class="{classe}">{esquerda}{direita}</div></section>')


def sources(props: dict, ctx: dict) -> str:
    """A procedência dos números.

    É o bloco que separa um relatório de uma peça de marketing. Todo número
    aqui aponta para onde foi buscado e quando — sem isso o corretor não tem
    como defender o dado numa conversa com o cliente, e a beleza vira risco.
    """
    itens = props.get("items") or ctx.get("data_sources") or []
    if not itens:
        return ""
    linhas = []
    for s in itens:
        quando = (f'<time datetime="{esc(s.get("as_of",""))}">'
                  f'{esc(s.get("as_of_label") or s.get("as_of",""))}</time>'
                  if s.get("as_of") or s.get("as_of_label") else "")
        linhas.append(f'<li><b>{esc(s.get("label",""))}</b>'
                      f'<span>{esc(s.get("detail",""))}</span>{quando}</li>')
    nota = (f'<p style="margin:14px 0 0">{esc(props["note"])}</p>'
            if props.get("note") else "")
    return (f'<section class="ab-block ab-sources">'
            f'<h4>{esc(props.get("title", "Origem dos dados"))}</h4>'
            f'<ul>{"".join(linhas)}</ul>{nota}</section>')


def footer(props: dict, ctx: dict) -> str:
    marca = ctx.get("brand") or {}
    logo = ""
    if marca.get("logo_url"):
        logo = f'<img src="{esc(marca["logo_url"])}" alt="">'
    nome = f'<span class="ab-foot-name">{esc(marca.get("name", ""))}</span>'

    meta = []
    if ctx.get("generated_label"):
        meta.append(f'Gerado em {esc(ctx["generated_label"])}')
    if marca.get("susep_code"):
        meta.append(f'SUSEP {esc(marca["susep_code"])}')
    if props.get("disclaimer"):
        meta.append(esc(props["disclaimer"]))

    marca_plataforma = ""
    if props.get("show_platform", True):
        marca_plataforma = ('<div class="ab-powered">Inteligência por AutoBrokers</div>')

    return (f'<footer class="ab-foot">'
            f'<div class="ab-foot-brand">{logo}{nome}</div>'
            f'<div class="ab-foot-meta">{"<br>".join(meta)}{marca_plataforma}</div>'
            f"</footer>")


BLOCOS: dict[str, Callable[[dict, dict], str]] = {
    "cover": cover, "kpis": kpis, "verdict": verdict, "chart": chart,
    "ranking": ranking, "donut": donut, "waterfall": waterfall, "funnel": funnel,
    "stacked": stacked, "table": table, "callout": callout, "actions": actions,
    "prose": prose, "ring": ring, "split": split, "sources": sources,
    "footer": footer,
}


def render_blocks(composicao: list[dict], ctx: dict) -> str:
    """Renderiza uma lista de blocos. Bloco desconhecido é ignorado em silêncio
    na peça — e registrado, para virar defeito e não mistério."""
    saida = []
    for i, item in enumerate(composicao or []):
        nome = item.get("block")
        fn = BLOCOS.get(nome)
        if not fn:
            ctx.setdefault("_desconhecidos", []).append(nome)
            continue
        props = dict(item.get("props") or {})
        props.setdefault("uid", f"b{i}")
        try:
            saida.append(fn(props, ctx))
        except Exception as exc:  # noqa: BLE001
            # Um bloco quebrado não pode derrubar o relatório inteiro: o resto
            # do documento continua útil, e a falha vira registro.
            ctx.setdefault("_falhas", []).append(f"{nome}: {type(exc).__name__}")
    return "".join(saida)
