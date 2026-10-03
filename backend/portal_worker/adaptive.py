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

import asyncio
import base64
import contextvars
import json
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from portal_worker import modelo_do_portal as _MODELO
from portal_worker import redaction as _RED
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
    extrair_franquia,
    extrair_link_de_vistoria,
    extrair_protocolo,
    preferencia_de_atendimento,
    tem_protocolo,
)

VALID_ACTIONS = ("fill", "select", "click", "check", "done", "ask_human")
# 🔴 SPEC-116 U9: aqui morava `_MODELO_DE_RESERVA = "gpt-4o-mini"` — a "rede"
# que QUALQUER erro >= 400 (429 e 5xx inclusive) disparava calada, fora do
# ledger, com o modelo que a propria autopsia dos 39 acionamentos reprovou.
# Rebaixar sem avisar nao e rede: e trocar o cerebro no meio do acionamento.
# Quem escolhe o modelo agora e a ROTA `portal_decisao` (modelo_do_portal.py);
# reserva so se a rota declarar.
MAX_STEPS = 22

#: O job em curso (company_id/job_id) para o LEDGER do cerebro. `run_adaptive`
#: o preenche a partir do `runtime`; um contextvar, e nao um parametro, para que
#: `decide_next_action(state, goal, collected, history, force)` mantenha a
#: assinatura que os dubles de teste e a bancada ja usam.
_JOB_EM_CURSO: contextvars.ContextVar = contextvars.ContextVar("portal_job_em_curso", default=None)
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


def registrar_franquia_e_vistoria(evidence: Dict[str, Any], page_text: str) -> Dict[str, str]:
    """Grava FRANQUIA e LINK DA VISTORIA assim que aparecem, pelo mesmo motivo
    do protocolo — e nas mesmas condições.

    📊 SPEC-071 BLOCO 6: a tela que a Regina fotografou em 14/08 tem TRÊS
    coisas, e o robô lia uma:

        Atendimento nº 23085997     para o segurado COBRAR
        Franquia R$ 925,00          quanto ele vai PAGAR
        https://vistoria.mobi/...   por onde ele MANDA AS FOTOS

    🔴 E o link não é conveniência — é a substituição de um passo manual que já
    deu errado. 📊 No corpus de destilação (`pacotes/pacote_003.jsonl` e mais 9
    arquivos) está a prova de que hoje quem manda esse link é uma pessoa,
    colando à mão:

        ATENDENTE: te mandei o link errado
        ATENDENTE: segue correto
        ATENDENTE: https://vistoria.mobi/app/#/app/intro/...

    IDEMPOTENTE e no MESMO ponto do protocolo, e isso é deliberado: entre a
    tela aparecer e o fluxo acabar cabem um teto de passos estourado, uma tela
    travada e uma exceção do Playwright. Nos três o pedido JÁ EXISTE — e um
    segurado com atendimento aberto, sem saber quanto paga nem por onde manda
    as fotos, é o mesmo resultado ruim que o protocolo perdido.

    ⚠️ Grava em `evidence` porque é o dicionário que o worker escreve no job em
    TODOS os desfechos, inclusive no `except` que marca `failed`.
    """
    achados: Dict[str, str] = {}
    if not isinstance(evidence, dict):
        return achados

    if not str(evidence.get("franquia") or "").strip():
        valor = extrair_franquia(page_text)
        if valor:
            evidence["franquia"] = valor
            achados["franquia"] = valor

    if not str(evidence.get("link_vistoria") or "").strip():
        link = extrair_link_de_vistoria(page_text)
        if link:
            evidence["link_vistoria"] = link
            achados["link_vistoria"] = link

    return achados


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
    bruto = str(texto or "")
    # ⚠️ Os TRÊS na mesma leitura: eles saem da MESMA tela, e ler duas vezes
    # abriria a janela em que a página muda entre uma leitura e a outra —
    # gravando o protocolo de um pedido e a franquia de outro.
    registrar_franquia_e_vistoria(evidence, bruto)
    return registrar_protocolo(evidence, bruto)


# ---------------------------------------------------------------------------
# A PROVA — a foto da tela que o robo estava vendo
# ---------------------------------------------------------------------------
# 📊 Medido em 08/09/2026 (`worker.py`, `if result.status == "needs_human"`): o
# worker so fotografava a tela quando PARAVA. Um acionamento que dava certo —
# com numero de atendimento, o desfecho que mais importa provar — nao deixava
# imagem nenhuma. Quem quisesse conferir o que o robo fez tinha o texto que o
# proprio robo escreveu, e mais nada.
#
# 🔴 E a foto da tela do PROTOCOLO nao pode esperar o fim: ela e a unica tela
# que prova que o pedido existe na seguradora, e o passo seguinte (escolher
# loja, agendar) NAVEGA para longe dela. Fotografar depois e fotografar outra
# coisa.
CHAVE_PROVA = "prova"
TETO_DA_FOTO_SEG = 15.0


def _agora_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


async def capturar_prova(page, evidence: Dict[str, Any], motivo: str,
                         teto_seg: float = TETO_DA_FOTO_SEG) -> Optional[Dict[str, Any]]:
    """Fotografa a tela ATUAL e guarda a foto em `evidence["prova"]`.

    Tenta a tela INTEIRA primeiro (`full_page`) e cai para o visivel quando o
    Playwright recusa — uma tela de portal cabe em duas dobras, e a prova que
    corta o rodape corta justamente o botao que faltava clicar.

    Guarda a foto em base64 aqui, e nao no cofre: esta funcao roda no meio de um
    laco que pode morrer no passo seguinte, e uma chamada de rede a mais e uma
    forma a mais de perder a prova. Quem sobe ao bucket e o worker, no fim, com
    `_materializar_provas` — e o base64 e o fallback caso ele nao consiga.

    ⚠️ NUNCA levanta excecao e NUNCA trava: um acionamento nao pode morrer por
    causa da fotografia dele.
    """
    if page is None or not isinstance(evidence, dict):
        return None
    bruto = None
    inteira = False
    for full_page in (True, False):
        try:
            bruto = await asyncio.wait_for(
                page.screenshot(type="jpeg", quality=60, full_page=full_page), teto_seg)
        except Exception:  # noqa: BLE001
            bruto = None
            continue
        if bruto:
            inteira = full_page
            break
    if not bruto:
        return None
    entrada = {
        "motivo": str(motivo or "desfecho")[:40],
        "quando": _agora_utc(),
        "tela_inteira": bool(inteira),
        "b64": base64.b64encode(bruto).decode("ascii"),
    }
    provas = evidence.setdefault(CHAVE_PROVA, [])
    if isinstance(provas, list):
        provas.append(entrada)
    return entrada


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
          // SPEC-127 P2: as OPCOES vem junto (o menu mora dentro do md-select ate
          // a 1a abertura e depois em `aria-owns`) — e e com elas que o CODIGO
          // decide o que e fato e a parada mostra a lista REAL ao segurado.
          // `value` e o do `md-select-value`: o textContent do md-select inteiro
          // trazia o menu junto ("Selecione uma opcao CHOQUE TERMICO ...").
          const mdOpcoes = m => { const own = m.getAttribute('aria-owns');
                const c = m.querySelector('.md-select-menu-container') || (own && document.getElementById(own));
                return c ? [...c.querySelectorAll('md-option')].map(o => clean(o.textContent))
                             .filter(t => t && !/^selecione/i.test(t)) : []; };
          const mdValor = m => { const v = m.querySelector('md-select-value');
                // vazio: o md-select-value mostra o PLACEHOLDER (o proprio rotulo)
                if (/ng-empty/.test(m.className) || (v && /md-select-placeholder/.test(v.className))) return '';
                const t = clean(v ? v.textContent : '');
                return /^selecione/i.test(t) ? '' : t; };
          const mdselects = [...document.querySelectorAll('md-select')].filter(vis)
            .map(m => ({id:m.id, name:m.getAttribute('name')||'', label:mdLabel(m),
                        value:mdValor(m), options:mdOpcoes(m), vazio:/ng-empty/.test(m.className),
                        empty_required: /ng-invalid-required|ng-empty/.test(m.className) && /ng-required|ng-invalid/.test(m.className)}));
          const buttons = [...document.querySelectorAll('button')].filter(vis)
            .map(b => ({text:clean(b.textContent), disabled:!!b.disabled})).filter(b=>b.text);
          const radios = [...document.querySelectorAll('input[type=radio],input[type=checkbox]')].filter(vis)
            .map(r => ({name:r.name, checked:r.checked, label:lbl(r), value:r.value||''}));
          // As perguntas do 80% (md-radio-group): a pergunta, as opcoes REAIS e se ja
          // foi respondida. Antes elas so existiam no `text` — o codigo nao tinha
          // como responder com o que o segurado disse.
          const questoes = [...document.querySelectorAll('md-radio-group')].filter(vis).map(g => {
                const item = g.closest('.aw-question-item') || g.parentElement;
                const l = item && item.querySelector('label');
                const bts = [...g.querySelectorAll('md-radio-button')];
                const marcada = bts.find(b => /md-checked/.test(b.className));
                return {id:g.id||'', pergunta:clean(l ? l.textContent : ''),
                        opcoes:bts.map(b => clean(b.getAttribute('aria-label') || b.textContent)).filter(Boolean),
                        respondida:!!marcada,
                        escolhida:marcada ? clean(marcada.getAttribute('aria-label') || marcada.textContent) : ''}; });
          // Resumo do que BLOQUEIA o Avancar: campos obrigatorios ainda vazios.
          const pending_required = [
            ...inputs.filter(e => e.empty_required).map(e => ({tipo:'input', label:e.label||e.id||e.name})),
            ...mdselects.filter(m => m.empty_required).map(m => ({tipo:'select', label:m.label||m.name||m.id})),
          ];
          const h = document.querySelector('h1,h2,h3,.titulo,.title');
          return {url:location.href, heading:clean(h?h.textContent:''),
                  inputs, selects, mdselects, buttons, radios, questoes, pending_required,
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


# 🔴 SPEC-073 F1/F2 — este override JA MANDOU "escolha a 1a opcao valida".
#
# A intencao era boa e o efeito, nao: o cerebro tende a "perguntar por educacao"
# em select/radio que ele conseguiria responder, e o override existia para
# empurra-lo a agir. So que a licenca de pegar a primeira opcao nao distingue
# "campo de formato, tanto faz" de "lado do vidro quebrado" — e num portal de
# vidros a primeira opcao da lista de LADO e `Motorista`. Escolher por POSICAO
# um campo cujo valor errado manda o vidraceiro trocar a porta errada nao e
# antitravamento, e chute com aparencia de decisao.
#
# O empurrao contra a pergunta desnecessaria FICA. A licenca de chutar SAI.
# Quando nao ha base, o desfecho correto e dizer QUAL dado falta -- e isso e
# util, porque vira a pergunta que o atendente faz ao segurado.
_FORCE_CHOOSE = (
    " ATENCAO: nao use ask_human para algo que a TELA ja responde ou que os "
    "dados fornecidos ja contem. Se houver relato/dado que case com uma opcao "
    "REAL da lista, escolha essa opcao e devolva fill/select/check/click. "
    "PROIBIDO escolher por posicao ('a primeira', 'a mais provavel') qualquer "
    "campo de peca, causa, lado, posicao, tamanho, cobertura, local, loja, "
    "data, horario ou pagamento. Sem base real para escolher, devolva "
    "ask_human dizendo EXATAMENTE qual dado falta — essa frase vira a pergunta "
    "que o atendente faz ao segurado."
)


# ---------------------------------------------------------------------------
# 🔴 SPEC-127 P2 — o PROVEDOR recebe só o que a TELA pede
# ---------------------------------------------------------------------------
# 📊 BLOCO 0 item 6: o `collected` inteiro ia CRU ao provedor do modelo —
# CPF do titular, nome, apólice, chassi, CEP, endereço, telefone e e-mail do
# segurado — em TODA chamada, por desenho ("humanos preenchem sem máscara").
# E a `tela` ia com a URL da SPA, cujo segmento `#/<seg>/passoN/<x>` é o
# `token_autorizacao` da sessão (📊 4/4 HAR Yelum, `b0_har_token2.py`).
#
# Depois da contenção o modelo só NAVEGA: o que é fato o código escreve. Então
# ele recebe a peça (contexto, não é PII) e, de dado pessoal, SÓ o valor que um
# campo VAZIO desta tela pede — nunca o que a tela não exige.
_URL_TOKEN = re.compile(r"[A-Za-z0-9_\-]{16,}")


def _url_sem_token(url: Any) -> str:
    """A URL sem segmento que possa ser token/sessão (≥ 16 caracteres seguidos)."""
    return _URL_TOKEN.sub("<token>", str(url or ""))


# (caminho no `collected`, pistas do campo que o pede, pistas que desqualificam)
_DADOS_QUE_A_TELA_PEDE = (
    (("solicitante", "nome"), ("nome",), ("segurado",)),
    (("solicitante", "email"), ("email", "e mail"), ()),
    (("solicitante", "telefone"), ("telefone",), ("tipo",)),
    (("solicitante", "cpf_cnpj"), ("cpf cnpj solicitante", "cpf ou cnpj"), ("inserir cpf",)),
    (("segurado", "chassi"), ("chassi",), ()),
    (("segurado", "ultimos_6_chassi"), ("chassi",), ()),
    (("segurado", "veiculo"), ("veiculo", "modelo"), ()),
    (("placa",), ("placa",), ()),
)


def _campos_vazios_da_tela(state: Dict[str, Any]) -> List[str]:
    from portal_worker import perception as _P

    vazios = []
    for c in (state or {}).get("inputs") or []:
        if isinstance(c, dict) and not str(c.get("value") or "").strip():
            vazios.append(_P._palavras_de(" ".join(str(c.get(k) or "") for k in
                                                   ("id", "name", "placeholder", "label"))))
    for c in list((state or {}).get("mdselects") or []) + list((state or {}).get("selects") or []):
        if isinstance(c, dict) and not str(c.get("value") or "").strip():
            vazios.append(_P._palavras_de(" ".join(str(c.get(k) or "") for k in
                                                   ("id", "name", "label"))))
    return vazios


def dados_para_o_modelo(collected: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    """PURO: o recorte do `collected` que vai ao PROVEDOR do modelo nesta tela."""
    collected = collected or {}
    saida: Dict[str, Any] = {}
    peca = ((collected.get("dano") or {}).get("peca") or "")
    if str(peca).strip():
        saida["dano"] = {"peca": str(peca)}
    vazios = _campos_vazios_da_tela(state)
    for caminho, pistas, proibidas in _DADOS_QUE_A_TELA_PEDE:
        if not any(any(f" {p} " in v for p in pistas) and not any(f" {x} " in v for x in proibidas)
                   for v in vazios):
            continue
        valor: Any = collected
        for k in caminho:
            valor = valor.get(k) if isinstance(valor, dict) else None
        if not str(valor or "").strip():
            continue
        alvo = saida
        for k in caminho[:-1]:
            alvo = alvo.setdefault(k, {})
        alvo[caminho[-1]] = valor
    return saida


def estado_para_o_modelo(state: Dict[str, Any]) -> Dict[str, Any]:
    """PURO: a tela sem PII — valor digitado vira "[preenchido]", o texto passa
    pelo redator único e a URL perde o token da sessão."""
    s = dict(state or {})
    s["url"] = _url_sem_token(s.get("url"))
    s["text"] = _RED.redigir_texto(s.get("text") or "")
    s["inputs"] = [{**c, "value": "[preenchido]" if str(c.get("value") or "").strip() else ""}
                   for c in (s.get("inputs") or []) if isinstance(c, dict)]
    return s


def _recorte_json(texto: str) -> str:
    """O primeiro objeto JSON do texto (modelos embrulham em cerca de codigo)."""
    t = str(texto or "").strip()
    i, j = t.find("{"), t.rfind("}")
    return t[i: j + 1] if i != -1 and j > i else t


async def decide_next_action(state: Dict[str, Any], goal: str, collected: Dict[str, Any],
                             history: List[Dict[str, Any]], force: bool = False, *,
                             chamar_modelo: Optional[Callable[[Dict[str, Any]], Any]] = None,
                             rota: Any = None) -> Dict[str, Any]:
    """Chama o cerebro (LLM) para decidir a proxima acao. Fail-safe -> ask_human.

    📊 O padrao era `gpt-4o-mini` — um modelo pequeno conduzindo uma tarefa
    agentica de 22 passos com 1.500 caracteres de instrucao. A autopsia dos 39
    acionamentos mostra os tres sintomas classicos de instrucao nao seguida:
    perguntou o que estava no payload (4x), repetiu acao que ja tinha dado
    certo (7x) e escreveu "Santa Catarina" onde o prompt manda a SIGLA.

    SPEC-116 U9: o modelo e o da ROTA `portal_decisao` (Model Router, mesmo
    catalogo do produto); `PORTAL_VISION_MODEL` fica IGNORADO. Falha do
    provedor NAO troca de modelo: vira `ask_human` com o MOTIVO, e o laco segue
    o caminho de `needs_human` que ja existe. O uso vai para o ledger
    (`token_usage_logs`, service_type='portal', company_id do job).

    `chamar_modelo` — ponto de injecao da BANCADA: recebe o pedido montado
    ({papel, provider, api_surface, model, url, corpo}) e devolve a resposta
    crua do provedor (Chat Completions, Messages ou Responses). Sem ele, o
    pedido sai por `httpx.AsyncClient.post` — que a bancada tambem sabe desviar.

    `rota` — (SPEC-116 F6) um `ModeloDoPortal` INJETADO pela bancada, para que
    o corpo do pedido seja o do provedor do BRACO medido. Sem ele (produção),
    nada muda: o modelo é o da rota `portal_decisao`.
    """
    system = _SYSTEM + (_FORCE_CHOOSE if force else "")
    user = json.dumps({"objetivo": goal, "dados_segurado_corretora": collected, "tela": state,
                       "acoes_ja_feitas": history[-8:]}, ensure_ascii=False)
    job = _JOB_EM_CURSO.get() or {}
    try:
        resposta = await _MODELO.decidir(system, user, company_id=job.get("company_id"),
                                         job_id=job.get("job_id"), chamar_modelo=chamar_modelo,
                                         rota=rota)
        return parse_action(json.loads(_recorte_json(resposta["texto"])))
    except _MODELO.ModeloDoPortalIndisponivel as e:
        return {"action": "ask_human", "value": f"cerebro do portal indisponivel: {e}"[:220],
                "reason": "llm error"}
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


def decidir_opcao(valor: Any, opcoes: List[str], rotulo: Any = "") -> Optional[str]:
    """PURO: o ÚNICO placar de opção do DOM — atributo do 80% (`explicar_especifico`)
    e, quando a lista não é dele, peça (`explicar_match`). `None` = sem confiança.
    O `_apply_mdselect` e a contenção (SPEC-127 P2) decidem por aqui."""
    esp = explicar_especifico(str(valor or ""), list(opcoes or []), str(rotulo or ""))
    if esp["dominio"] != "nenhum":
        return esp["escolha"]
    return explicar_match(str(valor or ""), list(opcoes or []))["escolha"]


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
            # (as MESMAS duas funções puras de `decidir_opcao`; as linhas ficam
            # literais aqui porque [R6]/[7.4i] as leem para provar o placar único)
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
    # SPEC-127 P2: as respostas do 80% são `md-radio-button` (📊 HTML `TELA 80%`,
    # `3 TELA DE QUAL VIDROO`), que não são `<label>`. IGUALDADE primeiro — "SIM"
    # contido em outra resposta não pode marcar a errada — e a resposta já dada
    # (desabilitada) nunca é clicada de novo.
    candidatos = []
    for lab in await page.query_selector_all(
            "md-radio-button, [role=radio], label, .radio, .mat-radio-label"):
        try:
            if not await lab.is_visible():
                continue
            if str(await lab.get_attribute("aria-disabled") or "").lower() == "true":
                continue
            texto = _norm(await lab.get_attribute("aria-label") or "") or _norm(await lab.inner_text())
            candidatos.append((texto, lab))
        except Exception:  # noqa: BLE001
            continue
    for igual in (True, False):
        for texto, lab in candidatos:
            if want and ((texto == want) if igual else (want in texto)):
                try:
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


async def _pick_autocomplete_igual(page, value: str) -> Tuple[Optional[bool], List[str]]:
    """🔴 SPEC-127 P2 — a sugestão do autocomplete por IGUALDADE, e só.

    `_pick_autocomplete` cai em "começa com → contém → a PRIMEIRA sugestão": 📊
    o red team da 001.10 mediu o que isso faz com a lista real de SC —
    "Curitiba" → CURITIBANOS, "Palmas" → PALMA SOLA, "Santo Amaro" → SANTO
    AMARO DA IMPERATRIZ. É a mesma régua de `vidros_apifirst.casar_igual` e de
    `destravador.mesmo_lugar` (o worker não importa `app/`): nome igual depois
    de normalizar, nunca prefixo, nunca a primeira da lista.

    `(True, [])` clicou · `(False, sugestoes)` havia lista e nenhuma é IGUAL ·
    `(None, [])` não apareceu lista nenhuma (input comum)."""
    # O navegador só LÊ as sugestões; quem DECIDE é o Python (`sugestao_igual`),
    # testável offline sobre a lista real — e só então o clique, pelo ÍNDICE.
    _SUGESTOES = ("[...document.querySelectorAll('.md-autocomplete-suggestions li, "
                  "md-autocomplete-suggestions li, li.md-autocomplete-suggestion, "
                  "ul.md-autocomplete-suggestions li')]"
                  ".filter(el => !!(el.offsetParent || el.getClientRects().length))"
                  ".filter(o => !/nenhum|nao encontr|n\\u00e3o encontr|sem resultado|no results|nenhuma op/i"
                  ".test(o.textContent||''))")
    for _ in range(4):
        await page.wait_for_timeout(450)
        try:
            textos = await page.evaluate(
                "() => " + _SUGESTOES + ".map(o => (o.textContent||'').replace(/\\s+/g,' ').trim()).slice(0, 20)")
        except Exception:  # noqa: BLE001
            return False, []
        textos = [str(t) for t in (textos or []) if str(t).strip()]
        if not textos:
            continue
        i = sugestao_igual(value, textos)
        if i is None:
            return False, textos
        try:
            await page.evaluate("(i) => { const lis = " + _SUGESTOES + "; if (lis[i]) lis[i].click(); }", i)
        except Exception:  # noqa: BLE001
            return False, textos
        return True, []
    return None, []


def sugestao_igual(valor: Any, sugestoes: List[str]) -> Optional[int]:
    """PURO: o índice da ÚNICA sugestão IGUAL ao valor (normalizado). Prefixo,
    "contém" e "a primeira" NÃO contam — 📊 "Curitiba" → CURITIBANOS."""
    alvo = _norm(valor)
    iguais = [i for i, s in enumerate(sugestoes or []) if alvo and _norm(s) == alvo]
    return iguais[0] if len(iguais) == 1 else None


async def apply_action(page, action: Dict[str, Any]) -> str:
    a = action.get("action")
    target = action.get("target") or ""
    value = action.get("value") or ""
    if a == "fill" and action.get("so_igual"):
        # Caminho do CÓDIGO (fato do caso) em autocomplete de LUGAR: só a
        # sugestão IGUAL. Nunca chega aqui uma ação de modelo.
        el = await _find_input(page, target)
        if not el:
            return "fill_notfound"
        await el.fill(str(value))
        try:
            await el.evaluate("e => e.dispatchEvent(new Event('input',{bubbles:true}))")
        except Exception:  # noqa: BLE001
            pass
        clicou, sugestoes = await _pick_autocomplete_igual(page, value)
        if clicou:
            return "filled_autocomplete"
        if clicou is False:
            try:
                await el.fill("")
            except Exception:  # noqa: BLE001
                pass
            return "fill_sem_igual=" + " | ".join(s[:60] for s in sugestoes)
        return "filled"
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
        "url": _url_sem_token(state.get("url")),
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
# Nome da corretora, e-mail, CNPJ, telefone e relacao (`Corretor`) tem **um
# unico valor certo, sabido antes de a tela abrir**. Mandar um modelo "decidir"
# preenche-los cria tres riscos de graca: ele pergunta o que ja sabe, erra o
# formato, ou gasta passos do teto.
#
# 🔴 SPEC-127 P2 — estado, cidade e CEP NAO tem "um valor unico": esta linha
# dizia que tinham, e era a premissa errada. A tela pergunta "Selecione o
# estado ONDE DESEJA SER ATENDIDO" (📊 HTML `TELA 50% CIDADE CEP`, `TELA 4`,
# `2 LANTERNA MALA`) — a cidade do SERVICO, que mora em `local.cidade_servico`
# (`portal_params`, P0-5). `local.cidade` e onde ele MORA (cadastro InfoCap).
# Quem mora em Palhoça e quer o vidro em Joinville tinha o pedido aberto em
# Palhoça, sem parada nenhuma. Agora: a do servico, ou PARADA — nunca o cadastro.
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


def _mesmo_lugar(cidade_a: Any, uf_a: Any, cidade_b: Any, uf_b: Any) -> bool:
    """Nome IGUAL depois de normalizar, e UF igual (ou ausente de um lado).

    🔴 Igualdade, nunca prefixo: "Curitiba" × "Curitibanos" NÃO é o mesmo lugar.
    É a régua de `destravador.mesmo_lugar` (P-124-14, SPEC-126) — copiada em
    três linhas porque o worker não importa `app/` (Dockerfile do portal-worker
    copia só `portal_worker/`)."""
    na, nb = _norm(cidade_a), _norm(cidade_b)
    ua, ub = _norm(uf_a), _norm(uf_b)
    return bool(na) and na == nb and (not ua or not ub or ua == ub)


def local_do_servico(collected: Dict[str, Any]) -> Dict[str, str]:
    """PURO: estado, cidade e CEP de ONDE O SERVIÇO É FEITO. `{}` se o pedido
    não traz a cidade do serviço — e aí quem decide é a PARADA, nunca o cadastro.

    O CEP do cadastro só vai quando a cidade do serviço É a do cadastro: o CEP
    de Palhoça numa busca em Joinville acha a loja errada e oferece domicílio
    no endereço errado. Sem ele o campo fica vazio (📊 a tela o marca
    "CEP (opcional)")."""
    local = (collected or {}).get("local") or {}
    if not isinstance(local, dict):
        return {}
    cs = local.get("cidade_servico") or {}
    if not isinstance(cs, dict):
        return {}
    cidade = str(cs.get("cidade") or "").strip()
    uf = str(cs.get("uf") or "").strip().upper()
    if not cidade:
        return {}
    saida = {"estado": uf, "cidade": cidade}
    cep = str(local.get("cep") or "").strip()
    if cep and _mesmo_lugar(cidade, uf, local.get("cidade"), local.get("estado")):
        saida["cep"] = cep
    return saida


def fatos_da_tela(state: Dict[str, Any], collected: Dict[str, Any]) -> List[Dict[str, str]]:
    """PURO: quais campos DESTA tela tem valor conhecido e ainda estao vazios.

    Devolve [{'alvo', 'valor', 'de'}]. Vazio quando nao ha nada obvio a fazer —
    e ai o cerebro trabalha, que e para o que ele serve.

    🔴 O lugar vem de `local_do_servico` (SPEC-127 P2): estado e cidade do
    SERVIÇO, marcados `so_igual` — o autocomplete só aceita a sugestão IGUAL.
    """
    state = state or {}
    solicitante = (collected or {}).get("solicitante") or {}
    local = local_do_servico(collected)
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
            fato = {"alvo": str(c.get("id") or c.get("name") or c.get("label") or ""),
                    "valor": valor, "de": chave}
            if origem is local and chave in ("estado", "cidade"):
                fato["so_igual"] = True
            saida.append(fato)
    return saida


async def preencher_o_que_e_fato(page, state: Dict[str, Any], collected: Dict[str, Any],
                                 falhas: Optional[List[Dict[str, Any]]] = None) -> List[str]:
    """Preenche os campos de valor conhecido. Devolve o que foi preenchido.

    `falhas` (SPEC-127 P2) recebe o lugar que o portal NÃO tem igual — a cidade
    do serviço que não casa com nenhuma sugestão vira `cidade_ambigua` com as
    sugestões REAIS, e não a primeira da lista."""
    feitos: List[str] = []
    for f in fatos_da_tela(state, collected):
        if not f["alvo"]:
            continue
        try:
            r = await apply_action(page, {"action": "fill", "target": f["alvo"], "value": f["valor"],
                                          "so_igual": bool(f.get("so_igual"))})
        except Exception:  # noqa: BLE001
            continue
        if str(r).startswith("fill_sem_igual") and falhas is not None:
            falhas.append({"slot": "cidade_servico", "campo": f["alvo"], "valor_do_caso": f["de"],
                           "opcoes": [o.strip() for o in str(r).split("=", 1)[1].split("|")
                                      if o.strip()]})
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


# ---------------------------------------------------------------------------
# 🔴 SPEC-127 P2 + a CONTENÇÃO do P6 (D-127-B) — O DOM PARA DE ERRAR CALADO
# ---------------------------------------------------------------------------
# Antes de o modelo `portal_decisao` ver a tela, o CÓDIGO olha cada campo
# crítico vazio (peça, causa, perímetro, descrição, a pergunta do 80%, a
# cidade) e cada botão de decisão do segurado (reparo, oferta, custo):
#
#     é FATO do caso? ........ o código escreve, pelo placar ÚNICO
#                              (`decidir_opcao`, `escolher_resposta` do 80%)
#     não é? ................. PARADA estruturada `responder:<slot>` com as
#                              opções REAIS da tela — volta ao segurado/
#                              destravador, nunca ao modelo
#
# Os `stage` são os MESMOS do API-first (`vidros_estado.ETAPA_DA_PARADA`,
# `destravador.CLASSE_DA_PARADA_DO_PORTAL`) quando o significado é o mesmo:
# `peca_ambigua`, `motivo_ambiguo`, `cidade_ambigua`, `questionario_incompleto`,
# `decidir_reparo`. Novos, só onde o DOM vê o que o API-first barra antes:
# `falta_cidade_servico`, `perimetro_desconhecido`, `descricao_curta`,
# `decidir_oferta`, `cobertura_nao_marcada`.
#
# O que SOBRA para o modelo é NAVEGAÇÃO: Avançar/Voltar, o campo de formato
# (tipo de telefone) e o que a contenção não reconhece como crítico — e mesmo
# assim o validador (`perception.recusa_da_contencao`) recusa campo crítico e
# botão NUNCA que ele proponha.
MAX_RODADAS_DA_CONTENCAO = 10
_MINIMO_DA_DESCRICAO = 30  # 📊 a tela: "Descreva como aconteceu (mín. 30 caracteres)"

_PARADA_DO_SLOT = {
    "peca": ("peca_ambigua", "responder:peca"),
    "pecas_lataria": ("peca_de_lataria_ambigua", "responder:pecas_lataria"),
    "como": ("motivo_ambiguo", "responder:como"),
    "onde": ("perimetro_desconhecido", "responder:onde"),
    "descricao": ("descricao_curta", "responder:descricao"),
    "pergunta": ("questionario_incompleto", "responder:pergunta"),
    "cidade_servico": ("cidade_ambigua", "responder:cidade_servico"),
    "aceita_reparo": ("decidir_reparo", "responder:aceita_reparo"),
    "oferta": ("decidir_oferta", "responder:oferta"),
    "cobertura": ("cobertura_nao_marcada", "reler"),
}


def _parada(slot: str, *, campo: str = "", pergunta: str = "", opcoes: Optional[List[str]] = None,
            mensagem: str = "", stage: str = "", nunca: str = "") -> Dict[str, Any]:
    st, acao = _PARADA_DO_SLOT.get(slot, ("contencao", "reler"))
    return {"stage": stage or st, "acao_esperada": acao, "slot": slot, "campo": str(campo or "")[:120],
            "pergunta": str(pergunta or "")[:200],
            "opcoes": [str(o)[:80] for o in (opcoes or []) if str(o).strip()][:30],
            "mensagem": mensagem, "nunca": nunca}


def _sim_ou_nao(texto: Any) -> str:
    t = _norm(texto)
    if t in ("sim", "s", "aceito", "true", "quero", "pode"):
        return "sim"
    if t in ("nao", "n", "recuso", "false"):
        return "nao"
    return ""


def _plano_do_aceite(botoes_de_custo: List[str], especificos: Dict[str, Any]) -> Dict[str, Any]:
    """A tela pede uma decisão de CUSTO do segurado (reparo × troca, oferta).

    📊 HTML `YELUM PARA BRISA/TELA 5`: "Sim, quero tentar o reparo" ·
    "Não, prefiro seguir com a troca". O código só aperta o botão que o
    SEGURADO escolheu (`especificos.aceita_reparo`, a mesma chave que o API-first
    lê em `_fase_materializar`); sem a resposta dele, PARADA com os dois botões."""
    from portal_worker import perception as _P

    reparo =[b for b in botoes_de_custo if " reparo " in _P._palavras_de(b) or " troca " in _P._palavras_de(b)]
    if reparo and len(reparo) == len(botoes_de_custo):
        dito = _sim_ou_nao((especificos or {}).get("aceita_reparo"))
        if dito == "sim":
            alvo = [b for b in reparo if " reparo " in _P._palavras_de(b) and " troca " not in _P._palavras_de(b)]
        elif dito == "nao":
            alvo = [b for b in reparo if " troca " in _P._palavras_de(b)]
        else:
            alvo = []
        if len(alvo) == 1:
            return {"acoes": [{"action": "click", "target": alvo[0], "slot": "aceita_reparo"}],
                    "parada": None}
        return {"acoes": [], "parada": _parada(
            "aceita_reparo", pergunta="O portal ofereceu REPARO em vez de troca",
            opcoes=reparo, nunca="aceite_de_custo",
            mensagem=("o portal ofereceu REPARO em vez de troca, e essa escolha e do segurado. "
                      "Nada foi escolhido por mim."))}
    # Oferta (polimento de farol, ADAS, cola rápida) ou custo: o DOM não aceita
    # oferta nenhuma — nem com a resposta na mão (o botão de "não" de uma oferta
    # não é identificável com segurança). Quem decide é o segurado, pela parada.
    return {"acoes": [], "parada": _parada(
        "oferta", pergunta="O portal ofereceu um servico/custo adicional",
        opcoes=botoes_de_custo, nunca="aceite_de_custo",
        mensagem="o portal ofereceu um servico ou custo adicional; aceitar e decisao do segurado.")}


def _responder_pergunta_do_80(questao: Dict[str, Any], collected: Dict[str, Any]) -> Optional[str]:
    """A resposta do SEGURADO para esta pergunta do 80%, pelo MESMO casador do
    API-first (`vidros_questionario.escolher_resposta`) — que já sabe que
    "Não sabe" só vale quando ELE disse, e só nesta pergunta."""
    from portal_worker.journeys import vidros_questionario as QZ

    opcoes = [str(o) for o in (questao.get("opcoes") or []) if str(o).strip()]
    if not opcoes:
        return None
    pergunta = QZ.Pergunta(codigo=0, texto=str(questao.get("pergunta") or ""), tipo="",
                           opcoes=[{"DescricaoResposta": o, "CodigoResposta": i + 1}
                                   for i, o in enumerate(opcoes)])
    dano = (collected or {}).get("dano") or {}
    r = QZ.escolher_resposta(pergunta, respostas_do_segurado=dict((collected or {}).get("especificos") or {}),
                             relato=str(dano.get("descricao") or ""))
    return r.get("texto") if r.get("situacao") == "ok" and r.get("texto") else None


def _opcao_do_perimetro(onde: Any, opcoes: List[str]) -> Optional[str]:
    """`urbano`/`rodoviario` (o enum de `portal_params.normalizar_perimetro`) →
    a opção que COMEÇA por essa palavra. 📊 Opções reais (HTML `TELA 3`,
    `TELA 50% LATARIA`): "Urbano (Cidade)" · "Rodoviário" · "Não Sabe". Nunca
    "Não Sabe"; duas candidatas = nenhuma."""
    t = _norm(onde)
    if t in ("u",):
        t = "urbano"
    if t in ("r",):
        t = "rodoviario"
    if t not in ("urbano", "rodoviario"):
        return None
    achadas = [o for o in opcoes if _norm(o).split(" ")[0:1] == [t]]
    return achadas[0] if len(achadas) == 1 else None


def _decidir_campo(slot: str, campo: Dict[str, Any], collected: Dict[str, Any],
                   tipo: str) -> Dict[str, Any]:
    """PURO: um campo crítico VAZIO → `{"acao": {...}}` (fato) ou `{"parada": {...}}`."""
    dano = (collected or {}).get("dano") or {}
    rotulo = str(campo.get("label") or campo.get("name") or campo.get("id") or "")
    alvo = str(campo.get("name") or campo.get("id") or campo.get("label") or "")
    opcoes = [str(o) for o in (campo.get("options") or []) if str(o).strip()
              and "selecione" not in _norm(o)]

    def _escolhe(valor: Any, decidida: Optional[str], slot_da_parada: str) -> Dict[str, Any]:
        if decidida:
            return {"acao": {"action": "select", "target": alvo or rotulo, "value": decidida, "slot": slot}}
        return {"parada": _parada(slot_da_parada, campo=rotulo, pergunta=rotulo, opcoes=opcoes,
                                  mensagem=(f"o portal pergunta '{rotulo}' e o que o segurado disse "
                                            f"({str(valor or 'nada')[:60]}) nao casa com UMA opcao."))}

    if slot == "peca":
        if " servicoitens " in f" {_norm(campo.get('name'))} " or "peca danificada" == _norm(rotulo):
            pecas = [p for p in (dano.get("pecas_lataria") or []) if str(p).strip()]
            # 🔴 lataria multi-peça no DOM: uma peça só. Mais de uma = parada (o
            # API-first faz a lista; o DOM é a exceção e não adivinha a ordem).
            if len(pecas) != 1:
                return {"parada": _parada("pecas_lataria", campo=rotulo, pergunta=rotulo, opcoes=opcoes,
                                          mensagem="a lataria tem mais de uma peca (ou nenhuma) e o DOM nao escolhe.")}
            valor = pecas[0]
            return _escolhe(valor, decidir_opcao(valor, opcoes, rotulo) if opcoes else None, "pecas_lataria")
        valor = dano.get("peca")
        return _escolhe(valor, decidir_opcao(valor, opcoes, rotulo) if (opcoes and valor) else None, "peca")
    if slot == "como":
        valor = dano.get("como")
        # A causa vem CANÔNICA (`portal_params.causa_conhecida`): igualdade e só.
        iguais = [o for o in opcoes if valor and _norm(o) == _norm(valor)]
        return _escolhe(valor, iguais[0] if len(iguais) == 1 else None, "como")
    if slot == "onde":
        valor = dano.get("onde")
        return _escolhe(valor, _opcao_do_perimetro(valor, opcoes), "onde")
    if slot == "descricao":
        texto = str(dano.get("descricao") or "").strip()
        if len(texto) >= _MINIMO_DA_DESCRICAO:
            return {"acao": {"action": "fill", "target": alvo or rotulo, "value": texto, "slot": slot}}
        return {"parada": _parada("descricao", campo=rotulo, pergunta=rotulo,
                                  mensagem=f"o portal exige descricao com {_MINIMO_DA_DESCRICAO}+ caracteres.")}
    if slot == "cobertura":
        return {"parada": _parada("cobertura", campo=rotulo, pergunta="Selecione a cobertura",
                                  opcoes=opcoes, mensagem="a tela pede a cobertura e ela nao foi marcada no passo 1.")}
    # Qualquer outro slot crítico num tipo de campo inesperado: o DOM não decide.
    return {"parada": _parada(slot, campo=rotulo, pergunta=rotulo, opcoes=opcoes,
                              mensagem=f"campo critico '{rotulo}' sem fato do caso.")}


def plano_de_contencao(state: Dict[str, Any], collected: Dict[str, Any]) -> Dict[str, Any]:
    """PURO: o que o CÓDIGO faz nesta tela antes de o modelo ver qualquer coisa.

    `{"acoes": [...], "parada": None}` — escrever o que é fato (pode ser `[]`);
    `{"acoes": [], "parada": {...}}` — parar com a pergunta e as opções reais."""
    from portal_worker import perception as _P

    state = state or {}
    collected = collected or {}
    especificos = collected.get("especificos") or {}
    especificos = especificos if isinstance(especificos, dict) else {}

    # ① decisão de CUSTO do segurado (reparo, oferta) — antes de tudo
    botoes = [str(b.get("text") or "") for b in (state.get("buttons") or [])
              if isinstance(b, dict) and not b.get("disabled")]
    de_custo = list(dict.fromkeys(b for b in botoes if _P.familia_nunca_sozinho(b) == "aceite_de_custo"))
    if de_custo:
        return _plano_do_aceite(de_custo, especificos)

    acoes: List[Dict[str, Any]] = []
    # ② a pergunta do 80% ainda aberta (uma por vez: a SPA revela a seguinte)
    for q in state.get("questoes") or []:
        if not isinstance(q, dict) or q.get("respondida") or not q.get("opcoes"):
            continue
        resposta = _responder_pergunta_do_80(q, collected)
        if not resposta:
            return {"acoes": [], "parada": _parada(
                "pergunta", campo=q.get("id") or "", pergunta=q.get("pergunta") or "",
                opcoes=q.get("opcoes") or [],
                mensagem=f"o portal perguntou '{q.get('pergunta')}' e o segurado ainda nao respondeu.")}
        acoes.append({"action": "check", "target": str(q.get("pergunta") or ""), "value": resposta,
                      "slot": "pergunta"})
        return {"acoes": acoes, "parada": None}

    # ③ a cobertura da Porto (rádio) — é do passo 1, onde o CÓDIGO a marca
    cobertura = [r for r in (state.get("radios") or [])
                 if isinstance(r, dict) and _P.slot_do_campo(r) == "cobertura"]
    if cobertura and not any(r.get("checked") for r in cobertura):
        return {"acoes": [], "parada": _parada(
            "cobertura", campo="tipoAtendimento", pergunta="Selecione a cobertura",
            opcoes=[str(r.get("label") or r.get("value") or "") for r in cobertura],
            mensagem="a tela pede a cobertura e ela nao foi marcada no passo 1.")}

    # ④ os campos críticos VAZIOS
    lugar = local_do_servico(collected)
    # 📊 HTML `TELA 3`: cada md-select carrega um `<select>` nativo ESPELHO com o
    # mesmo `name` (o Angular Material o esconde). O campo é o md-select.
    espelhos = {_norm(m.get("name")) for m in (state.get("mdselects") or [])
                if isinstance(m, dict) and m.get("name")}
    for chave, tipo in (("mdselects", "mdselect"), ("selects", "select"), ("inputs", "input")):
        for campo in state.get(chave) or []:
            if not isinstance(campo, dict):
                continue
            if tipo == "select" and _norm(campo.get("name")) in espelhos:
                continue
            if tipo == "input" and str(campo.get("type") or "").lower() in ("radio", "checkbox", "hidden"):
                continue
            if str(campo.get("value") or "").strip():
                continue
            slot = _P.slot_do_campo(campo)
            if not slot or slot == "pergunta":
                continue
            if slot == "cidade_servico":
                ident = _P._palavras_de(_identidade_do_campo(campo))
                if " cep " in ident:
                    continue  # opcional; só vai quando é o MESMO lugar (`local_do_servico`)
                if not lugar:
                    return {"acoes": [], "parada": _parada(
                        "cidade_servico", stage="falta_cidade_servico", campo=campo.get("label") or "",
                        pergunta="Em que cidade o servico deve ser feito?",
                        mensagem=("a tela pergunta ONDE o servico sera feito e o pedido nao traz a "
                                  "cidade do servico — nunca uso a cidade do cadastro."))}
                return {"acoes": [], "parada": _parada(
                    "cidade_servico", campo=campo.get("label") or "",
                    pergunta=str(campo.get("label") or ""),
                    mensagem=f"nao consegui marcar {lugar.get('cidade')}/{lugar.get('estado')} nesta tela.")}
            d = _decidir_campo(slot, campo, collected, tipo)
            if d.get("parada"):
                return {"acoes": [], "parada": d["parada"]}
            acoes.append(d["acao"])
    return {"acoes": acoes, "parada": None}


def _resultado_falhou(slot: str, r: str) -> bool:
    if slot == "aceita_reparo":
        return r != "clicked"
    if slot == "pergunta":
        return r != "checked"
    return not (str(r).startswith(("filled", "mdselect=", "select=")))


async def conter_a_tela(page, state: Dict[str, Any], collected: Dict[str, Any],
                        evidence: Dict[str, Any],
                        falhas: Optional[List[Dict[str, Any]]] = None) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """Executa a contenção até a tela não ter mais nada crítico vazio.

    Devolve `(parada, state)`: `parada` não-nula = o DOM PARA aqui, com a
    pergunta e as opções reais; `state` = a tela depois do que o código escreveu.
    Ação do código que o portal não aceita vira PARADA do slot (com as opções que
    o portal devolveu) — nunca uma segunda tentativa às cegas, nunca o modelo."""
    for f in falhas or []:
        return _parada("cidade_servico", campo=f.get("campo") or "", pergunta="Em que cidade o servico deve ser feito?",
                       opcoes=f.get("opcoes") or [],
                       mensagem=("a cidade do servico nao casa com NENHUMA sugestao do portal por "
                                 "igualdade — nao escolho cidade parecida.")), state
    feitas = set()
    for _ in range(MAX_RODADAS_DA_CONTENCAO):
        plano = plano_de_contencao(state, collected)
        if plano.get("parada"):
            return plano["parada"], state
        if not plano.get("acoes"):
            return None, state
        for ac in plano["acoes"]:
            slot = str(ac.get("slot") or "")
            assinatura = (ac.get("action"), ac.get("target"), ac.get("value"))
            if assinatura in feitas:
                return _parada(slot, campo=str(ac.get("target") or ""), pergunta=str(ac.get("target") or ""),
                               mensagem=f"o portal nao aceitou o que escrevi em '{ac.get('target')}'."), state
            feitas.add(assinatura)
            acao = {k: v for k, v in ac.items() if k != "slot"}
            try:
                r = str(await apply_action(page, acao))
            except Exception as e:  # noqa: BLE001
                r = f"erro:{type(e).__name__}"
            evidence.setdefault("contencao", []).append(
                {"slot": slot, "acao": str(ac.get("action")), "alvo": str(ac.get("target") or "")[:80],
                 "r": r[:80]})
            if _resultado_falhou(slot, r):
                opcoes = ([o.strip() for o in r.split("=", 1)[1].split("|") if o.strip()]
                          if r.startswith(("mdselect_options=", "select_options=")) else [])
                return _parada(slot, campo=str(ac.get("target") or ""), pergunta=str(ac.get("target") or ""),
                               opcoes=opcoes,
                               mensagem=f"o portal nao aceitou '{ac.get('value')}' em '{ac.get('target')}' ({r[:60]})."), state
            await page.wait_for_timeout(400)
        state = await capture_state(page)
    return None, state


def resultado_da_parada(evidence: Dict[str, Any], state: Dict[str, Any], collected: Dict[str, Any],
                        parada: Dict[str, Any]) -> JourneyResult:
    """A parada da contenção no formato que o resto do sistema lê: `needs_human`
    com `stage` + `acao_esperada` + as opções REAIS (a régua do destravador
    lê a TABELA pela `stage`, nunca pelo modelo)."""
    _registrar_parada(evidence, state, collected, campo=parada.get("campo") or "",
                      pergunta=parada.get("pergunta") or "", opcoes=parada.get("opcoes") or [])
    evidence["parada_do_dom"] = {k: parada.get(k) for k in
                                 ("stage", "acao_esperada", "slot", "campo", "pergunta", "opcoes", "nunca")}
    captured = {k: parada.get(k) for k in ("stage", "acao_esperada", "campo", "pergunta", "opcoes")}
    if parada.get("nunca"):
        captured["nunca"] = parada["nunca"]
    return JourneyResult(status="needs_human", captured=captured,
                         message=aviso_de_pedido_aberto(evidence) + str(parada.get("mensagem") or ""))


async def run_adaptive(page, goal: str, collected: Dict[str, Any], evidence: Dict[str, Any],
                       max_steps: int = MAX_STEPS, confirm: bool = False,
                       runtime: Any = None, conter: bool = False) -> JourneyResult:
    """Loop agentico: preenche o que e FATO -> enxerga -> cerebro decide o resto.

    `runtime` e OPCIONAL (SPEC-073 R3). Sem ele, o laco roda exatamente como
    rodava; com ele, cada acao proposta pelo modelo passa pelo validador
    deterministico antes de tocar a pagina, e o profiler observa a tela.
    """
    from portal_worker import perception as _P

    history: List[Dict[str, Any]] = []
    # Guard local quando a journey nao passou runtime: `confirm` continua sendo
    # a autoridade, e o validador precisa de alguem a quem perguntar.
    _guard = getattr(runtime, "guard", None)
    if _guard is None:
        from portal_worker.guardrails import PortalActionGuard as _PAG

        _guard = _PAG(material_liberado=bool(confirm))
    # A journey de vidros so tem UM botao material legitimo: o que confirma o
    # pedido no 80%. Nomear aqui impede que "Agendar a domicilio" ou "Cancelar
    # atendimento" -- que convivem na mesma tela do passo 7 -- sejam clicados
    # por uma decisao de modelo bem-intencionada.
    if not getattr(_guard, "acao_material_esperada", ""):
        # 📊 No Maxpar o clique que CRIA o pedido e o `Avancar` do passo 6 --
        # o mesmo texto inofensivo dos passos 1 a 5. Declarar os dois rotulos
        # nao afrouxa nada: o que protege e a lista ser FECHADA, combinada com
        # `tela_material`, que so liga na tela do 80%.
        _guard.acao_material_esperada = "avancar|confirmar"
    _escada = getattr(runtime, "escada", None) or _P.EscadaDePercepcao()
    _rejeitadas = 0
    # O job em curso, para o LEDGER do cerebro (SPEC-116 U9): quem pagou a decisao.
    _JOB_EM_CURSO.set({"company_id": getattr(runtime, "company_id", None) or None,
                       "job_id": getattr(runtime, "job_id", None) or None})
    for _ in range(max_steps):
        state = await capture_state(page)
        # Antes de gastar um passo com o modelo: o que ja sabemos, escrevemos.
        # Nao consome passo do teto de proposito — preencher o conhecido nao e
        # uma decisao, e transcricao.
        falhas: List[Dict[str, Any]] = []
        preenchidos = await preencher_o_que_e_fato(page, state, collected, falhas)
        if preenchidos:
            # L0 resolveu: fato conhecido nao passa por modelo (R6).
            _escada.registrar(_P.L0_FATO)
            evidence.setdefault("preenchidos_por_fato", []).extend(preenchidos)
            state = await capture_state(page)
        # O profiler e passivo e barato: registra a assinatura da tela para que
        # "esta tela mudou desde ontem?" tenha resposta sem abrir o portal.
        _prof = getattr(runtime, "profiler", None)
        if _prof is not None:
            _prof.registrar_tela(state)
        if has_protocol(state):
            # O pedido JA EXISTE na seguradora. A PRIMEIRA coisa a fazer, antes
            # de decidir qualquer outra, e gravar o numero: dai em diante nada
            # que der errado consegue mais apaga-lo.
            protocolo = registrar_protocolo(evidence, state.get("text", ""))
            # 🔴 E a FOTO, aqui, antes de qualquer outra coisa. Esta tela e a
            # unica que prova que o pedido existe na seguradora; o passo
            # seguinte navega para longe dela e nao volta.
            await capturar_prova(page, evidence, "protocolo")
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
        if conter:
            # 🔴 SPEC-127 P2 — o CÓDIGO escreve o que é fato e PARA no resto,
            # ANTES de o modelo ver a tela. Ver `plano_de_contencao`.
            parada, state = await conter_a_tela(page, state, collected, evidence, falhas)
            if parada:
                return resultado_da_parada(evidence, state, collected, parada)
        # O provedor do modelo recebe só o que ESTA tela pede (SPEC-127 P2 item 6).
        tela_do_modelo = estado_para_o_modelo(state) if conter else state
        dados_do_modelo = dados_para_o_modelo(collected, state) if conter else collected
        action = await decide_next_action(tela_do_modelo, goal, dados_do_modelo, history)
        _escada.registrar(_P.L3_TEXTO)
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
            forced = await decide_next_action(tela_do_modelo, goal, dados_do_modelo, history, force=True)
            if forced.get("action") in ("fill", "select", "check", "click"):
                action = forced
                history[-1] = action
            else:
                evidence["debug_dom"] = await _dump_dom(page)
                _registrar_parada(evidence, state, collected, pergunta=str(action.get("value") or ""))
                return JourneyResult(status="needs_human", captured={"pergunta": action.get("value")},
                                     message=aviso_de_pedido_aberto(evidence)
                                     + f"preciso de: {action.get('value')}")
        # ------------------------------------------------------------------
        # 🔴 O FUNIL — SPEC-073 E4. Nenhuma acao proposta por modelo toca a
        # pagina sem passar por aqui.
        #
        # Antes desta SPEC, `select` tinha validacao forte (le opcoes reais,
        # exige match confiante) e `fill`/`click`/`check` NAO tinham nenhuma:
        # `fill` escrevia o valor cru num input casado por substring, e a
        # proibicao de clicar "Agendar a domicilio" existia so como frase no
        # prompt. Tres superficies com um terco do rigor da quarta.
        # ------------------------------------------------------------------
        _v = _P.validar_acao(action, state, collected=collected, historico=history,
                             guard=_guard, origem=_P.L3_TEXTO,
                             # A tela do 80% E a fronteira do efeito: dela em
                             # diante, `Avancar` cria o pedido na seguradora.
                             tela_material=is_confirm_screen(state),
                             conter=conter)
        if not _v.ok:
            _rejeitadas += 1
            _escada.rejeitar(action, _v, camada=_P.L3_TEXTO)
            evidence.setdefault("acoes_recusadas", []).append({
                "acao": str(action.get("action") or "")[:16],
                "alvo": str(action.get("target") or "")[:80],
                "motivo": _v.motivo[:200],
            })
            # Escalada do F4: 1o tropeco relê a tela (ela pode ter mudado
            # sozinha); 2o tenta o degrau de cima; 3o para com dossiê. O que NAO
            # acontece mais e gastar 22 passos repetindo a mesma recusa.
            if _rejeitadas >= 3:
                estado_final = await _estado_seguro(page)
                registrar_protocolo(evidence, estado_final.get("text", ""))
                _registrar_parada(evidence, estado_final, collected,
                                  campo=str(action.get("target") or ""),
                                  pergunta=f"acao recusada pelo validador: {_v.motivo}"[:200])
                return JourneyResult(
                    status="needs_human",
                    captured={"stage": "acao_recusada", "motivo": _v.motivo[:200]},
                    message=aviso_de_pedido_aberto(evidence)
                    + f"parei por seguranca: {_v.motivo}")
            history[-1] = {**action, "resultado": f"RECUSADO: {_v.motivo[:160]}"}
            await page.wait_for_timeout(600)
            continue

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
        history[-1] = {**action, "resultado": applied[:220], "tela": _P.assinatura_da_tela(state)}
        if applied.startswith(("mdselect_options=", "select_options=")):
            evidence["campo"] = action.get("target")
            evidence["opcoes"] = [o.strip() for o in applied.split("=", 1)[1].split("|") if o.strip()]
            evidence["pergunta"] = _rotulo_do_campo(state, str(action.get("target") or ""))
            evidence["pedido_do_segurado"] = _pedido_do_segurado(collected)
        sig = (action.get("action"), action.get("target"), action.get("value"), applied)
        steps = evidence.setdefault("adaptive_steps", [])
        # 📊 Ate 08/09/2026 a trilha era `{a,t,v,r}` — a acao, o alvo, o valor e
        # o resultado. Nenhuma das quatro diz EM QUE TELA aquilo aconteceu nem
        # QUANDO: lendo a trilha de um acionamento real nao dava para separar
        # "preencheu o CEP na tela do segurado" de "preencheu o CEP na tela da
        # corretora", nem para saber onde o fluxo demorou. `url`, `tela` e `ts`
        # ja estao na mao (o `state` acabou de ser lido) — custo zero de rede.
        steps.append({"a": sig[0], "t": sig[1], "v": (action.get("value") or "")[:30], "r": applied[:80],
                      "url": _url_sem_token(state.get("url"))[:300],
                      "tela": _RED.redigir_texto(state.get("heading") or "")[:120],
                      "sig": _P.assinatura_da_tela(state),
                      "ts": _agora_utc()})
        # Parada antecipada: 3 acoes identicas seguidas sem mudar nada = tela travada.
        # Para com o DOM (diagnostico) em vez de arrastar ate MAX_STEPS.
        # 🔴 SPEC-127 P2: "sem mudar nada" inclui a TELA. 📊 Medido no fio da 127:
        # três `Avançar → clicked` em três telas DIFERENTES (20% → 50% → cidade)
        # eram declarados "tela travada" — o heading é "Dados da apólice" em todas.
        sigs = [(s["a"], s["t"], s["v"], s["r"], s.get("sig")) for s in steps[-3:]]
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
