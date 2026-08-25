"""Normalizador de inbound do Evolution API v2 (SPEC-017 P1.2) — PURO.

Converte o webhook `messages.upsert` do Evolution para o dict legado que o
pipeline existente (ZAPIWebhookPayload/process_whatsapp_message_background)
já entende. Defensivo: campos ausentes viram None; grupos/status/fromMe são
sinalizados para o caller ignorar.

INTERATIVAS (incidente 2026-07-12): as URAs das seguradoras mandam BOTÕES,
LISTAS (modais) e FORMULÁRIOS nativos (flows). Antes, essas mensagens caíam em
skip:no_text — o atendente ficava CEGO para elas (e o espelho do dashboard,
incompleto). Agora são renderizadas em texto NO MESMO FORMATO dos exports do
WhatsApp usados para minerar os corredores ("Botão 1: X" / linhas de lista),
então as âncoras dos playbooks casam sem mudança. Os metadados (ids, flow)
seguem em `interactive` para respostas estruturadas futuras.

PIN DE LOCALIZAÇÃO (03/08/2026): `locationMessage` e `liveLocationMessage`
caíam no mesmo `skip:no_text`. O agente perguntava "onde você está", o segurado
mandava o pin — a resposta mais rápida que o WhatsApp oferece a quem está no
acostamento — e o sistema ficava mudo. Agora o pin vira texto: nome/endereço do
lugar primeiro (é o que `parse_address_br` lê), coordenada rotulada no fim.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

# Wrappers que embrulham a mensagem real (interativas costumam vir dentro).
_WRAPPER_KEYS = (
    "viewOnceMessage", "viewOnceMessageV2", "viewOnceMessageV2Extension",
    "ephemeralMessage", "documentWithCaptionMessage",
)


def _unwrap_message(message: Dict[str, Any]) -> Dict[str, Any]:
    seen = 0
    while isinstance(message, dict) and seen < 4:
        wrapped = None
        for key in _WRAPPER_KEYS:
            inner = message.get(key)
            if isinstance(inner, dict) and isinstance(inner.get("message"), dict):
                wrapped = inner["message"]
                break
        if wrapped is None:
            return message
        message = wrapped
        seen += 1
    return message if isinstance(message, dict) else {}


def _clean(text: Any) -> str:
    return str(text).strip() if isinstance(text, str) and text.strip() else ""


# ------------------------------------------------------------------ #
# O CLIQUE — extração tolerante à grafia
# ------------------------------------------------------------------ #
# Quem serializa o protobuf do WhatsApp escolhe o nome das chaves, e não avisa.
#
# 📊 Medido em 03/08/2026 (`observed_events`, projeto de produção
# `dcajcvlzcjbmyapmklil`): dos 947 cliques de botão vindos do histórico, 937
# chegaram na forma
#
#     ["Response", "contextInfo", "selectedButtonID", "type"]
#
# e o extrator procurava exatamente `title`, `singleSelectReply.selectedRowId`
# e `selectedDisplayText` — nenhuma das três está aí. **98,9% dos cliques de
# botão da corretora foram apagados na leitura.**
#
# P-56 — o mesmo defeito estava VIVO aqui, no caminho ao vivo: até 03/08/2026
# `_text_from_message` procurava `selectedButtonId` (d minúsculo) e o campo real
# é `selectedButtonID`. E aqui a consequência é pior que no observador: texto
# vazio vira `skip:no_text`, e a mensagem inteira é DESCARTADA — o corredor não
# vê o clique do segurado, e o atendente humano também não.
#
# Estas funções moram neste arquivo, e não no observador, porque este é o
# parser canônico de mensagem do WhatsApp e não importa nada da aplicação. O
# observador as importa daqui (`observer_intake._extract_content`) — uma
# grafia nova precisa ser aprendida UMA vez, não duas (CLAUDE.md §5).
#
# 💭 INFERÊNCIA (não medida — o banco guarda as chaves, não os valores):
# `Response` e `InteractiveResponseMessage` são os nomes dos campos `oneof` das
# structs Go do whatsmeow, que vazam como objeto ANINHADO quando o payload não
# passa pelo protojson; `selectedButtonID` e `selectedID` são o mesmo vazamento,
# na grafia Go do "ID". Por isso a busca abaixo **não confere nome exato**:
# normaliza (minúsculas, sem `_`), varre nível por nível — do mais raso ao mais
# fundo — e para no primeiro achado.

# `contextInfo` carrega a mensagem CITADA — a tela anterior inteira, com o
# `title` e os `buttonId` dela. Descer ali roubaria o rótulo da tela e o
# colaria no clique: a resposta passaria a se chamar como a pergunta.
_CHAVE_DE_CONTEXTO = "contextinfo"

# Rótulo = o que o humano LEU no botão. A ordem é a preferência.
_CHAVES_DE_ROTULO = ("title", "selecteddisplaytext", "displaytext",
                     "selectedtext", "buttontext", "text")
# Identidade = o que o humano CLICOU. Opaco serve; vazio não serve.
_CHAVES_DE_ID = ("selectedbuttonid", "selectedid", "selectedrowid",
                 "buttonid", "rowid", "id", "name")

# Os invólucros de resposta estruturada, na grafia normalizada. A chave EXTERNA
# também é procurada normalizada: foi a grafia Go que produziu o defeito, e ela
# pode chegar no invólucro tanto quanto no miolo.
_INVOLUCROS_DE_RESPOSTA = (
    ("listresponsemessage", "list_reply"),
    ("buttonsresponsemessage", "button_reply"),
    ("templatebuttonreplymessage", "button_reply"),
    ("interactiveresponsemessage", "flow_reply"),
)


#: As chaves de id de UMA OPÇÃO — o mesmo alfabeto do clique, menos `name`.
#:
#: 🔴 Derivado de `_CHAVES_DE_ID`, nunca copiado: as duas listas descrevem a
#: mesma coisa em pontas opostas da conversa, e duas cópias divergem. Quem
#: acrescentar uma grafia nova lá acerta aqui de graça.
#:
#: ⚠️ `name` sai. Numa opção ele não é id — e num botão de formulário nativo
#: `name` vale `galaxy_message`, que viraria o "id" de toda opção da tela.
_CHAVES_DE_ID_DE_OPCAO = tuple(c for c in _CHAVES_DE_ID if c != "name")

#: Teto do cru guardado. Mesmo número do observador, e a razão é a mesma: um
#: payload de mídia inteiro não cabe numa linha de acervo.
_TETO_DO_CRU_BYTES = 50_000


def _sub(d: Any, *nomes: str) -> Dict[str, Any]:
    """O sub-dicionário chamado <nome>, seja qual for a grafia — e atravessando
    um nível de invólucro homônimo.

    🔴 ESTA FUNÇÃO É O BLOCO B INTEIRO, e ela existe porque o caminho real
    do convite tem **três** diferenças do que o parser procurava — e nenhuma
    delas é o rótulo do botão.

    📊 Medido em 25/08/2026, no `quotedMessage` das quatro capturas `live`
    da Yelum (03, 07, 17 e 19/08). O caminho de verdade é::

        quotedMessage
          .interactiveMessage
            .InteractiveMessage        ← NÍVEL EXTRA, e com I maiúsculo
              .NativeFlowMessage       ← N maiúsculo
                .buttons[0].name              = "galaxy_message"
                .buttons[0].buttonParamsJSON  ← JSON todo em maiúscula

    E o parser procurava ``interactiveMessage.nativeFlowMessage`` e
    ``buttonParamsJson``. Ele **nunca chegava aos botões**: caía no ramo final
    com `options` vazio e `body` preenchido, e devolvia
    ``{"kind": "buttons", "options": []}``.

    ⚠️ É exatamente o sintoma medido no acervo — 50 das 62 respostas de
    formulário têm, segundos antes, uma linha `buttons` com ZERO opções.

    🔴 **Por isso acrescentar `galaxy_message` à lista, sozinho, não
    consertaria nada.** A SPEC-092 §B.1 pede o rótulo; o rótulo é o terceiro
    dos três, e o único que já estava escrito em algum lugar.

    ⚠️ E é a MESMA família de defeito de `_valor_tolerante` (`buttonID` com D
    maiúsculo) e da P-56 (`selectedButtonId`, 98,9% dos cliques). Terceira
    aparição: **quem serializa o protobuf escolhe o nome das chaves, e não
    avisa.** O lado da RESPOSTA já lia com grafia normalizada; o lado do
    CONVITE lia com `.get()` cru.
    """
    cadeia = _cadeia(d, *nomes)
    return cadeia[-1] if cadeia else {}


#: Teto de profundidade da busca por invólucro homônimo.
#:
#: 🔴 SEM ELE O PARSER DERRUBAVA A ROTA DO WEBHOOK. Medido pelo red team:
#: `json.loads` aceita 5.000 níveis de aninhamento, `_sub` recursava sem teto, e
#: `webhook.py:1246` chama `normalize_evolution_inbound(body)` **sem
#: `try/except`** — `RecursionError` virava 500 na rota e a mensagem da
#: seguradora se perdia.
#:
#: ⚠️ 8 é folgado: 📊 a forma real do fio tem **dois** níveis homônimos.
_TETO_DE_INVOLUCROS = 8


def _cadeia(d: Any, *nomes: str) -> list:
    """Todos os níveis homônimos, **do mais externo ao mais interno**.

    🔴 ESTA FUNÇÃO EXISTE PORQUE `_sub` DEVOLVIA SÓ O MAIS INTERNO — E ISSO
    APAGAVA O TEXTO DA SEGURADORA.

    📊 Medido pelo painel, na forma real do fio: o `interactiveMessage` de fora
    tem `body` + `header` + `InteractiveMessage`; o de dentro tem **só**
    `NativeFlowMessage`. Procurando `body` no mais interno, não se acha nada::

        flow_id           âncora ANTES   âncora DEPOIS(com o defeito)
        2887131368288279  onde_parado    —
        3206000179602236  condicoes      —

    **3 de 3 casamentos de âncora viravam 0**, e `detect_native_flow` existe
    exatamente para o caso *"o `flow_id` não chegou"* — a rede de segurança que
    a própria SPEC-092 desenha.

    ⚠️ **E o guarda não via porque o fixture era inventado:** ele copiava o
    miolo para dentro (`interno: dict(miolo)`), dando `body` aos dois níveis. O
    fio não dá. É o `CLAUDE.md` §9.2 contra quem o escreveu — forma deduzida em
    vez de medida.
    """
    saida: list = []
    atual = d
    alvos = {n.lower().replace("_", "") for n in nomes}
    for _ in range(_TETO_DE_INVOLUCROS):
        if not isinstance(atual, dict):
            break
        achou = None
        for k, v in atual.items():
            if str(k).lower().replace("_", "") in alvos and isinstance(v, dict):
                achou = v
                break
        if achou is None:
            break
        saida.append(achou)
        atual = achou
    return saida


def _lista_tolerante(d: Any, nome: str) -> list:
    """A lista chamada `<nome>`, seja qual for a grafia que o fio usou.

    ⚠️ `_sub` e `_valor_tolerante` já normalizavam; `buttons`, `sections` e
    `rows` continuavam com `.get()` cru — tolerância assimétrica dentro do
    arquivo cuja tese é *"quem serializa o protobuf escolhe o nome das chaves"*.
    """
    if not isinstance(d, dict):
        return []
    alvo = nome.lower().replace("_", "")
    for k, v in d.items():
        if str(k).lower().replace("_", "") == alvo and isinstance(v, list):
            return v
    return []


def _de_qualquer_nivel(cadeia: list, nome: str, chave: str) -> str:
    """O valor de `<nome>.<chave>`, no nível em que ele existir.

    Do mais externo para o mais interno: 📊 na forma real do fio o `body` mora
    no de fora, e no fixture antigo morava nos dois.
    """
    for nivel in cadeia:
        valor = _clean(_sub(nivel, nome).get(chave))
        if valor:
            return valor
    return ""


def _valor_tolerante(d: Any, chaves: Tuple[str, ...]) -> str:
    """O valor de uma chave, seja qual for a grafia que o fio usou.

    🔴 ESTA FUNÇÃO EXISTE PORQUE O MESMO DEFEITO ESTAVA VIVO EM DUAS PONTAS.

    📊 Medido em 25/08/2026 sobre o cru dos dois acervos: o fio manda
    **`buttonID`** e **`rowID`**, com **D maiúsculo**. O parser lia
    ``b.get("buttonId")`` e ``row.get("rowId")``. Resultado, nas duas tabelas::

        list      6.726 + 3.318 opções   `id` preenchido em ZERO
        buttons   3.832 + 1.397 opções   `id` preenchido em ZERO
        ──────────────────────────────────────────────────────
        15.273 opções de convite, e nenhuma com id

    ⚠️ E o título sempre veio: só o id caía. Um acervo que guarda o rótulo e
    perde o identificador não permite responder — 📊 as respostas mostram id
    opaco de servidor (``pd-dc-<ts>-<hash>-0``), **não reconstruível a partir
    do título**.

    O `observer_intake.py:203` já conta esta MESMA história do lado da
    RESPOSTA — *"`_text_from_message` lia `selectedButtonId`, d minúsculo"* — e
    a busca tolerante que a resolveu mudou de casa para cá. **Ela nunca foi
    aplicada ao lado do CONVITE.** É a mesma cura, no gêmeo esquecido.
    """
    if not isinstance(d, dict):
        return ""
    normalizadas = {str(k).lower().replace("_", ""): v for k, v in d.items()}
    for chave in chaves:
        v = normalizadas.get(chave)
        if isinstance(v, bool):
            continue
        if isinstance(v, str) and v.strip():
            return v.strip()
        if isinstance(v, int):
            return str(v)
    return ""


#: Os invólucros que carregam uma TELA — o que a seguradora mostrou.
_CONTAINERS_DE_TELA = ("buttonsMessage", "templateMessage", "listMessage",
                       "interactiveMessage")


#: O que NUNCA entra no cru, em nenhuma profundidade e em nenhuma grafia.
#:
#: 🔴 `contextInfo` cita a mensagem anterior — pode ser qualquer coisa que a
#: pessoa do atendimento digitou. `mediaKey` e amigos são **chave de
#: descriptografia**. E `flow_metadata` traz `www_proxy_secret` e
#: `flow_token_signature`: **segredo, numa tabela durável**.
_FORA_DO_CRU = ("contextinfo", "mediakey", "directpath", "fileencsha256",
                "filesha256", "jpegthumbnail", "flowmetadata",
                "wwwproxysecret", "flowtokensignature", "mediakeytimestamp")


def _sem_o_que_nao_e_a_tela(o: Any, prof: int = 0) -> Any:
    """Tira do cru, em TODA profundidade e em QUALQUER grafia, o que não é tela.

    🔴 A PRIMEIRA VERSÃO CORTAVA `kk != "contextInfo"`, COMPARAÇÃO EXATA E SÓ
    NO PRIMEIRO NÍVEL — dentro do arquivo cuja tese inteira é que a grafia das
    chaves varia. Medido pelo painel, com controle::

        contextInfo  (grafia do corpus)   cru contem o citado?  False   ← cortava
        ContextInfo  (grafia Go)          cru contem o citado?  True
        context_info (snake)              cru contem o citado?  True
        aninhado 2 níveis                 cru contem o citado?  True + mediaKey

    ⚠️ E o mesmo serializador que produziu `InteractiveMessage`,
    `NativeFlowMessage`, `buttonID`, `rowID` e `Header` é quem escolhe essa caixa.

    ⚠️ **E o que sobra ainda pode ter dado de segurado**: 📊 a URA ecoa placa,
    CPF e telefone no texto da própria tela (`buttonsMessage.contentText`). A
    frase *"nada ali é do segurado"* era falsa e foi corrigida — o recorte
    reduz a superfície, **não a zera**, e isso está na pendência.
    """
    if prof > 14:
        return None
    if isinstance(o, dict):
        return {k: _sem_o_que_nao_e_a_tela(v, prof + 1) for k, v in o.items()
                if str(k).lower().replace("_", "") not in _FORA_DO_CRU}
    if isinstance(o, list):
        return [_sem_o_que_nao_e_a_tela(x, prof + 1) for x in o]
    return o


def cru_da_tela(message: Any) -> Optional[Dict[str, Any]]:
    """O cru da TELA que a seguradora mandou — e só dela.

    🔴 NÃO é a mensagem inteira, e a diferença é de PII.

    O invólucro de tela é o que a SEGURADORA escreveu: o texto do menu, as
    opções, os identificadores, os metadados do formulário. Nada ali é do
    segurado. Já `contextInfo` cita a mensagem anterior — que pode ser
    qualquer coisa que a pessoa do atendimento digitou. **Ele fica de fora.**

    ⚠️ Guardar a mensagem inteira seria mais fácil e traria dado de segurado
    para uma tabela durável sem ninguém decidir isso. Guardar só a tela é o
    recorte que responde à pergunta desta SPEC — *como era o convite?* — sem
    ampliar o que se retém sobre quem está do outro lado.

    📊 O `flow_token` FICA, e é decisão registrada: ele traz os dois
    telefones (medido: `uuid:<seguradora>:<cliente>`), e esta tabela já guarda
    os dois em `counterparty` e `observer_number`, como colunas de primeira
    classe. Não é classe nova de exposição, e o Gate A depende dele.
    ⛔ O que ele **nunca** faz é chegar ao checkpoint durável do Work Run:
    `_CHAVES_PROIBIDAS` corta toda chave com "token", e a sessão nunca guarda
    o `interactive` inteiro — só campos nomeados, em `registrar_formulario_nativo`.
    """
    if not isinstance(message, dict):
        return None
    alvos = {n.lower().replace("_", ""): n for n in _CONTAINERS_DE_TELA}
    tela = {alvos[str(k).lower().replace("_", "")]: v for k, v in message.items()
            if str(k).lower().replace("_", "") in alvos and isinstance(v, dict)}
    if not tela:
        return None
    return cru_limitado({k: _sem_o_que_nao_e_a_tela(v) for k, v in tela.items()})


def cru_limitado(message: Any) -> Optional[Dict[str, Any]]:
    """O payload cru, com teto — a memória que permite consertar depois.

    🔴 Mora aqui, no parser canônico, e não no observador: os DOIS acervos e o
    corredor ao vivo passam por esta função, e guardar o cru num só deles
    recria a assimetria que esta SPEC existe para matar. 📊 O caminho
    `history_sync` guardou apenas `sorted(m.keys())` e perdeu 37 eventos de
    Porto e Azul **para sempre** (P-084-38).

    ⚠️ Acima do teto guarda-se o nome das gavetas, que é melhor que nada e
    **pior que o conteúdo** — é exatamente o que aconteceu com Porto e Azul.
    O teto existe porque uma linha de acervo não comporta um vídeo.
    """
    try:
        blob = json.dumps(message, ensure_ascii=False, default=str)
        if len(blob.encode("utf-8")) > _TETO_DO_CRU_BYTES:
            return {"_truncado": True,
                    "chaves": sorted(message.keys()) if isinstance(message, dict) else []}
        return message if isinstance(message, dict) else None
    except Exception:  # noqa: BLE001
        return None


def _niveis_de(m: Dict[str, Any], fundo: int = 2) -> list:
    """Os escalares do payload agrupados por profundidade, chaves normalizadas.

    Nível 0 é o topo, nível 1 é o que está dentro de um objeto do topo, e assim
    por diante. Manter os níveis separados é o que garante que o campo mais
    específico ganhe do genérico sem depender da ordem do dicionário.
    """
    niveis: list = []
    atual = [m]
    for _ in range(fundo + 1):
        if not atual:
            break
        nivel: Dict[str, Any] = {}
        proximo: list = []
        for d in atual:
            for k, v in d.items():
                nk = str(k).lower().replace("_", "")
                if nk == _CHAVE_DE_CONTEXTO:
                    continue
                if isinstance(v, dict):
                    proximo.append(v)
                elif nk not in nivel:
                    nivel[nk] = v
        niveis.append(nivel)
        atual = proximo
    return niveis


def _primeiro_valor(niveis: list, chaves: Tuple[str, ...]) -> str:
    """O primeiro valor útil, do nível mais raso para o mais fundo."""
    for nivel in niveis:
        for chave in chaves:
            v = nivel.get(chave)
            if isinstance(v, bool):
                continue
            if isinstance(v, str) and v.strip():
                return v.strip()
            if isinstance(v, int):
                return str(v)
    return ""


def _resposta_estruturada(message: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
    """(kind, rótulo, id) do clique — ou None se não houver resposta estruturada."""
    if not isinstance(message, dict):
        return None
    normalizadas = {str(k).lower().replace("_", ""): k for k in message}
    for alvo, kind in _INVOLUCROS_DE_RESPOSTA:
        if alvo not in normalizadas:
            continue
        m = message.get(normalizadas[alvo])
        if not isinstance(m, dict):
            continue
        niveis = _niveis_de(m)
        return kind, _primeiro_valor(niveis, _CHAVES_DE_ROTULO), _primeiro_valor(niveis, _CHAVES_DE_ID)
    return None


def _interactive_from_message(message: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, Any]]]:
    """(texto_renderizado, metadados) para botões/listas/templates/flows.

    O texto imita o formato dos exports do WhatsApp (fonte dos playbooks):
    - botões:  corpo + "Botão 1: X" por botão;
    - lista:   corpo + "Título — descrição" por linha + nome do botão do modal;
    - flow:    corpo + marcador [FORMULARIO NATIVO: <cta>] (não responder por texto).
    """
    if not isinstance(message, dict):
        return None

    # --- buttonsMessage (quick replies clássicos) ---
    btns_msg = message.get("buttonsMessage")
    if isinstance(btns_msg, dict):
        body = _clean(btns_msg.get("contentText")) or _clean(btns_msg.get("text"))
        options: List[Dict[str, str]] = []
        for b in btns_msg.get("buttons") or []:
            if not isinstance(b, dict):
                continue
            title = _clean((b.get("buttonText") or {}).get("displayText"))
            if title:
                options.append({"id": _valor_tolerante(b, _CHAVES_DE_ID_DE_OPCAO), "title": title})
        if body or options:
            lines = [body] if body else []
            lines += [f"Botão {i}: {o['title']}" for i, o in enumerate(options, 1)]
            return "\n".join(lines), {"kind": "buttons", "options": options,
                                        "cru": cru_da_tela(message)}

    # --- templateMessage (hydratedTemplate) ---
    tpl = message.get("templateMessage")
    if isinstance(tpl, dict):
        hyd = tpl.get("hydratedTemplate") or tpl.get("hydratedFourRowTemplate") or {}
        if isinstance(hyd, dict):
            body = _clean(hyd.get("hydratedContentText"))
            options = []
            for b in hyd.get("hydratedButtons") or []:
                if not isinstance(b, dict):
                    continue
                qr = b.get("quickReplyButton")
                if isinstance(qr, dict) and _clean(qr.get("displayText")):
                    options.append({"id": _valor_tolerante(qr, _CHAVES_DE_ID_DE_OPCAO),
                                    "title": _clean(qr.get("displayText"))})
            if body or options:
                lines = [body] if body else []
                lines += [f"Botão {i}: {o['title']}" for i, o in enumerate(options, 1)]
                return "\n".join(lines), {"kind": "buttons", "options": options,
                                          "cru": cru_da_tela(message)}

    # --- listMessage (modal de opções) ---
    lst = message.get("listMessage")
    if isinstance(lst, dict):
        body = _clean(lst.get("description")) or _clean(lst.get("title"))
        button_label = _clean(lst.get("buttonText"))
        options = []
        for section in lst.get("sections") or []:
            for row in (section or {}).get("rows") or []:
                if not isinstance(row, dict):
                    continue
                title = _clean(row.get("title"))
                if title:
                    options.append({
                        "id": _valor_tolerante(row, _CHAVES_DE_ID_DE_OPCAO), "title": title,
                        "description": _clean(row.get("description")),
                    })
        if body or options:
            lines = [body] if body else []
            for o in options:
                lines.append(o["title"] + (f"\n{o['description']}" if o.get("description") else ""))
            meta = {"kind": "list", "options": options, "cru": cru_da_tela(message)}
            if button_label:
                meta["button_label"] = button_label
            return "\n".join(lines), meta

    # --- interactiveMessage (native flow: quick_reply/single_select/flow) ---
    cadeia = _cadeia(message, "interactiveMessage")
    inter = cadeia[-1] if cadeia else None
    if isinstance(inter, dict) and inter:
        # 🔴 O CORPO SE PROCURA EM TODOS OS NÍVEIS. Ver `_cadeia`.
        body = (_de_qualquer_nivel(cadeia, "body", "text")
                or _de_qualquer_nivel(cadeia, "header", "title"))
        nfm = _sub(inter, "nativeFlowMessage") or _sub(cadeia[0], "nativeFlowMessage")
        options = []
        flow_meta: Optional[Dict[str, Any]] = None
        # 🔴 `Buttons` com B maiúsculo é lido. Medido pelo red team: sem
        # isto, a mesma família de defeito que este arquivo inteiro documenta
        # reabria a P-084-68 **por uma letra**.
        for b in (_lista_tolerante(nfm, "buttons") or []):
            if not isinstance(b, dict):
                continue
            name = _valor_tolerante(b, ("name",))
            try:
                params = json.loads(
                    _valor_tolerante(b, ("buttonparamsjson", "buttonparams")) or "{}")
            except Exception:  # noqa: BLE001
                params = {}
            if not isinstance(params, dict):
                params = {}
            if name == "quick_reply":
                title = _clean(params.get("display_text"))
                if title:
                    options.append({"id": _valor_tolerante(params, _CHAVES_DE_ID_DE_OPCAO),
                                "title": title})
            elif name == "single_select":
                for section in _lista_tolerante(params, "sections"):
                    for row in _lista_tolerante(section, "rows"):
                        title = _clean(row.get("title"))
                        if title:
                            options.append({
                                "id": _valor_tolerante(row, _CHAVES_DE_ID_DE_OPCAO), "title": title,
                                "description": _clean(row.get("description")),
                            })
            # 🔴 `galaxy_message` é o rótulo LEGADO da Meta, e é o que a
            # família HDI/Yelum usa. 📊 Medido: nas quatro capturas `live` o
            # botão do convite se chama `galaxy_message`, e `"flow"` não aparece
            # em nenhuma delas.
            #
            # ⚠️ O lado do ENVIO documenta este MESMO fato desde 03/08
            # (`evolution_go.montar_nfm_reply`), e ninguém tinha cruzado com o
            # lado da LEITURA — as duas pontas do mesmo formulário, em dois
            # arquivos, com a mesma descoberta feita uma vez só.
            elif name in ("flow", "mpm", "wa_payment_details", "review_and_pay",
                          "galaxy_message"):
                flow_meta = {
                    "name": name,
                    "cta": (_valor_tolerante(params, ("flowcta",))
                            or _valor_tolerante(params, ("displaytext",))),
                    "flow_id": (_valor_tolerante(params, ("flowid",))
                                or _valor_tolerante(params, ("flowname",))) or None,
                    "flow_token": _valor_tolerante(params, ("flowtoken",)) or None,
                }
        if flow_meta:
            lines = [body] if body else []
            lines.append(f"[FORMULARIO NATIVO: {flow_meta.get('cta') or 'formulário'}] (exige clique — não aceita texto)")
            return "\n".join(lines), {"kind": "flow", "flow": flow_meta,
                                      "options": options, "cru": cru_da_tela(message)}
        if body or options:
            lines = [body] if body else []
            for o in options:
                lines.append(o["title"] + (f"\n{o['description']}" if o.get("description") else ""))
            return "\n".join(lines), {
                "kind": "list" if any(o.get("description") for o in options) else "buttons",
                "options": options, "cru": cru_da_tela(message)}

    # --- 🔴 A.2 · O QUE NAO SE RECONHECE, SE GUARDA -----------------------
    #
    # Até aqui, uma tela de forma desconhecida devolvia `None` — e o observador
    # a gravava como `("unknown", None, None, None)`: quatro nulos, msg_type
    # `unknown` e **nenhuma memória de que ela existiu**.
    #
    # 📊 É a mesma perda que apagou Porto e Azul para sempre (P-084-38), com
    # outro nome: forma que ninguém previu vira linha em branco, e quando
    # alguém for consertar não há do que partir.
    #
    # ⚠️ A guarda é ESTREITA de propósito: só dispara quando um invólucro de
    # TELA existe de verdade no payload. Mensagem de texto comum não passa por
    # aqui (o chamador trata texto antes), e nenhuma outra forma vira convite.
    _normais = {str(k).lower().replace("_", "") for k in message}
    if any(n.lower().replace("_", "") in _normais for n in _CONTAINERS_DE_TELA):
        return "[INTERATIVA NAO RECONHECIDA]", {
            "kind": "desconhecido", "options": [], "cru": cru_da_tela(message)}

    return None


# ------------------------------------------------------------------ #
# O PIN — a resposta que o produto pedia e depois jogava fora
# ------------------------------------------------------------------ #
# O agente pergunta "onde você está"; a pessoa no acostamento faz a coisa mais
# rápida que o WhatsApp oferece e manda o PIN. O laço de mídia acima não conhece
# `locationMessage`, `_text_from_message` não achava texto, e `normalize_...`
# devolvia `skip: no_text`. O sistema ficava mudo para a única resposta que o
# segurado tinha como dar depressa — e a pergunta era do próprio sistema.
#
# O que sai daqui é TEXTO, na ordem que serve a quem lê depois: o endereço
# primeiro (é o que `parse_address_br` sabe ler), a coordenada rotulada no fim
# (é o que o guincho usa, e é dado bruto, não endereço).
_LAT_KEYS = ("degreesLatitude", "latitude", "lat")
_LON_KEYS = ("degreesLongitude", "longitude", "lng", "lon", "long")


def _coord(fonte: Dict[str, Any], chaves) -> Optional[float]:
    """Primeira chave presente que vira float. Grafia tolerante, como no clique."""
    for k in chaves:
        v = fonte.get(k)
        if isinstance(v, bool) or v is None:
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return None


def _grau(valor: float) -> str:
    """6 casas (~0,11 m) sem zeros pendurados — o guincho lê isto."""
    return f"{valor:.6f}".rstrip("0").rstrip(".") or "0"


def _texto_de_localizacao(message: Dict[str, Any]) -> Optional[str]:
    """O pin virado em texto útil, ou None quando não há pin nenhum."""
    for chave, ao_vivo in (("locationMessage", False), ("liveLocationMessage", True)):
        loc = message.get(chave)
        if not isinstance(loc, dict):
            continue
        lat = _coord(loc, _LAT_KEYS)
        lon = _coord(loc, _LON_KEYS)
        # (0, 0) é o DEFAULT do protobuf para `double` não preenchido, não a Ilha
        # Nula no golfo da Guiné. Tratar como coordenada mandaria o guincho para
        # o meio do Atlântico com a confiança de quem tem número.
        if lat is None or lon is None or (lat == 0 and lon == 0):
            lat = lon = None
        rotulo = _clean(loc.get("name"))
        endereco = _clean(loc.get("address"))
        legenda = _clean(loc.get("caption"))  # a live location traz aqui
        if lat is None and not (rotulo or endereco or legenda):
            continue  # pin vazio não é resposta; deixa o skip:no_text acontecer

        cabeca = "Localização ao vivo compartilhada" if ao_vivo else "Localização compartilhada"
        # LINHAS SEPARADAS, e não uma frase só.
        #
        # A coordenada colada no fim do endereço envenenava `parse_address_br`:
        # ele quebra o texto em `,` e `-`, e `-48.5477` virava a CIDADE. Endereço
        # é uma linha; a coordenada é outra. O parser lê a primeira e ignora o
        # resto — errado com confiança é o defeito que este conserto evita, não
        # o que ele deveria introduzir.
        endereco_humano = ", ".join(dict.fromkeys([p for p in (rotulo, endereco) if p]))
        linhas: List[str] = []
        if endereco_humano:
            linhas.append(endereco_humano)
        cauda = f"{cabeca}: {_grau(lat)},{_grau(lon)}" if lat is not None else f"{cabeca} (sem coordenada)"
        if ao_vivo and lat is not None:
            cauda += " — a pessoa pode estar em movimento"
        linhas.append(cauda)
        if legenda and legenda not in endereco_humano:
            linhas.append(legenda)
        return "\n".join(linhas).strip()
    return None


def _text_from_message(message: Dict[str, Any]) -> Optional[str]:
    if not isinstance(message, dict):
        return None
    conversation = message.get("conversation")
    if isinstance(conversation, str) and conversation.strip():
        return conversation.strip()
    extended = message.get("extendedTextMessage")
    if isinstance(extended, dict):
        text = extended.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
    pin = _texto_de_localizacao(message)
    if pin:
        return pin
    for media_key in ("imageMessage", "videoMessage", "documentMessage"):
        media = message.get(media_key)
        if isinstance(media, dict):
            caption = media.get("caption")
            if isinstance(caption, str) and caption.strip():
                return caption.strip()
    # RESPOSTAS interativas (clique em botão/lista — ex.: humano copilotando a
    # URA com fromMe, ou cliente respondendo lista): extrair o rótulo escolhido.
    #
    # P-56 — as quatro grafias eram procuradas por nome exato, e a mais comum
    # (📊 937 de 947 cliques) não estava na lista. Aqui a busca é normalizada:
    # `selectedButtonID`, `selectedButtonId` e `selected_button_id` são o mesmo
    # campo, e uma grafia nova deixa de ser incidente.
    escolha = _resposta_estruturada(message)
    if escolha:
        _kind, rotulo, ident = escolha
        # O rótulo (o que a pessoa LEU) tem precedência. O id opaco é o último
        # recurso, e vale a pena: sem texto nenhum o inbound devolve
        # `skip:no_text` e a mensagem some — o corredor deixa de ver o clique.
        if rotulo or ident:
            return rotulo or ident
    return None


def _phone_from_jid(jid: Optional[str]) -> Optional[str]:
    if not isinstance(jid, str) or not jid:
        return None
    return jid.split("@")[0].split(":")[0] or None


def normalize_evolution_inbound(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Retorna dict normalizado:

    { skip: bool, skip_reason: str|None, message_id, phone, connected_phone,
      sender_name, text, is_group, from_me, timestamp }
    """
    out: Dict[str, Any] = {
        "skip": False, "skip_reason": None, "message_id": None, "phone": None,
        "connected_phone": None, "sender_name": None, "text": None,
        "is_group": False, "from_me": False, "timestamp": None, "media": None,
        "interactive": None,
    }
    if not isinstance(payload, dict):
        return {**out, "skip": True, "skip_reason": "invalid_payload"}

    event = str(payload.get("event") or "").strip().lower().replace("_", ".")
    if event and event not in ("messages.upsert",):
        return {**out, "skip": True, "skip_reason": f"event:{event}"}

    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    key = data.get("key") if isinstance(data.get("key"), dict) else {}

    remote_jid = key.get("remoteJid") or data.get("remoteJid")
    from_me = bool(key.get("fromMe") or data.get("fromMe"))
    is_group = isinstance(remote_jid, str) and remote_jid.endswith("@g.us")
    message_id = key.get("id") or data.get("id") or data.get("messageId")

    msg_dict = data.get("message") if isinstance(data.get("message"), dict) else {}
    msg_dict = _unwrap_message(msg_dict)
    media = None
    for media_key, kind in (("imageMessage", "image"), ("documentMessage", "document"), ("documentWithCaptionMessage", "document"), ("audioMessage", "audio")):
        m = msg_dict.get(media_key)
        if media_key == "documentWithCaptionMessage" and isinstance(m, dict):
            m = ((m.get("message") or {}).get("documentMessage")) or m
        if isinstance(m, dict):
            media = {
                "kind": kind,
                "caption": (str(m.get("caption")).strip() or None) if m.get("caption") else None,
                "mimetype": m.get("mimetype") or None,
                "file_name": m.get("fileName") or m.get("title") or None,
                # webhookBase64=true: a Evolution manda a mídia JÁ decodificada
                # no próprio evento (campo base64 no message ou no data).
                "base64": msg_dict.get("base64") or data.get("base64") or None,
            }
            break

    text = _text_from_message(msg_dict)
    interactive = None
    if not text and not media:
        rendered = _interactive_from_message(msg_dict)
        if rendered:
            text, interactive = rendered

    out.update({
        # A mensagem crua do WhatsApp, em memória e só nesta requisição.
        #
        # `/message/downloadmedia` do Evolution GO exige o `waE2E.Message`
        # inteiro — é ele que traz `mediaKey`, `directPath` e `fileEncSha256`,
        # sem os quais a foto do segurado não pode ser baixada nem descriptada.
        # Só o `message_id` não basta (isso é o wire do Baileys, outro fork).
        #
        # Nunca é gravada em banco nem em log: é material do cliente, e o
        # `media_meta` que fica guardado tem só tipo, nome e legenda.
        "raw_message": msg_dict or None,
        "message_id": str(message_id) if message_id else None,
        "phone": _phone_from_jid(remote_jid),
        "connected_phone": _phone_from_jid(payload.get("sender")) or str(payload.get("instance") or "") or None,
        "sender_name": data.get("pushName") or None,
        "text": text,
        "media": media,
        "interactive": interactive,
        "is_group": is_group,
        "from_me": from_me,
        "timestamp": data.get("messageTimestamp"),
    })

    if from_me:
        return {**out, "skip": True, "skip_reason": "from_me"}
    if is_group:
        return {**out, "skip": True, "skip_reason": "group"}
    # Número pessoal do corretor conectado: Status (status@broadcast), canais
    # (@newsletter) e listas de transmissão (@broadcast) NUNCA viram atendimento.
    # Individuais legítimos (@s.whatsapp.net, @c.us, @lid) seguem passando.
    if isinstance(remote_jid, str) and remote_jid.endswith(("@broadcast", "@newsletter", "@call")):
        return {**out, "skip": True, "skip_reason": "non_individual"}
    if not out["phone"]:
        return {**out, "skip": True, "skip_reason": "no_phone"}
    if not out["text"] and not media:
        return {**out, "skip": True, "skip_reason": "no_text"}
    return out


def dados_do_formulario_nativo(origem: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """O que o transporte precisa para RESPONDER um formulário nativo, ou None.

    Aceita as duas formas que circulam no produto: o payload cru do webhook e o
    dict já normalizado por :func:`normalize_evolution_inbound`. Devolve
    ``{"flow_id", "flow_token", "cta", "name"}``.

    POR QUE ISTO É UMA FUNÇÃO, E NÃO UM `dict.get` NA MÃO DO CHAMADOR
    ------------------------------------------------------------------
    Porque o `flow_token` tem uma regra que precisa viajar junto com ele, e
    regra em comentário solto não viaja: **ele é da sessão e não pode ser
    persistido.** Ele nasce na mensagem que abre o formulário, vale só naquela
    conversa, e some quando ela acaba. Guardá-lo em banco não o torna reusável —
    torna um token morto guardado para sempre, que é a pior combinação
    possível: sem utilidade e com superfície.

    📊 O acervo do Observador já segue essa regra do lado da leitura
    (`observer_intake._parse_native_form` exclui `flow_token` do que arquiva).
    Esta função é o mesmo compromisso do lado da escrita.

    O caminho quente do produto ainda não chama isto: `webhook.py` entrega ao
    roteador de acionamento apenas o TEXTO da mensagem, então o token não
    atravessa. O motor já sabe recebê-lo (`handle_insurer_message(...,
    interactive=...)`); falta o webhook passá-lo. Enquanto não passa, o motor
    monta a resposta e PAUSA — que é o comportamento certo, não um contorno.
    """
    if not isinstance(origem, dict):
        return None
    interativa = origem.get("interactive")
    if not isinstance(interativa, dict):
        dados = origem.get("data") if isinstance(origem.get("data"), dict) else origem
        mensagem = dados.get("message") if isinstance(dados.get("message"), dict) else {}
        rendered = _interactive_from_message(_unwrap_message(mensagem))
        interativa = rendered[1] if rendered else None
    if not isinstance(interativa, dict) or interativa.get("kind") != "flow":
        return None
    flow = interativa.get("flow") or {}
    if not isinstance(flow, dict):
        return None
    # `flow_id` chega como número em parte dos payloads reais — `_clean` só
    # trata str, e um id numérico virando "" faria o schema do formulário nunca
    # ser encontrado (falha silenciosa, exatamente a que trava o acionamento).
    def _txt(valor: Any) -> str:
        return "" if valor is None else str(valor).strip()

    flow_id, token = _txt(flow.get("flow_id")), _txt(flow.get("flow_token"))
    if not flow_id and not token:
        return None
    return {
        "flow_id": flow_id,
        "flow_token": token,
        "cta": _clean(flow.get("cta")),
        "name": _clean(flow.get("name")) or "flow",
    }


def connection_state_from_payload(payload: Dict[str, Any]) -> Optional[str]:
    """Extrai estado de conexão de eventos `connection.update` (watchdog)."""
    if not isinstance(payload, dict):
        return None
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    state = data.get("state") or data.get("connection") or data.get("status")
    return str(state).strip().lower() if state else None
