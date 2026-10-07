# -*- coding: utf-8 -*-
"""SPEC-130-A.1 · CONSERTO ÚNICO — os achados do juiz e do red team (07/10), cada um com o guarda que fica VERMELHO
com o defeito reintroduzido e uma linha de controle.

  1. (juiz B1 + red B2) o volume e o tempo contam SÓ as opções do pedido — o recálculo (`ajuste`) fica fora
  2. (red B1) A COSTURA: pedido do canal COM a mínima → `montar_proposta` → `mensagem_para` → os balões dizem
     "sem carro reserva" (a página diz "Sem carro reserva"); a "Mais em conta" é a mínima; a economia vai até ela
  3. (red P1) o NOME do selo vem do CANAL; a anfitriã só pode desligar o dela
  4. (red P2 / juiz 4) a trava de produto na régua: piso ≥ o do produto; passo em [mínimo, entrada − autônomo]
  5. (Founder) a parcela em destaque — migrou na SPEC-133-A F0 (§9.3): o MENOR valor de parcela, `12x de *R$ …*`

O fio é o REAL (porta → comparação → proposta → mensagem); a borda é só o banco DUBLÊ (CLAUDE.md §9.4).
🔬 LENTE: toda contagem é refeita AQUI, direto das linhas do dublê, sem `proposta` nem `comparacao`.
⛔ Nomes fictícios (CLAUDE.md §13.9). Rodar:
    cd backend && .venv/Scripts/python.exe -m pytest tests/test_spec130a1_conserto.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import copy
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from app.services.multicalculo import config as CFG  # noqa: E402
from app.services.multicalculo import mensagem as MSG  # noqa: E402
from app.services.multicalculo import negociacao as NEG  # noqa: E402
from app.services.multicalculo.proposta import montar_proposta  # noqa: E402
from dubles import mundo_da_proposta as M  # noqa: E402

LINK = "https://app.exemplo.test/r/tOkEn_ficticio_conserto_0123456789abcdef"
AGORA = datetime(2026, 10, 6, 11, 0, tzinfo=timezone.utc)
#: as OPÇÕES do pedido, escritas à mão (a lente não importa o código que ela confere)
OPCOES_DO_PEDIDO = ("padrao", "economica", "completa_mais", "minima")
SELO_INVENTADO = "Corretora Número 1 do Brasil"


def _montar(m, situacao="novo_sem_apolice", apolice=None):
    ctx: dict = {}
    modelo = asyncio.run(montar_proposta(m.dono, m.pedido_id, situacao, apolice, primeiro_nome="Mariana", db=m.db,
                                         agora=AGORA, _contexto=ctx))
    return modelo, ctx["cfg_sol"]


def _clonar_calculo(m, *, de_opcao, nova_opcao, corretora, fator, reserva="manter", origem=None, versao=9,
                    recebida_em=None):
    """Um cálculo novo no MESMO pedido com as ofertas do `de_opcao` daquela corretora × `fator` (o motor gravaria
    assim: cálculo → ofertas). `reserva` troca o `carroReserva` de cada oferta ("manter" = não mexe)."""
    base = next(c for c in m.banco.linhas("multicalculo_calculos")
                if c["opcao"] == de_opcao and c["company_id"] == corretora)
    novo = str(uuid.uuid4())
    m.banco.semear("multicalculo_calculos", {
        "id": novo, "pedido_id": m.pedido_id, "solicitante_company_id": m.dono, "company_id": corretora,
        "opcao": nova_opcao, "coberturas": {}, "status": "fechado", "negocio_ref": base.get("negocio_ref"),
        "versao": versao, "origem_calculo_id": origem, "prioridade": 0})
    precos = []
    for o in list(m.banco.linhas("multicalculo_ofertas")):
        if o["calculo_id"] != base["id"]:
            continue
        x = copy.deepcopy(o)
        x["id"] = str(uuid.uuid4())
        x["calculo_id"] = novo
        x["premio_total"] = round(float(o["premio_total"]) * fator, 2)
        if reserva != "manter" and isinstance(x.get("coberturas"), dict):
            x["coberturas"]["carroReserva"] = reserva
        if recebida_em is not None:
            x["recebida_em"] = recebida_em
        m.banco.semear("multicalculo_ofertas", x)
        precos.append(x["premio_total"])
    return novo, precos


def lente_cotacoes(m, *, com_ajuste=False):
    """Os preços que voltaram nos cálculos das OPÇÕES (o defeito: `com_ajuste=True`)."""
    op = {c["id"]: c["opcao"] for c in m.banco.linhas("multicalculo_calculos")}
    return sum(1 for o in m.banco.linhas("multicalculo_ofertas") if float(o.get("premio_total") or 0) > 0
               and (com_ajuste or op.get(o["calculo_id"]) in OPCOES_DO_PEDIDO))


def lente_falhas(m):
    """SPEC-133-A F0: pares DISTINTOS (cálculo das OPÇÕES × seguradora) com recusa — contados nas linhas do dublê."""
    op = {c["id"]: c["opcao"] for c in m.banco.linhas("multicalculo_calculos")}
    return len({(e["calculo_id"], e["seguradora_codigo"]) for e in m.banco.linhas("multicalculo_eventos")
                if op.get(e["calculo_id"]) in OPCOES_DO_PEDIDO and e["tipo"] == "seguradora_recusou"})


def lente_maior_de_todos(m):
    """O MAIOR preço de todos: a menor oferta de cada seguradora × corretora × opção que cobre o carro; o maior delas."""
    op = {c["id"]: c["opcao"] for c in m.banco.linhas("multicalculo_calculos")}
    menor = {}
    for o in m.banco.linhas("multicalculo_ofertas"):
        c = o["coberturas"]
        if (op.get(o["calculo_id"]) in OPCOES_DO_PEDIDO and float(o["premio_total"]) > 0
                and str(c.get("tipoPadronizado") or c.get("tipo") or "") == "Compreensiva" and c.get("casco") == 100
                and "assinatura" not in str(o["seguradora"]).lower()):
            k = (o["company_id"], o["seguradora_codigo"], op[o["calculo_id"]])
            menor[k] = min(menor.get(k, float("inf")), float(o["premio_total"]))
    return max(menor.values())


def _fiz(m, cfg, precos):
    return f"Fiz {cfg['canal']['volume']['base'] + precos + lente_falhas(m)} Cotações "


def _cobre_menos(texto):
    return [l for l in texto.splitlines() if l.startswith("_Cobre menos:")]


# =====================================================================================================================
# 1 · o volume e o tempo: só as opções do pedido
# =====================================================================================================================
def _negociar(m, vezes=6):
    """`vezes` tentativas da negociação = `vezes` recálculos (`ajuste`) da corretora inteira (o red team, A2)."""
    padrao_alfa = next(c for c in m.banco.linhas("multicalculo_calculos")
                       if c["opcao"] == "padrao" and c["company_id"] == m.alfa)["id"]
    n = 0
    for i in range(vezes):
        _, precos = _clonar_calculo(m, de_opcao="padrao", nova_opcao="ajuste", corretora=m.alfa,
                                    fator=0.99 - i / 100, origem=padrao_alfa, versao=10 + i)
        n += len(precos)
    return n


def test_1_o_recalculo_nao_e_cotacao_e_a_negociacao_nao_infla_o_volume(monkeypatch):
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    antes, cfg = _montar(m)
    assert antes["resumo"]["cotacoes_realizadas"] == lente_cotacoes(m) == 82        # 📊 canário d0bb15ba
    n_ajuste = _negociar(m)
    depois, cfg = _montar(m)
    texto = "\n".join(MSG.mensagem_para(depois, LINK, config=cfg))
    assert depois["resumo"]["cotacoes_realizadas"] == lente_cotacoes(m) == 82
    assert depois["resumo"]["seguradoras_com_preco"] == antes["resumo"]["seguradoras_com_preco"]
    assert depois["resumo"]["seguradoras_consultadas"] == antes["resumo"]["seguradoras_consultadas"]
    assert _fiz(m, cfg, 82) in texto                                  # SPEC-133-A F0: a base + o real
    # 🔴 CONTROLE: a conta com o recálculo é OUTRA (o guarda consegue ver a diferença) e não está no texto
    errado = lente_cotacoes(m, com_ajuste=True)
    assert errado == 82 + 22 + n_ajuste and _fiz(m, cfg, errado) not in texto


def test_1_o_tempo_vai_ate_a_ultima_oferta_das_opcoes_nunca_a_do_recalculo(monkeypatch):
    """📊 canário d0bb15ba: as opções terminaram em 495 s; o ajuste, em 648 s. O dublê reproduz a forma."""
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    criado = datetime.fromisoformat(m.banco.linhas("multicalculo_pedidos")[0]["criado_em"].replace("Z", "+00:00"))
    op = {c["id"]: c["opcao"] for c in m.banco.linhas("multicalculo_calculos")}
    for i, o in enumerate(m.banco.linhas("multicalculo_ofertas")):
        s = 648 if op[o["calculo_id"]] == "ajuste" else min(495, 400 + i)
        o["recebida_em"] = (criado + timedelta(seconds=s)).isoformat()
    modelo, cfg = _montar(m)
    assert modelo["resumo"]["tempo_do_calculo_s"] == 495
    texto = "\n".join(MSG.mensagem_para(modelo, LINK, config=cfg))
    # D-130A1-14 (§9.3 — a lição migra): no teto padrão 495 s não se mostra; nenhum dos dois tempos aparece
    assert "minutos" not in texto and "segundos" not in texto
    # com um teto acima dos DOIS (o do ajuste também caberia), o texto mostra o das opções — nunca o do recálculo
    largo = copy.deepcopy(cfg)
    largo["canal"]["tempo_exibido_ate_s"] = 1000
    texto = "\n".join(MSG.mensagem_para(modelo, LINK, config=largo))
    assert " Seguradoras em 8,3 minutos." in texto and "10,8 minutos" not in texto     # 495 s → 8,25 → 8,3


# =====================================================================================================================
# 2 · A COSTURA: o pedido do canal COM a mínima → a proposta → a mensagem
# =====================================================================================================================
FATOR_DA_MINIMA = 0.93          # 💭 a mínima do dublê = a econômica da anfitriã × 0,93 (o red team, A1)


def _com_minima(monkeypatch, reserva="Não contratar"):
    """O pedido do canal + um 4º cálculo `minima` da anfitriã. Devolve também a "Mais em conta" SEM a mínima (a
    econômica), para a lente saber qual preço a mínima tem de ter."""
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    sem, _cfg = _montar(m)
    economica = next(o for o in sem["opcoes"] if o["id"] == "mais_em_conta")
    _id, precos = _clonar_calculo(m, de_opcao="economica", nova_opcao="minima", corretora=m.alfa,
                                  fator=FATOR_DA_MINIMA, reserva=reserva, versao=4)
    return m, precos, economica


@pytest.mark.parametrize("reserva", ["Não contratar", 0, None],
                         ids=["nao_contratar", "zero", "seguradora_nao_informou"])
def test_2_costura_canal_com_minima_ate_os_baloes(monkeypatch, reserva):
    m, precos_minima, economica = _com_minima(monkeypatch, reserva)
    modelo, cfg = _montar(m)
    baloes = MSG.mensagem_para(modelo, LINK, config=cfg)
    texto = "\n".join(baloes)

    # a "Mais em conta" É a mínima: a mesma seguradora da econômica, com o preço do cálculo mínimo (contado por fora)
    barata = next(o for o in modelo["opcoes"] if o["id"] == "mais_em_conta")
    esperado = round(economica["premio_anual"] * FATOR_DA_MINIMA, 2)
    assert barata["seguradora"] == economica["seguradora"] and esperado in precos_minima
    assert round(barata["premio_anual"], 2) == esperado < economica["premio_anual"]
    # SPEC-133-A F0: a mínima é o MENOR de todos; sem preço atual, a economia vai do MAIOR de todos até ela
    assert modelo["resumo"]["economia"]["para"] == esperado
    assert modelo["resumo"]["economia"]["contra"] == "maior"
    de = lente_maior_de_todos(m)
    assert modelo["resumo"]["economia"]["de"] == round(de, 2)
    assert f"Você deve economizar até *R$ {int(de - esperado + 0.5):,}* por ano".replace(",", ".") in texto

    # a página e a mensagem dizem o MESMO: sem carro reserva — nunca "menos dias"
    assert "Sem carro reserva" in barata["o_que_muda"]
    assert barata["por_que_mais_barata"] and "sem carro reserva" in barata["por_que_mais_barata"]
    linhas = _cobre_menos(texto)
    assert len(linhas) == 1 and linhas[0].startswith("_Cobre menos: sem carro reserva")
    assert "menos dias de carro reserva" not in texto
    assert f"{barata['seguradora']} · *{MSG._brl(barata['premio_anual'])} por ano*" in baloes[1]

    # a contagem bate: a mínima é uma OPÇÃO do pedido (entra); 82 + as dela
    assert modelo["resumo"]["cotacoes_realizadas"] == lente_cotacoes(m) == 82 + len(precos_minima)
    assert _fiz(m, cfg, 82 + len(precos_minima)) in texto
    assert max(len(b) for b in baloes) <= MSG.TETO_POR_BALAO_DO_CANAL


def test_2_no_aperto_o_corte_que_sobra_e_o_sem_carro_reserva(monkeypatch):
    m, _, _ = _com_minima(monkeypatch)
    modelo, cfg = _montar(m)
    barata = next(o for o in modelo["opcoes"] if o["id"] == "mais_em_conta")
    assert MSG._cobre_menos_do_canal(barata, curto=True).startswith("_Cobre menos: sem carro reserva")


def test_2_controle_a_economica_com_dias_continua_menos_dias(monkeypatch):
    """CONTROLE: sem a mínima, a "Mais em conta" é a econômica (7 dias) — "menos dias", nunca "sem"."""
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    modelo, cfg = _montar(m)
    texto = "\n".join(MSG.mensagem_para(modelo, LINK, config=cfg))
    barata = next(o for o in modelo["opcoes"] if o["id"] == "mais_em_conta")
    assert "Sem carro reserva" not in barata["o_que_muda"]
    assert "menos dias de carro reserva" in barata["por_que_mais_barata"]
    assert "sem carro reserva" not in texto.lower()


def test_2_a_carteira_nao_pede_a_minima(monkeypatch):
    """A mesma mínima gravada num pedido da CARTEIRA não vira opção (só o canal a pede — D-130A1-05)."""
    m = M.montar_mundo(monkeypatch, solicitante="beta")
    _clonar_calculo(m, de_opcao="economica", nova_opcao="minima", corretora=m.beta, fator=0.5,
                    reserva="Não contratar", versao=4)
    modelo, _cfg = _montar(m)
    assert all("Sem carro reserva" not in o["o_que_muda"] for o in modelo["opcoes"])


# =====================================================================================================================
# 3 · o selo é do CANAL
# =====================================================================================================================
def _config_de(m, company_id):
    linha = next((c for c in m.banco.linhas("multicalculo_config") if c["company_id"] == company_id), None)
    if linha is None:
        m.banco.semear("multicalculo_config", {"company_id": company_id, "config": {}})
        linha = next(c for c in m.banco.linhas("multicalculo_config") if c["company_id"] == company_id)
    return linha["config"]


def test_3_a_anfitria_nao_renomeia_o_selo(monkeypatch):
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    _config_de(m, m.alfa)["canal"] = {"selo": {"nome": SELO_INVENTADO, "ligado": True}}
    modelo, cfg = _montar(m)
    texto = "\n".join(MSG.mensagem_para(modelo, LINK, config=cfg))
    assert SELO_INVENTADO not in texto and "Número 1" not in texto
    padrao = CFG.PADRAO_DO_PRODUTO["canal"]["selo"]["nome"]
    assert modelo["anfitria"]["selo"] == padrao and f"✅ {padrao}" in texto


def test_3_a_anfitria_pode_desligar_o_selo_dela(monkeypatch):
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    _config_de(m, m.alfa)["canal"] = {"selo": {"ligado": False}}
    modelo, cfg = _montar(m)
    texto = "\n".join(MSG.mensagem_para(modelo, LINK, config=cfg))
    assert "selo" not in modelo["anfitria"] and "Atenção" not in texto and "✅" not in texto


def test_3_controle_o_canal_e_quem_da_o_nome(monkeypatch):
    """CONTROLE: o MESMO nome, escrito na config do CANAL, aparece — o guarda acima consegue ficar vermelho."""
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    _config_de(m, m.canal)["canal"] = {"selo": {"nome": SELO_INVENTADO, "ligado": True}}
    modelo, cfg = _montar(m)
    texto = "\n".join(MSG.mensagem_para(modelo, LINK, config=cfg))
    assert f"✅ {SELO_INVENTADO}" in texto and "só aceite corretoras Número 1 do Brasil" in texto


# =====================================================================================================================
# 4 · a trava de produto na régua da margem
# =====================================================================================================================
@pytest.mark.parametrize("comissao", [
    {"piso": 3.0, "autonomo_minimo": 5.0},          # abaixo do piso do produto (o red team: desce sozinho até 3 %)
    {"piso": 9.5},                                   # meio ponto abaixo também volta
    {"passo_pp": 15.0},                              # passo maior que o trecho normal (pularia direto)
    {"passo_pp": 4.0},                               # entrada − autônomo = 3: um passo de 4 atravessa o trecho
    {"passo_pp": 0.01},                              # passo minúsculo (o juiz: 504 passos)
    {"passo_pp": 0.4},
], ids=["piso3", "piso9_5", "passo15", "passo4", "passo0_01", "passo0_4"])
def test_4_config_fora_da_trava_volta_ao_padrao(comissao):
    assert CFG.mesclar({"comissao": comissao})["comissao"] == CFG.PADRAO_DO_PRODUTO["comissao"]


def test_4_controle_dentro_da_trava_vale_a_da_corretora():
    pad = CFG.PADRAO_DO_PRODUTO["comissao"]
    trecho = pad["entrada"] - pad["autonomo_minimo"]
    for comissao in ({"piso": pad["piso"]}, {"piso": pad["piso"] + 1}, {"passo_pp": CFG.PASSO_PP_MINIMO},
                     {"passo_pp": trecho}):
        c = CFG.mesclar({"comissao": comissao})["comissao"]
        assert all(c[k] == v for k, v in comissao.items()), comissao
    # e o plano com o piso mais alto nunca desce abaixo dele
    alto = CFG.mesclar({"comissao": {"piso": pad["piso"] + 1}})
    oferta = {"id": "o1", "calculo_id": "c1", "seguradora": "Seguradora Ficticia", "seguradora_codigo": 4,
              "premio_total": 4000.0, "comissao_percentual": pad["entrada"], "coberturas": {}}
    niveis = [p.comissao_resultante for p in NEG.ordem_do_mais_barato(oferta, config=alto, fechamento=True)
              if p.alavanca == "comissao"]
    assert min(niveis) == pad["piso"] + 1


# =====================================================================================================================
# 5 · a parcela em destaque (§9.3 — a lição MIGRA, SPEC-133-A F0): o MENOR valor de parcela da oferta vencedora,
#     `12x de *R$ 341,00*` — o número em negrito, o "12x de" não; sem o total, sem "juros", sem o preço cheio
# =====================================================================================================================
def _parcelar_o_vencedor(m, vezes, primeira, demais):
    """Acrescenta à oferta da 1ª opção (a Youse padrão da anfitriã, 📊 4x sem juros) um parcelamento COM juros."""
    padrao_alfa = next(c for c in m.banco.linhas("multicalculo_calculos")
                       if c["opcao"] == "padrao" and c["company_id"] == m.alfa)["id"]
    o = next(o for o in m.banco.linhas("multicalculo_ofertas")
             if o["calculo_id"] == padrao_alfa and o["seguradora"] == "Youse")
    o["parcelamentos"] = list(o["parcelamentos"]) + [
        {"parcelas": vezes, "tipo_pagamento": 2, "primeira_parcela": primeira, "demais_parcelas": demais}]
    return o


def _vencedor(b1):
    return next(l for l in b1.splitlines() if l.startswith("*Quem cobra menos?*"))


def test_5_a_menor_parcela_em_destaque_pelo_caminho_real(monkeypatch):
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    o = _parcelar_o_vencedor(m, 12, 352.10, 341.00)
    modelo, cfg = _montar(m)
    rec = modelo["opcoes"][0]
    assert rec["seguradora"] == "Youse" and rec["parcelas"]["vezes"] == 12
    b1 = MSG.mensagem_para(modelo, LINK, config=cfg)[0]
    assert _vencedor(b1).endswith("com Youse · 12x de *R$ 341,00*")
    assert "932,64" not in b1 and "juros" not in b1 and "Total" not in b1 and "*12x" not in b1
    assert MSG._brl(o["premio_total"]) not in b1                                # o preço cheio fica nos cartões
    # o "12" é o que a oferta trouxe: com 10x, o destaque é 10x (nenhuma constante)
    m2 = M.montar_mundo(monkeypatch, solicitante="canal")
    _parcelar_o_vencedor(m2, 10, 400.0, 400.0)
    modelo2, cfg2 = _montar(m2)
    b1b = MSG.mensagem_para(modelo2, LINK, config=cfg2)[0]
    assert _vencedor(b1b).endswith("10x de *R$ 400,00*") and "12x" not in b1b


def test_5_controle_sem_parcelamento_maior_fica_o_sem_juros(monkeypatch):
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    modelo, cfg = _montar(m)
    b1 = MSG.mensagem_para(modelo, LINK, config=cfg)[0]
    assert _vencedor(b1).endswith("4x de *R$ 932,64*") and "R$ 3.730,56" not in b1


def test_5_a_parcela_em_destaque_e_pura():
    assert MSG._parcela_em_destaque({"premio_anual": 3600.0, "parcelas": {"vezes": 12, "valor": 330.0}}) == \
        "12x de *R$ 330,00*"
    assert MSG._parcela_em_destaque({"premio_anual": 3600.0, "parcelas": {"vezes": 12, "valor": 330.0},
                                     "parcelas_sem_juros": {"vezes": 6, "valor": 600.0}}) == "12x de *R$ 330,00*"
    assert MSG._parcela_em_destaque({"premio_anual": 3600.0}) is None
    assert MSG._parcela_em_destaque({"premio_anual": 3600.0, "parcelas": {"vezes": 1, "valor": 3600.0}}) is None
