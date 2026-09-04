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
import math
import re
import unicodedata
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
UNIDADES = ("BRL", "count", "pct", "ratio")

#: 🔴 SPEC-094.1 · BLOCO B: `ratio` entrou porque `pct` teria MENTIDO.
#:
#: 📊 Nesta casa `pct` é escala 0–100 — `mix.insurer` devolve `43.0` e o
#: formatador escreve "43,0%" (`executive_intelligence.py:1270`). A
#: sinistralidade do SES é uma FRAÇÃO: `sinistro_ocorrido ÷ premio_ganho`, e a
#: célula medida do trimestre da Porto dá `0,5712`. Declará-la como `pct`
#: faria a tela escrever **"0,6%"** onde o mercado tem **57%** — um número
#: certo lido como outro, que é a forma silenciosa de errar (CLAUDE.md §9.5).
#:
#: ⚠️ Multiplicar por 100 na fórmula resolveria a tela e estragaria a conta: o
#: golden do BLOCO B é `0,5712` porque é assim que a razão é conferida à mão
#: contra o CSV. O nome da unidade é que estava faltando.

#: A base temporal, obrigatória. 🔴 Uma apólice entra na produção pela data em
#: que a vigência COMEÇA e no radar pela data em que ela TERMINA — o mesmo
#: documento, em dois períodos diferentes. Número sem base temporal declarada é
#: número que não se consegue reproduzir.
BASES_TEMPORAIS = ("POLICY_VALID_FROM", "POLICY_VALID_TO")

ALTA, MEDIA, BAIXA = "HIGH", "MEDIUM", "LOW"
# 📊 03/09: o guarda `test_todo_import_aponta_para_algo_que_existe` não enxerga desempacotamento de tupla —
# as três constantes ficam também como atribuições simples, para o import ser visível ao guarda e ao leitor.
ALTA = 'HIGH'
MEDIA = 'MEDIUM'
BAIXA = 'LOW'

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


#: 🔴 A LETRA-ÂNCORA da referência de produtor. Ela aparece DUAS vezes, nas
#: posições 0 e 8, e isso não é enfeite nem estilo.
#:
#: 📊 Achado pela lente do dado, 03/09/2026: `sha256(...)[:16]` é hexadecimal, e
#: uma corrida de 11 dígitos ali dentro casa `\d{11}`. TODO detector de PII deste
#: repositório (o canário, o guarda do Artifact) acusa então "documento de 11
#: dígitos" na peça inteira — por causa de um hash.
#:
#: ⚠️ E um prefixo SÓ não resolve: ele impede a referência INTEIRA de ser
#: numérica, e a corrida pode acontecer nos 15 caracteres seguintes. 📊 Medido:
#: em 400 referências sintéticas, o prefixo sozinho ainda deixava passar.
#:
#: 🔴 Com a âncora nas posições 0 e 8, o maior bloco contíguo de dígitos possível
#: é de **7** caracteres. Não é "improvável": é impossível por construção, que é
#: a única forma de um guarda deste tipo não depender de sorte.
PREFIXO_DO_PRODUTOR = "p"


def normalizar_rotulo(s: str) -> str:
    """Minúsculas, sem acento, espaço colapsado. Para COMPARAR, nunca para exibir.

    🔴 Uma única implementação, e ela mora aqui, no módulo puro do fundo da
    pilha: `calculos._normalizar` delega para esta função (CLAUDE.md §5). Duas
    normalizações divergiriam no primeiro `.strip()` que uma ganhasse e a outra
    não — e o ranking do chat deixaria de casar com o do Artifact sem ninguém
    ver.
    """
    t = unicodedata.normalize("NFKD", str(s or ""))
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).strip().lower()


def ref_de_produtor(company_id: str, nome: str) -> str:
    """A referência OPACA de um produtor — `p` + 7 hex + `p` + 7 hex.

    🔴 É o que entra no pack no lugar do nome. Três propriedades importam:

    ```
    estável    o mesmo produtor da mesma corretora dá sempre a mesma referência
    por TENANT o `company_id` no meio impede cruzar produtores entre corretoras
    NORMALIZADA `Ana Souza`, `ANA  SOUZA` e `ana souza` são o MESMO produtor
    ANCORADA   uma letra nas posições 0 e 8 — nenhum bloco de dígitos passa de 7
    ```

    🔴 A normalização não é capricho. 📊 `por_dimensao` já normaliza o rótulo da
    seguradora desde a 081, porque a base traz `Allianz`, `allianz` e `ALLIANZ`
    contando separado — 56 valores crus que viram ~30. O rótulo do produtor vem
    da MESMA base, digitado à mão, e sem normalizar o mesmo vendedor aparece
    duas vezes no ranking, cada metade da comissão dele numa linha.

    O nome continua existindo no Artifact, que é conteúdo do tenant e não sai
    do prédio. O que não pode é o nome viajar no texto do chat, no log, no
    teste ou no relatório de execução (SPEC-094 §2).
    """
    semente = f"{company_id or ''}|{normalizar_rotulo(nome)}"
    bruto = hashlib.sha256(semente.encode("utf-8")).hexdigest()
    return (PREFIXO_DO_PRODUTOR + bruto[:7]
            + PREFIXO_DO_PRODUTOR + bruto[7:14])


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


#: A ordem das confianças, da pior para a melhor. 🔴 Serve a UMA regra:
#: `rebaixar_confianca` nunca SOBE. Um teto pedido por quem calculou não pode
#: ser desfeito pela cobertura — que só sabe quantas linhas entraram na conta.
ORDEM_DA_CONFIANCA = (BAIXA, MEDIA, ALTA)


def rebaixar_confianca(atual: str, teto: Optional[str]) -> str:
    """A PIOR das duas. `None` deixa como está."""
    if not teto or teto not in ORDEM_DA_CONFIANCA:
        return atual
    if atual not in ORDEM_DA_CONFIANCA:
        return teto
    return min((atual, teto), key=ORDEM_DA_CONFIANCA.index)


def valor_ou_indisponivel(v: Optional[Union[float, int]]) -> Valor:
    """`None` vira `UNAVAILABLE`. **Nunca** vira `0`."""
    return UNAVAILABLE if v is None else v


# --------------------------------------------------------------------------
# O envelope de UM número
# --------------------------------------------------------------------------
#: 🔴 As casas decimais com que um número CHEGA AO MODELO.
#:
#: 📊 Achado pelo canário do BLOCO G, 03/09/2026: o bloco que o modelo lê
#: carregava `56580.57999999994` e `3.0357144169723714416972369` — resíduo
#: binário de `float`, e não precisão. Três estragos de uma vez:
#:
#: ```
#: o modelo narra "R$ 56.580,57999999994"          e parece defeito de sistema
#: o número perde a cara de dinheiro                 e ninguém confere de olho
#: nasce um "documento de 11 dígitos" que NÃO existe e todo detector de PII
#:                                                    acusa a peça inteira
#: ```
#:
#: O arredondamento acontece **na serialização**, e não no cálculo: a
#: comparação com os controles-ouro continua sendo feita sobre o valor cheio.
#: É apresentação, e a `Decimal` do CBIM continua sendo quem soma.
CASAS_DO_NUMERO = 2
#: Cobertura é fração de 0 a 1: duas casas transformariam 0,806 em 0,81 e
#: 5,95% em 6%. Quatro casas mantêm o décimo de ponto percentual.
CASAS_DA_COBERTURA = 4


def _arredondar(valor: Any, casas: int = CASAS_DO_NUMERO) -> Any:
    """Corta o resíduo binário de `float`. **Não-finito vira `UNAVAILABLE`.**

    🔴 `NaN` e `Infinity` NÃO são números, e o pior deles é o `NaN`: ele
    atravessa toda soma sem levantar, contamina o total e chega ao dono como
    manchete. 📊 Achado pelo red team, 03/09/2026: a fonte devolvendo a string
    `"NaN"` produzia a manchete **"R$ nan"** e 46 ocorrências de `NaN` dentro do
    bloco que o modelo lê — e `json.dumps` do Python escreve `NaN` no JSON de
    boa vontade, que nem sequer é JSON válido.

    A recusa acontece em DOIS lugares de propósito: `cbim.interpretar_dinheiro`
    não deixa o valor virar `Money` na fronteira, e esta função não deixa um
    não-finito nascido de uma DIVISÃO (0/0, x/0) chegar ao pack.
    """
    if isinstance(valor, bool) or not isinstance(valor, float):
        return valor
    if not math.isfinite(valor):
        return UNAVAILABLE
    return round(valor, casas)


def _limpar(valor: Any) -> Any:
    """`_arredondar`, recursivo em dicionário e lista."""
    if isinstance(valor, dict):
        return {k: _limpar(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_limpar(v) for v in valor]
    return _arredondar(valor)


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
            "value": _limpar(self.value),
            "unit": self.unit,
            "period": dict(self.period),
            "time_basis": self.time_basis,
            "coverage": _arredondar(self.coverage, CASAS_DA_COBERTURA),
            "confidence": self.confidence,
            "provider_key": self.provider_key,
            "source_refs": list(self.source_refs),
            "warnings": list(self.warnings),
            "breakdown": [_limpar(dict(b)) for b in self.breakdown],
        }


def metrica(metric_id: str, valor: Optional[Union[float, int]], unit: str, *,
            period: Dict[str, str], time_basis: str,
            coverage: Optional[float] = None, version: int = 1,
            provider_key: str = "infocap",
            source_refs: Sequence[str] = (),
            warnings: Sequence[str] = (),
            breakdown: Sequence[Dict[str, Any]] = (),
            confianca_maxima: Optional[str] = None) -> MetricResult:
    """Monta um `MetricResult` já com a confiança derivada da cobertura.

    Levanta `ValueError` em unidade ou base temporal fora do contrato — um
    número com unidade inventada é pior que número nenhum, porque o modelo
    narra a unidade errada com a mesma segurança.

    🔴 `confianca_maxima` é um TETO, e existe porque cobertura não é a única
    coisa que estraga um número. 📊 Achado pela lente do dado, 03/09/2026: uma
    contribuição pós-repasse NEGATIVA (repasse maior que a comissão — estorno,
    provavelmente) tem cobertura de 100% e sairia `HIGH`. A cobertura mede
    quantas linhas entraram na conta; ela não sabe que a conta deu um resultado
    que o negócio não explica.
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
        coverage=coverage,
        confidence=rebaixar_confianca(confianca(coverage), confianca_maxima),
        provider_key=provider_key,
        source_refs=tuple(source_refs), warnings=tuple(warnings),
        breakdown=tuple(dict(b) for b in breakdown),
    )


# --------------------------------------------------------------------------
# O pacote
# --------------------------------------------------------------------------
ABERTURA = "<<PACK"
FECHAMENTO = "PACK>>"

#: 🔴 O que faz de dois avisos o MESMO aviso: a referência da linha sai, o
#: resto fica. Sem isto, 222 avisos idênticos ocupam o bloco citável um a um.
#:
#: ⚠️ As DUAS formas do acervo, medidas em 03/09/2026 na peça viva — a com
#: parênteses (`valor ilegível em X (apólice abcd1234…)`) e a SEM
#: (`repasse ilegível na apólice abcd1234…`). A primeira rodada deste conserto
#: só cobria a com parênteses, e a peça viva continuou com 222 linhas: a
#: mensagem que o produto escreve DE VERDADE era a outra. 🔴 O padrão vem do
#: acervo, e não da citação de um relatório (CLAUDE.md §9.4).
_REFERENCIA_NO_AVISO = re.compile(
    r"\(?\b(ap[óo]lice|documento|ref|linha)\b\s+[^\s):]+\)?",
    re.IGNORECASE)


def colapsar_avisos(avisos: Sequence[str]) -> List[str]:
    """Avisos iguais viram UM, com a contagem. A ordem de aparição é mantida.

    🔴 📊 Achado pelo juiz em 03/09/2026, no bloco citável da peça viva: **222**
    linhas de *"valor ilegível em repasse (apólice XXXXXXXX…): INDISPONÍVEL, não
    zero"*, uma por apólice. Cada uma é verdadeira e nenhuma delas informa mais
    que a primeira — e juntas empurram para fora do contexto do modelo o pedaço
    do bloco que responde à pergunta do dono.

    ⚠️ O que se colapsa é a REFERÊNCIA da linha, e só ela: o campo, o motivo e
    o `correlation_id` continuam escritos. Um aviso que fale de outro campo
    **não** se junta a este, e a contagem vai na frase, porque *"em 222
    apólices"* é um fato sobre o tamanho do problema — ele muda a decisão de
    quem lê, e some se a gente só disser "houve valor ilegível".
    """
    ordem: List[str] = []
    grupos: Dict[str, Dict[str, Any]] = {}
    for aviso in avisos:
        texto = str(aviso or "")
        if not texto.strip():
            continue
        assinatura = _REFERENCIA_NO_AVISO.sub(lambda m: "%s …" % m.group(1),
                                              texto)
        if assinatura not in grupos:
            grupos[assinatura] = {"texto": texto, "n": 0}
            ordem.append(assinatura)
        grupos[assinatura]["n"] += 1
    saida: List[str] = []
    for assinatura in ordem:
        g = grupos[assinatura]
        if g["n"] == 1:
            saida.append(g["texto"])
        else:
            saida.append("%s — em %d ocorrências (avisos idênticos "
                         "colapsados)" % (assinatura, g["n"]))
    return saida


#: 🔴 As chaves de UMA comparação, na ordem em que quem lê precisa delas.
CAMPOS_DA_COMPARACAO = ("metric_id", "unit", "atual", "anterior", "delta",
                        "delta_pct", "time_basis", "confidence")


def _comparacao_citavel(c: Dict[str, Any]) -> Dict[str, Any]:
    """UMA comparação, pronta para o bloco que o modelo cita.

    🔴 📊 Achado pelo juiz em 03/09/2026, na narrativa viva: o dono perguntou
    *"como estamos?"*, o pack trazia `compare_period` e o aviso *"comparacoes
    calculadas: 11"* — e a resposta saiu com **35 números e ZERO menção a
    crescimento ou queda**. Não foi o modelo que se esqueceu: as comparações
    eram calculadas, viajavam no `payload` do Artifact e **não entravam no
    `serializar()`** do pack. E `COMO_FALAR` proíbe citar o que não está no
    bloco — corretamente. O modelo obedeceu a uma regra sobre um bloco a que
    faltava a metade que responde à pergunta.

    ⚠️ O motivo da recusa vem JUNTO, num campo só (`motivo`), e não como lista
    solta: uma comparação recusada por janela desigual precisa dizer POR QUE o
    `delta_pct` é `UNAVAILABLE`, senão o modelo lê a ausência como zero — que é
    a mutação M2 entrando pela porta da comparação.
    """
    saida: Dict[str, Any] = {}
    for chave in CAMPOS_DA_COMPARACAO:
        if chave in c:
            saida[chave] = _limpar(c[chave])
    saida.setdefault("metric_id", str(c.get("metric_id") or ""))
    for chave in ("atual", "anterior", "delta", "delta_pct"):
        if saida.get(chave) is None:
            saida[chave] = UNAVAILABLE
    avisos = [str(a) for a in (c.get("warnings") or []) if str(a).strip()]
    saida["motivo"] = "; ".join(colapsar_avisos(avisos))
    return saida


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
    #: 🔴 As comparações com o período anterior, DENTRO do bloco citável.
    comparacoes: List[Dict[str, Any]] = field(default_factory=list)
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
            "comparacoes": [_comparacao_citavel(c) for c in self.comparacoes],
            "findings": [_limpar(dict(f)) for f in self.findings],
            "coverage": _limpar(dict(self.coverage)),
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
        # 🔴 `allow_nan=False`. 📊 O default do Python escreve `NaN` e
        # `Infinity` no JSON — que **não são JSON válido** (RFC 8259) e que
        # nenhum parser de outra linguagem lê. Um bloco citável que não é
        # parseável é um bloco que o próximo leitor terá de adivinhar.
        # `_limpar` já trocou o não-finito por `UNAVAILABLE` antes daqui; esta
        # linha é o cinto que LEVANTA se algum caminho novo escapar, em vez de
        # publicar o `NaN` com cara de dinheiro.
        corpo = json.dumps(self.serializar(), ensure_ascii=False, allow_nan=False)
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
