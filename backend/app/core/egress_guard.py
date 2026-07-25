"""HTTP Egress Guard — SPEC-054 Bloco C.

Toda saída HTTP iniciada por ferramenta do agente passa por aqui.

O problema que isto resolve: a HTTP tool dinâmica aceitava qualquer URL vinda
do cadastro e chamava `httpx` direto. Sem allowlist de host, sem bloqueio de
loopback, de rede privada ou do endpoint de metadata da cloud, sem revalidação
de redirect e sem limite real de resposta. Um agente induzido por prompt
injection — ou um cadastro errado — conseguiria ler credenciais de instância
(`169.254.169.254`), varrer a rede interna ou puxar um arquivo gigante.

Não existe HTTP tool cadastrada hoje. O risco estava dormente. Este módulo o
fecha ANTES do primeiro cadastro, que é o momento barato de fazer isso.

Design:
  - módulo puro o suficiente para ser testado offline (a resolução DNS é
    injetável);
  - falha FECHADA: dúvida bloqueia;
  - decisão separada da execução, para que a política seja auditável.
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Política
# ---------------------------------------------------------------------------

ALLOWED_SCHEMES = frozenset({"https"})

# http só é tolerado para host explicitamente allowlistado (integração interna
# legada). Nunca por padrão.
TOLERATED_PLAINTEXT_SCHEMES = frozenset({"http"})

ALLOWED_PORTS = frozenset({80, 443, 8443})

MAX_REDIRECTS = 3
MAX_RESPONSE_BYTES = 5 * 1024 * 1024  # 5 MB
CONNECT_TIMEOUT_S = 5.0
READ_TIMEOUT_S = 20.0
TOTAL_TIMEOUT_S = 30.0

ALLOWED_CONTENT_TYPE_PREFIXES = (
    "application/json",
    "application/xml",
    "application/pdf",
    "text/plain",
    "text/csv",
    "text/xml",
    "text/html",
)

# Endpoints de metadata de cloud — leitura destes vaza credencial de instância.
CLOUD_METADATA_HOSTS = frozenset(
    {
        "169.254.169.254",
        "metadata.google.internal",
        "metadata.goog",
        "instance-data",
        "100.100.100.100",
    }
)

# Cabeçalhos que nunca podem ir para o log.
SENSITIVE_HEADER_NAMES = frozenset(
    {"authorization", "proxy-authorization", "cookie", "set-cookie", "x-api-key", "api-key", "token"}
)


class EgressBlocked(Exception):
    """Bloqueio de política. A mensagem é segura para log — não contém segredo."""

    def __init__(self, reason: str, detail: str = ""):
        self.reason = reason
        self.detail = detail
        super().__init__(f"egress_blocked:{reason}" + (f" ({detail})" if detail else ""))


@dataclass(frozen=True)
class EgressPolicy:
    """Política de uma tool/connector específico.

    `allowed_hosts` vazio significa DENY ALL — a ausência de allowlist não
    libera a internet inteira. Foi essa a decisão da SPEC-054 §9.1.
    """

    allowed_hosts: frozenset[str] = field(default_factory=frozenset)
    allow_subdomains: bool = True
    allow_plaintext_http: bool = False
    allowed_ports: frozenset[int] = ALLOWED_PORTS
    max_response_bytes: int = MAX_RESPONSE_BYTES

    @staticmethod
    def from_iterable(hosts: Optional[Iterable[str]], **kwargs) -> "EgressPolicy":
        normalized = frozenset((h or "").strip().lower().lstrip(".") for h in (hosts or []) if (h or "").strip())
        return EgressPolicy(allowed_hosts=normalized, **kwargs)


# ---------------------------------------------------------------------------
# Verificações
# ---------------------------------------------------------------------------


def _is_forbidden_ip(ip: ipaddress._BaseAddress) -> Optional[str]:
    """Retorna o motivo do bloqueio, ou None se o IP for aceitável."""
    if ip.is_loopback:
        return "loopback"
    if ip.is_private:
        return "rede_privada"
    if ip.is_link_local:
        return "link_local"
    if ip.is_reserved:
        return "reservado"
    if ip.is_multicast:
        return "multicast"
    if ip.is_unspecified:
        return "nao_especificado"
    # IPv4 mapeado em IPv6 (::ffff:127.0.0.1) contorna as checagens acima
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None:
            return _is_forbidden_ip(ip.ipv4_mapped) or None
        if ip.sixtofour is not None:
            return _is_forbidden_ip(ip.sixtofour) or None
    return None


def _host_allowed(host: str, policy: EgressPolicy) -> bool:
    if not policy.allowed_hosts:
        return False  # deny by default
    host = host.lower().rstrip(".")
    if host in policy.allowed_hosts:
        return True
    if policy.allow_subdomains:
        return any(host.endswith("." + allowed) for allowed in policy.allowed_hosts)
    return False


def _default_resolver(host: str) -> list[str]:
    infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    return [info[4][0] for info in infos]


@dataclass(frozen=True)
class EgressDecision:
    url: str
    host: str
    port: int
    resolved_ips: tuple[str, ...]


def check_url(
    url: str,
    policy: EgressPolicy,
    resolver: Callable[[str], list[str]] = _default_resolver,
) -> EgressDecision:
    """Valida uma URL contra a política. Levanta `EgressBlocked` ao recusar.

    A resolução DNS acontece AQUI e o resultado é devolvido, para que o
    chamador possa conectar no IP já validado. Sem isso, um servidor
    malicioso pode responder um IP público na checagem e um IP interno na
    conexão seguinte — DNS rebinding.
    """
    if not url or not isinstance(url, str):
        raise EgressBlocked("url_invalida")

    parsed = urlparse(url.strip())
    scheme = (parsed.scheme or "").lower()

    if scheme in TOLERATED_PLAINTEXT_SCHEMES:
        if not policy.allow_plaintext_http:
            raise EgressBlocked("http_sem_tls")
    elif scheme not in ALLOWED_SCHEMES:
        raise EgressBlocked("esquema_nao_permitido", scheme or "(vazio)")

    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        raise EgressBlocked("host_ausente")

    if host in CLOUD_METADATA_HOSTS:
        raise EgressBlocked("metadata_cloud", host)

    if parsed.username or parsed.password:
        raise EgressBlocked("credencial_embutida_na_url")

    port = parsed.port or (443 if scheme == "https" else 80)
    if port not in policy.allowed_ports:
        raise EgressBlocked("porta_nao_permitida", str(port))

    if not _host_allowed(host, policy):
        raise EgressBlocked("host_fora_da_allowlist", host)

    # Host literal em IP: valida direto.
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None

    if literal is not None:
        motivo = _is_forbidden_ip(literal)
        if motivo:
            raise EgressBlocked("ip_bloqueado", motivo)
        return EgressDecision(url=url, host=host, port=port, resolved_ips=(host,))

    try:
        ips = resolver(host)
    except Exception as exc:  # noqa: BLE001
        raise EgressBlocked("dns_falhou", type(exc).__name__) from exc

    if not ips:
        raise EgressBlocked("dns_sem_resposta", host)

    for raw in ips:
        try:
            ip = ipaddress.ip_address(raw)
        except ValueError:
            raise EgressBlocked("ip_invalido")
        motivo = _is_forbidden_ip(ip)
        if motivo:
            # UM endereço proibido já basta: um host pode resolver para
            # público e interno ao mesmo tempo.
            raise EgressBlocked("ip_bloqueado", motivo)

    return EgressDecision(url=url, host=host, port=port, resolved_ips=tuple(ips))


def check_redirect(location: str, previous: EgressDecision, policy: EgressPolicy,
                   resolver: Callable[[str], list[str]] = _default_resolver) -> EgressDecision:
    """Todo redirect é revalidado do zero. Redirect é a rota clássica de SSRF."""
    if location.startswith("/"):
        location = f"https://{previous.host}{location}"
    return check_url(location, policy, resolver)


def content_type_allowed(content_type: Optional[str]) -> bool:
    if not content_type:
        return False
    normalized = content_type.split(";")[0].strip().lower()
    return any(normalized.startswith(prefix) for prefix in ALLOWED_CONTENT_TYPE_PREFIXES)


def redact_headers(headers: Optional[dict]) -> dict:
    """Cabeçalhos seguros para log. Segredo vira marcador de presença."""
    if not headers:
        return {}
    return {
        k: ("<redigido>" if k.lower() in SENSITIVE_HEADER_NAMES else v)
        for k, v in headers.items()
    }


def safe_log_url(url: str) -> str:
    """URL sem querystring — token em query é comum e não pode ir para o log."""
    try:
        p = urlparse(url)
        return f"{p.scheme}://{p.hostname}{p.path}"
    except Exception:  # noqa: BLE001
        return "<url_ilegivel>"
