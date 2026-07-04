"""F1 - Visao e documentos GLOBAIS (chat, atendente, auxiliares).

Rodar: python backend/tests/test_f1_vision_docs.py
Offline: so as partes puras (selecao de modelo, truncamento). A chamada de
visao/parse real depende de rede e e coberta pelo teste manual do founder.
"""

import importlib.util
import os
import sys
import types
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


for name in ("app", "app.services"):
    m = sys.modules.setdefault(name, types.ModuleType(name))
    m.__path__ = []

spec = importlib.util.spec_from_file_location("app.services.vision_service", ROOT / "app/services/vision_service.py")
vs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vs)


def run():
    print("== F1 - visao/documentos globais ==\n")

    os.environ["OPENAI_API_KEY"] = "sk-teste"
    os.environ.pop("ANTHROPIC_API_KEY", None)

    m = vs.resolve_vision_model({"vision_model": "gpt-4o"})
    check("F1: vision_model do agente tem prioridade", m == ("gpt-4o", "sk-teste"), m)

    m2 = vs.resolve_vision_model({})
    check("F1: SEM vision_model -> default da plataforma (nunca cego)", m2 == ("gpt-4o-mini", "sk-teste"), m2)

    m3 = vs.resolve_vision_model(None)
    check("F1: agent_data None -> default da plataforma", m3 == ("gpt-4o-mini", "sk-teste"), m3)

    os.environ.pop("OPENAI_API_KEY", None)
    os.environ["ANTHROPIC_API_KEY"] = "ak-teste"
    m4 = vs.resolve_vision_model({})
    check("F1: sem OpenAI -> cai para Claude", m4 is not None and m4[0].startswith("claude") and m4[1] == "ak-teste", m4)

    os.environ.pop("ANTHROPIC_API_KEY", None)
    check("F1: sem nenhuma chave -> None (fail-safe)", vs.resolve_vision_model({}) is None)
    os.environ["OPENAI_API_KEY"] = "sk-teste"

    t = vs.truncate_document_text("x" * 25000, max_chars=20000)
    check("F1: documento gigante e truncado com aviso", len(t) < 20500 and "TRUNCADO" in t, len(t))
    check("F1: documento curto passa intacto", vs.truncate_document_text("ola") == "ola")
    check("F1: texto vazio -> vazio", vs.truncate_document_text("") == "")

    check("F1: extensao suportada", vs.is_supported_document("apolice.PDF") is True and vs.is_supported_document("planilha.docx") is True)
    check("F1: extensao nao suportada", vs.is_supported_document("virus.exe") is False and vs.is_supported_document("") is False)

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        sys.exit(1)


if __name__ == "__main__":
    run()
