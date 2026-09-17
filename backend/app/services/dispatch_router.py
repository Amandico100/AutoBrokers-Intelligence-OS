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

import json
import logging
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

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


def _pii():
    """O mascarador do retrato para humano — SPEC-085 FASE 1.

    Tardio pelo mesmo motivo do `_motor()` acima, e por um a mais: quem dubla
    este módulo em teste não deve ser obrigado a ter o mascarador em pé para
    exercitar o roteamento, que é outro assunto."""
    from app.services import pii_da_sessao

    return pii_da_sessao


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
    # 🔴 SPEC-EXTRA-001.3 — 2º dos 11 pontos, agora pela PORTA ÚNICA.
    #
    # ⚠️ O `destino.get("number")` abaixo estava ERRADO desde sempre:
    # `resolver_destino_de_suporte` devolve `{"destino", "fonte", "recusa"}` —
    # `number` não existe nesse dicionário, e o `if not alvo: return` fazia
    # este aviso sair calado TODA vez. A porta única resolve o destino ela
    # mesma, então o defeito morre junto com as três linhas.
    try:
        from app.core.database import get_supabase_client
        from app.services.o_grupo_so_o_que_importa import TIPO_VIGIA, enviar_ao_grupo

        aviso = ("⚠️ O aviso de protocolo NÃO chegou ao segurado.\n"
                 f"Caso: {session.get('case_id')}\n"
                 f"Telefone: {session.get('client_phone')}\n\n{resumo}")
        await enviar_ao_grupo(
            get_supabase_client(), company_id=str(company_id), tipo=TIPO_VIGIA,
            texto=aviso,
            conversation_id=str(session.get("mirror_conversation_id") or ""),
            telefone=str(session.get("client_phone") or ""),
            sessao=session,
            resumo="aviso de protocolo nao chegou — caso %s"
                   % str(session.get("case_id") or "")[:8],
            motivo="aviso_nao_chegou")
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
#
# 🔴 SPEC-093-B BLOCO 0-bis — O INSERT NÃO MORA MAIS AQUI.
# A sombra do sinistro precisa do MESMO caminho (mesmo motivo: ninguém no worker
# a executa), e CLAUDE.md §5 proíbe a segunda cópia. Quem grava agora é
# `app.services.work.runs.criar_registro_sem_fila` — este arquivo virou um
# chamador entre outros. A razão acima continua valendo e está repetida lá.

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


#: Um UUID de verdade, não "sim" nem "wa-5548…". 📊 O simulador de acionamento
#: usa `company_id="sim"`, e a SPEC-087 já pagou por confiar na forma do texto.
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
                   r"[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


async def _conversa_provada_da_sessao(db, company_id: str,
                                      session: Dict[str, Any]) -> Optional[str]:
    """De qual conversa este acionamento nasceu — **ou `None`**. SPEC-090 A.

    ✅ O dado já está na mão: `dispatch_mirror.py:55-60` grava
    `session["mirror_conversation_id"]`. A SPEC acertou ao dizer *"escrito por
    quem CRIA o run — o dispatch já tem a conversa na mão"*.

    ⚠️ **E ele falta legitimamente:** é vazio com `DISPATCH_MIRROR=0` e quando a
    conversa não pôde ser criada. Isso não é erro — é ausência, e a ausência se
    escreve NULO.

    ---------------------------------------------------------------------------
    🔴 POR QUE ESTA FUNÇÃO CONFERE A CORRETORA, SE A FK JÁ CONFERE

    A migration deste bloco pôs uma FK **composta**
    `(conversation_id, company_id) → conversations (id, company_id)`: o banco
    RECUSA um run da Resulta apontando para conversa da AutoFleet. 📊 Provado no
    VERIFY V3, com linha de controle — cross-tenant recusado `t`, mesma
    corretora aceita `t`.

    ⛔ **Mas deixar a FK ser quem recusa custaria o acionamento inteiro.** O
    `INSERT` é um só: se ele falha por causa desta coluna, o run não nasce, o
    segurado fica esperando, e o produto perde a corrida por causa de um campo
    de relatório.

    A ordem certa é a inversa: **o código prova antes de gravar, e na dúvida
    grava NULO.** A FK fica sendo a segunda linha de defesa — a que pega o dia
    em que alguém refatorar esta função e esquecer o `.eq("company_id")`.

    ⚠️ E o SELECT que falha também devolve `None`. Perder a ligação de um run
    legítimo é recuperável — o backfill a reconstrói. Gravar a ligação errada
    produz relatório confiante e falso, que é o que o BLOCO A existe para
    impedir.
    """
    bruto = str(session.get("mirror_conversation_id") or "").strip()
    if not bruto or not _UUID.match(bruto):
        return None
    if not _UUID.match(str(company_id or "")):
        return None
    try:
        achado = await (db.client.table("conversations").select("id")
                        .eq("id", bruto).eq("company_id", str(company_id))
                        .limit(1).execute())
    except Exception as erro:  # noqa: BLE001
        logger.warning("[ACIONAMENTO] conversa não pôde ser provada (%s) — o run "
                       "nasce com conversation_id NULO", type(erro).__name__)
        return None
    if not (achado.data or []):
        # 🔴 NÃO É SÓ "não achou". A conversa existe em ALGUMA corretora e não
        # nesta, ou não existe. Os dois casos terminam igual — NULO — mas o
        # primeiro é cross-tenant tentado, e ele merece linha de log.
        logger.warning("[ACIONAMENTO] conversa %s… não pertence à corretora %s… — "
                       "run gravado com conversation_id NULO",
                       bruto[:8], str(company_id)[:8])
        return None
    return bruto


#: 🔴 Quanto tempo para trás o episódio corrente pode estar, em horas.
#:
#: ⚠️ O acionamento fala com a SEGURADORA; o episódio é a conversa com o
#: SEGURADO, e ela costuma emudecer assim que o segurado descreve o problema.
#: Exigir que o episódio esteja "vivo agora" recusaria o caso normal. 📊 O Atlas
#: fecha o episódio com 6 h de silêncio (`observer_intake._SESSION_GAP`), então
#: 24 h dão folga de um ciclo inteiro sem alcançar o guincho do mês passado.
_JANELA_DO_EPISODIO_H = 24


async def _episodio_do_atendimento(db, company_id: str,
                                   session: Dict[str, Any]) -> str:
    """Qual EPISÓDIO (`attendance_sessions`) este acionamento está atendendo.

    🔴 **SPEC-097 U1.2 — o elo que faltava.** 📊 Medido em 05/09/2026:
    `grep -rn "attendance_session_id" backend/app` dava 15 ocorrências e **ZERO
    escritas**. `_marcar_fim_do_atendimento` já sabia usar o episódio, mas
    ninguém jamais o punha na sessão de acionamento — então, com
    `DISPATCH_MIRROR=0`, o corredor continuava saindo sem marcar nada, que era
    exatamente o defeito que a U1.2 diz consertar. Ler a chave e nunca
    escrevê-la é um elo que não existe.

    ⚠️ **A junção é `(company_id, counterparty)`, e a normalização é a MESMA**
    que o resto do produto usa para achar conversa por telefone: só dígitos
    (`_digits` aqui, `so_digitos` no backfill, `_conversa_unica_do_telefone` no
    Atlas). 📊 `attendance_sessions.counterparty` é 12.762/12.762 só dígitos e
    `session["client_phone"]` já passou por `_digits` em `start_live_dispatch`.
    Um segundo jeito de normalizar seria um segundo conjunto de elos (§9.4).

    🔴 **O MAIS RECENTE dentro da janela, e o empate RECUSA.** 📊 5,8 episódios
    por contato: o contato tem passado, e marcar o desfecho no episódio errado
    encerraria o guincho de março com o motivo da dúvida de agosto. O corredor
    está rodando AGORA, então o episódio corrente é o de `last_event_at` mais
    novo; quando dois empatam no mesmo instante não há "o mais novo", e um
    palpite valeria menos que a ausência.

    ⛔ **Nunca levanta, e `""` é resposta legítima** — contato sem episódio
    (chat web, teste, simulador) existe, e ali o espelho segue sendo a âncora.
    """
    guardado = str(session.get("attendance_session_id") or "").strip()
    if _UUID.match(guardado):
        return guardado                     # já resolvido nesta sessão

    empresa = str(company_id or "").strip()
    # ⛔ `company_id="sim"` é o simulador (SPEC-087). Ele não tem episódio, e
    #    um SELECT por ele só custaria uma ida ao banco por acionamento falso.
    if not _UUID.match(empresa):
        return ""
    telefone = _digits(str(session.get("client_phone") or ""))
    if not telefone:
        return ""

    try:
        achado = await (db.client.table("attendance_sessions")
                        .select("id, last_event_at")
                        .eq("company_id", empresa)          # 🔴 §7
                        .eq("counterparty", telefone)
                        .order("last_event_at", desc=True)
                        .limit(2).execute())
    except Exception as erro:  # noqa: BLE001
        logger.warning("[FIM] episódio do atendimento não resolvido (%s) — o "
                       "desfecho fica com o espelho", type(erro).__name__)
        return ""
    linhas = list(achado.data or [])
    if not linhas:
        return ""

    quando = str(linhas[0].get("last_event_at") or "")
    if len(linhas) > 1 and str(linhas[1].get("last_event_at") or "") == quando:
        # 🔴 Empate no MESMO instante: não há episódio corrente, há dois.
        logger.info("[FIM] dois episódios deste contato empatam em "
                    "`last_event_at` — nenhum é marcado pelo corredor")
        return ""

    referencia = _agora()
    try:
        nascida = datetime.fromisoformat(
            str(session.get("created_at") or "").replace("Z", "+00:00"))
        referencia = nascida if nascida.tzinfo else nascida.replace(tzinfo=timezone.utc)
    except Exception:  # noqa: BLE001
        pass                                 # sem `created_at` legível: agora
    try:
        visto = datetime.fromisoformat(quando.replace("Z", "+00:00"))
        if visto.tzinfo is None:
            visto = visto.replace(tzinfo=timezone.utc)
    except Exception:  # noqa: BLE001
        return ""                            # sem relógio não há janela
    if referencia - visto > timedelta(hours=_JANELA_DO_EPISODIO_H):
        logger.info("[FIM] o episódio mais novo deste contato é anterior à "
                    "janela de %dh — o acionamento não o encerra",
                    _JANELA_DO_EPISODIO_H)
        return ""

    episodio = str(linhas[0].get("id") or "")
    if not _UUID.match(episodio):
        return ""
    # 🔴 E AGORA A CHAVE É ESCRITA — era esta a linha que não existia em lugar
    #    nenhum do produto. Resolver uma vez por sessão também poupa o SELECT
    #    em cada checkpoint.
    session["attendance_session_id"] = episodio
    return episodio


async def _garantir_work_run(db, company_id: str, insurer_digits: str,
                             session: Dict[str, Any]) -> Optional[str]:
    """O Work Run desta sessão — reaproveitado, nunca duplicado.

    🔴 **Quem grava é `criar_registro_sem_fila`, não este arquivo.** O INSERT
    direto morava aqui e era o único do produto que sabia escrever
    `conversation_id` num run. A SPEC-093-B precisa exatamente do mesmo INSERT
    para a sombra do sinistro, e CLAUDE.md §5 proíbe a segunda cópia — então ele
    foi EXTRAÍDO para `app.services.work.runs`, com a razão de não passar pelo
    RPC (o outbox) escrita lá. As colunas e os valores são os mesmos: o que
    mudou de lugar foi a mão que escreve.

    ⚠️ **A ÚNICA diferença de comportamento, dita em voz alta:** a prova da
    conversa passou a acontecer ANTES da checagem de idempotência, porque quem
    checa agora é o helper. Custo: um `SELECT` a mais em `conversations` no
    caminho raro em que a sessão perdeu o `work_run_id` mas o run já existe.
    Nenhuma ESCRITA mudou — nem coluna, nem valor, nem ordem.
    """
    # ⚠️ Import tardio pela MESMA razão do `_motor()` acima: este módulo é
    # carregado por guardas que montam um `app.services` de mentira com
    # `__path__ = []`, e um import de topo os obrigaria a conhecer cada
    # submódulo novo — quebrando quem não tem nada a ver com o assunto.
    from app.services.work.runs import criar_registro_sem_fila

    if session.get("work_run_id"):
        return str(session["work_run_id"])

    idem = _chave_idempotente(insurer_digits, session)
    fase = str(session.get("state") or "preparing")
    status = _motor().status_duravel_da_fase(fase)
    entrada = {
        "company_id": str(company_id),
        "case_id": str(session.get("case_id") or ""),
        "insurer_phone": insurer_digits,
        "playbook_ref": str(session.get("playbook_ref") or ""),
        "subservice": str(session.get("subservice") or ""),
    }
    linha = {
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
        "idempotency_key": idem,
        "input_payload": entrada,
        "current_step_key": fase,
        "progress_percent": _progresso_da_fase(fase, status),
        # 🔴 SPEC-090 BLOCO A — de qual conversa este acionamento nasceu.
        #
        # 📊 Sem esta linha, reconstruir *"o cliente escreveu X, o robô abriu o
        # chamado, travou na tela Y"* era impossível: `work_runs` não tinha
        # NENHUMA coluna de conversa (medido em 26/08 — 50 colunas, nenhuma).
        #
        # ⛔ `None` é resposta, não falha. Ver `_conversa_provada_da_sessao`.
        "conversation_id": await _conversa_provada_da_sessao(db, company_id, session),
    }
    registro = await criar_registro_sem_fila(db, **linha)
    run_id = str(registro["id"])
    session["work_run_id"] = run_id
    # ⚠️ Run reaproveitado não nasce de novo: sem `run.created` na linha do
    # tempo, sem linha de log de criação. Era assim antes da extração.
    if registro.get("reused"):
        return run_id

    await _evento(db, company_id, run_id, "run.created",
                  "Acionamento aberto na seguradora — a partir daqui cada fase "
                  "fica gravada, mesmo se o cache cair.",
                  payload={"fase": fase, "case_id": entrada["case_id"]})
    logger.info("[ACIONAMENTO DURAVEL] run %s criado para o caso %s",
                run_id, entrada["case_id"] or "?")
    return run_id


#: Os únicos valores que `work_events.actor_type` aceita — há CHECK no banco.
#: ⚠️ `human` **não está** aqui: escrever esse valor é um INSERT que o Postgres
#: recusa, e um evento que nunca acontece.
ATORES_VALIDOS = ("system", "worker", "user", "agent", "admin", "provider")


async def _evento(db, company_id: str, run_id: str, tipo: str, mensagem: str, *,
                  severidade: str = "info", payload: Optional[Dict[str, Any]] = None,
                  ator: str = "system") -> None:
    """Linha do tempo do Work Run. Sem dado do segurado: quem guarda o conteúdo
    da conversa é o Espelho, e `payload_redacted` tem esse nome por um motivo."""
    try:
        await db.client.table("work_events").insert({
            "company_id": str(company_id),
            "work_run_id": run_id,
            "event_type": tipo,
            "actor_type": ator if ator in ATORES_VALIDOS else "system",
            "severity": severidade,
            "message_human": str(mensagem)[:1000],
            "payload_redacted": payload or {},
        }).execute()
    except Exception as e:  # noqa: BLE001
        logger.warning("[ACIONAMENTO DURAVEL] evento '%s' nao registrado: %s",
                       tipo, type(e).__name__)


#: Quem, nesta casa, pode destravar um acionamento. 🔴 A ORDEM É A DE
#: CRÉDITO: o humano vence todos, porque foi ele quem fez o trabalho.
#:
#: 📊 Medido em 25/08/2026: `work_runs.assumido_por_humano` = **0** e
#: `work_events` com ator humano = **0** em 27.985 eventos. O clique da atendente
#: no WhatsApp dela não deixava rastro nenhum — e a fase seguinte era creditada
#: ao robô por `retomado_pelo_robo`.
DESTRAVADORES = ("humano", "cerebro", "sentinela", "vigia", "robo")

#: 🔴 QUEM, DENTRE ELES, NÃO É O ROBÔ.
#:
#: ⚠️ Cérebro, Sentinela e Vigia **são** o robô para efeito da COLUNA — quem
#: os distingue é o EVENTO, que é exatamente a granularidade que
#: `unblock_state` não tem (é o C.2 inteiro).
#:
#: 🔴 Tratar os três como "não-robô" deixava a coluna em `travado` **para
#: sempre** depois de um destrave automático: o caso aparecia na Fila como
#: travado tendo sido retomado, e o travamento seguinte era engolido pela
#: idempotência. O painel achou isso.
DESTRAVADORES_HUMANOS = ("humano",)

#: `work_events.actor_type` tem CHECK no banco e só aceita estes seis:
#: `system | worker | user | agent | admin | provider`. ⚠️ `human` **não está na
#: lista** — escrever esse valor é um evento que nunca acontece.
_ATOR_DO_DESTRAVADOR = {
    "humano": "user",
    "cerebro": "agent",
    "sentinela": "agent",
    "vigia": "agent",
    "robo": "system",
}


def tela_do_travamento(session: Dict[str, Any]) -> str:
    """PURO. Em que TELA da URA o acionamento parou.

    📊 Medido em produção: `reason` guarda a tela no próprio nome —
    `missing_slots:problema_eletrico_opcao`, e `problema_eletrico_opcao` **é** a
    tela. Quando o motivo não nomeia tela (`sentinela_stall`, `insurer_closed`),
    a última chave de `step_counts` é a tela em que se estava.

    ⚠️ `step_counts` só serve **na sessão viva**: dicionário Python preserva a
    ordem de inserção, `jsonb` do Postgres **não** (reordena por tamanho e byte).
    Por isso a tela vai no payload do evento, escrita aqui — e não é deduzida
    depois lendo a coluna.
    """
    motivo = str(session.get("reason") or "")
    if motivo.startswith("missing_slots:"):
        tela = motivo.split(":", 1)[1].strip()
        if tela:
            return tela[:120]
    passos = session.get("step_counts")
    if isinstance(passos, dict) and passos:
        return str(list(passos)[-1])[:120]
    return ""


def eventos_do_travamento(fase: str, fase_anterior: str,
                          session: Dict[str, Any], *,
                          segundos_travado: Optional[int] = None) -> List[Dict[str, Any]]:
    """PURO. Que linhas de `work_events` esta transição de fase gera.

    🔴 **UM EVENTO POR TRAVAMENTO, NÃO UM ESTADO POR RUN** — e essa é a
    diferença inteira do BLOCO C.

    📊 `work_runs.unblock_state` é **uma coluna**: um acionamento que trava,
    destrava e trava de novo tem um só valor no fim, e as duas primeiras vezes
    somem. A pergunta *"quantas vezes travou hoje"* não tem resposta possível a
    partir de uma coluna que só guarda o último estado.

    PURA pelo mesmo motivo de `decidir_travamento`: dá para percorrer as famílias
    de travamento sem banco, sem Redis e sem rede. Quem escreve é
    `_marcar_travamento`; quem **decide** é esta função.

    ⚠️ O `por` sai de `session["destravado_por"]`, que o humano
    (`note_manual_outbound`), o Cérebro e o Sentinela marcam. Sem marca nenhuma
    o crédito é do robô — que continua sendo verdade quando a URA volta a falar
    sozinha.
    """
    rota = str(session.get("playbook_ref") or "")[:180]
    tela = tela_do_travamento(session)
    eventos: List[Dict[str, Any]] = []

    if fase == "needs_human" and fase_anterior != "needs_human":
        eventos.append({
            "tipo": "travamento.aberto",
            "ator": "system",
            "severidade": "warning",
            "mensagem": ("O acionamento parou e precisa de uma pessoa da "
                         f"corretora. Tela: {tela or 'não identificada'}."),
            "payload": {
                "rota": rota, "tela": tela,
                "motivo": str(session.get("reason") or "")[:180],
                "fase_anterior": str(fase_anterior or ""),
            },
        })

    if fase_anterior == "needs_human" and fase and fase != "needs_human":
        por = str(session.get("destravado_por") or "robo")
        if por not in DESTRAVADORES:
            por = "robo"
        carga: Dict[str, Any] = {
            "rota": rota, "tela": tela, "por": por, "fase": str(fase),
        }
        canal = str(session.get("canal_do_destrave") or "")
        if canal:
            carga["canal"] = canal
        if segundos_travado is not None:
            carga["segundos_travado"] = int(segundos_travado)
        eventos.append({
            "tipo": "travamento.destravado",
            "ator": _ATOR_DO_DESTRAVADOR.get(por, "system"),
            "severidade": "info",
            "mensagem": f"Acionamento destravado por: {por}.",
            "payload": carga,
        })

    return eventos


def decidir_travamento(fase: str, fase_anterior: str, *,
                       destravado_por: Optional[str] = None) -> Optional[str]:
    """PURO. O travamento mudou de estado nesta transição de fase? — SPEC-085 F0.

    Devolve o novo `work_runs.unblock_state`, ou `None` quando nada mudou.

    🔴 ESTA FUNÇÃO É A LINHA DE CONTROLE DA §F0.3 ITEM 2, ESCRITA EM CÓDIGO.
    Um acionamento que vai bem — `ura → captured → monitoring` — devolve `None`
    em toda transição, e o run termina com `unblock_state IS NULL`. **Um
    gravador que grava sempre não mede nada**; a prova de que este mede é que
    ele sabe ficar calado.

    PURA porque a §F0.3 cobra o gate por FAMÍLIA de motivo, não por caso: dá
    para percorrer as 16 famílias sem banco, sem Redis e sem rede. Guarda que
    só existe dentro de um `await` é guarda que ninguém consegue rodar
    (`insurer_dispatch_service.acionamento_liberado` diz o mesmo, e pelo mesmo
    motivo).

    ⚠️ O QUE ELA DELIBERADAMENTE NÃO DECIDE: `assumido_por_humano`,
    `resolvido` e `abandonado`. Esses três nascem de um clique, não de uma
    transição de fase, e o dono deles é o BLOCO E. Escrever meia máquina de
    estados aqui é garantir que o BLOCO E a reescreva.
    """
    if fase == "needs_human":
        return "travado"
    # A fuga que a §2.3 da SPEC descreve: `try_route_insurer_inbound` não tem
    # early-return para `needs_human`, então a URA voltando a falar pode
    # devolver o caso a `ura` sozinha. Isso É um destravamento, e até hoje não
    # deixava rastro nenhum.
    if fase_anterior == "needs_human" and fase:
        # 🔴 BLOCO C.1 — A CONDIÇÃO A MAIS, E ELA CONSERTA UMA MENTIRA.
        #
        # 📊 Medido em 25/08/2026: `note_manual_outbound` só tocava no Redis.
        # A atendente respondia a seguradora pelo WhatsApp dela, a fase saía de
        # `needs_human`, e **o robô levava o crédito**. Zero linhas duráveis
        # diziam que uma pessoa tinha trabalhado ali.
        #
        # ⚠️ `robo` explícito continua valendo como robô: a URA voltando a falar
        # sozinha **é** retomada pelo robô, e apagar isso trocaria uma mentira
        # por outra.
        #
        # 🔴 E `cerebro`/`sentinela`/`vigia` TAMBÉM são o robô aqui. A
        # granularidade de qual deles trabalhou mora no EVENTO (C.2/C.3) — a
        # coluna só sabe *robô* ou *pessoa*, e forçá-la a saber mais deixava
        # `travado` gravado para sempre depois de um destrave automático.
        if destravado_por in DESTRAVADORES_HUMANOS:
            return None
        return "retomado_pelo_robo"
    return None


async def _gravar_eventos_de_travamento(db, company_id: str, run_id: str,
                                        fase: str, fase_anterior: str,
                                        session: Dict[str, Any]) -> None:
    """IO. Escreve o que `eventos_do_travamento` decidiu — e cuida do relógio.

    🔴 Best-effort de propósito: contar travamento nunca pode derrubar o
    acionamento que está travando. Mas sai como ERROR, porque sem esta linha
    duas semanas de piloto produzem **zero** linhas sobre onde o produto falha.

    ⚠️ `travado_desde` e `destravado_por` são escritos NA SESSÃO, in place —
    a mesma forma que `session["_checkpoint_fase"]` usa doze linhas abaixo, e
    pelo mesmo motivo: quem salva a sessão é o chamador.
    """
    agora = _agora()
    segundos = None
    desde = str(session.get("travado_desde") or "")
    if desde and fase_anterior == "needs_human":
        try:
            segundos = max(0, int((agora - datetime.fromisoformat(desde)).total_seconds()))
        except Exception:  # noqa: BLE001 — relógio ruim não apaga o evento
            segundos = None

    eventos = eventos_do_travamento(fase, fase_anterior, session,
                                    segundos_travado=segundos)

    # 🔴 A VARREDURA NÃO CONTA O MESMO TRAVAMENTO DE NOVO.
    #
    # ⚠️ `reconciliar_acionamentos_orfaos` roda **de 5 em 5 minutos** e chama
    # com `fase_anterior=""` fixo; a `entrada` que ela passa é o `input_payload`
    # lido do banco, **nunca regravado** — então `travado_desde` não persiste e
    # nada na sessão cortava o laço. Um `needs_human` sem `error_code` emitiria
    # `travamento.aberto` **para sempre**. 📊 Hoje há 0 runs em voo desse
    # workflow: não sangra ainda, passa a sangrar no primeiro.
    #
    # 🔴 **E O FILTRO É SÓ DA VARREDURA — `fase_anterior == ""`.** A primeira
    # versão filtrava toda abertura cuja coluna estivesse em `travado`, e o juiz
    # de confirmação mostrou que isso **engole travamento de verdade**: se a
    # escrita best-effort de `assumido_por_humano` falhar, a coluna fica
    # `travado` para sempre (nada mais a tira — ver `_estado_do_travamento`) e
    # todo travamento seguinte daquele run some da contagem.
    #
    # Uma transição REAL de fase (`ura → needs_human`) é sempre um travamento
    # novo, e conta. Só a varredura, que não sabe de onde veio, precisa perguntar
    # ao banco.
    if not fase_anterior and any(e["tipo"] == "travamento.aberto" for e in eventos):
        if await _estado_do_travamento(db, run_id) == "travado":
            eventos = [e for e in eventos if e["tipo"] != "travamento.aberto"]
    for ev in eventos:
        try:
            await _evento(db, company_id, run_id, ev["tipo"], ev["mensagem"],
                          severidade=ev["severidade"], payload=ev["payload"],
                          ator=ev["ator"])
        except Exception as e:  # noqa: BLE001
            logger.error("[TRAVAMENTO] evento '%s' do run %s NÃO gravado (%s) — "
                         "este travamento não vai ser contado",
                         ev["tipo"], run_id, type(e).__name__)

    if fase == "needs_human" and fase_anterior != "needs_human":
        session["travado_desde"] = agora.isoformat()
        # 🔴 A MARCA É LIMPA NA ABERTURA TAMBÉM — e o painel pegou isto.
        #
        # ⚠️ Limpar só no destrave deixava uma marca posta **fora** de qualquer
        # travamento sobreviver e ser consumida pelo travamento seguinte: um
        # `fromMe` chegando na fase `ura` marcava `humano`, e horas depois a URA
        # voltando a falar sozinha era contada como trabalho de pessoa — e
        # `decidir_travamento` ainda suprimia o `retomado_pelo_robo` que era a
        # verdade.
        #
        # Um travamento começa **sem dono**. Quem destravar recebe o crédito.
        session["destravado_por"] = None
        session["canal_do_destrave"] = None
    if fase_anterior == "needs_human" and fase and fase != "needs_human":
        # O crédito vale para ESTE destravamento. O seguinte começa sem dono —
        # senão o humano de hoje levaria o crédito de amanhã.
        session["destravado_por"] = None
        session["canal_do_destrave"] = None
        session["travado_desde"] = None


async def _estado_do_travamento(db, run_id: str) -> Optional[str]:
    """O que o BANCO diz sobre este travamento agora. `None` = nada, ou não deu.

    ⚠️ Best-effort de propósito, e a direção do erro importa: não conseguir ler
    devolve `None`, que faz o evento sair **como se fosse novo**. Entre contar
    um travamento duas vezes e não contar nenhum, contar demais é o erro
    recuperável — o outro apaga a única evidência que o piloto vai produzir.

    ## ⛔ E ELA NÃO SERVE PARA ATRIBUIR CRÉDITO. FOI TENTADO.

    🔴 `assumido_por_humano` é **grudento**: a escrita de `travado` filtra por
    `IS NULL`, a de `retomado_pelo_robo` por `== 'travado'` e a de `resolvido`
    por `IN ('travado','retomado_pelo_robo')`. **Nenhuma escrita posterior o
    tira.**

    Uma versão desta função creditava o humano sempre que a coluna dizia
    `assumido_por_humano` e a sessão estava sem marca — para resolver o destrave
    pelo painel, que grava no banco e não toca no Redis. ⚠️ O juiz de confirmação
    mostrou o preço: **todo destrave posterior daquele run virava trabalho de
    pessoa**, inclusive os que o robô fez. É a mesma mentira do eco da própria
    voz, com o gatilho invertido.

    > 🔴 O crédito mora na SESSÃO, que é por travamento. A coluna é por RUN, e
    > um valor por run não sabe atribuir N travamentos — é o C.2 inteiro.

    📊 E o que se perde é pouco: o destrave pelo painel sai com `por: robo`, mas
    o `travamento.assumido` que a própria rota grava (com `canal: dashboard`)
    continua na linha do tempo. 📊 A rota do painel não tem **nenhum consumidor
    de UI** (P-251) — hoje esse caminho não é alcançável. Registrado em
    `PENDENCIAS.md`.
    """
    if not run_id:
        return None
    try:
        r = await (db.client.table("work_runs").select("unblock_state")
                   .eq("id", run_id).limit(1).execute())
        linhas = getattr(r, "data", None) or []
        return str(linhas[0].get("unblock_state") or "") or None if linhas else None
    except Exception as e:  # noqa: BLE001
        logger.warning("[TRAVAMENTO] estado durável do run %s ilegível (%s)",
                       run_id, type(e).__name__)
        return None


async def registrar_ato_do_agente(company_id: str, session: Dict[str, Any], *,
                                  agente: str, mensagem: str,
                                  payload: Optional[Dict[str, Any]] = None) -> bool:
    """O que o Cérebro, o Sentinela e o Vigia fizeram — em linha durável.

    🔴 BLOCO C.3. 📊 Hoje só existe `beat("cerebro")` no Redis: um pulso, sem
    caso, sem rota, sem tela e sem histórico. O Founder pediu *"quero ver o
    desempenho do Vigia, Sentinela e do Cérebro"* — e **dois dos três são
    inauditáveis**.

    ⚠️ Best-effort e sem PII: quem guarda o conteúdo da conversa é o Espelho.
    Aqui vai o que uma pessoa precisa para julgar desempenho — qual agente, em
    que rota, em que tela.
    """
    run_id = str(session.get("work_run_id") or "")
    if not run_id or not company_id:
        return False
    try:
        db = await _db()
        if db is None:
            return False
        carga = dict(payload or {})
        carga.setdefault("agente", agente)
        carga.setdefault("rota", str(session.get("playbook_ref") or "")[:180])
        carga.setdefault("tela", tela_do_travamento(session))
        await _evento(db, company_id, run_id, f"agente.{agente}", mensagem,
                      payload=carga, ator="agent")
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("[AGENTE %s] ato não registrado (%s)", agente, type(e).__name__)
        return False


async def _marcar_travamento(db, run_id: str, fase: str, fase_anterior: str,
                             company_id: str = "",
                             session: Optional[Dict[str, Any]] = None) -> None:
    """IO. Aplica a decisão de `decidir_travamento` sem pisar em decisão humana.

    🔴 Os dois filtros são a parte que importa, e não são estilo:

      `travado`             só quando a coluna está NULL — um caso que já foi
                            assumido por uma pessoa e volta a travar continua
                            com o nome de quem o assumiu.
      `retomado_pelo_robo`  só quando estava exatamente em `travado` — se uma
                            pessoa assumiu e o caso andou, quem andou foi ela,
                            e creditar o robô é a mesma classe de mentira do
                            `dossier_sent = True` incondicional que custou o
                            "Dossiê entregue à equipe" de 18/08.

    Best-effort: falhar aqui nunca derruba o acionamento — mas sai como ERROR,
    porque sem esta linha o travamento volta a ser invisível, que é o defeito
    inteiro desta SPEC.
    """
    novo = decidir_travamento(fase, fase_anterior,
                              destravado_por=str(session.get("destravado_por") or "")
                              if session else None)
    if not run_id:
        return

    # 🔴 BLOCO C.2 — OS EVENTOS SAEM MESMO QUANDO A COLUNA NÃO MUDA.
    #
    # ⚠️ E é exatamente esse o furo que o bloco fecha: um run que trava, destrava
    # e trava de novo passa duas vezes por aqui com `novo == "travado"`, e a
    # SEGUNDA não muda coluna nenhuma (o filtro `IS NULL` a barra, e com razão).
    # Se os eventos dependessem de `novo`, o segundo travamento seria invisível.
    if session is not None:
        await _gravar_eventos_de_travamento(db, company_id, run_id, fase,
                                            fase_anterior, session)

    if not novo:
        return
    try:
        q = db.client.table("work_runs").update({"unblock_state": novo}).eq("id", run_id)
        if novo == "travado":
            q = q.is_("unblock_state", "null")
        else:
            q = q.eq("unblock_state", "travado")
        await q.execute()
    except Exception as e:  # noqa: BLE001
        logger.error("[ACIONAMENTO DURAVEL] run %s nao recebeu unblock_state='%s' (%s) — "
                     "o travamento deste caso nao vai aparecer na Fila",
                     run_id, novo, type(e).__name__)


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

        # 🔴 O GÊMEO É BEST-EFFORT. O PAYLOAD NÃO É.
        #
        # A primeira versão da FASE 1 chamava o mascarador DENTRO do dicionário
        # da etapa, e portanto dentro do `try` grande desta função. Um import
        # que falhasse — um dublê de teste, uma dependência ausente — derrubava
        # o checkpoint INTEIRO, e o acionamento voltava a morar só no Redis:
        # o defeito que esta SPEC existe para matar, reintroduzido por um
        # conserto de privacidade.
        #
        # ⚠️ A pergunta certa é qual falha é pior. Sem o gêmeo, a coluna fica
        # nula e o backfill a preenche depois. Sem o payload, o acionamento
        # some. **Perder o gêmeo é recuperável; perder o retrato não.**
        try:
            redigido = _pii().retrato_para_humano(session)
        except Exception as e:  # noqa: BLE001
            logger.error("[ACIONAMENTO DURAVEL] retrato mascarado indisponível "
                         "(%s) — a etapa vai SEM o gêmeo, e o payload sobrevive",
                         type(e).__name__)
            redigido = None

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
        if redigido is not None:
            # 🔴 O GÊMEO — SPEC-085 FASE 1. O `output_summary` acima é o PAYLOAD
            # DE RESTAURAÇÃO e continua CRU: `_ultimo_retrato` →
            # `sessao_restaurada` → `render_reply` → a URA. Mascarar ali faz um
            # acionamento restaurado responder `...4725` à seguradora.
            # Aqui vai a versão que uma PESSOA pode ler — e é a única que a
            # tela de destravamento (BLOCO E) e o dossiê devem consultar.
            etapa["output_redacted"] = redigido
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
            # 🔴 BLOCO A.3, a metade que faltava: O ERRO VENCIDO TAMBÉM SAI.
            #
            # 📊 Medido em produção: o run `448d3f08` está `completed` na fase
            # `test_aborted` — o que é CORRETO — carregando
            # `error_code = needs_human:missing_slots:problema_eletrico_opcao`,
            # que é de um travamento ANTERIOR do mesmo caso. O campo era escrito
            # ao travar e nunca limpo ao destravar.
            #
            # ⚠️ E a história não se perde: a etapa `needs_human` continua em
            # `work_steps` e a transição em `work_events`. O `error_code` do RUN
            # descreve o **desfecho**, não um momento — e um desfecho concluído
            # não tem erro.
            campos["error_code"] = None
            campos["error_message"] = None
        if fase == "needs_human":
            campos["error_code"] = f"needs_human:{str(session.get('reason') or '')}"[:180]
            campos["error_message"] = ("O acionamento precisa de uma pessoa da corretora "
                                       "para continuar.")
            # 🔴 BLOCO A.3 — OS TRÊS CAMPOS PASSAM A CONCORDAR.
            #
            # 📊 O defeito, medido em produção: um dos dois `needs_human`
            # duráveis carrega TRÊS verdades diferentes na mesma linha —
            #
            #   error_code        needs_human:missing_slots:problema_eletrico_opcao
            #   current_step_key  test_aborted
            #   result_summary    "Simulação completa"
            #
            # A causa é que `finished_at` e `result_summary` são escritos quando
            # a fase é terminal e **nunca limpos** quando ela deixa de ser. Um
            # acionamento que passou por `test_aborted` e caiu em `needs_human`
            # fica com o resumo do desfecho anterior.
            #
            # ⚠️ `None` é escrita, não omissão: omitir manteria o valor velho, e
            # é isso que está errado.
            campos["finished_at"] = None
            campos["result_summary"] = (
                "Parou e precisa de uma pessoa da corretora. Motivo: "
                f"{str(session.get('reason') or 'não registrado')}")[:400]
        await db.client.table("work_runs").update(campos).eq("id", run_id).execute()

        await _marcar_travamento(db, run_id, fase,
                                 str(session.get("_checkpoint_fase") or ""),
                                 company_id=str(company_id), session=session)

        if fase != str(session.get("_checkpoint_fase") or ""):
            await _evento(db, company_id, run_id, "step.completed",
                          f"Acionamento agora em '{fase}'.",
                          severidade="warning" if fase == "needs_human" else "info",
                          payload={"fase": fase, "motivo": str(session.get("reason") or "")})
            session["_checkpoint_fase"] = fase

        # 🔴 SPEC-086 BLOCO A — O ATENDIMENTO TERMINA, E O PRODUTO SABE.
        #
        # 📊 Medido em 26/08: `conversations.resolvido_em` tem **0 linhas em
        # 671**. O produto nunca marcou um atendimento como resolvido — então
        # *"acabou bem"* e *"o cliente desistiu e foi embora"* são, para o
        # banco, o MESMO estado.
        #
        # ⚠️ E só DUAS fases terminam atendimento: `resolvido` (o serviço foi
        # prestado) e `encaminhado` (o entregável está em mãos — P-46).
        # ⛔ `needs_human` NÃO entra: o acionamento parou, mas tem gente
        # esperando. ⛔ `test_aborted` NÃO entra: é simulação.
        #
        # ⛔ **Best-effort, e por fora do `return`:** a marca de fim vale menos
        # que o checkpoint. Se ela falhar, o acionamento continua espelhado.
        await _marcar_fim_do_atendimento(db, company_id, session, fase)

        # 🔴 SPEC-086 BLOCO B — E A ESPERA PASSA A NASCER.
        #
        # ⚠️ Sem um escritor, `work_waits` fica VAZIA: o vigia varre nada e a
        # sexta-feira responde `ainda_esperam: 0` para sempre. Os BLOCOS B e C
        # viram enfeite.
        #
        # 📊 E `needs_human` é o sinal MEDIDO que já existe: é a fase em que o
        # acionamento parou e **tem gente esperando uma pessoa da corretora**.
        # A SPEC-093 já grava `travamento.aberto` aqui; esta linha dá à mesma
        # transição um objeto com PRAZO, que é o que torna a espera varrível.
        #
        # ⚠️ O prazo sai de `HANDOFF_ALERTA_MINUTOS` — **a mesma variável do
        # vigia de handoff**, de propósito. Dois números para "quanto tempo é
        # espera demais" divergiriam, e o grupo receberia dois alarmes com
        # cadências diferentes sobre a mesma conversa (§5).
        await _abrir_espera_do_travamento(db, company_id, session, fase)

        # 🔴 SPEC-097.1 U1.1/U5.1 — E O ACIONAMENTO VIRA UMA ESPERA COM NOME.
        #
        # 📊 Medido em 05/09/2026: `work_waits` tem ZERO linhas na vida e
        # `work_steps` com `step_type='dispatch_phase'` são 12 em todo o banco,
        # sem um `captured` sequer. Não é que falte escritor: é que o único
        # escritor que existia só conhecia `needs_human`. Depois do protocolo,
        # o produto não sabia de quem estava esperando — e "e a previsão do
        # vidro?" não tinha resposta possível.
        #
        # ⚠️ **O mesmo funil, um ponto só.** 📊 `registrar_checkpoint` é
        # chamado de UM lugar (`save_active_dispatch:306`); os 27 escritores de
        # `session["state"]` passam todos por aqui. Nenhum motor novo (§5).
        await _pos_acionamento_do_checkpoint(db, company_id, session, fase)
        return run_id
    except Exception as e:  # noqa: BLE001
        # ERRO, não warning: falhar aqui devolve o produto ao defeito que esta
        # SPEC existe para matar — o acionamento voltando a morar só no Redis.
        logger.error("[ACIONAMENTO DURAVEL] checkpoint da fase '%s' NAO gravado (%s) — "
                     "esta sessao esta sem espelho durável", fase, type(e).__name__)
        return None


#: 📊 O mesmo padrão do vigia de handoff (`handoff_watchdog.py:41`). ⚠️ Não é
#: coincidência: é a MESMA pergunta — *"quanto tempo de espera já constrange?"*
_ESPERA_DO_TRAVAMENTO_MIN = 30

#: O escopo da espera aberta por travamento. ⚠️ Fixo de propósito: um wait
#: ATIVO por escopo, e um acionamento travado é UMA espera, não uma por fase.
_ESCOPO_DO_TRAVAMENTO = "acionamento"


#: 🔴 SPEC-097.1 U1.1 — quanto tempo se espera a seguradora quando ela NÃO deu
#: previsão. ⚠️ **48 horas, e o número mudou por medição:** 📊 o caso do acervo
#: dura **6,9 dias** (mediana), e o padrão anterior de +24 h fechava o
#: atendimento no dia seguinte com a seguradora ainda devendo resposta ([2] do
#: red team). ⛔ E o padrão é só padrão: quem manda é
#: `companies.acionamento_profile.prazo_pos_acionamento_horas`.
_ESPERA_DO_POS_ACIONAMENTO_MIN = 48 * 60


def _env_int_espera_pos() -> int:
    import os

    try:
        n = int(str(os.getenv("POS_ACIONAMENTO_ESPERA_MINUTOS") or "").strip()
                or _ESPERA_DO_POS_ACIONAMENTO_MIN)
    except Exception:  # noqa: BLE001
        return _ESPERA_DO_POS_ACIONAMENTO_MIN
    return max(1, n)


#: 📊 O número que o follow-up de sessão usava desde 12/07/2026, escrito à mão
#: dentro de `_followup_schedule`. ⚠️ Vira constante para que a mesma pergunta
#: — *"quanto tempo depois do prestador se pergunta se deu certo?"* — tenha UM
#: número, e para que a variável de operação possa vencê-lo sem editar código.
_ESPERA_DO_FOLLOWUP_MIN = 45

#: O intervalo entre a pergunta e o encerramento carinhoso. Era `2h30` literal.
_ESPERA_DO_ENCERRAMENTO_MIN = 150


def _espera_do_followup_min() -> int:
    """Minutos entre o horário combinado e o *"o prestador foi?"*.

    ⚠️ **O padrão daqui NÃO é o de `_env_int_espera_pos`**, e a diferença é de
    propósito: aquele responde *"quanto tempo se espera a SEGURADORA responder"*
    (48 h, medido no acervo); este responde *"quanto tempo depois do serviço se
    pergunta se deu certo"* (45 min). Um padrão só faria o produto perguntar
    dois dias depois — ou cobrar a seguradora 45 minutos depois de acionar.
    🔴 Em produção os dois são vencidos pela MESMA variável de operação
    (`POS_ACIONAMENTO_ESPERA_MINUTOS=90`), que é o que o Founder ajusta.
    """
    import os

    if str(os.getenv("POS_ACIONAMENTO_ESPERA_MINUTOS") or "").strip():
        return _env_int_espera_pos()
    return _ESPERA_DO_FOLLOWUP_MIN


async def _minutos_de_espera_do_perfil(db, company_id: str) -> int:
    """O prazo da CORRETORA, em minutos — `acionamento_profile` (U1.1).

    ⛔ **Nunca levanta e nunca fica sem resposta**: corretora não lida devolve
    o padrão. Um prazo ausente não pode custar a espera.
    """
    import os

    from app.atendimento.pos_acionamento import prazo_pos_acionamento_horas

    # ⚠️ A variável de ambiente é a saída de emergência da operação e vence
    #    tudo — mas só quando alguém a escreveu. Ela existia antes desta SPEC.
    if str(os.getenv("POS_ACIONAMENTO_ESPERA_MINUTOS") or "").strip():
        return _env_int_espera_pos()

    try:
        achado = await (db.client.table("companies")
                        .select("id, acionamento_profile")
                        .eq("id", str(company_id)).limit(1).execute())
        companhia = (achado.data or [{}])[0] or {}
    except Exception as erro:  # noqa: BLE001
        logger.warning("[POS-ACIONAMENTO] prazo da corretora não lido (%s) — "
                       "usando o padrão", type(erro).__name__)
        companhia = {}
    return max(1, int(prazo_pos_acionamento_horas(companhia)) * 60)


def _prazo_do_agendamento(captured: Dict[str, Any]) -> str:
    """O que a seguradora PROMETEU vira o prazo da espera — ou `""`.

    🔴 **Lê o formato REAL da sessão** (`extract_capture_anchors`,
    `corridor_playbooks:8964`): `schedule` é um DICIONÁRIO — `{day, at}` no
    auto, `{day, from, to}` na janela da Porto, `{day, periodo}` na
    residencial — e `eta_minutes` é o número de minutos, em texto.

    ⚠️ 📊 Achado [1] do red team: este bloco lia `session['protocolo'] /
    ['previsao'] / ['documentos_pendentes']`, **chaves que nenhum escritor
    produz** — o único hit do grep era o próprio leitor. A espera nunca nascia,
    e o guarda ficava verde porque fabricava a sessão imaginada (§9.4: o texto
    da tela vem do acervo, não da imaginação).

    ⛔ E a data sai por `instante_br`, nunca por `str()`: `'12/09/2026'` é 12 de
    setembro em toda ferramenta, não 9 de dezembro em uma delas ([3]).
    """
    from app.services.o_fim_do_atendimento import instante_br

    agenda = (captured or {}).get("schedule")
    if isinstance(agenda, dict) and str(agenda.get("day") or "").strip():
        # 🔴 A HORA SUMIA — medido em 08/09/2026, aqui mesmo.
        #
        # 📊 `"17h".replace("h", ":").strip(":")` é `"17"`, e `_DATA_BR` exige
        # um separador (`(\d{1,2})[:h](\d{1,2})?`). Sem ele a linha inteira não
        # casava, o `instante_br` devolvia `""` e o ramo de baixo salvava o dia
        # — **à meia-noite**:
        #
        #     {'at': '17h'}            -> 2026-09-09T03:00Z  (00:00 em SP)
        #     {'from': '8 h','to':...} -> 2026-09-09T03:00Z  (00:00 em SP)
        #     {'at': '14:30'}          -> 2026-09-09T17:30Z  ✓ o único que passava
        #
        # ⚠️ E não era caso raro: a âncora de auto captura `(\d{1,2}[:h]\d{0,2})`
        # — `\d{0,2}` permite ZERO dígitos, que é exatamente `"17h"` — e a
        # janela da Porto captura `(\d{1,2}\s?h)`, que é **sempre** `"8 h"`.
        # A janela da Porto perdia a hora em 100% dos casos.
        #
        # 🔴 Agora a hora é NORMALIZADA para `HH:MM` antes de ir ao motor —
        # `instante_br` continua sendo o único parser (§5).
        hora = str(agenda.get("at") or agenda.get("from") or "").strip().lower()
        texto = str(agenda["day"]).strip()
        if hora:
            achado = re.match(r"^(\d{1,2})\s*[:h]?\s*(\d{1,2})?", hora)
            if achado:
                texto = "%s %s:%02d" % (texto, achado.group(1),
                                        int(achado.group(2) or 0))
        # ⚠️ `periodo` ('manhã'/'tarde') fica de fora do prazo de propósito:
        #    ele não é uma hora, e transformá-lo em uma seria inventar (R3).
        instante = instante_br(texto)
        if instante:
            return instante
        instante = instante_br(str(agenda["day"]).strip())
        if instante:
            return instante

    minutos = str((captured or {}).get("eta_minutes") or "").strip()
    if minutos.isdigit():
        from datetime import datetime, timedelta, timezone

        return (datetime.now(timezone.utc)
                + timedelta(minutes=max(1, int(minutos)))).isoformat()
    return ""


async def _pos_acionamento_do_checkpoint(db, company_id: str,
                                         session: Dict[str, Any],
                                         fase: str) -> None:
    """O acionamento entregou algo — abre a espera e conta a novidade (R4/R10).

    ⛔ **Nunca levanta**: um erro aqui não pode custar o checkpoint, que é a
    única coisa que impede o acionamento de voltar a morar só no Redis.

    ⛔ **`encaminhado` NÃO entra** (E5). Ele está em `MOTIVO_DO_ESTADO` e
    `_marcar_fim_do_atendimento` acabou de ENCERRAR o atendimento algumas
    linhas acima, no mesmo checkpoint: abrir uma espera para um atendimento
    encerrado é criar trabalho que ninguém vai fazer.

    ⛔ **E o escopo do travamento continua intocado** (E4): a espera nasce em
    `pos_acionamento`, senão o ramo `else` do helper de cima a satisfaria no
    mesmo instante em que ela nascesse.
    """
    try:

        from app.atendimento import acompanhamento, pos_acionamento
        from app.services.o_fim_do_atendimento import (
            ESCOPO_POS_ACIONAMENTO, ESPERANDO_SEGURADORA, abrir_espera,
        )

        # 🔴 AS DUAS FASES, escritas em POSITIVO. ⛔ `encaminhado` fica de fora
        #    (E5) e `needs_human` também: aquela é a espera do TRAVAMENTO, e
        #    ela tem escopo próprio.
        abre_espera = str(fase or "") in ("captured", "monitoring")
        if not abre_espera:
            return

        conversa = str(session.get("mirror_conversation_id") or "").strip()
        if not conversa or not _UUID.match(conversa):
            return

        # 🔴 O FORMATO REAL, e ele é UM SÓ: `session['captured']`, escrito por
        #    `insurer_dispatch_service:2323` a partir de
        #    `corridor_playbooks.extract_capture_anchors`. Nada de `slots`:
        #    📊 `session['slots']` é o que a URA **pede** (placa, cep, `*_opcao`),
        #    nunca o que a seguradora **devolve**.
        captured = session.get("captured")
        captured = captured if isinstance(captured, dict) else {}
        protocolo = str(captured.get("protocol") or "").strip()
        agendamento = bool(str((captured.get("schedule") or {}).get("day") or "").strip()
                           if isinstance(captured.get("schedule"), dict) else False)
        eta = str(captured.get("eta_minutes") or "").strip()
        if not (protocolo or agendamento or eta):
            # ⚠️ Fase sem entregável nenhum não é espera: é o corredor no meio
            #    do caminho. Abrir aqui encheria `work_waits` de linhas que
            #    ninguém consegue satisfazer (o PAR [A2] mede exatamente isto).
            return

        # ---- de quem se espera --------------------------------------------
        #
        # ⚠️ R2/E13: `esperando_oficina` NÃO é um kind. "a loja" é palavra de
        #    texto humano; o banco conhece três kinds e só três.
        #
        # ⛔ **`esperando_cliente` fica de fora, e é por FALTA DE ESCRITOR.**
        #    📊 05/09/2026: o corredor não registra em lugar nenhum que pediu
        #    documento ao segurado — `extract_capture_anchors` lê `protocol`,
        #    `password`, `eta`, `ticket_de_entrada`, `schedule*` e
        #    `tracking_link`, e nenhuma âncora de documento existe (grep por
        #    'documento' em `corridor_playbooks.py`: só texto de instrução ao
        #    cliente). Inventar aqui a chave que ninguém escreve é exatamente o
        #    defeito [1] que esta função acabou de pagar. Quando houver escritor,
        #    o kind entra — está em `KINDS` esperando (P-097.1-DOC).
        kind = ESPERANDO_SEGURADORA

        # ---- até quando ----------------------------------------------------
        #
        # ⚠️ `prometido` e `vence` são coisas diferentes de propósito: o
        # primeiro é o que a SEGURADORA disse; o segundo é o prazo da espera,
        # que na falta de promessa é o da corretora. Só o primeiro é notícia.
        prometido = _prazo_do_agendamento(captured)

        # ---- o estado ANTERIOR, lido ANTES de a nova espera nascer ---------
        #
        # 🔴 É a comparação que decide se há NOVIDADE (R10-b). Ler depois de
        # abrir compararia a linha nova com ela mesma, e o cliente nunca seria
        # avisado de nada.
        anterior: Dict[str, Any] = {}
        try:
            achado = await (db.client.table("work_waits")
                            .select("id, vence_em, kind, scope, status, created_at")
                            .eq("company_id", str(company_id))     # 🔴 §7
                            .eq("conversation_id", conversa)
                            .eq("scope", ESCOPO_POS_ACIONAMENTO)
                            .eq("status", "ativo").limit(1).execute())
            anterior = (achado.data or [{}])[0] or {}
        except Exception as erro:  # noqa: BLE001
            logger.warning("[POS-ACIONAMENTO] estado anterior não lido (%s)",
                           type(erro).__name__)

        # ⛔ ESPERA JÁ ABERTA E NADA PROMETIDO = NADA A FAZER. Sem esta linha,
        #    cada checkpoint de `monitoring` empurraria o prazo 48 h para a
        #    frente: a espera nunca venceria, e o vigia nunca cobraria ninguém.
        if anterior and not prometido:
            return

        # 🔴 A ESPERA VENCE QUANDO O FOLLOW-UP DEVE SAIR — não quando o
        # prestador chega. Decisão do Founder, 08/09/2026.
        #
        # ⚠️ **`vence_em` mudou de significado, e é de propósito.** Ele era o
        # instante PROMETIDO: a espera vencia às 14h, o vigia disparava às 14h e
        # o segurado recebia *"e aí, deu tudo certo?"* no exato minuto em que o
        # guincho estava encostando. Agora ele é o instante do FOLLOW-UP —
        # combinado + `POS_ACIONAMENTO_ESPERA_MINUTOS`, dentro de 08:00–19:00.
        #
        # ⛔ E por isso a frase abaixo passou a dizer `prometido`, nunca `vence`:
        # depois desta linha os dois são coisas diferentes, e anunciar ao
        # segurado a hora em que o ROBÔ vai perguntar, chamando-a de "previsão
        # da seguradora", é o campo que mente da `CLAUDE.md` §12.1.
        # ⚠️ **O PERÍODO VEM PRIMEIRO, e é medido.** 📊 08/09/2026: para
        # `{day, periodo}` o `_prazo_do_agendamento` devolve o dia **à
        # meia-noite** (ele recusa o período e cai no ramo do dia). Usar isso
        # como base mandaria o follow-up às 08:00 da manhã perguntar sobre um
        # serviço marcado para a TARDE. O fim do período é a base honesta.
        #
        # ⛔ E ele continua não sendo PREVISÃO: 'tarde' não vira "às 18h" na
        # boca do produto — vira só a hora em que o produto PERGUNTA.
        combinado = acompanhamento.fim_do_periodo_combinado(
            captured.get("schedule"))
        if combinado is None and prometido:
            from datetime import datetime as _dt

            combinado = _dt.fromisoformat(prometido)
        # 🔴 **DUAS ESPERAS, DUAS PERGUNTAS — e misturar as duas custou o
        # gate zero da 097.1.** 📊 Medido em 08/09/2026:
        #
        #     combinado CONHECIDO    → "quanto tempo depois do serviço eu pergunto
        #                               se deu certo?"  45 min (90 em produção)
        #     combinado DESCONHECIDO → "quanto tempo eu espero a SEGURADORA
        #                               responder?"      48 h — o caso do acervo
        #                               dura 6,9 dias (`_ESPERA_DO_POS_ACIONAMENTO_MIN`)
        #
        # ⛔ Somar as 48 h a um agendamento das 14:00 joga a pergunta para
        # **dois dias depois** do guincho. E o estrago não para aí: como o dia
        # muda, o comparador de novidade acusa mudança onde nada mudou, e o
        # segurado recebe *"a seguradora atualizou a previsão"* sobre a MESMA
        # data — foi assim que o `[M1p]` de `test_o_caso_se_explica_sozinho`
        # ficou vermelho, e ele estava certo.
        #
        # ⚠️ Em produção os dois viram 90: `POS_ACIONAMENTO_ESPERA_MINUTOS`
        # vence os dois padrões, e é essa a variável que o Founder ajusta.
        if combinado is not None:
            minutos = _espera_do_followup_min()
        else:
            minutos = await _minutos_de_espera_do_perfil(db, str(company_id))
        vence = acompanhamento.calcular_envio_do_follow_up(
            _agora(), combinado, minutos).isoformat()

        # 🔴 A NOVIDADE se mede com a MESMA RÉGUA com que se fala (§9.4): a
        # frase entrega `_dia_e_mes(vence)`, então é o DIA que decide se houve
        # notícia. ⛔ Comparar o instante cru mandaria a MESMA frase duas vezes
        # quando só o fuso da conversão mudasse — e frase repetida ao segurado
        # é o defeito [2b] noutro lugar.
        mudou = (bool(anterior) and bool(prometido)
                 and pos_acionamento._dia_e_mes(anterior.get("vence_em"))
                 != pos_acionamento._dia_e_mes(vence))

        await abrir_espera(db, company_id=str(company_id),
                           conversation_id=conversa,
                           kind=kind,
                           scope=ESCOPO_POS_ACIONAMENTO,
                           vence_em_iso=str(vence),
                           work_run_id=str(session.get("work_run_id") or ""))

        # ---- a NOVIDADE (U5.1) — pela PORTA ÚNICA, nunca por saída própria --
        if not mudou:
            return
        # ⚠️ O DIA que o segurado ouve é o PROMETIDO pela seguradora, não o do
        #    follow-up. `vence` só volta a ser a fonte quando não há promessa —
        #    e aí os dois coincidem no que importa, que é o dia.
        quando = pos_acionamento._dia_e_mes(prometido or vence)
        texto = ("Novidade no seu caso: a seguradora atualizou a previsão"
                 + (" para %s." % quando if quando else ".")
                 + " Se mudar de novo, eu te aviso aqui, sem você precisar "
                   "perguntar.")
        await acompanhamento.entregar_novidade(
            db, company_id=str(company_id), conversation_id=conversa,
            texto=texto, gatilho="corredor")
    except Exception as erro:  # noqa: BLE001
        logger.warning("[POS-ACIONAMENTO] espera da fase '%s' não registrada (%s) — "
                       "o acionamento seguiu normalmente", fase, type(erro).__name__)


async def _abrir_espera_do_travamento(db, company_id: str,
                                      session: Dict[str, Any], fase: str) -> None:
    """`needs_human` abre uma espera com PRAZO — SPEC-086 BLOCO B.

    ⛔ **Nunca levanta**, e o `UNIQUE` violado não é erro: significa que este
    acionamento **já estava esperando**, que é exatamente o que o índice
    parcial existe para garantir.

    ⚠️ **E sair de `needs_human` SATISFAZ a espera.** Sem isso, o vigia
    cobraria uma conversa que voltou a andar sozinha — e alarme falso é como
    se ensina uma equipe a ignorar alarme.
    """
    try:
        from datetime import timedelta

        from app.services.o_fim_do_atendimento import (
            ESPERANDO_HUMANO, abrir_espera, satisfazer_espera,
        )

        conversa = str(session.get("mirror_conversation_id") or "").strip()
        if not conversa or not _UUID.match(conversa):
            return

        if fase == "needs_human":
            minutos = _env_int_espera()
            vence = (_agora() + timedelta(minutes=minutos)).isoformat()
            await abrir_espera(db, company_id=str(company_id),
                               conversation_id=conversa,
                               kind=ESPERANDO_HUMANO,
                               scope=_ESCOPO_DO_TRAVAMENTO,
                               vence_em_iso=vence,
                               work_run_id=str(session.get("work_run_id") or ""))
        else:
            # ⚠️ Qualquer OUTRA fase satisfaz: o acionamento voltou a andar.
            #    🔴 `satisfazer_espera` filtra por `status='ativo'`, então chamar
            #    quando não há espera é um no-op barato — e barato o bastante
            #    para não valer um estado novo na sessão só para evitá-lo.
            await satisfazer_espera(db, company_id=str(company_id),
                                    conversation_id=conversa,
                                    scope=_ESCOPO_DO_TRAVAMENTO,
                                    por="robo")
    except Exception as erro:  # noqa: BLE001
        logger.warning("[ESPERA] não registrada para a fase '%s' (%s) — o "
                       "acionamento seguiu normalmente", fase, type(erro).__name__)


def _env_int_espera() -> int:
    """O MESMO número do vigia de handoff. ⚠️ Dois números para "quanto tempo
    é espera demais" divergiriam, e o grupo receberia dois alarmes."""
    import os

    try:
        n = int(str(os.getenv("HANDOFF_ALERTA_MINUTOS") or "").strip()
                or _ESPERA_DO_TRAVAMENTO_MIN)
    except Exception:  # noqa: BLE001
        return _ESPERA_DO_TRAVAMENTO_MIN
    return max(1, n)


async def _marcar_fim_do_atendimento(db, company_id: str,
                                     session: Dict[str, Any], fase: str) -> None:
    """A conversa desta sessão terminou? — SPEC-086 BLOCO A.

    ⛔ **Nunca levanta.** Chamada de dentro do `try` de `registrar_checkpoint`,
    mas com `try` próprio: uma falha aqui não pode virar *"checkpoint da fase
    NÃO gravado"* no log, que é um alarme de outra gravidade.

    ⚠️ **A âncora é a CONVERSA, e ela pode faltar.** `mirror_conversation_id` é
    vazio com `DISPATCH_MIRROR=0`. Sem ela, não há o que marcar — e isso é
    ausência, não erro.
    """
    try:
        from app.services.o_fim_do_atendimento import (
            marcar_fim, motivo_do_estado_do_dispatch,
        )

        motivo = motivo_do_estado_do_dispatch(fase)
        if not motivo:
            return
        # 🔴 SPEC-097 U1.2 — o ESPELHO deixou de ser a única âncora.
        #
        # 📊 Medido em 05/09/2026: com `DISPATCH_MIRROR=0` esta função saía sem
        # marcar nada, e o atendimento terminava sem que o produto soubesse. O
        # desfecho mora no EPISÓDIO (`attendance_sessions`), então quando a
        # sessão de acionamento conhece o episódio ele basta — a conversa é
        # espelhada por `marcar_fim` quando a junção R3 existir.
        conversa = str(session.get("mirror_conversation_id") or "").strip()
        if not _UUID.match(conversa or ""):
            conversa = ""
        # 🔴 E QUANDO A SESSÃO NÃO CONHECE O EPISÓDIO, ELA O RESOLVE.
        #    Sem esta linha `episodio` era SEMPRE `""` (📊 zero escritas da
        #    chave em todo o backend) e o parágrafo acima descrevia um caminho
        #    que nenhuma execução alcançava.
        episodio = await _episodio_do_atendimento(db, str(company_id), session)
        if not conversa and not episodio:
            logger.info("[FIM] fase '%s' terminou o acionamento, mas esta sessão "
                        "não tem conversa espelhada nem episódio — nada a marcar", fase)
            return
        await marcar_fim(db, company_id=str(company_id), motivo=motivo,
                         conversation_id=conversa, attendance_session_id=episodio)
    except Exception as erro:  # noqa: BLE001
        logger.warning("[FIM] a conversa não foi marcada como encerrada (%s) — "
                       "o acionamento seguiu normalmente", type(erro).__name__)


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
            # 🔴 `unblock_state` NÃO ENTRA AQUI. Ver `_fechar_travamento`, logo
            # abaixo — e leia o porquê antes de "simplificar" trazendo de volta.
        }).eq("id", run_id).execute())
        if final == "completed":
            await _fechar_travamento(db, run_id)
        await _evento(db, company_id, run_id,
                      "run.succeeded" if final == "completed" else "run.cancelled",
                      motivo, payload={"fase": fase})
    except Exception as e:  # noqa: BLE001
        logger.error("[ACIONAMENTO DURAVEL] run %s nao foi encerrado (%s)",
                     run_id, type(e).__name__)


async def _fechar_travamento(db, run_id: str) -> None:
    """Fecha a marca de travamento — **só o desfecho BOM, e só onde ela existe.**

    🔴 ESTA FUNÇÃO NASCEU DE UM CONSERTO QUE VIROU DEFEITO, e a história inteira
    é o motivo de ela ser tão estreita.

    A primeira versão escrevia, dentro do UPDATE de `_encerrar_work_run`::

        "unblock_state": "resolvido" if final == "completed" else "abandonado"

    com **só** `.eq("id", run_id)`. Era a mesma escrita sem guarda que este
    mesmo painel tinha acabado de tirar da reconciliação, reintroduzida ao lado.
    O juiz de confirmação mediu dois gatilhos vivos, os dois normais:

    📊 **(i) supersede.** `needs_human` com `reason == "insurer_closed"` chama
    `clear_active_dispatch` no mesmo turno. Fase `needs_human` ⇒
    `final = "cancelled"` ⇒ a marca `travado` virava `abandonado`::

        reason=insurer_closed  antes='travado'  depois='abandonado'  na_Fila=False

    `insurer_closed` é *"a URA derrubou a conversa"* — a causa mais comum de
    travamento e a única família que retoma.

    📊 **(ii) sessão nova na mesma seguradora.** `stale` inclui `needs_human`,
    então uma sessão travada é stale **na hora**, sem esperar os 45 min. Segurado
    A trava; minutos depois o segurado B pede chaveiro na mesma seguradora; o
    supersede arquiva o caso de A. **Ninguém nunca mais é chamado.**

    ⚠️ E `abandonado` é o verbo do HUMANO, não da máquina: é o que o botão
    *arquivar* grava, e `test_arquivar_exige_motivo_escrito` obriga a ter motivo
    escrito, porque *"arquivar é dizer 'ninguém vai continuar isto'"*. A máquina
    estava arquivando sem motivo nenhum, por cima do nome de quem assumiu.

    ## A regra, então, é ESTREITA e tem três metades

    1. **Só `resolvido`.** A máquina nunca abandona. Um travamento que o
       acionamento não resolveu **continua na Fila**, que é o produto inteiro
       desta SPEC: alguém tem de ligar para aquela pessoa.
    2. **Só onde a marca EXISTE** (`travado` ou `retomado_pelo_robo`). Sem isso,
       todo acionamento bem-sucedido gravaria `resolvido` e destruiria a
       propriedade que `decidir_travamento` declara: *acionamento que vai bem
       termina com `unblock_state IS NULL`*.
    3. **Nunca por cima de `assumido_por_humano`.** O `IN` não alcança esse
       valor — é a mesma assimetria de `_marcar_travamento`, pelo mesmo motivo.
    """
    try:
        await (db.client.table("work_runs")
               .update({"unblock_state": "resolvido"})
               .eq("id", run_id)
               .in_("unblock_state", ["travado", "retomado_pelo_robo"])
               .execute())
    except Exception as e:  # noqa: BLE001
        # Falha aqui deixa a marca como está — o caso continua VISÍVEL na Fila.
        # É o lado seguro: sobra um caso para conferir, não falta um.
        logger.warning("[ACIONAMENTO DURAVEL] run %s: marca de travamento nao "
                       "foi fechada (%s) — ele segue na Fila", run_id, type(e).__name__)


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
                     # 🔴 BLOCO A.2 — O TRAVAMENTO SAI DA JANELA DA VARREDURA.
                     #
                     # Depois do conserto acima, um `needs_human` fica em
                     # `waiting_input`, que ESTÁ em `_STATUS_EM_VOO_WORK_RUN`.
                     # Sem este filtro ele seria revarrido a cada boot, para
                     # sempre — e com as 73 rotas ligadas a janela de 50
                     # encheria de casos estacionados, fazendo os órfãos DE
                     # VERDADE deixarem de ser detectados. Seria trocar um
                     # silêncio por outro.
                     #
                     # ⚠️ 📊 A FORMA DESTE FILTRO FOI MEDIDA, E A ÓBVIA ESTAVA
                     # ERRADA: `.not_.like("error_code", "needs_human:%")` não
                     # levanta erro e devolveu **0 de 4** — ele elimina também
                     # os runs de `error_code` NULO, porque `NOT (NULL LIKE ...)`
                     # é NULL, e NULL não passa. Isso deixaria a varredura cega
                     # exatamente para os órfãos que ela existe para achar.
                     # O `or_` abaixo devolve os 2 corretos.
                     .or_("error_code.is.null,error_code.not.like.needs_human:*")
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
        # Sumir do cache numa fase terminal é o fim natural do trabalho
        # AUTOMÁTICO — gritar "órfão" seria alarme falso, e alarme falso é como
        # se ensina uma equipe a ignorar alarme.
        #
        # 🔴 MAS "O AUTOMÁTICO ACABOU" NÃO É "O TRABALHO ACABOU" — BLOCO A.2.
        #
        # 📊 Este bloco gravava `completed` fixo para as QUATRO fases da lista, e
        # por isso os dois únicos `needs_human` duráveis da história do produto
        # estão em `work_runs` como **concluídos**. Um travamento marcado como
        # sucesso é invisível para qualquer consulta que pergunte "o que ficou
        # em pé?" — que é a pergunta inteira desta SPEC.
        #
        # ⚠️ E o conserto é CIRÚRGICO, de propósito: `status_duravel_da_fase`
        # (`insurer_dispatch_service.py:146`) já mapeia `needs_human` →
        # `waiting_input` e mantém `encaminhado`, `resolvido` e `test_aborted`
        # em `completed`. **A distinção já existia no vocabulário do motor; o
        # que faltava era este UPDATE deixar de atropelá-la.** Tirar
        # `needs_human` de `FASES_ENCERRADAS` seria o conserto errado: a lista
        # tem três consumidores, e o de `registrar_checkpoint` está CERTO hoje.
        final = _motor().status_duravel_da_fase(fase)
        agora_iso = _agora().isoformat()
        if final == "completed":
            campos = {
                "status": final, "finished_at": agora_iso, "updated_at": agora_iso,
                "progress_percent": 100,
                "result_summary": ("Caso entregue à equipe da corretora — a parte "
                                   "automática do acionamento terminou aqui."),
            }
        else:
            # 🔴 `needs_human`. Os OUTROS QUATRO CAMPOS também mentiriam:
            # `finished_at` diria que acabou, `progress_percent = 100` diria que
            # foi até o fim, e o resumo diria "entregue". Consertar só o
            # `status` deixaria a mesma mentira em quatro lugares.
            motivo_do_caso = str(entrada.get("reason") or "").strip()
            campos = {
                "status": final,
                "finished_at": None,
                "updated_at": agora_iso,
                "progress_percent": _progresso_da_fase(fase, final),
                "result_summary": ("Parou e precisa de uma pessoa da corretora. "
                                   f"Motivo: {motivo_do_caso or 'não registrado'}")[:400],
            }
        # 🔴 `unblock_state` SAIU DO UPDATE GERAL — painel da SPEC-085.
        #
        # Ele era escrito aqui com só `.eq("id", run_id)`, sem o filtro
        # `IS NULL` que a OUTRA cópia do escritor (`_marcar_travamento`) tem e
        # testa. Duas escritas da mesma coluna, uma com guarda e outra sem —
        # e esta pisaria em `assumido_por_humano`, apagando o nome de quem
        # assumiu o caso.
        #
        # ⚠️ Estava fechado HOJE por acidente: o `.or_(...)` da varredura
        # exclui runs com `error_code LIKE 'needs_human:%'`. Quem limpar o
        # `error_code` reabre. Acidente não é guarda.
        await db.client.table("work_runs").update(campos).eq("id", run_id).execute()
        if final != "completed":
            await _marcar_travamento(db, run_id, fase, "",
                                     company_id=str(company_id or ""), session=entrada)
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


def _destino_do_alert_target(raw: Any) -> str:
    """O destino DENTRO de `integrations.alert_target` — SPEC-085, painel.

    🔴 ESTA FUNÇÃO EXISTE PORQUE `_normalizar_destino` RECEBIA O OBJETO INTEIRO.
    📊 O red team reproduziu, executando a fonte real:

        {"label":"Grupo 24h","observer_scope":…}  → '24'
        {"observer_scope":…,"internal_numbers":[a,b]}  → os dois COLADOS
        {"number":"1203…@g.us"}                   → o grupo virava telefone

    As duas primeiras formas **existem em produção**: `admin_atlas.py:470` grava
    `{label, observer_scope}` e `whatsapp_channel.py:431` grava `{number}`. Um
    label como *"Assistência 24h - 11 3003 4000"* produzia um telefone REAL de
    terceiro — e o dossiê de handoff carrega nome, CPF e telefone do segurado
    (`CLAUDE.md` §7). `_destino_e_compartilhado` não protegia: `'24'` não é
    compartilhado com ninguém.

    ⚠️ E o leitor certo JÁ EXISTIA e não tinha sido reusado:
    `whatsapp/alerts.py:50` (`_alert_target_dict` + `.get("number") or
    .get("group")`). Aqui é a mesma leitura, escrita uma vez.
    """
    alvo = raw
    if isinstance(alvo, str):
        try:
            alvo = json.loads(alvo)
        except Exception:  # noqa: BLE001
            # String crua: é o valor, não um objeto. Formato antigo.
            return _normalizar_destino(alvo)
        # 🔴 O `except` ACIMA NUNCA RODAVA PARA A FORMA QUE ELE DESCREVE.
        # 📊 Medido pelo juiz de confirmação: `json.loads("5511999998888")`
        # devolve um **int**, não levanta. O número puro — exatamente o
        # "formato antigo" que o comentário promete tratar — caía no
        # `not isinstance(alvo, dict)` e virava `''`: destino nenhum, dossiê
        # não entregue, e ninguém chamado. O JSON válido mais parecido com uma
        # string crua é um número, e era o único que o caminho não pegava.
        if not isinstance(alvo, (dict, list)):
            return _normalizar_destino(raw)
    if not isinstance(alvo, dict):
        return ""
    return _normalizar_destino(alvo.get("number") or alvo.get("group") or "")


def _normalizar_destino(raw: Any) -> str:
    """GRUPO do WhatsApp (…@g.us) é destino válido — não reduzir a dígitos.

    🔴 RECUSA ESTRUTURA. Antes, um `dict` virava `str(dict)` e os dígitos de
    QUALQUER lugar dele — rótulo, escopo, lista de números internos — viravam
    um "telefone". Quem tem um objeto usa `_destino_do_alert_target`.
    """
    if isinstance(raw, (dict, list, tuple, set)):
        logger.error("[SUPORTE] destino veio como %s, não como texto — "
                     "recusado. Use `_destino_do_alert_target`.",
                     type(raw).__name__)
        return ""
    s = str(raw or "").strip()
    if not s:
        return ""
    # ⚠️ `@G.US` maiúsculo também é grupo. Sem o `lower()`, um grupo escrito em
    # caixa alta caía no `_digits` e virava um telefone fabricado — medido pelo
    # juiz do isolamento: `'120363042@G.US'` → `'120363042'`.
    return s if s.lower().endswith("@g.us") else _digits(s)


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

        # 🔴 NORMALIZA OS DOIS LADOS, E NÃO FILTRA POR `is_active`.
        #
        # 📊 A versão anterior comparava o destino JÁ NORMALIZADO contra o
        # `destination_ref` CRU, no banco. O juiz do isolamento mediu, com a
        # linha de controle que prova a comparação saber distinguir:
        #
        #   CONTROLE-  só a A tem o destino ................ liberou (certo)
        #   CONTROLE+  B tem o MESMO ref normalizado ....... RECUSA  (certo)
        #   B gravou '(47) 3333-4444' ..................... *** LIBEROU ***
        #   B tem o mesmo ref com is_active=False ......... *** LIBEROU ***
        #   B gravou '120363@G.US' ........................ *** LIBEROU ***
        #
        # ⚠️ E o `is_active` era o pior dos três: um destino DESATIVADO na
        # corretora B continua sendo **o grupo de WhatsApp da B**. O dossiê
        # chega lá do mesmo jeito. "Inativo" descreve a configuração dela, não
        # quem lê a mensagem.
        #
        # 🔴 A regra é RECUSAR, não avisar: um handoff que não sai é um
        # problema operacional que alguém conserta em minutos; um CPF na
        # conversa errada não se desfaz.
        # 🔴 TRUNCAR NÃO É PROVAR — juiz de confirmação da SPEC-085.
        #
        # Uma varredura com teto e sem `order` responde "não achei colisão"
        # tanto quando não há colisão quanto quando ela ficou depois da linha
        # 500. As duas respostas são a mesma, e uma delas manda um dossiê com
        # CPF de segurado para o grupo de OUTRA corretora.
        #
        # ⚠️ O `except` abaixo já recusa quando a consulta falha. O teto era o
        # caminho em que ela **não falha** e mesmo assim não prova nada.
        _TETO_DESTINOS, _TETO_EMPRESAS = 500, 200
        r1 = await (db.client.table("human_support_destinations")
                    .select("company_id, destination_ref")
                    .limit(_TETO_DESTINOS).execute())
        if len(r1.data or []) >= _TETO_DESTINOS:
            logger.error("[DISPATCH ROUTER] a varredura de destinos bateu no teto "
                         "de %s — exclusividade NAO provada, recusando", _TETO_DESTINOS)
            return ("não foi possível verificar se o destino é exclusivo desta "
                    "corretora (lista de destinos maior que o teto da varredura)")
        for row in r1.data or []:
            if str(row.get("company_id")) == str(company_id):
                continue
            if _normalizar_destino(row.get("destination_ref")) == destino:
                outras.add(str(row.get("company_id")))

        r2 = await (db.client.table("companies")
                    .select("id, acionamento_profile").limit(_TETO_EMPRESAS).execute())
        if len(r2.data or []) >= _TETO_EMPRESAS:
            logger.error("[DISPATCH ROUTER] a varredura de corretoras bateu no teto "
                         "de %s — exclusividade NAO provada, recusando", _TETO_EMPRESAS)
            return ("não foi possível verificar se o destino é exclusivo desta "
                    "corretora (mais corretoras que o teto da varredura)")
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
                # 🔴 O OBJETO, LIDO COMO OBJETO. Ver `_destino_do_alert_target`.
                d = _destino_do_alert_target(row.get("alert_target"))
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


async def entregar_dossie_uma_vez(session: Dict[str, Any], dossier: str,
                                  enviar, *, company_id: str = "") -> bool:
    """O dossiê passa pelo MARCADOR e pelo TETO — SPEC-085 BLOCO B.

    🔴 UMA implementação, usada pelas DUAS cadeias. O `dispatch_watchdog`
    importa daqui (ele já importa `save_active_dispatch` e `_support_contact`
    deste módulo). A §8 da SPEC proíbe "um segundo marcador de aviso", e duas
    cópias da mesma regra em arquivos diferentes é exatamente isso com outro
    nome — é o defeito nº 1 deste projeto.

    `enviar` é uma SEAM **assíncrona**: `await enviar(texto)` devolve se saiu.
    Cada cadeia tem o seu transporte (o Vigia usa `wa.send_message` por dentro
    de um `await`; o roteador usa o `send_to_client` síncrono que recebeu), e a
    REGRA não precisa saber disso.

    ⚠️ A seam nasceu SÍNCRONA e estava errada: os dois transportes vivem dentro
    de um loop já rodando, e a primeira versão tentou contornar isso com um
    `run_until_complete` — que estoura exatamente no scheduler, que é o único
    lugar onde este código roda. Async na seam é o conserto; contornar era o
    defeito.

    🔴 REUSA `human_handoff.py:69-152` — não reescreve. Aquele código é da
    SPEC-086, está pronto, e o que faltava era estas cadeias usá-lo.

    ⚠️ **A chave é por CONVERSA, e ela pode faltar.** Sai de
    `session["mirror_conversation_id"]` (gravado por `dispatch_mirror`), que é
    vazio com `DISPATCH_MIRROR=0` ou quando a conversa não pôde ser criada.
    Sem id, o aviso **sai sem marcador** e a ocorrência é registrada.
    **Nunca** `reivindicar_o_aviso(None, ...)`: isso gravaria
    `handoff_realerta:None`, uma chave GLOBAL que calaria o handoff de TODAS as
    corretoras por seis horas (`CLAUDE.md` §7 — isolamento entre corretoras).
    """
    conversa_id = str(session.get("mirror_conversation_id") or "").strip()
    if not conversa_id:
        logger.warning("[HANDOFF] sem id de conversa — o dossiê sai SEM "
                       "marcador e pode repetir. case=%s", session.get("case_id"))
        return bool(await enviar(dossier))

    try:
        from app.agents.tools.human_handoff import (
            HORAS_ENTRE_AVISOS_PADRAO,
            MAX_LEMBRETES_POR_CONVERSA,
            contar_lembrete,
            devolver_a_vez,
            reivindicar_o_aviso,
        )
    except Exception as exc:  # noqa: BLE001
        # O import arrasta `app.agents` → `graph.py` → `langgraph`. Falhando,
        # o dossiê SAI mesmo assim: o defeito grave é o silêncio, e a repetição
        # é só incômodo — a mesma escolha que o marcador faz sem Redis.
        logger.error("[HANDOFF] marcador indisponível (%s) — o dossiê sai sem ele",
                     type(exc).__name__)
        return bool(await enviar(dossier))

    # 🔴 SPEC-EXTRA-001.3 §7.5 — a chave do marcador passa a levar a
    #    CORRETORA e o TIPO. Sem `company_id` a chave continua sendo a da
    #    conversa, que já é única na base — nunca uma chave global.
    _empresa = str(company_id or session.get("company_id") or "")
    if await reivindicar_o_aviso(conversa_id, HORAS_ENTRE_AVISOS_PADRAO,
                                 company_id=_empresa):
        # 🔴 DEVOLVE `True`, E A CORREÇÃO É SOBRE O QUE O SEGURADO OUVE.
        #
        # Devolvia `session["dossier_sent"]`, que numa sessão NOVA é `False`. O
        # chamador então escolhia `aviso_de_handoff(False)` e o segurado ouvia
        # *"também não consegui avisar a equipe agora"* — **falso: avisaram, há
        # menos de seis horas, sobre esta mesma conversa.**
        #
        # ⚠️ O contrato desta função é "a equipe SABE deste caso?", não "esta
        # sessão mandou uma mensagem?". Quem reivindicou o aviso e o entregou
        # respondeu por ela. Reproduzido pelo red team com dublê.
        logger.info("[HANDOFF] a equipe já foi avisada desta conversa nas "
                    "últimas %sh — ficando quieto", HORAS_ENTRE_AVISOS_PADRAO)
        return True

    if await contar_lembrete(conversa_id) > MAX_LEMBRETES_POR_CONVERSA:
        # ⚠️ O teto cala o GRUPO, não o CASO: ele segue `needs_human`, com
        # `unblock_state='travado'`, visível na Fila. Alarme que chega para
        # sempre deixa de ser alarme.
        # 🔴 E AQUI A RESPOSTA É OUTRA, DE PROPÓSITO — a assimetria é a regra.
        #
        # O juiz de confirmação leu as duas metades e perguntou por que uma
        # devolve `True` e a outra `session["dossier_sent"]`. Porque a pergunta
        # que o SEGURADO faz não é "alguém foi avisado?", é **"alguém vem?"**.
        #
        #   marcador fresco → avisaram há < 6h e a equipe está com o caso na mão
        #   TETO atingido   → avisaram MAX vezes e **ninguém pegou**
        #
        # No teto, dizer "já passei para a equipe" é verdade inútil: ela foi
        # avisada e não agiu. Devolvendo `False`, o chamador escolhe
        # `aviso_de_handoff(False)` — que é a saída honesta E que entrega ao
        # segurado o caminho que ele pode tomar SOZINHO (a assistência 24h da
        # própria apólice). É a única mensagem que ainda ajuda alguém parado.
        logger.warning("[HANDOFF] teto de %s lembretes atingido — o caso segue "
                       "travado e visível", MAX_LEMBRETES_POR_CONVERSA)
        return bool(session.get("dossier_sent"))

    saiu = bool(await enviar(dossier))
    if not saiu:
        # Reserva que não virou aviso tem de ser devolvida, senão uma falha de
        # envio silencia o grupo pelas seis horas inteiras do marcador.
        await devolver_a_vez(conversa_id, company_id=_empresa)
    return saiu


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

    🔴 **A janela deixou de ser daqui** (08/09/2026): quem decide a hora é
    `acompanhamento.calcular_envio_do_follow_up` — 08:00–19:00 no fuso da
    corretora. Esta função lê a BASE e só."""
    from datetime import datetime, timedelta, timezone as _tz

    from app.atendimento import acompanhamento as _acomp

    # ⚠️ O fuso vem do MESMO leitor da janela (`AGENT_OS_TENANT_TIMEZONE`).
    #    Antes era `ZoneInfo("America/Sao_Paulo")` escrito aqui: a primeira
    #    corretora de Manaus teria a base lida num fuso e a janela em outro.
    tz = _acomp.fuso_da_corretora()
    now = datetime.now(tz)
    base = now
    captured = captured or {}
    sched = captured.get("schedule") or {}
    periodo_combinado = _acomp.fim_do_periodo_combinado(sched)
    if periodo_combinado is not None:
        # `{day, periodo}` — o corredor residencial. 'tarde' não é previsão,
        # mas o FIM da tarde é base honesta para perguntar "deu tudo certo?".
        base = periodo_combinado.astimezone(tz)
    elif sched.get("day"):
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

    # 🔴 A JANELA É UMA SÓ — e antes eram DUAS (CLAUDE.md §5).
    #
    # 📊 Medido em 08/09/2026, neste arquivo: `_polite` (aqui) adiava a partir
    # das 21h para as 9h, com `America/Sao_Paulo` ESCRITO NO CÓDIGO; a espera do
    # pós-acionamento (`_pos_acionamento_do_checkpoint`) não tinha janela
    # nenhuma. Dois motores para "quando se pode falar com o segurado" divergem
    # — e divergiram: a mesma corretora, no mesmo minuto, podia mandar a
    # pergunta do prestador e calar a novidade, ou o contrário.
    #
    # 🔴 A decisão do Founder (08/09/2026) é **08:00–19:00 no fuso da
    # corretora** (`AGENT_OS_TENANT_TIMEZONE`), e ela mora em UM lugar:
    # `acompanhamento.calcular_envio_do_follow_up`. Isto aqui passou a ser
    # apenas o leitor da BASE — o horário que o prestador combinou.
    #
    # ⚠️ `now + 20min` continua de pé: um agendamento no passado não vira
    # pergunta imediata, e a função pura já garante que nada nasce vencido.
    piso = now + timedelta(minutes=20)
    follow = _acomp.calcular_envio_do_follow_up(
        now, max(base, piso - timedelta(minutes=_espera_do_followup_min())),
        _espera_do_followup_min())
    closing = _acomp.calcular_envio_do_follow_up(
        follow, follow, _ESPERA_DO_ENCERRAMENTO_MIN)
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


#: `work_runs.unblock_state` quando uma pessoa assume o caso. 🔴 O VALOR É
#: ESTE, e não um nome novo, por três razões medidas:
#:
#: 1. 📊 o CHECK do banco (`work_runs_unblock_state_check`) aceita exatamente
#:    `travado | retomado_pelo_robo | assumido_por_humano | resolvido |
#:    abandonado`. Um sexto valor é um INSERT recusado — o clique não gravaria;
#: 2. 📊 o botão *assumir* do painel (`acionamentos-travados/route.ts:162`) já
#:    escreve este mesmo valor. É **o mesmo ato**, por outro canal;
#: 3. 📊 o botão *arquivar* filtra `.in_(['travado','assumido_por_humano'])`.
#:    Um valor novo faria o caso **sumir da Fila** — exatamente o defeito que
#:    esta SPEC existe para matar.
ASSUMIDO_POR_HUMANO = "assumido_por_humano"


async def note_manual_outbound(company_id: str, insurer_phone: str, text: str,
                               *, canal: str = "whatsapp",
                               foi_humano: bool = True) -> bool:
    """Uma pessoa da corretora falou com a seguradora — e agora o produto SABE.

    Registra no transcript a mensagem MANUAL (humano clicou/digitou direto na
    conversa com a seguradora — `fromMe`). Sem isso o espelho fica incompleto
    quando um humano copilota a URA (teste 2026-07-12).

    ## 🔴 BLOCO C.1 — O CLIQUE DELA PARA DE SER CREDITADO AO ROBÔ

    📊 Medido em 25/08/2026, no banco de produção:

    ```
    work_runs com unblock_state = 'assumido_por_humano' ....  0
    work_events com ator humano em 27.985 eventos ..........  0
    work_steps com marca `manual` ..........................  0
    ```

    Esta função tocava **só no Redis**. A atendente respondia a seguradora pelo
    WhatsApp dela, o caso saía de `needs_human`, e `decidir_travamento` gravava
    `retomado_pelo_robo`: **o robô levava o crédito do trabalho dela.** Duas
    semanas de piloto produziriam zero linhas sobre quanto trabalho humano o
    produto ainda custa.

    ⚠️ **Sem tela e sem fluxo novo.** Ela continua clicando no WhatsApp dela. O
    que muda é só que o produto passa a saber.

    ## As três escritas, e por que a ordem é esta

    1. a marca na SESSÃO — é ela que `decidir_travamento` vai olhar no próximo
       checkpoint, e sem ela o crédito volta para o robô;
    2. `work_runs.unblock_state` — **só onde está `travado`**, nunca por cima de
       `resolvido` ou `abandonado`. Mesmo filtro atômico do botão do painel: se
       outra pessoa assumiu primeiro, esta escrita não pisa nela;
    3. `work_events` — a linha do tempo, com o canal. A coluna diz o estado de
       agora; a linha do tempo responde *"quem assumiu, e quando?"*.

    🔴 As duas últimas são **best-effort**: falhar em registrar nunca pode
    desfazer o espelho, que é o que a função já fazia bem. Mas falham **alto**.
    """
    session = await load_active_dispatch(company_id, insurer_phone)
    if not session or not str(text or "").strip():
        return False

    # 🔴 `foi_humano=False` É O ECO DA NOSSA PRÓPRIA VOZ, E ELE NÃO ASSUME NADA.
    #
    # ⚠️ **O painel pegou esta inversão antes de ela sair.** `webhook.py` chama
    # esta função para TODO `fromMe` — e a resposta que o próprio Cérebro mandou
    # à seguradora volta como `fromMe`. Com as escritas duráveis do BLOCO C.1,
    # isso gravaria `assumido_por_humano` e um evento de ator `user` **para uma
    # mensagem que nenhuma pessoa escreveu**.
    #
    # 🔴 Seria o BLOCO C ao contrário: em vez de o humano deixar de ser
    # creditado ao robô, o robô passaria a ser creditado ao humano — e a
    # métrica que esta SPEC existe para produzir (*"quanto trabalho humano o
    # produto ainda custa"*) nasceria inteira errada.
    #
    # Quem sabe a resposta é `e_a_nossa_propria_voz`, que já existe desde 06/08 e
    # já é consultada no webhook. Aqui ela só passa a ser **usada**.
    via = "humano" if foi_humano else "robo"
    session.setdefault("transcript", []).append(
        {"direction": "out", "text": str(text)[:2000], "manual": bool(foi_humano),
         "at": _agora().isoformat(), "via": via}
    )
    if not foi_humano:
        # O espelho continua completo — era o que a função já fazia bem. O que
        # não acontece é a assunção: ninguém assumiu coisa nenhuma.
        await save_active_dispatch(company_id, insurer_phone, session)
        return True

    # (1) A MARCA. Ela viaja na sessão até o próximo checkpoint, e é o que impede
    #     `retomado_pelo_robo` de mentir sobre quem trabalhou.
    session["destravado_por"] = "humano"
    session["canal_do_destrave"] = str(canal or "whatsapp")[:40]
    session["assumido_por_humano_em"] = _agora().isoformat()

    # (0) 🔴 A JANELA DE 15 s — 1 FALA ESPERA, 2 FALAS ASSUMEM (Founder, 17/09).
    #
    # 📊 10/09, 17:18:12 ela digitou "1"; 17:18:14 e :16 o corredor digitou de
    # novo. Esta função fazia três escritas e NENHUM bloqueio. Agora a 1ª fala
    # abre a janela, que cala o motor, o Cérebro, o Vigia e o grupo; a 2ª fala
    # DENTRO dela ASSUME o acionamento. ⚠️ `foi_humano=False` saiu acima: o eco
    # da nossa voz não pausa.
    #
    # ⛔ NADA SAI POR CAUSA DISTO — nem ao grupo, nem ao destino de suporte, nem
    #    ao segurado. A atendente não recebe aviso, não decora palavra e não
    #    responde nada: o gesto que assume é o gesto que ela já faz.
    #
    # E ela já respondeu a tela que estava pendente: o Cérebro não a responde de
    # novo quando a janela acabar.
    evento_da_pausa = _motor().uma_fala_da_atendente(session, canal=canal)
    espera_cancelada = None
    if evento_da_pausa in ("aberta", "assumiu"):
        session.pop("pending_insurer_messages", None)
        session.pop("falta_para_a_ura", None)
        # D3 — ela respondeu a seguradora: a pergunta ao segurado deixa de valer.
        espera_cancelada = session.pop("esperando_do_segurado", None)
    await save_active_dispatch(company_id, insurer_phone, session)
    await _registrar_assuncao_humana(company_id, session, canal=canal)
    if evento_da_pausa in ("aberta", "assumiu"):
        await _depois_da_pausa(company_id, session, evento_da_pausa)
    if espera_cancelada:
        await _indexar_pergunta(company_id, str(espera_cancelada.get("client_phone") or ""),
                                insurer_phone, 1, apagar=True)
    return True


async def _depois_da_pausa(company_id: str, session: Dict[str, Any], evento: str) -> None:
    """O índice da janela e o rastro. ⛔ Nunca levanta. ⛔ NENHUM envio.

    🔴 O índice que cala o grupo segue o CICLO da janela: entra na 1ª fala (e
    expira sozinho junto com ela) e SAI quando ela assume — a partir daí quem
    cala o grupo é o próprio `humano_assumiu`, e um índice órfão calaria a
    conversa por 15 s depois de o acionamento já ter saído das nossas mãos.
    """
    from app.services.o_grupo_so_o_que_importa import (
        alvos_da_pausa, desmarcar_pausa_humana, marcar_pausa_humana,
    )

    alvos = alvos_da_pausa(session.get("mirror_conversation_id"),
                           session.get("client_phone"))
    try:
        if evento == "assumiu":
            await desmarcar_pausa_humana(company_id, alvos)
        else:
            restante = int(max(0.0, -_idade_segundos((session.get("pausa_humana") or {}).get("ate"))))
            await marcar_pausa_humana(company_id, alvos, restante + 5)
        await _anotar_ato(
            company_id, session, "pausa_humana.%s" % evento,
            ("Uma pessoa da equipe assumiu a conversa com a seguradora; o agente saiu."
             if evento == "assumiu"
             else "Uma pessoa da equipe falou com a seguradora; o agente esperou."),
            {"janela_s": int(_motor().PAUSA_HUMANA_S)})
    except Exception as e:  # noqa: BLE001
        logger.warning("[PAUSA HUMANA] efeitos da janela incompletos (%s)", type(e).__name__)


async def _avisar_retomada(company_id: str, session: Dict[str, Any]) -> None:
    """D2 — "a seguradora respondeu, retomei", pela porta única. ⛔ Nunca levanta."""
    try:
        from app.core.database import get_supabase_client
        from app.services.dispatch_mirror import insurer_label_from_ref
        from app.services.o_grupo_so_o_que_importa import TIPO_RETOMADA, enviar_ao_grupo

        seguradora = insurer_label_from_ref(str(session.get("playbook_ref") or ""))
        caso = str(session.get("case_id") or "")[:8]
        await enviar_ao_grupo(
            get_supabase_client(), company_id=str(company_id), tipo=TIPO_RETOMADA,
            texto=(f"↩️ A {seguradora} respondeu no caso {caso}. Retomei o atendimento "
                   "— aviso quando tiver o protocolo."),
            conversation_id=str(session.get("mirror_conversation_id") or ""),
            telefone=str(session.get("client_phone") or ""), sessao=session,
            resumo="retomada — caso %s" % caso, motivo="retomada")
    except Exception as e:  # noqa: BLE001
        logger.warning("[RETOMADA] aviso ao grupo não saiu (%s)", type(e).__name__)


async def _anotar_ato(company_id: str, session: Dict[str, Any], tipo: str,
                      mensagem: str, carga: Optional[Dict[str, Any]] = None) -> None:
    """Uma linha na linha do tempo do run — o mesmo `_evento`, best-effort."""
    run_id = str(session.get("work_run_id") or "")
    if not run_id or not company_id:
        return
    db = await _db()
    if db is None:
        return
    await _evento(db, str(company_id), run_id, tipo, mensagem,
                  payload={**(carga or {}), "rota": str(session.get("playbook_ref") or "")[:180]})


async def _a_atendente_entrou(company_id: str, insurer_phone: str, session: Dict[str, Any],
                              entradas_antes: int) -> Optional[Dict[str, Any]]:
    """A sessão DELA, se a atendente abriu a janela (ou assumiu) depois da nossa
    leitura — com as telas que chegaram neste turno acrescentadas. `None` = siga.

    ⚠️ Leitura pura do Redis (`_ler_do_redis`): `load_active_dispatch` agenda a
    reconciliação de órfãos quando não acha sessão, e isto roda no caminho quente.
    """
    motor = _motor()
    try:
        fresca = await _ler_do_redis(company_id, insurer_phone)
    except Exception as e:  # noqa: BLE001 — sem reler, segue como sempre seguiu
        logger.warning("[DISPATCH ROUTER] sessão não relida depois do Cérebro (%s)", type(e).__name__)
        return None
    if not fresca or not (motor.pausa_humana_aberta(fresca) or motor.humano_assumiu(fresca)):
        return None
    novas = [dict(t, _deste_turno=True) for t in (session.get("transcript") or [])[entradas_antes:]
             if isinstance(t, dict) and t.get("direction") == "in"]
    fresca.setdefault("transcript", []).extend(novas)
    logger.info("[DISPATCH ROUTER] a atendente entrou enquanto o Cérebro pensava — nada nosso sai")
    return fresca


async def _gravar_a_sessao_dela(company_id: str, insurer_phone: str,
                               dela: Dict[str, Any], entradas_antes: int) -> None:
    """Grava a sessão da atendente com a tela deste turno NO LUGAR CERTO.

    🔴 Confirmação pós-conserto (17/09): anexada no fim, a tela ficava DEPOIS da
    fala dela — e, vencida a pausa, o Vigia a via sem resposta e o Sentinela
    respondia de novo o que ela já tinha respondido. A ordem é tela → fala dela.
    ⚠️ Duas gravações, de propósito: a primeira (com espelho) leva a tela ao
    Espelho uma vez; a segunda só reordena no Redis, sem espelhar de novo.
    """
    await save_active_dispatch(company_id, insurer_phone, dela)
    transcript = dela.get("transcript") or []
    k = sum(1 for t in reversed(transcript) if isinstance(t, dict) and t.get("_deste_turno"))
    if k:
        novas = transcript[-k:]
        for t in novas:
            t.pop("_deste_turno", None)
        del transcript[-k:]
        pos = max(0, min(int(entradas_antes), len(transcript)))
        transcript[pos:pos] = novas
        dela["mirror_idx"] = len(transcript)
        await _gravar_no_redis(company_id, insurer_phone, dela)


async def _sessoes_da_corretora(company_id: str) -> List[tuple]:
    """`[(insurer_phone, session)]` desta corretora — pela chave COMPOSTA (§7)."""
    empresa = str(company_id or "").strip()
    if not empresa:
        return []
    prefixo = f"dispatch:active:{empresa}:"
    achadas: List[tuple] = []
    redis = await _redis()
    if redis is not None:
        async for chave in redis.scan_iter(match=prefixo + "*"):
            k = chave.decode() if isinstance(chave, (bytes, bytearray)) else str(chave)
            bruto = await redis.get(k)
            if not bruto:
                continue
            try:
                achadas.append((k[len(prefixo):], json.loads(bruto)))
            except Exception:  # noqa: BLE001
                continue
        return achadas
    for k, bruto in list(_memory_store.items()):
        if isinstance(k, str) and k.startswith(prefixo) and not k.endswith(":list"):
            try:
                achadas.append((k[len(prefixo):], json.loads(bruto) if isinstance(bruto, str) else dict(bruto)))
            except Exception:  # noqa: BLE001
                continue
    return achadas


# ===========================================================================
# ⚠️ ATALHO OPCIONAL — as palavras AGENTE e EU CUIDO
# ===========================================================================
#
# 🔴 DECISÃO DO FOUNDER (17/09/2026): A ATENDENTE NÃO PRECISA DESTAS PALAVRAS.
#
# Quem decide é o gesto que ela já faz (`uma_fala_da_atendente`): 1 fala e o
# robô espera; 2 falas dentro da janela e ele sai do acionamento. ⛔ NENHUM
# texto do produto — mensagem, dossiê, tela ou resumo — pede, ensina ou cita
# estas palavras. Elas continuam aqui porque já existem, custam uma comparação
# de string e servem a quem as conhece:
#
#     AGENTE     devolve ao robô um acionamento assumido, dentro de 30 min
#     EU CUIDO   faz o mesmo que a 2ª fala: tira o robô deste acionamento
#
# ⚠️ 📊 17/09: toda instância é criada com `ignoreGroups: True`
# (`pairing_orchestrator.py`, `whatsapp_channel.py`, `admin_atlas.py`) — a mensagem
# digitada NO GRUPO não chega ao webhook enquanto o canal estiver assim. Por isso
# a palavra vale de dois lugares: do chat de suporte da corretora (o grupo, quando
# o canal entregar grupos; ou o número de suporte) e do número de alguém da equipe
# (`numeros_da_casa`, EXTRA-001.3), no privado da corretora.
PALAVRA_AGENTE = "agente"
PALAVRA_EU_CUIDO = "eu cuido"
#: Até quanto tempo depois de a janela abrir as palavras ainda valem (o corredor
#: já pode ter retomado — a atendente continua podendo tirá-lo do acionamento).
_JANELA_DA_PALAVRA_S = 30 * 60


def palavra_da_equipe(texto: Any) -> Optional[str]:
    """`agente` · `eu cuido` · `None`. A mensagem tem de SER a palavra.

    ⛔ Nunca "contém": uma frase QUALQUER que mencione as duas palavras não pode
    virar comando. 📊 O aviso que as citava saiu do produto em 17/09 — a regra
    do `in` ficou, porque o eco de qualquer texto continua sendo possível.
    """
    limpo = re.sub(r"[^a-z ]+", " ", _norm(texto))
    limpo = " ".join(limpo.split())
    if limpo in (PALAVRA_AGENTE, PALAVRA_EU_CUIDO):
        return limpo
    return None


async def _e_da_equipe(company_id: str, remetente: str, chat: str, eh_grupo: bool) -> bool:
    try:
        alvo = await resolver_destino_de_suporte(company_id)
        destino = str(alvo.get("destino") or "").strip().lower()
        if eh_grupo:
            return bool(destino) and destino == str(chat or "").strip().lower()
        if destino and not destino.endswith("@g.us") and _digits(destino) == _digits(remetente):
            return True
        from app.core.database import get_supabase_client
        from app.services.o_grupo_so_o_que_importa import e_numero_da_casa, numeros_da_casa

        return e_numero_da_casa(await numeros_da_casa(get_supabase_client(), company_id), remetente)
    except Exception as e:  # noqa: BLE001
        logger.warning("[PALAVRA DA EQUIPE] remetente não conferido (%s) — ignorada",
                       type(e).__name__)
        return False


async def ler_palavra_da_equipe(company_id: str, texto: Any, *, remetente: str = "",
                                chat: str = "", eh_grupo: bool = False) -> Optional[str]:
    """Aplica AGENTE / EU CUIDO ao acionamento EM PAUSA desta corretora.

    Devolve `agente` · `eu_cuido` (aplicada) · `ambigua` (2+ acionamentos) · `None`.
    🔴 Só uma sessão elegível recebe a palavra: com duas, não se adivinha qual.
    """
    palavra = palavra_da_equipe(texto)
    empresa = str(company_id or "").strip()
    if not palavra or not empresa:
        return None
    if not await _e_da_equipe(empresa, remetente, chat, eh_grupo):
        return None
    motor = _motor()
    agora = _agora()
    candidatas = []
    for fone, sessao in await _sessoes_da_corretora(empresa):
        pausa = sessao.get("pausa_humana") or {}
        aberta_ha = _idade_segundos(pausa.get("aberta_em"))
        recente = 0 <= aberta_ha <= _JANELA_DA_PALAVRA_S
        if palavra == PALAVRA_AGENTE:
            ok = motor.pausa_humana_aberta(sessao, agora) or (motor.humano_assumiu(sessao) and recente)
        else:
            ok = recente and not motor.humano_assumiu(sessao) and sessao.get("state") in (
                "ura", "human_phase", "needs_human")
        if ok:
            candidatas.append((fone, sessao))
    if len(candidatas) != 1:
        if candidatas:
            logger.warning("[PALAVRA DA EQUIPE] %r com %d acionamentos em pausa — "
                           "não adivinho qual", palavra, len(candidatas))
            return "ambigua"
        return None
    fone, sessao = candidatas[0]
    from app.services.o_grupo_so_o_que_importa import alvos_da_pausa, desmarcar_pausa_humana

    if palavra == PALAVRA_AGENTE:
        motor.fechar_pausa(sessao, "agente", agora)
        if motor.humano_assumiu(sessao):
            sessao["state"] = str(sessao.pop("estado_antes_do_humano", "") or "ura")
            motivo_antes = str(sessao.pop("motivo_antes_do_humano", "") or "")
            if sessao["state"] == "needs_human" and motivo_antes:
                sessao["reason"] = motivo_antes     # travada antes, travada depois — com o motivo
            else:
                sessao.pop("reason", None)
        # A tela que chegou durante a pausa é respondida pelo Vigia no próximo
        # ciclo (≤ 20 s), lendo a TELA ATUAL — nenhum relógio novo.
        sessao["silencio_deliberado_ate"] = None
        resultado = "agente"
    else:
        motor.fechar_pausa(sessao, "eu_cuido", agora)
        sessao["estado_antes_do_humano"] = str(sessao.get("state") or "")
        sessao["motivo_antes_do_humano"] = str(sessao.get("reason") or "")
        sessao["state"] = "needs_human"
        sessao["reason"] = motor.HUMANO_ASSUMIU
        sessao["silencio_deliberado_ate"] = None
        sessao.pop("esperando_do_segurado", None)
        resultado = "eu_cuido"
    await save_active_dispatch(empresa, fone, sessao)
    await desmarcar_pausa_humana(empresa, alvos_da_pausa(sessao.get("mirror_conversation_id"),
                                                        sessao.get("client_phone")))
    await _anotar_ato(empresa, sessao, f"pausa_humana.{resultado}",
                      "A equipe respondeu AGENTE: o agente seguiu." if resultado == "agente"
                      else "A equipe respondeu EU CUIDO: o agente saiu deste acionamento.",
                      {"canal": "grupo" if eh_grupo else "privado"})
    logger.info("[PALAVRA DA EQUIPE] %s aplicada ao caso %s", resultado,
                str(sessao.get("case_id") or "")[:8])
    return resultado


# ===========================================================================
# 🔴 SPEC-EXTRA-001.4 D3 · PERGUNTAR AO SEGURADO E VOLTAR
# ===========================================================================
#
# 📊 10/09: a URA pediu PONTO DE REFERÊNCIA — só o segurado sabe — e o Cérebro
# respondeu NAO_SEI duas vezes, corretamente; a sessão morreu por não haver
# caminho. As 7 chamadas de `send_to_client` do roteador eram todas AVISOS.
#
# ⚠️ A espera mora na SESSÃO e o prazo é do VIGIA, que já varre a cada 20 s
# (proposta §3.1: `work_waits` só se o leitor existir — o leitor de `work_waits`
# é a `espera.vencida`, que avisaria o GRUPO sobre uma espera interna do acionamento).
#: 📊 O intervalo do "um instante" à seguradora: a Allianz encerra por inatividade
#: com 103 s no pior caso do acervo (56 encerramentos); a atendente do 10/09
#: encerrou 158 s depois de se apresentar. 60 s + o ciclo de 20 s do Vigia = 80 s.
PERGUNTA_HOLDING_S = 60
PERGUNTA_HOLDINGS_MAX = 2
_CHAVE_DA_PERGUNTA = "dispatch:pergunta:{empresa}:{fone}"


def _env_pergunta() -> tuple:
    motor = _motor()
    return (motor._env_int("PERGUNTA_AO_SEGURADO_HOLDING_S", PERGUNTA_HOLDING_S) or PERGUNTA_HOLDING_S,
            motor._env_int("PERGUNTA_AO_SEGURADO_HOLDINGS", PERGUNTA_HOLDINGS_MAX))


HOLDING_A_SEGURADORA = "Um instante, por favor — estou confirmando essa informação com o segurado."


def ao_vivo(session: Dict[str, Any]) -> bool:
    """O MESMO portão de `_emit`: sessão nascida ao vivo E o ambiente liberado.
    Em ensaio, a pergunta, o "um instante" e a resposta são registrados e NÃO saem."""
    return bool(session.get("live")) and _motor().dispatch_live_enabled()

#: 💭 Agradecimento e confirmação soltos — a lista é curta de propósito: o que não
#: está aqui é tratado como resposta (o segurado sabe o que perguntamos).
_SO_CONFIRMACAO = frozenset({
    "ok", "okay", "oks", "blz", "beleza", "certo", "ta", "ta bom", "ta certo", "obrigado",
    "obrigada", "obg", "valeu", "vlw", "grato", "grata", "entendi", "aguardo", "joia",
})


def e_resposta_de_conteudo(texto: Any) -> bool:
    """A mensagem do segurado TRAZ o dado? (não é só "ok", nem marcador de mídia)"""
    bruto = str(texto or "").strip()
    if not bruto or bruto.startswith("[") or bruto.rstrip().endswith("?"):
        # "[mídia…]" é marcador; "como assim?" é o segurado PERGUNTANDO (juiz, P5).
        return False
    limpo = " ".join(re.sub(r"[^a-z0-9 ]+", " ", _norm(bruto)).split())
    return bool(limpo) and limpo not in _SO_CONFIRMACAO


def pergunta_para_o_segurado(session: Dict[str, Any], rotulo: str) -> str:
    """💭 Copy — a régua de língua da 001.3: uma frase, sem jargão, com o porquê."""
    from app.services.dispatch_mirror import insurer_label_from_ref

    seguradora = insurer_label_from_ref(str(session.get("playbook_ref") or ""))
    return (f"Só mais uma informação que a {seguradora} pediu para seguir com o seu "
            f"atendimento: me diga {str(rotulo or 'o dado pedido').strip()}.")


async def _indexar_pergunta(company_id: str, client_phone: str, insurer_phone: str,
                            segundos: int, apagar: bool = False) -> None:
    try:
        from app.services.o_fim_do_atendimento import _variantes_do_telefone

        redis = await _redis()
        for v in _variantes_do_telefone(client_phone) or {_digits(client_phone)}:
            chave = _CHAVE_DA_PERGUNTA.format(empresa=company_id, fone=v)
            if redis is None:
                if apagar:
                    _memory_store.pop(chave, None)
                else:
                    _memory_store[chave] = _digits(insurer_phone)
            elif apagar:
                await redis.delete(chave)
            else:
                await redis.set(chave, _digits(insurer_phone), ex=max(1, int(segundos)))
    except Exception as e:  # noqa: BLE001
        logger.warning("[PERGUNTA] índice não gravado (%s)", type(e).__name__)


async def perguntar_ao_segurado(company_id: str, session: Dict[str, Any], *,
                                insurer_phone: str, slot: str, rotulo: str,
                                send_to_client: Callable[[str, str], Any],
                                send_to_insurer: Callable[[str], Any]) -> bool:
    """① pergunta pelo canal do CLIENTE · ② "um instante" à SEGURADORA (é o envio
    que reinicia o relógio de inatividade dela) · ③ a espera, na sessão.

    Devolve se perguntou. ⛔ Nunca pergunta duas vezes o mesmo dado no acionamento.
    """
    cliente = str(session.get("client_phone") or "").strip()
    if not cliente or not slot or slot in (session.get("perguntado_ao_segurado") or []):
        return False
    intervalo, _maximo = _env_pergunta()
    pergunta = pergunta_para_o_segurado(session, rotulo)
    vivo = ao_vivo(session)
    if vivo:
        try:
            send_to_client(cliente, pergunta)
        except Exception as e:  # noqa: BLE001
            logger.error("[PERGUNTA] a pergunta ao segurado NÃO saiu (%s)", type(e).__name__)
            return False
        await _registrar_fala_ao_cliente(company_id, cliente, "acionamento_pergunta", pergunta)
    agora = _agora()
    holding_ok = not vivo
    if vivo:
        try:
            send_to_insurer(HOLDING_A_SEGURADORA)
            holding_ok = True
        except Exception as e:  # noqa: BLE001
            logger.error("[PERGUNTA] o 'um instante' à seguradora NÃO saiu (%s)", type(e).__name__)
    transcript = session.setdefault("transcript", [])
    transcript.append({"direction": "out", "text": f"[AO CLIENTE] {pergunta}",
                       "at": agora.isoformat(), "step": "pergunta_ao_segurado", "dry_run": not vivo})
    if holding_ok:
        transcript.append({"direction": "out", "text": HOLDING_A_SEGURADORA, "dry_run": not vivo,
                           "at": agora.isoformat(), "step": "segurando_a_seguradora"})
    ate = (agora + timedelta(seconds=intervalo)).isoformat()
    session["esperando_do_segurado"] = {
        "slot": slot, "rotulo": str(rotulo or "")[:120], "client_phone": _digits(cliente),
        "pedido_em": agora.isoformat(), "ate": ate, "holdings": 0,
        "tela": _motor().tela_respondida(session)[-300:],
    }
    session["perguntado_ao_segurado"] = list(session.get("perguntado_ao_segurado") or []) + [slot]
    session["silencio_deliberado_ate"] = ate
    session.pop("pending_insurer_messages", None)
    await _indexar_pergunta(company_id, cliente, insurer_phone,
                            intervalo * (_maximo + 2) + 120)
    await _anotar_ato(company_id, session, "pergunta_ao_segurado.enviada",
                      "A seguradora pediu um dado que só o segurado sabe; perguntei a ele.",
                      {"slot": slot})
    return True


async def responder_pergunta_do_acionamento(company_id: str, from_phone: str, texto: Any,
                                            *, send_to_client: Callable[[str, str], Any]) -> bool:
    """A RESPOSTA do segurado volta para a seguradora — a reentrada da D3.

    ⚠️ Chega pelo caminho do ATENDIMENTO (webhook), não por um handler novo: o
    índice diz de qual acionamento é a pergunta, pela chave composta (§7).
    Devolve `True` quando a mensagem ERA a resposta (o agente não a responde).
    """
    resposta = str(texto or "").strip()
    empresa = str(company_id or "").strip()
    if not resposta or not empresa or not str(from_phone or "").strip():
        return False
    # ⛔ "ok", "obrigado" ou o marcador de uma mídia não baixada NÃO são a resposta:
    #    levá-los à seguradora como "ponto de referência" é pior do que esperar.
    #    Eles seguem o caminho normal (o agente responde) e a espera continua.
    if not e_resposta_de_conteudo(resposta):
        return False
    insurer_phone = ""
    try:
        from app.services.o_fim_do_atendimento import _variantes_do_telefone

        redis = await _redis()
        for v in _variantes_do_telefone(from_phone) or {_digits(from_phone)}:
            chave = _CHAVE_DA_PERGUNTA.format(empresa=empresa, fone=v)
            bruto = (await redis.get(chave)) if redis is not None else _memory_store.get(chave)
            if bruto:
                insurer_phone = bruto.decode() if isinstance(bruto, (bytes, bytearray)) else str(bruto)
                break
    except Exception as e:  # noqa: BLE001
        logger.warning("[PERGUNTA] índice ilegível (%s)", type(e).__name__)
        return False
    if not insurer_phone:
        return False
    session = await load_active_dispatch(empresa, insurer_phone)
    espera = (session or {}).get("esperando_do_segurado") or {}
    if not espera or not (_digits(from_phone) and espera.get("client_phone")
                          and (_digits(from_phone)[-8:] == str(espera["client_phone"])[-8:])):
        return False
    from app.tasks.dispatch_watchdog import _canal_da_conversa
    from app.services.integration_service import get_integration_service
    from app.services.whatsapp_service import get_whatsapp_service

    vivo = ao_vivo(session)
    if vivo:
        integration = _canal_da_conversa(get_integration_service(), empresa, session)
        if integration is None:
            logger.error("[PERGUNTA] sem canal para levar a resposta à seguradora")
            return False
        try:
            get_whatsapp_service().send_message(insurer_phone, resposta[:600], integration)
        except Exception as e:  # noqa: BLE001
            logger.error("[PERGUNTA] a resposta do segurado NÃO chegou à seguradora (%s)",
                         type(e).__name__)
            return False
    slot = str(espera.get("slot") or "")
    if slot:
        session.setdefault("slots", {})[slot] = resposta[:300]
    session.setdefault("transcript", []).append(
        {"direction": "out", "text": resposta[:600], "at": _agora().isoformat(),
         "via": "segurado", "step": "resposta_do_segurado", "dry_run": not vivo})
    session.pop("esperando_do_segurado", None)
    # O dado chegou: um dossiê depois disto não pode dizer que ele falta (juiz, P2).
    session.pop("falta_para_a_ura", None)
    session["silencio_deliberado_ate"] = None
    await save_active_dispatch(empresa, insurer_phone, session)
    await _indexar_pergunta(empresa, from_phone, insurer_phone, 1, apagar=True)
    await _anotar_ato(empresa, session, "pergunta_ao_segurado.respondida",
                      "O segurado respondeu e a resposta foi levada à seguradora.", {"slot": slot})
    if vivo:
        try:
            send_to_client(from_phone, "Obrigado! Já passei essa informação para a seguradora. 🙂")
        except Exception:  # noqa: BLE001
            pass
    return True


async def _registrar_assuncao_humana(company_id: str, session: Dict[str, Any],
                                     *, canal: str) -> bool:
    """IO do C.1: a coluna e a linha do tempo. Best-effort, mas nunca calado."""
    run_id = str(session.get("work_run_id") or "")
    if not run_id or not company_id:
        return False
    db = await _db()
    if db is None:
        return False
    assumiu = False
    try:
        # 🔴 O `.eq('unblock_state','travado')` é o que impede esta escrita de
        # pisar em quem assumiu antes — mesma escolha atômica do botão do painel.
        r = await (db.client.table("work_runs")
                   .update({"unblock_state": ASSUMIDO_POR_HUMANO,
                            "updated_at": _agora().isoformat()})
                   .eq("id", run_id).eq("company_id", str(company_id))
                   .eq("unblock_state", "travado").execute())
        assumiu = bool(getattr(r, "data", None))
    except Exception as e:  # noqa: BLE001
        logger.error("[TRAVAMENTO] run %s NÃO recebeu '%s' (%s) — o trabalho "
                     "desta pessoa vai ser creditado ao robô",
                     run_id, ASSUMIDO_POR_HUMANO, type(e).__name__)
    try:
        await _evento(
            db, str(company_id), run_id, "travamento.assumido",
            "Uma pessoa da corretora respondeu à seguradora e assumiu este caso.",
            payload={"por": "humano", "canal": str(canal or "whatsapp")[:40],
                     "rota": str(session.get("playbook_ref") or "")[:180],
                     "tela": tela_do_travamento(session),
                     "estava_travado": assumiu},
            ator="user")
    except Exception as e:  # noqa: BLE001
        logger.error("[TRAVAMENTO] assunção humana do run %s sem linha do tempo "
                     "(%s)", run_id, type(e).__name__)
        return assumiu
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

    _entradas_antes = len(session.get("transcript") or [])
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
    motor = _motor()
    _em_pausa = motor.pausa_humana_aberta(session)

    # 🔴 SPEC-EXTRA-001.4 D2 — REENTROU: o rastro, e a linha ao grupo SÓ se ele
    #    já tinha recebido o pedido de ajuda (a sessão decidiu em `avisar_retomada`).
    if session.pop("avisar_retomada", None) is not None:
        await registrar_ato_do_agente(
            company_id, session, agente="cerebro",
            mensagem="Uma pessoa da seguradora reabriu o acionamento travado; retomei.",
            payload={"reentrada": True, "de": str(session.get("reentrou_de") or "")[:60]})
        if session.get("dossier_sent"):
            await _avisar_retomada(company_id, session)

    # 🔴 SPEC-EXTRA-001.4 D3 — A TELA PEDE UM DADO QUE SÓ O SEGURADO SABE.
    #    `falta_para_a_ura` é o gatilho (`responder_da_ficha` já provou que a ficha
    #    não tem o dado). ⛔ Tecla de menu (`*_opcao`) não se pergunta ao segurado:
    #    quem a responde é o motor (e a do ramo vem da apólice, decisão do Founder).
    _falta = session.get("falta_para_a_ura") or {}
    _slot_falta = str(_falta.get("slot") or "")
    if (state in ("human_phase", "ura") and _slot_falta and "," not in _slot_falta
            and not _slot_falta.endswith("_opcao") and not ainda_vem_mais
            and not _ja_respondeu and not _em_pausa
            and not session.get("esperando_do_segurado")):
        from app.services.corridor_playbooks import _COMO_PERGUNTAR

        _rotulo = _COMO_PERGUNTAR.get(_slot_falta)
        if _rotulo and await perguntar_ao_segurado(
                company_id, session, insurer_phone=from_phone, slot=_slot_falta,
                rotulo=_rotulo, send_to_client=send_to_client,
                send_to_insurer=send_to_insurer):
            await save_active_dispatch(company_id, from_phone, session)
            return True

    # Fase humana: LLM redige, guard fiscaliza, falha repetida pausa (fail-closed).
    #
    # `not ainda_vem_mais` — ESPERA A TELA INTEIRA. Enquanto a rajada não
    # terminou, a mensagem apenas se acumula. Deliberar sobre meia tela era
    # responder à bolha errada em 2 de 3 turnos, e ainda gastava duas respostas
    # numa pergunta só (ver `_tela_do_turno`).
    # 🔴 SPEC-EXTRA-001.4 C — `not _em_pausa`: com a atendente na conversa, o
    #    Cérebro não redige. D3 — nem enquanto se espera o segurado.
    if (state == "human_phase" and human_reply_provider is not None
            and session.get("pending_insurer_messages")
            and not ainda_vem_mais and not _ja_respondeu and not _em_pausa
            and not session.get("esperando_do_segurado")):
        tela = _tela_do_turno(session, text)
        draft = None
        try:
            draft = await human_reply_provider(session, tela)
        except Exception as e:  # noqa: BLE001 — provider nunca derruba o roteador
            logger.error(f"[DISPATCH ROUTER] human reply provider error: {type(e).__name__}")
        # 🔴 SPEC-EXTRA-001.4 C — RELER DEPOIS DE PENSAR (juiz fresco, B1). O Cérebro
        #    levou segundos; se a atendente entrou na conversa nesse meio-tempo, nada
        #    nosso sai e a sessão DELA (pausa e a fala dela) é a que fica gravada.
        _dela = await _a_atendente_entrou(company_id, from_phone, session, _entradas_antes)
        if _dela is not None:
            await _gravar_a_sessao_dela(company_id, from_phone, _dela, _entradas_antes)
            return True
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
            # 🔴 BLOCO C.3 — O PULSO NÃO É RASTRO.
            #
            # 📊 `beat("cerebro")` é um número no Redis: sem caso, sem rota, sem
            # tela e sem histórico. O Founder pediu *"quero ver o desempenho do
            # Vigia, Sentinela e do Cérebro"* — e dois dos três eram
            # inauditáveis. Aqui a redação vira linha durável.
            #
            # ⚠️ E quando a fase anterior era `needs_human`, foi o Cérebro que
            # destravou: a marca faz o evento de destrave dizer `cerebro`, em
            # vez do `robo` genérico.
            if str(session.get("_checkpoint_fase") or "") == "needs_human":
                session["destravado_por"] = "cerebro"
            await registrar_ato_do_agente(
                company_id, session, agente="cerebro",
                mensagem="O Cérebro redigiu a resposta à seguradora e o guarda aprovou.",
                payload={"tentativa": 1, "aprovado": True})
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
            # 🔴 D6 — o silêncio também é ato do Cérebro (desempenho = tudo o que ele fez).
            await registrar_ato_do_agente(
                company_id, session, agente="cerebro",
                mensagem="O Cérebro leu a tela e ficou em silêncio: ela não pedia nada.",
                payload={"desfecho": "silencio", "seguidos": quietos})
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
                _dela = await _a_atendente_entrou(company_id, from_phone, session, _entradas_antes)
                if _dela is not None:
                    await _gravar_a_sessao_dela(company_id, from_phone, _dela, _entradas_antes)
                    return True
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
                    # BLOCO C.3 — a SEGUNDA redação conta igual: um desempenho
                    # que só registra os acertos de primeira não é desempenho.
                    if str(session.get("_checkpoint_fase") or "") == "needs_human":
                        session["destravado_por"] = "cerebro"
                    await registrar_ato_do_agente(
                        company_id, session, agente="cerebro",
                        mensagem=("O Cérebro refez a resposta no mesmo turno e o "
                                  "guarda aprovou."),
                        payload={"tentativa": 2, "aprovado": True,
                                 "recusa_anterior": motivo[:80]})
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
            # 🔴 SPEC-EXTRA-001.4 D6 — A CAUSA DAS 0 LINHAS `agente.*`, medida em 17/09:
            #    o registro só existia no ACERTO. 📊 Dos 6 acionamentos da base, 3
            #    terminaram em `sentinela_stall` sem um acerto sequer — nenhuma linha.
            #    Desempenho que só conta acertos não é desempenho.
            await registrar_ato_do_agente(
                company_id, session, agente="cerebro",
                mensagem="O Cérebro redigiu uma resposta e o guarda a recusou.",
                payload={"desfecho": "recusado",
                         "motivo": str(verdict.get("reason") or "")[:80],
                         "recusas_seguidas": int(session.get("human_phase_guard_fails") or 0),
                         "virou_pessoa": state == "needs_human"})

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

    if state == "needs_human" and motor.humano_assumiu(session):
        # 🔴 A ATENDENTE ASSUMIU: "nada mais sai". Sem retomada, sem
        #    dossiê, sem aviso ao segurado — a atendente está com o caso. Quando a
        #    URA encerra, o número da seguradora é liberado para a fila.
        if session.get("seguradora_encerrou"):
            await save_active_dispatch(company_id, from_phone, session)
            await clear_active_dispatch(company_id, from_phone)
            await _start_next_in_queue(company_id, from_phone, send_to_insurer, send_to_client)
        else:
            await save_active_dispatch(company_id, from_phone, session)
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
        # 🔴 SPEC-085 BLOCO D — a condição sai de UMA família para as DEZESSEIS.
        #
        # 📊 Era `reason == "insurer_closed"`: das 16 famílias de motivo, UMA
        # tinha retomada. As outras quinze caíam direto em avisar cliente →
        # dossiê → gravar, e ninguém tentava de novo — inclusive
        # `formulario_envio_falhou`, que é a família em que a causa mais
        # obviamente pode ter mudado (rede, instância, timeout).
        #
        # ⚠️ Os TRÊS FREIOS continuam, e são os mesmos: política da família,
        # teto de uma tentativa, e nunca depois do protocolo capturado. Eles
        # foram para `pode_retomar`, no núcleo puro, porque a §F0.3 cobra o
        # gate por FAMÍLIA e isso tem de ser percorrível sem banco nem rede.
        if _motor().pode_retomar(session):
            # 🔴 O TETO CONTA A TENTATIVA, NÃO O SUCESSO — painel da SPEC-085.
            #
            # `retry_count = 1` só era escrito DENTRO de `if retry.get("ok")`.
            # Uma retomada que FALHASSE deixava o contador em 0, e o próximo
            # inbound passava por `pode_retomar` de novo: **o teto de UMA
            # tentativa só valia quando a tentativa dava certo.**
            #
            # ⚠️ Marcado ANTES de tentar. E o que impede o laço quando a
            # tentativa FALHA não é esta marca — é a sessão deixar de existir.
            #
            # 📊 Medido pelo juiz de confirmação: no fall-through desta família
            # o código chama `clear_active_dispatch` e **nunca**
            # `save_active_dispatch`, então `retry_count` morre na memória. O
            # próximo inbound da seguradora não acha sessão nenhuma e não chega
            # aqui. O freio existe; ele só não é o que este comentário dizia.
            #
            # Fica assim de propósito: persistir a marca exigiria regravar uma
            # sessão que acabou de ser limpa, e sessão limpa é o que impede a
            # "sessão zumbi" de 12/07 de voltar a falar com a seguradora.
            session["retry_count"] = int(session.get("retry_count") or 0) + 1
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
                retry["session"]["retry_count"] = int(session.get("retry_count") or 1)
                await save_active_dispatch(company_id, from_phone, retry["session"])
                logger.info(f"[DISPATCH ROUTER] insurer_closed -> auto-retry iniciado case={session.get('case_id')}")
                return True
        # 🔴 SPEC-085 BLOCO C.1 — O AVISO AO SEGURADO DESCEU PARA DEPOIS DO DOSSIÊ.
        #
        # Ele saía AQUI, antes de qualquer tentativa de avisar alguém, e saía
        # IGUAL nos dois casos: *"um colega da equipe vai assumir daqui a
        # pouquinho"*. Numa corretora sem destino de suporte isso é uma promessa
        # sobre uma pessoa que não existe.
        #
        # ⚠️ A ordem é a da §4 da SPEC, e ela é deliberada: **primeiro exista o
        # colega, depois se promete o colega.** Ver o envio, logo abaixo do
        # dossiê.

        # DOSSIÊ MASTIGADO para o suporte humano da corretora (1x por sessão).
        if not session.get("dossier_sent"):
            # 🔴 SPEC-085 BLOCO B.2/B.3 — o resolvedor COMPLETO, não só o destino.
            #
            # `_support_contact` devolve string vazia tanto para "não existe"
            # quanto para "existe e foi RECUSADO por ser compartilhado". São
            # caminhos de código diferentes e dão instruções OPOSTAS à
            # corretora:
            #
            #   ausente   → CADASTRE um destino em Personalização → Suporte
            #   recusado  → PARE DE COMPARTILHAR o destino que você já tem
            #
            # Fundir os dois num `sem_destino_de_suporte` só apaga a diferença
            # que decide o que a pessoa faz.
            alvo = await resolver_destino_de_suporte(company_id)
            support = str(alvo.get("destino") or "")
            if support:
                # 🔴 BLOCO B.1 — o caminho B passa pelo MESMO marcador e teto do
                # caminho A. O `dossier_sent` desta sessão já impedia repetição
                # DENTRO dela; o marcador impede repetição ENTRE sessões — uma
                # retomada, ou um acionamento novo do mesmo caso em menos de
                # seis horas, mandava um segundo dossiê ao grupo.
                tentou = {"chamado": False, "ok": False}

                # 🔴 SPEC-EXTRA-001.3 — 3º dos 11 pontos, pela PORTA ÚNICA.
                #
                # ⚠️ `send_to_client` é o transporte do SEGURADO e não conhece
                # `bloco_unico`: por aqui o dossiê chegava PICOTADO ao grupo.
                # 📊 429 caracteres viram 4 balões (136 · 16 · 69 · 201) e a
                # atendente lê o último, que é o menos importante.
                async def _enviar(texto: str) -> bool:
                    # 🔴 SPEC-EXTRA-001.4 — o import que faltava. 📊 Desde 16/09
                    #    (`21f2243`) `get_supabase_client` não existia neste escopo:
                    #    o NameError subia de `entregar_dossie_uma_vez` e derrubava o
                    #    bloco inteiro — sem dossiê, sem aviso ao segurado, sem gravar.
                    from app.core.database import get_supabase_client
                    from app.services.o_grupo_so_o_que_importa import (
                        TIPO_PEDIDO_DE_AJUDA, enviar_ao_grupo,
                    )

                    tentou["chamado"] = True
                    saida = await enviar_ao_grupo(
                        get_supabase_client(), company_id=str(company_id),
                        tipo=TIPO_PEDIDO_DE_AJUDA, texto=texto, destino=support,
                        conversation_id=str(session.get("mirror_conversation_id") or ""),
                        telefone=str(session.get("client_phone") or ""),
                        sessao=session,
                        dedup=False,
                        resumo="pedido de ajuda — caso %s"
                               % str(session.get("case_id") or "")[:8],
                        motivo=str(reason or ""))
                    tentou["ok"] = bool(saida.get("enviado"))
                    return bool(saida.get("enviado") or saida.get("calado"))

                saiu = await entregar_dossie_uma_vez(
                    session, build_handoff_dossier(session, reason), _enviar,
                    company_id=str(company_id))
                session["dossier_sent"] = bool(saiu)
                if tentou["chamado"] and not tentou["ok"]:
                    # ⚠️ Montado e NÃO saiu. Isso não é "sem destino" — é falha
                    # de envio, e some do log em cinco minutos se não virar
                    # estado. São instruções diferentes para a corretora.
                    session["suporte_indisponivel"] = "envio_falhou"
                elif saiu:
                    session.pop("suporte_indisponivel", None)
            else:
                # 🔴 DEIXA DE SER UM `warning`. Um estado que só existe no log
                # é um estado que ninguém vê — é a SPEC inteira em miniatura.
                # Ele viaja no retrato durável (`output_summary` /
                # `output_redacted`) e é o que a Fila do BLOCO E lê.
                session["suporte_indisponivel"] = (
                    "recusado" if alvo.get("recusa") else "ausente")
                session["suporte_indisponivel_motivo"] = str(
                    alvo.get("recusa") or
                    "nenhum destino de suporte cadastrado para esta corretora")[:200]
                logger.error(
                    "[DISPATCH ROUTER] handoff SEM destino (%s) para a company "
                    "%s — o dossiê foi montado e NÃO tem para onde ir. %s",
                    session["suporte_indisponivel"], company_id,
                    session["suporte_indisponivel_motivo"])

        # 🔴 SPEC-085 BLOCO C.2 — E SÓ AGORA O SEGURADO OUVE, pelo que
        # REALMENTE aconteceu. `aviso_de_handoff` mora no motor porque as três
        # cadeias fazem a mesma pergunta, e a resposta tem de ser a mesma: um
        # `if` copiado em três lugares é onde a terceira cópia diverge.
        client_phone = str(session.get("client_phone") or "").strip()
        if client_phone and not session.get("client_notified_handoff"):
            try:
                send_to_client(client_phone,
                               _motor().aviso_de_handoff(bool(session.get("dossier_sent"))))
                # ⚠️ A flag só é marcada DEPOIS do envio — e é ela que o
                # `build_handoff_dossier` lê para dizer ao humano se o cliente
                # já sabe. Marcá-la antes produziria as duas mentiras de uma vez.
                session["client_notified_handoff"] = True
            except Exception as e:  # noqa: BLE001
                logger.error("[DISPATCH ROUTER] handoff notify failed: %s",
                             type(e).__name__)
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
