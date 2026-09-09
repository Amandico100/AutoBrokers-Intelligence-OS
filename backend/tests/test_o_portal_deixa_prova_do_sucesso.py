# -*- coding: utf-8 -*-
"""O portal deixa PROVA — inclusive do acionamento que deu certo.

📊 O defeito, medido em 08/09/2026 no `portal_worker`
====================================================

```
worker.py  if result.status == "needs_human":   ->  screenshot
adaptive.py  steps.append({"a","t","v"[:30],"r"[:80]})
```

🔴 **O unico desfecho que deixava imagem era o que dava errado.** Um
acionamento BEM-SUCEDIDO — com numero de atendimento aberto na seguradora, o
desfecho que alguem vai querer conferir quando o segurado ligar — nao deixava
foto nenhuma. E a trilha por passo nao dizia em QUE TELA cada acao aconteceu:
`fill cep` na tela do segurado e `fill cep` na tela da corretora eram a mesma
linha.

O que este guarda prova, e o que ele NAO prova
==============================================

Ele nao prova que o robo acerta o portal. Prova que, qualquer que seja o
desfecho, **fica uma imagem, uma trilha datada e uma frase que uma pessoa le**.

E ele chama os MOTORES de verdade (CLAUDE.md §9.4): `worker._run_job` inteiro
sobre um Playwright dublê, e `adaptive.run_adaptive` sobre uma pagina dublê.
Nenhuma asserção reimplementa o que quer medir.

⚠️ A LINHA DE CONTROLE, no fim: uma pagina que RECUSA fotografar nao pode
derrubar o acionamento. A prova e diagnostico; o pedido do segurado nao.

Rodar: python backend/tests/test_o_portal_deixa_prova_do_sucesso.py
House-style: sem pytest, stubs e `check`.
"""
from __future__ import annotations

import asyncio
import base64
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PASS = 0
FAIL = 0
FAILURES: list = []


def check(nome, cond, detalhe=None):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [ok] {nome}")
    else:
        FAIL += 1
        FAILURES.append((nome, detalhe))
        print(f"  [X] {nome}{': ' + str(detalhe) if detalhe else ''}")


JPEG = b"\xff\xd8\xff-jpeg-falso"
TELA_DO_PROTOCOLO = ("Solicitacao registrada\n"
                     "N do atendimento: 22842291\n"
                     "Escolha a loja onde deseja realizar o servico")


# ---------------------------------------------------------------------------
# DUBLÊS — uma pagina que fotografa, e um Supabase que guarda o que recebeu
# ---------------------------------------------------------------------------
class PaginaDublê:
    """Nem Playwright nem navegador: so as chamadas que o codigo faz.

    `recusa_full_page` reproduz o portal em que `full_page=True` levanta — a
    razao de a captura tentar a tela inteira e cair para o visivel.
    """

    def __init__(self, estado=None, texto="", url="https://portal.exemplo/passo",
                 recusa_full_page=False, recusa_tudo=False):
        self.estado = estado or {}
        self.texto = texto
        self.url = url
        self.recusa_full_page = recusa_full_page
        self.recusa_tudo = recusa_tudo
        self.fotos = []           # (url no momento da foto, full_page)
        self.esperas = []

    async def evaluate(self, script, *a, **kw):
        s = str(script)
        if "navigator.userAgent" in s:
            return "Mozilla/5.0 HeadlessChrome/126.0 Safari/537.36"
        if s.strip().startswith("() => (document.body.innerText"):
            return self.texto
        return dict(self.estado)

    async def screenshot(self, **kw):
        if self.recusa_tudo:
            raise RuntimeError("pagina fechada")
        if kw.get("full_page") and self.recusa_full_page:
            raise RuntimeError("full_page indisponivel neste alvo")
        self.fotos.append((self.url, bool(kw.get("full_page"))))
        return JPEG

    async def wait_for_timeout(self, ms):
        self.esperas.append(ms)

    def on(self, *a, **kw):
        return None

    async def close(self):
        return None


class _Storage:
    def __init__(self, dono):
        self.dono = dono

    def upload(self, caminho, blob, opts):
        if self.dono.cofre_recusa:
            raise RuntimeError("bucket indisponivel")
        self.dono.arquivos[caminho] = (blob, opts)
        return {"path": caminho}


class SupabaseDublê:
    def __init__(self, cofre_recusa=False):
        self.cofre_recusa = cofre_recusa
        self.arquivos = {}
        self.patches = []
        self._patch = None

    # ---- storage
    class _Bucket:
        def __init__(self, dono):
            self.dono = dono

        def from_(self, nome):
            assert nome == "portal-evidence", nome
            return _Storage(self.dono)

    @property
    def storage(self):
        return SupabaseDublê._Bucket(self)

    # ---- tabela
    def table(self, nome):
        assert nome == "portal_jobs", nome
        return self

    def update(self, patch):
        self._patch = dict(patch)
        return self

    def eq(self, *a, **kw):
        return self

    def execute(self):
        if self._patch is not None:
            self.patches.append(self._patch)
            self._patch = None
        return types.SimpleNamespace(data=[])

    @property
    def ultimo(self):
        return self.patches[-1] if self.patches else {}


def _playwright_falso(page):
    """Injeta um `playwright.async_api` que devolve SEMPRE esta pagina."""
    ctx = types.SimpleNamespace()

    async def _new_page():
        return page

    async def _close():
        return None

    async def _add_init_script(_s):
        return None

    async def _storage_state():
        return {}

    ctx.new_page = _new_page
    ctx.close = _close
    ctx.add_init_script = _add_init_script
    ctx.storage_state = _storage_state

    browser = types.SimpleNamespace(version="126.0")

    async def _new_context(**kw):
        return ctx

    browser.new_context = _new_context
    browser.close = _close

    chromium = types.SimpleNamespace()

    async def _launch(**kw):
        return browser

    chromium.launch = _launch

    class _PW:
        chromium_ = chromium

        async def __aenter__(self):
            return types.SimpleNamespace(chromium=chromium)

        async def __aexit__(self, *a):
            return False

    mod = types.ModuleType("playwright.async_api")
    mod.async_playwright = lambda: _PW()
    pai = types.ModuleType("playwright")
    pai.async_api = mod
    sys.modules["playwright"] = pai
    sys.modules["playwright.async_api"] = mod


def _rodar_job(page, resultado=None, excecao=None, cofre_recusa=False, evidence=None):
    """Roda `worker._run_job` INTEIRO com uma journey dublê. Devolve (supa, page)."""
    from portal_worker import journeys as _J
    from portal_worker import worker as W

    _playwright_falso(page)
    supa = SupabaseDublê(cofre_recusa=cofre_recusa)

    async def journey(pg, params, ev):
        ev.update(evidence or {})
        if excecao is not None:
            raise excecao
        return resultado

    barrar_original = _J.motivo_para_barrar
    get_original = _J.get_journey
    _J.motivo_para_barrar = lambda *a, **kw: ""
    _J.get_journey = lambda *a, **kw: journey
    try:
        asyncio.run(W._run_job(supa, {
            "id": "job-1", "company_id": "cia-1",
            "portal_key": "vidros_lanternas", "journey": "abrir_atendimento",
            "params": {}, "evidence": {},
        }))
    finally:
        _J.motivo_para_barrar = barrar_original
        _J.get_journey = get_original
    return supa


# ---------------------------------------------------------------------------
def run():
    print("== O portal deixa prova do sucesso ==\n")
    from portal_worker import adaptive as A
    from portal_worker import worker as W
    from portal_worker.journeys import JourneyResult

    # -----------------------------------------------------------------
    print("\n-- (a) o desfecho que DEU CERTO deixa foto --")
    page = PaginaDublê(texto=TELA_DO_PROTOCOLO, url="https://portal.exemplo/protocolo")
    supa = _rodar_job(page, resultado=JourneyResult(
        status="done", captured={"protocolo": "22842291"},
        message="atendimento aberto no portal, N 22842291"),
        evidence={"protocolo": "22842291",
                  "passo7": {"preferencia": "loja", "tem_loja": True,
                             "pedido_do_segurado": {"peca": "parabrisa"}}})
    ev = supa.ultimo.get("evidence") or {}
    provas = ev.get("prova") or []
    check("done grava status done", supa.ultimo.get("status") == "done", supa.ultimo.get("status"))
    check("done deixa PELO MENOS uma prova", len(provas) >= 1, ev.keys())
    check("a prova aponta para o cofre privado",
          bool(provas) and str(provas[0].get("onde", "")).startswith("portal-evidence/"), provas)
    check("a prova diz QUANDO foi tirada", bool(provas) and bool(provas[0].get("quando")), provas)
    check("o JPEG chegou ao bucket", any(v[0] == JPEG for v in supa.arquivos.values()),
          list(supa.arquivos))
    check("o base64 NAO ficou na evidencia", "b64" not in (provas[0] if provas else {}), provas)
    check("nada caiu no fallback base64", supa.ultimo.get("screenshots") == [],
          supa.ultimo.get("screenshots"))

    # -----------------------------------------------------------------
    print("\n-- (b) o desfecho que PEDE UMA PESSOA continua deixando foto --")
    page = PaginaDublê(texto="Confirme a peca danificada", url="https://portal.exemplo/80")
    supa = _rodar_job(page, resultado=JourneyResult(
        status="needs_human", captured={"stage": "confirme_80"},
        message="cheguei na confirmacao (80%) — aprove para enviar"),
        evidence={"stage_80": "Confirme a peca danificada\nParabrisa",
                  "passo": {"titulo": "Confirme a peca danificada"}})
    ev = supa.ultimo.get("evidence") or {}
    provas_h = ev.get("prova") or []
    check("needs_human grava status needs_human", supa.ultimo.get("status") == "needs_human")
    check("needs_human deixa prova", len(provas_h) >= 1, ev.keys())
    check("needs_human mantem o contrato hitl", (ev.get("hitl") or {}).get("required") is True, ev.get("hitl"))
    check("done e needs_human sao desfechos DIFERENTES e os dois deixam prova",
          len(provas) >= 1 and len(provas_h) >= 1 and provas[0].get("motivo") != provas_h[0].get("motivo"),
          (provas[:1], provas_h[:1]))

    # -----------------------------------------------------------------
    print("\n-- (b2) o desfecho que FALHOU deixa foto (pagina ainda viva) --")
    page = PaginaDublê(texto="erro", url="https://portal.exemplo/erro")
    supa = _rodar_job(page, excecao=RuntimeError("o portal caiu"))
    ev = supa.ultimo.get("evidence") or {}
    check("failed grava status failed", supa.ultimo.get("status") == "failed", supa.ultimo.get("status"))
    check("failed deixa prova", len(ev.get("prova") or []) >= 1, ev.keys())
    check("a foto do fracasso foi tirada com a pagina viva", len(page.fotos) >= 1, page.fotos)

    # -----------------------------------------------------------------
    print("\n-- (c) cada passo diz ONDE e QUANDO --")
    estado = {"url": "https://portal.exemplo/passo3", "heading": "Dados do solicitante",
              "inputs": [], "selects": [], "mdselects": [], "buttons": [{"text": "Avancar"}],
              "radios": [], "pending_required": [], "text": "Dados do solicitante"}
    page3 = PaginaDublê(estado=estado, texto="Dados do solicitante", url=estado["url"])
    evid = {}

    async def _decide(*a, **kw):
        return {"action": "click", "target": "Avancar", "value": "", "reason": "seguir"}

    async def _aplica(pg, acao):
        return "clicked"

    d0, a0 = A.decide_next_action, A.apply_action
    A.decide_next_action, A.apply_action = _decide, _aplica
    try:
        asyncio.run(A.run_adaptive(page3, "abrir atendimento", {}, evid, max_steps=2))
    finally:
        A.decide_next_action, A.apply_action = d0, a0
    passos = evid.get("adaptive_steps") or []
    check("o laco gravou passos", len(passos) >= 1, evid.keys())
    check("todo passo tem url", all(p.get("url") for p in passos), passos[:2])
    check("todo passo tem a TELA", all(p.get("tela") == "Dados do solicitante" for p in passos), passos[:2])
    check("todo passo tem hora UTC", all(str(p.get("ts", "")).startswith("20") and
                                         "+00:00" in str(p.get("ts", "")) for p in passos), passos[:2])
    check("os campos antigos continuam la",
          all({"a", "t", "v", "r"} <= set(p) for p in passos), passos[:2])
    check("a tela cabe em 120 chars", all(len(str(p.get("tela", ""))) <= 120 for p in passos))

    # -----------------------------------------------------------------
    print("\n-- (c2) a tela do PROTOCOLO e fotografada ANTES de navegar --")
    estado_p = {"url": "https://portal.exemplo/protocolo", "heading": "Solicitacao registrada",
                "inputs": [], "selects": [], "mdselects": [],
                "buttons": [{"text": "Agendar na loja"}], "radios": [],
                "pending_required": [], "text": TELA_DO_PROTOCOLO}
    page_p = PaginaDublê(estado=estado_p, texto=TELA_DO_PROTOCOLO, url=estado_p["url"])
    evp = {}
    r = asyncio.run(A.run_adaptive(page_p, "abrir atendimento", {}, evp, max_steps=3))
    check("a tela do protocolo devolve done", r.status == "done", r.status)
    check("o protocolo foi gravado", evp.get("protocolo") == "22842291", evp.get("protocolo"))
    check("existe prova com motivo 'protocolo'",
          any(p.get("motivo") == "protocolo" for p in (evp.get("prova") or [])), evp.get("prova"))
    check("a foto saiu NA TELA DO PROTOCOLO, nao na seguinte",
          bool(page_p.fotos) and page_p.fotos[0][0] == "https://portal.exemplo/protocolo",
          page_p.fotos)
    check("tentou a tela INTEIRA primeiro", bool(page_p.fotos) and page_p.fotos[0][1] is True,
          page_p.fotos)

    page_v = PaginaDublê(estado=estado_p, texto=TELA_DO_PROTOCOLO,
                         url=estado_p["url"], recusa_full_page=True)
    evv = {}
    asyncio.run(A.run_adaptive(page_v, "abrir atendimento", {}, evv, max_steps=3))
    prov_v = (evv.get("prova") or [{}])[0]
    check("portal que recusa full_page ainda deixa a prova do visivel",
          bool(prov_v.get("b64")) and prov_v.get("tela_inteira") is False, prov_v)

    # -----------------------------------------------------------------
    print("\n-- (d) o resumo e portugues, nao chave tecnica --")
    resumo_ok = W.resumo_do_desfecho("done", {
        "protocolo": "12345",
        "passo7": {"preferencia": "loja", "tem_loja": True,
                   "pedido_do_segurado": {"peca": "parabrisa"}}})
    resumo_h = W.resumo_do_desfecho("needs_human", {
        "passo": {"titulo": "Confirme a peca danificada"},
        "pergunta": "onde_realizar_o_servico?",
        "stage_80": "Confirme a peca danificada"})
    resumo_f = W.resumo_do_desfecho("failed", {"protocolo": "77", "error": "TimeoutError: x"})
    tecnicas = ("needs_human", "stage_80", "passo7", "adaptive_steps", "hitl", "captured",
                "JourneyResult", "evidence")
    for nome, txt in (("done", resumo_ok), ("needs_human", resumo_h), ("failed", resumo_f)):
        check(f"resumo {nome} nao tem sublinhado", "_" not in txt, txt)
        check(f"resumo {nome} nao vaza chave tecnica",
              not any(t in txt for t in tecnicas), txt)
        check(f"resumo {nome} nao e vazio", len(txt) > 20, txt)
    check("resumo done diz o numero e a peca", "12345" in resumo_ok and "parabrisa" in resumo_ok, resumo_ok)
    check("resumo done diz o proximo passo", "proximo passo" in resumo_ok, resumo_ok)
    check("resumo needs_human nomeia a tela", "Confirme a peca danificada" in resumo_h, resumo_h)
    check("resumo failed avisa que o pedido JA existe", "77" in resumo_f and "ja tinha sido aberto" in resumo_f,
          resumo_f)
    check("os tres resumos SAO diferentes entre si",
          len({resumo_ok, resumo_h, resumo_f}) == 3, (resumo_ok, resumo_h, resumo_f))
    page = PaginaDublê(texto=TELA_DO_PROTOCOLO)
    supa = _rodar_job(page, resultado=JourneyResult(status="done", captured={"protocolo": "22842291"},
                                                    message="ok"),
                      evidence={"protocolo": "22842291"})
    check("o resumo chega ao banco", "22842291" in str((supa.ultimo.get("evidence") or {}).get("resumo") or ""),
          (supa.ultimo.get("evidence") or {}).get("resumo"))

    # -----------------------------------------------------------------
    print("\n-- (e) cofre recusou: o base64 cai no fallback, a prova NAO se perde --")
    page = PaginaDublê(texto=TELA_DO_PROTOCOLO)
    supa = _rodar_job(page, resultado=JourneyResult(status="done", captured={}, message="ok"),
                      cofre_recusa=True)
    shots = supa.ultimo.get("screenshots") or []
    ev = supa.ultimo.get("evidence") or {}
    esperado = "data:image/jpeg;base64," + base64.b64encode(JPEG).decode("ascii")
    check("o cofre nao recebeu nada", supa.arquivos == {}, list(supa.arquivos))
    check("o base64 caiu em screenshots", esperado in shots, shots)
    check("a evidencia diz que a prova ficou nela mesma",
          "propria evidencia" in str(((ev.get("prova") or [{}])[0]).get("onde", "")), ev.get("prova"))
    check("mesmo assim o job fecha como done", supa.ultimo.get("status") == "done")

    # -----------------------------------------------------------------
    print("\n-- CONTROLE: fotografar e diagnostico; o acionamento nao morre por causa disso --")
    page = PaginaDublê(texto=TELA_DO_PROTOCOLO, recusa_tudo=True)
    supa = _rodar_job(page, resultado=JourneyResult(status="done", captured={"protocolo": "9"},
                                                    message="ok"),
                      evidence={"protocolo": "9"})
    ev = supa.ultimo.get("evidence") or {}
    check("pagina que recusa foto NAO derruba o job", supa.ultimo.get("status") == "done",
          supa.ultimo)
    check("sem foto, nenhuma prova e inventada", not (ev.get("prova") or []), ev.get("prova"))
    check("e o resumo continua saindo", bool(ev.get("resumo")), ev.get("resumo"))

    print(f"\n== {PASS} ok / {FAIL} fail ==")
    for n, d in FAILURES:
        print(f"  FALHOU: {n} ({d})")
    return FAIL == 0


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
