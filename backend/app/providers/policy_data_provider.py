# -*- coding: utf-8 -*-
"""A PORTA `PolicyDataProvider` — o contrato de leitura de apólice, o modelo
canônico da casa e a reconciliação CADASTRO × DOCUMENTO.

SPEC-016 E5 criou este arquivo. **SPEC-EXTRA-001.1 BLOCO A o evolui aqui, no
arquivo que já existe** — nenhum `backend/app/services/policy_provider/` nasce
ao lado dele (CLAUDE.md §5; proposta §0.3).

🔴 **ACL PERMANENTE. A InfoCap é o provider piloto, NUNCA a semântica.**
O padrão-mãe é o Anti-Corruption Layer (Evans/DDD; Microsoft Azure
Architecture Center), e a frase que vira teste é esta:

    "Communication between subsystem A and the anti-corruption layer always
     uses the data model and architecture of subsystem A."

Traduzido: **a porta devolve `Apolice`, nunca o `Dict[str, Any]` da InfoCap.**
Até 14/09/2026 ela devolvia o dicionário do fornecedor — e foi por isso que
`preliq`, `sit_renovacao_txt` e `tabela_itens` vazaram para o resto do sistema.
Um `Protocol` cujo valor de retorno é o dicionário do fornecedor **não isola
nada**.

## O que atravessa esta porta, e o que NÃO atravessa

```
✅ atravessa   Apolice · Cobertura · Parcela · PlanoDeAssistencia · Vigencia
               CampoComOrigem · Divergencia · Sinal · SeguradoraCanonica
               RamoCanonico · INDISPONIVEL · CapacidadeDoProvider
⛔ não atravessa   preliq · nosnum · codfil · sit_renovacao_txt · tabela_itens
                   forma_pag · inivig · fimvig · qualquer dict cru do provider
                   `date.today()` implícito — o "hoje" da vigência é PARÂMETRO
```

⚠️ **A exceção escrita:** `apolice_ref`/`cliente_ref` continuam sendo o
*locator técnico* `"<provider>:<parte>:<parte>"` que `parse_policy_locator_ref`
define aqui embaixo (:1). Ele é **opaco** para quem o consome — quem o lê não
sabe que a segunda parte é um `codfil`, e não pode saber. Número humano de
apólice **nunca** é ref.

## Por que `capacidades()` vem antes de tudo

O mesmo motivo da porta irmã (`brokerage_analytics_provider.py`): um provider
que não declara o que consegue entregar obriga quem pergunta a **descobrir por
ausência** — e ausência lida como zero é o defeito que esta SPEC existe para
matar. `DESCONHECIDA` lê-se *"não verificado"*, jamais *"não tem"*.

## Os três membros DEPRECIADOS, e por que eles estão NO contrato

📊 Medido em 14/09/2026 (`grep -rn "get_policy_data_provider|provider\\.(lookup|
detail|vehicle)" backend/app`): CINCO módulos, OITO pontos de chamada. Um deles
é `app/services/billing_collection.py:1205-1212`, da **EXTRA-001.6, que corre
em paralelo**. Tirar `lookup`/`detail`/`vehicle` agora quebraria a cobrança de
uma SPEC irmã em execução.

🔴 E o outro lado do mesmo defeito: `vehicle` **nunca esteve** no `Protocol` —
só na implementação concreta. 📊 Por isso EXISTIAM 4 `hasattr(provider,
"vehicle")` em produção: um adaptador novo que esquecesse o método não
quebrava, respondia *"Fonte de veículos indisponível"* — e o atendente pedia a
placa ao cliente. **Falha silenciosa que chega ao segurado.**
`register_policy_data_provider` agora **RECUSA** adaptador incompleto, com a
lista dos membros que faltam, e os 4 `hasattr` saíram no BLOCO D (📊 `grep -rn
"hasattr(provider" backend/app` → 0 em código; conte você).

Rodar o guarda:
    PYTHONIOENCODING=utf-8 python tests/test_a_porta_nao_vaza_o_fornecedor.py
"""

from __future__ import annotations

import io
import json
import logging
import os
import re
import unicodedata
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Literal,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)

logger = logging.getLogger(__name__)

__all__ = [
    # locator
    "parse_policy_locator_ref",
    # sentinela e dinheiro
    "Indisponivel",
    "INDISPONIVEL",
    "Dinheiro",
    "dinheiro",
    "dinheiro_de_texto",
    "reais",
    # modelo
    "Origem",
    "ORIGENS",
    "Confianca",
    "CampoComOrigem",
    "Divergencia",
    "Cobertura",
    "Parcela",
    "PlanoDeAssistencia",
    "SituacaoDaVigencia",
    "Vigencia",
    "Sinal",
    "ReferenciaDeDocumento",
    "LinhaDeCoberturaDoDocumento",
    "ApoliceDocumental",
    "DocumentoOficial",
    "SeguradoraCanonica",
    "RamoCanonico",
    "Apolice",
    "ApoliceNaLista",
    "ResultadoDeBusca",
    "ListaDeApolices",
    "Capacidade",
    "CapacidadeDoProvider",
    "UNKNOWN",
    # regras puras
    "normalizar_rotulo",
    "grupo_de_rotulo",
    "mapa_de_rotulos",
    "classificar_vigencia",
    # a escolha (BLOCO B) — vigência e ramo decididos NA PORTA
    "SITUACOES_OCULTAS",
    "FAMILIAS_DE_RAMO",
    "NOME_DA_FAMILIA",
    "familia_de_ramo",
    "StatusDaEscolha",
    "Escolha",
    "escolher_apolice",
    "NUMERO_NAO_RETORNADO",
    "NUMEROS_QUE_NAO_SAO_NUMERO",
    "normalizar_numero_humano",
    "numero_humano_valido",
    "numero_humano_de",
    "opcoes_em_texto",
    "reconciliar",
    "TOLERANCIA_DE_PREMIO",
    # contrato e registry
    "PolicyDataProvider",
    "MEMBROS_DO_CONTRATO",
    "InfocapPolicyDataProvider",
    "register_policy_data_provider",
    "get_policy_data_provider",
    "policy_data_providers",
]

_PROVIDER_KEY_RE = re.compile(r"^[a-z][a-z0-9_-]*$")

#: A palavra que o catálogo devolve quando não casa. É **STRING**, e nunca é
#: omitida nem virada em zero — o mesmo contrato da SPEC-094.1 (`coenti_de`).
UNKNOWN = "UNKNOWN"


def parse_policy_locator_ref(value: Any) -> Optional[Tuple[str, Tuple[str, ...]]]:
    """Parse genérico de locator técnico. Retorna (provider, partes) ou None.

    Número humano simples, vazio ou locator incompleto → None (o chamador deve
    tratar como policy_number humano, que resolve pelo caminho canônico).
    """
    text = str(value or "").strip()
    if not text or ":" not in text:
        return None
    parts = [p.strip() for p in text.split(":")]
    if len(parts) < 3 or any(not p for p in parts):
        return None
    provider = parts[0].lower()
    if not _PROVIDER_KEY_RE.match(provider):
        return None
    return provider, tuple(parts[1:])


# ===========================================================================
# A SENTINELA — ausência TIPADA. Nunca `0`, nunca `None` ambíguo.
# ===========================================================================
class Indisponivel:
    """A fonte não entregou este dado. **Não é zero, e não é "não existe".**

    🔴 Por que um TIPO e não a string `"UNAVAILABLE"` da SPEC-094:

    📊 Medido em 14/09/2026 — `grep -n "UNAVAILABLE" backend/app/comercial/
    evidence_pack.py` → `:61  UNAVAILABLE = "UNAVAILABLE"`. O sentinela da 094
    é uma **string**, e importá-lo aqui faria duas coisas ruins de uma vez:
    (1) `app/providers/policy_data_provider.py` passaria a importar
    `app.comercial.evidence_pack` (912 linhas do domínio de ANALYTICS),
    acoplando apólice a métrica — exatamente o que as duas portas existem para
    separar; (2) `INDISPONIVEL` seria um `str`, e `if valor:` sobre uma string
    não-vazia dá **True**, que é o contrário do que a ausência significa.

    Aqui `bool(INDISPONIVEL)` é **False**, o `repr` diz o que é, e a
    comparação é por identidade (`é` singleton).
    """

    _instancia: "Optional[Indisponivel]" = None

    def __new__(cls) -> "Indisponivel":
        if cls._instancia is None:
            cls._instancia = super().__new__(cls)
        return cls._instancia

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "INDISPONIVEL"

    def __str__(self) -> str:
        return "indisponível"

    def __eq__(self, outro: Any) -> bool:
        return outro is self

    def __hash__(self) -> int:
        return hash("__INDISPONIVEL__")


#: O singleton. Compare por identidade: `valor is INDISPONIVEL`.
INDISPONIVEL = Indisponivel()


# ===========================================================================
# DINHEIRO — `Decimal`, com duas casas. E o porquê está escrito.
# ===========================================================================
#: 🔴 DECISÃO (nota 90 x 55 para centavos-int): `Decimal` quantizado em 2 casas.
#: O motivo é medido, não estético: o contador de prêmio desta SPEC compara
#: `Σ premio` com `premio_liquido` sob tolerância de **R$ 0,05**, e a fonte
#: entrega `float` (`premio: 4803.67`). Somar 15 `float` e comparar com outro
#: `float` reintroduz o erro de ponto flutuante DENTRO da régua que decide se o
#: cadastro está incompleto — a diferença de R$ 0,01 da Allianz (4.803,67 x
#: 4.803,68) mora exatamente na casa que o `float` erra. Centavos-`int` também
#: resolveria, mas obrigaria cada leitor a saber a escala (é o defeito que a
#: própria fonte já comete: 📊 `parcelas[].vlvenc` da HDI vem `8231.0` para uma
#: parcela de R$ 82,31 — ver `Parcela`), e `Decimal("82.31")` não deixa dúvida.
Dinheiro = Decimal

_DOIS_CENTAVOS = Decimal("0.01")

#: 💭 Arredondamento de emissão. A tolerância é pequena DE PROPÓSITO: uma
#: tolerância generosa transforma o contador de prêmio em enfeite (proposta
#: §5.5 regra 3). 📊 Ela cobre o que foi medido: a maior diferença por
#: cobertura entre cadastro e PDF na Allianz do golden é R$ 0,04 (Incêndio de
#: Bens de Condôminos, 307,30 x 307,26).
TOLERANCIA_DE_PREMIO = Decimal("0.05")


def dinheiro(valor: Any) -> Union[Dinheiro, Indisponivel]:
    """Número/`str` da fonte → `Decimal` com 2 casas. Ilegível → `INDISPONIVEL`.

    ⛔ `None` **nunca** vira `Decimal("0")`. Zero é um valor; ausência não é.
    ⚠️ O zero EXPLÍCITO da fonte (`premio: 0.0`) continua sendo `Decimal("0")` —
    📊 é o caso da `ASSITENCIA 24HS` da Allianz, cujo cadastro diz 0,00 e cujo
    PDF diz R$ 23,88. Confundir esse zero com ausência apagaria a divergência.
    """
    if valor is None or isinstance(valor, Indisponivel):
        return INDISPONIVEL
    if isinstance(valor, Decimal):
        return valor.quantize(_DOIS_CENTAVOS)
    if isinstance(valor, bool):
        return INDISPONIVEL
    if isinstance(valor, (int, float)):
        try:
            return Decimal(str(valor)).quantize(_DOIS_CENTAVOS)
        except (InvalidOperation, ValueError):
            return INDISPONIVEL
    texto = str(valor or "").strip()
    if not texto:
        return INDISPONIVEL
    return dinheiro_de_texto(texto)


_RE_NUMERO_BR = re.compile(r"-?\d{1,3}(?:\.\d{3})*,\d{2}|-?\d+,\d{2}|-?\d+(?:\.\d+)?")


def dinheiro_de_texto(texto: Any) -> Union[Dinheiro, Indisponivel]:
    """`"R$ 1.234,56"` / `"1234.56"` / `"1.234,56"` → `Decimal`.

    O adaptador precisa disto porque o conector já formata em pt-BR
    (`_money_br`, `infocap_connector.py:3229`): o pack real traz
    `amount = "R$ 100.000,00"`, e a porta não pode devolver uma string de
    moeda para quem vai somar.
    """
    bruto = str(texto or "").strip()
    if not bruto:
        return INDISPONIVEL
    limpo = bruto.replace("R$", "").replace("r$", "").strip()
    achado = _RE_NUMERO_BR.search(limpo)
    if not achado:
        return INDISPONIVEL
    numero = achado.group(0)
    if "," in numero:
        numero = numero.replace(".", "").replace(",", ".")
    try:
        return Decimal(numero).quantize(_DOIS_CENTAVOS)
    except (InvalidOperation, ValueError):
        return INDISPONIVEL


def reais(valor: Any) -> str:
    """`Decimal` → `"R$ 1.234,56"`. `INDISPONIVEL` → `"indisponível"`."""
    if valor is None or isinstance(valor, Indisponivel):
        return "indisponível"
    try:
        numero = Decimal(str(valor)).quantize(_DOIS_CENTAVOS)
    except (InvalidOperation, ValueError):
        return "indisponível"
    formatado = f"{numero:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")
    return f"R$ {formatado}"


# ===========================================================================
# O MODELO CANÔNICO — com origem por campo (PROV-O modelado, não adotado)
# ===========================================================================
#
# 🔴 A ideia que se modela da PROV-O (W3C, 30/04/2013) é UMA: proveniência é
# **do dado**, não do log. `wasDerivedFrom` aplicado a uma linha de cobertura.
# ⛔ O que se REJEITA: RDF, OWL, a ontologia inteira, um grafo. Três campos num
#    dataclass congelado: `origem`, `confianca`, `detalhe`.

Origem = Literal["sistema_de_gestao", "documento_oficial", "catalogo", "manual"]
ORIGENS: Tuple[str, ...] = ("sistema_de_gestao", "documento_oficial", "catalogo", "manual")

Confianca = Literal["alta", "media", "baixa"]
_CONFIANCAS: Tuple[str, ...] = ("alta", "media", "baixa")

T = TypeVar("T")


@dataclass(frozen=True)
class CampoComOrigem(Generic[T]):
    """Um valor que sabe de onde veio. **Sem origem, não se constrói.**

    🔴 `origem=None` é `TypeError`, não um aviso — é a regra que o modelo
    inteiro existe para impor: *toda linha que chega ao corretor ou ao segurado
    carrega origem*. A mutação M-A2 (`__post_init__` aceitando `None`) tem de
    deixar o guarda vermelho.

    ⛔ `detalhe` guarda `provider_field`, `pagina`, `trecho_hash` — **nunca** o
    trecho cru com PII.
    """

    valor: Union[T, Indisponivel]
    origem: Origem
    confianca: Confianca = "media"
    detalhe: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.origem not in ORIGENS:
            raise TypeError(
                "CampoComOrigem exige `origem` em %r — recebeu %r. "
                "Toda linha que chega ao corretor carrega origem (SPEC-EXTRA-001.1 §5.2)."
                % (list(ORIGENS), self.origem)
            )
        if self.confianca not in _CONFIANCAS:
            raise TypeError(
                "CampoComOrigem exige `confianca` em %r — recebeu %r."
                % (list(_CONFIANCAS), self.confianca)
            )

    @property
    def tem_valor(self) -> bool:
        return not isinstance(self.valor, Indisponivel) and self.valor is not None


def indisponivel_por(origem: Origem = "sistema_de_gestao", **detalhe: Any) -> CampoComOrigem[Any]:
    """Ausência declarada, com origem. Existe para que nem a AUSÊNCIA seja órfã."""
    return CampoComOrigem(valor=INDISPONIVEL, origem=origem, confianca="baixa", detalhe=dict(detalhe))


@dataclass(frozen=True)
class Divergencia:
    """As DUAS fontes discordaram, e as duas ficam.

    🔴 Divergência **não escolhe**. 📊 A franquia de Danos Elétricos da HDI era
    `10.00%-550,00` no cadastro e "mínimo R$ 600,00" no documento. A resposta
    diz o número do documento **e** que o cadastro diz outro — o corretor
    decide, porque é o corretor que liga para a seguradora.
    """

    campo: str
    valor_sistema_de_gestao: Any
    valor_documento_oficial: Any
    detalhe: Dict[str, Any] = field(default_factory=dict)

    def como_frase(self) -> str:
        return (
            "%s: o documento oficial diz %s e o sistema de gestão diz %s"
            % (self.campo, _legivel(self.valor_documento_oficial), _legivel(self.valor_sistema_de_gestao))
        )


def _legivel(valor: Any) -> str:
    if isinstance(valor, Decimal):
        return reais(valor)
    if valor is None or isinstance(valor, Indisponivel):
        return "indisponível"
    return str(valor)


@dataclass(frozen=True)
class Cobertura:
    """Uma linha de cobertura, com origem em CADA campo."""

    rotulo: str
    rotulo_normalizado: str
    limite: CampoComOrigem[Any]
    franquia: CampoComOrigem[Any]
    premio: CampoComOrigem[Any]
    divergencias: Tuple[Divergencia, ...] = ()
    grupo: Optional[str] = None

    def __post_init__(self) -> None:
        for nome in ("limite", "franquia", "premio"):
            campo = getattr(self, nome)
            if not isinstance(campo, CampoComOrigem):
                raise TypeError(
                    "Cobertura.%s tem de ser CampoComOrigem — recebeu %r. "
                    "Cobertura só se constrói com origem (SPEC-EXTRA-001.1 §5.2)."
                    % (nome, type(campo).__name__)
                )

    @property
    def divergencia(self) -> Optional[Divergencia]:
        """A primeira divergência, para quem só quer saber SE diverge.

        ⚠️ DIVERGE da proposta §5.2, que declarava `divergencia: Divergencia |
        None` (singular). 📊 O motivo é medido: a **mesma** cobertura diverge em
        DOIS campos ao mesmo tempo — Danos Elétricos da HDI diverge na franquia
        (550 x 600) **e** no prêmio (19,17 x 17,25). Com um campo só, uma das
        duas seria descartada em silêncio, que é justamente o que a regra 1 de
        §5.5 proíbe. A tupla fica; esta propriedade mantém a leitura singular.
        """
        return self.divergencias[0] if self.divergencias else None

    @property
    def origens(self) -> Tuple[str, ...]:
        return tuple(sorted({self.limite.origem, self.franquia.origem, self.premio.origem}))


@dataclass(frozen=True)
class Parcela:
    """Uma parcela. 🔴 `forma_de_pagamento` vem DAS PARCELAS, nunca do cabeçalho.

    📊 §8.3: o `forma_pag` do cabeçalho da HDI diz **Boleto Bancário** enquanto
    as **4 parcelas** dizem **Cartão de Crédito**. O campo do cabeçalho não
    atravessa a fronteira com esse nome; ele vira o sinal
    `cabecalho_divergente`.

    ⚠️ 📊 **ACHADO de 14/09/2026, e ele não é meu de consertar:** o golden
    registra `parcelas[].valor = 8231.0` no cadastro para uma parcela que o PDF
    e o próprio cabeçalho dizem valer **R$ 82,31** — a fonte devolve o valor em
    CENTAVOS em `vlvenc`. A porta **não converte em silêncio** (seria adivinhar
    a escala): ela reconcilia com o documento e deixa a `Divergencia` escrita,
    para que o número errado não chegue calado ao segurado. Registrado como
    pendência no relatório do BLOCO A.
    """

    numero: int
    vencimento: CampoComOrigem[Any]
    valor: CampoComOrigem[Any]
    forma_de_pagamento: CampoComOrigem[Any]
    quitada_em: Optional[CampoComOrigem[Any]] = None
    divergencias: Tuple[Divergencia, ...] = ()

    def __post_init__(self) -> None:
        for nome in ("vencimento", "valor", "forma_de_pagamento"):
            campo = getattr(self, nome)
            if not isinstance(campo, CampoComOrigem):
                raise TypeError(
                    "Parcela.%s tem de ser CampoComOrigem — recebeu %r."
                    % (nome, type(campo).__name__)
                )
        if self.quitada_em is not None and not isinstance(self.quitada_em, CampoComOrigem):
            raise TypeError("Parcela.quitada_em tem de ser CampoComOrigem ou None.")

    @property
    def em_aberto(self) -> bool:
        return self.quitada_em is None or not self.quitada_em.tem_valor


EstadoDoPlano = Literal["contratado", "nao_contratado", "nao_sabemos_ainda"]


@dataclass(frozen=True)
class PlanoDeAssistencia:
    """O plano de assistência. `nao_sabemos_ainda` é um estado legítimo.

    📊 `tabela_itens` do fornecedor traz **o nome do plano** ("PACOTE",
    "Benefícios") e nada mais. Nome sem lista de serviços não é "contratado";
    é `nao_sabemos_ainda`, e a diferença é a que decide se o atendente promete
    guincho ao segurado.
    """

    nome: CampoComOrigem[Any]
    nivel: Optional[CampoComOrigem[Any]] = None
    servicos: Tuple[CampoComOrigem[Any], ...] = ()
    estado: EstadoDoPlano = "nao_sabemos_ainda"


SituacaoDaVigencia = Literal["VIGENTE", "VENCIDA", "CANCELADA", "FUTURA", "DESCONHECIDA"]


@dataclass(frozen=True)
class Vigencia:
    inicio: Optional[date]
    fim: Optional[date]
    situacao: SituacaoDaVigencia = "DESCONHECIDA"
    detalhe: Dict[str, Any] = field(default_factory=dict)

    @property
    def vigente(self) -> bool:
        return self.situacao == "VIGENTE"


@dataclass(frozen=True)
class Sinal:
    """Um fato sobre a apólice que o corretor precisa VER, não um erro.

    `cadastro_incompleto` · `cabecalho_divergente` · `rotulo_ambiguo` ·
    `renovacao` · `sinistro` · `conexao_arquivada_ignorada`.
    """

    codigo: str
    detalhe: Dict[str, Any] = field(default_factory=dict)


def frase_do_sinal(sinal: Sinal) -> str:
    """Um `Sinal` → a frase que o corretor LÊ. 💭 copy — nunca citável como fato.

    🔴 Ela existe porque **escrever o sinal não era mostrá-lo**. 📊 Medido em
    14/09/2026: dos 5 sinais que a porta produz, só `cadastro_incompleto` e
    `cabecalho_divergente` chegavam ao briefing; `rotulo_ambiguo`,
    `franquia_em_prosa_sem_dono` e `situacao_de_renovacao` eram escritos e
    ninguém os lia — e a pendência `P-E0011-FRANQUIA-EM-PROSA-SEM-DONO` afirmava
    *"o corretor VÊ o sinal"*.

    🔴 Mora na PORTA, não no adaptador: `Sinal` é do modelo canônico, e o
    próximo adaptador (Agger, Quiver) tem de produzir a MESMA frase. Uma
    segunda cópia da tradução seria um segundo motor (CLAUDE.md §5).

    ⛔ Nenhuma frase nomeia fornecedor: o que o corretor lê é *"o sistema de
    gestão"* e *"o documento oficial"* (§3.2 da fronteira).

    ⚠️ Código desconhecido **não some**: ele vira uma frase genérica com o
    próprio código em palavras — um aviso que ninguém traduziu ainda é melhor
    do que um aviso que ninguém vê.
    """
    detalhe = dict(sinal.detalhe or {})
    codigo = str(sinal.codigo or "").strip()

    if codigo == "franquia_em_prosa_sem_dono":
        textos = [str(t).strip() for t in (detalhe.get("textos") or []) if str(t).strip()]
        quantas = int(detalhe.get("quantidade") or len(textos))
        return (
            "o documento oficial lista %d franquia%s que o sistema de gestão não associa a "
            "nenhuma cobertura: %s. Confirme na seguradora antes de afirmar que uma cobertura "
            "não tem franquia."
            % (quantas, "" if quantas == 1 else "s", "; ".join(textos) or "sem texto legível")
        )
    if codigo == "rotulo_ambiguo":
        candidatos = [str(c).strip() for c in (detalhe.get("candidatos") or []) if str(c).strip()]
        return (
            "a cobertura «%s» do cadastro casa com mais de uma linha do documento oficial (%s) "
            "e o sistema não consegue dizer qual é qual: diga as duas e não escolha por conta."
            % (detalhe.get("rotulo") or "sem rótulo", ", ".join(candidatos) or "sem candidatas")
        )
    if codigo == "situacao_de_renovacao":
        return (
            "o sistema de gestão marca a renovação desta apólice como «%s». É um estado do "
            "CADASTRO: ele não decide vigência — quem decide é a data, já dita acima."
            % (str(detalhe.get("texto") or "").strip() or "sem texto")
        )
    if codigo == "situacao_de_sinistro":
        return (
            "o sistema de gestão registra «%s» na situação de sinistro desta apólice."
            % (str(detalhe.get("texto") or "").strip() or "sem texto")
        )
    if codigo == "cabecalho_divergente":
        nas_parcelas = [str(f).strip() for f in (detalhe.get("nas_parcelas") or []) if str(f).strip()]
        return (
            "o cabeçalho do cadastro e as parcelas discordam sobre %s: no cabeçalho «%s», "
            "nas parcelas «%s». A das parcelas é a que vale."
            % (detalhe.get("campo") or "um campo",
               detalhe.get("no_cabecalho") or "sem valor",
               ", ".join(nas_parcelas) or "sem valor")
        )
    if codigo == "cadastro_incompleto":
        return (
            "a soma das coberturas do cadastro não fecha com o prêmio líquido: faltam %s (%s%%) "
            "em %d cobertura%s cadastrada%s. As coberturas já reconciliadas acima é que valem."
            % (reais(detalhe.get("diferenca_reais")), str(detalhe.get("diferenca_pct") or "-"),
               int(detalhe.get("coberturas_do_cadastro") or 0),
               "" if int(detalhe.get("coberturas_do_cadastro") or 0) == 1 else "s",
               "" if int(detalhe.get("coberturas_do_cadastro") or 0) == 1 else "s")
        )
    if codigo == "apolice_cancelada":
        return "o sistema de gestão marca esta apólice como CANCELADA."
    if codigo == "status_do_fornecedor":
        return (
            "o sistema de gestão marca esta apólice como «%s». É um estado do CADASTRO; "
            "a vigência é a da data." % (str(detalhe.get("texto") or "").strip() or "sem texto")
        )
    # ⚠️ O desconhecido, em palavras — nunca `snake_case` no texto do produto.
    return "o sistema de gestão registrou o aviso «%s» sobre esta apólice." % (
        codigo.replace("_", " ") or "sem código")


@dataclass(frozen=True)
class ReferenciaDeDocumento:
    """O documento, por REFERÊNCIA. ⛔ O texto do PDF nunca entra no modelo."""

    paginas: Optional[int] = None
    parser: Optional[str] = None
    cache_key: Optional[str] = None
    conteudo_hash: Optional[str] = None
    itens_de_evidencia: int = 0


@dataclass(frozen=True)
class LinhaDeCoberturaDoDocumento:
    """Uma linha da tabela de coberturas do PDF, como ela foi lida."""

    rotulo: str
    limite: Union[Dinheiro, Indisponivel] = INDISPONIVEL
    premio: Union[Dinheiro, Indisponivel] = INDISPONIVEL
    franquia_texto: Optional[str] = None
    pagina: Optional[int] = None


@dataclass(frozen=True)
class ApoliceDocumental:
    """O que o DOCUMENTO OFICIAL diz — a outra metade de `reconciliar`.

    🔴 Quem liga o extrator real a isto é o **BLOCO D**. 📊 Medido no BLOCO 0
    (divergência D4): hoje `_COVERAGE_ROW_RE` exige `R$` e produz **0**
    `coverage_row` no PDF da HDI e **1** no da Allianz (e a única é "Prêmio
    Líquido", uma linha de prêmio lida como cobertura). Por isso
    `apolice_documental_do_pack()` existe e é honesta: sem linha, devolve
    `None`, e a reconciliação continua valendo para o dia em que o parser ler
    as duas tabelas reais. Os guardas do BLOCO A alimentam as linhas a partir
    do golden REAL (`documento_oficial.linhas_de_cobertura`), e por isso
    GA2/GA3 provam a reconciliação **sem depender do BLOCO D**.
    """

    linhas: Tuple[LinhaDeCoberturaDoDocumento, ...] = ()
    plano_de_assistencia: Optional[PlanoDeAssistencia] = None
    parcelas: Tuple[Parcela, ...] = ()
    premio_liquido: Union[Dinheiro, Indisponivel] = INDISPONIVEL
    referencia: Optional[ReferenciaDeDocumento] = None


@dataclass(frozen=True)
class DocumentoOficial:
    """O documento oficial pronto para ser citado: referência + o que ele diz."""

    referencia: ReferenciaDeDocumento
    conteudo: Optional[ApoliceDocumental] = None
    disponivel: bool = True
    motivo_de_ausencia: Optional[str] = None


@dataclass(frozen=True)
class SeguradoraCanonica:
    """A seguradora com a chave NOSSA. `coenti` vem de `coenti_de()`.

    ⛔ Esta classe **não lê JSON e não tem mapa**. Quem resolve a chave SUSEP é
    `app.providers.susep_ses_provider.coenti_de` — o leitor que já existe
    (SPEC-094.1 BLOCO B, 61 siglas revisadas por gente). Um segundo catálogo
    aqui seria motor paralelo (CLAUDE.md §5).
    """

    chave: str
    coenti: str = UNKNOWN
    nome_listado: Optional[str] = None

    @property
    def conhecida(self) -> bool:
        return self.coenti != UNKNOWN


@dataclass(frozen=True)
class RamoCanonico:
    abreviatura: str
    cogrupo: str = UNKNOWN
    nome_humano: Optional[str] = None

    @property
    def conhecido(self) -> bool:
        return self.cogrupo != UNKNOWN


@dataclass(frozen=True)
class ItemDeRisco:
    """O que está segurado: o objeto do risco, com origem por campo.

    🔴 **Existe para que `provider.vehicle(...)` possa morrer.** (§5.1.1, itens
    3–6.) 📊 Medido em 14/09/2026: quatro pontos de produção chamavam
    `provider.vehicle(...)` atrás de um `hasattr` — `infocap_tool`,
    `portal_tool`, `insurer_dispatch_tool` e `vehicle_tool`. O `hasattr` saiu no
    BLOCO D (o `Protocol` e o registry passaram a ser o contrato de verdade); a
    CHAMADA continua, porque migrá-la atravessaria os caminhos de acionamento
    (SPEC-017) e vidros (SPEC-025), que estão fora da superfície testada desta
    SPEC.

    ⚠️ Este campo já é preenchido pelo adaptador InfoCap. Quem o consome em vez
    de `vehicle()` é a **P-E0011-VEHICLE-VIA-DETALHAR** — e é por ele existir
    preenchido que a migração será uma troca de leitor, não uma peça nova.
    """

    item: Optional[int] = None
    descricao: Optional[CampoComOrigem[Any]] = None
    placa: Optional[CampoComOrigem[Any]] = None
    cidade: Optional[CampoComOrigem[Any]] = None
    estado: Optional[CampoComOrigem[Any]] = None
    observacoes: Optional[CampoComOrigem[Any]] = None


@dataclass(frozen=True)
class Apolice:
    """A apólice como a casa a entende. **Nunca o dicionário do fornecedor.**"""

    apolice_ref: str
    numero_humano: str
    seguradora: SeguradoraCanonica
    ramo: RamoCanonico
    vigencia: Vigencia
    coberturas: Tuple[Cobertura, ...] = ()
    parcelas: Tuple[Parcela, ...] = ()
    premio_liquido: Optional[CampoComOrigem[Any]] = None
    plano_de_assistencia: Optional[PlanoDeAssistencia] = None
    sinais: Tuple[Sinal, ...] = ()
    documento: Optional[ReferenciaDeDocumento] = None
    item_de_risco: Optional[ItemDeRisco] = None
    provider_key: str = ""

    def sinal(self, codigo: str) -> Optional[Sinal]:
        return next((s for s in self.sinais if s.codigo == codigo), None)

    @property
    def forma_de_pagamento(self) -> Union[str, Indisponivel]:
        """🔴 DAS PARCELAS. O cabeçalho do fornecedor não decide isto (§8.3)."""
        formas = [
            str(p.forma_de_pagamento.valor).strip()
            for p in self.parcelas
            if p.forma_de_pagamento.tem_valor
        ]
        if not formas:
            return INDISPONIVEL
        unicas = sorted(set(formas))
        return unicas[0] if len(unicas) == 1 else " / ".join(unicas)


@dataclass(frozen=True)
class ApoliceNaLista:
    """A apólice na LISTAGEM: o pouco que a listagem conhece, classificado.

    ⚠️ A **ESCOLHA** (found / sem_vigente / ambiguous, `auto_selected_reason`,
    ramo deduzido) é do **BLOCO B**. O BLOCO A entrega a lista classificada.
    """

    apolice_ref: str
    seguradora: SeguradoraCanonica
    ramo: RamoCanonico
    vigencia: Vigencia
    numero_humano: Optional[str] = None
    sinais: Tuple[Sinal, ...] = ()


@dataclass(frozen=True)
class ListaDeApolices:
    itens: Tuple[ApoliceNaLista, ...] = ()
    total: int = 0
    historico_oculto: int = 0
    cliente_ref: Optional[str] = None
    sinais: Tuple[Sinal, ...] = ()
    provider_key: str = ""

    @property
    def vigentes(self) -> Tuple[ApoliceNaLista, ...]:
        return tuple(a for a in self.itens if a.vigencia.situacao == "VIGENTE")


@dataclass(frozen=True)
class ResultadoDeBusca:
    """O cliente encontrado (ou não). ⛔ Nome/documento **não** moram aqui."""

    encontrado: bool
    cliente_ref: Optional[str] = None
    quantidade_de_apolices: int = 0
    motivo: Optional[str] = None
    sinais: Tuple[Sinal, ...] = ()
    provider_key: str = ""


Capacidade = Literal["SUPORTADA", "PARCIAL", "INDISPONIVEL", "DESCONHECIDA"]
_CAPACIDADES: Tuple[str, ...] = ("SUPORTADA", "PARCIAL", "INDISPONIVEL", "DESCONHECIDA")

#: As cinco operações do contrato — a ordem em que `capacidades()` as declara.
OPERACOES: Tuple[str, ...] = (
    "buscar_cliente",
    "listar_apolices",
    "detalhar_apolice",
    "documento_oficial",
    "parcelas_em_aberto",
)


@dataclass(frozen=True)
class CapacidadeDoProvider:
    """O que este provider CONSEGUE entregar, por operação.

    🔴 `DESCONHECIDA` lê-se *"não verificado"*, **jamais** *"não tem"*. É o que
    permite ao `PdfOnlyProvider` existir sem mentir, e ao adaptador Agger
    nascer amanhã sem quebrar o compositor.
    """

    provider_key: str
    por_operacao: Dict[str, Capacidade] = field(default_factory=dict)
    notas: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        faltando = [op for op in OPERACOES if op not in self.por_operacao]
        if faltando:
            raise ValueError(
                "capacidades() de %r não declara: %s. "
                "Operação não declarada vira 'descoberta por ausência', e "
                "ausência lida como zero é o defeito que esta porta existe "
                "para matar." % (self.provider_key, ", ".join(faltando))
            )
        ruins = {op: v for op, v in self.por_operacao.items() if v not in _CAPACIDADES}
        if ruins:
            raise ValueError(
                "capacidades() de %r usa valor fora de %r: %r"
                % (self.provider_key, list(_CAPACIDADES), ruins)
            )

    def de(self, operacao: str) -> Capacidade:
        return self.por_operacao.get(operacao, "DESCONHECIDA")  # type: ignore[return-value]


# ===========================================================================
# NORMALIZAÇÃO DE RÓTULO — e o arquivo de sinônimos, que é REVISÁVEL POR GENTE
# ===========================================================================
_ARQUIVO_DE_ROTULOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rotulos_de_cobertura.json")
_RE_PONTUACAO = re.compile(r"[^0-9a-z]+")
_CACHE_DE_ROTULOS: Optional[Dict[str, Any]] = None


def _sem_acento(texto: Any) -> str:
    normalizado = unicodedata.normalize("NFKD", str(texto or ""))
    return "".join(ch for ch in normalizado if not unicodedata.combining(ch))


def normalizar_rotulo(rotulo: Any) -> str:
    """`"RESP. CIVIL SIND. DE CON."` → `"resp civil sind de con"`.

    Minúsculas · sem acento · pontuação vira espaço · espaços colapsados.
    ⛔ Nenhuma abreviação é expandida por REGRA: expansão é sempre uma LINHA de
    `rotulos_de_cobertura.json`, datada e com critério.
    """
    texto = _sem_acento(rotulo).lower()
    texto = _RE_PONTUACAO.sub(" ", texto)
    return " ".join(texto.split())


def mapa_de_rotulos(caminho: str = "") -> Dict[str, Any]:
    """Lê (e memoriza) `rotulos_de_cobertura.json`. Ausente → grupos vazios."""
    global _CACHE_DE_ROTULOS
    alvo = caminho or _ARQUIVO_DE_ROTULOS
    if not caminho and _CACHE_DE_ROTULOS is not None:
        return _CACHE_DE_ROTULOS
    indice: Dict[str, Any] = {"por_rotulo": {}, "grupos": {}, "medido_em": None}
    try:
        with io.open(alvo, encoding="utf-8") as fh:
            bruto = json.load(fh)
    except Exception as exc:  # noqa: BLE001 — o casamento por igualdade continua valendo
        logger.warning("[APOLICE] rotulos_de_cobertura.json indisponivel (%s)", type(exc).__name__)
        if not caminho:
            _CACHE_DE_ROTULOS = indice
        return indice
    indice["medido_em"] = bruto.get("medido_em")
    for grupo in bruto.get("grupos") or []:
        gid = str(grupo.get("id") or "").strip()
        if not gid:
            continue
        rotulos = [normalizar_rotulo(r) for r in (grupo.get("rotulos") or [])]
        rotulos = [r for r in rotulos if r]
        indice["grupos"][gid] = {
            "nome_canonico": grupo.get("nome_canonico"),
            "rotulos": rotulos,
            "criterio": grupo.get("criterio"),
        }
        for r in rotulos:
            anterior = indice["por_rotulo"].get(r)
            if anterior and anterior != gid:
                # ⚠️ Um rótulo em dois grupos torna o casamento não-determinístico.
                # Isso é defeito do ARQUIVO, e ele fala alto em vez de escolher.
                logger.warning("[APOLICE] rotulo %r em dois grupos: %r e %r", r, anterior, gid)
                continue
            indice["por_rotulo"][r] = gid
    if not caminho:
        _CACHE_DE_ROTULOS = indice
    return indice


def grupo_de_rotulo(rotulo: Any, *, mapa: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """O id do grupo declarado deste rótulo — ou `None`. **Nunca por substring.**"""
    indice = mapa if mapa is not None else mapa_de_rotulos()
    return indice.get("por_rotulo", {}).get(normalizar_rotulo(rotulo))


def _chave_de_casamento(rotulo: Any, mapa: Optional[Dict[str, Any]] = None) -> str:
    """A chave sob a qual duas linhas se encontram: o grupo, ou o normalizado."""
    gid = grupo_de_rotulo(rotulo, mapa=mapa)
    return ("grupo:" + gid) if gid else ("rotulo:" + normalizar_rotulo(rotulo))


# ===========================================================================
# FRANQUIA — a comparação que decide se houve divergência
# ===========================================================================
_RE_FRANQUIA_PCT_VALOR = re.compile(
    r"(?P<pct>\d{1,3}(?:[.,]\d{1,2})?)\s*%?\s*(?:-\s*)?(?:sobre[^0-9]{0,60}?)?"
    r"(?:m[ií]nimo\s*(?:de\s*)?)?(?:r\$\s*)?"
    r"(?P<valor>\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}|\d+(?:\.\d{3})+)",
    re.IGNORECASE,
)
_SEM_FRANQUIA = ("sem franquia", "0", "0,00", "0.00", "nao ha franquia", "isento")


def _franquia_comparavel(texto: Any) -> Any:
    """`"20 - R$ 4.000,00"` e `"20 4.000,00"` viram o MESMO valor comparável.

    📊 É o que impede 7 divergências FALSAS na Allianz do golden: o cadastro
    escreve `20 - R$ 4.000,00` e o PDF escreve `20 4.000,00` — a mesma franquia
    com duas tipografias. Sem isto, o corretor leria "as fontes discordam" em 7
    coberturas que concordam, e a divergência de verdade (HDI Danos Elétricos,
    550 x 600) se perderia no meio.

    Devolve `("pct_valor", pct, valor)`, `"sem_franquia"`, ou o texto
    normalizado quando a forma não for reconhecida (ex.: `"- 168 Hrs"`, que é
    CARÊNCIA e não franquia, e por isso continua comparável só como texto).
    """
    if texto is None or isinstance(texto, Indisponivel):
        return None
    if isinstance(texto, Decimal):
        return ("valor", Decimal(texto).quantize(_DOIS_CENTAVOS))
    bruto = str(texto or "").strip()
    if not bruto:
        return None
    normal = normalizar_rotulo(bruto)
    if normal in (normalizar_rotulo(s) for s in _SEM_FRANQUIA):
        return "sem_franquia"
    achado = _RE_FRANQUIA_PCT_VALOR.search(bruto)
    if achado:
        pct_txt = achado.group("pct").replace(",", ".")
        valor = dinheiro_de_texto(achado.group("valor"))
        try:
            pct = Decimal(pct_txt).quantize(_DOIS_CENTAVOS)
        except (InvalidOperation, ValueError):
            pct = INDISPONIVEL  # type: ignore[assignment]
        return ("pct_valor", pct, valor)
    somente_valor = dinheiro_de_texto(bruto)
    if not isinstance(somente_valor, Indisponivel):
        return ("valor", somente_valor)
    return normal


# ===========================================================================
# VIGÊNCIA — a classificação pura, com o "hoje" como PARÂMETRO
# ===========================================================================
_FORMATOS_DE_DATA = ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%Y", "%Y/%m/%d")


def data_de(valor: Any) -> Optional[date]:
    """`"25/08/2026"` / `"2026-08-25"` / `date` → `date`. Ilegível → `None`."""
    if valor is None or isinstance(valor, Indisponivel):
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor or "").strip()
    if not texto:
        return None
    texto = texto.split("T")[0].split(" ")[0]
    for formato in _FORMATOS_DE_DATA:
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def classificar_vigencia(
    inicio: Any,
    fim: Any,
    cancelado: Any = False,
    hoje: Optional[date] = None,
) -> Vigencia:
    """`VIGENTE | VENCIDA | CANCELADA | FUTURA | DESCONHECIDA` — função PURA.

    🔴 `hoje` é PARÂMETRO. Uma classificação que chama `date.today()` por dentro
    não tem como ser testada sem viajar no tempo, e a data da corretora não é a
    data do servidor.

    ⚠️ O `policy_status`/`sit_renovacao_txt` do fornecedor **não decide**: ele
    entra como SINAL. 📊 As duas apólices do golden trazem
    `status_cru_do_fornecedor = "Recebido e não entregue ao cliente"` — um
    estado de ENTREGA DE DOCUMENTO, que nada diz sobre vigência, e que uma
    leitura ingênua transformaria em "não está valendo".
    """
    d_inicio = data_de(inicio)
    d_fim = data_de(fim)
    if _verdadeiro(cancelado):
        return Vigencia(inicio=d_inicio, fim=d_fim, situacao="CANCELADA")
    referencia = hoje or date.today()
    if d_inicio is None and d_fim is None:
        return Vigencia(inicio=None, fim=None, situacao="DESCONHECIDA")
    if d_fim is not None and d_fim < referencia:
        return Vigencia(inicio=d_inicio, fim=d_fim, situacao="VENCIDA")
    if d_inicio is not None and d_inicio > referencia:
        return Vigencia(inicio=d_inicio, fim=d_fim, situacao="FUTURA")
    if d_fim is None:
        # Começou e não se sabe quando acaba: não é "vigente", é DESCONHECIDA.
        return Vigencia(inicio=d_inicio, fim=None, situacao="DESCONHECIDA")
    return Vigencia(inicio=d_inicio, fim=d_fim, situacao="VIGENTE")


_TRUTHY = {"t", "true", "s", "sim", "y", "yes", "1"}


def _verdadeiro(valor: Any) -> bool:
    if isinstance(valor, bool):
        return valor
    if valor is None:
        return False
    return str(valor).strip().lower() in _TRUTHY


# ===========================================================================
# O NÚMERO HUMANO — uma regra, no lugar onde ela pertence (BLOCO B)
# ===========================================================================
#
# 📊 Medido em 14/09/2026: `infocap_tool.py:582` e `:622` importavam
# `_display_policy_number` de `app/api/infocap_connector.py` — 2 dos 3 imports
# que deixavam o G1a de `test_a_porta_nao_vaza_o_fornecedor.py` vermelho. A
# regra não é do fornecedor: "este número serve para o corretor dizer em voz
# alta?" vale para Agger, Quiver ou qualquer outro. Ela sobe para a porta, e o
# conector passa a DELEGAR — nunca a ter uma segunda cópia (CLAUDE.md §5).
#
#: O que a fonte manda quando NÃO tem número, e que nunca pode virar resposta.
NUMEROS_QUE_NAO_SAO_NUMERO = {"", "0", "00", "000", "0000", "null", "none", "n/a", "na", "-"}

#: 🔴 Frase NEUTRA de propósito: a porta não nomeia fornecedor. O conector
#: passa a sua própria frase por `ausente=` e continua dizendo "InfoCap".
NUMERO_NAO_RETORNADO = "numero nao retornado pela fonte"

_RE_SO_ALFANUMERICO = re.compile(r"[^0-9A-Za-z]")

#: As chaves em que o número humano pode vir, na ordem de preferência.
CHAVES_DE_NUMERO_HUMANO = ("policy_number", "numapo", "masked_policy_number")


def normalizar_numero_humano(valor: Any) -> str:
    """`"31.252/0261-1492"` → `"3125202611492"`. Só para COMPARAR, nunca exibir."""
    return _RE_SO_ALFANUMERICO.sub("", str(valor or "")).upper()


def numero_humano_valido(valor: Any) -> bool:
    """`"0"`, `"null"`, `"000"` e vazio NÃO são número de apólice.

    ⚠️ `set(normalizado) == {"0"}` pega `"00000"` — a fonte devolve zeros de
    preenchimento, e um "0" lido como número faz o corretor ditar um zero ao
    segurado.
    """
    cru = str(valor or "").strip()
    if cru.lower() in NUMEROS_QUE_NAO_SAO_NUMERO:
        return False
    normalizado = normalizar_numero_humano(cru)
    if not normalizado:
        return False
    if normalizado.isdigit() and set(normalizado) == {"0"}:
        return False
    return True


def numero_humano_de(record: Any, *, ausente: str = NUMERO_NAO_RETORNADO) -> str:
    """O número que se diz em voz alta — ou a frase que assume a ausência.

    Aceita `ApoliceNaLista`, `Apolice` ou o dicionário sanitizado do adaptador,
    porque os três atravessam esta função nos dois lados da fronteira.
    """
    if isinstance(record, (ApoliceNaLista, Apolice)):
        valor: Any = record.numero_humano
    elif isinstance(record, dict):
        valor = next((record.get(c) for c in CHAVES_DE_NUMERO_HUMANO if record.get(c)), None)
    else:
        valor = getattr(record, "numero_humano", None)
    return str(valor).strip() if numero_humano_valido(valor) else ausente


def opcoes_em_texto(matches: Any, *, include_internal_ref: bool = False) -> str:
    """As opções de apólice em texto, numeradas. **Uma só implementação.**

    📊 `infocap_tool.py:650` importava `_format_policy_options_for_summary` do
    conector — o terceiro import do G1a. A formatação de uma LISTA DE ESCOLHA
    não é tradução de fornecedor: é a pergunta que o produto faz. Ela sobe, e o
    conector delega.

    ⚠️ O corte em 10 aqui é de TEXTO (teto de prompt), nunca de decisão: quem
    decide é `escolher_apolice`, que lê a lista inteira (proposta §6.1).
    """
    linhas = ["Opcoes de apolice encontradas:"]
    for indice, bruto in enumerate(list(matches or [])[:10], start=1):
        situacao: str
        if isinstance(bruto, ApoliceNaLista):
            ref = bruto.apolice_ref or "-"
            num = numero_humano_de(bruto, ausente=NUMERO_NAO_RETORNADO)
            seguradora = bruto.seguradora.nome_listado or "-"
            ramo = bruto.ramo.nome_humano or bruto.ramo.abreviatura or "-"
            de = bruto.vigencia.inicio.strftime("%d/%m/%Y") if bruto.vigencia.inicio else "-"
            ate = bruto.vigencia.fim.strftime("%d/%m/%Y") if bruto.vigencia.fim else "-"
            situacao = str(bruto.vigencia.situacao)
        elif isinstance(bruto, dict):
            ref = bruto.get("policy_locator_ref") or bruto.get("policy_ref") or "-"
            num = numero_humano_de(bruto, ausente=NUMERO_NAO_RETORNADO)
            seguradora = bruto.get("insurer_key") or "-"
            ramo = bruto.get("product") or "-"
            de = bruto.get("valid_from") or "-"
            ate = bruto.get("valid_to") or "-"
            situacao = bruto.get("policy_status") or "-"
        else:
            continue
        linha = (
            "%d. Seguradora: %s; Produto/ramo: %s; Vigencia: %s a %s; Status: %s; Numero: %s"
            % (indice, seguradora, ramo, de, ate, situacao, num)
        )
        if include_internal_ref:
            linha += "; policy_ref interno: %s" % ref
        linhas.append(linha)
    return "\n".join(linhas)


# ===========================================================================
# A ESCOLHA — ela acontece na PORTA, e DIZ POR QUÊ (proposta §6.1/§6.2)
# ===========================================================================
#
# 🔴 CLAUDE.md §9.5: "uma constante que escolhe entre alternativas de conteúdo
# precisa dizer POR QUE está certa, escrito ao lado dela". Aqui a alternativa é
# uma APÓLICE, e o "ao lado dela" é `auto_selected_reason` — texto humano, que
# o corretor lê e consegue contestar.
#
# ⚠️ A regra já existia e já estava CERTA: `policy_answer_composer.py:279-300`
# calcula vigência pela DATA desde 10/07/2026, porque 📊 a fonte marca "ativo"
# em apólice vencida há anos. O que estava errado era o LUGAR: ela rodava no
# compositor, depois de o conector já ter devolvido `ambiguous_policy` — tarde
# demais, e só para quem chegava lá. Agora o compositor DELEGA para cá.

#: 🔴 As situações que a listagem NÃO mostra como opção. `FUTURA` e
#: `DESCONHECIDA` ficam de fora desta lista de propósito: uma apólice que ainda
#: vai começar, ou cuja data a fonte não devolveu, **não é histórico** — dizer
#: "vencida" sobre ela seria mentir para o corretor.
SITUACOES_OCULTAS = ("VENCIDA", "CANCELADA")

#: 🔴 O que NÃO é histórico e também **NÃO é vigente**. Até 14/09/2026 estas
#: duas situações eram simplesmente elegíveis, e `_motivo_da_escolha` escrevia
#: *"única apólice vigente do cliente"* sobre elas — uma apólice que **começa
#: mês que vem** era anunciada ao corretor como valendo hoje, e uma apólice sem
#: fim de vigência na fonte, idem. As duas frases chegam ao corretor; a segunda
#: chega ao segurado pelo atendimento.
#:
#: ```
#: há VIGENTE      ->  FUTURA e DESCONHECIDA ficam FORA das opções e do `found`,
#:                     e o motivo DIZ que elas existem (não somem)
#: não há VIGENTE  ->  elas continuam elegíveis — a FUTURA é a apólice que VAI
#:                     valer, e a DESCONHECIDA é a única que o cliente tem —
#:                     mas a palavra "vigente" não aparece no motivo
#: ```
#:
#: ⚠️ Elas continuam fora de `SITUACOES_OCULTAS`: não entram em
#: `historico_oculto`, porque histórico é o que já passou.
SITUACOES_QUE_NAO_SAO_VIGENTES = ("FUTURA", "DESCONHECIDA")

#: As famílias de ramo que a conversa consegue nomear. ⛔ Não é catálogo de
#: seguradora nem de ramo SUSEP (esse é `susep_ses_provider`): é o AGRUPAMENTO
#: que responde "a apólice do carro" quando a fonte diz `AUTO`, `AUTOM` ou
#: `AUTOMOVEL`. Cada linha é uma abreviatura VISTA no acervo ou o nome humano
#: correspondente; nada é derivado por prefixo (📊 SPEC-094.1: `SURA` casa
#: dentro de `ASSURANCE` — casamento parcial produz catálogo errado).
FAMILIAS_DE_RAMO: Dict[str, Tuple[str, ...]] = {
    "auto": ("auto", "autom", "automovel", "automoveis", "auto frota", "frota", "rcfv", "carro"),
    "resi": ("resi", "resid", "residencial", "residencia", "casa"),
    "cond": ("cond", "condominio", "condominios"),
    "vida": ("vida", "vind", "vgrp", "vida individual", "vida em grupo", "vidaind"),
    "viag": ("viag", "viagem"),
    "empr": ("empr", "empresarial", "empresa"),
    "saud": ("saud", "saude"),
}

_FAMILIA_POR_ABREVIATURA: Dict[str, str] = {
    normalizar_rotulo(sinonimo): familia
    for familia, sinonimos in FAMILIAS_DE_RAMO.items()
    for sinonimo in sinonimos
}

#: O nome que se diz ao corretor, por família. 💭 copy — nunca citável como fato.
NOME_DA_FAMILIA: Dict[str, str] = {
    "auto": "auto", "resi": "residencial", "cond": "condomínio",
    "vida": "vida", "viag": "viagem", "empr": "empresarial", "saud": "saúde",
}


def familia_de_ramo(ramo: Any) -> Optional[str]:
    """`RamoCanonico("VIND")` / `"residencial"` → `"vida"` / `"resi"`.

    `None` quando a abreviatura não está no agrupamento — e `None` significa
    *"não sei"*, nunca *"não é"*: quem chama trata como ausência de sinal.
    """
    if ramo is None:
        return None
    if isinstance(ramo, RamoCanonico):
        candidatos = [ramo.abreviatura, ramo.nome_humano]
    else:
        candidatos = [ramo]
    for candidato in candidatos:
        chave = normalizar_rotulo(candidato)
        if chave and chave in _FAMILIA_POR_ABREVIATURA:
            return _FAMILIA_POR_ABREVIATURA[chave]
    return None


StatusDaEscolha = Literal["found", "sem_vigente", "ambiguous_policy", "nenhuma"]


@dataclass(frozen=True)
class Escolha:
    """O resultado da escolha — e o PORQUÊ dela, em português.

    ```
    found             uma apólice. `apolice` preenchida, `auto_selected_reason` diz por quê
    ambiguous_policy  2+ do MESMO ramo. `opcoes` JÁ FILTRADAS: só vigentes, só do ramo
    sem_vigente       havia apólices, nenhuma vigente. `frase_sem_vigente` é a resposta
    nenhuma           a fonte não devolveu apólice alguma
    ```

    🔴 `opcoes` nunca contém vencida ou cancelada. É a regra inteira desta
    unidade: *vencida nunca vira opção*.
    """

    status: StatusDaEscolha
    apolice: Optional[ApoliceNaLista] = None
    opcoes: Tuple[ApoliceNaLista, ...] = ()
    auto_selected_reason: Optional[str] = None
    historico_oculto: int = 0
    ultima_vigente: Optional[ApoliceNaLista] = None
    frase_sem_vigente: Optional[str] = None


def _dia_br(valor: Optional[date]) -> str:
    return valor.strftime("%d/%m/%Y") if isinstance(valor, date) else "data não informada"


def _nome_do_ramo(apolice: ApoliceNaLista, humanizar_ramo: Any = None) -> str:
    familia = familia_de_ramo(apolice.ramo)
    if familia:
        return NOME_DA_FAMILIA.get(familia, familia)
    if callable(humanizar_ramo):
        rotulo = str(humanizar_ramo(apolice.ramo.abreviatura) or "").strip()
        if rotulo and rotulo.upper() != UNKNOWN:
            return rotulo.lower()
    bruto = apolice.ramo.nome_humano or apolice.ramo.abreviatura or ""
    return bruto.lower() if bruto and bruto != UNKNOWN else "seguro"


def _nome_da_seguradora(apolice: ApoliceNaLista, humanizar_seguradora: Any = None) -> str:
    bruto = apolice.seguradora.nome_listado or apolice.seguradora.chave or ""
    if callable(humanizar_seguradora):
        rotulo = str(humanizar_seguradora(bruto) or "").strip()
        if rotulo:
            return rotulo
    return bruto or "seguradora não informada"


def _motivo_da_escolha(
    escolhida: ApoliceNaLista,
    *,
    elegiveis: Sequence[ApoliceNaLista],
    ocultas: Sequence[ApoliceNaLista],
    historico_oculto: int,
    familia_pedida: Optional[str],
    humanizar_seguradora: Any,
    humanizar_ramo: Any,
    adiadas: Sequence[ApoliceNaLista] = (),
) -> str:
    """O texto que vai ao corretor. 💭 copy — legível, sem código, sem chave.

    🔴 Ele precisa passar na régua de língua que já existe
    (`problemas_de_lingua`): nada de `snake_case`, nada de `chave@versao`.

    🔴 **A palavra "vigente" só aparece quando a apólice É vigente.** Ela é a
    única palavra do motivo que o corretor repete ao segurado — e dizê-la sobre
    uma apólice que começa mês que vem é prometer cobertura que não existe.
    """
    ramo = _nome_do_ramo(escolhida, humanizar_ramo)
    familia_da_escolhida = familia_de_ramo(escolhida.ramo)
    vigente = escolhida.vigencia.situacao == "VIGENTE"
    if familia_pedida and familia_da_escolhida != familia_pedida:
        pedido = NOME_DA_FAMILIA.get(familia_pedida, familia_pedida)
        base = ("única apólice %sdo cliente, e ela é de %s — não há apólice "
                "vigente de %s no sistema de gestão"
                % ("vigente " if vigente else "", ramo, pedido))
    elif familia_pedida:
        base = ("única apólice vigente de %s" % ramo) if vigente else \
               ("única apólice do cliente, de %s" % ramo)
    elif len(elegiveis) == 1:
        base = ("única apólice vigente do cliente, de %s" % ramo) if vigente else \
               ("única apólice do cliente, de %s" % ramo)
    else:
        base = ("apólice vigente de %s" % ramo) if vigente else \
               ("apólice do cliente, de %s" % ramo)

    # 🔴 A situação, dita em português, quando ela NÃO é "vigente". 💭 copy.
    if escolhida.vigencia.situacao == "FUTURA":
        base += "; começa a valer em %s" % _dia_br(escolhida.vigencia.inicio)
    elif escolhida.vigencia.situacao == "DESCONHECIDA":
        base += "; o sistema de gestão não informa o fim da vigência"

    # ⚠️ As que existem e NÃO entraram: elas não são histórico, então não podem
    # ser contadas como "ocultadas" — mas sumir com elas em silêncio é o mesmo
    # defeito da §6.1 com outro nome.
    futuras = [a for a in adiadas if a.vigencia.situacao == "FUTURA"]
    sem_data = [a for a in adiadas if a.vigencia.situacao == "DESCONHECIDA"]
    if len(futuras) == 1:
        base += "; há 1 apólice que começa em %s" % _dia_br(futuras[0].vigencia.inicio)
    elif futuras:
        base += "; há %d apólices que ainda vão começar a valer" % len(futuras)
    if len(sem_data) == 1:
        base += "; há 1 apólice sem fim de vigência no sistema de gestão"
    elif sem_data:
        base += "; há %d apólices sem fim de vigência no sistema de gestão" % len(sem_data)

    # 🔴 A cauda conta `historico_oculto`, NUNCA só as vencidas que a resposta
    # trouxe. 📊 A empresa de 11 apólices devolve 10 linhas, 9 delas vencidas:
    # dizer "9 vencidas ocultadas" esconderia a 11ª, que é justamente a que o
    # truncamento comeu. O número honesto é 10.
    vencidas = [a for a in ocultas if a.vigencia.situacao == "VENCIDA"]
    canceladas = [a for a in ocultas if a.vigencia.situacao == "CANCELADA"]
    if historico_oculto <= 0:
        return base
    if historico_oculto == 1 and len(vencidas) == 1:
        return base + "; a %s venceu em %s" % (
            _nome_da_seguradora(vencidas[0], humanizar_seguradora),
            _dia_br(vencidas[0].vigencia.fim))
    if historico_oculto == 1 and len(canceladas) == 1:
        return base + "; a %s foi cancelada" % _nome_da_seguradora(canceladas[0], humanizar_seguradora)
    return base + "; %d apólice%s antiga%s ocultada%s" % (
        historico_oculto,
        "" if historico_oculto == 1 else "s",
        "" if historico_oculto == 1 else "s",
        "" if historico_oculto == 1 else "s",
    )


def _frase_sem_vigente(
    ultima: Optional[ApoliceNaLista], *, humanizar_seguradora: Any = None
) -> str:
    """💭 A resposta da §6.2, palavra por palavra do diagnóstico §3.

    ⛔ Ela **não** é "não encontrei". O cliente TEM histórico, e esconder isso
    faz o corretor achar que a busca falhou — e refazer a busca.
    """
    fim = ("Hoje não há nenhuma apólice vigente deste cliente no sistema de gestão. "
           "Quer que eu liste o histórico?")
    if ultima is None:
        return "Este cliente tem apólices no sistema de gestão, mas nenhuma vigente hoje. " + \
               "Quer que eu liste o histórico?"
    return "A última apólice vigente foi a %s, da %s, que valeu até %s. %s" % (
        numero_humano_de(ultima, ausente="sem número na fonte"),
        _nome_da_seguradora(ultima, humanizar_seguradora),
        _dia_br(ultima.vigencia.fim),
        fim,
    )


def escolher_apolice(
    lista: ListaDeApolices,
    *,
    ramo: Any = None,
    hoje: Optional[date] = None,
    humanizar_seguradora: Any = None,
    humanizar_ramo: Any = None,
) -> Escolha:
    """A apólice certa, ou a pergunta certa — e sempre o porquê (proposta §6.1).

    ```
    sobrou 1 vigente                    ->  found + auto_selected_reason + historico_oculto
    1 vigente + 1 futura                ->  found NA VIGENTE; a futura é DITA, não oferecida
    0 vigente, só futura/sem data       ->  found nela, e o motivo NÃO diz "vigente"
    0 vigente e N vencidas              ->  sem_vigente + ultima_vigente + a frase da §6.2
    2+ do MESMO ramo                    ->  ambiguous_policy com as opções JÁ FILTRADAS
    2+ de ramos DIFERENTES, com ramo    ->  aplica o ramo e recomeça
    2+ de ramos DIFERENTES, sem ramo    ->  ambiguous_policy (pergunta UMA vez)
    ```

    🔴 **`hoje` é parâmetro** e desce para a classificação, como em
    `classificar_vigencia`: a data da corretora não é a data do servidor.

    ⚠️ A lista tem de vir com as VENCIDAS dentro (`incluir_vencidas=True`), ou
    `ultima_vigente` não tem como existir e a frase da §6.2 sai sem a data. A
    função filtra; ela não pede à fonte que filtre por ela.

    📊 `lista.total` é `documents_count` — a contagem CHEIA da fonte, não
    `len(matches)`. É o que impede "a única vigente está na posição 11" de
    virar "o cliente não tem apólice vigente" (proposta §6.1, emenda 2).
    """
    itens = tuple(lista.itens or ())
    total = int(lista.total or len(itens))

    # 🔴 A reclassificação com o `hoje` recebido. Sem ela, uma lista montada com
    # o "hoje" do servidor decidiria com a data errada — e a escolha é do
    # produto, não do relógio de quem montou a lista.
    if hoje is not None:
        itens = tuple(
            replace(a, vigencia=classificar_vigencia(
                a.vigencia.inicio, a.vigencia.fim,
                a.vigencia.situacao == "CANCELADA", hoje=hoje))
            for a in itens
        )

    elegiveis = tuple(a for a in itens if a.vigencia.situacao not in SITUACOES_OCULTAS)
    ocultas = tuple(a for a in itens if a.vigencia.situacao in SITUACOES_OCULTAS)
    # 🔴 `total - elegíveis`, nunca `total - len(itens)`: o truncamento da fonte
    # e as vencidas são a MESMA coisa para quem pergunta — apólice que existe e
    # não está na resposta. Uma conta que ignorasse o truncamento diria
    # "3 ocultadas" quando são 14 (proposta §6.1).
    historico_oculto = max(0, total - len(elegiveis))

    if not itens and total <= 0:
        return Escolha(status="nenhuma", historico_oculto=0)

    if not elegiveis:
        vencidas = [a for a in ocultas if a.vigencia.fim is not None]
        ultima = max(vencidas, key=lambda a: a.vigencia.fim) if vencidas else None  # type: ignore[arg-type,return-value]
        return Escolha(
            status="sem_vigente",
            historico_oculto=historico_oculto,
            ultima_vigente=ultima,
            frase_sem_vigente=_frase_sem_vigente(ultima, humanizar_seguradora=humanizar_seguradora),
        )

    # 🔴 A VIGENTE VENCE A FUTURA. Havendo apólice vigente, a que ainda vai
    # começar (ou a que a fonte não datou) não entra na escolha nem nas opções:
    # ela seria oferecida ao corretor como se valesse hoje. Não havendo
    # vigente, elas continuam elegíveis — é o que o cliente tem — e o motivo
    # diz a verdade sobre cada uma (`_motivo_da_escolha`).
    vigentes = tuple(a for a in elegiveis if a.vigencia.situacao == "VIGENTE")
    adiadas: Tuple[ApoliceNaLista, ...] = ()
    if vigentes:
        adiadas = tuple(a for a in elegiveis
                        if a.vigencia.situacao in SITUACOES_QUE_NAO_SAO_VIGENTES)
    pool = vigentes if vigentes else elegiveis

    familia_pedida = familia_de_ramo(ramo)
    candidatas = pool
    if ramo is not None:
        if familia_pedida:
            do_ramo = tuple(a for a in pool if familia_de_ramo(a.ramo) == familia_pedida)
        else:
            alvo = normalizar_rotulo(ramo.abreviatura if isinstance(ramo, RamoCanonico) else ramo)
            do_ramo = tuple(a for a in pool if normalizar_rotulo(a.ramo.abreviatura) == alvo)
        # ⚠️ Ramo que não casa com NENHUMA vigente não elimina a resposta: ele
        # deixa de filtrar, e o motivo passa a DIZER que não há vigente daquele
        # ramo. Filtrar até zero responderia "não há apólice vigente" a um
        # cliente que tem — a mentira que a §6.2 existe para impedir.
        if do_ramo:
            candidatas = do_ramo

    if len(candidatas) == 1:
        escolhida = candidatas[0]
        return Escolha(
            status="found",
            apolice=escolhida,
            auto_selected_reason=_motivo_da_escolha(
                escolhida, elegiveis=pool, ocultas=ocultas,
                historico_oculto=historico_oculto, familia_pedida=familia_pedida,
                humanizar_seguradora=humanizar_seguradora, humanizar_ramo=humanizar_ramo,
                adiadas=adiadas,
            ),
            historico_oculto=historico_oculto,
        )

    return Escolha(
        status="ambiguous_policy",
        opcoes=candidatas,
        historico_oculto=historico_oculto,
    )


# ===========================================================================
# `reconciliar(corp, pdf)` — PURO, e mora na PORTA (proposta §5.5)
# ===========================================================================
#
# ⚠️ Por que aqui e não no adaptador: a escolha "o documento vence em cobertura"
# é **decisão do Founder** (D-PILOTO-11), não tradução de fornecedor. O próprio
# padrão Anti-Corruption Layer avisa: *"focus the anti-corruption layer on
# translation logic. Avoid placing business rules or orchestration in the
# layer."* Regra de negócio na camada de tradução obrigaria o próximo
# adaptador (Agger, Quiver) a reimplementar a decisão.
#
#: Quem vence, por campo. 🔴 Divergência NÃO escolhe: as duas ficam.
VENCE_O_DOCUMENTO = ("cobertura", "limite", "franquia", "clausula", "exclusao", "plano", "nivel")
VENCE_O_SISTEMA_DE_GESTAO = ("parcela", "quitacao", "status", "vigencia", "renovacao", "sinistro")



def _diferenca(a: Any, b: Any) -> Optional[Decimal]:
    if isinstance(a, Decimal) and isinstance(b, Decimal):
        return abs(a - b)
    return None


def _divergem_em_dinheiro(a: Any, b: Any) -> bool:
    """Só diverge quando os DOIS lados têm valor e a diferença passa da tolerância."""
    if isinstance(a, Indisponivel) or isinstance(b, Indisponivel) or a is None or b is None:
        return False
    delta = _diferenca(a, b)
    if delta is None:
        return str(a).strip() != str(b).strip()
    return delta > TOLERANCIA_DE_PREMIO


def reconciliar(corp: Apolice, pdf: Optional[ApoliceDocumental]) -> Apolice:
    """Casa cobertura por rótulo normalizado. **Puro: entra dois, sai um.**

    Sem I/O, sem LLM, sem rede — é o que torna o guarda barato.

    | campo | vence | por quê |
    |---|---|---|
    | cobertura, limite, franquia, cláusula, exclusão, plano | **documento** | 📊 o cadastro da HDI tinha 6 de 10 linhas e 77% do prêmio faltando |
    | parcela, quitação, status, vigência, renovação, sinistro | **sistema de gestão** | é o que muda todo dia; o PDF congela na emissão |

    O contador de prêmio acende sobre o **CADASTRO**, e continua aceso depois
    da reconciliação: o sinal é sobre o cadastro estar incompleto, não sobre a
    resposta estar incompleta.
    """
    mapa = mapa_de_rotulos()
    # 🔴 `reconciliar` e IDEMPOTENTE, e as duas metades da regra importam:
    #    o sinal recalculado SUBSTITUI o anterior (nao duplica), e quando nao ha
    #    o que recalcular o anterior FICA (nao some).
    #    ⚠️ Reconciliar duas vezes nao e hipotese: depois da primeira passada as
    #    coberturas carregam origem `documento_oficial`, entao nao sobra premio
    #    de CADASTRO para somar. Apagar o sinal ali faria a apolice com 77% do
    #    premio faltando no cadastro passar por completa — e um corretor que le
    #    o mesmo aviso duas vezes aprende a nao ler nenhum.
    sinais: List[Sinal] = [s for s in corp.sinais if s.codigo != "rotulo_ambiguo"]

    sinal_premio = _contador_de_premio(corp)
    if sinal_premio is not None:
        sinais = [s for s in sinais if s.codigo != "cadastro_incompleto"]
        sinais.append(sinal_premio)

    if pdf is None or not pdf.linhas:
        return replace(corp, sinais=tuple(sinais))

    # --- o índice do documento, por chave de casamento ----------------------
    por_chave: Dict[str, List[LinhaDeCoberturaDoDocumento]] = {}
    for do_documento in pdf.linhas:
        por_chave.setdefault(
            _chave_de_casamento(do_documento.rotulo, mapa), []).append(do_documento)

    usadas: set = set()
    coberturas: List[Cobertura] = []

    for cobertura in corp.coberturas:
        chave = _chave_de_casamento(cobertura.rotulo, mapa)
        candidatas = [l for l in por_chave.get(chave, []) if id(l) not in usadas]
        linha: Optional[LinhaDeCoberturaDoDocumento] = None
        if len(candidatas) == 1:
            linha = candidatas[0]
        elif len(candidatas) > 1:
            linha = _desempatar_por_lmi(cobertura, candidatas)
            if linha is None:
                sinais.append(Sinal("rotulo_ambiguo", {
                    "rotulo": cobertura.rotulo,
                    "candidatos": [l.rotulo for l in candidatas],
                }))
        if linha is None:
            coberturas.append(cobertura)
            continue
        usadas.add(id(linha))
        coberturas.append(_fundir_cobertura(cobertura, linha, mapa))

    # --- o que o documento tem e o cadastro não tem NUNCA é descartado ------
    for do_documento in pdf.linhas:
        if id(do_documento) in usadas:
            continue
        coberturas.append(_cobertura_do_documento(do_documento, mapa))

    parcelas = _reconciliar_parcelas(corp.parcelas, pdf.parcelas)

    plano = corp.plano_de_assistencia
    if pdf.plano_de_assistencia is not None:
        plano = _fundir_plano(corp.plano_de_assistencia, pdf.plano_de_assistencia)

    documento = corp.documento
    if pdf.referencia is not None:
        documento = pdf.referencia

    return replace(
        corp,
        coberturas=tuple(coberturas),
        parcelas=parcelas,
        plano_de_assistencia=plano,
        documento=documento,
        sinais=tuple(sinais),
    )


def _desempatar_por_lmi(
    cobertura: Cobertura, candidatas: Sequence[LinhaDeCoberturaDoDocumento]
) -> Optional[LinhaDeCoberturaDoDocumento]:
    """Desempate SECUNDÁRIO por LMI igual — e só com o primeiro token em comum.

    🔴 A trava está no primeiro token: sem ela, duas coberturas de assuntos
    diferentes que por acaso tenham o mesmo limite (📊 na HDI, **cinco**
    coberturas têm LMI de R$ 3.000,00) casariam uma com a outra. O critério é
    "mesmo limite E mesma família de rótulo", nunca "mesmo limite".
    """
    primeiro = normalizar_rotulo(cobertura.rotulo).split(" ")[0]
    if not primeiro:
        return None
    alvo = cobertura.limite.valor
    if isinstance(alvo, Indisponivel) or alvo is None:
        return None
    possiveis = [
        l for l in candidatas
        if normalizar_rotulo(l.rotulo).split(" ")[0] == primeiro
        and not isinstance(l.limite, Indisponivel)
        and l.limite == alvo
    ]
    return possiveis[0] if len(possiveis) == 1 else None


def _fundir_cobertura(
    cobertura: Cobertura, linha: LinhaDeCoberturaDoDocumento, mapa: Dict[str, Any]
) -> Cobertura:
    """O documento vence em cobertura/limite/franquia/prêmio — e as duas ficam."""
    divergencias: List[Divergencia] = list(cobertura.divergencias)
    detalhe_doc = {"pagina": linha.pagina} if linha.pagina else {}

    limite = cobertura.limite
    if not isinstance(linha.limite, Indisponivel):
        if _divergem_em_dinheiro(cobertura.limite.valor, linha.limite):
            divergencias.append(Divergencia(
                campo="limite",
                valor_sistema_de_gestao=cobertura.limite.valor,
                valor_documento_oficial=linha.limite,
                detalhe={"rotulo": cobertura.rotulo},
            ))
        limite = CampoComOrigem(valor=linha.limite, origem="documento_oficial",
                                confianca="alta", detalhe=dict(detalhe_doc))

    premio = cobertura.premio
    if not isinstance(linha.premio, Indisponivel):
        if _divergem_em_dinheiro(cobertura.premio.valor, linha.premio):
            divergencias.append(Divergencia(
                campo="prêmio",
                valor_sistema_de_gestao=cobertura.premio.valor,
                valor_documento_oficial=linha.premio,
                detalhe={"rotulo": cobertura.rotulo},
            ))
        premio = CampoComOrigem(valor=linha.premio, origem="documento_oficial",
                                confianca="alta", detalhe=dict(detalhe_doc))

    franquia = cobertura.franquia
    if linha.franquia_texto:
        de_corp = _franquia_comparavel(cobertura.franquia.valor)
        do_pdf = _franquia_comparavel(linha.franquia_texto)
        if de_corp is not None and do_pdf is not None and de_corp != do_pdf:
            divergencias.append(Divergencia(
                campo="franquia",
                valor_sistema_de_gestao=cobertura.franquia.valor,
                valor_documento_oficial=linha.franquia_texto,
                detalhe={"rotulo": cobertura.rotulo},
            ))
        franquia = CampoComOrigem(valor=linha.franquia_texto, origem="documento_oficial",
                                  confianca="alta", detalhe=dict(detalhe_doc))

    gid = grupo_de_rotulo(linha.rotulo, mapa=mapa) or cobertura.grupo
    return Cobertura(
        # 🔴 O RÓTULO também vence do documento: é o texto que a seguradora
        # imprime e que o segurado tem na mão. 📊 "RESP. CIVIL SIND. DE CON."
        # (cadastro) x "RC Síndico" (PDF): o segundo é o que dá para ler.
        rotulo=linha.rotulo,
        rotulo_normalizado=normalizar_rotulo(linha.rotulo),
        limite=limite,
        franquia=franquia,
        premio=premio,
        divergencias=tuple(divergencias),
        grupo=gid,
    )


def _cobertura_do_documento(linha: LinhaDeCoberturaDoDocumento, mapa: Dict[str, Any]) -> Cobertura:
    """Rótulo do PDF que não casa com nada entra como cobertura NOVA.

    ⛔ **Nunca é descartado** (proposta §5.5 regra 2). 📊 É assim que as 4
    linhas que só o documento da HDI tem — Ruptura de Tubulações, Vendaval,
    Cláusula de Valor Novo e as **Assistências Essenciais de R$ 125,94** —
    chegam ao corretor em vez de sumirem.
    """
    detalhe = {"pagina": linha.pagina} if linha.pagina else {}
    return Cobertura(
        rotulo=linha.rotulo,
        rotulo_normalizado=normalizar_rotulo(linha.rotulo),
        limite=CampoComOrigem(valor=linha.limite, origem="documento_oficial",
                              confianca="alta", detalhe=dict(detalhe)),
        franquia=CampoComOrigem(valor=(linha.franquia_texto or INDISPONIVEL),
                                origem="documento_oficial", confianca="alta",
                                detalhe=dict(detalhe)),
        premio=CampoComOrigem(valor=linha.premio, origem="documento_oficial",
                              confianca="alta", detalhe=dict(detalhe)),
        grupo=grupo_de_rotulo(linha.rotulo, mapa=mapa),
    )


def _reconciliar_parcelas(
    do_sistema: Sequence[Parcela], do_documento: Sequence[Parcela]
) -> Tuple[Parcela, ...]:
    """Parcela: **o sistema de gestão vence** — e a divergência fica escrita.

    ⚠️ 📊 E é aqui que o defeito de escala aparece em vez de passar calado: o
    cadastro da HDI diz `8231.0` e o documento diz `82.31` para a mesma
    parcela. A porta não divide por 100 (adivinhar escala é inventar), mas
    também não cala: sai uma `Divergencia` por parcela.
    """
    if not do_sistema:
        return tuple(do_documento)
    por_numero = {p.numero: p for p in do_documento}
    saida: List[Parcela] = []
    for parcela in do_sistema:
        outra = por_numero.get(parcela.numero)
        if outra is None:
            saida.append(parcela)
            continue
        divergencias = list(parcela.divergencias)
        if _divergem_em_dinheiro(parcela.valor.valor, outra.valor.valor):
            divergencias.append(Divergencia(
                campo="valor da parcela %d" % parcela.numero,
                valor_sistema_de_gestao=parcela.valor.valor,
                valor_documento_oficial=outra.valor.valor,
            ))
        saida.append(replace(parcela, divergencias=tuple(divergencias)))
    return tuple(saida)


def _fundir_plano(
    do_sistema: Optional[PlanoDeAssistencia], do_documento: PlanoDeAssistencia
) -> PlanoDeAssistencia:
    """Plano/nível: o documento vence. O nome do cadastro só sobrevive se o
    documento não trouxer nome."""
    if do_sistema is None:
        return do_documento
    nome = do_documento.nome if do_documento.nome.tem_valor else do_sistema.nome
    return PlanoDeAssistencia(
        nome=nome,
        nivel=do_documento.nivel or do_sistema.nivel,
        servicos=do_documento.servicos or do_sistema.servicos,
        estado=do_documento.estado,
    )


def _contador_de_premio(corp: Apolice) -> Optional[Sinal]:
    """`Σ premio(cobertura do sistema de gestão) ≠ premio_liquido` → sinal.

    📊 HDI: R$ 70,29 x R$ 306,60 → **R$ 236,31 faltando, 77%**. Teria acendido.
    📊 Allianz condomínio: R$ 17.973,02 x R$ 24.960,60 → **R$ 6.987,58, 28%**.
    📊 Controle (`apolice_de_controle_extra0011.json`, sintética): a soma bate →
    **sem sinal**. A linha de controle é o que dá direito à conclusão.

    🔴 O sinal é sobre o **CADASTRO**, e por isso continua aceso depois da
    reconciliação: a resposta fica inteira; o cadastro, não.
    """
    if corp.premio_liquido is None or not corp.premio_liquido.tem_valor:
        return None
    liquido = corp.premio_liquido.valor
    if not isinstance(liquido, Decimal) or liquido <= 0:
        return None
    do_cadastro = [
        c.premio.valor for c in corp.coberturas
        if c.premio.origem == "sistema_de_gestao" and isinstance(c.premio.valor, Decimal)
    ]
    if not do_cadastro:
        return None
    soma = sum(do_cadastro, Decimal("0")).quantize(_DOIS_CENTAVOS)
    diferenca = (liquido - soma).quantize(_DOIS_CENTAVOS)
    if abs(diferenca) <= TOLERANCIA_DE_PREMIO:
        return None
    pct = (diferenca / liquido * Decimal("100")).quantize(_DOIS_CENTAVOS)
    return Sinal("cadastro_incompleto", {
        "soma_das_coberturas": soma,
        "premio_liquido": liquido,
        "diferenca_reais": diferenca,
        "diferenca_pct": pct,
        "coberturas_do_cadastro": len(do_cadastro),
        "tolerancia_reais": TOLERANCIA_DE_PREMIO,
    })


# ===========================================================================
# O CONTRATO
# ===========================================================================
#: Os OITO membros que o verificador de tipos cobra: as 5 novas + `capacidades`
#: + os 3 depreciados. 🔴 `vehicle` está aqui porque a sua ausência do Protocol
#: é o que produziu 4 `hasattr` em produção e a falha silenciosa que chega ao
#: segurado (§5.1.1).
MEMBROS_DO_CONTRATO: Tuple[str, ...] = (
    "capacidades",
    "buscar_cliente",
    "listar_apolices",
    "detalhar_apolice",
    "documento_oficial",
    "parcelas_em_aberto",
    "lookup",
    "detail",
    "vehicle",
)


class PolicyDataProvider(Protocol):
    """O contrato de leitura de apólice por sistema de gestão.

    🔴 **`company_id` é SEMPRE o primeiro parâmetro nomeado** (keyword-only).
    Nenhuma operação deduz tenant de contexto global, de sessão ou do LLM
    (CLAUDE.md §7).

    🔴 **`apolice_ref` e `cliente_ref` são OPACOS** — o locator técnico
    `"<provider>:<parte>:<parte>"` que `parse_policy_locator_ref` define.
    Número humano de apólice nunca é ref.

    ⛔ Este `Protocol` **não** é `@runtime_checkable`, de propósito. A PEP 544
    diz que protocolos são fundamentalmente **estáticos** e que
    `@runtime_checkable` *"não é type safe no caso de atributos definidos
    dinamicamente"*. A prova do GATE A1 é o verificador de tipos; a segunda
    prova é `register_policy_data_provider`, que RECUSA em runtime — nunca um
    `isinstance`, que aprovaria um adaptador sem `vehicle`.
    """

    provider_key: str

    def capacidades(self) -> CapacidadeDoProvider:
        """O que este provider consegue entregar, por operação."""
        ...

    async def buscar_cliente(
        self,
        *,
        company_id: str,
        documento: Optional[str] = None,
        telefone: Optional[str] = None,
        nome: Optional[str] = None,
        **kwargs: Any,
    ) -> ResultadoDeBusca:
        """Acha o cliente. Devolve `cliente_ref` opaco — nunca nome nem CPF."""
        ...

    async def listar_apolices(
        self,
        *,
        company_id: str,
        cliente_ref: str,
        incluir_vencidas: bool = False,
        ramo: Optional[RamoCanonico] = None,
        hoje: Optional[date] = None,
        **kwargs: Any,
    ) -> ListaDeApolices:
        """A lista CLASSIFICADA por vigência. A ESCOLHA é do BLOCO B."""
        ...

    async def detalhar_apolice(
        self, *, company_id: str, apolice_ref: str, **kwargs: Any
    ) -> Apolice:
        """A apólice inteira: cadastro + documento, já reconciliados."""
        ...

    async def documento_oficial(
        self, *, company_id: str, apolice_ref: str, **kwargs: Any
    ) -> Optional[DocumentoOficial]:
        """O documento oficial por REFERÊNCIA. `None` = não há."""
        ...

    async def parcelas_em_aberto(
        self, *, company_id: str, cliente_ref: str, **kwargs: Any
    ) -> List[Parcela]:
        """As parcelas ainda não quitadas.

        ⚠️ Lista vazia **não** é "não deve nada" quando `capacidades()` diz
        `PARCIAL` ou `INDISPONIVEL` — quem chama tem de perguntar antes
        (P-PILOTO-19: 📊 `/parcelas` responde 403 hoje).
        """
        ...

    # ── MEMBROS DEPRECIADOS ────────────────────────────────────────────────
    async def lookup(self, **kwargs: Any) -> Dict[str, Any]:
        """DEPRECIADO — sai quando a tabela §5.1.1 estiver toda migrada; o item
        7 (`billing_collection.py`) é da EXTRA-001.6."""
        ...

    async def detail(self, **kwargs: Any) -> Dict[str, Any]:
        """DEPRECIADO — sai quando a tabela §5.1.1 estiver toda migrada; o item
        7 (`billing_collection.py`) é da EXTRA-001.6."""
        ...

    async def vehicle(self, **kwargs: Any) -> Dict[str, Any]:
        """DEPRECIADO — sai quando a tabela §5.1.1 estiver toda migrada; o item
        7 (`billing_collection.py`) é da EXTRA-001.6."""
        ...


# ===========================================================================
# O REGISTRY — o MESMO padrão da porta irmã (CLAUDE.md §5)
# ===========================================================================
_REGISTRY: Dict[str, Any] = {}


def register_policy_data_provider(provider: Any) -> None:
    """Registra o adaptador. 🔴 **RECUSA** o que não tiver os 8 membros.

    É a prova em runtime que o GATE A1 exige, e é o fim do `hasattr` como
    contrato: 📊 4 `hasattr(provider, "vehicle")` existiam em produção porque
    `vehicle` nunca esteve no `Protocol`. Com a recusa aqui, o adaptador
    incompleto **não chega** ao ponto em que o `hasattr` decidiria.

    ⚠️ E a mensagem nomeia os membros que faltam: um `ValueError` que só diz
    "adaptador inválido" obriga quem o lê a adivinhar, e adivinhar é o que
    produz o próximo `hasattr`.
    """
    key = str(getattr(provider, "provider_key", "") or "").strip().lower()
    if not key:
        raise ValueError("PolicyDataProvider requires provider_key")
    faltando = [nome for nome in MEMBROS_DO_CONTRATO if not callable(getattr(provider, nome, None))]
    if faltando:
        raise ValueError(
            "adaptador %s sem: %s — o contrato PolicyDataProvider tem %d membros "
            "(5 operações + capacidades() + 3 depreciados). Um adaptador incompleto "
            "não falha: ele responde 'fonte indisponível', e o atendente pede a "
            "placa ao cliente (SPEC-EXTRA-001.1 §5.1.1)."
            % (key, ", ".join(faltando), len(MEMBROS_DO_CONTRATO))
        )
    _REGISTRY[key] = provider


def get_policy_data_provider(provider_key: str = "infocap") -> Optional[Any]:
    """Resolve o adaptador por chave, registrando os nossos na primeira falta.

    ⚠️ 📊 O registro tardio existe por uma razão medida, não por elegância:
    `infocap_policy_provider` importa ESTE módulo, e este módulo registra
    aquele. Quem importar o ADAPTADOR primeiro encontra a porta a meio
    inicializar, e o `register` do fim do arquivo falha com `ImportError:
    cannot import name 'InfoCapProvider' from partially initialized module`.
    O sintoma seria o pior possível — `get_policy_data_provider("infocap")`
    devolvendo `None` conforme a ORDEM DE IMPORTAÇÃO do processo, e o atendente
    respondendo "fonte indisponível" em metade dos deploys.
    """
    chave = str(provider_key or "").strip().lower()
    encontrado = _REGISTRY.get(chave)
    if encontrado is None and chave in ("infocap", "pdf_only"):
        _registrar_os_nossos()
        encontrado = _REGISTRY.get(chave)
    return encontrado


def policy_data_providers() -> Dict[str, Any]:
    """Cópia do registro. Para diagnóstico e para o guarda — nunca para mutar."""
    return dict(_REGISTRY)


# ===========================================================================
# O adaptador InfoCap mora em `infocap_policy_provider.py` — aqui fica o ALIAS
# ===========================================================================
def _registrar_o_piloto() -> None:
    """Registra o InfoCap por padrão, como desde a SPEC-016 E5.

    ⚠️ O import é LOCAL e tolerante: `infocap_policy_provider` importa o
    conector, e o conector puxa FastAPI/httpx. Um `ImportError` no topo deste
    módulo deixaria a porta inteira indisponível por causa do adaptador —
    exatamente o acoplamento que a porta existe para impedir.
    """
    try:
        from app.providers.infocap_policy_provider import InfoCapProvider
    except ImportError:
        # ⚠️ O adaptador foi importado PRIMEIRO e ainda esta a meio caminho.
        # Nao e defeito: ele se registra no proprio fim, e `get_policy_data_provider`
        # tem o registro tardio. `debug`, e nao `warning`, porque um aviso que
        # aparece em toda importacao normal ensina a ignorar avisos.
        logger.debug("[APOLICE] adaptador InfoCap ainda inicializando; registro tardio assume")
        return
    except Exception as exc:  # noqa: BLE001
        logger.warning("[APOLICE] adaptador InfoCap nao registrado (%s: %s)",
                       type(exc).__name__, exc)
        return
    try:
        register_policy_data_provider(InfoCapProvider())
    except Exception as exc:  # noqa: BLE001
        logger.error("[APOLICE] adaptador InfoCap RECUSADO pelo contrato: %s", exc)


def _registrar_o_segundo() -> None:
    """Registra o `PdfOnlyProvider` sob `"pdf_only"`.

    🔴 Ele não é enfeite: enquanto só a InfoCap implementar a porta, nada impede
    que uma decisão da InfoCap vaze para a assinatura e ninguém perceba. O
    segundo adaptador no registro é o teste permanente disso — e o acervo dele
    nasce vazio de propósito: quem o usa injeta os documentos que já leu.
    """
    try:
        from app.providers.pdf_only_policy_provider import PdfOnlyProvider

        register_policy_data_provider(PdfOnlyProvider())
    except Exception as exc:  # noqa: BLE001
        logger.error("[APOLICE] adaptador PdfOnly nao registrado: %s", exc)


def _registrar_os_nossos() -> None:
    """Os dois adaptadores da casa. Idempotente: `register` só sobrescreve."""
    _registrar_o_piloto()
    _registrar_o_segundo()


_registrar_os_nossos()


def __getattr__(nome: str) -> Any:
    """`InfocapPolicyDataProvider` continua importável — é o nome antigo.

    📊 Cinco módulos e oito pontos de chamada falam com esta porta hoje. O nome
    velho continua resolvendo para a classe nova (`InfoCapProvider`), sem que o
    módulo precise importar o conector no topo.
    """
    if nome == "InfocapPolicyDataProvider":
        from app.providers.infocap_policy_provider import InfoCapProvider
        return InfoCapProvider
    raise AttributeError("module %r has no attribute %r" % (__name__, nome))
