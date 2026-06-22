"""SPEC-013 P0 — runtime do Chat Principal por papel (puro, sem deps externas).
Rodar de dentro de backend/: `python tests/test_core_prompts.py`."""
import importlib.util
import os
import sys
import types

# pytz pode não estar instalado no ambiente de teste; stub mínimo (timezone→None = naive).
sys.modules.setdefault("pytz", types.SimpleNamespace(timezone=lambda *a, **k: None))

# Carrega prompts.py DIRETO por caminho (evita app/core/__init__ que puxa pydantic).
_PROMPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "core", "prompts.py")
_spec = importlib.util.spec_from_file_location("ab_prompts", _PROMPTS)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
build_composite_prompt = _mod.build_composite_prompt
_select_base_prompt = _mod._select_base_prompt
CORE_BASE_PROMPT = _mod.CORE_BASE_PROMPT
ATTENDANCE_BASE_PROMPT = _mod.ATTENDANCE_BASE_PROMPT

_pass = 0
_fail = 0


def check(name, cond):
    global _pass, _fail
    if cond:
        _pass += 1
        print(f"  ok  {name}")
    else:
        _fail += 1
        print(f"  XX  {name}")


# seleção por papel
check("core seleciona base Core", _select_base_prompt("core") is CORE_BASE_PROMPT)
check("legado/sem papel = Core", _select_base_prompt(None) is CORE_BASE_PROMPT and _select_base_prompt("") is CORE_BASE_PROMPT)
check("attendance seleciona base Atendimento", _select_base_prompt("attendance") is ATTENDANCE_BASE_PROMPT)
check("insured_external = Atendimento", _select_base_prompt("insured_external") is ATTENDANCE_BASE_PROMPT)

core = build_composite_prompt("Tom: objetivo.", agent_role="core")
att = build_composite_prompt("Você é a Even.", agent_role="attendance")

# Core inteligente, NÃO rag-only
check("Core NÃO tem regra RAG-only legada", "ESTRITAMENTE nos documentos" not in core and "Se não estiver no texto recuperado, não existe" not in core)
check("Core permite conhecimento geral (cita Roma/Itália)", "Itália" in core or "Roma" in core)
check("Core é copiloto interno", "copiloto interno" in core)
check("Core mantém guardrail de cobertura", "cobertura" in core)
check("Core inclui instruções do cliente", "Tom: objetivo." in core)

# Atendimento evidence-first
check("Attendance é evidence-first (cobertura sem evidência)", "sem evidência" in att)
check("Attendance NÃO usa base Core", "copiloto interno" not in att)
check("Attendance inclui instruções do cliente", "Você é a Even." in att)

# legado (sem role) é Core inteligente
legacy = build_composite_prompt("x")
check("legado é Core inteligente", "copiloto interno" in legacy and "ESTRITAMENTE nos documentos" not in legacy)

print(f"\n== Resumo: {_pass} passaram, {_fail} falharam ==")
sys.exit(1 if _fail else 0)
