# -*- coding: utf-8 -*-
"""SPEC-121 · CONSERTO ÚNICO · parte X — a janela de 7 dias, o pedido do agente,
o histórico, o custo da leitura larga e o resumo das 19h.

O QUE CADA BLOCO PROVA — pelo MOTOR, com dublê só no banco/Redis/feed
=====================================================================
P1  (juiz P1) `human_handoff_reason = ''` + atendente há 8 dias + mensagem NOVA → o
    agente responde E a conversa REABRE. 📊 Antes: o agente respondia e a conversa
    ficava em HUMAN_REQUESTED (na Fila), porque o UPDATE só casava `IS NULL`.
    CONTROLE: o NULL de sempre reabre igual.
P2  (juiz P2 / red P7 — DECISÃO DO GERENTE sobre a D3 do Founder) o AGENTE pediu
    ajuda, uma PESSOA atendeu depois, 7+ dias sem gente, mensagem NOVA → reabre como
    conversa nova (e o motivo sai). CONTROLES: ninguém atendeu depois do pedido →
    segue calado, na Fila, e o vigia TEM a prova D6 para avisar · atendente há 3 dias
    → calado · sem mensagem nova → nada · agente desligado → nada · `Admin
    Intervention` → nada.
P5  (juiz P5) a última fala da corretora FORA das 20 mensagens do histórico: as
    paradas saem do histórico e o bloco do reencontro diz que não são pendência.
    CONTROLE: a corretora falou há 2 dias (também fora da fatia) → nada sai.
L   (red P5) a leitura LARGA num turno do webhook (entrada + saída + porta do
    grupo): 📊 medida pelo motor = 3 sem a memória (ver MUTAÇÃO L), 1 com ela.
    CONTROLE: a atendente que fala NO MEIO do turno continua calando o agente.
K3  o resumo das 19h conta cada silêncio do grupo na SUA classe. 📊 Antes: todo
    `grupo.calado` não-"assumiu" virava "fiquei em silêncio pela janela".
    CONTROLE: os eventos antigos (sem `calou_classe`) caem no mesmo lugar de antes.

🔴 MUTAÇÕES (em cópia, `git worktree`): P1 UPDATE de volta a `IS NULL` · P2 sem
`marca_do_agente` na porta · P2 sem a pergunta "gente atendeu depois?" · P5 sem a
medição no banco · L sem a memória · K3 de volta ao "todo calado é janela".

⛔ Nenhum dado pessoal: ids sintéticos, telefones de faixa de teste.
Roda com `python tests/test_spec121_conserto_grupo.py` (exit ≠ 0 em falha) E `pytest`.
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
        print("  ❌", frase + (("\n       " + str(detalhe)[:500]) if detalhe else ""))


def rodar(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


# =============================================================================
# DUBLÊS — só a borda
# =============================================================================
class _Resp:
    def __init__(self, data):
        self.data = data


class _Consulta:
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
        if self.t == "messages" and self.teto == 1000:
            self.b.leituras_largas += 1
        if self.ordem:
            c, desc = self.ordem
            achadas = sorted(achadas, key=lambda l: str(l.get(c) or ""), reverse=desc)
        teto = min(self.teto or 1000, 1000)
        return _Resp([dict(l) for l in achadas[:teto]])


class Banco:
    def __init__(self, **tabelas):
        self.tabelas = {k: list(v) for k, v in tabelas.items()}
        self.leituras_largas = 0

    def table(self, nome):
        return _Consulta(self, nome)

    def eventos(self, prefixo=""):
        return [e for e in self.tabelas.get("work_events", [])
                if str(e.get("event_type") or "").startswith(prefixo)]


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


REDIS = RedisFake()
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

    feed = types.ModuleType("app.services.activity_log")

    async def _feed(*_a, **_k):
        return None
    feed.log_activity = _feed
    _instalar("app.services.activity_log", feed)

    plat = types.ModuleType("app.services.platform_outbound")

    async def _conta(*_a, **_k):
        return None
    plat.record_platform_send = _conta
    plat.fuso_da_corretora = lambda *_a, **_k: timezone(timedelta(hours=-3))
    _instalar("app.services.platform_outbound", plat)


def _restaurar():
    for nome, antigo in list(_ANTES.items()):
        if antigo is None:
            sys.modules.pop(nome, None)
        else:
            sys.modules[nome] = antigo
    _ANTES.clear()


# =============================================================================
# O CENÁRIO — X com o agente LIGADO, Y DESLIGADO (duas corretoras, §7)
# =============================================================================
X = "11111111-1111-4111-8111-111111111111"
Y = "22222222-2222-4222-8222-222222222222"


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f+00:00")


def agentes():
    return [{"id": "ag-x", "company_id": X, "agent_role": "attendance", "is_active": True},
            {"id": "ag-y", "company_id": Y, "agent_role": "attendance", "is_active": False}]


def conversa(cid, empresa, *, status="HUMAN_REQUESTED", motivo=None, claimed_at=None):
    ja = datetime.now(timezone.utc)
    return {"id": cid, "company_id": empresa, "session_id": "ses-" + cid,
            "user_name": "Segurado Teste", "user_phone": "5547900000000", "status": status,
            "claimed_by": None, "claimed_by_name": None,
            "claimed_at": iso(claimed_at) if claimed_at else None,
            "human_handoff_reason": motivo, "resolvido_em": None,
            "last_message_at": iso(ja - timedelta(seconds=5)), "agent_id": None,
            "created_at": iso(ja - timedelta(days=30))}


def msg(cid, papel, quando, texto, origem=None):
    linha = {"conversation_id": cid, "role": papel, "content": texto,
             "created_at": iso(quando), "type": "text", "payload": {}}
    if origem:
        linha["payload"] = {"origem": origem}
    return linha


def banco_com(conversas=(), mensagens=()):
    return Banco(conversations=list(conversas), messages=list(mensagens), agents=agentes(),
                 work_events=[], company_internal_numbers=[], company_members=[],
                 users_v2=[], work_waits=[])


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
    import app.services.o_fim_do_atendimento as F

    # ------------------------------------------------------------------ P1
    print("\n" + "=" * 74 + "\n  P1 — '' e NULL: um critério só\n" + "=" * 74)
    for rotulo, valor in (("motivo ''", ""), ("🔴 CONTROLE: motivo NULL", None)):
        ja = datetime.now(timezone.utc)
        cid = "p1-%s" % ("vazio" if valor == "" else "nulo")
        b = banco_com([conversa(cid, X, motivo=valor)], [
            msg(cid, "user", ja - timedelta(days=9), "pergunta antiga"),
            msg(cid, "assistant", ja - timedelta(days=8), "resposta da atendente", "espelho"),
            msg(cid, "user", ja - timedelta(seconds=5), "mensagem nova")])
        calar, motivo = rodar(F.a_ia_deve_calar(b, company_id=X,
                                                conversa=dict(b.tabelas["conversations"][0]),
                                                por_mensagem_nova=True))
        linha = b.tabelas["conversations"][0]
        certo(calar is False and linha["status"] == "open"
              and linha["human_handoff_reason"] is None
              and len(b.eventos(F.EVENTO_REABERTA_PELA_JANELA)) == 1,
              "%s + atendente há 8 dias + mensagem NOVA → responde E a conversa REABRE" % rotulo,
              (calar, motivo, linha["status"], linha["human_handoff_reason"]))
    certo(F.marca_do_espelho({"status": "HUMAN_REQUESTED", "human_handoff_reason": ""})
          and not F.marca_do_agente({"status": "HUMAN_REQUESTED", "human_handoff_reason": ""}),
          "'' é marca do ESPELHO (e não do agente) — o mesmo critério da leitura e da escrita")

    # ------------------------------------------------------------------ P2
    print("\n" + "=" * 74 + "\n  P2 — o pedido do AGENTE que uma pessoa atendeu vence em 7 dias\n"
          + "=" * 74)

    def _pedido(cid, empresa, *, gente_ha_dias=None, motivo="o segurado pediu uma pessoa"):
        ja = datetime.now(timezone.utc)
        ms = [msg(cid, "user", ja - timedelta(days=11), "quero falar com alguém"),
              msg(cid, "assistant", ja - timedelta(days=10), "já passei para a equipe")]
        if gente_ha_dias is not None:
            ms.append(msg(cid, "assistant", ja - timedelta(days=gente_ha_dias),
                          "oi, aqui é da corretora", "espelho"))
        ms += [msg(cid, "user", ja - timedelta(days=5), "PARADA DO DIA 5"),
               msg(cid, "user", ja - timedelta(seconds=5), "MENSAGEM NOVA")]
        return banco_com([conversa(cid, empresa, motivo=motivo)], ms)

    b = _pedido("p2a", X, gente_ha_dias=9)
    calar, motivo = rodar(F.a_ia_deve_calar(b, company_id=X,
                                            conversa=dict(b.tabelas["conversations"][0]),
                                            por_mensagem_nova=True))
    linha = b.tabelas["conversations"][0]
    certo(calar is False and linha["status"] == "open" and linha["human_handoff_reason"] is None,
          "o agente pediu, a atendente atendeu há 9 dias, mensagem NOVA → conversa NOVA "
          "(open, sem o motivo antigo)", (calar, motivo, linha["status"]))
    certo(len(b.eventos(F.EVENTO_REABERTA_PELA_JANELA)) == 1
          and b.eventos(F.EVENTO_REABERTA_PELA_JANELA)[0]["company_id"] == X,
          "   com o rastro `conversa.reaberta_pela_janela` na corretora certa")

    b = _pedido("p2b", X, gente_ha_dias=None)
    calar, motivo = rodar(F.a_ia_deve_calar(b, company_id=X,
                                            conversa=dict(b.tabelas["conversations"][0]),
                                            por_mensagem_nova=True))
    linha = b.tabelas["conversations"][0]
    certo(calar is True and linha["status"] == "HUMAN_REQUESTED"
          and linha["human_handoff_reason"] == "o segurado pediu uma pessoa"
          and not b.eventos("conversa."),
          "🔴 CONTROLE: o agente pediu e NINGUÉM atendeu → segue esperando gente (calado, na Fila)",
          (calar, motivo, linha["status"]))
    import app.tasks.handoff_watchdog as WD
    certo(rodar(WD.prova_de_que_o_agente_pediu(b, dict(linha))) is True,
          "   e o vigia TEM a prova D6 para avisar o grupo (é ele quem chama gente)")

    b = _pedido("p2c", X, gente_ha_dias=3)
    calar, motivo = rodar(F.a_ia_deve_calar(b, company_id=X,
                                            conversa=dict(b.tabelas["conversations"][0]),
                                            por_mensagem_nova=True))
    certo(calar is True and F.foi_a_janela(motivo)
          and b.tabelas["conversations"][0]["status"] == "HUMAN_REQUESTED",
          "🔴 CONTROLE: a atendente atendeu há 3 dias → calado pela janela", motivo)

    b = _pedido("p2d", X, gente_ha_dias=9)
    calar, _ = rodar(F.a_ia_deve_calar(b, company_id=X,
                                       conversa=dict(b.tabelas["conversations"][0])))
    certo(calar is True and b.tabelas["conversations"][0]["status"] == "HUMAN_REQUESTED",
          "🔴 CONTROLE: sem mensagem NOVA (o proativo) → nada reabre")

    b = _pedido("p2e", Y, gente_ha_dias=9)
    calar, _ = rodar(F.a_ia_deve_calar(b, company_id=Y,
                                       conversa=dict(b.tabelas["conversations"][0]),
                                       por_mensagem_nova=True))
    certo(calar is True and b.tabelas["conversations"][0]["status"] == "HUMAN_REQUESTED",
          "🔴 CONTROLE: corretora com o agente DESLIGADO → não reabre (segue na Fila)")

    b = _pedido("p2f", X, gente_ha_dias=9, motivo=F.MOTIVO_DO_ADMIN)
    calar, _ = rodar(F.a_ia_deve_calar(b, company_id=X,
                                       conversa=dict(b.tabelas["conversations"][0]),
                                       por_mensagem_nova=True))
    certo(calar is True and b.tabelas["conversations"][0]["status"] == "HUMAN_REQUESTED",
          "🔴 CONTROLE: `Admin Intervention` (mão humana do painel) → não reabre")

    # ------------------------------------------------------------------ P5
    print("\n" + "=" * 74 + "\n  P5 — a fala da corretora FORA das 20 do histórico\n" + "=" * 74)
    from app.core.database import SupabaseClient

    def _enxurrada(cid, *, nossa_ha_dias):
        ja = datetime.now(timezone.utc)
        ms = [msg(cid, "user", ja - timedelta(days=nossa_ha_dias, hours=1), "pergunta de antes"),
              msg(cid, "assistant", ja - timedelta(days=nossa_ha_dias), "resposta da corretora")]
        for k in range(25):   # 25 do segurado DEPOIS da corretora: a fatia de 20 não a alcança
            ms.append(msg(cid, "user", ja - timedelta(days=nossa_ha_dias) + timedelta(
                minutes=10 * (k + 1)), "PARADA %02d" % k))
        ms.append(msg(cid, "user", ja - timedelta(seconds=5), "MENSAGEM NOVA"))
        return banco_com([conversa(cid, X, status="open")], ms)

    cli = SupabaseClient.__new__(SupabaseClient)
    b = _enxurrada("p5a", nossa_ha_dias=9)
    cli.client = b
    hist = [m["content"] for m in cli.get_conversation_history("ses-p5a", X, limit=20)]
    certo(hist == ["MENSAGEM NOVA"],
          "corretora falou há 9 dias e vieram 25 mensagens depois → o histórico traz SÓ a nova",
          hist[:5])
    bloco = rodar(F.bloco_do_reencontro(b, company_id=X, conversation_id="p5a"))
    certo("NÃO são pendências" in bloco and "9 dias" in bloco,
          "e o bloco do reencontro diz ASSUNTO NOVO há 9 dias, sem pendências", bloco[:160])
    b = _enxurrada("p5b", nossa_ha_dias=2)
    cli.client = b
    hist = cli.get_conversation_history("ses-p5b", X, limit=20)
    certo(len(hist) == 20 and "pendências" not in rodar(
        F.bloco_do_reencontro(b, company_id=X, conversation_id="p5b")),
          "🔴 CONTROLE: a corretora falou há 2 dias (também fora da fatia) → nada sai", len(hist))

    # ------------------------------------------------------------------ L
    print("\n" + "=" * 74 + "\n  L — a leitura LARGA num turno do webhook\n" + "=" * 74)
    import app.services.o_grupo_so_o_que_importa as G

    def _longa(cid):
        ja = datetime.now(timezone.utc)
        ms = []
        for k in range(60):   # 60 falas em 3 dias, sem gente: as 40 cabem na janela
            papel = "user" if k % 2 == 0 else "assistant"
            ms.append(msg(cid, papel, ja - timedelta(days=3) + timedelta(minutes=30 * k),
                          "fala %02d" % k))
        ms.append(msg(cid, "user", ja - timedelta(seconds=5), "mensagem nova"))
        return banco_com([conversa(cid, X, status="open")], ms)

    b = _longa("l1")
    linha = dict(b.tabelas["conversations"][0])
    c1, _ = rodar(F.a_ia_deve_calar(b, company_id=X, conversa=linha, por_mensagem_nova=True))
    c2, _ = rodar(F.a_ia_deve_calar(b, company_id=X, conversa=linha, por_mensagem_nova=True))
    pode, porque = rodar(G.o_grupo_pode_saber(
        b, company_id=X, conversation_id="l1", tipo=G.TIPO_PEDIDO_DE_AJUDA,
        prova_do_agente=G.PROVA_PEDIDO_DO_AGENTE))
    print("     📊 leituras largas no turno (entrada + saída + porta do grupo): %d"
          % b.leituras_largas)
    certo(c1 is False and c2 is False and pode is True,
          "o turno segue igual: o agente fala e o grupo pode ser avisado", (c1, c2, pode, porque))
    certo(b.leituras_largas == 1,
          "🔴 a leitura larga vai ao banco UMA vez no turno (era 3)", b.leituras_largas)
    b.tabelas["messages"].append(msg("l1", "assistant", datetime.now(timezone.utc),
                                     "deixa comigo, já estou vendo", "espelho"))
    c3, motivo = rodar(F.a_ia_deve_calar(b, company_id=X, conversa=linha,
                                         por_mensagem_nova=True))
    certo(c3 is True and F.foi_a_janela(motivo),
          "🔴 CONTROLE: a atendente fala NO MEIO do turno → a checagem da saída CALA o agente "
          "(a leitura curta é sempre fresca)", motivo)
    b2 = _longa("l2")
    rodar(F.a_ia_deve_calar(b2, company_id=X, conversa=dict(b2.tabelas["conversations"][0]),
                            por_mensagem_nova=True))
    certo(b2.leituras_largas == 1,
          "🔴 CONTROLE: outra conversa (outro banco) lê o SEU banco — a memória não se mistura")

    # ------------------------------------------------------------------ K3
    print("\n" + "=" * 74 + "\n  K3 — o resumo das 19h conta cada silêncio na sua classe\n" + "=" * 74)
    from app.services.os_modelos_do_grupo import contagens_do_dia, modelo_resumo_do_dia

    agora = datetime(2026, 9, 29, 22, 0, tzinfo=timezone.utc)
    seq = [0]

    def ev(tipo, **carga):
        seq[0] += 1
        return {"id": seq[0], "event_type": tipo, "payload_redacted": carga,
                "created_at": iso(agora - timedelta(hours=2))}

    linhas = [
        ev("grupo.calado", calou_porque=G.MOTIVO_AGENTE_DESLIGADO, calou_classe="agente_desligado"),
        ev("grupo.calado", calou_porque=G.MOTIVO_AGENTE_DESLIGADO, calou_classe="agente_desligado"),
        ev("grupo.calado", calou_porque=G.MOTIVO_SEM_PROVA, calou_classe="sem_prova"),
        ev("grupo.calado", calou_porque="a corretora não tem destino de suporte humano configurado",
           calou_classe="sem_destino"),
        ev("grupo.calado", calou_porque="a atendente falou nesta conversa hoje; …",
           calou_classe="janela"),
        ev("grupo.calado", calou_porque="Uma pessoa assumiu esta conversa", calou_classe="assumida"),
        ev("grupo.calado", calou_porque="repetido"),
        # os ANTIGOS, sem a classe (antes da SPEC-121)
        ev("grupo.calado", calou_porque="a atendente falou nesta conversa há 2 dias; …"),
        ev("grupo.calado", calou_porque="Regina assumiu esta conversa"),
    ]

    class _Q:
        def __init__(self, t):
            self.t, self.faixa = t, None

        def select(self, *_a, **_k):
            return self

        def eq(self, *_a, **_k):
            return self

        def gte(self, *_a, **_k):
            return self

        def lt(self, *_a, **_k):
            return self

        def order(self, *_a, **_k):
            return self

        def range(self, i, f):
            self.faixa = (int(i), int(f))
            return self

        async def execute(self):
            ls = linhas if self.t == "work_events" else []
            if self.faixa:
                ls = ls[self.faixa[0]:self.faixa[1] + 1]
            return types.SimpleNamespace(data=ls)

    c = rodar(contagens_do_dia(types.SimpleNamespace(table=lambda n: _Q(n)), X,
                               agora - timedelta(days=1), agora))
    print("     📊", {k: v for k, v in c.items() if v})
    certo(c["calados_pela_janela"] == 2,
          "🔴 'pela janela' conta SÓ a janela (2: 1 nova + 1 antiga) — 📊 antes eram 6 (todo não-assumido)",
          c)
    certo(c["calados_agente_desligado"] == 2 and c["calados_sem_pedido_do_agente"] == 1
          and c["calados_sem_destino"] == 1,
          "agente desligado 2 · sem pedido do agente 1 · sem destino 1 — cada um na sua linha", c)
    certo(c["ja_com_a_equipe"] == 2,
          "🔴 CONTROLE: 'assumiu' (novo com classe e antigo sem) continua 'já com a equipe'", c)
    linhas_do_resumo = sum(c[k] for k in (
        "ja_com_a_equipe", "calados_pela_janela", "calados_sem_pedido_do_agente",
        "calados_agente_desligado", "calados_sem_destino", "calados_outros"))
    certo(c["calados_total"] == 9 and linhas_do_resumo + c["calados_repetidos"] == 9,
          "a conta FECHA: as linhas + os repetidos = todos os `grupo.calado` do dia (9)", c)
    texto = modelo_resumo_do_dia("29/09", c)
    certo("🔕 2 conversas em que fiquei em silêncio pela janela" in texto
          and "🔌 2 avisos com o agente desligado" in texto
          and "⚠️ 1 aviso não chegou ao grupo" in texto,
          "o resumo que a corretora lê diz o número CERTO de cada razão", texto)


def test_spec121_conserto_grupo():
    _ok, falhas = rodar_tudo()
    assert falhas == 0


if __name__ == "__main__":
    _ok, _falhas = rodar_tudo()
    sys.exit(1 if _falhas else 0)
