"""Journey do portal de vidros/lanternas (SPEC-020 P2) — abraseuatendimento.com.br.

Mapeado AO VIVO (2026-07-06) com apólice de teste. O portal e PUBLICO (sem login).
Fluxo do acionamento (igual/quase-igual entre seguradoras — Yelum, Tokio, Porto):
  0. #/  -> #seguradora-input (digita) -> botao Avancar
  1. #/<insurer>/menu-atendimento -> "Iniciar atendimento"
  2. #/<insurer>/passo1 -> #inserir-cpf-input + #input_1(placa) + #input_3(data,
     datepicker Material) -> "Iniciar atendimento" -> modal "Dados da apolice"
     -> "Confirmar"
  3. #/<insurer>/passo2/<uuid> -> "Sua relacao com o titular?" (=Corretor),
     #email-segurado-input, nome/CPF-CNPJ solicitante, #telefone-input,
     "Tipo de telefone" -> Avancar
  4. #/<insurer>/passo3 -> "Qual foi a peca danificada?", "Como ocorreu o dano?",
     "Onde ocorreu o dano?" (dropdowns que VARIAM por peca/seguradora) + descricao
     (min 30 chars) -> Avancar
  5. local do servico: estado + cidade + CEP(opcional) -> Avancar
  6. 80% "Confirme a peca danificada": perguntas ESPECIFICAS que variam
     (pelicula, dianteira/traseira, lado; ou posicao do trincado, >10cm, versao).
     -> Avancar aqui CONFIRMA o pedido. So com confirm=True.
  7. escolha da loja/servico a domicilio -> confirmar -> PROTOCOLO.

DESIGN "cerebro unico": o AGENTE (Smith) DECIDE as escolhas (peca/como/onde/
especificos) a partir da conversa com o segurado; a journey CASA a escolha com a
opcao real do dropdown (match_option). Sem match confiante -> needs_human COM as
opcoes disponiveis (o agente/humano decide; a journey nunca escolhe errado nem
trava). match_option e puro e testavel offline.
"""
from __future__ import annotations

import unicodedata
from typing import Any, Dict, List, Optional

from portal_worker.journeys import JourneyResult

VIDROS_BASE = "https://abraseuatendimento.com.br/#/"


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(s.split())


def match_option(wanted: str, options: List[str]) -> Optional[str]:
    """PURO: acha a opcao do dropdown que melhor casa com 'wanted'. None se
    nenhuma casa com confianca (o agente/humano decide). Testavel offline."""
    w = _norm(wanted)
    if not w or not options:
        return None
    norm = [(_norm(o), o) for o in options]
    for n, o in norm:              # match exato
        if n == w:
            return o
    for n, o in norm:              # opcao contem tudo que o agente pediu
        if w in n:
            return o
    wset = set(w.split())          # todas as palavras do pedido estao na opcao
    best, best_score = None, 0
    for n, o in norm:
        nset = set(n.split())
        score = len(wset & nset)
        if wset <= nset and score > best_score:
            best, best_score = o, score
    return best


# ---- login (portais de CORRETOR — os que pedem login/senha; vidros nao usa) ----
_LOGIN_OK = ("sair", "logout", "meus pedidos", "bem-vindo", "bem vindo", "painel", "minha conta")
_LOGIN_FAIL = ("senha invalida", "usuario invalido", "credenciais invalidas", "login invalido",
               "dados incorretos", "senha incorreta")
_HITL = ("captcha", "verificacao", "codigo de seguranca", "autenticacao em duas etapas", "two-factor", "2fa")


def interpret_login(page_text: str, url: str = "") -> JourneyResult:
    """PURO: resultado do login (portais de corretor)."""
    text = _norm(page_text)
    if any(s in text for s in (_norm(x) for x in _LOGIN_FAIL)):
        return JourneyResult(status="failed", message="credenciais rejeitadas pelo portal")
    if any(s in text for s in _HITL):
        return JourneyResult(status="needs_human", message="portal pediu CAPTCHA/2FA")
    if any(s in text for s in _LOGIN_OK):
        return JourneyResult(status="done", captured={"logged_in": True})
    return JourneyResult(status="needs_human", message="tela pos-login nao reconhecida")


_VIDROS_ERR = ("nao encontrad", "invalid", "nao localizamos", "apolice nao", "sem cobertura")
_VIDROS_PROTO = ("protocolo", "numero do atendimento", "n do atendimento", "solicitacao registrada",
                 "atendimento n")


def interpret_atendimento(url: str, page_text: str) -> JourneyResult:
    """PURO: em que ponto do acionamento de vidros parou."""
    u = _norm(url)
    text = _norm(page_text)
    if any(s in text for s in _VIDROS_PROTO):
        return JourneyResult(status="done", captured={"stage": "protocolo"}, message="protocolo capturado")
    if any(s in text for s in _VIDROS_ERR):
        return JourneyResult(status="failed", message="portal nao localizou CPF/placa ou dado invalido")
    for stage in ("passo5", "passo4", "passo3", "passo2", "passo1", "menu-atendimento"):
        if stage in u:
            return JourneyResult(status="needs_human", captured={"stage": stage}, message=f"parou em {stage}")
    return JourneyResult(status="needs_human", message="tela do acionamento nao reconhecida")


# ---------------- shell Playwright (imperativo) ----------------
async def _dismiss(page) -> None:
    try:
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(250)
        await page.mouse.click(5, 5)
        await page.wait_for_timeout(250)
    except Exception:  # noqa: BLE001
        pass


async def _click_button(page, text: str) -> bool:
    for x in await page.query_selector_all("button"):
        try:
            if await x.is_visible() and _norm(text) in _norm(await x.inner_text()):
                await x.click()
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


async def _visible_options(page) -> List[str]:
    for sel in ("[role=option]", ".ng-option", "mat-option", ".dropdown-item", "li"):
        out = []
        for o in await page.query_selector_all(sel):
            try:
                if await o.is_visible():
                    t = (await o.inner_text() or "").strip()
                    if t:
                        out.append(t)
            except Exception:  # noqa: BLE001
                continue
        if out:
            return out
    return []


async def _choose(page, trigger, wanted: str) -> tuple:
    """Abre um dropdown e escolhe a opcao que casa com 'wanted'.
    Retorna (ok, options). Sem match -> (False, options) p/ o agente decidir."""
    try:
        await trigger.click()
        await page.wait_for_timeout(900)
        options = await _visible_options(page)
        chosen = match_option(wanted, options)
        if not chosen:
            await _dismiss(page)
            return False, options
        for o in await page.query_selector_all("[role=option], .ng-option, mat-option, .dropdown-item, li"):
            try:
                if await o.is_visible() and (await o.inner_text() or "").strip() == chosen:
                    await o.click()
                    await page.wait_for_timeout(500)
                    return True, options
            except Exception:  # noqa: BLE001
                continue
        await _dismiss(page)
        return False, options
    except Exception:  # noqa: BLE001
        return False, []


async def _choose_any_select(page, wanted: str) -> tuple:
    """Acha o <select> nativo (mesmo visually-hidden do Material) que tem a opcao
    desejada e a seleciona (dispara change/input p/ o Angular ligar). Robusto para
    dropdowns escondidos. Retorna (ok, options)."""
    if not wanted:
        return True, []
    for s in await page.query_selector_all("select"):
        try:
            opts = await s.evaluate(
                "el => Array.from(el.options).map(o => (o.textContent||'').trim()).filter(Boolean)")
        except Exception:  # noqa: BLE001
            continue
        chosen = match_option(wanted, opts)
        if chosen:
            try:
                await s.select_option(label=chosen)
                await s.evaluate(
                    "el => { el.dispatchEvent(new Event('change',{bubbles:true}));"
                    " el.dispatchEvent(new Event('input',{bubbles:true})); }")
                await page.wait_for_timeout(500)
                return True, opts
            except Exception:  # noqa: BLE001
                return False, opts
    return False, []


async def _select_first_real(page, sel_el) -> bool:
    """Seleciona a 1a opcao real (nao 'Selecione...') de um <select> — para campos
    obrigatorios onde qualquer valor serve para avancar (ex.: tipo de telefone)."""
    try:
        opts = await sel_el.evaluate(
            "el => Array.from(el.options).map(o => ({v:o.value, t:(o.textContent||'').trim()}))")
        for o in opts:
            if o["v"] and "selecione" not in o["t"].lower():
                await sel_el.select_option(value=o["v"])
                await sel_el.evaluate("el => el.dispatchEvent(new Event('change',{bubbles:true}))")
                await page.wait_for_timeout(400)
                return True
    except Exception:  # noqa: BLE001
        pass
    return False


async def _select_insurer_start(page, insurer: str) -> bool:
    await page.goto(VIDROS_BASE, wait_until="domcontentloaded")
    await page.wait_for_timeout(3500)
    inp = await page.query_selector("#seguradora-input")
    if not inp:
        return False
    await inp.click()
    await inp.fill(insurer)
    await page.wait_for_timeout(1500)
    for o in await page.query_selector_all("[role=option]"):
        if await o.is_visible():
            await o.click()
            break
    await page.wait_for_timeout(500)
    await _click_button(page, "Avan")            # Avancar
    await page.wait_for_timeout(3500)
    await _click_button(page, "Iniciar atendimento")
    await page.wait_for_timeout(3500)
    return "passo1" in page.url


async def abrir_atendimento(page, params: Dict[str, Any], evidence: Dict[str, Any]) -> JourneyResult:
    """Vidros PUBLICO. O agente monta os params a partir da conversa. A journey
    navega ate a tela de confirmacao (80%) e SO submete o pedido com confirm=True.
    params: insurer_name, cpf_cnpj, placa, data_dano, solicitante{relacao,email,
    nome,cpf_cnpj,telefone}, dano{peca,como,onde,descricao}, local{estado,cidade,
    cep}, especificos{pergunta->resposta}, confirm."""
    insurer = str(params.get("insurer_name") or "").strip()
    cpf = str(params.get("cpf_cnpj") or "").strip()
    placa = str(params.get("placa") or "").strip()
    data_dano = str(params.get("data_dano") or "").strip()
    if not (insurer and cpf and placa and data_dano):
        return JourneyResult(status="failed", message="faltam dados: insurer_name, cpf_cnpj, placa, data_dano")

    if not await _select_insurer_start(page, insurer):
        return JourneyResult(status="needs_human", message="tela inicial do portal de vidros mudou")

    # passo1: CPF + placa + data (datepicker Material -> digita e fecha overlay)
    await (await page.query_selector("#inserir-cpf-input")).fill(cpf)
    await (await page.query_selector("#input_1")).fill(placa)
    d = await page.query_selector("#input_3")
    if d:
        await d.click()
        await page.wait_for_timeout(300)
        await page.keyboard.type(data_dano)
        await page.keyboard.press("Tab")
        await _dismiss(page)
    await _click_button(page, "Iniciar atendimento")
    await page.wait_for_timeout(4500)
    body = await page.inner_text("body")
    if any(s in _norm(body) for s in _VIDROS_ERR):
        return JourneyResult(status="failed", message="portal nao localizou CPF/placa (verifique a apolice)")

    # modal "Dados da apolice" -> Confirmar
    await _click_button(page, "Confirmar")
    await page.wait_for_timeout(4000)

    # Camada 2 (SPEC-020) — daqui pra frente o CEREBRO dirige a tela (passo2 -> 80%).
    # Variacoes por seguradora/peca sao tratadas com inteligencia; nunca trava. Para
    # na confirmacao (80%) sem enviar (a menos de confirm=True). Dados REAIS, sem mascara.
    from portal_worker.adaptive import run_adaptive

    goal = f"Abrir atendimento de vidros na seguradora {insurer} para o segurado, ate a tela de confirmacao."
    collected = {
        "cpf_cnpj": cpf, "placa": placa, "data_dano": data_dano,
        "segurado": params.get("segurado") or {},   # apolice/chassi/veiculo (InfoCap)
        "solicitante": params.get("solicitante") or {},
        "dano": params.get("dano") or {},
        "local": params.get("local") or {},
        "especificos": params.get("especificos") or {},
    }
    return await run_adaptive(page, goal, collected, evidence, confirm=bool(params.get("confirm")))


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
