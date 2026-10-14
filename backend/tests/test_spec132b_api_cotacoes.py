# -*- coding: utf-8 -*-
"""SPEC-132-B · B3 — a API da aba Cotações (`backend/app/api/cotacoes.py`) e as regras da cotação na tela Configurar.

    ① duas corretoras: a lista, o detalhe e as duas ações nunca cruzam (o filtro no código, não a RLS)
       🔴 MUTAÇÃO 6 da SPEC: o módulo REAL com o filtro `company_id` arrancado devolve a cotação da outra → o guarda
       fica VERMELHO (e o real, verde — a linha de controle)
    ② "minhas" = quem pediu sou eu · "todas" = a corretora inteira
    ③ os estados Calculando · Pronta · Sem resposta saem do banco; a melhor parcela; o cliente do Work Run ou, sem ele,
       do pedido decifrado (só o PRIMEIRO nome, documento MASCARADO)
    ④ a busca vem SÓ no cabeçalho `x-busca` (nome ou CPF pelo HMAC); `?q=` é ignorado
    ⑤ o envio: o `wa.me` com o telefone que o corretor informou no PEDIDO; sem telefone → só o texto; `via=copiar`
       não decifra nada. 🔴 O telefone em NENHUM log e em NENHUMA escrita do banco
    ⑥ a apresentação: o link da conversa (Work Run) vale; sem ele, `publicar_cotacao` (B2) pelo contrato
    ⑦ as regras da cotação (D-132B-06): o efetivo, o padrão, as faixas e o que o backend já aceita gravar

Dublê só na BORDA: o banco (PostgREST em memória com as travas do multicálculo — UM dublê, o da 131-A), o cofre
(`_decifrar`) e as duas funções da B2 pelo CONTRATO. ⛔ Dados sintéticos e óbvios (§13.9).
Rodar: cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_spec132b_api_cotacoes.py -q -p no:cacheprovider
"""
from __future__ import annotations

import importlib.util
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import test_spec131a_o_fio as FIO  # noqa: E402  (o esquema e as travas do multicálculo — UM dublê)
import dubles_do_work_os as D  # noqa: E402
import app.api.cotacoes as API  # noqa: E402
import app.api.servicos_da_corretora as SERV  # noqa: E402
from app.services.multicalculo import config as CFG  # noqa: E402
from app.services.multicalculo import mensagem as MSG  # noqa: E402
from app.services.multicalculo import proposta as P  # noqa: E402
from app.services.multicalculo.porta import cpf_hmac  # noqa: E402

CHAVE = "chave-interna-de-teste-132b"
AGORA = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
#: o telefone SINTÉTICO do cliente — o que se caça em todo log e em toda escrita
TELEFONE = "11987654321"
CPF = "52998224725"          # 💭 sintético (dígitos verificadores válidos, de ninguém)
H = {"X-AutoBrokers-Internal-Key": CHAVE}


def _corretora(banco, nome: str) -> SimpleNamespace:
    cid = str(uuid.uuid4())
    banco.semear("companies", {"id": cid, "company_kind": "client", "company_name": f"Corretora {nome}",
                               "is_technical": False})
    pessoas = []
    for i, papel in enumerate(("member", "member", "admin_company")):
        uid = str(uuid.uuid4())
        banco.semear("users_v2", {"id": uid, "first_name": f"Pessoa{i}{nome}", "last_name": "Teste"})
        banco.semear("company_members", {"user_id": uid, "company_id": cid, "role": papel})
        pessoas.append(uid)
    return SimpleNamespace(id=cid, um=pessoas[0], dois=pessoas[1], admin=pessoas[2])


def _cifrado(nome: str, telefone=TELEFONE, cpf=CPF) -> str:
    dados = {"ramo": 31, "segurado": {"nome": nome, "cpf_cnpj": cpf, **({"telefone": telefone} if telefone else {})},
             "veiculo": {"modelo": "Carro Exemplo", "ano_modelo": 2022, "placa": "ABC1D23"}}
    return "dub:" + json.dumps(dados)


def _cotacao(m, c, quem: str, *, estado: str = "pronta", nome: str = "Fulano Ficticio da Silva", telefone=TELEFONE,
             run: dict = None) -> dict:
    pedido = m.banco.semear("multicalculo_pedidos", {
        "company_id": c.id, "origem": "auxiliar", "ramo": 31, "opcoes": ["padrao", "economica"], "corretoras": [c.id],
        "pedido_cifrado": _cifrado(nome, telefone), "cpf_hmac": cpf_hmac(CPF, chave=FIO.CHAVE_HMAC),
        "status": "aberto" if estado == "calculando" else "fechado", "servico": "cotacao",
        "solicitante_user_id": quem})
    status = {"pronta": "fechado", "calculando": "na_fila", "sem_resposta": "falhou"}[estado]
    for opcao, precos in (("padrao", (3100.0, 3400.0)), ("economica", (2700.0,))):
        calc = m.banco.semear("multicalculo_calculos", {
            "pedido_id": pedido["id"], "solicitante_company_id": c.id, "company_id": c.id, "opcao": opcao,
            "coberturas": {}, "status": status, "negocio_ref": f"neg-{opcao}" if status == "fechado" else None,
            "versao": 1 if status == "fechado" else None, "conta_regra": "cotacao_da_pessoa"})
        if estado != "pronta":
            continue
        for k, v in enumerate(precos):
            m.banco.semear("multicalculo_ofertas", {
                "calculo_id": calc["id"], "pedido_id": pedido["id"], "company_id": c.id,
                "solicitante_company_id": c.id, "seguradora": f"Seguradora {opcao} {k}", "premio_total": v,
                "franquia_valor": 2500.0,
                "parcelamentos": [{"parcelas": 1, "primeira_parcela": v},
                                  {"parcelas": 10, "primeira_parcela": round(v / 10, 2),
                                   "demais_parcelas": round(v / 10, 2)}]})
    if run is not None:
        run_id = str(uuid.uuid4())
        m.banco.semear("work_runs", {
            "id": run_id, "company_id": c.id, "source_type": "chat", "outcome_type": "cotacao",
            "outcome_title": "Cotação", "workflow_key": API.WORKFLOW, "thread_id": f"work:{c.id}:{run_id}",
            "input_fingerprint": "x",
            "idempotency_key": f"k-{pedido['id']}", "requester_user_id": quem, "status": "completed",
            "input_payload": {"pedido_id": pedido["id"], **run.get("entrada", {})},
            "result_payload": run.get("resultado", {})})
    return pedido


@pytest.fixture
def mundo(monkeypatch):
    FIO.instalar(monkeypatch)
    monkeypatch.setenv("BACKEND_INTERNAL_API_KEY", CHAVE)
    monkeypatch.setenv("MULTICALCULO_HMAC_KEY", FIO.CHAVE_HMAC)
    banco = FIO.BancoDaMadrugada(D.Relogio(AGORA))
    db = banco.visao("smith-api")
    m = SimpleNamespace(banco=banco, db=db, publicadas=[], mensagens=[], decifrados=0)
    monkeypatch.setattr(API, "_db", lambda: db)
    monkeypatch.setattr(API, "_agora", lambda: AGORA)

    def decifrar(cifrado):
        m.decifrados += 1
        assert cifrado.startswith("dub:")
        return json.loads(cifrado[4:])

    monkeypatch.setattr(API, "_decifrar", decifrar)

    def publicar_cotacao(company_id, pedido_id, *, pessoa_user_id, apolice_atual=None, db=None):
        # o contrato da B2 (SPEC §5): quem clicou vai como `pessoa_user_id`; o banco da sessão vai junto
        assert db is m.db and apolice_atual is None
        m.publicadas.append((company_id, pedido_id, pessoa_user_id))
        tok = f"tok{pedido_id[:8]}"
        return {"token": tok, "url": f"https://exemplo.invalid/r/{tok}", "artifact_id": str(uuid.uuid4()),
                "resumo": {"opcoes": [{"seguradora": "X", "premio": 3100.0}]}}

    def mensagem_de_cotacao(modelo, link):
        # ⛔ nunca o telefone: só o modelo da proposta e o link
        assert isinstance(modelo, dict) and link.startswith("https://")
        m.mensagens.append(link)
        return {"texto": f"Oi! A sua cotação está pronta: {link}", "texto_curto": f"Sua cotação: {link}"}

    monkeypatch.setattr(P, "publicar_cotacao", publicar_cotacao, raising=False)
    monkeypatch.setattr(MSG, "mensagem_de_cotacao", mensagem_de_cotacao, raising=False)
    app = FastAPI()
    app.include_router(API.router)
    m.cliente = TestClient(app)
    m.a = _corretora(banco, "A")
    m.b = _corretora(banco, "B")
    return m


def _lista(m, c, uid, cab=None, **params):
    r = m.cliente.get("/api/cotacoes", params={"company_id": c, "user_id": uid, **params}, headers={**H, **(cab or {})})
    assert r.status_code == 200, r.text
    return r.json()


def _post(m, pid, acao, corpo):
    return m.cliente.post(f"/api/cotacoes/{pid}/{acao}", json=corpo, headers=H)


# ---------------------------------------------------------------------------------------------------------------------
# ① duas corretoras — e a MUTAÇÃO 6
# ---------------------------------------------------------------------------------------------------------------------
def _vazamentos(m, cliente) -> list:
    """O que a API mostra à corretora A que é da B (lista, detalhe e as duas ações)."""
    pa = _cotacao(m, m.a, m.a.um, nome="Ana Exemplo")
    pb = _cotacao(m, m.b, m.b.um, nome="Bruno Exemplo")
    achados = []
    r = cliente.get("/api/cotacoes", params={"company_id": m.a.id, "user_id": m.a.admin, "escopo": "todas"}, headers=H)
    ids = {i["id"] for i in r.json().get("itens", [])} if r.status_code == 200 else set()
    if pb["id"] in ids:
        achados.append("a lista de A traz a cotação de B")
    if pa["id"] not in ids:
        achados.append("a lista de A perdeu a cotação de A")
    if cliente.get(f"/api/cotacoes/{pb['id']}", params={"company_id": m.a.id, "user_id": m.a.admin},
                   headers=H).status_code != 404:
        achados.append("o detalhe da cotação de B abre na sessão de A")
    for acao in ("apresentacao", "envio"):
        if cliente.post(f"/api/cotacoes/{pb['id']}/{acao}", json={"company_id": m.a.id, "user_id": m.a.admin},
                        headers=H).status_code != 404:
            achados.append(f"{acao} da cotação de B na sessão de A")
    return achados


def test_duas_corretoras_nunca_cruzam(mundo):
    assert _vazamentos(mundo, mundo.cliente) == []
    assert mundo.publicadas == []          # nada foi publicado com a cotação da outra


def _modulo_mutado():
    """O cotacoes.py REAL sem o filtro da corretora (o `.eq` no banco e a segunda trava) — o defeito da mutação 6."""
    fonte = Path(API.__file__).read_text(encoding="utf-8")
    alvo_banco = '.eq("company_id", cid)'
    alvo_trava = '    return str(linha.get(coluna) or "").lower() == cid'
    assert fonte.count(alvo_banco) >= 3 and fonte.count(alvo_trava) == 1     # as âncoras existem
    mutada = fonte.replace(alvo_banco, "").replace(alvo_trava, "    return True")
    spec = importlib.util.spec_from_loader("app.api.cotacoes_mutacao_6", loader=None)
    mod = importlib.util.module_from_spec(spec)
    exec(compile(mutada, "cotacoes_mutacao_6.py", "exec"), mod.__dict__)  # noqa: S102
    return mod


def test_mutacao_6_sem_o_filtro_a_outra_corretora_aparece(mundo, monkeypatch):
    mod = _modulo_mutado()
    monkeypatch.setattr(mod, "_db", lambda: mundo.db)
    monkeypatch.setattr(mod, "_agora", lambda: AGORA)
    monkeypatch.setattr(mod, "_decifrar", lambda c: json.loads(c[4:]))
    app = FastAPI()
    app.include_router(mod.router)
    achados = _vazamentos(mundo, TestClient(app))
    assert "a lista de A traz a cotação de B" in achados, achados          # 🔴 o guarda fica VERMELHO
    assert "o detalhe da cotação de B abre na sessão de A" in achados, achados


# ---------------------------------------------------------------------------------------------------------------------
# ② minhas × todas · ③ estados, a melhor parcela, o cliente
# ---------------------------------------------------------------------------------------------------------------------
def test_minhas_e_todas(mundo):
    m = mundo
    meu = _cotacao(m, m.a, m.a.um, nome="Carla Exemplo")
    dele = _cotacao(m, m.a, m.a.dois, nome="Davi Exemplo")
    minhas = _lista(m, m.a.id, m.a.um, escopo="minhas")
    assert [i["id"] for i in minhas["itens"]] == [meu["id"]]
    assert minhas["itens"][0]["quem_pediu"]["sou_eu"] is True
    todas = _lista(m, m.a.id, m.a.um, escopo="todas")
    assert {i["id"] for i in todas["itens"]} == {meu["id"], dele["id"]}
    outro = next(i for i in todas["itens"] if i["id"] == dele["id"])
    assert outro["quem_pediu"]["nome"].startswith("Pessoa1A") and outro["quem_pediu"]["sou_eu"] is False


def test_estados_parcela_e_cliente(mundo):
    m = mundo
    pronta = _cotacao(m, m.a, m.a.um, nome="Elisa Maria Exemplo")
    calc = _cotacao(m, m.a, m.a.um, estado="calculando", nome="Fabio Exemplo")
    sem = _cotacao(m, m.a, m.a.um, estado="sem_resposta", nome="Gabi Exemplo",
                   run={"entrada": {"cliente_nome_curto": "Gabi", "risco": "Carro Exemplo 2021"}})
    lista = _lista(m, m.a.id, m.a.um, escopo="todas")
    por_id = {i["id"]: i for i in lista["itens"]}
    assert por_id[pronta["id"]]["estado"] == "pronta" and por_id[pronta["id"]]["estado_rotulo"] == "Pronta"
    assert por_id[calc["id"]]["estado"] == "calculando"
    assert por_id[sem["id"]]["estado"] == "sem_resposta" and por_id[sem["id"]]["melhor"] is None
    assert lista["contagens"] == {"calculando": 1, "pronta": 1, "sem_resposta": 1}
    melhor = por_id[pronta["id"]]["melhor"]
    assert melhor["a_vista"] == 2700.0 and melhor["parcela"] == {"vezes": 10, "valor": 270.0}
    assert melhor["opcao"] == "Econômica" and por_id[pronta["id"]]["seguradoras"] == 3
    # o cliente: do pedido decifrado, só o PRIMEIRO nome e o documento mascarado; do Work Run quando ele diz
    assert por_id[pronta["id"]]["cliente"] == "Elisa" and por_id[pronta["id"]]["documento"] == "***.***.***-25"
    assert por_id[pronta["id"]]["risco"] == "Carro Exemplo 2022"
    assert por_id[sem["id"]]["cliente"] == "Gabi" and por_id[sem["id"]]["risco"] == "Carro Exemplo 2021"
    assert "Maria" not in json.dumps(lista) and CPF not in json.dumps(lista) and TELEFONE not in json.dumps(lista)
    # o filtro de estado
    so = _lista(m, m.a.id, m.a.um, escopo="todas", estado="calculando")
    assert [i["id"] for i in so["itens"]] == [calc["id"]]
    # o detalhe: as versões com o menor preço de cada uma e o link ao Agger
    d = m.cliente.get(f"/api/cotacoes/{pronta['id']}", params={"company_id": m.a.id, "user_id": m.a.um}, headers=H)
    assert d.status_code == 200, d.text
    dj = d.json()
    assert [o["rotulo"] for o in dj["opcoes"]] == ["Completa", "Econômica"]
    assert dj["opcoes"][0]["menor_preco"] == 3100.0 and dj["opcoes"][0]["seguradoras"] == 2
    assert dj["conta"]["onde"] == "pessoa" and dj["pode_enviar"] is True and TELEFONE not in d.text


# ---------------------------------------------------------------------------------------------------------------------
# ④ a busca vem SÓ no cabeçalho
# ---------------------------------------------------------------------------------------------------------------------
def test_a_busca_vem_so_no_cabecalho(mundo):
    m = mundo
    hel = _cotacao(m, m.a, m.a.um, nome="Helena Exemplo")
    _cotacao(m, m.a, m.a.um, nome="Igor Exemplo", run={"entrada": {"cliente_nome_curto": "Igor"}})
    pelo_nome = _lista(m, m.a.id, m.a.um, cab={"x-busca": "helena"}, escopo="todas")
    assert [i["id"] for i in pelo_nome["itens"]] == [hel["id"]]
    pelo_cpf = _lista(m, m.a.id, m.a.um, cab={"x-busca": "529.982.247-25"}, escopo="todas")
    assert len(pelo_cpf["itens"]) == 2                          # as duas têm o mesmo CPF sintético (pelo HMAC)
    na_query = _lista(m, m.a.id, m.a.um, escopo="todas", q="helena")
    assert len(na_query["itens"]) == 2                          # `?q=` não filtra (nem é lido)


# ---------------------------------------------------------------------------------------------------------------------
# ⑤ o envio · ⑥ a apresentação
# ---------------------------------------------------------------------------------------------------------------------
def test_envio_com_telefone_do_pedido_e_nada_vaza(mundo, caplog):
    m = mundo
    caplog.set_level(logging.DEBUG)
    p = _cotacao(m, m.a, m.a.um)
    escritas_antes = len(m.banco.linhas("work_runs")) + len(m.banco.linhas("multicalculo_pedidos"))
    r = _post(m, p["id"], "envio", {"company_id": m.a.id, "user_id": m.a.um})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["wa_me_url"].startswith("https://wa.me/55" + TELEFONE + "?text=") and j["sem_telefone"] is False
    assert "https://exemplo.invalid/r/" in j["texto"] and m.publicadas == [(m.a.id, p["id"], m.a.um)]
    # 🔴 o telefone só existe dentro do wa_me_url: nem no log, nem no banco
    assert TELEFONE not in caplog.text
    # (o `pedido_cifrado` do dublê é JSON aberto; o real é Fernet — fica de fora da caça)
    tudo = json.dumps({t: [{k: v for k, v in x.items() if k != "pedido_cifrado"} for x in m.banco.linhas(t)]
                       for t in ("work_runs", "multicalculo_pedidos", "multicalculo_calculos")}, default=str)
    assert TELEFONE not in tudo
    assert len(m.banco.linhas("work_runs")) + len(m.banco.linhas("multicalculo_pedidos")) == escritas_antes


def test_envio_sem_telefone_so_o_texto_e_copiar_nao_decifra(mundo):
    m = mundo
    p = _cotacao(m, m.a, m.a.um, telefone=None)
    r = _post(m, p["id"], "envio", {"company_id": m.a.id, "user_id": m.a.um})
    assert r.status_code == 200, r.text
    assert r.json()["sem_telefone"] is True and "wa_me_url" not in r.json() and r.json()["texto"]
    antes = m.decifrados
    c = _post(m, p["id"], "envio", {"company_id": m.a.id, "user_id": m.a.um, "via": "copiar"})
    assert c.status_code == 200 and "wa_me_url" not in c.json() and m.decifrados == antes
    # um corpo com chave estranha é recusado (a tela não manda estado nenhum)
    assert _post(m, p["id"], "envio", {"company_id": m.a.id, "user_id": m.a.um, "estado": "x"}).status_code == 400


def test_apresentacao_usa_o_link_da_conversa_e_so_publica_sem_ele(mundo):
    m = mundo
    com_link = _cotacao(m, m.a, m.a.um, run={"resultado": {"url": "https://exemplo.invalid/r/dachat", "token": "dachat"}})
    r = _post(m, com_link["id"], "apresentacao", {"company_id": m.a.id, "user_id": m.a.um})
    assert r.status_code == 200 and r.json()["url"] == "https://exemplo.invalid/r/dachat" and m.publicadas == []
    sem_link = _cotacao(m, m.a, m.a.dois)
    r = _post(m, sem_link["id"], "apresentacao", {"company_id": m.a.id, "user_id": m.a.um})
    assert r.status_code == 200 and m.publicadas == [(m.a.id, sem_link["id"], m.a.um)]
    calculando = _cotacao(m, m.a, m.a.um, estado="calculando")
    r = _post(m, calculando["id"], "apresentacao", {"company_id": m.a.id, "user_id": m.a.um})
    assert r.status_code == 409 and len(m.publicadas) == 1


# ---------------------------------------------------------------------------------------------------------------------
# ⑦ as regras da cotação na tela Configurar (D-132B-06)
# ---------------------------------------------------------------------------------------------------------------------
def test_as_regras_da_cotacao_sao_as_efetivas():
    padrao = SERV._efetivo(CFG.mesclar(None, "cotacao"), "cotacao")
    regras = padrao["regras"]
    assert regras["comissao"]["entrada"] == CFG.PADRAO_DO_PRODUTO["comissao"]["entrada"]
    assert regras["validade_dias"] == CFG.PADRAO_DO_PRODUTO["validade"]["padrao_dias"]
    assert regras["opcoes_na_pagina"] == CFG.PADRAO_DO_PRODUTO["opcoes"]["na_pagina"]
    assert regras["calculo_por_papel"] == CFG.PADRAO_DO_PRODUTO["calculo_por_papel"]
    assert set(regras["coberturas_essenciais"]) == set(CFG.PADRAO_DO_PRODUTO["coberturas_essenciais"])
    assert padrao["opcoes"] and "minima" not in padrao["opcoes"]
    # a corretora que mudou a comissão de entrada DA COTAÇÃO vê o número dela (e o padrão continua o do produto)
    entrada = CFG.PADRAO_DO_PRODUTO["comissao"]["entrada"] + 2
    dela = SERV._efetivo(CFG.mesclar({"servicos": {"cotacao": {"comissao": {"entrada": entrada}}}}, "cotacao"),
                         "cotacao")
    assert dela["regras"]["comissao"]["entrada"] == entrada != regras["comissao"]["entrada"]
    # as faixas vêm da régua da leitura: a entrada mínima é o autônomo + um passo (abaixo, a config volta ao padrão)
    f = SERV._faixas_da_cotacao(CFG.mesclar(None, "cotacao"))
    com = CFG.PADRAO_DO_PRODUTO["comissao"]
    assert f["comissao_entrada_da_cotacao"] == [com["autonomo_minimo"] + com["passo_pp"], com["teto_pct"]]
    assert "minima" not in f["opcoes_da_cotacao"] and f["validade_dias_da_cotacao"][0] >= 1


def test_a_prontidao_diz_qual_servico_tem_regra():
    class _R:
        def __init__(self, d):
            self.data = d

    class _Q:
        def __init__(self, linhas):
            self.linhas = linhas

        def select(self, *_a, **_k):
            return self

        def eq(self, *_a):
            return self

        def limit(self, *_a):
            return self

        def execute(self):
            return _R(self.linhas)

    cid = str(uuid.uuid4())
    db = SimpleNamespace(table=lambda _t: _Q([{"company_id": cid, "config": {"servicos": {"renovacao": {"modo": "calcular"}}},
                                               "atualizado_em": "x"}]))
    passo = SERV._servicos_configurados(db, cid)
    assert passo["por_servico"] == {"cotacao": False, "renovacao": True}
    vazio = SimpleNamespace(table=lambda _t: _Q([]))
    assert SERV._servicos_configurados(vazio, cid)["por_servico"] == {"cotacao": False, "renovacao": False}
