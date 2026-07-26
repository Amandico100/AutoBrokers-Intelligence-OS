"""Pontes para Intelligence, Knowledge e Artifact Hub. SPEC-060 §28, §29, §27.

Três fronteiras, e cada uma existe para impedir um atalho tentador:

**Research → Signal (§28).** Mudança relevante vira sinal da SPEC-059. O que
NÃO vira: resultado de busca rotineiro, mudança cosmética, opinião isolada,
conteúdo velho reencontrado. Sem esse filtro, o Radar de Mercado viraria uma
máquina de notificação — e o corretor desligaria o produto inteiro.

**Research → Knowledge Candidate (§29).** Pesquisa **nunca** publica no
conhecimento global. Notícia passageira, relatório de concorrente, score de
SEO e lista de leads não são conhecimento durável. Só norma oficial, mudança
confirmada e documento oficial viram candidato — e mesmo esses passam por
curadoria humana.

**Research → Artifact (§27).** A peça sai pelo Artifact Hub da SPEC-057, com
a marca da corretora. Nenhum formato novo, nenhum renderizador paralelo.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# §28.1 — o que justifica interromper alguém.
MUDANCAS_QUE_VIRAM_SINAL = ("relevant", "major")

# §29.1 — origens elegíveis a conhecimento durável. A lista é curta e cada
# item exige fonte oficial ou confirmação.
CLAIMS_ELEGIVEIS = ("regulatory",)


def _agora() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Intelligence — §28
# ---------------------------------------------------------------------------


class IntelligenceAdapter:
    def __init__(self, supabase_client: Any):
        self.raw = supabase_client
        self.db = getattr(supabase_client, "client", supabase_client)

    def sinal_de_observacao(self, *, company_id: str, monitor: dict,
                            observacao: dict) -> Optional[dict]:
        """Observação relevante → Intelligence Signal. §22.5 e §28.

        A checagem é dupla de propósito: aqui, e no CHECK do banco. Um caminho
        novo que esqueça esta função ainda esbarra na constraint — e um bug
        aqui não consegue transformar mudança de banner em alerta.
        """
        classe = str(observacao.get("change_class") or "")
        score = float(observacao.get("significance_score") or 0)
        if classe not in MUDANCAS_QUE_VIRAM_SINAL or score < 50:
            return None

        from ..intelligence.schemas import (TIER_DOCUMENTO, SignalDraft,
                                            evidencia)
        from ..intelligence.signal_service import SignalService
        from ..intelligence.dedupe_service import chave_de_sinal

        evid = observacao.get("evidence") or {}
        termos = evid.get("termos") or []
        nome = str(monitor.get("name") or "fonte monitorada")

        resumo = str(observacao.get("summary") or "Uma fonte monitorada mudou.")
        if termos:
            resumo = (f"{nome}: a fonte mudou em trecho que menciona "
                      f"{', '.join(termos[:3])}.")

        rascunho = SignalDraft(
            company_id=company_id,
            # `research_update_future` é o tipo que a SPEC-059 §9 reservou
            # justamente para isto. Ele deixa de ser "futuro" aqui.
            signal_type="research_update_future",
            subject_type="research_monitor",
            subject_id=str(monitor.get("id")),
            summary_redacted=resumo,
            dedupe_key=chave_de_sinal(
                company_id=company_id, signal_type="research_update_future",
                subject_type="research_monitor", subject_id=str(monitor.get("id")),
                rule_key="research.monitor", rule_version="1.0.0",
                parametros={"hash": str(observacao.get("content_hash") or "")[:16]}),
            # Tier 2: é documento/página oficial observada, não dado do nosso
            # banco (Tier 0) nem inferência (Tier 5).
            trust_tier=TIER_DOCUMENTO,
            source_type="research", source_ref=str(observacao.get("id") or ""),
            rule_key="research.monitor", rule_version="1.0.0",
            severity="high" if classe == "major" else "medium",
            confidence=0.85,
            impact_score=min(100.0, score),
            urgency_score=60.0 if classe == "major" else 40.0,
            actionability_score=55.0, freshness_score=100.0,
            metadata={"monitor": nome, "change_class": classe,
                      "significance": score, "termos": termos},
            evidencias=[evidencia(
                tipo="mudanca", sistema="research_monitor",
                ref=f"observation:{observacao.get('id')}",
                resumo=resumo, tier=TIER_DOCUMENTO,
                valores={"classe": classe, "score": score,
                         "trechos_novos": len(evid.get("novos") or [])})],
        )

        criado = SignalService(self.raw).registrar(rascunho)
        if criado and criado.get("id") and observacao.get("id"):
            try:
                # `status` e `signal_id` são os únicos campos que o append-only
                # de observações permite atualizar — exatamente para isto.
                self.db.table("research_observations").update({
                    "signal_id": criado["id"], "status": "promoted",
                }).eq("id", observacao["id"]).execute()
            except Exception as exc:  # noqa: BLE001
                logger.warning("[Research→Signal] vínculo: %s", type(exc).__name__)
        return criado

    def sinal_de_pesquisa(self, *, company_id: str, resultado: Any,
                          origem: str = "user") -> Optional[dict]:
        """Achado de pesquisa que merece entrar no Briefing — §28.3.

        Filtro de §28.2 + a regra transversal da SPEC-059: **pesquisa que a
        própria plataforma disparou não é sinal de mercado da corretora.**
        """
        from ..intelligence.origem import pesquisa_e_interna

        if pesquisa_e_interna({"requested_by_kind": origem}):
            return None

        claims = getattr(resultado, "claims", None) or []
        regulatorios = [c for c in claims
                        if c.get("claim_type") == "regulatory"
                        and c.get("status") in ("supported", "partially_supported")
                        and int(c.get("official_citation_count") or 0) > 0]
        if not regulatorios:
            # §28.2 — resultado de busca rotineiro não vira sinal.
            return None

        from ..intelligence.dedupe_service import chave_de_sinal
        from ..intelligence.schemas import (TIER_DOCUMENTO, SignalDraft,
                                            evidencia)
        from ..intelligence.signal_service import SignalService

        principal = regulatorios[0]
        texto = str(principal.get("claim_text") or "")[:400]
        rascunho = SignalDraft(
            company_id=company_id,
            signal_type="compliance_risk",
            subject_type="research_finding",
            subject_id=str(principal.get("claim_key") or "")[:64],
            summary_redacted=f"Fonte oficial indica: {texto}",
            dedupe_key=chave_de_sinal(
                company_id=company_id, signal_type="compliance_risk",
                subject_type="research_finding",
                subject_id=str(principal.get("claim_key") or "")[:64],
                rule_key="research.regulatory", rule_version="1.0.0"),
            trust_tier=TIER_DOCUMENTO,
            source_type="research",
            source_ref=str(getattr(resultado, "request_id", "") or ""),
            rule_key="research.regulatory", rule_version="1.0.0",
            severity="medium", confidence=float(principal.get("confidence") or 0.7),
            impact_score=60.0, urgency_score=45.0, actionability_score=50.0,
            freshness_score=100.0,
            metadata={"claims_regulatorios": len(regulatorios)},
            evidencias=[evidencia(
                tipo="claim", sistema="research",
                ref=f"claim:{principal.get('id')}",
                resumo=texto, tier=TIER_DOCUMENTO,
                valores={"citacoes_oficiais": principal.get("official_citation_count")})],
        )
        return SignalService(self.raw).registrar(rascunho)

    def sinal_de_radar(self, *, company_id: str, mudancas: list[dict],
                       periodo_dias: int,
                       artifact_id: Optional[str] = None) -> Optional[dict]:
        """O fechamento semanal do Radar — §37.

        É um sinal DIFERENTE do de cada mudança. Cada verificação já avisou o
        que mudou naquele dia; este avisa que existe uma leitura consolidada do
        período, e é o que o corretor abre quando quer entender o conjunto em
        vez de um item.

        Sem mudança, sem sinal: `mudancas` vazio devolve `None` antes de tocar
        no Fabric. Um radar que avisa toda semana mesmo sem novidade é o
        primeiro card que o corretor aprende a fechar sem ler.
        """
        if not mudancas:
            return None

        from ..intelligence.dedupe_service import chave_de_sinal
        from ..intelligence.schemas import (TIER_DOCUMENTO, SignalDraft,
                                            evidencia)
        from ..intelligence.signal_service import SignalService

        maiores = [m for m in mudancas if m.get("change_class") == "major"]
        # A janela entra na chave: o radar da semana passada e o desta são
        # fatos distintos, e sem ela o dedupe engoliria o segundo.
        janela = str((mudancas[0].get("observed_at") or ""))[:10]
        resumo = (f"{len(mudancas)} mudança(s) nas fontes oficiais nos últimos "
                  f"{periodo_dias} dias"
                  + (f", {len(maiores)} em trecho de norma ou prazo."
                     if maiores else "."))

        rascunho = SignalDraft(
            company_id=company_id,
            signal_type="compliance_risk" if maiores else "research_update_future",
            subject_type="research_monitor",
            subject_id="radar",
            summary_redacted=resumo,
            dedupe_key=chave_de_sinal(
                company_id=company_id,
                signal_type="compliance_risk" if maiores else "research_update_future",
                subject_type="research_monitor", subject_id="radar",
                rule_key="research.radar", rule_version="1.0.0",
                parametros={"janela": janela}),
            trust_tier=TIER_DOCUMENTO,
            source_type="research",
            source_ref=str(artifact_id or ""),
            rule_key="research.radar", rule_version="1.0.0",
            severity="high" if maiores else "medium",
            confidence=0.9,
            impact_score=70.0 if maiores else 45.0,
            urgency_score=55.0 if maiores else 30.0,
            actionability_score=60.0, freshness_score=100.0,
            metadata={"periodo_dias": periodo_dias,
                      "mudancas": len(mudancas),
                      "maiores": len(maiores),
                      "artifact_id": artifact_id},
            evidencias=[evidencia(
                tipo="mudanca", sistema="research_monitor",
                ref=f"observation:{m.get('id')}",
                resumo=str(m.get("summary") or "")[:300],
                tier=TIER_DOCUMENTO,
                valores={"classe": m.get("change_class"),
                         "fonte": m.get("fonte")})
                for m in mudancas[:5]],
        )
        return SignalService(self.raw).registrar(rascunho)


# ---------------------------------------------------------------------------
# Knowledge — §29
# ---------------------------------------------------------------------------


class KnowledgeAdapter:
    def __init__(self, supabase_client: Any):
        self.raw = supabase_client

    def propor(self, *, company_id: str, claims: list[dict],
               citacoes: dict[str, list[dict]]) -> list[dict]:
        """Claims elegíveis → Knowledge Candidate. NUNCA publicação — §29.3.

        Elegibilidade é dupla: o tipo do claim (só regulatório) **e** a
        existência de citação oficial. Um claim regulatório sem fonte oficial
        é justamente o que não pode entrar no cérebro de todas as corretoras.
        """
        from ..intelligence.knowledge_candidate_adapter import \
            KnowledgeCandidateAdapter

        adaptador = KnowledgeCandidateAdapter(self.raw)
        propostos: list[dict] = []

        for c in claims:
            if c.get("claim_type") not in CLAIMS_ELEGIVEIS:
                continue
            if c.get("status") not in ("supported", "partially_supported"):
                continue
            if int(c.get("official_citation_count") or 0) < 1:
                continue

            evidencias = [{
                "url": x.get("url"), "trecho": x.get("source_excerpt"),
                "tier": x.get("source_trust_tier"),
                "oficial": x.get("source_official"),
            } for x in citacoes.get(str(c.get("id")), [])[:5]]

            candidato = adaptador.propor(
                origem="conhecimento_de_dominio_com_fonte",
                titulo=str(c.get("claim_text") or "")[:180],
                texto=str(c.get("claim_text") or ""),
                company_id=company_id, escopo="company",
                # Tier 2: documento oficial. Não é Tier 0 porque o que chegou
                # aqui é a LEITURA do documento, não o dado do nosso banco.
                trust_tier=2,
                fontes=int(c.get("official_citation_count") or 1),
                evidencias=evidencias,
                source_ref=f"research_claim:{c.get('id')}",
                candidate_type="regulation")
            if candidato:
                adaptador.checar_contradicao(candidato)
                propostos.append(candidato)
        return propostos


# ---------------------------------------------------------------------------
# Artifact — §27
# ---------------------------------------------------------------------------


# §27.1 — a forma da peça segue o TIPO de pesquisa, não o assunto.
#
# Todos os modos produziam `research.market_brief` porque era o único template
# de pesquisa que existia. O resultado era um dossiê narrativo entregando uma
# lista de empresas: a informação estava lá e o corretor não conseguia usar.
# Os templates novos vivem no mesmo catálogo da SPEC-057 — nenhum motor de
# peça foi criado aqui.
TEMPLATE_POR_MODO = {
    "claim_check": "research.evidence_pack",
    "site_audit": "research.site_audit",
    "business_discovery": "research.company_list",
    "monitor": "research.change_report",
}

# Pesquisa sobre norma vira radar regulatório mesmo em modo verificado: a
# separação entre publicação e vigência é o que o corretor precisa ver, e o
# dossiê narrativo não tem onde mostrá-la.
_TERMOS_REGULATORIOS = ("susep", "cnsp", "circular", "resolução", "resolucao",
                        "norma", "regulament", "legislaç", "legislac")


def template_do_modo(modo: str, pergunta: str = "") -> str:
    especifico = TEMPLATE_POR_MODO.get((modo or "").strip().lower())
    if especifico:
        return especifico
    if any(t in (pergunta or "").lower() for t in _TERMOS_REGULATORIOS):
        return "research.regulatory_radar"
    return "research.market_brief"


class ArtifactAdapter:
    def __init__(self, supabase_client: Any):
        self.raw = supabase_client
        self.db = getattr(supabase_client, "client", supabase_client)

    def dossie(self, *, company_id: str, resultado: Any,
               citacoes: dict[str, list[dict]],
               work_run_id: Optional[str] = None) -> Optional[str]:
        """Gera o dossiê pelo Artifact Hub da SPEC-057."""
        from ..artifacts.service import ArtifactService

        composicao = self.compor_dossie(resultado, citacoes)
        try:
            servico = ArtifactService(self.raw)
            r = servico.criar(
                company_id=company_id,
                title=_titulo_do_dossie(resultado),
                template_key=template_do_modo(resultado.modo, resultado.pergunta),
                payload={"pergunta": resultado.pergunta,
                         "modo": resultado.modo,
                         "resumo": resultado.resumo},
                composition=composicao,
                subtitle=f"Pesquisa · {resultado.modo}",
                summary=resultado.resumo,
                kind="report", origin="chat", work_run_id=work_run_id,
                data_sources=_fontes_do_dossie(resultado))
            versao = (r.get("version") or {}).get("id")
            if versao:
                servico.renderizar(company_id=company_id, version_id=versao)
                servico.publicar(company_id=company_id, version_id=versao)
            return (r.get("artifact") or {}).get("id")
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Research] dossiê não gerado: %s", type(exc).__name__)
            return None

    def compor_dossie(self, resultado: Any,
                      citacoes: dict[str, list[dict]]) -> list[dict]:
        """Blocos do Artifact Hub. Pura, e **sem recalcular nada**.

        §27.2 exige que o dossiê carregue pergunta, escopo, data, metodologia,
        claims, fontes, limitações e conflitos. Cada um vem pronto do
        resultado — se esta função calculasse qualquer coisa, o PDF e a tela
        poderiam divergir.
        """
        claims = getattr(resultado, "claims", []) or []
        sustentados = [c for c in claims
                       if c.get("status") in ("supported", "partially_supported")]
        oficiais = [c for c in sustentados
                    if int(c.get("official_citation_count") or 0) > 0]

        blocos: list[dict] = [{
            "block": "cover",
            "props": {"eyebrow": "Dossiê de pesquisa",
                      "title": _titulo_do_dossie(resultado),
                      "subtitle": resultado.pergunta[:200],
                      "verdict": resultado.resumo,
                      "headline_label": "afirmações com fonte",
                      "headline_value": str(len(sustentados))},
        }, {
            "block": "kpis",
            "props": {"title": "O que sustenta este dossiê",
                      "items": [
                          {"label": "Afirmações verificadas", "value": str(len(sustentados))},
                          {"label": "Com fonte oficial", "value": str(len(oficiais))},
                          {"label": "Fontes lidas", "value": str(len(resultado.fontes))},
                          {"label": "Publishers distintos",
                           "value": str(resultado.diversidade_de_publishers)},
                      ]},
        }]

        if sustentados:
            blocos.append({"block": "table", "props": {
                "eyebrow": "Achados", "title": "O que as fontes dizem",
                "columns": [{"key": "afirmacao", "label": "Afirmação"},
                            {"key": "base", "label": "Base"},
                            {"key": "confianca", "label": "Confiança", "align": "right"}],
                "rows": [{
                    "afirmacao": str(c.get("claim_text") or "")[:280],
                    "base": ("fonte oficial"
                             if int(c.get("official_citation_count") or 0)
                             else f"{c.get('citation_count') or 0} fonte(s)"),
                    "confianca": f"{float(c.get('confidence') or 0) * 100:.0f}%",
                } for c in sustentados[:15]]}})

        if resultado.contradicoes:
            blocos.append({"block": "callout", "props": {
                "title": "As fontes divergem", "tone": "warning",
                "text": ("Encontramos afirmações que se contradizem. Elas estão "
                         "no dossiê com os dois lados, e a confiança foi "
                         "reduzida — nenhuma delas deve ser usada como "
                         "definitiva sem conferir a fonte.")}})

        if resultado.limitacoes:
            blocos.append({"block": "prose", "props": {
                "eyebrow": "Transparência", "title": "O que este dossiê não afirma",
                "text": "\n\n".join(f"• {l}" for l in resultado.limitacoes[:8])}})

        blocos.append({"block": "prose", "props": {
            "eyebrow": "Como foi feito", "title": "Metodologia",
            "text": (
                f"Pergunta: {resultado.pergunta}\n\n"
                f"Modo de pesquisa: {resultado.modo}. Cada afirmação acima "
                f"aponta para a fonte de onde saiu, com a data em que foi "
                f"recuperada. Conteúdo da web foi tratado como dado não "
                f"confiável e passou por sanitização antes de qualquer "
                f"leitura.\n\nFontes que não puderam ser abertas estão "
                f"declaradas nas limitações — nenhuma foi contornada.")}})

        blocos.append({"block": "sources", "props": {
            "title": "Fontes consultadas",
            "note": ("Toda afirmação numérica ou regulatória deste dossiê vem "
                     "de uma das fontes acima.")}})
        blocos.append({"block": "footer", "props": {
            "disclaimer": ("Este dossiê reúne informação pública com fonte e "
                           "data. Não é parecer jurídico nem confirma cobertura "
                           "de apólice específica.")}})
        return blocos


def _titulo_do_dossie(resultado: Any) -> str:
    pergunta = (getattr(resultado, "pergunta", "") or "").strip()
    if len(pergunta) <= 90:
        return pergunta or "Dossiê de pesquisa"
    return pergunta[:87].rstrip() + "…"


def _fontes_do_dossie(resultado: Any) -> list[dict]:
    saida = []
    for f in (getattr(resultado, "fontes", []) or [])[:12]:
        saida.append({
            "rotulo": (f.get("titulo") or f.get("url") or "fonte")[:80],
            "detalhe": f.get("url") or "",
            "data": (f.get("recuperado_em") or "")[:10],
        })
    return saida
