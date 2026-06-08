"""Tipos do provider de WhatsApp."""
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class SendResult:
    """Resultado estruturado de um envio (nunca contém segredo)."""

    success: bool
    provider: str
    dry_run: bool = False
    message_id: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "provider": self.provider,
            "dry_run": self.dry_run,
            "message_id": self.message_id,
            "error": self.error,
        }
