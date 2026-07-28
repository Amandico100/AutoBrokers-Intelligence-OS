"""Um vocabulário só para o estado do canal de WhatsApp.

O problema
----------
Havia três vocabulários para a mesma coisa, e ninguém tinha percebido:

    pareamento escreve ....  "connecting" / "connected"
    webhook escreve .......  "open" / "close" / "connecting"   (vocabulário do Evolution)
    telas leem ............  "connected"

Resultado, medido em 28/07/2026 com a Resulta já pareada e funcionando: o
Evolution Go dizia `connected: true`, o banco dizia `"connecting"`, e a tela do
Admin mostrava **`unknown`**.

Nada quebrou — o card do dashboard lê o estado ao vivo e mostrou "Conectado"
corretamente. Mas o Admin lê o banco, e ficou mentindo.

É a mesma família do `master` × `master_admin` que trancou o Founder fora do
próprio Admin: igualdade de string entre vocabulários que ninguém unificou.

A regra
-------
Este arquivo é o **único** tradutor. Quem grava `channel_status` passa por aqui;
quem lê compara com as constantes daqui. Um estado desconhecido vira
`DESCONHECIDO` de propósito, e não `"connected"` — inventar conexão que não se
confirmou é pior que admitir que não se sabe.
"""

from __future__ import annotations

CONECTADO = "connected"
CONECTANDO = "connecting"
DESCONECTADO = "disconnected"
APOSENTADO = "retired"
DESCONHECIDO = "unknown"

# Todo jeito que já vimos cada estado ser escrito — pelo Evolution v2, pelo GO,
# pelo pareamento e pelas telas. A lista cresce quando aparecer um novo; o que
# não pode é cada leitor conhecer um pedaço dela.
_TRADUCAO = {
    # conectado
    "open": CONECTADO, "connected": CONECTADO, "online": CONECTADO,
    "loggedin": CONECTADO, "logged_in": CONECTADO,
    # conectando
    "connecting": CONECTANDO, "pairing": CONECTANDO, "qr": CONECTANDO,
    "qrcode": CONECTANDO, "syncing": CONECTANDO,
    # desconectado
    "close": DESCONECTADO, "closed": DESCONECTADO, "disconnected": DESCONECTADO,
    "logout": DESCONECTADO, "logged_out": DESCONECTADO, "offline": DESCONECTADO,
    "qr_expired": DESCONECTADO, "timeout": DESCONECTADO,
    # aposentado
    "retired": APOSENTADO, "archived": APOSENTADO, "deleted": APOSENTADO,
}


def normalizar_estado(bruto: object) -> str:
    """Traduz qualquer forma conhecida para o vocabulário único."""
    chave = str(bruto or "").strip().lower().replace("-", "_")
    return _TRADUCAO.get(chave, DESCONHECIDO)


def esta_conectado(bruto: object) -> bool:
    """A única pergunta que a maioria das telas faz.

    Devolve `True` só quando o estado é reconhecidamente conectado. Estado
    desconhecido é `False`: uma tela que mostra "Conectado" sem confirmação faz
    o corretor achar que os segurados estão sendo atendidos quando não estão.
    """
    return normalizar_estado(bruto) == CONECTADO


def rotulo_humano(bruto: object) -> str:
    """O que aparece para uma pessoa — nunca a palavra crua do protocolo."""
    return {
        CONECTADO: "Conectado",
        CONECTANDO: "Conectando…",
        DESCONECTADO: "Desconectado",
        APOSENTADO: "Aposentado",
    }.get(normalizar_estado(bruto), "Estado desconhecido")
