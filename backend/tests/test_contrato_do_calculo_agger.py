# -*- coding: utf-8 -*-
"""G3 — o leitor do Agger sobre as fixtures saneadas reproduz a tela (SPEC-128 U2).

📊 Números medidos pelo gerente (BLOCO 0 #3, script inline sobre o HAR, 04/10/2026)
e reconferidos aqui pelo leitor, sobre a ÚLTIMA rodada de cada gravação:

    R1: 22 ofertas (prêmio > 0) de 12 seguradoras · 27 itens em `resultados` (item ≠ oferta)
    R2: 21 ofertas de 11 seguradoras · 25 itens · 17 seguradoras consultadas

O TESTE DO FIO (`test_o_fio_do_bruto_ao_leitor`) atravessa bruto → gerador →
fixture → leitor; só roda onde o intake existe (a máquina do gerente) — o resto
lê SÓ fixture, nunca rede.
"""
from __future__ import annotations

import dataclasses
import json
import re
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from portal_worker.multicalculo import contrato as C  # noqa: E402
from portal_worker.multicalculo.leitor_agger import (  # noqa: E402
    eventos_do_calculo, eventos_entre, ler_rodada, numero, pedido_de_calcularv2,
)

FIX = BACKEND / "tests" / "fixtures" / "agger"
INTAKE = BACKEND.parent / "docs" / "intake" / "MULTICALCULO AGGER"


def _fixture(rotulo: str) -> dict:
    return json.loads((FIX / f"{rotulo}.json").read_text(encoding="utf-8"))


def _rodadas(rotulo: str):
    return [ler_rodada(r) for r in _fixture(rotulo)["calculos"][0]["rodadas"]]


# (rótulo, ofertas, seguradoras com oferta, itens em resultados, seguradoras consultadas)
ESPERADO = (("gravacao_r1", 22, 12, 27, 17), ("gravacao_r2", 21, 11, 25, 17))

# 📊 famílias da ÚLTIMA rodada, medidas pelo leitor em 04/10/2026
FAMILIAS_DA_ULTIMA = {
    "gravacao_r1": {"OFERTA": 12, "ACEITACAO": 2, "CREDENCIAL": 1, "INSTABILIDADE": 1, "PERMISSAO": 1},
    "gravacao_r2": {"OFERTA": 11, "ACEITACAO": 2, "CREDENCIAL": 1, "INSTABILIDADE": 2, "DADO": 1},
}
# 🔴 a DESCONHECIDA não fica escondida: o número EXATO e a mensagem que a produz
DESCONHECIDAS = {
    "gravacao_r1": set(),
    "gravacao_r2": set(),  # a renovação inválida virou DADO (D-128-02)
}


# 🔴 G5: as capturas AO VIVO (16 cálculos, 04/10) — toda resposta da ÚLTIMA rodada tem família; nenhuma
# DESCONHECIDA. Cada mensagem nova que aparecer no motor tem de ganhar regra, não sumir num balde.
@pytest.mark.parametrize("rotulo", ["vivo_conta_a", "vivo_conta_b"])
def test_vivo_toda_resposta_tem_familia(rotulo):
    fx = _fixture(rotulo)
    com_rodada = [c for c in fx["calculos"] if c["rodadas"]]
    assert com_rodada, rotulo
    soltas = []
    for c in com_rodada:
        ultima = ler_rodada(c["rodadas"][-1]["corpo"] if isinstance(c["rodadas"][-1], dict) and "corpo" in c["rodadas"][-1] else c["rodadas"][-1])
        soltas += [m for x in ultima.respostas if x.familia == C.DESCONHECIDA for m in x.mensagens]
        assert sum(1 for x in ultima.respostas if x.familia == C.OFERTA) > 0
    assert soltas == [], soltas


@pytest.mark.parametrize("rotulo,n_ofertas,n_segs,n_itens,n_consultadas", ESPERADO)
def test_ultima_rodada_reproduz_a_tela(rotulo, n_ofertas, n_segs, n_itens, n_consultadas):
    bruto = _fixture(rotulo)["calculos"][0]["rodadas"][-1]["corpo"]
    ultima = ler_rodada(bruto)
    assert len(ultima.respostas) == n_consultadas
    itens = sum(len(i.get("resultados") or []) for i in bruto)
    assert itens == n_itens                       # item ≠ oferta
    assert len(ultima.ofertas) == n_ofertas
    assert len({o.seguradora_codigo for o in ultima.ofertas}) == n_segs
    assert ultima.fechado is True
    assert ultima.por_familia() == FAMILIAS_DA_ULTIMA[rotulo]


@pytest.mark.parametrize("rotulo", ["gravacao_r1", "gravacao_r2"])
def test_desconhecida_nao_fica_escondida(rotulo):
    rodadas = _rodadas(rotulo)
    msgs = {m for r in rodadas for x in r.respostas if x.familia == C.DESCONHECIDA for m in x.mensagens}
    assert msgs == DESCONHECIDAS[rotulo]
    assert all(x.familia in C.FAMILIAS for r in rodadas for x in r.respostas)


@pytest.mark.parametrize("rotulo", ["gravacao_r1", "gravacao_r2"])
def test_oferta_nunca_carrega_segredo(rotulo):
    for r in _rodadas(rotulo):
        for o in r.ofertas:
            d = dataclasses.asdict(o)
            chaves = set()

            def anda(v):
                if isinstance(v, dict):
                    for k, s in v.items():
                        chaves.add(str(k).lower())
                        anda(s)
                elif isinstance(v, (list, tuple)):
                    for s in v:
                        anda(s)
                elif isinstance(v, str):
                    assert not re.search(r"https?://|\.pdf\b", v, re.I), "URL/PDF numa Oferta"
            anda(d)
            assert not (chaves & set(C.CHAVES_PROIBIDAS_NA_OFERTA))
            assert o.premio_total > 0
    campo = {f.name: f for f in dataclasses.fields(C.Oferta)}["comissao_percentual"]
    assert campo.metadata.get("interno") is True


@pytest.mark.parametrize("rotulo", ["gravacao_r1", "gravacao_r2"])
def test_eventos_nao_duplicam_e_o_tempo_da_primeira_oferta_existe(rotulo):
    rodadas = _rodadas(rotulo)
    for r in rodadas:
        assert eventos_entre(r, r) == []          # rodadas iguais → nada novo
    eventos = eventos_do_calculo(rodadas)
    novas = [e for e in eventos if e.tipo == C.NOVA_OFERTA]
    assert len(novas) == len(rodadas[-1].ofertas)
    assert sum(e.tipo == C.CONJUNTO_FECHADO for e in eventos) == 1
    # a lista repetida (cada rodada 2×) produz os MESMOS eventos
    dobrada = [r for r in rodadas for _ in (0, 1)]
    assert len(eventos_do_calculo(dobrada)) == len(eventos)
    # fora de ordem: eventos_do_calculo ordena por t_s
    assert len(eventos_do_calculo(list(reversed(rodadas)))) == len(eventos)
    t_primeira = novas[0].t_s
    assert t_primeira is not None and 0 < t_primeira < rodadas[-1].t_s
    assert rodadas[0].fechado is False


def test_rodada_atrasada_nao_narra_o_passado():
    rodadas = _rodadas("gravacao_r1")
    assert eventos_entre(rodadas[-1], rodadas[0]) == []


def test_bordas_sem_pii():
    assert ler_rodada([]).respostas == () and ler_rodada([]).fechado is False
    for lixo in (None, {}, {"corpo": None}, "texto", 42, [None, 3, "x"]):
        r = ler_rodada(lixo)
        assert r.respostas == () and r.ofertas == ()
    base = {"seguradora": 99, "seguradoraTxt": "Seguradora Teste", "retorno": True}
    # resultados nulo, sem retornoErro, sem erros → respondeu sem nada: DESCONHECIDA
    r = ler_rodada([dict(base, resultados=None)])
    assert r.respostas[0].familia == C.DESCONHECIDA and r.fechado is True
    # prêmio 0 / nulo / string vazia / lixo não é oferta; string BR é
    for p, ofertas in ((0, 0), (None, 0), ("", 0), ("abc", 0), ("0,00", 0),
                       ("1.234,56", 1), ("1234.56", 1), (1234.56, 1), (True, 0)):
        rr = ler_rodada([dict(base, resultados=[{"premio": p, "identificacao": "Pacote"}])])
        assert len(rr.ofertas) == ofertas, p
    assert numero("1.234,56") == 1234.56
    # ainda não respondeu → PENDENTE e a rodada não fecha
    pend = ler_rodada([dict(base, retorno=False)])
    assert pend.respostas[0].familia == C.PENDENTE and pend.fechado is False
    # credencial pela bandeira, sem mensagem
    cred = ler_rodada([dict(base, credenciaisValidas=False, resultados=[])])
    assert cred.respostas[0].familia == C.CREDENCIAL
    # pendente → recusou → fechado, na ordem
    a = ler_rodada({"t_s": 1.0, "corpo": [dict(base, retorno=False)]})
    b = ler_rodada({"t_s": 2.0, "corpo": [dict(base, erros=["Não oferecemos seguro para os dados enviados no momento"])]})
    tipos = [e.tipo for e in eventos_entre(a, b)]
    assert tipos == [C.SEGURADORA_RECUSOU, C.CONJUNTO_FECHADO]
    assert eventos_entre(b, a) == []              # a anterior chegou depois: ignora


def test_pedido_do_calcularv2_tem_os_grupos_e_obrigatorio_ainda_nao_medido():
    corpo = _fixture("gravacao_r1")["calculos"][0]["pedido"]
    p = pedido_de_calcularv2(corpo)
    assert p.ramo == C.RAMO_AUTO == 31
    assert len(p.seguradoras) == 17
    for grupo in C.CAMPOS_DO_PEDIDO_AUTO:
        campos = getattr(p, grupo)
        assert campos and all(c.obrigatorio is None for c in campos)
    assert {c.nome for c in p.veiculo} >= {"fipe", "modelo", "ano_modelo"}
    with pytest.raises(ValueError):
        C.Ajuste("preco_magico", 1)
    assert C.Ajuste("comissao", 15).tipo == "comissao"


def test_o_contrato_e_puro_e_nao_se_chama_quote():
    pasta = BACKEND / "portal_worker" / "multicalculo"
    for arq in pasta.glob("*.py"):
        texto = arq.read_text(encoding="utf-8")
        assert not re.search(r"^\s*(from|import)\s+app\b", texto, re.M), arq.name
        assert not re.search(r"^\s*import\s+(requests|httpx|aiohttp|psycopg|supabase)", texto, re.M), arq.name
        assert not re.search(r"\bquote", texto, re.I), f"D-MC-37: {arq.name}"


@pytest.mark.skipif(not INTAKE.exists(), reason="o bruto só existe na máquina do gerente (G2 declarado)")
def test_o_fio_do_bruto_ao_leitor():
    """bruto (HAR) → gerador (em memória) → fixture → leitor → 22/12 e 21/11, e a
    fixture em memória é BYTE A BYTE a que está no repositório (G4)."""
    sys.path.insert(0, str(BACKEND / "scripts"))
    import agger_fixtures_saneadas as G
    for (rotulo, rel, conta), (_, n_of, n_seg, _, _) in zip(G.GRAVACOES, ESPERADO):
        fx, _meta = G.sanear(G.registros_do_har(INTAKE / rel), rotulo, conta)
        ultima = ler_rodada(fx["calculos"][0]["rodadas"][-1])
        assert (len(ultima.ofertas), len({o.seguradora_codigo for o in ultima.ofertas})) == (n_of, n_seg)
        assert G.serializar(fx) == G._sem_cr((FIX / f"{rotulo}.json").read_bytes())
