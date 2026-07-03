"""Prompt Efetivo (Onda 3 / SPEC-018 S1) — diagnóstico READ-ONLY de autoridade.

Responde, para um agente de uma corretora, a pergunta que o Portal Admin nunca
soube responder: "o que o runtime REALMENTE monta para este agente?"

- camadas de prompt (política da plataforma por papel, instruções do cliente);
- tools que o grafo anexaria e POR QUÊ (capability ativa, tools_config, sempre);
- divergências: switch ligado que o runtime não lê, capability sem conexão etc.

Módulo PURO: recebe as linhas do banco já carregadas (endpoint faz o I/O).
Nunca expõe segredo; instruções do cliente são REDIGIDAS (só tamanho/hash).
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional


def _redact(text: Optional[str]) -> Dict[str, Any]:
    raw = str(text or "")
    return {
        "present": bool(raw.strip()),
        "chars": len(raw),
        "sha256_12": hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12] if raw else None,
    }


def build_prompt_effective(
    *,
    agent: Dict[str, Any],
    company_config: Dict[str, Any],
    resolved_capabilities: Dict[str, Dict[str, str]],
    http_tools: List[Dict[str, Any]],
    mcp_tools: List[Dict[str, Any]],
    delegations_count: int = 0,
) -> Dict[str, Any]:
    """Monta o diagnóstico do Prompt Efetivo (espelha a lógica do graph.py)."""
    agent = agent or {}
    role = str(agent.get("agent_role") or "").strip().lower() or "core(legado)"
    tools_config = agent.get("tools_config") or {}
    active = {k for k, v in (resolved_capabilities or {}).items() if v.get("status") == "active"}

    bound_tools: List[Dict[str, Any]] = [
        {"tool": "knowledge_base_search", "authority": "sempre (base do agente)", "active": True}
    ]
    bound_tools.append({
        "tool": "web_search",
        "authority": "capability platform.web.search",
        "active": "platform.web.search" in active,
    })
    bound_tools.append({
        "tool": "request_human_agent",
        "authority": "tools_config.human_handoff (LEGADO — fora do Registry)",
        "active": bool((tools_config.get("human_handoff") or {}).get("enabled")),
        "divergence": "autorização concorrente ao Registry" if (tools_config.get("human_handoff") or {}).get("enabled") else None,
    })
    bound_tools.append({
        "tool": "csv_analytics",
        "authority": "tools_config.csv_analytics (LEGADO — fora do Registry)",
        "active": bool((tools_config.get("csv_analytics") or {}).get("enabled")),
        "divergence": "autorização concorrente ao Registry" if (tools_config.get("csv_analytics") or {}).get("enabled") else None,
    })
    active_http = [t for t in (http_tools or []) if t.get("is_active", True)]
    bound_tools.append({
        "tool": "http_api",
        "authority": "agent_http_tools + menção no prompt (SEM capability — S2 endurece)",
        "active": bool(active_http),
        "count": len(active_http),
        "divergence": "anexada sem capability" if active_http else None,
    })
    bound_tools.append({
        "tool": "mcp_tools",
        "authority": "tabelas MCP do agente (modo estrito exige capability tenant.mcp.<server>)",
        "active": bool(mcp_tools),
        "count": len(mcp_tools or []),
        "divergence": "anexada sem capability" if mcp_tools else None,
    })
    bound_tools.append({
        "tool": "infocap_policy_lookup",
        "authority": "capability operational.infocap.policy_lookup.read + conexão",
        "active": "operational.infocap.policy_lookup.read" in active,
        "role_exposure": "completo" if role in ("core", "core(legado)") else "mascarado",
    })
    bound_tools.append({
        "tool": "insurer_dispatch",
        "authority": "papel attendance (capability formal na S2)",
        "active": role == "attendance",
    })
    bound_tools.append({
        "tool": "delegate_to_subagent",
        "authority": "agent_delegations",
        "active": delegations_count > 0,
        "count": delegations_count,
    })

    divergences: List[str] = [str(t["divergence"]) for t in bound_tools if t.get("divergence")]
    if agent.get("allow_web_search") and "platform.web.search" not in active:
        divergences.append("agents.allow_web_search=true mas capability web inativa (flag legada diverge)")
    for key, info in (resolved_capabilities or {}).items():
        if info.get("status") == "needs_connection":
            divergences.append(f"capability {key} ligada mas SEM conexão da corretora")

    rag_scope = "privado + global curado" if role in ("core", "core(legado)", "attendance") else "somente privado"

    return {
        "agent_id": str(agent.get("id") or ""),
        "agent_role": role,
        "prompt_layers": [
            {"layer": "1. Política da plataforma (imutável)", "source": "CORE_BASE_PROMPT" if role != "attendance" else "ATTENDANCE_BASE_PROMPT"},
            {"layer": "2. Instruções do cliente/agente", "source": "agents.agent_system_prompt", **_redact(agent.get("agent_system_prompt") or company_config.get("agent_instructions"))},
            {"layer": "3. Contexto dinâmico", "source": "memória + RAG prefetch + contexto de auxiliares"},
        ],
        "rag_scope": rag_scope,
        "capabilities": resolved_capabilities or {},
        "bound_tools": bound_tools,
        "divergences": divergences,
        "read_only": True,
    }
