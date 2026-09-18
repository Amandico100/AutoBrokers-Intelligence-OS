# -*- coding: utf-8 -*-
"""A tela de Conhecimento pergunta à base de planos — SPEC-EXTRA-001.5 · BLOCO D.

Três perguntas, e só três:

```
GET  /api/assistance-plans/cobertura   o que a base cobre, por seguradora × ramo
GET  /api/assistance-plans/fila        o que espera gente, com o TRECHO e a PÁGINA
POST /api/assistance-plans/curadoria   publicar (com revisor) ou rejeitar (com motivo)
```

🔴 A BASE É GLOBAL — E POR ISSO NÃO HÁ `company_id` AQUI
========================================================
O que a apólice da HDI cobre é o mesmo para a Resulta e para a AutoFleet. Nenhum
endpoint deste arquivo aceita, lê ou filtra por corretora: dois usuários de
corretoras diferentes recebem **a mesma resposta**, e é isso que o GATE D prova.
A autorização continua existindo (a sessão é validada no Next, e aqui o
`X-Internal-Key`) — o que não existe é *escopo de dados por corretora*.

🔴 O TRECHO É LIDO DA FONTE NA HORA — NUNCA GRAVADO
===================================================
A base guarda o `trecho_hash`, não o trecho. Quem cura lê a frase **do PDF
arquivado**, pelo mesmo `texto_das_paginas` que o verificador usa. Guardar uma
cópia do trecho pareceria mais rápido e criaria a pior das telas: a que mostra à
pessoa um texto que o documento já não tem, e colhe a assinatura dela nisso.

⚠️ NENHUMA SEGUNDA FILA (CLAUDE.md §5)
======================================
A fila do **DOCUMENTO** (aprovar a condição geral inteira) já existe em
`api/corpus.py` e **não é tocada**. Esta é a fila da **LINHA** — *"guincho até
200 km, página 24"* —, que é a coluna `curadoria` das tabelas da fatia 1.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, Query

from ..core.auth import require_internal_key
from ..services.knowledge import assistance_plans_base as BASE

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/assistance-plans", tags=["Planos de assistência"])

#: Quantas linhas da fila por vez. A tela é de leitura humana: 200 itens numa
#: página não são "mais informação", são uma fila que ninguém começa.
TETO_DA_FILA = 60


def _db() -> Any:
    from ..core.database import get_supabase_client

    return get_supabase_client().client


@router.get("/cobertura", dependencies=[Depends(require_internal_key)])
def cobertura() -> Dict[str, Any]:
    """Os TRÊS números que é tentador juntar, separados (SPEC §9).

    ```
    com_plano_publicado   seguradora × ramo com ao menos um plano publicado
    com_condicao_geral    seguradora com condição geral no acervo
    sem_condicao_geral    seguradora da carteira sem nem o documento
    ```

    🔴 A régua conta **seguradora × ramo**, nunca linhas — 40 linhas de um ramo
    só não são cobertura, são um ramo só bem descrito
    (`tests/test_cobertura_nao_mente_para_cima.py`: 📊 Allianz, painel 63 %,
    real 37 %). Guarda M-D1.
    """
    cliente = _db()
    por_chave = BASE.cobertura_por_seguradora_e_ramo(db=cliente)

    docs = (
        cliente.table("normative_documents")
        .select("insurer_key, product_line, doc_kind, title, updated_at")
        .eq("status", "ingested")
        .execute()
    ).data or []
    com_cg: Dict[str, List[str]] = {}
    for d in docs:
        try:
            chave = BASE.chave_de_conhecimento(d.get("insurer_key"))
        except BASE.SeguradoraDesconhecida:
            continue
        ramos = com_cg.setdefault(chave, [])
        ramo = str(d.get("product_line") or "")
        if ramo and ramo not in ramos:
            ramos.append(ramo)

    linhas: List[Dict[str, Any]] = []
    vistos = set()
    for (insurer_key, ramo), n in sorted(por_chave.items()):
        vistos.add((insurer_key, ramo))
        linhas.append({
            "insurer_key": insurer_key, "ramo": ramo,
            "planos": n.get("planos_publicados", 0),
            "servicos": n.get("servicos_publicados", 0),
            "estado": "publicada",
        })
    for chave, ramos in sorted(com_cg.items()):
        for ramo in sorted(ramos):
            if (chave, ramo) in vistos:
                continue
            linhas.append({
                "insurer_key": chave, "ramo": ramo, "planos": 0, "servicos": 0,
                # 🔴 três estados, não dois: "tem o documento e ninguém curou" é
                # trabalho nosso; "não tem o documento" é trabalho de buscar.
                "estado": "sem_linha_publicada",
            })

    fila = BASE.fila_de_curadoria(limite=TETO_DA_FILA, db=cliente)
    return {
        "ok": True,
        "linhas": linhas,
        "resumo": {
            "seguradora_ramo_com_plano_publicado": len(por_chave),
            "seguradoras_com_condicao_geral": len(com_cg),
            "itens_na_fila": len(fila),
        },
    }


def _termos_do_servico(servico: str) -> List[str]:
    """Os sinônimos daquele serviço — para a tela GRIFAR na página.

    ⚠️ Vêm do vocabulário versionado, não de uma lista escrita aqui: duas listas
    de sinônimos divergiriam, e a tela passaria a grifar uma coisa e o extrator a
    procurar outra (CLAUDE.md §9.4).
    """
    item = BASE.vocabulario_de_servicos().get("servicos", {}).get(str(servico or "")) or {}
    termos = [str(servico or "").replace("_", " ")] + list(item.get("sinonimos") or [])
    return sorted({t for t in termos if len(t) >= 4}, key=len, reverse=True)


@router.get("/fila", dependencies=[Depends(require_internal_key)])
def fila(limite: int = Query(TETO_DA_FILA, ge=1, le=200)) -> Dict[str, Any]:
    """A fila da LINHA, com a PÁGINA lida do PDF arquivado NA HORA.

    🔴 POR QUE NÃO SE RECONFERE O `trecho_hash` AQUI
    ================================================
    A base guarda o **hash** do trecho, nunca o trecho. Hash é de mão única: sem
    o texto original não há como recalcular nada — hashear a página inteira dá
    outro valor, sempre. 📊 18/09/2026 a tela mostrava `trecho_confere: false`
    em **100 %** da fila por causa disso, e um selo que está sempre vermelho
    ensina a pessoa a ignorá-lo: é pior que selo nenhum.

    Quem conferiu foi o **verificador**, no momento da proposta, quando ainda
    tinha o trecho na mão (`conferir_pagina`). O que a tela mostra agora é o
    texto REAL da página, com os termos do serviço destacados, para a pessoa
    julgar com os próprios olhos — que é o ato que esta fila existe para colher.
    """
    cliente = _db()
    itens = BASE.fila_de_curadoria(limite=int(limite), db=cliente)

    # Uma leitura por DOCUMENTO, não por item: 📊 um documento do acervo tem 207
    # páginas e baixá-lo uma vez por linha seria o mesmo arquivo dez vezes.
    por_documento: Dict[str, List[int]] = {}
    for i in itens:
        if i.get("documento_id") and i.get("pagina"):
            por_documento.setdefault(str(i["documento_id"]), []).append(int(i["pagina"]))
    textos: Dict[str, Dict[int, str]] = {}
    motivos: Dict[str, str] = {}
    for doc_id, paginas in por_documento.items():
        try:
            lidas = BASE.texto_das_paginas(doc_id, sorted(set(paginas)), db=cliente)
            textos[doc_id] = lidas.paginas or {}
            motivos[doc_id] = lidas.motivo
        except Exception as exc:  # noqa: BLE001 — a fila abre mesmo sem o PDF
            logger.warning("[planos] fonte indisponivel: %s", type(exc).__name__)
            motivos[doc_id] = "fonte_indisponivel"

    for i in itens:
        doc_id, pagina = str(i.get("documento_id")), i.get("pagina")
        texto = (textos.get(doc_id) or {}).get(int(pagina)) if pagina else None
        if texto:
            # 🔴 A PÁGINA INTEIRA, não um recorte. 📊 18/09/2026: 5 das 6 páginas
            # da amostra têm 1.8 k–4.3 k caracteres, e o corte em 1.200 escondia
            # justamente o fim da tabela de limites — a pessoa aprovava o que
            # coube na tela.
            i["texto_da_pagina"] = str(texto)
            i["termos_do_servico"] = _termos_do_servico(str(i.get("servico") or ""))
            # ⚠️ `conferido_na_proposta` vem do VERIFICADOR, que era o único a ter
            # o trecho na mão. A linha só chega a `proposto` depois de
            # `conferir_pagina` bater o trecho com ESTA página (as que falharam
            # estão em `rascunho`) — por isso `proposto`/`publicado` significa
            # conferido.
            i["conferido_na_proposta"] = str(i.get("curadoria")) in ("proposto", "publicado")
        else:
            i["texto_da_pagina"] = None
            i["termos_do_servico"] = []
            i["conferido_na_proposta"] = None
            i["motivo_da_fonte"] = motivos.get(doc_id, "fonte_indisponivel")
    return {"ok": True, "itens": itens, "total": len(itens)}


@router.post("/curadoria", dependencies=[Depends(require_internal_key)])
def curadoria(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Publicar ou rejeitar UMA linha. 🔴 Publicar exige a pessoa; rejeitar, o motivo.

    `revisado_por` vem do usuário autenticado no Next — **nunca** do corpo
    escolhido pelo browser sem sessão: é ele que vai ficar gravado como quem
    respondeu por *"guincho até 200 km"*.
    """
    acao = str(payload.get("acao") or "").strip()
    servico_id = str(payload.get("id") or "").strip()
    revisado_por = str(payload.get("revisado_por") or "").strip()
    motivo = str(payload.get("motivo") or "").strip()
    if not servico_id:
        return {"ok": False, "error": "sem_id"}
    try:
        if acao == "publicar":
            linha = BASE.publicar_servico(servico_id, revisado_por, db=_db())
        elif acao == "rejeitar":
            linha = BASE.rejeitar_servico(servico_id, revisado_por, motivo, db=_db())
        else:
            return {"ok": False, "error": "acao_desconhecida"}
    except BASE.RevisorObrigatorio:
        return {"ok": False, "error": "sem_revisor"}
    except BASE.BaseDePlanosRecusa as exc:
        return {"ok": False, "error": "recusado", "detalhe": str(exc)}
    return {"ok": True, "curadoria": linha.get("curadoria"), "id": linha.get("id")}
