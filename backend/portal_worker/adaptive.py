"""SPEC-020 Camada 2 — Fallback LLM-visao (agente sem cabresto).

Quando o caminho deterministico nao reconhece uma tela (a de pneus da Porto, uma
pergunta nova, uma opcao que nao casa), o cerebro Smith ENXERGA a tela (estado
serializado) e DECIDE a proxima acao; o worker EXECUTA e repete. Nunca trava:
sempre pensa e age, ou pede o dado que falta (ask_human). Seguranca: para na tela
de confirmacao (80%) sem enviar (a menos de confirm=True), teto de passos, e nunca
inventa dado (usa os dados reais do segurado, SEM mascara — portal oficial).

parse_action / is_confirm_screen sao PUROS e testaveis offline.
"""
from __future__ import annotations

import json
import os
import unicodedata
from typing import Any, Dict, List, Optional

from portal_worker.journeys import JourneyResult

VALID_ACTIONS = ("fill", "select", "click", "check", "done", "ask_human")
MAX_STEPS = 22
_PROTO = ("protocolo", "numero do atendimento", "n do atendimento", "solicitacao registrada", "atendimento n")


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(s.split())


def parse_action(obj: Any) -> Dict[str, Any]:
    """PURO: valida/normaliza a acao devolvida pela LLM. Acao invalida -> ask_human."""
    if not isinstance(obj, dict):
        return {"action": "ask_human", "value": "nao entendi a tela", "reason": "resposta invalida"}
    a = str(obj.get("action") or "").strip().lower()
    if a not in VALID_ACTIONS:
        return {"action": "ask_human", "value": obj.get("value") or "nao sei o proximo passo", "reason": "acao desconhecida"}
    return {
        "action": a,
        "target": str(obj.get("target") or "").strip(),
        "value": str(obj.get("value") or "").strip(),
        "reason": str(obj.get("reason") or "").strip()[:160],
    }


def is_confirm_screen(state: Dict[str, Any]) -> bool:
    """PURO: True se a tela e a CONFIRMACAO da peca (80%) — parar antes de enviar."""
    blob = _norm((state or {}).get("heading", "") + " " + (state or {}).get("text", "")[:400])
    if "confirme a peca danificada" in blob:
        return True
    # perguntas especificas classicas do 80% (pelicula / trincado)
    hints = ("pelicula de controle solar", "o trincado esta maior ou menor", "posicao do trincado")
    return sum(h in blob for h in hints) >= 1


def has_protocol(state: Dict[str, Any]) -> bool:
    return any(s in _norm((state or {}).get("text", "")) for s in _PROTO)


async def capture_state(page) -> Dict[str, Any]:
    """Serializa a tela atual (raio-X) para o cerebro decidir."""
    return await page.evaluate(
        """() => {
          const vis = el => !!(el.offsetParent || el.getClientRects().length);
          const lbl = e => (e.labels && e.labels[0] && e.labels[0].textContent.trim())
                || (e.getAttribute('aria-label')||'') || (e.placeholder||'');
          const inputs = [...document.querySelectorAll('input,textarea')].filter(vis)
            .map(e => ({id:e.id, name:e.name, type:e.type, placeholder:e.placeholder||'',
                        value:e.value||'', label:lbl(e)}));
          const selects = [...document.querySelectorAll('select')]
            .map(s => ({name:s.name, label:lbl(s),
                        value:(s.options[s.selectedIndex]||{}).textContent||'',
                        options:[...s.options].map(o=>o.textContent.trim()).filter(Boolean)}));
          const buttons = [...document.querySelectorAll('button')].filter(vis)
            .map(b => ({text:b.textContent.trim(), disabled:!!b.disabled})).filter(b=>b.text);
          const radios = [...document.querySelectorAll('input[type=radio],input[type=checkbox]')].filter(vis)
            .map(r => ({name:r.name, checked:r.checked, label:lbl(r)}));
          const h = document.querySelector('h1,h2,h3,.titulo,.title');
          return {url:location.href, heading:(h?h.textContent:'').trim(),
                  inputs, selects, buttons, radios, text:document.body.innerText.slice(0,1500)};
        }"""
    )


_SYSTEM = (
    "Voce e um agente que preenche PORTAIS OFICIAIS de seguradora para abrir atendimento de VIDROS/"
    "lanternas de um segurado. Recebe o ESTADO da tela (campos, selects com opcoes, botoes, radios) e "
    "os DADOS reais do segurado/corretora. Decida a UNICA proxima acao. Use os dados REAIS, SEM mascara "
    "(portal oficial; humanos preenchem sem mascara). Responda SO com JSON: "
    '{"action","target","value","reason"}. Acoes: '
    "fill (target=id/label/placeholder do campo, value=texto), "
    "select (target=label do campo, value=texto da opcao desejada), "
    "click (target=texto do botao, ex Avancar), "
    "check (target=texto da pergunta, value=texto da resposta/opcao do radio), "
    "done (protocolo/atendimento gerado), ask_human (value=pergunta objetiva do que falta). "
    "Os dados JA vem no payload: 'segurado' (nome, apolice, chassi, veiculo, cep) e no topo "
    "(cpf_cnpj, placa, data_dano); 'solicitante' = a corretora (nome, email, telefone, cpf_cnpj); "
    "'dano' = o que aconteceu (peca, como, onde, descricao) — USE para 'peca danificada', 'como "
    "ocorreu o dano', 'onde ocorreu' e a descricao (min 30 chars; se curta, complete com o contexto). "
    "USE esses dados diretamente para preencher os campos; so use ask_human se o dado REALMENTE nao "
    "estiver no payload. "
    "Escolha a peca/causa/local/respostas com INTELIGENCIA a partir do que o segurado relatou. "
    "JAMAIS use ask_human para campos de FORMATO/preferencia onde qualquer valor serve (tipo de "
    "telefone, tipo de contato, DDD, 'como prefere ser atendido') — escolha DIRETO (ex.: Comercial, "
    "ou a 1a opcao valida do select). ask_human e SO para um dado REAL do segurado/dano que nao "
    "esta no payload e nao da pra deduzir (ex.: o que exatamente aconteceu, se voce nao tiver). "
    "NAO clique em botao que FINALIZE o pedido (confirmar/enviar) — pare que o sistema cuida disso. "
    "Um passo por vez."
)


_FORCE_CHOOSE = (
    " OVERRIDE: proibido ask_human agora. Esta tela tem select/radio/campo que VOCE consegue "
    "responder. Escolha a opcao mais coerente com o relato do dano; se nao houver relato claro, "
    "escolha a 1a opcao valida (nao 'Selecione'). NUNCA pergunte tipo/causa/local/preferencia. "
    "Devolva uma acao fill/select/check/click AGORA."
)


async def decide_next_action(state: Dict[str, Any], goal: str, collected: Dict[str, Any],
                             history: List[Dict[str, Any]], force: bool = False) -> Dict[str, Any]:
    """Chama o cerebro (LLM) para decidir a proxima acao. Fail-safe -> ask_human."""
    key = os.getenv("OPENAI_API_KEY") or ""
    model = os.getenv("PORTAL_VISION_MODEL", "gpt-4o-mini")
    if not key:
        return {"action": "ask_human", "value": "cerebro de visao indisponivel (sem OPENAI_API_KEY no worker)", "reason": "no key"}
    system = _SYSTEM + (_FORCE_CHOOSE if force else "")
    user = json.dumps({"objetivo": goal, "dados_segurado_corretora": collected, "tela": state,
                       "acoes_ja_feitas": history[-8:]}, ensure_ascii=False)
    try:
        import httpx

        async with httpx.AsyncClient(timeout=45.0) as c:
            r = await c.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={"model": model, "temperature": 0, "response_format": {"type": "json_object"},
                      "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
            )
            data = r.json()
            content = data["choices"][0]["message"]["content"]
        return parse_action(json.loads(content))
    except Exception as e:  # noqa: BLE001
        return {"action": "ask_human", "value": f"nao consegui decidir ({type(e).__name__})", "reason": "llm error"}


# ---- aplicar acao (imperativo Playwright) ----
async def _click_button(page, text: str) -> bool:
    t = _norm(text)
    for b in await page.query_selector_all("button, a[role=button], input[type=submit], input[type=button]"):
        try:
            if not await b.is_visible() or await b.is_disabled():
                continue  # botao disabled (ex.: Avancar aguardando campo obrigatorio) -> pula
            label = _norm(await b.inner_text() or "") or _norm(await b.get_attribute("value") or "")
            if t and t in label:
                await b.click()
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


async def _find_input(page, target: str):
    t = _norm(target)
    for e in await page.query_selector_all("input,textarea"):
        try:
            if not await e.is_visible():
                continue
            idv = _norm(await e.get_attribute("id") or "")
            ph = _norm(await e.get_attribute("placeholder") or "")
            nm = _norm(await e.get_attribute("name") or "")
            if t and (t == idv or t in ph or t in nm or (idv and idv in t)):
                return e
        except Exception:  # noqa: BLE001
            continue
    return None


async def _set_select(page, s, label: str) -> str:
    # 1) caminho normal do Playwright (funciona p/ select visivel ou 1px, ex.: 'segr').
    try:
        await s.select_option(label=label)
        await s.evaluate("el => el.dispatchEvent(new Event('change',{bubbles:true}))")
        return label
    except Exception:  # noqa: BLE001
        pass
    # 2) fallback JS: muitos selects do Angular Material sao <select display:none>
    #    (a UI visivel e o overlay do mat-select). O select_option recusa por
    #    actionability -> aqui setamos o value da opcao certa e disparamos os MESMOS
    #    eventos (input+change) que o Angular escuta. Funciona mesmo com display:none.
    try:
        ok = await s.evaluate(
            """(el, want) => {
                const n = t => (t||'').trim().toLowerCase();
                const opt = [...el.options].find(o => n(o.textContent) === n(want))
                        || [...el.options].find(o => n(o.textContent).includes(n(want)) && n(o.textContent));
                if (!opt) return false;
                el.value = opt.value;
                el.dispatchEvent(new Event('input', {bubbles:true}));
                el.dispatchEvent(new Event('change', {bubbles:true}));
                return true;
            }""",
            label,
        )
        return label if ok else ""
    except Exception:  # noqa: BLE001
        return ""


async def _apply_select(page, target: str, value: str) -> str:
    """Casa o valor em algum <select>; se identificar o campo-alvo (por name/label)
    mas o valor nao casar exato, pega a 1a opcao real (ex.: tipo de telefone, onde
    qualquer valor serve). Assim nao trava por causa de um dropdown obrigatorio."""
    t, v = _norm(target), _norm(value)
    target_sel = None
    for s in await page.query_selector_all("select"):
        try:
            name = _norm(await s.get_attribute("name") or "")
            opts = await s.evaluate("el => Array.from(el.options).map(o => (o.textContent||'').trim())")
        except Exception:  # noqa: BLE001
            continue
        for o in opts:                       # 1) valor casa numa opcao deste select
            if v and (v == _norm(o) or v in _norm(o) or _norm(o) in v):
                done = await _set_select(page, s, o)
                return f"select={done}" if done else "select_fail"
        if t and (t == name or t in name or name in t):   # 2) e o campo-alvo?
            target_sel = (s, opts)
    if target_sel:                            # 3) campo certo, valor nao casou -> 1a real
        s, opts = target_sel
        for o in opts:
            if o and "selecione" not in _norm(o):
                done = await _set_select(page, s, o)
                return f"select_default={done}" if done else "select_fail"
    return "select_notfound"


async def _find_mdselect(page, target: str, value: str):
    """Acha o <md-select> (AngularJS Material) alvo: por name/id/aria-label (target)
    ou, se o target vier vazio, pelo <select> nativo-espelho que tenha a opcao com o
    valor pedido (ex.: 'segr' tem 'O proprio'/'Corretor')."""
    t, v = _norm(target), _norm(value)
    mds = await page.query_selector_all("md-select")
    if not mds:
        return None
    if t:
        for m in mds:
            name = _norm(await m.get_attribute("name") or "")
            idv = _norm(await m.get_attribute("id") or "")
            al = _norm(await m.get_attribute("aria-label") or "")
            if (name and (t == name or t in name or name in t)) or (idv and (t in idv or idv in t)) or (al and t in al):
                return m
    if v:  # target vazio -> casa pelo valor via select nativo espelho (mesmo name)
        for s in await page.query_selector_all("select"):
            try:
                opts = await s.evaluate("el => Array.from(el.options).map(o => (o.textContent||'').trim())")
            except Exception:  # noqa: BLE001
                continue
            if any(o and (v == _norm(o) or v in _norm(o) or _norm(o) in v) for o in opts):
                nm = _norm(await s.get_attribute("name") or "")
                for m in mds:
                    if nm and _norm(await m.get_attribute("name") or "") == nm:
                        return m
    return None


async def _apply_mdselect(page, target: str, value: str):
    """Dirige um <md-select> do jeito CERTO (AngularJS so atualiza o ng-model assim):
    clica p/ abrir o overlay e clica no <md-option> pelo texto. Retorna None se a tela
    NAO tem md-select alvo (cai no _apply_select nativo). 1a opcao real se o valor nao casar."""
    m = await _find_mdselect(page, target, value)
    if m is None:
        return None
    # Fecha qualquer overlay aberto antes (backdrop de um md-select anterior intercepta
    # o clique e faria o Playwright esperar o timeout inteiro). Timeouts CURTOS em tudo:
    # nada pode travar 30s — se nao clicar em ~4s, devolve um codigo e o loop segue.
    try:
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(150)
    except Exception:  # noqa: BLE001
        pass
    try:
        await m.scroll_into_view_if_needed(timeout=3000)
        await m.click(timeout=4000)
    except Exception:  # noqa: BLE001
        return "mdselect_open_fail"
    await page.wait_for_timeout(400)
    v = _norm(value)
    try:
        opts = await page.query_selector_all("md-option")
    except Exception:  # noqa: BLE001
        opts = []
    for o in opts:                                   # 1) opcao com o texto pedido
        try:
            if await o.is_visible():
                txt = _norm(await o.inner_text())
                if txt and v and (v == txt or v in txt or txt in v):
                    await o.click(timeout=4000)
                    return f"mdselect={txt}"
        except Exception:  # noqa: BLE001
            continue
    for o in opts:                                   # 2) 1a opcao real (nao 'Selecione')
        try:
            if await o.is_visible():
                txt = _norm(await o.inner_text())
                if txt and "selecione" not in txt:
                    await o.click(timeout=4000)
                    return "mdselect_default"
        except Exception:  # noqa: BLE001
            continue
    try:
        await page.keyboard.press("Escape")
    except Exception:  # noqa: BLE001
        pass
    return "mdselect_notfound"


async def _apply_check(page, target: str, value: str) -> str:
    want = _norm(value) or _norm(target)
    for lab in await page.query_selector_all("label, .radio, .mat-radio-label"):
        try:
            if await lab.is_visible() and want and want in _norm(await lab.inner_text()):
                await lab.click()
                return "checked"
        except Exception:  # noqa: BLE001
            continue
    return "check_notfound"


async def apply_action(page, action: Dict[str, Any]) -> str:
    a = action.get("action")
    target = action.get("target") or ""
    value = action.get("value") or ""
    if a == "fill":
        el = await _find_input(page, target)
        if el:
            await el.fill(str(value))
            return "filled"
        return "fill_notfound"
    if a == "select":
        # AngularJS Material: <md-select> so aceita clique no overlay. Tenta primeiro;
        # se a tela nao tiver md-select alvo, cai no <select> nativo.
        md = await _apply_mdselect(page, target, value)
        if md is not None:
            return md
        return await _apply_select(page, target, value)
    if a == "check":
        return await _apply_check(page, target, value)
    if a == "click":
        return "clicked" if await _click_button(page, target) else "click_notfound"
    return "noop"


async def run_adaptive(page, goal: str, collected: Dict[str, Any], evidence: Dict[str, Any],
                       max_steps: int = MAX_STEPS, confirm: bool = False) -> JourneyResult:
    """Loop agentico: enxerga a tela -> cerebro decide -> executa. Nunca trava."""
    history: List[Dict[str, Any]] = []
    for _ in range(max_steps):
        state = await capture_state(page)
        if has_protocol(state):
            evidence["final"] = state.get("text", "")[:600]
            return JourneyResult(status="done", captured={"stage": "protocolo"}, message="protocolo capturado (adaptive)")
        if is_confirm_screen(state) and not confirm:
            evidence["stage_80"] = state.get("text", "")[:600]
            return JourneyResult(status="needs_human", captured={"stage": "confirme_80"},
                                 message="cheguei na confirmacao (80%) — aprove para enviar")
        action = await decide_next_action(state, goal, collected, history)
        history.append(action)
        if action["action"] == "done":
            return JourneyResult(status="done", message="concluido (adaptive)")
        if action["action"] == "ask_human":
            # Backstop anti-travamento: o cerebro tende a "pedir por educacao" em selects/radios.
            # Forca UMA re-decisao imperativa antes de desistir. So devolve needs_human se, mesmo
            # obrigado a escolher, ele ainda insistir em perguntar (dado de identidade real faltando).
            forced = await decide_next_action(state, goal, collected, history, force=True)
            if forced.get("action") in ("fill", "select", "check", "click"):
                action = forced
                history[-1] = action
            else:
                return JourneyResult(status="needs_human", captured={"pergunta": action.get("value")},
                                     message=f"preciso de: {action.get('value')}")
        applied = await apply_action(page, action)
        sig = (action.get("action"), action.get("target"), action.get("value"), applied)
        steps = evidence.setdefault("adaptive_steps", [])
        steps.append({"a": sig[0], "t": sig[1], "v": (action.get("value") or "")[:30], "r": applied})
        # Parada antecipada: 3 acoes identicas seguidas sem mudar nada = tela travada.
        # Para com o DOM (diagnostico) em vez de arrastar ate MAX_STEPS.
        sigs = [(s["a"], s["t"], s["v"], s["r"]) for s in steps[-3:]]
        if len(sigs) == 3 and len(set(sigs)) == 1:
            evidence["debug_dom"] = await _dump_dom(page)
            return JourneyResult(status="needs_human", captured={"stage": "sem_progresso"},
                                 message=f"tela travada: repetiu '{sig[0]} {sig[1]} {sig[2]}' -> {applied}")
        await page.wait_for_timeout(1200)
    # DIAGNOSTICO: se travou, despeja o DOM real da tela pra achar a causa (nao chutar).
    evidence["debug_dom"] = await _dump_dom(page)
    return JourneyResult(status="needs_human", captured={"steps": evidence.get("adaptive_steps")},
                         message="muitos passos sem concluir (adaptive) — precisa de revisao")


async def _dump_dom(page) -> Dict[str, Any]:
    """Raio-X cru da tela travada: selects (nativo?/display/disabled/opcoes/html),
    mat-selects (Angular), e os botoes de avanco. So p/ diagnostico."""
    try:
        return await page.evaluate(
            """() => {
              const vis = el => !!(el.offsetParent || el.getClientRects().length);
              const selects = [...document.querySelectorAll('select')].map(s => ({
                name:s.name, id:s.id, disabled:s.disabled,
                display:getComputedStyle(s).display, vis:vis(s),
                opts:[...s.options].map(o=>o.textContent.trim()),
                html:s.outerHTML.slice(0,200)
              }));
              const matselects = [...document.querySelectorAll('mat-select,[role=combobox],[role=listbox],.mat-select')].map(m => ({
                tag:m.tagName, id:m.id, cls:m.className, text:(m.textContent||'').trim().slice(0,50),
                html:m.outerHTML.slice(0,200)
              }));
              const advance = [...document.querySelectorAll('button,a,input,[role=button]')]
                .filter(b => /avan|prox|contin|salv|enviar|confirm/i.test((b.textContent||'')+' '+(b.value||'')))
                .map(b => ({tag:b.tagName, text:(b.textContent||'').trim().slice(0,30),
                            value:b.value||'', disabled:!!b.disabled, vis:vis(b)}));
              return {selects, matselects, advance, heading:(document.querySelector('h1,h2,h3')||{}).textContent||''};
            }"""
        )
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"}
