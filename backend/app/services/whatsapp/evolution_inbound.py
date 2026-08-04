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
                options.append({"id": _clean(b.get("buttonId")), "title": title})
        if body or options:
            lines = [body] if body else []
            lines += [f"Botão {i}: {o['title']}" for i, o in enumerate(options, 1)]
            return "\n".join(lines), {"kind": "buttons", "options": options}

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
                    options.append({"id": _clean(qr.get("id")), "title": _clean(qr.get("displayText"))})
            if body or options:
                lines = [body] if body else []
                lines += [f"Botão {i}: {o['title']}" for i, o in enumerate(options, 1)]
                return "\n".join(lines), {"kind": "buttons", "options": options}

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
                        "id": _clean(row.get("rowId")), "title": title,
                        "description": _clean(row.get("description")),
                    })
        if body or options:
            lines = [body] if body else []
            for o in options:
                lines.append(o["title"] + (f"\n{o['description']}" if o.get("description") else ""))
            meta = {"kind": "list", "options": options}
            if button_label:
                meta["button_label"] = button_label
            return "\n".join(lines), meta

    # --- interactiveMessage (native flow: quick_reply/single_select/flow) ---
    inter = message.get("interactiveMessage")
    if isinstance(inter, dict):
        body = _clean((inter.get("body") or {}).get("text")) or _clean((inter.get("header") or {}).get("title"))
        nfm = inter.get("nativeFlowMessage") or {}
        options = []
        flow_meta: Optional[Dict[str, Any]] = None
        for b in (nfm.get("buttons") or []):
            if not isinstance(b, dict):
                continue
            name = _clean(b.get("name"))
            try:
                params = json.loads(b.get("buttonParamsJson") or "{}")
            except Exception:  # noqa: BLE001
                params = {}
            if name == "quick_reply":
                title = _clean(params.get("display_text"))
                if title:
                    options.append({"id": _clean(params.get("id")), "title": title})
            elif name == "single_select":
                for section in params.get("sections") or []:
                    for row in (section or {}).get("rows") or []:
                        title = _clean(row.get("title"))
                        if title:
                            options.append({
                                "id": _clean(row.get("id")), "title": title,
                                "description": _clean(row.get("description")),
                            })
            elif name in ("flow", "mpm", "wa_payment_details", "review_and_pay"):
                flow_meta = {
                    "name": name,
                    "cta": _clean(params.get("flow_cta")) or _clean(params.get("display_text")),
                    "flow_id": params.get("flow_id") or params.get("flow_name"),
                    "flow_token": params.get("flow_token"),
                }
        if flow_meta:
            lines = [body] if body else []
            lines.append(f"[FORMULARIO NATIVO: {flow_meta.get('cta') or 'formulário'}] (exige clique — não aceita texto)")
            return "\n".join(lines), {"kind": "flow", "flow": flow_meta, "options": options}
        if body or options:
            lines = [body] if body else []
            for o in options:
                lines.append(o["title"] + (f"\n{o['description']}" if o.get("description") else ""))
            return "\n".join(lines), {"kind": "list" if any(o.get("description") for o in options) else "buttons", "options": options}

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
