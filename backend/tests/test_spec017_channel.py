"""SPEC-017 P1 - Canal WhatsApp (seam multi-provider transplantado do V7).

Rodar:
    python backend/tests/test_spec017_channel.py

Offline: sem rede, sem provider real, sem credencial. Valida o contrato do
seam: registry resolve Evolution/Z-API/uazapi, instância POR TENANT (nunca
singleton — evita vazamento de credencial entre corretoras), rótulo
desconhecido falha alto (sem fallback silencioso), e o pacote legado continua
importável (compatibilidade até a paridade P2).
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


def _load(dotted, rel):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(dotted, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = mod
    spec.loader.exec_module(mod)
    return mod


def _bootstrap():
    # Stubs mínimos: requests (providers usam requests.post) e pacotes app.*
    sys.modules.setdefault("requests", types.SimpleNamespace(
        post=lambda *a, **k: None, get=lambda *a, **k: None,
        Session=object, RequestException=Exception, Timeout=Exception,
        exceptions=types.SimpleNamespace(RequestException=Exception, Timeout=Exception),
    ))
    for name in ("app", "app.services", "app.services.whatsapp", "app.services.whatsapp.providers", "app.core"):
        module = sys.modules.setdefault(name, types.ModuleType(name))
        module.__path__ = []
    _load("app.services.whatsapp.exceptions", "app/services/whatsapp/exceptions.py")
    _load("app.services.whatsapp.models", "app/services/whatsapp/models.py")
    _load("app.services.whatsapp.providers.base", "app/services/whatsapp/providers/base.py")
    _load("app.services.whatsapp.providers.zapi", "app/services/whatsapp/providers/zapi.py")
    _load("app.services.whatsapp.providers.uazapi", "app/services/whatsapp/providers/uazapi.py")
    _load("app.services.whatsapp.providers.evolution", "app/services/whatsapp/providers/evolution.py")
    return _load("app.services.whatsapp.registry", "app/services/whatsapp/registry.py")


def run():
    print("== SPEC-017 P1 - seam WhatsApp multi-provider ==\n")
    try:
        registry = _bootstrap()
    except FileNotFoundError as exc:
        check("P1: pacote whatsapp v2 (V7 seam) presente", False, str(exc))
        print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
        sys.exit(1)

    def integration(provider):
        # Contrato real dos providers: Evolution exige base_url+instance_id+token;
        # Z-API exige instance_id+token; uazapi exige base_url+token.
        return {
            "provider": provider,
            "base_url": "https://evolution.interno.local",
            "instance_id": "inst-sintetica",
            "token": "tok-sintetico",
            "client_token": "ct-sintetico",
        }

    # Canonical set + alias
    for label, cls_name in (("evolution", "EvolutionProvider"), ("evolution-api", "EvolutionProvider"), ("z-api", "ZapiProvider"), ("uazapi", "UazapiProvider")):
        try:
            provider = registry.resolve_provider(integration(label))
            check(f"P1: '{label}' resolve para {cls_name}", type(provider).__name__ == cls_name, type(provider).__name__)
        except Exception as exc:  # noqa: BLE001
            check(f"P1: '{label}' resolve para {cls_name}", False, f"{type(exc).__name__}: {exc}")

    # Instância POR TENANT (nunca singleton)
    p1 = registry.resolve_provider(integration("evolution"))
    p2 = registry.resolve_provider(integration("evolution"))
    check("P1: instância nova por chamada (sem singleton cross-tenant)", p1 is not p2)

    # Rótulo desconhecido falha alto (sem fallback p/ Z-API)
    for bad in ("meta", "whatsapp-cloud", "wppconnect", "", None):
        try:
            registry.resolve_provider(integration(bad))
            check(f"P1: rótulo '{bad}' rejeitado", False, "não levantou erro")
        except Exception as exc:  # noqa: BLE001
            check(f"P1: rótulo '{bad}' rejeitado", "UnknownProvider" in type(exc).__name__ or "Whatsapp" in type(exc).__name__, type(exc).__name__)

    # Normalização de casing/espaços
    provider = registry.resolve_provider(integration("  Evolution  "))
    check("P1: normalização de casing/espaço", type(provider).__name__ == "EvolutionProvider")

    # Compat legado: submódulos antigos continuam existindo até a paridade P2.
    for legacy in ("integration_secrets.py", "zapi_provider.py"):
        check(f"P1: legado {legacy} preservado até paridade", (ROOT / "app/services/whatsapp" / legacy).exists())

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        sys.exit(1)


if __name__ == "__main__":
    run()
