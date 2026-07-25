"""SPEC-054 Bloco C — testes de comportamento do HTTP Egress Guard.

Estes testes exercitam a POLÍTICA de verdade, com resolver injetado. Não são
inspeção de fonte: se o guard parar de bloquear, o teste quebra.

Rodar:  python backend/tests/test_spec054_egress_guard.py
"""

import importlib.util
import os
import sys

# Carrega o módulo POR CAMINHO, sem passar pelo pacote `app.core`.
# O guard é puro de propósito: um teste de segurança precisa rodar offline,
# sem exigir pydantic, Supabase ou qualquer dependência de runtime.
_GUARD_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "app", "core", "egress_guard.py"
)
_spec = importlib.util.spec_from_file_location("egress_guard_isolated", _GUARD_PATH)
_guard = importlib.util.module_from_spec(_spec)
# @dataclass precisa do módulo registrado em sys.modules para resolver tipos
sys.modules["egress_guard_isolated"] = _guard
_spec.loader.exec_module(_guard)

EgressBlocked = _guard.EgressBlocked
EgressPolicy = _guard.EgressPolicy
check_url = _guard.check_url
content_type_allowed = _guard.content_type_allowed
redact_headers = _guard.redact_headers
safe_log_url = _guard.safe_log_url

FALHAS: list[str] = []


def _resolver(mapping):
    def resolve(host):
        if host not in mapping:
            raise OSError(f"nao resolve: {host}")
        return mapping[host]

    return resolve


def bloqueia(nome, url, policy, resolver, motivo_esperado=None):
    try:
        check_url(url, policy, resolver)
    except EgressBlocked as e:
        if motivo_esperado and e.reason != motivo_esperado:
            FALHAS.append(f"{nome}: bloqueou por '{e.reason}', esperado '{motivo_esperado}'")
        else:
            print(f"  OK  {nome}  -> bloqueado ({e.reason})")
        return
    FALHAS.append(f"{nome}: NAO BLOQUEOU (falha de seguranca)")


def permite(nome, url, policy, resolver):
    try:
        check_url(url, policy, resolver)
        print(f"  OK  {nome}  -> permitido")
    except EgressBlocked as e:
        FALHAS.append(f"{nome}: bloqueou indevidamente ({e.reason})")


def main():
    print("SPEC-054 — HTTP Egress Guard")

    publico = _resolver({"api.exemplo.com": ["93.184.216.34"], "sub.api.exemplo.com": ["93.184.216.34"]})
    pol = EgressPolicy.from_iterable(["api.exemplo.com"])

    print("\n[1] Caminho legitimo")
    permite("https em host allowlistado", "https://api.exemplo.com/v1/x", pol, publico)
    permite("subdominio permitido", "https://sub.api.exemplo.com/x", pol, publico)

    print("\n[2] SSRF - destinos proibidos")
    bloqueia("loopback IPv4", "https://api.exemplo.com/", pol,
             _resolver({"api.exemplo.com": ["127.0.0.1"]}), "ip_bloqueado")
    bloqueia("loopback IPv6", "https://api.exemplo.com/", pol,
             _resolver({"api.exemplo.com": ["::1"]}), "ip_bloqueado")
    bloqueia("rede privada 10/8", "https://api.exemplo.com/", pol,
             _resolver({"api.exemplo.com": ["10.1.2.3"]}), "ip_bloqueado")
    bloqueia("rede privada 192.168", "https://api.exemplo.com/", pol,
             _resolver({"api.exemplo.com": ["192.168.0.7"]}), "ip_bloqueado")
    bloqueia("link-local 169.254", "https://api.exemplo.com/", pol,
             _resolver({"api.exemplo.com": ["169.254.169.254"]}), "ip_bloqueado")
    bloqueia("IPv4 mapeado em IPv6", "https://api.exemplo.com/", pol,
             _resolver({"api.exemplo.com": ["::ffff:127.0.0.1"]}), "ip_bloqueado")
    bloqueia("metadata cloud por hostname",
             "https://metadata.google.internal/computeMetadata/v1/",
             EgressPolicy.from_iterable(["metadata.google.internal"]), publico, "metadata_cloud")
    bloqueia("metadata cloud por IP literal", "https://169.254.169.254/latest/meta-data/",
             EgressPolicy.from_iterable(["169.254.169.254"]), publico, "metadata_cloud")

    print("\n[3] DNS rebinding - um IP interno entre publicos ja basta")
    bloqueia("resposta mista publico+interno", "https://api.exemplo.com/", pol,
             _resolver({"api.exemplo.com": ["93.184.216.34", "10.0.0.5"]}), "ip_bloqueado")

    print("\n[4] Allowlist")
    bloqueia("host fora da allowlist", "https://evil.com/", pol,
             _resolver({"evil.com": ["93.184.216.34"]}), "host_fora_da_allowlist")
    bloqueia("allowlist VAZIA nega tudo", "https://api.exemplo.com/",
             EgressPolicy(), publico, "host_fora_da_allowlist")
    bloqueia("sufixo enganoso (naoapi.exemplo.com.evil.com)",
             "https://api.exemplo.com.evil.com/", pol,
             _resolver({"api.exemplo.com.evil.com": ["93.184.216.34"]}), "host_fora_da_allowlist")

    print("\n[5] Esquema, porta e credencial")
    bloqueia("http sem TLS", "http://api.exemplo.com/", pol, publico, "http_sem_tls")
    bloqueia("file://", "file:///etc/passwd", pol, publico, "esquema_nao_permitido")
    bloqueia("gopher://", "gopher://api.exemplo.com/", pol, publico, "esquema_nao_permitido")
    bloqueia("porta nao permitida", "https://api.exemplo.com:22/", pol, publico, "porta_nao_permitida")
    bloqueia("credencial embutida", "https://user:senha@api.exemplo.com/", pol, publico,
             "credencial_embutida_na_url")
    permite("http tolerado quando explicitamente liberado", "http://api.exemplo.com/",
            EgressPolicy.from_iterable(["api.exemplo.com"], allow_plaintext_http=True), publico)

    print("\n[6] Content-type")
    for ct, esperado in [("application/json", True), ("text/plain; charset=utf-8", True),
                         ("application/pdf", True), ("application/octet-stream", False),
                         ("image/svg+xml", False), (None, False)]:
        obtido = content_type_allowed(ct)
        if obtido != esperado:
            FALHAS.append(f"content_type_allowed({ct!r}) = {obtido}, esperado {esperado}")
        else:
            print(f"  OK  content-type {ct!r} -> {obtido}")

    print("\n[7] Nao vazar segredo em log")
    red = redact_headers({"Authorization": "Bearer supersecreto", "X-Api-Key": "k123", "Accept": "application/json"})
    if red.get("Authorization") != "<redigido>" or red.get("X-Api-Key") != "<redigido>":
        FALHAS.append("redact_headers nao redigiu cabecalho sensivel")
    elif red.get("Accept") != "application/json":
        FALHAS.append("redact_headers redigiu cabecalho inofensivo")
    else:
        print("  OK  cabecalhos sensiveis redigidos, inofensivos preservados")

    logado = safe_log_url("https://api.exemplo.com/v1/x?token=segredo123")
    if "segredo123" in logado or "token" in logado:
        FALHAS.append("safe_log_url vazou querystring")
    else:
        print(f"  OK  querystring removida do log -> {logado}")

    print("\n" + "=" * 60)
    if FALHAS:
        print(f"FALHAS: {len(FALHAS)}")
        for f in FALHAS:
            print(f"  X  {f}")
        return 1
    print("TODOS OS TESTES PASSARAM")
    return 0


if __name__ == "__main__":
    sys.exit(main())
