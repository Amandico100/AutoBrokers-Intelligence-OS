# -*- coding: utf-8 -*-
"""A saúde do portal dita em português — UM dicionário, DUAS telas.

SPEC-EXTRA-001.6 B3.4. A tela de Conectores > Portais e a Central de Agentes
mostram a mesma palavra porque leem a MESMA função: o `health` bruto
(`ok`, `expirada`, `credencial_recusada`, `pede_humano`, `fora_do_ar`,
`unknown`) nunca chega ao frontend sozinho.

🔴 O vocabulário não é redefinido aqui: ele é IMPORTADO de quem escreve
(`portal_worker.worker`). Uma segunda lista não avisa que envelheceu — foi
assim que a Central de Agentes ficou com 9 ids contra 14 do registro
(SPEC-088 BLOCO D). A direção do import é a que o repositório já usa em
`app/api/portal.py:78` e `app/services/billing_collection.py:71`.

⛔ Nada aqui lê banco, escreve banco ou fala com o portal. Função pura de
`(health, quando)` para `(rótulo, ação)`.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional

from portal_worker.worker import (  # a lista vive onde está o escritor
    GRAVIDADE_DA_SAUDE,
    SAUDE_CREDENCIAL_RECUSADA,
    SAUDE_DESCONHECIDA,
    SAUDE_EXPIRADA,
    SAUDE_FORA_DO_AR,
    SAUDE_OK,
    SAUDE_PEDE_HUMANO,
    VOCABULARIO_DE_SAUDE,
)

__all__ = [
    "GRAVIDADE_DA_SAUDE", "VOCABULARIO_DE_SAUDE", "ESTADO_NA_CENTRAL",
    "rotulo_e_acao", "pior_saude", "data_curta",
]

# O estado equivalente no contrato da Central de Agentes (SPEC-088 §4). ⚠️ Só
# estes cinco existem lá, e um valor fora deles aparece em VERMELHO na tela —
# de propósito. `unknown` NÃO é benigno: é "ninguém mediu ainda".
ESTADO_NA_CENTRAL: Dict[str, str] = {
    SAUDE_OK: "SAUDAVEL",
    SAUDE_DESCONHECIDA: "NAO_MEDIDO",
    SAUDE_EXPIRADA: "PULSA_SEM_PRODUZIR",
    SAUDE_PEDE_HUMANO: "PARADO",
    SAUDE_FORA_DO_AR: "PARADO",
    SAUDE_CREDENCIAL_RECUSADA: "PARADO",
}

# 💭 Os rótulos são proposta de copy (CLAUDE.md §12.1): valem até o Founder
# emendar. O que NÃO é ilustrativo é a regra — cada linha diz o que aconteceu e
# o que a pessoa faz a seguir; estado sem próximo passo é enfeite.
_ROTULOS: Dict[str, Dict[str, str]] = {
    SAUDE_OK: {
        "rotulo": "entrou {quando}",
        "acao": "",
        "icone": "✅",
    },
    SAUDE_DESCONHECIDA: {
        "rotulo": "não verificado ainda",
        "acao": "a próxima execução testa uma vez",
        "icone": "⏳",
    },
    SAUDE_EXPIRADA: {
        "rotulo": "sessão vencida",
        "acao": "o robô refaz o login na próxima execução",
        "icone": "\U0001f501",
    },
    SAUDE_CREDENCIAL_RECUSADA: {
        "rotulo": "senha recusada pelo portal",
        "acao": "atualize a senha aqui",
        "icone": "⛔",
    },
    SAUDE_PEDE_HUMANO: {
        "rotulo": "o portal pediu uma ação humana (CAPTCHA/2FA ou tela nova)",
        "acao": "uma pessoa precisa entrar uma vez no portal",
        "icone": "\U0001f9d1",
    },
    SAUDE_FORA_DO_AR: {
        "rotulo": "fora do ar {desde}",
        "acao": "tento de novo sozinho",
        "icone": "⚠️",
    },
}

_MESES_ATRAS = "sem data"


def _parse(quando: Any) -> Optional[datetime]:
    texto = str(quando or "").strip()
    if not texto:
        return None
    try:
        if texto.endswith("Z"):
            texto = texto[:-1] + "+00:00"
        lido = datetime.fromisoformat(texto)
    except Exception:  # noqa: BLE001
        return None
    return lido if lido.tzinfo else lido.replace(tzinfo=timezone.utc)


def data_curta(quando: Any, fuso_horas: int = -3) -> str:
    """`2026-09-13T09:12:00Z` -> `13/09 às 06:12`.

    ⚠️ O banco guarda UTC e quem lê a tela está no Brasil. Sem o deslocamento, a
    frase "entrou hoje às 09:12" apareceria três horas no futuro para quem
    acabou de ver o robô rodar.
    """
    lido = _parse(quando)
    if lido is None:
        return ""
    from datetime import timedelta

    local = lido.astimezone(timezone.utc) + timedelta(hours=fuso_horas)
    return local.strftime("%d/%m às %H:%M")


def rotulo_e_acao(health: Any, quando: Any = None) -> Dict[str, Any]:
    """O que a tela mostra para este `health`. Uma fonte, duas telas.

    Devolve `{"health", "rotulo", "acao", "icone", "estado", "verificado_em"}`.
    Valor desconhecido NUNCA vira verde: cai em `unknown` com o texto honesto.
    """
    bruto = str(health or "").strip() or SAUDE_DESCONHECIDA
    if bruto not in VOCABULARIO_DE_SAUDE:
        bruto = SAUDE_DESCONHECIDA
    modelo = _ROTULOS[bruto]
    data = data_curta(quando)
    texto = modelo["rotulo"].format(
        quando=("em " + data if data else "no portal"),
        desde=("desde " + data if data else "agora"),
    )
    return {
        "health": bruto,
        "rotulo": f"{modelo['icone']} {texto}".strip(),
        "acao": modelo["acao"],
        "icone": modelo["icone"],
        "estado": ESTADO_NA_CENTRAL.get(bruto, "NAO_MEDIDO"),
        "verificado_em": str(quando) if quando else None,
    }


def pior_saude(valores: Iterable[Any]) -> str:
    """A pior saúde de um conjunto de contas — o que o card do portal mostra.

    🔴 O card de um portal com duas contas, uma `ok` e uma `credencial_recusada`,
    NÃO é `ok`: existe cobrança que não sai. A ordem está em
    `GRAVIDADE_DA_SAUDE`, e ela mora junto do escritor.
    """
    lista = [str(v or "").strip() or SAUDE_DESCONHECIDA for v in (valores or [])]
    lista = [v if v in VOCABULARIO_DE_SAUDE else SAUDE_DESCONHECIDA for v in lista]
    if not lista:
        return SAUDE_DESCONHECIDA
    return sorted(lista, key=lambda v: GRAVIDADE_DA_SAUDE.get(v, 9))[0]
