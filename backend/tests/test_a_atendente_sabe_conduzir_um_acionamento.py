# -*- coding: utf-8 -*-
"""A atendente sabe o que perguntar ANTES de chamar a ferramenta.

O DEFEITO, MEDIDO
=================
📊 19/08/2026, consulta em `agents` (producao): os SETE agentes cadastrados tem
prompt entre 636 e 7.914 caracteres, e **nenhum** contem "eletrodomestico" ou
"maquina de lavar". O da atendente da Resulta (Saionara) tem 1.539 caracteres,
e diz o que NAO fazer -- nunca prometer cobertura, nunca inventar protocolo --
sem dizer o que FAZER num acionamento.

O conhecimento existia espalhado: na descricao dos parametros da ferramenta,
em comentario de codigo, e nas telas mapeadas do corredor. Nada disso chega a
conversa. A atendente descobria o que faltava DEPOIS de chamar a ferramenta e
receber `missing_data` -- o que, ao vivo, parece hesitacao.

A SOLUCAO, E POR QUE ELA E GERADA
==================================
`conhecimento_de_assistencia(refs)` monta o texto a partir dos PROPRIOS
corredores. Texto fixo seria uma segunda fonte de verdade sobre o que cada
rota exige, e no dia em que um `required_slots` mudasse o prompt continuaria
ensinando a versao velha -- sem nada ficar vermelho.

🔴 Foi exatamente esse o defeito de 18/08: `aparelho_marca_modelo` virou dois
campos (`aparelho_marca` + `aparelho_modelo`) e o resto do produto nao soube.
Este guarda existe para que a proxima mudanca de slot chegue sozinha ao prompt.
"""
from __future__ import annotations

import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _pkg in ("app", "app.services", "app.core"):
    if _pkg not in sys.modules:
        _m = types.ModuleType(_pkg)
        _m.__path__ = [os.path.join(_RAIZ, *_pkg.split("."))]
        sys.modules[_pkg] = _m

import importlib  # noqa: E402

CP = importlib.import_module("app.services.corridor_playbooks")

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


TODOS = sorted(CP._PLAYBOOKS)
BLOCO = CP.conhecimento_de_assistencia(TODOS)
SO_ALLIANZ_RESID = CP.conhecimento_de_assistencia(["allianz-residencial-whatsapp@v1"])

print()
print("=" * 74)
print("  1. O BLOCO SAI DOS CORREDORES — nao de texto escrito a mao")
print("=" * 74)

# Para CADA rota de CADA corredor, tudo que ela exige do cliente tem de estar
# dito no bloco, em portugues. Esta e a assercao que faz o texto seguir o
# codigo: acrescente um `required_slots` e ela fica vermelha ate o rotulo
# existir.
faltando = []
for ref in TODOS:
    pb = CP._PLAYBOOKS[ref]
    for rota, sub in (pb.get("subservices") or {}).items():
        for slot in sub.get("required_slots") or []:
            if slot in CP._NAO_SE_PERGUNTA:
                continue
            rotulo = CP._COMO_PERGUNTAR.get(slot)
            if not rotulo or rotulo not in BLOCO:
                faltando.append((ref, rota, slot))

certo(not faltando,
      "🔴 todo slot que o cliente precisa informar aparece no bloco, "
      "em portugues",
      "sem rotulo: " + "; ".join(f"{s} ({r}/{ro})" for r, ro, s in faltando[:6]))

certo(not any(f"  · {s}" in BLOCO for s in
              ("titular_cpf", "aparelho_marca", "periodo_preferido")),
      "e NENHUM nome interno de campo vaza para o texto",
      "chave interna na tela de quem trabalha e o defeito do dossie antigo")

print()
print("=" * 74)
print("  2. O CASO DE HOJE — maquina de lavar da Allianz residencial")
print("=" * 74)

req = CP._PLAYBOOKS["allianz-residencial-whatsapp@v1"]["subservices"]["maquina_de_lavar"]["required_slots"]
certo(len(req) == 7, f"a rota exige 7 dados ({len(req)})", str(req))
for slot in req:
    if slot in CP._NAO_SE_PERGUNTA:
        continue
    certo(CP._COMO_PERGUNTAR[slot] in SO_ALLIANZ_RESID,
          f"o bloco ensina a pedir: {slot}")

certo("AGENDADO" in SO_ALLIANZ_RESID and "Nao e hoje" in SO_ALLIANZ_RESID.replace("ã", "a").replace("é", "e"),
      "🔴 e avisa que conserto de eletrodomestico e AGENDADO, nao e hoje",
      "cliente que ouviu 'vou acionar' e esperava alguem em uma hora liga bravo")
certo("10 anos" in SO_ALLIANZ_RESID,
      "e diz a regra dos 10 anos, que pode fazer o chamado ser recusado")
certo("PEÇAS" in SO_ALLIANZ_RESID or "PECAS" in SO_ALLIANZ_RESID,
      "e que as pecas sao por conta do cliente")
certo("4 últimos" in SO_ALLIANZ_RESID or "4 ultimos" in SO_ALLIANZ_RESID,
      "e a senha do prestador (4 ultimos digitos do telefone)")

print()
print("=" * 74)
print("  3. O QUE O BLOCO NAO PODE FAZER")
print("=" * 74)

certo(CP.conhecimento_de_assistencia([]) == "",
      "🔴 corretora sem corredor recebe bloco VAZIO",
      "ensinar a acionar quem nao pode acionar e prometer o que nao se alcanca")
certo(CP.conhecimento_de_assistencia(["corredor-que-nao-existe@v9"]) == "",
      "e referencia invalida tambem devolve vazio, sem estourar")

certo("📊" not in BLOCO,
      "🔴 nenhuma marca de medicao interna vaza para a fala com o cliente",
      "📊 e marcador de nota tecnica (§12.1), nao texto de conversa")

# 🔴 A regra repetida em tres corredores aparece UMA vez -- e na redacao
# generica. 📊 Antes vinha "maior de 18 anos para acompanhar o GUINCHO", dito
# a um cliente de maquina de lavar.
dezoito = [ln for ln in BLOCO.splitlines() if "18 anos" in ln]
certo(len(dezoito) == 1,
      f"a regra dos 18 anos aparece UMA vez ({len(dezoito)})",
      "; ".join(dezoito))
certo(dezoito and "guincho" not in dezoito[0].lower(),
      "🔴 e na redacao generica, sem citar guincho",
      dezoito[0] if dezoito else "")

# CONTROLE: o bloco CONSEGUE falar de guincho onde e certo — na lista de
# coleta. Sem isto, o teste acima passaria num bloco que so nao fala de nada.
certo("guincho" in BLOCO.lower(),
      "CONTROLE: e o bloco FALA de guincho onde e certo (a rota de auto)")

print()
print("=" * 74)
print("  4. O TAMANHO — conhecimento que nao cabe nao ensina")
print("=" * 74)

certo(len(BLOCO) < 7000,
      f"o bloco cabe no prompt ({len(BLOCO)} caracteres, teto 7000)",
      "📊 uma linha por (corredor x rota) dava 7.763 e repetia 'peca o CPF' "
      "catorze vezes")
certo(len(BLOCO) > 1500,
      f"CONTROLE: e nao esta vazio nem truncado ({len(BLOCO)})")

print()
print("=" * 74)
print("  5. SO QUEM TEM A FERRAMENTA RECEBE O BLOCO")
print("=" * 74)

graph = open(os.path.join(_RAIZ, "app", "agents", "graph.py"),
             encoding="utf-8").read()
certo("conhecimento_de_assistencia" in graph,
      "o grafo chama o gerador")
certo('_papel == "attendance"' in graph,
      "🔴 e so para o papel `attendance`")
# CONTROLE: e o MESMO papel que ganha a ferramenta.
certo('== "attendance"' in graph and "InsurerDispatchTool" in graph,
      "CONTROLE: que e o mesmo papel que recebe InsurerDispatchTool",
      "se os dois gates divergirem, o agente sabe acionar e nao consegue, "
      "ou consegue e nao sabe")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
