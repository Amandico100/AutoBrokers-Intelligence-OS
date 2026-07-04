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

    # ---------- P1.2: segurança do token de webhook (puro) ----------
    print("\n== P1.2 - token de webhook / dedup / provider match ==\n")
    sec = _load("app.services.whatsapp.channel_security", "app/services/whatsapp/channel_security.py")
    token, thash, tprefix = sec.new_webhook_credentials()
    check("P1.2: token gerado tem formato válido", sec.validate_webhook_token_format(token))
    check("P1.2: hash bate com o token (compare_digest)", sec.webhook_token_matches(token, thash))
    check("P1.2: token errado não bate", not sec.webhook_token_matches("x" * 32, thash))
    check("P1.2: prefixo curto p/ log (não sensível)", tprefix == token[:8] and len(tprefix) == 8)
    for bad in ("", None, "curto", "a" * 81, "tem espaço aqui!!" + "a" * 10):
        check(f"P1.2: formato inválido rejeitado ({str(bad)[:12]!r})", not sec.validate_webhook_token_format(bad))
    check("P1.2: dedup namespace z-api sem prefixo", sec.dedup_key("z-api", "M1") == "wa:dedup:M1")
    check("P1.2: dedup namespace evolution", sec.dedup_key("evolution", "M1") == "wa:dedup:evolution:M1")
    check("P1.2: sem messageId -> sem dedup", sec.dedup_key("evolution", None) is None)
    check("P1.2: provider do path deve bater com o da linha", sec.provider_matches_integration("evolution", "evolution") and not sec.provider_matches_integration("z-api", "evolution"))
    check("P1.2: alias evolution-api aceito", sec.provider_matches_integration("evolution-api", "evolution"))
    check("P1.2: linha legada sem provider = z-api", sec.provider_matches_integration("z-api", None))

    # ---------- P1.2: normalizador de inbound Evolution (puro) ----------
    print("\n== P1.2 - normalizador Evolution ==\n")
    evo = _load("app.services.whatsapp.evolution_inbound", "app/services/whatsapp/evolution_inbound.py")
    base = {
        "event": "messages.upsert",
        "instance": "corretora-sintetica",
        "data": {
            "key": {"remoteJid": "5547999990000@s.whatsapp.net", "fromMe": False, "id": "MSG-1"},
            "pushName": "Cliente Sintetico",
            "message": {"conversation": "preciso de um chaveiro"},
            "messageTimestamp": 1780000000,
        },
    }
    n = evo.normalize_evolution_inbound(base)
    check("P1.2: inbound texto simples normalizado", not n["skip"] and n["phone"] == "5547999990000" and n["text"] == "preciso de um chaveiro" and n["message_id"] == "MSG-1", n)
    ext = {**base, "data": {**base["data"], "message": {"extendedTextMessage": {"text": "oi, era só isso mesmo"}}}}
    check("P1.2: extendedTextMessage normalizado", evo.normalize_evolution_inbound(ext)["text"] == "oi, era só isso mesmo")
    fm = {**base, "data": {**base["data"], "key": {**base["data"]["key"], "fromMe": True}}}
    check("P1.2: fromMe é ignorado", evo.normalize_evolution_inbound(fm)["skip_reason"] == "from_me")
    grp = {**base, "data": {**base["data"], "key": {**base["data"]["key"], "remoteJid": "1203630@g.us"}}}
    check("P1.2: grupo é ignorado", evo.normalize_evolution_inbound(grp)["skip_reason"] == "group")
    other = {**base, "event": "connection.update"}
    check("P1.2: evento não-mensagem é ignorado", evo.normalize_evolution_inbound(other)["skip"])
    # Número pessoal do corretor: Status, canais e broadcast NUNCA chegam ao agente.
    st = {**base, "data": {**base["data"], "key": {**base["data"]["key"], "remoteJid": "status@broadcast"}}}
    check("P1.2: Status (status@broadcast) é ignorado", evo.normalize_evolution_inbound(st)["skip"])
    nl = {**base, "data": {**base["data"], "key": {**base["data"]["key"], "remoteJid": "120363123456789@newsletter"}}}
    check("P1.2: canal (@newsletter) é ignorado", evo.normalize_evolution_inbound(nl)["skip"])
    bc = {**base, "data": {**base["data"], "key": {**base["data"]["key"], "remoteJid": "5547999990000@broadcast"}}}
    check("P1.2: lista de transmissão (@broadcast) é ignorada", evo.normalize_evolution_inbound(bc)["skip"])
    lid = {**base, "data": {**base["data"], "key": {**base["data"]["key"], "remoteJid": "98765432101@lid"}}}
    check("P1.2: contato individual em @lid CONTINUA passando", not evo.normalize_evolution_inbound(lid)["skip"])

    # Allowlist de teste (número pessoal): só responde quem estiver liberado.
    check("ALLOW: sem allowlist configurada, todo mundo passa", sec.attendant_inbound_allowed("5547999990000", allowlist="") is True)
    check("ALLOW: numero na lista passa (formatos com +55/espacos)", sec.attendant_inbound_allowed("5547988087463", allowlist="+55 47 98808-7463, 5511911112222") is True)
    check("ALLOW: numero fora da lista e bloqueado", sec.attendant_inbound_allowed("5547900000001", allowlist="5547988087463") is False)
    check("ALLOW: allowlist None = env ausente = passa", sec.attendant_inbound_allowed("qualquer", allowlist=None) is True)
    # BR: WhatsApp entrega números SEM o nono dígito p/ muitas contas — a
    # allowlist tem que casar nas duas formas (com e sem o 9).
    check("ALLOW: inbound sem nono digito casa com lista com 9", sec.attendant_inbound_allowed("554788087463", allowlist="5547988087463") is True)
    check("ALLOW: inbound com nono digito casa com lista sem 9", sec.attendant_inbound_allowed("5547988087463", allowlist="554788087463") is True)
    check("ALLOW: numeros diferentes continuam bloqueados", sec.attendant_inbound_allowed("554791111111", allowlist="5547988087463") is False)
    check("P1.2: connection.update extrai estado", evo.connection_state_from_payload({"event": "connection.update", "data": {"state": "close"}}) == "close")

    # ---------- P2 (S17-9): divisor de balões humanizado (puro) ----------
    print("\n== P2 - divisor de balões ==\n")
    bal = _load("app.services.whatsapp.balloons", "app/services/whatsapp/balloons.py")
    check("P2: texto curto = 1 balão", bal.split_whatsapp_balloons("Oi! Posso ajudar?") == ["Oi! Posso ajudar?"])
    long_prose = ("Entendi perfeitamente a sua situação e vou te ajudar com isso agora. " * 8).strip()
    parts = bal.split_whatsapp_balloons(long_prose)
    check("P2: prosa longa vira 2+ balões <=500", len(parts) >= 2 and all(len(p) <= 500 for p in parts), [len(p) for p in parts])
    lista = "Segue o que preciso:\n\n- CPF do titular\n- Endereço com número\n- Telefone de contato\n- Melhor período (manhã/tarde)\n- Descrição do problema\n- Marca do aparelho\n- Idade aproximada\n- Já abriu chamado antes?\n- Tem alguém maior de 18 em casa?\n- Pode receber amanhã?"
    parts = bal.split_whatsapp_balloons(lista + "\n\n" + long_prose)
    list_balloon = next((p for p in parts if "CPF do titular" in p), "")
    check("P2: lista NUNCA é fatiada", "Pode receber amanhã?" in list_balloon, parts)
    check("P2: máximo 4 balões", len(bal.split_whatsapp_balloons(long_prose * 5)) <= 4)
    check("P2: vazio = sem balões", bal.split_whatsapp_balloons("") == [])

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        sys.exit(1)


if __name__ == "__main__":
    run()
