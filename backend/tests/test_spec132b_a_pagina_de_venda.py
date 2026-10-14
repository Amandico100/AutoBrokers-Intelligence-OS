# -*- coding: utf-8 -*-
"""SPEC-132-B · B2 — a página de COTAÇÃO = a página de VENDA da corretora (D-132B-01/02/05/08), sobre o HTML SERVIDO.

🔴 A lição da 130-A vale aqui: o guarda lê o que `abrir_compartilhado` serve (o que o `route.ts` devolve) — nunca só o
modelo. As mutações da SPEC que estes guardas fecham:

    (4) a página da corretora mostra o canal comparador / o selo do programa / duelo   → test_mutacao_4_*
    (5) número sem prova: economia sem apólice, "N anos" sem founded_year, nota sem a ficha → test_mutacao_5_*
    + os guardas de HONESTIDADE da 130-A que valem para QUALQUER página do cliente (a melhor das N, sem WhatsApp
      nenhuma promessa de WhatsApp, economia só com apólice, sem JS, preço vencido, impressão)
    + a renovação, o canal e a carteira NÃO mudaram (o HTML byte a byte, contra o retrato tirado ANTES desta fatia)

Bordas: o banco (o PostgREST em memória da 129-B). Porta, comparação, Hub, marca e config são REAIS (CLAUDE.md §9.4).
⛔ Nomes fictícios (CLAUDE.md §13.9). Rodar:
    cd backend && .venv/Scripts/python.exe -m pytest tests/test_spec132b_a_pagina_de_venda.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
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

from app.services.artifacts import proposta_cotacao_html as PV  # noqa: E402
from app.services.artifacts import proposta_html as PH  # noqa: E402
from app.services.artifacts.proposta_canal_html import render_proposta_do_canal  # noqa: E402
from app.services.artifacts.service import ArtifactService  # noqa: E402
from app.services.multicalculo import NaoEncontrado  # noqa: E402
from app.services.multicalculo import config as CFG  # noqa: E402
from app.services.multicalculo import proposta as P  # noqa: E402
from app.services.multicalculo.mensagem import (FRASES_PROIBIDAS, TETO_DE_CARACTERES,  # noqa: E402
                                                TETO_DO_TEXTO_CURTO, mensagem_de_cotacao)
from dubles import mundo_da_proposta as M  # noqa: E402
from test_spec130a_o_fio import CHROME, ordem_das_opcoes, texto_visivel  # noqa: E402

BASE = "https://app.exemplo.test"
TABELAS_DO_HUB = ("artifacts", "artifact_versions", "artifact_renders", "artifact_shares", "artifact_events")
CONTRATO = json.loads((BACKEND / "tests" / "fixtures" / "proposta" / "modelo_contrato.json").read_text(encoding="utf-8"))

CORRETOR = "c0c00000-0000-4000-8000-00000000c132"        # quem cotou (membro da corretora beta)
WHATS_CORRETOR = "5548988881320"                         # o "Meu WhatsApp de trabalho" dele
WHATS_CORRETORA = "5548999990099"                        # o WhatsApp da marca PUBLICADA da beta (o dublê)
APOLICE_CARA = {"seguradora": "Porto", "premio_anual": 9000.0}

#: 🔴 o retrato tirado ANTES desta fatia (14/10/2026, `scratchpad/hashes_antes.py`, sha256 do HTML de cada página para
#: os modelos de `_modelos_de_referencia`). Mudou por verdade nova (uma decisão que muda ESTAS páginas)? Regere com o
#: mesmo cálculo e escreva aqui por quê — nunca por um efeito colateral da página de venda (D-131-42: copy nunca cruzada).
RETRATO_ANTES = {
    "carteira": "56d8c9e5469dc837fa11cf95379f2e1237818f3ab7293cce73f86166d2aeac96",
    "renovacao": "4dabd326d4c35a7bb74c4e6117612cf54d4f934a56e792529190e46171473986",
    "canal": "d5c72d4bffe4373d1e7c481081cd6c1bfb1789bf7f41565c09d77013b816a787",
}


# =====================================================================================================================
# o mundo
# =====================================================================================================================
def mundo(monkeypatch, *, corretor_confirmado=True, corretor_com_numero=True, sem_numero_da_corretora=False,
          marca_publicada=True, fundada=None, diferenciais=None, google=None):
    """O pedido do canário (a parte da corretora beta) pedido pela própria beta, com a marca dela PUBLICADA (no retrato
    de produção 📊 14/10 as corretoras-piloto estão publicadas) e o corretor que cotou na equipe."""
    monkeypatch.setenv("PUBLIC_APP_URL", BASE)
    m = M.montar_mundo(monkeypatch, solicitante="beta")
    ped = next(p for p in m.banco.linhas("multicalculo_pedidos") if p["id"] == m.pedido_id)
    ped["servico"] = "cotacao"
    for b in m.banco.linhas("brand_profiles"):
        if b["company_id"] == m.beta:
            b["is_published"] = marca_publicada
            b["founded_year"] = fundada
            b["differentiators"] = list(diferenciais or [])
            b["insurers"] = ["Porto", "Allianz", "Tokio", "Bradesco", "HDI"]
            b["about_md"] = "Corretora de bairro. Atendemos pessoas, com calma."
            b["susep_code"] = "SUSEP 10.2030405"
            if sem_numero_da_corretora:
                b["contact"] = {}
    if sem_numero_da_corretora:
        for i in m.banco.linhas("integrations"):
            if i["company_id"] == m.beta and i["purpose"] == "attendance":
                i["is_active"] = False
    if google:
        m.banco.semear("multicalculo_config", {"company_id": m.beta, "config": {"google_confirmado": google}})
    m.banco.semear("users_v2", {"id": CORRETOR, "first_name": "Caio Ficticio"})
    m.banco.semear("company_members", {
        "user_id": CORRETOR, "company_id": m.beta, "status": "active",
        "whatsapp_trabalho_e164": ("+" + WHATS_CORRETOR) if corretor_com_numero else None,
        "whatsapp_trabalho_confirmado_em": "2026-10-12T10:00:00+00:00" if corretor_confirmado else None})
    return m


def _publicar(m, company_id=None, **kw):
    kw.setdefault("primeiro_nome", "Ana")
    return asyncio.run(P.publicar_cotacao(company_id or m.beta, m.pedido_id, pessoa_user_id=CORRETOR, db=m.db,
                                          base_url=BASE, **kw))


def _servido(m, token):
    s = ArtifactService(m.banco.visao("rota-publica")).abrir_compartilhado(token, user_agent=CHROME)
    assert s, "o link não abriu"
    return s["html"]


def _h1(doc):
    return texto_visivel(re.search(r"<h1>(.*?)</h1>", doc, re.S).group(1))


def _dock(doc):
    m = re.search(r'<div class="dock">(.*?)</div><p class="dock-note">', doc, re.S)
    return m.group(1) if m else ""


def _venda(modelo=None, **extra):
    """O modelo do CONTRATO como a página de venda o recebe (para os guardas de desenho que não precisam do banco)."""
    m = copy.deepcopy(modelo or CONTRATO)
    m.update({"pagina": "venda", "situacao": m.get("situacao") or "novo_sem_apolice"})
    m.update(extra)
    return m


#: a página da corretora NUNCA fala do canal comparador nem do programa dele (mutação 4). Os nomes vêm da CONFIG do
#: produto (é dela que a página do canal os lê) + os textos fixos do canal; nada aqui é nome de corretora.
def _marcas_do_canal():
    canal = CFG.PADRAO_DO_PRODUTO["canal"]
    return [canal["nome"], canal["selo"]["nome"], "Nível 5", "Comparação independente", "Comparador independente",
            "comparador", "corretoras parceiras", "Outra corretora parceira", "a melhor das", "Quero renovar"]


def vazamentos_da_marca_isenta(doc):
    txt = texto_visivel(doc).lower()
    achados = [f for f in _marcas_do_canal() if f.lower() in txt]
    if 'class="duel' in doc or 'class="regua' in doc or 'class="rank"' in doc:
        achados.append("duelo/ranking")
    return achados


# =====================================================================================================================
# 1. a página servida, na ordem do §4
# =====================================================================================================================
_ORDEM = ['<header class="wrap vtop">', "<h1>", 'id="h-oferta"', 'id="h-op"', 'id="track"', 'id="comparar"', 'id="h-pq"',
          'id="h-host"', 'id="h-depois"', 'id="h-sin"', 'id="h-faq"', 'id="h-fim"', 'class="legal"', 'class="dock"']


def test_a_pagina_servida_de_venda_na_ordem(monkeypatch):
    m = mundo(monkeypatch, fundada=2011, diferenciais=["Atendimento por pessoas, do orçamento ao sinistro"])
    r = _publicar(m)
    assert r["url"] == f"{BASE}/r/{r['token']}"
    doc = _servido(m, r["token"])
    txt = texto_visivel(doc)
    pos = [doc.find(x) for x in _ORDEM]
    assert all(p >= 0 for p in pos), [x for x, p in zip(_ORDEM, pos) if p < 0]
    assert pos == sorted(pos), "os blocos fora da ordem do §4"
    assert re.fullmatch(r"Ana, a cotação do seu \S+ está pronta", _h1(doc)), _h1(doc)
    conta = PH._conta_do_resumo(r["modelo"])
    assert f"Comparamos {conta['cotadas']} seguradoras para você — sem custo e sem compromisso." in txt
    assert "Corretora de seguros" in txt and "SUSEP nº 10.2030405" in txt
    # as 3 opções, a recomendada primeiro (o "Quero esta" de cada cartão e o fechar do topo)
    ids = ordem_das_opcoes(doc)
    assert ids[0] == "recomendada" and len(ids) == len(r["modelo"]["opcoes"]) <= 3
    assert "Comparar coberturas" in txt and "Por que recomendamos" in txt and "Nossa recomendação" in txt
    # por que fechar com a corretora: fatos do banco (anos SÓ com founded_year; parceiras = `insurers`)
    assert "Por que fechar com a " in txt and "15 anos" in txt and "desde 2011" in txt
    assert "5 seguradoras parceiras da corretora" in txt
    assert "Atendimento por pessoas, do orçamento ao sinistro" in txt and "representa você" in txt
    assert "Como funciona depois do sim" in txt and "A apólice chega no seu e-mail" in txt
    for p in ("Por que fechar com uma corretora?", "E se eu bater o carro?", "O preço pode mudar?", "Como eu pago?",
              "Posso cancelar depois?", "Preciso fazer vistoria?", "Os meus dados estão seguros?"):
        assert p in txt, p
    assert f"valem até {PH.AP.data_br(r['modelo']['validade_ate'])}" in txt        # a data REAL, nunca "{validade}"
    assert "{validade}" not in doc and "{corretora}" not in doc
    assert "Nada é cobrado agora." in txt and "Tirar uma dúvida" in txt and "Quero fechar" in txt
    assert "Exemplo — dados fictícios" not in txt                                   # D-132B-08: só nos exemplos
    # o mesmo script (o hash da CSP do `/r/` é o da constante) e nada de comissão
    assert f"<script>{PH.SCRIPT_DA_PROPOSTA}</script>" in doc and doc.count("<script>") == 1
    assert "17,37" not in doc and "17.37" not in doc
    assert re.search(r'og:title" content="A cotação do seu seguro: [^"]+x de R\$', doc)
    # o Hub: a peça é da beta, marcada como venda
    art = m.banco.linhas("artifacts")
    assert len(art) == 1 and art[0]["company_id"] == m.beta
    assert art[0]["subject_ref"]["pagina"] == "venda" and art[0]["subject_ref"]["publicada_por"] == CORRETOR
    # §9.3 (SPEC-132-B B4, pedido da B3): publicar de novo a MESMA página devolve o MESMO link (nada é gravado — o
    # "Ver apresentação" não versiona a cada clique); com a página DIFERENTE = versão nova da MESMA peça
    de_novo = _publicar(m)
    assert (de_novo["versao"], de_novo["token"], de_novo["url"]) == (r["versao"], r["token"], r["url"])
    assert len(m.banco.linhas("artifact_versions")) == 1 and len(m.banco.linhas("artifact_shares")) == 1
    outra = _publicar(m, primeiro_nome="Bia")
    assert outra["versao"] == 2 and outra["token"] != r["token"] and len(m.banco.linhas("artifacts")) == 1


def test_o_resumo_para_o_chat_tem_a_mesma_parcela_da_pagina(monkeypatch):
    m = mundo(monkeypatch)
    r = _publicar(m)
    doc = _servido(m, r["token"])
    res = r["resumo"]
    assert [o["id"] for o in res["opcoes"]] == ordem_das_opcoes(doc)
    rec = res["opcoes"][0]
    assert rec["papel"] == "Recomendada" and rec["a_vista"] and rec["parcela"]["vezes"] > 1
    parcela = f"{rec['parcela']['vezes']}x de {PH._brl(rec['parcela']['valor'])}"
    assert parcela in _dock(doc).replace("\xa0", " ")                    # UMA parcela por opção, a mesma em todo lugar
    assert res["seguradoras_cotadas"] == PH._conta_do_resumo(r["modelo"])["cotadas"]
    assert "comiss" not in json.dumps(res).lower()


# =====================================================================================================================
# 2. mutação 4 — a página da CORRETORA não é a do canal
# =====================================================================================================================
def test_mutacao_4_a_pagina_de_venda_nao_fala_do_canal(monkeypatch):
    m = mundo(monkeypatch)
    doc = _servido(m, _publicar(m)["token"])
    assert vazamentos_da_marca_isenta(doc) == []
    # CONTROLE: o guarda FICA VERMELHO na página do canal (o mesmo contrato) e com o duelo reintroduzido
    assert vazamentos_da_marca_isenta(render_proposta_do_canal(dict(copy.deepcopy(CONTRATO), origem="canal")))
    assert vazamentos_da_marca_isenta(doc.replace("</main>", '<div class="duel">x</div></main>'))
    assert vazamentos_da_marca_isenta(doc.replace("</main>", f"<p>{CFG.PADRAO_DO_PRODUTO['canal']['nome']}</p></main>"))


# =====================================================================================================================
# 3. mutação 5 — bloco sem dado SOME (nunca um número sem prova)
# =====================================================================================================================
def test_mutacao_5_sem_dado_o_bloco_some(monkeypatch):
    m = mundo(monkeypatch)                     # sem founded_year, sem diferenciais, sem a ficha do Google, sem apólice
    doc = _servido(m, _publicar(m)["token"])
    txt = texto_visivel(doc)
    assert "no mercado" not in txt and "desde " not in txt
    assert "no Google" not in txt and 'id="h-eco"' not in doc     # ("a menos por ano" existe no COMPARAR, à parte)
    assert 'class="difs"' not in doc
    # CONTROLE: com cada dado, o bloco aparece (o guarda consegue falhar)
    m2 = mundo(monkeypatch, fundada=2011, diferenciais=["Revisamos o seu seguro todo ano"],
               google={"nota": 4.8, "avaliacoes": 21, "data": "10/10/2026", "fonte": "Google, ficha confirmada"})
    d2 = _servido(m2, _publicar(m2, apolice_atual=APOLICE_CARA)["token"])
    t2 = texto_visivel(d2)
    assert "no mercado, desde 2011" in t2 and "no Google, 21 avaliações" in t2 and "4,8" in t2
    assert "Revisamos o seu seguro todo ano" in t2 and 'id="h-eco"' in d2


def test_economia_so_com_a_apolice_e_nunca_um_aumento(monkeypatch):
    m = mundo(monkeypatch)
    r = _publicar(m, apolice_atual=APOLICE_CARA)
    doc = _servido(m, r["token"])
    rec = r["modelo"]["opcoes"][0]
    menos = texto_visivel(PH.AP.brl(9000.0 - rec["premio_anual"], False))
    eco = texto_visivel(re.search(r'<section class="eco".*?</section>', doc, re.S).group(0))
    assert eco.startswith(f"{menos} a menos por ano") and "R$ 9.000 por ano" in eco and "“Recomendada”" in eco
    # a apólice MAIS BARATA que a recomendada: nenhuma "economia" (um aumento nunca é vantagem)
    m2 = mundo(monkeypatch)
    doc2 = _servido(m2, _publicar(m2, apolice_atual={"seguradora": "Porto", "premio_anual": 1500.0})["token"])
    assert 'class="eco' not in doc2 and 'id="h-eco"' not in doc2
    # o modelo SEM apólice com uma "economia contra o maior preço" (a da carteira): a página não a mostra
    sem = _venda()
    sem["resumo"]["economia"] = {"ate": 4291.84, "de": 8460.29, "para": 4168.45, "contra": "maior"}
    assert 'id="h-eco"' not in PV.render_cotacao(sem)
    assert 'id="h-eco"' not in PV.render_cotacao(dict(sem, situacao="novo_com_apolice"))
    # CONTROLE: a mesma conta CONTRA o preço atual, com a apólice, aparece
    sem["resumo"]["economia"]["contra"] = "atual"
    assert 'id="h-eco"' in PV.render_cotacao(dict(sem, situacao="novo_com_apolice"))


# =====================================================================================================================
# 4. os guardas de honestidade da 130-A, agora na página de venda
# =====================================================================================================================
def test_recomendacao_so_para_a_1a_do_ranking():
    doc = PV.render_cotacao(_venda())
    assert "Nossa recomendação" in texto_visivel(doc) and "Por que recomendamos" in texto_visivel(doc)
    sem_a_1a = _venda()
    sem_a_1a["opcoes"] = [o for o in sem_a_1a["opcoes"] if o["id"] != "recomendada"]
    txt = texto_visivel(PV.render_cotacao(sem_a_1a))
    assert "Nossa recomendação" not in txt and "Por que recomendamos" not in txt and "Sobre esta opção" in txt
    assert "a melhor das" not in txt and "a melhor opção" not in txt


def test_quero_fechar_vai_ao_corretor_com_whatsapp_confirmado(monkeypatch):
    m = mundo(monkeypatch)
    r = _publicar(m)
    doc = _servido(m, r["token"])
    assert f"https://wa.me/{WHATS_CORRETOR}?text=" in _dock(doc) and WHATS_CORRETORA not in doc
    assert "Abre o WhatsApp com Caio." in texto_visivel(doc) and "Caio Ficticio" not in texto_visivel(doc)
    assert "Quem vai cuidar de você" in texto_visivel(doc) and "Falar com Caio" in texto_visivel(doc)
    for o in r["modelo"]["opcoes"]:              # o redirecionamento do `?fechar=` (o que o route.ts usa)
        d = PH.destino_do_fechar(r["modelo"], o["id"])
        assert d["destino"].startswith(f"https://wa.me/{WHATS_CORRETOR}?text=") and "Quero%20fechar" in d["destino"]
    assert r["modelo"]["venda"]["fechar_com"] == "corretor"


@pytest.mark.parametrize("caso", ["nao_confirmado", "sem_numero"])
def test_sem_corretor_confirmado_vai_a_corretora(monkeypatch, caso):
    m = mundo(monkeypatch, corretor_confirmado=caso != "nao_confirmado", corretor_com_numero=caso != "sem_numero")
    r = _publicar(m)
    doc = _servido(m, r["token"])
    assert f"wa.me/{WHATS_CORRETORA}?text=" in _dock(doc) and WHATS_CORRETOR not in doc
    assert r["modelo"]["venda"]["fechar_com"] == "corretora"


def test_sem_numero_nenhum_publica_sem_botao_e_nao_promete_whatsapp(monkeypatch):
    m = mundo(monkeypatch, corretor_com_numero=False, sem_numero_da_corretora=True)
    r = _publicar(m)                           # NUNCA recusa: o link vai pelo corretor (D-132B-05, D-131-44)
    doc = _servido(m, r["token"])
    txt = texto_visivel(doc)
    assert 'class="dock"' not in doc and "wa.me/" not in doc and "Quero fechar" not in txt and "Quero esta" not in txt
    assert "responda a mensagem em que recebeu este link" in txt and "Nada é cobrado agora." in txt
    assert "whatsapp" not in txt.lower()       # J-B1: nenhuma frase promete o que não existe
    dados = re.search(r'id="ab-dados">(.*?)</script>', doc, re.S).group(1)
    assert "whatsapp" not in dados.lower() and "vencido" not in dados
    assert r["modelo"]["cta"] is None and r["modelo"]["venda"]["fechar_com"] == "nenhum"
    # CONTROLE: com número, a palavra aparece (o guarda consegue falhar)
    m2 = mundo(monkeypatch)
    assert "whatsapp" in texto_visivel(_servido(m2, _publicar(m2)["token"])).lower()


def test_sem_js_a_pagina_funciona_e_o_preco_vencido_tem_o_texto_do_servidor():
    doc = PV.render_cotacao(_venda())
    assert '<html lang="pt-BR" class="no-js">' in doc
    sem_script = re.sub(r"<script\b.*?</script>", "", doc, flags=re.S)
    assert sem_script.count('href="?fechar=') >= len(_venda()["opcoes"]) + 2   # cada cartão + o fecho + a barra
    assert '<details class="cmp" id="comparar"' in doc and "scroll-snap-type" in doc
    assert ".no-js .venda .dock .close{display:flex}" in doc                 # sem JS a barra fica com a RECOMENDADA
    sub = re.search(r'<span id="close-sub">([^<]*)</span>', doc).group(1)
    assert sub.endswith(_venda()["opcoes"][0]["seguradora"]) and re.match(r"\d+x de R\$", sub)   # a parcela primeiro
    dados = json.loads(re.search(r'id="ab-dados">(.*?)</script>', doc, re.S).group(1))
    assert dados["vencido"]["botao"] == "Pedir preço atualizado" and dados["vencido"]["ate"] == CONTRATO["validade_ate"]
    assert "@media print" in doc


def test_nenhum_cpf_nem_telefone_do_cliente_no_html(monkeypatch):
    m = mundo(monkeypatch)
    r = _publicar(m)
    doc = _servido(m, r["token"])
    cpf = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
    assert not cpf.search(texto_visivel(doc))
    telefones = set(re.findall(r"(?<![\d.])\d{10,13}(?![\d.])", re.sub(r"<style\b.*?</style>", "", doc, flags=re.S)))
    assert telefones <= {WHATS_CORRETOR}, telefones                          # só o número de TRABALHO do corretor
    # CONTROLE: um CPF que chegasse ao modelo seria pego
    vaz = _venda(cliente={"primeiro_nome": "Ana 123.456.789-00"})
    assert cpf.search(texto_visivel(PV.render_cotacao(vaz)))


def test_duas_corretoras_duas_caras_e_outra_corretora_nao_le_o_pedido(monkeypatch):
    a = _venda()
    b = _venda()
    b["anfitria"] = dict(b["anfitria"], nome="Vega Corretora Ficticia",
                         tema_claro=M._paleta("#2E7D32", "#F9A825")["themes"]["light"],
                         tema_escuro=M._paleta("#2E7D32", "#F9A825")["themes"]["dark"])
    ta, tb = PV.render_cotacao(a), PV.render_cotacao(b)
    cor = lambda d: re.findall(r"--p:(#[0-9A-Fa-f]{6})", d)   # noqa: E731 — o neutro da base + o tema da marca
    assert cor(ta) != cor(tb)
    assert "Vega Corretora Ficticia" in texto_visivel(tb) and "Vega Corretora Ficticia" not in texto_visivel(ta)
    # 🔴 CLAUDE.md §7: a alfa não publica o pedido da beta — e nada é gravado
    m = mundo(monkeypatch)
    with pytest.raises(NaoEncontrado):
        _publicar(m, company_id=m.alfa)
    assert all(m.banco.linhas(t) == [] for t in TABELAS_DO_HUB)


def test_marca_nao_publicada_nao_vira_fato(monkeypatch):
    m = mundo(monkeypatch, marca_publicada=False, fundada=2011, diferenciais=["Diferencial de rascunho"])
    txt = texto_visivel(_servido(m, _publicar(m)["token"]))
    assert "Diferencial de rascunho" not in txt and "desde 2011" not in txt and "seguradoras parceiras" not in txt


def test_a_faixa_de_exemplo_so_com_a_bandeira(monkeypatch):
    assert "Exemplo — dados fictícios" in texto_visivel(PV.render_cotacao(_venda(exemplo=True)))
    assert "Exemplo — dados fictícios" not in texto_visivel(PV.render_cotacao(_venda()))
    m = mundo(monkeypatch)
    assert "Exemplo — dados fictícios" in texto_visivel(_servido(m, _publicar(m, exemplo=True)["token"]))


# =====================================================================================================================
# 5. a carteira, a renovação e o canal NÃO mudaram (byte a byte) — e quem vai para a venda
# =====================================================================================================================
def _modelos_de_referencia():
    ren = dict(copy.deepcopy(CONTRATO), situacao="renovacao")
    ren["opcoes"][0] = dict(ren["opcoes"][0], id="sua_renovacao", rotulo="Sua renovação",
                            por_que="A mesma seguradora de hoje.")
    ren["renovacao"] = {"vence_em": "2026-10-20", "seguradora_atual": "Bradesco", "premio_atual": 4500.0, "anos": 3,
                        "dono": {"primeiro_nome": "Bruna", "whatsapp": "5548988880001"}}
    return {"carteira": (PH.render_proposta, copy.deepcopy(CONTRATO)),
            "renovacao": (PH.render_proposta, ren),
            "canal": (render_proposta_do_canal, dict(copy.deepcopy(CONTRATO), origem="canal"))}


@pytest.mark.parametrize("pagina", sorted(RETRATO_ANTES))
def test_as_outras_paginas_nao_mudaram_byte_a_byte(pagina):
    render, modelo = _modelos_de_referencia()[pagina]
    assert hashlib.sha256(render(modelo).encode("utf-8")).hexdigest() == RETRATO_ANTES[pagina]


def test_quem_vai_para_a_pagina_de_venda():
    assert PV.e_venda(_venda()) and PV.e_venda(_venda(pagina=None, servico="cotacao"))
    assert not PV.e_venda(copy.deepcopy(CONTRATO))                     # o comando antigo (sem marcador): a carteira
    assert not PV.e_venda(_venda(origem="canal"))                      # o canal nunca
    assert not PV.e_venda(_venda(situacao="renovacao"))                # a renovação tem a página dela
    assert 'class="venda"' in PH.render_proposta(_venda())             # o desvio passa pelo gancho único do template
    assert PH.previa_do_modelo(_venda())["titulo"].startswith("A cotação do seu seguro")
    for chave in ("titulo", "descricao", "manchete", "seguradora", "preco", "marca", "logo", "validade"):
        assert chave in PH.previa_do_modelo(_venda())                  # o PNG da prévia lê as mesmas chaves
    prev = json.dumps(PH.previa_do_modelo(_venda()), ensure_ascii=False)
    assert "Mariana" not in prev and "Compass" not in prev             # sem dado pessoal na prévia


# =====================================================================================================================
# 6. a mensagem que o CORRETOR copia
# =====================================================================================================================
def test_a_mensagem_de_cotacao(monkeypatch):
    m = mundo(monkeypatch)
    r = _publicar(m)
    msg = mensagem_de_cotacao(r["modelo"], r["url"])
    assert set(msg) == {"texto", "texto_curto"}
    t, c = msg["texto"], msg["texto_curto"]
    assert t.startswith("Olá, Ana! A cotação do seguro do seu ") and r["url"] in t and r["url"] in c
    assert len(t) <= TETO_DE_CARACTERES and len(c) <= TETO_DO_TEXTO_CURTO
    assert t.index("*Recomendada:*") < t.index("*Mais em conta:*") if "*Mais em conta:*" in t else True
    assert t.rstrip().endswith("Caio · " + r["modelo"]["anfitria"]["nome"])
    rec = r["resumo"]["opcoes"][0]["parcela"]
    assert f"{rec['vezes']}x de {PH._brl(rec['valor'])}" in t                 # a MESMA parcela da página
    baixo = (t + c).lower()
    assert [f for f in FRASES_PROIBIDAS if f in baixo] == []
    assert [f for f in _marcas_do_canal() if f.lower() in baixo] == []
    # o mesmo vindo do que `publicar_cotacao` devolve; e o texto curto cabe com link e nomes compridos
    assert mensagem_de_cotacao(r, r["url"]) == msg
    longo = copy.deepcopy(r["modelo"])
    longo["anfitria"]["nome"] = "Corretora " + "Muito " * 40 + "Comprida"
    url = r["url"] + "?" + "x" * 380
    m2 = mensagem_de_cotacao(longo, url)
    assert len(m2["texto_curto"]) <= TETO_DO_TEXTO_CURTO and url in m2["texto_curto"]
    assert len(m2["texto"]) <= TETO_DE_CARACTERES + len(url)


# =====================================================================================================================
# 7. a config da cotação: os textos da página e as regras editáveis (D-132B-06)
# =====================================================================================================================
def test_a_config_da_pagina_e_as_regras_editaveis():
    pad = CFG.pagina_da_cotacao(CFG.mesclar(None, "cotacao"))
    assert pad["diferenciais"] == [] and len(pad["faq"]) == 7 and len(pad["depois_do_sim"]) == 3
    proprio = CFG.mesclar({"servicos": {"cotacao": {"pagina": {"diferenciais": ["Atendemos aos sábados"],
                                                                "faq": [{"pergunta": "P?", "resposta": "R."}]}}}},
                          "cotacao")
    pg = CFG.pagina_da_cotacao(proprio)
    assert pg["diferenciais"] == ["Atendemos aos sábados"] and pg["faq"] == [{"pergunta": "P?", "resposta": "R."}]
    assert len(pg["depois_do_sim"]) == 3                                      # a lista que ela não trocou: o padrão
    quebrado = CFG.mesclar({"servicos": {"cotacao": {"pagina": {"faq": [{"pergunta": ""}]}}}}, "cotacao")
    assert len(CFG.pagina_da_cotacao(quebrado)["faq"]) == 7                   # lista quebrada: nunca na página
    # as regras: opções, comissão de ENTRADA e validade
    assert CFG.opcoes_da_cotacao(CFG.mesclar(None, "cotacao")) == ("padrao", "economica", "completa_mais")
    ok = {"cotacao": {"opcoes": ["completa_mais", "padrao"], "comissao": {"entrada": 18}, "validade": {"padrao_dias": 3}}}
    assert CFG.erros_da_edicao(ok) == []
    c = CFG.mesclar({"servicos": ok}, "cotacao")
    assert CFG.opcoes_da_cotacao(c) == ("padrao", "completa_mais") and c["comissao"]["entrada"] == 18
    assert c["validade"]["padrao_dias"] == 3
    assert CFG.mesclar({"servicos": ok}, "renovacao")["comissao"]["entrada"] == 15       # nunca vaza para outro serviço
    for ruim in ({"opcoes": ["minima"]}, {"opcoes": ["economica"]}, {"opcoes": ["padrao", "padrao"]},
                 {"comissao": {"entrada": 5}}, {"comissao": {"entrada": 18, "piso": 1}}, {"comissao": 18},
                 {"validade": {"padrao_dias": 0}}, {"validade": {"padrao_dias": 2.5}}, {"validade": {"por_seguradora": {}}},
                 {"pagina": {"faq": []}}):
        assert CFG.erros_da_edicao({"cotacao": ruim}), ruim


# =====================================================================================================================
# 8. no navegador (Chromium do Playwright, com a CSP do `/r/`): lado a lado, sem JS, preço vencido, impressão, medidas
# =====================================================================================================================
from test_spec130a_conserto import _abrir, navegador  # noqa: E402,F401  (a MESMA CSP e o mesmo Chromium da 130-A)

_MEDIDAS = """() => {
  const fs = [...document.querySelectorAll('body *')].filter(e => e.checkVisibility() && [...e.childNodes]
      .some(n => n.nodeType === 3 && n.textContent.trim())).map(e => parseFloat(getComputedStyle(e).fontSize));
  const pequenos = [...document.querySelectorAll('a,button,summary')].filter(e => e.checkVisibility())
      .map(e => e.getBoundingClientRect()).filter(r => r.width > 0 && r.height < 44).length;
  return {fonte: Math.min(...fs), pequenos, rola: document.documentElement.scrollWidth > innerWidth};
}"""


@pytest.mark.parametrize("largura", [390, 1366])
def test_navegador_medidas_e_a_barra_com_a_recomendada(navegador, largura):
    """≥ 12 px, alvos ≥ 44 px, sem rolagem lateral; e a barra abre com a RECOMENDADA. 📊 a 1ª captura (14/10) mostrou
    no notebook "Quero fechar · Tokio" (a 3ª opção): o script media `offsetLeft` contra a PÁGINA (o trilho não era
    posicionado) e não via os três lado a lado. MUTAÇÃO: sem o `position:relative` do trilho → vermelho em 1366."""
    doc = PV.render_cotacao(_venda(validade_ate="2099-12-31"))
    ctx, pg, erros = _abrir(navegador, doc, largura)
    try:
        med = pg.evaluate(_MEDIDAS)
        assert med["fonte"] >= 12 and med["pequenos"] == 0 and med["rola"] is False, med
        assert pg.evaluate("document.querySelector('#ab-fechar').getAttribute('href')") == "?fechar=recomendada"
        if largura > 1024:
            assert pg.evaluate("document.querySelector('#track').classList.contains('spread')") is True
        assert erros == []
    finally:
        ctx.close()
    mutado = doc.replace(".venda .track{position:relative;", ".venda .track{")
    if largura > 1024:
        assert mutado != doc
        ctx, pg, _ = _abrir(navegador, mutado, largura)
        try:
            assert pg.evaluate("document.querySelector('#track').classList.contains('spread')") is False
        finally:
            ctx.close()


def test_navegador_sem_js_a_barra_fecha_a_recomendada_com_o_nome_dela(navegador):
    ctx, pg, erros = _abrir(navegador, PV.render_cotacao(_venda(validade_ate="2099-12-31")), js=False)
    try:
        assert pg.evaluate("document.querySelector('#ab-fechar').checkVisibility()") is True
        assert pg.evaluate("document.querySelector('#ab-fechar').getAttribute('href')") == "?fechar=recomendada"
        assert "Bradesco" in pg.evaluate("document.querySelector('#close-sub').textContent")
        assert erros == []
    finally:
        ctx.close()


def test_navegador_preco_vencido_vira_pedir_atualizacao_e_impressao(navegador):
    ctx, pg, erros = _abrir(navegador, PV.render_cotacao(_venda(validade_ate="2020-01-10")))
    try:
        assert pg.evaluate("document.querySelector('#ab-fechar b').textContent") == "Pedir preço atualizado"
        assert pg.evaluate("document.querySelector('#ab-fechar').getAttribute('href')").startswith("https://wa.me/")
        assert pg.evaluate("document.querySelector('.oferta .valid').textContent").startswith("Preço vencido em 10/01")
        pg.emulate_media(media="print")
        assert pg.evaluate("document.querySelector('.dock').checkVisibility()") is False
        assert pg.evaluate("[...document.querySelectorAll('.pass.op')].every(e => e.checkVisibility())") is True
        assert erros == []
    finally:
        ctx.close()
