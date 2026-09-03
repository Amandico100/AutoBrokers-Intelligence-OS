# -*- coding: utf-8 -*-
"""O sinistro deixa rastro — o guarda da SPEC-093-B (BLOCO E + o GATE ZERO do 0-bis).

🔴 **ESTE ARQUIVO NASCE VERMELHO, E É PARA NASCER.** Ele foi escrito ANTES do código
(protocolo §4: quem faz a prova não faz a resposta). O gate ⓪ — o ELO da SPEC — mede
que uma mensagem de sinistro atravessa o webhook **no modo observação** e abre a
sombra. Hoje nenhuma sombra abre, então ⓪ REPROVA, `main()` devolve **1** e o `def
test_` do pytest FALHA. Isso não se afrouxa: `CLAUDE.md` §9.3 — um guarda que fica
verde por conveniência é um carimbo.

⚠️ A saída separa **VERMELHO ESPERADO (até o BLOCO A/B/C)** de **VERMELHO DE VERDADE**.
O exit code é 1 nos dois casos. Quando um "vermelho esperado" ficar verde, o guarda
IMPRIME a instrução de trocar `vermelho_ate(...)` por `certo(...)` — é assim que ele
não passa a guardar verdade vencida.

O ELO que esta SPEC prova, e por que ele precisava de gate próprio
------------------------------------------------------------------
📊 Medido em 03/09/2026 (aquecimento da 093-B, §1.2): `attendance_agent_active()` é
falso em **4 de 4** agentes `attendance`. Com ele falso, `webhook.py` grava a mensagem,
espelha e **`return`** na linha 782, antes de `langchain_service.process_message`
(`:826`). **O grafo não roda em produção.** Um gancho de detecção escrito depois desse
`return` provaria um caminho que nenhuma mensagem percorre. O gate ⓪ existe para que
essa mentira específica seja impossível — e ele mede das duas formas, porque cada uma
pega o que a outra não pega:

    dinâmico     roda `process_whatsapp_message_background` DE VERDADE, com o cliente
                 Supabase falso e `attendance_agent_active` forçado a False, e olha
                 as linhas que sobraram no falso
    estrutural   lê `webhook.py` como texto e exige que a chamada da sombra esteja
                 ACIMA da linha do `return` do modo observação

Os blocos, e o que cada um mata
--------------------------------
```
 [0] GATE ZERO      0-bis①  a mensagem percorre o webhook EM SILÊNCIO e a sombra abre
 [1] VOCABULÁRIO    B⑤      um arquivo, 11 eventos, ator do CHECK real (nunca `human`)
 [2] DETECÇÃO       A①②③⑥  o detector separa sinistro de "terceiro andar"; a chave é a conversa
 [3] LEDGER         B①②③⑥  evento LIDO DO BANCO, payload só de enum, sem PII, sem texto
 [4] DOIS TENANTS   A④B④C⑥  a sombra da A não aparece no filtro da B — e a consulta EXECUTA
 [5] VARIANTES      C①②③④  N≥3; permutação é OUTRA variante; dedupe estável; denominador
 [6] PRAZOS         C⑤      nenhum `30` solto; 2026 e 2027 por caminhos diferentes
 [7] SEM TEXTO      §2 ref⑦ nenhum `content`/`text`/`body` copiado para payload
 [8] AGENT_TASKS    C⑦      o trabalhador `sombra_sinistros` existe e o workflow tem card
 [9] REGRESSÃO      §10     a linha de base do atendimento, medida HOJE, como SCRIPT
[10] CONTROLE GERAL         este guarda consegue ficar vermelho?
```

📊 A LINHA DE BASE DA REGRESSÃO, medida em 03/09/2026 nesta árvore, ANTES do código
da 093-B (`git rev-parse HEAD` → `3be076d` no instante da medição; a branch
`feat/spec093b-o-sinistro-deixa-rastro` avançou depois com o BLOCO 0-bis ② de outro
builder, que não toca o atendimento):
```
python backend/tests/test_a_maquina_de_lavar_vai_ate_o_fim.py
    exit 0 · "112 assercoes verdes - 0 vermelhas"
python backend/tests/test_golden_do_eletricista.py
    exit 1 · "14 PROBLEMA(S)" · exatamente 1 caso EXPLODIU (gold_007: KeyError 'live')
```
⚠️ **A §10 da SPEC diz "1 vermelho" e o número medido é 14.** Os dois se referem a
coisas diferentes: **1** é o CASO que explode (`gold_007`), **14** é o total de
asserções vermelhas do arquivo. O guarda [9] afirma os DOIS, porque só o par distingue
"a sombra quebrou um caso" de "a sombra quebrou uma asserção" (CLAUDE.md §12.1).

⛔ Este arquivo NUNCA imprime CPF, telefone, apólice, placa ou nome de pessoa. O banco
é lido só por SELECT, e sem credencial o bloco PULA com a razão escrita. Os textos das
fixtures são INVENTADOS — nenhum veio do acervo de um segurado.

As mutações obrigatórias do BLOCO E (o executor roda, restaura por cópia)
-------------------------------------------------------------------------
```
M1  faça um escritor gravar o texto do segurado no payload → [3] e [7] VERMELHOS
M2  remova a ordenação da assinatura da variante           → [5] gate ② VERMELHO
    (X e a permutação de X passam a ser a mesma variante)
M3  tire o filtro de company_id da leitura da sombra       → [4] VERMELHO
M4  mova o gancho para DEPOIS do `return` do modo observação → [0] VERMELHO nos dois
    caminhos (estrutural e dinâmico)
```
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import subprocess
import sys
import types
import urllib.error
import urllib.parse
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../backend
REPO = os.path.dirname(RAIZ)
APP = os.path.join(RAIZ, "app")
WEBHOOK = os.path.join(APP, "api", "webhook.py")
CLAIMS_SHADOW = os.path.join(APP, "services", "claims_shadow.py")
PRAZOS_PY = os.path.join(APP, "services", "prazos_regulatorios.py")
VOCAB = os.path.join(REPO, "lib", "atendimento", "claims-shadow-vocab.json")

if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


def _carregar_env():
    """`app.core.config` valida as settings no import e lê o `.env` pelo CWD.

    Rodando de `backend/` funciona; rodando da raiz do repo levantava `ValidationError`
    e o guarda PULAVA — um guarda pulado por causa do diretório de trabalho é um guarda
    que não guarda. ⛔ Nenhum valor é impresso: presença/ausência, nunca o segredo.
    """
    env = os.path.join(RAIZ, ".env")
    if not os.path.exists(env):
        return
    for linha in io.open(env, encoding="utf-8", errors="replace"):
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        k, v = linha.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_carregar_env()


def _cascas_de_pacote():
    """Deixa os SUBMÓDULOS de `app` serem importados sem executar os `__init__`.

    📊 Medido em 03/09/2026: `from app.services.intelligence.redaction_service import
    contem_pii` morria em `app/services/__init__.py`, que importa 14 serviços — e um
    deles puxa `fastembed`. O módulo alvo importa **só `re`**. Sem esta casca, TODOS
    os blocos deste guarda pulavam com a razão errada (`No module named 'fastembed'`)
    em vez da razão verdadeira (`o BLOCO A ainda não existe`), e um guarda que mente
    sobre o motivo do skip é pior que um guarda que pula.

    ⛔ A casca tem o `__path__` REAL: nenhum código nosso é falsificado — só o
    `__init__` do pacote deixa de rodar.
    """
    for sub in ("api", "services", "agents", "tasks", "factories", "core"):
        nome = "app." + sub
        atual = sys.modules.get(nome)
        if atual is not None and getattr(atual, "__file__", None) is None:
            continue          # já é casca
        casca = types.ModuleType(nome)
        casca.__path__ = [os.path.join(APP, sub)]
        sys.modules[nome] = casca


try:
    import app  # noqa: F401
    _cascas_de_pacote()
except Exception:  # noqa: BLE001
    pass

# ---------------------------------------------------------------------------
# 🔴 OS NOMES QUE ESTE GUARDA IMPORTA — concentrados aqui de propósito.
# O código foi escrito em paralelo (protocolo §4). Se um nome sair diferente, o
# INTEGRADOR muda AQUI, e em nenhum outro lugar do arquivo.
# ⚠️ Import ausente NUNCA mata o guarda: o bloco PULA com a razão escrita.
# ---------------------------------------------------------------------------
detectar_sinistro = abrir_sombra = registrar_evento = None
variantes_de = contadores_de = None
espera_vencida = PRAZOS = None
criar_registro_sem_fila = None
agente_por_id = workflow_keys_sem_card = None
contem_pii = None

_FALTA_SOMBRA = _FALTA_PRAZOS = _FALTA_RUNS = _FALTA_HB = _FALTA_PII = ""
try:
    from app.services.claims_shadow import (  # type: ignore  # noqa: F401
        abrir_sombra,
        contadores_de,
        detectar_sinistro,
        registrar_evento,
        variantes_de,
    )
except Exception as _e:  # noqa: BLE001
    _FALTA_SOMBRA = "app.services.claims_shadow: %s: %s" % (type(_e).__name__, _e)
try:
    from app.services.prazos_regulatorios import PRAZOS, espera_vencida  # type: ignore  # noqa: F401,F811
except Exception as _e:  # noqa: BLE001
    _FALTA_PRAZOS = "app.services.prazos_regulatorios: %s: %s" % (type(_e).__name__, _e)
try:
    from app.services.work.runs import criar_registro_sem_fila  # type: ignore  # noqa: F401,F811
except Exception as _e:  # noqa: BLE001
    _FALTA_RUNS = "app.services.work.runs.criar_registro_sem_fila: %s: %s" % (
        type(_e).__name__, _e)
try:
    from app.core.heartbeat import agente_por_id, workflow_keys_sem_card  # type: ignore  # noqa: F401,F811
except Exception as _e:  # noqa: BLE001
    _FALTA_HB = "app.core.heartbeat: %s: %s" % (type(_e).__name__, _e)
try:
    from app.services.intelligence.redaction_service import contem_pii  # type: ignore  # noqa: F401,F811
except Exception as _e:  # noqa: BLE001
    _FALTA_PII = "app.services.intelligence.redaction_service: %s: %s" % (
        type(_e).__name__, _e)


# ---------------------------------------------------------------------------
# O placar — a forma de `test_a_central_diz_a_verdade.py`
# ---------------------------------------------------------------------------
OK = FAIL = 0
PULADOS: list = []
ESPERADOS: list = []       # vermelhos que a SPEC PREVÊ até o bloco correspondente
JA_PODEM_VIRAR: list = []  # os que ficaram verdes: o integrador troca a chamada


def _p(texto):
    """Impressão à prova do console do Windows (cp1252). Um guarda que morre por
    causa da fonte do terminal não guarda."""
    try:
        print(texto)
    except UnicodeEncodeError:
        cod = getattr(sys.stdout, "encoding", None) or "ascii"
        print(texto.encode(cod, "replace").decode(cod, "replace"))


def certo(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        _p("  ok    %s" % rotulo)
    else:
        FAIL += 1
        _p("  FALHA %s" % rotulo + ("\n        %s" % detalhe if detalhe else ""))


def vermelho_ate(cond, rotulo, bloco, detalhe=""):
    """🔴 Vermelho PREVISTO pela SPEC — e mesmo assim vermelho.

    Diferente do `certo_xfail` da SPEC-088 de propósito: lá a falha esperada NÃO
    contava e o guarda podia sair verde. Aqui ela CONTA, o exit code é 1, e é isso
    que impede alguém de declarar a 093-B verde com a sombra inexistente.

    Quando ficar verde, o guarda imprime a instrução: trocar por `certo(...)`. Um
    `vermelho_ate` que virou verde e ficou é verdade vencida guardada (§9.3).
    """
    global OK, FAIL
    if cond:
        OK += 1
        _p("  ok    %s" % rotulo)
        JA_PODEM_VIRAR.append("%s   [era vermelho_ate('%s')]" % (rotulo, bloco))
    else:
        FAIL += 1
        ESPERADOS.append("%s   (esperado ate %s)" % (rotulo, bloco))
        _p("  VERMELHO-ESPERADO %s   (ate %s)" % (rotulo, bloco)
           + ("\n        %s" % detalhe if detalhe else ""))


def pular(rotulo, razao):
    PULADOS.append(rotulo)
    _p("  --    PULADO %s\n        %s" % (rotulo, razao))


def ler(p):
    return io.open(p, encoding="utf-8", errors="replace").read()


def sha256_de(caminho):
    return hashlib.sha256(io.open(caminho, "rb").read()).hexdigest()


# ---------------------------------------------------------------------------
# O BANCO REAL — só SELECT, e sem credencial o bloco PULA com a razão escrita
# ---------------------------------------------------------------------------
def _credencial():
    url = os.environ.get("SUPABASE_URL")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
           or os.environ.get("SUPABASE_SERVICE_KEY")
           or os.environ.get("SUPABASE_KEY"))
    return (url.rstrip("/") if url else None), (key or None)


def _get(caminho, timeout=30, contar=False):
    """GET no PostgREST. Devolve (status, corpo, total). Nunca levanta."""
    url, key = _credencial()
    if not url or not key:
        return None, None, None
    cab = {"apikey": key, "Authorization": "Bearer " + key}
    if contar:
        cab["Prefer"] = "count=exact"
    req = urllib.request.Request(url + "/rest/v1/" + caminho, headers=cab)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            faixa = r.headers.get("content-range") or ""
            total = None
            if "/" in faixa:
                cauda = faixa.split("/")[-1]
                total = int(cauda) if cauda.isdigit() else None
            return r.status, json.loads(r.read().decode()), total
    except urllib.error.HTTPError as e:
        return e.code, None, None
    except Exception:  # noqa: BLE001
        return None, None, None


# ---------------------------------------------------------------------------
# O CLIENTE SUPABASE FALSO — o coração dos blocos [0] e [3]
#
# 🔴 Por que ele existe, e não um mock por função: o gate B① da SPEC exige que o
# evento seja LIDO DO BANCO (ou do cliente falso), **nunca do retorno da função**.
# 📊 `dispatch_router._evento` (:578-581) engole a exceção do INSERT: um evento
# recusado pelo CHECK de `actor_type` some sem erro e a função devolve `None`
# alegremente. Testar o retorno provaria que a função foi CHAMADA; só a LINHA prova
# que ela GRAVOU.
# ---------------------------------------------------------------------------
class _Resposta:
    """Resposta do PostgREST — e também `await`-ável.

    ⚠️ `dispatch_router` faz `await db.client.table(...).insert(...).execute()`; o
    webhook faz `asyncio.to_thread(lambda: ...execute())`. Os dois estilos existem no
    código vivo, então o falso atende os dois em vez de escolher um e obrigar o
    builder a escrever para o teste.
    """

    def __init__(self, data):
        self.data = list(data or [])
        self.count = len(self.data)

    def __await__(self):
        async def _entrega():
            return self
        return _entrega().__await__()


class _Tabela:
    def __init__(self, banco, nome):
        self._banco = banco
        self._nome = nome
        self._filtros = []
        self._op = "select"
        self._linha = None

    def select(self, *a, **k):
        self._op = "select"
        return self

    def insert(self, linha, **k):
        self._op = "insert"
        self._linha = linha
        for x in (linha if isinstance(linha, list) else [linha]):
            self._banco.inseridos.append((self._nome, dict(x)))
        return self

    def upsert(self, linha, **k):
        return self.insert(linha, **k)

    def update(self, linha, **k):
        self._op = "update"
        self._linha = linha
        self._banco.updates.append((self._nome, dict(linha)))
        return self

    def delete(self, **k):
        self._op = "delete"
        return self

    def eq(self, coluna, valor):
        self._filtros.append((coluna, valor))
        return self

    def __getattr__(self, nome):
        """Toda a cauda do PostgREST (`order`, `limit`, `in_`, `gte`, `single`, …)
        continua a corrente sem filtrar. O falso é FIEL no que o gate mede — a linha
        gravada e o filtro de tenant — e permissivo no resto, de propósito: um falso
        que exige a API inteira vira um segundo PostgREST para manter."""
        if nome.startswith("__"):
            raise AttributeError(nome)

        def _corrente(*a, **k):
            return self
        return _corrente

    def execute(self):
        if self._op != "select":
            linhas = self._linha if isinstance(self._linha, list) else [self._linha]
            return _Resposta([x for x in linhas if x])
        base = self._banco.linhas.get(self._nome, [])
        return _Resposta([r for r in base
                          if all(str(r.get(c)) == str(v) for c, v in self._filtros)])


class BancoFalso:
    def __init__(self, linhas=None):
        self.linhas = {k: list(v) for k, v in (linhas or {}).items()}
        self.inseridos = []
        self.updates = []

    def table(self, nome):
        return _Tabela(self, nome)

    def de(self, tabela):
        return [x for n, x in self.inseridos if n == tabela]


class ClienteFalso:
    """O que o código chama de `db`/`supabase`: um objeto com `.client`."""

    def __init__(self, banco):
        self.client = banco


# ---------------------------------------------------------------------------
# AS FIXTURES — 💭 textos INVENTADOS. Nenhum veio do acervo de um segurado.
# ---------------------------------------------------------------------------
EMPRESA_A = "aaaaaaaa-0000-4000-8000-000000000001"
EMPRESA_B = "bbbbbbbb-0000-4000-8000-000000000002"
CONVERSA_A = "cccccccc-0000-4000-8000-00000000000a"
CONVERSA_SEM_SOMBRA = "dddddddd-0000-4000-8000-00000000000d"
RUN_SOMBRA_A = "eeeeeeee-0000-4000-8000-00000000000e"

FRASE_SINISTRO = "bati o carro e preciso de guincho"
FRASE_NAO_SINISTRO = "quero falar com o terceiro andar"
FRASE_ROUBO = "roubaram meu carro"
FRASE_VAZIA = ""

# 💭 CPF sintético — o valor que a Receita usa como inválido de propósito.
# ⛔ Ele existe aqui para o CONTROLE do redator, e nunca é impresso em relatório.
CPF_SINTETICO = "000.000.000-00"

WORKFLOW = "claims.shadow"


# ===========================================================================
# [0] GATE ZERO — a mensagem percorre o webhook EM SILÊNCIO e a sombra abre
# ===========================================================================
#
# 🔴 ESTE É O ELO. Os outros dez blocos provam PONTAS.
#
# ⚠️ O caminho dinâmico importa `app.api.webhook`, que é o topo de uma árvore de
# dependências de produção. Onde uma biblioteca de terceiro faltar, o guarda instala
# um **shim** e IMPRIME a lista — um shim invisível seria um teste que mede outra
# coisa. Nenhum módulo `app.*` é jamais falsificado: falsificar o código da casa
# seria testar a fixture.
_SHIMS: list = []


class _Qualquer:
    """Objeto permissivo para shim de biblioteca de terceiro ausente."""

    def __init__(self, *a, **k):
        pass

    def __call__(self, *a, **k):
        return _Qualquer()

    def __getattr__(self, n):
        if n.startswith("__"):
            raise AttributeError(n)
        return _Qualquer()

    def __iter__(self):
        return iter(())

    def __getitem__(self, k):
        return _Qualquer()

    def __setitem__(self, k, v):
        pass

    def __contains__(self, k):
        return False

    def __bool__(self):
        return False


class _ModuloPermissivo(types.ModuleType):
    def __getattr__(self, n):
        if n.startswith("__"):
            raise AttributeError(n)
        return _Qualquer()


def _importar_webhook():
    """Importa `app.api.webhook` sem executar os `__init__` que puxam o mundo.

    📊 Medido em 03/09/2026 nesta máquina: `import app.api.webhook` morria em
    `app/api/__init__.py` → `chat.py` → `slowapi` (ausente). Os `__init__` de
    `app.api` e `app.services` importam routers e serviços que o gate ⓪ não usa; a
    casca de pacote (`__path__` real, `__init__` vazio) deixa os SUBMÓDULOS reais
    serem importados sem eles.

    Devolve (modulo, razao_do_skip).
    """
    import importlib

    try:
        import app  # noqa: F401
    except Exception as e:  # noqa: BLE001
        return None, "nao consegui importar o pacote `app`: %s: %s" % (type(e).__name__, e)

    _cascas_de_pacote()

    for _ in range(60):
        try:
            return importlib.import_module("app.api.webhook"), ""
        except ModuleNotFoundError as e:
            faltante = e.name or ""
            if not faltante or faltante.startswith("app."):
                return None, "falta um modulo da CASA (%s) — nao falsifico codigo nosso" % faltante
            sys.modules[faltante] = _ModuloPermissivo(faltante)
            _SHIMS.append(faltante)
            raiz = faltante.split(".")[0]
            if raiz not in sys.modules:
                sys.modules[raiz] = _ModuloPermissivo(raiz)
        except Exception as e:  # noqa: BLE001
            return None, "import levantou %s: %s" % (type(e).__name__, e)
    return None, "desisti depois de 60 shims: %s" % ", ".join(_SHIMS)


def _rodar_webhook_em_observacao(texto):
    """Roda `process_whatsapp_message_background` DE VERDADE, em modo observação.

    ⛔ Nada sai: `whatsapp_service.send_message` é falso e as chamadas dele são
    CONTADAS (o gate exige zero). ⛔ Nada é gravado no Supabase real: `webhook.supabase`
    é o cliente falso.

    A SENTINELA do `return`: se o fluxo passar da linha 782, a próxima coisa que ele
    faz é `from app.services.billing_service import get_billing_service`. O falso
    registra a passagem. É medição, não leitura de código — e é o que distingue
    "parou no modo observação" de "seguiu para a IA".

    Devolve (banco_falso, trilha, envios, razao_do_skip).
    """
    import asyncio

    w, razao = _importar_webhook()
    if w is None:
        return None, [], [], razao

    try:
        import app.services.atlas.attendance_capture as ac
        import app.services.observability.sli as sli
    except Exception as e:  # noqa: BLE001
        return None, [], [], "nao consegui importar %s: %s" % (type(e).__name__, e)

    trilha: list = []
    envios: list = []
    banco = BancoFalso({"conversations": [{"session_id": "x", "status": "open"}]})

    async def _agente_desligado(*a, **k):
        trilha.append("attendance_agent_active->False")
        return False

    async def _capturou(*a, **k):
        trilha.append("capture_channel_message")
        return None

    async def _conversa(**k):
        trilha.append("get_or_create_conversation")
        return CONVERSA_A

    async def _nao_roteia(**k):
        return False

    def _billing(*a, **k):
        trilha.append("PASSOU_DO_RETURN")
        raise RuntimeError("sentinela do gate ZERO — o fluxo nao devia chegar aqui")

    class _WhatsAppFalso:
        def send_message(self, *a, **k):
            envios.append("send_message")
            trilha.append("send_message")
            return {}

        def __getattr__(self, n):
            def _(*a, **k):
                return None
            return _

    class _IntegracaoFalsa:
        def get_integration_by_id(self, _i):
            return None

        def get_integration_by_phone(self, _p):
            return {"id": "integracao-fixture", "company_id": EMPRESA_A,
                    "agent_id": None, "provider": "z-api"}

        def get_or_create_user(self, **k):
            return "usuario-fixture"

    guardado = {
        "supabase": w.supabase, "integ": w.integration_service,
        "whats": w.whatsapp_service, "conversa": w.get_or_create_conversation,
        "ativo": ac.attendance_agent_active, "captura": ac.capture_channel_message,
        "sli": sli.registrar,
        "billing": sys.modules.get("app.services.billing_service"),
        "router": sys.modules.get("app.services.dispatch_router"),
        "allow": os.environ.get("ATTENDANT_INBOUND_ALLOWLIST"),
        "carto": os.environ.get("CARTOGRAPHER_MODE"),
    }
    try:
        w.supabase = ClienteFalso(banco)
        w.integration_service = _IntegracaoFalsa()
        w.whatsapp_service = _WhatsAppFalso()
        w.get_or_create_conversation = _conversa
        ac.attendance_agent_active = _agente_desligado
        ac.capture_channel_message = _capturou
        sli.registrar = lambda *a, **k: None

        mod_billing = types.ModuleType("app.services.billing_service")
        mod_billing.get_billing_service = _billing
        sys.modules["app.services.billing_service"] = mod_billing

        mod_router = types.ModuleType("app.services.dispatch_router")
        mod_router.try_route_insurer_inbound = _nao_roteia
        sys.modules["app.services.dispatch_router"] = mod_router

        os.environ["ATTENDANT_INBOUND_ALLOWLIST"] = ""
        os.environ["CARTOGRAPHER_MODE"] = "0"

        asyncio.run(w.process_whatsapp_message_background({
            "connectedPhone": "5500000000000",
            "phone": "5500000000001",
            "isGroup": False, "fromMe": False,
            "text": {"message": texto},
            "messageId": "FIXTURE-093B-1",
            "senderName": "Fixture",
        }))
    except Exception as e:  # noqa: BLE001
        trilha.append("EXCECAO_SUBIU:%s" % type(e).__name__)
    finally:
        w.supabase = guardado["supabase"]
        w.integration_service = guardado["integ"]
        w.whatsapp_service = guardado["whats"]
        w.get_or_create_conversation = guardado["conversa"]
        ac.attendance_agent_active = guardado["ativo"]
        ac.capture_channel_message = guardado["captura"]
        sli.registrar = guardado["sli"]
        for chave, nome in (("billing", "app.services.billing_service"),
                            ("router", "app.services.dispatch_router")):
            if guardado[chave] is not None:
                sys.modules[nome] = guardado[chave]
            else:
                sys.modules.pop(nome, None)
        for chave, nome in (("allow", "ATTENDANT_INBOUND_ALLOWLIST"),
                            ("carto", "CARTOGRAPHER_MODE")):
            if guardado[chave] is None:
                os.environ.pop(nome, None)
            else:
                os.environ[nome] = guardado[chave]
    return banco, trilha, envios, ""


_RE_GANCHO = re.compile(r"claims_shadow|abrir_sombra|detectar_sinistro")


def _linha_do_return_do_silencio(fonte):
    """A linha do `return` que fecha o bloco `if _em_silencio:` — o fim do caminho.

    Puro sobre o texto, para que a linha de CONTROLE possa passar um snippet
    sintético em vez de estragar `webhook.py`.
    """
    linhas = fonte.split("\n")
    for i, linha in enumerate(linhas):
        if re.match(r"\s*if\s+_em_silencio\s*:", linha):
            recuo = len(linha) - len(linha.lstrip())
            for j in range(i + 1, len(linhas)):
                seguinte = linhas[j]
                if not seguinte.strip():
                    continue
                if (len(seguinte) - len(seguinte.lstrip())) <= recuo:
                    break
                if re.match(r"\s*return\s*$", seguinte):
                    return j + 1
    return None


def _linhas_do_gancho(fonte):
    return [i + 1 for i, l in enumerate(fonte.split("\n"))
            if _RE_GANCHO.search(l) and not l.lstrip().startswith("#")]


def bloco_0_gate_zero():
    _p("\n[0] GATE ZERO -- a mensagem percorre o webhook EM SILENCIO e a sombra ABRE")

    # --- (a) o caminho ESTRUTURAL: onde o gancho está escrito -----------------
    fonte = ler(WEBHOOK)
    fim = _linha_do_return_do_silencio(fonte)
    certo(fim is not None,
          "acho o `return` que fecha o modo observacao em webhook.py (linha %s)" % fim,
          "sem esta ancora o gate ZERO nao tem contra o que comparar")
    # ⚠️ O casador filtra comentário LINHA A LINHA e não usa `sem_comentario_py`:
    # aquela função reindexa o arquivo, e aqui a POSIÇÃO é o que está sendo medido.
    ganchos = _linhas_do_gancho(fonte)
    vermelho_ate(bool(ganchos),
                 "webhook.py CHAMA a sombra em algum lugar",
                 "BLOCO A",
                 "📊 hoje: zero ocorrencias de claims_shadow/abrir_sombra/detectar_sinistro "
                 "em webhook.py. A SPEC-093-B BLOCO A ainda nao existe -- a sombra nao abriu.")
    if ganchos and fim:
        vermelho_ate(min(ganchos) < fim,
                     "o gancho da sombra esta ACIMA do `return` do modo observacao",
                     "BLOCO A",
                     "gancho na(s) linha(s) %s, `return` na %d. Um gancho abaixo dele "
                     "prova um caminho que NENHUMA mensagem percorre (4 de 4 agentes "
                     "attendance inativos, medido em 03/09/2026)." % (ganchos, fim))

    # 🔴 CONTROLE do casador, sobre texto SINTETICO (§9.3: exigir o defeito de volta
    # no arquivo real seria guardar verdade vencida).
    bom = ('async def f():\n'
           '    if _em_silencio:\n'
           '        await abrir_sombra(company_id, conversation_id)\n'
           '        await capture()\n'
           '        return\n'
           '    return 1\n')
    ruim = ('async def f():\n'
            '    if _em_silencio:\n'
            '        await capture()\n'
            '        return\n'
            '    await abrir_sombra(company_id, conversation_id)\n'
            '    return 1\n')
    fb, fr = _linha_do_return_do_silencio(bom), _linha_do_return_do_silencio(ruim)
    certo(fb == 5 and fr == 4,
          "CONTROLE: o casador acha o `return` do silencio nos dois snippets",
          "veio %r e %r" % (fb, fr))
    certo(min(_linhas_do_gancho(bom)) < fb,
          "CONTROLE: a forma CORRETA passa (gancho acima do return)")
    certo(min(_linhas_do_gancho(ruim)) > fr,
          "CONTROLE: a MUTACAO M4 (gancho abaixo do return) e DETECTADA",
          "um gate que nao acusa a mutacao da SPEC e um carimbo")

    # --- (b) o caminho DINAMICO: rodar a funcao de verdade --------------------
    banco, trilha, envios, razao = _rodar_webhook_em_observacao(FRASE_SINISTRO)
    if banco is None:
        pular("[0] dinamico", razao + "  (o caminho ESTRUTURAL acima ja rodou)")
        return
    if _SHIMS:
        _p("        shims de biblioteca de terceiro AUSENTE: %s" % ", ".join(sorted(set(_SHIMS))))
    certo("capture_channel_message" in trilha,
          "o fluxo chegou ao MODO OBSERVACAO (capturou sem responder)",
          "trilha: %s" % trilha)
    certo("PASSOU_DO_RETURN" not in trilha,
          "o fluxo PAROU no `return` de :782 -- o grafo NAO foi chamado",
          "a sentinela do billing foi tocada: o fluxo seguiu para a IA. trilha: %s" % trilha)
    certo(envios == [],
          "NENHUMA mensagem saiu para o segurado",
          "envios: %d" % len(envios))
    sombras = [l for l in banco.de("work_runs") if l.get("workflow_key") == WORKFLOW]
    vermelho_ate(len(sombras) == 1,
                 "UMA sombra (work_runs.workflow_key='claims.shadow') foi aberta",
                 "BLOCO A",
                 "📊 gravou %d linha(s) em work_runs; as tabelas tocadas foram %s. "
                 "BLOCO A ainda nao existe / a sombra nao abriu."
                 % (len(sombras), sorted({n for n, _ in banco.inseridos})))
    if sombras:
        vermelho_ate(str(sombras[0].get("conversation_id") or "") == CONVERSA_A,
                     "a sombra guarda o conversation_id (a chave de reidentificacao)",
                     "BLOCO A")
        vermelho_ate(str(sombras[0].get("company_id") or "") == EMPRESA_A,
                     "a sombra guarda o company_id (CLAUDE.md §7)",
                     "BLOCO A")

    # 🔴 A LINHA DE CONTROLE (§9.2): a MESMA rodada, com um texto SEM sinistro.
    # Sem ela, um detector que abrisse sombra para toda mensagem passaria verde.
    banco2, trilha2, envios2, _ = _rodar_webhook_em_observacao(FRASE_NAO_SINISTRO)
    if banco2 is not None:
        sombras2 = [l for l in banco2.de("work_runs") if l.get("workflow_key") == WORKFLOW]
        certo(not sombras2,
              "CONTROLE: 'terceiro andar' NAO abre sombra",
              "abriu %d -- o detector casa 'terceiro' fora de contexto (SPEC §1.5)"
              % len(sombras2))
        certo(envios2 == [] and "PASSOU_DO_RETURN" not in trilha2,
              "CONTROLE: a rodada sem sinistro tambem fica em silencio")


# ===========================================================================
# [1] VOCABULARIO -- um arquivo, lido pelos dois lados
# ===========================================================================
EVENTOS_ESPERADOS = {
    "claims.sombra_aberta", "claims.handoff_pedido", "claims.humano_assumiu",
    "claims.humano_devolveu", "claims.humano_respondeu", "claims.nota_registrada",
    "claims.documento_recebido", "claims.seguradora_respondeu",
    "claims.espera_aberta", "claims.espera_satisfeita", "claims.encerrado",
}
# 📊 O CHECK real de `work_events.actor_type`, lido do banco em 03/09/2026 e
# transcrito em `dispatch_router.ATORES_VALIDOS` (:562).
# ⛔ `human` NAO esta na lista: escrever esse valor e um INSERT que o Postgres
# recusa -- e `_evento` engole a recusa. Um evento que nunca acontece.
ATORES_DO_CHECK = {"system", "worker", "user", "agent", "admin", "provider"}
ENUMS_ESPERADOS = {"confianca", "motivo", "origem", "canal", "tipo_documento",
                   "kind", "desfecho"}


def bloco_1_vocabulario():
    _p("\n[1] VOCABULARIO -- um arquivo so, e o ator vem do CHECK real")
    certo(os.path.exists(VOCAB),
          "lib/atendimento/claims-shadow-vocab.json existe",
          "🔴 no lib/, nunca no backend/: o Next nao importa nada de backend/")
    if not os.path.exists(VOCAB):
        return
    try:
        v = json.loads(ler(VOCAB))
    except Exception as e:  # noqa: BLE001
        certo(False, "o vocabulario e JSON valido", "%s: %s" % (type(e).__name__, e))
        return
    certo(True, "o vocabulario e JSON valido")
    eventos = v.get("eventos") or {}
    certo(set(eventos) == EVENTOS_ESPERADOS,
          "os 11 eventos da §5 estao la, nem a mais nem a menos",
          "faltam %s · sobram %s" % (sorted(EVENTOS_ESPERADOS - set(eventos)),
                                     sorted(set(eventos) - EVENTOS_ESPERADOS)))
    fora = sorted({e: d.get("ator") for e, d in eventos.items()
                   if d.get("ator") not in ATORES_DO_CHECK}.items())
    certo(not fora,
          "TODO `ator` do vocabulario esta no CHECK de work_events",
          "fora do CHECK: %s -- `human` nao existe e o INSERT some sem erro" % fora)
    certo(set(v.get("enums") or {}) == ENUMS_ESPERADOS,
          "os 7 enums da §5 estao la",
          "veio %s" % sorted(v.get("enums") or {}))
    sem_payload = [e for e, d in eventos.items() if not isinstance(d.get("payload"), list)]
    certo(not sem_payload,
          "todo evento declara a lista de chaves de payload",
          "sem payload: %s -- sem ela 'pediu documento' e 'pediu BO' colidem (ref. ③)"
          % sem_payload)
    certo(v.get("workflow_key") == WORKFLOW,
          "o vocabulario declara workflow_key='claims.shadow'")

    # 🔴 CONTROLE: o casador de ator CONSEGUE ficar vermelho.
    falso = {"claims.x": {"ator": "human", "payload": []}}
    achou = [e for e, d in falso.items() if d.get("ator") not in ATORES_DO_CHECK]
    certo(achou == ["claims.x"],
          "CONTROLE: um `ator: human` sintetico e RECUSADO",
          "se este gate aceitar `human`, ele nao guarda nada")

    _p("        📊 sha256 do vocabulario lido pelo Python: %s" % sha256_de(VOCAB))
    _p("        (o lado Next imprime o mesmo em `node scripts/claims-shadow-vocab.test.mjs`)")


# ===========================================================================
# [2] DETECCAO -- A①②③⑥
# ===========================================================================
def _detectar(texto, ficha=None):
    """Adaptador: `detectar_sinistro(texto_normalizado, ficha) -> (bool, conf, motivo)`.

    Aceita tupla, dict ou bool — o guarda mede o COMPORTAMENTO, não a embalagem.
    Devolve (abriu, confianca, razao_do_erro).
    """
    if detectar_sinistro is None:
        return None, None, "modulo ainda nao existe"
    try:
        r = detectar_sinistro(texto, ficha)
    except TypeError:
        try:
            r = detectar_sinistro(texto)
        except Exception as e:  # noqa: BLE001
            return None, None, "assinatura diferente da assumida (%s) -- ajuste _detectar()" % e
    except Exception as e:  # noqa: BLE001
        return None, None, "detectar_sinistro levantou %s: %s" % (type(e).__name__, e)
    if isinstance(r, bool):
        return r, None, ""
    if isinstance(r, dict):
        return bool(r.get("sinistro") or r.get("abre")), r.get("confianca"), ""
    if isinstance(r, (tuple, list)) and r:
        return bool(r[0]), (r[1] if len(r) > 1 else None), ""
    return None, None, "retorno de tipo inesperado: %s" % type(r).__name__


def bloco_2_deteccao():
    _p("\n[2] DETECCAO -- o detector separa sinistro de 'terceiro andar'")
    if detectar_sinistro is None:
        pular("[2] DETECCAO", _FALTA_SOMBRA or "detectar_sinistro ainda nao existe")
        return
    casos = [
        (FRASE_SINISTRO, True, "media", "A① regex do segurado -> abre com confianca MEDIA"),
        (FRASE_NAO_SINISTRO, False, None, "A② 'terceiro' sozinho NAO abre (§1.5)"),
        (FRASE_ROUBO, True, "media", "A① 'roubaram meu carro' -> abre"),
        (FRASE_VAZIA, False, None, "A⑥ texto vazio NAO abre"),
    ]
    vistos = []
    for texto, esperado, conf, rotulo in casos:
        abriu, confianca, erro = _detectar(texto)
        if erro:
            pular("[2] %s" % rotulo, erro)
            continue
        vistos.append(abriu)
        certo(abriu is esperado, rotulo,
              "veio %r para um texto de %d chars" % (abriu, len(texto)))
        if esperado and conf and confianca is not None:
            certo(str(confianca).lower() == conf,
                  "%s -- confianca %s" % (rotulo, conf),
                  "veio %r" % (confianca,))
    # 🔴 CONTROLE GERAL do bloco: um detector constante reprova.
    if len(vistos) == len(casos):
        certo(len(set(vistos)) > 1,
              "CONTROLE: o detector NAO devolve o mesmo para as 4 fixtures",
              "devolveu %r para todas -- um detector constante casa tudo ou nada" % vistos[0])

    # A③ idempotencia: a chave e a CONVERSA.
    if abrir_sombra is None:
        pular("[2] A③ idempotencia", "abrir_sombra ainda nao existe")
        return
    banco = BancoFalso()
    erro = None
    try:
        for _ in range(2):
            r = abrir_sombra(company_id=EMPRESA_A, conversation_id=CONVERSA_A,
                             db=ClienteFalso(banco))
            if hasattr(r, "__await__"):
                import asyncio
                asyncio.run(_espera(r))
    except TypeError as e:
        erro = "assinatura diferente da assumida (%s) -- ajuste o bloco [2]" % e
    except Exception as e:  # noqa: BLE001
        erro = "abrir_sombra levantou %s: %s" % (type(e).__name__, e)
    if erro:
        pular("[2] A③ idempotencia", erro)
        return
    sombras = [l for l in banco.de("work_runs") if l.get("workflow_key") == WORKFLOW]
    certo(len(sombras) == 1,
          "A③ duas mensagens da mesma conversa -> UMA sombra",
          "gravou %d" % len(sombras))
    if sombras:
        certo(str(sombras[0].get("idempotency_key") or "")
              == "claims.shadow:%s" % CONVERSA_A,
              "A③ a chave de idempotencia e `claims.shadow:{conversation_id}`",
              "veio %r" % sombras[0].get("idempotency_key"))
        chaves_texto = [k for k in sombras[0].get("input_payload") or {}
                        if k in ("texto", "text", "content", "mensagem", "body")]
        certo(not chaves_texto,
              "A⑥ input_payload nao tem NENHUM campo de texto do segurado",
              "achei %s -- o motivo e qual REGRA casou, nunca a frase" % chaves_texto)


async def _espera(coro):
    return await coro


# ===========================================================================
# [3] LEDGER -- B①②③⑥: o evento e LIDO DO BANCO, e o payload so tem enum
# ===========================================================================
def _registrar(banco, evento, payload, conversa=CONVERSA_A, empresa=EMPRESA_A):
    """Adaptador do escritor do BLOCO B. Se a assinatura sair diferente, o
    INTEGRADOR muda SÓ esta função."""
    if registrar_evento is None:
        return "registrar_evento ainda nao existe"
    tentativas = (
        dict(db=ClienteFalso(banco), company_id=empresa, conversation_id=conversa,
             event_type=evento, payload=payload),
        dict(db=ClienteFalso(banco), company_id=empresa, conversation_id=conversa,
             evento=evento, payload=payload),
    )
    ultimo = ""
    for kwargs in tentativas:
        try:
            r = registrar_evento(**kwargs)
            if hasattr(r, "__await__"):
                import asyncio
                asyncio.run(_espera(r))
            return ""
        except TypeError as e:
            ultimo = "assinatura diferente da assumida (%s) -- ajuste _registrar()" % e
        except Exception as e:  # noqa: BLE001
            return "registrar_evento levantou %s: %s" % (type(e).__name__, e)
    return ultimo


def _payload_de_exemplo(chaves, enums):
    """Um valor legal para cada chave declarada — enum quando há enum, inteiro
    quando a chave é `dias`, e um slug curto no resto."""
    fora = {}
    for k in chaves:
        if k in enums and enums[k]:
            fora[k] = enums[k][0]
        elif k == "dias":
            fora[k] = 3
        elif k == "tem_numero":
            fora[k] = True
        elif k == "seguradora_slug":
            fora[k] = "porto"
        elif k == "ramo":
            fora[k] = "auto"
        elif k == "motivo_enum":
            fora[k] = "sinistro"
        else:
            fora[k] = "desconhecido"
    return fora


def _banco_com_sombra():
    return BancoFalso({
        "work_runs": [{
            "id": RUN_SOMBRA_A, "company_id": EMPRESA_A,
            "conversation_id": CONVERSA_A, "workflow_key": WORKFLOW,
            "status": "running", "runtime_kind": "sombra",
        }],
    })


def bloco_3_ledger():
    _p("\n[3] LEDGER -- cada gesto vira UMA linha, com ator do CHECK e payload de enum")
    if registrar_evento is None:
        pular("[3] LEDGER", _FALTA_SOMBRA or "registrar_evento ainda nao existe")
    if not os.path.exists(VOCAB):
        pular("[3] LEDGER vocabulario", "lib/atendimento/claims-shadow-vocab.json ausente")
        return
    v = json.loads(ler(VOCAB))
    eventos, enums = v["eventos"], v["enums"]
    limite = int(v.get("limite_de_valor_em_chars") or 64)

    if registrar_evento is not None:
        for nome, decl in sorted(eventos.items()):
            banco = _banco_com_sombra()
            payload = _payload_de_exemplo(decl["payload"], enums)
            erro = _registrar(banco, nome, payload)
            if erro:
                pular("[3] B① %s" % nome, erro)
                break
            linhas = [l for l in banco.de("work_events") if l.get("event_type") == nome]
            certo(len(linhas) == 1,
                  "B①⑥ %s produz UMA linha em work_events" % nome,
                  "produziu %d -- ref. ① OCEL: um gesto com dois objetos e UM evento "
                  "com qualificadores, nao dois eventos" % len(linhas))
            if not linhas:
                continue
            linha = linhas[0]
            certo(linha.get("actor_type") == decl["ator"],
                  "B① %s grava actor_type=%s" % (nome, decl["ator"]),
                  "veio %r -- fora do CHECK o INSERT some sem erro" % linha.get("actor_type"))
            gravado = linha.get("payload_redacted") or {}
            certo(set(gravado) <= set(decl["payload"]),
                  "B② %s: payload so com chaves do vocabulario" % nome,
                  "sobrando %s" % sorted(set(gravado) - set(decl["payload"])))
            longos = {k: len(str(x)) for k, x in gravado.items() if len(str(x)) > limite}
            certo(not longos,
                  "B② %s: nenhum valor acima de %d chars" % (nome, limite),
                  "%s -- valor longo e texto disfarcado de enum" % longos)
            if contem_pii is not None:
                certo(not contem_pii(json.dumps(gravado, ensure_ascii=False)),
                      "B② %s: contem_pii(json.dumps(payload)) e FALSO" % nome)

        # B③ CONTROLE: conversa SEM sombra nao escreve evento.
        banco = BancoFalso({"work_runs": []})
        erro = _registrar(banco, "claims.humano_assumiu", {"origem": "dashboard"},
                          conversa=CONVERSA_SEM_SOMBRA)
        if not erro:
            certo(not banco.de("work_events"),
                  "B③ CONTROLE: conversa SEM sombra nao escreve evento",
                  "escreveu %d -- nada de sombra retroativa nesta SPEC"
                  % len(banco.de("work_events")))

        # 🔴 CONTROLE DE PII: um CPF sintetico no payload tem de ser RECUSADO.
        banco = _banco_com_sombra()
        erro = _registrar(banco, "claims.nota_registrada",
                          {"origem": "dashboard", "tem_numero": CPF_SINTETICO})
        if not erro:
            linhas = banco.de("work_events")
            gravado = (linhas[0].get("payload_redacted") if linhas else {}) or {}
            texto = json.dumps(gravado, ensure_ascii=False)
            certo("000" not in texto,
                  "B② CONTROLE DE PII: um CPF sintetico no payload e RECUSADO/esvaziado",
                  "o payload gravado ainda contem o numero. A SPEC manda gravar "
                  "payload_redacted={} e severity='warning': a sombra prefere perder "
                  "detalhe a vazar.")
            if linhas and gravado == {}:
                certo(str(linhas[0].get("severity")) == "warning",
                      "B② o evento com PII recusado grava severity='warning'",
                      "veio %r" % linhas[0].get("severity"))

    # 🔴 CONTROLE do proprio cliente falso: ele CONSEGUE ver uma linha errada?
    # Sem isto, todo gate acima poderia estar medindo um falso que nunca grava.
    prova = BancoFalso()
    prova.table("work_events").insert({"event_type": "x", "actor_type": "human"}).execute()
    certo(len(prova.de("work_events")) == 1
          and prova.de("work_events")[0]["actor_type"] == "human",
          "CONTROLE: o cliente falso REGISTRA a linha que recebeu (inclusive a errada)",
          "um falso que engole o INSERT deixaria os gates acima verdes por vazio")
    vazio = BancoFalso()
    certo(vazio.de("work_events") == [],
          "CONTROLE: o cliente falso comeca vazio")


# ===========================================================================
# [4] DOIS TENANTS -- A④ B④ C⑥
# ===========================================================================
def bloco_4_dois_tenants():
    _p("\n[4] DOIS TENANTS -- a sombra da A nao aparece no filtro da B")
    url, key = _credencial()
    if not url or not key:
        pular("[4] DOIS TENANTS",
              "sem SUPABASE_URL/SERVICE_ROLE_KEY no ambiente nem em backend/.env "
              "-- o bloco le SO por SELECT e nao inventa credencial")
        return
    st, linhas, _ = _get("agents?select=company_id&limit=200")
    if st != 200 or not linhas:
        pular("[4] DOIS TENANTS", "a leitura de `agents` devolveu status %r" % st)
        return
    empresas = sorted({str(l["company_id"]) for l in linhas if l.get("company_id")})
    certo(len(empresas) >= 2,
          "achei %d corretoras distintas em `agents` -- da para testar DOIS tenants"
          % len(empresas),
          "com uma so, o isolamento nao e testavel e o gate seria um carimbo")
    if len(empresas) < 2:
        return
    a, b = empresas[0], empresas[1]

    # 🔴 CONTROLE PRIMEIRO: a consulta EXECUTA? Hoje `claims.shadow` da 0 dos dois
    # lados, e "0 = 0" e o resultado que um filtro QUEBRADO tambem produz. O
    # controle e contar `agents` por company_id e exigir > 0 -- assim se sabe que a
    # forma da consulta funciona antes de acreditar no zero (CLAUDE.md §9.2).
    vivos = []
    for empresa in (a, b):
        st, _c, total = _get("agents?select=id&company_id=eq.%s&limit=1"
                             % urllib.parse.quote(empresa), contar=True)
        vivos.append(total or 0)
    certo(all(n > 0 for n in vivos),
          "CONTROLE: a consulta filtrada por company_id EXECUTA e devolve >0 em agents",
          "veio %r -- se esta consulta devolve zero, o zero das sombras nao prova nada"
          % vivos)

    contagens = {}
    for rotulo, empresa in (("A", a), ("B", b)):
        st, _c, total = _get(
            "work_runs?select=id&workflow_key=eq.%s&company_id=eq.%s&limit=1"
            % (urllib.parse.quote(WORKFLOW), urllib.parse.quote(empresa)), contar=True)
        certo(st == 200,
              "a consulta de sombras da corretora %s responde 200" % rotulo,
              "veio %r" % st)
        contagens[rotulo] = total or 0
    st, _c, geral = _get("work_runs?select=id&workflow_key=eq.%s&limit=1"
                         % urllib.parse.quote(WORKFLOW), contar=True)
    geral = geral or 0
    certo(contagens["A"] + contagens["B"] <= geral,
          "A④ a soma das duas corretoras nao passa do total de sombras",
          "A=%d B=%d total=%d -- soma maior que o total e linha contada duas vezes"
          % (contagens["A"], contagens["B"], geral))
    _p("        📊 hoje: work_runs workflow_key='claims.shadow' -> A=%d B=%d total=%d"
       % (contagens["A"], contagens["B"], geral))

    # A④/B④ de verdade: nenhuma linha da A carrega o company_id da B.
    st, linhas, _ = _get(
        "work_runs?select=company_id&workflow_key=eq.%s&company_id=eq.%s&limit=200"
        % (urllib.parse.quote(WORKFLOW), urllib.parse.quote(a)))
    intrusas = [l for l in (linhas or []) if str(l.get("company_id")) != a]
    certo(not intrusas,
          "A④ nenhuma linha do filtro da corretora A carrega company_id de outra",
          "%d intrusa(s)" % len(intrusas))
    if geral == 0:
        _p("        ⚠️ 0 sombras hoje: este gate ainda NAO exerceu o isolamento com "
           "dado real. Ele so vira prova depois do BLOCO A rodar no piloto.")

    # B④ o mesmo sobre work_events, e a coluna precisa EXISTIR.
    st, _c, _t = _get("work_events?select=company_id&limit=1")
    certo(st == 200,
          "B④ work_events tem coluna company_id (a barreira mora no filtro do codigo)",
          "veio %r -- sem company_id em work_events nao ha filtro possivel" % st)
    st, _c, _t = _get("work_events?select=coluna_que_nao_existe&limit=1")
    certo(st == 400,
          "CONTROLE: a sonda de coluna SABE ficar vermelha (coluna inexistente -> 400)",
          "veio %r -- uma sonda que responde 200 para tudo nao mede nada" % st)


# ===========================================================================
# [5] VARIANTES -- C①②③④
# ===========================================================================
X = ["claims.sombra_aberta", "claims.humano_assumiu", "claims.documento_recebido",
     "claims.espera_aberta", "claims.encerrado"]
X_PERMUTADA = ["claims.sombra_aberta", "claims.documento_recebido",
               "claims.humano_assumiu", "claims.espera_aberta", "claims.encerrado"]
Y = ["claims.sombra_aberta", "claims.nota_registrada", "claims.encerrado"]


def _trajetorias():
    """3 trajetorias X + 2 Y — a fixture do gate C①."""
    fora = []
    for i in range(3):
        fora.append({"work_run_id": "x%d" % i, "company_id": EMPRESA_A,
                     "ramo": "auto", "seguradora_slug": "porto", "eventos": list(X)})
    for i in range(2):
        fora.append({"work_run_id": "y%d" % i, "company_id": EMPRESA_A,
                     "ramo": "auto", "seguradora_slug": "porto", "eventos": list(Y)})
    return fora


def _assinaturas(resultado):
    """Normaliza o retorno de `variantes_de` em {assinatura: n}."""
    if isinstance(resultado, dict):
        return {str(k): (len(v) if isinstance(v, (list, tuple, set)) else int(v))
                for k, v in resultado.items()}
    fora = {}
    for item in (resultado or []):
        if isinstance(item, dict):
            chave = item.get("assinatura") or item.get("variante") or item.get("dedupe_key")
            n = item.get("n") or item.get("total") or item.get("count") or 0
            fora[str(chave)] = int(n)
        elif isinstance(item, (tuple, list)) and len(item) >= 2:
            fora[str(item[0])] = int(item[1])
    return fora


def bloco_5_variantes():
    _p("\n[5] VARIANTES -- N>=3, e a PERMUTACAO e outra variante")
    if variantes_de is None:
        pular("[5] VARIANTES", _FALTA_SOMBRA or "variantes_de ainda nao existe")
    else:
        try:
            r = variantes_de(_trajetorias(), limiar=3)
        except TypeError:
            try:
                r = variantes_de(_trajetorias())
            except Exception as e:  # noqa: BLE001
                r = e
        except Exception as e:  # noqa: BLE001
            r = e
        if isinstance(r, Exception):
            pular("[5] VARIANTES", "variantes_de levantou %s: %s" % (type(r).__name__, r))
        else:
            vistas = _assinaturas(r)
            certo(len(vistas) == 1,
                  "C① 3 trajetorias X + 2 Y com limiar 3 -> SO X vira variante",
                  "veio %d variante(s): %s -- com Y na lista o limiar nao esta valendo"
                  % (len(vistas), sorted(vistas)))
            if vistas:
                certo(list(vistas.values())[0] == 3,
                      "C① a variante X aparece com N=3",
                      "veio %r" % list(vistas.values()))

            # 🔴 C② CONTROLE (ref. ② Celonis): a ORDEM faz a variante.
            mistura = ([{"work_run_id": "x%d" % i, "company_id": EMPRESA_A, "ramo": "auto",
                         "seguradora_slug": "porto", "eventos": list(X)} for i in range(3)]
                       + [{"work_run_id": "p%d" % i, "company_id": EMPRESA_A, "ramo": "auto",
                           "seguradora_slug": "porto", "eventos": list(X_PERMUTADA)}
                          for i in range(3)])
            try:
                r2 = variantes_de(mistura, limiar=3)
            except TypeError:
                r2 = variantes_de(mistura)
            vistas2 = _assinaturas(r2)
            certo(len(vistas2) == 2,
                  "C② CONTROLE: X e a PERMUTACAO de X sao variantes DIFERENTES",
                  "veio %d -- 'if you ask three people how a process works you'll get "
                  "five answers': sem ordem, nao ha variante (ref. ②)" % len(vistas2))
            certo(sorted(vistas2.values()) == [3, 3],
                  "C② cada uma das duas aparece com N=3",
                  "veio %r" % sorted(vistas2.values()))

            # C③ dedupe deterministico: duas chamadas iguais -> mesma chave.
            try:
                r3 = variantes_de(_trajetorias(), limiar=3)
            except TypeError:
                r3 = variantes_de(_trajetorias())
            certo(sorted(_assinaturas(r3)) == sorted(vistas),
                  "C③ a assinatura e DETERMINISTICA (duas chamadas, mesma chave)",
                  "%r != %r -- chave instavel duplica sinal a cada rodada"
                  % (sorted(_assinaturas(r3)), sorted(vistas)))

    # C④ os cinco contadores, cada um com DENOMINADOR (ref. ⑤ Sprout.ai).
    if contadores_de is None:
        pular("[5] C④ contadores", _FALTA_SOMBRA or "contadores_de ainda nao existe")
        return
    try:
        c = contadores_de(_trajetorias())
    except Exception as e:  # noqa: BLE001
        pular("[5] C④ contadores", "contadores_de levantou %s: %s" % (type(e).__name__, e))
        return
    certo(isinstance(c, dict) and "total" in c,
          "C④ os contadores vem num dict COM `total` (o denominador)",
          "veio %r -- numero sem denominador nao e citavel (ref. ⑤)" % type(c).__name__)
    if isinstance(c, dict) and "total" in c:
        total = c["total"]
        acima = {k: x for k, x in c.items()
                 if k != "total" and isinstance(x, int) and x > total}
        certo(not acima,
              "C④ nenhum contador passa do denominador",
              "%s > total=%r" % (acima, total))
        certo(len([k for k in c if k != "total"]) >= 5,
              "C④ sao pelo menos os CINCO contadores da referencia ⑤",
              "vieram %d" % len([k for k in c if k != "total"]))


# ===========================================================================
# [6] PRAZOS -- C⑤
# ===========================================================================
def _numeros_sem_vigencia(fonte):
    """As linhas em que `30` ou `120` aparecem SEM `vigencia_de` ao lado.

    ⚠️ Exceção legítima ao CLAUDE.md §9.4 (teste que chama o motor): aqui o alvo é a
    FORMA DA DECLARAÇÃO — "nenhum prazo mora solto no código" — e não o
    comportamento. É o caso que a própria §9.4 nomeia como legítimo.
    """
    fora = []
    for i, linha in enumerate(fonte.split("\n")):
        se = linha.split("#")[0]
        if re.search(r"(?<![\w.])(30|120)(?![\w.])", se) and "vigencia_de" not in linha:
            fora.append(i + 1)
    return fora


def bloco_6_prazos():
    _p("\n[6] PRAZOS -- nenhum `30` solto, e 2026 e 2027 resolvem por caminhos diferentes")
    if os.path.exists(PRAZOS_PY):
        soltos = _numeros_sem_vigencia(ler(PRAZOS_PY))
        certo(not soltos,
              "C⑤ nenhum `30`/`120` fora de linha com vigencia_de",
              "linhas %s -- CNSP 496/2026 so vale para contratos formados ou renovados "
              "a partir de 05/01/2027. Prazo sem vigencia e bug futuro (ref. ⑥)" % soltos)
    else:
        pular("[6] C⑤ regex", "backend/app/services/prazos_regulatorios.py ainda nao existe")

    # 🔴 CONTROLE do casador, sobre texto SINTETICO.
    ruim = "PRAZO_REGULACAO = 30  # dias\n"
    bom = 'PRAZOS = ({"valor": 30, "vigencia_de": "2027-01-05"},)\n'
    certo(_numeros_sem_vigencia(ruim) == [1],
          "CONTROLE: o casador ACHA um `30` solto")
    certo(_numeros_sem_vigencia(bom) == [],
          "CONTROLE: um `30` COM vigencia_de ao lado passa",
          "um gate que reprova tudo e um carimbo ao contrario")

    if espera_vencida is None or PRAZOS is None:
        pular("[6] C⑤ motor", _FALTA_PRAZOS or "espera_vencida/PRAZOS ainda nao existem")
        return
    certo(bool(PRAZOS), "C⑤ PRAZOS nao esta vazia")
    campos = ("valor", "unidade", "ramo", "fonte", "vigencia_de", "vigencia_ate")
    try:
        primeiro = list(PRAZOS)[0]
        chaves = set(primeiro.keys()) if isinstance(primeiro, dict) else set(
            getattr(primeiro, "_fields", ()) or ())
        certo(set(campos) <= chaves,
              "C⑤ cada prazo declara valor/unidade/ramo/fonte/vigencia_de/vigencia_ate",
              "faltam %s" % sorted(set(campos) - chaves))
    except Exception as e:  # noqa: BLE001
        pular("[6] C⑤ forma de PRAZOS", "%s: %s" % (type(e).__name__, e))

    import datetime as _dt
    aberta = _dt.date(2026, 6, 15)
    respostas = {}
    erro = ""
    for rotulo, contrato in (("2026", _dt.date(2026, 6, 1)),
                             ("2027", _dt.date(2027, 2, 1)),
                             ("None", None)):
        try:
            respostas[rotulo] = espera_vencida("esperando_seguradora", aberta,
                                               data_contrato=contrato)
        except TypeError as e:
            erro = "assinatura diferente da assumida (%s) -- ajuste o bloco [6]" % e
            break
        except Exception as e:  # noqa: BLE001
            erro = "espera_vencida levantou %s: %s" % (type(e).__name__, e)
            break
    if erro:
        pular("[6] C⑤ espera_vencida", erro)
        return
    certo(str(respostas.get("None")) == "regime_nao_determinado",
          "C⑤ sem data de contrato -> 'regime_nao_determinado'",
          "veio %r -- inventar o regime e pior que dizer que nao se sabe"
          % respostas.get("None"))
    certo(respostas.get("2026") != respostas.get("2027")
          or str(respostas.get("2026")) == "regime_nao_determinado",
          "C⑤ CONTROLE: contrato de 2026 e de 2027 resolvem por CAMINHOS diferentes",
          "os dois deram %r -- se a vigencia nao muda nada, ela nao esta sendo usada "
          "e o `30` voltou a ser hardcode com outro nome" % respostas.get("2026"))


# ===========================================================================
# [7] SEM TEXTO -- §2 e referencia ⑦ (GDPR Art. 5(1)(c), minimizacao)
# ===========================================================================
_CAMPOS_DE_TEXTO = ("content", "text", "body", "last_message_preview", "message_text",
                    "transcript", "caption")
_RE_COPIA = re.compile(
    r"(payload|payload_redacted|input_payload|summary_redacted)\b[^\n]{0,120}?"
    r"\b(" + "|".join(_CAMPOS_DE_TEXTO) + r")\b")


def _copias_de_texto(fonte):
    fora = []
    for i, linha in enumerate(fonte.split("\n")):
        se = linha.split("#")[0]
        if _RE_COPIA.search(se):
            fora.append(i + 1)
    return fora


def bloco_7_sem_texto():
    _p("\n[7] SEM TEXTO -- nada do que o segurado escreveu entra no payload")
    if os.path.exists(CLAIMS_SHADOW):
        copias = _copias_de_texto(ler(CLAIMS_SHADOW))
        certo(not copias,
              "§2 claims_shadow.py nao copia texto do segurado para payload",
              "linhas %s -- a sombra guarda enum, contagem, tipo e timestamp. So." % copias)
    else:
        pular("[7] claims_shadow.py", _FALTA_SOMBRA or "o modulo ainda nao existe")

    # 🔴 CONTROLE: o casador ACHA a copia num snippet sintetico.
    ruim = 'payload = {"canal": canal, "content": mensagem.text}\n'
    ruim2 = 'input_payload={"confianca": c, "body": payload.text.message}\n'
    bom = 'payload = {"canal": canal, "tipo_documento": tipo}\n'
    certo(_copias_de_texto(ruim) == [1],
          "CONTROLE: o casador ACHA `content` copiado para payload")
    certo(_copias_de_texto(ruim2) == [1],
          "CONTROLE: o casador ACHA `body` copiado para input_payload")
    certo(_copias_de_texto(bom) == [],
          "CONTROLE: um payload so de enum passa",
          "um gate que reprova tudo e um carimbo ao contrario")


# ===========================================================================
# [8] AGENT_TASKS -- C⑦ (a Central mostra o trabalhador sem uma linha de frontend)
# ===========================================================================
WORKFLOW_DIGEST = "intelligence.claims_shadow_digest"


def bloco_8_agent_tasks():
    _p("\n[8] AGENT_TASKS -- o trabalhador `sombra_sinistros` e o card do digest")
    if agente_por_id is None or workflow_keys_sem_card is None:
        pular("[8] AGENT_TASKS", _FALTA_HB or "heartbeat/central ainda nao importam")
        return
    agente = agente_por_id("sombra_sinistros")
    vermelho_ate(agente is not None,
                 "C⑦ AGENT_TASKS tem o trabalhador `sombra_sinistros`",
                 "BLOCO C",
                 "📊 hoje ele nao existe. Sem card, a Central nao mostra o trabalhador "
                 "novo -- e o BLOCO C entrega justamente isso sem tocar no frontend.")
    if agente is not None:
        vermelho_ate(getattr(agente, "grupo", None) == "aprende_avisa",
                     "C⑦ ele esta no grupo `aprende_avisa`", "BLOCO C",
                     "veio %r" % getattr(agente, "grupo", None))
        vermelho_ate(bool(getattr(agente, "fonte_de_producao", None)),
                     "C⑦ ele declara `fonte_de_producao` (o que ele ENTREGA)", "BLOCO C",
                     "sem fonte ele pinta ⚫ NAO MEDIDO para sempre")
        vermelho_ate(getattr(agente, "cadencia_esperada_s", None) == 86400,
                     "C⑦ a cadencia declarada e 86400s (digest diario)", "BLOCO C",
                     "veio %r" % getattr(agente, "cadencia_esperada_s", None))
        eixo = getattr(agente, "eixo", None) or {}
        vermelho_ate(WORKFLOW_DIGEST in tuple(eixo.get("workflow_keys") or ()),
                     "C⑦ o eixo dele aponta para `%s`" % WORKFLOW_DIGEST, "BLOCO C",
                     "veio %r" % (eixo.get("workflow_keys"),))
    vermelho_ate(workflow_keys_sem_card([WORKFLOW_DIGEST]) == [],
                 "C⑦ `%s` tem card (o gate A② da SPEC-088 continua verde)" % WORKFLOW_DIGEST,
                 "BLOCO C",
                 "sem card, o guarda da 088 (test_a_central_diz_a_verdade) fica VERMELHO "
                 "-- e a 093-B teria quebrado a SPEC anterior")

    # 🔴 CONTROLE: um workflow inventado TEM de aparecer como sem card.
    inventado = "workflow.que.nunca.existiu.093b.xyz"
    certo(workflow_keys_sem_card([inventado]) == [inventado],
          "CONTROLE: um workflow_key inventado aparece como SEM CARD",
          "se este gate devolve vazio para qualquer coisa, ele nao cobre nada")


# ===========================================================================
# [9] REGRESSAO -- a linha de base do atendimento, medida HOJE, como SCRIPT
# ===========================================================================
#
# 🔴 COMO SCRIPT, e nao sob pytest, de proposito:
# 📊 `test_a_maquina_de_lavar_vai_ate_o_fim.py` chama `sys.exit` no nivel do modulo
# (:665) e CRASHA a coleta do pytest (P-093B-MAQUINA); `test_golden_do_eletricista.py`
# so expoe ao pytest a assercao de que os 10 casos EXISTEM -- os 10 rodam por `main()`
# (P-093B-GOLD, e e um carimbo pela CLAUDE.md §9.4). Rodar por subprocesso e a unica
# forma de medir o que eles realmente afirmam.
LINHA_DE_BASE_MAQUINA_OK = 112
LINHA_DE_BASE_GOLD_PROBLEMAS = 14
LINHA_DE_BASE_GOLD_EXPLODIU = 1


def _rodar_guarda(nome, segundos=180):
    caminho = os.path.join(RAIZ, "tests", nome)
    if not os.path.exists(caminho):
        return None, "", "%s nao existe" % nome
    amb = dict(os.environ)
    amb["PYTHONIOENCODING"] = "utf-8"
    try:
        r = subprocess.run([sys.executable, caminho], cwd=RAIZ, env=amb,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=segundos)
    except subprocess.TimeoutExpired:
        return None, "", "%s estourou %ds" % (nome, segundos)
    except Exception as e:  # noqa: BLE001
        return None, "", "%s: %s: %s" % (nome, type(e).__name__, e)
    return r.returncode, (r.stdout or "") + (r.stderr or ""), ""


def bloco_9_regressao():
    _p("\n[9] REGRESSAO -- a linha de base do atendimento (medida em 03/09/2026)")

    saida_cod, saida, erro = _rodar_guarda("test_a_maquina_de_lavar_vai_ate_o_fim.py")
    if erro:
        pular("[9] maquina de lavar", erro)
    else:
        certo(saida_cod == 0,
              "a maquina de lavar continua VERDE (exit 0)",
              "exit %r -- 🔴 a sombra OBSERVA; ela nao pode mudar um turno (§10)" % saida_cod)
        m = re.search(r"(\d+)\s+assercoes verdes\s*-\s*(\d+)\s+vermelhas", saida)
        certo(m is not None,
              "achei a contagem da maquina de lavar na saida",
              "sem a contagem, o exit 0 sozinho nao diz quantas asserces rodaram")
        if m:
            verdes, vermelhas = int(m.group(1)), int(m.group(2))
            certo(vermelhas == 0,
                  "maquina de lavar: 0 asserces vermelhas",
                  "vieram %d" % vermelhas)
            certo(verdes >= LINHA_DE_BASE_MAQUINA_OK,
                  "maquina de lavar: %d verdes (linha de base 📊 %d em 03/09/2026)"
                  % (verdes, LINHA_DE_BASE_MAQUINA_OK),
                  "caiu de %d para %d -- asserces somem quando um caminho deixa de "
                  "existir, e isso e regressao silenciosa"
                  % (LINHA_DE_BASE_MAQUINA_OK, verdes))

    saida_cod, saida, erro = _rodar_guarda("test_golden_do_eletricista.py")
    if erro:
        pular("[9] golden do eletricista", erro)
        return
    certo(saida_cod == 1,
          "o golden do eletricista continua com o vermelho PRE-EXISTENTE (exit 1)",
          "exit %r. Se virou 0, ALGUEM CONSERTOU o gold_007 -- otimo, e este teste "
          "tem de ser atualizado (§9.3), nao ignorado." % saida_cod)
    m = re.search(r"(\d+)\s+PROBLEMA\(S\)", saida)
    certo(m is not None, "achei a contagem de problemas do golden na saida")
    explodiu = re.findall(r"^\s*X\s+(\S+) EXPLODIU", saida, flags=re.M)
    certo(len(explodiu) == LINHA_DE_BASE_GOLD_EXPLODIU,
          "golden: exatamente %d caso EXPLODIU (linha de base 📊 03/09/2026)"
          % LINHA_DE_BASE_GOLD_EXPLODIU,
          "explodiram %r. 0 = alguem consertou (atualize a linha de base). "
          "2+ = REGRESSAO, e a sombra e a suspeita." % explodiu)
    certo(explodiu == ["gold_007_todos_os_slots_preenchidos"] or not explodiu,
          "golden: o caso que explode continua sendo o gold_007 (KeyError 'live')",
          "explodiu %r -- um caso NOVO explodindo e defeito desta SPEC" % explodiu)
    if m:
        problemas = int(m.group(1))
        certo(problemas <= LINHA_DE_BASE_GOLD_PROBLEMAS,
              "golden: %d problema(s) (linha de base 📊 %d em 03/09/2026)"
              % (problemas, LINHA_DE_BASE_GOLD_PROBLEMAS),
              "subiu de %d para %d -- a sombra acrescentou vermelho ao atendimento"
              % (LINHA_DE_BASE_GOLD_PROBLEMAS, problemas))
        _p("        📊 medido agora: maquina de lavar exit 0 · golden exit 1 com "
           "%d problema(s) e %d explosao(oes)" % (problemas, len(explodiu)))


# ===========================================================================
# [10] CONTROLE GERAL -- este guarda consegue ficar vermelho?
# ===========================================================================
def bloco_10_controle_geral():
    _p("\n[10] CONTROLE GERAL -- este guarda consegue ficar VERMELHO?")
    certo(os.path.exists(WEBHOOK), "backend/app/api/webhook.py existe")
    certo(os.path.exists(VOCAB), "lib/atendimento/claims-shadow-vocab.json existe")
    certo(os.path.exists(os.path.join(RAIZ, "tests",
                                      "test_a_maquina_de_lavar_vai_ate_o_fim.py")),
          "o guarda da regressao do atendimento existe")

    # o casador do gancho nao acha o que nao existe
    certo(not _linhas_do_gancho("x = AGENTE_INEXISTENTE_XYZ\n"),
          "CONTROLE: o casador do gancho NAO acha um nome inventado")
    certo(_linhas_do_gancho("await abrir_sombra(a, b)\n") == [1],
          "CONTROLE: o casador do gancho ACHA `abrir_sombra`")
    certo(not _linhas_do_gancho("# abrir_sombra(a, b)  -- comentado\n"),
          "CONTROLE: o casador do gancho IGNORA linha comentada",
          "um gancho em comentario nao roda, e nao pode pintar verde")

    if agente_por_id is not None:
        certo(agente_por_id("AGENTE_INEXISTENTE_XYZ") is None,
              "CONTROLE: o registro nao inventa agente")

    # 0-bis ② — o helper compartilhado que a sombra vai usar para nascer.
    # ⚠️ NAO e desta unidade construi-lo (outro builder o extrai de
    # `dispatch_router.py:545-548`). O guarda so DIZ se ele ja esta la, porque o
    # BLOCO A depende dele e o relatorio precisa do fato, nao da suposicao.
    # 🔴 `WorkRunService.criar` e o RPC `work_run_create` NAO servem: 📊 nenhum dos
    # dois aceita `conversation_id`, e o RPC enfileira no outbox -- o Smith worker
    # pegaria um run sem handler e o marcaria `failed`.
    vermelho_ate(criar_registro_sem_fila is not None,
                 "0-bis② `app.services.work.runs.criar_registro_sem_fila` existe",
                 "BLOCO 0-bis",
                 _FALTA_RUNS or "sem o helper, a sombra so nasce duplicando o INSERT "
                 "do dispatch_router -- e isso e motor paralelo (CLAUDE.md §5)")

    if contem_pii is not None:
        certo(contem_pii(CPF_SINTETICO) is True,
              "CONTROLE: `contem_pii` reconhece o CPF sintetico",
              "se o redator canonico nao pega este formato, o gate de PII do [3] "
              "estava verde por cegueira, nao por limpeza")
        certo(contem_pii("auto") is False,
              "CONTROLE: `contem_pii` NAO acusa um enum limpo",
              "um redator que acusa tudo faz a sombra gravar {} sempre")
    else:
        pular("[10] contem_pii", _FALTA_PII)


# ---------------------------------------------------------------------------
def main() -> int:
    _p("=" * 78)
    _p("  O SINISTRO DEIXA RASTRO -- SPEC-093-B  (BLOCO E + GATE ZERO do 0-bis)")
    _p("=" * 78)
    bloco_0_gate_zero()
    bloco_1_vocabulario()
    bloco_2_deteccao()
    bloco_3_ledger()
    bloco_4_dois_tenants()
    bloco_5_variantes()
    bloco_6_prazos()
    bloco_7_sem_texto()
    bloco_8_agent_tasks()
    bloco_9_regressao()
    bloco_10_controle_geral()

    de_verdade = FAIL - len(ESPERADOS)
    _p("\n" + "=" * 78)
    _p("  %d ok · %d falhas (%d VERMELHO ESPERADO + %d de verdade) · %d pulados"
       % (OK, FAIL, len(ESPERADOS), de_verdade, len(PULADOS)))
    if ESPERADOS:
        _p("\n  🔴 VERMELHO ESPERADO -- a SPEC-093-B PREVE estes ate o bloco citado.")
        _p("     O exit code e 1 mesmo assim (CLAUDE.md §9.3: nao se afrouxa).")
        for x in ESPERADOS:
            _p("     · %s" % x)
    if de_verdade > 0:
        _p("\n  ⛔ HA %d VERMELHO DE VERDADE acima -- procure as linhas `FALHA`."
           % de_verdade)
    if JA_PODEM_VIRAR:
        _p("\n  ✅ ESTES JA FICARAM VERDES. O INTEGRADOR troca `vermelho_ate(...)` por")
        _p("     `certo(...)` e apaga o argumento do bloco -- senao o guarda passa a")
        _p("     guardar verdade vencida (CLAUDE.md §9.3):")
        for x in JA_PODEM_VIRAR:
            _p("     · %s" % x)
    if PULADOS:
        _p("\n  -- pulados: %s" % " · ".join(PULADOS))
    _p("=" * 78)
    return 1 if FAIL else 0


def test_o_sinistro_deixa_rastro():
    """⚠️ FALHA DE PROPOSITO ate o BLOCO A da SPEC-093-B existir.

    A prova nasce antes do codigo (protocolo §4, nivel CRITICO). Quem rodar a suite
    hoje ve este teste vermelho com a lista de VERMELHO ESPERADO na saida -- e essa e
    a informacao que o executor precisa. Marcar `xfail` aqui esconderia exatamente o
    que a SPEC ainda deve.
    """
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
