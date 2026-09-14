# -*- coding: utf-8 -*-
"""`InfoCapProvider` — o adaptador que ENVOLVE o conector. SPEC-EXTRA-001.1 §5.6.

🔴 **Este é o ÚNICO módulo fora de `app/api/infocap_connector.py` que sabe o que
é `preliq`.** Ele traduz o pack canônico do conector para o modelo da casa
(`Apolice`), e nada do conector é reescrito — 4.487 linhas de motor continuam
sendo o motor (CLAUDE.md §5: consolidar e migrar antes de duplicar).

```
✅ o que entra aqui     o dict do conector: pack, matches, documents_count
✅ o que sai daqui      Apolice · ListaDeApolices · ResultadoDeBusca · DocumentoOficial
⛔ o que NUNCA sai      preliq · nosnum · codfil · tabela_itens · forma_pag
                        sit_renovacao_txt · inivig · fimvig · o dict cru
```

⚠️ **A exceção, e ela é a mesma da porta:** `apolice_ref` é o *locator técnico*
`"infocap:<parte>:<parte>"`. Ele atravessa a fronteira porque é **opaco** —
quem o consome não sabe (e não pode saber) que a segunda parte é um `codfil`.

## Os três depreciados delegam EXATAMENTE como antes

`lookup`, `detail` e `vehicle` continuam devolvendo o `Dict[str, Any]` do
conector, byte a byte. 📊 Oito pontos de chamada dependem disso hoje, e um
deles — `app/services/billing_collection.py:1205-1212` — é da **EXTRA-001.6,
que corre em paralelo**. `InfocapPolicyDataProvider` continua importável como
alias (o nome antigo).

## Os quatro campos que ninguém lia — e por onde eles passam agora

📊 Até 14/09/2026, `_safe_envelope_summary` (`infocap_connector.py`) guardava do
envelope apenas os **NOMES das chaves** (`{"type": "array", "count": N,
"sample_keys": [...]}`), e por isso `tabela_itens` (o nome do plano),
`sit_renovacao_txt`, `sit_sinistro_txt` e `itens[].observacoes` (a franquia em
prosa) **não chegavam ao pack**: do `tabela_itens` sobrava só o booleano
`unknown_table_field_present`.

🔴 **BLOCO D (§8.2):** o `_build_evidence_pack` passou a carregá-los com VALOR:

```
pack["provider_signals"]           sit_renovacao_txt · sit_sinistro_txt · tabela_itens
pack["coverage_sections"][].item_observacoes   a franquia em PROSA, por cobertura
pack["risk_objects"][].observacoes             o texto livre do item de risco
```

⚠️ O `evidence_envelope` continua sendo um resumo de **FORMA** — é para isso que
ele existe. Quem lê os valores é `_sinal_do_provedor`, aqui, e mais ninguém.
⛔ E nenhum deles decide: `sit_renovacao_txt` é SINAL; quem classifica vigência
é `classificar_vigencia(inicio, fim, cancelado, hoje)`, por DATA.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.providers.policy_data_provider import (
    INDISPONIVEL,
    UNKNOWN,
    Apolice,
    ApoliceDocumental,
    ApoliceNaLista,
    CampoComOrigem,
    Capacidade,
    CapacidadeDoProvider,
    Cobertura,
    DocumentoOficial,
    Indisponivel,
    ItemDeRisco,
    LinhaDeCoberturaDoDocumento,
    ListaDeApolices,
    Parcela,
    PlanoDeAssistencia,
    RamoCanonico,
    ReferenciaDeDocumento,
    ResultadoDeBusca,
    SeguradoraCanonica,
    Sinal,
    Vigencia,
    SITUACOES_OCULTAS,
    # ⚠️ Privados da PORTA, importados de propósito: são o casamento de rótulo e
    #    a comparação de franquia que `reconciliar` usa. Reescrevê-los aqui
    #    seria um segundo motor para a mesma regra (CLAUDE.md §5).
    _chave_de_casamento,
    _franquia_comparavel,
    classificar_vigencia,
    data_de,
    dinheiro,
    familia_de_ramo,
    normalizar_rotulo,
    reconciliar,
)

logger = logging.getLogger(__name__)

__all__ = [
    "InfoCapProvider",
    "InfocapPolicyDataProvider",
    "apolice_do_pack",
    "apolice_documental_do_pack",
    "seguradora_canonica",
    "ramo_canonico",
]

PROVIDER_KEY = "infocap"

#: 🔴 A origem de tudo que vem do sistema de gestão. O valor canônico do
#: `policy_facts.FACT_SOURCES` mudou junto (§5.3): `infocap_structured` tinha o
#: nome do FORNECEDOR dentro do modelo do DOMÍNIO. Numa corretora que use
#: Quiver, o fato de uma cobertura continuaria dizendo que veio da InfoCap.
SISTEMA_DE_GESTAO = "sistema_de_gestao"
DOCUMENTO_OFICIAL = "documento_oficial"


# ===========================================================================
# O CATÁLOGO — delegado, nunca reimplementado
# ===========================================================================
#
# ⛔ **`policy_catalog.py` NÃO existe, e a decisão está escrita** (§5.4): ao
# escrever a tradução, ela não precisou de mais que duas chamadas ao leitor que
# já existe. Um módulo novo que só repassasse `coenti_de`/`cogrupo_de` seria uma
# camada sem trabalho — e o risco declarado de virar o segundo catálogo no dia
# em que alguém lhe acrescentasse "só um mapinha".
def seguradora_canonica(abreviatura: Any) -> SeguradoraCanonica:
    """`"ALLI"` → chave nossa + `coenti` da SUSEP. O que não casa sai `UNKNOWN`.

    ⛔ Nunca por derivação de string. 📊 O censo da SPEC-094.1 mediu o token
    `SEGUROS` devolvendo **284** candidatos e `SURA` devolvendo **130** (casa
    dentro de "ASSURANCE"). `coenti_de()` casa por IGUALDADE, em três
    tentativas, e o que não casa sai `UNKNOWN` **com o nome listado** — nunca
    omitido, nunca zero.
    """
    nome = str(abreviatura or "").strip()
    if not nome:
        return SeguradoraCanonica(chave=UNKNOWN, coenti=UNKNOWN, nome_listado=None)
    try:
        from app.providers.susep_ses_provider import coenti_de

        coenti = coenti_de(nome)
    except Exception as exc:  # noqa: BLE001 — catálogo ausente nunca derruba a leitura
        logger.warning("[APOLICE] catalogo de seguradoras indisponivel (%s)", type(exc).__name__)
        coenti = UNKNOWN
    return SeguradoraCanonica(
        chave=normalizar_rotulo(nome).replace(" ", "_") or UNKNOWN,
        coenti=str(coenti or UNKNOWN),
        nome_listado=nome,
    )


def ramo_canonico(abreviatura: Any, nome_humano: Any = None) -> RamoCanonico:
    """`"COND"` → grupo de ramo da SUSEP, por `cogrupo_de()`. Idem: igualdade."""
    abrev = str(abreviatura or "").strip()
    if not abrev:
        return RamoCanonico(abreviatura=UNKNOWN, cogrupo=UNKNOWN, nome_humano=None)
    try:
        from app.providers.susep_ses_provider import cogrupo_de

        cogrupo = cogrupo_de(abrev)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[APOLICE] catalogo de ramos indisponivel (%s)", type(exc).__name__)
        cogrupo = UNKNOWN
    return RamoCanonico(
        abreviatura=abrev,
        cogrupo=str(cogrupo or UNKNOWN),
        nome_humano=(str(nome_humano).strip() if nome_humano else None),
    )


# ===========================================================================
# A TRADUÇÃO — pack do conector → `Apolice`
# ===========================================================================
def _campo(valor: Any, origem: str, *, confianca: str = "alta", **detalhe: Any) -> CampoComOrigem[Any]:
    return CampoComOrigem(
        valor=(INDISPONIVEL if valor in (None, "") else valor),
        origem=origem,  # type: ignore[arg-type]
        confianca=confianca,  # type: ignore[arg-type]
        detalhe={k: v for k, v in detalhe.items() if v not in (None, "")},
    )


def _coberturas_do_pack(pack: Dict[str, Any]) -> Tuple[Cobertura, ...]:
    """`coverage_sections` → `Cobertura`, com origem `sistema_de_gestao`.

    ⚠️ O conector já formatou em pt-BR (`_money_br`): `amount = "R$ 100.000,00"`.
    A porta não devolve string de moeda para quem vai somar, então a tradução
    volta para `Decimal` aqui — é literalmente o trabalho do adaptador.
    """
    saida: List[Cobertura] = []
    for secao in pack.get("coverage_sections") or []:
        if not isinstance(secao, dict):
            continue
        rotulo = str(secao.get("label") or "").strip()
        if not rotulo:
            continue
        campo_de_origem = secao.get("amount_source_field") or secao.get("source_field")
        saida.append(Cobertura(
            rotulo=rotulo,
            rotulo_normalizado=normalizar_rotulo(rotulo),
            limite=_campo(dinheiro(secao.get("amount")), SISTEMA_DE_GESTAO,
                          provider_field=campo_de_origem),
            franquia=_campo(secao.get("deductible"), SISTEMA_DE_GESTAO,
                            provider_field="franquia"),
            premio=_campo(dinheiro(secao.get("premium")), SISTEMA_DE_GESTAO,
                          provider_field="premio"),
        ))
    return tuple(saida)


def _parcelas_do_pack(pack: Dict[str, Any]) -> Tuple[Parcela, ...]:
    """`installments` → `Parcela`. 🔴 A forma de pagamento vem DAQUI (§8.3)."""
    saida: List[Parcela] = []
    for i, bruta in enumerate(pack.get("installments") or [], start=1):
        if not isinstance(bruta, dict):
            continue
        campos = bruta.get("source_fields") or {}
        try:
            numero = int(str(bruta.get("installment_number") or i).strip())
        except (TypeError, ValueError):
            numero = i
        quitada = data_de(bruta.get("paid_at"))
        saida.append(Parcela(
            numero=numero,
            vencimento=_campo(data_de(bruta.get("due_date")), SISTEMA_DE_GESTAO,
                              provider_field=campos.get("due_date")),
            valor=_campo(dinheiro(bruta.get("due_amount")), SISTEMA_DE_GESTAO,
                         provider_field=campos.get("due_amount")),
            forma_de_pagamento=_campo(bruta.get("payment_method"), SISTEMA_DE_GESTAO,
                                      provider_field=campos.get("payment_method")),
            quitada_em=(_campo(quitada, SISTEMA_DE_GESTAO,
                               provider_field=campos.get("paid_at")) if quitada else None),
        ))
    return tuple(saida)


def _premio_liquido_do_pack(pack: Dict[str, Any]) -> Optional[CampoComOrigem[Any]]:
    resumo = pack.get("premium_summary")
    if not isinstance(resumo, dict):
        return None
    liquido = resumo.get("net_premium")
    if not isinstance(liquido, dict):
        return None
    valor = dinheiro(liquido.get("value"))
    if isinstance(valor, Indisponivel):
        return None
    # ⛔ `provider_field` fica no `detalhe` da PROVENIÊNCIA, que é auditoria —
    #    ele nunca é o NOME do campo que o corretor lê. A diferença entre um
    #    adaptador e um alias é exatamente esta (§8.3).
    return _campo(valor, SISTEMA_DE_GESTAO, provider_field=liquido.get("provider_field"))


def _sinal_do_provedor(pack: Dict[str, Any], documento_cru: Optional[Dict[str, Any]],
                       campo: str) -> Optional[str]:
    """O texto cru do fornecedor, do `documento` OU do pack. `None` se não vier.

    🔴 SPEC-EXTRA-001.1 BLOCO D: até 14/09/2026 estes campos existiam na fonte e
    morriam no conector (`_safe_envelope_summary` guardava só os NOMES das
    chaves). Agora o `_build_evidence_pack` os carrega em `provider_signals`, e
    este é o ÚNICO lugar fora do conector que sabe como eles se chamam.
    """
    if isinstance(documento_cru, dict):
        do_documento = str(documento_cru.get(campo) or "").strip()
        if do_documento:
            return do_documento
    sinais = pack.get("provider_signals")
    if isinstance(sinais, dict):
        do_pack = str(sinais.get(campo) or "").strip()
        if do_pack:
            return do_pack
    return None


def _plano_do_pack(pack: Dict[str, Any], documento_cru: Optional[Dict[str, Any]]) -> Optional[PlanoDeAssistencia]:
    """`tabela_itens` → nome do plano. Nome sem serviços = `nao_sabemos_ainda`.

    📊 Quando o valor não atravessa (o caso de hoje — ver o cabeçalho deste
    módulo), sobra o booleano `unknown_table_field_present`: sabe-se que EXISTE
    um plano e não se sabe qual. `INDISPONIVEL` diz isso; `None` diria "não
    tem", e `""` diria "tem um plano sem nome". As três leituras são
    diferentes, e só uma é verdade.
    """
    nome = _sinal_do_provedor(pack, documento_cru, "tabela_itens")
    if nome is None and not pack.get("unknown_table_field_present"):
        return None
    return PlanoDeAssistencia(
        nome=_campo(nome, SISTEMA_DE_GESTAO, confianca="media", provider_field="tabela_itens"),
        estado="nao_sabemos_ainda",
    )


def _sinais_do_pack(pack: Dict[str, Any], documento_cru: Optional[Dict[str, Any]]) -> List[Sinal]:
    """Sinais que o corretor precisa VER — inclusive o do cabeçalho que mente."""
    sinais: List[Sinal] = []

    renovacao = _sinal_do_provedor(pack, documento_cru, "sit_renovacao_txt")
    if renovacao:
        # ⚠️ SINAL, nunca veredito de vigência: quem decide vigência é
        # `classificar_vigencia(inicio, fim, cancelado, hoje)`, por DATA.
        sinais.append(Sinal("situacao_de_renovacao", {"texto": renovacao}))
    sinistro = _sinal_do_provedor(pack, documento_cru, "sit_sinistro_txt")
    if sinistro:
        sinais.append(Sinal("situacao_de_sinistro", {"texto": sinistro}))

    # 🔴 `forma_pag` do CABEÇALHO x a forma das PARCELAS (§8.3).
    # 📊 HDI: cabeçalho "Boleto Bancário" x 4 parcelas "Cartão de Crédito".
    do_cabecalho = str((pack.get("premium_summary") or {}).get("payment_method") or "").strip()
    das_parcelas = sorted({
        str(p.get("payment_method") or "").strip()
        for p in (pack.get("installments") or [])
        if isinstance(p, dict) and str(p.get("payment_method") or "").strip()
    })
    if do_cabecalho and das_parcelas and normalizar_rotulo(do_cabecalho) not in {
        normalizar_rotulo(f) for f in das_parcelas
    }:
        sinais.append(Sinal("cabecalho_divergente", {
            "campo": "forma de pagamento",
            "no_cabecalho": do_cabecalho,
            "nas_parcelas": das_parcelas,
        }))

    # 🔴 As franquias em prosa do PDF que NÃO têm dono (BLOCO D). O corretor as
    # vê; o sistema não as adivinha. 📊 Na HDI real sobram 3 de 6 — a tabela do
    # PDF não diz quais coberturas têm franquia, e o cadastro só conhece 3.
    prosas = [str(e.get("text") or "").strip()
              for e in _estruturados(pack, "deductible_prose")
              if str(e.get("text") or "").strip()]
    if prosas:
        lidas = _linhas_e_plano_do_documento(pack)
        _casadas, sobras = _franquias_em_prosa_do_documento(
            pack, lidas[0] if lidas is not None else ())
        if sobras:
            sinais.append(Sinal("franquia_em_prosa_sem_dono", {
                "quantidade": len(sobras),
                "textos": sobras,
                "motivo": ("o documento não diz a qual cobertura cada franquia "
                           "pertence, e o cadastro só conhece as que já foram casadas"),
            }))

    if pack.get("cancelled"):
        sinais.append(Sinal("apolice_cancelada", {}))
    return sinais


def _franquias_em_prosa(
    itens_crus: Optional[Sequence[Any]], pack: Optional[Dict[str, Any]] = None
) -> Dict[str, str]:
    """`itens[].observacoes` → a prosa de franquia, por rótulo, quando vier.

    📊 O campo existe na fonte e ninguém o lia (§8.2): é ele que carrega
    *"15% dos prejuízos, mínimo R$ 600"*. Aqui a prosa é o VALOR da franquia,
    não um comentário — por isso `Cobertura.franquia` é
    `CampoComOrigem[Dinheiro | str]`.

    🔴 BLOCO D: em produção `itens_crus` não existe — só o conector vê o
    `/itens`. Por isso a prosa passa a viajar NO PACK, em
    `coverage_sections[].item_observacoes`, e este leitor aceita as duas
    entradas. ⚠️ A prosa só vira franquia quando a cobertura NÃO tem valor
    (`apolice_do_pack`): ela é o último recurso, não o preferido.
    """
    saida: Dict[str, str] = {}
    for item in itens_crus or []:
        if not isinstance(item, dict):
            continue
        prosa = str(item.get("observacoes") or "").strip()
        if not prosa:
            continue
        for garantia in item.get("garantias") or []:
            if isinstance(garantia, dict) and garantia.get("garantia"):
                saida.setdefault(normalizar_rotulo(garantia.get("garantia")), prosa)
    for secao in (pack or {}).get("coverage_sections") or []:
        if not isinstance(secao, dict):
            continue
        prosa = str(secao.get("item_observacoes") or "").strip()
        rotulo = str(secao.get("label") or "").strip()
        if prosa and rotulo:
            saida.setdefault(normalizar_rotulo(rotulo), prosa)
    return saida


def apolice_do_pack(
    pack: Dict[str, Any],
    *,
    apolice_ref: Optional[str] = None,
    documento_cru: Optional[Dict[str, Any]] = None,
    itens_crus: Optional[Sequence[Any]] = None,
    hoje: Optional[date] = None,
) -> Apolice:
    """O pack canônico do conector → `Apolice` do CADASTRO (sem o documento).

    Quem casa isto com o PDF é `reconciliar()`, na PORTA — e não aqui, porque
    "o documento vence em cobertura" é decisão do Founder (D-PILOTO-11), não
    tradução de fornecedor.
    """
    ref = str(apolice_ref or pack.get("policy_locator_ref") or "").strip()
    coberturas = _coberturas_do_pack(pack)

    prosa = _franquias_em_prosa(itens_crus, pack)
    if prosa:
        coberturas = tuple(
            c if c.franquia.tem_valor or c.rotulo_normalizado not in prosa
            else Cobertura(
                rotulo=c.rotulo, rotulo_normalizado=c.rotulo_normalizado,
                limite=c.limite,
                franquia=_campo(prosa[c.rotulo_normalizado], SISTEMA_DE_GESTAO,
                                provider_field="observacoes"),
                premio=c.premio, divergencias=c.divergencias, grupo=c.grupo,
            )
            for c in coberturas
        )

    return Apolice(
        apolice_ref=ref,
        numero_humano=str(pack.get("policy_number") or pack.get("masked_policy_number") or "").strip(),
        seguradora=seguradora_canonica(pack.get("insurer_detected")),
        ramo=ramo_canonico(pack.get("product_detected")),
        vigencia=classificar_vigencia(
            pack.get("valid_from"), pack.get("valid_to"), pack.get("cancelled"), hoje=hoje
        ),
        coberturas=coberturas,
        parcelas=_parcelas_do_pack(pack),
        premio_liquido=_premio_liquido_do_pack(pack),
        plano_de_assistencia=_plano_do_pack(pack, documento_cru),
        sinais=tuple(_sinais_do_pack(pack, documento_cru)),
        documento=_referencia_do_documento(pack),
        item_de_risco=_item_de_risco_do_pack(pack),
        provider_key=PROVIDER_KEY,
    )


def _item_de_risco_do_pack(pack: Dict[str, Any]) -> Optional[ItemDeRisco]:
    """`risk_objects[0]` → `ItemDeRisco`. É o que vai substituir `vehicle()`.

    ⚠️ Só o PRIMEIRO item: a apólice de vários itens (frota) é outra conversa, e
    inventar "o item" de uma frota seria pior que não ter campo nenhum.
    """
    for bruto in pack.get("risk_objects") or []:
        if not isinstance(bruto, dict):
            continue
        def campo(chave: str, provider_field: str):
            valor = bruto.get(chave)
            return (_campo(valor, SISTEMA_DE_GESTAO, provider_field=provider_field)
                    if str(valor or "").strip() else None)
        numero = bruto.get("item_number")
        return ItemDeRisco(
            item=int(numero) if isinstance(numero, int) else None,
            descricao=campo("kind", "tipo_imovel"),
            placa=campo("plate", "placa"),
            cidade=campo("city", "cidade"),
            estado=campo("state", "estado"),
            observacoes=campo("observacoes", "observacoes"),
        )
    return None


def _referencia_do_documento(pack: Dict[str, Any]) -> Optional[ReferenciaDeDocumento]:
    evidencia = pack.get("official_policy_document_evidence")
    if not isinstance(evidencia, dict):
        return None
    itens = evidencia.get("evidence_items") or []
    return ReferenciaDeDocumento(
        paginas=evidencia.get("page_count") or evidencia.get("pages"),
        parser=evidencia.get("extraction_mode") or evidencia.get("parser"),
        cache_key=evidencia.get("cache_key"),
        conteudo_hash=evidencia.get("content_hash"),
        itens_de_evidencia=len(itens) if isinstance(itens, list) else 0,
    )


#: Os tipos de `evidence_item` que carregam uma LINHA de cobertura do PDF.
_TIPOS_DE_LINHA = {"coverage_row", "assistance_plan"}


def _estruturados(pack: Dict[str, Any], tipo: str) -> List[Dict[str, Any]]:
    """Os `structured` de um `kind`, na ORDEM em que o extrator os produziu."""
    evidencia = pack.get("official_policy_document_evidence")
    if not isinstance(evidencia, dict):
        return []
    saida: List[Dict[str, Any]] = []
    for item in evidencia.get("evidence_items") or []:
        if not isinstance(item, dict):
            continue
        estruturado = item.get("structured")
        if isinstance(estruturado, dict) and str(estruturado.get("kind") or "") == tipo:
            saida.append({**estruturado, "_pagina": item.get("page_number")})
    return saida


def _franquias_em_prosa_do_documento(
    pack: Dict[str, Any], linhas: Sequence[LinhaDeCoberturaDoDocumento]
) -> Tuple[Dict[int, str], List[str]]:
    """As franquias em PROSA do PDF, casadas com as linhas — e as SOBRAS.

    🔴 A regra, escrita e falsificável (SPEC-EXTRA-001.1 BLOCO D):

    ```
    a i-ésima prosa casa com a i-ésima linha do documento
    cujo CADASTRO declara ter franquia — e só com essa.
    ```

    ⚠️ **Por que ancorada no cadastro, e não na ordem pura das coberturas:** a
    tabela da HDI **não tem coluna de franquia**; as 6 prosas vêm soltas, "na
    ordem das coberturas com franquia" (layout declarado em
    `tests/fixtures/pdf_tabelas_reais_extra0011.json`) — e nada no PDF diz
    QUAIS coberturas têm franquia. O cadastro diz, para as que ele conhece.

    📊 A âncora é falsificável, e duas das três associações CONFIRMAM o
    cadastro: Incêndio → mínimo R$ 350,00 = cadastro `10.00%-350,00`; Quebra de
    Vidros → R$ 150,00 = cadastro `10.00%-150,00`. A terceira DIVERGE: Danos
    Elétricos → R$ 600,00 x cadastro `10.00%-550,00` — que é exatamente a
    divergência que a apólice real tem, e que o corretor precisa ver inteira.
    Se a regra estivesse errada, as duas confirmações não existiriam.

    ⛔ **As prosas que sobram NÃO são adivinhadas.** Elas viram o sinal
    `franquia_em_prosa_sem_dono`, que o corretor lê. 📊 Na HDI real sobram 3 de
    6: atribuí-las por ordem daria a franquia de uma cobertura a outra — e uma
    franquia errada é um número que o corretor repete ao segurado.
    """
    prosas = [
        str(e.get("text") or "").strip()
        for e in _estruturados(pack, "deductible_prose")
        if str(e.get("text") or "").strip()
    ]
    if not prosas:
        return {}, []
    # ⚠️ `_chave_de_casamento` e `_franquia_comparavel` são os da PORTA, de
    #    propósito: reimplementá-los aqui seria um segundo motor de casamento
    #    de rótulo e um segundo de comparação de franquia (CLAUDE.md §5).
    do_cadastro = set()
    for secao in pack.get("coverage_sections") or []:
        if not isinstance(secao, dict) or not str(secao.get("label") or "").strip():
            continue
        comparavel = _franquia_comparavel(secao.get("deductible"))
        if comparavel is not None and comparavel != "sem_franquia":
            do_cadastro.add(_chave_de_casamento(secao.get("label")))
    alvos = [
        i for i, linha in enumerate(linhas)
        if not linha.franquia_texto and _chave_de_casamento(linha.rotulo) in do_cadastro
    ]
    casadas = {posicao: prosas[i] for i, posicao in enumerate(alvos) if i < len(prosas)}
    return casadas, list(prosas[len(alvos):])


def _parcelas_do_documento(pack: Dict[str, Any]) -> Tuple[Parcela, ...]:
    """As `installment_row` do PDF → `Parcela` com origem `documento_oficial`.

    🔴 Elas não vencem (parcela é do sistema de gestão, §5.5) — servem para a
    DIVERGÊNCIA aparecer: 📊 o cadastro da HDI já trouxe `82,31` depois da
    correção do montador, e é este par que prova, a cada leitura, que os dois
    lados continuam de acordo.
    """
    saida: List[Parcela] = []
    for e in _estruturados(pack, "installment_row"):
        try:
            numero = int(str(e.get("number") or "").strip())
        except (TypeError, ValueError):
            continue
        pagina = e.get("_pagina") if isinstance(e.get("_pagina"), int) else None
        saida.append(Parcela(
            numero=numero,
            vencimento=_campo(data_de(e.get("due_date")), DOCUMENTO_OFICIAL, pagina=pagina),
            valor=_campo(dinheiro(e.get("amount")), DOCUMENTO_OFICIAL, pagina=pagina),
            forma_de_pagamento=_campo(e.get("payment_method"), DOCUMENTO_OFICIAL, pagina=pagina),
        ))
    return tuple(saida)


def apolice_documental_do_pack(pack: Dict[str, Any]) -> Optional[ApoliceDocumental]:
    """`official_policy_document_evidence` → `ApoliceDocumental`. `None` se vazio.

    📊 **Medido em 14/09/2026 sobre as linhas reais dos dois PDFs** (BLOCO D,
    `tests/fixtures/pdf_tabelas_reais_extra0011.json`), depois que o extrator
    aprendeu os dois layouts (divergência D4, decisão D-E0011-02):

    ```
    HDI      10 coverage_row (Σ R$ 306,60) · 6 deductible_prose · 4 installment_row
    Allianz  20 coverage_row + 1 assistance_plan (Σ R$ 24.960,60) · 0 linha de prêmio
    ```

    ⚠️ Sem linha nenhuma, devolve `None` — e isso continua sendo a resposta
    honesta: `ApoliceDocumental(linhas=())` diria "o documento não tem
    coberturas", e `reconciliar` trataria as 6 linhas do cadastro como a
    apólice inteira. **Ausência de LEITURA não é ausência de COBERTURA.**

    🔴 O `assistance_plan` COM PREÇO entra nas duas pontas: vira o plano E vira
    uma linha de cobertura. 📊 A `Assistência 24h` da Allianz custa R$ 23,88 no
    PDF e R$ 0,00 no cadastro — descartá-la como "só plano" apagaria a
    divergência e tiraria R$ 23,88 da soma que fecha com o prêmio líquido.
    """
    lidas = _linhas_e_plano_do_documento(pack)
    if lidas is None:
        return None
    linhas, plano = list(lidas[0]), lidas[1]

    # 🔴 As franquias em PROSA (a tabela da HDI não tem coluna de franquia).
    casadas, _sobras = _franquias_em_prosa_do_documento(pack, linhas)
    if casadas:
        linhas = [
            linha if i not in casadas else LinhaDeCoberturaDoDocumento(
                rotulo=linha.rotulo, limite=linha.limite, premio=linha.premio,
                franquia_texto=casadas[i], pagina=linha.pagina,
            )
            for i, linha in enumerate(linhas)
        ]

    parcelas = _parcelas_do_documento(pack)
    if not linhas and plano is None and not parcelas:
        return None
    return ApoliceDocumental(
        linhas=tuple(linhas),
        plano_de_assistencia=plano,
        parcelas=parcelas,
        referencia=_referencia_do_documento(pack),
    )


def _linhas_e_plano_do_documento(
    pack: Dict[str, Any],
) -> Optional[Tuple[List[LinhaDeCoberturaDoDocumento], Optional[PlanoDeAssistencia]]]:
    """As linhas CRUAS do documento, antes das franquias em prosa.

    ⚠️ Existe separada porque o sinal `franquia_em_prosa_sem_dono` precisa
    perguntar quais linhas **ainda não têm** franquia. Perguntar isso à apólice
    documental já montada devolveria "nenhuma" — e o sinal diria que todas as
    prosas sobraram, inclusive as que já tinham dono.
    """
    evidencia = pack.get("official_policy_document_evidence")
    if not isinstance(evidencia, dict):
        return None
    linhas: List[LinhaDeCoberturaDoDocumento] = []
    plano: Optional[PlanoDeAssistencia] = None
    for item in evidencia.get("evidence_items") or []:
        if not isinstance(item, dict):
            continue
        estruturado = item.get("structured")
        if not isinstance(estruturado, dict):
            continue
        tipo = str(estruturado.get("kind") or "").strip()
        if tipo not in _TIPOS_DE_LINHA:
            continue
        pagina = item.get("page_number") if isinstance(item.get("page_number"), int) else None
        if tipo == "coverage_row":
            rotulo = str(estruturado.get("label") or "").strip()
            if not rotulo:
                continue
            linhas.append(LinhaDeCoberturaDoDocumento(
                rotulo=rotulo,
                limite=dinheiro(estruturado.get("lmi")),
                premio=dinheiro(estruturado.get("premium")),
                franquia_texto=(str(estruturado.get("participation")).strip()
                                if estruturado.get("participation") else None),
                pagina=pagina,
            ))
        else:  # assistance_plan
            nome = str(estruturado.get("plan") or "").strip()
            if not nome:
                continue
            plano = PlanoDeAssistencia(
                nome=_campo(nome, DOCUMENTO_OFICIAL, pagina=pagina),
                estado="contratado",
            )
            preco = dinheiro(estruturado.get("premium"))
            if not isinstance(preco, Indisponivel):
                linhas.append(LinhaDeCoberturaDoDocumento(
                    rotulo=nome,
                    premio=preco,
                    franquia_texto=(str(estruturado.get("participation")).strip()
                                    if estruturado.get("participation") else None),
                    pagina=pagina,
                ))
    return linhas, plano


def _apolice_na_lista(bruta: Dict[str, Any], hoje: Optional[date] = None) -> Optional[ApoliceNaLista]:
    """Um `match` sanitizado do conector → uma linha CLASSIFICADA da lista.

    🔴 `policy_status` do fornecedor entra como SINAL, **nunca** decide a
    vigência. 📊 As duas apólices do golden trazem *"Recebido e não entregue ao
    cliente"* — um estado de ENTREGA DE DOCUMENTO. A classificação é por DATA.
    """
    ref = str(bruta.get("policy_locator_ref") or "").strip()
    if not ref:
        return None
    sinais: List[Sinal] = []
    status = str(bruta.get("policy_status") or "").strip()
    if status:
        sinais.append(Sinal("status_do_fornecedor", {"texto": status}))
    return ApoliceNaLista(
        apolice_ref=ref,
        seguradora=seguradora_canonica(bruta.get("insurer_key")),
        ramo=ramo_canonico(bruta.get("product")),
        vigencia=classificar_vigencia(
            bruta.get("valid_from"), bruta.get("valid_to"), bruta.get("cancelled"), hoje=hoje
        ),
        numero_humano=(str(bruta.get("policy_number") or "").strip() or None),
        sinais=tuple(sinais),
    )


# ===========================================================================
# O ADAPTADOR
# ===========================================================================
class InfoCapProvider:
    """O adaptador InfoCap. **Envolve** o conector; não o reescreve."""

    provider_key = PROVIDER_KEY

    # ── capacidades ────────────────────────────────────────────────────────
    def capacidades(self) -> CapacidadeDoProvider:
        """O que a InfoCap consegue entregar, medido — não presumido.

        📊 `parcelas_em_aberto` = **PARCIAL** e não SUPORTADA: `/parcelas`
        responde **403** hoje (P-PILOTO-19). O adaptador entrega as parcelas
        que o `/documento` já traz no pack, e **declara** que é parcial — quem
        chama não pode ler lista vazia como "não deve nada".

        🔴 `listar_apolices` passou a **SUPORTADA** no BLOCO B: o conector expõe
        `policies_all` (a lista inteira, sem corte) ao lado de `matches` (o
        recorte de TEXTO, teto de prompt), e `linhas_cruas_da_listagem` lê a
        primeira. 📊 O caso que obrigou a emenda é real: a empresa da pergunta
        q4 tem `documents_count` **11** e `matches` **10** — a única VIGENTE
        podia estar na 11ª, e a porta responderia "nenhuma vigente" MENTINDO.
        """
        por_operacao: Dict[str, Capacidade] = {
            "buscar_cliente": "SUPORTADA",
            "listar_apolices": "SUPORTADA",
            "detalhar_apolice": "SUPORTADA",
            "documento_oficial": "PARCIAL",
            "parcelas_em_aberto": "PARCIAL",
        }
        return CapacidadeDoProvider(
            provider_key=self.provider_key,
            por_operacao=por_operacao,
            notas={
                "listar_apolices": "le a lista inteira (`policies_all`); `matches` continua truncado em 10 para o TEXTO, nunca para decidir",
                "documento_oficial": "o extrator de linhas nao le os dois layouts reais de tabela (D4; BLOCO D)",
                "parcelas_em_aberto": "P-PILOTO-19: /parcelas responde 403; as parcelas vem do /documento",
            },
        )

    # ── as cinco operações ─────────────────────────────────────────────────
    async def buscar_cliente(
        self,
        *,
        company_id: str,
        documento: Optional[str] = None,
        telefone: Optional[str] = None,
        nome: Optional[str] = None,
        db: Any = None,
        internal_key: Optional[str] = None,
        **kwargs: Any,
    ) -> ResultadoDeBusca:
        """Acha o cliente. ⛔ Devolve `cliente_ref` opaco — nunca nome nem CPF.

        ⚠️ `telefone` ainda não é chave de busca na fonte: ele entra como sinal
        `busca_por_telefone_nao_suportada` em vez de virar uma busca por nome
        que traria outra pessoa.
        """
        if telefone and not documento and not nome:
            return ResultadoDeBusca(
                encontrado=False,
                motivo="busca_por_telefone_nao_suportada",
                sinais=(Sinal("busca_por_telefone_nao_suportada", {}),),
                provider_key=self.provider_key,
            )
        bruto = await self.lookup(
            company_id=company_id, document=documento, name=nome,
            db=db, internal_key=internal_key,
        )
        return _resultado_de_busca(bruto, self.provider_key)

    async def listar_apolices(
        self,
        *,
        company_id: str,
        cliente_ref: str,
        incluir_vencidas: bool = False,
        ramo: Optional[RamoCanonico] = None,
        hoje: Optional[date] = None,
        db: Any = None,
        internal_key: Optional[str] = None,
        resposta_do_lookup: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> ListaDeApolices:
        """A lista CLASSIFICADA por DATA. A ESCOLHA é `escolher_apolice`.

        ⚠️ `resposta_do_lookup` não é vazamento de fornecedor: é a MESMA
        resposta devolvida ao adaptador que a produziu. 📊 Sem ele o caminho do
        chat faria **duas** chamadas idênticas à fonte por pergunta (uma para o
        pack, outra para a lista) — o corretor pagaria a latência duas vezes
        para ler o mesmo JSON.
        """
        bruto = resposta_do_lookup if isinstance(resposta_do_lookup, dict) else await self.lookup(
            company_id=company_id, document=cliente_ref,
            db=db, internal_key=internal_key,
        )
        return lista_de_apolices_do_lookup(
            bruto, cliente_ref=cliente_ref, incluir_vencidas=incluir_vencidas,
            ramo=ramo, hoje=hoje, provider_key=self.provider_key,
        )

    async def detalhar_apolice(
        self,
        *,
        company_id: str,
        apolice_ref: str,
        db: Any = None,
        internal_key: Optional[str] = None,
        **kwargs: Any,
    ) -> Apolice:
        """A apólice inteira: cadastro **reconciliado** com o documento oficial.

        🔴 A leitura documental é um passo do **caminho feliz**, não um
        `except`: o pack já vem com a evidência documental quando ela existe, e
        `reconciliar` é chamado sempre — com `None` quando não há documento.
        """
        bruto = await self.detail(
            company_id=company_id, policy_ref=apolice_ref,
            document_evidence_requested=True, db=db, internal_key=internal_key,
        )
        pack = bruto.get("policy_evidence_pack") if isinstance(bruto, dict) else None
        if not isinstance(pack, dict):
            raise ValueError(
                "InfoCap nao devolveu pack para %r (status=%r)"
                % (apolice_ref, (bruto or {}).get("status"))
            )
        return apolice_reconciliada_do_pack(pack, apolice_ref=apolice_ref, hoje=kwargs.get("hoje"))

    async def documento_oficial(
        self,
        *,
        company_id: str,
        apolice_ref: str,
        db: Any = None,
        internal_key: Optional[str] = None,
        **kwargs: Any,
    ) -> Optional[DocumentoOficial]:
        bruto = await self.detail(
            company_id=company_id, policy_ref=apolice_ref,
            document_evidence_requested=True, db=db, internal_key=internal_key,
        )
        pack = bruto.get("policy_evidence_pack") if isinstance(bruto, dict) else None
        if not isinstance(pack, dict):
            return None
        referencia = _referencia_do_documento(pack)
        if referencia is None:
            return None
        return DocumentoOficial(
            referencia=referencia,
            conteudo=apolice_documental_do_pack(pack),
            disponivel=bool(pack.get("document_evidence_ready")),
            motivo_de_ausencia=(None if pack.get("document_evidence_ready")
                                else "leitura documental nao concluida"),
        )

    async def parcelas_em_aberto(
        self,
        *,
        company_id: str,
        cliente_ref: str,
        db: Any = None,
        internal_key: Optional[str] = None,
        **kwargs: Any,
    ) -> List[Parcela]:
        """As parcelas ainda não quitadas do cliente.

        🔴 **PARCIAL, e `capacidades()` diz isso antes** (P-PILOTO-19: 📊 a rota
        `/parcelas` da fonte responde **403**). Estas vêm do `/documento`, que é
        a apólice selecionada — não a carteira inteira do cliente. Lista vazia
        aqui **não** significa "não deve nada", e quem chama tem de perguntar a
        capacidade antes de afirmar qualquer coisa ao segurado.
        """
        bruto = await self.lookup(
            company_id=company_id, document=cliente_ref, db=db, internal_key=internal_key,
        )
        pack = bruto.get("policy_evidence_pack") if isinstance(bruto, dict) else None
        if not isinstance(pack, dict):
            return []
        return [p for p in _parcelas_do_pack(pack) if p.em_aberto]

    # ── os três DEPRECIADOS — delegam EXATAMENTE como antes ────────────────
    async def lookup(
        self,
        *,
        company_id: str,
        document: Optional[str] = None,
        name: Optional[str] = None,
        policy_number: Optional[str] = None,
        user_query: Optional[str] = None,
        document_evidence_requested: bool = False,
        force_document_evidence_refresh: bool = False,
        unmasked: bool = True,
        db: Any = None,
        internal_key: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """DEPRECIADO — sai quando a tabela §5.1.1 estiver toda migrada; o item
        7 (`billing_collection.py:1205-1212`) é da EXTRA-001.6."""
        from app.api.infocap_connector import InfocapLookupPayload, infocap_lookup

        payload = InfocapLookupPayload(
            company_id=company_id,
            document=document or None,
            name=name or None,
            policy_number=policy_number or None,
            user_query=user_query,
            document_evidence_requested=bool(document_evidence_requested),
            force_document_evidence_refresh=bool(force_document_evidence_refresh),
            unmasked=bool(unmasked),
        )
        return await infocap_lookup(payload=payload, x_autobrokers_internal_key=internal_key, db=db)

    async def detail(
        self,
        *,
        company_id: str,
        policy_ref: str,
        user_query: Optional[str] = None,
        document_evidence_requested: bool = False,
        force_document_evidence_refresh: bool = False,
        unmasked: bool = True,
        db: Any = None,
        internal_key: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """DEPRECIADO — sai quando a tabela §5.1.1 estiver toda migrada; o item
        7 (`billing_collection.py:1205-1212`) é da EXTRA-001.6."""
        from app.api.infocap_connector import InfocapPolicyDetailPayload, infocap_policy_detail

        payload = InfocapPolicyDetailPayload(
            company_id=company_id,
            policy_ref=str(policy_ref),
            user_query=user_query,
            document_evidence_requested=bool(document_evidence_requested),
            force_document_evidence_refresh=bool(force_document_evidence_refresh),
            unmasked=bool(unmasked),
        )
        return await infocap_policy_detail(payload=payload, x_autobrokers_internal_key=internal_key, db=db)

    async def vehicle(
        self,
        *,
        company_id: str,
        document: str,
        policy_number: Optional[str] = None,
        db: Any = None,
        internal_key: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """DEPRECIADO — sai quando a tabela §5.1.1 estiver toda migrada; o item
        7 (`billing_collection.py:1205-1212`) é da EXTRA-001.6.

        SPEC-025: item do veículo da apólice AUTO (placa/chassi/veículo/fipe) +
        cadastro do cliente — a fonte para a `portal_action` montar o job com
        dados REAIS (o LLM nunca fornece placa/endereço).
        """
        from app.api.infocap_connector import InfocapVehiclePayload, infocap_vehicle_item

        payload = InfocapVehiclePayload(
            company_id=company_id,
            document=document,
            policy_number=policy_number or None,
        )
        return await infocap_vehicle_item(payload=payload, x_autobrokers_internal_key=internal_key, db=db)


#: 🔴 O nome antigo continua importável. 📊 Cinco módulos e oito pontos de
#: chamada falam com esta porta hoje — renomear sem alias quebraria os oito, e
#: um deles é a rotina de cobrança de uma SPEC irmã em execução simultânea.
InfocapPolicyDataProvider = InfoCapProvider


# ===========================================================================
# As funções PURAS que o adaptador usa — e que os guardas exercitam direto
# ===========================================================================
def apolice_reconciliada_do_pack(
    pack: Dict[str, Any],
    *,
    apolice_ref: Optional[str] = None,
    documento_cru: Optional[Dict[str, Any]] = None,
    itens_crus: Optional[Sequence[Any]] = None,
    documental: Optional[ApoliceDocumental] = None,
    hoje: Optional[date] = None,
) -> Apolice:
    """pack → `Apolice` do cadastro → `reconciliar` com o documento → `Apolice`.

    ⚠️ `documental` existe para que os guardas do BLOCO A alimentem as linhas do
    PDF a partir do golden REAL enquanto o extrator do BLOCO D não lê as duas
    tabelas (D4). Em produção ele é `None` e a leitura sai do próprio pack.
    """
    cadastro = apolice_do_pack(
        pack, apolice_ref=apolice_ref, documento_cru=documento_cru,
        itens_crus=itens_crus, hoje=hoje,
    )
    do_documento = documental if documental is not None else apolice_documental_do_pack(pack)
    return reconciliar(cadastro, do_documento)


def _resultado_de_busca(bruto: Any, provider_key: str) -> ResultadoDeBusca:
    if not isinstance(bruto, dict):
        return ResultadoDeBusca(encontrado=False, motivo="resposta_invalida", provider_key=provider_key)
    status = str(bruto.get("status") or "").strip()
    encontrado = status in ("found", "ambiguous_policy", "policy_number_ambiguous")
    cliente = None
    for match in bruto.get("matches") or []:
        if isinstance(match, dict) and match.get("policy_locator_ref"):
            cliente = str(match.get("policy_locator_ref"))
            break
    return ResultadoDeBusca(
        encontrado=encontrado,
        cliente_ref=cliente,
        quantidade_de_apolices=int(bruto.get("documents_count") or 0),
        motivo=(None if encontrado else (status or "nao_encontrado")),
        provider_key=provider_key,
    )


#: 🔴 A lista INTEIRA vem aqui; `matches` é o recorte de TEXTO (teto de prompt).
#: `infocap_connector.py` passou a devolver as duas (SPEC-EXTRA-001.1 §6.1).
CHAVE_DA_LISTA_INTEIRA = "policies_all"


def linhas_cruas_da_listagem(bruto: Any) -> List[Dict[str, Any]]:
    """As apólices da resposta do `lookup`, **sem truncamento**.

    📊 Medido em 14/09/2026: `infocap_connector.py` devolve `matches` cortado em
    10 (`policies[:10]`) e `documents_count` cheio. A empresa da pergunta q4 do
    acervo tem `documents_count` **11** e `matches` **10** — a única VIGENTE
    podia estar na 11ª posição, e a porta concluiria *"nenhuma vigente"*.
    Desde o BLOCO B o conector expõe também `policies_all`; esta função prefere
    a lista inteira e cai em `matches` só quando ela não existe (respostas
    gravadas antes da emenda, e o `found`, que já vem com uma só).
    """
    if not isinstance(bruto, dict):
        return []
    inteira = bruto.get(CHAVE_DA_LISTA_INTEIRA)
    fonte = inteira if isinstance(inteira, list) and inteira else (bruto.get("matches") or [])
    return [m for m in fonte if isinstance(m, dict)]


def lista_de_apolices_do_lookup(
    bruto: Any,
    *,
    cliente_ref: Optional[str] = None,
    incluir_vencidas: bool = False,
    ramo: Optional[RamoCanonico] = None,
    hoje: Optional[date] = None,
    provider_key: str = PROVIDER_KEY,
) -> ListaDeApolices:
    """A resposta do `lookup` → `ListaDeApolices` CLASSIFICADA por vigência.

    🔴 **Lê a lista INTEIRA, e classifica cada apólice pela DATA.** O
    `policy_status` do fornecedor entra como sinal e nunca como veredito
    (`classificar_vigencia`).

    🔴 **`historico_oculto` deriva de `documents_count`**, nunca de
    `len(matches)` — é a única fonte que conhece o tamanho real. E ele conta o
    que a resposta NÃO mostra: as vencidas/canceladas filtradas **mais** o que
    a fonte truncou. 📊 Para a empresa de 11 apólices com 1 vigente ele dá
    **10**, e não 1 (que era a conta do truncamento sozinho).
    """
    if not isinstance(bruto, dict):
        return ListaDeApolices(provider_key=provider_key)
    brutas = linhas_cruas_da_listagem(bruto)
    lidas = [a for a in (_apolice_na_lista(m, hoje=hoje) for m in brutas) if a is not None]
    total = int(bruto.get("documents_count") or len(lidas))

    # A conta do oculto é feita ANTES do filtro de ramo: apólice de outro ramo
    # não é "histórico", é outra pergunta. Só vigência e truncamento ocultam.
    elegiveis = [a for a in lidas if a.vigencia.situacao not in SITUACOES_OCULTAS]
    oculto = max(0, total - (len(lidas) if incluir_vencidas else len(elegiveis)))

    itens = lidas if incluir_vencidas else elegiveis
    if ramo is not None:
        familia = familia_de_ramo(ramo)
        if familia:
            itens = [a for a in itens if familia_de_ramo(a.ramo) == familia]
        else:
            alvo = normalizar_rotulo(ramo.abreviatura if isinstance(ramo, RamoCanonico) else ramo)
            itens = [a for a in itens if normalizar_rotulo(a.ramo.abreviatura) == alvo]

    sinais: List[Sinal] = []
    truncadas = max(0, total - len(lidas))
    if truncadas:
        sinais.append(Sinal("lista_truncada_pela_fonte", {
            "total": total, "devolvidas": len(brutas), "nao_devolvidas": truncadas,
        }))
    if oculto:
        sinais.append(Sinal("historico_oculto", {
            "total": total, "mostradas": len(itens), "historico_oculto": oculto,
        }))
    return ListaDeApolices(
        itens=tuple(itens),
        total=total,
        historico_oculto=oculto,
        cliente_ref=cliente_ref,
        sinais=tuple(sinais),
        provider_key=provider_key,
    )


# ===========================================================================
# 🔴 O adaptador se registra no PROPRIO fim — e o porque esta medido
# ===========================================================================
#
# A porta importa este modulo para registra-lo, e este modulo importa a porta.
# Quem importar O ADAPTADOR primeiro encontra a porta a meio inicializar, e o
# registro da porta falha com `ImportError: cannot import name
# 'InfoCapProvider' from partially initialized module`. O sintoma seria o pior
# possivel: `get_policy_data_provider("infocap")` devolvendo `None` conforme a
# ORDEM DE IMPORTACAO do processo — e o atendente respondendo "fonte
# indisponivel" em metade dos deploys, sem nada quebrar.
#
# Aqui, no fim do arquivo, a classe ja existe. `register_policy_data_provider`
# e idempotente e RECUSA adaptador incompleto, entao registrar duas vezes e
# inofensivo e registrar errado continua impossivel.
def _registrar_se() -> None:
    try:
        from app.providers.policy_data_provider import register_policy_data_provider

        register_policy_data_provider(InfoCapProvider())
    except Exception as exc:  # noqa: BLE001
        logger.warning("[APOLICE] auto-registro do InfoCap falhou: %s", exc)


_registrar_se()
