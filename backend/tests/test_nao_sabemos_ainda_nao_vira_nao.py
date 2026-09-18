# -*- coding: utf-8 -*-
r"""🔴 M-B1 · "NÃO SABEMOS AINDA" NÃO VIRA "NÃO" — e "não consegui olhar" é um terceiro.

SPEC-EXTRA-001.5 · BLOCO B. Três coisas diferentes chegam ao segurado pela
mesma pergunta, e confundi-las custa dinheiro dele:

```
nao_sabemos_ainda   "a condição geral dessa seguradora ainda não está na base"
nao_coberto         "o contrato DELE diz que não"          -> com documento e página
fonte_indisponivel  "não consegui abrir a apólice agora"   -> é FALHA, não resposta
```

🔴 **O primeiro virando o segundo** faz o agente dizer "não cobre" com a base
vazia — e o segurado deixa de acionar um serviço a que tinha direito. É o
defeito mais caro desta SPEC, e é silencioso: ninguém reclama de um "não".

🔴 **O terceiro virando o primeiro** esconde uma queda de infraestrutura atrás
de uma lacuna de curadoria. Quem lê o painel vai atrás de curar documento
enquanto o Qdrant/banco está fora do ar.

⚠️ Este guarda chama o MOTOR (CLAUDE.md §9.4): `responder_cobertura` de
verdade, sobre `assistance_plans_base` de verdade, com o transporte duplo. Não
há regex sobre a tabela que o código lê.
"""
from __future__ import annotations

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "tests"))

from base_de_planos_em_memoria import BaseEmMemoria, BaseQueCai  # noqa: E402

from app.services.skills.cobertura_e_assistencia import (  # noqa: E402
    FALHA,
    responder_cobertura,
)

OK = FAIL = 0


def checar(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA \U0001F534 {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


APOLICE = {
    "insurer": "HDI", "ramo": "auto", "produto": "Auto Perfil",
    "plano": "Essencial", "nivel": 1, "estado_do_plano": "contratado",
    "residencial": False, "assistencia_confirmada": True,
}
PERGUNTA = "ele tem carro reserva?"


print("\n[PAR 1a] a base está VAZIA -> nao_sabemos_ainda, com frase própria")
vazia = BaseEmMemoria()
v1 = responder_cobertura(pergunta=PERGUNTA, apolice=APOLICE, db=vazia)
checar(v1 is not None and v1.estado == "nao_sabemos_ainda",
       "🔴 sem linha publicada, o estado é `nao_sabemos_ainda`",
       repr(getattr(v1, "estado", None)))
checar("nao" != str(getattr(v1, "estado", "")) and "nao_coberto" != getattr(v1, "estado", ""),
       "🔴 e NÃO é `nao_coberto` — a base vazia não autoriza dizer 'não cobre'")
texto1 = (v1.texto if v1 else "").lower()
checar("ainda nao tenho" in texto1 or "ainda não tenho" in texto1,
       "a frase diz que a condição geral ainda não está na base", v1.texto if v1 else "")
checar("nao cobre" not in texto1 and "não cobre" not in texto1
       and not texto1.startswith("no plano dele, n"),
       "🔴 e a frase NÃO diz 'não cobre' em lugar nenhum", v1.texto if v1 else "")
checar(v1 is not None and v1.documento_id is None and v1.pagina is None,
       "sem fonte, os campos de fonte vêm VAZIOS — não há citação inventada",
       repr((getattr(v1, 'documento_id', '?'), getattr(v1, 'pagina', '?'))))

print("\n[PAR 1b] a MESMA pergunta, agora com a linha `nao` publicada -> nao_coberto COM FONTE")
cheia = BaseEmMemoria()
plano_id = cheia.plano(insurer_key="hdi", ramo="auto", produto="Auto Perfil",
                       plano="Essencial", nivel=1, documento_id="doc-hdi-cg", pagina=11)
cheia.servico(plano_id, "carro_reserva", "nao", documento_id="doc-hdi-cg", pagina=23)
v2 = responder_cobertura(pergunta=PERGUNTA, apolice=APOLICE, db=cheia)
checar(v2 is not None and v2.estado == "nao_coberto",
       "🔴 com a linha publicada dizendo `nao`, o estado é `nao_coberto`",
       repr(getattr(v2, "estado", None)))
checar(v2 is not None and v2.documento_id == "doc-hdi-cg" and int(v2.pagina) == 23,
       "🔴 e ele traz DOCUMENTO e PÁGINA (§6.2: todo 'não' carrega o lastro)",
       repr((getattr(v2, 'documento_id', None), getattr(v2, 'pagina', None))))
checar("p. 23" in (v2.texto if v2 else ""),
       "🔴 e a PÁGINA aparece no TEXTO que o segurado lê, não só no campo",
       v2.texto if v2 else "")
checar(v2 is not None and v2.origem == "base",
       "a origem é `base` — não é a regra genérica respondendo",
       repr(getattr(v2, "origem", None)))

print("\n[CONTROLE do par 1] o motor CONSEGUE dar os dois estados — e deu")
checar(v1 is not None and v2 is not None and v1.estado != v2.estado,
       "🔴 CONTROLE: mesma pergunta, mesma apólice, mesmo motor — estados DIFERENTES. "
       "O que mudou foi a LINHA publicada, e mais nada",
       f"{getattr(v1,'estado',None)} vs {getattr(v2,'estado',None)}")

print("\n[PAR 2] a busca CAI -> fonte_indisponivel, com TEXTO DIFERENTE")
v3 = responder_cobertura(pergunta=PERGUNTA, apolice=APOLICE, db=BaseQueCai())
checar(v3 is not None and v3.estado == FALHA,
       "🔴 a base derrubada dá `fonte_indisponivel`, não `nao_sabemos_ainda`",
       repr(getattr(v3, "estado", None)))
checar(v3 is not None and v1 is not None and v3.texto.strip() != v1.texto.strip(),
       "🔴 e o TEXTO é diferente do de `nao_sabemos_ainda` — quem lê tem de "
       "saber que a informação existe e NÃO CHEGOU",
       f"falha={getattr(v3,'texto','')!r}\n        naosei={getattr(v1,'texto','')!r}")
texto3 = (v3.texto if v3 else "").lower()
checar("nao consegui abrir" in texto3 or "não consegui abrir" in texto3,
       "a frase diz que não conseguiu ABRIR (falha), não que não sabe (lacuna)",
       v3.texto if v3 else "")
checar("nao cobre" not in texto3 and "não cobre" not in texto3,
       "🔴 e tampouco vira um 'não' — falha nunca é resposta", v3.texto if v3 else "")

print("\n[CONTROLE do par 2] os TRÊS textos são distintos entre si")
textos = {(v1.texto if v1 else "x").strip(), (v2.texto if v2 else "y").strip(),
          (v3.texto if v3 else "z").strip()}
checar(len(textos) == 3,
       "🔴 CONTROLE: `nao_sabemos_ainda`, `nao_coberto` e `fonte_indisponivel` "
       "produzem TRÊS frases diferentes — nenhum par colapsou",
       f"{len(textos)} texto(s) distinto(s)")

print("\n[3] o que NÃO é pergunta de cobertura devolve None — e não consulta a base")
sem_consulta = BaseEmMemoria()
v4 = responder_cobertura(pergunta="quantas parcelas faltam?", apolice=APOLICE, db=sem_consulta)
checar(v4 is None,
       "pergunta de parcela não é pergunta de cobertura: a Skill devolve `None`",
       repr(v4))
checar(sem_consulta.chamadas_de_tabela == [],
       "🔴 e ela não encostou na base — zero consultas",
       repr(sem_consulta.chamadas_de_tabela))

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
