"""SPEC-019 D - Robustez do executor de rotinas (timeout + retencao de runs).

Rodar: python backend/tests/test_spec019_executor.py
So nucleo puro: resolve_routine_timeout, retention_cutoff_iso, should_run_retention.
"""

import importlib.util
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASS = 0
FAIL = 0
FAILURES = []


def check(name, cond, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [ok] {name}")
    else:
        FAIL += 1
        FAILURES.append((name, detail))
        print(f"  [X] {name}{': ' + str(detail) if detail else ''}")


for name in ("app", "app.services"):
    m = sys.modules.setdefault(name, types.ModuleType(name))
    m.__path__ = []

spec = importlib.util.spec_from_file_location("app.services.routine_engine", ROOT / "app/services/routine_engine.py")
eng = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eng)


def run():
    print("== SPEC-019 D - Robustez do executor ==\n")

    # resolve_routine_timeout: default, env, piso, teto, invalido
    check("timeout default 180", eng.resolve_routine_timeout(None) == 180)
    check("timeout do env 240", eng.resolve_routine_timeout("240") == 240)
    check("timeout piso 30", eng.resolve_routine_timeout("5") == 30)
    check("timeout teto 600", eng.resolve_routine_timeout("9999") == 600)
    check("timeout invalido -> default", eng.resolve_routine_timeout("abc") == 180)

    # retention_cutoff_iso: now - 90 dias
    now = datetime(2026, 7, 6, 12, 0, tzinfo=timezone.utc)
    cutoff = eng.retention_cutoff_iso(now, 90)
    check("cutoff 90d = 2026-04-07", cutoff.startswith("2026-04-07"), cutoff)

    # should_run_retention: primeira vez, recente, antigo
    check("retention roda se nunca rodou", eng.should_run_retention(None, now) is True)
    check("retention NAO roda se rodou ha 1h", eng.should_run_retention(now - timedelta(hours=1), now) is False)
    check("retention roda se rodou ha 25h", eng.should_run_retention(now - timedelta(hours=25), now) is True)

    # SPEC-019 E — render_task_prompt injeta CONHECIMENTO DA ROTINA quando presente
    with_k = eng.render_task_prompt({"name": "R", "instructions": "faca X", "knowledge": "argumentos: A, B"})
    check("knowledge presente -> bloco CONHECIMENTO", "CONHECIMENTO DA ROTINA" in with_k)
    check("knowledge antes das instrucoes", with_k.index("CONHECIMENTO DA ROTINA") < with_k.index("INSTRU"))
    no_k = eng.render_task_prompt({"name": "R", "instructions": "faca X"})
    check("sem knowledge -> sem bloco", "CONHECIMENTO DA ROTINA" not in no_k)
    empty_k = eng.render_task_prompt({"name": "R", "instructions": "faca X", "knowledge": "   "})
    check("knowledge vazio -> sem bloco", "CONHECIMENTO DA ROTINA" not in empty_k)

    print(f"\n== {PASS} ok / {FAIL} fail ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  FALHOU: {n} ({d})")
    return FAIL == 0


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
