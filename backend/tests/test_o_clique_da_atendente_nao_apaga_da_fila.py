# -*- coding: utf-8 -*-
"""🔴 O clique da atendente NÃO pode apagar o caso da Fila.

📊 Achado em 26/08/2026 por auditoria da SPEC-093, e é uma REGRESSÃO:

    app/api/dashboard/atendimentos/route.ts:160
        .eq('unblock_state', 'travado')        <-- igualdade EXATA

O BLOCO C da SPEC-093 passou a gravar `assumido_por_humano` quando alguém
destrava pelo WhatsApp. Com a igualdade exata, **bastava a atendente mandar
"só um minuto" para o caso travado sumir da única Fila que existe** — assim
que o Redis expirasse (TTL de 6h, `dispatch_router.py:77`).

🔴 E não voltava nunca: `_fechar_travamento` (`dispatch_router.py:1126-1128`)
filtra `['travado','retomado_pelo_robo']` **de propósito**, para não pisar em
`assumido_por_humano`. Estado terminal e invisível.

⚠️ **E é a mesma classe de defeito que `e527705` consertou na véspera** — o
commit chama-se literalmente *"o desfecho parava de apagar da Fila quem ainda
espera gente"*. Consertado em 25/08, reintroduzido por outra porta em 26/08.

## O motivo de produto, que é o que decide

O Founder desenhou assim, com estas palavras: *"não é para ela assumir o
atendimento. É para ele apenas destravar e monitorar."*

> **A atendente DESTRAVA. Ela não assume.** O caso continua sendo do robô,
> continua em voo, e continua precisando de olho. Tirá-lo da Fila é dizer que
> alguém tomou conta — e ninguém tomou.

E o docstring de `_fechar_travamento:1114` já dizia: *"um travamento que o
acionamento não resolveu **continua na Fila**, que é o produto inteiro desta
SPEC"*.

## Por que este guarda é de FONTE, e não de banco

A Fila é uma rota Next.js que fala com o Supabase. Testá-la de ponta a ponta
exigiria subir o servidor e semear o banco. 🔴 Este guarda lê o **fonte** e
prova a única coisa que o defeito precisava: que o filtro não é uma igualdade
exata em `'travado'`.

⚠️ É um guarda mais fraco que um de comportamento — e a fraqueza está escrita
aqui de propósito, para que ninguém o confunda com prova de que a Fila
funciona. **Ele prova que ESTE defeito não voltou.**
"""
from __future__ import annotations

import io
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROTA = os.path.join(os.path.dirname(RAIZ), "app", "api", "dashboard",
                    "atendimentos", "route.ts")

OK = FAIL = 0


def certo(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  ok    %s" % rotulo)
    else:
        FAIL += 1
        print("  FALHA %s" % rotulo + ("\n        %s" % detalhe if detalhe else ""))


def main() -> int:
    print("\n[1] A FILA NAO PODE FILTRAR SO POR 'travado'")

    if not os.path.exists(ROTA):
        print("  FALHA a rota nao existe: %s" % ROTA)
        return 1

    fonte = io.open(ROTA, encoding="utf-8").read()

    # tira comentarios: o texto EXPLICA o defeito e citaria o padrao proibido
    sem_comentario = re.sub(r"//[^\n]*", "", fonte)
    sem_comentario = re.sub(r"/\*.*?\*/", "", sem_comentario, flags=re.S)

    igualdade_exata = re.search(
        r"\.eq\(\s*['\"]unblock_state['\"]\s*,\s*['\"]travado['\"]\s*\)",
        sem_comentario)
    certo(
        igualdade_exata is None,
        "o filtro NAO e `.eq('unblock_state','travado')`",
        "igualdade exata apaga da Fila o caso que a atendente destravou, "
        "assim que o Redis expira. Use `.in(...)`.")

    usa_in = re.search(
        r"\.in\(\s*['\"]unblock_state['\"]\s*,\s*\[[^\]]*['\"]travado['\"]",
        sem_comentario)
    certo(usa_in is not None,
          "o filtro usa `.in('unblock_state', [...])` incluindo 'travado'")

    certo("assumido_por_humano" in sem_comentario,
          "`assumido_por_humano` esta entre os estados que a Fila mostra",
          "e o estado que o BLOCO C da SPEC-093 grava quando um humano "
          "destrava pelo WhatsApp")

    # ------------------------------------------------------------------
    print("\n[2] LINHA DE CONTROLE -- o guarda CONSEGUE ficar vermelho?")
    # 🔴 Sem isto, um erro de regex faria os tres acima passarem para sempre.
    falso = "  .eq('unblock_state', 'travado')\n"
    certo(
        re.search(r"\.eq\(\s*['\"]unblock_state['\"]\s*,\s*['\"]travado['\"]\s*\)",
                  falso) is not None,
        "o padrao proibido E detectavel quando esta presente",
        "se este controle falhar, os testes de cima passam por vacuidade e "
        "nao guardam nada (CLAUDE.md §9.3)")

    certo(
        re.search(r"\.in\(\s*['\"]unblock_state['\"]\s*,\s*\[[^\]]*['\"]travado['\"]",
                  falso) is None,
        "o padrao BOM nao e detectado num texto que nao o tem",
        "um casador que casa com tudo aprova qualquer coisa")

    print("\n  %d ok, %d falhas" % (OK, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
