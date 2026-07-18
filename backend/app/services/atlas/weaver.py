"""SPEC-038 ATLAS — Tecelão/Weaver (Bloco B).

Lê as sessões observadas e TECE o mapa da URA: cada tela da URA vira um nó (com
as opções que ela oferece); a escolha do humano (evento 'out' entre duas telas)
vira a aresta rotulada A→B. Sem a escolha do humano (captura só da URA), cria
aresta SEQUENCIAL tentativa (confiança menor) para a árvore ainda se formar.

Merge ACUMULATIVO e versionado em ura_maps (source='observed'): cada passagem
soma evidência; aresta confirmada = vista ≥2x com a mesma escolha. Opção
oferecida mas nunca percorrida = LACUNA (amarelo na página). Qualidade sobre
pressa: dado ambíguo não é chutado — vira aresta tentativa com baixa confiança.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_CONFIRM_THRESHOLD = 2  # aresta vista ≥2x = confirmada


def _events_to_steps(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ordena a sessão e casa cada tela da URA (in) com a resposta humana (out)
    que veio logo depois. Retorna [{screen, choice}]."""
    ordered = sorted(events, key=lambda e: (e.get("wa_timestamp") or "", e.get("created_at") or ""))
    steps: List[Dict[str, Any]] = []
    pending_screen: Optional[Dict[str, Any]] = None
    for ev in ordered:
        if ev.get("direction") == "in":
            if pending_screen is not None:
                steps.append({"screen": pending_screen, "choice": None})
            pending_screen = ev
        else:  # out = escolha do humano
            if pending_screen is not None:
                steps.append({"screen": pending_screen, "choice": ev})
                pending_screen = None
            # out sem tela pendente (rajada) — ignora como âncora
    if pending_screen is not None:
        steps.append({"screen": pending_screen, "choice": None})
    return steps


def _choice_label(choice: Optional[Dict[str, Any]]) -> Optional[str]:
    if not choice:
        return None
    it = choice.get("interactive") or {}
    # clique de lista/botão traz o título; senão o texto digitado
    for k in ("title", "selected"):
        if it.get(k):
            return str(it[k])[:60]
    txt = str(choice.get("text") or "").strip()
    return txt[:60] or None


def weave_session(map_acc: Dict[str, Any], events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Tece UMA sessão sobre o mapa acumulado (mutação in-place + retorno)."""
    from app.services.atlas.templater import screen_node

    nodes: Dict[str, Any] = map_acc.setdefault("nodes", {})
    edges: Dict[str, Any] = map_acc.setdefault("edges", {})  # "src|label" -> {to, count}
    steps = _events_to_steps(events)

    prev_node_id: Optional[str] = None
    prev_choice: Optional[str] = None
    for step in steps:
        node = screen_node(step["screen"].get("text") or "")
        nid = node["hash"]
        if nid not in nodes:
            nodes[nid] = {**node, "samples": 0}
            if map_acc.get("root") is None:
                map_acc["root"] = nid
        nodes[nid]["samples"] += 1
        # funde opções novas que apareceram nesta passagem
        seen = {o["label"] for o in nodes[nid]["options"]}
        for o in node["options"]:
            if o["label"] not in seen:
                nodes[nid]["options"].append(o)

        # liga a aresta do passo anterior até este nó
        if prev_node_id is not None:
            label = prev_choice or "→"  # sem escolha capturada = sequencial
            ekey = f"{prev_node_id}|{label}"
            e = edges.setdefault(ekey, {"src": prev_node_id, "label": label, "to": nid,
                                        "count": 0, "inferred": prev_choice is None})
            # se destino divergir, mantém o mais frequente (conta por destino)
            e.setdefault("dests", {})
            e["dests"][nid] = e["dests"].get(nid, 0) + 1
            e["to"] = max(e["dests"], key=e["dests"].get)
            e["count"] += 1

        prev_node_id = nid
        prev_choice = _choice_label(step["choice"])

    return map_acc


def compute_coverage(map_acc: Dict[str, Any]) -> Dict[str, Any]:
    """Marca, por nó, quais opções JÁ foram percorridas (têm aresta confirmada) e
    quais são LACUNA. Preenche node['options'][i]['leads_to'] e status do nó."""
    edges = map_acc.get("edges") or {}
    nodes = map_acc.get("nodes") or {}
    # arestas confirmadas por (src, label)
    confirmed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for e in edges.values():
        confirmed[(e["src"], e["label"])] = e

    total_opts = covered_opts = 0
    for nid, node in nodes.items():
        node_gaps = 0
        for opt in node.get("options") or []:
            total_opts += 1
            e = confirmed.get((nid, opt["label"]))
            if e and e.get("count", 0) >= 1 and not e.get("inferred"):
                opt["leads_to"] = e["to"]
                opt["confidence"] = "confirmed" if e["count"] >= _CONFIRM_THRESHOLD else "seen_once"
                covered_opts += 1
            else:
                opt["leads_to"] = None
                opt["confidence"] = "gap"
                node_gaps += 1
        if node.get("kind") == "app_form":
            node["status"] = "app_form"
        elif node.get("kind") in ("finalize", "terminal", "informativo") and not node.get("options"):
            node["status"] = "complete"
        elif node_gaps == 0 and node.get("options"):
            node["status"] = "complete"
        elif node_gaps and covered_opts:
            node["status"] = "partial"
        else:
            node["status"] = "unknown"
    map_acc["coverage"] = {
        "options_total": total_opts,
        "options_covered": covered_opts,
        "pct": round(100 * covered_opts / total_opts) if total_opts else 0,
        "nodes": len(nodes),
    }
    return map_acc


async def weave_insurer(insurer_key: str, ramo: str = "auto", company_id: Optional[str] = None) -> Dict[str, Any]:
    """Reconstrói o mapa observado de uma seguradora×ramo a partir de TODAS as
    sessões capturadas e salva como proposta (source='observed'). Idempotente:
    reprocessa o histórico inteiro (a verdade é o acúmulo das observações)."""
    from app.core.database import get_supabase_client
    from app.services.atlas.templater import infer_ramo_servico

    supabase = get_supabase_client()

    def _load() -> Tuple[List[Dict], List[Dict]]:
        sess_q = (supabase.client.table("observed_sessions").select("id, ramo, servico")
                  .eq("insurer_key", insurer_key))
        if company_id:
            sess_q = sess_q.eq("company_id", company_id)
        sessions = sess_q.execute().data or []
        sess_ids = [s["id"] for s in sessions]
        events: List[Dict] = []
        # PostgREST: busca por lotes de session_id
        for i in range(0, len(sess_ids), 50):
            batch = sess_ids[i:i + 50]
            ev = (supabase.client.table("observed_events")
                  .select("session_id, direction, msg_type, text, interactive, wa_timestamp, created_at")
                  .in_("session_id", batch).execute().data or [])
            events.extend(ev)
        return sessions, events

    sessions, events = await asyncio.to_thread(_load)
    if not events:
        return {"ok": False, "error": "sem eventos observados", "insurer_key": insurer_key}

    by_session: Dict[str, List[Dict]] = defaultdict(list)
    for e in events:
        by_session[e.get("session_id")].append(e)

    map_acc: Dict[str, Any] = {"root": None, "nodes": {}, "edges": {}}
    all_labels: List[str] = []
    for sid, evs in by_session.items():
        weave_session(map_acc, evs)
    for node in map_acc["nodes"].values():
        all_labels.extend(o["label"] for o in node.get("options") or [])
    inferred_ramo, _servico = infer_ramo_servico(all_labels, " ".join(
        n["text"] for n in list(map_acc["nodes"].values())[:20]))
    ramo_final = ramo or inferred_ramo or "auto"

    compute_coverage(map_acc)
    map_acc["meta"] = {"insurer_key": insurer_key, "ramo": ramo_final,
                       "sessions": len(by_session), "events": len(events)}

    # Idempotente: substitui a proposta observada anterior (não empilha versões).
    def _save() -> None:
        supabase.client.table("ura_maps").update({"status": "superseded"}).eq(
            "insurer_key", insurer_key).eq("ramo", ramo_final).eq(
            "source", "observed").eq("status", "observed").execute()
        supabase.client.table("ura_maps").insert({
            "insurer_key": insurer_key, "ramo": ramo_final, "version": 1,
            "status": "observed", "map": map_acc, "source": "observed",
            "diff_summary": f"{len(map_acc['nodes'])} telas, cobertura {map_acc['coverage']['pct']}%",
        }).execute()

    await asyncio.to_thread(_save)
    logger.info(f"[ATLAS WEAVER] {insurer_key}/{ramo_final}: {len(map_acc['nodes'])} nós, "
                f"cobertura {map_acc['coverage']['pct']}%")
    return {"ok": True, "insurer_key": insurer_key, "ramo": ramo_final,
            "nodes": len(map_acc["nodes"]), "coverage": map_acc["coverage"]}
