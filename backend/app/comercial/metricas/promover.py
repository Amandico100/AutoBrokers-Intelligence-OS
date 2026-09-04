# -*- coding: utf-8 -*-
"""A promoção — SPEC-094.1 · BLOCO D. **Um CLI, e nunca uma tool.**

```
python -m app.comercial.metricas.promover <run_id> <metric_id> --company <id> \
       [--substitui "<motivo de o nome ter mudado>"]
```

🔴 **Isto é um comando de gente, e a ausência do equivalente para o modelo é a
peça inteira.** Modelado no MCP do Cube (ref ①), que *"deliberately exposes no
commit tool"*. Se houvesse uma tool `promover`, ela seria chamada — 📊 BIRD mede
o melhor sistema em 82,28% contra 92,96% do humano, uma resposta em cinco
errada, e pelo CLAUDE.md §9.5 a errada é a silenciosa. Uma métrica promovida por
engano não trava nada: ela responde, e responde para sempre.

## A ordem, e por que a conferência vem antes do UPDATE

```
1  a métrica EXISTE em registry.todas()?        senão REPROVA e nada é escrito
2  o run existe, é desta corretora e é `metric.proposal`?
3  o run ainda está VIVO?                        cancelled/failed/completed REPROVA
4  a decisão humana foi APPROVED?                rejected/pendente/ausente REPROVA
5  o `metric_id` é o da proposta?                senão exige `--substitui <motivo>`
6  work_events  metric.promovida  (actor_type='admin')
7  o run vai para `succeeded`
```

⚠️ O passo 1 é o ponto do comando. Promover um `metric_id` que ninguém
registrou fecharia a proposta afirmando que a métrica passou a existir — e o
próximo leitor do painel acreditaria. O run ficaria verde sobre o nada.

## 🔴 Os três buracos que o conserto de 04/09/2026 fechou

📊 Medidos na rodada única de conserto da SPEC-094.1:

```
o run RECUSADO era promovido    o comando lia `workflow_key` e nada mais. Uma
                                proposta que um humano REJEITOU virava
                                `succeeded`, com evento de promoção na linha do
                                tempo — o painel passava a dizer que a métrica
                                foi aprovada.
a DECISÃO nunca era lida        `approval_requests` existia, com dono e prazo, e
                                este comando não a consultava. O HITL inteiro
                                era decorativo: o gate estava lá e ninguém
                                perguntava por ele (SPEC-053 §11.1).
o `metric_id` podia ser OUTRO   nada comparava o id promovido com o
                                `nome_sugerido` da proposta. Aprovava-se uma
                                métrica e promovia-se outra, sem uma linha
                                dizendo que houve troca.
```

🔴 E promover DUAS VEZES parou de ser "ruído honesto": o run já está
`succeeded`, o passo 3 reprova, e a segunda promoção não escreve nada. Dois
eventos de promoção para a mesma proposta é como uma linha do tempo deixa de
ser lida.

⛔ Este módulo **não** cria métrica, não escreve em `metricas/` e não aprova a
`approval_request`: a decisão humana é a `decidir()` da SPEC-055, pela API admin
(`POST /work-runs/approvals/{id}/decide`). Este comando registra que a
definição, já commitada por gente, entrou em vigor.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

WORKFLOW_KEY = "metric.proposal"
EVENTO_PROMOVIDA = "metric.promovida"
#: 🔴 `admin`, e não `agent`: quem promove é uma pessoa com acesso ao
#: repositório. 📊 O CHECK `ck_work_events_actor` aceita
#: system|worker|user|agent|admin|provider.
ATOR = "admin"
#: O status final do vocabulário existente de `work_runs`.
STATUS_FINAL = "succeeded"

#: 🔴 Os status TERMINAIS. Um run que chegou a qualquer um deles não pode ser
#: promovido: a proposta acabou, de um jeito ou de outro, e reabri-la por um
#: comando de linha faria o painel contar duas vezes a mesma decisão.
#:
#: ⚠️ `succeeded` está na lista, e é ela que torna a SEGUNDA promoção
#: impossível — antes de 04/09/2026 o módulo declarava isso como "idempotente
#: por natureza", que é outro nome para "escreve dois eventos".
STATUS_TERMINAIS = ("cancelled", "failed", "completed", "expired", "succeeded")

#: A decisão humana que autoriza a promoção. 📊 `WorkApprovalService.decidir`
#: grava `decision` em `approved` / `approved_with_edit` / `rejected`, e
#: `status` em `approved` / `rejected` / `expired`.
DECISOES_QUE_APROVAM = ("approved", "approved_with_edit")


class Reprovado(RuntimeError):
    """A promoção não pode acontecer. 🔴 Nada foi escrito."""


def conferir_a_metrica(metric_id: str) -> str:
    """O `metric_id@versão` da métrica registrada. REPROVA se ela não existir.

    🔴 A pergunta é feita ao REGISTRY vivo (`registry.todas()`), e não a uma
    lista de nomes escrita neste arquivo. Uma cópia da lista divergiria da
    verdadeira no primeiro `git pull` — e o comando passaria a aprovar métricas
    que só existiam no seu próprio texto (CLAUDE.md §9.4: o teste chama o
    MOTOR).
    """
    from app.comercial.metricas import registry

    catalogo = registry.todas()
    # 🔴 `strip().lower()`, e a normalizacao mora AQUI porque esta e a primeira
    # porta. 📊 Um espaco a direita ou uma maiuscula faziam a comparacao com o
    # registry falhar, e a promocao reprovava uma metrica que existe.
    alvo = str(metric_id or "").strip().lower()
    if alvo not in catalogo:
        parecidas = sorted(m for m in catalogo
                           if alvo and alvo.split(".")[0] in m)
        raise Reprovado(
            "REPROVADO: %r não está em registry.todas() (%d métricas "
            "registradas). Promover um id que ninguém definiu fecharia a "
            "proposta afirmando que a métrica existe.%s" % (
                alvo, len(catalogo),
                (" Você quis dizer: %s?" % ", ".join(parecidas)) if parecidas
                else " Registre a definição primeiro — "
                     "docs/canon/COMO-NASCE-UM-RELATORIO.md."))
    return catalogo[alvo].ref


def conferir_o_run(db: Any, company_id: str, run_id: str) -> Dict[str, Any]:
    """A linha do run, se ela existir, for desta corretora e for uma proposta.

    🔴 O filtro por `company_id` está no CÓDIGO, e não só na RLS: o backend roda
    com service role (CLAUDE.md §7). Sem ele, um `run_id` de outra corretora
    seria promovido pelo operador da primeira, e o evento entraria na linha do
    tempo da casa errada.
    """
    try:
        r = (db.table("work_runs")
             .select("id, company_id, workflow_key, status, input_payload")
             .eq("id", run_id).eq("company_id", company_id)
             .limit(1).execute())
        linhas = getattr(r, "data", None) or []
    except Exception as exc:  # noqa: BLE001
        raise Reprovado("REPROVADO: não foi possível ler o run (%s)"
                        % type(exc).__name__) from exc
    if not linhas:
        raise Reprovado(
            "REPROVADO: run %r não existe para a corretora %r" % (run_id,
                                                                 company_id))
    linha = linhas[0]
    if str(linha.get("workflow_key") or "") != WORKFLOW_KEY:
        raise Reprovado(
            "REPROVADO: run %r é %r, e não uma proposta de métrica (%s)"
            % (run_id, linha.get("workflow_key"), WORKFLOW_KEY))
    estado = str(linha.get("status") or "").strip().lower()
    if estado in STATUS_TERMINAIS:
        raise Reprovado(
            "REPROVADO: o run %r já está em %r, que é um estado TERMINAL. A "
            "proposta acabou — promovê-la agora escreveria um segundo evento "
            "de promoção sobre uma decisão que já foi tomada." % (run_id, estado))
    return linha


def conferir_a_decisao(db: Any, company_id: str, run_id: str) -> Dict[str, Any]:
    """A `approval_request` APROVADA deste run. REPROVA se não houver uma.

    🔴 É esta função que faz o gate do HITL existir de verdade. 📊 Até
    04/09/2026 este comando nunca lia `approval_requests`: a linha era criada,
    um humano decidia, e a promoção acontecia do mesmo jeito — inclusive sobre
    uma proposta **rejeitada**. Um gate que ninguém consulta é um gate que não
    está lá (SPEC-053 §11.1: *"prompt não é gate"*).

    ⚠️ Ausência de linha também REPROVA: "ninguém decidiu" não é "decidiu que
    sim". A promoção é o momento em que a decisão humana vira efeito.
    """
    try:
        r = (db.table("approval_requests")
             .select("id, company_id, work_run_id, status, decision, "
                     "decided_at, subject_id")
             .eq("work_run_id", run_id).eq("company_id", company_id)
             .execute())
        linhas = getattr(r, "data", None) or []
    except Exception as exc:  # noqa: BLE001
        raise Reprovado("REPROVADO: não foi possível ler a aprovação (%s)"
                        % type(exc).__name__) from exc
    if not linhas:
        raise Reprovado(
            "REPROVADO: o run %r não tem aprovação registrada. Uma proposta "
            "sem decisão humana não é uma proposta aprovada — ninguém a olhou."
            % run_id)
    aprovadas = [x for x in linhas
                 if str(x.get("decision") or "").strip().lower()
                 in DECISOES_QUE_APROVAM]
    if not aprovadas:
        decisoes = sorted({str(x.get("decision") or x.get("status") or "pendente")
                           for x in linhas})
        raise Reprovado(
            "REPROVADO: a decisão humana sobre o run %r é %s, e não uma "
            "aprovação. ⛔ Promover uma proposta RECUSADA fecharia o run como "
            "sucesso e poria a métrica na linha do tempo como aprovada."
            % (run_id, ", ".join(decisoes)))
    return aprovadas[0]


def conferir_o_nome(metric_id: str, proposta: Dict[str, Any],
                    substitui: str = "") -> str:
    """O `metric_id` normalizado. REPROVA se ele não for o da proposta.

    🔴 `strip().lower()`: 📊 um espaço à direita ou uma maiúscula fariam a
    comparação falhar contra o registry e contra a proposta — e a mesma métrica
    entraria duas vezes com nomes que só um `diff` distingue.

    ⚠️ Promover um id DIFERENTE do proposto é legítimo (a revisão pode ter
    escolhido um nome melhor), e por isso existe `--substitui`: o que não pode
    é acontecer **calado**. O motivo vai escrito no evento, e é ele que o
    próximo leitor do painel encontra quando perguntar por que o nome mudou.
    """
    alvo = str(metric_id or "").strip().lower()
    proposto = str((proposta or {}).get("nome_sugerido") or "").strip().lower()
    if not proposto or alvo == proposto:
        return alvo
    if not str(substitui or "").strip():
        raise Reprovado(
            "REPROVADO: a proposta pediu %r e você está promovendo %r. Se a "
            "revisão escolheu outro nome, escreva por quê: "
            "`--substitui \"<motivo>\"`. ⛔ Trocar o nome em silêncio deixa o "
            "painel afirmando que foi aprovado o que não foi."
            % (proposto, alvo))
    return alvo


def promover(db: Any, *, company_id: str, run_id: str,
             metric_id: str, substitui: str = "") -> Dict[str, Any]:
    """Grava `metric.promovida` e fecha o run. Devolve o que foi escrito.

    🔴 **Não é idempotente, e é de propósito.** O passo 3 reprova um run que já
    está `succeeded`: uma segunda promoção da mesma proposta não escreve nada.
    Até 04/09/2026 este módulo chamava isso de "ruído honesto" — dois eventos
    de promoção na linha do tempo da mesma proposta é como um painel deixa de
    ser lido.
    """
    empresa = str(company_id or "").strip()
    if not empresa:
        raise Reprovado("REPROVADO: sem `company_id` (CLAUDE.md §7)")
    ref = conferir_a_metrica(metric_id)
    linha = conferir_o_run(db, empresa, str(run_id))
    proposta = dict(linha.get("input_payload") or {})
    decisao = conferir_a_decisao(db, empresa, str(run_id))
    metric_id = conferir_o_nome(metric_id, proposta, substitui)

    agora = datetime.now(timezone.utc).isoformat()
    evento = {
        "company_id": empresa,
        "work_run_id": str(run_id),
        "event_type": EVENTO_PROMOVIDA,
        "actor_type": ATOR,
        "severity": "info",
        "message_human": "Métrica promovida: %s" % ref,
        # ⛔ Enums e ids. O `nome_sugerido` da proposta e o `metric_id` que
        # entrou em vigor — nada de texto livre e nada de pessoa.
        "payload_redacted": {
            "metric_id": str(metric_id), "ref": ref,
            "nome_sugerido": str(proposta.get("nome_sugerido") or ""),
            "approval_id": str(decisao.get("id") or ""),
            "decision": str(decisao.get("decision") or ""),
            # ⛔ O motivo da troca de nome é a ÚNICA frase livre deste payload,
            # e ela é escrita por gente no terminal — nunca por um modelo.
            "substitui": str(substitui or "")[:300],
            "promovida_em": agora,
        },
    }
    db.table("work_events").insert(evento).execute()
    db.table("work_runs").update(
        {"status": STATUS_FINAL, "finished_at": agora}
    ).eq("id", str(run_id)).eq("company_id", empresa).execute()
    return {"run_id": str(run_id), "metric_id": str(metric_id), "ref": ref,
            "status": STATUS_FINAL, "evento": EVENTO_PROMOVIDA,
            "approval_id": str(decisao.get("id") or ""),
            "substitui": str(substitui or "")}


# --------------------------------------------------------------------------
def _argumentos(argv: Optional[list] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python -m app.comercial.metricas.promover",
        description="Promove uma proposta de métrica DEPOIS de a definição "
                    "estar registrada e commitada (SPEC-094.1 BLOCO D).")
    p.add_argument("run_id", help="o `work_run` da proposta")
    p.add_argument("metric_id", help="o metric_id que passou a existir")
    p.add_argument("--company", required=True, dest="company_id",
                   help="a corretora dona da proposta (obrigatório)")
    p.add_argument("--substitui", default="", dest="substitui",
                   help="o MOTIVO de promover um metric_id diferente do "
                        "`nome_sugerido` da proposta. Sem ele, o comando "
                        "reprova a troca de nome — ela é legítima, mas nunca "
                        "silenciosa")
    return p.parse_args(argv)


def main(argv: Optional[list] = None) -> int:
    args = _argumentos(argv)
    try:
        from app.core.database import get_supabase_client

        cliente = get_supabase_client()
        db = getattr(cliente, "client", cliente)
        saida = promover(db, company_id=args.company_id, run_id=args.run_id,
                         metric_id=args.metric_id, substitui=args.substitui)
    except Reprovado as exc:
        print(str(exc))
        return 2
    except Exception as exc:  # noqa: BLE001
        print("FALHOU: %s: %s" % (type(exc).__name__, exc))
        return 1
    print("PROMOVIDA " + json.dumps(saida, ensure_ascii=False))
    return 0


if __name__ == "__main__":   # pragma: no cover
    sys.exit(main())
