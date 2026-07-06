"""Journey do portal de vidros/lanternas (SPEC-020 P2) — abraseuatendimento.com.br.

DESCOBERTA (mapeado ao vivo 2026-07-06): o portal de vidros é PUBLICO — NAO tem
login/senha. Fluxo de acionamento (maior volume das corretoras):
  1. #/  -> #seguradora-input (digita a seguradora) -> #direcionar-seguradora-btn
  2. #/<insurer>/menu-atendimento -> #iniciar-atendimento-btn
  3. #/<insurer>/passo1 -> #inserir-cpf-input (CPF/CNPJ) + #input_1 (placa) +
     #input_3 (data do dano) -> submete (#iniciar-atendimento-btn)
  4. cobertura -> item (troca/reparo) -> agendamento -> PROTOCOLO  [passos 2-N a
     mapear com dados de teste reais; a journey para em needs_human na fronteira].

A DECISAO (que tela é essa? deu certo? precisa humano?) é PURA e testável offline
(interpret_atendimento). O agente (Smith) decide QUANDO acionar; a journey executa.
"""
from __future__ import annotations

from typing import Any, Dict

from portal_worker.journeys import JourneyResult

VIDROS_BASE = "https://abraseuatendimento.com.br/#/"

# ---- login (portais de CORRETOR — os que pedem login/senha; vidros nao usa) ----
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
    """PURO: resultado do login (portais de corretor). Testável offline."""
    text = (page_text or "").lower()
    if any(s in text for s in _LOGIN_FAIL):
        return JourneyResult(status="failed", message="credenciais rejeitadas pelo portal")
    if any(s in text for s in _HITL):
        return JourneyResult(status="needs_human", message="portal pediu CAPTCHA/2FA")
    if any(s in text for s in _LOGIN_OK):
        return JourneyResult(status="done", captured={"logged_in": True})
    return JourneyResult(status="needs_human", message="tela pós-login não reconhecida")


# ---- vidros (acionamento publico) ----
_VIDROS_ERR = ("não encontrad", "nao encontrad", "inválid", "invalid", "não localizamos", "nao localizamos")
_VIDROS_PROTO = ("protocolo", "número do atendimento", "numero do atendimento", "solicitação registrada")


def interpret_atendimento(url: str, page_text: str) -> JourneyResult:
    """PURO: em que ponto do acionamento de vidros a navegação parou.
    protocolo capturado -> done; erro/não-encontrado -> failed; senão -> needs_human
    (o agente nunca fica preso: sempre há uma saída — humano assume/reporta)."""
    u = (url or "").lower()
    text = (page_text or "").lower()
    if any(s in text for s in _VIDROS_PROTO):
        return JourneyResult(status="done", captured={"stage": "protocolo"}, message="protocolo capturado")
    if any(s in text for s in _VIDROS_ERR):
        return JourneyResult(status="failed", message="portal não localizou CPF/placa ou dado inválido")
    if "passo1" in u:
        return JourneyResult(status="needs_human", captured={"stage": "passo1"}, message="passo1 (dados do segurado)")
    if "menu-atendimento" in u:
        return JourneyResult(status="needs_human", captured={"stage": "menu"}, message="menu de atendimento")
    return JourneyResult(status="needs_human", message="tela do acionamento não reconhecida")


async def _select_insurer_and_start(page, insurer: str) -> bool:
    """Passos 0-2: seleciona seguradora e clica em Iniciar atendimento. True se chegou no passo1."""
    await page.goto(VIDROS_BASE, wait_until="domcontentloaded")
    await page.wait_for_timeout(3500)
    inp = await page.query_selector("#seguradora-input")
    if not inp:
        return False
    await inp.click()
    await inp.fill(insurer)
    await page.wait_for_timeout(1500)
    for os_sel in ("[role=option]", ".dropdown-item", "li"):
        opts = await page.query_selector_all(os_sel)
        for o in opts:
            try:
                if await o.is_visible():
                    await o.click()
                    break
            except Exception:  # noqa: BLE001
                continue
        else:
            continue
        break
    await page.wait_for_timeout(600)
    btn = await page.query_selector("#direcionar-seguradora-btn")
    if btn:
        await btn.click()
    await page.wait_for_timeout(3500)
    ini = await page.query_selector("#iniciar-atendimento-btn")
    if ini:
        await ini.click()
    await page.wait_for_timeout(3500)
    return True


async def abrir_atendimento(page, params: Dict[str, Any], evidence: Dict[str, Any]) -> JourneyResult:
    """Vidros PUBLICO (sem login): abre um acionamento de vidros.
    params: {insurer_name, cpf_cnpj, placa, data_dano?, confirm?}.
    Sem confirm=True NAO submete (dry-run seguro: preenche e para)."""
    insurer = str(params.get("insurer_name") or "").strip()
    cpf = str(params.get("cpf_cnpj") or "").strip()
    placa = str(params.get("placa") or "").strip()
    data_dano = str(params.get("data_dano") or "").strip()
    if not (insurer and cpf and placa):
        return JourneyResult(status="failed", message="faltam dados: insurer_name, cpf_cnpj, placa")

    if not await _select_insurer_and_start(page, insurer):
        return JourneyResult(status="needs_human", message="tela inicial do portal de vidros mudou")

    cpf_el = await page.query_selector("#inserir-cpf-input")
    placa_el = await page.query_selector("#input_1")
    if not (cpf_el and placa_el):
        evidence["url"] = page.url
        evidence["screen"] = (await page.inner_text("body"))[:400]
        return JourneyResult(status="needs_human", message="passo1 do acionamento não reconhecido")
    await cpf_el.fill(cpf)
    await placa_el.fill(placa)
    if data_dano:
        d = await page.query_selector("#input_3")
        if d:
            await d.fill(data_dano)

    # Segurança: só submete com confirm explícito (evita abrir acionamento por engano).
    if not params.get("confirm"):
        evidence["stage"] = "passo1_preenchido"
        return JourneyResult(status="needs_human", captured={"stage": "passo1_ready"},
                             message="passo1 preenchido (dry-run) — confirme para submeter")

    sub = await page.query_selector("#iniciar-atendimento-btn")
    if sub:
        await sub.click()
    await page.wait_for_timeout(4500)
    body = (await page.inner_text("body"))[:800]
    evidence["url"] = page.url
    evidence["screen"] = body
    return interpret_atendimento(page.url, body)


async def login_check(page, params: Dict[str, Any], evidence: Dict[str, Any]) -> JourneyResult:
    """Portais de CORRETOR (com login/senha). Vidros NAO usa isto."""
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
