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
from app.comercial.evidence_pack import (BAIXA, BASES_ACEITAS, BASES_TEMPORAIS,
                                         COMPETENCIA, MetricResult,
                                         ORDEM_DA_CONFIANCA, UNIDADES, metrica,
                                         periodo_iso)
from app.comercial.manifesto import (DEGRADED, FRASE_DO_ESTADO, NAO_VERIFICADO,
                                     PARTIAL, ProviderCapabilityManifest,
                                     SEM_AMOSTRA, SUPPORTED)

POLICY_VALID_FROM, POLICY_VALID_TO = BASES_TEMPORAIS

__all__ = [
    "MetricDefinition", "MetricResult", "METRICAS", "registrar", "definicao",
    "todas", "calcular", "comparar", "Contexto", "VisaoDeApolice",
    "VisaoDeProdutor", "VisaoDeVencimento", "POLICY_VALID_FROM", "POLICY_VALID_TO",
    "FIXTURE_094", "GOLDEN_INDISPONIVEL",
]

# ==========================================================================
# 🔴 SPEC-094.1 · BLOCO D — a PERGUNTA VERIFICADA e o GOLDEN
# ==========================================================================
#
# Modelado no [Verified Query Repository do Cortex Analyst][vqr]: perguntas
# verificadas por gente melhoram a precisão do sistema (📊 +20 p.p. em teste
# controlado da Snowflake) e, mais do que isso, dão à régua um jeito de
# perguntar *"o que respondia certo e passou a falhar?"*.
#
# [vqr]: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst/verified-query-repository
#
# Uma métrica sem os dois campos é uma métrica que ninguém consegue conferir:
# `pergunta_verificada` diz **que pergunta do dono este número responde**, em
# português, e `golden` diz **que número ele dá numa população conhecida**. Sem
# a primeira, o modelo escolhe a métrica pelo nome do `metric_id` — que é
# jargão. Sem o segundo, uma mudança de fórmula troca o número em silêncio, e o
# silêncio é o modo de falha caro (CLAUDE.md §9.5).
#
# ⚠️ Os dois campos têm default de dataclass porque as definições são passadas
# como `**kw` e há campos opcionais antes deles. **A obrigatoriedade é do
# `__post_init__`**, e não da assinatura — é lá que a mutação do guarda do
# protocolo (BLOCO E) bate.

#: A população conhecida sobre a qual os `golden` desta rodada foram medidos.
#: 🔴 É a fixture sintética da SPEC-094, montada pelo guarda dela em
#: `backend/tests/` (`_apolices_de_fixture` + `_vencimentos_de_fixture` +
#: `_mapa_de_fixture`). ⚠️ O nome do ARQUIVO do guarda não é escrito aqui:
#: ele cita a fonte piloto, e a regra M1 vale para o arquivo inteiro,
#: comentário incluído.
#: **6 apólices de 2025** (3 NEW, 3 RENEWAL; prêmio 29.000,00; comissão
#: 5.000,00), **4 vencimentos** e **4 atribuições de produtor** em 2 produtores
#: opacos, lida na janela **01/01/2025 → 31/12/2026** e SEM manifesto.
#:
#: ⚠️ A janela faz parte da fixture, e não é detalhe: `renewal.exposure` e
#: `projection.run_rate` são funções dela. Um golden sem janela declarada seria
#: um número que ninguém consegue reproduzir — que é o mesmo defeito que
#: `time_basis` existe para impedir.
#:
#: ⛔ NENHUM dado de pessoa: as referências são opacas por construção.
FIXTURE_094 = "094:6-apolices-2025+4-vencimentos@2025-01-01..2026-12-31"

#: O `esperado` de uma métrica que, nesta fixture, **não tem número**. 🔴 Ele é
#: o sentinela do CBIM, e não `0.0` nem `None`: um golden que afirmasse zero
#: ensinaria a régua a aceitar o zero de consolação que a 094 inteira recusa.
GOLDEN_INDISPONIVEL = UNAVAILABLE


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
    #: 🔴 O feixe de PLATAFORMA — a estatística pública do mercado, por código
    #: de companhia × mês × ramo (SPEC-094.1 BLOCO B).
    #:
    #: ⚠️ O nome da FONTE não é escrito aqui, e a omissão é a regra M1: nenhum
    #: arquivo de `metricas/` pode nomear um sistema de gestão nem um órgão —
    #: quem sabe de onde o feixe veio é o adapter. O guarda do protocolo
    #: (`test_o_relatorio_nasce_pelo_protocolo.py` [e]) mede isto, e foi ele
    #: que pegou a primeira versão desta linha.
    #:
    #: Ele é **separado** do
    #: `FactSet` de propósito: o `FactSet` é da corretora e tem `company_id`;
    #: este é de todas, e misturar os dois num feixe só seria a primeira porta
    #: para o dado de uma casa aparecer no relatório de outra (CLAUDE.md §7).
    #:
    #: ⚠️ A anotação é uma STRING: a classe nasce em `cbim.py`, e importá-la
    #: aqui faria o registry — que é o motor — depender do vocabulário de fatos
    #: antes de ele existir. `None` é o caso normal: nenhuma das 16 métricas de
    #: hoje olha para o mercado, e uma fórmula que o exija tem de dizer isso
    #: nas `required_capabilities` dela.
    mercado: Optional["MarketFactSet"] = None  # noqa: F821

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
    # 🔴 `BASES_ACEITAS` e nao `BASES_TEMPORAIS`: a competencia contabil e uma
    # base legitima (SPEC-094.1, conserto de 04/09/2026), e o par continua sendo
    # so o vocabulario da CARTEIRA. A projecao das apolices e a mesma — o que
    # muda e o que o envelope DECLARA.
    if time_basis not in BASES_ACEITAS:
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
    #: 🔴 A PERGUNTA DO DONO que este número responde, em português. Ela é o
    #: que o chat lista quando o modelo pergunta "o que existe?" antes de
    #: propor uma métrica nova (ref ⑥) — e é ela que evita a proposta duplicada,
    #: porque ninguém reconhece a própria pergunta num `metric_id`.
    pergunta_verificada: str = ""
    #: 🔴 O número esperado numa população conhecida:
    #: `{"fixture": str, "esperado": float | "UNAVAILABLE"}`.
    #: É a régua de regressão — "o que respondia certo e passou a falhar" (ref ④).
    golden: Dict[str, Any] = field(default_factory=dict)
    #: 🔴 SPEC-094.1, conserto de 04/09/2026 — QUAIS FONTES esta métrica lê.
    #:
    #: 📊 O defeito que estes dois campos consertam: a métrica DERIVED que
    #: compara a carteira com o mercado saía com `source_refs=[]`, um único
    #: `provider_key` e um único `period`. O envelope declarava UMA fonte para
    #: um número que veio de DUAS — e quem fosse conferir contra aquela fonte
    #: acharia a metade que fecha e concluiria que o número estava certo.
    #:
    #: ⚠️ São BOOLEANOS, e não nomes: nenhum arquivo de `metricas/` pode nomear
    #: um sistema de gestão nem um órgão (M1). Quem sabe o NOME de cada fonte é
    #: o feixe que chega, e é dele que `calcular` copia o `provider_key`.
    usa_carteira: bool = True
    usa_mercado: bool = False

    def __post_init__(self) -> None:
        if self.time_basis not in BASES_ACEITAS:
            raise ValueError(
                f"{self.metric_id}: base temporal fora do contrato: {self.time_basis!r}")
        if self.unit not in UNIDADES:
            raise ValueError(f"{self.metric_id}: unidade fora do contrato: {self.unit!r}")
        # 🔴 As duas exigências da 094.1. Elas levantam no REGISTRO, e não numa
        # conferência agendada: uma definição incompleta nunca chega a existir,
        # e por isso não há como esquecer de conferir depois.
        if not str(self.pergunta_verificada or "").strip():
            raise ValueError(
                f"{self.metric_id}: sem `pergunta_verificada`. Escreva, em "
                f"português, a pergunta do dono que este número responde — é "
                f"ela que o chat lista antes de propor uma métrica nova, e é "
                f"por ela que se descobre que a métrica já existe")
        alvo = self.golden or {}
        if not str(alvo.get("fixture") or "").strip() or "esperado" not in alvo:
            raise ValueError(
                f"{self.metric_id}: sem `golden` completo. Declare "
                f"{{'fixture': ..., 'esperado': ...}} — sem o número esperado "
                f"numa população conhecida, uma mudança de fórmula troca o "
                f"resultado em SILÊNCIO, e silêncio é o modo de falha caro")
        esperado = alvo.get("esperado")
        if esperado != GOLDEN_INDISPONIVEL and not isinstance(
                esperado, (int, float)):
            raise ValueError(
                f"{self.metric_id}: `golden['esperado']` é um número ou o "
                f"sentinela {GOLDEN_INDISPONIVEL!r} — nunca `None` nem 0 de "
                f"consolação (recebido: {esperado!r})")

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


#: A frase que uma métrica devolve quando a rota de que ela depende veio VAZIA.
#: 🔴 Ela diz **sobre o período**, e não sobre a fonte: a rota respondeu, e não
#: tinha linha. As duas coisas são diferentes, e o Artifact escreve a diferença.
ROTA_SEM_LINHAS = ("fonte sem linhas no período em %s: não há população para "
                   "esta conta — INDISPONÍVEL, e não zero")


def _rotas_do_lote(facts: Any) -> Tuple[set, set]:
    """`(rotas lidas, rotas que vieram VAZIAS)` — do fingerprint deste lote.

    🔴 Uma fonte só, e não um campo novo: `FactSet.fingerprints` já carrega uma
    entrada por rota LIDA, e o adapter grava `SEM_AMOSTRA` na rota que devolveu
    zero linhas. Um segundo campo divergiria do primeiro no dia em que alguém
    esquecesse de preencher um dos dois.
    """
    marcas = getattr(facts, "fingerprints", None) or {}
    lidas = {r for r in marcas if not str(r).startswith("__")}
    vazias = {r for r in lidas if marcas.get(r) == SEM_AMOSTRA}
    return lidas, vazias


def _sem_populacao(manifesto: Any, nome: str, lidas: set, vazias: set) -> bool:
    """Esta capacidade ficou sem NENHUMA rota com linha, nesta leitura?

    🔴 O recorte é `source_routes ∩ rotas lidas`, e o recorte é o ponto inteiro.
    📊 O censo lista, para `portfolio.policies`, cinco rotas — mas esta leitura
    toca duas. Perguntar "alguma das cinco veio vazia?" bloquearia a métrica por
    causa de uma rota que ninguém chamou; perguntar "as cinco vieram vazias?"
    nunca bloquearia nada, porque três delas nem foram lidas. A pergunta certa
    é sobre as rotas desta leitura.

    📊 Achado pelo red team em 03/09/2026: com `/documentos_bi` devolvendo `[]` e
    `/renovacoes` cheia, `production.policy_count` saía **0,0 com cobertura 1.0
    e confiança HIGH** — "a corretora não emitiu nada", afirmado com a maior
    confiança que o produto sabe dar, sobre uma rota que só não respondeu.
    """
    if not vazias:
        return False
    cap = getattr(manifesto, "capacidade", None)
    if not callable(cap):
        return False
    try:
        capacidade = cap(nome)
        rotas = set(capacidade.source_routes or ())
        primaria = str(getattr(capacidade, "rota_primaria", "") or "")
    except Exception:  # noqa: BLE001
        return False
    # 🔴 A ROTA PRIMÁRIA decide sozinha, e é o conserto de 03/09/2026.
    #
    # 📊 O juiz mediu na peça viva: `/renovacoes` vazia com `/documentos_bi`
    # cheia devolvia `renewal.exposure = 0,0 · cobertura 1,0 · HIGH`, e a peça
    # afirmava *"este 0 é um fato sobre a carteira"*. A regra antiga
    # (`efetivas <= vazias`) só bloqueia quando TODAS as rotas lidas vêm vazias
    # — e `portfolio.renewals` lista duas, das quais só uma dá população.
    #
    # ⚠️ Uma rota secundária cheia não substitui a primária vazia: `/renovacoes`
    # filtra `fimvig` (o que VENCE) e `/documentos_bi` filtra `inivig` (o que
    # foi EMITIDO). Somar as duas populações para dizer "há dados" é trocar a
    # pergunta pelo que sobrou dela.
    if primaria and primaria in lidas:
        return primaria in vazias
    efetivas = rotas & lidas
    return bool(efetivas) and efetivas <= vazias


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


def _avaliar(manifesto: Any, d: "MetricDefinition",
             lidas: Optional[set] = None,
             vazias: Optional[set] = None) -> Tuple[bool, List[str], bool]:
    """`(bloqueada, motivos, exige_cobertura)`.

    Sem manifesto, nada bloqueia — e nada bloquear é honesto: quem não
    perguntou pelas capacidades não pode afirmar que elas faltam.
    """
    if manifesto is None:
        return False, [], False
    lidas = lidas if lidas is not None else set()
    vazias = vazias if vazias is not None else set()
    detalhe = getattr(manifesto, "capacidade", None)
    motivos: List[str] = []
    bloqueada = False
    exige = False
    for nome in d.required_capabilities:
        if _sem_populacao(manifesto, nome, lidas, vazias):
            bloqueada = True
            rotas = sorted(set(detalhe(nome).source_routes or ()) & vazias)
            motivos.append("%s: %s" % (nome, ROTA_SEM_LINHAS % ", ".join(rotas)))
            continue
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


# ==========================================================================
# AS FONTES DE UM NUMERO — SPEC-094.1, conserto de 04/09/2026
# ==========================================================================
def _competencia(d: date) -> str:
    """`AAAAMM` — o mes contabil desta data."""
    return "%04d%02d" % (d.year, d.month)


def janela_de_competencia(feixe: Any, inicio: date, fim: date) -> Dict[str, str]:
    """`{start, end}` em competencia — a do FEIXE dentro do periodo, quando ela
    existe, e a do periodo quando o feixe nao tem celula nenhuma la dentro.

    🔴 A diferenca importa: dizer que o mercado foi lido de janeiro a dezembro
    quando a base publica so fechou ate junho e afirmar sobre seis meses que
    ninguem leu. O `source_ref` tem de dizer o que FOI lido.
    """
    piso, teto = _competencia(inicio), _competencia(fim)
    vistas = sorted(
        c for c in (str(getattr(x, "damesano", "") or "").strip()
                    for x in list(getattr(feixe, "facts", ()) or ()))
        if c and piso <= c <= teto)
    if not vistas:
        return {"start": piso, "end": teto}
    return {"start": vistas[0], "end": vistas[-1]}


def fontes_do_numero(d: "MetricDefinition", facts: Any, feixe: Any,
                     janela: Dict[str, str], inicio: date,
                     fim: date) -> Tuple[List[Dict[str, str]], str]:
    """`(source_refs, provider_key)` — UMA entrada por fonte que o numero leu.

    ⚠️ O feixe de mercado so entra quando ele CHEGOU. Uma metrica que declara
    ler o mercado e roda sem ele devolve INDISPONIVEL pela propria formula; o
    envelope nao pode declarar uma fonte que nao foi consultada — "nao
    perguntei" nao e "perguntei e veio vazio".
    """
    refs: List[Dict[str, str]] = []
    provedores: List[str] = []
    if d.usa_carteira:
        chave = str(getattr(facts, "provider_key", "") or "")
        refs.append({"provider": chave, "time_basis": d.time_basis
                     if d.time_basis in BASES_TEMPORAIS else BASES_TEMPORAIS[0],
                     "period": dict(janela)})
        if chave:
            provedores.append(chave)
    if d.usa_mercado and feixe is not None:
        chave = str(getattr(feixe, "provider_key", "") or "")
        refs.append({"provider": chave, "time_basis": COMPETENCIA,
                     "period": janela_de_competencia(feixe, inicio, fim)})
        if chave:
            provedores.append(chave)
    return refs, "+".join(dict.fromkeys(provedores))


def calcular(metric_id: str, facts: FactSet, period: Tuple[date, date],
             time_basis: Optional[str] = None,
             manifest: Optional[ProviderCapabilityManifest] = None,
             contexto: Optional[Contexto] = None,
             mercado: Optional["MarketFactSet"] = None) -> MetricResult:  # noqa: F821
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

    lidas, vazias = _rotas_do_lote(facts)
    bloqueada, motivos, exige_cobertura = _avaliar(manifest, d, lidas, vazias)
    avisos.extend(motivos)

    feixe_do_mercado = mercado if mercado is not None else getattr(
        contexto, "mercado", None)
    fontes, provedor = fontes_do_numero(d, facts, feixe_do_mercado, janela,
                                        inicio, fim)

    if bloqueada:
        return metrica(d.metric_id, None, d.unit, period=janela,
                       time_basis=d.time_basis, coverage=None, version=d.version,
                       provider_key=provedor or str(
                           getattr(facts, "provider_key", "") or ""),
                       source_refs=fontes,
                       warnings=avisos + [d.forbidden_fallback])

    ctx = contexto or montar_contexto(facts, inicio, fim, d.time_basis)
    if ctx.time_basis != d.time_basis:
        ctx = montar_contexto(facts, inicio, fim, d.time_basis)
    # 🔴 O feixe de mercado é REPASSADO, e nunca inventado: quando quem chamou
    # não o passou, o que estava no contexto continua valendo (é assim que
    # `calcular_varias` monta um contexto e o reusa em várias métricas). O que
    # esta linha nunca faz é apagar um feixe existente com `None`.
    if mercado is not None:
        ctx.mercado = mercado
    # ⚠️ A fórmula devolve QUATRO itens, e pode devolver um quinto: o TETO de
    # confiança. Opcional de propósito — as 15 métricas que não precisam dele
    # não pagam nada, e a que precisa não tem de inventar um canal (uma marca
    # no texto do aviso, por exemplo, que o modelo leria e narraria).
    saida_da_formula = d.formula(ctx)
    valor, cobertura, breakdown, mais = saida_da_formula[:4]
    teto_de_confianca = saida_da_formula[4] if len(saida_da_formula) > 4 else None
    avisos.extend(mais)
    if d.premissa:
        avisos.append(d.premissa)

    if cobertura is None and exige_cobertura:
        raise ValueError(
            f"{d.ref}: a capacidade exigida é parcial e a métrica não declarou "
            f"cobertura. Um número parcial apresentado como total mente por "
            f"omissão (M15) — {d.coverage_rule}")

    # 🔴 As fontes sao remontadas DEPOIS da formula: e so aqui que se sabe se o
    # feixe de mercado chegou de verdade (ele pode ter vindo pelo `contexto`).
    fontes, provedor = fontes_do_numero(d, facts, getattr(ctx, "mercado", None),
                                        janela, inicio, fim)
    return metrica(d.metric_id, valor, d.unit, period=janela,
                   time_basis=d.time_basis, coverage=cobertura,
                   version=d.version,
                   provider_key=provedor or str(
                       getattr(facts, "provider_key", "") or ""),
                   source_refs=fontes,
                   warnings=avisos, breakdown=breakdown,
                   confianca_maxima=teto_de_confianca)


def calcular_varias(metric_ids: Sequence[str], facts: FactSet,
                    period: Tuple[date, date],
                    manifest: Optional[ProviderCapabilityManifest] = None,
                    mercado: Optional["MarketFactSet"] = None  # noqa: F821
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
                              contexto=contextos[d.time_basis],
                              mercado=mercado))
    return saida


# ==========================================================================
# COMPARAR — e a recusa que é o coração da M6
# ==========================================================================
#: 💭 Quanto duas janelas podem diferir e ainda serem "a mesma janela". Cinco
#: por cento cobre o que é ruído de calendário — fevereiro contra março, ano
#: bissexto, mês de 30 contra mês de 31 — e não cobre trimestre contra ano.
TOLERANCIA_DE_JANELA_PCT = 5.0


def _dias_da_janela(m: MetricResult) -> Optional[int]:
    """Quantos dias a janela deste resultado cobre. `None` se não der para ler."""
    try:
        inicio, fim = _periodo(m.period)
    except Exception:  # noqa: BLE001
        return None
    return (fim - inicio).days + 1


def _janelas_desiguais(a: MetricResult, b: MetricResult) -> Tuple[bool, int, int]:
    """`(desiguais?, dias de a, dias de b)`.

    ⚠️ Janela ilegível de um dos lados **não** vira "desigual": não se afirma
    diferença contra uma medição que não existe. Ela sai como `(False, 0, 0)` e
    a comparação segue — o que ela não faz é inventar um alarme.
    """
    dias_a, dias_b = _dias_da_janela(a), _dias_da_janela(b)
    if not dias_a or not dias_b:
        return False, dias_a or 0, dias_b or 0
    maior = max(dias_a, dias_b)
    diferenca = 100.0 * abs(dias_a - dias_b) / maior
    return diferenca > TOLERANCIA_DE_JANELA_PCT, dias_a, dias_b


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

    🔴 E a QUARTA recusa, acrescentada em 03/09/2026: **janelas de duração
    diferente**. 📊 Achado pelo red team: `comparar(2025 inteiro, Q1 2024)`
    devolvia `delta_pct = 300,82` com `warnings: []` — quatro vezes mais dias de
    um lado, e o número saía limpo, com cara de crescimento de 300%. O `compare`
    é texto livre que o modelo preenche (*"contra o primeiro trimestre"*), então
    esta não é uma combinação exótica: é uma frase comum.

    ⚠️ Ela não levanta como a base temporal. Comparar 12 meses com 3 é um pedido
    ESQUISITO, e há quem queira mesmo — quem compara "o ano até hoje" com "o ano
    passado inteiro" sabe o que está fazendo. O que não pode é sair sem a
    ressalva. Então: `delta` e `delta_pct` viram `UNAVAILABLE`, a confiança cai
    para `LOW`, e o motivo vai escrito com os dois números de dias.
    """
    # ⚠️ Métrica e unidade diferentes viram AVISO, e não exceção: comparar
    # apólices com reais é um pedido esquisito, mas quem o faz enxerga as duas
    # unidades no envelope e se corrige. A base temporal é outra história — ela
    # não aparece em lugar nenhum do número, e o erro dela SE PARECE com um
    # resultado de negócio. É por isso que só ela levanta.
    ressalvas: List[str] = []
    desiguais, dias_a, dias_b = _janelas_desiguais(a, b)
    if desiguais:
        ressalvas.append(
            "janelas de duração diferente (%d dia(s) × %d dia(s), %.0f%% de "
            "diferença): a variação entre elas mede o TAMANHO DA JANELA, e não o "
            "negócio — não há delta a afirmar" % (
                dias_a, dias_b,
                100.0 * abs(dias_a - dias_b) / max(dias_a, dias_b, 1)))
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
    incomparavel = (desiguais or a.indisponivel or b.indisponivel
                    or a.unit != b.unit
                    or isinstance(a.value, dict) or isinstance(b.value, dict))
    if incomparavel:
        return {"metric_id": a.metric_id, "unit": a.unit,
                "atual": a.value, "anterior": b.value,
                "delta": UNAVAILABLE, "delta_pct": UNAVAILABLE,
                "time_basis": a.time_basis, "confidence": BAIXA,
                "warnings": ressalvas + ["não há variação a afirmar entre estes "
                                         "dois valores"]}
    atual, anterior = float(a.value), float(b.value)
    return {
        "metric_id": a.metric_id, "unit": a.unit,
        "atual": atual, "anterior": anterior,
        "delta": atual - anterior,
        "delta_pct": (100.0 * (atual - anterior) / anterior) if anterior else None,
        "time_basis": a.time_basis,
        "confidence": min((a.confidence, b.confidence),
                          key=lambda c: ORDEM_DA_CONFIANCA.index(c)
                          if c in ORDEM_DA_CONFIANCA else 0),
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
    # 🔴 SPEC-094.1 · BLOCOS A e B: os quatro arquivos novos entram AQUI, e não
    # por auto-descoberta da pasta. Um `glob` transformaria qualquer `.py`
    # esquecido em definição registrada — e o registro do que o produto responde
    # é lista explícita, revisada, ou não é registro.
    for nome in ("producao", "mix", "produtores", "renovacao",
                 "sinistros", "funil", "carteira", "mercado"):
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


# ==========================================================================
# O GOLDEN — a régua de regressão, e o carregador que a alimenta
# ==========================================================================
def fatos_do_golden(d: "MetricDefinition"):
    """O `FactSet` da fixture que a definição declara em `golden["fixture"]`.

    🔴 Ele existe para que o guarda consiga fazer a única pergunta que separa
    uma métrica viva de uma métrica que já foi certa: **este número ainda é
    este número?** (ref ④, o Verified Query Repository). Sem um carregador, o
    campo `golden` seria uma anotação — e anotação não reprova nada.

    ⚠️ A fixture é a população canônica da 094: 6 apólices de 2025, 4
    vencimentos, e — desde a 094.1 — 5 sinistros, 3 cotações e 3 clientes. Ela
    vem do **provider de referência**, que é CBIM puro: 📊 ele não importa fonte
    nenhuma (é a outra ponta da M17), e por isso o motor lê dali sem aprender o
    dialeto de sistema de gestão nenhum.

    🔴 E o import é LOCAL, dentro da função. Um import no topo faria este
    módulo — que é o motor — carregar um pacote de providers para responder
    `calcular()`, e o primeiro efeito seria um ciclo de importação no dia em que
    um provider quisesse ler uma definição.
    """
    from app.providers.reference_analytics_provider import fatos_de_fixture

    fixture = str((getattr(d, "golden", None) or {}).get("fixture") or "").strip()
    if not fixture:
        raise ValueError(
            f"{getattr(d, 'metric_id', '?')}: sem fixture declarada no golden")
    if not fixture.startswith("094:"):
        raise ValueError(
            f"{getattr(d, 'metric_id', '?')}: fixture desconhecida {fixture!r}. "
            f"Hoje existe uma so ({FIXTURE_094!r}); uma segunda tem de trazer o "
            f"carregador dela junto, e nao ser adivinhada por caminho")
    return fatos_de_fixture()
