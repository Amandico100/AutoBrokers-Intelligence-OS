"""SPEC-038 ATLAS — endpoints admin do Observador (Bloco A).

Todos exigem master admin (X-Admin-API-Key) — inteligência 100% AutoBrokers,
corretoras JAMAIS acessam (política do conhecimento global).
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import require_master_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/atlas", tags=["Admin ATLAS (SPEC-038)"])


@router.get("/observer/report")
async def observer_report(_: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Relatório vivo do spike/captura: últimos eventos observados (sem PII de
    não-seguradora por construção), sessões, contadores de descarte e a
    estrutura do último HISTORY_SYNC."""
    from app.core.database import get_supabase_client

    supabase = get_supabase_client()

    def _query() -> Dict[str, Any]:
        events = (supabase.client.table("observed_events")
                  .select("insurer_key, direction, msg_type, text, media_meta, wa_timestamp, created_at, session_id")
                  .order("created_at", desc=True).limit(25).execute())
        sessions = (supabase.client.table("observed_sessions")
                    .select("insurer_key, counterparty, status, started_at, last_event_at")
                    .order("last_event_at", desc=True).limit(10).execute())
        rows = []
        for e in (events.data or []):
            rows.append({**e, "text": (str(e.get("text") or "")[:120] or None)})
        return {"events": rows, "sessions": sessions.data or []}

    out = await asyncio.to_thread(_query)

    drops: Dict[str, Any] = {}
    history: Dict[str, Any] = {}
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        keys = [k async for k in r.scan_iter(match="atlas:drops:*")]
        for k in keys[:10]:
            name = k.decode() if isinstance(k, bytes) else str(k)
            h = await r.hgetall(name)
            drops[name.rsplit(":", 1)[-1]] = {
                (kk.decode() if isinstance(kk, bytes) else kk): (vv.decode() if isinstance(vv, bytes) else vv)
                for kk, vv in (h or {}).items()}
        hs = await r.get("atlas:history_sync:last_structure")
        hc = await r.hgetall("atlas:history_sync:count")
        history = {
            "last_structure": (hs.decode() if isinstance(hs, bytes) else hs),
            "count": {(kk.decode() if isinstance(kk, bytes) else kk): (vv.decode() if isinstance(vv, bytes) else vv)
                      for kk, vv in (hc or {}).items()},
        }
    except Exception as e:  # noqa: BLE001
        drops = {"error": type(e).__name__}

    return {"ok": True, **out, "drops": drops, "history_sync": history}


@router.post("/weave")
async def weave(body: Optional[Dict[str, Any]] = None, _: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Tece o mapa observado. Sem insurer_key: tece TODAS as seguradoras com
    sessões observadas. Idempotente (reprocessa o histórico)."""
    from app.services.atlas.weaver import weave_insurer

    payload = body or {}
    insurer = str(payload.get("insurer_key") or "").strip().lower()
    ramo = str(payload.get("ramo") or "").strip().lower() or "auto"
    if insurer:
        return await weave_insurer(insurer, ramo)

    from app.core.database import get_supabase_client

    supabase = get_supabase_client()

    def _distinct() -> list:
        rows = (supabase.client.table("observed_sessions")
                .select("insurer_key").not_.is_("insurer_key", "null").execute().data or [])
        return sorted({r["insurer_key"] for r in rows if r.get("insurer_key")})

    keys = await asyncio.to_thread(_distinct)
    results = [await weave_insurer(k, ramo) for k in keys]
    return {"ok": True, "woven": results}


@router.get("/maps")
async def atlas_maps(_: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Todos os mapas observados (resumo p/ a grade da página Atlas)."""
    from app.core.database import get_supabase_client

    supabase = get_supabase_client()

    def _q() -> list:
        return (supabase.client.table("ura_maps")
                .select("id, insurer_key, ramo, status, source, diff_summary, map, created_at")
                .in_("status", ["observed", "proposed", "active"])
                .order("created_at", desc=True).execute().data or [])

    rows = await asyncio.to_thread(_q)
    # dedupe por (insurer, ramo) mantendo o mais recente; resumo só (sem o mapa inteiro)
    seen = set()
    cards = []
    for r in rows:
        k = (r["insurer_key"], r["ramo"])
        if k in seen:
            continue
        seen.add(k)
        cov = ((r.get("map") or {}).get("coverage") or {})
        cards.append({
            "id": r["id"], "insurer_key": r["insurer_key"], "ramo": r["ramo"],
            "status": r["status"], "source": r["source"],
            "nodes": cov.get("nodes", 0), "coverage_pct": cov.get("pct", 0),
            "sessions": ((r.get("map") or {}).get("meta") or {}).get("sessions", 0),
            "updated_at": r["created_at"],
        })
    return {"ok": True, "cards": cards}


@router.post("/sentinela/run")
async def sentinela_run(body: Optional[Dict[str, Any]] = None, _: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Tece TODAS as seguradoras e passa cada uma pela Sentinela de Rotas
    (drift → Alfaiate v2 com gate do Simulador → alerta no estrutural)."""
    from app.services.atlas.route_sentinel import run_all

    drifts = await run_all(str((body or {}).get("company_id") or "") or None)
    return {"ok": True, "drifts": drifts, "count": len(drifts)}


@router.get("/drifts")
async def atlas_drifts(_: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Histórico de mudanças de menu (Sentinela) — para a página Atlas."""
    from app.core.database import get_supabase_client

    supabase = get_supabase_client()

    def _q() -> list:
        return (supabase.client.table("route_drift")
                .select("id, insurer_key, ramo, severity, summary, auto_applied, "
                        "simulator_passed, needs_founder, status, created_at")
                .order("created_at", desc=True).limit(40).execute().data or [])

    return {"ok": True, "drifts": await asyncio.to_thread(_q)}


@router.get("/cost-estimate")
async def cost_estimate(_: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Estimativa de custo do resolvedor de IA por seguradora (independe do nº
    de conversas históricas — a ingestão é gratuita/determinística)."""
    from app.core.database import get_supabase_client
    from app.services.atlas.atlas_parser import estimate_cost

    supabase = get_supabase_client()

    def _q() -> list:
        return (supabase.client.table("ura_maps").select("insurer_key, map")
                .eq("status", "observed").order("created_at", desc=True).limit(30).execute().data or [])

    rows = await asyncio.to_thread(_q)
    per = []
    seen = set()
    for r in rows:
        k = r["insurer_key"]
        if k in seen:
            continue
        seen.add(k)
        mp = r.get("map") or {}
        nodes = len(mp.get("nodes") or {})
        ambiguous = sum(1 for e in (mp.get("edges") or {}).values()
                        if e.get("label") == "→" and not e.get("echo"))
        est = estimate_cost(nodes, ambiguous)
        per.append({"insurer_key": k, "nodes": nodes, "ambiguous_edges": ambiguous, **est})
    total_brl = round(sum(p["brl_per_insurer"] for p in per), 2)
    return {"ok": True, "per_insurer": per, "total_brl_one_pass": total_brl,
            "nota": "Custo por PASSADA de tecelagem; a ingestão do histórico é gratuita (determinística)."}


@router.get("/native-form/{insurer_key}")
async def atlas_native_form(insurer_key: str, _: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """A PEDRA DE ROSETA: o schema do formulário nativo (app HDI/Yelum) + as
    respostas reais que um humano deu — a referência p/ a Even atravessar a tela."""
    from app.core.database import get_supabase_client

    supabase = get_supabase_client()

    def _q() -> list:
        return (supabase.client.table("observed_events")
                .select("interactive, insurer_key, wa_timestamp")
                .eq("insurer_key", insurer_key.lower()).eq("msg_type", "flow_reply")
                .order("wa_timestamp", desc=True).limit(5).execute().data or [])

    rows = await asyncio.to_thread(_q)
    from app.services.atlas.observer_intake import _parse_native_form

    forms = []
    for r in rows:
        it = r.get("interactive")
        if not isinstance(it, dict):
            continue
        nf = it.get("native_form")
        if not nf and it.get("extra"):  # captura antiga: parseia o extra na hora
            nf = _parse_native_form(it.get("extra"))
        if nf:
            forms.append(nf)
    return {"ok": True, "insurer_key": insurer_key, "captured": len(forms), "forms": forms}


@router.get("/map/{insurer_key}/{ramo}")
async def atlas_map_detail(insurer_key: str, ramo: str, _: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Mapa completo (árvore) de uma seguradora×ramo para a visualização."""
    from app.core.database import get_supabase_client

    supabase = get_supabase_client()

    def _q() -> Optional[dict]:
        rows = (supabase.client.table("ura_maps").select("id, map, status, source, created_at")
                .eq("insurer_key", insurer_key.lower()).eq("ramo", ramo.lower())
                .in_("status", ["observed", "proposed", "active"])
                .order("created_at", desc=True).limit(1).execute().data or [])
        return rows[0] if rows else None

    row = await asyncio.to_thread(_q)
    if not row:
        return {"ok": False, "error": "mapa não encontrado"}
    return {"ok": True, "insurer_key": insurer_key, "ramo": ramo,
            "status": row["status"], "map": row.get("map") or {}}


# ------------------------------------------------------------------ #
# ONBOARDING — parear o WhatsApp de uma atendente como OBSERVADOR
# (instância própria no GO, modo cofre, HISTORY_SYNC). Founder 18/07:
# "corretora nova fica 15-30 dias em modo observação".
# ------------------------------------------------------------------ #
def _go_admin() -> Dict[str, str]:
    base = (os.getenv("EVOLUTION_GO_BASE_URL") or "").rstrip("/")
    gk = os.getenv("EVOLUTION_GO_GLOBAL_KEY") or ""
    if not base or not gk:
        raise HTTPException(status_code=503, detail="evolution_go_admin_not_configured "
                                                    "(defina EVOLUTION_GO_GLOBAL_KEY para onboarding)")
    return {"base_url": base, "global_key": gk}


def _obs_instance_name(company_id: str, seq: int = 1) -> str:
    return f"ab-obs-{str(company_id).replace('-', '')[:10]}-{seq}"


@router.post("/onboarding/pair")
async def onboarding_pair(body: Dict[str, Any], _: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Cria uma instância OBSERVADORA no GO p/ a corretora e devolve o QR.
    Modo cofre por construção; subscribe MESSAGE+CONNECTION+HISTORY_SYNC."""
    import secrets

    from app.core.database import get_supabase_client
    from app.services.whatsapp.channel_security import build_webhook_url, new_webhook_credentials

    company_id = str(body.get("company_id") or "").strip()
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id_required")
    label = str(body.get("label") or "Atendente")
    # SPEC-040: escopo de captura. Onboarding de atendente captura por padrão
    # seguradoras E segurados (Espelho de Atendimento); 'insurers_only' opt-out.
    scope = str(body.get("scope") or "insurers_and_clients").strip().lower()
    if scope not in ("insurers_only", "insurers_and_clients"):
        scope = "insurers_and_clients"
    public_url = (os.getenv("PUBLIC_BACKEND_URL") or os.getenv("BACKEND_PUBLIC_URL") or "").rstrip("/")
    cfg = _go_admin()
    instance = _obs_instance_name(company_id, int(body.get("seq") or 1))
    inst_token = secrets.token_hex(16)
    token, token_hash, token_prefix = new_webhook_credentials()
    webhook_url = build_webhook_url(public_url, "evolution-go", token)

    async with httpx.AsyncClient(timeout=30.0, base_url=cfg["base_url"]) as client:
        gk = {"apikey": cfg["global_key"], "Content-Type": "application/json"}
        # 1) cria a instância (modo cofre no advancedSettings)
        cr = await client.post("/instance/create", headers=gk, json={
            "name": instance, "token": inst_token,
            "advancedSettings": {"readMessages": False, "alwaysOnline": False,
                                 "rejectCall": False, "ignoreGroups": True, "ignoreStatus": True},
        })
        if cr.status_code >= 400 and cr.status_code not in (409, 422):
            raise HTTPException(status_code=502, detail=f"go_create_failed:http_{cr.status_code}:{(cr.text or '')[:100]}")
        # 2) conecta + assina (webhook nosso, HISTORY_SYNC ligado)
        it = {"apikey": inst_token, "Content-Type": "application/json"}
        await client.post("/instance/connect", headers=it, json={
            "webhookUrl": webhook_url,
            "subscribe": ["MESSAGE", "CONNECTION", "HISTORY_SYNC"], "immediate": True})

    supabase = get_supabase_client()

    def _upsert() -> None:
        record = {
            "company_id": company_id, "identifier": instance, "purpose": "observer",
            "provider": "evolution-go", "base_url": cfg["base_url"], "instance_id": instance,
            "token": inst_token, "webhook_token_hash": token_hash, "webhook_token_prefix": token_prefix,
            "channel_status": "connecting", "is_active": True, "agent_id": None,
            "alert_target": {"label": label, "observer_scope": scope},
        }
        existing = (supabase.client.table("integrations").select("id")
                    .eq("company_id", company_id).eq("provider", "evolution-go")
                    .eq("instance_id", instance).limit(1).execute())
        if existing.data:
            supabase.client.table("integrations").update(record).eq("id", existing.data[0]["id"]).execute()
        else:
            supabase.client.table("integrations").insert(record).execute()

    await asyncio.to_thread(_upsert)
    return {"ok": True, "instance": instance, "next": f"/api/admin/atlas/onboarding/qr?instance={instance}"}


@router.get("/onboarding/qr")
async def onboarding_qr(instance: str, _: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    from app.core.database import get_supabase_client

    supabase = get_supabase_client()

    def _tok() -> Optional[str]:
        rows = (supabase.client.table("integrations").select("token")
                .eq("instance_id", instance).eq("purpose", "observer").limit(1).execute().data or [])
        return rows[0]["token"] if rows else None

    tok = await asyncio.to_thread(_tok)
    if not tok:
        raise HTTPException(status_code=404, detail="instancia_observer_nao_encontrada")
    cfg = _go_admin()
    async with httpx.AsyncClient(timeout=20.0, base_url=cfg["base_url"]) as client:
        r = await client.get("/instance/qr", headers={"apikey": tok})
        d = (r.json() or {}).get("data") if r.status_code < 400 and r.content else {}
    raw = str((d or {}).get("QRCode") or (d or {}).get("qrcode") or (d or {}).get("base64") or "")
    return {"ok": bool(raw), "instance": instance, "qr_base64": raw or None}


@router.get("/onboarding/status")
async def onboarding_status(_: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Todas as instâncias observadoras + estado ao vivo + eventos capturados hoje."""
    from app.core.database import get_supabase_client

    supabase = get_supabase_client()

    def _rows() -> list:
        return (supabase.client.table("integrations")
                .select("company_id, instance_id, token, channel_status, alert_target, created_at")
                .eq("purpose", "observer").eq("provider", "evolution-go").execute().data or [])

    rows = await asyncio.to_thread(_rows)
    out = []
    try:
        cfg = _go_admin()
        async with httpx.AsyncClient(timeout=15.0, base_url=cfg["base_url"]) as client:
            for r in rows:
                state = "unknown"
                try:
                    st = await client.get("/instance/status", headers={"apikey": r["token"]})
                    if st.status_code < 400:
                        data = (st.json() or {}).get("data") or {}
                        state = "conectado" if (data.get("LoggedIn")) else "aguardando pareamento"
                except Exception:  # noqa: BLE001
                    state = "indisponível"
                out.append({"company_id": r["company_id"], "instance": r["instance_id"],
                            "label": (r.get("alert_target") or {}).get("label"),
                            "scope": (r.get("alert_target") or {}).get("observer_scope") or "insurers_only",
                            "state": state, "since": r.get("created_at")})
    except HTTPException:
        # global key não configurada: ainda lista o que há no banco
        out = [{"company_id": r["company_id"], "instance": r["instance_id"],
                "label": (r.get("alert_target") or {}).get("label"),
                "state": r.get("channel_status") or "?", "since": r.get("created_at")} for r in rows]
    return {"ok": True, "observers": out}


@router.post("/observer/history-sync")
async def trigger_history_sync(
    body: Optional[Dict[str, Any]] = None, _: Any = Depends(require_master_admin)
) -> Dict[str, Any]:
    """Dispara o pedido de history sync no GO (POST /chat/history-sync) para a
    instância configurada nos envs — parte da verificação D2 do spike."""
    base = (os.getenv("EVOLUTION_GO_BASE_URL") or "").rstrip("/")
    token = os.getenv("EVOLUTION_GO_INSTANCE_TOKEN") or ""
    if not base or not token:
        return {"ok": False, "error": "evolution_go_not_configured"}
    count = int((body or {}).get("count") or 50)
    try:
        async with httpx.AsyncClient(timeout=30.0, base_url=base) as client:
            res = await client.post("/chat/history-sync",
                                    headers={"apikey": token, "Content-Type": "application/json"},
                                    json={"count": count})
            return {"ok": res.status_code < 400, "status": res.status_code, "body": (res.text or "")[:300]}
    except httpx.HTTPError as e:
        return {"ok": False, "error": f"go_unreachable:{type(e).__name__}"}


# ------------------------------------------------------------------ #
# SPEC-040 Onda 3 — Espelho de Atendimento (destilação, cards, playbooks)
# ------------------------------------------------------------------ #
@router.get("/espelho/resumo")
async def espelho_resumo(_: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Visão do Espelho: sessões destiladas, cards por status, playbooks e o
    BASELINE dos atendimentos humanos (INTERNO — nunca vai ao dashboard)."""
    from app.core.database import get_supabase_client

    db = get_supabase_client()

    def _query() -> Dict[str, Any]:
        sessions = (db.client.table("attendance_sessions")
                    .select("company_id, summary, started_at").eq("status", "closed")
                    .order("started_at", desc=True).limit(300).execute().data or [])
        distilled = [s for s in sessions if (s.get("summary") or {}).get("distilled")]
        scores = [int(((s.get("summary") or {}).get("distilled") or {}).get("score") or 0)
                  for s in distilled
                  if ((s.get("summary") or {}).get("distilled") or {}).get("score") is not None]
        by_company: Dict[str, list] = {}
        for s in distilled:
            sc = ((s.get("summary") or {}).get("distilled") or {}).get("score")
            if sc is not None:
                by_company.setdefault(str(s.get("company_id")), []).append(int(sc))
        cards = (db.client.table("knowledge_cards").select("status")
                 .limit(1000).execute().data or [])
        card_counts: Dict[str, int] = {}
        for c in cards:
            card_counts[c.get("status") or "?"] = card_counts.get(c.get("status") or "?", 0) + 1
        playbooks = (db.client.table("conduct_playbooks")
                     .select("id, ramo, servico, version, status, model_used, created_at")
                     .order("created_at", desc=True).limit(50).execute().data or [])
        return {
            "sessions_closed": len(sessions), "sessions_distilled": len(distilled),
            "baseline_humano": {
                "media_global": round(sum(scores) / len(scores), 1) if scores else None,
                "por_corretora": {k: round(sum(v) / len(v), 1) for k, v in by_company.items()},
                "amostras": len(scores),
            },
            "cards": card_counts, "playbooks": playbooks,
        }

    return {"ok": True, **(await asyncio.to_thread(_query))}


@router.get("/espelho/cards")
async def espelho_cards(status: str = "pending_review",
                        _: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    from app.core.database import get_supabase_client

    db = get_supabase_client()

    def _query() -> list:
        return (db.client.table("knowledge_cards")
                .select("id, card_text, category, ramo, insurer_key, status, pii_check, created_at")
                .eq("status", status).order("created_at", desc=True).limit(100).execute().data or [])

    return {"ok": True, "cards": await asyncio.to_thread(_query)}


@router.post("/espelho/cards/{card_id}/decide")
async def espelho_card_decide(card_id: str, body: Dict[str, Any],
                              _: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Aprova (publica no RAG global) ou rejeita um knowledge card."""
    from datetime import datetime, timezone

    from app.core.database import get_supabase_client

    action = str((body or {}).get("action") or "").strip().lower()
    if action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="action_must_be_approve_or_reject")
    db = get_supabase_client()

    def _get() -> Optional[Dict[str, Any]]:
        rows = (db.client.table("knowledge_cards").select("*")
                .eq("id", card_id).limit(1).execute().data or [])
        return rows[0] if rows else None

    card = await asyncio.to_thread(_get)
    if not card:
        raise HTTPException(status_code=404, detail="card_not_found")
    if action == "reject":
        await asyncio.to_thread(lambda: db.client.table("knowledge_cards").update(
            {"status": "rejected"}).eq("id", card_id).execute())
        return {"ok": True, "status": "rejected"}

    from app.services.attendance_distiller import publish_card_sync

    published = await asyncio.to_thread(publish_card_sync, card)
    if not published:
        raise HTTPException(status_code=422, detail="card_failed_pii_or_publish")
    await asyncio.to_thread(lambda: db.client.table("knowledge_cards").update(
        {"status": "published",
         "published_at": datetime.now(timezone.utc).isoformat()}).eq("id", card_id).execute())
    return {"ok": True, "status": "published"}


@router.get("/espelho/playbooks")
async def espelho_playbooks(_: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    from app.core.database import get_supabase_client

    db = get_supabase_client()

    def _query() -> list:
        return (db.client.table("conduct_playbooks")
                .select("id, ramo, servico, version, status, content, source_stats, model_used, created_at")
                .order("created_at", desc=True).limit(30).execute().data or [])

    return {"ok": True, "playbooks": await asyncio.to_thread(_query)}


@router.post("/espelho/run")
async def espelho_run(_: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Rodada MANUAL do destilador (verificação/urgência — ignora janela e
    marcador diário). Custo controlado pelo teto de sessões por rodada."""
    from app.services.attendance_distiller import distill_once

    stats = await distill_once(force=True)
    return {"ok": True, **stats}


# ------------------------------------------------------------------ #
# SPEC-040 Onda 4 — Gate de playbooks + Conselho de Agentes
# ------------------------------------------------------------------ #
@router.post("/espelho/playbooks/{playbook_id}/activate")
async def espelho_playbook_activate(playbook_id: str,
                                    _: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Roda o GATE completo (checks + juiz + conselho se ligado) e ativa se
    aprovado. Regressão é bloqueada por construção."""
    from app.services.playbook_gate import activate_playbook

    return await activate_playbook(playbook_id)


@router.post("/espelho/playbooks/rollback")
async def espelho_playbook_rollback(body: Dict[str, Any],
                                    _: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Rollback de 1 chamada: reativa a versão anterior do playbook."""
    from app.services.playbook_gate import rollback_playbook

    ramo = str((body or {}).get("ramo") or "").strip()
    servico = str((body or {}).get("servico") or "").strip()
    if not ramo or not servico:
        raise HTTPException(status_code=400, detail="ramo_e_servico_obrigatorios")
    return await rollback_playbook(ramo, servico)


@router.get("/conselho/status")
async def conselho_status(_: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    from app.services.agent_council import council_enabled, council_members

    last = None
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        raw = await r.get("council:last_convening")
        if raw:
            import json as _json

            last = _json.loads(raw.decode() if isinstance(raw, (bytes, bytearray)) else raw)
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True, "enabled": council_enabled(),
            "members": [f"{p}:{m}" for p, m in council_members()],
            "last_convening": last}


@router.post("/conselho/convene")
async def conselho_convene(body: Dict[str, Any],
                           _: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Convocação MANUAL (teste/decisão pontual do founder). Com o Conselho
    desligado, responde enabled=false sem custo nenhum."""
    from app.services.agent_council import convene_council

    question = str((body or {}).get("question") or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="question_obrigatoria")
    return await convene_council(question, str((body or {}).get("context") or ""),
                                 str((body or {}).get("kind") or "manual"))


# ------------------------------------------------------------------ #
# SPEC-040 Onda 5 — Memórias da Central, Replay e Contribuição
# ------------------------------------------------------------------ #
@router.get("/central/memorias")
async def central_memorias(_: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Blocos de memória de cada agente da Central (o que cada um 'sabe')."""
    from app.core.heartbeat import AGENT_TASKS
    from app.services.agent_memory import load_all_memories_sync

    rows = await asyncio.to_thread(load_all_memories_sync)
    names = {t[0]: t[1] for t in AGENT_TASKS}
    grouped: Dict[str, Any] = {}
    for r in rows:
        task = str(r.get("agent_task"))
        grouped.setdefault(task, {"agent": names.get(task, task), "blocks": []})
        grouped[task]["blocks"].append({"key": r.get("block_key"),
                                        "content": r.get("content"),
                                        "updated_at": r.get("updated_at")})
    return {"ok": True, "memorias": grouped}


@router.post("/central/memorias/rebuild")
async def central_memorias_rebuild(_: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Reescrita MANUAL dos blocos (verificação — normalmente roda 1x/dia)."""
    from app.services.agent_memory import rebuild_agent_memories

    written = await rebuild_agent_memories()
    return {"ok": True, "blocks_written": written}


@router.get("/replay/acionamentos")
async def replay_acionamentos(company_id: Optional[str] = None, limit: int = 20,
                              _: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Acionamentos ESPELHADOS (histórico persistente — sobrevive ao Redis)."""
    from app.core.database import get_supabase_client

    db = get_supabase_client()

    def _query() -> list:
        q = (db.client.table("conversations")
             .select("id, company_id, title, session_id, last_message_at, last_message_preview")
             .like("session_id", "dispatch:%")
             .order("last_message_at", desc=True).limit(min(max(1, limit), 50)))
        if company_id:
            q = q.eq("company_id", company_id)
        return q.execute().data or []

    return {"ok": True, "acionamentos": await asyncio.to_thread(_query)}


@router.get("/replay/acionamento/{conversation_id}")
async def replay_acionamento(conversation_id: str,
                             _: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Replay passo a passo de um acionamento: transcript espelhado + nota."""
    from app.core.database import get_supabase_client

    db = get_supabase_client()

    def _query() -> Dict[str, Any]:
        msgs = (db.client.table("messages")
                .select("role, content, created_at").eq("conversation_id", conversation_id)
                .order("created_at", desc=False).limit(300).execute().data or [])
        score = (db.client.table("conversation_scorecards")
                 .select("score, flags, created_at").eq("conversation_id", conversation_id)
                 .order("created_at", desc=True).limit(1).execute().data or [])
        return {"timeline": [
            {"at": m.get("created_at"),
             "quem": "seguradora" if m.get("role") == "user" else "motor",
             "texto": str(m.get("content") or "")[:400]} for m in msgs],
            "scorecard": score[0] if score else None}

    return {"ok": True, **(await asyncio.to_thread(_query))}


@router.get("/replay/atendimento/{session_id}")
async def replay_atendimento(session_id: str,
                             _: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Replay de uma sessão do Espelho de Atendimento — transcript MASCARADO
    (PII fica no cofre; a observabilidade não precisa do dado pessoal) +
    o resumo destilado."""
    from app.core.database import get_supabase_client
    from app.services.atlas.templater import templatize

    db = get_supabase_client()

    def _query() -> Dict[str, Any]:
        sess = (db.client.table("attendance_sessions").select("*")
                .eq("id", session_id).limit(1).execute().data or [])
        events = (db.client.table("attendance_transcripts")
                  .select("direction, msg_type, text, wa_timestamp")
                  .eq("session_id", session_id)
                  .order("wa_timestamp", desc=False).limit(300).execute().data or [])
        return {
            "session": ({"id": session_id,
                         "company_id": (sess[0] or {}).get("company_id"),
                         "started_at": (sess[0] or {}).get("started_at"),
                         "distilled": ((sess[0] or {}).get("summary") or {}).get("distilled")}
                        if sess else None),
            "timeline": [
                {"at": e.get("wa_timestamp"),
                 "quem": "atendente" if e.get("direction") == "out" else "cliente",
                 "tipo": e.get("msg_type"),
                 "texto": templatize(str(e.get("text") or ""))[:400]} for e in events],
        }

    return {"ok": True, **(await asyncio.to_thread(_query))}


@router.get("/onboarding/contribuicao")
async def onboarding_contribuicao(company_id: Optional[str] = None,
                                  _: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Contribuição de cada corretora para a inteligência global: sessões
    observadas (URA), sessões de atendimento capturadas e destiladas.
    O efeito rede visível: quem trouxe o quê."""
    from app.core.database import get_supabase_client

    db = get_supabase_client()

    def _query() -> Dict[str, Any]:
        def _count_by_company(table: str, extra=None) -> Dict[str, Dict[str, Any]]:
            q = db.client.table(table).select("company_id, created_at" + (", summary" if extra else ""))
            if company_id:
                q = q.eq("company_id", company_id)
            rows = q.order("created_at", desc=True).limit(3000).execute().data or []
            out: Dict[str, Dict[str, Any]] = {}
            for r in rows:
                cid = str(r.get("company_id"))
                b = out.setdefault(cid, {"total": 0, "destiladas": 0,
                                         "primeiro": r.get("created_at"), "ultimo": r.get("created_at")})
                b["total"] += 1
                if str(r.get("created_at") or "") < str(b["primeiro"] or ""):
                    b["primeiro"] = r.get("created_at")
                if str(r.get("created_at") or "") > str(b["ultimo"] or ""):
                    b["ultimo"] = r.get("created_at")
                if extra and ((r.get("summary") or {}).get("distilled")):
                    b["destiladas"] += 1
            return out

        return {"observacao_ura": _count_by_company("observed_sessions"),
                "atendimentos_parte1": _count_by_company("attendance_sessions", extra=True)}

    return {"ok": True, **(await asyncio.to_thread(_query))}
