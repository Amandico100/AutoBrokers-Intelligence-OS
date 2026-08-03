"""
Webhook API - Recebe mensagens do WhatsApp via Z-API
Corrigido: Datas ISO e Sanitização de Logs
"""

import asyncio
import time as _tempo
import hmac
import logging
import os
from datetime import date, datetime, timezone  # Importado datetime e timezone
from typing import Optional
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
from app.services.message_buffer_service import get_message_buffer_service
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
        response = await asyncio.to_thread(lambda: query.limit(1).execute())

        # CORREÇÃO: Data em formato ISO UTC
        current_time_iso = datetime.now(timezone.utc).isoformat()

        if response.data and len(response.data) > 0:
            conv = response.data[0]
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
            "channel": channel,
            "agent_name": "AutoBrokers",
            "status": "open",
            "status_color": "green",
            "unread_count": 1,
            "last_message_preview": message_text[:100],
            "last_message_at": current_time_iso, # FIX: Data correta
        }

        insert_response = await asyncio.to_thread(
            lambda: supabase_client.table("conversations").insert(new_conv).execute()
        )

        if insert_response.data:
            return insert_response.data[0]["id"]

        raise Exception("Failed to create conversation")

    except Exception as e:
        logger.error(f"[CONVERSATION] Error in get_or_create: {str(e)}")
        raise


# ===== HELPER: PROCESS IMAGE (VISION) =====
async def process_image_for_vision(
    image_url: str, company_id: str, supabase_client
) -> Optional[str]:
    try:
        logger.debug(f"[VISION] Downloading image from: {image_url}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(image_url)
            response.raise_for_status()
            image_bytes = response.content

        if len(image_bytes) > 5 * 1024 * 1024:
            logger.warning(f"[VISION] Image too large: {len(image_bytes)} bytes")
            return None

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
        public_url = supabase_client.storage.from_("chat-media").get_public_url(file_path)
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

        public_url = supabase_client.storage.from_("voice-messages").get_public_url(file_path)
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
async def process_whatsapp_message_background(
    payload_dict: dict, combined_message: Optional[str] = None,
    buffered_messages: Optional[list] = None,
):
    """Processa mensagem WhatsApp em background (Evita bloqueio do Webhook)"""
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

            def _send_to_insurer(text_out: str) -> None:
                whatsapp_service.send_message(payload.phone, text_out, integration)

            def _send_to_client(client_phone: str, text_out: str) -> None:
                whatsapp_service.send_message(client_phone, text_out, integration)

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
            _dispatch_texts = [m for m in (buffered_messages or []) if str(m or "").strip()]
            if not _dispatch_texts and payload.text and payload.text.message:
                _dispatch_texts = [payload.text.message]
            handled = False
            for _msg in _dispatch_texts or [""]:
                handled = await try_route_insurer_inbound(
                    company_id=str(company_id),
                    from_phone=str(payload.phone or ""),
                    text=str(_msg or ""),
                    send_to_insurer=_send_to_insurer,
                    send_to_client=_send_to_client,
                    human_reply_provider=_human_reply_provider,
                    # SPEC-063 — o `interactive` precisa ATRAVESSAR.
                    #
                    # Só o texto chegava aqui, e o `flow_token` mora no
                    # `interactive` da mensagem. Sem ele o motor sabe montar a
                    # resposta do formulário nativo e não tem como endereçá-la.
                    # É a última ponte entre "o corredor sabe" e "o corredor faz"
                    # — e é uma linha.
                    interactive=(payload_dict or {}).get("interactive"),
                ) or handled
                if not handled:
                    break  # sem sessão ativa para este número — segue fluxo normal
            if handled:
                logger.info("[WEBHOOK] inbound routed to dispatch engine (insurer conversation)")
                return
        except Exception as e:  # noqa: BLE001 — roteador nunca derruba o fluxo normal
            logger.error(f"[WEBHOOK] dispatch router error: {type(e).__name__}")

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
        is_human_mode = False
        try:
            check_status = await asyncio.to_thread(
                lambda: supabase.client.table("conversations")
                .select("status")
                .eq("session_id", session_id)
                .limit(1)
                .execute()
            )
            if check_status.data and len(check_status.data) > 0:
                if check_status.data[0].get("status") == "HUMAN_REQUESTED":
                    is_human_mode = True
                    logger.info("[WEBHOOK] 👤 Modo Humano detectado. Pulando IA.")
        except Exception as e:
            logger.warning(f"[WEBHOOK] Failed to check status: {e}")

        # 3. Processar Conteúdo
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
                    whatsapp_service.send_message(payload.phone, "Erro ao processar áudio.", integration)
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
            await asyncio.to_thread(
                lambda: supabase.client.table("messages").insert(user_message_data).execute()
            )
            logger.info("[MESSAGES] User message saved.")
        except Exception as e:
            logger.error(f"[MESSAGES] Failed to save user msg: {e}")

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
            whatsapp_service.send_message(
                to_number=payload.phone,
                text="⚠️ Serviço temporariamente indisponível. Por favor, entre em contato com o suporte.",
                integration=integration
            )
            return

        logger.info(f"[WEBHOOK] Invoking AI Agent for company {company_id}...")
        langchain_service = LangChainService(settings.OPENAI_API_KEY, supabase)

        # SPEC-045 — NOTA DE CONTEXTO: se este cliente recebeu envio de
        # plataforma recente (cobrança/campanha), o atendente responde SABENDO
        # do que se trata. Só o texto enviado à IA — a mensagem salva (passo 5)
        # fica limpa. Sem envio recente = zero ruído.
        message_for_ai = message_text
        try:
            from app.services.platform_outbound import context_note_for

            _note = await context_note_for(company_id, payload.phone)
            if _note:
                message_for_ai = f"{message_text}\n\n{_note}"
        except Exception:  # noqa: BLE001
            pass

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

        # 8. Salvar Resposta IA
        try:
            await asyncio.to_thread(
                lambda: supabase.client.table("messages").insert({
                    "conversation_id": conversation_id,
                    "role": "assistant",
                    "content": ai_response,
                }).execute()
            )
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
        success = whatsapp_service.send_message(
            to_number=payload.phone, text=ai_response, integration=integration
        )

        if success:
            logger.info(f"[WEBHOOK BACKGROUND] ✅ Message sent to {safe_phone}")
        else:
            logger.error("[WEBHOOK BACKGROUND] Failed to send WhatsApp message")

    except Exception as e:
        logger.error(f"[WEBHOOK BACKGROUND] Critical Error: {str(e)}", exc_info=True)


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

        # Buffer Logic
        if payload.text and payload.text.message:
            phone = payload.phone
            buffer_service = await get_message_buffer_service()
            await buffer_service.add_message(
                phone=phone,
                message=payload.text.message,
                company_id="pending",
                user_id="pending",
                integration={},
                payload=payload_dict,
            )
            logger.info(f"[WEBHOOK] Text from {phone} buffered")
            return {"status": "buffered", "phone": phone}

        elif payload.audio or payload.image:
            logger.info("[WEBHOOK] Dispatching media to background...")
            background_tasks.add_task(process_whatsapp_message_background, payload_dict)
            return {"status": "received", "type": "media"}

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
        return supabase.client.storage.from_(bucket).get_public_url(file_path)
    except Exception as e:  # noqa: BLE001
        logger.error(f"[WEBHOOK EVOLUTION] media upload failed: {type(e).__name__}")
        return None


async def _buffer_or_dispatch_text(payload_dict: dict, phone: str) -> dict:
    """Humanização S17-9: texto entra no buffer com debounce (espera a rajada)."""
    buffer_service = await get_message_buffer_service()
    await buffer_service.add_message(
        phone=phone,
        message=((payload_dict.get("text") or {}).get("message") or ""),
        company_id="pending",
        user_id="pending",
        integration={},
        payload=payload_dict,
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
    if payload.text and payload.text.message:
        return await _buffer_or_dispatch_text(payload_dict, payload.phone)
    background_tasks.add_task(process_whatsapp_message_background, payload_dict)
    return {"status": "received", "type": "media"}


@router.post("/api/v1/webhook/evolution/{token}")
@limiter.limit("240/minute")
async def evolution_webhook_token(token: str, request: Request, background_tasks: BackgroundTasks):
    """Webhook Evolution API v2 com token por integração (SPEC-017)."""
    integration = await _resolve_webhook_integration("evolution", token)
    body = await request.json()
    return await _handle_evolution_like_inbound(integration, body, background_tasks, "evolution")


@router.post("/api/v1/webhook/evolution-go/{token}")
@limiter.limit("240/minute")
async def evolution_go_webhook_token(token: str, request: Request, background_tasks: BackgroundTasks):
    """Webhook Evolution GO (SPEC-034 — migração do canal p/ GO, founder 14/07).

    O GO entrega o evento whatsmeow; convertemos para o envelope v2 e reusamos
    TODO o pipeline (normalizador, formulário nativo, buffer, dispatch)."""
    integration = await _resolve_webhook_integration("evolution-go", token)
    body = await request.json()

    # ATLAS (SPEC-038 Bloco A): captura passiva ANTES do pipeline.
    # purpose='observer' consome (instância dedicada, muda por construção);
    # purpose='attendance' = TAP: grava o que for de seguradora e o fluxo
    # segue INTACTO. O tap jamais derruba o atendimento.
    try:
        from app.services.atlas.observer_intake import observer_tap

        _observed = await observer_tap(integration, body if isinstance(body, dict) else {})
        if _observed is not None:
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
        # Mensagem MANUAL da própria corretora (fromMe) numa conversa com
        # dispatch ATIVO: registra no espelho (humano copilotando a URA).
        if normalized.get("skip_reason") == "from_me" and normalized.get("text") and normalized.get("phone"):
            try:
                from app.services.dispatch_router import note_manual_outbound

                await note_manual_outbound(
                    str(integration.get("company_id") or ""), str(normalized["phone"]), str(normalized["text"])
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
        return {"status": "ignored", "reason": normalized["skip_reason"]}
    if await _is_duplicate_namespaced(provider_label, normalized["message_id"]):
        return {"status": "ignored", "reason": "duplicate"}

    # F1 — mídia do cliente (imagem/PDF/áudio): baixa via Evolution, sobe no
    # storage e entra no fluxo normal (visão p/ imagem; texto extraído p/ doc).
    media = normalized.get("media")
    text_message = normalized["text"]
    image_payload = None
    audio_payload = None
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
                base_txt = media.get("caption") or f"[Cliente enviou o documento: {fname}]"
                if doc_text:
                    text_message = f"{base_txt}\n\n[CONTEÚDO DO DOCUMENTO {fname}]\n{doc_text}\n[FIM DO DOCUMENTO]"
                else:
                    text_message = f"{base_txt}\n(não foi possível ler o conteúdo do documento — peça para reenviar ou colar o texto)"
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
        "messageId": normalized["message_id"],
        "senderName": normalized["sender_name"],
        "momment": normalized.get("timestamp"),
        "_integration_id": integration.get("id"),
    }
    if image_payload or audio_payload:
        background_tasks.add_task(process_whatsapp_message_background, payload_dict)
        return {"status": "received", "type": "media"}
    return await _buffer_or_dispatch_text(payload_dict, normalized["phone"])


@router.post("/api/webhook/send-message")
async def admin_send_message(
    payload: AdminSendMessagePayload,
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
        integration = integration_service.get_whatsapp_integration(company_id, agent_id)

        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")

        success = False
        if payload.message:
            success = whatsapp_service.send_message(payload.phone, payload.message, integration)
        elif payload.image_url:
            success = whatsapp_service.send_image(payload.phone, payload.image_url, "", integration)
        elif payload.audio_url:
            success = whatsapp_service.send_audio(payload.phone, payload.audio_url, integration)

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
