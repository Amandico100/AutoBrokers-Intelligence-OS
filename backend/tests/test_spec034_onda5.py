"""SPEC-034 Onda 5 - IA de Sugestoes proativas (auxiliar global ON por padrao).

Rodar: python backend/tests/test_spec034_onda5.py
"""

import importlib.util
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASS = 0
FAIL = 0
FAILURES = []


def check(name, cond, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [ok] {name}")
    else:
        FAIL += 1
        FAILURES.append((name, detail))
        print(f"  [X] {name}{': ' + str(detail) if detail else ''}")


def _load(dotted, rel):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(dotted, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = mod
    spec.loader.exec_module(mod)
    return mod


for name in ("app", "app.services", "app.core"):
    module = sys.modules.setdefault(name, types.ModuleType(name))
    module.__path__ = []

sug = _load("app.services.proactive_suggestions", "app/services/proactive_suggestions.py")


def run():
    print("== SPEC-034 Onda 5 - IA de Sugestoes ==\n")

    check("ON por padrao (perfil vazio)", sug.suggestions_enabled({}) is True)
    check("ON com config parcial", sug.suggestions_enabled({"sugestoes": {}}) is True)
    check("so desliga com enabled=false explicito",
          sug.suggestions_enabled({"sugestoes": {"enabled": False}}) is False)

    check("alvo: whatsapp dedicado das sugestoes",
          sug.target_whatsapp({"sugestoes": {"whatsapp": "5547999"}}) == "5547999")
    check("alvo: fallback no suporte humano",
          sug.target_whatsapp({"suporte_humano_whatsapp": "5547888"}) == "5547888")

    insights = [
        {"kind": "dor", "summary": "relatorio de comissoes toma muito tempo"},
        {"kind": "desejo", "summary": "queria renovar apolices em lote"},
        {"kind": "risco_churn", "summary": "pensando em cancelar"},
    ]
    p = sug.compose_prompt("Resulta Seguros", insights, 82.0)
    check("prompt: 3 blocos exigidos (oportunidade/alerta/pergunta)",
          "Oportunidade" in p["system"] and "Alerta" in p["system"] and "Pergunta" in p["system"])
    check("prompt: dores e desejos do Garimpo entram no contexto",
          "comissoes" in p["user"] and "renovar" in p["user"] and "cancelar" in p["user"])
    check("prompt: nota media incluida", "82/100" in p["user"], p["user"][-80:])
    check("prompt: proibido inventar numeros", "NUNCA invente" in p["system"])
    p2 = sug.compose_prompt("X", [], None)
    check("prompt: sem dados -> contexto honesto", "Sem dados" in p2["user"])

    check("fallback deterministico tem a pergunta aberta das 3 coisas",
          "3 coisas" in sug.FALLBACK_TEXT)
    wk = sug.week_key(datetime(2026, 7, 13, tzinfo=timezone.utc))
    check("marcador semanal estavel (ISO week)", wk == "2026-W29", wk)

    src = (ROOT / "app/tasks/buffer_processor.py").read_text(encoding="utf-8")
    check("task registrada no scheduler", "sugestoes_check" in src and "check_suggestions" in src)
    sug_src = (ROOT / "app/services/proactive_suggestions.py").read_text(encoding="utf-8")
    check("registro SEMPRE em broker_insights (painel admin), mesmo sem canal",
          "sugestao_enviada" in sug_src)
    check("janela: segunda em horario comercial", "weekday() != 0" in sug_src)

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  FALHOU: {n} -> {d}")
        sys.exit(1)


if __name__ == "__main__":
    run()
