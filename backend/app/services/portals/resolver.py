# -*- coding: utf-8 -*-
"""Resolução de portal e de conexão — SPEC-075 Blocos B (§10.3) e F.

Responde duas perguntas, e só elas:

    1. que PORTAL atende esta operação para esta corretora?
    2. que CONTA desta corretora entra nesse portal?

Por que a conexão NÃO mora no Auxiliar (SPEC-075 §14.1)
=======================================================
📊 A corretora conecta a Allianz uma vez. Se a credencial morasse no Auxiliar,
instalar um segundo Auxiliar que usa Allianz pediria a senha de novo — e o
corretor teria duas senhas para trocar quando a Allianz forçasse a troca. Uma
delas ficaria velha, e o Auxiliar dela pararia sem ninguém entender por quê.

A conexão é da CORRETORA. Auxiliar, Agent e Rotina autorizados a usar reusam a
mesma — é o que a `CAMADAS-DE-CONEXAO.md` chama de "quem paga, quem conecta,
quem usa".

Multi-account é P0 de isolamento (§14.4)
=========================================
🔴 Uma corretora pode ter duas contas no mesmo portal — matriz e filial, ou dois
CNPJs. Escolher "a primeira que aparecer" faria a carteira da filial ser lida
como se fosse a da matriz. Quando há mais de uma e ninguém disse qual, este
módulo **recusa**. Recusar custa uma pergunta; adivinhar custa dado trocado
entre carteiras.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Portais que NÃO exigem conta da corretora.
#
# 📊 Medido: o portal de vidros (Maxpar/Autoglass) é PÚBLICO — a migration
# `20260804_01_spec065_o_portal_de_vidros_e_publico.sql` zerou
# `requires_connection` das capabilities de assistência exatamente por isso, e
# `portal_tool` cria o job sem `account_id`.
#
# A lista é FECHADA. Portal novo nasce exigindo conta; quem não exige tem de
# ser escrito aqui, com a medição que provou.
# --------------------------------------------------------------------------
PORTAIS_PUBLICOS: Tuple[str, ...] = ("vidros_lanternas",)


def portal_e_publico(portal_key: Any) -> bool:
    return str(portal_key or "").strip() in PORTAIS_PUBLICOS


# --------------------------------------------------------------------------
# Resultado da resolução de conta
# --------------------------------------------------------------------------
CONTA_OK = "ok"
CONTA_NAO_PRECISA = "nao_precisa"        # portal público
CONTA_AUSENTE = "ausente"                # corretora não conectou
CONTA_AMBIGUA = "ambigua"                # >1 conta e ninguém disse qual
CONTA_DE_OUTRA_CORRETORA = "de_outra_corretora"  # 🔴 P0
CONTA_INDISPONIVEL = "indisponivel"      # leitura falhou


@dataclass
class ResolucaoDeConta:
    estado: str
    account_id: Optional[str] = None
    account_label: str = ""
    motivo: str = ""

    @property
    def pode_executar(self) -> bool:
        return self.estado in (CONTA_OK, CONTA_NAO_PRECISA)


def resolver_portal(operation_key: str,
                    *,
                    insurer_key: Optional[str] = None,
                    portal_key_hint: Optional[str] = None,
                    hint_confiavel: bool = False) -> Tuple[Optional[str], str]:
    """`(portal_key, motivo)` — que portal atende esta operação.

    Os três casos da SPEC-075 §10.3, na ordem em que devem ser tentados:

    **C — hint de chamador server-side.** `billing_collection` deriva o
    `portal_key` do próprio registro, então o valor nasceu de código. Mesmo
    assim é CONFERIDO contra o registro: hint que não implementa a operação é
    recusado, não obedecido.

    **B — uma seguradora, um portal de corretor.** `insurer_key=mapfre` +
    `billing.overdue.list` → o portal da MAPFRE. A convenção `<insurer>_corretor`
    é conferida contra o registro, nunca montada e usada às cegas.

    **A — portal compartilhado.** Maxpar atende Porto, Azul e Itaú pela mesma
    tela; a seguradora vai como DADO DE NEGÓCIO. Quando só um portal implementa
    a operação, ele é a resposta e não há o que escolher.

    Ambiguidade real — vários portais e nenhum critério — devolve `None`. O
    Gateway transforma isso em `not_supported`, e não em "escolhi um".
    """
    from portal_worker.journeys import portais_com_operacao, suporta

    op = str(operation_key or "").strip()
    candidatos = portais_com_operacao(op)
    if not candidatos:
        return None, f"nenhum portal implementa a operacao `{op}`"

    # -- Caso C: hint de código ------------------------------------------
    hint = str(portal_key_hint or "").strip()
    if hint:
        if not hint_confiavel:
            return None, ("portal_key_hint so e aceito de chamador server-side "
                          "confiavel; de texto de modelo, nunca")
        if hint not in candidatos:
            return None, (f"o hint `{hint}` nao implementa `{op}` "
                          f"(implementam: {', '.join(candidatos)})")
        return hint, "hint de chamador confiavel, conferido contra o registro"

    # -- Caso B: uma seguradora, um portal --------------------------------
    ins = str(insurer_key or "").strip().lower()
    if ins:
        por_convencao = f"{ins}_corretor"
        if por_convencao in candidatos:
            return por_convencao, f"portal de corretor da seguradora `{ins}`"
        # A seguradora pode ser atendida por portal compartilhado; segue.

    # -- Caso A: um único portal implementa --------------------------------
    if len(candidatos) == 1:
        return candidatos[0], "unico portal que implementa a operacao"

    return None, (f"`{op}` e implementada por {len(candidatos)} portais "
                  f"({', '.join(candidatos)}) e nada no pedido diz qual")


def resolver_conta(supabase: Any,
                   *,
                   company_id: str,
                   portal_key: str,
                   account_id_hint: Optional[str] = None,
                   hint_confiavel: bool = False,
                   account_label: Optional[str] = None) -> ResolucaoDeConta:
    """Que conta desta corretora entra neste portal.

    🔴 Toda leitura filtra por `company_id` — CLAUDE.md §7. O backend usa
    service role: RLS sem filtro no código não protege nada.

    Falha de leitura é **fail-closed**. Um Supabase fora do ar não pode virar
    "siga sem conta" — seguir sem conta num portal que exige conta é entrar com
    a credencial de outra pessoa ou não entrar; nenhuma das duas é aceitável em
    silêncio.
    """
    pk = str(portal_key or "").strip()
    cid = str(company_id or "").strip()

    if portal_e_publico(pk):
        return ResolucaoDeConta(CONTA_NAO_PRECISA, motivo=f"`{pk}` e portal publico")

    if not cid:
        return ResolucaoDeConta(CONTA_INDISPONIVEL, motivo="company_id vazio")

    try:
        q = (supabase.table("portal_accounts")
             .select("id, account_label, portal_key, company_id, health")
             .eq("company_id", cid)
             .eq("portal_key", pk))
        linhas = list((q.execute().data) or [])
    except Exception as e:  # noqa: BLE001
        logger.warning("[portais] leitura de portal_accounts indisponivel: %s",
                       type(e).__name__)
        return ResolucaoDeConta(
            CONTA_INDISPONIVEL,
            motivo="nao consegui conferir a conexao da corretora; nao executo as cegas")

    if not linhas:
        return ResolucaoDeConta(
            CONTA_AUSENTE,
            motivo=f"a corretora nao conectou `{pk}`")

    # -- hint explícito ----------------------------------------------------
    hint = str(account_id_hint or "").strip()
    if hint:
        if not hint_confiavel:
            return ResolucaoDeConta(
                CONTA_INDISPONIVEL,
                motivo="account_id_hint so vale de chamador server-side confiavel")
        for l in linhas:
            if str(l.get("id")) == hint:
                return ResolucaoDeConta(CONTA_OK, account_id=hint,
                                        account_label=str(l.get("account_label") or ""),
                                        motivo="conta indicada pelo chamador confiavel")
        # 🔴 O hint existe mas não está entre as contas DESTA corretora. Isso é
        # exatamente a forma de um cross-tenant: um id válido, de outra empresa.
        return ResolucaoDeConta(
            CONTA_DE_OUTRA_CORRETORA,
            motivo="a conta indicada nao pertence a esta corretora neste portal")

    # -- rótulo explícito --------------------------------------------------
    rotulo = str(account_label or "").strip()
    if rotulo:
        iguais = [l for l in linhas
                  if str(l.get("account_label") or "").strip() == rotulo]
        if len(iguais) == 1:
            return ResolucaoDeConta(CONTA_OK, account_id=str(iguais[0].get("id")),
                                    account_label=rotulo,
                                    motivo="conta escolhida pelo rotulo")
        if not iguais:
            return ResolucaoDeConta(CONTA_AUSENTE,
                                    motivo=f"nao ha conta com o rotulo `{rotulo}`")
        return ResolucaoDeConta(CONTA_AMBIGUA,
                                motivo=f"ha {len(iguais)} contas com o rotulo `{rotulo}`")

    # -- sem critério ------------------------------------------------------
    if len(linhas) == 1:
        l = linhas[0]
        return ResolucaoDeConta(CONTA_OK, account_id=str(l.get("id")),
                                account_label=str(l.get("account_label") or ""),
                                motivo="a corretora tem uma unica conta neste portal")

    rotulos = sorted(str(l.get("account_label") or "?") for l in linhas)
    return ResolucaoDeConta(
        CONTA_AMBIGUA,
        motivo=(f"a corretora tem {len(linhas)} contas em `{pk}` ({', '.join(rotulos)}) "
                "e ninguem disse qual usar"))
