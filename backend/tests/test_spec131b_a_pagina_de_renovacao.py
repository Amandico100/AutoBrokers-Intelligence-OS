# -*- coding: utf-8 -*-
"""SPEC-131-B · G4 — a página de RENOVAÇÃO e a mensagem (D-131-22/23/24/40/42, laudo I3 §2.3, BLOCO 0 B1/B2).

🔴 A lição da 130-A vale aqui: o guarda lê o HTML SERVIDO (`abrir_compartilhado`, o que o `route.ts` devolve) e a
mensagem que sai — nunca só o modelo. Cada guarda das mutações da SPEC nasceu VERMELHO com o defeito reproduzido:

    (1) "a melhor das N" / a "menor completa em 1º" volta na renovação   → test_a_pagina_servida_* · test_a_ordem_*
    (2) "renova com a gente há N anos" SEM prova                          → test_sem_prova_a_frase_nao_aparece
    (3) "Quero renovar" vai à CORRETORA com dono de WhatsApp confirmado   → test_quero_renovar_vai_ao_dono_*
    + nenhum telefone do CLIENTE no HTML, no modelo, nas linhas do Hub ou na mensagem

Bordas: o banco (o PostgREST em memória da 129-B, com a CHECK de opções alargada como a 20261013_01) e o histórico da
InfoCap (dublê da borda — nenhuma chamada real). Porta, comparação, Hub, repositório da renovação e marca são REAIS
(CLAUDE.md §9.4). ⛔ Nomes fictícios (CLAUDE.md §13.9).
Rodar: cd backend && .venv/Scripts/python.exe -m pytest tests/test_spec131b_a_pagina_de_renovacao.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import copy
import json
import re
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from app.services.artifacts import proposta_html as PH  # noqa: E402
from app.services.artifacts.proposta_canal_html import render_proposta_do_canal  # noqa: E402
from app.services.artifacts.service import ArtifactService  # noqa: E402
from app.services.multicalculo import comparacao as C  # noqa: E402
from app.services.multicalculo import proposta as P  # noqa: E402
from app.services.multicalculo.mensagem import (FRASES_PROIBIDAS, TETO_DE_CARACTERES,  # noqa: E402
                                                TETO_DO_TEXTO_CURTO, conferir, mensagem_de_renovacao)
from app.services.multicalculo.renovacao import NaoEncontrada  # noqa: E402
from dubles import mundo_da_proposta as M  # noqa: E402
from dubles.banco_multicalculo import BancoU1  # noqa: E402
from test_spec130a_o_fio import CHROME, ordem_das_opcoes, texto_visivel  # noqa: E402

BASE = "https://app.exemplo.test"
TABELAS_DO_HUB = ("artifacts", "artifact_versions", "artifact_renders", "artifact_shares", "artifact_events")
CONTRATO = json.loads((BACKEND / "tests" / "fixtures" / "proposta" / "modelo_contrato.json").read_text(encoding="utf-8"))

DONO = "d0d00000-0000-4000-8000-00000000d0d0"            # o comercial DONO da apólice
PESSOA = "c0c00000-0000-4000-8000-00000000c0c0"          # quem clica "Ver apresentação"
RENOVACAO = "ae000000-0000-4000-8000-00000000a001"
WHATS_DONO = "5548988880001"                             # o "Meu WhatsApp de trabalho" do dono
WHATS_CORRETORA = "5548999990002"                        # a integração de atendimento da corretora (beta)
FONE_DO_CLIENTE = "48977776666"                          # vem no envelope da InfoCap — NUNCA pode chegar à página
NOSNUM = "900001"
SEGURADORA_DE_HOJE = "Porto"                             # 📊 a 11ª (a MAIS cara) de 11 no quadro da beta (RT-B1)
PREMIO_DE_HOJE = 7900.0
HOJE = date.today()
VENCE = HOJE + timedelta(days=7)


class Banco131B(BancoU1):
    """A CHECK de `multicalculo_calculos.opcao` como a 20261013_01 a deixou (as opções da renovação entram)."""

    def _travas(self, tabela, nova, velha):
        if tabela == "multicalculo_calculos" and nova.get("opcao") in ("anterior", "franquia_reduzida"):
            return super()._travas(tabela, dict(nova, opcao="padrao"), velha)
        return super()._travas(tabela, nova, velha)


def _derivar(m, base, opcao, fator, mexe):
    """Um cálculo da renovação a partir do `anterior` (o robô o grava assim: outra versão no MESMO negócio)."""
    calcs = m.banco.linhas("multicalculo_calculos")
    novo = dict(base, id=str(uuid.uuid4()), opcao=opcao, origem_calculo_id=base["id"],
                versao=max(c["versao"] for c in calcs if c["company_id"] == base["company_id"]) + 1)
    m.banco.semear("multicalculo_calculos", novo)
    for o in [o for o in m.banco.linhas("multicalculo_ofertas") if o["calculo_id"] == base["id"]]:
        x = copy.deepcopy(o)
        x.update(id=str(uuid.uuid4()), calculo_id=novo["id"], premio_total=round(o["premio_total"] * fator, 2))
        x["premio_mensal"] = round(x["premio_total"] / 12, 2)
        for p in x.get("parcelamentos") or []:
            p["primeira_parcela"] = round(p["primeira_parcela"] * fator, 2)
            p["demais_parcelas"] = round(p["demais_parcelas"] * fator, 2)
        mexe(x)
        m.banco.semear("multicalculo_ofertas", x)


def _franquia_reduzida(x):
    if x.get("franquia_valor"):
        x["franquia_valor"] = round(float(x["franquia_valor"]) / 2, 2)
        x["franquia_tipo"] = "Reduzida"


def _pequenos_reparos(x):
    x.setdefault("coberturas", {})["reparoRapido"] = True


def mundo(monkeypatch, *, whats_do_dono=WHATS_DONO, confirmado=True, dono_da_corretora=True,
          sem_numero_da_corretora=False, seguradora=SEGURADORA_DE_HOJE, estado="calculada"):
    """A renovação da 131-A pronta para apresentar: o pedido do canário (a parte da corretora beta) com o cálculo
    `anterior` (+ franquia reduzida e completa+), a linha de `renovacoes`, o dono na equipe e a outra corretora (alfa)
    no MESMO banco."""
    monkeypatch.setenv("PUBLIC_APP_URL", BASE)
    monkeypatch.setattr(M, "BancoU1", Banco131B)
    m = M.montar_mundo(monkeypatch, solicitante="beta")
    ped = next(p for p in m.banco.linhas("multicalculo_pedidos") if p["id"] == m.pedido_id)
    ped["servico"] = "renovacao"
    pad = next(c for c in m.banco.linhas("multicalculo_calculos") if c["opcao"] == "padrao" and c["company_id"] == m.beta)
    pad["opcao"] = "anterior"
    _derivar(m, pad, "franquia_reduzida", 1.05, _franquia_reduzida)
    _derivar(m, pad, "completa_mais", 1.08, _pequenos_reparos)
    if sem_numero_da_corretora:
        for i in m.banco.linhas("integrations"):
            if i["company_id"] == m.beta and i["purpose"] == "attendance":
                i["is_active"] = False
        for b in m.banco.linhas("brand_profiles"):
            if b["company_id"] == m.beta:
                b["contact"] = {}
    m.banco.semear("users_v2", {"id": DONO, "first_name": "Bruna Ficticia"})
    m.banco.semear("users_v2", {"id": PESSOA, "first_name": "Caio"})
    m.banco.semear("company_members", {
        "user_id": DONO, "company_id": m.beta if dono_da_corretora else m.alfa, "status": "active",
        "whatsapp_trabalho_e164": ("+" + whats_do_dono) if whats_do_dono else None,
        "whatsapp_trabalho_confirmado_em": "2026-10-12T10:00:00+00:00" if confirmado else None})
    m.banco.semear("company_members", {"user_id": PESSOA, "company_id": m.beta, "status": "active"})
    m.banco.semear("renovacoes", {
        "id": RENOVACAO, "company_id": m.beta, "sistema": "infocap", "codfil": 1, "nosnum": NOSNUM,
        "fimvig": VENCE.isoformat(), "ramo_sigla": "AUTO", "seguradora_atual": seguradora,
        "premio_atual": PREMIO_DE_HOJE, "cliente_nome_curto": "Ana", "documento_mascarado": "***.***.***-12",
        "dono_user_id": DONO, "estado": estado, "pedido_id": m.pedido_id, "versao": 1})
    return m


def historico(anos_atras=3, *, quebrado=False):
    """O envelope de `/documento` como a InfoCap o devolve (📊 12/10: `documento[1]` + `historico[]`), com o TELEFONE
    do cliente no meio — a página nunca pode levá-lo. `anos_atras` = o início da apólice mais antiga da cadeia."""
    ini_mais_antiga = date(HOJE.year - anos_atras, HOJE.month, 1) - timedelta(days=1)
    elos = [{"nosnum": "800001", "tipdoc": "A", "inivig": (VENCE - timedelta(days=365)).isoformat(),
             "nosnum_ren": "700001", "fone": FONE_DO_CLIENTE},
            {"nosnum": "700001", "tipdoc": "A", "inivig": ini_mais_antiga.isoformat(), "nosnum_ren": ""}]
    if quebrado:
        elos = elos[1:]                          # a apólice anterior NÃO está no histórico: sem prova
    resposta = {"header": {}, "documento": [{"nosnum": NOSNUM, "tipdoc": "A", "nosnum_ren": "800001",
                                             "inivig": (VENCE - timedelta(days=365)).isoformat(),
                                             "telefone": FONE_DO_CLIENTE}],
                "historico": elos}
    return lambda cid, codfil, nosnum: copy.deepcopy(resposta)


def _falha(*_a):
    raise RuntimeError("InfoCap fora")


def _publicar(m, company_id=None, **kw):
    kw.setdefault("historico", historico())
    return asyncio.run(P.publicar_renovacao(company_id or m.beta, RENOVACAO, pessoa=PESSOA, db=m.db, base_url=BASE,
                                            **kw))


def _servido(m, token):
    s = ArtifactService(m.banco.visao("rota-publica")).abrir_compartilhado(token, user_agent=CHROME)
    assert s, "o link não abriu"
    return s["html"]


def _texto(doc):
    return texto_visivel(doc)


def _h1(doc):
    return texto_visivel(re.search(r"<h1>(.*?)</h1>", doc, re.S).group(1))


def _dock(doc):
    m = re.search(r'<div class="dock">(.*?)</div><p class="dock-note">', doc, re.S)
    return m.group(1) if m else ""


# =====================================================================================================================
# (1) a página servida: hero com o vencimento, hoje × renovação, "Sua renovação" em 1º, nunca "a melhor das N"
# =====================================================================================================================
def test_a_pagina_servida_de_renovacao(monkeypatch):
    m = mundo(monkeypatch)
    r = _publicar(m)
    assert r["url"] == f"{BASE}/r/{r['token']}"
    doc = _servido(m, r["token"])
    txt = _texto(doc)
    vence = VENCE.strftime("%d/%m/%Y")

    # o hero: o VENCIMENTO é o motivo da página
    # §9.3 (conserto K1, laudo de design 7): o vencimento numa linha PRÓPRIA do título, sem o "·" colado
    assert _h1(doc).startswith("Ana, a renovação do seu ") and _h1(doc).endswith(f"está pronta vence em {vence}")
    assert re.search(r'<span class="vence">vence em ', doc) and "· vence em" not in doc
    # 🔴 mutação 1: a 1ª é a "Sua renovação" (a seguradora de HOJE, a mais cara do quadro) — nunca "a melhor das N"
    assert ordem_das_opcoes(doc)[0] == "sua_renovacao"
    assert texto_visivel(re.search(r'<span class="badge b1">(.*?)</span>', doc).group(1)) == "Sua renovação"
    assert re.search(r'<p class="insurer">Porto', doc)
    for proibida in ("a melhor das", "a melhor opção", "Mais em conta", "Recomendada", "Comparação independente",
                     "O que é o", "Onde cada opção cai", "corretoras parceiras", "cliente desde", "No banco ou na "
                     "cooperativa", "Outras seguradoras não ficaram melhores"):
        assert proibida not in txt, proibida
    assert 'class="duel' not in doc and 'class="regua' not in doc and "no Google" not in txt
    # o seu seguro hoje × a renovação: seguradora, quanto pagou, o que mudou em R$ e %
    secao = re.search(r'<section class="s" aria-labelledby="h-hoje">(.*?)</section>', doc, re.S).group(1)
    hoje = texto_visivel(secao)
    assert "O seu seguro hoje × a renovação" in hoje and "7.900,00" in hoje
    assert re.search(r'<span class="hl">Hoje</span><b>Porto</b>', secao)
    # §9.3 (conserto K1, laudo de design 2): "7%" sem espaço, como o "100%" da página
    assert re.search(r"O que mudou: R\$ [\d.]+ a mais por ano \(\+\d+%\); na mesma seguradora\.", hoje), hoje
    # os cartões: "por que recomendamos" em cada um; a franquia reduzida e a completa+ da MESMA seguradora
    ids = ordem_das_opcoes(doc)
    assert ids == ["sua_renovacao", "franquia_reduzida", "mais_completa"]
    # §9.3 (laudo de design 132-B, R2): "Por que recomendamos" só no cartão que a página propõe; os outros são
    # alternativas ("Por que considerar") — antes os três diziam "recomendamos"
    assert doc.count("<h3>Por que recomendamos</h3>") == 1 and doc.count("<h3>Por que considerar</h3>") == 2
    # R3: a MESMA nota nos três (diferença < 3) sai dos cartões; R4: sem "Tipo na seguradora" (as duas franquias
    # diferentes eram "reduzida"); R5: a SUSEP no topo, discreta — nunca um número solto no "Quem cuida"
    notas = [o.get("nota") for o in r["modelo"]["opcoes"] if o.get("nota") is not None]
    assert ('class="field"' in doc) == (bool(notas) and max(notas) - min(notas) >= 3)
    assert "Tipo na seguradora" not in txt and "registro na SUSEP" not in txt
    topo = texto_visivel(re.search(r'<header class="wrap top">(.*?)</header>', doc, re.S).group(1))
    assert topo.startswith("Corretora de seguros") or "Corretora de seguros" in topo
    assert PH.AP.FRASE_SEM_ORDEM not in txt
    assert "pequenos reparos" in txt and "Mostrar só o que muda" in txt
    # a relação: o DONO (primeiro nome), "renova com a gente há N anos" com PROVA (3 elos medidos no dublê)
    assert "Quem cuida de você" in txt and "Bruna" in txt and "Bruna Ficticia" not in txt
    assert "Você renova com a gente há 3 anos." in txt
    assert "Quem cuida é a " in txt and "não um 0800" in txt
    # a FAQ de RENOVAÇÃO
    for p in ("Por que o preço da renovação mudou?", "E o meu bônus?", "Posso mudar a franquia?",
              "E se eu não renovar?", "Dá para parcelar?"):
        assert p in txt, p
    # todas as seguradoras: RECOLHIDAS (nenhum `open`)
    assert re.search(r'<details class="line todas" id="todas">', doc) and "Todas as seguradoras que cotamos" in txt
    # o dock: "Quero renovar" e "Tirar uma dúvida"; "Salvar PDF" = imprimir
    assert "Quero renovar" in txt and "Tirar uma dúvida" in txt and "Salvar como PDF" in txt
    # nada de comissão (G3) nem o script trocado (o hash da CSP é o da constante)
    assert "17,37" not in doc and "17.37" not in doc and f"<script>{PH.SCRIPT_DA_PROPOSTA}</script>" in doc
    # a prévia não fala de ranking nem de dado pessoal
    assert re.search(r'og:title" content="A renovação do seu seguro: Porto por R\$ [\d.]+,\d\d ao ano"', doc)


def test_a_ordem_da_renovacao_na_comparacao_nunca_a_economica_nem_a_minima(monkeypatch):
    """D-131-22: a comparação PURA — "Sua renovação" em 1º mesmo mais cara; econômica e mínima nunca (nem com
    `incluir_minima`); a seguradora de hoje fora do quadro → "Recomendada", nunca "Sua renovação" (J-B2)."""
    dados = M.dados_do_canario()
    est = copy.deepcopy(dados["estados"])
    for e in est:
        if e["opcao"] == "padrao":
            e["opcao"] = "anterior"
    cfg = C.config_da_renovacao(None, est)
    assert cfg["calculo_por_papel"]["completa"] == "anterior"
    q = C.comparar(dados["ofertas"], dados["eventos"], estados=est, config=cfg)
    beta = dados["corretoras"]["corretora_b"]
    ops = C.opcoes(q, situacao="renovacao", apolice_atual={"seguradora": "Porto"}, config=cfg, corretora=beta,
                   incluir_minima=True)
    assert ops[0]["id"] == "sua_renovacao" and ops[0]["seguradora"] == "Porto"
    assert ops[0]["premio_anual"] == max(r["premio_anual"] for r in q.ranking("anterior", beta))   # a MAIS cara
    assert not {"mais_em_conta", "recomendada"} & {o["id"] for o in ops}
    assert all(o["por_que"] for o in ops)
    fora = C.opcoes(q, situacao="renovacao", apolice_atual={"seguradora": "Seguradora Que Nao Cotou"}, config=cfg,
                    corretora=beta)
    assert fora[0]["id"] == "recomendada" and "sua_renovacao" not in [o["id"] for o in fora]
    # CONTROLE: fora da renovação a regra da 130-A segue (a menor completa em 1º, RT-B1)
    cot = C.opcoes(q, situacao="novo_com_apolice", apolice_atual={"seguradora": "Porto"}, config=cfg, corretora=beta)
    assert cot[0]["id"] == "recomendada" and cot[0]["premio_anual"] == q.ranking("anterior", beta)[0]["premio_anual"]


def test_a_seguradora_de_hoje_fora_do_quadro_vira_recomendada_na_pagina(monkeypatch):
    m = mundo(monkeypatch, seguradora="Seguradora Que Nao Cotou")
    doc = _servido(m, _publicar(m)["token"])
    txt = _texto(doc)
    assert ordem_das_opcoes(doc)[0] == "recomendada" and "Sua renovação" not in txt
    assert "a melhor das" not in txt and "troca de Seguradora Que Nao Cotou para" in txt


# =====================================================================================================================
# (2) "N anos" SÓ com prova (BLOCO 0 B2, CDC art. 37)
# =====================================================================================================================
@pytest.mark.parametrize("busca", [_falha, historico(quebrado=True), historico(anos_atras=0),
                                   lambda *a: {"documento": [{"nosnum": NOSNUM, "nosnum_ren": ""}]},
                                   lambda *a: None],
                         ids=["infocap_fora", "elo_sem_a_anterior", "menos_de_1_ano", "sem_elo", "vazio"])
def test_sem_prova_a_frase_nao_aparece(monkeypatch, busca):
    m = mundo(monkeypatch)
    r = _publicar(m, historico=busca)
    txt = _texto(_servido(m, r["token"]))
    assert "renova com a gente" not in txt and "cliente desde" not in txt.lower()
    assert "anos" not in (r["modelo"]["renovacao"])


def test_anos_de_renovacao_conta_so_os_elos_provados():
    hoje = date(2026, 10, 13)
    env = {"documento": [{"nosnum": "3", "nosnum_ren": "2", "inivig": "2025-10-20"}],
           "historico": [{"nosnum": "2", "tipdoc": "A", "inivig": "2024-10-20", "nosnum_ren": "1"},
                         {"nosnum": "1", "tipdoc": "A", "inivig": "2022-09-01", "nosnum_ren": "0"}]}
    assert P.anos_de_renovacao(env, nosnum="3", hoje=hoje) == 4
    ciclo = copy.deepcopy(env)
    ciclo["historico"][1]["nosnum_ren"] = "3"                      # cadeia circular: para, não trava
    assert P.anos_de_renovacao(ciclo, nosnum="3", hoje=hoje) == 4
    endosso = copy.deepcopy(env)
    endosso["historico"][0]["tipdoc"] = "E"                         # endosso não é a apólice anterior
    assert P.anos_de_renovacao(endosso, nosnum="3", hoje=hoje) is None
    assert P.anos_de_renovacao(env, nosnum="999", hoje=hoje) is None   # a apólice nem está no envelope


# =====================================================================================================================
# (3) "Quero renovar": o DONO confirmado → a corretora → sem botão (D-131-42)
# =====================================================================================================================
def test_quero_renovar_vai_ao_dono_com_whatsapp_confirmado(monkeypatch):
    m = mundo(monkeypatch)
    r = _publicar(m)
    doc = _servido(m, r["token"])
    dock = _dock(doc)
    assert f"https://wa.me/{WHATS_DONO}?text=" in dock and WHATS_CORRETORA not in dock
    assert "Abre a conversa com Bruna no WhatsApp" in _texto(doc)
    for o in r["modelo"]["opcoes"]:          # o redirecionamento do `?fechar=` (o que o route.ts usa)
        d = PH.destino_do_fechar(r["modelo"], o["id"])
        assert d["destino"].startswith(f"https://wa.me/{WHATS_DONO}?text=") and "Quero%20renovar" in d["destino"]
    assert r["modelo"]["renovacao"]["fechar_com"] == "dono"


@pytest.mark.parametrize("caso", ["nao_confirmado", "sem_numero", "de_outra_corretora"])
def test_sem_dono_confirmado_o_quero_renovar_vai_a_corretora(monkeypatch, caso):
    m = mundo(monkeypatch, confirmado=caso != "nao_confirmado", whats_do_dono=None if caso == "sem_numero" else WHATS_DONO,
              dono_da_corretora=caso != "de_outra_corretora")
    r = _publicar(m)
    doc = _servido(m, r["token"])
    assert f"wa.me/{WHATS_CORRETORA}?text=" in _dock(doc) and WHATS_DONO not in doc
    assert r["modelo"]["renovacao"]["fechar_com"] == "corretora"
    if caso == "de_outra_corretora":         # o dono que não é DESTA corretora nem é nomeado (CLAUDE.md §7)
        assert "Bruna" not in _texto(doc)


def test_sem_numero_nenhum_publica_sem_botao_e_diz_o_caminho(monkeypatch):
    m = mundo(monkeypatch, whats_do_dono=None, sem_numero_da_corretora=True)
    r = _publicar(m)                         # D-131-42: NÃO recusa (a 130-A recusaria com SemCanalDeFechamento)
    doc = _servido(m, r["token"])
    txt = _texto(doc)
    assert 'class="dock"' not in doc and "wa.me/" not in doc and "Quero renovar" not in txt
    assert "responda a mensagem em que recebeu este link" in txt
    assert r["modelo"]["cta"] is None and r["modelo"]["renovacao"]["fechar_com"] == "nenhum"
    assert "pelo WhatsApp" not in txt        # nenhuma frase promete um WhatsApp que não existe


# =====================================================================================================================
# duas corretoras, PII e as recusas
# =====================================================================================================================
def test_outra_corretora_nao_le_a_renovacao_e_nada_e_gravado(monkeypatch):
    m = mundo(monkeypatch)
    with pytest.raises(NaoEncontrada):
        _publicar(m, company_id=m.alfa)
    assert all(m.banco.linhas(t) == [] for t in TABELAS_DO_HUB)
    r = _publicar(m)                         # CONTROLE: a dona publica
    arts = m.banco.linhas("artifacts")
    assert len(arts) == 1 and arts[0]["company_id"] == m.beta
    assert arts[0]["subject_ref"]["renovacao_id"] == RENOVACAO and arts[0]["subject_ref"]["publicada_por"] == PESSOA
    assert r["versao"] == 1 and _publicar(m)["versao"] == 2 and len(m.banco.linhas("artifacts")) == 1


def test_nenhum_telefone_do_cliente_na_pagina_no_hub_nem_na_mensagem(monkeypatch):
    m = mundo(monkeypatch)
    r = _publicar(m)
    doc = _servido(m, r["token"])
    msg = mensagem_de_renovacao(m.banco.linhas("renovacoes")[0], r, pessoa={"primeiro_nome": "Caio"})
    gravado = json.dumps({t: m.banco.linhas(t) for t in TABELAS_DO_HUB}, ensure_ascii=False, default=str)
    for onde, texto in (("html", doc), ("hub", gravado), ("modelo", json.dumps(r["modelo"], ensure_ascii=False)),
                        ("mensagem", json.dumps(msg, ensure_ascii=False))):
        assert FONE_DO_CLIENTE not in texto, onde
    # CONTROLE: o dublê da InfoCap TEM o telefone (a varredura pode falhar)
    assert FONE_DO_CLIENTE in json.dumps(historico()("x", 1, NOSNUM))


@pytest.mark.parametrize("estado", ["listada", "pendente", "calculando"])
def test_sem_calculo_nao_ha_o_que_apresentar(monkeypatch, estado):
    m = mundo(monkeypatch, estado=estado)
    with pytest.raises(P.PropostaImpossivel):
        _publicar(m)
    assert all(m.banco.linhas(t) == [] for t in TABELAS_DO_HUB)


# =====================================================================================================================
# a mensagem de RENOVAÇÃO (D-MC-74 ≤ 2 opções · BLOCO 0 B1 ≤ 500 no wa.me)
# =====================================================================================================================
def test_a_mensagem_de_renovacao(monkeypatch):
    m = mundo(monkeypatch)
    r = _publicar(m)
    item = m.banco.linhas("renovacoes")[0]
    msg = mensagem_de_renovacao(item, r, pessoa={"user_id": PESSOA, "primeiro_nome": "Caio"})
    assert set(msg) == {"texto", "texto_curto", "link"} and msg["link"] == r["url"]
    t = msg["texto"]
    assert t.startswith("Olá, Ana! Aqui é Caio, da ") and f"vence em {VENCE.strftime('%d/%m/%Y')}" in t
    assert t.index("*Sua renovação:* Porto") < t.index("*Franquia reduzida:*") and "*Mais completa:*" not in t
    assert re.search(r"_Hoje você paga R\$ 7\.900: R\$ [\d.]+ a mais por ano\._", t)
    assert r["url"] in t and t.rstrip().endswith("Caio · Vega Corretora Ficticia")
    assert len(t) <= TETO_DE_CARACTERES and conferir([t])["proibidas"] == [] and "a melhor das" not in t
    curto = msg["texto_curto"]
    assert len(curto) <= TETO_DO_TEXTO_CURTO and r["url"] in curto and "Porto" in curto
    # um user_id NÃO é nome: a mensagem não assina com ele
    sem_nome = mensagem_de_renovacao(item, r, pessoa=PESSOA)
    assert PESSOA not in sem_nome["texto"] and "Quem fala é a Vega Corretora Ficticia." in sem_nome["texto"]


def test_o_texto_curto_cabe_no_wa_me_mesmo_com_nomes_e_link_compridos(monkeypatch):
    m = mundo(monkeypatch)
    r = _publicar(m)
    longo = dict(r, url=r["url"] + "?" + "x" * 380)
    modelo = copy.deepcopy(r["modelo"])
    modelo["anfitria"]["nome"] = "Corretora " + "Muito " * 30 + "Comprida"
    msg = mensagem_de_renovacao({}, dict(longo, modelo=modelo), pessoa="Caio")
    assert len(msg["texto_curto"]) <= TETO_DO_TEXTO_CURTO and longo["url"] in msg["texto_curto"]
    assert len(msg["texto"]) > 0 and all(f not in msg["texto"].lower() for f in FRASES_PROIBIDAS)


# =====================================================================================================================
# três páginas, três momentos (D-131-40): a COTAÇÃO e o CANAL não mudaram
# =====================================================================================================================
@pytest.mark.parametrize("situacao", ["novo_sem_apolice", "novo_com_apolice"])
def test_a_pagina_da_cotacao_nao_mudou(situacao):
    modelo = dict(copy.deepcopy(CONTRATO), situacao=situacao)
    doc = PH.render_proposta(modelo)
    txt = texto_visivel(doc)
    assert "a melhor das" in _h1(doc) and "Quero fechar" in txt and "Por que recomendamos" in txt
    assert '<section class="s" aria-labelledby="h-all"><h2 id="h-all">Todas as seguradoras que cotamos</h2>' in doc
    for so_da_renovacao in ("Quero renovar", "O seu seguro hoje", "renova com a gente", "Dúvidas sobre a renovação",
                            "Quem cuida de você", "Salvar como PDF", "responda a mensagem"):
        assert so_da_renovacao not in txt, so_da_renovacao
    assert PH.previa_do_modelo(modelo)["titulo"].startswith("Sua proposta de seguro")


def test_a_pagina_do_canal_nao_mudou():
    modelo = dict(copy.deepcopy(CONTRATO), origem="canal", situacao="renovacao")   # nem com situação de renovação
    txt = texto_visivel(render_proposta_do_canal(modelo))
    for so_da_renovacao in ("Quero renovar", "O seu seguro hoje", "renova com a gente", "Dúvidas sobre a renovação"):
        assert so_da_renovacao not in txt, so_da_renovacao
    assert PH.e_renovacao(modelo) is False
