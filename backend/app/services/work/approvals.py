"""HITL executável — aprovação como gate, não como frase. SPEC-055 §15.

O estado anterior: `approval_requests` existia com dados e UI, mas o grafo não
parava. Aprovar era registro, não bloqueio. A SPEC-053 §11.1 é direta —
*"prompt não é gate"*.

Aqui a aprovação vira estado durável do Work Run:

    passo sensível  →  run entra em `waiting_approval`  →  worker solta a lease
                    →  humano decide na UI
                    →  resume explícito, validando fingerprint

**Fingerprint** é o detalhe que separa aprovação de cheque em branco. O humano
aprova um conteúdo específico. Se o conteúdo mudar entre o aceite e a execução
— reescrita do texto, outro destinatário, outro valor — a aprovação não vale
mais. Sem isso, "aprovado" viraria autorização genérica para qualquer coisa
que o agente decidisse fazer depois.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from .effects import fingerprint

logger = logging.getLogger(__name__)

VALIDADE_PADRAO_HORAS = 24

# SPEC-053 §11.2 — classes de risco
RISCO_SEM_APROVACAO = {"R0", "R1"}
RISCO_APROVACAO_OBRIGATORIA = {"R3", "R4"}


class ApprovalExpired(Exception):
    """A janela de decisão passou. Exige nova solicitação."""


class ApprovalFingerprintMismatch(Exception):
    """O conteúdo mudou depois do aceite. A aprovação não vale para isto."""


class ApprovalNotGranted(Exception):
    """Não existe aprovação válida para esta ação."""


class WorkApprovalService:
    def __init__(self, supabase_client: Any):
        self.db = getattr(supabase_client, "client", supabase_client)

    # ------------------------------------------------------------------

    def precisa_aprovacao(self, *, risk_class: Optional[str], scope: Optional[dict]) -> bool:
        """Decide pelo escopo da capability, não por heurística no prompt.

        A SPEC-054 Bloco C preencheu `requires_approval` e `side_effect` nos 46
        bindings — então isto deixou de ser inferência.
        """
        if scope and scope.get("requires_approval"):
            return True
        if risk_class in RISCO_APROVACAO_OBRIGATORIA:
            return True
        if scope and scope.get("side_effect") and risk_class not in RISCO_SEM_APROVACAO:
            return True
        return False

    # ------------------------------------------------------------------

    def solicitar(
        self,
        *,
        company_id: str,
        work_run_id: str,
        work_step_id: Optional[str],
        action_type: str,
        subject_type: str,
        subject_id: Optional[str],
        preview: dict,
        action_payload: dict,
        risk_level: str = "high",
        idempotency_key: Optional[str] = None,
        requested_by_user_id: Optional[str] = None,
        validade_horas: int = VALIDADE_PADRAO_HORAS,
    ) -> dict:
        """Cria a solicitação e devolve o registro com o fingerprint gravado.

        `preview` é o que o humano vê. `action_payload` é o que será executado.
        O fingerprint cobre o **payload**, porque é ele que produz o efeito.
        """
        agora = datetime.now(timezone.utc)
        expira = agora + timedelta(hours=validade_horas)
        fp = fingerprint(action_payload)

        registro = {
            "company_id": company_id,
            "work_run_id": work_run_id,
            "work_step_id": work_step_id,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "action_type": action_type,
            "status": "pending",
            "risk_level": risk_level,
            "preview": preview,
            "requested_preview": preview,
            "request_payload": action_payload,
            "action_fingerprint": fp,
            "idempotency_key": idempotency_key,
            "requested_by_user_id": requested_by_user_id,
            "requested_at": agora.isoformat(),
            "expires_at": expira.isoformat(),
        }

        try:
            res = self.db.table("approval_requests").insert(registro).execute()
            linha = (res.data or [{}])[0]
        except Exception as exc:  # noqa: BLE001
            # Idempotência: mesma ação não abre duas solicitações.
            if idempotency_key and ("duplicate" in str(exc).lower() or "unique" in str(exc).lower()):
                existente = self.buscar_por_idempotencia(company_id, idempotency_key)
                if existente:
                    return existente
            raise

        self._evento(company_id, work_run_id, work_step_id, "approval.requested",
                     f"Aguardando sua aprovação: {preview.get('titulo') or action_type}")
        return linha

    # ------------------------------------------------------------------

    def validar_para_execucao(self, *, company_id: str, approval_id: str,
                              action_payload: dict) -> dict:
        """Porta de execução. Levanta exceção sempre que não puder executar.

        Chamada **imediatamente antes** do efeito externo — não no início do
        passo. Entre o aceite e a execução, o mundo pode ter mudado.
        """
        try:
            res = (self.db.table("approval_requests").select("*")
                   .eq("id", approval_id).eq("company_id", company_id)
                   .maybe_single().execute())
            ap = res.data if res else None
        except Exception as exc:  # noqa: BLE001
            raise ApprovalNotGranted("não foi possível verificar a aprovação") from exc

        if not ap:
            raise ApprovalNotGranted("aprovação inexistente para este tenant")

        if ap.get("status") not in ("approved", "executed") and ap.get("decision") not in (
            "approved", "approved_with_edit"
        ):
            raise ApprovalNotGranted(f"aprovação em estado '{ap.get('status')}'")

        if ap.get("status") == "executed":
            # Já executada. Repetir aqui seria efeito duplicado.
            raise ApprovalNotGranted("aprovação já foi executada")

        expira = ap.get("expires_at")
        if expira:
            try:
                if datetime.fromisoformat(str(expira).replace("Z", "+00:00")) < datetime.now(timezone.utc):
                    self._marcar(approval_id, {"status": "expired", "decision": "expired"})
                    raise ApprovalExpired("a janela de aprovação venceu")
            except ApprovalExpired:
                raise
            except Exception:  # noqa: BLE001
                pass

        esperado = ap.get("action_fingerprint")
        # Aprovação com edição: o payload aprovado é o editado.
        if ap.get("decision") == "approved_with_edit" and ap.get("decision_payload"):
            esperado = fingerprint(ap["decision_payload"])

        if esperado and esperado != fingerprint(action_payload):
            self._evento(company_id, ap.get("work_run_id"), ap.get("work_step_id"),
                         "approval.rejected",
                         "Execução bloqueada: o conteúdo mudou depois da aprovação.",
                         severity="warning")
            raise ApprovalFingerprintMismatch(
                "o conteúdo mudou depois da aprovação — é necessário aprovar novamente"
            )

        return ap

    def marcar_executada(self, approval_id: str) -> None:
        self._marcar(approval_id, {
            "status": "executed",
            "executed_at": datetime.now(timezone.utc).isoformat(),
        })

    # ------------------------------------------------------------------

    def decidir(self, *, company_id: str, approval_id: str, decisao: str,
                usuario_id: str, payload_editado: Optional[dict] = None,
                motivo: Optional[str] = None) -> dict:
        """Registra a decisão humana. Só quem pertence ao tenant decide."""
        if decisao not in ("approved", "rejected", "approved_with_edit"):
            raise ValueError(f"decisão inválida: {decisao}")

        agora = datetime.now(timezone.utc).isoformat()
        campos = {
            "decision": decisao,
            "status": "approved" if decisao.startswith("approved") else "rejected",
            "resolved_at": agora,
            "resolved_by_user_id": usuario_id,
            "approved_by_user_id": usuario_id if decisao.startswith("approved") else None,
            "approved_at": agora if decisao.startswith("approved") else None,
            "rejected_at": agora if decisao == "rejected" else None,
            "decision_payload": payload_editado or {},
        }
        if motivo:
            campos["approval_result"] = {"motivo": motivo}

        # eq(company_id) é a defesa contra IDOR: aprovar recurso de outro tenant.
        res = (self.db.table("approval_requests").update(campos)
               .eq("id", approval_id).eq("company_id", company_id).execute())
        if not res.data:
            raise ApprovalNotGranted("aprovação não encontrada para este tenant")

        linha = res.data[0]
        self._evento(company_id, linha.get("work_run_id"), linha.get("work_step_id"),
                     "approval.edited" if decisao == "approved_with_edit"
                     else ("approval.approved" if decisao == "approved" else "approval.rejected"),
                     {"approved": "Aprovado pelo usuário",
                      "approved_with_edit": "Aprovado com edição pelo usuário",
                      "rejected": "Recusado pelo usuário"}[decisao],
                     actor_type="user", actor_id=usuario_id)
        return linha

    def pendentes(self, company_id: str, limite: int = 50) -> list[dict]:
        try:
            res = (self.db.table("approval_requests")
                   .select("id, work_run_id, action_type, risk_level, preview, requested_at, expires_at")
                   .eq("company_id", company_id).eq("status", "pending")
                   .order("requested_at").limit(limite).execute())
            return res.data or []
        except Exception as exc:  # noqa: BLE001
            logger.error("[Approvals] falha ao listar pendentes: %s", type(exc).__name__)
            return []

    def expirar_vencidas(self, limite: int = 200) -> int:
        agora = datetime.now(timezone.utc).isoformat()
        try:
            res = (self.db.table("approval_requests")
                   .update({"status": "expired", "decision": "expired", "resolved_at": agora})
                   .eq("status", "pending").lt("expires_at", agora).execute())
            n = len(res.data or [])
            if n:
                logger.info("[Approvals] %d aprovação(ões) expirada(s)", n)
            return n
        except Exception as exc:  # noqa: BLE001
            logger.error("[Approvals] falha ao expirar: %s", type(exc).__name__)
            return 0

    # ------------------------------------------------------------------

    def buscar_por_idempotencia(self, company_id: str, chave: str) -> Optional[dict]:
        try:
            res = (self.db.table("approval_requests").select("*")
                   .eq("company_id", company_id).eq("idempotency_key", chave)
                   .maybe_single().execute())
            return res.data if res else None
        except Exception:  # noqa: BLE001
            return None

    def _marcar(self, approval_id: str, campos: dict) -> None:
        try:
            self.db.table("approval_requests").update(campos).eq("id", approval_id).execute()
        except Exception as exc:  # noqa: BLE001
            logger.error("[Approvals] falha ao marcar %s: %s", approval_id, type(exc).__name__)

    def _evento(self, company_id: Optional[str], run_id: Optional[str], step_id: Optional[str],
                tipo: str, mensagem: str, *, actor_type: str = "system",
                actor_id: Optional[str] = None, severity: str = "info") -> None:
        if not company_id or not run_id:
            return
        try:
            self.db.table("work_events").insert({
                "company_id": company_id, "work_run_id": run_id, "work_step_id": step_id,
                "event_type": tipo, "actor_type": actor_type, "actor_id": actor_id,
                "severity": severity, "message_human": mensagem,
            }).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Approvals] evento não registrado: %s", type(exc).__name__)
