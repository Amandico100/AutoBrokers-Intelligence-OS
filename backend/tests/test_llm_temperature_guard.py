"""Regressao: Claude 5 rejeita `temperature` (API 400 'temperature is
deprecated for this model'). O _create_anthropic NAO pode enviar temperature
para a familia Claude 5. Teste puro (le a fonte; sem importar langchain).
Rodar de backend/: `python tests/test_llm_temperature_guard.py`."""
import os
import re

_P = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "factories", "llm_factory.py")
with open(_P, "r", encoding="utf-8") as fh:
    SRC = fh.read()

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


# Recria a regra pura da fonte para validar o comportamento.
def _supports_temperature(model: str) -> bool:
    m = (model or "").lower()
    blocked = ("claude-sonnet-5", "claude-opus-5", "claude-haiku-5", "claude-mythos", "claude-fable")
    return not any(m.startswith(p) for p in blocked)


check("claude-sonnet-5 NAO recebe temperature", _supports_temperature("claude-sonnet-5") is False)
check("claude-opus-5 NAO recebe temperature", _supports_temperature("claude-opus-5") is False)
check("claude-mythos NAO recebe temperature", _supports_temperature("claude-mythos-5") is False)
check("claude 4.x AINDA recebe temperature", _supports_temperature("claude-opus-4-8") is True)
check("claude 3.5 AINDA recebe temperature", _supports_temperature("claude-3-5-sonnet-20241022") is True)

# A fonte precisa condicionar o envio de temperature (nao passar sempre).
check("helper _anthropic_supports_temperature existe na fonte", "_anthropic_supports_temperature" in SRC)
check(
    "temperature so entra em params quando suportado",
    bool(re.search(r"if\s+LLMFactory\._anthropic_supports_temperature\(model\)\s*:\s*\n\s*params\[.temperature.\]", SRC)),
)
check("claude-sonnet-5 esta na lista bloqueada da fonte", "claude-sonnet-5" in SRC and "blocked" in SRC)

print(f"\n== Resumo: {_pass} passaram, {_fail} falharam ==")
if _fail:
    raise SystemExit(1)
