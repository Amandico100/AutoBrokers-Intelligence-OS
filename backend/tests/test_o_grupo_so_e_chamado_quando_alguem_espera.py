# -*- coding: utf-8 -*-
"""O suporte humano so e cobrado quando ha alguem esperando resposta.

O DEFEITO, MEDIDO
=================
📊 21/08/2026. O Founder relatou DEZENAS de "ATENDIMENTO PRECISA DE VOCE" no
grupo da Resulta, com a frase: *"nao tem coisa pra resolver"*.

Consulta no banco: quatro conversas em `HUMAN_REQUESTED`, paradas ha 43-48h,
terminando assim --

    "Ta bom, obrigado"
    "Olha o site desse video. Vai rolando e o carro vai andando."
    "Vixi... to indo entao"
    "Tem muito passo que ainda nao e feito pelo agente"

Conversas da propria equipe, capturadas pelo observador. Em TODAS a ultima
mensagem era do lado da corretora. **Ninguem aguardava nada.**

E o vigia as cobrava a cada 6 horas, para sempre, sem teto.

AS DUAS REGRAS NOVAS
====================
1. so cobra se a ULTIMA palavra foi do cliente (`role='user'`)
2. no maximo 4 lembretes por conversa -- e o ultimo AVISA que e o ultimo

🔴 As duas falham para o lado de AVISAR, nunca de calar: sem leitura possivel,
avisa todas; sem contador, ignora o teto. O defeito grave deste vigia sempre
foi o silencio (📊 uma conversa ficou 730 horas sem ninguem olhar), e um
conserto contra spam nao pode reintroduzi-lo.
"""
from __future__ import annotations

import asyncio
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _pkg in ("app", "app.agents", "app.agents.tools", "app.core",
             "app.services", "app.tasks"):
    if _pkg not in sys.modules:
        _m = types.ModuleType(_pkg)
        _m.__path__ = [os.path.join(_RAIZ, *_pkg.split("."))]
        sys.modules[_pkg] = _m

OK = 0
FAIL = 0


def certo(condicao, rotulo, detalhe=""):
    global OK, FAIL
    if condicao:
        OK += 1
        print(f"  ok   {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


# ---------------------------------------------------------------- dublês
class RedisFake:
    def __init__(self):
        self.chaves = {}
        self.contadores = {}

    async def set(self, chave, valor, ex=None, nx=False):
        if nx and chave in self.chaves:
            return None
        self.chaves[chave] = valor
        return True

    async def delete(self, chave):
        self.chaves.pop(chave, None)

    async def incr(self, chave):
        self.contadores[chave] = self.contadores.get(chave, 0) + 1
        return self.contadores[chave]

    async def expire(self, chave, seg):
        return True


class RedisMorto:
    async def set(self, *a, **k):
        raise ConnectionError("fora do ar")

    async def delete(self, *a, **k):
        raise ConnectionError("fora do ar")

    async def incr(self, *a, **k):
        raise ConnectionError("fora do ar")

    async def expire(self, *a, **k):
        raise ConnectionError("fora do ar")


def com_redis(fake):
    mod = types.ModuleType("app.core.redis")

    async def _get():
        return fake
    mod.get_async_redis_client = _get
    sys.modules["app.core.redis"] = mod


class Consulta:
    def __init__(self, banco, tabela):
        self.b, self.t = banco, tabela
        self.f = {}

    def select(self, *a):
        return self

    def eq(self, c, v):
        self.f[c] = v
        return self

    def lt(self, c, v):
        return self

    def in_(self, c, vals):
        self.f["__in"] = list(vals)
        return self

    def order(self, *a, **k):
        return self

    def limit(self, n):
        return self

    def execute(self):
        class R:
            pass
        r = R()
        if self.t == "conversations":
            r.data = list(self.b.conversas)
        else:
            if self.b.mensagens_estouram:
                raise RuntimeError("leitura de mensagens falhou")
            alvo = self.f.get("__in") or []
            r.data = [m for m in self.b.mensagens
                      if str(m["conversation_id"]) in [str(x) for x in alvo]]
        return r


class BancoFake:
    def __init__(self, conversas, mensagens, estoura=False):
        self.conversas, self.mensagens = conversas, mensagens
        self.mensagens_estouram = estoura

    def table(self, nome):
        return Consulta(self, nome)


def preparar(banco, redis):
    """Instala os dublês nos módulos que o vigia importa tardiamente."""
    com_redis(redis)
    dbmod = types.ModuleType("app.core.database")
    dbmod.get_supabase_client = lambda: banco
    sys.modules["app.core.database"] = dbmod

    obs = types.ModuleType("app.services.observability")
    sli = types.SimpleNamespace(HANDOFF_ESPERA="x",
                                registrar=lambda *a, **k: None)
    obs.sli = sli
    sys.modules["app.services.observability"] = obs
    sys.modules["app.services.observability.sli"] = sli


def conversa(cid, horas=48):
    from datetime import datetime, timedelta, timezone
    quando = (datetime.now(timezone.utc) - timedelta(hours=horas)).isoformat()
    return {"id": cid, "company_id": "emp-1", "session_id": f"ses-{cid}",
            "user_name": "Alguem", "user_phone": "5548999999999",
            "last_message_at": quando, "human_handoff_reason": "pediu humano"}


def rodar(banco, redis, avisos):
    preparar(banco, redis)
    import importlib
    wd = importlib.import_module("app.tasks.handoff_watchdog")
    hh = importlib.import_module("app.agents.tools.human_handoff")

    async def _falso(self, company_id, conv, motivo):
        avisos.append((str(conv.get("id")), motivo))
        return {"avisado": True, "motivo": ""}
    hh.HumanHandoffTool._avisar_suporte = _falso
    asyncio.run(wd.varrer_handoffs_parados())
    return wd


print()
print("=" * 74)
print("  1. QUEM NAO ESPERA NADA NAO VIRA ALARME")
print("=" * 74)

# Duas conversas paradas: numa a ultima palavra e do CLIENTE, na outra e nossa.
convs = [conversa("c-espera"), conversa("c-nao-espera")]
msgs = [
    {"conversation_id": "c-espera", "role": "user",
     "created_at": "2026-08-19T10:00:00Z"},
    {"conversation_id": "c-nao-espera", "role": "assistant",
     "created_at": "2026-08-19T10:00:00Z"},
]
avisos = []
rodar(BancoFake(convs, msgs), RedisFake(), avisos)
avisadas = {a[0] for a in avisos}

certo("c-espera" in avisadas,
      "🔴 CONTROLE: a conversa em que o CLIENTE falou por ultimo AVISA",
      f"avisadas: {sorted(avisadas)}")
certo("c-nao-espera" not in avisadas,
      "🔴 e a que terminou com a nossa palavra NAO avisa",
      f"avisadas: {sorted(avisadas)}")
certo(len(avisos) == 1, f"exatamente um aviso ({len(avisos)})")

print()
print("=" * 74)
print("  2. NAO CONSEGUIU LER? AVISA. (o defeito grave e o silencio)")
print("=" * 74)

avisos2 = []
rodar(BancoFake(convs, msgs, estoura=True), RedisFake(), avisos2)
certo(len(avisos2) == 2,
      "🔴 leitura de mensagens falhou -> avisa TODAS, como antes",
      f"avisos: {len(avisos2)}")

# CONTROLE: com a leitura funcionando, sao 1 -- entao o 2 acima veio da falha,
# nao de o filtro nunca funcionar.
certo(len(avisos2) > len(avisos),
      "CONTROLE: e sao MAIS que no caso saudavel (2 > 1) — "
      "logo o filtro existe e a falha o desliga de proposito")

print()
print("=" * 74)
print("  3. CONVERSA SEM MENSAGEM NENHUMA CONTINUA ELEGIVEL")
print("=" * 74)

avisos3 = []
rodar(BancoFake([conversa("c-sem-msg")], []), RedisFake(), avisos3)
certo(len(avisos3) == 1,
      "🔴 conversa sem transcricao NAO e silenciada",
      "calar sobre um caso que nunca teve mensagem seria inventar um motivo")

print()
print("=" * 74)
print("  4. O TETO — quatro lembretes, e o ultimo diz que e o ultimo")
print("=" * 74)

redis4 = RedisFake()
banco4 = BancoFake([conversa("c-teto")],
                   [{"conversation_id": "c-teto", "role": "user",
                     "created_at": "2026-08-19T10:00:00Z"}])
avisos4 = []
import importlib  # noqa: E402
for volta in range(7):
    redis4.chaves.clear()          # simula as 6h passando entre as varreduras
    rodar(banco4, redis4, avisos4)

certo(len(avisos4) == 4,
      f"🔴 sete varreduras produzem no maximo QUATRO avisos ({len(avisos4)})",
      "sem teto seriam sete, e a cada 6h para sempre")
certo(avisos4 and "ÚLTIMO lembrete" in avisos4[-1][1],
      "🔴 e o ultimo AVISA que e o ultimo",
      "parar em silencio seria trocar um defeito por outro pior")
certo(avisos4 and "ÚLTIMO lembrete" not in avisos4[0][1],
      "CONTROLE: e o primeiro NAO tem esse aviso "
      "(logo o teste acima mediu o teto, nao um texto fixo)")

print()
print("=" * 74)
print("  5. REDIS MORTO NAO PODE VIRAR MORDACA")
print("=" * 74)

hh = importlib.import_module("app.agents.tools.human_handoff")
com_redis(RedisMorto())
certo(asyncio.run(hh.contar_lembrete("qualquer")) == 0,
      "🔴 contador indisponivel devolve 0 = o teto e ignorado, e avisa",
      "freio quebrado nao pode virar mordaca")
certo(asyncio.run(hh.reivindicar_o_aviso("qualquer", 6)) is False,
      "CONTROLE: e o marcador tambem falha para o lado de avisar")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
