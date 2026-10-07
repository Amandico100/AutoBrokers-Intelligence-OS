# -*- coding: utf-8 -*-
"""SPEC-133-A F1 · a porta de entrada do canal de cotação.

🔴 O FIO (protocolo §5 ②, CLAUDE.md §9.4): `TestClient` na ROTA REAL `POST /api/v1/webhook/evolution-go/{token}` →
`_resolve_webhook_integration` real (hash do token) → o desvio do canal → `_handle_evolution_like_inbound` real →
`MessageBufferService` real (Redis em memória) → o motor REAL do buffer (`processar_buffers_prontos`) →
`process_whatsapp_message_background` real → `canal.entrada.turno` real → repositório real (banco em memória) →
`conversa.responder` (DUBLÊ — é da F2) → `envio.enviar` real → `send_message` (DUBLÊ na borda).
Dublê SÓ na borda: banco (PostgREST em memória), Redis, `send_message` e a conversa da F2.

O elo: "o canal só fala com quem foi convidado PORQUE o filtro roda antes de qualquer envio" — os 5 controles dão ZERO
`send_message` pelo webhook real. E a não-regressão: o mesmo payload numa integração `observer` de CORRETORA continua
sendo consumido pelo `observer_tap`, e a entrada do canal nunca é chamada.
"""
from __future__ import annotations

import asyncio
import copy
import json
import os
import sys
import types
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pytest

AQUI = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(AQUI)
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

os.environ.setdefault("OPENAI_API_KEY", "test-key")
if not os.environ.get("PORTAL_VAULT_KEY"):
    from cryptography.fernet import Fernet

    os.environ["PORTAL_VAULT_KEY"] = Fernet.generate_key().decode()

CANAL = "aaaaaaaa-0000-4000-8000-000000000001"
CANAL_B = "aaaaaaaa-0000-4000-8000-000000000002"      # um 2º canal (dois tenants)
CORRETORA = "bbbbbbbb-0000-4000-8000-000000000001"
TOKEN_CANAL = "tok-canal-" + "x" * 40
TOKEN_CORRETORA = "tok-corretora-" + "y" * 40
#: DDD 00 não existe — nenhum telefone real (CLAUDE.md §13 · pacote)
CONVIDADO = "5500999990001"
ESTRANHO = "5500999990002"
LINHA_DA_CORRETORA = "5500988887777"                  # pareada como "+550088887777" (sem o 9, como o WhatsApp grava)
LIMITADO = "5500999990003"

FIXTURE = os.path.join(AQUI, "fixtures", "canal_evolution_go_oi.json")


# =====================================================================================================================
# O BANCO em memória (PostgREST: table/select/eq/in_/limit/order/insert/upsert/update/execute)
# =====================================================================================================================
class _Resp:
    def __init__(self, data):
        self.data = data


class _Consulta:
    def __init__(self, banco: "Banco", tabela: str):
        self.banco, self.tabela = banco, tabela
        self.filtros: List[tuple] = []
        self.op, self.carga, self.conflito, self.lim = "select", None, "", None

    def select(self, *_a, **_k):
        self.op = "select"
        return self

    def eq(self, coluna, valor):
        if not (self.banco.ignora_filtro_de_empresa and coluna == "company_id"):
            self.filtros.append(("eq", coluna, valor))
        return self

    def in_(self, coluna, valores):
        self.filtros.append(("in", coluna, [str(v) for v in valores]))
        return self

    def limit(self, n):
        self.lim = n
        return self

    def order(self, *_a, **_k):
        return self

    def insert(self, carga):
        self.op, self.carga = "insert", carga
        return self

    def upsert(self, carga, on_conflict=""):
        self.op, self.carga, self.conflito = "upsert", carga, on_conflict
        return self

    def update(self, carga):
        self.op, self.carga = "update", carga
        return self

    def _casa(self, linha):
        for tipo, col, val in self.filtros:
            atual = linha.get(col)
            if tipo == "eq" and not (atual == val or str(atual) == str(val)):
                return False
            if tipo == "in" and str(atual) not in val:
                return False
        return True

    def execute(self):
        linhas = self.banco.dados.setdefault(self.tabela, [])
        self.banco.escritas.append((self.op, self.tabela)) if self.op != "select" else None
        if self.op == "select":
            achadas = [dict(x) for x in linhas if self._casa(x)]
            return _Resp(achadas[: self.lim] if self.lim else achadas)
        if self.op == "insert":
            novas = self.carga if isinstance(self.carga, list) else [self.carga]
            for n in novas:
                linhas.append(dict(n))
            return _Resp([dict(n) for n in novas])
        if self.op == "upsert":
            chaves = [c.strip() for c in self.conflito.split(",") if c.strip()]
            alvo = next((x for x in linhas if all(str(x.get(c)) == str(self.carga.get(c)) for c in chaves)), None)
            if alvo is None:
                linhas.append(dict(self.carga))
                return _Resp([dict(self.carga)])
            alvo.update(self.carga)
            return _Resp([dict(alvo)])
        if self.op == "update":
            feitas = [x for x in linhas if self._casa(x)]
            for x in feitas:
                x.update(self.carga)
            return _Resp([dict(x) for x in feitas])
        raise AssertionError(self.op)


class Banco:
    def __init__(self):
        self.dados: Dict[str, List[dict]] = {}
        self.escritas: List[tuple] = []
        self.ignora_filtro_de_empresa = False

    def table(self, nome):
        return _Consulta(self, nome)

    @property
    def client(self):
        return self


class SupabaseFalso:
    def __init__(self, banco):
        self.client = banco


# =====================================================================================================================
# O REDIS em memória (o que o buffer e o dedup usam) · o envio · a conversa da F2
# =====================================================================================================================
class _Pipe:
    def __init__(self, r):
        self.r, self.ops = r, []

    def get(self, k):
        self.ops.append(("get", k))

    def delete(self, k):
        self.ops.append(("delete", k))

    async def execute(self):
        out = []
        for op, k in self.ops:
            out.append(self.r.dados.get(k) if op == "get" else self.r.dados.pop(k, None))
        return out


class RedisFalso:
    def __init__(self):
        self.dados: Dict[str, Any] = {}

    async def set(self, k, v, ex=None, nx=False):
        if nx and k in self.dados:
            return None
        self.dados[k] = v
        return True

    async def get(self, k):
        return self.dados.get(k)

    async def setex(self, k, _ttl, v):
        self.dados[k] = v

    async def hincrby(self, k, campo, n=1):
        self.dados.setdefault(k, {})
        self.dados[k][campo] = self.dados[k].get(campo, 0) + n

    async def expire(self, *_a, **_k):
        return True

    def pipeline(self):
        return _Pipe(self)


class EnvioFalso:
    def __init__(self):
        self.enviados: List[dict] = []

    def send_message(self, to_number=None, text=None, integration=None, *, bloco_unico=False):
        self.enviados.append({"para": to_number, "texto": text, "empresa": (integration or {}).get("company_id"),
                              "bloco_unico": bloco_unico})
        return True

    def send_presence(self, *_a, **_k):
        return True


@dataclass
class Resposta:
    baloes: List[str]
    estado: dict
    disparar: Optional[dict] = None


class ConversaFalsa:
    """A F2 escreve a conversa de verdade; aqui só o CONTRATO §3 (responder → Resposta)."""

    def __init__(self):
        self.chamadas: List[dict] = []
        self.proxima: Optional[Resposta] = None

    async def responder(self, db, company_id, telefone_e164, texto, midia, estado, *, config):
        self.chamadas.append({"company_id": company_id, "tel": telefone_e164, "texto": texto, "estado": dict(estado),
                              "config_tem_canal": "canal" in (config or {})})
        if self.proxima is not None:
            r, self.proxima = self.proxima, None
            return r
        return Resposta(baloes=["Oi! Eu sou o Quem Cobra Menos.", "Posso cotar o seu seguro?"],
                        estado={"passo": "consentimento", "n": len(self.chamadas)})


class CotacaoFalsa:
    def __init__(self):
        self.disparos: List[dict] = []

    async def disparar(self, db, company_id, telefone_e164, perfil, estado):
        self.disparos.append({"company_id": company_id, "tel": telefone_e164, "perfil": dict(perfil)})
        return "run-1"


# =====================================================================================================================
# O MUNDO — o motor de verdade, com as bordas dubladas
# =====================================================================================================================
def _hash(tok):
    from app.services.whatsapp.channel_security import webhook_token_hash

    return webhook_token_hash(tok)


def _integracoes():
    return [
        {"id": "int-canal", "company_id": CANAL, "provider": "evolution-go", "purpose": "observer", "is_active": True,
         "channel_status": "connected", "identifier": "ab-obs-aaaaaaaa00-1", "base_url": "http://evolution.invalid",
         "webhook_token_hash": _hash(TOKEN_CANAL), "paired_phone_e164": "+550090000000"},
        {"id": "int-corretora", "company_id": CORRETORA, "provider": "evolution-go", "purpose": "observer",
         "is_active": True, "channel_status": "connected", "identifier": "ab-obs-bbbbbbbb00-1",
         "base_url": "http://evolution.invalid", "webhook_token_hash": _hash(TOKEN_CORRETORA),
         "paired_phone_e164": "+550088887777"},
    ]


class ServicoDeIntegracao:
    def __init__(self, banco):
        self.banco = banco

    def _todas(self):
        return self.banco.dados.get("integrations", [])

    def get_integration_by_webhook_token(self, tok):
        h = _hash(tok)
        return next((dict(x) for x in self._todas() if x.get("webhook_token_hash") == h), None)

    def get_integration_by_id(self, ident):
        return next((dict(x) for x in self._todas() if x.get("id") == ident and x.get("is_active")), None)

    def get_integration_by_phone(self, _p):
        return None


class BufferDoTeste:
    """O `MessageBufferService` REAL por baixo; só a JANELA de espera (relógio) e a trava distribuída são do teste."""

    def __init__(self, real):
        self.real = real

    async def should_process(self, _chave):
        return True

    async def get_and_clear_buffer(self, chave):
        return await self.real.get_and_clear_buffer(chave)

    def get_combined_message(self, buffer):
        return self.real.get_combined_message(buffer)

    async def abrir_turno(self, _escopo, _phone):
        return "trava-do-teste"

    async def fechar_turno(self, *_a):
        return None


import socket as _socket

_CONNECT_REAL = _socket.socket.connect
_CONNECT_EX_REAL = _socket.socket.connect_ex


def _loopback(destino) -> bool:
    return isinstance(destino, tuple) and str(destino[0]) in ("127.0.0.1", "::1", "localhost")


def _sem_rede(self, destino, *a, **k):  # noqa: ANN001
    """O laço de eventos do Windows abre um par de sockets no LOOPBACK (o self-pipe); fora dele, é rede."""
    if _loopback(destino):
        return _CONNECT_REAL(self, destino, *a, **k)
    raise AssertionError(f"o teste tentou a REDE ({destino!r}) — só a borda dublada é permitida")


def _sem_rede_ex(self, destino, *a, **k):  # noqa: ANN001
    if _loopback(destino):
        return _CONNECT_EX_REAL(self, destino, *a, **k)
    raise AssertionError(f"o teste tentou a REDE ({destino!r}) — só a borda dublada é permitida")


@pytest.fixture
def mundo(monkeypatch):
    import socket

    import app.core.database as _database
    import app.core.redis as _redis

    # ⛔ a rede fechada: nenhum caminho deste teste alcança banco, Redis ou Evolution de verdade
    monkeypatch.setattr(socket.socket, "connect", _sem_rede)
    monkeypatch.setattr(socket.socket, "connect_ex", _sem_rede_ex)

    banco, redis = Banco(), RedisFalso()
    sup = SupabaseFalso(banco)
    monkeypatch.setattr(_database, "get_supabase_client", lambda: sup)

    async def _redis_async():
        return redis

    monkeypatch.setattr(_redis, "get_async_redis_client", _redis_async)

    import app.api.webhook as w   # o MESMO módulo do produto

    from app.services.message_buffer_service import MessageBufferService

    servico_buffer = MessageBufferService(redis)

    async def _buffer():
        return servico_buffer

    monkeypatch.setattr(w, "supabase", sup)
    monkeypatch.setattr(w, "integration_service", ServicoDeIntegracao(banco))
    monkeypatch.setattr(w, "get_async_redis_client", _redis_async)
    monkeypatch.setattr(w, "get_message_buffer_service", _buffer)

    async def _nada(*_a, **_k):
        return None

    monkeypatch.setattr(w, "_registrar_retorno_de_cobranca", _nada)

    import app.services.atlas.attendance_capture as _captura

    async def _agente_desligado(*_a, **_k):
        return False

    monkeypatch.setattr(_captura, "attendance_agent_active", _agente_desligado)

    import app.services.atlas.observer_intake as _obs

    taps: List[str] = []
    tap_real = _obs.observer_tap

    async def _espiao(integration, body):
        taps.append(str((integration or {}).get("company_id")))
        return await tap_real(integration, body)

    monkeypatch.setattr(_obs, "observer_tap", _espiao)

    # o ramo `fromMe`/grupo do pipeline (espelho no chat, pausa da IA, palavra da equipe) — espiões: no canal, NADA
    import app.services.atlas.espelho_chat as _espelho
    import app.services.dispatch_router as _dispatch

    efeitos: List[str] = []

    def _espiao_de(nome):
        async def _f(*_a, **_k):
            efeitos.append(nome)
            return None
        return _f

    for _nome in ("espelhar_no_chat", "pausar_por_intervencao_humana"):
        monkeypatch.setattr(_espelho, _nome, _espiao_de(_nome))
    monkeypatch.setattr(_dispatch, "ler_palavra_da_equipe", _espiao_de("ler_palavra_da_equipe"))
    monkeypatch.setattr(_dispatch, "note_manual_outbound", _espiao_de("note_manual_outbound"))

    envio = EnvioFalso()
    import app.services.whatsapp_service as _ws

    monkeypatch.setattr(_ws, "get_whatsapp_service", lambda: envio)
    monkeypatch.setattr(w, "whatsapp_service", envio)

    import app.services.canal as _pacote
    import app.services.canal.envio as _envio_do_canal
    import app.services.canal.repositorio as repo

    monkeypatch.setattr(_envio_do_canal, "PAUSA_ENTRE_BALOES_S", 0)
    repo._CACHE_DO_TIPO.clear()
    conversa, cotacao = ConversaFalsa(), CotacaoFalsa()
    mod_conversa = types.ModuleType("app.services.canal.conversa")
    mod_conversa.responder, mod_conversa.Resposta = conversa.responder, Resposta
    # a regra de "quem está começando" é UMA, da conversa real (F2) — a entrada não tem cópia (costura 133-A)
    from app.services.canal.conversa import abre_conversa_nova as _abre

    mod_conversa.abre_conversa_nova = _abre
    mod_cotacao = types.ModuleType("app.services.canal.cotacao")
    mod_cotacao.disparar = cotacao.disparar
    monkeypatch.setitem(sys.modules, "app.services.canal.conversa", mod_conversa)
    monkeypatch.setitem(sys.modules, "app.services.canal.cotacao", mod_cotacao)
    monkeypatch.setattr(_pacote, "conversa", mod_conversa, raising=False)
    monkeypatch.setattr(_pacote, "cotacao", mod_cotacao, raising=False)

    banco.dados["companies"] = [{"id": CANAL, "company_kind": "platform_canal"},
                                {"id": CANAL_B, "company_kind": "platform_canal"},
                                {"id": CORRETORA, "company_kind": "client"}]
    banco.dados["integrations"] = _integracoes()
    banco.dados["canal_convidados"] = [
        {"id": "c1", "company_id": CANAL, "telefone": CONVIDADO, "apelido": "Teste 1", "ativo": True, "limite_dia": None},
        {"id": "c2", "company_id": CANAL, "telefone": LINHA_DA_CORRETORA, "ativo": True, "limite_dia": None},
        {"id": "c3", "company_id": CANAL, "telefone": LIMITADO, "ativo": True, "limite_dia": 1},
        {"id": "c4", "company_id": CANAL_B, "telefone": ESTRANHO, "ativo": True, "limite_dia": None},
    ]

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.core.rate_limit import limiter

    app = FastAPI()
    app.state.limiter = limiter
    app.include_router(w.router)
    cliente = TestClient(app)

    def postar(corpo, token=TOKEN_CANAL):
        r = cliente.post(f"/api/v1/webhook/evolution-go/{token}", json=corpo)
        assert r.status_code == 200, r.text
        return r.json()

    def drenar():
        from app.tasks.buffer_processor import processar_buffers_prontos

        chaves = [k for k in list(redis.dados) if str(k).startswith("whatsapp_buffer:")]
        return asyncio.run(processar_buffers_prontos(chaves, BufferDoTeste(servico_buffer),
                                                     w.process_whatsapp_message_background, paralelismo=2))

    return types.SimpleNamespace(w=w, banco=banco, redis=redis, envio=envio, conversa=conversa, cotacao=cotacao,
                                 taps=taps, efeitos=efeitos, postar=postar, drenar=drenar, repo=repo)


def evento(*, tel=CONVIDADO, texto="oi", from_me=False, grupo=False, ident="3EB0C0A0000000000000F1"):
    with open(FIXTURE, encoding="utf-8") as f:
        corpo = copy.deepcopy(json.load(f)["evento"])
    info = corpo["data"]["Info"]
    jid = "120363000000000001@g.us" if grupo else f"{tel}@s.whatsapp.net"
    info.update({"Chat": jid, "Sender": f"{tel}@s.whatsapp.net", "IsFromMe": from_me, "IsGroup": grupo, "ID": ident})
    corpo["data"]["Message"] = {"conversation": texto}
    return corpo


# =====================================================================================================================
# 🔴 O FIO
# =====================================================================================================================
def test_o_fio_da_entrada(mundo):
    resp = mundo.postar(evento())
    assert resp.get("status") == "buffered", resp            # NÃO morreu no observer
    assert mundo.taps == [], "o canal não pode passar pelo observer_tap"
    resumo = mundo.drenar()
    assert resumo["processadas"] == 1, resumo
    assert len(mundo.conversa.chamadas) == 1
    ch = mundo.conversa.chamadas[0]
    assert ch["company_id"] == CANAL and ch["tel"] == CONVIDADO and ch["texto"] == "oi" and ch["estado"] == {}
    assert ch["config_tem_canal"], "a conversa recebe a config do multicálculo (seção canal)"
    assert [e["texto"] for e in mundo.envio.enviados] == ["Oi! Eu sou o Quem Cobra Menos.", "Posso cotar o seu seguro?"]
    assert {e["para"] for e in mundo.envio.enviados} == {CONVIDADO}, "os balões vão para o MESMO telefone"
    assert {e["empresa"] for e in mundo.envio.enviados} == {CANAL}, "pela integração do CANAL"
    assert all(e["bloco_unico"] for e in mundo.envio.enviados), "balão pronto não é re-picotado"
    conv = [x for x in mundo.banco.dados["canal_conversas"] if x["telefone"] == CONVIDADO]
    assert len(conv) == 1 and conv[0]["company_id"] == CANAL
    assert "consentimento" not in conv[0]["estado_cifrado"], "o estado é CIFRADO em repouso"
    assert mundo.repo.carregar_estado(mundo.banco, CANAL, CONVIDADO) == {"passo": "consentimento", "n": 1}
    assert conv[0]["enviadas_no_dia"] == 2
    # 2º turno: o estado volta para a conversa
    mundo.postar(evento(texto="sim", ident="3EB0C0A0000000000000F2"))
    mundo.drenar()
    assert mundo.conversa.chamadas[1]["estado"] == {"passo": "consentimento", "n": 1}
    assert len(mundo.envio.enviados) == 4


@pytest.mark.parametrize("caso", ["nao_convidado", "numero_de_corretora", "from_me", "grupo"])
def test_os_controles_dao_zero_envio(mundo, caso):
    corpo = {"nao_convidado": evento(tel=ESTRANHO),
             # a linha da corretora chega COM o 9 e está pareada SEM ele: as duas formas casam
             "numero_de_corretora": evento(tel=LINHA_DA_CORRETORA),
             "from_me": evento(from_me=True),
             "grupo": evento(grupo=True)}[caso]
    mundo.postar(corpo)
    mundo.drenar()
    assert mundo.envio.enviados == [], caso
    assert mundo.conversa.chamadas == [], caso
    assert mundo.taps == [], "nem o controle passa pelo observer"
    assert not any(t == "conversations" for _op, t in mundo.banco.escritas), "fromMe no canal não espelha no chat"
    assert mundo.efeitos == [], f"o canal não espelha, não pausa e não lê palavra de equipe: {mundo.efeitos}"


def test_acima_do_limite_so_um_aviso(mundo):
    hoje = mundo.repo.hoje()
    mundo.banco.dados["canal_conversas"] = [{"company_id": CANAL, "telefone": LIMITADO, "estado_cifrado": None,
                                            "cotacoes_dia": hoje, "cotacoes_no_dia": 1, "enviadas_dia": None,
                                            "enviadas_no_dia": 0, "aviso_limite_dia": None}]
    mundo.postar(evento(tel=LIMITADO))
    mundo.drenar()
    mundo.postar(evento(tel=LIMITADO, texto="oi de novo", ident="3EB0C0A0000000000000F3"))
    mundo.drenar()
    assert mundo.conversa.chamadas == []
    assert len(mundo.envio.enviados) == 1 and mundo.envio.enviados[0]["para"] == LIMITADO
    assert "Amanhã" in mundo.envio.enviados[0]["texto"]


def test_conversa_encerrada_acima_do_limite_recebe_o_aviso(mundo):
    """Quem terminou (etapa de recomeço da F2) e já gastou o limite: o aviso, e a conversa nem é chamada."""
    mundo.repo.salvar_estado(mundo.banco, CANAL, LIMITADO, {"etapa": "encerrado"})
    mundo.repo._gravar_contadores(mundo.banco, CANAL, LIMITADO, {"cotacoes_dia": mundo.repo.hoje(),
                                                                   "cotacoes_no_dia": 1})
    mundo.postar(evento(tel=LIMITADO, texto="nova cotação"))
    mundo.drenar()
    assert mundo.conversa.chamadas == [] and len(mundo.envio.enviados) == 1
    assert mundo.envio.enviados[0]["texto"].startswith("Por hoje")


def test_o_teto_de_mensagens_cala(mundo):
    mundo.banco.dados["canal_conversas"] = [{"company_id": CANAL, "telefone": CONVIDADO, "estado_cifrado": None,
                                            "cotacoes_dia": None, "cotacoes_no_dia": 0, "enviadas_dia": mundo.repo.hoje(),
                                            "enviadas_no_dia": mundo.repo.teto_de_mensagens(None),
                                            "aviso_limite_dia": None}]
    mundo.postar(evento())
    mundo.drenar()
    assert mundo.envio.enviados == [] and mundo.conversa.chamadas == []


def test_o_perfil_completo_dispara_a_cotacao_e_conta(mundo):
    mundo.conversa.proxima = Resposta(baloes=["Calculando…"], estado={"passo": "calculando"},
                                      disparar={"placa": "AAA0A00"})
    mundo.postar(evento())
    mundo.drenar()
    assert mundo.cotacao.disparos == [{"company_id": CANAL, "tel": CONVIDADO, "perfil": {"placa": "AAA0A00"}}]
    assert mundo.repo.cotacoes_de_hoje(mundo.banco, CANAL, CONVIDADO) == 1


def test_no_meio_da_conversa_o_limite_barra_so_o_disparo(mundo):
    mundo.repo.salvar_estado(mundo.banco, CANAL, LIMITADO, {"etapa": "uso"})
    mundo.repo._gravar_contadores(mundo.banco, CANAL, LIMITADO, {"cotacoes_dia": mundo.repo.hoje(),
                                                                   "cotacoes_no_dia": 1})
    mundo.conversa.proxima = Resposta(baloes=["Ok!"], estado={"passo": "calculando"}, disparar={"placa": "AAA0A00"})
    mundo.postar(evento(tel=LIMITADO))
    mundo.drenar()
    assert len(mundo.conversa.chamadas) == 1, "quem está no meio continua a conversa"
    assert mundo.cotacao.disparos == [], "mas a 2ª cotação do dia não sai"
    assert [e["texto"] for e in mundo.envio.enviados][-1].startswith("Por hoje")


def test_nao_regressao_o_observer_da_corretora_continua_consumindo(mundo):
    resp = mundo.postar(evento(tel=ESTRANHO), token=TOKEN_CORRETORA)
    assert resp == {"status": "observed"}, resp
    assert mundo.taps == [CORRETORA]
    assert not [k for k in mundo.redis.dados if str(k).startswith("whatsapp_buffer:")], "nada chega ao buffer"
    assert mundo.envio.enviados == [] and mundo.conversa.chamadas == []


# =====================================================================================================================
# DOIS TENANTS e o CINTO
# =====================================================================================================================
def test_dois_tenants_o_canal_a_nao_le_o_b(mundo):
    repo, banco = mundo.repo, mundo.banco
    assert repo.convidado(banco, CANAL, CONVIDADO) is not None
    assert repo.convidado(banco, CANAL, ESTRANHO) is None          # é convidado do B, não do A
    assert repo.convidado(banco, CANAL_B, ESTRANHO) is not None    # CONTROLE: o B lê o dele
    assert {x["telefone"] for x in repo.listar_convidados(banco, CANAL_B)} == {ESTRANHO}
    repo.salvar_estado(banco, CANAL_B, CONVIDADO, {"de": "B"})
    assert repo.carregar_estado(banco, CANAL, CONVIDADO) == {}
    # o CINTO: um filtro de empresa que FALHA no banco não deixa a linha do B passar
    banco.ignora_filtro_de_empresa = True
    assert repo.convidado(banco, CANAL, ESTRANHO) is None
    assert {x["telefone"] for x in repo.listar_convidados(banco, CANAL_B)} == {ESTRANHO}
    assert repo.carregar_estado(banco, CANAL, CONVIDADO) == {}


def test_o_telefone_tem_uma_forma_so(mundo):
    repo = mundo.repo
    assert repo.canonico("550099990001") == "5500999990001"        # conta antiga, sem o 9
    assert repo.canonico("5500999990001@s.whatsapp.net") == "5500999990001"
    assert repo.canonico("+55 (00) 99999-0001") == "5500999990001"
    assert repo.canonico("550033330001") == "550033330001"         # fixo não ganha 9
    assert repo.canonico("123") == "" and repo.mascarar(CONVIDADO) == "...0001"
    assert repo.convidado(mundo.banco, CANAL, "550099990001") is not None


def test_envio_recusa_empresa_que_nao_e_o_canal(mundo):
    n = asyncio.run(__import__("app.services.canal.envio", fromlist=["enviar"]).enviar(
        mundo.banco, CORRETORA, CONVIDADO, ["oi"]))
    assert n == 0 and mundo.envio.enviados == []


def test_consentimento_e_lead(mundo):
    repo, banco = mundo.repo, mundo.banco
    repo.registrar_consentimento(banco, CANAL, CONVIDADO, aceito=True, versao_do_texto="v1")
    repo.registrar_consentimento(banco, CANAL, CONVIDADO, aceito=False, versao_do_texto="v1")
    assert [x["aceito"] for x in banco.dados["canal_consentimentos"]] == [True, False]   # append-only
    repo.registrar_lead(banco, CANAL, CONVIDADO, primeiro_nome="Ana")
    repo.registrar_lead(banco, CANAL, CONVIDADO, pedido_id="pedido-1")
    (lead,) = banco.dados["canal_leads"]
    assert lead["primeiro_nome"] == "Ana" and lead["pedido_id"] == "pedido-1"
    with pytest.raises(ValueError):
        repo.registrar_consentimento(banco, CANAL, CONVIDADO, aceito=True, versao_do_texto="")


# =====================================================================================================================
# O COMANDO do Founder e a MIGRATION
# =====================================================================================================================
def test_o_comando_dos_convidados(mundo, capsys):
    from app.services.canal import comando_convidados as cmd

    mundo.banco.dados["companies"] = [x for x in mundo.banco.dados["companies"] if x["id"] != CANAL_B]
    assert cmd.main(["--adicionar", "550099990009", "--apelido", "Teste 9"], db=mundo.banco) == 0
    assert cmd.main(["--listar"], db=mundo.banco) == 0
    assert cmd.main(["--remover", "5500999990009"], db=mundo.banco) == 0
    saida = capsys.readouterr().out
    assert "5500999990009" not in saida and "550099990009" not in saida, "o telefone nunca sai inteiro"
    assert "...0009" in saida
    linha = next(x for x in mundo.banco.dados["canal_convidados"] if x["telefone"] == "5500999990009")
    assert linha["company_id"] == CANAL and linha["apelido"] == "Teste 9" and linha["ativo"] is False
    assert cmd.main(["--adicionar", "123"], db=mundo.banco) == 2


def test_a_migration_tem_apply_verify_rollback_e_rls():
    caminho = os.path.join(BACKEND, "supabase", "migrations", "20261007_01_spec133a_canal.sql")
    sql = open(caminho, encoding="utf-8").read()
    for marca in ("APPLY:", "VERIFY (read-only", "VERIFY comportamental", "ROLLBACK", "EXPAND-FIRST"):
        assert marca in sql, marca
    corpo = "\n".join(l for l in sql.splitlines() if not l.lstrip().startswith("--"))
    for t in ("canal_convidados", "canal_consentimentos", "canal_leads", "canal_conversas"):
        assert f"create table if not exists public.{t}" in corpo
        assert f"alter table public.{t}" in corpo and "enable row level security" in corpo
        assert f"revoke all on table public.{t}" in corpo
        assert "company_id      uuid not null references public.companies(id)" in corpo or \
               "company_id       uuid not null references public.companies(id)" in corpo
    assert "create policy" not in corpo.lower(), "RLS SEM policy (só o backend lê)"
    assert "drop table" not in corpo.lower() and "delete from" not in corpo.lower()
