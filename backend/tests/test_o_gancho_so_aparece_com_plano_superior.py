# -*- coding: utf-8 -*-
r"""🔴 M-B3 · O GANCHO SÓ APARECE COM PLANO SUPERIOR — e ele não vende, passa o caso.

SPEC-EXTRA-001.5 · §6.3. O gancho é a frase *"o plano acima teria carro reserva
por 7 dias"*. Ele só pode existir quando existe para onde ir:

```
gancho  <=>  há plano PUBLICADO de nivel > o contratado, mesmo insurer/ramo/produto
             E a linha daquele serviço NELE diz coberto='sim'
```

🔴 **No nível máximo o gancho é mentira** — promete ao segurado uma troca que
não tem destino. O par de controle deste guarda é isso: a mesma pergunta, a
mesma base, muda só o plano contratado.

🔴 **E ele não vende** (D-PILOTO-12): não diz preço, não promete que a
seguradora aceita, e quem cuida do caso é a ATENDENTE do card Equipe — nunca o
nome do agente, que é escolha da corretora e não é uma pessoa que possa orçar
nada.
"""
from __future__ import annotations

import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "tests"))

from base_de_planos_em_memoria import BaseEmMemoria  # noqa: E402

from app.services.skills.cobertura_e_assistencia import responder_cobertura  # noqa: E402

OK = FAIL = 0


def checar(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA \U0001F534 {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


db = BaseEmMemoria()
BASICO = db.plano(insurer_key="porto", ramo="auto", produto="Auto Perfil",
                  plano="Essencial", nivel=1, documento_id="doc-porto", pagina=8)
TOPO = db.plano(insurer_key="porto", ramo="auto", produto="Auto Perfil",
                plano="Completo", nivel=2, documento_id="doc-porto", pagina=8)
db.servico(BASICO, "carro_reserva", "nao", documento_id="doc-porto", pagina=23)
db.servico(TOPO, "carro_reserva", "sim", documento_id="doc-porto", pagina=24,
           limite_valor=7, limite_unidade="dias")


def apolice(plano: str, nivel: int) -> dict:
    return {"insurer": "Porto Seguro", "ramo": "auto", "produto": "Auto Perfil",
            "plano": plano, "nivel": nivel, "estado_do_plano": "contratado"}


PERGUNTA = "tem carro reserva?"

print("\n[PAR A] nível 1, com um nível 2 publicado que COBRE -> gancho")
v1 = responder_cobertura(pergunta=PERGUNTA, apolice=apolice("Essencial", 1), db=db,
                         atendente="Regina")
checar(v1 is not None and v1.gancho is not None,
       "🔴 existe plano superior que cobre: o gancho aparece",
       repr(getattr(v1, "gancho", None)))
checar(v1.gancho.get("plano_superior") == "Completo" and v1.gancho.get("nivel") == 2,
       "e ele NOMEIA o plano superior e o nível", repr(v1.gancho))
checar("Regina" in v1.texto,
       "🔴 quem cuida do caso é a ATENDENTE, nomeada (D-PILOTO-12)", v1.texto)
checar("Completo" in v1.texto and "7 dias" in v1.texto,
       "e o texto diz o que o plano acima teria", v1.texto)

print("\n[PAR B] 🔴 CONTROLE: o MESMO serviço, no nível MÁXIMO -> SEM gancho")
# 🔴 O plano de BAIXO cobre guincho e o de CIMA nao. E proposital: se o
# filtro "nivel > o contratado" for afrouxado, o motor acha o BASICO e
# oferece como "plano acima" a alguem que ja esta no topo. Sem esta linha a
# mutacao (d) passaria despercebida — foi o que aconteceu na 1a rodada.
db.servico(BASICO, "guincho", "sim", documento_id="doc-porto", pagina=29,
           limite_valor=200, limite_unidade="km")
db.servico(TOPO, "guincho", "nao", documento_id="doc-porto", pagina=30)
v2 = responder_cobertura(pergunta="tem guincho?", apolice=apolice("Completo", 2), db=db,
                         atendente="Regina")
checar(v2 is not None and v2.estado == "nao_coberto",
       "no nível máximo a resposta continua sendo `nao_coberto`, com fonte",
       repr(getattr(v2, "estado", None)))
checar(v2 is not None and v2.gancho is None,
       "🔴 CONTROLE: e o gancho NÃO aparece — não há plano acima para onde ir",
       repr(getattr(v2, "gancho", None)))
checar("plano acima" not in v2.texto.lower(),
       "🔴 e o TEXTO não promete plano acima nenhum", v2.texto)

print("\n[PAR C] 🔴 CONTROLE 2: há plano superior, mas ele TAMBÉM não cobre -> sem gancho")
db.servico(BASICO, "hospedagem", "nao", documento_id="doc-porto", pagina=40)
db.servico(TOPO, "hospedagem", "nao", documento_id="doc-porto", pagina=41)
v3 = responder_cobertura(pergunta="o seguro paga hotel?", apolice=apolice("Essencial", 1),
                         db=db, atendente="Regina")
checar(v3 is not None and v3.gancho is None,
       "🔴 CONTROLE 2: existir plano acima não basta — ele tem de COBRIR o serviço",
       repr(getattr(v3, "gancho", None)))

print("\n[1] o gancho NÃO vende")
for rotulo, v in (("par A", v1),):
    checar(not re.search(r"R\$|pre[çc]o|custa|valor d[aeo]", v.texto, re.IGNORECASE),
           f"🔴 {rotulo}: sem preço, sem 'R$', sem 'quanto custa'", v.texto)
    checar(not re.search(r"a seguradora (vai )?aceita|garantid[oa]|com certeza", v.texto,
                         re.IGNORECASE),
           f"🔴 {rotulo}: sem promessa de que a seguradora aceita a troca", v.texto)

print("\n[2] 🔴 CONTROLE do bloco: o motor CONSEGUE dar as duas respostas")
checar((v1.gancho is not None) != (v2.gancho is not None),
       "🔴 CONTROLE: mesma base, mesmo motor — com gancho e sem gancho. "
       "O que mudou foi o NÍVEL contratado, e mais nada",
       f"nivel1={v1.gancho is not None} nivelMax={v2.gancho is not None}")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
