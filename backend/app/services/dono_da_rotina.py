"""Quem é o Auxiliar dono de uma Rotina — SPEC-078 Bloco C.3.

`ONTOLOGIA-DO-TRABALHO.md:51`  "Rotina nunca existe sozinha."
`GLOSSARIO.md:18`              "routines (sempre com tenant_auxiliary_id)"

📊 MEDIDO EM 17/08/2026: o repositório inteiro tinha 42 linhas mencionando
`tenant_auxiliary_id` e **nenhuma delas escrevia a coluna em `routines`**. Não
era descuido de um caso — não existia caminho de código no produto que desse
dono a uma rotina nova. Os quatro escritores (tela, chat, monitor, radar) todos
inseriam sem dono, e a única linha que já teve dono ganhou por uma migration
one-shot de 02/08 que casava por `name ilike '%cobran%'`.

Este módulo existe para que a resposta seja **uma só**. Três cópias da mesma
regra em três arquivos é como a divergência começa — o quarto escritor copia a
que estiver mais perto e ninguém percebe que ela já estava velha.

A ordem de escolha importa, e é a mesma do backfill da migration
`20260817_03_spec078_toda_rotina_tem_dono.sql`:

    1. o slug pedido explicitamente (a tela do Auxiliar manda o dela)
    2. o `kind` da config — billing_collection → cobranca-feita
    3. `tarefas-agendadas`, o Auxiliar de plataforma

Jogar tudo direto em `tarefas-agendadas` seria mais curto e erraria: uma rotina
de cobrança pertence ao Auxiliar de Cobrança, que é onde o corretor procura por
ela. `tarefas-agendadas` é o destino de quem **não tem** dono natural, não o
depósito de quem tem.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

#: O Auxiliar de plataforma que torna o `NOT NULL` possível.
#:
#: Sem ele, uma rotina pedida no chat ("todo dia às 8h me manda um resumo") não
#: teria dono possível — e transformá-la num Auxiliar quebraria três regras de
#: uma vez: `ONTOLOGIA:209` (Auxiliar nascendo fora do catálogo), SPEC-064 G.2.4
#: ("o chat nunca cria algo global") e a inexistência de "Auxiliar pessoal" no
#: cânone. Um Auxiliar para todas elas resolve sem inventar conceito.
AUXILIAR_DE_TAREFAS_SOLTAS = "tarefas-agendadas"

#: Rotina cujo `config.kind` é conhecido tem dono natural.
AUXILIAR_POR_KIND: Dict[str, str] = {
    "billing_collection": "cobranca-feita",
}

#: Auxiliar arquivado saiu de cena e não recebe rotina nova. Os demais estados
#: recebem — inclusive `inactive` e `paused`: é justamente pausado que a
#: corretora configura antes de ligar.
_ESTADOS_QUE_NAO_RECEBEM = frozenset({"archived", "uninstalled"})


def slugs_candidatos(
    slug_pedido: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> list[str]:
    """Os donos possíveis, do mais específico ao genérico, sem repetição."""
    cfg = config if isinstance(config, dict) else {}
    brutos = [
        str(slug_pedido or "").strip(),
        # O Radar grava o dono como STRING dentro do JSONB (`config.auxiliar`).
        # É o defeito do CLAUDE.md §12.1 — o campo mente sobre o que guarda.
        # Aqui a string ainda é LIDA para não perder a informação de quem já a
        # gravou; o Radar deixa de ESCREVÊ-LA em `radar.py`.
        str(cfg.get("auxiliar") or "").strip(),
        AUXILIAR_POR_KIND.get(str(cfg.get("kind") or ""), ""),
        AUXILIAR_DE_TAREFAS_SOLTAS,
    ]
    vistos: list[str] = []
    for s in brutos:
        if s and s not in vistos:
            vistos.append(s)
    return vistos


def resolver_dono(
    client: Any,
    company_id: str,
    slug_pedido: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """O `tenant_auxiliaries.id` que deve ser dono desta rotina.

    Devolve ``None`` quando **nenhum** candidato existe na corretora. Quem chama
    tem de tratar isso como falha — inserir sem dono agora bate no ``NOT NULL``
    do banco, que é a rede de baixo, e o erro chegaria cru na tela.

    🔴 O filtro por `company_id` não é decorativo. O backend usa service role:
    RLS sem policy não protege contra erro de filtro no código (CLAUDE.md §7).
    Sem ele, uma rotina poderia nascer apontando para o Auxiliar de outra
    corretora — e a FK composta `fk_routines_auxiliary_same_company` recusaria,
    mas com uma mensagem que ninguém entende.
    """
    candidatos = slugs_candidatos(slug_pedido, config)
    try:
        res = (
            client.table("tenant_auxiliaries")
            .select("id, slug, status")
            .eq("company_id", str(company_id))
            .in_("slug", candidatos)
            .execute()
        )
        linhas = list(res.data or [])
    except Exception as exc:  # noqa: BLE001
        logger.error("[DONO DA ROTINA] consulta falhou: %s", type(exc).__name__)
        return None

    por_slug = {str(l.get("slug")): l for l in linhas}
    for slug in candidatos:
        achado = por_slug.get(slug)
        if achado and str(achado.get("status") or "") not in _ESTADOS_QUE_NAO_RECEBEM:
            return str(achado.get("id"))

    logger.error(
        "[DONO DA ROTINA] corretora %s nao tem nenhum de: %s. A rotina NAO sera "
        "criada — rotina sem dono e o defeito que a SPEC-078 fechou.",
        company_id, ", ".join(candidatos),
    )
    return None
