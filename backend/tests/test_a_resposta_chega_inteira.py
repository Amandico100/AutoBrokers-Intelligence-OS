# -*- coding: utf-8 -*-
"""A RESPOSTA CHEGA INTEIRA -- o guarda do corte de saida (P-PILOTO, 09/09/2026).

O DEFEITO QUE ESTE ARQUIVO GUARDA
------------------------------------------------------------------------------
> "A resposta para na metade com muita frequencia; o corretor escreve
> 'continue' e o agente continua de onde parou." -- Founder, 09/09/2026,
> chat do PAINEL da Resulta Seguros.

📊 MEDIDO (09/09/2026, banco de producao, SELECT):

```
agents.llm_max_tokens do agente core da Resulta (20845996)   1200
token_usage_logs desde 08/09: chamadas do chat                 95
   dessas, com output_tokens == 1200 EXATO                     10   (11%)
messages (role=assistant, canal web, desde 01/09)              30
   dessas, terminando SEM pontuacao final (corte no meio)      10
maior resposta gravada                                      2961 ch
```

🔴 **Dez e dez.** As respostas cortadas sao exatamente as que bateram o teto de
saida gravado no agente. Nao ha teto de TEMPO no meio: uma resposta de 2392 ch
levou 107s e terminou em "?" (limpa), enquanto a de 2961 ch levou 55s e parou
em "...te entregar direto no What". ⛔ Logo: **nao e rede, e token.**

O ELO que este guarda mede
------------------------------------------------------------------------------
```
o corretor recebe a resposta INTEIRA
  PORQUE o teto de saida de quem CONVERSA tem piso (`piso_de_saida`)
  E PORQUE, se ainda assim o modelo parar por teto, o SERVIDOR emenda
     (`stream_agent_eventos` refaz a volta pedindo "continue de onde parou",
      no MESMO grafo e no MESMO thread_id -- nao ha motor novo)
  E PORQUE o motivo da parada fica GRAVADO no `payload.turn` da mensagem
     (o proximo diagnostico e leitura, nao inferencia -- CLAUDE.md §12.1)
  E PORQUE o stream nao morre calado enquanto o modelo pensa (batimento <=15s)
```

⚠️ **Cada bloco carrega um PAR** (protocolo §5): mesma superficie, veredito
oposto. O CONTROLE do [E1] e o [E2] -- resposta curta que NAO pode disparar
emenda nenhuma. Sem ele, "emendou" nao prova nada: um codigo que emendasse
sempre passaria no [E1] e cobraria 4x cada turno.

🔴 O que este arquivo NAO faz: nao mede o motor de terceiro. `astream_events`
e sempre DUBLADO; o que se exercita e o PROJETOR de producao
(`app.agents.graph.stream_agent_eventos`), a FABRICA de producao
(`app.factories.llm_factory.piso_de_saida`) e o ENDPOINT de producao
(`app.api.chat.router`). CLAUDE.md §9.4: o teste chama o MOTOR.

⛔ REUSO, NAO COPIA (§5): o arreio do endpoint (banco dublado, troca de
modulos, leitura de SSE) e o do `test_o_chat_fala_tipado.py` -- este arquivo o
IMPORTA. Duas copias do arreio seriam duas respostas para "como se sobe o
router de teste".

AS MUTACOES -- por copia, e so com `--mutar`
------------------------------------------------------------------------------
    1. app/agents/graph.py     MOTIVOS_DE_CORTE vazio        -> [E1] [E3] [E7]
    2. app/factories/llm_factory.py  piso devolve o gravado  -> [E4]
    3. app/api/chat.py         o desfecho nao entra no turno -> [E6]
    4. app/api/chat.py         batimento de 15s -> 600s      -> [E5]

Um bloco que NAO fica vermelho sob a sua mutacao e um carimbo, nao um guarda
(CLAUDE.md §9.3): a saida acusa isso com "MUTACAO NAO PEGOU".

SEGURANCA
------------------------------------------------------------------------------
```
· nenhuma leitura e nenhuma escrita de banco -- os dubles sao memoria pura
· nenhuma chamada de rede -- nenhum provedor de LLM e tocado
· NENHUM dado real: os textos sao sentinelas obvias ("PARTE-UM", "Corretora
  Alfa"); nenhum nome, CPF, apolice, telefone ou token aparece aqui
```

Rodar:  PYTHONIOENCODING=utf-8 python tests/test_a_resposta_chega_inteira.py
        (a partir de `backend/`)   `--mutar` acrescenta as mutacoes por copia.
"""
from __future__ import annotations

import asyncio
import importlib
import io
import os
import shutil
import sys
import types
import uuid

import httpx

# ⛔ O reembrulho de UTF-8 so vale para a execucao DIRETA. 📊 Feito no import,
# ele troca o `sys.stdout` que o pytest instalou para capturar a saida — e a
# COLETA do pytest morre com "I/O operation on closed file", derrubando este
# arquivo e os vizinhos sem nenhum defeito de produto no meio.
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

OK = 0
FAIL = 0
FALHAS: list = []


def _p(txt=""):
    print(txt, flush=True)


def certo(condicao, rotulo, detalhe=""):
    global OK, FAIL
    if condicao:
        OK += 1
        _p("  OK   %s" % rotulo)
    else:
        FAIL += 1
        FALHAS.append(rotulo)
        _p("  FALHA %s" % rotulo)
        if detalhe:
            _p("        %s" % detalhe)
    return bool(condicao)


# ===========================================================================
# O GRAFO DUBLADO -- `astream_events` de mentira, uma lista de eventos POR VOLTA
#
# 🔴 A emenda so pode ser medida por um grafo que responde DIFERENTE na segunda
# chamada. Um duble que repete a mesma lista provaria o contrario do que se
# quer: a resposta sairia duplicada e o teste passaria assim mesmo.
# ===========================================================================
class GrafoPorVoltas:
    def __init__(self, voltas):
        self._voltas = list(voltas)
        self.chamadas = 0
        self.estados = []

    async def astream_events(self, estado, config=None, **k):
        self.estados.append(estado)
        i = min(self.chamadas, len(self._voltas) - 1)
        self.chamadas += 1
        for e in self._voltas[i]:
            yield e


def ev_bruto(tipo, **campos):
    return {"event": tipo, "name": campos.get("name", ""),
            "data": campos.get("data", {}),
            "metadata": {"langgraph_node": campos.get("node", "agent")}}


def chunk_de_texto(texto, meta=None):
    """Um `AIMessageChunk` de mentira -- so o que o projetor le."""
    c = types.SimpleNamespace(content=texto, tool_call_chunks=[])
    if meta is not None:
        c.response_metadata = meta
    return c


def volta(texto, motivo=None, uso=None):
    """Uma volta do modelo: um delta e, opcionalmente, o motivo no chunk final."""
    eventos = [ev_bruto("on_chat_model_stream",
                        data={"chunk": chunk_de_texto(texto)}, node="agent")]
    if motivo is not None or uso is not None:
        fim = chunk_de_texto("", {"finish_reason": motivo} if motivo else {})
        if uso is not None:
            fim.usage_metadata = uso
        eventos.append(ev_bruto("on_chat_model_stream",
                                data={"chunk": fim}, node="agent"))
    return eventos


def volta_anthropic(texto, stop_reason):
    """O mesmo, no DIALETO da Anthropic -- `stop_reason`, nao `finish_reason`."""
    fim = chunk_de_texto("", {"stop_reason": stop_reason})
    return [ev_bruto("on_chat_model_stream", data={"chunk": chunk_de_texto(texto)}, node="agent"),
            ev_bruto("on_chat_model_stream", data={"chunk": fim}, node="agent")]


def coletar(gerador_async):
    saida = []

    async def _rodar():
        async for x in gerador_async:
            saida.append(x)
    asyncio.run(_rodar())
    return saida


def projetar(grafo):
    """Chama o PROJETOR DE PRODUCAO sobre o grafo dublado.

    ⛔ `user_message=None` e `company_config=None`: e a porta que o proprio
    `stream_agent_eventos` abre para exercitar o projetor sem tocar no banco.
    """
    graph_mod = importlib.import_module("app.agents.graph")
    return coletar(graph_mod.stream_agent_eventos(
        grafo, company_id="co-teste", session_id="ses-teste"))


def texto_de(itens):
    return "".join(i.get("text") or "" for i in itens if i.get("kind") == "delta")


def final_de(itens):
    finais = [i for i in itens if i.get("kind") == "final"]
    return finais[-1] if finais else None


# ===========================================================================
# BLOCO E1/E2/E3/E7 -- A EMENDA (o projetor de producao)
# ===========================================================================
def bloco_emenda():
    _p("\n[EMENDA] a resposta cortada e emendada pelo SERVIDOR -- e so ela")

    try:
        importlib.import_module("app.agents.graph")
    except BaseException as erro:  # noqa: BLE001
        certo(False, "[E1..E3] app.agents.graph importa", "%s: %s" % (type(erro).__name__, erro))
        return

    # ---- [E1] estourou o teto -> emenda, e o corretor recebe INTEIRO -------
    g = GrafoPorVoltas([
        volta("PARTE-UM ate o corte no meio da pala", motivo="length"),
        volta("vra e o resto que faltava.", motivo="stop"),
    ])
    itens = projetar(g)
    inteiro = texto_de(itens)
    certo(inteiro == "PARTE-UM ate o corte no meio da palavra e o resto que faltava.",
          "[E1] resposta cortada por teto de saida chega INTEIRA ao consumidor",
          "recebido: %r" % inteiro)
    certo(g.chamadas == 2,
          "[E1] o servidor deu exatamente 1 volta de emenda",
          "chamadas ao grafo: %d" % g.chamadas)
    fim = final_de(itens)
    certo(fim is not None and fim.get("continuations") == 1,
          "[E1] o turno declara 1 continuacao",
          "final: %r" % (fim,))
    # a emenda pede continuacao, e leva a CAUDA do que ja saiu
    pedido = ""
    if len(g.estados) > 1:
        msgs = (g.estados[1] or {}).get("messages") or []
        pedido = getattr(msgs[-1], "content", "") if msgs else ""
    certo("cortada" in pedido.lower() and "pala" in pedido,
          "[E1] o pedido de emenda ancora na cauda do que ja foi entregue",
          "pedido: %r" % pedido[:160])

    # ---- [E2] CONTROLE: resposta curta NAO emenda --------------------------
    # 🔴 Sem este par, [E1] passaria com um codigo que emendasse SEMPRE -- e
    # cada turno do corretor custaria 4x o que custa hoje.
    g2 = GrafoPorVoltas([
        volta("Resposta curta e completa.", motivo="stop"),
        volta("ISTO NUNCA PODE APARECER", motivo="stop"),
    ])
    itens2 = projetar(g2)
    certo(g2.chamadas == 1,
          "[E2] CONTROLE: resposta que terminou por conta propria NAO emenda",
          "chamadas ao grafo: %d" % g2.chamadas)
    certo("NUNCA PODE APARECER" not in texto_de(itens2),
          "[E2] CONTROLE: nada da volta seguinte vaza para a resposta",
          "recebido: %r" % texto_de(itens2))
    fim2 = final_de(itens2)
    certo(fim2 is not None and fim2.get("continuations") == 0 and fim2.get("truncated") is False,
          "[E2] CONTROLE: o turno declara ZERO continuacao e nao-cortado",
          "final: %r" % (fim2,))

    # ---- [E2b] CONTROLE: provedor que nao declara motivo nenhum ------------
    g2b = GrafoPorVoltas([volta("Sem metadado nenhum."), volta("NAO PODE APARECER")])
    itens2b = projetar(g2b)
    certo(g2b.chamadas == 1 and "NAO PODE" not in texto_de(itens2b),
          "[E2b] CONTROLE: ausencia de motivo NAO e corte (nao emenda)",
          "chamadas: %d | texto: %r" % (g2b.chamadas, texto_de(itens2b)))

    # ---- [E3] o teto de voltas -- emenda nao vira laco infinito ------------
    g3 = GrafoPorVoltas([volta("mais", motivo="length")])
    itens3 = projetar(g3)
    graph_mod = importlib.import_module("app.agents.graph")
    teto = getattr(graph_mod, "VOLTAS_DE_CONTINUACAO", None)
    certo(teto is not None and g3.chamadas == teto + 1,
          "[E3] o modelo que nunca termina para no teto de voltas (%s)" % teto,
          "chamadas ao grafo: %d" % g3.chamadas)
    fim3 = final_de(itens3)
    certo(fim3 is not None and fim3.get("truncated") is True,
          "[E3] quando nem a emenda basta, o turno diz que ficou CORTADO",
          "final: %r" % (fim3,))

    # ---- [E7] DIALETO: Anthropic diz `stop_reason: max_tokens` -------------
    # 🔴 CLAUDE.md §9.4: um motivo medido num provedor e aplicado noutro e um
    # motivo sobre outra coisa. A Resulta roda `claude-sonnet-5` -- se o guarda
    # so entendesse `finish_reason`, ele ficaria verde e a corretora cortada.
    g4 = GrafoPorVoltas([
        volta_anthropic("comeco cortado", "max_tokens"),
        volta_anthropic(" e o fim", "end_turn"),
    ])
    itens4 = projetar(g4)
    certo(g4.chamadas == 2 and texto_de(itens4) == "comeco cortado e o fim",
          "[E7] `stop_reason: max_tokens` (dialeto Anthropic) tambem e corte",
          "chamadas: %d | texto: %r" % (g4.chamadas, texto_de(itens4)))
    g5 = GrafoPorVoltas([volta_anthropic("terminou sozinho", "end_turn"),
                         volta_anthropic("NAO PODE", "end_turn")])
    itens5 = projetar(g5)
    certo(g5.chamadas == 1 and "NAO PODE" not in texto_de(itens5),
          "[E7] CONTROLE: `end_turn` NAO e corte",
          "chamadas: %d" % g5.chamadas)


# ===========================================================================
# BLOCO E4 -- O PISO DE SAIDA (a fabrica de producao)
# ===========================================================================
def bloco_piso():
    _p("\n[PISO] o teto de saida de quem CONVERSA nao cabe abaixo do piso")
    try:
        fab = importlib.import_module("app.factories.llm_factory")
    except BaseException as erro:  # noqa: BLE001
        certo(False, "[E4] app.factories.llm_factory importa",
              "%s: %s" % (type(erro).__name__, erro))
        return

    piso = getattr(fab, "piso_de_saida", None)
    if piso is None:
        certo(False, "[E4] `piso_de_saida` existe na fabrica", "funcao ausente")
        return

    valor_do_piso = fab.PISO_DE_SAIDA_DA_CONVERSA
    certo(valor_do_piso >= 8192,
          "[E4] o piso cabe uma apolice item a item (>= 8192)",
          "piso: %s" % valor_do_piso)
    # 📊 1200 e o numero GRAVADO do agente core da Resulta em 09/09/2026.
    certo(piso("core", 1200) == valor_do_piso,
          "[E4] core com 1200 gravado sobe ao piso",
          "recebido: %s" % piso("core", 1200))
    certo(piso("attendance", 2000) == valor_do_piso,
          "[E4] atendimento com 2000 gravado sobe ao piso",
          "recebido: %s" % piso("attendance", 2000))
    certo(piso(None, 1200) == valor_do_piso,
          "[E4] agente sem papel (chat legado) tambem tem piso",
          "recebido: %s" % piso(None, 1200))
    # ---- CONTROLE: o piso NAO engessa e NAO vale para quem nao conversa ----
    certo(piso("core", 16000) == 16000,
          "[E4] CONTROLE: quem configurou MAIS que o piso continua mandando",
          "recebido: %s" % piso("core", 16000))
    certo(piso("auxiliary", 512) == 512,
          "[E4] CONTROLE: auxiliar (que devolve campo curto) mantem o gravado",
          "recebido: %s" % piso("auxiliary", 512))


# ===========================================================================
# BLOCO E5/E6 -- PELO ENDPOINT DE PRODUCAO (batimento e gravacao do motivo)
#
# ⛔ REUSO: o arreio inteiro vem do guarda irmao da SPEC-096.
# ===========================================================================
def _arreio():
    return importlib.import_module("test_o_chat_fala_tipado")


def bloco_endpoint():
    _p("\n[ENDPOINT] o batimento aparece, e o motivo da parada fica GRAVADO")
    try:
        arreio = _arreio()
        chat_mod = importlib.import_module("app.api.chat")
    except BaseException as erro:  # noqa: BLE001
        certo(False, "[E5][E6] endpoint e arreio importam",
              "%s: %s" % (type(erro).__name__, erro))
        return

    # ---- [E5a] a constante do batimento cabe em qualquer proxy ------------
    # 📊 O proxy do EasyPanel/Nginx derruba conexao ociosa por volta de 60s.
    # Uma resposta de 107s (medida em 09/09) so sobrevive se algo trafegar.
    certo(chat_mod.SEGUNDOS_DE_BATIMENTO <= 15,
          "[E5a] o batimento do turno e de no maximo 15s",
          "SEGUNDOS_DE_BATIMENTO: %s" % chat_mod.SEGUNDOS_DE_BATIMENTO)

    chave_antiga = os.environ.get("ADMIN_API_KEY")
    os.environ["ADMIN_API_KEY"] = arreio.CHAVE_INTERNA_D
    batimento_original = chat_mod.SEGUNDOS_DE_BATIMENTO
    try:
        async def _rodar():
            # ---- [E5b] com um modelo LENTO, o batimento SAI no stream ------
            banco = arreio._banco_padrao_d(conversas=[])
            with arreio._TrocaModulosD(arreio._montar_stubs_d(banco)):
                # ⚠️ o relogio do teste e apertado de proposito: o que se prova
                # e que o MOTOR emite batimento no silencio, nao que 15s passem.
                chat_mod.SEGUNDOS_DE_BATIMENTO = 0.05
                arreio.EVENTOS_DO_GRAFO_D[:] = [
                    arreio._delta_d("comecou"), ("sleep", 0.4), arreio._delta_d(" terminou")]
                app = arreio._montar_app_d(chat_mod, banco)
                corpo = {"chatInput": "oi", "sessionId": str(uuid.uuid4()),
                         "companyId": arreio.CO_ALFA_D, "agentId": arreio.AGENTE_D,
                         "client_request_id": str(uuid.uuid4()),
                         "assistantMessageId": str(uuid.uuid4())}
                t = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=t, base_url="http://t", timeout=30) as c:
                    r = await c.post("/chat/stream", json=corpo,
                                     headers={"X-Internal-Key": arreio.CHAVE_INTERNA_D})
                eventos = arreio._linhas_sse_d(r.text)
                tipos = [e.get("type") for e in eventos]
                batimentos = [e for e in eventos if e.get("type") == "heartbeat"]
                certo(len(batimentos) >= 1,
                      "[E5b] com um modelo lento, o batimento aparece no stream",
                      "tipos: %s" % tipos)
                gravadas = [m for m in banco.dados["messages"] if m.get("role") == "assistant"]
                certo(len(gravadas) == 1 and gravadas[0]["content"] == "comecou terminou",
                      "[E5b] CONTROLE: o batimento NAO entra no texto da resposta",
                      "gravado: %r" % (gravadas[0]["content"] if gravadas else None))
                chat_mod.SEGUNDOS_DE_BATIMENTO = batimento_original

            # ---- [E6] o motivo e o uso ficam no `payload.turn` -------------
            banco = arreio._banco_padrao_d(conversas=[])
            with arreio._TrocaModulosD(arreio._montar_stubs_d(banco)):
                arreio.EVENTOS_DO_GRAFO_D[:] = [
                    arreio._delta_d("resposta"),
                    {"kind": "final", "finish_reason": "length", "truncated": True,
                     "continuations": 2,
                     "usage": {"input_tokens": 900, "output_tokens": 1200}},
                ]
                app = arreio._montar_app_d(chat_mod, banco)
                corpo = {"chatInput": "oi", "sessionId": str(uuid.uuid4()),
                         "companyId": arreio.CO_ALFA_D, "agentId": arreio.AGENTE_D,
                         "client_request_id": str(uuid.uuid4()),
                         "assistantMessageId": str(uuid.uuid4())}
                t = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=t, base_url="http://t", timeout=30) as c:
                    r = await c.post("/chat/stream", json=corpo,
                                     headers={"X-Internal-Key": arreio.CHAVE_INTERNA_D})
                eventos = arreio._linhas_sse_d(r.text)
                gravadas = [m for m in banco.dados["messages"] if m.get("role") == "assistant"]
                turno = ((gravadas[0].get("payload") or {}).get("turn") or {}) if gravadas else {}
                certo(turno.get("finish_reason") == "length",
                      "[E6] `finish_reason` fica GRAVADO no payload da mensagem",
                      "turn: %r" % (turno,))
                certo((turno.get("usage") or {}).get("output_tokens") == 1200,
                      "[E6] `usage` fica GRAVADO junto -- o custo do turno tem numero",
                      "turn.usage: %r" % (turno.get("usage"),))
                certo(turno.get("continuations") == 2 and turno.get("truncated") is True,
                      "[E6] o turno declara quantas emendas houve e se ficou cortado",
                      "turn: %r" % (turno,))
                # ⛔ CONTROLE R5: diagnostico NAO vira evento na conversa
                certo("final" not in [e.get("type") for e in eventos],
                      "[E6] CONTROLE: o diagnostico nao inventa evento novo no contrato",
                      "tipos: %s" % [e.get("type") for e in eventos])

            # ---- [E6b] CONTROLE: sem motivo declarado, nada e inventado ----
            banco = arreio._banco_padrao_d(conversas=[])
            with arreio._TrocaModulosD(arreio._montar_stubs_d(banco)):
                arreio.EVENTOS_DO_GRAFO_D[:] = [arreio._delta_d("resposta")]
                app = arreio._montar_app_d(chat_mod, banco)
                corpo = {"chatInput": "oi", "sessionId": str(uuid.uuid4()),
                         "companyId": arreio.CO_ALFA_D, "agentId": arreio.AGENTE_D,
                         "client_request_id": str(uuid.uuid4()),
                         "assistantMessageId": str(uuid.uuid4())}
                t = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=t, base_url="http://t", timeout=30) as c:
                    await c.post("/chat/stream", json=corpo,
                                 headers={"X-Internal-Key": arreio.CHAVE_INTERNA_D})
                gravadas = [m for m in banco.dados["messages"] if m.get("role") == "assistant"]
                turno = ((gravadas[0].get("payload") or {}).get("turn") or {}) if gravadas else {}
                certo("finish_reason" not in turno,
                      "[E6b] CONTROLE: provedor calado nao vira `finish_reason: null` no banco",
                      "turn: %r" % (turno,))
        asyncio.run(_rodar())
    finally:
        chat_mod.SEGUNDOS_DE_BATIMENTO = batimento_original
        if chave_antiga is None:
            os.environ.pop("ADMIN_API_KEY", None)
        else:
            os.environ["ADMIN_API_KEY"] = chave_antiga


# ===========================================================================
# AS MUTACOES -- por copia. Um guarda que nao acusa a mutacao e um carimbo.
# ===========================================================================
MUTACOES = [
    ("app/agents/graph.py",
     'MOTIVOS_DE_CORTE = ("length", "max_tokens", "max_output_tokens", "MAX_TOKENS")',
     'MOTIVOS_DE_CORTE = ()',
     "graph.py nao reconhece mais nenhum motivo como corte", ["[E1]", "[E3]", "[E7]"]),
    ("app/factories/llm_factory.py",
     "    return max(atual, PISO_DE_SAIDA_DA_CONVERSA)",
     "    return atual",
     "a fabrica volta a obedecer o numero gravado no banco", ["[E4]"]),
    ("app/api/chat.py",
     "                for chave, valor in (desfecho or {}).items():",
     "                for chave, valor in {}.items():",
     "o desfecho do modelo nao entra mais no turno gravado", ["[E6]"]),
    ("app/api/chat.py",
     "SEGUNDOS_DE_BATIMENTO = 15",
     "SEGUNDOS_DE_BATIMENTO = 600",
     "o batimento passa a ser de 10 minutos", ["[E5a]"]),
]


def rodar_mutacoes():
    global OK, FAIL, FALHAS
    _p("\n" + "=" * 74)
    _p("MUTACOES -- cada bloco tem de ficar VERMELHO quando o codigo mente")
    _p("=" * 74)
    for caminho, alvo, troca, descricao, rotulos in MUTACOES:
        completo = os.path.join(RAIZ, caminho)
        if not os.path.exists(completo):
            _p("  PULADA  %s (arquivo ausente)" % caminho)
            continue
        original = io.open(completo, encoding="utf-8").read()
        if alvo not in original:
            _p("  PULADA  %s -- ancora ausente: %r" % (caminho, alvo[:50]))
            continue
        backup = completo + ".bak-resposta-inteira"
        shutil.copy2(completo, backup)
        try:
            io.open(completo, "w", encoding="utf-8").write(original.replace(alvo, troca, 1))
            for nome in ("app.agents.graph", "app.factories.llm_factory", "app.api.chat"):
                if nome in sys.modules:
                    importlib.reload(sys.modules[nome])
            antes_fail = FAIL
            FALHAS_antes = list(FALHAS)
            ok_antes, fail_antes = OK, FAIL
            _p("\n  MUTACAO: %s" % descricao)
            silencio = io.StringIO()
            real = sys.stdout
            sys.stdout = silencio
            try:
                bloco_emenda()
                bloco_piso()
                bloco_endpoint()
            except BaseException as explodiu:  # noqa: BLE001
                sys.stdout = real
                _p("    (a mutacao derrubou o bloco: %s -- conta como vermelho)"
                   % type(explodiu).__name__)
            finally:
                sys.stdout = real
            novas = [f for f in FALHAS[len(FALHAS_antes):]]
            pegou = any(any(r in f for f in novas) for r in rotulos)
            # a contagem da rodada mutada nao entra no placar do guarda
            OK, FAIL = ok_antes, fail_antes
            FALHAS[:] = FALHAS_antes
            if pegou:
                _p("    OK   a mutacao ficou VERMELHA em %s" % ", ".join(rotulos))
            else:
                _p("    MUTACAO NAO PEGOU -- %s continuou verde. Isto e um CARIMBO."
                   % ", ".join(rotulos))
                FAIL += 1
                FALHAS.append("MUTACAO NAO PEGOU: %s (%s)" % (descricao, ", ".join(rotulos)))
        finally:
            shutil.move(backup, completo)
            for nome in ("app.agents.graph", "app.factories.llm_factory", "app.api.chat"):
                if nome in sys.modules:
                    importlib.reload(sys.modules[nome])


def main():
    _p("=" * 74)
    _p("A RESPOSTA CHEGA INTEIRA -- guarda do corte de saida (09/09/2026)")
    _p("=" * 74)
    bloco_emenda()
    bloco_piso()
    bloco_endpoint()
    if "--mutar" in sys.argv or os.environ.get("AUTOBROKERS_MUTAR") == "1":
        rodar_mutacoes()
    _p("\n" + "=" * 74)
    _p("PLACAR: %d OK · %d FALHA" % (OK, FAIL))
    for f in FALHAS:
        _p("  - %s" % f)
    _p("=" * 74)
    return 0 if FAIL == 0 else 1


def test_a_resposta_chega_inteira():
    """Porta do pytest -- o mesmo guarda, sem as mutacoes."""
    bloco_emenda()
    bloco_piso()
    bloco_endpoint()
    assert FAIL == 0, "falhas: %s" % FALHAS


if __name__ == "__main__":
    sys.exit(main())
