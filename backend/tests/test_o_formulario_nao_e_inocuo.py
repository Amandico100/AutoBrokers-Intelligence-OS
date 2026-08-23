# -*- coding: utf-8 -*-
r"""🔴 A tela que TRAVA o acionamento não é uma tela inócua.

📊 SPEC-084.2 C6. `replay.py` chamava `match_ura_step`,
`detect_handoff_trigger` e `extract_capture_anchors` — e **nunca**
`detect_native_flow`. `regua_motor` nem sequer a reexportava, então nenhum
consumidor da régua conseguia chamá-la sem furar a camada.

As 5 telas de formulário nativo do corpus caíam em
`_tela_pede_alguma_coisa=False`, porque o texto que ABRE o flow não tem marca de
pergunta: **a pergunta está DENTRO do formulário**. Saíam do denominador como
`ORFA_INOCUA`, e o item *"zero órfãs funcionais"* dava 20/20 a duas rotas que
não respondem o formulário.

🔴 **Este furo não é o do C8** (a régua punindo o comportamento certo). É o
inverso, e o mais perigoso: **a régua PREMIANDO o buraco.**

📊 O buraco é material: com os slots que o corredor declara coletar,
`montar_resposta_de_flow` devolve `ok=False` com três campos faltando — três
perguntas que ninguém faz ao segurado.

⚠️ E a trava que este guarda protege mais que os pontos: o replay consulta o
formulário **antes** do passo. Sem isso, três linhas de âncora de texto
comprariam os 20 pontos de volta e apagariam o defeito — a URA não aceita texto
naquela tela.
"""
from __future__ import annotations

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

import regua_motor as M      # noqa: E402
import replay as RP          # noqa: E402

OK = FAIL = 0


def certo(cond, nome, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {nome}")
    else:
        FAIL += 1
        print(f"  FALHA \U0001F534 {nome}" + (f"\n        {detalhe}" if detalhe else ""))


print("=" * 74)
print("[1] A CAMADA DA RÉGUA APONTA PARA O MOTOR DO FORMULÁRIO")
print("=" * 74)

for fn in ("detect_native_flow", "native_flow", "montar_resposta_de_flow",
           "flow_components", "slots_com_padrao_do_motor"):
    certo(callable(getattr(M, fn, None)),
          f"\U0001F4CA `regua_motor.{fn}` existe e é chamável")

print()
print("=" * 74)
print("[2] AS TELAS DE FORMULÁRIO ENTRAM NO DENOMINADOR")
print("=" * 74)

com_flow = {}
for rota in M.rotas():
    rp = RP.replay(rota)
    if rp.formularios:
        com_flow[str(rota)] = rp

certo(len(com_flow) == 2,
      "\U0001F4CA duas rotas têm formulário nativo no corpus",
      str(sorted(com_flow)))

for nome, rp in sorted(com_flow.items()):
    telas_flow = [t for t in rp.telas if str(t.passo or "").startswith("flow")]
    certo(all(t.classe != RP.ORFA_INOCUA for t in telas_flow),
          f"\U0001F534 {nome}: nenhuma tela de formulário é ORFA_INOCUA",
          str([t.classe for t in telas_flow]))
    certo(all(t.classe == RP.ORFA_FUNCIONAL for t in telas_flow),
          f"   {nome}: hoje elas são ORFA_FUNCIONAL — o corredor não as responde",
          str([(t.classe, t.passo) for t in telas_flow][:2]))

print()
print("=" * 74)
print("[3] E A EVIDÊNCIA DIZ QUAIS PERGUNTAS FALTAM AO SEGURADO")
print("=" * 74)
print("     'faltam três perguntas' vale mais que 'tem uma tela estranha aqui'")

nomes = {str(t.passo) for rp in com_flow.values() for t in rp.telas
         if str(t.passo or "").startswith("flow_falta")}
faltantes = {c for n in nomes for c in n.split(":", 1)[1].split(",")}
for campo in ("rb_EmGaragemOuEstacionamento", "rb_NivelDaRua",
              "rb_InformacoesLocal"):
    certo(campo in faltantes, f"a evidência nomeia `{campo}`",
          str(sorted(faltantes)))

print()
print("=" * 74)
print("[4] \U0001F534 O CONTROLE: a classificação CONSEGUE ser diferente")
print("=" * 74)
print("     um guarda que não tem como falhar não guarda nada (§9.3)")

# 🔴 CONTROLE POSITIVO: a tela do formulário é a que MUDA.
#    CONTROLE NEGATIVO: uma tela inócua de verdade CONTINUA inócua e fora do
#    denominador. Sem esta metade, "nenhuma órfã inócua" seria indistinguível
#    de "o replay parou de produzir órfãs inócuas".
inocuas = sum(rp.orfas_inocuas for rp in com_flow.values())
certo(inocuas > 0,
      "\U0001F534 CONTROLE: as rotas ainda TÊM órfãs inócuas — a classe não "
      "sumiu, só deixou de abrigar o formulário",
      f"{inocuas} órfãs inócuas nas duas rotas")

# 🔴 E o mecanismo consegue dizer RESPONDIDA: com os slots do formulário
#    preenchidos, `montar_resposta_de_flow` fecha. É a prova de que a classe
#    não é ORFA_FUNCIONAL fixa — a rota TEM como ficar verde quando consertada.
pb_hdi = M.get_playbook("hdi-auto-whatsapp@v1") or {}
flow = None
for rp in com_flow.values():
    for t in rp.telas:
        if str(t.passo or "").startswith("flow"):
            flow = M.detect_native_flow(pb_hdi, t.texto)
            if flow:
                break
    if flow:
        break

certo(flow is not None, "\U0001F4CA o schema do formulário foi achado pelo texto real")

if flow is not None:
    cheio = {}
    for _tela, comp in M.flow_components(flow):
        nome_slot = str(comp.get("slot") or "")
        if nome_slot:
            ops = comp.get("options") or []
            cheio[nome_slot] = str(ops[0].get("id")) if ops else "sim"
    montado = M.montar_resposta_de_flow(flow, cheio)
    certo(montado.get("ok"),
          "\U0001F534 CONTROLE: com TODOS os campos, a resposta MONTA — logo a "
          "classe consegue ser RESPONDIDA, e a rota tem como ficar verde",
          str(montado.get("missing")))
    vazio = M.montar_resposta_de_flow(flow, {})
    certo(not vazio.get("ok"),
          "   e com NENHUM campo ela recusa — os dois lados conseguem diferir")

print()
print("=" * 74)
print("[5] \U0001F534 A TRAVA ANTI-SOMBRA: o formulário vem ANTES do passo")
print("=" * 74)
print("     senão três linhas de âncora comprariam os 20 pontos de volta")

fonte = open(os.path.join(RAIZ, "scripts", "replay.py"), encoding="utf-8").read()
i_flow = fonte.find("flow = M.detect_native_flow(pb, texto)")
i_passo = fonte.find("passo = (None if flow is not None")
certo(i_flow > 0 and i_passo > i_flow,
      "\U0001F534 `detect_native_flow` é consultado ANTES de `match_ura_step`",
      f"flow em {i_flow}, passo em {i_passo}")

# 📊 E o custo da inversão é zero hoje: nenhuma tela de flow casa passo nenhum.
sombras = []
for nome, rp in com_flow.items():
    rota = [r for r in M.rotas() if str(r) == nome][0]
    pb = M.get_playbook(rota.ref) or {}
    for t in rp.telas:
        if str(t.passo or "").startswith("flow"):
            if M.match_ura_step(pb, t.texto, subservice=rota.servico) is not None:
                sombras.append(nome)
certo(not sombras,
      "\U0001F4CA CONTROLE: hoje nenhuma tela de formulário casa passo de texto "
      "— a inversão custa ZERO ponto, é guarda e não queda",
      str(sombras))

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
raise SystemExit(1 if FAIL else 0)
