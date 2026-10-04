# -*- coding: utf-8 -*-
"""O canário da espera durável (SPEC-129-A, G11) — pela linha de comando.

Prova, NO AR, depois do Implantar, que o motor de trabalhos dorme, acorda sozinho e não repete
nada quando o processador reinicia no meio. Usa o trabalho de teste `system.espera_de_teste`
(registrado em `app/services/work/workflows.py`): uma verificação (`ping`), um sono de N minutos,
o despertar pelo relógio, a conclusão.

⛔ NUNCA envia mensagem. NUNCA toca portal. NUNCA mexe em dado de segurado ou de corretor:
   escreve UMA linha em `work_runs` (+ a outbox, pela mesma RPC de sempre), e o resto é o motor.

```
(sem nada) / --criar          --dry-run (PADRÃO): lê o banco, mostra o PLANO, não grava nada
--criar --de-verdade          cria o trabalho de teste e imprime o comando de conferir
--conferir <id>               só leitura: o que aconteceu, em linguagem simples
--minutos N                   duração do sono (1–60, padrão 10)
--empresa <uuid>              opcional: força a corretora (senão vem do BANCO)
```

A corretora vem do BANCO (CLAUDE.md §13.9): a dona do trabalho de fila (`runtime_kind='smith'`)
concluído mais recente — é onde o motor está vivo. Nenhum nome de corretora aqui dentro.

O roteiro do G11 (o Founder ou o gerente, no contêiner `backend`):
```
python scripts/canario_espera_duravel.py --criar                 # o plano (nada gravado)
python scripts/canario_espera_duravel.py --criar --de-verdade    # cria; anote o id
#   ~3 min depois: reinicie o serviço `smith-worker` no EasyPanel (o trabalho está dormindo)
python scripts/canario_espera_duravel.py --conferir <id>         # depois de ~12 min
```
"""
from __future__ import annotations

import argparse
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

WORKFLOW = "system.espera_de_teste"
TERMINAIS = ("completed", "failed", "cancelled", "expired")


# ─────────────────────────────────────────────────────────────────────────────
# leituras (recebem o cliente PostgREST: o real, ou o dublê do teste)
# ─────────────────────────────────────────────────────────────────────────────
def _linhas(res: Any) -> list[dict]:
    dados = getattr(res, "data", None) if res is not None else None
    if isinstance(dados, list):
        return dados
    return [dados] if isinstance(dados, dict) else []


def _com_nome(db: Any, company_id: str) -> Optional[dict]:
    """`{"id", "company_name"}` — o nome só para a tela; sem ele, segue pelo id."""
    linha = _linhas(db.table("companies").select("id").eq("id", company_id).limit(1).execute())
    if not linha:
        return None
    try:
        nome = _linhas(db.table("companies").select("company_name").eq("id", company_id).limit(1).execute())
        linha[0]["company_name"] = (nome[0] if nome else {}).get("company_name")
    except Exception:  # noqa: BLE001
        pass
    return linha[0]


def escolher_empresa(db: Any, forcada: Optional[str] = None) -> Optional[dict]:
    """A corretora do canário, pelo BANCO. `None` = nenhuma serve."""
    if forcada:
        return _com_nome(db, forcada)
    ultimo = _linhas(db.table("work_runs").select("company_id")
                     .eq("runtime_kind", "smith").eq("status", "completed")
                     .order("finished_at", desc=True).limit(1).execute())
    if ultimo:
        alvo = _com_nome(db, str(ultimo[0]["company_id"]))
        if alvo:
            return alvo
    linha = _linhas(db.table("companies").select("id").order("created_at").limit(1).execute())
    return _com_nome(db, str(linha[0]["id"])) if linha else None


def migration_aplicada(db: Any) -> bool:
    """A `_02` (wake_at, wait_for) está no banco? Sem ela o trabalho dormiria sem relógio."""
    try:
        db.table("work_runs").select("id, wake_at, wait_for").limit(1).execute()
        return True
    except Exception:  # noqa: BLE001
        return False


def workflow_registrado() -> Optional[bool]:
    """O código deste contêiner conhece o trabalho de teste? `None` = não deu para conferir."""
    try:
        from app.services.work import workflows as W

        return WORKFLOW in W._REGISTRO
    except Exception:  # noqa: BLE001
        return None


def canarios_abertos(db: Any, company_id: str) -> list[dict]:
    return [r for r in _linhas(db.table("work_runs").select("id, status, requested_at")
                               .eq("company_id", company_id).eq("workflow_key", WORKFLOW)
                               .order("requested_at", desc=True).limit(20).execute())
            if r.get("status") not in TERMINAIS]


# ─────────────────────────────────────────────────────────────────────────────
# os três modos
# ─────────────────────────────────────────────────────────────────────────────
def plano(db: Any, *, minutos: int, empresa: Optional[str] = None) -> tuple[list[str], Optional[dict]]:
    """--dry-run: o que `--de-verdade` faria, e se pode fazer. Só leitura."""
    out = ["O CANÁRIO DA ESPERA DURÁVEL — plano (nada foi gravado)", ""]
    alvo = escolher_empresa(db, empresa)
    if not alvo:
        out.append("✗ Nenhuma corretora encontrada no banco. Nada a fazer.")
        return out, None
    out.append(f"Corretora (escolhida pelo banco): {alvo.get('company_name') or '—'} · id {str(alvo['id'])[:8]}…")
    mig = migration_aplicada(db)
    out.append(("✓" if mig else "✗") + " Migration da espera (wake_at/wait_for) "
               + ("está no banco." if mig else "NÃO está no banco — aplique a 20261004_02 antes."))
    reg = workflow_registrado()
    out.append({True: "✓ O código deste contêiner conhece o trabalho de teste.",
                False: "✗ O código deste contêiner NÃO conhece o trabalho de teste — falta o Implantar.",
                None: "? Não consegui conferir o código daqui (rode dentro do contêiner `backend`)."}[reg])
    abertos = canarios_abertos(db, str(alvo["id"]))
    if abertos:
        out.append(f"⚠ Já há {len(abertos)} canário(s) em andamento nesta corretora "
                   f"(o mais novo: {str(abertos[0]['id'])[:8]}…, {abertos[0]['status']}).")
    out += ["",
            "Com --de-verdade, eu faria:",
            f"  1. criar UM trabalho de teste ({WORKFLOW}) que dorme {minutos} min;",
            "  2. ele faz uma verificação rápida, dorme SEM segurar nenhum processo, e acorda sozinho;",
            "  3. nenhuma mensagem, nenhum portal, nenhum dado de cliente é tocado.",
            "",
            f"Para valer o teste do reinício: ~{max(1, minutos // 3)} min depois de criar, reinicie o `smith-worker`.",
            f"Depois de ~{minutos + 2} min: python scripts/canario_espera_duravel.py --conferir <id>"]
    pode = mig and reg is not False
    out.append("")
    out.append("PODE RODAR." if pode else "AINDA NÃO PODE RODAR — resolva o(s) ✗ acima.")
    return out, (alvo if pode else None)


def criar(db: Any, alvo: dict, *, minutos: int) -> tuple[list[str], Optional[str]]:
    """--de-verdade: cria o trabalho de teste pela MESMA RPC do produto (run + outbox juntos)."""
    from app.services.work.runs import WorkRunService

    agora = datetime.now(timezone.utc)
    linha = WorkRunService(db).criar(
        company_id=str(alvo["id"]), source_type="admin", outcome_type="canario",
        outcome_title=f"Canário da espera durável ({minutos} min)", workflow_key=WORKFLOW,
        idempotency_key=f"canario-129a:{agora:%Y%m%dT%H%M%S}:{uuid.uuid4().hex[:6]}",
        input_payload={"minutos": minutos, "canario": "SPEC-129-A G11"}, priority=50, risk_level="low")
    rid = str(linha.get("run_id") or linha.get("id") or "")
    if not rid:
        return ["✗ O banco não devolveu o id do trabalho. Nada mais a fazer; confira os logs."], None
    return [f"✓ Trabalho de teste criado: {rid}",
            f"  Ele dorme {minutos} min. Para o teste do reinício: reinicie o `smith-worker` em ~{max(1, minutos // 3)} min.",
            f"  Depois de ~{minutos + 2} min: python scripts/canario_espera_duravel.py --conferir {rid}"], rid


def conferir(db: Any, run_id: str) -> tuple[list[str], bool]:
    """Só leitura. `True` = passou (concluiu UMA vez, `ping` em UMA tentativa, acordou sozinho)."""
    base = _linhas(db.table("work_runs").select("id, company_id, workflow_key, status, wait_for, "
                                                "requested_at, finished_at, error_message, result_summary")
                   .eq("id", run_id).limit(1).execute())
    if not base:
        return [f"✗ Não achei o trabalho {run_id}."], False
    run = base[0]
    cid = str(run["company_id"])
    if run.get("workflow_key") != WORKFLOW:
        return [f"✗ {run_id} não é um canário ({run.get('workflow_key')}). Não confiro outro tipo."], False

    eventos = _linhas(db.table("work_events").select("event_type")
                      .eq("work_run_id", run_id).eq("company_id", cid).limit(500).execute())
    tipos = [e.get("event_type") for e in eventos]
    passos = {p.get("step_key"): p for p in _linhas(
        db.table("work_steps").select("id, step_key, status").eq("work_run_id", run_id)
        .eq("company_id", cid).execute())}
    ping = passos.get("ping") or {}
    tentativas_ping = len(_linhas(db.table("work_attempts").select("id").eq("work_step_id", ping["id"])
                                  .eq("company_id", cid).execute())) if ping.get("id") else 0
    espera = run.get("wait_for") if isinstance(run.get("wait_for"), dict) else {}
    concluiu = tipos.count("run.succeeded")
    acordou = int(espera.get("acordou") or 0)
    recuperado = tipos.count("worker.recovered") + tipos.count("run.redriven")

    out = [f"O CANÁRIO {run_id[:8]}… — status: {run.get('status')}", ""]
    if run.get("status") not in TERMINAIS:
        out.append("… Ainda em andamento" + (f" (dormindo; já acordou {acordou}×)." if acordou or espera
                                             else "."))
        out.append("  Rode de novo em alguns minutos.")
        return out, False
    out.append(("✓" if concluiu == 1 else "✗") + f" Concluiu {concluiu} vez(es) — o certo é 1.")
    out.append(("✓" if tentativas_ping == 1 else "✗")
               + f" A verificação inicial rodou {tentativas_ping} vez(es) — o certo é 1 (reinício não repete).")
    out.append(("✓" if acordou >= 1 else "✗") + f" Acordou sozinho {acordou} vez(es) pelo relógio.")
    if recuperado:
        out.append(f"ℹ O motor retomou o trabalho {recuperado}× depois de um processador parar — esperado "
                   "se você reiniciou o `smith-worker` com ele acordado.")
    if run.get("status") != "completed":
        out.append(f"✗ Terminou como '{run.get('status')}': {run.get('error_message') or '—'}")
    ok = run.get("status") == "completed" and concluiu == 1 and tentativas_ping == 1 and acordou >= 1
    out += ["", "PASSOU: o motor dorme, acorda sozinho e não repete nada." if ok
            else "NÃO PASSOU — guarde este texto e o id para a investigação."]
    return out, ok


def _banco() -> Any:
    from app.core.database import get_supabase_client

    return get_supabase_client().client


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="O canário da espera durável (SPEC-129-A G11)")
    ap.add_argument("--criar", action="store_true", help="planeja (padrão) ou cria, com --de-verdade")
    ap.add_argument("--de-verdade", action="store_true", help="grava o trabalho de teste (senão é dry-run)")
    ap.add_argument("--dry-run", action="store_true", help="só o plano — é o padrão")
    ap.add_argument("--conferir", metavar="ID", help="só leitura: o resultado de um canário")
    ap.add_argument("--minutos", type=int, default=10, help="duração do sono (1–60)")
    ap.add_argument("--empresa", metavar="UUID", help="força a corretora (senão vem do banco)")
    args = ap.parse_args(argv)
    minutos = max(1, min(60, int(args.minutos)))
    if args.de_verdade and args.dry_run:
        print("--de-verdade e --dry-run juntos: escolha um.")
        return 2

    try:
        db = _banco()
    except Exception as exc:  # noqa: BLE001
        print(f"✗ Sem acesso ao banco ({type(exc).__name__}). Rode dentro do contêiner `backend`.")
        return 2

    if args.conferir:
        if not migration_aplicada(db):
            print("✗ A migration da espera (20261004_02) não está no banco: não há canário para conferir.")
            return 1
        linhas, ok = conferir(db, args.conferir.strip())
        print("\n".join(linhas))
        return 0 if ok else 1

    linhas, alvo = plano(db, minutos=minutos, empresa=args.empresa)
    print("\n".join(linhas))
    if not args.de_verdade:
        return 0
    if alvo is None:
        return 1
    print("")
    linhas, rid = criar(db, alvo, minutos=minutos)
    print("\n".join(linhas))
    return 0 if rid else 1


if __name__ == "__main__":
    sys.exit(main())
