"""Work OS — execução durável. SPEC-055.

Autoridades, para não haver dúvida em nenhum ponto do código:

    Postgres   estado durável do trabalho (a verdade)
    Redis      transporte da fila (nunca a verdade)
    LangGraph  estado cognitivo e checkpoints
    MinIO      bytes de artifacts

Nada aqui cria um segundo runtime: o Smith Worker executa o mesmo Smith.
"""

from .approvals import (  # noqa: F401
    ApprovalExpired,
    ApprovalFingerprintMismatch,
    ApprovalNotGranted,
    WorkApprovalService,
)
from .effects import (  # noqa: F401
    EffectAlreadyExecuted,
    EffectNeedsReconciliation,
    WorkEffectService,
    build_idempotency_key,
    fingerprint,
)
from .queue import OutboxDispatcher, WorkQueue  # noqa: F401
from .runs import WorkRunService, worker_id  # noqa: F401
from .usage import UsageService  # noqa: F401
from .workflows import (  # noqa: F401
    executar_passo,
    registrar_workflow,
    resolver_workflow,
    workflows_registrados,
)

__all__ = [
    "WorkRunService", "WorkQueue", "OutboxDispatcher", "WorkEffectService",
    "WorkApprovalService", "UsageService", "worker_id",
    "build_idempotency_key", "fingerprint", "executar_passo",
    "registrar_workflow", "resolver_workflow", "workflows_registrados",
    "EffectAlreadyExecuted", "EffectNeedsReconciliation",
    "ApprovalExpired", "ApprovalFingerprintMismatch", "ApprovalNotGranted",
]
