"""Heartbeats e REGISTRO dos trabalhadores digitais (SPEC-036 Etapa 1 · SPEC-088 BLOCO A).

Cada task (Vigia/Sentinela, Follow-up, Garimpo, Auditor, Sugestões, Espelho via
router) registra pulso + contador de ações no Redis — a Central de Agentes do
portal admin lê daqui. Best-effort: nunca derruba a task.

🔴 SPEC-088 BLOCO A: `AGENT_TASKS` deixou de ser lista de tuplas `(id, nome, desc)`
e passou a ser o **registro único** dos trabalhadores digitais. Além do nome e da
descrição, cada linha declara:

    grupo               observa | atende_agora | mantem_rota | aprende_avisa
    cor                 🔴 saiu do frontend (`page.tsx` COLORS) e vive AQUI — uma lista só
    eixo                {"pulso": "redis"|"work_runs", "workflow_keys": (...)}
                        pulso = de onde vem o "rodou"; workflow_keys = de onde vem o TRABALHO
    fonte_de_producao   tupla de `Fonte` (o `last_success` do agente) ou **None EXPLÍCITO**
    cadencia_esperada_s de quanto em quanto tempo ele DEVIA produzir; None se não se sabe
    k                   multiplicador do limiar: limiar_s = k × cadencia_esperada_s
    desligado_quando    None, ou {"agents_attendance_all_inactive": True}

⛔ **Não é uma tabela nova.** `max(coluna)` da tabela que o agente já escreve **é** o
histórico. Uma tabela `agent_health` seria um segundo lugar para a verdade (CLAUDE.md §5).

⚠️ `Agente` é um `NamedTuple` cujos TRÊS primeiros campos continuam sendo
`(id, nome, descricao)`: `admin_atlas.py:935` (`{t[0]: t[1] for t in AGENT_TASKS}`) e os
testes da SPEC-040 que fazem `t[0]` seguem funcionando sem uma linha de mudança.
Quem precisa da lista antiga inteira chama `agent_tasks_legacy()`.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

logger = logging.getLogger(__name__)

_KEY = "spec034:heartbeat:{task}"
_TTL = 7 * 86400

# --------------------------------------------------------------------------- #
# Os grupos — por propósito para a corretora, não por tecnologia (SPEC-088 §3 ⑥)
# --------------------------------------------------------------------------- #
GRUPOS: Tuple[Tuple[str, str, str], ...] = (
    ("observa", "OBSERVA E REGISTRA", "o que aconteceu ficou gravado"),
    ("atende_agora", "ATENDE AGORA", "alguém está esperando neste minuto"),
    ("mantem_rota", "MANTÉM A ROTA CERTA", "a seguradora mudou e nós acompanhamos"),
    ("aprende_avisa", "APRENDE E AVISA", "ontem virou conserto e recomendação"),
)


class Fonte(NamedTuple):
    """De onde sai o `last_success` de um trabalhador.

    `tipo`:
      "tabela"            → max(greatest(colunas)) da `tabela`, com `filtro` opcional
      "work_runs_do_eixo" → max(work_runs.finished_at) status='completed' dos workflow_keys DELE
      "artifacts_do_eixo" → max(artifacts.created_at) cujos work_run_id caem nos workflow_keys DELE
    """

    tipo: str
    rotulo: str
    tabela: Optional[str] = None
    colunas: Tuple[str, ...] = ()
    # {"coluna": str, "op": "eq"|"like"|"in", "valor": Any}
    filtro: Optional[Dict[str, Any]] = None


class Agente(NamedTuple):
    """Uma linha do registro. Os 3 primeiros campos são a tupla histórica."""

    id: str
    nome: str
    descricao: str
    grupo: str
    cor: str
    eixo: Dict[str, Any]
    # 🔴 None EXPLÍCITO = "sem tabela própria" → o card sai ⚫ NÃO MEDIDO, nunca 🟢
    fonte_de_producao: Optional[Tuple[Fonte, ...]]
    cadencia_esperada_s: Optional[int]
    desligado_quando: Optional[Dict[str, Any]]
    k: int = 2


def _redis(workflow_keys: Tuple[str, ...] = ()) -> Dict[str, Any]:
    return {"pulso": "redis", "workflow_keys": workflow_keys}


def _por_runs(workflow_keys: Tuple[str, ...]) -> Dict[str, Any]:
    return {"pulso": "work_runs", "workflow_keys": workflow_keys}


def _tab(rotulo: str, tabela: str, *colunas: str, filtro: Optional[Dict[str, Any]] = None) -> Fonte:
    return Fonte(tipo="tabela", rotulo=rotulo, tabela=tabela, colunas=tuple(colunas), filtro=filtro)


_DESLIGA_COM_ATENDIMENTO = {"agents_attendance_all_inactive": True}

# --------------------------------------------------------------------------- #
# 📊 AS FONTES, MEDIDAS EM 03/09/2026 (produção `dcajcvlzcjbmyapmklil`)
#
# Critério (SPEC-088 BLOCO A): a tabela em que o MÓDULO do agente faz INSERT e que
# nenhum outro agente escreve. Se nenhuma, `None` — e o card diz ⚫ "sem tabela própria".
#
#   espelho          → `dispatch_mirror.py` insere em `messages` (:73) e `conversations`
#                      (:155); 📊 `grep -rln 'table("messages").insert'` = 4 módulos
#                      (chat.py, webhook.py, espelho_chat.py, dispatch_mirror.py).
#                      Não é exclusiva → None.
#   vigia_sentinela  → 📊 `grep -n '\.insert(' backend/app/tasks/dispatch_watchdog.py` = 0.
#                      O módulo não faz INSERT em tabela nenhuma → None.
#   cerebro          → `dispatch_router.py` insere `work_runs` (:548), `work_events` (:571)
#                      e `work_steps` (:1042) — as três são do motor de trabalho inteiro,
#                      não dele → None. O TRABALHO dele sai de `acionamento.seguradora`.
#   conselho         → 📊 `grep -n 'table("' backend/app/services/agent_council.py` = 0 → None.
# --------------------------------------------------------------------------- #

AGENT_TASKS: List[Agente] = [
    # ---------------------------------------------------------------- OBSERVA
    Agente(
        "observador", "Observador",
        "Observa em silêncio os atendimentos com as seguradoras e captura cada tela, botão e formulário nativo — nunca envia nada.",
        grupo="observa", cor="#7FB7E8", eixo=_redis(),
        # 📊 observed_events: 28.220 linhas, última 26/08 13:52
        fonte_de_producao=(_tab("observed_events.created_at", "observed_events", "created_at"),),
        cadencia_esperada_s=86400, desligado_quando=None, k=2,
    ),
    Agente(
        "tecelao", "Tecelão",
        "Costura as observações em mapas de rota fiéis à sequência real de cada seguradora.",
        grupo="observa", cor="#B48EAD", eixo=_redis(),
        # 📊 ura_maps: 324 linhas, última 26/08 14:07. ⚠️ compartilhada com o cartógrafo
        # (declaração da SPEC-088 BLOCO A) — está na pendência do relatório.
        fonte_de_producao=(_tab("ura_maps.created_at", "ura_maps", "created_at"),),
        cadencia_esperada_s=604800, desligado_quando=None, k=2,
    ),
    Agente(
        "espelho", "Espelho",
        "Espelha toda conversa com seguradora no banco e no dashboard, em tempo real.",
        grupo="observa", cor="#7FB7E8", eixo=_redis(),
        fonte_de_producao=None,  # 📊 medido: `messages`/`conversations` têm 4 escritores
        cadencia_esperada_s=None, desligado_quando=None, k=2,
    ),
    Agente(
        "espelho_atendimento", "Espelho de Atendimento",
        "Captura as conversas de trabalho da equipe da corretora com os segurados — matéria-prima dos playbooks de conduta e knowledge cards (PII isolada, nunca no RAG).",
        grupo="observa", cor="#43C08C", eixo=_redis(),
        # 📊 attendance_transcripts: 156.917 linhas, última 03/09 01:39
        fonte_de_producao=(_tab("attendance_transcripts.created_at", "attendance_transcripts", "created_at"),),
        cadencia_esperada_s=3600, desligado_quando=None, k=2,
    ),
    Agente(
        "cartografo", "Cartógrafo",
        "Mapeia os fluxos de URA das seguradoras (exploração ativa — só quando não há tráfego real).",
        grupo="observa", cor="#74ACE8", eixo=_redis(),
        fonte_de_producao=(_tab("ura_maps.created_at", "ura_maps", "created_at"),),
        cadencia_esperada_s=604800, desligado_quando=None, k=2,
    ),
    # ----------------------------------------------------------- ATENDE AGORA
    Agente(
        "vigia_sentinela", "Vigia + Sentinela",
        "Vigia o desfecho de todo acionamento; a Sentinela destrava conversas paradas na URA.",
        grupo="atende_agora", cor="#E2A94F", eixo=_redis(),
        fonte_de_producao=None,  # 📊 medido: dispatch_watchdog.py não faz INSERT nenhum
        cadencia_esperada_s=None, desligado_quando=_DESLIGA_COM_ATENDIMENTO, k=2,
    ),
    Agente(
        "cerebro", "Cérebro v2",
        "Decide nos desvios: lê o Mapa da URA e escolhe a opção que avança para o objetivo.",
        grupo="atende_agora", cor="#43C08C",
        # 📊 `acionamento.seguradora`: 4 runs em 30d, sem @registrar_workflow no repo (P-088-KEYS)
        eixo=_redis(("acionamento.seguradora",)),
        fonte_de_producao=None,  # 📊 medido: só escreve as tabelas do motor de trabalho
        cadencia_esperada_s=None, desligado_quando=_DESLIGA_COM_ATENDIMENTO, k=2,
    ),
    # ⚠️ INCOMPLETO, e a descrição diz isso.
    #
    # 📊 03/08/2026: ele PERGUNTA ao segurado se o prestador chegou — e
    # **ninguém lê a resposta**. Ela cai no agente de atendimento comum, que não
    # tem acesso à sessão do acionamento (a chave do acionamento é o telefone da
    # SEGURADORA; o do cliente nunca casa).
    #
    # A descrição antiga prometia "confere se o prestador chegou". Perguntar não
    # é conferir. E o card ficava VERDE, porque o critério da Central era só "o
    # laço rodou". Com a SPEC-088 o critério é o par pulso × produção. Ver P-70.
    Agente(
        "followup", "Follow-up",
        "Pós-acionamento: PERGUNTA ao segurado se o prestador chegou e manda o encerramento. ⚠️ A resposta do cliente ainda não é lida por ninguém — o ciclo não fecha (P-70).",
        grupo="atende_agora", cor="#43C08C", eixo=_redis(),
        # 🔴 A SPEC declarava `platform_sends.created_at` SEM filtro e citava 19/08 19:41.
        # 📊 03/09: aquela linha é `kind='acionamento_protocolo'`, escrita pelo
        # `dispatch_router.py`, não pelo Follow-up. `platform_sends` tem 7 escritores
        # (`grep -rln platform_sends backend/app`). O Follow-up grava
        # `acionamento_followup`/`acionamento_encerramento` (`dispatch_followup.py:322`)
        # e 📊 `SELECT kind, count(*) FROM platform_sends GROUP BY 1` → billing 4,
        # acionamento_protocolo 1. **Zero.** Sem o filtro, o card dele ficaria verde com a
        # produção de outro agente — que é exatamente o defeito desta SPEC. P-088-03.
        fonte_de_producao=(_tab(
            "platform_sends.created_at (kind de follow-up)", "platform_sends", "created_at",
            filtro={"coluna": "kind", "op": "in",
                    "valor": ("acionamento_followup", "acionamento_encerramento")},
        ),),
        cadencia_esperada_s=86400, desligado_quando=_DESLIGA_COM_ATENDIMENTO, k=2,
    ),
    # ------------------------------------------------------------ MANTÉM ROTA
    Agente(
        "sentinela_rotas", "Sentinela de Rotas",
        "Vigia se a seguradora mudou o menu; dispara a atualização e avisa no que for estrutural.",
        grupo="mantem_rota", cor="#74ACE8", eixo=_redis(),
        # 📊 route_drift: 17 linhas, última 26/08 14:07
        fonte_de_producao=(_tab("route_drift.created_at", "route_drift", "created_at"),),
        cadencia_esperada_s=86400, desligado_quando=None, k=2,
    ),
    Agente(
        "alfaiate", "Alfaiate",
        "Ajusta os playbooks quando a URA da seguradora muda — auto-aplica só o que passa no Simulador.",
        grupo="mantem_rota", cor="#B48EAD", eixo=_redis(),
        # 📊 playbook_overlays: 0 linhas, nunca. Cadência declarada de propósito (referência ②
        # da SPEC: quem NUNCA produziu tem de alertar — não há evento para comparar). P-088-02.
        fonte_de_producao=(_tab("playbook_overlays.created_at", "playbook_overlays", "created_at"),),
        cadencia_esperada_s=86400, desligado_quando=None, k=2,
    ),
    # ---------------------------------------------------------- APRENDE E AVISA
    Agente(
        "garimpo", "Garimpo",
        "Extrai dores, desejos e pedidos das conversas dos corretores — vira insight de produto.",
        grupo="aprende_avisa", cor="#43C08C", eixo=_por_runs(("intelligence.garimpo",)),
        # 🔴 `greatest()` das DUAS tabelas e das DUAS colunas: o fluxo canônico grava
        # `intelligence_signals` e projeta em `broker_insights` (`garimpo_v3.py:106-108`),
        # a projeção é condicional ao dedupe, e no acerto de dedupe `signal_service.py:144-167`
        # move `last_seen_at`, não `created_at`. Um garimpo que só reconfirma sinais não move
        # `created_at` — e o card congelaria num agente saudável.
        # 📊 intelligence_signals source_type='garimpo': 32 linhas, última 26/08 00:05.
        # 📊 broker_insights source LIKE 'garimpo%': 270 linhas ('garimpo_v3'), última 26/08 00:05.
        fonte_de_producao=(
            _tab("intelligence_signals.last_seen_at ∪ created_at", "intelligence_signals",
                 "last_seen_at", "created_at",
                 filtro={"coluna": "source_type", "op": "eq", "valor": "garimpo"}),
            _tab("broker_insights.created_at", "broker_insights", "created_at",
                 filtro={"coluna": "source", "op": "like", "valor": "garimpo%"}),
        ),
        cadencia_esperada_s=86400, desligado_quando=None, k=2,
    ),
    Agente(
        "detector", "Detector de Sinais",
        "Varre o que acontece na plataforma e levanta sinais de risco e de oportunidade antes de alguém pedir.",
        grupo="aprende_avisa", cor="#8FBF7A", eixo=_por_runs(("intelligence.detect_signals",)),
        # 📊 intelligence_signals source_type='detector': 59 linhas, última 03/09 02:03
        fonte_de_producao=(
            _tab("intelligence_signals.last_seen_at ∪ created_at", "intelligence_signals",
                 "last_seen_at", "created_at",
                 filtro={"coluna": "source_type", "op": "eq", "valor": "detector"}),
        ),
        cadencia_esperada_s=3600, desligado_quando=None, k=2,
    ),
    Agente(
        "auditor", "Auditor",
        "Dá nota de qualidade a cada conversa e detecta regressões nos corredores.",
        # ⛔ NÃO liga a `intelligence.investigate_quality`: 📊 0 runs em toda a história.
        # O pulso é o de `conversation_auditor.py:180` (Redis, 1×/dia); trabalho vazio.
        grupo="aprende_avisa", cor="#E2A94F", eixo=_redis(),
        # 📊 conversation_scorecards: 688 linhas, última 03/09 00:04
        fonte_de_producao=(_tab("conversation_scorecards.created_at", "conversation_scorecards", "created_at"),),
        cadencia_esperada_s=86400, desligado_quando=None, k=2,
    ),
    Agente(
        "sugestoes", "IA de Sugestões",
        "Envia recomendações semanais proativas às corretoras e registra as respostas.",
        grupo="aprende_avisa", cor="#7FB7E8", eixo=_redis(),
        # 📊 broker_insights source='sugestoes_ia': 0 de 270. Cadência None: não se sabe de
        # quanto em quanto tempo ele DEVIA produzir desde o cutover → ⚫, não um limiar inventado.
        fonte_de_producao=(_tab("broker_insights.created_at", "broker_insights", "created_at",
                                filtro={"coluna": "source", "op": "eq", "valor": "sugestoes_ia"}),),
        cadencia_esperada_s=None, desligado_quando=None, k=2,
    ),
    Agente(
        "conselho", "Conselho de Agentes",
        "Segunda opinião multi-modelo (GPT, Opus, Kimi, Grok) para decisões estruturais raras — liga por env, custo controlado.",
        grupo="aprende_avisa", cor="#E2A94F", eixo=_redis(),
        fonte_de_producao=None,  # 📊 medido: agent_council.py não escreve tabela nenhuma
        cadencia_esperada_s=None, desligado_quando=None, k=2,
    ),
    Agente(
        "briefing", "Briefing",
        "Escreve o resumo diário e o executivo semanal do que aconteceu na corretora — o que mudou, o que exige decisão.",
        grupo="aprende_avisa", cor="#88C0D0",
        eixo=_por_runs(("intelligence.daily_briefing", "intelligence.weekly_executive_briefing")),
        # 📊 artifacts com work_run_id desses dois keys em 7d: daily 21 · weekly 3.
        # A entrega (artifact) é a produção; o run completo é o piso quando não houver artifact.
        fonte_de_producao=(
            Fonte(tipo="artifacts_do_eixo", rotulo="artifacts.created_at (via work_run_id)"),
            Fonte(tipo="work_runs_do_eixo", rotulo="work_runs.finished_at (completed)"),
        ),
        cadencia_esperada_s=86400, desligado_quando=None, k=2,
    ),
    Agente(
        "medidor", "Medidor de Resultados",
        "Mede se o que foi prometido aconteceu: compara o resultado esperado com o que a corretora obteve.",
        grupo="aprende_avisa", cor="#D08770", eixo=_por_runs(("intelligence.measure_outcomes",)),
        # 📊 351 runs completed em 30d, última 03/09 00:01.
        # 🔴 A SPEC declarava 💭 3600s ("horária"). Medido em 03/09 com o intervalo entre
        # runs consecutivos (`lag(created_at)`, 14 dias): 56 horas distintas em 15 dias,
        # intervalo MÁXIMO de 21.879s (6h05) — ele NÃO roda de hora em hora. Com 3600s o
        # card ficaria 🔴 três horas por dia num agente saudável, que é o defeito §1.6
        # (limiar de 900s condenando quem roda 1×/dia) reconstruído. 6h × k=2 = 12h de
        # limiar, o dobro do maior silêncio já observado.
        fonte_de_producao=(Fonte(tipo="work_runs_do_eixo", rotulo="work_runs.finished_at (completed)"),),
        cadencia_esperada_s=21600, desligado_quando=None, k=2,
    ),
    Agente(
        "agrupador", "Agrupador de Demanda",
        "Junta pedidos parecidos de corretoras diferentes e mostra o que muita gente precisa da mesma coisa.",
        grupo="aprende_avisa", cor="#A3BE8C", eixo=_por_runs(("intelligence.cluster_demand",)),
        # 📊 31 runs completed em 30d, última 03/09 00:01
        fonte_de_producao=(Fonte(tipo="work_runs_do_eixo", rotulo="work_runs.finished_at (completed)"),),
        cadencia_esperada_s=86400, desligado_quando=None, k=2,
    ),
]


# --------------------------------------------------------------------------- #
# 🔴 O registro CRESCE, ou a chave é recusada por escrito (SPEC-088 BLOCO A, gate ②)
#
# Todo `workflow_key` visto em `work_runs` nos últimos 30 dias tem trabalhador OU
# está aqui, com o motivo escrito. Lista vazia com chave sem card REPROVA.
# 📊 Medido em 03/09/2026 — chaves com run nos últimos 30 dias:
#   intelligence.detect_signals 2.097 · measure_outcomes 351 · garimpo 90 ·
#   daily_briefing 87 · cluster_demand 31 · weekly_executive_briefing 12 ·
#   bridge.routine.execute 7 · acionamento.seguradora 4
# ⚠️ `test.wf` (1 run) NÃO aparece na janela de 30 dias de hoje — é mais velho. Fica
# declarado assim mesmo: a lista descreve a decisão, não a janela.
# --------------------------------------------------------------------------- #
SEM_CARD_POR_DECISAO: Tuple[Tuple[str, str], ...] = (
    ("test.wf", "lixo de teste, 1 run em toda a história (P-088-KEYS)"),
    ("bridge.routine.execute", "ponte de rotina, contada no auxiliar"),
    ("bridge.auxiliary.execute", "ponte de auxiliar, contada no auxiliar"),
    ("bridge.portal.job", "portal worker, tela própria"),
    ("portal.operation", "portal worker, tela própria"),
    ("research.execute", "pesquisa, tela própria"),
    ("research.monitor_check", "pesquisa, tela própria"),
    ("research.site_audit", "pesquisa, tela própria"),
    ("research.business_discovery", "pesquisa, tela própria"),
    ("research.radar_weekly", "pesquisa, tela própria"),
    ("system.healthcheck", "sonda de plataforma, não é trabalhador"),
    ("intelligence.investigate_failures", "0 runs em 30 dias (medido 03/09/2026)"),
    ("intelligence.investigate_quality", "0 runs em toda a história (medido 03/09/2026)"),
    ("intelligence.memory_sweep", "0 runs em 30 dias (medido 03/09/2026)"),
)


def agente_por_id(agent_id: str) -> Optional[Agente]:
    for a in AGENT_TASKS:
        if a.id == agent_id:
            return a
    return None


def agent_tasks_legacy() -> List[Tuple[str, str, str]]:
    """A lista antiga `(id, nome, descricao)`, para quem ainda a espera inteira."""
    return [(a.id, a.nome, a.descricao) for a in AGENT_TASKS]


def workflow_keys_declarados() -> Dict[str, str]:
    """`workflow_key` → id do trabalhador que o reivindica."""
    out: Dict[str, str] = {}
    for a in AGENT_TASKS:
        for k in a.eixo.get("workflow_keys") or ():
            out[k] = a.id
    return out


def workflow_keys_sem_card(chaves_vistas) -> List[str]:
    """🔴 O gate ② do BLOCO A: as chaves que ninguém reivindicou nem recusou.

    Puro, sem I/O — o guarda passa a lista de chaves vistas em `work_runs` (30 dias)
    e recebe as órfãs, em ordem estável. Lista vazia = registro em dia.
    """
    declarados = set(workflow_keys_declarados())
    recusados = {k for k, _ in SEM_CARD_POR_DECISAO}
    vistas: List[str] = []
    for k in chaves_vistas or ():
        k = str(k or "").strip()
        if k and k not in vistas:
            vistas.append(k)
    return [k for k in vistas if k not in declarados and k not in recusados]


# --------------------------------------------------------------------------- #
# O pulso (Redis) — assinaturas MANTIDAS: 27 call sites dependem delas
# --------------------------------------------------------------------------- #
async def beat(task: str, actions: int = 0) -> None:
    try:
        from app.core.redis import get_async_redis_client

        redis = await get_async_redis_client()
        key = _KEY.format(task=task)
        raw = await redis.get(key)
        data = {}
        if raw:
            try:
                data = json.loads(raw.decode() if isinstance(raw, (bytes, bytearray)) else raw)
            except Exception:  # noqa: BLE001
                data = {}
        today = datetime.now(timezone.utc).date().isoformat()
        if data.get("day") != today:
            data["day"] = today
            data["actions_today"] = 0
        data["last_run"] = datetime.now(timezone.utc).isoformat()
        data["actions_today"] = int(data.get("actions_today") or 0) + max(0, int(actions))
        await redis.set(key, json.dumps(data), ex=_TTL)
    except Exception as e:  # noqa: BLE001
        logger.debug(f"[HEARTBEAT] beat({task}) falhou: {type(e).__name__}")


async def read_all() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        from app.core.redis import get_async_redis_client

        redis = await get_async_redis_client()
        for a in AGENT_TASKS:
            raw = await redis.get(_KEY.format(task=a.id))
            data = {}
            if raw:
                try:
                    data = json.loads(raw.decode() if isinstance(raw, (bytes, bytearray)) else raw)
                except Exception:  # noqa: BLE001
                    data = {}
            out.append({"id": a.id, "name": a.nome, "desc": a.descricao,
                        "last_run": data.get("last_run"), "actions_today": data.get("actions_today") or 0})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[HEARTBEAT] read_all falhou: {type(e).__name__}")
        out = [{"id": a.id, "name": a.nome, "desc": a.descricao, "last_run": None, "actions_today": 0}
               for a in AGENT_TASKS]
    return out
