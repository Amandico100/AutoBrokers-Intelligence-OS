# -*- coding: utf-8 -*-
"""Liga os acionamentos já existentes à conversa que os gerou — SPEC-090 A.

```
APPLY     para cada `work_run` de acionamento sem `conversation_id`, extrai o
          telefone do `input_payload.case_id` e procura a conversa daquela
          corretora com aquele telefone. Grava SÓ quando há EXATAMENTE UMA.
VERIFY    o SQL no fim deste arquivo.
ROLLBACK  `update work_runs set conversation_id = null where ...` — ver o fim.
```

## 🔴 A REGRA QUE TORNA ESTE BACKFILL HONESTO

⛔ **O que não casar com certeza fica NULO.** Um `conversation_id` errado é pior
que nenhum: ele produz relatório confiante e falso, e ninguém revisa um número
que parece certo.

A evidência é a que a SPEC manda — **telefone + janela de tempo + corretora** —
e a janela é um FILTRO QUE PODE RECUSAR, nunca um critério de desempate:

```
candidatas ..... conversas DAQUELA corretora com AQUELE telefone
vivas .......... as que existiam quando o run nasceu:
                     created_at <= run.created_at <= last_message_at
exatamente 1 viva  →  liga
0 ou 2+ vivas      →  🔴 NULO
```

⚠️ **A janela não é enfeite, e eu tinha errado ao achar que era.** 📊 Medido em
26/08: os 4 acionamentos existentes casam DOIS candidatos cada — o mesmo
telefone tem a conversa do agente interno (04/07 a 15/07) e a do Espelho (17/08
a 20/08). Só pelo telefone, os quatro são ambíguos e ficam nulos. Com a janela,
**os quatro resolvem, e resolvem limpo**: a conversa de julho estava morta havia
um mês quando o run nasceu.

🔴 **E "a mais recente" seria a resposta errada disfarçada de certa.** Ela sempre
devolve alguém — inclusive quando as duas conversas estão vivas ao mesmo tempo,
que é exatamente o caso em que ninguém sabe a resposta. 📊 Medido: **2 pares
(corretora, telefone) têm mais de uma conversa, e o pior caso tem 57.**

## 📊 O TAMANHO REAL DESTE BACKFILL, medido em 26/08/2026

```
work_runs .......................... 2.778
  `acionamento.seguradora` .........     4    🔴 o alvo INTEIRO
  jobs de inteligência ............. 2.774    não nascem de conversa nenhuma
```

⚠️ **A SPEC orça este backfill como o trabalho que domina as ~4h do bloco.**
Ele tem quatro linhas. O valor da coluna é o FUTURO — todo acionamento a partir
do piloto nasce sabendo de onde veio, gravado no ato por `dispatch_router`.

⛔ **E não há backfill de transcript aqui, de propósito.** A SPEC afirma que
`attendance_transcripts` não casa com nada. 📊 Medido: `session_id` casa
`attendance_sessions` em 95 de 95 (100%), e `(company_id, counterparty)` casa
`conversations` por `(company_id, user_phone)` em 63 de 63 (100%). A ponte que
a SPEC diz faltar já existe; construir outra seria motor paralelo (§5).

## ⛔ Idempotente

Só toca em linhas com `conversation_id IS NULL`. Rodar duas vezes não muda nada
na segunda — e o relatório mostra os dois números.

Uso::

    python backend/scripts/backfill_spec090_work_runs_conversation.py --dry-run
    python backend/scripts/backfill_spec090_work_runs_conversation.py --aplicar
"""
from __future__ import annotations

import argparse
import os

import sys
from collections import Counter

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

# 🔴 A REGRA MORA NO PRODUTO, NÃO NESTE SCRIPT.
#
# ⚠️ Escrever a decisão aqui criaria uma SEGUNDA regra de junção ao lado da que
# o produto usa — e duas regras que precisam concordar divergem, sendo que a
# esquecida é justamente a que liga o run à conversa errada (`CLAUDE.md` §5).
# É a mesma lição do backfill da SPEC-087, que divergiu do escritor e corrompeu
# uma linha de produção (P-262).
#
# ⚠️ **Carregado por CAMINHO, não por `import app.services…`** — `app/services/
# __init__.py` arrasta `ingestion_service` → `fastembed`, que não existe em toda
# máquina onde um backfill precisa rodar. O módulo em si não depende de nada.
import importlib.util  # noqa: E402


def _carregar(rel: str, nome: str):
    caminho = os.path.join(RAIZ, rel)
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_JUNCAO = _carregar("app/services/o_dia_de_ontem.py", "_o_dia_de_ontem_backfill")
SEM_TELEFONE = _JUNCAO.SEM_TELEFONE
WORKFLOWS_COM_CONVERSA = _JUNCAO.WORKFLOWS_COM_CONVERSA
decidir_conversa_do_run = _JUNCAO.decidir_conversa_do_run
telefone_do_caso = _JUNCAO.telefone_do_caso


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--aplicar", action="store_true", help="grava. Sem isto, só mede.")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    aplicar = bool(a.aplicar) and not a.dry_run

    from app.core.database import get_supabase_client

    db = get_supabase_client().client

    runs = (db.table("work_runs")
            .select("id, company_id, source_id, input_payload, conversation_id, created_at")
            .in_("workflow_key", list(WORKFLOWS_COM_CONVERSA))
            .is_("conversation_id", "null")
            .limit(5000).execute().data or [])

    print(f"📊 runs de acionamento SEM ligação ..... {len(runs)}")
    print()

    motivo = Counter()
    ligadas = 0
    for r in runs:
        empresa = str(r.get("company_id") or "")
        entrada = r.get("input_payload") or {}
        caso = (entrada.get("case_id") if isinstance(entrada, dict) else "") or r.get("source_id")
        tel = telefone_do_caso(caso)
        curto = str(r["id"])[:8]

        if not tel:
            motivo[SEM_TELEFONE] += 1
            print(f"   NULO    {curto}…  {SEM_TELEFONE}")
            continue

        # 🔴 O FILTRO POR CORRETORA É O QUE PROTEGE (CLAUDE.md §7). A FK
        #    composta pega o que escapar daqui — ela é a segunda linha, não a
        #    primeira.
        convs = (db.table("conversations").select("id, created_at, last_message_at")
                 .eq("company_id", empresa).eq("user_phone", tel)
                 .limit(50).execute().data or [])

        escolhida, porque = decidir_conversa_do_run(convs, str(r.get("created_at") or ""))
        if not escolhida:
            motivo[porque] += 1
            # ⛔ NUNCA imprime o telefone.
            print(f"   NULO    {curto}…  {porque}  ({len(convs)} candidatas)")
            continue

        ligadas += 1
        print(f"   {'LIGA   ' if aplicar else 'LIGARIA'} {curto}…  → conversa {escolhida[:8]}…"
              f"  ({len(convs)} candidatas, 1 viva na hora do run)")
        if aplicar:
            (db.table("work_runs").update({"conversation_id": escolhida})
             .eq("id", r["id"]).eq("company_id", empresa).execute())

    print()
    print(f"📊 {'ligadas' if aplicar else 'ligariam'} ................... {ligadas} de {len(runs)}")
    print(f"📊 🔴 FICARAM NULAS ................ {len(runs) - ligadas}")
    for k, v in motivo.most_common():
        print(f"      {k:<32} {v}")
    if len(runs) and ligadas == len(runs):
        print()
        print("⚠️ 100% ligado. A SPEC avisa que este é o número SUSPEITO, não o bom —")
        print("   confira uma amostra à mão antes de acreditar.")
    if not aplicar:
        print()
        print("⚠️ DRY-RUN. Nada foi gravado. Use `--aplicar`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# =============================================================================
# VERIFY (read-only, rodar DEPOIS)
# =============================================================================
# select workflow_key,
#        count(*) total,
#        count(conversation_id) ligados,
#        count(*) - count(conversation_id) nulos
#   from work_runs
#  group by 1 order by 2 desc;
#
# -- 🔴 dois tenants: nenhum run aponta para conversa de OUTRA corretora.
# --    (a FK composta já impede; isto prova que ela está valendo)
# select count(*) as cross_tenant
#   from work_runs r join conversations c on c.id = r.conversation_id
#  where r.company_id <> c.company_id;
# -- esperado: 0
#
# =============================================================================
# ROLLBACK
# =============================================================================
# update work_runs set conversation_id = null
#  where workflow_key = 'acionamento.seguradora';
# -- ⚠️ Apaga TAMBÉM as ligações gravadas no ato por acionamentos novos.
