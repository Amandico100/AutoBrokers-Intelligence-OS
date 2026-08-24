# -*- coding: utf-8 -*-
r"""🔴 Toda afirmação de COBERTURA aponta uma tela do acervo.

O JUIZ 1 da SPEC-084.2 reprovou duas vezes, e na segunda escreveu a frase que
este guarda existe para tornar desnecessária:

> *"Nenhum guarda compara uma afirmação de cobertura contra o corpus da rota
> que a recebe. Enquanto isso não existir, esta auditoria só acontece quando um
> juiz a faz à mão."*

📊 O que ele achou, à mão, em duas voltas:

```
"a mão de obra é que está coberta"      → verdade no encanador, FALSA no
                                          eletrodoméstico da mesma seguradora
"instalação nova NÃO é coberta"          → invenção: a URA lista "Instalações"
                                          entre os serviços DISPONÍVEIS
"você vai receber um SMS com a previsão" → 0 telas em azul, mapfre, porto,
                                          tokio e yelum
```

🔴 **As três alcançavam um humano** — duas o segurado, uma a atendente que fala
com ele. E as três passavam por todos os testes verdes.

⚠️ Cobertura é da ROTA. Uma afirmação que vive no CORREDOR é verdadeira em
algumas rotas e falsa nas outras, e ninguém percebe, porque o texto é o mesmo.
"""
from __future__ import annotations

import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

import regua_motor as M      # noqa: E402
import replay as RP          # noqa: E402
CP = M.CP

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

# 🔴 As palavras que transformam uma frase em AFIRMAÇÃO DE COBERTURA — a que o
#    segurado usa para decidir se aceita o serviço e quanto vai pagar.
_AFIRMA_COBERTURA = re.compile(
    r"est[áa]\s+cobert|n[ãa]o\s+(?:est[áa]\s+)?cobert|"
    r"por\s+conta\s+do\s+segurado|por\s+conta\s+do\s+cliente|"
    r"ser[áa]\s+negad|recusad|"
    r"voc[êe]\s+vai\s+receber\s+um\s+sms|"
    r"n[ãa]o\s+afeta\s+a\s+sua\s+classe|n[ãa]o\s+ir[áa]\s+afetar",
    re.IGNORECASE)

# ⚠️ O termo do corpus que sustenta cada família de afirmação. Não é a frase
#    inteira — é a PALAVRA que só aparece quando a seguradora falou do assunto.
_LASTRO = (
    (r"cobert", r"cobert"),
    (r"por conta do (?:segurado|cliente)", r"por conta do segurado|peças|pecas"),
    (r"sms", r"\bsms\b"),
    (r"classe de b[ôo]nus", r"classe de b[ôo]nus"),
    (r"negad|recusad", r"negad|recusad|n[ãa]o\s+est[áa]\s+cobert"),
)


def corpus_de(rota):
    return " ".join(str(l.get("text") or "")
                    for l in RP.carregar_corpus(rota.seguradora, rota.ramo))


def mensagem(rota):
    return str(M.client_summary_from_capture(
        {"playbook_ref": rota.ref, "subservice": rota.servico,
         "captured": CAPTURA}) or "")


print("=" * 74)
print("[1] O QUE O SEGURADO LÊ SOBRE COBERTURA TEM TELA QUE SUSTENTE")
print("=" * 74)

rotas = list(M.rotas())
certo(len(rotas) >= 60, "\U0001F4CA o inventário de rotas está carregado",
      f"{len(rotas)} rotas")

sem_lastro = []
com_afirmacao = 0
for rota in rotas:
    msg = mensagem(rota)
    if not msg:
        continue
    for linha in msg.splitlines():
        if not _AFIRMA_COBERTURA.search(linha):
            continue
        com_afirmacao += 1
        texto = corpus_de(rota)
        if not texto:
            continue          # sem acervo não há como conferir — não é achado
        # 🔴 A frase precisa de UMA das famílias de lastro presente no corpus
        #    DAQUELE corredor. É o mínimo: a seguradora falou do assunto.
        casou = False
        for gatilho, lastro in _LASTRO:
            if re.search(gatilho, linha, re.IGNORECASE):
                if re.search(lastro, texto, re.IGNORECASE):
                    casou = True
                break
        if not casou:
            sem_lastro.append(f"{rota}: {linha.strip()[:64]}")

certo(com_afirmacao >= 3,
      "\U0001F4CA existem afirmações de cobertura a conferir",
      f"{com_afirmacao} linhas em {len(rotas)} rotas")
certo(not sem_lastro,
      "\U0001F534 toda afirmação de cobertura tem tela no corredor que a recebe",
      "; ".join(sem_lastro[:5]))

print()
print("=" * 74)
print("[2] \U0001F534 O CONTROLE: a busca CONSEGUE reprovar")
print("=" * 74)
print("     um guarda que não tem como falhar não guarda nada (§9.3)")

# 🔴 A frase que o JUIZ 1 pegou, contra um corredor onde ela tem ZERO telas.
_MENTIRA = "Você vai receber um SMS com a previsão de chegada do prestador."
_porto = " ".join(str(l.get("text") or "")
                  for l in RP.carregar_corpus("porto", "auto"))
certo(_AFIRMA_COBERTURA.search(_MENTIRA) is not None,
      "\U0001F534 CONTROLE: o detector RECONHECE a frase como afirmação")
certo(not re.search(r"\bsms\b", _porto, re.IGNORECASE),
      "\U0001F534 CONTROLE: e o corpus da porto tem ZERO telas com `sms` — "
      "logo a frase seria REPROVADA se estivesse lá",
      f"{len(_porto)} chars de corpus lidos")

# 🔴 E o outro lado: uma afirmação VERDADEIRA passa.
_VERDADE = "Este acionamento de vidros NÃO afeta a sua classe de bônus."
certo(_AFIRMA_COBERTURA.search(_VERDADE) is not None
      and re.search(r"classe de b[ôo]nus", _porto, re.IGNORECASE) is not None,
      "\U0001F534 CONTROLE: e a afirmação VERDADEIRA sobre a classe de bônus "
      "tem tela na porto — os dois lados conseguem diferir")

print()
print("=" * 74)
print("[3] REGRA DE COBERTURA NO BRIEFING TEM DONO")
print("=" * 74)
print("     cobertura é da ROTA; sem dono, alguém aplica na rota errada")

bloco = CP.conhecimento_de_assistencia(CP.list_playbooks())
linhas = bloco.splitlines()
i = next((k for k, l in enumerate(linhas) if "REGRAS DA SEGURADORA" in l), -1)
certo(i >= 0, "\U0001F4CA a seção de regras existe no briefing")

if i >= 0:
    # cada regra tem de vir depois de um cabeçalho `[DONO]`
    dono_atual = None
    orfas = []
    for l in linhas[i + 1:]:
        t = l.strip()
        if not t:
            break
        if t.startswith("["):
            dono_atual = t
        elif t.startswith("·") and not dono_atual:
            orfas.append(t[:56])
    certo(not orfas,
          "\U0001F534 nenhuma regra de cobertura sai sem dizer de QUEM é",
          "; ".join(orfas[:4]))
    certo(dono_atual and ("ALLIANZ" in dono_atual or "·" in dono_atual),
          "   e o dono nomeia a seguradora e o serviço",
          str(dono_atual))

certo(len(bloco) <= 7000,
      "\U0001F4CA e o bloco cabe no teto — dar dono não foi pago subindo o teto",
      f"{len(bloco)} caracteres")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
raise SystemExit(1 if FAIL else 0)
