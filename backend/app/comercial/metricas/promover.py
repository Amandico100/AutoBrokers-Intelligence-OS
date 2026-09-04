# -*- coding: utf-8 -*-
"""A promoção — SPEC-094.1 · BLOCO D. **Um CLI, e nunca uma tool.**

```
python -m app.comercial.metricas.promover <run_id> <metric_id> --company <id>
```

🔴 **Isto é um comando de gente, e a ausência do equivalente para o modelo é a
peça inteira.** Modelado no MCP do Cube (ref ①), que *"deliberately exposes no
commit tool"*. Se houvesse uma tool `promover`, ela seria chamada — 📊 BIRD mede
o melhor sistema em 82,28% contra 92,96% do humano, uma resposta em cinco
errada, e pelo CLAUDE.md §9.5 a errada é a silenciosa. Uma métrica promovida por
engano não trava nada: ela responde, e responde para sempre.

## A ordem, e por que a conferência vem antes do UPDATE

```
1  a métrica EXISTE em registry.todas()?   senão REPROVA e nada é escrito
2  o run existe, é desta corretora e é `metric.proposal`?
3  work_events  metric.promovida  (actor_type='admin')
4  o run vai para `succeeded`
```

⚠️ O passo 1 é o ponto do comando. Promover um `metric_id` que ninguém
registrou fecharia a proposta afirmando que a métrica passou a existir — e o
próximo leitor do painel acreditaria. O run ficaria verde sobre o nada.

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
    alvo = str(metric_id or "").strip()
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
    return linha


def promover(db: Any, *, company_id: str, run_id: str,
             metric_id: str) -> Dict[str, Any]:
    """Grava `metric.promovida` e fecha o run. Devolve o que foi escrito.

    ⚠️ Idempotente por natureza: rodar duas vezes grava dois eventos e deixa o
    run no mesmo estado. Dois eventos na linha do tempo é ruído honesto; um
    segundo UPDATE não muda nada.
    """
    empresa = str(company_id or "").strip()
    if not empresa:
        raise Reprovado("REPROVADO: sem `company_id` (CLAUDE.md §7)")
    ref = conferir_a_metrica(metric_id)
    linha = conferir_o_run(db, empresa, str(run_id))
    proposta = dict(linha.get("input_payload") or {})

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
            "promovida_em": agora,
        },
    }
    db.table("work_events").insert(evento).execute()
    db.table("work_runs").update(
        {"status": STATUS_FINAL, "finished_at": agora}
    ).eq("id", str(run_id)).eq("company_id", empresa).execute()
    return {"run_id": str(run_id), "metric_id": str(metric_id), "ref": ref,
            "status": STATUS_FINAL, "evento": EVENTO_PROMOVIDA}


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
    return p.parse_args(argv)


def main(argv: Optional[list] = None) -> int:
    args = _argumentos(argv)
    try:
        from app.core.database import get_supabase_client

        cliente = get_supabase_client()
        db = getattr(cliente, "client", cliente)
        saida = promover(db, company_id=args.company_id, run_id=args.run_id,
                         metric_id=args.metric_id)
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
