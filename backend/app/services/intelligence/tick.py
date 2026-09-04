"""Agendamento do Intelligence Fabric. SPEC-059 §28.

Nenhum agendador novo
---------------------
O CLAUDE.md §5 proíbe criar scheduler paralelo, e a SPEC-059 §0.1 repete. O
laço de manutenção do **Smith Worker** já existe e já roda a cada 5 minutos
(SPEC-055 §11) — foi ele que absorveu a reconferência do corpus normativo na
SPEC-057. É ele quem chama isto.

O que o tick faz, e o que ele deliberadamente NÃO faz
----------------------------------------------------
Ele **enfileira Work Runs**; não executa trabalho. A execução é do Work OS,
com lease, heartbeat e retomada. Se este processo morrer no meio do tick, o
pior que acontece é um Work Run já criado ser executado por outro worker — que
é exatamente o comportamento desejado.

A idempotência mora na `idempotency_key` de cada Work Run: ela carrega o
período. Dois ticks no mesmo minuto, dois workers concorrentes ou um restart
produzem **um** run, porque a SPEC-055 devolve o run existente em vez de criar
outro.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, time, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Intervalos mínimos entre execuções do mesmo tipo, por corretora.
INTERVALO_DETECCAO_HORAS = 1
INTERVALO_GARIMPO_HORAS = 24
INTERVALO_MEDICAO_HORAS = 6
INTERVALO_CLUSTER_HORAS = 24
# SPEC-093-B BLOCO C: o digest da sombra de sinistro. Diário, pelo modelo do
# `garimpo` — ⛔ NÃO pelo do `daily_briefing`, que exige perfil e horário e faria
# um trabalho de observação depender de configuração que a corretora nunca fez.
INTERVALO_CLAIMS_SHADOW_HORAS = 24
# 🔴 SPEC-094.1 BLOCO B: o censo do mercado (SUSEP SES). SEMANAL, e de
# PLATAFORMA — o molde e o do `cluster_demand`, e nao o por corretora: a
# estatistica publica e UMA para todas, e com o molde por tenant seriam N
# downloads do mesmo arquivo de 571 MB por semana. 📊 A fonte publica com
# `Last-Modified` semanal (31/08/2026 na medicao do BLOCO 0).
INTERVALO_SES_HORAS = 168


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def habilitado() -> bool:
    return str(os.getenv("INTELLIGENCE_TICK", "1")).strip().lower() \
        in ("1", "true", "yes", "on")


def _tz(nome: str):
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(nome or "America/Sao_Paulo")
    except Exception:  # noqa: BLE001
        return timezone(timedelta(hours=-3))


def _hora(texto: str, padrao: time) -> time:
    try:
        h, m = str(texto).split(":")[:2]
        return time(int(h), int(m))
    except Exception:  # noqa: BLE001
        return padrao


def deve_publicar_briefing(perfil: dict, agora: datetime,
                           ultima_publicacao: Optional[datetime]) -> bool:
    """Puro: chegou a hora agendada e ainda não publicou este período?

    A janela é de uma hora após o horário: o tick roda a cada 5 minutos, mas o
    worker pode ficar indisponível. Exigir o minuto exato faria o briefing
    simplesmente não sair no dia em que houvesse um deploy às 8h.
    """
    if not perfil.get("is_active", True):
        return False
    tz = _tz(perfil.get("timezone") or "America/Sao_Paulo")
    local = agora.astimezone(tz)
    agenda = perfil.get("schedule_spec") or {}
    alvo = _hora(agenda.get("time") or "08:00", time(8, 0))

    if perfil.get("cadence") == "weekly":
        dia = int(agenda.get("weekday", 0))
        if local.weekday() != dia:
            return False

    momento = local.replace(hour=alvo.hour, minute=alvo.minute,
                            second=0, microsecond=0)
    if local < momento or (local - momento) > timedelta(hours=1):
        return False

    if ultima_publicacao is None:
        return True
    ultima_local = ultima_publicacao.astimezone(tz)
    if perfil.get("cadence") == "weekly":
        return (local - ultima_local) >= timedelta(days=6)
    return ultima_local.date() < local.date()


class IntelligenceTick:
    """Enfileira o trabalho de inteligência que venceu."""

    def __init__(self, supabase_client: Any):
        self.db = getattr(supabase_client, "client", supabase_client)
        self._raw = supabase_client

    # ------------------------------------------------------------------

    def executar(self, *, agora: Optional[datetime] = None) -> dict:
        if not habilitado():
            return {"pulado": "INTELLIGENCE_TICK desligado"}
        agora = agora or _agora()
        resultado = {"deteccao": 0, "briefings": 0, "garimpo": 0,
                     "medicao": 0, "cluster": 0, "sombra_sinistros": 0,
                     "censo_do_mercado": 0, "expirados": 0}

        empresas = self._empresas()
        for empresa in empresas:
            company_id = str(empresa["id"])
            try:
                if self._agendar(company_id, "intelligence.detect_signals",
                                 "Procurar o que mudou na operação",
                                 self._janela(agora, INTERVALO_DETECCAO_HORAS)):
                    resultado["deteccao"] += 1
                if self._agendar(company_id, "intelligence.garimpo",
                                 "Escutar a voz do corretor",
                                 self._janela(agora, INTERVALO_GARIMPO_HORAS)):
                    resultado["garimpo"] += 1
                if self._agendar(company_id, "intelligence.measure_outcomes",
                                 "Medir o resultado do que foi feito",
                                 self._janela(agora, INTERVALO_MEDICAO_HORAS)):
                    resultado["medicao"] += 1
                if self._agendar(company_id, "intelligence.claims_shadow_digest",
                                 "Agrupar as sombras de sinistro",
                                 self._janela(agora, INTERVALO_CLAIMS_SHADOW_HORAS)):
                    resultado["sombra_sinistros"] += 1
                resultado["briefings"] += self._briefings(company_id, agora)
            except Exception as exc:  # noqa: BLE001
                # Uma corretora com problema não pode travar o tick das outras.
                logger.warning("[Tick] corretora %s falhou: %s",
                               company_id[:8], type(exc).__name__)

        # 🔴 A corretora ANCORA do trabalho de plataforma. Ela não é "a
        # primeira que veio": a leitura de corretoras não tem `order by`, e
        # `empresas[0]` mudava com a ordem do banco. O trabalho é o mesmo para
        # todas — o que a linha precisa é de um `company_id` ESTÁVEL.
        ancora = min((str(e["id"]) for e in empresas), default="")

        # Plataforma: agrupamento de demanda roda uma vez por dia, fora do
        # escopo de qualquer tenant — §19 é visão agregada, não de corretora.
        try:
            if ancora and self._agendar(
                    ancora, "intelligence.cluster_demand",
                    "Agrupar a demanda das corretoras",
                    self._janela(agora, INTERVALO_CLUSTER_HORAS),
                    escopo="plataforma"):
                resultado["cluster"] += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Tick] cluster de demanda: %s", type(exc).__name__)

        # SPEC-094.1 BLOCO B: o censo do mercado. 🔴 Mesmo molde de PLATAFORMA
        # do cluster — `escopo="plataforma"` e a janela SEMANAL. Quem baixa é o
        # WORKER, sob lease com heartbeat; o tick só cria o Work Run.
        try:
            if ancora and self._agendar(
                    ancora, "intelligence.susep_ses_ingest",
                    "Atualizar o censo do mercado",
                    self._janela(agora, INTERVALO_SES_HORAS),
                    escopo="plataforma"):
                resultado["censo_do_mercado"] += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Tick] censo do mercado: %s", type(exc).__name__)

        resultado["expirados"] = self._expirar()
        return resultado

    # ------------------------------------------------------------------

    def _empresas(self) -> list[dict]:
        """Corretoras reais. A empresa técnica fica de fora do proativo.

        Mandar briefing para o sandbox técnico gastaria modelo para produzir
        um relatório que ninguém lê — e poluiria a métrica de qualidade com
        dado que não é de corretora.
        """
        try:
            r = (self.db.table("companies").select("id, company_name, is_technical")
                 .limit(300).execute())
            return [c for c in (r.data or []) if not c.get("is_technical")]
        except Exception as exc:  # noqa: BLE001
            logger.error("[Tick] leitura de corretoras falhou: %s", type(exc).__name__)
            return []

    def _janela(self, agora: datetime, horas: int) -> str:
        """Rótulo estável do período. É o que torna o Work Run idempotente.

        🔴 SPEC-094.1 BLOCO B: **a cadência semanal precisa de rótulo semanal.**
        Até aqui, qualquer `horas >= 24` virava o rótulo do DIA — e um trabalho
        de 168 h com rótulo diário ganharia uma chave de idempotência nova a
        cada meia-noite. O efeito não seria "rodar mais": seria **baixar 571 MB
        todo dia** achando que é semanal.

        ⚠️ `%G-W%V` (ano ISO + semana ISO), e não `%Y-W%W`: na virada do ano as
        duas discordam — 31/12 pode ser a semana 1 do ano seguinte, e com `%Y` o
        rótulo saltaria para trás e reagendaria o mesmo trabalho.
        `_briefings` continua com `%Y-W%W` porque é a chave que já está gravada
        nos runs dele; trocá-la reagendaria o briefing de todo mundo uma vez.

        ```
        horas >= 168   2026-W36        a semana ISO
        24..167        2026-09-03      o dia
        < 24           2026-09-03T12   a fatia do dia
        ```
        """
        if horas >= 168:
            return agora.strftime("%G-W%V")
        if horas >= 24:
            return agora.strftime("%Y-%m-%d")
        marca = (agora.hour // max(1, horas)) * max(1, horas)
        return f"{agora.strftime('%Y-%m-%d')}T{marca:02d}"

    def _agendar(self, company_id: str, workflow_key: str, titulo: str,
                 janela: str, *, escopo: str = "tenant",
                 payload: Optional[dict] = None) -> bool:
        """Cria o Work Run se ainda não existe para esta janela."""
        from ..work.runs import WorkRunService

        # 🔴 SPEC-094.1, conserto de 04/09/2026 — a chave de PLATAFORMA nao
        # leva corretora.
        #
        # 📊 O defeito: `intel:plataforma:susep_ses_ingest:{company_id}:{janela}`
        # carregava `empresas[0]` — a PRIMEIRA linha que a leitura de corretoras
        # devolveu, numa consulta **sem `order by`**. Uma corretora nova, uma
        # marcada como tecnica, ou simplesmente outra ordem do Postgres trocava
        # o `company_id` da chave: a idempotencia caia, e o trabalho de
        # PLATAFORMA — que baixa 571 MB de arquivo publico uma vez por semana —
        # era reagendado do zero. O sintoma nao e erro: e banda.
        #
        # ⚠️ O `company_id` continua na LINHA (a coluna e obrigatoria e a
        # corretora ancora e escolhida de forma estavel); o que saiu foi da
        # CHAVE, que e o que decide se o trabalho ja existe.
        #
        # ⚠️ E a chave do `cluster_demand` muda junto, porque ele usa o mesmo
        # molde de plataforma: ele roda UMA vez a mais na janela da implantacao,
        # e nunca mais.
        chave = (f"intel:{escopo}:{workflow_key}:{janela}"
                 if escopo == "plataforma"
                 else f"intel:{escopo}:{workflow_key}:{company_id}:{janela}")
        try:
            r = WorkRunService(self._raw).criar(
                company_id=company_id,
                source_type="system",
                source_id=workflow_key,
                outcome_type="intelligence.cycle",
                outcome_title=titulo,
                workflow_key=workflow_key,
                idempotency_key=chave,
                input_payload=payload or {},
                priority=60,
                risk_level="low")
            return bool(r.get("run_id")) and not r.get("reused")
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Tick] não consegui agendar %s: %s",
                           workflow_key, type(exc).__name__)
            return False

    def _briefings(self, company_id: str, agora: datetime) -> int:
        criados = 0
        for cadencia, workflow, tipo, titulo in (
            ("daily", "intelligence.daily_briefing", "daily_operational",
             "Briefing do dia"),
            ("weekly", "intelligence.weekly_executive_briefing", "weekly_executive",
             "Briefing executivo da semana"),
        ):
            perfil = self._perfil(company_id, cadencia)
            if not perfil:
                continue
            ultima = self._ultima_publicacao(company_id, tipo)
            if not deve_publicar_briefing(perfil, agora, ultima):
                continue
            janela = (agora.strftime("%Y-%m-%d") if cadencia == "daily"
                      else agora.strftime("%Y-W%W"))
            if self._agendar(company_id, workflow, titulo, janela):
                criados += 1
        return criados

    def _perfil(self, company_id: str, cadencia: str) -> Optional[dict]:
        """Perfil ativo da corretora. Criado sob demanda pelo BriefingService."""
        from .briefing_service import BriefingService

        try:
            return BriefingService(self._raw).perfil(company_id, cadencia=cadencia)
        except Exception:  # noqa: BLE001
            return None

    def _ultima_publicacao(self, company_id: str, tipo: str) -> Optional[datetime]:
        try:
            r = (self.db.table("briefing_publications").select("published_at")
                 .eq("company_id", company_id).eq("briefing_type", tipo)
                 .eq("status", "published")
                 .order("published_at", desc=True).limit(1).execute())
            if not r.data:
                return None
            d = datetime.fromisoformat(
                str(r.data[0]["published_at"]).replace("Z", "+00:00"))
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except Exception:  # noqa: BLE001
            return None

    def _expirar(self) -> int:
        """Varre validade de sinais, findings e recomendações — §11.5."""
        total = 0
        try:
            from .finding_engine import FindingEngine
            from .recommendation_service import RecommendationService
            from .signal_service import SignalService

            total += SignalService(self._raw).expirar_vencidos()
            total += FindingEngine(self._raw).expirar_vencidos()
            total += RecommendationService(self._raw).expirar_vencidas()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Tick] expiração falhou: %s", type(exc).__name__)
        return total


def rodar(supabase_client: Any) -> dict:
    """Ponto de entrada chamado pelo laço de manutenção do Smith Worker."""
    return IntelligenceTick(supabase_client).executar()
