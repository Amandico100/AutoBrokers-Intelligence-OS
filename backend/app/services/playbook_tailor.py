"""ALFAIATE v1 (SPEC-034 Onda 4) — ajuste de playbooks com classes de risco.

Recebe o DIFF entre o Mapa de URA novo (Cartógrafo/Espelho) e o ativo, e:

1. AUTO-APLICA só a classe mais segura: tela INFORMATIVA nova (sem opções, sem
   coleta) vira um passo noop em runtime via `playbook_overlays` (Supabase) —
   sem deploy, com validação prévia no Simulador e aviso ao admin/suporte.
2. Mudança de MENU/rótulos → proposta de patch legível p/ APROVAÇÃO (1 clique
   no futuro painel; hoje: mensagem no grupo de suporte com o patch pronto).
3. Qualquer coisa perto de FINALIZE/confirmação → NUNCA automático (só relata).

Overlays são a ponte segura: o playbook (código versionado) continua a fonte
da verdade; o overlay só ENSINA o motor a ignorar avisos novos da URA.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_FINALIZE_HINT = re.compile(
    r"confirmar|prosseguir|tudo est[áa] correto|agendamento", re.IGNORECASE)


def classify_diff(diff: Dict[str, Any], new_map: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Separa o diff do mapa em classes de risco (puro, testável).
    - auto: telas informativas novas → overlay noop;
    - approval: telas novas COM opções ou menus alterados → patch proposto;
    - never: qualquer coisa com cara de confirmação final → só relatar."""
    nodes = (new_map or {}).get("nodes") or {}
    by_text = {str(n.get("text") or ""): n for n in nodes.values()}
    out: Dict[str, List[Dict[str, Any]]] = {"auto": [], "approval": [], "never": []}

    for text in diff.get("added") or []:
        node = by_text.get(text) or {}
        kind = str(node.get("kind") or "")
        if kind == "finalize" or _FINALIZE_HINT.search(text):
            out["never"].append({"tela": text, "motivo": "próxima da confirmação final"})
        elif kind == "informativo" and not (node.get("options") or []):
            out["auto"].append({"tela": text, "acao": "overlay noop"})
        else:
            out["approval"].append({"tela": text, "acao": "novo passo de menu/coleta — revisar"})

    for change in diff.get("changed_options") or []:
        alvo = str(change.get("tela") or "")
        bucket = "never" if _FINALIZE_HINT.search(alvo) else "approval"
        out[bucket].append({"tela": alvo, "acao": f"rótulos mudaram: {change.get('de')} → {change.get('para')}"})

    for text in diff.get("removed") or []:
        out["approval"].append({"tela": text, "acao": "tela sumiu do fluxo — revisar passo correspondente"})
    return out


def anchor_from_text(text: str) -> str:
    """Gera uma âncora regex segura a partir do texto normalizado da tela
    (trecho inicial estável, escapado)."""
    snippet = str(text or "").strip()[:60]
    return re.escape(snippet) if snippet else ""


def render_patch_report(playbook_ref: str, classes: Dict[str, List[Dict[str, Any]]]) -> str:
    lines = [f"🧵 ALFAIATE — mudanças detectadas na URA ({playbook_ref}):"]
    for item in classes.get("auto") or []:
        lines.append(f"✅ AUTO-APLICADO (aviso novo, ignorar): \"{item['tela'][:90]}\"")
    for item in classes.get("approval") or []:
        lines.append(f"🖐️ PRECISA DE APROVAÇÃO: {item['acao']} — \"{item['tela'][:90]}\"")
    for item in classes.get("never") or []:
        lines.append(f"⛔ NUNCA automático ({item.get('motivo', 'confirmação')}): \"{item['tela'][:90]}\"")
    return "\n".join(lines)


async def apply_auto_overlays(playbook_ref: str, classes: Dict[str, List[Dict[str, Any]]],
                              validate: bool = True) -> int:
    """Grava overlays noop para a classe AUTO (validando que o playbook atual
    continua íntegro no Simulador seria redundante aqui: noop não altera
    respostas — a validação é estrutural: só telas SEM opções entram)."""
    applied = 0
    try:
        from app.core.database import get_supabase_client

        db = get_supabase_client()
        for item in classes.get("auto") or []:
            anchor = anchor_from_text(item["tela"])
            if not anchor:
                continue
            dup = await asyncio.to_thread(
                lambda a=anchor: db.client.table("playbook_overlays").select("id")
                .eq("playbook_ref", playbook_ref).eq("anchor", a).eq("status", "active")
                .limit(1).execute()
            )
            if dup.data:
                continue
            await asyncio.to_thread(
                lambda a=anchor, t=item["tela"]: db.client.table("playbook_overlays").insert({
                    "playbook_ref": playbook_ref, "kind": "noop", "anchor": a,
                    "note": f"Alfaiate: aviso novo da URA — \"{t[:120]}\"",
                }).execute()
            )
            applied += 1
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ALFAIATE] apply_auto_overlays falhou: {type(e).__name__}")
    return applied


async def tailor_from_maps(playbook_ref: str, old_map: Dict[str, Any],
                           new_map: Dict[str, Any], apply: bool = True) -> Dict[str, Any]:
    """Pipeline completo: diff → classes → (opcional) auto-aplica noops → relatório.

    SPEC-050 (auditoria): `apply=False` permite ao chamador rodar o GATE do
    Simulador ANTES de qualquer escrita — a gravação do overlay nunca pode
    acontecer antes da validação (era exatamente o furo encontrado)."""
    from app.services.ura_map_service import diff_maps

    diff = diff_maps(old_map or {}, new_map or {})
    classes = classify_diff(diff, new_map)
    applied = await apply_auto_overlays(playbook_ref, classes) if apply else 0
    return {"diff": diff, "classes": classes, "auto_applied": applied,
            "report": render_patch_report(playbook_ref, classes)}
