"""SPEC-131-0-B2 · L1 — as ações da PESSOA sobre a linha dela: conectar, o QR, o estado, desconectar.

Tudo que fala com o Evolution GO passa pelo `PairingOrchestrator` que já existe (o pareamento da SPEC-051), com o
DONO no escopo: a tentativa, a chave do Redis, a linha do banco e o nome da instância são DESTA pessoa
(`channel_identity.nome_da_instancia(company, 'linha_do_usuario', dono)`). Nenhum cliente HTTP novo de WhatsApp.

    conectar(db, company_id, user_id)    → {tentativa_id, qr, estado, motivo}
    qr(db, company_id, user_id)          → {qr, estado, tentativa_id, motivo}   (renova depois do QRTimeout)
    estado(db, company_id, user_id)      → {estado, numero_mascarado, desde, motivo}
    desconectar(db, company_id, user_id) → {ok, estado}   (aceita a tentativa PENDENTE: é o "Cancelar" da tela)

`company_id` e `user_id` vêm SEMPRE da sessão (o BFF). As chaves: `LINHA_DO_USUARIO_LIGADA` ausente = recusa sem
chamar o Evolution; `LINHA_DO_USUARIO_MAX_LINHAS` = o teto do servidor (cheio → `limite`, com a frase humana).
⛔ O QR e o telefone nunca vão para log.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.services.linha_do_usuario import estado as E

logger = logging.getLogger(__name__)

#: o GO parou de gerar QR (QRTimeout depois de 5) ou a tentativa venceu: a tela que ainda espera ganha um connect novo
ESTADOS_QUE_RENOVAM = frozenset({"qr_expired", "timed_out"})
_CONECTADA = frozenset({"connected", "already_connected"})
_ESPERANDO = frozenset({
    "preparing_instance", "requesting_qr", "qr_ready", "qr_scanned", "authenticating", "connecting",
    "passkey_required", "passkey_challenge", "passkey_awaiting_confirmation", "passkey_code_available",
    "qr_expired", "timed_out",
})


def _orquestrador():
    from app.services.whatsapp.pairing_orchestrator import get_pairing_orchestrator

    return get_pairing_orchestrator()


def _terminais():
    from app.services.whatsapp.pairing_orchestrator import TERMINAL_STATES

    return TERMINAL_STATES


def _runtime(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """A linha com o token DECIFRADO em memória (só para falar com o provedor; nunca volta para fora)."""
    if not row:
        return None
    from app.services.whatsapp.integration_secrets import prepare_integration_for_runtime

    try:
        return prepare_integration_for_runtime(row)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[LINHA] token da linha nao decifrou (%s)", type(exc).__name__)
        return None


def _da_tentativa(st: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """A tentativa do orquestrador (forma pública) → o vocabulário da tela."""
    st = st or {}
    s = str(st.get("state") or "")
    if s in _CONECTADA:
        estado = "conectada"
    elif s in _ESPERANDO:
        estado = "aguardando_qr"
    else:
        estado = "nao_conectada"     # cancelada, ou um erro: a tela oferece o botão de novo, com o motivo
    qr = st.get("qr_base64") if s == "qr_ready" else None
    motivo = st.get("error") if estado == "nao_conectada" else None
    return {"tentativa_id": st.get("attempt_id"), "qr": qr or None, "estado": estado, "motivo": motivo}


def _recusa_de_pareamento(exc: Exception) -> Dict[str, Any]:
    logger.warning("[LINHA] o pareamento recusou (%s)", type(exc).__name__)
    return {"tentativa_id": None, "qr": None, "estado": "nao_conectada",
            "motivo": "Não consegui preparar a conexão agora. Tente de novo em instantes."}


# ---------------------------------------------------------------------------------------------------------------------
async def conectar(db: Any, company_id: Any, user_id: Any, *, orquestrador: Any = None) -> Dict[str, Any]:
    """Cria (ou reusa) a instância DESTA pessoa e devolve o primeiro QR."""
    cid, uid = E._uuid(company_id, "company_id"), E._uuid(user_id, "user_id")
    if not E.ligada():
        # a chave ausente recusa ANTES de tocar no provedor
        return {"tentativa_id": None, "qr": None, "estado": "desligada", "motivo": E.FRASE_DESLIGADA}
    if not E.membro_ativo(db, cid, uid):
        raise E.Recusa("Só quem é da corretora conecta o WhatsApp aqui.")
    if E.ativa_em_outra_corretora(db, cid, uid):
        raise E.Recusa("O seu WhatsApp já está conectado ao AutoBrokers em outra corretora. "
                       "Desconecte lá primeiro (Meu perfil → Meu WhatsApp → Desconectar).")
    if E.teto_cheio(db, uid):
        return {"tentativa_id": None, "qr": None, "estado": "limite", "motivo": E.FRASE_LIMITE}

    orq = orquestrador or _orquestrador()
    anterior = E.linha_crua_do_dono(db, cid, uid, incluir_inativa=True)
    if anterior and anterior.get("is_active") is not True:
        # já houve linha e ela caiu/foi desconectada: o provedor ainda guarda o JID dela e RECONECTARIA em vez de
        # emitir QR (ver `liberar_para_novo_numero`). Quem clica Conectar é a própria pessoa — soltar é seguro.
        try:
            await orq.liberar_para_novo_numero(cid, E.PURPOSE, owner_user_id=uid)
        except Exception as exc:  # noqa: BLE001 — o start abaixo diz se dá para seguir
            logger.warning("[LINHA] liberar a instancia anterior falhou (%s)", type(exc).__name__)

    from app.services.whatsapp.pairing_orchestrator import PairingConflictError

    try:
        st = await orq.start(cid, E.PURPOSE, owner_user_id=uid)
    except PairingConflictError:
        # outro clique da MESMA pessoa está preparando a instância: a tela segue esperando
        return {"tentativa_id": None, "qr": None, "estado": "aguardando_qr", "motivo": None}
    except Exception as exc:  # noqa: BLE001
        return _recusa_de_pareamento(exc)
    return _da_tentativa(st)


async def qr(db: Any, company_id: Any, user_id: Any, *, orquestrador: Any = None) -> Dict[str, Any]:
    """O QR da tentativa DESTA pessoa (nunca o de outra). Depois do QRTimeout, chama o connect de novo — pelo
    `start` do orquestrador, cujo corpo leva SEMPRE o webhookUrl (`channel_security.corpo_do_connect`)."""
    cid, uid = E._uuid(company_id, "company_id"), E._uuid(user_id, "user_id")
    if not E.ligada():
        return {"qr": None, "estado": "desligada", "tentativa_id": None, "motivo": E.FRASE_DESLIGADA}
    orq = orquestrador or _orquestrador()
    try:
        atual = await orq.tentativa_atual(cid, E.PURPOSE, owner_user_id=uid)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[LINHA] a tentativa nao foi lida (%s)", type(exc).__name__)
        atual = None
    if not atual:
        e = await estado(db, cid, uid, orquestrador=orq)
        return {"qr": None, "estado": e["estado"], "tentativa_id": None, "motivo": e.get("motivo")}
    st = atual
    try:
        if str(st.get("state") or "") not in _terminais():
            st = await orq.get(cid, E.PURPOSE, str(st.get("attempt_id") or ""), owner_user_id=uid)
        if str(st.get("state") or "") in ESTADOS_QUE_RENOVAM:
            if E.teto_cheio(db, uid):
                return {"qr": None, "estado": "limite", "tentativa_id": None, "motivo": E.FRASE_LIMITE}
            st = await orq.start(cid, E.PURPOSE, owner_user_id=uid)
    except Exception as exc:  # noqa: BLE001
        return {**_recusa_de_pareamento(exc)}
    r = _da_tentativa(st)
    return {"qr": r["qr"], "estado": r["estado"], "tentativa_id": r["tentativa_id"], "motivo": r["motivo"]}


async def estado(db: Any, company_id: Any, user_id: Any, *, orquestrador: Any = None) -> Dict[str, Any]:
    """O estado da linha DESTA pessoa nesta corretora: o banco + o provedor ao vivo (só o SIM dele conta) —
    sem provedor ou sem Redis, falha para o gravado."""
    cid, uid = E._uuid(company_id, "company_id"), E._uuid(user_id, "user_id")
    if not E.ligada():
        return E.calcular_estado(None, esta_ligada=False, sem_vaga=False, tentativa_pendente=None, ao_vivo=None)
    row = E.linha_crua_do_dono(db, cid, uid, incluir_inativa=True)
    sem_vaga = E.teto_cheio(db, uid)
    orq = orquestrador or _orquestrador()
    pendente: Optional[bool] = None
    try:
        atual = await orq.tentativa_atual(cid, E.PURPOSE, owner_user_id=uid)
        pendente = bool(atual) and str(atual.get("state") or "") not in _terminais()
    except Exception as exc:  # noqa: BLE001
        logger.info("[LINHA] tentativa ilegivel (%s) — estado pelo gravado", type(exc).__name__)
    ao_vivo = None
    if row and row.get("is_active") is True:
        try:
            ao_vivo = await orq.status_ao_vivo(_runtime(row))
        except Exception:  # noqa: BLE001 — falha para o gravado
            ao_vivo = None
    return E.calcular_estado(E._publica(row) if row else None, esta_ligada=True, sem_vaga=sem_vaga,
                             tentativa_pendente=pendente, ao_vivo=ao_vivo)


async def desconectar(db: Any, company_id: Any, user_id: Any, *, orquestrador: Any = None) -> Dict[str, Any]:
    """Logout + a instância solta do aparelho + `is_active=false` com data e motivo. Nada do histórico é apagado.

    Aceita a tentativa PENDENTE (o "Cancelar" da tela, durante o QR): cancela, solta e volta a `nao_conectada`.
    Idempotente: sem linha, responde `nao_conectada` sem erro. Funciona com a chave desligada (sair é sempre
    possível)."""
    cid, uid = E._uuid(company_id, "company_id"), E._uuid(user_id, "user_id")
    orq = orquestrador or _orquestrador()
    try:
        atual = await orq.tentativa_atual(cid, E.PURPOSE, owner_user_id=uid)
        if atual and str(atual.get("state") or "") not in _terminais():
            await orq.cancel(cid, E.PURPOSE, str(atual.get("attempt_id") or ""), owner_user_id=uid)
    except Exception as exc:  # noqa: BLE001 — a linha do banco é desligada mesmo assim
        logger.warning("[LINHA] cancelar a tentativa falhou (%s)", type(exc).__name__)
    row = E.linha_crua_do_dono(db, cid, uid)
    if not row:
        return {"ok": True, "estado": "nao_conectada"}
    pendente = row.get("channel_status") != "connected"
    try:
        await orq.encerrar_sessao(_runtime(row))
    except Exception as exc:  # noqa: BLE001
        logger.warning("[LINHA] logout falhou (%s)", type(exc).__name__)
    try:
        await orq.liberar_para_novo_numero(cid, E.PURPOSE, owner_user_id=uid)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[LINHA] soltar a instancia falhou (%s)", type(exc).__name__)
    E.registrar_desconexao(db, row, "cancelada_pelo_usuario" if pendente else "desconectada_pelo_usuario")
    return {"ok": True, "estado": "nao_conectada"}


__all__ = ["conectar", "qr", "estado", "desconectar", "ESTADOS_QUE_RENOVAM"]
