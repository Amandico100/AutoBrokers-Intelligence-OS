"""Recomendação aceita → caminho canônico. SPEC-059 §22.

O que este módulo NÃO faz
-------------------------
Não executa efeito. Nunca envia, nunca cobra, nunca toca portal. Ele **abre o
caminho** e devolve o que vai acontecer, em português.

A distinção importa por causa de §14.3: aceitar a recomendação não é aprovar
todo efeito futuro. O corretor disse "resolve isso"; a aprovação do que sai da
plataforma continua sendo um segundo ato, com fingerprint e validade próprias
(SPEC-055).

Três destinos, e só três:

    trabalho único      → Work Run pelo Work OS
    recorrência         → proposta de Rotina pela Auxiliary Factory
    navegação           → o link certo, quando não há o que executar
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from .signal_service import registrar_evento

logger = logging.getLogger(__name__)


def executar_recomendacao(supabase_client: Any, *, company_id: str,
                          recommendation_id: str,
                          user_id: Optional[str] = None,
                          action_key: Optional[str] = None) -> dict:
    """Abre o caminho da recomendação aceita. Devolve `{ok, mensagem, ...}`."""
    db = getattr(supabase_client, "client", supabase_client)

    try:
        rec = (db.table("recommendations").select("*")
               .eq("id", recommendation_id).eq("company_id", company_id)
               .maybe_single().execute()).data
    except Exception as exc:  # noqa: BLE001
        logger.error("[Execution] leitura da recomendação: %s", type(exc).__name__)
        return {"ok": False, "mensagem": "Não consegui abrir esta recomendação."}
    if not rec:
        return {"ok": False, "mensagem": "Recomendação não encontrada."}

    chave = action_key or rec.get("selected_action_key") or rec.get("recommended_action_key")
    opcao = _opcao(rec, chave)
    if not opcao:
        return {"ok": False,
                "mensagem": ("Esta recomendação não tem uma ação executável. "
                             "Ela serve para você decidir, não para eu resolver.")}

    # §14.3 — risco alto exige aprovação ANTES, e o aceite não substitui isso.
    if rec.get("approval_required") and not rec.get("approval_request_id"):
        _marcar(db, recommendation_id, {"status": "accepted"})
        return {"ok": True, "aguardando_aprovacao": True,
                "mensagem": ("Anotei. Como esta ação sai da plataforma, ela precisa "
                             "da sua aprovação formal antes de rodar — vou preparar "
                             "e te mostrar o que exatamente será feito.")}

    tipo = str(opcao.get("kind") or "abrir")

    if tipo == "abrir":
        _marcar(db, recommendation_id, {"status": "accepted",
                                        "selected_action_key": chave})
        destino = opcao.get("destino") or "/dashboard/briefing"
        return {"ok": True, "destino": destino,
                "mensagem": f"O caminho é {destino} — te levo até lá."}

    if tipo == "rotina":
        return _propor_rotina(db, supabase_client, rec, company_id, user_id)

    if tipo == "work_run":
        return _abrir_work_run(supabase_client, db, rec, company_id,
                              user_id, opcao, chave)

    return {"ok": False, "mensagem": "Não sei executar este tipo de ação ainda."}


def _opcao(rec: dict, chave: Optional[str]) -> Optional[dict]:
    for o in rec.get("action_options") or []:
        if o.get("key") == chave and o.get("executavel"):
            return o
    return None


def _marcar(db: Any, rec_id: str, campos: dict) -> None:
    try:
        db.table("recommendations").update(campos).eq("id", rec_id).execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Execution] marcação falhou: %s", type(exc).__name__)


def _abrir_work_run(supabase_client: Any, db: Any, rec: dict, company_id: str,
                    user_id: Optional[str], opcao: dict,
                    chave: Optional[str]) -> dict:
    """Cria o Work Run pelo Work OS. Idempotente pela recomendação.

    A `idempotency_key` carrega o id da recomendação: aceitar duas vezes por
    engano — dois cliques, dois canais, uma retomada — produz UM trabalho.
    """
    from ..work.runs import WorkRunService
    from .outcome_service import OutcomeService

    workflow = (opcao.get("payload") or {}).get("workflow_key")
    if not workflow:
        return {"ok": False, "mensagem": "Esta ação não tem execução definida."}

    try:
        r = WorkRunService(supabase_client).criar(
            company_id=company_id,
            source_type="recommendation",
            source_id=str(rec["id"]),
            outcome_type="intelligence.recommendation",
            outcome_title=str(rec.get("title") or "Trabalho pedido pelo corretor"),
            workflow_key=workflow,
            idempotency_key=f"rec:{rec['id']}",
            input_payload={"recommendation_id": str(rec["id"]),
                           "finding_id": rec.get("finding_id")},
            requester_user_id=user_id,
            priority=45, risk_level=str(rec.get("risk_level") or "low"))
    except Exception as exc:  # noqa: BLE001
        logger.exception("[Execution] Work Run não criado")
        return {"ok": False,
                "mensagem": f"Não consegui abrir o trabalho agora ({type(exc).__name__})."}

    run_id = r.get("run_id")
    if not run_id:
        return {"ok": False, "mensagem": "Não consegui abrir o trabalho agora."}

    _marcar(db, str(rec["id"]), {"status": "executing", "work_run_id": run_id,
                                 "selected_action_key": chave,
                                 "accepted_at": datetime.now(timezone.utc).isoformat()})

    # §20.2 — a medição abre AGORA, com a linha de base de antes da ação.
    # Aberta depois, ela mediria o efeito contra o próprio efeito.
    try:
        OutcomeService(supabase_client).abrir(
            company_id=company_id, recommendation_id=str(rec["id"]),
            plano=rec.get("measurement_plan") or {}, work_run_id=run_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Execution] medição não aberta: %s", type(exc).__name__)

    registrar_evento(db, company_id=company_id, tipo="action.started",
                     subject_type="recommendation", subject_id=str(rec["id"]),
                     actor_kind="user", actor_id=user_id,
                     mensagem=f"Trabalho aberto: {rec.get('title')}",
                     detalhe={"work_run_id": run_id, "workflow": workflow})

    reaproveitado = bool(r.get("reused"))
    return {
        "ok": True, "work_run_id": run_id, "reaproveitado": reaproveitado,
        "mensagem": ("Já estava rodando — não abri um segundo."
                     if reaproveitado else
                     "Combinado. Abri o trabalho e vou te avisar quando terminar; "
                     "depois eu meço se resolveu."),
    }


def _propor_rotina(db: Any, supabase_client: Any, rec: dict, company_id: str,
                   user_id: Optional[str]) -> dict:
    """Recorrência vai para a Factory da SPEC-058 — que decide o formato.

    Criar a Rotina daqui seria a segunda Factory que o CLAUDE.md §5 proíbe, e
    pior: pularia a árvore de decisão que existe justamente para não criar
    Auxiliar onde bastava um trabalho único.
    """
    from ..auxiliaries.factory import AuxiliaryFactory

    texto = str(rec.get("summary") or rec.get("title") or "")
    try:
        avaliacao = AuxiliaryFactory(db).avaliar(
            company_id=company_id, texto=texto, user_id=user_id,
            source="recommendation")
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Execution] Factory indisponível: %s", type(exc).__name__)
        return {"ok": False,
                "mensagem": "Não consegui avaliar a automação agora."}

    _marcar(db, str(rec["id"]), {"status": "accepted"})
    registrar_evento(db, company_id=company_id, tipo="action.started",
                     subject_type="recommendation", subject_id=str(rec["id"]),
                     actor_kind="user", actor_id=user_id,
                     mensagem="Pedido de automação encaminhado à Fábrica de Auxiliares",
                     detalhe={"padrao": avaliacao.get("padrao")})

    return {"ok": True, "proposta": avaliacao,
            "mensagem": (avaliacao.get("mensagem_humana")
                         or "Avaliei o formato certo para automatizar isso.")}
