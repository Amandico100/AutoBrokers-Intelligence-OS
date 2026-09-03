# -*- coding: utf-8 -*-
"""O pacote de evidência: o número chega ao modelo com ponteiro, nunca em prosa.

SPEC-094 · BLOCO 0-bis. Peça **pura** — só `dataclasses`, `datetime`,
`hashlib`, `json` e `uuid`. Não conhece InfoCap, não conhece Supabase, não
conhece LangChain. Quem calcula é `calculos.py`; quem publica é o
`ArtifactService`; aqui só se **embrulha** o que já foi calculado.

## Por que ele existe

📊 SPEC-094 §1.8: `relatorios_comerciais.py:378-385` devolvia ao modelo
`f"... {cob.apolices_total} apólices, {_reais(cob.comissao_total)} de comissão,
liderado por {topo.nome} ..."` — texto livre, sem `metric_id`, sem base
temporal, sem cobertura, **com nome de pessoa**. Três defeitos de uma vez:

```
o modelo recebe NÚMERO SOLTO      não tem como citar de onde veio, e parafraseia
o modelo recebe NOME DE PRODUTOR  dado de pessoa identificada no chat
ausente vira ZERO no meio da frase  "R$ 0,00 de comissão" e "não sei" viram a mesma coisa
```

O bloco `<<PACK … PACK>>` conserta os três: cada número vem com
`metric_id@version`, `unit`, `period`, `time_basis`, `coverage` e `confidence`,
e o produtor vem como **referência opaca** — o nome fica no Artifact do tenant,
que é onde ele pode estar.

## O que é `coverage`, exatamente

**A fração do universo devolvido pela fonte que ESTA métrica conseguiu usar.**

```
production.policy_count   conta todas as apólices que a fonte devolveu   → 1.0
producer.performance      só as que têm produtor identificado            → 0.806  💭 exemplo
renewal.exposure          conta tudo o que vence na janela               → 1.0
```

Não é "a fração da carteira real da corretora" — isso ninguém sabe, e afirmar
que sabe seria pior que não declarar. `None` significa **não medido**.

## A regra que não se negocia

`UNAVAILABLE` nunca é `0`. Um valor que a fonte não expõe é indisponível; zero
é uma afirmação sobre o negócio. `valor_ou_indisponivel(None)` devolve o
sentinela, e o modelo é instruído a dizer INDISPONÍVEL.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

# --------------------------------------------------------------------------
# O sentinela
# --------------------------------------------------------------------------
UNAVAILABLE = "UNAVAILABLE"

#: As unidades que o contrato aceita. Unidade é o que impede o modelo de ler
#: `0,806` como reais e `1.680` como porcentagem.
UNIDADES = ("BRL", "count", "pct")

#: A base temporal, obrigatória. 🔴 Uma apólice entra na produção pela data em
#: que a vigência COMEÇA e no radar pela data em que ela TERMINA — o mesmo
#: documento, em dois períodos diferentes. Número sem base temporal declarada é
#: número que não se consegue reproduzir.
BASES_TEMPORAIS = ("POLICY_VALID_FROM", "POLICY_VALID_TO")

ALTA, MEDIA, BAIXA = "HIGH", "MEDIUM", "LOW"

#: 🔴 O valor de uma métrica é UM número — exceto quando a resposta honesta
#: é uma repartição (novo × renovação), e aí forçar um escalar obrigaria o
#: modelo a escolher qual metade citar. `str` cobre o sentinela `UNAVAILABLE`.
Valor = Union[float, int, str, Dict[str, Any]]


# --------------------------------------------------------------------------
# Ajudantes
# --------------------------------------------------------------------------
def periodo_iso(inicio: Any, fim: Any) -> Dict[str, str]:
    """`{start, end}` em ISO. Aceita `date` ou string já formatada."""
    def _iso(v: Any) -> str:
        return v.isoformat() if isinstance(v, (date, datetime)) else str(v or "")
    return {"start": _iso(inicio), "end": _iso(fim)}


def ref_de_produtor(company_id: str, nome: str) -> str:
    """A referência OPACA de um produtor — `sha256(company_id + nome)[:16]`.

    🔴 É o que entra no pack no lugar do nome. Duas propriedades importam:

    ```
    estável   o mesmo produtor da mesma corretora dá sempre a mesma referência
    por TENANT o `company_id` no meio impede cruzar produtores entre corretoras
    ```

    O nome continua existindo no Artifact, que é conteúdo do tenant e não sai
    do prédio. O que não pode é o nome viajar no texto do chat, no log, no
    teste ou no relatório de execução (SPEC-094 §2).
    """
    semente = f"{company_id or ''}|{(nome or '').strip()}"
    return hashlib.sha256(semente.encode("utf-8")).hexdigest()[:16]


def confianca(cobertura: Optional[float]) -> str:
    """`HIGH` ≥ 0,8 · `MEDIUM` ≥ 0,5 · `LOW` abaixo · `MEDIUM` se não medida.

    Cobertura não medida não vira confiança alta: quem não sabe quanto cobre
    não pode afirmar que cobre tudo.
    """
    if cobertura is None:
        return MEDIA
    if cobertura >= 0.8:
        return ALTA
    if cobertura >= 0.5:
        return MEDIA
    return BAIXA


def valor_ou_indisponivel(v: Optional[Union[float, int]]) -> Valor:
    """`None` vira `UNAVAILABLE`. **Nunca** vira `0`."""
    return UNAVAILABLE if v is None else v


# --------------------------------------------------------------------------
# O envelope de UM número
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class MetricResult:
    """Um número, e tudo o que é preciso para conferir se ele diz a verdade."""

    metric_id: str
    version: int
    value: Valor
    unit: str
    period: Dict[str, str]
    time_basis: str
    coverage: Optional[float] = None
    confidence: str = MEDIA
    provider_key: str = "infocap"
    source_refs: Tuple[str, ...] = ()
    warnings: Tuple[str, ...] = ()
    #: 🔴 SPEC-094 BLOCO D. O DETALHE de uma métrica que não cabe num
    #: escalar — o ranking por produtor, as fatias de seguradora, as faixas de
    #: urgência. `value` continua sendo UM número (o que o modelo cita); isto é o
    #: que o Artifact desenha.
    #:
    #: ⛔ Nunca carrega nome de pessoa: produtor entra como `producer_ref`. O
    #: rótulo mora no Artifact do tenant, que é onde ele pode estar.
    breakdown: Tuple[Dict[str, Any], ...] = ()

    @property
    def indisponivel(self) -> bool:
        return self.value == UNAVAILABLE

    def serializar(self) -> Dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "version": self.version,
            "value": self.value,
            "unit": self.unit,
            "period": dict(self.period),
            "time_basis": self.time_basis,
            "coverage": self.coverage,
            "confidence": self.confidence,
            "provider_key": self.provider_key,
            "source_refs": list(self.source_refs),
            "warnings": list(self.warnings),
            "breakdown": [dict(b) for b in self.breakdown],
        }


def metrica(metric_id: str, valor: Optional[Union[float, int]], unit: str, *,
            period: Dict[str, str], time_basis: str,
            coverage: Optional[float] = None, version: int = 1,
            provider_key: str = "infocap",
            source_refs: Sequence[str] = (),
            warnings: Sequence[str] = (),
            breakdown: Sequence[Dict[str, Any]] = ()) -> MetricResult:
    """Monta um `MetricResult` já com a confiança derivada da cobertura.

    Levanta `ValueError` em unidade ou base temporal fora do contrato — um
    número com unidade inventada é pior que número nenhum, porque o modelo
    narra a unidade errada com a mesma segurança.
    """
    if unit not in UNIDADES:
        raise ValueError(f"unidade fora do contrato: {unit!r} (use {UNIDADES})")
    if time_basis not in BASES_TEMPORAIS:
        raise ValueError(
            f"base temporal fora do contrato: {time_basis!r} (use {BASES_TEMPORAIS})")
    return MetricResult(
        metric_id=metric_id, version=version,
        value=valor_ou_indisponivel(valor), unit=unit,
        period=dict(period), time_basis=time_basis,
        coverage=coverage, confidence=confianca(coverage),
        provider_key=provider_key,
        source_refs=tuple(source_refs), warnings=tuple(warnings),
        breakdown=tuple(dict(b) for b in breakdown),
    )


# --------------------------------------------------------------------------
# O pacote
# --------------------------------------------------------------------------
ABERTURA = "<<PACK"
FECHAMENTO = "PACK>>"


@dataclass
class EvidencePack:
    """O mesmo objeto que o chat lê e que o Artifact publica.

    🔴 `pack_id` é o ELO: o bloco que vai ao modelo e o `payload.evidence_pack`
    do Artifact carregam **o mesmo** identificador e as **mesmas** métricas,
    porque são o mesmo objeto serializado duas vezes — não duas consultas.
    """

    company_id: str
    period: Dict[str, str]
    compare_period: Optional[Dict[str, str]] = None
    metrics: List[MetricResult] = field(default_factory=list)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    coverage: Dict[str, Any] = field(default_factory=dict)
    freshness: str = ""
    provenance: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    pack_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def __post_init__(self) -> None:
        if not self.freshness:
            self.freshness = datetime.now().isoformat(timespec="seconds")

    # ---------------------------------------------------------------- #
    def serializar(self) -> Dict[str, Any]:
        """A forma JSON-able. Sem nome de pessoa: produtor é `producer_ref`."""
        return {
            "pack_id": self.pack_id,
            "company_id": self.company_id,
            "period": dict(self.period),
            "compare_period": dict(self.compare_period) if self.compare_period else None,
            "metrics": [m.serializar() for m in self.metrics],
            "findings": [dict(f) for f in self.findings],
            "coverage": dict(self.coverage),
            "freshness": self.freshness,
            "provenance": dict(self.provenance),
            "warnings": list(self.warnings),
        }

    def bloco_para_o_modelo(self) -> str:
        """O bloco citável. 🔴 É a ÚNICA parte da resposta que carrega número.

        Delimitado, e não solto no meio da frase, porque é isso que permite ao
        guarda perguntar *"há `R$ 1.234` FORA do bloco?"* — a pergunta que
        pega a prosa voltando.
        """
        corpo = json.dumps(self.serializar(), ensure_ascii=False)
        return f"{ABERTURA}\n{corpo}\n{FECHAMENTO}"


# ==========================================================================
# 🔴 SPEC-094 · BLOCO E — os FINDINGS determinísticos, e o que vira SINAL
# ==========================================================================
#
# Um número sozinho não é um achado. `mix.insurer = 62,3%` é um número; *"a
# comissão do período está concentrada acima do limiar numa única seguradora"*
# é um achado — tem limiar declarado, tem as métricas que o sustentam e tem
# uma frase que um humano lê. O pack carrega os dois, e o Artifact desenha os
# dois.
#
# 🔴 E o achado é DETERMINÍSTICO: sai de comparação com limiar escrito, nunca
# de um modelo. O mesmo pack produz os mesmos findings, sempre. Um "insight"
# gerado por LLM sobre os mesmos números mudaria de rodada para rodada, e o
# dono da corretora leria duas verdades diferentes sobre a mesma semana.
#
# ⚠️ Os limiares abaixo são 💭 ILUSTRATIVOS — escolhidos, não medidos. Eles
# viajam DENTRO do finding (campo `limiar_pct`), para que quem lê consiga
# discordar do corte sem abrir o código. Quando houver medição de qual corte
# separa "normal" de "digno de ação", ela substitui estes valores e o número
# vira 📊.

QUEDA_DE_PRODUTOR = "producer_drop"
CONCENTRACAO = "concentration"
EXPOSICAO_DE_RENOVACAO = "renewal_exposure"
COBERTURA_BAIXA = "low_coverage"

#: 💭 acima disto, uma seguradora só responde por fatia grande demais da
#: comissão do período para o dono não saber.
LIMIAR_CONCENTRACAO_PCT = 40.0
#: 💭 queda de comissão de um produtor contra o mesmo período anterior.
LIMIAR_QUEDA_PCT = -20.0
#: 💭 abaixo disto a comissão do produtor é pequena demais para a variação
#: percentual dizer alguma coisa: 100% de queda sobre R$ 50 é ruído.
PISO_DE_COMISSAO_PARA_QUEDA = 500.0
#: 💭 abaixo disto o relatório soma parte da carteira e precisa dizer isso.
LIMIAR_DE_COBERTURA = 0.8
#: Quantos produtores em queda entram no pack. 💭 Três cabem numa frase.
TETO_DE_QUEDAS = 3

#: 🔴 Os três que cabem num `signal_type` EXISTENTE com semântica honesta.
#: `commercial_opportunity` (domínio `comercial`) é o único dos 26 tipos do
#: Intelligence Fabric que descreve o que estes achados são: trabalho
#: comercial que alguém pode fazer esta semana.
#:
#: ⛔ E `COBERTURA_BAIXA` **não** está aqui. Ele é um fato sobre a FONTE, não
#: sobre o negócio, e o tipo que o descreveria tem gate próprio no Fabric
#: (SPEC-059 §12.4). Emitir um sinal daquele tipo por conta desta SPEC seria
#: atravessar um portão que outra SPEC construiu. Fica no pack e no Artifact,
#: que é onde ele serve: ao lado do número que ele qualifica.
FINDINGS_QUE_VIRAM_SINAL = (EXPOSICAO_DE_RENOVACAO, CONCENTRACAO,
                            QUEDA_DE_PRODUTOR)

#: O tipo de sinal, o `source_type` e o teto de severidade — os três fixos.
TIPO_DE_SINAL = "commercial_opportunity"
SOURCE_TYPE = "executive_360"
#: 🔴 `medium`, e nunca `critical`. Alerta crítico exige Tier 0/1/2 no Fabric,
#: e o que sustenta estes achados é agregado de leitura de API — não é
#: evidência de primeira mão sobre um caso. Severidade que o dado não sustenta
#: é a forma mais rápida de ensinar alguém a ignorar alerta.
SEVERIDADE_MAXIMA = "medium"


def ref_da_metrica(m: MetricResult) -> str:
    """`metric_id@versão` — a citação de UM número (SPEC-094 ref ⑥)."""
    return f"{m.metric_id}@{m.version}"


def _numero(m: Optional[MetricResult]) -> Optional[float]:
    """O valor da métrica como número, ou `None`. `UNAVAILABLE` é `None`."""
    if m is None or m.indisponivel:
        return None
    if isinstance(m.value, bool) or not isinstance(m.value, (int, float)):
        return None
    return float(m.value)


def finding(kind: str, *, summary: str, metric_refs: Sequence[str] = (),
            subject_type: str = "portfolio", subject_id: str = "",
            severity: str = "low", **detalhe: Any) -> Dict[str, Any]:
    """Um achado, na forma que o pack, o Artifact e o sinal leem.

    ⛔ `summary` e `subject_id` nunca carregam nome de pessoa. Produtor entra
    como `producer_ref` — a referência opaca, estável e por tenant.
    """
    achado: Dict[str, Any] = {
        "kind": kind,
        "summary": summary,
        "metric_refs": list(metric_refs),
        "subject_type": subject_type,
        "subject_id": subject_id,
        "severity": severity,
        "vira_sinal": kind in FINDINGS_QUE_VIRAM_SINAL,
    }
    achado.update(detalhe)
    return achado


def achar_findings(metrics: Sequence[MetricResult],
                   anteriores: Sequence[MetricResult] = ()
                   ) -> List[Dict[str, Any]]:
    """Os achados determinísticos deste pack. Ordem estável, sem LLM.

    ```
    concentração            mix.insurer acima do limiar
    exposição de renovação  renewal.exposure > 0 na janela
    queda de produtor       producer.performance do período × do anterior
    cobertura baixa         qualquer métrica que cubra menos que o limiar
    ```

    🔴 A queda de produtor compara **referência opaca com referência opaca**,
    entre os dois períodos, e só quando os DOIS lados existem. Um produtor que
    não aparece no período anterior não "caiu": ele não estava lá, e chamar
    isso de queda inventaria um problema que ninguém tem.
    """
    por_id = {m.metric_id: m for m in metrics}
    antes = {m.metric_id: m for m in anteriores}
    achados: List[Dict[str, Any]] = []

    # --- concentração -----------------------------------------------------
    mix = por_id.get("mix.insurer")
    pct = _numero(mix)
    if mix is not None and pct is not None and pct >= LIMIAR_CONCENTRACAO_PCT:
        topo = dict(mix.breakdown[0]) if mix.breakdown else {}
        achados.append(finding(
            CONCENTRACAO, subject_type="insurer",
            subject_id=str(topo.get("rotulo") or ""),
            summary=("a maior seguradora responde por uma fatia da comissão do "
                     "período acima do limiar declarado"),
            metric_refs=[ref_da_metrica(mix)], severity=SEVERIDADE_MAXIMA,
            valor_pct=round(pct, 1), limiar_pct=LIMIAR_CONCENTRACAO_PCT,
            unidade="pct"))

    # --- exposição de renovação -------------------------------------------
    exp = por_id.get("renewal.exposure")
    quantas = _numero(exp)
    if exp is not None and quantas is not None and quantas > 0:
        vencidas = next((dict(f) for f in exp.breakdown
                         if "vencid" in str(f.get("faixa", "")).lower()), {})
        achados.append(finding(
            EXPOSICAO_DE_RENOVACAO, subject_type="portfolio",
            subject_id="renewal_window",
            summary=("há carteira vencendo na janela; o detalhe por faixa de "
                     "urgência está no envelope da métrica"),
            metric_refs=[ref_da_metrica(exp)], severity=SEVERIDADE_MAXIMA,
            apolices=int(quantas),
            ja_vencidas=int(vencidas.get("apolices") or 0), unidade="count"))

    # --- queda de produtor ------------------------------------------------
    agora_p = por_id.get("producer.performance")
    antes_p = antes.get("producer.performance")
    if agora_p is not None and antes_p is not None:
        de_antes = {str(l.get("producer_ref") or ""): l for l in antes_p.breakdown}
        quedas = []
        for linha in agora_p.breakdown:
            referencia = str(linha.get("producer_ref") or "")
            anterior = de_antes.get(referencia)
            if not referencia or anterior is None:
                continue
            base = float(anterior.get("comissao") or 0.0)
            if base < PISO_DE_COMISSAO_PARA_QUEDA:
                continue
            atual = float(linha.get("comissao") or 0.0)
            delta = 100.0 * (atual - base) / base
            if delta <= LIMIAR_QUEDA_PCT:
                quedas.append((delta, referencia))
        for delta, referencia in sorted(quedas)[:TETO_DE_QUEDAS]:
            achados.append(finding(
                QUEDA_DE_PRODUTOR, subject_type="producer",
                subject_id=referencia,
                summary=("um produtor apropriou menos comissão que no período "
                         "anterior, abaixo do limiar declarado"),
                metric_refs=[ref_da_metrica(agora_p), ref_da_metrica(antes_p)],
                severity=SEVERIDADE_MAXIMA, producer_ref=referencia,
                delta_pct=round(delta, 1), limiar_pct=LIMIAR_QUEDA_PCT,
                unidade="pct"))

    # --- cobertura baixa: fica no pack, e NÃO vira sinal ------------------
    baixas = [m for m in metrics
              if m.coverage is not None and m.coverage < LIMIAR_DE_COBERTURA]
    if baixas:
        achados.append(finding(
            COBERTURA_BAIXA, subject_type="portfolio", subject_id="coverage",
            summary=("uma ou mais métricas do período cobrem menos que o "
                     "limiar: o relatório soma parte da carteira e diz isso"),
            metric_refs=[ref_da_metrica(m) for m in baixas], severity="low",
            limiar=LIMIAR_DE_COBERTURA,
            metricas=[{"metric_id": m.metric_id, "coverage": m.coverage}
                      for m in baixas]))
    return achados


# --------------------------------------------------------------------------
# Do finding ao SINAL — pelas leis do Fabric, sem tocar nelas
# --------------------------------------------------------------------------
def evidencia_da_metrica(m: MetricResult) -> Dict[str, Any]:
    """O envelope da métrica virando evidência. ⛔ Sem nome, sem documento.

    🔴 `value_snapshot` leva o número, a unidade, o período, a base temporal e
    a cobertura — exatamente o que permite conferir a afirmação depois. O que
    ele **não** leva é o `breakdown`: ranking e fatias são detalhe do Artifact,
    e evidência não é cópia do dado bruto (SPEC-059 §10.2).
    """
    return {
        "evidence_type": "metric",
        "source_system": SOURCE_TYPE,
        "source_ref": ref_da_metrica(m),
        "summary_redacted": (
            f"{m.metric_id} = {m.value} {m.unit} "
            f"(base {m.time_basis}, confianca {m.confidence})"),
        "value_snapshot": {
            "value": m.value, "unit": m.unit, "period": dict(m.period),
            "time_basis": m.time_basis, "coverage": m.coverage,
            "confidence": m.confidence, "provider_key": m.provider_key,
        },
    }


def sinais_do_pack(pack: "EvidencePack") -> List[Dict[str, Any]]:
    """Os rascunhos de sinal deste pack, prontos para o `SignalService`.

    Devolve **dicionários**, e não `SignalDraft`, de propósito: este módulo é
    puro e não importa `app.services.intelligence` (CLAUDE.md §5 — a fronteira
    é de mão dupla). Quem grava monta o `SignalDraft` com estes campos e chama
    `registrar()`, que é onde `valido()` roda de verdade.

    🔴 Todo rascunho sai COM evidência. Um sinal sem evidência é recusado pelo
    Fabric (lei central 1 da SPEC-059) — e ser recusado em silêncio, na hora
    de gravar, seria pior que não emitir: ninguém veria o achado e ninguém
    veria a recusa.
    """
    por_ref = {ref_da_metrica(m): m for m in pack.metrics}
    inicio = str(pack.period.get("start") or "")
    fim = str(pack.period.get("end") or "")
    rascunhos: List[Dict[str, Any]] = []

    for achado in pack.findings:
        kind = str(achado.get("kind") or "")
        if kind not in FINDINGS_QUE_VIRAM_SINAL:
            continue
        refs = [r for r in achado.get("metric_refs", []) if r in por_ref]
        evidencias = [evidencia_da_metrica(por_ref[r]) for r in refs]
        if not evidencias:
            # Achado sem métrica no pack não vira sinal. Preferimos o achado
            # visível no Artifact a um sinal que o Fabric recusaria na porta.
            continue
        coberturas = [por_ref[r].coverage for r in refs
                      if por_ref[r].coverage is not None]
        confianca_do_sinal = round(min(coberturas), 2) if coberturas else 0.7
        alvo = str(achado.get("subject_id") or "")
        rascunhos.append({
            "company_id": pack.company_id,
            "signal_type": TIPO_DE_SINAL,
            "subject_type": str(achado.get("subject_type") or "portfolio"),
            "subject_id": alvo or None,
            "summary_redacted": str(achado.get("summary") or ""),
            # 🔴 O dedupe carrega o PERÍODO. Sem ele, a exposição de renovação
            # de dois trimestres diferentes reforçaria um sinal só, e o dono
            # veria um alerta velho com data nova.
            "dedupe_key": f"094:{kind}:{inicio}:{fim}:{alvo}",
            "source_type": SOURCE_TYPE,
            "source_ref": pack.pack_id,
            "severity": SEVERIDADE_MAXIMA,
            "confidence": max(0.0, min(1.0, confianca_do_sinal)),
            "window_start": inicio or None,
            "window_end": fim or None,
            "metadata": {"metric_refs": refs, "pack_id": pack.pack_id,
                         "finding_kind": kind, "spec": "094"},
            "evidencias": evidencias,
        })
    return rascunhos
