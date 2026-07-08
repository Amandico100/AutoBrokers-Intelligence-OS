"""SPEC-023 P1 - Allianz authenticated portal login + session persistence.

Rodar: python backend/tests/test_spec023_allianz_login.py
House-style: importlib/stubs/check, sem pytest.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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


class _Res:
    def __init__(self, data=None):
        self.data = data or []


class _Table:
    def __init__(self, db, name):
        self.db = db
        self.name = name
        self.filters = []
        self.limit_n = None
        self.upsert_row = None
        self.update_row = None

    def select(self, *_args):
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def limit(self, n):
        self.limit_n = n
        return self

    def upsert(self, row, on_conflict=None):
        self.upsert_row = row
        self.on_conflict = on_conflict
        return self

    def update(self, row):
        self.update_row = row
        return self

    def execute(self):
        rows = self.db.setdefault(self.name, [])
        if self.upsert_row is not None:
            conflict = ["company_id", "portal_key", "account_label"]
            for idx, row in enumerate(rows):
                if all(row.get(k) == self.upsert_row.get(k) for k in conflict):
                    rows[idx] = {**row, **self.upsert_row}
                    return _Res([rows[idx]])
            rows.append(dict(self.upsert_row))
            return _Res([self.upsert_row])
        if self.update_row is not None:
            out = []
            for idx, row in enumerate(rows):
                if all(row.get(k) == v for k, v in self.filters):
                    rows[idx] = {**row, **self.update_row}
                    out.append(rows[idx])
            return _Res(out)
        out = [row for row in rows if all(row.get(k) == v for k, v in self.filters)]
        if self.limit_n is not None:
            out = out[: self.limit_n]
        return _Res(out)


class _Supa:
    def __init__(self):
        self.db = {}

    def table(self, name):
        return _Table(self.db, name)


def run():
    print("== SPEC-023 P1 - Allianz login/session ==\n")

    import asyncio
    from cryptography.fernet import Fernet

    os.environ["PORTAL_VAULT_KEY"] = Fernet.generate_key().decode()

    from portal_worker.journeys import get_journey
    from portal_worker.journeys.allianz_corretor import ALLIANZ_LOGIN_URL, interpret_login, login_check
    from portal_worker.worker import _load_session_bundle, _load_session_state, _save_session_state

    check("registry resolve allianz login_check", callable(get_journey("allianz_corretor", "login_check")))
    check("Allianz login URL oficial", ALLIANZ_LOGIN_URL.startswith("https://www.allianznet.com.br/"))

    ok = interpret_login("Allianz Corretor principal Parcelas Inadimplentes Nova Cotacao Sair")
    check("Allianz dashboard -> done", ok.status == "done", ok)
    check("Allianz dashboard captura logged_in", ok.captured.get("logged_in") is True, ok.captured)

    bad = interpret_login("Usuario ou senha invalida")
    check("Allianz credencial rejeitada -> failed", bad.status == "failed", bad)

    hitl = interpret_login("Informe o codigo de verificacao enviado para seu e-mail")
    check("Allianz codigo/2FA -> needs_human", hitl.status == "needs_human", hitl)

    unk = interpret_login("Bem-vindo(a) ao Allianznet Usuario Senha Iniciar sessao")
    check("Allianz tela de login sem dashboard -> needs_human", unk.status == "needs_human", unk)

    class _El:
        def __init__(self, page, kind):
            self.page = page
            self.kind = kind

        async def fill(self, value):
            self.page.filled[self.kind] = value

        async def click(self):
            self.page.submitted = True

    class _Page:
        url = ALLIANZ_LOGIN_URL

        def __init__(self):
            self.filled = {}
            self.submitted = False

        async def goto(self, url, wait_until=None):
            self.url = url

        async def wait_for_timeout(self, ms):
            pass

        async def wait_for_url(self, pattern, timeout=None):
            if self.submitted:
                self.url = "https://www.allianznet.com.br/ngx-azb-epac/private/home"

        async def wait_for_load_state(self, state, timeout=None):
            pass

        async def query_selector(self, selector):
            if "password" in selector or "senha" in selector:
                return _El(self, "password")
            if "button" in selector or "submit" in selector:
                return _El(self, "submit")
            if "usuario" in selector or "username" in selector or "text" in selector:
                return _El(self, "username")
            return None

        async def inner_text(self, selector):
            if "/private/" in self.url:
                return "Corretor principal Vendas Consultas Gestao Nova Cotacao"
            return "Bem-vindo(a) ao Allianznet Usuario Senha Iniciar sessao"

    fake_page = _Page()
    fake_ev = {}
    live_like = asyncio.run(login_check(fake_page, {"username": "BA000000", "password": "senha"}, fake_ev))
    check("login_check espera redirect privado atrasado", live_like.status == "done", live_like)
    check("login_check preenche usuario e senha", fake_page.filled.get("username") and fake_page.filled.get("password"), fake_page.filled)

    class _SessionPage(_Page):
        async def wait_for_url(self, pattern, timeout=None):
            self.url = "https://www.allianznet.com.br/ngx-azb-epac/private/home"

    session_page = _SessionPage()
    session_ev = {}
    reused = asyncio.run(login_check(session_page, {"username": "BA000000", "password": "senha", "session_loaded": True}, session_ev))
    check("login_check detecta sessao persistida antes de preencher", reused.status == "done" and session_ev.get("session_reused") is True, (reused, session_ev))
    check("login_check nao submete quando sessao ja esta valida", session_page.submitted is False, session_page.submitted)

    supa = _Supa()
    job = {"company_id": "company-1", "portal_key": "allianz_corretor"}
    account = {"account_label": "principal"}
    state = {"cookies": [{"name": "sid", "value": "secret-cookie"}], "origins": []}

    saved = _save_session_state(supa, job, account, state)
    check("save session retorna True", saved is True, saved)
    row = supa.db["portal_sessions"][0]
    enc = row.get("storage_state_encrypted") or ""
    check("session upsert usa identidade company/portal/account", row.get("company_id") == "company-1" and row.get("portal_key") == "allianz_corretor" and row.get("account_label") == "principal", row)
    check("session cifrada nao contem cookie em claro", "secret-cookie" not in enc, enc)

    loaded = _load_session_state(supa, job, account)
    check("load session decifra storage_state", loaded == state, loaded)

    session_storage = [{"origin": "https://www.allianznet.com.br", "entries": {"token": "session-token"}}]
    saved_bundle = _save_session_state(supa, job, account, state, session_storage=session_storage)
    check("save session bundle retorna True", saved_bundle is True, saved_bundle)
    enc2 = supa.db["portal_sessions"][0].get("storage_state_encrypted") or ""
    check("session bundle cifrada nao contem sessionStorage em claro", "session-token" not in enc2, enc2)
    bundle = _load_session_bundle(supa, job, account)
    check("load session bundle traz storage_state", bundle.get("storage_state") == state, bundle)
    check("load session bundle traz session_storage", bundle.get("session_storage") == session_storage, bundle)

    print(f"\n== {PASS} ok / {FAIL} fail ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  FALHOU: {n} ({d})")
    return FAIL == 0


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
