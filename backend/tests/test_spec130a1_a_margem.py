# -*- coding: utf-8 -*-
"""SPEC-130-A.1 · F1 · U1+U2 — a MARGEM CORRIGIDA (D-MC-68 corrigida) e o MANUAL por contexto (D-130A1-07).

A palavra do Founder (06/10, 23h): "o agente PODE ir até 10 % de comissão SEM autorização humana, mas não direto —
aos poucos; e usar os últimos ~2 % como alavanca de fechamento: dizer que vai falar com a seguradora e voltar com um
desconto de + R$ XXX (nunca '2 %'), condicionado ao fechamento". A versão gravada antes (10 % só com o corretor
aprovando + concorrência declarada) estava ERRADA — os guardas abaixo ficam VERMELHOS se ela voltar.

Tudo PURO (o motor de verdade: `negociacao` + `config` + `manual_de_negociacao`). O fio pela porta, com o recálculo
enfileirado e devolvido, mora em `test_spec130a_a_negociacao.py::test_o_fio_do_fechamento_pela_porta_ate_a_frase`.
⛔ Dado sintético; nomes de SEGURADORA são os do Agger; nenhum nome de corretora (§13.9).
"""
from __future__ import annotations

import inspect
import re

import pytest

from app.services.multicalculo import manual_de_negociacao as MANUAL
from app.services.multicalculo import negociacao as N
from app.services.multicalculo.config import PADRAO_DO_PRODUTO, mesclar

COB = {"tipoPadronizado": "Compreensiva", "casco": 100, "carroReserva": "Carro reserva 15 dias", "vidros": "Completo",
       "assist24hs": "Completa"}
GRANDE = mesclar({"negociacao": {"max_tentativas_por_etapa": 50}})     # sem o teto, para ver o plano INTEIRO


def _o(seg, cod, comissao=15.0, premio=5000.0, **kw):
    return {"id": f"o-{cod}", "calculo_id": f"c-{cod}", "seguradora": seg, "seguradora_codigo": cod,
            "premio_total": premio, "comissao_percentual": comissao, "franquia_tipo": kw.get("franquia", "Reduzida"),
            "coberturas": kw.get("cob", COB)}


def _margem(passos):
    return [p for p in passos if p.alavanca in N.ALAVANCAS_DE_MARGEM]


# =====================================================================================================================
# G5 · passo a passo — nunca direto
# =====================================================================================================================
def test_degraus_descem_de_passo_em_passo_e_caem_exatamente_no_limite():
    assert N.degraus(15, 12, 1) == [14.0, 13.0, 12.0]
    assert N.degraus(12, 10, 1) == [11.0, 10.0]
    assert N.degraus(15, 12, 2) == [13.0, 12.0]                 # o último degrau cai NO limite, nunca o atravessa
    assert N.degraus(15, 12, 0.5) == [14.5, 14.0, 13.5, 13.0, 12.5, 12.0]
    assert N.degraus(12, 12, 1) == [] and N.degraus(11, 12, 1) == []
    with pytest.raises(ValueError):
        N.degraus(15, 12, 0)


def test_a_comissao_desce_um_passo_por_vez_e_sem_fechamento_para_no_autonomo():
    """🔴 GUARDA · mutação: `n = ate` em `degraus` (pular de 15 direto para 12) → VERMELHO."""
    bra = N.ordem_do_mais_barato(_o("Bradesco", 1))
    margem = _margem(bra)
    assert [p.ajuste.valor for p in margem] == [14.0, 13.0, 12.0]
    anterior = 15.0
    for p in margem:                                            # nenhum salto maior que `passo_pp`
        assert anterior - p.ajuste.valor <= PADRAO_DO_PRODUTO["comissao"]["passo_pp"] + 1e-9
        anterior = p.ajuste.valor
    assert not any(p.fechamento for p in bra)
    assert min(p.comissao_resultante for p in margem) == PADRAO_DO_PRODUTO["comissao"]["autonomo_minimo"]
    assert margem[0].descricao == "comissão da corretora de 15 % para 14 %"
    # conserto 130-A.1 (juiz 6): cada tentativa recalcula da ORIGEM — a descrição diz a origem real, não o degrau anterior
    assert margem[1].descricao == "comissão da corretora de 15 % para 13 %"
    assert all(p.descricao.startswith("comissão da corretora de 15 % para ") for p in margem)


def test_plano_sem_fechamento_nunca_tem_degrau_abaixo_do_autonomo():
    """🔴 GUARDA · mutação: o filtro `fechamento or not f` trocado por `True` → VERMELHO."""
    ofertas = [_o("Bradesco", 1, premio=4458.32), _o("Porto Seguro", 8, premio=4700.0), _o("Tokio", 11, premio=5000.0)]
    plano = N.planejar(ofertas, alvo=3000, config=GRANDE)
    assert plano["status"] == "planejado" and plano["tentativas"]
    assert all(t["comissao_resultante"] >= 12.0 for t in plano["tentativas"])
    assert not any(t["fechamento"] for t in plano["tentativas"])
    assert plano["fechamento_disponivel"] is True                # a última cartada está GUARDADA, e o agente sabe
    assert "precisa_aprovacao" not in plano


# =====================================================================================================================
# G5 · a alavanca de fechamento: 12 → 10 SEM aprovação humana, só com o cliente fechando, nunca abaixo do piso
# =====================================================================================================================
def test_fechamento_vai_ate_o_piso_sem_aprovacao_e_sem_concorrencia():
    """🔴 GUARDA · mutação: reintroduzir "10 % só com aprovação" (os degraus de fechamento nunca entram no plano
    sem uma trava humana: `if not f`) → VERMELHO."""
    ofertas = [_o("Bradesco", 1, premio=4458.32)]
    plano = N.planejar(ofertas, alvo=3000, config=GRANDE, fechamento=True)
    margem = [t for t in plano["tentativas"] if t["passo"]["alavanca"] == "comissao"]
    assert [t["passo"]["ajuste"]["valor"] for t in margem] == [14.0, 13.0, 12.0, 11.0, 10.0]
    assert [t["fechamento"] for t in margem] == [False, False, False, True, True]
    assert "precisa_aprovacao" not in plano and all("precisa_aprovacao" not in t for t in plano["tentativas"])
    assert plano["fechamento_disponivel"] is False               # já está em uso
    # a trava humana SAIU da interface (a regra vencida não volta por um parâmetro esquecido)
    for f in (N.ordem_do_mais_barato, N.planejar, N.proxima_etapa):
        params = inspect.signature(f).parameters
        assert "aprovado_pelo_corretor" not in params and "concorrencia_declarada" not in params
        assert "fechamento" in params


def test_nunca_abaixo_do_piso_da_corretora():
    piso_alto = mesclar({"comissao": {"piso": 11.0}})
    valores = [p.ajuste.valor for p in _margem(N.ordem_do_mais_barato(_o("Bradesco", 1), config=piso_alto,
                                                                      fechamento=True))]
    assert valores == [14.0, 13.0, 12.0, 11.0] and min(valores) >= 11.0
    # já no piso: nenhuma margem; já em 12: só a alavanca (com fechamento) e nada sem ela
    assert _margem(N.ordem_do_mais_barato(_o("Bradesco", 1, comissao=10.0), fechamento=True)) == []
    assert _margem(N.ordem_do_mais_barato(_o("Bradesco", 1, comissao=12.0))) == []
    assert [p.id for p in _margem(N.ordem_do_mais_barato(_o("Bradesco", 1, comissao=12.0), fechamento=True))] == [
        "comissao:11.0", "comissao:10.0"]


def test_a_alavanca_vem_antes_dos_cortes_de_cobertura():
    """A decisão desta fatia: fechar SEM tirar cobertura — os degraus de fechamento vêm logo depois dos normais."""
    ids = [p.id for p in N.ordem_do_mais_barato(_o("Bradesco", 1), fechamento=True)]
    assert ids == ["comissao:14.0", "comissao:13.0", "comissao:12.0", "comissao:11.0", "comissao:10.0",
                   "franquia:normal", "carro_reserva:7 dias", "vidros:basico", "assistencia:basica"]


def test_nas_que_obedecem_desconto_a_mesma_regua_vale_para_o_desconto():
    porto = _margem(N.ordem_do_mais_barato(_o("Porto Seguro", 8)))
    assert [(p.alavanca, p.ajuste.valor, p.comissao_resultante) for p in porto] == [
        ("desconto", 1.0, 14.0), ("desconto", 2.0, 13.0), ("desconto", 3.0, 12.0)]
    porto_f = _margem(N.ordem_do_mais_barato(_o("Porto Seguro", 8), fechamento=True))
    assert [(p.ajuste.valor, p.fechamento) for p in porto_f] == [(1.0, False), (2.0, False), (3.0, False),
                                                                (4.0, True), (5.0, True)]


def test_o_passo_e_os_limites_vem_da_config():
    dois = mesclar({"comissao": {"passo_pp": 2.0}})
    assert [p.ajuste.valor for p in _margem(N.ordem_do_mais_barato(_o("Bradesco", 1), config=dois,
                                                                   fechamento=True))] == [13.0, 12.0, 10.0]
    outra = mesclar({"comissao": {"entrada": 14.0, "autonomo_minimo": 13.0, "piso": 12.0, "passo_pp": 0.5}})
    assert [(p.ajuste.valor, p.fechamento) for p in _margem(N.ordem_do_mais_barato(
        _o("Bradesco", 1, comissao=14.0), config=outra, fechamento=True))] == [
        (13.5, False), (13.0, False), (12.5, True), (12.0, True)]


def test_proxima_etapa_continua_passo_a_passo_e_o_fechamento_so_quando_pedido():
    oferta = dict(_o("Bradesco", 1, comissao=12.0, premio=4400.0), franquia_tipo="Normal",
                  coberturas=dict(COB, carroReserva="7 dias", vidros="Básico", assist24hs="Básica"))
    r = [{"calculo_id": "x", "passos": ["comissao:12.0", "franquia:normal"], "comissao_resultante": 12.0,
          "oferta": oferta}]
    sem = N.proxima_etapa(r, alvo=4000)
    assert sem["status"] == "sem_caminho" and sem["fechamento_disponivel"] is True
    com = N.proxima_etapa(r, alvo=4000, fechamento=True)
    assert com["status"] == "proxima_etapa"
    assert [t["passos"][-1] for t in com["tentativas"]] == ["comissao:11.0", "comissao:10.0"]
    assert all(t["fechamento"] for t in com["tentativas"])


# =====================================================================================================================
# G5 · a frase da alavanca — em REAIS, condicionada ao fechamento, nunca "%"
# =====================================================================================================================
_PROIBIDO_NA_FRASE = re.compile(r"%|comiss|percent|s[óo] hoje|corra|expira|urgente|[úu]ltima chance|agora ou",
                                re.IGNORECASE)


def test_texto_da_alavanca_em_reais_e_sem_percentual():
    """🔴 GUARDA · mutação: a frase com "%" → VERMELHO."""
    t = N.texto_da_alavanca(3730.56, 3418.16)
    assert t == ("Falei com a seguradora e consegui R$ 312,40 a menos no ano (fica R$ 3.418,16 por ano). "
                 "Vale se você fechar comigo.")
    c = N.texto_da_alavanca(4000, 2688, voz="canal")
    assert c.endswith("Vale se você fechar com a corretora.") and "R$ 1.312 a menos" in c and "R$ 2.688 por ano" in c
    for frase in (t, c, N.FRASE_DA_ALAVANCA):
        assert not _PROIBIDO_NA_FRASE.search(frase), frase
    assert N.reais(1312.999) == "R$ 1.312,99"                  # nunca arredonda a favor da corretora
    with pytest.raises(ValueError):
        N.texto_da_alavanca(3000, 3000)                         # sem diferença real, não há o que oferecer
    with pytest.raises(ValueError):
        N.texto_da_alavanca(3000, 3100)
    with pytest.raises(ValueError):
        N.texto_da_alavanca(3000, 2900, voz="robo")


def test_controle_o_guarda_da_frase_pega_o_que_deve():
    assert _PROIBIDO_NA_FRASE.search("consegui 2 % a menos")
    assert _PROIBIDO_NA_FRASE.search("baixei a minha comissão")
    assert _PROIBIDO_NA_FRASE.search("vale só hoje")
    assert not _PROIBIDO_NA_FRASE.search("consegui R$ 312 a menos no ano")


def test_escolher_traz_a_alavanca_com_os_dois_precos_do_recalculo():
    def r(passos, premio, com):
        return {"calculo_id": "x", "passos": passos, "comissao_resultante": com, "seguradora_codigo": 1,
                "premio_de_origem": 4500.0,
                "oferta": {"id": "o", "seguradora": "Bradesco", "seguradora_codigo": 1, "premio_total": premio}}
    res = [r(["comissao:12.0"], 4300.0, 12.0), r(["comissao:11.0"], 4180.0, 11.0), r(["comissao:10.0"], 4060.0, 10.0),
           r(["franquia:normal"], 3990.0, 15.0)]
    d = N.escolher(res, alvo=4100)
    assert d["escolhida"]["comissao_percentual"] == 10.0 and d["corta_cobertura"] == []    # sem cortar cobertura
    f = d["fechamento"]
    assert (f["preco_antes"], f["preco_depois"], f["diferenca"]) == (4300.0, 4060.0, 240.0)
    assert "R$ 240 a menos" in f["texto"]["corretora"] and f["texto"]["canal"].endswith("com a corretora.")
    # na margem normal não há alavanca; sem preço normal no lote, o antes é o da ORIGEM (também um preço real)
    assert N.escolher(res, alvo=4350)["fechamento"] is None
    so_fech = N.escolher([r(["comissao:12.0", "comissao:11.0"], 4180.0, 11.0)], alvo=4200)
    assert so_fech["fechamento"]["preco_antes"] == 4500.0


# =====================================================================================================================
# U2 · o MANUAL por contexto — a régua nova escrita com os números DA config
# =====================================================================================================================
def test_manual_regra_nova_com_os_numeros_da_config():
    m = MANUAL.montar()
    regra = m["limites"]["regra"]
    assert "1 pp por vez" in regra and "até 12 %" in regra and "10 %" in regra and "sem aprovação humana" in regra
    assert "aprovando" not in regra and "concorrência" not in regra                       # a regra vencida saiu
    assert m["limites"]["precisa_aprovacao_humana"] is False and m["limites"]["passo_pp"] == 1.0
    como = m["alavancas"][1]["como"]
    assert "de 15 % para 12 % sozinho, 1 pp por vez" in como and "alavanca de fechamento" in como
    assert "aprovando" not in como
    # (conserto 130-A.1: o piso nunca abaixo do do produto — a régua de exemplo sobe o piso em vez de descê-lo)
    outra = mesclar({"comissao": {"entrada": 16.0, "autonomo_minimo": 14.0, "piso": 11.0, "passo_pp": 0.5}})
    m2 = MANUAL.montar(outra)
    assert "0,5 pp por vez" in m2["limites"]["regra"] and "até 14 %" in m2["limites"]["regra"]
    assert "11 %" in m2["limites"]["regra"] and "12 %" not in m2["limites"]["regra"]
    assert m2["alavanca_de_fechamento"]["de"] == 14.0 and m2["alavanca_de_fechamento"]["ate"] == 11.0


def test_manual_carteira_e_canal():
    car, can = MANUAL.montar(contexto="carteira"), MANUAL.montar(contexto="canal")
    assert car["contexto"] == "carteira" and can["contexto"] == "canal"
    assert set(car["estrategias"]) == {"renovacao", "novo_com_apolice", "novo_sem_apolice"}
    assert set(can["estrategias"]) == {"canal"}
    est = can["estrategias"]["canal"]
    assert PADRAO_DO_PRODUTO["canal"]["nome"] in est["quando"] and "minima" in est["opcoes"]
    assert any("REAL" in item for item in est["mostra"])
    assert can["roteiro"][0].startswith("a PROVA primeiro") and "quem atende" in " ".join(can["roteiro"])
    # objeções na voz do comparador (nunca "a minha margem"); na carteira, a 1ª pessoa da corretora
    melhorar_can = next(o for o in can["objecoes"] if o["chave"] == "melhorar_preco")
    melhorar_car = next(o for o in car["objecoes"] if o["chave"] == "melhorar_preco")
    assert "minha" not in melhorar_can["resposta"] and "minha margem" in melhorar_car["resposta"]
    assert "minha margem" not in " ".join(i["resposta"] for i in can["faq"])
    # a alavanca de fechamento na voz de cada contexto, a frase sem número e sem "%"
    assert can["alavanca_de_fechamento"]["frase"].endswith("com a corretora.")
    assert car["alavanca_de_fechamento"]["frase"].endswith("comigo.")
    assert not _PROIBIDO_NA_FRASE.search(can["alavanca_de_fechamento"]["frase"])
    # a régua é a MESMA nos dois contextos
    assert car["limites"] == can["limites"] and car["alavancas"] == can["alavancas"]
    with pytest.raises(ValueError):
        MANUAL.montar(contexto="outro")


def test_follow_up_do_canal_vem_da_config():
    fu = MANUAL.montar(contexto="canal")["follow_up"]
    cfg = PADRAO_DO_PRODUTO["canal"]["follow_up"]
    assert fu["tempos"]["primeiro_apos_min"] == cfg["primeiro_apos_min"]
    assert fu["tempos"]["segundo_apos_h"] == cfg["segundo_apos_h"]
    assert len(fu["textos"]) == cfg["max_sem_resposta"] and all(t.rstrip().endswith("?") for t in fu["textos"])
    assert not any(_PROIBIDO_NA_FRASE.search(t) for t in fu["textos"])
    um = MANUAL.montar(mesclar({"canal": {"follow_up": {"max_sem_resposta": 1}}}), contexto="canal")["follow_up"]
    assert len(um["textos"]) == 1                                # a corretora manda MENOS lembretes, nunca mais
    car = MANUAL.montar(contexto="carteira")["follow_up"]
    assert car["tempos"]["primeiro_apos_h"] == PADRAO_DO_PRODUTO["lembretes"]["primeiro_apos_h"]
