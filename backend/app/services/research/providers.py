"""Adapters de provider. SPEC-060 §9.

Contrato único, providers intercambiáveis (§4.4). Cada adapter devolve
`RespostaDeProvider` — falha é **resultado**, não exceção. Um provider que
levanta exceção no meio de uma pesquisa profunda derruba as outras cinco
fontes que já tinham sido lidas.

Degradação sem mentira (D18)
----------------------------
O Firecrawl está sem crédito e o Founder decidiu não fazer upgrade agora.
Então cada adapter distingue três coisas que costumam virar um "erro" só:

    sem chave configurada   → a capacidade não existe nesta instalação
    sem crédito (HTTP 402)  → a capacidade existe e a fatura acabou
    erro do provedor        → a capacidade existe e falhou agora

A diferença não é cosmética. Um pipeline que trata as três igual manda o
corretor "tentar de novo" quando o problema é a fatura, e desiste da fonte
quando o problema era temporário. O tratamento de 402 é o mesmo já usado pelo
corpus normativo (SPEC-057 §H): **não gasta tentativa e para o ciclo**.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Optional, Protocol

from .schemas import (TIER_IMPRENSA, RespostaDeProvider, ResultadoDeFonte)
from .source_policy import classificar
from .urls import normalizar

logger = logging.getLogger(__name__)

# Motivos estáveis. O código de erro é contrato: a UI e o Admin decidem o que
# mostrar a partir dele, e mudar a string quebra as duas pontas.
SEM_CHAVE = "sem_chave"
SEM_CREDITO = "sem_credito"
INDISPONIVEL = "indisponivel"
BLOQUEADO = "bloqueado_por_politica"

MOTIVO_HUMANO = {
    SEM_CHAVE: "Esta forma de leitura ainda não está ativa nesta instalação.",
    SEM_CREDITO: ("O provedor de leitura da web está sem crédito. A pesquisa "
                  "continua com as fontes que já temos, e o restante entra na "
                  "fila — nada é descartado."),
    INDISPONIVEL: "O provedor não respondeu agora.",
    BLOQUEADO: "A política desta fonte não permite este tipo de leitura.",
}


class Provider(Protocol):
    """Contrato de §9.1. Nem todo provider implementa tudo."""

    provider_key: str

    def disponivel(self) -> bool: ...
    async def search(self, consulta: str, **kw: Any) -> RespostaDeProvider: ...


@dataclass
class SaudeDoProvider:
    provider_key: str
    configurado: bool
    disponivel: bool
    motivo: str = ""
    operacoes: tuple[str, ...] = ()


def _falha(provider: str, operacao: str, motivo: str, *,
           inicio: Optional[float] = None) -> RespostaDeProvider:
    return RespostaDeProvider(
        ok=False, provider=provider, operacao=operacao, erro=motivo,
        motivo_humano=MOTIVO_HUMANO.get(motivo, "Não consegui consultar agora."),
        sem_credito=(motivo == SEM_CREDITO),
        duracao_ms=int((time.monotonic() - inicio) * 1000) if inicio else 0)


# ===========================================================================
# Tavily — §9.2
# ===========================================================================


class TavilyProvider:
    """Busca. Assíncrono de verdade e com retorno estruturado.

    O `TavilyService` histórico é preservado (§35.1) e continua servindo a
    tool antiga durante a transição. O que muda aqui: em vez de devolver uma
    string markdown pronta para o prompt, devolve `ResultadoDeFonte` — que é
    o que permite classificar tier, deduplicar por URL e citar no nível da
    afirmação. String formatada não tem como virar citação.
    """

    provider_key = "tavily"
    operacoes = ("search", "extract")

    def __init__(self) -> None:
        self._cliente = None

    def disponivel(self) -> bool:
        return bool(self._chave())

    def _chave(self) -> str:
        try:
            from ...core.config import settings

            return (getattr(settings, "TAVILY_API_KEY", "") or "").strip()
        except Exception:  # noqa: BLE001
            return (os.getenv("TAVILY_API_KEY") or "").strip()

    def _obter_cliente(self):
        if self._cliente is None:
            from tavily import TavilyClient

            self._cliente = TavilyClient(api_key=self._chave())
        return self._cliente

    async def search(self, consulta: str, *, limite: int = 5,
                     profundidade: str = "basic",
                     dominios: Optional[list[str]] = None,
                     dias: Optional[int] = None, **_: Any) -> RespostaDeProvider:
        import asyncio

        if not self.disponivel():
            return _falha(self.provider_key, "search", SEM_CHAVE)

        inicio = time.monotonic()

        def _buscar() -> dict:
            kwargs: dict[str, Any] = {
                "query": consulta,
                "search_depth": profundidade if profundidade in ("basic", "advanced") else "basic",
                "max_results": max(1, min(int(limite), 20)),
            }
            if dominios:
                kwargs["include_domains"] = dominios[:20]
            if dias:
                kwargs["days"] = int(dias)
            return self._obter_cliente().search(**kwargs) or {}

        try:
            # O serviço histórico chamava a versão síncrona dentro de `_arun`
            # (§3.2). Aqui a thread separada é real — numa pesquisa profunda
            # com dez buscas, bloquear o event loop trava o worker inteiro.
            bruto = await asyncio.to_thread(_buscar)
        except Exception as exc:  # noqa: BLE001
            texto = str(exc).lower()
            if "402" in texto or "credit" in texto or "quota" in texto:
                return _falha(self.provider_key, "search", SEM_CREDITO, inicio=inicio)
            logger.warning("[tavily] busca falhou: %s", type(exc).__name__)
            return _falha(self.provider_key, "search", INDISPONIVEL, inicio=inicio)

        fontes: list[ResultadoDeFonte] = []
        for r in (bruto.get("results") or []):
            url = normalizar(str(r.get("url") or ""))
            if not url:
                continue
            tier, oficial = classificar(url, titulo=str(r.get("title") or ""))
            fontes.append(ResultadoDeFonte(
                url=url, titulo=str(r.get("title") or ""),
                resumo=str(r.get("content") or "")[:2_000],
                conteudo=str(r.get("raw_content") or "")[:60_000],
                publicado_em=r.get("published_date"),
                provider=self.provider_key, tier=tier, oficial=oficial,
                metadata={"score": r.get("score")}))

        return RespostaDeProvider(
            ok=True, provider=self.provider_key, operacao="search",
            fontes=fontes, creditos=float(len(fontes) or 1),
            credito_estimado=True,
            duracao_ms=int((time.monotonic() - inicio) * 1000))


# ===========================================================================
# Firecrawl — §9.3
# ===========================================================================


class FirecrawlProvider:
    """Leitura profunda: página inteira, PDF, mapa de site.

    **Não** reimplementa o cliente: usa o `FirecrawlClient` da SPEC-057, que
    já tem egress guard, medição de crédito e o tratamento de 402. Escrever
    outro seria o motor paralelo que o CLAUDE.md §5 proíbe — e perderíamos a
    medição por corretora que já funciona.
    """

    provider_key = "firecrawl"
    operacoes = ("search", "scrape", "map")

    def __init__(self, supabase: Any = None, *, company_id: Optional[str] = None):
        self._db = supabase
        self.company_id = company_id

    def disponivel(self) -> bool:
        from .firecrawl import configurado

        return configurado()

    def _cliente(self):
        from .firecrawl import FirecrawlClient

        return FirecrawlClient(self._db, company_id=self.company_id)

    async def scrape(self, url: str, *, work_run_id: Optional[str] = None,
                     **_: Any) -> RespostaDeProvider:
        if not self.disponivel():
            return _falha(self.provider_key, "scrape", SEM_CHAVE)

        from .firecrawl import FirecrawlIndisponivel

        inicio = time.monotonic()
        try:
            r = await self._cliente().scrape(url, work_run_id=work_run_id,
                                             skill="research.deep")
        except FirecrawlIndisponivel:
            return _falha(self.provider_key, "scrape", SEM_CHAVE, inicio=inicio)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[firecrawl] scrape falhou: %s", type(exc).__name__)
            return _falha(self.provider_key, "scrape", INDISPONIVEL, inicio=inicio)

        if not r.ok:
            # D18: 402 tem nome próprio e não gasta tentativa.
            motivo = SEM_CREDITO if r.erro == "HTTP 402" else INDISPONIVEL
            return _falha(self.provider_key, "scrape", motivo, inicio=inicio)

        d = r.dados if isinstance(r.dados, dict) else {}
        meta = d.get("metadata") or {}
        alvo = normalizar(str(meta.get("sourceURL") or url)) or url
        tier, oficial = classificar(alvo, titulo=str(meta.get("title") or ""))
        return RespostaDeProvider(
            ok=True, provider=self.provider_key, operacao="scrape",
            fontes=[ResultadoDeFonte(
                url=alvo, titulo=str(meta.get("title") or ""),
                conteudo=(d.get("markdown") or "")[:200_000],
                resumo=str(meta.get("description") or "")[:2_000],
                publicado_em=meta.get("publishedTime") or meta.get("modifiedTime"),
                provider=self.provider_key, tier=tier, oficial=oficial,
                http_status=meta.get("statusCode"),
                metadata={"language": meta.get("language")})],
            creditos=r.creditos, credito_estimado=r.credito_estimado,
            duracao_ms=r.duracao_ms)

    async def search(self, consulta: str, *, limite: int = 5,
                     work_run_id: Optional[str] = None,
                     **_: Any) -> RespostaDeProvider:
        """Busca COM conteúdo — um passo em vez de busca seguida de N leituras."""
        if not self.disponivel():
            return _falha(self.provider_key, "search", SEM_CHAVE)

        from .firecrawl import FirecrawlIndisponivel

        inicio = time.monotonic()
        try:
            r = await self._cliente().search(consulta, limite=limite,
                                             work_run_id=work_run_id,
                                             skill="research.deep")
        except FirecrawlIndisponivel:
            return _falha(self.provider_key, "search", SEM_CHAVE, inicio=inicio)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[firecrawl] busca falhou: %s", type(exc).__name__)
            return _falha(self.provider_key, "search", INDISPONIVEL, inicio=inicio)

        if not r.ok:
            motivo = SEM_CREDITO if r.erro == "HTTP 402" else INDISPONIVEL
            return _falha(self.provider_key, "search", motivo, inicio=inicio)

        brutos = r.dados if isinstance(r.dados, list) else (r.dados or {}).get("web") or []
        fontes: list[ResultadoDeFonte] = []
        for x in brutos:
            if not isinstance(x, dict):
                continue
            url = normalizar(str(x.get("url") or ""))
            if not url:
                continue
            tier, oficial = classificar(url, titulo=str(x.get("title") or ""))
            fontes.append(ResultadoDeFonte(
                url=url, titulo=str(x.get("title") or ""),
                resumo=str(x.get("description") or "")[:2_000],
                conteudo=(x.get("markdown") or "")[:60_000],
                provider=self.provider_key, tier=tier, oficial=oficial))

        return RespostaDeProvider(
            ok=True, provider=self.provider_key, operacao="search",
            fontes=fontes, creditos=r.creditos,
            credito_estimado=r.credito_estimado, duracao_ms=r.duracao_ms)

    async def map_site(self, url: str, *, limite: int = 100,
                       work_run_id: Optional[str] = None,
                       **_: Any) -> RespostaDeProvider:
        """§14.2 — mapear antes de rastrear. Barato e evita crawl integral."""
        if not self.disponivel():
            return _falha(self.provider_key, "map", SEM_CHAVE)

        from .firecrawl import FirecrawlIndisponivel

        inicio = time.monotonic()
        try:
            r = await self._cliente().map_site(url, limite=limite,
                                               work_run_id=work_run_id)
        except FirecrawlIndisponivel:
            return _falha(self.provider_key, "map", SEM_CHAVE, inicio=inicio)
        except Exception as exc:  # noqa: BLE001
            return _falha(self.provider_key, "map", INDISPONIVEL, inicio=inicio)

        if not r.ok:
            motivo = SEM_CREDITO if r.erro == "HTTP 402" else INDISPONIVEL
            return _falha(self.provider_key, "map", motivo, inicio=inicio)

        brutos = r.dados if isinstance(r.dados, list) else (r.dados or {}).get("links") or []
        fontes = []
        for item in brutos:
            alvo = item if isinstance(item, str) else (item or {}).get("url")
            url_ok = normalizar(str(alvo or ""))
            if not url_ok:
                continue
            tier, oficial = classificar(url_ok)
            fontes.append(ResultadoDeFonte(
                url=url_ok, provider=self.provider_key, tier=tier, oficial=oficial,
                titulo=(item.get("title") if isinstance(item, dict) else "") or ""))

        return RespostaDeProvider(
            ok=True, provider=self.provider_key, operacao="map", fontes=fontes,
            creditos=r.creditos, credito_estimado=r.credito_estimado,
            duracao_ms=r.duracao_ms)


# ===========================================================================
# Direct Fetch — §9.5
# ===========================================================================


class DirectFetchProvider:
    """Leitura direta de fonte pública, pelo Egress Guard da SPEC-054.

    Existe por dois motivos, e o segundo é o que importa hoje: para fonte
    oficial simples (HTML estático, XML, RSS, PDF), ela é **mais confiável e
    mais barata** que qualquer provider — e continua funcionando quando o
    crédito do Firecrawl acaba. Com D18 ativa, é este o caminho que sustenta
    a pesquisa.
    """

    provider_key = "direct_fetch"
    operacoes = ("fetch",)

    MIMES_PERMITIDOS = ("text/html", "text/plain", "application/xhtml+xml",
                        "application/xml", "text/xml", "application/rss+xml",
                        "application/atom+xml", "application/json",
                        "application/pdf")
    MAX_BYTES = 8_000_000
    TIMEOUT = 25.0

    def disponivel(self) -> bool:
        return True  # não depende de chave nem de fatura

    async def fetch(self, url: str, **_: Any) -> RespostaDeProvider:
        import httpx

        from ...core import egress_guard as eg

        alvo = normalizar(url)
        if not alvo:
            return _falha(self.provider_key, "fetch", BLOQUEADO)

        inicio = time.monotonic()
        # A allowlist é o domínio do próprio alvo: o guard continua barrando
        # loopback, rede privada, metadata da nuvem, rebinding e redirect
        # perigoso — que é o que ele existe para fazer (§15.5).
        from .urls import dominio

        politica = eg.EgressPolicy.from_iterable(
            [dominio(alvo)], max_response_bytes=self.MAX_BYTES)
        try:
            eg.check_url(alvo, politica)
        except Exception as exc:  # noqa: BLE001
            logger.info("[direct_fetch] bloqueado pelo egress guard: %s",
                        type(exc).__name__)
            return _falha(self.provider_key, "fetch", BLOQUEADO, inicio=inicio)

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.TIMEOUT), follow_redirects=True,
                max_redirects=3,
                headers={"User-Agent": "AutoBrokersResearch/1.0 (+https://autobrokers.ai)"},
            ) as cli:
                resp = await cli.get(alvo)
        except Exception as exc:  # noqa: BLE001
            return _falha(self.provider_key, "fetch", INDISPONIVEL, inicio=inicio)

        ms = int((time.monotonic() - inicio) * 1000)
        if resp.status_code >= 400:
            return RespostaDeProvider(
                ok=False, provider=self.provider_key, operacao="fetch",
                erro=f"HTTP {resp.status_code}", duracao_ms=ms,
                motivo_humano="A fonte respondeu com erro.")

        tipo = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
        if tipo and not any(tipo.startswith(m) for m in self.MIMES_PERMITIDOS):
            return RespostaDeProvider(
                ok=False, provider=self.provider_key, operacao="fetch",
                erro=f"mime_nao_permitido:{tipo}", duracao_ms=ms,
                motivo_humano="O conteúdo desta fonte não é texto legível.")

        bruto = resp.text if tipo != "application/pdf" else ""
        if tipo == "application/pdf":
            # PDF exige parser. Sem provider disponível, declara a limitação em
            # vez de devolver bytes ilegíveis como se fossem texto (§14.6).
            return RespostaDeProvider(
                ok=False, provider=self.provider_key, operacao="fetch",
                erro="pdf_sem_parser", duracao_ms=ms,
                motivo_humano=("Esta fonte é um PDF e a leitura de documentos "
                               "depende do provedor, que está sem crédito."))

        tier, oficial = classificar(str(resp.url))
        return RespostaDeProvider(
            ok=True, provider=self.provider_key, operacao="fetch",
            fontes=[ResultadoDeFonte(
                url=normalizar(str(resp.url)) or alvo,
                conteudo=bruto[:400_000], provider=self.provider_key,
                tier=tier, oficial=oficial, http_status=resp.status_code,
                metadata={"content_type": tipo,
                          "last_modified": resp.headers.get("last-modified"),
                          "etag": resp.headers.get("etag")})],
            creditos=0.0, credito_estimado=False, duracao_ms=ms)


# ===========================================================================
# Places — §9.4 e §19
# ===========================================================================


class PlacesProvider:
    """Descoberta de empresas pela Google Places API (New).

    §4.5 é categórica: **a interface do Google Maps não é raspada.** O caminho
    é a API licenciada, com Field Mask mínimo — e só campos comerciais.

    O Field Mask não é otimização de custo: é a fronteira de privacidade. Ele
    é a razão técnica de o sistema não conseguir coletar mais do que declarou,
    mesmo que alguém peça.
    """

    provider_key = "google_places"
    operacoes = ("search_businesses", "get_details")
    BASE = "https://places.googleapis.com/v1"

    # Só o que uma prospecção EMPRESARIAL precisa. Sem avaliações individuais,
    # sem fotos de pessoas, sem qualquer campo de pessoa física (§19.4).
    CAMPOS = ("places.id,places.displayName,places.formattedAddress,"
              "places.nationalPhoneNumber,places.websiteUri,places.types,"
              "places.businessStatus,places.location,places.primaryType")

    def disponivel(self) -> bool:
        return bool((os.getenv("GOOGLE_PLACES_API_KEY") or "").strip())

    async def buscar_empresas(self, consulta: str, *, regiao: str = "BR",
                              limite: int = 20, **_: Any) -> RespostaDeProvider:
        import httpx

        if not self.disponivel():
            return _falha(self.provider_key, "search_businesses", SEM_CHAVE)

        inicio = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(20.0)) as cli:
                resp = await cli.post(
                    f"{self.BASE}/places:searchText",
                    headers={
                        "Content-Type": "application/json",
                        "X-Goog-Api-Key": (os.getenv("GOOGLE_PLACES_API_KEY") or "").strip(),
                        "X-Goog-FieldMask": self.CAMPOS,
                    },
                    json={"textQuery": consulta,
                          "maxResultCount": max(1, min(int(limite), 20)),
                          "languageCode": "pt-BR", "regionCode": regiao})
        except Exception:  # noqa: BLE001
            return _falha(self.provider_key, "search_businesses", INDISPONIVEL,
                          inicio=inicio)

        ms = int((time.monotonic() - inicio) * 1000)
        if resp.status_code == 402 or resp.status_code == 429:
            return _falha(self.provider_key, "search_businesses", SEM_CREDITO,
                          inicio=inicio)
        if resp.status_code >= 400:
            return RespostaDeProvider(
                ok=False, provider=self.provider_key,
                operacao="search_businesses", erro=f"HTTP {resp.status_code}",
                duracao_ms=ms,
                motivo_humano="A busca de empresas não respondeu agora.")

        try:
            dados = resp.json() or {}
        except Exception:  # noqa: BLE001
            return _falha(self.provider_key, "search_businesses", INDISPONIVEL,
                          inicio=inicio)

        fontes: list[ResultadoDeFonte] = []
        for p in (dados.get("places") or []):
            site = normalizar(str(p.get("websiteUri") or "")) or ""
            fontes.append(ResultadoDeFonte(
                url=site or f"places://{p.get('id')}",
                titulo=str((p.get("displayName") or {}).get("text") or ""),
                provider=self.provider_key, tier=TIER_IMPRENSA, oficial=False,
                metadata={
                    "place_id": p.get("id"),
                    "endereco": p.get("formattedAddress"),
                    "telefone": p.get("nationalPhoneNumber"),
                    "site": site,
                    "categorias": p.get("types") or [],
                    "categoria_principal": p.get("primaryType"),
                    "status": p.get("businessStatus"),
                    # §19.4 e §34.3: a atribuição é obrigação do provider e
                    # viaja junto do dado, não numa nota de rodapé perdida.
                    "attribution": "Dados de lugares fornecidos pelo Google",
                }))

        return RespostaDeProvider(
            ok=True, provider=self.provider_key, operacao="search_businesses",
            fontes=fontes, creditos=float(len(fontes) or 1),
            credito_estimado=True, duracao_ms=ms)


# ===========================================================================
# Registro
# ===========================================================================


def registro(supabase: Any = None, *,
             company_id: Optional[str] = None) -> dict[str, Any]:
    return {
        "tavily": TavilyProvider(),
        "firecrawl": FirecrawlProvider(supabase, company_id=company_id),
        "direct_fetch": DirectFetchProvider(),
        "google_places": PlacesProvider(),
    }


def saude(supabase: Any = None) -> list[SaudeDoProvider]:
    """Estado de cada provider — §31.1. Sem revelar chave, só presença."""
    saida = []
    for chave, p in registro(supabase).items():
        try:
            ok = bool(p.disponivel())
        except Exception:  # noqa: BLE001
            ok = False
        saida.append(SaudeDoProvider(
            provider_key=chave, configurado=ok, disponivel=ok,
            motivo="" if ok else "chave não configurada nesta instalação",
            operacoes=tuple(getattr(p, "operacoes", ()))))
    return saida
