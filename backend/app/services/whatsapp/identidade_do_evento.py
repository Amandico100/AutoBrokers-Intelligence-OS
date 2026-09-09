# -*- coding: utf-8 -*-
"""De quem é este evento do WhatsApp — UMA resposta, um lugar só.

🔴 **POR QUE ESTE MÓDULO EXISTE (09/09/2026, primeiro dia de piloto real).**

A Regina trabalhou pelo WhatsApp Web. 📊 93% dos ids de saída daquele dia
estavam no formato multi-device, e o WhatsApp endereça esses chats por `@lid` —
um identificador **opaco** de ~15 dígitos que não é telefone de ninguém.

`normalize_evolution_inbound` fazia `remoteJid.split("@")[0]` e chamava aquilo de
"phone". Consequência medida no banco de produção:

    📊 as 5 pausas por intervenção humana de toda a história do produto estão em
       conversas cujo `user_phone` tem 15 dígitos — conversas-FANTASMA, criadas
       pelo LID. A conversa real do segurado seguia `open`, e o agente respondia
       por cima da atendente.

O telefone de verdade vem no envelope, ao lado do LID: `key.remoteJidAlt` (o
conversor do Evolution GO já o preserva, `evolution_go_events.py:123`) ou
`key.remoteJidPn`. `attendance_capture.client_chat_allowed` já fazia o certo — e
era o único. Esta função é aquele acerto, promovido a lugar único.

⚠️ **Este módulo não importa NADA do produto** — nem `app.core`, nem
`app.services`. É a mesma disciplina de `app/telefone_br.py`, e pelo mesmo
motivo: quem precisa saber de quem é o evento são normalizadores e guardas que
não podem subir o mundo para perguntar.

⛔ **Nunca inventar telefone.** Sem alternativo resolvível, a resposta é
`""` — e o chamador registra a recusa **sem PII** e segue. Um LID devolvido como
telefone é pior que telefone nenhum: ele cria uma pessoa que não existe.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

# Sufixos de JID que pertencem a uma LINHA de telefone de verdade. `@lid` está
# fora de propósito — é o identificador opaco, não a linha.
SUFIXOS_DE_LINHA = ("@s.whatsapp.net", "@c.us")

# 🔴 O GUARDA DE FORMA. Um LID brasileiro observado em produção tem 15 dígitos e
# não começa com `55`. Um celular BR completo tem 13 (`55` + DDD + 9 dígitos).
#
# ⚠️ O preço desta linha, dito por inteiro: um número ESTRANGEIRO com 13 dígitos
# ou mais é recusado aqui. É deliberado enquanto o produto atende corretoras
# brasileiras — o custo de recusar é uma conversa que não nasce (visível, com
# log); o custo de aceitar é uma conversa-fantasma que engole a pausa da
# atendente (invisível, e foi o defeito de 09/09).
DIGITOS_DE_TELEFONE_BR = 13


def _digitos(valor: Any) -> str:
    """Só os dígitos — a mesma normalização de `app/telefone_br.py::so_digitos`.

    Repetida aqui, e só ela, porque este módulo não importa nada: são três
    linhas de regra estável, não um motor paralelo (CLAUDE.md §5).
    """
    return "".join(ch for ch in str(valor or "") if ch.isdigit())


def _parece_telefone(digitos: str) -> bool:
    """A forma passa? — a pergunta que separa telefone de LID."""
    if not digitos:
        return False
    if len(digitos) >= DIGITOS_DE_TELEFONE_BR and not digitos.startswith("55"):
        return False
    return True


def jid_alternativo(key: Optional[Dict[str, Any]],
                    data: Optional[Dict[str, Any]] = None) -> str:
    """O JID de LINHA que viaja ao lado do `@lid`, ou `""`.

    As quatro grafias que circulam nos payloads reais, na ordem em que o
    Observador já as lia (`observer_intake.py:1010-1017`) — buscar por nome
    exato numa só foi o defeito P-56, e não se repete aqui.
    """
    k = key if isinstance(key, dict) else {}
    d = data if isinstance(data, dict) else {}
    for fonte, campo in ((k, "remoteJidAlt"), (k, "remoteJidPn"),
                         (d, "remoteJidAlt"), (d, "remoteJidPn"),
                         (d, "senderAlt")):
        valor = str(fonte.get(campo) or "").strip()
        if valor:
            return valor
    return ""


def telefone_do_evento(key: Optional[Dict[str, Any]],
                       data: Optional[Dict[str, Any]] = None) -> str:
    """O telefone (só dígitos) da contraparte deste evento, ou `""`.

    · chat por `@lid`  → o telefone vem do JID alternativo, **nunca** do LID.
    · chat por linha   → o telefone é o próprio JID.
    · grupo, status, canal, transmissão, chamada → `""` (não são pessoa).
    · qualquer coisa cuja FORMA não seja telefone → `""`.

    Vale para os dois sentidos: a mensagem que ENTRA e o `fromMe` que a
    atendente mandou. É o mesmo chat e tem de ser a mesma conversa.
    """
    k = key if isinstance(key, dict) else {}
    d = data if isinstance(data, dict) else {}
    remoto = str(k.get("remoteJid") or d.get("remoteJid") or "").strip().lower()
    if not remoto:
        return ""
    if remoto.endswith(("@g.us", "@broadcast", "@newsletter", "@call")):
        return ""
    if remoto.endswith("@lid"):
        alternativo = jid_alternativo(k, d).strip().lower()
        if not alternativo.endswith(SUFIXOS_DE_LINHA):
            return ""
        bruto = alternativo.split("@", 1)[0].split(":", 1)[0]
    else:
        bruto = remoto.split("@", 1)[0].split(":", 1)[0]
    digitos = _digitos(bruto)
    return digitos if _parece_telefone(digitos) else ""


__all__ = ["telefone_do_evento", "jid_alternativo", "SUFIXOS_DE_LINHA",
           "DIGITOS_DE_TELEFONE_BR"]
