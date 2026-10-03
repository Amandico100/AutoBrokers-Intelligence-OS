# -*- coding: utf-8 -*-
"""SPEC-127 P2 — a PÁGINA FALSA do portal de vidros, guiada pelas ÁRVORES REAIS.

O dublê fica na BORDA (o navegador): cada tela é uma árvore de percepção
derivada do HTML real (`fixtures/vidros/telas_dom.py`), e a página responde aos
MESMOS `evaluate`/`query_selector_all` que o código do DOM faz — `capture_state`,
`_find_input`, `_apply_mdselect`, `_apply_check`, `_click_button`, o
autocomplete. O MOTOR (`run_adaptive`, a contenção, o validador, o passo 1 de
`vidros_lanternas.abrir_atendimento`) roda inteiro, de verdade (CLAUDE.md §9.4).

Escolha registrada (BLOCO 0: "o playwright não está no venv"): instalar
Playwright no venv compartilhado mexeria no ambiente de outros builders e da
bateria; a página falsa sobre a árvore real exercita o mesmo código Python sem
navegador. O que ela NÃO prova: o JS do `capture_state` dentro do Chromium.
"""
from __future__ import annotations

import copy
from typing import Any, Callable, Dict, List, Optional

from portal_worker.adaptive import _norm as AD_norm
from tests.fixtures.vidros.telas_dom import TELAS

TELA_DO_PROTOCOLO = {
    "url": "", "heading": "Dados da apólice", "inputs": [], "selects": [], "mdselects": [],
    "radios": [], "questoes": [], "pending_required": [],
    "buttons": copy.deepcopy(TELAS["yelum_final"]["buttons"]),
    # 💭 número SINTÉTICO, no formato que `tem_protocolo` reconhece
    "text": "Dados da apólice Nº do atendimento: 40000001",
}


def tela(apelido: str) -> Dict[str, Any]:
    if apelido == "protocolo":
        return copy.deepcopy(TELA_DO_PROTOCOLO)
    return copy.deepcopy(TELAS[apelido])


class _Teclado:
    def __init__(self, pagina: "PaginaFalsa"):
        self.p = pagina

    async def press(self, tecla: str) -> None:
        if tecla == "Escape":
            self.p.aberto = None

    async def type(self, texto: str) -> None:
        self.p.log.append(("digitou_data", ""))


class _Mouse:
    async def click(self, *a: Any) -> None:
        return None


class _Botao:
    def __init__(self, p: "PaginaFalsa", texto: str, desabilitado: bool = False):
        self.p, self.texto, self.desabilitado = p, texto, desabilitado

    async def is_visible(self) -> bool:
        return True

    async def is_disabled(self) -> bool:
        # O `Avançar` do portal fica desabilitado enquanto houver obrigatório vazio
        # (📊 `ng-invalid-required` nas árvores reais) — e só por isso.
        if AD_norm(self.texto).startswith("avan"):
            t = self.p.tela
            return any(c.get("empty_required") and not str(c.get("value") or "").strip()
                       for c in list(t.get("inputs") or []) + list(t.get("mdselects") or []))
        return self.desabilitado

    async def inner_text(self) -> str:
        return self.texto

    async def get_attribute(self, _k: str) -> str:
        return ""

    async def click(self, **_k: Any) -> None:
        self.p.clicar(self.texto)


class _Campo:
    def __init__(self, p: "PaginaFalsa", campo: Dict[str, Any]):
        self.p, self.campo = p, campo

    async def is_visible(self) -> bool:
        return True

    async def fill(self, valor: str) -> None:
        self.campo["value"] = str(valor)
        self.p.ultimo_preenchido = self.campo
        self.p.log.append(("fill", self.campo.get("id") or self.campo.get("name"), str(valor)))

    async def click(self, **_k: Any) -> None:
        self.p.ultimo_preenchido = self.campo

    async def evaluate(self, js: str, *a: Any) -> Any:
        if "closest('label')" in js:          # o card da cobertura da Porto
            for r in self.p.tela.get("radios") or []:
                if r.get("name") == self.campo.get("name"):
                    r["checked"] = r.get("value") == self.campo.get("value")
            self.p.log.append(("cobertura", self.campo.get("value")))
            return None
        if "e.checked" in js:
            return any(r.get("checked") and r.get("value") == self.campo.get("value")
                       for r in self.p.tela.get("radios") or [])
        return None


class _MdSelect:
    def __init__(self, p: "PaginaFalsa", md: Dict[str, Any]):
        self.p, self.md = p, md

    async def get_attribute(self, k: str) -> str:
        return {"name": self.md.get("name"), "id": self.md.get("id")}.get(k) or ""

    async def scroll_into_view_if_needed(self, **_k: Any) -> None:
        return None

    async def click(self, **_k: Any) -> None:
        self.p.aberto = self.md


class _Opcao:
    def __init__(self, p: "PaginaFalsa", md: Dict[str, Any], texto: str):
        self.p, self.md, self.texto = p, md, texto

    async def is_visible(self) -> bool:
        return True

    async def inner_text(self) -> str:
        return self.texto

    async def click(self, **_k: Any) -> None:
        self.md["value"], self.md["vazio"], self.md["empty_required"] = self.texto, False, False
        self.p.aberto = None
        self.p.log.append(("select", self.md.get("name"), self.texto))


class _Radio:
    def __init__(self, p: "PaginaFalsa", q: Dict[str, Any], opcao: str):
        self.p, self.q, self.opcao = p, q, opcao

    async def is_visible(self) -> bool:
        return True

    async def get_attribute(self, k: str) -> str:
        if k == "aria-disabled":
            return "true" if self.q.get("respondida") else "false"
        if k == "aria-label":
            return self.opcao
        return ""

    async def inner_text(self) -> str:
        return self.opcao

    async def click(self, **_k: Any) -> None:
        self.q["respondida"], self.q["escolhida"] = True, self.opcao
        self.p.log.append(("check", self.q.get("pergunta"), self.opcao))


class PaginaFalsa:
    """`telas` = {apelido: árvore}; `fluxo` = {(apelido, botão): próximo apelido}."""

    def __init__(self, inicio: str, fluxo: Optional[Dict[tuple, str]] = None,
                 sugestoes: Optional[Dict[str, List[str]]] = None,
                 ao_clicar: Optional[Callable[["PaginaFalsa", str], None]] = None,
                 telas: Optional[Dict[str, Dict[str, Any]]] = None):
        self.telas: Dict[str, Dict[str, Any]] = telas or {}
        self.atual = inicio
        if inicio not in self.telas:
            self.telas[inicio] = tela(inicio)
        self.fluxo = fluxo or {}
        self.sugestoes = sugestoes or {}
        self.ao_clicar = ao_clicar
        self.log: List[tuple] = []
        self.cliques: List[str] = []
        self.aberto: Optional[Dict[str, Any]] = None
        self.ultimo_preenchido: Optional[Dict[str, Any]] = None
        self.keyboard = _Teclado(self)
        self.mouse = _Mouse()
        self.url = "https://portal.invalid/#/x/passo1/abcdefghijklmnopqrstuvwxyz0123"
        self.relogio: List[str] = []   # a ORDEM global: cliques e checkpoints

    @property
    def tela(self) -> Dict[str, Any]:
        return self.telas[self.atual]

    def clicar(self, texto: str) -> None:
        self.cliques.append(texto)
        self.relogio.append(f"clique:{texto}")
        self.log.append(("click", texto))
        if self.ao_clicar:
            self.ao_clicar(self, texto)
        prox = self.fluxo.get((self.atual, texto))
        if prox:
            if prox not in self.telas:
                self.telas[prox] = tela(prox)
            self.atual = prox

    # ---- a superfície do Playwright que o DOM usa ------------------------
    async def wait_for_timeout(self, _ms: int) -> None:
        return None

    async def screenshot(self, **_k: Any) -> bytes:
        return b"jpeg"

    async def inner_text(self, _sel: str) -> str:
        return str(self.tela.get("text") or "")

    async def goto(self, *_a: Any, **_k: Any) -> None:
        return None

    async def query_selector(self, sel: str):
        if "tipoAtendimento" in sel:
            valor = sel.split("value='")[-1].split("'")[0]
            for c in self.tela.get("inputs") or []:
                if c.get("name") == "tipoAtendimento" and c.get("value") == valor:
                    return _Campo(self, c)
            return None
        return None

    async def query_selector_all(self, sel: str):
        t = self.tela
        if sel.startswith("md-radio-button"):
            return [_Radio(self, q, o) for q in t.get("questoes") or [] for o in q.get("opcoes") or []]
        if sel.startswith("button"):
            return [_Botao(self, b.get("text") or "", bool(b.get("disabled"))) for b in t.get("buttons") or []]
        if sel == "input,textarea":
            return [_Campo(self, c) for c in t.get("inputs") or []]
        if sel == "md-select":
            return [_MdSelect(self, m) for m in t.get("mdselects") or []]
        if sel == "md-option":
            return [_Opcao(self, self.aberto, o) for o in (self.aberto or {}).get("options") or []]
        return []

    async def evaluate(self, js: str, *a: Any) -> Any:
        t = self.tela
        if "pending_required" in js:                                  # capture_state
            s = copy.deepcopy(t)
            s["url"] = self.url
            return s
        if "ph:e.placeholder" in js:                                  # _find_input
            return [{"id": c.get("id") or "", "name": c.get("name") or "", "ph": c.get("placeholder") or "",
                     "lab": c.get("label") or "", "vis": True} for c in t.get("inputs") or []]
        if "txt: [e.name" in js:                                      # _achar_campo (passo 1)
            return [{"i": i, "txt": " ".join(str(c.get(k) or "") for k in ("name", "id", "placeholder", "label")),
                     "vis": True} for i, c in enumerate(t.get("inputs") or [])]
        if "ng-invalid-required,textarea" in js:
            return []
        if "closest('md-input-container" in js and "md-select" in js:  # rótulos dos md-select
            return [m.get("label") or "" for m in t.get("mdselects") or []]
        if "lis[i].click()" in js:                                    # autocomplete: o clique
            i = a[0] if a else 0
            lista = self.sugestoes.get((self.ultimo_preenchido or {}).get("id") or "", [])
            if self.ultimo_preenchido is not None and 0 <= i < len(lista):
                self.ultimo_preenchido["value"] = lista[i]
                self.log.append(("autocomplete", self.ultimo_preenchido.get("id"), lista[i]))
            return None
        if "slice(0, 20)" in js:                                      # autocomplete: a leitura
            return list(self.sugestoes.get((self.ultimo_preenchido or {}).get("id") or "", []))
        if "hit.click()" in js:                                       # autocomplete antigo
            return {"found": 0}
        if "document.body.innerText" in js:
            return str(t.get("text") or "")
        return {}


class RuntimeFalso:
    """O `_runtime` que o worker injeta: guard com checkpoint, na ORDEM global."""

    def __init__(self, pagina: PaginaFalsa, liberado: bool):
        from portal_worker.guardrails import PortalActionGuard

        self.pagina = pagina
        self.gravacoes: List[Dict[str, Any]] = []
        self.guard = PortalActionGuard(material_liberado=liberado, _checkpoint=self.checkpoint)
        self.company_id, self.job_id = "", ""

    async def checkpoint(self, patch: Dict[str, Any]) -> None:
        self.gravacoes.append(patch)
        fase = (patch.get("critical_effect") or {}).get("phase")
        self.pagina.relogio.append(f"efeito:{fase}")
