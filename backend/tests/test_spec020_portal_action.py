"""SPEC-020 P3 - portal_action logica pura (build_portal_params + format_result).

Rodar: python backend/tests/test_spec020_portal_action.py
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


for name in ("app", "app.agents", "app.agents.tools"):
    m = sys.modules.setdefault(name, types.ModuleType(name))
    m.__path__ = []

spec = importlib.util.spec_from_file_location("app.agents.tools.portal_params", ROOT / "app/agents/tools/portal_params.py")
pp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pp)

PROFILE = {"nome": "Auto Fleet Corretora", "email": "operacional@autofleet.com.br", "telefone": "4833646664", "cpf_cnpj": "00000000000191"}


def run():
    print("== SPEC-020 P3 - portal_action (params) ==\n")

    # faltando dado obrigatorio -> erro
    p, e = pp.build_portal_params({"insurer_name": "Yelum", "placa": "ABC1D23"}, PROFILE)
    check("faltando cpf/data -> erro", p is None and e and "Faltam dados" in e)

    # perfil de acionamento vazio -> erro instrutivo
    p, e = pp.build_portal_params({"insurer_name": "Yelum", "cpf_cnpj": "x", "placa": "y", "data_dano": "05/07/2026"}, {})
    check("sem perfil de acionamento -> erro", p is None and e and "Perfil de Acionamento" in e)

    # valido -> params montados
    flat = {"insurer_name": "Yelum", "cpf_cnpj": "030", "placa": "QJQ0A91", "data_dano": "05/07/2026",
            "peca": "vidro de porta", "como_ocorreu": "encontrou danificado", "onde_ocorreu": "urbano",
            "descricao": "vidro quebrado no estacionamento", "estado": "SC", "cidade": "Florianopolis", "cep": "88010-001"}
    p, e = pp.build_portal_params(flat, PROFILE)
    check("valido -> sem erro", e is None and p is not None)
    check("solicitante = Corretor", p["solicitante"]["relacao"] == "Corretor")
    check("solicitante usa perfil da corretora", p["solicitante"]["email"] == PROFILE["email"])
    check("dano aninhado", p["dano"]["peca"] == "vidro de porta")
    check("local aninhado", p["local"]["cep"] == "88010-001")
    check("confirm sempre False (nunca envia sozinha)", p["confirm"] is False)

    # format_result
    check("done -> concluido", "concluido" in pp.format_result({"status": "done", "evidence": {"message": "protocolo 123"}}).lower())
    nh = pp.format_result({"status": "needs_human", "evidence": {"campo": "peca", "opcoes": ["VIDRO DE PORTA", "PARABRISA"], "message": "escolha"}})
    check("needs_human lista opcoes", "VIDRO DE PORTA" in nh)
    check("failed -> nao consegui", "nao consegui" in pp.format_result({"status": "failed", "error": "x"}).lower())
    check("queued -> worker nao processou", "worker" in pp.format_result({"status": "queued"}).lower())

    print(f"\n== {PASS} ok / {FAIL} fail ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  FALHOU: {n} ({d})")
    return FAIL == 0


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
