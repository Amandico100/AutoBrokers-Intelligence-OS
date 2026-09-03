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


def _mascarar(texto: str) -> str:
    """A máscara do pipeline de inteligência, aplicada a texto de tela.

    ⚠️ Import local de propósito: `redaction_service` não importa nada do
    projeto (só `re`), e este módulo não precisa carregá-lo para as funções que
    não escrevem em tabela global.
    """
    try:
        from app.services.intelligence.redaction_service import mascara_de_tela

        return mascara_de_tela(str(texto or ""))
    except Exception:  # noqa: BLE001
        # 🔴 FALHA FECHADA. Não conseguir mascarar **nunca** vira permissão
        # para gravar cru numa tabela que todas as corretoras leem.
        return "[TEXTO NAO MASCARAVEL]"


def anchor_from_text(text: str) -> str:
    """Âncora regex a partir da tela — **mascarada antes de virar âncora**.

    🔴 SPEC-087 BLOCO C. Isto fazia `re.escape(texto[:60])` sobre o texto CRU
    da tela, e o resultado ia para `playbook_overlays`, que é uma tabela
    **GLOBAL, sem `company_id`** — de propósito, porque o Atlas é um só.

    > ⚠️ **A chave global está certa. Era a CARGA que vazava:** tráfego de UMA
    > corretora entrando numa tabela lida por TODAS.

    📊 É o mesmo furo que a SPEC-063 fechou nos mapas do Atlas (115 nós com nome
    de segurado), num escritor que ela não cobriu.

    ⛔ **Não existe mascarador novo aqui** (`CLAUDE.md` §5): quem mascara é
    `redaction_service`, que já era a autoridade única do pipeline de
    inteligência — e `ancora_permissiva` é o inverso dele, que devolve o
    casamento que a máscara tiraria.
    """
    # ⛔ NUNCA LEVANTA. 🔴 Antes desta SPEC esta função era `re.escape` puro e
    # não tinha como falhar; ao ganhar um import ela ganhou uma forma de morrer
    # — e 📊 quebrou `test_spec034_onda4`, um guarda que roda como SCRIPT, sem o
    # pacote `app` completo (`ModuleNotFoundError: app.services.intelligence`).
    #
    # ⚠️ Em produção o import funciona; o risco é o inverso do óbvio — uma
    # exceção aqui subiria por `apply_auto_overlays` e derrubaria o Alfaiate
    # inteiro por causa de uma âncora.
    #
    # ⛔ E a degradação é FECHADA: sem mascarador não se devolve o texto cru —
    # devolve-se âncora nenhuma, e quem chama pula (`if not anchor: continue`).
    try:
        from app.services.intelligence.redaction_service import ancora_permissiva

        return ancora_permissiva(text)
    except Exception as erro:  # noqa: BLE001
        logger.error("[ALFAIATE] âncora não pôde ser mascarada (%s) — este overlay "
                     "NÃO será criado", type(erro).__name__)
        return ""


def render_patch_report(playbook_ref: str, classes: Dict[str, List[Dict[str, Any]]]) -> str:
    lines = [f"🧵 ALFAIATE — mudanças detectadas na URA ({playbook_ref}):"]
    for item in classes.get("auto") or []:
        lines.append(f"✅ AUTO-APLICADO (aviso novo, ignorar): \"{item['tela'][:90]}\"")
    for item in classes.get("approval") or []:
        lines.append(f"🖐️ PRECISA DE APROVAÇÃO: {item['acao']} — \"{item['tela'][:90]}\"")
    for item in classes.get("never") or []:
        lines.append(f"⛔ NUNCA automático ({item.get('motivo', 'confirmação')}): \"{item['tela'][:90]}\"")
    return "\n".join(lines)


#: ⛔ O AUTO-APPLY NASCE DESLIGADO — SPEC-087 BLOCO B.
#:
#: 🔴 Com a chave consertada, `apply_auto_overlays` volta a **poder escrever
#: no corredor** — e o piloto começa na semana que vem.
#:
#: ⚠️ O bloco entrega a capacidade de **MEDIR** (o simulador roda, o resultado
#: é gravado), não a de **APLICAR**. `simulator_passed` deixa de ser NULL e passa
#: a dizer sim ou não; aí sim dá para discutir auto-apply, com dado.
#:
#: > **A arma foi consertada, descarregada, e o gatilho fica com o Founder.**
_ENV_AUTO_APPLY = "ALFAIATE_AUTO_APPLY"

#: Os únicos valores que ligam. ⚠️ Lista fechada, e não `bool(valor)`: 📊
#: `bool("false")` é `True`, e foi exatamente assim que a SPEC-093 quase ligou um
#: agente de atendimento com um `PATCH {"is_active": "false"}`.
_LIGADO = ("1", "true", "yes", "on", "sim")


def auto_apply_ligado() -> bool:
    """O gatilho do Founder. ⛔ Padrão DESLIGADO, e ausente = desligado."""
    import os

    return str(os.getenv(_ENV_AUTO_APPLY, "") or "").strip().lower() in _LIGADO


async def apply_auto_overlays(playbook_ref: str, classes: Dict[str, List[Dict[str, Any]]],
                              validate: bool = True) -> int:
    """Grava overlays noop para a classe AUTO (validando que o playbook atual
    continua íntegro no Simulador seria redundante aqui: noop não altera
    respostas — a validação é estrutural: só telas SEM opções entram).

    ⛔ **E ela não escreve nada com `ALFAIATE_AUTO_APPLY` desligado**, que é o
    padrão. Ver `auto_apply_ligado`.
    """
    if not auto_apply_ligado():
        # ⚠️ `info`, não `warning`: isto é o estado NORMAL e esperado. Um log de
        # alerta a cada drift ensinaria todo mundo a ignorar o log.
        logger.info("[ALFAIATE] auto-apply DESLIGADO (%s) — %d overlay(s) da "
                    "classe AUTO ficaram sem gravar, de propósito",
                    _ENV_AUTO_APPLY, len(classes.get("auto") or []))
        return 0
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
                    # ⛔ SPEC-087 BLOCO C — a NOTA também é carga, e ela ia crua.
                    # 📊 `note` gravava `texto[:120]` sem máscara nenhuma numa
                    # tabela global. A âncora acima foi consertada; deixar a
                    # nota crua ao lado seria trancar a porta e abrir a janela.
                    "note": f"Alfaiate: aviso novo da URA — \"{_mascarar(t)[:120]}\"",
                }).execute()
            )
            applied += 1
        # 🔴 SPEC-088 BLOCO E: O PULSO DO ALFAIATE MORA AQUI, e só aqui.
        # Ele estava em TRÊS módulos que não são a casa dele — `atlas/route_sentinel.py`,
        # `conversation_auditor.py` e `prompt_optimizer.py` — e nenhum dos três grava
        # overlay nenhum. Este é o único ponto do código em que o Alfaiate termina o
        # trabalho DELE: o laço de INSERT em `playbook_overlays` fechou sem exceção.
        #
        # ⚠️ DENTRO do `try`, nunca depois do `except` e nunca num `finally`: o caminho de
        # exceção não pinta card (referência ① do §7.3 — o Prometheus escreve
        # `last_success` só no ramo de sucesso).
        # ⚠️ E não há pulso no `return 0` do `auto_apply_ligado()` desligado (o padrão):
        # com o gatilho do Founder fechado o Alfaiate não trabalha, e um card verde ali
        # seria a mentira que esta SPEC fecha. `actions` = overlays REALMENTE gravados.
        try:
            from app.core.heartbeat import beat

            await beat("alfaiate", applied)
        except Exception:  # noqa: BLE001
            pass
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
