"""Origem interna não vira sinal. Regra transversal a TODO detector.

Por que isto existe como conceito, e não como `if` num detector
---------------------------------------------------------------
O canário da SPEC-059 encontrou 18 "atendimentos parados" na Resulta que eram,
na verdade, as conversas **do próprio corretor** com o AutoBrokers. Corrigi no
detector de atendimento, e a correção estava certa — mas era pontual.

O defeito não é do detector de atendimento. É de classe:

    o sistema detectando os PRÓPRIOS artefatos como problema da corretora.

Ele volta a cada detector novo, com outra roupa:

* a conversa do corretor com o assistente virando fila de atendimento;
* o Work Run que o próprio tick criou virando "trabalho falhando";
* a peça que o briefing gerou virando "peça não entregue";
* a pesquisa que a plataforma disparou virando "sinal de mercado" (SPEC-060);
* o pedido que o Garimpo encaminhou à Factory virando "demanda do corretor".

Cada um desses é um alarme sobre o próprio reflexo. O corretor recebe um aviso
sobre algo que ele não fez, não controla e não pode resolver — e aprende que a
tela mente.

A regra
-------
**Origem interna não vira sinal, por padrão.** A exceção é explícita e tem de
ser justificada: um Work Run interno que falha É um problema operacional real
e deve aparecer. O que não pode é ele aparecer como se fosse *trabalho da
corretora* que quebrou.

Puro de propósito: é a checagem mais barata do pipeline e a que mais precisa
ser testável sem banco.
"""

from __future__ import annotations

from typing import Any, Optional

# Canais em que quem fala é o CORRETOR com a plataforma, não um segurado.
CANAIS_INTERNOS = frozenset({"web", "dashboard", "chat", "playground", "routine"})

# Prefixos de sessão que o próprio sistema cria.
PREFIXOS_DE_SESSAO_INTERNA = ("dispatch:", "routine:", "work:", "monitor:",
                              "research:", "system:", "eval:")

# `source_type` de Work Run que a própria plataforma disparou.
ORIGENS_DE_SISTEMA = frozenset({"system", "monitor", "recommendation",
                                "intelligence", "research"})

# `origin` de artefato gerado por rotina/briefing, sem pedido humano.
ORIGENS_DE_ARTEFATO_AUTOMATICO = frozenset({"routine", "monitor", "system"})

# Quem disparou a pesquisa. Pesquisa da plataforma não é sinal de mercado
# da corretora — SPEC-060 §28.2.
ORIGENS_DE_PESQUISA_INTERNA = frozenset({"platform", "system", "monitor",
                                         "warmup", "eval"})


def conversa_e_interna(conversa: dict) -> bool:
    """Conversa do corretor com o AutoBrokers, ou espelho de sistema."""
    sessao = str(conversa.get("session_id") or "")
    if any(sessao.startswith(p) for p in PREFIXOS_DE_SESSAO_INTERNA):
        return True
    return str(conversa.get("channel") or "").lower() in CANAIS_INTERNOS


def work_run_e_interno(run: dict) -> bool:
    """Work Run que a própria plataforma criou (tick, monitor, recomendação)."""
    return str(run.get("source_type") or "").lower() in ORIGENS_DE_SISTEMA


def artefato_e_automatico(artefato: dict) -> bool:
    """Peça gerada por rotina ou monitor, sem ninguém ter pedido."""
    return str(artefato.get("origin") or "").lower() in ORIGENS_DE_ARTEFATO_AUTOMATICO


def pesquisa_e_interna(pedido: dict) -> bool:
    """Pesquisa disparada pela plataforma — SPEC-060 §28.2."""
    origem = str(pedido.get("requested_by_kind")
                 or pedido.get("source")
                 or pedido.get("origin") or "").lower()
    return origem in ORIGENS_DE_PESQUISA_INTERNA


def empresa_e_tecnica(empresa: dict) -> bool:
    """Sandbox técnico da plataforma. Nunca recebe proatividade."""
    return bool(empresa.get("is_technical"))


# ---------------------------------------------------------------------------
# Filtro genérico
# ---------------------------------------------------------------------------

_CLASSIFICADORES = {
    "conversation": conversa_e_interna,
    "work_run": work_run_e_interno,
    "artifact": artefato_e_automatico,
    "research_request": pesquisa_e_interna,
    "company": empresa_e_tecnica,
}


def e_interno(tipo: str, registro: dict) -> bool:
    """`True` se este registro é artefato da própria plataforma.

    Tipo desconhecido devolve `False` — na dúvida, o item PASSA. Filtrar por
    engano esconde um problema real do corretor; deixar passar produz, no
    pior caso, um aviso a mais que o dedupe e o cooldown já contêm.
    """
    fn = _CLASSIFICADORES.get(tipo)
    return bool(fn(registro)) if fn else False


def filtrar_externos(tipo: str, registros: list[dict], *,
                     manter: Optional[Any] = None) -> list[dict]:
    """Remove o que é da própria casa. `manter` é a exceção explícita.

    `manter` recebe o registro e devolve `True` para preservá-lo mesmo sendo
    interno. É por onde passa o caso legítimo — por exemplo, uma conversa do
    dashboard em que alguém **pediu atendimento humano** e ninguém veio: a
    origem é interna, mas o problema é real e da corretora.

    A exceção existe como parâmetro, e não como lista global, porque ela é
    sempre específica de um detector. Uma exceção global viraria, com o tempo,
    a porta por onde o filtro deixa de valer.
    """
    saida = []
    for r in registros or []:
        if not e_interno(tipo, r):
            saida.append(r)
        elif manter is not None and manter(r):
            saida.append(r)
    return saida
