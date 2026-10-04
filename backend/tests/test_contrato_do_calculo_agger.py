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


# 🔴 G5: as capturas AO VIVO (16 cálculos pedidos em 04/10; 📊 12 deles com rodada na captura — os 4 recálculos
# por API foram lidos por `cotacao/versoes`, fora da captura filtrada) — toda resposta da ÚLTIMA rodada tem
# família; nenhuma DESCONHECIDA. A varredura de TODAS as seções está em `test_g5_nenhuma_desconhecida_em_secao_nenhuma`. Cada mensagem nova que aparecer no motor tem de ganhar regra, não sumir num balde.
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


def test_pedido_do_calcularv2_tem_os_grupos_e_o_obrigatorio_medido_no_E3():
    # §9.3: este teste dizia "obrigatório ainda não medido" — verdade até a E3 (04/10) medir. A lição migra:
    # agora ele fixa os 16 que a tela recusou vazios e os 4 que aceitou; o resto continua None (não medido).
    corpo = _fixture("gravacao_r1")["calculos"][0]["pedido"]
    p = pedido_de_calcularv2(corpo)
    assert p.ramo == C.RAMO_AUTO == 31
    assert len(p.seguradoras) == 17
    todos = [c for grupo in C.CAMPOS_DO_PEDIDO_AUTO for c in getattr(p, grupo)]
    assert all(getattr(p, g) for g in C.CAMPOS_DO_PEDIDO_AUTO)
    assert sum(1 for c in todos if c.obrigatorio is True) == 16
    assert {c.nome for c in todos if c.obrigatorio is False} == {"telefone", "email", "placa", "chassi"}
    assert {c.nome for c in p.condutor if c.obrigatorio} >= {"tempo_habilitacao", "cpf", "nascimento"}
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


# ---------------------------------------------------------------------------
# Conserto único da SPEC-128 (laudos do juiz e do red team, 04/10)
# ---------------------------------------------------------------------------
TODAS = sorted(p.stem for p in FIX.glob("*.json") if p.name != "MANIFESTO.json")


def _todas_as_respostas(fx: dict):
    """(seção, RodadaDoCalculo) de TODA seção que traz respostas de seguradora:
    `calculos[].rodadas[]`, `versoes[].corpo[]` (uma cotação por versão) e `negocio[].corpo`."""
    for c in fx.get("calculos", []):
        for r in c.get("rodadas", []):
            yield "rodadas", ler_rodada(r)
    for v in fx.get("versoes", []):
        for cot in v.get("corpo") or []:
            yield "versoes", ler_rodada(cot)
    for n in fx.get("negocio", []):
        yield "negocio", ler_rodada(n.get("corpo") or {})


@pytest.mark.parametrize("rotulo", TODAS)
def test_g5_nenhuma_desconhecida_em_secao_nenhuma(rotulo):
    """P1: o G5 varria só `calculos[].rodadas`; 📊 a `versoes` da gravacao_r2 tinha 12 DESCONHECIDA
    (3 mensagens reais sem regra). Agora: TODA seção, TODA fixture, 0."""
    soltas = sorted({(sec, m[:60]) for sec, rod in _todas_as_respostas(_fixture(rotulo))
                     for x in rod.respostas if x.familia == C.DESCONHECIDA for m in x.mensagens})
    assert soltas == [], soltas


def test_g5_varre_as_versoes_de_verdade():
    """CONTROLE: a varredura ALCANÇA a seção `versoes` (📊 85 respostas na gravacao_r2) — sem isso o 0
    acima poderia ser 0 de nada."""
    secs: dict = {}
    for sec, rod in _todas_as_respostas(_fixture("gravacao_r2")):
        secs[sec] = secs.get(sec, 0) + len(rod.respostas)
    assert secs.get("versoes", 0) == 85 and secs.get("rodadas", 0) > 0 and secs.get("negocio", 0) > 0


def test_cada_regra_cita_uma_fixture_que_existe():
    from portal_worker.multicalculo.leitor_agger import REGRAS_DE_FAMILIA
    for familia, _padrao, fonte in REGRAS_DE_FAMILIA:
        assert familia in C.FAMILIAS
        assert any(r in fonte for r in TODAS), fonte


@pytest.mark.parametrize("mensagem,familia", [
    ("Auto - Cotação indisponível, tente mais tarde realizando cópia da cotação", C.INSTABILIDADE),
    ("Os dados do condutor principal devem ser preenchidos.", C.DADO),
    ("A opção selecionada para vínculo do segurado do item 1 não possui aceitação para este produto.", C.ACEITACAO),
    ("COBERTURA CASCO FORA DO PERMITIDO", C.DADO),
])
def test_as_mensagens_novas_tem_familia(mensagem, familia):
    base = {"seguradora": 99, "seguradoraTxt": "Seguradora Teste", "retorno": True}
    assert ler_rodada([dict(base, erros=[mensagem])]).respostas[0].familia == familia


# -- B1(b): o leitor tira URL e chave de TODA string que sai -----------------
_CHAVE_FALSA = "AIza" + "Sy" + "0" * 33


def test_leitor_nunca_devolve_url_nem_chave():
    url = "https://api.seg.exemplo/v1/p?key=" + _CHAVE_FALSA
    item = {"seguradora": 9, "seguradoraTxt": "Seg www.seg.exemplo/x", "retorno": True,
            "erros": ["Read terminated for " + url],
            "resultados": [{"premio": 900.0, "identificacao": "Pacote arquivos.seg.exemplo/a/b",
                            "alertas": ["veja " + url], "observacoes": ["token=abc"],
                            "erros": ["access_token=xyz"],
                            "coberturas": {"tipo": url, "vidros": "sim"}}]}
    rod = ler_rodada([item])
    tudo = json.dumps([dataclasses.asdict(r) for r in rod.respostas], ensure_ascii=False)
    tudo += json.dumps([dataclasses.asdict(e) for e in eventos_do_calculo([rod])], ensure_ascii=False)
    assert not re.search(r"https?:|www[.]|seg[.]exemplo|AIza|token=|key=", tudo), "URL/chave saiu do leitor"
    assert "<removido:url>" in tudo
    # a mensagem continua classificável sem a URL
    so_erro = ler_rodada([{"seguradora": 9, "retorno": True, "erros": ["Read terminated for " + url]}])
    assert so_erro.respostas[0].familia == C.INSTABILIDADE


# -- P10: numero() e _inteiro() nunca mentem nem levantam ---------------------
@pytest.mark.parametrize("entrada,esperado", [
    ("1.234,56", 1234.56), ("1,234.56", 1234.56), ("1.234", 1234.0), ("1234.56", 1234.56),
    ("R$ 1.234,56", 1234.56), ("1.234.567", 1234567.0), ("0,00", 0.0), ("12,5", 12.5), (1234.56, 1234.56),
    (7, 7.0), ("NaN", None), ("nan", None), ("inf", None), ("-inf", None), ("1e400", None), ("abc", None),
    ("", None), (None, None), (True, None), (float("nan"), None), (float("inf"), None), (10 ** 400, None),
])
def test_numero_robusto(entrada, esperado):
    assert numero(entrada) == esperado


def test_lixo_numerico_nunca_vira_excecao_nem_oferta():
    from portal_worker.multicalculo.leitor_agger import _inteiro
    assert _inteiro("NaN") is None and _inteiro("inf") is None and _inteiro(float("nan")) is None
    r = ler_rodada({"t_s": float("nan"), "corpo": [
        {"seguradora": "NaN", "retorno": True, "tempoResposta": "inf",
         "resultados": [{"premio": p, "parcelamentos": [{"parcelas": "inf", "tipoPag": "NaN"}]}]}
        for p in ("NaN", "inf", "1e400", float("inf"), float("nan"))]})
    assert r.t_s is None and r.ofertas == () and len(r.respostas) == 5
    ok = ler_rodada([{"seguradora": 3, "retorno": True,
                      "resultados": [{"premio": "1.234,56", "parcelamentos": [{"parcelas": "inf"}]}]}])
    assert ok.ofertas[0].premio_total == 1234.56 and ok.ofertas[0].parcelamentos[0].parcelas is None


# -- P6: eventos ---------------------------------------------------------------
def _seg(cod, **k):
    d = {"seguradora": cod, "seguradoraTxt": f"S{cod}", "retorno": True}
    d.update(k)
    return d


def test_conjunto_fechado_sai_uma_vez_mesmo_quando_a_rodada_reabre():
    """P6(a): A responde (fecha) → B aparece pendente (reabre) → B responde (fecharia de novo)."""
    oferta = [{"premio": 100.0, "identificacao": "P"}]
    r1 = ler_rodada({"t_s": 1.0, "corpo": [_seg(1, resultados=oferta)]})
    r2 = ler_rodada({"t_s": 2.0, "corpo": [_seg(1, resultados=oferta), _seg(2, retorno=False)]})
    r3 = ler_rodada({"t_s": 3.0, "corpo": [_seg(1, resultados=oferta),
                                           _seg(2, resultados=[{"premio": 50, "identificacao": "Q"}])]})
    assert (r1.fechado, r2.fechado, r3.fechado) == (True, False, True)
    ev = [e.tipo for e in eventos_do_calculo([r1, r2, r3])]
    assert ev.count(C.CONJUNTO_FECHADO) == 1
    assert ev.count(C.NOVA_OFERTA) == 2


def test_seguradora_repetida_na_rodada_nao_recusa_e_oferta_ao_mesmo_tempo():
    """P6(b): a mesma seguradora em 2 itens (E20) — um com oferta, outro com erro: só a oferta."""
    a = ler_rodada({"t_s": 1.0, "corpo": [_seg(5, retorno=False)]})
    b = ler_rodada({"t_s": 2.0, "corpo": [
        _seg(5, resultados=[{"premio": 300.0, "identificacao": "Pacote 1"}]),
        _seg(5, erros=["A seguradora está apresentando instabilidade no momento."])]})
    tipos = [e.tipo for e in eventos_entre(a, b)]
    assert C.SEGURADORA_RECUSOU not in tipos and tipos.count(C.NOVA_OFERTA) == 1
    # os 2 itens com erro → UMA recusa, não duas
    c = ler_rodada({"t_s": 2.0, "corpo": [_seg(5, erros=["instabilidade"]), _seg(5, erros=["instabilidade"])]})
    assert [e.tipo for e in eventos_entre(a, c)] == [C.SEGURADORA_RECUSOU, C.CONJUNTO_FECHADO]


def test_premio_mudou_no_mesmo_pacote_vira_oferta_atualizada():
    """P6(c): o mesmo pacote com outro prêmio é OFERTA_ATUALIZADA (com a oferta nova), não uma 2ª nova."""
    a = ler_rodada({"t_s": 1.0, "corpo": [_seg(5, resultados=[{"premio": 300.0, "identificacao": "P", "packageType": 1}])]})
    b = ler_rodada({"t_s": 2.0, "corpo": [_seg(5, resultados=[{"premio": 280.0, "identificacao": "P", "packageType": 1}])]})
    ev = eventos_do_calculo([a, b])
    assert [e.tipo for e in ev] == [C.NOVA_OFERTA, C.CONJUNTO_FECHADO, C.OFERTA_ATUALIZADA]
    assert ev[-1].oferta.premio_total == 280.0
    # dois itens IGUAIS na MESMA rodada (franquias diferentes) são duas ofertas, não uma atualização
    d = ler_rodada({"t_s": 1.0, "corpo": [_seg(5, resultados=[
        {"premio": 300.0, "identificacao": "P", "packageType": 1},
        {"premio": 250.0, "identificacao": "P", "packageType": 1}])]})
    assert [e.tipo for e in eventos_entre(None, d)].count(C.NOVA_OFERTA) == 2
    # 📊 nas 5 fixtures reais: 0 OFERTA_ATUALIZADA (o prêmio não muda dentro de um cálculo) e ≤ 1 fechado
    for rot in TODAS:
        for c in _fixture(rot).get("calculos", []):
            evs = eventos_do_calculo([ler_rodada(r) for r in c.get("rodadas", [])])
            assert not any(e.tipo == C.OFERTA_ATUALIZADA for e in evs), rot
            assert sum(e.tipo == C.CONJUNTO_FECHADO for e in evs) <= 1, rot
