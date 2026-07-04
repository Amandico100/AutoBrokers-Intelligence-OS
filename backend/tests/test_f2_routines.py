"""F2 - Motor de Rotinas (agenda pura, prompt de execucao, validacao).

Rodar: python backend/tests/test_f2_routines.py
Offline: so o nucleo puro (compute_next_run, validate_schedule, render).
"""

import importlib.util
import sys
import types
from datetime import datetime, timezone
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
    print("== F2 - Motor de Rotinas ==\n")

    # validate_schedule
    check("F2: daily valido", eng.validate_schedule({"kind": "daily", "time": "08:00"})[0] is True)
    check("F2: daily sem time invalido", eng.validate_schedule({"kind": "daily"})[0] is False)
    check("F2: daily hora impossivel invalido", eng.validate_schedule({"kind": "daily", "time": "25:00"})[0] is False)
    check("F2: weekdays fora de 0-6 invalido", eng.validate_schedule({"kind": "daily", "time": "08:00", "weekdays": [7]})[0] is False)
    check("F2: interval valido", eng.validate_schedule({"kind": "interval", "minutes": 30})[0] is True)
    check("F2: interval abaixo do minimo invalido", eng.validate_schedule({"kind": "interval", "minutes": 1})[0] is False)
    check("F2: kind desconhecido invalido", eng.validate_schedule({"kind": "cron"})[0] is False)

    # compute_next_run — 2026-07-04 é SÁBADO. 12:00 UTC = 09:00 em São Paulo.
    now = datetime(2026, 7, 4, 12, 0, tzinfo=timezone.utc)

    nxt = eng.compute_next_run({"kind": "interval", "minutes": 30}, "America/Sao_Paulo", now)
    check("F2: interval agenda +30min", (nxt - now).total_seconds() == 1800, nxt)

    # daily 10:00 local ainda hoje (agora local = 09:00)
    nxt2 = eng.compute_next_run({"kind": "daily", "time": "10:00"}, "America/Sao_Paulo", now)
    check("F2: daily ainda hoje quando horario nao passou", nxt2.astimezone(timezone.utc).hour == 13 and nxt2.date() == now.date(), nxt2)

    # daily 08:00 local ja passou -> amanha
    nxt3 = eng.compute_next_run({"kind": "daily", "time": "08:00"}, "America/Sao_Paulo", now)
    check("F2: daily pula para amanha quando ja passou", nxt3.date() == datetime(2026, 7, 5, tzinfo=timezone.utc).date(), nxt3)

    # weekdays: so dias uteis (0-4) — sabado 10:00 -> segunda (2026-07-06)
    nxt4 = eng.compute_next_run({"kind": "daily", "time": "10:00", "weekdays": [0, 1, 2, 3, 4]}, "America/Sao_Paulo", now)
    check("F2: weekdays uteis pulam o fim de semana", nxt4.astimezone(eng._tz("America/Sao_Paulo")).weekday() == 0 and nxt4.day == 6, nxt4)

    check("F2: proxima execucao SEMPRE no futuro", all(
        eng.compute_next_run(s, "America/Sao_Paulo", now) > now
        for s in ({"kind": "daily", "time": "09:00"}, {"kind": "daily", "time": "23:59"}, {"kind": "interval", "minutes": 5})
    ))

    # render_task_prompt
    p = eng.render_task_prompt({"name": "Noticias diarias", "instructions": "Buscar noticias de seguros e resumir."})
    check("F2: prompt tem nome e instrucoes", "Noticias diarias" in p and "Buscar noticias" in p)
    check("F2: prompt proibe meta-comentarios", "sem meta-coment" in p.lower())

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        sys.exit(1)


if __name__ == "__main__":
    run()
