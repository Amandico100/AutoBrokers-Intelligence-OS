"""Work Effects — reserva de efeito externo idempotente. SPEC-055 §18.

Esta é a peça que impede o AutoBrokers de cobrar duas vezes, enviar o mesmo
WhatsApp duas vezes ou submeter o mesmo formulário de portal duas vezes.

O problema real que ela resolve já existe hoje: o Portal Worker conclui a ação
no portal da seguradora e o processo morre antes de gravar o status. Na
retomada, a ação repete. Com 67 de 91 jobs em `needs_human`, esse cenário não é
hipotético.

Padrão canônico — **reservar antes, confirmar depois**:

    with reserve_effect(...) as efeito:
        referencia = provider.enviar(...)      # o efeito externo
        efeito.confirmar(referencia)

Se o processo morrer entre a reserva e a confirmação, a linha fica em
`reserved`/`executing`. A retomada **não repete** — encontra a reserva e marca
`unknown`, que exige reconciliação humana ou consulta ao provider antes de
qualquer nova tentativa.

A alternativa ingênua — gravar um log depois de executar — não protege nada:
o crash acontece justamente na janela entre executar e gravar.
"""

from __future__ import annotations

import hashlib
import json
import logging
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Optional

logger = logging.getLogger(__name__)


class EffectAlreadyExecuted(Exception):
    """A chave já foi reservada. O efeito não pode ser repetido."""

    def __init__(self, idempotency_key: str, status: str, provider_reference: Optional[str]):
        self.idempotency_key = idempotency_key
        self.status = status
        self.provider_reference = provider_reference
        super().__init__(
            f"efeito já reservado (chave={idempotency_key}, status={status})"
        )


class EffectNeedsReconciliation(Exception):
    """Reserva anterior ficou sem confirmação. Exige reconciliação."""


def fingerprint(payload: Any) -> str:
    """Impressão estável do conteúdo de uma ação.

    Usada para detectar que o conteúdo mudou depois de aprovado — sem isso,
    "aprovar" viraria cheque em branco.
    """
    normalizado = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(normalizado.encode("utf-8")).hexdigest()


def build_idempotency_key(
    company_id: str, run_id: str, step_id: Optional[str], action: str, payload: Any
) -> str:
    """Formato canônico da SPEC-053 §10.5.

    `{company_id}:{run_id}:{step_id}:{action}:{payload_hash}`

    O hash do payload entra de propósito: se o conteúdo mudar, é outra ação e
    merece outra chave. Sem ele, uma correção de texto seria silenciosamente
    tratada como reenvio da mensagem antiga.
    """
    return f"{company_id}:{run_id}:{step_id or '-'}:{action}:{fingerprint(payload)[:32]}"


@dataclass
class EffectHandle:
    """Reserva viva. Só a confirmação fecha o ciclo."""

    effect_id: str
    idempotency_key: str
    _service: "WorkEffectService"
    _confirmado: bool = False

    def confirmar(self, provider_reference: str, response_summary: Optional[dict] = None) -> None:
        self._service._confirmar(self.effect_id, provider_reference, response_summary or {})
        self._confirmado = True

    def falhar(self, erro: str, retryable: bool = True) -> None:
        self._service._falhar(self.effect_id, erro, retryable)
        self._confirmado = True  # ciclo fechado: não vira `unknown`


class WorkEffectService:
    """Ledger de efeitos externos."""

    def __init__(self, supabase_client: Any):
        self.db = getattr(supabase_client, "client", supabase_client)

    # -- consulta -----------------------------------------------------------

    def buscar(self, company_id: str, idempotency_key: str) -> Optional[dict]:
        try:
            res = (
                self.db.table("work_effects")
                .select("*")
                .eq("company_id", company_id)
                .eq("idempotency_key", idempotency_key)
                .maybe_single()
                .execute()
            )
            return res.data if res and res.data else None
        except Exception as exc:  # noqa: BLE001
            logger.error("[WorkEffects] falha ao consultar reserva: %s", type(exc).__name__)
            # Fail-closed: não saber se o efeito já ocorreu é motivo para NÃO executar.
            raise EffectNeedsReconciliation(
                "não foi possível verificar reserva anterior"
            ) from exc

    # -- ciclo de vida ------------------------------------------------------

    @contextmanager
    def reserve(
        self,
        *,
        company_id: str,
        work_run_id: str,
        effect_type: str,
        provider: str,
        idempotency_key: str,
        request_payload: Any,
        work_step_id: Optional[str] = None,
        resource_key: Optional[str] = None,
    ) -> Iterator[EffectHandle]:
        """Reserva o efeito, entrega o controle, e fecha o ciclo.

        Levanta `EffectAlreadyExecuted` se a chave já existir — o chamador
        deve tratar isso como sucesso silencioso, não como erro.
        """
        existente = self.buscar(company_id, idempotency_key)
        if existente:
            raise EffectAlreadyExecuted(
                idempotency_key, existente.get("status", "?"), existente.get("provider_reference")
            )

        req_fp = fingerprint(request_payload)
        try:
            res = (
                self.db.table("work_effects")
                .insert({
                    "company_id": company_id,
                    "work_run_id": work_run_id,
                    "work_step_id": work_step_id,
                    "effect_type": effect_type,
                    "provider": provider,
                    "resource_key": resource_key,
                    "idempotency_key": idempotency_key,
                    "request_fingerprint": req_fp,
                    "status": "reserved",
                })
                .execute()
            )
        except Exception as exc:  # noqa: BLE001
            # A UNIQUE do banco é a autoridade final. Corrida entre dois
            # workers termina aqui, e não em efeito duplicado.
            if "duplicate" in str(exc).lower() or "unique" in str(exc).lower():
                atual = self.buscar(company_id, idempotency_key) or {}
                raise EffectAlreadyExecuted(
                    idempotency_key, atual.get("status", "?"), atual.get("provider_reference")
                ) from exc
            raise

        effect_id = res.data[0]["id"]
        handle = EffectHandle(effect_id=effect_id, idempotency_key=idempotency_key, _service=self)

        self._marcar(effect_id, {"status": "executing", "started_at": "now()"})
        self._evento(company_id, work_run_id, work_step_id, "effect.reserved",
                     f"Efeito reservado: {effect_type} via {provider}")

        try:
            yield handle
        except Exception:
            if not handle._confirmado:
                # Não sabemos se o provider executou. `unknown` é honesto —
                # e proíbe repetição automática.
                self._marcar(effect_id, {"status": "unknown", "unknown_at": "now()"})
                self._evento(company_id, work_run_id, work_step_id, "effect.unknown",
                             f"Efeito {effect_type} sem confirmação — exige reconciliação")
            raise
        else:
            if not handle._confirmado:
                self._marcar(effect_id, {"status": "unknown", "unknown_at": "now()"})
                self._evento(company_id, work_run_id, work_step_id, "effect.unknown",
                             f"Efeito {effect_type} terminou sem confirmar")

    # -- internos -----------------------------------------------------------

    def _marcar(self, effect_id: str, campos: dict) -> None:
        payload = {k: (None if v == "now()" else v) for k, v in campos.items()}
        for k, v in campos.items():
            if v == "now()":
                from datetime import datetime, timezone

                payload[k] = datetime.now(timezone.utc).isoformat()
        try:
            self.db.table("work_effects").update(payload).eq("id", effect_id).execute()
        except Exception as exc:  # noqa: BLE001
            logger.error("[WorkEffects] falha ao marcar efeito %s: %s", effect_id, type(exc).__name__)

    def _confirmar(self, effect_id: str, provider_reference: str, response_summary: dict) -> None:
        from datetime import datetime, timezone

        self.db.table("work_effects").update({
            "status": "confirmed",
            "provider_reference": provider_reference,
            "response_fingerprint": fingerprint(response_summary),
            "response_summary": response_summary,
            "confirmed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", effect_id).execute()

    def _falhar(self, effect_id: str, erro: str, retryable: bool) -> None:
        from datetime import datetime, timezone

        self.db.table("work_effects").update({
            "status": "failed_retryable" if retryable else "failed_terminal",
            "response_summary": {"erro": erro[:500]},
            "failed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", effect_id).execute()

    def _evento(self, company_id: str, run_id: str, step_id: Optional[str],
                tipo: str, mensagem: str) -> None:
        try:
            self.db.table("work_events").insert({
                "company_id": company_id,
                "work_run_id": run_id,
                "work_step_id": step_id,
                "event_type": tipo,
                "actor_type": "worker",
                "message_human": mensagem,
            }).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[WorkEffects] evento não registrado: %s", type(exc).__name__)

    # -- reconciliação ------------------------------------------------------

    def pendentes_de_reconciliacao(self, minutos: int = 15) -> list[dict]:
        """Efeitos presos em reserva/execução/desconhecido além do limite."""
        from datetime import datetime, timedelta, timezone

        corte = (datetime.now(timezone.utc) - timedelta(minutes=minutos)).isoformat()
        try:
            res = (
                self.db.table("work_effects")
                .select("*")
                .in_("status", ["reserved", "executing", "unknown"])
                .lt("reserved_at", corte)
                .limit(200)
                .execute()
            )
            return res.data or []
        except Exception as exc:  # noqa: BLE001
            logger.error("[WorkEffects] falha ao listar pendências: %s", type(exc).__name__)
            return []
