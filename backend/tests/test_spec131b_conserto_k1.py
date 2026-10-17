# -*- coding: utf-8 -*-
"""SPEC-131-B · CONSERTO K1 (backend) — os achados do juiz, do red team e do juiz de design, cada um com o guarda que
nasceu VERMELHO com o defeito reproduzido no código de `66feb3e` e ficou VERDE com o conserto.

    J-B1   a busca (CPF/nome) só no cabeçalho `x-busca` — `?q=` não filtra e não vai a log
    RT-B1  o envio não reaproveita a página quando QUEM ATENDE mudou (dono saiu/inativo/apagou/trocou o número)
    RT-B2  `texto` = a mensagem COMPLETA (o "Copiar"); `texto_curto` = a do `wa.me`
    RT-B3  o telefone do cliente só dos números DELE (nunca `contatos[]`); número de outro país nunca vira brasileiro
    RT-P1  dois "Enviar" ao mesmo tempo mandam o MESMO link, e é o gravado
    RT-P2  o link perto do fim é republicado e a referência gravada passa a ser o NOVO
    RT-P3  a regra do WhatsApp de trabalho = o CHECK do banco; recusa é 422 com a frase, nunca 500
    RT-P4  "renova há N anos" exige `tipdoc` explícito
    RT-P5  ausências cruzadas no mesmo período são recusadas
    J-P4   o serviço não deixa o admin conectar/trocar a senha do Agger de OUTRA pessoa (D-131-07)
    J-P6   "Minhas" inclui as renovações de quem eu cubro numa ausência ATIVA
    RT-P7  ligar a Renovação exige `confirmar_ligar` no servidor
    design consertos 1, 2 e 7 — o aumento nunca com ✓; "Franquia: R$ X"; aspas e "7%"; o vencimento numa linha própria

Dublê só na BORDA (o banco em memória e a InfoCap). O motor é o REAL (API, máquina da 131-A, publicação, Hub, página).
⛔ Dados sintéticos: o CPF de teste é o clássico inválido-de-exemplo; os telefones são inventados.
Rodar: cd backend && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_spec131b_conserto_k1.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import inspect
import logging
import re
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, unquote

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.api.renovacoes as API  # noqa: E402
import app.services.multicalculo.renovacao as R  # noqa: E402
import test_spec131b_a_pagina_de_renovacao as G4  # noqa: E402
import test_spec131b_api_renovacoes as G2  # noqa: E402
import test_spec131b_perfil_e_ausencia as PT  # noqa: E402
from app.services import perfil_do_membro as PF  # noqa: E402
from app.services.artifacts import proposta_html as PH  # noqa: E402
from app.services.artifacts.service import ArtifactService  # noqa: E402
from app.services.multicalculo import proposta as P  # noqa: E402
from app.services.sistema_de_gestao import dono as DONO  # noqa: E402
from test_spec130a_o_fio import CHROME, texto_visivel  # noqa: E402
from test_spec131b_api_renovacoes import mundo  # noqa: E402,F401  (fixture do mundo da G2)

CPF = "12345678909"                   # 💭 o CPF de EXEMPLO (sintético); nunca de alguém
CHAVE = "chave-interna-de-teste-131b-k1"
HK = {"X-AutoBrokers-Internal-Key": CHAVE}
#: a regra do CHECK `ck_company_members_whatsapp_e164` (migration 20261014_01), copiada do SQL
CHECK_DO_BANCO = re.compile(r"^\+55[1-9][1-9](9[0-9]{8}|[2-5][0-9]{7})$")


# =====================================================================================================================
# J-B1 — a busca no cabeçalho, nunca na query
# =====================================================================================================================
def _ids(resp):
    assert resp.status_code == 200, resp.text
    return {i["id"] for i in resp.json()["itens"]}


def test_jb1_q_na_query_nao_filtra_nem_vai_a_log_e_o_cabecalho_filtra(mundo, caplog):
    m = mundo
    caplog.set_level(logging.DEBUG)
    r1 = G2._renovacao(m.banco, m.a, nosnum="1", estado="calculada", dono=m.a.dono1, nome="Ana")
    r2 = G2._renovacao(m.banco, m.a, nosnum="2", estado="calculada", dono=m.a.dono1, nome="Bruno")
    for x in m.banco.linhas("renovacoes"):
        if x["id"] == r1["id"]:
            x["documento_hmac"] = R.hmac_do_documento(CPF)      # o banco só tem o HMAC (131-A)
    base = {"company_id": m.a.id, "user_id": m.a.dono1, "escopo": "minhas"}
    # 🔴 o CPF na QUERY: não é lido — a lista volta inteira. (A linha de CONTROLE do log: o cliente HTTP registra a
    # URL com a query, como o log de acesso do uvicorn — o guarda abaixo CONSEGUE ver o CPF quando ele está lá)
    assert _ids(m.cliente.get("/api/renovacoes", params={**base, "q": CPF}, headers=G2.H)) == {r1["id"], r2["id"]}
    assert _ids(m.cliente.get("/api/renovacoes", params={**base, "q": "Ana"}, headers=G2.H)) == {r1["id"], r2["id"]}
    assert [r for r in caplog.records if CPF in (r.getMessage() + repr(r.args))], "o guarda do log não enxerga"
    caplog.clear()
    # o CABEÇALHO filtra: CPF cru, CPF formatado e o nome (percent-encoded, como o `encodeURIComponent` da tela)
    for valor in (CPF, quote("123.456.789-09"), "ana"):
        assert _ids(m.cliente.get("/api/renovacoes", params=base, headers={**G2.H, "x-busca": valor})) == {r1["id"]}
    # ⛔ pelo cabeçalho, o CPF não aparece em NENHUM log (nem na linha da requisição, nem nos da rota)
    assert not [r.name for r in caplog.records if CPF in (r.getMessage() + repr(r.args))
                or "123.456.789" in (r.getMessage() + repr(r.args))]


def test_jb1_a_rota_nao_tem_parametro_de_busca_na_query_e_o_cabecalho_decodifica():
    """A FORMA da rota (CLAUDE.md §9.4, exceção): nenhum parâmetro de QUERY carrega texto livre de pessoa."""
    from fastapi.routing import APIRoute

    rota = next(r for r in API.router.routes if isinstance(r, APIRoute) and r.path == "/api/renovacoes"
                and "GET" in r.methods)
    da_query = {p.name for p in rota.dependant.query_params}
    assert da_query == {"company_id", "user_id", "escopo", "estado", "ramo", "de", "ate", "seguradora"}, da_query
    assert "x-busca" in {p.alias.lower() for p in rota.dependant.header_params}
    # o texto chega percent-encoded, cru (latin-1) ou como bytes UTF-8 lidos em latin-1 — sempre o mesmo texto
    assert API.busca_do_cabecalho(quote("brú")) == "brú"
    assert API.busca_do_cabecalho("brú") == "brú"
    assert API.busca_do_cabecalho("brú".encode("utf-8").decode("latin-1")) == "brú"
    assert API.busca_do_cabecalho("   ") is None and len(API.busca_do_cabecalho("x" * 300)) == 80


# =====================================================================================================================
# RT-B3 — o telefone do PRÓPRIO cliente, só do Brasil
# =====================================================================================================================
def test_rtb3_o_telefone_nunca_vem_de_contatos_nem_de_outro_pais():
    f = API.numero_de_whatsapp
    # 🔴 o celular do CONTATO (o contador, um parente) nunca vence o telefone do próprio cliente
    assert f({"telefone": "(11) 3333-4444",
              "contatos": [{"nome": "Contador X", "celular": "11 98888-7777"}]}) == "551133334444"
    assert f({"contatos": [{"celular": "11 98888-7777"}, "11 97777-6666"]}) is None
    # 🔴 número de outro país nunca vira um brasileiro de DDD trocado
    for estrangeiro in ("+1 415 555 2671", "001 415 555 2671", "+351 912 345 678", "+44 20 7946 0958"):
        assert f({"telefone": estrangeiro}) is None, estrangeiro
    # CONTROLE: o número dele, nas formas do cadastro, segue valendo (o celular primeiro)
    assert f({"telefone": "(11) 3333-4444", "telefones": [{"ddd": "21", "numero": "98888-7777"}]}) == "5521988887777"
    assert f({"telefone": "+55 (31) 99999-0000"}) == "5531999990000"
    assert f({"telefone": "0055 31 99999-0000"}) == "5531999990000"
    assert f({"telefone": "011 3333-4444"}) == "551133334444"


# =====================================================================================================================
# RT-B2 — `texto` completo, `texto_curto` no link
# =====================================================================================================================
def test_rtb2_texto_e_a_completa_e_texto_curto_a_do_link():
    curta = {"texto": "Oi! " + "a" * 40, "texto_curto": "curta", "link": "https://x.invalid/r/t"}
    r = API.textos_do_envio(curta)
    assert r == {"texto": curta["texto"], "texto_curto": curta["texto"], "link": curta["link"]}   # cabe: a mesma
    longa = {"texto": "b" * (API.LIMITE_DO_TEXTO_NO_LINK + 120), "texto_curto": "curta", "link": "l"}
    r = API.textos_do_envio(longa)
    assert r["texto"] == longa["texto"] and r["texto_curto"] == "curta" and "texto_completo" not in r


# =====================================================================================================================
# O mundo da G4 servido pela API (o fio): a publicação REAL, o Hub REAL, a página REAL
# =====================================================================================================================
class Infocap:
    def __init__(self):
        self._envelope = G4.historico()(None, None, None)

    def historico_cru(self, codfil, nosnum):
        return list(self._envelope["documento"]) + list(self._envelope["historico"])

    def documento_cru(self, codfil, nosnum):
        return {"codcli": 4242, "nosnum": nosnum}

    def cliente_cru(self, codfil, codigo):
        return {"codigo": codigo, "telefones": [{"ddd": "11", "numero": "912340000"}]}


def _fio(monkeypatch, **kw):
    m = G4.mundo(monkeypatch, **kw)
    monkeypatch.setenv("BACKEND_INTERNAL_API_KEY", CHAVE)
    monkeypatch.setattr(API, "_db", lambda: m.db)
    fonte = Infocap()

    async def abrir_fonte(_db, company_id):
        assert str(company_id).lower() == str(m.beta).lower(), "a InfoCap de OUTRA corretora foi aberta"
        return fonte

    monkeypatch.setattr(DONO, "abrir_fonte", abrir_fonte)
    app = FastAPI()
    app.include_router(API.router)
    m.cliente = TestClient(app)
    m.sessao = {"company_id": m.beta, "user_id": G4.DONO}
    return m


def _linha(m):
    return next(x for x in m.banco.linhas("renovacoes") if x["id"] == G4.RENOVACAO)


def _membro_dono(m):
    return next(x for x in m.banco.tabelas["company_members"] if x["user_id"] == G4.DONO)


def _apresentar(m):
    r = m.cliente.post(f"/api/renovacoes/{G4.RENOVACAO}/apresentacao", json=m.sessao, headers=HK)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _enviar(m):
    r = m.cliente.post(f"/api/renovacoes/{G4.RENOVACAO}/envio", json=m.sessao, headers=HK)
    assert r.status_code == 200, r.text
    corpo = r.json()
    token = re.search(r"/r/([A-Za-z0-9_-]+)", corpo["link"]).group(1)
    return corpo, token


def _dock(m, token):
    s = ArtifactService(m.banco.visao("rota-publica")).abrir_compartilhado(token, user_agent=CHROME)
    assert s, "o link não abriu"
    return G4._dock(s["html"]), s["html"]


# =====================================================================================================================
# RT-B1 — o envio não leva o cliente a quem não atende mais
# =====================================================================================================================
NOVO_NUMERO = "5548977770003"


def _saiu(m):
    m.banco.tabelas["company_members"].remove(_membro_dono(m))       # o DELETE da tela de Equipe


def _inativo(m):
    _membro_dono(m)["status"] = "inactive"


def _apagou(m):
    _membro_dono(m).update(whatsapp_trabalho_e164=None, whatsapp_trabalho_confirmado_em=None)


def _trocou(m):
    _membro_dono(m)["whatsapp_trabalho_e164"] = "+" + NOVO_NUMERO


@pytest.mark.parametrize("mudanca,destino_esperado", [
    (_saiu, G4.WHATS_CORRETORA), (_inativo, G4.WHATS_CORRETORA), (_apagou, G4.WHATS_CORRETORA),
    (_trocou, NOVO_NUMERO)], ids=["saiu", "inativo", "apagou", "trocou"])
def test_rtb1_quem_atende_mudou_o_envio_republica(monkeypatch, mudanca, destino_esperado):
    m = _fio(monkeypatch)
    token = _apresentar(m)
    assert f"wa.me/{G4.WHATS_DONO}?text=" in _dock(m, token)[0]          # a página com o dono confirmado
    m.sessao = {"company_id": m.beta, "user_id": G4.PESSOA}               # OUTRA pessoa da equipe clica "Enviar"
    mudanca(m)
    corpo, enviado = _enviar(m)
    # 🔴 o link enviado é uma página NOVA, com quem atende AGORA — nunca o WhatsApp de quem saiu/apagou/trocou
    assert enviado != token
    dock, doc = _dock(m, enviado)
    assert f"wa.me/{destino_esperado}?text=" in dock and G4.WHATS_DONO not in doc
    assert _linha(m)["proposta_ref"] == enviado and f"/r/{enviado}" in corpo["texto"]


def test_rtb1_controle_nada_mudou_reaproveita_e_quem_passa_a_ter_numero_republica(monkeypatch):
    m = _fio(monkeypatch)
    token = _apresentar(m)
    versoes = len(m.banco.linhas("artifact_versions"))
    assert _enviar(m)[1] == token and len(m.banco.linhas("artifact_versions")) == versoes   # CONTROLE: o mesmo link
    # a página foi publicada SEM o número do dono (não confirmado); ele confirma depois → o envio republica ao dono
    m2 = _fio(monkeypatch, confirmado=False)
    t2 = _apresentar(m2)
    assert f"wa.me/{G4.WHATS_CORRETORA}?text=" in _dock(m2, t2)[0]
    _membro_dono(m2)["whatsapp_trabalho_confirmado_em"] = "2026-10-13T10:00:00+00:00"
    _, e2 = _enviar(m2)
    assert e2 != t2 and f"wa.me/{G4.WHATS_DONO}?text=" in _dock(m2, e2)[0]


def test_jp2_o_dono_inativo_nao_e_nomeado_nem_recebe_o_quero_renovar(monkeypatch):
    m = G4.mundo(monkeypatch)
    _inativo(m)
    assert P.membro_para_o_cliente(m.db, m.beta, G4.DONO) == {}
    r = G4._publicar(m)
    doc = G4._servido(m, r["token"])
    assert G4.WHATS_DONO not in doc and "Bruna" not in texto_visivel(doc)
    assert r["modelo"]["renovacao"]["fechar_com"] == "corretora"


def test_rtb2_no_fio_o_texto_completo_vai_no_copiar_e_o_curto_no_link(monkeypatch):
    m = _fio(monkeypatch)
    corpo, token = _enviar(m)
    no_link = unquote(corpo["wa_me_url"].split("?text=", 1)[1])
    assert no_link == corpo["texto_curto"] and len(no_link) <= API.LIMITE_DO_TEXTO_NO_LINK
    # a COMPLETA: as opções, "Hoje você paga…", a assinatura — mais longa que a do link, ≤ 700
    assert len(corpo["texto_curto"]) < len(corpo["texto"]) <= 700
    assert "Hoje você paga" in corpo["texto"] and "Aqui é Bruna" in corpo["texto"] and f"/r/{token}" in corpo["texto"]


# =====================================================================================================================
# RT-P1 / RT-P2 — o link que sai é SEMPRE o gravado
# =====================================================================================================================
def test_rtp1_dois_enviar_ao_mesmo_tempo_mandam_o_link_gravado(monkeypatch):
    m = _fio(monkeypatch)
    original = API.publicar
    corrida = {}

    async def publicar_com_outro_clique(db, cid, rid, pessoa):
        meu = await original(db, cid, rid, pessoa)
        if not corrida:
            # entre a MINHA publicação e a minha gravação, o outro clique publica e grava o dele (a máquina, CAS)
            outro = await original(db, cid, rid, {"user_id": G4.PESSOA})
            API._apresentar(db, cid, rid, G4.PESSOA, outro["token"])
            corrida["outro"], corrida["meu"] = outro["token"], meu["token"]
        return meu

    monkeypatch.setattr(API, "publicar", publicar_com_outro_clique)
    corpo, enviado = _enviar(m)
    assert corrida["outro"] != corrida["meu"]
    # 🔴 um link só: o que foi ENVIADO é o gravado (a "vista" dele liga à renovação)
    assert enviado == _linha(m)["proposta_ref"] == corrida["outro"]
    assert f"/r/{corrida['outro']}" in unquote(corpo["wa_me_url"])


def test_rtp2_o_link_perto_do_fim_e_republicado_e_a_referencia_acompanha(monkeypatch):
    m = _fio(monkeypatch)
    velho = _apresentar(m)
    share = next(s for s in m.banco.tabelas["artifact_shares"] if s["token"] == velho)
    share["expires_at"] = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()   # vence amanhã
    _, novo = _enviar(m)
    assert novo != velho and _linha(m)["proposta_ref"] == novo                        # 🔴 a referência é o NOVO
    versoes = len(m.banco.linhas("artifact_versions"))
    assert _enviar(m)[1] == novo and len(m.banco.linhas("artifact_versions")) == versoes   # e ele é reaproveitado


# =====================================================================================================================
# RT-P3 — a regra do número É a do banco; recusa é 422 com a frase
# =====================================================================================================================
ENTRADAS = ["(11) 9 1234-5678", "11912345678", "+55 11 91234-5678", "5511912345678", "(11) 3123-4567",
            "+11987654321", "11 6123-4567", "+55 11 1234-5678", "+351 912 345 678", "(11) 8123-4567", "+1 415 555 2671",
            "0055 11 91234-5678", "011 91234-5678", "(01) 91234-5678", "abc", ""]


@pytest.mark.parametrize("entrada", ENTRADAS)
def test_rtp3_o_python_aceita_exatamente_o_que_o_check_do_banco_aceita(entrada):
    try:
        numero = PF.normalizar_whatsapp(entrada)
    except PF.Recusa as e:
        assert str(e)                                                   # sempre com a frase de correção
        return
    assert CHECK_DO_BANCO.match(numero), (entrada, numero)


def test_rtp3_esqueceu_o_55_ouve_a_frase_e_a_rota_responde_422(monkeypatch):
    with pytest.raises(PF.Recusa, match="55"):
        PF.normalizar_whatsapp("+11987654321")
    from app.api import contas_da_corretora as CC

    banco = PT.banco_de_duas_corretoras()
    monkeypatch.setenv("BACKEND_INTERNAL_API_KEY", CHAVE)
    monkeypatch.setattr(CC, "_db", lambda: banco)
    app = FastAPI()
    app.include_router(CC.router)
    cli = TestClient(app, raise_server_exceptions=False)
    corpo = {"company_id": PT.A, "user_id": PT.A1, "por_user_id": PT.A1, "confirmo": True}
    for numero in ("+1 415 555 2671", "+11987654321", "(11) 6123-4567"):
        r = cli.put("/api/contas-da-corretora/perfil/whatsapp-de-trabalho", json={**corpo, "numero": numero}, headers=HK)
        assert r.status_code == 422 and r.json()["detail"], (numero, r.status_code, r.text)
    # se o banco ainda assim recusar (regra divergente no futuro): a frase, nunca o 500
    def recusa_do_banco(*a, **k):
        raise RuntimeError('new row violates check constraint "ck_company_members_whatsapp_e164"')

    monkeypatch.setattr(PF, "gravar_whatsapp_trabalho", recusa_do_banco)
    r = cli.put("/api/contas-da-corretora/perfil/whatsapp-de-trabalho", json={**corpo, "numero": "11912345678"},
                headers=HK)
    assert r.status_code == 422 and "Brasil" in r.json()["detail"]
    assert [l for l in PT._linha(banco, PT.A, PT.A1).values() if l and "+1415" in str(l)] == []


# =====================================================================================================================
# RT-P4 — "N anos" exige o tipo explícito
# =====================================================================================================================
def test_rtp4_elo_sem_tipdoc_nao_prova_anos():
    hoje = date(2026, 10, 13)
    env = {"documento": [{"nosnum": "3", "nosnum_ren": "2"}],
           "historico": [{"nosnum": "2", "inivig": "2019-10-20", "nosnum_ren": ""}]}
    assert P.anos_de_renovacao(env, nosnum="3", hoje=hoje) is None          # 🔴 sem `tipdoc`: sem prova
    env["historico"][0]["tipdoc"] = "A"
    assert P.anos_de_renovacao(env, nosnum="3", hoje=hoje) == 6             # CONTROLE: com o tipo, prova


# =====================================================================================================================
# RT-P5 — ausências cruzadas
# =====================================================================================================================
def test_rtp5_quem_cobre_nao_pode_estar_fora_no_mesmo_periodo():
    banco = PT.banco_de_duas_corretoras()
    PT._criar(banco)                                                    # A1 fora 20–30/10, A2 cobrindo
    with pytest.raises(PF.Recusa, match="também está fora"):
        PT._criar(banco, user_id=PT.A2, substituto_user_id=PT.A1, por_user_id=PT.A2, de="2026-10-25",
                  ate="2026-10-28")                                     # A2 fora 25–28, A1 cobrindo: cruzada
    # CONTROLE: fora do período, A1 cobre A2 normalmente
    PT._criar(banco, user_id=PT.A2, substituto_user_id=PT.A1, por_user_id=PT.A2, de="2026-11-02", ate="2026-11-05")


# =====================================================================================================================
# J-P6 — "Minhas" inclui quem eu cubro hoje
# =====================================================================================================================
def test_jp6_minhas_inclui_as_renovacoes_de_quem_eu_cubro_hoje(mundo):
    m = mundo
    r_meu = G2._renovacao(m.banco, m.a, nosnum="1", estado="calculada", dono=m.a.dono1)
    r_coberto = G2._renovacao(m.banco, m.a, nosnum="2", estado="calculada", dono=m.a.dono2)
    r_admin = G2._renovacao(m.banco, m.a, nosnum="3", estado="calculada", dono=m.a.admin)
    hoje = G2.HOJE
    m.banco.semear("membro_ausencias", {"company_id": m.a.id, "user_id": m.a.dono2, "substituto_user_id": m.a.dono1,
                                        "de": (hoje - timedelta(days=1)).isoformat(),
                                        "ate": (hoje + timedelta(days=3)).isoformat()})
    # a ausência que já acabou e a de OUTRA corretora com o mesmo substituto não contam
    m.banco.semear("membro_ausencias", {"company_id": m.a.id, "user_id": m.a.admin, "substituto_user_id": m.a.dono1,
                                        "de": (hoje - timedelta(days=9)).isoformat(),
                                        "ate": (hoje - timedelta(days=2)).isoformat()})
    m.banco.semear("membro_ausencias", {"company_id": m.b.id, "user_id": m.b.dono2, "substituto_user_id": m.a.dono1,
                                        "de": hoje.isoformat(), "ate": hoje.isoformat()})
    minhas = {i["id"] for i in G2._lista(m, m.a.id, m.a.dono1, escopo="minhas")["itens"]}
    assert minhas == {r_meu["id"], r_coberto["id"]} and r_admin["id"] not in minhas
    # quem está FORA continua vendo as dele (a lista não some)
    assert {i["id"] for i in G2._lista(m, m.a.id, m.a.dono2, escopo="minhas")["itens"]} == {r_coberto["id"]}


# =====================================================================================================================
# J-P4 — o serviço também recusa o admin no login/senha do Agger de outra pessoa (D-131-07)
# =====================================================================================================================
def test_jp4_o_admin_nao_conecta_nem_troca_a_senha_do_agger_de_outra_pessoa(monkeypatch):
    from portal_worker.multicalculo import conta_do_robo as CR

    cid, dono, admin = (str(uuid.uuid4()) for _ in range(3))
    monkeypatch.setattr(CR.robos, "membro_ativo", lambda supa, c, u: True)
    monkeypatch.setattr(CR, "empresa", lambda supa, c: {"id": c, "company_kind": "client"})
    monkeypatch.setattr(CR, "_vinculo", lambda supa, c, u: {"role": "admin_company", "is_owner": False}
                        if u == admin else {"role": "member"})
    for acao in ("conectar", "trocar_senha"):
        with pytest.raises(CR.Recusa, match="Meu perfil"):
            CR._pode_mexer(None, cid, dono, admin, acao=acao)
        with pytest.raises(CR.Recusa, match="Meu perfil"):     # pela porta do serviço, antes de tocar o cofre
            CR.agir_do_membro(None, cid, dono, acao, por_user_id=admin, usuario="u@exemplo.invalid", senha="s",
                              cifrar=lambda t: t)
    with pytest.raises(CR.Recusa, match="Meu perfil"):          # cadastrar direto também é "conectar"
        CR.cadastrar_do_membro(None, cid, dono, "u@exemplo.invalid", "s", admin, cifrar=lambda t: t)
    # CONTROLE: o admin ainda pausa/religa (o gesto de segurança) e a própria pessoa conecta o dela
    CR._pode_mexer(None, cid, dono, admin, acao="pausar")
    CR._pode_mexer(None, cid, dono, dono, acao="conectar")


# =====================================================================================================================
# RT-P7 — ligar a Renovação exige a confirmação NO SERVIDOR
# =====================================================================================================================
def test_rtp7_a_rota_de_instalar_exige_confirmar_ligar_para_quem_instalar_ja_liga():
    """A FORMA da rota Next (CLAUDE.md §9.4, exceção: não há runtime de rota Next nesta bateria) — a trava fica no
    servidor, cobre `install` E `resume`, e roda ANTES de instalar."""
    rota = (BACKEND.parent / "app/api/dashboard/auxiliaries/[auxiliar]/route.ts").read_text(encoding="utf-8")
    assert "import { INSTALAR_JA_LIGA } from '@/lib/auxiliaries/catalog'" in rota
    trava = rota.index("confirmar_ligar !== true")
    assert rota.index("if (action === 'install' || action === 'resume')") < trava < rota.index("installTenantAuxiliary(")
    assert _a_trava_da_rota(rota)
    # CONTROLE HONESTO (K3, N2 da confirmação): o MESMO verificador, sobre rotas com o defeito, dá False — sem a trava,
    # com a trava só no `install` (o `resume` religaria sem confirmar) e com a trava DEPOIS de instalar
    sem_trava = rota.replace("confirmar_ligar !== true", "false", 1)
    so_install = rota.replace("if (action === 'install' || action === 'resume')", "if (action === 'install')", 1)
    depois = "await installTenantAuxiliary(/* instala ANTES de conferir */);\n" + rota
    assert not _a_trava_da_rota(sem_trava)
    assert not _a_trava_da_rota(so_install)
    assert not _a_trava_da_rota(depois)


def _a_trava_da_rota(rota: str) -> bool:
    """A trava de "Ligar" na rota Next: existe, cobre `install` E `resume`, vem ANTES de instalar e responde 400 com
    a frase. Uma função só — o guarda e o controle passam pelo MESMO verificador (CLAUDE.md §9.3, corolário)."""
    try:
        trava = rota.index("confirmar_ligar !== true")
        cobre = rota.index("if (action === 'install' || action === 'resume')")
        instala = rota.index("installTenantAuxiliary(")
    except ValueError:
        return False
    return cobre < trava < instala and "status: 400" in rota[trava:trava + 400] and "detalhe:" in rota[trava:trava + 400]


# =====================================================================================================================
# N1 (K3) — o número da corretora com ORDEM FIXA: duas integrações de atendimento ativas nunca oscilam entre leituras
# =====================================================================================================================
def test_n1_o_numero_da_corretora_le_a_integracao_mais_antiga_sempre(monkeypatch):
    m = G4.mundo(monkeypatch)
    for b in m.banco.linhas("brand_profiles"):          # sem o número da marca: vale a integração de atendimento
        if b["company_id"] == m.beta:
            b["contact"] = {}
    antiga = "5548988887777"                           # 💭 número inventado
    # semeada POR ÚLTIMO (o fim da tabela), mas criada ANTES — a leitura sem ORDER BY pegaria a outra
    m.banco.semear("integrations", {"company_id": m.beta, "provider": "evolution-go", "purpose": "attendance",
                                    "is_active": True, "channel_status": "connected", "paired_phone_e164": "+" + antiga,
                                    "created_at": "2020-01-01T00:00:00+00:00"})
    lidos = {P.whatsapp_da_corretora(m.db, m.beta) for _ in range(3)}
    assert lidos == {antiga}, lidos
    # CONTROLE: a leitura SEM ordem (a de antes) devolve outro número primeiro — o guarda consegue ficar vermelho
    sem_ordem = (m.db.table("integrations").select("company_id, paired_phone_e164, purpose, is_active").eq("company_id", m.beta)
                 .eq("purpose", "attendance").eq("is_active", True).limit(64).execute().data)
    assert P._digitos_de_whatsapp(sem_ordem[0]["paired_phone_e164"]) != antiga
    # e a vizinha (alfa) nunca entra na leitura da beta
    assert all(str(i.get("company_id")) == m.beta for i in sem_ordem)


# =====================================================================================================================
# O DESIGN da página do cliente (consertos 1, 2 e 7) — no HTML SERVIDO
# =====================================================================================================================
def test_design_o_aumento_nunca_e_vantagem_a_franquia_e_uma_palavra_e_o_vencimento_tem_linha_propria(monkeypatch):
    m = G4.mundo(monkeypatch)
    r = G4._publicar(m)
    doc = G4._servido(m, r["token"])
    txt = texto_visivel(doc)
    # o aumento existe (a renovação é MAIS cara que hoje) — e está no "o que mudou", neutro
    assert re.search(r"O que mudou: R\$ [\d.]+ a mais por ano \(\+\d+%\)", txt), txt[:400]
    # 🔴 conserto 1: nenhum ✓ com aumento ("a mais que a sua apólice atual")
    for lista in re.findall(r'<ul class="why">(.*?)</ul>', doc, re.S):
        assert "a mais que a sua apólice atual" not in texto_visivel(lista)
    assert "a mais que a sua apólice atual" not in txt
    # 🔴 conserto 2: "Franquia reduzida" é só o NOME de uma opção; a linha da franquia é "Franquia"
    assert "Franquia reduzida de" not in txt and not re.search(r"Franquia reduzida R\$", txt)
    assert not re.search(r'<span class="lbl">Franquia [^<]', doc)
    assert not re.search(r"Franquia de R\$ [\d.,]+ \(R\$ [\d.,]+ (menor|maior)\)", txt)
    # §9.3 (SPEC-130-C, conserto KA — laudo de design 130-C, pendência 2): o cartão que mostra a linha "Franquia R$ 5.171"
    # não repete o motivo "Franquia: R$ 5.170,54" (o mesmo número com duas caras) — a lição (uma palavra só, "Franquia",
    # nunca "Franquia reduzida R$") migra para a linha do cartão
    assert re.search(r"Franquia R\$ [\d.,]+", txt) and not re.search(r"Franquia: R\$ [\d.,]+", txt)
    sep = re.search(r"\d %", txt)                                       # "7%" e "100%", nunca "7 %"
    assert not sep, txt[max(0, sep.start() - 80):sep.end() + 30]
    assert '"Sua renovação"' not in txt and "“Sua renovação”" in txt     # aspas tipográficas
    # 🔴 conserto 7: o vencimento numa linha própria; o nome com peso forte; um eixo só no notebook
    assert re.search(r'<span class="vence">vence em \d\d/\d\d/\d{4}</span>', doc) and "· vence em" not in doc
    # §9.3 (SPEC-130-C, D-130C-01): a renovação mora no esqueleto da VENDA — o vencimento continua numa linha própria
    # (`.renova .vhero h1 .vence`), o título inteiro (com o nome) na tinta forte e UM eixo só no notebook (a coluna de
    # 1080 px da venda); antes as três lições moravam no CSS da carteira (`PH.CSS_DA_RENOVACAO`, que saiu)
    from app.services.artifacts import proposta_cotacao_html as PV
    assert ".renova .vhero h1 .vence{display:block" in PV.CSS_DA_RENOVACAO
    assert re.search(r"\.vhero h1\{[^}]*color:var\(--ink-strong\)", PV.CSS_DA_VENDA)
    assert "@media (min-width:1024px){" in PV.CSS_DA_VENDA and ".venda .wrap{max-width:1080px}" in PV.CSS_DA_VENDA
    assert '<body class="venda renova">' in doc


def test_design_a_cotacao_segue_com_os_textos_de_antes():
    """CONTROLE (cotação byte a byte): fora da renovação os textos da comparação são os da 130-A."""
    from app.services.multicalculo import comparacao as C

    e = {"premio_anual": 1100.0, "franquia": {"valor": 3000.0, "tipo": "Reduzida"}, "oferta_id": "x",
         "coberturas_brutas": {}, "parcelas": None}
    ref = {"premio_anual": 1000.0, "franquia": {"valor": 4000.0}, "oferta_id": "y", "seguradora": "S2",
           "coberturas_brutas": {}}
    e["seguradora"] = "S1"
    cot = C._motivos(e, "economica", ranking_completa=[], referencia=ref, rotulo_ref="Recomendada", pool=[e],
                     apolice_atual={"premio_anual": 1000.0}, ramo=C.RAMO_AUTO)
    assert 'que a opção "Recomendada"' in cot[0] and "a mais que a sua apólice atual (10 %)" in cot[1]
    assert "Franquia reduzida de R$" in cot[2]
    muda = C._o_que_muda(e, ref, "Recomendada")
    assert any(re.search(r"Franquia de R\$ [\d.,]+ \(R\$ [\d.,]+ menor\)", x) for x in muda)
    ren = C._motivos(e, "renovacao", ranking_completa=[], referencia=ref, rotulo_ref="Sua renovação", pool=[e],
                     apolice_atual={"premio_anual": 1000.0}, ramo=C.RAMO_AUTO, renovacao=True)
    assert not any("a mais que a sua apólice atual" in x for x in ren) and "Franquia: R$" in " ".join(ren)
    assert inspect.signature(C._motivos).parameters["renovacao"].default is False


# =====================================================================================================================
# K3 (juiz de design 4) — UMA parcela por opção na página de renovação, no HTML SERVIDO
# =====================================================================================================================
def _parcelas_divergentes(doc: str) -> list:
    """Em cada cartão (`<article class="pass">`), toda "Nx de R$ V" com o MESMO N tem o MESMO V. Devolve as divergências."""
    ruins = []
    for i, art in enumerate(re.findall(r'<article class="pass[^"]*".*?</article>', doc, re.S)):
        por_n: dict = {}
        for n, v in re.findall(r"(\d+)x de R\$\s*([\d.,]+)", texto_visivel(art)):
            por_n.setdefault(n, set()).add(v)
        ruins += [(i, n, sorted(vs)) for n, vs in por_n.items() if len(vs) > 1]
    return ruins


def test_k3_a_mesma_opcao_mostra_uma_parcela_so(monkeypatch):
    m = G4.mundo(monkeypatch)
    r = G4._publicar(m)
    doc = G4._servido(m, r["token"])
    cartoes = re.findall(r'<article class="pass[^"]*".*?</article>', doc, re.S)
    assert len(cartoes) >= 2, "a página de renovação tem os cartões das opções"
    assert any(re.search(r"\d+x de R\$", texto_visivel(c)) for c in cartoes), "a parcela continua sob o preço"
    assert _parcelas_divergentes(doc) == [], _parcelas_divergentes(doc)
    # e a parcela NÃO se repete no "por que" (a fonte é uma só: a que está sob o preço)
    for lista in re.findall(r'<ul class="why">(.*?)</ul>', doc, re.S):
        assert not re.search(r"Em até \d+x de R\$", texto_visivel(lista)), texto_visivel(lista)
    # CONTROLE: o defeito histórico (o "por que" com as "demais parcelas") fica VERMELHO no mesmo verificador
    historico_ = ('<article class="pass"><p>ou 10x de R$ 555,83 com juros</p>'
                  '<ul class="why"><li>Em até 10x de R$ 554,94</li></ul></article>')
    assert _parcelas_divergentes(historico_) == [(0, "10", ["554,94", "555,83"])]
