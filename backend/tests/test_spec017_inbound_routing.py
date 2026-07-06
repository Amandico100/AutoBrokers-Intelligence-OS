"""SPEC-017 - Precedencia de conteudo inbound do WhatsApp.

Rodar: python backend/tests/test_spec017_inbound_routing.py

Regressao (bug de campo, founder 2026-07-05): imagem enviada COM legenda tinha a
legenda tratada como texto e o branch de imagem era pulado -> o atendente perdia
a imagem (final_image_url None, describe_image nunca rodava, image_url null no
banco). A imagem tem que vencer o texto/legenda.
"""

import importlib.util
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


for name in ("app", "app.services", "app.services.whatsapp"):
    m = sys.modules.setdefault(name, types.ModuleType(name))
    m.__path__ = []

spec = importlib.util.spec_from_file_location(
    "app.services.whatsapp.inbound_routing", ROOT / "app/services/whatsapp/inbound_routing.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
pick = mod.pick_inbound_branch


def run():
    print("== SPEC-017 - Precedencia inbound (imagem com legenda) ==\n")

    # O BUG: imagem COM legenda (has_text True) tem que cair no branch de imagem.
    check("imagem+legenda -> image (nao text)",
          pick(has_combined=False, has_audio=False, has_image=True, has_text=True) == "image")
    check("imagem sem legenda -> image",
          pick(has_combined=False, has_audio=False, has_image=True, has_text=False) == "image")
    check("texto puro -> text",
          pick(has_combined=False, has_audio=False, has_image=False, has_text=True) == "text")
    check("audio vence texto -> audio",
          pick(has_combined=False, has_audio=True, has_image=False, has_text=True) == "audio")
    # audio antes de image e comportamento historico (audio raramente vem com imagem).
    check("audio antes de image -> audio",
          pick(has_combined=False, has_audio=True, has_image=True, has_text=False) == "audio")
    check("buffer combinado vence tudo -> combined",
          pick(has_combined=True, has_audio=True, has_image=True, has_text=True) == "combined")
    check("nada -> none",
          pick(has_combined=False, has_audio=False, has_image=False, has_text=False) == "none")

    print(f"\n== {PASS} ok / {FAIL} fail ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  FALHOU: {n} ({d})")
    return FAIL == 0


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
