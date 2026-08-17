# -*- coding: utf-8 -*-
"""O adapter de sombra — SPEC-075 Blocos U e V.

Os dois chamadores especializados que existem hoje — `billing_collection` e
`portal_tool` — funcionam em produção, com dinheiro de corretora e pedidos no
nome de segurados. A SPEC-075 pede que eles passem a usar a ponte, e pede
também que a migração seja **sem regressão**.

Uma coisa não se prova sozinha com a outra. Por isso a ordem aqui é:

    1. o caminho legado executa, como sempre executou
    2. a ponte RESOLVE em paralelo e registra o que TERIA feito
    3. quando os dois concordarem por tempo suficiente, vira o cutover

🔴 Este módulo **nunca cria job, nunca escreve em `portal_jobs`, nunca chama
portal**. Ele resolve e registra. Se ele falhar, o chamador não pode nem
perceber — é isso que `observar()` garante com o `except` largo, e é o único
lugar deste projeto onde engolir exceção é a decisão certa: uma observação que
derruba o observado não é observação, é sabotagem.

📊 O desenho não é novo aqui: é o mesmo `TOOL_GATEWAY_MODE` que a casa já usa, e
que já pagou por si — 51 diffs registrados em sombra na madrugada de 15→16/08
sem afetar nenhuma execução.

Onde a divergência aparece
==========================
Em `portal_jobs.evidence.gateway_sombra` do job que o caminho legado criou. Não
numa tabela nova: a comparação precisa viver ao lado do trabalho que ela
descreve, senão vira um segundo lugar para procurar quando algo dá errado.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def observar(supabase: Any, *, job_id: Optional[str], company_id: str,
             operation_key: str, business_input: Optional[Dict[str, Any]] = None,
             insurer_key: Optional[str] = None,
             portal_key_hint: Optional[str] = None,
             portal_key_legado: str = "",
             journey_legada: str = "") -> Dict[str, Any]:
    """Resolve pela ponte e compara com o que o caminho legado fez.

    Devolve o diff (para teste e log). Grava no `evidence` do job quando há
    `job_id` — e não grava nada quando não há, porque um diff sem trabalho ao
    lado não ajuda ninguém.

    Nunca levanta. Nunca escreve fora do `evidence` daquele job.
    """
    diff: Dict[str, Any] = {"operation_key": operation_key}
    try:
        from app.services.portals import contracts as C
        from app.services.portals.gateway import PortalExecutionGateway

        req = C.PortalExecutionRequest(
            company_id=str(company_id),
            operation_key=operation_key,
            business_input=dict(business_input or {}),
            insurer_key=insurer_key,
            portal_key_hint=portal_key_hint,
            # 🔴 `True` porque quem chama `observar()` é código server-side —
            # `billing_collection` e `portal_tool`, ambos derivando o portal do
            # registro, nunca de texto de modelo. Ver `hints_utilizaveis()`.
            origem_confiavel=True,
        )
        gw = PortalExecutionGateway(supabase)
        r = gw.resolver(req)

        if not r.get("ok"):
            resultado = r["resultado"]
            diff.update({
                "ponte_resolveu": False,
                "ponte_estado": resultado.business_state,
                "ponte_motivo": resultado.motivo,
                "legado_portal": portal_key_legado,
                "legado_journey": journey_legada,
                # 🔴 O caso que importa: o legado executou e a ponte teria
                # RECUSADO. Ou a ponte está errada, ou o legado está fazendo
                # algo que ninguém autorizou. Nenhuma das duas pode passar
                # despercebida — e é por isso que a sombra existe antes do
                # cutover, e não depois.
                "concorda": False,
                "gravidade": "ponte_recusaria_o_que_o_legado_fez",
            })
        else:
            pk = r["portal_key"]
            jk = r["definicao"].journey_key
            concorda = (pk == portal_key_legado and jk == journey_legada)
            diff.update({
                "ponte_resolveu": True,
                "ponte_portal": pk,
                "ponte_journey": jk,
                "ponte_effect_class": r["definicao"].effect_class,
                "ponte_conta": r["conta"].account_label or None,
                "legado_portal": portal_key_legado,
                "legado_journey": journey_legada,
                "concorda": concorda,
            })
            if not concorda:
                diff["gravidade"] = "ponte_escolheria_outra_journey"
    except Exception as e:  # noqa: BLE001
        # Observação que derruba o observado não é observação.
        diff.update({"ponte_resolveu": False, "erro": type(e).__name__,
                     "concorda": None})
        logger.warning("[portais][sombra] falhou sem afetar o legado: %s",
                       type(e).__name__)

    if job_id:
        _gravar(supabase, job_id, diff)
    if diff.get("concorda") is False:
        logger.warning("[portais][sombra] DIVERGENCIA em %s: %s",
                       operation_key, diff.get("gravidade"))
    return diff


def _gravar(supabase: Any, job_id: str, diff: Dict[str, Any]) -> None:
    """Anexa o diff ao `evidence`, preservando o que já estava lá.

    Lê antes de escrever porque `update` de coluna `jsonb` substitui o objeto
    inteiro. Um adapter de sombra que apagasse a evidência do trabalho seria o
    pior resultado possível: silencioso, e destruindo justamente o que serve
    para investigar.
    """
    try:
        atual = (supabase.table("portal_jobs").select("evidence")
                 .eq("id", job_id).limit(1).execute())
        base = {}
        if atual.data:
            ev = (atual.data[0] or {}).get("evidence")
            if isinstance(ev, dict):
                base = dict(ev)
        base["gateway_sombra"] = diff
        supabase.table("portal_jobs").update({"evidence": base}).eq("id", job_id).execute()
    except Exception:  # noqa: BLE001
        logger.warning("[portais][sombra] nao consegui gravar o diff; seguindo")


def sombra_ligada() -> bool:
    """A sombra roda em `shadow` e em `on`; em `legacy` fica quieta.

    Em `on` ela continua registrando de propósito: o dia do cutover é
    exatamente quando alguém vai querer conferir se a ponte está escolhendo o
    mesmo que escolhia na véspera.
    """
    from app.services.portals.contracts import MODO_LEGACY
    from app.services.portals.gateway import modo_do_gateway

    return modo_do_gateway() != MODO_LEGACY
