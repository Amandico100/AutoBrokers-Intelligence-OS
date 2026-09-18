# -*- coding: utf-8 -*-
"""Onda 2 — o elo entre a APÓLICE do segurado e a CONDIÇÃO GERAL que a rege.

SPEC-EXTRA-001.5 · BLOCO C (§7.2). Módulo pequeno de propósito: ele responde
uma pergunta só, e é uma pergunta de fato, não de opinião.

    "qual documento normativo rege ESTE contrato, na data em que foi emitido?"

🔴 O DEFEITO QUE ELE IMPEDE — e está escrito no próprio corpus
=============================================================
O docstring de abertura de `insurance_corpus.py` já avisava:

> *"Uma apólice emitida em 2023 é regida pela condição vigente **na emissão**,
> não pela de hoje. Um cache que guarda 'a condição atual' e responde sobre uma
> apólice antiga pode estar confiantemente errado sobre cobertura — e o corretor
> repete isso para o cliente."*

Só que ninguém consumia o elo: 📊 17/09/2026, `rg 'eq("susep_process"'` sobre
`backend/app` devolvia **zero linhas, exit 1**. O processo estava gravado em
**190 de 194** documentos e não era usado para nada. Este módulo é o consumidor.

🔴 NADA CASA → `None`. NUNCA "a mais parecida"
==============================================
A tentação natural aqui é devolver a condição geral da mesma seguradora e ramo
quando o processo não existe no corpus — *"é quase a mesma coisa"*. Não é: o
processo SUSEP identifica **o produto registrado**, e dois produtos da mesma
seguradora no mesmo ramo têm assistências diferentes. Uma resposta "quase certa"
sobre cobertura chega ao segurado como certa. Por isso a função devolve `None`,
e o par de controle do M-C2 prova que ela devolve.

⚠️ O TEXTO QUE ENTRA É O INTEGRAL, NÃO O FRAGMENTO
==================================================
📊 BLOCO 0, 17/09/2026: `extrair_susep(build_document_plain_text(pages))` devolve
`15414.900228/2017-63` num PDF real do acervo, e `build_document_plain_text`
**não** passa por `is_boilerplate_fragment` — o filtro de boilerplate (que
descarta linha com "susep") governa só os fragmentos de evidência. Por isso
`_BOILERPLATE_RE` **não é tocado** (SPEC §7.2 ②): mexer nele seria alterar um
guarda de outro fim para consertar um caminho onde ele nem está.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CondicaoGeralDaApolice:
    """O documento + a VERSÃO vigente na emissão. Tudo com nome e origem."""

    documento_id: str
    susep_process: str
    insurer_key: Optional[str]
    product_line: Optional[str]
    doc_kind: Optional[str]
    title: Optional[str]
    versao: Optional[int]
    effective_from: Optional[str]
    effective_until: Optional[str]
    data_de_referencia: Optional[str]
    origem: str = "susep_process"

    def para_registro(self) -> Dict[str, Any]:
        """Procedência, nunca conteúdo — o formato do `input_summary` (§9)."""
        return {
            "documento_id": self.documento_id,
            "susep_process": self.susep_process,
            "insurer_key": self.insurer_key,
            "versao": self.versao,
            "vigente_em": self.data_de_referencia,
            "origem": self.origem,
        }


def _data(valor: Any) -> Optional[date]:
    """Aceita `date`, `datetime`, ISO e `dd/mm/aaaa`. Não adivinha o resto."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    bruto = str(valor).strip()
    if "/" in bruto:
        partes = bruto.split("/")
        if len(partes) == 3 and len(partes[2]) == 4:
            try:
                return date(int(partes[2]), int(partes[1]), int(partes[0]))
            except ValueError:
                return None
        return None
    try:
        return datetime.fromisoformat(bruto.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _vigente_em(versoes: List[Dict[str, Any]], quando: Optional[date]) -> Optional[Dict[str, Any]]:
    """A versão cujo intervalo contém `quando`. 🔴 NUNCA `now()` (M-C3).

    `effective_until` nulo = ainda vigente (o `coalesce(..., 'infinity')` de
    §7.2, escrito aqui em Python porque a comparação de datas acontece depois do
    SELECT — e fazê-la no SQL obrigaria a passar a data para dentro da query do
    cliente Supabase, que o `db` duplo dos guardas não sabe interpretar).

    Sem data de emissão: devolve a **mais recente**, e quem chama recebe isso
    escrito em `data_de_referencia=None` — é uma resposta mais fraca, declarada,
    não um palpite silencioso.
    """
    if not versoes:
        return None
    ordenadas = sorted(versoes, key=lambda v: int(v.get("version") or 0), reverse=True)
    if quando is None:
        return ordenadas[0]
    for v in ordenadas:
        inicio = _data(v.get("effective_from"))
        fim = _data(v.get("effective_until"))
        if inicio is not None and quando < inicio:
            continue
        if fim is not None and quando >= fim:
            continue
        return v
    return None


def condicao_geral_da_apolice(
    document_text: Any,
    data_emissao: Any = None,
    *,
    db: Any = None,
    insurer_key: Optional[str] = None,
) -> Optional[CondicaoGeralDaApolice]:
    """O texto integral da apólice → a condição geral que a rege, ou `None`.

    ```
    extrair_susep(document_text)                  o processo, do próprio PDF
      → normative_documents where susep_process   o documento, por igualdade
        → a versão VIGENTE em data_emissao        nunca a de hoje (M-C3)
    ```

    `insurer_key` é **opcional e só serve para LOG**: casar por processo já é
    identidade; usá-lo como filtro faria uma divergência de normalização de
    seguradora esconder um documento que casa.
    """
    from .insurance_corpus import extrair_susep

    processo = extrair_susep(str(document_text or ""))
    if not processo:
        return None

    cliente = db if db is not None else _cliente()
    docs = (
        cliente.table("normative_documents")
        .select("id, insurer_key, product_line, doc_kind, title, susep_process")
        .eq("susep_process", str(processo))
        .execute()
    ).data or []
    if not docs:
        # 🔴 o caminho de controle do M-C2: processo que não existe no corpus.
        logger.info("[susep-link] processo sem documento no corpus")
        return None
    doc = docs[0]
    if len(docs) > 1 and insurer_key:
        doc = next((d for d in docs if str(d.get("insurer_key")) == str(insurer_key)), docs[0])

    quando = _data(data_emissao)
    versoes = (
        cliente.table("normative_document_versions")
        .select("version, effective_from, effective_until, superseded_at, storage_ref")
        .eq("document_id", str(doc["id"]))
        .execute()
    ).data or []
    v = _vigente_em(versoes, quando) or {}

    return CondicaoGeralDaApolice(
        documento_id=str(doc["id"]),
        susep_process=str(processo),
        insurer_key=doc.get("insurer_key"),
        product_line=doc.get("product_line"),
        doc_kind=doc.get("doc_kind"),
        title=doc.get("title"),
        versao=int(v["version"]) if v.get("version") is not None else None,
        effective_from=str(v.get("effective_from")) if v.get("effective_from") else None,
        effective_until=str(v.get("effective_until")) if v.get("effective_until") else None,
        data_de_referencia=quando.isoformat() if quando else None,
    )


def _cliente() -> Any:
    from ...core.database import get_supabase_client

    return get_supabase_client().client
