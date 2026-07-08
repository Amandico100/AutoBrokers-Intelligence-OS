"""Journey AllianzNet corretor (SPEC-023 P1).

P1 cobre apenas login autenticado e classificacao segura da sessao. A jornada de
cobranca (`cobranca_sweep`) vem depois e deve reusar a sessao persistida aqui.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from portal_worker.journeys import JourneyResult

ALLIANZ_LOGIN_URL = "https://www.allianznet.com.br/ngx-azb-epac/public/home"
ALLIANZ_PRIVATE_HOME = "https://www.allianznet.com.br/ngx-azb-epac/private/home"


def _norm(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(text.split())


def _digits(value: Any) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split())


def _parse_money_br(value: Any) -> Optional[float]:
    text = re.sub(r"[^0-9,.-]", "", str(value or "").strip())
    if not text:
        return None
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return round(float(text), 2)
    except ValueError:
        return None


def _date_like(value: Any) -> str:
    text = str(value or "")
    m = re.search(r"\b\d{2}/\d{2}/\d{4}\b", text)
    return m.group(0) if m else ""


def _slice_between(text: str, start: str, stops: Iterable[str]) -> str:
    blob = _clean_text(text)
    start_re = re.escape(start).replace("\\ ", r"\s+")
    m = re.search(start_re + r"\s*:?\s*", blob, flags=re.IGNORECASE)
    if not m:
        return ""
    tail = blob[m.end():]
    stop_positions = []
    for stop in stops:
        sm = re.search(re.escape(stop).replace("\\ ", r"\s+") + r"\s*:?", tail, flags=re.IGNORECASE)
        if sm:
            stop_positions.append(sm.start())
    if stop_positions:
        tail = tail[: min(stop_positions)]
    return _clean_text(tail)


def _looks_like_header(cells: List[str]) -> bool:
    blob = _norm(" ".join(cells))
    return any(token in blob for token in ("apolice susep", "resultado por parcela", "status recibo", "data de vencimento"))


def _normalize_inadimplente_cells(cells: List[str]) -> Dict[str, str]:
    data = cells[1:] if cells and not _digits(cells[0]) and len(cells) >= 10 else cells[:]
    has_parcela = len(data) > 1 and bool(re.match(r"^\d+\s*/\s*\d+$", data[1]))
    if has_parcela:
        return {
            "recibo": data[0] if len(data) > 0 else "",
            "parcela": data[1] if len(data) > 1 else "",
            "apolice": data[2] if len(data) > 2 else "",
            "adesao": data[3] if len(data) > 3 else "",
            "endosso": data[4] if len(data) > 4 else "",
            "fim": data[5] if len(data) > 5 else "",
            "prev": data[6] if len(data) > 6 else "",
            "vencimento": data[7] if len(data) > 7 else "",
            "valor": data[8] if len(data) > 8 else "",
            "comissao": data[9] if len(data) > 9 else "",
        }
    return {
        "recibo": data[0] if len(data) > 0 else "",
        "parcela": "",
        "apolice": data[1] if len(data) > 1 else "",
        "adesao": data[2] if len(data) > 2 else "",
        "endosso": data[3] if len(data) > 3 else "",
        "fim": data[4] if len(data) > 4 else "",
        "prev": data[5] if len(data) > 5 else "",
        "vencimento": data[6] if len(data) > 6 else "",
        "valor": data[7] if len(data) > 7 else "",
        "comissao": data[8] if len(data) > 8 else "",
    }


def _safe_path_token(value: Any, default: str = "item") -> str:
    text = _norm(str(value or ""))
    text = re.sub(r"[^a-z0-9_-]+", "-", text).strip("-")
    return text[:80] or default


def build_boleto_storage_path(
    *,
    company_id: str,
    job_id: str,
    portal_key: str,
    recibo: str = "",
    cpf_cnpj: str = "",
    cliente_nome: str = "",
) -> str:
    """Caminho privado do boleto sem PII no nome do arquivo."""
    _ = cpf_cnpj, cliente_nome  # contrato explicito: nunca entram no path.
    company = _safe_path_token(company_id, "company")
    job = _safe_path_token(job_id, "job")
    portal = _safe_path_token(portal_key, "portal")
    receipt = _safe_path_token(_digits(recibo) or recibo, "boleto")
    return f"{company}/{portal}/{job}/boleto-{receipt}.pdf"


def extract_inadimplentes_from_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extrai a tela Allianz 'PARCELAS INADIMPLENTES' de linhas DOM genericas."""
    out: List[Dict[str, Any]] = []
    seen = set()
    for row in rows or []:
        raw_cells = row.get("cells") if isinstance(row, dict) else None
        cells = [_clean_text(c) for c in (raw_cells or []) if _clean_text(c)]
        if len(cells) < 7 or _looks_like_header(cells):
            continue
        data = _normalize_inadimplente_cells(cells)
        detail = _clean_text((row or {}).get("detail") or " ".join(cells))
        doc = _digits(_slice_between(detail, "CPF/CNPJ", ("Modalidade", "Filial", "Telefone", "E-mail")))
        if len(doc) not in (11, 14):
            mdoc = re.search(r"CPF/CNPJ\s*:?\s*([0-9.\-/ ]{11,24})", detail, flags=re.IGNORECASE)
            doc = _digits(mdoc.group(1)) if mdoc else ""
        name = _slice_between(detail, "Segurado", ("CPF/CNPJ", "Modalidade", "Filial"))
        recibo = _digits(data["recibo"])
        apolice = _digits(data["apolice"])
        vencimento = _date_like(data["vencimento"])
        valor = _parse_money_br(data["valor"])
        if not (recibo or apolice or doc or name):
            continue
        key = (recibo, apolice, doc, vencimento)
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "portal": "allianz_corretor",
            "recibo": recibo or data["recibo"],
            "parcela": _clean_text(data["parcela"]),
            "apolice_susep": apolice,
            "adesao": _clean_text(data["adesao"]),
            "endosso": _clean_text(data["endosso"]),
            "dt_fim_cobertura": _date_like(data["fim"]),
            "dt_prev_cancelamento": _date_like(data["prev"]),
            "vencimento": vencimento,
            "valor": valor,
            "comissao": _parse_money_br(data["comissao"]),
            "cliente_nome": name,
            "cpf_cnpj": doc,
            "modalidade": _slice_between(detail, "Modalidade", ("Filial", "Telefone", "E-mail")),
            "raw": {"cells": cells[:12], "detail": detail[:500]},
        })
    return out


def extract_recibos_from_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extrai recibos pendentes da tela Allianz 'LISTAGEM DE RECIBOS'."""
    pending: List[Dict[str, Any]] = []
    seen = set()
    for row in rows or []:
        raw_cells = row.get("cells") if isinstance(row, dict) else None
        cells = [_clean_text(c) for c in (raw_cells or []) if _clean_text(c)]
        if len(cells) < 8 or _looks_like_header(cells):
            continue
        blob = _norm(" ".join(cells))
        if "pendente" not in blob:
            continue
        recibo = _digits(cells[0]) or (_digits(cells[3]) if len(cells) > 3 else "")
        key = (recibo, cells[1] if len(cells) > 1 else "")
        if key in seen:
            continue
        seen.add(key)
        pending.append({
            "portal": "allianz_corretor",
            "recibo": recibo or cells[0],
            "parcela": cells[1] if len(cells) > 1 else "",
            "endosso": cells[2] if len(cells) > 2 else "",
            "tipo_recibo": cells[4] if len(cells) > 4 else "",
            "emissao": _date_like(cells[5] if len(cells) > 5 else ""),
            "vencimento": _date_like(cells[6] if len(cells) > 6 else ""),
            "valor": _parse_money_br(cells[7] if len(cells) > 7 else ""),
            "status": "Pendente",
            "data_status": _date_like(cells[9] if len(cells) > 9 else ""),
            "raw": {"cells": cells[:12]},
        })
    return pending


def _looks_like_recibos_list(text: str) -> bool:
    body = _norm(text)
    if "listagem de recibos" in body:
        return True
    return "recibo" in body and "parcela" in body and "status" in body and "pendente" in body


def _looks_like_ficha_gestao(text: str) -> bool:
    body = _norm(text)
    if "ficha de gestao" in body:
        return True
    if "carta inadimplencia" in body and ("tipo modelo" in body or "description" in body):
        return True
    return "ep - p- apolice" in body and "tipo modelo" in body and "description" in body


def _receipt_click_terms(item: Dict[str, Any]) -> List[str]:
    terms: List[str] = []
    for value in (item.get("recibo"), item.get("parcela"), item.get("vencimento")):
        text = _clean_text(value)
        if text and text not in terms:
            terms.append(text)
    if "Pendente" not in terms:
        terms.append("Pendente")
    return terms


def _summarize_download_debug(page_text: str, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Resumo curto da tela quando o fluxo de boleto nao acha o proximo controle."""
    text = _clean_text(page_text)
    low = _norm(text)
    keywords = (
        "lista recibos",
        "lista de recibos",
        "ficha gestao",
        "ficha de gestao",
        "historico da apolice",
        "resultado por parcela",
        "gestor cobranca",
        "pendentes",
        "operar",
    )
    first_hit = -1
    for key in keywords:
        pos = low.find(key)
        if pos >= 0 and (first_hit < 0 or pos < first_hit):
            first_hit = pos
    start = max(0, first_hit - 500) if first_hit >= 0 else 0
    snippet = text[start:start + 1800]

    scored: List[Dict[str, Any]] = []
    for action in actions or []:
        label = _clean_text(action.get("text") or action.get("aria") or action.get("title") or "")
        hay = _norm(" ".join([
            label,
            str(action.get("role") or ""),
            str(action.get("tag") or ""),
            str(action.get("cls") or ""),
            str(action.get("id") or ""),
        ]))
        if not label or len(label) > 160:
            continue
        score = 0
        for idx, key in enumerate(keywords):
            if key in hay:
                score += 100 - idx
        if not score:
            continue
        clean = {
            "text": label[:120],
            "tag": str(action.get("tag") or "")[:30],
            "role": str(action.get("role") or "")[:40],
            "id": str(action.get("id") or "")[:80],
            "cls": str(action.get("cls") or "")[:120],
            "x": action.get("x"),
            "y": action.get("y"),
        }
        scored.append({"score": score, **clean})
    scored.sort(key=lambda item: int(item.get("score") or 0), reverse=True)
    return {"text_snippet": snippet, "actions": scored[:20]}


def _merge_recibos_context(item: Dict[str, Any], page_text: str) -> Dict[str, Any]:
    """Completa dados exibidos no topo da LISTAGEM DE RECIBOS."""
    merged = dict(item or {})
    ramo = _slice_between(page_text, "Ramo", ("Nome", "Incluido Historico", "Incluido", "Tomador", "RECIBOS"))
    nome = _slice_between(page_text, "Nome", ("Incluido Historico", "Incluido", "Tomador", "RECIBOS"))
    apolice = _digits(_slice_between(page_text, "Apolice SUSEP", ("Endosso", "Ramo", "Nome")))
    if ramo and not _clean_text(merged.get("item_segurado")):
        merged["item_segurado"] = ramo
    if nome and not _clean_text(merged.get("cliente_nome")):
        merged["cliente_nome"] = nome
    if apolice and not _clean_text(merged.get("apolice_susep")):
        merged["apolice_susep"] = apolice
    return merged


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


async def _body_text(page) -> str:
    try:
        return await page.inner_text("body", timeout=5000)
    except Exception:  # noqa: BLE001
        return ""


async def _all_body_text(page) -> str:
    texts = []
    for frame in getattr(page, "frames", [page]):
        try:
            text = await frame.inner_text("body", timeout=2500)
            if text:
                texts.append(text)
        except Exception:  # noqa: BLE001
            continue
    if texts:
        return "\n".join(texts)
    return await _body_text(page)


async def _extract_visible_rows_from_context(context) -> List[Dict[str, Any]]:
    """DOM generico para tabelas Angular/Material/HTML comuns."""
    try:
        rows = await context.evaluate(
            """() => {
              const clean = t => (t || '').replace(/\\s+/g, ' ').trim();
              const vis = el => !!(el && (el.offsetParent || el.getClientRects().length));
              const rowSel = [
                'table tr', '[role=row]', 'mat-row', '.mat-row', '.cdk-row',
                '.datatable-body-row', '.ngx-datatable .datatable-row-wrapper'
              ].join(',');
              const all = [...document.querySelectorAll(rowSel)].filter(vis);
              return all.map((r, idx) => {
                const cellEls = [...r.querySelectorAll('th,td,[role=cell],mat-cell,.mat-cell,.datatable-body-cell')].filter(vis);
                let cells = cellEls.map(c => clean(c.innerText || c.textContent)).filter(Boolean);
                const text = clean(r.innerText || r.textContent);
                if (!cells.length && text) cells = text.split(/\\n| {2,}/).map(clean).filter(Boolean);
                let detail = text;
                for (let j = idx + 1; j < Math.min(all.length, idx + 6); j++) {
                  const n = all[j];
                  const nt = n ? clean(n.innerText || n.textContent) : '';
                  if (nt && /Segurado\\s*:|CPF\\/?CNPJ\\s*:/i.test(nt)) {
                    detail = `${detail} ${nt}`;
                    break;
                  }
                }
                return {cells, detail: detail.slice(0, 1200), text: text.slice(0, 1200)};
              }).filter(r => r.cells.length || r.text);
            }"""
        )
        return rows if isinstance(rows, list) else []
    except Exception:  # noqa: BLE001
        return []


def _attach_expanded_details(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for idx, row in enumerate(rows):
        text = _clean_text((row or {}).get("detail") or (row or {}).get("text") or "")
        if not re.search(r"Segurado\s*:|CPF/?CNPJ\s*:", text, flags=re.IGNORECASE):
            continue
        for j in range(idx - 1, max(-1, idx - 12), -1):
            prev = rows[j]
            prev_cells = [_clean_text(c) for c in (prev.get("cells") or [])]
            prev_blob = _clean_text(prev.get("detail") or " ".join(prev_cells))
            if re.search(r"\b\d{8,10}\b", prev_blob) and not re.search(r"CPF/?CNPJ\s*:", prev_blob, flags=re.IGNORECASE):
                prev["detail"] = _clean_text(f"{prev_blob} {text}")[:1200]
                break
    return rows


async def _extract_visible_rows(page) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for frame in getattr(page, "frames", [page]):
        rows.extend(await _extract_visible_rows_from_context(frame))
    return _attach_expanded_details(rows)


async def _click_text_candidate(page, candidates: Iterable[str], *, timeout_ms: int = 1200) -> bool:
    cand = [str(c or "") for c in candidates if str(c or "").strip()]
    if not cand:
        return False
    for frame in getattr(page, "frames", [page]):
        try:
            clicked = await frame.evaluate(
            """(candidates) => {
              const norm = s => (s || '').normalize('NFKD').replace(/[\\u0300-\\u036f]/g, '')
                .toLowerCase().replace(/\\s+/g, ' ').trim();
              const toks = s => norm(s).split(/\\s+/).filter(Boolean);
              const vis = el => !!(el && (el.offsetParent || el.getClientRects().length));
              const disabled = el => !!(el.disabled || el.getAttribute('aria-disabled') === 'true');
              const selectors = [
                'button', 'a', '[role=button]', '[role=menuitem]', 'li', 'mat-option',
                '.mat-menu-item', '.dropdown-item', '[onclick]', '[tabindex]',
                'span', 'div', 'nx-link', 'nx-action', 'nx-button', 'nx-menu-item',
                '[class*=menu]', '[class*=nav]', '[class*=item]'
              ].join(',');
              const els = [...document.querySelectorAll(selectors)].filter(el => vis(el) && !disabled(el));
              let best = null, bestScore = 0;
              for (const el of els) {
                const txt = norm(el.innerText || el.textContent || el.getAttribute('aria-label') || el.title || el.value);
                if (!txt || txt.length > 180) continue;
                for (const c of candidates) {
                  const want = norm(c);
                  if (!want) continue;
                  let score = txt === want ? 1000 : (txt.includes(want) || want.includes(txt) ? 100 : 0);
                  const ct = toks(want);
                  if (!score && ct.length) score = ct.filter(t => txt.includes(t)).length;
                  if (score > bestScore) { best = el; bestScore = score; }
                }
              }
              if (!best || bestScore <= 0) return false;
              const target = best.closest('button,a,[role=button],[role=menuitem],[onclick],[tabindex],li,nx-link,nx-action,nx-button,nx-menu-item,[class*=menu],[class*=nav],[class*=item]') || best;
              target.click();
              return true;
            }""",
            cand,
            )
            if clicked:
                await page.wait_for_timeout(timeout_ms)
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


async def _collect_visible_action_candidates(page) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for frame in getattr(page, "frames", [page]):
        try:
            rows = await frame.evaluate(
                """() => {
                  const clean = t => (t || '').replace(/\\s+/g, ' ').trim();
                  const vis = el => !!(el && (el.offsetParent || el.getClientRects().length));
                  const selectors = [
                    'button', 'a', '[role=button]', '[role=menuitem]', '[onclick]', '[tabindex]',
                    'li', 'td', 'span', 'div', 'nx-link', 'nx-action', 'nx-button', 'nx-menu-item',
                    '[class*=menu]', '[class*=nav]', '[class*=item]', '[class*=button]', '[class*=btn]'
                  ].join(',');
                  return [...document.querySelectorAll(selectors)]
                    .filter(el => vis(el))
                    .map(el => {
                      const rect = el.getBoundingClientRect();
                      const style = getComputedStyle(el);
                      const clickable = el.closest('button,a,[role=button],[role=menuitem],[onclick],[tabindex],li,nx-link,nx-action,nx-button,nx-menu-item,[class*=menu],[class*=nav],[class*=item],[class*=button],[class*=btn]');
                      return {
                        text: clean(el.innerText || el.textContent || el.getAttribute('aria-label') || el.title || el.value || ''),
                        tag: (el.tagName || '').toLowerCase(),
                        role: el.getAttribute('role') || '',
                        id: el.id || '',
                        cls: String(el.className || '').slice(0, 180),
                        aria: el.getAttribute('aria-label') || '',
                        title: el.title || '',
                        href: el.href || '',
                        x: Math.round(rect.x),
                        y: Math.round(rect.y),
                        w: Math.round(rect.width),
                        h: Math.round(rect.height),
                        cursor: style.cursor || '',
                        clickable_tag: clickable ? (clickable.tagName || '').toLowerCase() : '',
                        clickable_cls: clickable ? String(clickable.className || '').slice(0, 120) : ''
                      };
                    })
                    .filter(a => a.text && a.text.length <= 180)
                    .slice(0, 450);
                }"""
            )
            if isinstance(rows, list):
                out.extend([row for row in rows if isinstance(row, dict)])
        except Exception:  # noqa: BLE001
            continue
    return out


async def _record_download_debug(page, item: Dict[str, Any], evidence: Dict[str, Any], stage: str) -> None:
    try:
        page_text = await _all_body_text(page)
        actions = await _collect_visible_action_candidates(page)
        summary = _summarize_download_debug(page_text, actions)
        try:
            url = page.url
        except Exception:  # noqa: BLE001
            url = ""
        summary.update({
            "stage": stage,
            "url": url,
            "item": {
                "recibo": item.get("recibo"),
                "parcela": item.get("parcela"),
                "apolice_susep": item.get("apolice_susep"),
                "vencimento": item.get("vencimento"),
            },
        })
        evidence.setdefault("download_debug", []).append(summary)
    except Exception as e:  # noqa: BLE001
        evidence.setdefault("download_notes", []).append(f"debug download falhou: {type(e).__name__}")


async def _click_row_candidate(page, candidates: Iterable[str], *, timeout_ms: int = 1200) -> bool:
    cand = [str(c or "") for c in candidates if str(c or "").strip()]
    if not cand:
        return False
    for frame in getattr(page, "frames", [page]):
        try:
            clicked = await frame.evaluate(
                """(candidates) => {
                  const norm = s => (s || '').normalize('NFKD').replace(/[\\u0300-\\u036f]/g, '')
                    .toLowerCase().replace(/\\s+/g, ' ').trim();
                  const digits = s => String(s || '').replace(/\\D+/g, '');
                  const vis = el => !!(el && (el.offsetParent || el.getClientRects().length));
                  const rows = [...document.querySelectorAll('tr,[role=row],.datatable-body-row,.datatable-row-wrapper,li')]
                    .filter(vis);
                  let best = null, bestScore = 0;
                  for (const row of rows) {
                    const raw = row.innerText || row.textContent || '';
                    const text = norm(raw);
                    if (!text || text.length > 900) continue;
                    if (/apolice susep|status recibo|tipo modelo|description/.test(text)) continue;
                    let score = 0;
                    for (const c of candidates) {
                      const want = norm(c);
                      const wantDigits = digits(c);
                      if (!want) continue;
                      if (wantDigits && wantDigits.length >= 6 && digits(raw).includes(wantDigits)) score += 1000;
                      else if (text.includes(want)) score += Math.max(20, want.length);
                    }
                    if (score > bestScore) { best = row; bestScore = score; }
                  }
                  if (!best || bestScore <= 0) return false;
                  const target = best.querySelector('button,a,[role=button],[onclick],[tabindex],img') || best;
                  target.click();
                  return true;
                }""",
                cand,
            )
            if clicked:
                await page.wait_for_timeout(timeout_ms)
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


async def _wait_until_recibos_list(page, timeout_ms: int = 12000) -> bool:
    deadline = timeout_ms // 600
    for _ in range(max(1, deadline)):
        if _looks_like_recibos_list(await _all_body_text(page)):
            return True
        await page.wait_for_timeout(600)
    return False


async def _wait_until_ficha_gestao(page, timeout_ms: int = 12000) -> bool:
    deadline = timeout_ms // 600
    for _ in range(max(1, deadline)):
        if _looks_like_ficha_gestao(await _all_body_text(page)):
            return True
        await page.wait_for_timeout(600)
    return False


async def _click_text_maybe_popup(page, candidates: Iterable[str], *, timeout_ms: int = 8000):
    clicked = False
    try:
        async with page.expect_popup(timeout=timeout_ms) as popup_info:
            clicked = await _click_text_candidate(page, candidates, timeout_ms=800)
        popup = await popup_info.value
        try:
            await popup.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
        except Exception:  # noqa: BLE001
            pass
        await popup.wait_for_timeout(1200)
        return popup
    except Exception:  # noqa: BLE001
        if clicked:
            await page.wait_for_timeout(1500)
            return page
    if await _click_text_candidate(page, candidates, timeout_ms=1500):
        return page
    return None


async def _scroll_pdf_regions(page) -> None:
    for frame in getattr(page, "frames", [page]):
        try:
            await frame.evaluate(
                """() => {
                  window.scrollTo(0, document.body.scrollHeight);
                  const els = [...document.querySelectorAll('*')];
                  for (const el of els) {
                    const style = getComputedStyle(el);
                    const scrollable = /(auto|scroll)/.test(style.overflowY || '') && el.scrollHeight > el.clientHeight + 20;
                    if (scrollable) el.scrollTop = el.scrollHeight;
                  }
                }"""
            )
        except Exception:  # noqa: BLE001
            continue
    await page.wait_for_timeout(700)


async def _click_pdf_icon_candidate(page) -> bool:
    await _scroll_pdf_regions(page)
    for frame in getattr(page, "frames", [page]):
        try:
            clicked = await frame.evaluate(
                """() => {
                  const vis = el => !!(el && (el.offsetParent || el.getClientRects().length));
                  const hay = el => [
                    el.innerText, el.textContent, el.getAttribute('aria-label'), el.title,
                    el.alt, el.src, el.href, el.className, el.id
                  ].join(' ');
                  const selectors = [
                    'a[download]', 'a[href*=".pdf" i]', 'a[href*="pdf" i]',
                    'img[src*="pdf" i]', 'img[alt*="pdf" i]', 'img[title*="pdf" i]',
                    'button', '[role=button]', '[onclick]', '[tabindex]',
                    '[class*="pdf" i]', '[id*="pdf" i]'
                  ].join(',');
                  const els = [...document.querySelectorAll(selectors)].filter(vis);
                  const scored = els.map(el => {
                    const text = hay(el);
                    const r = el.getBoundingClientRect();
                    let score = 0;
                    if (/\\.pdf|pdf|adobe|acrobat/i.test(text)) score += 100;
                    if (/download|baixar|salvar|detalhe/i.test(text)) score += 30;
                    if ((el.tagName || '').toLowerCase() === 'img') score += 20;
                    if (r.left > window.innerWidth * 0.42) score += 80;
                    if (r.top > window.innerHeight * 0.25) score += 25;
                    if (r.width >= 20 && r.height >= 20) score += 10;
                    return {el, score};
                  }).filter(x => x.score > 0).sort((a, b) => b.score - a.score);
                  if (!scored.length) return false;
                  const best = scored[0].el;
                  const target = best.closest('a,button,[role=button],[onclick],[tabindex]') || best;
                  target.scrollIntoView({block: 'center', inline: 'center'});
                  target.click();
                  return true;
                }"""
            )
            if clicked:
                await page.wait_for_timeout(800)
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


async def _fill_global_search(page, value: str) -> bool:
    query = _clean_text(value)
    if not query:
        return False
    try:
        filled = await page.evaluate(
            """(value) => {
              const norm = s => (s || '').normalize('NFKD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase();
              const vis = el => !!(el && (el.offsetParent || el.getClientRects().length));
              const inputs = [...document.querySelectorAll('input')].filter(i => vis(i) && (i.type || '').toLowerCase() !== 'password');
              const best = inputs.find(i => {
                const hay = norm([i.type, i.placeholder, i.getAttribute('aria-label'), i.id, i.name].join(' '));
                return /busca|buscar|pesquis|search|cliente|cpf|apolice|recibo/.test(hay);
              }) || inputs[0];
              if (!best) return false;
              best.focus();
              best.value = value;
              best.dispatchEvent(new Event('input', {bubbles: true}));
              best.dispatchEvent(new Event('change', {bubbles: true}));
              return true;
            }""",
            query,
        )
        if not filled:
            return False
        await page.wait_for_timeout(500)
        try:
            await page.keyboard.press("Enter")
        except Exception:  # noqa: BLE001
            pass
        await page.wait_for_timeout(1500)
        return True
    except Exception:  # noqa: BLE001
        return False


async def _wait_until_text(page, tokens: Iterable[str], timeout_ms: int = 12000) -> bool:
    wanted = [_norm(t) for t in tokens if _norm(t)]
    if not wanted:
        return False
    deadline = timeout_ms // 600
    for _ in range(max(1, deadline)):
        text = _norm(await _body_text(page))
        if all(t in text for t in wanted):
            return True
        await page.wait_for_timeout(600)
    return False


def _looks_like_inadimplentes_result(text: str) -> bool:
    body = _norm(text)
    if "resultado por parcela" in body:
        return True
    if "segurado:" in body and "cpf/cnpj" in body:
        return True
    table_signals = ("apolice susep", "vcto", "premio", "recibo")
    return sum(1 for token in table_signals if token in body) >= 2


def _looks_like_inadimplentes_totals(text: str) -> bool:
    body = _norm(text)
    if "resultado - totais" in body:
        return True
    return "qtd.apolices" in body and "qtd.pcs" in body and "premio" in body


async def _wait_until_inadimplentes_result(page, timeout_ms: int = 12000) -> bool:
    deadline = timeout_ms // 600
    for _ in range(max(1, deadline)):
        if _looks_like_inadimplentes_result(await _all_body_text(page)):
            return True
        await page.wait_for_timeout(600)
    return False


async def _wait_for_inadimplencias_entry(page, timeout_ms: int = 12000) -> bool:
    deadline = timeout_ms // 600
    for _ in range(max(1, deadline)):
        text = _norm(await _all_body_text(page))
        if "inadimplencias" in text or _looks_like_inadimplentes_totals(text) or _looks_like_inadimplentes_result(text):
            return True
        await page.wait_for_timeout(600)
    return False


async def _click_first_totals_row(page) -> bool:
    for frame in getattr(page, "frames", [page]):
        try:
            clicked = await frame.evaluate(
                """() => {
                  const clean = t => (t || '').replace(/\\s+/g, ' ').trim();
                  const vis = el => !!(el && (el.offsetParent || el.getClientRects().length));
                  const rows = [...document.querySelectorAll('tr,[role=row]')].filter(vis);
                  for (const row of rows) {
                    const text = clean(row.innerText || row.textContent);
                    if (!text || text.length > 260) continue;
                    if (/^\\d+\\s+\\d{4}\\s+-\\s+/.test(text) && /\\d+,\\d{2}/.test(text)) {
                      row.click();
                      return true;
                    }
                  }
                  return false;
                }"""
            )
            if clicked:
                await page.wait_for_timeout(2500)
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


async def _open_parcela_from_totals_if_needed(page, evidence: Dict[str, Any]) -> bool:
    text = await _all_body_text(page)
    if _looks_like_inadimplentes_result(text):
        return True
    if not _looks_like_inadimplentes_totals(text):
        return False
    if await _click_first_totals_row(page):
        if await _wait_until_inadimplentes_result(page, timeout_ms=8000):
            evidence["totals_row_opened"] = True
            return True
    evidence["totals_row_opened"] = False
    return False


async def _expand_inadimplente_details(page, max_items: int = 10) -> int:
    expanded = 0
    for frame in getattr(page, "frames", [page]):
        try:
            loc = frame.locator('img[id^="img_tdExtdInfo_"], img[alt*="extendida" i], img[title*="extendida" i]')
            count = min(await loc.count(), max_items - expanded)
            for i in range(max(0, count)):
                await loc.nth(i).click(timeout=2500)
                expanded += 1
                await page.wait_for_timeout(300)
            if expanded >= max_items:
                break
        except Exception:  # noqa: BLE001
            continue
    if expanded:
        await page.wait_for_timeout(3500)
    return expanded


async def _semantic_navigation_review(page, goal: str, params: Dict[str, Any], evidence: Dict[str, Any]) -> JourneyResult:
    """Usa o cerebro adaptativo existente quando os atalhos semanticos nao bastam."""
    try:
        from portal_worker.adaptive import run_adaptive

        collected = {
            "portal": "allianz_corretor",
            "tarefa": "cobranca_sweep",
            "orientacao": (
                "Navegue no AllianzNet do corretor ate a tela de cobranca/inadimplencia/listagem "
                "de recibos. Nao envie mensagens, nao finalize alteracoes no portal e pare quando "
                "a tela exibir parcelas inadimplentes, resultado por parcela, recibos pendentes ou "
                "gestor cobranca."
            ),
            "max_boletos": params.get("max_boletos"),
        }
        return await run_adaptive(page, goal, collected, evidence, max_steps=6, confirm=True)
    except Exception as e:  # noqa: BLE001
        return JourneyResult(status="needs_human", message=f"navegacao adaptativa falhou: {type(e).__name__}")


async def _ensure_inadimplentes_page(page, params: Dict[str, Any], evidence: Dict[str, Any]) -> bool:
    await _wait_for_inadimplencias_entry(page, timeout_ms=10000)
    text = _norm(await _all_body_text(page))
    if _looks_like_inadimplentes_result(text):
        return True
    if await _open_parcela_from_totals_if_needed(page, evidence):
        return True

    # Tenta caminho semantico pelo menu/atalho da home Allianz.
    candidates = (
        "INADIMPLÊNCIAS",
        "INADIMPLENCIAS",
        "Parcelas Inadimplentes",
        "Inadimplentes",
        "CobranÃ§a",
        "Cobranca",
        "GestÃ£o",
        "Gestao",
        "Recibo/Pagamento",
        "Pagamentos",
    )
    for label in candidates:
        if await _click_text_candidate(page, [label]):
            if await _wait_until_inadimplentes_result(page, timeout_ms=6500):
                return True
            if await _open_parcela_from_totals_if_needed(page, evidence):
                return True

    # Tenta busca global do proprio portal.
    for query in ("Parcelas Inadimplentes", "inadimplentes", "cobranca"):
        if await _fill_global_search(page, query):
            await _click_text_candidate(page, ("Parcelas Inadimplentes", "Recibo/Pagamento", "CobranÃ§a", "Cobranca"))
            if await _wait_until_inadimplentes_result(page, timeout_ms=7500):
                return True
            if await _open_parcela_from_totals_if_needed(page, evidence):
                return True

    adaptive = await _semantic_navigation_review(
        page,
        "Abra a area Allianz de parcelas inadimplentes/cobranca e pare na lista de atrasados.",
        params,
        evidence,
    )
    text = _norm(await _all_body_text(page))
    evidence["cobranca_navigation"] = {"adaptive_status": adaptive.status, "message": adaptive.message}
    return _looks_like_inadimplentes_result(text) or await _open_parcela_from_totals_if_needed(page, evidence)


async def _download_current_pdf(page, item: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    """Tenta baixar o PDF que estiver acessivel na tela atual e subir para storage."""
    upload = params.get("_upload_blob")
    path = build_boleto_storage_path(
        company_id=str(params.get("_company_id") or "company"),
        job_id=str(params.get("_job_id") or "job"),
        portal_key=str(params.get("_portal_key") or "allianz_corretor"),
        recibo=str(item.get("recibo") or ""),
        cpf_cnpj=str(item.get("cpf_cnpj") or ""),
        cliente_nome=str(item.get("cliente_nome") or ""),
    )
    buttons = (
        "Download",
        "Baixar",
        "Salvar",
        "Carta InadimplÃªncia - Aviso",
        "Carta Inadimplencia - Aviso",
        "Acesso detalhe extendido",
        "Boleto",
    )
    try:
        async with page.expect_download(timeout=15000) as dl:
            clicked = await _click_pdf_icon_candidate(page)
            if not clicked:
                clicked = await _click_text_candidate(page, buttons, timeout_ms=800)
            if not clicked:
                clicked = await page.evaluate(
                    """() => {
                      const vis = el => !!(el && (el.offsetParent || el.getClientRects().length));
                      const els = [...document.querySelectorAll('a[download], a[href*=".pdf"], button, [role=button]')].filter(vis);
                      const hit = els.find(e => /download|baixar|pdf|boleto|carta/i.test(
                        [e.innerText, e.textContent, e.getAttribute('aria-label'), e.title, e.href].join(' ')
                      ));
                      if (!hit) return false;
                      hit.click();
                      return true;
                    }"""
                )
            if not clicked:
                raise RuntimeError("nenhum controle de download encontrado")
        download = await dl.value
        tmp = await download.path()
        data = Path(str(tmp)).read_bytes() if tmp else b""
        if not data:
            return {"ok": False, "reason": "download vazio", "storage_path": None}
        if callable(upload):
            saved = await upload(path, data, "application/pdf")
            return {"ok": bool(saved), "storage_path": saved or path, "bytes": len(data)}
        return {"ok": True, "storage_path": path, "bytes": len(data), "not_uploaded": True}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "reason": f"{type(e).__name__}: {str(e)[:160]}", "storage_path": None}


async def _open_receipts_for_item(page, item: Dict[str, Any], evidence: Dict[str, Any]) -> bool:
    """Fluxo Allianz: linha do inadimplente -> Lista Recibos, com busca como fallback."""
    if _looks_like_recibos_list(await _all_body_text(page)):
        return True

    await _click_row_candidate(page, _receipt_click_terms(item), timeout_ms=900)
    if await _click_text_candidate(page, ("Lista Recibos", "Lista de Recibos"), timeout_ms=2200):
        if await _wait_until_recibos_list(page, timeout_ms=9000):
            evidence.setdefault("download_notes", []).append("lista recibos aberta a partir da linha do inadimplente")
            return True

    queries = [
        item.get("cpf_cnpj"),
        item.get("cliente_nome"),
        item.get("apolice_susep"),
        item.get("recibo"),
    ]
    for query in [q for q in queries if q]:
        if not await _fill_global_search(page, str(query)):
            continue
        await _click_text_candidate(page, ("Clientes", "CPF/CNPJ", "Nome/RazÃ£o Social", "Recibo/Pagamento", "ApÃ³lices/Proposta"))
        await page.wait_for_timeout(1500)
        await _click_text_candidate(page, ("Operar", "Lista Recibos", "Lista de Recibos", "HistÃ³rico da ApÃ³lice"))
        await _click_text_candidate(page, ("Lista Recibos", "Lista de Recibos", "Recibos", "Pendentes"))
        if await _wait_until_recibos_list(page, timeout_ms=9000):
            return True
    await _record_download_debug(page, item, evidence, "lista_recibos_not_opened")
    evidence.setdefault("download_notes", []).append("nao abriu listagem de recibos para item")
    return False


async def _open_ficha_gestao_for_item(page, item: Dict[str, Any], evidence: Dict[str, Any]):
    if _looks_like_ficha_gestao(await _all_body_text(page)):
        return page
    await _click_row_candidate(page, _receipt_click_terms(item), timeout_ms=900)
    target = await _click_text_maybe_popup(page, ("Ficha Gestao", "Ficha de Gestao"), timeout_ms=9000)
    if target and await _wait_until_ficha_gestao(target, timeout_ms=12000):
        evidence.setdefault("download_notes", []).append("ficha gestao aberta")
        return target
    evidence.setdefault("download_notes", []).append("ficha gestao nao abriu")
    return None


async def _select_carta_inadimplencia(page, evidence: Dict[str, Any]) -> bool:
    if await _click_row_candidate(page, ("Carta Inadimplencia - Aviso", "Carta Inadimplencia"), timeout_ms=1600):
        evidence.setdefault("download_notes", []).append("carta inadimplencia selecionada por linha")
        return True
    if await _click_text_candidate(page, ("Carta Inadimplencia - Aviso", "Carta Inadimplencia"), timeout_ms=1600):
        evidence.setdefault("download_notes", []).append("carta inadimplencia selecionada por texto")
        return True
    evidence.setdefault("download_notes", []).append("carta inadimplencia nao encontrada")
    return False


async def _download_boletos(page, items: List[Dict[str, Any]], params: Dict[str, Any], evidence: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        max_boletos = max(1, int(params.get("max_boletos") or params.get("max_boletos_por_execucao") or 10))
    except Exception:  # noqa: BLE001
        max_boletos = 10
    for idx, item in enumerate(items[:max_boletos]):
        result = {"recibo": item.get("recibo"), "cpf_cnpj": item.get("cpf_cnpj"), "ok": False}
        try:
            if idx > 0:
                await page.goto(ALLIANZ_PRIVATE_HOME, wait_until="domcontentloaded")
                await page.wait_for_timeout(1500)
            opened = await _open_receipts_for_item(page, item, evidence)
            if opened:
                item = _merge_recibos_context(item, await _all_body_text(page))
                rows = await _extract_visible_rows(page)
                pendentes = extract_recibos_from_rows(rows)
                result["recibos_pendentes"] = pendentes[:5]
                await _click_row_candidate(page, _receipt_click_terms(item), timeout_ms=1000)
                ficha = await _open_ficha_gestao_for_item(page, item, evidence)
                if ficha:
                    if await _select_carta_inadimplencia(ficha, evidence):
                        await ficha.wait_for_timeout(1200)
                    download = await _download_current_pdf(ficha, item, params)
                    result.update(download)
                    if ficha is not page:
                        try:
                            await ficha.close()
                        except Exception:  # noqa: BLE001
                            pass
                else:
                    result["reason"] = "ficha gestao nao encontrada"
                out.append(result)
                continue
            else:
                result["reason"] = "listagem de recibos nao encontrada"
        except Exception as e:  # noqa: BLE001
            result["reason"] = f"{type(e).__name__}: {str(e)[:160]}"
        out.append(result)
    return out


async def cobranca_sweep(page, params: Dict[str, Any], evidence: Dict[str, Any]) -> JourneyResult:
    """SPEC-023 P3: varre cobranca Allianz, extrai atrasados e baixa boletos quando possivel."""
    login = await login_check(page, params, evidence)
    if login.status != "done":
        return login

    evidence["logged_in"] = True
    if not await _ensure_inadimplentes_page(page, params, evidence):
        try:
            from portal_worker.adaptive import _dump_dom

            evidence["debug_dom"] = await _dump_dom(page)
        except Exception:  # noqa: BLE001
            evidence["body_text"] = (await _body_text(page))[:1200]
        return JourneyResult(
            status="needs_human",
            captured={"logged_in": True, "stage": "inadimplentes_nao_localizado"},
            message="nao consegui localizar a area de parcelas inadimplentes Allianz",
        )

    try:
        max_expand = max(1, int(params.get("max_boletos") or params.get("max_boletos_por_execucao") or 10))
    except Exception:  # noqa: BLE001
        max_expand = 10
    evidence["inadimplentes_details_expanded"] = await _expand_inadimplente_details(page, max_items=max_expand)

    rows = await _extract_visible_rows(page)
    segurado_rows = [
        _clean_text((r.get("detail") or r.get("text") or ""))[:500]
        for r in rows
        if re.search(r"Segurado\s*:|CPF/?CNPJ\s*:", _clean_text((r.get("detail") or r.get("text") or "")), flags=re.IGNORECASE)
    ]
    evidence["inadimplentes_detail_rows_seen"] = len(segurado_rows)
    items = extract_inadimplentes_from_rows(rows)
    evidence["inadimplentes_rows_seen"] = len(rows)
    evidence["inadimplentes_count"] = len(items)
    evidence["inadimplentes_sample"] = [
        {
            "recibo": i.get("recibo"),
            "apolice_susep": i.get("apolice_susep"),
            "vencimento": i.get("vencimento"),
            "valor": i.get("valor"),
            "cliente_nome": i.get("cliente_nome"),
            "cpf_cnpj": i.get("cpf_cnpj"),
        }
        for i in items[:5]
    ]

    text = _norm(await _body_text(page))
    if not items:
        if any(token in text for token in ("nenhum registro", "nao ha", "sem registros", "0 registro")):
            return JourneyResult(
                status="done",
                captured={"logged_in": True, "inadimplentes": [], "boletos": [], "portal": "allianz_corretor"},
                message="nenhuma parcela inadimplente encontrada",
            )
        return JourneyResult(
            status="needs_human",
            captured={"logged_in": True, "stage": "sem_linhas_extraiveis"},
            message="tela de inadimplentes encontrada, mas nao consegui extrair linhas",
        )

    download_boletos = bool(params.get("download_boletos", True))
    boletos: List[Dict[str, Any]] = []
    if download_boletos:
        boletos = await _download_boletos(page, items, params, evidence)
        ok_count = sum(1 for b in boletos if b.get("ok"))
        evidence["boletos_download_ok"] = ok_count
        evidence["boletos_download_attempts"] = len(boletos)
        if params.get("require_downloads", True) and ok_count == 0:
            return JourneyResult(
                status="needs_human",
                captured={
                    "logged_in": True,
                    "stage": "boletos_nao_baixados",
                    "inadimplentes": items,
                    "boletos": boletos,
                },
                message="inadimplentes extraidos, mas o download de boletos precisa de revisao humana",
            )

    return JourneyResult(
        status="done",
        captured={
            "logged_in": True,
            "portal": "allianz_corretor",
            "inadimplentes": items,
            "boletos": boletos,
        },
        message=f"cobranca Allianz concluida: {len(items)} inadimplente(s), {sum(1 for b in boletos if b.get('ok'))} boleto(s)",
    )
