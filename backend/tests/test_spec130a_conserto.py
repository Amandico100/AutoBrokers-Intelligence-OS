# -*- coding: utf-8 -*-
"""SPEC-130-A — o CONSERTO ÚNICO (laudos do juiz, do red team e do crítico final, 06/10/2026).

🔴 A lição que este arquivo fecha: 186 testes verdes conviveram com 4 frases mentirosas, porque o teste afirmava
sobre o MODELO e nunca sobre a FRASE do HTML SERVIDO. Aqui cada guarda lê o que `abrir_compartilhado` serve (o que o
`route.ts` devolve ao navegador) ou a mensagem que sai — e cada um nasceu VERMELHO com o defeito reproduzido.

    RT-B1  "a melhor das N" / o selo / o og:title só para a 1ª do RANKING (com apólice + completa+: a Porto, 11ª de 11,
           era "a melhor das 11")
    J-B1   sem WhatsApp da anfitriã: nenhuma frase promete WhatsApp, e publicar RECUSA (salvo a bandeira)
    J-B2   com apólice / renovação SEM a apólice: recusa (nunca "Igual à sua atual" inventado); o comando tem --apolice
    J-B3   a frase do resumo FECHA a conta — somada a partir dos números LIDOS do HTML
    RT-1 · RT-3 · RT-8 · RT-9 · RT-10 · J-P1 · J-P6 · o desenho (régua, sem JS, impressão, fim) · o dado (duelo, bem)

Bordas: só o banco (o PostgREST em memória da 129-B). Porta, comparação, Hub e marca são os REAIS (CLAUDE.md §9.4).
⛔ Nomes fictícios (CLAUDE.md §13.9). Rodar: cd backend && .venv/Scripts/python.exe -m pytest tests/test_spec130a_conserto.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import copy
import io
import json
import re
import sys
import uuid
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from app.services.artifacts import proposta_html as PH  # noqa: E402
from app.services.artifacts.service import ArtifactService  # noqa: E402
from app.services.multicalculo import proposta as P  # noqa: E402
from app.services.multicalculo.comando_proposta import executar  # noqa: E402
from app.services.multicalculo.mensagem import (TETO_POR_BALAO_DO_CANAL, conferir_do_canal,  # noqa: E402
                                                mensagem_whatsapp)
from dubles import mundo_da_proposta as M  # noqa: E402
from test_spec130a_o_fio import CHROME, secao_do_ranking, texto_visivel  # noqa: E402

BASE = "https://app.exemplo.test"
TABELAS_DO_HUB = ("artifacts", "artifact_versions", "artifact_renders", "artifact_shares", "artifact_events")
APOLICE_PORTO = {"seguradora": "Porto", "premio_anual": 8200}
CONTRATO = json.loads((BACKEND / "tests" / "fixtures" / "proposta" / "modelo_contrato.json").read_text(encoding="utf-8"))


def _publicar(m, situacao="novo_sem_apolice", **kw):
    return asyncio.run(P.publicar_proposta(m.dono, m.pedido_id, situacao, primeiro_nome=kw.pop("nome", "Ana"),
                                           db=m.db, base_url=BASE, **kw))


def _servido(m, token):
    s = ArtifactService(m.banco.visao("rota-publica")).abrir_compartilhado(token, user_agent=CHROME)
    assert s, "o link não abriu"
    return s["html"]


def _h1(doc):
    return texto_visivel(re.search(r"<h1>(.*?)</h1>", doc, re.S).group(1))


def _og_title(doc):
    return re.search(r'property="og:title" content="([^"]*)"', doc).group(1)


def _br_num(txt):
    return float(txt.replace(".", "").replace(",", "."))


def _com_completa_mais(m):
    """A completa+ como a F4 a grava (o roteiro `a3_apolice.py` do red team): um cálculo novo da MESMA corretora, as
    ofertas da padrão +8 % e `reparoRapido=True` nas coberturas."""
    calcs = m.banco.linhas("multicalculo_calculos")
    pad = next(c for c in calcs if c["opcao"] == "padrao" and c["company_id"] == m.dono)
    novo = dict(pad, id=str(uuid.uuid4()), opcao="completa_mais", origem_calculo_id=pad["id"],
                versao=max(c["versao"] for c in calcs if c["company_id"] == m.dono) + 1)
    m.banco.semear("multicalculo_calculos", novo)
    for o in [o for o in m.banco.linhas("multicalculo_ofertas") if o["calculo_id"] == pad["id"]]:
        x = copy.deepcopy(o)
        x.update(id=str(uuid.uuid4()), calculo_id=novo["id"], premio_total=round(o["premio_total"] * 1.08, 2))
        x["premio_mensal"] = round(x["premio_total"] / 12, 2)
        for p in x.get("parcelamentos") or []:
            p["primeira_parcela"] = round(p["primeira_parcela"] * 1.08, 2)
            p["demais_parcelas"] = round(p["demais_parcelas"] * 1.08, 2)
        x.setdefault("coberturas", {})["reparoRapido"] = True
        m.banco.semear("multicalculo_ofertas", x)


def _sem_whatsapp(m, corretora):
    """Tira da corretora TODO canal de fechamento: o WhatsApp da marca e a integração de atendimento."""
    for p in m.banco.linhas("brand_profiles"):
        if p["company_id"] == corretora:
            p["contact"] = {}
    for i in m.banco.linhas("integrations"):
        if i["company_id"] == corretora and i["purpose"] == "attendance":
            i["is_active"] = False


# =====================================================================================================================
# RT-B1 — "a melhor das N" só para a 1ª do RANKING (lido do HTML servido)
# =====================================================================================================================
@pytest.mark.parametrize("situacao,rotulo_da_atual", [("novo_com_apolice", "Igual à sua atual"),
                                                      ("renovacao", "Sua renovação")])
def test_RT_B1_com_apolice_e_completa_mais_o_topo_e_a_1a_do_ranking_no_html_servido(monkeypatch, situacao,
                                                                                    rotulo_da_atual):
    """📊 roteiro do red team (06/10): antes, o H1 era "Ana, a melhor das 11 para o seu Compass: Porto, R$ 8.460 por
    ano." e o og:title "…Porto por R$ 8.460,29…" — a Porto é a 11ª (a MAIS cara) de 11."""
    monkeypatch.setenv("PUBLIC_APP_URL", BASE)
    m = M.montar_mundo(monkeypatch, solicitante="beta")
    _com_completa_mais(m)
    r = _publicar(m, situacao, apolice_atual=APOLICE_PORTO)
    doc = _servido(m, r["token"])

    # 🔬 a 1ª do ranking, LIDA do próprio HTML servido (a lista "todas as seguradoras")
    rk = secao_do_ranking(doc)
    precos = [_br_num(x) for x in re.findall(r"R\$ ([\d.]+,\d{2})", rk)]
    assert precos and precos == sorted(precos)
    primeira = re.search(r'<ol class="rank"><li[^>]*><span class="n">1</span><span class="nm">([^<]+)', doc).group(1)
    menor = f"{precos[0]:,.0f}".replace(",", ".")
    h1 = _h1(doc)
    assert h1 == f"Ana, a melhor das {len(precos)} para o seu Compass: {primeira}, R$ {menor} por ano."
    assert "Porto" not in h1 and primeira != "Porto"
    assert _og_title(doc).startswith(f"Sua proposta de seguro: {primeira} por R$ ")
    # o 1º cartão leva o rótulo da 1ª do ranking; a seguradora da apólice aparece, com o rótulo dela, na posição dela
    assert texto_visivel(re.search(r'<span class="badge b1">(.*?)</span>', doc).group(1)) == "Recomendada"
    assert rotulo_da_atual in texto_visivel(doc)
    assert "11º menor preço entre as 11 seguradoras com cobertura completa" in texto_visivel(doc)
    # a mensagem: a 1ª linha de opção é a Recomendada (a 1ª do ranking), nunca a seguradora atual
    assert re.search(r"^\*Recomendada:\* " + primeira, r["mensagem"][0], re.M)


def test_RT_B1_sem_opcao_que_seja_a_1a_do_ranking_o_titulo_nao_afirma_posicao():
    m = copy.deepcopy(CONTRATO)
    m["opcoes"] = [o for o in m["opcoes"] if o["id"] != "recomendada"]          # a 1ª do ranking não está entre elas
    doc = PH.render_proposta(m)
    h1 = _h1(doc)
    assert "melhor" not in h1.lower() and "Tokio" in h1 and "(Menor franquia)" in h1
    assert "Por que recomendamos" not in texto_visivel(doc)
    # CONTROLE: o contrato inteiro afirma — e afirma a 1ª do ranking
    assert _h1(PH.render_proposta(CONTRATO)).startswith("Mariana, a melhor das 11 para o seu Compass: Bradesco")


# =====================================================================================================================
# J-B1 — sem WhatsApp: nenhuma promessa de WhatsApp, e publicar recusa sem a bandeira
# =====================================================================================================================
def test_J_B1_sem_whatsapp_publicar_recusa_antes_de_gravar_e_o_comando_explica(monkeypatch):
    monkeypatch.setenv("PUBLIC_APP_URL", BASE)
    m = M.montar_mundo(monkeypatch, solicitante="beta")
    _sem_whatsapp(m, m.beta)
    with pytest.raises(P.SemCanalDeFechamento, match="sem-whatsapp"):
        _publicar(m)
    assert all(m.banco.linhas(t) == [] for t in TABELAS_DO_HUB)
    saida = io.StringIO()
    assert asyncio.run(executar(["--pedido", m.pedido_id, "--confirmar"], db=m.db, saida=saida)) == 2
    assert "Quero fechar" in saida.getvalue() and "--sem-whatsapp" in saida.getvalue()
    assert all(m.banco.linhas(t) == [] for t in TABELAS_DO_HUB)
    saida = io.StringIO()
    assert asyncio.run(executar(["--pedido", m.pedido_id], db=m.db, saida=saida)) == 0           # o ensaio avisa
    assert "RECUSADA" in saida.getvalue()


@pytest.mark.parametrize("solicitante", ["canal", "beta"])
def test_J_B1_sem_whatsapp_nenhuma_frase_do_html_servido_promete_whatsapp(monkeypatch, solicitante):
    """📊 canário real (06/10): sem rodapé de fechar, a página dizia "atende você pelo WhatsApp", "Avise a sua corretora
    pelo WhatsApp" e "Para a sua corretora, pelo WhatsApp"."""
    monkeypatch.setenv("PUBLIC_APP_URL", BASE)
    m = M.montar_mundo(monkeypatch, solicitante=solicitante)
    anf = m.alfa if solicitante == "canal" else m.beta
    # CONTROLE primeiro (com WhatsApp): a palavra aparece — o guarda consegue falhar
    controle = _servido(m, _publicar(m)["token"])
    assert "whatsapp" in texto_visivel(controle).lower()
    _sem_whatsapp(m, anf)
    r = _publicar(m, permitir_sem_whatsapp=True)
    doc = _servido(m, r["token"])
    assert "whatsapp" not in texto_visivel(doc).lower()
    assert "whatsapp" not in json.dumps(re.search(r'id="ab-dados">(.*?)</script>', doc, re.S).group(1)).lower()
    sem_script = re.sub(r"<script\b.*?</script>", "", doc, flags=re.S)
    assert "?fechar=" not in sem_script and "wa.me" not in doc and 'class="dock"' not in doc
    assert "Avise a sua corretora assim que puder" in texto_visivel(doc)


# =====================================================================================================================
# J-B2 — com apólice / renovação sem a apólice: recusa; o comando tem --apolice
# =====================================================================================================================
@pytest.mark.parametrize("situacao", ["novo_com_apolice", "renovacao"])
def test_J_B2_sem_apolice_recusa_e_o_comando_pede_o_arquivo(monkeypatch, tmp_path, situacao):
    monkeypatch.setenv("PUBLIC_APP_URL", BASE)
    m = M.montar_mundo(monkeypatch, solicitante="beta")
    with pytest.raises(ValueError, match="apólice atual"):
        _publicar(m, situacao)
    assert all(m.banco.linhas(t) == [] for t in TABELAS_DO_HUB)
    saida = io.StringIO()
    assert asyncio.run(executar(["--pedido", m.pedido_id, "--situacao", situacao], db=m.db, saida=saida)) == 2
    assert "--apolice" in saida.getvalue()
    arq = tmp_path / "apolice.json"
    arq.write_text(json.dumps({"seguradora": "Porto", "premio_anual": 8200}), encoding="utf-8")
    saida = io.StringIO()
    codigo = asyncio.run(executar(["--pedido", m.pedido_id, "--situacao", situacao, "--apolice", str(arq),
                                   "--confirmar"], db=m.db, saida=saida))
    assert codigo == 0, saida.getvalue()
    doc = _servido(m, re.search(r"/r/(\S+)", saida.getvalue()).group(1))
    assert ("Igual à sua atual" if situacao == "novo_com_apolice" else "Sua renovação") in texto_visivel(doc)
    # arquivo sem a seguradora: recusa
    arq.write_text(json.dumps({"premio_anual": 8200}), encoding="utf-8")
    saida = io.StringIO()
    assert asyncio.run(executar(["--pedido", m.pedido_id, "--situacao", situacao, "--apolice", str(arq)],
                                db=m.db, saida=saida)) == 2


# =====================================================================================================================
# J-B3 — a frase do resumo FECHA a conta, somada dos números LIDOS do HTML
# =====================================================================================================================
def _numeros_da_conta(doc):
    frase = re.search(r"Cotamos em [^.]*\.", texto_visivel(doc)).group(0)
    nums = [int(x) for x in re.findall(r"\d+", frase)]
    return frase, nums[0], nums[1:]


def test_J_B3_a_frase_do_resumo_fecha_a_conta_no_html_servido(monkeypatch):
    """📊 canário (06/10): "Cotamos em 16 seguradoras: 13 deram preço … e 2 não deram preço" → 13 + 2 = 15."""
    monkeypatch.setenv("PUBLIC_APP_URL", BASE)
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    doc = _servido(m, _publicar(m)["token"])
    frase, total, partes = _numeros_da_conta(doc)
    assert total == sum(partes) and len(partes) == 3, frase
    assert (total, partes) == (16, [13, 1, 2]), frase                      # 📊 reconferido por SQL pelo juiz (G15)
    assert f"cotado em {total} seguradoras" in texto_visivel(doc)
    assert "Algumas também" not in texto_visivel(doc)


# =====================================================================================================================
# RT-1 · RT-3 — a proposta existente é a DO PEDIDO, e o assunto acompanha a versão nova
# =====================================================================================================================
def test_RT_1_depois_de_200_propostas_mais_novas_republicar_e_versao_nova(monkeypatch):
    monkeypatch.setenv("PUBLIC_APP_URL", BASE)
    m = M.montar_mundo(monkeypatch, solicitante="beta")
    um = _publicar(m)
    for i in range(201):
        m.banco.semear("artifacts", {"id": str(uuid.uuid4()), "company_id": m.dono, "template_key": "proposal.quote",
                                     "kind": "proposal", "title": "x", "current_version": 1,
                                     "subject_ref": {"kind": "multicalculo_pedido", "pedido_id": str(uuid.uuid4())},
                                     "created_at": f"2026-10-07T{(i // 60) % 24:02d}:{i % 60:02d}:00+00:00"})
    dois = _publicar(m)
    assert (dois["artifact_id"], dois["versao"]) == (um["artifact_id"], 2)
    assert len([a for a in m.banco.linhas("artifacts")
                if (a.get("subject_ref") or {}).get("pedido_id") == m.pedido_id]) == 1


def test_RT_3_a_versao_nova_regrava_o_assunto(monkeypatch):
    monkeypatch.setenv("PUBLIC_APP_URL", BASE)
    m = M.montar_mundo(monkeypatch, solicitante="beta")
    r = _publicar(m)
    art = next(a for a in m.banco.linhas("artifacts") if a["id"] == r["artifact_id"])
    certo = copy.deepcopy(art["subject_ref"])
    art["subject_ref"] = dict(certo, anfitria_company_id=m.alfa, opcoes={})      # o assunto VELHO de outra versão
    _publicar(m)
    art = next(a for a in m.banco.linhas("artifacts") if a["id"] == r["artifact_id"])
    assert art["subject_ref"] == certo


# =====================================================================================================================
# RT-9 — token inexistente: "não encontrado", nunca 500
# =====================================================================================================================
def test_RT_9_token_inexistente_devolve_none_e_nao_explode(monkeypatch):
    monkeypatch.setenv("PUBLIC_APP_URL", BASE)
    m = M.montar_mundo(monkeypatch, solicitante="beta")
    svc = ArtifactService(m.banco.visao("rota-publica"))
    falso = "x" * 43
    assert svc.abrir_compartilhado(falso, user_agent=CHROME) is None
    assert svc.previa_compartilhada(falso) is None and svc.fechar_compartilhado(falso, "recomendada") is None
    r = _publicar(m)                                                          # CONTROLE: o token de verdade abre
    assert svc.abrir_compartilhado(r["token"], user_agent=CHROME)


# =====================================================================================================================
# RT-10 — o nome do canal é CONFIGURAÇÃO
# =====================================================================================================================
def test_RT_10_o_nome_do_canal_vem_da_config(monkeypatch):
    for arq in ("proposta_apresentacao.py", "proposta_html.py", "proposta_previa.py"):
        assert "Quem Cobra Menos" not in (BACKEND / "app" / "services" / "artifacts" / arq).read_text(encoding="utf-8")
    monkeypatch.setenv("PUBLIC_APP_URL", BASE)
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    padrao = _servido(m, _publicar(m)["token"])
    assert "Comparação independente · Quem Cobra Menos" in texto_visivel(padrao)
    m.banco.semear("multicalculo_config", {"company_id": m.canal, "config": {"canal": {"nome": "Comparador Ficticio"}}})
    doc = _servido(m, _publicar(m)["token"])
    assert "Comparação independente · Comparador Ficticio" in texto_visivel(doc) and "Quem Cobra Menos" not in doc


# =====================================================================================================================
# J-P1 · J-P6 — a "Mais em conta" diz o que corta; o canal não fala na 1ª pessoa da corretora
# =====================================================================================================================
def test_J_P1_a_mais_em_conta_da_mensagem_diz_o_que_cobre_a_menos(monkeypatch):
    monkeypatch.setenv("PUBLIC_APP_URL", BASE)
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    r = _publicar(m, nome="Mariana")
    # SPEC-130-A.1 (§9.3 — a lição MIGRA): o pedido do CANAL leva a mensagem do canal (D-130A1-01); a "Mais em conta"
    # mora no cartão do balão 2 e continua dizendo o que cobre a menos, logo abaixo do preço
    b2 = r["mensagem"][1]
    bloco = b2.split("*Mais em conta*")[1].split("\n\n")[0]
    linhas = bloco.split("\n")
    assert len(linhas) == 3 and linhas[2].startswith("_Cobre menos: franquia normal de R$ ") and "vidros" in linhas[2]
    assert max(conferir_do_canal(r["mensagem"])["caracteres_por_balao"]) <= TETO_POR_BALAO_DO_CANAL


def test_J_P6_a_pagina_do_canal_nao_fala_na_primeira_pessoa_da_corretora(monkeypatch):
    monkeypatch.setenv("PUBLIC_APP_URL", BASE)
    primeira_pessoa = ("minha margem", "me mande", "eu calculo", "eu comparo", "eu procuro", "te mostrar", "Cotei em")
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    canal = texto_visivel(_servido(m, _publicar(m)["token"]))
    assert [x for x in primeira_pessoa if x in canal] == []
    assert "a corretora pode pedir o desconto" in canal.lower()
    mb = M.montar_mundo(monkeypatch, solicitante="beta")                  # CONTROLE: a página da corretora fala por ela
    assert "minha margem" in texto_visivel(_servido(mb, _publicar(mb)["token"]))


# =====================================================================================================================
# o DADO — o duelo só com o preço da recomendada; o carro escrito como o segurado o chama
# =====================================================================================================================
def _B(vencedora_preco):
    b = copy.deepcopy(CONTRATO)
    b["origem"] = "canal"
    b["anfitria"] = {"nome": "Atlas Fortis Ficticia", "marca_cadastrada": False, "whatsapp": "5547999999999"}
    b["entre_corretoras"] = [{"corretora": "Atlas Fortis Ficticia", "melhor_completa": vencedora_preco, "vencedora": True},
                             {"corretora": None, "melhor_completa": 5120.0, "vencedora": False}]
    return b


def test_o_duelo_entre_corretoras_so_aparece_com_o_preco_da_recomendada():
    diverge = texto_visivel(PH.render_proposta(_B(3730.56)))               # 📊 o caso B do crítico final
    assert "Outra corretora parceira" not in diverge and "Teve o menor preço com cobertura completa" not in diverge
    assert "Quem atende é a Atlas Fortis Ficticia, que teve" not in "\n".join(mensagem_whatsapp(_B(3730.56), BASE))
    igual = texto_visivel(PH.render_proposta(_B(4784.27)))                 # CONTROLE: o mesmo preço → o duelo aparece
    assert "Outra corretora parceira" in igual and "Teve o menor preço" in igual
    assert "Quem atende é a Atlas Fortis Ficticia, que teve" in "\n".join(mensagem_whatsapp(_B(4784.27), BASE))


@pytest.mark.parametrize("bruto,esperado", [
    ("COMPASS LIMITED 2.0 4X2 FLEX 16V AUT.", "Compass Limited 2.0 flex automático"),
    ("GOL 1.0 FLEX 12V 5P", "Gol 1.0 flex"),
    ("ONIX LTZ 1.4 FLEX 8V 4P MEC", "Onix LTZ 1.4 flex manual"),
    ("TORO VOLCANO 2.0 TB DIESEL 4X4 AUT", "Toro Volcano 2.0 turbo diesel automático"),
])
def test_a_descricao_do_carro_normalizada_do_texto_cru(bruto, esperado):
    assert P.descricao_do_veiculo(bruto) == esperado


def test_a_descricao_do_carro_no_html_servido(monkeypatch):
    monkeypatch.setenv("PUBLIC_APP_URL", BASE)
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    lede = texto_visivel(re.search(r'<p class="lede">(.*?)</p>', _servido(m, _publicar(m)["token"]), re.S).group(1))
    assert lede.startswith("Compass Limited 2.0 flex automático, cotado em ") and "4X2" not in lede and "16V" not in lede


# =====================================================================================================================
# o DESENHO — estático (o HTML) e no navegador de verdade (Chromium, CSP real)
# =====================================================================================================================
def test_a_regua_ancora_o_rotulo_na_ponta_so_quando_ele_esta_na_ponta():
    doc = PH.render_proposta(CONTRATO)
    ticks = re.findall(r'<span class="tick( first| last)?" style="left:([\d.]+)%">', doc)
    assert ticks
    for cls, pct in ticks:
        if cls == " last":
            assert float(pct) == 100.0, pct
        if cls == " first":
            assert float(pct) == 0.0, pct
    assert any(cls == "" and 50 < float(pct) < 100 for cls, pct in ticks)   # 📊 o "R$ 8 mil" a 80 % existe e é centrado


def test_a_nota_tem_legenda_no_cartao_e_o_fim_da_pagina_tem_quero_fechar():
    doc = PH.render_proposta(CONTRATO)
    assert doc.count('<span class="fh">preço, franquia e coberturas</span>') == len(CONTRATO["opcoes"])
    fim = re.search(r'<section class="s fim".*?</section>', doc, re.S).group(0)
    assert 'href="?fechar=recomendada"' in fim and "Recomendada" in texto_visivel(fim)
    sem = copy.deepcopy(CONTRATO)
    sem["anfitria"].pop("whatsapp", None)
    sem.pop("cta", None)
    assert 'class="s fim"' not in PH.render_proposta(sem)                 # sem WhatsApp não há fecho que prometa


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


def _abrir(navegador, doc, largura=390, js=True):
    csp = (f"default-src 'none'; script-src '{PH.HASH_DO_SCRIPT}'; img-src 'self' data:; style-src 'unsafe-inline'; "
           "font-src 'self' data:; base-uri 'none'; form-action 'none'")
    ctx = navegador.new_context(viewport={"width": largura, "height": 844 if largura < 600 else 900},
                                device_scale_factor=2, java_script_enabled=js)
    pg = ctx.new_page()
    erros = []
    pg.on("console", lambda m: erros.append(m.text) if m.type in ("error", "warning") else None)
    pg.set_content(doc.replace("<head>", f'<head>\n<meta http-equiv="Content-Security-Policy" content="{csp}">', 1),
                   wait_until="load")
    pg.wait_for_timeout(700)
    return ctx, pg, erros


_TICKS = r"""() => { const rail = document.querySelector('.rail').getBoundingClientRect();
  return [...document.querySelectorAll('.tick')].filter(e => e.checkVisibility()).map(e => {
    const b = e.getBoundingClientRect(), pct = parseFloat(e.style.left), x = rail.left + pct / 100 * rail.width;
    return {cls: e.className, pct, erro: (pct === 0 ? b.left - x : pct === 100 ? b.right - x
            : (b.left + b.right) / 2 - x) / rail.width * 100}; }); }"""


def _defeitos_da_regua(pg):
    return [t for t in pg.evaluate(_TICKS) if abs(t["erro"]) > 2]


@pytest.mark.parametrize("largura", [390, 1280])
def test_navegador_cada_rotulo_da_regua_esta_no_valor_dele(navegador, largura):
    """O centro de cada rótulo do meio cai no valor dele ±2 % do eixo (na ponta, a borda dele). MUTAÇÃO: o `last` de
    antes no último rótulo visível (a 80 %) → vermelho."""
    doc = PH.render_proposta(CONTRATO)
    ctx, pg, erros = _abrir(navegador, doc, largura)
    try:
        assert len(pg.evaluate(_TICKS)) >= 2 and _defeitos_da_regua(pg) == [] and erros == []
    finally:
        ctx.close()
    mutado = re.sub(r'(<span class="ticks n"[^>]*>(?:<span class="tick[^"]*" [^>]*>[^<]*</span>)*?)'
                    r'<span class="tick" (style="left:80\.00%")', r'\1<span class="tick last" \2', doc, count=1)
    if largura == 390:
        assert mutado != doc
        ctx, pg, _ = _abrir(navegador, mutado, largura)
        try:
            assert _defeitos_da_regua(pg) != [], "o guarda da régua não ficou vermelho"
        finally:
            ctx.close()


@pytest.mark.parametrize("js", [True, False])
def test_navegador_sem_js_o_rodape_nao_promete_a_opcao_errada(navegador, js):
    ctx, pg, erros = _abrir(navegador, PH.render_proposta(CONTRATO), js=js)
    try:
        fechar = pg.evaluate("document.querySelector('#ab-fechar').checkVisibility()")
        neutro = pg.evaluate("document.querySelector('.dock .pick').checkVisibility()")
        assert (fechar, neutro) == ((True, False) if js else (False, True))
        assert pg.evaluate("document.querySelector('.fim-fechar').checkVisibility()") is True   # o fecho vale sempre
        assert erros == []
    finally:
        ctx.close()


def test_navegador_preco_vencido_vira_pedir_atualizacao(navegador):
    """RT-8 (red team): depois da validade o "Quero fechar" deixava fechar pelo preço velho. CONTROLE: no prazo."""
    vencida = copy.deepcopy(CONTRATO)
    vencida["validade_ate"] = "2020-01-10"
    ctx, pg, erros = _abrir(navegador, PH.render_proposta(vencida))
    try:
        assert pg.evaluate("document.querySelector('.pass .valid').textContent") == \
            "Preço vencido em 10/01 — peça uma atualização"
        assert pg.evaluate("document.querySelector('#ab-fechar b').textContent") == "Pedir preço atualizado"
        assert pg.evaluate("document.querySelector('#ab-fechar').getAttribute('href')").startswith("https://wa.me/")
        assert pg.evaluate("[...document.querySelectorAll('.want')].every(a => a.textContent.trim() === "
                           "'Pedir preço atualizado')")
        pg.click("#tab-1")
        pg.wait_for_timeout(700)
        assert pg.evaluate("document.querySelector('#ab-fechar').getAttribute('href')").startswith("https://wa.me/")
        assert erros == []
    finally:
        ctx.close()
    no_prazo = copy.deepcopy(CONTRATO)
    no_prazo["validade_ate"] = "2099-12-31"
    ctx, pg, _ = _abrir(navegador, PH.render_proposta(no_prazo))
    try:
        assert pg.evaluate("document.querySelector('.pass .valid').textContent") == "Preço válido até 31/12"
        assert pg.evaluate("document.querySelector('#ab-fechar').getAttribute('href')") == "?fechar=recomendada"
    finally:
        ctx.close()


def test_navegador_impressao_sem_abas_e_o_cartao_na_margem_do_titulo(navegador):
    ctx, pg, _ = _abrir(navegador, PH.render_proposta(CONTRATO), largura=800)
    try:
        pg.emulate_media(media="print")
        med = pg.evaluate("""() => ({abas: [...document.querySelectorAll('.tabs, .nav, #count, .dock, .fim')]
              .some(e => e.checkVisibility()), h1: document.querySelector('h1').getBoundingClientRect().left,
              passe: document.querySelector('.pass').getBoundingClientRect().left,
              nome: document.querySelector('.badge.b1').checkVisibility()})""")
        assert med["abas"] is False and abs(med["h1"] - med["passe"]) <= 1 and med["nome"] is True
    finally:
        ctx.close()
