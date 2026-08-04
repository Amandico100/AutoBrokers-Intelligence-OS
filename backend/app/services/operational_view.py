"""SPEC-040 Onda 2 — Visão Operacional do Chat Principal (Missão B).

Consultas DETERMINÍSTICAS e token-eficientes para o Core enxergar a operação:
- operations_summary: acionamentos ativos + desfechos do período + qualidade,
  SEMPRE escopado pela corretora (company_id vem do runtime, nunca da LLM).
- atlas_routes_summary: os mapas de rota do Atlas (estrutura GLOBAL das URAs
  das seguradoras — sem nenhum dado de cliente).

Regra de custo (SPEC-040 §5): o serviço monta o digest pronto e ENXUTO; a LLM
só formata/apresenta. Nunca devolver listas cruas nem paginação para o modelo.
Fail-soft: cada seção falha sozinha sem derrubar o resto.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_STATE_PT = {
    "ura": "navegando a URA da seguradora",
    "human_phase": "com o analista da seguradora",
    "captured": "protocolo garantido",
    "monitoring": "monitorando a chegada do prestador",
    "needs_human": "com a equipe humana (dossiê entregue)",
    "encaminhado": "resolvido por encaminhamento (formulário/orientação entregue)",
    "resolvido": "resolvido — serviço prestado e ciclo fechado",
    "test_aborted": "simulação concluída (modo teste)",
    "insurer_closed": "encerrado pela seguradora",
    "queued": "na fila (aguardando vez)",
}

_MAX_LIST = 8          # itens por seção (digest enxuto — a LLM nunca pagina)
_TEXT_CAP = 90         # corte de texto de tela do Atlas


def _insurer_label_by_phone(phone: str) -> str:
    try:
        from app.services.atlas.observer_intake import _digits, insurer_allowlist
        from app.services.insurer_registry import INSURER_REGISTRY

        key = insurer_allowlist().get(_digits(phone))
        if key:
            return str((INSURER_REGISTRY.get(key) or {}).get("label") or key.title())
    except Exception:  # noqa: BLE001
        pass
    return "Seguradora"


def _fmt_when(iso: Any) -> str:
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).strftime("%d/%m %H:%M")
    except Exception:  # noqa: BLE001
        return ""


async def operations_summary(company_id: str, periodo: str = "hoje") -> str:
    """Digest da operação da corretora. periodo: 'hoje' (24h) ou 'semana' (7d)."""
    days = 7 if str(periodo or "").strip().lower() in ("semana", "7d", "7") else 1
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    lines: List[str] = [f"OPERAÇÃO DE ATENDIMENTO — período: {'últimos 7 dias' if days == 7 else 'últimas 24h'}"]

    # 1) Acionamentos ATIVOS agora (Redis — tempo real)
    try:
        from app.services.dispatch_router import list_active_dispatches

        active = await list_active_dispatches(company_id)
        if active:
            lines.append(f"\nACIONAMENTOS ATIVOS AGORA ({len(active)}):")
            for s in active[:_MAX_LIST]:
                label = _insurer_label_by_phone(str(s.get("insurer_phone") or ""))
                state = _STATE_PT.get(str(s.get("state") or ""), str(s.get("state") or "?"))
                cap = s.get("captured") or {}
                extra = ""
                if cap.get("protocol"):
                    extra = f" — protocolo {cap['protocol']}"
                elif cap.get("eta_minutes"):
                    extra = f" — previsão ~{cap['eta_minutes']} min"
                sub = f" ({s.get('subservice')})" if s.get("subservice") else ""
                lines.append(f"- {label}{sub}: {state}{extra}")
        else:
            lines.append("\nACIONAMENTOS ATIVOS AGORA: nenhum em andamento.")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[VISAO OPERACIONAL] ativos falhou: {type(e).__name__}")
        lines.append("\nACIONAMENTOS ATIVOS: indisponível no momento.")

    # 2) Movimento do período (Atividades — transições reais registradas)
    try:
        from app.core.database import get_supabase_client

        db = get_supabase_client()

        def _acts() -> list:
            return (db.client.table("agent_activities")
                    .select("category, title, created_at")
                    .eq("company_id", company_id)
                    .gte("created_at", since)
                    .order("created_at", desc=True).limit(200).execute().data or [])

        acts = await asyncio.to_thread(_acts)
        disp = [a for a in acts if a.get("category") == "acionamentos"]
        if disp:
            started = sum(1 for a in disp if "iniciado" in str(a.get("title", "")).lower())
            protocol = sum(1 for a in disp if "protocolo" in str(a.get("title", "")).lower())
            handoff = sum(1 for a in disp if "dossiê" in str(a.get("title", "")).lower()
                          or "dossie" in str(a.get("title", "")).lower())
            lines.append(f"\nMOVIMENTO DO PERÍODO: {started} acionamentos iniciados, "
                         f"{protocol} com protocolo garantido, {handoff} entregues à equipe humana.")
            lines.append("ÚLTIMOS EVENTOS:")
            for a in disp[:_MAX_LIST]:
                lines.append(f"- {_fmt_when(a.get('created_at'))} {a.get('title')}")
        else:
            lines.append("\nMOVIMENTO DO PERÍODO: nenhum acionamento registrado.")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[VISAO OPERACIONAL] atividades falhou: {type(e).__name__}")

    # 3) Qualidade (scorecards do Auditor)
    try:
        from app.core.database import get_supabase_client

        db = get_supabase_client()

        def _scores() -> list:
            return (db.client.table("conversation_scorecards")
                    .select("score, created_at").eq("company_id", company_id)
                    .gte("created_at", since).limit(200).execute().data or [])

        scores = await asyncio.to_thread(_scores)
        if scores:
            vals = [int(s.get("score") or 0) for s in scores]
            lines.append(f"\nQUALIDADE: {len(vals)} conversas auditadas, nota média "
                         f"{sum(vals) / len(vals):.0f}/100 no período.")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[VISAO OPERACIONAL] scorecards falhou: {type(e).__name__}")

    lines.append("\n(Fonte: dados reais do sistema. Apresente com clareza; não invente números.)")
    return "\n".join(lines)


# ------------------------------------------------------------------ #
# Atlas — mapas de rota (estrutura global, sem dado de cliente)
# ------------------------------------------------------------------ #
def _latest_maps_sync(insurer_key: Optional[str] = None) -> List[Dict[str, Any]]:
    from app.core.database import get_supabase_client

    db = get_supabase_client()
    q = (db.client.table("ura_maps")
         .select("insurer_key, ramo, status, map, diff_summary, created_at")
         .in_("status", ["active", "observed"])
         .order("created_at", desc=True).limit(60))
    if insurer_key:
        q = q.eq("insurer_key", insurer_key)
    rows = q.execute().data or []
    # 1 mapa por (insurer, ramo): active > observed; mais novo primeiro
    best: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        k = f"{r.get('insurer_key')}::{r.get('ramo')}"
        cur = best.get(k)
        if cur is None or (cur.get("status") != "active" and r.get("status") == "active"):
            best[k] = r
    return list(best.values())


def _trunc(text: Any, cap: int = _TEXT_CAP) -> str:
    t = " ".join(str(text or "").split())
    return t[: cap - 1] + "…" if len(t) > cap else t


def _route_to_service(map_data: Dict[str, Any], servico: str) -> List[str]:
    """BFS determinístico da raiz até a 1ª tela/aresta que casa o serviço."""
    nodes = map_data.get("nodes") or {}
    edges = (map_data.get("edges") or {}).values()
    root = map_data.get("root")
    if not root or root not in nodes:
        return []
    term = servico.strip().lower()
    adj: Dict[str, List[tuple]] = {}
    for e in edges:
        adj.setdefault(str(e.get("src")), []).append((str(e.get("label") or ""), str(e.get("to"))))
    from collections import deque

    seen = {root}
    queue = deque([(root, [])])
    while queue:
        nid, path = queue.popleft()
        for label, to in adj.get(nid, []):
            if to in seen:
                continue
            new_path = path + [(nid, label, to)]
            hit = term in label.lower() or term in str((nodes.get(to) or {}).get("text") or "").lower()
            if hit:
                out = []
                for src, lbl, dst in new_path:
                    out.append(f"[{_trunc((nodes.get(src) or {}).get('text'), 60)}] → responder \"{lbl or '(segue)'}\"")
                out.append(f"[{_trunc((nodes.get(new_path[-1][2]) or {}).get('text'), 60)}]")
                return out
            seen.add(to)
            queue.append((to, new_path))
    return []


async def atlas_routes_summary(insurer_key: Optional[str] = None, ramo: Optional[str] = None,
                               servico: Optional[str] = None) -> str:
    """Resumo dos mapas do Atlas. Sem seguradora: lista geral. Com seguradora:
    detalha (e com 'servico': mostra o caminho até o serviço)."""
    key = str(insurer_key or "").strip().lower() or None
    try:
        maps = await asyncio.to_thread(_latest_maps_sync, key)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[VISAO OPERACIONAL] atlas falhou: {type(e).__name__}")
        return "Os mapas do Atlas estão indisponíveis no momento."

    if ramo:
        maps = [m for m in maps if str(m.get("ramo") or "").lower() == str(ramo).lower()]
    if not maps:
        alvo = f" para {key or 'as seguradoras'}" + (f" ({ramo})" if ramo else "")
        return f"Ainda não há mapa de rotas observado{alvo}. O Observador constrói os mapas conforme os atendimentos acontecem."

    from app.services.insurer_registry import INSURER_REGISTRY

    if not key:
        lines = ["MAPAS DE ROTA DAS SEGURADORAS (Atlas):"]
        for m in sorted(maps, key=lambda x: str(x.get("insurer_key"))):
            label = str((INSURER_REGISTRY.get(str(m.get("insurer_key"))) or {}).get("label")
                        or str(m.get("insurer_key")).title())
            cov = ((m.get("map") or {}).get("coverage") or {})
            lines.append(f"- {label} ({m.get('ramo')}): {cov.get('nodes', '?')} telas, "
                         f"cobertura {cov.get('pct', '?')}% [{m.get('status')}]")
        lines.append("\nPara o caminho de um serviço: informe seguradora + serviço (ex.: porto + guincho).")
        return "\n".join(lines)

    m = maps[0]
    map_data = m.get("map") or {}
    cov = map_data.get("coverage") or {}
    label = str((INSURER_REGISTRY.get(key) or {}).get("label") or key.title())
    lines = [f"MAPA DA {label.upper()} ({m.get('ramo')}) — {cov.get('nodes', '?')} telas, "
             f"cobertura {cov.get('pct', '?')}% [{m.get('status')}]"]

    nodes = map_data.get("nodes") or {}
    root = map_data.get("root")
    if root and root in nodes:
        rn = nodes[root]
        lines.append(f"\nENTRADA: {_trunc(rn.get('text'))}")
        opts = [str(o.get("label") or "") for o in (rn.get("options") or []) if o.get("label")]
        if opts:
            lines.append("OPÇÕES INICIAIS: " + " · ".join(opts[:10]))

    if servico:
        path = _route_to_service(map_data, str(servico))
        if path:
            lines.append(f"\nCAMINHO ATÉ '{servico.upper()}':")
            lines.extend(f"  {i + 1}. {step}" for i, step in enumerate(path[:12]))
        else:
            lines.append(f"\nAinda não observamos o caminho de '{servico}' nesse mapa.")

    if m.get("diff_summary"):
        lines.append(f"\nRESUMO: {m['diff_summary']}")
    lines.append("(Estrutura global das URAs — sem nenhum dado de cliente.)")
    return "\n".join(lines)
