"""A porteira da cobrança. SPEC-062 §4, leis 2 e 4.

O que ela resolve
-----------------
Duas leis da SPEC-062 dizem a mesma coisa por ângulos diferentes:

> **Lei 2.** Usage event não é automaticamente uma cobrança.
> **Lei 4.** Nenhuma cobrança retroativa automática é permitida.

Hoje o sistema não separa as duas coisas. `has_sufficient_balance()` mistura
*medir* com *cobrar*: qualquer corretora sem linha em `company_credits` lê saldo
zero e é **recusada com HTTP 402** no chat e nos auxiliares.

Foi exatamente o que aconteceu com a **AutoFleet**: empresa ativa, sem
assinatura, sem registro de crédito — e portanto bloqueada, sem ninguém ter
decidido bloqueá-la. O bloqueio não foi uma decisão comercial; foi a ausência
de uma linha numa tabela.

O que este módulo faz
---------------------
Um interruptor único: **a cobrança está ligada?** Enquanto estiver desligada,
ninguém é barrado por saldo ou plano — e o consumo **continua sendo medido**.
Medir sem cobrar é o estado correto de um produto que ainda não tem preço.

Por que um interruptor e não apagar a checagem
----------------------------------------------
Apagar as chamadas de `has_sufficient_balance` resolveria hoje e deixaria o
sistema sem porteira nenhuma. Quando o preço existir, alguém teria que
reencontrar os cinco lugares e reintroduzir a checagem — e esquecer um deles é
oferecer serviço de graça sem saber.

Com o interruptor, os cinco lugares continuam chamando a porteira. Muda apenas
a resposta dela.

O que NUNCA é bloqueado
-----------------------
Empresa **suspensa** continua bloqueada, com cobrança ligada ou não. Suspensão
é decisão humana registrada, não consequência de saldo — e a §4 lei 15
(isolamento) depende de suspensão funcionar.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

# O interruptor. Ausente = DESLIGADO.
#
# O padrão é desligado de propósito: um sistema sem catálogo comercial aprovado
# (§4 lei 17 — "a venda não começa antes do catálogo comercial aprovado") não
# deveria conseguir cobrar por acidente de configuração. Ligar é um ato
# deliberado; ficar desligado é o repouso.
FLAG = "BILLING_ENFORCEMENT"


def cobranca_ligada() -> bool:
    return str(os.getenv(FLAG, "0")).strip().lower() in ("1", "true", "on", "yes")


def motivo_de_estar_desligada() -> str:
    return ("A cobrança está desligada nesta instalação. O consumo continua "
            "sendo medido e registrado; ninguém é barrado por saldo ou plano. "
            f"Para ligar: {FLAG}=1.")


# ---------------------------------------------------------------------------
# SPEC-062 §22 — a fronteira comercial
# ---------------------------------------------------------------------------
#
# Existem 1.239 linhas em `token_usage_logs`, todas com `billed = false`. Elas
# são o registro técnico de um ano de desenvolvimento e teste — não são dívida
# de ninguém.
#
# O worker legado `process_unbilled_usage` busca exatamente `billed = false` e
# debita crédito. Ele está parado só porque `USE_CELERY=false`. Uma variável de
# ambiente separa as corretoras de receberem um débito retroativo de um ano.
#
# A §22.1 dá a regra: tudo antes do `commercial_go_live_at` é
# `PRE_LAUNCH_NON_BILLABLE`, salvo decisão explícita do Founder. E a §22.3
# proíbe o atalho — `update token_usage_logs set billed = ...` sem snapshot e
# plano de rollback. Por isso a fronteira é uma DATA lida na hora, e não uma
# marcação gravada nas linhas: ela não reescreve histórico, e desfazer é mudar
# uma variável.
#
# Ausente = ainda não houve lançamento comercial = nada é cobrável. O padrão
# protege; ligar é ato deliberado.
FRONTEIRA = "COMMERCIAL_GO_LIVE_AT"


def fronteira_comercial() -> Optional[str]:
    """A data ISO a partir da qual consumo pode ser cobrado. `None` = nenhuma."""
    valor = (os.getenv(FRONTEIRA) or "").strip()
    return valor or None


def consumo_e_cobravel(criado_em: Any) -> bool:
    """Este registro de consumo nasceu depois do lançamento comercial?

    Responde `False` quando não há fronteira, quando a data é ilegível, ou
    quando o consumo é anterior a ela. Os três casos são "não sei" — e não
    saber nunca pode virar cobrança.
    """
    fronteira = fronteira_comercial()
    if not fronteira:
        return False
    if not criado_em:
        return False
    try:
        from datetime import datetime

        def _ler(x: Any) -> "datetime":
            if isinstance(x, datetime):
                return x
            return datetime.fromisoformat(str(x).replace("Z", "+00:00"))

        nascimento, corte = _ler(criado_em), _ler(fronteira)
        if (nascimento.tzinfo is None) != (corte.tzinfo is None):
            # Comparar ingênuo com consciente levanta TypeError. Cair no
            # `except` já daria o resultado certo, mas por acidente.
            from datetime import timezone as _tz
            if nascimento.tzinfo is None:
                nascimento = nascimento.replace(tzinfo=_tz.utc)
            else:
                corte = corte.replace(tzinfo=_tz.utc)
        return nascimento >= corte
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Fronteira] data ilegível (%s) — tratando como "
                       "pré-lançamento", type(exc).__name__)
        return False


class PorteiraDeCobranca:
    """Decide se uma ação pode seguir, e diz por quê.

    A resposta é sempre um par: `(pode, motivo)`. Nunca só um booleano — um
    "não" sem motivo é o que faz o corretor achar que o sistema quebrou.
    """

    def __init__(self, supabase_client: Any = None):
        # A porteira busca o PRÓPRIO cliente síncrono quando ninguém passa um.
        #
        # Não é conveniência: os cinco pontos de chamada têm contextos
        # diferentes — dois recebem um cliente ASSÍNCRONO por injeção, um roda
        # em background sem cliente nenhum, e outro é um helper de módulo.
        # Pedir o cliente ao chamador significava, na prática, receber a coisa
        # errada em três dos cinco: `.execute()` num cliente async devolve uma
        # corrotina, e `bool(corrotina)` é sempre verdadeiro — a checagem de
        # suspensão passaria a mentir sem levantar erro.
        self.raw = supabase_client or self._cliente_padrao()
        self.db = getattr(self.raw, "client", self.raw) if self.raw else None

    @staticmethod
    def _cliente_padrao() -> Any:
        try:
            from ..core.database import get_supabase_client

            return get_supabase_client()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Porteira] sem cliente de banco: %s", type(exc).__name__)
            return None

    def pode_consumir(self, company_id: str, *,
                      custo_estimado: float = 0.01) -> tuple[bool, str]:
        # Suspensão vem PRIMEIRO e vale sempre. É decisão humana registrada,
        # não consequência de saldo — e desligar a cobrança não pode ressuscitar
        # o acesso de quem foi suspenso deliberadamente.
        if self._suspensa(company_id):
            return False, ("Esta corretora está suspensa. Fale com a "
                           "plataforma para reativar.")

        if not cobranca_ligada():
            return True, "cobrança desligada nesta instalação"

        try:
            # O import mora DENTRO do try de propósito. Ele já esteve fora, e o
            # teste mostrou o que isso custa: `ModuleNotFoundError` não é
            # `Exception` que alguém previu no meio de uma rota — ela sobe e
            # derruba a requisição inteira. Não conseguir CARREGAR o serviço de
            # cobrança é a mesma categoria de falha que não conseguir LER o
            # saldo: falta de informação, não prova de inadimplência.
            from decimal import Decimal

            from .billing_service import get_billing_service

            ok = get_billing_service().has_sufficient_balance(
                company_id, Decimal(str(custo_estimado)))
        except Exception as exc:  # noqa: BLE001
            # Falha ao LER o saldo não é prova de saldo insuficiente. Barrar
            # aqui transformaria um erro de banco em corretora sem serviço —
            # e o corretor não tem como saber a diferença.
            logger.error("[Porteira] leitura de saldo falhou (%s) — liberando",
                         type(exc).__name__)
            return True, "não foi possível conferir o saldo agora"

        if ok:
            return True, "saldo suficiente"
        return False, ("Os créditos desta corretora acabaram. Recarregue para "
                       "continuar usando.")

    def _suspensa(self, company_id: str) -> bool:
        if not self.db:
            return False
        try:
            r = (self.db.table("companies").select("status")
                 .eq("id", str(company_id)).limit(1).execute())
            linha = (r.data or [None])[0]
            return bool(linha) and str(linha.get("status")) == "suspended"
        except Exception as exc:  # noqa: BLE001
            # Mesma lógica: não conseguir ler não é prova de suspensão.
            logger.warning("[Porteira] status da empresa: %s", type(exc).__name__)
            return False


def pode_consumir(company_id: str, supabase_client: Any = None, *,
                  custo_estimado: float = 0.01) -> tuple[bool, str]:
    """Atalho para quem só precisa da resposta."""
    return PorteiraDeCobranca(supabase_client).pode_consumir(
        company_id, custo_estimado=custo_estimado)
