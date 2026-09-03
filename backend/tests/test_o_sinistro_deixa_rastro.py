# -*- coding: utf-8 -*-
"""O sinistro deixa rastro — o guarda da SPEC-093-B (BLOCO E + o GATE ZERO do 0-bis).

🔴 **ESTE ARQUIVO NASCEU VERMELHO, E ERA PARA NASCER.** Ele foi escrito ANTES do
código (protocolo §4: quem faz a prova não faz a resposta). O gate ⓪ — o ELO da SPEC —
mede que uma mensagem de sinistro atravessa o webhook **no modo observação** e abre a
sombra; enquanto nenhuma sombra abria, ⓪ REPROVAVA, `main()` devolvia **1** e o `def
test_` do pytest FALHAVA. Isso nunca foi afrouxado: `CLAUDE.md` §9.3 — um guarda que
fica verde por conveniência é um carimbo.

📊 **03/09/2026, depois da rodada de conserto do painel** (`23cb27b`): 220 asserções
verdes, 0 vermelhas, 0 puladas. O que era `vermelho_ate('BLOCO A'…)` virou
`certo_bloco(…)` — a mesma linha, uma palavra de diferença — porque um `vermelho_ate`
que ficou verde e continuou lá é verdade vencida guardada.

⚠️ A saída separa **VERMELHO ESPERADO** de **VERMELHO DE VERDADE**. O exit code é 1
nos dois casos. Quando um "vermelho esperado" fica verde, o guarda IMPRIME a instrução
de trocar `vermelho_ate(...)` por `certo_bloco(...)` — é assim que ele não passa a
guardar verdade vencida.

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
[11] RESUMO ADMIN   D①②③④  o contrato fechado, os zeros sem erro, o master admin,
                           e ZERO campo textual no JSON
```

Os blocos que a RODADA DE CONSERTO acrescentou (painel de 03/09/2026)
----------------------------------------------------------------------
📊 O painel (4 lentes + red team, contexto limpo, sobre o diff) achou 7 blockers, e
**quatro deles existiam porque o guarda não os pegava**. Um guarda que não consegue
ficar vermelho com o defeito que ele existe para pegar é um carimbo (§9.3):

```
[12] TENANT PELO MOTOR      o [4] media contra o BANCO, e o banco tem ZERO sombra dos
                            dois lados: "0 = 0" e o que um filtro QUEBRADO tambem da.
                            Aqui a mutacao M3 (cliente cego a `company_id`) fica
                            VERMELHA -- antes ela passava cega
[13] DIGEST PONTA A PONTA   `digerir()` nao tinha UM teste. 3 sombras -> 1 variante ->
                            2 sinais; dedupe na 2a rodada; `truncado` no sinal; e a
                            mutacao M2 (sem ordenacao) colapsando duas variantes em uma
[14] O QUE ELA NAO PODE     a sombra chegando ao briefing (C7) · o detector abrindo em
                            frase de venda (C1) · `tem_numero` de UM digito (C2) ·
                            valor sem enum no Python (C4) · contador de seguradora
                            contando espera de humano (C6) · evento sem escritor no
                            vocabulario (C5)
[15] SEM TEXTO NOS 4        o [7] varre `claims_shadow.py`; quem MONTA o payload sao os
                            quatro escritores, e cada um tem o texto do segurado numa
                            variavel ao lado
[16] DEVOLVE O AMBIENTE     o guarda desfaz as cascas e os shims -- uma suite cujo
                            resultado depende da ORDEM nao mede nada
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

⚠️ **M2 e M3 deixaram de depender de alguém lembrar de editar e restaurar o arquivo.**
Elas rodam DENTRO da bateria, em memória: a M3 pelo `BancoFalsoSemTenant` (um cliente
cujo `.eq("company_id", …)` não filtra) no bloco [12], e a M2 trocando
`claims_shadow_digest.trajetorias_de` por uma versão sem ordenação no bloco [13]. Cada
uma tem a sua linha de CONTROLE afirmando que, **sem** a peça, o resultado é OUTRO —
que é o que dá direito à conclusão (CLAUDE.md §9.2).
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

    ⛔ **E ela DESFAZ o que fez** (`_restaurar_sys_modules`, chamado no `finally` de
    `main()`). 📊 Medido em 03/09/2026 pela lente 3 do painel: sem a restauração, este
    guarda deixava `app`, as seis cascas e todo submódulo carregado por elas dentro do
    `sys.modules` do processo — e o pytest roda os arquivos no MESMO processo. O
    resultado foi um guarda da SPEC-086 (`test_SEM_corretora_o_repositorio_devolve_
    VAZIO_e_nao_TUDO`) que passa sozinho e falha quando roda DEPOIS deste, porque
    `o_fim_do_atendimento` passou a conseguir importar `app.services.claims_shadow` e
    ganhou um SELECT a mais. **Uma suíte cujo resultado depende da ORDEM não mede
    nada** (CLAUDE.md §9.3).
    """
    for sub in ("api", "services", "agents", "tasks", "factories", "core"):
        nome = "app." + sub
        atual = sys.modules.get(nome)
        if atual is not None and getattr(atual, "__file__", None) is None:
            continue          # já é casca
        casca = types.ModuleType(nome)
        casca.__path__ = [os.path.join(APP, sub)]
        _guardar_modulo(nome)
        sys.modules[nome] = casca


#: O que o guarda encontrou em `sys.modules` ANTES de mexer: `nome -> módulo` para o
#: que existia, `nome -> _AUSENTE` para o que não existia. ⚠️ Só a PRIMEIRA gravação
#: por nome vale — a segunda guardaria a casca como se fosse o original.
_AUSENTE = object()
_MODULOS_ORIGINAIS: dict = {}
#: Fotografia de `sys.modules` no momento do primeiro toque. O que aparecer depois e
#: cair sob um prefixo nosso é entulho DESTE guarda, e sai junto.
_MODULOS_NO_INICIO: set = set()


def _guardar_modulo(nome):
    if nome not in _MODULOS_ORIGINAIS:
        _MODULOS_ORIGINAIS[nome] = sys.modules.get(nome, _AUSENTE)


def _fotografar_sys_modules():
    global _MODULOS_NO_INICIO
    if not _MODULOS_NO_INICIO:
        _MODULOS_NO_INICIO = set(sys.modules)


def _RAIZES_DE_SHIM():
    """Os pacotes-raiz das bibliotecas de terceiro que o guarda falsificou."""
    return {n.split(".")[0] for n in _SHIMS}


def _restaurar_sys_modules():
    """Devolve `sys.modules` ao estado em que este guarda o encontrou.

    Três limpezas, e cada uma pega o que as outras não pegam:
      · os módulos que o guarda SUBSTITUIU (as cascas e os falsos) voltam ao original;
      · os SHIMS de biblioteca de terceiro saem;
      · todo `app.*` que entrou DEPOIS da fotografia sai — senão um submódulo real
        carregado sob uma casca continuaria em cache com o `__init__` do pacote
        nunca executado, que é a mesma mentira em outro lugar.
    """
    # ⚠️ `_guardar_modulo` NÃO serve para estes: ele lê `sys.modules` AGORA, e agora
    # o que está lá é o entulho — guardá-lo seria "restaurar" o módulo para ele
    # mesmo. O que entrou depois da fotografia sai, e ponto.
    for nome in sorted(sys.modules):
        if nome in _MODULOS_NO_INICIO or nome in _MODULOS_ORIGINAIS:
            continue
        raiz = nome.split(".")[0]
        if nome == "app" or nome.startswith("app.") or raiz in _RAIZES_DE_SHIM():
            _MODULOS_ORIGINAIS[nome] = _AUSENTE
    for nome, anterior in list(_MODULOS_ORIGINAIS.items()):
        if anterior is _AUSENTE:
            sys.modules.pop(nome, None)
        else:
            sys.modules[nome] = anterior
    _MODULOS_ORIGINAIS.clear()
    del _SHIMS[:]


_fotografar_sys_modules()
try:
    _guardar_modulo("app")
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
sombra_da_conversa = registrar_gesto = None
tem_numero = None
digerir = trajetorias_de = summary_de_contadores = None
FindingEngine = None
espera_vencida = PRAZOS = None
criar_registro_sem_fila = None
agente_por_id = workflow_keys_sem_card = None
contem_pii = None

_FALTA_SOMBRA = _FALTA_PRAZOS = _FALTA_RUNS = _FALTA_HB = _FALTA_PII = ""
_FALTA_DIGEST = _FALTA_FINDING = _FALTA_TEM_NUMERO = ""
try:
    from app.services.claims_shadow import (  # type: ignore  # noqa: F401
        abrir_sombra,
        contadores_de,
        detectar_sinistro,
        registrar_evento,
        registrar_gesto,
        sombra_da_conversa,
        variantes_de,
    )
except Exception as _e:  # noqa: BLE001
    _FALTA_SOMBRA = "app.services.claims_shadow: %s: %s" % (type(_e).__name__, _e)
# 🔴 CONSERTO C2 — o nome não existe hoje. Import SEPARADO de propósito: se ele
# entrasse no `from … import` de cima, a ausência de UMA função derrubaria os
# blocos [0]–[11] inteiros, e o guarda pularia pelo motivo errado.
try:
    from app.services.claims_shadow import tem_numero  # type: ignore  # noqa: F401,F811
except Exception as _e:  # noqa: BLE001
    _FALTA_TEM_NUMERO = "app.services.claims_shadow.tem_numero: %s: %s" % (
        type(_e).__name__, _e)
try:
    from app.services.claims_shadow_digest import (  # type: ignore  # noqa: F401,F811
        digerir,
        summary_de_contadores,
        trajetorias_de,
    )
except Exception as _e:  # noqa: BLE001
    _FALTA_DIGEST = "app.services.claims_shadow_digest: %s: %s" % (type(_e).__name__, _e)
try:
    from app.services.intelligence.finding_engine import FindingEngine  # type: ignore  # noqa: F401,F811
except Exception as _e:  # noqa: BLE001
    _FALTA_FINDING = "app.services.intelligence.finding_engine: %s: %s" % (
        type(_e).__name__, _e)
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

# BLOCO D — o resumo admin. ⚠️ O guarda importa o CORPO da rota (`montar_resumo_...`),
# não o `async def` decorado: um gate que só sabe bater no HTTP precisa do servidor de
# pé, e um gate que não roda não guarda (CLAUDE.md §9.3). O `require_master_admin` é
# conferido no TEXTO do arquivo, como faz o bloco [9] do guarda da SPEC-088.
montar_resumo_claims_shadow = None
CHAVES_CS = CHAVES_CS_CORRETORA = CHAVES_CS_VARIANTE = CHAVES_CS_TOTAIS = ()
_FALTA_ADMIN = ""
try:
    from app.api.admin_spec034 import (  # type: ignore  # noqa: F401,F811
        CLAIMS_SHADOW_CHAVES as CHAVES_CS,
        CLAIMS_SHADOW_CHAVES_CORRETORA as CHAVES_CS_CORRETORA,
        CLAIMS_SHADOW_CHAVES_TOTAIS as CHAVES_CS_TOTAIS,
        CLAIMS_SHADOW_CHAVES_VARIANTE as CHAVES_CS_VARIANTE,
        montar_resumo_claims_shadow,
    )
except Exception as _e:  # noqa: BLE001
    _FALTA_ADMIN = "app.api.admin_spec034 (BLOCO D): %s: %s" % (type(_e).__name__, _e)


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


def certo_bloco(cond, rotulo, bloco, detalhe=""):
    """O bloco `bloco` JA FOI ENTREGUE (03/09/2026): o que era `vermelho_ate` virou gate
    de verdade. Mesma assinatura, para o diff ser de UMA palavra por linha."""
    return certo(cond, rotulo, detalhe)


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
        gravadas = []
        for x in (linha if isinstance(linha, list) else [linha]):
            x = dict(x)
            # 🔴 O FALSO VIVO (`vivo=True`): a linha inserida passa a EXISTIR para o
            # SELECT seguinte, e ganha `id` como a tabela real ganharia.
            # ⚠️ Só no modo vivo, e o padrão continua sendo o antigo: os blocos
            # [0]–[11] foram escritos contra um falso que só REGISTRA o INSERT, e
            # mudar isso para todos seria mudar o que eles medem sem dizer.
            if self._banco.vivo:
                if not x.get("id"):
                    self._banco.proximo_id += 1
                    x["id"] = "fake-%s-%d" % (self._nome, self._banco.proximo_id)
                self._banco.linhas.setdefault(self._nome, []).append(x)
            self._banco.inseridos.append((self._nome, dict(x)))
            gravadas.append(x)
        if isinstance(linha, list):
            self._linha = gravadas
        elif gravadas:
            self._linha = gravadas[0]
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
        if self._op == "select":
            # 🔴 A FALHA FORÇADA de leitura (`falhar_no_select`). Ela existe para um
            # gate só: `ler_paginado` devolve `truncou=True` tanto no teto quanto na
            # página que FALHOU ("meia leitura não é leitura", `leitura_completa.py`).
            # Forçar uma página CHEIA exigiria 1.000 linhas de fixture; forçar a
            # falha exercita o MESMO caminho de `truncou` com três.
            restam = self._banco.falhar_no_select.get(self._nome, 0)
            if restam:
                self._banco.falhar_no_select[self._nome] = restam - 1
                raise RuntimeError("falha de leitura forcada em %s" % self._nome)
        if self._op != "select":
            linhas = self._linha if isinstance(self._linha, list) else [self._linha]
            return _Resposta([x for x in linhas if x])
        base = self._banco.linhas.get(self._nome, [])
        return _Resposta([r for r in base
                          if all(str(r.get(c)) == str(v) for c, v in self._filtros)])


class BancoFalso:
    def __init__(self, linhas=None, vivo=False, falhar_no_select=None):
        self.linhas = {k: list(v) for k, v in (linhas or {}).items()}
        self.inseridos = []
        self.updates = []
        #: `vivo=True`: o INSERT vira linha visível ao SELECT e ganha `id`.
        self.vivo = bool(vivo)
        self.proximo_id = 0
        #: `{tabela: n}` — as próximas `n` leituras dessa tabela LEVANTAM.
        self.falhar_no_select = dict(falhar_no_select or {})

    def table(self, nome):
        return _Tabela(self, nome)

    def de(self, tabela):
        return [x for n, x in self.inseridos if n == tabela]

    def linhas_de(self, tabela):
        """O que o SELECT enxergaria — no modo vivo, inclui o que foi inserido."""
        return list(self.linhas.get(tabela, []))


class ClienteFalso:
    """O que o código chama de `db`/`supabase`: um objeto com `.client`."""

    def __init__(self, banco):
        self.client = banco


class _TabelaCegaAoTenant(_Tabela):
    """🔴 A MUTAÇÃO M3, aplicada em MEMÓRIA: `.eq("company_id", …)` não filtra nada.

    ⚠️ Por que aqui e não editando `claims_shadow.py`: a mutação da SPEC manda tirar
    o filtro de tenant da leitura da sombra, e o §9.3 exige que o guarda fique
    VERMELHO com ela. Fazer isso pelo CLIENTE tem duas vantagens medidas: roda dentro
    da própria bateria (não depende de alguém lembrar de editar e restaurar o arquivo)
    e ataca exatamente o ponto em que o filtro protege — a consulta. O que o guarda
    afirma é que, sem o filtro, o resultado MUDA; se não mudar, o filtro não estava
    protegendo coisa nenhuma e o gate [12] era um carimbo.
    """

    def eq(self, coluna, valor):
        if str(coluna) == "company_id":
            return self
        return _Tabela.eq(self, coluna, valor)


class BancoFalsoSemTenant(BancoFalso):
    def table(self, nome):
        return _TabelaCegaAoTenant(self, nome)


# ---------------------------------------------------------------------------
# AS FIXTURES — 💭 textos INVENTADOS. Nenhum veio do acervo de um segurado.
# ---------------------------------------------------------------------------
EMPRESA_A = "aaaaaaaa-0000-4000-8000-000000000001"
EMPRESA_B = "bbbbbbbb-0000-4000-8000-000000000002"
CONVERSA_A = "cccccccc-0000-4000-8000-00000000000a"
CONVERSA_B = "cccccccc-0000-4000-8000-00000000000b"
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
    certo_bloco(bool(ganchos),
                 "webhook.py CHAMA a sombra em algum lugar",
                 "BLOCO A",
                 "📊 hoje: zero ocorrencias de claims_shadow/abrir_sombra/detectar_sinistro "
                 "em webhook.py. A SPEC-093-B BLOCO A ainda nao existe -- a sombra nao abriu.")
    if ganchos and fim:
        certo_bloco(min(ganchos) < fim,
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
    # ⚠️ O rótulo cita a linha MEDIDA (`fim`), nunca um número escrito à mão. 📊 O
    # `:782` que estava aqui já nasceu vencido: o aquecimento mediu 782, o desenhista
    # 783, e o `return` anda a cada edição do webhook. Um guarda que anuncia a linha
    # errada ensina a desconfiar do guarda.
    certo("PASSOU_DO_RETURN" not in trilha,
          "o fluxo PAROU no `return` do modo observacao (webhook.py:%s) -- o grafo "
          "NAO foi chamado" % (fim if fim else "?"),
          "a sentinela do billing foi tocada: o fluxo seguiu para a IA. trilha: %s" % trilha)
    certo(envios == [],
          "NENHUMA mensagem saiu para o segurado",
          "envios: %d" % len(envios))
    sombras = [l for l in banco.de("work_runs") if l.get("workflow_key") == WORKFLOW]
    certo_bloco(len(sombras) == 1,
                 "UMA sombra (work_runs.workflow_key='claims.shadow') foi aberta",
                 "BLOCO A",
                 "📊 gravou %d linha(s) em work_runs; as tabelas tocadas foram %s. "
                 "BLOCO A ainda nao existe / a sombra nao abriu."
                 % (len(sombras), sorted({n for n, _ in banco.inseridos})))
    if sombras:
        certo_bloco(str(sombras[0].get("conversation_id") or "") == CONVERSA_A,
                     "a sombra guarda o conversation_id (a chave de reidentificacao)",
                     "BLOCO A")
        certo_bloco(str(sombras[0].get("company_id") or "") == EMPRESA_A,
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
#: 🔴 DEZ eventos, e não os onze da §5 da SPEC — CONSERTO C5.
#: 📊 A lente 1 do painel mediu em 03/09/2026: `claims.seguradora_respondeu` não tem
#: ESCRITOR em lugar nenhum (a linha da §5 aponta para "`attendance_capture`/
#: `dispatch_router` quando há sombra", e nenhum dos dois chama a sombra). Um evento
#: declarado e nunca escrito é uma promessa: o digest o procura, o admin o lista como
#: chave possível, e o leitor conclui que a seguradora nunca respondeu — quando o que
#: aconteceu foi ninguém ter gravado. **Vocabulário é contrato, não desejo**
#: (P-093B-SEGURADORA guarda o que o traria de volta).
EVENTOS_ESPERADOS = {
    "claims.sombra_aberta", "claims.handoff_pedido", "claims.humano_assumiu",
    "claims.humano_devolveu", "claims.humano_respondeu", "claims.nota_registrada",
    "claims.documento_recebido",
    "claims.espera_aberta", "claims.espera_satisfeita", "claims.encerrado",
}
# 📊 O CHECK real de `work_events.actor_type`, lido do banco em 03/09/2026 e
# transcrito em `dispatch_router.ATORES_VALIDOS` (:562).
# ⛔ `human` NAO esta na lista: escrever esse valor e um INSERT que o Postgres
# recusa -- e `_evento` engole a recusa. Um evento que nunca acontece.
ATORES_DO_CHECK = {"system", "worker", "user", "agent", "admin", "provider"}
#: 🔴 OITO enums — CONSERTO C5. `motivo_enum` entra porque ele é o payload inteiro de
#: `claims.handoff_pedido` e HOJE não tem enum declarado: 📊 `human_handoff.py:674`
#: grava `"sinistro"` ou `"outro"`, e sem a lista no vocabulário o validador de valor
#: do CONSERTO C4 não tem contra o que validar — a chave cairia na regra de "slug
#: qualquer", que é a porta por onde texto entra.
ENUMS_ESPERADOS = {"confianca", "motivo", "motivo_enum", "origem", "canal",
                   "tipo_documento", "kind", "desfecho"}


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
    certo_bloco(set(eventos) == EVENTOS_ESPERADOS,
                "os %d eventos COM ESCRITOR estao la, nem a mais nem a menos"
                % len(EVENTOS_ESPERADOS), "CONSERTO C5",
                "faltam %s · sobram %s -- evento sem escritor promete rastro que "
                "ninguem grava" % (sorted(EVENTOS_ESPERADOS - set(eventos)),
                                   sorted(set(eventos) - EVENTOS_ESPERADOS)))
    fora = sorted({e: d.get("ator") for e, d in eventos.items()
                   if d.get("ator") not in ATORES_DO_CHECK}.items())
    certo(not fora,
          "TODO `ator` do vocabulario esta no CHECK de work_events",
          "fora do CHECK: %s -- `human` nao existe e o INSERT some sem erro" % fora)
    certo_bloco(set(v.get("enums") or {}) == ENUMS_ESPERADOS,
                "os %d enums estao la (com `motivo_enum`)" % len(ENUMS_ESPERADOS),
                "CONSERTO C5",
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
    certo_bloco(agente is not None,
                 "C⑦ AGENT_TASKS tem o trabalhador `sombra_sinistros`",
                 "BLOCO C",
                 "📊 hoje ele nao existe. Sem card, a Central nao mostra o trabalhador "
                 "novo -- e o BLOCO C entrega justamente isso sem tocar no frontend.")
    if agente is not None:
        certo_bloco(getattr(agente, "grupo", None) == "aprende_avisa",
                     "C⑦ ele esta no grupo `aprende_avisa`", "BLOCO C",
                     "veio %r" % getattr(agente, "grupo", None))
        certo_bloco(bool(getattr(agente, "fonte_de_producao", None)),
                     "C⑦ ele declara `fonte_de_producao` (o que ele ENTREGA)", "BLOCO C",
                     "sem fonte ele pinta ⚫ NAO MEDIDO para sempre")
        certo_bloco(getattr(agente, "cadencia_esperada_s", None) == 86400,
                     "C⑦ a cadencia declarada e 86400s (digest diario)", "BLOCO C",
                     "veio %r" % getattr(agente, "cadencia_esperada_s", None))
        eixo = getattr(agente, "eixo", None) or {}
        certo_bloco(WORKFLOW_DIGEST in tuple(eixo.get("workflow_keys") or ()),
                     "C⑦ o eixo dele aponta para `%s`" % WORKFLOW_DIGEST, "BLOCO C",
                     "veio %r" % (eixo.get("workflow_keys"),))
    certo_bloco(workflow_keys_sem_card([WORKFLOW_DIGEST]) == [],
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
    certo_bloco(criar_registro_sem_fila is not None,
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




# ===========================================================================
# [11] RESUMO ADMIN -- D①②③④: o contrato fechado, os zeros, o master admin, zero texto
# ===========================================================================
#
# 🔴 O QUE ESTE BLOCO MATA. A rota do BLOCO D é a única peça da 093-B que um humano
# lê como número. Um campo textual que escape aqui não trava nada e não aparece em
# log: ele simplesmente vira PII na tela do admin — o defeito silencioso do §9.5.
# Por isso o gate ⓸ não pergunta "o autor lembrou de redigir?", e sim "existe ALGUM
# `str` no JSON que não seja uuid, timestamp, slug, enum ou hash?".
#
# ⚠️ E o contrato é conferido contra as tuplas que a PRÓPRIA rota exporta, não contra
# uma lista copiada para cá. Duas listas divergem em silêncio; uma só não tem como.
_RE_VALOR_SEM_TEXTO = re.compile(r"^[A-Za-z0-9_.:+\-]*$")


def _valores_textuais(no, caminho="raiz"):
    """Todo `str` do JSON que NÃO é uuid, timestamp ISO, slug, enum ou hash.

    Puro de propósito: recebe a estrutura, devolve a lista de ofensores. É o que
    permite a linha de CONTROLE provar que ele CONSEGUE achar texto (§9.3).
    """
    fora = []
    if isinstance(no, dict):
        for k, v in no.items():
            if isinstance(k, str) and not _RE_VALOR_SEM_TEXTO.match(k):
                fora.append("%s.<chave %r>" % (caminho, k[:40]))
            fora.extend(_valores_textuais(v, "%s.%s" % (caminho, k)))
    elif isinstance(no, (list, tuple)):
        for i, v in enumerate(no):
            fora.extend(_valores_textuais(v, "%s[%d]" % (caminho, i)))
    elif isinstance(no, str) and not _RE_VALOR_SEM_TEXTO.match(no):
        fora.append("%s = %r" % (caminho, no[:40]))
    return fora


def _fora_do_contrato(d, esperadas):
    """As chaves que faltam e as que sobram. Contrato FECHADO: sobrar é reprovar."""
    if not isinstance(d, dict):
        return ["nao e um dict: %s" % type(d).__name__]
    return (["falta '%s'" % k for k in esperadas if k not in d]
            + ["intrusa '%s'" % k for k in d if k not in esperadas])


def _rota_exige_master_admin(texto_rota, nome_rota):
    """A rota tem `Depends(require_master_admin)` na assinatura logo abaixo do
    decorador. Mesmo helper do bloco [9] do guarda da SPEC-088 — puro, para a linha
    de controle poder provar que ele reprova."""
    m = re.search(r'@router\.get\("/%s"\)\s*\n\s*async def \w+\(([^)]*)\)'
                  % re.escape(nome_rota), texto_rota)
    return bool(m) and "require_master_admin" in m.group(1)


def _banco_do_resumo():
    """Uma sombra da EMPRESA_A com dois gestos — e UM evento da EMPRESA_B pendurado
    no mesmo run. 🔴 O evento intruso é fixture de propósito: ele não deveria existir,
    e se a rota o contar, o número da A carrega trabalho da B (CLAUDE.md §7)."""
    return BancoFalso({
        "work_runs": [{"id": RUN_SOMBRA_A, "company_id": EMPRESA_A,
                       "workflow_key": WORKFLOW, "status": "running",
                       "created_at": "2026-09-01T10:00:00+00:00"}],
        "work_events": [
            {"id": 1, "work_run_id": RUN_SOMBRA_A, "company_id": EMPRESA_A,
             "event_type": "claims.sombra_aberta", "created_at": "2026-09-01T10:00:00+00:00",
             "payload_redacted": {"ramo": "auto", "seguradora_slug": "porto"}},
            {"id": 2, "work_run_id": RUN_SOMBRA_A, "company_id": EMPRESA_A,
             "event_type": "claims.espera_aberta", "created_at": "2026-09-01T11:00:00+00:00",
             "payload_redacted": {"kind": "esperando_seguradora"}},
            {"id": 3, "work_run_id": RUN_SOMBRA_A, "company_id": EMPRESA_B,
             "event_type": "claims.encerrado", "created_at": "2026-09-01T12:00:00+00:00",
             "payload_redacted": {"desfecho": "pago"}},
        ],
        "work_waits": [{"id": "w1", "company_id": EMPRESA_A, "work_run_id": RUN_SOMBRA_A,
                        "kind": "esperando_seguradora", "status": "ativo",
                        "created_at": "2026-09-01T11:00:00+00:00", "satisfeito_em": None}],
        "intelligence_signals": [{"id": "s1", "company_id": EMPRESA_A,
                                  "signal_type": "process_variant",
                                  "source_type": "claims_shadow",
                                  "created_at": "2026-09-02T00:00:00+00:00"}],
    })


def bloco_11_resumo_admin():
    _p("\n[11] RESUMO ADMIN -- o contrato fechado, os zeros, o master admin, zero texto")

    caminho = os.path.join(APP, "api", "admin_spec034.py")
    rota_txt = ler(caminho) if os.path.exists(caminho) else ""
    certo(_rota_exige_master_admin(rota_txt, "claims-shadow"),
          "D② /claims-shadow exige require_master_admin na assinatura",
          "sem a dependencia, a visao de PLATAFORMA (sem filtro de company_id) fica "
          "aberta -- e ela mostra TODAS as corretoras de uma vez")
    certo(not _rota_exige_master_admin(
        '@router.get("/claims-shadow")\nasync def claims_shadow() -> dict:\n    return {}\n',
        "claims-shadow"),
        "CONTROLE: a MESMA rota sem a dependencia REPROVA",
        "senao o gate acima passaria por nao saber olhar")
    certo("spec093b:claims-shadow:v1" in rota_txt and "CLAIMS_SHADOW_CACHE_S = 60" in rota_txt,
          "D② a chave de cache e 60s estao no codigo (`spec093b:claims-shadow:v1`)")

    if montar_resumo_claims_shadow is None:
        pular("[11] RESUMO ADMIN", _FALTA_ADMIN or "montar_resumo_claims_shadow nao existe")
        return

    # ---- D③ banco VAZIO: zeros, contrato inteiro, e NENHUM erro ---------------
    vazio, erro = None, ""
    try:
        vazio = montar_resumo_claims_shadow(BancoFalso({}))
    except Exception as e:  # noqa: BLE001
        erro = "%s: %s" % (type(e).__name__, e)
    certo(erro == "", "D③ com banco vazio a rota NAO levanta", erro)
    if vazio is not None:
        certo(not _fora_do_contrato(vazio, CHAVES_CS),
              "D① banco vazio devolve o contrato INTEIRO",
              " · ".join(_fora_do_contrato(vazio, CHAVES_CS)))
        certo(vazio.get("corretoras") == []
              and not _fora_do_contrato(vazio.get("totais"), CHAVES_CS_TOTAIS)
              and all(v == 0 for v in (vazio.get("totais") or {}).values()),
              "D③ banco vazio devolve ZEROS (nao null, nao ausente)",
              repr(vazio.get("totais"))[:120])

    # ---- D① e D④ com dados: contrato fechado, e nenhum campo textual ---------
    cheio, erro = None, ""
    try:
        cheio = montar_resumo_claims_shadow(_banco_do_resumo())
    except Exception as e:  # noqa: BLE001
        erro = "%s: %s" % (type(e).__name__, e)
    certo(erro == "", "D③ com uma sombra a rota NAO levanta", erro)
    if cheio is None:
        return

    certo(not _fora_do_contrato(cheio, CHAVES_CS),
          "D① a raiz tem exatamente as chaves de CLAIMS_SHADOW_CHAVES",
          " · ".join(_fora_do_contrato(cheio, CHAVES_CS)))

    corretoras = cheio.get("corretoras") or []
    certo(len(corretoras) == 1, "a sombra da EMPRESA_A aparece (1 corretora)",
          "vieram %d" % len(corretoras))
    if corretoras:
        c = corretoras[0]
        certo(not _fora_do_contrato(c, CHAVES_CS_CORRETORA),
              "D① a corretora tem exatamente as chaves de CHAVES_CORRETORA",
              " · ".join(_fora_do_contrato(c, CHAVES_CS_CORRETORA)))
        variantes = c.get("top_variantes") or []
        certo(bool(variantes) and not _fora_do_contrato(variantes[0], CHAVES_CS_VARIANTE),
              "D① a variante tem exatamente as chaves de CHAVES_VARIANTE",
              " · ".join(_fora_do_contrato(variantes[0], CHAVES_CS_VARIANTE))
              if variantes else "nenhuma variante")
        certo(all("work_run_ids" not in v and "work_run_id" not in v for v in variantes),
              "D④ a variante NAO carrega `work_run_ids`",
              "id de execucao amarra a estatistica a um caso -- o oposto do agregado")
        # 🔴 §7: o evento da EMPRESA_B pendurado na sombra da A NAO entra na conta da A.
        certo("claims.encerrado" not in (c.get("eventos_por_tipo") or {}),
              "§7 o evento de OUTRA corretora nao entra no numero desta",
              "eventos_por_tipo = %r" % (c.get("eventos_por_tipo"),))
        certo((c.get("contadores") or {}).get("total") == 1
              and (c.get("prazos") or {}).get("total") == 1,
              "§12.1 contadores e prazos saem COM denominador (`total`)")

    ofensores = _valores_textuais(cheio)
    certo(not ofensores, "D④ NENHUM campo textual no JSON (so uuid, ISO, slug, enum, hash)",
          " · ".join(ofensores[:4]))

    # ---- CONTROLE: os dois conferidores CONSEGUEM reprovar -------------------
    intrusa = dict(cheio)
    intrusa["resumo_do_atendimento"] = "o segurado bateu o carro na esquina"
    certo(bool(_fora_do_contrato(intrusa, CHAVES_CS)),
          "CONTROLE: uma chave INTRUSA no JSON reprova o contrato",
          "um contrato que aceita chave a mais nao e fechado")
    certo(bool(_valores_textuais(intrusa)),
          "CONTROLE: o varredor de texto ACHA a frase de conversa que plantei")
    certo(not _valores_textuais(
        {"company_id": EMPRESA_A, "gerado_em": "2026-09-03T11:00:00+00:00",
         "passos": ["claims.sombra_aberta"], "assinatura": "a1b2c3", "n": 3,
         "ramo": "auto-frota", "media_dias": 2.0}),
        "CONTROLE: o varredor NAO acusa uuid, ISO, slug com hifen nem enum",
        "um varredor que acusa tudo obrigaria a rota a devolver so numeros")


# ===========================================================================
# [12] DOIS TENANTS PELO MOTOR -- A④ B④ C⑥ pelo CODIGO, e a mutacao M3 VERMELHA
# ===========================================================================
#
# 🔴 POR QUE ESTE BLOCO EXISTE, E POR QUE O [4] NAO BASTAVA.
#
# 📊 Medido pelo painel em 03/09/2026 (lentes 1 e 4, achado B7): o bloco [4] mede o
# isolamento CONTRA O BANCO, e hoje o banco tem ZERO sombra dos dois lados. "0 = 0" e
# o resultado que um filtro QUEBRADO tambem produz -- e foi exatamente isso que
# aconteceu: a mutacao M3 obrigatoria da SPEC (tirar `.eq("company_id", …)` da leitura
# da sombra) passou CEGA. Um gate que nao consegue ficar vermelho com o defeito que
# ele existe para pegar e um carimbo (CLAUDE.md §9.3).
#
# Este bloco roda o MOTOR (`abrir_sombra`, `sombra_da_conversa`, `registrar_evento`,
# `digerir`, `montar_resumo_claims_shadow`) sobre um banco falso com DUAS corretoras,
# e a mutacao e aplicada em memoria, no cliente. CLAUDE.md §9.4: o que se afirma e o
# comportamento do MOTOR sobre o dado REAL, nunca o do regex sobre a declaracao.


def _rodar(valor):
    """Executa a corotina e devolve o resultado. Sincrono passa direto."""
    import asyncio

    if hasattr(valor, "__await__"):
        return asyncio.run(_espera(valor))
    return valor


def _duas_sombras_num_banco(classe=None, vivo=True):
    """Abre a sombra da corretora A (conversa A) e a da B (conversa B), pelo MOTOR.

    Devolve `(banco, cli, run_a, run_b, erro)`. ⚠️ `abrir_sombra` e o unico caminho
    usado: montar as linhas a mao provaria a fixture, nao o codigo.
    """
    banco = (classe or BancoFalso)({}, vivo=vivo)
    cli = ClienteFalso(banco)
    try:
        run_a = _rodar(abrir_sombra(cli, company_id=EMPRESA_A,
                                    conversation_id=CONVERSA_A))
        run_b = _rodar(abrir_sombra(cli, company_id=EMPRESA_B,
                                    conversation_id=CONVERSA_B))
    except Exception as e:  # noqa: BLE001
        return banco, cli, None, None, "abrir_sombra levantou %s: %s" % (
            type(e).__name__, e)
    return banco, cli, run_a, run_b, ""


def _releitura(banco, classe=None):
    """Um cliente NOVO sobre as MESMAS linhas de `work_runs`.

    🔴 Por que releitura e nao o mesmo cliente: `claims_shadow._MEMORIA` lembra, POR
    CLIENTE, qual conversa ja tem sombra, e responde sem consultar. Perguntar ao
    cliente que acabou de abrir a sombra mediria o dicionario, nao o SELECT -- e o
    filtro de §7 mora no SELECT.
    """
    novo = (classe or BancoFalso)({"work_runs": banco.linhas_de("work_runs")},
                                  vivo=True)
    return novo, ClienteFalso(novo)


def bloco_12_dois_tenants_pelo_motor():
    _p("\n[12] DOIS TENANTS PELO MOTOR -- a consulta EXECUTA, e a mutacao M3 fica vermelha")
    if abrir_sombra is None or sombra_da_conversa is None or registrar_evento is None:
        pular("[12] DOIS TENANTS PELO MOTOR",
              _FALTA_SOMBRA or "abrir_sombra/sombra_da_conversa nao importam")
        return

    banco, _cli, run_a, run_b, erro = _duas_sombras_num_banco()
    if erro:
        pular("[12] DOIS TENANTS PELO MOTOR", erro)
        return
    certo(bool(run_a) and bool(run_b) and run_a != run_b,
          "A④ duas corretoras, duas sombras DISTINTAS",
          "run_a=%r run_b=%r" % (run_a, run_b))
    linhas = banco.linhas_de("work_runs")
    donos = {str(l.get("id")): str(l.get("company_id")) for l in linhas}
    certo(donos.get(str(run_a)) == EMPRESA_A and donos.get(str(run_b)) == EMPRESA_B,
          "A④ cada sombra nasce com o company_id da SUA corretora (§7)",
          "donos=%r" % (sorted(donos.values()),))

    # ---- a LEITURA cruzada: o motor, num cliente que nunca viu estas conversas ----
    banco2, cli2 = _releitura(banco)
    achou_propria = _rodar(sombra_da_conversa(cli2, EMPRESA_A, CONVERSA_A))
    # 🔴 CONTROLE PRIMEIRO (CLAUDE.md §9.2): a consulta EXECUTA e ACHA. Sem esta
    # linha, o `None` da consulta cruzada abaixo poderia ser "o SELECT nao funciona".
    certo(str(achou_propria or "") == str(run_a),
          "CONTROLE: sombra_da_conversa(A, conversa da A) ACHA a sombra",
          "veio %r -- se a consulta propria nao acha, o None da cruzada nao prova nada"
          % (achou_propria,))
    cruzada = _rodar(sombra_da_conversa(cli2, EMPRESA_B, CONVERSA_A))
    certo(cruzada is None,
          "§7 sombra_da_conversa(B, conversa da A) devolve None",
          "veio %r -- o backend roda com service role: sem o filtro de company_id no "
          "CODIGO, a corretora B le a sombra da A" % (cruzada,))

    # ---- a ESCRITA cruzada: sem sombra DA CORRETORA, nao grava --------------------
    antes = len(banco2.de("work_events"))
    _rodar(registrar_evento(cli2, company_id=EMPRESA_B, conversation_id=CONVERSA_A,
                            event_type="claims.humano_assumiu",
                            payload={"origem": "dashboard"}))
    certo(len(banco2.de("work_events")) == antes,
          "B④ registrar_evento(B, conversa da A) NAO grava nada",
          "gravou %d evento(s) -- um gesto da B pendurado na sombra da A e trabalho de "
          "uma corretora contado na outra" % (len(banco2.de("work_events")) - antes))
    _rodar(registrar_evento(cli2, company_id=EMPRESA_A, conversation_id=CONVERSA_A,
                            event_type="claims.humano_assumiu",
                            payload={"origem": "dashboard"}))
    # 🔴 CONTROLE do escritor: ele CONSEGUE gravar quando a corretora e a dona.
    certo(len(banco2.de("work_events")) == antes + 1,
          "CONTROLE: registrar_evento(A, conversa da A) GRAVA",
          "um escritor que nunca grava faria o gate acima passar por vacuidade")
    _rodar(registrar_evento(cli2, company_id=EMPRESA_B, conversation_id=CONVERSA_B,
                            event_type="claims.humano_assumiu",
                            payload={"origem": "dashboard"}))

    # ---- o DIGEST nao agrega entre corretoras -------------------------------------
    if digerir is None:
        pular("[12] C⑥ digerir por corretora", _FALTA_DIGEST)
    else:
        r_b = digerir(cli2, EMPRESA_B)
        r_a = digerir(cli2, EMPRESA_A)
        certo(int(r_b.get("sombras") or 0) == 1 and int(r_a.get("sombras") or 0) == 1,
              "C⑥ digerir(B) conta 1 sombra e digerir(A) conta 1 -- nunca as duas",
              "B=%r A=%r" % (r_b.get("sombras"), r_a.get("sombras")))
        certo(int((r_b.get("contadores") or {}).get("total") or 0) == 1,
              "C⑥ o denominador do digest da B e o das sombras DA B",
              "total=%r -- um denominador que soma as duas corretoras torna toda "
              "fracao do relatorio errada" % ((r_b.get("contadores") or {}).get("total"),))

    # ---- o RESUMO ADMIN separa por corretora --------------------------------------
    if montar_resumo_claims_shadow is None:
        pular("[12] D① resumo por corretora", _FALTA_ADMIN)
    else:
        resumo = None
        try:
            resumo = montar_resumo_claims_shadow(banco2)
        except Exception as e:  # noqa: BLE001
            certo(False, "D① montar_resumo_claims_shadow com duas corretoras NAO levanta",
                  "%s: %s" % (type(e).__name__, e))
        if resumo is not None:
            por_empresa = {str(c.get("company_id")): c
                           for c in (resumo.get("corretoras") or [])}
            certo(set(por_empresa) == {EMPRESA_A, EMPRESA_B},
                  "D① o resumo lista as DUAS corretoras, cada uma na sua linha",
                  "veio %s" % sorted(por_empresa))
            certo(all(int(c.get("sombras_abertas") or 0) == 1
                      for c in por_empresa.values()),
                  "D① cada corretora conta 1 sombra -- nenhuma carrega a da outra",
                  "%r" % {k: v.get("sombras_abertas") for k, v in por_empresa.items()})

    # ---- 🔴 A MUTACAO M3: o guarda CONSEGUE ficar vermelho? -----------------------
    banco_m, _cli_m, run_ma, _run_mb, erro = _duas_sombras_num_banco(BancoFalsoSemTenant)
    if erro:
        pular("[12] MUTACAO M3", erro)
        return
    _banco_m2, cli_m2 = _releitura(banco_m, BancoFalsoSemTenant)
    cruzada_m = _rodar(sombra_da_conversa(cli_m2, EMPRESA_B, CONVERSA_A))
    certo(str(cruzada_m or "") == str(run_ma),
          "MUTACAO M3: SEM o filtro de company_id, a B ENXERGA a sombra da A",
          "veio %r -- se a mutacao tambem devolve None, o gate acima nao esta medindo "
          "o filtro, e a M3 obrigatoria da SPEC continua passando cega (foi o achado "
          "B7 do painel de 03/09/2026)" % (cruzada_m,))


# ===========================================================================
# [13] O DIGEST PONTA A PONTA -- gate E⑧ (CONSERTO B7 e C3)
# ===========================================================================
#
# 🔴 📊 O painel mediu: `digerir()` nao tinha UM teste. O fio inteiro -- sombra →
# gesto → trajetoria ordenada → variante → sinal -- so existia no relatorio do
# builder. E o `truncado`, que e a metade que faltava do conserto da paginacao, era
# calculado e jogado fora antes do sinal: o numero saia menor que a verdade com cara
# de verdade (achado B5).
_PASSOS_DA_SOMBRA = (
    ("claims.humano_assumiu", {"origem": "dashboard"}),
    ("claims.documento_recebido", {"tipo_documento": "cnh"}),
    ("claims.espera_aberta", {"kind": "esperando_seguradora"}),
    ("claims.encerrado", {"desfecho": "pago"}),
)


def _tres_sombras_com_gestos(**kw):
    """Tres conversas da MESMA corretora, cada uma com a MESMA sequencia de gestos.

    ⚠️ A sequencia e igual de proposito: tres trajetorias iguais sao UMA variante com
    N=3, que e exatamente o limiar da §C①. Duas seriam anedota e nao sairiam.
    """
    banco = BancoFalso({}, vivo=True, **kw)
    cli = ClienteFalso(banco)
    for i in range(3):
        conversa = "e2e-conversa-%d" % i
        _rodar(abrir_sombra(cli, company_id=EMPRESA_A, conversation_id=conversa))
        for evento, payload in _PASSOS_DA_SOMBRA:
            _rodar(registrar_evento(cli, company_id=EMPRESA_A,
                                    conversation_id=conversa,
                                    event_type=evento, payload=payload))
    return banco, cli


def _trajetorias_sem_ordem(eventos):
    """🔴 A MUTACAO M2 no lugar em que a ORDEM NASCE: `trajetorias_de` sem ordenar.

    ⚠️ Ela NAO reimplementa o motor para depois testar a copia (§9.4). Ela existe
    para uma pergunta so: *se a ordem nao fosse aplicada, o resultado seria outro?*
    Se for o mesmo, a ordenacao nao estava fazendo nada e o gate C② e vacuo.
    """
    por_run = {}
    ficha = {}
    for ev in (eventos or ()):
        if not isinstance(ev, dict):
            continue
        run = str(ev.get("work_run_id") or "")
        if not run or not str(ev.get("event_type") or "").startswith("claims."):
            continue
        ficha.setdefault(run, str(ev.get("company_id") or ""))
        por_run.setdefault(run, []).append(str(ev.get("event_type")))
    return [{"work_run_id": run, "company_id": ficha.get(run) or "",
             "ramo": "desconhecido", "seguradora_slug": "desconhecida",
             "eventos": tipos, "desfechos": [], "esperas": []}
            for run, tipos in sorted(por_run.items())]


def _banco_de_duas_ordens():
    """Duas sombras com os MESMOS tres passos e ordens cronologicas INVERTIDAS.

    🔴 O `created_at` inverte; a ordem de CHEGADA das linhas nao. E de proposito: e
    assim que se separa "o motor ordenou pelo relogio" de "o motor devolveu na ordem
    em que o PostgREST entregou". Sem a inversao, a mutacao daria o mesmo resultado e
    a linha de controle nao teria direito a conclusao (CLAUDE.md §9.2).
    """
    ida = ["claims.sombra_aberta", "claims.humano_assumiu", "claims.documento_recebido"]
    linhas = []
    for run, relogios in (("run-ida", ["10:00", "11:00", "12:00"]),
                          ("run-volta", ["10:00", "12:00", "11:00"])):
        for i, (tipo, hora) in enumerate(zip(ida, relogios)):
            linhas.append({"id": "%s-%d" % (run, i), "work_run_id": run,
                           "company_id": EMPRESA_A, "event_type": tipo,
                           "created_at": "2026-09-01T%s:00+00:00" % hora,
                           "payload_redacted": {}})
    banco = BancoFalso({
        "work_runs": [{"id": "run-ida", "company_id": EMPRESA_A,
                       "workflow_key": WORKFLOW, "status": "running",
                       "created_at": "2026-09-01T10:00:00+00:00"},
                      {"id": "run-volta", "company_id": EMPRESA_A,
                       "workflow_key": WORKFLOW, "status": "running",
                       "created_at": "2026-09-01T10:00:00+00:00"}],
        "work_events": linhas,
    }, vivo=True)
    return banco, ClienteFalso(banco)


_RE_COM_DENOMINADOR = re.compile(r"\d+/\d+")


def bloco_13_digest_ponta_a_ponta():
    _p("\n[13] O DIGEST PONTA A PONTA -- 3 sombras -> 1 variante -> 2 sinais (gate E⑧)")
    if digerir is None or abrir_sombra is None:
        pular("[13] DIGEST PONTA A PONTA", _FALTA_DIGEST or _FALTA_SOMBRA)
        return

    banco, cli = _tres_sombras_com_gestos()
    certo(len(banco.linhas_de("work_runs")) == 3
          and len(banco.linhas_de("work_events")) == 3 * (1 + len(_PASSOS_DA_SOMBRA)),
          "a fixture montou 3 sombras e %d eventos PELO MOTOR"
          % (3 * (1 + len(_PASSOS_DA_SOMBRA))),
          "runs=%d eventos=%d" % (len(banco.linhas_de("work_runs")),
                                  len(banco.linhas_de("work_events"))))

    r = None
    try:
        r = digerir(cli, EMPRESA_A)
    except Exception as e:  # noqa: BLE001
        certo(False, "E⑧ digerir() nao levanta", "%s: %s" % (type(e).__name__, e))
    if r is None:
        return
    certo(int(r.get("sombras") or 0) == 3 and int(r.get("variantes") or 0) == 1,
          "E⑧ 3 sombras iguais -> 1 variante (limiar N>=3 da §C①)",
          "sombras=%r variantes=%r" % (r.get("sombras"), r.get("variantes")))

    sinais = banco.linhas_de("intelligence_signals")
    por_tipo = {}
    for s in sinais:
        por_tipo.setdefault(str(s.get("signal_type")), []).append(s)
    certo(set(por_tipo) == {"process_variant", "claims_shadow_resumo"}
          and len(sinais) == 2,
          "E⑧ o digest escreve UM `process_variant` e UM `claims_shadow_resumo`",
          "gravou %d sinal(is): %s" % (len(sinais), sorted(por_tipo)))

    variante = (por_tipo.get("process_variant") or [{}])[0]
    assinatura = (variante.get("metadata") or {}).get("assinatura") or []
    esperados = ["claims.sombra_aberta"] + [e for e, _p_ in _PASSOS_DA_SOMBRA]
    certo(list(assinatura) == esperados,
          "E⑧ o sinal carrega a assinatura dos %d passos, NA ORDEM" % len(esperados),
          "veio %r" % (assinatura,))
    certo(int((variante.get("metadata") or {}).get("n") or 0) == 3
          and int((variante.get("metadata") or {}).get("denominador") or 0) == 3,
          "§12.1 a variante sai com `n` E com `denominador`",
          "metadata=%r" % ({k: v for k, v in (variante.get("metadata") or {}).items()
                            if k in ("n", "denominador")},))

    resumo = (por_tipo.get("claims_shadow_resumo") or [{}])[0]
    texto = str(resumo.get("summary_redacted") or "")
    certo(bool(_RE_COM_DENOMINADOR.search(texto)),
          "§12.1 os contadores saem COM denominador no summary (`n/total`)",
          "summary=%r -- numero sem denominador nao e citavel (ref. ⑤ Sprout.ai)"
          % texto[:120])
    # 🔴 CONTROLE do casador de denominador: ele CONSEGUE reprovar.
    certo(not _RE_COM_DENOMINADOR.search("37 sinistros com documento faltante"),
          "CONTROLE: o casador de denominador RECUSA o numero sozinho")

    # ---- DEDUPE: a segunda rodada nao duplica ------------------------------------
    r2 = digerir(cli, EMPRESA_A)
    certo(len(banco.linhas_de("intelligence_signals")) == 2,
          "C③ a MESMA rodada de novo nao cria linha nova (dedupe vivo)",
          "agora sao %d linhas; a segunda rodada devolveu %r sinal(is) -- um dedupe "
          "morto duplica o briefing a cada dia"
          % (len(banco.linhas_de("intelligence_signals")), r2.get("sinais")))

    # ---- 🔴 CONSERTO C3: a leitura truncada CHEGA ao sinal ------------------------
    banco_t, cli_t = _tres_sombras_com_gestos(falhar_no_select={"work_events": 1})
    r_t = digerir(cli_t, EMPRESA_A)
    certo(bool(r_t.get("truncado")),
          "a fixture de truncamento FUNCIONA: digerir() devolve `truncado` nao-vazio",
          "veio %r -- sem isto o gate abaixo mediria uma leitura completa"
          % (r_t.get("truncado"),))
    sinais_t = [s for s in banco_t.linhas_de("intelligence_signals")
                if str(s.get("signal_type")) == "claims_shadow_resumo"]
    meta_t = (sinais_t[0].get("metadata") if sinais_t else {}) or {}
    certo_bloco(bool(meta_t.get("truncado")),
                "C3 o sinal carrega `truncado` no metadata quando a leitura foi parcial",
                "CONSERTO C3",
                "metadata=%r -- `truncado` era calculado e jogado fora antes do sinal: "
                "um numero MENOR que a verdade, com cara de verdade (achado B5 do "
                "painel)" % (sorted(meta_t),))
    texto_t = str((sinais_t[0].get("summary_redacted") if sinais_t else "") or "")
    certo_bloco("truncad" in texto_t.lower(),
                "C3 o summary do sinal DIZ que a leitura foi truncada",
                "CONSERTO C3",
                "summary=%r -- quem le o sinal precisa poder dizer 'este numero esta "
                "incompleto' (mesma regra do `nao_instrumentado` da SPEC-088 §4)"
                % texto_t[:140])

    # ---- 🔴 A MUTACAO M2: sem ordenacao, duas trajetorias viram UMA ---------------
    mod = sys.modules.get("app.services.claims_shadow_digest")
    if mod is None or trajetorias_de is None:
        pular("[13] MUTACAO M2", "o modulo do digest nao esta em sys.modules")
        return
    _b1, cli1 = _banco_de_duas_ordens()
    r_ok = digerir(cli1, EMPRESA_A, limiar=1)
    _b2, cli2 = _banco_de_duas_ordens()
    original = mod.trajetorias_de
    try:
        mod.trajetorias_de = _trajetorias_sem_ordem
        r_mut = digerir(cli2, EMPRESA_A, limiar=1)
    finally:
        mod.trajetorias_de = original
    certo(int(r_ok.get("variantes") or 0) == 2,
          "C② X e a PERMUTACAO de X sao DUAS variantes (a ordem faz o processo)",
          "vieram %r -- 'o humano assumiu e entao o documento chegou' e o contrario "
          "sao dois processos" % (r_ok.get("variantes"),))
    certo(int(r_mut.get("variantes") or 0) == 1,
          "MUTACAO M2: SEM a ordenacao de `trajetorias_de`, as duas colapsam em UMA",
          "vieram %r -- se a mutacao der 2 tambem, a ordenacao nao esta fazendo nada "
          "e o gate C② e vacuo" % (r_mut.get("variantes"),))


# ===========================================================================
# [14] O QUE A SOMBRA NAO PODE FAZER -- os seis limites que o painel achou abertos
# ===========================================================================
#
# 🔴 Os seis sub-blocos abaixo nasceram do painel de 03/09/2026 (4 lentes + red team).
# Cada um mata um defeito de PRODUTO -- nenhum deles trava nada, e todos chegam ao
# relatorio que a corretora le (CLAUDE.md §9.5: o passo que responde errado e
# silencioso).


def _sinal_de_fixture(sid, tipo, source_type, empresa=EMPRESA_A):
    return {"id": sid, "company_id": empresa, "signal_type": tipo,
            "domain": "sinistro", "subject_type": "claims_shadow", "subject_id": None,
            "source_type": source_type, "source_ref": "fixture",
            "rule_key": "fixture.%s" % tipo, "rule_version": "1",
            "summary_redacted": "3 sinistro(s) seguiram 5 passo(s)",
            "status": "validated", "severity": "info", "confidence": 0.6,
            "priority_score": 50.0, "trust_tier": 3, "occurrence_count": 1,
            "dedupe_key": "fixture:%s" % sid, "valid_until": "2099-01-01T00:00:00+00:00",
            "metadata": {}}


def _evidencia_de_fixture(sid, empresa=EMPRESA_A):
    return {"id": "ev-%s" % sid, "company_id": empresa, "signal_id": sid,
            "evidence_type": "analysis", "source_system": "claims_shadow",
            "source_ref": "work_runs:claims.shadow", "trust_tier": 3,
            "summary_redacted": "3 sinistro(s) seguiram 5 passo(s)",
            "value_snapshot": {"n": 3}, "observed_at": "2026-09-02T00:00:00+00:00"}


def _findings_de(sinais):
    """Roda o `FindingEngine` REAL sobre os sinais dados. Devolve (criados, banco)."""
    banco = BancoFalso({
        "intelligence_signals": list(sinais),
        "intelligence_signal_evidence": [_evidencia_de_fixture(s["id"]) for s in sinais],
    }, vivo=True)
    return FindingEngine(ClienteFalso(banco)).consolidar(EMPRESA_A), banco


def bloco_14a_a_sombra_nao_chega_ao_briefing():
    _p("\n[14a] A SOMBRA NAO CHEGA AO BRIEFING -- C0 prometeu SILENCIO")
    if FindingEngine is None:
        pular("[14a] FindingEngine", _FALTA_FINDING)
        return
    # 🔴 CONTROLE PRIMEIRO: o motor CONSEGUE produzir Finding com este banco falso.
    # 📊 Sem ele, o zero do claims_shadow poderia ser "o FindingEngine nunca produz
    # nada aqui" -- e o gate estaria medindo a fixture (CLAUDE.md §9.2).
    controle, _b = _findings_de([_sinal_de_fixture("sig-controle", "connector_failure",
                                                   "connector")])
    certo(len(controle) >= 1,
          "CONTROLE: o FindingEngine PRODUZ Finding a partir de um sinal comum",
          "produziu %d -- um motor que nao produz nada faria o gate abaixo passar por "
          "vacuidade" % len(controle))

    da_sombra, banco = _findings_de([_sinal_de_fixture("sig-sombra", "process_variant",
                                                       "claims_shadow")])
    certo_bloco(not da_sombra and not banco.de("intelligence_findings"),
                "B1 um sinal `source_type='claims_shadow'` NAO vira Finding",
                "CONSERTO C7",
                "produziu %d finding(s) e gravou %d linha(s). 📊 O painel mediu 2.097 "
                "execucoes de `detect_signals` em 30 dias e 131 briefings enviados: a "
                "sombra CHEGARIA ao relatorio da corretora, quando a 093-B e C0 e "
                "prometeu observar em silencio."
                % (len(da_sombra), len(banco.de("intelligence_findings"))))


# --- (b) o DETECTOR: as 17 frases que o red team fixou ----------------------
#
# 💭 As frases sao INVENTADAS (⛔ nenhuma veio do acervo de um segurado), mas o
# PROBLEMA e medido: 📊 03/09/2026, red team: 12 de 14 frases NAO-sinistro abriam
# sombra, 16,4% das conversas do acervo abririam, e 15% delas com palavra de VENDA.
# Um detector assim nao "erra um pouco": ele envenena o dataset que a SPEC existe
# para criar, e o faz em silencio.
FRASES_QUE_ABREM = (
    "bati o carro, e agora?",
    "roubaram meu carro",
    "capotei na estrada",
    "levaram meu carro ontem",
    "pegou fogo o motor",
    "arrombaram o carro",
    "tive um acidente hoje",
    "houve um abalroamento",
)
FRASES_QUE_NAO_ABREM = (
    "que roubo esse preco do seguro",              # reclamacao de PRECO
    "quero contratar seguro contra roubo e furto",  # VENDA
    "quanto custa a cobertura de colisao?",         # VENDA
    "meu pai teve um acidente vascular cerebral",   # saude, e nao veiculo
    "por acidente mandei a foto errada",            # `acidente` como adverbio
    "a batida do motor esta estranha",              # `batida` como barulho
    "bati na porta do carro dele pra chamar",       # `bati` sem ocorrencia
    "quero falar com o terceiro andar",             # §1.5, o caso original
    "quero fazer uma cotacao de sinistro",          # a palavra existe; o pedido e VENDA
)


def bloco_14b_o_detector_separa():
    _p("\n[14b] O DETECTOR -- 8 frases que TEM de abrir e 9 que NAO podem")
    if detectar_sinistro is None:
        pular("[14b] DETECTOR", _FALTA_SOMBRA)
        return
    erraram_abrindo = []
    erraram_calando = []
    for frase in FRASES_QUE_ABREM:
        abriu, _c, erro = _detectar(frase)
        if erro:
            pular("[14b] %r" % frase[:32], erro)
            return
        if abriu is not True:
            erraram_calando.append(frase)
    for frase in FRASES_QUE_NAO_ABREM:
        abriu, _c, erro = _detectar(frase)
        if erro:
            pular("[14b] %r" % frase[:32], erro)
            return
        if abriu is not False:
            erraram_abrindo.append(frase)
    certo_bloco(not erraram_calando,
                "B2 as %d frases de OCORRENCIA abrem sombra" % len(FRASES_QUE_ABREM),
                "CONSERTO C1",
                "ficaram caladas: %s -- um sinistro que nao vira sombra e um caso que "
                "some do dataset" % [f[:34] for f in erraram_calando])
    certo_bloco(not erraram_abrindo,
                "B2 as %d frases de VENDA/CONVERSA nao abrem sombra"
                % len(FRASES_QUE_NAO_ABREM), "CONSERTO C1",
                "abriram: %s -- 📊 red team 03/09/2026: 1 em cada 6 conversas viraria "
                "sombra, 15%% delas de venda" % [f[:34] for f in erraram_abrindo])
    # 🔴 CONTROLE: o proprio conjunto de frases distingue alguma coisa?
    respostas = [_detectar(f)[0] for f in FRASES_QUE_ABREM + FRASES_QUE_NAO_ABREM]
    certo(len(set(respostas)) > 1,
          "CONTROLE: o detector NAO devolve o mesmo para as 17 frases",
          "devolveu %r para todas" % respostas[0])


# --- (c) a VALIDACAO DE VALOR: enum ou slug, nunca frase --------------------
def _evento_gravado(banco, tipo):
    linhas = [l for l in banco.de("work_events") if l.get("event_type") == tipo]
    return linhas[0] if linhas else None


def bloco_14c_validacao_de_valor():
    _p("\n[14c] VALIDACAO DE VALOR -- o contrato 'zero texto' tambem vale no Python")
    if registrar_evento is None:
        pular("[14c] VALIDACAO DE VALOR", _FALTA_SOMBRA)
        return

    # (1) fora do enum, mas com FORMA de slug -> a chave cai, o evento fica, warning.
    banco = _banco_com_sombra()
    _registrar(banco, "claims.humano_assumiu", {"origem": "carlos-da-silva"})
    linha = _evento_gravado(banco, "claims.humano_assumiu")
    certo_bloco(linha is not None
                and "origem" not in (linha.get("payload_redacted") or {}),
                "B6 valor FORA do enum e descartado (a chave nao entra)",
                "CONSERTO C4",
                "gravou %r -- hoje o Python valida so o TAMANHO do valor; o Next ja "
                "valida o enum, e um contrato que vale num stack so nao e contrato"
                % ((linha or {}).get("payload_redacted"),))
    certo_bloco(linha is not None and str(linha.get("severity")) == "warning",
                "B6 o evento com valor descartado grava severity='warning'",
                "CONSERTO C4",
                "veio %r -- perder o detalhe em silencio esconde que houve descarte"
                % ((linha or {}).get("severity"),))

    # (2) valor com FORMA DE FRASE.
    #
    # ⚠️ 🔴 AQUI HÁ UMA DIVERGÊNCIA DE LEITURA, e ela fica ESCRITA em vez de resolvida
    # por quem escreve a prova. O pacote do conserto diz que este caso é "recusado"; o
    # código entregue descarta a CHAVE, sobe o evento para `warning` e grava a linha.
    # As duas leituras defendem o mesmo bem (nenhum texto no payload) e discordam só
    # sobre a linha existir. ⚠️ A que o código adotou tem um argumento a favor que o
    # guarda não pode ignorar: `claims.espera_aberta` ACONTECEU, e apagar o evento
    # apagaria um passo real da variante — a sombra perderia o gesto para punir o
    # escritor. Quem decide é o integrador (registrado no relatório).
    #
    # 🔴 O que este bloco afirma é o que as DUAS leituras exigem, e é o que interessa
    # ao produto: a frase não entra no payload, nem inteira nem pela metade, e a perda
    # é DECLARADA. Um gate escrito sobre a parte em disputa ficaria vermelho para
    # sempre por causa de uma decisão de projeto, não de um defeito (CLAUDE.md §9.3).
    banco = _banco_com_sombra()
    _registrar(banco, "claims.espera_aberta",
               {"kind": "esperando o laudo do Dr Souza"})
    linha = _evento_gravado(banco, "claims.espera_aberta")
    gravado = (linha or {}).get("payload_redacted") or {}
    certo("kind" not in gravado
          and "souza" not in json.dumps(gravado, ensure_ascii=False).lower(),
          "B6 valor com FORMA DE FRASE nao entra no payload (nem truncado)",
          "gravou %r -- 'esperando o laudo do Dr Souza' tem 28 chars e passaria pelo "
          "limite de 64: e texto de conversa, com NOME de pessoa, entrando pela porta "
          "do enum" % (gravado,))
    certo(linha is None or str(linha.get("severity")) == "warning",
          "B6 quando a frase e descartada, o evento DECLARA a perda (warning)",
          "veio severity=%r com payload %r -- descartar em silencio esconde que ha um "
          "escritor mandando texto onde o vocabulario pede enum"
          % ((linha or {}).get("severity"), gravado))

    # 🔴 CONTROLE: o valor CERTO continua entrando. Um validador que recusa tudo e um
    # carimbo ao contrario, e apagaria o rastro inteiro sem ninguem notar.
    banco = _banco_com_sombra()
    _registrar(banco, "claims.encerrado", {"desfecho": "pago"})
    linha = _evento_gravado(banco, "claims.encerrado")
    certo(linha is not None and (linha.get("payload_redacted") or {}) == {"desfecho": "pago"},
          "CONTROLE: o valor DO enum e gravado normalmente",
          "veio %r" % ((linha or {}).get("payload_redacted"),))

    # (3) chave intrusa -> descartada (e o evento fica).
    banco = _banco_com_sombra()
    _registrar(banco, "claims.encerrado",
               {"desfecho": "pago", "nome_do_segurado": "fulano"})
    linha = _evento_gravado(banco, "claims.encerrado")
    certo(linha is not None
          and "nome_do_segurado" not in (linha.get("payload_redacted") or {}),
          "B② chave fora do vocabulario e DESCARTADA",
          "veio %r" % ((linha or {}).get("payload_redacted"),))

    # (4) o ATOR sai do vocabulario, nunca de quem chama.
    banco = _banco_com_sombra()
    try:
        _rodar(registrar_evento(ClienteFalso(banco), company_id=EMPRESA_A,
                                conversation_id=CONVERSA_A,
                                event_type="claims.humano_assumiu",
                                payload={"origem": "dashboard"},
                                actor_type="admin"))
    except Exception as e:  # noqa: BLE001
        pular("[14c] ator do vocabulario", "registrar_evento levantou %s" % type(e).__name__)
        return
    linha = _evento_gravado(banco, "claims.humano_assumiu")
    certo_bloco(linha is not None and str(linha.get("actor_type")) == "user",
                "B6 `actor_type='admin'` num evento de ator `user` grava `user`",
                "CONSERTO C4",
                "gravou %r -- o ator e o do VOCABULARIO. Deixar quem chama escolher "
                "faz o mesmo gesto aparecer com dois atores diferentes, e o digest "
                "conta dois processos onde ha um" % ((linha or {}).get("actor_type"),))


# --- (d) `tem_numero`: seis digitos, nos DOIS stacks ------------------------
#: ⚠️ O alvo é o CORPO da função do Next, e não o arquivo inteiro: `\d{6,}` podia
#: aparecer noutro lugar e este gate ficaria verde sem provar nada sobre ela.
#: ⚠️ O fecho é `\n}` na coluna zero, e não o primeiro `}`: 📊 o corpo contém
#: `/\d{6,}/`, e um casador que parasse na primeira chave leria `return /\d{6,` —
#: perdendo justamente o pedaço que ele existe para conferir.
_RE_TS_TEM_NUMERO = re.compile(
    r"function\s+anotacaoTemNumero[^\n]*\n(?P<corpo>.{0,600}?)\n\}", re.S)
CLAIMS_SHADOW_TS = os.path.join(REPO, "lib", "atendimento", "claims-shadow.ts")
NOTA_PY = os.path.join(APP, "services", "a_nota_da_atendente.py")


def bloco_14d_tem_numero():
    _p("\n[14d] `tem_numero` -- 6+ digitos, e o MESMO criterio nos dois stacks")
    # O lado Next ja esta certo: e ele que define a verdade que o Python tem de copiar.
    if os.path.exists(CLAIMS_SHADOW_TS):
        m = _RE_TS_TEM_NUMERO.search(ler(CLAIMS_SHADOW_TS))
        corpo = m.group("corpo") if m else ""
        certo(bool(m) and r"\d{6,}" in corpo,
              "o lado Next exige 6+ digitos dentro de `anotacaoTemNumero`",
              "corpo=%r -- sem o lado certo nao ha contra o que comparar o outro"
              % corpo.strip()[:80])
        # 🔴 CONTROLE: o casador CONSEGUE reprovar o criterio antigo (UM digito).
        certo(r"\d{6,}" not in "  return /\\d/.test(String(texto ?? ''));",
              "CONTROLE: o casador RECUSA o corpo que exige um digito so")
    else:
        pular("[14d] lado Next", "lib/atendimento/claims-shadow.ts nao existe")

    if tem_numero is not None:
        certo_bloco(tem_numero("liguei 2x") is False
                    and tem_numero("protocolo 123456") is True
                    and tem_numero("12345") is False
                    and tem_numero("") is False,
                    "B4 `tem_numero` do Python: 6+ digitos (o MOTOR, nao o regex)",
                    "CONSERTO C2",
                    "'liguei 2x'->%r 'protocolo 123456'->%r '12345'->%r"
                    % (tem_numero("liguei 2x"), tem_numero("protocolo 123456"),
                        tem_numero("12345")))
    elif os.path.exists(NOTA_PY):
        # ⚠️ Enquanto a funcao nao existe, o guarda mede a FORMA no unico escritor
        # que hoje calcula o booleano -- e diz, na razao, que este e o plano B.
        fonte = ler(NOTA_PY)
        certo_bloco(r"\d{6,}" in fonte and re.search(r'search\(r"\\d"', fonte) is None,
                    "B4 o escritor da nota exige 6+ digitos",
                    "CONSERTO C2",
                    "📊 `a_nota_da_atendente.py` casa `\\d` (UM digito): 'liguei 2x' "
                    "grava `tem_numero=True` e o Next grava `False` para a MESMA nota "
                    "-- dois eventos contraditorios inventam um passo na variante "
                    "(achado B4 do red team). ⚠️ Este gate mede TEXTO porque "
                    "`claims_shadow.tem_numero` ainda nao existe: %s" % _FALTA_TEM_NUMERO)
    else:
        pular("[14d] tem_numero", _FALTA_TEM_NUMERO or "nem a funcao nem o escritor")


# --- (e) o CONTADOR de espera: por `kind`, e `None` quando nao ha escritor ---
def _trajetoria_com_espera(run, kind):
    return {"work_run_id": run, "company_id": EMPRESA_A, "ramo": "auto",
            "seguradora_slug": "porto",
            "eventos": ["claims.sombra_aberta", "claims.espera_aberta"],
            "desfechos": [],
            "esperas": [{"work_run_id": run, "kind": kind, "aberta_em": None,
                         "satisfeita_em": None, "data_contrato": None}]}


def bloco_14e_contador_de_espera():
    _p("\n[14e] O CONTADOR DE ESPERA -- por `kind`, e `None` no que ninguem instrumentou")
    if contadores_de is None:
        pular("[14e] CONTADOR", _FALTA_SOMBRA)
        return

    so_humano = [_trajetoria_com_espera("h%d" % i, "esperando_humano") for i in range(3)]
    c = contadores_de(so_humano)
    certo_bloco(c.get("espera_de_seguradora_sem_retorno") is None,
                "B3 so esperas de HUMANO -> `espera_de_seguradora_sem_retorno` e None",
                "CONSERTO C6",
                "veio %r -- o contador contava `claims.espera_aberta` de QUALQUER "
                "kind. 📊 No piloto, 100%% das esperas sao de humano: o relatorio diria "
                "'3 com espera de seguradora sem retorno' e nenhuma era da seguradora"
                % (c.get("espera_de_seguradora_sem_retorno"),))
    nao = [str(x) for x in (c.get("nao_instrumentado") or ())]
    certo_bloco("espera_seguradora" in nao and "prazos" in nao,
                "B3 o que nao tem escritor sai em `nao_instrumentado`",
                "CONSERTO C6",
                "veio %r -- zero por falta de escritor e zero medido sao coisas "
                "diferentes, e so uma delas e citavel (SPEC-088 §4)" % (nao,))

    com_seguradora = so_humano + [_trajetoria_com_espera("s1", "esperando_seguradora")]
    c2 = contadores_de(com_seguradora)
    certo_bloco(c2.get("espera_de_seguradora_sem_retorno") == 1,
                "B3 UMA espera de seguradora aberta -> conta 1 (nao 4)",
                "CONSERTO C6",
                "veio %r com %d trajetorias, 3 delas de espera HUMANA"
                % (c2.get("espera_de_seguradora_sem_retorno"), len(com_seguradora)))
    nao2 = [str(x) for x in (c2.get("nao_instrumentado") or ())]
    certo_bloco("espera_seguradora" not in nao2,
                "B3 com escritor de verdade, `espera_seguradora` SAI de nao_instrumentado",
                "CONSERTO C6",
                "veio %r -- um rotulo de 'nao medido' que nunca sai e ruido" % (nao2,))
    # 🔴 CONTROLE: o denominador continua vindo junto, sempre (§12.1).
    certo(c.get("total") == 3 and c2.get("total") == 4,
          "§12.1 os dois contadores saem com `total`",
          "%r e %r" % (c.get("total"), c2.get("total")))

    if summary_de_contadores is None:
        pular("[14e] o summary", _FALTA_DIGEST)
        return
    texto = str(summary_de_contadores(c))
    certo_bloco("com espera de seguradora sem retorno" not in texto
                or "instrumentad" in texto.lower(),
                "B3 o summary NAO imprime numero de seguradora sem escritor",
                "CONSERTO C6",
                "summary=%r -- ou o contador sai do texto, ou ele vem com a marca de "
                "nao instrumentado; o que nao pode e um numero com rotulo errado"
                % texto[:160])


# --- (f) o VOCABULARIO v2 ---------------------------------------------------
def bloco_14f_vocabulario_v2():
    _p("\n[14f] VOCABULARIO v2 -- evento sem escritor sai, e `motivo_enum` ganha enum")
    if not os.path.exists(VOCAB):
        pular("[14f] VOCABULARIO v2", "lib/atendimento/claims-shadow-vocab.json ausente")
        return
    v = json.loads(ler(VOCAB))
    eventos = v.get("eventos") or {}
    enums = v.get("enums") or {}
    certo_bloco("claims.seguradora_respondeu" not in eventos,
                "P `claims.seguradora_respondeu` saiu do vocabulario",
                "CONSERTO C5",
                "📊 ele nao tem escritor em lugar nenhum do repo. Um evento declarado "
                "e nunca gravado faz o leitor concluir 'a seguradora nunca respondeu' "
                "quando o que houve foi ninguem ter gravado (P-093B-SEGURADORA)")
    certo_bloco(bool(enums.get("motivo_enum")),
                "P `motivo_enum` tem enum declarado",
                "CONSERTO C5",
                "sem enum, o validador de valor do C4 nao tem contra o que validar e "
                "a chave cai na regra de 'slug qualquer'")
    if enums.get("motivo_enum"):
        certo("sinistro" in list(enums["motivo_enum"]),
              "o enum de `motivo_enum` cobre o que `human_handoff.py` grava hoje",
              "veio %r -- 📊 :674 grava 'sinistro' ou 'outro'" % (enums["motivo_enum"],))
    certo_bloco(int(v.get("versao") or 0) == 2,
                "P o vocabulario declara `versao: 2`",
                "CONSERTO C5",
                "veio %r -- vocabulario que muda de conteudo e nao muda de versao faz "
                "os dois stacks discordarem sem ninguem saber qual esta velho"
                % (v.get("versao"),))
    # 🔴 CONTROLE: o arquivo continua sendo o MESMO nos dois stacks.
    if os.path.exists(CLAIMS_SHADOW_TS):
        certo("claims-shadow-vocab.json" in ler(CLAIMS_SHADOW_TS)
              or "vocab" in ler(CLAIMS_SHADOW_TS),
              "CONTROLE: o lado Next continua lendo o vocabulario, e nao uma copia")


# ===========================================================================
# [15] SEM TEXTO EM TODOS OS ESCRITORES -- §2, referencia ⑦, em CADA porta
# ===========================================================================
#
# 🔴 O bloco [7] varre `claims_shadow.py`. Mas quem monta o `payload` NAO e ele: sao
# os quatro escritores do BLOCO B, e cada um deles tem, a mao, o texto do segurado
# numa variavel ao lado. 📊 O painel achou um caso vivo dessa familia (a nota gravando
# dois eventos contraditorios). Este bloco fecha a porta pela FORMA, em todos.
ESCRITORES_DA_SOMBRA = (
    os.path.join(APP, "api", "webhook.py"),
    os.path.join(APP, "services", "o_fim_do_atendimento.py"),
    os.path.join(APP, "services", "a_nota_da_atendente.py"),
    os.path.join(APP, "agents", "tools", "human_handoff.py"),
)
#: As palavras que denunciam texto de conversa. ⚠️ `motivo_enum` NAO esta aqui de
#: proposito (ele e enum); `motivo` cru esta, porque em `human_handoff` ele e a frase
#: livre que o modelo escreveu.
_PALAVRAS_DE_TEXTO = ("content", "text", "body", "texto", "nome", "reason",
                      "mensagem", "message", "caption", "transcript")
#: As UNICAS funcoes que podem receber texto e devolver algo que NAO e texto. Lista
#: curta de proposito: cada nome aqui e uma porta, e `str(` jamais entra.
_REDUTORES = ("bool(", "tem_numero(", "anotacao_tem_numero(", "tipo_de_documento(",
              "len(")
_RE_ESCRITOR = re.compile(r"\bregistrar_(?:gesto|evento)\s*\(")


def _bloco_equilibrado(texto, inicio, abre, fecha):
    """O trecho de `texto` a partir de `inicio` ate o `fecha` que equilibra `abre`."""
    profundidade = 0
    for i in range(inicio, len(texto)):
        if texto[i] == abre:
            profundidade += 1
        elif texto[i] == fecha:
            profundidade -= 1
            if profundidade == 0:
                return texto[inicio:i + 1]
    return texto[inicio:]


def _payloads_dos_escritores(fonte):
    """Os dicionarios literais passados como `payload=` a um escritor da sombra.

    Devolve `[(linha, texto_do_dict)]`. ⚠️ `payload=<variavel>` e ignorado aqui de
    proposito: quem monta a variavel e `claims_shadow.py`, e o bloco [7] ja o varre.
    """
    fora = []
    for m in _RE_ESCRITOR.finditer(fonte):
        chamada = _bloco_equilibrado(fonte, m.end() - 1, "(", ")")
        p = chamada.find("payload=")
        if p < 0:
            continue
        resto = chamada[p + len("payload="):].lstrip()
        if not resto.startswith("{"):
            continue
        inicio_dict = chamada.index("{", p)
        fora.append((fonte[:m.start()].count("\n") + 1,
                    _bloco_equilibrado(chamada, inicio_dict, "{", "}")))
    return fora


def _pares_do_dict(texto):
    """`[(chave, valor)]` do dicionario literal, sem topo aninhado."""
    corpo = texto.strip()[1:-1]
    pares, atual, prof, dentro = [], "", 0, None
    for ch in corpo:
        if dentro:
            atual += ch
            if ch == dentro:
                dentro = None
            continue
        if ch in "\"'":
            dentro = ch
        elif ch in "([{":
            prof += 1
        elif ch in ")]}":
            prof -= 1
        if ch == "," and prof == 0:
            pares.append(atual)
            atual = ""
            continue
        atual += ch
    if atual.strip():
        pares.append(atual)
    fora = []
    for bruto in pares:
        prof, dentro, corte = 0, None, -1
        for i, ch in enumerate(bruto):
            if dentro:
                if ch == dentro:
                    dentro = None
                continue
            if ch in "\"'":
                dentro = ch
            elif ch in "([{":
                prof += 1
            elif ch in ")]}":
                prof -= 1
            elif ch == ":" and prof == 0:
                corte = i
                break
        if corte >= 0:
            fora.append((bruto[:corte].strip(), bruto[corte + 1:].strip()))
    return fora


def _texto_no_payload(fonte):
    """As ofensas de FORMA: palavra de texto na CHAVE, ou no VALOR sem redutor."""
    fora = []
    for linha, dicionario in _payloads_dos_escritores(fonte):
        for chave, valor in _pares_do_dict(dicionario):
            nu = chave.strip().strip("\"'")
            if any(p == nu or p in nu.split("_") for p in _PALAVRAS_DE_TEXTO):
                fora.append("linha %d: chave %r" % (linha, nu[:40]))
                continue
            v = " ".join(valor.split())
            if not any(p in v for p in _PALAVRAS_DE_TEXTO):
                continue
            if any(v.startswith(r) for r in _REDUTORES):
                continue
            fora.append("linha %d: valor de %r -> %r" % (linha, nu[:24], v[:60]))
    return fora


def bloco_15_sem_texto_nos_escritores():
    _p("\n[15] SEM TEXTO NOS ESCRITORES -- os quatro pontos de chamada do BLOCO B")
    for caminho in ESCRITORES_DA_SOMBRA:
        nome = os.path.basename(caminho)
        if not os.path.exists(caminho):
            pular("[15] %s" % nome, "arquivo nao existe")
            continue
        fonte = ler(caminho)
        payloads = _payloads_dos_escritores(fonte)
        if not payloads:
            pular("[15] %s" % nome,
                  "nenhum `registrar_gesto/registrar_evento(… payload={…})` -- o BLOCO "
                  "B ainda nao chegou neste arquivo")
            continue
        ofensas = _texto_no_payload(fonte)
        certo(not ofensas,
              "§2 %s: nenhum payload carrega texto do segurado (%d escritor(es))"
              % (nome, len(payloads)),
              " · ".join(ofensas[:4]) + "  -- o payload guarda enum, contagem, tipo e "
              "timestamp; texto do segurado mora no Espelho")

    # 🔴 OS CONTROLES, sobre codigo SINTETICO (§9.3: exigir o defeito de volta no
    # arquivo real seria guardar verdade vencida).
    ruim_chave = ('await registrar_gesto(\n'
                  '    db, company_id=x, event_type="claims.nota_registrada",\n'
                  '    payload={"origem": "dashboard", "texto": nota},\n'
                  ')\n')
    ruim_valor = ('await registrar_evento(\n'
                  '    db, event_type="claims.nota_registrada",\n'
                  '    payload={"tem_numero": campos.get("texto")},\n'
                  ')\n')
    bom_redutor = ('await registrar_gesto(\n'
                   '    db, event_type="claims.nota_registrada",\n'
                   '    payload={"origem": "whatsapp",\n'
                   '             "tem_numero": bool(re.search(r"\\d{6,}", texto))},\n'
                   ')\n')
    bom_enum = ('await registrar_gesto(\n'
                '    db, event_type="claims.documento_recebido",\n'
                '    payload={"tipo_documento": tipo_de_documento(message_text)},\n'
                ')\n')
    certo(len(_texto_no_payload(ruim_chave)) == 1,
          "CONTROLE: uma CHAVE `texto` no payload e ACUSADA",
          "veio %r" % (_texto_no_payload(ruim_chave),))
    certo(len(_texto_no_payload(ruim_valor)) == 1,
          "CONTROLE: um VALOR que copia `texto` sem redutor e ACUSADO",
          "veio %r" % (_texto_no_payload(ruim_valor),))
    certo(_texto_no_payload(bom_redutor) == [],
          "CONTROLE: `bool(re.search(...))` sobre o texto PASSA (o que entra e o bool)",
          "veio %r -- um gate que reprova o redutor obriga a escrever pior"
          % (_texto_no_payload(bom_redutor),))
    certo(_texto_no_payload(bom_enum) == [],
          "CONTROLE: `tipo_de_documento(message_text)` PASSA (o que entra e o enum)",
          "veio %r" % (_texto_no_payload(bom_enum),))
    certo(len(_payloads_dos_escritores(ruim_chave)) == 1
          and _payloads_dos_escritores('registrar_gesto(db, payload=entrada)') == [],
          "CONTROLE: o extrator acha o dicionario literal e ignora `payload=variavel`")


# ---------------------------------------------------------------------------
# ===========================================================================
# [16] O GUARDA DEVOLVE O AMBIENTE -- e isso tambem e medido, nao prometido
# ===========================================================================
#
# 🔴 Um conserto sem guarda e uma esperanca. Este bloco roda DEPOIS da restauracao,
# no `finally` da `main()`, e afirma que nada do que este arquivo instalou continua
# de pe. ⚠️ Ele NAO cobra as bibliotecas de terceiro que foram importadas DE VERDADE
# (pydantic, langchain, …): essas nao sao falsificacao nossa, e desimporta-las
# quebraria quem vier depois -- o que se desfaz e o que se fingiu.
def bloco_16_o_guarda_devolve_o_ambiente():
    _p("\n[16] O GUARDA DEVOLVE O AMBIENTE -- sys.modules como ele o encontrou")
    sobraram = sorted(n for n in sys.modules
                      if (n == "app" or n.startswith("app."))
                      and n not in _MODULOS_NO_INICIO)
    certo(not sobraram,
          "nenhum modulo `app.*` deste guarda sobrou em sys.modules",
          "sobraram %d: %s -- o pytest roda os arquivos no MESMO processo, e um `app` "
          "importavel muda o que OUTROS testes medem (foi assim que um guarda da "
          "SPEC-086 passou sozinho e falhou em bateria)"
          % (len(sobraram), sobraram[:6]))
    certo(not _SHIMS,
          "nenhum shim de biblioteca de terceiro sobrou instalado",
          "sobraram %s -- um shim esquecido faz o proximo teste rodar contra um objeto "
          "permissivo achando que e a biblioteca" % (_SHIMS,))
    # 🔴 CONTROLE: a verificacao CONSEGUE acusar. Um nome sintetico e plantado,
    # medido e removido -- se ela nao o achar, ela nao acharia nada.
    plantado = "app.modulo_que_nunca_existiu_093b"
    sys.modules[plantado] = types.ModuleType(plantado)
    try:
        achou = [n for n in sys.modules
                 if (n == "app" or n.startswith("app.")) and n not in _MODULOS_NO_INICIO]
    finally:
        sys.modules.pop(plantado, None)
    certo(achou == [plantado],
          "CONTROLE: a verificacao ACHA um `app.*` plantado de proposito",
          "veio %r" % (achou,))


def _rodar_os_blocos():
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
    bloco_11_resumo_admin()
    bloco_12_dois_tenants_pelo_motor()
    bloco_13_digest_ponta_a_ponta()
    bloco_14a_a_sombra_nao_chega_ao_briefing()
    bloco_14b_o_detector_separa()
    bloco_14c_validacao_de_valor()
    bloco_14d_tem_numero()
    bloco_14e_contador_de_espera()
    bloco_14f_vocabulario_v2()
    bloco_15_sem_texto_nos_escritores()


def main() -> int:
    _p("=" * 78)
    _p("  O SINISTRO DEIXA RASTRO -- SPEC-093-B  (BLOCO E + GATE ZERO do 0-bis)")
    _p("=" * 78)
    try:
        _rodar_os_blocos()
    finally:
        # 🔴 O guarda DEVOLVE o `sys.modules` como o encontrou. Sem isto ele deixa
        # `app`, as seis cascas e os shims de terceiro instalados para todo teste que
        # rodar DEPOIS no mesmo processo do pytest — e um guarda da SPEC-086 passava
        # sozinho e falhava em bateria por causa disso (lente 3 do painel, 03/09/2026).
        _restaurar_sys_modules()
        bloco_16_o_guarda_devolve_o_ambiente()

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
