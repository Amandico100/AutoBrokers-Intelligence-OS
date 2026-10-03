# -*- coding: utf-8 -*-
"""SPEC-127 P2 — a ÁRVORE DE PERCEPÇÃO de uma tela salva do portal de vidros.

O espelho em Python do `adaptive.capture_state` (o JS que roda no navegador),
para provar as funções puras do DOM sobre o HTML REAL do intake sem Playwright
(📊 BLOCO 0: `playwright` NÃO está no `backend/.venv`; está só no contêiner do
portal-worker, `portal_worker/requirements.txt`).

🔴 Só ESTRUTURA sai daqui: rótulos, nomes, ids, opções, botões, perguntas. O
valor digitado vira `""`/`"[preenchido]"` e o texto da tela NÃO é lido — o
`text` da árvore é sintetizado do heading, das perguntas e dos botões. Os HTML
do intake têm nome, CPF, placa e token (`docs/intake/materiais/portal-vidros/`,
fora do Git); a fixture derivada (`fixtures/vidros/telas_dom.py`) nasce daqui e
o teste prova por grep que ela não carrega PII.

Requer `lxml` (presente no venv de desenvolvimento; NÃO em `requirements.txt`) —
quem usa este módulo faz `pytest.importorskip("lxml")`.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

def pasta_do_intake() -> Path:
    """O acervo LOCAL (fora do Git). Num worktree ele não existe: aponte
    `AUTOBROKERS_INTAKE_VIDROS` para a pasta da árvore principal."""
    import os

    env = os.environ.get("AUTOBROKERS_INTAKE_VIDROS", "").strip()
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "docs" / "intake" / "materiais" / "portal-vidros"


# As telas que a fixture deriva — (apelido, caminho relativo no intake).
TELAS = (
    ("porto_passo1_cobertura", "PORTO/1 Atendimento Web.html"),
    ("yelum_passo1", "YELUM/YELUM PARA BRISA/Atendimento Web.html"),
    ("porto_cidade", "PORTO/2 LANTERNA MALA Atendimento Web.html"),
    ("yelum_contato_20", "YELUM/YELUM LATARIA/Atendimento Web TELA 20%.html"),
    ("yelum_parabrisa_50_peca_causa", "YELUM/YELUM PARA BRISA/Atendimento Web TELA 3.html"),
    ("yelum_lataria_50_cidade_cep", "YELUM/YELUM LATARIA/Atendimento Web TELA 50% CIDADE CEP.html"),
    ("yelum_parabrisa_reparo", "YELUM/YELUM PARA BRISA/Atendimento Web TELA 5.html"),
    ("yelum_lateral_80", "YELUM/YELUM VIDRO LATERAL/Atendimento Web TELA 80%.html"),
    ("yelum_antigo_80", "YELUM/YELUM VIDROS ANTIGO/3 TELA DE QUAL VIDROO Atendimento Web.html"),
    ("yelum_lataria_pecas", "YELUM/YELUM LATARIA/Atendimento Web TELA LOCAL DO DANO DEPOIS DE 50%.html"),
    ("yelum_final", "YELUM/YELUM VIDRO LATERAL/Atendimento Web TELA FINAL.html"),
)


def _limpa(t: Any) -> str:
    return re.sub(r"\s+", " ", str(t or "")).strip()


def _oculto(el) -> bool:
    while el is not None:
        cls = el.get("class") or ""
        st = (el.get("style") or "").replace(" ", "").lower()
        if (re.search(r"\bng-hide\b", cls) or "display:none" in st or el.get("hidden") is not None
                or el.tag in ("script", "style", "template")):
            return True
        el = el.getparent()
    return False


def _label_de(el, labels_for: Dict[str, str]) -> str:
    """`e.labels[0]` (for=id ou label ancestral) || aria-label || placeholder."""
    if el.get("id") and el.get("id") in labels_for:
        return labels_for[el.get("id")]
    p = el.getparent()
    while p is not None:
        if p.tag == "label":
            return _limpa(p.text_content())
        p = p.getparent()
    return _limpa(el.get("aria-label") or el.get("placeholder") or "")


def _md_label(m) -> str:
    p = m.getparent()
    while p is not None:
        if p.tag in ("md-input-container", "md-autocomplete") or "md-input-container" in (p.get("class") or ""):
            lab = p.find(".//label")
            if lab is not None:
                return _limpa(lab.text_content())
            break
        p = p.getparent()
    return _limpa(m.get("aria-label") or m.get("name") or m.get("id"))


def arvore_do_html(caminho: Path) -> Dict[str, Any]:
    import lxml.html as LH

    doc = LH.fromstring(Path(caminho).read_bytes())
    for lixo in doc.xpath("//script|//style|//noscript|//svg"):
        lixo.drop_tree()
    labels_for = {lab.get("for"): _limpa(lab.text_content()) for lab in doc.iter("label") if lab.get("for")}

    inputs: List[Dict[str, Any]] = []
    for e in doc.xpath("//input|//textarea"):
        if _oculto(e) or (e.get("type") or "").lower() == "hidden":
            continue
        cls = e.get("class") or ""
        bruto = e.get("value") if e.tag == "input" else (e.text or "")
        tipo = (e.get("type") or ("textarea" if e.tag == "textarea" else "")).lower()
        valor = ""
        if tipo in ("radio", "checkbox"):
            valor = _limpa(e.get("value") or "")[:4]  # 1/2 da cobertura, nunca dado
        elif str(bruto or "").strip():
            valor = "[preenchido]"
        inputs.append({"id": e.get("id") or "", "name": e.get("name") or "", "type": e.get("type") or "",
                       "placeholder": e.get("placeholder") or "", "value": valor,
                       "label": _label_de(e, labels_for),
                       "required": e.get("required") is not None or "ng-required" in cls,
                       "empty_required": "ng-invalid-required" in cls})

    selects = []
    for s in doc.xpath("//select"):
        if _oculto(s):
            continue
        ops = [_limpa(o.text_content()) for o in s.xpath(".//option") if _limpa(o.text_content())]
        sel = [o for o in s.xpath(".//option") if o.get("selected") is not None]
        selects.append({"name": s.get("name") or "", "label": _label_de(s, labels_for),
                        "value": _limpa(sel[0].text_content()) if sel else "", "options": ops})

    mdselects = []
    for m in doc.xpath("//md-select"):
        if _oculto(m):
            continue
        cls = m.get("class") or ""
        cont = m.xpath(".//div[contains(@class,'md-select-menu-container')]")
        if not cont and m.get("aria-owns"):
            cont = doc.xpath(f"//*[@id='{m.get('aria-owns')}']")
        ops = [_limpa(o.text_content()) for o in (cont[0].xpath(".//md-option") if cont else [])]
        ops = [o for o in ops if o and not o.lower().startswith("selecione")]
        v = m.xpath(".//md-select-value")
        valor = _limpa(v[0].text_content()) if v else ""
        if (valor.lower().startswith("selecione") or "ng-empty" in cls
                or (v and "md-select-placeholder" in (v[0].get("class") or ""))):
            valor = ""  # vazio: o md-select-value mostra o PLACEHOLDER (o próprio rótulo)
        mdselects.append({"id": m.get("id") or "", "name": m.get("name") or "", "label": _md_label(m),
                          "value": valor, "options": ops, "vazio": "ng-empty" in cls,
                          "empty_required": bool(re.search("ng-invalid-required|ng-empty", cls))
                          and bool(re.search("ng-required|ng-invalid", cls))})

    botoes = [{"text": _limpa(b.text_content()), "disabled": b.get("disabled") is not None}
              for b in doc.xpath("//button") if not _oculto(b) and _limpa(b.text_content())]

    radios = []
    for r in doc.xpath("//input[@type='radio']|//input[@type='checkbox']"):
        if _oculto(r):
            continue
        radios.append({"name": r.get("name") or "", "checked": r.get("checked") is not None,
                       "label": _label_de(r, labels_for), "value": _limpa(r.get("value") or "")[:4]})

    questoes = []
    for g in doc.xpath("//md-radio-group"):
        if _oculto(g):
            continue
        item = next((a for a in g.iterancestors() if "aw-question-item" in (a.get("class") or "")),
                    g.getparent())
        lab = item.find(".//label") if item is not None else None
        bts = g.xpath(".//md-radio-button")
        marcada = [b for b in bts if "md-checked" in (b.get("class") or "")]
        questoes.append({"id": g.get("id") or "", "pergunta": _limpa(lab.text_content()) if lab is not None else "",
                         "opcoes": [_limpa(b.get("aria-label") or b.text_content()) for b in bts],
                         "respondida": bool(marcada),
                         "escolhida": _limpa(marcada[0].get("aria-label") or marcada[0].text_content())
                         if marcada else ""})

    h = doc.xpath("//h1|//h2|//h3|//*[contains(concat(' ',@class,' '),' titulo ')]"
                  "|//*[contains(concat(' ',@class,' '),' title ')]")
    heading = _limpa(h[0].text_content()) if h else ""
    pend = ([{"tipo": "input", "label": e["label"] or e["id"] or e["name"]} for e in inputs if e["empty_required"]]
            + [{"tipo": "select", "label": m["label"] or m["name"] or m["id"]} for m in mdselects
               if m["empty_required"]])
    # O `text` é SINTETIZADO — nunca o corpo da página (que traz nome/CPF/placa).
    texto = " ".join([heading] + [q["pergunta"] for q in questoes]
                     + [b["text"] for b in botoes])[:1500]
    return {"url": "", "heading": heading, "inputs": inputs, "selects": selects, "mdselects": mdselects,
            "buttons": botoes, "radios": radios, "questoes": questoes, "pending_required": pend,
            "text": texto}
