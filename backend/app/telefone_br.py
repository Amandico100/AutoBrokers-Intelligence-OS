# -*- coding: utf-8 -*-
"""O telefone brasileiro tem DUAS formas — e esta é a regra, uma só.

> **O TESTE DO PRODUTO:** *"o mesmo celular gravado com o nono dígito numa
> tabela e sem ele na outra é a MESMA pessoa — e o produto tem de saber disso
> no mesmo lugar, sempre."*

🔴 **Por que este módulo existe (SPEC-097, P3-4).** A regra do nono dígito já
morava em três arquivos — `atlas/observer_intake.py::_br_variants`,
`whatsapp/channel_security.py::_variants` e `platform_outbound.py::
_phone_variants` — e o backfill do elo episódio↔conversa ia escrever a quarta.
📊 Medido em 05/09/2026: `_conversa_unica_do_telefone` casava por **igualdade
exata de dígitos** enquanto o MESMO arquivo correlacionava telefone com
variantes 40 linhas abaixo. Um par (com 9 / sem 9) virava "órfão" em vez de elo,
e o 📊 57,8% de casamento era o resultado do casador estrito, não do acervo.

⚠️ **E ele não importa NADA** — nem `app.core`, nem `app.services`. É de
propósito: quem precisa da regra são scripts e guardas que não podem subir o
mundo para perguntar como se escreve um telefone.
"""
from __future__ import annotations

from typing import Any, Set


def so_digitos(valor: Any) -> str:
    """Só os dígitos. ⛔ É a normalização do produto inteiro — não invente outra."""
    return "".join(ch for ch in str(valor or "") if ch.isdigit())


def variantes_br(numero: Any) -> Set[str]:
    """As formas em que ESTE número pode estar gravado — com e sem o 9º dígito.

    ⚠️ **Só mexe em `55` + DDD + 8/9 dígitos.** Número curto, estrangeiro ou
    `@lid` volta como veio: inventar um nono dígito onde ele não existe casaria
    duas pessoas diferentes, que é o oposto do que esta função serve.
    """
    d = so_digitos(numero)
    if not d:
        return set()
    formas = {d}
    if d.startswith("55"):
        resto = d[2:]
        if len(resto) == 11 and resto[2] == "9":
            formas.add("55" + resto[:2] + resto[3:])
        elif len(resto) == 10:
            formas.add("55" + resto[:2] + "9" + resto[2:])
    return formas
