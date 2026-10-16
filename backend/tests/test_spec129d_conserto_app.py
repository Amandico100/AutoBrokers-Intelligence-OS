# -*- coding: utf-8 -*-
"""SPEC-129-D · conserto K2 (app + tela da renovação) — o que a madrugada pergunta CHEGA à tela, e a resposta VOLTA.

O FIO DESTE CONSERTO (CLAUDE.md §9.4 — o teste vai até o que chega à tela):
    InfoCap /renovacoes (VIND) → madrugada.preparar_dia (REAL) → o evento `pendente(falta_dado)` com as perguntas →
    GET /api/renovacoes/{id} (a API REAL, TestClient) → as perguntas EM PORTUGUÊS no JSON + o formulário →
    POST /api/renovacoes/{id}/respostas-de-vida → o evento `respostas_de_vida` e `pronta` →
    madrugada._avaliar / preparar_dia (REAL) → o pedido 91 leva fumante/renda/esporte.

  B1 (juiz)        as perguntas e os avisos saem no JSON do detalhe; a frase diz "faltam respostas do cliente"
  B3 (red team)    o caminho da resposta: duas corretoras (B nunca responde item de A: 404), corpo estranho 400, falta
                   resposta 422; sem resposta nada é presumido (CONTROLE); esporte "sim" fica com a pessoa
  B2 (red team)    a frase da comissão aponta o Agger; o PUT de Serviços grava `vida_por_ramo` (a régua da config)
  V3 (D-131-38)    a moto com o texto REAL do motor (com o prefixo) vira `pendente(ramo_nao_cotado)`
  MUTAÇÕES         perguntas fora do JSON → VERMELHO · POST sem o filtro de company → VERMELHO
⛔ Tudo SINTÉTICO; nenhum nome de corretora (§13.9); fumante/renda/esporte nunca em log (LGPD art. 11).
Rodar: cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_spec129d_conserto_app.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import timedelta
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import test_spec131a_o_fio as FIO  # noqa: E402
from test_spec131a_o_fio import mundo_real  # noqa: E402,F401  (fixture)
import test_spec129d_app_vida as VIDA  # noqa: E402
import app.api.renovacoes as API  # noqa: E402
from app.services.multicalculo import madrugada as M  # noqa: E402
from app.services.multicalculo import renovacao as R  # noqa: E402

CHAVE_INTERNA = "chave-interna-de-teste-129d-k2"
H = {"X-AutoBrokers-Internal-Key": CHAVE_INTERNA}
#: 💭 a renda SINTÉTICA — o que a guarda de LGPD caça em todo log, na linha da renovação e no JSON da tela
RENDA = 8765.43
PERGUNTAS_NA_TELA = ["O cliente fuma?", "Qual a renda mensal do cliente?", "Pratica esporte radical? Qual?"]


@pytest.fixture
def k2(mundo_real, monkeypatch):
    """Duas corretoras com VIND, a madrugada de verdade já rodou o preparar, e a API real sobre o MESMO banco."""
    m = mundo_real
    monkeypatch.setenv(VIDA.CHAVE, "1")
    monkeypatch.setenv("BACKEND_INTERNAL_API_KEY", CHAVE_INTERNA)
    VIDA._instalar_vida_no_fio(monkeypatch, perfil=VIDA.perfil_vida)       # o cadastro, SEM fumante/renda/esporte
    fim = FIO.DIA + timedelta(days=10)
    # A: o AUTO (o controle "não-vida") e a VIND · B: só a VIND (o mesmo ramo na outra corretora)
    m.a = FIO.montar_corretora(m, "token-k2a", renovacoes=[FIO.linha_renov(920001, "AUTO", fim),
                                                            FIO.linha_renov(920004, "VIND", fim)])
    m.b = FIO.montar_corretora(m, "token-k2b", renovacoes=[FIO.linha_renov(930004, "VIND", fim)])
    for c in (m.a, m.b):
        asyncio.run(M.preparar_dia(m.db, c.id, FIO.DIA))
    monkeypatch.setattr(API, "_db", lambda: m.db)
    app = FastAPI()
    app.include_router(API.router)
    m.cliente = TestClient(app)
    m.vind = {c.id: next(x for x in FIO.itens(m, c.id) if x["ramo_sigla"] == "VIND") for c in (m.a, m.b)}
    return m


def _detalhe(m, c, rid):
    r = m.cliente.get(f"/api/renovacoes/{rid}", params={"company_id": c.id, "user_id": c.admin}, headers=H)
    assert r.status_code == 200, r.text
    return r.json()


def _responder(m, c, rid, **corpo):
    return m.cliente.post(f"/api/renovacoes/{rid}/respostas-de-vida",
                          json={"company_id": c.id, "user_id": c.admin, **corpo}, headers=H)


def _linha(m, rid):
    return next(x for x in m.banco.linhas("renovacoes") if x["id"] == rid)


def _eventos(m, rid):
    return [e for e in m.banco.linhas("renovacao_eventos") if e["renovacao_id"] == rid]


def _avaliar(m, c):
    item = _linha(m, m.vind[c.id]["id"])
    return asyncio.run(M._avaliar(m.db, c.id, item, m.fontes[c.id], M.carregar_config(m.db, c.id)))


def guarda_das_perguntas(d) -> list:
    """O que a corretora LÊ no detalhe de uma vida pendente (o juiz B1). Erros = a tela não recebe a pergunta."""
    erros = []
    if d.get("perguntas") != PERGUNTAS_NA_TELA:
        erros.append(f"perguntas = {d.get('perguntas')!r}")
    if d.get("motivo_frase") != R.FRASE_FALTAM_RESPOSTAS_DE_VIDA:
        erros.append(f"motivo_frase = {d.get('motivo_frase')!r}")
    if "dado da apólice" in json.dumps(d, ensure_ascii=False):
        erros.append("a tela ainda diz 'falta um dado da apólice'")
    if (d.get("respostas_de_vida") or {}).get("campos") != ["fumante", "renda_mensal", "esporte_radical"]:
        erros.append(f"respostas_de_vida = {d.get('respostas_de_vida')!r}")
    return erros


def guarda_do_isolamento(m) -> list:
    """B (outra corretora, a sessão dela) tenta responder o item de A: tem de ser 404 e A não muda."""
    rid = m.vind[m.a.id]["id"]
    antes = (_linha(m, rid)["estado"], len(_eventos(m, rid)))
    r = _responder(m, m.b, rid, fumante=False, renda_mensal=RENDA, esporte_radical=False)
    erros = [] if r.status_code == 404 else [f"B respondeu o item de A: {r.status_code}"]
    if (_linha(m, rid)["estado"], len(_eventos(m, rid))) != antes:
        erros.append("o item de A mudou com a sessão de B")
    return erros


# =====================================================================================================================
# B1 — do evento da madrugada ao JSON que a tela recebe
# =====================================================================================================================
def test_b1_as_perguntas_da_madrugada_chegam_ao_json_da_tela(k2):
    m = k2
    rid = m.vind[m.a.id]["id"]
    assert (_linha(m, rid)["estado"], _linha(m, rid)["motivo"]) == ("pendente", "falta_dado")
    d = _detalhe(m, m.a, rid)
    assert guarda_das_perguntas(d) == []
    assert d["proximo_passo"] == f"Precisa de você: {R.FRASE_FALTAM_RESPOSTAS_DE_VIDA}."
    assert d["respostas_de_vida"]["aviso"] == "Estas respostas são do cliente: confirme com ele."
    assert d["respostas_de_vida"]["ja_respondido"] is False
    # a LISTA também diz a verdade (não só o detalhe)
    lista = m.cliente.get("/api/renovacoes", params={"company_id": m.a.id, "user_id": m.a.admin, "escopo": "todas"},
                          headers=H).json()
    item = next(i for i in lista["itens"] if i["id"] == rid)
    assert item["motivo_frase"] == R.FRASE_FALTAM_RESPOSTAS_DE_VIDA
    # CONTROLE: o AUTO pendente/qualquer não-vida não ganha chave nenhuma de vida (byte a byte)
    auto = next(x for x in FIO.itens(m, m.a.id) if x["ramo_sigla"] == "AUTO")
    da = _detalhe(m, m.a, auto["id"])
    assert not {"perguntas", "avisos", "respostas_de_vida"} & set(da)


def test_b1_mutacao_perguntas_fora_do_json_deixa_vermelho(k2, monkeypatch):
    m = k2
    monkeypatch.setattr(API, "contexto_de_vida", lambda linha, eventos: {})
    assert guarda_das_perguntas(_detalhe(m, m.a, m.vind[m.a.id]["id"])) != []


def test_b1_os_avisos_de_vida_em_portugues_e_so_na_vida(monkeypatch):
    monkeypatch.setenv(VIDA.CHAVE, "1")
    linha = {"estado": "pendente", "motivo": "falta_dado", "ramo_sigla": "VIND"}
    evs = [{"para": "pendente", "dados": {"faltando": ["vida.capital_morte"], "avisos": [
        "coberturas_de_vida_nao_mapeadas", "codigo_novo_qualquer"],
        "perguntas": ["renove manualmente — não achei o capital da apólice atual"]}}]
    ctx = API.contexto_de_vida(linha, evs)
    assert ctx["avisos"] == [API.AVISO_NA_TELA["coberturas_de_vida_nao_mapeadas"], API.AVISO_GENERICO_NA_TELA]
    assert "coberturas da apólice não foram reconhecidas" in ctx["avisos"][0]
    # só o capital falta: não é resposta do cliente → nenhum formulário, e a frase NÃO vira "faltam respostas"
    assert ctx["respostas_de_vida"] is None
    assert R.frase_do_motivo("falta_dado", evs[0]["dados"]) == R.FRASE_DO_MOTIVO["falta_dado"]
    assert API.contexto_de_vida({**linha, "ramo_sigla": "AUTO"}, evs) == {}


# =====================================================================================================================
# B3 — o caminho da RESPOSTA
# =====================================================================================================================
def test_b3_sem_resposta_nada_e_presumido_controle(k2):
    estado, motivo, pedido, dados = _avaliar(k2, k2.a)
    assert (estado, motivo, pedido) == ("pendente", "falta_dado", None)
    assert dados["faltando"] == ["vida.fumante", "vida.renda_mensal", "vida.esporte_radical"]
    assert R.ultima_resposta_de_vida(_eventos(k2, k2.vind[k2.a.id]["id"])) == {}


def test_b3_duas_corretoras_b_nunca_responde_item_de_a(k2):
    assert guarda_do_isolamento(k2) == []


def test_b3_mutacao_post_sem_filtro_de_company_deixa_vermelho(k2, monkeypatch):
    original = R.RepositorioDeRenovacoes.por_id

    def por_id_sem_filtro(self, company_id, renovacao_id):
        linha = next((x for x in self.db.table(R.TABELA).select("*").eq("id", renovacao_id).execute().data), None)
        if linha is None:
            return original(self, company_id, renovacao_id)
        return dict(linha)

    monkeypatch.setattr(R.RepositorioDeRenovacoes, "por_id", por_id_sem_filtro)
    assert guarda_do_isolamento(k2) != []


def test_b3_o_corpo_errado_e_recusado_e_nada_muda(k2):
    m = k2
    rid = m.vind[m.a.id]["id"]
    antes = len(_eventos(m, rid))
    for corpo, status in (({"estado": "pronta", "fumante": False}, 400), ({"fumante": "nao"}, 400),
                          ({"renda_mensal": -1}, 400), ({"renda_mensal": True}, 400), ({}, 400),
                          ({"fumante": False, "renda_mensal": RENDA}, 422)):       # falta o esporte
        r = _responder(m, m.a, rid, **corpo)
        assert r.status_code == status, (corpo, r.status_code, r.text)
    assert len(_eventos(m, rid)) == antes and _linha(m, rid)["estado"] == "pendente"
    # item que não espera resposta (o AUTO) → 409
    auto = next(x for x in FIO.itens(m, m.a.id) if x["ramo_sigla"] == "AUTO")
    assert _responder(m, m.a, auto["id"], fumante=False).status_code == 409


def test_b3_a_resposta_volta_a_pronta_e_o_pedido_seguinte_leva_as_tres(k2, caplog):
    m = k2
    rid = m.vind[m.a.id]["id"]
    caplog.set_level(logging.DEBUG)
    r = _responder(m, m.a, rid, fumante=False, renda_mensal=RENDA, esporte_radical=False)
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "pronta"
    linha = _linha(m, rid)
    assert (linha["estado"], linha["motivo"]) == ("pronta", None)
    ultimo = _eventos(m, rid)[-1]
    assert ultimo["dados"]["respostas_de_vida"] == {"fumante": False, "renda_mensal": RENDA, "esporte_radical": False}
    assert ultimo["por"] == m.a.admin and ultimo["company_id"] == m.a.id
    # a madrugada LÊ a resposta: o "não" dito é resposta — o pedido de vida fica pronto com as três
    estado, motivo, pedido, _dados = _avaliar(m, m.a)
    assert (estado, motivo) == ("pronta", None)
    assert pedido.valor("vida", "fumante") is False and pedido.valor("vida", "esporte_radical") is False
    assert pedido.valor("vida", "renda_mensal") == RENDA
    # a noite seguinte reavalia e o item continua pronto (a resposta é durável); B não ganhou a resposta de A
    asyncio.run(M.preparar_dia(m.db, m.a.id, FIO.DIA))
    asyncio.run(M.preparar_dia(m.db, m.b.id, FIO.DIA))
    assert _linha(m, rid)["estado"] == "pronta"
    assert (_linha(m, m.vind[m.b.id]["id"])["estado"], _linha(m, m.vind[m.b.id]["id"])["motivo"]) == \
        ("pendente", "falta_dado")
    # a TELA: o formulário some, a linha do tempo diz quem respondeu — sem valor nenhum
    d = _detalhe(m, m.a, rid)
    assert d.get("respostas_de_vida") is None
    assert any("registrou as respostas do cliente" in e["frase"] for e in d["eventos"])
    # ⛔ LGPD art. 11: a renda nunca em log, na linha da renovação nem no JSON da tela
    alvo = ("8765", "8.765")
    assert not any(a in caplog.text for a in alvo)
    assert not any(a in json.dumps(d, ensure_ascii=False) for a in alvo)
    assert not any(a in json.dumps(x, default=str) for x in m.banco.linhas("renovacoes") for a in alvo)


def test_b3_esporte_radical_sim_fica_com_a_pessoa_nunca_um_palpite(k2):
    m = k2
    rid = m.vind[m.a.id]["id"]
    r = _responder(m, m.a, rid, fumante=True, renda_mensal=RENDA, esporte_radical=True)
    assert r.status_code == 200 and r.json()["estado"] == "pendente", r.text
    estado, motivo, pedido, dados = _avaliar(m, m.a)
    assert (estado, motivo, pedido) == ("pendente", "falta_dado", None)        # não gasta um login no Agger
    assert dados == M.pendencia_do_esporte_radical()
    d = _detalhe(m, m.a, rid)
    assert d["perguntas"] == [API.FRASE_DO_ESPORTE_NA_TELA]
    # o corretor pode corrigir (o cliente disse "não" afinal): só o esporte é pedido, o resto da resposta vale
    assert d["respostas_de_vida"]["campos"] == ["esporte_radical"]
    assert _responder(m, m.a, rid, esporte_radical=False).json()["estado"] == "pronta"
    _e, _m, pedido, _d = _avaliar(m, m.a)
    assert pedido.valor("vida", "fumante") is True and pedido.valor("vida", "esporte_radical") is False


def test_b3_a_profissao_respondida_vence_o_cadastro():
    from app.services.multicalculo import perfil_da_renovacao as PR

    p = PR.com_as_respostas_de_vida(VIDA.perfil_vida(), {"profissao_texto": "  ENGENHEIRA  ", "fumante": False})
    assert p["segurado"]["profissao_texto"] == "ENGENHEIRA" and p["vida"] == {"fumante": False}
    # CONTROLE: sem resposta, o perfil fica como veio (nenhum campo de vida inventado)
    assert "vida" not in PR.com_as_respostas_de_vida(VIDA.perfil_vida(), {})


# =====================================================================================================================
# B2 — a comissão de vida: a frase aponta o Agger; o PUT de Serviços grava `vida_por_ramo`
# =====================================================================================================================
def test_b2_a_frase_da_comissao_aponta_o_agger_e_nao_uma_tela_que_nao_existe():
    dados = M._recusas_de_vida()["comissao_de_vida_nao_configurada"][2]
    assert dados["perguntas"] == [R.FRASE_DA_COMISSAO_DE_VIDA] == [M.FRASE_DA_COMISSAO_DE_VIDA]
    frase = R.frase_do_motivo("porta_recusou", dados)
    assert frase == R.FRASE_DA_COMISSAO_DE_VIDA and "Agger" in frase and "(Serviços)" not in frase
    # CONTROLE: o `porta_recusou` que não é da vida mantém a frase de sempre
    assert R.frase_do_motivo("porta_recusou", {}) == R.FRASE_DO_MOTIVO["porta_recusou"]


def test_b2_o_put_de_servicos_grava_a_comissao_de_vida_com_a_regua_da_config(monkeypatch):
    import test_spec1310_f4_servicos as SV
    import app.api.servicos_da_corretora as S
    from app.services.multicalculo import config as CFG

    banco = SV._mundo()
    monkeypatch.setenv("BACKEND_INTERNAL_API_KEY", "chave-de-teste")
    monkeypatch.setattr(S, "_db", lambda: banco)
    app = FastAPI()
    app.include_router(S.router)
    c = TestClient(app)
    cab = {"X-AutoBrokers-Internal-Key": "chave-de-teste"}
    url = "/api/servicos-da-corretora"
    versao = c.get(f"{url}?company_id={SV.A}", headers=cab).json()["versao"]
    for ruim in ({"91": {"comissao_pct": 0}}, {"91": {"comissao_pct": 500}}, {"31": {"comissao_pct": 10}},
                 {"91": {"agenciamento_pct": 150}}, {"91": {"campo_inventado": 1}}, {"91": {"reajuste_capital_pct": None}}):
        r = c.put(url, json={"company_id": SV.A, "versao": versao, "vida_por_ramo": ruim}, headers=cab)
        assert r.status_code == 422, (ruim, r.text)
    assert banco.escritas == []
    r = c.put(url, json={"company_id": SV.A, "versao": versao,
                         "vida_por_ramo": {"91": {"comissao_pct": 20, "agenciamento_pct": 0}}}, headers=cab)
    assert r.status_code == 200, r.text
    (tabela, escrita), = banco.escritas
    assert tabela == "multicalculo_config" and escrita["company_id"] == SV.A
    efetivo = CFG.mesclar(escrita["config"])
    assert CFG.comissao_de_vida(efetivo, 91) == 20.0 and CFG.agenciamento_de_vida(efetivo, 91) == 0.0
    assert escrita["config"]["comissao"] == {"piso": 11.0}                   # o resto da linha FICA
    assert r.json()["comum"]["vida_por_ramo"]["91"]["comissao_pct"] == 20.0
    # B não ganhou nada
    rb = c.get(f"{url}?company_id={SV.B}", headers=cab).json()
    assert rb["comum"]["vida_por_ramo"]["91"]["comissao_pct"] is None


# =====================================================================================================================
# V3 (D-131-38) — a moto com o texto REAL do motor
# =====================================================================================================================
def test_v3_a_moto_com_o_texto_real_do_motor_vira_pendente_ramo_nao_cotado():
    from portal_worker.multicalculo import agger_robo as AR
    from portal_worker.multicalculo import motor as MOTOR

    erro = MOTOR._motivo_recusado(AR._recusa_do_preparo("veiculo_moto"))      # o que o motor GRAVA no `erro`
    assert erro.startswith(MOTOR.PREFIXO_DA_RECUSA + ": veiculo_moto"), erro   # o texto real TEM o prefixo
    assert M.estado_derivado([{"status": "falhou", "erro": erro}], 0, False) == ("pendente", "ramo_nao_cotado")
    # CONTROLE: a recusa de outra coisa com o MESMO prefixo continua `falhou` genérico
    outro = MOTOR._motivo_recusado(AR._recusa_do_preparo("nenhuma_seguradora"))
    assert M.estado_derivado([{"status": "falhou", "erro": outro}], 0, False) == ("falhou", "calculo_falhou")
