# -*- coding: utf-8 -*-
"""🔴 C16 — O ITEM DAS `notes` DAVA ZERO POR NÃO TER NADA PARA CONFERIR.

📊 23/08/2026, medindo `allianz/auto` na ONDA B. A régua excluía do exame todo
passo que aparecesse em mais de um playbook — a v3 do item, escrita para não
acusar de mentira uma nota certa de passo compartilhado.

O remédio apagava a pergunta em vez de respondê-la:

```
allianz/auto : ~60 passos no corredor  ->  1 sobrevive ao filtro
               e esse 1 não tem número  ->  com_numero = 0  ->  0 de 2
```

🔴 **Vinte e oito rotas levavam zero por não terem nada que pudesse ser
conferido** — o mesmo defeito que o C10 nomeou ("um item que ninguém pode
ganhar não mede nada"), voltando por outra porta.

⚠️ E o incentivo era pior que o zero: para ganhar o ponto, um executor teria de
**duplicar o passo** em cada corredor. A régua pagaria por violar a §5 do
CLAUDE.md.

A resposta já estava escrita uma linha acima e só faltava levá-la até o fim:
*"a note descreve um PASSO, e o passo é do corredor"*. Se o passo vive em N
corredores, o número dele é o dos N.
"""

from __future__ import annotations

import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

import regua_motor as M     # noqa: E402
import replay as RP         # noqa: E402
import rubrica as RB        # noqa: E402

OK = FAIL = 0


def certo(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


def _item(seg, ramo, sv):
    rota = [r for r in M.rotas()
            if (r.seguradora, r.ramo, r.servico) == (seg, ramo, sv)][0]
    for i in RB.eixo_b(rota, RP.replay(rota)):
        if "notes" in i.nome:
            return i
    raise AssertionError("item nao encontrado")


print("=" * 74)
print("[1] O MAPA SABE QUEM CARREGA CADA PASSO")
print("=" * 74)

mapa = RB.corredores_do_passo()
certo(len(mapa) > 100, "📊 o mapa cobre os passos do produto", f"{len(mapa)} passos")

compart = [(k, v) for k, v in mapa.items() if len(v) > 1]
certo(compart, "🔴 há passo que vive em MAIS DE UM corredor — é o caso que "
      "a v3 apagava", f"{len(compart)} passos compartilhados")

# 🔴 CONTROLE: e há passo de um corredor só. Se TODOS fossem compartilhados,
#    o item de cima passaria sem querer dizer nada.
sozinhos = [(k, v) for k, v in mapa.items() if len(v) == 1]
certo(sozinhos, "🔴 CONTROLE: e há passo de UM corredor só — os dois casos "
      "existem", f"{len(sozinhos)} passos exclusivos")

print()
print("=" * 74)
print("[2] 🔴 O ITEM DEIXOU DE SER VAZIO — e é este o conserto")
print("=" * 74)

for seg, ramo, sv in (("allianz", "auto", "guincho"),
                      ("allianz", "auto", "bateria"),
                      ("alfa", "auto", "guincho"),
                      ("yelum", "auto", "pneu")):
    ev = _item(seg, ramo, sv).evidencia
    m = re.search(r"(\d+) de (\d+) notes", ev)
    certo(m and int(m.group(2)) >= 1,
          f"🔴 {seg}/{ramo}/{sv}: há note com número PARA conferir",
          f"com_numero=0 -> o item daria 0 de 2 sem ninguem poder evitar | {ev}")

print()
print("=" * 74)
print("[3] 🔴 E O ITEM AINDA CONSEGUE ACUSAR — senão não guarda nada")
print("=" * 74)

# A rota de referência tem de continuar em 2/2: o conserto não pode ser um
# afrouxamento disfarçado.
ref = _item("allianz", "residencial", "maquina_de_lavar")
certo(ref.pontos == 2, "🔴 CONTROLE: a rota de referência segue em 2/2 — o "
      "conserto não afrouxou nada", ref.evidencia)

# 🔴 E O ITEM TEM DE CONSEGUIR FICAR VERMELHO. Um guarda em que todos passam
#    não separa nada.
#
# ⚠️ A primeira versão desta asserção apontava para `porto/residencial`, que
#    estava vermelha naquele minuto. **Um controle que depende de um defeito
#    continuar aberto não é controle: é refém** — e ele venceria no dia em que
#    a porto fosse consertada. A pergunta certa não é *"alguém está
#    vermelho?"*, é *"ele CONSEGUE acusar?"*.
#
# Então a note é quebrada de propósito, a RÉGUA é chamada (não uma cópia da
# regra, §9.4), o vermelho é conferido e a note volta.
rota_ref = [r for r in M.rotas()
            if (r.seguradora, r.ramo, r.servico) == ("allianz", "residencial",
                                                     "maquina_de_lavar")][0]
antes = _item("allianz", "residencial", "maquina_de_lavar")
alvo = next(p for p in M.get_playbook(rota_ref.ref)["ura_steps"]
            if p.get("notes") and re.search(r"(\d+)\s*(?:msgs?|telas?)", str(p["notes"]))
            and p.get("anchor"))
guardada = alvo["notes"]
alvo["notes"] = "📊 0 telas / 0 sessões."      # declara MENOS do que o corpus tem
quebrada = _item("allianz", "residencial", "maquina_de_lavar")
alvo["notes"] = guardada
devolvida = _item("allianz", "residencial", "maquina_de_lavar")

certo(quebrada.pontos < antes.pontos,
      "🔴 CONTROLE: uma note SUB-DECLARADA derruba o item — ele consegue "
      f"acusar (passo `{alvo.get('step')}`)",
      f"{antes.pontos}/2 -> {quebrada.pontos}/2")
certo(devolvida.pontos == antes.pontos,
      "🔴 CONTROLE: e a note foi RESTAURADA — o guarda não deixa lixo",
      f"{devolvida.pontos}/2 vs {antes.pontos}/2")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
