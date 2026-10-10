# -*- coding: utf-8 -*-
"""SPEC-133-A.1 · F1 — o CARROSSEL e as PARCELAS da página do Quem Cobra Menos (Founder 10/10 · D-133A1-01).

O que o Founder pediu, só no CANAL (a carteira não muda):
    1. as opções LADO A LADO em carrossel — no celular arrasta para o lado com o próximo cartão aparecendo; no computador
       lado a lado; sem JavaScript (scroll-snap de CSS) e com o MESMO script/hash da CSP;
    2. o vencedor e a linha "Quem cobra menos?" do balão com a MENOR parcela da oferta (as vezes da seguradora);
    3. cada cartão NESTA ORDEM: (a) a menor parcela · (b) o à vista · (c) o maior parcelamento SEM juros.

O FIO (o mesmo da 133-A): o pedido do canário (104 ofertas REAIS saneadas) no banco DUBLÊ → `proposta.publicar_proposta`
(montar → template → Hub → compartilhar) → `ArtifactService.abrir_compartilhado` (o HTML SERVIDO) + a `mensagem` que a
publicação devolve. Borda dublê: só o banco (CLAUDE.md §9.4).

🔬 LENTE DO DADO: a menor parcela e o maior sem juros são recontados AQUI, à mão, sobre os `parcelamentos` CRUS das ofertas
da fixture — nunca pelas funções da proposta ou da mensagem.

📊 10/10/2026 (SELECT só leitura no pedido d0bb15ba, 104 ofertas): a Youse devolve 4 parcelamentos (1x..4x, uma forma de
pagamento, todos sem juros) — ali a menor parcela É 4x de R$ 932,64; o 12x não existe e a página não o inventa. As
outras trazem até 10x/11x/12x (Aliro, Hdi, Zurich, Mapfre, Liberty: 12x sem juros; Tokio: 12x COM juros e 7x–10x sem).

⛔ Nomes fictícios (CLAUDE.md §13.9). Rodar:
    cd backend && .venv/Scripts/python.exe -m pytest tests/test_spec133a1_carrossel_e_parcelas.py -q -p no:cacheprovider
"""
from __future__ import annotations

import copy
import hashlib
import html as _html
import os
import re
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from app.services.artifacts import proposta_canal_html as PC  # noqa: E402
from app.services.artifacts import proposta_html as PH  # noqa: E402
from app.services.artifacts.templates import POR_CHAVE  # noqa: E402
from app.services.multicalculo import mensagem as MSG  # noqa: E402
from app.services.multicalculo import proposta as P  # noqa: E402
from dubles import mundo_da_proposta as M  # noqa: E402
from test_spec133a_a_pagina_canal import (BASE, CONTRATO, SHA_DA_CARTEIRA_HTML, _csp, _modelo_gravado,  # noqa: E402
                                          _publicar, _servir)

CAPTURAS = Path(os.environ.get("F1_133A1_CAPTURAS") or (Path(os.environ.get("TEMP", "/tmp")) / "f1-133a1"))


# =====================================================================================================================
# a LENTE — à mão, sobre os parcelamentos CRUS da fixture
# =====================================================================================================================
def _brl(v: float) -> str:
    inteiro, _, cent = f"{float(v):,.2f}".partition(".")
    return f"R$ {inteiro.replace(',', '.')},{cent}"


def _linhas(parcelamentos):
    for p in parcelamentos or ():
        n = int(p["parcelas"])
        demais = float(p.get("demais_parcelas") or p["primeira_parcela"])
        primeira = float(p.get("primeira_parcela") or demais)
        yield n, round(demais, 2), round(primeira + demais * (n - 1), 2)


def _sem_juros(total: float, premio: float) -> bool:
    """A régua, escrita de novo AQUI: o total não passa do prêmio além do arredondamento (📊 10/10: centavos ficam em
    [−0,049 %, +0,024 %]; juros começam em +0,99 %). Mais barato que o prêmio também é sem juros."""
    return total - premio <= max(1.0, premio * 0.0025)


def lente_da_oferta(bruta: dict) -> dict:
    """{"menor": (vezes, "R$ …", sem_juros), "sem_juros": (vezes, "R$ …") | None} — contagem independente."""
    premio = float(bruta["premio_total"])
    todas = [(n, v, _sem_juros(t, premio)) for n, v, t in _linhas(bruta.get("parcelamentos")) if n >= 2 and v > 0]
    menor = min(todas, key=lambda x: (x[1], -x[0], not x[2])) if todas else None
    sj = [x for x in todas if x[2]]
    maior_sj = max(sj, key=lambda x: (x[0], -x[1])) if sj else None
    return {"menor": (menor[0], _brl(menor[1]), menor[2]) if menor else None,
            "sem_juros": (maior_sj[0], _brl(maior_sj[1])) if maior_sj else None}


def oferta_crua(dados: dict, opcao: dict) -> dict:
    """A oferta da fixture que virou a opção, pelo PRÊMIO (o nome da seguradora a comparação normaliza: "Tokio" vira
    "Tokio Marine"). Mais de uma com o mesmo prêmio → todas com o MESMO parcelamento, senão o teste não decide."""
    achadas = [o for o in dados["ofertas"] if abs(float(o["premio_total"]) - float(opcao["premio_anual"])) < 0.005]
    assert achadas, f"a opção {opcao['id']} não veio de oferta nenhuma da fixture"
    assert len({str(lente_da_oferta(o)) for o in achadas}) == 1
    return achadas[0]


# =====================================================================================================================
# o que se LÊ
# =====================================================================================================================
def _vis(fragmento: str) -> str:
    t = re.sub(r"<(script|style)\b.*?</\1>", " ", fragmento, flags=re.S)
    t = _html.unescape(re.sub(r"<[^>]+>", " ", t)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", t).strip()


def _cartoes(doc: str) -> dict:
    return {m.group(1): m.group(2) for m in re.finditer(r'<article class="op[^"]*" data-opcao="([^"]+)"[^>]*>(.*?)</article>',
                                                        doc, re.S)}


def _p(cartao: str, cls: str) -> str:
    m = re.search(rf'<p class="[^"]*\b{cls}\b[^"]*">(.*?)</p>', cartao, re.S)
    return _vis(m.group(1)) if m else ""


def _linha_quem_cobra(baloes) -> str:
    return next((l for b in baloes for l in b.splitlines() if l.startswith("*Quem cobra menos?*")), "")


# =====================================================================================================================
# os GUARDAS (uma função: a mutação prova que cada um fica vermelho)
# =====================================================================================================================
def defeitos(doc: str, modelo: dict, dados: dict, baloes=None) -> list:
    d = []
    css = re.search(r"<style[^>]*>(.*?)</style>", doc, re.S)
    css = css.group(1) if css else ""
    regra = re.search(r"\.ops\{([^}]*)\}", css)
    if not regra or "display:flex" not in regra.group(1) or "overflow-x:auto" not in regra.group(1) \
            or "scroll-snap-type:x mandatory" not in regra.group(1):
        d.append("o contêiner .ops não é um carrossel (flex + overflow-x + scroll-snap)")
    if not re.search(r"\.ops>\.op\{[^}]*scroll-snap-align:start", css):
        d.append("os cartões não encaixam (scroll-snap-align)")
    if not re.search(r'<div class="ops[^"]*"[^>]*>\s*<article class="op', doc):
        d.append("os cartões não estão dentro do .ops")
    cartoes = _cartoes(doc)
    if list(cartoes) != [o["id"] for o in modelo["opcoes"]]:
        d.append(f"cartões ≠ opções: {list(cartoes)}")
    for o in modelo["opcoes"]:
        c = cartoes.get(o["id"], "")
        lente = lente_da_oferta(oferta_crua(dados, o))
        pos = {k: c.find(f"op-{k}") for k in ("menor", "vista", "sj")}
        if lente["menor"]:
            vezes, valor, sj = lente["menor"]
            topo = _p(c, "op-menor")
            esperado = f"{vezes}x de {valor} {'sem juros' if sj else 'com juros'}"
            if topo != esperado:
                d.append(f"{o['id']}: menor parcela {topo!r} ≠ lente {esperado!r}")
            if not (0 <= pos["menor"] < pos["vista"]):
                d.append(f"{o['id']}: a menor parcela não vem antes do à vista")
        if _p(c, "op-vista") != f"{_brl(o['premio_anual'])} à vista":
            d.append(f"{o['id']}: à vista {_p(c, 'op-vista')!r}")
        msj = lente["sem_juros"]
        repetida = msj and lente["menor"] and (msj[0], msj[1]) == lente["menor"][:2]
        if msj and not repetida:
            if _p(c, "op-sj") != f"ou {msj[0]}x sem juros de {msj[1]}":
                d.append(f"{o['id']}: sem juros {_p(c, 'op-sj')!r} ≠ lente {msj}")
            if not (pos["vista"] < pos["sj"]):
                d.append(f"{o['id']}: o sem juros não vem depois do à vista")
        elif pos["sj"] >= 0:
            d.append(f"{o['id']}: linha de sem juros sem dado (ou repetindo a do topo)")
    # o vencedor (o cartão escuro) e o balão com a MESMA menor parcela
    rec_lente = lente_da_oferta(oferta_crua(dados, modelo["opcoes"][0]))["menor"]
    win = re.search(r'<section class="win".*?</section>', doc, re.S)
    if rec_lente and f"{rec_lente[0]}x de {rec_lente[1]}" not in _vis(win.group(0) if win else ""):
        d.append("o vencedor sem a menor parcela da lente")
    if baloes is not None and rec_lente and not _linha_quem_cobra(baloes).endswith(f"{rec_lente[0]}x de *{rec_lente[1]}*"):
        d.append(f"balão: {_linha_quem_cobra(baloes)!r}")
    return d


# =====================================================================================================================
# o fio
# =====================================================================================================================
@pytest.fixture(scope="module")
def servido():
    mp = pytest.MonkeyPatch()
    try:
        mp.setenv("PUBLIC_APP_URL", BASE)
        m = M.montar_mundo(mp, solicitante="canal")
        r = _publicar(m)
        s = _servir(m, r["token"])
        yield m, r, s, _modelo_gravado(m, r["artifact_id"])
    finally:
        mp.undo()


def test_o_fio_carrossel_e_parcelas_da_lente_na_pagina_servida_e_no_balao(servido):
    m, r, s, modelo = servido
    doc = s["html"]
    assert modelo["origem"] == "canal" and len(modelo["opcoes"]) >= 2
    assert all("parcela_menor" in o for o in modelo["opcoes"])            # a proposta carrega a menor por opção
    assert defeitos(doc, modelo, m.dados, r["mensagem"]) == []
    # o mesmo script (o hash da CSP não muda) e nenhum #track da carteira
    assert s["csp_script_hashes"] == [PH.HASH_DO_SCRIPT] and 'id="track"' not in doc


def test_o_12_nunca_e_constante_youse_so_traz_4x():
    """📊 a forma MEDIDA da Youse (10/10): 1x..4x, uma forma de pagamento, sem juros → o topo é 4x e a linha (c) some."""
    m = copy.deepcopy(CONTRATO)
    m.update(origem="canal", canal={"nome": "Comparador Ficticio"})
    youse = {"premio_total": 3730.56, "parcelamentos": [
        {"parcelas": n, "primeira_parcela": round(3730.56 / n, 2), "demais_parcelas": round(3730.56 / n, 2),
         "tipo_pagamento": 1} for n in (1, 2, 3, 4)]}
    o = m["opcoes"][0]
    o.update(premio_anual=3730.56, parcelas={"vezes": 4, "valor": 932.64, "total": 3730.56},
             parcelas_sem_juros={"vezes": 4, "valor": 932.64}, parcela_menor=P._parcela_menor(youse))
    assert o["parcela_menor"] == {"vezes": 4, "valor": 932.64, "total": 3730.56, "sem_juros": True}
    c = _cartoes(PC.render_proposta_do_canal(m))[o["id"]]
    assert _p(c, "op-menor") == "4x de R$ 932,64 sem juros" and _p(c, "op-vista") == "R$ 3.730,56 à vista"
    assert "op-sj" not in c and "12x" not in _vis(c)
    assert _linha_quem_cobra(MSG.mensagem_do_canal(m, "https://x.test/r/abc")).endswith("4x de *R$ 932,64*")


def _tokio(formas):
    """Os parcelamentos REAIS da Tokio de R$ 3.480,38 na fixture do canário, só das formas de pagamento pedidas."""
    tabela = {1: [(2, 1740.11), (5, 695.96), (7, 497.10), (12, 289.90)],          # 12x: total R$ 1,58 MENOR que o prêmio
              2: [(2, 1740.11), (5, 695.96), (6, 602.02), (12, 356.32)]}          # 6x e 12x: com juros (+R$ 131 / +R$ 795)
    return {"premio_total": 3480.38, "parcelamentos": [
        {"parcelas": n, "primeira_parcela": v, "demais_parcelas": v, "tipo_pagamento": f}
        for f in formas for n, v in tabela[f]]}


def _cartao_com(bruta, indice=1):
    m = copy.deepcopy(CONTRATO)
    m.update(origem="canal", canal={"nome": "Comparador Ficticio"})
    o = m["opcoes"][indice]
    for k in ("parcela_menor", "parcela_sem_juros_maior", "parcelas_sem_juros"):
        o.pop(k, None)
    o.update(premio_anual=bruta["premio_total"], parcela_menor=P._parcela_menor(bruta))
    if P._parcela_sem_juros_maior(bruta):
        o["parcela_sem_juros_maior"] = P._parcela_sem_juros_maior(bruta)
    return m, o, _cartoes(PC.render_proposta_do_canal(m))[o["id"]]


def test_doze_com_juros_no_topo_e_o_maior_sem_juros_embaixo():
    """Só a forma 2 da Tokio: a menor parcela é 12x COM juros; o maior sem juros é 5x — as três linhas, nesta ordem."""
    m, o, c = _cartao_com(_tokio([2]))
    assert o["parcela_menor"] == {"vezes": 12, "valor": 356.32, "total": 4275.84, "sem_juros": False}
    assert _p(c, "op-menor") == "12x de R$ 356,32 com juros"
    assert _p(c, "op-vista") == "R$ 3.480,38 à vista"
    assert _p(c, "op-sj") == "ou 5x sem juros de R$ 695,96"
    assert c.find("op-menor") < c.find("op-vista") < c.find("op-sj")


def test_o_centavo_de_arredondamento_nao_vira_juros():
    """As duas formas da Tokio: o 12x da forma 1 custa R$ 1,58 a MENOS que o prêmio — é sem juros, e é a menor parcela.
    A carteira (`_parcelas_sem_juros`, |dif| < R$ 1, intocada — D-133A1-01) o chamaria de com juros."""
    bruta = _tokio([1, 2])
    m, o, c = _cartao_com(bruta)
    assert _p(c, "op-menor") == "12x de R$ 289,90 sem juros" and "op-sj" not in c
    assert P._parcelas_sem_juros(bruta) == {"vezes": 7, "valor": 497.1}          # a régua da carteira, de antes


def test_a_carteira_nao_ganha_a_chave_nem_muda_um_byte(monkeypatch):
    tpl = POR_CHAVE["proposal.quote"]
    doc = tpl.renderizador(copy.deepcopy(CONTRATO))
    assert hashlib.sha256(doc.encode()).hexdigest()[:16] == SHA_DA_CARTEIRA_HTML
    monkeypatch.setenv("PUBLIC_APP_URL", BASE)
    m = M.montar_mundo(monkeypatch, solicitante="beta")            # a corretora pedindo a própria (a carteira)
    import asyncio
    modelo = asyncio.run(P.montar_proposta(company_id=m.dono, pedido_id=m.pedido_id, situacao="novo_sem_apolice",
                                           db=m.db))
    assert modelo["origem"] == "corretora" and not any("parcela_menor" in o for o in modelo["opcoes"])


# =====================================================================================================================
# MUTAÇÕES — cada guarda fica VERMELHO (CLAUDE.md §9.3/§9.5)
# =====================================================================================================================
def test_MUTACOES_os_guardas_ficam_vermelhos(servido):
    m, r, s, modelo = servido
    doc = s["html"]
    assert defeitos(doc, modelo, m.dados, r["mensagem"]) == []                     # CONTROLE
    rec = modelo["opcoes"][0]
    menor = lente_da_oferta(oferta_crua(m.dados, rec))["menor"]
    outra_vez = "13x de" if menor[0] != 13 else "14x de"
    c0 = _cartoes(doc)[rec["id"]]
    vista = re.search(r'<p class="op-a op-vista">.*?</p>', c0, re.S).group(0)
    topo = re.search(r'<p class="op-p op-menor">.*?</p>', c0, re.S).group(0)
    mutacoes = {
        "a pilha de antes (sem carrossel)": doc.replace("display:flex;gap:12px;overflow-x:auto", "display:grid;gap:12px", 1),
        "sem encaixe": doc.replace("scroll-snap-align:start;scroll-snap-stop", "scroll-snap-stop", 1),
        "o à vista no topo (a ordem de antes)": doc.replace(c0, c0.replace(topo, "").replace(vista, vista + topo), 1),
        "as vezes como constante": doc.replace(f'<span class="x">{menor[0]}x de</span>', f'<span class="x">{outra_vez}</span>', 1),
        "a menor parcela trocada pelo maior parcelamento": doc.replace(
            topo, re.sub(r"<b>.*?</b>", "<b>R$ 9.999,99</b>", topo), 1),
        "o juros sem nome": doc.replace(topo, re.sub(r'<span class="j">.*?</span>', "", topo), 1),
        "a linha sem juros sumiu": re.sub(r'<p class="op-a op-sj">.*?</p>', "", doc, count=1, flags=re.S)
        if "op-sj" in doc else doc.replace(vista, vista + '<p class="op-a op-sj">ou 2x sem juros de R$ 1,00</p>', 1),
    }
    for nome, mutado in mutacoes.items():
        assert mutado != doc, nome
        assert defeitos(mutado, modelo, m.dados, r["mensagem"]) != [], f"o guarda de '{nome}' não ficou vermelho"
    # o balão com o parcelamento de ANTES (o maior sem juros, quando ele é outro)
    baloes = [b.replace(f"{menor[0]}x de *{menor[1]}*", f"{outra_vez} *{menor[1]}*") for b in r["mensagem"]]
    assert defeitos(doc, modelo, m.dados, baloes) != []


def test_MUTACAO_sem_os_campos_do_canal_o_topo_perde_o_nome_do_juros_e_o_maior_sem_juros_erra():
    """O modelo de ANTES (só `parcelas`/`parcelas_sem_juros`, sem `parcela_menor`/`parcela_sem_juros_maior`): o guarda
    das duas formas da Tokio fica vermelho — prova que os campos novos são o que faz o cartão certo."""
    bruta = _tokio([1, 2])
    m = copy.deepcopy(CONTRATO)
    m.update(origem="canal", canal={"nome": "Comparador Ficticio"})
    o = m["opcoes"][1]
    for k in ("parcela_menor", "parcela_sem_juros_maior"):
        o.pop(k, None)
    o.update(premio_anual=3480.38, parcelas={"vezes": 12, "valor": 289.90}, parcelas_sem_juros=P._parcelas_sem_juros(bruta))
    c = _cartoes(PC.render_proposta_do_canal(m))[o["id"]]
    assert _p(c, "op-menor") != "12x de R$ 289,90 sem juros" or "op-sj" in c


# =====================================================================================================================
# o navegador de verdade — 390 px (arrasta, o 2º aparece) e 1280 px (lado a lado)
# =====================================================================================================================
@pytest.fixture(scope="module")
def navegador():
    sync = pytest.importorskip("playwright.sync_api")
    try:
        pw = sync.sync_playwright().start()
        br = pw.chromium.launch()
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"Chromium do Playwright indisponível: {e}")
    yield br
    br.close()
    pw.stop()


_GEOMETRIA = """() => {
  const ops = document.querySelector('.ops'), cs = getComputedStyle(ops);
  const cards = [...ops.querySelectorAll(':scope > .op')].map(c => c.getBoundingClientRect());
  return {display: cs.display, snap: cs.scrollSnapType, overflowX: cs.overflowX, scrollW: ops.scrollWidth,
          clientW: ops.clientWidth, cards: cards.map(r => ({l: r.left, r: r.right, t: r.top, w: r.width})),
          docW: document.documentElement.scrollWidth, bodyW: document.body.scrollWidth, vw: innerWidth};
}"""


@pytest.mark.parametrize("largura,js", [(390, True), (390, False), (1280, True)])
def test_navegador_o_carrossel_no_celular_e_lado_a_lado_no_computador(servido, navegador, largura, js):
    doc = re.sub(r'<meta property="og:image".*?twitter:image" content="[^"]*">', "", servido[2]["html"], flags=re.S)
    ctx = navegador.new_context(viewport={"width": largura, "height": 844 if largura < 600 else 900},
                                java_script_enabled=js, color_scheme="light")
    pg = ctx.new_page()
    erros = []
    pg.on("console", lambda msg: erros.append(msg.text) if msg.type in ("error", "warning") else None)
    pg.on("pageerror", lambda e: erros.append(str(e)))
    try:
        pg.set_content(doc.replace("<head>", f'<head>\n<meta http-equiv="Content-Security-Policy" content="{_csp()}">', 1),
                       wait_until="load")
        pg.wait_for_timeout(700)
        assert erros == []
        g = pg.evaluate(_GEOMETRIA)
        c = g["cards"]
        assert len(c) >= 2
        assert g["docW"] <= largura and g["bodyW"] <= largura                    # a página não rola de lado
        assert all(b["l"] >= a["r"] - 0.5 for a, b in zip(c, c[1:]))             # lado a lado, nunca empilhados
        assert len({round(x["t"]) for x in c}) == 1                              # na mesma linha
        if largura < 880:
            assert g["display"] == "flex" and g["overflowX"] == "auto" and g["snap"].startswith("x")
            assert g["scrollW"] > g["clientW"]                                   # dá para arrastar
            assert c[1]["l"] < largura - 24                                      # o 2º cartão APARECE na borda
            assert c[0]["w"] >= 280                                              # e o 1º não fica espremido
        else:
            assert g["display"] == "grid" and g["scrollW"] <= g["clientW"] + 1   # todos à vista, sem arrastar
            assert c[-1]["r"] <= largura
        CAPTURAS.mkdir(parents=True, exist_ok=True)
        secao = pg.locator('section[aria-labelledby="h-ops"]')
        secao.screenshot(path=str(CAPTURAS / f"carrossel-{largura}{'' if js else '-sem-js'}.png"))
        if largura < 880 and js:                                                 # arrastado até o 2º
            pg.evaluate("document.querySelector('.ops').scrollBy({left: 400})")
            pg.wait_for_timeout(500)
            g2 = pg.evaluate(_GEOMETRIA)
            assert abs(g2["cards"][1]["l"] - 16) < 2 or g2["cards"][-1]["r"] <= largura   # encaixou na margem
            secao.screenshot(path=str(CAPTURAS / f"carrossel-{largura}-arrastado.png"))
    finally:
        ctx.close()
