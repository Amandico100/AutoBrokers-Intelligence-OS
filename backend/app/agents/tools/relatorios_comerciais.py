# -*- coding: utf-8 -*-
"""Raio-X Comercial e Radar por vendedor, pedidos no chat — SPEC-081 C e D.

## A inversão que define este arquivo

> **O modelo escolhe O QUE fazer. O código FAZ.**

📊 A ferramenta `gerar_relatorio` que já existe nunca produziu um artifact:
`select origin, count(*) from artifacts` → `routine: 40`, **`chat: 0`**. Três
defeitos em série, e o de fundo é o desenho: ela pede ao LLM que **invente o
conteúdo** do relatório — indicadores, seções, veredito — e depois valida.

Aqui o LLM faz uma coisa só: reconhece a intenção e escolhe o período. Busca,
cruzamento, cálculo, composição e publicação são código determinístico. O
mesmo pedido duas vezes produz o mesmo número.

## Por que não passa pelo `report_tool`

📊 A Cobrança gera artifact por outro caminho — `ArtifactService.criar(...,
composition=blocos) → renderizar → publicar` (`billing_collection.py:1369`) —
e esse caminho tem 40 execuções provadas.

`report_tool._compor()` só sabe traduzir **5** tipos de seção; passar a
composição pronta destrava os **17 blocos** e os **9 gráficos** que já existem.
Não é motor paralelo: é o mesmo `ArtifactService`, chamado do jeito que já
funciona.

## O que sai daqui

Uma frase em markdown com **o link**. Sempre. Mesmo quando a InfoCap falha, o
retorno diz ao modelo o que dizer ao corretor — nunca um `Exception` cru, que
foi o que fez a atendente inventar que tinha transferido um caso em 17/08.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import date, datetime
from typing import Any, ClassVar, Dict, List, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# 🔴 IMPORT TARDIO, e o pacote mora em `app/comercial/` e nao em
# `app/services/comercial/`. As duas coisas pelo mesmo motivo.
#
# 📊 `app/services/__init__.py` importa EAGER toda a arvore de servicos:
# `audio_service` puxa o SDK da OpenAI, `document_service` puxa `python-docx`,
# e assim por diante. Quem consome UM servico paga por TODOS.
#
# Para este modulo isso seria duas coisas ruins ao mesmo tempo: ele e
# carregado na MONTAGEM DO GRAFO, a cada conversa; e um relatorio de comissao
# passaria a depender de o leitor de .docx importar. 📊 Foi exatamente o que
# aconteceu ao rodar o teste ponta a ponta: `ModuleNotFoundError: docx`, num
# codigo que nao le documento nenhum.
#
# `app/comercial/` fica ao lado de `agents`, `api`, `core`, `providers` e
# `tasks` — os onze pacotes de topo, todos com `__init__` vazio. 📊
# `app/__init__.py` tem tres linhas.
#
# Consertar o `services/__init__.py` seria melhor ainda, e nao e para a
# vespera de uma apresentacao: ele e importado por tudo.
def _comercial():
    from app.comercial import calculos as calc
    from app.comercial.fonte_infocap import (
        FalhaDaInfocap, FonteInfocap, anos_de_vencimento_para,
    )
    return calc, FonteInfocap, FalhaDaInfocap, anos_de_vencimento_para

# 🔴 A peça sai no tema do TEMPLATE, e o template da Cobrança é `aurora`.
# Não passamos `visual_style` na renderização de propósito: 📊
# `service.py:187` resolve `pedido || marca.visual_style || template`, e
# forçar um tema aqui seria a mesma armadilha que trocaria o visual das peças
# da Cobrança pelo outro lado.
# 🔴 OS NOMES DE PROPRIEDADE SAO DO RENDERIZADOR, NAO MEUS.
#
# 📊 A primeira versao publicou tres pecas com SETE caixas escritas
# "Sem dado no periodo" e ZERO barras -- capa sem o numero, linha do mes a
# mes vazia, ranking vazio, tres roscas vazias. Todos os numeros estavam
# calculados e corretos; eram descartados na renderizacao.
#
# A causa e que `blocks.py` e `charts.py` misturam idiomas, e eu passei
# ingles em tudo:
#
#   cover    headline_value / headline_label   (nao `highlight`)
#   kpis     item.since                        (nao `base`)
#   chart    props.labels + series[].values    (nao `points` [{x,y}])
#   ranking  items[].{rotulo, valor}           (nao `label`/`value`)
#   donut    props.slices[].{rotulo, valor}    (nao `items`)
#
# 📊 A Cobranca acerta (`billing_collection.py:1262`) -- entao o contrato e
# real e conhecido, so nao estava escrito em lugar nenhum.
#
# 🔴 E 32 assercoes verdes NAO pegaram: o teste conferia que o NOME do bloco
# existia em `blocks.py`, nunca as propriedades dentro dele. Nome de bloco
# certo com propriedade errada renderiza uma caixa vazia, e uma caixa vazia
# num projetor e pior que bloco nenhum.

_TEMPLATE_RAIO_X = "commercial.pipeline"
_TEMPLATE_RADAR = "renewals.radar"


# --------------------------------------------------------------------------
# Entrada — uma coisa só: o período, em português
# --------------------------------------------------------------------------
class PeriodoIn(BaseModel):
    periodo: str = Field(
        default="",
        description=(
            "O período que o corretor pediu, COMO ELE FALOU. Exemplos que "
            "funcionam: '2025', 'este ano', 'ano passado', 'últimos 12 meses', "
            "'primeiro semestre', 'agosto', '3o trimestre', 'próximos 90 dias', "
            "'de 01/03/2026 a 30/06/2026'. Se ele não disse período, mande "
            "string vazia — o relatório sai no padrão e a capa avisa qual "
            "período usou. NUNCA pergunte o período de volta."),
    )


# --------------------------------------------------------------------------
# Ajudantes
# --------------------------------------------------------------------------
def _reais(v: float) -> str:
    calc, *_ = _comercial()
    return calc._reais(v)


def _slug_da_empresa(supabase, company_id: str) -> str:
    """O slug que resolve a credencial da InfoCap, a partir do NOME.

    🔴 📊 NAO EXISTE coluna `slug` em `companies`. A primeira versao pedia
    `select("slug, company_name")`, o PostgREST devolvia `APIError`, o
    `except` engolia num aviso e devolvia string vazia — e o erro so aparecia
    tres chamadas adiante como "a corretora ? nao tem credencial", que nao
    diz nada sobre a causa.

    📊 As colunas que existem: `company_name`, `legal_name`, `cnpj`.

    A regra e a PRIMEIRA PALAVRA do nome, normalizada — o mesmo padrao do
    Cartografo (`build_cartographer_dataset.py:170`):

        "Resulta Seguros"  ->  resulta   ->  CORP_INFOCAP_RESULTA_*
        "AutoFleet"        ->  autofleet ->  CORP_INFOCAP_AUTOFLEET_*

    E falha ALTO. Corretora sem credencial e um fato que quem le o relatorio
    precisa saber; devolver vazio empurra o problema para longe da causa.
    """
    from app.comercial.fonte_infocap import FalhaDaInfocap

    try:
        r = (supabase.table("companies").select("company_name")
             .eq("id", company_id).limit(1).execute().data or [])
    except Exception as exc:  # noqa: BLE001
        raise FalhaDaInfocap(
            f"nao consegui ler a corretora {company_id} para descobrir a "
            f"credencial da InfoCap ({type(exc).__name__})") from exc
    if not r:
        raise FalhaDaInfocap(f"corretora {company_id} nao encontrada")

    from app.comercial import calculos as _c
    nome = _c._normalizar(r[0].get("company_name") or "")
    slug = nome.split(" ")[0] if nome else ""
    if not slug:
        raise FalhaDaInfocap(
            f"a corretora {company_id} nao tem nome — sem nome nao ha como "
            f"resolver a credencial da InfoCap")
    return slug

def _publicar(supabase, company_id: str, *, titulo: str, subtitulo: str,
              resumo: str, template: str, payload: Dict[str, Any],
              blocos: List[Dict[str, Any]]) -> Optional[str]:
    """Cria, renderiza e publica. O MESMO caminho da Cobrança."""
    from app.services.artifacts.service import ArtifactService

    servico = ArtifactService(supabase)
    r = servico.criar(
        company_id=company_id, title=titulo, template_key=template,
        payload=payload, composition=blocos, subtitle=subtitulo,
        summary=resumo, kind="report", origin="chat",
        work_run_id=None,
        subject_ref={"kind": "chat", "id": ""},
    )
    versao = (r.get("version") or {}).get("id")
    if not versao:
        return None
    servico.renderizar(company_id=company_id, version_id=versao)
    servico.publicar(company_id=company_id, version_id=versao)
    return ((r.get("artifact") or {}).get("id")) or None


def _link(artifact_id: str) -> str:
    """A URL da peça, para o corretor clicar.

    🔴 Sempre devolve link. 📊 A ferramenta antiga só devolvia URL quando
    `compartilhar=True`, e o default era `False` — no caminho padrão a
    resposta era "Relatório X gerado.", sem endereço nenhum.
    """
    base = (os.getenv("FRONTEND_URL") or os.getenv("PUBLIC_APP_URL")
            or os.getenv("NEXT_PUBLIC_APP_URL") or "").rstrip("/")
    caminho = f"/dashboard/entregas/{artifact_id}"
    return f"{base}{caminho}" if base else caminho


def _fontes(quando: str, extra: str = "") -> Dict[str, Any]:
    """O bloco de procedência.

    🔴 A hora vai DENTRO do `as_of_label`. 📊 `blocks.py:363` renderiza
    `<time datetime="{as_of}">{as_of_label or as_of}</time>` — o texto visível
    é o LABEL. Passar `as_of_label="consultado em"` imprimiria "consultado em"
    e esconderia a hora num atributo. A Cobrança já faz certo
    (`billing_collection.py:1350`).
    """
    itens = [{"label": "InfoCap · carteira da corretora",
              "detail": "produção, comissão e produtores, lidos no momento do pedido",
              "as_of_label": f"consultado em {quando}"}]
    if extra:
        itens.append({"label": "Observação", "detail": extra,
                      "as_of_label": f"consultado em {quando}"})
    return {"block": "sources", "props": {"items": itens}}


def _encurtar(nome: str, teto: int = 18) -> str:
    """Nome de produtor que cabe num rótulo de gráfico.

    🔴 📊 `charts.py:512` escreve o rótulo centralizado, sem elipse e sem
    rotação, com passo de `720/len(categorias)`. `RAFAEL LACAU SILVEIRA -
    FECHADOR` tem 32 caracteres e a 72 px de passo vira um borrão — justamente
    no quadro que mostra o mix por vendedor.
    """
    n = " ".join(str(nome or "").split())
    if len(n) <= teto:
        return n
    # O primeiro nome mais a inicial do papel ("RAFAEL · EXEC") diz mais que
    # os primeiros 18 caracteres crus.
    partes = n.replace("-", " ").split()
    if len(partes) >= 2:
        curto = f"{partes[0]} {partes[-1][:6]}"
        if len(curto) <= teto:
            return curto
    return n[: teto - 1] + "…"


def _erro_legivel(exc: Exception) -> str:
    """O que o modelo deve DIZER quando não deu.

    Instrução, não relato. 📊 Em 17/08 a atendente recebeu
    `Erro: HumanHandoffTool exige execução assíncrona` e, sem instrução de
    fala, inventou que tinha transferido o caso. Mensagem de erro que não diz
    o que NÃO aconteceu vira permissão para inventar que aconteceu.
    """
    # 🔴 NAO IMPORTA NADA AQUI. Este defeito foi pego pelo proprio teste:
    # a versao anterior fazia `_comercial()` para conseguir o `isinstance`, e
    # quando o que falhou FOI o import, o tratador de erro quebrava junto —
    # deixando o modelo sem nenhuma instrucao, que e exatamente a situacao
    # que este texto existe para evitar.
    #
    # Caminho de erro nao pode depender do que falhou. Compara pelo NOME da
    # classe, que nao precisa de import nenhum.
    da_infocap = type(exc).__name__ == "FalhaDaInfocap"
    motivo = str(exc)[:200] if da_infocap else type(exc).__name__
    return (
        "RELATORIO_FALHOU · o relatório NÃO foi gerado e NÃO existe link. "
        "É PROIBIDO afirmar ao cliente que o relatório está pronto ou mandar "
        "qualquer endereço. Diga a verdade: a consulta à InfoCap não "
        f"completou agora, e ofereça tentar de novo. Motivo interno: {motivo}"
    )


# ==========================================================================
# BLOCO C — Raio-X Comercial
# ==========================================================================
class RaioXComercialTool(BaseTool):
    """Quem vende, quanto rende, quanto custa."""

    exige_async: ClassVar[bool] = True

    name: str = "raio_x_comercial"
    description: str = (
        "Relatório de PRODUTIVIDADE COMERCIAL da corretora, com dados reais da "
        "InfoCap: ranking de vendedores por comissão, ticket médio, custo de "
        "aquisição por canal, mix de ramo, novo contra renovação e comparação "
        "com o período anterior. Devolve o LINK de um relatório visual pronto. "
        "Use quando o corretor pedir: raio-x comercial, produtividade dos "
        "vendedores, quem mais vende, ranking de vendedores, desempenho "
        "comercial, resultado comercial, quanto custa cada canal, comissão por "
        "vendedor. "
        "IMPORTANTE: antes de chamar, diga UMA frase curta ao corretor avisando "
        "que vai levantar os dados na InfoCap e que leva alguns segundos. "
        "Se ele não disser o período, mande string vazia — NUNCA pergunte de volta."
    )
    args_schema: Type[BaseModel] = PeriodoIn

    company_id: Optional[str] = None
    supabase: Any = None

    class Config:
        arbitrary_types_allowed = True

    def _run(self, **_: Any) -> str:
        # 🔴 Levanta de propósito. `exige_async` lá em cima é o que faz o
        # executor aguardar `_arun` (`nodes.py:1084`). Se alguém chegar aqui,
        # a declaração foi ignorada — e a mensagem diz o que fazer, em vez de
        # repetir uma promessa que ninguém cumpriu.
        raise RuntimeError(
            "RaioXComercialTool exige execução assíncrona. Quem chamou ignorou "
            "`exige_async=True` — o executor precisa aguardar `_arun`.")

    async def _arun(self, periodo: str = "", **_: Any) -> str:
        try:
            return await asyncio.to_thread(self._montar, periodo)
        except Exception as exc:  # noqa: BLE001
            logger.error("[RAIO-X] falhou (%s): %s", type(exc).__name__, exc)
            return _erro_legivel(exc)

    # ------------------------------------------------------------------ #
    def _montar(self, texto_do_periodo: str) -> str:
        calc, FonteInfocap, FalhaDaInfocap, anos_de_vencimento_para = _comercial()
        p = calc.entender_periodo(texto_do_periodo)
        slug = _slug_da_empresa(self.supabase, str(self.company_id or ""))
        fonte = FonteInfocap.para_empresa(slug)

        apolices = fonte.producao(p.inicio, p.fim)
        if not apolices:
            return (f"RELATORIO_VAZIO · não há produção registrada em {p.rotulo}. "
                    "Diga isso ao corretor e sugira outro período. Não invente número.")

        mapa = fonte.mapa_de_produtores(anos_de_vencimento_para(p.inicio, p.fim))

        ant = p.anterior()
        try:
            apolices_ant = fonte.producao(ant.inicio, ant.fim)
        except FalhaDaInfocap:
            # Comparação é enfeite; o relatório do período pedido não pode
            # morrer porque o ano anterior não respondeu.
            apolices_ant = []

        ranking = calc.ranking_por_produtor(apolices, mapa)
        cob = calc.cobertura(apolices, mapa)
        comp = calc.comparar(apolices, apolices_ant)
        serie = calc.serie_mensal(apolices)
        nr = calc.novo_versus_renovacao(apolices)
        por_ramo = calc.por_dimensao(apolices, "ramo", teto=8)
        agora = datetime.now().strftime("%d/%m/%Y às %H:%M")

        blocos = self._compor(p, ranking, cob, comp, serie, nr, por_ramo, agora)
        payload = {
            "periodo": {"inicio": str(p.inicio), "fim": str(p.fim), "rotulo": p.rotulo},
            "cobertura": {"apolices": cob.apolices_total,
                          "com_produtor": cob.apolices_com_produtor,
                          "pct": round(cob.pct_apolices, 1),
                          "pct_comissao": round(cob.pct_comissao, 1)},
            "ranking": [{"nome": x.nome, "apolices": x.apolices,
                         "comissao": round(x.comissao, 2),
                         "ticket": round(x.ticket, 2),
                         "custo_aquisicao_pct": round(x.custo_de_aquisicao, 1)}
                        for x in ranking],
            "comparacao": {k: round(v, 2) for k, v in comp.items()},
            "novo_vs_renovacao": {k: {"apolices": v[0], "comissao": round(v[1], 2)}
                                  for k, v in nr.items()},
            "serie_mensal": [{"mes": m, "apolices": n, "comissao": round(c, 2)}
                             for m, n, c in serie],
        }
        ident = _publicar(
            self.supabase, str(self.company_id),
            titulo=f"Raio-X Comercial · {p.rotulo}",
            subtitulo=f"Produção, comissão e produtividade por vendedor",
            resumo=(f"{cob.apolices_total} apólices, {_reais(cob.comissao_total)} de "
                    f"comissão, {len(ranking)} vendedores."),
            template=_TEMPLATE_RAIO_X, payload=payload, blocos=blocos)
        if not ident:
            return _erro_legivel(RuntimeError("o artifact não foi criado"))

        aviso = " (período padrão — o corretor não especificou)" if p.e_padrao else ""
        topo = ranking[0] if ranking else None
        return (
            f"RELATORIO_PRONTO · Raio-X Comercial de **{p.rotulo}**{aviso}.\n\n"
            f"[Abrir o relatório]({_link(ident)})\n\n"
            f"Resumo para você comentar: {cob.apolices_total} apólices, "
            f"{_reais(cob.comissao_total)} de comissão"
            + (f", liderado por {topo.nome} com {_reais(topo.comissao)}" if topo else "")
            + f". Cobertura de produtor: {cob.pct_apolices:.1f}%."
        )

    # ------------------------------------------------------------------ #
    def _compor(self, p, ranking, cob, comp, serie, nr, por_ramo, agora) -> List[Dict]:
        """A peça, bloco a bloco. Todos os 13 existem em `blocks.py`."""
        seta = "up" if comp["comissao_delta_pct"] >= 0 else "down"
        blocos: List[Dict[str, Any]] = [
            {"block": "cover", "props": {
                "eyebrow": "Raio-X Comercial",
                "title": f"Produção e produtividade · {p.rotulo}",
                "headline_value": _reais(comp["comissao_atual"]),
                "headline_label": "comissão no período",
                "period": p.rotulo,
            }},
            {"block": "kpis", "props": {"title": "O período em seis números", "items": [
                {"label": "Comissão", "value": _reais(comp["comissao_atual"]),
                 "delta": round(comp["comissao_delta_pct"], 1),
                 "direction": seta, "since": f"contra {_reais(comp['comissao_anterior'])}"},
                {"label": "Prêmio emitido", "value": _reais(comp["premio_atual"]),
                 "delta": round(comp["premio_delta_pct"], 1), "direction": seta},
                {"label": "Apólices", "value": f"{cob.apolices_total}",
                 "since": f"{int(comp['apolices_anterior'])} no período anterior"},
                {"label": "Vendedores", "value": f"{len(ranking)}"},
                {"label": "Negócio novo", "value": f"{nr['novo'][0]}",
                 "since": _reais(nr["novo"][1])},
                {"label": "Renovação", "value": f"{nr['renovacao'][0]}",
                 "since": _reais(nr["renovacao"][1])},
            ]}},
        ]

        # 🔴 A COBERTURA, em destaque. Um relatório que soma parte da carteira
        # e se apresenta como o todo mente por omissão.
        blocos.append({"block": "callout", "props": {
            "tone": "info", "title": "O que este relatório cobre",
            "text": cob.frase(),
        }})

        if len(serie) >= 2:
            blocos.append({"block": "chart", "props": {
                "eyebrow": "Ritmo", "title": "Comissão mês a mês",
                "labels": [m for m, _n, _c in serie],
                "series": [{"name": "Comissão",
                            "values": [round(c, 2) for _m, _n, c in serie]}],
                "value_type": "currency_short",
            }})

        if ranking:
            blocos.append({"block": "ranking", "props": {
                "eyebrow": "Quem vende", "title": "Vendedores por comissão gerada",
                "value_type": "currency_short",
                "items": [{"rotulo": _encurtar(x.nome, 22),
                           "valor": round(x.comissao, 2)}
                          for x in ranking[:12]],
            }})

            # 🔴 A TABELA QUE VALE A APRESENTAÇÃO: volume × valor × custo.
            blocos.append({"block": "table", "props": {
                "eyebrow": "Volume, valor e custo",
                "title": "Cada vendedor em três eixos",
                "columns": [
                    {"key": "nome", "label": "Vendedor"},
                    {"key": "apolices", "label": "Apólices", "format": "number"},
                    {"key": "comissao", "label": "Comissão", "format": "currency"},
                    {"key": "ticket", "label": "Ticket médio", "format": "currency"},
                    {"key": "custo", "label": "Repasse", "format": "percent"},
                ],
                "rows": [{"nome": x.nome, "apolices": x.apolices,
                          "comissao": round(x.comissao, 2),
                          "ticket": round(x.ticket, 2),
                          "custo": round(x.custo_de_aquisicao, 1)}
                         for x in ranking[:15]],
                "total": {"nome": "Total", "apolices": sum(x.apolices for x in ranking),
                          "comissao": round(sum(x.comissao for x in ranking), 2)},
            }})

        direita: List[Dict[str, Any]] = []
        if por_ramo:
            direita = [{"block": "donut", "props": {
                "title": "Comissão por ramo", "value_type": "currency_short",
                "slices": [{"rotulo": r, "valor": round(c, 2)} for r, _n, c in por_ramo],
            }}]
        if direita:
            blocos.append({"block": "split", "props": {
                "left": [{"block": "donut", "props": {
                    "title": "Novo contra renovação", "value_type": "currency_short",
                    "slices": [
                        {"rotulo": "Negócio novo", "valor": round(nr["novo"][1], 2)},
                        {"rotulo": "Renovação", "valor": round(nr["renovacao"][1], 2)},
                    ]}}],
                "right": direita,
            }})

        # O veredito é DETERMINÍSTICO: sai dos números já calculados.
        blocos.append({"block": "verdict", "props": {
            "text": self._veredito(ranking, cob, comp, nr)}})

        acoes = self._acoes(ranking)
        if acoes:
            blocos.append({"block": "actions", "props": {
                "title": "O que fazer com isto", "items": acoes}})

        blocos.append(_fontes(agora,
                              "Apólices canceladas, endossos e propostas ficam fora."))
        blocos.append({"block": "footer", "props": {
            "disclaimer": "Documento interno. Não contém CPF/CNPJ de segurado.",
        }})
        return blocos

    @staticmethod
    def _veredito(ranking, cob, comp, nr) -> str:
        """A frase de abertura, montada dos números — nunca inventada."""
        if not ranking:
            return (f"O período soma {_reais(cob.comissao_total)} de comissão, mas "
                    f"nenhuma apólice tem vendedor identificado.")
        topo = ranking[0]
        partes = [
            f"{_reais(comp['comissao_atual'])} de comissão no período, "
            f"{'alta' if comp['comissao_delta_pct'] >= 0 else 'queda'} de "
            f"{abs(comp['comissao_delta_pct']):.0f}% contra o anterior."
        ]
        # O contraste volume × valor, quando existe.
        por_ticket = sorted(ranking[:12], key=lambda x: -x.ticket)
        if por_ticket and por_ticket[0].nome != topo.nome and por_ticket[0].ticket > 3 * topo.ticket:
            v = por_ticket[0]
            partes.append(
                f"{topo.nome} lidera em volume ({topo.apolices} apólices), mas "
                f"{v.nome} tem ticket de {_reais(v.ticket)} — "
                f"{v.ticket / max(topo.ticket, 1):.0f}× maior — com apenas "
                f"{v.apolices} apólices.")
        # A amplitude do repasse, quando existe.
        grandes = [x for x in ranking if x.comissao > 20000 and x.custo_de_aquisicao > 0]
        if len(grandes) >= 2:
            menor = min(grandes, key=lambda x: x.custo_de_aquisicao)
            maior = max(grandes, key=lambda x: x.custo_de_aquisicao)
            if maior.custo_de_aquisicao - menor.custo_de_aquisicao >= 10:
                partes.append(
                    f"E o repasse varia de {menor.custo_de_aquisicao:.1f}% "
                    f"({menor.nome}) a {maior.custo_de_aquisicao:.1f}% "
                    f"({maior.nome}) — de cada real de comissão.")
        return " ".join(partes)

    @staticmethod
    def _acoes(ranking) -> List[Dict[str, Any]]:
        acoes: List[Dict[str, Any]] = []
        grandes = [x for x in ranking if x.comissao > 20000 and x.custo_de_aquisicao > 0]
        if grandes:
            caro = max(grandes, key=lambda x: x.custo_de_aquisicao)
            if caro.custo_de_aquisicao >= 15:
                acoes.append({
                    "title": f"Revisar o acordo com {caro.nome}",
                    "detail": (f"{caro.custo_de_aquisicao:.1f}% da comissão vai em "
                               f"repasse — {_reais(caro.repasse)} sobre "
                               f"{_reais(caro.comissao)}."),
                    "owner": "Sócio", "impact": _reais(caro.repasse)})
        pequenos = [x for x in ranking if 0 < x.apolices <= 10 and x.ticket > 10000]
        if pequenos:
            v = pequenos[0]
            acoes.append({
                "title": f"Entender o que {v.nome} faz diferente",
                "detail": (f"{v.apolices} apólices com ticket de {_reais(v.ticket)}. "
                           f"É o padrão que vale replicar."),
                "owner": "Comercial", "impact": _reais(v.comissao)})
        return acoes


# ==========================================================================
# BLOCO D — Radar de Renovações, POR PERÍODO e POR VENDEDOR
# ==========================================================================
class RadarDeRenovacoesTool(BaseTool):
    """O que vence, quanto vale, e de quem é.

    🔴 Pedido explícito do Founder: *"tem que ser por período, e separado por
    vendedor — quem tem mais renovações, comissões em jogo. Não do ano
    inteiro."*
    """

    exige_async: ClassVar[bool] = True

    name: str = "radar_de_renovacoes"
    description: str = (
        "Relatório do que VENCE num período, com dados reais da InfoCap: "
        "prêmio em risco, agenda por urgência e — o principal — SEPARADO POR "
        "VENDEDOR, mostrando quem tem mais renovações e quanto tem em jogo. "
        "Devolve o LINK de um relatório visual pronto. "
        "Use quando o corretor pedir: radar de renovações, o que vence, "
        "carteira a vencer, quem tem mais renovação, comissão em jogo nas "
        "renovações, vencimentos do mês, renovações por vendedor. "
        "IMPORTANTE: antes de chamar, diga UMA frase curta avisando que vai "
        "levantar os dados na InfoCap. Se ele não disser o período, mande "
        "string vazia — o padrão são os próximos 90 dias. NUNCA pergunte de volta."
    )
    args_schema: Type[BaseModel] = PeriodoIn

    company_id: Optional[str] = None
    supabase: Any = None

    class Config:
        arbitrary_types_allowed = True

    def _run(self, **_: Any) -> str:
        raise RuntimeError(
            "RadarDeRenovacoesTool exige execução assíncrona. Quem chamou "
            "ignorou `exige_async=True` — o executor precisa aguardar `_arun`.")

    async def _arun(self, periodo: str = "", **_: Any) -> str:
        try:
            return await asyncio.to_thread(self._montar, periodo)
        except Exception as exc:  # noqa: BLE001
            logger.error("[RADAR] falhou (%s): %s", type(exc).__name__, exc)
            return _erro_legivel(exc)

    def _montar(self, texto_do_periodo: str) -> str:
        # 🔴 O padrão do Radar olha para o FUTURO — 90 dias. O do Raio-X olha
        # para trás. Um radar que abre no ano corrente mostraria o que já
        # venceu, que é o oposto do que ele serve para fazer.
        calc, FonteInfocap, FalhaDaInfocap, _anos = _comercial()
        p = calc.entender_periodo(texto_do_periodo, padrao_dias_futuro=90)
        slug = _slug_da_empresa(self.supabase, str(self.company_id or ""))
        fonte = FonteInfocap.para_empresa(slug)

        venc = fonte.carteira_a_vencer(p.inicio, p.fim)
        if not venc:
            return (f"RELATORIO_VAZIO · nada vence em {p.rotulo}. Diga isso ao "
                    "corretor e sugira ampliar a janela. Não invente número.")

        por_vend = calc.por_vendedor_no_radar(venc)
        faixas = calc.faixas_de_urgencia(venc)
        por_ramo = calc.por_dimensao(venc, "ramo", teto=8, campo_valor="premio")
        total = sum(v.premio for v in venc)
        agora = datetime.now().strftime("%d/%m/%Y às %H:%M")

        blocos = self._compor(p, venc, por_vend, faixas, por_ramo, total, agora)
        payload = {
            "periodo": {"inicio": str(p.inicio), "fim": str(p.fim), "rotulo": p.rotulo},
            "total_em_risco": round(total, 2), "apolices": len(venc),
            "por_vendedor": [{"nome": n, "apolices": a, "premio": round(pr, 2),
                              "vence_em_dias": d} for n, a, pr, d in por_vend],
            "faixas": [{"faixa": f, "apolices": n, "premio": round(pr, 2)}
                       for f, n, pr in faixas],
        }
        ident = _publicar(
            self.supabase, str(self.company_id),
            titulo=f"Radar de Renovações · {p.rotulo}",
            subtitulo="O que vence, quanto vale e de quem é",
            resumo=f"{len(venc)} apólices, {_reais(total)} em risco, "
                   f"{len(por_vend)} vendedores.",
            template=_TEMPLATE_RADAR, payload=payload, blocos=blocos)
        if not ident:
            return _erro_legivel(RuntimeError("o artifact não foi criado"))

        aviso = " (período padrão — o corretor não especificou)" if p.e_padrao else ""
        return (
            f"RELATORIO_PRONTO · Radar de Renovações de **{p.rotulo}**{aviso}.\n\n"
            f"[Abrir o relatório]({_link(ident)})\n\n"
            f"Resumo para você comentar: {len(venc)} apólices vencendo, "
            f"{_reais(total)} em prêmio, distribuídos entre {len(por_vend)} vendedores."
        )

    def _compor(self, p, venc, por_vend, faixas, por_ramo, total, agora) -> List[Dict]:
        urgentes = [v for v in venc if 0 <= v.dias_a_vencer <= 30]
        vencidas = [v for v in venc if v.dias_a_vencer < 0]
        blocos: List[Dict[str, Any]] = [
            {"block": "cover", "props": {
                "eyebrow": "Radar de Renovações",
                "title": f"O que vence · {p.rotulo}",
                "headline_value": _reais(total),
                "headline_label": f"{len(venc)} apólices em risco",
                "period": p.rotulo,
            }},
            {"block": "kpis", "props": {"title": "A janela", "items": [
                {"label": "Prêmio em risco", "value": _reais(total)},
                {"label": "Apólices", "value": f"{len(venc)}"},
                {"label": "Vencem em 30 dias", "value": f"{len(urgentes)}",
                 "since": _reais(sum(v.premio for v in urgentes))},
                {"label": "Vendedores envolvidos", "value": f"{len(por_vend)}"},
            ]}},
        ]
        if vencidas:
            blocos.append({"block": "callout", "props": {
                "tone": "warning", "title": "Já venceram e continuam na lista",
                "text": (f"{len(vencidas)} apólices já passaram do vencimento, "
                         f"somando {_reais(sum(v.premio for v in vencidas))}. "
                         "Elas vêm primeiro."),
            }})

        # 🔴 O QUE O FOUNDER PEDIU: separado por vendedor.
        if por_vend:
            blocos.append({"block": "table", "props": {
                "eyebrow": "Por vendedor",
                "title": "Quem tem mais renovação em jogo",
                "columns": [
                    {"key": "nome", "label": "Vendedor"},
                    {"key": "apolices", "label": "Apólices", "format": "number"},
                    {"key": "premio", "label": "Prêmio em jogo", "format": "currency"},
                    {"key": "dias", "label": "Vence em (dias)", "format": "number"},
                ],
                "rows": [{"nome": n, "apolices": a, "premio": round(pr, 2), "dias": d}
                         for n, a, pr, d in por_vend[:20]],
                "total": {"nome": "Total", "apolices": len(venc),
                          "premio": round(total, 2)},
            }})
            blocos.append({"block": "ranking", "props": {
                "eyebrow": "Concentração", "title": "Prêmio a vencer por vendedor",
                "value_type": "currency_short",
                "items": [{"rotulo": _encurtar(n, 22), "valor": round(pr, 2)}
                          for n, _a, pr, _d in por_vend[:12]],
            }})

        if faixas:
            blocos.append({"block": "chart", "props": {
                "eyebrow": "Urgência", "title": "Prêmio por janela de vencimento",
                "labels": [f for f, _n, _pr in faixas],
                "series": [{"name": "Prêmio",
                            "values": [round(pr, 2) for _f, _n, pr in faixas]}],
                "value_type": "currency_short",
            }})

        if por_ramo:
            blocos.append({"block": "donut", "props": {
                "title": "A vencer por ramo", "value_type": "currency_short",
                "slices": [{"rotulo": r, "valor": round(c, 2)} for r, _n, c in por_ramo],
            }})

        proximos = sorted(venc, key=lambda v: v.dias_a_vencer)[:15]
        blocos.append({"block": "table", "props": {
            "eyebrow": "Agenda", "title": "Os quinze mais urgentes",
            "columns": [
                {"key": "cliente", "label": "Cliente"},
                {"key": "seguradora", "label": "Seguradora"},
                {"key": "dias", "label": "Dias", "format": "number"},
                {"key": "premio", "label": "Prêmio", "format": "currency"},
                {"key": "vendedor", "label": "Vendedor"},
            ],
            # 🔴 SEM telefone e SEM CPF na peça. O contato existe no sistema;
            # um relatório é documento que circula, e dado de segurado em
            # documento que circula é vazamento esperando acontecer.
            "rows": [{"cliente": v.cliente[:38], "seguradora": v.seguradora,
                      "dias": v.dias_a_vencer, "premio": round(v.premio, 2),
                      "vendedor": _encurtar(v.produtor, 22)} for v in proximos],
        }})

        blocos.append({"block": "verdict", "props": {"text": (
            f"{_reais(total)} vencem em {p.rotulo}, em {len(venc)} apólices. "
            + (f"{len(urgentes)} delas nos próximos 30 dias. " if urgentes else "")
            + (f"A maior concentração é de {por_vend[0][0]}, com "
               f"{_reais(por_vend[0][2])}." if por_vend else "")
        )}})
        blocos.append(_fontes(agora,
                              "Apólices canceladas e documentos que não são apólice ficam fora."))
        blocos.append({"block": "footer", "props": {
            "disclaimer": "Documento interno. Não contém CPF/CNPJ nem telefone de segurado.",
        }})
        return blocos


# --------------------------------------------------------------------------
def ferramentas_comerciais(*, company_id: Optional[str], supabase: Any) -> List[BaseTool]:
    """As duas tools, ou lista vazia. Nunca levanta na montagem do grafo."""
    if not company_id or supabase is None:
        return []
    return [
        RaioXComercialTool(company_id=str(company_id), supabase=supabase),
        RadarDeRenovacoesTool(company_id=str(company_id), supabase=supabase),
    ]
