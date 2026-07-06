"""SPEC-020 P1 - Portal worker: logica pura (interpretador de login, gate, vault).

Rodar: python backend/tests/test_spec020_portal.py
Nao roda Playwright aqui (isso e journey contra fixture no CI do worker); testa a
DECISAO pura (interpret_login) + o gate + o round-trip do cofre (se cryptography).
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # backend/
sys.path.insert(0, str(ROOT))

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


from portal_worker.journeys.vidros_lanternas import interpret_login
from portal_worker.worker import portal_real_enabled


def run():
    print("== SPEC-020 P1 - Portal worker (logica pura) ==\n")

    # interpret_login: sucesso, falha, captcha->humano, desconhecido->humano
    ok = interpret_login("Bem-vindo! Meus Pedidos | Sair", "https://portal/painel")
    check("login sucesso -> done", ok.status == "done")
    check("login sucesso captura logged_in", ok.captured.get("logged_in") is True)

    bad = interpret_login("Erro: senha invalida. Tente novamente.")
    check("senha invalida -> failed", bad.status == "failed")

    cap = interpret_login("Por favor complete o CAPTCHA para continuar")
    check("captcha -> needs_human", cap.status == "needs_human")

    unk = interpret_login("Alguma tela estranha sem sinais conhecidos")
    check("tela desconhecida -> needs_human", unk.status == "needs_human")

    # gate PORTAL_REAL_ENABLED: default OFF; liga so com valores truthy
    os.environ.pop("PORTAL_REAL_ENABLED", None)
    check("gate default OFF", portal_real_enabled() is False)
    os.environ["PORTAL_REAL_ENABLED"] = "true"
    check("gate ON com 'true'", portal_real_enabled() is True)
    os.environ["PORTAL_REAL_ENABLED"] = "0"
    check("gate OFF com '0'", portal_real_enabled() is False)
    os.environ.pop("PORTAL_REAL_ENABLED", None)

    # vault round-trip (so se cryptography instalado localmente)
    try:
        from cryptography.fernet import Fernet
        from portal_worker import vault

        os.environ["PORTAL_VAULT_KEY"] = Fernet.generate_key().decode()
        token = vault.encrypt("senha-secreta-123")
        check("vault cifra != claro", token != "senha-secreta-123")
        check("vault round-trip", vault.decrypt(token) == "senha-secreta-123")
    except ImportError:
        print("  [skip] cryptography ausente localmente (vault testado no worker)")

    print(f"\n== {PASS} ok / {FAIL} fail ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  FALHOU: {n} ({d})")
    return FAIL == 0


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
