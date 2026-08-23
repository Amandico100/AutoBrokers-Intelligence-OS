# -*- coding: utf-8 -*-
"""🔴 C8 — HANDOFF É UM DESFECHO, E A RÉGUA O CONTAVA COMO BURACO.

> ## A régua punia o handoff correto.

O réplay perguntava só `match_ura_step`. Uma tela que o corredor manda para
humano **de propósito** não casa passo nenhum — e caía em `ORFA_FUNCIONAL`,
que a própria rubrica chama de *"o defeito"*.

📊 Medido em 22/08/2026: **28 telas em 6 rotas** já disparavam
`detect_handoff_trigger` e eram contadas como falha.

🔴 **O incentivo era invertido:** um executor que otimizasse pela régua
apagaria os gatilhos e ganharia ponto — e o corredor passaria a conduzir, em
silêncio, fluxos que exigem uma pessoa (cancelar serviço, alterar agendamento,
sinistro). É o mesmo formato do P-084-30, onde escopar certo derrubava a nota.
"""

from __future__ import annotations

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

import regua_motor as M   # noqa: E402
import replay as RP       # noqa: E402

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
print("[1] A CLASSE EXISTE E TEM POPULAÇÃO")
print("=" * 74)

certo(hasattr(RP, "HANDOFF"), "🔴 o réplay conhece a classe HANDOFF")

achou = {}
for r in M.rotas():
    if not M.get_playbook(r.ref):
        continue
    rp = RP.replay(r)
    if rp.handoffs:
        achou[f"{r.seguradora}/{r.ramo}/{r.servico}"] = (
            rp.handoffs, len(rp.orfas_funcionais))

certo(len(achou) >= 5,
      "📊 e há rotas cujo corredor manda telas REAIS para humano",
      f"{len(achou)} rotas: {sorted(achou)[:4]}")

# 🔴 CONTROLE DE VACUIDADE: se NENHUMA tela do corpus disparasse gatilho, tudo
#    acima passaria por não haver o que classificar.
total = sum(h for h, _ in achou.values())
certo(total >= 10, "📊 e são muitas telas, não uma coincidência",
      f"{total} telas de handoff")

print()
print("=" * 74)
print("[2] 🔴 HANDOFF SAI DO DENOMINADOR — não entra no numerador")
print("=" * 74)
print("     parar não é responder deterministicamente; contá-lo como acerto")
print("     inflaria o determinismo de quem só sabe desistir")

alvo = [r for r in M.rotas()
        if f"{r.seguradora}/{r.ramo}/{r.servico}" in achou][0]
rp = RP.replay(alvo)
certo(rp.pedem_algo == rp.respondidas + len(rp.orfas_funcionais),
      "🔴 `pedem_algo` = respondidas + órfãs — o handoff não está em nenhum",
      f"pedem_algo={rp.pedem_algo} resp={rp.respondidas} "
      f"orfas={len(rp.orfas_funcionais)} handoff={rp.handoffs}")
certo(rp.handoffs > 0 and rp.pedem_algo < rp.respondidas + len(
          rp.orfas_funcionais) + rp.handoffs,
      "🔴 e o denominador é MENOR do que seria se o handoff entrasse nele")

print()
print("=" * 74)
print("[3] 🔴 A ORDEM É A DO MOTOR: passo primeiro, gatilho depois")
print("=" * 74)
print("     inverter mediria outro corredor — em `insurer_dispatch_service`")
print("     o gatilho só é lido quando NENHUM passo casou")

FONTE = open(os.path.join(RAIZ, "scripts", "replay.py"), encoding="utf-8").read()
i_passo = FONTE.find("passo = M.match_ura_step(pb, texto, subservice=rota.servico)")
i_hand = FONTE.find("elif M.detect_handoff_trigger(pb, texto):")
certo(0 < i_passo < i_hand,
      "🔴 `match_ura_step` vem ANTES de `detect_handoff_trigger`",
      f"passo em {i_passo}, gatilho em {i_hand}")

# 🔴 CONTROLE POSITIVO: uma tela que casa passo E dispara gatilho tem de sair
#    RESPONDIDA. Sem esta prova, a ordem no arquivo seria só uma coincidência
#    de layout.
achou_conflito = None
for r in M.rotas():
    pb = M.get_playbook(r.ref)
    if not pb:
        continue
    for t in RP.replay(r).telas:
        if t.classe == RP.RESPONDIDA and M.detect_handoff_trigger(pb, t.texto):
            achou_conflito = (r, t)
            break
    if achou_conflito:
        break
if achou_conflito:
    r, t = achou_conflito
    certo(t.classe == RP.RESPONDIDA,
          "🔴 CONTROLE: tela que casa passo E dispara gatilho sai RESPONDIDA — "
          "o passo vence, como no motor",
          f"{r.seguradora}/{r.servico}: {' '.join(t.texto.split())[:56]}")
else:
    certo(True, "⚠️ nenhuma tela casa passo E gatilho ao mesmo tempo hoje — "
                "a ordem fica provada só pela posição no arquivo")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
