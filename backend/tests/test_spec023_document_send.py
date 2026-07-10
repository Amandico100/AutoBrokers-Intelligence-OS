"""SPEC-023 P4 - boleto como DOCUMENTO PDF no WhatsApp (seam multi-provider).

Rodar: python backend/tests/test_spec023_document_send.py
Testa payloads puros dos providers (sem rede: _post capturado) + nome do arquivo
sem PII + contrato do OutboundMedia com kind=document.
"""

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # backend/
sys.path.insert(0, str(ROOT))

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


import importlib.util


def _load(dotted, rel):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(dotted, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = mod
    spec.loader.exec_module(mod)
    return mod


# Bootstrap isolado (padrão house): stubs de requests/httpx + pacotes app.* sem
# executar app/services/__init__.py (que puxa openai etc.).
sys.modules.setdefault("requests", types.SimpleNamespace(
    post=lambda *a, **k: None, get=lambda *a, **k: None,
    Session=object, RequestException=Exception, Timeout=Exception,
    exceptions=types.SimpleNamespace(RequestException=Exception, Timeout=Exception),
))
sys.modules.setdefault("httpx", types.ModuleType("httpx"))
for name in ("app", "app.services", "app.services.whatsapp", "app.services.whatsapp.providers", "app.core"):
    module = sys.modules.setdefault(name, types.ModuleType(name))
    module.__path__ = []
_load("app.services.whatsapp.exceptions", "app/services/whatsapp/exceptions.py")
models_mod = _load("app.services.whatsapp.models", "app/services/whatsapp/models.py")
_load("app.services.whatsapp.providers.base", "app/services/whatsapp/providers/base.py")
zapi_mod = _load("app.services.whatsapp.providers.zapi", "app/services/whatsapp/providers/zapi.py")
uazapi_mod = _load("app.services.whatsapp.providers.uazapi", "app/services/whatsapp/providers/uazapi.py")
evolution_mod = _load("app.services.whatsapp.providers.evolution", "app/services/whatsapp/providers/evolution.py")
billing_mod = _load("app.services.billing_collection", "app/services/billing_collection.py")

OutboundMedia = models_mod.OutboundMedia
SendResult = models_mod.SendResult
EvolutionProvider = evolution_mod.EvolutionProvider
UazapiProvider = uazapi_mod.UazapiProvider
ZapiProvider = zapi_mod.ZapiProvider
boleto_document_name = billing_mod.boleto_document_name


def _capture_post(provider):
    calls = []

    def fake_post(url, payload):
        calls.append({"url": url, "payload": payload})
        return SendResult(ok=True)

    provider._post = fake_post
    return calls


def run():
    print("== SPEC-023 P4 - documento PDF no WhatsApp ==\n")

    media = OutboundMedia(
        kind="document",
        url="https://storage.example/signed/boleto.pdf",
        mime_type="application/pdf",
        filename="boleto-317418783.pdf",
    )
    check("OutboundMedia aceita kind=document", media.kind == "document")
    check("OutboundMedia carrega filename", media.filename == "boleto-317418783.pdf")

    # Evolution: sendMedia com mediatype document + fileName
    evo = EvolutionProvider({"base_url": "https://evo.test", "instance_id": "inst1", "token": "tok"})
    evo_calls = _capture_post(evo)
    res = evo.send_media("5547999999999", media)
    check("evolution document -> ok", res.ok is True)
    check("evolution usa endpoint sendMedia", "message/sendMedia/inst1" in evo_calls[0]["url"], evo_calls)
    check("evolution mediatype=document", evo_calls[0]["payload"].get("mediatype") == "document", evo_calls)
    check("evolution manda fileName", evo_calls[0]["payload"].get("fileName") == "boleto-317418783.pdf", evo_calls)
    check("evolution manda mimetype pdf", evo_calls[0]["payload"].get("mimetype") == "application/pdf", evo_calls)

    # uazapi: send/media type=document + docName
    ua = UazapiProvider({"base_url": "https://ua.test", "token": "tok"})
    ua_calls = _capture_post(ua)
    res = ua.send_media("5547999999999", media)
    check("uazapi document -> ok", res.ok is True)
    check("uazapi type=document", ua_calls[0]["payload"].get("type") == "document", ua_calls)
    check("uazapi manda docName", ua_calls[0]["payload"].get("docName") == "boleto-317418783.pdf", ua_calls)

    # z-api: rota send-document/{ext} + fileName
    za = ZapiProvider({"base_url": "https://za.test", "instance_id": "i1", "token": "t1"})
    za_calls = _capture_post(za)
    res = za.send_media("5547999999999", media)
    check("zapi document -> ok", res.ok is True)
    check("zapi rota send-document/pdf", za_calls[0]["url"].endswith("/send-document/pdf"), za_calls)
    check("zapi manda fileName", za_calls[0]["payload"].get("fileName") == "boleto-317418783.pdf", za_calls)

    # imagem continua intacta no evolution (regressão)
    img = OutboundMedia(kind="image", url="https://x.test/i.png", caption="oi")
    res = evo.send_media("5547999999999", img)
    check("evolution imagem segue ok", res.ok is True)
    check("evolution imagem mediatype=image", evo_calls[-1]["payload"].get("mediatype") == "image", evo_calls)

    # nome do arquivo do boleto: recibo sim, PII nao
    name = boleto_document_name({"recibo": "317418783", "cliente_nome": "MONICA B", "cpf_cnpj": "03184509923"})
    check("nome do boleto usa recibo", name == "boleto-317418783.pdf", name)
    check("nome do boleto sem nome do cliente", "MONICA" not in name.upper(), name)
    check("nome do boleto sem CPF", "03184509923" not in name, name)
    check("sem recibo -> nome generico", boleto_document_name({}) == "boleto.pdf")

    print(f"\nPASS={PASS} FAIL={FAIL}")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  FALHOU: {n} -> {d}")
        sys.exit(1)


if __name__ == "__main__":
    run()
