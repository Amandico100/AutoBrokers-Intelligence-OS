# -*- coding: utf-8 -*-
"""SPEC-132-C · C2 — O ATALHO: o número do AutoBrokers responde ao corretor VERIFICADO com o MESMO chat principal.

O FIO deste arquivo (dublê SÓ na borda — banco em memória, Redis, Storage, o `send_message` do WhatsApp, o grafo do
modelo; a rede fica FECHADA):

    POST /api/v1/webhook/evolution-go/{token}   ROTA REAL (`app.api.webhook.router`), token pelo hash REAL
      → o desvio do assistente (purpose='assistente' + empresa da plataforma, ANTES do QCM e do observer)
      → atalho.entrada.turno_do_atalho REAL (filtros, ATIVAR → verificacao REAL, membros verificados, escolha, teto)
      → atalho.turno.rodar REAL (agente CORE, conversa do canal, a pergunta como o BFF grava, mídia → Storage)
      → POST /chat/stream REAL (`app.api.chat.router`, modo painel pela X-Internal-Key; o grafo é o dublê
        `stream_agent_eventos` do arreio da SPEC-096 — `test_o_chat_fala_tipado`, REUSO, não cópia)
      → atalho.envio REAL (markdown → WhatsApp, corte ≤ 3.500) → whatsapp_service.send_message (DUBLÊ: captura)

As mutações (SPEC-132-C §6) — `python tests/test_spec132c_o_atalho.py --mutar` aplica cada uma POR CÓPIA, roda os
testes que a guardam, exige VERMELHO e restaura:
    M1  número NÃO verificado é atendido ............. entrada: o silêncio vira resposta
    M4  a mensagem do QCM cai no assistente .......... webhook + entrada: o portão aceita purpose 'observer'
    M5  fromMe gera resposta ......................... entrada: o filtro deixa passar fromMe
    M5b o anti-laço desligado ........................ entrada: `numero_do_produto` sempre False
    M6  membro de 2 corretoras sem a pergunta ........ entrada: sempre a 1ª corretora

⛔ Dados fictícios: nomes inventados ("Corretora Alfa"), telefones 💭 inventados com DDD válido (a régua do produto
recusa DDD 00), uuids sintéticos. Nenhum nome de corretora real (CLAUDE.md §13.9).
Rodar: cd backend && .venv/Scripts/python.exe -m pytest tests/test_spec132c_o_atalho.py -q -p no:cacheprovider
"""
from __future__ import annotations

import base64
import copy
import importlib
import json
import os
import shutil
import subprocess
import sys
import types
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ⚠️ importados ANTES dos dublês do arreio (que trocam `app.services.langchain_service` e companhia em sys.modules)
import app.api.chat  # noqa: E402,F401
import app.api.webhook  # noqa: E402,F401
import app.services.chat_anexos  # noqa: E402,F401
from app.services.atalho import entrada as E  # noqa: E402
from app.services.atalho import envio as ENV  # noqa: E402
from app.services.atalho import turno as T  # noqa: E402
from app.services.atalho import verificacao as V  # noqa: E402

FIXTURE = BACKEND / "tests" / "fixtures" / "canal_evolution_go_oi.json"

# --- o mundo (uuid4 sintéticos: o `ChatRequest` exige UUID4) ---------------------------------------------------------
CANAL = "0c0c0c0c-0000-4000-8000-0000000000c0"
ALFA = "aaaaaaaa-0000-4000-8000-0000000000a1"
BETA = "bbbbbbbb-0000-4000-8000-0000000000b1"
U1 = "11111111-0000-4000-8000-000000000001"     # Alfa
U2 = "22222222-0000-4000-8000-000000000002"     # Alfa E Beta (a mesma pessoa nas duas)
U3 = "33333333-0000-4000-8000-000000000003"     # Beta, número DECLARADO e confirmado, ainda NÃO verificado (vai ATIVAR)
U4 = "44444444-0000-4000-8000-000000000004"     # Beta
U5 = "55555555-0000-4000-8000-000000000005"     # Alfa, verificou o número que é a LINHA da corretora (anti-laço)
U6 = "66666666-0000-4000-8000-000000000006"     # Alfa, número CONFIRMADO por clique mas NÃO verificado
AG_ALFA_CORE = "a0a0a0a0-0000-4000-8000-0000000000a2"
AG_ALFA_ATEND = "a0a0a0a0-0000-4000-8000-0000000000a3"
AG_BETA_CORE = "b0b0b0b0-0000-4000-8000-0000000000b2"
CEL_1 = "+5511912340001"      # 💭 inventado
CEL_2 = "+5511912340002"
CEL_3 = "+5521912340003"
CEL_4 = "+5521912340004"
CEL_LINHA_ALFA = "+5511933330000"   # a linha de atendimento da Alfa (pareada) — e verificada por U5
CEL_6 = "+5511912340006"
CEL_ESTRANHO = "+5511912349999"
ASSISTENTE = "5511955554444"
QCM = "5511966665555"
TOKEN_ASSISTENTE = "tok-assistente-132c-" + "a" * 40
TOKEN_QCM = "tok-qcm-132c-" + "q" * 40
TOKEN_ALFA = "tok-alfa-132c-" + "z" * 40
TOKEN_FALSO_ASSISTENTE = "tok-falso-132c-" + "f" * 40
#: uma chave Fernet de TESTE (o cofre cifra a fala que espera a escolha da corretora — `atalho.estado`)
CHAVE_DO_COFRE = "dGVzdGUtZG8tY29mcmUtMTMyYy1hdGFsaG8tMzJieXQ="
TABELA_MD = ("**Cotação Rápida — 3 seguradoras**\n\n"
             "| Seguradora | Parcelas | À vista |\n|---|---|---|\n"
             "| Seguradora Um | 12x R$ 99,90 | R$ 1.100,00 |\n| Seguradora Dois | 10x R$ 120,00 | R$ 1.150,00 |\n\n"
             "Veja a [apresentação](https://app.exemplo.test/r/abc123).")


# =====================================================================================================================
# o banco em memória: PostgREST síncrono E aguardável (o atalho usa o cliente síncrono; o /chat/stream, o assíncrono)
# =====================================================================================================================
class _Resp:
    def __init__(self, data):
        self.data = data

    def __await__(self):
        if False:  # pragma: no cover
            yield
        return self


def _agora_iso():
    return datetime.now(timezone.utc).isoformat()


class _Consulta:
    def __init__(self, banco, tabela):
        self.banco, self.tabela = banco, tabela
        self.filtros, self.op, self.carga, self.lim, self.ordem, self._negar = [], "select", None, None, None, False

    @property
    def not_(self):
        self._negar = True
        return self

    def _f(self, teste):
        negar, self._negar = self._negar, False
        self.filtros.append((lambda l: not teste(l)) if negar else teste)
        return self

    @staticmethod
    def _v(linha, campo):
        if "->>" in campo:
            base, chave = campo.split("->>", 1)
            return (linha.get(base) or {}).get(chave)
        return linha.get(campo)

    def select(self, *_a, **_k):
        self.op = "select"
        return self

    def eq(self, c, v):
        return self._f(lambda l: str(self._v(l, c)) == str(v) if not isinstance(v, bool) else self._v(l, c) is v)

    def neq(self, c, v):
        return self._f(lambda l: str(self._v(l, c)) != str(v))

    def in_(self, c, vs):
        vs = [str(x) for x in vs]
        return self._f(lambda l: str(self._v(l, c)) in vs)

    def is_(self, c, v):
        return self._f(lambda l: self._v(l, c) is None) if str(v) == "null" else self._f(lambda l: self._v(l, c) is v)

    def gte(self, c, v):
        return self._f(lambda l: self._v(l, c) is not None and str(self._v(l, c)) >= str(v))

    def lte(self, c, v):
        return self._f(lambda l: self._v(l, c) is not None and str(self._v(l, c)) <= str(v))

    def limit(self, n):
        self.lim = n
        return self

    def order(self, c, desc=False, **_k):
        self.ordem = (c, desc)
        return self

    def maybe_single(self):
        return self

    def insert(self, carga):
        self.op, self.carga = "insert", carga
        return self

    def upsert(self, carga, on_conflict=None):
        self.op, self.carga = "upsert", carga
        return self

    def update(self, carga):
        self.op, self.carga = "update", dict(carga)
        return self

    def delete(self):
        self.op = "delete"
        return self

    def execute(self):
        linhas = self.banco.dados.setdefault(self.tabela, [])
        casam = [l for l in linhas if all(f(l) for f in self.filtros)]
        if self.op == "select":
            if self.ordem:
                c, desc = self.ordem
                casam = sorted(casam, key=lambda l: str(l.get(c) or ""), reverse=desc)
            if self.lim:
                casam = casam[: self.lim]
            return _Resp(copy.deepcopy(casam))
        if self.op in ("insert", "upsert"):
            saida = []
            for nova in (self.carga if isinstance(self.carga, list) else [self.carga]):
                nova = copy.deepcopy(dict(nova))
                existente = next((l for l in linhas if "id" in nova and str(l.get("id")) == str(nova["id"])), None)
                if existente is not None:
                    if self.op == "insert":
                        raise RuntimeError("23505 duplicate key")
                    existente.update(nova)
                    saida.append(copy.deepcopy(existente))
                    continue
                nova.setdefault("id", str(uuid.uuid4()))
                nova.setdefault("created_at", _agora_iso())
                if self.tabela == V.TABELA_CODIGOS:
                    nova.setdefault("usado_em", None)
                    nova.setdefault("invalidado_em", None)
                linhas.append(nova)
                self.banco.escritas.append((self.tabela, self.op, copy.deepcopy(nova)))
                saida.append(copy.deepcopy(nova))
            return _Resp(saida)
        if self.op == "update":
            for l in casam:
                l.update(copy.deepcopy(self.carga))
                self.banco.escritas.append((self.tabela, "update", copy.deepcopy(l)))
            return _Resp(copy.deepcopy(casam))
        if self.op == "delete":
            linhas[:] = [l for l in linhas if l not in casam]
            return _Resp([])
        raise AssertionError(self.op)


class _Balde:
    def __init__(self, banco, nome):
        self.banco, self.nome = banco, nome

    def upload(self, path, blob, opcoes=None):
        self.banco.arquivos.append({"bucket": self.nome, "path": path, "bytes": len(blob), "opcoes": dict(opcoes or {})})
        return {"path": path}


class Banco:
    def __init__(self, **tabelas):
        self.dados = {k: [dict(l) for l in v] for k, v in tabelas.items()}
        self.escritas, self.arquivos = [], []
        self.storage = types.SimpleNamespace(from_=lambda nome: _Balde(self, nome))

    def table(self, nome):
        return _Consulta(self, nome)

    def linhas(self, nome):
        return self.dados.setdefault(nome, [])


def _hash(tok):
    from app.services.whatsapp.channel_security import webhook_token_hash

    return webhook_token_hash(tok)


def _membro(cid, uid, cel=None, *, verificado=True):
    return {"company_id": cid, "user_id": uid, "role": "member", "status": "active",
            "whatsapp_trabalho_e164": cel, "whatsapp_trabalho_confirmado_em": _agora_iso() if cel else None,
            "whatsapp_trabalho_verificado_em": _agora_iso() if (cel and verificado) else None}


def _pessoa(uid, nome):
    p, _, r = nome.partition(" ")
    return {"id": uid, "first_name": p, "last_name": r, "status": "active", "deleted_at": None}


def mundo_inicial() -> Banco:
    return Banco(
        companies=[{"id": CANAL, "company_name": "AutoBrokers Plataforma", "company_kind": "platform_canal"},
                   {"id": ALFA, "company_name": "Corretora Alfa", "company_kind": "client"},
                   {"id": BETA, "company_name": "Corretora Beta", "company_kind": "client"}],
        users_v2=[_pessoa(U1, "Pessoa Um"), _pessoa(U2, "Pessoa Dois"), _pessoa(U3, "Pessoa Tres"),
                  _pessoa(U4, "Pessoa Quatro"), _pessoa(U5, "Pessoa Cinco"), _pessoa(U6, "Pessoa Seis")],
        company_members=[_membro(ALFA, U1, CEL_1), _membro(ALFA, U2, CEL_2), _membro(BETA, U2, CEL_2),
                         _membro(BETA, U3, CEL_3, verificado=False), _membro(BETA, U4, CEL_4),
                         _membro(ALFA, U5, CEL_LINHA_ALFA),
                         _membro(ALFA, U6, CEL_6, verificado=False)],
        agents=[{"id": AG_ALFA_ATEND, "company_id": ALFA, "is_active": True, "agent_role": "attendance",
                 "widget_config": {}},
                {"id": AG_ALFA_CORE, "company_id": ALFA, "is_active": True, "agent_role": "core", "widget_config": {}},
                {"id": AG_BETA_CORE, "company_id": BETA, "is_active": True, "agent_role": "core", "widget_config": {}}],
        integrations=[
            {"id": "int-assistente", "company_id": CANAL, "provider": "evolution-go", "purpose": "assistente",
             "is_active": True, "channel_status": "connected", "identifier": "ab-assistente-1",
             "base_url": "http://evolution.invalid", "paired_phone_e164": "+" + ASSISTENTE,
             "webhook_token_hash": _hash(TOKEN_ASSISTENTE)},
            {"id": "int-qcm", "company_id": CANAL, "provider": "evolution-go", "purpose": "observer",
             "is_active": True, "channel_status": "connected", "identifier": "ab-qcm-1",
             "base_url": "http://evolution.invalid", "paired_phone_e164": "+" + QCM,
             "webhook_token_hash": _hash(TOKEN_QCM)},
            {"id": "int-alfa", "company_id": ALFA, "provider": "evolution-go", "purpose": "observer",
             "is_active": True, "channel_status": "connected", "identifier": "ab-alfa-1",
             "base_url": "http://evolution.invalid", "paired_phone_e164": CEL_LINHA_ALFA,
             "webhook_token_hash": _hash(TOKEN_ALFA)},
            # uma CORRETORA que gravou purpose='assistente' na própria linha NÃO vira o número do AutoBrokers
            {"id": "int-falso", "company_id": BETA, "provider": "evolution-go", "purpose": "assistente",
             "is_active": True, "channel_status": "connected", "identifier": "ab-beta-1",
             "base_url": "http://evolution.invalid", "paired_phone_e164": "+5521977770000",
             "webhook_token_hash": _hash(TOKEN_FALSO_ASSISTENTE)}],
        canal_convidados=[{"company_id": CANAL, "telefone": V._canonico(CEL_1), "ativo": True}],
        human_support_destinations=[], conversations=[], messages=[], artifacts=[],
        whatsapp_atalho_codigos=[], whatsapp_atalho_tentativas=[], whatsapp_atalho_estado=[],
    )


class ServicoDeIntegracao:
    def __init__(self, banco):
        self.banco = banco

    def get_integration_by_webhook_token(self, tok):
        h = _hash(tok)
        return next((dict(x) for x in self.banco.linhas("integrations") if x.get("webhook_token_hash") == h), None)

    def get_integration_by_id(self, ident):
        return None

    def get_integration_by_phone(self, _p):
        return None


class RedisFalso:
    def __init__(self):
        self.dados = {}

    async def set(self, k, v, ex=None, nx=False):
        if nx and k in self.dados:
            return None
        self.dados[k] = v
        return True

    async def get(self, k):
        return self.dados.get(k)

    async def delete(self, k):
        self.dados.pop(k, None)
        return 1


class EnvioFalso:
    def __init__(self):
        self.enviados, self.presencas = [], []

    def send_message(self, to_number=None, text=None, integration=None, *, bloco_unico=False):
        self.enviados.append({"para": to_number, "texto": text, "purpose": (integration or {}).get("purpose"),
                              "integracao": (integration or {}).get("id"), "bloco_unico": bloco_unico})
        return True

    def send_presence(self, to_number, estado, integration, delay_ms=0):
        self.presencas.append((to_number, estado, (integration or {}).get("id")))
        return True


# =====================================================================================================================
# a fixture: o webhook REAL + o /chat/stream REAL, com o grafo e o banco dublados
# =====================================================================================================================
@pytest.fixture
def fio(monkeypatch):
    import socket

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import app.api.webhook as w
    import app.core.redis as _redis
    import app.services.atlas.observer_intake as _obs
    import app.services.whatsapp_service as _ws
    from app.core.rate_limit import limiter

    arreio = importlib.import_module("test_o_chat_fala_tipado")
    from test_spec133a_a_entrada import _sem_rede, _sem_rede_ex

    monkeypatch.setattr(socket.socket, "connect", _sem_rede)
    monkeypatch.setattr(socket.socket, "connect_ex", _sem_rede_ex)
    monkeypatch.setenv(E.ENV_LIGADO, "1")
    monkeypatch.setenv("ADMIN_API_KEY", arreio.CHAVE_INTERNA_D)
    monkeypatch.setenv("ATALHO_CODIGO_SEGREDO", "segredo-de-teste-132c")
    monkeypatch.setenv("PORTAL_VAULT_KEY", CHAVE_DO_COFRE)
    monkeypatch.setenv("PUBLIC_APP_URL", "https://app.exemplo.test")
    monkeypatch.setattr(ENV, "PAUSA_ENTRE_MENSAGENS_S", 0)

    banco = mundo_inicial()
    sup = types.SimpleNamespace(client=banco)
    redis = RedisFalso()

    async def _redis_async():
        return redis

    async def _nada(*_a, **_k):
        return None

    monkeypatch.setattr(_redis, "get_async_redis_client", _redis_async)
    monkeypatch.setattr(w, "supabase", sup)
    monkeypatch.setattr(w, "integration_service", ServicoDeIntegracao(banco))
    monkeypatch.setattr(w, "get_async_redis_client", _redis_async)
    monkeypatch.setattr(w, "_registrar_retorno_de_cobranca", _nada)
    from app.services.canal import repositorio as _repo

    _repo._CACHE_DO_TIPO.clear()

    taps, pipeline = [], []

    async def _tap(integration, body):     # o observer CONSOME
        taps.append(str((integration or {}).get("id")))
        return {"status": "observed"}

    async def _pipeline(integration, body, background_tasks, label):   # o caminho de sempre (QCM / atendimento)
        pipeline.append(str((integration or {}).get("id")))
        return {"status": "buffered"}

    monkeypatch.setattr(_obs, "observer_tap", _tap)
    monkeypatch.setattr(w, "_handle_evolution_like_inbound", _pipeline)

    envio = EnvioFalso()
    monkeypatch.setattr(_ws, "get_whatsapp_service", lambda: envio)
    monkeypatch.setattr(w, "whatsapp_service", envio)

    troca = arreio._TrocaModulosD(arreio._montar_stubs_d(banco))
    troca.__enter__()
    chat_mod = importlib.import_module("app.api.chat")
    app_do_chat = arreio._montar_app_d(chat_mod, banco)
    monkeypatch.setattr(T, "_aplicacao", lambda: app_do_chat)
    arreio.EVENTOS_DO_GRAFO_D[:] = [arreio._delta_d(TABELA_MD)]
    chamadas_do_grafo = []
    original = sys.modules["app.agents.graph"].stream_agent_eventos

    async def _espiao(graph, **k):
        chamadas_do_grafo.append(dict(k))
        async for ev in original(graph, **k):
            yield ev

    sys.modules["app.agents.graph"].stream_agent_eventos = _espiao

    app = FastAPI()
    app.state.limiter = limiter
    app.include_router(w.router)
    cliente = TestClient(app)
    seq = {"n": 0}

    def postar(texto="oi", *, tel=CEL_1, token=TOKEN_ASSISTENTE, from_me=False, grupo=False, jid=None):
        with open(FIXTURE, encoding="utf-8") as f:
            corpo = copy.deepcopy(json.load(f)["evento"])
        seq["n"] += 1
        digitos = tel.lstrip("+")
        chat = jid or ("120363000000000001@g.us" if grupo else f"{digitos}@s.whatsapp.net")
        corpo["data"]["Info"].update({"Chat": chat, "Sender": f"{digitos}@s.whatsapp.net", "IsFromMe": from_me,
                                      "IsGroup": grupo, "ID": f"3EB0C0A1{seq['n']:014d}"})
        corpo["data"]["Message"] = {"conversation": texto}
        limiter.reset()
        r = cliente.post(f"/api/v1/webhook/evolution-go/{token}", json=corpo)
        assert r.status_code == 200, r.text
        return r.json()

    def postar_v2(mensagem, *, tel=CEL_1, token=TOKEN_ASSISTENTE):
        seq["n"] += 1
        corpo = {"event": "messages.upsert", "data": {
            "key": {"remoteJid": f"{tel.lstrip('+')}@s.whatsapp.net", "fromMe": False, "id": f"3EB0V2{seq['n']:014d}"},
            "pushName": "Pessoa", "message": mensagem}}
        limiter.reset()
        r = cliente.post(f"/api/v1/webhook/evolution-go/{token}", json=corpo)
        assert r.status_code == 200, r.text
        return r.json()

    cliente_cru = TestClient(app, raise_server_exceptions=False)

    def postar_cru(corpo, *, token=TOKEN_ASSISTENTE):
        """O corpo como veio (formatos estranhos): devolve (status HTTP, json ou texto) — sem afirmar 200."""
        limiter.reset()
        r = cliente_cru.post(f"/api/v1/webhook/evolution-go/{token}", json=corpo)
        try:
            return r.status_code, r.json()
        except ValueError:
            return r.status_code, r.text

    try:
        yield types.SimpleNamespace(banco=banco, envio=envio, taps=taps, pipeline=pipeline, grafo=chamadas_do_grafo,
                                    redis=redis, postar=postar, postar_v2=postar_v2, postar_cru=postar_cru,
                                    arreio=arreio)
    finally:
        sys.modules["app.agents.graph"].stream_agent_eventos = original
        troca.__exit__(None, None, None)


def _conversas(b, **filtro):
    return [c for c in b.linhas("conversations") if all(str(c.get(k)) == str(v) for k, v in filtro.items())]


def _mensagens(b, conversa_id):
    return [m for m in b.linhas("messages") if str(m.get("conversation_id")) == str(conversa_id)]


# =====================================================================================================================
# 1. O FIO: número verificado → o CORE da corretora DELE → a resposta pelo número do AutoBrokers
# =====================================================================================================================
def test_numero_verificado_o_turno_roda_com_a_corretora_dele_e_responde_pelo_assistente(fio):
    r = fio.postar("quanto fica o seguro do meu cliente?", tel=CEL_1)
    assert r == {"status": "accepted", "reason": "atalho"}
    # o turno do chat rodou UMA vez, com o company_id/user_id do membro (do número VERIFICADO, nunca do texto)
    assert len(fio.grafo) == 1
    assert fio.grafo[0]["company_id"] == ALFA and fio.grafo[0]["user_id"] == U1
    (conv,) = _conversas(fio.banco, company_id=ALFA, user_id=U1)
    assert conv["channel"] == T.CANAL_DO_ATALHO and conv["agent_id"] == AG_ALFA_CORE   # o CORE, nunca o atendimento
    assert fio.grafo[0]["session_id"] == conv["session_id"]
    msgs = _mensagens(fio.banco, conv["id"])
    pergunta = [m for m in msgs if m["role"] == "user"]
    resposta = [m for m in msgs if m["role"] == "assistant"]
    assert [m["content"] for m in pergunta] == ["quanto fica o seguro do meu cliente?"]
    assert pergunta[0]["payload"]["client_request_id"] and pergunta[0]["payload"]["origem"] == T.CANAL_DO_ATALHO
    assert len(resposta) == 1 and resposta[0]["content"] == TABELA_MD            # o chat grava o markdown (painel)
    assert resposta[0]["payload"]["client_request_id"] == pergunta[0]["payload"]["client_request_id"]
    # a resposta saiu pelo número do AutoBrokers, para o telefone de quem mandou, em formato WhatsApp
    assert len(fio.envio.enviados) == 1
    saida = fio.envio.enviados[0]
    assert saida["integracao"] == "int-assistente" and saida["purpose"] == "assistente" and saida["bloco_unico"]
    assert saida["para"] == V._canonico(CEL_1)
    assert "*Cotação Rápida — 3 seguradoras*" in saida["texto"] and "**" not in saida["texto"]
    assert "• Seguradora Um — parcelas 12x R$ 99,90 · à vista R$ 1.100,00" in saida["texto"]
    assert saida["texto"].rstrip().endswith("apresentação: https://app.exemplo.test/r/abc123")
    assert "|" not in saida["texto"]
    # nada passou pelo observer nem pelo caminho do QCM/atendimento
    assert fio.taps == [] and fio.pipeline == []


def test_duas_corretoras_cada_membro_no_proprio_chat(fio):
    fio.postar("oi", tel=CEL_1)
    fio.postar("oi", tel=CEL_4)
    assert [(g["company_id"], g["user_id"]) for g in fio.grafo] == [(ALFA, U1), (BETA, U4)]
    assert {c["company_id"] for c in _conversas(fio.banco, user_id=U4)} == {BETA}
    assert {c["company_id"] for c in _conversas(fio.banco, user_id=U1)} == {ALFA}
    # a 2ª mensagem do mesmo membro volta para a MESMA conversa (uma ativa por membro por corretora)
    fio.postar("e o prazo?", tel=CEL_1)
    assert len(_conversas(fio.banco, company_id=ALFA, user_id=U1)) == 1
    assert fio.grafo[2]["session_id"] == fio.grafo[0]["session_id"]


def test_conversa_nova_depois_de_12h_de_silencio(fio):
    fio.postar("oi", tel=CEL_1)
    (conv,) = _conversas(fio.banco, company_id=ALFA, user_id=U1)
    for c in fio.banco.linhas("conversations"):
        c["last_message_at"] = (datetime.now(timezone.utc) - timedelta(hours=13)).isoformat()
    fio.postar("oi de novo", tel=CEL_1)
    assert len(_conversas(fio.banco, company_id=ALFA, user_id=U1)) == 2
    assert fio.grafo[1]["session_id"] != conv["session_id"]


# =====================================================================================================================
# 2. número NÃO verificado = SILÊNCIO total (mutação 1)
# =====================================================================================================================
@pytest.mark.parametrize("tel", [CEL_ESTRANHO, CEL_6], ids=["desconhecido", "confirmado-sem-verificar"])
def test_numero_nao_verificado_silencio_sem_resposta_e_sem_conteudo(fio, tel):
    escritas_antes = len(fio.banco.escritas)
    r = fio.postar("me passa os dados do cliente", tel=tel)
    assert r["status"] == "accepted"          # o webhook aceitou; quem cala é o turno
    assert fio.envio.enviados == [] and fio.envio.presencas == []
    assert fio.grafo == []
    assert fio.banco.linhas("conversations") == [] and fio.banco.linhas("messages") == []
    assert fio.banco.escritas[escritas_antes:] == []          # nenhuma linha escrita, de nada


# =====================================================================================================================
# 3. o número de ATENDIMENTO e o do QCM seguem como hoje (mutação 4)
# =====================================================================================================================
def test_a_mesma_mensagem_ao_qcm_ou_ao_atendimento_nao_passa_pelo_atalho(fio):
    # o QCM (mesma empresa da plataforma, purpose observer): o desvio do QCM, convidado → o pipeline de sempre
    fio.postar("quanto fica o seguro?", tel=CEL_1, token=TOKEN_QCM)
    assert fio.pipeline == ["int-qcm"]
    # o atendimento de uma corretora: o observer consome
    fio.postar("quanto fica o seguro?", tel=CEL_1, token=TOKEN_ALFA)
    assert fio.taps == ["int-alfa"]
    # uma corretora com purpose='assistente' na própria linha NÃO é o número do AutoBrokers — e (conserto B1) o
    # portão FECHA: não vira atalho, nem observer, nem pipeline (antes caía no observer: a verdade mudou, §9.3)
    r = fio.postar("quanto fica o seguro?", tel=CEL_1, token=TOKEN_FALSO_ASSISTENTE)
    assert r == {"status": "ignored", "reason": "atalho_nao_confirmado"}
    assert fio.taps == ["int-alfa"] and fio.pipeline == ["int-qcm"]
    assert fio.grafo == [] and fio.envio.enviados == [] and fio.banco.linhas("conversations") == []


# =====================================================================================================================
# 4. fromMe, grupo, status e as instâncias do produto não geram resposta (mutação 5)
# =====================================================================================================================
def test_from_me_grupo_e_status_nao_geram_resposta(fio):
    assert fio.postar("eco da nossa própria voz", tel=CEL_1, from_me=True)["status"] == "ignored"
    assert fio.postar("mensagem no grupo", tel=CEL_1, grupo=True)["status"] == "ignored"
    assert fio.postar("status", tel=CEL_1, jid="status@broadcast")["status"] == "ignored"
    assert fio.envio.enviados == [] and fio.grafo == [] and fio.banco.linhas("conversations") == []


def test_anti_laco_numero_de_instancia_do_produto_nao_recebe_resposta(fio):
    # U5 verificou o número que é a LINHA de atendimento da Alfa (um robô falaria com o outro)
    r = fio.postar("oi", tel=CEL_LINHA_ALFA)
    assert r["status"] == "accepted"
    assert fio.envio.enviados == [] and fio.grafo == []
    # o próprio QCM escrevendo ao assistente também cala (a linha da plataforma, que o anti-laço do QCM deixa passar)
    assert E.numero_do_produto(fio.banco, "+" + QCM) is True
    assert E.numero_do_produto(fio.banco, "+" + ASSISTENTE) is True
    assert E.numero_do_produto(fio.banco, CEL_1) is False      # CONTROLE: o corretor não é instância


# =====================================================================================================================
# 5. membro de duas corretoras: pergunta UMA vez e não mistura (mutação 6)
# =====================================================================================================================
def test_membro_de_duas_corretoras_pergunta_e_nao_mistura(fio):
    fio.postar("preciso de uma cotação para o cliente", tel=CEL_2)
    assert fio.grafo == []
    (pergunta,) = [e["texto"] for e in fio.envio.enviados]
    assert "qual corretora" in pergunta and "1) Corretora Alfa" in pergunta and "2) Corretora Beta" in pergunta
    assert fio.banco.linhas("conversations") == []
    fio.postar("2", tel=CEL_2)
    # a fala guardada segue pela BETA — e só pela Beta
    assert len(fio.grafo) == 1
    assert fio.grafo[0]["company_id"] == BETA and fio.grafo[0]["user_id"] == U2
    (conv,) = _conversas(fio.banco, user_id=U2)
    assert conv["company_id"] == BETA
    assert [m["content"] for m in _mensagens(fio.banco, conv["id"]) if m["role"] == "user"] == [
        "preciso de uma cotação para o cliente"]
    assert _conversas(fio.banco, company_id=ALFA, user_id=U2) == []
    # a próxima mensagem já vai para a Beta, sem perguntar de novo
    n = len(fio.envio.enviados)
    fio.postar("e o prazo?", tel=CEL_2)
    assert fio.grafo[1]["company_id"] == BETA and fio.grafo[1]["session_id"] == conv["session_id"]
    assert all("qual corretora" not in e["texto"] for e in fio.envio.enviados[n:])
    # "trocar corretora" pergunta de novo; "1" leva para a Alfa, numa conversa DELA
    fio.postar("trocar corretora", tel=CEL_2)
    assert "qual corretora" in fio.envio.enviados[-1]["texto"]
    fio.postar("1", tel=CEL_2)
    assert "Corretora Alfa" in fio.envio.enviados[-1]["texto"]
    fio.postar("e agora?", tel=CEL_2)
    assert fio.grafo[-1]["company_id"] == ALFA
    (conv_alfa,) = _conversas(fio.banco, company_id=ALFA, user_id=U2)
    assert fio.grafo[-1]["session_id"] == conv_alfa["session_id"] != conv["session_id"]
    assert [m["content"] for m in _mensagens(fio.banco, conv_alfa["id"]) if m["role"] == "user"] == ["e agora?"]


# =====================================================================================================================
# 6. ATIVAR casa o código e responde; o número passa a ser identidade
# =====================================================================================================================
def test_ativar_casa_o_codigo_responde_e_o_numero_vira_identidade(fio):
    codigo = V.gerar_codigo(fio.banco, company_id=BETA, user_id=U3)["codigo"]
    fio.postar("ATIVAR 000000", tel=CEL_3)                 # código errado: silêncio (C1)
    assert fio.envio.enviados == []
    fio.postar(f"ATIVAR {codigo}", tel=CEL_3)
    (pronto,) = fio.envio.enviados
    assert pronto["texto"].startswith("Pronto, Pessoa!") and "Corretora Beta" in pronto["texto"]
    assert pronto["integracao"] == "int-assistente"
    membro = next(m for m in fio.banco.linhas("company_members") if m["company_id"] == BETA and m["user_id"] == U3)
    assert membro["whatsapp_trabalho_verificado_em"] and membro["whatsapp_trabalho_e164"] == CEL_3
    assert fio.grafo == []                                  # a ativação não é turno do chat
    fio.postar("oi", tel=CEL_3)
    assert fio.grafo[0]["company_id"] == BETA and fio.grafo[0]["user_id"] == U3


# =====================================================================================================================
# 7. desligado: o desvio não lê, não grava, não responde
# =====================================================================================================================
def test_desligado_nao_responde_e_nao_le_o_banco(fio, monkeypatch):
    monkeypatch.delenv(E.ENV_LIGADO, raising=False)
    r = fio.postar("oi", tel=CEL_1)
    assert r == {"status": "ignored", "reason": "atalho_desligado"}
    assert fio.envio.enviados == [] and fio.grafo == [] and fio.banco.escritas == []
    assert fio.taps == [] and fio.pipeline == []           # nem cai no QCM nem no observer


# =====================================================================================================================
# 8. o teto de mensagens por dia
# =====================================================================================================================
def test_teto_de_mensagens_por_dia_uma_frase_e_depois_silencio(fio):
    fio.postar("oi", tel=CEL_1)
    (conv,) = _conversas(fio.banco, company_id=ALFA, user_id=U1)
    agora = datetime.now(timezone.utc).isoformat()
    for i in range(T.TETO_DE_MENSAGENS_POR_DIA - 1):
        fio.banco.linhas("messages").append({"id": str(uuid.uuid4()), "conversation_id": conv["id"], "role": "user",
                                             "content": f"m{i}", "created_at": agora})
    n_grafo = len(fio.grafo)
    fio.postar("mais uma", tel=CEL_1)
    assert fio.envio.enviados[-1]["texto"] == E.FRASE_DO_TETO and len(fio.grafo) == n_grafo
    n = len(fio.envio.enviados)
    fio.postar("e mais outra", tel=CEL_1)
    assert len(fio.envio.enviados) == n and len(fio.grafo) == n_grafo


# =====================================================================================================================
# 9. a mídia: Storage no prefixo da corretora DO MEMBRO → os anexos do turno
# =====================================================================================================================
def test_documento_sobe_no_prefixo_do_membro_e_vira_anexo_do_turno(fio, monkeypatch):
    import app.services.chat_anexos as CA

    recebidos = []

    async def _preparar(company_id, anexos, *, ao_progredir=None):
        recebidos.append((company_id, [dict(a) for a in anexos]))
        r = CA.ResultadoDosAnexos()
        r.texto = "[DOCUMENTO ANEXADO: apolice.pdf]\n(texto mascarado)\n[FIM DO DOCUMENTO]"
        return r

    monkeypatch.setattr(CA, "preparar", _preparar)
    pdf = b"%PDF-1.4 conteudo ficticio"
    fio.postar_v2({"documentMessage": {"mimetype": "application/pdf", "fileName": "apolice.pdf",
                                       "caption": "confere essa apólice"},
                   "base64": base64.b64encode(pdf).decode()}, tel=CEL_4)
    (arquivo,) = fio.banco.arquivos
    assert arquivo["bucket"] == "chat-docs" and arquivo["bytes"] == len(pdf)
    assert arquivo["path"].startswith(f"{BETA}/{U4}/chat-docs/") and arquivo["path"].endswith(".pdf")
    ((cid, anexos),) = recebidos
    assert cid == BETA and anexos == [{"bucket": "chat-docs", "path": arquivo["path"], "nome": "apolice.pdf",
                                       "mime": "application/pdf", "bytes": len(pdf)}]
    (conv,) = _conversas(fio.banco, company_id=BETA, user_id=U4)
    (pergunta,) = [m for m in _mensagens(fio.banco, conv["id"]) if m["role"] == "user"]
    assert pergunta["payload"]["attachments"][0]["path"] == arquivo["path"]
    assert fio.grafo[0]["company_id"] == BETA and "DOCUMENTO ANEXADO" in fio.grafo[0]["user_message"]
    assert len(fio.envio.enviados) == 1


# =====================================================================================================================
# 10. o formato WhatsApp (puro)
# =====================================================================================================================
def test_o_formato_whatsapp_da_tabela_titulos_negrito_e_links():
    md = ("## Resumo\n\nO **melhor** preço é da *Seguradora Um*.\n\n"
          "| Seguradora | Parcelas | À vista |\n|:---|---:|---|\n| **Seguradora Um** | 12x R$ 99,90 | R$ 1.100 |\n\n"
          "- primeiro ponto\n- segundo ponto\n\n---\n\n[Abrir a apresentação](/dashboard/entregas/abc) e "
          "https://solto.exemplo.test/x")
    os.environ["PUBLIC_APP_URL"] = "https://app.exemplo.test"
    try:
        texto = ENV.para_whatsapp(md)
    finally:
        os.environ.pop("PUBLIC_APP_URL", None)
    assert texto.startswith("*Resumo*")
    assert "O *melhor* preço é da _Seguradora Um_." in texto
    assert "• Seguradora Um — parcelas 12x R$ 99,90 · à vista R$ 1.100" in texto
    assert "• primeiro ponto\n• segundo ponto" in texto
    assert "---" not in texto and "|" not in texto and "**" not in texto and "](" not in texto
    assert texto.endswith("Abrir a apresentação: https://app.exemplo.test/dashboard/entregas/abc")
    assert "https://solto.exemplo.test/x" in texto
    # duas colunas: sem rótulo
    assert ENV.para_whatsapp("| Campo | Valor |\n|---|---|\n| Placa | ABC1D23 |") == "• Placa — ABC1D23"


def test_o_corte_em_mensagens_inteiras_de_ate_3500():
    SEP = chr(10) * 2
    paragrafos = [(("parágrafo %d " % i) * 40).strip() for i in range(20)]
    partes = ENV.em_mensagens(SEP.join(paragrafos))
    assert len(partes) > 1 and all(len(p) <= ENV.TETO_DE_UMA_MENSAGEM for p in partes)
    assert SEP.join(partes) == SEP.join(paragrafos)      # nada some, nada se repete
    for p in partes:                                             # nenhum parágrafo partido no meio
        assert all(x in paragrafos for x in p.split(SEP))
    assert ENV.em_mensagens("x" * 8000) == ["x" * 3500, "x" * 3500, "x" * 1000]
    assert ENV.em_mensagens("curta") == ["curta"] and ENV.em_mensagens("  ") == []


def test_o_envio_recusa_integracao_que_nao_e_a_do_assistente(monkeypatch):
    import asyncio

    import app.services.whatsapp_service as _ws

    envio = EnvioFalso()
    monkeypatch.setattr(_ws, "get_whatsapp_service", lambda: envio)
    monkeypatch.setenv("ATALHO_CODIGO_SEGREDO", "segredo-de-teste-132c")
    banco = mundo_inicial()
    n = asyncio.run(ENV.enviar({"id": "int-qcm", "purpose": "observer"}, CEL_1, ["oi"], db=banco))
    assert n == 0 and envio.enviados == []
    # sem banco não há como conferir o anti-laço nem o teto: nada sai (fail-closed)
    n = asyncio.run(ENV.enviar({"id": "int-assistente", "purpose": "assistente"}, CEL_1, ["oi"]))
    assert n == 0 and envio.enviados == []
    n = asyncio.run(ENV.enviar({"id": "int-assistente", "purpose": "assistente"}, CEL_1, ["oi"], db=banco))
    assert n == 1 and envio.enviados[0]["integracao"] == "int-assistente"


# =====================================================================================================================
# 11. O CONSERTO ÚNICO (laudos JUIZ-132-C e RED-TEAM-132-C) — cada guarda tem a sua mutação lá embaixo (C*)
# =====================================================================================================================
def test_o_portao_do_assistente_falha_fechado_com_o_banco_instavel(fio, monkeypatch):
    """B1 (juiz): a leitura do tipo da empresa falha → a mensagem ao número do ASSISTENTE é IGNORADA ali — nunca o
    observer, o QCM nem o pipeline de atendimento."""
    from app.services.canal import repositorio as _repo

    # CONTROLE: banco bom → o atalho (nada no observer nem no pipeline)
    assert fio.postar("oi", tel=CEL_ESTRANHO) == {"status": "accepted", "reason": "atalho"}
    assert fio.taps == [] and fio.pipeline == []
    _repo._CACHE_DO_TIPO.clear()
    original = fio.banco.table

    def _table(nome):   # o PostgREST não responde à leitura de `companies`
        if nome == "companies":
            raise RuntimeError("banco instavel")
        return original(nome)

    monkeypatch.setattr(fio.banco, "table", _table)
    r = fio.postar("me passa os dados do cliente", tel=CEL_ESTRANHO)
    assert r == {"status": "ignored", "reason": "atalho_nao_confirmado"}
    assert fio.taps == [] and fio.pipeline == [] and fio.grafo == [] and fio.envio.enviados == []


def _conversa_do_atalho(fio, cid, uid):
    linha = {"id": str(uuid.uuid4()), "company_id": cid, "user_id": uid, "channel": T.CANAL_DO_ATALHO,
             "session_id": str(uuid.uuid4()), "status": "open", "last_message_at": _agora_iso()}
    fio.banco.linhas("conversations").append(linha)
    return linha


def test_a_saida_nao_manda_para_instancia_do_produto(fio):
    """RT-132C-01: U5 verificou o celular e DEPOIS ele virou a linha de atendimento da Alfa. A volta da cotação (e
    qualquer envio) NÃO sai para lá — o anti-laço vale na SAÍDA. U1 é o controle."""
    import asyncio

    conv_u5 = _conversa_do_atalho(fio, ALFA, U5)
    assert asyncio.run(ENV.avisar_pelo_atalho_se_for_o_caso(
        fio.banco, company_id=ALFA, conversation_id=conv_u5["id"], texto_markdown="**Cotação** pronta")) is False
    integ = ENV.integracao_do_assistente(fio.banco)
    assert asyncio.run(ENV.enviar(integ, CEL_LINHA_ALFA, ["oi"], db=fio.banco)) == 0
    assert asyncio.run(ENV.enviar(integ, "+" + QCM, ["oi"], db=fio.banco)) == 0
    assert fio.envio.enviados == []
    # CONTROLE: o mesmo caminho para U1 (o celular de uma pessoa) sai, uma vez
    conv_u1 = _conversa_do_atalho(fio, ALFA, U1)
    assert asyncio.run(ENV.avisar_pelo_atalho_se_for_o_caso(
        fio.banco, company_id=ALFA, conversation_id=conv_u1["id"], texto_markdown="**Cotação** pronta")) is True
    assert [e["para"] for e in fio.envio.enviados] == [V._canonico(CEL_1)]


def test_o_codigo_vazado_mandado_de_outro_celular_nao_troca_a_identidade(fio):
    """P1 (juiz e red team): o código de U1 mandado de OUTRO celular → silêncio; o número, a confirmação e a
    verificação de U1 não mudam; o turno seguinte do outro celular não roda como U1."""
    antes = copy.deepcopy(next(m for m in fio.banco.linhas("company_members")
                               if m["company_id"] == ALFA and m["user_id"] == U1))
    passo = V.gerar_codigo(fio.banco, company_id=ALFA, user_id=U1)
    fio.postar(passo["texto"], tel=CEL_ESTRANHO)
    depois = next(m for m in fio.banco.linhas("company_members") if m["company_id"] == ALFA and m["user_id"] == U1)
    assert depois == antes                                    # nada mudou no membro
    assert fio.envio.enviados == []
    fio.postar("lista os meus clientes", tel=CEL_ESTRANHO)
    assert fio.grafo == [] and fio.envio.enviados == []
    # CONTROLE: o MESMO código, do número declarado de U1, verifica
    fio.postar(passo["texto"], tel=CEL_1)
    (pronto,) = fio.envio.enviados
    assert pronto["para"] == V._canonico(CEL_1) and pronto["texto"].startswith("Pronto, ")


def test_qual_corretora_vai_uma_vez_e_as_falas_esperam_juntas(fio):
    """P2 (red team): 8 mensagens sem escolher → UMA pergunta; a escolha leva as falas guardadas, juntas, para a
    corretora escolhida. E cada mensagem que saiu contou no teto do dia."""
    from app.services.atalho import estado as EST

    for i in range(8):
        fio.postar(f"pergunta {i}", tel=CEL_2)
    perguntas = [e for e in fio.envio.enviados if "qual corretora" in e["texto"]]
    assert len(perguntas) == 1 and len(fio.envio.enviados) == 1 and fio.grafo == []
    fio.postar("2", tel=CEL_2)
    assert [(g["company_id"], g["user_id"]) for g in fio.grafo] == [(BETA, U2)]
    (conv,) = _conversas(fio.banco, company_id=BETA, user_id=U2)
    (fala,) = [m["content"] for m in _mensagens(fio.banco, conv["id"]) if m["role"] == "user"]
    assert fala == "\n".join(f"pergunta {i}" for i in range(8))
    assert EST.enviadas_hoje(fio.banco, CEL_2) == len(fio.envio.enviados) == 2


def test_toda_mensagem_que_sai_conta_no_teto_de_envios(fio, monkeypatch):
    """P2 (red team): sem agente CORE, cada mensagem recebia a frase e o contador ficava em zero. Agora a frase conta,
    e no teto do dia nada mais sai (💭 teto rebaixado para 3 no teste)."""
    from app.services.atalho import estado as EST

    monkeypatch.setattr(EST, "TETO_DE_ENVIOS_POR_DIA", 3)
    fio.banco.dados["agents"] = [a for a in fio.banco.linhas("agents") if a["company_id"] != BETA]
    for i in range(10):
        fio.postar(f"oi {i}", tel=CEL_4)
    assert len(fio.envio.enviados) == 3 and all("ainda não está ligado" in e["texto"] for e in fio.envio.enviados)
    assert EST.enviadas_hoje(fio.banco, CEL_4) == 3
    # CONTROLE: outro telefone tem o próprio teto
    fio.postar("oi", tel=CEL_1)
    assert fio.envio.enviados[-1]["para"] == V._canonico(CEL_1)


def test_sem_redis_trocar_corretora_funciona(fio, monkeypatch):
    """P3 (red team): a pergunta pendente mora no banco — Redis fora, "trocar corretora" + "2" vai para a Beta."""
    import app.api.webhook as w
    import app.core.redis as _redis

    fio.postar("oi", tel=CEL_2)
    fio.postar("1", tel=CEL_2)                       # escolhe a Alfa

    async def _sem():
        raise RuntimeError("redis fora")

    monkeypatch.setattr(_redis, "get_async_redis_client", _sem)
    monkeypatch.setattr(w, "get_async_redis_client", _sem)
    fio.postar("trocar corretora", tel=CEL_2)
    assert "qual corretora" in fio.envio.enviados[-1]["texto"]
    fio.postar("2", tel=CEL_2)
    assert "Corretora Beta" in fio.envio.enviados[-1]["texto"]
    fio.postar("e agora?", tel=CEL_2)
    assert fio.grafo[-1]["company_id"] == BETA
    assert all(m["content"] != "2" for m in fio.banco.linhas("messages") if m["role"] == "user")


@pytest.mark.parametrize("chave", [["a"], "texto", 5], ids=["lista", "texto", "numero"])
def test_formato_estranho_da_chave_e_ignorado_sem_500(fio, chave):
    """P4 (red team): `data.key` como lista dava 500 no webhook do assistente."""
    status, corpo = fio.postar_cru({"event": "messages.upsert",
                                    "data": {"key": chave, "message": {"conversation": "oi"}}})
    assert status == 200 and corpo["status"] == "ignored"
    assert fio.envio.enviados == [] and fio.grafo == []
    # CONTROLE: o mesmo envelope com a chave certa entra
    assert fio.postar_v2({"conversation": "oi"}, tel=CEL_1) == {"status": "accepted", "reason": "atalho"}


def test_texto_enorme_e_cortado_antes_do_turno_com_aviso(fio):
    """P5 (red team): 1 MB de texto virava `chatInput`. Agora até 💭 8.000 caracteres, e a pessoa é avisada."""
    fio.postar("a" * 20000, tel=CEL_1)
    (turno,) = fio.grafo
    (conv,) = _conversas(fio.banco, company_id=ALFA, user_id=U1)
    (pergunta,) = [m for m in _mensagens(fio.banco, conv["id"]) if m["role"] == "user"]
    assert len(pergunta["content"]) == E.LIMITE_DO_TEXTO
    assert fio.envio.enviados[0]["texto"] == E.FRASE_TEXTO_LONGO and len(fio.envio.enviados) == 2
    # CONTROLE: o texto do tamanho do limite passa inteiro, sem aviso
    fio.postar("b" * E.LIMITE_DO_TEXTO, tel=CEL_1)
    assert fio.envio.enviados[-2]["texto"] != E.FRASE_TEXTO_LONGO and len(fio.envio.enviados) == 3


# =====================================================================================================================
# as MUTAÇÕES (por cópia) — `python tests/test_spec132c_o_atalho.py --mutar`
# =====================================================================================================================
MUTACOES = [
    ("M1", "app/services/atalho/entrada.py",
     '                logger.info("[ATALHO] número não verificado (%s) — silêncio", _mascarar(tel))\n',
     '                await envio.enviar_texto(integracao, tel, "Este número é exclusivo de corretores.", db=db)\n',
     "test_numero_nao_verificado_silencio_sem_resposta_e_sem_conteudo"),
    ("M4", "app/services/atalho/entrada.py",
     "    if str((integracao or {}).get(\"purpose\") or \"\").strip().lower() != PURPOSE_DO_ASSISTENTE:\n",
     "    if str((integracao or {}).get(\"purpose\") or \"\").strip().lower() not in (PURPOSE_DO_ASSISTENTE, "
     "\"observer\"):\n",
     "test_a_mesma_mensagem_ao_qcm_ou_ao_atendimento_nao_passa_pelo_atalho",
     ("app/api/webhook.py", 'if str(integration.get("purpose") or "").strip().lower() == "assistente":',
      'if str(integration.get("purpose") or "").strip().lower() in ("assistente", "observer"):')),
    ("M5", "app/services/atalho/entrada.py",
     '    if chave.get("fromMe") or jid.endswith(("@g.us", "@broadcast", "@newsletter", "@call")):\n',
     '    if jid.endswith(("@g.us", "@broadcast", "@newsletter", "@call")):\n',
     "test_from_me_grupo_e_status_nao_geram_resposta",
     ("app/services/atalho/entrada.py", '    if normalizado.get("skip"):\n',
      '    if normalizado.get("skip") and normalizado.get("skip_reason") != "from_me":\n'),
     ("app/services/atalho/entrada.py", '    if normalizado.get("from_me") or normalizado.get("is_group"):\n',
      '    if normalizado.get("is_group"):\n')),
    ("M5b", "app/services/atalho/entrada.py",
     "    fs = repo.formas(telefone)\n    if not fs:\n        return False\n",
     "    fs = repo.formas(telefone)\n    if True:\n        return False\n",
     "test_anti_laco_numero_de_instancia_do_produto_nao_recebe_resposta"),
    ("M6", "app/services/atalho/entrada.py",
     "            if len(membros) == 1:\n                membro = membros[0]\n",
     "            if len(membros) >= 1:\n                membro = membros[0]\n",
     "test_membro_de_duas_corretoras_pergunta_e_nao_mistura"),
    # --- o conserto único (cada uma é o defeito do laudo DE VOLTA) ---
    ("C-B1 o portão volta a falhar aberto", "app/api/webhook.py",
     '        return {"status": "ignored", "reason": "atalho_nao_confirmado"}\n',
     "",
     "test_o_portao_do_assistente_falha_fechado"),
    ("C-RT01 a saída sem anti-laço", "app/services/atalho/envio.py",
     "    if await asyncio.to_thread(numero_do_produto, db, tel):\n",
     "    if False:\n",
     "test_a_saida_nao_manda_para_instancia_do_produto"),
    ("C-P1 o código vale de qualquer celular", "app/services/atalho/verificacao.py",
     "            or not _mesmo_telefone(membro.get(\"whatsapp_trabalho_e164\"), e164):\n",
     "            and not _mesmo_telefone(membro.get(\"whatsapp_trabalho_e164\"), e164):\n",
     "test_o_codigo_vazado_mandado_de_outro_celular",
     ("app/services/atalho/verificacao.py",
      "    patch = {\"whatsapp_trabalho_verificado_em\": t0.isoformat()}\n",
      "    patch = {\"whatsapp_trabalho_e164\": _e164_de(telefone), \"whatsapp_trabalho_verificado_em\": t0.isoformat()}\n"),
     ("app/services/atalho/verificacao.py",
      "                                   .eq(\"whatsapp_trabalho_e164\", e164).execute())",
      "                                   .execute())")),
    ("C-P2a a pergunta volta a cada mensagem", "app/services/atalho/entrada.py",
     "    if pendente and not trocar:\n",
     "    if pendente and not trocar and _escolha(texto, membros):\n",
     "test_qual_corretora_vai_uma_vez"),
    ("C-P2b o envio não conta no teto", "app/services/atalho/envio.py",
     "    if not await asyncio.to_thread(EST.reservar_envios, db, tel, len(textos)):\n",
     "    if False:\n",
     "test_toda_mensagem_que_sai_conta_no_teto"),
    ("C-P3 a pergunta pendente some (como Redis fora)", "app/services/atalho/entrada.py",
     "    guardado = await asyncio.to_thread(EST.ler, db, telefone)\n",
     "    guardado = {}\n",
     "test_sem_redis_trocar_corretora_funciona"),
    ("C-P4 a chave estranha volta a derrubar", "app/services/atalho/entrada.py",
     "    if not isinstance(chave, dict):        # P4 (red team): `key` como lista/texto → ignorado, nunca um 500\n"
     "        return None, \"payload_invalido\"\n",
     "",
     "test_formato_estranho_da_chave"),
    ("C-P5 sem corte do texto", "app/services/atalho/entrada.py",
     "    if isinstance(texto, str) and len(texto) > LIMITE_DO_TEXTO:\n",
     "    if False:\n",
     "test_texto_enorme_e_cortado"),
]


def _mutar() -> int:
    falhas = 0
    for mut in MUTACOES:
        rotulo, arquivo, de, para, teste = mut[:5]
        trocas = [(arquivo, de, para)] + list(mut[5:])
        copias = {}
        try:
            for arq, d, p in trocas:
                caminho = BACKEND / arq
                if caminho not in copias:
                    copias[caminho] = caminho.read_bytes()
                atual = caminho.read_bytes().decode("utf-8")
                assert atual.count(d.replace("\n", "\r\n")) + atual.count(d) >= 1, \
                    f"{rotulo}: o trecho não está em {arq}"
                trocado = atual.replace(d.replace("\n", "\r\n"), p.replace("\n", "\r\n"), 1) \
                    if d.replace("\n", "\r\n") in atual else atual.replace(d, p, 1)
                assert trocado != atual, f"{rotulo}: a troca não mudou {arq}"
                caminho.write_bytes(trocado.encode("utf-8"))
            r = subprocess.run([sys.executable, "-m", "pytest", __file__, "-q", "-p", "no:cacheprovider",
                                "-k", teste], cwd=str(BACKEND), capture_output=True, text=True)
            vermelho = r.returncode != 0
            print(f"{rotulo}: {'VERMELHO (o guarda pegou)' if vermelho else 'MUTACAO NAO PEGOU'} — {teste}")
            falhas += 0 if vermelho else 1
        finally:
            # 🔴 restaura POR CÓPIA DOS BYTES — e confere (o arquivo volta idêntico, byte a byte)
            for caminho, original in copias.items():
                caminho.write_bytes(original)
                assert caminho.read_bytes() == original, f"{rotulo}: {caminho.name} não voltou igual"
    return falhas


if __name__ == "__main__" and "--mutar" in sys.argv:
    sys.exit(_mutar())
