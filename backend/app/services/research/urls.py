"""Normalização e canonicalização de URL. SPEC-060 §13.4, §24.3, §24.5.

Parece detalhe e é a base de três coisas que não funcionam sem ele:

* **dedupe** — a mesma notícia chega por cinco caminhos com `utm_source`
  diferente. Sem normalizar, o sistema conta cinco fontes independentes para
  o mesmo fato, e a "verificação cruzada" vira uma ilusão perigosa: parece
  confirmado por muitos e é um release só, copiado.
* **cache** — chave de cache que muda com parâmetro de rastreamento nunca
  acerta, e o custo do provider volta a cada consulta.
* **identidade da fonte** — `research_sources` tem UNIQUE no fingerprint.

Puro. Sem rede, sem DNS, sem banco.
"""

from __future__ import annotations

import hashlib
import re
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# Parâmetros que identificam a CAMPANHA, não o conteúdo. Removê-los é o que
# faz a mesma página compartilhada por cinco canais virar uma fonte só.
PARAMETROS_DE_RASTREAMENTO = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "utm_id", "utm_source_platform", "utm_creative_format",
    "gclid", "gbraid", "wbraid", "fbclid", "msclkid", "dclid", "twclid",
    "igshid", "mc_cid", "mc_eid", "_ga", "_gl", "yclid", "ttclid",
    "ref", "referrer", "source", "spm", "at_medium", "at_campaign",
    "campaign_id", "ad_id", "adset_id", "cmpid", "s_kwcid",
}

# Fragmentos que servem para leitura humana, não para identificar o recurso.
FRAGMENTOS_IGNORADOS = ("#:~:text=", "#page=")

ESQUEMAS_PERMITIDOS = ("http", "https")

_WWW = re.compile(r"^www\d*\.")
_BARRAS = re.compile(r"/{2,}")


def normalizar(url: str, *, manter_fragmento: bool = False) -> Optional[str]:
    """URL canônica. `None` quando o endereço não serve para pesquisa.

    Devolver `None` em vez de levantar exceção é deliberado: URL inválida
    aparece o tempo todo em conteúdo web (link quebrado, `javascript:`,
    caminho relativo em página malformada) e não é um erro do sistema — é uma
    entrada que se descarta.
    """
    bruto = (url or "").strip()
    if not bruto:
        return None

    # Sem esquema, assume https. Muito link em texto vem como "site.com.br".
    if "://" not in bruto:
        if bruto.startswith("//"):
            bruto = "https:" + bruto
        elif re.match(r"^[\w.-]+\.[a-z]{2,}", bruto, re.I):
            bruto = "https://" + bruto
        else:
            return None

    try:
        partes = urlsplit(bruto)
    except Exception:  # noqa: BLE001
        return None

    esquema = (partes.scheme or "").lower()
    if esquema not in ESQUEMAS_PERMITIDOS:
        # `file:`, `javascript:`, `data:` — §38.3 exige que nunca virem fonte.
        return None

    # `http` e `https` da MESMA página são a mesma fonte. Manter os dois
    # esquemas faria a verificação cruzada contar duas — e "confirmado por
    # duas fontes" seria a mesma página duas vezes, que é justamente a ilusão
    # perigosa que §24.5 existe para impedir.
    #
    # Canonicalizar para `https` também é coerente com a política: §9.5 exige
    # TLS na leitura direta, então o endereço `http` nunca seria buscado assim
    # mesmo. O que muda aqui é só a IDENTIDADE da fonte.
    esquema = "https"

    host = (partes.hostname or "").lower().strip(".")
    if not host or "." not in host:
        return None
    host = _WWW.sub("", host)

    # Porta padrão não entra: `https://x.com:443/a` e `https://x.com/a` são o
    # mesmo recurso, e mantê-la criaria duas fontes.
    porta = partes.port
    if porta and not ((esquema == "https" and porta == 443)
                      or (esquema == "http" and porta == 80)):
        host = f"{host}:{porta}"

    caminho = _BARRAS.sub("/", partes.path or "/")
    if len(caminho) > 1 and caminho.endswith("/"):
        caminho = caminho.rstrip("/")
    if not caminho:
        caminho = "/"

    consulta = _limpar_consulta(partes.query)
    fragmento = ""
    if manter_fragmento and partes.fragment:
        if not any(partes.fragment.startswith(f.lstrip("#"))
                   for f in FRAGMENTOS_IGNORADOS):
            fragmento = partes.fragment

    return urlunsplit((esquema, host, caminho, consulta, fragmento))


def _limpar_consulta(query: str) -> str:
    """Remove rastreamento e ordena o resto. Ordenar torna a chave estável."""
    if not query:
        return ""
    try:
        pares = parse_qsl(query, keep_blank_values=True)
    except Exception:  # noqa: BLE001
        return ""
    mantidos = [(k, v) for k, v in pares
                if k.lower() not in PARAMETROS_DE_RASTREAMENTO]
    if not mantidos:
        return ""
    return urlencode(sorted(mantidos))


def dominio(url: str) -> str:
    """Domínio normalizado, sem `www`. Vazio quando a URL não serve."""
    canonica = normalizar(url)
    if not canonica:
        return ""
    return urlsplit(canonica).hostname or ""


def dominio_raiz(url: str) -> str:
    """Domínio registrável aproximado — `noticias.uol.com.br` → `uol.com.br`.

    Aproximação sem lista pública de sufixos: trata os compostos brasileiros
    que importam aqui (`.com.br`, `.gov.br`, `.org.br`…). Serve para agrupar
    fontes do mesmo publisher, não para decisão de segurança — o egress guard
    é quem decide o que pode ser acessado.
    """
    host = dominio(url)
    if not host:
        return ""
    partes = host.split(".")
    if len(partes) <= 2:
        return host
    compostos = {"com", "gov", "org", "net", "edu", "mil", "leg", "jus", "adv"}
    if len(partes) >= 3 and partes[-1] == "br" and partes[-2] in compostos:
        return ".".join(partes[-3:])
    return ".".join(partes[-2:])


def fingerprint(url: str) -> str:
    """Identidade estável da fonte. É o UNIQUE de `research_sources`."""
    canonica = normalizar(url) or (url or "").strip().lower()
    return hashlib.sha256(canonica.encode("utf-8")).hexdigest()[:40]


def mesma_fonte(a: str, b: str) -> bool:
    return fingerprint(a) == fingerprint(b)


def e_do_dominio(url: str, padrao: str) -> bool:
    """Casa URL com padrão de domínio (`*.gov.br`, `susep.gov.br`)."""
    host = dominio(url)
    if not host:
        return False
    alvo = (padrao or "").lower().lstrip("*.").strip()
    if not alvo:
        return False
    return host == alvo or host.endswith("." + alvo)


def deduplicar(urls: list[str]) -> list[str]:
    """Remove repetição preservando a ordem de chegada.

    A ordem importa: o primeiro resultado costuma ser o mais relevante do
    provider, e reordenar por acidente de `set()` degradaria a seleção.
    """
    vistos: set[str] = set()
    saida: list[str] = []
    for u in urls or []:
        canonica = normalizar(u)
        if not canonica:
            continue
        fp = fingerprint(canonica)
        if fp in vistos:
            continue
        vistos.add(fp)
        saida.append(canonica)
    return saida


def agrupar_por_publisher(urls: list[str]) -> dict[str, list[str]]:
    """§24.5 — cópias do mesmo release não são fontes independentes.

    Agrupar por publisher é o que permite contar "três veículos" em vez de
    "três URLs" quando os três republicaram a mesma nota.
    """
    grupos: dict[str, list[str]] = {}
    for u in deduplicar(urls):
        grupos.setdefault(dominio_raiz(u), []).append(u)
    return grupos


def diversidade(urls: list[str]) -> int:
    """Quantos publishers distintos. É o número que vale em §13.2."""
    return len(agrupar_por_publisher(urls))
