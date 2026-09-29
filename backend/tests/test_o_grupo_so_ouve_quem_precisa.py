# -*- coding: utf-8 -*-
"""SPEC-121 F1 — o grupo obedece UMA regra, e a janela de 7 dias vale de verdade.

O DEFEITO, MEDIDO
=================
📊 29/09/2026 (`investigacoes-2026-09-29/o-grupo-de-suporte.md` e o BLOCO 0 da
fatia, `f1/b0.sql`, só leitura): **29 de 29** avisos que saíram ao grupo desde
16/09 falavam de conversas que a atendente JÁ tinha atendido pelo celular
(237,6 a 295,7 h antes), com o agente de atendimento DESLIGADO e que o agente
nunca pediu. Legítimos: **0**. Três causas no código:

  1. o vigia lia `HUMAN_REQUESTED` — que o espelho grava quando a ATENDENTE
     responde — como "o agente pediu ajuda";
  2. a proteção vencia: claim por 6 h, janela limitada às últimas 40 linhas,
     sinistro e ✅ isentos, e na dúvida a porta AVISAVA;
  3. ninguém perguntava se o agente de atendimento estava ligado.

E a regra dos 7 dias do Founder não valia para as 477 conversas em
`HUMAN_REQUESTED` (todas do espelho): `pausar_ia` as calava PARA SEMPRE.

O QUE ESTE ARQUIVO PROVA — chamando o MOTOR, com dublê só no banco/HTTP/Redis
=============================================================================
T1  agente desligado → calado · CONTROLE ligado → enviado · CONTROLE cobrança e
    sentinela com o agente desligado → enviados · e sem PROVA → calado
T2  espelho HUMAN_REQUESTED + atendente há 8 dias + cliente agora: o vigia NÃO
    chega à porta · CONTROLE: o agente pediu e o aviso falhou → 1 envio
T3  atendente há 3 dias + 60 mensagens depois → calado (o teto de 40 caiu) ·
    CONTROLE sem gente → enviado
T4  claim de 6,1 h → calado · CONTROLE claim de 7 d 1 h → enviado
T5  sinistro e ✅ com a atendente há 2 dias → calados (pelo remetente REAL do ✅)
    · CONTROLE sem gente → enviados · e o ✅ `fechado_por_humano` cala
T6  leitura falha → aviso de conversa calado · CONTROLE cobrança → enviado
T7  🔴 G1: as 29 formas reais de 21/09, anonimizadas → ZERO envios (pelo vigia
    e pela porta com a prova mais forte) · e a corretora armada de hoje → zero
T8  vigia com 50 conversas e > 1.000 mensagens: nenhuma cortada vira aviso ·
    CONTROLE: a que tem PROVA, mesmo cortada do lote, avisa 1 vez
T9  🔴 a regra dos 7 dias: mensagem NOVA depois do vencimento → o agente fala,
    a conversa reabre, o histórico do modelo não traz as mensagens paradas, e
    ZERO aviso · CONTROLES: atendente há 3 dias → calado · sem mensagem nova →
    nada · o AGENTE pediu → como hoje · agente desligado → nada muda
G2  agente desligado → zero avisos de conversa em TODOS os tipos · CONTROLE:
    cobrança sai

🔴 AS MUTAÇÕES QUE TÊM DE FICAR VERMELHAS (rodadas pela fatia, em cópia):
tirar A · claim de volta a 6 h · teto de 40 de volta · sinistro isento de novo ·
fail-open de volta · sem a prova D6 no vigia · sem a regra B · sem a reabertura ·
sem o corte do histórico.

⛔ Nenhum dado pessoal: ids sintéticos, telefones de faixa de teste, textos
inventados. As 29 formas são NÚMEROS (horas, contagens), não conversas.
"""
from __future__ import annotations

import asyncio
import os
import sys
import types
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _pkg in ("app", "app.agents", "app.agents.tools", "app.core", "app.services",
             "app.services.atlas", "app.tasks"):
    if _pkg not in sys.modules:
        _m = types.ModuleType(_pkg)
        _m.__path__ = [os.path.join(_RAIZ, *_pkg.split("."))]
        sys.modules[_pkg] = _m

OK = 0
FAIL = 0


def certo(condicao, frase, detalhe=""):
    global OK, FAIL
    if condicao:
        OK += 1
        print("  ✅", frase)
    else:
        FAIL += 1
        print("  ❌", frase + (("\n       " + str(detalhe)) if detalhe else ""))


def rodar(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


# =============================================================================
# DUBLÊS — só a borda: o banco (PostgREST), o Redis e o envio de WhatsApp
# =============================================================================
TETO_POSTGREST = 1000


class _Resp:
    def __init__(self, data):
        self.data = data


class _Consulta:
    """PostgREST de mentira que HONRA filtro, ordem, limite e o teto de 1000."""

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

    def lt(self, c, v):
        self.filtros.append(("lt", c, v))
        return self

    def lte(self, c, v):
        self.filtros.append(("lte", c, v))
        return self

    def gte(self, c, v):
        self.filtros.append(("gte", c, v))
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
            if op == "lt" and not (x is not None and str(x) < str(v)):
                return False
            if op == "lte" and not (x is not None and str(x) <= str(v)):
                return False
            if op == "gte" and not (x is not None and str(x) >= str(v)):
                return False
        return True

    def execute(self):
        if self.t in self.b.quebradas:
            raise RuntimeError("banco fora do ar (%s)" % self.t)
        fonte = self.b.tabelas.setdefault(self.t, [])
        if self.acao == "insert":
            linhas = self.carga if isinstance(self.carga, list) else [self.carga]
            fonte.extend(dict(l) for l in linhas)
            return _Resp([dict(l) for l in linhas])
        achadas = [l for l in fonte if self._casa(l)]
        if self.acao == "update":
            for l in achadas:
                l.update(self.carga)
            return _Resp([dict(l) for l in achadas])
        if self.ordem:
            c, desc = self.ordem
            achadas = sorted(achadas, key=lambda l: str(l.get(c) or ""), reverse=desc)
        teto = min(self.teto or TETO_POSTGREST, TETO_POSTGREST)
        return _Resp([dict(l) for l in achadas[:teto]])


class Banco:
    def __init__(self, **tabelas):
        self.tabelas = {k: list(v) for k, v in tabelas.items()}
        self.quebradas = set()

    def table(self, nome):
        return _Consulta(self, nome)

    def eventos(self, prefixo=""):
        return [e for e in self.tabelas.get("work_events", [])
                if str(e.get("event_type") or "").startswith(prefixo)]


class _Embrulho:
    """O `SupabaseClient` da casa: o PostgREST mora em `.client`."""

    def __init__(self, banco):
        self.client = banco


class RedisFake:
    def __init__(self):
        self.chaves, self.contadores = {}, {}

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
        self.contadores[chave] = self.contadores.get(chave, 0) + 1
        return self.contadores[chave]

    async def expire(self, *_a, **_k):
        return True


ENVIOS: list = []
REDIS = RedisFake()
BANCO_ATUAL = {"b": Banco()}
_ANTES = {}


def _instalar(nome, modulo):
    if nome not in _ANTES:
        _ANTES[nome] = sys.modules.get(nome)
    sys.modules[nome] = modulo


def _instalar_dubles():
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

    # ⚠️ O resolvedor de destino é HTTP/banco de outra tabela — borda. O
    #    isolamento dele tem guardas próprios (SPEC-085).
    rot = types.ModuleType("app.services.dispatch_router")

    async def _destino(_empresa):
        return {"destino": "grupo-de-teste@g.us", "fonte": "teste", "recusa": ""}
    rot.resolver_destino_de_suporte = _destino
    _instalar("app.services.dispatch_router", rot)

    plat = types.ModuleType("app.services.platform_outbound")

    async def _conta(*_a, **_k):
        return None
    plat.record_platform_send = _conta
    _instalar("app.services.platform_outbound", plat)

    feed = types.ModuleType("app.services.activity_log")

    async def _feed(*_a, **_k):
        return None
    feed.log_activity = _feed
    _instalar("app.services.activity_log", feed)

    obs = types.ModuleType("app.services.observability")
    obs.sli = types.SimpleNamespace(HANDOFF_ESPERA="x", registrar=lambda *a, **k: None)
    _instalar("app.services.observability", obs)
    _instalar("app.services.observability.sli", obs.sli)

    import app.core.database as dbreal  # o módulo REAL (a montagem do histórico)
    _ANTES.setdefault("__get_supabase_client", dbreal.get_supabase_client)
    dbreal.get_supabase_client = lambda: _Embrulho(BANCO_ATUAL["b"])


def _restaurar():
    import app.core.database as dbreal

    if "__get_supabase_client" in _ANTES:
        dbreal.get_supabase_client = _ANTES.pop("__get_supabase_client")
    for nome, antigo in list(_ANTES.items()):
        if antigo is None:
            sys.modules.pop(nome, None)
        else:
            sys.modules[nome] = antigo
    _ANTES.clear()


# =============================================================================
# O CENÁRIO — duas corretoras reais do teste (§7): X com agente LIGADO, Y DESLIGADO
# =============================================================================
X = "11111111-1111-4111-8111-111111111111"
Y = "22222222-2222-4222-8222-222222222222"
AGORA = datetime.now(timezone.utc)


def iso(dt):
    """Sempre com microssegundos: o dublê compara datas como TEXTO, igual ao
    PostgREST com `timestamptz` serializado — e `isoformat()` omite `.000000`."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f+00:00")


def antes(**kw):
    return AGORA - timedelta(**kw)


def agentes():
    return [{"id": "ag-x", "company_id": X, "agent_role": "attendance", "is_active": True},
            {"id": "ag-y", "company_id": Y, "agent_role": "attendance", "is_active": False}]


def conversa(cid, empresa, *, status="open", claimed_by=None, claimed_by_name=None,
             claimed_at=None, motivo=None, ultima=None, telefone="5547900000000"):
    return {"id": cid, "company_id": empresa, "session_id": "ses-" + cid,
            "user_name": "Segurado Teste", "user_phone": telefone, "status": status,
            "claimed_by": claimed_by, "claimed_by_name": claimed_by_name,
            "claimed_at": iso(claimed_at) if claimed_at else None,
            "human_handoff_reason": motivo, "resolvido_em": None,
            "last_message_at": iso(ultima or antes(minutes=40)), "agent_id": None,
            "created_at": iso(antes(days=20))}


def msg(cid, papel, quando, texto, origem=None):
    linha = {"conversation_id": cid, "role": papel, "content": texto,
             "created_at": iso(quando), "type": "text", "payload": {}}
    if origem:
        linha["payload"] = {"origem": origem}
    return linha


def banco_com(conversas=(), mensagens=()):
    b = Banco(conversations=list(conversas), messages=list(mensagens),
              agents=agentes(), work_events=[], company_internal_numbers=[],
              company_members=[], users_v2=[], work_waits=[])
    BANCO_ATUAL["b"] = b
    return b


def porta(b, empresa, cid, tipo, prova="", sessao=None, conversa_linha=None):
    from app.services.o_grupo_so_o_que_importa import enviar_ao_grupo

    antes_n = len(ENVIOS)
    r = rodar(enviar_ao_grupo(
        b, company_id=empresa, tipo=tipo, texto="aviso de teste",
        conversation_id=cid, destino="grupo-de-teste@g.us",
        integration={"canal": "teste"}, dedup=False, agora=AGORA,
        prova_do_agente=prova, sessao=sessao, conversa=conversa_linha))
    return r, len(ENVIOS) - antes_n


def vigia(b):
    import importlib

    wd = importlib.import_module("app.tasks.handoff_watchdog")
    antes_n = len(ENVIOS)
    rodar(wd.varrer_handoffs_parados())
    return len(ENVIOS) - antes_n


def rodar_tudo():
    global OK, FAIL
    OK = FAIL = 0
    _instalar_dubles()
    try:
        _casos()
    finally:
        _restaurar()
    print()
    print("=" * 74)
    print("  %d asserções verdes · %d vermelhas" % (OK, FAIL))
    print("=" * 74)
    return OK, FAIL


def _casos():
    import app.services.o_grupo_so_o_que_importa as G
    import app.services.o_fim_do_atendimento as F

    N = F.janela_de_silencio_dias()
    certo(N == 7, "a janela da plataforma é %d dias — a MESMA do atendimento" % N)

    # ------------------------------------------------------------------ T1
    print("\n" + "=" * 74 + "\n  T1 — A: o agente de atendimento DESLIGADO cala o aviso de conversa\n" + "=" * 74)
    b = banco_com([conversa("c1x", X), conversa("c1y", Y)])
    r, n = porta(b, Y, "c1y", G.TIPO_PEDIDO_DE_AJUDA, G.PROVA_PEDIDO_DO_AGENTE)
    certo(n == 0 and r["calado"] and r["motivo"] == G.MOTIVO_AGENTE_DESLIGADO,
          "corretora com o agente DESLIGADO + pedido de ajuda → calado", r)
    calados = [e for e in b.eventos("grupo.calado")
               if e["payload_redacted"].get("calou_classe") == "agente_desligado"]
    certo(len(calados) == 1 and calados[0]["company_id"] == Y,
          "e o silêncio deixa rastro `grupo.calado` com a classe, NA corretora certa (§7)")
    r, n = porta(b, X, "c1x", G.TIPO_PEDIDO_DE_AJUDA, G.PROVA_PEDIDO_DO_AGENTE)
    certo(n == 1 and r["enviado"], "🔴 CONTROLE: a corretora com o agente LIGADO → enviado", r)
    r, n = porta(b, Y, "", G.TIPO_COBRANCA)
    certo(n == 1, "🔴 CONTROLE 2: cobrança (sem conversa) com o agente desligado → sai", r)
    r, n = porta(b, Y, "", G.TIPO_VIGIA)
    certo(n == 1, "🔴 CONTROLE 2: sentinela de regressão (sem conversa) com o agente desligado → sai", r)
    r, n = porta(b, X, "c1x", G.TIPO_PEDIDO_DE_AJUDA, "")
    certo(n == 0 and r["motivo"] == G.MOTIVO_SEM_PROVA,
          "regra B: agente ligado, conversa limpa, mas SEM prova de que o agente pediu → calado", r)
    r, n = porta(b, X, "c1x", G.TIPO_PEDIDO_DE_AJUDA, "HUMAN_REQUESTED")
    certo(n == 0, "regra B: o status do espelho NÃO é prova", r)

    # A é a MESMA pergunta do webhook — no mesmo banco, a mesma resposta
    from app.services.atlas.attendance_capture import attendance_agent_active

    b = banco_com([])
    sem = "55555555-5555-4555-8555-555555555555"
    iguais = [rodar(attendance_agent_active(e)) == rodar(G.agente_de_atendimento_ligado(b, e))
              for e in (X, Y, sem)]
    respostas = [rodar(G.agente_de_atendimento_ligado(b, e)) for e in (X, Y, sem)]
    b.quebradas.add("agents")
    iguais.append(rodar(attendance_agent_active(X)) == rodar(G.agente_de_atendimento_ligado(b, X)))
    certo(all(iguais) and respostas == [True, False, False],
          "a regra A responde IGUAL a `attendance_agent_active` (ligado · desligado · sem agente · "
          "banco quebrado)", (iguais, respostas))

    # ------------------------------------------------------------------ T2
    print("\n" + "=" * 74 + "\n  T2 — o vigia só avisa com a PROVA D6\n" + "=" * 74)
    ENVIOS.clear()
    REDIS.chaves.clear()
    esp = conversa("c2esp", X, status="HUMAN_REQUESTED",
                   claimed_by_name="Atendente pelo celular", claimed_at=antes(days=8),
                   ultima=antes(minutes=40))
    b = banco_com([esp], [
        msg("c2esp", "user", antes(days=8, minutes=10), "preciso de ajuda"),
        msg("c2esp", "assistant", antes(days=8), "estou vendo", origem="espelho"),
        msg("c2esp", "user", antes(minutes=40), "e agora?")])
    n = vigia(b)
    certo(n == 0, "espelho HUMAN_REQUESTED + atendente há 8 dias + cliente agora → ZERO avisos", n)
    certo(not b.eventos("grupo."),
          "e o vigia NEM CHEGA à porta (nenhum `grupo.enviado`/`grupo.calado` escrito)",
          b.eventos("grupo."))
    # D6 ②: o agente pediu há 10 dias, a ATENDENTE respondeu depois dele (há 8), e o
    # cliente voltou agora. O motivo gravado é velho: quem conhece a conversa é ela.
    velho = conversa("c2velho", X, status="HUMAN_REQUESTED", motivo="o segurado pediu uma pessoa",
                     ultima=antes(minutes=40))
    b = banco_com([velho], [
        msg("c2velho", "user", antes(days=10, minutes=5), "quero uma pessoa"),
        msg("c2velho", "assistant", antes(days=10), "vou chamar a equipe"),
        msg("c2velho", "assistant", antes(days=8), "resolvido por aqui", origem="espelho"),
        msg("c2velho", "user", antes(minutes=40), "voltei com outra coisa")])
    n = vigia(b)
    certo(n == 0,
          "motivo do agente ANTIGO + a atendente falou DEPOIS dele → sem prova D6, zero avisos", n)
    # CONTROLE: o AGENTE pediu (motivo gravado, fala dele depois de gente) e o aviso da hora falhou
    ped = conversa("c2ag", X, status="HUMAN_REQUESTED", motivo="o segurado pediu uma pessoa",
                   ultima=antes(minutes=40))
    b = banco_com([ped], [
        msg("c2ag", "user", antes(minutes=60), "quero falar com alguém"),
        msg("c2ag", "assistant", antes(minutes=55), "vou chamar a equipe"),
        msg("c2ag", "user", antes(minutes=40), "ok, aguardo")])
    n1 = vigia(b)
    n2 = vigia(b)
    certo(n1 == 1 and n2 == 0,
          "🔴 CONTROLE: o agente pediu e o aviso falhou → o vigia avisa UMA vez (%d, depois %d)" % (n1, n2))

    # ------------------------------------------------------------------ T3
    print("\n" + "=" * 74 + "\n  T3 — C: a janela lê os 7 dias INTEIROS (o teto de 40 caiu)\n" + "=" * 74)
    muitas = [msg("c3", "assistant", antes(days=3), "já estou cuidando", origem="espelho")]
    muitas += [msg("c3", "user", antes(days=3) + timedelta(minutes=5 * (i + 1)), "msg %d" % i)
               for i in range(60)]
    b = banco_com([conversa("c3", X)], muitas)
    r, n = porta(b, X, "c3", G.TIPO_PEDIDO_DE_AJUDA, G.PROVA_PEDIDO_DO_AGENTE)
    certo(n == 0 and r["calado"] and F.foi_a_janela(r["motivo"]),
          "atendente falou há 3 dias e vieram 60 mensagens depois → calado pela janela", r)
    ultima40 = F.ultima_palavra_humana(rodar(F.janela_de_mensagens(b, "c3"))[0])
    certo(ultima40 is None,
          "(e as 40 linhas de sempre NÃO a enxergam — é a leitura larga que acha)")
    b = banco_com([conversa("c3", X)], muitas[1:])
    r, n = porta(b, X, "c3", G.TIPO_PEDIDO_DE_AJUDA, G.PROVA_PEDIDO_DO_AGENTE)
    certo(n == 1, "🔴 CONTROLE: as mesmas 60 mensagens SEM fala de gente → enviado", r)

    # ------------------------------------------------------------------ T4
    print("\n" + "=" * 74 + "\n  T4 — C: o claim vale N dias, não 6 h\n" + "=" * 74)
    b = banco_com([conversa("c4", X, claimed_by_name="Atendente", claimed_at=antes(hours=6.1))])
    r, n = porta(b, X, "c4", G.TIPO_PEDIDO_DE_AJUDA, G.PROVA_PEDIDO_DO_AGENTE)
    certo(n == 0 and "assumiu" in r["motivo"], "claim de 6,1 h sem mensagem de gente → calado", r)
    b = banco_com([conversa("c4", X, claimed_by_name="Atendente",
                            claimed_at=antes(days=7, hours=1))])
    r, n = porta(b, X, "c4", G.TIPO_PEDIDO_DE_AJUDA, G.PROVA_PEDIDO_DO_AGENTE)
    certo(n == 1, "🔴 CONTROLE: claim de 7 dias e 1 h → enviado (não vira mordaça)", r)

    # ------------------------------------------------------------------ T5
    print("\n" + "=" * 74 + "\n  T5 — sinistro e ✅ obedecem à regra (D5)\n" + "=" * 74)
    com_gente = [msg("c5", "user", antes(days=2, minutes=5), "bati o carro"),
                 msg("c5", "assistant", antes(days=2), "já vou ver", origem="espelho")]
    b = banco_com([conversa("c5", X)], com_gente)
    r, n = porta(b, X, "c5", G.TIPO_SINISTRO, G.PROVA_PEDIDO_DO_AGENTE)
    certo(n == 0, "sinistro com a atendente há 2 dias → calado", r)
    antes_n = len(ENVIOS)
    rodar(F._contar_a_conclusao(_Embrulho(b), X, "c5", F.ACIONAMENTO_CONCLUIDO))
    certo(len(ENVIOS) == antes_n, "✅ (o remetente REAL, `_contar_a_conclusao`) com a atendente há 2 dias → calado")
    b = banco_com([conversa("c5", X)], com_gente[:1])
    r, n = porta(b, X, "c5", G.TIPO_SINISTRO, G.PROVA_PEDIDO_DO_AGENTE)
    certo(n == 1, "🔴 CONTROLE: sinistro sem gente na conversa → enviado", r)
    antes_n = len(ENVIOS)
    rodar(F._contar_a_conclusao(_Embrulho(b), X, "c5", F.ACIONAMENTO_CONCLUIDO))
    certo(len(ENVIOS) == antes_n + 1, "🔴 CONTROLE: ✅ do acionamento que o AGENTE concluiu → enviado")
    antes_n = len(ENVIOS)
    rodar(F._contar_a_conclusao(_Embrulho(b), X, "c5", F.FECHADO_POR_HUMANO))
    certo(len(ENVIOS) == antes_n, "✅ `fechado_por_humano` (trabalho da equipe) → calado: a equipe já sabe")

    # ------------------------------------------------------------------ T6
    print("\n" + "=" * 74 + "\n  T6 — na DÚVIDA a porta cala o aviso de conversa (D3/D4)\n" + "=" * 74)
    b = banco_com([conversa("c6", X)])
    b.quebradas.add("messages")
    r, n = porta(b, X, "c6", G.TIPO_PEDIDO_DE_AJUDA, G.PROVA_PEDIDO_DO_AGENTE)
    certo(n == 0 and r["motivo"] == G.MOTIVO_SEM_LEITURA, "mensagens ilegíveis → calado", r)
    r, n = porta(b, X, "", G.TIPO_COBRANCA)
    certo(n == 1, "🔴 CONTROLE: cobrança com o MESMO banco quebrado → sai", r)
    b = banco_com([])
    r, n = porta(b, X, "conversa-que-nao-existe", G.TIPO_PEDIDO_DE_AJUDA, G.PROVA_PEDIDO_DO_AGENTE)
    certo(n == 0, "conversa que não se consegue ler → calado", r)
    b = banco_com([conversa("c6", X)])
    b.quebradas.add("agents")
    r, n = porta(b, X, "c6", G.TIPO_PEDIDO_DE_AJUDA, G.PROVA_PEDIDO_DO_AGENTE)
    certo(n == 0 and r["motivo"] == G.MOTIVO_AGENTE_DESLIGADO,
          "não dá para saber se o agente está ligado → calado (A é fail-closed)", r)

    # ------------------------------------------------------------------ T7
    print("\n" + "=" * 74 + "\n  T7 — 🔴 G1: as 29 formas reais de 21/09 → ZERO envios\n" + "=" * 74)
    # 📊 `bloco0/g_classif.txt` + `f1/b0.sql` (29/09/2026). Por aviso: tipo · horas
    #    entre a última fala da atendente e o aviso · mensagens do segurado DEPOIS
    #    dela · falas do agente (todas ANTES dela) · o motivo do agente existia?
    FORMAS = [
        ("p", 238.1, 2, 0, 0), ("p", 237.6, 3, 0, 0), ("p", 270.4, 0, 0, 0),
        ("p", 295.7, 0, 2, 0), ("p", 273.1, 0, 0, 0), ("p", 271.2, 0, 0, 0),
        ("p", 268.5, 0, 0, 0), ("p", 268.3, 0, 0, 0), ("s", 267.3, 0, 6, 1),
        ("p", 266.8, 0, 0, 0), ("p", 266.7, 0, 0, 0), ("p", 266.6, 0, 0, 0),
        ("p", 266.0, 0, 0, 0), ("p", 248.9, 0, 0, 0), ("p", 248.7, 0, 0, 0),
        ("p", 247.9, 0, 0, 0), ("p", 247.9, 0, 0, 0), ("p", 247.9, 0, 4, 0),
        ("p", 247.8, 0, 0, 0), ("p", 247.7, 0, 0, 0), ("p", 247.3, 0, 0, 0),
        ("p", 245.3, 0, 0, 0), ("p", 245.0, 0, 0, 0), ("p", 244.6, 0, 0, 0),
        ("p", 244.5, 0, 0, 0), ("p", 244.3, 0, 0, 0), ("p", 242.9, 0, 0, 0),
        ("p", 242.9, 0, 0, 0), ("p", 241.6, 0, 0, 0),
    ]
    certo(len(FORMAS) == 29, "as 29 formas estão aqui (📊 29 de 29 avisos de 21/09)")
    convs, msgs = [], []
    for i, (tipo, horas, depois, falas, com_motivo) in enumerate(FORMAS):
        cid = "c7-%02d" % i
        empresa = Y if i % 2 else "33333333-3333-4333-8333-33333333333%d" % (i % 3)
        humana = antes(hours=horas)
        convs.append(conversa(cid, empresa, status="HUMAN_REQUESTED",
                              claimed_by_name="Atendente pelo celular", claimed_at=humana,
                              motivo=("relato de sinistro" if com_motivo else None),
                              ultima=antes(minutes=45)))
        msgs.append(msg(cid, "user", humana - timedelta(minutes=30), "pergunta"))
        for k in range(falas):
            msgs.append(msg(cid, "assistant", humana - timedelta(minutes=20 - k), "resposta %d" % k))
        msgs.append(msg(cid, "assistant", humana, "resposta da atendente", origem="espelho"))
        for k in range(depois):
            msgs.append(msg(cid, "user", humana + timedelta(minutes=30 + k), "obrigado %d" % k))
    ENVIOS.clear()
    REDIS.chaves.clear()
    b = banco_com(convs, msgs)
    b.tabelas["agents"] += [{"id": "ag-z%d" % k, "company_id": "33333333-3333-4333-8333-33333333333%d" % k,
                             "agent_role": "attendance", "is_active": False} for k in range(3)]
    n = vigia(b)
    certo(n == 0, "🔴 o VIGIA, armado ao máximo (cliente escreveu há 45 min em todas) → ZERO envios", n)
    enviados = 0
    for c, (tipo, *_r) in zip(convs, FORMAS):
        _, k = porta(b, c["company_id"], c["id"],
                     G.TIPO_SINISTRO if tipo == "s" else G.TIPO_PEDIDO_DE_AJUDA,
                     G.PROVA_PEDIDO_DO_AGENTE)
        enviados += k
    certo(enviados == 0,
          "🔴 e a PORTA, mesmo com a prova mais forte (como se o agente tivesse pedido) → ZERO", enviados)
    # A corretora ARMADA hoje: destino ativo, agente desligado, 4 conversas do espelho
    # 📊 `f1/b0.sql`: atendente há 1,7 · 23,0 · 44,7 · 48,6 h; cliente por último nas 4.
    armada = "44444444-4444-4444-8444-444444444444"
    convs3, msgs3 = [], []
    for i, (h_humana, h_ult) in enumerate([(1.7, 0.7), (23.0, 9.0), (44.7, 44.3), (48.6, 48.6)]):
        cid = "c7-armada-%d" % i
        convs3.append(conversa(cid, armada, status="HUMAN_REQUESTED",
                               claimed_by_name="Atendente pelo celular",
                               claimed_at=antes(hours=h_humana), ultima=antes(hours=h_ult)))
        msgs3.append(msg(cid, "assistant", antes(hours=h_humana), "oi", origem="espelho"))
        msgs3.append(msg(cid, "user", antes(hours=h_ult), "voltei"))
    b = banco_com(convs3, msgs3)
    b.tabelas["agents"].append({"id": "ag-a", "company_id": armada,
                                "agent_role": "attendance", "is_active": False})
    n = vigia(b)
    enviados = sum(porta(b, armada, c["id"], G.TIPO_PEDIDO_DE_AJUDA,
                         G.PROVA_PEDIDO_DO_AGENTE)[1] for c in convs3)
    certo(n == 0 and enviados == 0,
          "🔴 a corretora armada de hoje (destino ATIVO, agente desligado) → zero (vigia %d · porta %d)"
          % (n, enviados))

    # ------------------------------------------------------------------ T8
    print("\n" + "=" * 74 + "\n  T8 — o lote cortado pelo PostgREST não vira aviso\n" + "=" * 74)
    ENVIOS.clear()
    REDIS.chaves.clear()
    convs8, msgs8 = [], []
    for i in range(49):
        cid = "c8-%02d" % i
        base = 31 + i * 1.2     # cada conversa ocupa ~1 min; as mais velhas saem do lote
        convs8.append(conversa(cid, X, status="HUMAN_REQUESTED", motivo="pedido antigo",
                               ultima=antes(minutes=base)))
        for k in range(25):     # 49 × 25 = 1.225 mensagens, e a última é da ATENDENTE
            papel, origem = ("assistant", "espelho") if k == 24 else ("user", None)
            msgs8.append(msg(cid, papel, antes(minutes=base + (24 - k) * 0.04), "m%d" % k, origem))
    # CONTROLE: a que TEM prova (o agente pediu, falou depois de gente, o cliente espera),
    # com mensagens MAIS VELHAS que o corte do lote — ela some do lote.
    convs8.append(conversa("c8-prova", X, status="HUMAN_REQUESTED", motivo="o segurado pediu uma pessoa",
                           ultima=antes(minutes=50)))
    msgs8 += [msg("c8-prova", "user", antes(minutes=100), "quero uma pessoa"),
              msg("c8-prova", "assistant", antes(minutes=99), "vou chamar"),
              msg("c8-prova", "user", antes(minutes=98), "ok")]
    certo(len(msgs8) > 1000, "o cenário soma %d mensagens (> 1.000)" % len(msgs8))
    b = banco_com(convs8, msgs8)
    lote = b.table("messages").select("*").in_("conversation_id", [c["id"] for c in convs8]) \
        .order("created_at", desc=True).limit(1500).execute().data
    cortadas = {c["id"] for c in convs8} - {m["conversation_id"] for m in lote}
    certo("c8-prova" in cortadas and len(cortadas) >= 2,
          "(o dublê corta o lote como o PostgREST: %d conversas somem dele)" % len(cortadas))
    n = vigia(b)
    certo(n == 1,
          "🔴 nenhuma das 49 com a última palavra da atendente vira aviso · CONTROLE: a que tem "
          "PROVA, mesmo cortada do lote, avisa 1 vez (%d envio)" % n)

    # ------------------------------------------------------------------ T9
    print("\n" + "=" * 74 + "\n  T9 — 🔴 a regra dos 7 dias do Founder\n" + "=" * 74)
    from app.core.database import SupabaseClient

    def _cenario(cid, empresa, *, humana_ha_dias, motivo=None):
        # ⚠️ O relógio é o de AGORA, não o do começo do arquivo: a montagem do
        #    histórico usa o relógio real, e "a mensagem nova" tem de estar no
        #    turno de verdade (< 120 s) quando o histórico é lido.
        ja = datetime.now(timezone.utc)
        linha = conversa(cid, empresa, status="HUMAN_REQUESTED",
                         claimed_by_name="Atendente pelo celular",
                         claimed_at=ja - timedelta(days=humana_ha_dias), motivo=motivo,
                         ultima=ja - timedelta(seconds=5))
        ms = [msg(cid, "user", ja - timedelta(days=9), "pergunta do começo"),
              msg(cid, "assistant", ja - timedelta(days=humana_ha_dias),
                  "resposta da atendente", origem="espelho"),
              msg(cid, "user", ja - timedelta(days=5), "PERGUNTA VELHA DO DIA 3"),
              msg(cid, "user", ja - timedelta(days=3), "PERGUNTA VELHA DO DIA 5"),
              msg(cid, "user", ja - timedelta(seconds=5), "MENSAGEM NOVA DE HOJE")]
        return linha, ms

    ENVIOS.clear()
    REDIS.chaves.clear()
    linha, ms = _cenario("c9", X, humana_ha_dias=8)
    b = banco_com([linha], ms)
    calar, motivo = rodar(F.a_ia_deve_calar(b, company_id=X, conversa=dict(linha),
                                            por_mensagem_nova=True))
    certo(calar is False, "atendente há 8 dias + mensagem NOVA → o agente RESPONDE", motivo)
    certo(b.tabelas["conversations"][0]["status"] == "open"
          and b.tabelas["conversations"][0]["claimed_by_name"] is None,
          "a conversa REABRE (open, sem 'Atendente pelo celular')", b.tabelas["conversations"][0]["status"])
    certo(len(b.eventos(F.EVENTO_REABERTA_PELA_JANELA)) == 1
          and b.eventos(F.EVENTO_REABERTA_PELA_JANELA)[0]["company_id"] == X,
          "com o rastro `conversa.reaberta_pela_janela` na corretora certa")
    cli = SupabaseClient.__new__(SupabaseClient)
    cli.client = b
    historico = cli.get_conversation_history("ses-c9", X, limit=60)
    textos = [m["content"] for m in historico]
    certo("MENSAGEM NOVA DE HOJE" in textos and not any("VELHA" in t for t in textos),
          "o HISTÓRICO do modelo traz a mensagem nova e NÃO as dos dias 3 e 5", textos)
    certo("pergunta do começo" in textos and "resposta da atendente" in textos,
          "e a conversa de antes do silêncio fica como MEMÓRIA", textos)
    bloco = rodar(F.bloco_do_reencontro(b, company_id=X, conversation_id="c9"))
    certo("ASSUNTO NOVO" in bloco and "NÃO são pendências" in bloco,
          "o bloco do reencontro diz ASSUNTO NOVO e que as paradas não são pendência", bloco[:120])
    certo(vigia(b) == 0 and not b.eventos("grupo."), "e ZERO aviso ao grupo pela reabertura")
    calar2, _ = rodar(F.a_ia_deve_calar(b, company_id=X, conversa=dict(b.tabelas["conversations"][0]),
                                        por_mensagem_nova=True))
    certo(calar2 is False and len(b.eventos(F.EVENTO_REABERTA_PELA_JANELA)) == 1,
          "a próxima mensagem segue atendida, sem reabrir de novo (idempotente)")

    linha, ms = _cenario("c9b", X, humana_ha_dias=3)
    b = banco_com([linha], ms)
    calar, motivo = rodar(F.a_ia_deve_calar(b, company_id=X, conversa=dict(linha),
                                            por_mensagem_nova=True))
    certo(calar is True and F.foi_a_janela(motivo)
          and b.tabelas["conversations"][0]["status"] == "HUMAN_REQUESTED",
          "🔴 CONTROLE 1: a atendente falou há 3 dias → o agente CALA e a conversa segue dela", motivo)
    certo(vigia(b) == 0 and not b.eventos("grupo.") and not b.eventos("conversa."),
          "   e zero grupo, zero reabertura")

    linha, ms = _cenario("c9c", X, humana_ha_dias=8)
    b = banco_com([linha], ms)
    calar, _ = rodar(F.a_ia_deve_calar(b, company_id=X, conversa=dict(linha)))
    certo(calar is True and b.tabelas["conversations"][0]["status"] == "HUMAN_REQUESTED"
          and not b.eventos("conversa."),
          "🔴 CONTROLE 2: sem mensagem nova (o caminho proativo) → nada acontece, nenhuma resposta")
    certo(vigia(b) == 0, "   e o vigia não avisa nem responde nada por ela")

    linha, ms = _cenario("c9d", X, humana_ha_dias=8, motivo="o segurado pediu uma pessoa")
    b = banco_com([linha], ms)
    calar, motivo = rodar(F.a_ia_deve_calar(b, company_id=X, conversa=dict(linha),
                                            por_mensagem_nova=True))
    certo(calar is True and "pediu para falar com uma pessoa" in motivo
          and b.tabelas["conversations"][0]["status"] == "HUMAN_REQUESTED",
          "🔴 CONTROLE 3: o AGENTE pediu ajuda (human_handoff_reason) → como hoje: calado", motivo)

    linha, ms = _cenario("c9e", Y, humana_ha_dias=8)
    b = banco_com([linha], ms)
    calar, _ = rodar(F.a_ia_deve_calar(b, company_id=Y, conversa=dict(linha),
                                       por_mensagem_nova=True))
    certo(calar is True and b.tabelas["conversations"][0]["status"] == "HUMAN_REQUESTED",
          "🔴 CONTROLE 4: agente DESLIGADO → a conversa NÃO sai da Fila (não reabre)")

    ja = datetime.now(timezone.utc)
    b = banco_com([conversa("c9f", X)], [
        msg("c9f", "user", ja - timedelta(hours=2), "oi"),
        msg("c9f", "assistant", ja - timedelta(hours=1), "olá, como posso ajudar?"),
        msg("c9f", "user", ja - timedelta(seconds=5), "tenho outra dúvida")])
    cli.client = b
    certo(len(cli.get_conversation_history("ses-c9f", X, limit=60)) == 3
          and "pendências" not in rodar(F.bloco_do_reencontro(b, company_id=X, conversation_id="c9f")),
          "🔴 CONTROLE 5: conversa normal (o agente falou há 1 h) → histórico inteiro, sem aviso de pendência")

    # ------------------------------------------------------------------ G2
    print("\n" + "=" * 74 + "\n  G2 — agente desligado: ZERO avisos de conversa, em todo tipo\n" + "=" * 74)
    ENVIOS.clear()
    b = banco_com([conversa("g2", Y)])
    sessao = {"case_id": "caso-teste", "mirror_conversation_id": "", "client_phone": ""}
    casos = [(G.TIPO_PEDIDO_DE_AJUDA, "g2", G.PROVA_PEDIDO_DO_AGENTE, None),
             (G.TIPO_SINISTRO, "g2", G.PROVA_PEDIDO_DO_AGENTE, None),
             (G.TIPO_CONCLUSAO, "g2", G.PROVA_ACIONAMENTO, None),
             (G.TIPO_ESPERA_VENCIDA, "g2", G.PROVA_ESPERA_DO_AGENTE, None),
             (G.TIPO_RETOMADA, "g2", G.PROVA_ACIONAMENTO, None),
             (G.TIPO_VIGIA, "", G.PROVA_ACIONAMENTO, sessao),
             (G.TIPO_PEDIDO_DE_AJUDA, "", G.PROVA_ACIONAMENTO, sessao)]
    total = sum(porta(b, Y, cid, tipo, prova, sessao=s)[1] for tipo, cid, prova, s in casos)
    certo(total == 0, "%d tipos de aviso de conversa com o agente desligado → 0 envios" % len(casos), total)
    r, n = porta(b, Y, "", G.TIPO_COBRANCA)
    certo(n == 1, "🔴 CONTROLE: a cobrança da mesma corretora sai", r)
    r, n = porta(b, Y, "", G.TIPO_RESUMO_DIARIO)
    certo(n == 1, "🔴 CONTROLE: o resumo (isento) continua sendo decidido por quem o chama", r)


def test_o_grupo_so_ouve_quem_precisa():
    _ok, falhas = rodar_tudo()
    assert falhas == 0


if __name__ == "__main__":
    _ok, _falhas = rodar_tudo()
    sys.exit(1 if _falhas else 0)
