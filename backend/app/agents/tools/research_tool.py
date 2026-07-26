"""Pesquisa pelo chat. SPEC-060 §30.3 e §36.

O corretor pede *"pesquise o que mudou na SUSEP"* e recebe fontes com data —
não um texto plausível. É a diferença entre pesquisa e improviso.

Três ferramentas, não dez
------------------------
§32.3 nomeia dez operações. No chat elas chegam agrupadas em três, pelo mesmo
motivo registrado em CA-010 na SPEC-059: o Tool Gateway tem teto de 12
ferramentas por execução (SPEC-053 §13.1), e o Core já carrega perto disso.
Todas as dez operações continuam disponíveis pelas APIs de §32.1.

O contrato com o modelo
-----------------------
Estas ferramentas devolvem texto **já com as fontes e as limitações**. O
modelo apresenta; não completa lacuna, não arredonda, não transforma "não
encontrei" em "provavelmente é assim". Se a ferramenta disser que o provedor
está sem crédito, essa frase é para ser repassada.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class _PesquisarIn(BaseModel):
    pergunta: str = Field(
        description="A pergunta do corretor, nas palavras dele. Não reescreva.")
    rigor: str = Field(
        default="auto",
        description="'auto' na dúvida. 'rapido' para pergunta simples; "
                    "'verificado' quando envolver regra, cobertura, prazo ou "
                    "norma; 'profundo' para dossiê ou comparação.")


class PesquisarTool(BaseTool):
    name: str = "pesquisar_na_web"
    description: str = (
        "Pesquisa informação ATUAL na internet com fontes rastreáveis e data. "
        "Use quando o corretor perguntar sobre mudanças na SUSEP, legislação, "
        "novidade de seguradora, notícia, produto de mercado ou qualquer coisa "
        "que você não sabe de cor e que muda com o tempo. "
        "Devolve as afirmações com a fonte de cada uma. NÃO invente nada além "
        "do que vier aqui: se a ferramenta disser que não encontrou, diga isso."
    )
    args_schema: Type[BaseModel] = _PesquisarIn

    company_id: Optional[str] = None
    supabase: Any = None
    user_id: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True

    def _run(self, **_: Any) -> str:
        return "Ferramenta assíncrona; o runtime deve chamá-la por `arun`."

    async def _arun(self, pergunta: str, rigor: str = "auto", **_: Any) -> str:
        if not self.company_id or self.supabase is None:
            return "Não consegui identificar a corretora para pesquisar."

        from ...services.research.orchestrator import pesquisar
        from ...services.research.planner import resolver_modo

        mapa = {"rapido": "quick", "verificado": "verified", "profundo": "deep"}
        modo = mapa.get(str(rigor).lower()) or resolver_modo(pergunta)

        # Pesquisa profunda pelo chat vira Work Run: ela dura minutos, e
        # segurar a conversa esperando é pior do que avisar e entregar depois.
        if modo == "deep":
            return await self._agendar_profunda(pergunta)

        try:
            r = await pesquisar(self.supabase, company_id=self.company_id,
                                pergunta=pergunta, modo=modo,
                                user_id=self.user_id, origem="user")
        except Exception as exc:  # noqa: BLE001
            logger.exception("[Research] pesquisa falhou")
            return (f"Não consegui pesquisar agora ({type(exc).__name__}). "
                    "Diga isso ao corretor sem inventar a resposta.")

        return formatar(r)

    async def _agendar_profunda(self, pergunta: str) -> str:
        import asyncio

        from ...services.work.runs import WorkRunService

        def _criar() -> dict:
            return WorkRunService(self.supabase).criar(
                company_id=str(self.company_id), source_type="research",
                source_id=None, outcome_type="research.request",
                outcome_title=pergunta[:180],
                workflow_key="research.execute",
                idempotency_key=f"research:{self.company_id}:{abs(hash(pergunta.lower().strip()))}",
                input_payload={"pergunta": pergunta, "modo": "deep",
                               "user_id": self.user_id, "origem": "user"},
                requester_user_id=self.user_id, priority=45, risk_level="low")

        try:
            r = await asyncio.to_thread(_criar)
        except Exception as exc:  # noqa: BLE001
            return (f"Não consegui abrir a pesquisa profunda ({type(exc).__name__}).")

        if r.get("reused"):
            return ("Essa pesquisa já está rodando. Assim que terminar, o "
                    "resultado aparece em Pesquisas.")
        return ("Comecei uma pesquisa profunda sobre isso. Ela lê várias fontes "
                "e monta um dossiê com procedência — leva alguns minutos. "
                "Avise ao corretor que o resultado vai aparecer em Pesquisas.")


def formatar(resultado: Any) -> str:
    """Resultado → texto para o chat. Puro, e sem número novo."""
    claims = getattr(resultado, "claims", []) or []
    sustentados = [c for c in claims
                   if c.get("status") in ("supported", "partially_supported")]

    if not sustentados:
        linhas = [resultado.resumo or "Não encontrei fonte com procedência."]
        for l in (resultado.limitacoes or [])[:3]:
            linhas.append(f"• {l}")
        linhas.append(
            "\n[Diga isso ao corretor com suas palavras. NÃO responda a "
            "pergunta de cabeça: o ponto da ferramenta é ter fonte.]")
        return "\n".join(linhas)

    linhas = [f"**O que as fontes dizem** ({len(sustentados)} afirmação(ões))", ""]
    for c in sustentados[:8]:
        marca = "🏛️" if int(c.get("official_citation_count") or 0) else "•"
        linhas.append(f"{marca} {str(c.get('claim_text') or '')[:400]}")
        detalhes = []
        if int(c.get("official_citation_count") or 0):
            detalhes.append("fonte oficial")
        elif c.get("citation_count"):
            detalhes.append(f"{c['citation_count']} fonte(s)")
        if c.get("confidence") is not None:
            detalhes.append(f"confiança {float(c['confidence']) * 100:.0f}%")
        if c.get("status") == "partially_supported":
            detalhes.append("sustentação parcial")
        if detalhes:
            linhas.append(f"   _{' · '.join(detalhes)}_")

    fontes = getattr(resultado, "fontes", []) or []
    if fontes:
        linhas.append("")
        linhas.append("**Fontes**")
        for f in fontes[:6]:
            rotulo = f.get("titulo") or f.get("url") or "fonte"
            marca = " (oficial)" if f.get("oficial") else ""
            linhas.append(f"• {rotulo}{marca} — {f.get('url')}")

    if getattr(resultado, "contradicoes", None):
        linhas.append("")
        linhas.append(
            f"⚠️ As fontes divergem em {len(resultado.contradicoes)} ponto(s). "
            "Mostre os dois lados ao corretor.")

    if resultado.limitacoes:
        linhas.append("")
        linhas.append("**O que isto não afirma**")
        for l in resultado.limitacoes[:4]:
            linhas.append(f"• {l}")

    linhas.append("")
    linhas.append(
        "[Apresente com suas palavras, mantendo as afirmações como estão e "
        "citando as fontes. Não acrescente conclusão que não esteja acima.]")
    return "\n".join(linhas)


# ---------------------------------------------------------------------------


class _MonitorIn(BaseModel):
    nome: str = Field(description="Como o corretor chamaria isso. Ex.: 'Circulares da SUSEP'")
    enderecos: list[str] = Field(
        description="URLs a acompanhar. Se o corretor não deu, pergunte antes.")
    frequencia: str = Field(default="daily",
                            description="hourly, daily, weekly ou monthly")
    termos: list[str] = Field(
        default_factory=list,
        description="Palavras que tornam a mudança relevante. Ex.: cobertura, vigência.")


class MonitorarTool(BaseTool):
    name: str = "monitorar_fonte"
    description: str = (
        "Cria um acompanhamento recorrente de páginas — norma, seguradora, "
        "concorrente. O corretor é avisado SÓ quando muda algo relevante; "
        "mudança de banner e data automática são ignoradas. "
        "Use quando ele disser 'me avise quando', 'monitore' ou 'fique de olho'. "
        "Peça os endereços se ele não tiver dito quais."
    )
    args_schema: Type[BaseModel] = _MonitorIn

    company_id: Optional[str] = None
    supabase: Any = None
    user_id: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True

    def _run(self, **_: Any) -> str:
        return "Ferramenta assíncrona; o runtime deve chamá-la por `arun`."

    async def _arun(self, nome: str, enderecos: list[str],
                    frequencia: str = "daily",
                    termos: Optional[list[str]] = None, **_: Any) -> str:
        import asyncio

        if not self.company_id or self.supabase is None:
            return "Não consegui identificar a corretora."
        if not enderecos:
            return ("Preciso de pelo menos um endereço para acompanhar. "
                    "Pergunte ao corretor qual página ele quer monitorar.")

        from ...services.research.monitor_service import MonitorService

        def _criar() -> dict:
            return MonitorService(self.supabase).criar(
                company_id=str(self.company_id), nome=nome, urls=enderecos,
                cadencia=frequencia if frequencia in
                ("hourly", "daily", "weekly", "monthly") else "daily",
                user_id=self.user_id, termos=termos or [])

        try:
            r = await asyncio.to_thread(_criar)
        except Exception as exc:  # noqa: BLE001
            return f"Não consegui criar o acompanhamento ({type(exc).__name__})."

        if not r.get("ok"):
            return str(r.get("erro") or "Não consegui criar o acompanhamento.")

        quantos = len(enderecos)
        return (f"Pronto: vou acompanhar {quantos} endereço(s) "
                f"({'todo dia' if frequencia == 'daily' else frequencia}) e avisar "
                f"só quando mudar algo que importa. Mudança de banner, data e "
                f"contador de visitas não geram aviso.")


# ---------------------------------------------------------------------------


class _AuditarIn(BaseModel):
    site: str = Field(description="Endereço do site a analisar")


class AuditarSiteTool(BaseTool):
    name: str = "analisar_site"
    description: str = (
        "Analisa um site e diz o que está no caminho de ele ser encontrado no "
        "Google e citado por assistentes de IA. Use quando o corretor pedir "
        "para analisar o site dele, falar de SEO, ou perguntar por que não "
        "aparece nas buscas. Devolve pontos verificáveis e por onde começar — "
        "nunca promete posição no ranking."
    )
    args_schema: Type[BaseModel] = _AuditarIn

    company_id: Optional[str] = None
    supabase: Any = None
    user_id: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True

    def _run(self, **_: Any) -> str:
        return "Ferramenta assíncrona; o runtime deve chamá-la por `arun`."

    async def _arun(self, site: str, **_: Any) -> str:
        if not self.company_id or self.supabase is None:
            return "Não consegui identificar a corretora."

        from ...services.research.site_audit import SiteAudit

        try:
            r = await SiteAudit(self.supabase,
                                company_id=str(self.company_id)).auditar_site(
                site, max_paginas=10)
        except Exception as exc:  # noqa: BLE001
            logger.exception("[Research] auditoria falhou")
            return f"Não consegui analisar o site agora ({type(exc).__name__})."

        if not r.get("ok"):
            linhas = [str(r.get("erro") or "Não consegui abrir o site.")]
            linhas.extend(f"• {l}" for l in (r.get("limitacoes") or [])[:3])
            return "\n".join(linhas)

        resumo = r.get("resumo") or {}
        linhas = [
            f"**Analisei {resumo.get('paginas_analisadas', 0)} página(s)**",
            f"{resumo.get('achados', 0)} ponto(s) encontrados, "
            f"{resumo.get('achados_de_alto_impacto', 0)} de alto impacto.",
            "",
        ]
        for a in (r.get("achados") or [])[:6]:
            linhas.append(f"• **{a['titulo']}** ({a['impacto']} impacto, "
                          f"esforço {a['esforco']})")
            linhas.append(f"   {a['detalhe']}")
            if a.get("evidencia"):
                linhas.append(f"   _encontrado: {a['evidencia']}_")

        if r.get("limitacoes"):
            linhas.append("")
            linhas.append("**Limitações desta análise**")
            for l in r["limitacoes"][:3]:
                linhas.append(f"• {l}")

        linhas.append("")
        linhas.append(
            "[Apresente na ordem acima — ela já está priorizada por impacto e "
            "esforço. NÃO prometa posição no Google nem citação por IA: "
            "ninguém controla isso.]")
        return "\n".join(linhas)


# ---------------------------------------------------------------------------


def ferramentas_de_pesquisa(*, company_id: Optional[str], supabase: Any,
                            user_id: Optional[str] = None) -> list[BaseTool]:
    if not company_id or supabase is None:
        return []
    comum = {"company_id": company_id, "supabase": supabase, "user_id": user_id}
    return [PesquisarTool(**comum), MonitorarTool(**comum),
            AuditarSiteTool(**comum)]
