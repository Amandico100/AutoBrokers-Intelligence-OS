# -*- coding: utf-8 -*-
"""O vigia de conversa parada NAO cobra mais o grupo — e a licao migrou.

A HISTORIA, EM TRES DATAS
=========================
📊 21/08/2026 — o Founder recebeu DEZENAS de "ATENDIMENTO PRECISA DE VOCE" sobre
conversas em que ninguem esperava nada ("Ta bom, obrigado"). Nasceram duas regras:
so cobrar se a ULTIMA palavra foi do cliente, e no maximo 4 lembretes.

📊 21/09/2026 — os grupos de suporte, desativados desde 10/09, voltaram. O vigia
mandou **29 lembretes no mesmo dia** (`work_events.handoff.realertado`: 14 numa
corretora, 15 na outra), sobre conversas paradas ha **243 e 244 horas**. Um deles
dizia "AINDA SEM ATENDIMENTO" e "Atendente pelo celular ja assumiu" NA MESMA
MENSAGEM.

🔴 28/09/2026 — a regra do Founder (SPEC-120, D16 e D17):
   *"Nao deve ficar enviando dossies antigos. E um aviso so na hora do
    atendimento e so se o atendimento for feito pelo agente. Agente nao se mete
    em atendimento de humano e nao envia msg no suporte humano quando o humano
    estiver atendendo."*

O QUE ESTE ARQUIVO GUARDA AGORA
===============================
1. o vigia NAO manda nada ao grupo — nem sobre quem espera, nem sobre quem nao espera;
2. e o ZERO significa algo: o vigia CHEGOU a cada conversa e MEDIU a espera
   (o SLI `HANDOFF_ESPERA` e registrado uma vez por conversa, por varredura).
   Sem esta linha de controle, "zero avisos" passaria tambem com o vigia
   quebrado no inicio — e seria carimbo, nao guarda (CLAUDE.md §9.3).

⚠️ O CONTRA-ARGUMENTO, QUE CONTINUA VERDADEIRO E FICA ESCRITO
=============================================================
A regra antiga dizia: *"o defeito grave deste vigia sempre foi o silencio —
📊 uma conversa ficou 730 horas sem ninguem olhar"*. Isso nao deixou de ser
verdade. O Founder decidiu aceita-lo porque o risco tem outro dono agora:
  · o aviso da HORA (quando o agente pede a pessoa) continua saindo, uma vez;
  · a conversa parada continua na FILA do painel, com a espera medida.
Se um dia o grupo ficar fora do ar no momento do aviso, aquela conversa NAO sera
lembrada no grupo — ela estara so na Fila. E o preco declarado da regra.
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
#: cada vez que o vigia MEDE uma conversa parada (o SLI). E a prova de que ele
#: chegou ate' ela — sem isto, "zero avisos" nao distinguiria regra de quebra.
MEDIDAS: list = []


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

    def is_(self, c, v):
        """PostgREST `col=is.null` — SPEC-085 BLOCO F.2.

        🔴 O dublê aprendeu isto porque o Vigia passou a FILTRAR por
        `claimed_by is null`. `HUMAN_REQUESTED` significa duas coisas opostas
        neste produto — *"a IA pediu um humano"* e *"um humano JA assumiu"* — e
        `claimed_by` e' a coluna que as separa. O select nem a pedia.

        ⚠️ Sem conhecer o filtro, o dublê levantava `AttributeError`, o
        `try/except` do Vigia engolia, e a varredura devolvia ZERO conversas:
        📊 o guarda do teto media "no maximo QUATRO avisos" e recebia **0** —
        vermelho por ignorancia do dublê, nao por defeito do produto.
        """
        self.f["__is"] = (c, str(v))
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
            linhas = list(self.b.conversas)
            # 🔴 O filtro `is.null` aplicado de VERDADE: uma conversa ja'
            # assumida (com `claimed_by`) sai da varredura, que e' o conserto
            # do BLOCO F.2. Um dublê que ignorasse isso deixaria o teste
            # aprovar um Vigia que continua cobrando quem ja' tem dono.
            alvo = self.f.get("__is")
            if alvo:
                coluna, valor = alvo
                if valor == "null":
                    linhas = [c for c in linhas if c.get(coluna) is None]
                else:
                    linhas = [c for c in linhas if c.get(coluna) is not None]
            r.data = linhas
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
                                registrar=lambda *a, **k: MEDIDAS.append(k.get("company_id")))
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
print("  1. O VIGIA NAO COBRA O GRUPO — nem quem espera (SPEC-120 D16)")
print("=" * 74)

# Duas conversas paradas ha' 48h: numa a ultima palavra e' do CLIENTE (era a que
# a regra de 21/08 AVISAVA), na outra e' nossa.
convs = [conversa("c-espera"), conversa("c-nao-espera")]
msgs = [
    {"conversation_id": "c-espera", "role": "user",
     "created_at": "2026-08-19T10:00:00Z"},
    {"conversation_id": "c-nao-espera", "role": "assistant",
     "created_at": "2026-08-19T10:00:00Z"},
]
avisos = []
MEDIDAS.clear()
rodar(BancoFake(convs, msgs), RedisFake(), avisos)

certo(avisos == [],
      "🔴 NENHUM aviso ao grupo — nem para a conversa em que o CLIENTE falou por ultimo",
      f"avisos: {avisos}")
certo(len(MEDIDAS) == 1,
      "🔴 CONTROLE: e o vigia CHEGOU a ela — mediu a espera da que tem alguem esperando "
      "(a que terminou com a nossa palavra ja' sai antes, pelo filtro de 21/08)",
      f"medidas: {len(MEDIDAS)}")

# 🔴 CONTROLE DO CONTROLE: o espiao do grupo FUNCIONA. Chamado de verdade, ele
#    registra. Sem esta linha, "avisos == []" passaria com o espiao quebrado.
import importlib  # noqa: E402
hh = importlib.import_module("app.agents.tools.human_handoff")
asyncio.run(hh.HumanHandoffTool._avisar_suporte(None, "emp-1", {"id": "c-prova"}, "prova"))
certo(("c-prova", "prova") in avisos,
      "CONTROLE: o espiao do grupo registra quando e' chamado — logo o ZERO acima e' do vigia")
avisos.clear()

print()
print("=" * 74)
print("  2. LEITURA FALHOU? CONTINUA SEM AVISO — e continua MEDINDO")
print("=" * 74)

avisos2 = []
MEDIDAS.clear()
rodar(BancoFake(convs, msgs, estoura=True), RedisFake(), avisos2)
certo(avisos2 == [],
      "🔴 a leitura das mensagens falhou -> AINDA nenhum aviso (antes: avisava TODAS)",
      f"avisos: {len(avisos2)}")
certo(len(MEDIDAS) == 2,
      "CONTROLE: sem ler quem espera, trata as DUAS como pendentes e mede as duas "
      "— logo o filtro de 21/08 continua existindo, so' nao vira mensagem",
      f"medidas: {len(MEDIDAS)}")

print()
print("=" * 74)
print("  3. CONVERSA SEM MENSAGEM NENHUMA: MEDIDA, NAO ANUNCIADA")
print("=" * 74)

avisos3 = []
MEDIDAS.clear()
rodar(BancoFake([conversa("c-sem-msg")], []), RedisFake(), avisos3)
certo(avisos3 == [], "🔴 nenhum aviso", f"avisos: {avisos3}")
certo(len(MEDIDAS) == 1, "CONTROLE: e ela nao some — a espera dela e' medida")

print()
print("=" * 74)
print("  4. SETE VARREDURAS, ZERO MENSAGENS (antes: quatro)")
print("=" * 74)

redis4 = RedisFake()
banco4 = BancoFake([conversa("c-teto", horas=244)],
                   [{"conversation_id": "c-teto", "role": "user",
                     "created_at": "2026-08-19T10:00:00Z"}])
avisos4 = []
MEDIDAS.clear()
for volta in range(7):
    redis4.chaves.clear()          # simula as 6h passando entre as varreduras
    rodar(banco4, redis4, avisos4)

certo(avisos4 == [],
      f"🔴 uma conversa parada ha' 244h, varrida 7 vezes: ZERO mensagens ({len(avisos4)})",
      "e' o caso exato do print do Founder de 21/09")
certo(len(MEDIDAS) == 7,
      "CONTROLE: e as sete varreduras chegaram ate' ela (7 medidas)",
      f"medidas: {len(MEDIDAS)}")

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
