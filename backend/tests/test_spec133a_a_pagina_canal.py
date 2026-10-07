# -*- coding: utf-8 -*-
"""SPEC-133-A · F3 · G6 — A PÁGINA DO CANAL (D-133A-09 · D-133A-13 · D-130A1-04/08/15).

O FIO (pelo caminho REAL do Artifact Hub, como os testes da 130-A):
    o pedido do canário gravado no banco DUBLÊ → `proposta.publicar_proposta` (montar → criar → renderizar pelo GANCHO do
    template → publicar → compartilhar) → `ArtifactService.abrir_compartilhado(token)` (o que o `route.ts` serve) →
    afirmações sobre o HTML SERVIDO e sobre `fechar_compartilhado` (o `?fechar=` medido).
    Borda dublê: só o banco. Proposta, comparação, template, renderizador e Hub são os REAIS (CLAUDE.md §9.4).

🔬 LENTE DO DADO: o volume e as seguradoras são recontados da FIXTURE pelas lentes independentes da 130-A.1; a menor
parcela é recalculada aqui, à mão, das parcelas do modelo gravado.

⚠️ `canal.whatsapp` (o número da CONVERSA do canal, para o "Quero fechar" voltar a ela — D-133A-13) ainda não é escrito
por `proposta.py` (pendência da F3 ao gerente). Aqui ele entra por um embrulho de `montar_proposta` que SÓ preenche a
chave quando ela falta — quando a proposta passar a escrevê-la, o embrulho não muda nada e o teste mede a real.

⛔ Nomes fictícios (CLAUDE.md §13.9). Rodar:
    cd backend && .venv/Scripts/python.exe -m pytest tests/test_spec133a_a_pagina_canal.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import base64
import copy
import hashlib
import json
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
from app.services.artifacts import proposta_apresentacao as AP  # noqa: E402
from app.services.artifacts.proposta_previa import render_previa_png  # noqa: E402
from app.services.artifacts.service import ArtifactService  # noqa: E402
from app.services.artifacts.templates import POR_CHAVE  # noqa: E402
from app.services.multicalculo import config as CFG  # noqa: E402
from app.services.multicalculo import proposta as P  # noqa: E402
from dubles import mundo_da_proposta as M  # noqa: E402
from test_spec130a1_a_mensagem_do_canal import (RE_NUMERO_DE_CORRETORAS, lente_cotacoes,  # noqa: E402
                                                lente_seguradoras_consultadas, lente_tentativas_sem_preco)
from test_spec130a_o_fio import CHROME, texto_visivel  # noqa: E402

BASE = "https://app.exemplo.test"
WHATS_DO_CANAL = M.WHATS_DO_CANAL          # fictício: o número da conversa do canal (a integração do canal no mundo)
CONTRATO = json.loads((BACKEND / "tests" / "fixtures" / "proposta" / "modelo_contrato.json").read_text(encoding="utf-8"))
#: 📊 07/10/2026 — sha256 do HTML e do PNG da CARTEIRA (o contrato da 130-A) gerados ANTES do diff da F3 (HEAD 098b26c,
#: `scratchpad/f3-133a/antes`) e iguais depois. A carteira muda só por decisão: quem a mudar de propósito atualiza aqui.
SHA_DA_CARTEIRA_HTML = "56d8c9e5469dc837"
SHA_DA_CARTEIRA_PNG = "1c371a324f69df77"
#: o `montar_proposta` REAL (a fixture de módulo o embrulha enquanto vive; o caso "sem número" volta a este)
_MONTAR_REAL = P.montar_proposta


# =====================================================================================================================
# o caminho real
# =====================================================================================================================
def _com_numero_do_canal(monkeypatch, numero=WHATS_DO_CANAL):
    """Costura 133-A: o número vem do REAL — `proposta.whatsapp_do_canal` lê a integração ativa do canal, semeada pelo
    mundo (`montar_mundo(canal_pareado=True)`). O antigo embrulho escrevia `canal.whatsapp` DEPOIS do `cta` — e
    escondia que o texto do botão (com a "Ref.") não existia sem o WhatsApp da corretora."""
    assert numero == WHATS_DO_CANAL


def _publicar(m):
    return asyncio.run(P.publicar_proposta(company_id=m.dono, pedido_id=m.pedido_id, situacao="novo_sem_apolice",
                                           primeiro_nome="Mariana", db=m.db, base_url=BASE))


def _servir(m, token):
    s = ArtifactService(m.banco.visao("rota-publica")).abrir_compartilhado(token, user_agent=CHROME)
    assert s, "o link não abriu"
    return s


def _modelo_gravado(m, artifact_id):
    v = [x for x in m.banco.linhas("artifact_versions") if x["artifact_id"] == artifact_id]
    return sorted(v, key=lambda x: x["version"])[-1]["payload"]


def _config_de(m, company_id):
    linha = next((c for c in m.banco.linhas("multicalculo_config") if c["company_id"] == company_id), None)
    if linha is None:
        m.banco.semear("multicalculo_config", {"company_id": company_id, "config": {}})
        linha = next(c for c in m.banco.linhas("multicalculo_config") if c["company_id"] == company_id)
    return linha["config"]


def _scripts(doc):
    return re.findall(r"<script([^>]*)>(.*?)</script>", doc, flags=re.S)


def _hash(texto):
    return "sha256-" + base64.b64encode(hashlib.sha256(texto.encode("utf-8")).digest()).decode()


def _bloco(doc, cls):
    """O texto de um bloco: `<p>`/`<section>` até o fecho dele; o `host` (tem divs dentro) até o fim da seção."""
    if cls == "host":
        m = re.search(r'<div class="host">(.*?)</section>', doc, re.S)
        return _vis(m.group(1)) if m else ""
    m = re.search(rf'<(p|section)\b[^>]*class="{cls}"[^>]*>(.*?)</\1>', doc, re.S)
    return _vis(m.group(2)) if m else ""


def _vis(fragmento):
    """O que se LÊ num bloco: cada tag vira um espaço (os `<span>` do desenho não grudam palavras)."""
    import html as _h
    t = re.sub(r"<(script|style)\b.*?</\1>", " ", fragmento, flags=re.S)
    t = _h.unescape(re.sub(r"<[^>]+>", " ", t)).replace("\xa0", " ")
    return re.sub(r"\s+([.,:!?])", r"\1", re.sub(r"\s+", " ", t)).strip()


def _br_int(v):
    return "R$ " + f"{int(float(v) + 0.5):,}".replace(",", ".")


def _menor_parcela(o):
    """A LENTE: a menor parcela (vezes > 1) entre `parcelas` e `parcelas_sem_juros`, à mão."""
    c = [(float(p["valor"]), int(p["vezes"])) for p in (o.get("parcelas"), o.get("parcelas_sem_juros"))
         if isinstance(p, dict) and int(p.get("vezes") or 0) > 1 and float(p.get("valor") or 0) > 0]
    valor, vezes = min(c, key=lambda x: (x[0], -x[1]))
    inteiro, _, cent = f"{valor:,.2f}".partition(".")
    return f"{vezes}x de", f"R$ {inteiro.replace(',', '.')},{cent}"


# =====================================================================================================================
# os GUARDAS (uma função, para a mutação provar que cada um consegue ficar vermelho)
# =====================================================================================================================
PERDEDORA = (M.NOME_BETA, M.MARCA_BETA, "Vega", "99999-0002", "999990002", "999990003", "Outra corretora parceira")


def defeitos_da_pagina(doc: str, modelo: dict, *, dados=None) -> list:
    d = []
    vis = texto_visivel(doc)
    nome = (modelo.get("canal") or {}).get("nome") or CFG.PADRAO_DO_PRODUTO["canal"]["nome"]
    if not re.search(r'<span class="qcm"><svg class="q"[^>]*>.*?class="q-ring".*?class="q-tail".*?</svg><b>'
                     + re.escape(PH._e(nome)) + "</b>", doc, re.S):
        d.append("a marca do canal (símbolo + nome da config) não está no topo")
    if RE_NUMERO_DE_CORRETORAS.findall(vis):
        d.append(f"número de corretoras: {RE_NUMERO_DE_CORRETORAS.findall(vis)}")
    d += [f"perdedora: {x}" for x in PERDEDORA if x in doc]
    r = modelo["resumo"]
    vol = _bloco(doc, "vol")
    total = r["volume_do_canal"]["total"]
    if not vol.startswith(f"Fiz {total} cotações") or f"e {r['seguradoras_consultadas']} seguradoras" not in vol:
        d.append(f"volume: {vol!r}")
    if dados is not None:       # 🔬 a lente: o número publicado = base da config + o recontado da fixture
        cor = [c for c in dados["corretoras"].values()]
        esperado = (CFG.PADRAO_DO_PRODUTO["canal"]["volume"]["base"] + lente_cotacoes(dados, cor)
                    + lente_tentativas_sem_preco(dados, cor))
        if f"Fiz {esperado} cotações" not in vol or f"{lente_seguradoras_consultadas(dados, cor)} seguradoras" not in vol:
            d.append(f"volume ≠ lente ({esperado}): {vol!r}")
    eco = _bloco(doc, "eco")
    if r.get("economia") and f"Você deve economizar até {_br_int(r['economia']['ate'])} por ano" not in eco:
        d.append(f"economia: {eco!r}")
    win = _bloco(doc, "win")
    vezes, valor = _menor_parcela(modelo["opcoes"][0])
    if f"{vezes} {valor}" not in win or AP.brl(modelo["opcoes"][0]["premio_anual"]).replace(AP.NB, " ") not in win:
        d.append(f"vencedor/parcela: {win!r}")
    anf = modelo["anfitria"]["nome"]
    if f"Quem cobra menos Corretora {anf} com {modelo['opcoes'][0]['seguradora']}" not in win:
        d.append(f"quem cobra menos: {win!r}")
    execs = [c for a, c in _scripts(doc) if "application/json" not in a]
    if execs != [PH.SCRIPT_DA_PROPOSTA]:
        d.append(f"scripts executáveis: {len(execs)}")
    if re.search(r"\son[a-z]+\s*=", re.sub(r"<script\b.*?</script>", "", doc, flags=re.S), re.I):
        d.append("handler inline (a CSP o bloquearia)")
    tem_selo = bool((modelo.get("anfitria") or {}).get("selo"))
    if tem_selo != ('class="n5"' in doc) or tem_selo != ("Só cotamos com Corretoras Nível 5" in vis):
        d.append(f"bloco Nível 5 ≠ selo ({tem_selo})")
    return d


# =====================================================================================================================
# G6 · o fio — a página servida do canal
# =====================================================================================================================
@pytest.fixture(scope="module")
def servido():
    mp = pytest.MonkeyPatch()
    try:
        mp.setenv("PUBLIC_APP_URL", BASE)
        m = M.montar_mundo(mp, solicitante="canal")
        _com_numero_do_canal(mp)
        r = _publicar(m)
        s = _servir(m, r["token"])
        yield m, r, s, _modelo_gravado(m, r["artifact_id"])
    finally:
        mp.undo()


def test_o_fio_a_pagina_servida_do_canal_tem_a_marca_e_os_numeros_do_modelo(servido):
    m, r, s, modelo = servido
    assert modelo["origem"] == "canal" and modelo["canal"]["whatsapp"] == WHATS_DO_CANAL
    doc = s["html"]
    assert s["kind"] == "proposal" and s["csp_script_hashes"] == [PH.HASH_DO_SCRIPT]
    assert defeitos_da_pagina(doc, modelo, dados=m.dados) == []
    # o render guardado É o do renderizador do canal (o gancho escolheu pela origem) e a carteira não aparece nele
    assert doc.replace(re.search(r"<meta property=\"og:image\".*?twitter:image\" content=\"[^\"]*\">", doc, re.S).group(0),
                       PH.MARCADOR_DA_PREVIA) == PC.render_proposta_do_canal(modelo)
    assert 'class="track"' not in doc and "Comparação independente · Quem Cobra Menos" in texto_visivel(doc)
    # as opções na ordem do modelo, cada uma com o "Quero esta" que volta ao canal
    ids = re.findall(r'data-opcao="([^"]+)"', doc)
    assert ids == [o["id"] for o in modelo["opcoes"]] and len(ids) == 3
    # a anfitriã DENTRO: nome, selo, SUSEP, Google, anos, site — e o número DELA não é o destino de nada
    host = _bloco(doc, "host")
    for x in (M.MARCA_ALFA, "Corretora Nível 5", "202031234", "4,9", "37 avaliações", "17 anos", "orion-ficticia.test"):
        assert x in host, x
    assert M.WHATS_ALFA not in doc


def test_o_quero_fechar_volta_a_conversa_do_canal_pelo_redirecionamento_medido(servido):
    m, r, s, modelo = servido
    doc = s["html"]
    sem_script = re.sub(r"<script\b.*?</script>", "", doc, flags=re.S)
    assert f'href="?fechar={modelo["opcoes"][0]["id"]}"' in sem_script            # sem JS: link comum, mesma URL
    svc = ArtifactService(m.banco.visao("rota-publica"))
    for o in modelo["opcoes"]:
        destino = svc.fechar_compartilhado(r["token"], o["id"])
        assert destino.startswith(f"https://wa.me/{WHATS_DO_CANAL}?text="), destino
        assert M.WHATS_ALFA not in destino
    assert "Ref." in svc.fechar_compartilhado(r["token"], "recomendada").replace("%20", " ")   # leva a referência
    assert svc.fechar_compartilhado(r["token"], "https://evil.example") is None
    cliques = [e for e in m.banco.linhas("artifact_events") if e["event_type"] == "share.clicked"]
    assert len(cliques) >= 3                                                       # medido, como na carteira


def test_sem_o_numero_do_canal_o_botao_some_e_nada_redireciona(monkeypatch):
    monkeypatch.setenv("PUBLIC_APP_URL", BASE)
    monkeypatch.setattr(P, "montar_proposta", _MONTAR_REAL)
    m = M.montar_mundo(monkeypatch, solicitante="canal", canal_pareado=False)
    with pytest.raises(P.SemCanalDeFechamento):            # sem o número do canal, publicar recusa (nada gravado)
        _publicar(m)
    r = asyncio.run(P.publicar_proposta(company_id=m.dono, pedido_id=m.pedido_id, situacao="novo_sem_apolice",
                                        primeiro_nome="Mariana", db=m.db, base_url=BASE, permitir_sem_whatsapp=True))
    doc = _servir(m, r["token"])["html"]
    modelo = _modelo_gravado(m, r["artifact_id"])
    assert "whatsapp" not in (modelo.get("canal") or {}), "sem número a chave NÃO existe"
    sem_script = re.sub(r"<script\b.*?</script>", "", doc, flags=re.S)
    assert "?fechar=" not in sem_script and "wa.me" not in doc and "Quero fechar" not in texto_visivel(doc)
    assert ArtifactService(m.banco.visao("rota-publica")).fechar_compartilhado(r["token"], "recomendada") is None
    assert defeitos_da_pagina(doc, modelo) == []                                   # o resto da página continua certo


def test_o_bloco_nivel_5_some_com_o_selo_desligado(monkeypatch):
    monkeypatch.setenv("PUBLIC_APP_URL", BASE)
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    _config_de(m, m.alfa)["canal"] = {"selo": {"ligado": False}}
    _com_numero_do_canal(monkeypatch)
    r = _publicar(m)
    doc = _servir(m, r["token"])["html"]
    modelo = _modelo_gravado(m, r["artifact_id"])
    assert "selo" not in modelo["anfitria"]
    assert 'class="n5"' not in doc and "Nível 5" not in texto_visivel(doc)
    assert defeitos_da_pagina(doc, modelo) == []


def test_a_lista_do_nivel_5_e_a_do_programa_e_o_modelo_pode_trocar():
    m = copy.deepcopy(CONTRATO)
    m.update(origem="canal", canal={"nome": "Comparador Ficticio"})
    m["anfitria"]["selo"] = "Corretora Nível 5"
    vis = texto_visivel(PC.render_proposta_do_canal(m))
    assert all(a in vis for a, _b in PC.CRITERIOS_DO_NIVEL_5) and "versão 1" in vis
    m["canal"]["selo_criterios"] = [["Critério fictício A", "detalhe"], ["Critério fictício B", "detalhe"]]
    vis2 = texto_visivel(PC.render_proposta_do_canal(m))
    assert "Critério fictício A" in vis2 and PC.CRITERIOS_DO_NIVEL_5[0][0] not in vis2 and "os 2 itens" in vis2


def test_o_nome_do_canal_vem_da_config_e_nao_e_constante_do_renderizador():
    assert "Quem Cobra Menos" not in (BACKEND / "app/services/artifacts/proposta_canal_html.py").read_text(encoding="utf-8")
    m = copy.deepcopy(CONTRATO)
    m.update(origem="canal", canal={"nome": "Comparador Ficticio", "whatsapp": WHATS_DO_CANAL})
    doc = PC.render_proposta_do_canal(m)
    assert "Comparador Ficticio" in doc and "Quem Cobra Menos" not in doc


# =====================================================================================================================
# G6 · a CARTEIRA byte a byte
# =====================================================================================================================
def test_a_carteira_e_byte_a_byte_a_de_antes():
    tpl = POR_CHAVE["proposal.quote"]
    doc = tpl.renderizador(copy.deepcopy(CONTRATO))
    assert doc == PH.render_proposta(copy.deepcopy(CONTRATO))
    assert hashlib.sha256(doc.encode()).hexdigest()[:16] == SHA_DA_CARTEIRA_HTML
    png = render_previa_png(copy.deepcopy(CONTRATO))
    if png is not None:
        assert hashlib.sha256(png).hexdigest()[:16] == SHA_DA_CARTEIRA_PNG
    assert "Quem Cobra Menos" not in doc and 'class="qcm"' not in doc
    # CONTROLE: o MESMO modelo com origem canal sai pelo outro renderizador
    canal = dict(copy.deepcopy(CONTRATO), origem="canal")
    assert tpl.renderizador(canal) == PC.render_proposta_do_canal(canal) != PH.render_proposta(canal)


def test_a_previa_do_canal_tem_a_marca_e_nenhum_dado_pessoal():
    m = copy.deepcopy(CONTRATO)
    m.update(origem="canal", canal={"nome": "Comparador Ficticio"})
    p = PC.previa_do_canal(m)
    texto = json.dumps({k: v for k, v in p.items() if k != "logo"}, ensure_ascii=False)
    for pessoal in ("Mariana", "Compass", "2018/2019"):
        assert pessoal not in texto, pessoal
    assert p["marca_do_canal"] == "Comparador Ficticio" and p["corretoras"] is None
    png = render_previa_png(m)
    if png is not None:
        outro = copy.deepcopy(m)
        outro["cliente"]["primeiro_nome"] = "Joana"
        outro["bem"]["apelido"] = "Onix"
        assert render_previa_png(outro) == png                         # dado pessoal não muda um byte
        assert png != render_previa_png(dict(copy.deepcopy(CONTRATO)))  # CONTROLE: a da carteira é outra


# =====================================================================================================================
# MUTAÇÕES — cada guarda fica VERMELHO com o defeito reintroduzido (CLAUDE.md §9.3/§9.5)
# =====================================================================================================================
def test_MUTACOES_os_guardas_da_pagina_ficam_vermelhos(servido, monkeypatch):
    m, r, s, modelo = servido
    doc = s["html"]
    assert defeitos_da_pagina(doc, modelo) == []                                   # CONTROLE
    total = modelo["resumo"]["volume_do_canal"]["total"]
    mutacoes = {
        "a página da carteira no lugar da do canal": PH.render_proposta(modelo),
        "o número de corretoras": doc.replace("entre Corretoras de Nível 5", "entre 2 corretoras de Nível 5", 1),
        "a perdedora pelo nome": doc.replace("</main>", f"<p>{M.MARCA_BETA}</p></main>", 1),
        "o duelo de antes": doc.replace("</main>", "<p>Outra corretora parceira R$ 4.784,27</p></main>", 1),
        "o volume com a base duas vezes": doc.replace(f"Fiz <b>{total} cotações", f"Fiz <b>{total + 100} cotações", 1),
        "a economia errada": doc.replace(_br_int(modelo["resumo"]["economia"]["ate"]).replace(" ", AP.NB), "R$ 1", 1),
        "o preço cheio no lugar da parcela": re.sub(r'(<p class="parc">).*?(</p>)', r"\1<b>R$ 3.730,56</b>\2", doc, 1, re.S),
        "um script a mais": doc.replace("</body>", "<script>alert(1)</script></body>", 1),
        "um handler inline": doc.replace('<a class="cta"', '<a onclick="x()" class="cta"', 1),
        "o bloco Nível 5 sem selo": doc.replace('class="n5"', 'class="n5x"', 1),
    }
    for nome, mutado in mutacoes.items():
        assert mutado != doc, nome
        assert defeitos_da_pagina(mutado, modelo) != [], f"o guarda de '{nome}' não ficou vermelho"
    # o FECHAR: o destino de antes (o WhatsApp da anfitriã) é pego pelo guarda do redirecionamento
    monkeypatch.setattr(PC, "_digitos_do_canal", lambda modelo: M.WHATS_ALFA)
    destino = ArtifactService(m.banco.visao("rota-publica")).fechar_compartilhado(r["token"], "recomendada")
    assert not destino.startswith(f"https://wa.me/{WHATS_DO_CANAL}?")              # o teste do fechar ficaria vermelho


# =====================================================================================================================
# o navegador de verdade (Chromium, CSP real do /r/) e o contraste AA
# =====================================================================================================================
def _csp():
    return (f"default-src 'none'; script-src '{PH.HASH_DO_SCRIPT}'; img-src 'self' data:; style-src 'unsafe-inline'; "
            "font-src 'self' data:; base-uri 'none'; form-action 'none'")


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


@pytest.mark.parametrize("largura,esquema,js", [(390, "light", True), (390, "dark", True), (390, "light", False),
                                                (1280, "light", True), (1280, "dark", True)])
def test_navegador_sem_rolagem_lateral_sem_erro_de_csp_e_com_a_fonte(navegador, servido, largura, esquema, js):
    doc = re.sub(r'<meta property="og:image".*?twitter:image" content="[^"]*">', "", servido[2]["html"], flags=re.S)
    ctx = navegador.new_context(viewport={"width": largura, "height": 844 if largura < 600 else 900},
                                java_script_enabled=js, color_scheme=esquema)
    pg = ctx.new_page()
    erros = []
    pg.on("console", lambda msg: erros.append(msg.text) if msg.type in ("error", "warning") else None)
    pg.on("pageerror", lambda e: erros.append(str(e)))
    try:
        pg.set_content(doc.replace("<head>", f'<head>\n<meta http-equiv="Content-Security-Policy" content="{_csp()}">', 1),
                       wait_until="load")
        pg.wait_for_timeout(600)
        assert erros == []
        assert pg.evaluate("document.documentElement.scrollWidth") <= largura
        assert pg.evaluate("document.fonts.check('16px \"Instrument Sans\"')") is True
        assert pg.evaluate("document.documentElement.classList.contains('no-js')") is (not js)
        # o "Quero fechar" do vencedor e o rodapé (só no celular) com alvo de toque ≥ 44 px
        alturas = pg.evaluate("[...document.querySelectorAll('.cta,.want')].filter(e => e.offsetParent).map(e => e.offsetHeight)")
        assert alturas and min(alturas) >= 44
        dock = pg.evaluate("getComputedStyle(document.querySelector('.dock')).display")
        assert (dock == "none") is (largura >= 960)
    finally:
        ctx.close()


def _tokens(bloco):
    return dict(re.findall(r"--([a-z0-9-]+):(#[0-9A-Fa-f]{6})", bloco))


PARES_AA = [("ink-strong", "canvas"), ("ink", "surface"), ("ink-muted", "canvas"), ("ink-muted", "surface"),
            ("ink-muted", "surface-2"), ("hero-on", "hero"), ("hero-muted", "hero"), ("on-lime", "lime"),
            ("pos", "pos-bg"), ("neg", "neg-bg"), ("lime", "hero")]


def test_contraste_AA_nos_dois_temas():
    css = PC.CSS_DO_CANAL
    claro = _tokens(css.split("@media (prefers-color-scheme:dark)")[0])
    escuro = dict(claro, **_tokens(css.split(':root[data-theme="dark"]{')[1].split("}")[0]))
    for nome, v in (("claro", claro), ("escuro", escuro)):
        for frente, fundo in PARES_AA:
            assert AP.contraste(v[frente], v[fundo]) >= 4.5, f"{nome}: {frente} sobre {fundo}"
    assert AP.contraste(escuro["lime"], escuro["canvas"]) >= 4.5     # o nome do canal em limão no título escuro
