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

## O que o conector NÃO deixa atravessar hoje, e é preciso dizer

📊 Medido em 14/09/2026 — `_safe_envelope_summary` (`infocap_connector.py:3460-
3483`) guarda do envelope apenas os **NOMES das chaves**, nunca os valores:

```python
summary[key] = {"type": "array", "count": len(value), "sample_keys": [...]}
```

Consequência: `tabela_itens` (o nome do plano), `sit_renovacao_txt`,
`sit_sinistro_txt` e `itens[].observacoes` **não chegam ao pack** — do
`tabela_itens` sobra só o booleano `unknown_table_field_present`. O leitor
deles existe aqui e funciona (os guardas do BLOCO A o exercitam sobre o
documento cru real do golden); o que falta é o conector **carregar os valores**
no pack. O patch exato está no relatório do BLOCO A, e é do BLOCO D, que já
reescreve `_build_evidence_pack` para os dois layouts de tabela.

Sem os valores, o adaptador não inventa: o plano sai
`estado="nao_sabemos_ainda"` com o nome `INDISPONIVEL`, que é a verdade.
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
    classificar_vigencia,
    data_de,
    dinheiro,
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


def _plano_do_pack(pack: Dict[str, Any], documento_cru: Optional[Dict[str, Any]]) -> Optional[PlanoDeAssistencia]:
    """`tabela_itens` → nome do plano. Nome sem serviços = `nao_sabemos_ainda`.

    📊 Quando o valor não atravessa (o caso de hoje — ver o cabeçalho deste
    módulo), sobra o booleano `unknown_table_field_present`: sabe-se que EXISTE
    um plano e não se sabe qual. `INDISPONIVEL` diz isso; `None` diria "não
    tem", e `""` diria "tem um plano sem nome". As três leituras são
    diferentes, e só uma é verdade.
    """
    nome = None
    if isinstance(documento_cru, dict):
        nome = str(documento_cru.get("tabela_itens") or "").strip() or None
    if nome is None and not pack.get("unknown_table_field_present"):
        return None
    return PlanoDeAssistencia(
        nome=_campo(nome, SISTEMA_DE_GESTAO, confianca="media", provider_field="tabela_itens"),
        estado="nao_sabemos_ainda",
    )


def _sinais_do_pack(pack: Dict[str, Any], documento_cru: Optional[Dict[str, Any]]) -> List[Sinal]:
    """Sinais que o corretor precisa VER — inclusive o do cabeçalho que mente."""
    sinais: List[Sinal] = []
    cru = documento_cru if isinstance(documento_cru, dict) else {}

    renovacao = str(cru.get("sit_renovacao_txt") or "").strip()
    if renovacao:
        # ⚠️ SINAL, nunca veredito de vigência: quem decide vigência é
        # `classificar_vigencia(inicio, fim, cancelado, hoje)`, por DATA.
        sinais.append(Sinal("situacao_de_renovacao", {"texto": renovacao}))
    sinistro = str(cru.get("sit_sinistro_txt") or "").strip()
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

    if pack.get("cancelled"):
        sinais.append(Sinal("apolice_cancelada", {}))
    return sinais


def _franquias_em_prosa(itens_crus: Optional[Sequence[Any]]) -> Dict[str, str]:
    """`itens[].observacoes` → a prosa de franquia, por rótulo, quando vier.

    📊 O campo existe na fonte e ninguém o lia (§8.2): é ele que carrega
    *"15% dos prejuízos, mínimo R$ 600"*. Aqui a prosa é o VALOR da franquia,
    não um comentário — por isso `Cobertura.franquia` é
    `CampoComOrigem[Dinheiro | str]`.
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

    prosa = _franquias_em_prosa(itens_crus)
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
        provider_key=PROVIDER_KEY,
    )


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


def apolice_documental_do_pack(pack: Dict[str, Any]) -> Optional[ApoliceDocumental]:
    """`official_policy_document_evidence` → `ApoliceDocumental`. `None` se vazio.

    🔴 **Hoje isto devolve `None` nas duas apólices reais, e está certo que
    devolva.** 📊 Medido no BLOCO 0 (D4): `_COVERAGE_ROW_RE` exige `R$` e a
    tabela da HDI escreve `<rótulo> <LMI>   <prêmio>` sem `R$` — resultado: **0**
    `coverage_row` na HDI e **1** na Allianz, e a única é *"Prêmio Líquido"*,
    uma linha de prêmio lida como cobertura. Quem ensina o extrator a ler os
    dois layouts reais é o **BLOCO D**
    (`backend/tests/fixtures/pdf_tabelas_reais_extra0011.json` tem o texto cru).

    ⚠️ Devolver `None` é a resposta honesta: `ApoliceDocumental(linhas=())`
    diria "o documento não tem coberturas", e `reconciliar` trataria as 6
    linhas do cadastro como a apólice inteira. Ausência de LEITURA não é
    ausência de COBERTURA.
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
            if nome:
                plano = PlanoDeAssistencia(
                    nome=_campo(nome, DOCUMENTO_OFICIAL, pagina=pagina),
                    estado="contratado",
                )
    if not linhas and plano is None:
        return None
    return ApoliceDocumental(
        linhas=tuple(linhas),
        plano_de_assistencia=plano,
        referencia=_referencia_do_documento(pack),
    )


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

        ⚠️ `listar_apolices` = **PARCIAL**, e o motivo é o truncamento:
        `infocap_connector.py:1105` e `:1326` devolvem `matches` cortado em
        **10**. 📊 O caso real existe: a empresa da pergunta q4 tem
        `documents_count` **11** e `matches` **10**. `ListaDeApolices.total` traz
        `documents_count` e `historico_oculto` traz a diferença — a lista diz
        que está incompleta em vez de fingir que acabou. Fechar o truncamento é
        do BLOCO B (o patch está no relatório).
        """
        por_operacao: Dict[str, Capacidade] = {
            "buscar_cliente": "SUPORTADA",
            "listar_apolices": "PARCIAL",
            "detalhar_apolice": "SUPORTADA",
            "documento_oficial": "PARCIAL",
            "parcelas_em_aberto": "PARCIAL",
        }
        return CapacidadeDoProvider(
            provider_key=self.provider_key,
            por_operacao=por_operacao,
            notas={
                "listar_apolices": "matches truncado em 10 pela fonte; `total` e `historico_oculto` dizem o tamanho real (BLOCO B fecha)",
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
        **kwargs: Any,
    ) -> ListaDeApolices:
        """A lista CLASSIFICADA. ⚠️ A ESCOLHA (found/ambiguous) é do BLOCO B."""
        bruto = await self.lookup(
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

    🔴 **A lista sabe que está truncada, e diz.** 📊 `documents_count` é a
    contagem cheia da fonte; `matches` vem cortado em 10
    (`infocap_connector.py:1105`, `:1326`). `historico_oculto` é a diferença —
    e é o número que impede "a única vigente está na posição 11" de virar "o
    cliente não tem apólice vigente".
    """
    if not isinstance(bruto, dict):
        return ListaDeApolices(provider_key=provider_key)
    brutas = [m for m in (bruto.get("matches") or []) if isinstance(m, dict)]
    itens = [a for a in (_apolice_na_lista(m, hoje=hoje) for m in brutas) if a is not None]
    total = int(bruto.get("documents_count") or len(itens))
    oculto = max(0, total - len(itens))

    if ramo is not None and ramo.abreviatura:
        alvo = normalizar_rotulo(ramo.abreviatura)
        itens = [a for a in itens if normalizar_rotulo(a.ramo.abreviatura) == alvo]
    if not incluir_vencidas:
        itens = [a for a in itens if a.vigencia.situacao not in ("VENCIDA", "CANCELADA")]

    sinais: List[Sinal] = []
    if oculto:
        sinais.append(Sinal("lista_truncada_pela_fonte", {
            "total": total, "devolvidas": len(brutas), "historico_oculto": oculto,
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
