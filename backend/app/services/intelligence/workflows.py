"""Workflows de inteligencia no Work OS. SPEC-059 §22.1 e §28.

Todos registrados no MESMO registro da SPEC-055 (`registrar_workflow`). Nao ha
executor novo: o Smith Worker continua sendo quem executa, com lease,
heartbeat, retomada e trilha auditavel.

Por que briefing precisa ser Work Run e nao uma funcao qualquer: ele consome
modelo, gera artefato e entrega por canal. Sem Work Run, um deploy no meio
mata a geracao e ninguem fica sabendo; com Work Run, o trabalho e retomado e o
custo fica atribuido ao tenant certo.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from ..work.workflows import executar_passo, registrar_workflow

logger = logging.getLogger(__name__)


def _agora() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Deteccao
# ---------------------------------------------------------------------------


@registrar_workflow("intelligence.detect_signals")
async def detectar_sinais(ctx: dict) -> str:
    """Roda os detectores de uma corretora e consolida os Findings."""
    from .finding_engine import FindingEngine
    from .recommendation_service import RecommendationService
    from .rule_engine import RuleEngine

    company_id = ctx["company_id"]
    db = ctx["db"]

    async def _detectar() -> Any:
        return RuleEngine(db).varrer_empresa(company_id)

    resultado = await executar_passo(
        ctx, step_key="detectar", ordinal=1, nome="Procurar o que mudou",
        step_type="analysis", fn=_detectar)

    async def _consolidar() -> Any:
        return FindingEngine(db).consolidar(company_id)

    findings = await executar_passo(
        ctx, step_key="consolidar", ordinal=2, nome="Montar os diagnósticos",
        step_type="analysis", fn=_consolidar)

    async def _recomendar() -> Any:
        servico = RecommendationService(db)
        criadas = 0
        for f in findings or []:
            if servico.a_partir_do_finding(f):
                criadas += 1
        return criadas

    recomendacoes = await executar_passo(
        ctx, step_key="recomendar", ordinal=3, nome="Propor o que fazer",
        step_type="analysis", fn=_recomendar)

    return (f"{resultado.resumo()}; {len(findings or [])} diagnóstico(s) e "
            f"{recomendacoes} recomendação(ões).")


# ---------------------------------------------------------------------------
# Briefings
# ---------------------------------------------------------------------------


@registrar_workflow("intelligence.daily_briefing")
async def briefing_diario(ctx: dict) -> str:
    return await _briefing(ctx, "daily_operational", "Briefing do dia")


@registrar_workflow("intelligence.weekly_executive_briefing")
async def briefing_semanal(ctx: dict) -> str:
    return await _briefing(ctx, "weekly_executive", "Briefing executivo da semana")


async def _briefing(ctx: dict, tipo: str, nome: str) -> str:
    from .briefing_service import BriefingService

    company_id = ctx["company_id"]
    db = ctx["db"]
    user_id = (ctx.get("payload") or {}).get("user_id")

    async def _gerar() -> Any:
        return BriefingService(db).gerar(
            company_id, briefing_type=tipo, user_id=user_id,
            work_run_id=ctx.get("run_id"))

    resultado = await executar_passo(
        ctx, step_key="gerar_briefing", ordinal=1, nome=nome,
        step_type="analysis", fn=_gerar)

    if not resultado.get("ok"):
        return "Não consegui montar o briefing agora."
    if resultado.get("reaproveitado"):
        return "O briefing deste período já estava publicado — nada foi duplicado."

    publicacao = resultado.get("publication") or {}
    spec = resultado.get("spec") or {}

    # A peca do Artifact Hub e opcional de proposito: o briefing ja esta
    # publicado e visivel no dashboard. Se a geracao da peca falhar, o
    # corretor NAO perde o briefing — perde o PDF, que e outro problema, menor.
    async def _artefato() -> Any:
        return await _gerar_artefato(db, company_id, tipo, spec, publicacao,
                                     ctx.get("run_id"))

    try:
        await executar_passo(ctx, step_key="artefato", ordinal=2,
                             nome="Montar a peça do briefing",
                             step_type="artifact", fn=_artefato)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Briefing] peça não gerada: %s", type(exc).__name__)

    return (f"{publicacao.get('headline') or nome} — "
            f"{publicacao.get('item_count') or 0} item(ns).")


async def _gerar_artefato(db: Any, company_id: str, tipo: str, spec: dict,
                          publicacao: dict, run_id) -> Any:
    """Cria a peca no Artifact Hub da SPEC-057. Nao cria formato novo."""
    from ..artifacts.service import ArtifactService

    from ..artifacts.service import tags_do_canario

    template = ("briefing.weekly_executive" if tipo == "weekly_executive"
                else "briefing.daily_operational")
    servico = ArtifactService(db)
    # 🔴 SPEC-095 · B.1/B.2: a identidade do briefing é o DIA — o tick já
    # publica um por dia, e `gerar` é idempotente por período. Sem
    # `subject_ref`, as peças de dias diferentes eram indistinguíveis para a
    # lista (📊 `subject_ref.id` não vazio em 5/136 peças em todo o banco).
    #
    # E `data_as_of` é o FIM DO PERÍODO que o briefing mede — a data do DADO.
    # 📊 §1.9: até aqui a coluna guardava a hora da escrita em 136/136 versões.
    periodo = spec.get("period") or {}
    fim = _quando(periodo.get("end"))
    dia = fim.strftime("%Y-%m-%d") if fim else str(periodo.get("end") or "")
    r = servico.criar(
        company_id=company_id,
        title=str(spec.get("headline") or "Briefing"),
        template_key=template, payload=spec,
        composition=compor_pecas(spec),
        subtitle=_periodo_legivel(spec), summary=str(spec.get("executive_summary") or ""),
        kind="report", origin="routine", work_run_id=run_id,
        data_sources=_fontes(spec),
        subject_ref={"kind": "periodo", "id": dia,
                     "label": fim.strftime("%d/%m") if fim else dia,
                     "produtor": "checklist-6h"},
        data_as_of=fim, tags=tags_do_canario())
    versao = (r.get("version") or {}).get("id")
    if versao:
        servico.renderizar(company_id=company_id, version_id=versao)
        servico.publicar(company_id=company_id, version_id=versao)
    artifact_id = (r.get("artifact") or {}).get("id")
    if artifact_id and publicacao.get("id"):
        try:
            getattr(db, "client", db).table("briefing_publications").update(
                {"artifact_id": artifact_id}).eq("id", publicacao["id"]).execute()
        except Exception:  # noqa: BLE001
            pass
    return artifact_id


def compor_pecas(spec: dict) -> list[dict]:
    """Briefing Spec → blocos do Artifact Hub. Pura, e **sem recalcular nada**.

    Cada numero que aparece na peca ja veio pronto do Spec. §17.2 exige que
    web, PDF e resumo curto saiam da MESMA publicacao: se esta funcao
    calculasse qualquer coisa, o PDF poderia divergir da tela — e o corretor
    descobriria isso na frente de um cliente.

    Secao vazia nao vira bloco (§16.1): um "Riscos" com a frase "nenhum risco
    identificado" ocupa espaco e ensina o leitor a pular secoes.
    """
    periodo = _periodo_legivel(spec)
    secoes = spec.get("sections") or []
    acionaveis = [i for s in secoes for i in (s.get("items") or [])
                  if i.get("item_type") in ("finding", "recommendation")]
    resultados = [i for s in secoes for i in (s.get("items") or [])
                  if i.get("item_type") == "result"]

    blocos: list[dict] = [{
        "block": "cover",
        "props": {"eyebrow": "Briefing", "title": spec.get("headline") or "Briefing",
                  "period": periodo, "verdict": spec.get("executive_summary"),
                  "headline_label": "itens esperando você",
                  "headline_value": str(len(acionaveis))},
    }]

    indicadores = [{"label": "Esperando você", "value": str(len(acionaveis))}]
    # ⛔ "Concluído no período: 0" só aparecia porque a linha era incondicional.
    # 📊 Depois do D.5 (o relógio da plataforma fora), o valor é 0 em 5 de 5
    # dias medidos — um cartão fixo em zero, todo dia, é a mesma "enchição de
    # linguiça" que o §0 tirou da manchete. Ele volta sozinho no dia em que a
    # corretora tiver trabalho pedido e concluído.
    if resultados:
        indicadores.append({"label": "Concluído no período",
                            "value": str(len(resultados))})
    criticos = [i for i in acionaveis if float(i.get("priority_score") or 0) >= 85]
    if criticos:
        indicadores.insert(0, {"label": "Crítico", "value": str(len(criticos))})
    blocos.append({"block": "kpis", "props": {"title": "Onde a corretora está",
                                              "items": indicadores}})

    for s in secoes:
        itens = s.get("items") or []
        if not itens:
            continue
        chave = s.get("key")
        if chave in ("precisa_de_voce", "gargalos", "decisoes", "automacao"):
            blocos.append({"block": "actions", "props": {
                "eyebrow": s.get("title"), "title": _titulo_da_secao(chave),
                "items": [{"title": i.get("headline"),
                           "detail": _detalhe_do_item(i),
                           "owner": i.get("action_label")} for i in itens[:8]]}})
        elif chave in ("riscos", "qualidade", "custos"):
            for i in itens[:4]:
                blocos.append({"block": "callout", "props": {
                    "title": i.get("headline"), "text": i.get("summary"),
                    "tone": "negative" if float(i.get("priority_score") or 0) >= 85
                            else "warning"}})
        elif chave in ("concluido", "resultados", "em_andamento", "trabalhos"):
            blocos.append({"block": "table", "props": {
                "eyebrow": s.get("title"), "title": _titulo_da_secao(chave),
                "columns": [{"key": "o_que", "label": "O quê"},
                            {"key": "situacao", "label": "Situação"}],
                "rows": [{"o_que": i.get("headline"), "situacao": i.get("summary")}
                         for i in itens[:10]]}})
        elif chave in ("faltando", "indicadores") and itens:
            blocos.append({"block": "prose", "props": {
                "eyebrow": "Transparência",
                "title": "O que ainda não dá para afirmar",
                "text": "\n\n".join(str(i.get("headline") or "") for i in itens[:5])}})
        elif chave == "oportunidades":
            blocos.append({"block": "ranking", "props": {
                "eyebrow": s.get("title"), "title": "Oportunidades",
                "items": [{"rotulo": i.get("headline"),
                           "valor": float(i.get("priority_score") or 0)}
                          for i in itens[:6]]}})

    # 🔴 SPEC-095 · D.3: "Método" era uma SEÇÃO inteira com uma frase FIXA — a
    # mesma em todo briefing, de toda corretora, todo dia. Uma seção que nunca
    # muda ensina o leitor a pular seções (§16.1), e a peça terminava com duas
    # caixas cerimoniais. As duas viram UMA linha de rodapé.
    blocos.append({"block": "sources", "props": {}})
    blocos.append({"block": "footer", "props": {
        "disclaimer": " ".join(p for p in (
            str(spec.get("methodology") or "").strip(),
            "Documento interno.") if p)}})
    return blocos


def _detalhe_do_item(i: dict) -> str:
    """O `detail` de um item de ação: o que é · por que AGORA · o próximo passo.

    🔴 SPEC-095 · D.3, modelado do AWS Trusted Advisor (§3 ②): cada check abre
    com o critério, a ação recomendada e os itens afetados — três campos
    NOMEADOS, e não uma cor.

    📊 O porquê e o próximo passo já existiam no banco: `why_now` preenchido em
    **12/12** achados da Resulta e `next_step` em **11/12**. Eles morriam em
    `ItemDeBriefing`, que não tinha campo para eles — e a tela recebia só o
    `summary`. Esta função é o último metro do caminho.
    """
    resumo = " ".join(str(i.get("summary") or "").split())
    porque = " ".join(str(i.get("why_now") or "").split())
    passo = " ".join(str(i.get("next_step") or "").split())
    partes = [resumo]
    # ⚠️ Só acrescenta o porquê se ele não estiver JÁ no resumo: desde a D.1 o
    # `summary_redacted` dos achados comerciais é "{título}. {porquê} {ação}",
    # e repetir a mesma frase duas vezes no mesmo cartão é ruído.
    if porque and porque not in resumo:
        partes.append(porque)
    if passo and passo not in resumo:
        partes.append("→ %s" % passo)
    return " ".join(p for p in partes if p)


def _titulo_da_secao(chave: str) -> str:
    return {
        "precisa_de_voce": "O que precisa de você",
        "gargalos": "Onde a operação está travando",
        "decisoes": "Decisões recomendadas",
        "automacao": "O que dá para deixar automático",
        "concluido": "O que ficou pronto",
        "resultados": "Resultados do período",
        "em_andamento": "Em andamento",
        "trabalhos": "Trabalhos e Auxiliares",
    }.get(chave, chave)


def _fontes(spec: dict) -> list[dict]:
    """Fontes declaradas na peca. §24.1 — todo numero diz de onde veio.

    🔴 SPEC-095 · B.1: as chaves são `label` / `detail` / `as_of_label` —
    as que `blocks.sources` (`blocks.py:359-364`) e o detalhe da tela leem.
    Antes eram `rotulo` / `detalhe` / `data`, e `sources` desenhava
    `<li><b></b><span></span></li>`: **três bullets vazios** no fim de todo
    briefing, com o dado presente na coluna e invisível na peça.

    ⚠️ E são as MESMAS chaves que o Pulso grava (`_fontes` de
    `relatorios_comerciais.py`). Uma forma só, porque a tela de detalhe é uma
    só — dois formatos de procedência dariam duas telas, e uma delas vazia.
    """
    periodo = _periodo_legivel(spec)
    fontes = [{"label": "Operação",
               "detail": "Work Runs, aprovações e conexões da corretora",
               "as_of_label": periodo}]
    tipos = spec.get("sources_summary") or []
    if any(t in ("attendance_quality",) for t in tipos):
        fontes.append({"label": "Qualidade", "detail": "auditoria de conversas",
                       "as_of_label": periodo})
    if any(t in ("repeated_task", "capability_gap", "broker_desire") for t in tipos):
        fontes.append({"label": "Pedidos",
                       "detail": "o que você pediu ao AutoBrokers",
                       "as_of_label": periodo})
    return fontes


def _quando(valor: Any) -> Optional[datetime]:
    """A data ISO do Spec como `datetime`, ou `None`. Nunca levanta.

    ⛔ `None` é NULL na coluna `data_as_of` — e NULL é "não sei". A alternativa
    (cair em `now()`) é o defeito da §1.9: uma afirmação de frescor que o
    sistema não tem como sustentar.
    """
    try:
        return datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        return None


def _periodo_legivel(spec: dict) -> str:
    p = spec.get("period") or {}
    i, f = _quando(p.get("start")), _quando(p.get("end"))
    if i is None or f is None:
        return ""
    return f"{i.strftime('%d/%m')} a {f.strftime('%d/%m/%Y')}"


# ---------------------------------------------------------------------------
# Garimpo, demanda e medicao
# ---------------------------------------------------------------------------


@registrar_workflow("intelligence.garimpo")
async def garimpo(ctx: dict) -> str:
    from .garimpo_v3 import GarimpoV3

    horas = int((ctx.get("payload") or {}).get("horas") or 24)

    async def _minerar() -> Any:
        return GarimpoV3(ctx["db"]).minerar_recentes(horas=horas)

    r = await executar_passo(ctx, step_key="garimpar", ordinal=1,
                             nome="Escutar a voz do corretor",
                             step_type="analysis", fn=_minerar)
    return (f"{r.get('conversas', 0)} conversa(s) lidas, "
            f"{r.get('sinais', 0)} sinal(is) e {r.get('pedidos', 0)} pedido(s) registrados.")


@registrar_workflow("intelligence.cluster_demand")
async def agrupar_demanda(ctx: dict) -> str:
    """Batch de PLATAFORMA. Le pedidos de todas as corretoras, anonimizados."""
    from .demand_cluster_service import DemandClusterService

    async def _agrupar() -> Any:
        return DemandClusterService(ctx["db"]).agregar()

    r = await executar_passo(ctx, step_key="agrupar", ordinal=1,
                             nome="Agrupar a demanda das corretoras",
                             step_type="analysis", fn=_agrupar)
    return f"{r.get('clusters', 0)} necessidade(s) distinta(s) atualizadas."


@registrar_workflow("intelligence.claims_shadow_digest")
async def digerir_sombras_de_sinistro(ctx: dict) -> str:
    """SPEC-093-B BLOCO C. Agrupa as sombras em variantes e escreve sinais.

    ⚠️ Aqui é só a TOMADA: o corpo mora em `app.services.claims_shadow_digest`,
    junto das funções puras (`variantes_de`, `contadores_de`) que ele usa. Um
    workflow que carrega a regra dentro de si só é testável com Work Run montado —
    e foi assim que a regra da variante deixaria de ter linha de controle.

    ⛔ Observação pura: nenhuma mensagem sai, nenhum sinistro é decidido, e a
    escrita é só `intelligence_signals`, pela porta única do `signal_service`.
    """
    from ..claims_shadow_digest import executar

    return await executar(ctx)


@registrar_workflow("intelligence.measure_outcomes")
async def medir_resultados(ctx: dict) -> str:
    from .outcome_service import OutcomeService

    async def _medir() -> Any:
        servico = OutcomeService(ctx["db"])
        vencidos = servico.vencidos(limite=30)
        medidos = [servico.medir(o) for o in vencidos]
        return [m for m in medidos if m]

    medidos = await executar_passo(ctx, step_key="medir", ordinal=1,
                                   nome="Medir o que foi feito",
                                   step_type="analysis", fn=_medir)
    if not medidos:
        return "Nenhuma medição vencida no momento."
    por_status: dict[str, int] = {}
    for m in medidos:
        s = str(m.get("measurement_status"))
        por_status[s] = por_status.get(s, 0) + 1
    partes = ", ".join(f"{n} {s}" for s, n in por_status.items())
    return f"{len(medidos)} medição(ões) fechada(s): {partes}."


# ---------------------------------------------------------------------------
# Investigacoes — o CTA "Resolver" das recomendacoes
# ---------------------------------------------------------------------------


@registrar_workflow("intelligence.investigate_failures")
async def investigar_falhas(ctx: dict) -> str:
    """Junta o que se sabe sobre as falhas e registra o diagnostico.

    Deliberadamente **so leitura**. Reexecutar o que falhou sem saber por que
    falhou e a forma mais rapida de transformar uma falha em duas.
    """
    from .signal_service import registrar_evento

    company_id, db = ctx["company_id"], ctx["db"]
    cliente = getattr(db, "client", db)

    async def _investigar() -> Any:
        from datetime import timedelta

        desde = (_agora() - timedelta(hours=48)).isoformat()
        runs = (cliente.table("work_runs")
                .select("id, workflow_key, error_code, error_message, finished_at")
                .eq("company_id", company_id).eq("status", "failed")
                .gte("finished_at", desde).limit(100).execute()).data or []
        por_causa: dict[str, int] = {}
        for r in runs:
            causa = str(r.get("error_code") or "desconhecida")
            por_causa[causa] = por_causa.get(causa, 0) + 1
        conexoes = (cliente.table("tenant_connections")
                    .select("name, status, health_status")
                    .eq("company_id", company_id).limit(50).execute()).data or []
        ruins = [c for c in conexoes
                 if str(c.get("health_status") or c.get("status") or "").lower()
                 in ("expired", "degraded", "error", "disconnected")]
        return {"falhas": len(runs), "por_causa": por_causa,
                "conexoes_ruins": [c.get("name") for c in ruins]}

    r = await executar_passo(ctx, step_key="investigar", ordinal=1,
                             nome="Investigar as falhas", step_type="analysis",
                             fn=_investigar)

    if r["conexoes_ruins"]:
        conclusao = ("As falhas coincidem com conexão indisponível: "
                     + ", ".join(str(c) for c in r["conexoes_ruins"] if c)
                     + ". Reconectar deve resolver.")
    elif r["por_causa"]:
        causa = max(r["por_causa"].items(), key=lambda x: x[1])
        conclusao = (f"{r['falhas']} falha(s) em 48h; a causa mais comum é "
                     f"'{causa[0]}' ({causa[1]} vez(es)). "
                     "Nenhuma conexão aparece degradada — a causa provável é do provedor.")
    else:
        conclusao = "Nenhuma falha registrada nas últimas 48h."

    registrar_evento(db, company_id=company_id, tipo="action.completed",
                     subject_type="work_run", mensagem=conclusao,
                     detalhe=r)
    return conclusao


@registrar_workflow("intelligence.investigate_quality")
async def investigar_qualidade(ctx: dict) -> str:
    """Abre a queda de qualidade em fatos, sem inventar causa.

    §13.3: causa raiz so pode ser afirmada com evidencia suficiente, regra
    deterministica ou confirmacao humana. Aqui se entrega o que os scorecards
    mostram e onde ficou a maior concentracao — chamando de "possivel causa".
    """
    from datetime import timedelta

    company_id, db = ctx["company_id"], ctx["db"]
    cliente = getattr(db, "client", db)

    async def _investigar() -> Any:
        desde = (_agora() - timedelta(hours=48)).isoformat()
        cards = (cliente.table("conversation_scorecards")
                 .select("score, flags, created_at")
                 .eq("company_id", company_id).gte("created_at", desde)
                 .limit(500).execute()).data or []
        flags: dict[str, int] = {}
        for c in cards:
            for f in (c.get("flags") or []):
                flags[str(f)] = flags.get(str(f), 0) + 1
        notas = [float(c.get("score") or 0) for c in cards]
        return {"amostras": len(cards),
                "media": round(sum(notas) / len(notas), 1) if notas else None,
                "flags": sorted(flags.items(), key=lambda x: -x[1])[:5]}

    r = await executar_passo(ctx, step_key="investigar", ordinal=1,
                             nome="Investigar a queda de qualidade",
                             step_type="analysis", fn=_investigar)

    if not r["amostras"]:
        return ("Não há conversas auditadas nas últimas 48h. "
                "Sem amostra não dá para afirmar nada sobre a qualidade.")
    if not r["flags"]:
        return (f"{r['amostras']} conversa(s) auditadas, nota média {r['media']}. "
                "Nenhum padrão dominante — a queda não se concentra em um motivo.")
    principal, vezes = r["flags"][0]
    return (f"{r['amostras']} conversa(s) auditadas, nota média {r['media']}. "
            f"Possível causa: '{principal}' apareceu {vezes} vez(es), mais que "
            f"qualquer outro padrão. Isso indica concentração, não comprova causa.")


@registrar_workflow("intelligence.memory_sweep")
async def varrer_memoria(ctx: dict) -> str:
    """Fecha sessoes inativas e produz memoria. SPEC-052 Lote 4."""
    from ..memory_fabric import MemoryFabric

    async def _fechar() -> Any:
        return await MemoryFabric(ctx["db"]).fechar_sessoes_inativas(limite=15)

    r = await executar_passo(ctx, step_key="fechar_sessoes", ordinal=1,
                             nome="Fechar conversas paradas e guardar o que importa",
                             step_type="analysis", fn=_fechar)
    return (f"{r.get('resumidas', 0)} sessão(ões) resumida(s) de "
            f"{r.get('avaliadas', 0)} avaliada(s).")
