"""Geração de relatório pelo chat. SPEC-057 §Bloco I.

É onde tudo desde a SPEC-054 vira algo que o corretor vê: ele pede "me faz o
panorama do mês" e recebe uma peça com a marca da corretora dele, pronta para
mandar ao cliente.

O contrato com o modelo
-----------------------
O agente entrega **conteúdo**: título, veredito, indicadores, seções, ações,
fontes. Ele **não** escolhe bloco, não escreve CSS, não decide cor. Essa
separação não é preciosismo — é o que garante que a décima peça saia tão boa
quanto a primeira. Qualidade visual que depende do modelo acertar o layout é
qualidade que varia com a temperatura.

Honestidade
-----------
`fontes` é obrigatório e a ferramenta recusa sem ele. Um relatório bonito com
número sem procedência é pior do que nenhum relatório: ele convence sem poder
ser conferido, e do outro lado tem um corretor decidindo o que falar para o
cliente.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

TIPOS_ACEITOS = (
    "executive.panorama", "financial.commissions", "commercial.pipeline",
    "research.market_brief", "portfolio.client_dossier", "renewals.radar",
    "claims.performance", "briefing.daily",
)


class _Indicador(BaseModel):
    rotulo: str = Field(description="Nome curto do indicador. Ex.: 'Prêmio emitido'")
    valor: str = Field(description="Valor já formatado. Ex.: 'R$ 1,28 mi' ou '87,2'")
    unidade: Optional[str] = Field(default=None, description="Ex.: '%', 'mil', 'dias'")
    variacao: Optional[float] = Field(
        default=None, description="Variação percentual contra a base. Ex.: 12.4 ou -3.1")
    base: Optional[str] = Field(
        default=None, description="Contra o que se compara. Ex.: 'vs. junho'. "
                                  "Obrigatório sempre que houver variação.")
    melhor: Optional[str] = Field(
        default=None,
        description="'up' se subir é bom, 'down' se cair é bom. Use 'down' em "
                    "sinistralidade, inadimplência e prazo — senão o relatório "
                    "pinta melhora de vermelho.")


class _Secao(BaseModel):
    tipo: str = Field(
        description="tabela | ranking | rosca | texto | alerta. Escolha pelo dado: "
                    "tabela para precisão, ranking para comparar, rosca para "
                    "composição, texto para argumento, alerta para risco.")
    titulo: str
    chapeu: Optional[str] = Field(default=None, description="Rótulo pequeno acima do título")
    texto: Optional[str] = Field(default=None, description="Para tipo=texto ou alerta")
    tom: Optional[str] = Field(
        default=None, description="Para alerta: info | warning | negative | positive")
    colunas: Optional[list[dict]] = Field(
        default=None, description="Para tabela: [{key, label, align?, format?}]. "
                                  "format: currency | percent | number")
    linhas: Optional[list[dict]] = Field(default=None, description="Para tabela")
    itens: Optional[list[dict]] = Field(
        default=None, description="Para ranking/rosca: [{rotulo, valor, nota?}]")
    formato_valor: Optional[str] = Field(
        default=None, description="currency | currency_short | percent | number | short")


class _Acao(BaseModel):
    titulo: str
    detalhe: Optional[str] = None
    responsavel: Optional[str] = None
    prazo: Optional[str] = None
    impacto: Optional[str] = Field(default=None, description="Ex.: 'R$ 312 mil'")


class _Fonte(BaseModel):
    rotulo: str = Field(description="De onde veio. Ex.: 'Carteira', 'Comissões'")
    detalhe: str = Field(description="Qual base exatamente")
    data: Optional[str] = Field(default=None, description="A que data o dado se refere")


class RelatorioIn(BaseModel):
    tipo: str = Field(description=f"Um de: {', '.join(TIPOS_ACEITOS)}")
    titulo: str = Field(description="O título é uma AFIRMAÇÃO, não um rótulo. "
                                    "'A carteira cresceu mas frota está travando', "
                                    "não 'Relatório de julho'.")
    veredito: str = Field(description="Uma frase que responde 'e daí?'. É o que o "
                                      "leitor lê primeiro e às vezes só.")
    subtitulo: Optional[str] = None
    periodo: Optional[str] = Field(default=None, description="Ex.: 'Julho de 2026'")
    destaque_rotulo: Optional[str] = None
    destaque_valor: Optional[str] = None
    destaque_variacao: Optional[float] = None
    indicadores: list[_Indicador] = Field(default_factory=list)
    secoes: list[_Secao] = Field(default_factory=list)
    acoes: list[_Acao] = Field(default_factory=list)
    fontes: list[_Fonte] = Field(
        description="OBRIGATÓRIO. De onde vieram os números. Sem isto o "
                    "relatório não é gerado.")
    compartilhar: bool = Field(
        default=False,
        description="true gera link público válido por 30 dias, com a marca da "
                    "corretora. Use só quando o corretor pedir para enviar a alguém.")


_MAPA_SECAO = {
    "tabela": "table", "ranking": "ranking", "rosca": "donut",
    "texto": "prose", "alerta": "callout",
}


def _compor(dados: RelatorioIn) -> list[dict]:
    """Traduz conteúdo em composição de blocos. O modelo não faz isto."""
    blocos: list[dict] = [{
        "block": "cover",
        "props": {
            "eyebrow": "Relatório", "title": dados.titulo,
            "subtitle": dados.subtitulo, "period": dados.periodo,
            "verdict": dados.veredito,
            "headline_label": dados.destaque_rotulo,
            "headline_value": dados.destaque_valor,
            "headline_delta": dados.destaque_variacao,
        },
    }]

    if dados.indicadores:
        blocos.append({"block": "kpis", "props": {
            "title": "Os números", "items": [{
                "label": i.rotulo, "value": i.valor, "unit": i.unidade,
                "delta": i.variacao, "since": i.base, "better": i.melhor or "up",
            } for i in dados.indicadores[:6]],
        }})

    # O veredito aparece na capa e de novo como bloco só quando há muita coisa
    # depois — repetir numa peça curta seria eco.
    if dados.veredito and (len(dados.secoes) + len(dados.acoes)) >= 3:
        blocos.append({"block": "verdict", "props": {"text": dados.veredito}})

    for s in dados.secoes[:8]:
        bloco = _MAPA_SECAO.get((s.tipo or "").lower())
        if not bloco:
            continue
        props: dict[str, Any] = {"title": s.titulo, "eyebrow": s.chapeu}
        if bloco == "table":
            props["columns"] = s.colunas or []
            props["rows"] = s.linhas or []
        elif bloco in ("ranking", "donut"):
            chave = "items" if bloco == "ranking" else "slices"
            props[chave] = s.itens or []
            props["value_type"] = s.formato_valor or "number"
        elif bloco == "prose":
            props["text"] = s.texto or ""
        elif bloco == "callout":
            props["text"] = s.texto or ""
            props["tone"] = s.tom or "info"
            props["title"] = s.titulo
        blocos.append({"block": bloco, "props": props})

    if dados.acoes:
        blocos.append({"block": "actions", "props": {
            "eyebrow": "Plano", "title": "O que fazer",
            "items": [{"title": a.titulo, "detail": a.detalhe,
                       "owner": a.responsavel, "due": a.prazo,
                       "impact": a.impacto} for a in dados.acoes[:8]],
        }})

    blocos.append({"block": "sources", "props": {}})
    blocos.append({"block": "footer", "props": {}})
    return blocos


class GerarRelatorioTool(BaseTool):
    name: str = "gerar_relatorio"
    description: str = (
        "Gera um relatório profissional com a identidade visual da corretora e devolve "
        "o link. Use quando o corretor pedir um relatório, panorama, dossiê, briefing ou "
        "análise para apresentar. Você fornece o CONTEÚDO (título, veredito, indicadores, "
        "seções, ações, fontes) — o sistema cuida do layout. "
        "O campo 'fontes' é obrigatório: todo número precisa dizer de onde veio."
    )
    args_schema: Type[BaseModel] = RelatorioIn

    company_id: Optional[str] = None
    supabase: Any = None
    user_id: Optional[str] = None
    work_run_id: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True

    def _run(self, **_: Any) -> str:
        return "Esta ferramenta é assíncrona; o runtime deve chamá-la por `arun`."

    async def _arun(self, **kwargs: Any) -> str:
        import os

        try:
            dados = RelatorioIn(**kwargs)
        except Exception as exc:  # noqa: BLE001
            return f"Não consegui montar o relatório com esses dados: {exc}"

        if not dados.fontes:
            return ("Não gerei o relatório: falta dizer de onde vieram os números. "
                    "Preencha 'fontes' com as bases usadas — um relatório sem "
                    "procedência não pode ser conferido por quem recebe.")

        if dados.tipo not in TIPOS_ACEITOS:
            return (f"Tipo '{dados.tipo}' não existe. Use um destes: "
                    f"{', '.join(TIPOS_ACEITOS)}.")

        if not self.company_id or self.supabase is None:
            return "Não consegui identificar a corretora para gerar o relatório."

        from ...services.artifacts.service import ArtifactService

        svc = ArtifactService(self.supabase)
        try:
            criado = svc.criar(
                company_id=self.company_id, title=dados.titulo,
                template_key=dados.tipo, payload=dados.model_dump(),
                composition=_compor(dados), subtitle=dados.subtitulo,
                summary=dados.veredito, origin="chat",
                work_run_id=self.work_run_id, requested_by=self.user_id,
                data_sources=[{"label": f.rotulo, "detail": f.detalhe,
                               "as_of_label": f.data} for f in dados.fontes],
            )
            render = svc.renderizar(company_id=self.company_id,
                                    version_id=criado["version"]["id"])
            svc.publicar(company_id=self.company_id,
                         version_id=criado["version"]["id"], user_id=self.user_id)
        except ValueError as exc:
            return f"Não consegui publicar o relatório: {exc}"
        except Exception as exc:  # noqa: BLE001
            logger.exception("[Relatorio] falhou")
            return (f"Houve uma falha ao gerar o relatório ({type(exc).__name__}). "
                    "Tente de novo em instantes.")

        marca_padrao = (criado.get("brand") or {}).get("is_fallback")
        base = (os.getenv("PUBLIC_APP_URL") or os.getenv("NEXT_PUBLIC_APP_URL") or "").rstrip("/")

        partes = [f"Relatório **{dados.titulo}** gerado."]

        if dados.compartilhar:
            try:
                s = svc.compartilhar(
                    company_id=self.company_id, artifact_id=criado["artifact"]["id"],
                    version_id=criado["version"]["id"], dias=30, user_id=self.user_id)
                if base:
                    partes.append(f"Link para enviar (válido por 30 dias): {base}/r/{s['token']}")
                else:
                    partes.append("Link criado, válido por 30 dias.")
            except Exception:  # noqa: BLE001
                partes.append("O relatório ficou pronto, mas não consegui criar o "
                              "link de compartilhamento agora.")

        if marca_padrao:
            # Dizer isto é obrigatório: o corretor precisa saber que a peça saiu
            # com a identidade padrão antes de mandá-la a um cliente.
            partes.append(
                "Atenção: a peça saiu com a identidade padrão porque a marca da "
                "corretora ainda não foi montada. Em Personalização › Corretora › "
                "Identidade, informe o site e clique em *Montar identidade* — os "
                "próximos relatórios já saem com o logo e as cores de vocês.")

        diag = render.get("diagnostico") or {}
        if diag.get("falhas"):
            partes.append("Algumas partes não puderam ser montadas e ficaram de fora.")

        return " ".join(partes)


def ferramenta_de_relatorio(*, company_id: Optional[str], supabase: Any,
                            user_id: Optional[str] = None,
                            work_run_id: Optional[str] = None) -> list[BaseTool]:
    if not company_id or supabase is None:
        return []
    return [GerarRelatorioTool(company_id=company_id, supabase=supabase,
                               user_id=user_id, work_run_id=work_run_id)]
