"""Detectores iniciais de lancamento. SPEC-059 §23.

Contrato de um detector
-----------------------
Recebe o contexto (empresa, banco, agora, configuracao da regra) e devolve
`SignalDraft`. **Nao grava.** Quem grava e o `SignalService`, que aplica
validacao, redacao, evidencia obrigatoria e dedupe.

Essa separacao e o que impede o problema classico: doze detectores, doze
jeitos de escrever na tabela, e um deles esquecendo o dedupe.

Cada detector tem uma funcao de ANALISE pura ao lado da funcao que consulta o
banco. A analise e o que muda com calibragem, e calibragem sem teste e ajuste
no escuro.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from ..schemas import SignalDraft

logger = logging.getLogger(__name__)


@dataclass
class ContextoDeDeteccao:
    company_id: str
    db: Any
    agora: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    config: dict = field(default_factory=dict)
    rule_key: str = ""
    rule_version: str = "1.0.0"

    def cfg(self, chave: str, padrao: Any) -> Any:
        valor = (self.config or {}).get(chave)
        return padrao if valor is None else valor


Detector = Callable[[ContextoDeDeteccao], list[SignalDraft]]

_REGISTRO: dict[str, Detector] = {}


def registrar(rule_key: str) -> Callable[[Detector], Detector]:
    def decorador(fn: Detector) -> Detector:
        _REGISTRO[rule_key] = fn
        return fn

    return decorador


def resolver(rule_key: str) -> Optional[Detector]:
    _carregar()
    return _REGISTRO.get(rule_key)


def registrados() -> list[str]:
    _carregar()
    return sorted(_REGISTRO)


_carregado = False


def _carregar() -> None:
    """Importa os modulos de detector uma vez. Falha de um nao derruba os outros."""
    global _carregado
    if _carregado:
        return
    _carregado = True
    for modulo in ("operacao", "conexoes", "qualidade", "automacao"):
        try:
            __import__(f"{__name__}.{modulo}", fromlist=["*"])
        except Exception as exc:  # noqa: BLE001
            logger.error("[Detectores] modulo '%s' nao carregou: %s",
                         modulo, type(exc).__name__)


def horas_desde(valor: Any, agora: datetime) -> Optional[float]:
    """Horas entre um timestamp e agora. `None` quando o valor nao e legivel."""
    if not valor:
        return None
    try:
        d = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return (agora - d).total_seconds() / 3600.0
    except Exception:  # noqa: BLE001
        return None


def plural(n: int, singular: str, plural_: str) -> str:
    return f"{n} {singular if n == 1 else plural_}"
