# -*- coding: utf-8 -*-
"""A PROPOSTA de métrica — SPEC-094.1 · BLOCO D.

O corretor pede *"qual a comissão média por produtor só nas apólices de
frota?"*. Não existe. O que o produto faz com isso é a decisão inteira desta
peça, e ela foi tomada com número:

📊 `RELATORIOS-QUE-VALEM-DINHEIRO.md` §E — o estado da arte não deixa o LLM
criar métrica persistente em **nenhum** dos cinco sistemas medidos (dbt Semantic
Layer, Cube, Cortex Analyst, Genie, Looker): *"a saída do LLM é sempre um objeto
de consulta, nunca uma definição"*. O Cube **"deliberately exposes no commit
tool"**. Notas da pesquisa: propor → humano promove **92** · só registradas
**74** · criar na hora **18**.

📊 E o motivo do 18: BIRD mede o melhor sistema em 82,28% contra 92,96% do
humano — **1 resposta em 5 errada**. Pelo CLAUDE.md §9.5, a errada é a
silenciosa, e um número silenciosamente errado com o nome de uma métrica nova é
a pior coisa que este produto pode pôr na tela do dono.

## Por que é um TIPO PRÓPRIO, e não um `MetricResult` com `value=None`

🔴 Um `MetricResult` sabe carregar valor. Enquanto ele existir com esse campo,
alguém — uma fórmula nova, um `_compor` distraído, uma serialização — vai
preenchê-lo, e a proposta vira número na tela com cara de métrica registrada.
A `PropostaDeMetrica` **não tem onde guardar um número**. É a mesma escolha do
Cube: remover a capacidade, não pedir contenção (ref ①).

📊 Modelado também no Euno (ref ②): a proposta é revisada contra o catálogo
ANTES de existir, porque **duplicata é o modo de falha real** — três "comissão
do mês" divergentes destroem mais confiança que uma métrica faltando. Daí
`parecida_com`.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

__all__ = ["PropostaDeMetrica", "propor_a_partir_do_pedido", "parecidas",
           "PREFIXO_DA_PROPOSTA", "FRASE_DA_RECUSA", "TETO_DA_PERGUNTA"]

#: 🔴 Todo `nome_sugerido` começa por aqui. Não é enfeite: é o que impede a
#: proposta de ser confundida com um `metric_id` registrado quando ela viaja
#: solta num log, num evento ou numa mensagem — e é o que o guarda procura.
PREFIXO_DA_PROPOSTA = "proposta."

#: A frase que o chat diz. Ela vai FORA do bloco citável, sempre.
FRASE_DA_RECUSA = "não tenho essa métrica registrada"

#: 💭 Quanto do pedido do dono cabe no eco. Cento e vinte caracteres é uma
#: pergunta inteira; mais que isso é texto do modelo entrando no registro.
TETO_DA_PERGUNTA = 120

#: 💭 Acima disto duas perguntas falam da mesma coisa. Escolhido, não medido —
#: e ele viaja fora do número, em `parecida_com`, para que quem discorde do
#: corte veja a lista e decida por conta.
LIMIAR_DE_PARECENCA = 0.18

#: Quantas métricas parecidas entram na proposta. 💭 Três cabem numa frase.
TETO_DE_PARECIDAS = 3

#: 🔴 As palavras que NÃO distinguem nada. Sem esta lista, "quanto" e "por"
#: casariam todas as 16 métricas, e `parecida_com` apontaria o catálogo
#: inteiro — que é a mesma coisa que não apontar nada.
VAZIAS = frozenset("""
a o as os um uma de da do das dos e ou em no na nos nas por para com sem que
qual quais quanto quanta quantos quantas quando onde como me nos meu minha
meus minhas seu sua eu voce nosso nossa esse essa este esta isso ser esta
tem ter foi sao e mais menos so apenas todo toda todos todas ano mes periodo
""".split())

#: As famílias de fato do CBIM que um pedido pode nomear, e a palavra por que
#: o dono as chama. 🔴 A lista é FECHADA de propósito: uma proposta que
#: inventasse um fato novo a partir do texto do modelo estaria criando
#: vocabulário canônico por prompt (SPEC-053 §11.1 — *"prompt não é gate"*).
FATOS_CONHECIDOS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("PolicyFact", ("apolice", "apolices", "carteira", "emissao", "emitida",
                    "emitidas", "vigencia")),
    ("CommissionFact", ("comissao", "comissoes", "repasse", "remuneracao",
                        "corretagem")),
    ("PolicyFact.premium", ("premio", "premios", "faturamento", "receita")),
    ("ProducerAssignmentFact", ("produtor", "produtores", "vendedor",
                                "vendedores", "canal", "canais", "corretor")),
    ("RenewalFact", ("renovacao", "renovacoes", "vencimento", "vencimentos",
                     "vence", "vencem")),
)

#: As dimensões que o registry sabe recortar hoje. Mesma regra: lista fechada.
DIMENSOES_CONHECIDAS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("insurer", ("seguradora", "seguradoras", "cia", "companhia")),
    ("branch", ("ramo", "ramos", "produto", "produtos", "segmento",
                "segmentos", "frota", "frotas", "auto", "vida",
                "residencial")),
    ("producer", ("produtor", "produtores", "vendedor", "vendedores",
                  "canal", "canais")),
    ("month", ("mes", "meses", "mensal", "trimestre", "trimestral")),
)


# ==========================================================================
def normalizar(texto: str) -> str:
    """Minúsculas, sem acento, só letras e dígitos.

    🔴 Um só normalizador, e ele é usado nos DOIS lados da comparação. 📊
    CLAUDE.md §9.4: um padrão medido num dialeto e aplicado noutro é um padrão
    sobre outra coisa — e "comissão" contra "comissao" é exatamente isso.
    """
    cru = unicodedata.normalize("NFKD", str(texto or ""))
    sem_acento = "".join(c for c in cru if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", sem_acento.lower()).strip()


def palavras(texto: str) -> List[str]:
    """As palavras que DISTINGUEM alguma coisa, na ordem em que aparecem."""
    vistas: List[str] = []
    for p in normalizar(texto).split():
        if len(p) >= 3 and p not in VAZIAS and p not in vistas:
            vistas.append(p)
    return vistas


def _parecenca(pedido: Sequence[str], alvo: Sequence[str]) -> float:
    """Jaccard entre dois sacos de palavras. `0.0` quando um dos dois é vazio.

    ⚠️ Jaccard, e não "quantas do pedido aparecem": a segunda daria 1,0 para
    um pedido de UMA palavra contra a métrica de vinte, e `parecida_com`
    apontaria a métrica mais tagarela do catálogo em vez da mais parecida.
    """
    a, b = set(pedido), set(alvo)
    if not a or not b:
        return 0.0
    return len(a & b) / float(len(a | b))


def parecidas(pedido: str, metricas: Dict[str, Any],
              teto: int = TETO_DE_PARECIDAS) -> List[str]:
    """Os `metric_id` que respondem a uma pergunta parecida, do mais ao menos.

    🔴 A comparação é contra o **label** e a **pergunta_verificada**, e não
    contra o `metric_id`. É por isso que a `pergunta_verificada` virou campo
    obrigatório nesta SPEC: ninguém reconhece a própria pergunta em
    `mix.branch`, e um catálogo em que a duplicata não é reconhecível é um
    catálogo que vai ganhar três "comissão do mês" (ref ②).

    ⚠️ O `metric_id` entra na sacola mesmo assim — as palavras dele às vezes
    são as do dono ("renewal", "producer" não; "mix", "commission" às vezes) —
    mas nunca sozinho.
    """
    saco = palavras(pedido)
    if not saco:
        return []
    notas: List[Tuple[float, str]] = []
    for mid, d in (metricas or {}).items():
        alvo = palavras(" ".join((
            str(getattr(d, "label", "") or ""),
            str(getattr(d, "pergunta_verificada", "") or ""),
            str(mid).replace(".", " ").replace("_", " "))))
        nota = _parecenca(saco, alvo)
        if nota >= LIMIAR_DE_PARECENCA:
            notas.append((nota, str(mid)))
    notas.sort(key=lambda x: (-x[0], x[1]))
    return [mid for _, mid in notas[:teto]]


def _casar(saco: Sequence[str],
           vocabulario: Sequence[Tuple[str, Tuple[str, ...]]]) -> Tuple[str, ...]:
    """Os itens do vocabulário FECHADO que o pedido nomeia. Nunca inventa."""
    saida: List[str] = []
    for canonico, sinonimos in vocabulario:
        if any(p in sinonimos for p in saco) and canonico not in saida:
            saida.append(canonico)
    return tuple(saida)


def _slug(pedido: str) -> str:
    """O sufixo do `nome_sugerido`: até quatro palavras do pedido, com `_`."""
    partes = palavras(pedido)[:4]
    return "_".join(partes) if partes else "sem_nome"


# ==========================================================================
@dataclass(frozen=True)
class PropostaDeMetrica:
    """Uma métrica que **não existe** — descrita, nunca calculada.

    🔴 Repare no que não está aqui: `value`, `coverage`, `confidence`,
    `breakdown`. Não é esquecimento — é a peça inteira. Uma proposta com onde
    guardar um número acaba com um número guardado.
    """

    nome_sugerido: str
    fatos: Tuple[str, ...] = ()
    dimensoes: Tuple[str, ...] = ()
    time_basis: str = ""
    parecida_com: Tuple[str, ...] = ()
    pergunta_exemplo: str = ""
    #: O que o pedido tinha e o vocabulário fechado não reconheceu. Ele viaja
    #: para que o humano que promover a métrica saiba o que ainda falta
    #: decidir — e não para que alguém o transforme em fato canônico.
    nao_reconhecido: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not str(self.nome_sugerido or "").startswith(PREFIXO_DA_PROPOSTA):
            raise ValueError(
                "o nome sugerido de uma proposta começa por %r — sem isso ela "
                "se confunde com um metric_id registrado no primeiro log em "
                "que aparecer" % PREFIXO_DA_PROPOSTA)

    def serializar(self) -> Dict[str, Any]:
        """A forma JSON-able. ⛔ **Nenhuma chave de valor**, por construção.

        🔴 `origem` vai escrito em cada proposta, e não só na seção que as
        agrupa. Modelado no selo *Trusted* do Databricks Genie (ref ③): o selo
        viaja COM a resposta, porque é assim que ele sobrevive a alguém copiar
        uma linha da resposta para outro lugar.
        """
        return {
            "origem": "proposta",
            "nome_sugerido": self.nome_sugerido,
            "fatos": list(self.fatos),
            "dimensoes": list(self.dimensoes),
            "time_basis": self.time_basis,
            "parecida_com": list(self.parecida_com),
            "pergunta_exemplo": self.pergunta_exemplo,
            "nao_reconhecido": list(self.nao_reconhecido),
            "estado": "em revisão — nenhum número foi calculado",
        }

    def frase(self) -> str:
        """A recusa, em uma frase, para o modelo repassar. FORA do bloco."""
        duplicata = ""
        if self.parecida_com:
            duplicata = (" Já existe algo parecido: %s — confira antes de "
                         "registrar outra." % ", ".join(self.parecida_com))
        return ("⚠️ %s. Proponho `%s`%s. Nenhum número foi calculado, e nenhum "
                "será até um humano registrar a definição.%s" % (
                    FRASE_DA_RECUSA, self.nome_sugerido,
                    (" sobre %s" % ", ".join(self.fatos)) if self.fatos else "",
                    duplicata))


def propor_a_partir_do_pedido(pedido: str, metricas: Dict[str, Any],
                              time_basis_padrao: str = "") -> PropostaDeMetrica:
    """A proposta que nasce de um pedido que o catálogo não atende.

    🔴 O `pergunta_exemplo` é o eco do pedido **higienizado e cortado**, e não
    o texto do modelo verbatim.

    📊 Achado pelo red team na 094, em 03/09/2026, sobre `dimension`: texto
    livre que o LLM preenchia entrava **dentro** do bloco `<<PACK>>` — a única
    parte da resposta que o narrador foi instruído a tratar como verdade
    citável — e qualquer instrução escrita ali chegava com a autoridade do
    dado. A proposta viaja no MESMO bloco, então paga o mesmo pedágio:
    normalizada, sem pontuação, com teto de tamanho.

    ⚠️ O `time_basis` sai da métrica mais parecida quando há uma, e do padrão
    quando não há. Ele é uma SUGESTÃO — quem promove decide, e o protocolo do
    BLOCO E manda decidir explicitamente. Escolher a base temporal por conta
    seria escolher a população, que é a diferença entre 1.680 e 3.536 apólices.
    """
    saco = palavras(pedido)
    proximas = parecidas(pedido, metricas)
    base = time_basis_padrao
    if proximas:
        d = (metricas or {}).get(proximas[0])
        base = str(getattr(d, "time_basis", "") or "") or time_basis_padrao
    fatos = _casar(saco, FATOS_CONHECIDOS)
    dimensoes = _casar(saco, DIMENSOES_CONHECIDAS)
    reconhecidas = {p for _, sin in FATOS_CONHECIDOS for p in sin}
    reconhecidas |= {p for _, sin in DIMENSOES_CONHECIDAS for p in sin}
    return PropostaDeMetrica(
        nome_sugerido=PREFIXO_DA_PROPOSTA + _slug(pedido),
        fatos=fatos, dimensoes=dimensoes, time_basis=base,
        parecida_com=tuple(proximas),
        pergunta_exemplo=" ".join(normalizar(pedido).split())[:TETO_DA_PERGUNTA],
        nao_reconhecido=tuple(p for p in saco if p not in reconhecidas))
