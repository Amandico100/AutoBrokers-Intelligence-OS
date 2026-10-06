# -*- coding: utf-8 -*-
"""SPEC-130-A F3 — O TESTE DO FIO (G1 · G2 · G3 · G4 · G12 · G15), sobre o HTML que o `/r/` SERVE.

    o pedido REAL do canário (104 ofertas, 5 cálculos, 6 eventos) gravado no banco DUBLÊ como o motor o deixa
      → `proposta.publicar_proposta` (a costura: porta.consultar → comparacao → modelo → Artifact Hub
         criar → renderizar → publicar → compartilhar)
      → `ArtifactService.abrir_compartilhado(token)` — o que o `route.ts` devolve ao navegador
      → afirmações sobre o HTML SERVIDO (não sobre a função):
         3 opções, na ordem · a anfitriã certa · 0 comissão · 0 produto diferente no ranking · a Azul por Assinatura
         fora · a econômica fora do ranking da padrão · nenhum nome da PERDEDORA · o `?fechar=` monta o wa.me da anfitriã
    bordas: só o banco (o PostgREST em memória). Porta, comparação, Hub e marca são os REAIS (CLAUDE.md §9.4).

🔬 LENTE INDEPENDENTE (G15): a vencedora e o ranking esperados são recalculados AQUI, direto da fixture, sem
`comparacao` (protocolo §5 ②: número publicado reconferido por caminho independente do que o produziu).

⛔ Nomes fictícios (CLAUDE.md §13.9). Rodar: cd backend && .venv/Scripts/python.exe -m pytest tests/test_spec130a_o_fio.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import html as _html
import re
import sys
from collections import defaultdict
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from app.services.artifacts.service import ArtifactService  # noqa: E402
from app.services.multicalculo import NaoEncontrado  # noqa: E402
from app.services.multicalculo.proposta import publicar_proposta  # noqa: E402
from dubles import mundo_da_proposta as M  # noqa: E402

BASE = "https://app.exemplo.test"
CHROME = ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/129.0.0.0 Mobile Safari/537.36")
TABELAS_DO_HUB = ("artifacts", "artifact_versions", "artifact_renders", "artifact_shares", "artifact_events")


# =====================================================================================================================
# a LENTE independente — direto da fixture, sem `comparacao`
# =====================================================================================================================
def _opcao_do_calculo(dados):
    return {e["calculo_id"]: e["opcao"] for e in dados["estados"]}


def _e_completa(o):
    c = o["coberturas"]
    return (str(c.get("tipoPadronizado") or c.get("tipo") or "") == "Compreensiva" and c.get("casco") == 100
            and "assinatura" not in str(o["seguradora"]).lower())


def lente_melhor_completa_por_corretora(dados, opcao="padrao"):
    op = _opcao_do_calculo(dados)
    melhor = {}
    for o in dados["ofertas"]:
        if op.get(o["calculo_id"]) == opcao and _e_completa(o):
            c = o["corretora_company_id"]
            melhor[c] = min(melhor.get(c, float("inf")), o["premio_total"])
    return melhor


def lente_ranking(dados, corretora, opcao="padrao"):
    """O menor prêmio COMPLETO por seguradora (código), menor primeiro."""
    op = _opcao_do_calculo(dados)
    por_seg = {}
    for o in dados["ofertas"]:
        if o["corretora_company_id"] == corretora and op.get(o["calculo_id"]) == opcao and _e_completa(o):
            k = o["seguradora_codigo"]
            por_seg[k] = min(por_seg.get(k, float("inf")), o["premio_total"])
    return sorted(por_seg.values())


def _br(v: float) -> str:
    inteiro, _, cent = f"{v:,.2f}".partition(".")
    return f"{inteiro.replace(',', '.')},{cent}"


def texto_visivel(fragmento: str) -> str:
    """O que se LÊ: sem tags, entidades resolvidas, espaços (inclusive os inquebráveis) colapsados."""
    t = re.sub(r"<script\b.*?</script>", " ", fragmento, flags=re.S | re.I)
    t = re.sub(r"<style\b.*?</style>", " ", t, flags=re.S | re.I)
    t = _html.unescape(re.sub(r"<[^>]+>", "", t))
    return re.sub(r"\s+", " ", t.replace("\xa0", " ").replace(" ", " ")).strip()


def secao_do_ranking(documento: str) -> str:
    """A lista "todas as seguradoras" da página (o desenho aprovado: `<ol class="rank">`)."""
    m = re.search(r"<(ol|ul|table)\b[^>]*class=\"[^\"]*\brank\b[^\"]*\"[^>]*>(.*?)</\1>", documento, re.S | re.I)
    assert m, "a página servida não tem a lista das seguradoras comparadas (`class=\"rank\"`)"
    return texto_visivel(m.group(2))


def ordem_das_opcoes(documento: str):
    vistos = []
    for o in re.findall(r'data-opcao="([^"]+)"', documento):
        if o not in vistos:
            vistos.append(o)
    return vistos


def _publicar(m, **kw):
    return asyncio.run(publicar_proposta(company_id=m.dono, pedido_id=m.pedido_id, situacao="novo_sem_apolice",
                                         primeiro_nome="Mariana", db=m.db, base_url=BASE, **kw))


def _servir(m, token):
    return ArtifactService(m.banco.visao("rota-publica")).abrir_compartilhado(token, user_agent=CHROME)


def _modelo_gravado(m, artifact_id):
    v = [x for x in m.banco.linhas("artifact_versions") if x["artifact_id"] == artifact_id]
    return sorted(v, key=lambda x: x["version"])[-1]["payload"]


# =====================================================================================================================
# O FIO — pedido do CANAL nas duas corretoras (o canário real)
# =====================================================================================================================
def test_o_fio_do_canal_pedido_real_ate_o_html_servido(monkeypatch):
    monkeypatch.setenv("PUBLIC_APP_URL", BASE)
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    d = m.dados

    # 🔬 a lente: quem VENCE, recalculado sem o motor
    melhores = lente_melhor_completa_por_corretora(d)
    vencedora = min(melhores, key=melhores.get)
    perdedora = next(c for c in melhores if c != vencedora)
    assert vencedora == m.alfa and round(melhores[m.alfa], 2) == 3730.56 and round(melhores[m.beta], 2) == 4784.27

    r = _publicar(m)
    assert r["url"] == f"{BASE}/r/{r['token']}" and r["versao"] == 1
    servido = _servir(m, r["token"])
    assert servido and servido["kind"] == "proposal" and servido["csp_script_hashes"]
    doc = servido["html"]
    tudo = texto_visivel(doc)
    modelo = _modelo_gravado(m, r["artifact_id"])

    # --- 3 opções, na ordem certa (a recomendada = a menor completa da VENCEDORA)
    ids = ordem_das_opcoes(doc)
    assert ids == [o["id"] for o in modelo["opcoes"]] and len(ids) == 3
    assert ids[0] == "recomendada" and ids[1] == "mais_em_conta" and ids[2] in ("menor_franquia", "outra_completa")
    assert modelo["opcoes"][0]["premio_anual"] == round(melhores[vencedora], 2)
    assert modelo["opcoes"][1]["premio_anual"] < modelo["opcoes"][0]["premio_anual"]

    # --- a anfitriã certa: a VENCEDORA, com a marca PUBLICADA dela
    anf = modelo["anfitria"]
    assert modelo["origem"] == "canal" and anf["nome"] == M.MARCA_ALFA and anf["marca_cadastrada"] is True
    assert anf["logo_data_url"] == M.LOGO_DATA_URL and anf["tema_claro"] and anf["tema_escuro"]
    assert M.MARCA_ALFA in tudo

    # --- nenhum nome da PERDEDORA (nem o da empresa, nem o da marca-rascunho, nem o número dela)
    for proibido in (M.NOME_BETA, M.MARCA_BETA, "Vega", "99999-0002", "999990002", "999990003"):
        assert proibido not in doc, proibido
    perdedora_no_modelo = [e for e in modelo["entre_corretoras"] if not e["vencedora"]]
    assert len(perdedora_no_modelo) == 1 and perdedora_no_modelo[0]["corretora"] is None
    assert perdedora_no_modelo[0]["melhor_completa"] == round(melhores[perdedora], 2)
    assert perdedora not in str(modelo) and m.canal not in str(modelo)

    # --- 0 comissão (G3): o número gravado no banco não chega à página nem ao modelo
    assert "comiss" not in doc.lower() and "comiss" not in str(modelo).lower()
    for forma in (_br(M.COMISSAO_NO_BANCO), str(M.COMISSAO_NO_BANCO)):
        assert forma not in doc and forma not in str(modelo)

    # --- o RANKING servido: só completas da padrão, da anfitriã, menor primeiro (G2 · G12)
    rk = secao_do_ranking(doc)
    esperado = lente_ranking(d, vencedora)
    assert [x["premio_anual"] for x in modelo["ranking"]] == [round(v, 2) for v in esperado]
    posicoes = [rk.find(_br(v)) for v in esperado]
    assert all(p >= 0 for p in posicoes) and posicoes == sorted(posicoes), "ranking servido fora de ordem"
    op = _opcao_do_calculo(d)
    da_vencedora = [o for o in d["ofertas"] if o["corretora_company_id"] == vencedora]
    precos_completos_padrao = {_br(o["premio_total"]) for o in da_vencedora
                               if op[o["calculo_id"]] == "padrao" and _e_completa(o)}
    diferentes = {_br(o["premio_total"]) for o in da_vencedora if op[o["calculo_id"]] == "padrao" and not _e_completa(o)}
    economica = {_br(o["premio_total"]) for o in da_vencedora if op[o["calculo_id"]] == "economica"}
    ajuste = {_br(o["premio_total"]) for o in da_vencedora if op[o["calculo_id"]] == "ajuste"}
    # controle: os conjuntos PODEM se distinguir (nenhum preço da padrão completa coincide com os outros)
    assert diferentes and economica and ajuste
    assert not (precos_completos_padrao & (diferentes | economica | ajuste))
    for preco in diferentes | economica | ajuste:
        assert preco not in rk, f"preço fora do ranking da padrão apareceu nele: {preco}"
    assert "Assinatura" not in rk and "assinatura" not in rk.lower()

    # --- a Azul por Assinatura: fora do ranking E o preço dela (que não é anual) em lugar nenhum da página
    assinatura = [o for o in d["ofertas"] if "assinatura" in o["seguradora"].lower()]
    assert assinatura
    for o in assinatura:
        assert _br(o["premio_total"]) not in tudo and _br(o["premio_mensal"]) not in tudo

    # --- o "Quero fechar": o servidor monta o wa.me da ANFITRIÃ (nunca da query)
    svc = ArtifactService(m.banco.visao("rota-publica"))
    for i in ids:
        destino = svc.fechar_compartilhado(r["token"], i)
        assert destino and destino.startswith(f"https://wa.me/{M.WHATS_ALFA}?text=")
    assert svc.fechar_compartilhado(r["token"], "nao_existe") is None

    # --- a mensagem do WhatsApp sai junto, com o link e sem comissão nem perdedora
    msg = "\n".join(r["mensagem"])
    assert r["url"] in msg and "comiss" not in msg.lower() and "Vega" not in msg

    # --- DOIS tenants: o artefato mora no SOLICITANTE (o canal); a anfitriã e a perdedora não recebem linha
    for t in TABELAS_DO_HUB:
        donos = {x.get("company_id") for x in m.banco.linhas(t)}
        assert donos <= {m.canal}, (t, donos)
    assert m.banco.linhas("artifacts") and m.banco.linhas("artifact_shares")


# =====================================================================================================================
# O FIO — pedido da PRÓPRIA corretora (a anfitriã é ela mesma; marca NÃO publicada = neutra)
# =====================================================================================================================
def test_o_fio_da_corretora_anfitria_e_ela_mesma_e_sem_marca_publicada_fica_neutra(monkeypatch):
    monkeypatch.setenv("PUBLIC_APP_URL", BASE)
    m = M.montar_mundo(monkeypatch, solicitante="beta")
    r = _publicar(m)
    doc = _servir(m, r["token"])["html"]
    modelo = _modelo_gravado(m, r["artifact_id"])

    assert modelo["origem"] == "corretora" and modelo["entre_corretoras"] is None
    anf = modelo["anfitria"]
    assert anf["nome"] == M.NOME_BETA and anf["marca_cadastrada"] is False
    for chave in ("logo_data_url", "tema_claro", "tema_escuro", "cores", "google"):
        assert not anf.get(chave), chave
    assert M.MARCA_BETA not in doc                       # o rascunho não vale como marca
    ids = ordem_das_opcoes(doc)
    assert ids == [o["id"] for o in modelo["opcoes"]] and len(ids) == 3 and ids[0] == "recomendada"
    assert modelo["opcoes"][0]["premio_anual"] == round(lente_melhor_completa_por_corretora(m.dados)[m.beta], 2)
    # a dona VÊ a comissão na porta — e mesmo assim ela não chega à página
    assert "comiss" not in doc.lower() and _br(M.COMISSAO_NO_BANCO) not in doc
    for proibido in (M.NOME_ALFA, M.MARCA_ALFA, "Orion"):
        assert proibido not in doc
    destino = ArtifactService(m.banco.visao("rota-publica")).fechar_compartilhado(r["token"], ids[0])
    assert destino and destino.startswith("https://wa.me/5548999990002?text=")    # o de ATENDIMENTO, não o observer
    for t in TABELAS_DO_HUB:
        assert {x.get("company_id") for x in m.banco.linhas(t)} <= {m.beta}


# =====================================================================================================================
# A autorização vem ANTES de gravar
# =====================================================================================================================
@pytest.mark.parametrize("quem", ["intruso", "alfa"])
def test_o_solicitante_errado_e_recusado_antes_de_gravar(monkeypatch, quem):
    monkeypatch.setenv("PUBLIC_APP_URL", BASE)
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    with pytest.raises(NaoEncontrado):
        asyncio.run(publicar_proposta(company_id=getattr(m, quem), pedido_id=m.pedido_id,
                                      situacao="novo_sem_apolice", db=m.db, base_url=BASE))
    for t in TABELAS_DO_HUB:
        assert m.banco.linhas(t) == [], t
