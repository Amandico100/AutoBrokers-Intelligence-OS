# -*- coding: utf-8 -*-
"""SPEC-130-A F4 — a 3ª opção "Mais completa" (completa+, D-MC-69 / D-130A-09) do preset ao corpo do Agger.

A completa+ = a padrão (D-MC-65: franquia reduzida, vidros completos, reserva 15 d, assistência completa) + PEQUENOS
REPAROS (`reparoRapido: true` no corpo do `calcularV2`). Ela é calculada no MESMO negócio, DEPOIS da econômica, com o
mesmo checkpoint/retomada, os mesmos freios e a mesma regra das 24 h que já existem (129-B).

O que se afirma é o comportamento dos MOTORES reais (CLAUDE.md §9.4): `presets.coberturas_de`, a PORTA
(`MulticalculoProvider.calcular`, com os presets REAIS — sem o `presets=` de teste), o MOTOR (`Motor.uma_volta`) e, no
fio, o robô REAL (`agger_robo` + `montador.js` num Chromium) contra o Agger dublê: o `reparoRapido` lido no corpo que
SAIU. O dublê fica só na borda (o banco PostgREST, o Agger).

⛔ Dado FICTÍCIO; nenhum nome de corretora (§13.9).
    cd backend && .venv/Scripts/python.exe -m pytest tests/test_spec130a_completa_mais.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import test_spec129b_a_porta as TP  # noqa: E402
import test_spec129b_o_motor as TM  # noqa: E402
from test_spec129b_o_motor import ambiente  # noqa: E402,F401  (fixture)
from app.services.multicalculo import MulticalculoProvider  # noqa: E402
from app.services.multicalculo import porta as PORTA  # noqa: E402
from app.services.multicalculo.repositorio import RepositorioMulticalculo  # noqa: E402
from portal_worker.multicalculo import motor as MOT  # noqa: E402
from portal_worker.multicalculo import presets as P  # noqa: E402

MIGRATION = BACKEND / "supabase" / "migrations" / "20261006_02_spec130a_completa_mais.sql"
TRES = ("padrao", "economica", "completa_mais")


# =====================================================================================================================
# O preset — a padrão + pequenos reparos, e NADA mais
# =====================================================================================================================
def test_o_preset_da_completa_mais_e_a_padrao_com_pequenos_reparos():
    cm, pad = P.coberturas_de("completa_mais"), P.coberturas_de("padrao")
    assert set(cm) == set(P.CHAVES_DE_COBERTURA) == set(pad), "o montador aplica exatamente as 15 chaves"
    assert cm["reparoRapido"] is True
    assert pad["reparoRapido"] is False, "CONTROLE: a padrão NÃO manda pequenos reparos (as duas diferem)"
    assert {k: v for k, v in cm.items() if v != pad[k]} == {"reparoRapido": True}, "só os pequenos reparos mudam"
    # a franquia reduzida da completa+ (D-MC-69) JÁ é da padrão: 📊 código 1 = reduzida (AF Prata)
    assert cm["tipoFranquia"] == P.VALORES_DO_AJUSTE["franquia"]["reduzida"]
    # a cópia não contamina o próximo pedido
    cm["reparoRapido"] = False
    assert P.coberturas_de("completa_mais")["reparoRapido"] is True
    # as duas opções de hoje intactas
    assert P.coberturas_de("economica")["reparoRapido"] is False and P.coberturas_de("economica")["vidros"] == 1


def test_porta_presets_e_motor_dizem_as_mesmas_opcoes_na_mesma_ordem():
    assert PORTA.OPCOES == P.ORDEM == TRES
    assert set(P.PRESETS) == set(PORTA.OPCOES), "opção aceita pela porta sem preset (ou preset que ninguém pede)"
    assert PORTA.OPCOES_PADRAO == ("padrao", "economica"), "o default da 129-B não muda: a completa+ é PEDIDA"
    ordem = MOT._ORDEM_DA_OPCAO
    assert ordem["padrao"] < ordem["economica"] < ordem["completa_mais"] < ordem["ajuste"]
    with pytest.raises(ValueError):
        P.coberturas_de("ajuste")


def test_a_migration_alarga_as_duas_checks_e_nada_mais():
    sql = MIGRATION.read_text(encoding="utf-8")
    corpo = "\n".join(l for l in sql.splitlines() if not l.lstrip().startswith("--"))
    # as listas do APPLY são as da porta (+ o ajuste no cálculo)
    pedidos = re.search(r"opcoes <@ array\[([^\]]*)\]::text\[\]", corpo)
    calculos = re.search(r"check \(opcao in \(([^)]*)\)\)", corpo)
    assert pedidos and calculos
    assert tuple(re.findall(r"'([a-z_]+)'", pedidos.group(1))) == PORTA.OPCOES
    assert tuple(re.findall(r"'([a-z_]+)'", calculos.group(1))) == PORTA.OPCOES + ("ajuste",)
    assert "cardinality(opcoes) >= 1" in corpo, "a cardinalidade ≥ 1 do pedido não pode cair"
    # idempotente e numa transação: as duas trocas dentro do MESMO bloco DO, cada uma guardada pelo texto atual
    assert corpo.count("do $$") == 1 and corpo.count("like '%completa_mais%'") == 2
    assert not re.search(r"\b(update|delete|insert|truncate|drop table|drop column)\b", corpo, re.I), \
        "a migration só troca CHECK (expand-only, nenhum dado)"
    # o cabeçalho: APPLY / VERIFY / ROLLBACK escritos; o ROLLBACK recusa com linha da completa+
    for secao in ("-- APPLY:", "-- VERIFY (read-only", "-- VERIFY comportamental", "-- ROLLBACK"):
        assert secao in sql, secao
    rollback = sql[sql.index("-- ROLLBACK"):]
    assert "opcao = 'completa_mais'" in rollback and "'completa_mais' = any(opcoes)" in rollback
    assert "array['padrao', 'economica']::text[]" in rollback and "('padrao', 'economica', 'ajuste')" in rollback
    # 🔴 o defeito de 06/10: `text[] || 'literal'` ambíguo em PL/pgSQL — todo append do VERIFY leva ::text
    appends = [l for l in sql.splitlines() if "res := res ||" in l]
    assert appends and all(l.rstrip().endswith(")::text;") for l in appends), appends


# =====================================================================================================================
# A PORTA — 3 opções viram 3 cálculos na MESMA corretora, com os presets REAIS
# =====================================================================================================================
def _porta_real(db):
    return MulticalculoProvider(RepositorioMulticalculo(db), cifrar=lambda t: "cifrado:" + str(len(t)),
                                ambiente={"MULTICALCULO_HMAC_KEY": TP.CHAVE_HMAC})


def test_a_porta_aceita_a_completa_mais_e_resolve_o_preset_real():
    db = TP._mundo()
    porta = _porta_real(db)
    # a ordem do chamador NÃO importa: grava na ordem do disparo
    aberto = TM.rodar(porta.calcular(company_id=TP.A, pedido=TP._pedido(), opcoes=("completa_mais", "padrao",
                                                                                     "economica"),
                                     origem="auxiliar"))
    ped = db.linhas("multicalculo_pedidos")[0]
    assert list(ped["opcoes"]) == list(TRES)
    calcs = db.linhas("multicalculo_calculos")
    assert [(c["company_id"], c["opcao"]) for c in calcs] == [(TP.A, o) for o in TRES]
    assert {c["pedido_id"] for c in calcs} == {aberto.pedido_id} and len(aberto.calculos) == 3
    por = {c["opcao"]: c["coberturas"] for c in calcs}
    assert por["completa_mais"] == P.coberturas_de("completa_mais") and por["completa_mais"]["reparoRapido"] is True
    assert por["padrao"] == P.coberturas_de("padrao") and por["economica"] == P.coberturas_de("economica")
    assert "completa_mais" in porta.capacidades()["opcoes"]


def test_a_porta_sem_escolha_continua_com_as_duas_e_recusa_o_desconhecido():
    db = TP._mundo()
    porta = _porta_real(db)
    TM.rodar(porta.calcular(company_id=TP.A, pedido=TP._pedido(), origem="auxiliar"))
    assert [c["opcao"] for c in db.linhas("multicalculo_calculos")] == ["padrao", "economica"]
    for ruins in (("completa",), ("padrao", "completa+"), ()):
        with pytest.raises(ValueError, match="opções aceitas"):
            TM.rodar(porta.calcular(company_id=TP.A, pedido=TP._pedido(), opcoes=ruins, origem="auxiliar"))
    assert len(db.linhas("multicalculo_calculos")) == 2, "a recusa não gravou nada"


# =====================================================================================================================
# O MOTOR — a completa+ no MESMO negócio, depois da econômica; retomada, freios e 24 h
# =====================================================================================================================
def test_o_motor_dispara_as_tres_no_mesmo_negocio_e_o_ajuste_por_ultimo(ambiente):
    amb = ambiente
    a = TM.empresa(amb)
    TM.robo(amb, a)
    pid, ids = TM.pedido(amb, a, [a], opcoes=TRES)
    # um ajuste do corretor sobre a PADRÃO, na fila JUNTO: ele sai depois de todas as opções
    aj = str(uuid4())
    amb.banco.semear("multicalculo_calculos", {
        "id": aj, "pedido_id": pid, "solicitante_company_id": a, "company_id": a, "opcao": "ajuste",
        "coberturas": {"preset": "ajuste"}, "origem_calculo_id": ids[0],
        "ajuste": {"tipo": "franquia", "valor": "normal"}, "expira_em": (TM.T0 + timedelta(hours=1)).isoformat()})
    TM.rodar(TM.motor(amb, "motor-1").uma_volta())

    assert [p[3] for p in amb.mundo.posts] == ["padrao", "economica", "completa_mais", "ajuste"]
    assert {p[1] for p in amb.mundo.posts} == {"NEG-1"}, "a completa+ abriu outro negócio"
    por = {TM.calc(amb, c)["opcao"]: TM.calc(amb, c) for c in ids + [aj]}
    assert {o: (c["status"], c["negocio_ref"], c["versao"]) for o, c in por.items()} == {
        "padrao": ("fechado", "NEG-1", 1), "economica": ("fechado", "NEG-1", 2),
        "completa_mais": ("fechado", "NEG-1", 3), "ajuste": ("fechado", "NEG-1", 4)}
    assert amb.mundo.recalculos and amb.mundo.recalculos[0][:2] == ("NEG-1", 1), "o ajuste parte da versão da PADRÃO"
    cm = por["completa_mais"]
    evs = TM.linhas(amb, "multicalculo_eventos", calculo_id=cm["id"])
    assert len(evs) == len({e["chave"] for e in evs}) == 30 and TM.linhas(amb, "multicalculo_ofertas",
                                                                          calculo_id=cm["id"])
    assert TM.linhas(amb, "multicalculo_pedidos", id=pid)[0]["status"] == "fechado"


def test_a_retomada_da_completa_mais_nao_recalcula(ambiente):
    amb = ambiente
    a = TM.empresa(amb)
    TM.robo(amb, a)
    _pid, ids = TM.pedido(amb, a, [a], opcoes=TRES)
    amb.mundo.matar_em = (("NEG-1", 3), 1)   # morre depois de gravar a 2ª rodada da COMPLETA+ (versão 3)
    m1 = TM.motor(amb, "motor-1")

    async def cenario():
        await m1.uma_volta()
        await asyncio.sleep(0.05)

    TM.rodar(cenario())
    assert m1.supa.morto and len(amb.mundo.posts) == 3
    cm = next(c for c in ids if TM.calc(amb, c)["opcao"] == "completa_mais")
    assert TM.calc(amb, cm)["status"] == "calculando" and TM.calc(amb, cm)["versao"] == 3, \
        "o checkpoint gravou o negócio da completa+ ANTES do GET"

    amb.relogio.avancar(MOT.LEASE_VENCE_S + 1)
    TM.rodar(TM.motor(amb, "motor-2").uma_volta())
    assert len(amb.mundo.posts) == 3, "a retomada fez POST de novo"
    for cid in ids:
        c = TM.calc(amb, cid)
        assert c["status"] == "fechado", (c["opcao"], c["status"], c["erro"])
        evs = TM.linhas(amb, "multicalculo_eventos", calculo_id=cid)
        assert len(evs) == len({e["chave"] for e in evs}) == 30, c["opcao"]
    assert TM.calc(amb, cm)["dono"] == "motor-2"


def test_a_completa_mais_respeita_a_regra_das_24h(ambiente):
    amb = ambiente
    a = TM.empresa(amb)
    TM.robo(amb, a)
    _pid, ids = TM.pedido(amb, a, [a], opcoes=TRES)
    amb.mundo.mexeu = True                     # uma pessoa mexeu no negócio: nada entra nele
    TM.rodar(TM.motor(amb, "motor-1").uma_volta())
    assert [p[3] for p in amb.mundo.posts] == ["padrao"], "entrou no negócio que uma pessoa mexeu"
    st = {TM.calc(amb, c)["opcao"]: TM.calc(amb, c) for c in ids}
    assert st["completa_mais"]["status"] == "falhou" and MOT.MOTIVO_PESSOA_MEXEU in (st["completa_mais"]["erro"] or "")
    assert st["padrao"]["status"] == "fechado"


def test_o_freio_da_corretora_conta_a_completa_mais(ambiente, monkeypatch):
    amb = ambiente
    a = TM.empresa(amb)
    TM.robo(amb, a)
    _pid, ids = TM.pedido(amb, a, [a], opcoes=TRES)
    monkeypatch.setenv("MULTICALCULO_TETO_CORRETORA_HORA", "2")    # 3 cálculos > 2: o grupo inteiro espera
    TM.rodar(TM.motor(amb, "motor-1").uma_volta())
    assert amb.mundo.posts == [] and {TM.calc(amb, c)["status"] for c in ids} == {"na_fila"}
    monkeypatch.setenv("MULTICALCULO_TETO_CORRETORA_HORA", "3")    # CONTROLE: com espaço para os 3, saem
    TM.rodar(TM.motor(amb, "motor-1").uma_volta())
    assert len(amb.mundo.posts) == 3 and {TM.calc(amb, c)["status"] for c in ids} == {"fechado"}


# =====================================================================================================================
# 🔴 O FIO — porta (presets REAIS) → banco → motor → robô REAL + montador.js (Chromium) → o CORPO que saiu no Agger
# =====================================================================================================================
@pytest.fixture
def mundo_fio(monkeypatch):
    pytest.importorskip("playwright.async_api")
    from cryptography.fernet import Fernet

    import dubles_do_work_os as D
    from dubles.agger_duble import EMAIL, SENHA
    from dubles.banco_multicalculo import BancoU1, instalar_esquema
    from portal_worker import leases, vault

    instalar_esquema(monkeypatch, com_porta=True)
    monkeypatch.setenv("PORTAL_VAULT_KEY", Fernet.generate_key().decode())
    monkeypatch.delenv("PORTAL_VAULT_KEY_ANTERIOR", raising=False)
    for nome in ("MULTICALCULO_TETO_CORRETORA_HORA", "MULTICALCULO_TETO_GERAL_HORA", "AUTOBROKERS_CANARIO"):
        monkeypatch.delenv(nome, raising=False)
    monkeypatch.setattr(leases, "redis_disponivel", lambda *a, **k: False)
    relogio = D.Relogio(datetime.now(timezone.utc).replace(microsecond=0))
    banco = BancoU1(relogio)
    a = str(uuid4())
    banco.semear("companies", {"id": a, "company_kind": "client"})
    banco.semear("portal_accounts", {
        "id": str(uuid4()), "company_id": a, "portal_key": "agger", "account_label": "robo-1", "username": EMAIL,
        "secret_encrypted": vault.encrypt(SENHA), "robo_estado": "ativo"})
    porta = MulticalculoProvider(RepositorioMulticalculo(banco.visao("smith-api")),
                                 ambiente={"MULTICALCULO_HMAC_KEY": "chave-hmac-ficticia-f4-0123456789"},
                                 agora=relogio.agora)
    return SimpleNamespace(banco=banco, relogio=relogio, porta=porta, a=a, uploads=[])


def test_o_fio_o_corpo_da_completa_mais_sai_com_pequenos_reparos_no_mesmo_negocio(mundo_fio):
    import test_spec129b_o_fio as TF
    from app.services.multicalculo import PedidoDeCalculo

    m = mundo_fio

    async def tudo(d, novo_navegador):
        nav = await novo_navegador()
        await m.porta.calcular(company_id=m.a, pedido=PedidoDeCalculo.de_dict(TF.dados_do_pedido()),
                               opcoes=TRES, origem="auxiliar")
        mot = TF.motor(m, "motor-1", nav, d)
        await TF.ate_esvaziar(mot, m)
        try:
            calcs = {c["opcao"]: c for c in m.banco.linhas("multicalculo_calculos")}
            assert set(calcs) == set(TRES) and {c["status"] for c in calcs.values()} == {"fechado"}, \
                [(c["opcao"], c["status"], c["erro"]) for c in calcs.values()]
            assert len({c["negocio_ref"] for c in calcs.values()}) == 1
            assert [calcs[o]["versao"] for o in TRES] == [1, 2, 3]
            posts = list(d.posts_calcular)
            assert len(posts) == 3
            itens = [[i for i in p["cotacao"]["calculos"]] for p in posts]
            assert all(itens), "um corpo sem item de seguradora"
            # o CORPO que saiu: a completa+ (3º POST) com pequenos reparos em TODO item; a padrão e a econômica sem
            assert [sorted({i["reparoRapido"] for i in its}) for its in itens] == [[False], [False], [True]]
            # e o resto da completa+ é a padrão, chave por chave, item por item
            for i_pad, i_cm in zip(itens[0], itens[2]):
                diferentes = {k for k in P.CHAVES_DE_COBERTURA if i_pad.get(k) != i_cm.get(k)}
                assert diferentes == {"reparoRapido"}, diferentes
        finally:
            await mot.desligar()

    TM.rodar(TF.com_agger_e_navegador(tudo))
