# -*- coding: utf-8 -*-
"""SPEC-130-C · F2 — AS PÁGINAS: a renovação no esqueleto da venda, o BLOCO DA CORRETORA nas três páginas (cotação,
renovação, Quem Cobra Menos), os RAMOS (auto 31, condomínio 16, residencial 2, empresarial 18, vida 91) e o QCM com o
carrossel único (`#track > .slot > .pass`, abas e "1 de N").

🔴 Cada guarda lê o HTML RENDERIZADO (o texto que se LÊ, `texto_visivel`) — nunca o modelo. As mutações da SPEC §6 que
estes guardas fecham, cada uma com a sua LINHA DE CONTROLE (o guarda consegue ficar vermelho — CLAUDE.md §9.3):

    (2) "Corretora premiada" com 0 prêmios                 → test_mutacao_2_*
    (3) "carro"/"guincho"/"FIPE" numa página de RE ou vida  → test_mutacao_3_*
    (4) `isAppMorte` (a chave crua) na tela                 → test_mutacao_4_*
    (5) a renovação com o `transform` 3D no cartão          → test_mutacao_5_*  (+ o navegador, se houver Chromium)

Modelos: o CONTRATO da 130-A (auto) e modelos de RE e de vida feitos AQUI à mão. ⛔ Nomes fictícios (CLAUDE.md §13.9):
a corretora é "Vega Corretora Ficticia". Nada de banco: F2 só lê o modelo (o fio com o banco é da F4).
Rodar: cd backend && .venv/Scripts/python.exe -m pytest tests/test_spec130c_as_paginas.py -q -p no:cacheprovider
"""
from __future__ import annotations

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

from app.services.artifacts import proposta_apresentacao as AP  # noqa: E402
from app.services.artifacts import proposta_canal_html as PC  # noqa: E402
from app.services.artifacts import proposta_corretora as BC  # noqa: E402
from app.services.artifacts import proposta_cotacao_html as PV  # noqa: E402
from app.services.artifacts import proposta_html as PH  # noqa: E402
from test_spec130a_o_fio import texto_visivel  # noqa: E402

CONTRATO = json.loads((BACKEND / "tests" / "fixtures" / "proposta" / "modelo_contrato.json").read_text(encoding="utf-8"))
NOME = "Vega Corretora Ficticia"
#: 📊 07/10/2026 — o retrato da CARTEIRA (o mesmo de `test_spec133a_a_pagina_canal.SHA_DA_CARTEIRA_HTML`): a carteira
#: não muda nesta SPEC
SHA_DA_CARTEIRA_HTML = "56d8c9e5469dc837"
#: 📊 16/10/2026 — o hash da CSP do `/r/` ANTES desta SPEC (sha256 do `SCRIPT_DA_PROPOSTA` de `git show HEAD:…` em
#: ee4f3eb, `scratchpad/f2/hash_head.py`): as páginas publicadas dependem dele; nenhum script novo
HASH_DO_SCRIPT_ANTES = "sha256-Y/94tzdeHaonwuJGufDjYV5rEPDMRM6ynCaISL21ts0="
#: base64 qualquer (a página só confere a FORMA do `data:`; os bytes são da marca — F1)
_B64 = "UklGRiQAAABXRUJQVlA4IBgAAAAwAQCdASoBAAEAAwA0JaQAA3AA/vuUAAA="
FOTOS = [{"src": f"data:image/webp;base64,{_B64}", "legenda": legenda} for legenda in
         ("A equipe no escritório", "Entrega do prêmio de 2025", "Atendimento no sábado", "")]
PREMIO = {"nome": "Prêmio Corretor Destaque", "ano": 2025}
#: 🔴 as palavras do AUTO que nunca aparecem em RE/vida — escritas AQUI de novo (a lente não usa o regex do módulo)
CARRO = re.compile(r"\b(carros?|guinchos?|fipe|b[ôo]nus|bat(?:er|eu|ida)|oficinas?|onix|compass)\b", re.I)


# =====================================================================================================================
# os modelos
# =====================================================================================================================
def _anf(rica: bool = True, **extra) -> dict:
    a = dict(copy.deepcopy(CONTRATO["anfitria"]), nome=NOME, susep="SUSEP 202031234")
    if rica:
        a.update(selo="Corretora Nível 5", premios=[dict(PREMIO)], fotos=copy.deepcopy(FOTOS))
    a.update(extra)
    return a


def venda(**anf) -> dict:
    m = copy.deepcopy(CONTRATO)
    m.update(pagina="venda", situacao="novo_sem_apolice", anfitria=_anf(**anf))
    m["venda"] = {"corretor": {"primeiro_nome": "Caio", "whatsapp": "5548988881320"},
                  "marca": {"seguradoras_parceiras": 5, "sobre": "Corretora de bairro. Atendemos pessoas."},
                  "diferenciais": ["Atendimento por pessoas, do orçamento ao sinistro"]}
    return m


def renovacao(anos=3, **anf) -> dict:
    m = copy.deepcopy(CONTRATO)
    m.update(situacao="renovacao", anfitria=_anf(**anf))
    m["opcoes"][0] = dict(m["opcoes"][0], id="sua_renovacao", rotulo="Sua renovação",
                          por_que="A mesma seguradora de hoje, com as mesmas coberturas.")
    m["renovacao"] = {"vence_em": "2026-10-20", "seguradora_atual": "Bradesco", "premio_atual": 4500.0,
                      "dono": {"primeiro_nome": "Bruna", "whatsapp": "5548999999999"}}
    if anos:
        m["renovacao"]["anos"] = anos
    return m


def canal(**anf) -> dict:
    m = copy.deepcopy(CONTRATO)
    m.update(origem="canal", canal={"nome": "Comparador Ficticio", "whatsapp": "5548900000000"}, anfitria=_anf(**anf))
    return m


#: os textos do AUTO (faq, sinistro) postos de propósito no modelo de RE/vida: a página do ramo tem de deixá-los fora
_FAQ_DO_AUTO = [{"p": "E se eu bater o carro?", "r": "Você avisa a corretora e acompanhamos a oficina."},
                {"p": "Posso mudar a franquia?", "r": "Pode. A corretora mostra quanto muda no preço."}]
_SINISTRO_DO_AUTO = ["Você avisa a corretora pelo WhatsApp", "Acompanha o guincho e a oficina com você"]


def _op(i: str, rotulo: str, seguradora: str, premio: float, coberturas: list, **extra) -> dict:
    return dict({"id": i, "rotulo": rotulo, "seguradora": seguradora, "produto": "", "premio_anual": premio,
                 "parcelas": {"vezes": 6, "valor": round(premio / 6, 2)}, "coberturas": coberturas,
                 "motivos": ["Menor preço entre as seguradoras com a mesma cobertura"], "o_que_muda": []}, **extra)


def _re(ramo: int) -> list[dict]:
    cob = [{"chave": "isDanosIncendioRaioExplosao", "nome": "Básica (incêndio, raio e explosão)", "valor": "R$ 2.000.000"},
           {"chave": "isDanosEletricos", "nome": "Danos elétricos", "valor": "R$ 50.000"},
           {"chave": "isDanosVendaval", "nome": "Vendaval", "valor": "R$ 100.000"},
           {"chave": "isValorCondominio", "nome": "RC Condomínio", "valor": "R$ 200.000"},
           {"chave": "vidros", "nome": "Vidros", "valor": "R$ 20.000"},
           {"chave": "isDanosRouboNovo", "nome": "isDanosRouboNovo", "valor": "R$ 30.000"}]
    mais = cob + [{"chave": "lucroCessante", "nome": "Lucros cessantes", "valor": "R$ 80.000"}]
    return [_op("recomendada", "Recomendada", "Seguradora Ficticia A", 3120.4, cob),
            _op("mais_completa", "Mais completa", "Seguradora Ficticia B", 3580.0, mais,
                o_que_muda=["Lucros cessantes incluídos"])]


def _vida() -> list[dict]:
    cob = [{"chave": "isAppMorte", "nome": "isAppMorte", "valor": "100000"},
           {"chave": "isAppMorteAcidental", "nome": "isAppMorteAcidental", "valor": "100000"},
           {"chave": "isAppInvalidez", "nome": "isAppInvalidez", "valor": "50000"},
           {"chave": "isInvalidezDoenca", "nome": "isInvalidezDoenca", "valor": "0"},
           {"chave": "isCoberturaNovaFicticia", "nome": "isCoberturaNovaFicticia", "valor": "20000"}]
    return [_op("recomendada", "Recomendada", "Seguradora Ficticia A", 612.0, cob),
            _op("outra_completa", "Outra seguradora", "Seguradora Ficticia B", 655.0, copy.deepcopy(cob))]


_BEM = {16: {"rotulo": "condomínio", "descricao": "Condomínio residencial, 48 unidades"},
        2: {"rotulo": "imóvel", "descricao": "Apartamento"},
        18: {"rotulo": "empresa", "descricao": "Escritório comercial"},
        91: {"rotulo": "vida"}}


def do_ramo(ramo: int, *, renova: bool = False, **anf) -> dict:
    base = renovacao(**anf) if renova else venda(**anf)
    base.update(ramo=ramo, bem=_BEM[ramo], opcoes=_vida() if ramo == AP.RAMO_VIDA else _re(ramo),
                faq=copy.deepcopy(_FAQ_DO_AUTO), sinistro=list(_SINISTRO_DO_AUTO), ranking=[], produto_diferente=[],
                nao_responderam=[], veiculo=None)
    base.pop("veiculo", None)
    if renova:
        base["opcoes"][0].update(id="sua_renovacao", rotulo="Sua renovação", por_que="A mesma seguradora de hoje.")
    return base


PAGINAS = {"venda": (PV.render_cotacao, venda), "renovacao": (PH.render_proposta, renovacao),
           "canal": (PC.render_proposta_do_canal, canal)}


def _pagina(nome: str, **anf) -> str:
    render, fabrica = PAGINAS[nome]
    return render(fabrica(**anf))


def _bloco(doc: str) -> str:
    m = re.search(r'<section class="s bc"[^>]*>(.*?)</section>', doc, re.S)
    return m.group(1) if m else ""


# =====================================================================================================================
# 1. o BLOCO DA CORRETORA — a ordem, nas três páginas
# =====================================================================================================================
_ORDEM_DO_BLOCO = ['id="h-corretora"', 'class="bc-card"', 'class="bc-selos"', 'class="bc-titulo"', 'class="bc-itens"',
                   'class="bc-fotos']
_TITULO = {"venda": f"Por que fechar com a {NOME}", "renovacao": "Mais um ano em boas mãos",
           "canal": "Quem é a corretora que cobra menos?"}


@pytest.mark.parametrize("pagina", sorted(PAGINAS))
def test_o_bloco_na_ordem_nas_tres_paginas(pagina):
    doc = _pagina(pagina)
    bloco = _bloco(doc)
    pos = [bloco.find(x) for x in _ORDEM_DO_BLOCO]
    assert all(p >= 0 for p in pos), [x for x, p in zip(_ORDEM_DO_BLOCO, pos) if p < 0]
    assert pos == sorted(pos), "título → cartão → selos → título do nível → itens → fotos"
    assert bloco.count('<li class="bc-selo') == 2                                    # Nível 5 + premiada, lado a lado
    vis = texto_visivel(bloco)
    assert vis.startswith(_TITULO[pagina]), vis[:80]
    assert f"{NOME}, corretora premiada Nível 5" in vis
    assert "Corretora Nível 5" in vis and "Corretora premiada" in vis and "Prêmio Corretor Destaque · 2025" in vis
    # §9.3 (conserto KA, D-130C-11): os itens viraram COMPROMISSOS (versão 2 da lista) e cada foto diz "Foto N de 4"
    # (laudo de design, pendência 5) — antes: "versão 1" e nenhum "Foto " visível
    assert all(a in vis for a, _b in BC.CRITERIOS_DO_NIVEL_5) and "versão 2" in vis
    assert re.findall(r"Foto \d de 4", vis) == [f"Foto {i} de 4" for i in range(1, 5)]
    assert len(re.findall(r'<figure class="bc-foto"', bloco)) == 4
    assert 'aria-label="Foto 1 de 4"' in bloco and 'alt="A equipe no escritório"' in bloco
    assert f'alt="Foto da {NOME}"' in bloco                                          # a foto sem legenda
    # o bloco vem DEPOIS das opções e ANTES de "quem cuida de você" (venda/renovação)
    assert doc.find('id="track"') < doc.find('id="h-corretora"')
    if pagina != "canal":
        assert doc.find('id="h-corretora"') < doc.find('id="h-host"')


def test_cada_momento_tem_a_sua_voz():
    v, r, c = (texto_visivel(_bloco(_pagina(p))) for p in ("venda", "renovacao", "canal"))
    assert "Quem representa você é a corretora." in v and "5 seguradoras parceiras da corretora" in v
    assert "Atendimento por pessoas, do orçamento ao sinistro" in v and "no Google" in v
    assert "Quem já conhece o seu seguro." in r and "Você renova com a gente há 3 anos." in r
    assert "no Google" not in r                                   # quem já é cliente não precisa de prova de estranho
    assert "O Comparador Ficticio só compara" in c and "Só cotamos com Corretoras Nível 5" in c
    # §9.3 (conserto K2, laudo de design R2 pendência 5): a venda mostra a SUSEP no cartão como o QCM (antes: só no
    # canal); a renovação continua com ela só no topo
    assert "SUSEP 202031234" in c and "SUSEP 202031234" in v and "202031234" not in r
    # "renova com a gente há N anos" SÓ com prova (CDC art. 37)
    assert "renova com a gente" not in texto_visivel(PH.render_proposta(renovacao(anos=None)))


def test_o_cartao_magro_continua_cartao():
    """📊 BLOCO 0 M9: a marca publicada SEM ano, SEM diferenciais, SEM parceiras, 0 fotos — nome, cidade, o texto do
    momento e o selo fazem o cartão."""
    m = venda(rica=False, desde=None, google=None, selo="Corretora Nível 5")
    m["venda"] = {}
    bloco = _bloco(PV.render_cotacao(m))
    vis = texto_visivel(bloco)
    assert NOME in vis and "Florianópolis" in vis and "Quem representa você é a corretora." in vis
    # §9.3 (conserto K2, pendência 5): o único fato do cartão é a SUSEP (a venda a mostra como o QCM)
    assert [texto_visivel(x) for x in re.findall(r"<li><b[^>]*>(.*?)</b>",
                                                 re.search(r'<ul class="bc-fatos">(.*?)</ul>', bloco).group(1))] == \
        ["SUSEP 202031234"]
    assert 'class="bc-fotos' not in bloco and "no mercado" not in vis
    assert bloco.count('<li class="bc-selo') == 1 and f"{NOME}, corretora Nível 5" in vis


# =====================================================================================================================
# 2. mutação 2 — "premiada" SÓ com prêmio (CDC art. 37); sem selo, sem nível; sem fotos, sem carrossel
# =====================================================================================================================
def premiada_sem_premio(doc: str, modelo: dict) -> bool:
    return "premiad" in texto_visivel(doc).lower() and not BC.premios_da_anfitria(modelo)


@pytest.mark.parametrize("pagina", sorted(PAGINAS))
def test_mutacao_2_sem_premio_nenhuma_premiada(pagina):
    render, fabrica = PAGINAS[pagina]
    for premios in ([], [{"nome": "  ", "ano": 2025}], None):
        m = fabrica(premios=premios)
        doc = render(m)
        assert not premiada_sem_premio(doc, m), premios
        assert _bloco(doc).count('<li class="bc-selo') == 1 and f"{NOME}, corretora Nível 5" in texto_visivel(doc)
    # CONTROLE: com 1 prêmio a palavra aparece; e o guarda pega "premiada" numa página sem prêmio
    assert "Corretora premiada" in texto_visivel(render(fabrica()))
    m = fabrica(premios=[])
    assert premiada_sem_premio(render(m).replace("</main>", "<p>Corretora premiada</p></main>"), m)


def test_sem_selo_some_o_nivel_e_os_premios_vao_ao_cartao():
    for pagina in PAGINAS:
        doc = _pagina(pagina, selo=None)
        bloco = _bloco(doc)
        assert 'class="bc-selos' not in bloco and 'class="bc-titulo"' not in bloco and 'class="bc-itens"' not in bloco
        assert "Nível 5" not in texto_visivel(bloco)
        assert 'class="bc-card"' in bloco and 'class="bc-fotos' in bloco                     # fica cartão + fotos
        assert "Prêmio Corretor Destaque · 2025" in texto_visivel(bloco)                       # o prêmio, como linha


def test_sem_fotos_o_carrossel_some_e_foto_que_nao_e_imagem_fica_fora():
    for pagina in PAGINAS:
        assert 'class="bc-fotos' not in _pagina(pagina, fotos=[])
    ruins = [{"src": "https://exemplo.test/foto.webp", "legenda": "url"},
             {"src": "javascript:alert(1)", "legenda": "js"},
             {"src": f"data:image/svg+xml;base64,{_B64}", "legenda": "svg"},
             {"src": f"data:text/html;base64,{_B64}", "legenda": "html"},
             {"src": f"data:image/webp;base64,{_B64}\"><script>x</script>", "legenda": "fecha"},
             {"src": "data:image/webp;base64," + "A" * (BC.TETO_DA_FOTO + 1), "legenda": "gigante"},
             "não é dict"]
    m = venda(fotos=ruins + [FOTOS[0]])
    assert BC.fotos_da_anfitria(m) == [FOTOS[0]]
    doc = PV.render_cotacao(m)
    assert len(re.findall(r'<figure class="bc-foto"', doc)) == 1 and "javascript:" not in doc and "<script>x" not in doc
    assert len(BC.fotos_da_anfitria(venda(fotos=FOTOS * 3))) == BC.TETO_DE_FOTOS                 # 4 na página


# =====================================================================================================================
# 3. os RAMOS — mutação 3 (nenhuma palavra de carro fora do auto) e o título pelo ramo
# =====================================================================================================================
_H1 = {16: "a cotação do seguro do condomínio está pronta", 2: "a cotação do seu seguro residencial está pronta",
       18: "a cotação do seguro da sua empresa está pronta", 91: "a cotação do seu seguro de vida está pronta"}


def palavras_de_carro(doc: str) -> list:
    return sorted({x.lower() for x in CARRO.findall(texto_visivel(doc))})


@pytest.mark.parametrize("ramo", [16, 2, 18, 91])
@pytest.mark.parametrize("renova", [False, True], ids=["cotacao", "renovacao"])
def test_mutacao_3_re_e_vida_sem_palavra_de_carro(ramo, renova):
    m = do_ramo(ramo, renova=renova)
    doc = PH.render_proposta(m)
    assert palavras_de_carro(doc) == [], palavras_de_carro(doc)
    h1 = texto_visivel(re.search(r"<h1>(.*?)</h1>", doc, re.S).group(1))
    quem = CONTRATO["cliente"]["primeiro_nome"]
    assert h1.startswith(f"{quem}, {_H1[ramo]}".replace("cotação", "renovação" if renova else "cotação")), h1
    assert "Posso mudar a franquia?" in texto_visivel(doc)                   # a dúvida que NÃO fala de carro fica
    if not renova:
        assert "Se ela pedir vistoria, avisamos" in texto_visivel(doc)       # o padrão sem o "do carro"
    # CONTROLE: o MESMO modelo como auto tem as palavras (o guarda consegue falhar)
    assert palavras_de_carro(PH.render_proposta(dict(m, ramo=AP.RAMO_AUTO)))


def test_o_auto_continua_falando_de_carro():
    doc = PV.render_cotacao(venda())
    assert {"carro", "guincho"} <= set(palavras_de_carro(doc))
    assert "E se eu bater o carro?" in texto_visivel(doc)


# =====================================================================================================================
# 4. mutação 4 — a VIDA com os nomes do cliente (nunca a chave crua); o RE com os ícones dele
# =====================================================================================================================
@pytest.mark.parametrize("renova", [False, True], ids=["cotacao", "renovacao"])
def test_mutacao_4_vida_sem_a_chave_crua(renova):
    doc = PH.render_proposta(do_ramo(AP.RAMO_VIDA, renova=renova))
    vis = texto_visivel(doc)
    sem_script = re.sub(r"<script\b.*?</script>", "", doc, flags=re.S)        # (o script tem `isSpread`)
    assert not re.search(r"\bis[A-Z]", sem_script), re.findall(r"\bis[A-Z]\w+", sem_script)[:5]
    for nome in ("Morte", "Morte acidental", "Invalidez por acidente", "Cobertura nova ficticia"):
        assert nome in vis, nome
    assert "R$ 100.000" in vis and "Invalidez por doença" not in vis           # capital zero = não contratada
    assert "Franquia" not in vis                                                # franquia só se existir
    # CONTROLE: sem o dicionário (o modelo cru direto no cartão) a chave aparece — o guarda consegue falhar
    cru = do_ramo(AP.RAMO_VIDA, renova=renova)
    assert re.search(r"\bisAppMorte\b", PH._celula_cobertura("isAppMorte", cru["opcoes"][0], cru["opcoes"][0], "li"))


def test_re_com_os_nomes_e_os_icones_do_ramo():
    doc = PV.render_cotacao(do_ramo(AP.RAMO_CONDOMINIO))
    vis = texto_visivel(doc)
    assert "Danos elétricos" in vis and "Danos roubo novo" in vis and "isDanos" not in doc
    assert PH.ICO_DOS_RAMOS["isDanosEletricos"] in doc and PH.ICO_DOS_RAMOS["vidros"] in doc
    assert PH.ICO["vidros"] not in doc                                          # o para-brisa nunca no condomínio
    # a manchete da prévia pelo ramo, sem dado pessoal
    assert PH.previa_do_modelo(do_ramo(16))["manchete"] == "A cotação do seguro do condomínio está pronta"
    assert PH.previa_do_modelo(do_ramo(91, renova=True))["manchete"] == "A renovação do seu seguro de vida está pronta"


def test_os_ramos_sao_os_do_contrato():
    from portal_worker.multicalculo import contrato as K
    assert (AP.RAMO_AUTO, AP.RAMO_RESIDENCIAL, AP.RAMO_CONDOMINIO, AP.RAMO_EMPRESARIAL) == (
        K.RAMO_AUTO, K.RAMO_RESIDENCIAL, K.RAMO_CONDOMINIO, K.RAMO_EMPRESARIAL)
    assert AP.RAMO_VIDA == int(K.RAMO_VIDA) and set(K.RAMOS_RE) <= set(AP.FALA_DO_RAMO)


# =====================================================================================================================
# 5. mutação 5 — a RENOVAÇÃO no esqueleto da venda: sem o 3D da carteira, com abas e "1 de N"
# =====================================================================================================================
def cartao_com_3d(doc: str) -> bool:
    """O cartão da carteira gira (`rotateY` + máscara) quando o script escreve `--d`; a venda neutraliza com
    `.venda .pass{…transform:none…mask:none}` no `<body class="venda">`. Sem as duas coisas, o 3D volta."""
    corpo = re.search(r'<body class="([^"]*)"', doc)
    neutro = re.search(r"\.venda \.pass\{[^}]*transform:none[^}]*mask:none", doc)
    cartoes = re.findall(r'<article class="(pass[^"]*)"', doc)
    return not (corpo and "venda" in corpo.group(1).split() and neutro and cartoes
                and all("op" in c.split() for c in cartoes))


def test_mutacao_5_a_renovacao_sem_o_3d_e_com_as_abas():
    doc = PH.render_proposta(renovacao())
    assert not cartao_com_3d(doc)
    assert 'id="track"' in doc and 'role="tablist"' in doc and 'id="count"' in doc and '>1 de 3<' in doc
    assert doc.count('class="tab"') == 3 and doc.count('<div class="slot"') == 3
    vis = texto_visivel(doc)
    assert vis.count("vence em") == 1 and "Mais um ano em boas mãos" in vis and "Quero renovar" in vis
    # §9.3 (conserto K2, laudo de design R2 pendência 1): o preço do CONTRATO vale até ANTES do vencimento (20/10) — o
    # apelo usa a data do preço; a frase de antes vale quando o preço dura até o vencimento (test_k2_2)
    assert re.search(r"Renove até \d\d/\d\d e garanta este preço — o seu seguro vale até 20/10", vis), vis[:600]
    assert "O mesmo atendimento: Bruna continua cuidando de você" in vis
    for proibida in ("a melhor das", "Nossa recomendação", "Onde cada opção cai", "Comparação independente"):
        assert proibida not in vis, proibida
    assert 'class="regua' not in doc and 'class="duel' not in doc
    # a ordem do contrato da renovação
    ordem = ['<header class="wrap vtop">', "<h1>", 'id="h-oferta"', 'id="h-hoje"', 'id="track"', 'id="comparar"',
             'id="h-corretora"', 'id="h-host"', 'id="h-sin"', 'id="h-faq"', 'id="h-fim"', 'id="todas"', 'class="legal"']
    pos = [doc.find(x) for x in ordem]
    assert all(p >= 0 for p in pos) and pos == sorted(pos), list(zip(ordem, pos))
    # CONTROLE: a página de antes (o `.track` da carteira, sem o `venda`) é pega pelo guarda
    assert cartao_com_3d(doc.replace('<body class="venda renova">', '<body class="renova">'))
    assert cartao_com_3d(PH.render_proposta(copy.deepcopy(CONTRATO)))                      # a carteira gira (é dela)


def test_a_renovacao_sem_numero_nao_promete_whatsapp():
    m = renovacao()
    m["anfitria"].pop("whatsapp", None)
    m["renovacao"]["dono"].pop("whatsapp", None)
    doc = PH.render_proposta(m)
    vis = texto_visivel(doc)
    assert 'class="dock"' not in doc and "wa.me/" not in doc and "Quero renovar" not in vis
    assert "responda a mensagem em que recebeu este link" in vis and "toque em" not in vis


# =====================================================================================================================
# 6. o QUEM COBRA MENOS no carrossel da venda (D-130C-09)
# =====================================================================================================================
def test_o_qcm_usa_o_carrossel_com_abas_da_venda():
    m = canal()
    doc = PC.render_proposta_do_canal(m)
    assert re.search(r'<div class="ops[^"]*" id="track"[^>]*>\s*<div class="slot"', doc)
    assert doc.count('<div class="slot"') == len(m["opcoes"]) == doc.count('class="tab"')
    assert 'role="tablist"' in doc and f">1 de {len(m['opcoes'])}<" in doc and 'id="close-sub"' in doc
    assert re.findall(r'data-opcao="([^"]+)"', doc) == [o["id"] for o in m["opcoes"]]
    assert 'class="track"' not in doc                                     # o trilho 3D da carteira não entra
    dados = json.loads(re.search(r'id="ab-dados">(.*?)</script>', doc, re.S).group(1))
    assert all(o.get("sub") and o.get("aria") for o in dados["opcoes"])   # o "Quero fechar" acompanha o cartão
    assert 'class="n5"' not in doc and "Só cotamos com Corretoras Nível 5" in texto_visivel(doc)   # não se repete
    assert texto_visivel(doc).count("Só cotamos com Corretoras Nível 5") == 1


# =====================================================================================================================
# 7. o que NÃO muda: a carteira byte a byte, o hash da CSP, um script só
# =====================================================================================================================
def test_a_carteira_e_byte_a_byte_a_de_antes():
    doc = PH.render_proposta(copy.deepcopy(CONTRATO))
    assert hashlib.sha256(doc.encode()).hexdigest()[:16] == SHA_DA_CARTEIRA_HTML
    assert 'class="bc' not in doc                                          # o bloco não entra na carteira


def test_o_hash_do_script_e_o_de_antes_e_cada_pagina_tem_um_script_so():
    assert PH.HASH_DO_SCRIPT == HASH_DO_SCRIPT_ANTES
    for pagina in PAGINAS:
        doc = _pagina(pagina)
        execs = [c for a, c in re.findall(r"<script([^>]*)>(.*?)</script>", doc, re.S) if "application/json" not in a]
        assert execs == [PH.SCRIPT_DA_PROPOSTA], pagina
        sem = re.sub(r"<script\b.*?</script>", "", doc, flags=re.S)
        assert not re.search(r"\son[a-z]+\s*=", sem, re.I), pagina          # nenhum handler inline (a CSP o bloquearia)
        # o carrossel das fotos é CSS: não usa as classes que o script dirige
        assert not re.search(r'class="bc-[^"]*\b(slot|tab|pass)\b', doc)


def test_o_css_do_bloco_cabe_nas_regras_da_pagina():
    css = BC.CSS_DO_BLOCO_DA_CORRETORA
    tamanhos = [float(x) for x in re.findall(r"font-size:(\d+(?:\.\d+)?)px", css)]
    assert tamanhos and min(tamanhos) >= 12                                 # nenhuma fonte < 12 px
    assert "scroll-snap-type:x mandatory" in css and "@media print" in css
    assert "prefers-color-scheme:dark" in css and 'data-theme="dark"' in css
    assert "transform:" not in re.sub(r"rotate\([^)]*\)", "", css)          # nenhum 3D no bloco


# =====================================================================================================================
# 8. CONSERTO KA — os laudos da 130-C (design B1–B4 + pendências 2/4/5, juiz B1, red team B1/B2). Cada guarda nasceu
#    VERMELHO no código de 15bb812 e tem a sua mutação ou linha de controle (CLAUDE.md §9.3/§9.5)
# =====================================================================================================================
#: 🔴 D-130C-11 (gerente, nota 88): o selo Nível 5 FICA em toda cotação e renovação (ordem do Founder), mas ninguém
#: confere os itens por corretora — o bloco não pode afirmar conferência, prova, certificado ou garantia (CDC art. 37)
_AFIRMA_CONFERENCIA = re.compile(r"conferid|comprovad|certificad|garantid", re.I)


def selo_afirma_o_que_ninguem_confere(doc: str) -> list:
    return sorted({x.lower() for x in _AFIRMA_CONFERENCIA.findall(texto_visivel(_bloco(doc)))})


def _paginas_com_selo():
    yield "venda", PV.render_cotacao(venda())
    yield "renovacao", PH.render_proposta(renovacao())
    yield "canal", PC.render_proposta_do_canal(canal())
    for ramo in (16, 91):
        for renova in (False, True):
            yield f"{ramo}-{'renovacao' if renova else 'venda'}", PH.render_proposta(do_ramo(ramo, renova=renova))


def test_ka1_o_selo_diz_compromissos_e_nunca_que_alguem_confere():
    for nome, doc in _paginas_com_selo():
        vis = texto_visivel(_bloco(doc))
        assert selo_afirma_o_que_ninguem_confere(doc) == [], (nome, selo_afirma_o_que_ninguem_confere(doc))
        assert "cinco compromissos" in vis and "5 compromissos" in vis, (nome, vis[:600])
        assert "cumpre os" not in vis and "o multicálculo prova" not in vis and "24 horas" not in vis, nome
    # cada compromisso diz como o CLIENTE vê: a SUSEP está no topo desta página. §9.3 (conserto K2, pendência 5): o
    # cartão da venda passou a mostrar a SUSEP como o do QCM — o número do cartão é o MESMO do topo (test_k2_7)
    v = texto_visivel(_bloco(PV.render_cotacao(venda())))
    assert "o número está no topo desta página" in v and "SUSEP 202031234" in v
    sem = texto_visivel(_bloco(PV.render_cotacao(venda(susep=None))))
    assert "o número está" not in sem and f"peça o número à {NOME}" in sem
    # a nota do Google só é "a desta página" quando a página a mostra (a renovação nunca mostra Google)
    assert "a nota do Google aparece no cartão acima" in v
    r = texto_visivel(_bloco(PH.render_proposta(renovacao())))
    assert "no cartão acima" not in r and "nunca escolhida a dedo" in r
    # o WhatsApp só é prometido onde a página tem o botão (o canal volta à conversa DELE, não à da corretora)
    assert "o botão de WhatsApp desta página" in v
    c = texto_visivel(_bloco(PC.render_proposta_do_canal(canal())))
    assert "o botão de WhatsApp desta página" not in c and "Só cotamos com Corretoras Nível 5" in c
    # a lista da config continua vencendo (e o número por extenso acompanha)
    m = venda()
    m["anfitria"]["selo_criterios"] = [["Compromisso fictício A", "detalhe"], ["Compromisso fictício B", "detalhe"]]
    vm = texto_visivel(_bloco(PV.render_cotacao(m)))
    assert "Compromisso fictício A" in vm and "dois compromissos" in vm and BC.CRITERIOS_DO_NIVEL_5[0][0] not in vm
    # MUTAÇÃO: a frase antiga de volta → o guarda fica VERMELHO
    doc = PV.render_cotacao(venda())
    antiga = doc.replace('<p class="bc-sub">', '<p class="bc-sub">a Vega cumpre os 5 itens — e cada um é conferido. ', 1)
    assert selo_afirma_o_que_ninguem_confere(antiga) == ["conferid"]


#: 📊 o leitor de RE grava franquia 0 quando a seguradora NÃO informou (`leitor_agger.py:585`: 0 em 38 resultados,
#: ausente em 22 — laudo de design 130-C B2) — "Franquia R$ 0" é afirmação sem dado
_FRANQUIA_NA_TELA = re.compile(r"[Ff]ranquia:?\s+R\$|pesa preço, franquia")


def franquia_sem_dado(doc: str) -> list:
    return _FRANQUIA_NA_TELA.findall(texto_visivel(doc))


def _re_com_franquia(valores, renova=False, ramo=16):
    m = do_ramo(ramo, renova=renova)
    for o, v in zip(m["opcoes"], valores):
        if v is not None:
            o["franquia"] = {"valor": v, "tipo": ""}
    m["ranking"] = [{"seguradora": o["seguradora"], "premio_anual": o["premio_anual"],
                     "franquia": (o.get("franquia") or {}).get("valor")} for o in m["opcoes"]]
    m["faq"] = []
    return m


@pytest.mark.parametrize("renova", [False, True], ids=["cotacao", "renovacao"])
def test_ka2_fora_do_auto_franquia_zero_e_sem_franquia(renova):
    for valores in ((0, 0.0), (0, None), (None, None)):
        m = _re_com_franquia(valores, renova=renova)
        doc = PH.render_proposta(m)
        assert franquia_sem_dado(doc) == [], (valores, franquia_sem_dado(doc))
        previa = PH._previa_da_renovacao(m) if renova else PV.previa_da_cotacao(m)
        assert previa["franquia"] == "", previa["franquia"]
        if not renova:
            assert "pesa preço e coberturas" in texto_visivel(doc)
    # CONTROLE: com uma franquia DE VERDADE ela aparece (e a régua volta a pesar a franquia); o auto não muda
    doc = PH.render_proposta(_re_com_franquia((5000, 0), renova=renova))
    assert "Franquia R$ 5.000" in texto_visivel(doc) and "Franquia R$ 0" not in texto_visivel(doc)
    if not renova:
        assert "pesa preço, franquia e coberturas" in texto_visivel(doc)
        assert "pesa preço, franquia e coberturas" in texto_visivel(PV.render_cotacao(venda()))


@pytest.mark.parametrize("renova", [False, True], ids=["cotacao", "renovacao"])
def test_ka2_vida_sem_vistoria_nem_franquia_no_rodape(renova):
    doc = PH.render_proposta(do_ramo(AP.RAMO_VIDA, renova=renova))
    legal = texto_visivel(re.search(r'<footer class="legal">(.*?)</footer>', doc, re.S).group(1))
    assert "vistoria" not in legal and "franquia" not in legal.lower(), legal
    assert "O preço final depende da aceitação da seguradora." in legal
    # CONTROLE: no condomínio a vistoria do imóvel é real — a frase fica
    doc_re = PH.render_proposta(do_ramo(16, renova=renova))
    assert "vistoria" in texto_visivel(re.search(r'<footer class="legal">(.*?)</footer>', doc_re, re.S).group(1))


#: o FAQ e o "se acontecer" da config trazem `{corretora}`/`{validade}` e "a sua corretora" — as três páginas trocam
_CHAVE_CRUA = re.compile(r"\{[a-z_]+\}")


def chaves_cruas(doc: str) -> list:
    return _CHAVE_CRUA.findall(texto_visivel(doc))


def _faq_da_config(ramo: int = AP.RAMO_AUTO) -> list:
    from app.services.multicalculo.config import PADRAO_DO_PRODUTO
    pag = PADRAO_DO_PRODUTO["servicos"]["cotacao"]["pagina"]
    lista = pag["faq"] if ramo == AP.RAMO_AUTO else pag["por_ramo"]["vida" if ramo == AP.RAMO_VIDA else "re"]["faq"]
    return [{"p": f["pergunta"], "r": f["resposta"]} for f in lista]


_SINISTRO_DA_CONFIG = ["Avise a sua corretora assim que puder", "Ela orienta o que fazer e abre o aviso de sinistro",
                       "A corretora acompanha com a seguradora até o fim"]


def _paginas_com_os_textos_da_config():
    for ramo in (31, 16, 91):
        for nome, fabrica, render in (("venda", venda, PV.render_cotacao), ("renovacao", renovacao, PH.render_proposta),
                                      ("canal", canal, PC.render_proposta_do_canal)):
            if nome == "canal" and ramo != 31:
                continue
            m = fabrica() if ramo == 31 else do_ramo(ramo, renova=(nome == "renovacao"))
            m.update(faq=_faq_da_config(ramo), sinistro=list(_SINISTRO_DA_CONFIG), validade_ate="2026-11-13")
            yield f"{nome}-{ramo}", render(m)


def test_ka3_nenhuma_pagina_mostra_chave_crua_e_o_qcm_diz_o_nome():
    paginas = dict(_paginas_com_os_textos_da_config())
    assert len(paginas) == 7
    for nome, doc in paginas.items():
        assert chaves_cruas(doc) == [], (nome, chaves_cruas(doc))
    qcm = paginas["canal-31"]
    vis = texto_visivel(qcm)
    assert f"Você avisa a {NOME}. A {NOME} orienta o que fazer" in vis
    assert "valem até 13/11/2026" in vis
    sin = texto_visivel(re.search(r'<section class="s" aria-labelledby="h-sin">(.*?)</section>', qcm, re.S).group(1))
    assert f"Avise a {NOME} assim que puder." in sin and f"A {NOME} acompanha" in sin and "sua corretora" not in sin
    # MUTAÇÃO: a chave crua de volta → VERMELHO
    assert chaves_cruas(qcm.replace("</main>", "<p>Você avisa a {corretora}.</p></main>")) == ["{corretora}"]


@pytest.mark.parametrize("ramo", [16, 91])
def test_ka4_o_sinistro_diz_com_quem(ramo):
    vis = texto_visivel(PV.render_cotacao(do_ramo(ramo)))
    assert f"Quem cuida do seu caso com a seguradora é a {NOME}, não um 0800." in vis
    assert "com ela" not in vis
    # CONTROLE: no auto com assistência, "ela" tem a quem se referir (a seguradora do guincho)
    auto = texto_visivel(PV.render_cotacao(venda()))
    assert "O guincho e a assistência 24 h são da seguradora. Quem cuida do seu caso com ela" in auto


def _vida_com_capital(n=2, origem="pedido", renova=False):
    m = do_ramo(AP.RAMO_VIDA, renova=renova)
    m["opcoes"] = m["opcoes"][:n]
    for o in m["opcoes"]:
        o["capital_segurado"] = {"valor": 100000, "origem": origem}
    return m


def _cartoes(doc: str) -> list:
    return re.findall(r'<article class="pass op".*?</article>', doc, re.S)


@pytest.mark.parametrize("renova", [False, True], ids=["cotacao", "renovacao"])
def test_ka5_a_vida_diz_o_capital(renova):
    doc = PH.render_proposta(_vida_com_capital(renova=renova))
    hero = texto_visivel(re.search(r'<article class="oferta".*?</article>', doc, re.S).group(0))
    assert "Capital segurado R$ 100.000" in hero and ("o valor pedido na renovação" if renova
                                                      else "o valor que você pediu") in hero, hero
    assert _cartoes(doc) and all("Capital segurado R$ 100.000" in texto_visivel(c) for c in _cartoes(doc))
    # a seguradora devolveu o capital: sem "pediu"
    seg = texto_visivel(PH.render_proposta(_vida_com_capital(origem="seguradora", renova=renova)))
    assert "Capital segurado R$ 100.000" in seg and "pediu" not in seg and "valor pedido" not in seg
    # CONTROLE: sem o campo, nada (nunca um capital inventado)
    assert "Capital segurado" not in texto_visivel(PH.render_proposta(do_ramo(AP.RAMO_VIDA, renova=renova)))


def test_ka5_uma_opcao_so_o_cartao_nao_repete_o_hero():
    doc = PV.render_cotacao(_vida_com_capital(n=1))
    cart = _cartoes(doc)
    assert len(cart) == 1 and 'class="preco"' not in cart[0] and "Capital segurado" not in texto_visivel(cart[0])
    assert "Morte" in texto_visivel(cart[0])                               # o que se compra, sem repetir o preço
    assert re.search(r'<h2 id="h-op">O que está coberto</h2>', doc) and 'id="track"' in doc   # o script segue igual
    # sem cobertura nenhuma (o robô real devolve assim): a frase honesta no lugar da lista
    m = _vida_com_capital(n=1)
    m["opcoes"][0]["coberturas"] = []
    assert f"a {NOME} confirma cada cobertura com você antes de fechar" in texto_visivel(PV.render_cotacao(m))
    # CONTROLE: com 2 opções, os cartões têm o preço (o carrossel de sempre)
    assert all('class="preco"' in c for c in _cartoes(PV.render_cotacao(_vida_com_capital(n=2))))


def _renovacao_com_as_franquias(tipos=("Reduzida", "Reduzida", "Reduzida")):
    m = renovacao()
    m["opcoes"][0].update(franquia={"valor": 5170.54, "tipo": tipos[0]},
                          motivos=["Franquia: R$ 5.170,54", "Carro reserva por 15 dias"])
    m["opcoes"][1].update(franquia={"valor": 2585.27, "tipo": tipos[1]},
                          o_que_muda=["R$ 239,21 a mais por ano que a opção “Sua renovação”", "Franquia: R$ 2.585,27"])
    m["opcoes"][2].update(franquia={"valor": 5170.54, "tipo": tipos[2]})
    return m


def _linha_da_franquia(doc: str) -> str:
    m = re.search(r'<div class="row"><h4>Franquia</h4>(.*?)</div></div>', doc, re.S)
    assert m, "a linha da franquia sumiu do comparar"
    return texto_visivel(m.group(1))


def test_ka6_a_franquia_uma_vez_por_cartao_e_o_tipo_so_quando_muda():
    doc = PH.render_proposta(_renovacao_com_as_franquias())
    for c in _cartoes(doc):
        assert len(re.findall(r"[Ff]ranquia:?\s+R\$", texto_visivel(c))) == 1, texto_visivel(c)[:300]
    vis = _linha_da_franquia(doc)
    assert "reduzida" not in vis.lower() and "R$ 5.171" in vis and "5.170,54" not in vis, vis
    # CONTROLE: tipos diferentes → o tipo aparece (é a diferença)
    vis2 = _linha_da_franquia(PH.render_proposta(_renovacao_com_as_franquias(("Reduzida", "Normal", "Reduzida"))))
    assert "normal" in vis2.lower() and "reduzida" in vis2.lower(), vis2


def test_ka7_cada_foto_diz_a_sua_posicao_e_a_moldura_nao_corta_a_etiqueta():
    vis = texto_visivel(_bloco(PV.render_cotacao(venda())))
    assert all(f"Foto {i} de 4" in vis for i in range(1, 5)), vis[-400:]
    um = texto_visivel(_bloco(PV.render_cotacao(venda(fotos=FOTOS[:1]))))
    assert "Foto 1 de 1" not in um                                         # uma foto só não precisa de contador
    css = BC.CSS_DO_BLOCO_DA_CORRETORA
    # as ilustrações do exemplo são 960×640 (3:2): numa moldura 4:3 o `cover` cortava 53 px de cada lado e empurrava a
    # etiqueta "EXEMPLO" para o canto arredondado — a moldura é 3:2
    assert re.search(r"\.bc-foto img\{[^}]*aspect-ratio:3/2", css), "a moldura voltou a cortar as laterais"


def test_ka8_a_capa_e_da_cor_da_marca_e_o_cartao_magro_tem_um_fato():
    css = BC.CSS_DO_BLOCO_DA_CORRETORA
    capa = re.search(r"\.bc-capa\{[^}]*\}", css).group(0)
    assert "--bc-acento" not in capa and "var(--bc-marca)" in capa, capa   # marca + acento virava marrom/oliva
    # o cartão magro (sem cidade, sem ano, sem Google, sem diferenciais) ganha um fato de verdade: a SUSEP
    m = venda(rica=False, desde=None, google=None, cidade=None, selo="Corretora Nível 5")
    m["venda"] = {}
    vis = texto_visivel(_bloco(PV.render_cotacao(m)))
    assert "SUSEP 202031234" in vis, vis[:400]                  # §9.3 (K2): o rótulo junto do número
    m["anfitria"]["susep"] = None
    assert "site da corretora" in texto_visivel(_bloco(PV.render_cotacao(m)))
    # CONTROLE: a renovação com cidade, o cartão de antes (a SUSEP mora no topo — laudo 132-B D6). §9.3 (K2): a venda
    # passou a mostrar a SUSEP sempre (como o QCM) — o controle migrou para a renovação
    com_cidade = renovacao(rica=False, desde=None, google=None)
    assert "202031234" not in texto_visivel(_bloco(PH.render_proposta(com_cidade)))
    # o site do canal ocupa a linha inteira (não quebra deixando um buraco)
    assert re.search(r'<li class="bc-largo"><a href="https://', _bloco(PC.render_proposta_do_canal(canal())))


# =====================================================================================================================
# CONSERTO K2 (laudo do juiz de design R2, 17/10) — cada guarda com a sua LINHA DE CONTROLE (CLAUDE.md §9.3/§9.4)
# =====================================================================================================================
def _vida_pelo_motor(*, renova: bool, cobertura_detalhada: bool = False) -> dict:
    """A página de VIDA com as opções do MOTOR (§9.4): a gravação REAL pelo leitor (`andamento_do_ramo`), a comparação, as
    opções do produto e `opcoes_da_pagina` — os motivos e o "por que" nascem onde nascem no produto. `cobertura_detalhada`
    (o CONTROLE): a seguradora devolve a cobertura de morte detalhada → a página volta a poder falar de cobertura."""
    from datetime import datetime, timezone

    from app.services.multicalculo import comparacao as CMP
    from app.services.multicalculo import config as CFG
    from app.services.multicalculo import proposta as P
    from scripts import publicar_exemplo_da_pagina as EX

    cid, pid = "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222"
    ofertas, eventos, estados = EX.andamento_do_ramo(cid, AP.RAMO_VIDA, pid, datetime(2026, 10, 17, tzinfo=timezone.utc))
    if cobertura_detalhada:
        for o in ofertas:
            o["coberturas"] = dict(o.get("coberturas") or {}, isAppMorte=100000)
    cfg = CMP.config_da_renovacao(CFG.PADRAO_DO_PRODUTO, estados) if renova else CFG.PADRAO_DO_PRODUTO
    quadro = CMP.comparar(ofertas, eventos, estados=estados, config=cfg, ramo=AP.RAMO_VIDA)
    ranking = quadro.ranking(quadro.opcao_completa, cid)
    apolice = {"seguradora": str(ranking[0].get("seguradora_original") or ranking[0]["seguradora"])} if renova else None
    ops = CMP.opcoes(quadro, situacao="renovacao" if renova else "novo_sem_apolice", apolice_atual=apolice, config=cfg,
                     corretora=cid)
    opcoes, _b = P.opcoes_da_pagina(ops, ofertas, cfg, ramo=AP.RAMO_VIDA)
    m = do_ramo(AP.RAMO_VIDA, renova=renova)
    resumo = {k: quadro.resumo[k] for k in ("seguradoras_cotadas", "com_preco_comparavel", "com_produto_diferente",
                                             "nao_responderam")}
    m.update(opcoes=opcoes, resumo=resumo, **P.partes_do_quadro(quadro, ranking))
    m["faq"] = P._faq({}, resumo=resumo, opcoes=opcoes, situacao="novo_sem_apolice", ramo=AP.RAMO_VIDA) if not renova \
        else P.faq_da_renovacao(ramo=AP.RAMO_VIDA, opcoes=opcoes)
    return m


@pytest.mark.parametrize("renova", [False, True], ids=["venda", "renovacao"])
def test_k2_1_vida_sem_cobertura_detalhada_nunca_diz_cobertura_completa(renova):
    m = _vida_pelo_motor(renova=renova)
    assert AP.vida_sem_coberturas(m), "a gravação real de vida deveria vir SEM cobertura detalhada (📊 canário 16/10)"
    doc = (PH.render_proposta if renova else PV.render_cotacao)(m)
    assert "cobertura completa" not in doc.lower(), [x for x in re.findall(r"[^.<>]{0,60}cobertura completa[^.<>]{0,30}",
                                                                         texto_visivel(doc), re.I)]
    assert "cobertura completa" not in json.dumps(m["faq"], ensure_ascii=False).lower()
    vis = texto_visivel(doc)
    assert re.search(r"Capital de R\$\s100\.000\s*para quem você indicar", vis), vis[:900]
    assert re.search(r'<h2 id="h-op">O que você (contrata|renova)</h2>', doc) and "O que está coberto" not in vis
    assert ("A mesma seguradora de hoje, com o capital de R$ 100.000" if renova
            else "A única que devolveu preço para o capital que você pediu") in vis, vis[:1200]
    if not renova:
        assert "pesa preço." in vis and "pesa preço e coberturas" not in vis
        assert "Cotamos em 7 seguradoras para você — 1 devolveu preço." in vis
    # CONTROLE: a MESMA gravação com a cobertura de morte detalhada → o guarda consegue ficar vermelho
    controle = (PH.render_proposta if renova else PV.render_cotacao)(_vida_pelo_motor(renova=renova,
                                                                                      cobertura_detalhada=True))
    assert "cobertura completa" in controle.lower(), "controle: com cobertura detalhada a frase de antes volta"


def test_k2_1_a_regra_de_sem_detalhe_e_o_marcador_do_leitor():
    from portal_worker.multicalculo.leitor_agger import CAPITAL_PEDIDO

    assert AP.CAPITAL_PEDIDO == CAPITAL_PEDIDO
    so_capital = [{"coberturas": [{"chave": CAPITAL_PEDIDO, "valor": "100000"}]}]
    assert AP.sem_cobertura_detalhada(so_capital)
    assert AP.sem_cobertura_detalhada([{"coberturas": [{"chave": "isAppMorte", "valor": "0"}]}])   # zero = não tem
    assert not AP.sem_cobertura_detalhada([{"coberturas": [{"chave": "isAppMorte", "valor": "100000"}]}])
    assert not AP.sem_cobertura_detalhada([])


def test_k2_2_renovacao_o_preco_vence_antes_do_seguro():
    m = renovacao()
    m.update(validade_ate="2026-10-15")
    m["renovacao"]["vence_em"] = "2026-10-20"
    vis = texto_visivel(PH.render_proposta(m))
    assert "Renove até 15/10 e garanta este preço — o seu seguro vale até 20/10" in vis, vis[:700]
    assert vis.count("vence em") == 1                       # o vencimento por extenso é um só (o título)
    assert "Renovando até 20/10" not in vis
    # CONTROLE: o preço vale até depois do vencimento → a frase de sempre
    m.update(validade_ate="2026-10-25")
    vis2 = texto_visivel(PH.render_proposta(m))
    assert "Renovando até 20/10, o seu seguro continua sem um dia descoberto" in vis2 and "Renove até" not in vis2


def _linha(doc: str, rotulo: str) -> str:
    m = re.search(rf'<div class="row"><h4>{re.escape(rotulo)}</h4>(.*?)</div></div>', doc, re.S)
    return m.group(1) if m else ""


def test_k2_3_comparar_preco_rotulado_e_nota_so_quando_difere():
    m = renovacao()
    for o in m["opcoes"]:
        o["nota"] = 91
    doc = PH.render_proposta(m)
    preco = _linha(doc, "Preço por ano")
    assert preco.startswith('<div class="cols"><div class="cell"><b>R$'), preco[:120]   # rótulo + o valor da 1ª coluna
    assert "Nota, de 0 a 100" not in doc                                             # 91 · 91 · 91 não diz nada
    # CONTROLE: notas diferentes → a linha volta (e a carteira, sem `cliente`, nunca muda — test_a_carteira_e_byte_a_byte)
    m["opcoes"][1]["nota"] = 80
    assert "Nota, de 0 a 100" in PH.render_proposta(m)


def test_k2_4_re_a_basica_primeiro_e_a_assistencia_por_ultimo():
    from app.services.multicalculo import comparacao as CMP
    from app.services.multicalculo.pedido import CHAVE_DA_BASICA

    assert AP.CHAVE_DA_BASICA_RE == CHAVE_DA_BASICA and set(AP.ORDEM_DO_RE_POR_ULTIMO) <= set(CMP.NOME_DA_COBERTURA_RE)
    m = do_ramo(16)
    for o in m["opcoes"]:                                   # 📊 a ordem que o motor deu ao condomínio de exemplo (16/10)
        o["coberturas"] = ([{"chave": "assist24hs", "nome": "Assistência", "valor": "Assistência Condomínio"},
                            {"chave": "valorDeNovo", "nome": "valorDeNovo", "valor": "1"}] + o["coberturas"])
    m["opcoes"][1]["coberturas"][0] = dict(m["opcoes"][1]["coberturas"][0], valor="Contratada")
    doc = PV.render_cotacao(m)
    lis = [texto_visivel(x) for x in re.findall(r"<li>.*?</li>",
                                                re.search(r'<ul class="covs">.*?</ul>', _cartoes(doc)[0], re.S).group(0))]
    assert lis[0].startswith("Básica (incêndio, raio e explosão)"), lis
    assert lis[-1].startswith("Assistência"), lis
    cmp_ = doc[doc.find('id="comparar"'):]
    assert cmp_.find("Básica (incêndio") < cmp_.find("Danos elétricos") < cmp_.find(">Assistência<")
    # CONTROLE: o auto não é reordenado (o mesmo objeto volta)
    a = venda()
    assert AP.coberturas_para_o_cliente(a["opcoes"], a) is a["opcoes"]


def test_k2_5_a_susep_com_o_rotulo_e_no_cartao_da_venda():
    magro = venda(rica=False, desde=None, google=None, cidade=None, selo="Corretora Nível 5")
    magro["venda"] = {}
    for doc in (PV.render_cotacao(magro), PV.render_cotacao(venda()), PC.render_proposta_do_canal(canal())):
        vis = texto_visivel(_bloco(doc))
        assert "SUSEP 202031234" in vis and "registro na SUSEP" not in vis, vis[:500]
    # CONTROLE: a renovação com cidade não repete a SUSEP no cartão (ela mora no topo — laudo 132-B D6)
    assert "202031234" not in texto_visivel(_bloco(PH.render_proposta(renovacao())))


@pytest.mark.parametrize("cadastro", ["SUSEP 202031234", "SUSEP nº: 202031234", "susep n° 202031234",
                                      "SUSEP no. 202031234", "SUSEP#202031234", "202031234"])
def test_k2_7_o_numero_do_compromisso_e_o_que_o_topo_mostra(cadastro):
    doc = PV.render_cotacao(venda(susep=cadastro))
    topo = re.search(r'<p class="cred">.*?SUSEP nº ([^<]+)</b>', doc, re.S).group(1)
    cartao = re.search(r'<span class="bc-num">([^<]+)</span>', _bloco(doc)).group(1)
    assert topo == cartao == AP.susep_limpa({"susep": cadastro}) == "202031234", (topo, cartao)
    assert "o número está no topo desta página" in texto_visivel(_bloco(doc))
    # o canal: o cartão e o rodapé com o MESMO número
    c = PC.render_proposta_do_canal(canal(susep=cadastro))
    assert "SUSEP 202031234" in texto_visivel(_bloco(c)) and "sob o nº 202031234" in texto_visivel(c)
    # CONTROLE: as duas regras de ANTES divergiam (📊 17/10, `git show 8e6c930`): o recorte do cartão deixava "o. " em
    # "SUSEP no. 202031234" enquanto o do topo dava "202031234" — o guarda acima pega essa divergência
    antes_cartao = re.sub(r"^\s*susep\b[\s:nº°.#-]*", "", "SUSEP no. 202031234", flags=re.I).strip()
    antes_topo = re.sub(r"(?i)^\s*susep\s*(?:n\s*[º°o.]*\s*)?[:\-]?\s*", "", "SUSEP no. 202031234").strip()
    assert antes_cartao != antes_topo == "202031234"


def test_k2_6_se_acontecer_numerado_como_no_qcm():
    doc = PV.render_cotacao(venda())
    sec = re.search(r'<section class="s" aria-labelledby="h-sin">.*?</section>', doc, re.S).group(0)
    passos = [s for s in CONTRATO.get("sinistro") or [] if isinstance(s, str) and s.strip()]
    assert '<ol class="steps">' in sec and sec.count("<li>") == len(passos) >= 2 and "<ul>" not in sec, sec[:400]
