# -*- coding: utf-8 -*-
"""O `confirmacao_id` — SPEC-132-B D-132B-03: confirmação EXPLÍCITA, de USO ÚNICO, que vale 30 min.

    guardar(company_id=, user_id=, conversation_id=, conteudo=, falas_vistas=) -> confirmacao_id
    consumir(company_id=, user_id=, conversation_id=, confirmacao_id=, falas_do_corretor=) -> conteudo
                                                                               (ou ConfirmacaoRecusada)
    ler_falas(db, conversation_id) · confirmou_depois(falas, vistas=, resumo_em=) · e_confirmacao(texto)

🔴 O "SIM" É DO CORRETOR (conserto juiz B4 · D-132B-03 · CLAUDE.md §6 "Approval não é frase de prompt"): o resumo
   guarda quais falas do corretor JÁ estavam na conversa; o disparo só consome se existe uma fala NOVA dele (role user,
   esta conversa) e a mais recente delas é um "sim" (sem "não"/"espera", sem dado novo). O modelo que encadeia
   preparar → disparar no mesmo turno ouve `sem_sim` — e o id NÃO é consumido.

ONDE MORA (decisão do builder B1, nota 85 · `work_runs` "aguardando" 60 · `messages.payload` 40): no REDIS, que o
CLAUDE.md §6 dá como a casa do TRANSITÓRIO (fila, lock, lease, cache) — e um "sim, pode calcular" de 30 minutos é
transitório por natureza: some sozinho (TTL), não precisa de tabela nova (§3 da SPEC) e não vira trabalho que o worker
pegaria (um `work_run` na fila RODA; um em estado próprio de "aguardando confirmação" não existe na máquina de estados).
Redis fora → a confirmação NÃO é guardada e o corretor ouve uma frase honesta (fail-closed: nada calcula sem o "sim").

🔴 USO ÚNICO: quem consome APAGA a chave e só segue se o `DEL` apagou (1). Duas chamadas ao mesmo tempo → só uma apaga.
   Depois de usada fica uma marca (`…:usada`, 30 min) para a segunda chamada ouvir "já foi" em vez de "expirou".
🔴 DONO: a chave tem o `company_id` (o id de A não existe em B) e o conteúdo tem quem preparou e em qual conversa —
   outra pessoa, ou a mesma noutra conversa, é recusada SEM consumir.
🔴 O conteúdo leva o PEDIDO (CPF, nome…): vai CIFRADO (`portal_vault`, o mesmo cofre do `pedido_cifrado` e do contato
   do canal). Nada disto vai a log.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import secrets
from typing import Any, Dict, Mapping, Optional

logger = logging.getLogger(__name__)

VALIDADE_S = 30 * 60
PREFIXO = "autobrokers:cotacao:confirmacao"
_ID = re.compile(r"^[0-9a-f]{16}$")

FRASES = {
    "inexistente": "Essa confirmação não vale mais (passou de 30 minutos ou não é desta conversa). Eu preparo de novo: "
                   "me diga \"prepara a cotação\" e confira o resumo.",
    "ja_usada": "Essa cotação já foi disparada — o resultado volta aqui nesta conversa. Para calcular de novo, peça "
                "uma cotação nova.",
    "de_outra_pessoa": "Essa confirmação é de outra conversa ou de outra pessoa da equipe — não posso usá-la aqui.",
    "sem_redis": "Não consegui guardar a confirmação agora (problema do nosso lado). Tente de novo em instantes.",
    # 🔴 conserto juiz B4: a frase vai ao MODELO (não é recusa definitiva — o id NÃO é consumido)
    "sem_sim": "PARA O ASSISTENTE — ainda NÃO calculei: o corretor não confirmou o resumo depois que eu o mostrei. "
               "Mostre o resumo e pergunte se pode calcular; quando ele responder \"sim\", chame cotacao_disparar de "
               "novo com o mesmo confirmacao_id.",
}

#: o "sim" do corretor (sem acento, minúsculo). Qualquer uma destas palavras numa fala CURTA, sem negação e sem dado novo
_SIM = re.compile(r"\b(sim|s|claro|vamos|pode|podes|calcula|calcular|calcule|ok|okay|okey|manda|mande|confirmo|confirmado|"
                  r"confirma|isso|certo|correto|beleza|blz|bora|vai|fechado|positivo|perfeito|tudo certo|"
                  r"esta certo|ta certo|pode ser|segue|siga|faz|faca|dispara)\b")
#: a negação (ou "espera") vence o "sim": "sim, mas espera" não calcula
#: ("para" fica de fora de propósito: "pode calcular para mim" é um sim)
_NAO = re.compile(r"\b(nao|n|espera|espere|pera|perai|aguarda|aguarde|calma|cancela|cancele|pare|errado|"
                  r"errada|corrige|corrija|muda|mude|troca|troque)\b")
#: uma fala com dado novo (CPF, CEP, placa, data) é CORREÇÃO, não confirmação: prepara de novo
_DADO = re.compile(r"\d{5}-?\d{3}|\d{3}\.?\d{3}\.?\d{3}-?\d{2}|\b[a-z]{3}-?\d[a-z0-9]\d{2}\b|\d{1,2}/\d{1,2}/\d{2,4}")
#: a folga entre o relógio do backend (o instante do resumo) e o do banco (o `created_at` da fala): a régua de "depois"
#: é o `vistas` (a fala que já estava lá); o instante é só o cinto para a fala que caiu fora da janela lida
FOLGA_DO_RELOGIO_S = 300
#: uma confirmação é curta (💭 o "sim, pode calcular" cabe; um parágrafo com pedido novo não)
TETO_DA_FALA = 80


def e_confirmacao(texto: Any) -> bool:
    """A fala do corretor é um "sim" ao resumo? (sim/pode/calcula/ok/manda… — sem "não"/"espera", sem dado novo)."""
    from app.services.canal.conversa import _sem_acento

    t = re.sub(r"\s+", " ", _sem_acento(texto or "")).strip(" .!,;")
    if not t or len(t) > TETO_DA_FALA or _DADO.search(t):
        return False
    return bool(_SIM.search(t)) and not _NAO.search(t)


def ler_falas(db: Any, conversation_id: str, *, limite: int = 20) -> list:
    """As últimas falas do CORRETOR (role user) NESTA conversa, a mais recente primeiro: `{id, content, created_at}`.
    A conversa é conferida por quem chama (`conversations.company_id` + dono). ⛔ O conteúdo nunca vai a log."""
    cli = getattr(db, "client", db)
    linhas = list(getattr(cli.table("messages").select("id, conversation_id, role, content, payload, created_at")
                          .eq("conversation_id", str(conversation_id)).eq("role", "user")
                          .order("created_at", desc=True).limit(limite).execute(), "data", None) or [])
    return [{"id": str(l.get("id")), "content": _texto_da_fala(l), "created_at": l.get("created_at")}
            for l in linhas if str(l.get("conversation_id")) == str(conversation_id) and l.get("role") == "user"]


def _texto_da_fala(linha: Any) -> str:
    """🔴 Confirmação 132-B (defeito novo): o "sim" FALADO. Quando o corretor manda só áudio, `content` guarda
    "[Anexo] audio.webm" e o que ele disse mora em `payload.transcricao` (mascarada). Sem isto, quem confirma por voz
    — o jeito natural no WhatsApp — entrava em laço com a recusa `sem_sim`."""
    conteudo = str(linha.get("content") or "")
    payload = linha.get("payload") if isinstance(linha.get("payload"), dict) else {}
    transcricao = str(payload.get("transcricao") or "").strip()
    if transcricao and (not conteudo.strip() or conteudo.strip().startswith("[Anexo]")):
        return transcricao
    return conteudo


def _instante(v: Any) -> Any:
    from datetime import datetime, timezone

    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def confirmou_depois(falas: Any, *, vistas: Any, resumo_em: Any) -> bool:
    """🔴 Conserto juiz B4 (D-132B-03, CLAUDE.md §6 "Approval não é frase de prompt"): existe uma fala do CORRETOR
    gravada DEPOIS do resumo — uma que NÃO estava na conversa quando o resumo foi mostrado (`vistas`) e não é mais velha
    que ele — e a MAIS RECENTE dessas é um "sim"? O modelo encadeando `preparar` → `disparar` no mesmo turno não tem
    fala nova nenhuma: recusa."""
    vistas = {str(v) for v in (vistas or ())}
    marco = _instante(resumo_em)
    novas = []
    for f in falas or ():
        if not isinstance(f, Mapping) or str(f.get("id")) in vistas:
            continue
        quando = _instante(f.get("created_at"))
        if marco is not None and quando is not None and (marco - quando).total_seconds() > FOLGA_DO_RELOGIO_S:
            continue
        novas.append((quando, f))
    if not novas:
        return False
    com_instante = [x for x in novas if x[0] is not None]
    ultima = max(com_instante, key=lambda x: x[0])[1] if com_instante else novas[0][1]
    return e_confirmacao(ultima.get("content"))


class ConfirmacaoRecusada(Exception):
    def __init__(self, motivo: str):
        self.motivo = motivo
        self.frase = FRASES.get(motivo, FRASES["inexistente"])
        super().__init__(motivo)


async def _redis_padrao() -> Any:
    from app.core.redis import get_async_redis_client

    return await asyncio.wait_for(get_async_redis_client(), timeout=2.0)


#: o provedor do cliente Redis (os testes trocam por um dublê em memória)
obter_redis = _redis_padrao


def _chave(company_id: str, confirmacao_id: str) -> str:
    return f"{PREFIXO}:{company_id}:{confirmacao_id}"


def _cifrar(conteudo: Mapping[str, Any]) -> str:
    from app.services import portal_vault

    return portal_vault.encrypt(json.dumps(dict(conteudo), ensure_ascii=False, sort_keys=True))


def _decifrar(token: str) -> Dict[str, Any]:
    from app.services import portal_vault

    return json.loads(portal_vault.decrypt(token))


async def guardar(*, company_id: str, user_id: str, conversation_id: str, conteudo: Mapping[str, Any],
                  falas_vistas: Any = (), redis: Any = None) -> str:
    """Guarda o pedido preparado e devolve o `confirmacao_id` (16 hex, imprevisível). Redis fora → `sem_redis`.
    `falas_vistas`: os ids das falas do corretor que JÁ estavam na conversa quando o resumo foi mostrado (o "sim" tem de
    ser uma fala que não está aqui — `confirmou_depois`)."""
    from datetime import datetime, timezone

    if not company_id or not user_id or not conversation_id:
        raise ConfirmacaoRecusada("de_outra_pessoa")
    cid = secrets.token_hex(8)
    corpo = {"company_id": str(company_id), "user_id": str(user_id), "conversation_id": str(conversation_id),
             "conteudo": dict(conteudo), "resumo_em": datetime.now(timezone.utc).isoformat(),
             "falas_vistas": sorted({str(f) for f in (falas_vistas or ())})}
    try:
        r = redis or await obter_redis()
        ok = await r.set(_chave(company_id, cid), _cifrar(corpo), ex=VALIDADE_S, nx=True)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[COTACAO] confirmação não guardada (%s)", type(exc).__name__)
        raise ConfirmacaoRecusada("sem_redis") from None
    if not ok:
        raise ConfirmacaoRecusada("sem_redis")
    return cid


async def consumir(*, company_id: str, user_id: str, conversation_id: str, confirmacao_id: Any,
                   falas_do_corretor: Any, redis: Any = None) -> Dict[str, Any]:
    """O conteúdo guardado — UMA vez. Recusas: `inexistente` · `ja_usada` · `de_outra_pessoa` · `sem_redis` ·
    `sem_sim` (🔴 conserto juiz B4: sem uma fala do corretor DEPOIS do resumo que seja um "sim" — `confirmou_depois` —
    recusa SEM consumir; `falas_do_corretor` é obrigatório: `ler_falas` desta conversa, lido por quem chama)."""
    cid = str(confirmacao_id or "").strip().lower()
    if not _ID.match(cid) or not company_id:
        raise ConfirmacaoRecusada("inexistente")
    chave = _chave(company_id, cid)
    try:
        r = redis or await obter_redis()
        bruto = await r.get(chave)
        if bruto is None:
            raise ConfirmacaoRecusada("ja_usada" if await r.get(chave + ":usada") else "inexistente")
        try:
            corpo = _decifrar(bruto)
        except Exception:  # noqa: BLE001 — chave trocada ou conteúdo estranho: não vale
            raise ConfirmacaoRecusada("inexistente") from None
        if (str(corpo.get("company_id")) != str(company_id) or str(corpo.get("user_id")) != str(user_id)
                or str(corpo.get("conversation_id")) != str(conversation_id)):
            raise ConfirmacaoRecusada("de_outra_pessoa")
        if not confirmou_depois(falas_do_corretor, vistas=corpo.get("falas_vistas"), resumo_em=corpo.get("resumo_em")):
            raise ConfirmacaoRecusada("sem_sim")             # ⛔ NÃO consome: o "sim" do próximo turno vale
        if int(await r.delete(chave) or 0) != 1:     # 🔴 só quem APAGOU segue (a outra chamada perdeu a corrida)
            raise ConfirmacaoRecusada("ja_usada")
        try:
            await r.set(chave + ":usada", "1", ex=VALIDADE_S)
        except Exception as exc:  # noqa: BLE001 — a marca é cortesia (a frase); o uso único já valeu pelo DEL
            logger.warning("[COTACAO] marca de 'já usada' não gravada (%s)", type(exc).__name__)
    except ConfirmacaoRecusada:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning("[COTACAO] confirmação ilegível (%s)", type(exc).__name__)
        raise ConfirmacaoRecusada("sem_redis") from None
    return dict(corpo.get("conteudo") or {})
