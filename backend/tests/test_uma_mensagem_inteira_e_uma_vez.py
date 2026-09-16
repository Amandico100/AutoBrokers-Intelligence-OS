# -*- coding: utf-8 -*-
"""G-C1 · G-C2 · G-C3 · G-C4 — uma mensagem, inteira, e uma vez.

O DEFEITO, MEDIDO
=================
📊 10/09/2026, o grupo da Resulta, 75,7 minutos:

```
17:14:18  Dossiê — acionamento travou     ┐
17:21:34  Dossiê — acionamento travou     ├ 3 dossiês, 21 min, A MESMA conversa
17:35:57  Dossiê — Allianz                ┘  (a sessão reabriu 3 vezes)
17:50:39  WhatsApp de atendimento desconectado   <- foi para o GRUPO
18:09:58  ⏳ ESPERA VENCIDA (aviso 1 de 3)  ┐
18:19:58  ⏳ ESPERA VENCIDA (aviso 2 de 3)  ├ 3 avisos idênticos em 20 minutos
18:29:59  ⏳ ESPERA VENCIDA (aviso 3 de 3)  ┘
```

📊 E o conserto de 18/08 (`bloco_unico`) tinha sido aplicado **em um caminho
só**: dos 11 pontos de envio ao grupo, `bloco_unico` estava em **1**.

O QUE ESTE GUARDA PROVA
=======================
G-C1  o que sai pela porta única sai em UM balão — e a LINHA DE CONTROLE: o
      mesmo texto SEM `bloco_unico` sai em MAIS DE UM. ⛔ A asserção é `> 1`,
      nunca o literal `4`: o 4 veio de 429 caracteres e muda com o conteúdo.
G-C2  um vencimento de espera → 1 mensagem ao grupo; e a conversa AINDA EXPIRA
      ao terceiro aviso interno. 🔴 Quem corta `AVISOS_ATE_EXPIRAR` quebra
      `deve_expirar_a_conversa` e a conversa nunca expira.
G-C3  replay das 3 reaberturas de sessão do 10/09 → 1 dossiê.
      CONTROLE: duas conversas diferentes no mesmo minuto → 2 dossiês.
G-C4  a queda de canal vai ao DONO; sem dono cadastrado vai ao grupo COM a
      frase que explica.

🔴 As mutações estão em `docs/canon/reports/SPEC-EXTRA-001.3-EXECUTION-REPORT.md`
e cada uma deixa uma destas seções vermelha.
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


# ---------------------------------------------------------------------------
# Os dublês. 🔴 O de Redis é REAL no comportamento (`nx`, `ex`): é ele que o
# marcador usa, e um dublê que sempre deixa gravar provaria o oposto do que o
# teste afirma.
# ---------------------------------------------------------------------------
class RedisDeMentira:
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

    async def expire(self, *_a, **_k):
        return True

    async def incr(self, chave):
        self.chaves[chave] = int(self.chaves.get(chave) or 0) + 1
        return self.chaves[chave]


_redis = RedisDeMentira()
_mod_redis = types.ModuleType("app.core.redis")


async def _get_async_redis_client():
    return _redis


_mod_redis.get_async_redis_client = _get_async_redis_client
sys.modules["app.core.redis"] = _mod_redis

ENVIADOS = []
_mod_wa = types.ModuleType("app.services.whatsapp_service")


class _WhatsappDeMentira:
    def send_message(self, destino, texto, integracao, *, bloco_unico=False):
        from app.services.whatsapp.balloons import split_whatsapp_balloons

        if bloco_unico:
            from app.services.whatsapp_service_real import _fatiar_documento

            baloes = _fatiar_documento(texto)
        else:
            baloes = split_whatsapp_balloons(texto) or [texto]
        ENVIADOS.append({"destino": destino, "baloes": baloes,
                         "bloco_unico": bloco_unico, "texto": texto})
        return True


_mod_wa.get_whatsapp_service = lambda: _WhatsappDeMentira()
sys.modules["app.services.whatsapp_service"] = _mod_wa

# O `_fatiar_documento` REAL, carregado por caminho (o módulo verdadeiro puxa o
# provider Z-API). ⛔ Reimplementar o fatiador aqui provaria a cópia, não o motor.
import importlib.util as _il  # noqa: E402

_spec = _il.spec_from_file_location(
    "app.services.whatsapp_service_real",
    os.path.join(_RAIZ, "app", "services", "whatsapp_service.py"))
_real = _il.module_from_spec(_spec)
try:
    _spec.loader.exec_module(_real)
except Exception:  # noqa: BLE001 — só precisamos da função pura do topo
    pass
sys.modules["app.services.whatsapp_service_real"] = _real

_mod_int = types.ModuleType("app.services.integration_service")
_mod_int.get_integration_service = lambda *_a, **_k: types.SimpleNamespace(
    get_whatsapp_integration=lambda _c: {"provider": "z-api", "company_id": "X"})
sys.modules["app.services.integration_service"] = _mod_int

_mod_po = types.ModuleType("app.services.platform_outbound")
CONTADOS = []


async def _record_platform_send(company_id, phone, kind, summary):
    CONTADOS.append({"company_id": company_id, "phone": phone, "kind": kind,
                     "summary": summary})


_mod_po.record_platform_send = _record_platform_send
sys.modules["app.services.platform_outbound"] = _mod_po

from app.services.o_grupo_so_o_que_importa import (  # noqa: E402
    TIPO_ESPERA_VENCIDA, TIPO_PEDIDO_DE_AJUDA, TIPO_SINISTRO, enviar_ao_grupo,
    kind_do_grupo,
)

EMPRESA = "11111111-1111-1111-1111-111111111111"
CONVERSA = "aaaaaaaa-0000-0000-0000-000000000001"
OUTRA = "bbbbbbbb-0000-0000-0000-000000000002"
DESTINO = "120363000000000000@g.us"


class BancoQuePassa:
    """Conversa SEM humano e SEM dono: a guarda deixa passar, e é o que estes
    guardas querem medir — eles são sobre REPETIÇÃO e FORMA, não sobre a guarda."""

    def __init__(self):
        self.escritas = []

    def table(self, nome):
        return _Q(self, nome)


class _Q:
    def __init__(self, banco, tabela):
        self.banco, self.tabela, self.f = banco, tabela, {}

    def select(self, *_a, **_k):
        return self

    def eq(self, c, v):
        self.f[c] = v
        return self

    def in_(self, *_a, **_k):
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def insert(self, linha):
        self.banco.escritas.append((self.tabela, linha))
        return self

    def execute(self):
        if self.tabela == "conversations":
            return types.SimpleNamespace(data=[{
                "id": self.f.get("id"), "company_id": self.f.get("company_id"),
                "user_phone": "5547988880001", "claimed_by": None,
                "claimed_by_name": None, "claimed_at": None}])
        if self.tabela == "messages":
            return types.SimpleNamespace(data=[
                {"role": "user", "content": "socorro",
                 "created_at": "2026-09-16T10:00:00+00:00", "payload": {}}])
        return types.SimpleNamespace(data=[])


# O dossiê de 429 caracteres, o MESMO que a §7.1 mediu.
DOSSIE = (
    "🔔 *ATENDIMENTO PRECISA DE VOCÊ*\n"
    "────────────────────\n"
    "*Etapa:* acionamento de assistência — na URA da Allianz\n"
    "\n"
    "*O que aconteceu:* o menu pediu para escolher entre três opções e eu não\n"
    "consegui responder do jeito que ele aceita. Tentei duas vezes.\n"
    "\n"
    "*Resumo:* O segurado tem um vazamento embaixo da pia da cozinha, começou\n"
    "hoje de manhã e ele já fechou o registro. Confirmei a apólice residencial\n"
    "vigente, peguei o endereço e ele prefere o período da tarde.\n"
    "\n"
    "*WhatsApp do segurado:* https://wa.me/5547988880001\n")

print("=" * 70)
print("  G-C1 — UM balão, pelo caminho REAL de envio")
print("=" * 70)

print("     📊 o dossiê deste teste tem %d caracteres" % len(DOSSIE))
ENVIADOS.clear()
_redis.chaves.clear()

for i, tipo in enumerate((TIPO_PEDIDO_DE_AJUDA, TIPO_SINISTRO, "vigia")):
    saida = rodar(enviar_ao_grupo(
        BancoQuePassa(), company_id=EMPRESA, tipo=tipo, texto=DOSSIE,
        conversation_id="conv-%d" % i, destino=DESTINO, dedup=False,
        resumo="teste"))
    certo(saida["enviado"] is True, "o caminho `%s` entregou" % tipo)

certo(len(ENVIADOS) == 3, "três caminhos, três envios")
certo(all(e["bloco_unico"] for e in ENVIADOS),
      "🔴 os TRÊS passam `bloco_unico=True` — não um só, como em 18/08")
certo(all(len(e["baloes"]) == 1 for e in ENVIADOS),
      "e os três chegam em 1 balão: %s" % [len(e["baloes"]) for e in ENVIADOS])

# 🔴 A LINHA DE CONTROLE: o mesmo texto SEM a flag chega picotado.
from app.services.whatsapp.balloons import split_whatsapp_balloons  # noqa: E402

sem_flag = split_whatsapp_balloons(DOSSIE) or [DOSSIE]
certo(len(sem_flag) > 1,
      "🔴 CONTROLE: o MESMO texto sem `bloco_unico` sai em %d balões (⛔ a "
      "asserção é `> 1`, nunca o literal 4)" % len(sem_flag))

print()
print("=" * 70)
print("  G-C2 — espera vencida: 1 aviso ao grupo, e a conversa AINDA expira")
print("=" * 70)

from app.services.o_fim_do_atendimento import (  # noqa: E402
    AVISOS_ATE_EXPIRAR, deve_expirar_a_conversa,
)

certo(AVISOS_ATE_EXPIRAR == 3,
      "⛔ `AVISOS_ATE_EXPIRAR` CONTINUA 3 — o ciclo interno de expiração não muda")
certo(deve_expirar_a_conversa({"avisos": 3, "status": "vencido"}) is True,
      "🔴 e a conversa AINDA EXPIRA ao 3º aviso interno (o motor, não a leitura)")
certo(deve_expirar_a_conversa({"avisos": 1, "status": "vencido"}) is False,
      "CONTROLE: ao 1º aviso ela NÃO expira")

from app.tasks.handoff_watchdog import EVENTO_ESPERA_REPETIDA  # noqa: E402

certo(EVENTO_ESPERA_REPETIDA == "espera.vencida.repetida",
      "e os avisos 2 e 3 têm onde ficar registrados: `%s`" % EVENTO_ESPERA_REPETIDA)

ENVIADOS.clear()
_redis.chaves.clear()
banco = BancoQuePassa()
for _ in range(3):
    rodar(enviar_ao_grupo(banco, company_id=EMPRESA, tipo=TIPO_ESPERA_VENCIDA,
                          texto="⏳ ESPERA VENCIDA", conversation_id=CONVERSA,
                          destino=DESTINO, janela_s=3600, resumo="espera"))
certo(len(ENVIADOS) == 1,
      "🔴 três passadas do vigia sobre a MESMA espera → %d mensagem ao grupo"
      % len(ENVIADOS))

print()
print("=" * 70)
print("  G-C3 — as 3 reaberturas de sessão do 10/09 → 1 dossiê")
print("=" * 70)

ENVIADOS.clear()
_redis.chaves.clear()
banco = BancoQuePassa()
# As três sessões do 10/09: `case_id` diferente, MESMA conversa.
for sessao in ("case-17-14", "case-17-21", "case-17-35"):
    rodar(enviar_ao_grupo(banco, company_id=EMPRESA, tipo=TIPO_PEDIDO_DE_AJUDA,
                          texto=DOSSIE, conversation_id=CONVERSA,
                          destino=DESTINO, resumo=sessao))
certo(len(ENVIADOS) == 1,
      "🔴 3 sessões, 1 conversa → %d dossiê (a chave é a CONVERSA, não a sessão)"
      % len(ENVIADOS))

# CONTROLE: duas conversas diferentes no mesmo minuto → 2 dossiês.
ENVIADOS.clear()
_redis.chaves.clear()
for conversa in (CONVERSA, OUTRA):
    rodar(enviar_ao_grupo(BancoQuePassa(), company_id=EMPRESA,
                          tipo=TIPO_PEDIDO_DE_AJUDA, texto=DOSSIE,
                          conversation_id=conversa, destino=DESTINO, resumo="x"))
certo(len(ENVIADOS) == 2,
      "🔴 CONTROLE: duas conversas diferentes no mesmo minuto → 2 dossiês")

# E o TIPO faz parte da chave: um sinistro não é calado por um pedido de ajuda.
ENVIADOS.clear()
_redis.chaves.clear()
for tipo in (TIPO_PEDIDO_DE_AJUDA, TIPO_SINISTRO):
    rodar(enviar_ao_grupo(BancoQuePassa(), company_id=EMPRESA, tipo=tipo,
                          texto=DOSSIE, conversation_id=CONVERSA,
                          destino=DESTINO, resumo="x"))
certo(len(ENVIADOS) == 2,
      "🔴 o TIPO entra na chave: um sinistro NÃO é calado pelo pedido de ajuda")

# E duas corretoras com a MESMA conversa-molde não se calam (§7).
ENVIADOS.clear()
_redis.chaves.clear()
for empresa in (EMPRESA, "22222222-2222-2222-2222-222222222222"):
    rodar(enviar_ao_grupo(BancoQuePassa(), company_id=empresa,
                          tipo=TIPO_PEDIDO_DE_AJUDA, texto=DOSSIE,
                          conversation_id=CONVERSA, destino=DESTINO, resumo="x"))
certo(len(ENVIADOS) == 2,
      "🔴 §7: a corretora entra na chave — X não cala Y")

print()
print("=" * 70)
print("  G-C4 — a queda de canal vai ao DONO, não ao grupo")
print("=" * 70)

_alertas = _il.spec_from_file_location(
    "_alerts_do_canal", os.path.join(_RAIZ, "app", "services", "whatsapp", "alerts.py"))
_al = _il.module_from_spec(_alertas)
_alertas.loader.exec_module(_al)

DONO = "5547977770001"
_al._telefone_do_dono = lambda _c: DONO
integracao = {"company_id": EMPRESA, "identifier": "5547966660001",
              "alert_target": {}}
certo(_al._alert_destination(integracao) == DONO,
      "🔴 com dono cadastrado, o aviso vai para ELE — não para o grupo")
certo(_al.destino_e_o_grupo(integracao, DONO) is False,
      "e o aviso ao dono NÃO leva a frase de explicação")

_al._telefone_do_dono = lambda _c: ""
_mod_dr = types.ModuleType("app.services.dispatch_router")


async def _support_contact(_c):
    return DESTINO


_mod_dr._support_contact = _support_contact
sys.modules["app.services.dispatch_router"] = _mod_dr
certo(_al._alert_destination(integracao) == DESTINO,
      "sem dono cadastrado, o último degrau CONTINUA sendo o grupo — um aviso "
      "de canal caído que não chega a ninguém é pior")
certo(_al.destino_e_o_grupo(integracao, DESTINO) is True,
      "🔴 e aí a mensagem DIZ POR QUÊ (é o que impede o degrau 3 de virar permanente)")

explicito = {"company_id": EMPRESA, "identifier": "x",
             "alert_target": {"number": "5547955550001"}}
certo(_al._alert_destination(explicito) == "5547955550001",
      "CONTROLE: o destino explícito do `alert_target` continua vencendo os dois")
certo(_al.destino_e_o_grupo(explicito, "5547955550001") is False,
      "CONTROLE: destino explícito não leva a frase")

print()
print("=" * 70)
print("  %d assercoes verdes · %d vermelhas" % (OK, FAIL))
print("=" * 70)
sys.exit(1 if FAIL else 0)
