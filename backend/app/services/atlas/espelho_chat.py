"""A ponte entre o que o Observador captura e o chat da corretora.

POR QUE ESTE MÓDULO EXISTE
==========================
📊 06/08/2026: a captura da AutoFleet gravava **124 mensagens por hora** em
`attendance_transcripts` — conversas reais de sinistro, em tempo real — e a tela
`Atendimentos → Conversas` da corretora dizia *"Nenhuma conversa ainda"*.

As duas coisas eram verdade. O acervo enchia; a mesa de trabalho ficava vazia.
Faltava a ponte: `observer_tap` consome o evento enquanto o agente de atendimento
está desligado, e era o pipeline consumido que criaria a conversa.

Este módulo é essa ponte, e nada além dela.

O QUE ELA NÃO FAZ — e cada linha disso é uma decisão do Founder
===============================================================
**Não dá voz ao Observador.** Não há caminho de envio aqui. O Observador observa
em silêncio, ligado a hora toda, e isso não muda.

**Não liga agente nenhum.** A conversa nasce e o agente continua desligado até
alguém clicar no botão. Quem decide se o agente fala é
`attendance_capture.attendance_agent_active`, lá no `observer_tap`, e esta ponte
não tem opinião sobre isso — ela grava e devolve.

**Não esconde histórico.** A janela desta ponte é larga (30 dias) e existe para
um caso só: o HISTORY_SYNC de um pareamento novo, que chega com meses de conversa
de uma vez. Quem enxuga a mesa de trabalho é a LISTA, com `JANELA_DA_LISTA_DIAS`.
Abrir uma conversa mostra o histórico inteiro — um sinistro que arrasta 45 dias
continua legível do começo.

A CHAVE — o ponto mais fácil de errar deste arquivo
====================================================
🔴 A conversa criada aqui tem de ser a **mesma** que o pipeline do agente
encontra no dia em que ele for ligado.

📊 `webhook.get_or_create_conversation` procura por
`company_id` + `user_id` + `channel` + `agent_id IS NULL`. Procurar por
`user_phone` — o caminho óbvio — criaria uma conversa que o pipeline não acharia,
e o mesmo cliente apareceria em duas: uma com o histórico do espelho, outra com o
do agente. O defeito só apareceria no dia do go-live, que é o dia mais caro
possível para descobrir qualquer coisa.

Por isso o usuário é resolvido pela **mesma** `integration_service.get_or_create_user`
e a busca usa os **mesmos** filtros. Há teste de convergência, e ele lê a linha
do `webhook.py` para avisar se ela mudar.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Quantos dias de conversa aparecem NA LISTA do chat. Decisão do Founder,
# 06/08/2026. É o que a atendente vê ao abrir a tela.
JANELA_DA_LISTA_DIAS = 7

# Até onde uma mensagem ainda merece entrar no chat. Larga de propósito: não é
# para esconder conversa (disso cuida a lista), é para o HISTORY_SYNC de um
# pareamento novo não despejar meses de histórico de uma vez só.
LIMITE_DE_RECENCIA_HORAS = 720.0  # 30 dias

# Tipos que valem uma conversa mesmo sem uma palavra escrita.
_TIPOS_SEM_TEXTO = ("audio", "image", "document", "video", "sticker")


def _digitos(valor: Any) -> str:
    return "".join(ch for ch in str(valor or "") if ch.isdigit())


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def session_id_do_chat(company_id: str, telefone: str) -> str:
    """A MESMA sessão que o pipeline do agente monta (`webhook.py:491`).

    📊 Lá: ``f"whatsapp:{payload.phone}:{company_id}:{agent_suffix}"``, com
    ``agent_suffix = "default"`` quando a integração não tem agente vinculado —
    que é o caso das três linhas de observer em produção (`agent_id = null`).

    Só dígitos, porque o mesmo número chega ora ``+55 (47) 9995-6540``, ora
    ``554799956540``. Um hífen de diferença criaria uma segunda conversa para o
    mesmo cliente, e ninguém desconfiaria de um hífen.
    """
    return f"whatsapp:{_digitos(telefone)}:{company_id}:default"


def deve_espelhar(*, counterparty: str, texto: str, msg_type: str,
                  e_grupo: bool, e_seguradora: bool, idade_horas: float,
                  limite_horas: float = LIMITE_DE_RECENCIA_HORAS) -> bool:
    """Esta mensagem capturada merece uma conversa no chat da corretora? PURO.

    O chat é a mesa de trabalho da corretora; o acervo
    (`attendance_transcripts`) é outra coisa e guarda tudo — inclusive
    seguradora, grupo e conversa de meses atrás.

    ⚠️ A janela daqui NÃO é a que a atendente vê. Mensagem ao vivo tem idade ~0
    e passa sempre. Quem esconde conversa velha da mesa é a LISTA, com
    `JANELA_DA_LISTA_DIAS`. Esta existe para o HISTORY_SYNC de um pareamento
    novo, que chegaria com meses de história de uma vez.

    Áudio sem texto passa de propósito: a atendente precisa VER que chegou algo.
    Uma conversa que aparece vazia é melhor que uma que não aparece.
    """
    if not str(counterparty or "").strip():
        return False
    if e_grupo or e_seguradora:
        return False
    if float(idade_horas) > float(limite_horas):
        return False
    return bool(str(texto or "").strip()) or str(msg_type or "") in _TIPOS_SEM_TEXTO


async def espelhar_no_chat(*, company_id: str, counterparty: str, texto: str,
                           msg_type: str, direcao: str, message_id: str,
                           quando_iso: str, nome: Optional[str] = None,
                           db: Any = None) -> Optional[str]:
    """Põe a mensagem capturada no chat da corretora. Devolve o id da conversa.

    ⚠️ Esta função NÃO faz o agente falar. Quem faz o agente responder é o
    pipeline do webhook, e o `observer_tap` continua consumindo o evento
    enquanto o agente está desligado. Aqui só se grava o que aconteceu.

    Idempotente por `message_id`: a resposta enviada pelo dashboard vai ao
    WhatsApp e **volta** como `fromMe`. Sem esta guarda, cada resposta apareceria
    duas vezes no chat de quem acabou de escrevê-la.
    """
    telefone = _digitos(counterparty)
    empresa = str(company_id or "").strip()
    if not telefone or not empresa:
        return None

    if db is None:
        from app.core.database import get_supabase_client

        db = get_supabase_client()
    cliente = getattr(db, "client", db)

    def _trabalho() -> Optional[str]:
        from app.services.integration_service import integration_service

        # 1) dedup — esta mensagem já está no chat?
        if message_id:
            ja = (cliente.table("messages").select("id")
                  .eq("payload->>wa_message_id", message_id)
                  .limit(1).execute().data or [])
            if ja:
                return None

        # 2) o MESMO usuário e a MESMA chave que o pipeline do agente usa.
        #    ⚠️ A ordem é (phone, company_id, name) — conferida na assinatura
        #    real em `integration_service.py:370`. Trocar os dois primeiros
        #    criaria usuários com o id da empresa como telefone, em silêncio.
        usuario = integration_service.get_or_create_user(
            phone=telefone, company_id=empresa, name=nome)
        if not usuario:
            return None

        linhas = (cliente.table("conversations").select("id, status")
                  .eq("company_id", empresa).eq("user_id", usuario)
                  .eq("channel", "whatsapp").is_("agent_id", "null")
                  .limit(1).execute().data or [])
        if linhas:
            conversa_id = linhas[0]["id"]
        else:
            nova = (cliente.table("conversations").insert({
                "company_id": empresa, "channel": "whatsapp",
                "user_id": usuario, "agent_id": None,
                "user_phone": telefone,
                "user_name": nome or f"WhatsApp {telefone[-4:]}",
                "session_id": session_id_do_chat(empresa, telefone),
                # 'open', nunca HUMAN_REQUESTED: aquele estado significa "uma
                # pessoa PEDIU para assumir" e alimenta o vigia de handoff.
                # Uma conversa espelhada não pediu nada.
                "status": "open", "status_color": "green",
                "agent_name": "Espelho", "unread_count": 0,
                "last_message_at": quando_iso,
            }).execute().data or [])
            if not nova:
                return None
            conversa_id = nova[0]["id"]

        # 3) a mensagem
        cliente.table("messages").insert({
            "conversation_id": conversa_id,
            # É assim que o chat sabe de que lado desenhar o balão: o cliente
            # é 'user'; a corretora (pessoa ou agente) é 'assistant'.
            "role": "user" if direcao == "in" else "assistant",
            "content": texto or f"[{msg_type or 'mídia'}]",
            "type": msg_type or "text",
            # NOT NULL no schema — valores fixos e legíveis.
            "topic": "whatsapp", "extension": "espelho",
            "payload": {"wa_message_id": message_id, "origem": "espelho",
                        "direcao": direcao},
        }).execute()

        cliente.table("conversations").update({
            "last_message_preview": (texto or f"[{msg_type or 'mídia'}]")[:100],
            "last_message_at": quando_iso,
        }).eq("id", conversa_id).eq("company_id", empresa).execute()
        return conversa_id

    try:
        return await asyncio.to_thread(_trabalho)
    except Exception as erro:  # noqa: BLE001
        # O espelho é um bônus; a CAPTURA é a obrigação, e ela já aconteceu
        # antes desta chamada. Falhar aqui não pode perder conversa nenhuma.
        logger.warning("[ESPELHO] não consegui espelhar no chat (%s)", type(erro).__name__)
        return None


__all__ = [
    "deve_espelhar", "espelhar_no_chat", "session_id_do_chat",
    "JANELA_DA_LISTA_DIAS", "LIMITE_DE_RECENCIA_HORAS",
]
