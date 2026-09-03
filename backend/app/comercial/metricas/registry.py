# -*- coding: utf-8 -*-
"""O Metric Registry — a fórmula não conhece a fonte, e carrega a base temporal.

SPEC-094 · BLOCO D. Modelado nos [semantic models do dbt][dbt]: cada métrica é
uma **declaração**, não um trecho de código espalhado, e a declaração é
obrigada a dizer a sua base temporal — o análogo do `agg_time_dimension`.

[dbt]: https://docs.getdbt.com/docs/build/semantic-models

## Por que `time_basis` é obrigatório, e não um detalhe de configuração

📊 O censo do BLOCO 0 mediu, na fonte piloto, **duas** bases temporais e só
duas: a rota de produção filtra pelo **início** de vigência (1.680/1.680
registros de 2025 dentro da janela; só 106 terminam dentro dela) e a rota de
vencimentos filtra pelo **fim** (3.536/3.536). São duas populações quase
disjuntas — 📊 interseção de **2,8%** — porque apólice anual que começa num ano
termina no seguinte.

🔴 A MESMA apólice está em dois períodos diferentes, dependendo da pergunta. Um
número sem base temporal declarada é um número que ninguém consegue reproduzir,
e comparar dois deles é a mutação **M6** — que `comparar()` recusa com
`ValueError`, e não com um aviso.

## O que o registry NÃO faz

```
⛔ não escolhe QUAIS métricas o usuário quer   isso é do modelo (o query plan)
⛔ não busca dado                              isso é do provider
⛔ não formata                                 isso é do Artifact
⛔ não sabe o nome de nenhum sistema de gestão
```

## E a regra que fecha a porta do zero de consolação

Toda soma de dinheiro devolve **o total E o denominador**. Uma métrica que
some 80% da carteira e se apresente como "o período" mente por omissão — 📊 a
`Cobertura` da 081 nasceu disso: 19,4% das apólices de 2025 não têm produtor
identificado. Quando a capacidade é parcial, declarar `coverage` deixa de ser
boa prática e vira **obrigação verificada** (mutação M15): `calcular()` levanta
se a métrica esquecer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import (Any, Callable, Dict, List, Optional, Sequence, Tuple)

from app.comercial.cbim import (CommissionFact, FactSet, Money, PolicyFact,
                                RenewalFact, UNAVAILABLE, somar_dinheiro)
from app.comercial.evidence_pack import (BASES_TEMPORAIS, MetricResult,
                                         UNIDADES, metrica, periodo_iso)
from app.comercial.manifesto import (DEGRADED, FRASE_DO_ESTADO, NAO_VERIFICADO,
                                     PARTIAL, ProviderCapabilityManifest, SUPPORTED)

POLICY_VALID_FROM, POLICY_VALID_TO = BASES_TEMPORAIS

__all__ = [
    "MetricDefinition", "MetricResult", "METRICAS", "registrar", "definicao",
    "todas", "calcular", "comparar", "Contexto", "VisaoDeApolice",
    "VisaoDeProdutor", "VisaoDeVencimento", "POLICY_VALID_FROM", "POLICY_VALID_TO",
]


# ==========================================================================
# A VISÃO — a projeção do CBIM na forma que a matemática da 081 lê
# ==========================================================================
#
# ⚠️ Isto **não** é um segundo modelo (CLAUDE.md §5). A matemática continua em
# `app/comercial/calculos.py`, intacta, e continua sendo a mesma que a 081 usa
# em produção. O que estas três classes fazem é apresentar os fatos canônicos
# com os nomes de atributo que aquelas funções leem — `policy_ref`, `premio`,
# `comissao`, `rotulo`, `dias_a_vencer`.
#
# 🔴 E elas carregam a bandeira do que é CONHECIDO. Um `premio` que a fonte não
# expôs não vira `0.0` aqui: ele vem com `premio_conhecido=False` e a métrica
# decide — ou o exclui da soma e declara cobertura, ou bloqueia. O que ele nunca
# faz é entrar como zero, porque zero é uma afirmação sobre o negócio.
@dataclass(frozen=True)
class VisaoDeApolice:
    policy_ref: str
    seguradora: str = ""
    ramo: str = ""
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    e_renovacao: bool = False
    e_endosso: bool = False
    premio: float = 0.0
    comissao: float = 0.0
    premio_conhecido: bool = False
    comissao_conhecida: bool = False


@dataclass(frozen=True)
class VisaoDeProdutor:
    """🔴 `rotulo` é a REFERÊNCIA OPACA do produtor. Nunca o nome.

    O nome existe em `ProducerAssignmentFact.producer_label` e é lido pelo
    Artifact do tenant, que é conteúdo da corretora. O que não pode é ele
    viajar no pacote que vai ao modelo (SPEC-094 §2).
    """

    rotulo: str
    repasse: float = 0.0
    repasse_conhecido: bool = False


@dataclass(frozen=True)
class VisaoDeVencimento:
    policy_ref: str
    seguradora: str = ""
    ramo: str = ""
    valid_to: Optional[date] = None
    dias_a_vencer: int = 0
    produtor: str = ""
    premio: float = 0.0
    premio_conhecido: bool = False


def _float(v: Any) -> Tuple[float, bool]:
    """`(valor, conhecido)`. `UNAVAILABLE` devolve `(0.0, False)` — nunca `(0.0, True)`.

    🔴 A checagem é por FORMA (*tem `amount`?*), e não por `isinstance(v, Money)`.
    Não é frouxidão: um mesmo arquivo `.py` carregado duas vezes — uma como
    parte do pacote, outra por caminho, que é como um guarda isolado carrega —
    produz **duas classes `Money` diferentes**, e `isinstance` diz `False` para
    um valor perfeitamente válido. O sintoma seria a comissão inteira virando
    INDISPONÍVEL, com o dado ali. Foi medido no gate do BLOCO D.

    ⚠️ E a forma é estreita o bastante: o sentinela `UNAVAILABLE` é uma `str`,
    e `str` não tem `amount`.
    """
    quantia = getattr(v, "amount", None)
    if quantia is None:
        return 0.0, False
    try:
        return float(quantia), True
    except (TypeError, ValueError):
        return 0.0, False


def _no_periodo(quando: Optional[date], inicio: date, fim: date) -> bool:
    return quando is not None and inicio <= quando <= fim


# ==========================================================================
# O contexto de UMA rodada de cálculo
# ==========================================================================
@dataclass
class Contexto:
    """Tudo o que uma métrica precisa, já filtrado pela base temporal dela.

    🔴 O filtro acontece AQUI, uma vez, e não dentro de cada fórmula. Duas
    fórmulas filtrando por conta própria divergiriam no primeiro `<=` que uma
    ganhasse e a outra não — e a divergência apareceria como "dois números
    diferentes para a mesma coisa" no mesmo relatório.
    """

    company_id: str
    provider_key: str
    inicio: date
    fim: date
    time_basis: str
    apolices: List[VisaoDeApolice] = field(default_factory=list)
    mapa: Dict[str, VisaoDeProdutor] = field(default_factory=dict)
    vencimentos: List[VisaoDeVencimento] = field(default_factory=list)
    #: A comissão por apólice, das duas pontas — para as métricas DERIVADAS.
    comissoes: Dict[str, CommissionFact] = field(default_factory=dict)
    #: `policy_ref -> [producer_ref]`, para cobertura de produtor.
    produtores_da_apolice: Dict[str, List[str]] = field(default_factory=dict)
    fatos: Optional[FactSet] = None

    @property
    def periodo(self) -> Dict[str, str]:
        return periodo_iso(self.inicio, self.fim)

    @property
    def meses(self) -> int:
        return max(1, (self.fim.year - self.inicio.year) * 12
                   + (self.fim.month - self.inicio.month) + 1)


def montar_contexto(fatos: FactSet, inicio: date, fim: date,
                    time_basis: str) -> Contexto:
    """Projeta o `FactSet` na visão, já recortado pela base temporal pedida.

    ```
    POLICY_VALID_FROM  as apólices cuja vigência COMEÇA no período
    POLICY_VALID_TO    o que VENCE no período
    ```

    ⚠️ O mapa de produtores e as comissões NÃO são recortados: eles são o
    universo de junção. 📊 Recortá-los pelo mesmo período deixaria 97% da
    produção sem produtor conhecido (a interseção medida é de 2,8%).
    """
    if time_basis not in BASES_TEMPORAIS:
        raise ValueError(f"base temporal fora do contrato: {time_basis!r}")

    # ⚠️ O feixe é lido por ATRIBUTO, e não por método. A SPEC fixa a
    # assinatura da fórmula, não a classe do feixe — e um motor que só aceitasse
    # `FactSet` obrigaria todo provider futuro a importar o nosso tipo para ser
    # testado, o que é a fronteira ao contrário.
    politicas = list(getattr(fatos, "policies", ()) or ())
    lista_comissoes = list(getattr(fatos, "commissions", ()) or ())
    lista_atribuicoes = list(getattr(fatos, "assignments", None)
                             or getattr(fatos, "producer_assignments", ()) or ())
    lista_renovacoes = list(getattr(fatos, "renewals", ()) or ())

    comissoes = {c.policy_ref: c for c in lista_comissoes}
    atribuicoes: Dict[str, List[Any]] = {}
    for a in lista_atribuicoes:
        atribuicoes.setdefault(a.policy_ref, []).append(a)

    # --- o mapa de produtor: TODOS os assignments, agregados por apólice ----
    #
    # 🔴 O repasse do mapa soma TODOS os produtores da apólice, e não só o
    # primeiro. 📊 O censo mediu, na mesma apólice, o primeiro com 4% e o
    # segundo com 15%: somar só o primeiro subestima o que sai da corretora.
    # Já o RÓTULO do ranking é o do produtor de ordem 1 — porque a pergunta
    # "quem vendeu" tem uma resposta só, e é a que a 081 sempre deu.
    mapa: Dict[str, VisaoDeProdutor] = {}
    produtores_da_apolice: Dict[str, List[str]] = {}
    for ref, lista in atribuicoes.items():
        produtores_da_apolice[ref] = [a.producer_ref for a in lista if a.producer_ref]
        principal = min(
            (a for a in lista if a.producer_ref),
            key=lambda a: (a.order is None, a.order if a.order is not None else 0),
            default=None)
        if principal is None:
            continue
        comissao = comissoes.get(ref)
        repasse, conhecido = _float(
            comissao.producer_repasse if comissao else UNAVAILABLE)
        mapa[ref] = VisaoDeProdutor(rotulo=principal.producer_ref,
                                    repasse=repasse, repasse_conhecido=conhecido)

    ctx = Contexto(company_id=str(getattr(fatos, "company_id", "") or ""),
                   provider_key=str(getattr(fatos, "provider_key", "") or ""),
                   inicio=inicio, fim=fim, time_basis=time_basis,
                   mapa=mapa, comissoes=comissoes,
                   produtores_da_apolice=produtores_da_apolice, fatos=fatos)

    for p in politicas:
        if not _no_periodo(p.valid_from, inicio, fim):
            continue
        premio, premio_ok = _float(p.premium)
        c = comissoes.get(p.policy_ref)
        comissao, comissao_ok = _float(
            c.broker_commission_accrued if c else UNAVAILABLE)
        ctx.apolices.append(VisaoDeApolice(
            policy_ref=p.policy_ref, seguradora=p.insurer, ramo=p.branch,
            valid_from=p.valid_from, valid_to=p.valid_to,
            e_renovacao=(getattr(p, "kind", "") == "RENEWAL"),
            # 🔴 O literal mora AQUI, no motor, e não numa propriedade do fato:
            # é esta linha que a mutação M5 troca para provar que o filtro de
            # endosso EXISTE. Um filtro que a mutação não alcança não é filtro
            # provado, é filtro afirmado.
            e_endosso=(getattr(p, "kind", "") == "ENDORSEMENT"),
            premio=premio, comissao=comissao,
            premio_conhecido=premio_ok, comissao_conhecida=comissao_ok))

    # 🔴 A população de FIM de vigência vem de DUAS pontas, e não de uma. A
    # rota de vencimentos é a fonte natural, mas uma apólice cuja vigência termina
    # na janela é exposição mesmo quando foi a rota de produção que a trouxe.
    # Ignorá-la seria deixar de fora justamente a intersecção — que é a única
    # população onde a contribuição pós-repasse existe.
    vistos_venc = set()
    for r in lista_renovacoes:
        if not _no_periodo(r.valid_to, inicio, fim):
            continue
        vistos_venc.add(r.policy_ref)
        premio, premio_ok = _float(r.premium)
        ctx.vencimentos.append(VisaoDeVencimento(
            policy_ref=r.policy_ref, seguradora=r.insurer, ramo=r.branch,
            valid_to=r.valid_to,
            dias_a_vencer=int(r.dias_a_vencer or 0),
            produtor=r.producer_ref, premio=premio, premio_conhecido=premio_ok))
    for p in politicas:
        if p.policy_ref in vistos_venc or not _no_periodo(p.valid_to, inicio, fim):
            continue
        vistos_venc.add(p.policy_ref)
        premio, premio_ok = _float(p.premium)
        principal = mapa.get(p.policy_ref)
        ctx.vencimentos.append(VisaoDeVencimento(
            policy_ref=p.policy_ref, seguradora=p.insurer, ramo=p.branch,
            valid_to=p.valid_to,
            dias_a_vencer=(p.valid_to - inicio).days if p.valid_to else 0,
            produtor=principal.rotulo if principal else "",
            premio=premio, premio_conhecido=premio_ok))
    return ctx


# ==========================================================================
# A DEFINIÇÃO
# ==========================================================================
#: O que uma fórmula devolve: `(valor, cobertura, breakdown, avisos)`.
#: `valor` é `None` quando não há número — e `None` vira `UNAVAILABLE`, nunca 0.
Saida = Tuple[Optional[float], Optional[float], List[Dict[str, Any]], List[str]]
Formula = Callable[[Contexto], Saida]


@dataclass(frozen=True)
class MetricDefinition:
    """Uma métrica, declarada por inteiro. Nove campos, e nenhum opcional por acaso."""

    metric_id: str
    version: int
    label: str
    grain: str
    time_basis: str
    required_capabilities: Tuple[str, ...]
    formula: Formula
    #: Como se lê a cobertura desta métrica, em uma frase. Vai ao Artifact.
    coverage_rule: str
    #: 🔴 O que esta métrica **não** pode fazer quando falta dado. Escrito, e
    #: não subentendido: é a linha que o próximo leitor encontra antes de
    #: "arredondar para zero só desta vez".
    forbidden_fallback: str
    unit: str = "count"
    #: Os estados de capacidade que bastam. 📊 O default aceita `PARTIAL`
    #: (com ressalva); a comissão recebida exige `SUPPORTED`, porque o dado só
    #: existe no detalhe de uma apólice por chamada.
    estados_aceitos: Tuple[str, ...] = (SUPPORTED, PARTIAL)
    #: A premissa que o número carrega — vai no envelope como warning. Projeção
    #: sem premissa escrita é adivinhação com cara de número (mutação M9).
    premissa: str = ""

    def __post_init__(self) -> None:
        if self.time_basis not in BASES_TEMPORAIS:
            raise ValueError(
                f"{self.metric_id}: base temporal fora do contrato: {self.time_basis!r}")
        if self.unit not in UNIDADES:
            raise ValueError(f"{self.metric_id}: unidade fora do contrato: {self.unit!r}")

    @property
    def ref(self) -> str:
        """`metric_id@versão` — é assim que o número é citado (ref ⑥)."""
        return f"{self.metric_id}@{self.version}"


METRICAS: Dict[str, MetricDefinition] = {}


def registrar(d: MetricDefinition) -> MetricDefinition:
    if d.metric_id in METRICAS:
        raise ValueError(f"métrica já registrada: {d.metric_id}")
    METRICAS[d.metric_id] = d
    return d


def definicao(metric_id: str) -> MetricDefinition:
    d = METRICAS.get(metric_id)
    if d is None:
        raise KeyError(f"métrica desconhecida: {metric_id!r}")
    return d


def todas() -> Dict[str, MetricDefinition]:
    return dict(METRICAS)


# ==========================================================================
# CALCULAR
# ==========================================================================
def _periodo(period: Any) -> Tuple[date, date]:
    """`(inicio, fim)` a partir de um par de datas OU de `{start, end}` ISO.

    ⚠️ As duas formas existem porque quem pergunta muda: a tool passa datas e
    um envelope já serializado passa o dicionário ISO. Recusar uma delas só
    obrigaria cada chamador a converter por conta — e conversor espalhado é
    onde nasce a divergência de um dia.
    """
    if isinstance(period, dict):
        bruto = (period.get("start"), period.get("end"))
    else:
        bruto = tuple(period)
    saida = []
    for valor in bruto:
        if isinstance(valor, datetime):
            saida.append(valor.date())
        elif isinstance(valor, date):
            saida.append(valor)
        else:
            ano, mes, dia = str(valor or "").strip()[:10].split("-")
            saida.append(date(int(ano), int(mes), int(dia)))
    return saida[0], saida[1]


def _estado_da_capacidade(manifesto: Any, nome: str) -> str:
    """O estado de UMA capacidade, seja qual for a forma do manifesto.

    🔴 O motor exige o mínimo: um `estado(capability)` que devolva uma das
    cinco palavras. Exigir a nossa classe inteira faria o registry recusar
    qualquer manifesto que não fosse o nosso — inclusive o de um provider novo,
    que é exatamente o caso que esta SPEC existe para permitir.
    """
    for atributo in ("estado", "state"):
        f = getattr(manifesto, atributo, None)
        if callable(f):
            return str(f(nome) or NAO_VERIFICADO).strip().upper()
    return NAO_VERIFICADO


def _avaliar(manifesto: Any, d: "MetricDefinition") -> Tuple[bool, List[str], bool]:
    """`(bloqueada, motivos, exige_cobertura)`.

    Sem manifesto, nada bloqueia — e nada bloquear é honesto: quem não
    perguntou pelas capacidades não pode afirmar que elas faltam.
    """
    if manifesto is None:
        return False, [], False
    detalhe = getattr(manifesto, "capacidade", None)
    motivos: List[str] = []
    bloqueada = False
    exige = False
    for nome in d.required_capabilities:
        estado = _estado_da_capacidade(manifesto, nome)
        texto = FRASE_DO_ESTADO.get(estado, estado)
        if callable(detalhe):
            try:
                texto = detalhe(nome).frase()
            except Exception:  # noqa: BLE001
                pass
        if estado in (PARTIAL, DEGRADED):
            exige = True
        if estado in d.estados_aceitos:
            if estado == PARTIAL:
                motivos.append("%s: %s" % (nome, texto))
            continue
        bloqueada = True
        motivos.append("%s: %s" % (nome, texto))
    return bloqueada, motivos, exige


def calcular(metric_id: str, facts: FactSet, period: Tuple[date, date],
             time_basis: Optional[str] = None,
             manifest: Optional[ProviderCapabilityManifest] = None,
             contexto: Optional[Contexto] = None) -> MetricResult:
    """Um `MetricResult`, com tudo o que é preciso para conferir se ele é verdade.

    A ordem não é arbitrária:

    ```
    1  a base temporal pedida é a da métrica?        senão ValueError (M6)
    2  a fonte entrega as capacidades exigidas?      senão UNAVAILABLE + MOTIVO
    3  a fórmula roda sobre o contexto já recortado
    4  métrica parcial declarou cobertura?           senão ValueError (M15)
    ```

    🔴 O passo 2 vem ANTES do 3 de propósito. Calcular primeiro e descartar
    depois produziria, no caminho de erro, um número correto sobre uma
    população errada — e alguém acabaria por publicá-lo.
    """
    d = definicao(metric_id)
    inicio, fim = _periodo(period)
    janela = periodo_iso(inicio, fim)
    avisos: List[str] = []

    # 🔴 A base temporal de uma métrica é PROPRIEDADE DELA, e não parâmetro de
    # chamada. Pedir a exposição de renovação em base de emissão não muda a
    # população: muda só o que quem pediu ACHA que está vendo. Então a definição
    # vence, o envelope declara a base de verdade, e o pedido divergente vira
    # aviso.
    # ⚠️ A recusa DURA mora em `comparar()`, que é onde o estrago acontece: é
    # comparar duas bases que produz a "queda" que nunca houve (M6).
    if time_basis and time_basis != d.time_basis:
        avisos.append(
            f"pedida em {time_basis}, mas {d.ref} é calculada em {d.time_basis} "
            f"— são populações diferentes, e vale a base da métrica")

    bloqueada, motivos, exige_cobertura = _avaliar(manifest, d)
    avisos.extend(motivos)

    if bloqueada:
        return metrica(d.metric_id, None, d.unit, period=janela,
                       time_basis=d.time_basis, coverage=None, version=d.version,
                       provider_key=str(getattr(facts, "provider_key", "") or ""),
                       warnings=avisos + [d.forbidden_fallback])

    ctx = contexto or montar_contexto(facts, inicio, fim, d.time_basis)
    if ctx.time_basis != d.time_basis:
        ctx = montar_contexto(facts, inicio, fim, d.time_basis)
    valor, cobertura, breakdown, mais = d.formula(ctx)
    avisos.extend(mais)
    if d.premissa:
        avisos.append(d.premissa)

    if cobertura is None and exige_cobertura:
        raise ValueError(
            f"{d.ref}: a capacidade exigida é parcial e a métrica não declarou "
            f"cobertura. Um número parcial apresentado como total mente por "
            f"omissão (M15) — {d.coverage_rule}")

    return metrica(d.metric_id, valor, d.unit, period=janela,
                   time_basis=d.time_basis, coverage=cobertura,
                   version=d.version,
                   provider_key=str(getattr(facts, "provider_key", "") or ""),
                   warnings=avisos, breakdown=breakdown)


def calcular_varias(metric_ids: Sequence[str], facts: FactSet,
                    period: Tuple[date, date],
                    manifest: Optional[ProviderCapabilityManifest] = None
                    ) -> List[MetricResult]:
    """Várias métricas sobre UM lote — e um contexto por base temporal.

    🔴 As duas bases são montadas no máximo uma vez cada. Não é otimização:
    é o que garante que duas métricas da mesma base vejam **a mesma população**.
    """
    contextos: Dict[str, Contexto] = {}
    saida: List[MetricResult] = []
    for mid in metric_ids:
        d = definicao(mid)
        if d.time_basis not in contextos:
            contextos[d.time_basis] = montar_contexto(
                facts, period[0], period[1], d.time_basis)
        saida.append(calcular(mid, facts, period, manifest=manifest,
                              contexto=contextos[d.time_basis]))
    return saida


# ==========================================================================
# COMPARAR — e a recusa que é o coração da M6
# ==========================================================================
def comparar(a: MetricResult, b: MetricResult) -> Dict[str, Any]:
    """A variação entre dois resultados. **Recusa** o que não é comparável.

    🔴 Três recusas, e a terceira é a que a SPEC existe para impor:

    ```
    métricas diferentes    somar maçã com laranja
    unidades diferentes    `0,806` lido como reais e `1.680` como porcentagem
    BASES TEMPORAIS        📊 duas populações com 2,8% de interseção  (M6)
    ```

    A terceira **não** é um aviso. Comparar o que começou num período com o que
    termina noutro produz um delta que parece uma queda de negócio e é só uma
    troca de eixo — o defeito que trocar início por fim de vigência custou à 081.

    `delta_pct` é `None` quando a base é zero: um cartão que mostra "∞%" não
    informa nada, e `0,0%` afirmaria estabilidade onde houve partida do zero.
    """
    # ⚠️ Métrica e unidade diferentes viram AVISO, e não exceção: comparar
    # apólices com reais é um pedido esquisito, mas quem o faz enxerga as duas
    # unidades no envelope e se corrige. A base temporal é outra história — ela
    # não aparece em lugar nenhum do número, e o erro dela SE PARECE com um
    # resultado de negócio. É por isso que só ela levanta.
    ressalvas: List[str] = []
    if a.metric_id != b.metric_id:
        ressalvas.append(
            f"comparação entre métricas diferentes ({a.metric_id} × {b.metric_id})")
    if a.unit != b.unit:
        ressalvas.append(
            f"unidades diferentes ({a.unit} × {b.unit}): a variação não tem "
            f"significado numérico")
    if a.time_basis != b.time_basis:
        raise ValueError(
            f"{a.metric_id}: bases temporais diferentes ({a.time_basis} × "
            f"{b.time_basis}). São duas populações, não a mesma em outra janela "
            f"— 📊 a interseção medida entre elas é de 2,8%")
    incomparavel = (a.indisponivel or b.indisponivel or a.unit != b.unit
                    or isinstance(a.value, dict) or isinstance(b.value, dict))
    if incomparavel:
        return {"metric_id": a.metric_id, "unit": a.unit,
                "atual": a.value, "anterior": b.value,
                "delta": UNAVAILABLE, "delta_pct": UNAVAILABLE,
                "time_basis": a.time_basis,
                "warnings": ressalvas + ["não há variação a afirmar entre estes "
                                         "dois valores"]}
    atual, anterior = float(a.value), float(b.value)
    return {
        "metric_id": a.metric_id, "unit": a.unit,
        "atual": atual, "anterior": anterior,
        "delta": atual - anterior,
        "delta_pct": (100.0 * (atual - anterior) / anterior) if anterior else None,
        "time_basis": a.time_basis,
        "warnings": ressalvas,
    }


# ==========================================================================
# AS DEFINIÇÕES — carregadas por INJEÇÃO, e não por import
# ==========================================================================
def _carregar_definicoes() -> None:
    """Cada arquivo de definição recebe ESTE módulo e se registra nele.

    🔴 Injeção, e não `import`, por um defeito que ela evita: quando alguém
    carrega este arquivo por CAMINHO — que é como um guarda isolado o carrega,
    para não arrastar o pacote inteiro —, um import absoluto dentro do arquivo de
    definição criaria uma SEGUNDA cópia do registry. Uma ficaria com as 16
    métricas e a outra vazia, e `calcular()` responderia *"métrica desconhecida"*
    sobre uma métrica que existe. É o tipo de defeito que só aparece no guarda, e
    tarde.

    ⚠️ Idempotente: chamada duas vezes, não registra duas vezes.
    """
    import importlib.util
    import os
    import sys

    if METRICAS:
        return
    pasta = os.path.dirname(os.path.abspath(__file__))
    eu = sys.modules[__name__]
    for nome in ("producao", "mix", "produtores", "renovacao"):
        caminho = os.path.join(pasta, nome + ".py")
        if not os.path.exists(caminho):
            continue
        chave = "_094_definicoes_%s_%x" % (nome, id(eu))
        spec = importlib.util.spec_from_file_location(chave, caminho)
        modulo = importlib.util.module_from_spec(spec)
        sys.modules[chave] = modulo
        try:
            spec.loader.exec_module(modulo)   # type: ignore[union-attr]
            modulo.instalar(eu)
        finally:
            sys.modules.pop(chave, None)


_carregar_definicoes()
