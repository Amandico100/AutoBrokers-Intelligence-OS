"""Cliente Firecrawl com medição de consumo. SPEC-057 §Bloco G.

O que este módulo é, e o que ele não é
--------------------------------------
Ele **não** é uma segunda busca na web. `platform.web.search` já existe e usa
Tavily; criar outra ao lado seria exatamente o motor paralelo que o CLAUDE.md §5
proíbe. O que o Firecrawl acrescenta é uma capacidade que não existia:

  ler uma página específica por inteiro, resolvendo o JavaScript,
  e ler um documento público (PDF de apólice, condição geral, circular)
  como texto limpo.

Para uma corretora isso não é detalhe técnico. A condição geral de uma apólice
mora num PDF de 60 páginas no site da seguradora; hoje ninguém lê. Poder abrir
esse PDF e responder "o que cobre vidro nessa apólice" é trabalho pronto.

Medição
-------
Toda chamada emite um `usage_event` pelo `UsageService` da SPEC-055 — o mesmo
medidor dos tokens, com `unit_kind='firecrawl_credit'`. Nasce
`PRE_LAUNCH_NON_BILLABLE`: mede, não cobra. Quando a SPEC-062 ligar o rating,
o histórico já estará lá, atribuído por corretora.

O crédito reportado pela própria API é sempre preferido à estimativa. Quando
só há estimativa, o evento carrega `estimado=true` — número inventado que se
apresenta como medido é pior do que número ausente, porque vai virar fatura.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from app.core import egress_guard as eg

logger = logging.getLogger(__name__)

HOST = "api.firecrawl.dev"
BASE = f"https://{HOST}/v2"
POLITICA = eg.EgressPolicy.from_iterable([HOST], max_response_bytes=12_000_000)

TIMEOUT_CONEXAO = 8.0
TIMEOUT_LEITURA = 120.0     # scrape com JS e PDF grande passam de um minuto

# Estimativas de crédito, usadas só quando a resposta não informa o consumo.
# Marcadas como estimativa no evento — ver docstring.
CREDITO_ESTIMADO = {
    "scrape": 1.0,
    "search": 1.0,     # por resultado
    "parse": 1.0,
    "map": 1.0,
    "crawl": 1.0,      # por página
}


class FirecrawlIndisponivel(RuntimeError):
    """Sem chave, sem rede ou erro do provedor. Sempre tratável pelo chamador."""


@dataclass
class RespostaFirecrawl:
    ok: bool
    dados: Any = None
    creditos: float = 0.0
    credito_estimado: bool = True
    duracao_ms: int = 0
    erro: Optional[str] = None
    job_id: Optional[str] = None


def configurado() -> bool:
    return bool(os.getenv("FIRECRAWL_API_KEY", "").strip())


class FirecrawlClient:
    """Chamadas ao Firecrawl, sempre pelo guard de egresso e sempre medidas."""

    def __init__(self, supabase_client: Any = None, *, company_id: Optional[str] = None):
        self._db = supabase_client
        self.company_id = company_id
        self._usage = None

    # ------------------------------------------------------------------

    def _chave(self) -> str:
        k = os.getenv("FIRECRAWL_API_KEY", "").strip()
        if not k:
            raise FirecrawlIndisponivel("FIRECRAWL_API_KEY nao configurada")
        return k

    def _medir(self, operacao: str, r: RespostaFirecrawl, *,
               work_run_id: Optional[str] = None, skill: Optional[str] = None,
               detalhe: Optional[str] = None) -> None:
        """Emite o evento de consumo. Falha aqui nunca derruba a operação."""
        if not self._db or not self.company_id:
            return
        try:
            if self._usage is None:
                from app.services.work.usage import UsageService
                self._usage = UsageService(self._db)
            self._usage.registrar(
                company_id=self.company_id,
                source="tool",
                work_run_id=work_run_id,
                skill_slug=skill,
                capability_key="platform.web.scrape",
                tool_name=f"firecrawl.{operacao}",
                provider="firecrawl",
                model=("estimado" if r.credito_estimado else "medido"),
                units=r.creditos,
                unit_kind="firecrawl_credit",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[firecrawl] medicao nao gravada: %s", type(exc).__name__)

    async def _post(self, caminho: str, corpo: dict, *, timeout: float = TIMEOUT_LEITURA
                    ) -> RespostaFirecrawl:
        import httpx

        url = f"{BASE}{caminho}"
        eg.check_url(url, POLITICA)
        inicio = time.monotonic()
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(connect=TIMEOUT_CONEXAO, read=timeout,
                                      write=TIMEOUT_CONEXAO, pool=TIMEOUT_CONEXAO)
            ) as client:
                resp = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {self._chave()}",
                             "Content-Type": "application/json"},
                    json=corpo,
                )
        except FirecrawlIndisponivel:
            raise
        except Exception as exc:  # noqa: BLE001
            return RespostaFirecrawl(False, erro=type(exc).__name__,
                                     duracao_ms=int((time.monotonic() - inicio) * 1000))

        ms = int((time.monotonic() - inicio) * 1000)
        if resp.status_code >= 400:
            # Nunca logar a URL com querystring nem o corpo — pode conter dado
            # do segurado numa busca.
            logger.warning("[firecrawl] %s HTTP %s", caminho, resp.status_code)
            return RespostaFirecrawl(False, erro=f"HTTP {resp.status_code}", duracao_ms=ms)

        try:
            j = resp.json() or {}
        except Exception:  # noqa: BLE001
            return RespostaFirecrawl(False, erro="resposta nao-JSON", duracao_ms=ms)

        creditos = j.get("creditsUsed")
        if creditos is None:
            creditos = (j.get("metadata") or {}).get("creditsUsed")

        return RespostaFirecrawl(
            ok=bool(j.get("success", True)),
            dados=j.get("data", j),
            creditos=float(creditos) if creditos is not None else 0.0,
            credito_estimado=creditos is None,
            duracao_ms=ms,
            job_id=j.get("id") or j.get("jobId"),
        )

    # ------------------------------------------------------------------
    # Operações
    # ------------------------------------------------------------------

    async def scrape(self, url: str, *, formatos: Optional[list[str]] = None,
                     so_conteudo: bool = True, timeout_ms: int = 45_000,
                     work_run_id: Optional[str] = None,
                     skill: Optional[str] = None) -> RespostaFirecrawl:
        """Lê uma página inteira, resolvendo JavaScript. Serve também para PDF público."""
        r = await self._post("/scrape", {
            "url": url,
            "formats": formatos or ["markdown"],
            "onlyMainContent": so_conteudo,
            "timeout": timeout_ms,
        })
        if r.credito_estimado and r.ok:
            r.creditos = CREDITO_ESTIMADO["scrape"]
        self._medir("scrape", r, work_run_id=work_run_id, skill=skill)
        return r

    async def search(self, consulta: str, *, limite: int = 5,
                     com_conteudo: bool = True, pais: str = "br",
                     work_run_id: Optional[str] = None,
                     skill: Optional[str] = None) -> RespostaFirecrawl:
        """Busca **com conteúdo** — um passo, não busca seguida de N leituras.

        É o ganho concreto sobre a busca que já existe: para um dossiê, o que
        importa é o texto da fonte, e ir buscar cada link depois custa latência
        e crédito a mais.
        """
        corpo: dict[str, Any] = {"query": consulta, "limit": max(1, min(limite, 20))}
        if com_conteudo:
            corpo["scrapeOptions"] = {"formats": ["markdown"], "onlyMainContent": True}
        if pais:
            corpo["location"] = {"country": pais}

        r = await self._post("/search", corpo)
        if r.credito_estimado and r.ok:
            n = len(r.dados if isinstance(r.dados, list) else (r.dados or {}).get("web") or [])
            r.creditos = CREDITO_ESTIMADO["search"] * max(1, n)
        self._medir("search", r, work_run_id=work_run_id, skill=skill)
        return r

    async def map_site(self, url: str, *, limite: int = 100,
                       work_run_id: Optional[str] = None) -> RespostaFirecrawl:
        """Lista as URLs de um site. Usado para achar a página certa antes de ler."""
        r = await self._post("/map", {"url": url, "limit": limite}, timeout=60.0)
        if r.credito_estimado and r.ok:
            r.creditos = CREDITO_ESTIMADO["map"]
        self._medir("map", r, work_run_id=work_run_id)
        return r


# --------------------------------------------------------------------------
# Uso pelo agente
# --------------------------------------------------------------------------

async def ler_pagina(url: str, *, supabase=None, company_id: Optional[str] = None,
                     work_run_id: Optional[str] = None) -> dict:
    """Fachada para a tool `research.web_scrape`.

    Devolve sempre um dicionário com `ok` — o agente precisa distinguir "a
    página não tem a resposta" de "não consegui ler a página", e uma exceção
    solta no meio do grafo vira as duas coisas ao mesmo tempo.
    """
    if not configurado():
        return {"ok": False, "motivo": "firecrawl_nao_configurado",
                "mensagem_humana": "A leitura de páginas ainda não está ativa nesta conta."}

    cli = FirecrawlClient(supabase, company_id=company_id)
    try:
        r = await cli.scrape(url, work_run_id=work_run_id, skill="research.web_brief")
    except FirecrawlIndisponivel as exc:
        return {"ok": False, "motivo": "indisponivel", "mensagem_humana": str(exc)}

    if not r.ok:
        return {"ok": False, "motivo": r.erro or "falha",
                "mensagem_humana": "Não consegui abrir essa página agora."}

    d = r.dados if isinstance(r.dados, dict) else {}
    meta = d.get("metadata") or {}
    return {
        "ok": True,
        "url": meta.get("sourceURL") or url,
        "titulo": meta.get("title"),
        "conteudo": (d.get("markdown") or "")[:120_000],
        "creditos": r.creditos,
        "duracao_ms": r.duracao_ms,
    }


async def pesquisar_com_fontes(consulta: str, *, limite: int = 5, supabase=None,
                               company_id: Optional[str] = None,
                               work_run_id: Optional[str] = None) -> dict:
    """Fachada para a tool `research.web_search_deep`."""
    if not configurado():
        return {"ok": False, "motivo": "firecrawl_nao_configurado", "resultados": []}

    cli = FirecrawlClient(supabase, company_id=company_id)
    try:
        r = await cli.search(consulta, limite=limite, work_run_id=work_run_id,
                             skill="research.web_brief")
    except FirecrawlIndisponivel as exc:
        return {"ok": False, "motivo": str(exc), "resultados": []}

    if not r.ok:
        return {"ok": False, "motivo": r.erro or "falha", "resultados": []}

    brutos = r.dados if isinstance(r.dados, list) else (r.dados or {}).get("web") or []
    return {
        "ok": True,
        "creditos": r.creditos,
        "resultados": [{
            "url": x.get("url"),
            "titulo": x.get("title"),
            "resumo": x.get("description"),
            # O conteúdo entra truncado: um dossiê com cinco fontes inteiras
            # estoura a janela e o modelo passa a ignorar o começo.
            "conteudo": (x.get("markdown") or "")[:24_000],
        } for x in brutos if isinstance(x, dict)],
    }
