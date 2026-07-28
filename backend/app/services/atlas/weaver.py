"""SPEC-038 ATLAS — Tecelão/Weaver v2 (Bloco B + fidelidade de sequência).

Lê as sessões observadas e TECE o mapa da URA: cada tela da URA vira um nó (com
as opções que ela oferece); a escolha do humano (evento 'out' entre duas telas)
vira a aresta rotulada A→B. Sem a escolha capturada, cria aresta SEQUENCIAL
inferida (menor confiança) para a árvore ainda se formar.

v2 (founder 18/07 — "a sequência precisa ser fiel à seguradora"):
- Sessões processadas em ORDEM CRONOLÓGICA; cada nó/aresta ganha `order`
  (primeira vez em que apareceu) — a árvore renderiza na sequência real.
- RAIZ = a tela por onde as sessões mais COMEÇAM (saudação), não a primeira
  processada por acaso.
- `paths` = transcript fiel (templatizado, sem PII) das últimas sessões, para
  o modal "Sequência escrita".
- Casamento FUZZY clique×opção: o buttonText do clique ("Chaveiro") casa com o
  rótulo formatado da tela ("*7 -* *Chaveiro*") por normalização.
- VARIANTES: mesma escolha levando a telas diferentes em sessões diferentes
  (ex.: seguradora já tem o telefone salvo) ficam registradas com contagem.

Merge ACUMULATIVO em ura_maps (source='observed'). Qualidade sobre pressa:
ambíguo não é chutado — vira aresta inferida de baixa confiança.
"""

from __future__ import annotations

import asyncio
import logging
import re
import unicodedata
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_CONFIRM_THRESHOLD = 2  # aresta vista ≥2x = confirmada
_MAX_PATHS = 12         # transcripts guardados p/ o modal


def _norm_label(label: str) -> str:
    """Normaliza rótulo p/ casar clique×opção: sem acento/asterisco/número/pontuação."""
    s = unicodedata.normalize("NFKD", str(label or ""))
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    s = re.sub(r"[^a-z]", "", s)
    return s


def labels_match(option_label: str, click_label: str) -> bool:
    a, b = _norm_label(option_label), _norm_label(click_label)
    if not a or not b:
        return False
    return a == b or a.endswith(b) or b.endswith(a) or (len(b) >= 4 and b in a) or (len(a) >= 4 and a in b)


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
    if pending_screen is not None:
        steps.append({"screen": pending_screen, "choice": None})
    return steps


def _choice_label(choice: Optional[Dict[str, Any]]) -> Optional[str]:
    if not choice:
        return None
    it = choice.get("interactive") or {}
    for k in ("title", "selected"):
        if it.get(k):
            return str(it[k])[:60]
    txt = str(choice.get("text") or "").strip()
    return txt[:60] or None


def weave_session(map_acc: Dict[str, Any], events: List[Dict[str, Any]],
                  session_at: Optional[str] = None) -> Dict[str, Any]:
    """Tece UMA sessão sobre o mapa acumulado (mutação in-place + retorno)."""
    from app.services.atlas.templater import screen_node

    nodes: Dict[str, Any] = map_acc.setdefault("nodes", {})
    edges: Dict[str, Any] = map_acc.setdefault("edges", {})
    starts: Dict[str, int] = map_acc.setdefault("_starts", {})
    steps = _events_to_steps(events)

    path_steps: List[Dict[str, Any]] = []
    prev_node_id: Optional[str] = None
    prev_choice: Optional[str] = None
    first = True
    for step in steps:
        node = screen_node(step["screen"].get("text") or "")
        nid = node["hash"]
        if nid not in nodes:
            map_acc["_seq"] = int(map_acc.get("_seq") or 0) + 1
            nodes[nid] = {**node, "samples": 0, "order": map_acc["_seq"]}
        nodes[nid]["samples"] += 1
        # RECÊNCIA (founder 18/07): guarda a última vez que a tela apareceu — o
        # recente prevalece; telas obsoletas são marcadas depois (compute_coverage).
        st = step["screen"].get("wa_timestamp")
        if st and str(st) > str(nodes[nid].get("last_seen") or ""):
            nodes[nid]["last_seen"] = st
        # funde opções novas que apareceram nesta passagem (mantendo a ordem da URA)
        seen = {o["label"] for o in nodes[nid]["options"]}
        for o in node["options"]:
            if o["label"] not in seen:
                nodes[nid]["options"].append(o)
        if first:
            starts[nid] = starts.get(nid, 0) + 1
            first = False

        # liga a aresta do passo anterior até este nó
        if prev_node_id is not None:
            label = prev_choice or "→"  # sem escolha capturada = sequencial
            ekey = f"{prev_node_id}|{label}"
            e = edges.get(ekey)
            if e is None:
                map_acc["_seq"] = int(map_acc.get("_seq") or 0) + 1
                e = edges[ekey] = {"src": prev_node_id, "label": label, "to": nid,
                                   "count": 0, "inferred": prev_choice is None,
                                   "order": map_acc["_seq"], "dests": {}}
            e.setdefault("dests", {})
            e["dests"][nid] = e["dests"].get(nid, 0) + 1
            e["to"] = max(e["dests"], key=e["dests"].get)
            e["count"] += 1
            if prev_choice is not None:
                e["inferred"] = False  # escolha real confirma a aresta

        choice_lab = _choice_label(step["choice"])
        path_steps.append({"n": nid, "c": choice_lab})
        prev_node_id = nid
        prev_choice = choice_lab

    if path_steps:
        paths: List[Dict[str, Any]] = map_acc.setdefault("paths", [])
        paths.append({"at": session_at, "steps": path_steps})
        del paths[:-_MAX_PATHS]
    return map_acc


def label_inferred_edges(map_acc: Dict[str, Any]) -> int:
    """ROTULADOR POR ECO (Bloco C, determinístico — custo zero): em URAs de menu
    DIGITADO (Allianz "*1 -* ...") a escolha não chega por evento; mas a tela
    SEGUINTE costuma ecoar a opção ("Certo! ... *chaveiro* ..."). Se o destino
    de uma aresta sequencial ecoa EXATAMENTE UMA opção da origem, a aresta é
    rotulada com essa opção (echo=True). Ambíguo = não mexe (qualidade>pressa).
    Retorna quantas arestas foram rotuladas."""
    nodes = map_acc.get("nodes") or {}
    edges = map_acc.get("edges") or {}
    labeled = 0
    for ekey in list(edges.keys()):
        e = edges[ekey]
        if e.get("label") != "→":
            continue
        src, dest = nodes.get(e.get("src")), nodes.get(e.get("to"))
        if not src or not dest or not src.get("options"):
            continue
        dest_norm = _norm_label(dest.get("text", "")[:240])
        matches = [o["label"] for o in src["options"]
                   if len(_norm_label(o["label"])) >= 4 and _norm_label(o["label"]) in dest_norm]
        if len(matches) == 1:
            new_label = matches[0]
            new_key = f"{e['src']}|{new_label}"
            if new_key not in edges:
                edges[new_key] = {**e, "label": new_label, "inferred": False, "echo": True}
                del edges[ekey]
                labeled += 1
    return labeled


def compute_coverage(map_acc: Dict[str, Any]) -> Dict[str, Any]:
    """Casa cada OPÇÃO oferecida com a aresta percorrida (fuzzy), marca lacunas,
    variantes e o status de cada nó. Escolhe a RAIZ pela frequência de abertura."""
    edges = map_acc.get("edges") or {}
    nodes = map_acc.get("nodes") or {}

    # arestas reais (não sequenciais) agrupadas por nó de origem
    by_src: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for e in edges.values():
        if e.get("label") != "→":
            by_src[e["src"]].append(e)

    total_opts = covered_opts = 0
    for nid, node in nodes.items():
        node_gaps = 0
        for opt in node.get("options") or []:
            total_opts += 1
            match = None
            for e in by_src.get(nid, []):
                if labels_match(opt["label"], e["label"]):
                    match = e
                    break
            if match:
                opt["leads_to"] = match["to"]
                if match.get("echo"):
                    opt["confidence"] = "echo"  # deduzida pelo eco da tela seguinte
                else:
                    opt["confidence"] = "confirmed" if match.get("count", 0) >= _CONFIRM_THRESHOLD else "seen_once"
                opt["seen_count"] = match.get("count", 0)
                dests = match.get("dests") or {}
                if len(dests) > 1:  # variação real (ex.: já tem telefone salvo)
                    opt["variants"] = sorted(
                        ({"to": d, "count": c} for d, c in dests.items()),
                        key=lambda v: -v["count"])
                covered_opts += 1
            else:
                opt["leads_to"] = None
                opt["confidence"] = "gap"
                node_gaps += 1
        if node.get("kind") == "app_form":
            node["status"] = "app_form"
        elif not node.get("options"):
            node["status"] = "complete"
        elif node_gaps == 0:
            node["status"] = "complete"
        else:
            node["status"] = "partial"

    # RAIZ fiel: a tela por onde as sessões mais começam
    starts = map_acc.get("_starts") or {}
    if starts:
        map_acc["root"] = max(starts, key=starts.get)

    # OBSOLETO: telas cujo last_seen é muito mais antigo que o mais recente do
    # mapa (>60 dias) — provável menu antigo. Marcadas p/ revisão, não apagadas.
    seens = [str(n.get("last_seen")) for n in nodes.values() if n.get("last_seen")]
    if seens:
        newest = max(seens)
        try:
            from datetime import datetime, timezone

            newest_dt = datetime.fromtimestamp(int(newest), tz=timezone.utc) if newest.isdigit() \
                else datetime.fromisoformat(newest.replace("Z", "+00:00"))
            for n in nodes.values():
                ls = str(n.get("last_seen") or "")
                if ls:
                    ls_dt = datetime.fromtimestamp(int(ls), tz=timezone.utc) if ls.isdigit() \
                        else datetime.fromisoformat(ls.replace("Z", "+00:00"))
                    if (newest_dt - ls_dt).days > 60:
                        n["stale"] = True
        except (ValueError, OverflowError, OSError):
            pass
    map_acc["coverage"] = {
        "options_total": total_opts,
        "options_covered": covered_opts,
        "pct": round(100 * covered_opts / total_opts) if total_opts else 0,
        "nodes": len(nodes),
    }
    return map_acc


async def weave_insurer(insurer_key: str, ramo: str = "auto", company_id: Optional[str] = None,
                        use_ai: bool = False) -> Dict[str, Any]:
    """Reconstrói o mapa observado de uma seguradora×ramo a partir de TODAS as
    sessões capturadas (recência-primeiro) e salva como observed. Idempotente.
    use_ai=True liga o resolvedor de IA no resíduo ambíguo (custa; só na
    passada oficial da Sentinela, não no 'Tecer' manual)."""
    from app.core.database import get_supabase_client
    from app.services.atlas.templater import infer_ramo_servico

    supabase = get_supabase_client()

    # O PostgREST devolve no máximo 1.000 linhas por consulta, em silêncio.
    #
    # Isto custou caro em 28/07/2026. O laço abaixo pedia os eventos em lotes de
    # 50 sessões e confiava no que voltava. Com o histórico da Resulta:
    #
    #     Allianz .. 81 sessões, 2 lotes  ->  2.000 eventos de 4.986
    #     Porto .... 38 sessões, 1 lote   ->  1.000 eventos de 1.009
    #
    # O mapa da Allianz foi construído sobre 40% do material, e o número
    # gravado em `meta.events` era exatamente 2000 — redondo demais para ser
    # coincidência, e ninguém olhou.
    #
    # Truncar em silêncio é o pior defeito que um leitor pode ter: o mapa não
    # parecia quebrado, parecia pequeno. E "pequeno" a gente atribui a "a
    # corretora usou pouco".
    _PAGINA = 1000

    def _pagina_tudo(query_fn) -> List[Dict]:
        """Lê TODAS as páginas até a fonte secar. Nunca devolve pela metade."""
        tudo: List[Dict] = []
        inicio = 0
        while True:
            lote = (query_fn().range(inicio, inicio + _PAGINA - 1).execute().data) or []
            tudo.extend(lote)
            if len(lote) < _PAGINA:
                return tudo
            inicio += _PAGINA
            if inicio > 500_000:
                # Trava de segurança. Se um dia chegarmos aqui, é bug de laço,
                # não volume real — e é melhor gritar no log do que girar.
                logger.error("[ATLAS WEAVER] paginação passou de 500k linhas em "
                             "'%s' — interrompendo", insurer_key)
                return tudo

    def _load() -> Tuple[List[Dict], List[Dict]]:
        def _sessoes():
            q = (supabase.client.table("observed_sessions")
                 .select("id, started_at, ramo, servico")
                 .eq("insurer_key", insurer_key).order("started_at", desc=False))
            return q.eq("company_id", company_id) if company_id else q

        sessions = _pagina_tudo(_sessoes)
        sess_ids = [s["id"] for s in sessions]

        events: List[Dict] = []
        for i in range(0, len(sess_ids), 50):
            batch = sess_ids[i:i + 50]

            def _eventos(b=batch):
                return (supabase.client.table("observed_events")
                        .select("session_id, direction, msg_type, text, "
                                "interactive, wa_timestamp, created_at")
                        .in_("session_id", b)
                        # A ordem é obrigatória para paginar: sem `order`, o
                        # Postgres não garante a mesma sequência entre páginas,
                        # e a paginação passa a pular e repetir linhas.
                        .order("created_at", desc=False))

            events.extend(_pagina_tudo(_eventos))
        return sessions, events

    sessions, events = await asyncio.to_thread(_load)
    if not events:
        return {"ok": False, "error": "sem eventos observados", "insurer_key": insurer_key}

    by_session: Dict[str, List[Dict]] = defaultdict(list)
    for e in events:
        by_session[e.get("session_id")].append(e)

    map_acc: Dict[str, Any] = {"root": None, "nodes": {}, "edges": {}}
    # RECÊNCIA-PRIMEIRO (founder 18/07): a conversa MAIS RECENTE define a
    # estrutura/ordem canônica; as antigas só somam cobertura. Menus obsoletos
    # não contaminam a sequência do fluxo atual.
    sessions_recent_first = sorted(sessions, key=lambda s: str(s.get("started_at") or ""), reverse=True)
    for sess in sessions_recent_first:
        evs = by_session.get(sess["id"])
        if evs:
            weave_session(map_acc, evs, session_at=sess.get("started_at"))

    all_labels: List[str] = []
    for node in map_acc["nodes"].values():
        all_labels.extend(o["label"] for o in node.get("options") or [])
    inferred_ramo, _servico = infer_ramo_servico(all_labels, " ".join(
        n["text"] for n in list(map_acc["nodes"].values())[:20]))
    ramo_final = ramo or inferred_ramo or "auto"

    echoes = label_inferred_edges(map_acc)  # Bloco C: rotula menus digitados pelo eco
    if echoes:
        logger.info(f"[ATLAS WEAVER] {insurer_key}: {echoes} rotas rotuladas por eco")
    compute_coverage(map_acc)
    # RESOLVEDOR DE IA (modelo forte): só o resíduo ambíguo que o eco não pegou.
    # OPT-IN (custo): só na passada oficial da Sentinela, não no 'Tecer' manual.
    if use_ai:
        try:
            from app.services.atlas.atlas_parser import resolve_typed_choices

            await resolve_typed_choices(map_acc, insurer_key)
        except Exception as e:  # noqa: BLE001
            logger.info(f"[ATLAS WEAVER] resolvedor de IA pulado ({type(e).__name__})")
    map_acc.pop("_starts", None)
    map_acc.pop("_seq", None)
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
    try:
        from app.core.heartbeat import beat

        await beat("tecelao", 1)
    except Exception:  # noqa: BLE001
        pass
    logger.info(f"[ATLAS WEAVER] {insurer_key}/{ramo_final}: {len(map_acc['nodes'])} nós, "
                f"cobertura {map_acc['coverage']['pct']}%")
    return {"ok": True, "insurer_key": insurer_key, "ramo": ramo_final,
            "nodes": len(map_acc["nodes"]), "coverage": map_acc["coverage"]}
