# -*- coding: utf-8 -*-
"""De quem é o dado que acabei de ler? — SPEC-073, gate de identidade de corretora.

O incidente que originou tudo, já medido
========================================
📊 `mapfre_corretor.py:222-223`:

    "um brokerId errado traz a carteira inteira da outra empresa — medido:
     59 parcelas de uma, 8 da outra, zero clientes em comum."

A MAPFRE ganhou duas trancas por causa disso: escolher o broker por
correspondência única (`escolher_broker`) e conferir o broker de **cada linha
lida** (`conferir_broker_dos_itens`). Funciona, tem teste com duas carteiras
disjuntas, e é o único guarda cross-tenant provado do produto.

📊 O que a auditoria de 16/08/2026 encontrou nas outras journeys:

    Yelum ...... `_api(..., corpo={"brokerlist": []})` — busca SEM filtro de
                 corretora. Lê `BrokerName` de cada linha (`:227`) e DESCARTA o
                 valor. `grep account_label yelum_corretor.py` → zero.
    Tokio ...... captura `nomeParceiroNegocioPrimario` em
                 `evidence["tokio_usuario"]` e nunca compara.
    Zurich ..... compara, mas só quando o rótulo NÃO é `principal`/`default` —
                 e `principal` é exatamente o default que o dashboard grava
                 (`portal-credentials/route.ts:67`). Toda conta criada pela tela
                 nasce com a revalidação desligada.
    HDI/Allianz  nenhuma menção a `account_label`.

A generalização que faltava
===========================
A tranca da MAPFRE parecia depender de saber **qual** corretora esperar. Isso a
tornava inaplicável onde o `account_label` é genérico — e é genérico em 14 das
16 contas medidas.

Mas a pergunta que realmente protege é outra:

> **A leitura inteira veio de UMA corretora só?**

Duas corretoras distintas na mesma resposta é vazamento cross-tenant qualquer
que seja o rótulo da conta, e não é preciso saber o nome certo para recusar. É
essa a regra que alcança o `brokerlist: []` da Yelum mesmo com
`account_label='principal'`.

Então são duas perguntas, e as duas valem:

    1. a leitura é internamente consistente?   (sempre exigida)
    2. ela bate com a corretora esperada?      (quando o rótulo diz um nome)

🔴 Fail-closed nas duas. Na dúvida sobre de quem é o dado, não se grava o dado.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, Iterable, List, Sequence

# Rótulos que o produto usa como "não informado". Não nomeiam corretora nenhuma,
# então comparar contra eles seria teatro — mas a pergunta 1 continua valendo.
ROTULOS_GENERICOS = ("principal", "default", "padrao", "")


def _norm(txt: Any) -> str:
    s = unicodedata.normalize("NFKD", str(txt or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


def rotulo_e_generico(account_label: Any) -> bool:
    """`principal` não é o nome de uma corretora; é a ausência de um."""
    return _norm(account_label) in ROTULOS_GENERICOS


def _valores(itens: Iterable[Any], campo: str) -> List[str]:
    out: List[str] = []
    for i in itens or []:
        if isinstance(i, dict):
            v = str(i.get(campo) or "").strip()
            if v:
                out.append(v)
    return out


def conferir_itens_da_corretora(itens: Sequence[Any],
                                *,
                                campo: str,
                                esperado: Any = "",
                                portal: str = "") -> str:
    """A tranca portátil. Devolve `""` quando está tudo certo, ou o motivo da recusa.

    Generaliza `conferir_broker_dos_itens` da MAPFRE para qualquer journey cujas
    linhas declarem a corretora dona — que é o caso de Yelum (`BrokerName`),
    Tokio (`nomeParceiroNegocioPrimario`) e Zurich.

    **Pergunta 1 — consistência interna, sempre exigida.** Duas corretoras
    distintas na mesma leitura é vazamento, mesmo sem saber qual era a certa.

    **Pergunta 2 — corresponde ao esperado.** Só quando o `account_label` nomeia
    alguém de verdade.

    Uma leitura sem o campo preenchido NÃO é tratada como erro: nem todo portal
    devolve o dono em toda linha, e recusar por ausência transformaria este
    guarda no motivo de a cobrança parar. O que ele recusa é **divergência**,
    não silêncio — e o silêncio fica registrado pelo chamador.
    """
    vistos = sorted({_norm(v) for v in _valores(itens, campo)})
    vistos = [v for v in vistos if v]

    if not vistos:
        return ""  # o portal não declarou dono nesta leitura

    if len(vistos) > 1:
        crus = sorted({v for v in _valores(itens, campo)})
        return (f"a leitura trouxe linhas de {len(vistos)} corretoras diferentes "
                f"({crus}) — um login que enxerga mais de uma empresa nao pode "
                f"gravar as duas juntas{f' [{portal}]' if portal else ''}. "
                "NAO gravo nada desta leitura.")

    if not rotulo_e_generico(esperado):
        alvo = _norm(esperado)
        unico = vistos[0]
        # Nome de corretora vem com sufixo variável ("LTDA", "S/A", corte de
        # coluna). Continência nos dois sentidos, nunca igualdade literal —
        # 📊 o `account_label` da MAPFRE no banco vem TRUNCADO em 30 chars
        # ("AUTO FLEET R CORRETORA DE SEGU"), então exigir igualdade reprovaria
        # a conta correta.
        if not (alvo == unico or alvo in unico or unico in alvo):
            return (f"a leitura veio da corretora '{_valores(itens, campo)[0]}' e "
                    f"esta conta e '{esperado}' — NAO gravo dado de outra empresa.")

    return ""


def conferir_corretora_da_sessao(lida: Any, esperada: Any, *, portal: str = "") -> str:
    """Depois do login: a sessão é da corretora que eu esperava?

    Corrige o fail-open do Zurich por dois lados:

        1. `lida` vazia deixava de conferir e devolvia sucesso. Falha de leitura
           virava permissão — e é justamente quando não se sabe que não se deve
           seguir.
        2. rótulo `principal` pulava a checagem. Continua sendo impossível
           comparar contra um rótulo que não nomeia ninguém, mas isso agora é
           registrado como não-verificado, não como verificado-e-ok.

    Devolve `""` (segue), ou o motivo da recusa.
    """
    if rotulo_e_generico(esperada):
        # Nada a comparar. Quem chama registra `identidade_verificada=False`.
        return ""
    alvo, atual = _norm(esperada), _norm(lida)
    if not atual:
        return (f"nao consegui ler de qual corretora e esta sessao, e a conta diz "
                f"'{esperada}' — sem saber de quem e o dado, nao sigo"
                f"{f' [{portal}]' if portal else ''}")
    if alvo == atual or alvo in atual or atual in alvo:
        return ""
    return (f"a sessao esta na corretora '{lida}' e a conta e '{esperada}' — "
            f"parar aqui e o certo{f' [{portal}]' if portal else ''}")


# --------------------------------------------------------------------------
# Os estados de identidade — SPEC-073, correção do Founder de 16/08/2026
#
# 🔴 A primeira versão deste módulo gravava `verificado: True` sempre que a
# leitura passava. Com `account_label='principal'` — que é o caso de 14 das 16
# contas — isso significava marcar como verificada uma identidade que ninguém
# conferiu, só porque apareceu **uma** corretora.
#
# O Founder cravou a distinção, e ela é exata:
#
#     "o portal retornou somente uma corretora" prova UNICIDADE,
#     não necessariamente IDENTIDADE.
#
# Unicidade responde *"eu misturei dados de duas empresas?"* — e é a pergunta
# que impede o vazamento. Identidade responde *"esta é a empresa certa?"* — e é
# a que impede trabalhar na empresa errada com dados coerentes. São defeitos
# diferentes, e chamar o primeiro de segundo é o tipo de mentira que só aparece
# no dia do incidente.
# --------------------------------------------------------------------------
VERIFICADO = "verified"                              # rótulo nomeado casou
UNICO_NAO_VERIFICADO = "unique_context_unverified"   # um contexto, nada a comparar
ILEGIVEL = "unreadable"                              # não consegui observar
BLOQUEADO = "blocked"                                # divergiu ou veio mais de um


def marca_de_identidade(*, campo: str, itens: Sequence[Any],
                        esperado: Any, bloqueado: bool) -> Dict[str, Any]:
    """O bloco de evidência que diz o que foi conferido — e o que NÃO foi.

    Sem isso, "não vazou", "não conferi" e "conferi e bate" ficam
    indistinguíveis no artefato. Um guarda que não deixa rastro não é auditável
    depois do incidente; um que deixa rastro **otimista demais** é pior, porque
    dá a alguém a confiança para pular a próxima checagem.
    """
    vistos = sorted({v for v in _valores(itens, campo)})
    nomeado = not rotulo_e_generico(esperado)

    if bloqueado:
        estado = BLOQUEADO
    elif not vistos:
        estado = ILEGIVEL
    elif nomeado:
        estado = VERIFICADO
    else:
        estado = UNICO_NAO_VERIFICADO

    return {
        "campo": campo,
        "estado": estado,
        "contextos_na_leitura": len(vistos),
        # O que o portal DECLAROU ser. Só entra quando há exatamente um: com
        # dois, o valor já está na mensagem de bloqueio, e repetir aqui só
        # duplicaria a exposição.
        "contexto_observado": vistos[0] if len(vistos) == 1 else "",
        "esperado_nomeado": nomeado,
        # `verificado` continua existindo por compatibilidade de leitura, mas
        # agora só é True quando a identidade foi PROVADA de verdade.
        "verificado": estado == VERIFICADO,
    }


def marca_de_identidade_da_sessao(*, lida: Any, esperado: Any,
                                  bloqueado: bool) -> Dict[str, Any]:
    """A mesma honestidade, para o gate pós-login (Tokio/Zurich)."""
    nomeado = not rotulo_e_generico(esperado)
    if bloqueado:
        estado = BLOQUEADO
    elif not str(lida or "").strip():
        estado = ILEGIVEL
    elif nomeado:
        estado = VERIFICADO
    else:
        estado = UNICO_NAO_VERIFICADO
    return {
        "estado": estado,
        "contexto_observado": str(lida or "")[:120],
        "esperado_nomeado": nomeado,
        "verificado": estado == VERIFICADO,
    }
