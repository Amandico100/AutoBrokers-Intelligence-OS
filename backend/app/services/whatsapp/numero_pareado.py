"""Qual telefone está do outro lado deste pareamento. SPEC-063.

Por que este módulo existe
--------------------------
Em 04/08/2026 o Founder não soube dizer qual número estava conectado no celular
da atendente. Não era falha de memória dele: **o sistema nunca guardou**. O
pareamento gravava `channel_status='connected'` e `last_seen_at`, e o telefone —
a única coisa que responde "de quem é esta linha?" — era descartado.

O que sobrava para adivinhar era o `identifier`, que no evolution-go é o NOME DA
INSTÂNCIA (`ab-obs-6c9c55e22f-1`). Quem lesse aquilo procurando um telefone
achava `6955221`, que não é telefone de ninguém.

A regra mora aqui, sozinha e sem dependência, porque tem DOIS chamadores — o
orquestrador de pareamento (que vê o `/instance/status`) e o Observador (que vê
o `connection.update` do webhook). Duas implementações divergiriam, e a segunda
ficaria para trás: foi exatamente assim que a leitura de cliques do WhatsApp
durou três semanas errada em um arquivo depois de consertada no outro.

O que este módulo NÃO faz
------------------------
Não inventa. O provedor pode não mandar o JID, e nesse caso a resposta é `None`
— não um palpite tirado do nome da instância. Um número errado gravado como
"o WhatsApp da Regina" é pior que campo vazio: o vazio se pergunta, o errado se
acredita.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

# Onde os provedores escrevem o JID de quem pareou. A lista é generosa de
# propósito: o shape do evolution-go não está confirmado ao vivo para o
# `connection.update`, e procurar em vários nomes custa nada. Inventar um
# parser por tentativa de deploy custa um ciclo inteiro (CLAUDE.md §9.2).
_CHAVES_DE_JID = (
    "jid", "Jid", "JID", "wid", "Wid", "wuid", "Wuid",
    "ownerJid", "OwnerJid", "owner", "Owner",
    "loggedInJid", "LoggedInJid", "deviceJid", "DeviceJid",
    "me", "Me", "user", "User", "device", "Device", "id", "ID", "Id",
)

# Sufixos de JID que pertencem a uma LINHA de telefone. `@lid` fica de fora de
# propósito: é um identificador opaco do WhatsApp, e dele não se deduz número.
_SERVIDORES_DE_LINHA = ("@s.whatsapp.net", "@c.us")


def _digitos(valor: Any) -> str:
    return "".join(ch for ch in str(valor or "") if ch.isdigit())


def jid_pareado(payload: Any, _profundidade: int = 0) -> Optional[str]:
    """Acha o JID de quem pareou dentro de um payload de status/conexão.

    Busca em profundidade porque o mesmo dado chega ora em `data.jid`, ora em
    `data.Me.ID`, ora na raiz. Limite de profundidade para não passear por
    payload grande — o JID sempre esteve perto do topo nos exemplos conhecidos.
    """
    if _profundidade > 4 or not isinstance(payload, dict):
        return None

    for chave in _CHAVES_DE_JID:
        if chave not in payload:
            continue
        valor = payload[chave]
        if isinstance(valor, str) and valor.endswith(_SERVIDORES_DE_LINHA):
            return valor
        if isinstance(valor, dict):
            # JID estruturado do whatsmeow: {User: "5547...", Server: "s.whatsapp.net"}
            usuario = valor.get("User") or valor.get("user")
            servidor = valor.get("Server") or valor.get("server")
            if usuario and _digitos(usuario):
                return f"{_digitos(usuario)}@{servidor or 's.whatsapp.net'}"
            achado = jid_pareado(valor, _profundidade + 1)
            if achado:
                return achado

    for chave in ("data", "Data", "instance", "Instance", "status", "Status"):
        aninhado = payload.get(chave)
        if isinstance(aninhado, dict):
            achado = jid_pareado(aninhado, _profundidade + 1)
            if achado:
                return achado
    return None


def telefone_e164(jid: Optional[str]) -> Optional[str]:
    """`5547999999999:12@s.whatsapp.net` → `+5547999999999`.

    O sufixo `:12` é o número do DISPOSITIVO, não do telefone. Mantê-lo faria
    o mesmo WhatsApp aparecer como duas linhas diferentes toda vez que a pessoa
    trocasse de aparelho.
    """
    if not jid or not str(jid).endswith(_SERVIDORES_DE_LINHA):
        return None
    numero = _digitos(str(jid).split("@", 1)[0].split(":", 1)[0])
    # Um E.164 plausível tem entre 8 e 15 dígitos. Fora disso não é telefone —
    # é o nome de uma instância picotado, e é justamente esse engano que este
    # módulo existe para não repetir.
    if not (8 <= len(numero) <= 15):
        return None
    return f"+{numero}"


def identidade_pareada(payload: Any) -> Tuple[Optional[str], Optional[str]]:
    """(jid, telefone_e164) — ou (None, None) quando o provedor não disse."""
    jid = jid_pareado(payload)
    return jid, telefone_e164(jid)


def mascarar(numero: Optional[str]) -> str:
    """`+5547988087463` → `5547*****463`. Para log, tela de suporte e relatório.

    Telefone de segurado e de atendente é PII. CLAUDE.md §13.3 manda mostrar
    presença, nunca o valor — e um canal só precisa ser RECONHECÍVEL por quem
    já o conhece, não legível por quem não deveria.
    """
    digitos = _digitos(numero)
    if not digitos:
        return "sem-numero"
    if len(digitos) <= 7:
        return digitos[:2] + "*" * 5
    # Cinco estrelas SEMPRE, e não uma por dígito escondido: a quantidade de
    # estrelas revelaria o comprimento do número, que separa celular de fixo e
    # estreita quem pode ser. Máscara não deve contar o que esconde.
    return f"{digitos[:4]}*****{digitos[-3:]}"


def dados_de_pareamento(payload: Any, agora_iso: str) -> Dict[str, Any]:
    """O que gravar em `integrations` quando uma linha conecta.

    Devolve dicionário VAZIO quando não há JID: um update sem campo nenhum é
    melhor que um update que apaga o telefone que já estava lá. O provedor
    silenciar num refresh não pode desfazer o que ele disse no pareamento.
    """
    jid, telefone = identidade_pareada(payload)
    if not jid or not telefone:
        return {}
    return {"paired_jid": jid, "paired_phone_e164": telefone, "paired_at": agora_iso}


__all__ = [
    "jid_pareado", "telefone_e164", "identidade_pareada",
    "mascarar", "dados_de_pareamento",
]
