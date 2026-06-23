"""SPEC-013 FB-1 — política de modelo do Core (puro, offline).
Rodar de backend/: `python tests/test_model_policy.py`."""
import importlib.util
import os

_P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "factories", "model_policy.py")
_spec = importlib.util.spec_from_file_location("ab_model_policy", _P)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
resolve_chat_model = _mod.resolve_chat_model
is_core_chat_role = _mod.is_core_chat_role
DEFAULT_CORE_MODEL = _mod.DEFAULT_CORE_MODEL

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


os.environ.pop("CORE_CHAT_MODEL", None)  # usa default

check("core é chat principal", is_core_chat_role("core") and is_core_chat_role("") and is_core_chat_role(None))
check("attendance não é core", not is_core_chat_role("attendance"))

# Core econômico é promovido
check("core + mini -> modelo forte", resolve_chat_model("core", "gpt-4o-mini") == DEFAULT_CORE_MODEL)
check("legado/None + mini -> modelo forte", resolve_chat_model(None, "gpt-4o-mini") == DEFAULT_CORE_MODEL)
check("core sem modelo -> modelo forte", resolve_chat_model("core", None) == DEFAULT_CORE_MODEL)
# Core já forte não é rebaixado
check("core + gpt-4o mantém", resolve_chat_model("core", "gpt-4o") == "gpt-4o")
check("core + modelo custom mantém", resolve_chat_model("core", "gpt-4.1") == "gpt-4.1")
# Attendance/auxiliar mantêm o seu (não engessa, não promove)
check("attendance + mini mantém", resolve_chat_model("attendance", "gpt-4o-mini") == "gpt-4o-mini")
check("subagent + mini mantém", resolve_chat_model("subagent", "gpt-4o-mini") == "gpt-4o-mini")
# env override
os.environ["CORE_CHAT_MODEL"] = "gpt-4o-2024-11-20"
check("env CORE_CHAT_MODEL respeitado", resolve_chat_model("core", "gpt-4o-mini") == "gpt-4o-2024-11-20")
os.environ.pop("CORE_CHAT_MODEL", None)

print(f"\n== Resumo: {_pass} passaram, {_fail} falharam ==")
import sys
sys.exit(1 if _fail else 0)
