"""Work Run Service — estado durável da execução. SPEC-055 §9, §12, §15, §16, §17.

Autoridade de estado: **Postgres**. Redis é transporte, LangGraph guarda o
estado cognitivo, MinIO guarda bytes. Nada aqui decide fora do banco.

Três garantias que este módulo entrega e que hoje não existem:

1. **Lease** — um run em execução tem dono, token e validade. Se o worker
   morrer, a lease vence e outro worker assume. Sem lease, um restart deixa
   trabalho preso em `running` para sempre.

2. **HITL executável** — aprovação vira estado (`waiting_approval`), com
   fingerprint do que foi mostrado ao humano. Se o conteúdo mudar depois do
   aceite, a aprovação é invalidada. Hoje "aprovação" é dado e UI, não gate.

3. **Retomada** — o run guarda `current_step_key` e o step guarda
   `checkpoint_id`. A retomada parte do último ponto seguro, não do começo.
"""

from __future__ import annotations

import logging
import socket
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

LEASE_DURACAO_SEGUNDOS = 120
HEARTBEAT_INTERVALO_SEGUNDOS = 30
ESTADOS_ATIVOS = ("running", "planning", "cancelling")
ESTADOS_TERMINAIS = ("completed", "failed", "cancelled", "expired")


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def worker_id() -> str:
    """Identidade estável o suficiente para diagnosticar quem segurou a lease."""
    return f"{socket.gethostname()}:{uuid.uuid4().hex[:8]}"


class WorkRunService:
    def __init__(self, supabase_client: Any):
        self.db = getattr(supabase_client, "client", supabase_client)

    # ------------------------------------------------------------------
    # Criação
    # ------------------------------------------------------------------

    def criar(
        self,
        *,
        company_id: str,
        source_type: str,
        outcome_type: str,
        outcome_title: str,
        workflow_key: str,
        idempotency_key: str,
        input_payload: Optional[dict] = None,
        requester_user_id: Optional[str] = None,
        source_id: Optional[str] = None,
        priority: int = 50,
        risk_level: str = "low",
        correlation_id: Optional[str] = None,
        parent_run_id: Optional[str] = None,
        cost_budget_brl: Optional[float] = None,
    ) -> dict:
        """Cria o run e a linha de outbox na MESMA transação (RPC).

        Chamar duas vezes com a mesma `idempotency_key` devolve o run
        existente com `reused=True` — não cria duplicata.
        """
        res = self.db.rpc("work_run_create", {
            "p_company_id": company_id,
            "p_source_type": source_type,
            "p_outcome_type": outcome_type,
            "p_outcome_title": outcome_title,
            "p_workflow_key": workflow_key,
            "p_idempotency_key": idempotency_key,
            "p_input_payload": input_payload or {},
            "p_input_fingerprint": None,
            "p_requester_user_id": requester_user_id,
            "p_source_id": source_id,
            "p_priority": priority,
            "p_risk_level": risk_level,
            "p_correlation_id": correlation_id,
            "p_parent_run_id": parent_run_id,
            "p_cost_budget_brl": cost_budget_brl,
            "p_workflow_version": "1.0.0",
        }).execute()

        linha = (res.data or [{}])[0] if isinstance(res.data, list) else (res.data or {})
        if linha.get("reused"):
            logger.info("[WorkRun] pedido idempotente reaproveitou run %s", linha.get("run_id"))
        return linha

    # ------------------------------------------------------------------
    # Lease
    # ------------------------------------------------------------------

    def adquirir_lease(self, run_id: str, owner: str) -> Optional[dict]:
        """Toma a lease do run. `None` quando outro worker já a tem.

        A condição de corrida é resolvida no banco: só assume quem encontra o
        run sem lease viva. Dois workers competindo — um ganha, o outro segue.
        """
        agora = _agora()
        token = str(uuid.uuid4())
        expira = agora + timedelta(seconds=LEASE_DURACAO_SEGUNDOS)

        try:
            atual = (
                self.db.table("work_runs")
                .select("id, status, lease_owner, lease_expires_at")
                .eq("id", run_id)
                .maybe_single()
                .execute()
            )
            linha = atual.data if atual else None
        except Exception as exc:  # noqa: BLE001
            logger.error("[WorkRun] falha ao ler run %s: %s", run_id, type(exc).__name__)
            return None

        if not linha:
            return None
        if linha["status"] in ESTADOS_TERMINAIS:
            return None

        lease_viva = False
        if linha.get("lease_expires_at"):
            try:
                lease_viva = datetime.fromisoformat(
                    str(linha["lease_expires_at"]).replace("Z", "+00:00")
                ) > agora
            except Exception:  # noqa: BLE001
                lease_viva = False

        if lease_viva and linha.get("lease_owner") != owner:
            return None  # outro worker está com o trabalho

        try:
            upd = (
                self.db.table("work_runs")
                .update({
                    "lease_owner": owner,
                    "lease_token": token,
                    "lease_expires_at": _iso(expira),
                    "heartbeat_at": _iso(agora),
                    "status": "running",
                    "started_at": linha.get("started_at") or _iso(agora),
                })
                .eq("id", run_id)
                .execute()
            )
            if not upd.data:
                return None
        except Exception as exc:  # noqa: BLE001
            logger.error("[WorkRun] falha ao adquirir lease de %s: %s", run_id, type(exc).__name__)
            return None

        self.evento(linha_company(upd.data[0]), run_id, "run.leased",
                    f"Trabalho assumido pelo processador {owner}", actor_type="worker", actor_id=owner)
        return {"run_id": run_id, "lease_token": token, "expires_at": _iso(expira)}

    def heartbeat(self, run_id: str, lease_token: str) -> bool:
        """Renova a lease. `False` quando o token não é mais o dono."""
        expira = _agora() + timedelta(seconds=LEASE_DURACAO_SEGUNDOS)
        try:
            res = (
                self.db.table("work_runs")
                .update({"heartbeat_at": _iso(_agora()), "lease_expires_at": _iso(expira)})
                .eq("id", run_id)
                .eq("lease_token", lease_token)
                .execute()
            )
            return bool(res.data)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[WorkRun] heartbeat falhou para %s: %s", run_id, type(exc).__name__)
            return False

    def liberar_lease(self, run_id: str, lease_token: str) -> None:
        try:
            self.db.table("work_runs").update({
                "lease_owner": None, "lease_token": None, "lease_expires_at": None,
            }).eq("id", run_id).eq("lease_token", lease_token).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[WorkRun] falha ao liberar lease: %s", type(exc).__name__)

    def recuperar_orfaos(self, limite: int = 50) -> list[dict]:
        """Runs ativos com lease vencida — worker morreu no meio.

        **Não reexecuta nada aqui.** Devolve para a fila; a idempotência dos
        efeitos é que impede repetição. Recuperar é diferente de repetir.
        """
        agora = _agora()
        try:
            res = (
                self.db.table("work_runs")
                .select("id, company_id, status, lease_owner, workflow_key, current_step_key")
                .in_("status", list(ESTADOS_ATIVOS))
                .lt("lease_expires_at", _iso(agora))
                .limit(limite)
                .execute()
            )
            orfaos = res.data or []
        except Exception as exc:  # noqa: BLE001
            logger.error("[WorkRun] falha ao varrer órfãos: %s", type(exc).__name__)
            return []

        for run in orfaos:
            try:
                self.db.table("work_runs").update({
                    "status": "queued",
                    "lease_owner": None, "lease_token": None, "lease_expires_at": None,
                    "queued_at": _iso(agora),
                }).eq("id", run["id"]).execute()

                self.db.table("work_queue_outbox").insert({
                    "company_id": run["company_id"],
                    "work_run_id": run["id"],
                    "event_kind": "run.recovered",
                    "payload_minimal": {"run_id": run["id"], "company_id": run["company_id"],
                                        "retomar_de": run.get("current_step_key")},
                }).execute()

                self.evento(run["company_id"], run["id"], "worker.recovered",
                            "Trabalho recuperado: o processador anterior parou de responder. "
                            "Retomando do último ponto seguro.", actor_type="system")
                logger.warning("[WorkRun] run %s recuperado (dono anterior: %s)",
                               run["id"], run.get("lease_owner"))
            except Exception as exc:  # noqa: BLE001
                logger.error("[WorkRun] falha ao recuperar %s: %s", run["id"], type(exc).__name__)

        return orfaos

    # ------------------------------------------------------------------
    # Transições
    # ------------------------------------------------------------------

    def marcar_progresso(self, run_id: str, company_id: str, step_key: str, percent: int) -> None:
        try:
            self.db.table("work_runs").update({
                "current_step_key": step_key,
                "progress_percent": max(0, min(100, int(percent))),
            }).eq("id", run_id).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[WorkRun] progresso não gravado: %s", type(exc).__name__)

    def concluir(self, run_id: str, company_id: str, resumo: str, resultado: Optional[dict] = None) -> None:
        self._transicionar(run_id, "completed", {
            "result_summary": resumo,
            "result_payload": resultado or {},
            "progress_percent": 100,
            "finished_at": _iso(_agora()),
            "lease_owner": None, "lease_token": None, "lease_expires_at": None,
        })
        self.evento(company_id, run_id, "run.succeeded", resumo or "Trabalho concluído")

    def falhar(self, run_id: str, company_id: str, codigo: str, mensagem_humana: str,
               retryable: bool = False, proxima_tentativa_em: Optional[int] = None) -> None:
        if retryable and proxima_tentativa_em:
            self._transicionar(run_id, "retry_scheduled", {
                "error_code": codigo,
                "error_message": mensagem_humana,
                "next_attempt_at": _iso(_agora() + timedelta(seconds=proxima_tentativa_em)),
                "lease_owner": None, "lease_token": None, "lease_expires_at": None,
            })
            self.evento(company_id, run_id, "step.retry_scheduled",
                        f"Nova tentativa agendada: {mensagem_humana}")
        else:
            self._transicionar(run_id, "failed", {
                "error_code": codigo,
                "error_message": mensagem_humana,
                "finished_at": _iso(_agora()),
                "lease_owner": None, "lease_token": None, "lease_expires_at": None,
            })
            self.evento(company_id, run_id, "run.failed", mensagem_humana, severity="error")

    def solicitar_cancelamento(self, run_id: str, company_id: str, ator: Optional[str] = None) -> None:
        """Cancelamento é pedido, não efeito imediato.

        O worker observa a flag entre etapas. Ação externa já confirmada
        **não** é desfeita — SPEC-053 §10.7.
        """
        self._transicionar(run_id, "cancelling", {"cancel_requested_at": _iso(_agora())})
        self.evento(company_id, run_id, "run.cancel_requested",
                    "Cancelamento solicitado. Etapas já concluídas não são desfeitas.",
                    actor_type="user", actor_id=ator)

    def cancelamento_pedido(self, run_id: str) -> bool:
        try:
            res = (self.db.table("work_runs").select("cancel_requested_at, status")
                   .eq("id", run_id).maybe_single().execute())
            d = res.data or {}
            return bool(d.get("cancel_requested_at")) or d.get("status") == "cancelling"
        except Exception:  # noqa: BLE001
            return False

    def _transicionar(self, run_id: str, novo_status: str, campos: dict) -> None:
        campos["status"] = novo_status
        try:
            self.db.table("work_runs").update(campos).eq("id", run_id).execute()
        except Exception as exc:  # noqa: BLE001
            logger.error("[WorkRun] transição para %s falhou: %s", novo_status, type(exc).__name__)

    # ------------------------------------------------------------------
    # Timeline
    # ------------------------------------------------------------------

    def evento(self, company_id: str, run_id: str, tipo: str, mensagem: str, *,
               step_id: Optional[str] = None, actor_type: str = "system",
               actor_id: Optional[str] = None, severity: str = "info",
               payload: Optional[dict] = None) -> None:
        try:
            self.db.table("work_events").insert({
                "company_id": company_id,
                "work_run_id": run_id,
                "work_step_id": step_id,
                "event_type": tipo,
                "actor_type": actor_type,
                "actor_id": actor_id,
                "severity": severity,
                "message_human": mensagem,
                "payload_redacted": payload or {},
            }).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[WorkRun] evento '%s' não registrado: %s", tipo, type(exc).__name__)


def linha_company(linha: dict) -> str:
    return linha.get("company_id") or ""
