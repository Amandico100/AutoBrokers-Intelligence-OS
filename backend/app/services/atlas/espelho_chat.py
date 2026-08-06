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
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Quantos dias de conversa aparecem NA LISTA do chat. Decisão do Founder,
# 06/08/2026. É o que a atendente vê ao abrir a tela.
JANELA_DA_LISTA_DIAS = 7

# Até onde uma mensagem ainda merece entrar no chat. Larga de propósito: não é
# para esconder conversa (disso cuida a lista), é para o HISTORY_SYNC de um
# pareamento novo não despejar meses de histórico de uma vez só.
LIMITE_DE_RECENCIA_HORAS = 720.0  # 30 dias

# Quanto tempo uma resposta enviada pelo dashboard ainda pode "voltar" pelo
# webhook como `fromMe`. Curto: é o tempo de ida ao WhatsApp e volta, não uma
# janela de conveniência. Longo demais engoliria a atendente repetindo a mesma
# frase de propósito.
_JANELA_DE_ECO_SEGUNDOS = 120.0

# Tipos que valem uma conversa mesmo sem uma palavra escrita.
_TIPOS_SEM_TEXTO = ("audio", "image", "document", "video", "sticker")


def _digitos(valor: Any) -> str:
    return "".join(ch for ch in str(valor or "") if ch.isdigit())


async def contar(motivo: str, quantos: int = 1) -> None:
    """Conta o que aconteceu com o espelho. Agregado, nunca conteúdo.

    🔴 EXISTE PORQUE EU FIQUEI CEGO, e o preço foi alto.

    📊 06/08/2026: a ponte estava no ar (`espelho_no_chat=True` no /health),
    13.200 mensagens entraram no acervo em três horas, e **zero** conversas
    apareceram no chat. O `try/except` que protege a captura engolia o motivo,
    e a única forma de saber o que falhou seria ler o log do contêiner — que o
    Founder não tem por que abrir.

    Sem contador, "não apareceu" tem cinco explicações e nenhuma forma de
    escolher entre elas. Com contador, a resposta cabe numa linha do /health.
    """
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        await r.hincrby("espelho:chat", motivo, int(quantos))
    except Exception:  # noqa: BLE001 — contador nunca derruba o que ele mede
        pass


async def diagnostico() -> dict:
    """O que o espelho fez desde que o processo subiu. Para o /health e para mim."""
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        bruto = await r.hgetall("espelho:chat")
        return {(k.decode() if isinstance(k, bytes) else str(k)):
                int(v.decode() if isinstance(v, bytes) else v)
                for k, v in (bruto or {}).items()}
    except Exception:  # noqa: BLE001
        return {}


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

    def _eco_do_dashboard(recentes: list) -> bool:
        """Esta mensagem é o eco da que o dashboard acabou de enviar?

        A resposta escrita no chat vai ao WhatsApp e **volta** pelo webhook como
        `fromMe`. Sem esta guarda, cada resposta apareceria duas vezes no chat de
        quem acabou de escrevê-la.

        O caminho óbvio seria comparar o `message_id` do WhatsApp. 📊 Ele não
        está disponível: `POST /api/webhook/send-message` devolve `{"status":
        "sent"}` porque `whatsapp_service.send_message` devolve um booleano.
        Fazer o id subir por essa cadeia mexeria num caminho quente usado por
        muita coisa — risco maior que o defeito.

        Então a comparação é: mesma conversa, mesmo texto, marcado como vindo do
        dashboard, nos últimos `_JANELA_DE_ECO_SEGUNDOS`. Restrita a mensagens
        `origem='dashboard'` de propósito — assim uma atendente que digita a
        mesma palavra duas vezes NO CELULAR não perde a segunda.
        """
        texto_limpo = str(texto or "").strip()
        if direcao != "out" or not texto_limpo:
            return False
        for m in recentes:
            # A marca de origem é lida EM PYTHON, sobre linhas já carregadas.
            # Filtrar `payload->>origem` no banco foi o que cegou o espelho —
            # ver o comentário grande em `_trabalho`.
            if (m.get("payload") or {}).get("origem") != "dashboard":
                continue
            if str(m.get("content") or "").strip() != texto_limpo:
                continue
            quando = m.get("created_at")
            if quando is None:
                return True
            try:
                nascida = datetime.fromisoformat(str(quando).replace("Z", "+00:00"))
            except (TypeError, ValueError):
                return True
            if nascida.tzinfo is None:
                nascida = nascida.replace(tzinfo=timezone.utc)
            idade = (datetime.now(timezone.utc) - nascida).total_seconds()
            if 0 <= idade <= _JANELA_DE_ECO_SEGUNDOS:
                return True
        return False

    def _trabalho() -> tuple:
        """Devolve ``(conversation_id, motivo)``. O motivo vai para o contador.

        🔴 A ORDEM MUDOU EM 06/08/2026, E O MOTIVO IMPORTA.

        A primeira versão deduplicava ANTES de resolver a conversa, com
        ``.eq("payload->>wa_message_id", ...)`` — um filtro JSON no PostgREST.
        📊 O resultado medido: 13.200 mensagens entraram no acervo em três
        horas e **nenhuma** conversa nasceu. A exceção morria no `try/except`
        que protege a captura, e de fora só dava para ver uma tela vazia.

        Agora a conversa é resolvida primeiro e a deduplicação acontece **em
        Python**, sobre as últimas mensagens daquela conversa. Uma leitura só,
        filtro simples, comparação no código. O que o banco faz mal, o Python
        faz bem — e o que o Python faz, eu consigo testar.
        """
        from app.services.integration_service import integration_service

        # 1) o MESMO usuário e a MESMA chave que o pipeline do agente usa.
        #    ⚠️ A ordem é (phone, company_id, name) — conferida na assinatura
        #    real em `integration_service.py:370`. Trocar os dois primeiros
        #    criaria usuários com o id da empresa como telefone, em silêncio.
        usuario = integration_service.get_or_create_user(
            phone=telefone, company_id=empresa, name=nome)
        if not usuario:
            return None, "sem_usuario"

        linhas = (cliente.table("conversations").select("id, status")
                  .eq("company_id", empresa).eq("user_id", usuario)
                  .eq("channel", "whatsapp").is_("agent_id", "null")
                  .limit(1).execute().data or [])
        nasceu = not linhas
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
                return None, "conversa_nao_criada"
            conversa_id = nova[0]["id"]

        # 2) as últimas mensagens desta conversa — UMA leitura, e é dela que
        #    saem as duas checagens: mensagem repetida e eco do dashboard.
        recentes = (cliente.table("messages")
                    .select("id, content, created_at, payload")
                    .eq("conversation_id", conversa_id)
                    .order("created_at", desc=True).limit(40).execute().data or [])

        # 3) esta mensagem já está no chat? (o WhatsApp reentrega em reconexão)
        if message_id:
            for m in recentes:
                if (m.get("payload") or {}).get("wa_message_id") == message_id:
                    return conversa_id, "ja_estava"

        # 4) é o eco da resposta que o próprio dashboard mandou? Então ela já
        #    está no chat, escrita por quem a digitou.
        if _eco_do_dashboard(recentes):
            return conversa_id, "eco_do_dashboard"

        # 5) a mensagem
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
        return conversa_id, ("conversa_nova" if nasceu else "mensagem_nova")

    try:
        conversa_id, motivo = await asyncio.to_thread(_trabalho)
        await contar(motivo)
        return conversa_id
    except Exception as erro:  # noqa: BLE001
        # O espelho é um bônus; a CAPTURA é a obrigação, e ela já aconteceu
        # antes desta chamada. Falhar aqui não pode perder conversa nenhuma.
        #
        # Mas o MOTIVO não se perde mais: vai para o contador, e do contador
        # para o /health. 📊 Foi por não ter isto que 13.200 mensagens entraram
        # e ninguém conseguiu dizer por que o chat continuava vazio.
        await contar(f"erro:{type(erro).__name__}")
        logger.warning("[ESPELHO] não consegui espelhar no chat (%s)", type(erro).__name__)
        return None


async def pausar_por_intervencao_humana(*, company_id: str, counterparty: str,
                                        quem: str = "Atendente pelo celular",
                                        db: Any = None) -> bool:
    """Uma pessoa respondeu: o agente cala NESTA conversa, e só nesta.

    Decisão do Founder, 06/08/2026:

        "Ele precisa parar a conversar com aquele cliente naquele número, mas
         ele deve continuar ligado e fazendo o trabalho dele nas outras
         conversas. Ele só para totalmente se o agente for desligado no botão."

    Por isso o UPDATE é por LINHA de conversa e **nunca** toca `agents.is_active`.
    Duas pessoas respondendo o mesmo cliente é o defeito que isto evita; um
    agente mudo na corretora inteira seria um defeito maior.

    `closed` fica de fora: conversa encerrada não ressuscita porque alguém
    mandou uma mensagem solta para o mesmo número.

    Devolve ``True`` quando alguma conversa foi pausada. Nunca levanta — se a
    pausa falhar, a captura e o espelho já aconteceram, e o pior caso é o
    agente responder junto uma vez, não o produto cair.
    """
    telefone = _digitos(counterparty)
    empresa = str(company_id or "").strip()
    if not telefone or not empresa:
        return False

    if db is None:
        from app.core.database import get_supabase_client

        db = get_supabase_client()
    cliente = getattr(db, "client", db)

    def _trabalho() -> bool:
        resposta = (cliente.table("conversations").update({
            "status": "HUMAN_REQUESTED",
            "claimed_by_name": quem,
            "claimed_at": _agora_iso(),
        }).eq("company_id", empresa).eq("channel", "whatsapp")
          .eq("user_phone", telefone).neq("status", "closed").execute())
        return bool(getattr(resposta, "data", None))

    try:
        pausou = await asyncio.to_thread(_trabalho)
        if pausou:
            # Sem o telefone no log: é a linha de trabalho de uma pessoa real
            # e a de um segurado (CLAUDE.md §13.3). Qual corretora basta.
            logger.info("[ESPELHO] intervenção humana pausou o agente numa conversa de %s",
                        empresa)
        return pausou
    except Exception as erro:  # noqa: BLE001
        logger.warning("[ESPELHO] não consegui pausar a conversa (%s)", type(erro).__name__)
        return False


async def trazer_conversas_ja_capturadas(
    *, company_id: str, dias: int = 2, limite: int = 3000, db: Any = None
) -> dict:
    """Leva ao chat o que o Observador JÁ capturou. Uma vez, sob demanda.

    POR QUE ISTO EXISTE
    ===================
    A ponte só age quando chega mensagem nova. 📊 Em 06/08/2026, no dia em que
    ela subiu, a AutoFleet tinha **32.128 mensagens capturadas em 7 dias** e o
    chat abriu vazio — porque a última mensagem tinha entrado 22 minutos antes
    do deploy. A corretora estaria olhando uma tela vazia sobre um acervo cheio,
    esperando um cliente escrever.

    Não é motor paralelo: é a MESMA `espelhar_no_chat`, chamada em lote a partir
    do acervo em vez do webhook. E é idempotente pelo `message_id`, então rodar
    duas vezes não duplica nada.

    `dias=2` por padrão porque a mesa de trabalho é do que está aberto agora;
    quem quiser a semana inteira pede `dias=7`. `limite` existe para a chamada
    não virar uma varredura de 32 mil linhas sem ninguém ter pedido isso.
    """
    empresa = str(company_id or "").strip()
    if not empresa:
        return {"ok": False, "motivo": "company_id_obrigatorio"}

    if db is None:
        from app.core.database import get_supabase_client

        db = get_supabase_client()
    cliente = getattr(db, "client", db)

    desde = (datetime.now(timezone.utc) - timedelta(days=max(1, int(dias)))).isoformat()

    def _ler() -> list:
        return (cliente.table("attendance_transcripts")
                .select("counterparty, direction, msg_type, text, message_id, wa_timestamp")
                .eq("company_id", empresa)
                .gte("created_at", desde)
                # Mais antigas primeiro: o chat precisa da ordem da conversa,
                # não da ordem da consulta.
                .order("wa_timestamp", desc=False)
                .limit(max(1, int(limite))).execute().data or [])

    try:
        linhas = await asyncio.to_thread(_ler)
    except Exception as erro:  # noqa: BLE001
        logger.warning("[ESPELHO] backfill não leu o acervo (%s)", type(erro).__name__)
        return {"ok": False, "motivo": type(erro).__name__}

    levadas = 0
    for linha in linhas:
        quando = str(linha.get("wa_timestamp") or "") or _agora_iso()
        conversa = await espelhar_no_chat(
            company_id=empresa,
            counterparty=str(linha.get("counterparty") or ""),
            texto=str(linha.get("text") or ""),
            msg_type=str(linha.get("msg_type") or "text"),
            direcao=str(linha.get("direction") or "in"),
            message_id=str(linha.get("message_id") or ""),
            quando_iso=quando, db=db)
        if conversa:
            levadas += 1

    logger.info("[ESPELHO] backfill de %s: %s linhas lidas, %s levadas ao chat",
                empresa, len(linhas), levadas)
    return {"ok": True, "lidas": len(linhas), "levadas": levadas, "dias": dias}


async def sincronizar_chats() -> dict:
    """Varre as corretoras ativas e leva ao chat o que ainda não chegou lá.

    POR QUE ISTO É AUTOMÁTICO, e não um comando
    ============================================
    O Founder, 06/08/2026: *"eu não sei como fazer isso. Onde é /app? Também
    não quero ter todo esse trabalho. Eu só quero as coisas funcionando."*

    Ele está certo, e a versão anterior — um comando de console — era um
    conserto que exigia da pessoa errada o trabalho errado. Um produto que
    precisa de alguém abrir terminal para mostrar as conversas do dia não está
    pronto; está esperando ajuda.

    Roda no agendador que já existe (`buffer_processor`), junto do heartbeat.
    Nenhum motor novo (CLAUDE.md §5).

    É barato porque é incremental: a dedup por `message_id` faz a segunda
    passada não escrever nada. E é a rede que pega o que a ponte ao vivo perdeu
    — mensagem que chegou durante um deploy, erro momentâneo do banco, ou o
    acervo que já estava lá antes de a ponte existir.
    """
    from app.core.database import get_supabase_client

    db = get_supabase_client()
    cliente = getattr(db, "client", db)

    def _corretoras() -> list:
        return (cliente.table("integrations").select("company_id")
                .eq("provider", "evolution-go").eq("is_active", True)
                .limit(200).execute().data or [])

    try:
        linhas = await asyncio.to_thread(_corretoras)
    except Exception as erro:  # noqa: BLE001
        logger.warning("[ESPELHO] sync não leu as corretoras (%s)", type(erro).__name__)
        return {"ok": False, "motivo": type(erro).__name__}

    vistas: set = set()
    resumo = {"ok": True, "corretoras": 0, "levadas": 0}
    for linha in linhas:
        empresa = str(linha.get("company_id") or "").strip()
        if not empresa or empresa in vistas:
            continue
        vistas.add(empresa)
        resumo["corretoras"] += 1
        # Janela curta: a passada é frequente, e o que interessa é o que a
        # ponte ao vivo pode ter perdido agora há pouco. O acervo antigo já
        # entrou na primeira passada depois do deploy.
        r = await trazer_conversas_ja_capturadas(
            company_id=empresa, dias=int(os.getenv("ESPELHO_SYNC_DIAS", "2")),
            limite=int(os.getenv("ESPELHO_SYNC_LIMITE", "1500")), db=db)
        resumo["levadas"] += int(r.get("levadas") or 0)

    logger.info("[ESPELHO] sync: %s corretoras, %s mensagens levadas ao chat",
                resumo["corretoras"], resumo["levadas"])
    return resumo


__all__ = [
    "deve_espelhar", "espelhar_no_chat", "session_id_do_chat",
    "pausar_por_intervencao_humana", "trazer_conversas_ja_capturadas",
    "sincronizar_chats", "contar", "diagnostico",
    "JANELA_DA_LISTA_DIAS", "LIMITE_DE_RECENCIA_HORAS",
]
