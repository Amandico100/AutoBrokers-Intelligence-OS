# -*- coding: utf-8 -*-
"""*"O que aconteceu ontem, o que falhou, e o que eu conserto hoje?"* — SPEC-090.

> **Terça de manhã. O Founder abre o chat e escreve: "o que aconteceu ontem?" —
> e recebe: quantos atendimentos, quantos travaram, em que telas, quem
> destravou, quanto tempo, e o que a Regina anotou.**

⛔ **É UMA LEITURA, NÃO UM MOTOR.** Nada aqui decide, agenda, envia ou grava
estado de negócio. Quem grava o travamento é `dispatch_router` (SPEC-093); quem
grava a tela cega é `tela_cega` (SPEC-087); quem grava a nota é o webhook. Este
módulo **só junta e conta** — e é por isso que ele é um arquivo só e não uma
pasta: `CLAUDE.md` §5.

Três perguntas, três blocos:

```
A  de qual conversa este acionamento nasceu?     `decidir_conversa_do_run`
B  como foi a trajetória de cada travamento?     `trajetoria_dos_travamentos`
D  o que aconteceu ontem, em números?            `o_que_aconteceu_ontem`
```

🔴 **E as três respeitam a mesma regra:** o que não dá para provar vira NULO ou
zero — nunca um palpite. Um relatório confiante e falso é pior que um vazio,
porque ninguém revisa um número que parece certo.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

# =============================================================================
# BLOCO A · a chave de junção
# =============================================================================

#: Os workflows que NASCEM de uma conversa.
#:
#: ⛔ Os jobs de inteligência não entram: 📊 medido em 26/08, **2.774 de 2.778**
#: `work_runs` são deles (`intelligence.detect_signals` e companhia), e eles não
#: nascem de conversa nenhuma. Ligá-los seria inventar uma origem.
WORKFLOWS_COM_CONVERSA: Tuple[str, ...] = ("acionamento.seguradora",)

#: `case_id` nasce como `wa-<telefone>` — 📊 medido: `source_id = 'wa-554788087…'`.
#:
#: ⚠️ **As âncoras dos dois lados não são decoração.** Sem `^` e `$`, um
#: identificador com dígitos no meio viraria "telefone" — é literalmente a P-262,
#: onde um padrão sem fronteira comeu dígitos dentro de um sha256 e corrompeu uma
#: linha de produção.
_TELEFONE_DO_CASO = re.compile(r"^wa-(\d{10,15})$", re.I)


def telefone_do_caso(case_id: Any) -> str:
    """O telefone dentro do `case_id`, ou `""` — e ele **não adivinha**."""
    m = _TELEFONE_DO_CASO.match(str(case_id or "").strip())
    return m.group(1) if m else ""


#: Os motivos pelos quais um run fica SEM conversa. Cada um é reportado
#: separadamente, porque eles pedem consertos diferentes.
SEM_TELEFONE = "sem telefone no case_id"
SEM_CONVERSA = "nenhuma conversa desta corretora com este telefone"
AMBIGUA = "AMBÍGUA: mais de uma conversa viva na hora do run"
LIGADA = "ligada"


def decidir_conversa_do_run(
    candidatas: Sequence[Dict[str, Any]],
    nascimento_do_run: str,
) -> Tuple[Optional[str], str]:
    """Qual conversa gerou este run — **ou `None`, com o motivo**.

    🔴 FUNÇÃO PURA. Recebe as candidatas já filtradas por corretora e telefone
    (o filtro do §7 é de quem chama, e a FK composta é a segunda linha), e
    devolve `(conversation_id, motivo)`.

    Ser pura é o que torna o guarda honesto: o teste roda offline, em
    microssegundos, e a mutação da regra fica **vermelha de verdade** em vez de
    depender de o banco estar de pé.

    ---------------------------------------------------------------------------
    🔴 A JANELA É UM FILTRO QUE PODE RECUSAR — NÃO UM DESEMPATE

    Uma conversa estava viva quando o run nasceu se::

        created_at <= nascimento_do_run <= last_message_at

    ✅ **Exatamente uma viva** → é ela.
    ⛔ **Zero ou duas ou mais** → `None`. Ninguém sabe, e o backfill diz isso.

    ⚠️ **"A mais recente" seria a resposta errada disfarçada de certa.** Ela
    sempre devolve alguém — inclusive quando as duas conversas estão vivas ao
    mesmo tempo, que é exatamente o caso em que a resposta não existe.

    📊 E a janela não é enfeite: medido em 26/08, os 4 acionamentos existentes
    têm DOIS candidatos cada — a conversa do agente interno (04/07 a 15/07) e a
    do Espelho (17/08 a 20/08). Só por telefone, os quatro são ambíguos e ficam
    nulos. Com a janela, **os quatro resolvem**, e a conversa de julho estava
    morta havia um mês.

    ⚠️ `last_message_at` vazio cai para `created_at`: uma conversa sem nenhuma
    mensagem viveu um instante, e um instante não cobre um run de outro dia.
    """
    nascimento = str(nascimento_do_run or "").strip()
    if not nascimento:
        # Sem a hora do run não há janela, e sem janela não há prova.
        return None, SEM_CONVERSA
    if not candidatas:
        return None, SEM_CONVERSA

    vivas: List[str] = []
    for c in candidatas:
        inicio = str(c.get("created_at") or "").strip()
        if not inicio:
            continue
        fim = str(c.get("last_message_at") or "").strip() or inicio
        # ⚠️ Comparação de texto ISO-8601 em UTC é ordenação correta — e é o
        #    formato que o PostgREST devolve. Converter para datetime aqui só
        #    acrescentaria um jeito de errar de fuso.
        if inicio <= nascimento <= fim:
            vivas.append(str(c.get("id") or ""))

    vivas = [v for v in vivas if v]
    if len(vivas) == 1:
        return vivas[0], LIGADA
    if not vivas:
        return None, SEM_CONVERSA
    return None, AMBIGUA
