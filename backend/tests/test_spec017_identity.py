"""SPEC-017 - Identidade configurável do atendente (fim do 'Even' fixo).

Rodar: python backend/tests/test_spec017_identity.py
Offline: carrega prompts.py direto; sem banco/rede.
"""

import importlib.util
import sys
import types
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


for name in ("app", "app.core"):
    m = sys.modules.setdefault(name, types.ModuleType(name))
    m.__path__ = []

spec = importlib.util.spec_from_file_location("app.core.prompts", ROOT / "app/core/prompts.py")
prompts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prompts)


def run():
    print("== SPEC-017 - Identidade configuravel do atendente ==\n")

    p = prompts.build_composite_prompt("Regras da corretora.", agent_role="attendance", agent_display_name="Saionara")
    check("attendance com nome: nome entra no prompt", "Saionara" in p)
    check("attendance com nome: bloco de identidade presente", "SUA IDENTIDADE" in p)
    check("attendance com nome: proibicao de nomes internos", "nomes internos" in p.lower())

    p2 = prompts.build_composite_prompt("Regras.", agent_role="attendance")
    check("attendance sem nome: sem bloco de identidade (nao inventa nome)", "SUA IDENTIDADE" not in p2)

    p3 = prompts.build_composite_prompt("Regras.", agent_role="core", agent_display_name="Saionara")
    check("core: identidade de atendente NAO se aplica", "SUA IDENTIDADE" not in p3)

    p4 = prompts.build_composite_prompt("Regras.", agent_role="attendance", agent_display_name="  ")
    check("nome vazio/espacos tratado como ausente", "SUA IDENTIDADE" not in p4)

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        sys.exit(1)


if __name__ == "__main__":
    run()
