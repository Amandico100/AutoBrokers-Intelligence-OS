"""
Webhook API - Recebe mensagens do WhatsApp via Z-API
Corrigido: Datas ISO e Sanitização de Logs
"""

import asyncio
import time as _tempo
import hmac
import logging
import os
import re
from datetime import date, datetime, timezone  # Importado datetime e timezone
from typing import Any, Dict, Optional
from uuid import uuid4

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel

from app.core.auth import require_master_admin
from app.core.config import settings
from app.core.database import get_supabase_client
from app.core.rate_limit import limiter
from app.core.redis import get_async_redis_client
from app.services.audio_service import AudioService

# Services
from app.services.integration_service import get_integration_service
from app.services.langchain_service import LangChainService
from app.services.message_buffer_service import (
    REPLANEJAMENTOS_MAX,
    TETO_DA_RAJADA_SEGUNDOS,
    get_message_buffer_service,
    texto_combinado_dos_itens,
)
from app.services.whatsapp.channel_security import (
    dedup_key,
    provider_matches_integration,
    validate_webhook_token_format,
    webhook_token_matches,
)
from app.services.whatsapp.evolution_inbound import (
    connection_state_from_payload,
    normalize_evolution_inbound,
)
from app.services.whatsapp.inbound_routing import pick_inbound_branch
from app.services.whatsapp_service import get_whatsapp_service

# Configuração de Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Singleton Services
supabase = get_supabase_client()
integration_service = get_integration_service(supabase.client)
whatsapp_service = get_whatsapp_service()


# ==============================================================================
# PYDANTIC MODELS (Definições de Dados)
# ==============================================================================

class ZAPITextMessage(BaseModel):
    message: str

class ZAPIAudioMessage(BaseModel):
    audioUrl: Optional[str] = None

class ZAPIImageMessage(BaseModel):
    """Imagem recebida via WhatsApp"""
    imageUrl: str
    caption: Optional[str] = None
    mimeType: Optional[str] = None

class ZAPIWebhookPayload(BaseModel):
    """Payload recebido da Z-API"""
    connectedPhone: str
    phone: str
    isGroup: bool = False
    fromMe: bool = False
    text: Optional[ZAPITextMessage] = None
    audio: Optional[ZAPIAudioMessage] = None
    image: Optional[ZAPIImageMessage] = None
    messageId: Optional[str] = None
    momment: Optional[int] = None
    senderName: Optional[str] = None

# --- MODELS QUE ESTAVAM FALTANDO ---
class AdminSendMessagePayload(BaseModel):
    """Payload para envio de mensagem pelo Admin"""
    session_id: str  # Format: whatsapp:{phone}:{company_id}:{agent_id}
    phone: str
    message: Optional[str] = None
    image_url: Optional[str] = None
    audio_url: Optional[str] = None

class StatusUpdatePayload(BaseModel):
    """Payload para atualização de status"""
    status: str  # 'open', 'HUMAN_REQUESTED', 'resolved'


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

#: 🔴 SPEC-093-B — AS DUAS MARCAS QUE O RAMO `document` ESCREVE NO TEXTO.
#:
#: Elas moram aqui, e não soltas nas f-strings do ramo, porque `nome_do_documento`
#: precisa RECONHECÊ-LAS. Uma segunda cópia da frase no reconhecedor divergiria da
#: primeira na primeira vez que alguém editasse a mensagem — e quem ficaria para trás
#: é justamente o lado que faz o documento virar evento (CLAUDE.md §5).
MARCA_DO_DOCUMENTO = "[Cliente enviou o documento: %s]"
CABECALHO_DO_DOCUMENTO = "[CONTEÚDO DO DOCUMENTO %s]"


def _padrao_da_marca(molde: str) -> "re.Pattern[str]":
    """O molde vira padrão: tudo escapado, e o `%s` vira o grupo do nome."""
    antes, depois = molde.split("%s", 1)
    return re.compile(re.escape(antes) + r"([^\]\n]{1,160})" + re.escape(depois))


_MARCAS_DO_DOCUMENTO = tuple(_padrao_da_marca(m) for m in
                             (MARCA_DO_DOCUMENTO, CABECALHO_DO_DOCUMENTO))


def nome_do_documento(texto: Any, payload_dict: Optional[dict] = None) -> Optional[str]:
    """O nome do arquivo que o segurado mandou, ou `None` se não veio arquivo.

    🔴 **Este é o BLOCKER 1 da auditoria externa de 03/09/2026.** O único escritor de
    `claims.documento_recebido` estava atrás de `if final_image_url:` — só IMAGEM. O
    ramo `document` do Evolution (o PDF do boletim de ocorrência) nunca preenche
    `image_payload`: ele entra como TEXTO. 📊 Medido em produção, nas sessões que falam
    de sinistro: **1.060 imagens e 730 documentos** inbound — 40,8% dos arquivos de um
    sinistro não viravam evento nenhum, e `contadores_de` publicava esses casos como
    `sem_documento`, um número que o Founder leria como "a operação não pede papel".

    Duas fontes, nesta ordem, porque cada uma pega o que a outra não pega:

      · `payload_dict["document"]["fileName"]` — o campo, sempre certo quando existe.
        ⚠️ Ele pode se PERDER no buffer de debounce: se uma mensagem de texto chegar
        na mesma janela de 8 s, o payload dela vence (`message_buffer_service`
        sobrescreve tudo menos `interactive`). É por isso que existe a segunda fonte.
      · a MARCA no texto — sobrevive ao buffer porque as mensagens são CONCATENADAS.
        ⚠️ E ela some quando o segurado manda legenda junto E a extração falha; é por
        isso que existe a primeira.

    ⛔ O nome NUNCA é gravado: quem o lê é `tipo_de_documento`, e o que atravessa para
    o `payload_redacted` é o enum (SPEC-093-B §2).
    """
    doc = (payload_dict or {}).get("document")
    if isinstance(doc, dict):
        nome = str(doc.get("fileName") or "").strip()
        if nome:
            return nome
    alvo = str(texto or "")
    for padrao in _MARCAS_DO_DOCUMENTO:
        achado = padrao.search(alvo)
        if achado:
            nome = achado.group(1).strip()
            if nome:
                return nome
    return None


def payload_do_pipeline(wa_message_id: Optional[str], direcao: str,
                        wa_message_ids: Optional[list] = None) -> dict:
    """O `payload` das linhas que o PIPELINE do agente grava em `messages`.

    🔴 **Por que ele existe (SPEC-EXTRA-001.2 BLOCO E1).** O índice único parcial
    `messages_espelho_sem_duplicata_uidx` existe desde 06/08/2026 sobre
    `(conversation_id, payload->>'wa_message_id')` — e as linhas do pipeline
    nasciam **sem `payload`**, logo fora do índice. 📊 Em 14/09/2026,
    33.348 de 34.682 linhas (96,2%) tinham a chave: as que faltavam eram
    justamente estas.

    ⚠️ **A forma é a MESMA do espelho** (`espelho_chat.py:_inserir_mensagem`),
    de propósito: duas grafias da mesma chave seriam duas chaves.

    ⛔ **Sem id, a chave não é inventada** — a entrada sai do dicionário e a
    linha fica fora do índice, declaradamente. Um `wa_message_id` falso faria
    duas mensagens diferentes colidirem, que é pior que nenhuma dedupe.
    """
    todos = [str(i).strip() for i in (wa_message_ids or []) if str(i or "").strip()]
    # 🔴 O PRIMEIRO id da rajada, não o último (J7, 14/09/2026).
    #
    # 📊 O defeito: a linha COMBINADA do pipeline entrava no índice com o id da
    # ÚLTIMA mensagem da rajada, e o espelho grava cada mensagem com o SEU id,
    # na MESMA conversa (E2). Quem chegasse depois levava 23505 — e se o
    # perdedor fosse o pipeline, era o TEXTO COMBINADO que se perdia, ficando
    # no chat só a última frase solta. Os N−1 ids ficavam fora do índice, então
    # a reentrega da Meta de qualquer um deles virava linha nova.
    #
    # ⚠️ O PRIMEIRO id porque ele é o mais antigo da rajada: é o que o espelho
    # tende a espelhar primeiro, e é o que torna a colisão determinística em
    # vez de depender de quem terminou antes.
    chave = str(wa_message_id or "").strip() or (todos[0] if todos else "")
    saida = {"origem": "agente", "direcao": str(direcao or "")}
    if chave:
        saida["wa_message_id"] = chave
    if todos:
        # ⛔ TODOS os ids da rajada. É a lista que o espelho consulta para não
        # escrever de novo o que já está no chat como texto combinado.
        saida["wa_message_ids"] = todos
    return saida


def e_duplicata_do_banco(erro: Any) -> bool:
    """O banco disse *"esta mensagem já está aqui"*? — **PURA**.

    `23505` é o índice único parcial funcionando, não uma falha. A mesma
    leitura que `espelho_chat.py:571-579` faz desde 13/08/2026.
    """
    texto = str(erro or "")
    return "23505" in texto or "duplicate key" in texto.lower()


async def gravar_mensagem_do_pipeline(
    supabase_client, *, dados: dict, wa_message_id: Optional[str], direcao: str,
    wa_message_ids: Optional[list] = None,
) -> str:
    """Grava UMA linha em `messages` e deixa o BANCO responder se ela já estava.

    Devolve `"gravada"` ou `"ja_estava"`; **nunca levanta** por duplicata —
    ⚠️ qualquer outro erro sobe, porque banco fora do ar não é dedupe.

    🔴 É o ÚNICO escritor de `messages` do pipeline: os dois inserts
    (mensagem do segurado e resposta da IA) passam por aqui, e é isso que faz a
    chave existir nos dois lados sem duas grafias.
    """
    linha = dict(dados or {})
    linha["payload"] = payload_do_pipeline(wa_message_id, direcao, wa_message_ids)

    # =====================================================================
    # \U0001F534 O ID QUE J\u00c1 EST\u00c1 DENTRO DE UMA LINHA COMBINADA (J7, 14/09/2026)
    # =====================================================================
    #
    # O \u00edndice \u00fanico cobre UM id por linha (`payload->>'wa_message_id'`). Uma
    # linha combinada representa N mensagens, e as outras N\u22121 ficam fora dele:
    # a reentrega da Meta de qualquer uma delas viraria uma linha nova, com o
    # texto repetido no chat da corretora.
    #
    # \u26a0\ufe0f **Uma consulta por TURNO de entrada** \u2014 n\u00e3o por mensagem, e nenhuma
    # nas de sa\u00edda. \u26d4 E fail-open: n\u00e3o conseguir consultar nunca pode custar
    # a mensagem do segurado; o \u00edndice continua sendo a garantia dura.
    chave_unica = str(wa_message_id or "").strip()
    if str(direcao or "") == "in" and chave_unica and linha.get("conversation_id"):
        try:
            ja = await asyncio.to_thread(
                lambda: supabase_client.table("messages").select("id")
                .eq("conversation_id", linha["conversation_id"])
                .contains("payload->wa_message_ids", [chave_unica])
                .limit(1).execute()
            )
            if getattr(ja, "data", None):
                return "ja_estava"
        except Exception as erro_lista:  # noqa: BLE001
            logger.debug("[MESSAGES] consulta de wa_message_ids falhou (%s)",
                         type(erro_lista).__name__)
    try:
        await asyncio.to_thread(
            lambda: supabase_client.table("messages").insert(linha).execute()
        )
    except Exception as erro:  # noqa: BLE001
        if e_duplicata_do_banco(erro):
            return "ja_estava"
        raise
    return "gravada"


async def _conversa_da_contraparte(
    supabase_client, *, company_id: str, contraparte: str,
    channel: str = "whatsapp", agent_id=None,
):
    """A conversa ABERTA desta contraparte — a MESMA chave do índice único.

    🔴 As quatro cláusulas são as do `uq_conversations_contraparte_aberta`
    (M2): `company_id`, `contraparte`, canal WhatsApp, `agent_id IS NULL` e
    `status <> 'closed'`. ⚠️ Escrever essa chave duas vezes com grafias
    diferentes seria ter duas chaves — por isso a busca do começo e a releitura
    do 23505 são a MESMA função.
    """
    if not contraparte:
        return None
    busca = (
        supabase_client.table("conversations")
        .select("id, unread_count")
        .eq("company_id", company_id)
        .eq("contraparte", contraparte)
        .eq("channel", channel)
        .neq("status", "closed")
    )
    if agent_id:
        busca = busca.eq("agent_id", agent_id)
    else:
        busca = busca.is_("agent_id", "null")
    achado = await asyncio.to_thread(lambda: busca.limit(1).execute())
    linhas = getattr(achado, "data", None) or []
    return linhas[0] if linhas else None


async def get_or_create_conversation(
    supabase_client,
    company_id: str,
    user_id: str,
    session_id: str,
    message_text: str,
    payload: ZAPIWebhookPayload,
    channel: str = "whatsapp",
    agent_id: Optional[str] = None,
) -> str:
    try:
        # 🔴 A CONTRAPARTE — a chave que faz a fantasma nº 176 não nascer.
        #
        # 📊 13/09/2026: 175 conversas-fantasma de `@lid`, 100% abertas, 10 com
        # pausa de atendente presa. O `session_id` UNIQUE não as impedia — o
        # `@lid` gera um `session_id` diferente e a fantasma nasce legalmente.
        #
        # ⚠️ A busca por contraparte vem ANTES da busca por `user_id` porque é
        # ela que atravessa as duas resoluções (esta e a do espelho). `user_id`
        # continua valendo como segunda tentativa: conversa antiga, criada antes
        # do backfill, ainda não tem `contraparte`.
        from app.services.whatsapp.identidade_do_evento import contraparte_de

        contraparte = contraparte_de(payload.phone)
        conversa_por_contraparte = await _conversa_da_contraparte(
            supabase_client, company_id=company_id, contraparte=contraparte,
            channel=channel, agent_id=agent_id)

        # Tentar encontrar conversa existente
        query = (
            supabase_client.table("conversations")
            .select("id, unread_count")
            .eq("company_id", company_id)
            .eq("user_id", user_id)
            .eq("channel", channel)
        )

        if agent_id:
            query = query.eq("agent_id", agent_id)
        else:
            query = query.is_("agent_id", "null")

        # Non-blocking DB call
        if conversa_por_contraparte is not None:
            existentes = [conversa_por_contraparte]
        else:
            response = await asyncio.to_thread(lambda: query.limit(1).execute())
            existentes = getattr(response, "data", None) or []

        # CORREÇÃO: Data em formato ISO UTC
        current_time_iso = datetime.now(timezone.utc).isoformat()

        if existentes:
            conv = existentes[0]
            conversation_id = conv["id"]
            current_unread = conv.get("unread_count") or 0

            await asyncio.to_thread(
                lambda: supabase_client.table("conversations").update(
                    {
                        "last_message_preview": message_text[:100],
                        "last_message_at": current_time_iso, # FIX: Não usar string "now()"
                        "unread_count": current_unread + 1,
                    }
                ).eq("id", conversation_id).execute()
            )
            return conversation_id

        # Criar nova conversa
        logger.info(f"[CONVERSATION] Creating new conversation for user {user_id}")
        new_conv = {
            "company_id": company_id,
            "user_id": user_id,
            "session_id": session_id,
            "agent_id": agent_id,
            "user_name": payload.senderName or "Usuário WhatsApp",
            "user_phone": payload.phone,
            # 🔴 A chave única da contraparte (SPEC-EXTRA-001.2 E2). `None`
            # quando o telefone não é telefone (um `@lid` cru): o índice único
            # parcial ignora NULL, então a linha nasce sem bloquear ninguém —
            # e sem ser reusada como se fosse alguém.
            "contraparte": contraparte or None,
            "channel": channel,
            "agent_name": "AutoBrokers",
            "status": "open",
            "status_color": "green",
            "unread_count": 1,
            "last_message_preview": message_text[:100],
            "last_message_at": current_time_iso, # FIX: Data correta
        }

        try:
            insert_response = await asyncio.to_thread(
                lambda: supabase_client.table("conversations").insert(new_conv).execute()
            )
        except Exception as erro_insert:  # noqa: BLE001
            # =================================================================
            # 🔴 23505 AQUI É CORRIDA, NÃO FALHA — J4, 14/09/2026
            # =================================================================
            #
            # O índice `uq_conversations_contraparte_aberta` nasceu na M2 desta
            # mesma SPEC. Ele impede a conversa duplicada — e passou a poder
            # RECUSAR este insert, porque há DOIS resolvedores para a mesma
            # contraparte: este e o do espelho (`espelho_chat._trabalho`). Uma
            # mensagem que chega pelo pipeline enquanto o espelho cria a linha
            # (ou vice-versa) leva 23505.
            #
            # ⛔ Deixar o erro subir mata o turno em SILÊNCIO: quem chamou está
            # no passo 4, antes de gravar a mensagem e antes de gerar — o
            # segurado não recebe nada. E o índice acabou de dizer, com todas
            # as letras, que a conversa que este código queria criar JÁ EXISTE.
            #
            # 🔴 Relê pela MESMA chave do índice. Se a leitura não achar (o
            # dono da corrida pode ter fechado a conversa no meio), o erro
            # sobe — nunca se inventa um id.
            if not e_duplicata_do_banco(erro_insert):
                raise
            logger.info("[CONVERSATION] 23505 na criação — outra rodada criou a "
                        "conversa desta contraparte primeiro; relendo")
            relido = await _conversa_da_contraparte(
                supabase_client, company_id=company_id, contraparte=contraparte,
                channel=channel, agent_id=agent_id)
            if relido:
                return relido["id"]
            raise

        if insert_response.data:
            return insert_response.data[0]["id"]

        raise Exception("Failed to create conversation")

    except Exception as e:
        logger.error(f"[CONVERSATION] Error in get_or_create: {str(e)}")
        raise


# ===== HELPER: PROCESS IMAGE (VISION) =====
# ---------------------------------------------------------------------------
# 🔴 URL DE MIDIA QUE REALMENTE ABRE — consertado em 17/08/2026.
#
# 📊 O defeito, medido no primeiro teste de atendimento da Resulta: o segurado
# mandou uma foto, o arquivo SUBIU certinho para `chat-media` (esta no bucket,
# 22:54:20), e a atendente respondeu *"essa imagem nao chegou ate mim com
# conteudo visivel"*.
#
# A causa: `chat-media`, `chat-docs` e `voice-messages` sao buckets PRIVADOS
# (`storage.buckets.public = false`, conferido no banco), e o codigo pedia
# `get_public_url()`. Isso devolve um endereco bem-formado que responde 400.
#
# Dai em diante tudo falha em silencio:
#   1. `process_image_for_vision` BAIXA a URL que acabou de criar -> 400 ->
#      `raise_for_status` -> devolve None
#   2. sem URL, o bloco de visao nem roda
#   3. e o modelo, que recebe a imagem COMO URL (`vision_service.py:107`),
#      tambem nao conseguiria busca-la
#
# Uma linha errada, tres caminhos mortos, nenhuma mensagem de erro para quem
# estava testando.
#
# 7 dias e o mesmo prazo do boleto assinado (`billing_collection.TEST_LINK_TTL`)
# — a conversa precisa continuar abrindo a foto depois, no painel.
_TTL_MIDIA_S = 7 * 24 * 60 * 60


def _url_de_midia(client, bucket: str, file_path: str) -> Optional[str]:
    """URL assinada. Cai para a publica so em bucket realmente publico."""
    try:
        assinada = client.storage.from_(bucket).create_signed_url(file_path, _TTL_MIDIA_S)
        url = (assinada or {}).get("signedURL") or (assinada or {}).get("signedUrl")
        if url:
            return url if url.startswith("http") else f"{settings.SUPABASE_URL}/storage/v1{url}"
    except Exception as e:  # noqa: BLE001
        logger.warning("[MIDIA] assinatura falhou em %s (%s) — tentando publica",
                       bucket, type(e).__name__)
    return client.storage.from_(bucket).get_public_url(file_path)


# =============================================================================
# 🔴 A FOTO GRANDE — o descarte em silêncio
# =============================================================================
#
# O teto era 5 MB e o `return None` era mudo. Do lado do segurado: ele
# fotografou o para-choque com um celular moderno, apertou enviar, e não voltou
# NADA. Nem a análise, nem um pedido de outra foto, nem um erro. E a foto de
# dano é justamente a mensagem que ele mais precisa que chegue.
#
# ⚠️ 5 MB não é limite de lugar nenhum: o WhatsApp aceita até 16 MB de mídia, e
# é esse o número que descreve o que pode entrar pela porta. O limite do modelo
# de visão é OUTRO (≈5 MB) e mora dentro — por isso são duas constantes, não
# uma. Confundi-las foi o que fez o produto recusar o que o canal entrega.
_LIMITE_DO_WHATSAPP_BYTES = 16 * 1024 * 1024
_LIMITE_DA_VISAO_BYTES = 5 * 1024 * 1024

# ⛔ Sentinela, e não `None`, porque `None` é o que o chamador já usa para
# "falhou e eu não sei explicar". Foto grande demais é a única falha aqui que o
# produto sabe explicar em português — e explicar é a diferença entre um
# segurado atendido e um segurado no vácuo. Um objeto próprio (comparado com
# `is`) não pode ser confundido com uma URL de verdade.
FOTO_GRANDE_DEMAIS = "__foto_grande_demais__"

# A frase que o segurado lê. Sem jargão, sem código de erro, e ela pede a
# PRÓXIMA AÇÃO — porque avisar sem dizer o que fazer devolve o problema para
# quem já está no acostamento.
AVISO_DE_AUDIO_ILEGIVEL = (
    "Não consegui ouvir o seu áudio agora. Pode me escrever em poucas palavras "
    "o que aconteceu?"
)

AVISO_DE_FOTO_GRANDE = (
    "Recebi a sua foto, mas ela veio grande demais e não consegui abrir aqui. "
    "Pode mandar de novo em tamanho menor, ou tirar outra pela câmera do "
    "WhatsApp mesmo?"
)


def _encolher_para_a_visao(image_bytes: bytes, limite: int) -> "bytes | None":
    """Recomprime a foto até caber em `limite`. `None` = não deu (ou sem Pillow).

    ⚠️ Pillow **não** está em `requirements.txt` e esta SPEC não adiciona
    dependência (o Dockerfile instala só o que está lá). Então o import é
    condicional e a ausência dele não é erro: sem Pillow o produto ainda ganha o
    teto de 16 MB e o aviso humano; com Pillow, ganha também a foto grande
    ATENDIDA em vez de recusada. Um caminho a mais, nenhum caminho a menos.
    """
    try:
        from PIL import Image  # opcional de propósito: pode não estar instalado
    except Exception:  # noqa: BLE001
        logger.info("[VISION] Pillow ausente — sem redução; vale só o teto de tamanho")
        return None

    import io

    # Qualidade primeiro, tamanho depois: o que o modelo lê é o DETALHE (placa,
    # trinca, número do chassi), e reduzir pixel destrói detalhe antes de
    # destruir peso. Só encolhe de verdade quando recomprimir não bastou.
    dados = None
    for escala, qualidade in ((1.0, 82), (1.0, 68), (0.75, 75), (0.55, 70), (0.4, 65)):
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                img = img.convert("RGB")
                if escala != 1.0:
                    largura = max(1, int(img.width * escala))
                    altura = max(1, int(img.height * escala))
                    img = img.resize((largura, altura))
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=qualidade, optimize=True)
                dados = buffer.getvalue()
        except Exception as e:  # noqa: BLE001
            logger.warning("[VISION] redução falhou (%s)", type(e).__name__)
            return None
        if len(dados) <= limite:
            return dados
    return None


async def process_image_for_vision(
    image_url: str, company_id: str, supabase_client
) -> Optional[str]:
    try:
        logger.debug(f"[VISION] Downloading image from: {image_url}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(image_url)
            response.raise_for_status()
            image_bytes = response.content

        # Acima do que o próprio canal entrega, não há o que fazer com os bytes
        # — mas há o que dizer a quem enviou. 📊 Log sem PII: só o tamanho.
        if len(image_bytes) > _LIMITE_DO_WHATSAPP_BYTES:
            logger.warning("[VISION] foto acima do limite do canal: %d bytes (teto %d)",
                           len(image_bytes), _LIMITE_DO_WHATSAPP_BYTES)
            return FOTO_GRANDE_DEMAIS

        # ⚠️ Entre 5 MB e 16 MB a foto PASSA — reduzida quando dá, inteira
        # quando não dá. Não reduzir custa o CONTEXTO VISUAL (o modelo recusa e
        # o `except` do chamador segue sem ele); recusar a foto custa a FOTO,
        # que a atendente veria no chat. O barato aqui é o caminho que entrega
        # alguma coisa, não o que devolve nada.
        if len(image_bytes) > _LIMITE_DA_VISAO_BYTES:
            menor = await asyncio.to_thread(
                _encolher_para_a_visao, image_bytes, _LIMITE_DA_VISAO_BYTES
            )
            if menor is None:
                logger.warning("[VISION] foto de %d bytes acima do limite do modelo e "
                               "não reduzida — segue para o storage assim mesmo",
                               len(image_bytes))
            else:
                logger.info("[VISION] foto reduzida de %d para %d bytes",
                            len(image_bytes), len(menor))
                image_bytes = menor

        # Gerar caminho único
        today = date.today().isoformat()
        file_id = str(uuid4())
        file_path = f"{company_id}/{today}/{file_id}.jpg"

        # Upload
        await asyncio.to_thread(
            lambda: supabase_client.storage.from_("chat-media").upload(
                file_path,
                image_bytes,
                {"content-type": "image/jpeg", "cache-control": "3600"},
            )
        )

        # URL pública
        public_url = _url_de_midia(supabase_client, "chat-media", file_path)
        logger.info(f"[VISION] Uploaded image: {public_url}")
        return public_url

    except Exception as e:
        logger.error(f"[VISION] Error processing image: {str(e)}")
        return None


# ===== HELPER: PROCESS AUDIO (STORAGE) =====
async def process_audio_for_storage(
    audio_url: str, company_id: str, supabase_client
) -> Optional[str]:
    try:
        logger.debug(f"[AUDIO STORAGE] Downloading audio from: {audio_url}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(audio_url)
            response.raise_for_status()
            audio_bytes = response.content

        file_id = str(uuid4())
        today = date.today().isoformat()
        file_path = f"{company_id}/{today}/{file_id}.ogg"

        await asyncio.to_thread(
            lambda: supabase_client.storage.from_("voice-messages").upload(
                file_path,
                audio_bytes,
                {"content-type": "audio/ogg", "cache-control": "3600"},
            )
        )

        public_url = _url_de_midia(supabase_client, "voice-messages", file_path)
        logger.info(f"[AUDIO STORAGE] Saved audio: {public_url}")
        return public_url

    except Exception as e:
        logger.error(f"[AUDIO STORAGE] Error processing audio: {str(e)}")
        return None


# ==============================================================================
# 42W0 — Attendance Runtime bridge (flag-gated; default OFF)
# ==============================================================================
# MAIN BACKGROUND TASK
# ==============================================================================
async def _midia_do_turno(itens, *, company_id, agent_id, supabase_client,
                          is_human_mode: bool):
    """Descreve as imagens e transcreve os áudios DO TURNO. `(texto, url)`.

    🔴 SPEC-EXTRA-001.2 §6.2 — a descrição e a transcrição saíam no WEBHOOK,
    num turno próprio por arquivo. Agora saem AQUI, dentro do turno que já tem
    a rajada inteira: o modelo lê a foto e a frase que a explica de uma vez.

    ⚠️ Nada de motor novo: são as MESMAS `process_image_for_vision`,
    `describe_image` e `AudioService.transcribe_audio_from_url` de sempre.
    ⛔ Falha de mídia não derruba o turno — o texto do segurado ainda vale.
    """
    pedacos = []
    url_da_imagem = None
    for item in itens or []:
        tipo = str((item or {}).get("tipo") or "").strip().lower()
        midia = (item or {}).get("midia") or {}
        if tipo == "image" and midia.get("imageUrl"):
            try:
                url = await process_image_for_vision(
                    midia["imageUrl"], company_id, supabase_client)
                if url is FOTO_GRANDE_DEMAIS:
                    pedacos.append(
                        "[o cliente enviou uma foto grande demais para eu abrir]")
                    continue
                if not url:
                    continue
                url_da_imagem = url
                if is_human_mode:
                    continue
                from app.services.vision_service import describe_image

                visao = await describe_image(
                    url, company_id=str(company_id),
                    agent_id=str(agent_id) if agent_id else None,
                    purpose_hint="Atendente de corretora falando com o segurado")
                if visao:
                    pedacos.append(
                        "[CONTEXTO VISUAL — imagem enviada pelo cliente]:\n%s" % visao)
            except Exception as erro:  # noqa: BLE001
                logger.error("[WEBHOOK] visão do turno falhou (%s)", type(erro).__name__)
        elif tipo == "audio" and midia.get("audioUrl") and not is_human_mode:
            try:
                audio_service = AudioService(settings.OPENAI_API_KEY)
                transcrito = await audio_service.transcribe_audio_from_url(
                    midia["audioUrl"], company_id=company_id, agent_id=agent_id)
                if transcrito:
                    pedacos.append(str(transcrito))
            except Exception as erro:  # noqa: BLE001
                # ⛔ O mesmo desfecho do ramo de áudio de sempre: o produto NÃO
                # fala de si para quem acabou de descrever uma batida.
                logger.error("[WEBHOOK] transcrição do turno falhou (%s)",
                             type(erro).__name__)
    return "\n\n".join(p for p in pedacos if p), url_da_imagem


async def _presenca(integration: dict, phone: str, estado: str,
                    delay_ms: int = 0) -> None:
    """"digitando…" — e a regra que impede a promessa vazia (§6.4).

    🔴 Só é chamada DEPOIS do portão de silêncio. E02 é literal: *"only display
    a typing indicator if you are going to respond."* ⛔ Nunca se simula
    "digitando…" com uma mensagem de texto.
    """
    if not getattr(settings, "PRESENCA_DIGITANDO_LIGADA", False):
        return
    try:
        await asyncio.to_thread(
            whatsapp_service.send_presence, phone, estado, integration,
            min(int(delay_ms or 0), TETO_DA_RAJADA_SEGUNDOS * 1000),
        )
    except Exception as erro:  # noqa: BLE001
        # ⛔ Presença é enfeite. Um erro aqui nunca pode custar a RESPOSTA.
        logger.debug("[PRESENCA] não enviada (%s)", type(erro).__name__)


# =============================================================================
# 🔴 O TURNO SE RENOVA — e a rajada NUNCA é jogada fora (J2, 14/09/2026)
# =============================================================================
#
# 📊 O defeito medido: `renovar_turno` existia em
# `message_buffer_service.py` e **não tinha um chamador no produto inteiro**
# (`grep` = 0 fora dos testes). Um turno que passasse dos 90 s de TTL perdia a
# posse, caía no `return` seco daqui de baixo — e o buffer já tinha sido
# consumido pelo `get_and_clear` do varredor. A rajada inteira do segurado
# sumia e **ninguém respondia**.
#
# ⚠️ O contador é uma lista de propósito: ele atravessa as chamadas dentro do
# mesmo turno sem virar `global` nem atributo de objeto.
async def _renovar_o_turno(turno, contador: list) -> bool:
    """Estende o TTL do turno — E01: só o dono estende, e há TETO.

    ⛔ Nunca levanta. Devolve `True` se renovou (ou se não havia turno a
    renovar, que é o caminho do dublê sem trava).
    """
    if turno is None:
        return True
    try:
        from app.services.message_buffer_service import (
            TURNO_RENOVACOES_MAX, get_message_buffer_service,
        )

        feitas = int(contador[0] if contador else 0)
        if feitas >= TURNO_RENOVACOES_MAX:
            return False
        servico = await get_message_buffer_service()
        ok = await servico.renovar_turno(
            turno.escopo, turno.phone, turno.token, renovacoes_feitas=feitas)
        if ok and contador:
            contador[0] = feitas + 1
        return bool(ok)
    except Exception as erro:  # noqa: BLE001
        logger.debug("[TURNO] renovação não aconteceu (%s)", type(erro).__name__)
        return False


async def process_whatsapp_message_background(
    payload_dict: dict, combined_message: Optional[str] = None,
    buffered_messages: Optional[list] = None,
    *,
    turno=None, chave_do_buffer: str = "",
    buffered_items: Optional[list] = None,
):
    """Processa mensagem WhatsApp em background (Evita bloqueio do Webhook)"""
    # AS DUAS CONDIÇÕES DO FALLBACK — ver o `except` no fim desta função.
    #
    # Uma exceção no caminho da IA deixava o segurado em SILÊNCIO TOTAL: o
    # `except` de fora só logava. O ramo de áudio, dez passos acima, sempre
    # avisou ("Erro ao processar áudio"); o caminho principal, não. A pessoa
    # mandava a mensagem e nada voltava — nunca.
    #
    # Mas avisar tem duas pré-condições, e nenhuma pode ser presumida:
    #
    #   `_pode_falar_ao_cliente`  o PORTÃO DE SILÊNCIO já autorizou. Falar por
    #                             uma corretora em modo observação não é
    #                             recuperável (é o mesmo raciocínio do passo
    #                             6.5). Enquanto o portão não passou, o padrão
    #                             é calar — inclusive no erro.
    #   `_resposta_ja_enviada`    a resposta do agente já saiu. Uma exceção
    #                             DEPOIS do envio (métrica, preview, billing)
    #                             não pode virar um segundo balão dizendo que
    #                             deu errado quando deu certo.
    _pode_falar_ao_cliente = False
    _resposta_ja_enviada = False
    try:
        # LOG SANITIZADO: Apenas último 4 dígitos do telefone
        safe_phone = f"...{str(payload_dict.get('phone', ''))[-4:]}"
        logger.info(f"[WEBHOOK BG] Processing for {safe_phone}")

        payload = ZAPIWebhookPayload(**payload_dict)

        # 1. Resolver Integração
        # SPEC-017 P1.2: rotas com token por integração já resolveram o tenant —
        # o id viaja no payload (inclusive pelo buffer) e tem prioridade sobre a
        # resolução legada por connectedPhone (forjável).
        integration = None
        pinned_integration_id = payload_dict.get("_integration_id")
        if pinned_integration_id:
            integration = integration_service.get_integration_by_id(str(pinned_integration_id))
        if not integration:
            integration = integration_service.get_integration_by_phone(payload.connectedPhone)
        if not integration:
            logger.error(f"[WEBHOOK] No integration found for {payload.connectedPhone}")
            return

        company_id = integration["company_id"]
        agent_id = integration.get("agent_id")

        # CARTÓGRAFO (SPEC-034): com CARTOGRAPHER_MODE=1 e exploração ATIVA para
        # este número de seguradora, o mapeador consome a mensagem — antes do
        # motor de acionamento (que continua tendo prioridade via checagem no
        # start_exploration). Mesmo número pareado, zero re-pareamento.
        try:
            from app.services.cartographer_runner import (
                cartographer_mode_enabled,
                handle_cartographer_inbound,
            )

            if cartographer_mode_enabled():
                _carto_texts = [m for m in (buffered_messages or []) if str(m or "").strip()]
                _carto_text = "\n".join(_carto_texts) if _carto_texts else (
                    payload.text.message if payload.text and payload.text.message else "")
                _carto_handled = await handle_cartographer_inbound(
                    str(payload.phone or ""),
                    _carto_text,
                    lambda text_out: whatsapp_service.send_message(payload.phone, text_out, integration),
                )
                if _carto_handled:
                    logger.info("[WEBHOOK] inbound consumido pelo CARTOGRAFO (exploracao ativa)")
                    return
        except Exception as e:  # noqa: BLE001 — cartógrafo nunca derruba o fluxo
            logger.error(f"[WEBHOOK] cartographer runner error: {type(e).__name__}")

        # SPEC-017 P5/P6: se este inbound vem do NÚMERO DA SEGURADORA com um
        # dispatch ATIVO, é a URA/especialista respondendo — roteia para o motor
        # de acionamento e NÃO para o agente de atendimento.
        try:
            from app.services.dispatch_router import try_route_insurer_inbound

            # ⚠️ ESTES TRÊS NÃO GANHARAM `to_thread`, E É DE PROPÓSITO.
            #
            # `_send_to_insurer`, `_send_to_client` e o lambda do cartógrafo são
            # funções SÍNCRONAS entregues a outro motor, que as chama como
            # `callable(...)`. Embrulhar em `to_thread` faria cada uma devolver
            # uma corrotina que ninguém aguarda — o envio simplesmente não
            # aconteceria, e o corredor da seguradora pararia em silêncio. O
            # conserto certo delas é mudar o CONTRATO do chamador (aceitar
            # awaitable), que é obra de outra SPEC e não véspera de piloto.
            #
            # Por isso o guarda de `to_thread` mira só a chamada DIRETA no corpo
            # do `async def`: é lá que o defeito é real e o conserto é local.
            def _send_to_insurer(text_out: str) -> None:
                whatsapp_service.send_message(payload.phone, text_out, integration)

            def _send_to_client(client_phone: str, text_out: str) -> None:
                whatsapp_service.send_message(client_phone, text_out, integration)

            def _responder_formulario_nativo(**kwargs) -> bool:
                """O transporte da resposta de formulário nativo — a última ponte.

                O motor já sabia montar a resposta: lê o schema do formulário,
                preenche os campos com a ficha do atendimento e ecoa o envelope da
                captura. Só não tinha por onde entregá-la. Sem esta função,
                `flow_sender` chegava `None` e **todo** formulário virava
                `formulario_pronto_sem_transporte` — parado, esperando uma pessoa,
                com a resposta pronta ao lado.

                📊 A rota existe desde o patch 0005 e foi provada no ar em
                03/08/2026. Falha aqui devolve False, nunca exceção: o motor
                trata False pausando para humano, que é o desfecho certo — e uma
                exceção subindo derrubaria o inbound inteiro.
                """
                try:
                    provider_nome = str((integration or {}).get("provider") or "").strip().lower()
                    if provider_nome != "evolution-go":
                        logger.warning("[WEBHOOK] formulario nativo pedido em provider %s", provider_nome)
                        return False
                    from app.services.whatsapp.providers.evolution_go import EvolutionGoProvider

                    resultado = EvolutionGoProvider(integration).send_native_flow_response(
                        str(payload.phone or ""), **kwargs
                    )
                    if not getattr(resultado, "ok", False):
                        logger.error("[WEBHOOK] formulario nativo recusado: %s",
                                     getattr(resultado, "error", "sem motivo"))
                        return False
                    return True
                except Exception as e:  # noqa: BLE001
                    logger.error("[WEBHOOK] transporte de formulario falhou: %s", type(e).__name__)
                    return False

            async def _human_reply_provider(dispatch_session, insurer_text):
                # Fase humana da seguradora: LLM plataforma redige; o guard do
                # roteador fiscaliza. Qualquer falha aqui → None (acumula, nunca
                # responde às cegas).
                try:
                    from langchain_core.messages import HumanMessage, SystemMessage

                    from app.core.utils import get_api_key_for_provider
                    from app.factories.llm_factory import LLMFactory
                    from app.services.insurer_dispatch_service import build_human_phase_messages

                    # CÉREBRO v2 (SPEC-034): passa o Mapa de URA ativo quando existir.
                    _ura_map = None
                    try:
                        from app.services.corridor_playbooks import get_playbook as _get_pb
                        from app.services.ura_map_service import get_active_map as _gam

                        _pb = _get_pb(str(dispatch_session.get("playbook_ref") or "")) or {}
                        _row = await _gam(str(_pb.get("insurer_key") or ""),
                                          str(_pb.get("line_kind") or "auto"))
                        _ura_map = (_row or {}).get("map")
                    except Exception:  # noqa: BLE001
                        _ura_map = None
                    msgs = build_human_phase_messages(dispatch_session, insurer_text, ura_map=_ura_map)
                    # Cérebro da fase humana do dispatch: forte por padrão, com
                    # override por env (DISPATCH_LLM_PROVIDER/DISPATCH_LLM_MODEL).
                    import os as _os
                    d_provider = _os.getenv("DISPATCH_LLM_PROVIDER") or "openai"
                    d_model = _os.getenv("DISPATCH_LLM_MODEL") or "gpt-4o"
                    llm = LLMFactory.create_llm(
                        company_config={},
                        agent_data={"llm_provider": d_provider, "llm_model": d_model},
                        api_key=get_api_key_for_provider(d_provider, d_model),
                        company_id=str(company_id),
                        agent_id=None,
                    )
                    result = await llm.ainvoke(
                        [SystemMessage(content=msgs["system"]), HumanMessage(content=msgs["user"])]
                    )
                    return getattr(result, "content", None)
                except Exception as e:  # noqa: BLE001
                    logger.error(f"[WEBHOOK] human phase LLM failed: {type(e).__name__}")
                    return None

            # A URA manda RAJADAS (menu em 2-3 mensagens): o buffer junta, mas o
            # motor precisa ver CADA mensagem em ordem — a última pode ser filler
            # ("aguarde") e o menu real estar na primeira.
            #
            # 📊 E era só isso que acontecia: o buffer juntava a rajada e este
            # laço a DESJUNTAVA, chamando o motor uma vez por bolha. Em 34,1% dos
            # turnos chegam 2+ mensagens, e neles a pergunta está na ÚLTIMA em
            # 68,1% das vezes (medido em 05/08/2026 sobre o tráfego real das
            # seguradoras). O modelo respondia a primeira bolha — quase sempre um
            # "aguarde" — e já tinha falado quando o menu de verdade chegou.
            #
            # O conserto NÃO é juntar tudo num texto só: o determinístico perderia
            # o menu que veio na primeira. É separar os dois tempos —
            # `ainda_vem_mais=True` deixa a mensagem passar pelo determinístico e
            # apenas se acumular; só a ÚLTIMA do turno abre a deliberação, e aí
            # sobre a tela inteira. Ver `dispatch_router._tela_do_turno`.
            _dispatch_texts = [m for m in (buffered_messages or []) if str(m or "").strip()]
            if not _dispatch_texts and payload.text and payload.text.message:
                _dispatch_texts = [payload.text.message]
            handled = False
            _rajada = _dispatch_texts or [""]
            for _i, _msg in enumerate(_rajada):
                handled = await try_route_insurer_inbound(
                    company_id=str(company_id),
                    from_phone=str(payload.phone or ""),
                    text=str(_msg or ""),
                    send_to_insurer=_send_to_insurer,
                    send_to_client=_send_to_client,
                    human_reply_provider=_human_reply_provider,
                    # A ponte entre "o corredor sabe responder" e "o corredor
                    # responde". Era sempre None, e por isso nenhum formulário
                    # nativo jamais foi respondido em produção.
                    # 🔴 O canal por onde a conversa entrou vai JUNTO.
                    # Sem ele, quem retomar a conversa depois (o Sentinela, no
                    # relogio) nao tem por onde falar. Ver dispatch_router.
                    integration_id=str((integration or {}).get("id") or ""),
                    flow_sender=_responder_formulario_nativo,
                    # SPEC-063 — o `interactive` precisa ATRAVESSAR.
                    #
                    # Só o texto chegava aqui, e o `flow_token` mora no
                    # `interactive` da mensagem. Sem ele o motor sabe montar a
                    # resposta do formulário nativo e não tem como endereçá-la.
                    # É a última ponte entre "o corredor sabe" e "o corredor faz"
                    # — e é uma linha.
                    interactive=(payload_dict or {}).get("interactive"),
                    # A tela ainda não terminou de chegar.
                    ainda_vem_mais=(_i < len(_rajada) - 1),
                ) or handled
                if not handled:
                    break  # sem sessão ativa para este número — segue fluxo normal
            if handled:
                logger.info("[WEBHOOK] inbound routed to dispatch engine (insurer conversation)")
                return
        except Exception as e:  # noqa: BLE001 — roteador nunca derruba o fluxo normal
            logger.error(f"[WEBHOOK] dispatch router error: {type(e).__name__}")

        # 🔴 SPEC-EXTRA-001.4 C · D3 — duas mensagens que NÃO são para o agente:
        #    ① AGENTE / EU CUIDO de alguém da equipe (o número de suporte ou um
        #       número da casa), sobre o acionamento em pausa;
        #    ② a RESPOSTA do segurado a uma pergunta que a seguradora fez.
        #    Custo no caminho comum: um teste de texto (①) e um GET no Redis (②).
        try:
            from app.services.dispatch_router import (
                ler_palavra_da_equipe, responder_pergunta_do_acionamento,
            )

            _texto_in = " ".join(str(m or "").strip() for m in (buffered_messages or [])
                                 if str(m or "").strip())
            if not _texto_in and payload.text and payload.text.message:
                _texto_in = str(payload.text.message)
            # ⚠️ Só a palavra APLICADA encerra o turno; `ambigua` (dois acionamentos
            #    em pausa) segue o caminho normal em vez de sumir sem rastro.
            _palavra = await ler_palavra_da_equipe(
                str(company_id), _texto_in, remetente=str(payload.phone or "")) if _texto_in else None
            if _palavra in ("agente", "eu_cuido"):
                logger.info("[WEBHOOK] palavra da equipe aplicada ao acionamento")
                return

            def _ao_cliente(fone: str, texto_out: str) -> None:
                whatsapp_service.send_message(fone, texto_out, integration)

            if _texto_in and await responder_pergunta_do_acionamento(
                    str(company_id), str(payload.phone or ""), _texto_in,
                    send_to_client=_ao_cliente):
                logger.info("[WEBHOOK] resposta do segurado levada à seguradora")
                return
        except Exception as e:  # noqa: BLE001 — nunca derruba o fluxo normal
            logger.error(f"[WEBHOOK] palavra/pergunta do acionamento: {type(e).__name__}")

        # S17 — Piloto em número pessoal: allowlist de teste (env
        # ATTENDANT_INBOUND_ALLOWLIST). Fora da lista = ignorado em silêncio
        # (não cria usuário/conversa, não responde). Vazia = produção normal.
        from app.services.whatsapp.channel_security import attendant_inbound_allowed

        if not attendant_inbound_allowed(str(payload.phone or "")):
            logger.info("[WEBHOOK] inbound fora da ATTENDANT_INBOUND_ALLOWLIST — ignorado")
            return

        # 2. Resolver Usuário
        user_id = integration_service.get_or_create_user(
            phone=payload.phone, company_id=company_id, name=payload.senderName
        )

        agent_suffix = agent_id if agent_id else "default"
        session_id = f"whatsapp:{payload.phone}:{company_id}:{agent_suffix}"

        # Check de Status (Modo Humano)
        #
        # 🔴 ESTE PORTÃO ERA FAIL-OPEN ATÉ 14/08/2026, E ISSO ESTAVA ERRADO.
        #
        # 📊 Antes: o `except` só logava e `is_human_mode` continuava `False` —
        # ou seja, **uma falha de leitura virava permissão de fala**. A IA
        # responderia por cima da atendente que já estava conduzindo a conversa,
        # e o segurado receberia duas vozes.
        #
        # E o portão irmão, 140 linhas abaixo (`_em_silencio`), sempre foi
        # fail-closed — "assumindo SILÊNCIO". Dois portões que respondem
        # perguntas parecidas falhavam para lados opostos, e o que protegia a
        # atendente era justamente o frouxo.
        #
        # Agora: **não conseguir confirmar que a conversa está livre nunca é
        # permissão para falar.** O custo de errar para este lado é uma
        # mensagem não respondida, que o vigia de handoff pega. O custo de
        # errar para o outro é a IA atropelando uma pessoa na frente do cliente.
        #
        # O filtro ganhou `company_id` (CLAUDE.md §7): o `session_id` já embute
        # o tenant, mas filtro de tenant no código é obrigação, não redundância.
        #
        # 🔴 SPEC-097 U2.3/E6 — E O DONO TAMBÉM CALA A IA.
        #
        # 📊 Medido em 05/09/2026: aqui se perguntava SÓ `status ==
        # 'HUMAN_REQUESTED'`. A conversa que a atendente assumiu pela tela
        # (`claimed_by` preenchido) continua com status `open` — e o robô
        # respondia POR CIMA dela. `pausar_ia` é o helper único que responde as
        # duas razões, e por isso o `select` passou a trazer `claimed_by`.
        #
        # 🔴 E A TERCEIRA RAZÃO — A JANELA (PLANO-HANDOFF-E-PAUSA §2, 09/09/2026).
        #
        # ⚠️ `pausar_ia` responde *"alguém está com a conversa AGORA?"*. Ele não
        # responde *"alguém da corretora falou ONTEM?"* — e a atendente que
        # respondeu pelo celular ontem não clicou em botão nenhum: não há
        # `claimed_by`, o status segue `open`, e o robô voltava a falar por cima
        # dela hoje. `a_ia_deve_calar` é a porta ÚNICA que soma as duas
        # perguntas (§5) e **nunca levanta** — o `except` abaixo continua sendo
        # o guarda do que ela não prevê.
        #
        # 🔴 O `select` ganhou `id` porque a janela precisa LER a conversa em
        # `messages`, e `messages` não tem `company_id`: o `conversation_id`
        # resolvido junto com a corretora é o que cumpre o §7.
        is_human_mode = False
        try:
            from app.services.o_fim_do_atendimento import (
                a_ia_deve_calar, anotar_silencio_no_feed, foi_a_janela,
            )

            check_status = await asyncio.to_thread(
                lambda: supabase.client.table("conversations")
                .select("id, status, claimed_by, claimed_by_name, claimed_at, resolvido_em")  # 🔴 P0-1 (097): sem resolvido_em, pausar_ia não sabe que o atendimento acabou; `claimed_at` é P-PILOTO-15 (takeover DEPOIS do encerramento protege a conversa reaberta)
                .eq("company_id", company_id)
                .eq("session_id", session_id)
                .limit(1)
                .execute()
            )
            if check_status.data and len(check_status.data) > 0:
                _linha_da_conversa = check_status.data[0]
                _calar, _motivo = await a_ia_deve_calar(
                    supabase, company_id=str(company_id), conversa=_linha_da_conversa)
                if _calar:
                    is_human_mode = True
                    # ⛔ A FRASE só vai para o log quando é a da JANELA: a do
                    #    takeover carrega `claimed_by_name`, que é NOME DE
                    #    PESSOA, e nome de pessoa não entra em log.
                    if foi_a_janela(_motivo):
                        logger.info("[WEBHOOK] 👤 a IA fica em silêncio nesta "
                                    "conversa: %s", _motivo)
                    else:
                        logger.info("[WEBHOOK] 👤 Modo Humano detectado (status=%s "
                                    "dono=%s). Pulando IA.",
                                    _linha_da_conversa.get("status"),
                                    bool(_linha_da_conversa.get("claimed_by")))
                    await anotar_silencio_no_feed(
                        company_id=str(company_id),
                        conversation_id=str(_linha_da_conversa.get("id") or ""),
                        motivo=_motivo)
        except Exception as e:
            is_human_mode = True
            logger.error(
                "[WEBHOOK] 🛑 não consegui confirmar o estado da conversa (%s) — "
                "assumindo MODO HUMANO. A IA não fala sem prova de que a "
                "conversa está livre.", type(e).__name__,
            )

        # 3. Processar Conteúdo
        # ⚠️ Fora do ramo de propósito (J2): quem perde a posse do turno lá
        #    embaixo precisa saber QUAIS itens devolver ao buffer, e o `return`
        #    seco de antes só conseguia perdê-los.
        _itens_do_turno = list(buffered_items or [])
        _renovacoes = [0]
        message_text = None
        final_audio_url = None
        final_image_url = None

        branch = pick_inbound_branch(
            has_combined=bool(combined_message),
            has_audio=bool(payload.audio and payload.audio.audioUrl),
            has_image=bool(payload.image),
            has_text=bool(payload.text and payload.text.message),
        )

        if branch == "combined":
            message_text = combined_message
            # 🔴 §6.3 — RE-LEITURA DO BUFFER, ainda antes de gravar a linha do
            # segurado e de montar o prompt. A mensagem que chega no segundo 9
            # de uma janela de 18 s entrava como resposta SEPARADA; agora entra
            # nesta. Teto de REPLANEJAMENTOS_MAX para não virar laço — o que
            # chegar depois fica no buffer, e a trava garante que vire o turno
            # SEGUINTE, nunca um turno paralelo.
            if turno is not None and chave_do_buffer:
                _servico = await get_message_buffer_service()
                for _rodada in range(REPLANEJAMENTOS_MAX):
                    _novos = await _servico.mesclar_o_que_chegou(chave_do_buffer)
                    if not _novos:
                        break
                    _itens_do_turno.extend(_novos)
                    message_text = texto_combinado_dos_itens(_itens_do_turno)
                    logger.info("[TURNO] re-planejamento %d: +%d item(ns) na MESMA "
                                "resposta", _rodada + 1, len(_novos))
            # A mídia da rajada é lida AQUI, dentro do turno (§6.2).
            if _itens_do_turno:
                _extra, _url_img = await _midia_do_turno(
                    _itens_do_turno, company_id=company_id, agent_id=agent_id,
                    supabase_client=supabase.client, is_human_mode=is_human_mode)
                if _url_img:
                    final_image_url = _url_img
                if _extra:
                    message_text = f"{message_text}\n\n{_extra}"

        elif branch == "audio":
            if is_human_mode:
                final_audio_url = await process_audio_for_storage(
                    payload.audio.audioUrl, company_id, supabase.client
                )
                message_text = "[Mensagem de voz]"
            else:
                logger.info("[WEBHOOK] Transcribing Audio with Whisper...")
                try:
                    audio_service = AudioService(settings.OPENAI_API_KEY)
                    message_text = await audio_service.transcribe_audio_from_url(
                        payload.audio.audioUrl,
                        company_id=company_id,
                        agent_id=agent_id
                    )
                    # LOG SANITIZADO
                    logger.info("[WEBHOOK] Processing Audio Message")
                except Exception as e:
                    logger.error(f"Whisper failed: {e}")
                    # 🔴 SPEC-065 — aqui o sistema FALAVA com o segurado 115
                    # linhas ANTES do portão de silêncio (`_em_silencio`, abaixo).
                    #
                    # Áudio é o formato mais comum de segurado no WhatsApp. Uma
                    # transcrição que falha mandava "Erro ao processar áudio."
                    # para ele — com o agente DESLIGADO, em modo observação, com
                    # a atendente humana respondendo pelo celular. Do lado dele:
                    # o robô se intrometeu numa conversa que era de gente.
                    #
                    # 📊 Só não mordia porque a `ATTENTANT_INBOUND_ALLOWLIST`
                    # barrava antes. Uma trava que depende de OUTRA trava não é
                    # trava: é sorte. No dia em que a allowlist for esvaziada —
                    # que é o dia do go-live — este caminho abria sozinho.
                    #
                    # Agora ele pergunta a mesma coisa que o portão de baixo, e
                    # fail-closed: erro de leitura = silêncio.
                    try:
                        from app.services.atlas.attendance_capture import attendance_agent_active

                        _pode_falar = await attendance_agent_active(company_id)
                    except Exception:  # noqa: BLE001
                        _pode_falar = False
                    if _pode_falar:
                        # 🔴 "Erro ao processar áudio." era o produto falando de
                        # SI para uma pessoa que acabou de descrever uma batida.
                        # Ela não sabe o que é processar áudio, não é culpada
                        # pelo erro e não recebe o que fazer agora. A frase nova
                        # diz a mesma verdade em língua de gente e devolve um
                        # caminho — escrever em poucas palavras — que funciona
                        # mesmo com a transcrição fora do ar.
                        await asyncio.to_thread(
                            whatsapp_service.send_message,
                            payload.phone, AVISO_DE_AUDIO_ILEGIVEL, integration,
                        )
                    else:
                        logger.info("[WEBHOOK] 🔇 audio falhou, mas o agente está em silêncio — não respondo")
                    return

        elif branch == "text":
            message_text = payload.text.message
            # LOG SANITIZADO
            logger.info(f"[WEBHOOK] Processing Text Message (len={len(message_text)})")

        elif branch == "image":
            # Imagem SEMPRE processada quando presente — a legenda NAO pode
            # descartar a imagem (bug: atendente ficava cego a foto do segurado).
            final_image_url = await process_image_for_vision(
                payload.image.imageUrl, company_id, supabase.client
            )
            # 🔴 A FOTO GRANDE NÃO SOME MAIS EM SILÊNCIO.
            #
            # O sentinela (e não `None`) é o único caso em que o produto SABE o
            # que aconteceu e sabe o que pedir. As duas pré-condições de fala
            # são as mesmas do ramo do áudio, e pelo mesmo motivo:
            #
            #   is_human_mode            a atendente está conduzindo — o robô
            #                            não se intromete. Aqui ele NÃO fala e
            #                            NÃO retorna: a mensagem segue o fluxo
            #                            e a foto aparece no chat dela.
            #   attendance_agent_active  o portão de silêncio. Erro de leitura
            #                            = silêncio (fail-closed).
            if final_image_url is FOTO_GRANDE_DEMAIS:
                final_image_url = None
                if not is_human_mode:
                    try:
                        from app.services.atlas.attendance_capture import attendance_agent_active

                        _pode_falar = await attendance_agent_active(company_id)
                    except Exception:  # noqa: BLE001
                        _pode_falar = False
                    if _pode_falar:
                        await asyncio.to_thread(
                            whatsapp_service.send_message,
                            payload.phone, AVISO_DE_FOTO_GRANDE, integration,
                        )
                    else:
                        logger.info("[WEBHOOK] 🔇 foto grande, mas o agente está em "
                                    "silêncio — não respondo")
                    return
            # Legenda = fala do cliente ("o que tem nessa imagem?"); sem legenda, placeholder.
            caption = payload.image.caption or (payload.text.message if payload.text else None)
            message_text = caption or ("📷 [Imagem]" if is_human_mode else "🖼️ [Imagem enviada]")
            logger.info(f"[WEBHOOK] Image processed. URL: {final_image_url}")
            # F1 — atendente VÊ a imagem do segurado (foto de dano, documento,
            # boleto): contexto visual entra no texto; falhou → segue sem.
            if final_image_url and not is_human_mode:
                try:
                    from app.services.vision_service import describe_image

                    vision_text = await describe_image(
                        final_image_url,
                        company_id=str(company_id),
                        agent_id=str(agent_id) if agent_id else None,
                        purpose_hint="Atendente de corretora falando com o segurado",
                    )
                    if vision_text:
                        message_text = f"{message_text}\n\n[CONTEXTO VISUAL — imagem enviada pelo cliente]:\n{vision_text}"
                        logger.info("[WEBHOOK] ✅ Imagem do cliente analisada (F1)")
                except Exception as e:  # noqa: BLE001
                    logger.error(f"[WEBHOOK] vision falhou: {type(e).__name__}")

        else:
            logger.error("[WEBHOOK BACKGROUND] No valid message content found")
            return

        if not message_text:
            return

        # 4. Get Conversation
        conversation_id = await get_or_create_conversation(
            supabase_client=supabase.client,
            company_id=company_id,
            user_id=user_id,
            session_id=session_id,
            message_text=message_text,
            payload=payload,
            channel="whatsapp",
            agent_id=agent_id,
        )

        # (SPEC-046) O desvio 4b para o "Attendance Runtime bridge" (TS legado,
        # 42W0) foi REMOVIDO: desde a SPEC-017 P2 o atendente externo roda
        # direto no Smith como qualquer agente — cérebro único, sem bridge.

        # 5. Salvar Msg Usuário
        try:
            user_message_data = {
                "conversation_id": conversation_id,
                "role": "user",
                "content": message_text,
                "type": "voice" if final_audio_url else "text",
                "audio_url": final_audio_url,
                "image_url": final_image_url,
            }
            # 🔴 SPEC-EXTRA-001.2 E1 — a linha do segurado ENTRA no índice único.
            # `payload.messageId` é o id global do WhatsApp, o mesmo que o
            # dedupe do Redis usa (:1425) e o mesmo que o espelho grava. A
            # reentrega da Meta deixa de virar segunda linha e segunda leitura.
            # 🔴 TODOS os ids da rajada (J7): a linha combinada representa N
            # mensagens do WhatsApp, e não só a que fechou a janela.
            _ids_da_rajada = [str(i.get("wa_message_id") or "")
                              for i in _itens_do_turno
                              if str((i or {}).get("wa_message_id") or "").strip()]
            _desfecho = await gravar_mensagem_do_pipeline(
                supabase.client, dados=user_message_data,
                wa_message_id=(_ids_da_rajada[0] if _ids_da_rajada
                               else payload.messageId),
                direcao="in", wa_message_ids=_ids_da_rajada)
            logger.info("[MESSAGES] User message saved (%s).", _desfecho)
        except Exception as e:
            logger.error(f"[MESSAGES] Failed to save user msg: {e}")

        # =====================================================================
        # 🔴 SPEC-093-B BLOCO A — A SOMBRA DO SINISTRO NASCE AQUI, E SÓ AQUI
        # =====================================================================
        #
        # 📊 Medido em 03/09/2026: `attendance_agent_active()` é falso em 4 de 4
        # agentes `attendance`. Com ele falso, este fluxo grava a mensagem,
        # espelha e **`return`** ~70 linhas abaixo, ANTES de
        # `langchain_service.process_message`. **O grafo não roda em produção.**
        #
        # ⛔ Um gancho escrito depois daquele `return` — que é onde a primeira
        # versão desta SPEC o colocava — provaria um caminho que NENHUMA
        # mensagem percorre. Este ponto, logo depois do INSERT em `messages`, é
        # o único que TODA mensagem de segurado atravessa hoje.
        #
        # ⛔ A sombra OBSERVA: não envia nada, não liga agente, não muda um
        # turno. O `try/except` é largo de propósito (o modelo é o do cartógrafo,
        # `webhook.py:373-375`): perder o rastro é ruim e recuperável; derrubar o
        # atendimento de um segurado por causa dele, não.
        try:
            from app.services.claims_shadow import (
                abrir_sombra, detectar_sinistro, ficha_da_conversa, registrar_gesto,
                tipo_de_documento,
            )

            # A ficha da conversa é o caminho (a) — confiança ALTA. 📊 Ela tem
            # conteúdo em 1 de 679 conversas hoje (o grafo não roda, então
            # `nodes.py:860` nunca a grava), mas quando existir ela é a verdade
            # melhor que o regex, e é lida em UMA consulta indexada por id.
            #
            # 🔴 ESTE SELECT É NOVO, E O CUSTO DELE TAMBÉM É — a marca anterior
            # dizia o contrário e foi corrigida na auditoria de 03/09/2026 (A-02).
            #
            # 📊 O texto que estava aqui afirmava que "678 de 679 conversas PAGAVAM
            # este SELECT" e que a consulta só tinha "mudado de lugar". Não havia
            # lugar de onde mudar: `git log --diff-filter=A` mostra que
            # `claims_shadow.py` nasceu nesta branch, e na `main` não existe leitura
            # nenhuma de `ficha_atendimento` no webhook. Um custo NOVO descrito como
            # custo antigo é um número que se cita como economia (§12.1).
            #
            # A verdade medida: a SPEC acrescenta **+1 SELECT na PRIMEIRA mensagem de
            # cada conversa**; da segunda em diante a resposta vem da memória de
            # processo (`_MEMORIA_DA_FICHA`), inclusive quando é `None` — e 📊 ela é
            # `None` em 678 de 679 conversas hoje, porque o grafo não roda e
            # `nodes.py:860` nunca grava a ficha. O filtro de `company_id` (§7) é do
            # próprio módulo e continua lá.
            _ficha = await ficha_da_conversa(supabase, company_id, conversation_id)

            _abre, _confianca, _motivo = detectar_sinistro(message_text, _ficha)
            if _abre:
                await abrir_sombra(
                    supabase, company_id=str(company_id),
                    conversation_id=str(conversation_id),
                    confianca=_confianca, motivo=_motivo,
                )

            # O arquivo do segurado vira EVENTO, nunca conteúdo: o que fica
            # gravado é o enum do tipo, e ele sai do NOME DO ARQUIVO e da legenda
            # pelo classificador da sombra (que consulta o
            # `attendance_media._detect_document_type` como segundo leitor).
            # 🔴 `registrar_gesto` não escreve quando a conversa não tem sombra.
            #
            # 🔴 IMAGEM **E** DOCUMENTO — foi o BLOCKER 1 da auditoria externa.
            # 📊 03/09/2026, nas sessões de sinistro em produção: 1.060 imagens e
            # 730 documentos inbound. Com o `if` só na imagem, 40,8% dos arquivos
            # de um sinistro não viravam evento — e esses casos saíam do digest
            # como `sem_documento`, que se lê como "o papel nunca chegou".
            #
            # ⚠️ Áudio continua FORA: uma mensagem de voz não é documento, e o
            # enum `tipo_documento` não tem valor para ela. Gravá-la como
            # `documento_recebido: desconhecido` encheria o contador "sinistros
            # com documento" com áudios — um número que mentiria por construção.
            #
            # ⛔ UM `registrar_gesto` só, e não um por ramo: um payload de imagem
            # não pode carregar `document`, então as duas condições nunca são
            # verdadeiras juntas — mas um segundo escritor aqui seria a porta
            # aberta para o dia em que passassem a ser (evento duplicado no
            # ledger é uma variante inventada no digest).
            _nome_do_arquivo = nome_do_documento(message_text, payload_dict)
            if final_image_url or _nome_do_arquivo:
                await registrar_gesto(
                    supabase, company_id=str(company_id),
                    conversation_id=str(conversation_id),
                    event_type="claims.documento_recebido",
                    payload={"tipo_documento": tipo_de_documento(
                        _nome_do_arquivo, message_text)},
                )
        except Exception as e:  # noqa: BLE001
            logger.warning("[SOMBRA] rastro do sinistro não registrado (%s)",
                           type(e).__name__)

        # 6. Se for HUMANO, parar
        if is_human_mode:
            logger.info("[WEBHOOK] 🛑 Human Requested - Stopping pipeline.")
            # Atualizar unread...
            return

        # 6.5 SPEC-045 — MODO OBSERVAÇÃO: agente de atendimento DESLIGADO
        # (agents.is_active=false). O número segue pareado, a atendente humana
        # responde pelo celular, e o sistema CAPTURA (conversa já espelhada no
        # passo 5 + cofre do Espelho aqui). O agente não responde ninguém.
        # Ligar o agente no dashboard reativa a resposta NO MESMO número —
        # o Observador/Espelho seguem funcionando sempre (nunca desligam).
        # A decisão de FALAR e o ato de CAPTURAR são separados de propósito.
        #
        # Antes eram um `try` só, e isso criava um caminho que ninguém queria:
        # se a CAPTURA falhasse, o `except` engolia e o código seguia para o
        # fluxo de IA — o agente respondia um segurado real porque a gravação
        # do transcript deu erro. Duas falhas diferentes, o mesmo desfecho
        # errado.
        #
        # Agora: primeiro decide-se se pode falar; depois grava-se, e uma falha
        # na gravação não vira permissão para falar.
        try:
            # SPEC-063 Bloco A — a pergunta virou POSITIVA.
            #
            # Antes: `attendance_observation_mode` — que só devolve True quando o
            # agente de atendimento EXISTE e está desligado. Corretora que NÃO TEM
            # agente de atendimento recebia False, e False significava "pode
            # falar". O pipeline seguia e respondia o segurado com o primeiro
            # agente ativo por data — o copiloto interno, cujo prompt manda
            # entregar CPF sem mascarar.
            #
            # Os dois estados não são a mesma coisa e não podem cair no mesmo
            # ramo: "desligado de propósito" e "nunca existiu" são ambos motivo
            # para calar, e nenhum é motivo para falar.
            #
            # Agora: só fala quem PROVA que tem agente de atendimento ligado.
            from app.services.atlas.attendance_capture import attendance_agent_active

            _em_silencio = not await attendance_agent_active(company_id)
        except Exception as e:  # noqa: BLE001
            # Nem o portão conseguiu ser consultado. Fail-closed: não falar.
            logger.error("[WEBHOOK] portão de observação indisponível (%s) — "
                         "assumindo SILÊNCIO", type(e).__name__)
            _em_silencio = True

        if _em_silencio:
            try:
                from app.services.atlas.attendance_capture import capture_channel_message
                from app.services.observability import sli as _sli

                _t0 = _tempo.perf_counter()
                await capture_channel_message(
                    company_id, payload.connectedPhone or "", payload.phone,
                    message_text, "in", payload.messageId,
                    "voice" if final_audio_url else ("image" if final_image_url else "text"),
                )
                # SPEC-062 §18 — quanto demora observar. E o SLI que diz se o
                # Observador aguenta o volume da corretora sem atrasar nada.
                _sli.registrar(_sli.WHATSAPP_OBSERVACAO,
                               (_tempo.perf_counter() - _t0) * 1000,
                               company_id=company_id)
                logger.info("[WEBHOOK] 👁 Modo observação — capturado sem resposta do agente.")
            except Exception as e:  # noqa: BLE001
                # Perder o transcript é ruim e é recuperável — a conversa
                # continua no WhatsApp da corretora. Responder sem autorização
                # não é recuperável.
                logger.error("[WEBHOOK] captura do espelho falhou (%s) — o "
                             "agente permanece em silêncio", type(e).__name__)
            return

        # Daqui para baixo o agente TEM autorização para falar com este segurado
        # — e, portanto, tem o dever de não emudecer se algo explodir.
        _pode_falar_ao_cliente = True

        # 7. Fluxo IA
        # 🔥 BILLING: Verificar saldo antes de invocar IA
        from app.services.billing_service import get_billing_service
        billing_service = get_billing_service()

        # SPEC-062 §4, leis 2 e 4 — a PORTEIRA decide, nao o saldo direto.
        # Interruptor BILLING_ENFORCEMENT (padrao DESLIGADO); suspensao vale sempre.
        from app.services.billing_gate import pode_consumir

        _pode, _motivo = pode_consumir(company_id)
        if not _pode:
            logger.info("[WEBHOOK] barrado pela porteira: %s", _motivo)
            # Enviar mensagem informativa ao usuário
            await asyncio.to_thread(
                whatsapp_service.send_message,
                to_number=payload.phone,
                text="⚠️ Serviço temporariamente indisponível. Por favor, entre em contato com o suporte.",
                integration=integration,
            )
            return

        logger.info(f"[WEBHOOK] Invoking AI Agent for company {company_id}...")
        langchain_service = LangChainService(settings.OPENAI_API_KEY, supabase)

        # SPEC-045 — NOTA DE CONTEXTO: se este cliente recebeu envio de
        # plataforma recente (cobrança/campanha), o atendente responde SABENDO
        # do que se trata. Só o texto enviado à IA — a mensagem salva (passo 5)
        # fica limpa. Sem envio recente = zero ruído.
        #
        # 🔴 SPEC-EXTRA-001 §4 — QUANDO HÁ COBRANÇA, O CASO VENCE O GENÉRICO.
        #
        # `context_note_for` diz *"este cliente recebeu algo da corretora"*. Ao
        # responder *"já paguei"*, quem atende precisa de outra coisa: QUAL
        # seguradora, QUAL parcela, em QUE estado — e as regras de conduta (não
        # confirmar pagamento, não reenviar boleto por conta própria).
        #
        # ⚠️ Sem caso, nada muda: o genérico de hoje continua sendo a nota, e é
        # ele o CONTROLE deste bloco (CLAUDE.md §9.2).
        #
        # ⛔ O bloco é DADO para o modelo, nunca instrução que mude autorização.
        message_for_ai = message_text
        try:
            from app.services.billing_replies import (
                contexto_de_cobranca, telefones_da_equipe_de_cobranca,
            )
            from app.services.platform_outbound import context_note_for

            # A ATENDENTE NÃO HERDA O CASO DE NINGUÉM: no modo `equipe` o ledger
            # guarda o telefone de quem recebeu o pacote para encaminhar.
            _equipe = await telefones_da_equipe_de_cobranca(company_id)
            _note = await contexto_de_cobranca(company_id, payload.phone,
                                               excluir_phones=_equipe or ())
            if not _note:
                _note = await context_note_for(company_id, payload.phone)
            if _note:
                message_for_ai = f"{message_text}\n\n{_note}"
        except Exception:  # noqa: BLE001
            pass

        # 🔴 "digitando…" — AQUI, e não antes (§6.4 regra 1). O portão de
        # silêncio já passou (`is_human_mode` acima) e a resposta vai ser
        # gerada. E02 é literal: *"only display a typing indicator if you are
        # going to respond"* — prometer e calar é pior que calar.
        # ⚠️ O `delay` do Evolution GO mantém o `composing` vivo re-enviando e
        # manda `paused` sozinho no fim; o teto é o mesmo 25 s da rajada.
        await _presenca(integration, payload.phone, "composing",
                        TETO_DA_RAJADA_SEGUNDOS * 1000)

        # 🔴 A RENOVAÇÃO ANTES DA GERAÇÃO (J2). 📊 O TTL é 90 s e o modelo
        # mediu máx 53,4 s (`conversation_logs.response_time_ms`, 14/09) — mas
        # esse é o tempo do MODELO: ferramenta, InfoCap e as regenerações dos
        # fiscais somam por cima, e o envio soma depois. Renovar aqui é o que
        # impede o turno de vencer NO MEIO da própria geração.
        # ⚠️ As regenerações dos fiscais rodam DENTRO do grafo (`agent_node`),
        #    que não recebe o turno; elas ficam cobertas por esta renovação e
        #    pela de baixo — P-E0012-J2.
        await _renovar_o_turno(turno, _renovacoes)

        ai_response, metrics = await langchain_service.process_message(
            user_message=message_for_ai,
            company_id=company_id,
            user_id=user_id,
            session_id=session_id,
            collect_metrics=True,
            channel="whatsapp",
            image_url=final_image_url,
            agent_id=agent_id,
            # SPEC-063 Bloco A — este caminho fala com o SEGURADO. O papel é
            # exigido, não sugerido: se a corretora não tiver agente de
            # atendimento ativo, `process_message` levanta e ninguém responde.
            # É a segunda trava, depois do portão de silêncio — porque o
            # `agent_id` da integração pode estar velho ou apontar para o
            # agente errado, e um id herdado não pode virar permissão de fala.
            required_role="attendance",
        )

        # =====================================================================
        # 🔴 A SEGUNDA PERGUNTA — E ELA É NA SAÍDA, NÃO NA ENTRADA (09/09/2026)
        # =====================================================================
        #
        # 📊 Medido no primeiro dia de piloto: de 14 respostas do robô por cima
        # da atendente, **2 chegaram a 25 segundos ou menos depois da fala dela**.
        # Não foram pausa quebrada — foram CORRIDA. A mensagem do segurado já
        # estava no buffer (8-25 s de debounce) e o modelo já estava pensando
        # quando a Regina escreveu. O portão da entrada (`is_human_mode`, ~380
        # linhas acima) tinha perguntado **antes** de tudo isso, e a resposta era
        # verdadeira quando ele perguntou.
        #
        # ⛔ Uma pergunta só, no começo do turno, não tem como cobrir um turno
        # que dura meio minuto. Esta é a MESMA pergunta (`pausar_ia`, o helper
        # único — CLAUDE.md §5), refeita no último instante em que ainda dá para
        # não falar.
        #
        # 🔴 E ela vem ANTES do passo 8 de propósito: mais adiante a resposta é
        # GRAVADA em `messages` e vira preview da conversa. Gravar uma fala que
        # não vai sair põe no chat da corretora uma frase que o segurado nunca
        # recebeu — e a atendente responderia achando que o robô já disse aquilo.
        #
        # ⚠️ Falha de leitura CALA (fail-closed), como o portão irmão da entrada:
        # não conseguir confirmar que a conversa está livre nunca é permissão
        # para falar. O custo é uma resposta perdida; o outro custo é duas vozes.
        #
        # 🔴 E A PERGUNTA DA SAÍDA É A PORTA INTEIRA, não só o takeover: a
        # atendente que responde pelo CELULAR durante o turno não clica em
        # botão nenhum — a fala dela chega pelo espelho, `claimed_by` continua
        # vazio, e só a JANELA vê isso. É a mesma `a_ia_deve_calar` da entrada,
        # refeita no último instante em que ainda dá para não falar (§5).
        _motivo_do_silencio = ""
        try:
            from app.services.o_fim_do_atendimento import (
                a_ia_deve_calar, anotar_silencio_no_feed, foi_a_janela,
            )

            _estado_agora = await asyncio.to_thread(
                lambda: supabase.client.table("conversations")
                .select("id, status, claimed_by, claimed_by_name, claimed_at, resolvido_em")
                .eq("company_id", company_id)
                .eq("id", conversation_id)
                .limit(1)
                .execute()
            )
            _linhas_agora = getattr(_estado_agora, "data", None) or []
            if _linhas_agora:
                _assumida_no_meio, _motivo_do_silencio = await a_ia_deve_calar(
                    supabase, company_id=str(company_id), conversa=_linhas_agora[0])
            else:
                _assumida_no_meio = False
        except Exception as e:  # noqa: BLE001
            logger.error("[WEBHOOK] 🛑 não consegui reconferir a conversa antes de "
                         "responder (%s) — a IA NÃO fala", type(e).__name__)
            _assumida_no_meio = True

        if _assumida_no_meio:
            # A resposta pronta é DESCARTADA, e é isso mesmo: uma pessoa assumiu
            # esta conversa enquanto o modelo escrevia. Ela não é reaproveitável
            # depois — o contexto mudou junto com quem está atendendo.
            # ⚠️ Em `try` próprio: o de cima é fail-closed e pode ter caído
            #    ANTES do import. Um NameError aqui derrubaria o descarte, que é
            #    justamente a parte que protege a atendente.
            try:
                from app.services.o_fim_do_atendimento import (
                    anotar_silencio_no_feed, foi_a_janela,
                )

                if foi_a_janela(_motivo_do_silencio):
                    logger.info("[WEBHOOK] 👤 a atendente falou DURANTE o turno: %s",
                                _motivo_do_silencio)
                    await anotar_silencio_no_feed(
                        company_id=str(company_id),
                        conversation_id=str(conversation_id),
                        motivo=_motivo_do_silencio)
            except Exception as _e_feed:  # noqa: BLE001
                logger.debug("[WEBHOOK] feed do silêncio não escrito (%s)",
                             type(_e_feed).__name__)
            logger.info("[WEBHOOK] 👤 a conversa foi assumida DURANTE o turno — "
                        "resposta do agente descartada, nada foi enviado")
            # §6.4 regra 4: `paused` SEMPRE ao terminar — inclusive quando o
            # turno é descartado. Um "digitando…" pendurado é a promessa vazia.
            await _presenca(integration, payload.phone, "paused")
            return

        # =====================================================================
        # 🔴 A TERCEIRA PERGUNTA — AINDA SOU O DONO DESTE TURNO? (§5.5)
        # =====================================================================
        #
        # E01 é explícita: *"don't assume that a lock is retained as long as the
        # process that had acquired it is alive"* — e o Redis não usa relógio
        # monotônico para expirar TTL. Um turno que passou dos 90 s pode já ter
        # sido reaberto por outra varredura, com o buffer inteiro na mão.
        #
        # ⛔ Enviar "por via das dúvidas" é exatamente o defeito que esta SPEC
        # existe para matar: duas respostas para uma pergunta.
        #
        # 🔴 E vem ANTES do passo 8 pela mesma razão que a pergunta do silêncio:
        # gravar uma fala que não vai sair põe no chat da corretora uma frase
        # que o segurado nunca recebeu.
        if turno is not None:
            # 🔴 RENOVAR É A PRIMEIRA TENTATIVA, e ela vale mais que a pergunta
            # (J2): `renovar_turno` roda o MESMO EVAL comparando o token, então
            # ele já responde "sou o dono?" — e, quando é, ainda estende o TTL
            # para cobrir o envio, que é síncrono e pode levar dezenas de
            # segundos em três balões.
            await _renovar_o_turno(turno, _renovacoes)
            _servico_do_turno = await get_message_buffer_service()
            if not await _servico_do_turno.ainda_sou_o_dono(
                    turno.escopo, turno.phone, turno.token):
                # =============================================================
                # 🔴 A RAJADA VOLTA PARA O BUFFER — NÃO SE PERDE (J2)
                # =============================================================
                #
                # 📊 O `return` seco que estava aqui descartava a rajada
                # INTEIRA: o `get_and_clear` do varredor já tinha esvaziado o
                # Redis, então as cinco mensagens do segurado sumiam e ninguém
                # respondia. ⛔ "Outra rodada já respondeu" era uma SUPOSIÇÃO:
                # a posse pode ter sido perdida por TTL vencido sem que rodada
                # nenhuma tenha assumido.
                #
                # ⚠️ E `turno_perdido` NÃO é silêncio do agente (J6): é evento
                # interno do runtime. Ele não vai ao feed da Regina — ela não
                # tem o que fazer com ele, e no feed ele aparecia como token
                # cru, classificado junto do takeover.
                try:
                    await _servico_do_turno.devolver_itens_ao_buffer(
                        chave_do_buffer or _servico_do_turno.chave(
                            turno.escopo, turno.phone),
                        _itens_do_turno,
                        payload=payload_dict, company_id=str(company_id),
                        user_id=str(user_id or ""), integration=integration)
                except Exception as _e_volta:  # noqa: BLE001
                    logger.error("[TURNO] devolução ao buffer falhou (%s)",
                                 type(_e_volta).__name__)
                logger.warning("[TURNO] posse perdida ANTES do envio — resposta "
                               "descartada e a rajada devolvida ao buffer")
                await _presenca(integration, payload.phone, "paused")
                return

        # 8. Salvar Resposta IA
        try:
            # 🔴 A LINHA VEM ANTES DO ENVIO, e é de propósito: se o envio
            # falhar, a resposta que o modelo escreveu não se perde do registro.
            #
            # ⛔ E ELA FICA SEM `wa_message_id` HOJE — declarado, não escondido.
            # 📊 Medido em 14/09/2026: `whatsapp_service.send_message` devolve
            # **`bool`** (`whatsapp_service.py:131`), não `SendResult`, e fatia o
            # texto em BALÕES — um envio produz N ids, não um. O id do provider
            # existe (`SendResult.provider_message_id`, `models.py:242`;
            # `evolution_go.py:425` o preenche) mas não atravessa a fachada.
            # Enquanto não atravessar, a rede de segurança continua sendo
            # `e_a_nossa_propria_voz` (:1951-1953) e `_eco_do_dashboard`
            # (`espelho_chat.py:433-459`) — P-E0012-02.
            #
            # 🔴 O que muda já: a linha passa pelo MESMO escritor do segurado,
            # com `origem` e `direcao`. No dia em que a fachada devolver o id,
            # é um argumento — não um segundo caminho de escrita.
            await gravar_mensagem_do_pipeline(
                supabase.client,
                dados={"conversation_id": conversation_id,
                       "role": "assistant", "content": ai_response},
                wa_message_id=None, direcao="out")
            # LOG SANITIZADO
            logger.info("[WEBHOOK BACKGROUND] Agent response generated")
        except Exception as e:
            logger.error(f"[MESSAGES] Failed to save AI message: {e}")

        # 8.1 Atualizar preview
        try:
            preview_text = ai_response[:100] if len(ai_response) > 100 else ai_response
            # Get current unread
            res = await asyncio.to_thread(
                lambda: supabase.client.table("conversations").select("unread_count").eq("id", conversation_id).single().execute()
            )
            new_unread = (res.data.get("unread_count") or 0) + 1

            # FIX DE DATA ISO
            current_time_iso = datetime.now(timezone.utc).isoformat()

            await asyncio.to_thread(
                lambda: supabase.client.table("conversations").update({
                    "last_message_preview": preview_text,
                    "last_message_at": current_time_iso,
                    "unread_count": new_unread,
                }).eq("id", conversation_id).execute()
            )
        except Exception as e:
            logger.warning(f"[CONVERSATION] Metadata update error: {e}")

        # 9. Enviar no WhatsApp
        # LOG SANITIZADO
        logger.info(f"[WEBHOOK BACKGROUND] Sending response to {safe_phone}")
        # 🔴 `send_message` é SÍNCRONO — `requests.post` com timeout de 30 s e
        # `time.sleep(0.7)` entre balões. Chamado direto de uma corrotina, ele
        # PARA O EVENT LOOP INTEIRO: enquanto uma conversa espera a Evolution
        # responder, nenhum outro webhook é lido, nenhum outro buffer é
        # processado, nenhuma outra pessoa é atendida. Uma resposta de três
        # balões para um segurado congela o produto por mais de dois segundos —
        # e um timeout congela por trinta.
        #
        # ⚠️ `to_thread` não muda um argumento nem um retorno: o valor devolvido
        # é o mesmo `bool`, e a exceção sobe pelo mesmo caminho. O que muda é
        # que o loop continua atendendo os outros enquanto este envio acontece.
        success = await asyncio.to_thread(
            whatsapp_service.send_message,
            to_number=payload.phone, text=ai_response, integration=integration,
        )

        # §6.4 regra 4: `paused` ao terminar, sempre.
        await _presenca(integration, payload.phone, "paused")

        if success:
            _resposta_ja_enviada = True
            logger.info(f"[WEBHOOK BACKGROUND] ✅ Message sent to {safe_phone}")
            # =============================================================
            # 🔴 A APRESENTAÇÃO SÓ CONTA DEPOIS DE SAIR (J5, 14/09/2026)
            # =============================================================
            #
            # 📊 O defeito: `graph.py` gravava `identidade.apresentado_em` na
            # MONTAGEM do prompt. Bastava montar. Se o turno fosse descartado
            # depois — posse perdida, atendente assumiu, envio falhou — o
            # segurado nunca ouvia a apresentação e a ficha já dizia que ela
            # tinha acontecido: **"se apresenta uma vez" virava "nunca"**.
            #
            # ⚠️ Este é o ÚNICO ponto do produto em que se sabe que a mensagem
            # SAIU. E ele ainda confere a terceira condição: que o texto
            # enviado realmente carregue a apresentação — o modelo pode ter
            # ignorado a instrução, e marcar aí seria mentir para o próximo
            # turno (CLAUDE.md §9.4: o que se afirma é o comportamento sobre o
            # texto REAL).
            try:
                from app.services.o_fim_do_atendimento import (
                    confirmar_apresentacao_enviada,
                )

                await confirmar_apresentacao_enviada(
                    supabase.client, company_id=str(company_id),
                    session_id=str(session_id or ""), resposta=ai_response)
            except Exception as _e_apres:  # noqa: BLE001
                logger.debug("[APRESENTACAO] não confirmada (%s)",
                             type(_e_apres).__name__)
        else:
            logger.error("[WEBHOOK BACKGROUND] Failed to send WhatsApp message")

    except Exception as e:
        logger.error(f"[WEBHOOK BACKGROUND] Critical Error: {str(e)}", exc_info=True)
        # O SEGURADO NÃO FICA SEM RESPOSTA.
        #
        # Log não é atendimento. Quem mandou a mensagem não vê o Sentry: vê um
        # WhatsApp que não respondeu, e conclui que ninguém está lá.
        #
        # O texto é curto e **não promete nada que não vá acontecer**: não diz
        # que um atendente vai assumir (ninguém foi acionado), não diz que a
        # mensagem foi registrada (a gravação pode ter sido justamente o que
        # falhou) e não estima prazo. Diz o que é verdade — deu erro aqui — e o
        # que a pessoa pode fazer agora.
        if _pode_falar_ao_cliente and not _resposta_ja_enviada:
            try:
                await asyncio.to_thread(
                    whatsapp_service.send_message,
                    to_number=payload.phone,
                    text=("Tive uma falha técnica aqui e não consegui processar sua "
                          "última mensagem. Pode enviar de novo, por favor? "
                          "Se for urgente, ligue para a corretora."),
                    integration=integration,
                )
                logger.info("[WEBHOOK BACKGROUND] fallback honesto enviado ao cliente")
            except Exception:  # noqa: BLE001
                # O fallback do fallback é o log. Aqui o canal em si está fora.
                logger.error("[WEBHOOK BACKGROUND] nem o fallback saiu — cliente "
                             "SEM resposta (canal indisponível)")


# ==============================================================================
# ROUTES
# ==============================================================================

@router.post("/api/v1/webhook/z-api")
@limiter.limit("120/minute")
async def z_api_webhook(request: Request, background_tasks: BackgroundTasks):
    """Webhook Z-API (Non-blocking)"""
    try:
        # 42W0 — Guard de autenticação do webhook (não quebra dev; protege prod).
        auth_mode = (settings.WHATSAPP_WEBHOOK_AUTH_MODE or "disabled").lower()
        if auth_mode == "shared_secret":
            expected = settings.WHATSAPP_WEBHOOK_SECRET
            provided = request.headers.get("x-webhook-secret") or request.query_params.get("secret")
            if not expected or not provided or not hmac.compare_digest(str(provided), str(expected)):
                logger.warning("[WEBHOOK] webhook_auth_failed mode=shared_secret")
                raise HTTPException(status_code=401, detail="webhook_auth_failed")
        elif auth_mode == "provider_signature":
            # Z-API ainda não envia assinatura; guard pronto para quando enviar.
            if not request.headers.get("x-zapi-signature"):
                logger.warning("[WEBHOOK] webhook_auth_failed mode=provider_signature")
                raise HTTPException(status_code=401, detail="webhook_auth_failed")
        else:
            logger.warning("[WEBHOOK] auth disabled (dev only) — set WHATSAPP_WEBHOOK_AUTH_MODE for production")

        payload_dict = await request.json()
        logger.info(f"[WEBHOOK] Received from ...{str(payload_dict.get('connectedPhone'))[-4:]}")

        try:
            payload = ZAPIWebhookPayload(**payload_dict)
        except Exception:
            return {"status": "ignored", "reason": "invalid_payload"}

        if payload.isGroup or payload.fromMe:
            return {"status": "ignored"}

        if not payload.text and not payload.audio and not payload.image:
            return {"status": "ignored", "reason": "no_content"}

        # 42W0 — Dedupe por messageId (Redis SET NX + TTL). Evita resposta dupla.
        if payload.messageId:
            try:
                redis = await get_async_redis_client()
                was_set = await redis.set(
                    f"wa_dedupe:{payload.messageId}", "1", ex=settings.WHATSAPP_DEDUPE_TTL_SECONDS, nx=True
                )
                if not was_set:
                    logger.info("[WEBHOOK] inbound_deduped (duplicate messageId)")
                    return {"status": "ignored", "reason": "duplicate"}
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[WEBHOOK] dedupe skipped: {type(e).__name__}")

        # Buffer Logic — 🔴 DESVIO DE MÍDIA Nº 1, MORTO (SPEC-EXTRA-001.2 §6.2).
        # A foto abria um turno em PARALELO ao texto que ainda estava no buffer:
        # o segurado mandava "bateu aqui" + foto e recebia duas respostas, uma
        # delas sem ter visto a outra metade. Agora os dois são a mesma rajada.
        if payload.text and payload.text.message or payload.audio or payload.image:
            return await _buffer_or_dispatch_text(payload_dict, payload.phone)

        return {"status": "ignored"}

    except HTTPException:
        raise  # 42W0: preserva 401 do guard de auth (não vira 500)
    except Exception as e:
        logger.error(f"[WEBHOOK] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Server error") from e


@router.get("/api/v1/webhook/z-api/health")
async def webhook_health():
    """Health check endpoint para webhook"""
    return {
        "status": "healthy",
        "webhook": "z-api",
        "version": "1.0.0",
        "mode": "background_processing",
    }


# ==============================================================================
# SPEC-017 P1.2 — ROTAS COM TOKEN POR INTEGRAÇÃO (multi-tenant fail-closed)
# Tenant resolvido pelo HASH do token do path (nunca pelo corpo forjável).
# ==============================================================================

async def _resolve_webhook_integration(provider: str, path_token: str) -> dict:
    """Auth fail-closed da rota de webhook por token. 401 uniforme (anti-enum)."""
    if not validate_webhook_token_format(path_token):
        raise HTTPException(status_code=401, detail="webhook_auth_failed")
    integration = await asyncio.to_thread(
        integration_service.get_integration_by_webhook_token, path_token
    )
    if not integration:
        raise HTTPException(status_code=401, detail="webhook_auth_failed")
    if not webhook_token_matches(path_token, integration.get("webhook_token_hash")):
        raise HTTPException(status_code=401, detail="webhook_auth_failed")
    if not provider_matches_integration(provider, integration.get("provider")):
        logger.warning("[WEBHOOK TOKEN] provider mismatch (rota %s)", provider)
        raise HTTPException(status_code=401, detail="webhook_auth_failed")
    return integration


async def _is_duplicate_namespaced(provider: str, message_id: Optional[str]) -> bool:
    key = dedup_key(provider, message_id)
    if not key:
        return False
    try:
        redis = await get_async_redis_client()
        was_set = await redis.set(key, "1", ex=settings.WHATSAPP_DEDUPE_TTL_SECONDS, nx=True)
        return not was_set
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[WEBHOOK TOKEN] dedupe skipped: {type(e).__name__}")
        return False


async def _download_evolution_media(integration: dict, message_id: str,
                                    raw_message: Optional[dict] = None) -> Optional[tuple]:
    """(bytes, mimetype) da mídia criptografada do WhatsApp via Evolution.

    São DOIS wires diferentes, e confundi-los é ficar cego para a mídia:

    - Baileys (`evolution`): ``/chat/getBase64FromMediaMessage/{instância}``,
      corpo ``{"message": {"key": {"id": ...}}}`` — o id basta.
    - GO (`evolution-go`): ``/message/downloadmedia``, corpo
      ``{"message": <waE2E.Message>}`` — a mensagem INTEIRA é obrigatória,
      porque é ela que traz `mediaKey`/`directPath`/`fileEncSha256`.

    O caminho do GO estava marcado como "shape a confirmar" e devolvia None:
    com o agente ligado, toda foto, áudio e PDF do segurado ficaria invisível.
    O shape foi confirmado em 28/07/2026 no próprio Swagger do fork
    (`/swagger/doc.json`, `DownloadMediaStruct` = `{message: waE2E.Message}`),
    que também mostrou que `/chat/getBase64FromMediaMessage` responde 404 ali —
    são forks distintos mesmo.

    O download em si é o do Observador (`observer_media._download_media`), que
    já trata tamanho máximo e base64 com prefixo `data:`. Um motor só.
    """
    base = str(integration.get("base_url") or "").rstrip("/")
    apikey = str(integration.get("token") or "")
    inst = str(integration.get("instance_id") or "")
    if not (base and apikey):
        return None
    if str(integration.get("provider") or "").strip().lower() == "evolution-go":
        if not raw_message:
            logger.warning("[WEBHOOK EVOLUTION-GO] sem a mensagem crua não há como baixar a mídia")
            return None
        try:
            from app.services.atlas.observer_media import _download_media

            return await _download_media(integration, raw_message)
        except Exception as exc:  # noqa: BLE001 — mídia nunca derruba o atendimento
            from app.services.atlas.observer_media import _motivo_da_falha

            logger.error("[WEBHOOK EVOLUTION-GO] download de mídia falhou: %s",
                         _motivo_da_falha(exc))
            return None
    if not (inst and message_id):
        return None
    try:
        import base64 as b64mod

        async with httpx.AsyncClient(timeout=45.0) as client:
            res = await client.post(
                f"{base}/chat/getBase64FromMediaMessage/{inst}",
                headers={"apikey": apikey},
                json={"message": {"key": {"id": message_id}}, "convertToMp4": False},
            )
            if res.status_code >= 400:
                logger.error(f"[WEBHOOK EVOLUTION] media download http_{res.status_code}")
                return None
            j = res.json() if res.content else {}
            b64 = str(j.get("base64") or "")
            if b64.startswith("data:") and "," in b64[:100]:
                b64 = b64.split(",", 1)[1]
            if not b64:
                return None
            return b64mod.b64decode(b64), str(j.get("mimetype") or "")
    except Exception as e:  # noqa: BLE001
        logger.error(f"[WEBHOOK EVOLUTION] media download failed: {type(e).__name__}")
        return None


async def _upload_media_bytes(company_id: str, blob: bytes, mime: str, ext: str, bucket: str = "chat-media") -> Optional[str]:
    """Sobe bytes de mídia no storage e devolve URL pública.
    Imagem → chat-media; documento/áudio → chat-docs (chat-media só aceita imagem)."""
    try:
        today = date.today().isoformat()
        file_path = f"{company_id}/{today}/{uuid4()}{ext}"
        await asyncio.to_thread(
            lambda: supabase.client.storage.from_(bucket).upload(
                file_path, blob, {"content-type": mime or "application/octet-stream", "cache-control": "3600"}
            )
        )
        return _url_de_midia(supabase.client, bucket, file_path)
    except Exception as e:  # noqa: BLE001
        logger.error(f"[WEBHOOK EVOLUTION] media upload failed: {type(e).__name__}")
        return None


def _item_do_inbound(payload_dict: dict) -> tuple:
    """`(tipo, conteudo, midia)` deste evento — PURA, e é a única classificação.

    🔴 SPEC-EXTRA-001.2 §6.2: foto, áudio e documento deixam de ser "outro
    caminho". 📊 27,06% das rajadas do acervo têm mídia, e havia rajadas 100%
    mídia — nessas, o buffer não via NADA e cada foto virava um turno próprio.

    ⚠️ A legenda viaja NO MESMO item que o arquivo: são uma fala só, e separá-las
    é o que fazia o agente responder a foto antes de ler o que ela explicava.
    """
    dados = payload_dict or {}
    texto = str((dados.get("text") or {}).get("message") or "")
    imagem = dados.get("image") or None
    audio = dados.get("audio") or None
    documento = dados.get("document") or None
    if imagem:
        return "image", str(imagem.get("caption") or texto or ""), dict(imagem)
    if audio:
        return "audio", texto, dict(audio)
    if documento:
        # O texto extraído do PDF já vem montado pelo caminho da Evolution.
        return "document", texto, dict(documento)
    return "text", texto, None


async def _buffer_or_dispatch_text(payload_dict: dict, phone: str) -> dict:
    """Humanização S17-9: a mensagem entra no buffer e espera a rajada.

    ⚠️ O nome ficou: o escopo é que cresceu. Desde a SPEC-EXTRA-001.2 isto é o
    ÚNICO portão de entrada do buffer — texto, foto, áudio e documento.

    O `escopo` NÃO é derivado aqui: quem o deriva é `add_message`
    (`_integration_id` → `connectedPhone` → rótulo fixo), e uma segunda cópia
    dessa cadeia divergiria da primeira (CLAUDE.md §5).
    """
    tipo, conteudo, midia = _item_do_inbound(payload_dict)
    buffer_service = await get_message_buffer_service()
    await buffer_service.add_message(
        phone=phone,
        message=conteudo,
        company_id="pending",
        user_id="pending",
        integration={},
        payload=payload_dict,
        tipo=tipo,
        midia=midia,
        wa_message_id=str(payload_dict.get("messageId") or ""),
    )
    return {"status": "buffered", "phone": f"...{str(phone)[-4:]}"}


def _notify_disconnect_background(integration: dict, state: str) -> None:
    """S17-3: alerta de desconexão via instância-plataforma (nunca e-mail)."""
    try:
        from app.services.whatsapp.alerts import send_disconnect_alert

        send_disconnect_alert(integration, state)
    except Exception as e:  # noqa: BLE001
        logger.error(f"[WEBHOOK ALERT] disconnect alert failed: {type(e).__name__}")


@router.post("/api/v1/webhook/z-api/{token}")
@limiter.limit("240/minute")
async def z_api_webhook_token(token: str, request: Request, background_tasks: BackgroundTasks):
    """Webhook Z-API com token por integração (substitui a resolução por telefone)."""
    integration = await _resolve_webhook_integration("z-api", token)
    payload_dict = await request.json()
    try:
        payload = ZAPIWebhookPayload(**payload_dict)
    except Exception:
        return {"status": "ignored", "reason": "invalid_payload"}
    if payload.isGroup or payload.fromMe:
        return {"status": "ignored"}
    if not payload.text and not payload.audio and not payload.image:
        return {"status": "ignored", "reason": "no_content"}
    if await _is_duplicate_namespaced("z-api", payload.messageId):
        return {"status": "ignored", "reason": "duplicate"}
    payload_dict["_integration_id"] = integration.get("id")
    # 🔴 DESVIO DE MÍDIA Nº 2, MORTO (§6.2): texto e mídia pelo mesmo portão.
    return await _buffer_or_dispatch_text(payload_dict, payload.phone)


async def _registrar_retorno_de_cobranca(integration: dict, body: Any) -> None:
    """SPEC-EXTRA-001 §4 — o cliente que RESPONDE a uma cobrança é ouvido.

    📊 Medido em 07/09/2026: 4/4 agentes `attendance` desligados, e o canal da
    Resulta é uma instância `purpose='observer'`. Nesse arranjo o evento morre
    duas linhas abaixo — `observer_tap` CONSOME e devolve, o background nunca
    nasce, `_handle_evolution_like_inbound` nunca roda. O segurado responde
    *"já paguei"* ao boleto que a corretora mandou e **ninguém fica sabendo**.

    🔴 **Por isso o registro mora no ENDPOINT, e antes do tap.** Qualquer lugar
    depois dele registraria só as corretoras que já têm agente ligado — que hoje
    são zero.

    ⛔ Ele só ESCREVE no ledger da cobrança. Não responde, não envia, não liga
    agente, não toca `conversations`. E não derruba o webhook: toda falha vira
    um `warning` sem PII e o fluxo segue exatamente como seguia.
    """
    try:
        from app.services.billing_replies import registrar_retorno
        from app.services.whatsapp.evolution_go_events import go_event_to_v2_envelope
        from app.services.whatsapp.evolution_inbound import normalize_evolution_inbound

        company_id = str(integration.get("company_id") or "")
        if not company_id:
            return
        # ⚠️ UMA regra de extração, e não duas. `go_event_to_v2_envelope` é pura
        # e devolve o envelope v2 intacto quando ele JÁ é v2 (o caso da rota
        # Evolution legada), então as duas rotas entram por aqui sem que a
        # forma do evento seja reinterpretada em dois lugares — o defeito do
        # CLAUDE.md §9.4 que a SPEC-083 pagou três vezes.
        envelope = go_event_to_v2_envelope(body if isinstance(body, dict) else {})
        dados = normalize_evolution_inbound(envelope)
        # Eco da própria corretora e grupo NUNCA são retorno de cobrança: o
        # boleto foi para um número individual, e quem responde é ele.
        if dados.get("from_me") or dados.get("is_group"):
            return
        phone = str(dados.get("phone") or "")
        texto = str(dados.get("text") or "").strip()
        # Mídia sem legenda sai daqui sem rótulo (P-097.1-MIDIA-SEM-TEXTO):
        # adivinhar o conteúdo de um áudio para SUPRIMIR a cobrança dele seria
        # decidir pelo cliente com base num palpite.
        if not phone or not texto:
            return
        # 🔴 A ATENDENTE não é o cliente (painel 07/09, B1 das duas lentes): no
        #    modo `equipe` o ledger tem `to_phone = team_number`, e uma mensagem
        #    dela ao canal da corretora encerraria a cobrança do segurado.
        #    A mesma lista que protege a LEITURA (`contexto_de_cobranca`) protege
        #    a ESCRITA.
        # 🔴 E o hook está no caminho quente de TODO inbound (red team P2):
        #    2 s é o teto — passou disso, o atendimento segue e o retorno é
        #    perdido com um warning, nunca o contrário.
        from app.services.billing_replies import telefones_da_equipe_de_cobranca

        async def _registrar() -> None:
            equipe = await telefones_da_equipe_de_cobranca(company_id)
            if equipe is None:
                # 🔴 FALHA FECHADA (juiz fresco 07/09, B-J2): sem saber quem é a
                #    equipe, este texto pode ser da atendente — e o registro
                #    escreve estado TERMINAL. Não sei → não escrevo.
                logger.warning("[COBRANCA RETORNO] não registrado: equipe ilegível")
                return
            await registrar_retorno(company_id, phone, texto, excluir_phones=equipe)

        await asyncio.wait_for(_registrar(), timeout=2.0)
    except asyncio.TimeoutError:
        logger.warning("[COBRANCA RETORNO] não registrado: banco lento (>2s); o atendimento seguiu")
    except Exception as e:  # noqa: BLE001
        # ⛔ Sem telefone, sem texto do cliente, sem nome — só o tipo do erro.
        logger.warning("[COBRANCA RETORNO] não registrado: %s", type(e).__name__)


async def _pausar_quando_a_atendente_fala(integration: dict, body: Any) -> None:
    """A atendente respondeu e o agente está DESLIGADO — a conversa cala mesmo assim.

    🔴 O DEFEITO C' DE 09/09/2026, medido no primeiro dia de piloto.

    📊 430 mensagens `fromMe` humanas naquele dia, 11 tentativas de pausa. Com o
    agente desligado, `observer_tap` CONSOME o evento (`observer_intake.py:812`)
    e o pipeline — onde mora o ramo `fromMe` que pausa — nunca roda. A conversa
    que a Regina assumiu ficava `open`, e no instante em que o Founder ligasse o
    agente ela voltava a ser do robô.

    🔴 **POR QUE AQUI, DEPOIS DO TAP E ANTES DO `return`, e não nas duas outras
    formas que estavam na mesa** (a decisão pedida em voz alta, para o próximo
    leitor não a refazer):

      (a) *antes* do tap, como `_registrar_retorno_de_cobranca` — funciona, mas
          roda TAMBÉM quando o agente está ligado, e aí o ramo `fromMe` do
          pipeline pausa de novo: **dois UPDATEs para a mesma pausa**, um deles
          sem o `conversation_id` que o espelho devolve. Duplicação de escrita.
      (b) *dentro* do tap (`from_me and not insurer`) — o Observador teria de
          conhecer `#nota`, a voz própria do robô e a pausa. Ele é MUDO por
          construção e não decide nada sobre fala (`observer_intake.py:1-20`);
          e as três regras passariam a existir em dois arquivos, que é como uma
          delas fica para trás (CLAUDE.md §5).
      (c) **aqui**: só roda quando o tap CONSUMIU — exatamente o caso em que o
          pipeline não vai rodar. Os dois caminhos são mutuamente exclusivos,
          então a pausa acontece **uma vez** e as regras continuam morando neste
          arquivo, ao lado do ramo `fromMe` que as escreveu.

    ⛔ E ela obedece às mesmas três exceções, sem reescrevê-las: eco da própria
    voz não pausa, `#nota` não pausa, seguradora e grupo não são atendente.

    ⚠️ Teto de 2 s e falha aberta, como o hook da cobrança: o webhook responde
    ao WhatsApp de qualquer jeito.
    """
    try:
        from app.services.whatsapp.evolution_go_events import go_event_to_v2_envelope

        empresa = str(integration.get("company_id") or "")
        if not empresa:
            return
        dados = normalize_evolution_inbound(
            go_event_to_v2_envelope(body if isinstance(body, dict) else {}))
        # Só o `fromMe` de uma conversa individual com telefone RESOLVÍVEL. Um
        # `@lid` sem alternativo chega aqui com `phone` vazio, e pausar sem
        # saber QUEM é a contraparte pausaria a conversa de outra pessoa.
        if not dados.get("from_me") or dados.get("is_group"):
            return
        telefone = str(dados.get("phone") or "")
        if not telefone:
            return
        texto = str(dados.get("text") or "")

        async def _pausar() -> None:
            from app.services.atlas.espelho_chat import pausar_por_intervencao_humana
            from app.services.atlas.observer_intake import _br_variants, insurer_allowlist
            from app.services.whatsapp.voz_propria import e_a_nossa_propria_voz

            # A URA da seguradora não é a atendente da corretora, e a conversa
            # com ela não é a do segurado.
            if any(v in insurer_allowlist() for v in _br_variants(telefone)):
                return
            if texto and e_a_nossa_propria_voz(empresa, telefone, texto):
                logger.info("[ESPELHO] eco da própria voz (agente desligado) — "
                            "nada a pausar")
                return
            if texto and _e_uma_anotacao(texto):
                logger.info("[NOTA] anotação da atendente (agente desligado) — "
                            "a conversa NÃO é pausada")
                return
            await pausar_por_intervencao_humana(
                company_id=empresa, counterparty=telefone)

        await asyncio.wait_for(_pausar(), timeout=2.0)
    except asyncio.TimeoutError:
        logger.warning("[ESPELHO] pausa por intervenção não registrada: banco "
                       "lento (>2s); o webhook seguiu")
    except Exception as e:  # noqa: BLE001
        logger.warning("[ESPELHO] pausa por intervenção não registrada: %s",
                       type(e).__name__)


@router.post("/api/v1/webhook/evolution/{token}")
@limiter.limit("240/minute")
async def evolution_webhook_token(token: str, request: Request, background_tasks: BackgroundTasks):
    """Webhook Evolution API v2 com token por integração (SPEC-017)."""
    integration = await _resolve_webhook_integration("evolution", token)
    body = await request.json()
    await _registrar_retorno_de_cobranca(integration, body)
    return await _handle_evolution_like_inbound(integration, body, background_tasks, "evolution")


@router.post("/api/v1/webhook/evolution-go/{token}")
@limiter.limit("240/minute")
async def evolution_go_webhook_token(token: str, request: Request, background_tasks: BackgroundTasks):
    """Webhook Evolution GO (SPEC-034 — migração do canal p/ GO, founder 14/07).

    O GO entrega o evento whatsmeow; convertemos para o envelope v2 e reusamos
    TODO o pipeline (normalizador, formulário nativo, buffer, dispatch)."""
    integration = await _resolve_webhook_integration("evolution-go", token)
    body = await request.json()

    # SPEC-EXTRA-001 §4 — ANTES do tap, porque o tap CONSOME (📊 4/4 agentes
    # desligados; a Resulta recebe por instância `purpose='observer'`).
    await _registrar_retorno_de_cobranca(integration, body)

    # ATLAS (SPEC-038 Bloco A): captura passiva ANTES do pipeline.
    # purpose='observer' consome (instância dedicada, muda por construção);
    # purpose='attendance' = TAP: grava o que for de seguradora e o fluxo
    # segue INTACTO. O tap jamais derruba o atendimento.
    try:
        from app.services.atlas.observer_intake import observer_tap

        _observed = await observer_tap(integration, body if isinstance(body, dict) else {})
        if _observed is not None:
            # 🔴 O TAP CONSUMIU = O AGENTE ESTÁ DESLIGADO, e o ramo `fromMe` do
            # pipeline — o que pausa a conversa — não vai rodar. Ver a função.
            await _pausar_quando_a_atendente_fala(integration, body)
            return _observed
    except Exception as e:  # noqa: BLE001
        logger.error(f"[WEBHOOK EVOLUTION-GO] atlas tap error: {type(e).__name__}")

    from app.services.whatsapp.evolution_go_events import go_event_to_v2_envelope

    env = go_event_to_v2_envelope(body if isinstance(body, dict) else {})
    if env.get("event") == "unknown":
        # Shape ainda não confirmado ao vivo: loga as CHAVES (nunca conteúdo)
        # para eu ajustar o conversor em minutos no primeiro teste real.
        keys = list(body)[:12] if isinstance(body, dict) else type(body).__name__
        logger.warning(f"[WEBHOOK EVOLUTION-GO] payload não reconhecido keys={keys}")
        return {"status": "ignored", "reason": "unrecognized_payload"}
    return await _handle_evolution_like_inbound(integration, env, background_tasks, "evolution-go")


async def _handle_evolution_like_inbound(
    integration: dict, body: dict, background_tasks: BackgroundTasks, provider_label: str
):
    """Pipeline compartilhado Evolution v2 / Evolution GO (body já no envelope v2)."""
    event = str(body.get("event") or "").strip().lower().replace("_", ".")
    if event == "connection.update":
        state = connection_state_from_payload(body) or "unknown"
        logger.info(f"[WEBHOOK EVOLUTION] connection.update state={state}")
        try:
            from app.services.whatsapp.channel_state import normalizar_estado

            def _update_status():
                supabase.client.table("integrations").update(
                    {"channel_status": normalizar_estado(state),
                     "last_seen_at": datetime.now(timezone.utc).isoformat()}
                ).eq("id", integration.get("id")).execute()
            await asyncio.to_thread(_update_status)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[WEBHOOK EVOLUTION] status update failed: {type(e).__name__}")
        if state in ("close", "closed", "disconnected", "logout"):
            background_tasks.add_task(_notify_disconnect_background, integration, state)
        return {"status": "ok", "event": "connection.update", "state": state}

    normalized = normalize_evolution_inbound(body)
    if normalized["skip"]:
        # 🔴 SPEC-EXTRA-001.4 C — AGENTE / EU CUIDO digitado NO GRUPO de suporte.
        #    ⚠️ Só chega quando o canal entrega grupos (📊 17/09: instâncias são
        #    criadas com `ignoreGroups: True`). A palavra tem de SER a mensagem e o
        #    grupo tem de ser o destino de suporte da corretora (`_e_da_equipe`).
        #    ⚠️ `from_me` também: a atendente pode responder do próprio WhatsApp da
        #    corretora, e aí o evento chega marcado `from_me` antes de `group`.
        _chave_msg = ((body.get("data") or {}).get("key") or {}) if isinstance(body, dict) else {}
        if (normalized.get("text") and str(_chave_msg.get("remoteJid") or "").endswith("@g.us")
                and normalized.get("skip_reason") in ("group", "from_me")):
            try:
                from app.services.dispatch_router import ler_palavra_da_equipe

                await ler_palavra_da_equipe(
                    str(integration.get("company_id") or ""), normalized.get("text"),
                    chat=str(_chave_msg.get("remoteJid") or ""), eh_grupo=True)
            except Exception as e:  # noqa: BLE001
                logger.warning("[WEBHOOK] palavra do grupo não lida (%s)", type(e).__name__)
        # Mensagem MANUAL da própria corretora (fromMe) numa conversa com
        # dispatch ATIVO: registra no espelho (humano copilotando a URA).
        if normalized.get("skip_reason") == "from_me" and normalized.get("phone"):
            # A ATENDENTE RESPONDEU PELO CELULAR. Duas coisas acontecem aqui, e
            # as duas ANTES de qualquer teste de agente ligado.
            #
            # 🔴 A CONDIÇÃO EXIGIA TEXTO ATÉ 14/08/2026 — e isso era um buraco.
            #
            # 📊 Áudio é o formato mais comum no WhatsApp (o próprio
            # `webhook.py:546` diz isso). A atendente que respondesse por áudio,
            # foto ou localização não pausava a IA: ela gravava um áudio para o
            # segurado e o agente respondia por cima, com duas vozes na mesma
            # conversa. Agora QUALQUER `fromMe` humano pausa.
            #
            # 🔴 O bloco de captura logo abaixo roda dentro de
            # `if not await attendance_agent_active(...)` — ou seja, só quando o
            # agente JÁ está desligado, que é exatamente o caso em que não há
            # nada para pausar. Com o agente LIGADO, a resposta manual da
            # atendente não era vista, não entrava no chat e não calava ninguém:
            # duas pessoas responderiam o mesmo cliente.
            #
            # 1) a mensagem dela aparece no chat do dashboard
            # 2) o agente para NAQUELA conversa — e só nela; nas outras ele
            #    segue trabalhando (decisão do Founder, 06/08/2026)
            # 🔴 `_fomos_nos` NASCE AQUI, FORA DO `try` — o juiz de confirmação
            # mostrou por quê.
            #
            # ⚠️ Ele só era atribuído DENTRO do bloco abaixo. Se aquele bloco
            # estourasse antes da atribuição (um import que falha, o Espelho
            # fora do ar), a chamada a `note_manual_outbound` mais adiante
            # levantaria `NameError`, cairia no próprio `except` — e a
            # intervenção humana deixaria de ser registrada POR INTEIRO, com um
            # `warning` genérico. Antes do BLOCO C a chamada não dependia de
            # variável nenhuma; foi o conserto que criou a dependência.
            #
            # 🔴 `False` é a inicialização certa, e não é arbitrária: sem prova
            # de que a voz é nossa, o registro segue o caminho de sempre — o de
            # atribuir a mensagem a uma pessoa. Um eco perdido é recuperável; o
            # trabalho da atendente sumindo do registro, não.
            _fomos_nos = False
            # 🔴 `_e_nota` NASCE AQUI, FORA DO `try`, PELO MESMO MOTIVO.
            #
            # ⚠️ Eu escrevi a primeira versão com ele DENTRO do bloco abaixo — e
            # é literalmente o defeito que o juiz da SPEC-093 achou em
            # `_fomos_nos`, três linhas acima, com o comentário explicando por
            # quê. Se o Espelho cair antes da atribuição, o `elif _e_nota` mais
            # adiante levanta `NameError`.
            #
            # 🔴 `False` é a inicialização certa e não é arbitrária: sem prova de
            # que é anotação, a mensagem segue o caminho de sempre — PAUSA a IA.
            # Uma nota que pausou por engano é um clique para religar; um robô
            # falando por cima da atendente é duas vozes na mesma conversa.
            _e_nota = False
            # 🔴 SPEC-093-B BLOCO B — NASCE AQUI, FORA DO `try`, PELO MESMO MOTIVO
            # que `_fomos_nos` e `_e_nota` acima: se o Espelho cair antes da
            # atribuição, o bloco da sombra logo abaixo levantaria `NameError` e
            # levaria junto o registro da intervenção humana.
            _conversa_espelhada = None
            try:
                from app.services.atlas.espelho_chat import (
                    espelhar_no_chat, pausar_por_intervencao_humana,
                )

                _empresa = str(integration.get("company_id") or "")
                _texto = str(normalized.get("text") or "")
                _tipo = str(normalized.get("msg_type") or "text")

                # 🔴 QUEM ESCREVEU ISTO? — a pergunta que faltava.
                #
                # 📊 14/08/2026: este ramo tratava TODO `fromMe` como "a
                # atendente respondeu". Mas a resposta do próprio agente volta
                # por aqui — está medido e documentado desde 06/08
                # (`espelho_chat`, guarda de eco). Consequência: o agente
                # responderia UMA vez, pausaria a si mesmo e emudeceria para
                # sempre naquela conversa, com o vigia mandando
                # "⏳ AINDA SEM ATENDIMENTO" ao grupo 30 min depois.
                #
                # O produto agora anota a digital do que vai dizer antes de
                # falar (`whatsapp_service.send_message`) e reconhece aqui.
                # Em erro, `e_a_nossa_propria_voz` devolve False e a IA cala —
                # a direção segura.
                from app.services.whatsapp.voz_propria import e_a_nossa_propria_voz

                _fomos_nos = e_a_nossa_propria_voz(_empresa, normalized["phone"], _texto)

                # O espelho continua acontecendo nos dois casos: a mensagem
                # apareceu no WhatsApp e tem de aparecer no chat. Quem
                # deduplica é o índice único, não este `if`.
                # ⚠️ O retorno passou a ser GUARDADO (SPEC-093-B): `espelhar_no_chat`
                # sempre devolveu o id da conversa (`espelho_chat.py:303`) e ele era
                # descartado aqui. Guardá-lo não muda um byte do comportamento — é a
                # única forma de a sombra saber DE QUAL conversa é esta resposta sem
                # uma segunda consulta por telefone.
                _conversa_espelhada = await espelhar_no_chat(
                    company_id=_empresa,
                    counterparty=str(normalized["phone"]),
                    texto=_texto,
                    msg_type=_tipo, direcao="out",
                    message_id=str(normalized.get("message_id") or ""),
                    quando_iso=datetime.now(timezone.utc).isoformat())

                # =============================================================
                # 🔴 SPEC-090 BLOCO C — A NOTA NÃO PAUSA A IA
                # =============================================================
                #
                # 📊 Desde 14/08, QUALQUER `fromMe` humano pausa a IA, e a regra
                # está certa: antes dela a atendente respondia por áudio e o
                # agente falava por cima — *"duas vozes na mesma conversa"*.
                #
                # ⛔ **Mas ela transformaria toda anotação em intervenção.** A
                # Regina escreve *"#nota o robô perguntou a placa duas vezes"* e
                # o robô PARA DE ATENDER. Anotar viraria assumir, que é
                # exatamente o que o Founder mandou não fazer.
                #
                # ⚠️ A exceção é ESTREITA de propósito: o prefixo tem de abrir a
                # mensagem. *"o robô errou #nota"* não é nota — é intervenção, e
                # pausa. Uma exceção larga vira o buraco que 14/08 fechou.
                #
                # ⚠️ **E aqui a nota chega com `origem='whatsapp'`, que é a
                # verdade:** este webhook é o ECO de uma mensagem que o WhatsApp
                # JÁ ENTREGOU. O produto não interceptou nada — ele soube depois.
                # A coluna existe para o relatório não dizer *"nenhuma vazou"*
                # sobre um dia em que sete foram lidas pelo segurado.
                if not _fomos_nos and _texto:
                    _e_nota = _e_uma_anotacao(_texto)
                    if _e_nota:
                        await _capturar_anotacao_do_whatsapp(
                            company_id=_empresa,
                            phone=str(normalized["phone"]), mensagem=_texto)

                if _fomos_nos:
                    logger.info("[ESPELHO] eco da própria voz — a IA continua "
                                "trabalhando nesta conversa")
                elif _e_nota:
                    # 🔴 O gate ③ inteiro é esta linha: NÃO pausa.
                    logger.info("[NOTA] anotação da atendente — a IA CONTINUA "
                                "atendendo nesta conversa")
                else:
                    # 🔴 PELO ID DA CONVERSA, E O TELEFONE SÓ COMO PLANO B.
                    #
                    # 📊 09/09/2026: a pausa era gravada por `user_phone`, e num
                    # chat por `@lid` o "telefone" era o LID — a pausa caía numa
                    # conversa-fantasma e a real seguia com o robô solto. O
                    # `telefone_do_evento` conserta o telefone; este argumento
                    # dispensa a pergunta: `espelhar_no_chat` ACABOU de devolver
                    # o id da linha em que esta mensagem entrou.
                    await pausar_por_intervencao_humana(
                        company_id=_empresa, counterparty=str(normalized["phone"]),
                        conversation_id=_conversa_espelhada)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[ESPELHO] intervenção humana não registrada: {type(e).__name__}")

            # 🔴 A NOTA NÃO ASSUME O ATENDIMENTO — e este é o segundo lugar
            #    onde "anotar viraria assumir", que a SPEC só viu no primeiro.
            #
            # 📊 `note_manual_outbound(foi_humano=True)` faz TRÊS escrituras
            # duráveis (SPEC-093 BLOCO C.1): a marca na sessão,
            # `work_runs.unblock_state = 'assumido_por_humano'` e um
            # `work_events` de ator `user`.
            #
            # ⛔ **E ela dispara no cenário exato do piloto:** a Regina está
            # olhando a conversa com a SEGURADORA — é onde a URA trava e onde
            # ela destrava. Anotar ali marcaria o acionamento como assumido por
            # humano, que é o oposto do que o Founder pediu.
            #
            # ⚠️ E `foi_humano=False` seria pior ainda: creditaria ao ROBÔ uma
            # mensagem que uma pessoa escreveu — o BLOCO C.1 ao contrário.
            #
            # ✅ Pular não perde nada: `espelhar_no_chat` acima já registrou a
            # mensagem nos dois casos, e a autoria da nota fica em
            # `notas_da_atendente`, com telefone e origem.
            if _e_nota:
                logger.info("[NOTA] anotação NÃO conta como assunção humana — "
                            "o acionamento segue como estava")
            try:
                from app.services.dispatch_router import note_manual_outbound

                # 🔴 `foi_humano` — SPEC-093 BLOCO C, conserto do painel.
                #
                # ⚠️ Esta chamada está FORA do `if _fomos_nos` acima, e ficou assim
                # de propósito: o espelho tem de registrar os dois casos. Mas
                # com as escritas duráveis do C.1, deixar de dizer QUEM falou
                # gravaria `assumido_por_humano` para a resposta que o próprio
                # Cérebro acabou de mandar.
                #
                # `_fomos_nos` já estava calculado vinte linhas acima. Só
                # faltava usá-lo aqui.
                #
                # 🔴 SPEC-090 BLOCO C — `_e_nota` corta a chamada INTEIRA.
                #    Ver o comentário logo acima do `try`: nem `True` nem
                #    `False` em `foi_humano` seriam a resposta certa para uma
                #    anotação. A resposta certa é **não marcar nada**.
                if not _e_nota:
                    await note_manual_outbound(
                        str(integration.get("company_id") or ""), str(normalized["phone"]), str(normalized["text"]),
                        foi_humano=not _fomos_nos,
                    )
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[WEBHOOK EVOLUTION] manual outbound note failed: {type(e).__name__}")
            # SPEC-045 — MODO OBSERVAÇÃO: a resposta da ATENDENTE HUMANA pelo
            # celular (fromMe) é o lado de ouro da conduta — captura no cofre
            # do Espelho quando o agente está desligado e não é seguradora.
            try:
                # SPEC-063 Bloco A — mesma troca do portao de fala, pelo motivo
                # inverso: aqui queremos CAPTURAR a resposta da atendente humana.
                # `attendance_observation_mode` so era True com agente existente
                # e desligado; corretora SEM agente nenhum — que e a mais humana
                # de todas — nao tinha o lado de ouro capturado.
                from app.services.atlas.attendance_capture import (
                    attendance_agent_active, capture_channel_message,
                )
                from app.services.atlas.observer_intake import _br_variants, insurer_allowlist

                _company = str(integration.get("company_id") or "")
                _phone = str(normalized["phone"])
                _is_insurer = any(v in insurer_allowlist() for v in _br_variants(_phone))
                if _company and not _is_insurer and not await attendance_agent_active(_company):
                    await capture_channel_message(
                        _company, str(integration.get("identifier") or ""), _phone,
                        str(normalized["text"]), "out", normalized.get("message_id"),
                    )
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[WEBHOOK EVOLUTION] observation fromMe capture failed: {type(e).__name__}")
            # 🔴 SPEC-093-B BLOCO B — a atendente respondeu pelo celular.
            #
            # 📊 §1.3: `work_events` com ator humano = 0 em 35.705. O trabalho da
            # Regina não deixava rastro nenhum. Aqui ele deixa — e **sem o texto**:
            # o que fica gravado é o canal, e mais nada.
            #
            # ⛔ Os dois `not` são a regra, não zelo: o eco da nossa própria voz
            # (`_fomos_nos`) não é uma pessoa respondendo, e a anotação (`_e_nota`)
            # tem evento próprio, gravado por `a_nota_da_atendente`.
            #
            # ⚠️ E ele mora no FIM do ramo, depois da captura, por uma razão
            # medida: `test_quem_fala_primeiro_cala_o_outro` exige que
            # `espelhar_no_chat` e `attendance_agent_active` caibam nos mesmos
            # 3.000 caracteres de código do ramo `fromMe` — é assim que aquele
            # guarda prova que o espelho vem ANTES do teste de agente ligado.
            # 📊 Escrito logo depois do espelho, este bloco empurrava
            # `attendance_agent_active` para FORA da janela e deixava o guarda
            # vermelho. A sombra não pode custar a prova de outra SPEC.
            if _conversa_espelhada and not _fomos_nos and not _e_nota:
                try:
                    from app.services.claims_shadow import registrar_gesto

                    await registrar_gesto(
                        supabase, company_id=str(integration.get("company_id") or ""),
                        conversation_id=str(_conversa_espelhada),
                        event_type="claims.humano_respondeu",
                        payload={"canal": "whatsapp"},
                    )
                except Exception as e:  # noqa: BLE001
                    logger.warning("[SOMBRA] resposta humana não registrada (%s)",
                                   type(e).__name__)
        return {"status": "ignored", "reason": normalized["skip_reason"]}
    if await _is_duplicate_namespaced(provider_label, normalized["message_id"]):
        return {"status": "ignored", "reason": "duplicate"}

    # F1 — mídia do cliente (imagem/PDF/áudio): baixa via Evolution, sobe no
    # storage e entra no fluxo normal (visão p/ imagem; texto extraído p/ doc).
    media = normalized.get("media")
    text_message = normalized["text"]
    image_payload = None
    audio_payload = None
    documento_payload = None
    if media:
        blob_mime = None
        # Caminho preferido: webhookBase64=true entrega a mídia no próprio evento.
        if media.get("base64"):
            try:
                import base64 as _b64

                raw = str(media["base64"])
                if raw.startswith("data:") and "," in raw[:100]:
                    raw = raw.split(",", 1)[1]
                blob_mime = (_b64.b64decode(raw), str(media.get("mimetype") or ""))
            except Exception:  # noqa: BLE001
                blob_mime = None
        if blob_mime is None:
            # Fallback: download via API (retry 1x — o store da Evolution pode
            # persistir a mensagem DEPOIS do webhook disparar).
            blob_mime = await _download_evolution_media(
                integration, normalized["message_id"], normalized.get("raw_message"))
            if blob_mime is None:
                await asyncio.sleep(2.5)
                blob_mime = await _download_evolution_media(
                    integration, normalized["message_id"], normalized.get("raw_message"))
        if blob_mime:
            blob, mime = blob_mime
            mime = mime or str(media.get("mimetype") or "")
            company_for_media = str(integration.get("company_id") or "")
            if media["kind"] == "image":
                ext = ".png" if "png" in mime else ".jpg"
                url = await _upload_media_bytes(company_for_media, blob, mime or "image/jpeg", ext)
                if url:
                    image_payload = {"imageUrl": url, "caption": media.get("caption")}
            elif media["kind"] == "document":
                fname = str(media.get("file_name") or "documento.pdf")
                ext = os.path.splitext(fname)[1].lower() or ".pdf"
                url = await _upload_media_bytes(company_for_media, blob, mime or "application/pdf", ext, bucket="chat-docs")
                doc_text = None
                if url:
                    from app.services.vision_service import extract_document_text

                    doc_text = await extract_document_text(url, fname)
                base_txt = media.get("caption") or MARCA_DO_DOCUMENTO % fname
                if doc_text:
                    text_message = f"{base_txt}\n\n{CABECALHO_DO_DOCUMENTO % fname}\n{doc_text}\n[FIM DO DOCUMENTO]"
                else:
                    text_message = f"{base_txt}\n(não foi possível ler o conteúdo do documento — peça para reenviar ou colar o texto)"
                # 🔴 SPEC-093-B — O NOME DO ARQUIVO VIAJA COMO CAMPO, e não só dentro
                # do texto. Aqui ele é certo; no texto ele SOME quando o segurado manda
                # legenda junto (`base_txt` vira a legenda) e a extração falha.
                # ⚠️ Só o NOME, nunca a URL nem o conteúdo: quem lê isto é
                # `tipo_de_documento`, e o que sobrevive dela é um enum (§2).
                documento_payload = {"fileName": fname}
            elif media["kind"] == "audio":
                url = await _upload_media_bytes(company_for_media, blob, mime or "audio/ogg", ".ogg", bucket="chat-docs")
                if url:
                    audio_payload = {"audioUrl": url}
        else:
            logger.warning("[WEBHOOK EVOLUTION] mídia recebida mas download falhou")
            if not text_message:
                text_message = "[Cliente enviou uma mídia que não consegui baixar — peça para reenviar]"

    payload_dict = {
        "connectedPhone": str(integration.get("identifier") or normalized.get("connected_phone") or ""),
        "phone": normalized["phone"],
        "isGroup": False,
        "fromMe": False,
        "text": {"message": text_message} if text_message else None,
        "image": image_payload,
        "audio": audio_payload,
        # 🔴 SPEC-093-B — o nome do arquivo do ramo `document`. O modelo pydantic o
        # IGNORA (ele não declara o campo); quem o lê é `nome_do_documento`, direto
        # no `payload_dict`, do mesmo jeito que `_integration_id` já viajava.
        "document": documento_payload,
        "messageId": normalized["message_id"],
        "senderName": normalized["sender_name"],
        "momment": normalized.get("timestamp"),
        "_integration_id": integration.get("id"),
        # A METADE QUE FALTAVA DA PONTE.
        #
        # O leitor já existia — `try_route_insurer_inbound` recebe
        # `interactive=payload_dict.get("interactive")` — mas quem MONTA o
        # payload nunca copiava o campo. Resultado: sempre `None`, e o
        # `flow_token` (que endereça a resposta do formulário e carrega os dois
        # telefones dentro dele) morria aqui, três linhas antes de ser usado.
        #
        # 📊 O canal de resposta a formulário foi provado no ar em 03/08/2026.
        # Sem esta linha ele nunca teria sido exercitado em produção: o motor
        # montaria a resposta e pausaria por falta de token, exatamente como
        # `evolution_inbound.py` já avisava em comentário — *"o caminho quente
        # do produto ainda não chama isto"*.
        "interactive": normalized.get("interactive"),
    }
    # 🔴 DESVIO DE MÍDIA Nº 3, MORTO (§6.2) — e era o mais caro dos três: este é
    # o caminho quente de `/evolution/{token}` e `/evolution-go/{token}`, por
    # onde passa o atendimento inteiro. O documento já caía no buffer; a
    # assimetria com foto e áudio era acidental.
    return await _buffer_or_dispatch_text(payload_dict, normalized["phone"])


def _e_uma_anotacao(mensagem: str) -> bool:
    """`#nota …` no começo? — SPEC-090 BLOCO C.

    ⚠️ **A decisão mora em `a_nota_da_atendente`, não aqui.** Uma segunda cópia
    da regra do prefixo divergiria da primeira, e a que ficasse para trás seria
    justamente a que deixa a nota virar mensagem para o segurado (§5).

    ⛔ **Import que falha devolve `False`, e a direção é a segura:** a mensagem
    segue o caminho de hoje — sai, e a atendente vê que saiu. O contrário
    (engolir por acidente) seria uma mensagem que a atendente acha que mandou e
    o segurado nunca recebeu.
    """
    try:
        from app.services.a_nota_da_atendente import e_nota
    except Exception as erro:  # noqa: BLE001
        logger.error("[NOTA] regra do prefixo indisponível (%s) — a mensagem "
                     "segue o caminho normal", type(erro).__name__)
        return False
    return bool(e_nota(mensagem))


async def _consumir_anotacao_do_painel(*, company_id: str, phone: str,
                                       mensagem: str) -> Dict[str, Any]:
    """Grava a anotação e **devolve sem enviar nada**.

    🔴 O gate ② da SPEC vive nesta função: nenhum caminho daqui chama
    `send_message`. ⛔ E ela nunca levanta — um erro ao gravar não pode virar um
    500 que faça a atendente reenviar a mesma nota, agora achando que falhou.
    """
    from app.core.database import create_async_supabase_client
    from app.services.a_nota_da_atendente import (
        ORIGEM_PAINEL, gravar_nota, travamento_mais_recente,
    )

    gravou, motivo = False, "erro"
    try:
        db = await create_async_supabase_client()
        conversa = await _conversa_do_telefone(db, company_id, phone)
        contexto = await travamento_mais_recente(db, company_id, conversa)
        gravou, motivo = await gravar_nota(
            db, company_id=company_id, texto_bruto=mensagem,
            origem=ORIGEM_PAINEL, conversation_id=conversa,
            work_run_id=contexto.get("work_run_id") or None,
            rota=contexto.get("rota", ""), tela=contexto.get("tela", ""))
    except Exception as erro:  # noqa: BLE001
        motivo = type(erro).__name__
        logger.warning("[NOTA] painel: não gravada (%s)", motivo)

    # ⚠️ `status` diz `anotada`, nunca `sent`. O painel precisa poder mostrar à
    #    atendente que aquilo virou anotação e **não foi para o segurado** — se
    #    a tela disser "enviado", ela vai achar que o cliente leu.
    return {"status": "anotada", "gravada": gravou, "motivo": motivo,
            "enviada": False}


async def _capturar_anotacao_do_whatsapp(*, company_id: str, phone: str,
                                         mensagem: str) -> None:
    """A anotação escrita no WhatsApp da atendente — SPEC-090 BLOCO C.

    ⚠️ **Aqui o produto NÃO interceptou nada.** Este caminho é o eco de uma
    mensagem que o WhatsApp já entregou (`evolution_inbound.py:847`). Por isso
    a linha nasce com `origem='whatsapp'`: ela diz a verdade sobre si mesma.

    ⛔ **Nunca levanta.** Uma anotação que não gravou é uma anotação perdida;
    uma exceção aqui derrubaria o tratamento do `fromMe` inteiro, e junto dele
    o espelho e a pausa por intervenção humana.
    """
    from app.core.database import create_async_supabase_client
    from app.services.a_nota_da_atendente import (
        ORIGEM_WHATSAPP, gravar_nota, travamento_mais_recente,
    )

    try:
        db = await create_async_supabase_client()
        conversa = await _conversa_do_telefone(db, company_id, phone)
        contexto = await travamento_mais_recente(db, company_id, conversa)
        await gravar_nota(
            db, company_id=company_id, texto_bruto=mensagem,
            origem=ORIGEM_WHATSAPP, conversation_id=conversa,
            work_run_id=contexto.get("work_run_id") or None,
            # ⛔ O telefone É gravado (é da equipe, não do segurado) e NUNCA
            #    é impresso — nem aqui, nem no log de erro de `gravar_nota`.
            autor_telefone=str(phone or ""),
            rota=contexto.get("rota", ""), tela=contexto.get("tela", ""))
    except Exception as erro:  # noqa: BLE001
        logger.warning("[NOTA] whatsapp: não capturada (%s)", type(erro).__name__)


async def _conversa_do_telefone(db, company_id: str, phone: str) -> Optional[str]:
    """A conversa daquele telefone naquela corretora, ou `None`.

    ⚠️ **`None` quando há mais de uma**, pela mesma regra do BLOCO A: 📊 medido
    em 26/08, 2 pares (corretora, telefone) têm mais de uma conversa e o pior
    caso tem 57. Uma nota pendurada na conversa errada é pior que uma nota solta
    — a solta ainda aparece na leitura do dia.
    """
    digitos = "".join(c for c in str(phone or "") if c.isdigit())
    if not digitos or not company_id:
        return None
    try:
        achado = await (db.client.table("conversations").select("id")
                        .eq("company_id", str(company_id))   # 🔴 §7
                        .eq("user_phone", digitos).limit(5).execute())
    except Exception as erro:  # noqa: BLE001
        logger.warning("[NOTA] conversa não resolvida (%s)", type(erro).__name__)
        return None
    linhas = achado.data or []
    return str(linhas[0]["id"]) if len(linhas) == 1 else None


@router.post("/api/webhook/send-message")
async def admin_send_message(
    payload: AdminSendMessagePayload,
    request: Request,
    _: bool = Depends(require_master_admin)
):
    """Admin send message - requires logged in user"""
    try:
        logger.info(f"[ADMIN SEND] Sending to {payload.phone}")
        parts = payload.session_id.split(":")
        if len(parts) < 3:
            raise HTTPException(status_code=400, detail="Invalid session_id")

        company_id = parts[2]
        agent_id = parts[3] if len(parts) > 3 and parts[3] != "default" else None

        # =====================================================================
        # 🔴 SPEC-098 R9 · CONSERTO 1 (red team B4) — QUEM PEDIU AINDA PODE?
        # =====================================================================
        #
        # 📊 Medido em 06/09/2026: a revalidação do ator (R9) tinha **ZERO**
        # chamadores. Ela morava dentro de `send_to_client_guarded`, e os 4
        # chamadores daquela função são jobs de sistema, sem pessoa por trás.
        # O único envio com um humano atrás é ESTE — a atendente respondendo
        # pelo painel — e ele nunca passou por lá.
        #
        # O `actor_user_id` chega no cabeçalho `X-Actor-User-Id`, carimbado pelo
        # nosso BFF (`app/api/dashboard/conversas/[id]/route.ts`) JUNTO da chave
        # interna. ⛔ Nunca vem do navegador direto: o cabeçalho só é lido
        # porque `require_master_admin` já provou que quem fala é a nossa casa.
        # Sem o cabeçalho (chamador antigo, job), o comportamento é o de hoje.
        #
        # ⛔ A pergunta é a MESMA de `platform_outbound` — a porta é uma só
        # (CLAUDE.md §5). E ela vem ANTES de `send_message`: perguntar depois de
        # enviar é enviar.
        ator = (request.headers.get("X-Actor-User-Id") or "").strip() or None
        if ator:
            from app.services.platform_outbound import ator_ainda_pode

            # 🔴 CONSERTO 2 — `work_run_id` fica None, e isso é a VERDADE deste
            # caminho: a atendente responde pelo painel, não há Work Run. 📊
            # `work_events.work_run_id` é NOT NULL (information_schema,
            # 06/09/2026), então a recusa aqui é anotada na FICHA da conversa
            # daquele telefone — o mesmo destino da 097.1
            # (`atendimento/acompanhamento.py::_registrar`). O `phone` vai
            # junto só para ACHAR a conversa; ele nunca é gravado.
            if not await ator_ainda_pode(company_id, ator, kind="atendimento_humano",
                                         summary=(payload.message or "")[:80],
                                         work_run_id=None,
                                         phone=(payload.phone or "")):
                raise HTTPException(
                    status_code=403,
                    detail="Quem pediu o envio não tem mais vínculo vigente nesta corretora.")

        integration = integration_service.get_whatsapp_integration(company_id, agent_id)

        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")

        # =====================================================================
        # 🔴 SPEC-090 BLOCO C — A ANOTAÇÃO, E É AQUI QUE O GATE ② É DE VERDADE
        # =====================================================================
        #
        # 📊 Este é o único caminho em que **o produto é o remetente**: ele
        # chama `whatsapp_service.send_message` logo abaixo. Interceptar aqui
        # é interceptação real — a mensagem provadamente não sai, e o teste
        # consegue contar `platform_sends`.
        #
        # ⚠️ O caminho do WhatsApp direto NÃO tem essa propriedade: `fromMe` é
        # o eco de uma mensagem que o WhatsApp já entregou. Lá a nota é
        # capturada com `origem='whatsapp'`, dizendo a verdade.
        #
        # ⛔ **O `return` vem ANTES do envio, e não é um detalhe de ordem.**
        # Gravar depois de enviar seria enviar.
        if payload.message and _e_uma_anotacao(payload.message):
            return await _consumir_anotacao_do_painel(
                company_id=company_id, phone=str(payload.phone),
                mensagem=str(payload.message))

        # ⚠️ Mesmo motivo do envio do agente: os três são síncronos (`requests`
        # com 30 s de timeout) e este é o caminho da ATENDENTE respondendo pelo
        # painel. Segurar o event loop aqui é segurar todos os outros
        # atendimentos enquanto uma pessoa manda um "bom dia".
        success = False
        if payload.message:
            success = await asyncio.to_thread(
                whatsapp_service.send_message, payload.phone, payload.message, integration)
        elif payload.image_url:
            success = await asyncio.to_thread(
                whatsapp_service.send_image, payload.phone, payload.image_url, "", integration)
        elif payload.audio_url:
            success = await asyncio.to_thread(
                whatsapp_service.send_audio, payload.phone, payload.audio_url, integration)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to send")

        return {"status": "sent", "phone": payload.phone}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ADMIN SEND] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch("/api/conversations/{conversation_id}/status")
async def update_conversation_status(
    conversation_id: str,
    payload: StatusUpdatePayload,
    _: bool = Depends(require_master_admin)
):
    """Update status - requires admin API key (called via Next.js proxy)"""
    try:
        update_data = {"status": payload.status}
        if payload.status == "open":
            update_data["human_handoff_reason"] = None
        elif payload.status == "HUMAN_REQUESTED":
            update_data["human_handoff_reason"] = "Admin Intervention"

        await asyncio.to_thread(
            lambda: supabase.client.table("conversations")
            .update(update_data)
            .eq("id", conversation_id)
            .execute()
        )
        logger.info(f"[ADMIN] Status updated for {conversation_id}")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"[ADMIN] Update status error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
