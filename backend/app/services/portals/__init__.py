# -*- coding: utf-8 -*-
"""Execução de portal como capacidade do Work OS — SPEC-075.

Um `import` deste pacote NÃO pode puxar Supabase, Redis nem Playwright: ele é
lido por código que só quer o vocabulário (contratos, estados, políticas de
retry). Por isso aqui só entram reexportações do módulo puro `contracts`; o
`gateway`, o `resolver`, o `leases` e a `prontidao` são importados
explicitamente por quem precisa deles.
"""
from app.services.portals.contracts import (  # noqa: F401
    ESPERA_AGUARDAR, ESPERA_ENFILEIRAR, ESTADOS_DE_NEGOCIO, MODO_LEGACY,
    MODO_ON, MODO_SHADOW, MODOS_VALIDOS, NAO_REPETIR, NEGOCIO_BLOQUEADO_PELO_PORTAL,
    NEGOCIO_FALHOU, NEGOCIO_NADA_A_FAZER, NEGOCIO_NAO_AUTORIZADO,
    NEGOCIO_NAO_SUPORTADO, NEGOCIO_OK, NEGOCIO_PRECISA_HUMANO,
    NEGOCIO_SEM_CONEXAO, NEGOCIO_TALVEZ_COMMITADO, IdempotencyRecord,
    PortalExecutionRequest, PortalExecutionResult, RECONCILIAR, RETRY_AUTOMATICO,
    RETRY_PROIBIDO, RETRY_SE_NADA_CRIADO, modo_valido, pode_repetir,
    politica_de_retry, precisa_de_idempotencia, recusa,
)

__all__ = [n for n in dir() if not n.startswith("_")]
