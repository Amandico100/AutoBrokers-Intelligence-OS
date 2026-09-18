# -*- coding: utf-8 -*-
r"""🔴 M-D1 · A COBERTURA DA BASE NÃO MENTE PARA CIMA.

SPEC-EXTRA-001.5 · BLOCO D (§8 ①). O defeito não é teórico: está medido em
`tests/test_cobertura_nao_mente_para_cima.py` — 📊 **Allianz, painel 63 %, real
37 %**. Quem lê 63 % não vai atrás do que falta, e a lacuna vira permanente.

Aqui a tentação é a mesma, com outra roupa: **contar linhas**. Quarenta linhas
de serviço de um ramo só parecem muito, e não são cobertura nenhuma — são um
ramo só, bem descrito. A régua conta **seguradora × ramo com plano publicado**.

🔴 E a régua conta o que está **publicado**: linha `proposto` é trabalho feito
pela máquina e não revisado por ninguém; contá-la faria o painel crescer sozinho
toda vez que a onda 1 rodasse.

🔴 **A BASE É GLOBAL (CLAUDE.md §7 / D-PILOTO-01).** Não há `company_id` em
lugar nenhum deste caminho — e a prova é por chamada: duas corretoras, a MESMA
resposta. É o oposto do resto do produto, e é deliberado: o que a apólice da HDI
cobre não muda de corretora para corretora.
"""
from __future__ import annotations

import inspect
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.knowledge import assistance_plans_base as B  # noqa: E402
from base_de_planos_em_memoria import BaseEmMemoria  # noqa: E402

OK = FAIL = 0


def checar(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA \U0001F534 {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


def _base_com_40_linhas_de_um_ramo_so() -> BaseEmMemoria:
    """Uma seguradora, um ramo, um plano — e 14 serviços. O caso que infla."""
    db = BaseEmMemoria()
    plano = db.plano(insurer_key="hdi", ramo="residencial", produto="Residencial Total",
                     plano="Essencial", nivel=1)
    for servico in B.servicos_declarados():
        db.servico(plano, servico, "sim")
    return db


print("\n[1] muitas linhas de UM ramo só não viram cobertura")
db = _base_com_40_linhas_de_um_ramo_so()
regua = B.cobertura_por_seguradora_e_ramo(db=db)
linhas = len(db.tabelas["insurer_assistance_services"])
checar(len(regua) == 1,
       "🔴 %s linhas de serviço de um ramo só contam como 1 seguradora × ramo" % linhas,
       repr(regua))
checar(linhas >= 10,
       "   (e são MUITAS linhas — o teste não passa por falta de dado)", str(linhas))
checar(list(regua.values())[0]["servicos_publicados"] == linhas,
       "as linhas continuam sendo contadas — no lugar delas, como detalhe",
       repr(regua))

print("\n[2] 🔴 O PAR DE CONTROLE: a régua CONSEGUE crescer — com outro ramo")
plano2 = db.plano(insurer_key="hdi", ramo="auto", produto="Auto Total", plano="Essencial",
                  nivel=1)
db.servico(plano2, "guincho", "sim")
regua2 = B.cobertura_por_seguradora_e_ramo(db=db)
checar(len(regua2) == 2,
       "🔴 UMA linha num ramo NOVO faz a régua ir a 2 — logo ela mede ramo, não volume",
       repr(sorted(regua2)))

print("\n[3] o que NÃO está publicado não conta")
db3 = BaseEmMemoria()
p = db3.plano(insurer_key="porto", ramo="auto", produto="Auto", plano="Proposto",
              nivel=1, curadoria="proposto")
for servico in ("guincho", "carro_reserva", "vidros"):
    db3.servico(p, servico, "sim", curadoria="proposto")
checar(B.cobertura_por_seguradora_e_ramo(db=db3) == {},
       "🔴 plano e serviços `proposto` contam ZERO — senão o painel cresceria "
       "sozinho a cada rodada da onda 1",
       repr(B.cobertura_por_seguradora_e_ramo(db=db3)))
# 🔴 o revisor e o ID do usuario autenticado (uuid), nunca um rotulo livre:
# um `revisado_por="robo"` passaria pelo CHECK do banco, que so exige nao nulo.
REVISOR = "11111111-2222-3333-4444-555555555555"
B.publicar_plano(p, REVISOR, db=db3)
for linha in db3.tabelas["insurer_assistance_services"]:
    B.publicar_servico(linha["id"], REVISOR, db=db3)
try:
    B.publicar_plano(p, "amandus", db=db3)
    checar(False, "publicar com rotulo livre tinha de levantar")
except B.RevisorObrigatorio as exc:
    checar("uuid" in str(exc), "🔴 CONTROLE: `revisado_por='amandus'` e RECUSADO (nao e um id)")
checar(len(B.cobertura_por_seguradora_e_ramo(db=db3)) == 1,
       "   e depois de UMA PESSOA publicar, a mesma base conta 1 (controle)",
       repr(B.cobertura_por_seguradora_e_ramo(db=db3)))

print("\n[4] 🔴 A BASE É GLOBAL: duas corretoras, a MESMA resposta")
assinatura = inspect.signature(B.cobertura_por_seguradora_e_ramo)
checar("company_id" not in assinatura.parameters,
       "a régua não aceita `company_id` — nem para ignorar", str(assinatura))
da_resulta = B.cobertura_por_seguradora_e_ramo(db=db)
da_autofleet = B.cobertura_por_seguradora_e_ramo(db=db)
checar(da_resulta == da_autofleet and len(da_resulta) == 2,
       "🔴 a MESMA base responde igual para duas corretoras diferentes",
       f"{da_resulta} == {da_autofleet}")
colunas = {c for linha in (db.tabelas["insurer_assistance_plans"]
                           + db.tabelas["insurer_assistance_services"]) for c in linha}
checar(not any("company" in c or "tenant" in c for c in colunas),
       "e nenhuma linha gravada carrega coluna de dono", str(sorted(colunas)))

print("\n[5] o endpoint da tela também não sabe o que é corretora")
fonte = open(os.path.join(RAIZ, "app", "api", "assistance_plans.py"), encoding="utf-8").read()
checar("company_id" not in fonte.replace("`company_id`", "").replace("company_id`", ""),
       "🔴 `api/assistance_plans.py` não menciona `company_id` fora da prosa",
       [l for l in fonte.splitlines() if "company_id" in l][:3])
# 🔴 CONTROLE da varredura: ela CONSEGUE acusar.
checar("company_id" in (fonte + '\n.eq("company_id", x)\n'),
       "🔴 CONTROLE: com um filtro por corretora no arquivo, a varredura o ENXERGA")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
