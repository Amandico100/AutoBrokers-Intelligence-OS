"""SPEC-038 ATLAS — Sentinela de Rotas (Bloco C: auto-atualização).

O agente que dá VIDA PRÓPRIA ao Atlas. Após cada tecelagem, compara o mapa
OBSERVADO (verdade fresca do tráfego real) com o mapa ATIVO que o Cérebro usa,
e decide (política aprovada pelo founder 18/07):

- Sem mapa ativo (seguradora nova) → nada a fazer, o observado acumula.
- Drift COSMÉTICO (texto de tela mudou, mesma estrutura) → Alfaiate v2 patcheia
  e AUTO-APLICA **só se passar no Simulador**.
- Drift ESTRUTURAL (tela nova exigindo dado, opção nova, app nativo novo) →
  registra + ALERTA o founder (grupo WhatsApp), NÃO aplica sozinho.

Determinístico primeiro (diff_maps é puro). Nunca derruba quem chama.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def classify_severity(diff: Dict[str, Any], new_map: Dict[str, Any]) -> str:
    """cosmetic vs structural. Estrutural = telas novas OU opções que mudaram OU
    app_form novo. Só texto ajustado em telas existentes = cosmético."""
    added = diff.get("added") or []
    changed = diff.get("changed_options") or []
    if changed:
        return "structural"
    # tela nova que é MENU/PERGUNTA (muda o fluxo) = estrutural; informativa = cosmético
    new_nodes = (new_map or {}).get("nodes") or {}
    by_text = {str(n.get("text", ""))[:120]: n for n in new_nodes.values()}
    for txt in added:
        node = by_text.get(str(txt)[:120])
        if node and node.get("kind") in ("menu", "pergunta", "app_form"):
            return "structural"
    return "cosmetic" if (added or diff.get("removed")) else "cosmetic"


async def check_insurer(insurer_key: str, ramo: str, observed_map: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Compara o observado com o ativo; registra drift; aciona Alfaiate (gated).
    Retorna o registro de drift (ou None se nada mudou / greenfield)."""
    from app.core.database import get_supabase_client
    from app.services.ura_map_service import diff_maps, get_active_map

    active = await get_active_map(insurer_key, ramo)
    if not active or not (active.get("map") or {}).get("nodes"):
        return None  # greenfield: sem mapa ativo, nada a comparar

    diff = diff_maps(active.get("map") or {}, observed_map or {})
    if not (diff.get("added") or diff.get("removed") or diff.get("changed_options")):
        return None  # sem mudança

    severity = classify_severity(diff, observed_map)
    summary = (f"{len(diff.get('added') or [])} telas novas, "
               f"{len(diff.get('removed') or [])} removidas, "
               f"{len(diff.get('changed_options') or [])} menus alterados")

    auto_applied = False
    simulator_passed: Optional[bool] = None
    needs_founder = severity == "structural"

    # COSMÉTICO → Alfaiate v2 com GATE do Simulador
    if severity == "cosmetic":
        try:
            playbook_ref = f"{insurer_key}:{ramo}"
            gate = await _alfaiate_with_gate(playbook_ref, active.get("map") or {}, observed_map)
            simulator_passed = gate.get("passed")
            auto_applied = gate.get("applied", False)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[SENTINELA ROTAS] alfaiate falhou: {type(e).__name__}")

    supabase = get_supabase_client()
    row = {
        "insurer_key": insurer_key, "ramo": ramo, "severity": severity,
        "summary": summary, "detail": {"added": (diff.get("added") or [])[:20],
                                       "changed": (diff.get("changed_options") or [])[:20]},
        "auto_applied": auto_applied, "simulator_passed": simulator_passed,
        "needs_founder": needs_founder,
        "status": "applied" if auto_applied else ("escalated" if needs_founder else "open"),
    }
    try:
        await asyncio.to_thread(lambda: supabase.client.table("route_drift").insert(row).execute())
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[SENTINELA ROTAS] registro falhou: {type(e).__name__}")

    if needs_founder:
        await _alert_founder(insurer_key, ramo, summary, diff)

    try:
        from app.core.heartbeat import beat

        await beat("sentinela_rotas", 1)
    except Exception:  # noqa: BLE001
        pass
    logger.info(f"[SENTINELA ROTAS] {insurer_key}/{ramo}: {severity} — {summary}")
    return row


async def _alfaiate_with_gate(playbook_ref: str, old_map: Dict[str, Any],
                              new_map: Dict[str, Any]) -> Dict[str, Any]:
    """Alfaiate v2: só AUTO-APLICA se o Simulador aprovar o playbook novo contra
    o mapa novo. SPEC-050 (auditoria): o GATE roda ANTES da escrita — antes o
    overlay já estava no banco quando o Simulador rodava, o que anulava o gate."""
    from app.services.playbook_tailor import apply_auto_overlays, tailor_from_maps

    # 1) Diff + classes + relatório, SEM gravar nada ainda.
    result = await tailor_from_maps(playbook_ref, old_map, new_map, apply=False)
    passed = None
    try:
        from app.services.ura_simulator import simulate

        # GATE: replay do playbook contra a SESSÃO REAL mais recente (transcript
        # observado do mapa novo). Passa = playbook responde tudo sem divergir.
        script = _script_from_observed(new_map)
        if script:
            sim = simulate(playbook_ref, "guincho", {}, script)
            passed = bool(sim.get("ok")) if isinstance(sim, dict) else None
    except Exception as e:  # noqa: BLE001
        logger.info(f"[ALFAIATE v2] simulador indisponível ({type(e).__name__}) — não auto-aplica")
        passed = None

    # 2) Escrita SÓ com o gate verde (fail-closed: sem simulador = sem escrita).
    applied_count = 0
    if passed is True:
        applied_count = await apply_auto_overlays(playbook_ref, result.get("classes") or {})
    applied = applied_count > 0
    try:
        from app.core.heartbeat import beat

        await beat("alfaiate", 1 if applied else 0)
    except Exception:  # noqa: BLE001
        pass
    return {"passed": passed, "applied": applied, "report": result.get("report")}


def _script_from_observed(observed_map: Dict[str, Any]) -> List[Dict[str, Optional[str]]]:
    """Monta o script do Simulador a partir do transcript observado mais recente:
    tela templatizada da URA + a resposta REAL do humano que funcionou."""
    paths = (observed_map or {}).get("paths") or []
    nodes = (observed_map or {}).get("nodes") or {}
    if not paths:
        return []
    last = paths[-1]
    script: List[Dict[str, Optional[str]]] = []
    for step in last.get("steps") or []:
        node = nodes.get(step.get("n"))
        if not node:
            continue
        script.append({"screen": str(node.get("text") or ""), "expected": step.get("c")})
    return [s for s in script if s["screen"].strip()]


async def _alert_founder(insurer_key: str, ramo: str, summary: str, diff: Dict[str, Any]) -> None:
    """Alerta de mudança ESTRUTURAL pelo grupo (mesmo caminho do Vigia)."""
    try:
        from app.services.integration_service import get_integration_service
        from app.services.whatsapp_service import get_whatsapp_service

        added = "; ".join((diff.get("added") or [])[:3])
        msg = (f"🗺️ *Atlas — mudança estrutural detectada*\n\n"
               f"Seguradora: *{insurer_key}* ({ramo})\n{summary}\n"
               f"{('Telas novas: ' + added) if added else ''}\n\n"
               f"O menu da seguradora mudou de forma que exige revisão. "
               f"Abra o Atlas de Rotas para conferir e aprovar.")
        svc = get_integration_service()
        integ = svc.get_platform_whatsapp_integration()  # corretora da plataforma
        if integ:
            get_whatsapp_service().send_message(_founder_alert_number(), msg, integ)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[SENTINELA ROTAS] alerta ao founder falhou: {type(e).__name__}")


def _founder_alert_number() -> str:
    import os

    raw = os.getenv("ATTENDANT_INBOUND_ALLOWLIST", "") or ""
    return raw.split(",")[0].strip() or ""


async def check_atlas_sentinela() -> int:
    """Task periódica (APScheduler): tece TODAS as seguradoras e checa drift,
    no máximo 1x/dia (marcador Redis). Dá 'vida própria' ao Atlas — auto-atualiza
    os mapas e detecta mudança de menu sem ninguém clicar. Falha nunca derruba
    o scheduler."""
    try:
        from datetime import datetime, timezone

        today = datetime.now(timezone.utc).date().isoformat()
        try:
            from app.core.redis import get_async_redis_client

            redis = await get_async_redis_client()
            last = await redis.get("atlas:sentinela:last_run")
            last = last.decode() if isinstance(last, (bytes, bytearray)) else last
            if last == today:
                return 0
            await redis.set("atlas:sentinela:last_run", today, ex=2 * 86400)
        except Exception:  # noqa: BLE001 — sem redis, roda mesmo
            pass
        drifts = await run_all(None)  # global (todas as corretoras — a URA é global)
        # pulsa SEMPRE que roda (mesmo sem drift) — mostra o agente vivo na Central
        try:
            from app.core.heartbeat import beat

            await beat("sentinela_rotas", len(drifts))
        except Exception:  # noqa: BLE001
            pass
        return len(drifts)
    except Exception as e:  # noqa: BLE001 — nunca derruba o scheduler
        logger.warning(f"[SENTINELA ROTAS] check periódico falhou: {type(e).__name__}")
        return 0


async def run_all(company_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Tece TODAS as seguradoras observadas e passa cada uma pela Sentinela.
    Chamado sob demanda (admin) ou por agendamento. Retorna os drifts achados."""
    from app.core.database import get_supabase_client
    from app.services.atlas.weaver import weave_insurer

    supabase = get_supabase_client()

    def _keys() -> List[tuple]:
        rows = (supabase.client.table("observed_sessions").select("insurer_key, ramo")
                .not_.is_("insurer_key", "null").execute().data or [])
        seen = set()
        for r in rows:
            k = (r.get("insurer_key"), r.get("ramo") or "auto")
            if r.get("insurer_key"):
                seen.add(k)
        return sorted(seen)

    drifts: List[Dict[str, Any]] = []
    for insurer_key, ramo in await asyncio.to_thread(_keys):
        # SPEC-050 (auditoria): guarda POR seguradora — uma falha (ex.: mapa
        # corrompido de uma marca) não pode abortar a passada diária inteira.
        try:
            # passada oficial: liga o resolvedor de IA (resíduo ambíguo)
            woven = await weave_insurer(insurer_key, ramo, company_id, use_ai=True)
            if not woven.get("ok"):
                continue
            fresh = await _load_observed(insurer_key, woven.get("ramo") or ramo)
            if fresh:
                d = await check_insurer(insurer_key, woven.get("ramo") or ramo, fresh)
                if d:
                    drifts.append(d)
        except Exception as e:  # noqa: BLE001
            logger.error(f"[SENTINELA ROTAS] {insurer_key}/{ramo} falhou (segue as demais): {type(e).__name__}")
    return drifts


async def _load_observed(insurer_key: str, ramo: str) -> Optional[Dict[str, Any]]:
    from app.core.database import get_supabase_client

    supabase = get_supabase_client()

    def _q():
        rows = (supabase.client.table("ura_maps").select("map")
                .eq("insurer_key", insurer_key).eq("ramo", ramo)
                .eq("status", "observed").order("created_at", desc=True).limit(1).execute().data or [])
        return rows[0]["map"] if rows else None

    return await asyncio.to_thread(_q)
