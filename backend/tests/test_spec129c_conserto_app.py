# -*- coding: utf-8 -*-
"""SPEC-129-C · CONSERTO do lado do APP — os achados do juiz e do red team, cada um com o defeito VERMELHO + controle.

    1. BLOCKER (red B2) — a RC SOMADA: 📊 nas 3/3 gravações de condomínio a HDI e a Axa devolvem RC Condomínio + RC
       Síndico SOMADAS numa chave só, e a Allianz devolve a RC Condomínio como `responsabilidadeCivil`.
    2. Red P1 + juiz P3 — "não devolveu" ≠ "não inclui": não ecoar = "não informou" (fica, com aviso); ecoar menos numa
       essencial = "cobre menos" (sai).
    3. Red P2 + canário #2 — a régua compara com o PEDIDO do cálculo (a básica e as coberturas), não com o quadro.
    4. Juiz B2 — o ajuste não muda a Básica (D-129C-03): recusa clara; o que se grava = o que se envia.
    5. Red P4 — a comissão do item de RE: > 0 e ≤ `comissao.teto_pct`; `por_ramo = 0` volta à entrada.
    6. Red P6 — a "mais em conta" com extras tira as acessórias (as essenciais do ramo ficam).
    7. Red P7 — `_sem_margem` vale para todos os ramos e não muda nada VISÍVEL no auto.
    8. Juiz P2 — `basica_renovada` sem chamador nesta SPEC (chamada pela 131): o teste próprio dela.

O fio: a porta REAL sobre o banco dublê, o leitor REAL e a linha REAL do motor (os helpers da F2) com as gravações reais.
O "esperado" das gravações é lido do JSON CRU aqui mesmo (§9.4), nunca do código que se testa.
⛔ Dado SINTÉTICO; as gravações já vêm saneadas; nenhum nome de corretora (§13.9).
Rodar: cd backend && .venv/Scripts/python.exe -m pytest tests/test_spec129c_conserto_app.py -q -p no:cacheprovider
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from test_spec129c_o_app_por_ramo import (PED, PRE, C, CFG, calcular_e_comparar, carregar, dados,  # noqa: E402,F401
                                          motor_grava_a_gravacao, mundo, rodar)
from app.services.multicalculo import porta as PORTA  # noqa: E402
from app.services.multicalculo.porta import PedidoIncompleto  # noqa: E402

B = PED.CHAVE_DA_BASICA
NOME = {1: "Bradesco", 4: "HDI", 5: "Allianz", 8: "Porto", 11: "Tokio Marine", 35: "Axa"}
A = "a0000000-0000-4000-8000-0000000000d1"


def _rc_crua(nome: str):
    """Do JSON CRU, sem código do produto: o pedido de RC (cond + síndico) e o que cada oferta com preço ecoou."""
    g = carregar(nome)
    c = g["versao"]["configuracoes"]
    soma = (c.get("isValorCondominio") or 0) + (c.get("isValorSindico") or 0)
    ecos = {}
    for it in g["calculos"]:
        for r in it.get("resultados") or []:
            if (r.get("premio") or 0) > 0:
                cob = r.get("coberturas") or {}
                ecos[it["seguradora"]] = {k: cob[k] for k in ("isValorCondominio", "isValorSindico",
                                                              "responsabilidadeCivil") if k in cob}
    return soma, ecos


# =====================================================================================================================
# 1 · BLOCKER — a RC somada
# =====================================================================================================================
@pytest.mark.parametrize("nome", ["gravacao_condominio_1", "gravacao_condominio_2", "gravacao_condominio_3"])
def test_a_rc_somada_e_medida_no_json_cru(nome):
    """📊 a EVIDÊNCIA da equivalência, contada aqui no JSON cru: HDI → só `isValorSindico` = a soma; Axa → só
    `isValorCondominio` = a soma (3 de 3 gravações)."""
    soma, ecos = _rc_crua(nome)
    assert ecos[4] == {"isValorSindico": soma} and ecos[35] == {"isValorCondominio": soma}


def test_as_rc_somadas_nao_viram_aviso_nem_tiram_do_ranking_condominio_3(mundo):
    """O caso do red: na condominio_3 a Allianz (R$ 4.870,41, `responsabilidadeCivil` = a RC Condomínio) é a MAIS BARATA
    e o 1º lugar; HDI e Axa (RC somada) ficam no ranking sem aviso de RC."""
    _a, _p, q, _and = calcular_e_comparar(mundo, 16, "gravacao_condominio_3")
    linhas = {l["seguradora"]: l for l in q.ranking()}
    assert q.ranking()[0]["seguradora"] == "Allianz" and q.ranking()[0]["premio_anual"] == 4870.41
    for seg in ("Allianz", "HDI", "Axa"):
        assert not any("RC" in a for a in linhas[seg]["avisos"]), (seg, linhas[seg]["avisos"])
    assert not any("RC" in (d["motivo"] or "") for d in q.diferentes)
    # a Bradesco calculou OUTRA básica (📊 JSON cru: 8,4 mi × 8 mi do pedido) — fora, pelo motivo certo
    assert [(d["seguradora"], d["chave_motivo"]) for d in q.diferentes] == [("Bradesco", "basica_diferente")]


@pytest.mark.parametrize("nome", ["gravacao_condominio_1", "gravacao_condominio_2", "gravacao_condominio_3"])
def test_ecos_re_le_as_duas_rc_nas_ofertas_reais(nome):
    """O MOTOR (`ecos_re`) sobre as coberturas REAIS: as RC do pedido saem ecoadas (nunca None) em todas as ofertas com
    RC somada ou com `responsabilidadeCivil`."""
    g = carregar(nome)
    c = g["versao"]["configuracoes"]
    pedido = {B: float(c[B]), "isValorCondominio": float(c["isValorCondominio"]),
              "isValorSindico": float(c["isValorSindico"])}
    soma, ecos = _rc_crua(nome)
    for seg, eco in ecos.items():
        if sum(eco.values()) >= soma and seg != 1:
            lido = C.ecos_re(eco, pedido, 16)
            assert lido == {"isValorCondominio": pedido["isValorCondominio"],
                            "isValorSindico": pedido["isValorSindico"]}, (nome, seg, eco)


def test_a_rc_somada_so_vale_com_a_soma_inteira_e_so_no_condominio():
    """Controle (§9.3: o guarda consegue ser diferente): UMA chave com MENOS que a soma não cobre as duas; e
    `responsabilidadeCivil` só vira a RC Condomínio no ramo 16."""
    pedido = {B: 8e6, "isValorCondominio": 200000.0, "isValorSindico": 200000.0}
    assert C.ecos_re({"isValorSindico": 200000}, pedido, 16) == {"isValorCondominio": None, "isValorSindico": 200000.0}
    assert C.ecos_re({"isValorSindico": 400000}, pedido, 16) == {"isValorCondominio": 200000.0,
                                                                 "isValorSindico": 200000.0}
    assert C.ecos_re({"responsabilidadeCivil": 200000}, pedido, 2)["isValorCondominio"] is None


def test_mutacao_sem_as_equivalencias_fica_vermelho(mundo, monkeypatch):
    """Mutação: `ecos_re` sem as equivalências → o aviso FALSO de RC volta na HDI, Axa e Allianz (condominio_3)."""
    monkeypatch.setattr(C, "ecos_re", lambda cob, pedido, ramo: {
        k: C._num(cob.get(k)) for k, v in pedido.items() if v and k not in C._FORA_DA_COMPARACAO_RE})
    _a, _p, q, _and = calcular_e_comparar(mundo, 16, "gravacao_condominio_3")
    com_aviso_rc = {l["seguradora"] for l in q.ranking() if any("RC" in a for a in l["avisos"])}
    assert com_aviso_rc == {"Allianz", "HDI", "Axa"}


# =====================================================================================================================
# 2 · "não devolveu" ≠ "não inclui"
# =====================================================================================================================
def _of(i, seg, cod, premio, cob, calc="c1"):
    return {"id": f"o{i}", "calculo_id": calc, "corretora_company_id": A, "premio_total": premio, "pacote": "P",
            "seguradora": seg, "seguradora_codigo": cod, "coberturas": cob}


def _estado(pedido, calc="c1", opcao="padrao"):
    return {"calculo_id": calc, "corretora_company_id": A, "opcao": opcao, "coberturas_pedidas": pedido}


PEDIDO_RESID = {B: 550000, "isDanosEletricos": 10000, "isDanosVendaval": 45000, "vidros": 20000, "assist24hs": 2}


def test_nao_ecoar_fica_com_aviso_e_ecoar_menos_sai():
    q = C.comparar([
        _of(1, "Allianz", 5, 700.0, {B: 550000, "isDanosVendaval": 45000, "vidros": 20000}),            # não ecoou
        _of(2, "HDI", 4, 650.0, {B: 550000, "isDanosEletricos": 5000, "isDanosVendaval": 45000}),       # menos
        _of(3, "Mapfre", 3, 600.0, {B: 550000, "isDanosEletricos": 0, "isDanosVendaval": 45000}),       # zero
        _of(4, "Tokio", 11, 900.0, {B: 550000, "isDanosEletricos": 10000, "isDanosVendaval": 45000,
                                    "vidros": 5000, "assist24hs": "Plano Plus"}),                      # não essencial
    ], estados=[_estado(PEDIDO_RESID)], ramo=2)
    linhas = {l["seguradora"]: l for l in q.ranking()}
    assert set(linhas) == {"Allianz", "Tokio Marine"}
    assert linhas["Allianz"]["avisos"] == ["não informou Danos elétricos"]
    # a assistência (código × texto) nunca vira "cobre menos"; o vidros menor (não essencial) é aviso, não exclusão
    assert linhas["Tokio Marine"]["avisos"] == ["cobre menos que o pedido: Vidros"]
    motivos = {d["seguradora"]: (d["chave_motivo"], d["motivo"]) for d in q.diferentes}
    assert motivos == {"HDI": ("cobre_menos", "cobre menos: Danos elétricos"),
                       "Mapfre": ("cobre_menos", "cobre menos: Danos elétricos")}
    assert not any("não inclui" in (d["motivo"] or "") for d in q.diferentes)


@pytest.mark.parametrize("nome,seg,premio,aviso", [
    ("gravacao_empresarial_1", "Bradesco", 816.0, "Responsabilidade civil"),
    ("gravacao_empresarial_2", "Tokio Marine", 507.96, "Danos elétricos")])
def test_a_que_nao_devolveu_fica_no_ranking_com_o_aviso(mundo, nome, seg, premio, aviso):
    """📊 red P1: a Bradesco (empresarial_1, a MAIS BARATA) não devolve RC; a Tokio não devolve danos elétricos. Ficam."""
    g = carregar(nome)
    _a, _p, q, _and = calcular_e_comparar(mundo, 18, nome)
    linha = next(l for l in q.ranking() if l["seguradora"] == seg)
    assert linha["premio_anual"] == premio and aviso in linha["avisos"][0]
    assert linha["avisos"][0].startswith("não informou")
    if nome.endswith("_1"):
        assert q.ranking()[0]["seguradora"] == "Bradesco"
    del g


# =====================================================================================================================
# 3 · a régua compara com o PEDIDO
# =====================================================================================================================
def test_basica_diferente_do_pedido_sai_mesmo_quando_todas_concordam(mundo):
    """📊 red P2: o pedido com a Básica de 800 mil (empresarial_2) e as ofertas da empresarial_3 com 2,5 mi — antes a
    MODA do quadro (2,5 mi) punha todas no ranking sem aviso. Contra o PEDIDO, nenhuma é comparável."""
    m = mundo
    pedido = PED.PedidoDeCalculo.de_dict(dados(18), ramo=18)
    aberto = rodar(m.porta.calcular(company_id=m.a, pedido=pedido, origem="auxiliar"))
    calc = next(c for c in m.banco.linhas("multicalculo_calculos")
                if c["pedido_id"] == aberto.pedido_id and c["opcao"] == "padrao")
    motor_grava_a_gravacao(m, aberto.pedido_id, calc, carregar("gravacao_empresarial_3"))
    cfg, andamento = rodar(m.porta._config_e_andamento(company_id=m.a, pedido_id=aberto.pedido_id))
    q = C.comparar(andamento.ofertas, andamento.eventos, estados=andamento.estados, config=cfg, ramo=18)
    assert q.ranking() == [] and q.resumo["regua"] == "re"
    assert {d["chave_motivo"] for d in q.diferentes} == {"basica_diferente"}
    assert all("o pedido, com R$ 800.000" in d["motivo"] for d in q.diferentes)
    # mutação: o estado SEM as coberturas pedidas → o plano B (a moda do quadro) as aceita — e a régua o DIZ
    sem = [{k: v for k, v in e.items() if k != "coberturas_pedidas"} for e in andamento.estados]
    q2 = C.comparar(andamento.ofertas, andamento.eventos, estados=sem, config=cfg, ramo=18)
    assert len(q2.ranking()) >= 5 and q2.resumo["regua"] == "re_sem_pedido"


def test_uma_oferta_so_e_comparada_contra_o_pedido():
    """Canário #2 (📊 11/10): a Allianz do empresarial tirou roubo e vidros e saiu "comparável" sozinha — a referência
    era ela mesma. Contra o pedido, o corretor LÊ o que sumiu."""
    pedido = {B: 911000, "isDanosEletricos": 30000, "responsabilidadeCivil": 125000, "isDanosRoubo": 13700,
              "vidros": 4600}
    oferta = _of(1, "Allianz", 5, 2072.76, {B: 911000, "isDanosEletricos": 30000, "responsabilidadeCivil": 125000,
                                            "isDanosRoubo": 0, "vidros": 0, "isDanosMorais": 62500})
    q = C.comparar([oferta], estados=[_estado(pedido)], ramo=18)
    assert q.ranking()[0]["avisos"] == ["cobre menos que o pedido: Roubo de bens, Vidros"]
    # controle: a MESMA oferta contra o quadro (sem pedido) não tinha o que avisar
    q0 = C.comparar([oferta], estados=[{k: v for k, v in _estado(pedido).items() if k != "coberturas_pedidas"}],
                    ramo=18)
    assert q0.ranking()[0]["avisos"] == [] and q0.resumo["regua"] == "re_sem_pedido"


def test_o_estado_de_re_leva_o_pedido_sem_a_margem_e_o_auto_nao_muda(mundo):
    m = mundo
    aberto = rodar(m.porta.calcular(company_id=m.a, pedido=PED.PedidoDeCalculo.de_dict(dados(16), ramo=16),
                                    opcoes=("padrao",), origem="auxiliar"))
    calc = next(c for c in m.banco.linhas("multicalculo_calculos") if c["pedido_id"] == aberto.pedido_id)
    calc["coberturas"] = {**calc["coberturas"], "percComissao": 30}         # o ajuste de comissão grava aqui
    estado = rodar(m.porta.consultar(company_id=m.a, pedido_id=aberto.pedido_id)).estados[0]
    assert estado["coberturas_pedidas"][B] == calc["coberturas"][B]
    assert "percComissao" not in estado["coberturas_pedidas"]


# =====================================================================================================================
# 4 · o ajuste não muda a Básica
# =====================================================================================================================
def test_o_ajuste_com_a_basica_e_recusado_e_o_resto_passa(mundo):
    m = mundo
    aberto = rodar(m.porta.calcular(company_id=m.a, pedido=PED.PedidoDeCalculo.de_dict(dados(16), ramo=16),
                                    opcoes=("padrao",), origem="auxiliar"))
    calc = next(c for c in m.banco.linhas("multicalculo_calculos") if c["pedido_id"] == aberto.pedido_id)
    calc.update(negocio_ref="neg-ficticio", versao=1, status="fechado")
    antes = len(m.banco.linhas("multicalculo_calculos"))
    for ruim, trecho in (({B: 1000, "vidros": 5000}, "Básica"), ({"basica": 1000}, "Básica"),
                         ({"valor_basica": 1000}, "Básica"), ({"bike": 3000}, "sem código"),
                         ({"vidros": -1}, "≥ 0")):
        with pytest.raises(ValueError, match=trecho):
            rodar(m.porta.recalcular(company_id=m.a, calculo_id=calc["id"],
                                     ajuste={"tipo": "cobertura", "valor": ruim}))
    assert len(m.banco.linhas("multicalculo_calculos")) == antes             # nada gravado nas recusas
    ok = rodar(m.porta.recalcular(company_id=m.a, calculo_id=calc["id"],
                                  ajuste={"tipo": "cobertura", "valor": {"vidros": 5000}}))
    novo = next(c for c in m.banco.linhas("multicalculo_calculos") if c["id"] == ok["id"])
    assert novo["coberturas"]["vidros"] == 5000 and novo["coberturas"][B] == calc["coberturas"][B]
    assert novo["ajuste"]["valor"] == {"vidros": 5000}                       # o que se grava = o que se envia


# =====================================================================================================================
# 5 · a comissão com piso e teto
# =====================================================================================================================
def test_a_config_recusa_comissao_zero_ou_acima_do_teto():
    teto = CFG.PADRAO_DO_PRODUTO["comissao"]["teto_pct"]
    entrada = CFG.PADRAO_DO_PRODUTO["comissao"]["entrada"]
    cfg = CFG.mesclar({"comissao": {"por_ramo": {"16": 0, "2": teto + 10, "18": 7.5}}})
    assert CFG.comissao_do_ramo(cfg, 16) == entrada                         # 0 volta ao padrão (não é comissão)
    assert CFG.comissao_do_ramo(cfg, 2) == entrada                          # acima do teto → padrão
    assert CFG.comissao_do_ramo(cfg, 18) == 7.5                             # controle: o válido fica
    ruim = CFG.mesclar({"comissao": {"teto_pct": entrada - 1}})             # teto abaixo da entrada: incoerente
    assert CFG.teto_da_comissao(ruim) == teto


@pytest.mark.parametrize("valor,aceita", [(0, False), (500, False), (-1, False), (20, True)])
def test_a_porta_recusa_a_comissao_do_pedido_fora_da_regua(mundo, valor, aceita):
    m = mundo
    d = dados(2)
    d["comissao_desconto"] = {"comissao_percentual": valor}
    pedido = PED.PedidoDeCalculo.de_dict(d, ramo=2)
    if aceita:
        rodar(m.porta.calcular(company_id=m.a, pedido=pedido, origem="auxiliar"))
        return
    with pytest.raises(PedidoIncompleto) as e:
        rodar(m.porta.calcular(company_id=m.a, pedido=pedido, origem="auxiliar"))
    assert "comissao_desconto.comissao_percentual" in e.value.campos
    assert m.banco.linhas("multicalculo_pedidos") == []


def test_o_ajuste_de_comissao_de_re_passa_pela_mesma_regua(mundo):
    m = mundo
    aberto = rodar(m.porta.calcular(company_id=m.a, pedido=PED.PedidoDeCalculo.de_dict(dados(2), ramo=2),
                                    opcoes=("padrao",), origem="auxiliar"))
    calc = next(c for c in m.banco.linhas("multicalculo_calculos") if c["pedido_id"] == aberto.pedido_id)
    calc.update(negocio_ref="neg-ficticio", versao=1, status="fechado")
    for ruim in (0, 80):
        with pytest.raises(ValueError, match="maior que 0"):
            rodar(m.porta.recalcular(company_id=m.a, calculo_id=calc["id"], ajuste={"tipo": "comissao", "valor": ruim}))
    ok = rodar(m.porta.recalcular(company_id=m.a, calculo_id=calc["id"], ajuste={"tipo": "comissao", "valor": 20}))
    assert ok["opcao"] == "ajuste"


# =====================================================================================================================
# 6 · a "mais em conta" com extras
# =====================================================================================================================
@pytest.mark.parametrize("ramo", [16, 2, 18])
def test_a_mais_em_conta_tira_as_extras_acessorias(mundo, ramo, monkeypatch):
    m = mundo

    def as_duas():
        aberto = rodar(m.porta.calcular(company_id=m.a, pedido=PED.PedidoDeCalculo.de_dict(dados(ramo), ramo=ramo),
                                        origem="auxiliar"))
        return {c["opcao"]: c["coberturas"] for c in m.banco.linhas("multicalculo_calculos")
                if c["pedido_id"] == aberto.pedido_id}

    cob = as_duas()
    extras = dados(ramo)["risco"]["extras"]
    base_eco = PRE.coberturas_re(ramo, "economica", float(dados(ramo)["risco"]["valor_basica"]), {})
    acessorias = {k for k in extras if not base_eco.get(k)}
    essenciais = set(extras) - acessorias
    assert acessorias and essenciais, ramo                                  # a gravação tem das duas (o teste morde)
    assert all(cob["economica"][k] == 0 for k in acessorias)                # saíram da mais em conta
    assert all(cob["economica"][k] == extras[k] for k in essenciais)        # as essenciais ficam, com o valor do pedido
    assert all(cob["padrao"][k] == v for k, v in extras.items())            # a padrão leva todas
    assert cob["economica"] != cob["padrao"]
    # mutação: a extra vencendo a opção de novo → as acessórias voltam na mais em conta
    monkeypatch.setattr(PORTA, "extras_da_opcao_re", lambda base, opcao, ex: dict(ex))
    mutado = as_duas()
    assert all(mutado["economica"][k] == extras[k] for k in acessorias)


# =====================================================================================================================
# 7 · `_sem_margem` não muda nada visível no auto
# =====================================================================================================================
def test_sem_margem_nao_muda_nada_visivel_no_auto():
    estados = [{"calculo_id": "c1", "corretora_company_id": A, "opcao": "padrao"},
               {"calculo_id": "c2", "corretora_company_id": A, "opcao": "economica"}]

    def ofertas(com_margem):
        extra = {"percComissao": 20, "percDesconto": 5} if com_margem else {}
        base = {"tipoPadronizado": "Compreensiva", "casco": 100, "vidros": "Vidros completo",
                "carroReserva": "7 dias", "assist24hs": "500 km", **extra}
        return [_of(1, "Allianz", 5, 3000.0, dict(base)), _of(2, "HDI", 4, 2800.0, dict(base)),
                _of(3, "Tokio", 11, 2500.0, dict(base, casco=80)), _of(4, "Porto", 8, 2600.0, dict(base), calc="c2")]

    def visivel(q):
        ops = C.opcoes(q, situacao="novo_sem_apolice")
        return ([(l["seguradora"], l["premio_anual"]) for l in q.ranking()], [d["motivo"] for d in q.diferentes],
                [(o["rotulo"], o["seguradora"], o["coberturas"], o["motivos"], o["o_que_muda"], o["nota"]) for o in ops])

    com, sem = C.comparar(ofertas(True), estados=estados), C.comparar(ofertas(False), estados=estados)
    assert visivel(com) == visivel(sem)
    assert "avisos" not in com.ranking()[0]                                 # a linha do auto não ganhou campo
    # controle: a margem existe na entrada e NÃO sai na coberturas_brutas
    assert ofertas(True)[0]["coberturas"]["percComissao"] == 20
    assert not any(k.startswith("perc") for l in com.ranking() for k in l["coberturas_brutas"])


# =====================================================================================================================
# 8 · a regra de renovação (sem chamador nesta SPEC — chamada pela 131)
# =====================================================================================================================
def test_basica_renovada_aplica_o_reajuste_do_ramo():
    padrao = CFG.mesclar(None)
    pct = CFG.PADRAO_DO_PRODUTO["renovacao"]["reajuste_basica_pct"]["16"]
    assert CFG.basica_renovada(padrao, 16, 1_000_000) == round(1_000_000 * (1 + pct / 100), 2)
    propria = CFG.mesclar({"renovacao": {"reajuste_basica_pct": {"16": 10.0, "2": 15.0, "18": 15.0}}})
    assert CFG.basica_renovada(propria, 16, 1_000_000) == 1_100_000.0      # a corretora troca o dela
    assert CFG.basica_renovada(padrao, 31, 1_000_000) is None               # o auto não tem a regra
    assert CFG.basica_renovada(padrao, 16, 0) is None and CFG.basica_renovada(padrao, 16, "x") is None
    assert "chamada pela 131" in CFG.basica_renovada.__doc__
