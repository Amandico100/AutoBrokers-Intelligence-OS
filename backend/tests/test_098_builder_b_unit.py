"""SPEC-098 · builder B — os seams do FastAPI, a empresa ativa e o ator até o efeito.

⚠️ **Este arquivo NÃO é o guarda da SPEC.** O guarda é
`backend/tests/test_cada_coisa_sabe_de_quem_e.py`, do desenhista, e é ele que o
gate final roda com `--mutar`. Aqui ficam os testes de UNIDADE do builder B:
cada gate do card com a saída colada.

🔴 **Por que um `FastAPI()` mínimo, e não `app.main`.** 📊 Importar `app.main`
leva ≈4 min (ele sobe LangChain, Qdrant, Redis e o grafo). Um teste que custa
4 min não é rodado — e teste que não se roda não guarda nada. Montamos só os
routers que esta unidade toca; a dependency é a MESMA função de produção
(`app.core.auth.require_internal_key`), então o que se prova aqui é o
comportamento do MOTOR, não de uma cópia (CLAUDE.md §9.4).

⛔ NENHUMA mensagem sai: `_entregar_agora` e o Redis são dublados. NENHUM banco
real é tocado: os clientes são dublês.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

CHAVE = "chave-de-teste-098"
ERRADA = "chave-errada-098"


# ===========================================================================
# Dublês
# ===========================================================================


class _Res:
    """⚠️ AGUARDÁVEL de propósito: `get_current_company_id` faz
    `await db.client.table(...).execute()` (o cliente real é async) e
    `vinculo_vigente` passa pelo `_talvez_await`. Um dublê que só servisse a um
    dos dois esconderia metade do caminho."""

    def __init__(self, data):
        self.data = data

    def __await__(self):
        async def _eu():
            return self
        return _eu().__await__()


class _Tabela:
    """Um dublê de PostgREST que RESPONDE ao que foi filtrado.

    ⚠️ Ele guarda os `.eq()` recebidos e devolve linhas só quando TODOS batem.
    Um dublê que devolve sempre a mesma linha não conseguiria ficar vermelho
    quando o código esquecesse o `company_id` — e é justamente isso que os
    testes de tenant precisam poder detectar.
    """

    def __init__(self, linhas, registro):
        self._linhas = linhas
        self._filtros = {}
        self._registro = registro

    def select(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def single(self, *_a, **_k):
        """⚠️ `.single()` do PostgREST devolve UM objeto, não uma lista — e é
        assim que `get_current_company_id` lê a corretora primária."""
        self._single = True
        return self

    def eq(self, coluna, valor):
        self._filtros[coluna] = str(valor)
        return self

    def insert(self, linha):
        self._registro.append(("insert", linha))
        return _Feito(_Res([dict(linha, id="art-1")]))

    def execute(self):
        self._registro.append(("select", dict(self._filtros)))
        casam = [l for l in self._linhas
                 if all(str(l.get(k)) == v for k, v in self._filtros.items())]
        if getattr(self, "_single", False):
            return _Res(casam[0] if casam else None)
        return _Res(casam)


class _Feito:
    def __init__(self, res):
        self._res = res

    def execute(self):
        return self._res


class _Cliente:
    def __init__(self, tabelas, registro=None):
        self._tabelas = tabelas
        self.registro = registro if registro is not None else []

    def table(self, nome):
        return _Tabela(self._tabelas.get(nome, []), self.registro)


class _Db:
    def __init__(self, cliente):
        self.client = cliente


# ===========================================================================
# [G5] · as 14 rotas com `company_id` de fora exigem a chave do BFF
# ===========================================================================

#: 🔴 A tabela é a LISTA DO CARD, escrita à mão. Derivá-la do próprio router
#: (`[r.path for r in router.routes]`) faria o teste concordar com o código:
#: se alguém apagasse a dependency de uma rota, a lista encolheria junto e o
#: teste continuaria verde. É a mutação M9 que isto precisa pegar.
ROTAS = [
    ("sanitization", "POST",   "/api/sanitization/upload"),
    ("sanitization", "GET",    "/api/sanitization/jobs?company_id=X"),
    ("sanitization", "GET",    "/api/sanitization/jobs/j1?company_id=X"),
    ("sanitization", "GET",    "/api/sanitization/download/j1?company_id=X"),
    ("sanitization", "DELETE", "/api/sanitization/jobs/j1?company_id=X"),
    ("agent_config", "GET",    "/api/agent/config/C"),
    ("agent_config", "PUT",    "/api/agent/config/C"),
    ("agent_config", "POST",   "/api/agent/test/C"),
    ("mcp",          "GET",    "/api/mcp/servers"),
    ("mcp",          "GET",    "/api/mcp/servers/s1/tools"),
    ("mcp",          "POST",   "/api/mcp/agent/a1/enable-server"),
    ("mcp",          "DELETE", "/api/mcp/agent/a1/disable-server/m1?company_id=X"),
    ("mcp",          "PATCH",  "/api/mcp/agent/a1/tool/t1/toggle?company_id=X"),
    ("mcp",          "POST",   "/api/mcp/agent/a1/disconnect/m1?company_id=X"),
]


@pytest.fixture(scope="module")
def cliente_http():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    os.environ["ADMIN_API_KEY"] = CHAVE
    os.environ.setdefault("BACKEND_INTERNAL_API_KEY", CHAVE)

    from app.api import agent_config, mcp, sanitization

    app = FastAPI()
    app.include_router(sanitization.router, prefix="/api/sanitization")
    app.include_router(agent_config.router, prefix="/api/agent")
    app.include_router(mcp.router, prefix="/api/mcp")
    return TestClient(app, raise_server_exceptions=False)


def _chamar(cliente, metodo, url, chave=None):
    cabecalhos = {"X-Internal-Key": chave} if chave else {}
    return cliente.request(metodo, url, headers=cabecalhos,
                           json={} if metodo in ("POST", "PUT", "PATCH") else None)


@pytest.mark.parametrize("arquivo,metodo,url", ROTAS)
def test_g5_sem_chave_e_401(cliente_http, arquivo, metodo, url):
    r = _chamar(cliente_http, metodo, url)
    assert r.status_code == 401, f"{arquivo} {metodo} {url} devolveu {r.status_code}"


@pytest.mark.parametrize("arquivo,metodo,url", ROTAS)
def test_g5_chave_errada_e_401(cliente_http, arquivo, metodo, url):
    """🔴 Chave errada = chave nenhuma. Mesmo status, mesma frase."""
    r = _chamar(cliente_http, metodo, url, chave=ERRADA)
    assert r.status_code == 401, f"{arquivo} {metodo} {url} devolveu {r.status_code}"


@pytest.mark.parametrize("arquivo,metodo,url", ROTAS)
def test_g5_chave_certa_chega_no_handler(cliente_http, arquivo, metodo, url):
    """🔴 O CONTROLE. Sem ele, um `Depends` que recusasse TODA request passaria
    nos dois testes acima — e o painel ficaria 401 para sempre com o gate verde.

    ⚠️ Não se afirma 200: o handler dublado bate em banco/gateway que não
    existem aqui. Afirma-se que a PORTA abriu — qualquer coisa que não seja 401.
    """
    r = _chamar(cliente_http, metodo, url, chave=CHAVE)
    assert r.status_code != 401, f"{arquivo} {metodo} {url} recusou a chave VÁLIDA"


# ===========================================================================
# [G6] · a empresa ativa
# ===========================================================================


def _auth():
    from app.core import auth
    return auth


def test_g6_header_com_chave_devolve_a_ativa():
    auth = _auth()
    os.environ["ADMIN_API_KEY"] = CHAVE
    db = _Db(_Cliente({
        "company_members": [{"company_id": "ATIVA", "user_id": "U", "status": "active", "id": 1}],
        "users_v2": [{"id": "U", "status": "active", "company_id": "PRIMARIA"}],
    }))
    r = asyncio.run(auth.get_current_company_id(
        user_id="U", db=db, x_internal_key=CHAVE, x_active_company_id="ATIVA"))
    assert r == "ATIVA"


def test_g6_header_sem_chave_e_ignorado_vale_a_primaria():
    """⚠️ Ignorado, não recusado: sem chave o header é ruído, e o comportamento
    de hoje (a primária) é o seguro."""
    auth = _auth()
    db = _Db(_Cliente({
        "company_members": [{"company_id": "ATIVA", "user_id": "U", "status": "active", "id": 1}],
        "users_v2": [{"id": "U", "status": "active", "company_id": "PRIMARIA"}],
    }))
    r = asyncio.run(auth.get_current_company_id(
        user_id="U", db=db, x_internal_key=None, x_active_company_id="ATIVA"))
    assert r == "PRIMARIA"


def test_g6_chave_errada_tambem_e_ignorada():
    auth = _auth()
    os.environ["ADMIN_API_KEY"] = CHAVE
    db = _Db(_Cliente({
        "company_members": [{"company_id": "ATIVA", "user_id": "U", "status": "active", "id": 1}],
        "users_v2": [{"id": "U", "status": "active", "company_id": "PRIMARIA"}],
    }))
    r = asyncio.run(auth.get_current_company_id(
        user_id="U", db=db, x_internal_key=ERRADA, x_active_company_id="ATIVA"))
    assert r == "PRIMARIA"


def test_g6_sem_vinculo_e_403_nunca_a_primaria():
    """🔴 Cair na primária aqui devolveria dado da corretora ERRADA com 200."""
    from fastapi import HTTPException

    auth = _auth()
    os.environ["ADMIN_API_KEY"] = CHAVE
    db = _Db(_Cliente({
        "company_members": [],
        "users_v2": [{"id": "U", "status": "active", "company_id": "PRIMARIA"}],
    }))
    with pytest.raises(HTTPException) as e:
        asyncio.run(auth.get_current_company_id(
            user_id="U", db=db, x_internal_key=CHAVE, x_active_company_id="OUTRA"))
    assert e.value.status_code == 403


def test_g6_vinculo_inativo_e_403():
    from fastapi import HTTPException

    auth = _auth()
    os.environ["ADMIN_API_KEY"] = CHAVE
    db = _Db(_Cliente({
        "company_members": [{"company_id": "ATIVA", "user_id": "U", "status": "inactive", "id": 1}],
        "users_v2": [{"id": "U", "status": "active", "company_id": "PRIMARIA"}],
    }))
    with pytest.raises(HTTPException) as e:
        asyncio.run(auth.get_current_company_id(
            user_id="U", db=db, x_internal_key=CHAVE, x_active_company_id="ATIVA"))
    assert e.value.status_code == 403


def test_g6_conta_suspensa_e_403_mesmo_com_vinculo_ativo():
    """As duas metades da R9: o vínculo vive, a CONTA foi suspensa."""
    from fastapi import HTTPException

    auth = _auth()
    os.environ["ADMIN_API_KEY"] = CHAVE
    db = _Db(_Cliente({
        "company_members": [{"company_id": "ATIVA", "user_id": "U", "status": "active", "id": 1}],
        "users_v2": [{"id": "U", "status": "suspended", "company_id": "PRIMARIA"}],
    }))
    with pytest.raises(HTTPException) as e:
        asyncio.run(auth.get_current_company_id(
            user_id="U", db=db, x_internal_key=CHAVE, x_active_company_id="ATIVA"))
    assert e.value.status_code == 403


def test_g6_banco_explode_e_500_nunca_a_primaria():
    from fastapi import HTTPException

    auth = _auth()
    os.environ["ADMIN_API_KEY"] = CHAVE

    class _Explode:
        def table(self, _nome):
            raise RuntimeError("supabase mudo")

    with pytest.raises(HTTPException) as e:
        asyncio.run(auth.get_current_company_id(
            user_id="U", db=_Db(_Explode()), x_internal_key=CHAVE,
            x_active_company_id="ATIVA"))
    assert e.value.status_code == 500


def test_g6_vinculo_vigente_levanta_em_erro_de_banco():
    """🔴 `vinculo_vigente` NUNCA devolve True nem False por erro — LEVANTA."""
    auth = _auth()

    class _Explode:
        def table(self, _nome):
            raise RuntimeError("supabase mudo")

    with pytest.raises(RuntimeError):
        asyncio.run(auth.vinculo_vigente(_Db(_Explode()), "C", "U"))


# ===========================================================================
# [G7] · o ator e a conversa viajam
# ===========================================================================


def _linha_base(**extra):
    base = dict(company_id="C", workflow_key="w", outcome_type="o",
                outcome_title="t", source_type="chat", source_id=None,
                conversation_id=None, runtime_kind="k", status="queued",
                risk_level="low", idempotency_key="idem-1", input_payload={})
    base.update(extra)
    return base


def _db_de_run(registro):
    cli = _Cliente({"work_runs": []}, registro)
    return cli


def test_g7_run_grava_o_ator_quando_o_chamador_o_conhece():
    from app.services.work.runs import criar_registro_sem_fila

    registro = []
    asyncio.run(criar_registro_sem_fila(_db_de_run(registro),
                                        requester_user_id="U1",
                                        requester_agent_id="A1", **_linha_base()))
    inserts = [l for op, l in registro if op == "insert"]
    assert inserts and inserts[0]["requester_user_id"] == "U1"
    assert inserts[0]["requester_agent_id"] == "A1"


def test_g7_run_sem_ator_nao_inventa_a_chave():
    """⚠️ O CONTROLE: a chave só entra quando tem valor."""
    from app.services.work.runs import criar_registro_sem_fila

    registro = []
    asyncio.run(criar_registro_sem_fila(_db_de_run(registro), **_linha_base()))
    inserts = [l for op, l in registro if op == "insert"]
    assert "requester_user_id" not in inserts[0]
    assert "requester_agent_id" not in inserts[0]


@pytest.mark.parametrize("vazio", [None, "", "  ", "None"])
def test_g7_run_sem_company_levanta(vazio):
    from app.services.work.runs import criar_registro_sem_fila

    with pytest.raises(ValueError):
        asyncio.run(criar_registro_sem_fila(_db_de_run([]),
                                            **_linha_base(company_id=vazio)))


def test_g7_peca_herda_a_conversa_do_run_da_MESMA_corretora():
    from app.services.artifacts.service import ArtifactService

    registro = []
    cli = _Cliente({"work_runs": [{"id": "R1", "company_id": "C", "conversation_id": "CONV"}]},
                   registro)
    svc = ArtifactService.__new__(ArtifactService)
    svc.db = cli
    assert svc._conversa_da_peca("C", "R1", None) == "CONV"


def test_g7_peca_nao_herda_conversa_de_run_de_OUTRA_corretora():
    """🔴 O CONTROLE do tenant. Sem o `.eq(company_id)`, isto devolveria `CONV`
    — e a FK COMPOSTA recusaria o INSERT da peça inteira."""
    from app.services.artifacts.service import ArtifactService

    cli = _Cliente({"work_runs": [{"id": "R1", "company_id": "OUTRA", "conversation_id": "CONV"}]})
    svc = ArtifactService.__new__(ArtifactService)
    svc.db = cli
    assert svc._conversa_da_peca("C", "R1", None) is None


def test_g7_aprovacao_herda_a_conversa_do_run():
    from app.services.work.approvals import WorkApprovalService

    cli = _Cliente({"work_runs": [{"id": "R1", "company_id": "C", "conversation_id": "CONV"}]})
    svc = WorkApprovalService.__new__(WorkApprovalService)
    svc.db = cli
    assert svc._conversa_do_run("C", "R1") == "CONV"
    assert svc._conversa_do_run("OUTRA", "R1") is None   # o controle do tenant


# ===========================================================================
# [G8] · o PAR do envio — a porta revalida o ator no instante do efeito
# ===========================================================================


@pytest.fixture
def porta(monkeypatch):
    """Monta a porta com TUDO dublado: nada sai, nada toca Redis nem banco."""
    from app.services import platform_outbound as po

    entregas = []
    fila = []
    eventos = []

    async def _entregar(company_id, phone, text, kind, summary):
        entregas.append((company_id, phone, kind))
        return {"ok": True, "queued": False, "reason": None}

    async def _agente_ligado(_cid):
        return True

    async def _enfileirar(company_id, phone, text, kind, summary, *, espera_s,
                          tentativas=0, adiamentos=0, actor_user_id=None,
                          work_run_id=None):
        fila.append({"phone": phone, "kind": kind, "actor_user_id": actor_user_id,
                     "work_run_id": work_run_id})
        return True

    async def _recusa(company_id, actor_user_id, kind, summary, *,
                      work_run_id=None, phone=""):
        # ⚠️ CONSERTO 2: o dublê carrega o `work_run_id` e o telefone porque é
        #    a PRESENÇA do run que escolhe o destino do registro.
        eventos.append({"event_type": "envio.recusado", "actor_id": actor_user_id,
                        "kind": kind, "work_run_id": work_run_id, "phone": phone})

    monkeypatch.setattr(po, "_entregar_agora", _entregar)
    monkeypatch.setattr(po, "_enfileirar", _enfileirar)
    monkeypatch.setattr(po, "_registrar_envio_recusado", _recusa)
    import app.services.atlas.attendance_capture as ac
    monkeypatch.setattr(ac, "attendance_agent_active", _agente_ligado, raising=False)
    return po, entregas, fila, eventos


def _vinculo(po, monkeypatch, resposta):
    async def _v(_cid, _uid):
        return resposta
    monkeypatch.setattr(po, "_vinculo_do_ator_vigente", _v)


def test_g8_vinculo_vigente_entrega_uma_vez(porta, monkeypatch):
    po, entregas, _fila, eventos = porta
    _vinculo(po, monkeypatch, True)
    r = asyncio.run(po.send_to_client_guarded("C", "5511999999999", "oi",
                                              temperatura=po.QUENTE,
                                              actor_user_id="U1"))
    assert r["ok"] is True
    assert len(entregas) == 1
    assert eventos == []


def test_g8_vinculo_revogado_zero_entregas_e_evento(porta, monkeypatch):
    po, entregas, _fila, eventos = porta
    _vinculo(po, monkeypatch, False)
    r = asyncio.run(po.send_to_client_guarded("C", "5511999999999", "oi",
                                              temperatura=po.QUENTE,
                                              actor_user_id="U1"))
    assert r["status"] == "recusado"
    assert r["motivo"] == "o vínculo de quem pediu não está mais vigente"
    assert entregas == []
    assert len(eventos) == 1 and eventos[0]["event_type"] == "envio.recusado"
    # 🔴 CONSERTO 2: sem run, o registro NÃO pode tentar `work_events`
    #    (`work_run_id` é NOT NULL) — e o telefone chega para achar a ficha.
    assert eventos[0]["work_run_id"] is None
    assert eventos[0]["phone"] == "5511999999999"


def test_g8_sem_ator_e_o_comportamento_de_hoje(porta, monkeypatch):
    """🔴 A LINHA DE CONTROLE (CLAUDE.md §9.2). O revalidador é dublado para
    RECUSAR — e mesmo assim a mensagem sai, porque sem ator ele não é chamado.
    Sem esta linha, um "recusou" acima poderia ser mérito de qualquer coisa."""
    po, entregas, _fila, eventos = porta
    _vinculo(po, monkeypatch, False)
    r = asyncio.run(po.send_to_client_guarded("C", "5511999999999", "oi",
                                              temperatura=po.QUENTE))
    assert r["ok"] is True
    assert len(entregas) == 1
    assert eventos == []


def test_g8_a_fila_carrega_o_ator():
    """A entrada gravada leva o ator — e SÓ o id (nada de PII no Redis)."""
    from app.services import platform_outbound as po

    gravadas = []

    class _R:
        async def rpush(self, _k, raw):
            gravadas.append(raw)

    async def _redis():
        return _R()

    import app.core.redis as redismod
    original = redismod.get_async_redis_client
    redismod.get_async_redis_client = _redis
    try:
        assert asyncio.run(po._enfileirar("C", "5511999999999", "oi", "other", "",
                                          espera_s=1, actor_user_id="U1")) is True
        assert asyncio.run(po._enfileirar("C", "5511999999999", "oi", "other", "",
                                          espera_s=1)) is True
    finally:
        redismod.get_async_redis_client = original

    import json
    com_ator = json.loads(gravadas[0])
    sem_ator = json.loads(gravadas[1])
    assert com_ator["actor_user_id"] == "U1"
    # 🔴 O CONTROLE: sem ator, a chave NÃO existe — é assim que a entrada
    #    ANTIGA da fila cai em "sem ator" por construção (compatibilidade).
    assert "actor_user_id" not in sem_ator


def test_g8_item_da_fila_com_ator_revogado_e_descartado(porta, monkeypatch):
    """O drenador re-chama a porta; quem recusa é a porta, não o drenador."""
    po, entregas, _fila, eventos = porta
    _vinculo(po, monkeypatch, False)
    r = asyncio.run(po.send_to_client_guarded(
        "C", "5511999999999", "oi", "other", "", temperatura=po.QUENTE,
        actor_user_id="U1", tentativas=3, adiamentos=1))
    assert entregas == []
    assert r["status"] == "recusado"


# ===========================================================================
# [K] · a migration tem APPLY / VERIFY / ROLLBACK e é idempotente no texto
# ===========================================================================

MIGRATIONS = [
    "20260906_01_spec098_de_quem_e.sql",
    "20260906_02_spec098_indice_cobre_a_fk.sql",
]


@pytest.mark.parametrize("nome", MIGRATIONS)
def test_k_migration_tem_as_tres_secoes(nome):
    p = Path(__file__).resolve().parents[1] / "supabase" / "migrations" / nome
    texto = p.read_text(encoding="utf-8")
    for secao in ("-- APPLY", "-- VERIFY", "-- ROLLBACK"):
        assert secao in texto, f"{nome} sem {secao}"


@pytest.mark.parametrize("nome", MIGRATIONS)
def test_k_migration_e_idempotente(nome):
    """Todo DDL de criação do APPLY é guardado: `IF NOT EXISTS` ou `pg_constraint`.

    ⚠️ Só o APPLY entra na régua: VERIFY e ROLLBACK moram em comentário e não
    rodam. Medir o arquivo inteiro faria o `create index` do ROLLBACK reprovar
    uma migration correta.
    """
    p = Path(__file__).resolve().parents[1] / "supabase" / "migrations" / nome
    aplica = p.read_text(encoding="utf-8").upper().split("-- VERIFY")[0]
    assert aplica.count("ADD COLUMN") == aplica.count("ADD COLUMN IF NOT EXISTS"),         f"{nome}: ADD COLUMN sem IF NOT EXISTS"
    assert aplica.count("CREATE INDEX") == aplica.count("CREATE INDEX IF NOT EXISTS"),         f"{nome}: CREATE INDEX sem IF NOT EXISTS"
    # ADD CONSTRAINT não aceita IF NOT EXISTS: tem de vir guardado por pg_constraint
    if "ADD CONSTRAINT" in aplica:
        assert "PG_CONSTRAINT" in aplica, f"{nome}: ADD CONSTRAINT desprotegido"
    # 🔴 O CONTROLE — a régua CONSEGUE ficar vermelha. Sem esta prova ela é
    #    carimbo: um arquivo com `ADD COLUMN` cru tem de reprovar (CLAUDE.md §9.3).
    if "ADD COLUMN" in aplica:
        estragado = aplica.replace("ADD COLUMN IF NOT EXISTS", "ADD COLUMN")
        assert estragado.count("ADD COLUMN") != estragado.count("ADD COLUMN IF NOT EXISTS")
    if "CREATE INDEX" in aplica:
        estragado = aplica.replace("CREATE INDEX IF NOT EXISTS", "CREATE INDEX")
        assert estragado.count("CREATE INDEX") != estragado.count("CREATE INDEX IF NOT EXISTS")


# ===========================================================================
# CONSERTO 1 · B1 — o varredor do ROUTER (não a lista escrita à mão)
# ===========================================================================
#
# 🔴 O red team achou 4 rotas de `/api/mcp` abertas — uma delas um DELETE
# destrutivo anônimo — e o `ROTAS` acima não as viu, porque ele enumera as rotas
# que FORAM CONSERTADAS. Um guarda que lista o que já foi feito não consegue
# achar o que falta: é carimbo, não régua (CLAUDE.md §9.5).
#
# ⚠️ A lista à mão CONTINUA (é ela que pega a mutação M9, em que uma dependency
# some e uma lista derivada encolheria junto). O varredor é o COMPLEMENTO: ele
# mede o TODO e obriga a exceção a ser escrita ao lado da rota.

#: A única rota do router que fica sem `Depends`, com a razão ao lado.
#: 🔴 Uma rota entra aqui por decisão escrita, nunca por esquecimento.
ABERTAS_COM_RAZAO = {
    ("/oauth/callback/{provider}", "GET"):
        "quem chama é o NAVEGADOR redirecionado pelo Google/GitHub/Slack: não "
        "passa pela proxy e não pode carregar a chave. O guarda dela é o `state` "
        "assinado com HMAC (`_encode_state`), e o convite que gera esse state "
        "(`GET /oauth/url/...`) exige a chave E confere o agente.",
}


def _rotas_do_router():
    from app.api import mcp as mod

    saida = []
    for rota in mod.router.routes:
        for metodo in sorted(getattr(rota, "methods", set()) - {"HEAD", "OPTIONS"}):
            nomes = {getattr(getattr(d, "dependency", None), "__name__", "")
                     for d in getattr(rota, "dependencies", [])}
            saida.append((rota.path, metodo, "require_internal_key" in nomes))
    return saida


def test_g5bis_varredura_do_router_mcp__toda_rota_guardada_ou_declarada():
    """Itera `mcp.router.routes` e exige a chave em TODAS — menos as declaradas.

    📊 Red team 06/09/2026 (`scratchpad/rt2_api.py`): `GET /agent/{id}/tools`,
    `GET /agent/{id}/connections`, `DELETE /connections/{id}` e
    `GET /oauth/url/...` respondiam **200 sem chave nenhuma**, com `/servers`
    (guardada) devolvendo 401 na mesma bateria como linha de controle.
    """
    todas = _rotas_do_router()
    abertas = [(p, m) for p, m, guardada in todas if not guardada]
    sem_razao = [x for x in abertas if x not in ABERTAS_COM_RAZAO]
    assert not sem_razao, (
        "rotas de /api/mcp sem `Depends(require_internal_key)` e sem razão escrita: "
        f"{sem_razao}")
    # 🔴 O CONTROLE: o varredor CONSEGUE ler o router. Se ele nunca vê rota
    #    nenhuma, ele está lendo o vazio e ficaria verde para sempre.
    assert len(todas) >= 11, f"o varredor enxergou só {len(todas)} rotas"
    assert ABERTAS_COM_RAZAO, "sem exceção declarada, ele não prova que sabe distinguir"


@pytest.mark.parametrize("metodo,url", [
    ("GET", "/api/mcp/agent/a1/tools?company_id=X"),
    ("GET", "/api/mcp/agent/a1/connections?company_id=X"),
    ("GET", "/api/mcp/oauth/url/google?agent_id=a1&mcp_server_id=m1&company_id=X"),
    ("GET", "/api/mcp/oauth/providers"),
    ("DELETE", "/api/mcp/connections/cx1?company_id=X"),
])
def test_g5bis_as_rotas_abertas_do_red_team_agora_sao_401(cliente_http, metodo, url):
    """A reprodução do red team, com a mesma bateria — agora 401."""
    assert _chamar(cliente_http, metodo, url).status_code == 401


def test_g5bis_agente_de_outra_corretora_com_chave_boa_e_403(cliente_http, monkeypatch):
    """Chave boa não é permissão para o agente alheio: a corretora ainda decide.

    🔴 Era o coração do B1: a proxy resolvia `company_id = A` (verdadeiro),
    carimbava a chave, e o backend não olhava a corretora nessas rotas — então
    saía a lista de contas conectadas da corretora B.
    """
    from app.api import mcp as mod

    vistos = []

    async def _pertence(agent_id, company_id):
        vistos.append((agent_id, company_id))
        return agent_id == "a-da-alfa" and company_id == "co-alfa"

    monkeypatch.setattr(mod, "_validate_agent_belongs_to_company", _pertence)

    r = _chamar(cliente_http, "GET",
                "/api/mcp/agent/a-da-beta/connections?company_id=co-alfa", chave=CHAVE)
    assert r.status_code == 403, r.text
    assert vistos, "a rota nem chegou a perguntar de quem é o agente"

    # 🔴 O PAR: o agente da PRÓPRIA corretora continua passando — senão a cerca
    #    teria fechado a porta de quem podia entrar.
    class _Oauth:
        @staticmethod
        async def get_agent_connections(_agent_id):
            return []

    import app.services.mcp_oauth_service as oauth_mod
    monkeypatch.setattr(oauth_mod, "get_mcp_oauth_service", lambda: _Oauth())
    ok = _chamar(cliente_http, "GET",
                 "/api/mcp/agent/a-da-alfa/connections?company_id=co-alfa", chave=CHAVE)
    assert ok.status_code == 200, ok.text


# ===========================================================================
# CONSERTO 1 · B4 — a revalidação do ator é ALCANÇADA por um chamador real
# ===========================================================================

def test_r9_o_envio_humano_do_painel_revalida_o_ator(monkeypatch):
    """📊 Red team: `send_to_client_guarded` tinha 4 chamadores e **0** com ator.

    O envio que TEM humano por trás é `POST /api/webhook/send-message` — a
    atendente respondendo pelo painel — e ele nunca passou por aquela função.
    A pergunta foi extraída para `platform_outbound.ator_ainda_pode` (porta
    ÚNICA, CLAUDE.md §5) e o BFF passa a mandar `X-Actor-User-Id`.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import app.api.webhook as w
    import app.services.platform_outbound as po
    from app.core.auth import require_master_admin

    enviadas = []
    eventos = []
    vigente = {"resposta": False}

    async def _vinculo(_company_id, _ator):
        return vigente["resposta"]

    async def _registrar(company_id, _ator, kind, _summary, *,
                         work_run_id=None, phone=""):
        eventos.append({"company_id": company_id, "kind": kind,
                        "work_run_id": work_run_id})

    def _mandou(*a, **_k):
        enviadas.append(a)
        return True

    monkeypatch.setattr(po, "_vinculo_do_ator_vigente", _vinculo)
    monkeypatch.setattr(po, "_registrar_envio_recusado", _registrar)
    monkeypatch.setattr(w.integration_service, "get_whatsapp_integration",
                        lambda *_a, **_k: {"instance": "duble"})
    monkeypatch.setattr(w.whatsapp_service, "send_message", _mandou)

    app = FastAPI()
    app.include_router(w.router)
    app.dependency_overrides[require_master_admin] = lambda: True
    cliente = TestClient(app, raise_server_exceptions=False)

    corpo = {"session_id": "whatsapp:5511900000001:co-alfa:default",
             "phone": "5511900000001", "message": "Bom dia, tudo certo por aqui."}

    # 🔴 Vínculo REVOGADO: 0 entregas, e a recusa fica registrada.
    r = cliente.post("/api/webhook/send-message", json=corpo,
                     headers={"X-Actor-User-Id": "u-demitido"})
    assert r.status_code == 403, r.text
    assert enviadas == [], "a mensagem SAIU com o vínculo revogado"
    assert len(eventos) == 1 and eventos[0]["company_id"] == "co-alfa"
    # ⚠️ O painel não tem run: o registro vai para a ficha da conversa.
    assert eventos[0]["work_run_id"] is None

    # 🔴 O PAR: com o vínculo vigente, 1 entrega. Sem ele, um endpoint que
    #    recusasse tudo passaria no teste acima e mataria o atendimento.
    vigente["resposta"] = True
    r2 = cliente.post("/api/webhook/send-message", json=corpo,
                      headers={"X-Actor-User-Id": "u-empregado"})
    assert r2.status_code == 200, r2.text
    assert len(enviadas) == 1 and len(eventos) == 1

    # 🔴 O CONTROLE: SEM ator (job de sistema) o comportamento é o de hoje —
    #    entrega, sem perguntar nada. É o que dá sentido aos dois de cima.
    vigente["resposta"] = False
    r3 = cliente.post("/api/webhook/send-message", json=corpo)
    assert r3.status_code == 200 and len(enviadas) == 2 and len(eventos) == 1


def test_r9_o_work_event_da_recusa_usa_a_coluna_que_existe():
    """📊 Guarda [J3] do desenhista: a coluna é `payload_redacted`.

    `work_events` em `tests/fixtures/schema_vivo.json` não tem `payload` — o
    INSERT falharia com 42703 e, como a função é best-effort (`except` mudo), a
    recusa sumiria em silêncio: em produção a mensagem barrada não deixaria
    rastro nenhum.
    """
    import inspect
    import json

    import app.services.platform_outbound as po

    esquema = json.loads(
        (Path(__file__).resolve().parent / "fixtures" / "schema_vivo.json")
        .read_text(encoding="utf-8"))
    colunas = set(((esquema.get("tabelas") or {}).get("work_events") or {}).keys())
    assert "payload_redacted" in colunas and "payload" not in colunas

    fonte = inspect.getsource(po._registrar_envio_recusado)
    escritas = {c for c in ("payload_redacted", "event_type", "actor_type", "actor_id",
                            "severity", "message_human", "company_id")
                if '"%s":' % c in fonte}
    assert "payload_redacted" in escritas and escritas <= colunas
    # 🔴 O PAR: a coluna do defeito NÃO pode voltar.
    assert '"payload":' not in fonte, "voltou a gravar na coluna fantasma `payload`"



# ===========================================================================
# CONSERTO 2 · o registro da recusa tem DOIS destinos — e quem escolhe é o run
# ===========================================================================

class _TabelaDaFicha:
    """Um PostgREST mínimo que sabe `in_`, `order` e `update` — e que RECUSA
    `work_events` sem `work_run_id`.

    🔴 📊 `information_schema.columns` (06/09/2026): `work_events.work_run_id`
    é NOT NULL. Um dublê que aceitasse esse INSERT deixaria verde exatamente o
    defeito que o canário vivo mediu (`recusa não pôde ser registrada:
    APIError`). Aqui ele responde 23502, como o banco.
    """

    def __init__(self, nome, mundo, registro):
        self.nome, self.mundo, self.registro = nome, mundo, registro
        self.filtros, self.dentro, self.op, self.carga = {}, None, "select", None

    def select(self, *_a, **_k):
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def eq(self, coluna, valor):
        self.filtros[coluna] = str(valor)
        return self

    def in_(self, coluna, valores):
        self.dentro = (coluna, [str(v) for v in valores])
        return self

    def insert(self, carga):
        self.op, self.carga = "insert", carga
        return self

    def update(self, carga):
        self.op, self.carga = "update", carga
        return self

    def _casa(self, linha):
        if any(str(linha.get(k)) != v for k, v in self.filtros.items()):
            return False
        if self.dentro and str(linha.get(self.dentro[0])) not in self.dentro[1]:
            return False
        return True

    def execute(self):
        linhas = self.mundo.setdefault(self.nome, [])
        self.registro.append({"tabela": self.nome, "op": self.op,
                              "carga": self.carga, "filtros": dict(self.filtros)})
        if self.op == "insert":
            if self.nome == "work_events" and not (self.carga or {}).get("work_run_id"):
                raise RuntimeError('23502: null value in column '
                                   '"work_events.work_run_id" violates not-null')
            linhas.append(dict(self.carga))
            return _Res([dict(self.carga)])
        if self.op == "update":
            tocadas = [l for l in linhas if self._casa(l)]
            for l in tocadas:
                l.update(self.carga or {})
            return _Res([dict(l) for l in tocadas])
        return _Res([dict(l) for l in linhas if self._casa(l)])


def _banco_da_ficha(monkeypatch, conversas):
    mundo = {"conversations": conversas, "work_events": []}
    registro = []

    class _Cli:
        def table(self, nome):
            return _TabelaDaFicha(nome, mundo, registro)

    class _DbSinc:
        client = _Cli()

    import app.core.database as dbmod
    monkeypatch.setattr(dbmod, "get_supabase_client", lambda: _DbSinc())
    return mundo, registro


def test_r9_sem_run_a_recusa_vai_para_a_ficha_da_conversa(monkeypatch):
    """🔴 O defeito que o canário vivo pegou em 06/09/2026.

    `work_events.work_run_id` é NOT NULL (📊 information_schema) e o envio do
    painel não tem run: o INSERT levantava `APIError` dentro do `except` mudo e
    a recusa **não ficava registrada em lugar nenhum**. O destino que sempre
    existe é a ficha da conversa — o mesmo precedente da 097.1
    (`atendimento/acompanhamento.py::_registrar`).
    """
    import app.services.platform_outbound as po

    conversa = {"id": "cv-1", "company_id": "co-alfa",
                # 📊 gravado SEM o nono dígito de propósito: `variantes_br`
                #    (SPEC-097) é o que faz o telefone com 9 casar com este.
                "user_phone": "551100000001", "ficha_atendimento": {}}
    mundo, registro = _banco_da_ficha(monkeypatch, [conversa])

    asyncio.run(po._registrar_envio_recusado("co-alfa", "u-demitido", "other", "x",
                                             phone="5511900000001"))

    assert mundo["work_events"] == [], "tentou `work_events` sem run (NOT NULL)"
    anotadas = conversa["ficha_atendimento"].get("envios_recusados") or []
    assert len(anotadas) == 1
    assert "vínculo" in anotadas[0]["motivo"] and anotadas[0]["ator"] == "u-demitido"
    # ⛔ §7: nem telefone nem texto da mensagem na ficha.
    assert "5511900000001" not in json.dumps(anotadas[0])
    # 🔴 §7: o UPDATE é filtrado por `company_id` — nunca só por `id`.
    upd = [w for w in registro if w["op"] == "update"]
    assert len(upd) == 1 and upd[0]["filtros"].get("company_id") == "co-alfa"


def test_r9_com_run_a_recusa_e_um_work_event(monkeypatch):
    """🔴 O PAR. Com run, o Work Event é possível — e é o registro certo.

    Sem este lado, "0 eventos" acima poderia ser mérito de uma função quebrada.
    """
    import app.services.platform_outbound as po

    conversa = {"id": "cv-1", "company_id": "co-alfa",
                "user_phone": "5511900000001", "ficha_atendimento": {}}
    mundo, _registro = _banco_da_ficha(monkeypatch, [conversa])

    asyncio.run(po._registrar_envio_recusado(
        "co-alfa", "u-demitido", "other", "x",
        work_run_id="99999999-9999-4999-8999-999999999999",
        phone="5511900000001"))

    assert len(mundo["work_events"]) == 1
    linha = mundo["work_events"][0]
    assert linha["work_run_id"] == "99999999-9999-4999-8999-999999999999"
    assert linha["company_id"] == "co-alfa" and linha["event_type"] == "envio.recusado"
    assert "vínculo" in linha["message_human"]
    # ⛔ `id` é GENERATED ALWAYS AS IDENTITY (📊 information_schema): mandar
    #    valor nele é erro 428C9.
    assert "id" not in linha
    # ⚠️ Com run, a ficha não é usada: o registro tem UM destino por vez.
    assert not (conversa["ficha_atendimento"].get("envios_recusados") or [])


def test_r9_sem_conversa_o_registro_e_um_warning_sem_pii(monkeypatch, caplog):
    """O envio a quem nunca falou com a corretora: não há ficha, e não se
    inventa uma. 📊 É o caminho que o canário 098 mede (telefone que não é de
    ninguém) — e o aviso não pode carregar o número."""
    import logging

    import app.services.platform_outbound as po

    mundo, _registro = _banco_da_ficha(monkeypatch, [])
    with caplog.at_level(logging.WARNING):
        asyncio.run(po._registrar_envio_recusado("co-alfa", "u-demitido", "other", "x",
                                                 phone="5500000000098"))
    assert mundo["work_events"] == []
    avisos = [r.getMessage() for r in caplog.records
              if "sem conversa para o telefone" in r.getMessage()]
    assert len(avisos) == 1 and "5500000000098" not in avisos[0]
