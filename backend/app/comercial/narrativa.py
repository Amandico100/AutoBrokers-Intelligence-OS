# -*- coding: utf-8 -*-
"""A narrativa de um achado: título, por que importa, o que fazer, a pergunta.

SPEC-095 · BLOCO D.1. Peça **pura** — só `typing`. Não conhece Supabase, não
conhece InfoCap, não conhece LangChain e **não conhece LLM**.

## Por que ela existe

📊 SPEC-095 §1.4: o texto dos achados foi escrito para o MODELO e chega ao
corretor. `evidence_pack.py:684` diz *"há carteira vencendo na janela; o
detalhe por faixa de urgência está no envelope da métrica"* e `:712` diz *"um
produtor apropriou menos comissão que no período anterior, abaixo do limiar
declarado"* — **sem número e sem sujeito, de propósito**: o pack é o que vai ao
modelo, e ali o nome não pode estar. Certo para o modelo; inútil para o dono da
corretora, que abre o relatório e lê uma frase que não diz quanto, nem o que
fazer com aquilo.

Este módulo é a **outra** metade: a mesma comparação determinística, escrita
para GENTE. O achado continua nascendo de limiar escrito em `evidence_pack.py`;
aqui ele ganha quatro campos que um humano lê.

```
titulo            o achado com o NÚMERO dentro — é o que vira título da peça
por_que_importa   o limiar cruzado, dito como consequência de negócio
o_que_fazer       a próxima ação, no imperativo curto
pergunta          a frase que o chat abre já escrita ("Perguntar ao AutoBrokers")
```

## ⛔ As três regras que não se negociam

```
1. NENHUM LLM escreve nada aqui. Mesmo achado → mesmas quatro frases, sempre.
   Um "insight" gerado por modelo mudaria de rodada para rodada, e o dono leria
   duas verdades diferentes sobre a mesma semana (a mesma razão que fez os
   findings serem determinísticos na SPEC-094).
2. NENHUM nome de pessoa. `QUEDA_DE_PRODUTOR` carrega `producer_ref` — a
   referência opaca — e o título fala de "um produtor". O nome do produtor mora
   no Artifact do tenant, via `rotulos_de_produtor`, e em lugar nenhum daqui
   (SPEC-094 §2 · M16). Nome de SEGURADORA pode: é empresa, e é o sujeito do
   achado de concentração.
3. NENHUM número novo. Tudo o que aparece já veio calculado dentro do achado
   (`valor_pct`, `apolices`, `ja_vencidas`, `delta_pct`, `limiar_pct`). Este
   módulo FORMATA; ele não conta.
```

## O `periodo` é um parâmetro, e ele desce de quem MONTA o pack

`achar_findings` recebe métricas, e o rótulo humano do período ("2026",
"próximos 90 dias") é do `Periodo` de `calculos.py` — quem o conhece é quem
monta o pack. Por isso ele desce como parâmetro, com padrão vazio:

```
narrar(achado)                    -> "…% da comissão do período"
narrar(achado, periodo="2026")    -> "…% da comissão de 2026"
```

🔴 E o título é **gravado UMA vez**, dentro do achado, por `finding()`. Quem
desenha a peça LÊ o campo (`campos()`), e não renarra: duas chamadas ao playbook
com parâmetros diferentes dariam dois títulos para o mesmo achado — um no card
da lista e outro na capa —, e nenhum leitor teria como saber qual é o certo.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, Optional

# --------------------------------------------------------------------------
# Os kinds. 🔴 As MESMAS constantes de `evidence_pack.py`, repetidas como
# literal de propósito: importar de lá criaria um ciclo (o `evidence_pack`
# importa ESTE módulo para preencher os quatro campos em `finding()`), e um
# ciclo entre duas peças puras é um preço alto por quatro strings.
# O guarda [D1] confere que os dois lados falam dos mesmos kinds.
# --------------------------------------------------------------------------
QUEDA_DE_PRODUTOR = "producer_drop"
CONCENTRACAO = "concentration"
EXPOSICAO_DE_RENOVACAO = "renewal_exposure"
COBERTURA_BAIXA = "low_coverage"

#: Os quatro campos que todo playbook devolve. Lista fechada: quem acrescentar
#: um quinto tem de acrescentá-lo em todos, e o guarda [D1] cobra.
CAMPOS = ("titulo", "por_que_importa", "o_que_fazer", "pergunta")


# --------------------------------------------------------------------------
# Formatação — vírgula decimal, e nada de arredondar para outro número
# --------------------------------------------------------------------------
def _numero(valor: Any) -> Optional[float]:
    """O valor como float, ou `None`. `bool` não é número aqui."""
    if isinstance(valor, bool) or valor is None:
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def pct(valor: Any, casas: int = 1) -> str:
    """`46.8` → `"46,8%"`. Vazio quando não há número.

    🔴 Vírgula, e não ponto. 📊 O resto da peça já escreve assim
    (`executive_intelligence.py:_reais` e `frase_da_cobertura`); um título com
    `46.8%` no meio de cartões com `46,8%` denuncia que o título veio de outro
    lugar — e neste caso ele veio mesmo, mas de outro lugar NOSSO.
    """
    n = _numero(valor)
    if n is None:
        return ""
    return ("%.*f%%" % (casas, n)).replace(".", ",")


def inteiro(valor: Any) -> str:
    """`61.0` → `"61"`. Vazio quando não há número."""
    n = _numero(valor)
    if n is None:
        return ""
    return "%d" % int(round(n))


def _do_periodo(periodo: str = "") -> str:
    """`"de 2026"` ou `"do período"` — nunca um rótulo inventado."""
    rotulo = " ".join(str(periodo or "").split())
    return ("de %s" % rotulo) if rotulo else "do período"


# --------------------------------------------------------------------------
# Os playbooks. Um por kind. 💭 As frases são escolhidas, não medidas.
# --------------------------------------------------------------------------
def _concentracao(achado: Mapping[str, Any], periodo: str) -> Dict[str, str]:
    """Uma seguradora responde por fatia grande demais da comissão.

    ⚠️ `subject_id` aqui é o rótulo da SEGURADORA (`mix.breakdown[0].rotulo`).
    É empresa, não pessoa: pode aparecer no título, no sinal e no pack.
    """
    seguradora = " ".join(str(achado.get("subject_id") or "").split())
    fatia = pct(achado.get("valor_pct"))
    limiar = pct(achado.get("limiar_pct"), 0)
    quem = seguradora or "A maior seguradora"

    titulo = ("%s concentra %s da comissão %s" % (quem, fatia, _do_periodo(periodo))
              if fatia else
              "%s concentra a maior fatia da comissão %s" % (quem, _do_periodo(periodo)))
    return {
        "titulo": titulo,
        "por_que_importa": (
            "Acima de %s, um reajuste ou uma mudança de política dessa "
            "seguradora mexe em quase metade da receita da corretora."
            % (limiar or "o limiar declarado")),
        "o_que_fazer": (
            "Distribuir as próximas renovações entre outras seguradoras e "
            "comparar a sinistralidade dela com a do mercado antes do próximo "
            "reajuste."),
        "pergunta": ("como está a %s contra o mercado?" % seguradora
                     if seguradora else
                     "como está a maior seguradora da carteira contra o mercado?"),
    }


def _exposicao_de_renovacao(achado: Mapping[str, Any], periodo: str) -> Dict[str, str]:
    """Carteira vencendo na janela — e quanto dela já venceu."""
    quantas = inteiro(achado.get("apolices"))
    vencidas = inteiro(achado.get("ja_vencidas"))
    ja = _numero(achado.get("ja_vencidas")) or 0.0

    titulo = "%s apólices vencem na janela" % (quantas or "Há apólices que")
    if not quantas:
        titulo = "Há carteira vencendo na janela"
    if ja > 0:
        titulo = "%s · %s já vencidas" % (titulo, vencidas)

    fazer = ("Começar pelas %s que já venceram — renovação atrasada é a que o "
             "concorrente encontra primeiro." % vencidas) if ja > 0 else (
        "Distribuir a janela entre os produtores antes que ela encoste no "
        "vencimento.")
    return {
        "titulo": titulo,
        "por_que_importa": (
            "Renovação não trabalhada é comissão que some no mês seguinte, e "
            "some sem aparecer em lugar nenhum: a apólice simplesmente não "
            "volta."),
        "o_que_fazer": fazer,
        "pergunta": ("quais apólices já venceram e não renovaram?" if ja > 0
                     else "quais apólices vencem primeiro nesta janela?"),
    }


def _queda_de_produtor(achado: Mapping[str, Any], periodo: str) -> Dict[str, str]:
    """Um produtor apropriou menos que no período anterior.

    ⛔ **Sem nome, e sem a referência opaca.** O achado carrega `producer_ref`
    (`p7baf5d5aadb1`) porque o pack precisa dele para casar os dois períodos;
    o título fala de "um produtor" e ponto. Quem é ele aparece na tabela
    "Quem apropriou comissão no período", dentro do Artifact do tenant, onde o
    nome pode estar (SPEC-094.1 · `rotulos_de_produtor`).
    """
    delta = _numero(achado.get("delta_pct"))
    queda = pct(abs(delta)) if delta is not None else ""
    return {
        "titulo": ("Um produtor apropriou %s menos que no período anterior" % queda
                   if queda else
                   "Um produtor apropriou menos comissão que no período anterior"),
        "por_que_importa": (
            "Queda dessa ordem contra o mesmo período anterior costuma ser "
            "carteira parada ou pessoa desengajada — e as duas causas se "
            "resolvem antes do fechamento, não depois."),
        "o_que_fazer": (
            "Conversar com o produtor antes do fechamento do período e olhar a "
            "carteira dele apólice a apólice."),
        "pergunta": "como está cada produtor este período?",
    }


def _cobertura_baixa(achado: Mapping[str, Any], periodo: str) -> Dict[str, str]:
    """Uma ou mais métricas cobrem menos que o limiar.

    ⛔ Este achado **não vira sinal** (não está em `FINDINGS_QUE_VIRAM_SINAL`) e
    **não entra em "O que importa agora"**: ele é fato sobre a FONTE, não sobre
    o negócio. O lugar dele é a linha "O que não deu para medir neste período"
    (SPEC-095 D.2). Ele tem os quatro campos assim mesmo, porque quem lê a
    linha ainda precisa saber por que ela está lá e o que fazer a respeito.
    """
    metricas = list(achado.get("metricas") or [])
    quantas = len(metricas)
    limiar = _numero(achado.get("limiar"))
    corte = pct(100.0 * limiar, 0) if limiar is not None else ""

    coberturas = [c for c in (_numero(m.get("coverage")) for m in metricas
                              if isinstance(m, Mapping)) if c is not None]
    menor = pct(100.0 * min(coberturas)) if coberturas else ""

    alvo = "%d métrica(s)" % quantas if quantas else "Uma ou mais métricas"
    titulo = ("%s cobrem menos de %s da carteira" % (alvo, corte) if corte
              else "%s cobrem parte da carteira" % alvo)
    if menor:
        titulo = "%s (a menor cobre %s)" % (titulo, menor)
    return {
        "titulo": titulo,
        "por_que_importa": (
            "O número existe e está certo — mas é sobre a fatia da carteira "
            "que a fonte conseguiu identificar, e não sobre a carteira "
            "inteira. Somar como se fosse tudo superestimaria o que falta."),
        "o_que_fazer": (
            "Ler esses números sobre a fatia declarada ao lado de cada um, e "
            "completar o cadastro de produtor na fonte para a próxima leitura."),
        "pergunta": "quais números do relatório cobrem menos que a carteira toda?",
    }


#: 🔴 O playbook por kind. O guarda [D1] exige que TODO kind de
#: `FINDINGS_QUE_VIRAM_SINAL` tenha entrada aqui — kind sem playbook é achado
#: que chega ao dono como frase de máquina, que é o defeito que a §1.4 mediu.
PLAYBOOKS: Dict[str, Callable[[Mapping[str, Any], str], Dict[str, str]]] = {
    CONCENTRACAO: _concentracao,
    EXPOSICAO_DE_RENOVACAO: _exposicao_de_renovacao,
    QUEDA_DE_PRODUTOR: _queda_de_produtor,
    COBERTURA_BAIXA: _cobertura_baixa,
}


# --------------------------------------------------------------------------
def narrar(achado: Mapping[str, Any], periodo: str = "") -> Dict[str, str]:
    """Os quatro campos humanos de UM achado. Determinístico, sem LLM.

    Kind desconhecido devolve os quatro campos preenchidos com o `summary` que
    o achado já carrega — e nunca um dicionário vazio nem uma exceção. 🔴 A
    razão é a mesma do `NARRATIVA_PADRAO` do Fabric: um achado novo que
    chegasse aqui antes do playbook dele sumiria da peça em silêncio, e sumir
    em silêncio é pior que aparecer com a frase de máquina.
    """
    kind = str(achado.get("kind") or "")
    playbook = PLAYBOOKS.get(kind)
    if playbook is not None:
        return playbook(achado, periodo)

    resumo = " ".join(str(achado.get("summary") or "").split())
    return {
        "titulo": resumo or "Ponto de atenção no período",
        "por_que_importa": resumo or "Apareceu no período e ainda não foi tratado.",
        "o_que_fazer": "Abrir o relatório e olhar os números desta seção.",
        "pergunta": "o que este ponto de atenção quer dizer?",
    }


def campos(achado: Mapping[str, Any], periodo: str = "") -> Dict[str, str]:
    """Os quatro campos humanos do achado: os que ele JÁ carrega, ou o playbook.

    🔴 Esta é a função que quem DESENHA usa. `finding()` gravou os quatro campos
    no ato da criação, com o rótulo do período que o pack conhecia; ler o que
    está lá é o que garante que a capa da peça, o card da lista e o sinal digam
    a MESMA frase.

    O playbook só roda quando o achado chega sem eles — um dicionário montado à
    mão, uma fixture, um pack antigo. Nesse caso a frase sai igual, porque a
    função é a mesma; o que não sai é uma frase inventada nem um campo vazio.
    """
    prontos = {c: " ".join(str(achado.get(c) or "").split()) for c in CAMPOS}
    if all(prontos.values()):
        return prontos
    return narrar(achado, periodo)


def numero_curto(achado: Mapping[str, Any]) -> str:
    """O número do achado em uma expressão curta — o `impact` do bloco `actions`.

    Vazio quando o achado não carrega número. ⚠️ Vazio é vazio: um `impact`
    com `"0"` faria o cartão afirmar zero, que é a troca que a SPEC-094 existe
    para impedir.
    """
    kind = str(achado.get("kind") or "")
    if kind == CONCENTRACAO:
        return pct(achado.get("valor_pct"))
    if kind == EXPOSICAO_DE_RENOVACAO:
        quantas = inteiro(achado.get("apolices"))
        return ("%s apólices" % quantas) if quantas else ""
    if kind == QUEDA_DE_PRODUTOR:
        delta = _numero(achado.get("delta_pct"))
        return ("−%s" % pct(abs(delta))) if delta is not None else ""
    if kind == COBERTURA_BAIXA:
        metricas = list(achado.get("metricas") or [])
        return ("%d métrica(s)" % len(metricas)) if metricas else ""
    return ""
