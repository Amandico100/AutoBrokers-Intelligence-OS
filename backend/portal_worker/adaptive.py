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
from portal_worker.journeys.vidros_lanternas import explicar_match, explicar_especifico
# Duas declaracoes do mesmo modulo de proposito: a linha acima e o placar de
# PECA/ATRIBUTO, e ela e literalmente o que dois testes leem para provar que
# nao existe um segundo placar aqui dentro (test_portal_de_reparos [R6],
# test_o_80_por_cento_sabe_o_que_pergunta [7.4i]). Emenda-la numa lista so
# quebraria essas duas guardas sem que a verdade que elas guardam mudasse.
# Abaixo, pelo MESMO motivo, o vocabulario do PROTOCOLO e da escolha do passo 7:
# uma lista de rotulos copiada em dois arquivos sao duas verdades que divergem
# no dia em que so uma for corrigida — e foi exatamente o que aconteceu com o
# `_PROTO` que vivia aqui.
from portal_worker.journeys.vidros_lanternas import (
    botao_de_domicilio,
    botao_de_loja,
    extrair_protocolo,
    preferencia_de_atendimento,
    tem_protocolo,
)

VALID_ACTIONS = ("fill", "select", "click", "check", "done", "ask_human")
# O modelo que ja rodou em producao. Serve de rede: se o padrao novo nao existir
# na conta, o acionamento cai aqui em vez de morrer.
_MODELO_DE_RESERVA = "gpt-4o-mini"
MAX_STEPS = 22
LAST_MDSELECT_DEBUG = None  # ultimo overlay md-option nao-clicavel (diagnostico)


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
    blob = _norm((state or {}).get("heading", "") + " " + (state or {}).get("text", "")[:600])
    # Gatilhos ESPECIFICOS do 80% "Confirme a peca danificada". NAO usar o banner
    # permanente "SELECAO de 1 ITEM" (aparece em TODAS as telas -> falso positivo).
    strong = ("confirme a peca danificada", "confirme a peca a ser", "confirme a peca danif")
    if any(s in blob for s in strong):
        return True
    # perguntas especificas classicas do 80% (pelicula / trincado) — so existem la
    hints = ("pelicula de controle solar", "o trincado esta maior ou menor", "posicao do trincado")
    return sum(h in blob for h in hints) >= 1


def has_protocol(state: Dict[str, Any]) -> bool:
    """PURO: esta tela ja mostra o pedido aberto? O vocabulario e UM SO e mora
    em `vidros_lanternas` — antes havia duas listas identicas por copia, em dois
    arquivos, e a que rodava aqui nao reconhecia o formato real (📊 ver a secao
    DO PROTOCOLO la; `Nº do atendimento: 22842291` devolvia False)."""
    return tem_protocolo((state or {}).get("text", ""))


def registrar_protocolo(evidence: Dict[str, Any], page_text: str) -> str:
    """Grava o protocolo na evidencia ASSIM QUE ELE APARECE. Devolve o numero.

    🔴 Por que nao pode esperar o fim: 📊 o `Nº do atendimento` nasce no passo 7,
    no TOPO da tela, ANTES da escolha da loja (mapa §7). Entre esse instante e o
    fim do fluxo cabem um teto de passos estourado, uma tela travada e uma
    excecao do Playwright. Em qualquer um desses o pedido JA EXISTE na
    seguradora — e um segurado com atendimento aberto que ninguem sabe rastrear
    e o pior resultado possivel deste sistema: pior que falhar, porque falhar
    pelo menos nao promete nada.

    Por que gravar em `evidence` e nao no retorno: `evidence` e o MESMO dicionario
    que o worker ja escreve no job em TODOS os desfechos — inclusive no `except`
    que grava `status=failed`. Um numero que so viajasse no JourneyResult morreria
    junto com a excecao que o impediu de chegar.

    IDEMPOTENTE: o primeiro numero visto manda. Reescrever a cada tela deixaria
    o campo a mercê do ultimo numero que passasse pela pagina.
    """
    if not isinstance(evidence, dict):
        return ""
    if str(evidence.get("protocolo") or "").strip():
        return str(evidence["protocolo"])
    numero = extrair_protocolo(page_text)
    if numero:
        evidence["protocolo"] = numero
        evidence["protocolo_visto_em"] = (page_text or "")[:300]
    return numero


def aviso_de_pedido_aberto(evidence: Dict[str, Any]) -> str:
    """PURO: o prefixo que toda PARADA depois do passo 7 precisa carregar. ""
    quando nao ha protocolo — nao se avisa sobre um pedido que nao existe.

    Sem esta frase, uma parada por "tela travada" ocorrida DEPOIS do passo 7
    parece uma tentativa que nao deu em nada, e a reacao natural de quem le e
    tentar de novo — que e exatamente o que cria o segundo atendimento.
    """
    numero = str((evidence or {}).get("protocolo") or "").strip()
    if not numero:
        return ""
    return (f"ATENCAO: o atendimento JA FOI ABERTO na seguradora (N {numero}) — "
            "NAO reexecute, repetir cria um segundo pedido. ")


async def registrar_protocolo_da_pagina(page, evidence: Dict[str, Any]) -> str:
    """Le SO o texto da tela e grava o protocolo, se houver. Chamada depois de
    cada clique: e o clique que cria o pedido, e o intervalo entre ele e a
    proxima leitura completa da tela e justamente onde o numero se perderia.
    Nunca levanta excecao — um erro aqui nao pode derrubar o acionamento."""
    try:
        texto = await page.evaluate("() => (document.body.innerText||'').slice(0,2000)")
    except Exception:  # noqa: BLE001
        return ""
    return registrar_protocolo(evidence, str(texto or ""))


async def capture_state(page) -> Dict[str, Any]:
    """Serializa a tela atual (raio-X) para o cerebro decidir. Inclui md-select
    (AngularJS Material) com o LABEL, valor atual e se esta VAZIO+OBRIGATORIO
    (ng-invalid-required) — assim o cerebro ENXERGA exatamente qual campo trava o
    Avancar e mira nele (era o buraco: so capturava <select> nativo, e o md-select
    de 'tipo de telefone' ficava invisivel pro cerebro)."""
    return await page.evaluate(
        """() => {
          const vis = el => !!(el.offsetParent || el.getClientRects().length);
          const clean = t => (t||'').replace(/\\s+/g,' ').trim();
          const lbl = e => clean((e.labels && e.labels[0] && e.labels[0].textContent)
                || e.getAttribute('aria-label') || e.placeholder || '');
          const mdLabel = m => { const c = m.closest('md-input-container,.md-input-container,md-autocomplete');
                let l = c && c.querySelector('label'); if (l) return clean(l.textContent);
                return clean(m.getAttribute('aria-label') || m.getAttribute('name') || m.id); };
          const inputs = [...document.querySelectorAll('input,textarea')].filter(vis)
            .map(e => ({id:e.id, name:e.name, type:e.type, placeholder:e.placeholder||'',
                        value:e.value||'', label:lbl(e),
                        required: !!e.required || /ng-required/.test(e.className),
                        empty_required: /ng-invalid-required/.test(e.className)}));
          const selects = [...document.querySelectorAll('select')].filter(vis)
            .map(s => ({name:s.name, label:lbl(s),
                        value:(s.options[s.selectedIndex]||{}).textContent||'',
                        options:[...s.options].map(o=>o.textContent.trim()).filter(Boolean)}));
          // md-select (Angular Material): o widget REAL das telas de vidros.
          const mdselects = [...document.querySelectorAll('md-select')].filter(vis)
            .map(m => ({id:m.id, name:m.getAttribute('name')||'', label:mdLabel(m),
                        value:clean(m.textContent),
                        empty_required: /ng-invalid-required|ng-empty/.test(m.className) && /ng-required|ng-invalid/.test(m.className)}));
          const buttons = [...document.querySelectorAll('button')].filter(vis)
            .map(b => ({text:clean(b.textContent), disabled:!!b.disabled})).filter(b=>b.text);
          const radios = [...document.querySelectorAll('input[type=radio],input[type=checkbox]')].filter(vis)
            .map(r => ({name:r.name, checked:r.checked, label:lbl(r)}));
          // Resumo do que BLOQUEIA o Avancar: campos obrigatorios ainda vazios.
          const pending_required = [
            ...inputs.filter(e => e.empty_required).map(e => ({tipo:'input', label:e.label||e.id||e.name})),
            ...mdselects.filter(m => m.empty_required).map(m => ({tipo:'select', label:m.label||m.name||m.id})),
          ];
          const h = document.querySelector('h1,h2,h3,.titulo,.title');
          return {url:location.href, heading:clean(h?h.textContent:''),
                  inputs, selects, mdselects, buttons, radios, pending_required,
                  text:document.body.innerText.slice(0,1500)};
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
    "Em 'select', o value deve ser um texto de OPCAO REAL: se a tela mostrar as options do select, "
    "COPIE exatamente a opcao mais coerente com o relato (nao parafraseie). Se uma acao sua voltar "
    "com resultado 'mdselect_options=...' ou 'select_options=...' em acoes_ja_feitas, essas SAO as "
    "opcoes reais daquele campo: refaca o select escolhendo UMA delas (texto exato). "
    "Nas perguntas ESPECIFICAS dos 80% (lado do item, porta dianteira/traseira, pelicula/insulfilm, "
    "posicao do trincado, maior/menor que 10 cm, versao do veiculo) responda com o que o SEGURADO "
    "disse ou com o que a apolice ja diz. NUNCA escolha 'Nao sabe' para destravar a tela: isso "
    "faz a seguradora perder qual vidro pedir. 'Nao sabe' so quando o segurado nao souber mesmo. "
    "JAMAIS use ask_human para campos de FORMATO/preferencia onde qualquer valor serve (tipo de "
    "telefone, tipo de contato, DDD, 'como prefere ser atendido') — escolha DIRETO (ex.: Comercial, "
    "ou a 1a opcao valida do select). ask_human e SO para um dado REAL do segurado/dano que nao "
    "esta no payload e nao da pra deduzir (ex.: o que exatamente aconteceu, se voce nao tiver). "
    "NAO clique em botao que FINALIZE o pedido (confirmar/enviar) — pare que o sistema cuida disso. "
    "Se a tela ja mostrar um numero de atendimento/protocolo, o pedido JA FOI ABERTO: responda "
    "action=done imediatamente. NAO clique em 'Agendar na loja', 'Agendar a domicilio', "
    "'Consultar distancia' nem 'Cancelar atendimento' — QUAL loja (ou se o tecnico vai ate a casa "
    "dele) e escolha do SEGURADO, e o portal nao deixa corrigir: seria preciso abrir outro "
    "atendimento. Escolher por ele nao e agilidade, e sorteio. "
    "Se o botao Avancar/Continuar aparecer DESABILITADO (disabled) ou o clique nao mudar a tela, "
    "e porque um campo OBRIGATORIO ainda esta VAZIO: o payload traz 'pending_required' = a LISTA "
    "EXATA dos campos que faltam (com o label). Preencha CADA UM deles antes de Avancar — um por "
    "vez, comecando pelo primeiro de pending_required. Se uma acao sua voltar "
    "'click_bloqueado: ... Falta preencher: X, Y' em acoes_ja_feitas, o botao EXISTE e esta "
    "BLOQUEADO: NAO reclique — preencha X e depois Y. 'click_notfound' e outra coisa: o botao nao "
    "esta na tela (procure o rotulo certo). Para um campo 'select', use action select com "
    "target = o label/name do campo (ex.: 'tipo de telefone') e value = a opcao (ex.: 'Comercial'). "
    "NUNCA repita a mesma acao que ja aplicou (ex.: reselecionar um campo que ja tem valor) — olhe "
    "'pending_required' e mire no que AINDA falta. 'mdselects' lista os dropdowns Material com label/"
    "valor atual/empty_required. Preencha os DROPDOWNS primeiro e o TEXTO LIVRE (descricao) por ULTIMO: mudar "
    "um dropdown as vezes limpa a descricao. Em campo de ESTADO/UF com autocomplete, digite "
    "a SIGLA de 2 letras (ex.: 'SC', 'SP', 'RJ') — o nome por extenso ('Santa Catarina') nao "
    "retorna resultado. Se um autocomplete disser 'nenhum resultado', voce usou o termo errado: "
    "tente a sigla/forma curta. Um passo por vez."
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
    # 📊 O padrao era `gpt-4o-mini` — um modelo pequeno conduzindo uma tarefa
    # agentica de 22 passos com 1.500 caracteres de instrucao. A autopsia dos 39
    # acionamentos mostra os tres sintomas classicos de instrucao nao seguida:
    # perguntou o que estava no payload (4x), repetiu acao que ja tinha dado
    # certo (7x) e escreveu "Santa Catarina" onde o prompt manda a SIGLA.
    #
    # Continua trocavel por env — e o fallback abaixo garante que um nome de
    # modelo invalido nunca derrube o acionamento.
    model = os.getenv("PORTAL_VISION_MODEL", "gpt-4o")
    if not key:
        return {"action": "ask_human", "value": "cerebro de visao indisponivel (sem OPENAI_API_KEY no worker)", "reason": "no key"}
    system = _SYSTEM + (_FORCE_CHOOSE if force else "")
    user = json.dumps({"objetivo": goal, "dados_segurado_corretora": collected, "tela": state,
                       "acoes_ja_feitas": history[-8:]}, ensure_ascii=False)
    try:
        import httpx

        mensagens = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        async with httpx.AsyncClient(timeout=45.0) as c:
            async def _pedir(m: str):
                return await c.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}"},
                    json={"model": m, "temperature": 0, "response_format": {"type": "json_object"},
                          "messages": mensagens},
                )

            r = await _pedir(model)
            # Um nome de modelo que a conta nao tem nao pode custar o
            # acionamento inteiro. Cai UMA vez no modelo antigo, que
            # comprovadamente responde — pior decisao e melhor que nenhuma.
            if r.status_code >= 400 and model != _MODELO_DE_RESERVA:
                r = await _pedir(_MODELO_DE_RESERVA)
            data = r.json()
            content = data["choices"][0]["message"]["content"]
        return parse_action(json.loads(content))
    except Exception as e:  # noqa: BLE001
        return {"action": "ask_human", "value": f"nao consegui decidir ({type(e).__name__})", "reason": "llm error"}


# ---- aplicar acao (imperativo Playwright) ----
async def _click_button(page, text: str) -> str:
    """'clicked' | 'disabled' (existe mas esta bloqueado) | 'notfound'.

    A diferenca importa: 📊 03/08/2026 — 31 dos 34 acionamentos com passos
    gravados bateram em 'click_notfound' no Avancar, e o cerebro recebia a mesma
    palavra tanto para 'o botao sumiu' quanto para 'o botao existe mas falta
    preencher um campo'. Sem saber a diferenca, ele reclicava ate a tela ser
    declarada travada. Botao DESABILITADO nao e botao ausente: e campo faltando."""
    t = _norm(text)
    achou_desabilitado = False
    for b in await page.query_selector_all("button, a[role=button], input[type=submit], input[type=button]"):
        try:
            if not await b.is_visible():
                continue
            label = _norm(await b.inner_text() or "") or _norm(await b.get_attribute("value") or "")
            if not (t and t in label):
                continue
            if await b.is_disabled():
                achou_desabilitado = True
                continue
            await b.click()
            return "clicked"
        except Exception:  # noqa: BLE001
            continue
    return "disabled" if achou_desabilitado else "notfound"


async def _campos_que_faltam(page) -> List[str]:
    """Os obrigatorios ainda vazios — o motivo real de um Avancar desabilitado.
    Devolve os rotulos para o cerebro mirar no campo certo em vez de reclicar."""
    try:
        return await page.evaluate(
            """() => {
              const clean = t => (t||'').replace(/\\s+/g,' ').trim();
              const vis = el => !!(el.offsetParent || el.getClientRects().length);
              const rot = e => { const c = e.closest('md-input-container,.md-input-container,md-autocomplete');
                    const l = c && c.querySelector('label'); if (l) return clean(l.textContent);
                    return clean((e.labels && e.labels[0] && e.labels[0].textContent)
                       || e.getAttribute('aria-label') || e.getAttribute('placeholder')
                       || e.getAttribute('name') || e.id); };
              return [...document.querySelectorAll(
                  'input.ng-invalid-required,textarea.ng-invalid-required,md-select.ng-invalid-required,'
                + 'md-select.ng-invalid.ng-required,md-autocomplete.ng-invalid-required,'
                + 'md-datepicker.ng-invalid-required,md-checkbox.ng-invalid-required')]
                .filter(vis).map(rot).filter(Boolean).slice(0, 8);
            }"""
        ) or []
    except Exception:  # noqa: BLE001
        return []


async def _find_input(page, target: str):
    """Acha o input/textarea alvo. O cerebro as vezes mira pelo ID (fl-input-65) e as
    vezes pelo LABEL que ve na tela ('Selecione o estado...') — casa pelos DOIS: id,
    name, placeholder, aria-label e o <label> associado (inclui md-autocomplete/
    md-input-container). els e metas vem na MESMA ordem (document order)."""
    t = _norm(target)
    if not t:
        return None
    els = await page.query_selector_all("input,textarea")
    try:
        metas = await page.evaluate(
            """() => [...document.querySelectorAll('input,textarea')].map(e => {
                 let lab = (e.labels && e.labels[0] && e.labels[0].textContent) || e.getAttribute('aria-label') || '';
                 if (!lab) { const c = e.closest('md-autocomplete,md-input-container');
                             if (c) { const l = c.querySelector('label'); if (l) lab = l.textContent; } }
                 return {id:e.id||'', name:e.name||'', ph:e.placeholder||'',
                         lab:(lab||'').trim(), vis:!!(e.offsetParent || e.getClientRects().length)};
               })"""
        )
    except Exception:  # noqa: BLE001
        metas = []
    for i, e in enumerate(els):
        m = metas[i] if i < len(metas) else {}
        if metas and not m.get("vis"):
            continue
        if not metas:
            try:
                if not await e.is_visible():
                    continue
            except Exception:  # noqa: BLE001
                continue
        idv, nm = _norm(m.get("id", "")), _norm(m.get("name", ""))
        ph, lab = _norm(m.get("ph", "")), _norm(m.get("lab", ""))
        if (t == idv or (idv and idv in t) or (ph and t in ph) or (nm and t in nm)
                or (lab and (t in lab or lab in t))):
            return e
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
    qualquer valor serve). Assim nao trava por causa de um dropdown obrigatorio.

    🔴 A 1a opcao real SO vale em campo tolerante. Este e o mesmo sorteio que o
    _apply_mdselect ja evitava — pela porta do <select> nativo, onde ninguem
    tinha posto a checagem. Em campo critico devolve as opcoes ao cerebro."""
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
    if target_sel:                            # 3) campo certo, valor nao casou
        s, opts = target_sel
        reais = [o for o in opts if o and "selecione" not in _norm(o)]
        if _is_critical_select(target):        # critico: PARAR e devolver a lista
            return "select_options=" + " | ".join(o[:60] for o in reais[:20])
        for o in reais:                        # tolerante: 1a real serve
            done = await _set_select(page, s, o)
            return f"select_default={done}" if done else "select_fail"
    return "select_notfound"


async def _find_mdselect(page, target: str, value: str):
    """Acha o <md-select> (AngularJS Material) alvo: por name/id/aria-label OU pelo
    <label> do container (o cerebro as vezes mira pelo LABEL que ve, ex.: 'tipo de
    telefone', cujo name real e 'TipoTelefoneSolicitante0'); ou, se o target vier
    vazio, pelo <select> nativo-espelho que tenha a opcao com o valor pedido."""
    t, v = _norm(target), _norm(value)
    mds = await page.query_selector_all("md-select")
    if not mds:
        return None
    if t:
        # label do container md-input (mesma tecnica do _find_input); ordem = document order
        try:
            labels = await page.evaluate(
                """() => [...document.querySelectorAll('md-select')].map(m => {
                     const c = m.closest('md-input-container,.md-input-container,md-autocomplete');
                     const l = c && c.querySelector('label');
                     return (l ? l.textContent : '').replace(/\\s+/g,' ').trim();
                   })"""
            )
        except Exception:  # noqa: BLE001
            labels = []
        for i, m in enumerate(mds):
            name = _norm(await m.get_attribute("name") or "")
            idv = _norm(await m.get_attribute("id") or "")
            al = _norm(await m.get_attribute("aria-label") or "")
            lab = _norm(labels[i]) if i < len(labels) else ""
            if ((name and (t == name or t in name or name in t)) or (idv and (t in idv or idv in t))
                    or (al and t in al) or (lab and (t in lab or lab in t))):
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


# Campos de FORMATO/preferencia: o portal so quer que estejam preenchidos, e
# qualquer opcao valida serve. Sao verificados ANTES da lista de criticos — se
# virarem criticos, o robo trava num campo onde parar nao protege ninguem.
_TOLERANTES = ("tipo de telefone", "tipotelefone", "tipo do telefone",
               "tipo de contato", "tipocontato", "ddd", "como prefere",
               "prefere ser atendido", "meio de contato", "forma de contato")

# 🔴 Campos onde a opcao ERRADA vira SERVICO errado — e o portal nao deixa
# corrigir: seria preciso abrir OUTRO acionamento (mapa do portal §3).
#
# 📊 medido em 04/08/2026 com a lista antiga ("item","peca","danific","ocorreu",
#    "causa","dano"), em backend/tests/test_o_80_por_cento_sabe_o_que_pergunta.py:
#      _is_critical_select("Escolha a loja onde deseja realizar o servico") -> False
#      _is_critical_select("O trincado esta maior ou menor que 10 cm?")     -> False
#      _is_critical_select("Poderia informar a posicao do trincado?")       -> False
#    Campo nao-critico sem match cai na 1a opcao (escolha = reais[0][0]). Na
#    tela do passo 7 isso e SORTEAR A OFICINA; na do trincado, 'menor que 10 cm'
#    virava "Maior (troca do vidro)" — trocar um parabrisa que tinha reparo.
#
# Falso positivo aqui e barato (o robo para e pergunta); falso negativo e caro
# (o robo escolhe errado e o pedido abre). Por isso a lista peca por incluir.
_CRITICOS = (
    "item", "peca", "danific", "ocorreu", "causa", "dano",        # ja existiam
    "loja", "oficina", "unidade", "concessionaria", "prestador",  # ONDE consertar
    "domicili", "agendar", "agendamento", "horario",              # COMO e QUANDO
    "lado", "direita", "esquerda", "dianteira", "traseira",       # QUAL vidro
    "pelicula", "insulfilm", "controle solar",
    "trincad", "trinca", "posicao", "tamanho",
    "versao", "comfortline",
    "estado", "cidade", "cep", "municipio", "bairro",             # ONDE o segurado esta
)


def _is_critical_select(target: str) -> bool:
    """PURO: campos onde escolher a opcao ERRADA = acionamento ERRADO. Nesses
    NUNCA cair na 1a opcao as cegas — devolver as opcoes reais ao cerebro.
    Campos de FORMATO continuam tolerantes (qualquer opcao valida serve), e e
    por isso que a checagem deles vem primeiro: um campo pode conter uma palavra
    critica por acaso, mas se ele e de formato, parar nele nao protege ninguem."""
    t = _norm(target)
    if any(k in t for k in _TOLERANTES):
        return False
    return any(k in t for k in _CRITICOS)


def score_option_tokens(want: str, option: str) -> int:
    """PURO: similaridade por tokens (sem stopwords). 'vidro da porta' vs
    'VIDRO DE PORTA' = 2; vs 'VIDRO PARABRISA - CARGA' = 1. Match exato = 999."""
    stop = {"de", "da", "do", "das", "dos", "e", "o", "a", "os", "as", "um", "uma", "no", "na", "em", "para", "por", "com"}
    nw, no = _norm(want), _norm(option)
    if nw and nw == no:
        return 999
    tw = [t for t in nw.replace("-", " ").split() if t and t not in stop]
    to = [t for t in no.replace("-", " ").split() if t and t not in stop]
    return sum(1 for t in to if t in tw)


async def _apply_mdselect(page, target: str, value: str):
    """Dirige um <md-select> do jeito CERTO (AngularJS so atualiza o ng-model assim):
    clica p/ abrir o overlay e clica no <md-option> pelo texto. Retorna None se a tela
    NAO tem md-select alvo (cai no _apply_select nativo).

    QUEM DECIDE e o match_option (puro, testavel offline, um so no sistema). Antes
    existia um segundo placar escrito em JS aqui dentro, e era ELE que rodava em
    producao: bastava UM token em comum para clicar. 📊 03/08/2026 — em 34
    acionamentos com passos gravados, esse placar escolheu campo critico 17 vezes e
    NUNCA parou para perguntar; 6 escolhas estavam erradas ('vidro da porta' ->
    'VIDRO PARABRISA - CARGA', 3x; relato de furto -> 'CHOQUE TERMICO', 3x).
    Em campo CRITICO sem match confiante, devolve as opcoes reais ao cerebro."""
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
    # Abre o overlay com RETRY: logo apos uma troca de tela (ex.: Avancar) o md-select
    # pode ainda estar animando/nao-pronto -> 1a tentativa falha. Tenta 2x com espera.
    opened = False
    for _attempt in range(2):
        try:
            await m.scroll_into_view_if_needed(timeout=2500)
            await m.click(timeout=3500)
            opened = True
            break
        except Exception:  # noqa: BLE001
            await page.wait_for_timeout(600)
    if not opened:
        return "mdselect_open_fail"
    await page.wait_for_timeout(650)
    try:
        # 1) LER as opcoes reais do overlay. So leitura — a decisao e do Python.
        # Escopo nas md-option VISIVEIS (as do select ja fechado ficam no DOM com
        # offsetParent nulo, e clicar nelas marcaria o campo errado).
        visiveis = []
        for o in await page.query_selector_all("md-option"):
            try:
                if await o.is_visible():
                    txt = " ".join((await o.inner_text() or "").split())
                    if txt:
                        visiveis.append((txt, o))
            except Exception:  # noqa: BLE001
                continue
        reais = [(t, o) for t, o in visiveis if "selecione" not in _norm(t)]
        if reais:
            # 2) DECIDIR com as funcoes PURAS — as mesmas que os testes exercitam
            # offline. Sao DUAS porque o portal faz duas perguntas diferentes: a
            # do passo 4 e sobre a PECA ("VIDRO DE PORTA"); a do passo 6 (80%) e
            # sobre um ATRIBUTO dela (lado, dianteira/traseira, pelicula, tamanho
            # do trincado) — e ali o mapa de pecas ATRAPALHA: 📊 'porta dianteira'
            # contra ["DIANTEIRA","TRASEIRA"] devolvia None porque o veto de peca
            # eliminava as duas opcoes reais. Cada funcao diz quando a lista NAO
            # e dela ('dominio' == 'nenhum'), entao continua havendo um so lugar
            # que decide cada pergunta — nunca dois placares para a mesma.
            critico = _is_critical_select(target)
            esp = explicar_especifico(value, [t for t, _ in reais], target)
            if esp["dominio"] != "nenhum":
                escolha = esp["escolha"]
            else:
                escolha = explicar_match(value, [t for t, _ in reais])["escolha"]
            # Campo de FORMATO: qualquer opcao valida serve. Mas NUNCA quando a
            # pergunta e um atributo do 80% — ali a 1a opcao seria sortear lado,
            # tamanho ou posicao, e o portal nao deixa corrigir depois.
            if escolha is None and not critico and esp["dominio"] == "nenhum":
                escolha = reais[0][0]
            if escolha is None:
                # Campo CRITICO sem match confiante: FECHA o overlay e devolve as
                # opcoes REAIS ao cerebro. A proxima decisao ve a lista em
                # acoes_ja_feitas e copia o texto exato. Inteligencia, nao chute.
                try:
                    await page.keyboard.press("Escape")
                except Exception:  # noqa: BLE001
                    pass
                return "mdselect_options=" + " | ".join(t[:60] for t, _ in reais[:20])
            # 3) CLICAR a opcao escolhida. Primeiro pelo elemento; se o backdrop de
            # um md-select anterior interceptar (estourava 4s no Playwright), cai
            # no ng-click via JS, que e imune a interceptacao.
            alvo = next(o for t, o in reais if t == escolha)
            try:
                await alvo.click(timeout=3000)
            except Exception:  # noqa: BLE001
                await page.evaluate(
                    """(txt) => {
                      const lim = t => (t||'').replace(/\\s+/g,' ').trim();
                      const vis = el => !!(el.offsetParent || el.getClientRects().length);
                      const o = [...document.querySelectorAll('md-option')].filter(vis)
                                 .find(x => lim(x.textContent) === txt);
                      if (o) { o.click(); return true; }
                      return false;
                    }""",
                    escolha,
                )
            await page.wait_for_timeout(300)
            return f"mdselect={_norm(escolha)}"
    except Exception:  # noqa: BLE001
        pass
    # DIAGNOSTICO: nada clicavel — grava o overlay real p/ ver o que tem.
    global LAST_MDSELECT_DEBUG
    try:
        LAST_MDSELECT_DEBUG = await page.evaluate(
            """() => [...document.querySelectorAll('md-option')].map(o => ({
                 text:(o.textContent||'').trim().slice(0,40),
                 val:o.getAttribute('value')||o.getAttribute('ng-value')||'',
                 vis:!!(o.offsetParent||o.getClientRects().length),
                 html:o.outerHTML.slice(0,160)}))"""
        )
    except Exception:  # noqa: BLE001
        LAST_MDSELECT_DEBUG = "eval_fail"
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


async def _pick_autocomplete(page, value: str) -> bool:
    """AngularJS md-autocomplete: apos digitar, clica a sugestao que casa (senao o
    md-selected-item nao seta e o Avancar fica desabilitado). Poll: as sugestoes
    carregam com debounce/busca. Clica em JS (imune a interceptacao). False se nao
    houver sugestao (input normal)."""
    for _ in range(4):
        await page.wait_for_timeout(450)
        try:
            res = await page.evaluate(
                """(want) => {
                  const n = t => (t||'').normalize('NFKD').replace(/[\\u0300-\\u036f]/g,'').trim().toLowerCase();
                  const w = n(want);
                  const vis = el => !!(el.offsetParent || el.getClientRects().length);
                  const all = [...document.querySelectorAll(
                     '.md-autocomplete-suggestions li, md-autocomplete-suggestions li, li.md-autocomplete-suggestion, ul.md-autocomplete-suggestions li')].filter(vis);
                  // ignora mensagem de "nenhum resultado" (nao e opcao clicavel de verdade)
                  const bad = t => /nenhum|nao encontr|sem resultado|no results|nenhuma op/.test(n(t));
                  const lis = all.filter(o => !bad(o.textContent));
                  if (!all.length) return {found:0};
                  if (!lis.length) return {found:all.length, ok:false, noresult:true};
                  // preferencia: exato -> comeca-com -> contem -> primeira sugestao
                  let hit = w && (lis.find(o => n(o.textContent) === w)
                              || lis.find(o => n(o.textContent).startsWith(w) || w.startsWith(n(o.textContent)))
                              || lis.find(o => n(o.textContent).includes(w) || w.includes(n(o.textContent))));
                  if (!hit) hit = lis[0];
                  hit.click();
                  return {found:lis.length, ok:true, text:(hit.textContent||'').trim().slice(0,30)};
                }""",
                value,
            )
        except Exception:  # noqa: BLE001
            return False
        if isinstance(res, dict) and res.get("found"):
            return bool(res.get("ok"))
    return False


async def apply_action(page, action: Dict[str, Any]) -> str:
    a = action.get("action")
    target = action.get("target") or ""
    value = action.get("value") or ""
    if a == "fill":
        el = await _find_input(page, target)
        if el:
            await el.fill(str(value))
            try:
                await el.evaluate("e => e.dispatchEvent(new Event('input',{bubbles:true}))")
            except Exception:  # noqa: BLE001
                pass
            # md-autocomplete (estado/cidade): digitar NAO basta — o Avancar depende do
            # ITEM selecionado. Se aparecerem sugestoes, clica a que casa. Se nao houver
            # (input normal), dispara change+blur pra o AngularJS validar.
            picked = await _pick_autocomplete(page, value)
            if not picked:
                try:
                    await el.evaluate(
                        "e => ['change','blur'].forEach(t => e.dispatchEvent(new Event(t,{bubbles:true})))")
                except Exception:  # noqa: BLE001
                    pass
            return "filled_autocomplete" if picked else "filled"
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
        r = await _click_button(page, target)
        if r == "clicked":
            return "clicked"
        if r == "disabled":
            faltam = await _campos_que_faltam(page)
            return ("click_bloqueado: o botao existe mas esta DESABILITADO. Falta preencher: "
                    + (", ".join(faltam) if faltam else "campo obrigatorio nao identificado"))
        return "click_notfound"
    return "noop"


def _rotulo_do_campo(state: Dict[str, Any], alvo: str) -> str:
    """PURO: a pergunta LITERAL que o portal fez naquele campo. O cerebro mira
    ora pelo name tecnico ('qualItemDanificado'), ora pelo rotulo — aqui o
    name vira a frase que o humano vai ler ('Qual foi a peca danificada?')."""
    t = _norm(alvo)
    if not t:
        return ""
    for campo in list((state or {}).get("mdselects") or []) + list((state or {}).get("selects") or []):
        nome, rotulo = _norm(campo.get("name") or ""), str(campo.get("label") or "").strip()
        if rotulo and nome and (t == nome or t in nome or nome in t):
            return rotulo
    return alvo


def _pedido_do_segurado(collected: Dict[str, Any]) -> Dict[str, Any]:
    """PURO: o que o segurado disse, do jeito que ele disse. Vai junto com toda
    parada — sem isso, quem for resolver no lugar do robo nao sabe o que casar."""
    dano = (collected or {}).get("dano") or {}
    return {k: v for k, v in {
        "peca": dano.get("peca"), "como": dano.get("como"),
        "onde": dano.get("onde"), "descricao": dano.get("descricao"),
    }.items() if v}


# ---------------------------------------------------------------------------
# O PASSO 7 — o protocolo ja nasceu; falta dizer ONDE o servico acontece
# ---------------------------------------------------------------------------
# 📊 A tela (mapa §7) mostra `Nº do atendimento: 22842291` no topo e, abaixo,
# "Escolha a loja onde deseja realizar o serviço": ou "Agendar a domicilio",
# ou uma lista de lojas com endereco e "Agendar na loja".
#
# 🔴 POR QUE O ROBO NAO ESCOLHE, E POR QUE ISSO NAO E COVARDIA
#
# 1. A lista de lojas so existe NESTA tela. O segurado nunca a viu. Perguntar
#    antes "qual loja?" seria pedir que ele responda algo que ele nao sabe.
# 2. Escolher por ele — a primeira, a mais perto — e sortear com passos extras:
#    quem mora numa ponta da cidade e trabalha na outra tem uma resposta que
#    nenhuma heuristica de distancia adivinha.
# 3. E o portal NAO deixa corrigir: seria preciso abrir OUTRO acionamento
#    (mapa §3 e §9.5). Nao existe desfazer.
#
# 🔴 E POR QUE O ROBO TAMBEM NAO CLICA EM "Agendar a domicilio" — nem quando o
# segurado pediu domicilio. O que vem DEPOIS desse botao e uma tela de
# AGENDAMENTO (dia e hora) que 📊 nunca foi capturada (mapa §7, lacunas) e para
# a qual nao temos dado nenhum do segurado. Clicar so mudaria o sorteio de tela:
# em vez de sortear a loja, o robo sortearia o dia em que um tecnico vai a casa
# de alguem. Parar aqui e mais barato do que parar uma tela adiante — e o
# protocolo, que era a coisa irrecuperavel, ja esta salvo.
#
# O que a preferencia coletada na conversa compra, entao: o dossie chega
# RESOLVIDO. Quem termina nao precisa ligar de volta para o segurado — ja sabe
# se ele quer o tecnico em casa ou se vai levar o carro, e ja ve na mesma tela
# se o CEP dele tem domicilio.
_ONDE_REALIZAR_O_SERVICO = "onde_realizar_o_servico"


def preferencia_do_segurado(collected: Dict[str, Any]) -> str:
    """PURO: 'domicilio' | 'loja' | ''. Le a resposta coletada na conversa, que
    viaja em `especificos` — o mesmo transporte das respostas do 80%."""
    especificos = (collected or {}).get("especificos") or {}
    if not isinstance(especificos, dict):
        return ""
    return preferencia_de_atendimento(str(especificos.get(_ONDE_REALIZAR_O_SERVICO) or ""))


def decidir_no_passo_7(state: Dict[str, Any], collected: Dict[str, Any]) -> Dict[str, Any]:
    """PURO: o dossie da tela do protocolo. NUNCA devolve uma escolha de loja.

    Devolve os FATOS da tela (protocolo, se ha domicilio, se ha lojas), o que o
    segurado pediu, e a frase que diz a quem for terminar exatamente o que fazer.
    """
    state = state or {}
    botoes = state.get("buttons") or []
    protocolo = extrair_protocolo(state.get("text", ""))
    preferencia = preferencia_do_segurado(collected)
    domicilio, loja = botao_de_domicilio(botoes), botao_de_loja(botoes)

    if preferencia == "domicilio" and domicilio:
        recomendacao = (f"O segurado pediu atendimento a DOMICILIO e o portal oferece '{domicilio}' "
                        "para o CEP dele: clique nesse botao e agende com ele o dia e a hora.")
    elif preferencia == "domicilio" and not domicilio:
        recomendacao = ("O segurado pediu atendimento a DOMICILIO, mas o portal NAO oferece domicilio "
                        "nesta tela — 📊 ele depende de disponibilidade no CEP. Avise o segurado e "
                        "escolha com ele uma das lojas listadas.")
    elif preferencia == "loja":
        recomendacao = ("O segurado prefere LEVAR o carro. Mostre a ele as lojas desta tela (nome, "
                        "endereco e distancia) e deixe que ELE escolha — eu nao escolho loja.")
    else:
        recomendacao = ("Ainda nao sei se o segurado prefere que o tecnico va ate ele ou levar o carro "
                        "numa loja. Pergunte, e escolha com ele nesta tela.")
    if not (domicilio or loja):
        recomendacao += (" (Nenhum botao de agendamento visivel nesta leitura — confira a tela real "
                         "antes de concluir.)")

    return {
        "protocolo": protocolo,
        "preferencia": preferencia,
        "tem_domicilio": bool(domicilio),
        "tem_loja": bool(loja),
        "botao_domicilio": domicilio,
        "botao_loja": loja,
        "recomendacao": recomendacao,
        "pedido_do_segurado": _pedido_do_segurado(collected),
    }


async def _estado_seguro(page) -> Dict[str, Any]:
    """capture_state que nunca derruba a parada. Registrar o motivo do
    needs_human nao pode transformar uma parada honesta em 'failed'."""
    try:
        return await capture_state(page)
    except Exception:  # noqa: BLE001
        return {}


def _registrar_parada(evidence: Dict[str, Any], state: Dict[str, Any], collected: Dict[str, Any],
                      campo: str = "", pergunta: str = "", opcoes: Optional[List[str]] = None) -> None:
    """Uma parada so vale se um humano resolver em 10 segundos. Entao ela guarda
    SEMPRE: o passo, a pergunta literal do portal, TODAS as opcoes oferecidas e o
    que o segurado disse. 📊 03/08/2026: nos 33 needs_human de producao,
    evidence.opcoes estava NULO em 33 — ninguem tinha como decidir sem reabrir o
    portal, e a proxima versao do match_option nao tinha com o que aprender."""
    state = state or {}
    evidence["passo"] = {
        "url": state.get("url") or "",
        "titulo": state.get("heading") or "",
        "obrigatorios_vazios": state.get("pending_required") or [],
    }
    evidence["pedido_do_segurado"] = _pedido_do_segurado(collected)
    if campo:
        evidence["campo"] = campo
    if pergunta:
        evidence["pergunta"] = pergunta
    if opcoes:
        evidence["opcoes"] = [str(o) for o in opcoes]
    # Se o cerebro nao nomeou o campo, guarda TODOS os dropdowns da tela com as
    # opcoes reais: e o material bruto do proximo ajuste do casamento.
    if not evidence.get("opcoes"):
        listas = [{"campo": s.get("label") or s.get("name") or "", "opcoes": s.get("options") or []}
                  for s in (state.get("selects") or []) if s.get("options")]
        if listas:
            evidence["dropdowns_da_tela"] = listas[:6]


# ---------------------------------------------------------------------------
# O QUE E FATO NAO PASSA POR UM MODELO
# ---------------------------------------------------------------------------
# 📊 Autopsia dos 39 acionamentos (04/08/2026, Supabase dcajcvlzcjbmyapmklil):
#
#   9  estouraram o teto de 22 passos
#   4  o cerebro PERGUNTOU um dado que estava no payload — inclusive
#      "Qual e o tipo de telefone do segurado?", que o proprio prompt do
#      sistema proibe literalmente
#   7  ele repetiu uma acao que ja tinha voltado `filled` / `mdselect=corretor`,
#      ou seja, que TINHA FUNCIONADO
#   1  mandou "Santa Catarina" num autocomplete onde o prompt manda usar a SIGLA
#
# 📊 E nao foi falta de cerebro: ZERO jobs registram `cerebro de visao
# indisponivel` ou `nao consegui decidir`. Ele estava la, com a instrucao na
# frente, e nao seguiu.
#
# Nome da corretora, e-mail, CNPJ, telefone, relacao (`Corretor`), estado,
# cidade e CEP tem **um unico valor certo, sabido antes de a tela abrir**.
# Mandar um modelo "decidir" preenche-los cria tres riscos de graca: ele
# pergunta o que ja sabe, erra o formato, ou gasta passos do teto.
#
# Cada campo preenchido por codigo e um passo que nao e gasto — e o teto foi
# atingido 9 vezes.
#
# A REGRA DE SEGURANCA: so preenche quando EXATAMENTE UM campo visivel e vazio
# casa. Duas correspondencias = ambiguidade = o cerebro decide. E o mesmo
# principio do `explicar_match`: na duvida, nao chuta.
_FATOS_DE_TEXTO = (
    # (chave, pistas que identificam o campo, pistas que o DESQUALIFICAM)
    ("nome",     ("nome-solicitante", "nome completo", "nome do solicitante"), ("segurado",)),
    ("cpf_cnpj", ("cpf-cnpj-solicitante", "cpf ou cnpj", "cnpj"), ("inserir-cpf", "placa")),
    ("email",    ("email", "e-mail"), ()),
    ("telefone", ("telefone",), ("tipo",)),
)
_FATOS_DE_LOCAL = (
    ("estado", ("estado", "uf"), ("cidade",)),
    ("cidade", ("cidade",), ("estado",)),
    ("cep",    ("cep",), ()),
)


def _identidade_do_campo(campo: Dict[str, Any]) -> str:
    return _norm(" ".join(str(campo.get(k) or "") for k in ("id", "name", "placeholder", "label")))


def fatos_da_tela(state: Dict[str, Any], collected: Dict[str, Any]) -> List[Dict[str, str]]:
    """PURO: quais campos DESTA tela tem valor conhecido e ainda estao vazios.

    Devolve [{'alvo', 'valor', 'de'}]. Vazio quando nao ha nada obvio a fazer —
    e ai o cerebro trabalha, que e para o que ele serve.
    """
    state = state or {}
    solicitante = (collected or {}).get("solicitante") or {}
    local = (collected or {}).get("local") or {}
    campos = [c for c in (state.get("inputs") or []) if not str(c.get("value") or "").strip()]

    saida: List[Dict[str, str]] = []
    for origem, chaves in ((solicitante, _FATOS_DE_TEXTO), (local, _FATOS_DE_LOCAL)):
        for chave, pistas, proibidas in chaves:
            valor = str(origem.get(chave) or "").strip()
            if not valor:
                continue
            casaram = [c for c in campos
                       if any(p in _identidade_do_campo(c) for p in pistas)
                       and not any(x in _identidade_do_campo(c) for x in proibidas)]
            # Zero: o campo nao esta nesta tela. Dois ou mais: ambiguo — quem
            # decide e o cerebro, com a tela inteira na frente.
            if len(casaram) != 1:
                continue
            c = casaram[0]
            saida.append({"alvo": str(c.get("id") or c.get("name") or c.get("label") or ""),
                          "valor": valor, "de": chave})
    return saida


async def preencher_o_que_e_fato(page, state: Dict[str, Any], collected: Dict[str, Any]) -> List[str]:
    """Preenche os campos de valor conhecido. Devolve o que foi preenchido."""
    feitos: List[str] = []
    for f in fatos_da_tela(state, collected):
        if not f["alvo"]:
            continue
        try:
            r = await apply_action(page, {"action": "fill", "target": f["alvo"], "value": f["valor"]})
        except Exception:  # noqa: BLE001
            continue
        if str(r).startswith("filled"):
            feitos.append(f["de"])
            await page.wait_for_timeout(250)

    # A relacao com o titular tem UM valor certo: somos a corretora. E o tipo de
    # telefone e formato puro — qualquer opcao valida serve, e o cerebro chegou a
    # PERGUNTAR por ele. Nenhum dos dois merece uma chamada de modelo.
    for alvo, valor, nome in (("relacao com o titular", "Corretor", "relacao"),
                              ("segr", "Corretor", "relacao"),
                              ("tipo de telefone", "", "tipo_de_telefone")):
        if nome in feitos:
            continue
        vazio_obrigatorio = any(
            _norm(alvo) in _norm(str(m.get("label") or "") + " " + str(m.get("name") or ""))
            and m.get("empty_required")
            for m in (state.get("mdselects") or []))
        if not vazio_obrigatorio:
            continue
        try:
            r = await apply_action(page, {"action": "select", "target": alvo, "value": valor})
        except Exception:  # noqa: BLE001
            continue
        if str(r).startswith(("mdselect=", "select=", "select_default=")):
            feitos.append(nome)
            await page.wait_for_timeout(250)
    return feitos


async def run_adaptive(page, goal: str, collected: Dict[str, Any], evidence: Dict[str, Any],
                       max_steps: int = MAX_STEPS, confirm: bool = False) -> JourneyResult:
    """Loop agentico: preenche o que e FATO -> enxerga -> cerebro decide o resto."""
    history: List[Dict[str, Any]] = []
    for _ in range(max_steps):
        state = await capture_state(page)
        # Antes de gastar um passo com o modelo: o que ja sabemos, escrevemos.
        # Nao consome passo do teto de proposito — preencher o conhecido nao e
        # uma decisao, e transcricao.
        preenchidos = await preencher_o_que_e_fato(page, state, collected)
        if preenchidos:
            evidence.setdefault("preenchidos_por_fato", []).extend(preenchidos)
            state = await capture_state(page)
        if has_protocol(state):
            # O pedido JA EXISTE na seguradora. A PRIMEIRA coisa a fazer, antes
            # de decidir qualquer outra, e gravar o numero: dai em diante nada
            # que der errado consegue mais apaga-lo.
            protocolo = registrar_protocolo(evidence, state.get("text", ""))
            evidence["final"] = state.get("text", "")[:1200]
            passo7 = decidir_no_passo_7(state, collected)
            evidence["passo7"] = passo7
            # 🔴 `done`, e nao `needs_human`, mesmo faltando escolher a loja.
            # Nao e otimismo: `needs_human` neste sistema significa "aprove e eu
            # continuo" e abre a porta para o job ser reenfileirado — e reexecutar
            # este acionamento comecaria do passo 1 e criaria um SEGUNDO
            # atendimento na seguradora (mapa §9.5). O trabalho que a tool
            # prometeu ("abrir o atendimento") esta FEITO e tem numero; o que
            # falta e uma escolha do segurado, e ela vai escrita no resultado.
            return JourneyResult(
                status="done",
                captured={"stage": "protocolo", "protocolo": protocolo},
                message=((f"atendimento aberto no portal, N {protocolo}. " if protocolo
                          else "atendimento aberto no portal (o portal nao mostrou o numero nesta tela). ")
                         + passo7["recomendacao"]),
            )
        if is_confirm_screen(state) and not confirm:
            # A TRAVA: o passo 6 e o que ABRE o pedido na seguradora. Sem
            # confirm=True nada e enviado — para aqui e espera aprovacao humana.
            evidence["stage_80"] = state.get("text", "")[:600]
            _registrar_parada(evidence, state, collected,
                              pergunta=state.get("heading") or "Confirme a peca danificada")
            return JourneyResult(status="needs_human", captured={"stage": "confirme_80"},
                                 message="cheguei na confirmacao (80%) — aprove para enviar")
        action = await decide_next_action(state, goal, collected, history)
        history.append(action)
        if action["action"] == "done":
            # SEGURANCA: com confirm=False nunca finalizamos sozinhos. "done" = o cerebro
            # terminou de preencher -> paramos p/ revisao/aprovacao humana (nada e enviado).
            evidence["final_state"] = {"heading": state.get("heading", ""),
                                       "text": (state.get("text") or "")[:800],
                                       "buttons": state.get("buttons", [])}
            if not confirm:
                _registrar_parada(evidence, state, collected,
                                  pergunta=state.get("heading") or "revisao final antes de enviar")
                return JourneyResult(status="needs_human", captured={"stage": "fim_preenchimento"},
                                     message="preenchimento completo — pare para revisao/aprovacao antes de enviar")
            # Ultima rede: o cerebro pode declarar fim numa tela cuja redacao do
            # protocolo o `tem_protocolo` nao reconheca. Se o numero estiver ali,
            # ele sai daqui gravado; se nao estiver, nada e inventado.
            protocolo = registrar_protocolo(evidence, state.get("text", ""))
            return JourneyResult(status="done", captured={"protocolo": protocolo} if protocolo else {},
                                 message=(f"concluido (adaptive) — atendimento N {protocolo}"
                                          if protocolo else "concluido (adaptive)"))
        if action["action"] == "ask_human":
            # Backstop anti-travamento: o cerebro tende a "pedir por educacao" em selects/radios.
            # Forca UMA re-decisao imperativa antes de desistir. So devolve needs_human se, mesmo
            # obrigado a escolher, ele ainda insistir em perguntar (dado de identidade real faltando).
            forced = await decide_next_action(state, goal, collected, history, force=True)
            if forced.get("action") in ("fill", "select", "check", "click"):
                action = forced
                history[-1] = action
            else:
                evidence["debug_dom"] = await _dump_dom(page)
                _registrar_parada(evidence, state, collected, pergunta=str(action.get("value") or ""))
                return JourneyResult(status="needs_human", captured={"pergunta": action.get("value")},
                                     message=aviso_de_pedido_aberto(evidence)
                                     + f"preciso de: {action.get('value')}")
        applied = await apply_action(page, action)
        # 🔴 A JANELA MAIS CARA DO FLUXO INTEIRO. E um clique que CRIA o pedido, e
        # entre ele e a proxima leitura completa da tela cabem uma excecao do
        # Playwright, a parada por tela travada e o fim do teto de passos. Ler o
        # texto AQUI custa um evaluate e fecha a janela: o numero fica gravado
        # antes de qualquer coisa poder dar errado.
        if applied == "clicked":
            await registrar_protocolo_da_pagina(page, evidence)
        # O cerebro VE o resultado de cada acao (acoes_ja_feitas): um select que nao
        # casou volta com as opcoes REAIS (mdselect_options=...) e a proxima decisao
        # escolhe o texto exato da lista — inteligencia com a lista na mao, sem chute.
        history[-1] = {**action, "resultado": applied[:220]}
        if applied.startswith(("mdselect_options=", "select_options=")):
            evidence["campo"] = action.get("target")
            evidence["opcoes"] = [o.strip() for o in applied.split("=", 1)[1].split("|") if o.strip()]
            evidence["pergunta"] = _rotulo_do_campo(state, str(action.get("target") or ""))
            evidence["pedido_do_segurado"] = _pedido_do_segurado(collected)
        sig = (action.get("action"), action.get("target"), action.get("value"), applied)
        steps = evidence.setdefault("adaptive_steps", [])
        steps.append({"a": sig[0], "t": sig[1], "v": (action.get("value") or "")[:30], "r": applied[:80]})
        # Parada antecipada: 3 acoes identicas seguidas sem mudar nada = tela travada.
        # Para com o DOM (diagnostico) em vez de arrastar ate MAX_STEPS.
        sigs = [(s["a"], s["t"], s["v"], s["r"]) for s in steps[-3:]]
        if len(sigs) == 3 and len(set(sigs)) == 1:
            evidence["debug_dom"] = await _dump_dom(page)
            evidence["mdselect_overlay"] = LAST_MDSELECT_DEBUG
            estado_final = await _estado_seguro(page)
            registrar_protocolo(evidence, estado_final.get("text", ""))
            _registrar_parada(evidence, estado_final, collected,
                              campo=str(sig[1] or ""), pergunta=f"o portal nao aceitou: {applied}"[:200])
            return JourneyResult(status="needs_human", captured={"stage": "sem_progresso"},
                                 message=aviso_de_pedido_aberto(evidence)
                                 + f"tela travada: repetiu '{sig[0]} {sig[1]} {sig[2]}' -> {applied}")
        await page.wait_for_timeout(1200)
    # DIAGNOSTICO: se travou, despeja o DOM real da tela pra achar a causa (nao chutar).
    evidence["debug_dom"] = await _dump_dom(page)
    evidence["mdselect_overlay"] = LAST_MDSELECT_DEBUG
    estado_final = await _estado_seguro(page)
    registrar_protocolo(evidence, estado_final.get("text", ""))
    _registrar_parada(evidence, estado_final, collected,
                      pergunta="cheguei ao teto de passos sem concluir")
    return JourneyResult(status="needs_human", captured={"steps": evidence.get("adaptive_steps")},
                         message=aviso_de_pedido_aberto(evidence)
                         + "muitos passos sem concluir (adaptive) — precisa de revisao")


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
              // Campos obrigatorios AINDA invalidos = o que bloqueia o Avancar.
              const invalids = [...document.querySelectorAll('input,textarea,select,md-select,md-datepicker,md-checkbox,md-radio-group,md-input-container,md-autocomplete')]
                .filter(e => /ng-invalid/.test(e.className) && (/ng-required|ng-invalid-required/.test(e.className) || e.required))
                .map(e => ({tag:e.tagName, name:e.getAttribute('name')||'', id:e.id,
                            cls:e.className.slice(0,80), ph:e.getAttribute('placeholder')||'',
                            val:(e.value||'').slice(0,25), vis:vis(e)}));
              const inputs = [...document.querySelectorAll('input,textarea')].filter(vis)
                .map(e => ({name:e.name, id:e.id, type:e.type, req:!!e.required,
                            val:(e.value||'').slice(0,30), cls:e.className.slice(0,60)}));
              const buttons = [...document.querySelectorAll('button,a[role=button],md-button,[role=button]')].filter(vis)
                .map(b => ({text:(b.textContent||'').trim().slice(0,30), disabled:!!b.disabled}))
                .filter(b => b.text);
              const text = (document.body.innerText||'').replace(/\\s+/g,' ').slice(0,600);
              return {selects, matselects, advance, invalids, inputs, buttons, text,
                      heading:(document.querySelector('h1,h2,h3')||{}).textContent||''};
            }"""
        )
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"}
