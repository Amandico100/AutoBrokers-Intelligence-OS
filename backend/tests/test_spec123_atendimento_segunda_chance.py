# -*- coding: utf-8 -*-
"""SPEC-123 · F7 · D8 — o agente de atendimento só chama pessoa quando precisa.

O FIO (dublê só na borda: banco, Redis, WhatsApp, destino do grupo, feed)
=========================================================================
O agente chama `request_human_agent` (o `HumanHandoffTool._arun` REAL) →
`por_que_vai_direto_a_pessoa` (REAL, com `classificar_o_motivo` e o detector de
sinistro REAIS) → o contador da conversa (o `diario_de_decisoes` lido pelo
cliente da ferramenta) → `diario_de_decisoes.registrar_decisao` (REAL, com a
máscara real) → ou a SEGUNDA CHANCE (nada marcado, nada enviado), ou o caminho de
hoje (`_avisar_suporte` → `o_grupo_so_o_que_importa.enviar_ao_grupo`, REAIS).

O QUE SE PROVA
==============
  ① o TESTE DO FIO: "não sei responder" → 1ª vez devolve a instrução, NÃO marca a
    conversa, NÃO avisa o grupo, grava UMA linha no diário → 2ª vez passa a pessoa.
  ② CONTROLES byte a byte com a ferramenta de ANTES (commit `80f1234`, lida por
    `git show`): sinistro, cliente pediu pessoa e condomínio passam na 1ª — o que é
    gravado (todas as tabelas, menos o diário novo), o que é enviado ao grupo, as
    chaves do Redis e a resposta ao agente são IGUAIS.
  ③ duas conversas não dividem o contador.
  ④ sem linha no diário, sem segunda chance (diário fora do ar → pessoa, como hoje);
    e a leitura do contador falhando → pessoa.
  ⑤ a tabela da decisão (pura) e a instrução (sem o carimbo, sem afirmar transferência).

🔴 MUTAÇÕES (rodadas uma vez, por cópia): `cliente_pediu_humano` na segunda chance →
②/⑤ VERMELHOS; sem o `registrar_decisao` → ① VERMELHO.

⛔ Nenhum dado pessoal: nomes, telefones e ids inventados (faixa de teste).
"""
from __future__ import annotations

import asyncio
import importlib.util
import os
import re
import subprocess
import sys
import types
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _pkg in ("app", "app.agents", "app.agents.tools", "app.core", "app.services",
             "app.services.atlas", "app.tasks"):
    if _pkg not in sys.modules:
        _m = types.ModuleType(_pkg)
        _m.__path__ = [os.path.join(_RAIZ, *_pkg.split("."))]
        sys.modules[_pkg] = _m

#: A ferramenta de ANTES desta fatia — a linha de controle do "byte a byte".
COMMIT_DE_ANTES = "80f1234"


def rodar(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


# =============================================================================
# DUBLÊS — só a borda
# =============================================================================
class _Resp:
    def __init__(self, data):
        self.data = data


class _Consulta:
    """PostgREST de mentira que honra filtro, ordem e limite."""

    def __init__(self, banco, tabela):
        self.b, self.t = banco, tabela
        self.filtros, self.ordem, self.teto = [], None, None
        self.acao, self.carga = "select", None

    def select(self, *_a, **_k):
        return self

    def eq(self, c, v):
        self.filtros.append(("eq", c, v))
        return self

    def neq(self, c, v):
        self.filtros.append(("neq", c, v))
        return self

    def is_(self, c, v):
        self.filtros.append(("is", c, str(v)))
        return self

    def in_(self, c, vals):
        self.filtros.append(("in", c, [str(x) for x in vals]))
        return self

    def gte(self, c, v):
        self.filtros.append(("gte", c, v))
        return self

    def lt(self, c, v):
        self.filtros.append(("lt", c, v))
        return self

    def lte(self, c, v):
        self.filtros.append(("lte", c, v))
        return self

    def order(self, c, desc=False):
        self.ordem = (c, desc)
        return self

    def limit(self, n):
        self.teto = int(n)
        return self

    def update(self, campos):
        self.acao, self.carga = "update", dict(campos)
        return self

    def insert(self, linha):
        self.acao, self.carga = "insert", linha
        return self

    def _casa(self, linha):
        for op, c, v in self.filtros:
            x = linha.get(c)
            if op == "eq" and str(x) != str(v):
                return False
            if op == "neq" and str(x) == str(v):
                return False
            if op == "is" and ((x is None) != (v == "null")):
                return False
            if op == "in" and str(x) not in v:
                return False
            if op == "gte" and not (x is not None and str(x) >= str(v)):
                return False
            if op == "lt" and not (x is not None and str(x) < str(v)):
                return False
            if op == "lte" and not (x is not None and str(x) <= str(v)):
                return False
        return True

    def execute(self):
        if self.b.quebrada == self.t:
            raise RuntimeError("tabela fora do ar (dublê)")
        fonte = self.b.tabelas.setdefault(self.t, [])
        if self.acao == "insert":
            linhas = self.carga if isinstance(self.carga, list) else [self.carga]
            novas = []
            for l in linhas:
                l = dict(l)
                if self.t == "diario_de_decisoes":
                    l.setdefault("id", "d-%04d" % (len(fonte) + 1))
                    l.setdefault("created_at", datetime.now(timezone.utc).isoformat())
                    l.setdefault("resultado", "pendente")
                fonte.append(l)
                novas.append(dict(l))
            return _Resp(novas)
        achadas = [l for l in fonte if self._casa(l)]
        if self.acao == "update":
            for l in achadas:
                l.update(self.carga)
            return _Resp([dict(l) for l in achadas])
        if self.ordem:
            c, desc = self.ordem
            achadas = sorted(achadas, key=lambda l: str(l.get(c) or ""), reverse=desc)
        teto = min(self.teto or 1000, 1000)
        return _Resp([dict(l) for l in achadas[:teto]])


class _ConsultaAsync(_Consulta):
    """A MESMA consulta, com `execute` aguardável — é como o diário fala com o banco."""

    async def execute(self):  # type: ignore[override]
        return _Consulta.execute(self)


class Banco:
    def __init__(self, **tabelas):
        self.tabelas = {k: list(v) for k, v in tabelas.items()}
        self.quebrada = ""

    def table(self, nome):
        return _Consulta(self, nome)

    def eventos(self, prefixo=""):
        return [e for e in self.tabelas.get("work_events", [])
                if str(e.get("event_type") or "").startswith(prefixo)]


class _BancoAsync:
    def __init__(self, banco):
        self.b = banco

    def table(self, nome):
        return _ConsultaAsync(self.b, nome)


class _Embrulho:
    def __init__(self, cliente):
        self.client = cliente


class RedisFake:
    def __init__(self):
        self.chaves = {}

    async def set(self, chave, valor, ex=None, nx=False):
        if nx and chave in self.chaves:
            return None
        self.chaves[chave] = valor
        return True

    async def get(self, chave):
        return self.chaves.get(chave)

    async def delete(self, chave):
        self.chaves.pop(chave, None)

    async def incr(self, chave):
        self.chaves[chave] = int(self.chaves.get(chave) or 0) + 1
        return self.chaves[chave]

    async def expire(self, *_a, **_k):
        return True


ENVIOS: list = []
REDIS = RedisFake()
BANCO = {"b": None}
FUSO_BR = timezone(timedelta(hours=-3))


@pytest.fixture()
def borda(monkeypatch):
    """Os dublês da borda, instalados e DEVOLVIDOS pelo monkeypatch (nada vaza)."""
    ENVIOS.clear()
    REDIS.chaves.clear()

    def _instalar(nome, modulo):
        monkeypatch.setitem(sys.modules, nome, modulo)

    red = types.ModuleType("app.core.redis")

    async def _redis():
        return REDIS
    red.get_async_redis_client = _redis
    _instalar("app.core.redis", red)

    zap = types.ModuleType("app.services.whatsapp_service")

    class _Zap:
        def send_message(self, alvo, texto, integ, bloco_unico=False):
            ENVIOS.append((alvo, texto))
            return True
    zap.get_whatsapp_service = lambda: _Zap()
    _instalar("app.services.whatsapp_service", zap)

    integ = types.ModuleType("app.services.integration_service")

    class _Integ:
        def get_whatsapp_integration(self, _empresa):
            return {"canal": "teste"}
    integ.get_integration_service = lambda _bruto=None: _Integ()
    _instalar("app.services.integration_service", integ)

    rot = types.ModuleType("app.services.dispatch_router")

    async def _destino(_empresa):
        return {"destino": "grupo-de-teste@g.us", "fonte": "teste", "recusa": ""}
    rot.resolver_destino_de_suporte = _destino
    _instalar("app.services.dispatch_router", rot)

    plat = types.ModuleType("app.services.platform_outbound")

    async def _conta(*_a, **_k):
        return None
    plat.record_platform_send = _conta
    plat.fuso_da_corretora = lambda *_a, **_k: FUSO_BR
    _instalar("app.services.platform_outbound", plat)

    feed = types.ModuleType("app.services.activity_log")
    FEED: list = []

    async def _feed(*a, **_k):
        FEED.append(a)
        return None
    feed.log_activity = _feed
    _instalar("app.services.activity_log", feed)

    obs = types.ModuleType("app.services.observability")
    obs.sli = types.SimpleNamespace(HANDOFF_ESPERA="x", registrar=lambda *a, **k: None)
    _instalar("app.services.observability", obs)
    _instalar("app.services.observability.sli", obs.sli)

    import app.core.database as dbreal
    monkeypatch.setattr(dbreal, "get_supabase_client", lambda: _Embrulho(BANCO["b"]))

    import app.services.claims_shadow as CS
    GESTOS: list = []

    async def _gesto(_db, **kw):
        GESTOS.append(kw)
        return True
    monkeypatch.setattr(CS, "registrar_gesto", _gesto)

    # 🔴 a borda do DIÁRIO: o cliente durável dele (no produto, `dispatch_router._db`).
    #    O `registrar_decisao` que roda é o REAL — máscara, listas fechadas, idempotência.
    import app.services.diario_de_decisoes as D
    estado = {"fora": False}

    async def _cliente():
        if estado["fora"]:
            return None
        return _Embrulho(_BancoAsync(BANCO["b"]))
    monkeypatch.setattr(D, "_cliente", _cliente)
    return types.SimpleNamespace(feed=FEED, gestos=GESTOS, diario=estado)


X = "11111111-1111-4111-8111-111111111111"


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f+00:00")


def _conversa(cid, *, preview="tenho uma dúvida", ficha=None):
    ja = datetime.now(timezone.utc)
    return {"id": cid, "company_id": X, "session_id": "ses-" + cid,
            "user_name": "Pessoa de Teste", "user_phone": "5547900000000",
            "status": "open", "claimed_by": None, "claimed_by_name": None,
            "claimed_at": None, "human_handoff_reason": None, "resolvido_em": None,
            "ficha_atendimento": ficha, "last_message_preview": preview,
            "last_message_at": iso(ja - timedelta(seconds=30)),
            "created_at": iso(ja - timedelta(hours=1))}


def _banco(*conversas):
    b = Banco(conversations=list(conversas), messages=[],
              agents=[{"id": "ag-x", "company_id": X, "agent_role": "attendance",
                       "is_active": True, "name": "Assistente"}],
              work_events=[], company_internal_numbers=[], company_members=[],
              users_v2=[], work_waits=[], agent_activities=[], diario_de_decisoes=[])
    BANCO["b"] = b
    return b


def _pedir(modulo, banco, cid, motivo, codigo=None):
    tool = modulo.HumanHandoffTool(supabase_client=banco)
    return rodar(tool._arun(reason=motivo, session_id="ses-" + cid, company_id=X,
                            codigo=codigo))


def _linha(banco, cid):
    return [c for c in banco.tabelas["conversations"] if c["id"] == cid][0]


def _diario(banco, cid=None):
    return [l for l in banco.tabelas.get("diario_de_decisoes", [])
            if cid is None or l.get("conversation_id") == cid]


# =============================================================================
# ① O TESTE DO FIO
# =============================================================================
def test_o_fio_nao_sei_responder_ganha_uma_segunda_chance_e_so_ela(borda):
    import app.agents.tools.human_handoff as H
    from app.agents.honestidade_do_handoff import SUCESSO_DO_HANDOFF

    cid = "c-fio-0001"
    b = _banco(_conversa(cid))

    # ── 1ª vez ────────────────────────────────────────────────────────────
    r1 = _pedir(H, b, cid, "não sei responder a dúvida do cliente")
    linha = _linha(b, cid)
    assert r1 == H.SEGUNDA_CHANCE_DO_HANDOFF, r1
    assert H.foi_segunda_chance(r1)
    assert "HANDOFF_OK" not in r1
    assert linha["status"] == "open", "a conversa NÃO pode ser marcada na segunda chance"
    assert linha["human_handoff_reason"] is None, "nenhum motivo de handoff é gravado"
    assert ENVIOS == [], "o grupo NÃO é avisado na segunda chance"
    assert b.eventos("grupo.") == []
    assert REDIS.chaves == {}, "nem a vez do grupo é reservada"
    assert borda.feed == [] and b.tabelas["agent_activities"] == []
    assert borda.gestos == []
    d1 = _diario(b, cid)
    assert len(d1) == 1, d1
    assert d1[0]["company_id"] == X
    assert d1[0]["origem"] == "atendimento"
    assert d1[0]["acao"] == "perguntou_segurado"
    assert d1[0]["classe"] == "perguntar_ao_segurado"
    assert d1[0]["modo"] == "on"
    assert d1[0]["conversation_id"] == cid
    assert "pessoa" in d1[0]["explicacao_para_gente"]
    assert "_" not in d1[0]["explicacao_para_gente"], "D7: nada de nome de variável"

    # ── 2ª vez: passa a pessoa como hoje ─────────────────────────────────
    r2 = _pedir(H, b, cid, "o cliente quer saber se a franquia muda e eu não achei")
    linha = _linha(b, cid)
    assert r2 == SUCESSO_DO_HANDOFF, r2
    assert not H.foi_segunda_chance(r2)
    assert linha["status"] == "HUMAN_REQUESTED"
    assert linha["human_handoff_reason"]
    assert len(ENVIOS) == 1, "o grupo é avisado UMA vez"
    d2 = _diario(b, cid)
    assert len(d2) == 2, d2
    assert d2[1]["acao"] == "chamou_pessoa"
    assert d2[1]["origem"] == "atendimento"
    assert d2[1]["classe"] == "perguntar_ao_segurado"
    assert d2[1]["chave_idempotencia"] != d2[0]["chave_idempotencia"]


def test_o_motivo_vazio_tambem_ganha_a_segunda_chance(borda):
    """O agente que chama sem dizer por quê é o caso de 💭 "não sei" mais comum."""
    import app.agents.tools.human_handoff as H

    cid = "c-vazio-01"
    b = _banco(_conversa(cid))
    assert _pedir(H, b, cid, "") == H.SEGUNDA_CHANCE_DO_HANDOFF
    assert _linha(b, cid)["status"] == "open"
    assert len(_diario(b, cid)) == 1


# =============================================================================
# ② CONTROLES — passam na 1ª, byte a byte com a ferramenta de ANTES
# =============================================================================
def _ferramenta_de_antes():
    caminho = "backend/app/agents/tools/human_handoff.py"
    try:
        fonte = subprocess.run(
            ["git", "show", "%s:%s" % (COMMIT_DE_ANTES, caminho)],
            cwd=_RAIZ, capture_output=True, check=True, timeout=60).stdout.decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        pytest.skip("a linha de controle exige o git com o commit %s (%s)"
                    % (COMMIT_DE_ANTES, type(exc).__name__))
    assert "SEGUNDA_CHANCE" not in fonte, "a linha de controle tem de ser a de ANTES"
    nome = "app.agents.tools._human_handoff_%s" % COMMIT_DE_ANTES
    if nome in sys.modules:
        return sys.modules[nome]
    spec = importlib.util.spec_from_loader(nome, loader=None)
    mod = importlib.util.module_from_spec(spec)
    # ⚠️ registrado ANTES do exec: o pydantic resolve as anotações pelo módulo.
    #    Nome próprio (com o commit) — nunca colide com o módulo real.
    sys.modules[nome] = mod
    exec(compile(fonte, "<%s:%s>" % (COMMIT_DE_ANTES, caminho), "exec"), mod.__dict__)
    return mod


_TS = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:\+00:00|Z)?")
_HORA = re.compile(r"🕐 \d{2}/\d{2} às \d{2}:\d{2}")
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def _norm(obj):
    texto = repr(obj)
    texto = _TS.sub("<TS>", texto)
    texto = _HORA.sub("🕐 <H>", texto)
    return _UUID.sub(lambda m: m.group(0) if m.group(0) == X else "<UUID>", texto)


def _efeito(modulo, cid, motivo, conversa_kw, borda):
    ENVIOS.clear()
    REDIS.chaves.clear()
    borda.feed.clear()
    borda.gestos.clear()
    b = _banco(_conversa(cid, **conversa_kw))
    resposta = _pedir(modulo, b, cid, motivo)
    # ⚠️ só o que tem LINHA: uma LEITURA cria a tabela vazia no dublê (`setdefault`), e
    #    leitura com cache de processo (ex.: dados da corretora) depende da ordem dos
    #    testes — o que se compara é o que é GRAVADO.
    tabelas = {k: v for k, v in b.tabelas.items() if v and k != "diario_de_decisoes"}
    return {"resposta": resposta, "tabelas": _norm(tabelas), "envios": _norm(list(ENVIOS)),
            "redis": sorted(REDIS.chaves), "feed": _norm(list(borda.feed)),
            "gestos": _norm(list(borda.gestos))}, b


CONTROLES = [
    # (rótulo, motivo do agente, conversa)
    ("sinistro", "colisão com outro carro, é sinistro e precisa de pessoa", {}),
    ("cliente pediu pessoa", "o cliente pediu para falar com uma pessoa", {}),
    ("condomínio", "apólice de condomínio, a corretora cuida", {}),
    ("sem corredor", "sem corredor para a seguradora deste serviço", {}),
    ("segurado irritado", "segurado irritado depois de duas tentativas", {}),
]


@pytest.mark.parametrize("rotulo,motivo,conversa_kw", CONTROLES, ids=[c[0] for c in CONTROLES])
def test_controle_passa_na_primeira_byte_a_byte_com_antes(borda, rotulo, motivo, conversa_kw):
    import app.agents.tools.human_handoff as H
    from app.agents.honestidade_do_handoff import SUCESSO_DO_HANDOFF

    antes = _ferramenta_de_antes()
    cid = "c-ctrl-%s" % re.sub(r"\W", "", rotulo)[:10]
    efeito_antes, _ = _efeito(antes, cid, motivo, conversa_kw, borda)
    efeito_agora, b = _efeito(H, cid, motivo, conversa_kw, borda)

    assert efeito_agora["resposta"] == SUCESSO_DO_HANDOFF, (rotulo, efeito_agora["resposta"])
    assert _linha(b, cid)["status"] == "HUMAN_REQUESTED"
    assert len(ENVIOS) == 1
    for chave in ("resposta", "tabelas", "envios", "redis", "feed", "gestos"):
        assert efeito_agora[chave] == efeito_antes[chave], (rotulo, chave)
    d = _diario(b, cid)
    assert len(d) == 1, d
    assert d[0]["acao"] == "chamou_pessoa" and d[0]["origem"] == "atendimento"
    assert d[0]["classe"] == "nunca_sozinho", (rotulo, d[0]["classe"])


def test_a_linha_de_controle_consegue_ser_diferente(borda):
    """§9.3: o comparador vê a diferença quando ela existe — "não sei" ANTES passava a
    pessoa, AGORA não passa."""
    import app.agents.tools.human_handoff as H

    antes = _ferramenta_de_antes()
    e_antes, _ = _efeito(antes, "c-dif-0001", "não sei responder", {}, borda)
    e_agora, _ = _efeito(H, "c-dif-0001", "não sei responder", {}, borda)
    assert e_antes["envios"] != e_agora["envios"]
    assert e_antes["tabelas"] != e_agora["tabelas"]


# =============================================================================
# ③ DUAS CONVERSAS NÃO DIVIDEM O CONTADOR
# =============================================================================
def test_duas_conversas_nao_dividem_o_contador(borda):
    import app.agents.tools.human_handoff as H

    a, c = "c-dois-000a", "c-dois-000b"
    b = _banco(_conversa(a), _conversa(c))
    assert _pedir(H, b, a, "não achei o dado") == H.SEGUNDA_CHANCE_DO_HANDOFF
    assert _pedir(H, b, c, "não achei o dado") == H.SEGUNDA_CHANCE_DO_HANDOFF, \
        "a segunda chance da conversa A não pode gastar a da conversa B"
    assert _linha(b, a)["status"] == "open" and _linha(b, c)["status"] == "open"
    assert ENVIOS == []
    assert len(_diario(b, a)) == 1 and len(_diario(b, c)) == 1


def test_outra_corretora_nao_gasta_a_segunda_chance(borda):
    """§7: o contador é lido por `company_id` — a linha de OUTRA corretora com a mesma
    chave não conta."""
    import app.agents.tools.human_handoff as H

    cid = "c-tenant-01"
    b = _banco(_conversa(cid))
    chave = H._chave_da_segunda_chance(cid)
    b.tabelas["diario_de_decisoes"].append({
        "id": "d-outra", "company_id": "22222222-2222-4222-8222-222222222222",
        "chave_idempotencia": chave, "conversation_id": cid, "origem": "atendimento",
        "acao": "perguntou_segurado", "classe": "perguntar_ao_segurado", "modo": "on"})
    assert _pedir(H, b, cid, "não sei responder") == H.SEGUNDA_CHANCE_DO_HANDOFF
    assert _linha(b, cid)["status"] == "open"


# =============================================================================
# ④ SEM REGISTRO, SEM AUTONOMIA
# =============================================================================
def test_diario_fora_do_ar_passa_a_pessoa_como_hoje(borda):
    import app.agents.tools.human_handoff as H
    from app.agents.honestidade_do_handoff import SUCESSO_DO_HANDOFF

    borda.diario["fora"] = True
    cid = "c-semdiario"
    b = _banco(_conversa(cid))
    assert _pedir(H, b, cid, "não sei responder") == SUCESSO_DO_HANDOFF
    assert _linha(b, cid)["status"] == "HUMAN_REQUESTED"
    assert len(ENVIOS) == 1
    assert _diario(b) == []


def test_contador_ilegivel_passa_a_pessoa_e_a_ferramenta_nao_cai(borda):
    import app.agents.tools.human_handoff as H
    from app.agents.honestidade_do_handoff import SUCESSO_DO_HANDOFF

    cid = "c-ilegivel1"
    b = _banco(_conversa(cid))
    b.quebrada = "diario_de_decisoes"           # leitura E escrita do diário estouram
    assert _pedir(H, b, cid, "não sei responder") == SUCESSO_DO_HANDOFF
    assert _linha(b, cid)["status"] == "HUMAN_REQUESTED"
    assert len(ENVIOS) == 1


def test_o_caso_ja_com_a_equipe_nao_ganha_segunda_chance(borda):
    import app.agents.tools.human_handoff as H

    cid = "c-equipe-01"
    conversa = _conversa(cid)
    conversa["status"] = "HUMAN_REQUESTED"
    b = _banco(conversa)
    r = _pedir(H, b, cid, "não sei responder")
    assert not H.foi_segunda_chance(r)
    assert "HANDOFF_OK" in r


# =============================================================================
# ⑤ A TABELA DA DECISÃO E A INSTRUÇÃO
# =============================================================================
DIRETO = [
    "o cliente pediu para falar com uma pessoa",
    "cliente quer falar com alguém",
    "sinistro — exige humano",
    "bateu o carro, colisão",
    "apólice de condomínio",
    "seguro empresarial da loja",
    "sem corredor para HDI",
    "Mapfre não tem corredor para chaveiro",
    "há vítima ferida",
    "cheiro de queimado e fumaça na tomada",
    "segurado irritado",
    "pedido de carro reserva",
]
SEGUNDA_CHANCE = [
    "não sei responder",
    "dúvida do cliente sobre a franquia",
    "não achei o dado",
    "não tenho a resposta",
    "",
    "o agente travou",
]


@pytest.mark.parametrize("motivo", DIRETO)
def test_vai_direto_a_pessoa(motivo):
    import app.agents.tools.human_handoff as H

    assert H.por_que_vai_direto_a_pessoa(motivo), motivo


@pytest.mark.parametrize("motivo", SEGUNDA_CHANCE)
def test_ganha_a_segunda_chance(motivo):
    import app.agents.tools.human_handoff as H

    assert H.por_que_vai_direto_a_pessoa(motivo) == "", motivo


def test_a_marca_do_motor_e_o_pos_acionamento_vao_direto():
    import app.agents.tools.human_handoff as H

    assert H.por_que_vai_direto_a_pessoa("não sei", codigo="carro_reserva_por_desenho")
    assert H.por_que_vai_direto_a_pessoa(
        "não sei", caso={"ficha_atendimento": {"dispatch_state": "captured"}})
    assert H.por_que_vai_direto_a_pessoa(
        "não sei", caso={"ficha_atendimento": {"ramo": "condominio"}})
    assert H.por_que_vai_direto_a_pessoa(
        "não sei", caso={"last_message_preview": "bateram no meu carro"})


def test_a_instrucao_nao_carimba_nem_afirma_transferencia():
    import app.agents.tools.human_handoff as H
    from app.agents.honestidade_do_handoff import _houve_handoff_confirmado, afirma_transferencia

    texto = H.SEGUNDA_CHANCE_DO_HANDOFF
    assert "HANDOFF_OK" not in texto
    assert not afirma_transferencia(texto)
    msg = types.SimpleNamespace(name="request_human_agent", content=texto)
    assert not _houve_handoff_confirmado([msg])
    for termo in ("pergunte", "segurado", "de novo", "request_human_agent"):
        assert termo in texto, termo
    assert H.foi_segunda_chance(texto) and not H.foi_segunda_chance("HANDOFF_OK · x")
