# -*- coding: utf-8 -*-
r"""🔴 M-C2 · O PROCESSO SUSEP DA APÓLICE ENCONTRA A CONDIÇÃO GERAL.

SPEC-EXTRA-001.5 · BLOCO C (§7.2). O processo SUSEP é a única identidade que
liga **este contrato** ao documento que o rege. 📊 17/09/2026 ele estava gravado
em **190 de 194** documentos do corpus e não era lido por ninguém:
`rg 'eq("susep_process"' backend/app` devolvia **zero linhas, exit 1**.

```
texto integral da apólice  ->  extrair_susep  ->  normative_documents  ->  a versão
```

🔴 **O PAR DE CONTROLE É O QUE DÁ DIREITO À CONCLUSÃO.** Uma apólice cujo
processo **não existe** no corpus tem de devolver **NADA** — nunca a condição
geral "mais parecida" da mesma seguradora. O processo identifica o PRODUTO
registrado, e dois produtos da mesma seguradora têm assistências diferentes: uma
resposta "quase certa" sobre cobertura chega ao segurado como certa.

⚠️ **E a terceira asserção é sobre o CAMINHO, não sobre o filtro.** O BLOCO 0
mediu que `build_document_plain_text` **não** passa por `is_boilerplate_fragment`
— logo, o filtro (que descarta linha com "susep") governa só os fragmentos de
evidência e **não está neste caminho**. Aqui isso é provado dos dois lados: o
filtro continua recusando a linha de SUSEP **e** o elo funciona mesmo assim. Por
isso `_BOILERPLATE_RE` não foi tocado (§7.2 ②).

📊 **O texto é do ACERVO REAL**, não da imaginação (CLAUDE.md §9.4): a linha
abaixo foi lida em 17/09/2026 da página 1 do documento `bradesco/auto`
`fba57b04…` (condição geral pública — sem PII).
"""
from __future__ import annotations

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.knowledge.assistance_plans_susep_link import (  # noqa: E402
    condicao_geral_da_apolice,
)
from app.services.knowledge.insurance_corpus import extrair_susep  # noqa: E402
from app.services.policy_document_evidence_service import (  # noqa: E402
    build_document_plain_text,
    is_boilerplate_fragment,
)
from base_de_planos_em_memoria import BaseEmMemoria  # noqa: E402

OK = FAIL = 0


def checar(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA \U0001F534 {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


#: 📊 A linha REAL, como o `fitz` a devolve (acervo, 17/09/2026).
LINHA_REAL = "Processo SUSEP Nº: 15414.900666/2014-89"
PROCESSO = "15414.900666/2014-89"
DOC_REAL = "fba57b04-9962-4070-8963-1db856d02370"

#: As páginas como a porta da 001.1 as entrega ao compositor.
PAGINAS_DA_APOLICE = [
    {"page": 1, "text": "APOLICE DE SEGURO AUTOMOVEL\nCondicoes Gerais\n" + LINHA_REAL},
    {"page": 2, "text": "Coberturas contratadas e limites."},
]


def _banco_do_corpus() -> BaseEmMemoria:
    """O corpus como ele é: o documento real, com uma versão vigente."""
    db = BaseEmMemoria()
    db.tabelas["normative_documents"] = [{
        "id": DOC_REAL, "insurer_key": "bradesco", "product_line": "auto",
        "doc_kind": "condicoes_gerais", "title": "Condicoes gerais auto",
        "susep_process": PROCESSO,
    }]
    db.tabelas["normative_document_versions"] = [{
        "document_id": DOC_REAL, "version": 1, "storage_ref": "acervo/x.pdf",
        "effective_from": "2014-01-01", "effective_until": None, "superseded_at": None,
    }]
    return db


print("\n[1] o texto INTEGRAL da apólice devolve o processo — pelo motor")
texto = build_document_plain_text(PAGINAS_DA_APOLICE)
checar(PROCESSO in texto,
       "🔴 `build_document_plain_text` mantém a linha de SUSEP no texto integral",
       texto[:200])
checar(extrair_susep(texto) == PROCESSO,
       "`extrair_susep` sobre esse texto devolve o processo real do acervo",
       repr(extrair_susep(texto)))

print("\n[2] e o processo CASA com o documento do corpus")
db = _banco_do_corpus()
achado = condicao_geral_da_apolice(texto, "2020-05-10", db=db)
checar(achado is not None and achado.documento_id == DOC_REAL,
       "🔴 a condição geral encontrada é a DAQUELE processo",
       repr(achado))
checar(achado is not None and achado.susep_process == PROCESSO
       and achado.origem == "susep_process",
       "e ela carrega a ORIGEM — quem perguntar de onde veio, tem resposta",
       repr(achado.para_registro() if achado else None))

print("\n[3] 🔴 O PAR DE CONTROLE: processo que NÃO existe no corpus -> NADA")
outro = ("APOLICE DE SEGURO AUTOMOVEL\nCondicoes Gerais\n"
         "Processo SUSEP Nº: 15414.999999/1999-99")
checar(extrair_susep(outro) == "15414.999999/1999-99",
       "   (o processo inexistente É extraído — o teste não falha por falta de texto)")
checar(condicao_geral_da_apolice(outro, "2020-05-10", db=_banco_do_corpus()) is None,
       "🔴 processo inexistente devolve None — NUNCA a condição 'mais parecida'")
checar(condicao_geral_da_apolice("uma apolice sem processo nenhum", "2020-05-10",
                                 db=_banco_do_corpus()) is None,
       "e texto sem processo nenhum também devolve None")

print("\n[4] ⚠️ o filtro de boilerplate NÃO está neste caminho — e continua valendo no dele")
checar(is_boilerplate_fragment(LINHA_REAL) is True,
       "🔴 `is_boilerplate_fragment` CONTINUA recusando a linha de SUSEP (fragmentos)",
       repr(is_boilerplate_fragment(LINHA_REAL)))
checar(condicao_geral_da_apolice(texto, "2020-05-10", db=_banco_do_corpus()) is not None,
       "🔴 e MESMO ASSIM o elo funciona — logo o filtro não está no caminho medido "
       "(por isso `_BOILERPLATE_RE` não foi tocado)")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
