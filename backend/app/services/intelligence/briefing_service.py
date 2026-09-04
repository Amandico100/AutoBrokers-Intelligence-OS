"""Briefing Diario e Executivo Semanal. SPEC-059 §16, §24, §28.

Uma publicacao, varias saidas
-----------------------------
§17.2 exige que web, PDF e resumo curto venham da MESMA publicacao. Aqui isso
e literal: `compor()` produz o Briefing Spec, e todo canal renderiza a partir
dele. Se o resumo do WhatsApp fosse gerado separado, ele divergiria da tela em
algum momento — e o corretor descobriria isso na frente de um cliente.

Secao vazia nao vira texto
--------------------------
§16.1 proibe preencher secao vazia com frase generica, e §24.2 da o exemplo:
"a qualidade permaneceu estavel" e PROIBIDO quando nao ha conversas auditadas
suficientes; o certo e dizer que nao ha dado. Por isso `compor()` monta a
secao "O que ainda nao da para afirmar" a partir do que faltou — em vez de
esconder a ausencia.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from typing import Any, Optional

from .delivery_policy import _tz
from .redaction_service import redigir
from .signal_service import registrar_evento

logger = logging.getLogger(__name__)

SCHEMA_VERSION = "1.0"

# §16.1 — as oito secoes do briefing diario, na ordem em que sao lidas.
SECOES_DIARIO = [
    ("precisa_de_voce", "Precisa de você"),
    ("riscos", "Riscos e bloqueios"),
    ("oportunidades", "Oportunidades"),
    ("em_andamento", "Trabalhos em andamento"),
    ("concluido", "Resultados concluídos"),
    ("automacao", "Automação sugerida"),
    ("faltando", "O que ainda não dá para afirmar"),
]

SECOES_SEMANAL = [
    ("resumo", "Resumo executivo"),
    ("indicadores", "Indicadores disponíveis"),
    ("mudancas", "Principais mudanças"),
    ("gargalos", "Gargalos"),
    ("qualidade", "Qualidade"),
    ("trabalhos", "Trabalhos e Auxiliares"),
    ("custos", "Custos"),
    ("resultados", "Resultados"),
    ("riscos", "Riscos"),
    ("oportunidades", "Oportunidades"),
    ("decisoes", "Decisões recomendadas"),
    ("plano", "Plano da próxima semana"),
]

# Para qual secao vai cada tipo de Finding.
SECAO_POR_FINDING = {
    "aprovacao_parada": "precisa_de_voce",
    "portal_bloqueado": "precisa_de_voce",
    "conexao_indisponivel": "riscos",
    "falha_recorrente": "riscos",
    "trabalho_travado": "riscos",
    "queda_de_qualidade": "riscos",
    "custo_no_limite": "riscos",
    "fila_acumulada": "precisa_de_voce",
    "tarefa_repetida": "automacao",
    "pedido_nao_atendido": "faltando",
    "resultado_do_periodo": "concluido",
    "dor_declarada": "oportunidades",
    "risco_relacionamento": "riscos",
}


def _agora() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# 🔴 SPEC-095 · D.5 — o briefing conta o trabalho DA CORRETORA, não o relógio
# ---------------------------------------------------------------------------
#
# 📊 Medido em 04/09/2026: `work_runs` da Resulta tem **1.228** linhas na vida,
# **1.214 (98,86%) com `source_type='system'`** — `intelligence.detect_signals`
# rodou 953 vezes para produzir 32 sinais. Pedidos pela corretora: `chat` 7 +
# `routine` 7.
#
# 📊 E o efeito no que o dono lê: **40 de 41** itens de trabalho dos 5 últimos
# briefings vinham de Work Run `system` — 70,2% de todos os 57 itens. No
# briefing de 04/09, 6 dos 14 itens eram o MESMO ciclo do tick repetido
# ("Procurar o que mudou na operação · 0 regra(s) executada(s)…" ×4 e "· 0%
# concluído" ×2). A manchete do semanal de 31/08 anunciava "20 trabalho(s)
# entregue(s)": eram 20 voltas do relógio.
#
# ⛔ A regra é uma CONSTANTE nomeada, e não um literal no meio de um `if`:
# o guarda [D5] a reintroduz por mutação e tem de ficar vermelho.
ORIGEM_DO_RELOGIO = "system"


#: O que CONTA como trabalho pedido — a MESMA regra do placar (INCLUSÃO,
#: `CONTA_COMO_TRABALHO` em `app/api/dashboard/relatorios/placar/route.ts`).
#: 📊 04/09/2026, red team: aqui `source_type` ausente contava como pedido e no
#: placar como não-trabalho — duas políticas para a mesma pergunta. Hoje
#: `source_type is null` = 0 linhas; a regra única existe para quando não for.
ORIGENS_PEDIDAS = ("chat", "routine")


def _do_relogio(w: dict) -> bool:
    """Este Work Run é o sistema se olhando, e não trabalho pedido?

    Regra de INCLUSÃO: só `chat` e `routine` são trabalho da corretora. O
    `system` (📊 98,86% dos Work Runs) é o caso principal, nomeado em
    `ORIGEM_DO_RELOGIO`; um `source_type` novo ou ausente fica FORA até alguém
    o declarar pedido — a mesma decisão fechada do placar.
    """
    origem = str(w.get("source_type") or "")
    if origem == ORIGEM_DO_RELOGIO:
        return True
    return origem not in ORIGENS_PEDIDAS


def _colapsar_runs(rows: list[dict]) -> list[dict]:
    """Work Runs iguais viram UM. Chave declarada: `(outcome_title, status)`.

    📊 No briefing de 04/09 da Resulta, 6 dos 14 itens eram o MESMO Work Run
    repetido — "Procurar o que mudou na operação · 0 regra(s) executada(s), 0
    sinal(is) registrado(s)" ×4 e "· 0% concluído" ×2.

    O contador vai no próprio dicionário (`_iguais`), e não numa estrutura ao
    lado: quem lê a lista depois não tem como esquecer de olhar a outra.
    """
    vistos: dict = {}
    saida: list[dict] = []
    for w in rows:
        k = (str(w.get("outcome_title") or ""), str(w.get("status") or ""))
        if k in vistos:
            vistos[k]["_iguais"] = int(vistos[k].get("_iguais") or 0) + 1
            continue
        copia = dict(w)
        vistos[k] = copia
        saida.append(copia)
    return saida


def _colapsar(itens: list["ItemDeBriefing"],
              chave) -> list["ItemDeBriefing"]:
    """Itens iguais viram UM, com "(+N iguais)" no fim da manchete.

    🔴 A chave de colapso é DECLARADA por quem chama (SPEC-095 §3 ③, Datadog
    Watchdog): itens por `(headline, summary)`, Work Runs por `(outcome_title,
    status)`. Uma chave implícita — "parecem iguais" — não dá para conferir
    depois, e a primeira duplicata que ela deixasse passar seria invisível.
    """
    vistos: dict = {}
    saida: list[ItemDeBriefing] = []
    for i in itens:
        k = chave(i)
        if k in vistos:
            vistos[k].iguais += 1
            continue
        vistos[k] = i
        saida.append(i)
    for i in saida:
        if i.iguais:
            i.headline = "%s (+%d iguais)" % (i.headline, i.iguais)
    return saida


def primeira_frase(texto: str) -> str:
    """A 1ª frase de um texto. Vazio devolve vazio.

    ⚠️ Corta no primeiro `.`/`!`/`?` **seguido de espaço ou fim**. Sem a
    exigência do espaço, "R$ 1.234,00 parados" viraria "R$ 1." — e o resumo do
    briefing passaria a mentir sobre dinheiro.
    """
    t = " ".join(str(texto or "").split())
    if not t:
        return ""
    for pos, ch in enumerate(t):
        if ch in ".!?" and (pos + 1 >= len(t) or t[pos + 1] == " "):
            return t[: pos + 1]
    return t


def resto_das_frases(texto: str) -> str:
    """O que sobra depois da 1ª frase."""
    t = " ".join(str(texto or "").split())
    primeira = primeira_frase(t)
    return t[len(primeira):].strip() if len(primeira) < len(t) else ""


#: 🔴 As colunas que a tabela `briefing_items` REALMENTE tem, medidas em
#: 04/09/2026 (`select * from briefing_items limit 1` → 18 colunas, sem
#: `why_now`, sem `next_step`, sem `iguais`).
#:
#: ⛔ Por que esta lista existe: `publicar()` insere `{**item.como_dict(i)}` —
#: TODA chave do dicionário vira coluna. E o insert mora dentro de um
#: `try/except` que só escreve um `warning`: uma chave a mais faria a tabela
#: **parar de receber linhas em silêncio**, e ninguém veria por semanas.
#:
#: A SPEC-095 tem ZERO migration por trava (§2), e os campos novos não precisam
#: de coluna: eles chegam à tela pelo `payload` jsonb da publicação
#: (`como_payload` → `sections[].items[]`), que é de onde o detalhe lê. A
#: tabela é o índice relacional; o jsonb é o conteúdo.
COLUNAS_DE_BRIEFING_ITEMS = (
    "item_type", "section", "position", "headline", "summary",
    "evidence_summary", "confidence", "action_label", "action_payload",
    "priority_score", "finding_id", "recommendation_id", "work_run_id",
    "artifact_id",
)


def so_as_colunas_da_tabela(item: dict) -> dict:
    """O item do jsonb reduzido ao que `briefing_items` sabe guardar."""
    return {k: v for k, v in item.items() if k in COLUNAS_DE_BRIEFING_ITEMS}


@dataclass
class ItemDeBriefing:
    item_type: str
    section: str
    headline: str
    summary: str = ""
    evidence_summary: Optional[str] = None
    confidence: Optional[float] = None
    action_label: Optional[str] = None
    action_payload: dict = field(default_factory=dict)
    priority_score: float = 0.0
    finding_id: Optional[str] = None
    recommendation_id: Optional[str] = None
    work_run_id: Optional[str] = None
    artifact_id: Optional[str] = None
    #: 🔴 SPEC-095 · D.3. O porquê e o próximo passo do achado.
    #:
    #: 📊 Medido em 04/09/2026 em `intelligence_findings` da Resulta: `why_now`
    #: preenchido em **12/12** e `next_step` em **11/12**. Este dataclass não
    #: tinha campo para nenhum dos dois, e `como_dict` — o jsonb que vira
    #: `payload.sections[].items[]` e chega à tela — não os emitia. **O porquê
    #: e o próximo passo morriam uma chamada antes da tela**, todo dia, em
    #: todas as corretoras.
    why_now: Optional[str] = None
    next_step: Optional[str] = None
    #: Quantos itens IDÊNTICOS este item representa (SPEC-095 · D.5). 0 = só
    #: ele. 📊 35,1% dos itens dos 5 últimos briefings da Resulta eram cópia
    #: exata de outro do MESMO briefing.
    iguais: int = 0

    def como_dict(self, posicao: int) -> dict:
        return {
            "item_type": self.item_type, "section": self.section,
            "position": posicao, "headline": self.headline,
            "summary": self.summary, "evidence_summary": self.evidence_summary,
            "confidence": self.confidence, "action_label": self.action_label,
            "action_payload": self.action_payload,
            "priority_score": self.priority_score,
            "finding_id": self.finding_id,
            "recommendation_id": self.recommendation_id,
            "work_run_id": self.work_run_id, "artifact_id": self.artifact_id,
            "why_now": self.why_now, "next_step": self.next_step,
            "iguais": self.iguais,
        }


@dataclass
class BriefingSpec:
    """O payload estruturado de §24. Uma so fonte para todos os canais."""

    briefing_type: str
    company_id: str
    period_start: str
    period_end: str
    headline: str
    executive_summary: str
    secoes: list[dict] = field(default_factory=list)
    itens: list[ItemDeBriefing] = field(default_factory=list)
    missing_data: list[str] = field(default_factory=list)
    methodology: str = ""
    sources_summary: list[str] = field(default_factory=list)
    user_id: Optional[str] = None
    profile_id: Optional[str] = None
    schema_version: str = SCHEMA_VERSION

    def content_hash(self) -> str:
        base = json.dumps(
            {"h": self.headline, "i": [i.headline for i in self.itens],
             "p": [self.period_start, self.period_end], "t": self.briefing_type},
            sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(base.encode("utf-8")).hexdigest()[:40]

    def como_payload(self) -> dict:
        por_secao: dict[str, list] = {}
        for i, item in enumerate(self.itens):
            por_secao.setdefault(item.section, []).append(item.como_dict(i))
        return {
            "schema_version": self.schema_version,
            "briefing_type": self.briefing_type,
            "company_id": self.company_id,
            "user_id": self.user_id,
            "profile_id": self.profile_id,
            "period": {"start": self.period_start, "end": self.period_end},
            "headline": self.headline,
            "executive_summary": self.executive_summary,
            "sections": [{"key": k, "title": t, "items": por_secao.get(k, [])}
                         for k, t in self.secoes],
            "missing_data": self.missing_data,
            "methodology": self.methodology,
            "sources_summary": self.sources_summary,
            "created_at": _agora().isoformat(),
        }


# ---------------------------------------------------------------------------
# Composicao — pura
# ---------------------------------------------------------------------------


def compor(
    *, company_id: str, briefing_type: str,
    findings: list[dict], recomendacoes: list[dict],
    trabalhos_em_curso: list[dict], resultados: list[dict],
    outcomes: list[dict], faltando: list[str],
    period_start: datetime, period_end: datetime,
    max_itens: int = 7, user_id: Optional[str] = None,
    profile_id: Optional[str] = None,
) -> BriefingSpec:
    """Monta o Briefing Spec. Sem banco, sem LLM, sem numero novo.

    Todo numero que aparece no briefing ja existe em um Finding ou em um
    registro do Work OS. Este modulo **soma e ordena**; nao calcula
    indicador novo. Se calculasse, existiriam duas versoes do mesmo numero e
    uma delas estaria errada em algum momento.
    """
    secoes = SECOES_SEMANAL if briefing_type == "weekly_executive" else SECOES_DIARIO
    rec_por_finding: dict[str, dict] = {}
    for r in recomendacoes:
        if r.get("finding_id"):
            rec_por_finding[str(r["finding_id"])] = r

    # 🔴 SPEC-095 · D.5: o relógio da plataforma sai AQUI, dentro da função
    # pura — e não na consulta. É `compor` que o guarda executa, e uma regra
    # que morasse só no SELECT ficaria sem teste possível.
    trabalhos_em_curso = _colapsar_runs(
        [w for w in trabalhos_em_curso if not _do_relogio(w)])
    resultados = _colapsar_runs([w for w in resultados if not _do_relogio(w)])

    itens: list[ItemDeBriefing] = []
    criticos = 0

    for f in sorted(findings, key=lambda x: -float(x.get("priority_score") or 0)):
        secao = SECAO_POR_FINDING.get(str(f.get("finding_type") or ""),
                                      "riscos" if briefing_type == "weekly_executive"
                                      else "precisa_de_voce")
        if briefing_type == "weekly_executive" and secao == "precisa_de_voce":
            secao = "gargalos"
        if str(f.get("severity")) == "critical":
            criticos += 1
        rec = rec_por_finding.get(str(f.get("id")))

        # 🔴 SPEC-095 · D.3. Quando o achado é do tipo PADRÃO do Fabric, o
        # título dele é a string estática "Ponto de atenção" — 📊 3/3 findings
        # da Resulta, 2 com o resumo idêntico. A causa está em
        # `finding_engine.py:200`: `NARRATIVAS.get(tipo, NARRATIVA_PADRAO)`, e
        # `commercial_opportunity` não tem entrada lá (0 hits, 04/09/2026).
        #
        # O conserto no Fabric é a P-095-NARRATIVA-DO-FABRIC (SPEC-059: 3
        # `signal_type` + 3 Narrativas). Aqui o briefing contorna pela frente:
        # o `summary_redacted` que a SPEC-095 · D.1 passou a gravar JÁ é
        # "{título}. {porquê} {ação}" — então a 1ª frase é a manchete e o resto
        # é o resumo. ⛔ Só para `observacao`: nos tipos que têm Narrativa
        # própria, o título já é o título, e cortá-lo pioraria.
        titulo = str(f.get("title") or "Ponto de atenção")
        resumo = str(f.get("summary") or "")
        if str(f.get("finding_type") or "") == "observacao":
            cabeca = primeira_frase(resumo)
            cauda = resto_das_frases(resumo)
            if cabeca and cauda:
                titulo, resumo = cabeca.rstrip("."), cauda

        itens.append(ItemDeBriefing(
            item_type="finding", section=secao,
            headline=titulo,
            summary=resumo,
            why_now=str(f.get("why_now") or "") or None,
            next_step=str(f.get("next_step") or "") or None,
            evidence_summary=str(f.get("fact_statement") or "") or None,
            confidence=float(f.get("confidence") or 0) or None,
            action_label=(_rotulo_da_acao(rec) if rec else None),
            action_payload=({"recommendation_id": str(rec["id"]),
                             "action_key": rec.get("recommended_action_key")}
                            if rec else {}),
            priority_score=float(f.get("priority_score") or 0),
            finding_id=str(f.get("id")),
            recommendation_id=str(rec["id"]) if rec else None,
        ))

    for r in recomendacoes:
        if r.get("finding_id") and str(r["finding_id"]) in {str(f.get("id")) for f in findings}:
            continue  # ja apareceu junto do Finding
        itens.append(ItemDeBriefing(
            item_type="recommendation",
            section="automacao" if r.get("recommendation_type") == "propor_automacao"
                    else "oportunidades",
            headline=str(r.get("title") or "Sugestão"),
            summary=str(r.get("summary") or ""),
            confidence=float(r.get("confidence") or 0) or None,
            action_label=_rotulo_da_acao(r),
            action_payload={"recommendation_id": str(r["id"])},
            priority_score=float(r.get("priority_score") or 0),
            recommendation_id=str(r["id"])))

    for w in trabalhos_em_curso[:5]:
        itens.append(ItemDeBriefing(
            item_type="work_run",
            section="trabalhos" if briefing_type == "weekly_executive" else "em_andamento",
            headline=str(w.get("outcome_title") or "Trabalho em andamento"),
            summary=f"{int(w.get('progress_percent') or 0)}% concluído.",
            priority_score=10.0, work_run_id=str(w.get("id")),
            iguais=int(w.get("_iguais") or 0)))

    for w in resultados[:5]:
        itens.append(ItemDeBriefing(
            item_type="result",
            section="resultados" if briefing_type == "weekly_executive" else "concluido",
            headline=str(w.get("outcome_title") or "Trabalho concluído"),
            summary=str(w.get("result_summary") or "")[:200],
            priority_score=5.0, work_run_id=str(w.get("id")),
            iguais=int(w.get("_iguais") or 0)))

    for o in outcomes[:5]:
        itens.append(ItemDeBriefing(
            item_type="result",
            section="resultados" if briefing_type == "weekly_executive" else "concluido",
            headline=_rotulo_de_outcome(o),
            summary=str(o.get("value_summary") or ""),
            confidence=float(o.get("confidence") or 0) or None,
            priority_score=6.0))

    for texto in faltando:
        itens.append(ItemDeBriefing(
            item_type="missing_data",
            section="faltando" if briefing_type != "weekly_executive" else "indicadores",
            headline=texto, priority_score=0.0))

    # Limite de itens: o teto vale para o que EXIGE acao. Resultado e dado
    # faltante nao competem com prioridade — se competissem, um dia cheio de
    # entregas empurraria para fora justamente o problema que precisa de
    # decisao.
    acionaveis = [i for i in itens if i.item_type in ("finding", "recommendation")]
    outros = [i for i in itens if i.item_type not in ("finding", "recommendation")]
    acionaveis.sort(key=lambda i: -i.priority_score)

    # 🔴 SPEC-095 · D.5 — o colapso, por chave DECLARADA (§3 ③).
    # 📊 20 de 57 itens (35,1%) dos 5 últimos briefings da Resulta eram cópia
    # exata de outro item do MESMO briefing.
    acionaveis = _colapsar(acionaveis, lambda i: (i.headline, i.summary))
    outros = _colapsar(outros, lambda i: (i.headline, i.summary))

    # 🔴 O que a manchete promete é o que a PEÇA contém. 📊 §1.3: `:269`
    # cortava em `max_itens` e `:314` contava a lista INTEIRA — a manchete
    # anunciava pontos que o briefing não tinha.
    ficaram = acionaveis[:max_itens]
    itens = ficaram + outros

    headline, resumo = _narrativa(briefing_type, ficaram, resultados, outcomes,
                                  criticos, faltando)

    return BriefingSpec(
        briefing_type=briefing_type, company_id=company_id,
        period_start=period_start.isoformat(), period_end=period_end.isoformat(),
        headline=headline, executive_summary=resumo,
        secoes=secoes, itens=itens, missing_data=faltando,
        methodology=("Contagens e comparações vêm direto do banco operacional. "
                     "Inferências aparecem marcadas como leitura, nunca como fato."),
        sources_summary=sorted({str(f.get("metadata", {}).get("signal_type") or "")
                                for f in findings if f.get("metadata")} - {""}),
        user_id=user_id, profile_id=profile_id)


def _rotulo_da_acao(rec: Optional[dict]) -> Optional[str]:
    if not rec:
        return None
    opcoes = rec.get("action_options") or []
    chave = rec.get("recommended_action_key")
    for o in opcoes:
        if o.get("key") == chave:
            return o.get("label")
    return None


def _rotulo_de_outcome(o: dict) -> str:
    return {
        "realized": "Resultado confirmado",
        "partially_realized": "Resultado parcial",
        "inconclusive": "Resultado inconclusivo",
        "negative": "A ação não ajudou",
    }.get(str(o.get("measurement_status")), "Medição")


def _narrativa(briefing_type: str, acionaveis: list[ItemDeBriefing],
               resultados: list[dict], outcomes: list[dict],
               criticos: int, faltando: list[str]) -> tuple[str, str]:
    """Manchete e resumo em uma frase. §16.1 e §24.1 · SPEC-095 · D.3.

    Sem itens acionaveis, a frase diz isso com todas as letras. Um briefing
    que sempre encontra algo urgente perde o significado do urgente.

    🔴 A manchete é o ACHADO, e não a contagem dele. 📊 Medido em 04/09/2026
    nas manchetes da Resulta de 26/08 a 04/09: "2 item(ns) esperando você hoje"
    ×5 — cinco DIAS diferentes, a mesma string —, "1 item(ns)…" ×2, "Nada
    precisa de você agora" ×2, "4 item(ns)…" ×1. Esta função só contava. O
    achado principal ("Fila acumulada — 61 atendimentos parados há mais de
    24h") era o item 1 do corpo e nunca chegava ao título.

    🔴 E `acionaveis` é a lista que FICOU na peça. 📊 §1.3: `compor` cortava em
    `max_itens` e passava a lista INTEIRA para cá — a manchete prometia pontos
    que o briefing não continha.

    ⛔ A frase "· M trabalho(s) pronto(s)" só existe com M > 0. 📊 Depois do
    D.5 (o relógio da plataforma fora), M = 0 em **5 de 5** dias medidos: um
    "0 trabalho(s) pronto(s)" fixo na manchete seria a mesma string todo dia,
    que é o defeito que esta função existe para consertar.
    """
    n = len(acionaveis)
    m = len(resultados)
    prontos = ("%d trabalho(s) pronto(s)" % m) if m else ""

    if briefing_type == "weekly_executive":
        if not n and not m:
            return ("Semana sem movimento registrado",
                    "Não houve trabalhos nem pontos de atenção registrados no período.")
        # O ramo semanal mantém a FORMA dele — contagem de decisões —, porque
        # o resumo da semana é sobre volume. Só o M ganhou a mesma regra.
        manchete = "%d ponto(s) de decisão" % n
        if m:
            manchete += " e %d trabalho(s) entregue(s)" % m
        resumo = ("A semana fechou com %d trabalho(s) concluído(s)" % m if m
                  else "A semana fechou sem trabalho pedido pela corretora")
        resumo += (" e %d ponto(s) esperando decisão." % n if n
                   else " e nada pendente de decisão.")
        return (manchete, resumo)

    if n:
        topo = acionaveis[0]
        manchete = topo.headline
        # "crítico:" só quando o TOPO é crítico. 📊 04/09/2026, red team:
        # `criticos` conta todos os findings críticos, mas `acionaveis` já
        # passou pelo corte de `max_itens` — o elo "há crítico ⇒ o topo é o
        # crítico" não estava medido no código (hoje vale: 87 > 81). O limiar é
        # o MESMO que `publicar()` usa para `critical_count`.
        if criticos and float(topo.priority_score or 0) >= 85:
            manchete = "crítico: %s" % manchete
        partes = [(primeira_frase(topo.summary) or topo.why_now
                   or topo.headline).rstrip(".")]
        if n > 1:
            partes.append("e mais %d ponto(s)" % (n - 1))
        if prontos:
            partes.append(prontos)
        return (manchete, " · ".join(partes))

    if m or outcomes:
        return ("Nada precisa de você hoje" + (" · %s" % prontos if prontos else ""),
                "%d trabalho(s) concluído(s) e nenhum ponto pendente." % m)
    if faltando:
        return ("Sem dados suficientes para um panorama",
                "Ainda não há registro suficiente no período para afirmar qualquer coisa.")
    return ("Nada precisa de você hoje", "Nenhum ponto de atenção no período.")


# ---------------------------------------------------------------------------
# Servico
# ---------------------------------------------------------------------------


class BriefingService:
    def __init__(self, supabase_client: Any):
        self.db = getattr(supabase_client, "client", supabase_client)

    # ------------------------------------------------------------------
    # Perfis
    # ------------------------------------------------------------------

    def perfil(self, company_id: str, *, cadencia: str = "daily",
               user_id: Optional[str] = None) -> dict:
        """Perfil da corretora, criando o padrao na primeira vez.

        Criar sob demanda evita um backfill que ficaria desatualizado no dia
        seguinte, quando uma corretora nova entrasse.
        """
        try:
            q = (self.db.table("briefing_profiles").select("*")
                 .eq("company_id", company_id).eq("cadence", cadencia)
                 .eq("is_active", True))
            q = q.is_("user_id", "null") if not user_id else q.eq("user_id", user_id)
            r = q.limit(1).execute()
            if r.data:
                return r.data[0]
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Briefing] leitura de perfil: %s", type(exc).__name__)

        padrao = {
            "company_id": company_id, "user_id": user_id,
            "scope": "personal" if user_id else "company",
            "name": "Briefing diário" if cadencia == "daily" else "Briefing executivo",
            "cadence": cadencia,
            "schedule_spec": {"time": "08:00"} if cadencia == "daily"
                             else {"time": "08:00", "weekday": 0},
            "channels": ["dashboard"],
        }
        try:
            r = self.db.table("briefing_profiles").insert(padrao).execute()
            return (r.data or [padrao])[0]
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Briefing] perfil padrão não criado: %s", type(exc).__name__)
            return padrao

    def atualizar_preferencias(self, company_id: str, *, cadencia: str,
                               user_id: Optional[str], campos: dict) -> Optional[dict]:
        permitidos = {"timezone", "channels", "quiet_hours", "severity_threshold",
                      "max_items", "max_pushes_per_day", "enabled_categories",
                      "disabled_categories", "detail_level", "is_active",
                      "schedule_spec", "include_completed_results",
                      "include_suggested_automations", "recipient_refs"}
        limpos = {k: v for k, v in (campos or {}).items() if k in permitidos}
        if not limpos:
            return None
        perfil = self.perfil(company_id, cadencia=cadencia, user_id=user_id)
        try:
            r = (self.db.table("briefing_profiles").update(limpos)
                 .eq("id", perfil["id"]).eq("company_id", company_id).execute())
            return (r.data or [{}])[0]
        except Exception as exc:  # noqa: BLE001
            logger.error("[Briefing] preferências não salvas: %s", type(exc).__name__)
            return None

    # ------------------------------------------------------------------
    # Publicacao
    # ------------------------------------------------------------------

    def gerar(self, company_id: str, *, briefing_type: str = "daily_operational",
              user_id: Optional[str] = None,
              agora: Optional[datetime] = None,
              work_run_id: Optional[str] = None) -> dict:
        """Reune, compoe e publica. Idempotente por perfil + tipo + periodo."""
        from .finding_engine import FindingEngine
        from .outcome_service import OutcomeService
        from .recommendation_service import RecommendationService

        agora = agora or _agora()
        cadencia = "weekly" if briefing_type == "weekly_executive" else "daily"
        perfil = self.perfil(company_id, cadencia=cadencia, user_id=user_id)
        inicio, fim = janela(briefing_type, agora, perfil.get("timezone"))

        findings = FindingEngine(self.db).ativos(company_id, user_id=user_id, limite=40)
        recomendacoes = RecommendationService(self.db).elegiveis(
            company_id, user_id=user_id, limite=20)
        em_curso = self._trabalhos(company_id, ativos=True)
        concluidos = self._trabalhos(company_id, ativos=False, desde=inicio)
        outcomes = OutcomeService(self.db).do_periodo(
            company_id, dias=7 if cadencia == "weekly" else 2)
        faltando = self._o_que_falta(company_id, inicio, findings)

        spec = compor(
            company_id=company_id, briefing_type=briefing_type,
            findings=findings, recomendacoes=recomendacoes,
            trabalhos_em_curso=em_curso, resultados=concluidos,
            outcomes=outcomes, faltando=faltando,
            period_start=inicio, period_end=fim,
            max_itens=int(perfil.get("max_items") or 7),
            user_id=user_id, profile_id=perfil.get("id"))

        return self.publicar(spec, perfil=perfil, work_run_id=work_run_id)

    def publicar(self, spec: BriefingSpec, *, perfil: dict,
                 work_run_id: Optional[str] = None) -> dict:
        """Grava a publicacao e seus itens. §28.3 — idempotente por periodo."""
        existente = self._publicacao_existente(spec)
        if existente:
            return {"ok": True, "reaproveitado": True, "publication": existente,
                    "spec": spec.como_payload()}

        acionaveis = [i for i in spec.itens
                      if i.item_type in ("finding", "recommendation")]
        linha = {
            "company_id": spec.company_id,
            "user_id": spec.user_id,
            "briefing_profile_id": spec.profile_id,
            "briefing_type": spec.briefing_type,
            "period_start": spec.period_start,
            "period_end": spec.period_end,
            "status": "published",
            "work_run_id": work_run_id,
            "headline": redigir(spec.headline, limite=200),
            "summary_text": redigir(spec.executive_summary, limite=1200),
            "payload": spec.como_payload(),
            "item_count": len(spec.itens),
            "critical_count": sum(1 for i in acionaveis if i.priority_score >= 85),
            "recommendation_count": sum(1 for i in spec.itens
                                        if i.item_type == "recommendation"
                                        or i.recommendation_id),
            "content_hash": spec.content_hash(),
            "delivery_status": "pending",
            "published_at": _agora().isoformat(),
            "expires_at": (_agora() + timedelta(days=30)).isoformat(),
        }
        try:
            r = self.db.table("briefing_publications").insert(linha).execute()
            publicacao = (r.data or [{}])[0]
        except Exception as exc:  # noqa: BLE001
            if "duplicate" in str(exc).lower() or "unique" in str(exc).lower():
                existente = self._publicacao_existente(spec)
                if existente:
                    return {"ok": True, "reaproveitado": True,
                            "publication": existente, "spec": spec.como_payload()}
            logger.error("[Briefing] publicação falhou: %s", type(exc).__name__)
            return {"ok": False, "erro": "não consegui publicar o briefing"}

        pub_id = publicacao.get("id")
        if pub_id and spec.itens:
            try:
                self.db.table("briefing_items").insert([
                    {"company_id": spec.company_id,
                     "briefing_publication_id": pub_id,
                     **so_as_colunas_da_tabela(item.como_dict(i))}
                    for i, item in enumerate(spec.itens)]).execute()
            except Exception as exc:  # noqa: BLE001
                logger.warning("[Briefing] itens não gravados: %s", type(exc).__name__)

        self._marcar_entregas(spec)
        registrar_evento(self.db, company_id=spec.company_id,
                         tipo="briefing.published", subject_type="briefing",
                         subject_id=pub_id, mensagem=spec.headline,
                         detalhe={"tipo": spec.briefing_type,
                                  "itens": len(spec.itens)})

        # SPEC-064 Bloco E — publicar não é entregar.
        #
        # Aqui a linha nascia com `delivery_status = 'pending'` e ficava assim
        # para sempre: 26 de 26 publicações estavam pendentes em 02/08/2026, e
        # `delivery_policy.decidir()` — a política que decide canal e horário —
        # tinha ZERO chamadores em produção. Não havia bug: havia um fio solto
        # entre duas peças prontas.
        #
        # A entrega é best-effort de propósito: se ela falhar, o briefing
        # continua publicado e visível em Entregas. O que NÃO pode acontecer é
        # o inverso — a publicação dar certo e ninguém nunca saber o que houve
        # com a entrega.
        entrega = self._entregar(publicacao, perfil)

        return {"ok": True, "reaproveitado": False, "publication": publicacao,
                "spec": spec.como_payload(), "entrega": entrega}

    def _entregar(self, publicacao: dict, perfil: dict) -> Optional[dict]:
        """Chama o executor de entrega. Falha aqui nunca desfaz a publicação."""
        try:
            from .delivery_executor import DeliveryExecutor

            return DeliveryExecutor(self.db).entregar(publicacao, perfil=perfil)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Briefing] entrega não executada: %s", type(exc).__name__)
            return {"ok": False, "erro": type(exc).__name__}

    def _publicacao_existente(self, spec: BriefingSpec) -> Optional[dict]:
        try:
            q = (self.db.table("briefing_publications").select("*")
                 .eq("company_id", spec.company_id)
                 .eq("briefing_type", spec.briefing_type)
                 .eq("period_start", spec.period_start)
                 .eq("period_end", spec.period_end))
            q = q.is_("user_id", "null") if not spec.user_id else q.eq("user_id", spec.user_id)
            r = q.limit(1).execute()
            return (r.data or [None])[0]
        except Exception:  # noqa: BLE001
            return None

    def _marcar_entregas(self, spec: BriefingSpec) -> None:
        from .recommendation_service import RecommendationService

        ids = [i.recommendation_id for i in spec.itens if i.recommendation_id]
        if ids:
            RecommendationService(self.db).marcar_entregue(spec.company_id, ids)
        finding_ids = [i.finding_id for i in spec.itens if i.finding_id]
        if finding_ids:
            try:
                # `last_delivered_at` e o que o cooldown consulta. Sem ele, o
                # mesmo Finding entraria no briefing de amanha como novidade.
                self.db.table("intelligence_findings").update({
                    "last_delivered_at": _agora().isoformat(),
                }).eq("company_id", spec.company_id).in_("id", finding_ids).execute()
            except Exception as exc:  # noqa: BLE001
                logger.warning("[Briefing] marcação de entrega: %s", type(exc).__name__)

    # ------------------------------------------------------------------

    def _trabalhos(self, company_id: str, *, ativos: bool,
                   desde: Optional[datetime] = None) -> list[dict]:
        try:
            q = (self.db.table("work_runs")
                 # 🔴 `source_type` entrou na SELEÇÃO para o filtro do D.5
                 # poder morar DENTRO de `compor` — que é a função pura, a que
                 # o guarda executa. Filtrar aqui deixaria a regra sem teste.
                 .select("id, outcome_title, status, progress_percent, "
                         "result_summary, finished_at, source_type")
                 .eq("company_id", company_id))
            if ativos:
                q = q.in_("status", ["running", "queued", "planning", "waiting_approval"])
            else:
                q = q.eq("status", "completed")
                if desde:
                    q = q.gte("finished_at", desde.isoformat())
            return (q.limit(20).execute()).data or []
        except Exception:  # noqa: BLE001
            return []

    def _o_que_falta(self, company_id: str, desde: datetime,
                     findings: list[dict]) -> list[str]:
        """§24.2 — declarar a ausencia em vez de afirmar estabilidade."""
        faltas: list[str] = []
        try:
            r = (self.db.table("conversation_scorecards").select("id", count="exact")
                 .eq("company_id", company_id)
                 .gte("created_at", desde.isoformat()).execute())
            n = int(getattr(r, "count", None) or len(r.data or []))
            if n < 5:
                faltas.append(
                    "Ainda não há conversas auditadas suficientes no período para "
                    "comparar a qualidade do atendimento.")
        except Exception:  # noqa: BLE001
            pass
        if not findings:
            faltas.append(
                "Nenhum sinal operacional foi registrado no período — isso pode "
                "significar tranquilidade ou fonte de dados parada.")
        return faltas

    # ------------------------------------------------------------------

    def atual(self, company_id: str, *, briefing_type: str = "daily_operational",
              user_id: Optional[str] = None) -> Optional[dict]:
        try:
            q = (self.db.table("briefing_publications").select("*")
                 .eq("company_id", company_id).eq("briefing_type", briefing_type)
                 .eq("status", "published"))
            q = q.is_("user_id", "null") if not user_id else q.eq("user_id", user_id)
            r = q.order("period_start", desc=True).limit(1).execute()
            return (r.data or [None])[0]
        except Exception as exc:  # noqa: BLE001
            logger.error("[Briefing] leitura falhou: %s", type(exc).__name__)
            return None

    def historico(self, company_id: str, *, limite: int = 30) -> list[dict]:
        try:
            r = (self.db.table("briefing_publications")
                 .select("id, briefing_type, period_start, period_end, headline, "
                         "summary_text, item_count, critical_count, "
                         "recommendation_count, delivery_status, published_at, artifact_id")
                 .eq("company_id", company_id).eq("status", "published")
                 .order("published_at", desc=True).limit(limite).execute())
            return r.data or []
        except Exception:  # noqa: BLE001
            return []


def janela(briefing_type: str, agora: datetime,
           timezone_nome: Optional[str] = None) -> tuple[datetime, datetime]:
    """Periodo coberto. Alinhado ao fuso da corretora, nao ao UTC.

    Alinhar em UTC faria o "dia" do corretor comecar as 21h do dia anterior —
    e o briefing das 8h traria metade do dia errado.
    """
    tz = _tz(timezone_nome or "America/Sao_Paulo")
    local = agora.astimezone(tz)
    if briefing_type == "weekly_executive":
        inicio_local = (local - timedelta(days=local.weekday() + 7)).replace(
            hour=0, minute=0, second=0, microsecond=0)
        fim_local = inicio_local + timedelta(days=7)
    else:
        inicio_local = datetime.combine(local.date(), time(0, 0), tzinfo=tz) - timedelta(days=1)
        fim_local = inicio_local + timedelta(days=1)
    return inicio_local.astimezone(timezone.utc), fim_local.astimezone(timezone.utc)
