# -*- coding: utf-8 -*-
"""SPEC-131-B · G2 — a API da aba Renovações (`backend/app/api/renovacoes.py`).

    ① duas corretoras com o MESMO nosnum: a lista, o detalhe e as duas ações nunca cruzam (o filtro, não a RLS)
    ② "minhas" = dono ou responsável = eu · "todas" = a corretora inteira
    ③ o item: nome CURTO, documento MASCARADO, a FRASE do motivo, os cálculos por opção (menor preço, nº de seguradoras)
    ④ a apresentação: `calculada → apresentada` pela máquina, uma vez (a 2ª chamada não gera evento)
    ⑤ o envio: o `wa.me` com o telefone lido NA HORA; evento `aberto_para_envio` (quem, versão, via) e `enviada`
       🔴 MUTAÇÃO 5 da SPEC: o telefone do cliente em NENHUM log (caplog DEBUG) e em NENHUMA linha/escrita do banco dublê
    ⑥ sem telefone: só o texto; "Copiar a mensagem" registra o envio sem ler telefone
    ⑦ 🔴 MUTAÇÃO 4 da SPEC: nenhuma rota muda estado por coluna (as rotas são EXATAMENTE as do contrato; corpo com
       `estado`/`coluna` é 400 e o banco não muda)

Dublê só na BORDA: o banco (PostgREST em memória com as travas da 20261013_01), a InfoCap da corretora (`abrir_fonte`)
e as duas funções da G4 pelo CONTRATO (`publicar_renovacao`, `mensagem_de_renovacao`). O repositório e a máquina da
131-A são os REAIS. ⛔ Dados sintéticos e óbvios.
Rodar: cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_spec131b_api_renovacoes.py -q -p no:cacheprovider
"""
from __future__ import annotations

import json
import logging
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import test_spec131a_o_fio as FIO  # noqa: E402  (o esquema e as travas da 20261013_01 — UM dublê)
import dubles_do_work_os as D  # noqa: E402
import app.api.renovacoes as API  # noqa: E402
import app.services.multicalculo.renovacao as R  # noqa: E402
from app.services.multicalculo import mensagem as MSG  # noqa: E402
from app.services.multicalculo import proposta as P  # noqa: E402

CHAVE = "chave-interna-de-teste-131b"
HOJE = date(2026, 10, 13)
#: o telefone SINTÉTICO do cliente — o que a mutação 5 caça em todo log e em toda linha
DDD, NUMERO = "11", "912345678"
TELEFONE = "55" + DDD + NUMERO
NOSNUM_COMUM = "990001"


class FonteDuble:
    """A InfoCap da corretora: `/documento` dá o codcli; `/cliente` dá o cadastro (com ou sem telefone)."""

    def __init__(self, com_telefone: bool = True):
        self.com_telefone = com_telefone
        self.chamadas = []

    def documento_cru(self, codfil, nosnum):
        self.chamadas.append(("documento", codfil, nosnum))
        return {"codcli": 4242, "nosnum": nosnum}

    def cliente_cru(self, codfil, codigo):
        self.chamadas.append(("cliente", codfil, codigo))
        if not self.com_telefone:
            return {"codigo": codigo, "telefones": []}
        return {"codigo": codigo, "telefone": "(11) 3333-4444",
                "telefones": [{"ddd": "11", "numero": "33334444"}, {"ddd": DDD, "numero": NUMERO}]}


def _corretora(banco, nome: str, *, ligada: bool) -> SimpleNamespace:
    cid = str(uuid.uuid4())
    banco.semear("companies", {"id": cid, "company_kind": "client", "company_name": f"Corretora {nome}",
                               "is_technical": False})
    if ligada:
        banco.semear("tenant_auxiliaries", {"company_id": cid, "slug": "renovacao", "status": "active"})
    pessoas = []
    for i, papel in enumerate(("member", "member", "admin_company")):
        uid = str(uuid.uuid4())
        banco.semear("users_v2", {"id": uid, "first_name": f"Pessoa{i}{nome}", "last_name": "Teste"})
        banco.semear("company_members", {"user_id": uid, "company_id": cid, "role": papel})
        pessoas.append(uid)
    return SimpleNamespace(id=cid, dono1=pessoas[0], dono2=pessoas[1], admin=pessoas[2])


def _renovacao(banco, c, *, nosnum: str, estado: str, dono: str = None, responsavel: str = None, motivo: str = None,
               fimvig: date = HOJE + timedelta(days=5), nome: str = "Ficticio", com_calculos: bool = True,
               premio_atual: float = 2000.0) -> dict:
    pedido_id = None
    if com_calculos:
        pedido = banco.semear("multicalculo_pedidos", {
            "company_id": c.id, "origem": "auxiliar", "ramo": 31,
            "opcoes": ["anterior", "franquia_reduzida", "completa_mais"], "corretoras": [c.id],
            "pedido_cifrado": "x", "status": "fechado", "servico": "renovacao"})
        pedido_id = pedido["id"]
    linha = banco.semear("renovacoes", {
        "company_id": c.id, "sistema": "infocap", "codfil": 1, "nosnum": nosnum, "fimvig": fimvig.isoformat(),
        "ramo_sigla": "AUTO", "ramo_agger": 31, "seguradora_atual": "Seguradora Atual Teste",
        "premio_atual": premio_atual, "cliente_nome_curto": nome, "documento_mascarado": "***.***.***-00",
        "documento_hmac": "a" * 64, "dono_user_id": dono, "responsavel_user_id": responsavel, "estado": estado,
        "motivo": motivo, "pedido_id": pedido_id, "versao": 3})
    if com_calculos:
        precos = {"anterior": (2100.0, 2400.0), "franquia_reduzida": (2500.0,), "completa_mais": (2900.0, 3100.0)}
        for opcao, valores in precos.items():
            calc = banco.semear("multicalculo_calculos", {
                "pedido_id": pedido_id, "solicitante_company_id": c.id, "company_id": c.id, "opcao": opcao,
                "coberturas": {}, "status": "fechado", "negocio_ref": f"neg-{opcao}", "versao": 1})
            for k, v in enumerate(valores):
                banco.semear("multicalculo_ofertas", {
                    "calculo_id": calc["id"], "pedido_id": pedido_id, "company_id": c.id,
                    "solicitante_company_id": c.id, "seguradora": f"Seguradora {k}", "premio_total": v,
                    "franquia_valor": 3000.0})
    return linha


@pytest.fixture
def mundo(monkeypatch):
    FIO.instalar(monkeypatch)
    monkeypatch.setenv("BACKEND_INTERNAL_API_KEY", CHAVE)
    monkeypatch.setenv("MULTICALCULO_HMAC_KEY", FIO.CHAVE_HMAC)
    relogio = D.Relogio(datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc))
    banco = FIO.BancoDaMadrugada(relogio)
    db = banco.visao("smith-api")
    monkeypatch.setattr(API, "_db", lambda: db)
    monkeypatch.setattr(API, "_hoje", lambda: HOJE)

    m = SimpleNamespace(banco=banco, db=db, fontes={}, publicadas=[], mensagens=[])

    def publicar_renovacao(company_id, renovacao_id, *, pessoa):
        m.publicadas.append((company_id, renovacao_id, pessoa))
        return {"token": f"tok{renovacao_id[:8]}", "url": f"https://exemplo.invalid/r/tok{renovacao_id[:8]}",
                "versao": 1}

    def mensagem_de_renovacao(renovacao, proposta, *, pessoa):
        m.mensagens.append((renovacao["id"], pessoa))
        return {"texto": f"Oi, {renovacao['cliente_nome_curto']}! Sua renovação está pronta: {proposta['url']}",
                "texto_curto": f"Sua renovação: {proposta['url']}", "link": proposta["url"]}

    monkeypatch.setattr(P, "publicar_renovacao", publicar_renovacao, raising=False)
    monkeypatch.setattr(MSG, "mensagem_de_renovacao", mensagem_de_renovacao, raising=False)

    async def abrir_fonte(_db, company_id):
        if company_id not in m.fontes:
            raise RuntimeError(f"InfoCap fora para {TELEFONE}")   # a mensagem carrega o dado: o log NÃO pode
        return m.fontes[company_id]

    monkeypatch.setattr(API, "abrir_fonte", abrir_fonte)
    app = FastAPI()
    app.include_router(API.router)
    m.cliente = TestClient(app)
    m.a = _corretora(banco, "A", ligada=True)
    m.b = _corretora(banco, "B", ligada=False)
    m.fontes[m.a.id] = FonteDuble()
    m.fontes[m.b.id] = FonteDuble()
    return m


H = {"X-AutoBrokers-Internal-Key": CHAVE}


def _lista(m, c, uid, **params):
    r = m.cliente.get("/api/renovacoes", params={"company_id": c, "user_id": uid, **params}, headers=H)
    assert r.status_code == 200, r.text
    return r.json()


def _post(m, rid, acao, corpo):
    return m.cliente.post(f"/api/renovacoes/{rid}/{acao}", json=corpo, headers=H)


def _eventos(m, rid):
    return [e for e in m.banco.linhas("renovacao_eventos") if e["renovacao_id"] == rid]


def _linha(m, rid):
    return next(x for x in m.banco.linhas("renovacoes") if x["id"] == rid)


# ---------------------------------------------------------------------------------------------------------------------
# ① duas corretoras
# ---------------------------------------------------------------------------------------------------------------------
def test_duas_corretoras_com_o_mesmo_nosnum_nunca_cruzam(mundo):
    m = mundo
    ra = _renovacao(m.banco, m.a, nosnum=NOSNUM_COMUM, estado="calculada", dono=m.a.dono1)
    rb = _renovacao(m.banco, m.b, nosnum=NOSNUM_COMUM, estado="calculada", dono=m.b.dono1, nome="Outro")

    ids_a = {i["id"] for i in _lista(m, m.a.id, m.a.admin, escopo="todas")["itens"]}
    ids_b = {i["id"] for i in _lista(m, m.b.id, m.b.admin, escopo="todas")["itens"]}
    assert ids_a == {ra["id"]} and ids_b == {rb["id"]}

    # o id da OUTRA corretora com a sessão desta: "não existe" — no detalhe e nas duas ações
    r = m.cliente.get(f"/api/renovacoes/{rb['id']}", params={"company_id": m.a.id, "user_id": m.a.admin}, headers=H)
    assert r.status_code == 404
    antes = json.dumps(_linha(m, rb["id"]), default=str, sort_keys=True)
    for acao in ("apresentacao", "envio"):
        r = _post(m, rb["id"], acao, {"company_id": m.a.id, "user_id": m.a.admin})
        assert r.status_code == 404, (acao, r.text)
    assert json.dumps(_linha(m, rb["id"]), default=str, sort_keys=True) == antes
    assert _eventos(m, rb["id"]) == [] and m.publicadas == []
    # os cálculos de B nunca entram no resumo de A (o filtro do solicitante)
    (item_a,) = _lista(m, m.a.id, m.a.admin, escopo="todas")["itens"]
    assert item_a["calculos"][0]["seguradoras"] == 2


def test_sem_a_chave_interna_e_401(mundo):
    r = mundo.cliente.get("/api/renovacoes", params={"company_id": mundo.a.id, "user_id": mundo.a.admin})
    assert r.status_code == 401


# ---------------------------------------------------------------------------------------------------------------------
# ② minhas × todas
# ---------------------------------------------------------------------------------------------------------------------
def test_minhas_e_dono_ou_responsavel_todas_e_a_corretora(mundo):
    m = mundo
    r1 = _renovacao(m.banco, m.a, nosnum="1", estado="calculada", dono=m.a.dono1)
    r2 = _renovacao(m.banco, m.a, nosnum="2", estado="calculada", dono=m.a.dono2, responsavel=m.a.dono1)
    r3 = _renovacao(m.banco, m.a, nosnum="3", estado="calculada", dono=m.a.dono2)
    minhas = {i["id"] for i in _lista(m, m.a.id, m.a.dono1, escopo="minhas")["itens"]}
    todas = {i["id"] for i in _lista(m, m.a.id, m.a.dono1, escopo="todas")["itens"]}
    assert minhas == {r1["id"], r2["id"]}
    assert todas == {r1["id"], r2["id"], r3["id"]}
    r = m.cliente.get("/api/renovacoes", params={"company_id": m.a.id, "user_id": m.a.dono1, "escopo": "tudo"},
                      headers=H)
    assert r.status_code == 400


def test_filtros_estado_coluna_ramo_seguradora_datas_e_busca(mundo):
    m = mundo
    r1 = _renovacao(m.banco, m.a, nosnum="1", estado="calculada", dono=m.a.dono1, nome="Ana")
    r2 = _renovacao(m.banco, m.a, nosnum="2", estado="pendente", motivo="ramo_nao_cotado", dono=m.a.dono1,
                    nome="Bruno", fimvig=HOJE + timedelta(days=20), com_calculos=False)
    _renovacao(m.banco, m.a, nosnum="3", estado="substituida", dono=m.a.dono1, com_calculos=False)
    _renovacao(m.banco, m.a, nosnum="4", estado="enviada", dono=m.a.dono1, fimvig=HOJE - timedelta(days=60),
               com_calculos=False)   # venceu há 60 dias: fora da janela padrão

    def ids(**p):
        return {i["id"] for i in _lista(m, m.a.id, m.a.dono1, escopo="minhas", **p)["itens"]}

    assert ids() == {r1["id"], r2["id"]}                        # substituída e vencida há muito não aparecem
    assert ids(estado="vai_calcular") == {r2["id"]}             # a COLUNA
    assert ids(estado="calculada,apresentada") == {r1["id"]}     # o estado cru
    assert ids(ramo="auto") == {r1["id"], r2["id"]}
    assert ids(seguradora="seguradora atual teste") == {r1["id"], r2["id"]}
    assert ids(de=HOJE.isoformat(), ate=(HOJE + timedelta(days=7)).isoformat()) == {r1["id"]}
    assert ids(q="brú") == {r2["id"]}                            # sem acento, sem caixa
    r = m.cliente.get("/api/renovacoes", params={"company_id": m.a.id, "user_id": m.a.dono1, "de": "13/10/2026"},
                      headers=H)
    assert r.status_code == 400


# ---------------------------------------------------------------------------------------------------------------------
# ③ o item
# ---------------------------------------------------------------------------------------------------------------------
def test_o_item_tem_nome_curto_documento_mascarado_frase_e_calculos_por_opcao(mundo):
    m = mundo
    r1 = _renovacao(m.banco, m.a, nosnum="1", estado="calculada", dono=m.a.dono1)
    _renovacao(m.banco, m.a, nosnum="2", estado="pendente", motivo="ramo_nao_cotado", dono=m.a.dono1,
               com_calculos=False)
    corpo = _lista(m, m.a.id, m.a.dono1, escopo="todas")
    bruto = json.dumps(corpo, ensure_ascii=False)
    assert "documento_hmac" not in bruto and "nosnum" not in bruto and "a" * 64 not in bruto
    calc = next(i for i in corpo["itens"] if i["id"] == r1["id"])
    pend = next(i for i in corpo["itens"] if i["id"] != r1["id"])
    assert calc["cliente"] == "Ficticio" and calc["documento"] == "***.***.***-00"
    assert calc["responsavel"]["nome"] == "Pessoa0A Teste"
    # a ordem da página: a "Sua renovação" em 1º; menor preço e nº de seguradoras de cada opção
    assert [c["opcao"] for c in calc["calculos"]] == ["anterior", "franquia_reduzida", "completa_mais"]
    assert [c["rotulo"] for c in calc["calculos"]][0] == "Sua renovação"
    assert [(c["menor_preco"], c["seguradoras"]) for c in calc["calculos"]] == [(2100.0, 2), (2500.0, 1),
                                                                                 (2900.0, 2)]
    assert calc["premio_novo"] == 2100.0 and calc["variacao_pct"] == 5.0
    assert calc["calculos"][0]["agger_url"].endswith("/cotacao/auto/resultados/neg-anterior")
    assert calc["coluna"] == "calculada" and "para_enviar_hoje" in calc["atalhos"]
    assert "vence_esta_semana" in calc["atalhos"] and not calc["precisa_de_voce"]
    # o motivo vem com a FRASE humana da 131-A
    assert pend["precisa_de_voce"] and pend["motivo_frase"] == R.frase_do_motivo("ramo_nao_cotado")
    assert pend["coluna"] == "vai_calcular" and pend["calculos"] == []
    assert corpo["contagens"] == {"para_enviar_hoje": 1, "precisa_de_voce": 1, "vence_esta_semana": 2,
                                  "enviadas": 0}
    assert corpo["ligado"] is True and _lista(m, m.b.id, m.b.admin)["ligado"] is False


def test_toda_coluna_vem_do_estado_e_substituida_nao_aparece():
    for estado in R.ESTADOS_LIGADOS + R.ESTADOS_RESERVADOS:
        if estado == "substituida":
            assert estado not in API.ESTADOS_VISIVEIS
            continue
        assert API.COLUNA_DO_ESTADO[estado] in ("vai_calcular", "calculada", "enviada", "em_negociacao", "fechada",
                                                "emitida", "perdida"), estado


def test_o_detalhe_traz_a_linha_do_tempo_o_proximo_passo_e_o_agger(mundo):
    m = mundo
    r1 = _renovacao(m.banco, m.a, nosnum="1", estado="calculada", dono=m.a.dono1)
    R.RepositorioDeRenovacoes(m.db)._evento(m.a.id, r1["id"], "calculando", "calculada", "smith-worker", None)
    r = m.cliente.get(f"/api/renovacoes/{r1['id']}", params={"company_id": m.a.id, "user_id": m.a.dono1}, headers=H)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["proximo_passo"].startswith("Confira os cálculos")
    assert d["agger_url"].endswith("/cotacao/auto/resultados/neg-anterior")
    assert d["eventos"][0]["frase"] == "Calculada"


# ---------------------------------------------------------------------------------------------------------------------
# ④ a apresentação
# ---------------------------------------------------------------------------------------------------------------------
def test_apresentacao_publica_e_vira_apresentada_uma_vez(mundo):
    m = mundo
    r1 = _renovacao(m.banco, m.a, nosnum="1", estado="calculada", dono=m.a.dono1)
    corpo = {"company_id": m.a.id, "user_id": m.a.dono1}
    r = _post(m, r1["id"], "apresentacao", corpo)
    assert r.status_code == 200, r.text
    assert r.json()["url"].startswith("https://exemplo.invalid/r/") and r.json()["estado"] == "apresentada"
    assert m.publicadas == [(m.a.id, r1["id"], m.a.dono1)]
    assert _linha(m, r1["id"])["estado"] == "apresentada"
    assert _linha(m, r1["id"])["proposta_ref"] == f"tok{r1['id'][:8]}"
    assert [(e["de"], e["para"], e["por"]) for e in _eventos(m, r1["id"])] == [("calculada", "apresentada",
                                                                                m.a.dono1)]
    r = _post(m, r1["id"], "apresentacao", corpo)                 # a 2ª vez: a mesma página, nenhum evento a mais
    assert r.status_code == 200 and len(_eventos(m, r1["id"])) == 1


def test_o_que_nao_foi_calculado_nao_se_apresenta_nem_se_envia(mundo):
    m = mundo
    r1 = _renovacao(m.banco, m.a, nosnum="1", estado="pendente", motivo="falta_dado", dono=m.a.dono1,
                    com_calculos=False)
    for acao in ("apresentacao", "envio"):
        r = _post(m, r1["id"], acao, {"company_id": m.a.id, "user_id": m.a.dono1})
        assert r.status_code == 409, r.text
    assert m.publicadas == [] and _eventos(m, r1["id"]) == []


# ---------------------------------------------------------------------------------------------------------------------
# ⑤ o envio — e a MUTAÇÃO 5 (o telefone em nenhum log e em nenhuma linha)
# ---------------------------------------------------------------------------------------------------------------------
def _o_telefone_em_algum_lugar(m, caplog) -> list:
    achados = []
    alvos = (TELEFONE, DDD + NUMERO, NUMERO)
    for rec in caplog.records:
        texto = rec.getMessage() + " " + repr(rec.args)
        if any(a in texto for a in alvos):
            achados.append(f"log {rec.name}: {rec.levelname}")
    for tabela, linhas in m.banco.tabelas.items():
        for linha in linhas:
            if any(a in json.dumps(linha, default=str) for a in alvos):
                achados.append(f"linha de {tabela}")
    for esc in m.banco.escritas:
        if any(a in json.dumps(getattr(esc, "__dict__", {}), default=str) for a in alvos):
            achados.append(f"escrita em {getattr(esc, 'tabela', '?')}")
    return achados


def test_envio_abre_o_wa_me_do_cliente_e_o_telefone_nunca_e_gravado_nem_logado(mundo, caplog):
    m = mundo
    caplog.set_level(logging.DEBUG)
    r1 = _renovacao(m.banco, m.a, nosnum="1", estado="calculada", dono=m.a.dono1)
    r = _post(m, r1["id"], "envio", {"company_id": m.a.id, "user_id": m.a.dono2})
    assert r.status_code == 200, r.text
    corpo = r.json()
    # o CELULAR (não o fixo), no wa.me; o texto do link é o mesmo do "Copiar"
    assert corpo["wa_me_url"].startswith(f"https://wa.me/{TELEFONE}?text=")
    assert corpo["sem_telefone"] is False and corpo["texto"].startswith("Oi, Ficticio!")
    assert corpo["estado"] == "enviada" and _linha(m, r1["id"])["estado"] == "enviada"
    ev = _eventos(m, r1["id"])
    assert [(e["de"], e["para"]) for e in ev] == [("calculada", "apresentada"), ("apresentada", "enviada")]
    assert ev[-1]["motivo"] == "aberto_para_envio" and ev[-1]["por"] == m.a.dono2
    assert ev[-1]["dados"]["via"] == "whatsapp" and ev[-1]["dados"]["versao"] == 4
    assert ("documento", 1, "1") in m.fontes[m.a.id].chamadas    # lido NA HORA, na InfoCap DESTA corretora
    # 🔴 mutação 5: o telefone só existe na resposta
    assert _o_telefone_em_algum_lugar(m, caplog) == []
    # reabrir o envio de uma enviada: só o evento (a máquina não tem enviada → enviada)
    r = _post(m, r1["id"], "envio", {"company_id": m.a.id, "user_id": m.a.dono1})
    assert r.status_code == 200 and len(_eventos(m, r1["id"])) == 3
    assert _o_telefone_em_algum_lugar(m, caplog) == []


def test_o_guarda_do_telefone_consegue_ficar_vermelho(mundo, caplog):
    """§9.3: o guarda acha o telefone quando ele ESTÁ lá (linha de controle da mutação 5)."""
    m = mundo
    caplog.set_level(logging.DEBUG)
    logging.getLogger("app.api.renovacoes").info("vazou %s", TELEFONE)
    assert _o_telefone_em_algum_lugar(m, caplog) != []


def test_sem_telefone_devolve_so_o_texto_e_copiar_registra_o_envio(mundo, caplog):
    m = mundo
    caplog.set_level(logging.DEBUG)
    m.fontes[m.a.id] = FonteDuble(com_telefone=False)
    r1 = _renovacao(m.banco, m.a, nosnum="1", estado="apresentada", dono=m.a.dono1)
    r = _post(m, r1["id"], "envio", {"company_id": m.a.id, "user_id": m.a.dono1})
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["sem_telefone"] is True and "wa_me_url" not in corpo and corpo["texto"]
    assert _linha(m, r1["id"])["estado"] == "apresentada" and _eventos(m, r1["id"]) == []   # nada foi aberto
    chamadas_antes = len(m.fontes[m.a.id].chamadas)
    r = _post(m, r1["id"], "envio", {"company_id": m.a.id, "user_id": m.a.dono1, "via": "copiar"})
    assert r.status_code == 200 and r.json()["texto"] == corpo["texto"] and "wa_me_url" not in r.json()
    assert len(m.fontes[m.a.id].chamadas) == chamadas_antes        # copiar não lê telefone nenhum
    (ev,) = _eventos(m, r1["id"])
    assert ev["para"] == "enviada" and ev["dados"]["via"] == "copiar"


def test_infocap_fora_vira_sem_telefone_e_o_erro_nao_vaza_o_dado(mundo, caplog):
    m = mundo
    caplog.set_level(logging.DEBUG)
    del m.fontes[m.a.id]                                          # a borda levanta COM o telefone na mensagem
    r1 = _renovacao(m.banco, m.a, nosnum="1", estado="calculada", dono=m.a.dono1)
    r = _post(m, r1["id"], "envio", {"company_id": m.a.id, "user_id": m.a.dono1})
    assert r.status_code == 200 and r.json()["sem_telefone"] is True
    assert _o_telefone_em_algum_lugar(m, caplog) == []
    assert any("RuntimeError" in rec.getMessage() for rec in caplog.records)


def test_o_texto_longo_vai_curto_no_link_e_inteiro_no_copiar(mundo, monkeypatch):
    m = mundo
    longo = "x" * (API.LIMITE_DO_TEXTO_NO_LINK + 50)
    monkeypatch.setattr(MSG, "mensagem_de_renovacao",
                        lambda ren, prop, *, pessoa: {"texto": longo, "texto_curto": "curto", "link": prop["url"]},
                        raising=False)
    r1 = _renovacao(m.banco, m.a, nosnum="1", estado="calculada", dono=m.a.dono1)
    corpo = _post(m, r1["id"], "envio", {"company_id": m.a.id, "user_id": m.a.dono1}).json()
    assert corpo["wa_me_url"].endswith("?text=curto") and corpo["texto"] == "curto"
    assert corpo["texto_completo"] == longo


def test_numero_de_whatsapp_prefere_o_celular_e_recusa_lixo():
    f = API.numero_de_whatsapp
    assert f({"telefone": "(11) 3333-4444", "telefones": [{"ddd": "21", "numero": "98888-7777"}]}) == "5521988887777"
    assert f({"telefone": "011 3333-4444"}) == "551133334444"
    assert f({"telefones": ["+55 (31) 99999-0000"]}) == "5531999990000"
    assert f({"telefone": "123"}) is None and f({}) is None


# ---------------------------------------------------------------------------------------------------------------------
# ⑦ a MUTAÇÃO 4 — arrastar não existe na API
# ---------------------------------------------------------------------------------------------------------------------
CONTRATO = {("GET", "/api/renovacoes"), ("GET", "/api/renovacoes/{renovacao_id}"),
            ("POST", "/api/renovacoes/{renovacao_id}/apresentacao"), ("POST", "/api/renovacoes/{renovacao_id}/envio")}


def test_nenhuma_rota_muda_estado_por_coluna(mundo):
    m = mundo
    rotas = {(metodo, r.path) for r in API.router.routes for metodo in getattr(r, "methods", set())}
    assert rotas == CONTRATO, rotas - CONTRATO
    r1 = _renovacao(m.banco, m.a, nosnum="1", estado="calculada", dono=m.a.dono1)
    for acao in ("apresentacao", "envio"):
        for estranho in ({"estado": "perdida"}, {"coluna": "fechada"}, {"para": "enviada"}):
            r = _post(m, r1["id"], acao, {"company_id": m.a.id, "user_id": m.a.dono1, **estranho})
            assert r.status_code == 400, (acao, estranho, r.text)
    assert _linha(m, r1["id"])["estado"] == "calculada" and _eventos(m, r1["id"]) == []
    assert m.publicadas == []


def test_a_tela_nao_tem_como_arrastar():
    """A FORMA da declaração (CLAUDE.md §9.4, exceção): o quadro e a aba não têm handler nem biblioteca de arrasto —
    a coluna vem do estado. Linha de controle: o padrão casa num texto que arrasta."""
    import re

    padrao = re.compile(r"draggable|onDrag|onDrop|@dnd-kit|react-beautiful-dnd|react-dnd")
    assert padrao.search('<div draggable onDragStart={x} />')            # o guarda consegue ficar vermelho
    raiz = BACKEND.parent
    arquivos = [raiz / "components/aplicativos/QuadroOuLista.tsx",
                *sorted((raiz / "components/aplicativos/renovacao").glob("*.ts*"))]
    assert len(arquivos) >= 2
    achados = [str(a.relative_to(raiz)) for a in arquivos if padrao.search(a.read_text(encoding="utf-8"))]
    assert achados == []
