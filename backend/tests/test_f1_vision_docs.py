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

    # 🔴 VERDADE ATUALIZADA em 23/09/2026 (SPEC-116 U8, CLAUDE.md §9.3): o
    # `resolve_vision_model` com default `gpt-4o-mini` (e fallback para um Claude
    # RETIRADO) saiu — a visão pede o PAPEL `visao` à fábrica e a ROTA decide.
    # A lição "nunca cego" migrou para o MOTOR, com mutação:
    # `test_spec116_f3a_o_segurado_pede_papel.py` (G-VIS-1 e G-VIS-2).
    check("F1: o default literal de visão não existe mais",
          not hasattr(vs, "resolve_vision_model") and hasattr(vs, "criar_llm_de_visao"))
    check("F1: a marca do contexto visual reconhece a descrição do webhook",
          vs.imagem_ja_descrita("oi\n\n[CONTEXTO VISUAL — imagem enviada pelo cliente]:\nx") is True)
    check("F1: CONTROLE — texto sem a marca não conta como descrito",
          vs.imagem_ja_descrita("o que tem nessa imagem?") is False and vs.imagem_ja_descrita(None) is False)

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
