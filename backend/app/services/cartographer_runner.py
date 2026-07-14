"""CARTÓGRAFO — runner (SPEC-034 Onda 2, fiação 14/07).

Liga o motor puro (cartographer.py) ao WhatsApp real. Pode rodar com o MESMO
número já pareado do atendimento (decisão do founder 14/07 — mapeamento único
enquanto o chip dedicado não chega): com CARTOGRAPHER_MODE=1, o webhook entrega
ao Cartógrafo os inbound de seguradoras COM exploração ativa — sem tocar no
atendimento (que só age com sessão de dispatch ativa) e sem re-parear nada.

Segurança em camadas:
- exploração NUNCA assume um número que tenha dispatch:active (acionamento real
  em curso tem prioridade absoluta);
- todos os freios do motor valem (nunca confirma, nunca entra em sinistro,
  orçamento de mensagens);
- ao terminar (done/aborted), o mapa vira ura_maps status=proposed (aprovação
  1-clique no admin) e a exploração é encerrada.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

_memory_store: Dict[str, str] = {}
_TTL = 6 * 3600


def cartographer_mode_enabled() -> bool:
    return os.getenv("CARTOGRAPHER_MODE", "0").strip() == "1"


def _key(insurer_phone: str) -> str:
    digits = "".join(ch for ch in str(insurer_phone or "") if ch.isdigit())
    return f"carto:active:{digits}"


async def _redis():
    try:
        from app.core.redis import get_async_redis_client

        return await get_async_redis_client()
    except Exception:  # noqa: BLE001
        return None


async def _save(insurer_phone: str, exp: Dict[str, Any]) -> None:
    exp2 = dict(exp)
    if isinstance(exp2.get("visited_edges"), set):
        exp2["visited_edges"] = [list(v) for v in exp2["visited_edges"]]
    payload = json.dumps(exp2, ensure_ascii=False, default=str)
    r = await _redis()
    if r is not None:
        await r.set(_key(insurer_phone), payload, ex=_TTL)
    else:
        _memory_store[_key(insurer_phone)] = payload


async def load_exploration(insurer_phone: str) -> Optional[Dict[str, Any]]:
    r = await _redis()
    raw = await r.get(_key(insurer_phone)) if r is not None else _memory_store.get(_key(insurer_phone))
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:  # noqa: BLE001
        return None


async def clear_exploration(insurer_phone: str) -> None:
    r = await _redis()
    if r is not None:
        await r.delete(_key(insurer_phone))
    else:
        _memory_store.pop(_key(insurer_phone), None)


async def start_exploration(*, insurer_key: str, ramo: str, test_data: Dict[str, str],
                            send: Callable[[str], None]) -> Dict[str, Any]:
    """Abre a exploração e cumprimenta a URA. Recusa se houver acionamento ativo."""
    from app.services.cartographer import new_exploration
    from app.services.insurer_registry import registry_whatsapp
    from app.services.corridor_playbooks import resolve_insurer_contact

    phone = resolve_insurer_contact(insurer_key) or registry_whatsapp(insurer_key)
    if not phone:
        return {"ok": False, "error": f"sem WhatsApp para '{insurer_key}'"}
    try:
        from app.services.dispatch_router import load_active_dispatch

        # prioridade absoluta do atendimento real (qualquer company)
        # checagem simples: se existir QUALQUER dispatch ativo p/ este número
        r = await _redis()
        if r is not None:
            async for k in r.scan_iter(match=f"dispatch:active:*:{phone}"):
                return {"ok": False, "error": "acionamento REAL ativo neste número — exploração recusada"}
    except Exception:  # noqa: BLE001
        pass

    exp = new_exploration(insurer_key=insurer_key, ramo=ramo, test_data=test_data)
    exp["insurer_phone"] = phone
    await _save(phone, exp)
    try:
        send("Oi")
        exp.setdefault("transcript", []).append({"direction": "out", "text": "Oi"})
        await _save(phone, exp)
    except Exception as e:  # noqa: BLE001
        logger.error(f"[CARTO] abertura falhou: {type(e).__name__}")
        return {"ok": False, "error": "falha ao enviar abertura"}
    logger.info(f"[CARTO] exploração iniciada: {insurer_key}/{ramo} → {phone}")
    return {"ok": True, "insurer_phone": phone}


async def handle_cartographer_inbound(from_phone: str, text: str,
                                      send: Callable[[str], None]) -> bool:
    """True = mensagem consumida pelo Cartógrafo. Chamado pelo webhook ANTES do
    dispatch router quando CARTOGRAPHER_MODE=1."""
    if not cartographer_mode_enabled():
        return False
    exp = await load_exploration(from_phone)
    if not exp:
        return False
    from app.services.cartographer import exploration_to_map, handle_insurer_message, has_unexplored

    if isinstance(exp.get("visited_edges"), list):
        exp["visited_edges"] = set(tuple(v) for v in exp["visited_edges"])
    reply = handle_insurer_message(exp, str(text or ""))
    if reply:
        try:
            send(reply)
        except Exception as e:  # noqa: BLE001
            logger.error(f"[CARTO] envio falhou: {type(e).__name__}")
    state = str(exp.get("state") or "")
    if state in ("done", "aborted"):
        # MULTI-PASS (exigência do founder 14/07: TODAS as combinações, não só
        # uma rota): terminou um ramo com segurança e ainda há opções seguras
        # não percorridas → recomeça a conversa ("Oi") mantendo o mapa e as
        # arestas já visitadas. Limite duro de passadas por seguradora.
        passes = int(exp.get("pass_count") or 0) + 1
        exp["pass_count"] = passes
        max_passes = int(os.getenv("CARTOGRAPHER_MAX_PASSES", "12"))
        if (state == "done" and passes < max_passes and has_unexplored(exp)):
            exp["state"] = "exploring"
            exp["msg_count"] = 0
            exp["current_path"] = []
            exp["last_node"] = None
            exp["last_reply"] = None
            await _save(from_phone, exp)
            try:
                send("Oi")
                exp.setdefault("transcript", []).append({"direction": "out", "text": "Oi"})
                await _save(from_phone, exp)
                logger.info(f"[CARTO] passada {passes} concluída — reiniciando p/ próximo ramo "
                            f"({exp.get('insurer_key')}, nodes={len(exp.get('nodes') or {})})")
            except Exception as e:  # noqa: BLE001
                logger.error(f"[CARTO] reinício falhou: {type(e).__name__}")
            return True
        try:
            from app.services.ura_map_service import save_proposed_map

            map_obj = exploration_to_map(exp)
            map_id = await save_proposed_map(str(exp.get("insurer_key")), str(exp.get("ramo") or "auto"), map_obj)
            logger.info(f"[CARTO] mapa salvo ({state}, {passes} passadas): {exp.get('insurer_key')} "
                        f"nodes={len(map_obj.get('nodes') or {})} id={map_id}")
        except Exception as e:  # noqa: BLE001
            logger.error(f"[CARTO] salvar mapa falhou: {type(e).__name__}")
        await clear_exploration(from_phone)
    else:
        await _save(from_phone, exp)
    try:
        from app.core.heartbeat import beat

        await beat("cartografo", 1)
    except Exception:  # noqa: BLE001
        pass
    return True
