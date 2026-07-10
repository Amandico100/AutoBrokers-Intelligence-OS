"""Journey AllianzNet corretor (SPEC-023 P1).

P1 cobre apenas login autenticado e classificacao segura da sessao. A jornada de
cobranca (`cobranca_sweep`) vem depois e deve reusar a sessao persistida aqui.
"""
from __future__ import annotations

import re
import html
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

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


def extract_totals_from_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extrai os ramos da tela Allianz 'RESULTADO - TOTAIS'."""
    out: List[Dict[str, Any]] = []
    seen = set()
    for row in rows or []:
        raw_cells = row.get("cells") if isinstance(row, dict) else None
        cells = [_clean_text(c) for c in (raw_cells or []) if _clean_text(c)]
        if len(cells) < 6 or _looks_like_header(cells):
            continue
        if not _digits(cells[0]) or not re.match(r"^\d{4}\s+-\s+", cells[1]):
            continue
        key = (cells[0], cells[1])
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "codigo_corretor": _digits(cells[0]),
            "ramo": cells[1],
            "ramo_br": cells[2] if len(cells) > 2 else "",
            "qtd_apolices": int(_digits(cells[3]) or 0) if len(cells) > 3 else 0,
            "qtd_pcs": int(_digits(cells[4]) or 0) if len(cells) > 4 else 0,
            "premio": _parse_money_br(cells[5] if len(cells) > 5 else ""),
            "comissao": _parse_money_br(cells[6] if len(cells) > 6 else ""),
            "raw": {"cells": cells[:8]},
        })
    return out


def _looks_like_recibos_list(text: str) -> bool:
    body = _norm(text)
    if "listagem de recibos" in body:
        return True
    return "recibo" in body and "parcela" in body and "status" in body and "pendente" in body


def _looks_like_ficha_gestao(text: str) -> bool:
    # Tela real (print p13): header 'Nota | Indexar', titulo 'EP - P- APÓLICE -
    # <numero> - 16 (16) registros', colunas 'Fecha | Tipo Modelo | Descripcion
    # | Usuario' (grafia espanhola — NAO 'description').
    body = _norm(text)
    if "ficha de gestao" in body:
        return True
    if "carta inadimplencia" in body and ("tipo modelo" in body or "descripcion" in body or "description" in body):
        return True
    if "indexar" in body and "registros" in body and ("tipo modelo" in body or "descripcion" in body):
        return True
    return "ep - p- apolice" in body and "tipo modelo" in body


def _looks_like_policy_context(text: str) -> bool:
    body = _norm(text)
    if "resultado por parcela" in body or "parcelas inadimplentes" in body:
        return False
    tab_hits = sum(1 for token in ("gerais", "segurado", "dados risco", "coberturas", "clausulas", "resumo") if token in body)
    action_hits = sum(1 for token in ("lista recibos", "ficha gestao", "lista sinistros", "historico da apolice") if token in body)
    return tab_hits >= 3 or action_hits >= 2


def _receipt_click_terms(item: Dict[str, Any]) -> List[str]:
    terms: List[str] = []
    for value in (item.get("recibo"), item.get("parcela"), item.get("vencimento")):
        text = _clean_text(value)
        if text and text not in terms:
            terms.append(text)
    if "Pendente" not in terms:
        terms.append("Pendente")
    return terms


def _policy_search_terms(item: Dict[str, Any]) -> List[str]:
    """NOME primeiro: é o fluxo que o corretor executa manualmente com sucesso
    (prints 2026-07-10 — barra Pesquisar + categoria 'Nome / Razão Social').
    CPF fica de fallback (categoria CPF/CNPJ devolveu 'Não foram encontrados
    resultados' em produção) e recibo por último. A apólice SUSEP concatenada
    (19 dígitos) NÃO entra: o portal responde 'Apólice inexistente' para esse
    formato (job b693d9de)."""
    terms: List[str] = []
    for value in (item.get("cliente_nome"), item.get("cpf_cnpj"), item.get("recibo")):
        text = _clean_text(value)
        if text and text not in terms:
            terms.append(text)
    return terms


def search_result_is_empty(text: str) -> bool:
    """Detecta o modal de busca sem resultados da Allianz (que BLOQUEIA a tela
    até clicar FECHAR — causa raiz do job a9f4b375: buscas seguintes falhavam)."""
    low = _norm(text)
    return any(
        token in low
        for token in (
            "nao foram encontrados resultados",
            "nenhum resultado encontrado",
            "nenhum registro encontrado",
            "nao encontramos resultados",
            "apolice inexistente",
            "cliente inexistente",
        )
    )


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


def _score_global_search_input(meta: Dict[str, Any]) -> int:
    hay = _norm(" ".join([
        str(meta.get("placeholder") or ""),
        str(meta.get("aria") or ""),
        str(meta.get("id") or ""),
        str(meta.get("name") or ""),
    ]))
    near = _norm(str(meta.get("near_text") or ""))
    score = 0
    if re.search(r"busca|buscar|pesquis|search|cliente|cpf|apolice|recibo", hay):
        score += 180
    try:
        y = int(float(meta.get("y") or 0))
        w = int(float(meta.get("w") or 0))
    except Exception:  # noqa: BLE001
        y, w = 0, 0
    if y < 260 and w > 220:
        score += 90
    if w > 320:
        score += 30
    if re.search(r"filtro\s+susep|codigo corretor|premio ramo|comissao ramo", near):
        score -= 160
    return score


def _summarize_policy_search_debug(inputs: List[Dict[str, Any]]) -> Dict[str, Any]:
    scored: List[Dict[str, Any]] = []
    for meta in inputs or []:
        clean = {
            "placeholder": str(meta.get("placeholder") or "")[:80],
            "id": str(meta.get("id") or "")[:80],
            "name": str(meta.get("name") or "")[:80],
            "value": str(meta.get("value") or "")[:120],
            "x": meta.get("x"),
            "y": meta.get("y"),
            "w": meta.get("w"),
            "h": meta.get("h"),
            "near_text": _clean_text(meta.get("near_text") or "")[:180],
        }
        scored.append({"score": _score_global_search_input(meta), **clean})
    scored.sort(key=lambda item: int(item.get("score") or 0), reverse=True)
    return {"inputs": scored[:12]}


def _score_policy_search_node(meta: Dict[str, Any]) -> int:
    hay = _norm(" ".join([
        str(meta.get("text") or ""),
        str(meta.get("aria") or ""),
        str(meta.get("title") or ""),
        str(meta.get("id") or ""),
        str(meta.get("cls") or ""),
        str(meta.get("tag") or ""),
        str(meta.get("html") or "")[:300],
    ]))
    score = 0
    if re.search(r"search|pesquis|buscar|lupa|magnif", hay):
        score += 200
    if re.search(r"info|help|ajuda", hay):
        score -= 120
    if str(meta.get("tag") or "").lower() in ("button", "a"):
        score += 40
    if str(meta.get("role") or "").lower() == "button":
        score += 40
    try:
        x = int(float(meta.get("x") or 0))
        w = int(float(meta.get("w") or 0))
        h = int(float(meta.get("h") or 0))
    except Exception:  # noqa: BLE001
        x, w, h = 0, 0, 0
    if x >= 540:
        score += 30
    if 12 <= w <= 80 and 12 <= h <= 80:
        score += 20
    return score


def _summarize_policy_search_component(nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
    scored: List[Dict[str, Any]] = []
    for meta in nodes or []:
        clean = {
            "tag": str(meta.get("tag") or "")[:30],
            "role": str(meta.get("role") or "")[:50],
            "id": str(meta.get("id") or "")[:100],
            "cls": str(meta.get("cls") or "")[:160],
            "text": _clean_text(meta.get("text") or "")[:120],
            "aria": str(meta.get("aria") or "")[:120],
            "title": str(meta.get("title") or "")[:120],
            "x": meta.get("x"),
            "y": meta.get("y"),
            "w": meta.get("w"),
            "h": meta.get("h"),
            "html": _clean_text(meta.get("html") or "")[:500],
        }
        scored.append({"score": _score_policy_search_node(meta), **clean})
    scored.sort(key=lambda item: int(item.get("score") or 0), reverse=True)
    return {"nodes": scored[:30]}


def _sanitize_trace_url(url: Any) -> str:
    text = str(url or "").strip()
    if not text:
        return ""
    try:
        parts = urlsplit(text)
        blocked = {
            "access_token",
            "auth",
            "authorization",
            "cookie",
            "jwt",
            "password",
            "pwd",
            "refresh_token",
            "senha",
            "session",
            "token",
        }
        query = [
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if key.strip().lower() not in blocked
        ]
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))[:600]
    except Exception:  # noqa: BLE001
        redacted = re.sub(r"(?i)(token|senha|password|authorization|session)=([^&#]+)", r"\1=<redacted>", text)
        return redacted[:600]


def _score_network_event(event: Dict[str, Any]) -> int:
    url = _norm(str(event.get("url") or ""))
    score = 0
    if "application/static" in url:
        score += 320
    if "filemanagement" in url or "ngx-file-management" in url:
        score += 280
    if re.search(r"apolice|recibo|cobranca|gestao|consulta|inadimpl|search|azr|policy", url):
        score += 180
    if str(event.get("kind") or "") == "response":
        score += 10
    if re.search(r"\.(png|jpg|jpeg|gif|svg|css|woff2?|ico)(\?|$)", url):
        score -= 220
    return score


def _summarize_network_trace(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    cleaned: List[Dict[str, Any]] = []
    for event in events or []:
        url = _sanitize_trace_url(event.get("url"))
        if not url:
            continue
        clean = {
            "kind": str(event.get("kind") or "")[:20],
            "method": str(event.get("method") or "")[:10],
            "status": event.get("status"),
            "url": url,
        }
        cleaned.append({"score": _score_network_event(clean), **clean})
    cleaned.sort(key=lambda item: int(item.get("score") or 0), reverse=True)
    return {"event_count": len(events or []), "events": cleaned[:30]}


def _score_policy_result_node(meta: Dict[str, Any], item: Dict[str, Any]) -> int:
    text = _clean_text(meta.get("text") or "")
    hay = _norm(" ".join([
        text,
        str(meta.get("tag") or ""),
        str(meta.get("role") or ""),
        str(meta.get("id") or ""),
        str(meta.get("cls") or ""),
        str(meta.get("onclick") or ""),
        str(meta.get("href") or ""),
        str(meta.get("cursor") or ""),
    ]))
    digits = _digits(" ".join([text, str(meta.get("href") or ""), str(meta.get("onclick") or "")]))
    apolice = _digits(item.get("apolice_susep"))
    recibo = _digits(item.get("recibo"))
    score = 0
    if apolice and apolice in digits:
        score += 300
    if recibo and recibo in digits:
        score += 220
    if str(meta.get("cursor") or "").lower() == "pointer":
        score += 60
    if str(meta.get("onclick") or "").strip():
        score += 80
    if str(meta.get("href") or "").strip():
        score += 80
    if str(meta.get("tag") or "").lower() in ("a", "button", "img"):
        score += 70
    if str(meta.get("role") or "").lower() == "button":
        score += 60
    if str(meta.get("tabindex") or "").strip() and str(meta.get("tabindex")) != "-1":
        score += 35
    if re.search(r"gerar planilha|voltar|filtro|codigo corretor|premio ramo|comissao ramo", hay):
        score -= 180
    if len(text) > 500:
        score -= 30
    return score


def _summarize_policy_result_trace(nodes: List[Dict[str, Any]], item: Dict[str, Any]) -> Dict[str, Any]:
    scored: List[Dict[str, Any]] = []
    for meta in nodes or []:
        clean = {
            "text": _clean_text(meta.get("text") or "")[:180],
            "tag": str(meta.get("tag") or "")[:30],
            "role": str(meta.get("role") or "")[:40],
            "id": str(meta.get("id") or "")[:80],
            "cls": str(meta.get("cls") or "")[:140],
            "href": _sanitize_trace_url(meta.get("href")),
            "onclick": str(meta.get("onclick") or "")[:160],
            "cursor": str(meta.get("cursor") or "")[:30],
            "cell_index": meta.get("cell_index"),
            "x": meta.get("x"),
            "y": meta.get("y"),
            "w": meta.get("w"),
            "h": meta.get("h"),
            "clickable_tag": str(meta.get("clickable_tag") or "")[:30],
            "clickable_cls": str(meta.get("clickable_cls") or "")[:120],
            "html": _clean_text(meta.get("html") or "")[:500],
        }
        scored.append({"score": _score_policy_result_node(meta, item or {}), **clean})
    scored.sort(key=lambda row: int(row.get("score") or 0), reverse=True)
    return {"row_candidates": scored[:30]}


def _remember_evidence_list(evidence: Dict[str, Any], key: str, value: Dict[str, Any], limit: int = 12) -> None:
    bucket = evidence.setdefault(key, [])
    if isinstance(bucket, list):
        bucket.append(value)
        if len(bucket) > limit:
            del bucket[:-limit]


def _extract_menu_candidates(payload: Any) -> List[Dict[str, str]]:
    keywords = (
        "apolice",
        "apolices",
        "boleto",
        "cobranca",
        "consulta",
        "ficha",
        "gestao",
        "historico",
        "pagamento",
        "proposta",
        "recibo",
        "sinistro",
    )
    label_keys = ("label", "title", "text", "name", "caption", "description", "nome", "descricao")
    url_keys = ("url", "path", "href", "link", "route", "targetUrl", "serviceUrl", "applicationUrl")
    out: List[Dict[str, str]] = []
    seen = set()

    def walk(node: Any, trail: List[str]) -> None:
        if isinstance(node, dict):
            labels = [_clean_text(node.get(key)) for key in label_keys if _clean_text(node.get(key))]
            urls = [_clean_text(node.get(key)) for key in url_keys if _clean_text(node.get(key))]
            label = " > ".join([*trail, *labels])[:240]
            hay = _norm(" ".join([label, *urls]))
            if any(key in hay for key in keywords):
                url = urls[0] if urls else ""
                ident = (label, url)
                if ident not in seen:
                    seen.add(ident)
                    out.append({"label": label, "url": _sanitize_trace_url(url)})
            next_trail = [*trail, *labels[:1]]
            for value in node.values():
                if isinstance(value, (dict, list)):
                    walk(value, next_trail)
        elif isinstance(node, list):
            for value in node:
                walk(value, trail)

    walk(payload, [])
    return out[:80]


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


async def _click_section_button_candidate(page, candidates: Iterable[str], *, timeout_ms: int = 1600) -> bool:
    cand = [str(c or "") for c in candidates if str(c or "").strip()]
    if not cand:
        return False
    for frame in getattr(page, "frames", [page]):
        try:
            clicked = await frame.evaluate(
                """(candidates) => {
                  const norm = s => (s || '').normalize('NFKD').replace(/[\\u0300-\\u036f]/g, '')
                    .toLowerCase().replace(/\\s+/g, ' ').trim();
                  const vis = el => !!(el && (el.offsetParent || el.getClientRects().length));
                  const wants = candidates.map(norm).filter(Boolean);
                  const els = [...document.querySelectorAll('.sectionButton, div, td, span')]
                    .filter(vis)
                    .map(el => {
                      const text = norm(el.innerText || el.textContent || el.getAttribute('aria-label') || el.title || '');
                      let score = 0;
                      for (const want of wants) {
                        if (text === want) score = Math.max(score, 1000);
                        else if (text.includes(want)) score = Math.max(score, 100);
                      }
                      const target = el.closest('.sectionButton') || el;
                      const r = target.getBoundingClientRect();
                      const cls = String(target.className || '');
                      if (cls.includes('sectionButton')) score += 300;
                      return {score, target, x: r.left + r.width / 2, y: r.top + r.height / 2, area: r.width * r.height};
                    })
                    .filter(x => x.score > 0 && x.area > 0)
                    .sort((a, b) => (b.score - a.score) || (a.area - b.area));
                  const hit = els[0];
                  if (!hit) return false;
                  hit.target.scrollIntoView({block: 'center', inline: 'center'});
                  for (const type of ['mouseover', 'mousedown', 'mouseup', 'click']) {
                    hit.target.dispatchEvent(new MouseEvent(type, {
                      bubbles: true,
                      cancelable: true,
                      view: window,
                      clientX: hit.x,
                      clientY: hit.y
                    }));
                  }
                  hit.target.click();
                  return true;
                }""",
                cand,
            )
            if not clicked:
                continue
            await page.wait_for_timeout(timeout_ms)
            return True
        except Exception:  # noqa: BLE001
            continue
    return False


async def _click_section_button_candidate_trusted(page, candidates: Iterable[str], *, timeout_ms: int = 1600) -> bool:
    cand = [_norm(str(c or "")) for c in candidates if _norm(str(c or ""))]
    if not cand:
        return False
    for frame in getattr(page, "frames", [page]):
        try:
            handles = await frame.query_selector_all(".sectionButton")
        except Exception:  # noqa: BLE001
            continue
        scored = []
        for handle in handles:
            try:
                text = _norm(await handle.inner_text())
            except Exception:  # noqa: BLE001
                continue
            score = 0
            for want in cand:
                if text == want:
                    score = max(score, 1000)
                elif want in text:
                    score = max(score, 100)
            if score > 0:
                scored.append((score, handle))
        scored.sort(key=lambda row: row[0], reverse=True)
        for _, handle in scored:
            try:
                await handle.scroll_into_view_if_needed(timeout=3000)
            except Exception:  # noqa: BLE001
                pass
            try:
                await handle.click(timeout=5000)
                await page.wait_for_timeout(timeout_ms)
                return True
            except Exception:  # noqa: BLE001
                continue
    return False


def _extract_new_window_url_from_onclick(onclick: Any, base_url: str = "") -> str:
    text = html.unescape(str(onclick or ""))
    if not text:
        return ""
    match = re.search(r"sendMenuVerticalEventNewWindow\s*\(\s*(['\"])(.*?)\1", text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    url = html.unescape(match.group(2).strip())
    if not url:
        return ""
    return urljoin(base_url, url) if base_url else url


async def _section_button_new_window_url(page, candidates: Iterable[str]) -> str:
    cand = [str(c or "") for c in candidates if str(c or "").strip()]
    if not cand:
        return ""
    for frame in getattr(page, "frames", [page]):
        try:
            onclick = await frame.evaluate(
                """(candidates) => {
                  const norm = s => (s || '').normalize('NFKD').replace(/[\\u0300-\\u036f]/g, '')
                    .toLowerCase().replace(/\\s+/g, ' ').trim();
                  const vis = el => !!(el && (el.offsetParent || el.getClientRects().length));
                  const wants = candidates.map(norm).filter(Boolean);
                  const nodes = [...document.querySelectorAll('.sectionButton, div, td, span')]
                    .filter(vis)
                    .map(el => {
                      const target = el.closest('.sectionButton') || el;
                      const text = norm(target.innerText || target.textContent || target.getAttribute('aria-label') || target.title || '');
                      const onclick = target.getAttribute('onclick') || '';
                      let score = 0;
                      for (const want of wants) {
                        if (text === want) score = Math.max(score, 1000);
                        else if (text.includes(want)) score = Math.max(score, 100);
                      }
                      if (/sendMenuVerticalEventNewWindow/i.test(onclick)) score += 500;
                      if (String(target.className || '').includes('sectionButton')) score += 250;
                      return {score, onclick};
                    })
                    .filter(x => x.score > 0 && x.onclick)
                    .sort((a, b) => b.score - a.score);
                  return nodes[0]?.onclick || '';
                }""",
                cand,
            )
            url = _extract_new_window_url_from_onclick(onclick, getattr(page, "url", ""))
            if url:
                return url
        except Exception:  # noqa: BLE001
            continue
    return ""


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


async def _collect_visible_input_candidates(page) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for frame in getattr(page, "frames", [page]):
        try:
            rows = await frame.evaluate(
                """() => {
                  const clean = t => (t || '').replace(/\\s+/g, ' ').trim();
                  const vis = el => !!(el && (el.offsetParent || el.getClientRects().length));
                  return [...document.querySelectorAll('input')]
                    .filter(el => vis(el) && (el.type || '').toLowerCase() !== 'password')
                    .map(el => {
                      const rect = el.getBoundingClientRect();
                      const near = el.closest('form,section,div,table') || document.body;
                      return {
                        placeholder: el.placeholder || '',
                        id: el.id || '',
                        name: el.name || '',
                        aria: el.getAttribute('aria-label') || '',
                        type: el.type || '',
                        value: el.value || '',
                        x: Math.round(rect.x),
                        y: Math.round(rect.y),
                        w: Math.round(rect.width),
                        h: Math.round(rect.height),
                        near_text: clean(near.innerText || '').slice(0, 300)
                      };
                    })
                    .slice(0, 80);
                }"""
            )
            if isinstance(rows, list):
                out.extend([row for row in rows if isinstance(row, dict)])
        except Exception:  # noqa: BLE001
            continue
    return out


async def _collect_policy_search_component_nodes(page) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for frame in getattr(page, "frames", [page]):
        try:
            rows = await frame.evaluate(
                """() => {
                  const clean = t => (t || '').replace(/\\s+/g, ' ').trim();
                  const vis = el => !!(el && (el.offsetParent || el.getClientRects().length));
                  const input = document.querySelector('input[name="target"], input[id^="nx-input-"]');
                  if (!input) return [];
                  const ib = input.getBoundingClientRect();
                  const around = [...document.querySelectorAll('button,a,[role=button],[onclick],[tabindex],span,div,i,svg,nx-icon,path,use')]
                    .filter(el => vis(el))
                    .map(el => {
                      const r = el.getBoundingClientRect();
                      const cx = r.x + r.width / 2;
                      const cy = r.y + r.height / 2;
                      const near = cx >= ib.right - 80 && cx <= ib.right + 180 && cy >= ib.top - 80 && cy <= ib.bottom + 80;
                      const ancestor = input.parentElement && input.parentElement.contains(el);
                      return {el, r, near, ancestor};
                    })
                    .filter(x => x.near || x.ancestor)
                    .map(x => {
                      const el = x.el;
                      const r = x.r;
                      return {
                        tag: (el.tagName || '').toLowerCase(),
                        role: el.getAttribute('role') || '',
                        id: el.id || '',
                        cls: String(el.className || '').slice(0, 220),
                        text: clean(el.innerText || el.textContent || ''),
                        aria: el.getAttribute('aria-label') || '',
                        title: el.title || '',
                        onclick: el.getAttribute('onclick') || '',
                        x: Math.round(r.x),
                        y: Math.round(r.y),
                        w: Math.round(r.width),
                        h: Math.round(r.height),
                        html: clean(el.outerHTML || '').slice(0, 700)
                      };
                    });
                  return around.slice(0, 120);
                }"""
            )
            if isinstance(rows, list):
                out.extend([row for row in rows if isinstance(row, dict)])
        except Exception:  # noqa: BLE001
            continue
    return out


async def _collect_policy_result_row_nodes(page, item: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    terms = [
        _clean_text(item.get("recibo")),
        _clean_text(item.get("apolice_susep")),
        _clean_text(item.get("cpf_cnpj")),
        _clean_text(item.get("cliente_nome")),
        _clean_text(item.get("parcela")),
    ]
    terms = [term for term in terms if term]
    for frame in getattr(page, "frames", [page]):
        try:
            rows = await frame.evaluate(
                """(terms) => {
                  const clean = t => (t || '').replace(/\\s+/g, ' ').trim();
                  const norm = s => clean(s).normalize('NFKD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase();
                  const digits = s => String(s || '').replace(/\\D+/g, '');
                  const vis = el => !!(el && (el.offsetParent || el.getClientRects().length));
                  const rowSel = 'tr,[role=row],.datatable-body-row,.datatable-row-wrapper,li';
                  const rows = [...document.querySelectorAll(rowSel)].filter(vis);
                  const scoredRows = rows.map((row, rowIndex) => {
                    const raw = clean(row.innerText || row.textContent || '');
                    const text = norm(raw);
                    let score = 0;
                    for (const term of terms || []) {
                      const want = norm(term);
                      const wantDigits = digits(term);
                      if (!want) continue;
                      if (wantDigits && wantDigits.length >= 6 && digits(raw).includes(wantDigits)) score += 1000;
                      else if (text.includes(want)) score += Math.max(20, want.length);
                    }
                    if (/apolice susep|resultado - por parcela|status recibo|tipo modelo|description/.test(text)) score -= 500;
                    return {row, rowIndex, score, raw};
                  }).filter(x => x.score > 0).sort((a, b) => b.score - a.score).slice(0, 3);
                  const result = [];
                  for (const entry of scoredRows) {
                    const row = entry.row;
                    const cells = [...row.querySelectorAll('th,td,[role=cell],mat-cell,.mat-cell,.datatable-body-cell')].filter(vis);
                    const inner = [
                      row,
                      ...cells,
                      ...row.querySelectorAll('a,button,img,input,span,div,[role=button],[onclick],[tabindex]')
                    ].filter(vis);
                    const unique = [];
                    for (const el of inner) {
                      if (!unique.includes(el)) unique.push(el);
                    }
                    for (const el of unique.slice(0, 90)) {
                      const rect = el.getBoundingClientRect();
                      const style = getComputedStyle(el);
                      const cell = el.closest('th,td,[role=cell],mat-cell,.mat-cell,.datatable-body-cell');
                      const clickable = el.closest('a,button,[role=button],[onclick],[tabindex],img');
                      const attrs = {};
                      for (const attr of [...(el.attributes || [])]) {
                        const name = attr.name || '';
                        if (/^(data-|ng-|_ng|routerlink|href|target|onclick|tabindex|role|title|alt|src|id|class|name)$/i.test(name)) {
                          attrs[name] = String(attr.value || '').slice(0, 180);
                        }
                      }
                      result.push({
                        row_index: entry.rowIndex,
                        row_score: entry.score,
                        row_text: entry.raw.slice(0, 500),
                        cell_index: cell ? cells.indexOf(cell) : -1,
                        text: clean(el.innerText || el.textContent || el.getAttribute('aria-label') || el.title || el.alt || el.value || ''),
                        tag: (el.tagName || '').toLowerCase(),
                        role: el.getAttribute('role') || '',
                        id: el.id || '',
                        cls: String(el.className || '').slice(0, 220),
                        aria: el.getAttribute('aria-label') || '',
                        title: el.title || '',
                        alt: el.alt || '',
                        href: el.href || '',
                        src: el.src || '',
                        onclick: el.getAttribute('onclick') || '',
                        tabindex: el.getAttribute('tabindex') || '',
                        cursor: style.cursor || '',
                        x: Math.round(rect.x),
                        y: Math.round(rect.y),
                        w: Math.round(rect.width),
                        h: Math.round(rect.height),
                        clickable_tag: clickable ? (clickable.tagName || '').toLowerCase() : '',
                        clickable_cls: clickable ? String(clickable.className || '').slice(0, 160) : '',
                        attrs,
                        html: clean(el.outerHTML || '').slice(0, 700)
                      });
                    }
                  }
                  return result.slice(0, 180);
                }""",
                terms,
            )
            if isinstance(rows, list):
                out.extend([row for row in rows if isinstance(row, dict)])
        except Exception:  # noqa: BLE001
            continue
    return out


async def _capture_page_activity(page, label: str, action, *, wait_ms: int = 1800):
    events: List[Dict[str, Any]] = []
    popups: List[str] = []

    def on_request(request):
        if len(events) >= 140:
            return
        try:
            events.append({"kind": "request", "method": request.method, "url": request.url})
        except Exception:  # noqa: BLE001
            return

    def on_response(response):
        if len(events) >= 180:
            return
        try:
            events.append({"kind": "response", "status": response.status, "url": response.url})
        except Exception:  # noqa: BLE001
            return

    def on_page(new_page):
        try:
            popups.append(_sanitize_trace_url(getattr(new_page, "url", "")))
        except Exception:  # noqa: BLE001
            return

    try:
        before_url = _sanitize_trace_url(page.url)
    except Exception:  # noqa: BLE001
        before_url = ""
    try:
        page.on("request", on_request)
        page.on("response", on_response)
        page.context.on("page", on_page)
    except Exception:  # noqa: BLE001
        pass
    result = False
    error = ""
    try:
        result = await action()
        await page.wait_for_timeout(wait_ms)
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {str(exc)[:160]}"
    finally:
        for event_name, handler in (("request", on_request), ("response", on_response)):
            try:
                page.remove_listener(event_name, handler)
            except Exception:  # noqa: BLE001
                pass
        try:
            page.context.remove_listener("page", on_page)
        except Exception:  # noqa: BLE001
            pass
    try:
        after_url = _sanitize_trace_url(page.url)
    except Exception:  # noqa: BLE001
        after_url = ""
    trace = {
        "label": label[:80],
        "result": bool(result),
        "error": error,
        "before_url": before_url,
        "after_url": after_url,
        "url_changed": before_url != after_url,
        "popups": [popup for popup in popups if popup][:8],
    }
    trace.update(_summarize_network_trace(events))
    return result, trace


async def _record_session_menu_trace(page, evidence: Dict[str, Any], stage: str) -> None:
    try:
        payload = await page.evaluate(
            """async () => {
              const urls = performance.getEntriesByType('resource')
                .map(e => e && e.name)
                .filter(u => typeof u === 'string' && u.includes('/rws-bff-epac/api/private/session-menu'));
              const url = urls.length ? urls[urls.length - 1] : '';
              if (!url) return {ok: false, reason: 'session-menu url not found'};
              const res = await fetch(url, {credentials: 'include'});
              let body = null;
              try { body = await res.json(); } catch (e) { body = await res.text(); }
              return {ok: res.ok, status: res.status, url, body};
            }"""
        )
        candidates = _extract_menu_candidates((payload or {}).get("body") if isinstance(payload, dict) else None)
        summary = {
            "stage": stage,
            "ok": bool(isinstance(payload, dict) and payload.get("ok")),
            "status": payload.get("status") if isinstance(payload, dict) else None,
            "url": _sanitize_trace_url(payload.get("url") if isinstance(payload, dict) else ""),
            "reason": str(payload.get("reason") or "")[:160] if isinstance(payload, dict) else "",
            "candidates": candidates,
        }
        _remember_evidence_list(evidence, "session_menu_trace", summary, limit=6)
    except Exception as e:  # noqa: BLE001
        evidence.setdefault("download_notes", []).append(f"trace menu sessao falhou: {type(e).__name__}")


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


async def _record_policy_search_debug(page, item: Dict[str, Any], evidence: Dict[str, Any], stage: str, term: str = "") -> None:
    try:
        inputs = await _collect_visible_input_candidates(page)
        nodes = await _collect_policy_search_component_nodes(page)
        summary = _summarize_policy_search_debug(inputs)
        summary.update(_summarize_policy_search_component(nodes))
        try:
            url = page.url
        except Exception:  # noqa: BLE001
            url = ""
        summary.update({
            "stage": stage,
            "term": _clean_text(term)[:120],
            "url": url,
            "item": {
                "recibo": item.get("recibo"),
                "parcela": item.get("parcela"),
                "apolice_susep": item.get("apolice_susep"),
            },
        })
        _remember_evidence_list(evidence, "policy_search_debug", summary, limit=12)
    except Exception as e:  # noqa: BLE001
        evidence.setdefault("download_notes", []).append(f"debug busca apolice falhou: {type(e).__name__}")


async def _record_policy_result_trace(page, item: Dict[str, Any], evidence: Dict[str, Any], stage: str) -> None:
    try:
        nodes = await _collect_policy_result_row_nodes(page, item)
        summary = _summarize_policy_result_trace(nodes, item)
        try:
            url = page.url
        except Exception:  # noqa: BLE001
            url = ""
        summary.update({
            "stage": stage,
            "url": _sanitize_trace_url(url),
            "item": {
                "recibo": item.get("recibo"),
                "parcela": item.get("parcela"),
                "apolice_susep": item.get("apolice_susep"),
                "cpf_cnpj": item.get("cpf_cnpj"),
            },
        })
        _remember_evidence_list(evidence, "policy_result_trace", summary, limit=12)
    except Exception as e:  # noqa: BLE001
        evidence.setdefault("download_notes", []).append(f"trace resultado apolice falhou: {type(e).__name__}")


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
              const overlapY = (a, b) => Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
              const inputChoices = [...document.querySelectorAll('input')]
                .filter(i => vis(i) && (i.type || '').toLowerCase() !== 'password')
                .map(i => {
                  const rect = i.getBoundingClientRect();
                  const hay = norm([i.type, i.placeholder, i.getAttribute('aria-label'), i.id, i.name].join(' '));
                  const nearText = norm((i.closest('form,section,div,table') || document.body).innerText || '');
                  let score = 0;
                  if (/busca|buscar|pesquis|search|cliente|cpf|apolice|recibo/.test(hay)) score += 180;
                  if (rect.top < 260 && rect.width > 220) score += 90;
                  if (rect.width > 320) score += 30;
                  if (/filtro\\s+susep|codigo corretor|premio ramo|comissao ramo/.test(nearText)) score -= 160;
                  return {el: i, rect, score};
                })
                .filter(x => x.score > 0)
                .sort((a, b) => b.score - a.score);
              const best = inputChoices.length ? inputChoices[0].el : null;
              if (!best) return false;
              best.focus();
              const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
              if (setter) setter.call(best, value); else best.value = value;
              best.dispatchEvent(new InputEvent('input', {bubbles: true, inputType: 'insertText', data: value}));
              best.dispatchEvent(new KeyboardEvent('keyup', {bubbles: true, key: 'Enter', code: 'Enter'}));
              best.dispatchEvent(new Event('change', {bubbles: true}));
              const inputRect = best.getBoundingClientRect();
              const clickables = [...document.querySelectorAll('button,a,[role=button],[onclick],[tabindex],i,svg,span,div,nx-icon')]
                .filter(el => vis(el) && el !== best)
                .map(el => {
                  const rect = el.getBoundingClientRect();
                  const hay = norm([
                    el.innerText, el.textContent, el.getAttribute('aria-label'), el.title,
                    el.id, el.className, el.getAttribute('name')
                  ].join(' '));
                  let score = 0;
                  if (/search|pesquis|buscar|lupa|magnif/.test(hay)) score += 80;
                  if (rect.left >= inputRect.right - 16 && rect.left <= inputRect.right + 140 && overlapY(rect, inputRect) > Math.min(rect.height, inputRect.height) * 0.35) score += 90;
                  if (rect.width <= 90 && rect.height <= 90) score += 15;
                  return {el, score};
                })
                .filter(x => x.score >= 90)
                .sort((a, b) => b.score - a.score);
              if (clickables.length) {
                const target = clickables[0].el.closest('button,a,[role=button],[onclick],[tabindex]') || clickables[0].el;
                target.click();
              }
              return true;
            }""",
            query,
        )
        if not filled:
            return False
        await page.wait_for_timeout(500)
        for frame in getattr(page, "frames", [page]):
            try:
                candidates = frame.locator('input[name="target"], input[id^="nx-input-"]')
                if await candidates.count() <= 0:
                    continue
                loc = candidates.first
                await loc.click(timeout=1500)
                try:
                    await loc.press("Control+A", timeout=800)
                    await loc.press("Backspace", timeout=800)
                    await loc.type(query, delay=18, timeout=5000)
                except Exception:  # noqa: BLE001
                    await loc.fill(query, timeout=1500)
                box = await loc.bounding_box(timeout=1500)
                try:
                    await loc.press("Enter", timeout=1000)
                except Exception:  # noqa: BLE001
                    pass
                if box:
                    await page.mouse.click(box["x"] + box["width"] + 24, box["y"] + (box["height"] / 2))
                break
            except Exception:  # noqa: BLE001
                continue
        try:
            await page.keyboard.press("Enter")
        except Exception:  # noqa: BLE001
            pass
        await page.wait_for_timeout(1500)
        return True
    except Exception:  # noqa: BLE001
        return False


async def _dismiss_blocking_modal(page) -> bool:
    """Fecha modal Allianz que intercepta a tela (ex.: 'Não foram encontrados
    resultados' + FECHAR). Clique via JS (imune a interceptação) + Escape."""
    closed = False
    try:
        closed = bool(
            await page.evaluate(
                """() => {
                  const vis = el => !!(el && (el.offsetParent || el.getClientRects().length));
                  const norm = s => (s || '').normalize('NFKD').replace(/[\\u0300-\\u036f]/g, '')
                    .toLowerCase().replace(/\\s+/g, ' ').trim();
                  const scopes = document.querySelectorAll(
                    '[role=dialog], .nx-modal__container, .cdk-overlay-container, .modal, [class*="modal"]');
                  for (const scope of scopes) {
                    const controls = scope.querySelectorAll('button, a, [role=button], .nx-button');
                    for (const el of controls) {
                      const text = norm(el.innerText || el.textContent || el.getAttribute('aria-label') || '');
                      if (vis(el) && (text === 'fechar' || text === 'close' || text === 'x' || text === 'ok')) {
                        el.click();
                        return true;
                      }
                    }
                  }
                  return false;
                }"""
            )
        )
    except Exception:  # noqa: BLE001
        closed = False
    if not closed:
        try:
            await page.keyboard.press("Escape")
        except Exception:  # noqa: BLE001
            pass
    try:
        await page.wait_for_timeout(700)
    except Exception:  # noqa: BLE001
        pass
    return closed


async def _fill_global_search_for_category(page, value: str, *, _retry: bool = True) -> bool:
    """Preenche a busca Allianz e deixa o popover de categorias aberto."""
    query = _clean_text(value)
    if not query:
        return False
    for frame in getattr(page, "frames", [page]):
        try:
            # A barra global tem placeholder 'Pesquisar ...'; os seletores
            # genéricos (nx-input) também casam com campos de FILTRO da tela
            # de inadimplências — por isso o placeholder vem primeiro.
            candidates = frame.locator(
                'input[placeholder*="esquisar"], input[name="target"], input[role="searchBar"], input[id^="nx-input-"]'
            )
            if await candidates.count() <= 0:
                continue
            loc = candidates.first
            await loc.click(timeout=2500)
            try:
                await loc.press("Control+A", timeout=800)
                await loc.press("Backspace", timeout=800)
                await loc.type(query, delay=35, timeout=8000)
            except Exception:  # noqa: BLE001
                await loc.fill(query, timeout=2500)
                await loc.dispatch_event("input")
            await page.wait_for_timeout(1300)
            return True
        except Exception:  # noqa: BLE001
            continue
    # Nenhum frame aceitou o clique: um modal pode estar interceptando a tela
    # (causa raiz do job a9f4b375). Fecha e tenta UMA vez de novo.
    if _retry and await _dismiss_blocking_modal(page):
        return await _fill_global_search_for_category(page, value, _retry=False)
    return False


async def _click_search_category_candidate(page, candidates: Iterable[str], *, timeout_ms: int = 1600) -> bool:
    cand = [str(c or "") for c in candidates if str(c or "").strip()]
    if not cand:
        return False
    try:
        point = await page.evaluate(
            """(candidates) => {
              const norm = s => (s || '').normalize('NFKD').replace(/[\\u0300-\\u036f]/g, '')
                .toLowerCase().replace(/\\s+/g, ' ').trim();
              const vis = el => !!(el && (el.offsetParent || el.getClientRects().length));
              const wants = candidates.map(norm).filter(Boolean);
              const selectors = [
                '.cdk-overlay-container a',
                '.cdk-overlay-container nx-link',
                '.cdk-overlay-container mat-tree-node',
                '[role=dialog] a',
                '[role=treeitem] a'
              ].join(',');
              const matches = [...document.querySelectorAll(selectors)].filter(vis).map(el => {
                const text = norm(el.innerText || el.textContent || el.getAttribute('aria-label') || el.title || '');
                let score = 0;
                for (const want of wants) {
                  if (text === want) score = Math.max(score, 1000);
                  else if (text.includes(want) || want.includes(text)) score = Math.max(score, 100);
                }
                const target = el.querySelector('a') || el;
                const r = target.getBoundingClientRect();
                return {score, text, x: r.left + r.width / 2, y: r.top + r.height / 2, area: r.width * r.height};
              }).filter(x => x.score > 0 && x.area > 0)
                .sort((a, b) => (b.score - a.score) || (a.area - b.area) || (a.y - b.y));
              return matches[0] || null;
            }""",
            cand,
        )
        if not point:
            return False
        await page.mouse.click(float(point["x"]), float(point["y"]))
        await page.wait_for_timeout(timeout_ms)
        return True
    except Exception:  # noqa: BLE001
        return False


async def _click_search_category_for_term(page, term: str, item: Dict[str, Any]) -> bool:
    """Depois de digitar na busca global Allianz, escolhe a categoria correta."""
    term_digits = _digits(term)
    cpf_digits = _digits((item or {}).get("cpf_cnpj"))
    apolice_digits = _digits((item or {}).get("apolice_susep"))
    recibo_digits = _digits((item or {}).get("recibo"))
    if cpf_digits and term_digits == cpf_digits:
        candidates = ("CPF/CNPJ", "Clientes CPF/CNPJ")
    elif apolice_digits and term_digits == apolice_digits:
        candidates = (
            "Apolice Susep / Endosso",
            "Apolice SUSEP",
            "Apolices / Proposta",
            "Apolices/Proposta",
        )
    elif recibo_digits and term_digits == recibo_digits:
        candidates = ("Recibo / Pagamento", "Recibo/Pagamento")
    else:
        candidates = (
            "Nome / Razao Social",
            "Nome/Razao Social",
            "Nome Razao Social",
            "Clientes Nome",
        )
    clicked = await _click_search_category_candidate(page, candidates, timeout_ms=1800)
    if not clicked:
        clicked = await _click_text_candidate(page, candidates, timeout_ms=1800)
    if clicked:
        await page.wait_for_timeout(1600)
    return clicked


async def _click_customer_search_result(page, item: Dict[str, Any], evidence: Dict[str, Any]) -> bool:
    """Clica no cliente retornado pela busca; em duplicados Allianz, o ultimo costuma trazer a apolice.
    Tambem aceita o resultado da categoria 'Apolice Susep / Endosso': linha cujo
    conjunto de digitos contem a apolice do item (o anchor ali nao e o nome)."""
    name = _clean_text((item or {}).get("cliente_nome"))
    cpf = _digits((item or {}).get("cpf_cnpj"))
    apolice = _digits((item or {}).get("apolice_susep"))
    if not name and not cpf and not apolice:
        return False
    try:
        point = await page.evaluate(
            """({name, cpf, apolice}) => {
              const norm = s => (s || '').normalize('NFKD').replace(/[\\u0300-\\u036f]/g, '')
                .toLowerCase().replace(/\\s+/g, ' ').trim();
              const digits = s => String(s || '').replace(/\\D/g, '');
              const vis = el => !!(el && (el.offsetParent || el.getClientRects().length));
              const wantName = norm(name);
              const wantCpf = digits(cpf);
              const wantApolice = digits(apolice);
              const anchors = [...document.querySelectorAll('[role=dialog] a, .nx-modal__container a')]
                .filter(vis)
                .map(el => {
                  const row = el.closest('tr') || el.closest('[role=row]') || el.closest('div');
                  const text = norm(el.innerText || el.textContent || '');
                  const rowText = norm(row ? (row.innerText || row.textContent || '') : text);
                  const rowDigits = digits(rowText);
                  const r = el.getBoundingClientRect();
                  let score = 0;
                  if (wantName && text === wantName) score += 500;
                  if (wantApolice && wantApolice.length >= 10 && rowDigits.includes(wantApolice)) score += 500;
                  if (wantName && rowText.includes(wantName)) score += 150;
                  if (wantCpf && rowDigits.includes(wantCpf)) score += 120;
                  if ((getComputedStyle(el).cursor || '').includes('pointer')) score += 20;
                  return {score, text, rowText, x: r.left + r.width / 2, y: r.top + r.height / 2, area: r.width * r.height};
                })
                .filter(x => x.score >= 500 && x.area > 0)
                .sort((a, b) => (b.score - a.score) || (b.y - a.y));
              return anchors[0] || null;
            }""",
            {"name": name, "cpf": cpf, "apolice": apolice},
        )
        if not point:
            return False
        await page.mouse.click(float(point["x"]), float(point["y"]))
        await page.wait_for_timeout(4500)
        evidence.setdefault("download_notes", []).append("resultado de cliente aberto pela busca")
        return True
    except Exception:  # noqa: BLE001
        return False


async def _click_operar_candidate(page, index: int = 0) -> bool:
    for frame in getattr(page, "frames", [page]):
        try:
            clicked = await frame.evaluate(
                """(index) => {
                  const norm = s => (s || '').normalize('NFKD').replace(/[\\u0300-\\u036f]/g, '')
                    .toLowerCase().replace(/\\s+/g, ' ').trim();
                  const vis = el => !!(el && (el.offsetParent || el.getClientRects().length));
                  const selectors = 'button,a,[role=button],[onclick],[tabindex],span,div,nx-button';
                  const els = [...document.querySelectorAll(selectors)]
                    .filter(el => vis(el) && norm(el.innerText || el.textContent || el.getAttribute('aria-label') || el.title) === 'operar')
                    .map(el => {
                      const target = el.closest('button,a,[role=button],[onclick],[tabindex],nx-button') || el;
                      const rect = target.getBoundingClientRect();
                      return {target, y: rect.y, x: rect.x};
                    })
                    .sort((a, b) => (a.y - b.y) || (a.x - b.x));
                  if (!els[index]) return false;
                  els[index].target.click();
                  return true;
                }""",
                index,
            )
            if clicked:
                await page.wait_for_timeout(1200)
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


async def _open_policy_detail_from_customer(page, item: Dict[str, Any], evidence: Dict[str, Any]) -> bool:
    if _looks_like_policy_context(await _all_body_text(page)):
        text = await _all_body_text(page)
        return _policy_context_matches_item(text, item) or _policy_context_matches_customer(text, item)

    detail_terms = (
        "Detalhe de Apolice",
        "Detalhes de Apolice",
        "Detalhe da Apolice",
        "Detalhes da Apolice",
    )
    for index in range(6):
        if await _click_text_candidate(page, detail_terms, timeout_ms=1600):
            if await _wait_until_policy_context(page, timeout_ms=10000):
                text = await _all_body_text(page)
                if _policy_context_matches_item(text, item) or _policy_context_matches_customer(text, item):
                    evidence.setdefault("download_notes", []).append("detalhe de apolice aberto")
                    return True
                evidence.setdefault("download_notes", []).append("detalhe abriu apolice diferente do item")
        clicked_operar = await _click_operar_candidate(page, index=index)
        if not clicked_operar:
            if index == 0:
                evidence.setdefault("download_notes", []).append("botao Operar nao encontrado na ficha do cliente")
            break
        if await _click_text_candidate(page, detail_terms, timeout_ms=1800):
            if await _wait_until_policy_context(page, timeout_ms=10000):
                text = await _all_body_text(page)
                if _policy_context_matches_item(text, item) or _policy_context_matches_customer(text, item):
                    evidence.setdefault("download_notes", []).append("operar + detalhe de apolice aberto")
                    return True
                evidence.setdefault("download_notes", []).append("operar abriu apolice diferente do item")
        if _looks_like_policy_context(await _all_body_text(page)):
            text = await _all_body_text(page)
            if _policy_context_matches_item(text, item) or _policy_context_matches_customer(text, item):
                evidence.setdefault("download_notes", []).append("operar abriu contexto de apolice direto")
                return True
    try:
        await page.wait_for_timeout(2500)
    except Exception:  # noqa: BLE001
        pass
    text = await _all_body_text(page)
    if _looks_like_policy_context(text) and (
        _policy_context_matches_item(text, item) or _policy_context_matches_customer(text, item)
    ):
        evidence.setdefault("download_notes", []).append("contexto de apolice confirmado apos carregamento")
        return True
    return False


async def _wait_until_policy_context(page, timeout_ms: int = 12000) -> bool:
    deadline = timeout_ms // 600
    for _ in range(max(1, deadline)):
        text = await _all_body_text(page)
        if _looks_like_policy_context(text) or _looks_like_recibos_list(text):
            return True
        await page.wait_for_timeout(600)
    return False


def _policy_context_matches_item(page_text: str, item: Dict[str, Any]) -> bool:
    apolice = _digits((item or {}).get("apolice_susep"))
    if not apolice:
        return True
    return apolice in _digits(page_text)


def _policy_context_matches_customer(page_text: str, item: Dict[str, Any]) -> bool:
    name = _norm((item or {}).get("cliente_nome"))
    body = _norm(page_text)
    return bool(name and name in body)


async def _wait_until_text(page, tokens: Iterable[str], timeout_ms: int = 12000) -> bool:
    wanted = [_norm(t) for t in tokens if _norm(t)]
    if not wanted:
        return False
    deadline = timeout_ms // 600
    for _ in range(max(1, deadline)):
        text = _norm(await _all_body_text(page))
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


def _should_restart_policy_search_from_home(text: str) -> bool:
    if _looks_like_policy_context(text) or _looks_like_recibos_list(text):
        return False
    _ = text
    return False


def _looks_like_inadimplentes_totals(text: str) -> bool:
    body = _norm(text)
    if "resultado - totais" in body:
        return True
    return "qtd.apolices" in body and "qtd.pcs" in body and "premio" in body


def _safe_home_inadimplencias_text(text: str) -> bool:
    body = _norm(text)
    if "inadimplencias" not in body:
        return False
    blocked = ("chat", "fale com a gente", "nova cotacao", "login", "documentacao")
    return not any(token in body for token in blocked)


async def _click_home_inadimplencias_entry(page) -> bool:
    """Clica no alerta da home Allianz, evitando atalhos de chat/cotacao."""
    for frame in getattr(page, "frames", [page]):
        try:
            clicked = await frame.evaluate(
                """() => {
                  const norm = s => (s || '').normalize('NFKD').replace(/[\\u0300-\\u036f]/g, '')
                    .toLowerCase().replace(/\\s+/g, ' ').trim();
                  const vis = el => !!(el && (el.offsetParent || el.getClientRects().length));
                  const blocked = text => /chat|fale com a gente|nova cotacao|login|documentacao/.test(text);
                  const selectors = [
                    'tr', '[role=row]', 'li', 'button', 'a', '[role=button]', '[onclick]', '[tabindex]',
                    '.row', '.card', '.item', 'nx-link', 'nx-action', 'span', 'div'
                  ].join(',');
                  const els = [...document.querySelectorAll(selectors)].filter(vis);
                  let best = null, bestScore = 0;
                  for (const el of els) {
                    const raw = (el.innerText || el.textContent || el.getAttribute('aria-label') || el.title || '');
                    const text = norm(raw);
                    if (!text || text.length > 220 || blocked(text)) continue;
                    let score = 0;
                    if (text === 'inadimplencias') score += 1000;
                    if (/^inadimplencias\\b/.test(text)) score += 800;
                    if (text.includes('inadimplencias')) score += 500;
                    if (/\\b\\d+\\b/.test(text)) score += 50;
                    const tag = (el.tagName || '').toLowerCase();
                    if (tag === 'tr' || el.getAttribute('role') === 'row') score += 80;
                    if (el.closest('button,a,[role=button],[onclick],[tabindex],tr,[role=row],li')) score += 40;
                    if (score > bestScore) { best = el; bestScore = score; }
                  }
                  if (!best || bestScore < 500) return false;
                  const target = best.closest('button,a,[role=button],[onclick],[tabindex],tr,[role=row],li') || best;
                  target.scrollIntoView({block: 'center', inline: 'center'});
                  target.click();
                  return true;
                }"""
            )
            if clicked:
                await page.wait_for_timeout(2500)
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


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
    return await _click_totals_row_by_index(page, 0)


async def _click_totals_row_by_index(page, index: int) -> bool:
    for frame in getattr(page, "frames", [page]):
        try:
            clicked = await frame.evaluate(
                """(index) => {
                  const clean = t => (t || '').replace(/\\s+/g, ' ').trim();
                  const vis = el => !!(el && (el.offsetParent || el.getClientRects().length));
                  const rows = [...document.querySelectorAll('tr,[role=row]')].filter(vis);
                  const matches = [];
                  for (const row of rows) {
                    const text = clean(row.innerText || row.textContent);
                    if (!text || text.length > 260) continue;
                    if (/^\\d+\\s+\\d{4}\\s+-\\s+/.test(text) && /\\d+,\\d{2}/.test(text)) {
                      matches.push(row);
                    }
                  }
                  if (!matches[index]) return false;
                  matches[index].scrollIntoView({block: 'center', inline: 'center'});
                  matches[index].click();
                  return true;
                }""",
                int(index),
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
    if _looks_like_inadimplentes_result(text) or _looks_like_inadimplentes_totals(text):
        return True

    if await _click_home_inadimplencias_entry(page):
        if await _wait_until_inadimplentes_result(page, timeout_ms=6500):
            return True
        if _looks_like_inadimplentes_totals(await _all_body_text(page)):
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
            if _looks_like_inadimplentes_totals(await _all_body_text(page)):
                return True

    adaptive = await _semantic_navigation_review(
        page,
        (
            "Abra o alerta/card INADIMPLENCIAS da home Allianz e pare na tela de Parcelas "
            "Inadimplentes. Nao use a busca global, nao clique em Fale com a gente, Chat "
            "Allianz, Chat Help Desk ou Nova Cotacao."
        ),
        params,
        evidence,
    )
    text = _norm(await _all_body_text(page))
    evidence["cobranca_navigation"] = {"adaptive_status": adaptive.status, "message": adaptive.message}
    return _looks_like_inadimplentes_result(text) or _looks_like_inadimplentes_totals(text)


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


async def _open_receipts_for_item(page, item: Dict[str, Any], params: Dict[str, Any], evidence: Dict[str, Any]) -> bool:
    """Fluxo REAL do corretor (prints 2026-07-10): busca por nome na barra
    global -> 'Nome / Razão Social' -> página do cliente -> Operar ->
    Detalhe de Apólice -> Lista Recibos."""
    if _looks_like_recibos_list(await _all_body_text(page)):
        return True

    if await _open_policy_context_for_item(page, item, params, evidence):
        await _wait_until_text(page, ("Lista Recibos",), timeout_ms=9000)
        if _looks_like_recibos_list(await _all_body_text(page)):
            return True
        clicked_recibos = await _click_section_button_candidate(
            page, ("Lista Recibos", "Lista de Recibos"), timeout_ms=2200
        )
        if not clicked_recibos:
            clicked_recibos = await _click_text_candidate(page, ("Lista Recibos", "Lista de Recibos"), timeout_ms=2200)
        if clicked_recibos:
            if await _wait_until_recibos_list(page, timeout_ms=9000):
                evidence.setdefault("download_notes", []).append("lista recibos aberta a partir do contexto da apolice")
                return True
        await _record_download_debug(page, item, evidence, "lista_recibos_not_found_in_policy_context")

    await _record_download_debug(page, item, evidence, "lista_recibos_not_opened")
    evidence.setdefault("download_notes", []).append("nao abriu listagem de recibos para item")
    return False

async def _relogin_fresh(page, params: Dict[str, Any], evidence: Dict[str, Any]) -> bool:
    """Aprendizado 2026-07-10 (job b693d9de): TODAS as runs de cobrança rodaram
    com sessão RESTAURADA e a busca global devolveu vazio até para cliente que
    comprovadamente existe — enquanto o mesmo fluxo manual (login fresco do
    corretor) funciona. A busca do AllianzNet degrada com storage antigo sem
    derrubar o resto do portal. Limpa cookies/storage e refaz o login."""
    try:
        await page.context.clear_cookies()
    except Exception:  # noqa: BLE001
        pass
    try:
        await page.evaluate("() => { try { localStorage.clear(); sessionStorage.clear(); } catch (e) {} }")
    except Exception:  # noqa: BLE001
        pass
    fresh_params = dict(params or {})
    fresh_params["session_loaded"] = False
    result = await login_check(page, fresh_params, evidence)
    ok = getattr(result, "status", "") == "done"
    evidence["fresh_login_after_empty_search"] = bool(ok)
    evidence.setdefault("download_notes", []).append(
        "relogin fresco apos busca vazia: " + ("ok" if ok else f"falhou ({_clean_text(getattr(result, 'message', ''))[:80]})")
    )
    return ok


async def _open_policy_context_for_item(page, item: Dict[str, Any], params: Dict[str, Any], evidence: Dict[str, Any]) -> bool:
    text = await _all_body_text(page)
    if (_looks_like_policy_context(text) or _looks_like_recibos_list(text)) and _policy_context_matches_item(text, item):
        return True
    if _should_restart_policy_search_from_home(text):
        async def go_home():
            await page.goto(ALLIANZ_PRIVATE_HOME, wait_until="domcontentloaded")
            await page.wait_for_timeout(1800)
            return True

        _, home_trace = await _capture_page_activity(
            page,
            "goto_home_before_policy_search",
            go_home,
            wait_ms=500,
        )
        _remember_evidence_list(evidence, "interaction_traces", home_trace, limit=16)
        await _record_session_menu_trace(page, evidence, "after_home_before_policy_search")
        evidence.setdefault("download_notes", []).append("busca de apolice reiniciada na home apos resultado legado")
    click_terms = _policy_search_terms(item)
    for attempt in range(2):
        for term in click_terms:
            searched, search_trace = await _capture_page_activity(
                page,
                f"global_search:{_clean_text(term)[:48]}",
                lambda term=term: _fill_global_search_for_category(page, term),
                wait_ms=1000,
            )
            search_trace["term"] = _clean_text(term)[:120]
            _remember_evidence_list(evidence, "interaction_traces", search_trace, limit=16)
            if not searched:
                continue
            # O popover 'Pesquisar este dado em...' precisa abrir para a
            # categoria existir; se não abriu, o texto caiu no campo errado.
            if "pesquisar este dado em" not in _norm(await _all_body_text(page)):
                evidence.setdefault("download_notes", []).append(
                    f"popover de categorias nao abriu apos digitar '{_clean_text(term)[:40]}'"
                )
            await _click_search_category_for_term(page, str(term), item)
            # Busca sem resultados abre modal BLOQUEANTE: registrar, fechar e ir
            # direto ao próximo termo (clicar em "resultado" aqui só acha o texto
            # do próprio modal — visto no job a9f4b375).
            after_search_text = await _body_text(page)
            if search_result_is_empty(after_search_text):
                evidence.setdefault("download_notes", []).append(
                    f"busca sem resultados para termo '{_clean_text(term)[:60]}' — modal fechado"
                )
                evidence["empty_search_terms"] = int(evidence.get("empty_search_terms") or 0) + 1
                await _dismiss_blocking_modal(page)
                continue
            await _click_customer_search_result(page, item, evidence)
            if await _open_policy_detail_from_customer(page, item, evidence):
                return True
            if await _wait_until_policy_context(page, timeout_ms=7000):
                text = await _all_body_text(page)
                if _policy_context_matches_item(text, item):
                    evidence.setdefault("download_notes", []).append("contexto da apolice aberto por busca")
                    return True
            if await _open_policy_detail_from_customer(page, item, evidence):
                return True
            clicked_search_row, search_row_trace = await _capture_page_activity(
                page,
                "click_search_result_row",
                lambda: _click_row_candidate(page, click_terms, timeout_ms=1200),
                wait_ms=900,
            )
            _remember_evidence_list(evidence, "interaction_traces", search_row_trace, limit=16)
            if clicked_search_row:
                if await _wait_until_policy_context(page, timeout_ms=8000):
                    text = await _all_body_text(page)
                    if _policy_context_matches_item(text, item):
                        evidence.setdefault("download_notes", []).append("contexto da apolice aberto por linha de busca")
                        return True
                if await _open_policy_detail_from_customer(page, item, evidence):
                    return True
            clicked_search_text, search_text_trace = await _capture_page_activity(
                page,
                "click_search_result_text",
                lambda: _click_text_candidate(page, click_terms, timeout_ms=1200),
                wait_ms=900,
            )
            _remember_evidence_list(evidence, "interaction_traces", search_text_trace, limit=16)
            if clicked_search_text:
                if await _wait_until_policy_context(page, timeout_ms=8000):
                    text = await _all_body_text(page)
                    if _policy_context_matches_item(text, item):
                        evidence.setdefault("download_notes", []).append("contexto da apolice aberto por resultado de busca")
                        return True
                if await _open_policy_detail_from_customer(page, item, evidence):
                    return True
            await _record_policy_search_debug(page, item, evidence, "policy_context_not_opened_after_search", term)
            # Higiene entre termos: dialogo residual da tentativa anterior não pode
            # contaminar a próxima busca.
            await _dismiss_blocking_modal(page)
        # Todos os termos falharam nesta passada. Uma única vez: relogin fresco
        # (sessão restaurada degrada a busca — ver _relogin_fresh) e repete.
        if attempt == 0 and await _relogin_fresh(page, params, evidence):
            evidence.setdefault("download_notes", []).append("repetindo busca apos relogin fresco")
            continue
        break
    evidence.setdefault("download_notes", []).append("contexto da apolice nao abriu")
    return False


def _attach_page_diagnostics(target, sink: List[str]) -> None:
    """Coleta erros de console/página/rede do popup da Ficha de Gestão: o corpo
    veio VAZIO após 25s em produção (job efcebf9c) e sem isso não dá para saber
    se o Angular não sobe, se a rede falha ou se o server nega."""
    def _console(msg):
        try:
            if getattr(msg, "type", "") in ("error", "warning"):
                sink.append(f"console.{msg.type}: {str(msg.text)[:140]}")
        except Exception:  # noqa: BLE001
            pass

    def _pageerror(err):
        try:
            sink.append(f"pageerror: {str(err)[:140]}")
        except Exception:  # noqa: BLE001
            pass

    def _requestfailed(req):
        try:
            sink.append(f"reqfail: {str(req.url)[:110]} {str(req.failure or '')[:60]}")
        except Exception:  # noqa: BLE001
            pass

    def _response(resp):
        try:
            if int(getattr(resp, "status", 0) or 0) >= 400:
                headers = getattr(resp.request, "headers", {}) or {}
                auth = "com-auth-header" if "authorization" in {k.lower() for k in headers} else "SEM-auth-header"
                sink.append(f"http{resp.status}: {str(resp.url)[:110]} [{auth}]")
        except Exception:  # noqa: BLE001
            pass

    try:
        target.on("console", _console)
        target.on("pageerror", _pageerror)
        target.on("requestfailed", _requestfailed)
        target.on("response", _response)
    except Exception:  # noqa: BLE001
        pass


async def _page_html_head(target, limit: int = 400) -> str:
    try:
        return _clean_text(await target.content())[:limit]
    except Exception as e:  # noqa: BLE001
        return f"<content indisponivel: {type(e).__name__}>"


async def _find_ficha_gestao_page(page):
    """O botão pode abrir a Ficha de Gestão numa aba que o expect_popup não
    capturou (janela nomeada / popup antes do arm). Varre as abas do contexto."""
    try:
        pages = list(getattr(page.context, "pages", []) or [])
    except Exception:  # noqa: BLE001
        return None
    for candidate in pages:
        try:
            url = str(getattr(candidate, "url", "")).lower().replace("-", "")
            if "filemanagement" in url:
                return candidate
        except Exception:  # noqa: BLE001
            continue
    return None


async def _open_ficha_gestao_for_item(page, item: Dict[str, Any], evidence: Dict[str, Any]):
    if _looks_like_ficha_gestao(await _all_body_text(page)):
        return page
    _ = item
    # O popup herda uma CÓPIA do sessionStorage do opener; o app da ficha lê
    # a chave PLANA 'access_token' (tokenGetter do bundle). Garante que ela
    # exista antes do clique para o popup nascer autenticado.
    try:
        await page.evaluate(
            """() => {
              if (!sessionStorage.getItem('access_token')) {
                const raw = sessionStorage.getItem('STORAGE_NGX-AZB-EPAC::access_token') || '';
                let tok = raw;
                try {
                  const p = JSON.parse(raw);
                  if (typeof p === 'string') tok = p;
                  else if (p && typeof p.value === 'string') tok = p.value;
                } catch (e) {}
                if (tok) sessionStorage.setItem('access_token', tok);
              }
            }"""
        )
    except Exception:  # noqa: BLE001
        pass
    target = None
    clicked_trusted = False
    try:
        async with page.expect_popup(timeout=9000) as popup_info:
            clicked_trusted = await _click_section_button_candidate_trusted(
                page, ("Ficha Gestao", "Ficha de Gestao"), timeout_ms=800
            )
        if clicked_trusted:
            target = await popup_info.value
            try:
                await target.wait_for_load_state("domcontentloaded", timeout=9000)
            except Exception:  # noqa: BLE001
                pass
            await target.wait_for_timeout(1200)
    except Exception:  # noqa: BLE001
        if clicked_trusted:
            target = page
    if target is None and clicked_trusted:
        target = await _find_ficha_gestao_page(page)
    diag: List[str] = []
    if target is not None and target is not page:
        _attach_page_diagnostics(target, diag)
    # App Angular (ngx-file-management) demora para montar a lista no VPS —
    # espera longa aqui é barata comparada a perder o boleto.
    if target and await _wait_until_ficha_gestao(target, timeout_ms=25000):
        evidence.setdefault("download_notes", []).append("ficha gestao aberta por clique trusted")
        return target
    if target and target is not page:
        snippet = _clean_text(await _all_body_text(target))[:280]
        evidence.setdefault("download_notes", []).append(f"popup pos-clique sem lista: '{snippet[:160]}'")
        evidence["ficha_gestao_popup_debug"] = {
            "url_path": urlsplit(str(getattr(target, "url", ""))).path,
            "html_head": await _page_html_head(target),
            "diag": diag[:10],
        }
        try:
            await target.close()
        except Exception:  # noqa: BLE001
            pass

    direct_url = await _section_button_new_window_url(page, ("Ficha Gestao", "Ficha de Gestao"))
    if direct_url:
        direct_target = None
        direct_diag: List[str] = []
        try:
            evidence["ficha_gestao_url_params"] = sorted({k for k, _ in parse_qsl(urlsplit(direct_url).query)})
            direct_target = await page.context.new_page()
            _attach_page_diagnostics(direct_target, direct_diag)
            # window.open real herda o sessionStorage do opener; new_page() não.
            # O token de API do app pode viver lá — semeia antes do boot.
            try:
                session_dump = await page.evaluate("() => JSON.stringify(sessionStorage)")
                if session_dump and session_dump != "{}":
                    await direct_target.add_init_script(
                        "try { const d = " + session_dump + "; "
                        "for (const k in d) { try { sessionStorage.setItem(k, d[k]); } catch (e) {} } } catch (e) {}"
                    )
            except Exception:  # noqa: BLE001
                pass
            resp = await direct_target.goto(direct_url, wait_until="commit", timeout=15000)
            try:
                await direct_target.wait_for_load_state("load", timeout=12000)
            except Exception:  # noqa: BLE001
                pass
            await direct_target.wait_for_timeout(2500)
            if await _wait_until_ficha_gestao(direct_target, timeout_ms=25000):
                evidence.setdefault("download_notes", []).append("ficha gestao aberta por janela operacional Allianz")
                return direct_target
            snippet = _clean_text(await _all_body_text(direct_target))[:280]
            evidence.setdefault("download_notes", []).append(
                f"ficha gestao abriu URL operacional mas nao carregou a lista: '{snippet[:160]}'"
            )
            evidence["ficha_gestao_direct_debug"] = {
                "status": getattr(resp, "status", None),
                "final_url_path": urlsplit(str(getattr(direct_target, "url", ""))).path,
                "html_head": await _page_html_head(direct_target),
                "diag": direct_diag[:10],
            }
            # Fix da causa-raiz do 401 (bundle chunk-PD6FDXSL do app): o
            # tokenGetter é sessionStorage.getItem('access_token') — chave
            # PLANA que a nossa sessão não tem (só a namespaced do shell EPAC
            # e a plana refresh_token). Sem ela o interceptor JWT não anexa
            # Authorization. Semeia a chave e recarrega para o app autenticar.
            url_token = ""
            for k, v in parse_qsl(urlsplit(direct_url).query):
                if k.lower() == "accesstoken":
                    url_token = v
                    break
            epac_token = ""
            try:
                epac_token = await page.evaluate(
                    """() => {
                      const raw = sessionStorage.getItem('STORAGE_NGX-AZB-EPAC::access_token') || '';
                      try {
                        const p = JSON.parse(raw);
                        if (typeof p === 'string') return p;
                        if (p && typeof p.value === 'string') return p.value;
                      } catch (e) {}
                      return raw;
                    }"""
                )
            except Exception:  # noqa: BLE001
                pass
            seeded = False
            for label, tok in (("url_token", url_token), ("epac_token", epac_token)):
                if not tok:
                    continue
                try:
                    await direct_target.evaluate("(t) => sessionStorage.setItem('access_token', t)", tok)
                    await direct_target.reload(wait_until="commit", timeout=15000)
                    await direct_target.wait_for_timeout(2000)
                except Exception:  # noqa: BLE001
                    continue
                if await _wait_until_ficha_gestao(direct_target, timeout_ms=20000):
                    evidence.setdefault("download_notes", []).append(
                        f"ficha gestao autenticada semeando sessionStorage.access_token ({label})"
                    )
                    seeded = True
                    break
                evidence.setdefault("download_notes", []).append(
                    f"seed access_token ({label}) nao destravou a lista: "
                    f"'{_clean_text(await _all_body_text(direct_target))[:120]}'"
                )
            if seeded:
                return direct_target
        except Exception as e:  # noqa: BLE001
            evidence.setdefault("download_notes", []).append(f"ficha gestao por URL falhou: {type(e).__name__}")
            evidence["ficha_gestao_direct_debug"] = {"error": f"{type(e).__name__}: {str(e)[:120]}", "diag": direct_diag[:10]}
        if direct_target:
            try:
                await direct_target.close()
            except Exception:  # noqa: BLE001
                pass

    target = None
    clicked_section = False
    try:
        async with page.expect_popup(timeout=9000) as popup_info:
            clicked_section = await _click_section_button_candidate(
                page, ("Ficha Gestao", "Ficha de Gestao"), timeout_ms=800
            )
        if clicked_section:
            target = await popup_info.value
            try:
                await target.wait_for_load_state("domcontentloaded", timeout=9000)
            except Exception:  # noqa: BLE001
                pass
            await target.wait_for_timeout(1200)
    except Exception:  # noqa: BLE001
        if clicked_section:
            target = page
    if target is None:
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
                # Home limpa entre itens: a busca global parte de qualquer página.
                await page.goto(ALLIANZ_PRIVATE_HOME, wait_until="domcontentloaded")
                await page.wait_for_timeout(1500)
            # Fluxo real do corretor: busca por nome -> cliente -> Operar ->
            # Detalhe de apólice -> Lista Recibos.
            opened = await _open_receipts_for_item(page, item, params, evidence)
            ctx = page if opened else None
            if ctx is None:
                # Fallback (print p8): a página do cliente tem botão 'FICHA
                # GESTÃO' direto — a carta aparece lá mesmo sem a Lista Recibos.
                body_raw = await _all_body_text(page)
                if "ficha gest" in _norm(body_raw) and _policy_context_matches_customer(body_raw, item):
                    evidence.setdefault("download_notes", []).append("fallback: ficha gestao direto da pagina do cliente")
                    ctx = page
            if ctx is not None:
                item = _merge_recibos_context(item, await _all_body_text(ctx))
                rows = await _extract_visible_rows(ctx)
                pendentes = extract_recibos_from_rows(rows)
                result["recibos_pendentes"] = pendentes[:5]
                ficha = await _open_ficha_gestao_for_item(ctx, item, evidence)
                if ficha:
                    if await _select_carta_inadimplencia(ficha, evidence):
                        await ficha.wait_for_timeout(1200)
                    download = await _download_current_pdf(ficha, item, params)
                    result.update(download)
                    if ficha is not ctx and ficha is not page:
                        try:
                            await ficha.close()
                        except Exception:  # noqa: BLE001
                            pass
                else:
                    result["reason"] = "ficha gestao nao encontrada"
                if ctx is not page:
                    try:
                        await ctx.close()
                    except Exception:  # noqa: BLE001
                        pass
                out.append(result)
                continue
            else:
                result["reason"] = "listagem de recibos nao encontrada"
        except Exception as e:  # noqa: BLE001
            result["reason"] = f"{type(e).__name__}: {str(e)[:160]}"
        out.append(result)
    return out


async def _return_to_inadimplentes_totals(page) -> bool:
    if _looks_like_inadimplentes_totals(await _all_body_text(page)):
        return True
    if await _click_text_candidate(page, ("Voltar",), timeout_ms=1800):
        deadline = 10
        for _ in range(deadline):
            if _looks_like_inadimplentes_totals(await _all_body_text(page)):
                return True
            await page.wait_for_timeout(600)
    try:
        await page.go_back(wait_until="domcontentloaded", timeout=6000)
        await page.wait_for_timeout(1200)
    except Exception:  # noqa: BLE001
        pass
    return _looks_like_inadimplentes_totals(await _all_body_text(page))


async def _extract_current_inadimplentes_result(page, max_items: int, evidence: Dict[str, Any]) -> List[Dict[str, Any]]:
    expanded = await _expand_inadimplente_details(page, max_items=max_items)
    evidence["inadimplentes_details_expanded"] = int(evidence.get("inadimplentes_details_expanded") or 0) + expanded
    rows = await _extract_visible_rows(page)
    evidence["inadimplentes_rows_seen"] = int(evidence.get("inadimplentes_rows_seen") or 0) + len(rows)
    segurado_rows = [
        _clean_text((r.get("detail") or r.get("text") or ""))[:500]
        for r in rows
        if re.search(r"Segurado\s*:|CPF/?CNPJ\s*:", _clean_text((r.get("detail") or r.get("text") or "")), flags=re.IGNORECASE)
    ]
    evidence["inadimplentes_detail_rows_seen"] = int(evidence.get("inadimplentes_detail_rows_seen") or 0) + len(segurado_rows)
    return extract_inadimplentes_from_rows(rows)


async def _collect_inadimplentes_items(page, max_items: int, evidence: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not _looks_like_inadimplentes_totals(await _all_body_text(page)):
        return await _extract_current_inadimplentes_result(page, max_items, evidence)

    totals_rows = await _extract_visible_rows(page)
    totals = extract_totals_from_rows(totals_rows)
    evidence["inadimplentes_totals"] = totals[:20]
    items: List[Dict[str, Any]] = []
    seen = set()
    for idx, total in enumerate(totals):
        if len(items) >= max_items:
            break
        if not await _click_totals_row_by_index(page, idx):
            evidence.setdefault("download_notes", []).append(f"nao abriu ramo total {idx + 1}: {total.get('ramo')}")
            continue
        if not await _wait_until_inadimplentes_result(page, timeout_ms=9000):
            evidence.setdefault("download_notes", []).append(f"ramo sem resultado por parcela: {total.get('ramo')}")
            await _return_to_inadimplentes_totals(page)
            continue
        branch_items = await _extract_current_inadimplentes_result(page, max_items - len(items), evidence)
        for item in branch_items:
            key = (
                str(item.get("recibo") or ""),
                str(item.get("apolice_susep") or ""),
                str(item.get("cpf_cnpj") or ""),
            )
            if key in seen:
                continue
            seen.add(key)
            items.append({**item, "ramo_total": total.get("ramo")})
            if len(items) >= max_items:
                break
        if idx < len(totals) - 1:
            if not await _return_to_inadimplentes_totals(page):
                evidence.setdefault("download_notes", []).append("nao consegui voltar para Resultado - Totais")
                break
    return items


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
    evidence["inadimplentes_details_expanded"] = 0
    evidence["inadimplentes_detail_rows_seen"] = 0
    evidence["inadimplentes_rows_seen"] = 0
    items = await _collect_inadimplentes_items(page, max_expand, evidence)
    evidence["inadimplentes_count"] = len(items)
    evidence["inadimplentes_sample"] = [
        {
            "recibo": i.get("recibo"),
            "apolice_susep": i.get("apolice_susep"),
            "vencimento": i.get("vencimento"),
            "valor": i.get("valor"),
            "cliente_nome": i.get("cliente_nome"),
            "cpf_cnpj": i.get("cpf_cnpj"),
            "ramo_total": i.get("ramo_total"),
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
            message = "inadimplentes extraidos, mas o download de boletos precisa de revisao humana"
            # Aprendizado 2026-07-10: a busca de clientes da Allianz devolve
            # 'sem resultados' p/ clientes EXISTENTES fora do horario comercial
            # (mesma cliente achada as 13h22, vazia as 01h-02h). Orientar o
            # operador em vez de parecer bug do worker.
            if int(evidence.get("empty_search_terms") or 0) >= 2:
                message += (
                    " (busca de clientes do portal devolveu vazio para varios termos —"
                    " provavel indisponibilidade fora do horario comercial; reexecutar entre 9h-18h)"
                )
            return JourneyResult(
                status="needs_human",
                captured={
                    "logged_in": True,
                    "stage": "boletos_nao_baixados",
                    "inadimplentes": items,
                    "boletos": boletos,
                },
                message=message,
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
