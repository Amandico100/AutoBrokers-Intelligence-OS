# -*- coding: utf-8 -*-
"""SPEC-132-C conserto (P2/P3 do red team) — o estado DURÁVEL do atalho, por TELEFONE.

    ler(db, telefone)                         {"perguntou_em"?, "fala"?} decifrado ({} quando nada pendente)
    guardar(db, telefone, estado | None)      grava (cifrado) ou limpa a pergunta pendente
    reservar_envios(db, telefone, n)          o TETO de mensagens ENVIADAS hoje a este telefone: True = pode mandar n

Uma linha por telefone em `whatsapp_atalho_estado` (migration 20261014_05): a chave é o HMAC do telefone
(`verificacao._hash_do_telefone` — nunca o número em claro) e a fala guardada vai CIFRADA (portal_vault, o mesmo cofre
do estado do QCM). O Redis NÃO é a fonte: Redis fora = a escolha da corretora continua funcionando (P3).

🔴 Erro de banco SOBE em `ler`/`guardar` (quem chama cala: fail-closed) e devolve False em `reservar_envios` (o envio
   não sai). ⛔ Nenhum telefone e nenhum conteúdo em log.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

TABELA = "whatsapp_atalho_estado"
#: 💭 quantas mensagens o número do AutoBrokers manda, no máximo, a UM telefone por dia (dia de Brasília). Conta TODA
#: mensagem que sai: a resposta do turno (cada pedaço de ≤ 3.500), "qual corretora?", "sem agente", a ativação, a
#: frase do teto e a volta da cotação. Acima dele, silêncio até o dia seguinte (o número é UM para todas as corretoras:
#: banido, o atalho cai para todas).
TETO_DE_ENVIOS_POR_DIA = 300
FUSO = timezone(timedelta(hours=-3))


def _dados(r: Any) -> List[Dict[str, Any]]:
    return [x for x in list(getattr(r, "data", None) or []) if isinstance(x, dict)]


def _t(db: Any):
    cliente = db if hasattr(db, "table") else getattr(db, "client", db)
    return cliente.table(TABELA)


def _chave(telefone: Any) -> str:
    """O HMAC do telefone canônico (com o 9º dígito) — o MESMO de `whatsapp_atalho_tentativas`. Sem segredo → levanta."""
    from app.services.atalho import verificacao as V

    e164 = V._e164_de(telefone)
    if not e164:
        raise ValueError("telefone inválido")
    return V._hash_do_telefone(e164)


def _hoje() -> str:
    return datetime.now(FUSO).date().isoformat()


def _linha(db: Any, chave: str) -> Optional[Dict[str, Any]]:
    linhas = _dados(_t(db).select("telefone_hash, estado_cifrado, enviadas_dia, enviadas_no_dia")
                    .eq("telefone_hash", chave).limit(1).execute())
    return next((x for x in linhas if x.get("telefone_hash") == chave), None)


def _gravar(db: Any, chave: str, campos: Dict[str, Any]) -> None:
    """UPDATE se a linha existe, senão INSERT (a corrida do INSERT perde para a PK → refaz como UPDATE)."""
    campos = {**campos, "atualizado_em": datetime.now(timezone.utc).isoformat()}
    if _linha(db, chave) is not None:
        _t(db).update(campos).eq("telefone_hash", chave).execute()
        return
    try:
        _t(db).insert({"telefone_hash": chave, **campos}).execute()
    except Exception:  # noqa: BLE001 — outro processo criou a linha no meio: vale o UPDATE
        _t(db).update(campos).eq("telefone_hash", chave).execute()


# ---------------------------------------------------------------------------------------------------------------------
# a pergunta pendente (membro de 2+ corretoras)
# ---------------------------------------------------------------------------------------------------------------------
def ler(db: Any, telefone: Any) -> Dict[str, Any]:
    """O estado pendente decifrado — `{}` quando não há. Cifra ilegível (chave trocada) → `{}` (recomeça a pergunta).
    Erro de BANCO sobe (o turno cala)."""
    linha = _linha(db, _chave(telefone))
    cifrado = str((linha or {}).get("estado_cifrado") or "")
    if not cifrado:
        return {}
    from app.services import portal_vault

    try:
        valor = json.loads(portal_vault.decrypt(cifrado))
    except Exception as erro:  # noqa: BLE001
        logger.warning("[ATALHO] estado ilegível (%s) — recomeça", type(erro).__name__)
        return {}
    return valor if isinstance(valor, dict) else {}


def guardar(db: Any, telefone: Any, estado: Optional[Dict[str, Any]]) -> None:
    """Grava o estado CIFRADO (ou limpa com None). Erro sobe (o turno cala — a pergunta não sai sem estar guardada)."""
    chave = _chave(telefone)
    if not estado:
        _gravar(db, chave, {"estado_cifrado": None})
        return
    from app.services import portal_vault

    texto = json.dumps(estado, ensure_ascii=False, default=str)
    _gravar(db, chave, {"estado_cifrado": portal_vault.encrypt(texto)})


# ---------------------------------------------------------------------------------------------------------------------
# o teto de ENVIOS (toda mensagem que sai conta)
# ---------------------------------------------------------------------------------------------------------------------
def enviadas_hoje(db: Any, telefone: Any) -> int:
    linha = _linha(db, _chave(telefone))
    if not linha or str(linha.get("enviadas_dia") or "")[:10] != _hoje():
        return 0
    try:
        return max(0, int(linha.get("enviadas_no_dia") or 0))
    except (TypeError, ValueError):
        return 0


def reservar_envios(db: Any, telefone: Any, n: int) -> bool:
    """Reserva `n` mensagens no teto do dia deste telefone. True = pode mandar (o contador já subiu); False = o teto
    estouraria (nada muda) ou o banco não respondeu (fail-closed: na dúvida, o número do AutoBrokers CALA).
    Um processo só (`backend/Dockerfile:27`) e a trava por telefone do turno: a leitura-e-escrita não disputa consigo."""
    try:
        n = max(0, int(n))
        chave = _chave(telefone)
        linha = _linha(db, chave)
        hoje = _hoje()
        feitas = 0
        if linha and str(linha.get("enviadas_dia") or "")[:10] == hoje:
            feitas = max(0, int(linha.get("enviadas_no_dia") or 0))
        if feitas + n > TETO_DE_ENVIOS_POR_DIA:
            logger.warning("[ATALHO] teto de envios do dia atingido (%d/%d) — não sai", feitas, TETO_DE_ENVIOS_POR_DIA)
            return False
        _gravar(db, chave, {"enviadas_dia": hoje, "enviadas_no_dia": feitas + n})
        return True
    except Exception as erro:  # noqa: BLE001
        logger.error("[ATALHO] teto de envios não conferido (%s) — não sai", type(erro).__name__)
        return False


__all__ = ("TABELA", "TETO_DE_ENVIOS_POR_DIA", "ler", "guardar", "enviadas_hoje", "reservar_envios")
