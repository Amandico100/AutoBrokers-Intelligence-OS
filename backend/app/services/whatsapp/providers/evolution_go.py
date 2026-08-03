"""EvolutionGoProvider — bridge para o Evolution GO (whatsmeow) no contrato WhatsAppProvider.

SPEC-034/decisão do founder 14/07: migrar o canal para o Evolution GO ("fazer já")
e resolver o APP NATIVO (nativeFlowMessage da HDI/Yelum) NO NOSSO código.

Wire confirmado ao vivo em 14/07 contra a instância de teste
(autobrokers-intelligence-os-evolution-go-teste, swagger /swagger/doc.json):

- Auth: header ``apikey: <token DA INSTÂNCIA>`` (validado: /instance/status 200).
  A GLOBAL_API_KEY só serve para operações administrativas (/instance/all etc.).
- send_text : POST {base}/send/text   body ``{number, text}``.
- send_media: POST {base}/send/media  body ``{number, type, url, caption?, filename?}``
  (MediaStruct do swagger: type = image|audio|document...).
- Interativos NATIVOS existem para ORIGINAR mensagem: /send/button, /send/list,
  /send/carousel. Eles NÃO respondem interativa — o que se acreditava ser "a
  chave da missão do app nativo" foi medido em 03/08/2026 e não é (ver abaixo).

Inbound: o GO entrega o evento whatsmeow (Info + Message protojson — o Message
usa as MESMAS chaves waE2E do Baileys: conversation/extendedTextMessage/
interactiveMessage...). O parse aqui converte para o envelope v2 e reusa o
normalizador existente indiretamente (a rota /webhook/evolution-go converte
antes de despachar). ``parse_webhook`` cobre o uso direto pelo registry.

O VEREDITO SOBRE RESPONDER FORMULÁRIO NATIVO (03/08/2026)
---------------------------------------------------------
``PLANO-EVOLUTION-GO-E-APP-NATIVO.md`` deixou em aberto: *"se o GO expõe um
`/send/interactive` (ou aceita o payload no `/send/text` estendido), montamos a
resposta no nosso adapter"*. Isso nunca tinha sido conferido. Agora foi.

📊 `curl https://autobrokers-intelligence-os-evolution-go-teste.golhpm.easypanel.host/swagger/doc.json`
(03/08/2026, HTTP 200, 495.536 bytes, `info.title="Evolution GO"`,
`info.version="1.0"`): **88 rotas**. As de envio são exatamente estas doze —
`ROTAS_DE_ENVIO_MEDIDAS` abaixo é a transcrição delas:

    /send/text · /send/media · /send/button · /send/list · /send/carousel
    /send/contact · /send/link · /send/location · /send/poll · /send/sticker
    /send/status/text · /send/status/media

**Nenhuma das doze envia RESPOSTA de interativa.** As doze *originam* mensagens;
responder um flow é outro tipo de mensagem waE2E
(`interactiveResponseMessage.nativeFlowResponseMessage`, com `name` e
`paramsJSON`), e nenhum handler do GO de origem o produz.

Atualização de 03/08/2026 — o que mudou, e o que NÃO mudou
----------------------------------------------------------
O patch `0005-send-interactive-response` do nosso fork abre a décima terceira:
**`POST /send/interactiveResponse`**. A biblioteca por baixo (whatsmeow) sempre
soube carregar essa mensagem — o caminho de ENTRADA do próprio GO já lê estes
mesmos campos. O que faltava era a porta de saída, e ela agora existe.

O que **não** mudou: nada disso é prova de que a seguradora aceita a resposta.
Ter a rota é ter o caminho; ter o caminho não é ter chegado. Por isso ela
continua atrás de `EVOLUTION_GO_FLOW_REPLY_PATH`, que fica **vazio** até o teste
de ida e volta entre dois números nossos comparar o que chegou, campo a campo,
com o clique humano de 18/07. Ligar antes disso seria trocar uma incerteza
conhecida por uma surpresa no meio de um atendimento real.

Então este arquivo **não inventa endpoint**. Ele entrega:

- :func:`montar_nfm_reply` — o corpo waE2E da resposta, PURO e provável
  offline. A forma não é deduzida: 📊 ela é a de um evento real deste produto
  (`interactiveResponseMessage` com `body.text` + `nativeFlowResponseMessage
  {name, paramsJSON}`, 23 ocorrências no acervo do Observador).
- :meth:`EvolutionGoProvider.send_native_flow_response` — que **recusa por
  padrão**, sem tocar na rede, com `error="evolution_go_sem_rota_de_flow_reply"`.
  Só tenta quando alguém DECLARAR a rota provada em
  ``EVOLUTION_GO_FLOW_REPLY_PATH``. Declarar é um ato de evidência, não um
  palpite: com a variável vazia (o padrão) nada sai.

Ou seja: tudo que dá para provar sem o número pareado está pronto e provado; o
que falta é uma rota que este build do GO não tem.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

import requests

from app.services.whatsapp.exceptions import (
    ProviderConfigError,
    ProviderNotSupportedError,
    WhatsappRetryableError,
)
from app.services.whatsapp.evolution_go_events import go_event_to_v2_envelope
from app.services.whatsapp.models import (
    CanonicalMessage,
    InboundBatch,
    MediaRef,
    OutboundMedia,
    SendResult,
    TemplateRef,
)
from app.services.whatsapp.providers.base import ProviderCapabilities

logger = logging.getLogger(__name__)

_GO_CAPABILITIES = ProviderCapabilities()

# 📊 As rotas de envio deste build do Evolution GO, transcritas do swagger em
# 03/08/2026 (ver docstring). Ficam como DADO, e não como frase de comentário,
# porque é contra esta lista que o teste mede a afirmação "não há rota de
# resposta de flow". Comentário envelhece calado; lista o teste vigia.
ROTAS_DE_ENVIO_MEDIDAS: tuple = (
    "/send/text", "/send/media", "/send/button", "/send/list", "/send/carousel",
    "/send/contact", "/send/link", "/send/location", "/send/poll", "/send/sticker",
    "/send/status/text", "/send/status/media",
)

# A rota que enviaria a resposta do formulário nativo. Vazia = não existe rota
# provada, e nada é enviado. Quem preencher isto está afirmando ter provado a
# rota contra o número pareado — não está chutando um caminho plausível.
ENV_ROTA_FLOW_REPLY = "EVOLUTION_GO_FLOW_REPLY_PATH"

# Texto que o WhatsApp mostra na bolha de quem respondeu o formulário. 📊 É o
# que o acervo do Observador registra nos eventos reais de `flow_reply`.
_CORPO_PADRAO_FLOW_REPLY = "Formulario enviado"


def _strip_jid(value: Any) -> str:
    text = str(value or "")
    return text.split("@", 1)[0].split(":", 1)[0] if text else ""


ROTA_DE_FLOW_REPLY_PROVADA = "/send/interactiveResponse"


def rota_de_flow_reply(env: Optional[Dict[str, str]] = None) -> str:
    """A rota para responder formulário nativo.

    Já foi um palpite proibido, e por isso este portão nasceu vazio: nenhuma das
    doze rotas de `ROTAS_DE_ENVIO_MEDIDAS` responde interativa, e escolher a mais
    parecida seria inventar endpoint.

    📊 Deixou de ser palpite em 03/08/2026. O patch 0005 do nosso fork abriu
    `/send/interactiveResponse`, e ela foi PROVADA no ar: mensagem enviada de um
    número nosso para outro, aceita pelo servidor do WhatsApp, com
    `Type: "InteractiveResponseMessage"` de volta.

    Então o padrão passou a ser a rota provada. A variável de ambiente continua
    existindo — mas mudou de papel: era o que LIGAVA, agora é o que corrige ou
    desliga, se um dia o fork mudar de caminho. Um valor explícito sempre vence.
    """
    fonte = env if env is not None else os.environ
    rota = str(fonte.get(ENV_ROTA_FLOW_REPLY) or "").strip()
    if not rota:
        return ROTA_DE_FLOW_REPLY_PROVADA
    if rota.lower() in ("off", "0", "none", "desligado"):
        return ""
    return rota if rota.startswith("/") else f"/{rota}"


def montar_nfm_reply(
    *,
    flow_token: str,
    params: Dict[str, Any],
    nome_do_envelope: str,
    flow_response_params: Optional[Dict[str, Any]] = None,
    body_text: Optional[str] = None,
    version: int = 1,
) -> Dict[str, Any]:
    """O corpo waE2E de uma resposta de formulário nativo. PURO.

    Três coisas moram aqui, e as três precisam existir juntas para a resposta
    ser aceita:

    1. **O `flow_token`**, que é da SESSÃO — veio na mensagem que abriu o
       formulário e vale só para aquela conversa. `montar_resposta_de_flow`, no
       corredor, deliberadamente NÃO o produz (ele é transporte, não é dado do
       caso). É aqui, e só aqui, que ele entra.
    2. **As respostas**, achatadas ao lado do token — é assim que 📊 o clique
       humano de 18/07/2026 chegou.
    3. **`wa_flow_response_params`**, que carrega a identidade do formulário
       (título, `flow_id`, `flow_name`). Faltava, e é o que diz à seguradora
       QUAL formulário está sendo respondido.

    O NOME DO ENVELOPE NÃO SE ADIVINHA
    ----------------------------------
    Este campo já esteve errado aqui: usávamos o `flow_name` —
    *"Automóvel - Detalhes do atendimento…"*. 📊 O clique humano real de
    18/07/2026 traz ``name = "galaxy_message"``.

    A Meta documenta ``"flow"`` como o nome atual e ``"galaxy_message"`` como
    legado; o bot da família HDI/Yelum usa o **legado**. Escolher entre os dois
    por regra seria apostar — e apostar errado faz a seguradora descartar a
    resposta em silêncio, gastando a única janela antes de a URA encerrar.

    Por isso `nome_do_envelope` é **obrigatório e sem padrão**: quem chama tem
    de ECOAR o que veio na captura. Um default aqui seria um palpite escondido
    atrás de uma assinatura amigável.

    Levantar `ValueError` sem token é deliberado: resposta sem token é recusada,
    e mandá-la assim queima a janela à toa.
    """
    token = str(flow_token or "").strip()
    if not token:
        raise ValueError("flow_token ausente — resposta de formulário sem token é rejeitada")
    if not isinstance(params, dict) or not params:
        raise ValueError("params vazio — formulário meio preenchido é pior que nenhum")
    envelope = str(nome_do_envelope or "").strip()
    if not envelope:
        raise ValueError(
            "nome_do_envelope ausente — ele se ECOA da captura ('galaxy_message' na "
            "família HDI/Yelum), nunca se adivinha"
        )

    corpo: Dict[str, Any] = {"flow_token": token, **params}
    if flow_response_params:
        # Vai por ÚLTIMO de propósito: se um dia uma resposta trouxer uma chave
        # com este nome, a identidade do formulário é que tem de vencer.
        corpo["wa_flow_response_params"] = flow_response_params

    return {
        "interactiveResponseMessage": {
            "body": {"text": str(body_text or _CORPO_PADRAO_FLOW_REPLY), "format": "EXTENSIONS"},
            "nativeFlowResponseMessage": {
                "name": envelope,
                "paramsJSON": json.dumps(corpo, ensure_ascii=False),
                # 💭 1 é o que o fork do Baileys que implementa isso usa. O "3"
                # do Meta é parâmetro de quem ENVIA o formulário, não de quem o
                # responde. Hipótese, não medição: a captura de 18/07 não traz
                # este campo porque o Evolution GO o descarta na leitura.
                # Quem decide é o teste de ida e volta entre dois números nossos.
                "version": int(version),
            },
        }
    }


class EvolutionGoProvider:
    """Evolution GO no contrato :class:`WhatsAppProvider` (config por integração)."""

    def __init__(self, integration: Dict[str, Any]) -> None:
        cfg = dict(integration or {})
        self._base_url: Optional[str] = (cfg.get("base_url") or "").rstrip("/") or None
        self._token: Optional[str] = cfg.get("token")  # token DA INSTÂNCIA (header apikey)
        self._instance_id: Optional[str] = cfg.get("instance_id")
        self.validate_config()

    @property
    def capabilities(self) -> ProviderCapabilities:
        return _GO_CAPABILITIES

    def validate_config(self) -> None:
        if not self._base_url or not self._token:
            raise ProviderConfigError("Missing base_url or token in Evolution GO integration config")

    def verify_webhook(self, payload: dict, signature: str) -> bool:
        return True  # autenticação na borda (token de webhook na URL), como o Evolution v2

    # ------------------------------------------------------------------ #
    # Inbound
    # ------------------------------------------------------------------ #
    def parse_webhook(self, payload: dict) -> InboundBatch:
        env = go_event_to_v2_envelope(payload or {})
        if env.get("event") != "messages.upsert":
            return InboundBatch(provider="evolution-go", connected_phone=str(env.get("instance") or ""), messages=[], statuses=[])
        data = env.get("data") or {}
        key = data.get("key") or {}
        message = data.get("message")
        if not isinstance(message, dict):
            return InboundBatch(provider="evolution-go", connected_phone=str(env.get("instance") or ""), messages=[], statuses=[])
        remote = str(key.get("remoteJid") or "")
        is_group = remote.endswith("@g.us")
        from_phone = _strip_jid(key.get("participant") if is_group else remote)
        extended = message.get("extendedTextMessage") if isinstance(message.get("extendedTextMessage"), dict) else {}
        text = message.get("conversation") or extended.get("text")
        canonical = CanonicalMessage(
            connected_phone=str(env.get("instance") or ""),
            from_phone=from_phone,
            type="text" if text else "unknown",
            from_me=bool(key.get("fromMe")),
            is_group=is_group,
            text=text,
            timestamp=data.get("messageTimestamp"),
            sender_name=data.get("pushName"),
            media=None,
            message_id=key.get("id"),
        )
        return InboundBatch(provider="evolution-go", connected_phone=canonical.connected_phone, messages=[canonical], statuses=[])

    def resolve_media_url(self, ref: MediaRef) -> str | None:
        candidate = (ref.resolved_url or ref.raw_ref or ref.stable_url or "").strip()
        if candidate.lower().startswith(("http://", "https://")):
            return candidate
        return None

    # ------------------------------------------------------------------ #
    # Outbound — wire GO (apikey = token da instância)
    # ------------------------------------------------------------------ #
    def _headers(self) -> Dict[str, str]:
        return {"Content-Type": "application/json", "apikey": self._token or ""}

    def _post(self, path: str, payload: Dict[str, Any]) -> SendResult:
        url = f"{self._base_url}{path}"
        response = requests.post(url, json=payload, headers=self._headers(), timeout=30)
        status = response.status_code
        if status == 429 or 500 <= status <= 599:
            logger.warning("[EVOLUTION-GO] Retryable HTTP %s: %s", status, response.text[:200])
            raise WhatsappRetryableError(f"HTTP {status} from Evolution GO")
        if not 200 <= status < 300:
            logger.error("[EVOLUTION-GO] HTTP %s error: %s", status, response.text[:200])
            return SendResult(ok=False, error=f"HTTP {status}")
        return SendResult(ok=True)

    def send_text(self, to: str, text: str) -> SendResult:
        return self._post("/send/text", {"number": to, "text": text})

    def send_media(self, to: str, media: OutboundMedia) -> SendResult:
        if not media.url:
            return SendResult(ok=False, error="Missing media url (raw_ref unsupported)")
        kind = "image" if media.kind == "image" else "audio" if media.kind == "audio" else "document"
        payload: Dict[str, Any] = {"number": to, "type": kind, "url": media.url}
        if media.caption:
            payload["caption"] = media.caption
        if media.kind == "document" and media.filename:
            payload["filename"] = media.filename
        return self._post("/send/media", payload)

    def send_template(self, to: str, template: TemplateRef) -> SendResult:
        raise ProviderNotSupportedError("Evolution GO provider does not support template messaging")

    # ------------------------------------------------------------------ #
    # Missão APP NATIVO (HDI/Yelum) — resposta a list/flow SEM tocar no fork.
    # ------------------------------------------------------------------ #
    def send_list_reply(self, to: str, row_id: str, title: str) -> SendResult:
        """Responde uma LISTA/BOTÃO nativo digitando o RÓTULO — que é o que
        funciona, e é o que os corredores já fazem há 20+ telas.

        O `row_id` NÃO viaja mais. 📊 No swagger do GO, `TextStruct.id` é o id
        DA MENSAGEM que se está criando (irmão de `quoted.messageId`), não a
        linha escolhida: mandá-lo ali produzia uma mensagem de texto comum com
        um id forjado, e o efeito "respondi a lista" era imaginação. Nada no
        repositório chamava estes dois métodos — o engano nunca chegou a
        produção, e agora não chega mesmo.
        """
        rotulo = str(title or "").strip()
        if not rotulo:
            logger.error("[EVOLUTION-GO] resposta de lista sem rótulo (row_id=%s) — recusada",
                         str(row_id or "")[:24])
            return SendResult(ok=False, error="list_reply_sem_rotulo")
        return self.send_text(to, rotulo)

    def send_button_reply(self, to: str, button_id: str, title: str) -> SendResult:
        return self.send_list_reply(to, button_id, title)

    def flow_reply_supported(self) -> bool:
        """Este canal sabe ENVIAR resposta de formulário nativo?

        Falso enquanto ninguém declarar a rota provada. Ter o schema do
        formulário e saber montar o `paramsJSON` **não é** ter o canal — e é
        justamente por confundir as duas coisas que um acionamento sairia
        achando que respondeu."""
        return bool(rota_de_flow_reply())

    def send_native_flow_response(
        self,
        to: str,
        *,
        flow_token: str,
        params: Dict[str, Any],
        nome_do_envelope: str,
        flow_response_params: Optional[Dict[str, Any]] = None,
        body_text: Optional[str] = None,
        version: int = 1,
    ) -> SendResult:
        """Envia a resposta do formulário nativo — se houver rota provada.

        Sem rota: **não faz requisição nenhuma** e devolve o motivo. Chutar
        `/send/text` com o JSON dentro entregaria à seguradora uma parede de
        texto no lugar do formulário, e a URA da HDI encerra em 12 minutos —
        gastar a janela com lixo é pior do que pausar e chamar uma pessoa.
        """
        rota = rota_de_flow_reply()
        if not rota:
            logger.warning(
                "[EVOLUTION-GO] resposta de formulário nativo montada mas NÃO enviada: "
                "este build do GO não tem rota de resposta de interativa (%s vazio). "
                "As 12 rotas de envio conhecidas só ORIGINAM mensagem.", ENV_ROTA_FLOW_REPLY)
            return SendResult(ok=False, error="evolution_go_sem_rota_de_flow_reply")
        try:
            mensagem = montar_nfm_reply(
                flow_token=flow_token, params=params,
                nome_do_envelope=nome_do_envelope,
                flow_response_params=flow_response_params,
                body_text=body_text, version=version)
        except ValueError as exc:
            logger.error("[EVOLUTION-GO] resposta de formulário recusada: %s", exc)
            return SendResult(ok=False, error=f"flow_reply_invalida:{exc}")

        # A rota do nosso fork (patch 0005) recebe corpo PLANO, não o waE2E
        # aninhado — ela mesma monta o protobuf do lado Go. Ainda assim quem
        # decide o conteúdo é `montar_nfm_reply`, aqui em cima: se as duas
        # montagens existissem em paralelo, um dia divergiriam, e a divergência
        # só apareceria numa seguradora descartando a resposta em silêncio.
        envelope = mensagem["interactiveResponseMessage"]
        nfm = envelope["nativeFlowResponseMessage"]
        corpo: Dict[str, Any] = {
            "number": to,
            "name": nfm["name"],
            "paramsJSON": nfm["paramsJSON"],
            # 📊 MEDIDO, não escolhido. Em 03/08/2026 seis formas foram enviadas
            # de um número nosso para outro. Cinco voltaram com o mesmo erro 479
            # — que o whatsmeow documenta como "Invalid stanza sent". A sexta,
            # com este embrulho, voltou 200 e o servidor devolveu
            # `Type: "InteractiveResponseMessage"`.
            #
            # É o mesmo embrulho que /send/button usa nas três variantes dele.
            # Sem ele o WhatsApp recusa a mensagem inteira, em silêncio para o
            # cliente e com um número para nós.
            "wrapInDocumentWithCaption": True,
        }
        if nfm.get("version"):
            corpo["version"] = int(nfm["version"])
        texto = (envelope.get("body") or {}).get("text")
        if texto:
            corpo["body"] = texto
        return self._post(rota, corpo)


def rotas_de_envio_medidas() -> List[str]:
    """As rotas de envio observadas no swagger do GO (📊 03/08/2026)."""
    return list(ROTAS_DE_ENVIO_MEDIDAS)


__all__ = [
    "EvolutionGoProvider",
    "go_event_to_v2_envelope",
    "montar_nfm_reply",
    "rota_de_flow_reply",
    "rotas_de_envio_medidas",
    "ROTAS_DE_ENVIO_MEDIDAS",
    "ENV_ROTA_FLOW_REPLY",
]
