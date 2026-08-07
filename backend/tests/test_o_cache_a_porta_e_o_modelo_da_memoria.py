"""Três consertos que custavam dinheiro ou abriam a porta para o lado errado.

1. A HORA DENTRO DO BLOCO CACHEADO
==================================
O cache da Anthropic casa por prefixo EXATO. O `static_prompt` — o único bloco
que recebe `cache_control: ephemeral` — trazia a hora com minuto dentro:

    Hoje é Sexta-feira, 07/08/2026 21:43 (horário de Brasília).

O bloco mudava a cada 60 segundos; o TTL do cache é de 5 minutos. Pagava-se o
prêmio de ESCRITA (~1,25×) em quase toda chamada e quase nunca se colhia a
LEITURA (~0,1×).

📊 07/08/2026, `token_usage_logs`, 30 dias, claude-sonnet-5:
**104 de 4.509 chamadas (2,3%)** tiveram `cache_read_tokens > 0`.

A DATA fica no bloco estável (muda uma vez por dia). A HORA foi para o
`dynamic_context`, que nunca foi cacheado.

2. A PORTA QUE ABRIA PARA O LADO ERRADO
=======================================
`_select_base_prompt` devolvia `CORE_BASE_PROMPT` como **default**, e esse
prompt manda *"repassar o CPF do segurado, sem mascarar"*.

Para o corretor isso está **certo** — decisão do Founder, 07/08/2026: *"quando
o corretor estiver conversando com o chat principal, não é pra ter nenhum
filtro nunca. Os dados são dele."*

O defeito era a DIREÇÃO da porta: papel vazio por bug, papel escrito errado ou
um papel novo que alguém criasse amanhã herdavam os poderes do corretor. Agora
só quem é reconhecidamente o corretor recebe o prompt interno.

3. O MODELO DA MEMÓRIA
======================
`gpt-4o-mini` decidia QUAIS FATOS do usuário sobrevivem à conversa — e o que ela
guarda alimenta todo atendimento seguinte. Erro ali não parece erro: parece
agente que esqueceu. 📊 148 chamadas em 30 dias, US$ 0,0162 no total.
"""

from __future__ import annotations

import importlib.util
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PROBLEMAS: list = []


def checar(condicao: bool, o_que: str, evidencia: str = "") -> None:
    if condicao:
        print(f"  OK  {o_que}" + (f"  ({evidencia})" if evidencia else ""))
    else:
        print(f"  X   {o_que}" + (f"  ({evidencia})" if evidencia else ""))
        _PROBLEMAS.append(o_que)


def _fonte(rel: str) -> str:
    with open(os.path.join(RAIZ, rel), encoding="utf-8") as arquivo:
        return arquivo.read()


def _carregar_prompts():
    nome = "_teste_prompts"
    if nome in sys.modules:
        return sys.modules[nome]
    caminho = os.path.join(RAIZ, "backend", "app", "core", "prompts.py")
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nome] = modulo
    spec.loader.exec_module(modulo)
    return modulo


# ---------------------------------------------------------------------------
def teste_o_bloco_cacheado_nao_muda_a_cada_minuto():
    print("\n[1] O prompt cacheado é estável dentro da hora")
    P = _carregar_prompts()

    montado = P.build_composite_prompt("base", agent_role="core")
    checar("DATA DE HOJE" in montado,
           "a DATA continua no bloco estável",
           "muda uma vez por dia; o cache de 5 min não sente")

    # 🔴 O teste que importa: montar duas vezes tem de dar EXATAMENTE o mesmo
    # texto. Se a hora estivesse aqui, dois pedidos no mesmo minuto poderiam
    # divergir na virada do segundo — e o cache casa por prefixo exato.
    checar(montado == P.build_composite_prompt("base", agent_role="core"),
           "duas montagens seguidas produzem o MESMO texto")

    import re
    horas = re.findall(r"\b\d{1,2}:\d{2}\b", montado)
    checar(not horas,
           "e não há hora:minuto em lugar nenhum do bloco cacheado",
           f"achei {horas}" if horas else "era isto que quebrava o cache")

    # CONTROLE — a hora não sumiu do produto: ela mudou de lugar. Um agente que
    # não sabe que horas são não consegue dizer "amanhã".
    agora = P.data_e_hora_agora()
    checar(bool(re.search(r"\b\d{1,2}:\d{2}\b", agora)),
           "CONTROLE — a hora existe, no bloco dinâmico", agora.replace("\n", " "))

    grafo = _fonte("backend/app/agents/graph.py")
    cmd = "\n".join(l for l in grafo.split("\n") if not l.lstrip().startswith("#"))
    checar("data_e_hora_agora()" in cmd and "dynamic_context = f" in cmd,
           "e o grafo a injeta no contexto DINÂMICO",
           "é o pedaço que nunca recebeu cache_control")


def teste_a_porta_abre_para_o_lado_seguro():
    print("\n[2] Papel desconhecido NÃO herda os poderes do corretor")
    P = _carregar_prompts()

    # 📊 Os dois papéis que existem de verdade no banco (07/08/2026): 4 agentes
    # `core` e 4 `attendance`. Zero nulos.
    checar(P._select_base_prompt("core") is P.CORE_BASE_PROMPT,
           "o corretor (core) recebe o prompt interno, sem filtro nenhum",
           "decisão do Founder: os dados são dele")
    checar(P._select_base_prompt("") is P.CORE_BASE_PROMPT,
           "e o chat interno legado (sem papel) também",
           "tirar isto quebraria o produto sem consertar nada")
    checar(P._select_base_prompt("attendance") is P.ATTENDANCE_BASE_PROMPT,
           "o atendimento recebe o prompt do cliente final")
    checar(P._select_base_prompt("insured_external") is P.ATTENDANCE_BASE_PROMPT,
           "e o segurado externo também")

    # `None` NÃO é papel desconhecido: é "não existe agente nesta conversa", e
    # isso é o chat interno do corretor (`graph.py:1018` devolve None quando não
    # há `real_agent_data`). Tratá-lo como estranho tiraria o chat principal do
    # dono da corretora — o oposto da decisão do Founder.
    checar(P._select_base_prompt(None) is P.CORE_BASE_PROMPT,
           "papel None é 'sem agente' = chat interno do corretor",
           "não é desconhecido; é a ausência de agente")

    # 🔴 O CONSERTO: qualquer coisa desconhecida cai no RESTRITO.
    for estranho in ("atendimento", "ATTENDANCE ", "auxiliar", "papel_novo_2027",
                     "attendace", "externo", "cliente"):
        checar(P._select_base_prompt(estranho) is P.ATTENDANCE_BASE_PROMPT,
               f"papel desconhecido ({estranho!r}) cai no prompt RESTRITO",
               "era aqui que um erro de digitação virava CPF sem máscara")

    # CONTROLE — o prompt do corretor CONTINUA sem filtro. O conserto foi sobre
    # a porta, não sobre a regra: esvaziar o poder do corretor seria trocar um
    # defeito por outro, e contra uma decisão explícita do Founder.
    checar("sem mascarar" in P.CORE_BASE_PROMPT,
           "CONTROLE — o corretor continua recebendo o dado completo",
           "a regra não mudou; mudou para que lado a porta abre")


def teste_os_modelos_sairam_do_mais_fraco():
    print("\n[3] Memória, auxiliar e visão saíram do gpt-4o-mini")
    constantes = _fonte("backend/app/core/constants.py")
    cmd = "\n".join(l for l in constantes.split("\n") if not l.lstrip().startswith("#"))
    checar('"memory_llm_model": "claude-haiku-4-5' in cmd,
           "a MEMÓRIA saiu do modelo mais fraco",
           "📊 US$ 0,0162/mês — a melhor troca ganho/custo do sistema")

    aux = _fonte("backend/app/api/auxiliaries.py")
    cmd_aux = "\n".join(l for l in aux.split("\n") if not l.lstrip().startswith("#"))
    checar("gpt-4o-mini" not in cmd_aux,
           "o auxiliar que escreve para o CLIENTE FINAL também",
           "modelo fraco + temperatura alta é o pior para respeitar proibição")
    checar("AUXILIAR_LLM_MODEL" in cmd_aux,
           "e passou a ser configurável por ambiente",
           "trocar modelo não deveria exigir deploy")

    lc = _fonte("backend/app/services/langchain_service.py")
    cmd_lc = "\n".join(l for l in lc.split("\n") if not l.lstrip().startswith("#"))
    checar("claude-3-5-sonnet-20241022" not in cmd_lc.split("SUPPORTED_PROVIDERS")[0],
           "o fallback de visão não aponta mais para modelo RETIRADO",
           "ele devolve 404 desde 28/10/2025 — o agente ficava cego")

    # CONTROLE — os tetos de token que protegem CUSTO continuam de pé. Liberar
    # qualquer um deles aumenta a conta de IA, que é o oposto do objetivo.
    checar("DEFAULT_MAX_MESSAGES = 80" in aux,
           "CONTROLE — o teto de 80 mensagens do auxiliar continua",
           "é freio de gasto, não descuido")


def main() -> int:
    print("=" * 70)
    print("O CACHE, A PORTA E O MODELO DA MEMÓRIA")
    print("=" * 70)
    teste_o_bloco_cacheado_nao_muda_a_cada_minuto()
    teste_a_porta_abre_para_o_lado_seguro()
    teste_os_modelos_sairam_do_mais_fraco()

    print("\n" + "=" * 70)
    if _PROBLEMAS:
        print(f"{len(_PROBLEMAS)} PROBLEMA(S):")
        for p in _PROBLEMAS:
            print(f"  - {p}")
        return 1
    print("TUDO VERDE — o cache vale, a porta abre certo, a memória pensa.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
