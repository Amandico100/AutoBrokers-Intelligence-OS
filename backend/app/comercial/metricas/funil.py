# -*- coding: utf-8 -*-
"""O funil de cotações — SPEC-094.1 · BLOCO A. **Duas métricas, dois vazios diferentes.**

📊 O censo v2.1 §A4 mediu as três rotas do funil e achou DOIS achados que não se
confundem, e que produzem `UNAVAILABLE` por motivos opostos:

```
ACERVO VAZIO       as três rotas RESPONDEM e não têm linha no período
                   📊 `/negocios_andamento` = 1 negócio em 2025 inteiro;
                   `/em_calculo` e `/negocios_finalizados` = 404, que é VAZIO.
                   A corretora piloto não usa o CRM da fonte.
CAPACIDADE AUSENTE `motivo_perda` NÃO ESTÁ entre as 30 chaves do GET. Ele existe
                   só no CORPO do `POST /negocio` da documentação — não há fonte
                   de LEITURA provada.
```

🔴 A diferença importa para quem lê. *"Você não perdeu nenhuma cotação"* e
*"eu não consigo ver por que você perdeu"* são frases diferentes, e a segunda é
a verdadeira. Por isso `quotes.lost_reasons@1` **nunca** devolve número — nem
zero, nem lista vazia — e escreve o motivo no envelope.

⚠️ E o 500 das três rotas era **parâmetro faltando**, não rota quebrada: com
`status` na query elas respondem. Isso está no adapter, não aqui — a fórmula não
conhece a fonte (M1).
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.comercial.evidence_pack import BASES_TEMPORAIS

POLICY_VALID_FROM, POLICY_VALID_TO = BASES_TEMPORAIS

_DEFINICOES: List[Dict[str, Any]] = []

FIXTURE = "094:6-apolices-2025+4-vencimentos@2025-01-01..2026-12-31"
INDISPONIVEL = "UNAVAILABLE"

#: A ordem em que as etapas são lidas. 💭 É a ordem do trabalho comercial, e é
#: ela que faz o gráfico de funil descer em vez de embaralhar.
ETAPAS = ("EM_ANDAMENTO", "EM_CALCULO", "FINALIZADO")

Contexto = Any
Saida = Any


def golden(esperado):
    return {"fixture": FIXTURE, "esperado": esperado}


def instalar(reg) -> None:
    for kw in _DEFINICOES:
        reg.registrar(reg.MetricDefinition(**kw))


#: O nome CANÔNICO da população do funil — vocabulário do modelo de fatos, e
#: nunca o nome de uma rota (M1).
POPULACAO_DO_FUNIL = "quotes"


def _foi_lida(ctx: Contexto) -> bool:
    """A população do funil foi PERGUNTADA nesta consulta?

    🔴 Sem esta pergunta, uma lista vazia porque ninguém consultou é
    indistinguível de uma lista vazia porque não há cotação — e a frase que o
    dono lê ("o acervo está vazio") vira uma afirmação sobre a corretora que
    ninguém mediu.
    """
    return POPULACAO_DO_FUNIL in (
        getattr(getattr(ctx, "fatos", None), "populacoes_lidas", None) or set())


def _cotacoes(ctx: Contexto) -> List[Any]:
    """As cotações do período — **e as sem data entram**.

    🔴 SPEC-094.1, conserto de 04/09/2026. 📊 O defeito: a rota da etapa
    FINALIZADO não expõe a chave de data que as outras expõem, então todo
    negócio fechado nascia sem `created_at` e este filtro o descartava. A etapa
    que responde *"quantos eu fechei"* sumia do funil inteiro, em silêncio.

    ⚠️ Incluir o sem-data é correto porque **a janela da consulta já recortou a
    população**: a rota foi chamada com o período. O que não se pode é deixar o
    silêncio decidir — e por isso a fórmula conta quantos são e escreve.
    """
    saida = []
    for q in list(getattr(getattr(ctx, "fatos", None), "quotes", ()) or ()):
        quando = getattr(q, "created_at", None)
        if quando is None or ctx.inicio <= quando <= ctx.fim:
            saida.append(q)
    return saida


def _sem_data(cotacoes: List[Any]) -> int:
    return len([q for q in cotacoes if getattr(q, "created_at", None) is None])


def _funil(ctx: Contexto) -> Saida:
    if not _foi_lida(ctx):
        return None, None, [], [
            "a população do funil NÃO FOI LIDA nesta consulta: INDISPONÍVEL "
            "por rota não lida. 🔴 'Não perguntei' e 'perguntei e não veio "
            "nada' são afirmações diferentes, e só a segunda pode virar 'o "
            "acervo está vazio'"]
    cotacoes = _cotacoes(ctx)
    if not cotacoes:
        return None, None, [], [
            "as rotas do funil RESPONDERAM e o acervo está VAZIO no período: "
            "INDISPONÍVEL por acervo. 🔴 Isto NÃO é 'zero cotações' — é 'a "
            "corretora não registra cotação nesta fonte'"]
    por_etapa: Dict[str, Dict[str, Any]] = {}
    premio_conhecido = 0
    for q in cotacoes:
        etapa = str(getattr(q, "stage", "") or "").strip() or "(sem etapa)"
        balde = por_etapa.setdefault(etapa, {"rotulo": etapa, "cotacoes": 0,
                                             "premio_esperado": 0.0,
                                             "premio_conhecido": 0})
        balde["cotacoes"] += 1
        quantia = getattr(getattr(q, "expected_premium", None), "amount", None)
        if quantia is not None:
            balde["premio_esperado"] += float(quantia)
            balde["premio_conhecido"] += 1
            premio_conhecido += 1
    ordem = {e: i for i, e in enumerate(ETAPAS)}
    linhas = sorted(por_etapa.values(),
                    key=lambda x: (ordem.get(x["rotulo"], 99), x["rotulo"]))
    avisos = ["⛔ o motivo de perda NÃO acompanha estas contagens: a rota de "
              "leitura não o expõe (ver `quotes.lost_reasons@1`)"]
    orfas = _sem_data(cotacoes)
    if orfas:
        avisos.append(
            f"{orfas} negócio(s) sem data legível na fonte entram nas contagens "
            f"por etapa e ficam de fora de qualquer corte por data: a janela da "
            f"consulta já os recortou. 🔴 Descartá-los faria a etapa cujo "
            f"formato de linha não traz data SUMIR do funil, sem aviso")
    # 🔴 SPEC-094.1, conserto de 04/09/2026 (rodada 3) — A COBERTURA PASSA A
    # MEDIR O QUE O NÚMERO É.
    #
    # 📊 O defeito: `value` é uma CONTAGEM (`unit="count"`) e a cobertura
    # declarada era a fração das cotações com PRÊMIO legível. As duas coisas não
    # se falam: um funil com 100% das cotações lidas e nenhum prêmio exposto
    # saía com `coverage = 0.0` e confiança rebaixada, como se metade das
    # cotações tivesse sumido — e, no caminho oposto, `commercial.quotes` é
    # PARTIAL na fonte, então a ausência de cobertura calculável virava recusa
    # dura (M15) e derrubava o Pulso inteiro.
    #
    # ✅ A cobertura de uma CONTAGEM é a fração da população que a fonte
    # datou: são essas as linhas que qualquer corte por data consegue
    # reproduzir. A legibilidade do prêmio continua escrita — ela é sobre o
    # DINHEIRO do detalhamento, e vai num aviso, que é onde ela informa.
    com_data = len(cotacoes) - orfas
    if premio_conhecido < len(cotacoes):
        avisos.append(
            f"o prêmio esperado é legível em {premio_conhecido} de "
            f"{len(cotacoes)} cotação(ões): a COLUNA de dinheiro do "
            f"detalhamento é parcial, e as contagens por etapa não são. ⛔ "
            f"prêmio ilegível não entra como zero (M2)")
    return (float(len(cotacoes)),
            com_data / len(cotacoes),
            linhas, avisos)


_DEFINICOES.append(dict(
    metric_id="quotes.funnel", version=1,
    label="Cotações por etapa do funil", grain="stage", unit="count",
    time_basis=POLICY_VALID_FROM,
    required_capabilities=("commercial.quotes",),
    formula=_funil,
    coverage_rule="fração das cotações do período cuja DATA a fonte expôs — a "
                  "cobertura mede a mesma coisa que o número (uma contagem), e "
                  "não o dinheiro do detalhamento. 🔴 A legibilidade do prêmio "
                  "esperado é outra pergunta, e sai escrita no envelope",
    forbidden_fallback="⛔ acervo vazio nunca vira 'zero cotações': a primeira "
                       "frase é sobre a fonte e a segunda é sobre o negócio. "
                       "⛔ E rota NÃO LIDA nunca vira 'acervo vazio': ninguém "
                       "perguntou",
    pergunta_verificada="Quantas cotações estão em cada etapa do funil?",
    golden=golden(3.0),
))


# --------------------------------------------------------------------------
# quotes.lost_reasons — a métrica que NUNCA tem número, e diz por quê
# --------------------------------------------------------------------------
def _motivos(ctx: Contexto) -> Saida:
    """🔴 Ela devolve `None` SEMPRE, e não porque a população está vazia.

    ⚠️ Esta é a diferença que o produto inteiro existe para preservar: uma
    métrica que a fonte **não consegue** responder é diferente de uma que ela
    responde com nada. A primeira é uma dívida com endereço; a segunda é um
    fato sobre a corretora.

    ⛔ E ela não vira lista vazia. Uma lista vazia no Artifact vira a frase
    *"nenhum motivo de perda registrado"*, que é falsa: os motivos podem existir
    do lado de lá, e é a LEITURA que não existe.
    """
    cotacoes = _cotacoes(ctx)
    return None, None, [], [
        "motivo de perda INDISPONÍVEL por CAPACIDADE, e não por acervo: 📊 o "
        "campo não está entre as 30 chaves que a rota de leitura devolve — ele "
        "existe só no corpo da rota de ESCRITA, que esta SPEC não usa. "
        f"({len(cotacoes)} cotação(ões) no período, nenhuma com motivo legível)",
        "🔴 nunca escrever 'nenhum motivo registrado': os motivos podem existir "
        "na fonte, e o que falta é a leitura",
    ]


_DEFINICOES.append(dict(
    metric_id="quotes.lost_reasons", version=1,
    label="Motivos de perda das cotações", grain="reason", unit="count",
    time_basis=POLICY_VALID_FROM,
    required_capabilities=("commercial.quotes",),
    formula=_motivos,
    coverage_rule="não há cobertura a declarar: a leitura do motivo de perda "
                  "não existe na fonte medida",
    forbidden_fallback="⛔ NUNCA devolver lista vazia nem zero: 'nenhum motivo "
                       "registrado' é uma afirmação sobre a corretora, e a "
                       "verdade é uma afirmação sobre a fonte",
    premissa="📊 medido em 03/09/2026: `motivo_perda` não aparece no GET do "
             "funil. A métrica existe registrada para que a pergunta tenha "
             "resposta escrita, e não para produzir número",
    pergunta_verificada="Por que estamos perdendo as cotações?",
    golden=golden(INDISPONIVEL),
))
