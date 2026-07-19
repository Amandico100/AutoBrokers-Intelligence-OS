"""Heartbeats dos agentes de fundo (SPEC-036 Etapa 1).

Cada task (Vigia/Sentinela, Follow-up, Garimpo, Auditor, Sugestões, Espelho via
router) registra pulso + contador de ações no Redis — a Central de Agentes do
portal admin lê daqui. Best-effort: nunca derruba a task.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

_KEY = "spec034:heartbeat:{task}"
_TTL = 7 * 86400

AGENT_TASKS = [
    # SPEC-038 ATLAS — a equipe do Observador (passiva, sempre ligada)
    ("observador", "Observador", "Observa em silêncio os atendimentos com as seguradoras e captura cada tela, botão e formulário nativo — nunca envia nada."),
    ("tecelao", "Tecelão", "Costura as observações em mapas de rota fiéis à sequência real de cada seguradora."),
    ("sentinela_rotas", "Sentinela de Rotas", "Vigia se a seguradora mudou o menu; dispara a atualização e avisa no que for estrutural."),
    # Atendimento / acionamento
    ("espelho", "Espelho", "Espelha toda conversa com seguradora no banco e no dashboard, em tempo real."),
    ("vigia_sentinela", "Vigia + Sentinela", "Vigia o desfecho de todo acionamento; a Sentinela destrava conversas paradas na URA."),
    ("followup", "Follow-up", "Pós-acionamento: confere se o prestador chegou e encerra com carinho."),
    ("garimpo", "Garimpo", "Extrai dores, desejos e pedidos das conversas dos corretores — vira insight de produto."),
    ("auditor", "Auditor", "Dá nota de qualidade a cada conversa e detecta regressões nos corredores."),
    ("alfaiate", "Alfaiate", "Ajusta os playbooks quando a URA da seguradora muda — auto-aplica só o que passa no Simulador."),
    ("sugestoes", "IA de Sugestões", "Envia recomendações semanais proativas às corretoras e registra as respostas."),
    ("cartografo", "Cartógrafo", "Mapeia os fluxos de URA das seguradoras (exploração ativa — só quando não há tráfego real)."),
    ("cerebro", "Cérebro v2", "Decide nos desvios: lê o Mapa da URA e escolhe a opção que avança para o objetivo."),
]


async def beat(task: str, actions: int = 0) -> None:
    try:
        from app.core.redis import get_async_redis_client

        redis = await get_async_redis_client()
        key = _KEY.format(task=task)
        raw = await redis.get(key)
        data = {}
        if raw:
            try:
                data = json.loads(raw.decode() if isinstance(raw, (bytes, bytearray)) else raw)
            except Exception:  # noqa: BLE001
                data = {}
        today = datetime.now(timezone.utc).date().isoformat()
        if data.get("day") != today:
            data["day"] = today
            data["actions_today"] = 0
        data["last_run"] = datetime.now(timezone.utc).isoformat()
        data["actions_today"] = int(data.get("actions_today") or 0) + max(0, int(actions))
        await redis.set(key, json.dumps(data), ex=_TTL)
    except Exception as e:  # noqa: BLE001
        logger.debug(f"[HEARTBEAT] beat({task}) falhou: {type(e).__name__}")


async def read_all() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        from app.core.redis import get_async_redis_client

        redis = await get_async_redis_client()
        for task_id, name, desc in AGENT_TASKS:
            raw = await redis.get(_KEY.format(task=task_id))
            data = {}
            if raw:
                try:
                    data = json.loads(raw.decode() if isinstance(raw, (bytes, bytearray)) else raw)
                except Exception:  # noqa: BLE001
                    data = {}
            out.append({"id": task_id, "name": name, "desc": desc,
                        "last_run": data.get("last_run"), "actions_today": data.get("actions_today") or 0})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[HEARTBEAT] read_all falhou: {type(e).__name__}")
        out = [{"id": t, "name": n, "desc": d, "last_run": None, "actions_today": 0}
               for t, n, d in AGENT_TASKS]
    return out
