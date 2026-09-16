# -*- coding: utf-8 -*-
"""G-E1 — todo envio ao grupo fica contado, e NENHUM envenena o governador.

O DEFEITO, MEDIDO
=================
📊 16/09/2026, `platform_sends` na base inteira: **19 linhas**
(`billing` 18 · `acionamento_protocolo` 1), a mais recente de 11/09.
**Zero de grupo.** A pergunta *"quantas mensagens o grupo recebeu ontem?"* não
tinha resposta em lugar nenhum.

🔴 **E o achado que podia CALAR O ATENDIMENTO.** `platform_outbound._historico_sync`
fazia **TRÊS** leituras de `platform_sends` sem filtro de `kind`:

```
:606-610  recentes   → a cota da HORA e do DIA
:611-613  primeiro   → dias_de_uso  ┐
:614-616  total_res  → total        ┴→ maturidade_do_canal → teto_do_dia
```

1. cada mensagem interna consome a cota do SEGURADO → num dia movimentado o
   produto para de falar com clientes, e o motivo seria invisível;
2. um canal que NUNCA falou com um segurado "amadurece" com mensagens internas
   e SOBE o teto diário — o contrário exato do que `maturidade_do_canal` prova.

⛔ E o conserto NÃO é o prefixo `grupo_`: `billing_nota` (a nota interna à
atendente, EXTRA-001.6) não começa com `grupo_` e passaria igual. É uma
ALLOWLIST, e o padrão é NÃO CONTAR.

O QUE ESTE GUARDA PROVA
=======================
1. toda saída pela porta única grava UMA linha `grupo_*` — e o número de linhas
   é o número de mensagens que saíram (não de intenções);
2. depois de N linhas `grupo_*` **e** N `billing_nota`, as QUATRO grandezas
   ficam iguais: cota da hora, cota do dia, `dias_de_uso` e `maturidade_do_canal`;
3. 🔴 LINHA DE CONTROLE: N linhas `billing` **mexem** nas quatro — sem ela o
   teste estaria provando que o governador não funciona;
4. todo `kind` que o produto escreve está numa das duas listas — um `kind` novo
   que fale com o segurado e fique de fora deixa este guarda vermelho.
"""
from __future__ import annotations

import asyncio
import os
import re
import sys
import types
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _pkg in ("app", "app.agents", "app.agents.tools", "app.core", "app.services",
             "app.services.whatsapp", "app.tasks"):
    if _pkg not in sys.modules:
        _m = types.ModuleType(_pkg)
        _m.__path__ = [os.path.join(_RAIZ, *_pkg.split("."))]
        sys.modules[_pkg] = _m

OK = FAIL = 0


def certo(condicao, frase):
    global OK, FAIL
    if condicao:
        OK += 1
        print("  ✅", frase)
    else:
        FAIL += 1
        print("  ❌", frase)


def rodar(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


EMPRESA = "11111111-1111-1111-1111-111111111111"

# ---------------------------------------------------------------------------
# O banco de mentira de `platform_sends` — 🔴 ele HONRA o `.in_("kind", …)`.
# Um dublê que ignorasse o filtro provaria o contrário do que o teste afirma.
# ---------------------------------------------------------------------------
LINHAS = []


class _Res:
    def __init__(self, data, count=None):
        self.data, self.count = data, count


class _Q:
    def __init__(self, tabela):
        self.tabela, self.f, self.kinds, self.desde = tabela, {}, None, None
        self.contar = False

    def select(self, *_a, **k):
        self.contar = (k.get("count") == "exact")
        return self

    def eq(self, c, v):
        self.f[c] = v
        return self

    def in_(self, coluna, valores):
        if coluna == "kind":
            self.kinds = set(valores)
        return self

    def gte(self, _c, v):
        self.desde = v
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def insert(self, linha):
        LINHAS.append(linha)
        return self

    def execute(self):
        if self.tabela != "platform_sends":
            return _Res([])
        saida = [l for l in LINHAS
                 if str(l.get("company_id")) == str(self.f.get("company_id", l.get("company_id")))]
        if self.kinds is not None:
            saida = [l for l in saida if l.get("kind") in self.kinds]
        if self.desde:
            saida = [l for l in saida if str(l.get("sent_at")) >= str(self.desde)]
        saida = sorted(saida, key=lambda l: str(l.get("sent_at")))
        return _Res(saida, count=len(saida))


class _Cliente:
    def table(self, nome):
        return _Q(nome)


_mod_db = types.ModuleType("app.core.database")
_mod_db.get_supabase_client = lambda: types.SimpleNamespace(client=_Cliente())
sys.modules["app.core.database"] = _mod_db

_mod_redis = types.ModuleType("app.core.redis")


class _RedisDeMentira:
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


_redis = _RedisDeMentira()


async def _get_redis():
    return _redis


_mod_redis.get_async_redis_client = _get_redis
sys.modules["app.core.redis"] = _mod_redis

from app.services.platform_outbound import (  # noqa: E402
    KINDS_INTERNOS, KINDS_QUE_CONTAM_NA_COTA_DO_SEGURADO, conta_na_cota_do_segurado,
    historico_de_envios, maturidade_do_canal, record_platform_send, teto_do_dia,
)

AGORA = datetime.now(timezone.utc)


def _linha(kind, dias_atras=0):
    return {"company_id": EMPRESA, "phone": "120363@g.us", "kind": kind,
            "summary": "x",
            "sent_at": (AGORA - timedelta(days=dias_atras, minutes=1)).isoformat()}


def _foto():
    h = rodar(historico_de_envios(EMPRESA, AGORA))
    m = maturidade_do_canal(h["dias_de_uso"], h["total"])
    return {"na_hora": h["na_hora"], "no_dia": h["no_dia"],
            "dias_de_uso": h["dias_de_uso"], "maturidade": m,
            "teto_do_dia": teto_do_dia(m)}


print("=" * 70)
print("  G-E1a — as três leituras do governador ignoram o que não conta")
print("=" * 70)

LINHAS.clear()
# O canal nasce com um envio ao segurado há 40 dias e 199 no total: falta UM
# para amadurecer. É a borda onde a maturidade realmente muda.
LINHAS.append(_linha("billing", dias_atras=40))
for _ in range(198):
    LINHAS.append(_linha("billing", dias_atras=5))
antes = _foto()
print("     📊 antes:", antes)
certo(antes["maturidade"] == "novo",
      "o canal começa NOVO (199 envios, falta 1 para os 200)")

# 200 linhas internas: 100 de grupo + 100 `billing_nota`
for i in range(100):
    LINHAS.append(_linha("grupo_pedido_de_ajuda"))
    LINHAS.append(_linha("billing_nota"))
depois = _foto()
print("     📊 depois de 100 `grupo_*` + 100 `billing_nota`:", depois)

certo(depois["na_hora"] == antes["na_hora"],
      "🔴 a cota da HORA não mexeu (%d)" % depois["na_hora"])
certo(depois["no_dia"] == antes["no_dia"],
      "🔴 a cota do DIA não mexeu (%d)" % depois["no_dia"])
certo(depois["dias_de_uso"] == antes["dias_de_uso"],
      "🔴 `dias_de_uso` não mexeu (%d)" % depois["dias_de_uso"])
certo(depois["maturidade"] == antes["maturidade"] == "novo",
      "🔴 `maturidade_do_canal` CONTINUA `novo` — o canal não ganhou reputação "
      "de veterano conversando consigo mesmo")
certo(depois["teto_do_dia"] == antes["teto_do_dia"],
      "e o teto do dia continua %d" % depois["teto_do_dia"])

print()
print("  🔴 A LINHA DE CONTROLE — e é ela que dá direito à conclusão")
LINHAS.append(_linha("billing"))
controle = _foto()
print("     📊 depois de +1 `billing`:", controle)
certo(controle["na_hora"] == antes["na_hora"] + 1,
      "CONTROLE: 1 linha `billing` MEXE na cota da hora (%d → %d)"
      % (antes["na_hora"], controle["na_hora"]))
certo(controle["no_dia"] == antes["no_dia"] + 1,
      "CONTROLE: MEXE na cota do dia")
certo(controle["maturidade"] == "maduro",
      "🔴 CONTROLE: o 200º envio AO SEGURADO amadurece o canal — o governador "
      "funciona, e é por isso que o silêncio acima significa alguma coisa")
certo(controle["teto_do_dia"] > antes["teto_do_dia"],
      "CONTROLE: e o teto do dia sobe (%d → %d)"
      % (antes["teto_do_dia"], controle["teto_do_dia"]))

print()
print("=" * 70)
print("  G-E1b — uma linha por MENSAGEM que saiu")
print("=" * 70)

LINHAS.clear()
rodar(record_platform_send(EMPRESA, "120363@g.us", "grupo_sinistro", "um sinistro"))
certo(len(LINHAS) == 1, "um envio → uma linha")
certo(LINHAS[0]["kind"] == "grupo_sinistro", "com o `kind` do tipo")
certo("@" not in str(LINHAS[0]["phone"]) and LINHAS[0]["phone"].isdigit(),
      "e o `phone` é o destino do GRUPO em dígitos — ⛔ nunca o do segurado")

print()
print("=" * 70)
print("  G-E1c — nenhum `kind` do produto fica fora das DUAS listas")
print("=" * 70)

certo(not (KINDS_QUE_CONTAM_NA_COTA_DO_SEGURADO & KINDS_INTERNOS),
      "as duas listas não se cruzam")
certo(conta_na_cota_do_segurado("billing") is True,
      "`billing` conta — é o texto que a pessoa lê")
certo(conta_na_cota_do_segurado("billing_nota") is False,
      "🔴 `billing_nota` NÃO conta — e ela não começa com `grupo_`, que é "
      "exatamente por que o filtro por prefixo estaria errado")
certo(conta_na_cota_do_segurado("kind_que_ninguem_declarou") is False,
      "🔴 o padrão é NÃO CONTAR: todo `kind` interno futuro nasce seguro")

# A varredura: todo literal passado a `record_platform_send` no produto.
_LITERAL = re.compile(r"record_platform_send\(\s*[^)]*?[\"']([a-z_]+)[\"']", re.S)
achados = set()
for raiz, _d, arquivos in os.walk(os.path.join(_RAIZ, "app")):
    for nome in arquivos:
        if nome.endswith(".py"):
            texto = open(os.path.join(raiz, nome), encoding="utf-8",
                         errors="replace").read()
            achados |= set(_LITERAL.findall(texto))
from app.services.platform_outbound import KIND_DE_CONTAGEM  # noqa: E402

achados |= set(KIND_DE_CONTAGEM.values())
achados |= {"grupo_" + t for t in ("pedido_de_ajuda", "sinistro", "conclusao",
                                   "resumo_diario", "espera_vencida", "vigia",
                                   "queda_de_canal", "cobranca")}
fora = sorted(k for k in achados
              if k not in KINDS_QUE_CONTAM_NA_COTA_DO_SEGURADO
              and k not in KINDS_INTERNOS)
print("     📊 kinds encontrados no produto: %d" % len(achados))
certo(not fora,
      "🔴 nenhum `kind` do produto está fora das duas listas — fora: %s"
      % (fora or "nenhum"))

print()
print("=" * 70)
print("  %d assercoes verdes · %d vermelhas" % (OK, FAIL))
print("=" * 70)
sys.exit(1 if FAIL else 0)
