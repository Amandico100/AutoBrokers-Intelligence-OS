# -*- coding: utf-8 -*-
"""Prazos regulatórios de sinistro, com VIGÊNCIA. SPEC-093-B BLOCO C ⑤ · referência ⑥.

Por que este módulo existe, e por que ele é PURO
------------------------------------------------
🔴 **Prazo sem vigência é bug futuro.** A Resolução CNSP nº 496/2026 (📊 notícia da
SUSEP de 17/08/2026, lida em 03/09/2026) é obrigatória **apenas** para contratos de
seguros de danos *formados ou renovados a partir de 05/01/2027*; os planos anteriores
têm até 04/01/2027 para se adaptar. Um número escrito solto no código responde certo
hoje e errado no ano que vem, sem nunca acusar a mudança — e ninguém descobre, porque
o código não diz de quando ele fala.

Então aqui nenhum prazo é um literal: cada um é uma LINHA declarada com
`{valor, unidade, ramo, kind, etapa, fonte, vigencia_de, vigencia_ate, aplicabilidade}`,
e `espera_vencida()` resolve pela **data do contrato**. Sem essa data, a resposta é
`'regime_nao_determinado'` — dizer que não se sabe é mais barato que inventar o regime.

⚠️ O que este módulo NÃO faz, de propósito
------------------------------------------
⛔ Não interpreta aplicabilidade (isso é do humano) · ⛔ não alerta o segurado ·
⛔ não decide sobre cobertura. Ele responde uma pergunta só: *"esta espera passou do
prazo declarado para o regime do contrato?"* — e admite não saber.

📊 O regime ANTERIOR (Resolução CNSP nº 407/2021, revogada pela 496/2026)
--------------------------------------------------------------------------
A notícia da SUSEP diz que a 496 **revoga** a 407/2021, e **não** informa os prazos da
norma antiga. Pesquisado em 03/09/2026 na própria fonte declarada na referência ⑥; não
achado ali. Então a linha do regime anterior nasce com `valor=None` e fonte escrita
como *não determinado nesta SPEC* — e a função devolve `'regime_nao_determinado'` para
contrato anterior a 05/01/2027. 💭 Preencher esse valor com um palpite seria pior que a
lacuna: viraria "vencido" citável sobre uma norma que ninguém leu (CLAUDE.md §12.1).
"""

from __future__ import annotations

import datetime as _dt
from typing import Any, Optional, Union

#: Resposta quando o regime aplicável não pode ser determinado. NUNCA um booleano.
REGIME_NAO_DETERMINADO = "regime_nao_determinado"

#: A data a partir da qual a CNSP 496/2026 é obrigatória (contratos formados ou renovados).
INICIO_CNSP_496 = "2027-01-05"
#: O último dia em que um plano anterior ainda podia rodar sob o regime velho.
FIM_DO_REGIME_ANTERIOR = "2027-01-04"

_FONTE_496 = "CNSP 496/2026 (notícia SUSEP 17/08/2026, lida em 03/09/2026)"
_APLICA_496 = "contratos de seguros de danos formados ou renovados a partir de 05/01/2027"


# ---------------------------------------------------------------------------
# A TABELA. 🔴 Cada linha carrega o número E a vigência dele — na mesma linha
# física, para que `grep` de número solto no código não tenha o que achar.
# ---------------------------------------------------------------------------
PRAZOS: list[dict] = [
    {
        "ramo": "*", "kind": "esperando_seguradora", "etapa": "regulacao",
        "valor": 30, "unidade": "dias", "vigencia_de": INICIO_CNSP_496, "vigencia_ate": None,
        "fonte": _FONTE_496, "aplicabilidade": _APLICA_496,
        "capitulo": "geral",
    },
    {
        "ramo": "capitulo_iii", "kind": "esperando_seguradora", "etapa": "regulacao",
        "valor": 120, "unidade": "dias", "vigencia_de": INICIO_CNSP_496, "vigencia_ate": None,
        "fonte": _FONTE_496, "aplicabilidade": _APLICA_496,
        "capitulo": "III",
    },
    {
        "ramo": "*", "kind": "esperando_seguradora", "etapa": "liquidacao",
        "valor": 30, "unidade": "dias", "vigencia_de": INICIO_CNSP_496, "vigencia_ate": None,
        "fonte": _FONTE_496, "aplicabilidade": _APLICA_496,
        "capitulo": "geral",
    },
    {
        "ramo": "capitulo_iii", "kind": "esperando_seguradora", "etapa": "liquidacao",
        "valor": 120, "unidade": "dias", "vigencia_de": INICIO_CNSP_496, "vigencia_ate": None,
        "fonte": _FONTE_496, "aplicabilidade": _APLICA_496,
        "capitulo": "III",
    },
    {
        # 🔴 A LACUNA, escrita. Ver o cabeçalho: a fonte declarada da referência ⑥
        # não informa os prazos da norma revogada, e esta SPEC não os determina.
        "ramo": "*", "kind": "esperando_seguradora", "etapa": "regulacao",
        "valor": None, "unidade": "dias",
        "vigencia_de": None, "vigencia_ate": FIM_DO_REGIME_ANTERIOR,
        "fonte": "regime anterior: não determinado nesta SPEC",
        "aplicabilidade": "planos formados antes de 05/01/2027 (CNSP 407/2021, revogada)",
        "capitulo": "anterior",
    },
    {
        "ramo": "*", "kind": "esperando_seguradora", "etapa": "liquidacao",
        "valor": None, "unidade": "dias",
        "vigencia_de": None, "vigencia_ate": FIM_DO_REGIME_ANTERIOR,
        "fonte": "regime anterior: não determinado nesta SPEC",
        "aplicabilidade": "planos formados antes de 05/01/2027 (CNSP 407/2021, revogada)",
        "capitulo": "anterior",
    },
]


# ---------------------------------------------------------------------------
# Conversão de data — permissiva na entrada, estrita na saída
# ---------------------------------------------------------------------------
_Data = Union[str, _dt.date, _dt.datetime, None]


def como_data(valor: _Data) -> Optional[_dt.date]:
    """`date` a partir de `date`, `datetime` ou ISO-8601. `None` quando não dá.

    ⚠️ Aceita o `Z` do PostgREST: `fromisoformat` do Python só passou a aceitá-lo em
    3.11, e o worker não é o lugar de descobrir isso.
    """
    if valor is None:
        return None
    if isinstance(valor, _dt.datetime):
        return valor.date()
    if isinstance(valor, _dt.date):
        return valor
    # 🔴 NÚMERO NÃO É DATA — e é a recusa que fecha a porta mais perigosa deste módulo.
    #
    # 📊 Um epoch (`1767571200`) e um `20270105` viram `str` e chegam ao
    # `date.fromisoformat(texto[:10])`. O epoch falha e devolve `None` (por sorte, não
    # por regra); o `20270105` é aceito por `fromisoformat` desde o Python 3.11, que é
    # o formato básico da ISO-8601 — e o worker roda em 3.14. Um `int` de outro
    # formato entraria como uma data que ninguém escreveu, e a resposta seria
    # "vencida"/"não vencida" sobre um regime inventado. ⛔ `bool` cai aqui junto,
    # que é onde ele tem de cair.
    if isinstance(valor, (bool, int, float)):
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    try:
        return _dt.datetime.fromisoformat(texto.replace("Z", "+00:00")).date()
    except Exception:  # noqa: BLE001
        pass
    try:
        return _dt.date.fromisoformat(texto[:10])
    except Exception:  # noqa: BLE001
        return None


def _vigente_para(prazo: dict, data_contrato: _dt.date) -> bool:
    """A linha cobre um contrato formado nesta data?"""
    de = como_data(prazo.get("vigencia_de"))
    ate = como_data(prazo.get("vigencia_ate"))
    if de is not None and data_contrato < de:
        return False
    if ate is not None and data_contrato > ate:
        return False
    return True


def prazo_aplicavel(kind: str, *, ramo: str = "*", etapa: str = "regulacao",
                    data_contrato: _Data = None) -> Optional[dict]:
    """A linha de `PRAZOS` que rege esta espera, ou `None`.

    O `ramo` casa exato ou pelo curinga `*`; o exato vence, para que o Capítulo III
    não seja apagado pela regra geral quando o chamador souber o ramo.
    """
    dc = como_data(data_contrato)
    if dc is None:
        return None
    candidatos = [p for p in PRAZOS
                  if p.get("kind") == kind
                  and p.get("etapa") == etapa
                  and p.get("ramo") in (ramo, "*")
                  and _vigente_para(p, dc)]
    if not candidatos:
        return None
    exatos = [p for p in candidatos if p.get("ramo") == ramo]
    return (exatos or candidatos)[0]


def espera_vencida(kind: str, aberta_em: _Data, agora: _Data = None,
                   data_contrato: _Data = None, *,
                   ramo: str = "*", etapa: str = "regulacao"
                   ) -> Union[bool, str]:
    """A espera passou do prazo do regime DO CONTRATO?

    Devolve `True`, `False` ou `'regime_nao_determinado'` — três respostas, porque
    duas obrigariam a chutar. 🔴 Sem `data_contrato` a resposta é sempre a terceira:
    a norma nova vale por data de formação/renovação, e sem ela não há regime.
    """
    inicio = como_data(aberta_em)
    if inicio is None:
        return REGIME_NAO_DETERMINADO
    if como_data(data_contrato) is None:
        return REGIME_NAO_DETERMINADO

    prazo = prazo_aplicavel(kind, ramo=ramo, etapa=etapa, data_contrato=data_contrato)
    if not prazo or prazo.get("valor") is None:
        return REGIME_NAO_DETERMINADO

    fim = como_data(agora) or _dt.date.today()
    return (fim - inicio).days > int(prazo["valor"])


def descrever(prazo: Optional[dict]) -> str:
    """Uma linha citável: valor, unidade, fonte e desde quando vale. Sem PII."""
    if not prazo or prazo.get("valor") is None:
        return "regime não determinado"
    desde = prazo.get("vigencia_de") or "sempre"
    return "%s %s (%s, desde %s)" % (prazo["valor"], prazo.get("unidade") or "dias",
                                     prazo.get("fonte") or "sem fonte", desde)


def _tabela_como_dicts() -> list[dict[str, Any]]:
    """Cópia rasa da tabela — para quem quiser exibi-la sem poder alterá-la."""
    return [dict(p) for p in PRAZOS]
