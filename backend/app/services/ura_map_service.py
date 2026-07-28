"""MAPA DE URA (SPEC-034 Onda 2) — o território completo dos fluxos por seguradora.

Formato do mapa (JSONB em ura_maps.map):
{
  "root": "<node_id>",
  "nodes": {
    "<node_id>": {
      "text": "<texto normalizado da tela>",
      "kind": "menu" | "pergunta" | "informativo" | "finalize" | "terminal",
      "options": [{"label": "...", "reply": "...", "leads_to": "<node_id>|null"}],
      "hash": "<sha1 curto do texto normalizado>"
    }
  }
}

O playbook continua sendo o CAMINHO FELIZ compilado; o mapa é o que o Cérebro v2
consulta nos DESVIOS e o que o Alfaiate diffa para detectar mudanças (Onda 4).
Funções de diff/normalização são PURAS (testáveis offline); IO Supabase é
best-effort e nunca derruba quem chama.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import unicodedata
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def normalize_screen_text(text: str) -> str:
    """Normaliza a tela p/ hash estável: sem acentos, minúsculo, sem números
    voláteis (protocolos/telefones/nomes ficam como placeholder)."""
    s = unicodedata.normalize("NFKD", str(text or ""))
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    s = re.sub(r"\d[\d\.\-/() ]{5,}", "<num>", s)  # protocolos, cpfs, telefones
    s = re.sub(r"\s+", " ", s).strip()
    return s


def node_hash(text: str) -> str:
    return hashlib.sha1(normalize_screen_text(text).encode("utf-8")).hexdigest()[:12]


def diff_maps(old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """Diff legível entre dois mapas: nós adicionados/removidos e opções que
    mudaram em nós persistentes. Base do Alfaiate (Onda 4) e do aviso no admin."""
    old_nodes = (old or {}).get("nodes") or {}
    new_nodes = (new or {}).get("nodes") or {}
    old_by_hash = {n.get("hash"): (nid, n) for nid, n in old_nodes.items()}
    new_by_hash = {n.get("hash"): (nid, n) for nid, n in new_nodes.items()}
    added = [n["text"][:120] for h, (_, n) in new_by_hash.items() if h not in old_by_hash]
    removed = [n["text"][:120] for h, (_, n) in old_by_hash.items() if h not in new_by_hash]
    changed_options = []
    for h, (_, n_new) in new_by_hash.items():
        if h in old_by_hash:
            n_old = old_by_hash[h][1]
            old_labels = [o.get("label") for o in n_old.get("options") or []]
            new_labels = [o.get("label") for o in n_new.get("options") or []]
            if old_labels != new_labels:
                changed_options.append({"tela": n_new["text"][:80], "de": old_labels, "para": new_labels})
    return {
        "added": added, "removed": removed, "changed_options": changed_options,
        "safe_auto_apply": bool(added) and not removed and not changed_options,
    }


def render_map_for_llm(map_obj: Dict[str, Any], max_nodes: int = 30) -> str:
    """Resumo do mapa em texto p/ o Cérebro v2 ('onde estou e o que cada opção faz')."""
    nodes = (map_obj or {}).get("nodes") or {}
    lines: List[str] = []
    for nid, n in list(nodes.items())[:max_nodes]:
        opts = " | ".join(
            f"'{o.get('label')}'→responder '{o.get('reply')}'" for o in (n.get("options") or [])[:8]
        )
        lines.append(f"- [{n.get('kind')}] \"{n.get('text', '')[:110]}\"" + (f" → opções: {opts}" if opts else ""))
    return "\n".join(lines)


# ── IO Supabase (best-effort) ─────────────────────────────────────────────────
# Uma seguradora tem UM WhatsApp para toda a assistencia. A URA pergunta qual
# seguro e ramifica dali — o mapa observado contem a arvore INTEIRA, com auto,
# residencial, condominio e empresarial dentro dela.
#
# `todos` e o ramo desse mapa unico. Rotula-lo como "auto" era mentira com
# consequencia: a Resulta conversa sobre residencial e condominio, a AutoFleet
# so sobre auto e frota, e as duas falam com o MESMO numero.
RAMO_COMPLETO = "todos"


async def save_proposed_map(insurer_key: str, ramo: str, map_obj: Dict[str, Any],
                            source: str = "cartographer") -> Optional[str]:
    try:
        from app.core.database import get_supabase_client

        db = get_supabase_client()
        active = await get_active_map(insurer_key, ramo)
        diff = diff_maps((active or {}).get("map") or {}, map_obj)
        version = int((active or {}).get("version") or 0) + 1
        row = {
            "insurer_key": insurer_key, "ramo": ramo, "version": version,
            "status": "proposed", "map": map_obj, "source": source,
            "diff_summary": (
                f"+{len(diff['added'])} telas novas, -{len(diff['removed'])} removidas, "
                f"{len(diff['changed_options'])} menus alterados"
            ),
        }
        res = await asyncio.to_thread(lambda: db.client.table("ura_maps").insert(row).execute())
        return res.data[0]["id"] if res.data else None
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[URA_MAP] save_proposed falhou: {type(e).__name__}")
        return None


async def get_active_map(insurer_key: str, ramo: str = "auto") -> Optional[Dict[str, Any]]:
    """O mapa ativo da seguradora. Cai para o mapa COMPLETO quando não há um
    específico do ramo pedido.

    Quem chama pergunta por um ramo concreto — o acionamento pede "auto",
    porque é o que o playbook dele diz. Mas o mapa observado é **um só**, com a
    árvore inteira, e vive sob `todos`.

    Sem esta reserva, mudar o rótulo para a verdade faria o acionamento parar de
    achar o mapa: uma correção de nome viraria um defeito de funcionamento.
    """
    try:
        from app.core.database import get_supabase_client

        db = get_supabase_client()

        def _buscar(r: str):
            return (db.client.table("ura_maps").select("*")
                    .eq("insurer_key", insurer_key).eq("ramo", r)
                    .eq("status", "active")
                    .order("version", desc=True).limit(1).execute())

        res = await asyncio.to_thread(lambda: _buscar(ramo))
        if not res.data and ramo != RAMO_COMPLETO:
            res = await asyncio.to_thread(lambda: _buscar(RAMO_COMPLETO))
        return res.data[0] if res.data else None
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[URA_MAP] get_active falhou: {type(e).__name__}")
        return None


async def activate_map(map_id: str) -> bool:
    """Promove um mapa proposed→active e aposenta o active anterior."""
    try:
        from app.core.database import get_supabase_client

        db = get_supabase_client()
        res = await asyncio.to_thread(
            lambda: db.client.table("ura_maps").select("insurer_key, ramo").eq("id", map_id).limit(1).execute()
        )
        if not res.data:
            return False
        ik, ramo = res.data[0]["insurer_key"], res.data[0]["ramo"]
        await asyncio.to_thread(
            lambda: db.client.table("ura_maps").update({"status": "retired"})
            .eq("insurer_key", ik).eq("ramo", ramo).eq("status", "active").execute()
        )
        await asyncio.to_thread(
            lambda: db.client.table("ura_maps").update({"status": "active"}).eq("id", map_id).execute()
        )
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[URA_MAP] activate falhou: {type(e).__name__}")
        return False
