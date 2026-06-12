"""
Core Auxiliary Awareness (42A7).

Carrega de forma SEGURA e COMPACTA os Auxiliares instalados da corretora e
monta um bloco curto para o Context Assembly do AutoBrokers Core — para que o
Core saiba responder "quais auxiliares eu tenho", "esse exige aprovação?",
"qual usar para follow-up?", etc.

Garantias:
- Só injeta para o Core (agent_role='core'); nunca para outros papéis.
- Nunca quebra o chat (chamador usa try/except; aqui degradamos para [] / "").
- Bloco compacto (até 8 itens, campos curtos) → evita context bloat.
- Lê apenas campos seguros do contrato (42A5); NUNCA config/default_config
  inteiro, system_prompt, permissions, token, segredo, dado de cliente.
- Compatível semanticamente com lib/auxiliaries/contract.ts (sem importar TS).
"""

import logging
import unicodedata
from typing import Any, Dict, List

from .context_package import get_agent_field

logger = logging.getLogger(__name__)

_MAX_AUX = 8
_MAX_GOAL = 90
_MAX_WHEN = 90

# Palavras que indicam intenção sobre auxiliares/automação/capacidades.
_AUX_KEYWORDS = (
    "auxiliar", "auxiliares", "automacao", "automacoes", "rotina", "rotinas",
    "follow-up", "followup", "follow up", "resumo", "atendimento", "aprovar",
    "aprovacao", "whatsapp", "mensagem", "relatorio", "cobranca", "executar",
    "instalar", "disponivel", "disponiveis", "capacidade", "capacidades",
)
# Perguntas amplas sobre o que o sistema consegue fazer.
_AUX_BROAD_PHRASES = (
    "o que voce consegue fazer", "o que posso automatizar", "quais recursos",
    "como voce pode me ajudar", "o que voce faz", "suas capacidades",
    "o que da pra automatizar", "o que da para automatizar",
)

_TITLES = {
    "resumo-atendimentos": "Resumo de Atendimentos",
    "follow-up-whatsapp": "Follow-up WhatsApp",
}


def _norm(text: Any) -> str:
    t = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def _safe_str(v: Any, default: str = "") -> str:
    return v if isinstance(v, str) and v.strip() else default


def _trunc(text: str, limit: int) -> str:
    t = " ".join((text or "").split())
    return t if len(t) <= limit else t[:limit].rstrip() + "…"


def _title_from_slug(slug: str) -> str:
    return _TITLES.get(slug, "")


def should_load_auxiliary_context(agent_data: Any, user_message: str) -> bool:
    """True só para o Core e quando a mensagem indica intenção sobre auxiliares."""
    role = (get_agent_field(agent_data, "agent_role") or "").strip().lower()
    if role != "core":
        return False
    audience = (get_agent_field(agent_data, "agent_audience") or "").strip().lower()
    if audience and audience != "broker_internal":
        return False
    msg = _norm(user_message)
    if not msg:
        return False
    if any(k in msg for k in _AUX_KEYWORDS):
        return True
    if any(p in msg for p in _AUX_BROAD_PHRASES):
        return True
    return False


def load_tenant_auxiliaries_for_context(client: Any, company_id: str, limit: int = _MAX_AUX) -> List[Dict[str, Any]]:
    """Lê tenant_auxiliaries ativos da corretora (campos seguros). [] em erro/vazio."""
    if not client or not company_id:
        return []
    try:
        resp = (
            client.table("tenant_auxiliaries")
            .select("id, slug, status, name, display_name, config")
            .eq("company_id", str(company_id))
            .limit(20)
            .execute()
        )
        rows = resp.data or []
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[AuxContext] error ignored type={type(e).__name__}")
        return []

    inactive = ("archived", "deleted", "disabled", "removed", "inactive")
    active = [r for r in rows if str(r.get("status") or "active").lower() not in inactive and r.get("slug")]
    return active[:limit]


def _summarize_tools(value: Any) -> str:
    if not isinstance(value, list):
        return ""
    out: List[str] = []
    for item in value[:3]:
        if isinstance(item, dict):
            t = _safe_str(item.get("type"))
            if t and t != "internal":
                out.append(t)
    return "/".join(dict.fromkeys(out))  # dedupe preservando ordem


def _summarize_knowledge(value: Any) -> str:
    if not isinstance(value, list):
        return ""
    out: List[str] = []
    for item in value[:3]:
        if isinstance(item, dict) and item.get("required") is True:
            scope = _safe_str(item.get("scope"))
            if scope and scope != "none":
                out.append(scope)
    return "/".join(dict.fromkeys(out))


def _infer_minimal(slug: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Inferência mínima quando não há contrato explícito (genérica, sem hardcode de empresa)."""
    runtime = config.get("runtime") if isinstance(config.get("runtime"), dict) else {}
    kind = _safe_str(runtime.get("kind"))
    if "whatsapp" in slug:
        return {
            "auxiliary_type": "approval_required", "side_effects": "approval_required",
            "risk_level": "medium", "approval_required": True, "tools": "whatsapp", "knowledge": "",
        }
    aux_type = "agent_based" if kind in ("smith_agent_blueprint", "smith_agent") else "read_only"
    return {
        "auxiliary_type": aux_type, "side_effects": "none",
        "risk_level": "low", "approval_required": False, "tools": "", "knowledge": "",
    }


def normalize_auxiliary_contract_for_context(row: Dict[str, Any]) -> Dict[str, Any]:
    """Extrai apenas os campos seguros do contrato (ou infere mínimo)."""
    row = row or {}
    slug = _safe_str(row.get("slug"))
    name = (
        _safe_str(row.get("display_name"))
        or _safe_str(row.get("name"))
        or _title_from_slug(slug)
        or slug
        or "Auxiliar"
    )
    status = _safe_str(row.get("status"), "active")
    config = row.get("config") if isinstance(row.get("config"), dict) else {}
    contract = config.get("contract") if isinstance(config.get("contract"), dict) else None

    if contract:
        approval_obj = contract.get("approval_policy") if isinstance(contract.get("approval_policy"), dict) else {}
        base = {
            "auxiliary_type": _safe_str(contract.get("auxiliary_type"), "read_only"),
            "side_effects": _safe_str(contract.get("side_effects"), "none"),
            "risk_level": _safe_str(contract.get("risk_level"), "low"),
            "approval_required": bool(approval_obj.get("required", False)),
            "tools": _summarize_tools(contract.get("requires_tools")),
            "knowledge": _summarize_knowledge(contract.get("requires_knowledge")),
        }
        when = contract.get("when_to_use") if isinstance(contract.get("when_to_use"), list) else []
        goal = _trunc(_safe_str(contract.get("goal")), _MAX_GOAL)
        when_short = _trunc("; ".join(str(w) for w in when[:2] if w), _MAX_WHEN)
    else:
        base = _infer_minimal(slug, config)
        goal = ""
        when_short = ""

    base.update({"name": name, "slug": slug, "status": status, "goal": goal, "when_to_use": when_short})
    return base


def render_auxiliary_context_block(rows: List[Dict[str, Any]], limit: int = _MAX_AUX) -> str:
    """Monta o bloco [AVAILABLE AUXILIARIES] compacto. "" se não houver itens."""
    items = [normalize_auxiliary_contract_for_context(r) for r in (rows or [])][:limit]
    items = [n for n in items if n.get("slug")]
    if not items:
        return ""

    lines = ["[AVAILABLE AUXILIARIES]"]
    for n in items:
        meta = [n["auxiliary_type"], f"risk={n['risk_level']}", f"approval={'true' if n['approval_required'] else 'false'}"]
        if n["side_effects"] and n["side_effects"] not in ("none", n["auxiliary_type"]):
            meta.insert(1, n["side_effects"])
        if n["tools"]:
            meta.append(f"tool={n['tools']}")
        if n["knowledge"]:
            meta.append(f"knowledge={n['knowledge']}")
        tail = ""
        if n["goal"]:
            tail += f" {n['goal']}"
        if n["when_to_use"]:
            tail += f" Use: {n['when_to_use']}."
        status_txt = "" if n["status"] in ("active", "") else f" [{n['status']}]"
        lines.append(f"- {n['name']} ({n['slug']}): {', '.join(meta)}.{tail}{status_txt}")

    lines += [
        "",
        "Instructions:",
        "- You may suggest these auxiliaries when relevant to the user's request.",
        "- Do not claim an auxiliary was executed unless a run/tool confirms it.",
        "- External actions require human approval (HITL).",
        "- If a required connector/tool is missing, explain what must be configured.",
    ]
    return "\n".join(lines)
