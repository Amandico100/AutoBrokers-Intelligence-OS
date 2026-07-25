"""Leitura profunda da web — Firecrawl. SPEC-057 §Bloco G.

Três ferramentas que respondem a coisas diferentes:

  research.web_scrape        "abra este endereço e me diga o que tem lá"
  research.web_search_deep   "pesquise e já me traga o texto das fontes"
  research.document_read     "leia este PDF inteiro"

A terceira é a que mais muda a vida de uma corretora. A condição geral de uma
apólice mora num PDF de 60 páginas no site da seguradora, e por isso ninguém
lê — nem o corretor, nem o cliente. Poder abrir esse documento e responder "o
que essa apólice cobre em vidro" é a diferença entre achar e saber.

Nenhuma delas substitui a `web_search` que já existe. Aquela responde "o que
se fala sobre X" e é mais barata. Estas custam crédito e existem para quando o
resumo não basta.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

LIMITE_CONTEUDO = 60_000


class _UrlIn(BaseModel):
    url: str = Field(description="Endereço completo da página ou documento, começando com https://")


class _BuscaIn(BaseModel):
    query: str = Field(description="O que pesquisar, em linguagem natural")
    limit: int = Field(default=4, ge=1, le=8,
                       description="Quantas fontes trazer. Cada fonte custa crédito — peça o que vai usar.")


class _Base(BaseTool):
    """Base comum: leva o tenant junto para a medição de consumo.

    Sem `company_id`, o crédito gasto não é atribuível a ninguém — e um custo
    que não se atribui é um custo que não se cobra depois.
    """

    company_id: Optional[str] = None
    supabase: Any = None
    work_run_id: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True

    def _run(self, *args, **kwargs) -> str:  # noqa: D401
        return ("Esta ferramenta é assíncrona. O runtime deve chamá-la por `arun`.")


class WebScrapeTool(_Base):
    name: str = "web_scrape"
    description: str = (
        "Abre uma página da internet e devolve o conteúdo completo, resolvendo JavaScript. "
        "Use quando já tiver o endereço e precisar do texto inteiro — não use para descobrir "
        "endereços (para isso, use web_search). Consome crédito da corretora."
    )
    args_schema: Type[BaseModel] = _UrlIn

    async def _arun(self, url: str, **_: Any) -> str:
        from ...services.research.firecrawl import ler_pagina

        r = await ler_pagina(url, supabase=self.supabase, company_id=self.company_id,
                             work_run_id=self.work_run_id)
        if not r.get("ok"):
            # Devolve texto, não exceção: o agente precisa distinguir "a página
            # não tem a resposta" de "não consegui abrir a página", e uma
            # exceção solta no grafo transforma as duas coisas numa só.
            return f"Não foi possível ler a página. Motivo: {r.get('mensagem_humana') or r.get('motivo')}"
        return (f"# {r.get('titulo') or url}\nFonte: {r.get('url')}\n\n"
                f"{(r.get('conteudo') or '')[:LIMITE_CONTEUDO]}")


class DocumentReadTool(_Base):
    """Lê documento público — mas só depois de confirmar que não temos.

    Condição geral é o mesmo documento para todas as corretoras. Buscá-lo de
    novo a cada pergunta cobraria de cada corretora a leitura de algo que já
    está no conhecimento global — e, pior, poderia devolver respostas
    diferentes conforme o dia da leitura.

    Ordem: catálogo primeiro. Se estiver lá, custo zero e a resposta vem da
    busca de conhecimento. Se não estiver, lê ao vivo **e registra o documento
    como candidato ao corpus** — a próxima corretora que precisar não paga.
    """

    name: str = "document_read"
    description: str = (
        "Lê um documento público pela URL (PDF, DOCX). Use para condições gerais de "
        "apólice, circulares da SUSEP e manuais de seguradora. Antes de usar, prefira "
        "knowledge_base_search: boa parte das condições gerais já está no conhecimento "
        "da AutoBrokers e sai de graça."
    )
    args_schema: Type[BaseModel] = _UrlIn

    async def _arun(self, url: str, **_: Any) -> str:
        from ...services.knowledge.insurance_corpus import InsuranceCorpusService
        from ...services.research.firecrawl import ler_pagina

        corpus = None
        if self.supabase is not None:
            try:
                corpus = InsuranceCorpusService(self.supabase)
                ja = corpus.ja_temos(url)
            except Exception:  # noqa: BLE001
                ja = None
        else:
            ja = None

        if ja:
            vig = ja.get("effective_from") or "não declarada"
            return (
                f"Este documento **já está no conhecimento da AutoBrokers** — não é "
                f"preciso baixá-lo de novo.\n\n"
                f"- **{ja.get('title')}**\n"
                f"- Seguradora: {ja.get('insurer_name')} · Ramo: {ja.get('product_line')}\n"
                + (f"- Processo SUSEP: {ja.get('susep_process')}\n" if ja.get("susep_process") else "")
                + f"- Vigência a partir de: {vig}\n"
                f"- Conferido pela última vez em: {(ja.get('last_checked_at') or '')[:10]}\n\n"
                f"Use `knowledge_base_search` com o termo da dúvida para achar o trecho "
                f"exato. Ao responder, informe a vigência acima — apólice emitida antes "
                f"dela pode ser regida por versão anterior."
            )

        r = await ler_pagina(url, supabase=self.supabase, company_id=self.company_id,
                             work_run_id=self.work_run_id)
        if not r.get("ok"):
            return f"Não foi possível ler o documento. Motivo: {r.get('mensagem_humana') or r.get('motivo')}"

        # Documento normativo lido ao vivo vira candidato do corpus. É o que
        # faz a primeira leitura ser a única: quem pagou por ela paga uma vez,
        # e todas as outras corretoras passam a ter a resposta de graça.
        if corpus is not None:
            try:
                corpus.propor_candidato(url=url, titulo=r.get("titulo") or "",
                                        texto=r.get("conteudo") or "")
            except Exception:  # noqa: BLE001
                pass

        corpo = (r.get("conteudo") or "")[:LIMITE_CONTEUDO]
        aviso = ""
        if len(r.get("conteudo") or "") > LIMITE_CONTEUDO:
            # Truncar em silêncio faria o agente responder "não consta" sobre
            # algo que consta na parte que ele não recebeu.
            aviso = ("\n\n[Documento truncado nesta leitura. Se a resposta puder estar "
                     "em uma parte não lida, diga isso em vez de afirmar que não consta.]")
        return f"# {r.get('titulo') or 'Documento'}\nFonte: {r.get('url')}\n\n{corpo}{aviso}"


class DeepSearchTool(_Base):
    name: str = "web_search_deep"
    description: str = (
        "Pesquisa na internet e já devolve o TEXTO das fontes encontradas, em uma chamada. "
        "Use para dossiê e análise que precisam citar a fonte. Para uma pergunta simples, "
        "prefira web_search, que é mais barata. Consome crédito por fonte."
    )
    args_schema: Type[BaseModel] = _BuscaIn

    async def _arun(self, query: str, limit: int = 4, **_: Any) -> str:
        from ...services.research.firecrawl import pesquisar_com_fontes

        r = await pesquisar_com_fontes(query, limite=limit, supabase=self.supabase,
                                       company_id=self.company_id, work_run_id=self.work_run_id)
        if not r.get("ok"):
            return f"A pesquisa profunda não está disponível agora ({r.get('motivo')})."
        itens = r.get("resultados") or []
        if not itens:
            return "A pesquisa não encontrou fontes para essa consulta."

        partes = []
        for i, x in enumerate(itens, 1):
            partes.append(
                f"## Fonte {i}: {x.get('titulo') or '(sem título)'}\n"
                f"URL: {x.get('url')}\n"
                f"{x.get('resumo') or ''}\n\n{(x.get('conteudo') or '')[:18_000]}")
        return "\n\n---\n\n".join(partes)


def ferramentas_de_leitura_profunda(*, company_id: Optional[str] = None,
                                    supabase: Any = None,
                                    work_run_id: Optional[str] = None) -> list[BaseTool]:
    """As três, ou nenhuma se o Firecrawl não estiver configurado.

    Nenhuma é melhor do que uma ferramenta que sempre responde "não configurado":
    tool quebrada no catálogo gasta token em toda invocação e ensina o modelo a
    tentar de novo.
    """
    from ...services.research.firecrawl import configurado

    if not configurado():
        return []
    comum = {"company_id": company_id, "supabase": supabase, "work_run_id": work_run_id}
    return [WebScrapeTool(**comum), DeepSearchTool(**comum), DocumentReadTool(**comum)]
