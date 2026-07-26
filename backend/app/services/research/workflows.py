"""Workflows de pesquisa no Work OS. SPEC-060 §25.

Registrados no MESMO registro da SPEC-055. Nenhum executor novo: quem roda é o
Smith Worker, com lease, heartbeat, retomada e cancelamento cooperativo.

Por que pesquisa profunda PRECISA ser Work Run (§25.1): ela dura minutos,
consome provider pago e produz artefato. Sem Work Run, um deploy no meio mata
a pesquisa depois de já ter gasto o crédito — e ninguém fica sabendo.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from ..work.workflows import executar_passo, registrar_workflow

logger = logging.getLogger(__name__)


@registrar_workflow("research.execute")
async def executar_pesquisa(ctx: dict) -> str:
    """Pesquisa completa: plano → fontes → claims → verificação → dossiê."""
    from .adapters import ArtifactAdapter, IntelligenceAdapter, KnowledgeAdapter
    from .claim_service import ClaimService
    from .orchestrator import ResearchOrchestrator
    from .schemas import ResearchRequest, PERFIL_DO_MODO

    payload = ctx.get("payload") or {}
    company_id = ctx["company_id"]
    db = ctx["db"]
    pergunta = str(payload.get("pergunta") or "").strip()
    if not pergunta:
        return "Pesquisa sem pergunta — nada a fazer."

    pedido = ResearchRequest(
        company_id=company_id, question=pergunta,
        objective=str(payload.get("objetivo") or ""),
        mode=str(payload.get("modo") or "verified"),
        user_id=payload.get("user_id"),
        conversation_id=payload.get("conversation_id"),
        requested_by_kind=str(payload.get("origem") or "user"),
        saidas=list(payload.get("saidas") or []))

    async def _pesquisar() -> Any:
        orquestrador = ResearchOrchestrator(
            db, company_id=company_id, work_run_id=ctx.get("run_id"),
            user_id=payload.get("user_id"))
        return await orquestrador.pesquisar(pedido)

    resultado = await executar_passo(
        ctx, step_key="pesquisar", ordinal=1, nome="Pesquisar e verificar",
        step_type="research", fn=_pesquisar,
        capability_key="platform.research.deep")

    if not resultado.claims:
        # Resultado vazio é resultado. Falhar o Work Run aqui faria o sistema
        # tentar de novo e gastar de novo, para chegar ao mesmo lugar.
        return resultado.resumo or "A pesquisa não encontrou fonte utilizável."

    citacoes = ClaimService(db).citacoes(
        company_id, [str(c.get("id")) for c in resultado.claims if c.get("id")])

    # O dossiê só entra quando o modo pede (§7). Gerar peça para uma pergunta
    # rápida enche a biblioteca de PDF que ninguém abre.
    if PERFIL_DO_MODO.get(pedido.mode, {}).get("artifact"):
        async def _dossie() -> Any:
            return ArtifactAdapter(db).dossie(
                company_id=company_id, resultado=resultado,
                citacoes=citacoes, work_run_id=ctx.get("run_id"))

        try:
            await executar_passo(ctx, step_key="dossie", ordinal=2,
                                 nome="Montar o dossiê", step_type="artifact",
                                 fn=_dossie)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Research] dossiê não gerado: %s", type(exc).__name__)

    async def _encaminhar() -> Any:
        candidatos = KnowledgeAdapter(db).propor(
            company_id=company_id, claims=resultado.claims, citacoes=citacoes)
        sinal = IntelligenceAdapter(db).sinal_de_pesquisa(
            company_id=company_id, resultado=resultado,
            origem=pedido.requested_by_kind)
        return {"candidatos": len(candidatos), "sinal": bool(sinal)}

    encaminhado = await executar_passo(
        ctx, step_key="encaminhar", ordinal=3,
        nome="Encaminhar o que é durável", step_type="analysis", fn=_encaminhar)

    partes = [resultado.resumo]
    if encaminhado.get("candidatos"):
        partes.append(
            f"{encaminhado['candidatos']} item(ns) foram propostos para o "
            f"conhecimento e aguardam revisão — nada foi publicado.")
    if resultado.limitacoes:
        partes.append(f"{len(resultado.limitacoes)} limitação(ões) declarada(s).")
    return " ".join(partes)


@registrar_workflow("research.monitor_check")
async def verificar_monitor(ctx: dict) -> str:
    """Executa um monitor. Disparado pela Rotina — nenhum agendador novo."""
    from .adapters import IntelligenceAdapter
    from .monitor_service import MonitorService

    payload = ctx.get("payload") or {}
    db = ctx["db"]
    company_id = ctx["company_id"]

    servico = MonitorService(db)
    monitor_id = payload.get("monitor_id")
    if not monitor_id and payload.get("routine_id"):
        # A ponte de Rotinas da SPEC-055 manda `routine_id`; o monitor é
        # encontrado por ele. É o que permite reusar o motor de Rotinas sem
        # inventar um agendador de monitores.
        m = servico.por_rotina(str(payload["routine_id"]))
        monitor_id = (m or {}).get("id")
    if not monitor_id:
        return "Monitor não identificado — nada a verificar."

    async def _verificar() -> Any:
        return await servico.executar(str(monitor_id),
                                      work_run_id=ctx.get("run_id"))

    r = await executar_passo(ctx, step_key="verificar", ordinal=1,
                             nome="Verificar as fontes monitoradas",
                             step_type="research", fn=_verificar,
                             capability_key="platform.research.monitor")

    if not r.get("ok"):
        return str(r.get("erro") or "Não consegui verificar o monitor agora.")

    monitor = servico._carregar(str(monitor_id)) or {}
    relevantes = [o for o in (r.get("observacoes") or [])
                  if o.get("change_class") in ("relevant", "major")]

    async def _promover() -> Any:
        adaptador = IntelligenceAdapter(db)
        criados = 0
        for o in relevantes:
            if adaptador.sinal_de_observacao(company_id=company_id,
                                             monitor=monitor, observacao=o):
                criados += 1
        return criados

    sinais = await executar_passo(
        ctx, step_key="promover", ordinal=2,
        nome="Avisar sobre o que mudou de verdade", step_type="analysis",
        fn=_promover) if relevantes else 0

    if r.get("falhas") and not r.get("verificadas"):
        return ("Nenhuma fonte deste monitor pôde ser lida nesta verificação. "
                "Não afirmo que nada mudou — apenas que não consegui olhar.")
    if not relevantes:
        return (f"{r.get('verificadas', 0)} fonte(s) verificada(s). "
                f"Nada relevante mudou.")
    return (f"{len(relevantes)} mudança(s) relevante(s) em "
            f"{r.get('verificadas', 0)} fonte(s); {sinais} viraram aviso.")


@registrar_workflow("research.site_audit")
async def auditar_site(ctx: dict) -> str:
    """Auditoria de SEO/AEO do site da corretora — §21."""
    from .site_audit import SiteAudit

    payload = ctx.get("payload") or {}
    url = str(payload.get("url") or "").strip()
    if not url:
        return "Auditoria sem endereço de site."

    async def _auditar() -> Any:
        return await SiteAudit(ctx["db"], company_id=ctx["company_id"],
                               work_run_id=ctx.get("run_id")).auditar_site(
            url, max_paginas=int(payload.get("max_paginas") or 12))

    r = await executar_passo(ctx, step_key="auditar", ordinal=1,
                             nome="Analisar o site", step_type="research",
                             fn=_auditar,
                             capability_key="platform.research.site_audit")

    if not r.get("ok"):
        return str(r.get("erro") or "Não consegui analisar o site agora.")

    resumo = r.get("resumo") or {}
    partes = [f"{resumo.get('paginas_analisadas', 0)} página(s) analisadas, "
              f"{resumo.get('achados', 0)} ponto(s) encontrados"]
    if resumo.get("primeiro_passo"):
        partes.append(f"Comece por: {resumo['primeiro_passo']}")
    if r.get("limitacoes"):
        partes.append(f"{len(r['limitacoes'])} limitação(ões) declarada(s).")
    return ". ".join(partes) + "."


@registrar_workflow("research.business_discovery")
async def descobrir_empresas(ctx: dict) -> str:
    """Lista de empresas por região e segmento — §19. Sem outreach."""
    from .discovery import BusinessDiscovery

    payload = ctx.get("payload") or {}
    segmento = str(payload.get("segmento") or "").strip()
    regiao = str(payload.get("regiao") or "").strip()
    if not segmento or not regiao:
        return "Preciso do segmento e da região para procurar empresas."

    async def _descobrir() -> Any:
        return await BusinessDiscovery(
            ctx["db"], company_id=ctx["company_id"],
            work_run_id=ctx.get("run_id")).descobrir(
                segmento=segmento, regiao=regiao,
                limite=int(payload.get("limite") or 50))

    r = await executar_passo(ctx, step_key="descobrir", ordinal=1,
                             nome="Procurar empresas", step_type="research",
                             fn=_descobrir,
                             capability_key="platform.research.places")

    if not r.get("ok"):
        return str(r.get("mensagem_humana")
                   or "Não consegui montar a lista de empresas agora.")
    return (f"{r.get('total', 0)} empresa(s) encontradas em {regiao}. "
            f"Nenhuma mensagem foi enviada — o contato é uma ação separada.")


@registrar_workflow("research.radar_weekly")
async def fechar_radar(ctx: dict) -> str:
    """Fechamento do Auxiliar Radar de Mercado e Regulação — §37.

    Não verifica fonte nenhuma: quem verifica é `research.monitor_check`, na
    cadência de cada monitor. Este passo apenas LÊ o que já foi observado e
    consolida. Reverificar aqui gastaria crédito duas vezes pela mesma leitura
    e — pior — poderia produzir um radar que discorda dos avisos já entregues.
    """
    from .radar import RadarDeMercado

    payload = ctx.get("payload") or {}
    dias = int(payload.get("dias") or 7)

    async def _fechar() -> Any:
        return RadarDeMercado(ctx["db"]).compor_semanal(
            company_id=ctx["company_id"], dias=dias,
            work_run_id=ctx.get("run_id"))

    r = await executar_passo(ctx, step_key="consolidar", ordinal=1,
                             nome="Consolidar o que mudou na regulação",
                             step_type="analysis", fn=_fechar)

    if not r.get("ok"):
        return "Não consegui fechar o radar desta semana."
    if r.get("sem_mudanca"):
        # Dizer que nada mudou é diferente de não dizer nada: a segunda forma
        # deixa o corretor sem saber se o radar rodou.
        return str(r.get("mensagem"))
    return (f"{r.get('mudancas')} mudança(s) relevante(s) na regulação nos "
            f"últimos {dias} dias. O radar está pronto.")
