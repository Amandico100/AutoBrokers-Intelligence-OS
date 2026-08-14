"""O produto reconhece a própria voz quando ela volta pelo WhatsApp.

🔴 POR QUE ESTE MÓDULO EXISTE — o defeito que teria matado o go-live
====================================================================
Toda mensagem que o produto envia pelo WhatsApp **volta** pelo webhook marcada
como `fromMe`. Está medido e documentado desde 06/08/2026 (`espelho_chat.py` —
é a razão de existir a guarda de eco do dashboard).

📊 14/08/2026, conferido em `webhook.py:1180`: o ramo que trata `fromMe`
pergunta apenas *"veio de nós e tem texto?"*. **Não pergunta QUEM escreveu.**
E `webhook.py:777` grava a resposta da IA sem `payload` — não havia marca
nenhuma que permitisse distinguir.

O resultado, no dia em que o agente fosse ligado:

    cliente:  "bati o carro"
    agente:   "Sinto muito! Me diga a placa..."      ← responde certo
              (a resposta volta como fromMe)
    sistema:  "uma pessoa respondeu pelo celular" → pausa a IA
    cliente:  "ABC1234"
    agente:   (silêncio, para sempre)

O agente responderia **uma vez** e emudeceria. Trinta minutos depois o grupo de
suporte receberia "⏳ AINDA SEM ATENDIMENTO" sobre uma conversa que ninguém
abandonou.

Isso não mordia em produção só porque o agente estava desligado — o padrão
exato do CLAUDE.md §9.1: o defeito abre sozinho no dia mais caro possível.

COMO FUNCIONA
=============
Antes de o produto falar, ele anota a digital do que vai dizer. Quando aquilo
volta como `fromMe`, ele reconhece e **não** trata como intervenção humana.

    registrar_nossa_fala(company, telefone, texto)   antes de enviar
    e_a_nossa_propria_voz(company, telefone, texto)  no ramo fromMe

🔴 POR BALÃO, NÃO POR MENSAGEM. `whatsapp_service.send_message` quebra a
resposta em balões curtos (humanização, S17-9) e envia um a um — então voltam
N mensagens `fromMe`, uma por balão. Registrar o texto inteiro reconheceria
zero delas.

POR QUE REDIS, E POR QUE ISSO É SEGURO
======================================
Estado transitório de segundos: é exatamente o que o Redis guarda (CLAUDE.md
§6). E a direção da falha é a certa — se o Redis sumir, nenhuma digital é
encontrada, toda volta é lida como intervenção humana e a IA **cala**. Chato e
reversível pelo botão "Devolver à IA"; nunca o contrário.

O consumo é destrutivo (`GETDEL`): a digital vale para UMA volta. Se a
atendente digitar de propósito a mesma frase que a IA acabou de mandar, a
primeira é reconhecida como eco e a segunda pausa — que é o comportamento certo,
porque a segunda é mesmo dela.
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Quanto tempo a digital sobrevive. O eco volta em segundos; o teto é folgado
# para um provedor lento não fazer o agente se calar. Curto o bastante para não
# reconhecer como eco uma frase repetida pela atendente meia hora depois.
_TTL_SEGUNDOS = 180

_CHAVE = "voz:{empresa}:{telefone}:{digital}"


def _digitos(valor: Any) -> str:
    return "".join(ch for ch in str(valor or "") if ch.isdigit())


def _digital(texto: str) -> str:
    """A impressão digital do texto. Normaliza o que o transporte pode mexer.

    O WhatsApp e os provedores não devolvem sempre byte a byte o que receberam:
    espaço em excesso, quebra de linha e espaço nas pontas variam. Comparar o
    texto cru faria a digital falhar justamente no caso comum.

    Não guardamos o texto — só o hash. Conteúdo de conversa não vira chave de
    Redis (CLAUDE.md §7: nenhum segredo, nenhum conteúdo, em log ou cache).
    """
    normalizado = re.sub(r"\s+", " ", str(texto or "")).strip().lower()
    return hashlib.sha256(normalizado.encode("utf-8")).hexdigest()[:32]


def _chave(company_id: str, telefone: str, texto: str) -> str:
    return _CHAVE.format(
        empresa=str(company_id or "").strip(),
        telefone=_digitos(telefone),
        digital=_digital(texto),
    )


def registrar_nossa_fala(company_id: str, telefone: str, texto: str) -> None:
    """Anota que o PRODUTO vai dizer isto. Chamar ANTES de enviar.

    Nunca levanta: se o Redis estiver fora, o envio continua e o pior caso é a
    IA se pausar sozinha naquela conversa — visível, reversível por botão.
    Falhar o envio para proteger uma guarda seria trocar um defeito por outro
    pior: o segurado ficaria sem resposta nenhuma.
    """
    if not str(texto or "").strip() or not company_id or not telefone:
        return
    try:
        from app.core.redis import get_redis_client

        get_redis_client().setex(_chave(company_id, telefone, texto), _TTL_SEGUNDOS, "1")
    except Exception as erro:  # noqa: BLE001
        logger.warning("[VOZ] não consegui registrar a própria fala (%s)",
                       type(erro).__name__)


def e_a_nossa_propria_voz(company_id: str, telefone: str, texto: str) -> bool:
    """Este `fromMe` é eco do que NÓS acabamos de dizer?

    `True`  → é o produto se ouvindo. Espelha, mas NÃO pausa a IA.
    `False` → é uma pessoa de verdade escrevendo. Pausa.

    Consome a digital (`GETDEL`): ela vale para uma volta só.

    ⚠️ Em caso de erro devolve `False` — ou seja, trata como intervenção humana
    e a IA cala. É a direção segura: duas vozes falando com o mesmo segurado é
    pior que uma IA calada que a atendente reativa num clique.
    """
    if not str(texto or "").strip() or not company_id or not telefone:
        return False
    try:
        from app.core.redis import get_redis_client

        cliente = get_redis_client()
        chave = _chave(company_id, telefone, texto)
        # GETDEL é atômico: duas voltas simultâneas do mesmo texto não podem
        # ambas se declarar eco. A segunda é tratada como pessoa — que é o
        # lado certo de errar.
        try:
            achou = cliente.getdel(chave)
        except AttributeError:
            # Redis < 6.2 não tem GETDEL. Pipeline em MULTI mantém a atomicidade.
            pipe = cliente.pipeline()
            pipe.get(chave)
            pipe.delete(chave)
            achou = pipe.execute()[0]
        return bool(achou)
    except Exception as erro:  # noqa: BLE001
        logger.warning("[VOZ] não consegui conferir a própria voz (%s) — "
                       "tratando como intervenção humana", type(erro).__name__)
        return False


__all__ = ["registrar_nossa_fala", "e_a_nossa_propria_voz"]
