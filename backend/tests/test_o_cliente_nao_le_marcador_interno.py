# -*- coding: utf-8 -*-
r"""🔴 O que chega ao SEGURADO é escrito para ele.

SPEC-084.2 C5. Três defeitos da mesma família, e uma varredura da classe.

```
📊 yelum/residencial enviava "📊 A senha da visita técnica…" ao SEGURADO
   — o 📊 é marcador INTERNO (CLAUDE.md §12.1), "número medido". Para quem
   está esperando um técnico, é um rabisco no meio da frase.

📊 socorro_mecanico recebia "alguém para acompanhar o GUINCHO" — a palavra
   nomeia um caminhão que não vem. O mecânico vai ATÉ o carro.

📊 o dossiê do handoff dizia "Motivo: sem_chute:transporte_destino" a uma
   PESSOA que precisa agir em minutos.
```

E a causa das três é a mesma: **texto de corredor herdado por rota que não é
aquela**, e **identificador cru vazando para onde se lê português**.

⚠️ O guarda varre a CLASSE, não os três casos. E ele tem controle positivo:
sem ele, apagar `client_instructions` faria tudo passar — e o cliente deixaria
de receber a senha da visita.
"""
from __future__ import annotations

import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

import regua_motor as M      # noqa: E402
CP = M.CP
IDS = M.IDS

OK = FAIL = 0


def certo(cond, nome, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {nome}")
    else:
        FAIL += 1
        print(f"  FALHA \U0001F534 {nome}" + (f"\n        {detalhe}" if detalhe else ""))


CAPTURA = {"protocol": "9662631",
           "schedule": {"day": "sexta-feira, 28/08/2026", "periodo": "tarde"}}


def mensagem(ref, servico):
    return str(M.client_summary_from_capture(
        {"playbook_ref": ref, "subservice": servico, "captured": CAPTURA}) or "")


print("=" * 74)
print("[1] NENHUM MARCADOR INTERNO CHEGA AO SEGURADO — em TODAS as rotas")
print("=" * 74)

MARCAS = ("📊", "💭", "🔵")
sujas, cruas = [], []
rotas = list(M.rotas())
for rota in rotas:
    msg = mensagem(rota.ref, rota.servico)
    if any(m in msg for m in MARCAS):
        sujas.append(str(rota))
    if re.search(r"\b\w+_(opcao|slots|situacao|nivel_rua)\b|required_slots|corpus", msg):
        cruas.append(str(rota))

certo(len(rotas) >= 60, "\U0001F4CA o inventário de rotas está carregado",
      f"{len(rotas)} rotas")
certo(not sujas, "\U0001F534 nenhuma marca interna (📊 💭 🔵) chega ao segurado",
      "; ".join(sujas[:6]))
certo(not cruas, "\U0001F534 nenhum nome de campo cru chega ao segurado",
      "; ".join(cruas[:6]))

# 🔴 CONTROLE POSITIVO — sem ele, apagar `client_instructions` passaria verde,
#    e o cliente deixaria de receber a senha da visita técnica.
yelum = mensagem("yelum-residencial-whatsapp@v1", "encanador")
certo("4 últimos dígitos" in yelum,
      "\U0001F534 CONTROLE: a regra da senha CHEGA ao cliente — o guarda acima "
      "não passou por a mensagem estar vazia",
      yelum[:110])

print()
print("=" * 74)
print("[2] A INSTRUÇÃO É DO SERVIÇO, NÃO DO CORREDOR")
print("=" * 74)

sm = mensagem("hdi-auto-whatsapp@v1", "socorro_mecanico")
gc = mensagem("hdi-auto-whatsapp@v1", "guincho")

certo("guincho" not in sm.lower() and "reboque" not in sm.lower(),
      "\U0001F534 socorro mecânico não manda esperar um guincho", sm[:110])
certo("mecânico" in sm.lower(),
      "   e diz que quem vem é o mecânico", sm[:110])

# 🔴 CONTROLE: as duas rotas CONSEGUEM ser diferentes. Se elas fossem sempre
#    iguais, as duas asserções acima seriam impossíveis de reprovar.
certo("guincho" in gc.lower(),
      "\U0001F534 CONTROLE: o guincho continua dizendo guincho — e está certo")
certo(sm != gc,
      "\U0001F534 CONTROLE: as duas mensagens não são a mesma string")

print()
print("=" * 74)
print("[3] LISTA VAZIA É UMA DECISÃO, NÃO UM ACIDENTE")
print("=" * 74)
print("     `or` fazia o [] herdar o texto do guincho; agora é `in`")

taxi = mensagem("porto-auto-whatsapp@v1", "taxi")
certo("guincho" not in taxi.lower() and "documento do veículo" not in taxi.lower(),
      "\U0001F534 porto/taxi não manda o segurado esperar um caminhão — no táxi "
      "ele é o transportado", taxi[:110])
# 🔴 CONTROLE: o mecanismo CONSEGUE entregar instrução — porto/tecnico entrega.
tec = mensagem("porto-auto-whatsapp@v1", "tecnico")
certo("15 minutos" in tec,
      "\U0001F534 CONTROLE: porto/tecnico RECEBE a instrução medida dele — o "
      "silêncio do táxi é escolha, não canal quebrado", tec[:110])

print()
print("=" * 74)
print("[4] O QUE FALTA É DITO EM PORTUGUÊS — uma fonte de verdade só")
print("=" * 74)

fonte = open(os.path.join(RAIZ, "app/agents/tools/insurer_dispatch_tool.py"),
             encoding="utf-8").read()
codigo = "\n".join(l for l in fonte.splitlines()
                   if l.strip() and not l.lstrip().startswith("#"))
certo("friendly = {" not in codigo,
      "\U0001F534 a ferramenta não tem dicionário próprio de rótulos — "
      "`_COMO_PERGUNTAR` é a fonte única",
      "ainda há um `friendly` escrito à mão")

# 📊 Todo slot que o PORTÃO cobra tem redação. O guarda antigo varria só
#    `required_slots`; quem cobra é `missing_slots_for_subservice`, que soma os
#    `requires` dos passos.
sem_redacao = set()
for rota in rotas:
    pb = CP.get_playbook(rota.ref) or {}
    for slot in CP.missing_slots_for_subservice(pb, rota.servico, {}) or []:
        if slot == CP.SUBSERVICO_INVALIDO:
            continue
        if not CP._COMO_PERGUNTAR.get(slot):
            sem_redacao.add(slot)
certo(not sem_redacao,
      "\U0001F534 todo slot que o PORTÃO cobra tem redação em português",
      str(sorted(sem_redacao)))

# 🔴 CONTROLE: a população varrida é MAIOR que `required_slots` — é por isso
#    que este guarda existe ao lado do outro.
so_required = set()
for rota in rotas:
    pb = CP.get_playbook(rota.ref) or {}
    sub = (pb.get("subservices") or {}).get(CP.canonical_subservice(rota.servico)) or {}
    so_required |= set(sub.get("required_slots") or [])
todos = set()
for rota in rotas:
    pb = CP.get_playbook(rota.ref) or {}
    todos |= {s for s in (CP.missing_slots_for_subservice(pb, rota.servico, {}) or [])
              if s != CP.SUBSERVICO_INVALIDO}
certo(len(todos) > len(so_required),
      "\U0001F534 CONTROLE: o portão cobra MAIS que `required_slots` — o guarda "
      "antigo não via essa diferença, e é ela que deixou dois slots sem redação",
      f"portão={len(todos)} · required_slots={len(so_required)}")

print()
print("=" * 74)
print("[5] O MOTIVO DO HANDOFF É LIDO POR GENTE")
print("=" * 74)

ses = IDS.new_dispatch_session(
    case_id="g", company_id="g", playbook_ref="hdi-auto-whatsapp@v1",
    subservice="guincho",
    slots={"titular_cpf": "52998224725", "veiculo_placa": "AAA1111",
           "local_atual": "Rua X, 100", "problema_descricao": "nao liga",
           "quando": "agora", "telefone_contato": "47900000000",
           "local_destino": "oficina", "pessoa_no_local": "Fulano",
           "local_seguro": "sim", "veiculo_em_garagem": "nao",
           "veiculo_nivel_rua": "nivel", "local_situacao": "Local Seguro",
           "meio_transporte_opcao": "Sim"})
ses = IDS.start_dispatch(ses)
ses = IDS.handle_insurer_message(ses, "E para onde devemos te levar?")

certo(ses.get("state") == "needs_human",
      "\U0001F4CA o passo `sem_chute` continua indo para humano — não inventa",
      str(ses.get("state")))
# 🔴 ATUALIZADO na rodada dos juízes · `falta_para_a_ura` alimenta o CÉREBRO,
#    e o `sem_chute` existe para NÃO acordá-lo. O dossiê humano passou a ter
#    campo próprio (`motivo_legivel`) — dois consumidores com necessidades
#    opostas não podem dividir um campo.
rotulo = str((ses.get("motivo_legivel")
              or ses.get("falta_para_a_ura") or {}).get("rotulo") or "")
certo(rotulo and "_" not in rotulo,
      "\U0001F534 e o dossiê diz a PERGUNTA, não o nome do campo",
      f"rotulo={rotulo!r}")
certo("destino DELE" in rotulo or "levado" in rotulo,
      "   e a pergunta distingue o destino da PESSOA do destino do veículo",
      rotulo[:90])

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
raise SystemExit(1 if FAIL else 0)
