# -*- coding: utf-8 -*-
"""🔴 A anotação da atendente não pode virar fala da corretora ao cliente.

📊 Achado em 26/08/2026 por auditoria externa da SPEC-090.

A rota do painel gravava a nota em `messages` como `role:'assistant'`, com o
texto **cru**, e a marca `nota_interna` dentro do `payload`:

```
grep -rn "nota_interna" no repositório inteiro  →  2 ocorrências,
                                                   ambas no mesmo arquivo.
                                                   ZERO leitores.
```

⚠️ **E os quatro consumidores de `messages` selecionam `role, content` e nunca
`payload`:**

```
conversation_auditor.py:90   → conversation_scorecards
garimpo_v3.py:78             → sinais e pedidos
memory_fabric.py:217         → memória da empresa
broker_insights.py:186       → insights comerciais
```

🔴 Logo *"o robô perguntou a placa duas vezes"* entrava nos quatro **como turno
da corretora** — e é desse histórico que o produto aprende.

## E nem a atendente distinguia

📊 O `select` da própria thread pede `id, role, content, type, image_url,
audio_url, sender_user_id, created_at`. **Sem `payload`.** A nota aparecia na
conversa idêntica a uma mensagem enviada ao cliente.

## O que torna este defeito exemplar

O comentário no código **já dizia a intenção**, com estas palavras:

> *"`nota_interna` diz que esta linha NÃO foi para o segurado. Sem a marca, uma
> nota vira, no histórico, uma fala da corretora ao cliente — e é desse
> histórico que o produto aprende."*

🔴 **A frase estava certa e não tinha código atrás dela.** É o `CLAUDE.md` §9.3
na forma mais educada: não é um guarda que falha, é uma promessa que ninguém
cumpre — e ela lê como se estivesse cumprida.

## O conserto, e por que é o `content`

A marca foi para onde os leitores olham. ⚠️ `payload.nota_interna` **fica**, como
versão legível por máquina para quem acrescentar filtro depois (P-265).

⛔ **E o envio já estava certo** — não é isto que este arquivo guarda: o backend
responde `{"status":"anotada","enviada":false}`, `delivered = res.ok && !ehNota`,
e a resposta carrega `anotada` para a tela dizer *"anotação registrada"*.
**A nota nunca foi entregue. Ela só ficava gravada indistinguível.**
"""
from __future__ import annotations

import io
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROTA = os.path.join(os.path.dirname(RAIZ), "app", "api", "dashboard",
                    "conversas", "[id]", "route.ts")

OK = FAIL = 0


def certo(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  ok    %s" % rotulo)
    else:
        FAIL += 1
        print("  FALHA %s" % rotulo + ("\n        %s" % detalhe if detalhe else ""))


def _so_o_codigo(fonte: str) -> str:
    """Sem comentários. 🔴 A prosa deste arquivo CITA o defeito inteiro."""
    fonte = re.sub(r"/\*[\s\S]*?\*/", "", fonte)
    return re.sub(r"//[^\n]*", "", fonte)


def main() -> int:
    if not os.path.exists(ROTA):
        print("  FALHA a rota nao existe: %s" % ROTA)
        return 1

    bruto = io.open(ROTA, encoding="utf-8").read()
    codigo = _so_o_codigo(bruto)

    print("\n[1] A MARCA VAI NO `content`, NAO SO NO `payload`")

    certo("PREFIXO_DA_NOTA" in codigo,
          "existe a constante do prefixo")

    certo(re.search(r"content:\s*ehNota\s*\?\s*PREFIXO_DA_NOTA", codigo) is not None,
          "o `content` recebe o prefixo quando e nota",
          "sem isto os quatro consumidores de `messages` leem a nota como "
          "fala da corretora ao cliente")

    certo(re.search(r"content:\s*text\s*,", codigo) is None,
          "o `content` NAO e mais o texto cru incondicional",
          "era assim que a nota entrava indistinguivel")

    certo("nota_interna" in codigo,
          "`payload.nota_interna` continua la",
          "ele e a versao legivel por maquina, para o filtro da P-265")

    # ------------------------------------------------------------------
    print("\n[2] A ROTA CONTINUA SENDO UMA ROTA DO NEXT.JS")
    # 🔴 Exportar constante arbitraria de um arquivo de rota derruba o `tsc`
    #    E o `next build`. E a familia do defeito que deixou o produto 1h40 no
    #    chao em 02/08 (CLAUDE.md §9.1). Aconteceu ao escrever este conserto.
    certo(re.search(r"export\s+const\s+PREFIXO_DA_NOTA", codigo) is None,
          "o prefixo NAO e exportado",
          "TS2344: rota do Next.js so aceita os exports do framework")

    # ------------------------------------------------------------------
    print("\n[3] LINHA DE CONTROLE -- o cortador de prosa corta?")
    # Sem isto, [1] leria o comentario que EXPLICA o defeito e passaria com o
    # codigo de volta ao errado.
    certo(len(codigo) < len(bruto), "o cortador tirou alguma coisa")
    # ⚠️ A isca cabe numa LINHA de propósito: o comentário do fonte quebra em
    #    várias, cada uma com o `//` na frente, então uma frase longa nunca
    #    casa. A primeira versão deste controle escolheu uma que atravessava a
    #    quebra — e acusou o fonte de não ter o que ele tem.
    isca = "nota vira, no histórico, uma fala da"
    certo(isca in bruto, "a frase-isca esta no fonte",
          "troque a isca deste controle")
    certo(isca not in codigo,
          "e o cortador REMOVE a prosa",
          "se ele nao corta, o teste [1] le comentario em vez de codigo")
    certo("PREFIXO_DA_NOTA" in codigo,
          "e nao corta demais -- o codigo real sobrevive")

    print("\n  %d ok, %d falhas" % (OK, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
