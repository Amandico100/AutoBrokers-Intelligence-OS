"""Journey do portal de vidros/lanternas (SPEC-020 P1).

Portal exato a confirmar com o founder (abraseuatendimento.com.br?). Os seletores
são genéricos até a confirmação; a DECISÃO (login ok/falha/precisa humano) é PURA
e testável offline (interpret_login) contra fixtures HTML.
"""
from __future__ import annotations

from typing import Any, Dict

from portal_worker.journeys import JourneyResult

_LOGIN_OK = ("sair", "logout", "meus pedidos", "bem-vindo", "bem vindo", "painel", "minha conta")
_LOGIN_FAIL = (
    "senha invalida", "senha inválida", "usuario invalido", "usuário inválido",
    "credenciais invalidas", "credenciais inválidas", "login invalido", "login inválido",
    "dados incorretos", "senha incorreta",
)
_HITL = (
    "captcha", "verificacao", "verificação", "codigo de seguranca", "código de segurança",
    "autenticacao em duas etapas", "autenticação em duas etapas", "two-factor", "2fa",
)


def interpret_login(page_text: str, url: str = "") -> JourneyResult:
    """PURO: resultado do login a partir do texto/URL pós-submit. Testável offline.
    Ordem: falha explícita > CAPTCHA/2FA (humano) > sucesso > desconhecido (humano)."""
    text = (page_text or "").lower()
    if any(s in text for s in _LOGIN_FAIL):
        return JourneyResult(status="failed", message="credenciais rejeitadas pelo portal")
    if any(s in text for s in _HITL):
        return JourneyResult(status="needs_human", message="portal pediu CAPTCHA/2FA")
    if any(s in text for s in _LOGIN_OK):
        return JourneyResult(status="done", captured={"logged_in": True})
    return JourneyResult(status="needs_human", message="tela pós-login não reconhecida")


async def login_check(page: Any, params: Dict[str, Any], evidence: Dict[str, Any]) -> JourneyResult:
    """Shell Playwright: navega, preenche user/senha, submete, coleta sinais e decide."""
    login_url = str(params.get("login_url") or "")
    username = str(params.get("username") or "")
    password = str(params.get("password") or "")
    if not login_url:
        return JourneyResult(status="failed", message="login_url ausente nos params")

    await page.goto(login_url, wait_until="domcontentloaded")
    for sel in ("input[type=email]", "input[name=usuario]", "input[name=login]",
                "input[name=email]", "input[name=user]", "#usuario", "#login", "#email"):
        el = await page.query_selector(sel)
        if el:
            await el.fill(username)
            break
    for sel in ("input[type=password]", "input[name=senha]", "input[name=password]", "#senha", "#password"):
        el = await page.query_selector(sel)
        if el:
            await el.fill(password)
            break
    for sel in ("button[type=submit]", "input[type=submit]",
                "button:has-text('Entrar')", "button:has-text('Acessar')", "button:has-text('Login')"):
        el = await page.query_selector(sel)
        if el:
            await el.click()
            break
    await page.wait_for_timeout(2500)
    try:
        body = await page.inner_text("body")
    except Exception:  # noqa: BLE001
        body = ""
    evidence["url"] = getattr(page, "url", login_url)
    return interpret_login(body, evidence["url"])
