"""Porta PolicyDataProvider (SPEC-016 E5) — contrato multi-provider de leitura de apólice.

A InfoCap é o provider piloto, NUNCA a arquitetura. Quiver/Segfy futuros entram
por esta mesma porta sem tocar a inteligência (facts, política, compositor,
guards, cache documental — tudo fala com o contrato, não com o provider).

Regras:
- PolicyLocator técnico genérico: "<provider>:<parte>:<parte>[...]"
  (InfoCap: "infocap:<codfil>:<nosnum>"). Número humano simples NUNCA é locator.
- O provider concreto reutiliza a cadeia canônica existente (P0/P0.1 intactos);
  esta porta não cria caminho paralelo — apenas define a fronteira.
- Nenhum código fora da implementação concreta pode assumir "infocap".
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Protocol, Tuple

_PROVIDER_KEY_RE = re.compile(r"^[a-z][a-z0-9_-]*$")


def parse_policy_locator_ref(value: Any) -> Optional[Tuple[str, Tuple[str, ...]]]:
    """Parse genérico de locator técnico. Retorna (provider, partes) ou None.

    Número humano simples, vazio ou locator incompleto → None (o chamador deve
    tratar como policy_number humano, que resolve pelo caminho canônico).
    """
    text = str(value or "").strip()
    if not text or ":" not in text:
        return None
    parts = [p.strip() for p in text.split(":")]
    if len(parts) < 3 or any(not p for p in parts):
        return None
    provider = parts[0].lower()
    if not _PROVIDER_KEY_RE.match(provider):
        return None
    return provider, tuple(parts[1:])


class PolicyDataProvider(Protocol):
    """Contrato de leitura de apólice por provider de gestão."""

    provider_key: str

    async def lookup(self, **kwargs: Any) -> Dict[str, Any]:
        """Busca cliente/apólice (document | name | policy_number)."""
        ...

    async def detail(self, **kwargs: Any) -> Dict[str, Any]:
        """Detalha apólice por locator técnico completo do provider."""
        ...


class InfocapPolicyDataProvider:
    """Implementação InfoCap: delega à cadeia canônica existente (P0/P0.1)."""

    provider_key = "infocap"

    async def lookup(
        self,
        *,
        company_id: str,
        document: Optional[str] = None,
        name: Optional[str] = None,
        policy_number: Optional[str] = None,
        user_query: Optional[str] = None,
        document_evidence_requested: bool = False,
        force_document_evidence_refresh: bool = False,
        unmasked: bool = True,
        db: Any = None,
        internal_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        from app.api.infocap_connector import InfocapLookupPayload, infocap_lookup

        payload = InfocapLookupPayload(
            company_id=company_id,
            document=document or None,
            name=name or None,
            policy_number=policy_number or None,
            user_query=user_query,
            document_evidence_requested=bool(document_evidence_requested),
            force_document_evidence_refresh=bool(force_document_evidence_refresh),
            unmasked=bool(unmasked),
        )
        return await infocap_lookup(payload=payload, x_autobrokers_internal_key=internal_key, db=db)

    async def detail(
        self,
        *,
        company_id: str,
        policy_ref: str,
        user_query: Optional[str] = None,
        document_evidence_requested: bool = False,
        force_document_evidence_refresh: bool = False,
        unmasked: bool = True,
        db: Any = None,
        internal_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        from app.api.infocap_connector import InfocapPolicyDetailPayload, infocap_policy_detail

        payload = InfocapPolicyDetailPayload(
            company_id=company_id,
            policy_ref=str(policy_ref),
            user_query=user_query,
            document_evidence_requested=bool(document_evidence_requested),
            force_document_evidence_refresh=bool(force_document_evidence_refresh),
            unmasked=bool(unmasked),
        )
        return await infocap_policy_detail(payload=payload, x_autobrokers_internal_key=internal_key, db=db)

    async def vehicle(
        self,
        *,
        company_id: str,
        document: str,
        policy_number: Optional[str] = None,
        db: Any = None,
        internal_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """SPEC-025: item do veiculo da apolice AUTO (placa/chassi/veiculo/fipe) +
        cadastro do cliente (endereco/telefone) — fonte para a portal_action montar
        o job com dados REAIS (o LLM nunca fornece placa/endereco)."""
        from app.api.infocap_connector import InfocapVehiclePayload, infocap_vehicle_item

        payload = InfocapVehiclePayload(
            company_id=company_id,
            document=document,
            policy_number=policy_number or None,
        )
        return await infocap_vehicle_item(payload=payload, x_autobrokers_internal_key=internal_key, db=db)


_REGISTRY: Dict[str, Any] = {}


def register_policy_data_provider(provider: Any) -> None:
    key = str(getattr(provider, "provider_key", "") or "").strip().lower()
    if not key:
        raise ValueError("PolicyDataProvider requires provider_key")
    _REGISTRY[key] = provider


def get_policy_data_provider(provider_key: str = "infocap") -> Optional[Any]:
    return _REGISTRY.get(str(provider_key or "").strip().lower())


# Provider piloto registrado por padrão.
register_policy_data_provider(InfocapPolicyDataProvider())
