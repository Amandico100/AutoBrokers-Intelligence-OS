"""Leitura de sinais de marca em páginas públicas. SPEC-057 §Bloco A.

Dois caminhos, na ordem:

1. **Firecrawl**, quando há chave. Resolve JavaScript, o que importa porque
   parte dos sites de corretora é feita em construtor que monta o cabeçalho no
   cliente — e é no cabeçalho que mora o logo.
2. **Busca direta**, sempre disponível. Site de corretora costuma ser WordPress
   com HTML servido pronto; para esses, o HTML cru já traz tudo.

O segundo não é plano B envergonhado: é o que garante que a funcionalidade
exista mesmo sem chave configurada. Recurso que só funciona com integração
paga vira recurso que a maioria dos clientes nunca vê.

Segurança
---------
Todo egresso passa pelo `egress_guard` da SPEC-054, com uma allowlist montada a
partir das URLs que a **própria corretora declarou**. Não existe caminho para
apontar a captura a um host arbitrário: quem escolhe o destino é o dono do
tenant, e o guard revalida cada redirect do zero.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

from app.core import egress_guard as eg

logger = logging.getLogger(__name__)

FIRECRAWL_HOST = "api.firecrawl.dev"
TIMEOUT_CONEXAO = 8.0
TIMEOUT_LEITURA = 25.0
MAX_HTML = 3_000_000
MAX_IMAGEM = 4_000_000


# --------------------------------------------------------------------------
# Sinais
# --------------------------------------------------------------------------

@dataclass
class SinaisWeb:
    """O que uma página pública revela sobre a marca."""

    url: str
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    nome: Optional[str] = None
    legal_name: Optional[str] = None
    tagline: Optional[str] = None
    theme_color: Optional[str] = None
    logo_urls: list[str] = field(default_factory=list)
    icon_urls: list[str] = field(default_factory=list)
    og_image: Optional[str] = None
    fontes: list[str] = field(default_factory=list)
    cores_css: list[str] = field(default_factory=list)
    telefones: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    endereco: dict = field(default_factory=dict)
    cnpj: Optional[str] = None
    sociais: dict = field(default_factory=dict)
    servicos: list[str] = field(default_factory=list)
    texto_md: str = ""
    http_status: Optional[int] = None
    via: str = "direct"

    def as_extract(self) -> dict:
        d = {
            "titulo": self.titulo, "descricao": self.descricao, "nome": self.nome,
            "legal_name": self.legal_name, "tagline": self.tagline,
            "theme_color": self.theme_color, "logo_urls": self.logo_urls[:6],
            "icon_urls": self.icon_urls[:4], "og_image": self.og_image,
            "fontes": self.fontes[:6], "cores_css": self.cores_css[:12],
            "telefones": self.telefones[:6], "emails": self.emails[:4],
            "endereco": self.endereco, "cnpj": self.cnpj, "sociais": self.sociais,
            "servicos": self.servicos[:24], "via": self.via,
        }
        return {k: v for k, v in d.items() if v not in (None, [], {}, "")}


# --------------------------------------------------------------------------
# Extração de HTML
# --------------------------------------------------------------------------

_RE_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
_RE_META = re.compile(r"<meta\s+([^>]+?)/?>", re.I)
_RE_ATTR = re.compile(r'([\w:\-]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s">]+))')
_RE_LINK = re.compile(r"<link\s+([^>]+?)/?>", re.I)
_RE_IMG = re.compile(r"<img\s+([^>]+?)/?>", re.I)
_RE_JSONLD = re.compile(
    r'<script[^>]+type\s*=\s*["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.I | re.S)
_RE_CSSVAR = re.compile(r"--[\w\-]*(?:brand|primary|accent|main|theme|color)[\w\-]*\s*:\s*([^;}\n]+)", re.I)
_RE_TEL = re.compile(r"(?:\+?55\s*)?\(?(\d{2})\)?[\s.\-]?(\d{4,5})[\s.\-]?(\d{4})")
_RE_EMAIL = re.compile(r"[\w.+\-]+@[\w\-]+\.[\w.\-]+")
_RE_CNPJ = re.compile(r"\b(\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})\b")
_RE_TAG = re.compile(r"<[^>]+>")
_RE_SCRIPT = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", re.I | re.S)

_SOCIAIS = {
    "instagram": "instagram.com",
    "linkedin": "linkedin.com",
    "facebook": "facebook.com",
    "youtube": "youtube.com",
    "tiktok": "tiktok.com",
    "whatsapp": "wa.me",
}

_PISTAS_LOGO = ("logo", "brand", "marca", "header-image", "site-logo", "custom-logo")


def _attrs(bruto: str) -> dict:
    saida = {}
    for m in _RE_ATTR.finditer(bruto):
        saida[m.group(1).lower()] = (m.group(2) or m.group(3) or m.group(4) or "").strip()
    return saida


def _limpa(texto: str) -> str:
    import html as _html
    return _html.unescape(re.sub(r"\s+", " ", texto)).strip()


def extrair_sinais(html: str, url_base: str, *, via: str = "direct") -> SinaisWeb:
    s = SinaisWeb(url=url_base, via=via)
    if not html:
        return s

    m = _RE_TITLE.search(html)
    if m:
        s.titulo = _limpa(_RE_TAG.sub("", m.group(1)))[:300]

    # --- meta ---
    for m in _RE_META.finditer(html):
        a = _attrs(m.group(1))
        chave = (a.get("property") or a.get("name") or "").lower()
        valor = a.get("content", "").strip()
        if not valor:
            continue
        if chave in ("description", "og:description"):
            s.descricao = s.descricao or _limpa(valor)[:600]
        elif chave in ("og:site_name", "application-name"):
            s.nome = s.nome or _limpa(valor)[:160]
        elif chave == "og:image":
            s.og_image = s.og_image or urljoin(url_base, valor)
        elif chave == "theme-color":
            # Declarada pelo dono do site para a barra do navegador. É a cor
            # que a marca escolheu para se representar — sinal muito bom.
            s.theme_color = s.theme_color or valor
        elif chave == "og:title" and not s.tagline:
            s.tagline = _limpa(valor)[:200]

    # --- link rel ---
    for m in _RE_LINK.finditer(html):
        a = _attrs(m.group(1))
        rel = (a.get("rel") or "").lower()
        href = a.get("href", "")
        if not href:
            continue
        if "icon" in rel:
            s.icon_urls.append(urljoin(url_base, href))
        if "stylesheet" in rel and "fonts.googleapis.com" in href:
            for fam in re.findall(r"family=([^&:;]+)", href):
                s.fontes.append(fam.replace("+", " "))

    # --- img com pista de logo ---
    for m in _RE_IMG.finditer(html):
        a = _attrs(m.group(1))
        src = a.get("src") or a.get("data-src") or ""
        if not src or src.startswith("data:"):
            continue
        assinatura = " ".join((a.get("class", ""), a.get("id", ""),
                               a.get("alt", ""), src)).lower()
        if any(p in assinatura for p in _PISTAS_LOGO):
            s.logo_urls.append(urljoin(url_base, src))

    # --- JSON-LD: o sinal mais confiável quando existe ---
    for m in _RE_JSONLD.finditer(html):
        try:
            dados = json.loads(m.group(1).strip())
        except Exception:  # noqa: BLE001
            continue
        for no in _achatar_jsonld(dados):
            tipo = str(no.get("@type", "")).lower()
            if tipo not in ("organization", "localbusiness", "corporation",
                            "insuranceagency", "professionalservice", "website"):
                continue
            s.nome = s.nome or _texto(no.get("name"))
            s.legal_name = s.legal_name or _texto(no.get("legalName"))
            s.tagline = s.tagline or _texto(no.get("slogan"))
            logo = no.get("logo")
            if isinstance(logo, dict):
                logo = logo.get("url")
            if isinstance(logo, str):
                s.logo_urls.insert(0, urljoin(url_base, logo))
            tel = _texto(no.get("telephone"))
            if tel:
                s.telefones.append(tel)
            end = no.get("address")
            if isinstance(end, dict) and not s.endereco:
                s.endereco = {
                    "logradouro": _texto(end.get("streetAddress")),
                    "cidade": _texto(end.get("addressLocality")),
                    "uf": _texto(end.get("addressRegion")),
                    "cep": _texto(end.get("postalCode")),
                    "pais": _texto(end.get("addressCountry")),
                }
            same = no.get("sameAs")
            if isinstance(same, str):
                same = [same]
            for u in same or []:
                _classificar_social(str(u), s.sociais)

    # --- variáveis CSS que se declaram como marca ---
    for m in _RE_CSSVAR.finditer(html):
        s.cores_css.append(m.group(1).strip())

    # --- corpo em texto ---
    corpo = _RE_SCRIPT.sub(" ", html)
    texto = _limpa(_RE_TAG.sub(" ", corpo))
    s.texto_md = texto[:24000]

    for m in _RE_TEL.finditer(texto):
        s.telefones.append(f"({m.group(1)}) {m.group(2)}-{m.group(3)}")
    s.emails = [e for e in dict.fromkeys(_RE_EMAIL.findall(texto))
                if not e.lower().endswith((".png", ".jpg", ".gif", ".webp"))][:6]
    m = _RE_CNPJ.search(texto)
    if m:
        s.cnpj = m.group(1)

    for href in re.findall(r'href\s*=\s*["\']([^"\']+)["\']', html, re.I):
        _classificar_social(href, s.sociais)

    s.telefones = list(dict.fromkeys(s.telefones))[:8]
    s.logo_urls = list(dict.fromkeys(s.logo_urls))[:8]
    s.icon_urls = list(dict.fromkeys(s.icon_urls))[:6]
    s.fontes = list(dict.fromkeys(s.fontes))[:8]
    s.cores_css = list(dict.fromkeys(s.cores_css))[:16]
    s.servicos = _servicos_de_seguro(texto)
    return s


def _texto(v: Any) -> Optional[str]:
    if isinstance(v, str) and v.strip():
        return _limpa(v)[:300]
    return None


def _achatar_jsonld(dados: Any) -> list[dict]:
    saida: list[dict] = []
    pilha = [dados]
    while pilha:
        no = pilha.pop()
        if isinstance(no, list):
            pilha.extend(no)
        elif isinstance(no, dict):
            saida.append(no)
            for chave in ("@graph", "publisher", "provider", "parentOrganization"):
                if chave in no:
                    pilha.append(no[chave])
    return saida


def _classificar_social(url: str, destino: dict) -> None:
    baixo = url.lower()
    for nome, host in _SOCIAIS.items():
        if host in baixo and nome not in destino:
            destino[nome] = url if url.startswith("http") else f"https://{url.lstrip('/')}"


# Vocabulário do setor. Determinístico de propósito: é catálogo de ramo, não
# interpretação — e um LLM aqui custaria token para acertar menos.
_RAMOS = [
    ("auto", ("seguro auto", "seguro de auto", "automóvel", "automovel", "veicular")),
    ("frota", ("frota", "gestão de frota")),
    ("residencial", ("residencial", "seguro residência", "seguro casa")),
    ("vida", ("seguro de vida", "seguro vida")),
    ("previdência", ("previdência", "previdencia", "pgbl", "vgbl")),
    ("saúde", ("plano de saúde", "seguro saúde", "saude", "odontológico", "odontologico")),
    ("empresarial", ("empresarial", "seguro empresa", "patrimonial")),
    ("condomínio", ("condomínio", "condominio")),
    ("viagem", ("seguro viagem", "viagem")),
    ("responsabilidade civil", ("responsabilidade civil", " rc ", "d&o", "e&o")),
    ("riscos de engenharia", ("riscos de engenharia", "engenharia")),
    ("garantia", ("seguro garantia", "fiança locatícia", "fianca locaticia")),
    ("transporte", ("seguro de transporte", "cargas")),
    ("agro", ("agro", "agrícola", "agricola", "rural")),
    ("eventos", ("seguro de eventos", "eventos")),
    ("consórcio", ("consórcio", "consorcio")),
]


def _servicos_de_seguro(texto: str) -> list[str]:
    baixo = texto.lower()
    return [nome for nome, pistas in _RAMOS if any(p in baixo for p in pistas)]


# --------------------------------------------------------------------------
# Busca
# --------------------------------------------------------------------------

def _politica(urls: list[str]) -> eg.EgressPolicy:
    """Allowlist derivada do que a corretora declarou. Nada além."""
    hosts: set[str] = set()
    for u in urls:
        try:
            h = (urlparse(u).hostname or "").lower()
        except Exception:  # noqa: BLE001
            continue
        if h:
            hosts.add(h)
            hosts.add(h[4:] if h.startswith("www.") else f"www.{h}")
    return eg.EgressPolicy.from_iterable(hosts, max_response_bytes=MAX_HTML)


async def _buscar(client, decisao: eg.EgressDecision, policy: eg.EgressPolicy, *,
                  limite: int) -> tuple[Optional[bytes], int, str]:
    """GET com o guard, revalidando cada salto. Devolve (corpo, status, tipo).

    Redirect nunca é seguido pelo cliente HTTP: cada destino volta ao guard e é
    checado do zero. É o caminho clássico de SSRF — um host permitido que
    redireciona para 169.254.169.254.
    """
    for _ in range(4):
        resp = await client.get(decisao.url, follow_redirects=False)
        if resp.status_code not in (301, 302, 303, 307, 308):
            return resp.content[:limite], resp.status_code, resp.headers.get("content-type", "")
        destino = resp.headers.get("location", "")
        if not destino:
            return None, resp.status_code, ""
        decisao = eg.check_redirect(destino, decisao, policy)
    return None, 310, ""


async def buscar_pagina(url: str, *, allowlist: Optional[list[str]] = None) -> SinaisWeb:
    """Busca uma página e devolve os sinais de marca."""
    import httpx

    policy = _politica(allowlist or [url])
    decisao = eg.check_url(url, policy)

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(connect=TIMEOUT_CONEXAO, read=TIMEOUT_LEITURA,
                              write=TIMEOUT_CONEXAO, pool=TIMEOUT_CONEXAO),
        headers={"User-Agent": "AutoBrokersBrandBot/1.0 (+https://autobrokers.ai/bot)"},
        follow_redirects=False,
    ) as client:
        corpo, status, tipo = await _buscar(client, decisao, policy, limite=MAX_HTML)

    if not corpo or status >= 400:
        s = SinaisWeb(url=url)
        s.http_status = status
        return s

    sinais = extrair_sinais(corpo.decode("utf-8", errors="ignore"), url)
    sinais.http_status = status
    return sinais


async def buscar_com_firecrawl(url: str) -> Optional[SinaisWeb]:
    """Usa Firecrawl quando há chave. Resolve JS; é o que pega construtor de site."""
    chave = os.getenv("FIRECRAWL_API_KEY", "").strip()
    if not chave:
        return None

    import httpx

    policy = eg.EgressPolicy.from_iterable([FIRECRAWL_HOST], max_response_bytes=MAX_HTML)
    endpoint = f"https://{FIRECRAWL_HOST}/v1/scrape"
    eg.check_url(endpoint, policy)

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(connect=TIMEOUT_CONEXAO, read=60.0,
                                  write=TIMEOUT_CONEXAO, pool=TIMEOUT_CONEXAO)
        ) as client:
            resp = await client.post(
                endpoint,
                headers={"Authorization": f"Bearer {chave}", "Content-Type": "application/json"},
                json={"url": url, "formats": ["html", "markdown"],
                      "onlyMainContent": False, "timeout": 45000},
            )
        if resp.status_code >= 400:
            logger.warning("[brand] Firecrawl HTTP %s em %s", resp.status_code, eg.safe_log_url(url))
            return None
        dados = (resp.json() or {}).get("data") or {}
    except Exception as exc:  # noqa: BLE001
        logger.warning("[brand] Firecrawl indisponivel (%s) — seguindo por busca direta",
                       type(exc).__name__)
        return None

    html = dados.get("html") or dados.get("rawHtml") or ""
    sinais = extrair_sinais(html, url, via="firecrawl")
    if dados.get("markdown"):
        sinais.texto_md = dados["markdown"][:24000]

    meta = dados.get("metadata") or {}
    sinais.titulo = sinais.titulo or meta.get("title")
    sinais.descricao = sinais.descricao or meta.get("description")
    sinais.og_image = sinais.og_image or meta.get("ogImage")
    sinais.http_status = meta.get("statusCode") or 200
    return sinais


async def coletar(url: str, *, allowlist: Optional[list[str]] = None) -> SinaisWeb:
    """Firecrawl quando dá, busca direta sempre. O melhor resultado dos dois.

    Não é "tenta um, senão o outro": se ambos rodam, as listas de logo e as
    cores são unidas. Firecrawl vê o que o JS montou; a busca direta vê o HTML
    original, onde às vezes está o JSON-LD que o construtor descarta.
    """
    direto = await buscar_pagina(url, allowlist=allowlist)
    try:
        fc = await buscar_com_firecrawl(url)
    except Exception:  # noqa: BLE001
        fc = None

    if not fc:
        return direto
    if not direto.http_status or direto.http_status >= 400:
        return fc

    for campo in ("titulo", "descricao", "nome", "legal_name", "tagline",
                  "theme_color", "og_image", "cnpj"):
        if not getattr(fc, campo):
            setattr(fc, campo, getattr(direto, campo))
    for campo in ("logo_urls", "icon_urls", "fontes", "cores_css", "telefones",
                  "emails", "servicos"):
        unidos = list(dict.fromkeys(getattr(fc, campo) + getattr(direto, campo)))
        setattr(fc, campo, unidos)
    fc.sociais = {**direto.sociais, **fc.sociais}
    fc.endereco = fc.endereco or direto.endereco
    fc.via = "firecrawl+direct"
    return fc


async def baixar_binario(url: str, *, allowlist: Optional[list[str]] = None
                         ) -> tuple[Optional[bytes], str]:
    """Baixa uma imagem (logo/ícone) com o guard aplicado."""
    import httpx

    policy = _politica(allowlist or [url])
    decisao = eg.check_url(url, policy)
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(connect=TIMEOUT_CONEXAO, read=TIMEOUT_LEITURA,
                              write=TIMEOUT_CONEXAO, pool=TIMEOUT_CONEXAO),
        headers={"User-Agent": "AutoBrokersBrandBot/1.0"},
        follow_redirects=False,
    ) as client:
        corpo, status, tipo = await _buscar(client, decisao, policy, limite=MAX_IMAGEM)
    if not corpo or status >= 400:
        return None, ""
    return corpo, tipo
