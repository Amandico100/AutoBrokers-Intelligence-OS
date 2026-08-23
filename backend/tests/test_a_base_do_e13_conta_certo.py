# -*- coding: utf-8 -*-
"""\U0001f534 A LINHA DE BASE DO E13 CONSEGUE BAIXAR — SPEC-084.1 FASE 1.

> ## Um guarda que nao tem como falhar nao guarda nada. (CLAUDE.md \u00a79.3)

A base do E13 conta telas em que o corredor esta CALADO sobre uma tela que
PEDE algo. Se o contador estivesse preso -- lendo um cache, olhando o passo
errado -- ele imprimiria 78 para sempre e ninguem notaria.

\u26a0\ufe0f **E este teste ja falhou uma vez, pelo defeito do proprio teste.** A 1a
versao recarregava `regua_motor` mas NAO `app.services.corridor_playbooks`,
que e onde os playbooks moram. O modulo em cache devolvia a arvore antiga:
`78 -> 78`, e a conclusao teria sido *"o contador esta preso"* sobre uma
ferramenta que funciona.
"""
from __future__ import annotations

import hashlib
import importlib
import io
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
sys.path.insert(0, RAIZ)

import base_do_e13 as E   # noqa: E402

P = os.path.join(RAIZ, "app", "services", "corridor_playbooks.py")
OK = FAIL = 0


def certo(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


print("=" * 74)
print("[1] A LINHA DE BASE, no estado de hoje")
print("=" * 74)

base = E.levantar()
antes = sum(1 for e in base.values() if not e["just"])
certo(len(base) > 0, "\U0001f4ca a base do E13 encontra telas", f"{len(base)} distintas")
certo(antes > 0, "\U0001f4ca e ha telas SEM `noop_justificado` (senao o teste e vacuo)",
      f"{antes} sem justificativa")

# \U0001f534 Tela sem onda e entrada invalida -- a SPEC \u00a73.3 nomeia isso.
sem_onda = []
for e in base.values():
    ondas = {E.onda_da_rota(type("R", (), {
        "seguradora": s, "ramo": ra, "servico": sv})())
        for s, ra, sv in e["rotas"]}
    if not ondas:
        sem_onda.append(e)
certo(not sem_onda,
      "\U0001f534 NENHUMA tela sem onda que a pague — tela sem onda e entrada invalida",
      f"{len(sem_onda)} orfas")

print()
print("=" * 74)
print("[2] \U0001f534 O CONTROLE: justificar um passo BAIXA o contador")
print("=" * 74)

orig = io.open(P, "rb").read()
h0 = hashlib.sha256(orig).hexdigest()
# ⚠️ 🔴 O ALVO TEM DE SER UMA TELA DE **UM PASSO SO** -- 23/08/2026.
#
#    `just` so vira True quando TODOS os passos daquela tela tem
#    `noop_justificado`. A versao anterior pegava a tela de maior corpus, e ela
#    casa DOIS passos (`abertura` e `aguarde_fila`): injetar a justificativa em
#    um deles nao mudava o veredito daquela tela. O controle so passava por
#    efeito colateral -- havia OUTRA tela que casava `abertura` sozinha, e era
#    ela que baixava o contador.
#
# 🔴 Quando essa outra tela deixou de casar `abertura` (a alternativa que a
#    engolia saiu, na ONDA F), o controle perdeu a alavanca e ficou vermelho --
#    corretamente. Um controle que depende de um efeito colateral nao prova o
#    que diz provar.
#
# Agora ele escolhe uma tela de UM passo so, que e o caso em que a injecao
# TEM de mudar o veredito. E se nao houver nenhuma, ele diz isso em vez de
# passar calado.
_de_um_passo = [kv for kv in base.items() if len(kv[1]["passos"]) == 1
                and not kv[1]["just"]]
certo(bool(_de_um_passo),
      "🔴 CONTROLE: ha tela de UM passo so para servir de alavanca",
      f"{len(base)} telas, nenhuma com um passo so e sem justificativa")
alvo = sorted(_de_um_passo, key=lambda kv: -len(kv[1]["corpus"]))[0]
passo = sorted(alvo[1]["passos"])[0]
token = '{"step": "%s",' % passo
certo(token in orig.decode("utf-8"),
      f"o passo alvo `{passo}` existe no corredor")

depois = None
try:
    io.open(P, "w", encoding="utf-8").write(
        orig.decode("utf-8").replace(
            token, token + ' "noop_justificado": "CONTROLE",'))
    # \U0001f534 A LINHA QUE O TESTE ERROU NA 1a VERSAO. Sem recarregar o modulo
    #    dos playbooks, tudo abaixo le a arvore ANTIGA.
    for m in ("app.services.corridor_playbooks", "regua_motor",
              "conferir_respostas", "base_do_e13"):
        if m in sys.modules:
            importlib.reload(sys.modules[m])
    depois = sum(1 for e in sys.modules["base_do_e13"].levantar().values()
                 if not e["just"])
finally:
    io.open(P, "wb").write(orig)

certo(depois is not None and depois < antes,
      "\U0001f534 CONTROLE: o contador do E13 BAIXA quando um passo e justificado",
      f"{antes} -> {depois}")
certo(hashlib.sha256(io.open(P, "rb").read()).hexdigest() == h0,
      "\U0001f534 o corredor foi RESTAURADO byte a byte (conferido por hash)")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
