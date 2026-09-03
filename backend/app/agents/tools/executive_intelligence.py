# -*- coding: utf-8 -*-
"""O Pulso 360 — uma tool de DOMÍNIO, não uma tool por relatório.

SPEC-094 · BLOCO F. O dono da corretora escreve *"como estamos?"* e recebe um
veredito executivo cujo **cada número aponta para a métrica que o produziu**.

## A inversão, e por que ela é diferente da 081

> **O modelo escolhe O QUE. O registry CALCULA.**

A SPEC-081 entregou duas tools, uma por relatório: Raio-X e Radar. Cada
pergunta nova pediria uma tool nova, e cada tool nova reimplementaria a
composição. Esta recebe um **query plan** — `period`, `compare`, `views[]`,
`dimension?` — e o plano é a única coisa que o LLM preenche. Busca, tradução,
cálculo, achado, composição e publicação são código determinístico: a mesma
pergunta duas vezes produz o mesmo número, com o mesmo `pack_id`.

⛔ E **nenhuma chamada nova de modelo**. Quem narra é o grafo, que já narra
hoje, e ele narra sobre o bloco `<<PACK … PACK>>` — blocos citáveis, no espírito
das *citations* (SPEC-094 §3 ref ⑥). Um narrador próprio seria a terceira
chamada de LLM do turno, e a §1.9 orçou duas.

## O que esta tool NÃO conhece

```
⛔ não sabe o nome de nenhum sistema de gestão   quem sabe é o adapter (BLOCO B)
⛔ não tem fórmula                               quem tem é o registry (BLOCO D)
⛔ não decide o que é capacidade                 quem decide é o manifesto (C)
⛔ não escreve nome de pessoa em lugar nenhum    o rótulo mora no Artifact
```

📊 Por isso o grep do juiz (`infocap|nosnum|val_c|inivig|fimvig|codfil` sobre o
CÓDIGO deste arquivo) tem de dar **zero**: se a tool falasse o dialeto de uma
fonte, trocar de fonte voltaria a significar reescrever o produto — que é a
dívida que a SPEC-094 existe para pagar.

## O follow-up, e por que ele não refaz a consulta

📊 A leitura de um ano custa entre 3,3 s e 15 s por rota (censo do BLOCO 0). A
segunda pergunta da mesma conversa — *"e só a maior seguradora?"* — não pode
pagar aquilo de novo, e não pode responder com **outros números**: refazer a
leitura entre duas perguntas da mesma conversa produziria dois totais
diferentes para o mesmo ano, e nenhum dos dois estaria errado.

Então o pack fica em memória, por processo, com a chave carregando o
`company_id` — e o follow-up filtra a dimensão sobre o pack que já existe.

## O mapa de produtor, e por que `unknown` é a resposta certa

📊 A fonte devolve um rótulo de papel (`EXECUTIVO`, `FECHADOR`) que descreve
função comercial, e **não** vínculo. Chamar de "funcionário" quem a fonte
chamou de EXECUTIVO é uma afirmação trabalhista inventada pelo software, sobre
uma pessoa, num documento que circula. O papel vem de arquivo versionado,
curado por gente; sem entrada no arquivo, o papel é `unknown` e o Artifact
escreve "papel não mapeado". O rótulo da fonte vai para `role_source`, que é
onde ele pode estar: como procedência, nunca como veredito.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

TEMPLATE_PULSE = "executive.pulse360"

# ==========================================================================
# O QUERY PLAN — o modelo escolhe O QUE, e nada além disso
# ==========================================================================
#
# 🔴 Cada visão é uma lista FECHADA de `metric_id`. O modelo não escolhe
# métrica: ele escolhe assunto. Deixá-lo nomear métricas transformaria a
# taxonomia do registry em superfície de prompt — e uma métrica inventada
# viraria `KeyError` na frente do dono, ou pior, um número parecido.
VISOES: Dict[str, Tuple[str, ...]] = {
    "producao": ("production.policy_count", "production.premium_written",
                 "commission.broker_accrued", "production.new_vs_renewal"),
    "pessoas": ("producer.performance", "data.coverage",
                "repasse.producer_accrued", "contribution.after_repasse"),
    "mix": ("mix.insurer", "mix.branch"),
    "renovacao": ("renewal.exposure",),
    "projecao": ("projection.run_rate", "producer.momentum"),
    "caixa": ("commission.broker_received",),
}

#: "Como estamos?" sem mais nada: TODAS as visões. 🔴 A pergunta genérica é a
#: mais comum e a que menos tolera resposta parcial — um panorama que
#: silenciasse a exposição de renovação seria um panorama que esconde trabalho.
VISOES_PADRAO: Tuple[str, ...] = tuple(VISOES)

#: As visões que só fazem sentido sobre o que TERMINA na janela. O registry
#: recusa comparar bases temporais diferentes (M6); aqui a gente nem pede.
COMPARAVEIS = ("producao", "pessoas", "mix", "projecao")


class PlanoDeConsulta(BaseModel):
    """O que o modelo preenche. Quatro campos, e nenhum deles é uma fórmula."""

    period: str = Field(
        default="",
        description=(
            "O período que o dono pediu, COMO ELE FALOU: '2025', 'este ano', "
            "'ano passado', 'últimos 12 meses', 'primeiro semestre', 'agosto', "
            "'de 01/03/2026 a 30/06/2026'. Se ele não disse, mande string "
            "vazia — o padrão é o ano até hoje e a peça avisa qual período "
            "usou. NUNCA pergunte o período de volta."),
    )
    compare: str = Field(
        default="",
        description=(
            "Contra o que comparar, como ele falou. Vazio = o MESMO período do "
            "ano anterior, que é o que 'como estamos?' quer dizer. Use "
            "'nenhum' quando ele pedir só o período, sem comparação."),
    )
    views: List[str] = Field(
        default_factory=list,
        description=(
            "Os assuntos que ele quer, entre: producao, pessoas, mix, "
            "renovacao, projecao, caixa. Vazio = todos, que é o certo para "
            "'como estamos?'. Peça só o assunto citado quando ele for "
            "específico ('quanto vence?' -> ['renovacao'])."),
    )
    dimension: str = Field(
        default="",
        description=(
            "Um recorte para a resposta, quando ele nomear um: a seguradora ou "
            "o ramo ('e só a maior seguradora?'). Vazio = a carteira inteira."),
    )
    pack_id: str = Field(
        default="",
        description=(
            "SÓ em pergunta de acompanhamento: o `pack_id` que veio no bloco "
            "PACK da resposta anterior desta MESMA conversa. Com ele a "
            "resposta sai do pacote que já existe, sem consultar de novo — e "
            "os números continuam sendo os mesmos. Vazio na primeira "
            "pergunta."),
    )


# ==========================================================================
# O MAPA DE PRODUTOR — e o `unknown` que não se arredonda
# ==========================================================================
PAPEIS = ("employee", "partner", "indicator", "channel", "unknown")
PAPEL_PADRAO = "unknown"
FRASE_SEM_MAPA = "papel não mapeado"

_CACHE_DE_PAPEIS: Dict[str, Dict[str, str]] = {}


def _arquivo_de_papeis(slug: str) -> str:
    """O caminho do mapa versionado desta corretora.

    🔴 A pasta é a do censo do provider, e ela é composta a partir da constante
    do CBIM — o nome do sistema de gestão não é escrito aqui. 📊 A única coluna
    `jsonb` de `companies` é `acionamento_profile`, que é outra coisa; guardar
    o mapa em banco exigiria migration de estrutura, e a §7 desta SPEC tem uma
    migration só, de seed.
    """
    from app.comercial import cbim
    from app.comercial import manifesto

    return os.path.join(manifesto.DIRETORIO_DO_CENSO, cbim.PROVIDER_PILOTO,
                        "producer-roles.%s.json" % (slug or "").strip().lower())


def mapa_de_papeis(slug: str) -> Dict[str, str]:
    """`{rótulo do produtor: actor_type}` — do arquivo versionado, ou vazio."""
    chave = (slug or "").strip().lower()
    if chave in _CACHE_DE_PAPEIS:
        return _CACHE_DE_PAPEIS[chave]
    mapa: Dict[str, str] = {}
    caminho = _arquivo_de_papeis(chave)
    try:
        with open(caminho, encoding="utf-8") as fh:
            bruto = json.load(fh)
        for item in (bruto.get("producers") or []):
            rotulo = str(item.get("label") or "").strip().lower()
            papel = str(item.get("actor_type") or "").strip().lower()
            if rotulo and papel in PAPEIS:
                mapa[rotulo] = papel
    except FileNotFoundError:
        pass
    except Exception as exc:  # noqa: BLE001
        # ⚠️ Mapa ilegível NÃO derruba o relatório e NÃO vira `employee`:
        # vira ausência de mapa, que é a verdade.
        logger.warning("[094] mapa de papeis ilegivel (%s)", type(exc).__name__)
    _CACHE_DE_PAPEIS[chave] = mapa
    return mapa


def actor_type_de(company: str = "", rotulo: str = "",
                  role_source: str = "") -> str:
    """O papel de um produtor. **`unknown` quando não há mapa.**

    🔴 `role_source` é o rótulo que a fonte devolveu. Ele entra como
    procedência e **nunca** decide o papel: a fonte descreve função comercial,
    e função comercial não é vínculo. Um software que promove `EXECUTIVO` a
    `employee` está afirmando uma relação trabalhista que ninguém declarou,
    sobre uma pessoa, num documento que circula.

    ⚠️ `company` aceita o slug da corretora ou o identificador dela — o mapa é
    procurado pelo slug, e uma corretora sem arquivo devolve `unknown` para
    todo mundo, que é a resposta honesta.
    """
    mapa = mapa_de_papeis(company)
    papel = mapa.get((rotulo or "").strip().lower(), PAPEL_PADRAO)
    return papel if papel in PAPEIS else PAPEL_PADRAO


def esquecer_papeis() -> None:
    """Solta o cache do mapa. Existe para teste, e para o arquivo recarregar."""
    _CACHE_DE_PAPEIS.clear()


# ==========================================================================
# O CACHE DO PACK — o follow-up não refaz a leitura
# ==========================================================================
#
# 🔴 A chave carrega o `company_id`. Um cache de carteira indexado só pelo
# identificador do pacote serviria o pacote de uma corretora a outra no mesmo
# processo — cross-tenant silencioso, com número certo (CLAUDE.md §7).
_CACHE_DE_PACOTES: Dict[str, Dict[str, Any]] = {}
#: 💭 Doze pacotes por processo. O follow-up acontece na mesma conversa; o que
#: passa disso é histórico, e histórico se lê no Artifact.
TETO_DE_PACOTES = 12

#: 🔴 Quinze minutos, e o relógio não é decoração.
#:
#: 📊 Achado pelo red team em 03/09/2026: o pacote ficava em memória até o teto
#: de doze o empurrar para fora. Uma conversa retomada duas horas depois com o
#: mesmo `pack_id` recebia os números de duas horas atrás — apresentados como
#: os de agora, com o `freshness` verdadeiro escondido dentro do JSON e a frase
#: determinística sem nenhuma menção à hora. 💭 Quinze minutos é o que dura uma
#: conversa; o que passa disso se relê, e reler custa uma leitura de carteira.
TTL_DO_PACOTE_S = 15 * 60


def chave_do_pack(company_id: str, pack_id: str) -> str:
    return "%s|%s" % (str(company_id or ""), str(pack_id or ""))


def guardar_pack(company_id: str, pacote: Any, link: str) -> None:
    from time import monotonic

    if len(_CACHE_DE_PACOTES) >= TETO_DE_PACOTES:
        _CACHE_DE_PACOTES.pop(next(iter(_CACHE_DE_PACOTES)), None)
    _CACHE_DE_PACOTES[chave_do_pack(company_id, pacote.pack_id)] = {
        "pacote": pacote, "link": link, "guardado_em": monotonic()}


def buscar_pack(company_id: str, pack_id: str) -> Optional[Dict[str, Any]]:
    """O pacote guardado, ou `None` — inclusive quando ele **venceu**.

    ⚠️ `monotonic()`, e não `time()`: o relógio de parede pode andar para trás
    (NTP, fuso), e um TTL que anda para trás nunca vence.
    """
    from time import monotonic

    chave = chave_do_pack(company_id, pack_id)
    guardado = _CACHE_DE_PACOTES.get(chave)
    if guardado is None:
        return None
    if monotonic() - float(guardado.get("guardado_em") or 0.0) > TTL_DO_PACOTE_S:
        _CACHE_DE_PACOTES.pop(chave, None)
        return None
    return guardado


def esquecer_pacotes() -> None:
    _CACHE_DE_PACOTES.clear()


# ==========================================================================
# O PERÍODO — e o que "como estamos?" quer dizer
# ==========================================================================
def _um_ano_atras(quando: date) -> date:
    """A mesma data no ano anterior. 29/02 vira 28/02, e não 01/03."""
    try:
        return quando.replace(year=quando.year - 1)
    except ValueError:
        return quando.replace(year=quando.year - 1, day=28)


class RecusaDePeriodo(ValueError):
    """A janela pedida não é uma janela. 🔴 `Recusa…` de propósito.

    `_erro_legivel` classifica pelo PREFIXO do nome da classe, e uma recusa
    conhecida chega ao modelo com o MOTIVO escrito — em vez de virar o nome
    genérico de uma exceção que ninguém consegue explicar ao dono.
    """


#: 🔴 O teto da janela. 💭 Dois anos, e o motivo é de custo medido, não de gosto:
#: 📊 uma leitura de UM ano custa 3,9 s em `/documentos_bi` e 11,4 s em
#: `/renovacoes` (censo de 03/09/2026), e a janela de vencimento é sempre quatro
#: anos civis mais larga que a de produção. Uma pergunta de dez anos pagaria
#: mais de dez leituras e provavelmente morreria no meio — e o dono veria
#: "RELATORIO_FALHOU" sem entender que ele pediu demais.
TETO_DA_JANELA_DIAS = 366 * 2


def _conferir_periodo(p: Any, comofalado: str) -> Any:
    """A janela é uma janela? Senão, **recusa** — e nunca conserta em silêncio.

    📊 Achado pelo red team em 03/09/2026: `period` é texto livre que o modelo
    preenche a partir da frase do dono. Duas formas passavam:

    ```
    invertida   fim < início: o motor devolvia população VAZIA, e a resposta
                era "não há movimento registrado" — que é uma afirmação sobre a
                CARTEIRA, feita por causa de uma data trocada
    absurda     "de 2010 a 2030": vinte anos de leitura, quatro rotas por ano
    ```

    🔴 Inverter a janela em silêncio seria pior que as duas: quem pediu
    *"de dezembro a janeiro"* provavelmente quer o virar do ano, e adivinhar
    qual dos dois ele quis dizer é escolher pelo dono.
    """
    inicio, fim = p.inicio, p.fim
    if fim < inicio:
        raise RecusaDePeriodo(
            "o período pedido termina antes de começar (%s a %s, lido de %r). "
            "Não dá para adivinhar qual das duas datas está trocada, e inverter "
            "por conta própria seria decidir pelo dono: peça o período de novo, "
            "com as duas datas." % (inicio, fim, comofalado[:60]))
    if (fim - inicio).days + 1 > TETO_DA_JANELA_DIAS:
        raise RecusaDePeriodo(
            "o período pedido tem %d dias (%s a %s) e o teto desta peça é de "
            "%d. Uma janela desse tamanho custa mais de uma dezena de leituras "
            "da carteira e costuma não completar. Peça em pedaços de até dois "
            "anos." % ((fim - inicio).days + 1, inicio, fim, TETO_DA_JANELA_DIAS))
    return p


def periodo_e_comparacao(calc: Any, texto: str, texto_da_comparacao: str = ""):
    """`(período, comparação ou None)`.

    🔴 O padrão de *"como estamos?"* é **ano até hoje × mesmo período do ano
    anterior** — e não os 365 dias imediatamente anteriores. 📊 A produção é
    sazonal: comparar janeiro-a-setembro com abril-a-dezembro do ano passado
    mede a estação, não o negócio. `Periodo.anterior()` da 081 devolve a janela
    imediatamente anterior, que serve ao Raio-X e não serve aqui.
    """
    p = _conferir_periodo(calc.entender_periodo(texto or ""), texto or "")
    pedido = (texto_da_comparacao or "").strip().lower()
    if pedido in ("nenhum", "nenhuma", "nao", "não", "sem"):
        return p, None
    if pedido:
        return p, _conferir_periodo(
            calc.entender_periodo(texto_da_comparacao), texto_da_comparacao)
    inicio = _um_ano_atras(p.inicio)
    fim = _um_ano_atras(p.fim)
    return p, calc.Periodo(inicio, fim, "%s (mesmo período)" % inicio.year)


# ==========================================================================
# A TOOL
# ==========================================================================
CARIMBO_PRONTO = "RELATORIO_PRONTO"
CARIMBO_VAZIO = "RELATORIO_VAZIO"

#: 🔴 A frase determinística. Ela **não carrega número**: o número está no
#: bloco, com `metric_id@versão` ao lado. Foi assim que a §1.8 desta SPEC
#: descreveu o defeito de origem — o número virava prosa antes de chegar ao
#: modelo, e o modelo parafraseava o que ninguém conseguia conferir depois.
RESUMO_DETERMINISTICO = (
    "O veredito, a comparação com o período anterior, a cobertura de cada "
    "número e o que a fonte não expõe estão no bloco PACK acima e no "
    "relatório, cada um com a métrica que o produziu ao lado."
)


def resumo_deterministico(pacote: Any, reusado: bool = False) -> str:
    """O resumo, com a HORA da leitura na frente do modelo.

    🔴 `freshness` existia dentro do JSON e nunca aparecia na frase. 📊 Achado
    pelo red team em 03/09/2026: num follow-up, o dono lia números de uma
    leitura antiga sem nada dizer que eram antigos — e a peça só dizia "mesmo
    pacote", que soa como uma garantia de consistência e não como um aviso de
    idade.
    """
    quando = str(getattr(pacote, "freshness", "") or "").strip()
    origem = ("Estes números são os da leitura de %s, reaproveitada sem nova "
              "consulta — diga a hora ao dono se ele perguntar se está "
              "atualizado." % quando) if reusado else (
        "Carteira lida em %s." % quando)
    return RESUMO_DETERMINISTICO + " " + origem

#: 🔴 De QUE a cobertura é fração, métrica por métrica, na língua do dono.
#:
#: ⚠️ "6,0%" sozinho não informa: 6% de quê? A `coverage_rule` do registry diz
#: isso para quem lê código; estas frases dizem para quem lê o relatório. As
#: duas descrevem a MESMA fração — quem mudar uma tem de mudar a outra, e é por
#: isso que o `metric_id` está escrito nos dois lugares.
DO_QUE_E_A_COBERTURA = {
    "producer.performance": "da comissão do período (o resto não tem produtor "
                            "identificado na fonte)",
    "data.coverage": "das apólices do período",
    "repasse.producer_accrued": "das apólices que VENCEM na janela — não das "
                                "emitidas nela",
    "contribution.after_repasse": "da comissão do período que tem repasse "
                                  "conhecido; a conta só existe sobre a "
                                  "INTERSEÇÃO das duas populações",
    "production.premium_written": "das apólices do período cujo prêmio a fonte "
                                  "expôs",
    "commission.broker_accrued": "das apólices do período com comissão legível",
    "mix.insurer": "das apólices do período com comissão legível",
    "mix.branch": "das apólices do período com comissão legível",
    "renewal.exposure": "dos vencimentos da janela com prêmio legível",
    "projection.run_rate": "das apólices do período com comissão legível",
    "producer.momentum": "das apólices do período com comissão legível",
    "production.new_vs_renewal": "das apólices do período com comissão legível",
}

COMO_FALAR = (
    "Comente para o dono usando SÓ os números do bloco PACK acima, citando "
    "`metric_id@version` ao lado de cada número que você disser. `UNAVAILABLE` "
    "quer dizer INDISPONÍVEL na fonte — diga isso com essas letras, e nunca "
    "zero. Comissão apropriada é o que foi ganho na emissão, e não o que "
    "entrou em caixa: não troque uma coisa pela outra. Não invente número que "
    "não esteja no bloco, e não cite nome de produtor: ele está no relatório, "
    "que é o lugar dele."
)


class ExecutiveIntelligenceTool(BaseTool):
    """O Pulso 360 da corretora, num pedido só."""

    exige_async: ClassVar[bool] = True

    name: str = "executive_intelligence"
    description: str = (
        "PANORAMA EXECUTIVO da corretora, com os dados reais da carteira dela: "
        "produção, prêmio, comissão apropriada, produtores e canais, "
        "concentração por seguradora e por ramo, exposição de renovação e "
        "projeção no ritmo atual — comparados com o período anterior, cada "
        "número com a métrica que o produziu e com a cobertura declarada. "
        "Devolve o LINK de um relatório visual pronto. "
        "Use quando o dono perguntar: como estamos, como foi o ano, panorama, "
        "resultado da corretora, visão executiva, estamos crescendo, como está "
        "a carteira, quanto vencemos, onde estamos concentrados. "
        "IMPORTANTE: antes de chamar, diga UMA frase curta avisando que vai "
        "levantar os dados e que leva alguns segundos. Se ele não disser o "
        "período, mande string vazia — NUNCA pergunte de volta. "
        "Em pergunta de acompanhamento da MESMA conversa, repasse o `pack_id` "
        "do bloco PACK anterior: a resposta sai do mesmo pacote, sem "
        "reconsultar."
    )
    args_schema: Type[BaseModel] = PlanoDeConsulta

    company_id: Optional[str] = None
    supabase: Any = None

    class Config:
        arbitrary_types_allowed = True

    def _run(self, **_: Any) -> str:
        raise RuntimeError(
            "ExecutiveIntelligenceTool exige execução assíncrona. Quem chamou "
            "ignorou `exige_async=True` — o executor precisa aguardar `_arun`.")

    async def _arun(self, period: str = "", compare: str = "",
                    views: Optional[List[str]] = None, dimension: str = "",
                    pack_id: str = "", **_: Any) -> str:
        try:
            if pack_id:
                seguindo = self._seguir(pack_id, dimension, period, compare)
                if seguindo is not None:
                    return seguindo
            return await self._montar(period, compare, views or [], dimension)
        except Exception as exc:  # noqa: BLE001
            logger.error("[PULSO-360] falhou (%s): %s", type(exc).__name__, exc)
            return self._erro_legivel(exc)

    # ------------------------------------------------------------------ #
    @staticmethod
    def _erro_legivel(exc: Exception) -> str:
        """O que o modelo deve DIZER quando não deu. Instrução, não relato.

        🔴 A classificação é pelo NOME da classe, e por PREFIXO — `Falha…` e
        `Recusa…`. Duas razões: o tratador de erro não pode importar nada (📊
        na 081 a versão anterior importava para conseguir o `isinstance`, e
        quando o que falhava ERA o import ele quebrava junto, deixando o modelo
        sem instrução nenhuma); e nomear a exceção de UM provider aqui traria o
        dialeto de uma fonte para dentro da tool, que é o acoplamento que esta
        SPEC existe para tirar.
        """
        nome = type(exc).__name__
        conhecida = nome.startswith("Falha") or nome.startswith("Recusa")
        motivo = str(exc)[:220] if conhecida else nome
        return (
            "RELATORIO_FALHOU · o panorama NÃO foi gerado e NÃO existe link. "
            "É PROIBIDO afirmar que o relatório está pronto ou mandar qualquer "
            "endereço. Diga a verdade: a leitura da carteira não completou "
            f"agora, e ofereça tentar de novo. Motivo interno: {motivo}"
        )

    # ------------------------------------------------------------------ #
    def _seguir(self, pack_id: str, dimension: str,
                period: str = "", compare: str = "") -> Optional[str]:
        """A pergunta de acompanhamento, sobre o pacote que JÁ existe.

        🔴 Sem refetch, e portanto sem números novos. `pack_id` desconhecido —
        ou VENCIDO — devolve `None`, e aí o caminho normal roda e consulta.
        Fingir que o cache tinha seria responder com um pacote de outra pergunta.

        🔴 **E um período diferente do pacote também devolve `None`.**

        📊 Achado pelo red team em 03/09/2026: `pack_id` + `period="2019"`
        devolvia o pacote de 2025, inteiro, **sem dizer nada**. O modelo repassa
        o `pack_id` em toda pergunta seguinte da conversa (é o que a descrição da
        tool manda fazer), então basta o dono dizer *"e em 2019?"* para receber
        os números do ano errado com a segurança de quem citou `metric_id`. O
        recorte por `dimension` é filtro sobre o MESMO pacote e continua sem
        consulta; trocar de PERÍODO é outra pergunta, e outra pergunta se
        calcula.
        """
        guardado = buscar_pack(str(self.company_id or ""), pack_id)
        if guardado is None:
            return None
        pacote = guardado["pacote"]
        if self._periodo_diverge(pacote, period, compare):
            logger.info("[094] follow-up com periodo diferente do pacote: "
                        "recalculando em vez de reusar")
            return None
        recorte, fora_do_bloco = self._recortar(pacote, dimension)
        aviso = ""
        if dimension and not fora_do_bloco:
            aviso = (" · recorte pedido: `%s` (filtrado sobre o MESMO pacote, "
                     "sem nova consulta)" % dimension)
        return (
            f"{CARIMBO_PRONTO} · Pulso 360 (mesmo pacote `{pacote.pack_id}`)"
            f"{aviso}.\n\n"
            f"[Abrir o relatório]({guardado['link']})\n\n"
            + (fora_do_bloco + "\n\n" if fora_do_bloco else "")
            + recorte.bloco_para_o_modelo()
            + "\n\n" + resumo_deterministico(pacote, reusado=True)
            + "\n\n" + COMO_FALAR
        )

    # ------------------------------------------------------------------ #
    def _periodo_diverge(self, pacote: Any, period: str, compare: str) -> bool:
        """O `period`/`compare` pedidos batem com os do pacote guardado?

        ⚠️ A comparação é feita sobre as DATAS resolvidas, e não sobre o texto:
        *"2025"*, *"este ano"* e *"de 01/01/2025 a 31/12/2025"* são a mesma
        janela ditas de três jeitos, e recalcular por diferença de redação
        pagaria uma leitura de carteira por sinônimo.
        """
        if not (period or "").strip() and not (compare or "").strip():
            return False
        try:
            p, anterior = periodo_e_comparacao(self._calculos(), period, compare)
        except Exception:  # noqa: BLE001
            # Período ilegível ou recusado não é motivo para servir o pacote
            # velho: manda para o caminho normal, que levanta com o motivo certo.
            return True
        from app.comercial import evidence_pack as ep

        if (period or "").strip() and ep.periodo_iso(p.inicio, p.fim) != dict(
                pacote.period or {}):
            return True
        if not (compare or "").strip():
            return False
        pedido = (ep.periodo_iso(anterior.inicio, anterior.fim)
                  if anterior is not None else None)
        guardado = dict(pacote.compare_period) if pacote.compare_period else None
        return pedido != guardado

    # ------------------------------------------------------------------ #
    @staticmethod
    def rotulos_do_pacote(pacote: Any) -> Dict[str, str]:
        """A LISTA FECHADA de recortes válidos: `{normalizado: como aparece}`.

        🔴 Ela sai do `breakdown` que o registry já calculou — as seguradoras,
        os ramos e as faixas de urgência DESTE pacote. Não é uma lista escrita à
        mão em lugar nenhum: é o conjunto de coisas sobre as quais existe
        detalhe para mostrar.
        """
        from app.comercial.evidence_pack import normalizar_rotulo

        saida: Dict[str, str] = {}
        for m in getattr(pacote, "metrics", ()) or ():
            for b in (m.breakdown or ()):
                cru = str(b.get("rotulo") or b.get("faixa") or "").strip()
                if cru:
                    saida.setdefault(normalizar_rotulo(cru), cru)
        return saida

    @staticmethod
    def _recortar(pacote: Any, dimension: str) -> Tuple[Any, str]:
        """`(pacote, aviso FORA do bloco)`. O detalhe filtrado pela dimensão.

        ⚠️ O `pack_id` não muda, e o valor de cada métrica também não. O que
        o recorte faz é mostrar a linha pedida do detalhe — dizer que o total
        da carteira virou o total de uma seguradora seria inventar um número
        que ninguém calculou.

        🔴 **`dimension` só aceita rótulo que EXISTE no breakdown**, e o que não
        está na lista é recusado com o aviso FORA do bloco citável.

        📊 Achado pelo red team em 03/09/2026. `dimension` é texto livre que o
        LLM preenche a partir da frase do dono, e ele entrava **verbatim** em
        `pack.warnings` — isto é, DENTRO do bloco `<<PACK … PACK>>`, que é a
        única parte da resposta que o narrador foi instruído a tratar como
        verdade citável. Qualquer instrução escrita ali chegava ao modelo com a
        autoridade do dado. A lista fechada fecha a porta pela raiz: o que entra
        no bloco é rótulo que o registry calculou, e nada mais.

        🔴 E a recusa vai FORA do bloco, de propósito: é uma frase sobre o
        PEDIDO, não sobre a carteira. Dentro do pack ela seria um "dado" que o
        modelo citaria com `metric_id` ao lado.
        """
        if not dimension:
            return pacote, ""
        from app.comercial.evidence_pack import normalizar_rotulo

        alvo = normalizar_rotulo(dimension)
        permitidos = ExecutiveIntelligenceTool.rotulos_do_pacote(pacote)
        casados = [bonito for chave, bonito in permitidos.items()
                   if alvo and alvo in chave]
        if not casados:
            amostra = ", ".join(sorted(permitidos.values())[:8])
            return pacote, (
                "⚠️ O recorte pedido não existe neste relatório, então NADA foi "
                "filtrado e os números abaixo são os da carteira inteira. Diga "
                "isso ao dono e ofereça um destes recortes, que são os que a "
                "peça tem: " + (amostra or "nenhum — este pacote não traz "
                                "detalhe por seguradora, ramo ou faixa"))
        import copy

        alvos = {normalizar_rotulo(x) for x in casados}
        recortado = copy.deepcopy(pacote)
        for i, m in enumerate(recortado.metrics):
            if not m.breakdown:
                continue
            linhas = [b for b in m.breakdown
                      if normalizar_rotulo(
                          str(b.get("rotulo") or b.get("faixa") or "")) in alvos]
            if linhas:
                recortado.metrics[i] = type(m)(
                    **dict(m.__dict__, breakdown=tuple(linhas)))
        # ✅ O que entra no bloco é o rótulo que o REGISTRY calculou, e nunca a
        # string do modelo — mesmo quando as duas casam.
        recortado.warnings = list(recortado.warnings) + [
            "recorte %s aplicado sobre o detalhe; os totais continuam sendo "
            "os da carteira inteira" % (", ".join(sorted(casados)))]
        return recortado, ""

    # ------------------------------------------------------------------ #
    async def _montar(self, period: str, compare: str, views: List[str],
                      dimension: str) -> str:
        from app.comercial import cbim
        from app.comercial import evidence_pack as ep
        from app.comercial.metricas import registry
        from app.providers.brokerage_analytics_provider import (
            resolve_brokerage_analytics_provider)

        calc = self._calculos()
        company_id = str(self.company_id or "")
        p, anterior = periodo_e_comparacao(calc, period, compare)

        escolhidas = [v for v in (views or VISOES_PADRAO) if v in VISOES]
        if not escolhidas:
            escolhidas = list(VISOES_PADRAO)
        ids: List[str] = []
        for v in escolhidas:
            for mid in VISOES[v]:
                if mid not in ids:
                    ids.append(mid)

        provider = self._provider(resolve_brokerage_analytics_provider,
                                  cbim.PROVIDER_PILOTO)
        fatos = await provider.fatos(company_id=company_id, inicio=p.inicio,
                                     fim=p.fim, db=self.supabase)
        manifesto_ = await self._manifesto(provider, company_id, fatos)
        if not getattr(fatos, "policies", None) and not getattr(fatos, "renewals", None):
            return (f"{CARIMBO_VAZIO} · não há movimento registrado em "
                    f"{p.rotulo}. Diga isso ao dono e sugira outro período. "
                    "Não invente número.")

        metricas = registry.calcular_varias(ids, fatos, (p.inicio, p.fim),
                                            manifest=manifesto_)
        anteriores: List[Any] = []
        comparacoes: List[Dict[str, Any]] = []
        if anterior is not None:
            ids_comparaveis = [mid for v in escolhidas if v in COMPARAVEIS
                               for mid in VISOES[v] if mid in ids]
            fatos_antes = await provider.fatos(
                company_id=company_id, inicio=anterior.inicio,
                fim=anterior.fim, db=self.supabase)
            anteriores = registry.calcular_varias(
                ids_comparaveis, fatos_antes, (anterior.inicio, anterior.fim),
                manifest=manifesto_)
            de_antes = {m.metric_id: m for m in anteriores}
            for m in metricas:
                par = de_antes.get(m.metric_id)
                if par is None:
                    continue
                try:
                    comparacoes.append(registry.comparar(m, par))
                except ValueError as exc:
                    # 🔴 A recusa do M6 é resultado legítimo, e vai escrita.
                    comparacoes.append({"metric_id": m.metric_id,
                                        "warnings": [str(exc)]})

        agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
        pacote = self._empacotar(ep, company_id, p, anterior, metricas,
                                 anteriores, comparacoes, fatos, agora,
                                 manifesto_)
        link = self._publicar_a_peca(pacote, p, anterior, metricas,
                                     comparacoes, agora, fatos)
        guardar_pack(company_id, pacote, link)
        self._registrar_sinais(ep, pacote)

        recorte, fora_do_bloco = self._recortar(pacote, dimension)
        aviso = " (período padrão — o dono não especificou)" if p.e_padrao else ""
        return (
            f"{CARIMBO_PRONTO} · Pulso 360 de **{p.rotulo}**{aviso}.\n\n"
            f"[Abrir o relatório]({link})\n\n"
            + (fora_do_bloco + "\n\n" if fora_do_bloco else "")
            + recorte.bloco_para_o_modelo()
            + "\n\n" + resumo_deterministico(pacote)
            + "\n\n" + COMO_FALAR
        )

    # ------------------------------------------------------------------ #
    @staticmethod
    def _calculos() -> Any:
        from app.comercial import calculos

        return calculos

    @staticmethod
    def _provider(resolver: Any, chave: str) -> Any:
        """O provider da corretora, pelo registro do port.

        ⚠️ O import do adapter fica AQUI, e é por nome de módulo composto a
        partir da constante do CBIM: é ele que se registra ao ser importado, e
        esta tool não pode nomear sistema de gestão nenhum (M1). Quem quiser
        outro provider registra o dele e muda a constante — sem tocar nesta
        linha, que é o ponto inteiro.
        """
        import importlib

        provider = resolver(chave)
        if provider is None:
            importlib.import_module("app.providers.%s_analytics_provider" % chave)
            provider = resolver(chave)
        if provider is None:
            raise RuntimeError(
                "nenhum provider de analítica registrado para a chave %r" % chave)
        return provider

    @staticmethod
    async def _manifesto(provider: Any, company_id: str, fatos: Any) -> Any:
        """O manifesto do provider, já com o drift desta leitura marcado.

        🔴 **FAIL-CLOSED.** Se o manifesto não carrega, esta função devolve um
        manifesto que bloqueia TUDO — e não `None`.

        📊 Achado pelo red team em 03/09/2026: `except` → `return None`, e
        `registry._avaliar(None, d)` devolve *"nada bloqueia"*. A frase que
        justificava isso ("quem não perguntou pelas capacidades não pode afirmar
        que elas faltam") vale para quem NÃO PERGUNTOU. Aqui perguntou-se, a
        pergunta falhou, e a resposta era liberar as 16 métricas com confiança
        HIGH sobre uma fonte cuja capacidade ninguém conseguiu ler — sem uma
        linha de aviso no pack nem no relatório.

        ⚠️ Provider que **não expõe** `manifesto` continua devolvendo `None`:
        esse é o caso legítimo de "não perguntei". A diferença entre não ter a
        porta e a porta ter quebrado é a diferença inteira.
        """
        f = getattr(provider, "manifesto", None)
        if not callable(f):
            return None
        try:
            return await f(company_id=company_id, lote=fatos)
        except Exception as exc:  # noqa: BLE001
            logger.error("[094] manifesto NAO carregado (%s) — fail-closed: "
                         "todas as metricas ficam INDISPONIVEL",
                         type(exc).__name__)
            from app.comercial.manifesto import (CENSO_ILEGIVEL,
                                                 ProviderCapabilityManifest)

            return ProviderCapabilityManifest(
                provider_key=str(getattr(fatos, "provider_key", "") or ""),
                ilegivel="%s (%s)" % (CENSO_ILEGIVEL, type(exc).__name__))

    # ------------------------------------------------------------------ #
    def _empacotar(self, ep: Any, company_id: str, p: Any, anterior: Any,
                   metricas: List[Any], anteriores: List[Any],
                   comparacoes: List[Dict[str, Any]], fatos: Any,
                   agora: str, manifesto_: Any = None) -> Any:
        """UM pacote — o que o chat lê e o que o Artifact publica."""
        proveniencia = {"spec": "094", "tool": self.name,
                        "template": TEMPLATE_PULSE, "consultado_em": agora,
                        "periodo_rotulo": p.rotulo,
                        "provider_key": str(getattr(fatos, "provider_key", "") or "")}
        prov = getattr(fatos, "provenance", None)
        if prov is not None and hasattr(prov, "serializar"):
            proveniencia.update(prov.serializar())

        cobertura = {m.metric_id: m.coverage for m in metricas}
        avisos = list(getattr(fatos, "warnings", []) or [])
        if p.e_padrao:
            avisos.append("periodo padrao: o dono nao especificou")
        if anterior is None:
            avisos.append("sem comparacao: nenhum periodo anterior foi pedido")
        indisponiveis = [m.metric_id for m in metricas if m.indisponivel]
        if indisponiveis:
            avisos.append("INDISPONIVEL na fonte: " + ", ".join(indisponiveis))
        # 🔴 A integridade do CENSO vai escrita no topo do pack, e não só no
        # envelope de cada métrica. Um relatório inteiro de INDISPONÍVEL parece
        # defeito da fonte do cliente quando o defeito é da nossa medição — e
        # essa troca é a mutação M2 na forma mais cara.
        avisos.extend(getattr(manifesto_, "avisos_de_integridade", []) or [])

        pacote = ep.EvidencePack(
            company_id=company_id,
            period=ep.periodo_iso(p.inicio, p.fim),
            compare_period=(ep.periodo_iso(anterior.inicio, anterior.fim)
                            if anterior is not None else None),
            metrics=list(metricas),
            coverage=cobertura,
            freshness=agora,
            provenance=proveniencia,
            warnings=avisos,
        )
        pacote.findings = ep.achar_findings(metricas, anteriores)
        pacote.warnings.append(
            "comparacoes calculadas: %d" % len(
                [c for c in comparacoes if not c.get("warnings")]))
        return pacote

    # ------------------------------------------------------------------ #
    def _registrar_sinais(self, ep: Any, pacote: Any) -> None:
        """Grava os sinais deste pack. ⚠️ Nunca derruba o relatório.

        🔴 Quem valida é o Fabric, com o `valido()` dele — esta SPEC só LÊ as
        regras (§4: `schemas.py` e `finding_engine.py` NÃO mudam). Um rascunho
        recusado vira log, e não exceção: recusa é resultado legítimo.
        """
        rascunhos = ep.sinais_do_pack(pacote)
        if not rascunhos or self.supabase is None:
            return
        try:
            from app.services.intelligence.schemas import SignalDraft
            from app.services.intelligence.signal_service import SignalService

            servico = SignalService(self.supabase)
            for bruto in rascunhos:
                servico.registrar(SignalDraft(**bruto))
        except Exception as exc:  # noqa: BLE001
            logger.warning("[094] sinais nao gravados (%s)", type(exc).__name__)

    # ------------------------------------------------------------------ #
    @staticmethod
    def rotulos_de_produtor(fatos: Any) -> Dict[str, str]:
        """`{producer_ref: nome}` — 🔴 **e isto NUNCA entra no pack.**

        📊 Achado pelo red team em 03/09/2026: a tabela "Quem apropriou comissão
        no período" do relatório mostrava uma coluna de **hashes truncados**.
        Ela é a peça que o dono da corretora abre para saber quem vendeu o quê —
        e ninguém reconhece um vendedor por `p7baf5d5aadb1`.

        🔴 A regra da §2 desta SPEC nunca foi "o nome não existe": foi *"o nome
        não viaja no que vai ao MODELO"*. O Artifact é conteúdo do tenant, dentro
        do tenant, e é o lugar onde o nome pode estar. O pack — que o chat lê e
        que o narrador cita — continua carregando só a referência opaca, e o
        guarda tem o PAR dos dois lados: o nome no relatório, e nunca no bloco.

        ⚠️ O rótulo do produtor de ORDEM 1, que é a resposta da pergunta "quem
        vendeu". 📊 Uma apólice tem em média 2,0 produtores (censo), e o ranking
        agrupa pelo principal.
        """
        rotulos: Dict[str, str] = {}
        for a in (getattr(fatos, "assignments", None) or ()):
            ref = str(getattr(a, "producer_ref", "") or "")
            nome = str(getattr(a, "producer_label", "") or "").strip()
            if not ref or not nome:
                continue
            ordem = getattr(a, "order", None)
            if ref not in rotulos or ordem == 1:
                rotulos[ref] = nome
        return rotulos

    # ------------------------------------------------------------------ #
    @staticmethod
    def frase_da_cobertura(m: Any) -> str:
        """A cobertura DESTE número, em uma frase, ou vazio quando é 100%.

        🔴 Ela vai DENTRO do cartão. 📊 Achado pela lente do dado, 03/09/2026: a
        cobertura morava só na oitava seção, "Fontes e confiança" — seis seções
        abaixo do número que ela qualifica. O cartão "Quem apropriou comissão no
        período" cobria **6,0%** da comissão, e quem lesse a tabela não tinha
        como saber; o cartão "O que sobra depois do repasse" punha lado a lado
        dois valores de POPULAÇÕES diferentes sem uma linha de ressalva.

        Uma ressalva a seis seções do número não é ressalva: é nota de rodapé de
        um relatório que ninguém rola até o fim.
        """
        if m is None or m.coverage is None or m.coverage >= 1.0:
            return ""
        pct = ("%.1f%%" % (100.0 * m.coverage)).replace(".", ",")
        return "sobre %s %s" % (pct, DO_QUE_E_A_COBERTURA.get(
            m.metric_id, "da população que esta conta consegue usar"))

    # ------------------------------------------------------------------ #
    def _publicar_a_peca(self, pacote: Any, p: Any, anterior: Any,
                         metricas: List[Any], comparacoes: List[Dict[str, Any]],
                         agora: str, fatos: Any = None) -> str:
        from app.agents.tools.relatorios_comerciais import _link, _publicar

        rotulos = self.rotulos_de_produtor(fatos)
        blocos = self._compor(pacote, p, anterior, metricas, comparacoes, agora,
                              rotulos)
        payload = {
            "evidence_pack": pacote.serializar(),
            "periodo": {"inicio": str(p.inicio), "fim": str(p.fim),
                        "rotulo": p.rotulo},
            "comparacao": comparacoes,
            "findings": [dict(f) for f in pacote.findings],
            "papel_dos_produtores": FRASE_SEM_MAPA,
            # 🔴 O nome do produtor mora AQUI, no payload do Artifact do tenant,
            # e em lugar nenhum do `evidence_pack` acima. As duas chaves são
            # vizinhas de propósito: quem editar esta linha vê a outra.
            "rotulos_de_produtor": dict(rotulos),
        }
        ident = _publicar(
            self.supabase, str(self.company_id),
            titulo="Pulso 360 · %s" % p.rotulo,
            subtitulo="O período inteiro, com a fonte de cada número",
            resumo=("Panorama executivo de %s, com cobertura declarada por "
                    "métrica." % p.rotulo),
            template=TEMPLATE_PULSE, payload=payload, blocos=blocos)
        if not ident:
            raise RuntimeError("o artifact não foi criado")
        return _link(ident)

    # ------------------------------------------------------------------ #
    def _compor(self, pacote: Any, p: Any, anterior: Any, metricas: List[Any],
                comparacoes: List[Dict[str, Any]], agora: str,
                rotulos: Optional[Dict[str, str]] = None) -> List[Dict]:
        """As oito seções do `executive.pulse360`, na ordem do template.

        ⛔ Nenhum bloco novo: todos existem em `blocks.py` desde a SPEC-057.
        """
        from app.agents.tools.relatorios_comerciais import _fontes, _reais

        por_id = {m.metric_id: m for m in metricas}
        comp = {c.get("metric_id"): c for c in comparacoes}
        rotulos = rotulos or {}

        def cobertura(mid: str) -> str:
            return self.frase_da_cobertura(por_id.get(mid))

        def lede(*mids: str) -> Dict[str, Any]:
            """A ressalva de cobertura do cartão, pronta para virar `props`.

            🔴 `lede` é renderizado por `blocks._cabecalho`, logo abaixo do
            título e ACIMA dos números — dentro do cartão, e não seis seções
            adiante. Cartão com cobertura cheia não ganha frase nenhuma: um
            aviso que aparece sempre é um aviso que ninguém lê.
            """
            frases = [f for f in (cobertura(m) for m in mids) if f]
            return {"lede": "Conta " + "; ".join(frases) + "."} if frases else {}

        def texto(mid: str) -> str:
            m = por_id.get(mid)
            if m is None or m.indisponivel:
                return "INDISPONÍVEL"
            if m.unit == "BRL":
                return _reais(float(m.value))
            if m.unit == "pct":
                return "%.1f%%" % float(m.value)
            if isinstance(m.value, dict):
                return json.dumps(m.value, ensure_ascii=False)
            return "%d" % int(float(m.value))

        def variacao(mid: str) -> Dict[str, Any]:
            c = comp.get(mid) or {}
            delta = c.get("delta_pct")
            if not isinstance(delta, (int, float)):
                return {}
            return {"delta": round(float(delta), 1),
                    "direction": "up" if delta >= 0 else "down"}

        # 1 · veredito ------------------------------------------------------
        blocos: List[Dict[str, Any]] = [
            {"block": "cover", "props": {
                "eyebrow": "Pulso 360",
                "title": "O período inteiro · %s" % p.rotulo,
                "headline_value": texto("commission.broker_accrued"),
                "headline_label": "comissão apropriada no período",
                "period": p.rotulo}},
            {"block": "verdict", "props": {"text": self._veredito(pacote, p)}},
        ]

        # 2 · atual × anterior ---------------------------------------------
        itens = []
        for mid, rotulo in (("commission.broker_accrued", "Comissão apropriada"),
                            ("production.premium_written", "Prêmio emitido"),
                            ("production.policy_count", "Apólices"),
                            ("renewal.exposure", "A vencer na janela"),
                            ("mix.insurer", "Maior seguradora"),
                            ("producer.performance", "Produtores")):
            if mid not in por_id:
                continue
            item = {"label": rotulo, "value": texto(mid)}
            item.update(variacao(mid))
            rodape = []
            if anterior is not None and mid in comp:
                rodape.append("contra %s" % anterior.rotulo)
            # 🔴 A cobertura no RODAPÉ DO CARTÃO, colada no número. `blocks.kpis`
            # imprime `since` mesmo sem delta — então a ressalva aparece tanto no
            # cartão que tem comparação quanto no que não tem.
            frase = cobertura(mid)
            if frase:
                rodape.append(frase)
            if rodape:
                item["since"] = " · ".join(rodape)
            itens.append(item)
        if itens:
            blocos.append({"block": "kpis", "props": {
                "title": "Este período contra o anterior", "items": itens}})

        # 3 · pessoas e canais ---------------------------------------------
        pessoas = por_id.get("producer.performance")
        if pessoas is not None and pessoas.breakdown:
            props = {
                "eyebrow": "Pessoas e canais",
                "title": "Quem apropriou comissão no período",
                "columns": [
                    {"key": "produtor", "label": "Produtor"},
                    {"key": "papel", "label": "Papel"},
                    {"key": "apolices", "label": "Apólices", "format": "number"},
                    {"key": "comissao", "label": "Comissão", "format": "currency"},
                    {"key": "ticket", "label": "Ticket", "format": "currency"},
                ],
                # 🔴 O NOME, e não o hash. Esta é a ÚNICA seção da peça que o
                # carrega, e ele vem de `rotulos_de_produtor` — que sai dos
                # fatos, e nunca do pack. Um relatório de pessoas com uma coluna
                # de hashes não é um relatório de pessoas.
                "rows": [{"produtor": rotulos.get(
                              str(b.get("producer_ref") or ""),
                              "produtor não identificado na fonte"),
                          "papel": FRASE_SEM_MAPA,
                          "apolices": b.get("apolices"),
                          "comissao": round(float(b.get("comissao") or 0.0), 2),
                          "ticket": round(float(b.get("ticket") or 0.0), 2)}
                         for b in pessoas.breakdown[:15]]}
            props.update(lede("producer.performance"))
            blocos.append({"block": "table", "props": props})

        # 4 · economia pós-repasse, ou a ausência dela ----------------------
        contrib = por_id.get("contribution.after_repasse")
        if contrib is not None and not contrib.indisponivel:
            # 🔴 Os dois números deste cartão são de POPULAÇÕES DIFERENTES —
            # a contribuição é da base de emissão e o repasse é da de vencimento
            # (📊 2,8% de interseção medida). Eles ficam lado a lado porque a
            # pergunta é uma só; a ressalva fica junto porque, sem ela, o cartão
            # convida a subtrair um do outro.
            props = {
                "title": "O que sobra depois do repasse",
                "items": [
                    {"label": "Contribuição depois do repasse",
                     "value": texto("contribution.after_repasse"),
                     "since": cobertura("contribution.after_repasse")
                              or "sobre a interseção das duas populações"},
                    {"label": "Repasse apropriado",
                     "value": texto("repasse.producer_accrued"),
                     "since": cobertura("repasse.producer_accrued")
                              or "sobre as apólices que VENCEM na janela"}]}
            props.update(lede("contribution.after_repasse",
                              "repasse.producer_accrued"))
            blocos.append({"block": "kpis", "props": props})
        else:
            blocos.append({"block": "callout", "props": {
                "tone": "info", "title": "Economia depois do repasse",
                "text": ("Indisponível na fonte conectada: ela não expõe o "
                         "repasse desta janela. Não é zero — é ausência de "
                         "dado, e o número não foi estimado.")}})

        # 5 · mix e concentração -------------------------------------------
        mix = por_id.get("mix.insurer")
        if mix is not None and mix.breakdown:
            blocos.append({"block": "donut", "props": {
                "title": "Comissão por seguradora", "value_type": "currency_short",
                **lede("mix.insurer"),
                "slices": [{"rotulo": str(b.get("rotulo") or ""),
                            "valor": round(float(b.get("comissao") or 0.0), 2)}
                           for b in mix.breakdown]}})

        # 6 · exposição de renovação ---------------------------------------
        exp = por_id.get("renewal.exposure")
        if exp is not None and exp.breakdown:
            blocos.append({"block": "chart", "props": {
                "eyebrow": "Exposição", "title": "O que vence, por urgência",
                **lede("renewal.exposure"),
                "labels": [str(b.get("faixa") or "") for b in exp.breakdown],
                "series": [{"name": "Prêmio",
                            "values": [round(float(b.get("premio") or 0.0), 2)
                                       for b in exp.breakdown]}],
                "value_type": "currency_short"}})

        # 7 · projeção ------------------------------------------------------
        proj = por_id.get("projection.run_rate")
        if proj is not None:
            blocos.append({"block": "callout", "props": {
                "tone": "warning" if proj.indisponivel else "info",
                "title": "Onde o período fecha, no ritmo atual",
                "text": ("%s — premissa: o ritmo dos meses completos se "
                         "mantém. Comissão histórica NÃO é renovação "
                         "garantida." % texto("projection.run_rate"))}})

        # 8 · fontes e confiança -------------------------------------------
        blocos.append(self._fontes_e_confianca(pacote, metricas, agora))
        blocos.append(_fontes(agora, "Endossos e documentos que não são "
                                     "apólice ficam fora da contagem."))
        blocos.append({"block": "footer", "props": {
            "disclaimer": "Documento interno. Não contém CPF/CNPJ nem telefone "
                          "de segurado."}})
        return blocos

    # ------------------------------------------------------------------ #
    @staticmethod
    def _fontes_e_confianca(pacote: Any, metricas: List[Any],
                            agora: str) -> Dict[str, Any]:
        """A oitava seção — a que diz de onde veio cada número.

        🔴 Ela é a que impede o relatório de ser bonito e indefensável: sem
        `pack_id`, sem cobertura por métrica e sem o aviso de INDISPONÍVEL,
        quem lê não tem como discordar de nada.
        """
        linhas = []
        for m in metricas:
            detalhe = "base %s · cobertura %s · confiança %s" % (
                m.time_basis,
                ("%.1f%%" % (100.0 * m.coverage)) if m.coverage is not None
                else "não medida",
                m.confidence)
            if m.indisponivel:
                detalhe += " · INDISPONÍVEL na fonte"
            linhas.append({"label": "%s@%d" % (m.metric_id, m.version),
                           "detail": detalhe,
                           "as_of_label": "consultado em %s" % agora})
        linhas.append({
            "label": "Pacote de evidência",
            "detail": "pack_id %s · provider %s · o chat e esta peça leem o "
                      "MESMO pacote" % (
                          pacote.pack_id,
                          pacote.provenance.get("provider_key") or "não declarado"),
            "as_of_label": "consultado em %s" % agora})
        return {"block": "sources", "props": {"items": linhas}}

    # ------------------------------------------------------------------ #
    @staticmethod
    def _veredito(pacote: Any, p: Any) -> str:
        """O veredito, DETERMINÍSTICO: sai dos achados, não de um modelo."""
        if not pacote.findings:
            return ("O período %s não acionou nenhum limiar dos achados "
                    "determinísticos desta peça. Os números e a cobertura de "
                    "cada um estão nas seções abaixo." % p.rotulo)
        frases = [str(f.get("summary") or "") for f in pacote.findings]
        return ("O que este período pede atenção, na ordem em que os limiares "
                "foram acionados: " + "; ".join(frases) + ".")


# --------------------------------------------------------------------------
def ferramenta_do_pulso_360(*, company_id: Optional[str],
                            supabase: Any) -> List[BaseTool]:
    """A tool, ou lista vazia. Nunca levanta na montagem do grafo."""
    if not company_id or supabase is None:
        return []
    supabase = getattr(supabase, "client", supabase)
    return [ExecutiveIntelligenceTool(company_id=str(company_id),
                                      supabase=supabase)]
