# -*- coding: utf-8 -*-
r"""G6 · G9 — O MODELO TEM RELÓGIO.
SPEC-EXTRA-001.8 BLOCO C (§7, §12).

🔴 **O defeito, medido.** 📊 21/09/2026, de dentro de `backend/`:
`grep -n "timeout\|max_retries" app/factories/llm_factory.py` devolvia **ZERO**
linhas, e `grep -rn "httpx.AsyncClient(" app` mostrava **4** clientes sem teto
algum. Uma chamada pendurada ao modelo segurava a vaga de atendimento até o SDK
desistir por conta própria — e enquanto isso a mensagem da OUTRA corretora
esperava atrás dela.

```
 [G6a] O TETO NO OBJETO   os 4 construtores, pela FÁBRICA REAL -> o teto e as
                          voltas lidos no ATRIBUTO do objeto (nome medido por
                          classe), nunca no fonte. CONTROLE: teto 0 -> sem kwarg
 [G6b] ZERO SEM TETO      nenhum httpx.AsyncClient( em app/ sem `timeout`,
                          contando os de VÁRIAS LINHAS
 [G6c] O SILÊNCIO         ⛔ nenhum wait_for TOTAL em volta do astream_events
                          (regressão da SPEC-096)
 [G9a] 401 NÃO REPETE     e_transitorio(401) é False, e o SDK do objeto que a
                          fábrica construiu faz UMA requisição só.
                          LINHA DE CONTROLE: o MESMO caminho com 500 faz TRÊS
 [G9b] O BREAKER          abre na 5ª falha, a 6ª não sai; depois de T passa UMA
                          sonda (a segunda é barrada); sucesso fecha
 [G9c] REDIS FORA         fail-open: deixa passar e nada levanta
 [G9d] FULL JITTER        mesma volta, valores diferentes, sempre <= teto
```

⛔ SEGURANÇA: zero chamada real a modelo, zero crédito gasto, zero rede. As
chaves são literais falsas passadas por PARÂMETRO — nunca o `.env`. O
transporte é um `httpx.MockTransport`, que responde sem abrir socket.

Rodar (de dentro de `backend/`):
    PYTHONIOENCODING=utf-8 python tests/test_o_modelo_tem_relogio.py
    PYTHONIOENCODING=utf-8 python -m pytest tests/test_o_modelo_tem_relogio.py -q
    ... --so G9b   ·   ... --mutar   ·   ... --mutar M-C3
"""
from __future__ import annotations

import asyncio
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../backend
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ["SEM_REDE"] = "1"

PASS = 0
FAIL = 0

#: ⛔ 100% FALSA. Não existe em provedor nenhum, e não vem do ambiente.
CHAVE_FALSA = "chave-falsa-de-teste-nao-existe"

import httpx  # noqa: E402
from langchain_core.messages import HumanMessage  # noqa: E402


# ===========================================================================
# 🔴 O DUBLÊ DO BANCO VEM **ANTES** DA FÁBRICA — e é por medição, não por zelo
# ===========================================================================
#
# 📊 Achado em 21/09/2026: `LLMFactory.create_llm` constrói um
# `CostCallbackHandler`, que chama `get_usage_service()`, que chama
# `get_supabase_client()` — um cliente Supabase **de verdade**, com a
# `SUPABASE_URL` do ambiente (`llm_factory.py:155` → `cost_callback.py:46` →
# `usage_service.py:102` → `database.py:210`, pilha lida com o construtor
# instrumentado). Com uma URL morta o gate ficava verde sem consultar nada; com
# uma chave fora do formato JWT ele explodia em `SupabaseException: Invalid API
# key`. Um guarda que só passa porque o endereço está quebrado não é um guarda.
#
# ⛔ `usage_service` faz `from ..core.database import get_supabase_client` no
# topo, então o nome é trocado NOS DOIS módulos: trocar só num deles deixaria o
# caminho vivo pelo outro.
class _BancoMudo:
    """Um banco que responde VAZIO a tudo. Zero rede, zero linha."""

    class _Consulta:
        data: list = []

        def __getattr__(self, _nome):
            return lambda *a, **k: self

        def execute(self):
            return self

    client = None

    def table(self, _nome):
        return self._Consulta()


def _dublar_o_banco():
    import app.core.database as _db
    import app.services.usage_service as _uso

    _db.get_supabase_client = lambda: _BancoMudo()
    _uso.get_supabase_client = _db.get_supabase_client


_dublar_o_banco()

import app.core.relogio_do_modelo as R  # noqa: E402
from app.factories.llm_factory import LLMFactory  # noqa: E402

# 🔴 SPEC-116 F2 (CLAUDE.md §9.3 — a lição migra): a fábrica só constrói o que o
# CATÁLOGO governa. `gemini-2.0-flash` é HISTORICAL e o OpenRouter não tem linha
# no snapshot: este guarda passou a construir um Gemini governado e uma linha de
# OpenRouter no DUBLÊ do banco das rotas. O que ele prova não mudou: o teto e as
# voltas chegam aos QUATRO construtores.
import json as _json  # noqa: E402

from app.factories import model_policy as _MP  # noqa: E402

_SNAP = _json.loads(_MP.SNAPSHOT_PATH.read_text(encoding="utf-8"))
_CAT = dict(_SNAP["catalogo"])
_CAT["meta-llama/llama-3.1-8b-instruct"] = {
    "model_name": "meta-llama/llama-3.1-8b-instruct", "provider": "openrouter", "tipo": "chat",
    "api_surface": "chat_completions", "lifecycle": "CANDIDATE",
    "classes_de_dado": ["publico", "interno", "pii"], "capacidades": {}}
_MP.leitor_do_banco = lambda: (_CAT, _SNAP["papeis"])
_MP.limpar_cache()

#: O produto, guardado antes de qualquer dublê — é para cá que os gates voltam.
_CLIENTE_ORIGINAL = R._cliente
_AGORA_ORIGINAL = R._agora


def _p(texto):
    try:
        print(texto)
    except UnicodeEncodeError:
        cod = getattr(sys.stdout, "encoding", None) or "ascii"
        print(str(texto).encode(cod, "replace").decode(cod, "replace"))


def check(nome, cond, detalhe=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        _p("  [ok] %s" % nome)
    else:
        FAIL += 1
        _p("  [FALHOU] %s" % nome + ("\n         %s" % str(detalhe)[:700] if detalhe else ""))
    return bool(cond)


def _construir(provedor, modelo):
    """O objeto que o PRODUTO usa — pela função pública da fábrica real."""
    return LLMFactory.create_llm(
        company_config={},
        agent_data={"llm_provider": provedor, "llm_model": modelo},
        api_key=CHAVE_FALSA,
        company_id="11111111-1111-1111-1111-111111111111",
    )


# ⚠️ O NOME DO ATRIBUTO É MEDIDO, NÃO PRESUMIDO. 📊 21/09/2026,
# `python -c "from langchain_openai import ChatOpenAI; print(ChatOpenAI.model_fields)"`
# (e as outras duas classes) nas versões instaladas — langchain-openai 1.0.3,
# langchain-anthropic 1.1.0, langchain-google-genai 3.1.0:
#     ChatOpenAI              campo `request_timeout`         alias `timeout`
#     ChatAnthropic           campo `default_request_timeout` alias `timeout`
#     ChatGoogleGenerativeAI  campo `timeout`                 alias `request_timeout`
# Ler o fonte da fábrica provaria só que a LINHA existe; ler o atributo prova
# que o kwarg CHEGOU na classe com o nome que ela entende.
OS_QUATRO = [
    ("openai", "gpt-4o", "request_timeout"),
    ("anthropic", "claude-sonnet-5", "default_request_timeout"),
    ("google", "gemini-3-flash-preview", "timeout"),
    ("openrouter", "meta-llama/llama-3.1-8b-instruct", "request_timeout"),
]


# ===========================================================================
# G6a — o teto e as voltas, lidos no OBJETO
# ===========================================================================
def g6a():
    _p("\n[G6a] O TETO NO OBJETO -- os 4 construtores pela fabrica real")
    for provedor, modelo, campo in OS_QUATRO:
        llm = _construir(provedor, modelo)
        teto = getattr(llm, campo, None)
        check("%s: %s = %s (esperado %s)" % (provedor, campo, teto, R.TIMEOUT_S),
              teto == R.TIMEOUT_S, "objeto=%s" % type(llm).__name__)
        check("%s: max_retries = %s (esperado %s)" % (provedor, llm.max_retries, R.MAX_RETRIES),
              llm.max_retries == R.MAX_RETRIES)

    # 🔴 O ELO QUE A COSTURA VAI USAR: o provedor que a fábrica despachou é o
    # MESMO nome que `provedor_configurado` devolve. Se os dois discordarem, a
    # costura pergunta ao breaker de um provedor e a chamada sai por outro.
    for provedor, modelo, _campo in OS_QUATRO:
        agente = {"llm_provider": provedor, "llm_model": modelo}
        llm = _construir(provedor, modelo)
        sensor = [c for c in llm.callbacks if isinstance(c, R.RelogioDoModeloCallback)]
        check("%s: o sensor do breaker esta anexado" % provedor, len(sensor) == 1)
        if sensor:
            check("%s: fabrica e costura concordam no nome do provedor" % provedor,
                  sensor[0].provedor == R.provedor_configurado({}, agente),
                  "fabrica=%s costura=%s" % (sensor[0].provedor,
                                             R.provedor_configurado({}, agente)))

    # ⚠️ LINHA DE CONTROLE — o guarda CONSEGUE ver a ausência? Com o relógio
    # desligado (o rollback escrito na §7.1) o kwarg NÃO é passado e o atributo
    # volta a ser o do SDK. Sem esta linha, um guarda que sempre lê 90 poderia
    # estar lendo um default de biblioteca.
    original = R.TIMEOUT_S
    try:
        R.TIMEOUT_S = 0
        llm = _construir("openai", "gpt-4o")
        check("CONTROLE: LLM_TIMEOUT_SEGUNDOS=0 -> nenhum teto passado (%s)"
              % getattr(llm, "request_timeout", None),
              getattr(llm, "request_timeout", None) is None)
    finally:
        R.TIMEOUT_S = original
    check("CONTROLE: o teto voltou (%s)" % R.TIMEOUT_S, R.TIMEOUT_S > 0)


# ===========================================================================
# G6b — zero httpx.AsyncClient sem teto, inclusive os de várias linhas
# ===========================================================================
#
# ⚠️ CLAUDE.md §9.4 exige que o teste chame o MOTOR. A exceção escrita lá vale
# aqui: o alvo NÃO é o comportamento do httpx, é a FORMA da declaração no fonte
# — "nenhum cliente nasce sem teto". Por isso a varredura é legítima; o que ela
# não pode é dar falso verde, e é por isso que ela conta PARÊNTESES em vez de
# olhar uma linha só.
def _clientes_sem_teto(raiz_app, total=None):
    achados = []
    for pasta, _dirs, arquivos in os.walk(raiz_app):
        if "__pycache__" in pasta:
            continue
        for nome in arquivos:
            if not nome.endswith(".py"):
                continue
            caminho = os.path.join(pasta, nome)
            texto = io.open(caminho, encoding="utf-8").read()
            for m in re.finditer(r"httpx\.AsyncClient\(", texto):
                if total is not None:
                    total.append(1)
                i = m.end() - 1          # no '('
                nivel, j = 0, i
                while j < len(texto):    # fecha o parêntese, atravessando linhas
                    if texto[j] == "(":
                        nivel += 1
                    elif texto[j] == ")":
                        nivel -= 1
                        if nivel == 0:
                            break
                    j += 1
                argumentos = texto[i + 1:j]
                if "timeout" not in argumentos:
                    linha = texto[:m.start()].count("\n") + 1
                    achados.append("%s:%d" % (os.path.relpath(caminho, RAIZ).replace("\\", "/"),
                                              linha))
    return achados


def g6b():
    _p("\n[G6b] ZERO httpx.AsyncClient SEM TETO em app/")
    raiz_app = os.path.join(RAIZ, "app")
    total = []
    sem_teto = _clientes_sem_teto(raiz_app, total)
    # ⚠️ Antes de acreditar no zero: o varredor ACHOU alguma coisa? Um regex
    # quebrado também devolve zero — e passaria por guarda.
    check("o varredor enxerga os clientes de app/ (%d encontrados)" % len(total),
          len(total) >= 30, total)
    check("nenhum cliente sem timeout (achados: %d)" % len(sem_teto),
          not sem_teto, " · ".join(sem_teto))

    # ⚠️ LINHA DE CONTROLE — o varredor SABE ler um cliente de várias linhas?
    # Se ele não soubesse, contaria como "sem teto" os que declaram o timeout na
    # linha de baixo, e o número acima seria alto por engano.
    with tempfile.TemporaryDirectory() as tmp:
        io.open(os.path.join(tmp, "a.py"), "w", encoding="utf-8").write(
            "import httpx\n"
            "async def f():\n"
            "    async with httpx.AsyncClient(\n"
            "        timeout=httpx.Timeout(30.0, connect=10.0),\n"
            "        follow_redirects=False,\n"
            "    ) as c:\n"
            "        pass\n"
            "    async with httpx.AsyncClient(follow_redirects=True) as c2:\n"
            "        pass\n")
        controle = _clientes_sem_teto(tmp)
        check("CONTROLE: o de varias linhas COM teto nao e acusado, o sem teto e"
              " (achados=%d)" % len(controle), len(controle) == 1, controle)


# ===========================================================================
# G6c — o relógio do streaming é de SILÊNCIO, nunca um teto total
# ===========================================================================
def g6c():
    _p("\n[G6c] O SILENCIO -- nenhum wait_for TOTAL em volta do astream_events")
    caminho = os.path.join(RAIZ, "app", "agents", "graph.py")
    texto = io.open(caminho, encoding="utf-8").read()
    linhas = texto.splitlines()
    alvos = [i for i, l in enumerate(linhas) if "astream_events(" in l and "#" not in l.split("astream_events")[0]]
    check("o produto ainda chama astream_events (%d chamada(s))" % len(alvos), len(alvos) >= 1)
    suspeitas = []
    for i in alvos:
        # 🔴 Um `wait_for` em volta de um turno que está EMITINDO delta corta a
        # resposta boa pela metade — é a regressão da SPEC-096. O relógio certo
        # é tempo SEM PROGRESSO, uma camada abaixo (o `read` do httpx, §7.1).
        janela = "\n".join(linhas[max(0, i - 6):i + 1])
        if "wait_for" in janela:
            suspeitas.append(i + 1)
    check("nenhum wait_for total envolvendo o stream (linhas: %s)" % (suspeitas or "-"),
          not suspeitas)


# ===========================================================================
# G9a — 401 não é transitório, e não sai uma segunda requisição
# ===========================================================================
def _responder(status, chamadas):
    def handler(request):
        chamadas.append(str(request.url.path))
        return httpx.Response(status, json={"error": {"message": "dublê", "type": "x"}})
    return handler


def _chamar_com_transporte(status):
    """Chama o objeto que a FÁBRICA construiu, com a rede dublada na borda.

    ⛔ `MockTransport` responde sem abrir socket: nenhum byte sai da máquina e
    nenhum crédito é gasto. Trocamos só o TRANSPORTE — o cliente, a política de
    retry e o objeto são os de produção.
    """
    chamadas = []
    alvo = _construir("openai", "gpt-4o")
    # Sem streaming a resposta do dublê é um JSON só; a política de retry e o
    # teto são exatamente os mesmos objetos.
    alvo.streaming = False
    alvo.root_async_client._client._transport = httpx.MockTransport(_responder(status, chamadas))

    async def rodar():
        try:
            await alvo.ainvoke([HumanMessage(content="oi")])
            return None
        except Exception as exc:  # noqa: BLE001
            return exc

    erro = asyncio.run(rodar())
    return erro, chamadas


def g9a():
    _p("\n[G9a] 401 NAO REPETE -- e o 500 repete (linha de controle)")
    erro401, chamadas401 = _chamar_com_transporte(401)
    check("401 levanta erro (%s)" % type(erro401).__name__, erro401 is not None)
    check("401 -> UMA requisicao so (foram %d)" % len(chamadas401), len(chamadas401) == 1)
    check("e_transitorio(401) e False", R.e_transitorio(erro401) is False,
          type(erro401).__name__)

    # 🔴 LINHA DE CONTROLE: o contador CONSEGUE passar de 1? Sem isto, um
    # cliente quebrado que nunca chama nada daria "1 requisição" e passaria.
    erro500, chamadas500 = _chamar_com_transporte(500)
    check("CONTROLE: 500 -> %d requisicoes (1 + LLM_MAX_RETRIES=%d)"
          % (len(chamadas500), R.MAX_RETRIES), len(chamadas500) == R.MAX_RETRIES + 1)
    check("e_transitorio(500) e True", R.e_transitorio(erro500) is True,
          type(erro500).__name__)

    # A classificação, caso a caso — é ela que o breaker usa.
    class _Status(Exception):
        def __init__(self, code):
            super().__init__(str(code))
            self.status_code = code

    for code, esperado in ((400, False), (401, False), (403, False), (404, False),
                           (408, True), (429, True), (500, True), (503, True)):
        check("HTTP %d -> transitorio=%s" % (code, esperado),
              R.e_transitorio(_Status(code)) is esperado)
    check("timeout de leitura e transitorio",
          R.e_transitorio(httpx.ReadTimeout("x")) is True)
    check("erro de conexao e transitorio",
          R.e_transitorio(httpx.ConnectError("x")) is True)
    # 🔴 Um defeito NOSSO não pode abrir o breaker de um provedor.
    check("ValueError (defeito nosso) NAO e transitorio",
          R.e_transitorio(ValueError("chave ausente")) is False)
    # Embrulhado: o SDK levanta `from` o erro de baixo.
    embrulhado = RuntimeError("falhou")
    embrulhado.__cause__ = httpx.ConnectTimeout("x")
    check("erro EMBRULHADO em transitorio e transitorio",
          R.e_transitorio(embrulhado) is True)


# ===========================================================================
# G9b/G9c — o breaker por provedor
# ===========================================================================
RELOGIO = [1000.0]


def _andar(segundos):
    RELOGIO[0] += segundos


class _RedisQueExplode:
    def __getattr__(self, _nome):
        async def _boom(*a, **k):
            raise RuntimeError("redis fora")
        return _boom


def _breaker_limpo():
    """Zera o estado e prende o breaker num Redis de MEMÓRIA com relógio nosso.

    ⚠️ O dublê é o `_RedisDeMemoria` DO PRODUTO — o mesmo degrau que roda quando
    o Redis falta de verdade. Um dublê escrito no teste provaria o dublê.
    """
    R._MEMORIA.clear()
    R._agora = lambda: RELOGIO[0]
    memoria = R._RedisDeMemoria(R._MEMORIA)

    async def _cliente_de_memoria():
        return memoria
    R._cliente = _cliente_de_memoria
    return memoria


class _Erro500(Exception):
    status_code = 500


class _Erro401(Exception):
    status_code = 401


def g9b():
    _p("\n[G9b] O BREAKER -- abre na 5a, a 6a nao sai, uma sonda depois de T")
    _breaker_limpo()
    prov = "anthropic"

    async def cenario():
        resultados = {}
        for i in range(R.BREAKER_FALHAS - 1):
            await R.registrar_falha(prov, _Erro500())
        resultados["antes_da_quinta"] = await R.provedor_disponivel(prov)
        await R.registrar_falha(prov, _Erro500())
        resultados["depois_da_quinta"] = await R.provedor_disponivel(prov)
        resultados["outro_provedor"] = await R.provedor_disponivel("openai")
        resultados["estado"] = await R.estado_do_breaker(prov)

        # Ainda dentro da janela de espera: continua barrado.
        _andar(R.BREAKER_SEGUNDOS - 5)
        resultados["quase_no_prazo"] = await R.provedor_disponivel(prov)

        # Passou o prazo: MEIO-ABERTO — UMA sonda passa, a segunda não.
        _andar(10)
        resultados["sonda_1"] = await R.provedor_disponivel(prov)
        resultados["sonda_2"] = await R.provedor_disponivel(prov)
        resultados["estado_meio"] = await R.estado_do_breaker(prov)

        # A sonda deu certo: fecha para todo mundo.
        await R.registrar_sucesso(prov)
        resultados["depois_do_sucesso"] = await R.provedor_disponivel(prov)
        resultados["estado_fim"] = await R.estado_do_breaker(prov)
        return resultados

    r = asyncio.run(cenario())
    check("com %d falhas ainda passa" % (R.BREAKER_FALHAS - 1), r["antes_da_quinta"] is True)
    check("na %da falha o breaker ABRE e a chamada seguinte NAO sai" % R.BREAKER_FALHAS,
          r["depois_da_quinta"] is False, r["estado"])
    check("estado = aberto", r["estado"]["estado"] == "aberto", r["estado"])
    # 🔴 ISOLAMENTO: a queda de um provedor não pode calar os outros.
    check("o OUTRO provedor continua liberado", r["outro_provedor"] is True)
    check("antes de T continua barrado", r["quase_no_prazo"] is False)
    check("depois de T passa UMA sonda", r["sonda_1"] is True, r["estado_meio"])
    check("e a SEGUNDA e barrada (uma sonda, nao uma enxurrada)", r["sonda_2"] is False)
    check("sucesso FECHA o breaker", r["depois_do_sucesso"] is True)
    check("estado final = fechado", r["estado_fim"]["estado"] == "fechado", r["estado_fim"])

    # A sonda que FALHA reabre o relógio inteiro (senão o provedor caído seria
    # sondado de 30 em 30 s para sempre).
    _breaker_limpo()

    async def sonda_que_falha():
        for _ in range(R.BREAKER_FALHAS):
            await R.registrar_falha(prov, _Erro500())
        _andar(R.BREAKER_SEGUNDOS + 1)
        passou = await R.provedor_disponivel(prov)
        await R.registrar_falha(prov, _Erro500())
        return passou, await R.provedor_disponivel(prov)

    passou, depois = asyncio.run(sonda_que_falha())
    check("a sonda passa", passou is True)
    check("a sonda que FALHA reabre (segue barrado)", depois is False)

    # 🔴 O DEFEITO DO TITULO DA SPEC: 401 e coisa da CHAVE, nao queda de
    # provedor. 📊 hoje a chave e global (`app/core/utils.py:38-49`), mas no dia
    # em que for por corretora, um 401 de UMA abriria o provedor para TODAS.
    _breaker_limpo()

    async def so_401():
        for _ in range(R.BREAKER_FALHAS * 3):
            await R.registrar_falha(prov, _Erro401())
        return await R.provedor_disponivel(prov), await R.estado_do_breaker(prov)

    livre, estado = asyncio.run(so_401())
    check("%d erros 401 NAO abrem o breaker do provedor" % (R.BREAKER_FALHAS * 3),
          livre is True, estado)


def g9c():
    _p("\n[G9c] REDIS FORA -- fail-open, e nada levanta")
    R._MEMORIA.clear()
    R._AVISOU_SEM_REDIS[0] = False

    # (1) O Redis não sobe: `_cliente` degrada para memória, sem levantar.
    # ⚠️ O `_cliente` aqui é o DO PRODUTO, devolvido ao lugar depois que o G9b
    # o trocou pelo dublê — senão este gate testaria o dublê do gate anterior.
    import app.core.redis as redis_mod
    R._cliente = _CLIENTE_ORIGINAL
    R._agora = _AGORA_ORIGINAL
    original = redis_mod.get_async_redis_client

    async def _recusa():
        raise ConnectionError("redis fora")
    redis_mod.get_async_redis_client = _recusa

    async def sem_redis():
        cliente = await R._cliente()
        livre = await R.provedor_disponivel("openai")
        await R.registrar_falha("openai", _Erro500())   # não pode levantar
        await R.registrar_sucesso("openai")             # não pode levantar
        estado = await R.estado_do_breaker("openai")
        return cliente, livre, estado

    try:
        cliente, livre, estado = asyncio.run(sem_redis())
        check("sem Redis o breaker degrada para memoria (%s)" % type(cliente).__name__,
              isinstance(cliente, R._RedisDeMemoria))
        check("sem Redis provedor_disponivel devolve True (fail-open)", livre is True)
        check("sem Redis nada levanta (estado=%s)" % estado["estado"], True)
    except Exception as exc:  # noqa: BLE001
        check("sem Redis nada levanta", False, "%s: %s" % (type(exc).__name__, exc))
    finally:
        redis_mod.get_async_redis_client = original

    # (2) O Redis responde, mas TODO comando explode: ainda assim, passa.
    async def _cliente_explosivo():
        return _RedisQueExplode()
    R._cliente = _cliente_explosivo
    try:
        livre = asyncio.run(R.provedor_disponivel("openai"))
        check("Redis que explode em todo comando -> ainda deixa passar", livre is True)
        asyncio.run(R.registrar_falha("openai", _Erro500()))
        check("e registrar_falha nao levanta", True)
    except Exception as exc:  # noqa: BLE001
        check("Redis que explode nao derruba o atendimento", False,
              "%s: %s" % (type(exc).__name__, exc))


# ===========================================================================
# G9d — full jitter
# ===========================================================================
def g9d():
    _p("\n[G9d] FULL JITTER -- mesma volta, valores diferentes, sempre <= teto")
    amostras = [R.espera_do_backoff(2) for _ in range(40)]
    check("a mesma volta da valores DIFERENTES (%d distintos em 40)" % len(set(amostras)),
          len(set(amostras)) > 30, amostras[:5])
    check("nenhuma espera negativa", all(a >= 0 for a in amostras))
    for n in (1, 2, 3, 6, 12):
        teto = min(R.BACKOFF_BASE_S * (2 ** (n - 1)), R.BACKOFF_TETO_S)
        valores = [R.espera_do_backoff(n) for _ in range(60)]
        check("volta %d: tudo <= %.1fs (max %.2fs)" % (n, teto, max(valores)),
              max(valores) <= teto + 1e-9)
    check("volta 12 nunca passa do teto de %.0fs" % R.BACKOFF_TETO_S,
          max(R.espera_do_backoff(12) for _ in range(60)) <= R.BACKOFF_TETO_S)
    check("volta 0 nao espera", R.espera_do_backoff(0) == 0.0)


GATES = {"G6a": g6a, "G6b": g6b, "G6c": g6c, "G9a": g9a, "G9b": g9b,
         "G9c": g9c, "G9d": g9d}


# ===========================================================================
# AS MUTACOES — por COPIA, em SUBPROCESSO. A arvore precisa estar parada.
# ===========================================================================
REL = "app/core/relogio_do_modelo.py"
FAB = "app/factories/llm_factory.py"
MCP = "app/mcp_servers/base_server.py"

MUTACOES = [
    # (a) um construtor sem o relógio = a vaga presa pelo tempo do SDK
    ("M-C1", FAB,
     "        llm_params.update(kwargs_de_relogio())\n\n        return ChatOpenAI(**llm_params)",
     "        pass  # MUTACAO\n\n        return ChatOpenAI(**llm_params)",
     "G6a"),
    # (b) um cliente http de volta ao "espera para sempre"
    ("M-C2", MCP,
     "async with httpx.AsyncClient(timeout=timeout_http()) as client:",
     "async with httpx.AsyncClient() as client:  # MUTACAO",
     "G6b"),
    # (c) 🔴 tratar TUDO como transitório = repetir o 401 e abrir o breaker do
    #     provedor por causa da chave de UMA corretora
    ("M-C3", REL,
     "    vistos: set = set()\n    atual: Optional[BaseException] = exc",
     "    return True  # MUTACAO\n    vistos: set = set()\n"
     "    atual: Optional[BaseException] = exc",
     "G9b"),
    # (d) breaker SEM meio-aberto: passado o prazo, todo mundo entra de uma vez
    ("M-C4", REL,
     '    await cliente.set(meio, "1", ex=BREAKER_SEGUNDOS + BREAKER_MEIO_S)',
     "    pass  # MUTACAO",
     "G9b"),
    # (e) fail-open virando fail-closed: o Redis cai e o atendimento cala
    ("M-C5", REL,
     '        logger.warning("[RelogioDoModelo] breaker indisponível (%s) — deixando "\n'
     '                       "passar", type(exc).__name__)\n        return True',
     "        raise  # MUTACAO",
     "G9c"),
    # (f) backoff FIXO: todo mundo volta no mesmo segundo
    ("M-C6", REL,
     "    return random.uniform(0.0, teto)",
     "    return teto  # MUTACAO",
     "G9d"),
    # (g) o teto TOTAL de volta em cima do stream = a regressão da SPEC-096
    ("M-C7", "app/agents/graph.py",
     "                    async for event in graph.astream_events(estado_da_volta, config, version=\"v1\"):",
     "                    _t = asyncio.wait_for(None, timeout=120)  # MUTACAO\n"
     "                    async for event in graph.astream_events(estado_da_volta, config, version=\"v1\"):",
     "G6c"),
]


def _rodar(gate):
    return subprocess.run(
        [sys.executable, os.path.abspath(__file__), "--so", gate],
        # 🔴 `text=True` sozinho decodifica com a codepage do Windows e ESTOURA
        # no primeiro emoji: `r.stdout` volta vazio e uma mutacao VERMELHA e
        # contada como verde.
        cwd=RAIZ, capture_output=True, text=True, timeout=900,
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"},
    )


def rodar_mutacoes(filtro=None):
    _p("\n[MUT] MUTACOES POR COPIA -- cada uma em SUBPROCESSO. A arvore precisa estar parada.")
    vermelhas = verdes = 0
    for mid, relativo, de, para, gate in MUTACOES:
        if filtro and mid != filtro:
            continue
        caminho = os.path.normpath(os.path.join(RAIZ, relativo))
        original = io.open(caminho, encoding="utf-8").read()
        if de not in original:
            _p("  [FALHOU] %s: a ancora nao existe em %s -- mutacao NAO aplicada "
               "NAO e mutacao passada" % (mid, relativo))
            verdes += 1
            continue
        base = _rodar(gate)
        backup = tempfile.NamedTemporaryFile(delete=False, suffix=".bak-c-g6").name
        shutil.copyfile(caminho, backup)
        try:
            io.open(caminho, "w", encoding="utf-8", newline="\n").write(
                original.replace(de, para, 1))
            r = _rodar(gate)
            falhas = [l.strip() for l in (r.stdout or "").splitlines() if "[FALHOU]" in l]
            if base.returncode == 0 and r.returncode != 0 and falhas:
                vermelhas += 1
                _p("  [ok] %s deixa %s VERMELHO: %s" % (mid, gate, falhas[0][:180]))
            else:
                verdes += 1
                _p("  [FALHOU] %s NAO deixou %s vermelho (base rc=%s, mutado rc=%s)\n%s"
                   % (mid, gate, base.returncode, r.returncode, (r.stdout or r.stderr)[-900:]))
        finally:
            shutil.copyfile(backup, caminho)
            os.unlink(backup)
            assert io.open(caminho, encoding="utf-8").read() == original, \
                "restauracao falhou em " + relativo
    _p("\n  PLACAR DAS MUTACOES: %d vermelhas - %d verdes" % (vermelhas, verdes))
    return verdes == 0


def main():
    args = sys.argv[1:]
    if "--mutar" in args:
        i = args.index("--mutar")
        filtro = args[i + 1] if len(args) > i + 1 and args[i + 1].startswith("M-") else None
        return 0 if rodar_mutacoes(filtro) else 1

    so = args[args.index("--so") + 1] if "--so" in args else None
    if not so:
        _p("=" * 78)
        _p("  G6 G9 -- O MODELO TEM RELOGIO  (SPEC-EXTRA-001.8 BLOCO C)")
        _p("=" * 78)
    for gid, fn in GATES.items():
        if so and gid != so:
            continue
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            import traceback
            check("%s EXPLODIU (defeito do guarda ou do produto)" % gid, False,
                  "%s: %s\n%s" % (type(exc).__name__, exc, traceback.format_exc()[-900:]))
    if not so:
        _p("\n" + "=" * 78)
        _p("  %d assercoes verdes - %d vermelhas" % (PASS, FAIL))
        _p("=" * 78)
    return 1 if FAIL else 0


def _instalar_os_dubles():
    """Os dublês DESTE guarda (banco do ledger + catálogo com o OpenRouter)."""
    _dublar_o_banco()
    _MP.leitor_do_banco = lambda: (_CAT, _SNAP["papeis"])
    _MP.limpar_cache()


def test_o_modelo_tem_relogio():
    # 🔴 (conserto único): os dublês eram instalados SÓ no import do módulo. No
    # pytest, a coleta importa todos os módulos antes de rodar — 📊 com
    # `test_llm_temperature_guard.py` na mesma sessão o `leitor_do_banco` dele
    # vencia e o G6a caía em "meta-llama/llama-3.1-8b-instruct fora do catálogo".
    # Agora o teste instala os SEUS na hora de rodar e devolve os de antes.
    import app.core.database as _db
    import app.services.usage_service as _uso

    # E o breaker: 📊 o G9c deixava `R._cliente` num Redis que EXPLODE em todo
    # comando (fail-open) — o teste seguinte da sessão via o disjuntor sempre
    # "fechado" (`test_buffer_segue_pela_reserva_e_retem_sem_ela` caía, também
    # no HEAD). Devolve o cliente, o relógio e a memória do breaker.
    antes = (_MP.leitor_do_banco, _db.get_supabase_client, _uso.get_supabase_client)
    breaker = (R._cliente, R._agora, dict(R._MEMORIA), R.TIMEOUT_S)
    _instalar_os_dubles()
    try:
        assert main() == 0
    finally:
        _MP.leitor_do_banco, _db.get_supabase_client, _uso.get_supabase_client = antes
        _MP.limpar_cache()
        R._cliente, R._agora, memoria, R.TIMEOUT_S = breaker
        R._MEMORIA.clear()
        R._MEMORIA.update(memoria)


if __name__ == "__main__":
    sys.exit(main())
