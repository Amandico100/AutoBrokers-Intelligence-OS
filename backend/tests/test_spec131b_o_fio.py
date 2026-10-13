# -*- coding: utf-8 -*-
"""SPEC-131-B · G5 — O FIO (SPEC §2), de ponta a ponta, com a saída REAL de cada fatia como entrada da seguinte.

    renovação `calculada` (no banco dublê, com o pedido e as ofertas do canário)
      → GET  /api/renovacoes?escopo=minhas         (G2: a lista do DONO a mostra, "pode enviar")
      → POST /api/renovacoes/<id>/apresentacao     (G2 → G4: `publicar_renovacao` REAL → o Hub → /r/<token>)
      → o HTML SERVIDO por `abrir_compartilhado`    (G4: a página de RENOVAÇÃO — hero com o vencimento, "Sua
                                                    renovação" em 1º, a relação com prova, nada de "a melhor das N")
      → POST /api/renovacoes/<id>/envio            (G2 → G4: `mensagem_de_renovacao` REAL, assinada por QUEM clica;
                                                    o MESMO link da apresentação, sem republicar; `{wa_me_url, texto}`;
                                                    evento `aberto_para_envio` SEM telefone; estado `enviada`)
      → a mesma chamada com a sessão de OUTRA corretora → 404 (o filtro, não a RLS)

Motor REAL (API, repositório e máquina da 131-A, porta, comparação, Hub, página, mensagem). Dublê só na BORDA: o banco
(o PostgREST em memória da 129-B, o mesmo da G4) e a InfoCap da corretora (`dono.abrir_fonte` — o histórico da apólice
e o cadastro do cliente; nenhuma chamada real). ⛔ Dados sintéticos e óbvios; nenhum nome de corretora (§13.9).
Rodar: cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_spec131b_o_fio.py -q -p no:cacheprovider
"""
from __future__ import annotations

import json
import logging
import re
import sys
import uuid
from pathlib import Path
from urllib.parse import unquote

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.api.renovacoes as API  # noqa: E402
import test_spec131b_a_pagina_de_renovacao as G4  # noqa: E402  (o mundo da G4: o pedido, as ofertas, o dono)
from app.services.artifacts.service import ArtifactService  # noqa: E402
from app.services.sistema_de_gestao import dono as DONO  # noqa: E402
from test_spec130a_o_fio import CHROME, ordem_das_opcoes, texto_visivel  # noqa: E402

CHAVE = "chave-interna-de-teste-131b-fio"
H = {"X-AutoBrokers-Internal-Key": CHAVE}
#: o telefone SINTÉTICO do cliente: só pode existir dentro do `wa_me_url` da resposta (mutação 5)
DDD, NUMERO = "11", "912340000"
TELEFONE = "55" + DDD + NUMERO


class InfocapDaCorretora:
    """A borda: a InfoCap DESTA corretora. `historico_cru` = o envelope de `/documento` em linhas (a cadeia
    `nosnum_ren` de 3 anos da G4); `documento_cru` → o `codcli`; `cliente_cru` → o cadastro com o celular."""

    def __init__(self):
        self.chamadas = []
        self._envelope = G4.historico()(None, None, None)

    def historico_cru(self, codfil, nosnum):
        self.chamadas.append(("historico", codfil, nosnum))
        return list(self._envelope["documento"]) + list(self._envelope["historico"])

    def documento_cru(self, codfil, nosnum):
        self.chamadas.append(("documento", codfil, nosnum))
        return {"codcli": 4242, "nosnum": nosnum}

    def cliente_cru(self, codfil, codigo):
        self.chamadas.append(("cliente", codfil, codigo))
        return {"codigo": codigo, "telefones": [{"ddd": DDD, "numero": NUMERO}]}


@pytest.fixture
def fio(monkeypatch):
    m = G4.mundo(monkeypatch)                     # a renovação `calculada` da corretora beta, o dono, a corretora alfa
    monkeypatch.setenv("BACKEND_INTERNAL_API_KEY", CHAVE)
    monkeypatch.setattr(API, "_db", lambda: m.db)
    fonte = InfocapDaCorretora()

    async def abrir_fonte(_db, company_id):
        if str(company_id).lower() != str(m.beta).lower():
            raise AssertionError("a InfoCap de OUTRA corretora foi aberta")
        return fonte

    monkeypatch.setattr(DONO, "abrir_fonte", abrir_fonte)
    app = FastAPI()
    app.include_router(API.router)
    m.cliente = TestClient(app)
    m.fonte = fonte
    m.outro_da_alfa = str(uuid.uuid4())
    m.banco.semear("users_v2", {"id": m.outro_da_alfa, "first_name": "Outro"})
    m.banco.semear("company_members", {"user_id": m.outro_da_alfa, "company_id": m.alfa, "status": "active"})
    return m


def _linha(m):
    return next(x for x in m.banco.linhas("renovacoes") if x["id"] == G4.RENOVACAO)


def _eventos(m):
    return [e for e in m.banco.linhas("renovacao_eventos") if e["renovacao_id"] == G4.RENOVACAO]


def _o_telefone_em_algum_lugar(m, caplog):
    alvos = (TELEFONE, DDD + NUMERO, NUMERO)
    achados = [f"log {r.name}" for r in caplog.records
               if any(a in (r.getMessage() + " " + repr(r.args)) for a in alvos)]
    for tabela, linhas in m.banco.tabelas.items():
        if any(any(a in json.dumps(l, default=str) for a in alvos) for l in linhas):
            achados.append(f"linha de {tabela}")
    return achados


def test_o_fio_da_renovacao_calculada_ao_whatsapp_do_comercial(fio, caplog):
    m = fio
    caplog.set_level(logging.DEBUG)
    sessao = {"company_id": m.beta, "user_id": G4.DONO}

    # ① a lista "minhas" do DONO mostra a renovação calculada, pronta para enviar
    r = m.cliente.get("/api/renovacoes", params={**sessao, "escopo": "minhas"}, headers=H)
    assert r.status_code == 200, r.text
    (item,) = [i for i in r.json()["itens"] if i["id"] == G4.RENOVACAO]
    assert item["estado"] == "calculada" and item["pode_enviar"] is True and item["coluna"] == "calculada"
    assert item["cliente"] == "Ana" and item["vence_em"] == G4.VENCE.isoformat()

    # ② "Ver apresentação": a G4 REAL publica; a API leva a `apresentada` com a referência da página
    versoes_antes = len(m.banco.linhas("artifact_versions"))
    r = m.cliente.post(f"/api/renovacoes/{G4.RENOVACAO}/apresentacao", json=sessao, headers=H)
    assert r.status_code == 200, r.text
    apres = r.json()
    token = apres["token"]
    assert apres["url"] == f"{G4.BASE}/r/{token}" and apres["estado"] == "apresentada"
    assert _linha(m)["estado"] == "apresentada" and _linha(m)["proposta_ref"] == token
    assert len(m.banco.linhas("artifact_versions")) == versoes_antes + 1

    # ③ o HTML SERVIDO é o de RENOVAÇÃO
    servido = ArtifactService(m.banco.visao("rota-publica")).abrir_compartilhado(token, user_agent=CHROME)
    assert servido and servido["kind"] == "proposal"
    doc = servido["html"]
    txt = texto_visivel(doc)
    h1 = texto_visivel(re.search(r"<h1>(.*?)</h1>", doc, re.S).group(1))
    assert h1.endswith(f"vence em {G4.VENCE.strftime('%d/%m/%Y')}"), h1
    assert ordem_das_opcoes(doc)[0] == "sua_renovacao"
    assert "O seu seguro hoje × a renovação" in txt
    assert "Você renova com a gente há 3 anos." in txt            # a prova pela cadeia, lida pelo leitor PÚBLICO
    assert ("historico", 1, G4.NOSNUM) in m.fonte.chamadas
    for proibida in ("a melhor das", "Mais em conta", "Recomendada", "Comparação independente", "cliente desde"):
        assert proibida not in txt, proibida
    assert NUMERO not in doc                                        # o telefone do cliente nunca na página

    # ④ "Enviar pelo WhatsApp": a MESMA página (nenhuma versão nova), a mensagem assinada por quem clicou
    r = m.cliente.post(f"/api/renovacoes/{G4.RENOVACAO}/envio", json=sessao, headers=H)
    assert r.status_code == 200, r.text
    env = r.json()
    assert env["wa_me_url"].startswith(f"https://wa.me/{TELEFONE}?text=")
    no_link = unquote(env["wa_me_url"].split("?text=", 1)[1])
    assert no_link == env["texto"] and f"/r/{token}" in env["texto"]
    assert f"/r/{token}" in env["texto_completo"] and "Aqui é Bruna" in env["texto_completo"]
    assert "Ana" in env["texto_completo"] and "a melhor das" not in env["texto_completo"]
    assert len(m.banco.linhas("artifact_versions")) == versoes_antes + 1, "o envio republicou a página"
    assert env["estado"] == "enviada" and _linha(m)["estado"] == "enviada"
    ev = _eventos(m)
    assert [(e["de"], e["para"]) for e in ev] == [("calculada", "apresentada"), ("apresentada", "enviada")]
    assert ev[-1]["motivo"] == "aberto_para_envio" and ev[-1]["por"] == G4.DONO
    assert ev[-1]["dados"]["via"] == "whatsapp" and ev[-1]["dados"]["proposta_versao"] == apres.get("versao", 1)
    # 🔴 mutação 5: o telefone só existe na resposta (nem log, nem linha do banco, nem evento)
    assert _o_telefone_em_algum_lugar(m, caplog) == []

    # ⑤ a sessão de OUTRA corretora: a renovação não existe para ela
    outra = {"company_id": m.alfa, "user_id": m.outro_da_alfa}
    for acao in ("envio", "apresentacao"):
        r = m.cliente.post(f"/api/renovacoes/{G4.RENOVACAO}/{acao}", json=outra, headers=H)
        assert r.status_code == 404, (acao, r.text)
    r = m.cliente.get(f"/api/renovacoes/{G4.RENOVACAO}", params=outra, headers=H)
    assert r.status_code == 404
    r = m.cliente.get("/api/renovacoes", params={**outra, "escopo": "todas"}, headers=H)
    assert r.status_code == 200 and r.json()["itens"] == []
    assert len(_eventos(m)) == 2 and _linha(m)["estado"] == "enviada"


def test_o_guarda_do_telefone_do_fio_consegue_ficar_vermelho(fio, caplog):
    """§9.3: o guarda acha o telefone quando ele ESTÁ lá (a linha de controle)."""
    caplog.set_level(logging.DEBUG)
    logging.getLogger("app.api.renovacoes").info("vazou %s", TELEFONE)
    assert _o_telefone_em_algum_lugar(fio, caplog) != []


# =====================================================================================================================
# "Com qual conta" (D-131-04, pedido do Founder): a escolha da tela chega à decisão do Agger — nos dois sentidos
# =====================================================================================================================
import test_spec1310_f3_contas as F3  # noqa: E402
from test_spec129b_o_motor import ambiente  # noqa: E402,F401  (fixture do motor da 129-B)
import test_spec129b_o_motor as TM  # noqa: E402
from app.services.multicalculo import config as CFG  # noqa: E402
from app.services.multicalculo import qual_agger as QA  # noqa: E402


def test_com_qual_conta_responsavel_ou_corretora_chega_ao_qual_agger(ambiente):
    amb = ambiente
    a, b = TM.empresa(amb), TM.empresa(amb)
    for c in (a, b):
        F3.conta_global(amb, c)
    dono_a, dono_b = F3.membro(amb, a), F3.membro(amb, b)
    pa, pb = F3.conta_da_pessoa(amb, a, dono_a), F3.conta_da_pessoa(amb, b, dono_b)

    # o padrão (nenhuma linha de config): o Agger do RESPONSÁVEL
    d = QA.decidir(F3.supa(amb), company_id=a, servico="renovacao", dono_user_id=dono_a)
    assert (d.conta_id, d.regra) == (pa, "renovacao_do_dono")

    # a corretora A escolhe "da corretora": SEMPRE o Agger dela, regra própria, sem fallback e SEM aviso de desvio
    amb.banco.semear("multicalculo_config", {"company_id": a, "config": {"servicos": {"renovacao": {
        "conta": "corretora"}}}})
    d = QA.decidir(F3.supa(amb), company_id=a, servico="renovacao", dono_user_id=dono_a)
    assert (d.conta_id, d.uso, d.regra, d.fallback, d.recusa, d.aviso) == (
        None, "global", "renovacao_conta_da_corretora", False, None, None)
    # … e a corretora B (sem a escolha) segue no Agger do responsável — a config de uma nunca vale para a outra
    d = QA.decidir(F3.supa(amb), company_id=b, servico="renovacao", dono_user_id=dono_b)
    assert (d.conta_id, d.regra) == (pb, "renovacao_do_dono")
    # o recálculo continua na conta de origem (o negócio mora nela), mesmo com "da corretora"
    d = QA.decidir(F3.supa(amb), company_id=a, servico="renovacao", conta_de_origem_id=pa)
    assert (d.conta_id, d.regra) == (pa, "recalculo_mesma_conta")
    # a cotação não lê a chave da renovação
    d = QA.decidir(F3.supa(amb), company_id=a, servico="cotacao", solicitante_user_id=dono_a)
    assert (d.conta_id, d.regra) == (pa, "cotacao_da_pessoa")


def test_com_qual_conta_a_escrita_valida_e_a_leitura_volta_ao_padrao():
    assert CFG.conta_da_renovacao(None) == "responsavel"
    assert CFG.conta_da_renovacao(CFG.mesclar(None, "renovacao")) == "responsavel"
    assert CFG.conta_da_renovacao(CFG.mesclar({"servicos": {"renovacao": {"conta": "corretora"}}}, "renovacao")) \
        == "corretora"
    # fora do formato: a leitura volta ao padrão; a escrita recusa
    assert CFG.conta_da_renovacao(CFG.mesclar({"servicos": {"renovacao": {"conta": "de_alguem"}}}, "renovacao")) \
        == "responsavel"
    assert CFG.erros_da_edicao({"renovacao": {"conta": "corretora"}}) == []
    assert CFG.erros_da_edicao({"renovacao": {"conta": "de_alguem"}})
    assert CFG.erros_da_edicao({"cotacao": {"conta": "corretora"}}), "a cotação não tem 'com qual conta'"


# =====================================================================================================================
# O "N anos" lê o histórico pelo leitor PÚBLICO da fonte (nunca pelo `_get` privado)
# =====================================================================================================================
def test_historico_cru_devolve_a_apolice_e_as_anteriores_e_prova_os_anos():
    from app.comercial.fonte_infocap import FonteInfocap
    from app.services.multicalculo.proposta import anos_de_renovacao

    envelope = G4.historico()(None, None, None)
    fonte = object.__new__(FonteInfocap)
    pedidos = []
    fonte._get = lambda rota, params, **kw: pedidos.append((rota, params)) or envelope
    linhas = fonte.historico_cru(1, G4.NOSNUM)
    assert pedidos == [("/documento", {"codfil": 1, "nosnum": G4.NOSNUM})]
    assert [l["nosnum"] for l in linhas] == [G4.NOSNUM, "800001", "700001"]
    assert anos_de_renovacao(linhas, nosnum=G4.NOSNUM, hoje=G4.HOJE) == 3
    fonte._get = lambda rota, params, **kw: {}
    assert fonte.historico_cru(1, G4.NOSNUM) == []
