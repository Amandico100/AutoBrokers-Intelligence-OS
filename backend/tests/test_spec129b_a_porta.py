# -*- coding: utf-8 -*-
"""SPEC-129-B · F1 — A PORTA do multicálculo: o FIO da fatia, o isolamento com DOIS tenants + o canal, a comissão,
as origens, a renovação, o cofre de 2 chaves e a recusa do `agger` na tela de credenciais.

O FIO DA FATIA (a 1ª entrega):
    porta.calcular → autorização → repositorio grava pedido + cálculos (banco DUBLÊ em memória)
    → o "motor" grava ofertas/eventos À MÃO, como o motor gravaria (F3 é a outra fatia)
    → porta.consultar por CADA tenant → isolamento e comissão.
O motor (porta + repositório + pedido) roda INTEIRO; só o transporte (PostgREST) é dublê. O dublê é BURRO de
propósito: compara igualdade e ordena — quem sabe de tenant é a porta e o repositório (o que os guardas medem).
⚠️ O que o dublê NÃO prova: CHECK, FK composta e unique do banco — isso é `test_spec129b_o_banco.py` (G7).

Gates: G1 · G2 · G9 (smith-api) · G10 (parte da porta) · G13 (porta) · D-129B-11. Mutações: ver a entrega da F1.
⛔ Dado SINTÉTICO: CPF/placa/nome inventados; nenhum nome de corretora (uuids gerados aqui, §13.9).
"""
from __future__ import annotations

import asyncio
import copy
import json
import types
import uuid
from datetime import date
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from app.services.multicalculo import (
    ChaveAusente,
    MulticalculoProvider,
    NaoAutorizado,
    NaoEncontrado,
    OrigemRecusada,
    PedidoDeCalculo,
    PedidoIncompleto,
    PerfilIncompleto,
    de_apolice,
)
from app.services.multicalculo.pedido import OBRIGATORIOS
from app.services.multicalculo.porta import cpf_hmac
from app.services.multicalculo.repositorio import RepositorioMulticalculo
from portal_worker.multicalculo.contrato import CAMPOS_DO_PEDIDO_AUTO

BACKEND = Path(__file__).resolve().parents[1]
FIXTURE_INFOCAP = BACKEND / "tests" / "fixtures" / "infocap_contract_shapes" / "policy_chain_top_level_lists.json"


# =====================================================================================================================
# o banco DUBLÊ — só o transporte
# =====================================================================================================================
class _Resp:
    def __init__(self, data):
        self.data = data


class _Consulta:
    def __init__(self, banco: "Banco", tabela: str):
        self.banco, self.tabela = banco, tabela
        self.op, self.payload, self.filtros, self._ordem, self._limite = "select", None, [], None, None

    # verbos
    def select(self, *_a, **_k):
        self.op = "select"
        return self

    def insert(self, linhas):
        self.op, self.payload = "insert", linhas
        return self

    def update(self, patch):
        self.op, self.payload = "update", patch
        return self

    def delete(self):
        self.op = "delete"
        return self

    # filtros
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

    def _casa(self, l):
        return all(f(l) for f in self.filtros)

    def execute(self):
        linhas = self.banco.tabelas.setdefault(self.tabela, [])
        self.banco.log.append((self.tabela, self.op))
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
                if self._casa(l):
                    l.update(copy.deepcopy(self.payload))
                    saida.append(copy.deepcopy(l))
            return _Resp(saida)
        if self.op == "delete":
            fora = [l for l in linhas if self._casa(l)]
            self.banco.tabelas[self.tabela] = [l for l in linhas if not self._casa(l)]
            return _Resp(fora)
        saida = [copy.deepcopy(l) for l in linhas if self._casa(l)]
        if self._ordem:
            c, desc = self._ordem
            saida.sort(key=lambda l: (l.get(c) is None, l.get(c)), reverse=desc)
        if self._limite is not None:
            saida = saida[: self._limite]
        return _Resp(saida)


class Banco:
    def __init__(self):
        self.tabelas: dict = {}
        self.log: list = []

    def table(self, nome):
        return _Consulta(self, nome)

    def linhas(self, nome):
        return self.tabelas.get(nome, [])


# =====================================================================================================================
# o mundo: DUAS corretoras + o canal + um cliente forjador + uma técnica (uuids gerados, nenhum nome)
# =====================================================================================================================
A, B, C, X = (str(uuid.uuid4()) for _ in range(4))      # clientes: A e B aderidas ao canal; C sem adesão; X forja
CANAL = str(uuid.uuid4())
TECNICA = str(uuid.uuid4())
CHAVE_HMAC = "chave-hmac-sintetica-de-teste-0123456789"
CHAVE_COFRE = Fernet.generate_key()
PRESETS = {"padrao": {"franquia": "reduzida", "vidros": "completo", "carro_reserva": 15},
           "economica": {"franquia": "normal", "vidros": "basico", "carro_reserva": 7}}


def _mundo():
    db = Banco()
    for cid, kind in ((A, "client"), (B, "client"), (C, "client"), (X, "client"),
                      (CANAL, "platform_canal"), (TECNICA, "platform_knowledge")):
        db.tabelas.setdefault("companies", []).append({"id": cid, "company_kind": kind})
    for canal, corretora in ((CANAL, A), (CANAL, B), (X, A)):      # (X, A): adesão FORJADA por um cliente
        db.tabelas.setdefault("multicalculo_adesoes", []).append(
            {"id": str(uuid.uuid4()), "canal_company_id": canal, "corretora_company_id": corretora, "ativa": True})
    return db


def _porta(db, *, ambiente=None):
    env = {"MULTICALCULO_HMAC_KEY": CHAVE_HMAC} if ambiente is None else ambiente
    return MulticalculoProvider(RepositorioMulticalculo(db), cifrar=lambda t: Fernet(CHAVE_COFRE).encrypt(
        t.encode()).decode(), presets=lambda o: PRESETS[o], ambiente=env)


# 💭 dado SINTÉTICO (CPF com dígito válido inventado; placa e nome inventados)
CPF = "52998224725"


def _dados(perfil=True):
    d = {
        "segurado": {"cpf_cnpj": "529.982.247-25", "nome": "Pessoa Sintetica", "nascimento": "01/02/1980",
                     "sexo": "M", "estado_civil": "casado", "cep": "01001-000"},
        "veiculo": {"fipe": "001234-5", "ano_fabricacao": 2020, "combustivel": "flex", "placa": "abc-1d23"},
        "pernoite": {"cep_pernoite": "01001000"},
        "condutor": {"cpf": CPF, "nome": "Pessoa Sintetica", "nascimento": "1980-02-01", "sexo": "M",
                     "estado_civil": "casado", "tempo_habilitacao": 20},
    }
    if perfil:
        d["pernoite"]["garagem_residencia"] = "sim"
        d["veiculo"]["uso"] = "particular"
        d["questionario"] = {"km_mensal": 800}
        d["condutor"]["jovem_condutor"] = False
    return d


def _pedido(perfil=True):
    return PedidoDeCalculo.de_dict(_dados(perfil))


def rodar(coro):
    return asyncio.run(coro)


def _motor_grava(db, calculo, *, premio, comissao, seguradora="Seguradora Sintetica", codigo=1, n_evento=None):
    """Como o motor (F3) gravaria: negócio no cálculo, 1 oferta, 1 evento — com as 4 colunas do cálculo."""
    calculo.update({"status": "calculando", "negocio_ref": "neg-" + calculo["id"][:8], "versao": 0})
    oferta = {"id": str(uuid.uuid4()), "calculo_id": calculo["id"], "pedido_id": calculo["pedido_id"],
              "company_id": calculo["company_id"], "solicitante_company_id": calculo["solicitante_company_id"],
              "seguradora": seguradora, "seguradora_codigo": codigo, "pacote": "Completo", "tipo_de_pacote": 1,
              "premio_total": premio, "comissao_percentual": comissao, "tem_pdf": False, "alertas": []}
    db.tabelas.setdefault("multicalculo_ofertas", []).append(oferta)
    eventos = db.tabelas.setdefault("multicalculo_eventos", [])
    eventos.append({"id": n_evento or len(eventos) + 1, "calculo_id": calculo["id"], "pedido_id": calculo["pedido_id"],
                    "company_id": calculo["company_id"], "solicitante_company_id": calculo["solicitante_company_id"],
                    "tipo": "nova_oferta", "seguradora": seguradora, "seguradora_codigo": codigo,
                    "oferta_id": oferta["id"], "chave": f"nova_oferta|{codigo}|{premio}"})
    return oferta


# =====================================================================================================================
# O TESTE DO FIO (a 1ª entrega)
# =====================================================================================================================
def test_o_fio_canal_calcula_em_duas_corretoras_e_cada_um_le_so_o_seu():
    db = _mundo()
    porta = _porta(db)
    aberto = rodar(porta.calcular(company_id=CANAL, pedido=_pedido(), corretoras=[A, B], origem="canal"))

    # ① gravou 1 pedido do CANAL + 2 corretoras × 2 opções na FILA
    pedidos = db.linhas("multicalculo_pedidos")
    calcs = db.linhas("multicalculo_calculos")
    assert len(pedidos) == 1 and pedidos[0]["company_id"] == CANAL and pedidos[0]["origem"] == "canal"
    assert sorted((c["company_id"], c["opcao"]) for c in calcs) == sorted(
        [(A, "padrao"), (A, "economica"), (B, "padrao"), (B, "economica")])
    assert all(c["status"] == "na_fila" and c["solicitante_company_id"] == CANAL and c["prioridade"] == 0
               and c["expira_em"] for c in calcs)
    assert {c["opcao"]: c["coberturas"] for c in calcs} == PRESETS
    assert len(aberto.calculos) == 4 and aberto.pedido_id == pedidos[0]["id"]

    # ② o pedido está CIFRADO (nenhum dado pessoal em claro em linha nenhuma) e decifra no formato do contrato
    bruto = json.dumps(db.tabelas, default=str)
    for segredo in (CPF, "Pessoa Sintetica", "ABC1D23", "01001000"):
        assert segredo not in bruto
    claro = json.loads(Fernet(CHAVE_COFRE).decrypt(pedidos[0]["pedido_cifrado"].encode()))
    assert set(CAMPOS_DO_PEDIDO_AUTO) <= set(claro) and claro["ramo"] == 31
    assert claro["segurado"]["cpf_cnpj"] == CPF and claro["veiculo"]["placa"] == "ABC1D23"
    assert claro["coberturas"] == {} and claro["pacotes"] == {}
    assert pedidos[0]["cpf_hmac"] == cpf_hmac(CPF, chave=CHAVE_HMAC) and len(pedidos[0]["cpf_hmac"]) == 64

    # ③ o "motor" grava (à mão): A comissão 20 % a 1500; B comissão 25 % a 1200
    por = {(c["company_id"], c["opcao"]): c for c in calcs}
    _motor_grava(db, por[(A, "padrao")], premio=1500.0, comissao=20.0, codigo=1)
    _motor_grava(db, por[(B, "padrao")], premio=1200.0, comissao=25.0, codigo=2)

    # ④ o CANAL (solicitante, com adesão) lê as duas, menor preço primeiro, SEM comissão
    and_canal = rodar(porta.consultar(company_id=CANAL, pedido_id=aberto.pedido_id))
    assert [o["premio_total"] for o in and_canal.ofertas] == [1200.0, 1500.0]
    assert {o["corretora_company_id"] for o in and_canal.ofertas} == {A, B}
    assert all(o["comissao_percentual"] is None for o in and_canal.ofertas)          # G2
    assert len(and_canal.eventos) == 2 and and_canal.ultimo_evento == 2
    assert len(and_canal.estados) == 4
    assert rodar(porta.consultar(company_id=CANAL, pedido_id=aberto.pedido_id, desde_evento=1)).eventos[0]["id"] == 2

    # ⑤ a corretora A NÃO lê o pedido do canal; B também não (o pedido é de quem PEDIU)
    for intruso in (A, B, C):
        with pytest.raises(NaoEncontrado):
            rodar(porta.consultar(company_id=intruso, pedido_id=aberto.pedido_id))


def test_g1_g2_a_corretora_le_o_proprio_pedido_com_comissao_e_a_outra_nao_le():
    db = _mundo()
    porta = _porta(db)
    pa = rodar(porta.calcular(company_id=A, pedido=_pedido(), opcoes=["padrao"], origem="auxiliar"))
    pb = rodar(porta.calcular(company_id=B, pedido=_pedido(), opcoes=["padrao"], origem="auxiliar"))
    ca = next(c for c in db.linhas("multicalculo_calculos") if c["pedido_id"] == pa.pedido_id)
    cb = next(c for c in db.linhas("multicalculo_calculos") if c["pedido_id"] == pb.pedido_id)
    assert ca["company_id"] == A and ca["prioridade"] == 5          # corretoras=None → só a própria
    _motor_grava(db, ca, premio=900.0, comissao=18.0)
    _motor_grava(db, cb, premio=800.0, comissao=22.0)

    da_a = rodar(porta.consultar(company_id=A, pedido_id=pa.pedido_id))
    assert [(o["premio_total"], o["comissao_percentual"]) for o in da_a.ofertas] == [(900.0, 18.0)]   # G2: a dona vê
    assert all(e["corretora_company_id"] == A for e in da_a.eventos)
    with pytest.raises(NaoEncontrado):                       # G1: B não lê o pedido de A
        rodar(porta.consultar(company_id=B, pedido_id=pa.pedido_id))
    with pytest.raises(NaoEncontrado):                       # nem recalcula o cálculo de A
        rodar(porta.recalcular(company_id=B, calculo_id=ca["id"], ajuste={"tipo": "desconto", "valor": 5}))


def test_g1_sem_adesao_forjada_ou_tecnica_recusa_antes_de_gravar():
    db = _mundo()
    porta = _porta(db)
    casos = [
        (CANAL, [C]),          # canal sem adesão com C
        (X, [A]),              # cliente X com "adesão" forjada → só o CANAL calcula noutra corretora
        (A, [B]),              # corretora pedindo na outra
        (CANAL, [TECNICA]),    # alvo que não é corretora cliente
        (CANAL, [CANAL]),      # o canal não é corretora
        (CANAL, [A, C]),       # uma aderida e uma não → recusa TUDO
    ]
    for solicitante, corretoras in casos:
        with pytest.raises(NaoAutorizado):
            rodar(porta.calcular(company_id=solicitante, pedido=_pedido(), corretoras=corretoras, origem="canal"))
    assert db.linhas("multicalculo_pedidos") == [] and db.linhas("multicalculo_calculos") == []
    assert not any(op == "insert" for (_t, op) in db.log)


def test_g1_adesao_desativada_depois_o_canal_deixa_de_ver_e_de_recalcular():
    db = _mundo()
    porta = _porta(db)
    aberto = rodar(porta.calcular(company_id=CANAL, pedido=_pedido(), corretoras=[A, B], opcoes=["padrao"],
                                  origem="canal"))
    calcs = {c["company_id"]: c for c in db.linhas("multicalculo_calculos")}
    _motor_grava(db, calcs[A], premio=1000.0, comissao=10.0, codigo=1)
    _motor_grava(db, calcs[B], premio=1100.0, comissao=10.0, codigo=2)
    for ad in db.linhas("multicalculo_adesoes"):
        if ad["canal_company_id"] == CANAL and ad["corretora_company_id"] == B:
            ad["ativa"] = False
    andam = rodar(porta.consultar(company_id=CANAL, pedido_id=aberto.pedido_id))
    assert {o["corretora_company_id"] for o in andam.ofertas} == {A}
    assert {e["corretora_company_id"] for e in andam.eventos} == {A}
    assert {s["corretora_company_id"] for s in andam.estados} == {A}
    with pytest.raises(NaoAutorizado):
        rodar(porta.recalcular(company_id=CANAL, calculo_id=calcs[B]["id"], ajuste={"tipo": "desconto", "valor": 5}))


def test_g10_origem_teste_so_no_canario_e_origem_desconhecida_recusada():
    db = _mundo()
    with pytest.raises(OrigemRecusada):
        rodar(_porta(db).calcular(company_id=A, pedido=_pedido(), origem="teste"))
    with pytest.raises(OrigemRecusada):
        rodar(_porta(db, ambiente={"MULTICALCULO_HMAC_KEY": CHAVE_HMAC, "AUTOBROKERS_CANARIO": "0"}).calcular(
            company_id=A, pedido=_pedido(), origem="teste"))
    with pytest.raises(OrigemRecusada):
        rodar(_porta(db).calcular(company_id=A, pedido=_pedido(), origem="whatsapp"))
    assert db.linhas("multicalculo_pedidos") == []
    # CONTROLE: com o canário ligado, o mesmo pedido entra
    ok = _porta(db, ambiente={"MULTICALCULO_HMAC_KEY": CHAVE_HMAC, "AUTOBROKERS_CANARIO": "1"})
    rodar(ok.calcular(company_id=A, pedido=_pedido(), origem="teste"))
    assert [p["origem"] for p in db.linhas("multicalculo_pedidos")] == ["teste"]


def test_perfil_canal_pergunta_auxiliar_assume_e_obrigatorios_por_nome():
    db = _mundo()
    porta = _porta(db)
    with pytest.raises(PerfilIncompleto) as e:
        rodar(porta.calcular(company_id=CANAL, pedido=_pedido(perfil=False), corretoras=[A], origem="canal"))
    assert set(e.value.campos) == {"pernoite.garagem_residencia", "veiculo.uso", "questionario.km_mensal",
                                   "condutor.jovem_condutor"}
    rodar(porta.calcular(company_id=A, pedido=_pedido(perfil=False), origem="auxiliar"))
    claro = json.loads(Fernet(CHAVE_COFRE).decrypt(db.linhas("multicalculo_pedidos")[0]["pedido_cifrado"].encode()))
    assert {"pernoite.garagem_residencia", "veiculo.uso", "questionario.km_mensal",
            "condutor.jovem_condutor"} <= set(claro["assumidos"])

    dados = _dados()
    del dados["segurado"]["estado_civil"], dados["condutor"]["tempo_habilitacao"]
    with pytest.raises(PedidoIncompleto) as e2:
        rodar(porta.calcular(company_id=A, pedido=PedidoDeCalculo.de_dict(dados), origem="auxiliar"))
    assert e2.value.campos == ["segurado.estado_civil", "condutor.tempo_habilitacao"]
    assert CPF not in str(e2.value) and len(OBRIGATORIOS) == 16          # 📊 E3: 16 obrigatórios


def test_sem_chave_hmac_recusa_antes_de_gravar():
    db = _mundo()
    with pytest.raises(ChaveAusente):
        rodar(_porta(db, ambiente={}).calcular(company_id=A, pedido=_pedido(), origem="auxiliar"))
    assert db.linhas("multicalculo_pedidos") == []


def test_recalcular_nova_versao_na_mesma_corretora_a_partir_da_origem():
    db = _mundo()
    porta = _porta(db)
    aberto = rodar(porta.calcular(company_id=CANAL, pedido=_pedido(), corretoras=[A, B], origem="canal"))
    padrao_a = next(c for c in db.linhas("multicalculo_calculos") if c["company_id"] == A and c["opcao"] == "padrao")
    with pytest.raises(ValueError):          # ainda sem negócio no portal
        rodar(porta.recalcular(company_id=CANAL, calculo_id=padrao_a["id"], ajuste={"tipo": "desconto", "valor": 5}))
    padrao_a.update({"status": "fechado", "negocio_ref": "neg-1", "versao": 3})
    novo = rodar(porta.recalcular(company_id=CANAL, calculo_id=padrao_a["id"],
                                  ajuste={"tipo": "carro_reserva", "valor": 30}))
    linha = next(c for c in db.linhas("multicalculo_calculos") if c["id"] == novo["id"])
    assert linha["company_id"] == A and linha["opcao"] == "ajuste" and linha["origem_calculo_id"] == padrao_a["id"]
    assert linha["pedido_id"] == aberto.pedido_id and linha["solicitante_company_id"] == CANAL
    assert linha["coberturas"] == {**PRESETS["padrao"], "carro_reserva": 30}
    assert linha["ajuste"]["versao_base"] == 3 and linha["ajuste"]["negocio_ref"] == "neg-1"
    assert linha["status"] == "na_fila"


def test_cancelar_tira_da_fila_so_o_proprio_pedido():
    db = _mundo()
    porta = _porta(db)
    pa = rodar(porta.calcular(company_id=A, pedido=_pedido(), origem="auxiliar"))
    pb = rodar(porta.calcular(company_id=B, pedido=_pedido(), origem="auxiliar"))
    with pytest.raises(NaoEncontrado):
        rodar(porta.cancelar(company_id=B, pedido_id=pa.pedido_id))
    assert rodar(porta.cancelar(company_id=A, pedido_id=pa.pedido_id)) == 2
    st = {(c["pedido_id"], c["status"]) for c in db.linhas("multicalculo_calculos")}
    assert st == {(pa.pedido_id, "cancelado"), (pb.pedido_id, "na_fila")}


def test_posicao_na_fila_conta_quem_esta_a_frente():
    db = _mundo()
    porta = _porta(db)
    rodar(porta.calcular(company_id=A, pedido=_pedido(), opcoes=["padrao"], origem="auxiliar"))   # prioridade 5
    aberto = rodar(porta.calcular(company_id=CANAL, pedido=_pedido(), corretoras=[B], opcoes=["padrao"],
                                  origem="canal"))                                                  # prioridade 0
    estado = rodar(porta.consultar(company_id=CANAL, pedido_id=aberto.pedido_id)).estados[0]
    assert estado["posicao_na_fila"] == 1                    # o canal passa na frente do auxiliar


# =====================================================================================================================
# G13 — a RENOVAÇÃO a partir da ficha da InfoCap
# =====================================================================================================================
def _apolice_da_fixture():
    from app.providers.infocap_policy_provider import apolice_do_pack

    doc = json.loads(FIXTURE_INFOCAP.read_text(encoding="utf-8"))["documento"][0]
    pack = {"policy_locator_ref": "infocap:1:" + doc["nosnum"], "policy_number": doc["numapo"],
            "insurer_detected": "Seguradora Sintetica", "product_detected": "AUTO",
            "valid_from": "2025-11-01", "valid_to": "2026-11-01",
            "risk_objects": [{"item_number": 1, "plate": "XYZ9A87"}]}
    return doc, apolice_do_pack(pack, hoje=date(2026, 10, 5))


def test_g13_de_apolice_vira_pedido_de_renovacao_com_o_bonus_e_os_assumidos():
    doc, apolice = _apolice_da_fixture()
    perfil = {"segurado": {"cpf_cnpj": "529.982.247-25", "nome": doc["cliente"], "nascimento": "1980-02-01",
                           "sexo": "F", "estado_civil": "solteiro", "cep": "88000-000"},
              "veiculo": {"fipe": "009999-1", "ano_fabricacao": 2019, "ano_modelo": 2020, "combustivel": "flex",
                          "chassi": "9bw zzz377vt004251"},
              "renovacao": {"bonus_anterior": 4},
              "condutor": {}}
    pedido = de_apolice(apolice, perfil)
    d = pedido.para_dict()
    assert d["renovacao"]["renovacao"] is True
    assert d["renovacao"]["bonus_anterior"] == 4                                   # 🔴 G13: o bônus NUNCA some
    assert d["renovacao"]["numero_apolice_anterior"] == doc["numapo"]
    assert d["renovacao"]["vigencia_inicio"] == "2026-11-01" and d["renovacao"]["vigencia_fim"] == "2027-11-01"
    assert d["veiculo"]["placa"] == "XYZ9A87" and d["veiculo"]["chassi"] == "9BWZZZ377VT004251"
    assert {"condutor.cpf", "condutor.nome", "pernoite.cep_pernoite"} <= set(d["assumidos"])
    assert d["pernoite"]["cep_pernoite"] == "88000000"
    assert pedido.faltando() == ["condutor.tempo_habilitacao"]     # não deduzível → não inventado

    # no dublê, o corretor responde o que falta e o pedido VIRA cálculo
    perfil["condutor"] = {"tempo_habilitacao": 15}
    pedido = de_apolice(apolice, perfil)
    assert pedido.faltando() == []
    assert pedido.valor("condutor", "estado_civil") == "solteiro" and "condutor.estado_civil" in pedido.assumidos
    db = _mundo()
    aberto = rodar(_porta(db).calcular(company_id=A, pedido=pedido, origem="auxiliar"))
    assert len(aberto.calculos) == 2 and db.linhas("multicalculo_pedidos")[0]["origem"] == "auxiliar"
    claro = json.loads(Fernet(CHAVE_COFRE).decrypt(db.linhas("multicalculo_pedidos")[0]["pedido_cifrado"].encode()))
    assert claro["renovacao"]["bonus_anterior"] == 4


def test_g13_o_repr_do_pedido_nao_mostra_dado_pessoal():
    p = _pedido()
    assert CPF not in repr(p) and "Sintetica" not in repr(p) and "ABC1D23" not in str(p)


# =====================================================================================================================
# G9 (smith-api) — o cofre de 2 chaves
# =====================================================================================================================
def test_g9_cofre_do_smith_api_decifra_com_a_anterior_e_cifra_com_a_atual(monkeypatch):
    from app.services import portal_vault

    atual, anterior = Fernet.generate_key().decode(), Fernet.generate_key().decode()
    velho = Fernet(anterior.encode()).encrypt(b"segredo-sintetico").decode()
    monkeypatch.setenv("PORTAL_VAULT_KEY", atual)
    monkeypatch.delenv("PORTAL_VAULT_KEY_ANTERIOR", raising=False)
    with pytest.raises(Exception):                       # CONTROLE: sem a anterior, o velho não decifra
        portal_vault.decrypt(velho)
    monkeypatch.setenv("PORTAL_VAULT_KEY_ANTERIOR", anterior)
    assert portal_vault.decrypt(velho) == "segredo-sintetico"
    novo = portal_vault.encrypt("outro-segredo")
    assert Fernet(atual.encode()).decrypt(novo.encode()) == b"outro-segredo"       # a cifra nova sai na ATUAL
    with pytest.raises(Exception):
        Fernet(anterior.encode()).decrypt(novo.encode())


# =====================================================================================================================
# D-129B-11 — a tela de credenciais não troca o login do robô
# =====================================================================================================================
def _salvar(monkeypatch, portal_key):
    import app.api.portal as API

    monkeypatch.setenv("BACKEND_INTERNAL_API_KEY", "chave-interna-sintetica")
    monkeypatch.setenv("PORTAL_VAULT_KEY", Fernet.generate_key().decode())
    db = Banco()
    monkeypatch.setattr(API, "get_supabase_client", lambda: types.SimpleNamespace(client=db))

    class _Req:
        async def json(self):
            return {"company_id": A, "portal_key": portal_key, "username": "usuario-sintetico",
                    "password": "senha-sintetica"}

    return API, db, _Req()


def test_d129b11_post_credentials_recusa_agger_e_nao_grava(monkeypatch):
    from fastapi import HTTPException

    for chave in ("agger", " Agger "):
        API, db, req = _salvar(monkeypatch, chave)
        with pytest.raises(HTTPException) as e:
            rodar(API.save_credential(req, x_key="chave-interna-sintetica"))
        assert e.value.status_code == 403 and db.log == []
    # CONTROLE: um portal de seguradora continua gravando
    API, db, req = _salvar(monkeypatch, "allianz_corretor")
    assert rodar(API.save_credential(req, x_key="chave-interna-sintetica")) == {"ok": True}
    assert ("portal_accounts", "insert") in db.log


# =====================================================================================================================
# P10 — o nome do canal não vira "marca" genérica no porteiro das cartas globais
# =====================================================================================================================
def test_p10_o_nome_do_canal_so_mascara_o_nome_inteiro():
    from app.services.curadoria_cartas import _PerfilDeCorretora

    canal = _PerfilDeCorretora("AutoBrokers Canal de Cotação")
    textos = ("a cotação do canal saiu", "faça a cotação pelo canal oficial", "Cotação de auto")
    for t in textos:
        assert not any(rx.search(t.lower()) for rx in canal.frases), t
    assert any(rx.search("autobrokers canal de cotacao") for rx in canal.frases)
    # CONTROLE: as 2 técnicas de hoje se comportam igual (o nome inteiro, nunca a palavra comum)
    for nome, comum in (("AutoBrokers Global Knowledge", "um conhecimento global"),
                        ("AutoBrokers Blueprint Studio", "o studio abriu")):
        p = _PerfilDeCorretora(nome)
        assert any(rx.search(nome.lower()) for rx in p.frases)
        assert not any(rx.search(comum) for rx in p.frases)
