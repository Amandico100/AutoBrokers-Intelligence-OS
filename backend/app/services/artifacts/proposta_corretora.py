"""O BLOCO DA CORRETORA — um componente, três vozes (SPEC-130-C · U2 · D-130C-02).

As três páginas do cliente — a COTAÇÃO (venda: quem ainda não é cliente), a RENOVAÇÃO (quem já é) e o QUEM COBRA MENOS
(o canal) — apresentam a corretora com o MESMO bloco, nesta ordem (as palavras do Founder, 16/10):

    1. o título do momento   venda "Por que fechar com a <Nome>" · renovação "Mais um ano em boas mãos" (D-130C-07) ·
                             canal "Quem é a corretora que cobra menos?"
    2. o cartão              logo/monograma, nome, cidade, o texto do momento e os FATOS (só com dado)
    3. dois selos            "Nível 5" (o selo do programa, `anfitria.selo`) e "Corretora premiada" (SÓ com prêmio)
    4. "<Nome>, corretora premiada Nível 5" (sem prêmio: "<Nome>, corretora Nível 5"; sem selo: 3–5 somem)
    5. os itens do Nível 5   a lista do programa (a do modelo vence)
    6. as fotos              carrossel de CSS (scroll-snap), até 4, com legenda; sem foto o carrossel SOME

```
bloco_da_corretora(modelo, momento, *, nome_canal="")   o HTML do bloco ("" sem o nome da corretora)
CSS_DO_BLOCO_DA_CORRETORA                               o CSS, nas DUAS famílias de tokens (marca e canal)
fotos_da_anfitria · premios_da_anfitria                  o que o modelo traz, já validado (nada inventado)
```

🔴 Bloco sem dado SOME (D-132B-02, CDC art. 37): nenhum ano, nota, prêmio ou foto inventados. "Corretora premiada" só com
`anfitria.premios` não vazio (D-130C-04). Nenhum script novo: a página tem UM script (o da CSP) e ele só dirige o `#track`
das opções — o carrossel das fotos é scroll-snap PURO e não usa `.slot`, `.tab` nem `#track`. Nenhum nome de corretora
aqui (CLAUDE.md §13.9): tudo vem do modelo.
"""

from __future__ import annotations

import html
import math
import re
from typing import Any, Optional

from . import proposta_apresentacao as AP

#: 💭 Os 5 itens do "Corretora Nível 5" — o RASCUNHO do programa (PRONTIDAO-DA-133-A §8, para o Founder lapidar;
#: D-130A1-04: a lista tem de estar escrita e pública antes de abrir ao público). O modelo pode trazer a própria lista
#: (`anfitria.selo_criterios` ou `canal.selo_criterios`: [[título, detalhe], …]) — vence esta. (Veio da página do canal
#: na SPEC-130-C: agora as TRÊS páginas a mostram.)
CRITERIOS_DO_NIVEL_5 = (
    ("Registro ativo na SUSEP", "conferido no cadastro e na consulta pública."),
    ("Cota em todas as seguradoras que aceitam o seu perfil", "o multicálculo prova, a cada pedido."),
    ("Responde na hora, 24 horas", "o agente da corretora atende; a pessoa da corretora assume no horário dela."),
    ("Acompanha o sinistro do aviso ao fim", "cada passo fica registrado."),
    ("Reputação pública conferida", "Google e Reclame Aqui lidos e respondidos — a nota aparece como está, sem filtro."),
)
#: a versão da lista acima (sobe quando o texto muda — o consumidor vê qual lista valia)
VERSAO_DOS_CRITERIOS = 1

#: Quantas fotos a página mostra (a marca guarda até 8 — §4 da SPEC; a página, as 4 primeiras) e quantos prêmios o bloco
#: lê. São do DESENHO da página (D-130C-03), não número comercial.
TETO_DE_FOTOS = 4
TETO_DE_PREMIOS = 10
#: O tamanho máximo de UMA foto embutida (os caracteres do `data:`): a marca reduz cada foto a ≤ 90 KB em WEBP (≈ 120 mil
#: caracteres em base64); acima de 400 mil a foto não é a da marca reduzida — fica fora (a página nunca carrega 4 MB).
TETO_DA_FOTO = 400_000
#: Só imagem raster em base64 — o MESMO rigor do logo (`proposta_html._LOGO_OK`), SEM svg (que pode carregar script)
_FOTO_OK = re.compile(r"^data:image/(?:webp|jpeg|png);base64,[A-Za-z0-9+/=]+$")

MOMENTOS = ("venda", "renovacao", "canal")


def _e(texto: Any) -> str:
    return html.escape("" if texto is None else str(texto), quote=True)


def _anf(modelo: dict) -> dict:
    a = modelo.get("anfitria") if isinstance(modelo, dict) else None
    return a if isinstance(a, dict) else {}


# =====================================================================================================================
# o que o modelo traz — validado (nada inventado)
# =====================================================================================================================
def fotos_da_anfitria(modelo: dict) -> list[dict]:
    """[{src, legenda}] — só `data:image/(webp|jpeg|png);base64,…` dentro do teto; a legenda ≤ 80 caracteres; até 4."""
    saida = []
    for f in _anf(modelo).get("fotos") or []:
        if not isinstance(f, dict):
            continue
        src = str(f.get("src") or "")
        if len(src) > TETO_DA_FOTO or not _FOTO_OK.match(src):
            continue
        legenda = re.sub(r"\s+", " ", str(f.get("legenda") or "")).strip()[:80]
        saida.append({"src": src, "legenda": legenda})
        if len(saida) == TETO_DE_FOTOS:
            break
    return saida


def premios_da_anfitria(modelo: dict) -> list[dict]:
    """[{nome, ano}] — nome ≤ 80, ano inteiro plausível ou None; até 10. Sem nome, não é prêmio."""
    saida = []
    for p in _anf(modelo).get("premios") or []:
        if not isinstance(p, dict):
            continue
        nome = re.sub(r"\s+", " ", str(p.get("nome") or "")).strip()[:80]
        if not nome:
            continue
        ano = AP.numero_inteiro(p.get("ano"))
        saida.append({"nome": nome, "ano": ano if ano is not None and 1900 <= ano <= 2100 else None})
        if len(saida) == TETO_DE_PREMIOS:
            break
    return saida


def _premio_em_texto(p: dict) -> str:
    return f"{p['nome']} · {p['ano']}" if p.get("ano") else p["nome"]


def nivel_do_selo(selo: str) -> str:
    """"Corretora Nível 5" → "Nível 5" (o nome do selo SEM a palavra "Corretora")."""
    m = re.match(r"^corretora\s+(.+)$", selo, re.I)
    return m.group(1).strip() if m else selo


def criterios(modelo: dict) -> tuple[list[tuple[str, str]], Optional[str]]:
    """(a lista, a versão) — a do modelo (`anfitria.selo_criterios`, senão `canal.selo_criterios`) vence a do programa.
    A versão: a da lista do programa, ou `selo_versao` do modelo (o que veio junto com a lista dele)."""
    canal = modelo.get("canal") if isinstance(modelo.get("canal"), dict) else {}
    for dono in (_anf(modelo), canal):
        crit = dono.get("selo_criterios")
        if (isinstance(crit, list) and crit and all(isinstance(x, (list, tuple)) and len(x) == 2 for x in crit)):
            lista = [(str(a).strip(), str(b).strip()) for a, b in crit if str(a).strip()]
            if lista:
                versao = str(dono.get("selo_versao") or canal.get("selo_versao") or "").strip()
                return lista, (versao or "do modelo")
    return list(CRITERIOS_DO_NIVEL_5), str(VERSAO_DOS_CRITERIOS)


def anos_de_mercado(anf: dict, modelo: dict) -> Optional[tuple[int, int]]:
    """(anos, desde) — só com o ano de fundação da marca e a data do modelo; 1 a 199 anos."""
    desde = AP.numero_inteiro(anf.get("desde"))
    ano = re.match(r"^(\d{4})", str(modelo.get("gerado_em") or modelo.get("validade_ate") or ""))
    if desde and ano and 1 <= int(ano.group(1)) - desde < 200:
        return int(ano.group(1)) - desde, desde
    return None


def _google(anf: dict) -> Optional[tuple[str, int, str]]:
    g = anf.get("google") if isinstance(anf.get("google"), dict) else None
    if not g:
        return None
    nota, n = AP.dec(g.get("nota")), AP.numero_inteiro(g.get("avaliacoes"))
    if nota is None or n is None or n < 1:
        return None
    return f"{nota:.1f}".replace(".", ","), n, str(g.get("fonte") or "").strip()


def _susep(anf: dict) -> str:
    return re.sub(r"^\s*susep\b[\s:nº°.#-]*", "", str(anf.get("susep") or ""), flags=re.I).strip()


def _logo(anf: dict) -> Optional[str]:
    from .proposta_html import _logo as logo
    return logo(anf)


# =====================================================================================================================
# os selos (SVG inline, decorativos — o nome vai em texto ao lado)
# =====================================================================================================================
def selo_do_programa(nivel: str) -> str:
    """O selo de certificação do programa (o "ISO" do Founder): anel duplo, o nível no centro."""
    num = re.search(r"(\d+)\s*$", nivel)
    centro = (f'<text x="60" y="80" text-anchor="middle" class="s5-num">{_e(num.group(1))}</text>' if num else
              '<path d="M42 62l12 12 24-26" fill="none" stroke-width="7" stroke-linecap="round" stroke-linejoin="round" '
              'class="s5-ok"/>')
    palavra = _e((nivel[: num.start()] if num else "").strip().upper()[:10])
    return ('<svg class="s5" viewBox="0 0 120 120" aria-hidden="true" focusable="false">'
            '<circle cx="60" cy="60" r="57" class="s5-out"/><circle cx="60" cy="60" r="49" class="s5-in"/>'
            '<circle cx="60" cy="60" r="44" class="s5-line" fill="none" stroke-width="1.6" stroke-dasharray="2 3.2"/>'
            + (f'<text x="60" y="44" text-anchor="middle" class="s5-word">{palavra}</text>' if palavra else "")
            + centro + "</svg>")


def _louros() -> str:
    """Os dois ramos de louro do selo "premiada" — folhas tangentes a um arco, geradas uma vez (texto fixo)."""
    folhas = []
    for lado in (-1, 1):
        for k in range(6):
            ang = math.radians(90 + lado * (28 + k * 21))        # do pé do selo subindo pelos lados
            r = 37.5
            x, y = 60 + r * math.cos(ang), 64 + r * math.sin(ang)
            giro = math.degrees(ang) + (20 if lado < 0 else -20)
            folhas.append(f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="3.1" ry="7.2" transform="rotate({giro:.1f} {x:.1f} '
                          f'{y:.1f})"/>')
    return "".join(folhas)


_LOUROS = _louros()


def selo_premiada(ano: Optional[int]) -> str:
    """O selo "Corretora premiada": louros, a estrela e — com o ano do prêmio mais recente — o ano."""
    estrela = ('<path class="sp-star" d="M60 30l5.6 11.4 12.6 1.8-9.1 8.9 2.1 12.5L60 58.7l-11.2 5.9 2.1-12.5-9.1-8.9 '
               '12.6-1.8z"/>')
    return ('<svg class="s5 sp" viewBox="0 0 120 120" aria-hidden="true" focusable="false">'
            '<circle cx="60" cy="60" r="57" class="sp-out"/><circle cx="60" cy="60" r="49" class="sp-in"/>'
            f'<g class="sp-leaf">{_LOUROS}</g>{estrela}'
            + (f'<text x="60" y="88" text-anchor="middle" class="sp-ano">{ano}</text>' if ano else
               '<path class="sp-fita" d="M48 76h24l-4 6 4 6H48l4-6z"/>')
            + "</svg>")


def _P(d: str) -> str:
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true" focusable="false">{d}</svg>')


_ICO = {
    "check": _P('<path d="M5 12.5l4.2 4.2L19 7"/>'),
    "star": ('<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false"><path d="M12 2.8l2.8 6 '
             '6.5.7-4.9 4.4 1.4 6.4L12 17l-5.8 3.3 1.4-6.4-4.9-4.4 6.5-.7z"/></svg>'),
    "louro": _P('<path d="M12 21V9"/><path d="M12 13c-3 0-5-2-5.5-5 3 0 5 2 5.5 5zM12 13c3 0 5-2 5.5-5-3 0-5 2-5.5 5zM12 9'
                'c-1.8-.6-2.7-2.2-2.5-4.2 1.9.5 2.8 2.1 2.5 4.2zM12 9c1.8-.6 2.7-2.2 2.5-4.2-1.9.5-2.8 2.1-2.5 4.2z"/>'),
    "pino": _P('<path d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0113 0c0 5.4-6.5 11-6.5 11z"/><circle cx="12" cy="10" r="2.3"/>'),
}


# =====================================================================================================================
# o bloco
# =====================================================================================================================
def _titulo(momento: str, nome: str) -> str:
    if momento == "renovacao":
        return "Mais um ano em boas mãos"
    if momento == "canal":
        return "Quem é a corretora que cobra menos?"
    return f"Por que fechar com a {nome}"


def _voz(momento: str, nome: str, modelo: dict, nome_canal: str) -> str:
    """O texto do cartão em cada momento — só o que é verdade nesse momento."""
    n = _e(nome)
    if momento == "renovacao":
        ren = modelo.get("renovacao") if isinstance(modelo.get("renovacao"), dict) else {}
        anos = AP.numero_inteiro(ren.get("anos"))
        rel = (f"Você renova com a gente há {anos}{AP.NB}{'ano' if anos == 1 else 'anos'}. "
               if anos and anos >= 1 else "")             # SÓ com prova (CDC art. 37; a 131-B mede os elos)
        from .proposta_html import _ranking
        n_rk = len(_ranking(modelo))
        revisou = (f"revisou {n_rk} seguradoras para a sua renovação" if n_rk > 1
                   else "preparou a sua renovação")
        return (f"<b>Quem já conhece o seu seguro.</b> {_e(rel)}A {n} {revisou} e continua do seu lado — no dia a dia e, "
                "principalmente, se você precisar acionar o seguro.")
    if momento == "canal":
        return (f"<b>Quem atende e cuida do seu seguro é a corretora.</b> O {_e(nome_canal)} só compara e indica quem "
                "cobrou menos com a mesma cobertura completa.")
    return (f"<b>Quem representa você é a corretora.</b> A {n} compara as seguradoras, explica cada cobertura antes de "
            "você decidir e fica do seu lado diante da seguradora — na contratação e, principalmente, se você precisar "
            "acionar o seguro.")


def _fatos(momento: str, anf: dict, modelo: dict) -> tuple[list[str], str]:
    """(os fatos do cartão, a linha da fonte). Cada um SÓ com dado. A SUSEP só no canal (na venda e na renovação ela
    mora no topo e no rodapé — laudo de design 132-B, D6); o Google nunca na renovação (quem já é cliente não precisa de
    prova de estranho — laudo I3 §2.3); o site no canal (na venda/renovação ele está em "quem cuida de você")."""
    fatos, fonte = [], ""
    g = _google(anf) if momento != "renovacao" else None
    if g:
        fatos.append(f'<li><b>{_ICO["star"]}{g[0]}</b> <span>no Google, {g[1]} '
                     f'{"avaliações" if g[1] != 1 else "avaliação"}</span></li>')
        if g[2]:
            fonte = f'<p class="bc-fonte">Nota e avaliações: {_e(AP.aspas_tipograficas(g[2]))}.</p>'
    if momento == "canal" and _susep(anf):
        fatos.append(f'<li><b>{_e(_susep(anf))}</b> <span>registro na SUSEP</span></li>')
    anos = anos_de_mercado(anf, modelo)
    if anos:
        fatos.append(f'<li><b>{anos[0]}{AP.NB}{"ano" if anos[0] == 1 else "anos"}</b> '
                     f'<span>no mercado, desde {anos[1]}</span></li>')
    if momento == "venda":
        venda = modelo.get("venda") if isinstance(modelo.get("venda"), dict) else {}
        marca = venda.get("marca") if isinstance(venda.get("marca"), dict) else {}
        parceiras = AP.numero_inteiro(marca.get("seguradoras_parceiras"))
        if parceiras and parceiras > 1:
            fatos.append(f'<li><b>{parceiras} seguradoras</b> <span>parceiras da corretora</span></li>')
    site = str(anf.get("site") or "").strip()
    if momento == "canal" and re.fullmatch(r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}(/[A-Za-z0-9._~/-]*)?", site or ""):
        fatos.append(f'<li><a href="https://{_e(site)}" rel="noopener">{_e(site)}</a> <span>site da corretora</span></li>')
    return fatos, fonte


def bloco_da_corretora(modelo: dict, momento: str, *, nome_canal: str = "", sobre: str = "",
                       diferenciais: Optional[list[str]] = None) -> str:
    """O bloco inteiro (`<section class="s bc">`). `momento`: "venda" | "renovacao" | "canal". Sem o nome da corretora,
    "" (não há quem apresentar). `sobre` (a 1ª frase do "sobre" da marca) e `diferenciais` só a venda passa."""
    modelo = modelo if isinstance(modelo, dict) else {}
    momento = momento if momento in MOMENTOS else "venda"
    anf = _anf(modelo)
    nome = str(anf.get("nome") or "").strip()
    if not nome:
        return ""
    logo = _logo(anf)
    cidade = str(anf.get("cidade") or "").strip()
    selo = str(anf.get("selo") or "").strip()
    premios = premios_da_anfitria(modelo)
    fotos = fotos_da_anfitria(modelo)

    # ---- 2. o cartão
    if logo:
        marca = f'<span class="bc-logo"><img src="{_e(logo)}" alt="" height="40"></span>'
    else:
        marca = f'<span class="bc-mono" aria-hidden="true">{_e(AP.monograma(nome))}</span>'
    fatos, fonte = _fatos(momento, anf, modelo)
    difs = [d.strip() for d in diferenciais or [] if isinstance(d, str) and d.strip()]
    # sem o selo, os prêmios moram no cartão (com o selo, o selo "premiada" os diz — nunca duas vezes)
    premios_no_cartao = ""
    if premios and not selo:
        premios_no_cartao = ('<ul class="bc-premios">' + "".join(
            f'<li>{_ICO["louro"]}<span>{_e(_premio_em_texto(p))}</span></li>' for p in premios) + "</ul>")
    cartao = (f'<div class="bc-card"><div class="bc-capa" aria-hidden="true"></div><div class="bc-corpo">'
              f'<div class="bc-id">{marca}</div>'
              f'<h3 class="bc-nome">{_e(nome)}</h3>'
              + (f'<p class="bc-cidade">{_ICO["pino"]}<span>{_e(cidade)}</span></p>' if cidade else "")
              + f'<p class="bc-voz">{_voz(momento, nome, modelo, nome_canal)}</p>'
              + (f'<ul class="bc-fatos">{"".join(fatos)}</ul>' if fatos else "") + fonte
              + ('<ul class="difs">' + "".join(f'<li>{_ICO["check"]}<span>{_e(AP.nbsp(d))}</span></li>' for d in difs)
                 + "</ul>" if difs else "")
              + premios_no_cartao + "</div></div>")

    # ---- 3–5. os selos, o título do nível e os itens (só com o selo ligado)
    n5 = ""
    if selo:
        nivel = nivel_do_selo(selo)
        lista, versao = criterios(modelo)
        tiles = [f'<li class="bc-selo">{selo_do_programa(nivel)}<p><b>{_e(selo)}</b> '
                 f'<span>{len(lista)} itens conferidos</span></p></li>']
        if premios:                                    # 🔴 D-130C-04 / CDC art. 37: "premiada" SÓ com prêmio cadastrado
            mais = len(premios) - 1
            tiles.append(f'<li class="bc-selo bc-ouro">{selo_premiada(premios[0]["ano"])}<p><b>Corretora premiada</b> '
                         f'<span>{_e(_premio_em_texto(premios[0]))}'
                         + (f" e mais {mais}" if mais else "") + "</span></p></li>")
        titulo_n5 = f"{nome}, corretora {'premiada ' if premios else ''}{nivel}"
        if momento == "canal":
            sub = (f"Só cotamos com Corretoras {_e(nivel)}. O selo é do programa {_e(nome_canal)}, não do tamanho da "
                   f"corretora: qualquer corretora pode ser {_e(nivel)}, desde que cumpra os {len(lista)} itens — e "
                   "cada um é conferido.")
        else:
            sub = (f"{_e(nivel)} é um selo de conduta, não de tamanho: a {_e(nome)} cumpre os {len(lista)} itens "
                   "abaixo — e cada um é conferido.")
        itens = "".join(f'<li><span class="bc-ck">{_ICO["check"]}</span><span><b>{_e(a)}</b>: {_e(b)}</span></li>'
                        for a, b in lista)
        n5 = (f'<div class="bc-n5"><ul class="bc-selos{" um" if len(tiles) == 1 else ""}" aria-label="Selos da '
              f'{_e(nome)}">{"".join(tiles)}</ul>'
              f'<h3 class="bc-titulo">{_e(titulo_n5)}</h3><p class="bc-sub">{sub}</p>'
              f'<ul class="bc-itens">{itens}</ul>'
              f'<p class="bc-v">Lista do programa {_e(selo)} · versão {_e(versao)}</p></div>')

    # ---- 6. as fotos (scroll-snap PURO; lado a lado no notebook)
    fotos_html = ""
    if fotos:
        n = len(fotos)
        figs = "".join(
            f'<figure class="bc-foto" role="group" aria-roledescription="slide" aria-label="Foto {i + 1} de {n}">'
            f'<img src="{_e(f["src"])}" alt="{_e(f["legenda"] or "Foto da " + nome)}">'
            + (f'<figcaption>{_e(f["legenda"])}</figcaption>' if f["legenda"] else "") + "</figure>"
            for i, f in enumerate(fotos))
        fotos_html = (f'<div class="bc-galeria"><h3 class="bc-fotos-t">A {_e(nome)} de perto</h3>'
                      + (f'<p class="bc-dica">{n} fotos · arraste para o lado</p>' if n > 1 else "")
                      + f'<div class="bc-fotos n{n}" tabindex="0" role="region" aria-roledescription="carrossel" '
                        f'aria-label="Fotos da {_e(nome)}">{figs}</div></div>')

    return (f'<section class="s bc" id="corretora" aria-labelledby="h-corretora">'
            f'<h2 id="h-corretora">{_e(_titulo(momento, nome))}</h2>'
            + (f'<p class="sub bc-sobre">{_e(sobre)}</p>' if sobre else "")
            + f'<div class="bc-grade{" so" if not n5 else ""}">{cartao}{n5}</div>{fotos_html}</section>')


# =====================================================================================================================
# o CSS — tokens próprios do bloco, com padrão para as DUAS famílias (a marca: --p/--badge; o canal: --navy/--lime)
# =====================================================================================================================
CSS_DO_BLOCO_DA_CORRETORA = r"""
/* SPEC-130-C: o bloco da corretora. Cada página pode trocar os --bc-*; o padrão lê o tema da marca (venda/renovação)
   e, sem ele, o do canal. Claro e escuro vêm dos tokens da página; o ouro do "premiada" é do selo (igual nos dois). */
.bc{--bc-marca:var(--p,var(--navy,#2E3740));--bc-marca-on:var(--p-on,#FFFFFF);--bc-acento:var(--badge,var(--lime,#FFFFFF));
  --bc-selo:var(--bc-marca);--bc-selo-acento:var(--bc-acento);--bc-selo-num:var(--bc-marca-on);
  --bc-ok:var(--pos);--bc-ok-bg:var(--pos-bg);--bc-gutter:var(--gutter,16px);
  --bc-ouro:#C9952B;--bc-ouro-claro:#F3CF63;--bc-ouro-fundo:#2B2213;--bc-ouro-tinta:#8A5A00}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .bc{--bc-ouro-tinta:#E8BE55}}
:root[data-theme="dark"] .bc{--bc-ouro-tinta:#E8BE55}
.bc-sobre{font-size:16.5px;color:var(--ink)}
.bc-grade{margin-top:18px;display:grid;gap:18px}
/* o cartão: a capa na cor da marca, o logo numa placa branca sobre a borda dela */
.bc-card{position:relative;border-radius:24px;background:var(--surface);border:1px solid var(--line);overflow:hidden;
  box-shadow:0 18px 40px -30px rgb(0 0 0 / .45)}
.bc-capa{position:relative;height:86px;overflow:hidden;
  background:linear-gradient(128deg,var(--bc-marca) 0%,var(--bc-marca) 46%,color-mix(in srgb,var(--bc-marca) 58%,var(--bc-acento)) 100%)}
.bc-capa::before{content:"";position:absolute;inset:0;background:radial-gradient(120% 150% at 0% 0%,rgb(255 255 255 / .24),rgb(255 255 255 / 0) 56%)}
.bc-capa::after{content:"";position:absolute;right:-46px;top:-74px;width:210px;height:210px;border-radius:50%;
  border:26px solid rgb(255 255 255 / .09);box-shadow:0 0 0 30px rgb(255 255 255 / .05)}
.bc-corpo{padding:0 18px 18px}
.bc-id{position:relative;margin-top:-36px;display:flex}
.bc-logo{display:grid;place-items:center;min-width:72px;height:72px;padding:8px 14px;border-radius:18px;background:#FFFFFF;
  border:1px solid var(--line);box-shadow:0 10px 24px -14px rgb(0 0 0 / .45)}
.bc-logo img{height:40px;width:auto;max-width:150px;object-fit:contain;display:block}
.bc-mono{display:grid;place-items:center;width:72px;height:72px;border-radius:20px;background:var(--bc-marca);
  color:var(--bc-marca-on);font-weight:680;font-size:25px;letter-spacing:-.02em;box-shadow:0 0 0 4px var(--surface),
  0 10px 24px -14px rgb(0 0 0 / .45)}
.bc-nome{margin:12px 0 0;font-size:23px;line-height:1.15;font-weight:650;letter-spacing:-.02em;color:var(--ink-strong)}
.bc-cidade{margin:4px 0 0;display:flex;align-items:center;gap:6px;font-size:14px;color:var(--ink-muted)}
.bc-cidade svg{width:16px;height:16px;flex:none}
.bc-voz{margin:14px 0 0;font-size:15.5px;line-height:1.5;color:var(--ink);max-width:62ch}
.bc-voz b{display:block;font-size:16.5px;font-weight:650;color:var(--ink-strong);margin-bottom:2px}
.bc-fatos{list-style:none;margin:16px 0 0;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(138px,1fr));gap:10px}
.bc-fatos li{display:grid;gap:2px;align-content:start;padding:11px 13px;border-radius:14px;background:var(--surface-2);min-width:0}
.bc-fatos b{display:flex;align-items:center;gap:5px;font-size:19px;line-height:1.15;font-weight:650;color:var(--ink-strong);overflow-wrap:anywhere}
.bc-fatos b svg{width:16px;height:16px;flex:none;color:#C98A00}
.bc-fatos span{font-size:13px;line-height:1.3;color:var(--ink-muted)}
.bc-fatos a{display:inline-flex;align-items:center;min-height:44px;font-size:15px;font-weight:650;color:var(--ink-strong);
  overflow-wrap:anywhere;text-underline-offset:3px}
.bc-fonte{margin:10px 0 0;font-size:13px;color:var(--ink-muted)}
.bc .difs{list-style:none;margin:16px 0 0;padding:0;display:grid;gap:9px}
.bc .difs li{display:grid;grid-template-columns:20px 1fr;gap:10px;font-size:15px;line-height:1.4;color:var(--ink)}
.bc .difs svg{width:20px;height:20px;color:var(--bc-ok);margin-top:1px}
.bc-premios{list-style:none;margin:14px 0 0;padding:0;display:grid;gap:8px}
.bc-premios li{display:grid;grid-template-columns:22px 1fr;gap:8px;font-size:15px;font-weight:600;color:var(--ink-strong)}
.bc-premios svg{width:22px;height:22px;color:var(--bc-ouro-tinta)}
/* os selos: lado a lado; um só vira uma faixa (selo + legenda) */
.bc-selos{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.bc-selo{position:relative;isolation:isolate;display:grid;justify-items:center;align-content:start;gap:10px;text-align:center;
  padding:18px 10px 16px;border-radius:20px;background:var(--surface);border:1px solid var(--line);overflow:hidden}
.bc-selo::before{content:"";position:absolute;z-index:-1;left:50%;top:-30px;width:170px;height:170px;margin-left:-85px;
  border-radius:50%;background:radial-gradient(closest-side,color-mix(in srgb,var(--bc-marca) 16%,transparent),transparent)}
.bc-selo.bc-ouro::before{background:radial-gradient(closest-side,color-mix(in srgb,var(--bc-ouro) 24%,transparent),transparent)}
.bc-selo p{margin:0;display:grid;gap:2px}
.bc-selo b{font-size:15.5px;line-height:1.2;font-weight:650;color:var(--ink-strong)}
.bc-selo span{font-size:13px;line-height:1.3;color:var(--ink-muted)}
.bc-selos.um .bc-selo{grid-column:1/-1;grid-template-columns:auto 1fr;justify-items:start;align-items:center;text-align:left;
  padding:14px 18px;gap:16px}
.bc-selos.um .bc-selo::before{left:-22px;margin-left:0;top:50%;margin-top:-85px}
.bc .s5{width:92px;height:92px;flex:none;filter:drop-shadow(0 6px 10px rgb(0 0 0 / .18))}
.bc .s5-out{fill:var(--bc-selo)}
.bc .s5-in{fill:var(--bc-selo);stroke:var(--bc-selo-acento);stroke-width:3}
.bc .s5-line{stroke:var(--bc-selo-acento)}
.bc .s5-word{fill:var(--bc-selo-acento);font:700 12px var(--font);letter-spacing:2px}
.bc .s5-num{fill:var(--bc-selo-num);font:700 44px var(--font)}
.bc .s5-ok{stroke:var(--bc-selo-num)}
.bc .sp-out{fill:var(--bc-ouro)}
.bc .sp-in{fill:var(--bc-ouro-fundo);stroke:var(--bc-ouro-claro);stroke-width:2}
.bc .sp-leaf{fill:var(--bc-ouro-claro)}
.bc .sp-star,.bc .sp-fita{fill:var(--bc-ouro-claro)}
.bc .sp-ano{fill:#FFFFFF;font:700 17px var(--font);letter-spacing:.5px}
/* o título do nível e os itens */
.bc-titulo{margin:22px 0 0;font-size:22px;line-height:1.2;font-weight:650;letter-spacing:-.015em;color:var(--ink-strong);text-wrap:balance}
.bc-sub{margin:6px 0 0;font-size:15px;line-height:1.45;color:var(--ink-muted);max-width:60ch}
.bc-itens{list-style:none;margin:14px 0 0;padding:0;display:grid;gap:10px}
.bc-itens li{display:grid;grid-template-columns:28px 1fr;gap:10px;align-items:start;font-size:15px;line-height:1.42;color:var(--ink)}
.bc-itens b{font-weight:650;color:var(--ink-strong)}
.bc-ck{display:grid;place-items:center;width:28px;height:28px;border-radius:50%;background:var(--bc-ok-bg);color:var(--bc-ok)}
.bc-ck svg{width:17px;height:17px}
.bc-v{margin:12px 0 0;font-size:13px;color:var(--ink-muted)}
/* as fotos: carrossel de CSS (a próxima aparece na borda); grade no notebook */
.bc-galeria{margin-top:26px}
.bc-fotos-t{margin:0;font-size:19px;line-height:1.2;font-weight:650;color:var(--ink-strong);letter-spacing:-.01em}
.bc-dica{margin:4px 0 0;font-size:13px;color:var(--ink-muted)}
.bc-fotos{margin:12px calc(-1 * var(--bc-gutter)) 0;display:flex;gap:12px;overflow-x:auto;overscroll-behavior-x:contain;
  scroll-snap-type:x mandatory;scroll-padding-inline:var(--bc-gutter);padding:2px var(--bc-gutter) 8px;scrollbar-width:none}
.bc-fotos::-webkit-scrollbar{display:none}
.bc-fotos:focus-visible{outline-offset:-3px;border-radius:20px}
.bc-foto{flex:0 0 min(300px,calc(100% - 64px));margin:0;scroll-snap-align:start}
.bc-foto:last-child{scroll-snap-align:end}
.bc-fotos.n1 .bc-foto{flex-basis:100%}
.bc-foto img{display:block;width:100%;aspect-ratio:4/3;object-fit:cover;border-radius:18px;background:var(--surface-2);
  box-shadow:0 14px 28px -22px rgb(0 0 0 / .55)}
.bc-foto figcaption{margin:8px 2px 0;font-size:13.5px;line-height:1.35;color:var(--ink-muted)}
@media (min-width:760px){
  .bc-fotos{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));overflow:visible;margin:12px 0 0;padding:0;gap:16px}
  .bc-fotos.n1{grid-template-columns:minmax(0,560px)}
  .bc-fotos.n3{grid-template-columns:repeat(3,minmax(0,1fr))}
  .bc-dica{display:none}
}
@media (min-width:1024px){
  .bc-grade{grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:32px;align-items:start}
  .bc-grade.so{grid-template-columns:minmax(0,640px)}
  .bc-titulo{margin-top:24px}
  .bc-fotos.n4{grid-template-columns:repeat(4,minmax(0,1fr))}
}
@media (max-width:359px){.bc-selos{grid-template-columns:1fr}.bc .s5{width:80px;height:80px}}
@media print{
  .bc-capa,.bc-dica{display:none}
  .bc-id{margin-top:12px}
  .bc-card,.bc-selo{box-shadow:none;border:1px solid #888}
  .bc .s5{filter:none}
  .bc-fotos{display:grid!important;grid-template-columns:repeat(4,1fr);overflow:visible;margin:12px 0 0;padding:0}
  .bc-grade,.bc-galeria{break-inside:avoid-page}
}
"""
