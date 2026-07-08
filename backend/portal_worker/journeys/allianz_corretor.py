"""Journey AllianzNet corretor (SPEC-023 P1).

P1 cobre apenas login autenticado e classificacao segura da sessao. A jornada de
cobranca (`cobranca_sweep`) vem depois e deve reusar a sessao persistida aqui.
"""
from __future__ import annotations

import unicodedata
from typing import Any, Dict

from portal_worker.journeys import JourneyResult

ALLIANZ_LOGIN_URL = "https://www.allianznet.com.br/ngx-azb-epac/public/home"


def _norm(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(text.split())


_FAIL = (
    "senha invalida",
    "usuario invalido",
    "usuario ou senha invalida",
    "credenciais invalidas",
    "login invalido",
    "dados incorretos",
    "nao autorizado",
)

_HITL = (
    "captcha",
    "codigo de verificacao",
    "codigo de seguranca",
    "token",
    "otp",
    "autenticacao em duas etapas",
    "duas etapas",
    "2fa",
    "mfa",
)

_DASHBOARD_SIGNALS = (
    "corretor principal",
    "parcelas inadimplentes",
    "nova cotacao",
    "fale com a gente agora",
    "tempo sessao",
    "vendas",
    "consultas",
    "gestao",
)


def interpret_login(page_text: str, url: str = "") -> JourneyResult:
    """Classifica a tela pos-login da Allianz sem expor credenciais."""
    text = _norm(page_text)
    url_norm = _norm(url)
    if any(item in text for item in _FAIL):
        return JourneyResult(status="failed", message="credenciais rejeitadas pelo portal Allianz")
    if any(item in text for item in _HITL):
        return JourneyResult(status="needs_human", message="portal Allianz pediu CAPTCHA/2FA")
    hits = sum(1 for item in _DASHBOARD_SIGNALS if item in text)
    if hits >= 2 or "ngx-azb-epac/private/" in url_norm:
        return JourneyResult(status="done", captured={"logged_in": True, "portal": "allianz_corretor"})
    return JourneyResult(status="needs_human", message="tela pos-login Allianz nao reconhecida")


async def _fill_first(page, selectors, value: str) -> bool:
    for sel in selectors:
        try:
            el = await page.query_selector(sel)
            if el:
                await el.fill(value)
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


async def _fill_login_fallback(page, username: str, password: str) -> Dict[str, bool]:
    """Fallback DOM para Angular/Material quando atributos mudam."""
    try:
        return await page.evaluate(
            """({username, password}) => {
              const visible = (el) => {
                const r = el.getBoundingClientRect();
                const s = getComputedStyle(el);
                return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
              };
              const setValue = (el, value) => {
                el.focus();
                el.value = value;
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
              };
              const inputs = [...document.querySelectorAll('input')].filter(visible);
              const pass = inputs.find(i => (i.type || '').toLowerCase() === 'password');
              const user = inputs.find(i => {
                if ((i.type || '').toLowerCase() === 'password') return false;
                const hay = [
                  i.id, i.name, i.placeholder, i.getAttribute('aria-label'),
                  i.getAttribute('formcontrolname')
                ].join(' ').toLowerCase();
                return /usu|user|login|email|corretor|susep|codigo/.test(hay);
              }) || inputs.find(i => (i.type || '').toLowerCase() !== 'password');
              if (user) setValue(user, username);
              if (pass) setValue(pass, password);
              return {user: !!user, pass: !!pass};
            }""",
            {"username": username, "password": password},
        )
    except Exception:  # noqa: BLE001
        return {"user": False, "pass": False}


async def _click_submit(page) -> bool:
    selectors = (
        "button[type=submit]",
        "input[type=submit]",
        "button:has-text('Iniciar sessao')",
        "button:has-text('Iniciar sessão')",
        "button:has-text('Entrar')",
        "button:has-text('Acessar')",
        "button:has-text('Login')",
    )
    for sel in selectors:
        try:
            el = await page.query_selector(sel)
            if el:
                await el.click()
                return True
        except Exception:  # noqa: BLE001
            continue
    try:
        return bool(await page.evaluate(
            """() => {
              const norm = (s) => (s || '').normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase();
              const visible = (el) => {
                const r = el.getBoundingClientRect();
                const s = getComputedStyle(el);
                return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
              };
              const buttons = [...document.querySelectorAll('button,input[type=submit]')].filter(visible);
              const btn = buttons.find(b => /iniciar sessao|entrar|acessar|login/.test(norm(b.innerText || b.value)));
              if (!btn) return false;
              btn.click();
              return true;
            }"""
        ))
    except Exception:  # noqa: BLE001
        return False


async def login_check(page, params: Dict[str, Any], evidence: Dict[str, Any]) -> JourneyResult:
    """Login AllianzNet com usuario/senha de `portal_accounts`.

    CAPTCHA/2FA nunca e burlado: se aparecer, devolve needs_human com evidencia.
    """
    login_url = str(params.get("login_url") or ALLIANZ_LOGIN_URL).strip()
    username = str(params.get("username") or "").strip()
    password = str(params.get("password") or "")
    if not username or not password:
        return JourneyResult(status="failed", message="username/password ausentes para Allianz")

    await page.goto(login_url, wait_until="domcontentloaded")
    await page.wait_for_timeout(2500)
    if params.get("session_loaded"):
        try:
            timeout_ms = int(params.get("session_reuse_timeout_ms") or 15000)
        except Exception:  # noqa: BLE001
            timeout_ms = 15000
        try:
            await page.wait_for_url("**/private/**", timeout=timeout_ms)
        except Exception:  # noqa: BLE001
            pass
    try:
        initial_text = await page.inner_text("body")
    except Exception:  # noqa: BLE001
        initial_text = ""
    initial = interpret_login(initial_text, getattr(page, "url", login_url))
    if initial.status == "done":
        evidence["url"] = getattr(page, "url", login_url)
        evidence["session_reused"] = True
        return initial

    user_ok = await _fill_first(
        page,
        (
            "input[name=usuario]",
            "input[name=username]",
            "input[name=login]",
            "input[id*=usuario i]",
            "input[id*=user i]",
            "input[formcontrolname*=usuario i]",
            "input[formcontrolname*=user i]",
            "input[placeholder*=Usuario i]",
            "input[placeholder*=Usuário i]",
            "input[type=text]",
        ),
        username,
    )
    pass_ok = await _fill_first(
        page,
        (
            "input[type=password]",
            "input[name=senha]",
            "input[name=password]",
            "input[id*=senha i]",
            "input[id*=password i]",
            "input[formcontrolname*=senha i]",
            "input[formcontrolname*=password i]",
        ),
        password,
    )
    if not (user_ok and pass_ok):
        fallback = await _fill_login_fallback(page, username, password)
        user_ok = user_ok or bool(fallback.get("user"))
        pass_ok = pass_ok or bool(fallback.get("pass"))
    evidence["login_fields_found"] = {"username": bool(user_ok), "password": bool(pass_ok)}
    if not (user_ok and pass_ok):
        return JourneyResult(status="needs_human", message="campos de login Allianz nao encontrados")

    if not await _click_submit(page):
        return JourneyResult(status="needs_human", message="botao de login Allianz nao encontrado")

    try:
        timeout_ms = int(params.get("login_timeout_ms") or 60000)
    except Exception:  # noqa: BLE001
        timeout_ms = 60000
    try:
        await page.wait_for_url("**/private/**", timeout=timeout_ms)
    except Exception:  # noqa: BLE001
        pass
    await page.wait_for_timeout(2500)
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:  # noqa: BLE001
        pass
    try:
        body = await page.inner_text("body")
    except Exception:  # noqa: BLE001
        body = ""
    evidence["url"] = getattr(page, "url", login_url)
    return interpret_login(body, evidence["url"])
