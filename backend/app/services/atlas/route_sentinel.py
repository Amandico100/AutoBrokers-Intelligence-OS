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
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Import local nas funcoes, nao no topo: `ura_map_service` puxa o cliente do
# banco em tempo de carga, e um modulo do Atlas nao pode exigir banco so
# para ser importado por um teste.


def _drift_signature(insurer_key: str, ramo: str, severity: str, diff: Dict[str, Any]) -> str:
    payload = {
        "insurer_key": insurer_key,
        "ramo": ramo,
        "severity": severity,
        "added": diff.get("added") or [],
        "removed": diff.get("removed") or [],
        "changed_options": diff.get("changed_options") or [],
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _session_watermarks(rows: List[Dict[str, Any]]) -> List[tuple[str, str, str]]:
    """Uma marca d'água por rota — para saber se há material novo a tecer.

    A marca é a data de INGESTÃO (`created_at`), não a data original da
    mensagem (`last_event_at`). A troca aconteceu em 28/07/2026, e o motivo é
    concreto.

    O que acontecia
    ---------------
    A Resulta pareou o WhatsApp e o `HISTORY_SYNC` despejou 7.445 eventos de
    seis seguradoras em duas horas — conversas de março, junho e julho. A
    Sentinela comparou `max(last_event_at)`, viu que a mensagem mais nova da
    Allianz continuava sendo a de 18/07 que ela já conhecia, e concluiu
    **"nada novo"**.

    Resultado: 4.954 eventos da Allianz chegaram e o mapa não foi retecido.
    Ficou seis dias parado com 22 telas, enquanto os dados davam 450.

    Por que `created_at` é a marca certa
    ------------------------------------
    A pergunta que a Sentinela faz é *"chegou material novo desde a última
    tecelagem?"* — e material novo é o que **entrou**, não o que é recente.
    Pareamento traz passado: detectar novidade pela data da mensagem falha
    justamente quando a novidade É passado, que é o caso mais importante que
    existe aqui.

    `created_at` só anda para a frente quando dado entra. Não há como o
    histórico de março fazer a marca voltar.

    A tecelagem em si continua **recência-primeiro** (decisão do Founder,
    18/07): a conversa mais recente define a sequência canônica, e as antigas
    só somam cobertura. Isto muda apenas QUANDO tecer, nunca COMO.
    """
    latest: Dict[tuple[str, str], str] = {}
    for row in rows:
        insurer = str(row.get("insurer_key") or "").strip()
        if not insurer:
            continue
        # Sessao sem ramo declarado pertence ao mapa COMPLETO da seguradora,
        # nao a um mapa de "auto" que nao existe.
        ramo = str(row.get("ramo") or "todos")
        # `created_at` primeiro; `last_event_at` só como reserva para linhas
        # antigas que porventura não tenham o campo.
        stamp = str(row.get("created_at") or row.get("last_event_at") or "")
        key = (insurer, ramo)
        latest[key] = max(latest.get(key, ""), stamp)
    return [(key[0], key[1], stamp) for key, stamp in sorted(latest.items())]


def _watermark_key(insurer_key: str, ramo: str) -> str:
    digest = hashlib.sha256(f"{insurer_key}\0{ramo}".encode("utf-8")).hexdigest()[:24]
    return f"atlas:sentinela:watermark:{digest}"


async def _claim_with_redis(redis: Any, key: str, *, ttl_seconds: int) -> Optional[str]:
    """Atomic single-winner claim shared by all API/scheduler workers."""
    import secrets

    token = secrets.token_hex(12)
    acquired = await redis.set(key, token, nx=True, ex=max(1, ttl_seconds))
    return token if acquired else None


async def _release_redis_claim(redis: Any, key: str, token: str) -> None:
    try:
        await redis.eval(
            "if redis.call('get',KEYS[1])==ARGV[1] then "
            "return redis.call('del',KEYS[1]) else return 0 end",
            1,
            key,
            token,
        )
    except Exception:  # noqa: BLE001 - claim TTL remains the fallback
        pass


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
    signature = _drift_signature(insurer_key, ramo, severity, diff)
    summary = (f"{len(diff.get('added') or [])} telas novas, "
               f"{len(diff.get('removed') or [])} removidas, "
               f"{len(diff.get('changed_options') or [])} menus alterados")

    auto_applied = False
    simulator_passed: Optional[bool] = None
    needs_founder = severity == "structural"

    supabase = get_supabase_client()
    drift_claim_redis = None
    drift_claim_token: Optional[str] = None
    drift_claim_key = f"atlas:sentinela:drift:{signature}"
    if needs_founder:
        try:
            from app.core.redis import get_async_redis_client

            drift_claim_redis = await get_async_redis_client()
            drift_claim_token = await _claim_with_redis(
                drift_claim_redis, drift_claim_key, ttl_seconds=90 * 86400
            )
            if not drift_claim_token:
                return None
        except Exception:  # noqa: BLE001 - DB dedupe remains a fail-safe
            drift_claim_redis = None
            drift_claim_token = None

        def _same_unresolved_drift() -> bool:
            rows = (
                supabase.client.table("route_drift")
                .select("detail,status")
                .eq("insurer_key", insurer_key).eq("ramo", ramo)
                .order("created_at", desc=True).limit(10).execute().data or []
            )
            for previous in rows:
                if previous.get("status") not in ("open", "escalated"):
                    continue
                detail = previous.get("detail") if isinstance(previous.get("detail"), dict) else {}
                if detail.get("signature") == signature:
                    return True
            return False

        try:
            if await asyncio.to_thread(_same_unresolved_drift):
                return None
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[SENTINELA ROTAS] dedupe falhou: {type(e).__name__}")

    # COSMÉTICO → Alfaiate v2 com GATE do Simulador
    if severity == "cosmetic":
        try:
            playbook_ref = f"{insurer_key}:{ramo}"
            gate = await _alfaiate_with_gate(playbook_ref, active.get("map") or {}, observed_map)
            simulator_passed = gate.get("passed")
            auto_applied = gate.get("applied", False)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[SENTINELA ROTAS] alfaiate falhou: {type(e).__name__}")

    row = {
        "insurer_key": insurer_key, "ramo": ramo, "severity": severity,
        "summary": summary, "detail": {"added": (diff.get("added") or [])[:20],
                                       "removed": (diff.get("removed") or [])[:20],
                                       "changed": (diff.get("changed_options") or [])[:20],
                                       "signature": signature},
        "auto_applied": auto_applied, "simulator_passed": simulator_passed,
        "needs_founder": needs_founder,
        "status": "applied" if auto_applied else ("escalated" if needs_founder else "open"),
    }
    inserted = False
    try:
        await asyncio.to_thread(lambda: supabase.client.table("route_drift").insert(row).execute())
        inserted = True
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[SENTINELA ROTAS] registro falhou: {type(e).__name__}")
        if drift_claim_redis is not None and drift_claim_token:
            await _release_redis_claim(
                drift_claim_redis, drift_claim_key, drift_claim_token
            )

    if needs_founder and inserted:
        await _alert_founder(insurer_key, ramo, summary, diff)

    try:
        from app.core.heartbeat import beat

        await beat("sentinela_rotas", 1)
    except Exception:  # noqa: BLE001
        pass
    logger.info(f"[SENTINELA ROTAS] {insurer_key}/{ramo}: {severity} — {summary}")
    return row if inserted else None


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
    incrementalmente a cada janela configurada. Dá 'vida própria' ao Atlas — auto-atualiza
    os mapas e detecta mudança de menu sem ninguém clicar. Falha nunca derruba
    o scheduler."""
    try:
        import os
        from datetime import datetime, timezone

        try:
            interval_minutes = max(1, int(os.getenv("ATLAS_INCREMENTAL_INTERVAL_MINUTES", "15")))
        except ValueError:
            interval_minutes = 15
        window = int(datetime.now(timezone.utc).timestamp() // (interval_minutes * 60))
        try:
            from app.core.redis import get_async_redis_client

            redis = await get_async_redis_client()
            run_claim = await _claim_with_redis(
                redis,
                f"atlas:sentinela:last_run:{window}",
                ttl_seconds=max(120, interval_minutes * 120),
            )
            if not run_claim:
                return 0
        except Exception:  # noqa: BLE001 — sem redis, roda mesmo
            pass
        drifts = await run_all(None, incremental=True)
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


async def run_all(
    company_id: Optional[str] = None, *, incremental: bool = False
) -> List[Dict[str, Any]]:
    """Tece TODAS as seguradoras observadas e passa cada uma pela Sentinela.
    Chamado sob demanda (admin) ou por agendamento. Retorna os drifts achados."""
    from app.core.database import get_supabase_client
    from app.services.atlas.weaver import weave_insurer

    supabase = get_supabase_client()

    def _keys() -> List[tuple[str, str, str]]:
        # Paginado. O PostgREST corta em 1.000 linhas SEM avisar, e aqui isso
        # não daria erro nenhum: daria uma lista de rotas incompleta, e as
        # seguradoras que ficassem de fora simplesmente nunca seriam retecidas.
        #
        # Hoje são 177 sessões e caberia. Com três corretoras pareadas não cabe
        # mais — e o sintoma seria "o mapa da Tokio parou de atualizar", sem
        # nada no log para explicar.
        rows: List[Dict[str, Any]] = []
        inicio = 0
        while True:
            lote = (supabase.client.table("observed_sessions")
                    .select("insurer_key, ramo, last_event_at, created_at")
                    .not_.is_("insurer_key", "null")
                    # Ordem fixa: sem ela o Postgres não garante a mesma
                    # sequência entre páginas, e a paginação pula e repete.
                    .order("created_at", desc=False)
                    .range(inicio, inicio + 999).execute().data) or []
            rows.extend(lote)
            if len(lote) < 1000:
                break
            inicio += 1000
        return _session_watermarks(rows)

    redis = None
    if incremental:
        try:
            from app.core.redis import get_async_redis_client

            redis = await get_async_redis_client()
        except Exception:  # noqa: BLE001 - no Redis means process safely
            redis = None

    drifts: List[Dict[str, Any]] = []
    for insurer_key, ramo, watermark in await asyncio.to_thread(_keys):
        marker_key = _watermark_key(insurer_key, ramo)
        route_claim_key = f"{marker_key}:run"
        route_claim_token: Optional[str] = None
        if incremental and redis is not None:
            route_claim_token = await _claim_with_redis(
                redis, route_claim_key, ttl_seconds=15 * 60
            )
            if not route_claim_token:
                continue
            try:
                previous = await redis.get(marker_key)
                previous = previous.decode() if isinstance(previous, (bytes, bytearray)) else previous
                if previous == watermark:
                    await _release_redis_claim(
                        redis, route_claim_key, route_claim_token
                    )
                    route_claim_token = None
                    continue
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    f"[SENTINELA ROTAS] watermark indisponível: {type(e).__name__}"
                )
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
            if incremental and redis is not None:
                await redis.set(marker_key, watermark, ex=90 * 86400)
        except Exception as e:  # noqa: BLE001
            logger.error(f"[SENTINELA ROTAS] {insurer_key}/{ramo} falhou (segue as demais): {type(e).__name__}")
        finally:
            if redis is not None and route_claim_token:
                await _release_redis_claim(redis, route_claim_key, route_claim_token)
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
