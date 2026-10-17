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
    assert all(a in vis for a, _b in BC.CRITERIOS_DO_NIVEL_5) and "versão 1" in vis
    assert vis.count("Foto ") == 0 and len(re.findall(r'<figure class="bc-foto"', bloco)) == 4
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
    assert "202031234" in c and "202031234" not in v and "202031234" not in r     # a SUSEP no topo da venda/renovação
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
    assert 'class="bc-fatos"' not in bloco and 'class="bc-fotos' not in bloco and "no mercado" not in vis
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
    assert "Renovando até 20/10, o seu seguro continua sem um dia descoberto" in vis
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
