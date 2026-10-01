# -*- coding: utf-8 -*-
"""SPEC-123 · CONSERTO ÚNICO · parte Z — o Vigia e o Sentinela alinhados ao roteador.

Z1 · O Vigia VENCE a espera SEGURADA (a URA fechou com a pergunta ao segurado no ar,
     `_segurar_para_retomar`). Durante a espera, um 2º acionamento para o MESMO número da seguradora
     entrou na fila (`start_live_dispatch` → `dispatch_already_active`, conserto X3). Ao desistir, o
     Vigia NÃO esvaziava a fila — o 2º pedido ficava parado até a fila expirar (2 h). Agora ele a
     libera como o fim de sessão do roteador faz (`_start_next_in_queue`).
Z2 · No teto do PONTO A (`TETO_DO_DESTRAVADOR_NO_PONTO_A`) o roteador volta ao turno de HOJE (o
     cérebro de produção); o Sentinela lia o `d=None` do mesmo teto como PESSOA. Agora segue o de hoje.

O FIO (dublê só na BORDA — Redis, banco, WhatsApp, o destravador/modelo):
  Z1 · try_route_insurer_inbound (MOTOR real, telas do ACERVO) → _segurar_para_retomar →
       start_live_dispatch (2º pedido) → enqueue_dispatch (o que `insurer_dispatch_tool` faz com
       `dispatch_already_active`) → check_dispatch_watchdog (a varredura REAL) → diagnose →
       _segurar_ou_desistir → save_active_dispatch → _start_next_in_queue → start_live_dispatch.
  Z2 · _sentinela_recover → _tentativa_do_destravador → (teto) `_adaptive_reply` →
       invocar_com_reserva("dispatch") (DUBLÊ) → guard_human_phase_reply → envio de hoje.

MUTAÇÕES (por cópia): sem a liberação da fila no Vigia → Z1 VERMELHO; sem o
`cabe_mais_um_no_ponto_a` no Sentinela → Z2 VERMELHO.
"""
from __future__ import annotations

import asyncio
import copy
import json
import os
import re
import sys
import types
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.environ.setdefault("INSURER_DISPATCH_LIVE", "false")
os.environ["DISPATCH_MIRROR"] = "0"

FIO_Z = (
    "app.services.corridor_playbooks",
    "app.services.insurer_dispatch_service",
    "app.services.acao_do_cerebro",
    "app.services.o_grupo_so_o_que_importa",
    "app.services.dispatch_router",
    "app.tasks.dispatch_watchdog",
)
_NADA = object()


def _carregar_fio() -> dict:
    """O fio importado UMA vez, coerente — e o `sys.modules` devolvido intacto (P-121-28)."""
    import importlib

    antes = dict(sys.modules)
    pais = {}
    for nome in FIO_Z:
        pai, _, filho = nome.rpartition(".")
        p = sys.modules.get(pai)
        pais[nome] = (p, filho, getattr(p, filho, _NADA) if p is not None else _NADA)
    try:
        for nome in FIO_Z:
            sys.modules.pop(nome, None)
        return {nome: importlib.import_module(nome) for nome in FIO_Z}
    finally:
        for nome in [n for n in sys.modules if n not in antes and (n == "app" or n.startswith("app."))]:
            novo = sys.modules.pop(nome)
            pai, _, filho = nome.rpartition(".")
            p = sys.modules.get(pai)
            if p is not None and getattr(p, filho, None) is novo:
                delattr(p, filho)
        for nome in FIO_Z:
            if nome in antes:
                sys.modules[nome] = antes[nome]
            else:
                sys.modules.pop(nome, None)
            p, filho, attr = pais[nome]
            if p is None:
                continue
            if attr is _NADA:
                if hasattr(p, filho):
                    delattr(p, filho)
            else:
                setattr(p, filho, attr)


FIO = _carregar_fio()
CP = FIO["app.services.corridor_playbooks"]
D = FIO["app.services.insurer_dispatch_service"]
AC = FIO["app.services.acao_do_cerebro"]
G = FIO["app.services.o_grupo_so_o_que_importa"]
R = FIO["app.services.dispatch_router"]
W = FIO["app.tasks.dispatch_watchdog"]

CORPUS = Path(RAIZ) / "tests" / "corpus" / "telas_reais"
URA = "5511999990000"
CLIENTE = "5548988887777"
CLIENTE_B = "5548911112222"
EMPRESA_A = "11111111-1111-1111-1111-111111111111"
REF_ALLIANZ = "allianz-residencial-whatsapp@v1"
REF_PORTO = "porto-auto-whatsapp@v1"


def telas(arquivo: str) -> list:
    return [json.loads(l)["text"] for l in (CORPUS / f"{arquivo}.jsonl").read_text(encoding="utf-8").splitlines()]


def tela_real(arquivo: str, padrao: str) -> str:
    for t in telas(arquivo):
        if re.search(padrao, D._norm_text(t)):
            return t
    raise AssertionError(f"o corpus {arquivo} não tem tela que case {padrao!r}")


def _caso_do_cerebro(chave: str) -> dict:
    for linha in (Path(RAIZ) / "tests/corpus/bancada/cerebro/casos.jsonl").read_text(encoding="utf-8").splitlines():
        c = json.loads(linha)
        if c["chave"] == chave:
            return c
    raise AssertionError(chave)


# --------------------------------------------------------------------------- as telas (do ACERVO)
RES = telas("allianz-residencial")
_PB_ALLIANZ = CP.get_playbook(REF_ALLIANZ)
#: a tela que pede um dado que a ficha não tem — a MESMA escolha de `test_spec123_ida_e_volta_retomada`
PEDE = next(t for t in RES if CP.match_ura_step(_PB_ALLIANZ, t, subservice="encanador") is None
            and D.responder_da_ficha(_PB_ALLIANZ, t, {}).get("motivo") == "sem_dado_na_ficha"
            and not str(D.responder_da_ficha(_PB_ALLIANZ, t, {}).get("slot") or "").endswith("_opcao")
            and CP._COMO_PERGUNTAR.get(str(D.responder_da_ficha(_PB_ALLIANZ, t, {}).get("slot") or "")))
SLOT = str(D.responder_da_ficha(_PB_ALLIANZ, PEDE, {}).get("slot") or "")
ENCERRA_ALLIANZ = tela_real("allianz-residencial", r"encerrado por inatividade")
#: 📊 uma tela REAL sem passo (grupo A da bancada da 122) — a mesma da ligação do destravador.
TELA_SEM_PASSO = _caso_do_cerebro("cer-A-porto-019")["entrada"]["tela"]

#: valores de TESTE (nada de PII; §13.9)
SLOTS_ALLIANZ = {"titular_cpf": "11122233344", "endereco_numero": "100", "telefone_contato": "48999998888",
                 "ramo_da_apolice": "resi", "problema_descricao": "vazamento no banheiro",
                 "periodo_preferido": "manha", "vazamento_local": "banheiro", "agua_escorrendo": "sim",
                 "risco_confirmado_registro_fechado": "sim"}
SLOTS_PORTO = {"titular_cpf": "11122233344", "telefone_contato": "48900000000",
               "problema_descricao": "carro não liga", "endereco_numero": "100"}


# --------------------------------------------------------------------------- a borda (dublês)
class _Redis:
    def __init__(self):
        self.d, self.listas = {}, {}

    async def get(self, k):
        return self.d.get(k)

    async def set(self, k, v, ex=None, nx=False):
        if nx and k in self.d:
            return None
        self.d[k] = v
        return True

    async def delete(self, *ks):
        for k in ks:
            self.d.pop(k, None)

    async def exists(self, k):
        return 1 if k in self.d else 0

    async def lpop(self, k):
        lst = self.listas.get(k) or []
        return lst.pop(0) if lst else None

    async def llen(self, k):
        return len(self.listas.get(k) or [])

    async def rpush(self, k, v):
        self.listas.setdefault(k, []).append(v)
        return len(self.listas[k])

    async def expire(self, k, s):
        return True

    async def scan_iter(self, match="*"):
        for k in list(self.d):
            if k.startswith(match.rstrip("*")):
                yield k


class _Consulta:
    def __init__(self, amb, tabela):
        self.amb, self.tabela, self.linha = amb, tabela, None

    def insert(self, linha):
        self.linha = linha
        return self

    def __getattr__(self, _nome):
        return lambda *a, **k: self

    async def execute(self):
        return types.SimpleNamespace(data=[])


class _Banco:
    def __init__(self, amb):
        self.amb, self.client = amb, self

    def table(self, nome):
        return _Consulta(self.amb, nome)


class _Wa:
    def __init__(self, amb):
        self.amb = amb

    def send_message(self, fone, texto, integ=None, **k):
        self.amb.wa.append((fone, texto))


@dataclass
class Destravamento:
    """A MESMA forma do contrato (`destravador.Destravamento`)."""
    classe: str
    acao: str
    valor: str = ""
    opcoes: Optional[list] = None
    nota: Optional[int] = None
    limiar: int = 70
    motivo: str = ""
    explicacao: str = ""
    segunda_opiniao: Optional[dict] = None
    modelo: str = ""
    proibicao: str = ""
    modo: str = "on"
    diario_id: Optional[str] = None
    custo_usd: float = 0.0


class Ambiente:
    def __init__(self):
        self.redis = _Redis()
        self.enviadas, self.wa, self.grupo, self.aberturas = [], [], [], []
        self.modo = ("off", 70)
        self.decisao = Destravamento(classe="deduzir", acao="PESSOA", proibicao="sem_saida")
        self.destravar_chamadas, self.cerebro_chamadas = [], []
        self.resposta_do_cerebro = "Para você"

    def ura(self, texto):
        self.enviadas.append(("seguradora", texto))

    def cliente(self, fone, texto):
        self.enviadas.append(("cliente", texto))


def _destravador_duble(a: Ambiente) -> types.ModuleType:
    m = types.ModuleType("app.services.destravador")
    m.Destravamento = Destravamento
    m.LIMIAR_MINIMO = 70

    async def modo_do_destravador(company_id, insurer_key, ramo):
        return a.modo

    async def destravar(company_id, sessao, tela, *, gatilho, modo, limiar=70):
        a.destravar_chamadas.append(gatilho)
        return copy.deepcopy(a.decisao)

    def agendar_em_sombra(company_id, sessao_copia, tela, *, gatilho):
        return None

    def opcao_que_nao_vai_ao_segurado(rotulo, com_custo=False):
        return False

    m.modo_do_destravador, m.destravar, m.agendar_em_sombra = modo_do_destravador, destravar, agendar_em_sombra
    m.opcao_que_nao_vai_ao_segurado = opcao_que_nao_vai_ao_segurado
    return m


def _diario_duble() -> types.ModuleType:
    m = types.ModuleType("app.services.diario_de_decisoes")

    async def marcar_resultado(**k):
        return 1

    async def registrar_decisao(**k):
        return "d-x"

    m.marcar_resultado, m.registrar_decisao = marcar_resultado, registrar_decisao
    return m


@pytest.fixture
def amb(monkeypatch):
    for nome, mod in FIO.items():
        monkeypatch.setitem(sys.modules, nome, mod)
        pai, _, filho = nome.rpartition(".")
        p = sys.modules.get(pai)
        if p is not None:
            monkeypatch.setattr(p, filho, mod, raising=False)
    _antes = set(sys.modules)
    import app.services  # noqa: F401 — o pacote real antes dos dublês de canal
    a = Ambiente()

    async def _redis():
        return a.redis

    async def _db():
        return _Banco(a)

    async def _porta(db, **kw):
        a.grupo.append(kw.get("tipo"))
        return {"enviado": True, "calado": False, "motivo": ""}

    async def _destino(company_id):
        return {"destino": "120363000000000000@g.us", "fonte": "teste", "recusa": ""}

    async def _cerebro_nao_sabe(company_id, session, *, slot, rotulo, tela, llm=None):
        return None, ""

    async def _dossie(company_id, session, dossier, wa, integration):
        a.grupo.append("dossie")
        return True

    async def _modelo(papel, mensagens, **kw):
        # A BORDA do modelo de produção (o cérebro de HOJE do Sentinela).
        a.cerebro_chamadas.append(papel)
        return types.SimpleNamespace(content=a.resposta_do_cerebro)

    import app.core.database as _core_db
    import app.core.redis as _core_redis
    from app.factories import llm_factory

    monkeypatch.setattr(llm_factory, "invocar_com_reserva", _modelo)
    monkeypatch.setattr(_core_redis, "get_async_redis_client", _redis)
    monkeypatch.setattr(_core_db, "get_supabase_client", lambda: None)
    monkeypatch.setattr(R, "_redis", _redis)
    monkeypatch.setattr(R, "_db", _db)
    monkeypatch.setattr(R, "resolver_destino_de_suporte", _destino)
    monkeypatch.setattr(R, "o_cerebro_ja_sabe", _cerebro_nao_sabe)
    monkeypatch.setattr(G, "enviar_ao_grupo", _porta)
    monkeypatch.setattr(D, "dispatch_live_enabled", lambda: True)
    ws = types.ModuleType("app.services.whatsapp_service")
    ws.get_whatsapp_service = lambda: _Wa(a)
    monkeypatch.setitem(sys.modules, "app.services.whatsapp_service", ws)
    is_ = types.ModuleType("app.services.integration_service")
    is_.get_integration_service = lambda *x: types.SimpleNamespace()
    is_.IntegrationService = type("IntegrationService", (), {})
    monkeypatch.setitem(sys.modules, "app.services.integration_service", is_)
    monkeypatch.setitem(sys.modules, "app.services.destravador", _destravador_duble(a))
    monkeypatch.setitem(sys.modules, "app.services.diario_de_decisoes", _diario_duble())
    monkeypatch.setattr(W, "_canal_da_conversa", lambda i, c, s: {"id": "canal-teste"})
    monkeypatch.setattr(W, "_entregar_dossie_com_marcador", _dossie)
    real_start = R.start_live_dispatch

    async def _start_contado(**kw):
        a.aberturas.append(dict(kw))
        return await real_start(**kw)

    monkeypatch.setattr(R, "start_live_dispatch", _start_contado)
    AC._CACHE_DA_CHAVE.clear()
    R._memory_store.clear()
    yield a
    AC._CACHE_DA_CHAVE.clear()
    R._memory_store.clear()
    monkeypatch.undo()
    for nome in [n for n in sys.modules if n not in _antes and (n == "app" or n.startswith("app."))]:
        novo = sys.modules.pop(nome)
        pai, _, filho = nome.rpartition(".")
        p = sys.modules.get(pai)
        if p is not None and getattr(p, filho, None) is novo:
            delattr(p, filho)


def sessao(ref, subservice, *, estado="ura", slots=None, **extra):
    s = D.new_dispatch_session(case_id="caso-a", company_id=EMPRESA_A, playbook_ref=ref,
                               subservice=subservice, slots=dict(slots or {}))
    s.update({"state": estado, "client_phone": CLIENTE, "work_run_id": "run-z", "live": True,
              "mirror_conversation_id": "conv-z", "retry_count": 0, "insurer_phone": URA})
    s.update(extra)
    return s


def salvar(s):
    asyncio.run(R.save_active_dispatch(EMPRESA_A, URA, s))


def carregar():
    return asyncio.run(R.load_active_dispatch(EMPRESA_A, URA))


def turno(amb, texto):
    asyncio.run(R.try_route_insurer_inbound(company_id=EMPRESA_A, from_phone=URA, text=texto,
                                            send_to_insurer=amb.ura, send_to_client=amb.cliente))
    return carregar()


# =============================================================================
# Z1 · o Vigia que vence a espera SEGURADA libera a fila
# =============================================================================
def _segurada(amb):
    """Allianz: a tela pede um dado que só o segurado tem → a URA encerra → a sessão fica SEGURADA."""
    salvar(sessao(REF_ALLIANZ, "encanador", slots={k: v for k, v in SLOTS_ALLIANZ.items() if k != SLOT}))
    s = turno(amb, PEDE)
    assert s.get("esperando_do_segurado", {}).get("slot") == SLOT, (s.get("state"), s.get("reason"))
    s = turno(amb, ENCERRA_ALLIANZ)
    assert R.sessao_segurada_no_prazo(s), (s.get("state"), s.get("reason"))
    assert amb.aberturas == []
    return s


def _segundo_pedido(amb):
    """O 2º acionamento do MESMO número da seguradora — e o que `insurer_dispatch_tool` faz com a
    recusa `dispatch_already_active` (`enqueue_dispatch`)."""
    pedido = {"case_id": "caso-b", "playbook_ref": REF_ALLIANZ, "subservice": "encanador",
              "slots": SLOTS_ALLIANZ, "client_phone": CLIENTE_B}
    r = asyncio.run(R.start_live_dispatch(company_id=EMPRESA_A, insurer_phone=URA, sender=amb.ura,
                                          **pedido))
    assert r.get("error") == "dispatch_already_active", r.get("error")
    asyncio.run(R.enqueue_dispatch(EMPRESA_A, URA, pedido))


def _vencer_o_prazo(s):
    espera = s["esperando_do_segurado"]
    espera["holdings"] = 99
    espera["ate"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    salvar(s)
    assert W.diagnose(s) == "segurado_sem_resposta"


def test_Z1_o_vigia_que_desiste_da_espera_segurada_libera_a_fila(amb):
    s = _segurada(amb)
    _segundo_pedido(amb)
    assert [a["case_id"] for a in amb.aberturas] == ["caso-b"] and carregar()["case_id"] == "caso-a"
    _vencer_o_prazo(s)
    asyncio.run(W.check_dispatch_watchdog())
    # o caso A foi a uma pessoa com o dossiê (o caminho de hoje) …
    assert "dossie" in amb.grupo
    # … e o pedido que esperava na fila COMEÇOU, sem esperar a fila expirar.
    assert [a["case_id"] for a in amb.aberturas] == ["caso-b", "caso-b"], amb.aberturas
    viva = carregar()
    assert viva["case_id"] == "caso-b" and viva["state"] == "ura", (viva.get("case_id"), viva.get("state"))
    assert any(f == CLIENTE_B and "Chegou a sua vez" in t for f, t in amb.wa), amb.wa
    assert asyncio.run(R._ha_fila(EMPRESA_A, URA)) is False


def test_Z1_CONTROLE_sem_fila_o_vigia_desiste_como_hoje_e_a_sessao_fica(amb):
    s = _segurada(amb)
    _vencer_o_prazo(s)
    asyncio.run(W.check_dispatch_watchdog())
    viva = carregar()
    assert "dossie" in amb.grupo and amb.aberturas == []
    assert viva["case_id"] == "caso-a" and viva["reason"] == "segurado_nao_respondeu"
    assert (viva.get("espera_vencida") or {}).get("ura_fechou") is True


def test_Z1_CONTROLE_a_espera_que_ainda_corre_nao_libera_a_fila(amb):
    _segurada(amb)
    _segundo_pedido(amb)
    asyncio.run(W.check_dispatch_watchdog())
    assert [a["case_id"] for a in amb.aberturas] == ["caso-b"] and carregar()["case_id"] == "caso-a"
    assert asyncio.run(R._ha_fila(EMPRESA_A, URA)) is True


# =============================================================================
# Z2 · no teto do PONTO A o Sentinela segue o caminho de HOJE, não PESSOA
# =============================================================================
def _sessao_parada(**extra):
    s = sessao(REF_PORTO, "guincho", estado="human_phase", slots=SLOTS_PORTO, retry_count=1, **extra)
    s["transcript"].append({"direction": "in", "text": TELA_SEM_PASSO, "at": "2026-09-30T10:00:00+00:00"})
    return s


def _sentinela(amb, s):
    salvar(s)
    return asyncio.run(W._sentinela_recover(EMPRESA_A, URA, s, _Wa(amb), {"id": "canal-teste"}))


def test_Z2_no_teto_do_ponto_A_o_sentinela_usa_o_cerebro_de_hoje(amb):
    amb.modo = ("on", 70)
    s = _sessao_parada(destravamentos_ponto_a=R.TETO_DO_DESTRAVADOR_NO_PONTO_A)
    desfecho = _sentinela(amb, s)
    assert amb.cerebro_chamadas == ["dispatch"], "no teto, o Sentinela não chamou o cérebro de hoje"
    assert not str(s.get("reason") or "").startswith("destravador:"), s.get("reason")
    assert desfecho == "recovered" and amb.wa == [(URA, amb.resposta_do_cerebro)], (desfecho, amb.wa)
    assert amb.destravar_chamadas == []


def test_Z2_CONTROLE_abaixo_do_teto_PESSOA_do_destravador_e_pessoa(amb):
    amb.modo = ("on", 70)
    s = _sessao_parada(destravamentos_ponto_a=R.TETO_DO_DESTRAVADOR_NO_PONTO_A - 1)
    assert _sentinela(amb, s) == "handoff"
    assert s["reason"] == "destravador:pessoa:sem_saida" and amb.destravar_chamadas == ["sentinela"]
    assert amb.cerebro_chamadas == [] and "dossie" in amb.grupo
