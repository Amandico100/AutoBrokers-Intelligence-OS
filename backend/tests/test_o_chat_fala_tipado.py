# -*- coding: utf-8 -*-
"""O CHAT FALA TIPADO -- o guarda da SPEC-096 do lado do MOTOR (backend).

🔴 **ESTE ARQUIVO NASCE VERMELHO, E E PARA NASCER.** Protocolo AAA v11.2 §4
(opcao B): quem faz a prova nao faz a resposta. O DESENHISTA o escreveu com o
BLOCO B (o protocolo tipado), o BLOCO A (a persistencia ate o fim) e a migration
A.1 ainda inexistentes -- e a saida separa **VERMELHO ESPERADO** (a SPEC ainda
deve aquele bloco, com o nome do bloco ao lado) de **VERMELHO DE VERDADE**
(defeito). O gate FINAL da SPEC-096 so fecha com a lista de VERMELHO ESPERADO
**vazia**.

O GATE ZERO -- os defeitos de HOJE que este arquivo prova em `e1494ab`
------------------------------------------------------------------------------
Do §4 BLOCO 0.1, os itens que sao do MOTOR (os outros cinco moram no guarda da
tela, `scripts/o-chat-responde-e-continua.test.mjs`):
```
 (iii)  o backend honra `userId` do corpo SEM chave interna                [B8]
        (📊 chat.py:432 `if agent_data and not chat_request.userId`: quem
         manda um userId qualquer pula as checagens de widget)
  (iv)   credito insuficiente sai como `{"token": ...}`                     [B4]
        (📊 chat.py:362 "Creditos insuficientes..." vira token e memoria)
   (v)   a excecao crua vai ao browser (`{"error": str(e)}`)               [B5]
        (📊 chat.py:668)
  (ix)   `on_tool_start` e ignorado -- o estagio nunca nasce do runtime     [B9]
        (📊 §1.5: o no `tools` chama `_arun`/`_run`, que pulam o
         CallbackManager; `on_tool_start` NUNCA e emitido)
   (x)   a resposta parcial e descartada na falha                          [B5/B6]
        (📊 chat.py:614 grava so `if full_response.strip()`, DEPOIS do
         stream inteiro; a excecao no meio nao grava nada)
```

O ELO que esta SPEC afirma, e que este guarda mede
------------------------------------------------------------------------------
```
o corretor ve o que esta acontecendo PORQUE o estagio nasce do evento REAL
  -> `stream_agent_eventos` projeta o laco de `astream_events` (mantendo v1)
     em dicts tipados: token · tool_start{name} · tool_end · error
  -> `chat_eventos.py` embrulha cada um num Envelope(seq, type, turn, payload)
     com `protocol='autobrokers.interaction.v1'` e seq monotonico por turno
  -> o CATALOGO DE ESTAGIOS traduz a tool para a frase da corretora, SEM nome
     tecnico -- tool fora do catalogo => "Trabalhando nisso..."
E nada de aviso/erro/estagio entra em `messages.content` (R5).
```
🔴 O passo que ninguem da (protocolo §0.3) e o do MEIO. Por isso os blocos [B3]-
[B10] chamam `stream_agent_eventos` com o grafo DUBLADO (nunca o grafo real),
em vez de conferir por `grep` que existe uma funcao com esse nome. Enquanto a
funcao nao existe, o bloco captura a ausencia e REPROVA com a mensagem -- nunca
estoura, nunca `xfail` (D5).

⚠️ **E toda lista de casos carrega PARES** (protocolo §5): mesma superficie,
veredito oposto. Aqui os pares sao SINTETICOS e moram em memoria.

🔴 AS MUTACOES -- por COPIA, e por que elas NAO rodam por padrao
------------------------------------------------------------------------------
⛔ **Elas nao rodam sem `--mutar`.** Este guarda nasce enquanto DOIS builders
escrevem `backend/app/` no mesmo diretorio: mutar em disco e restaurar por copia
apagaria a edicao de quem estivesse salvando naquele segundo. Com a arvore
parada -- integracao, conserto, confirmacao mecanica -- rode:

    PYTHONIOENCODING=utf-8 python backend/tests/test_o_chat_fala_tipado.py --mutar

Cada mutacao: copia o arquivo para `.bak-096`, aplica a substituicao, RECARREGA
o modulo, mede, e restaura no `finally`. O bloco fica VERMELHO se a assercao
**nao** ficar vermelha sob a mutacao -- um gate que nao acusa a mutacao e um
carimbo (CLAUDE.md §9.3). Enquanto o arquivo/ancora nao existir (o codigo do
builder ainda nao chegou), a mutacao e PULADA com a razao -- nunca conta como
passada.

    MUTACOES (arquivo · o que trocar · qual assercao fica vermelha):
     1. app/api/chat_eventos.py  o CATALOGO devolve "Chamando tool X"    -> [B2]
     2. app/api/chat_eventos.py  `erro_seguro` devolve str(exc)          -> [B5] (EXECUCAO, bloco_D_endpoint)
     3. app/api/chat.py          policy.blocked volta a `{"token"}`      -> [B4] (EXECUCAO, bloco_D_endpoint)
     4. app/api/chat.py          a chave interna e ignorada (honra userId) -> [B8a] (EXECUCAO, bloco_D_endpoint)
     5. app/agents/graph.py      `stream_agent_eventos` nao emite tool_start -> [B9]
     6. app/api/chat.py          o Stop nao grava status interrupted     -> [B7] (EXECUCAO, bloco_D_endpoint)
     7. supabase/migrations/20260904_01_spec096_turno_idempotente.sql
                                 o indice sem `WHERE` (nao parcial)       -> [B11]

⛔ SEGURANCA, e ela nao e opcional
------------------------------------------------------------------------------
```
· `SEM_REDE=1` e `socket.connect` BLOQUEADO -- so DENTRO de `main()`, e
  devolvido no `finally` (📊 instalado no import, o bloqueio pega a COLETA do
  pytest e deixa vermelhos testes de outros arquivos).
· Nenhuma escrita e nenhuma leitura de banco: os dubles sao memoria pura.
· NENHUM nome de pessoa, CPF, apolice, placa, telefone, senha ou token nas
  fixtures. Os rotulos sao sentinelas obvias -- "Corretora Alfa". A excecao do
  [B5] levanta a string "segredo-XYZ" DE PROPOSITO: o guarda prova que ela NAO
  aparece em nenhum evento (R7).
```

Rodar:  PYTHONIOENCODING=utf-8 python backend/tests/test_o_chat_fala_tipado.py
        (a partir de `backend/`: `python tests/test_o_chat_fala_tipado.py`)
        `--mutar` acrescenta as mutacoes por copia (so com a arvore parada).
"""
from __future__ import annotations

import asyncio
import importlib
import io
import json
import os
import re
import shutil
import socket
import sys
import types
import uuid

import httpx
from fastapi import FastAPI

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

TESTES = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(TESTES)                      # .../backend
APP = os.path.join(RAIZ, "app")
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

CO_ALFA = "co-alfa-0000-4000-8000-000000000001"
CO_BETA = "co-beta-0000-4000-8000-000000000002"
U_ALFA = "u-alfa-0000-4000-8000-000000000001"

MIGRATION_096 = "supabase/migrations/20260904_01_spec096_turno_idempotente.sql"

# ===========================================================================
# 🔴 A DECLARACAO DE MUTACOES -- lida pelo arnes compartilhado
#
# Formato: (caminho relativo a `backend/`, de, para, rotulo). Todo arquivo
# citado aqui passa a ser vigiado, restaurado e cobrado no fim da sessao.
# ===========================================================================
MUTACOES = [
    ("app/api/chat_eventos.py",
     '"key": "generic"', '"key": "generic_MUTADO"', "B2"),
    ("app/api/chat_eventos.py",
     '"message_human": MENSAGENS_HUMANAS.get(codigo, MENSAGENS_HUMANAS["unknown"]),',
     '"message_human": str(exc),', "B5"),
    ("app/api/chat.py",
     "policy.blocked", '{"token"}', "B4"),
    ("app/api/chat.py",
     "X-Internal-Key", "X-Internal-Key-MUTADO", "B8a"),
    ("app/agents/graph.py",
     "tool_start", "tool_start_MUTADO", "B9"),
    ("app/api/chat.py",
     'estado = "interrupted"', 'estado = "interrupted_MUTADO"', "B7"),
    (MIGRATION_096,
     "WHERE", "WHERE_MUTADO", "B11"),
]

# ===========================================================================
# A rede fechada -- so dentro de main()
# ===========================================================================
_CONNECT = socket.socket.connect
_CONNECT_EX = socket.socket.connect_ex


def _loopback(destino):
    try:
        return isinstance(destino, tuple) and str(destino[0]) in ("127.0.0.1", "::1", "localhost")
    except Exception:  # noqa: BLE001
        return False


def _proibir(self, destino, *a, **k):  # noqa: ANN001
    if _loopback(destino):
        return _CONNECT(self, destino, *a, **k)
    raise RuntimeError("SEM_REDE: este guarda nao fala com a rede (destino %r)" % (destino,))


def _proibir_ex(self, destino, *a, **k):  # noqa: ANN001
    if _loopback(destino):
        return _CONNECT_EX(self, destino, *a, **k)
    raise RuntimeError("SEM_REDE: este guarda nao fala com a rede (destino %r)" % (destino,))


def _fechar_a_rede():
    os.environ["SEM_REDE"] = "1"
    socket.socket.connect = _proibir        # type: ignore[assignment]
    socket.socket.connect_ex = _proibir_ex  # type: ignore[assignment]


def _abrir_a_rede():
    socket.socket.connect = _CONNECT        # type: ignore[assignment]
    socket.socket.connect_ex = _CONNECT_EX  # type: ignore[assignment]
    os.environ.pop("SEM_REDE", None)


# ===========================================================================
# `sys.modules` -- as cascas de pacote, e a devolucao do ambiente
#
# 📊 `app/agents/__init__.py` puxa langgraph e `app/api/__init__.py` puxa o
# mundo: sem a casca, importar `app.api.chat_eventos` pularia com a razao ERRADA
# em vez da verdadeira ("o BLOCO B ainda nao existe"). A casca tem `__path__`
# REAL: nenhum codigo nosso e falsificado, so os `__init__` deixam de rodar.
# ===========================================================================
_AUSENTE = object()
_ORIGINAIS: dict = {}
_NO_INICIO: set = set()


class _Qualquer:
    """Um substituto universal -- aceita qualquer chamada/atributo, sem fazer
    nada. Usado só para satisfazer `from app.services import AudioService,
    LangChainService` no topo de `chat.py` sem subir os serviços reais (o
    bloco D nunca instancia estas classes -- `/chat/stream` só usa
    `get_audio_service`/`get_langchain_service` de dentro de `/chat`, rota
    que este guarda não exercita)."""

    def __init__(self, *a, **k):
        pass

    def __getattr__(self, item):
        return _Qualquer()

    def __call__(self, *a, **k):
        return _Qualquer()


def _fotografar():
    global _NO_INICIO
    if not _NO_INICIO:
        _NO_INICIO = set(sys.modules)


def _guardar(nome):
    if nome not in _ORIGINAIS:
        _ORIGINAIS[nome] = sys.modules.get(nome, _AUSENTE)


def _cascas():
    for sub in ("api", "services", "agents", "comercial", "providers", "tasks"):  # "core" NAO: app/core/__init__ exporta settings/get_supabase_client (📊 05/09)
        nome = "app." + sub
        atual = sys.modules.get(nome)
        if atual is not None and getattr(atual, "__file__", None) is None:
            continue
        casca = types.ModuleType(nome)
        casca.__path__ = [os.path.join(APP, sub)]
        casca.__package__ = nome
        if sub == "services":
            # 🔴 bloco_D_endpoint importa `app.api.chat` de verdade, e o topo
            # dele faz `from app.services import AudioService, LangChainService`
            # -- sem isto o import quebraria por AttributeError na casca vazia.
            casca.AudioService = _Qualquer
            casca.LangChainService = _Qualquer
        _guardar(nome)
        sys.modules[nome] = casca
    # 📊 05/09/2026: `app.agents.tools` NAO vira casca. `graph.py:30` faz
    # `from .tools import HumanHandoffTool, ...` -- precisa do __init__ real do
    # pacote de tools. Com a casca, o grafo nunca importava e os blocos B3-B13
    # ficavam vermelhos por "ainda nao existe" -- que era falso. O que o
    # __init__ das tools puxa (qdrant, langchain-*) e dependencia do produto:
    # onde falta, o bloco diz AMBIENTE, nao inventa defeito.


def _restaurar_sys_modules():
    for nome in sorted(sys.modules):
        if nome in _NO_INICIO or nome in _ORIGINAIS:
            continue
        if nome == "app" or nome.startswith("app."):
            _ORIGINAIS[nome] = _AUSENTE
    for nome, anterior in list(_ORIGINAIS.items()):
        if anterior is _AUSENTE:
            sys.modules.pop(nome, None)
        else:
            sys.modules[nome] = anterior
    _ORIGINAIS.clear()


def _abrir_o_ambiente():
    _fotografar()
    try:
        _guardar("app")
        import app  # noqa: F401
        _cascas()
    except Exception:  # noqa: BLE001
        pass


# ===========================================================================
# O placar -- tres verbos (o molde de 095/protocolo §5)
# ===========================================================================
OK = FAIL = 0
PULADOS: list = []
ESPERADOS: list = []
JA_PODEM_VIRAR: list = []
# 🔴 CONSERTO (1): o CONJUNTO de nomes de assercoes que ja falharam (de
# verdade OU esperadas). `rodar_mutacoes` compara este conjunto antes x
# depois de cada mutacao -- so conta como ACUSADA a mutacao que fez aparecer
# um nome NOVO (ou um `certo` que virou falha).
NOMES_FALHOS: set = set()


def _p(texto):
    try:
        print(texto)
    except UnicodeEncodeError:
        cod = getattr(sys.stdout, "encoding", None) or "ascii"
        print(texto.encode(cod, "replace").decode(cod, "replace"))


def certo(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        _p("  [ok] %s" % rotulo)
    else:
        FAIL += 1
        NOMES_FALHOS.add(rotulo)
        _p("  [FALHOU] %s" % rotulo + ("\n         %s" % str(detalhe)[:600] if detalhe else ""))
    return bool(cond)


# 🔴 INTEGRADO (04/09/2026, depois dos builders): o que era "devendo" passou a ser exigido.
#    Uma assercao que falhe e VERMELHO DE VERDADE. Bloco que nao pode ser medido por falta
#    de dependencia nesta maquina continua sendo FALHA aqui -- o gate roda onde o grafo importa.
INTEGRADO = True


def devendo(cond, rotulo, bloco, detalhe=""):
    global OK, FAIL
    if INTEGRADO:
        return certo(cond, rotulo, detalhe)
    if cond:
        OK += 1
        _p("  [ok] %s" % rotulo)
        JA_PODEM_VIRAR.append("%s   [era devendo('%s')]" % (rotulo, bloco))
    else:
        FAIL += 1
        NOMES_FALHOS.add(rotulo)
        ESPERADOS.append("%s   (esperado ate %s)" % (rotulo, bloco))
        _p("  VERMELHO-ESPERADO %s   (ate %s)" % (rotulo, bloco)
           + ("\n         %s" % str(detalhe)[:600] if detalhe else ""))
    return bool(cond)


def par(cond_reprovou, rotulo, detalhe=""):
    """A linha de controle. `cond_reprovou` e True quando o guarda ACUSOU."""
    global OK, FAIL
    if cond_reprovou:
        OK += 1
        _p("  [ok] PAR %s -- o guarda acusou" % rotulo)
    else:
        FAIL += 1
        _p("  [FALHOU] PAR %s -- o guarda NAO acusou; ele nao guarda nada" % rotulo
           + ("\n         %s" % str(detalhe)[:400] if detalhe else ""))
    return bool(cond_reprovou)


def pular(rotulo, razao):
    PULADOS.append(rotulo)
    _p("  --   PULADO %s\n         %s" % (rotulo, razao))


def rel(caminho):
    try:
        return os.path.relpath(caminho, RAIZ).replace("\\", "/")
    except Exception:  # noqa: BLE001
        return caminho


def ler(relativo):
    return io.open(os.path.join(RAIZ, relativo), encoding="utf-8", errors="replace").read()


def existe(relativo):
    return os.path.exists(os.path.join(RAIZ, relativo))


def razao_ausencia(mod_opcional, mensagem_produto):
    """🔴 CONSERTO (bonus): escolhe a razao certa quando um bloco B3-B13
    depende de um modulo opcional que falhou ao importar. Se a falha e um
    `ModuleNotFoundError` de PACOTE DE TERCEIRO (ex.: langgraph ausente
    nesta maquina), a causa e AMBIENTE -- dizer "ainda nao existe" seria
    FALSO quando o codigo do produto ja esta escrito e so falta o pacote."""
    if isinstance(mod_opcional, dict) and mod_opcional.get("__erro"):
        erro = str(mod_opcional["__erro"])
        if erro.startswith("ModuleNotFoundError"):
            m = re.search(r"No module named '([^']+)'", erro)
            pacote = m.group(1).split(".")[0] if m else erro
            return ("AMBIENTE: falta %s -- o bloco nao pode ser medido nesta maquina "
                    "(%s)" % (pacote, erro))
        # 📊 05/09: qualquer OUTRA falha de import tambem e mostrada -- um guarda
        # que esconde a causa ensina a chutar ("ainda nao existe" com o codigo
        # escrito foi exatamente isso).
        return "IMPORT FALHOU: %s -- (a razao de produto seria: %s)" % (erro, mensagem_produto)
    return mensagem_produto


def modulo_opt(nome_arquivo, nome_modulo):
    """Importa um modulo do produto SE o arquivo existir. Ausente => None (o
    bloco vira VERMELHO ESPERADO com a mensagem escrita, nunca estoura)."""
    if not existe(nome_arquivo):
        return None
    try:
        return importlib.import_module(nome_modulo)
    except Exception as exc:  # noqa: BLE001
        return {"__erro": "%s: %s" % (type(exc).__name__, str(exc)[:200])}


# ===========================================================================
# O CATALOGO DE TOOLS -- lido da arvore (o mesmo grep do investigador)
#
# 📊 38 tools declaradas (`grep -rhn 'name: str = "' backend/app/agents/tools/
# *.py`). O [B2] exige que TODA tool tenha entrada no CATALOGO, com label sem
# nome tecnico. Enquanto `chat_eventos.py` nao existe, o bloco e VERMELHO
# ESPERADO -- mas a LISTA e lida agora, para o guarda ja saber o que cobrar.
# ===========================================================================
def nomes_de_tools():
    nomes = set()
    dir_tools = os.path.join(APP, "agents", "tools")
    if not os.path.isdir(dir_tools):
        return nomes
    for f in os.listdir(dir_tools):
        if not f.endswith(".py"):
            continue
        s = io.open(os.path.join(dir_tools, f), encoding="utf-8", errors="replace").read()
        for m in re.finditer(r'name:\s*str\s*=\s*"([^"]+)"', s):
            nomes.add(m.group(1))
    return nomes


# ⛔ nome tecnico proibido em qualquer label (§3, R6).
RE_NOME_TECNICO = re.compile(r"tool|node|mcp|langgraph|qdrant|subagent|graph", re.IGNORECASE)


# ===========================================================================
# O GRAFO DUBLADO -- um `astream_events` de mentira, com 1 tool
#
# 🔴 Nunca o grafo real (protocolo: nao meca o motor de terceiro). Um gerador
# assincrono que o teste escolhe: tokens, on_tool_start/on_chain_end, excecao.
# `stream_agent_eventos` (quando existir) projeta ISTO em dicts tipados.
# ===========================================================================
class GrafoDublado:
    def __init__(self, eventos):
        self._eventos = eventos

    async def astream_events(self, *a, **k):
        for e in self._eventos:
            if isinstance(e, BaseException):
                raise e
            yield e


def evento(tipo, **campos):
    """Um evento no formato do `astream_events(version='v1')`."""
    return {"event": tipo, "name": campos.get("name", ""),
            "data": campos.get("data", {}),
            "metadata": {"langgraph_node": campos.get("node", "")}}


def turno_feliz_com_tool():
    """on_chat_model_stream (com tool_call_chunk) -> tool -> 3 deltas -> fim."""
    chunk = types.SimpleNamespace(tool_call_chunks=[{"name": "listar_entregas", "id": "call-1"}])
    return [
        evento("on_chat_model_stream", data={"chunk": chunk}, node="agent"),
        evento("on_chain_start", name="tools", node="tools"),
        evento("on_chain_end", name="tools", node="tools"),
        evento("on_chat_model_stream", data={"chunk": types.SimpleNamespace(content="Oi", tool_call_chunks=[])}, node="agent"),
        evento("on_chat_model_stream", data={"chunk": types.SimpleNamespace(content=" tudo", tool_call_chunks=[])}, node="agent"),
        evento("on_chat_model_stream", data={"chunk": types.SimpleNamespace(content=" bem", tool_call_chunks=[])}, node="agent"),
    ]


def coletar_sync(gerador_async):
    """Roda um gerador assincrono ate o fim e devolve a lista de itens."""
    saida = []

    async def _rodar():
        async for x in gerador_async:
            saida.append(x)
    asyncio.run(_rodar())  # 3.12+/3.14 nao cria loop implicito
    return saida


# ===========================================================================
# BLOCO B -- O PROTOCOLO TIPADO
# ===========================================================================
def bloco_B_protocolo(ctx):
    _p("\n[B] O PROTOCOLO -- o chat fala tipado (Envelope, seq, catalogo, erro seguro)")

    ce = ctx["chat_eventos"]

    # ---- B1 · Envelope + seq monotonico ------------------------------------
    if ce is None:
        devendo(False, "[B1] Envelope(seq, type, turn, payload) com protocol v1 e seq monotonico",
                "B.1", "`backend/app/api/chat_eventos.py` ainda nao existe -- o Envelope, o "
                "CATALOGO e `erro_seguro` do BLOCO B.1 nao foram escritos")
    elif isinstance(ce, dict) and ce.get("__erro"):
        devendo(False, "[B1] chat_eventos.py importa", "B.1", ce["__erro"])
    else:
        Envelope = getattr(ce, "Envelope", None)
        if Envelope is None:
            devendo(False, "[B1] `Envelope` existe em chat_eventos.py", "B.1", "sem a classe Envelope")
        else:
            try:
                e1 = Envelope(seq=1, type="turn.accepted", turn={"client_request_id": "c1"}, payload={})
                d1 = e1.as_dict() if hasattr(e1, "as_dict") else (e1.model_dump() if hasattr(e1, "model_dump") else vars(e1))
                certo(d1.get("protocol") == "autobrokers.interaction.v1" and d1.get("seq") == 1,
                      "[B1] o Envelope serializa com protocol v1 e seq=1",
                      "serializou %r" % d1)
            except Exception as exc:  # noqa: BLE001
                devendo(False, "[B1] o Envelope serializa", "B.1", "%s: %s" % (type(exc).__name__, exc))

    # ---- B2 · o CATALOGO DE ESTAGIOS ---------------------------------------
    tools = ctx["nomes_de_tools"]
    _p("      tools declaradas na arvore: %d" % len(tools))
    if ce is None or isinstance(ce, dict):
        devendo(False, "[B2] toda tool tem entrada no CATALOGO, com label sem nome tecnico",
                "B.1", "chat_eventos.py ausente -- o CATALOGO DE ESTAGIOS (tool -> {key, label}) "
                "e `estagio_da_tool` do B.1 nao existem. Tools a cobrir: %d" % len(tools))
    else:
        estagio_da_tool = getattr(ce, "estagio_da_tool", None)
        if estagio_da_tool is None:
            devendo(False, "[B2] `estagio_da_tool(nome)` existe", "B.1", "sem a funcao")
        else:
            faltando, tecnicos = [], []
            for nome in sorted(tools):
                try:
                    ent = estagio_da_tool(nome)
                except Exception as exc:  # noqa: BLE001
                    faltando.append("%s (estourou: %s)" % (nome, exc))
                    continue
                label = str((ent or {}).get("label") or "")
                if not label:
                    faltando.append(nome)
                elif RE_NOME_TECNICO.search(label):
                    tecnicos.append("%s -> %r" % (nome, label))
            certo(not faltando, "[B2] toda tool do registry tem entrada no CATALOGO",
                  "sem entrada: %s" % ", ".join(faltando[:6]))
            certo(not tecnicos, "[B2] nenhum label carrega nome tecnico (tool|node|mcp|langgraph|qdrant|subagent|graph)",
                  "labels tecnicos: %s" % "; ".join(tecnicos[:4]))
            generico = estagio_da_tool("tool_que_nao_existe") or {}
            certo(generico.get("key") == "generic" and str(generico.get("label") or "").strip(),
                  "[B2] tool fora do catalogo -> {key:'generic', label:'Trabalhando nisso...'}",
                  "devolveu %r" % (generico,))
            # PAR sintetico -- um catalogo que devolve "Chamando tool X" e ACUSADO.
            par(bool(RE_NOME_TECNICO.search("Chamando tool listar_entregas")),
                "[B2] o detector de nome tecnico acha 'Chamando tool X'",
                "o detector nao acha o nome tecnico nem quando ele esta la")

    # ---- B13 · Envelope + catalogo puros (sem grafo) -----------------------
    #  (coberto pelos dois acima enquanto chat_eventos.py nao existe)


# ===========================================================================
# BLOCO B (grafo dublado) -- a ORDEM, o erro, a persistencia ate o fim
# ===========================================================================
def bloco_B_grafo(ctx):
    _p("\n[Bg] O GRAFO DUBLADO -- ordem dos eventos, erro seguro, persistencia ate o fim")

    graph = ctx["graph"]
    tem_eventos = graph is not None and not isinstance(graph, dict) and hasattr(graph, "stream_agent_eventos")

    # ---- B3 · a ordem dos eventos, turno feliz com 1 tool ------------------
    if not tem_eventos:
        motivo = razao_ausencia(graph,
                  "`stream_agent_eventos` ainda nao existe em graph.py (B.2) -- hoje so ha "
                  "`stream_agent`, que devolve string (§1.5). O projetor tipado do BLOCO B "
                  "nao foi escrito.")
        devendo(False, "[B3] a ordem: turn.accepted -> stage.* -> delta*N -> content.completed -> turn.completed",
                "B.2", motivo)
        devendo(False, "[B4] porteira/agente/guardrail -> policy.blocked/notice SEM gravar messages", "B.3", motivo)
        devendo(False, "[B5] excecao -> error{code, correlation_id, message_human} SEM str(e); parcial gravado", "B.3", motivo)
        devendo(False, "[B6] consumidor abandona -> a resposta INTEIRA e gravada (A.4)", "A.4", motivo)
        devendo(False, "[B9] stream_agent_eventos emite tool_start a partir de tool_call_chunk (nunca relogio)", "B.2", motivo)
        devendo(False, "[B10] heartbeat a cada 16s sem evento; nunca dentro de content", "B.3", motivo)
        devendo(False, "[B13] assistant.content.completed.content == concatenacao dos deltas", "B.3", motivo)
        devendo(False, "[B12] a linha gravada tem payload.turn com client_request_id/status/ttft_ms/"
                "total_ms/stages/artifacts/attempt", "B.3", motivo)
        devendo(False, "[B9b] stream_agent roda sobre o grafo dublado com tool_start + erro", "B.2", motivo)
    else:
        # Quando o builder escrever a funcao, ESटES executam o motor sobre o
        # grafo dublado. O molde ja esta aqui para o gate final medir de verdade.
        try:
            eventos = coletar_sync(graph.stream_agent_eventos(
                GrafoDublado(turno_feliz_com_tool()),
                company_id=CO_ALFA, user_id=U_ALFA, session_id="ss", client_request_id="c1"))
            tipos = [str((e or {}).get("kind") or (e or {}).get("type") or "") for e in eventos]
            certo(any("tool_start" in t for t in tipos),
                  "[B9] tool_start emitido a partir do tool_call_chunk (nao de relogio)",
                  "tipos: %s" % ", ".join(tipos))
            certo(not any(t == "token" for t in tipos) or any("delta" in t for t in tipos),
                  "[B3] a ordem tem deltas/estagios tipados (nao `{'token'}` cru no modo painel)",
                  "tipos: %s" % ", ".join(tipos))
        except Exception as exc:  # noqa: BLE001
            devendo(False, "[B3/B9] stream_agent_eventos roda sobre o grafo dublado", "B.2",
                    "%s: %s" % (type(exc).__name__, str(exc)[:200]))

        # ---- B9b · `stream_agent` (o wrapper legado) EXECUTADO -----------------
        # 🔴 P1-2: o wrapper foi REESCRITO nesta SPEC (itera stream_agent_eventos e
        # filtra kind=='delta'). O unico guarda de antes era um grep no NOME da
        # funcao -- isto roda o motor de verdade sobre tokens + tool_start + erro.
        try:
            eventos_b9b = turno_feliz_com_tool() + [RuntimeError("segredo-b9b")]
            saida_b9b = coletar_sync(graph.stream_agent(
                GrafoDublado(eventos_b9b),
                user_message="x", company_id=CO_ALFA, user_id=U_ALFA, session_id="ss", company_config={}))
            certo(bool(saida_b9b) and all(isinstance(p, str) for p in saida_b9b)
                  and not any(isinstance(p, dict) for p in saida_b9b),
                  "[B9b] `stream_agent` (o wrapper legado) devolve SO strings (contrato do "
                  "widget/WhatsApp/n8n), mesmo com tool_start + erro no meio",
                  "tipos: %s" % [type(p).__name__ for p in saida_b9b])
            certo(not any("tool_start" in p for p in saida_b9b),
                  "[B9b] o tool_start NUNCA vaza como texto no wrapper legado",
                  "saida: %r" % (saida_b9b,))
        except Exception as exc:  # noqa: BLE001
            devendo(False, "[B9b] stream_agent roda sobre o grafo dublado com tool_start + erro", "B.2",
                    "%s: %s" % (type(exc).__name__, str(exc)[:200]))

    # ---- B9 legado · `stream_agent` continua devolvendo SO strings ---------
    if graph is None:
        devendo(False, "[B9] `stream_agent` (o wrapper) devolve SO strings de token", "B.2",
                "graph.py nao pode ser lido")
    else:
        fonte_graph = ler("app/agents/graph.py")
        certo("async def stream_agent(" in fonte_graph or "def stream_agent(" in fonte_graph,
              "[B9] `stream_agent` (o wrapper legado) existe -- quem consome string continua igual",
              "sem a funcao stream_agent em graph.py")


# ===========================================================================
# BLOCO S/B (fonte) -- os defeitos de HOJE que o GATE ZERO prova
# ===========================================================================
def bloco_gate_zero(ctx):
    _p("\n[0] GATE ZERO -- os defeitos do MOTOR que a SPEC-096 promete matar")
    chat = ler("app/api/chat.py")

    # (iv) credito insuficiente sai como token; (v) str(e); (x) parcial descartado
    certo('{"token": "Creditos insuficientes' not in chat and "policy.blocked" in chat,
          "(iv) credito insuficiente vira `policy.blocked`, nunca `{'token'}` (B.3/R4)",
          "📊 chat.py:362 emite `{\"token\": \"Creditos insuficientes...\"}` -- vira resposta "
          "e memoria. A SPEC exige policy.blocked SEM gravar messages (R5).")
    certo("str(e)" not in chat and "erro_seguro" in chat,
          "(v) a excecao vira `error` seguro (code/correlation_id/message_human), nunca `str(e)`",
          "📊 chat.py:668 `{\"error\": str(e)}` -- a excecao crua vai ao browser (R7).")
    certo("_modo_de_confianca" in chat,
          "(iii) `_modo_de_confianca(request)` decide painel|widget pela chave interna",
          "📊 chat.py:432 `if agent_data and not chat_request.userId` -- quem manda um userId "
          "qualquer pula as checagens de widget. O backend deve honrar userId SO com "
          "X-Internal-Key valida (S.2/B8).")
    certo("except BaseException" in chat or "CancelledError" in chat,
          "(x) a persistencia da task pega `BaseException` (o parcial sobrevive ao cancelamento)",
          "📊 A.4/E4: `CancelledError` herda de BaseException; o `except Exception` de hoje "
          "nao a pega, e o parcial e descartado na falha/Stop.")

    graph = ler("app/agents/graph.py")
    certo("stream_agent_eventos" in graph,
          "(ix) `stream_agent_eventos` projeta o estagio a partir do evento REAL do runtime",
          "📊 §1.5: `on_tool_start` NUNCA e emitido (o no `tools` chama `_arun`/`_run`, que "
          "pulam o CallbackManager); o estagio de hoje nasce de nada, e a tela fica muda.")


# ===========================================================================
# BLOCO A -- persistencia, Stop, modo de confianca
# ===========================================================================
def bloco_A_turno(ctx):
    _p("\n[A] O TURNO -- modo de confianca, Stop, o parcial, a migration idempotente")

    chat = ler("app/api/chat.py") if existe("app/api/chat.py") else ""

    # ---- B8/B8a/B8b/B8c · modo de confianca, isolamento widget e cross-tenant
    # 🔴 P1-1: B8a/B8b/B8c sao EXECUTADOS em `bloco_D_endpoint` (chat_stream real
    # + banco/grafo dublados) -- aqui so o portao de PRONTIDAO: sem
    # `_modo_de_confianca`, a SPEC ainda nao existe e o bloco D nao tem o que medir.
    ce = ctx["chat_eventos"]
    tem_modo = "_modo_de_confianca" in chat
    if not tem_modo:
        devendo(False, "[B8] sem X-Internal-Key + userId no corpo -> userId=None (modo widget); com chave valida -> honrado",
                "S.2", "📊 chat.py nao tem `_modo_de_confianca` -- hoje o backend honra qualquer "
                "userId do corpo, sem chave (§1.1). Chave errada tem de valer como sem chave.")

    # ---- B4 · porteira sem gravar (R5) -- EXECUTADO em bloco_D_endpoint
    if not tem_modo:
        pass  # coberto pelo gate zero

    # ---- B7 · Stop -- 🔴 P1-1: o status 'interrupted' e o `stopped_by` sao
    # EXECUTADOS em bloco_D_endpoint (POST /chat/stop de verdade sobre um
    # gerador lento); aqui so o portao de PRONTIDAO (a mutacao #6/B7 -- estado=
    # "interrupted" -> _MUTADO -- e pega por EXECUCAO, nao por regex).
    devendo("/chat/stop" in chat, "[B7] `POST /chat/stop {client_request_id}` cancela a task e grava o parcial (interrupted)",
            "B.4", "📊 chat.py nao tem a rota `/chat/stop` -- o Stop do BLOCO B.4/R8 nao existe; "
            "hoje 'Parar' so aborta o fetch do browser, e o backend nao sabe.")

    # ---- B6 · a task propria (A.4) -- 🔴 P1-1: o consumidor abandonando o
    # stream e a linha ficando 'complete' e EXECUTADO em bloco_D_endpoint;
    # aqui so o portao de PRONTIDAO.
    devendo("TURNOS_ATIVOS" in chat and "create_task" in chat,
            "[B6] a geracao corre em asyncio.create_task; a desconexao nao cancela (A.4)",
            "A.4", "📊 chat.py grava `full_response` DEPOIS do stream inteiro (:608/:614), no "
            "mesmo fluxo do gerador SSE: o browser fechar aborta a persistencia. A SPEC exige "
            "a geracao numa task propria, com TURNOS_ATIVOS[client_request_id].")

    # ---- B11 · a migration A.1 ---------------------------------------------
    if not existe(MIGRATION_096):
        devendo(False, "[B11] a migration do indice de idempotencia existe (A.1)",
                "A.1", "📊 `%s` ainda nao existe -- o indice unico parcial "
                "`messages_turno_sem_duplicata_uidx` do BLOCO A.1 nao foi escrito." % MIGRATION_096)
    else:
        mig = ler(MIGRATION_096)
        certo("CREATE UNIQUE INDEX IF NOT EXISTS messages_turno_sem_duplicata_uidx" in mig,
              "[B11] a migration cria o indice unico `messages_turno_sem_duplicata_uidx` com IF NOT EXISTS",
              "sem o CREATE UNIQUE INDEX IF NOT EXISTS")
        certo(re.search(r"\bWHERE\b", mig) is not None and "client_request_id" in mig,
              "[B11] o indice e PARCIAL (`WHERE ... client_request_id IS NOT NULL`)",
              "sem o WHERE parcial -- sem ele, uma linha sem client_request_id colidiria (expand-first)")
        for marca in ("APPLY", "VERIFY", "ROLLBACK"):
            certo(marca in mig, "[B11] a migration tem a linha %s escrita antes de rodar" % marca,
                  "sem a linha %s (MIGRATIONS-AUTHORITY.md)" % marca)
        certo(not re.search(r"\bDROP\b|\bTRUNCATE\b", mig),
              "[B11] a migration nao tem DROP/TRUNCATE (nao destrutiva, expand-first)",
              "achei DROP/TRUNCATE na migration")
        # PAR sintetico -- um indice sem IF NOT EXISTS e ACUSADO.
        par("IF NOT EXISTS" not in "CREATE UNIQUE INDEX messages_turno_sem_duplicata_uidx ON messages (...)",
            "[B11] o detector acha o indice sem IF NOT EXISTS",
            "o detector aceita um CREATE sem IF NOT EXISTS")


# ===========================================================================
# BLOCO D -- o TURNO por EXECUCAO: sobe o `chat_router` de PRODUCAO com banco
# PostgREST dublado e `stream_agent_eventos`/`stream_agent` dublados.
#
# 🔴 P0-1/P1-1/P1-2: o molde e o mesmo do builder (`medir_turno.py`), copiado
# para DENTRO do guarda (nunca importado do scratchpad). O motor de VERDADE que
# roda aqui e `app.api.chat` inteiro -- porteira, modo de confianca,
# persistencia, Stop, heartbeat. O que e dublado e so o que NAO e nosso: o
# banco (PostgREST) e o PROJETOR do grafo (`stream_agent_eventos`) -- esse ja
# tem guarda proprio em `bloco_B_grafo`, com o grafo REAL projetado por
# `stream_agent_eventos` sobre um `astream_events` dublado.
# ===========================================================================
CO_ALFA_D = "aaaaaaaa-0000-4000-8000-0000000000a1"
CO_BETA_D = "bbbbbbbb-0000-4000-8000-0000000000b1"
AGENTE_D = "cccccccc-0000-4000-8000-0000000000c1"
CHAVE_INTERNA_D = "chave-de-teste-096"


class _RespostaBancoD:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class _ConsultaBancoD:
    def __init__(self, banco, tabela):
        self.banco, self.tabela = banco, tabela
        self.filtros, self.op, self.carga = [], None, None

    def select(self, *a, **k):
        self.op = "select"; return self

    def insert(self, carga):
        self.op, self.carga = "insert", carga; return self

    def upsert(self, carga, on_conflict=None):
        self.op, self.carga = "upsert", carga; return self

    def update(self, carga):
        self.op, self.carga = "update", carga; return self

    def delete(self):
        self.op = "delete"; return self

    def eq(self, campo, valor):
        self.filtros.append((campo, valor)); return self

    def in_(self, campo, valores):
        self.filtros.append((campo, list(valores))); return self

    def limit(self, n): return self
    def order(self, *a, **k): return self
    def maybe_single(self): return self

    @staticmethod
    def _valor(linha, campo):
        if "->>" in campo:
            base, chave = campo.split("->>", 1)
            return (linha.get(base) or {}).get(chave)
        return linha.get(campo)

    def _casa(self, linha):
        for campo, valor in self.filtros:
            atual = self._valor(linha, campo)
            if isinstance(valor, list):
                if atual not in valor:
                    return False
            elif str(atual) != str(valor):
                return False
        return True

    async def execute(self):
        linhas = self.banco.dados.setdefault(self.tabela, [])
        if self.op == "select":
            return _RespostaBancoD([dict(l) for l in linhas if self._casa(l)])
        if self.op in ("insert", "upsert"):
            carga = self.carga if isinstance(self.carga, list) else [self.carga]
            saida = []
            for nova in carga:
                nova = dict(nova)
                existente = None
                if "id" in nova:
                    existente = next((l for l in linhas if str(l.get("id")) == str(nova["id"])), None)
                crid = (nova.get("payload") or {}).get("client_request_id")
                if crid and self.tabela == "messages":
                    for outra in linhas:
                        if str(outra.get("id")) == str(nova.get("id")):
                            continue
                        if (str(outra.get("conversation_id")) == str(nova.get("conversation_id"))
                                and outra.get("role") == nova.get("role")
                                and (outra.get("payload") or {}).get("client_request_id") == crid):
                            raise RuntimeError(
                                "23505 duplicate key value violates unique constraint "
                                "messages_turno_sem_duplicata_uidx")
                if existente is not None:
                    if self.op == "insert":
                        raise RuntimeError("23505 duplicate key value violates unique constraint")
                    existente.update(nova)
                    saida.append(dict(existente))
                else:
                    nova.setdefault("id", str(uuid.uuid4()))
                    linhas.append(nova)
                    saida.append(dict(nova))
            return _RespostaBancoD(saida)
        if self.op == "update":
            tocadas = [l for l in linhas if self._casa(l)]
            for l in tocadas:
                l.update(self.carga)
            return _RespostaBancoD([dict(l) for l in tocadas])
        if self.op == "delete":
            ficam = [l for l in linhas if not self._casa(l)]
            n = len(linhas) - len(ficam)
            linhas[:] = ficam
            return _RespostaBancoD([], count=n)
        raise AssertionError(self.op)


class BancoDubleD:
    def __init__(self, dados=None):
        self.dados = dados or {}

    def table(self, nome):
        return _ConsultaBancoD(self, nome)


def _banco_padrao_d(agentes=None, conversas=None):
    return BancoDubleD({
        "conversations": conversas if conversas is not None else [],
        "messages": [],
        "companies": [{"id": CO_ALFA_D, "name": "Corretora Alfa"},
                      {"id": CO_BETA_D, "name": "Corretora Beta"}],
        "agents": agentes if agentes is not None else
                  [{"id": AGENTE_D, "company_id": CO_ALFA_D, "widget_config": {}}],
        "artifacts": [],
    })


def _delta_d(texto):
    return {"kind": "delta", "text": texto}


# --- o grafo dublado desta camada: so o que `stream_agent_eventos` PROJETA --
EVENTOS_DO_GRAFO_D: list = []
CHAMADA_DO_GRAFO_D: dict = {}
CHAMADAS_BILLING_D: list = []
PODE_CONSUMIR_D = [True, "ok"]


async def _stream_agent_eventos_dublado(graph, **k):
    CHAMADA_DO_GRAFO_D.clear()
    CHAMADA_DO_GRAFO_D.update(k)
    for ev in EVENTOS_DO_GRAFO_D:
        if isinstance(ev, BaseException):
            raise ev
        if isinstance(ev, tuple) and ev and ev[0] == "sleep":
            await asyncio.sleep(ev[1])
            continue
        yield ev


async def _stream_agent_dublado(*a, **k):
    # 🔴 `stream_agent` do widget e chamado com `graph=...` em `k` (kwarg) --
    # nao passar `None` posicional aqui, senao vira "multiplos valores para
    # 'graph'". `_stream_agent_eventos_dublado(graph, **k)` aceita `graph`
    # tanto posicional (painel) quanto por kwarg (widget).
    async for ev in _stream_agent_eventos_dublado(**k):
        if ev.get("kind") == "delta":
            yield ev.get("text") or ""
        elif ev.get("kind") == "error":
            yield "\n\n[Erro interno no servidor durante a geracao da resposta.]"


def _pode_consumir_d(company_id):
    CHAMADAS_BILLING_D.append(str(company_id))
    return tuple(PODE_CONSUMIR_D)


class _GuardrailDubladoD:
    fail_close = True

    def __init__(self, **k):
        pass

    async def validate_input(self, texto):
        return (False, None, texto)


class _AgentServiceDubladoD:
    def __init__(self, banco):
        self._banco = banco

    def get_agent_by_id(self, aid):
        achado = next((a for a in self._banco.dados.get("agents", []) if str(a["id"]) == str(aid)), None)
        if achado is None:
            return None
        return types.SimpleNamespace(model_dump=lambda: dict(achado))


async def _get_or_create_graph_d(**k):
    return object()


def _montar_stubs_d(banco):
    """Devolve {nome_do_modulo: modulo} -- os LAZY imports de dentro de chat.py."""
    graph_mod = types.ModuleType("app.agents.graph")
    graph_mod.stream_agent = _stream_agent_dublado
    graph_mod.stream_agent_eventos = _stream_agent_eventos_dublado

    guardrails_mod = types.ModuleType("app.agents.guardrails")
    guardrails_mod.SmithGuardrail = _GuardrailDubladoD

    billing_mod = types.ModuleType("app.services.billing_gate")
    billing_mod.pode_consumir = _pode_consumir_d

    qdrant_mod = types.ModuleType("app.services.qdrant_service")
    qdrant_mod.get_qdrant_service = lambda: None

    vision_mod = types.ModuleType("app.services.vision_service")
    vision_mod.describe_image = None
    vision_mod.extract_document_text = None

    agent_service_mod = types.ModuleType("app.services.agent_service")
    agent_service_mod.AgentService = lambda: _AgentServiceDubladoD(banco)

    langchain_mod = types.ModuleType("app.services.langchain_service")
    langchain_mod.get_or_create_graph = _get_or_create_graph_d

    return {
        "app.agents.graph": graph_mod,
        "app.agents.guardrails": guardrails_mod,
        "app.services.billing_gate": billing_mod,
        "app.services.qdrant_service": qdrant_mod,
        "app.services.vision_service": vision_mod,
        "app.services.agent_service": agent_service_mod,
        "app.services.langchain_service": langchain_mod,
    }


class _TrocaModulosD:
    """Troca `sys.modules[nome]` pelos dubles -- e devolve os originais no __exit__."""

    def __init__(self, novos):
        self._novos = novos
        self._anteriores = {}

    def __enter__(self):
        for nome, mod in self._novos.items():
            self._anteriores[nome] = sys.modules.get(nome, _AUSENTE)
            sys.modules[nome] = mod
        return self

    def __exit__(self, *exc):
        for nome, anterior in self._anteriores.items():
            if anterior is _AUSENTE:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = anterior
        return False


def _montar_app_d(chat_mod, banco):
    from app.core.database import get_async_db
    from app.core.rate_limit import limiter
    # 🔴 o `limiter` e um SINGLETON global (`app.core.rate_limit.limiter`),
    # nunca recarregado -- sem resetar, o "100/minute" do `/chat/stream` some
    # sozinho depois de o suficiente de CENARIOS x MUTACOES na mesma janela,
    # e todo request vira 429 (a resposta some da leitura SSE em silencio).
    limiter.reset()
    aplicacao = FastAPI()
    aplicacao.include_router(chat_mod.router)
    aplicacao.dependency_overrides[get_async_db] = lambda: types.SimpleNamespace(client=banco)
    aplicacao.state.limiter = limiter
    return aplicacao


def _linhas_sse_d(texto):
    eventos = []
    for linha in texto.splitlines():
        if not linha.startswith("data: "):
            continue
        bruto = linha[6:].strip()
        if bruto == "[DONE]":
            eventos.append({"type": "[DONE]"})
            continue
        try:
            ev = json.loads(bruto)
        except Exception:  # noqa: BLE001
            eventos.append({"type": "__raw__", "texto": bruto})
            continue
        if "token" in ev and "type" not in ev:
            ev = dict(ev); ev["type"] = "__legado_token__"
        elif "error" in ev and "type" not in ev:
            ev = dict(ev); ev["type"] = "__legado_erro__"
        eventos.append(ev)
    return eventos


def bloco_D_endpoint(ctx):
    _p("\n[D] O TURNO PELO ENDPOINT -- chat_router de producao + banco/grafo dublados")

    chat_mod = ctx.get("chat_mod")
    graph_pronto = ctx["graph"] is not None and not isinstance(ctx["graph"], dict)
    ce_pronto = ctx["chat_eventos"] is not None and not isinstance(ctx["chat_eventos"], dict)

    if chat_mod is None or isinstance(chat_mod, dict) or not graph_pronto or not ce_pronto:
        motivo = razao_ausencia(chat_mod if isinstance(chat_mod, dict) else None,
                  "app/api/chat.py nao importa -- o BLOCO D nao pode subir o router de producao")
        for rotulo in ("[B4]", "[B5]", "[B6]", "[B7]", "[B8a]", "[B8b]", "[B8c]",
                       "[B10]", "[B12]", "[B13]"):
            devendo(False, "%s (execucao, bloco_D_endpoint) -- pre-requisito ausente" % rotulo,
                    "D", motivo)
        return

    async def _rodar_casos():
        # 🔴 `_modo_de_confianca` valida a chave contra `_chaves_internas()`
        # (settings.ADMIN_API_KEY / os.getenv), lidos NO MOMENTO da chamada --
        # setar aqui, e devolver no `finally` la embaixo, e suficiente (nao
        # precisa recarregar `app.core.settings`).
        # -------------------------------------------------------------
        # [B4] porteira bloqueia -> policy.blocked + turn.completed(failed),
        # ZERO insert/upsert em messages
        # -------------------------------------------------------------
        banco = _banco_padrao_d(conversas=[])
        with _TrocaModulosD(_montar_stubs_d(banco)):
            PODE_CONSUMIR_D[:] = [False, "sem credito (teste)"]
            EVENTOS_DO_GRAFO_D[:] = [_delta_d("nunca chega")]
            aplicacao = _montar_app_d(chat_mod, banco)
            crid = str(uuid.uuid4())
            sessao = str(uuid.uuid4())
            corpo = {"chatInput": "oi", "sessionId": sessao, "companyId": CO_ALFA_D,
                     "agentId": AGENTE_D, "client_request_id": crid}
            transporte = httpx.ASGITransport(app=aplicacao)
            async with httpx.AsyncClient(transport=transporte, base_url="http://t", timeout=30) as cliente:
                r = await cliente.post("/chat/stream", json=corpo,
                                       headers={"X-Internal-Key": CHAVE_INTERNA_D})
            eventos = _linhas_sse_d(r.text)
            tipos = [e.get("type") for e in eventos]
            bloqueios = [e for e in eventos if e.get("type") == "policy.blocked"]
            completados = [e for e in eventos if e.get("type") == "turn.completed"]
            certo(len(bloqueios) == 1 and bloqueios[0]["payload"].get("code") == "billing",
                  "[B4] porteira bloqueada -> exatamente 1 policy.blocked{code:'billing'}",
                  "tipos: %s" % tipos)
            certo(len(completados) == 1 and completados[0]["payload"].get("status") == "failed",
                  "[B4] porteira bloqueada -> turn.completed{status:'failed'}",
                  "completados: %s" % completados)
            certo(banco.dados["messages"] == [],
                  "[B4] porteira bloqueada -> ZERO insert/upsert em messages",
                  "messages: %s" % banco.dados["messages"])
            PODE_CONSUMIR_D[:] = [True, "ok"]

        # -------------------------------------------------------------
        # [B5] excecao apos 3 deltas -> error{code,correlation_id,message_human}
        # sem "segredo-XYZ"; linha gravada tem os 3 deltas + status failed +
        # error_code
        # -------------------------------------------------------------
        banco = _banco_padrao_d(conversas=[])
        with _TrocaModulosD(_montar_stubs_d(banco)):
            EVENTOS_DO_GRAFO_D[:] = [_delta_d("a"), _delta_d("b"), _delta_d("c"),
                                     RuntimeError("segredo-XYZ")]
            aplicacao = _montar_app_d(chat_mod, banco)
            crid = str(uuid.uuid4())
            sessao = str(uuid.uuid4())
            amid = str(uuid.uuid4())
            corpo = {"chatInput": "oi", "sessionId": sessao, "companyId": CO_ALFA_D,
                     "agentId": AGENTE_D, "client_request_id": crid, "assistantMessageId": amid}
            transporte = httpx.ASGITransport(app=aplicacao)
            async with httpx.AsyncClient(transport=transporte, base_url="http://t", timeout=30) as cliente:
                r = await cliente.post("/chat/stream", json=corpo,
                                       headers={"X-Internal-Key": CHAVE_INTERNA_D})
            certo("segredo-XYZ" not in r.text,
                  "[B5] a excecao crua (\"segredo-XYZ\") NUNCA aparece em nenhum evento",
                  "resposta: %s" % r.text[:400])
            eventos = _linhas_sse_d(r.text)
            erros = [e for e in eventos if e.get("type") == "error"]
            certo(len(erros) == 1
                  and set(("code", "correlation_id", "message_human")) <= set(erros[0].get("payload") or {})
                  and "segredo-XYZ" not in (erros[0]["payload"].get("message_human") or ""),
                  "[B5] error{code,correlation_id,message_human} -- sem a excecao crua",
                  "erros: %s" % erros)
            linhas = banco.dados["messages"]
            certo(bool(linhas) and linhas[0].get("content") == "abc",
                  "[B5] a linha gravada tem o CONTEUDO PARCIAL dos 3 deltas",
                  "linhas: %s" % linhas)
            if linhas:
                turno_gravado = (linhas[0].get("payload") or {}).get("turn") or {}
                certo(turno_gravado.get("status") == "failed" and turno_gravado.get("error_code"),
                      "[B5] a linha gravada tem payload.turn.status='failed' + error_code",
                      "turno gravado: %s" % turno_gravado)

        # -------------------------------------------------------------
        # [B10] heartbeat quando o gerador demora mais que o intervalo --
        # nunca dentro de content
        # -------------------------------------------------------------
        banco = _banco_padrao_d(conversas=[])
        with _TrocaModulosD(_montar_stubs_d(banco)):
            intervalo_original = chat_mod.SEGUNDOS_DE_BATIMENTO
            chat_mod.SEGUNDOS_DE_BATIMENTO = 0.05
            try:
                EVENTOS_DO_GRAFO_D[:] = [_delta_d("x"), ("sleep", 0.3), _delta_d("y")]
                aplicacao = _montar_app_d(chat_mod, banco)
                crid = str(uuid.uuid4())
                sessao = str(uuid.uuid4())
                corpo = {"chatInput": "oi", "sessionId": sessao, "companyId": CO_ALFA_D,
                         "agentId": AGENTE_D, "client_request_id": crid}
                transporte = httpx.ASGITransport(app=aplicacao)
                async with httpx.AsyncClient(transport=transporte, base_url="http://t", timeout=30) as cliente:
                    r = await cliente.post("/chat/stream", json=corpo,
                                           headers={"X-Internal-Key": CHAVE_INTERNA_D})
                eventos = _linhas_sse_d(r.text)
                tipos = [e.get("type") for e in eventos]
                certo("heartbeat" in tipos, "[B10] o heartbeat aparece quando o gerador demora",
                      "tipos: %s" % tipos)
                completado = next((e for e in eventos if e.get("type") == "assistant.content.completed"), None)
                certo(bool(completado) and completado["payload"].get("content") == "xy",
                      "[B10] o heartbeat nunca entra em content -- o conteudo final ainda e a concatenacao",
                      "completado: %s" % completado)
            finally:
                chat_mod.SEGUNDOS_DE_BATIMENTO = intervalo_original

        # -------------------------------------------------------------
        # o turno feliz com 1 tool -- a ORDEM pelo endpoint, [B12] e [B13]
        # -------------------------------------------------------------
        banco = _banco_padrao_d(conversas=[])
        with _TrocaModulosD(_montar_stubs_d(banco)):
            EVENTOS_DO_GRAFO_D[:] = [{"kind": "tool_start", "name": "listar_entregas"},
                                     {"kind": "tool_end", "name": "listar_entregas"},
                                     _delta_d("Oi"), _delta_d(" tudo"), _delta_d(" bem")]
            aplicacao = _montar_app_d(chat_mod, banco)
            crid = str(uuid.uuid4())
            sessao = str(uuid.uuid4())
            corpo = {"chatInput": "oi", "sessionId": sessao, "companyId": CO_ALFA_D,
                     "agentId": AGENTE_D, "client_request_id": crid}
            transporte = httpx.ASGITransport(app=aplicacao)
            async with httpx.AsyncClient(transport=transporte, base_url="http://t", timeout=30) as cliente:
                r = await cliente.post("/chat/stream", json=corpo,
                                       headers={"X-Internal-Key": CHAVE_INTERNA_D})
            eventos = _linhas_sse_d(r.text)
            tipos = [e.get("type") for e in eventos]
            completado = next((e for e in eventos if e.get("type") == "assistant.content.completed"), None)
            certo(bool(tipos) and tipos[0] == "turn.accepted" and tipos[-1] == "[DONE]"
                  and tipos[-2] == "turn.completed",
                  "[B3-D] a ordem pelo endpoint: turn.accepted ... turn.completed [DONE]",
                  "tipos: %s" % tipos)
            certo(bool(completado) and completado["payload"].get("content") == "Oi tudo bem",
                  "[B13] assistant.content.completed.payload.content == concatenacao exata dos deltas",
                  "completado: %s" % completado)
            linhas = banco.dados["messages"]
            certo(bool(linhas), "[B12] a linha do turno foi gravada", "messages: %s" % linhas)
            if linhas:
                turno_gravado = (linhas[0].get("payload") or {}).get("turn") or {}
                chaves_ok = (
                    "client_request_id" in turno_gravado and turno_gravado.get("status") == "complete"
                    and isinstance(turno_gravado.get("ttft_ms"), int) and turno_gravado.get("ttft_ms") >= 0
                    and isinstance(turno_gravado.get("total_ms"), int)
                    and isinstance(turno_gravado.get("stages"), list)
                    and isinstance(turno_gravado.get("artifacts"), list)
                    and "attempt" in turno_gravado
                )
                certo(chaves_ok,
                      "[B12] a linha gravada tem payload.turn com client_request_id/status/ttft_ms/"
                      "total_ms/stages/artifacts/attempt",
                      "turno gravado: %s" % turno_gravado)

        # -------------------------------------------------------------
        # [B6] o consumidor abandona (aclose no 2o evento) -> status 'complete'
        # -------------------------------------------------------------
        banco = _banco_padrao_d(conversas=[])
        with _TrocaModulosD(_montar_stubs_d(banco)):
            EVENTOS_DO_GRAFO_D[:] = [_delta_d("nao"), _delta_d("morre")]
            aplicacao = _montar_app_d(chat_mod, banco)
            crid = str(uuid.uuid4())
            sessao = str(uuid.uuid4())
            corpo = {"chatInput": "oi", "sessionId": sessao, "companyId": CO_ALFA_D,
                     "agentId": AGENTE_D, "client_request_id": crid}
            transporte = httpx.ASGITransport(app=aplicacao)
            async with httpx.AsyncClient(transport=transporte, base_url="http://t", timeout=30) as cliente:
                lidas = 0
                async with cliente.stream("POST", "/chat/stream", json=corpo,
                                          headers={"X-Internal-Key": CHAVE_INTERNA_D}) as resp:
                    async for linha in resp.aiter_lines():
                        if linha.startswith("data: "):
                            lidas += 1
                        if lidas >= 2:
                            break
                await asyncio.sleep(0.2)
            linhas = banco.dados["messages"]
            turno_gravado = (linhas[0].get("payload") or {}).get("turn") if linhas else {}
            certo(bool(linhas) and turno_gravado.get("status") == "complete",
                  "[B6] o consumidor abandona o stream -- a linha gravada tem status 'complete'",
                  "linhas: %s" % linhas)

        # -------------------------------------------------------------
        # [B7] POST /chat/stop durante um gerador lento -> 200 e status
        # 'interrupted' + payload.turn.stopped_by
        # -------------------------------------------------------------
        banco = _banco_padrao_d(conversas=[])
        with _TrocaModulosD(_montar_stubs_d(banco)):
            EVENTOS_DO_GRAFO_D[:] = [_delta_d("parte1"), ("sleep", 0.4), _delta_d("nunca chega")]
            aplicacao = _montar_app_d(chat_mod, banco)
            crid = str(uuid.uuid4())
            sessao = str(uuid.uuid4())
            corpo = {"chatInput": "oi", "sessionId": sessao, "companyId": CO_ALFA_D,
                     "agentId": AGENTE_D, "client_request_id": crid}
            transporte = httpx.ASGITransport(app=aplicacao)
            status_do_stop = {}
            async with httpx.AsyncClient(transport=transporte, base_url="http://t", timeout=30) as cliente:
                # 🔴 `.stream()` + leitura parcial nao garante que o STOP chegue
                # ANTES do fim: com ASGITransport o corpo pode so comecar a ser
                # entregue quando o gerador do turno ja tiver terminado (o mesmo
                # loop de eventos). O que garante a janela e rodar as DUAS
                # requisicoes CONCORRENTES (`asyncio.gather`): o POST completo a
                # /chat/stream so retorna quando o SSE fechar ([DONE]), e o Stop
                # dispara 50ms depois de lancado -- bem dentro do `sleep(0.4)`
                # em que a task `_gerar` esta presa.
                async def _chamar_stream():
                    return await cliente.post("/chat/stream", json=corpo,
                                              headers={"X-Internal-Key": CHAVE_INTERNA_D})

                async def _chamar_stop_depois():
                    await asyncio.sleep(0.05)
                    return await cliente.post(
                        "/chat/stop",
                        json={"client_request_id": crid, "company_id": CO_ALFA_D},
                        headers={"X-Internal-Key": CHAVE_INTERNA_D})

                r, r_stop = await asyncio.gather(_chamar_stream(), _chamar_stop_depois())
            status_do_stop["stopped"] = r_stop.status_code
            status_do_stop["corpo"] = r_stop.json() if r_stop.status_code == 200 else r_stop.text
            certo(status_do_stop.get("stopped") == 200
                  and isinstance(status_do_stop.get("corpo"), dict)
                  and status_do_stop["corpo"].get("status") == "interrupted",
                  "[B7] POST /chat/stop devolve 200 {status:'interrupted'}",
                  "resposta do stop: %s" % status_do_stop)
            linhas = banco.dados["messages"]
            turno_gravado = (linhas[0].get("payload") or {}).get("turn") if linhas else {}
            certo(bool(linhas) and turno_gravado.get("status") == "interrupted"
                  and turno_gravado.get("stopped_by"),
                  "[B7] a linha gravada tem status 'interrupted' e payload.turn.stopped_by",
                  "turno gravado: %s" % turno_gravado)

        # -------------------------------------------------------------
        # [B8a] sem X-Internal-Key + userId no corpo -> modo widget, userId
        # NAO chega ao dublado; com chave valida -> modo painel, userId chega
        # -------------------------------------------------------------
        banco = _banco_padrao_d(conversas=[])
        with _TrocaModulosD(_montar_stubs_d(banco)):
            EVENTOS_DO_GRAFO_D[:] = [_delta_d("oi")]
            aplicacao = _montar_app_d(chat_mod, banco)
            sessao = str(uuid.uuid4())
            user_id = str(uuid.uuid4())
            corpo_sem_chave = {"chatInput": "oi", "sessionId": sessao, "companyId": CO_ALFA_D,
                               "agentId": AGENTE_D, "userId": user_id}
            transporte = httpx.ASGITransport(app=aplicacao)
            async with httpx.AsyncClient(transport=transporte, base_url="http://t", timeout=30) as cliente:
                r_widget = await cliente.post("/chat/stream", json=corpo_sem_chave)
                userid_widget = CHAMADA_DO_GRAFO_D.get("user_id")
                eventos_widget = _linhas_sse_d(r_widget.text)
                tem_forma_legado = any(e.get("type") == "__legado_token__" for e in eventos_widget)

                EVENTOS_DO_GRAFO_D[:] = [_delta_d("oi")]
                sessao2 = str(uuid.uuid4())
                crid2 = str(uuid.uuid4())
                corpo_com_chave = {"chatInput": "oi", "sessionId": sessao2, "companyId": CO_ALFA_D,
                                   "agentId": AGENTE_D, "userId": user_id, "client_request_id": crid2}
                r_painel = await cliente.post("/chat/stream", json=corpo_com_chave,
                                              headers={"X-Internal-Key": CHAVE_INTERNA_D})
                userid_painel = CHAMADA_DO_GRAFO_D.get("user_id")
                eventos_painel = _linhas_sse_d(r_painel.text)
                tem_forma_painel = any(e.get("type") == "turn.accepted" for e in eventos_painel)
            certo(tem_forma_legado and userid_widget is None,
                  "[B8a] sem X-Internal-Key -> modo widget (forma legada) e o userId NAO chega ao motor",
                  "userId capturado: %r · legado: %s" % (userid_widget, tem_forma_legado))
            certo(tem_forma_painel and userid_painel == user_id,
                  "[B8a] com X-Internal-Key valida -> modo painel e o userId CHEGA ao motor",
                  "userId capturado: %r · painel: %s" % (userid_painel, tem_forma_painel))

        # -------------------------------------------------------------
        # [B8b] dois tenants: companyId do CORPO = Beta, agentId de ALFA ->
        # o turno roda com a company do DONO DO AGENTE (Alfa), sem chave
        # -------------------------------------------------------------
        banco = _banco_padrao_d(
            agentes=[{"id": AGENTE_D, "company_id": CO_ALFA_D, "widget_config": {}}],
            conversas=[])
        with _TrocaModulosD(_montar_stubs_d(banco)):
            del CHAMADAS_BILLING_D[:]
            EVENTOS_DO_GRAFO_D[:] = [_delta_d("oi")]
            aplicacao = _montar_app_d(chat_mod, banco)
            sessao = str(uuid.uuid4())
            corpo = {"chatInput": "oi", "sessionId": sessao, "companyId": CO_BETA_D,
                     "agentId": AGENTE_D}
            transporte = httpx.ASGITransport(app=aplicacao)
            async with httpx.AsyncClient(transport=transporte, base_url="http://t", timeout=30) as cliente:
                await cliente.post("/chat/stream", json=corpo)
            company_no_motor = CHAMADA_DO_GRAFO_D.get("company_id")
            certo(company_no_motor == CO_ALFA_D
                  and (not CHAMADAS_BILLING_D or CHAMADAS_BILLING_D[-1] == CO_ALFA_D),
                  "[B8b] widget: o companyId do CORPO (Beta) e IGNORADO -- o turno roda com a "
                  "company DONA do agentId (Alfa)",
                  "company no motor: %r · billing: %s" % (company_no_motor, CHAMADAS_BILLING_D))

        # -------------------------------------------------------------
        # [B8c] session_id de conversa de OUTRA company -> policy.blocked,
        # nada gravado
        # -------------------------------------------------------------
        sessao_de_outra = str(uuid.uuid4())
        banco = _banco_padrao_d(conversas=[{"id": "conv-de-outra", "session_id": sessao_de_outra,
                                            "status": "open", "unread_count": 0,
                                            "company_id": CO_BETA_D}])
        with _TrocaModulosD(_montar_stubs_d(banco)):
            EVENTOS_DO_GRAFO_D[:] = [_delta_d("nunca chega")]
            aplicacao = _montar_app_d(chat_mod, banco)
            crid = str(uuid.uuid4())
            corpo = {"chatInput": "oi", "sessionId": sessao_de_outra, "companyId": CO_ALFA_D,
                     "agentId": AGENTE_D, "client_request_id": crid}
            transporte = httpx.ASGITransport(app=aplicacao)
            async with httpx.AsyncClient(transport=transporte, base_url="http://t", timeout=30) as cliente:
                r = await cliente.post("/chat/stream", json=corpo,
                                       headers={"X-Internal-Key": CHAVE_INTERNA_D})
            eventos = _linhas_sse_d(r.text)
            bloqueios = [e for e in eventos if e.get("type") == "policy.blocked"]
            certo(len(bloqueios) == 1 and banco.dados["messages"] == [],
                  "[B8c] session_id de conversa de OUTRA company -> policy.blocked, nada gravado",
                  "bloqueios: %s · messages: %s" % (bloqueios, banco.dados["messages"]))

    _env_anterior = os.environ.get("ADMIN_API_KEY")
    os.environ["ADMIN_API_KEY"] = CHAVE_INTERNA_D
    try:
        asyncio.run(_rodar_casos())
    except Exception as exc:  # noqa: BLE001
        certo(False, "[D] o BLOCO D rodou sem estourar (nenhum caso estourou fora do esperado)",
              "%s: %s" % (type(exc).__name__, str(exc)[:400]))
    finally:
        if _env_anterior is None:
            os.environ.pop("ADMIN_API_KEY", None)
        else:
            os.environ["ADMIN_API_KEY"] = _env_anterior


# ===========================================================================
# BLOCO C -- CONTROLE: o guarda sabe falhar, e a arvore ficou limpa
# ===========================================================================
def bloco_C_controle(ctx):
    _p("\n[C] CONTROLE -- o guarda sabe falhar, e nada ficou para tras")

    par(True, "o placar CONSEGUE reprovar", "")
    certo(os.environ.get("SEM_REDE") == "1",
          "a rede estava fechada durante a medicao", "SEM_REDE=%r" % os.environ.get("SEM_REDE"))
    try:
        socket.socket().connect(("198.51.100.7", 80))
        certo(False, "o bloqueio de rede esta em pe", "uma conexao externa passou")
    except RuntimeError:
        certo(True, "o bloqueio de rede esta em pe")
    except Exception as exc:  # noqa: BLE001
        certo(False, "o bloqueio de rede esta em pe",
              "a conexao falhou por outra razao (%s)" % type(exc).__name__)

    sobrando = [rel(os.path.join(RAIZ, c)) for c, *_ in MUTACOES
                if os.path.exists(os.path.join(RAIZ, c + ".bak-096"))]
    certo(not sobrando, "nenhuma copia `.bak-096` ficou na arvore",
          "sobraram: %s" % ", ".join(sobrando))

    # ⛔ Nenhuma fixture deste arquivo carrega dado de pessoa.
    fonte_do_guarda = io.open(os.path.abspath(__file__), encoding="utf-8", errors="replace").read()
    proibidos = re.findall(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\b\d{11}\b|\b55\d{10,11}\b", fonte_do_guarda)
    certo(not proibidos, "nenhum CPF/telefone nas fixtures deste guarda", "achei: %s" % proibidos[:3])
    amostra = ".".join(["123", "456", "789"]) + "-01"
    par(bool(re.findall(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", amostra)),
        "o detector de CPF CONSEGUE achar um CPF", "o detector nao acha um CPF nem quando ele esta la")

    # Nenhuma entrada de MUTACOES aponta para um caminho fantasma (o caminho pode
    # ainda nao existir -- e VERMELHO ESPERADO no --mutar, nao aqui; mas o
    # diretorio pai tem de ser real, senao a mutacao nunca aplicaria).
    for c, *_ in MUTACOES:
        pai = os.path.dirname(os.path.join(RAIZ, c))
        certo(os.path.isdir(pai), "o diretorio de %s existe (a mutacao tem onde aplicar)" % c,
              "diretorio ausente: %s" % rel(pai))


# ===========================================================================
# O contexto
# ===========================================================================
def montar_contexto():
    ctx = {}
    ce = modulo_opt("app/api/chat_eventos.py", "app.api.chat_eventos")
    ctx["chat_eventos"] = ce
    # graph.py existe; importar pode puxar langgraph. Tentamos, e se falhar,
    # caimos para a leitura de FONTE (que ja cobre o gate zero (ix)).
    ctx["graph"] = modulo_opt("app/agents/graph.py", "app.agents.graph")
    ctx["nomes_de_tools"] = nomes_de_tools()
    # 🔴 P0-1/P1-1: `app.api.chat` real -- o router de PRODUCAO que o bloco D
    # sobe com banco/grafo dublados. Precisa da casca de `app.services` com
    # AudioService/LangChainService (ver `_cascas()`) para o `from app.services
    # import ...` do topo de chat.py nao quebrar.
    ctx["chat_mod"] = modulo_opt("app/api/chat.py", "app.api.chat")
    return ctx


def _rodar(ctx):
    bloco_gate_zero(ctx)
    bloco_B_protocolo(ctx)
    bloco_B_grafo(ctx)
    bloco_A_turno(ctx)
    bloco_D_endpoint(ctx)


# ===========================================================================
# As mutacoes por COPIA -- so com `--mutar`
# ===========================================================================
def rodar_mutacoes(ctx):
    _p("\n[M] MUTACOES POR COPIA -- a arvore precisa estar parada")
    for caminho, de, para, rotulo in MUTACOES:
        alvo = os.path.join(RAIZ, caminho)
        if not os.path.exists(alvo):
            pular("mutacao %s (%s)" % (rotulo, caminho), "o arquivo ainda nao existe (o builder ainda nao escreveu)")
            continue
        original = io.open(alvo, encoding="utf-8", errors="replace").read()
        if de not in original:
            pular("mutacao %s (%s)" % (rotulo, caminho),
                  "a ancora %r nao existe -- mutacao que nao aplica NAO e mutacao passada" % de[:50])
            continue
        backup = alvo + ".bak-096"
        shutil.copyfile(alvo, backup)
        try:
            io.open(alvo, "w", encoding="utf-8").write(original.replace(de, para, 1))
            # 🔴 CONSERTO (1): compara o CONJUNTO de nomes que falharam antes x
            # depois -- nao a contagem crua de FAIL (que so cresce enquanto a
            # lista de VERMELHO ESPERADO nao estiver vazia, e faria QUALQUER
            # mutacao "acusar" mesmo sem relacao com ela).
            # 🔴 CONSERTO (2): `NOMES_FALHOS` e limpo ANTES de cada mutacao --
            # senao um rotulo que uma mutacao ANTERIOR ja tinha feito falhar
            # (ex.: a B8a/X-Internal-Key tambem derruba os dois [B7] do Stop,
            # que dependem do MESMO `_modo_de_confianca`) nunca mais conta como
            # "novo" para a mutacao SEGUINTE que o deveria pegar -- e essa
            # mutacao pareceria carimbo, quando na verdade o guarda ACUSA (so
            # nao com um nome que ainda nao existia).
            NOMES_FALHOS.clear()
            antes_nomes = set(NOMES_FALHOS)
            novos: list = []
            try:
                ctx["remedir"]()
                depois_nomes = set(NOMES_FALHOS)
                novos = sorted(depois_nomes - antes_nomes)
                ficou_vermelho = bool(novos)
            except RuntimeError as exc:
                if "MUTACAO_QUEBROU_O_MODULO" not in str(exc):
                    raise
                _p("        o arquivo mutado NAO carrega: o produto nem sobe -- VERMELHO")
                ficou_vermelho = True
            if novos:
                _p("        nomes NOVOS que ficaram vermelhos: %s" % "; ".join(novos))
            elif ficou_vermelho:
                _p("        (o modulo mutado nao carregou -- nenhuma assercao rodou)")
            else:
                _p("        nenhum nome novo ficou vermelho")
            par(ficou_vermelho, "mutacao %s em %s" % (rotulo, rel(alvo)),
                "a mutacao foi aplicada e NENHUM NOME NOVO ficou vermelho -- o bloco %s e carimbo" % rotulo)
        finally:
            shutil.copyfile(backup, alvo)
            os.remove(backup)


def main():
    global OK, FAIL
    mutar = "--mutar" in sys.argv or os.environ.get("AUTOBROKERS_MUTAR") == "1"

    _p("=" * 78)
    _p("  O CHAT FALA TIPADO -- o guarda do MOTOR  (SPEC-096)")
    _p("=" * 78)

    _abrir_o_ambiente()
    _fechar_a_rede()
    try:
        ctx = montar_contexto()

        def remedir():
            # 🔴 CONSERTO: `app.api.chat` precisa entrar aqui TAMBEM -- senao uma
            # mutacao em chat.py (policy.blocked, X-Internal-Key, interrupted)
            # nunca chegaria ao bloco_D_endpoint, que roda sobre o MODULO ja
            # importado (nao sobre o texto do arquivo). A ORDEM importa:
            # chat_eventos e graph primeiro (chat.py os importa no topo/lazy).
            for nome in ("app.api.chat_eventos", "app.agents.graph", "app.api.chat"):
                if nome in sys.modules and getattr(sys.modules[nome], "__file__", None):
                    try:
                        importlib.reload(sys.modules[nome])
                    except Exception as exc:  # noqa: BLE001
                        raise RuntimeError("MUTACAO_QUEBROU_O_MODULO %s: %s" % (nome, type(exc).__name__)) from exc
            _rodar(montar_contexto())

        ctx["remedir"] = remedir
        _rodar(ctx)
        if mutar:
            rodar_mutacoes(ctx)
        else:
            _p("\n[M] MUTACOES POR COPIA -- NAO rodaram (sem `--mutar`).")
            _p("      ⛔ Elas escrevem em `backend/app/`, e dois builders escrevem la em")
            _p("      paralelo. Com a arvore parada: `--mutar`. A lista declarada esta em")
            _p("      `MUTACOES`, no topo deste arquivo (%d entradas)." % len(MUTACOES))
        bloco_C_controle(ctx)
    finally:
        _abrir_a_rede()
        _restaurar_sys_modules()

    de_verdade = FAIL - len(ESPERADOS)
    _p("\n" + "=" * 78)
    _p("  %d ok · %d falhas (%d VERMELHO ESPERADO + %d de verdade) · %d pulados"
       % (OK, FAIL, len(ESPERADOS), de_verdade, len(PULADOS)))
    if ESPERADOS:
        _p("\n  🔴 VERMELHO ESPERADO -- a SPEC-096 PREVE estes ate o bloco citado.")
        _p("     O GATE ZERO desta SPEC (§4 BLOCO 0.1) e esta lista em `e1494ab`.")
        for x in ESPERADOS:
            _p("     · %s" % x)
    if de_verdade > 0:
        _p("\n  ⛔ HA %d VERMELHO DE VERDADE acima -- procure as linhas `[FALHOU]`." % de_verdade)
    if JA_PODEM_VIRAR:
        _p("\n  ✅ ESTES JA FICARAM VERDES. O integrador troca `devendo(...)` por `certo(...)`:")
        for x in JA_PODEM_VIRAR:
            _p("     · %s" % x)
    if PULADOS:
        _p("\n  -- pulados (%d): %s" % (len(PULADOS), " · ".join(PULADOS)))
    _p("=" * 78)
    if ESPERADOS and de_verdade == 0:
        _p("  (exit 0 com %d VERMELHO ESPERADO e 0 de verdade: o gate FINAL da SPEC-096\n"
           "   so fecha com a lista acima VAZIA -- protocolo v11.2, opcao B)" % len(ESPERADOS))
    return 1 if de_verdade else 0


def test_o_chat_fala_tipado():
    """🔴 A prova nasceu ANTES do codigo (protocolo §4, opcao B)."""
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
