# -*- coding: utf-8 -*-
"""SPEC-130-A · F1 · U3 — a NEGOCIAÇÃO: a ordem do "mais barato" (D-MC-67), a margem (D-MC-68), a cotação-alvo
(D-MC-72) assíncrona pela `recalcular` que JÁ existe, e "só a corretora dona negocia" (D-MC-63).

A porta roda INTEIRA (porta + repositório + negociação + comparação + config); só o transporte (PostgREST) é dublê,
BURRO de propósito (igualdade, ordem, faixa). O "motor" grava o resultado dos recálculos À MÃO, como gravaria.
⛔ Dado SINTÉTICO: uuids gerados aqui, nenhum nome de corretora (§13.9); nomes de SEGURADORA são os do Agger.
"""
from __future__ import annotations

import asyncio
import copy
import uuid

import pytest

from app.services.multicalculo import negociacao as N
from app.services.multicalculo.config import PADRAO_DO_PRODUTO, mesclar
from app.services.multicalculo.porta import MulticalculoProvider, NaoAutorizado, NaoEncontrado
from app.services.multicalculo.repositorio import RepositorioMulticalculo


# =====================================================================================================================
# o banco DUBLÊ — só o transporte
# =====================================================================================================================
class _Resp:
    def __init__(self, data):
        self.data = data


class _Consulta:
    def __init__(self, banco, tabela):
        self.banco, self.tabela = banco, tabela
        self.op, self.payload, self.filtros, self._ordem, self._limite, self._faixa = "select", None, [], None, None, None

    def select(self, *_a, **_k):
        self.op = "select"
        return self

    def insert(self, linhas):
        self.op, self.payload = "insert", linhas
        return self

    def update(self, patch):
        self.op, self.payload = "update", patch
        return self

    def eq(self, c, v):
        self.filtros.append(lambda l, c=c, v=v: str(l.get(c)) == str(v))
        return self

    def in_(self, c, vs):
        alvo = {str(v) for v in vs}
        self.filtros.append(lambda l, c=c: str(l.get(c)) in alvo)
        return self

    def gt(self, c, v):
        self.filtros.append(lambda l, c=c, v=v: l.get(c) is not None and l.get(c) > v)
        return self

    def order(self, c, desc=False):
        self._ordem = (c, desc)
        return self

    def limit(self, n):
        self._limite = n
        return self

    def range(self, a, b):
        self._faixa = (a, b)
        return self

    def execute(self):
        linhas = self.banco.tabelas.setdefault(self.tabela, [])
        self.banco.log.append((self.tabela, self.op))
        casa = lambda l: all(f(l) for f in self.filtros)  # noqa: E731
        if self.op == "insert":
            novas = self.payload if isinstance(self.payload, list) else [self.payload]
            saida = []
            for n in novas:
                n = copy.deepcopy(n)
                n.setdefault("id", str(uuid.uuid4()))
                linhas.append(n)
                saida.append(copy.deepcopy(n))
            return _Resp(saida)
        if self.op == "update":
            saida = []
            for l in linhas:
                if casa(l):
                    l.update(copy.deepcopy(self.payload))
                    saida.append(copy.deepcopy(l))
            return _Resp(saida)
        saida = [copy.deepcopy(l) for l in linhas if casa(l)]
        if self._ordem:
            c, desc = self._ordem
            saida.sort(key=lambda l: (l.get(c) is None, str(l.get(c))), reverse=desc)
        if self._faixa:
            saida = saida[self._faixa[0]: self._faixa[1] + 1]
        if self._limite is not None:
            saida = saida[: self._limite]
        return _Resp(saida)


class Banco:
    def __init__(self):
        self.tabelas, self.log = {}, []

    def table(self, nome):
        return _Consulta(self, nome)

    def linhas(self, nome):
        return self.tabelas.get(nome, [])


# =====================================================================================================================
# o mundo: a corretora A (dona do pedido), a corretora B, o CANAL e uma técnica
# =====================================================================================================================
A, B, CANAL, TECNICA = (str(uuid.uuid4()) for _ in range(4))
COB = {"tipoPadronizado": "Compreensiva", "casco": 100, "carroReserva": "Carro reserva 15 dias", "vidros": "Completo",
       "assist24hs": "Completa"}


def _oferta(calc, seg, cod, premio, *, comissao=15.0, pacote="Tradicional", cob=None, franquia="Reduzida"):
    return {"id": str(uuid.uuid4()), "calculo_id": calc["id"], "pedido_id": calc["pedido_id"],
            "company_id": calc["company_id"], "solicitante_company_id": calc["solicitante_company_id"],
            "seguradora": seg, "seguradora_codigo": cod, "pacote": pacote, "tipo_de_pacote": 0, "premio_total": premio,
            "franquia_valor": 5000.0, "franquia_tipo": franquia, "coberturas": dict(cob or COB), "parcelamentos": [],
            "tem_pdf": False, "alertas": [], "comissao_percentual": comissao}


def _mundo(config_de_a=None):
    db = Banco()
    for cid, kind in ((A, "client"), (B, "client"), (CANAL, "platform_canal"), (TECNICA, "platform_knowledge")):
        db.tabelas.setdefault("companies", []).append({"id": cid, "company_kind": kind})
    if config_de_a is not None:
        db.tabelas["multicalculo_config"] = [{"company_id": A, "config": config_de_a}]
    pedido = {"id": str(uuid.uuid4()), "company_id": A, "origem": "auxiliar", "ramo": 31, "opcoes": ["padrao"],
              "corretoras": [A], "status": "fechado", "criado_em": "2026-10-06T08:00:00"}
    db.tabelas["multicalculo_pedidos"] = [pedido]
    calc = {"id": str(uuid.uuid4()), "pedido_id": pedido["id"], "solicitante_company_id": A, "company_id": A,
            "opcao": "padrao", "coberturas": {"tipoFranquia": 1}, "status": "fechado", "negocio_ref": "neg-1",
            "versao": 1, "prioridade": 5, "disponivel_em": "2026-10-06T08:00:00", "criado_em": "2026-10-06T08:00:00"}
    db.tabelas["multicalculo_calculos"] = [calc]
    db.tabelas["multicalculo_ofertas"] = [
        _oferta(calc, "Bradesco", 1, 4458.32), _oferta(calc, "Porto Seguro", 8, 4700.0),
        _oferta(calc, "Tokio", 11, 5000.0),
        _oferta(calc, "Tokio", 11, 2900.0, pacote="Auto Roubo", cob={"tipoPadronizado": "Roubo/Furto", "casco": 100}),
    ]
    db.tabelas["multicalculo_eventos"] = []
    return db, pedido, calc


def _porta(db):
    return MulticalculoProvider(RepositorioMulticalculo(db), cifrar=lambda t: t, presets=lambda o: {}, ambiente={})


def rodar(coro):
    return asyncio.run(coro)


def _ajustes_na_fila(db):
    return [c for c in db.linhas("multicalculo_calculos") if c.get("opcao") == "ajuste"]


# =====================================================================================================================
# a ORDEM (puro) — D-MC-67 · D-MC-63 (desconto onde a seguradora ignora a comissão) · o piso
# =====================================================================================================================
def _o(seg, cod, comissao=15.0, **kw):
    return {"id": "o", "calculo_id": "c", "seguradora": seg, "seguradora_codigo": cod, "premio_total": 1000.0,
            "comissao_percentual": comissao, "franquia_tipo": kw.get("franquia", "Reduzida"),
            "coberturas": kw.get("cob", COB)}


def test_a_ordem_margem_antes_de_cobertura_e_o_botao_por_seguradora():
    # SPEC-130-A.1 (D-MC-68 corrigida): a margem desce PASSO A PASSO (15 → 14 → 13 → 12), nunca direto
    bra = N.ordem_do_mais_barato(_o("Bradesco", 1))
    assert [p.id for p in bra] == ["comissao:14.0", "comissao:13.0", "comissao:12.0", "franquia:normal",
                                   "carro_reserva:7 dias", "vidros:basico", "assistencia:basica"]
    assert [p.corta_cobertura for p in bra] == [False, False, False, True, True, True, True]
    assert all(p.ajuste.seguradora == 1 for p in bra) and not any(p.fechamento for p in bra)
    porto = N.ordem_do_mais_barato(_o("Porto Seguro", 8))
    assert [p.id for p in porto][:4] == ["desconto:1.0", "desconto:2.0", "desconto:3.0", "franquia:normal"]
    assert porto[2].comissao_resultante == 12.0 and not any(p.alavanca == "comissao" for p in porto)
    # a lista vem da CONFIG, não do código
    sem_lista = mesclar({"seguradoras_que_obedecem_desconto": []})
    assert N.ordem_do_mais_barato(_o("Porto Seguro", 8), config=sem_lista)[0].id == "comissao:14.0"
    # o desconto que a seguradora libera (①), quando a corretora o configurou
    com_desc = mesclar({"desconto_permitido_pct": {"Bradesco": 4}})
    assert [p.id for p in N.ordem_do_mais_barato(_o("Bradesco", 1), config=com_desc)][:2] == ["desconto:4.0",
                                                                                            "comissao:14.0"]
    # o que já está no corte não vira passo · sem código de seguradora → nenhum passo
    ja = _o("Bradesco", 1, franquia="Normal", cob=dict(COB, carroReserva="7 dias", vidros="Básico", assist24hs="Básica"))
    assert [p.id for p in N.ordem_do_mais_barato(ja)] == ["comissao:14.0", "comissao:13.0", "comissao:12.0"]
    assert N.ordem_do_mais_barato(_o("Bradesco", None)) == []


def test_o_piso_sem_aprovacao_so_no_fechamento_e_nunca_abaixo():
    # §9.3: a regra vencida ("o piso só com concorrência E aprovação") saiu; a lição MIGRA — o piso continua sendo
    # o chão, agora alcançado SOZINHO e só quando o cliente sinaliza que fecha (`fechamento=True`)
    sem = N.ordem_do_mais_barato(_o("Bradesco", 1))
    assert all(p.comissao_resultante >= 12.0 for p in sem if p.alavanca == "comissao")
    com = N.ordem_do_mais_barato(_o("Bradesco", 1), fechamento=True)
    margem = [p for p in com if p.alavanca == "comissao"]
    assert [(p.ajuste.valor, p.fechamento) for p in margem] == [(14.0, False), (13.0, False), (12.0, False),
                                                                (11.0, True), (10.0, True)]
    porto = [p for p in N.ordem_do_mais_barato(_o("Porto", 8), fechamento=True) if p.alavanca == "desconto"]
    assert [(p.ajuste.valor, p.fechamento) for p in porto] == [(1.0, False), (2.0, False), (3.0, False), (4.0, True),
                                                               (5.0, True)]
    # já em 12: só a alavanca (com fechamento); já no piso: nenhuma margem; nunca abaixo do piso da corretora
    assert [p.id for p in N.ordem_do_mais_barato(_o("Bradesco", 1, comissao=12.0), fechamento=True)
            if p.alavanca == "comissao"] == ["comissao:11.0", "comissao:10.0"]
    assert not [p for p in N.ordem_do_mais_barato(_o("Bradesco", 1, comissao=10.0), fechamento=True)
                if p.alavanca == "comissao"]
    piso_alto = mesclar({"comissao": {"piso": 11.0}})
    valores = [p.ajuste.valor for p in N.ordem_do_mais_barato(_o("Bradesco", 1), config=piso_alto,
                                                              fechamento=True) if p.alavanca == "comissao"]
    assert valores == [14.0, 13.0, 12.0, 11.0] and min(valores) >= 11.0


def test_planejar_passo_a_passo_e_o_fechamento_guardado():
    ofertas = [dict(_o("Bradesco", 1), id="b", premio_total=4458.32), dict(_o("Porto Seguro", 8), id="p", premio_total=4700.0),
               dict(_o("Tokio", 11), id="t", premio_total=5000.0), dict(_o("Mapfre", 3), id="m", premio_total=5100.0)]
    assert N.planejar(ofertas, alvo=4500)["status"] == "ja_no_alvo"
    plano = N.planejar(ofertas, alvo=4300)
    assert plano["status"] == "planejado" and plano["fechamento_disponivel"] is True
    # o 1º degrau de todas antes do 2º de qualquer; o teto (6) corta a etapa — a cobertura nem entra nesta
    assert [(t["seguradora"], t["passos"]) for t in plano["tentativas"]] == [
        ("Bradesco", ["comissao:14.0"]), ("Porto", ["desconto:1.0"]), ("Tokio Marine", ["comissao:14.0"]),
        ("Bradesco", ["comissao:13.0"]), ("Porto", ["desconto:2.0"]), ("Tokio Marine", ["comissao:13.0"])]
    assert plano["fora_do_teto"] > 0
    assert "Mapfre" not in {t["seguradora"] for t in plano["tentativas"]}          # teto de seguradoras
    assert all(t["passo"]["comissao_resultante"] >= 12.0 for t in plano["tentativas"])
    # com o fechamento pedido e sem teto: o piso entra SEM aprovação humana e SEM concorrência declarada
    grande = mesclar({"negociacao": {"max_tentativas_por_etapa": 50}})
    ok = N.planejar(ofertas, alvo=4300, config=grande, fechamento=True)
    assert {"comissao:10.0", "desconto:5.0"} <= {t["passo"]["id"] for t in ok["tentativas"]}
    assert ok["fechamento_disponivel"] is False and "precisa_aprovacao" not in ok
    sem = N.planejar(ofertas, alvo=4300, config=grande)
    assert not any(t["passo"]["comissao_resultante"] < 12.0 for t in sem["tentativas"])
    assert N.planejar(ofertas, alvo=4300, seguradora="Porto")["tentativas"][0]["seguradora"] == "Porto"


def test_escolher_margem_antes_de_cobertura_e_a_maior_comissao():
    def r(passos, premio, com):
        return {"calculo_id": "x", "passos": passos, "comissao_resultante": com,
                "oferta": {"id": "o", "seguradora": "Bradesco", "seguradora_codigo": 1, "premio_total": premio}}
    # o corte chega mais barato e com comissão MAIOR, mas a margem chega também → a margem vence (D-MC-67)
    d = N.escolher([r(["franquia:normal"], 4100, 15.0), r(["comissao:12.0"], 4290, 12.0)], alvo=4300)
    assert d["status"] == "chegou" and d["escolhida"]["passos"] == ["comissao:12.0"] and d["corta_cobertura"] == []
    # entre margens, a MAIOR comissão
    d = N.escolher([r(["comissao:12.0"], 4290, 12.0), r(["comissao:12.0", "comissao:10.0"], 4000, 10.0)], alvo=4300)
    assert d["escolhida"]["comissao_percentual"] == 12.0
    # só o corte chega: listado, e a recomendação segue a config
    d = N.escolher([r(["franquia:normal"], 4100, 15.0)], alvo=4300)
    assert d["corta_cobertura"] == ["franquia"] and d["recomenda"] is True
    d = N.escolher([r(["vidros:basico"], 4100, 15.0)], alvo=4300)
    assert d["recomenda"] is False and "NÃO recomendo" in d["recomendacao"]
    assert N.escolher([r(["comissao:12.0"], 4400, 12.0)], alvo=4300)["status"] == "nao_chegou"


# =====================================================================================================================
# a PORTA — assíncrona, só a dona, autorização antes de qualquer efeito
# =====================================================================================================================
def test_cotacao_alvo_enfileira_pela_recalcular_e_o_repetido_nao_duplica():
    db, pedido, calc = _mundo()
    porta = _porta(db)
    r = rodar(porta.cotacao_alvo(company_id=A, pedido_id=pedido["id"], alvo=4300))
    assert r["status"] == "em_andamento" and r["custo"] == "1 recálculo da corretora inteira por tentativa"
    fila = _ajustes_na_fila(db)
    assert len(fila) == len(r["tentativas"]) == PADRAO_DO_PRODUTO["negociacao"]["max_tentativas_por_etapa"]
    assert {c["id"] for c in fila} == {t["calculo_id"] for t in r["tentativas"]}
    assert all(c["origem_calculo_id"] == calc["id"] and c["status"] == "na_fila" and c["company_id"] == A for c in fila)
    # passo a passo (D-MC-68 corrigida): a 1ª etapa é só MARGEM, os degraus menores primeiro, nada abaixo de 12
    margem_bra = sorted(c["ajuste"]["valor"] for c in fila if c["ajuste"]["tipo"] == "comissao"
                        and c["ajuste"]["seguradora"] == 1)
    assert margem_bra == [13.0, 14.0]
    assert not any(c["ajuste"]["tipo"] == "comissao" and c["ajuste"]["valor"] < 12.0 for c in fila)
    assert r["fechamento_disponivel"] is True and "precisa_aprovacao" not in r
    assert "Auto Roubo" not in str(r)                                           # o pacote sem batida não negocia
    assert db.linhas("multicalculo_pedidos")[0]["status"] == "aberto"            # o pedido fechado foi reaberto
    # o MESMO pedido de novo → `repetido`, nenhuma linha nova
    r2 = rodar(porta.cotacao_alvo(company_id=A, pedido_id=pedido["id"], alvo=4300))
    assert all(t["repetido"] for t in r2["tentativas"]) and len(_ajustes_na_fila(db)) == len(fila)


def test_o_corte_de_cobertura_vai_codificado_e_so_depois_da_margem():
    # a lição da 130-A (o rótulo "normal" vira o CÓDIGO medido) migra: com a margem passo a passo, o corte só entra
    # numa etapa com espaço — aqui, sem o teto
    db, pedido, calc = _mundo(config_de_a={"negociacao": {"max_tentativas_por_etapa": 50}})
    r = rodar(_porta(db).cotacao_alvo(company_id=A, pedido_id=pedido["id"], alvo=4300, seguradora="Bradesco"))
    ids = [t["passo"]["id"] for t in r["tentativas"]]
    assert ids[:4] == ["comissao:14.0", "comissao:13.0", "comissao:12.0", "franquia:normal"]
    franquia = next(c for c in _ajustes_na_fila(db) if c["ajuste"]["tipo"] == "franquia")
    assert franquia["ajuste"]["valor"] == 2 and franquia["ajuste"]["seguradora"] == 1   # "normal" → o CÓDIGO medido


def test_o_canal_nao_negocia_e_a_outra_corretora_nao_le():
    db, pedido, calc = _mundo()
    porta = _porta(db)
    antes = len(db.log)
    r = rodar(porta.cotacao_alvo(company_id=CANAL, pedido_id=pedido["id"], alvo=4300))
    assert r["status"] == "so_a_corretora_negocia"
    assert db.log[antes:] == [("companies", "select")]                        # nada lido além do tipo, nada gravado
    o = rodar(porta.ordem_do_mais_barato(company_id=CANAL, oferta_ref={"pedido_id": pedido["id"],
                                                                       "oferta_id": db.linhas("multicalculo_ofertas")[0]["id"]}))
    assert o["status"] == "so_a_corretora_negocia"
    with pytest.raises(NaoEncontrado):
        rodar(porta.cotacao_alvo(company_id=B, pedido_id=pedido["id"], alvo=4300))
    with pytest.raises(NaoAutorizado):
        rodar(porta.cotacao_alvo(company_id=TECNICA, pedido_id=pedido["id"], alvo=4300))
    assert not any(op == "insert" for _t, op in db.log) and _ajustes_na_fila(db) == []


def test_ordem_do_mais_barato_pela_porta_le_a_config_da_corretora():
    db, pedido, calc = _mundo(config_de_a={"seguradoras_que_obedecem_desconto": ["bradesco"]})
    porta = _porta(db)
    bra = next(o for o in db.linhas("multicalculo_ofertas") if o["seguradora"] == "Bradesco")
    r = rodar(porta.ordem_do_mais_barato(company_id=A, oferta_ref={"pedido_id": pedido["id"], "oferta_id": bra["id"]}))
    assert r["status"] == "ok" and r["passos"][0]["id"] == "desconto:1.0"          # a CONFIG dela trocou o botão
    assert [p["id"] for p in r["passos"]][:3] == ["desconto:1.0", "desconto:2.0", "desconto:3.0"]   # passo a passo
    assert not any(p["fechamento"] for p in r["passos"])                        # a alavanca só com `fechamento`
    rf = rodar(porta.ordem_do_mais_barato(company_id=A, oferta_ref={"pedido_id": pedido["id"], "oferta_id": bra["id"]},
                                          fechamento=True))
    assert [p["id"] for p in rf["passos"] if p["fechamento"]] == ["desconto:4.0", "desconto:5.0"]
    assert r["ajustes"][0].tipo == "desconto" and r["ajustes"][0].seguradora == 1
    with pytest.raises(NaoEncontrado):
        rodar(porta.ordem_do_mais_barato(company_id=A, oferta_ref={"pedido_id": pedido["id"],
                                                                   "oferta_id": str(uuid.uuid4())}))


def _motor_responde(db, tentativas, precos, *, extra=None):
    """Como o motor gravaria: cada ajuste fecha com negócio e devolve a oferta da seguradora dele."""
    calcs = {c["id"]: c for c in db.linhas("multicalculo_calculos")}
    for t in tentativas:
        c = calcs[t["calculo_id"]]
        c.update({"status": "fechado", "negocio_ref": "neg-" + c["id"][:6], "versao": 2})
        chave = (t["seguradora_codigo"], t["passos"][-1])
        if chave in precos:
            premio, com = precos[chave]
            seg = {1: "Bradesco", 8: "Porto Seguro", 11: "Tokio"}[t["seguradora_codigo"]]
            db.tabelas["multicalculo_ofertas"].append(_oferta(c, seg, t["seguradora_codigo"], premio, comissao=com))
    for (calc_id, oferta) in (extra or []):
        db.tabelas["multicalculo_ofertas"].append(_oferta(calcs[calc_id], *oferta))


def test_avaliar_espera_depois_escolhe_a_margem_e_ignora_o_pacote_sem_batida():
    db, pedido, calc = _mundo()
    porta = _porta(db)
    r = rodar(porta.cotacao_alvo(company_id=A, pedido_id=pedido["id"], alvo=4300))
    tent = r["tentativas"]
    av = rodar(porta.avaliar_cotacao_alvo(company_id=A, pedido_id=pedido["id"], alvo=4300, tentativas=tent))
    assert av == {"status": "em_andamento", "pendentes": len(tent), "total": len(tent)}
    tokio_c13 = next(t for t in tent if t["seguradora_codigo"] == 11 and t["passos"] == ["comissao:13.0"])
    # a Tokio NÃO devolveu o pacote completo no recálculo — só o "Auto Roubo" de 1.999 (sem batida, abaixo do alvo)
    _motor_responde(db, tent, {(1, "comissao:14.0"): (4390.0, 14.0), (1, "comissao:13.0"): (4290.0, 13.0),
                               (8, "desconto:2.0"): (4560.0, 15.0)},
                    extra=[(tokio_c13["calculo_id"], ("Tokio", 11, 1999.0))])
    db.tabelas["multicalculo_ofertas"][-1].update(pacote="Auto Roubo", coberturas={"tipoPadronizado": "Roubo/Furto"},
                                                  comissao_percentual=13.0)
    av = rodar(porta.avaliar_cotacao_alvo(company_id=A, pedido_id=pedido["id"], alvo=4300, tentativas=tent))
    assert av["status"] == "chegou" and av["escolhida"]["seguradora"] == "Bradesco"
    assert av["escolhida"]["passos"] == ["comissao:13.0"] and av["corta_cobertura"] == [] and av["recomenda"]
    assert av["fechamento"] is None                                            # na margem normal, sem alavanca
    assert "_oferta" not in av["escolhida"]
    # o canal não avalia
    assert rodar(porta.avaliar_cotacao_alvo(company_id=CANAL, pedido_id=pedido["id"], alvo=4300,
                                            tentativas=tent))["status"] == "so_a_corretora_negocia"


def test_nao_chegou_vira_etapa_encadeada_sobre_o_melhor_parcial():
    db, pedido, calc = _mundo()
    porta = _porta(db)
    tent = rodar(porta.cotacao_alvo(company_id=A, pedido_id=pedido["id"], alvo=4000))["tentativas"]
    _motor_responde(db, tent, {(1, "comissao:13.0"): (4290.0, 13.0), (1, "comissao:14.0"): (4350.0, 14.0),
                               (8, "desconto:2.0"): (4560.0, 15.0)})
    av = rodar(porta.avaliar_cotacao_alvo(company_id=A, pedido_id=pedido["id"], alvo=4000, tentativas=tent))
    assert av["status"] == "proxima_etapa"
    parcial = av["melhor_parcial"]
    assert parcial["premio_anual"] == 4290.0 and parcial["passos"] == ["comissao:13.0"]
    assert all(t["passos"][0] == "comissao:13.0" and len(t["passos"]) == 2 for t in av["tentativas"])
    assert all(t["origem_calculo_id"] == parcial["calculo_id"] for t in av["tentativas"])
    # passo a passo continua de onde parou (13 → 12) e a margem já atingida segue junto nos cortes; sem o fechamento
    # pedido, nada abaixo de 12 — e a alavanca segue guardada
    assert av["tentativas"][0]["passos"] == ["comissao:13.0", "comissao:12.0"]
    assert all(t["comissao_resultante"] in (12.0, 13.0) for t in av["tentativas"])
    assert av["fechamento_disponivel"] is True
    # enfileira a etapa encadeada pela mesma porta
    antes = len(_ajustes_na_fila(db))
    r2 = rodar(porta.cotacao_alvo(company_id=A, pedido_id=pedido["id"], alvo=4000, tentativas_anteriores=tent))
    assert r2["status"] == "em_andamento" and len(_ajustes_na_fila(db)) == antes + len(r2["tentativas"])
    assert all(c["origem_calculo_id"] == parcial["calculo_id"] for c in _ajustes_na_fila(db)[antes:])


def test_sem_passo_restante_e_nao_recomendo():
    oferta = {"id": "o", "seguradora": "Bradesco", "seguradora_codigo": 1, "premio_total": 4400.0,
              "comissao_percentual": 12.0, "franquia_tipo": "Normal",
              "coberturas": dict(COB, carroReserva="7 dias", vidros="Básico", assist24hs="Básica")}
    r = [{"calculo_id": "x", "passos": ["comissao:12.0", "franquia:normal"], "comissao_resultante": 12.0,
          "oferta": oferta}]
    e = N.proxima_etapa(r, alvo=4000)
    assert e["status"] == "sem_caminho" and e["recomendacao"].startswith("não recomendo")
    assert e["fechamento_disponivel"] is True                                  # ainda há a última cartada


def test_o_fio_do_fechamento_pela_porta_ate_a_frase():
    """O FIO da fatia: porta.cotacao_alvo(fechamento=True) → negociacao.planejar → recalcular (a fila real) → o motor
    devolve os preços → porta.avaliar_cotacao_alvo → negociacao.escolher → a alavanca em REAIS. Sem o fechamento, o
    mesmo pedido nunca enfileira degrau abaixo de 12. Só o transporte é dublê."""
    cfg = {"negociacao": {"max_tentativas_por_etapa": 50}}
    db0, pedido0, _ = _mundo(config_de_a=cfg)
    r0 = rodar(_porta(db0).cotacao_alvo(company_id=A, pedido_id=pedido0["id"], alvo=4100, seguradora="Bradesco"))
    assert r0["fechamento_disponivel"] is True
    assert not any(c["ajuste"]["tipo"] == "comissao" and c["ajuste"]["valor"] < 12.0 for c in _ajustes_na_fila(db0))

    db, pedido, calc = _mundo(config_de_a=cfg)
    porta = _porta(db)
    r = rodar(porta.cotacao_alvo(company_id=A, pedido_id=pedido["id"], alvo=4100, seguradora="Bradesco",
                                 fechamento=True))
    assert r["status"] == "em_andamento" and r["fechamento_disponivel"] is False
    na_fila = sorted(c["ajuste"]["valor"] for c in _ajustes_na_fila(db) if c["ajuste"]["tipo"] == "comissao")
    assert na_fila == [10.0, 11.0, 12.0, 13.0, 14.0]                           # sem aprovação humana, até o piso
    tent = r["tentativas"]
    _motor_responde(db, tent, {(1, "comissao:14.0"): (4400.0, 14.0), (1, "comissao:13.0"): (4350.0, 13.0),
                               (1, "comissao:12.0"): (4300.0, 12.0), (1, "comissao:11.0"): (4180.0, 11.0),
                               (1, "comissao:10.0"): (4060.0, 10.0), (1, "franquia:normal"): (3990.0, 15.0)})
    av = rodar(porta.avaliar_cotacao_alvo(company_id=A, pedido_id=pedido["id"], alvo=4100, tentativas=tent,
                                          fechamento=True))
    assert av["status"] == "chegou" and av["corta_cobertura"] == []              # fecha SEM tirar cobertura
    assert av["escolhida"]["passos"] == ["comissao:10.0"]
    f = av["fechamento"]
    assert (f["preco_antes"], f["preco_depois"], f["diferenca"]) == (4300.0, 4060.0, 240.0)
    assert f["texto"]["corretora"] == ("Falei com a seguradora e consegui R$ 240 a menos no ano (fica R$ 4.060 por "
                                       "ano). Vale se você fechar comigo.")
    assert "%" not in f["texto"]["corretora"] and "%" not in f["texto"]["canal"]
