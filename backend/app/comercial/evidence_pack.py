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

Valor = Union[float, int, str]


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
