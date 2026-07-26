"""Trilha administrativa. SPEC-061 §9.3.

O que ela responde
------------------
Seis meses depois: **quem fez o quê, em qual corretora, e por quê.**

O "por quê" é a parte que costuma faltar. O `action_key` já diz o que foi
feito; o que ninguém consegue reconstruir depois é o motivo — e é exatamente o
motivo que se precisa quando uma corretora pergunta por que foi suspensa.

Por isso o banco tem `admin_audit_events_critico_exige_motivo_ck`: ação
crítica sem motivo escrito **não entra**.

Redação, não anonimização
-------------------------
Os campos terminam em `_redacted` porque o que se guarda é o suficiente para
auditar, nunca o suficiente para vazar. Um `before`/`after` de configuração de
conexão carregaria segredo; um `reason` copiado de um chamado carregaria dado
de cliente. Os dois passam por filtro antes de virar linha.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Chaves cujo VALOR nunca é gravado, em qualquer profundidade do jsonb.
_CHAVES_SENSIVEIS = re.compile(
    r"(?i)(senha|password|secret|token|api[_-]?key|chave|authorization|"
    r"credential|private|bearer|cookie|session|cpf|cnpj)")

# Padrões que aparecem dentro de TEXTO livre — motivo escrito por humano,
# mensagem de erro colada de um log.
_SEGREDO_EM_TEXTO = re.compile(
    r"(?i)\b(api[_-]?key|token|secret|password|bearer)\b\s*[=:]\s*\S+|"
    r"tvly-\S+|AIza\S+|fc-\S+|sk-\S+|eyJ[A-Za-z0-9_-]{20,}")

LIMITE_DE_TEXTO = 2_000
LIMITE_DE_CAMPOS = 60


def redigir_texto(valor: Optional[str]) -> Optional[str]:
    if valor is None:
        return None
    return _SEGREDO_EM_TEXTO.sub("[redigido]", str(valor))[:LIMITE_DE_TEXTO]


def redigir_objeto(valor: Any, _nivel: int = 0) -> Any:
    """Percorre o objeto trocando valor sensível por marcador.

    Profundidade limitada de propósito: um payload aninhado sem fim viraria
    uma linha de auditoria gigante, e auditoria que ninguém consegue ler é
    auditoria que ninguém lê.
    """
    if _nivel > 4:
        return "[profundo demais]"
    if isinstance(valor, dict):
        saida = {}
        for i, (k, v) in enumerate(valor.items()):
            if i >= LIMITE_DE_CAMPOS:
                saida["..."] = f"+{len(valor) - LIMITE_DE_CAMPOS} campos"
                break
            saida[k] = ("[redigido]" if _CHAVES_SENSIVEIS.search(str(k))
                        else redigir_objeto(v, _nivel + 1))
        return saida
    if isinstance(valor, (list, tuple)):
        return [redigir_objeto(v, _nivel + 1) for v in valor[:20]]
    if isinstance(valor, str):
        return redigir_texto(valor)
    return valor


def diferenca(antes: Optional[dict], depois: Optional[dict]) -> dict:
    """Só os campos que MUDARAM.

    Gravar o objeto inteiro nos dois lados transforma "trocou o limite de 100
    para 200" numa parede de trinta campos idênticos, e a mudança real some no
    meio. Quem audita precisa ver a diferença, não o estado.
    """
    a, d = antes or {}, depois or {}
    mudou = {}
    for chave in sorted(set(a) | set(d)):
        va, vd = a.get(chave), d.get(chave)
        if va != vd:
            mudou[chave] = {"de": va, "para": vd}
    return mudou


class TrilhaAdministrativa:
    def __init__(self, supabase_client: Any):
        self.raw = supabase_client
        self.db = getattr(supabase_client, "client", supabase_client)

    def registrar(self, *, actor_user_id: str, action_key: str,
                  target_type: str, result_status: str,
                  permission_key: Optional[str] = None,
                  target_id: Optional[str] = None,
                  company_id: Optional[str] = None,
                  reason: Optional[str] = None,
                  antes: Optional[dict] = None,
                  depois: Optional[dict] = None,
                  metadata: Optional[dict] = None,
                  papeis: Optional[list[str]] = None,
                  support_session_id: Optional[str] = None,
                  work_run_id: Optional[str] = None,
                  correlation_id: Optional[str] = None,
                  result_code: Optional[str] = None) -> dict:
        """Grava o evento. O risco vem da permission, não de quem chama.

        Deixar o risco ser informado pelo chamador permitiria registrar uma
        suspensão de corretora como `low` — e o CHECK que exige motivo escrito
        deixaria de valer justamente na ação em que ele importa.
        """
        from .rbac import risco_de

        risco = risco_de(permission_key or "") if permission_key else "low"
        motivo = redigir_texto(reason)

        if risco == "critical" and (not motivo or len(motivo.strip()) < 10):
            # O banco recusaria de qualquer jeito. Recusar aqui devolve uma
            # frase que o operador entende, em vez de um erro de constraint.
            return {"ok": False,
                    "erro": ("ação crítica exige motivo escrito com pelo menos "
                             "10 caracteres — quem ler isto em seis meses "
                             "precisa entender por que foi feito")}

        linha: dict[str, Any] = {
            "actor_user_id": actor_user_id,
            "actor_roles": papeis or [],
            "permission_key": permission_key,
            "action_key": action_key,
            "risk_tier": risco,
            "target_type": target_type,
            "target_id": str(target_id) if target_id else None,
            "company_id": company_id,
            "support_session_id": support_session_id,
            "work_run_id": work_run_id,
            "correlation_id": correlation_id,
            "reason_redacted": motivo,
            "result_status": result_status,
            "result_code": result_code,
            "metadata_redacted": redigir_objeto(metadata or {}),
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }
        if antes is not None or depois is not None:
            mudou = diferenca(antes, depois)
            linha["before_redacted"] = redigir_objeto(
                {k: v["de"] for k, v in mudou.items()})
            linha["after_redacted"] = redigir_objeto(
                {k: v["para"] for k, v in mudou.items()})

        try:
            r = self.db.table("admin_audit_events").insert(linha).execute()
            return {"ok": True, "evento": (r.data or [{}])[0]}
        except Exception as exc:  # noqa: BLE001
            # Falha ao auditar é grave e é LOGADA como grave. Mas não derruba
            # a ação: uma trilha indisponível não pode virar indisponibilidade
            # do Admin inteiro.
            logger.error("[Auditoria] evento NAO gravado (%s): %s",
                         action_key, type(exc).__name__)
            return {"ok": False, "erro": "não consegui registrar o evento"}

    def listar(self, *, limite: int = 100, company_id: Optional[str] = None,
               actor_user_id: Optional[str] = None,
               risco: Optional[str] = None) -> list[dict]:
        try:
            q = (self.db.table("admin_audit_events")
                 .select("id, occurred_at, actor_user_id, actor_roles, "
                         "action_key, permission_key, risk_tier, target_type, "
                         "target_id, company_id, reason_redacted, "
                         "result_status, result_code")
                 .order("occurred_at", desc=True).limit(limite))
            if company_id:
                q = q.eq("company_id", company_id)
            if actor_user_id:
                q = q.eq("actor_user_id", actor_user_id)
            if risco:
                q = q.eq("risk_tier", risco)
            return q.execute().data or []
        except Exception as exc:  # noqa: BLE001
            logger.error("[Auditoria] leitura falhou: %s", type(exc).__name__)
            return []
