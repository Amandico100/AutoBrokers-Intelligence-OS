# -*- coding: utf-8 -*-
r"""🔴 M-C3 · A CONDIÇÃO É A DA EMISSÃO, NÃO A DE HOJE.

SPEC-EXTRA-001.5 · BLOCO C (§7.2). O aviso já estava escrito no próprio corpus,
na abertura de `insurance_corpus.py`, antes desta SPEC existir:

> *"Uma apólice emitida em 2023 é regida pela condição vigente **na emissão**,
> não pela de hoje. Um cache que guarda 'a condição atual' e responde sobre uma
> apólice antiga pode estar **confiantemente errado** sobre cobertura — e o
> corretor repete isso para o cliente."*

📊 `normative_document_versions` tem **206 linhas para 194 documentos**, com
`effective_from`/`effective_until`: o corpus **sustenta** a pergunta certa. O que
faltava era alguém fazê-la.

🔴 **O par de controle é o coração deste guarda:** o MESMO processo, as MESMAS
duas versões, e duas datas de emissão. Se as duas datas devolvessem a mesma
versão, a função estaria ignorando a data — que é exatamente a mutação (c),
`now()` no lugar de `data_emissao`. Um guarda em que os dois lados dão o mesmo
resultado não guarda nada (CLAUDE.md §9.3).
"""
from __future__ import annotations

import os
import sys
from datetime import date

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.knowledge.assistance_plans_susep_link import (  # noqa: E402
    condicao_geral_da_apolice,
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


PROCESSO = "15414.900666/2014-89"
DOC = "fba57b04-9962-4070-8963-1db856d02370"
TEXTO = "APOLICE\nCondicoes Gerais\nProcesso SUSEP N: %s" % PROCESSO


def _corpus_com_duas_versoes() -> BaseEmMemoria:
    """O mesmo documento, duas versões — a antiga fechada, a nova aberta."""
    db = BaseEmMemoria()
    db.tabelas["normative_documents"] = [{
        "id": DOC, "insurer_key": "bradesco", "product_line": "auto",
        "doc_kind": "condicoes_gerais", "title": "Condicoes gerais auto",
        "susep_process": PROCESSO,
    }]
    db.tabelas["normative_document_versions"] = [
        {"document_id": DOC, "version": 1, "storage_ref": "acervo/v1.pdf",
         "effective_from": "2014-01-01", "effective_until": "2022-01-01",
         "superseded_at": "2022-01-01"},
        {"document_id": DOC, "version": 2, "storage_ref": "acervo/v2.pdf",
         "effective_from": "2022-01-01", "effective_until": None, "superseded_at": None},
    ]
    return db


print("\n[1] apólice ANTIGA -> a versão vigente NA EMISSÃO")
antiga = condicao_geral_da_apolice(TEXTO, "2019-08-14", db=_corpus_com_duas_versoes())
checar(antiga is not None and antiga.versao == 1,
       "🔴 emitida em 2019 -> versão 1 (a que valia em 2019)",
       repr(antiga))
checar(antiga is not None and antiga.data_de_referencia == "2019-08-14",
       "e a data que decidiu está ESCRITA no resultado — não é implícita",
       repr(antiga.data_de_referencia if antiga else None))

print("\n[2] 🔴 O PAR DE CONTROLE: apólice de HOJE -> a versão atual")
hoje = condicao_geral_da_apolice(TEXTO, date.today(), db=_corpus_com_duas_versoes())
checar(hoje is not None and hoje.versao == 2,
       "🔴 emitida hoje -> versão 2",
       repr(hoje))
checar(antiga is not None and hoje is not None and antiga.versao != hoje.versao,
       "🔴 E AS DUAS SÃO DIFERENTES — o par CONSEGUE distinguir, logo a data é lida",
       f"antiga={antiga.versao if antiga else None} hoje={hoje.versao if hoje else None}")

print("\n[3] os limites do intervalo, que é onde o erro de sinal mora")
na_virada = condicao_geral_da_apolice(TEXTO, "2022-01-01", db=_corpus_com_duas_versoes())
checar(na_virada is not None and na_virada.versao == 2,
       "no dia exato da virada vale a NOVA (`effective_from <= data < effective_until`)",
       repr(na_virada.versao if na_virada else None))
vespera = condicao_geral_da_apolice(TEXTO, "2021-12-31", db=_corpus_com_duas_versoes())
checar(vespera is not None and vespera.versao == 1,
       "e na véspera ainda vale a ANTIGA", repr(vespera.versao if vespera else None))

print("\n[4] antes de existir versão nenhuma, e sem data")
antes = condicao_geral_da_apolice(TEXTO, "2010-01-01", db=_corpus_com_duas_versoes())
checar(antes is not None and antes.versao is None,
       "apólice anterior à primeira versão: o documento é achado, a VERSÃO fica vazia "
       "— nunca a versão de hoje por default",
       repr(antes))
sem_data = condicao_geral_da_apolice(TEXTO, None, db=_corpus_com_duas_versoes())
checar(sem_data is not None and sem_data.versao == 2
       and sem_data.data_de_referencia is None,
       "⚠️ sem data de emissão: devolve a mais recente E declara que não houve data",
       repr(sem_data))

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
