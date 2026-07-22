# -*- coding: utf-8 -*-
"""SPEC-050 - QR que sempre nasce, variaveis que nunca congelam, Conhecimento
humano e quick-wins da auditoria dos agentes da Central.

Cobre: computeAgentConfigUpdate persiste o valor CRU (nao o renderizado),
desconectar nuclear + auto-cura de instancia zumbi no canal GO, pagina de
Conhecimento sem seletor de assistente e com lista humana, gate do Alfaiate
ANTES da escrita, guarda por-seguradora no run_all, dedup estrutural do
Auditor, pulso com contagem no Garimpo, Vigia/Follow-up no feed de Atividades.
Standalone (source checks), sem pytest.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT.parent
PASS = FAIL = 0
FAILURES = []


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  [ok] {name}")
    else:
        FAIL += 1
        FAILURES.append((name, detail))
        print(f"  [X] {name}{': ' + str(detail) if detail else ''}")


def _src(rel, base=None):
    return ((base or WEB) / rel).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
print("\n[1] Variaveis nunca congelam (2a raiz do bug do rename)")

_bp = _src("lib/admin/agent-blueprints-canonical.ts")
check("computeAgentConfigUpdate NAO grava o renderizado",
      "savedVars[k] = eff.variables_used[k]" not in _bp)
check("persiste o CRU: input > salvo anterior", "prevSaved" in _bp and "incoming !== undefined" in _bp)

# ---------------------------------------------------------------------------
print("\n[2] Canal GO — QR sempre nasce")

_ch = _src("app/api/whatsapp_channel.py", ROOT)
check("desconectar apaga instancia com sessao registrada (jid persistente)",
      "instance/delete/" in _ch and "still_registered" in _ch)
check("linha aposentada apos delete (retired)", "retired" in _ch)
check("setup auto-cura linha zumbi (connect 401/404 -> recria)",
      "linha zumbi" in _ch and "(401, 404)" in _ch)
check("create auto-cura instancia fantasma (409/422 -> delete+recria)",
      "_go_find_by_name" in _ch)

# ---------------------------------------------------------------------------
print("\n[3] Conhecimento — humano e sem selecao de assistente")

_kc = _src("app/dashboard/personalizacao/conhecimento/KnowledgeClient.tsx")
check("seletor 'qual assistente' REMOVIDO", "Qual assistente" not in _kc and "agentId" not in _kc)
check("lista humanizada (apolices InfoCap legiveis)",
      "humanize" in _kc and "Apólice do sistema da corretora" in _kc)
check("status em portugues", "Pronto para uso" in _kc and "Processando" in _kc)
_up = _src("app/api/dashboard/knowledge/upload/route.ts")
check("upload resolve o agente Core sozinho (server-side)",
      "agent_role', 'core'" in _up.replace('"', "'"))

# ---------------------------------------------------------------------------
print("\n[4] Quick-wins da auditoria dos agentes")

_pt = _src("app/services/playbook_tailor.py", ROOT)
check("Alfaiate: tailor aceita apply=False (gate antes da escrita)",
      "apply: bool = True" in _pt and "if apply else 0" in _pt)
_rs = _src("app/services/atlas/route_sentinel.py", ROOT)
check("Alfaiate v2: escrita SO com gate verde (fail-closed)",
      "apply=False" in _rs and "if passed is True:" in _rs)
check("run_all: guarda POR seguradora (falha nao aborta a passada)",
      "segue as demais" in _rs)
_ca = _src("app/services/conversation_auditor.py", ROOT)
check("Auditor: dedup estrutural por conversa/dia", "ja auditada hoje" in _ca or "já auditada hoje" in _ca)
check("Auditor: docstring honesta (cascata LLM = planejada)",
      "NÃO implementadas" in _ca or "NAO implementadas" in _ca)
_bi = _src("app/services/broker_insights.py", ROOT)
check("Garimpo: pulso com contagem", 'beat("garimpo", mined)' in _bi)
check("Garimpo: docstring alinhada (LLM ligada por padrao, desligavel)",
      "LIGADA por padrão" in _bi or "LIGADA por padrao" in _bi)
_wd = _src("app/tasks/dispatch_watchdog.py", ROOT)
check("Vigia: handoff aparece nas Atividades", "log_activity" in _wd)
_fu = _src("app/tasks/dispatch_followup.py", ROOT)
check("Follow-up: acao aparece nas Atividades", "log_activity" in _fu)

# ---------------------------------------------------------------------------
print(f"\n{'=' * 60}")
print(f"RESULTADO: {PASS} ok, {FAIL} falhas")
for name, detail in FAILURES:
    print(f"  FALHOU: {name} {detail}")
sys.exit(1 if FAIL else 0)
