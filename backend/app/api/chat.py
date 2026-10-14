"""
Chat API Endpoint - Multi-Tenant Secure
SIMPLIFICADO: Usa apenas LangChainService
Otimizado: Query única e Correção de Datas
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import UUID4, BaseModel, Field, field_validator

from app.core import settings
from app.core.auth import _chaves_internas
from app.core.database import AsyncSupabaseClient, get_async_db, get_supabase_client
from app.core.rate_limit import limiter
from app.services import AudioService, LangChainService

# SPEC-096 B.1 — o vocabulário do turno. Módulo PURO: nada aqui puxa banco,
# rede ou modelo, e por isso ele pode ser lido e mutado sem subir o produto.
from app.api.chat_eventos import (
    MENSAGENS_HUMANAS,
    Sequenciador,
    erro_seguro,
    estagio_da_tool,
    href_da_peca,
    pecas_do_turno,
)

# P-PILOTO-18 — a ligação entre o turno e a invocação de ferramenta.
# ⛔ Este módulo NÃO é um segundo registro de tool call: quem grava continua
# sendo o `RegistroDeInvocacao` chamado pelo nó de tool. Daqui só vêm a marca do
# turno em voo e o FORMATO da chave — um formato, um lugar.
from app.services.skills.invocation_recorder import chave_de_rastro, marcar_turno

# SPEC-132-A B8 — as escolhas de esforço moram no Model Router (módulo PURO: só
# biblioteca padrão no topo), e não numa segunda lista aqui.
from app.factories.model_policy import ESCOLHAS_DE_ESFORCO

logger = logging.getLogger(__name__)

#: O teto de anexos por pedido (SPEC-132-A §5: "até 10 arquivos").
TETO_DE_ANEXOS = 10


def opcoes_validas(bruto: Any) -> Optional[Dict[str, Any]]:
    """`options` do pedido, só com o que o turno conhece. **PURA.** (SPEC-132-A)

    ⛔ Chave nova ou valor fora do conjunto é IGNORADO com log — nunca 422 (a tela
    pode ganhar uma opção antes do backend saber dela, e o turno não morre por isso).
    `web_search` só como booleano; `esforco` só em `ESCOLHAS_DE_ESFORCO`
    (rapido · equilibrado · maximo). ⛔ O VALOR ignorado não vai ao log (é do
    cliente); só a CHAVE, cortada.
    """
    if bruto is None:
        return None
    if not isinstance(bruto, dict):
        logger.warning("[STREAM] options ignorado: não é um objeto (%s)", type(bruto).__name__)
        return None
    limpas: Dict[str, Any] = {}
    for chave, valor in bruto.items():
        if chave == "web_search" and isinstance(valor, bool):
            limpas[chave] = valor
        elif (chave == "esforco" and isinstance(valor, str)
              and valor.strip().lower() in ESCOLHAS_DE_ESFORCO):
            limpas[chave] = valor.strip().lower()
        else:
            logger.warning("[STREAM] opção ignorada: %s", str(chave)[:30])
    return limpas

router = APIRouter()


# =============================================================================
# WIDGET SECURITY HELPERS
# =============================================================================

from app.api.middleware.widget_security import (
    check_widget_rate_limit,
    validate_widget_domain,
)

# Serviços (lazy loading)
_langchain_service = None
_audio_service = None

def get_langchain_service():
    global _langchain_service
    if _langchain_service is None:
        _langchain_service = LangChainService(
            openai_api_key=settings.OPENAI_API_KEY,
            supabase_client=get_supabase_client(),
        )
    return _langchain_service

def get_audio_service():
    global _audio_service
    if _audio_service is None:
        _audio_service = AudioService(openai_api_key=settings.OPENAI_API_KEY)
    return _audio_service


class ChatRequest(BaseModel):
    chatInput: Optional[str] = Field(None, description="Mensagem do usuário")
    audioData: Optional[str] = Field(None, description="Áudio em base64")
    imageUrl: Optional[str] = Field(None, description="URL pública da imagem enviada")
    fileUrl: Optional[str] = Field(None, description="URL pública de documento anexado (PDF/DOCX...)")
    fileName: Optional[str] = Field(None, description="Nome original do documento anexado")
    sessionId: UUID4 = Field(..., description="ID da sessão")
    companyId: UUID4 = Field(..., description="ID da empresa")
    userId: Optional[UUID4] = Field(None, description="ID do usuário")
    agentId: Optional[UUID4] = Field(None, description="ID do agente específico")
    assistantMessageId: Optional[UUID4] = Field(None, description="ID pré-gerado")
    channel: str = Field(default="web", description="Origin: web, whatsapp, widget")
    conversationHistory: Optional[List[Dict[str, Any]]] = None
    # 🔴 SPEC-132-A B8: `{web_search?: bool, esforco?: 'rapido'|'equilibrado'|'maximo'}`.
    # Validado por `opcoes_validas` — o que não se conhece some com log, sem 422.
    options: Optional[Dict[str, Any]] = Field(None)
    # 🔴 SPEC-132-A §5: `[{bucket, path, nome, mime, bytes}]` — o arquivo JÁ subido.
    # O backend lê os BYTES pelo service role (`chat_anexos.preparar`); o path tem
    # de estar no prefixo `<company_id>/` (o BFF recusa antes; aqui, de novo).
    attachments: Optional[List[Dict[str, Any]]] = Field(None, max_length=TETO_DE_ANEXOS)
    # SPEC-096 A.1/A.3 — o id que o PEDIDO carrega. É por ele que o índice único
    # parcial recusa a resposta duplicada e que a tela descarta o eco do
    # Realtime. Obrigatório no modo painel. ⚠️ Aceito nas duas grafias porque a
    # tela fala camelCase e o protocolo do turno fala snake_case.
    clientRequestId: Optional[str] = Field(None, alias="client_request_id")
    userMessageId: Optional[UUID4] = Field(None, alias="user_message_id")

    model_config = {"populate_by_name": True}

    @field_validator("options", mode="before")
    @classmethod
    def _so_as_opcoes_conhecidas(cls, valor):
        return opcoes_validas(valor)

class ChatResponse(BaseModel):
    output: str = Field(..., description="Resposta da IA")
    companyId: str
    sessionId: str


class DeleteSessionRequest(BaseModel):
    """Request to delete an expired session's memory."""
    sessionId: str = Field(..., description="Session ID to delete")
    companyId: str = Field(..., description="Company ID for thread_id composition")


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("100/minute")
async def chat_endpoint(
    request: Request,
    chat_request: ChatRequest,
    db: AsyncSupabaseClient = Depends(get_async_db),
) -> ChatResponse:
    try:
        if not chat_request.chatInput and not chat_request.audioData and not chat_request.imageUrl:
            raise HTTPException(status_code=400, detail="No content provided")

        # 🔴 A MESMA lei do /chat/stream: sem chave interna, quem manda no
        # `userId` e na corretora é o AGENTE, não o corpo (S.2/R1).
        modo = _modo_de_confianca(request)
        if modo == "widget":
            chat_request.userId = None
            dona = await _empresa_do_widget(db, agent_id=chat_request.agentId,
                                            company_do_corpo=chat_request.companyId)
            if not dona:
                # 📊 05/09 (juiz): sem agente resolvível, o `companyId` do corpo
                # sobrevivia até `pode_consumir` e `companies.select` — o par 200×404
                # da §1.1 continuava vivo para agentId inexistente. Widget sem agente
                # não tem corretora: 404 antes de tocar qualquer tabela da company.
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="agent not found")
            chat_request.companyId = uuid.UUID(str(dona))

        logger.info(f"[CHAT] Request: company={chat_request.companyId}, session={chat_request.sessionId}")

        # Transcrever áudio
        user_message = chat_request.chatInput
        if chat_request.audioData:
            try:
                user_message = await get_audio_service().transcribe_audio(
                    chat_request.audioData,
                    company_id=str(chat_request.companyId),
                    agent_id=str(chat_request.agentId) if chat_request.agentId else None
                )
                # LOG SANITIZADO
                logger.info(f"[AUDIO] Transcribed (len={len(user_message)})")
            except Exception as e:
                logger.error(f"[AUDIO] Transcription failed: {e}")
                raise HTTPException(status_code=400, detail="Audio transcription failed") from e

        # ==============================================================================
        # OTIMIZAÇÃO: Query Única para Status e Dados da Conversa
        # ==============================================================================
        conv_check = (
            await db.client.table("conversations")
            .select("id, status, unread_count, company_id, claimed_by, resolvido_em") # Pega tudo que precisa
            .eq("session_id", str(chat_request.sessionId))
            .limit(1)
            .execute()
        )

        conversation_id = None
        current_unread = 0
        existing_company_id = None
        conv_status = "open"
        linha_da_conversa: dict = {}

        if conv_check and conv_check.data and len(conv_check.data) > 0:
            data = conv_check.data[0]
            linha_da_conversa = data
            conversation_id = data.get("id")
            conv_status = data.get("status")
            current_unread = data.get("unread_count") or 0
            existing_company_id = data.get("company_id")

        # ==============================================================================
        # HUMAN HANDOFF CHECK
        # ==============================================================================
        # 🔴 SPEC-097 U2.3/E6 — pausa por STATUS **ou por DONO**: a conversa que
        # a atendente assumiu (`claimed_by`) segue `open`, e a IA respondia por
        # cima dela. `pausar_ia` é o helper único das duas razões.
        #
        # 🔴 E A JANELA ENTRA AQUI **SÓ NO WIDGET** (09/09/2026). Esta rota é
        # DUAS rotas: no `widget` quem digita é o SEGURADO (o mesmo atendimento
        # do WhatsApp, por outro canal — e a atendente responde a ele pelo
        # painel, com `payload.origem='dashboard'`); no `painel` quem digita é a
        # PRÓPRIA corretora, conversando com o agente dela. ⛔ Ligar a janela no
        # painel seria calar o agente para quem o está usando.
        from app.services.o_fim_do_atendimento import (
            HUMAN_REQUESTED, a_ia_deve_calar, anotar_silencio_no_feed, foi_a_janela,
            pausar_ia,
        )

        _calar = pausar_ia(linha_da_conversa)
        _motivo_do_silencio = ""
        if not _calar and modo == "widget" and conversation_id:
            _calar, _motivo_do_silencio = await a_ia_deve_calar(
                db, company_id=str(existing_company_id or chat_request.companyId),
                conversa=linha_da_conversa)

        if _calar:
            # ⚠️ A RAZÃO vai no log: "pausada" por pedido do segurado e
            # "pausada" porque alguém assumiu são operações diferentes, e sem a
            # razão escrita não dá para saber qual delas segurou a resposta.
            razao = (HUMAN_REQUESTED if str(conv_status or "").upper() == HUMAN_REQUESTED
                     else "claimed_by")
            if foi_a_janela(_motivo_do_silencio):
                razao = "janela"
                logger.info("[CHAT] 🚫 %s", _motivo_do_silencio)
                await anotar_silencio_no_feed(
                    company_id=str(existing_company_id or chat_request.companyId),
                    conversation_id=str(conversation_id or ""),
                    motivo=_motivo_do_silencio)
            logger.info("[CHAT] 🚫 Modo HUMANO (%s) - Agente pausado", razao)

            if user_message and conversation_id:
                # Salvar mensagem do usuário
                await db.client.table("messages").insert({
                    "conversation_id": conversation_id,
                    "role": "user",
                    "content": user_message,
                    "type": "text",
                }).execute()

                # Atualizar conversa
                await (
                    db.client.table("conversations")
                    .update({
                        "last_message_preview": (user_message or "")[:100],
                        "last_message_at": datetime.utcnow().isoformat() + "Z", # DATA CORRETA
                        "unread_count": current_unread + 1,
                    })
                    .eq("id", conversation_id)
                    .execute()
                )
            return ChatResponse(output="", companyId=str(chat_request.companyId), sessionId=str(chat_request.sessionId))

        # ==============================================================================
        # BALANCE CHECK (Paywall)
        # ==============================================================================
        from app.services.billing_service import get_billing_service
        billing_service = get_billing_service()

        # SPEC-062 §4, leis 2 e 4 — a PORTEIRA decide, nao o saldo direto.
        # Interruptor BILLING_ENFORCEMENT (padrao DESLIGADO); suspensao vale sempre.
        from app.services.billing_gate import pode_consumir

        _pode, _motivo = pode_consumir(str(chat_request.companyId))
        if not _pode:
            logger.info("[CHAT] barrado pela porteira: %s", _motivo)
            # Return empty response (not error) to avoid "connection error" in frontend
            return ChatResponse(output="", companyId=str(chat_request.companyId), sessionId=str(chat_request.sessionId))

        # ==============================================================================
        # PROCESSAMENTO LANGCHAIN
        # ==============================================================================
        try:
            response_text, metrics = await get_langchain_service().process_message(
                user_message=user_message or "",
                company_id=str(chat_request.companyId),
                user_id=str(chat_request.userId) if chat_request.userId else None,
                session_id=str(chat_request.sessionId),
                conversation_history=chat_request.conversationHistory,
                options=chat_request.options,
                image_url=chat_request.imageUrl,
                agent_id=str(chat_request.agentId) if chat_request.agentId else None,
                async_supabase_client=db.client,
            )
        except ValueError as e:
            # ✅ VALIDATION: Check if it's an agent configuration error
            error_msg = "%s" % e
            if "CONFIG_REQUIRED" in error_msg or "No active agents" in error_msg or "Agente de IA" in error_msg:
                logger.warning(f"[CHAT] Agent validation failed: {error_msg}")
                return ChatResponse(
                    output="⚠️ Nenhum agente configurado. Configure um agente em Configurações.",
                    companyId=str(chat_request.companyId),
                    sessionId=str(chat_request.sessionId)
                )
            # Re-raise if it's a different ValueError
            raise

        # ==============================================================================
        # PERSISTÊNCIA E ATUALIZAÇÃO (Usando dados já carregados)
        # ==============================================================================
        try:
            needs_company_update = False

            # Se conversa existe (carregada lá em cima)
            if conversation_id:
                if existing_company_id is None:
                    needs_company_update = True
                    logger.info(f"[CHAT] Updating null company_id for {conversation_id}")
            else:
                # CRIAR NOVA CONVERSA
                logger.info(f"[CHAT] Creating new conversation for session {chat_request.sessionId}")
                try:
                    new_conv = {
                        "company_id": str(chat_request.companyId),
                        "user_id": str(chat_request.userId) if chat_request.userId else None,
                        "session_id": str(chat_request.sessionId),
                        "agent_id": str(chat_request.agentId) if chat_request.agentId else None,
                        "channel": chat_request.channel or "web",
                        "status": "open",
                        "unread_count": 1,
                        "last_message_preview": (response_text[:100] if response_text else "Nova conversa"),
                        "last_message_at": datetime.utcnow().isoformat() + "Z", # DATA CORRETA
                    }
                    insert_res = await db.client.table("conversations").insert(new_conv).execute()

                    if insert_res.data:
                        conversation_id = insert_res.data[0]["id"]

                except Exception as insert_error:
                    # Retry para race condition
                    if "23505" in str(insert_error) or "duplicate key" in str(insert_error):
                        retry = await db.client.table("conversations").select("id, unread_count").eq("session_id", str(chat_request.sessionId)).single().execute()
                        if retry.data:
                            conversation_id = retry.data["id"]
                            current_unread = retry.data.get("unread_count") or 0

            # UPDATE FINAL
            if conversation_id:
                preview = response_text[:100] if response_text else "Nova mensagem"
                update_data = {
                    "last_message_preview": preview,
                    "last_message_at": datetime.utcnow().isoformat() + "Z", # DATA CORRETA
                    "unread_count": current_unread + 1,
                }
                if needs_company_update:
                    update_data["company_id"] = str(chat_request.companyId)

                await db.client.table("conversations").update(update_data).eq("id", conversation_id).execute()

                # SALVAR MENSAGENS
                if user_message:
                    await db.client.table("messages").insert({
                        "conversation_id": conversation_id,
                        "role": "user",
                        "content": user_message,
                        "type": "text",
                    }).execute()

                if response_text:
                    await db.client.table("messages").insert({
                        "conversation_id": conversation_id,
                        "role": "assistant",
                        "content": response_text,
                        "type": "text",
                    }).execute()

        except Exception as e:
            logger.error(f"[CHAT] Database update failed: {e}", exc_info=True)

        return ChatResponse(
            output=response_text,
            companyId=str(chat_request.companyId),
            sessionId=str(chat_request.sessionId),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from e

# =============================================================================
# O TURNO — SPEC-096 · S.2 (modo de confiança) · A.3/A.4 (a task) · B.3/B.4
#
# 🔴 Três coisas mudaram aqui, e cada uma fecha um defeito medido:
#
#  (iii) **quem manda um `userId` no corpo não é mais quem ele diz que é.**
#        📊 O `if agent_data and not chat_request.userId` de antes fazia as
#        checagens de widget (domínio, rate limit) dependerem de um campo que o
#        próprio cliente escolhe: bastava mandar um uuid qualquer para pulá-las.
#        Agora a identidade só é honrada com a chave interna do BFF.
#
#   (iv) **aviso não é resposta.** Porteira, agente ausente e guardrail viravam
#        `{"token": "..."}` — e o token virava `messages.content` e memória do
#        agente. No painel eles saem como evento de POLÍTICA (bloqueio ou
#        aviso), e NADA é gravado (R5). Para o widget, a forma legada segue
#        idêntica.
#
#    (x) **a resposta não morre com a conexão.** A geração roda numa task
#        própria; o gerador de SSE só LÊ de uma fila. Se o browser fecha, a task
#        continua, termina e grava — inclusive o parcial (A.4).
# =============================================================================

#: 🔴 O cabeçalho que separa o PAINEL do WIDGET. Só o BFF o conhece (é ele quem
#: tem a sessão do corretor); um browser nunca o tem.
CABECALHO_INTERNO = "X-Internal-Key"

#: ⚠️ Este literal aparece UMA vez no arquivo de propósito: é o tipo do evento
#: de porteira, e quem o renomear renomeia num lugar só.
TIPO_POLICY_BLOCKED = "policy.blocked"
#: ⚠️ `notice` SEM ponto — e o nome do contrato R4 da SPEC, e e por ele
#: que a tela decide entre "nao deu para responder" e "alguem assumiu daqui".
TIPO_POLICY_NOTICE = "notice"

#: Sem evento nenhum, a conexão precisa dar sinal de vida antes de qualquer
#: proxy desistir dela. 15 s é metade do timeout mais curto que já vimos.
SEGUNDOS_DE_BATIMENTO = 15

#: Tetos do BLOCO A.4 — memoria por turno, e turnos por processo.
TETO_DE_EVENTOS_NA_FILA = 5000
TETO_DE_TURNOS_ATIVOS = 200

#: Os turnos em voo, por `company_id:client_request_id`. 🔴 A chave leva o
#: tenant: um `client_request_id` de outra corretora não para o turno desta.
TURNOS_ATIVOS: Dict[str, Any] = {}

#: Quem pediu o Stop (E11) — lido pela task ao gravar o parcial.
PARADAS: Dict[str, str] = {}

#: 💭 O nome que o corretor lê no lugar do `kind` técnico da peça.
KINDS_HUMANOS = {
    "report": "Relatório",
    "briefing": "Briefing",
    "dashboard": "Painel",
    "proposal": "Proposta",
    "letter": "Carta",
    "spreadsheet": "Planilha",
}

TEXTO_SEM_CREDITO = "Creditos insuficientes para responder. Configure plano/creditos da empresa no Admin."
TEXTO_SEM_AGENTE = "⚠️ Nenhum agente configurado. Configure um agente em Configurações."
TEXTO_AGENTE_NAO_ENCONTRADO = "⚠️ Agente não encontrado. Verifique a configuração."
TEXTO_ERRO_DE_SEGURANCA = "Erro temporário de segurança. Por favor, tente novamente."

CABECALHOS_SSE = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


#: 🔴 SPEC-098 R7 — a definição MUDOU DE CASA, não foi copiada. Ela agora mora
#: em `app/core/auth.py`, ao lado do `require_internal_key` que os outros
#: routers usam, e este arquivo a IMPORTA. Duas cópias da lista de chaves
#: válidas seriam duas respostas para "quem é o BFF" (CLAUDE.md §5), e a
#: divergência apareceria como uma rota autenticando e a vizinha não.
#: ⚠️ O nome local fica: `_modo_de_confianca` e os testes já o chamam assim.


def _modo_de_confianca(request: Request) -> str:
    """`painel` (chave interna válida) ou `widget`.

    🔴 Chave errada vale como chave nenhuma: cai em `widget`, onde o `userId`
    do corpo é descartado e as checagens de widget rodam. Não existe estado
    intermediário — é isso que impede o corpo de escolher a identidade.
    """
    chave = (request.headers.get(CABECALHO_INTERNO) or "").strip()
    if chave and chave in _chaves_internas():
        return "painel"
    return "widget"


async def _empresa_do_widget(db, *, agent_id, company_do_corpo):
    """No widget, a CREDENCIAL é o AGENTE — e o corpo não escolhe a corretora.

    🔴 O defeito que isto fecha. Sem chave interna, o `companyId` chegava do
    corpo e era usado para carregar a corretora e para GASTAR O CRÉDITO dela.
    A única barreira era o domínio do widget — e 📊 `widget_security.py:18-19`
    devolve `True` quando não há `allowedDomains`, que é o caso de 0 de 8
    agentes hoje. Ou seja: qualquer um que soubesse um `companyId` consumia a
    conta de outra corretora.

    A partir daqui o `agentId` é a credencial: a corretora é a DONA do agente.
    Um `agentId` da corretora A só serve à corretora A, mande o corpo o que
    mandar. Divergência não é erro (o widget antigo continua funcionando) — é
    log, e o valor do corpo é ignorado.
    """
    if not agent_id:
        logger.warning("[WIDGET SECURITY] trust=widget_sem_agente — sem agentId não há credencial")
        return None
    try:
        achado = (
            await db.client.table("agents")
            .select("id, company_id, widget_config")
            .eq("id", str(agent_id))
            .limit(1)
            .execute()
        ).data
    except Exception as erro_de_leitura:  # noqa: BLE001
        logger.warning("[WIDGET SECURITY] agente ilegivel: %s", type(erro_de_leitura).__name__)
        return None
    if not achado:
        return None

    dona = achado[0].get("company_id")
    if dona and company_do_corpo and str(dona) != str(company_do_corpo):
        logger.warning(
            "[WIDGET SECURITY] trust=widget_company_ignored agente=%s corpo=%s dona=%s",
            str(agent_id)[:8], str(company_do_corpo)[:8], str(dona)[:8],
        )

    configuracao = achado[0].get("widget_config") or {}
    if not (configuracao.get("allowedDomains") or []):
        # ⚠️ Permite (não quebra widget instalado), mas fica registrado: sem
        # domínio, a porta de entrada do agente é pública.
        logger.warning("[WIDGET SECURITY] widget_sem_dominio agente=%s — "
                       "qualquer origem passa; configure allowedDomains", str(agent_id)[:8])
    return dona


def _e_conflito_de_chave(erro: BaseException) -> bool:
    """O banco recusou por chave repetida?

    🔴 O `messages_turno_sem_duplicata_uidx` recusa uma SEGUNDA resposta
    para o mesmo (conversa, papel, client_request_id) — e e para recusar
    mesmo. O que ele nao pode e virar `persisted: false`: a tentativa nova tem
    de ACHAR a linha do turno e escrever nela.
    """
    texto = ("%s %s" % (type(erro).__name__, erro)).lower()
    return ("23505" in texto or "409" in texto or "duplicate key" in texto
            or "conflict" in texto)


async def anexar_documento_do_corretor(mensagem: str, file_url: str, file_name: str = "", *,
                                       company_id: str) -> str:
    """O anexo do CORRETOR no chat principal entra no turno — SPEC-130-B F3 (D-130B-05).

    Os bytes passam pelo LEITOR do produto (`conteudo_do_anexo`, o mesmo do WhatsApp): documento de seguro →
    a ficha MASCARADA + o texto mascarado (o corretor pergunta de cláusula); outro → o texto MASCARADO.
    📊 Antes: o texto cru do PDF, até 20.000 caracteres, CPF incluso. Falhou → o AVISO INTERNO de sempre.
    ⛔ Nunca a URL, o nome do arquivo nem o conteúdo no log.
    """
    company_id = str(company_id or "").strip()
    if company_id.lower() == "none":
        company_id = ""
    corpo = None
    # 🔴 SPEC-130-B F5 (C4): o NOME vai ao modelo MASCARADO (o arquivo pode se chamar pelo CPF).
    try:
        from app.services.vision_service import nome_do_anexo_para_o_modelo

        nome = nome_do_anexo_para_o_modelo(file_name, padrao="arquivo")
    except Exception:  # noqa: BLE001 — sem a máscara, nunca o nome cru
        nome = "arquivo"
    try:
        from app.services.vision_service import baixar_documento, conteudo_do_anexo

        dados = await baixar_documento(file_url)
        if dados:
            corpo = await conteudo_do_anexo(dados, file_name or file_url, company_id=company_id,
                                            audiencia="corretor")
    except Exception as e:  # noqa: BLE001
        logger.error("[STREAM DOC] leitura do anexo falhou (%s)", type(e).__name__)
        corpo = None
    if corpo:
        logger.info("[STREAM DOC] ✅ Documento anexado lido pelo leitor do produto (SPEC-130-B)")
        return f"{mensagem}\n\n[DOCUMENTO ANEXADO: {nome}]\n{corpo}\n[FIM DO DOCUMENTO]"
    return (
        f"{mensagem}\n\n[AVISO INTERNO: o usuário anexou o documento "
        f"'{nome}' mas a extração falhou — diga isso com naturalidade e peça para reenviar ou colar o trecho.]"
    )


# =============================================================================
# 🔴 SPEC-132-A — O ANEXO DO CHAT NOVO E A LINHA DE ATIVIDADE (módulo, PURO)
# =============================================================================

#: A linha de atividade usa o `stage.started` que a tela JÁ lê (`{key, label}`,
#: `lib/chat/protocolo.ts`) — nenhum evento novo. O 1º delta a apaga.
ESTAGIO_PENSANDO = {"key": "thinking", "label": "Pensando…"}
CHAVE_DOS_ANEXOS = "attachments.reading"

#: O nome do arquivo na linha de atividade não cresce sem fim (a linha é uma só).
TETO_DO_NOME_NA_TELA = 48

AVISO_SEM_LEITURA = "não consegui ler os arquivos anexados agora"


def _e_foto(anexo: Dict[str, Any]) -> bool:
    return str((anexo or {}).get("mime") or "").lower().startswith("image/")


def _e_audio(anexo: Dict[str, Any]) -> bool:
    return str((anexo or {}).get("mime") or "").lower().startswith("audio/")


def _nome_para_a_tela(nome: Any) -> str:
    """O nome do arquivo MASCARADO (o arquivo pode se chamar pelo CPF — 130-B F5).

    ⛔ Sem a máscara, nunca o nome cru: vira "o arquivo".
    """
    try:
        from app.services.vision_service import nome_do_anexo_para_o_modelo

        limpo = nome_do_anexo_para_o_modelo(nome, padrao="o arquivo")
    except Exception:  # noqa: BLE001 — sem a máscara, nunca o nome cru
        limpo = "o arquivo"
    limpo = str(limpo or "o arquivo")
    if len(limpo) > TETO_DO_NOME_NA_TELA:
        limpo = limpo[:TETO_DO_NOME_NA_TELA - 1] + "…"
    return limpo


def rotulo_dos_anexos(anexos: List[Dict[str, Any]], *, imagem_antiga: bool = False,
                      documento_antigo: Optional[str] = None) -> str:
    """A frase que o corretor lê enquanto o AutoBrokers lê o que ele mandou. **PURA.**

    "Lendo apolice.pdf…" · "Ouvindo o áudio…" · "Olhando a foto…" · "Lendo 3 arquivos…".
    """
    itens = [a for a in (anexos or []) if isinstance(a, dict)]
    if imagem_antiga:
        itens.append({"mime": "image/*"})
    if documento_antigo is not None:
        itens.append({"mime": "application/octet-stream", "nome": documento_antigo})
    if not itens:
        return ESTAGIO_PENSANDO["label"]
    fotos = [a for a in itens if _e_foto(a)]
    audios = [a for a in itens if _e_audio(a)]
    if len(itens) == 1:
        if fotos:
            return "Olhando a foto…"
        if audios:
            return "Ouvindo o áudio…"
        return "Lendo %s…" % _nome_para_a_tela(itens[0].get("nome"))
    if len(fotos) == len(itens):
        return "Olhando as %d fotos…" % len(itens)
    if len(audios) == len(itens):
        return "Ouvindo os %d áudios…" % len(itens)
    return "Lendo %d arquivos…" % len(itens)


def _como_lista(valor: Any) -> List[str]:
    if valor is None:
        return []
    if isinstance(valor, str):
        return [valor] if valor.strip() else []
    if isinstance(valor, (list, tuple)):
        return [str(x) for x in valor if x is not None and str(x).strip()]
    texto = str(valor)
    return [texto] if texto.strip() else []


def incorporar_os_anexos(mensagem: Optional[str], resultado: Any) -> Tuple[str, Optional[str]]:
    """O que `chat_anexos.preparar` leu entra no turno — no MESMO formato dos campos antigos.

    Devolve `(mensagem_do_turno, transcricao)`. **PURA.**
      · `.descricoes` → `[CONTEXTO VISUAL — imagem enviada pelo usuário]` (o bloco da visão de antes)
      · `.texto`      → os blocos `[DOCUMENTO ANEXADO …]` JÁ MASCARADOS, como vieram
      · `.transcricoes` → sem texto do corretor, a transcrição É a mensagem; com texto, um bloco
      · `.avisos`     → `[AVISO INTERNO: …]`, a mesma frase que o documento ilegível já usa
    ⛔ `resultado is None` (o leitor não existe ou caiu) vira AVISO — o turno nunca morre por anexo.
    """
    base = mensagem or ""
    if resultado is None:
        return (base + "\n\n[AVISO INTERNO: %s — diga isso com naturalidade e peça para "
                "reenviar ou colar o trecho.]" % AVISO_SEM_LEITURA), None
    blocos = _como_lista(getattr(resultado, "texto", None))
    descricoes = _como_lista(getattr(resultado, "descricoes", None))
    transcricoes = _como_lista(getattr(resultado, "transcricoes", None))
    avisos = _como_lista(getattr(resultado, "avisos", None))
    transcricao = "\n\n".join(transcricoes) if transcricoes else None
    partes = []
    if not base.strip() and transcricao:
        partes.append(transcricao)          # só áudio: a transcrição é a pergunta
        transcricoes = []
    else:
        partes.append(base)
    for descricao in descricoes:
        partes.append("[CONTEXTO VISUAL — imagem enviada pelo usuário]:\n%s" % descricao)
    partes.extend(blocos)
    for trecho in transcricoes:
        partes.append("[ÁUDIO ENVIADO PELO CORRETOR — transcrição]:\n%s" % trecho)
    for aviso in avisos:
        partes.append("[AVISO INTERNO: %s — diga isso com naturalidade e peça para reenviar "
                      "ou colar o trecho.]" % aviso)
    return "\n\n".join(p for p in partes if p), transcricao


def anexos_fora_da_corretora(company_id: Any, anexos: Optional[List[Dict[str, Any]]]) -> int:
    """Quantos anexos NÃO estão no prefixo `<company_id>/`. **PURA.** (CLAUDE.md §7)

    🔴 O BFF já recusa (403); aqui é o cinto: o backend lê pelo SERVICE ROLE, e um
    path de outra corretora seria um arquivo alheio lido em nome desta.
    """
    prefixo = "%s/" % str(company_id or "").strip()
    fora = 0
    for anexo in anexos or []:
        caminho = str((anexo or {}).get("path") or "") if isinstance(anexo, dict) else ""
        if (prefixo == "/" or not caminho.startswith(prefixo) or ".." in caminho
                or "\\" in caminho):
            fora += 1
    return fora


def _nivel_efetivo(agent_data: Optional[Dict[str, Any]], nivel: Optional[str]) -> Optional[str]:
    """O esforço que o modelo do turno vai de fato usar (para o `payload.turn`).

    ⚠️ Só com o cache do Model Router QUENTE (o grafo acabou de resolver a rota):
    descrever o turno nunca abre uma ida ao banco. Frio → o nível PEDIDO.
    """
    try:
        from app.factories import model_policy as _MP

        if not _MP.cache_quente():
            return nivel
        from app.factories.llm_factory import LLMFactory

        with _MP.esforco_do_pedido(nivel):
            return LLMFactory.resolver_para(agent_data or {}, agent_data or {}).effort
    except Exception:  # noqa: BLE001 — diagnóstico, nunca derruba o turno
        return None


async def _nenhum_evento():
    """O turno barrado pelo guardrail não chama o modelo: nenhum evento do motor."""
    return
    yield  # noqa: B901 — faz desta função um gerador assíncrono vazio


def _sse_legado(payload: Dict[str, Any]) -> str:
    return "data: %s\n\n" % json.dumps(payload)


def _resposta_de_politica(*, modo: str, turno: Dict[str, Any], tipo: str, code: str,
                          texto: str, legado: Dict[str, Any]) -> StreamingResponse:
    """O turno que termina antes de começar — e NÃO grava nada (R5).

    ⛔ Nem `messages`, nem memória, nem preview da conversa: um aviso do sistema
    não é uma resposta do agente, e o que ele não gravar hoje não volta amanhã
    como se o agente tivesse dito.
    """

    async def gerar():
        if modo == "painel":
            seq = Sequenciador(turno)
            yield seq.sse("turn.accepted", dict(turno))
            yield seq.sse(tipo, {"code": code, "message_human": texto})
            # 🔴 `failed`, nao `blocked`: o vocabulario de `status` tem tres
            # palavras — complete · interrupted · failed (A.3). O motivo mora
            # em `error_code`, que e onde a tela ja olha.
            yield seq.sse("turn.completed", {"status": "failed", "error_code": code,
                                             "persisted": False})
        else:
            yield _sse_legado(legado)
        yield "data: [DONE]\n\n"

    return StreamingResponse(gerar(), media_type="text/event-stream", headers=dict(CABECALHOS_SSE))


class _ReservaDoTurno:
    """O lugar do turno em `TURNOS_ATIVOS` entre a conferência do "já em andamento" e o `create_task`.

    🔴 Conserto da SPEC-132-A (juiz P1, medido): a conferência e o registro da task tinham `await`s no meio (a
    porteira e o agente foram para `asyncio.to_thread`) — dois POSTs com o MESMO `client_request_id` passavam os dois
    pela conferência, e o modelo era chamado 2× (📊 6/6 rodadas). A chave agora é RESERVADA logo depois da
    conferência, sem `await` no meio, e solta em todo caminho que não chega ao `create_task` (`chat_stream`).
    `done()` = falso: para quem confere, o turno já está em voo. `cancel()` (o Stop chegou antes da task) fica anotado
    e a task nasce cancelada.
    """

    __slots__ = ("parado",)

    def __init__(self):
        self.parado = False

    def done(self) -> bool:
        return False

    def cancel(self) -> bool:
        self.parado = True
        return True


@router.post("/chat/stream")
@limiter.limit("100/minute")
async def chat_stream(
    request: Request,
    chat_request: ChatRequest,
    db: AsyncSupabaseClient = Depends(get_async_db),
):
    """Streaming chat endpoint (SSE) — ver `_chat_stream_do_pedido`.

    Aqui só mora a ÚLTIMA palavra sobre a reserva do turno: o caminho que não chegou ao `create_task` (recusa de
    política, porteira, agente, 4xx, exceção) solta a chave — e só a SUA reserva, nunca a task de outro pedido.
    """
    reservas: list = []
    try:
        return await _chat_stream_do_pedido(request, chat_request, db, reservas)
    finally:
        for chave, reserva in reservas:
            if TURNOS_ATIVOS.get(chave) is reserva:
                TURNOS_ATIVOS.pop(chave, None)


async def _chat_stream_do_pedido(
    request: Request,
    chat_request: ChatRequest,
    db: AsyncSupabaseClient,
    reservas: list,
):
    """Streaming chat endpoint (SSE).

    Duas línguas, uma rota: o **widget** continua recebendo `{"token": "..."}`
    exatamente como antes; o **painel** recebe o protocolo tipado da SPEC-096.

    🔴 SPEC-132-A B6 — no PAINEL o `StreamingResponse` sai assim que as checagens
    BARATAS e de SEGURANÇA passam (a conversa é desta corretora, a porteira, o
    agente). O caro — anexos, visão, guardrail, grafo frio, o estado do turno —
    roda DENTRO de `_gerar`, com linhas de atividade. O widget segue igual.
    """
    # 🔴 SPEC-132-A: o relógio do turno começa no RECEBIMENTO (`ttft_ms`).
    recebido_em = time.monotonic()
    modo = _modo_de_confianca(request)
    if modo == "widget" and chat_request.attachments:
        # ⛔ Sem o BFF ninguém conferiu a sessão nem o prefixo do arquivo: o widget
        # não lê anexo por lista (ele tem `imageUrl`/`fileUrl`, como sempre).
        logger.warning("[STREAM] widget com attachments — ignorados")
        chat_request.attachments = None

    # Validation
    # SPEC-132-A: no painel, um áudio sozinho É a pergunta (sem `chatInput`).
    if not chat_request.chatInput and not chat_request.attachments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="chatInput is required for streaming",
        )

    if modo == "widget":
        # 🔴 O corpo não escolhe a identidade. Sem a chave do BFF, o `userId`
        # some — e com ele somem os privilégios que ele carregava.
        chat_request.userId = None
        # ...nem a CORRETORA: ela é derivada do agente, antes da porteira gastar
        # crédito e antes de carregar a `companies` (ver `_empresa_do_widget`).
        dona = await _empresa_do_widget(db, agent_id=chat_request.agentId,
                                        company_do_corpo=chat_request.companyId)
        if not dona:
            # 📊 05/09 (juiz): mesma regra do /chat — sem agente resolvível não há
            # corretora; o corpo não pode sobreviver até a porteira.
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="agent not found")
        chat_request.companyId = uuid.UUID(str(dona))

    client_request_id = (chat_request.clientRequestId or "").strip()
    if modo == "painel" and not client_request_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="client_request_id é obrigatório no modo painel",
        )

    assistant_message_id = (
        str(chat_request.assistantMessageId) if chat_request.assistantMessageId else str(uuid.uuid4())
    )
    turno = {
        "client_request_id": client_request_id or None,
        "session_id": str(chat_request.sessionId),
        "user_message_id": str(chat_request.userMessageId) if chat_request.userMessageId else None,
        "assistant_message_id": assistant_message_id,
    }
    chave_do_turno = "%s:%s" % (chat_request.companyId, client_request_id)

    # 🔴 SPEC-132-A · CLAUDE.md §7 — o anexo é DESTA corretora, ou o turno não começa.
    # Checagem de SEGURANÇA e barata: fica ANTES do stream, e nada é gravado (R5).
    if chat_request.attachments and anexos_fora_da_corretora(chat_request.companyId,
                                                             chat_request.attachments):
        logger.warning("[STREAM] trust=anexo_fora_da_corretora company=%s",
                       str(chat_request.companyId)[:8])
        return _resposta_de_politica(
            modo=modo, turno=turno, tipo=TIPO_POLICY_BLOCKED, code="policy",
            texto=MENSAGENS_HUMANAS["policy"],
            legado={"token": MENSAGENS_HUMANAS["policy"], "blocked": True},
        )

    logger.info(
        "[STREAM] modo=%s company=%s session=%s turno=%s",
        modo, str(chat_request.companyId)[:8], str(chat_request.sessionId)[:8],
        (client_request_id or "-")[:8],
    )

    # 📊 05/09 (juiz fresco, resíduo): dois POSTs do MESMO turno em voo (segunda aba,
    # retentativa do proxy, Enter que escapou da trava da tela) viravam DUAS tasks,
    # duas chamadas ao modelo e dois créditos — e o handle da primeira se perdia
    # (o Stop só alcançava a segunda). Um turno em andamento não ganha segunda
    # geração: é aviso tipado, sem gravar nada (R5). A retentativa legítima é a
    # do turno que JÁ TERMINOU (falhou/parou) — essa continua entrando.
    reserva: Optional[_ReservaDoTurno] = None
    if modo == "painel" and client_request_id:
        em_voo = TURNOS_ATIVOS.get(chave_do_turno)
        if em_voo is not None and not em_voo.done():
            logger.info("[STREAM] turno %s ja em andamento — sem 2a geracao",
                        client_request_id[:8])
            return _resposta_de_politica(
                modo=modo, turno=turno, tipo=TIPO_POLICY_NOTICE, code="turn_in_progress",
                texto=MENSAGENS_HUMANAS["turn_in_progress"],
                legado={"token": MENSAGENS_HUMANAS["turn_in_progress"]},
            )
        # 🔴 SEM `await` entre a conferência acima e esta linha: é isso que faz a 2ª chamada ver o turno em voo.
        reserva = _ReservaDoTurno()
        TURNOS_ATIVOS[chave_do_turno] = reserva
        reservas.append((chave_do_turno, reserva))

    # Check HUMAN_REQUESTED status
    # 🔴 A conversa e lida pela SESSAO, mas ela TEM DONO. Sem esta
    # conferencia, um `sessionId` de outra corretora era lido, respondido e
    # gravado aqui — a leitura nao filtrava empresa nenhuma (R1). Um
    # `company_id` nulo e legado (o `/chat` ainda o preenche depois) e continua
    # valendo.
    conv_check = (
        await db.client.table("conversations")
        .select("id, status, unread_count, company_id, claimed_by, resolvido_em")
        .eq("session_id", str(chat_request.sessionId))
        .limit(1)
        .execute()
    )

    conversation_id = None
    current_unread = 0

    if conv_check and conv_check.data and len(conv_check.data) > 0:
        dona_da_conversa = conv_check.data[0].get("company_id")
        if dona_da_conversa and str(dona_da_conversa) != str(chat_request.companyId):
            logger.warning(
                "[STREAM] trust=conversa_de_outra_corretora sessao=%s dona=%s pedida=%s",
                str(chat_request.sessionId)[:8], str(dona_da_conversa)[:8],
                str(chat_request.companyId)[:8],
            )
            return _resposta_de_politica(
                modo=modo, turno=turno, tipo=TIPO_POLICY_BLOCKED, code="policy",
                texto=MENSAGENS_HUMANAS["policy"],
                legado={"token": MENSAGENS_HUMANAS["policy"], "blocked": True},
            )
        conv_status = conv_check.data[0].get("status")
        conversation_id = conv_check.data[0].get("id")
        current_unread = conv_check.data[0].get("unread_count") or 0

        # 🔴 SPEC-097 U2.3/E6 — o mesmo portão do `/chat`: status OU dono.
        # ⚠️ E a JANELA só no `widget`, pela mesma razão do `/chat`: no `painel`
        #    quem digita é a corretora, e calar o agente para ela seria calar o
        #    agente para quem o está usando.
        from app.services.o_fim_do_atendimento import (
            HUMAN_REQUESTED, a_ia_deve_calar, anotar_silencio_no_feed, foi_a_janela,
            pausar_ia,
        )

        _calar = pausar_ia(conv_check.data[0])
        _motivo_do_silencio = ""
        if not _calar and modo == "widget" and conversation_id:
            _calar, _motivo_do_silencio = await a_ia_deve_calar(
                db, company_id=str(chat_request.companyId),
                conversa=conv_check.data[0])

        if _calar:
            razao = (HUMAN_REQUESTED if str(conv_status or "").upper() == HUMAN_REQUESTED
                     else "claimed_by")
            if foi_a_janela(_motivo_do_silencio):
                razao = "janela"
                logger.info("[STREAM] 🚫 %s", _motivo_do_silencio)
                await anotar_silencio_no_feed(
                    company_id=str(chat_request.companyId),
                    conversation_id=str(conversation_id or ""),
                    motivo=_motivo_do_silencio)
            logger.info("[STREAM] 🚫 Conversa em modo HUMANO (%s) - não streamar", razao)

            async def human_mode_response():
                yield "data: [HUMAN_MODE]\n\n"
                yield "data: [DONE]\n\n"

            if modo == "widget":
                return StreamingResponse(human_mode_response(), media_type="text/event-stream",
                                         headers=dict(CABECALHOS_SSE))
            return _resposta_de_politica(
                modo=modo, turno=turno, tipo=TIPO_POLICY_NOTICE, code="human_mode",
                texto=MENSAGENS_HUMANAS["human_mode"],
                legado={"token": ""},
            )

    # ===========================================================================
    # BALANCE CHECK (Paywall)
    # ===========================================================================
    # SPEC-062 §4, leis 2 e 4 — a PORTEIRA decide, nao o saldo direto.
    from app.services.billing_gate import pode_consumir

    # SPEC-132-A: síncrona e vai ao banco — fora do event loop (o resultado é o mesmo).
    _pode, _motivo = await asyncio.to_thread(pode_consumir, str(chat_request.companyId))
    if not _pode:
        logger.info("[STREAM] barrado pela porteira: %s", _motivo)
        return _resposta_de_politica(
            modo=modo, turno=turno, tipo=TIPO_POLICY_BLOCKED, code="billing",
            texto=TEXTO_SEM_CREDITO, legado={"token": TEXTO_SEM_CREDITO},
        )

    # Get company config and prepare graph
    from app.agents.graph import stream_agent, stream_agent_eventos
    from app.services.agent_service import AgentService

    sync_db = get_supabase_client()

    # Get company config
    company_response = (
        await db.client.table("companies")
        .select("*")
        .eq("id", str(chat_request.companyId))
        .limit(1)
        .execute()
    )

    if not company_response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    company_config = company_response.data[0]

    # Get agent if specified
    agent_data = None
    api_key = settings.OPENAI_API_KEY

    # ✅ VALIDATION: Agent ID is mandatory
    if not chat_request.agentId:
        logger.warning(f"[STREAM] No agentId provided for company {chat_request.companyId}")
        return _resposta_de_politica(
            modo=modo, turno=turno, tipo=TIPO_POLICY_NOTICE, code="no_agent",
            texto=TEXTO_SEM_AGENTE, legado={"token": TEXTO_SEM_AGENTE},
        )

    # Try to load agent
    try:
        agent_service = AgentService()
        # SPEC-132-A: cache de 60 s; no frio vai ao banco (síncrono) — fora do loop.
        agent_obj = await asyncio.to_thread(agent_service.get_agent_by_id, str(chat_request.agentId))
        if agent_obj:
            agent_data = agent_obj.model_dump()
            # Use agent's API key if available (decrypted)
            if agent_data.get("llm_api_key"):
                api_key = agent_data["llm_api_key"]
        else:
            # Agent not found
            logger.warning(f"[STREAM] Agent {chat_request.agentId} not found")
            return _resposta_de_politica(
                modo=modo, turno=turno, tipo=TIPO_POLICY_NOTICE, code="agent_not_found",
                texto=TEXTO_AGENTE_NAO_ENCONTRADO,
                legado={"token": TEXTO_AGENTE_NAO_ENCONTRADO},
            )
    except Exception as agent_error:
        logger.error(f"[STREAM] Error loading agent: {type(agent_error).__name__}")

    # ===========================================================================
    # WIDGET SECURITY: Domain Validation + Rate Limiting
    # ===========================================================================
    # 🔴 O gatilho é o MODO, não o `userId` do corpo: quem não prova ser o BFF
    # passa pelas checagens de widget, mande o corpo que mandar.
    if agent_data and modo == "widget":
        try:
            # 1. Validate domain whitelist
            await validate_widget_domain(request, agent_data, db)

            # 2. Rate limit by session_id (50 requests/hour default)
            await check_widget_rate_limit(
                db=db,
                identifier=str(chat_request.sessionId),
                agent_id=str(chat_request.agentId),
                max_requests=50,
                window_minutes=60
            )
            logger.info(f"[STREAM] Widget security checks passed for session {chat_request.sessionId}")
        except HTTPException:
            raise
        except Exception as widget_error:
            logger.warning(f"[STREAM] Widget security check error (allowing): {type(widget_error).__name__}")

    # =========================================================================
    # 🔴 SPEC-132-A B6 — O PRÉ-TRABALHO CARO, escrito UMA vez para os dois modos
    # =========================================================================
    # WIDGET: roda ANTES do stream, na ordem de sempre (grafo → visão → documento
    # → guardrail) — o contrato legado não tem linha de atividade.
    # PAINEL: roda DENTRO de `_gerar`, depois do `turn.accepted`.
    async def _o_grafo(nivel: Optional[str] = None):
        # 🔥 Usar cache de grafos (LRUCache) para evitar recriação a cada mensagem
        from app.services.langchain_service import get_or_create_graph
        from app.services.qdrant_service import get_qdrant_service

        qdrant = get_qdrant_service()
        argumentos = dict(
            company_id=str(chat_request.companyId),
            agent_id=str(chat_request.agentId),
            agent_config=agent_data,
            api_key=api_key,
            qdrant_service=qdrant,
            supabase_client=sync_db,
            enable_logging=True,
        )
        if nivel is not None:
            # SPEC-132-A B8: o esforço do pedido (o MESMO modelo do papel).
            argumentos["esforco_do_pedido"] = nivel
        # agent_data contém updated_at que é usado como chave do cache
        return await get_or_create_graph(**argumentos)

    async def _os_campos_antigos(mensagem: str) -> str:
        """`imageUrl`/`fileUrl` — o caminho de antes (o widget e as chamadas antigas)."""
        enriched_message = mensagem

        # F1 — visão/documentos GLOBAIS: default de plataforma quando o agente não
        # tem vision_model (nunca mais "não consigo visualizar"); PDF/DOCX viram
        # texto via docling. Fail-safe: falhou → segue só com o texto do usuário.
        if chat_request.imageUrl:
            from app.services.vision_service import describe_image

            vision_text = await describe_image(
                chat_request.imageUrl,
                company_id=str(chat_request.companyId),
                agent_id=str(chat_request.agentId) if chat_request.agentId else None,
                agent_data=agent_data,
            )
            if vision_text:
                enriched_message = f"{mensagem}\n\n[CONTEXTO VISUAL — imagem enviada pelo usuário]:\n{vision_text}"
                logger.info("[STREAM VISION] ✅ Imagem analisada (F1)")

        if chat_request.fileUrl:
            enriched_message = await anexar_documento_do_corretor(
                enriched_message, chat_request.fileUrl, chat_request.fileName or "",
                # 🔴 SPEC-130-B conserto (juiz J5): `str(None)` é "None" — uma corretora que não existe no ledger
                company_id=str(chat_request.companyId or ""),
            )
        return enriched_message

    async def _o_guardrail(enriched_message: str):
        """`(bloqueio | None, final_message)` — 🛡️ o MESMO portão de antes.

        `bloqueio` = `{code, texto, legado}`; quem chama decide a forma (o widget
        devolve a resposta de política; o painel emite o evento DENTRO do stream).
        """
        from app.agents.guardrails import SmithGuardrail

        final_message = enriched_message
        guardrail = None

        if agent_data:
            try:
                guardrail = SmithGuardrail(
                    agent_config=agent_data,
                    company_id=str(chat_request.companyId)
                )
                is_blocked, block_reason, sanitized_text = await guardrail.validate_input(enriched_message)

                if is_blocked:
                    logger.warning("[SECURITY] 🛡️ Stream message BLOCKED")
                    return ({"code": "policy",
                             "texto": block_reason or MENSAGENS_HUMANAS["policy"],
                             "legado": {"token": block_reason, "blocked": True}},
                            final_message)

                # 🔥 Usa texto sanitizado
                final_message = sanitized_text
                logger.debug("[SECURITY] ✅ Stream message passed guardrail")

            except HTTPException:
                raise
            except Exception as gr_error:
                logger.error(f"[SECURITY] ⚠️ Guardrail error: {type(gr_error).__name__}", exc_info=True)

                # 🔥 Fail-close se configurado (default: True)
                fail_close = getattr(guardrail, 'fail_close', True) if guardrail else True
                if fail_close:
                    return ({"code": "policy", "texto": TEXTO_ERRO_DE_SEGURANCA,
                             "legado": {"token": TEXTO_ERRO_DE_SEGURANCA, "blocked": True}},
                            final_message)
        return None, final_message

    async def _gravar_a_transcricao(transcricao: Optional[str]) -> None:
        """A transcrição do áudio vai para `payload.transcricao` da PERGUNTA (a bolha de voz).

        🔴 A linha é achada por `id` E pela conversa DESTA corretora (conferida lá em
        cima) — nunca só pelo `id` que veio no corpo (CLAUDE.md §7). Melhor-esforço.
        """
        if not (transcricao and chat_request.userMessageId and conversation_id):
            return
        try:
            linhas = (
                await db.client.table("messages")
                .select("payload")
                .eq("id", str(chat_request.userMessageId))
                .eq("conversation_id", conversation_id)
                .eq("role", "user")
                .limit(1)
                .execute()
            ).data or []
            if not linhas:
                return
            payload = dict(linhas[0].get("payload") or {})
            payload["transcricao"] = transcricao
            await (
                db.client.table("messages")
                .update({"payload": payload})
                .eq("id", str(chat_request.userMessageId))
                .eq("conversation_id", conversation_id)
                .execute()
            )
        except Exception as sem_transcricao:  # noqa: BLE001
            logger.warning("[STREAM ANEXOS] transcrição não gravada (%s)",
                           type(sem_transcricao).__name__)

    # =========================================================================
    # A PERSISTÊNCIA — a mesma para os dois modos, e ela é do TURNO
    # =========================================================================
    async def _persistir(conteudo: str, dados_do_turno: Dict[str, Any]) -> bool:
        """Grava a resposta (ou o parcial). Devolve se gravou.

        ⛔ Conteúdo vazio não vira mensagem: uma falha antes do primeiro token
        não deixa bolha muda na conversa — deixa só o evento `error`.
        """
        nonlocal conversation_id, current_unread
        if not (conteudo or "").strip():
            return False
        try:
            if not conversation_id:
                new_conv = (
                    await db.client.table("conversations")
                    .insert({
                        "company_id": str(chat_request.companyId),
                        "user_id": str(chat_request.userId) if chat_request.userId else None,
                        "session_id": str(chat_request.sessionId),
                        "agent_id": str(chat_request.agentId) if chat_request.agentId else None,
                        "channel": chat_request.channel or "web",
                        "status": "open",
                        "unread_count": 1,
                        "last_message_preview": conteudo[:100],
                        "last_message_at": datetime.utcnow().isoformat() + "Z",
                    })
                    .execute()
                )
                if new_conv.data:
                    conversation_id = new_conv.data[0]["id"]

            if not conversation_id:
                return False

            # 🔴 C2 — RETENTATIVA É A MESMA LINHA, NÃO UMA NOVA.
            # R3: repetir a pergunta é uma nova TENTATIVA do mesmo turno, e a
            # tela reusa o mesmo `assistantMessageId` e o mesmo
            # `client_request_id`. Um INSERT aqui violava a chave primária E o
            # índice novo, caía no `except BaseException` e a resposta boa da 2ª
            # tentativa terminava como `persisted: false` — o parcial da 1ª
            # ficava na tela para sempre. Com UPSERT por `id`, a tentativa nova
            # SUBSTITUI a linha: conteúdo novo, status novo, `attempt` somado.
            anteriores = (
                await db.client.table("messages")
                .select("payload")
                .eq("id", assistant_message_id)
                .limit(1)
                .execute()
            ).data or []
            tentativa_anterior = 0
            if anteriores:
                tentativa_anterior = int(
                    (((anteriores[0].get("payload") or {}).get("turn") or {}).get("attempt")) or 0
                )
            dados_do_turno = dict(dados_do_turno)
            dados_do_turno["attempt"] = tentativa_anterior + 1

            message_data = {
                "id": assistant_message_id,
                "conversation_id": conversation_id,
                "role": "assistant",
                "content": conteudo,
                "type": "text",
            }
            if client_request_id:
                # 🔴 O `client_request_id` vai no TOPO do payload porque é ele
                # que o índice único parcial da migration A.1 lê
                # (`payload->>'client_request_id'`) — e é por ele que o Realtime
                # da tela descarta a duplicata.
                message_data["payload"] = {
                    "client_request_id": client_request_id,
                    "turn": dados_do_turno,
                }
            else:
                message_data["payload"] = {"turn": dados_do_turno}

            try:
                await db.client.table("messages").upsert(message_data, on_conflict="id").execute()
            except BaseException as choque:  # noqa: BLE001
                if not (_e_conflito_de_chave(choque) and client_request_id):
                    raise
                # 🔴 A TENTATIVA CHEGOU COM UM `id` NOVO.
                # 📊 05/09/2026, canário --vivo: a 2ª tentativa do mesmo
                # `client_request_id` veio com outro `assistantMessageId`, o
                # índice recusou (`409 Conflict`) e a RESPOSTA BOA virou
                # `persisted: false` — o parcial da 1ª ficava na tela para
                # sempre. O UPSERT por `id` nao alcanca esse caso: a linha
                # existe, mas com OUTRA chave primaria. Entao a achamos pelo
                # que de fato identifica o turno — conversa + papel +
                # `client_request_id` — e escrevemos NELA, mantendo o `id`
                # antigo (que e o que a tela ja tem na mao).
                do_turno = (
                    await db.client.table("messages")
                    .select("id, payload")
                    .eq("conversation_id", conversation_id)
                    .eq("role", "assistant")
                    .eq("payload->>client_request_id", client_request_id)
                    .limit(1)
                    .execute()
                ).data or []
                if not do_turno:
                    raise
                id_antigo = do_turno[0]["id"]
                dados_do_turno["attempt"] = int(
                    (((do_turno[0].get("payload") or {}).get("turn") or {}).get("attempt")) or 1
                ) + 1
                await (
                    db.client.table("messages")
                    .update({
                        "content": conteudo,
                        "type": "text",
                        "payload": {"client_request_id": client_request_id,
                                    "turn": dados_do_turno},
                    })
                    .eq("id", id_antigo)
                    .execute()
                )
                logger.info("[STREAM] retentativa reaproveitou a linha %s (tentativa %s)",
                            str(id_antigo)[:8], dados_do_turno["attempt"])

            await db.client.table("conversations").update({
                "last_message_preview": conteudo[:100],
                "last_message_at": datetime.utcnow().isoformat() + "Z",
                "unread_count": current_unread + 1,
            }).eq("id", conversation_id).execute()

            logger.info("[STREAM] resposta gravada em %s (%s, tentativa %s)",
                        str(conversation_id)[:8], dados_do_turno.get("status"),
                        dados_do_turno.get("attempt"))
            return True
        except BaseException as erro_ao_gravar:  # noqa: BLE001
            # ⚠️ `BaseException` e não `Exception`: `CancelledError` desce de
            # `BaseException`, e é ELA que chega aqui quando o Stop cancela a
            # task no meio da gravação (E4). Perder o parcial por causa disso
            # foi o defeito (x) do GATE ZERO.
            logger.error("[STREAM] falha ao gravar a resposta: %s", type(erro_ao_gravar).__name__)
            return False

    async def _entregas_do_turno() -> List[Dict[str, Any]]:
        """As peças que o Artifact Hub publicou DENTRO deste turno.

        📊 `ArtifactService.publicar` só enxerga `id, artifact_id, version,
        status, brand_snapshot` — não tem título nem tipo para dar. Por isso o
        ContextVar guarda só o `artifact_id`, e o nome que o corretor lê sai
        daqui, de um SELECT em `artifacts` já no fim do turno.
        """
        registradas = pecas_do_turno.get(None) or []
        ids = [p.get("artifact_id") for p in registradas if p.get("artifact_id")]
        if not ids:
            return []
        entregas = []
        try:
            achadas = (
                await db.client.table("artifacts")
                .select("id, title, kind")
                .eq("company_id", str(chat_request.companyId))
                .in_("id", ids)
                .execute()
            )
            for linha in (achadas.data or []):
                entregas.append({
                    "artifact_id": linha["id"],
                    "title": linha.get("title") or "Entrega",
                    "kind_human": KINDS_HUMANOS.get(linha.get("kind"), "Entrega"),
                    "href": href_da_peca(linha["id"]),
                })
        except Exception as erro_de_leitura:  # noqa: BLE001
            logger.warning("[STREAM] entregas do turno indisponiveis: %s", type(erro_de_leitura).__name__)
        return entregas

    # =========================================================================
    # MODO WIDGET — o contrato antigo, intacto
    # =========================================================================
    if modo == "widget":
        # ⚠️ O pré-trabalho do widget fica ANTES do stream, na ordem de sempre.
        graph = await _o_grafo()
        enriched_message = await _os_campos_antigos(chat_request.chatInput)
        bloqueio, final_message = await _o_guardrail(enriched_message)
        if bloqueio is not None:
            return _resposta_de_politica(
                modo=modo, turno=turno, tipo=TIPO_POLICY_BLOCKED, code=bloqueio["code"],
                texto=bloqueio["texto"], legado=bloqueio["legado"],
            )

        async def event_generator():
            """Generate SSE events with tokens from the LLM stream."""
            full_response = ""
            try:
                async for token in stream_agent(
                    graph=graph,
                    user_message=final_message,
                    company_id=str(chat_request.companyId),
                    user_id=str(chat_request.userId) if chat_request.userId else None,
                    session_id=str(chat_request.sessionId),
                    company_config=company_config,
                    options=chat_request.options,
                    supabase_client=sync_db,
                    agent_id=str(chat_request.agentId) if chat_request.agentId else None,
                    async_supabase_client=db.client,
                ):
                    full_response += token
                    yield _sse_legado({"token": token})

                await _persistir(full_response, {"status": "complete"})
            except Exception as erro_do_widget:  # noqa: BLE001
                logger.error("[STREAM] erro no stream do widget: %s",
                             type(erro_do_widget).__name__, exc_info=True)
                # ⛔ A exceção CRUA não vai ao browser (R7): o que sai é a
                # família, a correlação e uma frase que alguém entende.
                yield _sse_legado({"error": erro_seguro(erro_do_widget)})

            yield "data: [DONE]\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream",
                                 headers=dict(CABECALHOS_SSE))

    # =========================================================================
    # MODO PAINEL — o turno tipado, numa task que não morre com a conexão
    # =========================================================================
    # ⚠️ Dois tetos, e nenhuma fila nova (§5): a fila do turno tem teto para
    # o consumidor que sumiu nao crescer sem fim na memoria, e o processo tem
    # teto de turnos em voo. Estourou o segundo, e 429 — nao e espera muda.
    if len(TURNOS_ATIVOS) - (1 if reserva is not None else 0) >= TETO_DE_TURNOS_ATIVOS:
        logger.warning("[STREAM] teto de turnos em voo atingido (%d)", len(TURNOS_ATIVOS))
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="muitos turnos em voo; tente de novo em instantes")

    fila: "asyncio.Queue" = asyncio.Queue(maxsize=TETO_DE_EVENTOS_NA_FILA)

    # 🔴 ANTES do `create_task`: a task COPIA o contexto, e é essa cópia que o
    # Artifact Hub vai encontrar quando publicar no meio do turno.
    pecas_do_turno.set([])

    # 🔴 E a MESMA cópia de contexto carrega QUAL TURNO está em voo, para o nó
    # de tool poder escrever isso no `trace_id` da invocação (P-PILOTO-18).
    # ⛔ Não é um segundo registro de tool call: a escrita continua sendo uma só
    # (`nodes.py:1057 → RegistroDeInvocacao → gateway.py:294`). O que se
    # acrescenta é a CHAVE que permite a junção, e ela é montada por
    # `chave_de_rastro` — a mesma função dos dois lados (CLAUDE.md §5 e §9.4).
    marcar_turno(client_request_id)

    #: SPEC-132-A B8 — Rápido · Equilibrado · Máximo (já validado por `opcoes_validas`).
    escolha = (chat_request.options or {}).get("esforco") or "equilibrado"

    async def _preparar_o_turno(emitir, fases: Dict[str, Any], extras: Dict[str, Any]):
        """O pré-trabalho CARO do painel — DENTRO do stream (SPEC-132-A B6).

        Os anexos (`chat_anexos.preparar` + os campos antigos) e o grafo (frio na 1ª
        vez do processo ou do esforço) correm JUNTOS; o guardrail vem depois, sobre
        a mensagem já enriquecida — a mesma ordem de decisão de antes.
        Devolve `(final_message, graph, politica | None)`.
        """
        from app.factories.model_policy import nivel_da_escolha

        nivel = nivel_da_escolha(escolha)
        anexos = list(chat_request.attachments or [])
        mostrou_anexos = bool(anexos or chat_request.imageUrl or chat_request.fileUrl)
        if mostrou_anexos:
            emitir("stage.started", {"key": CHAVE_DOS_ANEXOS, "label": rotulo_dos_anexos(
                anexos, imagem_antiga=bool(chat_request.imageUrl),
                documento_antigo=(chat_request.fileName or "") if chat_request.fileUrl else None)})
        else:
            emitir("stage.started", dict(ESTAGIO_PENSANDO))

        async def _cronometrar(nome: str, corrotina):
            inicio = time.monotonic()
            try:
                return await corrotina
            finally:
                fases[nome] = int((time.monotonic() - inicio) * 1000)

        def _ao_progredir(*args, **kwargs):
            # ⚠️ Serve chamado com ou sem `await`: devolve um futuro já resolvido.
            rotulo = None
            for item in list(args) + list(kwargs.values()):
                if isinstance(item, dict):
                    rotulo = rotulo_dos_anexos([item])
                    break
                if isinstance(item, str) and item.strip() and len(item) <= 80:
                    rotulo = item.strip()
                    break
            if rotulo:
                emitir("stage.started", {"key": CHAVE_DOS_ANEXOS, "label": rotulo})
            pronto = asyncio.get_running_loop().create_future()
            pronto.set_result(None)
            return pronto

        async def _ler_o_que_veio() -> str:
            texto = await _os_campos_antigos(chat_request.chatInput or "")
            if not anexos:
                return texto
            resultado = None
            try:
                from app.services.chat_anexos import preparar

                resultado = await preparar(str(chat_request.companyId), anexos,
                                           ao_progredir=_ao_progredir)
            except Exception as sem_leitor:  # noqa: BLE001 — anexo nunca derruba o turno
                logger.error("[STREAM ANEXOS] leitura dos anexos falhou (%s)",
                             type(sem_leitor).__name__)
            texto, transcricao = incorporar_os_anexos(texto, resultado)
            extras["anexos"] = {
                "recebidos": len(anexos),
                "lidos": len(_como_lista(getattr(resultado, "lidos", None))) if resultado else 0,
                "avisos": len(_como_lista(getattr(resultado, "avisos", None))) if resultado else 1,
            }
            await _gravar_a_transcricao(transcricao)
            return texto

        tarefa_do_grafo = asyncio.ensure_future(_cronometrar("grafo", _o_grafo(nivel)))
        tarefa_do_grafo.add_done_callback(lambda t: t.cancelled() or t.exception())
        try:
            texto = await _cronometrar("anexos", _ler_o_que_veio())
        except BaseException:
            tarefa_do_grafo.cancel()
            raise
        graph = await tarefa_do_grafo
        extras["esforco_nivel"] = _nivel_efetivo(agent_data, nivel)

        bloqueio, final = await _cronometrar("guardrail", _o_guardrail(texto))
        if bloqueio is not None:
            return texto, graph, {"tipo": TIPO_POLICY_BLOCKED, "code": bloqueio["code"],
                                  "texto": bloqueio["texto"]}
        if mostrou_anexos:
            emitir("stage.started", dict(ESTAGIO_PENSANDO))
        return final, graph, None

    async def _gerar(fila_de_saida: "asyncio.Queue") -> None:
        comeco = time.monotonic()
        ttft_ms = None
        # SPEC-132-A B1: `ttft_ms` agora conta do RECEBIMENTO do pedido; o de antes
        # (do começo da geração) continua gravado, para comparar com o histórico.
        ttft_gerar_ms = None
        fases: Dict[str, Any] = {"preparo": int((comeco - recebido_em) * 1000)}
        extras: Dict[str, Any] = {"esforco": escolha}
        politica: Optional[Dict[str, str]] = None
        partes: List[str] = []
        estagios: List[str] = []
        estado = "complete"
        erro = None
        # 🔴 POR QUE O MODELO PAROU DE FALAR — §12.1: fato, não inferência.
        # 📊 09/09/2026: as 10 respostas cortadas da Resulta foram gravadas com
        # `status="complete"` e nada mais; descobrir o motivo exigiu cruzar
        # `messages` com `token_usage_logs` à mão. Agora o motivo vem no turno.
        desfecho: Dict[str, Any] = {}

        def emitir(tipo: str, payload: Dict[str, Any]) -> None:
            # `put_nowait`: emitir NUNCA suspende — e o que nao suspende nao
            # morre no meio de um cancelamento. Fila cheia = consumidor que
            # sumiu: o evento e descartado, a GERACAO segue, e a resposta e
            # gravada do mesmo jeito (o que importa e a persistencia).
            try:
                fila_de_saida.put_nowait((tipo, payload))
            except asyncio.QueueFull:
                logger.warning("[STREAM] fila cheia no turno %s; evento %s descartado",
                               (client_request_id or "-")[:8], tipo)

        try:
            emitir("turn.accepted", dict(turno))
            # 🔴 SPEC-132-A B6 — o caro começa AQUI, com o stream já aberto.
            final_message, graph, politica = await _preparar_o_turno(emitir, fases, extras)
            if politica is not None:
                # O guardrail barrou: o MESMO aviso de antes, agora dentro do stream —
                # e NADA é gravado (sem delta não há conteúdo; R5).
                estado = "failed"
                emitir(politica["tipo"], {"code": politica["code"],
                                          "message_human": politica["texto"]})
            inicio_do_modelo = time.monotonic()
            async for ev in (stream_agent_eventos(
                graph,
                user_message=final_message,
                company_id=str(chat_request.companyId),
                user_id=str(chat_request.userId) if chat_request.userId else None,
                session_id=str(chat_request.sessionId),
                company_config=company_config,
                options=chat_request.options,
                supabase_client=sync_db,
                agent_id=str(chat_request.agentId) if chat_request.agentId else None,
                async_supabase_client=db.client,
                client_request_id=client_request_id,
                esforco=escolha,
                fases=fases,
            ) if politica is None else _nenhum_evento()):
                especie = ev.get("kind")
                if especie == "delta":
                    texto = ev.get("text") or ""
                    if not texto:
                        continue
                    if ttft_ms is None:
                        agora = time.monotonic()
                        ttft_ms = int((agora - recebido_em) * 1000)
                        ttft_gerar_ms = int((agora - comeco) * 1000)
                        fases["primeiro_token"] = max(
                            0, int((agora - inicio_do_modelo) * 1000) - int(fases.get("contexto") or 0))
                    partes.append(texto)
                    emitir("assistant.content.delta", {"text": texto})
                elif especie == "tool_start":
                    estagio = estagio_da_tool(ev.get("name"))
                    if estagio["key"] not in estagios:
                        estagios.append(estagio["key"])
                    emitir("stage.started", estagio)
                elif especie == "tool_end":
                    emitir("stage.completed", {"key": estagio_da_tool(ev.get("name"))["key"]})
                elif especie == "final":
                    # ⛔ Não vira evento SSE novo: o contrato do turno é o que a
                    # tela já sabe ler (R6). Isto é diagnóstico, e vai ao banco.
                    desfecho = {
                        "finish_reason": ev.get("finish_reason"),
                        "usage": ev.get("usage"),
                        "continuations": ev.get("continuations"),
                        "truncated": ev.get("truncated"),
                    }
                elif especie == "error":
                    excecao = ev.get("exc") or RuntimeError("falha no stream")
                    erro = erro_seguro(excecao)
                    estado = "failed"
                    # 🔴 A MESMA correlacao que foi ao browser tem de estar no
                    # log — senao o corretor liga com um `correlation_id` que nao
                    # existe em lugar nenhum. ⛔ O TIPO da excecao, nunca o texto
                    # dela, e nunca a pergunta do corretor.
                    logger.error("[STREAM] turno falhou correlation_id=%s code=%s exc=%s",
                                 erro.get("correlation_id"), erro.get("code"),
                                 type(excecao).__name__)
                    break
        except asyncio.CancelledError:
            # Parar foi decisão de alguém — o parcial vale, e ele é gravado.
            estado = "interrupted"
        except BaseException as exc:  # noqa: BLE001
            estado = "failed"
            erro = erro_seguro(exc)
            logger.error("[STREAM] turno falhou correlation_id=%s code=%s exc=%s",
                         erro.get("correlation_id"), erro.get("code"), type(exc).__name__)

        finally:
            # 🔴 O FECHO DO TURNO E `finally`, e nao codigo solto depois do
            # `except`. Uma excecao no meio daqui (um SELECT de entregas que
            # falha, por exemplo) deixava a chave viva em TURNOS_ATIVOS e a
            # sentinela sem ser posta — o consumidor ficava em batimento
            # eterno e o Stop achava um turno que nao existia mais.
            try:
                conteudo = "".join(partes)
                entregas = await _entregas_do_turno()
                for entrega in entregas:
                    emitir("artifact.ready", entrega)
                if erro:
                    emitir("error", erro)
                if conteudo:
                    # ⚠️ O campo e `content` — e o nome do contrato R6.
                    emitir("assistant.content.completed", {"content": conteudo})

                agora_no_fecho = time.monotonic()
                dados_do_turno = {
                    "client_request_id": client_request_id,
                    "status": estado,
                    "ttft_ms": ttft_ms,
                    "total_ms": int((agora_no_fecho - recebido_em) * 1000),
                    "stages": estagios,
                    "artifacts": [{"artifact_id": e["artifact_id"], "title": e["title"]}
                                  for e in entregas],
                    "error_code": (erro or {}).get("code") or (politica or {}).get("code"),
                    # SPEC-132-A B1 — as fases medidas, e as medidas de antes ao lado
                    "ttft_gerar_ms": ttft_gerar_ms,
                    "total_gerar_ms": int((agora_no_fecho - comeco) * 1000),
                    "fases_ms": dict(fases),
                }
                # SPEC-132-A B8 — o esforço escolhido e o que o modelo usou; os anexos lidos
                for chave, valor in extras.items():
                    if valor is not None:
                        dados_do_turno[chave] = valor
                # ⚠️ Só o que o modelo de fato declarou entra: chave com `None`
                # é ruído no `payload` e mente sobre ter havido medição.
                for chave, valor in (desfecho or {}).items():
                    if valor is not None:
                        dados_do_turno[chave] = valor

                # 🔴 QUE FERRAMENTAS ESTE TURNO CHAMOU — P-PILOTO-18, reescrita.
                #
                # ⛔ UMA ESCRITA, DOIS LEITORES. Quem grava `tool_invocations` é
                # o nó de tool, e continua sendo o único. Aqui só se LÊ de volta,
                # pela chave que o próprio turno montou. 📊 `stages` (acima) diz
                # que o agente PAROU para consultar algo; `tool_calls` diz o QUÊ,
                # se deu certo, quanto demorou e com que erro — e `stages` não
                # sabe nada disso.
                #
                # ⚠️ Falhar aqui NUNCA derruba o turno: a resposta do corretor
                # vale mais que a contabilidade dela. Sem as tool calls, o turno
                # grava sem a chave (nunca com `[]` mentindo "não chamou nada").
                #
                # 🔴 E A JUNCAO SO EXISTE SE HOUVER TURNO. Ate 14/09/2026 esta
                # chave era montada mesmo sem `client_request_id` — e sem ele
                # `chave_de_rastro` devolvia a SESSAO PURA, que e o que o no de
                # tool grava fora de turno. O `.eq("trace_id", chave)` colhia
                # entao as ferramentas de OUTROS momentos da mesma sessao e as
                # gravava como "as deste turno". Sem turno nao se mente: o campo
                # fica AUSENTE, com o motivo escrito ao lado.
                chave_de_juncao = (
                    chave_de_rastro(chat_request.sessionId, client_request_id)
                    if client_request_id else None
                )
                if not client_request_id:
                    dados_do_turno["tool_calls_ausentes"] = "sem client_request_id"
                if chave_de_juncao and estagios:
                    try:
                        invocadas = (
                            await db.client.table("tool_invocations")
                            # 🔴 `company_id` PRIMEIRO e SEMPRE: o backend usa
                            # service role, e RLS sem filtro no código não
                            # protege nada (CLAUDE.md §7).
                            .select("capability_key, status, latency_ms, error_code, started_at")
                            .eq("company_id", str(chat_request.companyId))
                            .eq("trace_id", chave_de_juncao)
                            .order("started_at")
                            .limit(50)
                            .execute()
                        ).data or []
                        if invocadas:
                            dados_do_turno["tool_calls"] = [
                                {"capability_key": linha.get("capability_key"),
                                 "status": linha.get("status"),
                                 "latency_ms": linha.get("latency_ms"),
                                 "error_code": linha.get("error_code")}
                                for linha in invocadas
                            ]
                    except BaseException as sem_juncao:  # noqa: BLE001
                        logger.warning(
                            "[STREAM] tool_calls nao lidas no turno %s: %s",
                            (client_request_id or "-")[:8], type(sem_juncao).__name__)
                if estado == "interrupted":
                    # E11 — quem parou fica escrito ao lado do parcial.
                    dados_do_turno["stopped_by"] = PARADAS.get(chave_do_turno)

                gravou = await _persistir(conteudo, dados_do_turno)
                emitir("turn.completed", {
                    "status": estado,
                    "ttft_ms": ttft_ms,
                    "total_ms": dados_do_turno["total_ms"],
                    "persisted": gravou,
                    "error_code": dados_do_turno["error_code"],
                })
            except BaseException as falha_no_fecho:  # noqa: BLE001
                logger.error("[STREAM] falha ao fechar o turno %s: %s",
                             (client_request_id or "-")[:8], type(falha_no_fecho).__name__)
            finally:
                # ⛔ Estes tres nao dependem de nada dar certo acima.
                TURNOS_ATIVOS.pop(chave_do_turno, None)
                PARADAS.pop(chave_do_turno, None)
                try:
                    fila_de_saida.put_nowait(None)
                except asyncio.QueueFull:
                    # A fila cheia ja e sinal de consumidor ausente; e o
                    # gerador ainda tem a segunda saida: ele confere
                    # `task.done()` a cada batimento.
                    logger.warning("[STREAM] sentinela nao coube na fila do turno %s",
                                   (client_request_id or "-")[:8])

    task = asyncio.create_task(_gerar(fila))
    TURNOS_ATIVOS[chave_do_turno] = task
    if reserva is not None and reserva.parado:
        task.cancel()  # o Stop chegou enquanto o turno ainda se preparava

    async def gerador_do_painel():
        seq = Sequenciador(turno)
        try:
            while True:
                try:
                    item = await asyncio.wait_for(fila.get(), timeout=SEGUNDOS_DE_BATIMENTO)
                except asyncio.TimeoutError:
                    if task.done() and fila.empty():
                        # A task terminou e nao ha mais nada a ler: se a
                        # sentinela se perdeu (fila cheia), o turno acaba aqui
                        # do mesmo jeito — batimento eterno nao e opcao.
                        break
                    # ⛔ O batimento e um EVENTO, nunca texto: ele nao entra em
                    # `content` e nao aparece na conversa.
                    yield seq.sse("heartbeat", {})
                    continue
                if item is None:
                    break
                tipo, payload = item
                yield seq.sse(tipo, payload)
            yield "data: [DONE]\n\n"
        finally:
            # 🔴 A task NÃO é cancelada aqui. Quando o browser fecha, este
            # gerador morre — e a geração segue até o fim, grava a resposta e
            # some sozinha do registro. Foi por cancelar aqui que a resposta
            # inteira se perdia ao trocar de aba (A.4).
            logger.debug("[STREAM] consumidor saiu do turno %s", (client_request_id or "-")[:8])

    return StreamingResponse(gerador_do_painel(), media_type="text/event-stream",
                             headers=dict(CABECALHOS_SSE))


class StopRequest(BaseModel):
    """O Stop do painel — B.4/R8."""

    model_config = {"populate_by_name": True}

    clientRequestId: str = Field(..., alias="client_request_id")
    companyId: UUID4 = Field(..., alias="company_id")
    stoppedBy: Optional[str] = Field(None, alias="stopped_by")


@router.post("/chat/stop")
async def chat_stop(request: Request, stop_request: StopRequest):
    """Para o turno de verdade — não só o `fetch` do browser.

    ⚠️ Antes, "Parar" abortava a conexão e o backend continuava gerando sem
    saber. Agora ele cancela a task: o parcial é gravado com
    `status="interrupted"`, e quem pediu fica registrado ao lado dele.
    """
    if _modo_de_confianca(request) != "painel":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="não autorizado")

    chave = "%s:%s" % (stop_request.companyId, stop_request.clientRequestId)
    task = TURNOS_ATIVOS.get(chave)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="turno não está em voo")

    PARADAS[chave] = stop_request.stoppedBy or "painel"
    task.cancel()
    logger.info("[STREAM] Stop pedido para o turno %s", stop_request.clientRequestId[:8])
    return {"status": "interrupted"}


# =============================================================================
# SESSION TTL - DELETE EXPIRED SESSION MEMORY
# =============================================================================

@router.delete("/session")
async def delete_session(request: Request, delete_request: DeleteSessionRequest):
    """Apaga os checkpoints de uma sessão que expirou (TTL de 24 h).

    -------------------------------------------------------------------------
    🔴 SPEC-098 U4.a/E5 — O CORPO NÃO ESCOLHE MAIS A CORRETORA
    -------------------------------------------------------------------------

    📊 Medido em 06/09/2026: esta rota era o irmão do P0 da SPEC-096. Ela não
    passava por `_modo_de_confianca`, aceitava `companyId` do corpo e a única
    checagem de posse tinha um **`except → pass` explícito** — comentado como
    *"para não quebrar o widget"*. Um banco mudo (ou um erro de digitação numa
    coluna) transformava a checagem em nada, e o `thread_id` era montado com o
    `companyId` que o corpo mandasse.

    ⚠️ **Fail-open é pior que guarda nenhum**: com guarda nenhum o defeito é
    visível; com fail-open ele é uma linha de log de nível `warning` em produção.

    Agora existem dois modos, e é o CABEÇALHO que decide qual:

        `painel` (chave interna válida)  o BFF já tem a sessão do corretor —
                                         o `companyId` do corpo é honrado e a
                                         posse é conferida contra ele;
        `widget` (sem chave)             o `companyId` do corpo é IGNORADO: a
                                         corretora é **DERIVADA** da linha de
                                         `conversations` achada por `session_id`.

    🔴 Por que derivar funciona: `conversations.session_id` tem UNIQUE
    (`conversations_session_id_key`) — a sessão aponta para no máximo uma linha,
    e essa linha JÁ diz de quem ela é. O widget nunca precisou dizer a corretora;
    ele só precisava dizer a sessão.

    ⛔ E o `except → pass` morreu: banco mudo agora é **503**, não permissão.
    Não conseguir provar a posse não é o mesmo que provar a posse. A memória de
    sessão que não foi apagada agora é apagada na próxima tentativa; a memória
    apagada da corretora errada não volta.
    """
    modo = _modo_de_confianca(request)
    session_id = str(delete_request.sessionId)

    try:
        db = get_supabase_client()
        conv = db.client.table("conversations") \
            .select("id, company_id") \
            .eq("session_id", session_id) \
            .limit(1) \
            .execute()
        linhas = (conv.data or [])
    except Exception as e:
        # 🔴 O `except → pass` de antes morava aqui. 503, não `pass`.
        logger.error("[Session TTL] não deu para conferir de quem é a sessão: %s",
                     type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível confirmar de quem é esta sessão agora. Tente de novo.",
        ) from e

    if not linhas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found for this company",
        )

    dona = str(linhas[0].get("company_id") or "")
    if modo == "painel":
        # O BFF provou que é o BFF: o `companyId` que ele mandou vale como
        # afirmação — e é conferido contra a dona real.
        if str(delete_request.companyId) != dona:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found for this company",
            )
    elif not dona:
        # Conversa sem corretora não deveria existir; sem ela não há `thread_id`
        # legítimo para montar. Não se adivinha com o corpo.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found for this company",
        )

    try:
        from app.services.memory_service import MemoryService

        # 🔴 O `thread_id` é montado com a corretora DERIVADA do banco — nunca
        #    com a que veio no corpo. É esta linha que o defeito atacava.
        thread_id = f"{dona}:{session_id}"

        logger.info(f"[Session TTL] Deleting expired session: {thread_id}")

        # Use MemoryService to clean up checkpoints
        memory_service = MemoryService(supabase_client=get_supabase_client().client)
        success = await memory_service.clear_session_memory(thread_id)

        if success:
            return {"success": True, "message": "Session memory cleared"}
        else:
            return {"success": False, "message": "Failed to clear session memory"}

    except Exception as e:
        logger.error(f"[Session TTL] Error deleting session: {e}")
        # ⛔ A exceção crua não vai ao cliente (R7): o texto dela carrega URL de
        # conexão e id de terceiro. O detalhe vive no log.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=erro_seguro(e, code="transport")["message_human"],
        ) from e
