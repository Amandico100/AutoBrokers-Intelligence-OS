"""Roteador de despacho (SPEC-017 P5/P6) — a espinha do acionamento real.

Quando um dispatch está ATIVO, as mensagens que chegam DO NÚMERO DA SEGURADORA
no WhatsApp da corretora não são "cliente": são a URA/especialista respondendo.
Este módulo:
- guarda a sessão de dispatch ativa por (company_id, telefone da seguradora)
  em Redis (fallback memória p/ testes);
- intercepta o inbound ANTES do agente: alimenta handle_insurer_message;
- envia as respostas de URA pela MESMA integração da corretora (gate S17-6:
  só com INSURER_DISPATCH_LIVE ligado);
- ao capturar protocolo/agendamento, envia o resumo humanizado AO CLIENTE
  e encerra a sessão.

Fail-safe: needs_human → sessão pausa e marca handoff (nunca responde às cegas).

SPEC-063 Bloco E — o Redis deixou de ser a ÚNICA verdade
--------------------------------------------------------
Até 03/08/2026 o estado do acionamento existia só na chave acima. Um restart do
Redis, ou seis horas de silêncio, perdiam um acionamento EM VOO — e não havia
reconciliação nenhuma: o segurado com o guincho a caminho ficava órfão e ninguém
percebia. O Vigia (`dispatch_watchdog`) não cobre isso: ele varre as sessões que
ESTÃO no Redis, então é justamente cego para a que sumiu de lá.

Agora cada transição de fase vira checkpoint durável num **Work Run** (SPEC-055,
o mesmo motor de todo o resto — nenhuma tabela nova, nenhum executor paralelo).
O Redis continua sendo o cache quente; o que ele não é mais é a única cópia.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import unicodedata
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Optional

from app.services.insurer_dispatch_service import (
    build_handoff_dossier,
    client_summary_from_capture,
    guard_human_phase_reply,
    handle_insurer_message,
    new_dispatch_session,
    reply_human_phase,
    start_dispatch,
)

logger = logging.getLogger(__name__)


def _motor():
    """O vocabulário de fases do motor, carregado sob demanda.

    Import tardio de propósito. Este módulo é importado por telas, tarefas e
    testes que **dublam** o motor de acionamento (`sys.modules[...] = stub`), e
    um import de topo obrigaria todo dublê a conhecer cada nome novo que o
    espelho durável usa — quebrando quem não tem nada a ver com o assunto.
    Quando qualquer função daqui roda, o núcleo já está carregado: custo zero."""
    from app.services import insurer_dispatch_service as motor

    return motor


_TTL_SECONDS = 6 * 3600
_MONITOR_TTL_SECONDS = 24 * 3600  # updates da seguradora chegam por até ~1 dia

# Quanto tempo o Vigia deve RESPEITAR um silêncio deliberado.
#
# 📊 Medido em 05/08/2026 no acervo, isolando encerramentos por inatividade: o
# menor silêncio que a Allianz tolerou foi de **103 segundos**. Sessenta cabe
# folgado embaixo disso, e é o dobro dos 30s em que o Vigia hoje acorda.
#
# O limite existe porque silêncio sem teto vira a nova forma de travar: o
# Sentinela precisa poder voltar se a seguradora seguir falando.
_SILENCIO_S = 60
# Teto da TELA montada a partir da rajada (ver `_tela_do_turno`). Generoso de
# propósito: o corte é a exceção, não o caminho.
_TETO_DA_TELA = 4000
_memory_store: Dict[str, str] = {}  # fallback p/ testes offline

# Pós-protocolo: a seguradora manda updates espontâneos (HDI: "prestador a
# caminho, faltam 30 min"; "agendada para 29/01 às 09:30"). Repassar AO CLIENTE
# em tempo real = acompanhamento de verdade. Pesquisas/avaliações: ignorar.
_MONITOR_FORWARD_RE = (
    r"prestador(?:.{0,80})(?:a caminho|encontrad|realizar[áa]|chegada)|encontramos o prestador|"
    r"agendad[ao] para|previs[ãa]o de chegada|faltam aproximadamente|procurando um prestador|"
    r"foi aberta com sucesso|est[áa] a caminho|"
    # MÁ NOTÍCIA TAMBÉM É NOTÍCIA — e é a que mais urge.
    #
    # 📊 Até 03/08 a lista branca só deixava passar o que dava certo. Uma URA
    # que dissesse "não encontramos prestador na sua região" ou "serviço
    # cancelado" era **silenciosamente engolida**: o segurado continuava
    # esperando um guincho que não vinha, e a corretora não sabia de nada.
    #
    # Repassar o problema é o que separa acompanhar de torcer. Quem está com o
    # carro parado no acostamento precisa saber que precisa de outra saída — e
    # precisa saber ANTES, não quando desistir de esperar.
    r"n[ãa]o (?:foi poss[íi]vel|conseguimos|encontramos|localizamos)|"
    r"sem prestador|nenhum prestador|indispon[íi]vel na (?:sua )?regi[ãa]o|"
    r"cancelad[ao]|servi[çc]o negad|n[ãa]o (?:h[áa]|possui) cobertura|"
    r"fora da [áa]rea de atendimento|houve um problema|"
    r"atraso|remarcad[ao]|reagendad[ao]"
)
_MONITOR_IGNORE_RE = (
    r"pesquisa|avalie|sua opini[ãa]o|recomendaria|grau de satisfa[çc][ãa]o|nota"
)


def _norm(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def _tela_do_turno(session: Dict[str, Any], texto_atual: str) -> str:
    """A TELA INTEIRA — não o último pedaço dela.

    A URA não manda uma mensagem: manda uma RAJADA. O aviso vem numa bolha, o
    menu na seguinte, a pergunta na terceira. Quem lê no celular vê uma tela só,
    e é sobre a tela inteira que se decide.

    📊 Medido em 05/08/2026 sobre o tráfego real das seguradoras: em 34,1% dos
    turnos chegam 2+ mensagens, e nesses turnos a pergunta está na ÚLTIMA
    mensagem em 68,1% das vezes. Antes disto, o roteador era chamado uma vez por
    mensagem e o modelo respondia a primeira bolha — quase sempre um "aguarde" —
    e já tinha falado quando o menu de verdade chegou. Duas respostas para uma
    pergunta, e a primeira sobre a tela errada.

    A fonte é `pending_insurer_messages`, não a rajada crua do webhook: é a lista
    do que a seguradora disse e nós ainda NÃO respondemos. `reply_human_phase` a
    zera a cada resposta aceita, então ela é exatamente o turno em aberto —
    inclusive quando o turno anterior terminou em silêncio deliberado, e aí o
    "aguarde" calado entra junto com o menu que veio depois. É o certo: era uma
    tela só desde o começo.

    Se estourar o teto, corta pela CABEÇA e por mensagens inteiras. Cortar pelo
    fim jogaria fora justamente a pergunta.
    """
    pendentes = [
        " ".join(str(m).split())
        for m in (session.get("pending_insurer_messages") or [])
        if str(m or "").strip()
    ]
    if not pendentes:
        return str(texto_atual or "").strip()
    while len(pendentes) > 1 and len("\n".join(pendentes)) > _TETO_DA_TELA:
        pendentes.pop(0)
    return "\n".join(pendentes)[-_TETO_DA_TELA:]


async def _support_alert_seguro(company_id: str, session: Dict[str, Any], resumo: str) -> None:
    """O segurado não recebeu o protocolo — alguém tem de saber HOJE.

    Não existe segunda chance automática aqui: a URA já encerrou, o serviço está
    aberto, e o único que não sabe disso é justamente quem vai receber o
    prestador. Um humano resolve isso em trinta segundos — se souber.
    """
    # 🔴 ESTE BLOCO NUNCA RODOU, e ninguém soube — 06/08/2026.
    #
    # Ele importava `integration_service` e `whatsapp_service` como se fossem
    # objetos de módulo. Os dois são FÁBRICAS (`get_integration_service`,
    # `get_whatsapp_service`), e os dois imports levantavam ImportError — dentro
    # de um `except Exception` que escrevia "alerta não saiu" e seguia.
    #
    # Ou seja: toda vez que o segurado NÃO recebia o protocolo, o aviso ao
    # humano também não saía, e o log dizia isso de um jeito que parecia falha
    # de rede. Foi encontrado por varredura depois que o MESMO defeito parou o
    # espelho do chat — ver `test_todo_import_aponta_para_algo_que_existe`.
    #
    # `resolver_destino_de_suporte` também estava no lugar errado: ela é uma
    # função DESTE módulo (linha ~953), não um método do integration_service.
    try:
        from app.core.database import get_supabase_client
        from app.services.integration_service import get_integration_service
        from app.services.whatsapp_service import get_whatsapp_service

        destino = await resolver_destino_de_suporte(company_id)
        if not destino:
            return
        alvo = destino.get("number") if isinstance(destino, dict) else destino
        if not alvo:
            return

        servico = get_integration_service(get_supabase_client().client)
        integ = servico.get_platform_whatsapp_integration(company_id)
        if not integ:
            return
        aviso = ("⚠️ O aviso de protocolo NÃO chegou ao segurado.\n"
                 f"Caso: {session.get('case_id')}\n"
                 f"Telefone: {session.get('client_phone')}\n\n{resumo}")
        get_whatsapp_service().send_message(str(alvo), aviso, integ)
    except Exception:  # noqa: BLE001
        logger.warning("[DISPATCH ROUTER] alerta de falha de aviso nao saiu")


# 🔴 A régua que o prompt nunca contou ao modelo.
#
# `guard_human_phase_reply` reprova acima de 400 caracteres
# (`insurer_dispatch_service.py:1843`). O prompt do cérebro nunca mencionou
# esse teto. 📊 Em 18/08 o modelo devolveu 459 e 297 tokens de prosa numa tela
# de menu de dois botões — resposta CERTA no conteúdo, reprovada na forma, por
# uma regra que ele não tinha como conhecer.
#
# Régua secreta não é rigor: é armadilha. Esta frase entra na retentativa.
_PEDIDO_DE_ENCURTAR = (
    "ATENCAO: sua resposta anterior foi RECUSADA por ser longa demais. "
    "A URA espera o NUMERO da opcao ou o rotulo curto do botao. "
    "Responda com no maximo 200 caracteres. Nao explique sua escolha, "
    "nao cumprimente, nao justifique — so a resposta."
)


async def _registrar_fala_ao_cliente(company_id: str, client_phone: str,
                                     kind: str, resumo: str) -> None:
    """Deixa RASTRO de tudo que o motor diz ao segurado.

    📊 Até 03/08 o motor falava com o cliente e **ninguém registrava**. O agente
    de atendimento não tinha como saber que o protocolo já tinha sido entregue —
    e podia prometer "já te retorno com o número" que já fora enviado dois
    minutos antes, pelo mesmo WhatsApp.

    O lugar certo já existia: `platform_sends` é exatamente a tabela que alimenta
    a nota de contexto do atendente (`context_note_for`). O motor é que não
    escrevia nela.

    Best-effort de propósito: registro que falha não pode impedir o segurado de
    receber a notícia. Perder o rastro é ruim; perder a mensagem é pior.
    """
    if not client_phone:
        return
    try:
        from app.services.platform_outbound import record_platform_send

        await record_platform_send(company_id, client_phone, kind, resumo[:180])
    except Exception:  # noqa: BLE001
        logger.warning("[DISPATCH ROUTER] rastro do aviso ao cliente falhou")


def _key(company_id: str, insurer_phone: str) -> str:
    digits = "".join(ch for ch in str(insurer_phone or "") if ch.isdigit())
    return f"dispatch:active:{company_id}:{digits}"


async def _redis():
    try:
        from app.core.redis import get_async_redis_client

        return await get_async_redis_client()
    except Exception:  # noqa: BLE001 — testes offline
        return None


async def _gravar_no_redis(company_id: str, insurer_phone: str, session: Dict[str, Any],
                           ttl: Optional[int] = None) -> None:
    """Escreve a sessão no cache quente. Só isso — nada de espelho nem banco.

    Existe separado de `save_active_dispatch` porque a restauração precisa
    devolver a sessão ao Redis SEM disparar de novo o espelho e o checkpoint que
    a produziram (seria gravar duas vezes o mesmo passado)."""
    key = _key(company_id, insurer_phone)
    if ttl is None:
        ttl = _MONITOR_TTL_SECONDS if str(session.get("state") or "") == "monitoring" else _TTL_SECONDS
    payload = json.dumps(session, ensure_ascii=False, default=str)
    redis = await _redis()
    if redis is not None:
        await redis.set(key, payload, ex=max(60, int(ttl)))
    else:
        _memory_store[key] = payload


async def _ler_do_redis(company_id: str, insurer_phone: str) -> Optional[Dict[str, Any]]:
    key = _key(company_id, insurer_phone)
    redis = await _redis()
    raw = await redis.get(key) if redis is not None else _memory_store.get(key)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:  # noqa: BLE001
        return None


async def save_active_dispatch(company_id: str, insurer_phone: str, session: Dict[str, Any]) -> None:
    # ESPELHO (SPEC-034): todo transcript novo vai para o banco/dashboard antes
    # de persistir no Redis — ponto único de captura. Nunca bloqueia o motor.
    try:
        from app.services.dispatch_mirror import mirror_session

        await mirror_session(company_id, insurer_phone, session)
    except Exception:  # noqa: BLE001 — espelho é best-effort
        pass
    # CHECKPOINT DURÁVEL (SPEC-063 E): a fase vai para o Work Run ANTES do Redis.
    # Ordem importa: se o processo morrer entre as duas escritas, o pior caso é
    # um checkpoint mais novo que o cache — recuperável. O inverso (cache mais
    # novo que a verdade durável) é justamente o defeito que estamos matando.
    await registrar_checkpoint(company_id, insurer_phone, session)
    await _gravar_no_redis(company_id, insurer_phone, session)


async def load_active_dispatch(company_id: str, insurer_phone: str) -> Optional[Dict[str, Any]]:
    sessao = await _ler_do_redis(company_id, insurer_phone)
    if sessao is None:
        # Cache vazio é o SINTOMA do defeito desta SPEC. Uma vez por processo,
        # isso agenda a varredura que compara a verdade durável com o cache.
        _agendar_reconciliacao_uma_vez()
    return sessao


async def clear_active_dispatch(company_id: str, insurer_phone: str) -> None:
    # Ler antes de apagar: é a última chance de saber QUAL Work Run esta chave
    # representava. Sem isto, toda sessão encerrada de propósito (supersede,
    # retomada automática, seguradora que derrubou a conversa) deixaria um run
    # eternamente "em voo" — o defeito do `corridor_runs`, 📊 50 execuções
    # abandonadas em `active`, hoje no schema `graveyard`.
    sessao = await _ler_do_redis(company_id, insurer_phone)
    key = _key(company_id, insurer_phone)
    redis = await _redis()
    if redis is not None:
        await redis.delete(key)
    else:
        _memory_store.pop(key, None)
    if sessao and sessao.get("work_run_id"):
        await _encerrar_work_run(company_id, sessao, motivo="sessão encerrada e liberada")


# ---------------------------------------------------------------------------
# ESPELHO DURÁVEL DO ACIONAMENTO — SPEC-063 Bloco E sobre a SPEC-055
# ---------------------------------------------------------------------------
#
# POR QUE UM WORK RUN, E NÃO UMA TABELA DE ESTADO NOVA
# ----------------------------------------------------
# Porque a tabela nova já foi tentada e morreu: 📊 `corridor_runs` tem 50
# execuções abandonadas, todas em `active`, e hoje mora no schema `graveyard`.
# CLAUDE.md §5 proíbe criar executor em paralelo ao existente, e a SPEC-055 já
# define Work Run como a execução universal — com etapa, checkpoint, linha do
# tempo e retomada. O acionamento é uma execução. Ele cabe lá inteiro.
#
# POR QUE NÃO PASSA PELO `work_run_create`
# -----------------------------------------
# O RPC grava, na mesma transação, uma linha em `work_queue_outbox`. O
# OutboxDispatcher publica no Redis Stream, o Smith Worker consome e chama
# `resolver_workflow("acionamento.seguradora")` — que devolve `None`, porque
# **este trabalho não é executado pelo worker**: quem o executa é o inbound do
# WhatsApp, mensagem por mensagem, ao longo de horas. O worker então marcaria o
# run como `failed` com "workflow_desconhecido" enquanto o acionamento está VIVO.
# O espelho durável passaria a mentir — que é pior do que não existir.
#
# Por isso o run nasce direto na tabela, com `runtime_kind='acionamento'`: mesma
# tabela, mesmo enum de status, mesma linha do tempo em `work_events`, mesmos
# checkpoints em `work_steps`. O que ele não tem é fila — de propósito.
#
# E não há conflito com o varredor de órfãos da SPEC-055: `recuperar_orfaos()`
# filtra `lease_expires_at < agora`, e um run sem lease tem esse campo NULO —
# PostgREST não devolve NULL num `.lt()`. O Smith Worker nunca toca nestes runs.

WORKFLOW_ACIONAMENTO = "acionamento.seguradora"
RUNTIME_ACIONAMENTO = "acionamento"

_STATUS_EM_VOO_WORK_RUN = ("draft", "queued", "planning", "running",
                           "waiting_approval", "waiting_input", "paused",
                           "retry_scheduled", "cancelling")
_ERRO_ORFAO = "acionamento_orfao"
_PRAZO_EXPIRAR_ORFAO_DIAS = 7
_reconciliacao_agendada = False


async def _db():
    """Cliente durável. `None` quando offline (teste) — nunca derruba o motor."""
    try:
        from app.core.database import create_async_supabase_client

        return await create_async_supabase_client()
    except Exception as e:  # noqa: BLE001
        logger.error("[ACIONAMENTO DURAVEL] banco indisponivel (%s) — o acionamento "
                     "segue, mas SEM espelho durável nesta escrita", type(e).__name__)
        return None


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _idade_segundos(ts: Any) -> float:
    """Segundos desde `ts`. `-1` quando ilegível — quem chama decide o que fazer
    com o desconhecido (aqui: tratar como velho, nunca como novo)."""
    try:
        quando = datetime.fromisoformat(str(ts or "").replace("Z", "+00:00"))
        if quando.tzinfo is None:
            quando = quando.replace(tzinfo=timezone.utc)
        return (_agora() - quando).total_seconds()
    except Exception:  # noqa: BLE001
        return -1.0


def _chave_idempotente(insurer_digits: str, session: Dict[str, Any]) -> str:
    """Um run por SESSÃO de acionamento, não por caso.

    O `case_id` sozinho fundiria coisas diferentes: a retomada automática depois
    de a URA derrubar a conversa abre uma SEGUNDA tentativa, e um guincho novo
    para o mesmo caso semanas depois é outro trabalho. `created_at` da sessão
    separa as três sem inventar contador nenhum."""
    caso = str(session.get("case_id") or "sem-caso")
    nascimento = str(session.get("created_at") or "")
    return f"acionamento:{insurer_digits}:{caso}:{nascimento}"[:250]


def _progresso_da_fase(fase: str, status: str) -> int:
    if status == "completed":
        return 100
    return max(5, min(95, _motor().ordem_da_fase(fase) * 15))


async def _garantir_work_run(db, company_id: str, insurer_digits: str,
                             session: Dict[str, Any]) -> Optional[str]:
    """O Work Run desta sessão — reaproveitado, nunca duplicado."""
    if session.get("work_run_id"):
        return str(session["work_run_id"])

    idem = _chave_idempotente(insurer_digits, session)
    achado = await (db.client.table("work_runs").select("id")
                    .eq("company_id", company_id).eq("idempotency_key", idem)
                    .limit(1).execute())
    if achado.data:
        session["work_run_id"] = str(achado.data[0]["id"])
        return session["work_run_id"]

    fase = str(session.get("state") or "preparing")
    status = _motor().status_duravel_da_fase(fase)
    run_id = str(uuid.uuid4())
    entrada = {
        "company_id": str(company_id),
        "case_id": str(session.get("case_id") or ""),
        "insurer_phone": insurer_digits,
        "playbook_ref": str(session.get("playbook_ref") or ""),
        "subservice": str(session.get("subservice") or ""),
    }
    agora = _agora().isoformat()
    linha = {
        "id": run_id,
        "company_id": str(company_id),
        "source_type": "chat",
        "source_id": str(session.get("case_id") or "")[:180] or None,
        "outcome_type": "acionamento_assistencia",
        "outcome_title": (f"Acionamento {str(session.get('playbook_ref') or 'seguradora')}"
                          f" — {str(session.get('subservice') or 'assistência')}")[:180],
        "status": status,
        # Alto por definição: o outro lado é a seguradora de verdade, e com
        # INSURER_DISPATCH_LIVE aberto cada passo sai no WhatsApp dela.
        "risk_level": "high",
        "runtime_kind": RUNTIME_ACIONAMENTO,
        "workflow_key": WORKFLOW_ACIONAMENTO,
        "workflow_version": "1.0.0",
        "thread_id": f"work:{company_id}:{run_id}",
        "input_payload": entrada,
        "input_fingerprint": hashlib.sha256(
            json.dumps(entrada, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
        "idempotency_key": idem,
        "current_step_key": fase,
        "progress_percent": _progresso_da_fase(fase, status),
        "queued_at": agora,
        "started_at": agora,
    }
    await db.client.table("work_runs").insert(linha).execute()
    session["work_run_id"] = run_id
    await _evento(db, company_id, run_id, "run.created",
                  "Acionamento aberto na seguradora — a partir daqui cada fase "
                  "fica gravada, mesmo se o cache cair.",
                  payload={"fase": fase, "case_id": entrada["case_id"]})
    logger.info("[ACIONAMENTO DURAVEL] run %s criado para o caso %s",
                run_id, entrada["case_id"] or "?")
    return run_id


async def _evento(db, company_id: str, run_id: str, tipo: str, mensagem: str, *,
                  severidade: str = "info", payload: Optional[Dict[str, Any]] = None) -> None:
    """Linha do tempo do Work Run. Sem dado do segurado: quem guarda o conteúdo
    da conversa é o Espelho, e `payload_redacted` tem esse nome por um motivo."""
    try:
        await db.client.table("work_events").insert({
            "company_id": str(company_id),
            "work_run_id": run_id,
            "event_type": tipo,
            "actor_type": "system",
            "severity": severidade,
            "message_human": str(mensagem)[:1000],
            "payload_redacted": payload or {},
        }).execute()
    except Exception as e:  # noqa: BLE001
        logger.warning("[ACIONAMENTO DURAVEL] evento '%s' nao registrado: %s",
                       tipo, type(e).__name__)


async def registrar_checkpoint(company_id: str, insurer_phone: str,
                               session: Dict[str, Any]) -> Optional[str]:
    """Grava a fase atual do acionamento como etapa durável do Work Run.

    Uma etapa POR FASE (`uq_work_steps_run_key` garante isso), atualizada a cada
    save. A conversa oscila — `ura → human_phase → ura` acontece toda hora —
    então a fase não serve de ordem cronológica: o mais recente é o de
    `finished_at` maior, e é assim que a restauração acha o retrato certo.
    """
    digits = _digits(insurer_phone)
    fase = str(session.get("state") or "")
    if not fase or not company_id:
        return None

    db = await _db()
    if db is None:
        return None

    try:
        run_id = await _garantir_work_run(db, company_id, digits, session)
        if not run_id:
            return None

        status = _motor().status_duravel_da_fase(fase)
        agora = _agora().isoformat()
        retrato = _motor().snapshot_duravel(session)

        etapa = {
            "work_run_id": run_id,
            "company_id": str(company_id),
            "step_key": fase,
            "ordinal": _motor().ordem_da_fase(fase),
            "name": f"Fase do acionamento: {fase}",
            "step_type": "dispatch_phase",
            "status": "succeeded" if fase not in _motor().FASES_ENCERRADAS else "waiting_input",
            "risk_level": "high",
            "output_summary": retrato,
            "idempotency_key": f"{company_id}:{run_id}:{fase}"[:250],
            "finished_at": agora,
            "updated_at": agora,
        }
        existente = await (db.client.table("work_steps").select("id, attempt_count")
                           .eq("work_run_id", run_id).eq("step_key", fase)
                           .limit(1).execute())
        if existente.data:
            etapa["attempt_count"] = int(existente.data[0].get("attempt_count") or 0) + 1
            await (db.client.table("work_steps").update(etapa)
                   .eq("id", existente.data[0]["id"]).execute())
        else:
            etapa["attempt_count"] = 1
            etapa["started_at"] = agora
            await db.client.table("work_steps").insert(etapa).execute()

        campos: Dict[str, Any] = {
            "status": status,
            "current_step_key": fase,
            "progress_percent": _progresso_da_fase(fase, status),
            "updated_at": agora,
        }
        if status == "completed":
            campos["finished_at"] = agora
            campos["result_summary"] = (
                "Simulação completa: o fluxo rodou até a confirmação final e foi "
                "CANCELADO antes de abrir o serviço (modo teste)."
                if fase == "test_aborted" else "Acionamento concluído.")
        if fase == "needs_human":
            campos["error_code"] = f"needs_human:{str(session.get('reason') or '')}"[:180]
            campos["error_message"] = ("O acionamento precisa de uma pessoa da corretora "
                                       "para continuar.")
        await db.client.table("work_runs").update(campos).eq("id", run_id).execute()

        if fase != str(session.get("_checkpoint_fase") or ""):
            await _evento(db, company_id, run_id, "step.completed",
                          f"Acionamento agora em '{fase}'.",
                          severidade="warning" if fase == "needs_human" else "info",
                          payload={"fase": fase, "motivo": str(session.get("reason") or "")})
            session["_checkpoint_fase"] = fase
        return run_id
    except Exception as e:  # noqa: BLE001
        # ERRO, não warning: falhar aqui devolve o produto ao defeito que esta
        # SPEC existe para matar — o acionamento voltando a morar só no Redis.
        logger.error("[ACIONAMENTO DURAVEL] checkpoint da fase '%s' NAO gravado (%s) — "
                     "esta sessao esta sem espelho durável", fase, type(e).__name__)
        return None


async def _encerrar_work_run(company_id: str, session: Dict[str, Any], *,
                             motivo: str, status: Optional[str] = None) -> None:
    """Fecha o run desta sessão. Um run que ninguém fecha é um órfão futuro."""
    run_id = str(session.get("work_run_id") or "")
    if not run_id:
        return
    db = await _db()
    if db is None:
        return
    fase = str(session.get("state") or "")
    # `encaminhado` é DESFECHO DE SUCESSO (P-46): a seguradora não abre chamado
    # por este canal, e o segurado recebeu o formulário/orientação. Fora desta
    # lista, um encaminhamento entregue seria gravado como `cancelled`.
    final = status or ("completed" if fase in ("captured", "monitoring",
                                               "test_aborted", "encaminhado")
                       else "cancelled")
    try:
        agora = _agora().isoformat()
        await (db.client.table("work_runs").update({
            "status": final,
            "finished_at": agora,
            "updated_at": agora,
            "progress_percent": 100 if final == "completed" else _progresso_da_fase(fase, final),
            "result_summary": f"{motivo} (última fase: {fase or 'desconhecida'})"[:400],
        }).eq("id", run_id).execute())
        await _evento(db, company_id, run_id,
                      "run.succeeded" if final == "completed" else "run.cancelled",
                      motivo, payload={"fase": fase})
    except Exception as e:  # noqa: BLE001
        logger.error("[ACIONAMENTO DURAVEL] run %s nao foi encerrado (%s)",
                     run_id, type(e).__name__)


def _agendar_reconciliacao_uma_vez() -> None:
    """Dispara a varredura de boot, uma vez por processo, fora do caminho quente."""
    global _reconciliacao_agendada
    if _reconciliacao_agendada:
        return
    try:
        import asyncio

        asyncio.get_running_loop().create_task(reconciliar_acionamentos_orfaos())
        _reconciliacao_agendada = True
    except Exception:  # noqa: BLE001 — sem loop rodando: tenta na próxima
        pass


async def _ultimo_retrato(db, run_id: str, fase: str) -> Optional[Dict[str, Any]]:
    """O checkpoint mais recente do run. Preferimos o da fase que o run declara;
    sem ele, o de `finished_at` maior — porque a fase oscila e a ordem numérica
    não é cronológica."""
    try:
        if fase:
            r = await (db.client.table("work_steps").select("output_summary, finished_at")
                       .eq("work_run_id", run_id).eq("step_key", fase).limit(1).execute())
            if r.data and (r.data[0].get("output_summary") or {}):
                return r.data[0]
        r2 = await (db.client.table("work_steps").select("output_summary, finished_at")
                    .eq("work_run_id", run_id).order("finished_at", desc=True)
                    .limit(1).execute())
        return r2.data[0] if r2.data else None
    except Exception as e:  # noqa: BLE001
        logger.error("[RECONCILIACAO] retrato do run %s ilegivel (%s)", run_id, type(e).__name__)
        return None


async def reconciliar_acionamentos_orfaos(limite: int = 50) -> Dict[str, int]:
    """Compara a verdade durável com o cache e não deixa acionamento órfão calado.

    Roda no boot (agendada no primeiro cache-miss do processo) e pode ser
    chamada por qualquer laço de manutenção. É idempotente: um órfão já
    sinalizado não vira alarme de novo.

    O QUE ELA RESTAURA, E O QUE ELA DELIBERADAMENTE NÃO RESTAURA
    ------------------------------------------------------------
    Restaura `monitoring`. Nessa fase o motor **nunca fala com a seguradora** —
    o roteador só repassa updates ao segurado e ignora pesquisa de satisfação.
    Devolver a sessão ao cache é puro ganho: é o caso do guincho a caminho.

    NÃO restaura `ura` nem `human_phase`. Ali a sessão VOLTARIA A RESPONDER à
    seguradora, e com `INSURER_DISPATCH_LIVE` aberto isso é mensagem real num
    atendimento que já andou sem nós — do lado de lá pode ter havido timeout,
    encerramento ou outro atendente. Ressuscitar uma conversa dessas é o bug
    "sessão zumbi" de 12/07 com outro nome. Essas viram `needs_human` com motivo
    escrito e uma pessoa assume. Menos automação; nunca automação errada.
    """
    resumo = {"vistos": 0, "vivos": 0, "restaurados": 0, "orfaos": 0,
              "encerrados": 0, "expirados": 0, "ja_sinalizados": 0}
    db = await _db()
    if db is None:
        return resumo

    try:
        res = await (db.client.table("work_runs")
                     .select("id, company_id, status, current_step_key, input_payload, "
                             "error_code, created_at")
                     .eq("workflow_key", WORKFLOW_ACIONAMENTO)
                     .in_("status", list(_STATUS_EM_VOO_WORK_RUN))
                     .order("created_at", desc=True).limit(int(limite)).execute())
        runs = res.data or []
    except Exception as e:  # noqa: BLE001
        logger.error("[RECONCILIACAO] varredura falhou (%s) — nenhum acionamento "
                     "foi conferido neste boot", type(e).__name__)
        return resumo

    for run in runs:
        resumo["vistos"] += 1
        try:
            await _reconciliar_um(db, run, resumo)
        except Exception as e:  # noqa: BLE001
            logger.error("[RECONCILIACAO] run %s nao pode ser reconciliado (%s)",
                         run.get("id"), type(e).__name__)

    if resumo["vistos"]:
        logger.info("[RECONCILIACAO] %s", json.dumps(resumo, ensure_ascii=False))
    return resumo


async def _reconciliar_um(db, run: Dict[str, Any], resumo: Dict[str, int]) -> None:
    run_id = str(run.get("id") or "")
    company_id = str(run.get("company_id") or "")
    entrada = run.get("input_payload") or {}
    insurer = _digits(str(entrada.get("insurer_phone") or ""))
    fase = str(run.get("current_step_key") or "")

    if insurer and await _ler_do_redis(company_id, insurer) is not None:
        resumo["vivos"] += 1
        return

    # Daqui para baixo: o banco diz que existe trabalho em voo e o cache não tem
    # nada. É exatamente o buraco que esta SPEC fecha.
    retrato = await _ultimo_retrato(db, run_id, fase)
    snapshot = (retrato or {}).get("output_summary") or {}
    idade = _idade_segundos((retrato or {}).get("finished_at") or run.get("created_at"))
    janela = _motor().janela_de_vida_segundos(fase)

    if str(run.get("error_code") or "") == _ERRO_ORFAO:
        # Já gritou. Só não pode ficar gritando para sempre nem virar entulho.
        if idade < 0 or idade > _PRAZO_EXPIRAR_ORFAO_DIAS * 86400:
            await (db.client.table("work_runs").update({
                "status": "expired", "finished_at": _agora().isoformat(),
                "updated_at": _agora().isoformat(),
                "result_summary": "Acionamento órfão sem desfecho em 7 dias — encerrado.",
            }).eq("id", run_id).execute())
            resumo["expirados"] += 1
        else:
            resumo["ja_sinalizados"] += 1
        return

    # `insurer` é obrigatório para restaurar: sem ele a chave do cache sairia
    # truncada (`dispatch:active:{empresa}:`) e a "restauração" gravaria uma
    # sessão que inbound nenhum acharia — pior que não restaurar, porque
    # pareceria resolvido. Sem telefone, o run cai no caminho do órfão.
    if fase == "monitoring" and insurer and snapshot and 0 <= idade <= janela:
        sessao = _motor().sessao_restaurada(snapshot, motivo="reconciliacao_boot")
        await _gravar_no_redis(company_id, insurer, sessao,
                               ttl=max(300, int(janela - idade)))
        await _evento(db, company_id, run_id, "run.recovered",
                      "Acompanhamento restaurado: o cache tinha perdido este "
                      "acionamento e o cliente voltou a receber as atualizações.",
                      severidade="warning",
                      payload={"fase": fase, "idade_s": int(idade)})
        logger.warning("[RECONCILIACAO] monitoramento restaurado run=%s caso=%s",
                       run_id, entrada.get("case_id") or "?")
        resumo["restaurados"] += 1
        return

    if fase in ("monitoring", "captured") and idade > janela:
        await (db.client.table("work_runs").update({
            "status": "completed", "finished_at": _agora().isoformat(),
            "updated_at": _agora().isoformat(), "progress_percent": 100,
            "result_summary": "Monitoramento encerrado por tempo — a janela de "
                              "acompanhamento do acionamento passou.",
        }).eq("id", run_id).execute())
        resumo["encerrados"] += 1
        return

    if fase in _motor().FASES_ENCERRADAS:
        # A máquina já entregou: em `needs_human` o dossiê foi para o suporte da
        # corretora e o segurado foi avisado; em `test_aborted` o fluxo rodou até
        # a confirmação e cancelou. Sumir do cache aqui é o fim natural do
        # trabalho AUTOMÁTICO — gritar "órfão" seria alarme falso, e alarme falso
        # é como se ensina uma equipe a ignorar alarme.
        await (db.client.table("work_runs").update({
            "status": "completed", "finished_at": _agora().isoformat(),
            "updated_at": _agora().isoformat(), "progress_percent": 100,
            "result_summary": ("Caso entregue à equipe da corretora — a parte "
                               "automática do acionamento terminou aqui."),
        }).eq("id", run_id).execute())
        resumo["encerrados"] += 1
        return

    # ÓRFÃO QUE GRITA. Não devolvemos a sessão ao cache: em `ura`/`human_phase`
    # ela voltaria a FALAR com a seguradora (ver docstring). Vira trabalho
    # esperando gente, com o motivo escrito em três lugares que humanos leem.
    agora = _agora().isoformat()
    await (db.client.table("work_runs").update({
        "status": "waiting_input",
        "error_code": _ERRO_ORFAO,
        "error_message": (f"O acionamento sumiu do cache na fase '{fase or 'desconhecida'}' "
                          "e não pode ser retomado sozinho sem risco de responder "
                          "errado à seguradora. Precisa de alguém da corretora."),
        "updated_at": agora,
    }).eq("id", run_id).execute())
    await _evento(db, company_id, run_id, "approval.requested",
                  "Este acionamento perdeu o acompanhamento automático e precisa "
                  "de uma pessoa. O caso está inteiro na página Conversas.",
                  severidade="error",
                  payload={"fase": fase, "case_id": str(entrada.get("case_id") or ""),
                           "idade_s": int(idade)})
    logger.error("[RECONCILIACAO] ACIONAMENTO ORFAO run=%s fase=%s caso=%s idade_s=%s",
                 run_id, fase or "?", entrada.get("case_id") or "?", int(idade))
    try:
        from app.services.activity_log import log_activity

        await log_activity(company_id, "acionamentos",
                           "Acionamento precisa de alguém da equipe",
                           "O acompanhamento automático foi interrompido. O caso está "
                           "preparado na página Conversas para alguém assumir.")
    except Exception:  # noqa: BLE001
        pass
    resumo["orfaos"] += 1


def _digits(phone: str) -> str:
    return "".join(ch for ch in str(phone or "") if ch.isdigit())


async def list_active_dispatches(company_id: str) -> list:
    """Sessões de dispatch ATIVAS da corretora (espelho na página Conversas).

    Retorna resumo por sessão: telefone da seguradora, estado, subserviço,
    transcript e capturas — somente leitura, escopo por company."""
    prefix = f"dispatch:active:{company_id}:"
    raws: Dict[str, str] = {}
    redis = await _redis()
    if redis is not None:
        try:
            async for key in redis.scan_iter(match=prefix + "*"):
                k = key.decode() if isinstance(key, (bytes, bytearray)) else str(key)
                raw = await redis.get(k)
                if raw:
                    raws[k] = raw.decode() if isinstance(raw, (bytes, bytearray)) else str(raw)
        except Exception as e:  # noqa: BLE001
            logger.error(f"[DISPATCH ROUTER] list scan failed: {type(e).__name__}")
    else:
        raws = {k: v for k, v in _memory_store.items() if k.startswith(prefix)}

    sessions = []
    for key, raw in raws.items():
        try:
            s = json.loads(raw)
        except Exception:  # noqa: BLE001
            continue
        sessions.append({
            "insurer_phone": key[len(prefix):],
            "case_id": s.get("case_id"),
            "state": s.get("state"),
            "subservice": s.get("subservice"),
            "playbook_ref": s.get("playbook_ref"),
            "client_phone": s.get("client_phone"),
            "captured": s.get("captured") or {},
            "slots": s.get("slots") or {},
            "reason": s.get("reason"),
            "transcript": s.get("transcript") or [],
            "created_at": s.get("created_at"),
        })
    sessions.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
    return sessions


async def start_live_dispatch(
    *,
    company_id: str,
    case_id: str,
    playbook_ref: str,
    subservice: str,
    slots: Dict[str, Any],
    client_phone: str,
    insurer_phone: str,
    sender: Callable[[str], Any],
) -> Dict[str, Any]:
    """Inicia um acionamento REAL (gate já aberto pelo chamador): cria a sessão,
    envia a abertura à seguradora via sender e ativa o roteamento do inbound.

    Fail-safes: sessão ativa existente bloqueia (nunca duplo acionamento);
    slots incompletos não enviam nada nem salvam sessão.
    """
    insurer = _digits(insurer_phone)
    existing = await load_active_dispatch(company_id, insurer)
    if existing:
        # Sessão MORTA não pode bloquear um novo acionamento (teste 2026-07-10:
        # lock preso após a seguradora derrubar a conversa). Supersede quando:
        # needs_human/captured/test_aborted/monitoring/encaminhado, seguradora
        # encerrou, ou sessão velha (>45min).
        stale = str(existing.get("state") or "") in ("needs_human", "captured", "test_aborted",
                                                     "monitoring", "encaminhado")
        stale = stale or str(existing.get("reason") or "") == "insurer_closed"

        # MAS `monitoring` COM FOLLOW-UP AGENDADO NAO E SESSAO MORTA.
        #
        # 📊 O Follow-up morria ao nascer, e por um caminho que ninguem veria:
        # `_start_next_in_queue` roda na MESMA transicao que criou o timer
        # (captured -> monitoring), inicia o proximo da fila no MESMO
        # `insurer_phone`, e este trecho apagava a sessao anterior por "velha".
        #
        # O efeito: numa corretora com dois acionamentos na mesma seguradora, o
        # segurado do primeiro NUNCA recebia a pergunta "o prestador chegou?".
        # E nao havia erro nenhum — a sessao simplesmente sumia.
        #
        # `monitoring` significa "o servico foi aberto e estamos acompanhando".
        # Isso e o CONTRARIO de morto. Enquanto houver um follow-up ou um
        # encerramento por vir, a sessao fica.
        if stale and str(existing.get("state") or "") == "monitoring":
            tem_compromisso = bool(
                (existing.get("followup_at") and not existing.get("followup_sent"))
                or (existing.get("closing_at") and not existing.get("closing_sent"))
            )
            if tem_compromisso:
                logger.info("[DISPATCH ROUTER] monitoring com follow-up pendente — nao supersede")
                return {"ok": False, "error": "dispatch_monitoring_com_followup", "session": existing}
        try:
            from datetime import datetime, timezone

            created = datetime.fromisoformat(str(existing.get("created_at") or "").replace("Z", "+00:00"))
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            age_s = (datetime.now(timezone.utc) - created).total_seconds()
            stale = stale or age_s > 45 * 60
        except Exception:  # noqa: BLE001
            stale = True  # created_at ilegível = sessão suspeita, não bloqueia
        if not stale:
            return {"ok": False, "error": "dispatch_already_active", "session": existing}
        await clear_active_dispatch(company_id, insurer)
        logger.info(f"[DISPATCH ROUTER] stale session superseded (state={existing.get('state')})")

    session = new_dispatch_session(
        case_id=case_id, company_id=company_id, playbook_ref=playbook_ref,
        subservice=subservice, slots=slots,
    )
    if session.get("state") != "ready_to_send":
        return {"ok": False, "error": session.get("reason") or "not_ready", "session": session}

    session["client_phone"] = _digits(client_phone)
    session["insurer_phone"] = insurer
    session = start_dispatch(session, sender=sender)
    await save_active_dispatch(company_id, insurer, session)
    logger.info(f"[DISPATCH ROUTER] live dispatch started case={case_id} state={session.get('state')}")
    return {"ok": True, "session": session}


def _normalizar_destino(raw: Any) -> str:
    """GRUPO do WhatsApp (…@g.us) é destino válido — não reduzir a dígitos."""
    s = str(raw or "").strip()
    if not s:
        return ""
    return s if s.endswith("@g.us") else _digits(s)


async def _destino_e_compartilhado(db, company_id: str, destino: str) -> Optional[str]:
    """Este destino pertence a MAIS DE UMA corretora? Devolve o motivo, ou None.

    SPEC-063 Bloco B. 📊 Em 02/08/2026, Resulta e AutoFleet apontavam para o
    MESMO grupo de WhatsApp em `acionamento_profile`. O dossiê de handoff leva
    nome, telefone e CPF do segurado. Mandar o dossiê de um segurado da
    AutoFleet para um grupo que a Resulta lê é vazamento entre corretoras —
    o pior defeito que este produto pode ter.

    A regra é **recusar, não avisar**. Um handoff que não sai é um problema
    operacional que alguém conserta em minutos. Um CPF na conversa errada não
    se desfaz.
    """
    if not destino:
        return None
    try:
        outras: set = set()

        r1 = await (db.client.table("human_support_destinations")
                    .select("company_id, destination_ref")
                    .eq("destination_ref", destino).eq("is_active", True)
                    .limit(20).execute())
        for row in r1.data or []:
            if str(row.get("company_id")) != str(company_id):
                outras.add(str(row.get("company_id")))

        r2 = await (db.client.table("companies")
                    .select("id, acionamento_profile").limit(200).execute())
        for row in r2.data or []:
            if str(row.get("id")) == str(company_id):
                continue
            prof = row.get("acionamento_profile") or {}
            if _normalizar_destino(prof.get("suporte_humano_whatsapp")) == destino:
                outras.add(str(row.get("id")))

        if outras:
            return (f"destino de suporte compartilhado com {len(outras)} outra(s) "
                    f"corretora(s) — recusado para não vazar dossiê de segurado")
    except Exception as e:  # noqa: BLE001
        # Não conseguir PROVAR que é exclusivo não é permissão para enviar.
        logger.error("[DISPATCH ROUTER] nao foi possivel verificar exclusividade do "
                     "destino (%s) — recusando por seguranca", type(e).__name__)
        return "não foi possível verificar se o destino é exclusivo desta corretora"
    return None


async def resolver_destino_de_suporte(company_id: str) -> Dict[str, Any]:
    """O destino canônico de suporte humano da corretora — com prova de que é dela.

    Este é o ÚNICO resolvedor. Antes existiam duas verdades que não se falavam:
    a UI gravava em `human_support_destinations` (com prioridade, horário e
    escalonamento) e o backend lia `companies.acionamento_profile` — 📊 e a
    tabela da UI não aparecia UMA VEZ em `backend/app/`. Resultado: a corretora
    configurava um destino na tela e o dossiê ia para outro lugar.

    Ordem de autoridade, do mais específico para o mais velho:

        human_support_destinations   ativo, primary primeiro, depois priority
        companies.acionamento_profile.suporte_humano_whatsapp
        integrations.alert_target

    Devolve ``{"destino": str, "fonte": str, "recusa": Optional[str]}``.
    Com `recusa` preenchida, **não envie** — o motivo é para o log e para a tela.
    """
    saida: Dict[str, Any] = {"destino": "", "fonte": "", "recusa": None}
    try:
        from app.core.database import create_async_supabase_client

        db = await create_async_supabase_client()

        res0 = await (db.client.table("human_support_destinations")
                      .select("destination_ref, is_primary, priority_order")
                      .eq("company_id", company_id).eq("is_active", True)
                      .order("is_primary", desc=True).order("priority_order")
                      .limit(1).execute())
        if res0.data:
            saida["destino"] = _normalizar_destino(res0.data[0].get("destination_ref"))
            saida["fonte"] = "human_support_destinations"

        if not saida["destino"]:
            res = await (db.client.table("companies").select("acionamento_profile")
                         .eq("id", company_id).limit(1).execute())
            if res.data:
                prof = res.data[0].get("acionamento_profile") or {}
                saida["destino"] = _normalizar_destino(prof.get("suporte_humano_whatsapp"))
                if saida["destino"]:
                    saida["fonte"] = "acionamento_profile (legado)"

        if not saida["destino"]:
            res2 = await (db.client.table("integrations").select("alert_target")
                          .eq("company_id", company_id).limit(3).execute())
            for row in res2.data or []:
                d = _normalizar_destino(row.get("alert_target"))
                if d:
                    saida["destino"], saida["fonte"] = d, "integrations.alert_target"
                    break

        if saida["destino"]:
            motivo = await _destino_e_compartilhado(db, company_id, saida["destino"])
            if motivo:
                logger.error("[SUPORTE] corretora %s: %s", company_id, motivo)
                saida["recusa"] = motivo
                saida["destino"] = ""
    except Exception as e:  # noqa: BLE001 — offline/teste: sem contato
        logger.warning(f"[DISPATCH ROUTER] support contact lookup failed: {type(e).__name__}")
    return saida


async def _support_contact(company_id: str) -> str:
    """Compatibilidade: devolve só o destino, vazio quando recusado."""
    return (await resolver_destino_de_suporte(company_id)).get("destino") or ""


async def _log_deflection(company_id: str, session: Dict[str, Any]) -> None:
    """Telemetria de deflexão: cada needs_human vira registro estruturado
    (corredor, motivo, quantos passos andou) — é o combustível da meta dos 3%."""
    entry = {
        "at": _now_iso(),
        "case_id": session.get("case_id"),
        "playbook_ref": session.get("playbook_ref"),
        "subservice": session.get("subservice"),
        "reason": str(session.get("reason") or ""),
        "steps_out": len([t for t in (session.get("transcript") or []) if t.get("direction") == "out"]),
    }
    logger.warning(f"[DEFLECTION] {json.dumps(entry, ensure_ascii=False)}")
    try:
        redis = await _redis()
        if redis is not None:
            key = f"deflection:{company_id}"
            await redis.lpush(key, json.dumps(entry, ensure_ascii=False))
            await redis.ltrim(key, 0, 199)
    except Exception:  # noqa: BLE001
        pass


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _followup_schedule(captured: Dict[str, Any]) -> tuple:
    """(followup_at, closing_at) INTELIGENTES (feedback founder 12/07):
    - serviço AGENDADO (dia/hora capturados) → follow-up 45min APÓS o horário
      marcado do prestador (não após o protocolo);
    - ETA em minutos → 45min após a previsão de chegada;
    - sem nada → 45min após agora.
    Janela educada: nunca mandar mensagem entre 21h e 8h30 (America/Sao_Paulo)
    — adia para as 9h da manhã seguinte."""
    from datetime import datetime, timedelta, timezone as _tz

    try:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo("America/Sao_Paulo")
    except Exception:  # noqa: BLE001
        tz = _tz.utc
    now = datetime.now(tz)
    base = now
    captured = captured or {}
    sched = captured.get("schedule") or {}
    if sched.get("day"):
        try:
            parts = [p for p in str(sched["day"]).split("/") if p]
            d = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 else now.month
            y = int(parts[2]) if len(parts) > 2 else now.year
            if y < 100:
                y += 2000
            hh, mm = 9, 0
            at = sched.get("at") or sched.get("from")
            if at:
                bits = str(at).replace(" ", "").replace("h", ":").strip(":").split(":")
                hh = int(bits[0])
                mm = int(bits[1]) if len(bits) > 1 and bits[1] else 0
            base = datetime(y, m, d, hh, mm, tzinfo=tz)
        except Exception:  # noqa: BLE001
            base = now
    elif captured.get("eta_minutes"):
        try:
            base = now + timedelta(minutes=int(captured["eta_minutes"]))
        except Exception:  # noqa: BLE001
            base = now

    def _polite(dt):
        if dt.hour >= 21:
            return (dt + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
        if dt.hour < 8 or (dt.hour == 8 and dt.minute < 30):
            return dt.replace(hour=9, minute=0, second=0, microsecond=0)
        return dt

    follow = _polite(max(base + timedelta(minutes=45), now + timedelta(minutes=20)))
    closing = _polite(follow + timedelta(hours=2, minutes=30))
    return follow.astimezone(_tz.utc).isoformat(), closing.astimezone(_tz.utc).isoformat()


def _queue_key(company_id: str, insurer_phone: str) -> str:
    return f"dispatch:queue:{company_id}:{_digits(insurer_phone)}"


async def enqueue_dispatch(company_id: str, insurer_phone: str, request: Dict[str, Any]) -> int:
    """FILA multi-cliente: 2º acionamento para a MESMA seguradora espera o 1º
    terminar (1 conversa por número). Retorna a posição na fila (1-based)."""
    payload = json.dumps({**request, "queued_at": _now_iso()}, ensure_ascii=False, default=str)
    redis = await _redis()
    if redis is not None:
        size = await redis.rpush(_queue_key(company_id, insurer_phone), payload)
        await redis.expire(_queue_key(company_id, insurer_phone), 2 * 3600)
        return int(size)
    _memory_store.setdefault(_queue_key(company_id, insurer_phone) + ":list", [])
    _memory_store[_queue_key(company_id, insurer_phone) + ":list"].append(payload)
    return len(_memory_store[_queue_key(company_id, insurer_phone) + ":list"])


async def _pop_queued(company_id: str, insurer_phone: str) -> Optional[Dict[str, Any]]:
    redis = await _redis()
    raw = None
    if redis is not None:
        raw = await redis.lpop(_queue_key(company_id, insurer_phone))
    else:
        lst = _memory_store.get(_queue_key(company_id, insurer_phone) + ":list") or []
        raw = lst.pop(0) if lst else None
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:  # noqa: BLE001
        return None


async def _start_next_in_queue(
    company_id: str, insurer_phone: str,
    send_to_insurer: Callable[[str], Any], send_to_client: Callable[[str, str], Any],
) -> None:
    """Sessão liberou o número da seguradora → inicia o próximo da fila."""
    nxt = await _pop_queued(company_id, insurer_phone)
    if not nxt:
        return
    result = await start_live_dispatch(
        company_id=company_id, case_id=str(nxt.get("case_id") or "queued"),
        playbook_ref=str(nxt.get("playbook_ref") or ""), subservice=str(nxt.get("subservice") or ""),
        slots=nxt.get("slots") or {}, client_phone=str(nxt.get("client_phone") or ""),
        insurer_phone=insurer_phone, sender=send_to_insurer,
    )
    client_phone = _digits(str(nxt.get("client_phone") or ""))
    if result.get("ok") and client_phone:
        try:
            send_to_client(client_phone, "Chegou a sua vez! 🙂 Estou acionando a seguradora agora e te aviso assim que sair o protocolo.")
        except Exception:  # noqa: BLE001
            pass
    logger.info(f"[DISPATCH ROUTER] queue drained -> started={result.get('ok')}")


async def note_manual_outbound(company_id: str, insurer_phone: str, text: str) -> bool:
    """Registra no transcript uma mensagem MANUAL da corretora (humano clicou/
    digitou direto na conversa com a seguradora — fromMe). Sem isso o espelho
    fica incompleto quando um humano copilota a URA (teste 2026-07-12)."""
    session = await load_active_dispatch(company_id, insurer_phone)
    if not session or not str(text or "").strip():
        return False
    session.setdefault("transcript", []).append(
        {"direction": "out", "text": str(text)[:2000], "manual": True}
    )
    await save_active_dispatch(company_id, insurer_phone, session)
    return True


async def try_route_insurer_inbound(
    *,
    company_id: str,
    from_phone: str,
    text: str,
    send_to_insurer: Callable[[str], Any],
    send_to_client: Callable[[str, str], Any],
    human_reply_provider: Optional[Callable[..., Any]] = None,
    interactive: Optional[Dict[str, Any]] = None,
    flow_sender: Optional[Callable[..., Any]] = None,
    ainda_vem_mais: bool = False,
    # 🔴 O canal por onde o inbound chegou. Opcional: nenhum chamador antigo
    # quebra, e sem ele o comportamento e o de sempre.
    integration_id: Optional[str] = None,
) -> bool:
    """Se o inbound vier do número da seguradora com dispatch ativo, processa
    aqui e retorna True (o webhook NÃO deve seguir para o agente).

    send_to_insurer(texto) — responde a seguradora (mesma integração).
    send_to_client(telefone, texto) — avisa o segurado (protocolo/handoff).
    human_reply_provider(session, texto) — async; redige a resposta na fase
    humana da seguradora. TODA resposta passa pelo guard determinístico;
    2 reprovações seguidas → needs_human (nunca responde às cegas).

    interactive — os metadados da mensagem interativa, como o parser de inbound
    os entrega (`normalize_evolution_inbound(...)["interactive"]`). É por aqui
    que o `flow_token` do formulário nativo chega ao motor. Volátil: fica na
    sessão (Redis) e é cortado do checkpoint durável pelo nome.
    `webhook.py` ainda não o passa — enquanto não passar, o motor monta a
    resposta do formulário e PAUSA, que é o desfecho certo, não um contorno.

    flow_sender(flow_token=, flow_name=, params=) — o transporte que entrega a
    resposta do formulário nativo. `None` (o padrão) significa "não há caminho
    provado", e o motor pausa em vez de fingir que respondeu. 📊 O build atual
    do Evolution GO não tem rota para isso: 12 rotas de envio, nenhuma responde
    interativa (ver `providers/evolution_go.py`).

    ainda_vem_mais — "esta mensagem é um PEDAÇO da tela; o resto vem já".
    O caminho determinístico continua vendo cada mensagem em ordem, porque o
    menu pode estar na primeira e o "aguarde" na última. Mas a DELIBERAÇÃO (a
    chamada ao modelo e o guarda) espera a rajada inteira: com `True` a mensagem
    só se acumula em `pending_insurer_messages`; com `False` — a última do turno,
    e o padrão para quem chama com uma mensagem só — o modelo é chamado UMA vez,
    sobre a tela completa. Ver `_tela_do_turno`.
    """
    session = await load_active_dispatch(company_id, from_phone)
    if not session:
        return False

    # 🔴 A SESSAO LEMBRA POR ONDE A CONVERSA ENTROU — 18/08/2026.
    #
    # 📊 O defeito, medido: o Sentinela respondeu "1" a uma tela da Allianz, a
    # resposta estava CERTA, e nao saiu. Ele roda no relogio (APScheduler), sem
    # inbound, e pedia uma "integracao de plataforma". A Resulta nao tem
    # nenhuma: o dashboard pareia o WhatsApp da corretora como `observer`, e
    # observador nunca envia — regra boa, que existe para o segurado nao
    # receber mensagem de um numero que jurou ficar calado.
    #
    # Mas RESPONDER NAO E SURPREENDER. O corredor ja mandou dezenas de
    # mensagens para a URA por este mesmo canal. O Sentinela nao esta abrindo
    # conversa com ninguem: esta terminando a frase de uma conversa que ja
    # existe, com a seguradora, que nao e segurado de ninguem.
    #
    # A proibicao do observador continua inteira para tudo que e iniciativa
    # propria — cobranca, relatorio, sugestao. Muda so o significado de
    # "responder".
    if integration_id:
        session["integration_id"] = str(integration_id)

    # TEST_ABORTED = sessão ENCERRADA: nunca mais responder à seguradora
    # (teste Allianz 12/07: a URA mandou nova saudação após o cancelamento e a
    # sessão "zumbi" respondeu '1' reabrindo o fluxo). Só registra no espelho.
    if str(session.get("state") or "") == "test_aborted":
        session.setdefault("transcript", []).append({"direction": "in", "text": str(text)[:2000]})
        await save_active_dispatch(company_id, from_phone, session)
        return True

    # MONITORING (pós-protocolo): nunca responde à seguradora; repassa os
    # updates relevantes ao cliente e ignora pesquisas de satisfação.
    if str(session.get("state") or "") == "monitoring":
        norm = _norm(text)
        session.setdefault("transcript", []).append({"direction": "in", "text": str(text)[:2000]})
        if text.strip() and not re.search(_MONITOR_IGNORE_RE, norm) and re.search(_MONITOR_FORWARD_RE, norm):
            client_phone = str(session.get("client_phone") or "").strip()
            if client_phone:
                try:
                    send_to_client(client_phone, f"🔔 Atualização da sua assistência:\n{str(text).strip()[:600]}")
                except Exception as e:  # noqa: BLE001
                    logger.error(f"[DISPATCH ROUTER] monitor forward failed: {type(e).__name__}")
        await save_active_dispatch(company_id, from_phone, session)
        return True

    _saidas_antes = sum(1 for t in (session.get("transcript") or [])
                        if isinstance(t, dict) and t.get("direction") == "out")
    session = handle_insurer_message(session, text, sender=send_to_insurer,
                                     interactive=interactive, flow_sender=flow_sender)
    state = session.get("state")
    # O DETERMINÍSTICO JÁ FALOU NESTA BOLHA? Então o turno está respondido.
    #
    # O passo mapeado responde sozinho o que sabe responder — "qual o CPF",
    # "qual a placa", o menu numerado. Quando ele responde, o modelo era chamado
    # logo em seguida sobre o que tivesse sobrado de pendente, e saíam DUAS
    # mensagens nossas para uma pergunta da URA. Uma resposta por turno é o que
    # uma pessoa faz — e é o que a URA espera receber.
    #
    # O pendente não se perde: fica em `pending_insurer_messages` e entra na
    # tela do próximo turno.
    _ja_respondeu = sum(1 for t in (session.get("transcript") or [])
                        if isinstance(t, dict) and t.get("direction") == "out") > _saidas_antes

    # Fase humana: LLM redige, guard fiscaliza, falha repetida pausa (fail-closed).
    #
    # `not ainda_vem_mais` — ESPERA A TELA INTEIRA. Enquanto a rajada não
    # terminou, a mensagem apenas se acumula. Deliberar sobre meia tela era
    # responder à bolha errada em 2 de 3 turnos, e ainda gastava duas respostas
    # numa pergunta só (ver `_tela_do_turno`).
    if (state == "human_phase" and human_reply_provider is not None
            and session.get("pending_insurer_messages")
            and not ainda_vem_mais and not _ja_respondeu):
        tela = _tela_do_turno(session, text)
        draft = None
        try:
            draft = await human_reply_provider(session, tela)
        except Exception as e:  # noqa: BLE001 — provider nunca derruba o roteador
            logger.error(f"[DISPATCH ROUTER] human reply provider error: {type(e).__name__}")
        # O guarda julga a MESMA tela que o modelo leu. Se recebesse só a última
        # bolha, um "aguarde" solto passaria por tela que não pede nada e o
        # silêncio seria aprovado — com a pergunta duas linhas acima.
        verdict = guard_human_phase_reply(str(draft or ""), session,
                                          insurer_message=tela)
        if verdict["ok"]:
            session = reply_human_phase(session, verdict["reply"], sender=send_to_insurer)
            session["human_phase_guard_fails"] = 0
            # A retentativa de redação se renova aqui, no ACERTO — e só aqui.
            # Renová-la na falha faria o ciclo se repetir para sempre: errava,
            # ganhava perdão, errava de novo, ganhava perdão de novo, e o
            # contador nunca chegava a dois. 📊 Foi o teste do SPEC-017 que
            # pegou isso, na primeira rodada depois da mudança.
            session["retentou_redacao"] = False
            session["silencios_seguidos"] = 0
            # SPEC-039 F2: o Cérebro v2 decidiu numa fase humana (com o Mapa da
            # URA) — pulsa na Central de Agentes (antes nunca registrava).
            try:
                from app.core.heartbeat import beat

                await beat("cerebro", 1)
            except Exception:  # noqa: BLE001
                pass
        elif verdict.get("silencio"):
            # SILÊNCIO DELIBERADO — e ele NÃO gasta chance.
            #
            # 📊 43,2% das mensagens das seguradoras não pedem nada: aviso,
            # fila, "aguarde", termo de privacidade. Antes disso existir, duas
            # telas de aviso seguidas chamavam um humano — por dois avisos.
            #
            # O guarda já provou por código que a tela não pede nada; aqui só
            # se registra. Mas o silêncio tem TETO: três seguidos com a
            # seguradora ainda falando e o caso volta a andar, porque calar
            # para sempre é a nova forma de travar.
            quietos = int(session.get("silencios_seguidos") or 0) + 1
            session["silencios_seguidos"] = quietos
            # O Vigia precisa saber que este silêncio é de propósito, senão
            # ele acorda em 30s e o Sentinela fala por cima da tela.
            session["silencio_deliberado_ate"] = (
                datetime.now(timezone.utc) + timedelta(seconds=_SILENCIO_S)
            ).isoformat()
            logger.info("[DISPATCH ROUTER] silencio deliberado (%d seguidos) — "
                        "a tela nao pedia nada", quietos)
            if quietos >= 3:
                session["silencios_seguidos"] = 0
                session["silencio_deliberado_ate"] = None
                logger.warning("[DISPATCH ROUTER] 3 silencios seguidos — "
                               "deixando o Vigia acordar")
        else:
            # ERRO DE REDAÇÃO NÃO É RECUSA — e misturar os dois custava caro.
            #
            # 📊 Cinco motivos alimentavam UM contador. Uma resposta CERTA com
            # 401 caracteres contava igual a "não sei", e duas delas chamavam um
            # humano. O agente acertava e era punido por prolixidade.
            #
            # Redação ganha UMA nova tentativa no mesmo turno; recusa conta
            # direto. O teto de uma é duro: 💭 custa ~4s de modelo contra os
            # 103s de silêncio que a Allianz tolera — cabe uma vez, não duas.
            from app.services.insurer_dispatch_service import MOTIVOS_DE_REDACAO

            motivo = str(verdict.get("reason") or "")
            retentou = bool(session.get("retentou_redacao"))
            if motivo in MOTIVOS_DE_REDACAO and not retentou:
                session["retentou_redacao"] = True
                # 🔴 A RETENTATIVA AGORA ACONTECE — 18/08/2026.
                #
                # Este bloco marcava a bandeira, escrevia no log "uma nova
                # tentativa" e NÃO CHAMAVA NADA. O turno terminava em silêncio.
                # O modelo só voltaria a falar quando chegasse mensagem nova —
                # ou 30s depois, pelo Sentinela.
                #
                # 📊 Foi o que produziu o "travou" de 18/08: o cérebro
                # respondeu 459 tokens de prosa, o guarda reprovou por
                # `too_long` (régua de 400 caracteres), o log prometeu uma
                # nova tentativa, e a Allianz esperou 248 segundos até
                # encerrar por inatividade.
                #
                # Promessa em log é a forma mais barata de mentir para quem
                # investiga: parece que o sistema tentou.
                logger.info("[DISPATCH ROUTER] recusa de REDACAO (%s) — "
                            "REFAZENDO a resposta neste mesmo turno", motivo)
                try:
                    draft2 = await human_reply_provider(
                        session, tela + chr(10) * 2 + _PEDIDO_DE_ENCURTAR)
                except Exception as e:  # noqa: BLE001
                    logger.error("[DISPATCH ROUTER] retentativa falhou: %s",
                                 type(e).__name__)
                    draft2 = None
                v2 = guard_human_phase_reply(str(draft2 or ""), session,
                                             insurer_message=tela)
                if v2.get("ok"):
                    # 🔴 NAO devolve aqui. A funcao devolve `bool`, e sair por
                    # este ponto pularia o resto do turno -- o registro, o
                    # espelho e a gravacao no fim. Foi um defeito MEU, pego
                    # relendo o proprio conserto: `return session` num lugar
                    # que promete `-> bool` e verdadeiro por acidente, e por
                    # isso nao apareceria em teste nenhum de tipo.
                    #
                    # A resposta JA FOI ENVIADA por `reply_human_phase`. O
                    # fluxo segue normalmente daqui, igual ao acerto de
                    # primeira.
                    session = reply_human_phase(session, v2["reply"],
                                                sender=send_to_insurer)
                    session["human_phase_guard_fails"] = 0
                    logger.info("[DISPATCH ROUTER] retentativa ACEITA")
                else:
                    # A retentativa também falhou: agora sim conta como recusa.
                    fails = int(session.get("human_phase_guard_fails") or 0) + 1
                    session["human_phase_guard_fails"] = fails
                    logger.error("[DISPATCH ROUTER] retentativa TAMBEM recusada "
                                 "(%s) — %s/2", v2.get("reason"), fails)
            else:
                # A MARCA NÃO SE APAGA AQUI. Este era um defeito meu, pego pelo
                # teste: zerar `retentou_redacao` na FALHA fazia o ciclo se
                # repetir para sempre — errava, ganhava perdão, errava de novo,
                # ganhava perdão de novo, e o contador nunca chegava a dois.
                # A retentativa é UMA por turno; ela só se renova quando uma
                # resposta é de fato aceita (ver o ramo de sucesso acima).
                fails = int(session.get("human_phase_guard_fails") or 0) + 1
                session["human_phase_guard_fails"] = fails
                logger.warning(f"[DISPATCH ROUTER] human phase reply rejected ({verdict['reason']}) fails={fails}")
                if fails >= 2:
                    session["state"] = "needs_human"
                    session["reason"] = f"human_phase_guard:{verdict['reason']}"
                    state = "needs_human"

    if state == "test_aborted":
        # Modo TESTE: fluxo executado até a confirmação final e CANCELADO — nada
        # foi aberto na seguradora. Avisar quem está testando e manter a sessão
        # no espelho para inspeção (supersede libera novo acionamento).
        client_phone = str(session.get("client_phone") or "").strip()
        if client_phone and not session.get("client_notified_test_abort"):
            try:
                send_to_client(
                    client_phone,
                    "🧪 Teste concluído: o acionamento na seguradora foi executado até a "
                    "confirmação final e CANCELADO antes de abrir o serviço (modo teste). "
                    "Nenhum prestador foi acionado.",
                )
                session["client_notified_test_abort"] = True
            except Exception as e:  # noqa: BLE001
                logger.error(f"[DISPATCH ROUTER] test abort notify failed: {type(e).__name__}")
        await save_active_dispatch(company_id, from_phone, session)
        logger.info(f"[DISPATCH ROUTER] test_aborted case={session.get('case_id')} reason={session.get('reason')}")
        await _start_next_in_queue(company_id, from_phone, send_to_insurer, send_to_client)
        return True

    if state == "encaminhado":
        # P-46 — O SEGUNDO DESFECHO DE SUCESSO. A seguradora não abre chamado
        # por este canal; ela entregou o caminho, e o trabalho do corredor é
        # ENTREGAR esse caminho ao segurado e encerrar.
        #
        # Antes disto, o passo de encaminhamento era `noop` (certo: não se
        # responde à URA aqui) e o caso ficava aberto até o watchdog — o
        # segurado nunca recebia o formulário e o desfecho virava abandono.
        referral = dict(session.get("referral") or {})
        client_phone = str(session.get("client_phone") or "").strip()
        # O LINK É O DA CONVERSA, nunca um endereço de memória: quem o escreve é
        # a seguradora, e `extract_capture_anchors` só o guarda se ele chegou.
        # As palavras da seguradora vão junto, entre aspas e sem paráfrase — é
        # o que os dois `client_message` mandam repassar.
        dito = str(referral.get("insurer_text") or "").strip()
        partes = [str(referral.get("client_message") or "").strip(),
                  f"A seguradora informou:\n“{dito}”" if dito else "",
                  str(referral.get("link") or "").strip()]
        aviso = "\n\n".join(p for p in partes if p)
        if aviso and client_phone and not session.get("client_notified_referral"):
            try:
                send_to_client(client_phone, aviso)
                session["client_notified_referral"] = True
                await _registrar_fala_ao_cliente(
                    company_id, client_phone, "acionamento_encaminhamento", aviso)
                session.setdefault("transcript", []).append(
                    {"direction": "out", "text": f"[AO CLIENTE] {aviso}",
                     "at": _now_iso(), "step": "encaminhamento"})
            except Exception as e:  # noqa: BLE001
                # Mesma regra do protocolo: falha de aviso NÃO passa em silêncio.
                # Sem esta entrega o encaminhamento não aconteceu — o segurado
                # ficou sem o formulário e o caso se declararia resolvido.
                logger.error(f"[DISPATCH ROUTER] referral notify failed: {type(e).__name__}")
                session["client_notify_failed"] = type(e).__name__
                try:
                    await _support_alert_seguro(company_id, session, aviso)
                except Exception:  # noqa: BLE001
                    pass
        await _log_deflection(company_id, session)
        # SALVAR ANTES DE LIBERAR. `clear_active_dispatch` relê a sessão do
        # Redis para saber QUAL Work Run fechar e em que fase — sem este save
        # ela leria o estado anterior e encerraria o run como `cancelled`,
        # registrando um encaminhamento bem-sucedido como abandono.
        session["resolved_at"] = _now_iso()
        await save_active_dispatch(company_id, from_phone, session)
        # Sessão ENCERRADA: liberar a chave é o que impede o run de ficar
        # eternamente "em voo" e o que deixa o próximo acionamento entrar.
        await clear_active_dispatch(company_id, from_phone)
        logger.info(f"[DISPATCH ROUTER] encaminhado case={session.get('case_id')} "
                    f"kind={referral.get('kind')} link={'sim' if referral.get('link') else 'nao'}")
        await _start_next_in_queue(company_id, from_phone, send_to_insurer, send_to_client)
        return True

    if state == "captured":
        summary = client_summary_from_capture(session)
        client_phone = str(session.get("client_phone") or "").strip()
        if summary and client_phone:
            try:
                send_to_client(client_phone, summary)
                session["client_notified"] = True
                # O aviso passa a EXISTIR para quem atende. Sem isto, o agente
                # podia prometer o protocolo que já tinha sido entregue.
                await _registrar_fala_ao_cliente(
                    company_id, client_phone, "acionamento_protocolo", summary)
                # E entra no transcript: é o que o Espelho, a linha do tempo e o
                # dossiê mostram. Falar com o cliente e não deixar rastro faz os
                # três mentirem por omissão.
                session.setdefault("transcript", []).append(
                    {"direction": "out", "text": f"[AO CLIENTE] {summary}",
                     "at": _now_iso(), "step": "aviso_de_protocolo"})
            except Exception as e:  # noqa: BLE001
                # FALHA AO AVISAR NÃO PODE PASSAR EM SILÊNCIO.
                #
                # 📊 Antes, o erro era logado e o fluxo seguia para `monitoring`
                # como se tudo tivesse dado certo: `client_notified` ficava
                # ausente e ninguém olhava. O protocolo se perdia para o cliente
                # em definitivo — ele nunca saberia que o serviço foi aberto.
                logger.error(f"[DISPATCH ROUTER] client notify failed: {type(e).__name__}")
                session["client_notify_failed"] = type(e).__name__
                try:
                    from app.services.dispatch_router import _support_alert_seguro
                    await _support_alert_seguro(company_id, session, summary)
                except Exception:  # noqa: BLE001
                    pass
        # Protocolo capturado → MONITORING: seguimos ouvindo a seguradora para
        # repassar updates ao cliente + FOLLOW-UP proativo com timer ("o guincho
        # chegou?" ~45min; encerramento carinhoso ~3h) via check_dispatch_followups.
        session["state"] = "monitoring"
        session["followup_at"], session["closing_at"] = _followup_schedule(session.get("captured") or {})
        await save_active_dispatch(company_id, from_phone, session)
        logger.info(f"[DISPATCH ROUTER] captured->monitoring case={session.get('case_id')} protocol=***")
        await _start_next_in_queue(company_id, from_phone, send_to_insurer, send_to_client)
        return True

    if state == "needs_human":
        reason = str(session.get("reason") or "")
        # RETOMADA AUTOMÁTICA: a URA derrubou a conversa (timeout/erro) e o fluxo
        # é idempotente até o freio → reabre SOZINHO uma vez, sem humano.
        # `not session.get("captured")` — a guarda que faltava.
        #
        # A retomada existe para quando a URA derruba a conversa ANTES de abrir
        # nada: o fluxo é idempotente até o freio, então refazer é seguro.
        #
        # Deixa de ser seguro no instante em que a seguradora já deu um
        # protocolo. Aí o serviço EXISTE — há um guincho a caminho — e reabrir
        # manda um segundo. O segurado recebe dois prestadores, a corretora
        # responde por dois acionamentos, e a seguradora vê duplicidade no
        # sistema dela.
        #
        # 📊 O risco não era teórico: até 03/08 o gatilho de `captured` exigia
        # protocolo E (agendamento OU eta OU link). O residencial da Allianz não
        # captura eta nem link — então protocolo sem agendamento reconhecido
        # caía direto aqui, e o re-acionamento era o caminho normal, não a
        # exceção. Os dois consertos são o mesmo defeito visto de dois lados.
        if (reason == "insurer_closed"
                and int(session.get("retry_count") or 0) == 0
                and not (session.get("captured") or {}).get("protocol")):
            await clear_active_dispatch(company_id, from_phone)
            retry = await start_live_dispatch(
                company_id=company_id, case_id=str(session.get("case_id") or "retry"),
                playbook_ref=str(session.get("playbook_ref") or ""),
                subservice=str(session.get("subservice") or ""),
                slots=session.get("slots") or {},
                client_phone=str(session.get("client_phone") or ""),
                insurer_phone=from_phone, sender=send_to_insurer,
            )
            if retry.get("ok"):
                retry["session"]["retry_count"] = 1
                await save_active_dispatch(company_id, from_phone, retry["session"])
                logger.info(f"[DISPATCH ROUTER] insurer_closed -> auto-retry iniciado case={session.get('case_id')}")
                return True
        client_phone = str(session.get("client_phone") or "").strip()
        if client_phone and not session.get("client_notified_handoff"):
            try:
                send_to_client(
                    client_phone,
                    "Estou finalizando um detalhe do seu atendimento com a seguradora e um colega da equipe vai assumir daqui a pouquinho, tá bom? Já já te retorno 🙂",
                )
                session["client_notified_handoff"] = True
            except Exception as e:  # noqa: BLE001
                logger.error(f"[DISPATCH ROUTER] handoff notify failed: {type(e).__name__}")
        # DOSSIÊ MASTIGADO para o suporte humano da corretora (1x por sessão).
        if not session.get("dossier_sent"):
            support = await _support_contact(company_id)
            if support:
                try:
                    send_to_client(support, build_handoff_dossier(session, reason))
                    session["dossier_sent"] = True
                except Exception as e:  # noqa: BLE001
                    logger.error(f"[DISPATCH ROUTER] dossier send failed: {type(e).__name__}")
            else:
                logger.warning("[DISPATCH ROUTER] handoff SEM contato de suporte configurado (acionamento_profile.suporte_humano_whatsapp)")
        await _log_deflection(company_id, session)
        if reason == "insurer_closed":
            await clear_active_dispatch(company_id, from_phone)
            await _start_next_in_queue(company_id, from_phone, send_to_insurer, send_to_client)
        else:
            await save_active_dispatch(company_id, from_phone, session)
        logger.warning(f"[DISPATCH ROUTER] needs_human case={session.get('case_id')} reason={reason}")
        return True

    await save_active_dispatch(company_id, from_phone, session)
    return True
