# -*- coding: utf-8 -*-
"""`PdfOnlyProvider` — a corretora que não tem sistema de gestão. §5.6.

🔴 **Ele não é enfeite: é ele que prova que o contrato é um contrato.**

Um `Protocol` com um único implementador não é uma fronteira — é um arquivo com
uma classe dentro. Enquanto só a InfoCap implementar a porta, nada impede que
uma decisão da InfoCap vaze para a assinatura e ninguém perceba. O segundo
adaptador é o teste permanente disso, e ele é o mais pobre de propósito: se a
porta puder ser satisfeita por quem **só tem o PDF**, ela não está pedindo nada
que seja da InfoCap.

```
capacidades()
   buscar_cliente ....... INDISPONIVEL   não há cadastro para procurar
   listar_apolices ...... PARCIAL        só as apólices cujo PDF foi entregue
   detalhar_apolice ..... SUPORTADA      o documento é a fonte, e é inteira
   documento_oficial .... SUPORTADA      é literalmente o que ele tem
   parcelas_em_aberto ... INDISPONIVEL   quitação muda todo dia; o PDF congela
```

⚠️ `INDISPONIVEL` aqui é **medido**, não presumido — por isso não é
`DESCONHECIDA`. A diferença importa: `DESCONHECIDA` lê-se *"não verificado"*, e
quem a recebe pode tentar; `INDISPONIVEL` lê-se *"perguntei e a fonte não
tem"*, e quem a recebe não promete nada ao segurado.

🔴 **Todas as origens são `documento_oficial`.** É a outra metade da prova: uma
`Apolice` montada só do documento tem de passar pelos mesmos guardas de origem
por linha que a da InfoCap.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.providers.policy_data_provider import (
    INDISPONIVEL,
    Apolice,
    ApoliceDocumental,
    CampoComOrigem,
    Capacidade,
    CapacidadeDoProvider,
    Cobertura,
    DocumentoOficial,
    ListaDeApolices,
    Parcela,
    PlanoDeAssistencia,
    RamoCanonico,
    ResultadoDeBusca,
    SeguradoraCanonica,
    Sinal,
    UNKNOWN,
    Vigencia,
    classificar_vigencia,
    grupo_de_rotulo,
    normalizar_rotulo,
)

logger = logging.getLogger(__name__)

__all__ = ["PdfOnlyProvider", "apolice_do_documento"]

PROVIDER_KEY = "pdf_only"
DOCUMENTO_OFICIAL = "documento_oficial"


def _campo(valor: Any, **detalhe: Any) -> CampoComOrigem[Any]:
    """Todo campo deste adaptador nasce com `origem="documento_oficial"`.

    ⚠️ A origem e ESCRITA na chamada, e nao a constante `DOCUMENTO_OFICIAL`:
    o verificador de tipos precisa ver o literal para conferir o `Literal[...]`
    do `CampoComOrigem`. Uma constante `str` passaria pelo `mypy` sem prova, e
    a prova e o GATE A1 inteiro.
    """
    return CampoComOrigem(
        valor=(INDISPONIVEL if valor in (None, "") else valor),
        origem="documento_oficial",
        confianca="alta",
        detalhe={k: v for k, v in detalhe.items() if v not in (None, "")},
    )


def apolice_do_documento(
    documental: ApoliceDocumental,
    *,
    apolice_ref: str,
    numero_humano: str = "",
    seguradora: Optional[SeguradoraCanonica] = None,
    ramo: Optional[RamoCanonico] = None,
    inicio: Any = None,
    fim: Any = None,
    hoje: Optional[date] = None,
) -> Apolice:
    """`ApoliceDocumental` → `Apolice` completa, com TODAS as origens no documento.

    ⚠️ Seguradora e ramo chegam por parâmetro porque quem só tem o PDF **não os
    deduz do texto**: deduzir a seguradora de uma palavra no cabeçalho é
    exatamente o casamento por derivação de string que o catálogo proíbe (📊 o
    token `SEGUROS` casou 284 candidatos no censo da 094.1). Sem parâmetro, sai
    `UNKNOWN` — que é a verdade, e é uma string que atravessa escrita.
    """
    coberturas: List[Cobertura] = []
    for linha in documental.linhas:
        detalhe = {"pagina": linha.pagina} if linha.pagina else {}
        coberturas.append(Cobertura(
            rotulo=linha.rotulo,
            rotulo_normalizado=normalizar_rotulo(linha.rotulo),
            limite=_campo(linha.limite, **detalhe),
            franquia=_campo(linha.franquia_texto, **detalhe),
            premio=_campo(linha.premio, **detalhe),
            grupo=grupo_de_rotulo(linha.rotulo),
        ))
    return Apolice(
        apolice_ref=apolice_ref,
        numero_humano=str(numero_humano or ""),
        seguradora=seguradora or SeguradoraCanonica(chave=UNKNOWN, coenti=UNKNOWN),
        ramo=ramo or RamoCanonico(abreviatura=UNKNOWN, cogrupo=UNKNOWN),
        vigencia=classificar_vigencia(inicio, fim, False, hoje=hoje),
        coberturas=tuple(coberturas),
        parcelas=tuple(documental.parcelas),
        premio_liquido=(_campo(documental.premio_liquido)
                        if not isinstance(documental.premio_liquido, type(INDISPONIVEL)) else None),
        plano_de_assistencia=documental.plano_de_assistencia,
        sinais=(Sinal("sem_sistema_de_gestao", {
            "detalhe": "a apolice foi montada so do documento oficial; parcela, "
                       "quitacao e status nao tem fonte viva",
        }),),
        documento=documental.referencia,
        provider_key=PROVIDER_KEY,
    )


class PdfOnlyProvider:
    """Adaptador mínimo: uma `Apolice` montada só do documento oficial.

    O acervo é injetado (`documentos`), porque este provider não tem fonte
    remota: quem o instancia é quem sabe onde os PDFs já lidos moram.
    """

    provider_key = PROVIDER_KEY

    def __init__(self, documentos: Optional[Dict[str, ApoliceDocumental]] = None) -> None:
        self._documentos: Dict[str, ApoliceDocumental] = dict(documentos or {})

    def capacidades(self) -> CapacidadeDoProvider:
        por_operacao: Dict[str, Capacidade] = {
            "buscar_cliente": "INDISPONIVEL",
            "listar_apolices": "PARCIAL",
            "detalhar_apolice": "SUPORTADA",
            "documento_oficial": "SUPORTADA",
            "parcelas_em_aberto": "INDISPONIVEL",
        }
        return CapacidadeDoProvider(
            provider_key=self.provider_key,
            por_operacao=por_operacao,
            notas={
                "buscar_cliente": "nao ha cadastro de cliente: o documento nao indexa pessoa",
                "listar_apolices": "so as apolices cujo documento ja foi lido",
                "parcelas_em_aberto": "quitacao muda todo dia e o PDF congela na emissao",
            },
        )

    async def buscar_cliente(
        self,
        *,
        company_id: str,
        documento: Optional[str] = None,
        telefone: Optional[str] = None,
        nome: Optional[str] = None,
        **kwargs: Any,
    ) -> ResultadoDeBusca:
        """⛔ Sempre `encontrado=False`, com o motivo escrito. **Não é falha.**

        É a diferença entre *"procurei e não achei"* e *"não tenho como
        procurar"*. `capacidades()` já dizia `INDISPONIVEL`, e o motivo repete
        aqui para quem chamou sem perguntar antes.
        """
        return ResultadoDeBusca(
            encontrado=False,
            motivo="sem_cadastro_de_cliente",
            sinais=(Sinal("capacidade_indisponivel", {"operacao": "buscar_cliente"}),),
            provider_key=self.provider_key,
        )

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
        """Só o que já foi lido. `total` == o que existe AQUI, e ele diz isso."""
        return ListaDeApolices(
            itens=(),
            total=len(self._documentos),
            historico_oculto=0,
            cliente_ref=cliente_ref,
            sinais=(Sinal("capacidade_parcial", {
                "operacao": "listar_apolices",
                "detalhe": "so as apolices cujo documento ja foi lido",
            }),),
            provider_key=self.provider_key,
        )

    async def detalhar_apolice(
        self, *, company_id: str, apolice_ref: str, **kwargs: Any
    ) -> Apolice:
        documental = self._documentos.get(str(apolice_ref))
        if documental is None:
            raise ValueError("documento oficial ausente para %r" % apolice_ref)
        return apolice_do_documento(
            documental,
            apolice_ref=str(apolice_ref),
            numero_humano=str(kwargs.get("numero_humano") or ""),
            seguradora=kwargs.get("seguradora"),
            ramo=kwargs.get("ramo"),
            inicio=kwargs.get("inicio"),
            fim=kwargs.get("fim"),
            hoje=kwargs.get("hoje"),
        )

    async def documento_oficial(
        self, *, company_id: str, apolice_ref: str, **kwargs: Any
    ) -> Optional[DocumentoOficial]:
        documental = self._documentos.get(str(apolice_ref))
        if documental is None:
            return None
        referencia = documental.referencia
        if referencia is None:
            from app.providers.policy_data_provider import ReferenciaDeDocumento

            referencia = ReferenciaDeDocumento(itens_de_evidencia=len(documental.linhas))
        return DocumentoOficial(referencia=referencia, conteudo=documental, disponivel=True)

    async def parcelas_em_aberto(
        self, *, company_id: str, cliente_ref: str, **kwargs: Any
    ) -> List[Parcela]:
        """⛔ Sempre vazia — e `capacidades()` diz `INDISPONIVEL` **antes**.

        🔴 É por isso que `capacidades()` existe. Lista vazia sem a capacidade
        declarada seria lida como "o cliente não deve nada", e essa frase chega
        ao segurado.
        """
        return []

    # ── os três DEPRECIADOS ────────────────────────────────────────────────
    #
    # 🔴 Eles existem aqui porque estão NO `Protocol` (§5.1.1) — e um adaptador
    # que os omitisse passaria pelo `hasattr` e falharia em silêncio no ponto de
    # chamada. Recusam com a mensagem certa em vez de devolver `{}`: um dict
    # vazio é indistinguível de "não achei nada".
    async def lookup(self, **kwargs: Any) -> Dict[str, Any]:
        """DEPRECIADO — o `PdfOnlyProvider` não tem sistema de gestão a consultar."""
        return {"ok": False, "status": "capability_unavailable", "source": PROVIDER_KEY,
                "blockers": ["sem_sistema_de_gestao"]}

    async def detail(self, **kwargs: Any) -> Dict[str, Any]:
        """DEPRECIADO — use `detalhar_apolice`, que é o caminho deste provider."""
        return {"ok": False, "status": "capability_unavailable", "source": PROVIDER_KEY,
                "blockers": ["sem_sistema_de_gestao"]}

    async def vehicle(self, **kwargs: Any) -> Dict[str, Any]:
        """DEPRECIADO — o documento não traz o item de risco em forma consultável."""
        return {"ok": False, "status": "capability_unavailable", "source": PROVIDER_KEY,
                "blockers": ["sem_item_de_risco"]}
