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

📊 CONFERIDO contra producao em 03/08/2026 (Supabase dcajcvlzcjbmyapmklil, 39
portal_jobs de 06 a 10/07/2026). Os 8 passos continuam valendo; os nomes reais
dos campos, vistos nos jobs, sao:
  passo2  segr (relacao) · email-segurado-input · nome-solicitante-input ·
          cpf-cnpj-solicitante-input · telefone-input · TipoTelefoneSolicitante0
  passo3  qualItemDanificado · comoOcorreuDanoVeiculo · ondeOcorreuDano ·
          descrever-acontecimento-textarea
  local   estado e cidade sao md-autocomplete (o estado exige a SIGLA: 'SC')
  80%     "Confirme a peca danificada" + "O vidro danificado tem pelicula de
          controle solar (insulfilm)?" — SIM / NAO / Nao sabe
O passo 7 (loja/protocolo) NUNCA foi alcancado: em 39 acionamentos, zero
protocolos capturados (has_protocol jamais retornou True).

DESIGN "cerebro unico": o AGENTE (Smith) DECIDE as escolhas (peca/como/onde/
especificos) a partir da conversa com o segurado; a journey CASA a escolha com a
opcao real do dropdown (match_option). Sem match confiante -> needs_human COM as
opcoes disponiveis (o agente/humano decide; a journey nunca escolhe errado nem
trava). match_option e puro e testavel offline — e e o UNICO placar do sistema:
o adaptive.py o importa em vez de manter um segundo, escrito em JS, que decidia
diferente do que os testes provavam.

A TRAVA: o passo 6 e o que ABRE o pedido. run_adaptive para nele com
confirm=False (is_confirm_screen) e tambem recusa o 'done' do cerebro sem
confirm. Nao afrouxar: 📊 o unico job 'done' de producao foi criado
03:51:55Z de 07/07, quatro minutos ANTES de a trava existir (commit 7d31490,
03:56:10Z), com confirm=false e sem protocolo nenhum.
"""
from __future__ import annotations

import unicodedata
from typing import Any, Dict, List, Optional

from portal_worker.journeys import JourneyResult

VIDROS_BASE = "https://abraseuatendimento.com.br/#/"


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(s.split())


# ---------------------------------------------------------------------------
# VOCABULARIO DE PECAS — portugues do Brasil (como o segurado FALA) x como o
# portal ESCREVE. Cada chave e uma IDENTIDADE de peca. Duas identidades
# diferentes NUNCA sao a mesma peca: e essa regra que impede 'vidro da porta'
# de virar 'VIDRO PARABRISA - CARGA'.
#
# 📊 medido em 03/08/2026 (Supabase dcajcvlzcjbmyapmklil, portal_jobs):
#     qualItemDanificado   'vidro da porta'   -> VIDRO PARABRISA - CARGA   3x
#     comoOcorreuDanoVeiculo 'deixei o carro estacionado...' -> CHOQUE TERMICO 3x
# Nos dois casos a opcao CERTA nao existia na lista daquela seguradora, e um
# unico token generico ('vidro') bastou para o casamento errado.
# ---------------------------------------------------------------------------
_PECAS = {
    "parabrisa":  ("parabrisa", "windshield"),
    "lateral":    ("porta", "janela", "lateral", "basculante", "ventarola", "quebra-vento"),
    "vigia":      ("vigia",),
    "retrovisor": ("retrovisor", "espelho"),
    "farol":      ("farol", "farolete", "farolim"),
    "lanterna":   ("lanterna",),
    "teto":       ("teto", "panoramico"),
}
# 'luz' nao identifica peca: pode ser farol OU lanterna. Fica AMBIGUO de
# proposito — se o portal oferecer os dois, a funcao para em vez de escolher.
_AMBIGUOS = {"luz": ("farol", "lanterna"), "lampada": ("farol", "lanterna"),
             "farois": ("farol",), "luzes": ("farol", "lanterna")}
# Modificador de POSICAO: so vira identidade quando nao ha substantivo de peca
# ('vidro dianteiro' = parabrisa; mas 'porta dianteira' continua sendo LATERAL).
_POSICAO = {"dianteiro": "parabrisa", "dianteira": "parabrisa", "frontal": "parabrisa",
            "frente": "parabrisa", "traseiro": "vigia", "traseira": "vigia"}
# Expressoes de varias palavras, resolvidas ANTES de separar em tokens.
_EXPRESSOES = (
    ("para brisa", "parabrisa"), ("para-brisa", "parabrisa"), ("parabrisas", "parabrisa"),
    ("vidro dianteiro", "parabrisa"), ("vidro da frente", "parabrisa"),
    ("vidro frontal", "parabrisa"), ("vidro traseiro", "vidro vigia"),
    ("vidro de tras", "vidro vigia"), ("oculo traseiro", "vidro vigia"),
    ("oculos traseiro", "vidro vigia"), ("espelho retrovisor", "retrovisor"),
)
_STOP = {"de", "da", "do", "das", "dos", "e", "o", "a", "os", "as", "um", "uma",
         "no", "na", "em", "para", "por", "com", "meu", "minha", "the"}
# Substantivo de CATEGORIA: nomeia o balcao, nao a peca. Num portal de vidros
# 'vidro' esta em quase toda opcao — nao distingue nem desqualifica nada.
_CATEGORIA = {"vidro", "peca", "item", "veiculo", "carro", "auto", "automovel"}

# Confianca minima e distancia minima para o 2o colocado. Abaixo disso a
# funcao devolve None: parar e o comportamento correto (o agente/humano ve as
# opcoes e decide). NUNCA "chutar o mais proximo".
_CONFIANCA_MINIMA = 1.0
_MARGEM_MINIMA = 0.5


def _singular(t: str) -> str:
    """Plural do portugues -> singular (lanternas->lanterna, retrovisores->
    retrovisor, farois->farol, laterais->lateral)."""
    for fim, troca in (("oes", "ao"), ("ais", "al"), ("eis", "el"), ("ois", "ol"),
                       ("res", "r"), ("ns", "m")):
        if t.endswith(fim) and len(t) > len(fim) + 1:
            return t[: -len(fim)] + troca
    return t[:-1] if t.endswith("s") and len(t) > 3 else t


def _tokens(s: str) -> List[str]:
    """Texto -> tokens comparaveis: sem acento, sem pontuacao, sem plural, sem
    palavra vazia. A ORDEM nao importa (conjunto), entao 'porta do vidro' e
    'vidro da porta' dao o mesmo resultado."""
    t = _norm(s)
    for de, para in _EXPRESSOES:
        t = t.replace(de, para)
    limpo = "".join(c if c.isalnum() else " " for c in t)
    return [_singular(x) for x in limpo.split() if x and x not in _STOP]


def identidade_peca(texto: str) -> set:
    """PURO: quais IDENTIDADES de peca o texto nomeia. Vazio = o texto nao fala
    de peca (ex.: uma causa de dano) — ai o casamento cai so nas palavras."""
    toks = set(_tokens(texto))
    achados = {nome for nome, sin in _PECAS.items()
               if any(_singular(_norm(s)) in toks for s in sin)}
    for t in toks:                      # 'luz' pode ser farol OU lanterna
        if t in _AMBIGUOS:
            achados.update(_AMBIGUOS[t])
    if not achados:                     # so entao a posicao vira identidade
        for t in toks:
            if t in _POSICAO:
                achados.add(_POSICAO[t])
    return achados


def explicar_match(wanted: str, options: List[str]) -> Dict[str, Any]:
    """PURO: decide E explica. {'escolha', 'motivo', 'placar', 'opcoes'}.
    'escolha' None = ninguem casou com confianca -> quem chamou PARA e mostra
    'opcoes' para o agente/humano decidir. Testavel offline."""
    reais = [o for o in (options or []) if str(o).strip() and "selecione" not in _norm(o)]
    vazio = {"escolha": None, "motivo": "sem_opcoes", "placar": [], "opcoes": reais}
    if not str(wanted or "").strip() or not reais:
        return vazio

    alvo = _norm(wanted)
    for o in reais:                                     # 1) igualdade literal
        if _norm(o) == alvo:
            return {"escolha": o, "motivo": "exato", "placar": [(o, 999.0)], "opcoes": reais}

    tw, cw = set(_tokens(wanted)), identidade_peca(wanted)
    if not tw:
        return {**vazio, "motivo": "pedido_vazio"}

    # 2) Peso por raridade: um token que aparece em TODA opcao ('vidro' num
    # portal de vidros) nao distingue nada — foi ele que casou 'vidro da porta'
    # com 'VIDRO PARABRISA - CARGA'. Palavra rara vale; palavra comum, quase nada.
    tokens_por_opcao = {o: set(_tokens(o)) for o in reais}
    def peso(t: str) -> float:
        if len(reais) < 3:
            return 1.0
        freq = sum(1 for s in tokens_por_opcao.values() if t in s) / len(reais)
        return 0.0 if freq >= 1.0 else (0.25 if freq > 0.6 else 1.0)

    placar = []
    for o in reais:
        to, co = tokens_por_opcao[o], identidade_peca(o)
        # 3) VETO: pedido e opcao nomeiam PECAS DIFERENTES -> nunca casa.
        if cw and co and not (cw & co):
            continue
        nota = sum(peso(t) for t in tw if t in to)
        if cw & co:
            nota += 1.0
        if tw <= to:            # a opcao e o pedido, mais especifico
            nota += 1.0
        # Qualificador extra na opcao ('- CARGA', 'BLINDADO') pede cautela. Nao
        # conta como extra: o substantivo da CATEGORIA ('vidro' num portal de
        # vidros) nem a palavra que nomeia a MESMA peca que o pedido — sao
        # sinonimos, nao ressalvas ('janela' x 'VIDRO DE PORTA').
        extras = [t for t in to if t not in tw and peso(t) > 0.5
                  and t not in _CATEGORIA and t not in _POSICAO and t not in _AMBIGUOS
                  and not (identidade_peca(t) & cw)]
        nota -= min(0.5, 0.25 * len(extras))
        placar.append((o, round(nota, 3)))

    placar.sort(key=lambda x: -x[1])
    if not placar:
        return {**vazio, "motivo": "peca_diferente"}
    melhor, nota = placar[0]
    segunda = placar[1][1] if len(placar) > 1 else 0.0
    # Sobrou UMA opcao da peca pedida e nenhuma concorrente: nao ha o que
    # confundir. E o caso de 'espelho' quando o portal so oferece um retrovisor.
    if len(placar) == 1 and cw and (cw & identidade_peca(melhor)) and nota >= 0.5:
        return {"escolha": melhor, "motivo": "unica_da_peca", "placar": placar, "opcoes": reais}
    if nota < _CONFIANCA_MINIMA:
        return {"escolha": None, "motivo": "confianca_baixa", "placar": placar, "opcoes": reais}
    if nota - segunda < _MARGEM_MINIMA:
        return {"escolha": None, "motivo": "ambiguo", "placar": placar, "opcoes": reais}
    return {"escolha": melhor, "motivo": "confiante", "placar": placar, "opcoes": reais}


def match_option(wanted: str, options: List[str]) -> Optional[str]:
    """PURO: a opcao do dropdown que casa com 'wanted' COM CONFIANCA. None
    quando nenhuma casa, quando o pedido nomeia outra peca, ou quando duas
    opcoes empatam — nesses casos quem chama PARA e mostra as opcoes. Casar
    errado abre um pedido errado na seguradora; parar so custa 10 segundos de
    um humano. Testavel offline."""
    return explicar_match(wanted, options)["escolha"]


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


async def _achar_campo(page, ids: tuple, pistas: tuple):
    """Acha um input pelo SENTIDO antes da POSICAO. 'pistas' casa contra
    name/id/placeholder/aria-label/label; 'ids' sao os seletores numerados pelo
    Angular (#input_1, #input_3), aceitos so quando o sentido nao resolve —
    id numerado depende da ordem dos campos e muda sem aviso."""
    try:
        metas = await page.evaluate(
            """() => [...document.querySelectorAll('input,textarea')].map((e, i) => {
                 let lab = (e.labels && e.labels[0] && e.labels[0].textContent) || '';
                 if (!lab) { const c = e.closest('md-input-container,md-autocomplete');
                             if (c) { const l = c.querySelector('label'); if (l) lab = l.textContent; } }
                 return {i, txt: [e.name, e.id, e.placeholder, e.getAttribute('aria-label'), lab]
                            .filter(Boolean).join(' '),
                         vis: !!(e.offsetParent || e.getClientRects().length)};
               })"""
        )
    except Exception:  # noqa: BLE001
        metas = []
    els = await page.query_selector_all("input,textarea")
    for m in metas or []:
        if m.get("vis") and any(p in _norm(m.get("txt")) for p in pistas):
            i = m.get("i")
            if isinstance(i, int) and i < len(els):
                return els[i]
    for sel in ids:                      # ultimo recurso: o id numerado de sempre
        el = await page.query_selector(sel)
        if el:
            return el
    return None


async def _campos_visiveis(page) -> List[Dict[str, Any]]:
    """Raio-X do passo1 quando ele nao e reconhecido — para o proximo ajuste ser
    feito com o DOM real na mao, e nao por chute."""
    try:
        return await page.evaluate(
            """() => [...document.querySelectorAll('input,textarea')]
                 .filter(e => !!(e.offsetParent || e.getClientRects().length))
                 .map(e => ({id:e.id, name:e.name, ph:e.placeholder||'', type:e.type}))"""
        ) or []
    except Exception:  # noqa: BLE001
        return []


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

    # passo1: CPF + placa + data (datepicker Material -> digita e fecha overlay).
    # Os ids #input_1/#input_3 sao NUMERADOS pelo Angular: dependem da ORDEM em
    # que os campos nascem. Um campo a mais na tela e a placa vai para o campo
    # errado, calada. Por isso procuramos primeiro pelo SENTIDO (label/placeholder/
    # name) e so caimos no id numerado como ultimo recurso.
    campo_cpf = await _achar_campo(page, ("#inserir-cpf-input",), ("cpf", "cnpj", "documento"))
    campo_placa = await _achar_campo(page, ("#input_1",), ("placa",))
    if not campo_cpf or not campo_placa:
        evidence["passo1"] = await _campos_visiveis(page)
        return JourneyResult(status="needs_human",
                             message="passo1 do portal mudou: nao achei o campo de CPF ou de placa")
    await campo_cpf.fill(cpf)
    await campo_placa.fill(placa)
    d = await _achar_campo(page, ("#input_3",), ("data", "sinistro", "ocorrencia", "ocorreu"))
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
