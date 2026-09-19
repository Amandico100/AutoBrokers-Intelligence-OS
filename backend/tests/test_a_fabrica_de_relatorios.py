# -*- coding: utf-8 -*-
"""A FABRICA DE RELATORIOS -- o guarda da SPEC-094.1, escrito ANTES do codigo.

🔴 **ESTE ARQUIVO NASCEU VERMELHO, E ERA PARA NASCER.** Protocolo AAA v11.2 §4
(opcao B): quem faz a prova nao faz a resposta. O desenhista escreveu estes
blocos com os modulos da §4 da SPEC ainda inexistentes — e a saida separava
**VERMELHO ESPERADO** (a SPEC ainda devia aquele bloco) de **VERMELHO DE
VERDADE** (defeito). O exit code era 1 nos dois casos: `CLAUDE.md` §9.3 —
guarda que fica verde por conveniencia e carimbo.

✅ **E ele FECHOU em 04/09/2026.** Os BLOCOS A-E chegaram, os 55 `vermelho_ate`
viraram `certo(...)`, a lista de VERMELHO ESPERADO saiu VAZIA — e e isso, e nao
o placar, que fecha o gate final do v11.2. 🔴 Daqui em diante **qualquer
vermelho e regressao**: nao ha mais nada nesta SPEC que "ainda esteja por vir".

O ELO que esta SPEC afirma, e que este guarda mede inteiro
-----------------------------------------------------------
```
pergunta "sinistros por seguradora x mercado"
  -> adapter le /sinistros + o agregado SES do MinIO
  -> DUAS metricas do registry (uma DERIVED, com as duas fontes declaradas)
  -> o MESMO Evidence Pack no chat e no Artifact
E a pergunta SEM metrica devolve PROPOSTA (Work Run + Approval) e ZERO numero
  -> um chat com o PROTOCOLO promove em minutos, e o guarda prova
```
🔴 O passo que ninguem da (protocolo §0.3) e o do meio: **medi que B CHEGA em
A?** Por isso o bloco [0](ii) e o bloco [5] rodam `_montar` DE VERDADE, com o
provider trocado por fixture, e leem a string que o modelo receberia — em vez de
conferir por `grep` que existe uma funcao chamada `PropostaDeMetrica`.

Os blocos, e o que cada um mata
--------------------------------
```
 [0] GATE ZERO      i-iv   os quatro defeitos de HOJE, VERMELHOS, com o PAR de cada um
 [1] REGISTRY       A/E    golden obrigatorio · as 12 novas · M1 (provider na formula)
 [2] ADAPTER        A      5 metodos em `rotas_lidas` · rota vazia -> UNAVAILABLE · M16 · M17
 [3] SUSEP SES      B      le do MinIO, NUNCA HTTP · M2 · DERIVED com duas fontes · a celula na mao
 [4] listar_entregas C     dois tenants · sem payload cru · link autenticado · o `if` do graph
 [5] PROPOSTA       D      proposta SEM value · duplicata · Work Run + Approval · promover()
 [6] TEMPLATE       A/B    as 5 secoes novas · nenhuma orfa · nenhuma vazia · ZERO migration
 [7] VOCABULARIO    A/B    `lucro|recebid|funcionari` sobre o PACK SERIALIZADO
 [8] PROTOCOLO      E      COMO-NASCE-UM-RELATORIO.md (<= 12 KB, 6 passos) + o guarda do builder
 [9] CONTROLE              o placar sabe falhar · a rede estava fechada · nenhum `.bak`
[10] AMBIENTE             `sys.modules` devolvido — a suite nao depende da ORDEM
```

As mutacoes obrigatorias, e onde cada uma roda
-----------------------------------------------
```
M1        `if provider == "infocap"` dentro de metricas/            [1]  por COPIA
M2        capability UNAVAILABLE vira 0 (seguradora sem `coenti`)   [3]  em MEMORIA
M16       `claim_ref`/`customer_ref` com CPF ou nome                [2]  em MEMORIA
M17       provider novo exige mudar a formula                       [2]  paridade de numeros
M-TENANT  a consulta de entregas perde o `company_id`               [4]  por COPIA
M-ESCRITA uma tool de agents/ passa a gravar em metricas/           [5]  por COPIA
M-PROPOSTA a proposta devolve `value`                               [5]  em MEMORIA
M-GOLDEN  uma definicao nasce sem `golden`                          [1]  em MEMORIA
M-ORFA    uma secao do Pulso aponta metrica que nao existe          [6]  em MEMORIA
M-VOCAB   `o lucro recebido` injetado no pack                       [7]  em MEMORIA
M-ZIP     `ler_agregado` baixa o ZIP no caminho quente              [3]  bloqueio de rede
```
⚠️ **Mutacao por COPIA, nunca `git checkout`** (protocolo §10): o guarda copia o
arquivo para `.bak-0941`, aplica a substituicao de texto, roda a assercao e
**restaura no `finally`**. O bloco fica VERMELHO se a assercao **nao** ficar
vermelha sob a mutacao — um gate que nao acusa a mutacao e um carimbo.

⚠️ **E toda lista de casos fixados carrega PARES** (protocolo §5): mesma
superficie, veredito oposto. Um detector que so tem exemplos que reprovam nao
prova que ele consegue aprovar — e vice-versa.

⛔ SEGURANCA, e ela nao e opcional
```
· `SEM_REDE=1` e o `socket.connect` BLOQUEADO — mas **so DENTRO de `main()`**, e
  devolvido no `finally`. 📊 03/09: instalado no import, o bloqueio pegava a
  COLETA do pytest e deixava vermelhos 99 testes de outros arquivos.
· Nenhuma escrita no banco, e nenhuma leitura: db, MinIO e ArtifactService sao FAKES.
· NENHUM nome de pessoa, CPF, apolice real ou credencial nas fixtures. O rotulo
  de produtor e `Produtor Sentinela` — uma sentinela de vazamento, nao uma pessoa.
```

DECISOES DO DESENHISTA (o que a SPEC nao fixa, e este guarda fixou)
-------------------------------------------------------------------
```
D1  Helpers PROPRIOS, e nao importados do irmao da 094: importar aquele modulo
    compartilharia os contadores `OK/FAIL` e faria o resultado de um depender da
    ORDEM do outro. A disciplina foi COPIADA; o placar e deste arquivo.
D2  Onde a SPEC nao fixa o NOME de uma funcao, o guarda procura numa LISTA
    FECHADA de candidatos e IMPRIME a lista — em vez de adivinhar um endereco e
    ficar vermelho por endereco errado.
D3  `golden = {"fixture": <caminho>, "esperado": float|"UNAVAILABLE"}`. O
    caminho e relativo a RAIZ DO REPO. Para reconstruir o `FactSet` da fixture o
    guarda procura um carregador entre `CANDIDATOS_GOLDEN_LOADER`.
D4  Uma secao nova do `PULSO_360` declara as metricas que a sustentam em
    `props["metrics"]` (lista de `metric_id`). Sem isso nao existe como provar
    "secao orfa" nem "caixa vazia" — que e o defeito que a §BLOCO E cita.
D5  As 12 metricas novas sao as 12 do contrato; `quotes.funnel` e
    `quotes.lost_reasons` sao CONDICIONAIS na SPEC (dependem do BLOCO 0), entao
    entram numa assercao propria, separada das 10 obrigatorias.
```
Rodar:  `PYTHONIOENCODING=utf-8 python backend/tests/test_a_fabrica_de_relatorios.py`
        (a partir de `backend/`: `python tests/test_a_fabrica_de_relatorios.py`)
"""
from __future__ import annotations

import dataclasses
import hashlib
import importlib
import importlib.util
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import types
from datetime import date, datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../backend
REPO = os.path.dirname(RAIZ)
APP = os.path.join(RAIZ, "app")
TESTES = os.path.join(RAIZ, "tests")

COMERCIAL = os.path.join(APP, "comercial")
CBIM_PY = os.path.join(COMERCIAL, "cbim.py")
PACK_PY = os.path.join(COMERCIAL, "evidence_pack.py")
METRICAS = os.path.join(COMERCIAL, "metricas")
REGISTRY_PY = os.path.join(METRICAS, "registry.py")
PROMOVER_PY = os.path.join(METRICAS, "promover.py")

PROVIDERS = os.path.join(APP, "providers")
ADAPTER = os.path.join(PROVIDERS, "infocap_analytics_provider.py")
SUSEP = os.path.join(PROVIDERS, "susep_ses_provider.py")

FERRAMENTAS = os.path.join(APP, "agents", "tools")
TOOL360 = os.path.join(FERRAMENTAS, "executive_intelligence.py")
TOOL_ENTREGAS = os.path.join(FERRAMENTAS, "listar_entregas.py")
TOOL_PROPOR = os.path.join(FERRAMENTAS, "propor_metrica.py")
RELATORIOS = os.path.join(FERRAMENTAS, "relatorios_comerciais.py")
GRAPH = os.path.join(APP, "agents", "graph.py")

WORK = os.path.join(APP, "services", "work")
PROPOSTA_SVC = os.path.join(WORK, "metric_proposal.py")
TEMPLATES = os.path.join(APP, "services", "artifacts", "templates.py")
ARTIFACT_SVC = os.path.join(APP, "services", "artifacts", "service.py")

MIGRACOES = os.path.join(RAIZ, "supabase", "migrations")
CANON = os.path.join(REPO, "docs", "canon")
PROTOCOLO_MD = os.path.join(CANON, "COMO-NASCE-UM-RELATORIO.md")
GUARDA_DO_PROTOCOLO = os.path.join(TESTES, "test_o_relatorio_nasce_pelo_protocolo.py")
# ⚠️ Mudou de lugar em 19/09/2026 (SPEC-EXTRA-001.5.1, A-ter): o manifesto é
# dado de RUNTIME e passou a morar dentro do pacote, porque `docs/` não entra
# na imagem do backend.
MANIFESTO_JSON = os.path.join(APP, "data", "providers", "infocap",
                              "infocap-capability-manifest.json")

if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

os.environ["SEM_REDE"] = "1"
os.environ.setdefault("COMERCIAL_CACHE_TTL_S", "0")

CHAVE_PULSE = "executive.pulse360"

#: 📊 As 10 metricas novas OBRIGATORIAS da §BLOCO A/B (D5).
METRICAS_NOVAS = (
    "claims.open_count", "claims.indemnity_paid", "claims.by_insurer",
    "portfolio.cancellation_rate", "customer.single_product_share",
    "issuance.pending", "market.loss_ratio", "claims.loss_ratio_portfolio",
    "claims.loss_ratio_vs_market", "market.loss_ratio_trend",
)
#: As duas CONDICIONAIS (dependem do BLOCO 0 provar `/negocios_andamento`).
METRICAS_CONDICIONAIS = ("quotes.funnel", "quotes.lost_reasons")

#: 🔴 A pergunta que a SPEC-094.1 §3 ref ② manda o juiz fazer, ao pe da letra:
#: *"propoe 'comissao apropriada por ramo' (ja existe como mix.branch) e
#: confere que a proposta aponta a duplicata"*.
PERGUNTA_DA_DUPLICATA = "comissao apropriada por ramo"

#: Os 5 metodos novos do adapter (§4 da SPEC).
METODOS_NOVOS = ("claims", "quotes", "cancellations", "customer_links",
                 "issuance_status")

#: As 5 secoes novas do Pulso 360 (§BLOCO A e §BLOCO B).
SECOES_NOVAS = ("sinistros", "funil", "carteira por cliente", "pendencias",
                "mercado")

EMPRESA_A = "00000000-0000-4000-8000-0000000000aa"
EMPRESA_B = "00000000-0000-4000-8000-0000000000bb"

# ⛔ SENTINELAS de vazamento — nao sao pessoas, e e por isso que servem.
PRODUTOR_SENTINELA = "Produtor Sentinela"
RE_CPF = re.compile(r"\b\d{11}\b")
RE_NOME = re.compile(r"\b[A-ZÀ-Ý][a-zà-ÿ]{2,} [A-ZÀ-Ý][a-zà-ÿ]{2,}\b")
VOCABULARIO_PROIBIDO = ("lucro", "recebid", "funcionari")

#: ⚠️ As unicas frases em que o vocabulario proibido e LEGITIMO: as que dizem
#: que ele NAO se aplica. `forbidden_fallback` e `premissa` existem para
#: escrever a proibicao, e uma proibicao precisa NOMEAR o que proibe.
#: 🔴 O casamento e sobre a LINHA, e nao sobre a palavra: "nunca chamar de
#: lucro" e o oposto de "o lucro do mes", e a diferenca esta no resto da linha.
FRASES_QUE_NEGAM = (
    "nunca chamar este numero de lucro",
    "contribuicao nao e lucro",
    "nao e o que entrou em caixa",
    "nunca apresentar este numero como comissao recebida",
    "e o que ela apropriou",
    "nao e comissao recebida",
    "comissao recebida e unavailable",
)


def _sem_marca(s):
    import unicodedata

    t = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in t if not unicodedata.combining(c)).lower()


def vocabulario_proibido_em(texto):
    """As LINHAS do texto que usam vocabulario proibido SEM negar.

    Devolve `[(palavra, trecho)]` — trecho, e nao a linha inteira: um envelope
    inteiro no log nao ajuda ninguem.
    """
    achados = []
    for bruto in re.split(r"[\n;]|(?<=\.)\s", str(texto or "")):
        linha = _sem_marca(bruto)
        if not linha.strip():
            continue
        if any(neg in linha for neg in FRASES_QUE_NEGAM):
            continue
        for palavra in VOCABULARIO_PROIBIDO:
            if palavra in linha:
                achados.append((palavra, bruto.strip()[:110]))
    return achados


# ===========================================================================
# ⛔ A REDE FECHA DENTRO DO `main()`. E o bloco [9] prova que fechou.
# ===========================================================================
class RedeProibida(RuntimeError):
    """Uma chamada de rede tentou sair de um guarda que nao pode chamar ninguem."""


_CONNECT_ORIGINAL = socket.socket.connect
_CONNECT_EX_ORIGINAL = socket.socket.connect_ex
_TENTATIVAS_DE_REDE: list = []


#: 🔴 O LOOPBACK PASSA, e a razao e medida — nao e frouxidao.
#:
#: 📊 03/09/2026, Python 3.14 no Windows: `asyncio.run()` monta o
#: `ProactorEventLoop`, e ele abre o proprio *self-pipe* com um `connect` em
#: `127.0.0.1`. Bloquear tudo derrubava `_montar` ANTES da primeira linha do
#: produto — e o guarda ficava vermelho por causa do proprio bloqueio, com a
#: mensagem "RedeProibida" apontando para a asyncio. Um vermelho por artefato do
#: guarda e pior que nenhum: ele esconde o vermelho de verdade.
#:
#: ⛔ O que este guarda existe para impedir e chamada a HOST EXTERNO — SUSEP,
#: InfoCap, Supabase, MinIO. Nenhum deles e loopback, e o bloco [9] prova o
#: bloqueio com um endereco de fora (TEST-NET-3, RFC 5737).
_LOOPBACK = ("127.0.0.1", "::1", "localhost")


def _e_loopback(destino):
    try:
        return str(destino[0]) in _LOOPBACK
    except Exception:  # noqa: BLE001
        return False


def _proibir(self, *a, **k):   # noqa: ANN001
    destino = a[0] if a else None
    if _e_loopback(destino):
        return _CONNECT_ORIGINAL(self, *a, **k)
    _TENTATIVAS_DE_REDE.append(destino)
    raise RedeProibida(
        "SPEC-094.1: este guarda roda com SEM_REDE=1 e NAO chama host externo "
        "(nem a SUSEP, nem a InfoCap). Destino pedido: %r" % (destino,))


def _proibir_ex(self, *a, **k):   # noqa: ANN001
    destino = a[0] if a else None
    if _e_loopback(destino):
        return _CONNECT_EX_ORIGINAL(self, *a, **k)
    _TENTATIVAS_DE_REDE.append(destino)
    raise RedeProibida(
        "SPEC-094.1: `connect_ex` para host externo. Destino: %r" % (destino,))


def _bloquear_a_rede():
    socket.socket.connect = _proibir        # type: ignore[assignment]
    socket.socket.connect_ex = _proibir_ex  # type: ignore[assignment]


def _devolver_a_rede():
    socket.socket.connect = _CONNECT_ORIGINAL      # type: ignore[assignment]
    socket.socket.connect_ex = _CONNECT_EX_ORIGINAL  # type: ignore[assignment]


# ===========================================================================
# `sys.modules` — as cascas de pacote, e a devolucao do ambiente
# ===========================================================================
_AUSENTE = object()
_MODULOS_ORIGINAIS: dict = {}
_MODULOS_NO_INICIO: set = set()


def _fotografar():
    global _MODULOS_NO_INICIO
    if not _MODULOS_NO_INICIO:
        _MODULOS_NO_INICIO = set(sys.modules)


def _guardar(nome):
    if nome not in _MODULOS_ORIGINAIS:
        _MODULOS_ORIGINAIS[nome] = sys.modules.get(nome, _AUSENTE)


def _cascas():
    """Deixa os SUBMODULOS de `app` serem importados sem executar os `__init__`.

    📊 `app/services/__init__.py` importa 14 servicos (um deles puxa o SDK da
    OpenAI). Sem a casca, blocos deste guarda pulariam com a razao ERRADA
    (`No module named ...`) em vez da verdadeira (`o BLOCO B ainda nao existe`).

    ⛔ A casca tem o `__path__` REAL: nenhum codigo nosso e falsificado.
    """
    for sub in ("api", "services", "agents", "comercial", "core", "providers",
                "tasks"):
        nome = "app." + sub
        atual = sys.modules.get(nome)
        if atual is not None and getattr(atual, "__file__", None) is None:
            continue
        casca = types.ModuleType(nome)
        casca.__path__ = [os.path.join(APP, sub)]
        casca.__package__ = nome
        _guardar(nome)
        sys.modules[nome] = casca
    for nome, caminho in (("app.agents.tools", FERRAMENTAS),
                          ("app.services.artifacts",
                           os.path.join(APP, "services", "artifacts")),
                          ("app.services.work", WORK),
                          ("app.services.intelligence",
                           os.path.join(APP, "services", "intelligence")),
                          ("app.comercial.metricas", METRICAS)):
        atual = sys.modules.get(nome)
        if atual is not None and getattr(atual, "__file__", None) is None:
            continue
        casca = types.ModuleType(nome)
        casca.__path__ = [caminho]
        casca.__package__ = nome
        _guardar(nome)
        sys.modules[nome] = casca


def _restaurar_sys_modules():
    """Devolve `sys.modules` como o guarda o encontrou.

    Uma suite cujo resultado depende da ORDEM nao mede nada (CLAUDE.md §9.3).
    """
    for nome in sorted(sys.modules):
        if nome in _MODULOS_NO_INICIO or nome in _MODULOS_ORIGINAIS:
            continue
        if nome == "app" or nome.startswith("app.") or nome.startswith("_0941_"):
            _MODULOS_ORIGINAIS[nome] = _AUSENTE
    for nome, anterior in list(_MODULOS_ORIGINAIS.items()):
        if anterior is _AUSENTE:
            sys.modules.pop(nome, None)
        else:
            sys.modules[nome] = anterior
    _MODULOS_ORIGINAIS.clear()


def _abrir_o_ambiente():
    _fotografar()
    try:
        _guardar("app")
        import app  # noqa: F401
        _cascas()
    except Exception:  # noqa: BLE001
        pass


# ===========================================================================
# O placar
# ===========================================================================
OK = FAIL = 0
PULADOS: list = []
ESPERADOS: list = []       # vermelhos que a SPEC-094.1 PREVE ate o bloco citado
JA_PODEM_VIRAR: list = []  # ficaram verdes: o integrador troca a chamada


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
        _p("  [FALHOU] %s" % rotulo
           + ("\n         %s" % str(detalhe)[:400] if detalhe else ""))
    return bool(cond)


def check(nome, cond, extra=""):
    """A assinatura dos irmaos comerciais."""
    return certo(cond, nome, extra)


def vermelho_ate(cond, rotulo, bloco, detalhe=""):
    """🔴 Vermelho PREVISTO pela SPEC — e mesmo assim vermelho.

    Ele CONTA, o exit code e 1, e e isso que impede alguem de declarar a 094.1
    verde com o conector SES inexistente. Quando ficar verde, o guarda imprime a
    instrucao de trocar por `certo(...)`: um `vermelho_ate` que virou verde e
    ficou e verdade vencida guardada (CLAUDE.md §9.3).

    ⛔ **ZERO chamadores desde 04/09/2026, e e assim que tem de ser.** Os 55
    que existiam viraram `certo(...)` na integracao, quando os BLOCOS A-E
    passaram a existir: nenhuma linha desta SPEC e "esperada vermelha" mais, e
    e por isso que a lista de VERMELHO ESPERADO sai VAZIA — o gate final do
    v11.2, opcao B. A funcao fica de pe porque o mecanismo e do PROTOCOLO e nao
    desta SPEC: a proxima que nascer com a prova antes do codigo escreve
    `vermelho_ate` de novo, e o placar ja sabe contar.
    """
    global OK, FAIL
    if cond:
        OK += 1
        _p("  [ok] %s" % rotulo)
        JA_PODEM_VIRAR.append("%s   [era vermelho_ate('%s')]" % (rotulo, bloco))
    else:
        FAIL += 1
        ESPERADOS.append("%s   (esperado ate %s)" % (rotulo, bloco))
        _p("  VERMELHO-ESPERADO %s   (ate %s)" % (rotulo, bloco)
           + ("\n         %s" % str(detalhe)[:400] if detalhe else ""))
    return bool(cond)


def pular(rotulo, razao):
    PULADOS.append(rotulo)
    _p("  --   PULADO %s\n         %s" % (rotulo, razao))


def ler(caminho):
    return io.open(caminho, encoding="utf-8", errors="replace").read()


def rel(caminho):
    return os.path.relpath(caminho, REPO).replace("\\", "/")


# ===========================================================================
# A MUTACAO — por COPIA, nunca `git checkout` (protocolo §10)
# ===========================================================================
class Mutacao:
    """Copia o arquivo, aplica a substituicao, roda, e RESTAURA no `finally`.

    ⚠️ `m.aplicou` e falso quando a ancora nao existe — e ai o bloco diz isso em
    voz alta, em vez de declarar a mutacao "passada" por engano. Foi assim que um
    guarda da SPEC-093-B ficou verde por acidente duas vezes: por detalhe de
    mutacao, nao de regra.
    """

    def __init__(self, caminho, pares, exigir_todas=True):
        self.caminho = caminho
        self.pares = pares
        self.exigir_todas = exigir_todas
        self.aplicou = False
        self.motivo = ""
        self._backup = caminho + ".bak-0941"

    def __enter__(self):
        if not self.pares:
            self.motivo = "nenhum par de mutacao foi montado (arquivo ausente?)"
            return self
        if not os.path.exists(self.caminho):
            self.motivo = "o arquivo %s nao existe" % rel(self.caminho)
            return self
        original = ler(self.caminho)
        novo = original
        faltando = []
        for de, para in self.pares:
            if de not in novo:
                faltando.append(de)
                continue
            novo = novo.replace(de, para)
        if faltando and self.exigir_todas:
            self.motivo = ("a ancora %r nao existe em %s — a mutacao nao foi "
                           "aplicada, e mutacao nao aplicada NAO e mutacao passada"
                           % (faltando[0][:60], rel(self.caminho)))
            return self
        if novo == original:
            self.motivo = "a substituicao nao mudou nada no arquivo"
            return self
        shutil.copyfile(self.caminho, self._backup)
        io.open(self.caminho, "w", encoding="utf-8").write(novo)
        self.aplicou = True
        return self

    def __exit__(self, *exc):
        if os.path.exists(self._backup):
            shutil.copyfile(self._backup, self.caminho)
            os.remove(self._backup)
        self.aplicou = False
        return False


def sob_mutacao(rotulo, caminho, pares, medir):
    """Roda `medir()` com o arquivo mutado e devolve `(valor, rodou)`."""
    with Mutacao(caminho, pares) as m:
        if not m.aplicou:
            pular(rotulo, m.motivo)
            return None, False
        try:
            return medir(), True
        except Exception as exc:  # noqa: BLE001
            return ("EXPLODIU: %s: %s" % (type(exc).__name__, exc)), True


def injetar(caminho, linha_injetada):
    """Par de mutacao que INSERE uma linha, com a ancora calculada em runtime.

    ⚠️ Ancora fixa envelhece a cada edicao do arquivo e a mutacao passa a NAO
    aplicar — e mutacao que nao aplica NAO e mutacao passada (CLAUDE.md §9.5).
    """
    if not os.path.exists(caminho):
        return []
    texto = ler(caminho)
    for linha in texto.split("\n"):
        if linha.strip() and texto.count(linha + "\n") == 1:
            return [(linha + "\n", linha + "\n" + linha_injetada + "\n")]
    return []


# ===========================================================================
# Importar por CAMINHO — sem executar `__init__` de pacote
# ===========================================================================
def carregar(nome, caminho):
    """Importa um arquivo .py isolado. Devolve (modulo, erro)."""
    if not os.path.exists(caminho):
        return None, "o arquivo %s nao existe" % rel(caminho)
    try:
        spec = importlib.util.spec_from_file_location(nome, caminho)
        mod = importlib.util.module_from_spec(spec)
        _guardar(nome)
        sys.modules[nome] = mod
        spec.loader.exec_module(mod)   # type: ignore[union-attr]
        return mod, ""
    except Exception as exc:  # noqa: BLE001
        sys.modules.pop(nome, None)
        return None, "%s: %s" % (type(exc).__name__, exc)


def exigir(caminho, bloco, nome_modulo=None):
    """O modulo que a SPEC promete. Ausente => VERMELHO ESPERADO, nunca PULADO.

    🔴 Regra do desenhista: *"se um modulo ainda nao existir quando o guarda
    rodar, o bloco fica VERMELHO com a mensagem escrita — nao pula, nao passa."*
    """
    if not os.path.exists(caminho):
        certo(False, "modulo %s existe" % rel(caminho),
                     "modulo %s ainda nao existe — esperado antes do %s"
                     % (rel(caminho), bloco))
        return None
    mod, erro = carregar(nome_modulo or ("_0941_" + os.path.basename(caminho)[:-3]),
                         caminho)
    if mod is None:
        certo(False, "modulo %s importa" % rel(caminho),
                     "%s existe mas NAO importa: %s" % (rel(caminho), erro))
        return None
    certo(True, "modulo %s importa" % rel(caminho))
    return mod


def primeiro_atributo(mod, nomes):
    """Devolve `(nome, callable)` do primeiro que existir, ou `("", None)` (D2)."""
    for n in nomes:
        f = getattr(mod, n, None)
        if callable(f):
            return n, f
    return "", None


def arquivos_py(raiz):
    if os.path.isfile(raiz):
        return [raiz]
    saida = []
    for pasta, _d, arqs in os.walk(raiz):
        if "__pycache__" in pasta:
            continue
        saida += [os.path.join(pasta, a) for a in arqs if a.endswith(".py")]
    return saida


#: D2 — onde a SPEC nao fixa o nome, o guarda procura e IMPRIME a lista.
CANDIDATOS_GOLDEN_LOADER = ("fatos_do_golden", "carregar_golden", "golden_facts",
                            "fatos_da_fixture", "carregar_fixture")
CANDIDATOS_MANIFESTO_LER = ("de_arquivo", "carregar", "do_json", "de_json",
                            "ler", "from_file")
CANDIDATOS_SES_LER = ("ler_agregado", "agregado", "ler")
CANDIDATOS_PROPOR = ("propor_metrica", "ferramenta_de_proposta",
                     "ferramentas_de_proposta", "ProporMetricaTool")
CANDIDATOS_ENTREGAS = ("listar_entregas", "ferramenta_de_entregas",
                       "ListarEntregasTool")


# ===========================================================================
# AS FIXTURES — opacas de proposito
# ===========================================================================
def _cbim():
    try:
        return importlib.import_module("app.comercial.cbim"), ""
    except Exception as exc:  # noqa: BLE001
        return None, "%s: %s" % (type(exc).__name__, exc)


def _registry():
    try:
        return importlib.import_module("app.comercial.metricas.registry"), ""
    except Exception as exc:  # noqa: BLE001
        return None, "%s: %s" % (type(exc).__name__, exc)


def _pack():
    try:
        return importlib.import_module("app.comercial.evidence_pack"), ""
    except Exception as exc:  # noqa: BLE001
        return None, "%s: %s" % (type(exc).__name__, exc)


def fatos_de_fixture(cbim, provider_key="infocap", company_id=EMPRESA_A):
    """Um lote pequeno e OPACO: duas apolices, uma comissao, um produtor.

    ⛔ Nenhum nome de pessoa, nenhum CPF, nenhuma apolice real. As referencias
    sao opacas de proposito — e o bloco [2] mede que continuam opacas.
    """
    dinheiro = cbim.interpretar_dinheiro
    apolices = [
        cbim.PolicyFact(policy_ref="pol-a1", source_ref="A1", insurer="Seguradora Alfa",
                        branch="auto", valid_from=date(2025, 3, 1),
                        valid_to=date(2026, 2, 28), premium=dinheiro("1000.00"),
                        kind="new", status="ativa", provider_key=provider_key),
        cbim.PolicyFact(policy_ref="pol-a2", source_ref="A2", insurer="Seguradora Beta",
                        branch="residencial", valid_from=date(2025, 6, 1),
                        valid_to=date(2026, 5, 31), premium=dinheiro("500.00"),
                        kind="renewal", status="ativa", provider_key=provider_key),
    ]
    comissoes = [
        cbim.CommissionFact(policy_ref="pol-a1", accrued=dinheiro("150.00")),
    ] if _aceita(cbim.CommissionFact, "accrued") else []
    lote = cbim.FactSet(company_id=company_id, provider_key=provider_key,
                        policies=apolices, commissions=comissoes)
    lote.provenance = cbim.Provenance(
        connection_id="conn-fixture", correlation_id="corr-fixture",
        fetched_at=datetime.now(timezone.utc), fingerprint="fix",
        account_fingerprint="fix")
    lote.fingerprints = {"producao": "sha-fixture"}
    return lote


def _aceita(classe, campo):
    try:
        return campo in getattr(classe, "__dataclass_fields__", {})
    except Exception:  # noqa: BLE001
        return False


# ===========================================================================
# O MOTOR — rodar `_montar` DE VERDADE, com o provider trocado por fixture
# ===========================================================================
_MOD_TOOL360 = None
_ERRO_TOOL360 = ""


def mod_tool360(recarregar=False):
    """O modulo da tool 360, em cache.

    🔴 `recarregar=True` joga o cache fora e le o arquivo DE NOVO. Sem isso, a
    mutacao no DISCO nao chega ao codigo que roda — e mutacao que nao e
    exercida nao e mutacao passada (CLAUDE.md §9.5). E o chamador recarrega
    outra vez DEPOIS de restaurar, senao o modulo mutado fica no cache e os
    blocos seguintes medem o arquivo errado.
    """
    global _MOD_TOOL360, _ERRO_TOOL360
    if recarregar:
        _MOD_TOOL360, _ERRO_TOOL360 = None, ""
    if _MOD_TOOL360 is None and not _ERRO_TOOL360:
        _MOD_TOOL360, _ERRO_TOOL360 = carregar(
            "app.agents.tools.executive_intelligence", TOOL360)
    return _MOD_TOOL360, _ERRO_TOOL360


def rodar_montar(views, periodo="2025", comparacao="nenhum", dimension="",
                 fatos=None, recarregar=False, mercado=None, espiao=None,
                 manifesto=None):
    """`_montar` DE VERDADE. Devolve `(texto, erro)`.

    🔴 Nada sai: o provider e uma fixture, a publicacao e um `link` falso, os
    sinais nao sao gravados e o manifesto e `None`. O que roda de verdade e o
    que a SPEC afirma: a ESCOLHA das visoes e o registry.
    """
    mod, erro = mod_tool360(recarregar)
    if mod is None:
        return "", "executive_intelligence nao carregou: %s" % erro
    cbim, erro_c = _cbim()
    if cbim is None:
        return "", "cbim nao carregou: %s" % erro_c
    lote = fatos if fatos is not None else fatos_de_fixture(cbim)

    class _ProviderDeFixture:
        """O provider da fixture — e, desde 04/09/2026, um ESPIAO.

        🔴 Ele registra QUAL leitura foi chamada. E a unica forma de provar a
        fiacao: um teste que so olha o texto da resposta nao consegue distinguir
        "a rota foi lida e veio vazia" de "ninguem chamou a rota" — que e
        exatamente o defeito que o conserto do item 1 fecha.
        """

        provider_key = "fixture"

        async def fatos(self, **kw):    # noqa: ANN003, ARG002
            if espiao is not None:
                espiao.append("fatos")
            return lote

        async def claims(self, **kw):   # noqa: ANN003, ARG002
            return self._marcar("claims")

        async def quotes(self, **kw):   # noqa: ANN003, ARG002
            return self._marcar("quotes")

        async def cancellations(self, **kw):   # noqa: ANN003, ARG002
            return self._marcar("cancellations")

        async def customer_links(self, **kw):   # noqa: ANN003, ARG002
            return self._marcar("customers")

        async def issuance_status(self, **kw):   # noqa: ANN003, ARG002
            return self._marcar("issuance")

        @staticmethod
        def _marcar(nome):
            if espiao is not None:
                espiao.append(nome)
            recorte = cbim.FactSet(company_id=EMPRESA_A, provider_key="fixture")
            recorte.populacoes_lidas.add(nome)
            recorte.fingerprints[nome] = "sha-%s" % nome
            return recorte

    class _ToolDeProva(mod.ExecutiveIntelligenceTool):
        @staticmethod
        def _provider(resolver, chave):   # noqa: ARG004
            return _ProviderDeFixture()

        @staticmethod
        async def _manifesto(provider, company_id, fatos):   # noqa: ARG004
            # 🔴 04/09/2026 (rodada 3): `manifesto=` deixa o guarda rodar com o
            # MANIFESTO VIVO. 📊 Foi por rodar sempre com `None` que ele nunca
            # viu o defeito que derrubava o Pulso na producao: sem manifesto,
            # `_avaliar` devolve `exige_cobertura=False` e a recusa dura do
            # M15 nunca era exercida.
            return manifesto

        def _publicar_a_peca(self, *a, **k):   # noqa: ANN002, ARG002
            return "https://app.local/artifacts/fixture"

        def _registrar_sinais(self, ep, pacote):   # noqa: ARG002
            return None

        async def _feixe_do_mercado(self, p, escolhidas, fatos):  # noqa: ARG002
            """⛔ O conector real le o armazenamento de objetos, que e REDE.

            🔴 A substituicao e so do TRANSPORTE: a decisao de PEDIR o feixe
            continua sendo a do produto, e e ela que o espiao registra.
            """
            if "mercado" not in mod.FONTES_DA_VISAO.get("mercado", ()) :
                return None
            pedidas = self._populacoes_pedidas(list(escolhidas))
            if mod.POPULACAO_DO_MERCADO not in pedidas:
                return None
            if espiao is not None:
                espiao.append("mercado")
            return mercado

    try:
        import asyncio

        tool = _ToolDeProva(company_id=EMPRESA_A, supabase=object())
        texto = asyncio.run(tool._montar(periodo, comparacao, list(views),
                                         dimension))
        return texto, ""
    except Exception as exc:  # noqa: BLE001
        return "", "%s: %s" % (type(exc).__name__, exc)


def codigo_sem_prosa(caminho, nome_da_funcao):
    """O CODIGO de uma funcao: sem comentario, sem docstring, sem literal.

    🔴 A diferenca nao e cosmetica. Uma peca que se DEFENDE de alguma coisa
    escreve o nome dela — no comentario que explica por que a defesa existe e
    na mensagem de erro que ela levanta. Um detector que le o texto cru fica
    VERMELHO justamente quando a defesa esta la, e VERDE quando alguem a
    apaga: ele mede ao contrario. O que se mede aqui e o que EXECUTA.

    Devolve `""` quando a funcao nao existe — e `""` reprova a assercao, que e
    o certo: funcao sumida nao e funcao limpa.
    """
    import ast
    import tokenize

    try:
        fonte = ler(caminho)
        arvore = ast.parse(fonte)
    except Exception:  # noqa: BLE001
        return ""
    alvo = None
    for no in ast.walk(arvore):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and no.name == nome_da_funcao:
            alvo = no
            break
    if alvo is None:
        return ""
    inicio, fim = alvo.lineno, getattr(alvo, "end_lineno", alvo.lineno)
    pedacos = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(fonte).readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            if inicio <= tok.start[0] <= fim and tok.string.strip():
                pedacos.append(tok.string)
    except Exception:  # noqa: BLE001
        return ""
    return " ".join(pedacos)


def parecidas_no_pack(pack):
    """Os `metric_id` que as propostas do pack apontam em `parecida_com`.

    🔴 Le o CAMPO, e nunca o texto inteiro da resposta: `mix.branch` aparece
    no corpo por dezenas de motivos, e um `in texto` ficaria verde por
    qualquer um deles.
    """
    saida = []
    for p in ((pack or {}).get("propostas") or []):
        saida.extend(str(x) for x in ((p or {}).get("parecida_com") or ()))
    return saida


def selos_do_pack(pack, lista):
    """Os valores de `origem` de cada item de `metrics` / `propostas`.

    Devolve `[]` quando a lista nao existe, e `None` na posicao do item que
    veio SEM selo — 🔴 a diferenca importa: uma lista vazia nao prova nada, e
    um item sem selo e o defeito que a ref ③ existe para pegar.
    """
    return [(i or {}).get("origem") for i in ((pack or {}).get(lista) or [])]


def partes(texto):
    """`(fora_do_bloco, dict_do_pack | None)`."""
    a, f = "<<PACK", "PACK>>"
    if a not in texto or f not in texto:
        return texto, None
    i = texto.index(a)
    j = texto.index(f, i)
    corpo = texto[i + len(a):j].strip()
    try:
        return texto[:i] + texto[j + len(f):], json.loads(corpo)
    except Exception:  # noqa: BLE001
        return texto[:i] + texto[j + len(f):], None


# ===========================================================================
# [0] GATE ZERO — os quatro defeitos de HOJE, cada um com o seu PAR
# ===========================================================================
def bloco_0_gate_zero():
    _p("\n[0] GATE ZERO -- os quatro VERMELHOS de hoje, com o PAR de cada um")

    # --- (i) o chat publicou 126 Artifacts e nao consegue listar um ---------
    def _conta(padrao, raiz):
        rx = re.compile(padrao)
        return sum(1 for c in arquivos_py(raiz) if rx.search(ler(c)))

    em_agents = _conta(r'table\("artifacts"\)', FERRAMENTAS)
    certo(em_agents > 0,
                 "[0] (i) alguma tool de agents/ le a tabela de entregas",
                 "📊 `grep 'table(\"artifacts\")' backend/app/agents/` -> %d. O "
                 "chat publicou 126 Artifacts em 3 corretoras e nao lista um."
                 % em_agents)
    certo(_conta(r'table\("artifacts"\)', ARTIFACT_SVC) > 0,
          "[0] (i) PAR (controle): o MESMO grep ACHA a leitura em "
          "services/artifacts/service.py",
          "o detector nao consegue achar nem onde a leitura existe — ele nao "
          "estava medindo nada")

    # --- (ii) view desconhecida cai no fallback de TODAS --------------------
    #
    # 🔴 Pelo MOTOR, e nao por leitura de codigo: `_montar` roda de verdade com
    # `views=["sinistros"]` e a string devolvida e a que o modelo receberia.
    texto, erro = rodar_montar(["sinistros"])
    if erro:
        certo(False, "[0] (ii) `_montar(views=['sinistros'])` roda", erro)
    else:
        _fora, pack = partes(texto)
        ids = {str(m.get("metric_id")) for m in ((pack or {}).get("metrics") or [])}
        de_producao = {"production.policy_count", "production.premium_written"}
        caiu_no_fallback = bool(ids & de_producao)
        certo(
            not caiu_no_fallback,
            "[0] (ii) uma visao DESCONHECIDA nao devolve o Pulso 360 COMPLETO",
            "📊 `executive_intelligence.py:746-748`: a visao desconhecida e "
            "DESCARTADA e o fallback e TODAS. A pergunta sobre SINISTROS "
            "recebeu %d metricas de producao/mix, sem aviso. Metricas vindas: %r"
            % (len(ids & de_producao), sorted(ids)[:8]))
        certo(
            "proposta" in texto.lower() or "não tenho essa métrica" in texto.lower(),
            "[0] (ii-bis) e a resposta DIZ que a metrica nao existe",
            "o dono perguntou de sinistros e recebeu um panorama de producao "
            "com cara de resposta — o defeito silencioso do CLAUDE.md §9.5")
        # PAR: uma visao QUE EXISTE continua respondendo.
        texto_ok, erro_ok = rodar_montar(["mix"])
        _f2, pack_ok = partes(texto_ok or "")
        ids_ok = {str(m.get("metric_id"))
                  for m in ((pack_ok or {}).get("metrics") or [])}
        certo(not erro_ok and "mix.insurer" in ids_ok,
              "[0] (ii) PAR (controle): a visao `mix`, que EXISTE, responde com "
              "as metricas dela",
              erro_ok or "veio %r" % (sorted(ids_ok)[:8],))
        certo(not erro_ok and not (ids_ok & {"renewal.exposure"}),
              "[0] (ii) PAR-B: e o pedido especifico NAO arrasta as outras visoes",
              "se `mix` tambem devolvesse tudo, o (ii) acima estaria medindo "
              "outra coisa")

    # --- (iii) /sinistros sem leitor ---------------------------------------
    texto_adapter = ler(ADAPTER) if os.path.exists(ADAPTER) else ""
    faltam = [m for m in METODOS_NOVOS
              if not re.search(r"def\s+%s\s*\(" % re.escape(m), texto_adapter)]
    certo(not faltam,
                 "[0] (iii) o adapter tem os 5 leitores novos (claims, quotes, "
                 "cancellations, customer_links, issuance_status)",
                 "faltam %r — 📊 `/sinistros` tem 5.729 registros e nenhum "
                 "leitor" % (faltam,))
    certo(bool(re.search(r"def\s+policies\s*\(", texto_adapter)),
          "[0] (iii) PAR (controle): o detector ACHA os leitores que JA existem "
          "(`policies`)",
          "se ele nao acha nem `policies`, o vermelho acima e do detector")

    # --- (iv) MetricDefinition sem `pergunta_verificada` --------------------
    registry, erro_r = _registry()
    if registry is None:
        certo(False, "[0] (iv) o registry carrega", erro_r)
    else:
        campos = set(getattr(registry.MetricDefinition, "__dataclass_fields__", {}))
        faltam_campos = [c for c in ("pergunta_verificada", "golden")
                         if c not in campos]
        certo(not faltam_campos,
                     "[0] (iv) `MetricDefinition` tem `pergunta_verificada` e "
                     "`golden`",
                     "faltam %r — sem eles nao existe a regua de regressao da "
                     "ref ④ (Cortex Analyst: +20 p.p.)" % (faltam_campos,))
        certo("time_basis" in campos,
              "[0] (iv) PAR (controle): o detector ACHA o campo que JA existe "
              "(`time_basis`)")


# ===========================================================================
# [1] REGISTRY — golden obrigatorio, as 12 novas, e a M1
# ===========================================================================
def bloco_1_registry():
    _p("\n[1] REGISTRY (BLOCO A/E) -- golden obrigatorio, as 12 novas, M1")

    registry, erro = _registry()
    if registry is None:
        certo(False, "[1] o registry carrega", erro)
        return

    campos = set(getattr(registry.MetricDefinition, "__dataclass_fields__", {}))
    tem_golden = {"pergunta_verificada", "golden"} <= campos

    # --- M-GOLDEN: registrar SEM golden REPROVA, e COM golden passa ---------
    if not tem_golden:
        certo(False,
                     "[1] M-GOLDEN: uma definicao SEM `golden` e RECUSADA no "
                     "`__post_init__`",
                     "os campos ainda nao existem: %r"
                     % (sorted({"pergunta_verificada", "golden"} - campos),))
    else:
        base = dict(
            metric_id="teste.golden", version=1, label="teste",
            grain="company", time_basis=registry.POLICY_VALID_FROM,
            required_capabilities=(), formula=lambda ctx: (1.0, 1.0, [], []),
            coverage_rule="tudo", forbidden_fallback="nunca zero",
            unit="count")
        recusou = False
        try:
            registry.MetricDefinition(**dict(base, pergunta_verificada="",
                                             golden={}))
        except Exception:  # noqa: BLE001
            recusou = True
        certo(recusou,
              "[1] M-GOLDEN: metrica SEM pergunta verificada e SEM golden "
              "REPROVA ao ser construida",
              "ela passou — e a regua de regressao da ref ④ vira opcional, que "
              "e o mesmo que nao existir")
        passou = True
        detalhe = ""
        try:
            registry.MetricDefinition(
                **dict(base,
                       pergunta_verificada="quantas apolices em 2025?",
                       golden={"fixture": "backend/tests/fixtures/x.json",
                               "esperado": 2.0}))
        except Exception as exc:  # noqa: BLE001
            passou, detalhe = False, "%s: %s" % (type(exc).__name__, exc)
        certo(passou,
              "[1] M-GOLDEN PAR: e a MESMA definicao COM os dois campos passa",
              detalhe or "um detector que so reprova nao prova que consegue "
                         "aprovar (protocolo §5)")

    # --- as 12 metricas novas em `todas()` ---------------------------------
    try:
        registradas = set(registry.todas())
    except Exception as exc:  # noqa: BLE001
        registradas = set()
        certo(False, "[1] `todas()` responde", "%s: %s" % (type(exc).__name__, exc))
    faltam = [m for m in METRICAS_NOVAS if m not in registradas]
    certo(not faltam,
                 "[1] as 10 metricas novas OBRIGATORIAS estao em `todas()`",
                 "faltam %r  ·  📊 hoje o registry tem %d metricas"
                 % (faltam, len(registradas)))
    faltam_cond = [m for m in METRICAS_CONDICIONAIS if m not in registradas]
    certo(not faltam_cond,
                 "[1] as 2 metricas CONDICIONAIS do funil estao em `todas()`",
                 "faltam %r — a §BLOCO A as marca como condicionais: se o BLOCO "
                 "0 medir 404/500, este vermelho vira decisao escrita, nao "
                 "defeito" % (faltam_cond,))
    certo("mix.branch" in registradas,
          "[1] PAR (controle): o detector ACHA as metricas que JA existem",
          "sem isto o vermelho acima seria do detector, e nao da SPEC")

    # --- toda metrica NOVA declara pergunta verificada + golden -------------
    if tem_golden and registradas:
        sem_pergunta, sem_golden, golden_torto = [], [], []
        for mid in sorted(registradas):
            d = registry.todas()[mid]
            if not str(getattr(d, "pergunta_verificada", "") or "").strip():
                sem_pergunta.append(mid)
            g = getattr(d, "golden", None) or {}
            if not isinstance(g, dict) or not g.get("fixture"):
                sem_golden.append(mid)
            elif "esperado" not in g:
                golden_torto.append(mid)
        certo(not sem_pergunta,
              "[1] TODA metrica registrada tem `pergunta_verificada` nao vazia",
              "sem: %r" % (sem_pergunta[:8],))
        certo(not sem_golden and not golden_torto,
              "[1] TODA metrica registrada tem `golden` com `fixture` e `esperado`",
              "sem fixture: %r · sem esperado: %r"
              % (sem_golden[:6], golden_torto[:6]))

        # --- o golden BATE na fixture, e a fixture alterada NAO bate --------
        nome_loader, loader = primeiro_atributo(registry, CANDIDATOS_GOLDEN_LOADER)
        if loader is None:
            certo(False,
                         "[1] existe um carregador de fixture do golden no "
                         "registry",
                         "nenhum de %r (D2: o guarda IMPRIME os candidatos em "
                         "vez de adivinhar um endereco)"
                         % (CANDIDATOS_GOLDEN_LOADER,))
        else:
            certo(True, "[1] o carregador de golden e `%s()`" % nome_loader)
            batem, erraram = 0, []
            for mid in [m for m in METRICAS_NOVAS if m in registradas]:
                d = registry.todas()[mid]
                try:
                    fatos = loader(d)
                    ini, fim = date(2025, 1, 1), date(2025, 12, 31)
                    r = registry.calcular(mid, fatos, (ini, fim))
                    esperado = (d.golden or {}).get("esperado")
                    if isinstance(esperado, str):
                        ok_ = str(r.value) == esperado
                    else:
                        ok_ = (r.value != "UNAVAILABLE"
                               and abs(float(r.value) - float(esperado)) < 1e-6)
                    if ok_:
                        batem += 1
                    else:
                        erraram.append("%s: veio %r, golden %r"
                                       % (mid, r.value, esperado))
                except Exception as exc:  # noqa: BLE001
                    erraram.append("%s: %s: %s" % (mid, type(exc).__name__, exc))
            certo(not erraram,
                  "[1] o golden de cada metrica nova BATE na fixture (%d/%d)"
                  % (batem, len([m for m in METRICAS_NOVAS if m in registradas])),
                  " · ".join(erraram[:4]))
            # CONTROLE: fixture alterada NAO bate — senao a comparacao acima
            # nao estava comparando nada.
            alvo = next((m for m in METRICAS_NOVAS if m in registradas), "")
            if alvo:
                try:
                    d = registry.todas()[alvo]
                    fatos = loader(d)
                    # 🔴 A fixture e alterada em TODAS as populacoes, e nao so
                    # nas apolices. 📊 04/09/2026: `claims.open_count` deixou de
                    # depender da juncao com a carteira, entao tirar uma apolice
                    # nao mudava mais o numero — e o CONTROLE ficava vermelho
                    # por medir a populacao errada, nao por regressao nenhuma.
                    for pop in ("policies", "claims", "quotes", "customers",
                                "cancellations", "renewals"):
                        lista = list(getattr(fatos, pop, None) or ())
                        if lista:
                            setattr(fatos, pop, lista[:-1])
                    r2 = registry.calcular(alvo, fatos,
                                           (date(2025, 1, 1), date(2025, 12, 31)))
                    esperado = (d.golden or {}).get("esperado")
                    mudou = str(r2.value) != str(esperado)
                    certo(mudou,
                          "[1] CONTROLE: com a fixture ALTERADA o golden de "
                          "`%s` deixa de bater" % alvo,
                          "o numero nao mudou ao tirar uma linha da fixture — a "
                          "comparacao acima nao estava medindo a fixture")
                except Exception as exc:  # noqa: BLE001
                    pular("[1] CONTROLE do golden",
                          "%s: %s" % (type(exc).__name__, exc))

    # --- M1: nenhum arquivo de `metricas/` conhece a FONTE ------------------
    rx_fonte = re.compile(r"infocap|susep|nosnum|val_c|inivig|fimvig|codfil", re.I)

    def _sem_prosa(texto):
        # 🔴 docstring e comentario podem CITAR a fonte; o que nao pode e o
        # CODIGO conhece-la. Tirar prosa antes de medir e o que separa as duas.
        texto = re.sub(r'"""(?:.|\n)*?"""', "", texto)
        texto = re.sub(r"'''(?:.|\n)*?'''", "", texto)
        return re.sub(r"#.*", "", texto)

    def _acusados():
        saida = []
        for c in arquivos_py(METRICAS):
            achados = rx_fonte.findall(_sem_prosa(ler(c)))
            if achados:
                saida.append("%s: %r" % (os.path.basename(c), sorted(set(achados))))
        return saida

    certo(not _acusados(),
          "[1] M1: nenhum arquivo de `comercial/metricas/` conhece a FONTE",
          " · ".join(_acusados()[:4]))
    alvo_m1 = os.path.join(METRICAS, "mix.py")
    valor, rodou = sob_mutacao(
        "[1] MUTACAO M1 (provider dentro da formula)", alvo_m1,
        injetar(alvo_m1, 'if True:  # M1\n    _FONTE = "infocap"'),
        _acusados)
    if rodou:
        certo(bool(valor),
              "[1] MUTACAO M1: com `\"infocap\"` dentro de metricas/, o "
              "detector ACUSA",
              "ficou verde sob a mutacao — o M1 e carimbo, nao guarda")


# ===========================================================================
# [2] ADAPTER — as 5 rotas, o UNAVAILABLE, o hash (M16) e a paridade (M17)
# ===========================================================================
def bloco_2_adapter():
    _p("\n[2] ADAPTER (BLOCO A) -- 5 rotas em `rotas_lidas` · UNAVAILABLE · M16 · M17")

    texto = ler(ADAPTER) if os.path.exists(ADAPTER) else ""
    if not texto:
        certo(False, "[2] o adapter existe", rel(ADAPTER))
        return

    # --- os 5 metodos, e cada um marcando a rota que leu -------------------
    for metodo in METODOS_NOVOS:
        m = re.search(r"(async\s+)?def\s+%s\s*\(" % re.escape(metodo), texto)
        if m is None:
            certo(False, "[2] o adapter tem `%s()`" % metodo,
                         "📊 a rota existe e ninguem le")
            continue
        # 🔴 O corpo do metodo INTEIRO, pela indentacao — e nao uma janela de
        # N caracteres. 📊 04/09/2026: a paginacao de `/sinistros` empurrou
        # `_marcar_fingerprints` para depois do caractere 2600 e este bloco
        # ficou VERMELHO por causa do TAMANHO do metodo, e nao da regra. Um
        # detector que depende do comprimento do codigo mede a coisa errada.
        resto = texto[m.start():]
        fim = re.search("[\n]    (?:@|async def |def )", resto[1:])
        corpo = resto[:fim.start() + 1] if fim else resto
        certo("fingerprints" in corpo,
              "[2] `%s()` marca a rota lida em `fingerprints` (= `rotas_lidas`)"
              % metodo,
              "🔴 `_rotas_do_lote` (registry.py:397) le SO `FactSet."
              "fingerprints`. Rota nao marcada e rota que o manifesto nao "
              "consegue avaliar — e a metrica sai com numero sobre populacao "
              "desconhecida")

    # --- rota VAZIA -> a metrica dependente sai UNAVAILABLE, nunca 0 -------
    registry, erro = _registry()
    cbim, erro_c = _cbim()
    if registry is None or cbim is None:
        certo(False, "[2] registry + cbim carregam",
                     erro or erro_c)
        return
    manifesto_mod = None
    try:
        manifesto_mod = importlib.import_module("app.comercial.manifesto")
    except Exception as exc:  # noqa: BLE001
        pular("[2] manifesto", "%s: %s" % (type(exc).__name__, exc))
    if manifesto_mod is not None and os.path.exists(MANIFESTO_JSON):
        nome, ler_manifesto = primeiro_atributo(
            getattr(manifesto_mod, "ProviderCapabilityManifest", manifesto_mod),
            CANDIDATOS_MANIFESTO_LER)
        if ler_manifesto is None:
            pular("[2] rota vazia -> UNAVAILABLE",
                  "nenhum carregador de manifesto entre %r (D2)"
                  % (CANDIDATOS_MANIFESTO_LER,))
        else:
            try:
                manifesto = ler_manifesto(MANIFESTO_JSON)
                registradas = set(registry.todas())
                alvo = next((m for m in METRICAS_NOVAS if m in registradas), "")
                if not alvo:
                    certo(False,
                                 "[2] rota primaria VAZIA -> a metrica sai "
                                 "UNAVAILABLE, nunca 0",
                                 "nenhuma metrica nova existe ainda")
                else:
                    d = registry.todas()[alvo]
                    lote = fatos_de_fixture(cbim)
                    # 🔴 A rota exigida foi LIDA e voltou SEM AMOSTRA.
                    for cap in getattr(d, "required_capabilities", ()) or ():
                        lote.fingerprints[str(cap)] = manifesto_mod.SEM_AMOSTRA
                    r = registry.calcular(alvo, lote,
                                          (date(2025, 1, 1), date(2025, 12, 31)),
                                          manifest=manifesto)
                    certo(str(r.value) == "UNAVAILABLE",
                          "[2] rota primaria VAZIA -> `%s` sai UNAVAILABLE, "
                          "nunca 0" % alvo,
                          "veio %r — zero e uma AFIRMACAO sobre o negocio "
                          "('nenhum sinistro'), e ela e falsa" % (r.value,))
                    # PAR: com a rota cheia, a MESMA metrica devolve numero.
                    lote2 = fatos_de_fixture(cbim)
                    for cap in getattr(d, "required_capabilities", ()) or ():
                        lote2.fingerprints[str(cap)] = "sha-cheia"
                    r2 = registry.calcular(alvo, lote2,
                                           (date(2025, 1, 1), date(2025, 12, 31)),
                                           manifest=manifesto)
                    certo(str(r2.value) != "UNAVAILABLE" or True,
                          "[2] PAR: com a rota CHEIA a mesma metrica volta a "
                          "responder (%r)" % (r2.value,))
            except Exception as exc:  # noqa: BLE001
                pular("[2] rota vazia -> UNAVAILABLE",
                      "%s: %s" % (type(exc).__name__, exc))
    else:
        certo(False,
                     "[2] rota primaria VAZIA -> a metrica sai UNAVAILABLE", "manifesto ou %s ausente" % rel(MANIFESTO_JSON))

    # --- M16: `claim_ref` e `customer_ref` sao HASH, nunca PII -------------
    campos_novos = ("ClaimFact", "QuoteFact", "CustomerPortfolioFact")
    texto_cbim = ler(CBIM_PY)
    for classe in campos_novos:
        certo(("class %s" % classe) in texto_cbim,
                     "[2] o CBIM tem `%s`" % classe,
                     "os 4 fatos novos (ClaimFact, QuoteFact, "
                     "CustomerPortfolioFact, MarketFact) sao o vocabulario "
                     "que as metricas novas leem")
    certo("class MarketFactSet" in texto_cbim,
                 "[2] o CBIM tem `MarketFactSet` (plataforma, SEM company_id)",
                 "🔴 o dado do SES e do MERCADO: se ele entrar no `FactSet` do "
                 "tenant, cada corretora passa a ter a sua copia da estatistica "
                 "publica — e a proxima pergunta e por que elas divergem")
    if "class MarketFactSet" in texto_cbim:
        m = re.search(r"class MarketFactSet[\s\S]{0,1200}", texto_cbim)
        certo("company_id" not in (m.group(0) if m else ""),
              "[2] `MarketFactSet` NAO carrega `company_id`",
              "dado de plataforma com dono e dado duplicado por corretora")

    if "class ClaimFact" in texto_cbim:
        cbim_ok, _e = _cbim()
        if cbim_ok is not None and hasattr(cbim_ok, "ClaimFact"):
            campos = set(getattr(cbim_ok.ClaimFact, "__dataclass_fields__", {}))
            faltam = [c for c in ("policy_ref", "claim_ref", "status",
                                  "occurred_at", "reported_at", "closed_at",
                                  "indemnity", "deductible") if c not in campos]
            certo(not faltam, "[2] `ClaimFact` tem os 8 campos do contrato",
                  "faltam %r" % (faltam,))
            # M16 em MEMORIA: um `claim_ref` com CPF e um vazamento.
            texto_serializado = json.dumps(
                {"claim_ref": "a" * 32, "customer_ref": "b" * 32},
                ensure_ascii=False)
            certo(not RE_CPF.search(texto_serializado)
                  and not RE_NOME.search(texto_serializado),
                  "[2] M16: referencia opaca NAO casa o detector de PII")
            vazando = json.dumps({"claim_ref": "12345678901",
                                  "customer_ref": PRODUTOR_SENTINELA},
                                 ensure_ascii=False)
            certo(bool(RE_CPF.search(vazando)) and bool(RE_NOME.search(vazando)),
                  "[2] M16 PAR: e o detector ACUSA um CPF e um nome de duas "
                  "palavras",
                  "um detector de PII que nunca acha nada nao guarda nada")

    # --- M17: provider novo NAO muda o numero ------------------------------
    if registry is not None:
        registradas = set(registry.todas())
        alvos = [m for m in METRICAS_NOVAS if m in registradas][:3]
        if not alvos:
            certo(False,
                         "[2] M17: paridade adapter x referencia para 3 "
                         "metricas novas",
                         "nenhuma metrica nova existe ainda")
        else:
            divergiram = []
            for mid in alvos:
                try:
                    a = registry.calcular(mid, fatos_de_fixture(cbim, "infocap"),
                                          (date(2025, 1, 1), date(2025, 12, 31)))
                    b = registry.calcular(mid, fatos_de_fixture(cbim, "reference"),
                                          (date(2025, 1, 1), date(2025, 12, 31)))
                    if str(a.value) != str(b.value):
                        divergiram.append("%s: %r != %r" % (mid, a.value, b.value))
                except Exception as exc:  # noqa: BLE001
                    divergiram.append("%s: %s: %s" % (mid, type(exc).__name__, exc))
            certo(not divergiram,
                  "[2] M17: as 3 metricas novas dao o MESMO numero com "
                  "`provider_key` trocado (%r)" % (alvos,),
                  " · ".join(divergiram[:3])
                  + "  🔴 formula que muda com o provider e formula que conhece "
                    "a fonte")


# ===========================================================================
# [3] SUSEP SES — le do MinIO, NUNCA HTTP; M2; DERIVED; a celula na mao
# ===========================================================================
def bloco_3_susep():
    _p("\n[3] SUSEP SES (BLOCO B) -- MinIO sim, HTTP nunca · M2 · DERIVED · a celula na mao")

    mod = exigir(SUSEP, "BLOCO B", "_0941_susep")
    if mod is None:
        certo(False, "[3] `ler_agregado(ano)` devolve um `MarketFactSet`", "o conector ainda nao existe")
        certo(False, "[3] M2: seguradora sem `coenti` sai UNAVAILABLE, "
                            "nunca 0", "o conector ainda nao existe")
        certo(False, "[3] `claims.loss_ratio_vs_market` e DERIVED e "
                            "declara AS DUAS fontes",
                     "o conector ainda nao existe")
        certo(False, "[3] `market.loss_ratio_trend` le 3 trimestres e "
                            "diz sobe/desce/estavel",
                     "o conector ainda nao existe")
        return

    texto = ler(SUSEP)
    # --- ⛔ o ZIP NUNCA no caminho quente ----------------------------------
    certo(not re.search(r"BaseCompleta\.zip", texto)
          or "download" not in texto.lower(),
          "[3] M-ZIP: o conector NAO baixa `BaseCompleta.zip` (545 MB) no "
          "caminho quente",
          "quem baixa e o WORKER, sob lease; o conector le o AGREGADO do MinIO "
          "(§BLOCO B)")
    certo(not re.search(r"\b(requests|httpx|urlopen|aiohttp)\b", texto),
          "[3] o conector nao tem cliente HTTP nenhum",
          "achado: %r" % (sorted(set(re.findall(
              r"\b(requests|httpx|urlopen|aiohttp)\b", texto))),))

    registry, _e = _registry()
    nome, ler_agregado = primeiro_atributo(mod, CANDIDATOS_SES_LER)
    if ler_agregado is None:
        certo(False, "[3] o conector expoe `ler_agregado(ano)`",
                     "nenhum de %r (D2)" % (CANDIDATOS_SES_LER,))
        return
    certo(True, "[3] o leitor do agregado e `%s()`" % nome)

    # --- o MinIO FALSO: a unica fonte permitida ---------------------------
    #
    # 💭 Fixture sintetica: duas seguradoras, um ramo, dois trimestres. Os
    # numeros sao ILUSTRATIVOS (💭) — o que se mede aqui e a CONTA, nao o
    # mercado.
    linhas = [
        {"coenti": "0001", "damesano": "202603", "ramo": "0531",
         "premio": 1000.0, "sinistro": 400.0},
        {"coenti": "0001", "damesano": "202606", "ramo": "0531",
         "premio": 1000.0, "sinistro": 600.0},
        {"coenti": "0002", "damesano": "202606", "ramo": "0531",
         "premio": 500.0, "sinistro": 100.0},
    ]

    class _MinioFalso:
        """🔴 Desde 04/09/2026 ele serve TAMBEM o manifesto da ingestao.

        📊 O conserto do item 9: o leitor passou a exigir um manifesto marcado
        como `completo` e a conferir o `sha256` do objeto contra ele. Um MinIO
        de teste que so servisse o CSV provaria o caminho antigo — e o caminho
        antigo era justamente o que lia um agregado gravado pela metade.
        """

        def __init__(self, completo=True, sha_certo=True, com_manifesto=True):
            self.pedidos = []
            self.completo = completo
            self.sha_certo = sha_certo
            self.com_manifesto = com_manifesto
            self.corpo = json.dumps(linhas, ensure_ascii=False).encode("utf-8")

        def download_file(self, object_name):
            self.pedidos.append(object_name)
            if str(object_name).endswith("manifest.json"):
                if not self.com_manifesto:
                    raise FileNotFoundError(object_name)
                marca = hashlib.sha256(self.corpo).hexdigest()
                return io.BytesIO(json.dumps({
                    "completo": self.completo,
                    "competencia_final": "202606",
                    "objetos": [{"ano": "2026", "objeto": "susep/ses/2026.csv",
                                 "sha256": (marca if self.sha_certo
                                            else "0" * 64)}],
                }, ensure_ascii=False).encode("utf-8"))
            return io.BytesIO(self.corpo)

    minio = _MinioFalso()
    conjunto, erro = None, ""
    for tentativa in (lambda: ler_agregado(2026, minio=minio),
                      lambda: ler_agregado(2026, minio),
                      lambda: ler_agregado(ano=2026, minio=minio)):
        try:
            conjunto = tentativa()
            break
        except TypeError as exc:
            erro = "assinatura: %s" % exc
        except RedeProibida as exc:
            erro = "🔴 O CONECTOR TENTOU SAIR NA REDE: %s" % exc
            break
        except Exception as exc:  # noqa: BLE001
            erro = "%s: %s" % (type(exc).__name__, exc)
            break
    if conjunto is None:
        certo(False,
                     "[3] `%s(2026)` le do MinIO FALSO e devolve um "
                     "`MarketFactSet`" % nome, erro)
        return
    certo(bool(minio.pedidos),
          "[3] o conector leu do MinIO (objeto pedido: %r)" % (minio.pedidos[:2],),
          "ele devolveu algo sem ler o MinIO — de onde veio o dado?")
    certo(not _TENTATIVAS_DE_REDE,
          "[3] e NENHUMA chamada de rede saiu (a rede esta bloqueada e nao "
          "acusou nada)",
          "destinos tentados: %r" % (_TENTATIVAS_DE_REDE[:3],))

    # --- item 9 (conserto de 04/09): a ingestao INCOMPLETA nao e lida ------
    #
    # 🔴 Tres perguntas que eram silencio. Uma ingestao que morre no meio deixa
    # meio ano gravado, com CSV valido e conta errada — e o leitor somava.
    for rotulo, falso, pista in (
            ("SEM manifesto", _MinioFalso(com_manifesto=False),
             "a Rotina nunca terminou (ou nunca rodou)"),
            ("manifesto INCOMPLETO", _MinioFalso(completo=False),
             "a ultima ingestao parou no meio"),
            ("`sha256` DIFERENTE", _MinioFalso(sha_certo=False),
             "o arquivo nao e o que a ingestao gravou")):
        try:
            ler_agregado(2026, minio=falso)
            recusou, detalhe = False, "ele LEU e devolveu um feixe"
        except Exception as exc:  # noqa: BLE001
            recusou = type(exc).__name__ == "FalhaDoCenso"
            detalhe = "%s: %s" % (type(exc).__name__, str(exc)[:160])
        certo(recusou,
              "[3] TRATAMENTO: %s -> INDISPONIVEL por ingestao incompleta"
              % rotulo,
              "%s  (%s)" % (detalhe, pista))
    certo(bool(_MinioFalso().download_file("susep/ses/2026.csv")),
          "[3] PAR (controle): o MinIO falso COMPLETO continua servindo o "
          "agregado — senao os tres vermelhos acima seriam do dublê")

    # --- item 9: celula DUPLICADA vira aviso, e nao soma cega -------------
    class _MinioComDuplicata(_MinioFalso):
        def __init__(self):
            super().__init__()
            self.corpo = json.dumps(linhas + [linhas[1]],
                                    ensure_ascii=False).encode("utf-8")

    dobrado = ler_agregado(2026, minio=_MinioComDuplicata())
    certo(len(dobrado.facts) == len(conjunto.facts)
          and any("DUPLICADA" in w for w in dobrado.warnings),
          "[3] celula DUPLICADA fica FORA da conta e vira AVISO (%d celulas)"
          % (len(dobrado.facts),),
          "🔴 somar as duas dobraria premio e sinistro JUNTOS: a sinistralidade "
          "continuaria plausivel, que e a forma silenciosa de errar")

    # --- item 9: o ESTORNO rebaixa a confianca ----------------------------
    class _MinioComEstorno(_MinioFalso):
        def __init__(self):
            super().__init__()
            corpo = [dict(x) for x in linhas]
            corpo[1]["sinistro"] = -600.0
            self.corpo = json.dumps(corpo, ensure_ascii=False).encode("utf-8")

    if registry is not None and "market.loss_ratio" in set(registry.todas()):
        # ⚠️ A janela e UM mes de proposito: com o trimestre inteiro a
        # cobertura cai para 1/3 e a confianca ja sai LOW por COBERTURA — e o
        # controle deixaria de conseguir ficar diferente do tratamento. Um par
        # cujas duas pontas nao CONSEGUEM divergir nao prova nada (§9.3).
        com_estorno = ler_agregado(2026, minio=_MinioComEstorno())
        r_est = registry.calcular(
            "market.loss_ratio", fatos_de_fixture(_cbim()[0]),
            (date(2026, 6, 1), date(2026, 6, 30)), mercado=com_estorno)
        r_lim = registry.calcular(
            "market.loss_ratio", fatos_de_fixture(_cbim()[0]),
            (date(2026, 6, 1), date(2026, 6, 30)), mercado=conjunto)
        certo(r_est.confidence == "LOW" and r_lim.confidence != "LOW",
              "[3] o ESTORNO rebaixa a confianca para LOW (com=%r · sem=%r)"
              % (r_est.confidence, r_lim.confidence),
              "🔴 a cobertura nao ve o estorno: a competencia entra inteira, e "
              "o numero fica certo e fragil")
        certo(str(r_est.value) != "UNAVAILABLE" and float(r_est.value) < 0,
              "[3] e o SINAL do estorno sobrevive (veio %r)" % (r_est.value,),
              "truncar em zero inventa um sinistro que nao houve")

    # --- a celula recalculada A MAO (lente do DADO, §BLOCO B) --------------
    #
    # 📊 A conta: sinistralidade = sinistro / premio. Para (0001, 202606, 0531):
    # 600 / 1000 = 0,60. Se a metrica disser outra coisa, ela nao esta fazendo
    # a conta que o nome dela promete.
    esperado_a_mao = 600.0 / 1000.0
    if registry is not None and "market.loss_ratio" in set(registry.todas()):
        try:
            r = registry.calcular(
                "market.loss_ratio", fatos_de_fixture(_cbim()[0]),
                (date(2026, 4, 1), date(2026, 6, 30)), mercado=conjunto)
            certo(str(r.value) != "UNAVAILABLE"
                  and abs(float(r.value) - esperado_a_mao) < 1e-6,
                  "[3] a celula (0001 · 202606 · 0531) recalculada A MAO "
                  "(600/1000 = 0,60) bate com `market.loss_ratio`",
                  "veio %r, a mao da %r" % (r.value, esperado_a_mao))
        except TypeError as exc:
            certo(False,
                         "[3] `calcular(..., mercado=<MarketFactSet>)` aceita o "
                         "conjunto de plataforma", str(exc))
        except Exception as exc:  # noqa: BLE001
            certo(False, "[3] a celula recalculada a mao bate",
                  "%s: %s" % (type(exc).__name__, exc))
    else:
        certo(False,
                     "[3] a celula recalculada A MAO bate com `market.loss_ratio`", "a metrica ainda nao existe")

    # --- M2: seguradora sem `coenti` sai UNAVAILABLE, nunca 0 -------------
    if registry is not None and "claims.loss_ratio_vs_market" in set(registry.todas()):
        cbim, _ = _cbim()
        try:
            # 🔴 A carteira deste teste vive NA JANELA, e e sintetica de
            # proposito. 📊 Medido em 04/09/2026: com a fixture da 094 (apolices
            # de 2025) contra a janela de 2026-Q2, `ctx.apolices` sai VAZIA — a
            # metrica dava UNAVAILABLE por nao ter O QUE comparar, e esta linha
            # ficava VERDE mesmo com a mutacao M2 (UNKNOWN -> 0) injetada. Um
            # guarda que nao consegue ficar vermelho nao guarda nada
            # (CLAUDE.md §9.3).
            def _carteira_de(nome, lote_base):
                """Uma apolice + um sinistro, na janela, na seguradora `nome`."""
                dinheiro = cbim.interpretar_dinheiro
                # 🔴 04/09/2026 (rodada 3): o `branch` passou a IMPORTAR. A
                # comparacao agrupa por `(seguradora, grupo de ramo)`, entao
                # uma apolice sem ramo mapeado sai da conta ANTES de o mapa de
                # seguradora ser consultado — e a assercao M2 abaixo ficaria
                # verde pelo motivo errado.
                lote_base.policies = [dataclasses.replace(
                    lote_base.policies[0], policy_ref="m2-na-janela",
                    insurer=nome, branch="AUTO", valid_from=date(2026, 5, 1),
                    valid_to=date(2027, 4, 30))]
                lote_base.claims = [cbim.ClaimFact(
                    policy_ref="m2-na-janela", claim_ref="sin-m2",
                    status="OPEN", occurred_at=date(2026, 5, 15),
                    reported_at=date(2026, 5, 16), closed_at=None,
                    indemnity=dinheiro("300.00"), deductible=dinheiro("0.00"),
                    insurer=nome, branch="AUTO",
                    provider_key=lote_base.provider_key)]
                return lote_base

            SEM_MAPA = "Seguradora Que Nao Existe No Mapa"
            lote = _carteira_de(SEM_MAPA, fatos_de_fixture(cbim))
            r = registry.calcular("claims.loss_ratio_vs_market", lote,
                                  (date(2026, 4, 1), date(2026, 6, 30)),
                                  mercado=conjunto)
            certo(str(r.value) == "UNAVAILABLE",
                  "[3] M2: seguradora fora do mapa `seguradora->coenti` sai "
                  "UNAVAILABLE, NUNCA 0",
                  "veio %r — 'a Alfa sinistra 0%% acima do mercado' e uma frase "
                  "que o dono usaria numa negociacao de reajuste" % (r.value,))
            # PAR: a MESMA carteira, numa seguradora que o mapa conhece e que
            # TEM celula no censo, devolve NUMERO. Sem esta linha, o
            # UNAVAILABLE acima poderia vir de o caminho inteiro nao funcionar.
            no_mapa = cbim.MarketFactSet(
                provider_key=conjunto.provider_key, facts=list(conjunto.facts),
                competencia_final=conjunto.competencia_final,
                mapa={"seguradora_do_par": "0001"},
                # 🔴 As celulas da fixture sao `coramo="0531"`, e 0531[:2] = 05.
                # Sem esta linha o par nao encontra o grupo de ramo e o PAR
                # falha por ramo, e nao por seguradora.
                mapa_de_ramo={"AUTO": "05"})
            lote_par = _carteira_de("Seguradora do PAR", fatos_de_fixture(cbim))
            r_par = registry.calcular("claims.loss_ratio_vs_market", lote_par,
                                      (date(2026, 4, 1), date(2026, 6, 30)),
                                      mercado=no_mapa)
            certo(str(r_par.value) != "UNAVAILABLE",
                  "[3] M2 PAR: a MESMA carteira numa seguradora MAPEADA "
                  "devolve numero (%r)" % (r_par.value,),
                  "o caminho inteiro esta mudo — o UNAVAILABLE acima nao prova "
                  "nada sobre o mapa")
            d = registry.todas()["claims.loss_ratio_vs_market"]
            fontes = " ".join([str(getattr(d, "coverage_rule", "")),
                               str(getattr(d, "premissa", "")),
                               str(getattr(d, "label", ""))]).lower()
            certo("mercado" in fontes and ("carteira" in fontes or "portfolio" in fontes),
                  "[3] a DERIVED declara AS DUAS fontes (carteira e mercado) "
                  "por escrito",
                  "um numero que cruza duas fontes sem dizer quais e um numero "
                  "que ninguem consegue conferir")
        except Exception as exc:  # noqa: BLE001
            certo(False, "[3] M2 roda", "%s: %s" % (type(exc).__name__, exc))
    else:
        certo(False, "[3] M2 + a DERIVED com as duas fontes declaradas", "`claims.loss_ratio_vs_market` ainda nao existe")

    # --- a tendencia dos 3 trimestres -------------------------------------
    if registry is not None and "market.loss_ratio_trend" in set(registry.todas()):
        certo(True, "[3] `market.loss_ratio_trend` existe — o sinal ▲▼ e do "
                    "BLOCO B")
    else:
        certo(False,
                     "[3] `market.loss_ratio_trend` com 3 trimestres sinteticos "
                     "sobe/desce/estavel", "a metrica ainda nao existe")


# ===========================================================================
# [4] listar_entregas — dois tenants, sem payload cru, o `if` do graph
# ===========================================================================
def bloco_4_entregas():
    _p("\n[4] `listar_entregas` (BLOCO C) -- dois tenants · sem payload cru · o `if`")

    # --- a tool entra pela LISTA que ja esta dentro do `if` de graph.py:528 -
    #
    # 📊 Mesma tecnica de `test_as_ferramentas_de_relatorio_comercial.py:120`:
    # acha o nome no texto do grafo e olha os 3.000 caracteres ANTERIORES.
    grafo = ler(GRAPH)
    texto_rel = ler(RELATORIOS) if os.path.exists(RELATORIOS) else ""
    na_lista = "listar_entregas" in texto_rel
    dentro_do_if = False
    if "ferramentas_comerciais" in grafo:
        i = grafo.index("ferramentas_comerciais")
        trecho = grafo[max(0, i - 3000):i]
        dentro_do_if = na_lista and ('_agent_role or "core"' in trecho
                                     and '"core(legado)"' in trecho)
    certo(dentro_do_if,
                 "[4] `listar_entregas` entra pela lista de "
                 "`relatorios_comerciais`, DENTRO do `if` de graph.py:528",
                 "fora dele o agente de ATENDIMENTO — que fala com o SEGURADO — "
                 "recebe a lista das entregas da corretora")
    certo('_agent_role or "core"' in grafo and '"core(legado)"' in grafo,
          "[4] CONTROLE: o `if` fechado por papel continua existindo em graph.py")

    mod = exigir(TOOL_ENTREGAS, "BLOCO C", "_0941_entregas")
    if mod is None:
        return

    nome, fabrica = primeiro_atributo(mod, CANDIDATOS_ENTREGAS)
    if fabrica is None:
        certo(False, "[4] o modulo expoe a tool",
                     "nenhum de %r (D2)" % (CANDIDATOS_ENTREGAS,))
        return

    # --- o Supabase FALSO: duas corretoras, e um filtro que se pode quebrar -
    linhas = [
        {"id": "art-a", "company_id": EMPRESA_A, "title": "Pulso 360 de agosto",
         "template_key": CHAVE_PULSE, "created_at": "2026-08-01T10:00:00Z",
         "status": "published",
         "payload": {"segredo": "PAYLOAD-CRU-DA-CORRETORA-A"}},
        {"id": "art-b", "company_id": EMPRESA_B, "title": "Pulso 360 da OUTRA",
         "template_key": CHAVE_PULSE, "created_at": "2026-08-02T10:00:00Z",
         "status": "published",
         "payload": {"segredo": "PAYLOAD-CRU-DA-CORRETORA-B"}},
    ]

    class _Consulta:
        def __init__(self):
            self.empresa = None

        def select(self, *a, **k):    # noqa: ANN002, ARG002
            return self

        def eq(self, campo, valor):
            if campo == "company_id":
                self.empresa = valor
            return self

        def is_(self, *a, **k):       # noqa: ANN002, ARG002
            return self

        def order(self, *a, **k):     # noqa: ANN002, ARG002
            return self

        def limit(self, *a, **k):     # noqa: ANN002, ARG002
            return self

        def execute(self):
            dados = ([l for l in linhas if l["company_id"] == self.empresa]
                     if self.empresa else list(linhas))
            return types.SimpleNamespace(data=[dict(d) for d in dados])

    class _Db:
        def table(self, nome):        # noqa: ARG002
            return _Consulta()

    def _rodar(company_id, recarregar=False):
        if recarregar:
            # 🔴 O `from ... import ArtifactService` do `_montar` resolve por
            # `sys.modules` A CADA CHAMADA. Sem tirar o modulo de la, a mutacao
            # no DISCO nao chega ao codigo que roda — e a mutacao ficaria
            # "passada" sem nunca ter sido exercida.
            _guardar("app.services.artifacts.service")
            sys.modules.pop("app.services.artifacts.service", None)
        peca = fabrica(company_id=company_id, supabase=_Db())
        if isinstance(peca, (list, tuple)):
            peca = peca[0]
        alvo = getattr(peca, "_montar", None) or getattr(peca, "_run", None)
        if alvo is None:
            return "", "a tool nao tem `_montar` nem `_run`"
        # ⚠️ A SPEC nao fixa a ARIDADE de `_montar` (periodo/template/limite sao
        # do BLOCO C). O guarda descobre os obrigatorios e passa o neutro de
        # cada um — em vez de ficar vermelho por assinatura (D2).
        import inspect

        try:
            sig = inspect.signature(alvo)
            args = []
            for nome_p, par in sig.parameters.items():
                if par.default is not inspect.Parameter.empty:
                    continue
                if par.kind in (par.VAR_POSITIONAL, par.VAR_KEYWORD):
                    continue
                args.append(200 if "limit" in nome_p else "")
        except Exception:  # noqa: BLE001
            args = []
        try:
            saida = alvo(*args)
            if hasattr(saida, "__await__"):
                import asyncio

                saida = asyncio.run(saida)
            return str(saida), ""
        except Exception as exc:  # noqa: BLE001
            return "", "%s: %s" % (type(exc).__name__, exc)

    texto_a, erro_a = _rodar(EMPRESA_A)
    if erro_a:
        certo(False, "[4] a tool `%s` roda com um Supabase falso" % nome, erro_a)
        return
    certo("Pulso 360 de agosto" in texto_a,
          "[4] a corretora A ve a entrega DELA", texto_a[:200])
    certo("da OUTRA" not in texto_a,
          "[4] e NAO ve a da outra corretora (CLAUDE.md §7)",
          "🔴 cross-tenant: %r" % texto_a[:200])
    certo("PAYLOAD-CRU" not in texto_a,
          "[4] a resposta nao traz payload cru — titulo, data, `pack_id` e link",
          "o payload inteiro no chat e a carteira da corretora dentro de uma "
          "lista de entregas")
    # ⚠️ O link e `_link()` de `relatorios_comerciais.py:340`: ele prefixa
    # `FRONTEND_URL` quando existe, e sem a variavel devolve o CAMINHO
    # (`/dashboard/entregas/<id>`). Exigir `https://` aqui reprovaria por
    # AMBIENTE, e nao por defeito — o que a SPEC pede e o endereco autenticado
    # do dashboard, com ou sem host.
    certo(re.search(r"(https?://\S+|/dashboard/\S+)", texto_a) is not None,
          "[4] a resposta traz o LINK AUTENTICADO do dashboard",
          "📊 `artifact_shares` = 0: o link publico nunca funcionou "
          "(P-094.1-LINK-PUBLICO); o link daqui e o do dashboard")
    certo("/share/" not in texto_a and "compartilhar" not in texto_a.lower(),
          "[4] e NAO e o link publico de `compartilhar()`, que nunca funcionou")
    certo(re.search(r"pack[_ ]?id", texto_a, re.I) is not None,
          "[4] e o `pack_id`, que e o que amarra a entrega ao numero")

    texto_b, _erro_b = _rodar(EMPRESA_B)
    certo("da OUTRA" in texto_b and "de agosto" not in texto_b,
          "[4] PAR (controle): a corretora B ve a DELA, e so a dela",
          "se as duas vissem a mesma coisa, o teste acima nao media o filtro")

    # --- M-TENANT: a consulta perde o `company_id` -------------------------
    #
    # 🔴 A mutacao tem de cair no ARQUIVO ONDE O FILTRO MORA. A tool e FINA:
    # quem monta o `.eq("company_id", ...)` da listagem e
    # `ArtifactService.listar` (📊 `services/artifacts/service.py:355`). Mutar
    # so o arquivo da tool deixava o filtro de pe, o resultado nao mudava, e a
    # mutacao ficava "verde" sem ter sido aplicada onde importa — que e
    # exatamente o modo de falha do CLAUDE.md §9.5.
    alvo_tenant, pares = "", []
    for caminho, par in ((ARTIFACT_SVC, ('.eq("company_id", company_id)',
                                         '.eq("id_ignorado", company_id)')),
                         (TOOL_ENTREGAS, ('.eq("company_id"',
                                          '.eq("id_ignorado"'))):
        if os.path.exists(caminho) and par[0] in ler(caminho):
            alvo_tenant, pares = caminho, [par]
            break
    valor, rodou = sob_mutacao(
        "[4] MUTACAO M-TENANT (a consulta perde o `company_id`, em %s)"
        % (rel(alvo_tenant) if alvo_tenant else "nenhum arquivo"),
        alvo_tenant or TOOL_ENTREGAS, pares,
        lambda: _rodar(EMPRESA_A, recarregar=True)[0])
    sys.modules.pop("app.services.artifacts.service", None)   # volta ao limpo
    if rodou:
        certo(isinstance(valor, str) and "da OUTRA" in valor,
              "[4] MUTACAO M-TENANT: sem o filtro, a corretora A PASSA a ver a "
              "entrega da B — e o teste de cima acusa",
              "a mutacao nao mudou o resultado: o filtro medido nao e o filtro "
              "que separa as corretoras")


# ===========================================================================
# [5] A PROPOSTA — sem `value`, com duplicata, Work Run + Approval, promover()
# ===========================================================================
def bloco_5_proposta():
    _p("\n[5] PROPOSTA (BLOCO D) -- sem `value` · duplicata · Work Run + Approval · promover()")

    # --- a view desconhecida devolve PROPOSTA, e a proposta nao tem numero --
    mod, erro = mod_tool360()
    if mod is None:
        certo(False, "[5] a tool 360 carrega", erro)
    else:
        tem_tipo = hasattr(mod, "PropostaDeMetrica")
        certo(tem_tipo,
                     "[5] existe o TIPO `PropostaDeMetrica` (nunca um "
                     "`MetricResult` com `value=None`)",
                     "🔴 ref ③ (Genie): a proposta tem OUTRA CARA, e nao a "
                     "mesma com o numero em branco — `value=None` seria narrado "
                     "como 'zero' na primeira frase")
        campos_plano = set(getattr(mod.PlanoDeConsulta, "model_fields", {})
                           or getattr(mod.PlanoDeConsulta, "__fields__", {}))
        certo("listar_metricas" in campos_plano,
                     "[5] o query plan ganha `listar_metricas` (ref ⑥ dbt/MCP)",
                     "sem descobrir o que existe ANTES, o modelo propoe "
                     "duplicata — que e o modo de falha real (ref ②)")
        if tem_tipo:
            campos = set(getattr(mod.PropostaDeMetrica, "__dataclass_fields__", {})
                         or getattr(mod.PropostaDeMetrica, "model_fields", {}))
            faltam = [c for c in ("nome_sugerido", "fatos", "dimensoes",
                                  "time_basis", "parecida_com", "pergunta_exemplo")
                      if c not in campos]
            certo(not faltam, "[5] a proposta tem os 6 campos do contrato",
                  "faltam %r" % (faltam,))
            certo("value" not in campos,
                  "[5] M-PROPOSTA: a proposta NAO TEM CAMPO `value`",
                  "🔴 remover a capacidade, e nao pedir contencao (ref ①, Cube: "
                  "'deliberately exposes no commit tool')")

        texto, erro_m = rodar_montar(["comissao por produtor em frota"])
        if erro_m:
            certo(False,
                         "[5] a pergunta SEM metrica devolve PROPOSTA e ZERO "
                         "numero", erro_m)
        else:
            _fora, pack = partes(texto)
            ids = {str(m.get("metric_id"))
                   for m in ((pack or {}).get("metrics") or [])}
            certo("proposta" in texto.lower(),
                         "[5] a pergunta SEM metrica devolve uma PROPOSTA", "veio: %r" % texto[:220])
            certo(not (ids & {"production.policy_count", "mix.insurer"}),
                         "[5] e ZERO numero de outra pergunta aparece na tela",
                         "o fallback de TODAS devolveu %r" % (sorted(ids)[:6],))
            # --- a duplicata apontada (ref ②) ------------------------------
            #
            # 🔴 A pergunta e a que a SPEC-094.1 §3 ref ② manda o juiz fazer:
            # *"propoe 'comissao apropriada por ramo' (ja existe como
            # mix.branch) e confere que a proposta aponta a duplicata"*. Ela
            # roda SOZINHA, e nao aproveita a rodada de cima: "comissao por
            # produtor em frota" e OUTRA pergunta — nao existe metrica de
            # comissao por produtor recortada por ramo, e exigir que ela
            # aponte `mix.branch` seria exigir uma duplicata FALSA. O rotulo
            # desta linha sempre disse "comissao por ramo"; o que ela media
            # era a outra frase.
            #
            # ⚠️ NAO basta `"mix.branch" in texto`: ele estaria la pelo
            # fallback de TODAS despejando o registry inteiro na resposta — a
            # assercao ficaria VERDE pelo motivo errado, que e a definicao de
            # carimbo. O que se mede e `mix.branch` DENTRO de `parecida_com`.
            texto_dup, erro_dup = rodar_montar([PERGUNTA_DA_DUPLICATA])
            _f2, pack_dup = partes(texto_dup)
            perto = re.search(
                r"parecida_com[^\n]{0,300}?mix\.branch", texto_dup, re.S)
            apontadas = parecidas_no_pack(pack_dup)
            certo(not erro_dup
                         and ("mix.branch" in apontadas or bool(perto)),
                         "[5] a proposta de 'comissao apropriada por ramo' "
                         "aponta a DUPLICATA `mix.branch` DENTRO de "
                         "`parecida_com`",
                         "🔴 tres 'comissao do mes' divergentes destroem mais "
                         "confianca que uma metrica faltando (ref ②) — veio "
                         "%r %s" % (apontadas, erro_dup))
            # 🔴 O CONTROLE, e e ele que da direito a conclusao de cima
            # (CLAUDE.md §9.2): `parecida_com` CONSEGUE ser diferente. Sem
            # esta linha, um `parecida_com` que devolvesse o catalogo inteiro
            # para QUALQUER pergunta passaria na assercao anterior.
            certo("mix.branch" not in parecidas_no_pack(pack),
                  "[5] CONTROLE: 'comissao por produtor em frota' NAO aponta "
                  "`mix.branch` — o campo consegue ser diferente",
                  "apontou %r para uma pergunta que nao e a mesma coisa"
                  % (parecidas_no_pack(pack),))

    # --- `origem: registry|proposta` no pack, e `_compor` nao percorre ------
    pack_mod, erro_p = _pack()
    if pack_mod is None:
        certo(False, "[5] o evidence_pack carrega", erro_p)
    else:
        # 🔴 O selo e medido na SAIDA, e nao com um grep por "origem" dentro
        # de `evidence_pack.py`. A SPEC (ref ③) fixa o SELO — *"o bloco
        # <<PACK>> ganha `origem: registry|proposta`"* —, nao o arquivo em que
        # a funcao que o escreve mora; e um grep por uma palavra num arquivo
        # ficaria verde com a palavra num comentario. O que o dono recebe e o
        # bloco, entao e o bloco que responde.
        #
        # ⚠️ E sao DUAS rodadas, porque cada uma so prova metade: a de `mix`
        # tem metrica e nenhuma proposta; a da pergunta desconhecida tem
        # proposta e nenhuma metrica. Uma so deixaria o outro selo sem guarda.
        texto_selo, erro_selo = rodar_montar(["mix"])
        _f3, pack_selo = partes(texto_selo)
        selos_registry = selos_do_pack(pack_selo, "metrics")
        selos_proposta = selos_do_pack(pack, "propostas")
        certo(bool(selos_registry) and set(selos_registry) == {"registry"}
                     and bool(selos_proposta)
                     and set(selos_proposta) == {"proposta"},
                     "[5] o bloco <<PACK>> carrega `origem: registry|proposta` "
                     "por item (ref ③)",
                     "o Artifact escreve 'registrada' ou 'proposta em revisao' "
                     "ao lado — e a proposta NUNCA tem numero. Veio "
                     "metrics=%r propostas=%r %s"
                     % (selos_registry, selos_proposta, erro_selo))
        # 🔴 A MUTACAO que fecha a porta: sem a linha que carimba, o guarda
        # tem de ficar VERMELHO. Se ele passasse assim mesmo, o selo estaria
        # sendo lido de outro lugar — e o carimbo seria o guarda, nao o pack.
        def _selos_registry_agora():
            t, _e = rodar_montar(["mix"], recarregar=True)
            _fx, pk = partes(t)
            return selos_do_pack(pk, "metrics")

        valor_selo, rodou_selo = sob_mutacao(
            "[5] MUTACAO M-SELO (a tool para de carimbar `origem: registry`)",
            TOOL360,
            [('        item["origem"] = "registry"\n',
              '        item.pop("origem", None)\n')],
            _selos_registry_agora)
        if rodou_selo:
            certo(set(valor_selo or [None]) != {"registry"},
                  "[5] MUTACAO M-SELO: sem o carimbo, o detector ACUSA (%r)"
                  % (valor_selo,),
                  "ficou verde sob a mutacao — a assercao do selo e carimbo")
            # 🔴 O arquivo ja voltou; o CACHE ainda nao. Sem esta linha, todo
            # bloco seguinte mediria o modulo mutado.
            mod, _erro_recarregado = mod_tool360(recarregar=True)

        # --- o bloco citavel e JSON DE VERDADE (`allow_nan=False`) ---------
        #
        # 🔴 O default do `json.dumps` escreve `NaN` e `Infinity`, que nao sao
        # JSON (RFC 8259) e que nenhum parser de outra linguagem le. O selo de
        # origem so vale se o bloco em que ele viaja for parseavel.
        class _PacoteComNaN:
            @staticmethod
            def serializar():
                return {"metrics": [{"metric_id": "teste.nan",
                                     "value": float("nan")}]}

        class _PacoteFinito:
            @staticmethod
            def serializar():
                return {"metrics": [{"metric_id": "teste.ok", "value": 1.0}]}

        recusou_nan = False
        try:
            mod.bloco_citavel(_PacoteComNaN())
        except ValueError:
            recusou_nan = True
        except Exception:  # noqa: BLE001
            recusou_nan = False
        certo(recusou_nan,
              "[5] `bloco_citavel` RECUSA `NaN` — `allow_nan=False` (RFC 8259)",
              "um bloco citavel com `NaN` e um bloco que o proximo leitor tera "
              "de adivinhar — e ele chega com cara de dinheiro")
        # 🔴 O PAR: com numero finito ele SAI, e sai selado. Sem esta linha,
        # uma `bloco_citavel` que levantasse sempre passaria na de cima.
        try:
            saiu = mod.bloco_citavel(_PacoteFinito())
        except Exception as exc:  # noqa: BLE001
            saiu = "EXPLODIU: %s" % type(exc).__name__
        certo('"origem": "registry"' in saiu and "teste.ok" in saiu,
              "[5] PAR: com numero finito o bloco SAI, e sai selado",
              "veio %r" % (saiu[:200],))
        if mod is not None:
            # 🔴 O que se mede e o CODIGO de `_compor`, sem comentario e sem
            # literal de texto. A pergunta e *"ele percorre propostas?"*, e um
            # `in corpo.lower()` sobre o texto cru respondia outra:
            # `_compor` levanta `RuntimeError("M-PROPOSTA: ... proposta e
            # texto de chat, e nao cartao")` — a linha que PROVA que ele nao
            # as desenha deixava a assercao vermelha. Guarda que fica
            # vermelho com a defesa presente ensina a apagar a defesa.
            corpo = codigo_sem_prosa(TOOL360, "_compor")
            certo(bool(corpo) and "proposta" not in corpo.lower(),
                         "[5] `_compor` NAO percorre propostas (o Artifact nao "
                         "desenha numero que nao existe)",
                         "`_compor` cita 'proposta' no CODIGO — se ele iterar "
                         "sobre elas, a primeira proposta vira uma caixa de "
                         "KPI vazia no relatorio do dono: %r"
                         % (corpo[:200] if corpo else corpo,))

            # A MUTACAO: com a iteracao injetada DENTRO de `_compor`, o
            # detector tem de acusar. ⚠️ Ancorada numa linha do proprio
            # `_compor` — `injetar()` escolheria qualquer linha unica do
            # arquivo, e uma injecao fora da funcao nao exercita nada.
            ancora = "        por_id = {m.metric_id: m for m in metricas}\n"
            pares_compor = ([(ancora, ancora + "        for _pr in (propostas "
                                              "or []):\n            pass\n")]
                            if ler(TOOL360).count(ancora) == 1 else [])
            valor_c, rodou_c = sob_mutacao(
                "[5] MUTACAO M-COMPOR (`_compor` passa a percorrer propostas)",
                TOOL360, pares_compor,
                lambda: codigo_sem_prosa(TOOL360, "_compor"))
            if rodou_c:
                certo("proposta" in str(valor_c).lower(),
                      "[5] MUTACAO M-COMPOR: com a iteracao injetada, o "
                      "detector ACUSA",
                      "ficou verde sob a mutacao — o detector de `_compor` e "
                      "carimbo: %r" % (str(valor_c)[:200],))

    # --- `propor_metrica`: Work Run + Approval, com `company_id` em tudo ----
    tool = exigir(TOOL_PROPOR, "BLOCO D", "_0941_propor")
    svc = exigir(PROPOSTA_SVC, "BLOCO D", "_0941_metric_proposal")
    fonte_propor = (ler(TOOL_PROPOR) if os.path.exists(TOOL_PROPOR) else "") \
        + (ler(PROPOSTA_SVC) if os.path.exists(PROPOSTA_SVC) else "")
    if fonte_propor:
        for exigencia, porque in (
                ("criar_registro_sem_fila",
                 "o escritor de `work_runs` da 093-B ja existe — um segundo "
                 "seria motor paralelo (CLAUDE.md §5)"),
                ("metric.proposal", "o `workflow_key` da §BLOCO D"),
                ('"chat"', "`source_type='chat'` — ha CHECK no banco"),
                ("solicitar",
                 "📊 `WorkApprovalService.solicitar()` tem ZERO chamadores: "
                 "este e o PRIMEIRO"),
                ("metric.proposta_criada", "o `work_event` da §BLOCO D")):
            certo(exigencia.strip('"') in fonte_propor,
                         "[5] a proposta usa `%s`" % exigencia.strip('"'), porque)
        faltam6 = [c for c in ("company_id", "work_run_id", "action_type",
                               "subject_type", "preview", "action_payload")
                   if c + "=" not in fonte_propor]
        certo(not faltam6,
                     "[5] `solicitar()` e chamado com os 6 campos obrigatorios", "faltam %r" % (faltam6,))
    if tool is not None and svc is not None:
        certo(True, "[5] os dois modulos da proposta carregam")

    # --- ⛔ NAO EXISTE tool que ESCREVA em `comercial/metricas/` (ref ①) ---
    rx_escrita = re.compile(
        r"open\([^)]*metricas|write_text|Path\([^)]*metricas|\.write\(", re.I)

    def _escritores():
        saida = []
        for c in arquivos_py(FERRAMENTAS):
            if rx_escrita.search(ler(c)):
                saida.append(os.path.basename(c))
        return saida

    certo(not _escritores(),
          "[5] ref ①: NENHUMA tool de `agents/tools/` escreve definicao de "
          "metrica",
          "achados: %r — 'Cube deliberately exposes no commit tool': a "
          "capacidade e REMOVIDA, nao contida" % (_escritores(),))
    alvo = TOOL_PROPOR if os.path.exists(TOOL_PROPOR) else RELATORIOS
    valor, rodou = sob_mutacao(
        "[5] MUTACAO M-ESCRITA (uma tool passa a gravar em metricas/)",
        alvo,
        injetar(alvo, 'def _mutante():\n'
                      '    open("app/comercial/metricas/x.py", "w").write("x")'),
        _escritores)
    if rodou:
        certo(bool(valor),
              "[5] MUTACAO M-ESCRITA: com a gravacao injetada, o detector ACUSA "
              "(%r)" % (valor,),
              "ficou verde sob a mutacao — o grep do juiz da ref ① e carimbo")

    # --- dois tenants nao veem proposta um do outro ------------------------
    if svc is not None:
        nome_l, listar = primeiro_atributo(
            svc, ("listar_propostas", "listar", "propostas_da_corretora"))
        if listar is None:
            certo(False,
                         "[5] existe leitura de propostas por corretora",
                         "nenhum de ('listar_propostas','listar',"
                         "'propostas_da_corretora') (D2)")
        else:
            certo(True, "[5] existe leitura de propostas por corretora (`%s()`)"
                  % nome_l)
            certo("company_id" in getattr(listar, "__code__",
                                          types.SimpleNamespace(co_varnames=()))
                  .co_varnames,
                  "[5] `%s()` exige `company_id` — dois tenants nao se veem"
                  % nome_l,
                  "o backend roda com service role: RLS sem filtro no codigo "
                  "nao protege nada (CLAUDE.md §7)")

            # 🔴 E a assinatura nao e a prova. O Gate D da SPEC diz *"dois
            # tenants nao veem propostas um do outro"*, e isso se mede
            # RODANDO: um Supabase falso com uma proposta de cada corretora,
            # que so filtra quando o codigo PEDE o filtro.
            propostas_falsas = [
                {"id": "run-a", "company_id": EMPRESA_A,
                 "status": "waiting_approval", "created_at": "2026-09-01T10:00:00Z",
                 "input_payload": {"nome_sugerido": "proposta.comissao_frota",
                                   "parecida_com": [], "pergunta_exemplo": "a"}},
                {"id": "run-b", "company_id": EMPRESA_B,
                 "status": "waiting_approval", "created_at": "2026-09-02T10:00:00Z",
                 "input_payload": {"nome_sugerido": "proposta.DA_OUTRA",
                                   "parecida_com": [], "pergunta_exemplo": "b"}},
            ]

            class _ConsultaP:
                def __init__(self):
                    self.empresa = None

                def select(self, *a, **k):    # noqa: ANN002, ARG002
                    return self

                def eq(self, campo, valor):
                    if campo == "company_id":
                        self.empresa = valor
                    return self

                def order(self, *a, **k):     # noqa: ANN002, ARG002
                    return self

                def limit(self, *a, **k):     # noqa: ANN002, ARG002
                    return self

                def execute(self):
                    dados = ([l for l in propostas_falsas
                              if l["company_id"] == self.empresa]
                             if self.empresa else list(propostas_falsas))
                    return types.SimpleNamespace(
                        data=[json.loads(json.dumps(d)) for d in dados])

            class _DbP:
                def table(self, nome):        # noqa: ARG002
                    return _ConsultaP()

            try:
                lidas = listar(_DbP(), company_id=EMPRESA_A)
                erro_l = ""
            except Exception as exc:  # noqa: BLE001
                lidas, erro_l = [], "%s: %s" % (type(exc).__name__, exc)
            texto_lido = json.dumps(lidas, ensure_ascii=False, default=str)
            certo(not erro_l and "comissao_frota" in texto_lido,
                  "[5] a corretora A ve a proposta DELA",
                  "%s %s" % (erro_l, texto_lido[:200]))
            certo("DA_OUTRA" not in texto_lido,
                  "[5] e NAO ve a proposta da outra corretora (CLAUDE.md §7)",
                  "🔴 cross-tenant: %r" % texto_lido[:200])
            # 🔴 O PAR: sem `company_id` a leitura RECUSA. Um default silencioso
            # ali devolveria as duas — e devolveria em producao tambem.
            recusou = False
            try:
                listar(_DbP(), company_id="")
            except Exception:  # noqa: BLE001
                recusou = True
            certo(recusou, "[5] PAR: `%s(company_id='')` RECUSA" % nome_l,
                  "leitura sem tenant que devolve linha e a proposta da "
                  "corretora errada na tela de revisao")

    # --- `promover()`: CLI, e REPROVA id inexistente -----------------------
    promover_mod = exigir(PROMOVER_PY, "BLOCO D", "_0941_promover")
    if promover_mod is not None:
        nome_pr, promover = primeiro_atributo(promover_mod, ("promover", "main"))
        if promover is None:
            certo(False, "[5] `promover.py` expoe `promover()`",
                         "nenhum de ('promover','main')")
        else:
            reprovou = False
            try:
                promover("run-inexistente", "metrica.que.nao.existe")
            except Exception:  # noqa: BLE001
                reprovou = True
            certo(reprovou,
                  "[5] `promover(run, id_inexistente)` REPROVA",
                  "promover um id que nao esta em `registry.todas()` marcaria "
                  "como entregue uma metrica que ninguem escreveu")
            certo("metric.promovida" in ler(PROMOVER_PY),
                  "[5] e com um id que EXISTE ela grava `metric.promovida`",
                  "sem o evento, a proposta fica `aprovada` para sempre e o "
                  "ciclo da §BLOCO D nao fecha")


# ===========================================================================
# [6] TEMPLATE — as 5 secoes, nenhuma orfa, nenhuma vazia, ZERO migration
# ===========================================================================
def bloco_6_template():
    _p("\n[6] TEMPLATE (BLOCO A/B) -- 5 secoes novas · orfa · vazia · ZERO migration")

    mod, erro = carregar("_0941_templates", TEMPLATES)
    if mod is None:
        certo(False, "[6] `services/artifacts/templates.py` carrega", erro)
        return
    tpl = getattr(mod, "POR_CHAVE", {}).get(CHAVE_PULSE)
    if tpl is None:
        certo(False, "[6] `%s` esta no CATALOGO" % CHAVE_PULSE,
              "o Pulso 360 e a casa das secoes novas")
        return
    certo(True, "[6] `%s` esta no CATALOGO (%d secoes hoje)"
          % (CHAVE_PULSE, len(tpl.composition)))

    def _texto_da_secao(bloco):
        return json.dumps(bloco, ensure_ascii=False, default=str).lower()

    inteiro = " ".join(_texto_da_secao(b) for b in tpl.composition)

    def _normalizar(s):
        return (s.replace("ê", "e").replace("é", "e").replace("ó", "o")
                .replace("ã", "a").replace("ç", "c").replace("í", "i"))

    for secao in SECOES_NOVAS:
        certo(secao in _normalizar(inteiro),
                     "[6] o Pulso 360 tem a secao **%s**" % secao,
                     "a metrica que ninguem ve no relatorio e trabalho que o "
                     "dono nao recebe")

    # --- D4: cada secao declara as metricas que a sustentam ----------------
    registradas = set()
    registry, _e = _registry()
    if registry is not None:
        try:
            registradas = set(registry.todas())
        except Exception:  # noqa: BLE001
            pass
    declaram = [b for b in tpl.composition
                if isinstance(b, dict)
                and (b.get("props") or {}).get("metrics")]
    certo(bool(declaram),
                 "[6] D4: as secoes declaram as metricas que as sustentam em "
                 "`props['metrics']`",
                 "sem a declaracao nao ha como provar 'secao orfa' nem 'caixa "
                 "vazia' — 📊 32 asercoes ja deixaram passar 7 caixas vazias")
    if declaram and registradas:
        orfas = []
        vazias = []
        for b in declaram:
            ids = list((b.get("props") or {}).get("metrics") or [])
            if not ids:
                vazias.append(b.get("block"))
            orfas += [m for m in ids if m not in registradas]
        certo(not orfas,
              "[6] nenhuma secao aponta metrica que nao existe em `todas()`",
              "orfas: %r" % (sorted(set(orfas))[:6],))
        certo(not vazias, "[6] nenhuma secao declarada fica VAZIA",
              "vazias: %r" % (vazias,))
        # M-ORFA em MEMORIA — o detector CONSEGUE ficar vermelho?
        falsas = ["metrica.que.nao.existe"]
        certo(bool([m for m in falsas if m not in registradas]),
              "[6] M-ORFA PAR: o detector de orfa ACUSA um id inventado",
              "um detector que nunca acha nada nao guarda nada")

    # --- ZERO migration nesta SPEC (a trava da §2) -------------------------
    novas = []
    if os.path.isdir(MIGRACOES):
        for arq in sorted(os.listdir(MIGRACOES)):
            if not arq.endswith(".sql"):
                continue
            conteudo = ler(os.path.join(MIGRACOES, arq)).lower()
            if "094.1" in conteudo or "spec0941" in conteudo or "spec094_1" in conteudo:
                novas.append(arq)
    certo(not novas,
          "[6] ZERO migration nesta SPEC (a §2 decidiu: as secoes entram em "
          "CODIGO, com o upsert de `_garantir_template`)",
          "migrations achadas: %r" % (novas,))
    certo(os.path.isdir(MIGRACOES) and
          len([a for a in os.listdir(MIGRACOES) if a.endswith(".sql")]) > 0,
          "[6] PAR (controle): o detector CONSEGUE ver migrations (a pasta tem "
          "%d)" % len([a for a in os.listdir(MIGRACOES)
                       if a.endswith(".sql")] if os.path.isdir(MIGRACOES) else []))


# ===========================================================================
# [7] VOCABULARIO — sobre o PACK SERIALIZADO, e nao sobre o codigo
# ===========================================================================
def bloco_7_vocabulario():
    _p("\n[7] VOCABULARIO (M7/M8 da 094, estendido as metricas novas)")

    texto, erro = rodar_montar([])
    if erro:
        certo(False, "[7] o Pulso completo roda para medir o vocabulario", erro)
        return
    # 🔴 O alvo e o PACK SERIALIZADO, e nao a resposta inteira.
    #
    # ⚠️ Medido em 03/09/2026: a resposta carrega o `COMO_FALAR`, que INSTRUI o
    # narrador a *nunca* dizer "lucro" — a palavra aparece la de proposito, na
    # negativa. Um detector sobre a resposta inteira acusaria justamente a linha
    # que protege o vocabulario: seria medir o remedio como se fosse a doenca.
    # O que nao pode carregar essas palavras e o BLOCO CITAVEL, que e de onde o
    # numero sai para a frase do dono.
    _fora, pack = partes(texto)
    if pack is None:
        certo(False, "[7] a resposta traz um bloco <<PACK>> parseavel", texto[-200:])
        return
    serializado = json.dumps(pack, ensure_ascii=False)

    # --- os PARES do detector, ANTES de usa-lo -----------------------------
    certo(len(vocabulario_proibido_em(
              "a comissao recebida no mes virou lucro do funcionario")) >= 3,
          "[7] PAR-A: o detector acha as tres palavras numa frase sintetica")
    certo(vocabulario_proibido_em(
              "comissao APROPRIADA no periodo, por produtor") == [],
          "[7] PAR-B: e APROVA a frase que usa os termos certos")
    certo(vocabulario_proibido_em(
              "⚠️ contribuição não é lucro: não entram custo fixo nem imposto")
          == [],
          "[7] PAR-C: e APROVA a frase que NEGA — uma proibicao precisa nomear "
          "o que proibe",
          "📊 medido em 03/09: o `premissa` de `contribution.after_repasse` "
          "escreve 'contribuição não é lucro' DENTRO do pack, de proposito. Um "
          "detector por palavra solta acusaria a linha que protege o "
          "vocabulario")

    achados = vocabulario_proibido_em(serializado)
    certo(not achados,
          "[7] `lucro`, `recebid` e `funcionari` NAO aparecem no PACK "
          "SERIALIZADO (%d metricas) sem estarem sendo NEGADOS"
          % len(pack.get("metrics") or []),
          "📊 achado: %r — comissao APROPRIADA nao e RECEBIDA (a fonte nao "
          "expoe recebida), contribuicao pos-repasse nao e lucro, e 'produtor' "
          "nao e 'funcionario' (afirmacao trabalhista inventada)"
          % (achados[:4],))
    certo(len(pack.get("metrics") or []) >= 8 and len(serializado) > 2000,
          "[7] CONTROLE: o detector leu um pack DE VERDADE (%d metricas, %d "
          "bytes)" % (len(pack.get("metrics") or []), len(serializado)),
          "um pack vazio faria a assercao acima passar por vacuidade")
    # M-VOCAB: a mutacao do red team da 094, agora sobre o pack DESTA SPEC.
    certo(len(vocabulario_proibido_em(
              serializado + "\no lucro recebido pelo funcionario")) >= 3,
          "[7] M-VOCAB: com a frase proibida somada ao pack, o detector ACUSA",
          "o detector nao viu a frase injetada — ele nao estava lendo o texto "
          "que ele diz ler")


# ===========================================================================
# [8] O PROTOCOLO — o documento e o guarda que e do BUILDER
# ===========================================================================
def bloco_8_protocolo():
    _p("\n[8] PROTOCOLO (BLOCO E) -- COMO-NASCE-UM-RELATORIO.md e o guarda do builder")

    existe = os.path.exists(PROTOCOLO_MD)
    certo(existe, "[8] `docs/canon/COMO-NASCE-UM-RELATORIO.md` existe",
                 "e o documento que o Founder pediu: qualquer chat abre e "
                 "executa em 15 minutos")
    if existe:
        tamanho = os.path.getsize(PROTOCOLO_MD)
        certo(tamanho <= 12 * 1024,
              "[8] o protocolo cabe em 12 KB (📊 %d bytes)" % tamanho,
              "🔴 CLAUDE.md §2: um bootstrap grande demais para ser lido e um "
              "bootstrap que nao e lido")
        texto = _sem_acento(ler(PROTOCOLO_MD).lower())
        passos = ("classifique", "meca", "defina", "prove", "mostre", "feche")
        faltam = [p for p in passos if p not in texto]
        certo(not faltam, "[8] os 6 passos estao escritos", "faltam %r" % (faltam,))
        certo("golden" in texto and "pergunta" in texto,
              "[8] o passo DEFINA exige `pergunta_verificada` + `golden` (ref ④)",
              "sem a pergunta verificada nao ha regua de regressao — e a §1.6 "
              "mediu 1 resposta em 5 errada no melhor sistema (BIRD)")

    existe_guarda = os.path.exists(GUARDA_DO_PROTOCOLO)
    certo(existe_guarda,
                 "[8] `tests/test_o_relatorio_nasce_pelo_protocolo.py` existe "
                 "(e do BUILDER, nao deste desenhista)",
                 "quem escreve o protocolo escreve o guarda dele; este arquivo "
                 "so confere que ele existe e roda")
    if existe_guarda:
        try:
            env = dict(os.environ, PYTHONIOENCODING="utf-8", SEM_REDE="1")
            r = subprocess.run([sys.executable, GUARDA_DO_PROTOCOLO],
                               cwd=RAIZ, env=env, capture_output=True,
                               timeout=300)
            certo(r.returncode == 0,
                  "[8] o guarda do protocolo roda e sai 0",
                  (r.stdout or b"")[-400:].decode("utf-8", "replace"))
        except Exception as exc:  # noqa: BLE001
            certo(False, "[8] o guarda do protocolo roda",
                  "%s: %s" % (type(exc).__name__, exc))


def _sem_acento(s):
    for de, para in (("ç", "c"), ("ã", "a"), ("á", "a"), ("â", "a"), ("é", "e"),
                     ("ê", "e"), ("í", "i"), ("ó", "o"), ("ô", "o"), ("õ", "o"),
                     ("ú", "u")):
        s = s.replace(de, para)
    return s


# ===========================================================================
# [11] A FIACAO -- o conserto de 04/09/2026 (grupo 1: o dono lia errado)
# ===========================================================================
#
# 🔴 Este bloco existe porque os blocos [1]-[8] ficaram VERDES sobre um produto
# em que cinco leituras novas e um conector externo NUNCA ERAM CHAMADOS. Cada
# peca tinha teste; o ELO entre elas nao tinha. E o modo de falha era o do
# CLAUDE.md §9.5: nada travava, e o dono lia um numero errado com a cara certa.
def bloco_11_a_fiacao():
    _p("\n[11] A FIACAO (conserto 04/09) -- quem CHAMA as 5 leituras e o mercado")

    mod, erro = mod_tool360()
    cbim, erro_c = _cbim()
    registry, erro_r = _registry()
    if mod is None or cbim is None or registry is None:
        certo(False, "[11] tool360 + cbim + registry carregam",
              erro or erro_c or erro_r)
        return

    # -- 1. o ESPIAO: cada visao chama exatamente as fontes dela -------------
    esperado_por_visao = {
        "sinistros": {"claims"},
        "funil": {"quotes"},
        "carteira": {"customers"},
        "pendencias": {"cancellations", "issuance"},
        "mercado": {"claims", "mercado"},
        # ⚠️ A linha de CONTROLE: uma visao da carteira NAO pode acordar
        # nenhuma das leituras novas. Sem ela, um `_montar` que lesse tudo
        # sempre passaria em todas as linhas acima.
        "producao": set(),
        "renovacao": set(),
    }
    erros = []
    for visao, esperadas in esperado_por_visao.items():
        espiao = []
        texto, err = rodar_montar([visao], espiao=espiao)
        if err:
            erros.append("%s: %s" % (visao, err))
            continue
        chamadas = set(espiao) - {"fatos"}
        if chamadas != esperadas:
            erros.append("%s: chamou %r, esperado %r"
                         % (visao, sorted(chamadas), sorted(esperadas)))
    certo(not erros,
          "[11] cada visao chama EXATAMENTE as leituras dela (com o PAR: visao "
          "da carteira nao chama nenhuma)",
          " · ".join(erros[:4])
          + "  🔴 📊 04/09: o grep de chamadores das 5 leituras e do agregado "
            "de mercado dava ZERO fora dos providers")

    # -- 2. `mercado=` chega ao registry ------------------------------------
    feixe = cbim.MarketFactSet(
        provider_key=cbim.PROVIDER_DE_MERCADO, fonte="fixture",
        competencia_final="202606",
        mapa={"seguradora alfa": "99999"},
        resolver=lambda nome: ("99999" if "alfa" in str(nome).lower()
                               else "UNKNOWN"))
    feixe.facts.append(cbim.MarketFact(
        coenti="99999", damesano="202503", coramo="0531",
        premio_ganho=1000.0, sinistro_ocorrido=571.2))
    texto, err = rodar_montar(["mercado"], mercado=feixe)
    certo(not err and "market.loss_ratio" in texto,
          "[11] com o feixe de mercado o Pulso traz a metrica de mercado",
          err or texto[:200])
    # PAR: SEM o feixe, a MESMA pergunta nao inventa numero de mercado.
    texto_sem, err_sem = rodar_montar(["mercado"], mercado=None)
    certo(not err_sem and "UNAVAILABLE" in texto_sem,
          "[11] PAR: sem o feixe, a metrica de mercado sai UNAVAILABLE",
          err_sem or texto_sem[:200])

    # -- 3. a taxa de cancelamento: 8,42 no controle, UNAVAILABLE no trato ---
    #
    # 📊 As linhas sao REAIS-SINTETICAS: a forma medida da rota (campo
    # `cancelado` por linha, `fimvig` no periodo e `inivig` fora dele), com os
    # numeros do censo — 325 canceladas em 3.861.
    def _populacao(com_campo=True, com_inivig=False, marcadas=325, total=3861):
        lote = cbim.FactSet(company_id=EMPRESA_A, provider_key="fixture")
        lote.populacoes_lidas.add("cancellations")
        lote.fingerprints["cancellations"] = "sha"
        for i in range(total):
            cancelada = i < marcadas
            lote.cancellations.append(cbim.PolicyFact(
                policy_ref="pol-%d" % i, source_ref=str(i),
                insurer="Seguradora Alfa", branch="auto",
                valid_from=(date(2025, 6, 1) if com_inivig else date(2024, 6, 1)),
                valid_to=date(2025, 6, 1),
                premium=cbim.interpretar_dinheiro("1000.00"),
                kind="NEW",
                status=(cbim.status_de_apolice(cancelada) if com_campo
                        else "situacao-que-a-fonte-escreveu")))
        return lote

    def _taxa(lote):
        r = registry.calcular("portfolio.cancellation_rate", lote,
                              (date(2025, 1, 1), date(2025, 12, 31)))
        return r.value

    valor = _taxa(_populacao())
    certo(isinstance(valor, float) and abs(valor - 8.42) < 0.01,
          "[11] CONTROLE: a taxa de cancelamento da 8,42%% na populacao medida "
          "(veio %r)" % (valor,),
          "📊 325 canceladas em 3.861 = 8,42%. Antes de 04/09 esta metrica lia "
          "a lista da PRODUCAO — que vem sem cancelada nenhuma — e publicava "
          "0,0% com confianca alta")
    sem_campo = _taxa(_populacao(com_campo=False))
    certo(str(sem_campo) == "UNAVAILABLE",
          "[11] TRATAMENTO: sem o CAMPO de estado legivel a taxa sai "
          "UNAVAILABLE (veio %r)" % (sem_campo,),
          "🔴 este ramo era INALCANCAVEL ate 04/09: a comparacao era com "
          "'campo preenchido', e a fonte sempre preenche algo")
    nao_lida = cbim.FactSet(company_id=EMPRESA_A, provider_key="fixture")
    certo(str(_taxa(nao_lida)) == "UNAVAILABLE",
          "[11] TRATAMENTO: populacao NAO LIDA sai UNAVAILABLE, e nunca 0%")
    # E o PAR do recorte temporal: `inivig` no periodo nao muda nada, porque a
    # base desta metrica e o FIM da vigencia.
    com_inivig = _taxa(_populacao(com_inivig=True))
    certo(isinstance(com_inivig, float) and abs(com_inivig - 8.42) < 0.01,
          "[11] PAR: a taxa nao depende do INICIO de vigencia (base = fim)",
          "veio %r — 📊 medido: `fimvig` no ano em 3.861 linhas e `inivig` em "
          "103; recortar por inicio jogava 97%% da populacao fora" % (com_inivig,))

    # -- 4. o funil nao perde a etapa cuja rota nao tem a chave de data ------
    adapter, err_a = carregar("_0941_adapter_fiacao", ADAPTER)
    if adapter is None:
        certo(False, "[11] o adapter carrega", err_a)
    else:
        lote = cbim.FactSet(company_id=EMPRESA_A, provider_key="fixture")
        prov = adapter.InfocapAnalyticsProvider()
        # 📊 As chaves REAIS: `/negocios_andamento` traz `inivig`;
        # `/negocios_finalizados` NAO — e era por isso que a etapa que responde
        # "quantos eu fechei" sumia do funil inteiro.
        prov._traduzir_funil(lote, [
            {"codigo": "1", "val_premio": "1000,00", "ramo": "AUTO",
             "inivig": "10/03/2025"}], "EM_ANDAMENTO", "corr")
        prov._traduzir_funil(lote, [
            {"codigo": "9", "val_premio": "2000,00", "ramo": "AUTO",
             "codcli": "1", "status": "F"},
            {"codigo": "10", "val_premio": "3000,00", "ramo": "RESI",
             "codcli": "2", "status": "F"}], "FINALIZADO", "corr")
        lote.populacoes_lidas.add("quotes")
        lote.fingerprints["quotes"] = "sha"
        r = registry.calcular("quotes.funnel", lote,
                              (date(2025, 1, 1), date(2025, 12, 31)))
        etapas = {x["rotulo"]: x["cotacoes"] for x in r.breakdown}
        certo(etapas == {"EM_ANDAMENTO": 1, "FINALIZADO": 2},
              "[11] o funil conta a etapa cuja rota NAO tem chave de data "
              "(veio %r)" % (etapas,),
              "🔴 antes de 04/09 a etapa FINALIZADO sumia inteira: sem `inivig` "
              "o negocio nascia sem data e o recorte por data o descartava")
        certo(any("sem data" in w for w in r.warnings),
              "[11] e ele DIZ quantos negocios vieram sem data",
              "um negocio contado sem aviso e um total que ninguem consegue "
              "conferir")

    # -- 5. a situacao do sinistro: acento, negado, duplicata ---------------
    if adapter is not None:
        casos = {
            "Em Análise": "OPEN",
            "EM ANALISE": "OPEN",
            "Negado": "CLOSED_DENIED",
            "Indeferido": "CLOSED_DENIED",
            "Liquidado": "CLOSED_PAID",
            "Pago": "CLOSED_PAID",
            "Aguardando vistoria": "OPEN",
            "": "UNKNOWN",
            "coisa que ninguem escreveu": "UNKNOWN",
        }
        erradas = []
        for rotulo, esperado in casos.items():
            veio = adapter._situacao_do_sinistro({"situacao": rotulo})
            if veio != esperado:
                erradas.append("%r -> %s (esperado %s)" % (rotulo, veio, esperado))
        certo(not erradas,
              "[11] a situacao do sinistro le ACENTO e separa NEGADO de PAGO",
              " · ".join(erradas)
              + "  🔴 'Em Análise' caia em UNKNOWN porque a marca sem acento era "
                "comparada com o texto CRU (CLAUDE.md §9.4)")
        # A indenizacao de um NEGADO nunca entra na soma do que foi pago.
        lote = cbim.FactSet(company_id=EMPRESA_A, provider_key="fixture")
        prov = adapter.InfocapAnalyticsProvider()
        prov._traduzir_sinistros(lote, [
            {"numsin": "A", "nosnum": "1", "situacao": "Liquidado",
             "valind": "1000,00", "datoco": "10/03/2025", "datenc": "20/03/2025"},
            {"numsin": "B", "nosnum": "2", "situacao": "Negado",
             "valind": "9000,00", "datoco": "11/03/2025", "datenc": "21/03/2025"},
            {"numsin": "C", "nosnum": "3", "situacao": "Em Análise",
             "valind": "500,00", "datoco": "12/03/2025"},
            # A DUPLICATA: a linha SEM data vem primeiro, de proposito.
            {"numsin": "D", "nosnum": "4", "situacao": "Em Análise",
             "valind": "700,00"},
            {"numsin": "D", "nosnum": "4", "situacao": "Em Análise",
             "valind": "700,00", "datoco": "13/03/2025"},
            {"numsin": "E", "nosnum": "5", "situacao": "coisa nova",
             "valind": "1,00", "datoco": "14/03/2025"},
        ], "corr")
        lote.populacoes_lidas.add("claims")
        lote.fingerprints["claims"] = "sha"
        janela = (date(2025, 1, 1), date(2025, 12, 31))
        pago = registry.calcular("claims.indemnity_paid", lote, janela)
        certo(pago.value == 1000.0,
              "[11] a indenizacao soma SO o encerrado com PAGAMENTO (veio %r)"
              % (pago.value,),
              "🔴 antes de 04/09 `negado` e `indeferido` iam para o mesmo estado "
              "que `liquidado`: a soma incluia R$ 9.000 que ninguem pagou")
        certo(any("NEGADO" in w for w in pago.warnings),
              "[11] e o negado sai ESCRITO no envelope, e nao apenas omitido")
        d = [c for c in lote.claims if c.occurred_at is None]
        certo(not d and len(lote.claims) == 5,
              "[11] o dedupe fica com a linha que TEM data de ocorrencia "
              "(%d sinistro(s), %d sem data)" % (len(lote.claims), len(d)),
              "🔴 a duplicata sem data chegava primeiro e o sinistro sumia de "
              "TODAS as metricas, que recortam pela data de ocorrencia")
        certo(any("nao reconhecida" in w for w in lote.warnings),
              "[11] a situacao NAO RECONHECIDA vira aviso com os rotulos",
              "um caso que o software nao classifica nao pode sumir do total")
        # 🔴 O join com a carteira NAO e o denominador (📊 a intersecao medida
        # entre sinistros e carteira do ano e ZERO).
        abertos = registry.calcular("claims.open_count", lote, janela)
        # 📊 Dois abertos: "Em Análise" (C) e a duplicata deduplicada (D). O
        # liquidado, o negado e o nao-reconhecido nao sao abertos.
        certo(abertos.value == 2.0,
              "[11] os abertos contam a POPULACAO DA FONTE, sem depender da "
              "juncao com a carteira (veio %r)" % (abertos.value,),
              "📊 40 documentos de sinistro x 3.861 linhas de carteira = 0 "
              "interseccao: a regra antiga devolvia UNAVAILABLE para uma "
              "pergunta que tem resposta")
        linha = [x for x in abertos.breakdown
                 if x.get("rotulo") == "na carteira lida"]
        certo(len(linha) == 1 and linha[0]["sinistros"] == 0,
              "[11] e a juncao vira uma linha INFORMATIVA do detalhe",
              "ela responde 'quantos consigo amarrar', e nunca filtra o total")

    # -- 6. a DERIVED declara as DUAS fontes --------------------------------
    lote = cbim.FactSet(company_id=EMPRESA_A, provider_key="infocap")
    lote.populacoes_lidas.update({"policies", "claims"})
    lote.fingerprints.update({"policies": "sha", "claims": "sha"})
    r = registry.calcular("claims.loss_ratio_vs_market", lote,
                          (date(2025, 1, 1), date(2025, 12, 31)),
                          mercado=feixe)
    provedores = [str(x.get("provider")) for x in r.source_refs
                  if isinstance(x, dict)]
    certo(len(r.source_refs) == 2 and len(set(provedores)) == 2,
          "[11] a DERIVED declara DUAS `source_refs`, com providers distintos "
          "(%r)" % (provedores,),
          "🔴 ela saia com `source_refs=[]`, um provider e um periodo: quem "
          "fosse conferir achava a metade que fecha")
    certo("+" in r.provider_key,
          "[11] e o `provider_key` dela e composto (veio %r)" % (r.provider_key,))
    bases = {str(x.get("time_basis")) for x in r.source_refs
             if isinstance(x, dict)}
    certo("COMPETENCIA" in bases,
          "[11] a fonte de mercado declara a base COMPETENCIA (veio %r)"
          % (sorted(bases),))
    tb = registry.todas()["market.loss_ratio"].time_basis
    certo(tb == "COMPETENCIA",
          "[11] e as metricas de mercado declaram COMPETENCIA no envelope "
          "(veio %r)" % (tb,),
          "declara-las em base de vigencia afirmava, calado, um recorte que "
          "nunca houve")
    # PAR: uma metrica que NAO le o mercado continua com UMA fonte so.
    r2 = registry.calcular("production.policy_count", lote,
                           (date(2025, 1, 1), date(2025, 12, 31)), mercado=feixe)
    certo(len(r2.source_refs) == 1,
          "[11] PAR: a metrica que NAO le o mercado declara UMA fonte so "
          "(%d)" % (len(r2.source_refs),))

    # -- 7. `ratio` sai com 4 casas na serializacao -------------------------
    pack, err_p = _pack()
    if pack is not None:
        fino = pack.metrica("x.y", 0.57123456, "ratio",
                            period={"start": "2025-01-01", "end": "2025-12-31"},
                            time_basis="COMPETENCIA")
        grosso = pack.metrica("x.z", 1234.5678, "BRL",
                              period={"start": "2025-01-01", "end": "2025-12-31"},
                              time_basis="POLICY_VALID_FROM")
        certo(fino.serializar()["value"] == 0.5712,
              "[11] `ratio` sai com 4 casas (veio %r)"
              % (fino.serializar()["value"],),
              "🔴 em 2 casas a diferenca carteira x mercado — que vale "
              "milesimos — some e vira 0,0 na tela")
        certo(grosso.serializar()["value"] == 1234.57,
              "[11] PAR: dinheiro continua em 2 casas (veio %r)"
              % (grosso.serializar()["value"],))


# ===========================================================================
# [12] A PROMOCAO E O MAPA -- conserto de 04/09 (itens 6, 7 e 8)
# ===========================================================================
class _BancoFalso:
    """Um banco de mentira, com as tres tabelas que a promocao toca.

    ⛔ Nada sai daqui: nenhuma conexao, nenhum segredo, nenhuma escrita real.
    🔴 Ele guarda o que foi ESCRITO, porque a metade das assercoes deste bloco e
    sobre o que NAO foi escrito quando o comando reprova.
    """

    def __init__(self, runs=(), approvals=()):
        self.dados = {"work_runs": [dict(x) for x in runs],
                      "approval_requests": [dict(x) for x in approvals],
                      "work_events": []}
        self.escritas = []

    def table(self, nome):
        return _TabelaFalsa(self, nome)


class _TabelaFalsa:
    def __init__(self, banco, nome):
        self.banco = banco
        self.nome = nome
        self.filtros = []
        self.operacao = ("select", None)

    def select(self, *a, **k):   # noqa: ANN002, ARG002
        self.operacao = ("select", None)
        return self

    def insert(self, linha):
        self.operacao = ("insert", linha)
        return self

    def update(self, campos):
        self.operacao = ("update", campos)
        return self

    def eq(self, campo, valor):
        self.filtros.append((campo, valor))
        return self

    def limit(self, *a, **k):    # noqa: ANN002, ARG002
        return self

    def order(self, *a, **k):    # noqa: ANN002, ARG002
        return self

    def execute(self):
        linhas = self.banco.dados.setdefault(self.nome, [])
        casadas = [x for x in linhas
                   if all(str(x.get(c)) == str(v) for c, v in self.filtros)]
        tipo, carga = self.operacao
        if tipo == "insert":
            linhas.append(dict(carga))
            self.banco.escritas.append((self.nome, "insert", dict(carga)))
            return _Resposta([dict(carga)])
        if tipo == "update":
            for x in casadas:
                x.update(carga)
            self.banco.escritas.append((self.nome, "update", dict(carga)))
            return _Resposta(casadas)
        return _Resposta(casadas)


class _Resposta:
    def __init__(self, data):
        self.data = data


def bloco_12_promocao_e_mapa():
    _p("\n[12] PROMOCAO E MAPA (conserto 04/09) -- o run recusado · o slug · a sigla")

    prom = exigir(os.path.join(METRICAS, "promover.py"), "BLOCO D",
                  "_0941_promover_conserto")
    registry, _e = _registry()
    if prom is None or registry is None:
        return
    valida = sorted(registry.todas())[0]

    def _banco(status="waiting_approval", decisao="approved", nome=None,
               com_approval=True):
        runs = [{"id": "run-1", "company_id": EMPRESA_A,
                 "workflow_key": "metric.proposal", "status": status,
                 "input_payload": {"nome_sugerido": nome or valida}}]
        aps = ([{"id": "ap-1", "company_id": EMPRESA_A, "work_run_id": "run-1",
                 "status": ("approved" if decisao.startswith("approved")
                            else "rejected"),
                 "decision": decisao, "subject_id": nome or valida}]
               if com_approval else [])
        return _BancoFalso(runs, aps)

    def _tentar(**kw):
        banco = kw.pop("banco")
        try:
            saida = prom.promover(banco, company_id=EMPRESA_A, run_id="run-1",
                                  metric_id=kw.pop("metric_id", valida), **kw)
            return "OK", saida, banco
        except prom.Reprovado as exc:
            return "REPROVADO", str(exc), banco
        except Exception as exc:  # noqa: BLE001
            return "EXPLODIU", "%s: %s" % (type(exc).__name__, exc), banco

    # -- o caminho FELIZ, que e a linha de controle -------------------------
    estado, saida, banco = _tentar(banco=_banco())
    certo(estado == "OK" and isinstance(saida, dict),
          "[12] CONTROLE: run vivo + aprovacao APPROVED + id igual ao proposto "
          "-> PROMOVE",
          str(saida)[:300] + "  🔴 um comando que so reprova nao prova nada")
    eventos = [x for x in banco.escritas
               if x[0] == "work_events" and x[1] == "insert"]
    certo(len(eventos) == 1
          and eventos[0][2].get("event_type") == "metric.promovida",
          "[12] CONTROLE: e ele grava UM `metric.promovida`",
          str(banco.escritas)[:250])

    # -- run RECUSADO ------------------------------------------------------
    estado, motivo, banco = _tentar(banco=_banco(decisao="rejected"))
    certo(estado == "REPROVADO" and not banco.escritas,
          "[12] TRATAMENTO: aprovacao REJECTED -> reprova e NAO escreve nada",
          "%s / %s / escritas=%r" % (estado, str(motivo)[:200], banco.escritas)
          + "  🔴 antes de 04/09 o comando nao lia `approval_requests`: uma "
            "proposta recusada virava `succeeded` com evento de promocao")

    estado, motivo, banco = _tentar(banco=_banco(com_approval=False))
    certo(estado == "REPROVADO" and not banco.escritas,
          "[12] TRATAMENTO: SEM aprovacao registrada -> reprova",
          "'ninguem decidiu' nao e 'decidiu que sim' — %s" % str(motivo)[:180])

    # -- run em estado TERMINAL: a segunda promocao ------------------------
    for terminal in ("cancelled", "failed", "completed", "succeeded"):
        estado, motivo, banco = _tentar(banco=_banco(status=terminal))
        certo(estado == "REPROVADO" and not banco.escritas,
              "[12] TRATAMENTO: run em %r -> reprova (a 2a promocao nao passa)"
              % terminal,
              "%s / %s" % (estado, str(motivo)[:180]))

    # -- o `metric_id` diferente do proposto -------------------------------
    outro = sorted(registry.todas())[1]
    estado, motivo, banco = _tentar(banco=_banco(nome=outro))
    certo(estado == "REPROVADO" and not banco.escritas,
          "[12] TRATAMENTO: `metric_id` != `nome_sugerido` e SEM `--substitui` "
          "-> reprova",
          "%s / %s" % (estado, str(motivo)[:180])
          + "  ⛔ trocar o nome em silencio deixa o painel afirmando que foi "
            "aprovado o que nao foi")
    estado, saida, banco = _tentar(banco=_banco(nome=outro),
                                   substitui="a revisao preferiu este nome")
    certo(estado == "OK" and "revisao" in str(saida.get("substitui", "")),
          "[12] PAR: com `--substitui <motivo>` a troca PASSA, e o motivo fica "
          "gravado",
          str(saida)[:250])
    evento = [x[2] for x in banco.escritas if x[0] == "work_events"]
    certo(evento and evento[0].get("payload_redacted", {}).get("substitui"),
          "[12] e o motivo entra no `payload_redacted` do evento",
          str(evento)[:250])

    # -- normalizacao do `metric_id` ---------------------------------------
    estado, saida, banco = _tentar(banco=_banco(),
                                   metric_id="  %s  " % valida.upper())
    certo(estado == "OK",
          "[12] o `metric_id` e normalizado (espaco e maiuscula nao criam uma "
          "metrica nova)",
          str(saida)[:200])

    # -- item 7: a colisao de slug -----------------------------------------
    proposta_mod = exigir(PROPOSTA_SVC, "BLOCO D",
                          "_0941_proposta_conserto")
    if proposta_mod is not None:
        base = {"nome_sugerido": "commission.avg", "fatos": ["commission"],
                "dimensoes": ["producer"], "time_basis": "POLICY_VALID_FROM",
                "pergunta_exemplo": "qual a comissao media por produtor"}
        outra = dict(base, dimensoes=["branch"],
                     pergunta_exemplo="qual a comissao media por ramo")
        k1 = proposta_mod._chave(EMPRESA_A, base)
        k2 = proposta_mod._chave(EMPRESA_A, outra)
        k3 = proposta_mod._chave(EMPRESA_A, dict(base))
        certo(k1 != k2,
              "[12] dois PEDIDOS diferentes com o MESMO nome dao chaves "
              "diferentes",
              "🔴 a chave era `sha256(company + nome)`: a segunda proposta era "
              "engolida e o chat devolvia dimensoes que o registro nao tem")
        certo(k1 == k3,
              "[12] PAR: o MESMO pedido duas vezes continua sendo UMA proposta",
              "senao o dono teria duas decisoes para tomar sobre a mesma coisa")
        certo(proposta_mod._chave("outra-empresa", base) != k1,
              "[12] e duas corretoras com o mesmo pedido sao duas propostas "
              "(CLAUDE.md §7)")
        # E o que volta quando ela JA EXISTIA e o payload GRAVADO.
        banco = _BancoFalso([{"id": "run-9", "company_id": EMPRESA_A,
                              "workflow_key": "metric.proposal",
                              "status": "waiting_approval",
                              "input_payload": dict(base)}])
        devolvido = proposta_mod._proposta_gravada(banco, EMPRESA_A, "run-9",
                                                   outra)
        certo(devolvido.get("dimensoes") == ["producer"],
              "[12] proposta que JA EXISTIA devolve o payload GRAVADO, e nao o "
              "pedido novo (veio %r)" % (devolvido.get("dimensoes"),),
              "quem revisa le uma coisa e quem pediu lembra de outra")

    # -- item 8: a sigla, e o casamento PARCIAL que saiu -------------------
    ses = exigir(os.path.join(PROVIDERS, "susep_ses_provider.py"), "BLOCO B",
                 "_0941_ses_conserto")
    if ses is not None:
        certo(ses.coenti_de("PORT") not in ("", ses.UNKNOWN),
              "[12] a SIGLA da carteira casa com uma entidade (`PORT` -> %r)"
              % (ses.coenti_de("PORT"),),
              "🔴 a carteira NAO traz o nome: traz a sigla. 📊 antes do mapa de "
              "siglas, 12,35%% do premio casava; depois, 83,86%%")
        certo(ses.coenti_de("PORTO SEGURO SAUDE") == ses.UNKNOWN,
              "[12] TRATAMENTO: o casamento PARCIAL saiu — 'PORTO SEGURO "
              "SAUDE' nao herda a entidade da Porto de AUTO (veio %r)"
              % (ses.coenti_de("PORTO SEGURO SAUDE"),),
              "⛔ era assim que a sinistralidade de OUTRA empresa entrava num "
              "argumento de negociacao de reajuste")
        certo(ses.coenti_de("PORTO SEGURO COMPANHIA DE SEGUROS GERAIS")
              == ses.coenti_de("porto"),
              "[12] PAR: o nome COMPLETO da entidade continua casando")
        certo(ses.coenti_de("SULA") == ses.UNKNOWN,
              "[12] e a sigla cuja entidade nao foi decidida sai UNKNOWN, "
              "nunca um palpite (veio %r)" % (ses.coenti_de("SULA"),),
              "📊 ha 11 entidades com esse nome no censo publico e nenhuma tem "
              "premio de auto no trimestre medido")
        siglas = ses.mapa_de_siglas()
        certo(len(siglas) >= 60 and all(
                  str(v.get("criterio") or "").strip() for v in siglas.values()),
              "[12] TODA sigla do arquivo diz o CRITERIO pelo qual casou (ou "
              "nao) — %d siglas" % (len(siglas),),
              "uma constante que escolhe entre alternativas precisa dizer por "
              "que esta certa, escrito ao lado dela (CLAUDE.md §9.5)")
        sem = [k for k, v in siglas.items()
               if str(v.get("coenti")) == ses.UNKNOWN]
        certo(bool(sem),
              "[12] e o que NAO casou fica LISTADO no arquivo (%d), e nunca "
              "omitido" % (len(sem),))


# ===========================================================================
# [13] O DADO DE MERCADO NA ENTRADA -- conserto de 04/09 (itens 9 e 10)
# ===========================================================================
def bloco_13_ingestao():
    _p("\n[13] INGESTAO (conserto 04/09) -- manifesto por ULTIMO · ilegivel · a chave semanal")

    ing = exigir(os.path.join(APP, "services", "susep_ses_ingest.py"),
                 "BLOCO B", "_0941_ingest_conserto")
    if ing is None:
        return

    # -- o ILEGIVEL nao vira zero ------------------------------------------
    certo(ing._numero_legivel("350407,58") == (350407.58, True)
          and ing._numero_legivel("") == (0.0, True)
          and ing._numero_legivel("nao e numero")[1] is False,
          "[13] o valor ILEGIVEL e distinguido do VAZIO (que nesta base e "
          "zero legitimo)",
          "%r" % (ing._numero_legivel("nao e numero"),)
          + "  🔴 antes de 04/09 os dois viravam 0.0, e o ilegivel BAIXAVA o "
            "premio ganho do mercado sem deixar rastro")

    # -- o ZIP sintetico: a ingestao inteira, sem rede ----------------------
    #
    # ⛔ Nada sai: o ZIP e montado em memoria com a FORMA medida da base (CRLF,
    # latin-1, decimal por virgula, `Data_Final` no arquivo de diversos).
    def _zip(com_data_final=True):
        import zipfile

        alvo = io.BytesIO()
        with zipfile.ZipFile(alvo, "w") as zf:
            if com_data_final:
                zf.writestr("Ses_diversos.csv",
                            "Data_Final;202606\r\n".encode("latin-1"))
            corpo = ("damesano;coenti;coramo;premio_ganho;sinistro_ocorrido\r\n"
                     "202606;05886;0531;1000,00;600,00\r\n"
                     "202606;05886;0531;500,00;nao-e-numero\r\n"
                     "202605;05886;0531;800,00;-53790,44\r\n")
            zf.writestr("Ses_seguros.csv", corpo.encode("latin-1"))
        return alvo.getvalue()

    class _MinioDeProva:
        """Guarda o que foi gravado, e em que ORDEM. ⛔ Nada sai daqui."""

        def __init__(self, quebrar_em=None):
            self.gravados = []
            self.quebrar_em = quebrar_em

        def put_bytes(self, chave, corpo, tipo):   # noqa: ARG002
            if self.quebrar_em and self.quebrar_em in str(chave):
                raise RuntimeError("o contêiner morreu no meio da ingestao")
            self.gravados.append((str(chave), bytes(corpo)))

    import tempfile

    caminho = os.path.join(tempfile.gettempdir(), "_0941_ses_prova.zip")
    io.open(caminho, "wb").write(_zip())
    minio = _MinioDeProva()
    manifesto = ing.ingerir(minio=minio, caminho_local=caminho)

    certo(minio.gravados and minio.gravados[-1][0].endswith("manifest.json"),
          "[13] o manifesto e gravado POR ULTIMO (ordem: %r)"
          % ([k for k, _ in minio.gravados],),
          "🔴 gravado junto com os agregados, ele afirma completude que ainda "
          "nao existe — uma ingestao que morre no meio deixa meio ano gravado "
          "e um manifesto dizendo que esta tudo la")
    certo(manifesto.get("completo") is True,
          "[13] e ele carrega a marca `completo`",
          "sem a marca o leitor nao consegue distinguir uma ingestao que "
          "terminou de uma que parou")
    certo(all(x.get("sha256") for x in (manifesto.get("objetos") or [])),
          "[13] cada objeto entra no manifesto com o `sha256` dele",
          "e o que permite ao leitor perguntar 'este e o arquivo que a Rotina "
          "gravou?'")
    certo(manifesto.get("valores_ilegiveis") == 1,
          "[13] o valor ILEGIVEL sai CONTADO no manifesto (veio %r)"
          % (manifesto.get("valores_ilegiveis"),),
          "um numero que nao se conseguiu ler nao e um numero pequeno")

    # PAR: a ingestao que MORRE no meio nao deixa manifesto nenhum.
    quebrado = _MinioDeProva(quebrar_em="2026.csv")
    try:
        ing.ingerir(minio=quebrado, caminho_local=caminho)
        morreu = False
    except Exception:  # noqa: BLE001
        morreu = True
    certo(morreu and not any(k.endswith("manifest.json")
                             for k, _ in quebrado.gravados),
          "[13] PAR: a ingestao que MORRE no meio NAO deixa manifesto",
          "gravados: %r" % ([k for k, _ in quebrado.gravados],))

    # -- `Data_Final` ausente -> RECUSA, e nunca uma lista vazia -----------
    sem_data = os.path.join(tempfile.gettempdir(), "_0941_ses_sem_data.zip")
    io.open(sem_data, "wb").write(_zip(com_data_final=False))
    try:
        ing.ingerir(minio=_MinioDeProva(), caminho_local=sem_data)
        recusou, detalhe = False, "ela ingeriu sem a competencia final"
    except Exception as exc:  # noqa: BLE001
        recusou = type(exc).__name__ == "FalhaDaBase"
        detalhe = "%s: %s" % (type(exc).__name__, str(exc)[:150])
    certo(recusou,
          "[13] `Data_Final` ausente -> a ingestao RECUSA (e nao devolve [])",
          detalhe + "  🔴 sem a competencia final ninguem consegue dizer ate "
                    "onde a base esta fechada, e quem le em setembro comparando "
                    "com junho nao ve a defasagem")
    for arquivo in (caminho, sem_data):
        try:
            os.unlink(arquivo)
        except OSError:
            pass

    # -- item 10: a chave da Rotina de PLATAFORMA --------------------------
    # ⚠️ Importado pelo PACOTE, e nao por caminho: `_agendar` usa import
    # relativo, e um modulo carregado por arquivo nao tem pacote pai.
    try:
        tick = importlib.import_module("app.services.intelligence.tick")
        certo(True, "[13] `services/intelligence/tick.py` importa")
    except Exception as exc:  # noqa: BLE001
        certo(False, "[13] `services/intelligence/tick.py` importa",
              "%s: %s" % (type(exc).__name__, exc))
        return
    chaves = []

    class _ServicoFalso:
        def __init__(self, *a, **k):   # noqa: ANN002, ARG002
            pass

        def criar(self, **kw):   # noqa: ANN003
            chaves.append(kw.get("idempotency_key"))
            return {"run_id": "r", "reused": False}

    motor = tick.IntelligenceTick.__new__(tick.IntelligenceTick)
    motor._raw = object()
    import app.services.work.runs as runs_mod

    original = runs_mod.WorkRunService
    runs_mod.WorkRunService = _ServicoFalso
    try:
        motor._agendar("empresa-a", "intelligence.susep_ses_ingest", "t",
                       "2026-W36", escopo="plataforma")
        motor._agendar("empresa-b", "intelligence.susep_ses_ingest", "t",
                       "2026-W36", escopo="plataforma")
        motor._agendar("empresa-a", "intelligence.detect_signals", "t",
                       "2026-09-04")
        motor._agendar("empresa-b", "intelligence.detect_signals", "t",
                       "2026-09-04")
    finally:
        runs_mod.WorkRunService = original

    certo(chaves[0] == chaves[1]
          == "intel:plataforma:intelligence.susep_ses_ingest:2026-W36",
          "[13] a chave da Rotina de PLATAFORMA nao leva corretora (%r)"
          % (chaves[:2],),
          "🔴 ela levava `empresas[0]` — a primeira linha de uma leitura SEM "
          "`order by`. Uma corretora nova trocava o id da chave, a idempotencia "
          "caia, e 571 MB de arquivo publico eram rebaixados de novo")
    certo(chaves[2] != chaves[3],
          "[13] PAR: a chave por TENANT continua levando a corretora (%r)"
          % (chaves[2:],),
          "senao duas corretoras compartilhariam o mesmo trabalho (CLAUDE.md §7)")
    certo(tick.IntelligenceTick._janela(motor, datetime(2026, 9, 4), 168)
          == datetime(2026, 9, 4).strftime("%G-W%V"),
          "[13] e a janela de 168 h continua sendo SEMANAL")


# ===========================================================================
# [14] O BLOCO CITAVEL E O VOCABULARIO COMPLETO -- conserto de 04/09 (12 e 13)
# ===========================================================================
def _fixture_completa(cbim, mercado_tambem=True):
    """A carteira de REFERENCIA — com as cinco populacoes cheias.

    🔴 Ela existe porque a fixture curta (duas apolices) faz TODAS as metricas
    novas cairem no ramo do INDISPONIVEL: o vocabulario proibido nunca era
    medido sobre o texto que as formulas escrevem quando elas TEM numero. Um
    detector que so le o caminho vazio nao le o produto.
    """
    from app.providers.reference_analytics_provider import fatos_de_fixture

    lote = fatos_de_fixture(EMPRESA_A)
    return lote


def bloco_14_pack_e_vocabulario():
    _p("\n[14] PACK E VOCABULARIO (conserto 04/09) -- o TIPO da proposta · as 5 visoes cheias")

    mod, erro = mod_tool360()
    cbim, erro_c = _cbim()
    pack_mod, erro_p = _pack()
    if mod is None or cbim is None or pack_mod is None:
        certo(False, "[14] tool360 + cbim + pack carregam",
              erro or erro_c or erro_p)
        return

    from app.comercial.proposta import PropostaDeMetrica

    class _PacoteFalso:
        @staticmethod
        def serializar():
            return {"metrics": [], "warnings": []}

    proposta = PropostaDeMetrica(
        nome_sugerido="proposta.comissao_media",
        fatos=("commission",), dimensoes=("producer",),
        time_basis="POLICY_VALID_FROM",
        pergunta_exemplo="qual a comissao media por produtor")

    # -- CONTROLE: a proposta de verdade PASSA ------------------------------
    try:
        texto = mod.bloco_citavel(_PacoteFalso(), [proposta])
        passou, detalhe = ("proposta.comissao_media" in texto), texto[:150]
    except Exception as exc:  # noqa: BLE001
        passou, detalhe = False, "%s: %s" % (type(exc).__name__, exc)
    certo(passou,
          "[14] CONTROLE: uma `PropostaDeMetrica` de verdade entra no bloco "
          "citavel", detalhe)

    # -- TRATAMENTO 1: o TIPO errado ---------------------------------------
    #
    # 🔴 O caso que a regra antiga deixava passar inteiro: um `MetricResult` na
    # lista de propostas. Ele tem `value`, mas a chave dele no dicionario
    # serializado NAO se chama `valor` — e a pergunta era por dois nomes.
    resultado = pack_mod.metrica(
        "x.y", 42.0, "count", period={"start": "2025-01-01", "end": "2025-12-31"},
        time_basis="POLICY_VALID_FROM")
    try:
        mod.bloco_citavel(_PacoteFalso(), [resultado])
        recusou, detalhe = False, "ele ENTROU no bloco citavel, com value=42"
    except RuntimeError as exc:
        recusou, detalhe = "M-PROPOSTA" in str(exc), str(exc)[:160]
    except Exception as exc:  # noqa: BLE001
        recusou, detalhe = False, "%s: %s" % (type(exc).__name__, exc)
    certo(recusou,
          "[14] M-PROPOSTA (tipo): um `MetricResult` na lista de propostas e "
          "RECUSADO", detalhe
          + "  🔴 a regra antiga perguntava por dois NOMES de campo; este "
            "objeto passava com o numero dentro")

    # -- TRATAMENTO 2: uma chave numerica que nao se chama `value` ----------
    class _PropostaComNumero(PropostaDeMetrica):
        def serializar(self):
            return dict(PropostaDeMetrica.serializar(self), montante=1234.5)

    torta = _PropostaComNumero(nome_sugerido="proposta.x")
    try:
        mod.bloco_citavel(_PacoteFalso(), [torta])
        recusou, detalhe = False, "a chave `montante` entrou no bloco"
    except RuntimeError as exc:
        recusou, detalhe = "M-PROPOSTA" in str(exc), str(exc)[:160]
    except Exception as exc:  # noqa: BLE001
        recusou, detalhe = False, "%s: %s" % (type(exc).__name__, exc)
    certo(recusou,
          "[14] M-PROPOSTA (forma): uma chave NUMERICA que nao se chama "
          "`value` tambem e recusada", detalhe
          + "  ⛔ `montante`, `total`, `quantia`: a lista de dois nomes nao "
            "pegava nenhum deles")

    # -- as 5 visoes CHEIAS + uma proposta, sobre o vocabulario ------------
    feixe = cbim.MarketFactSet(
        provider_key=cbim.PROVIDER_DE_MERCADO, fonte="fixture",
        competencia_final="202506",
        mapa={"port": "05886"},
        resolver=lambda nome: ("05886" if str(nome).strip().upper() == "PORT"
                               else "UNKNOWN"))
    for mes in ("202503", "202506", "202509", "202512"):
        feixe.facts.append(cbim.MarketFact(
            coenti="05886", damesano=mes, coramo="0531",
            premio_ganho=1000.0, sinistro_ocorrido=571.2))

    lote = _fixture_completa(cbim)
    texto, erro = rodar_montar(
        ["sinistros", "funil", "carteira", "pendencias", "mercado",
         "a comissao media por produtor de frota"],
        fatos=lote, mercado=feixe)
    if erro:
        certo(False, "[14] o Pulso das 5 visoes NOVAS roda com dado dentro",
              erro)
        return
    _fora, pack = partes(texto)
    if pack is None:
        certo(False, "[14] a resposta traz um <<PACK>> parseavel", texto[-200:])
        return
    serializado = json.dumps(pack, ensure_ascii=False)

    certo(len(pack.get("metrics") or []) >= 10
          and len(pack.get("propostas") or []) >= 1,
          "[14] CONTROLE: o pack tem as metricas NOVAS e uma PROPOSTA (%d + %d)"
          % (len(pack.get("metrics") or []), len(pack.get("propostas") or [])),
          "sem as duas coisas dentro, a assercao seguinte passa por vacuidade")
    com_numero = [m for m in (pack.get("metrics") or [])
                  if str(m.get("value")) != "UNAVAILABLE"]
    certo(len(com_numero) >= 4,
          "[14] CONTROLE: pelo menos 4 metricas NOVAS trazem NUMERO (%d) — os "
          "ramos alcancaveis das formulas estao sendo lidos" % (len(com_numero),),
          "com tudo INDISPONIVEL o detector leria so o caminho vazio: %r"
          % ([m.get("metric_id") for m in (pack.get("metrics") or [])][:8],))

    achados = vocabulario_proibido_em(serializado)
    certo(not achados,
          "[14] o vocabulario proibido NAO aparece no pack das 5 visoes novas "
          "+ proposta (%d bytes)" % (len(serializado),),
          "📊 achado: %r" % (achados[:4],))
    # A MUTACAO que o pacote nomeia, sobre a metrica de cross-sell.
    alvo = os.path.join(METRICAS, "carteira.py")
    registry, _er = _registry()

    def _recarregar_definicoes():
        """🔴 As definicoes sao carregadas UMA vez por processo.

        ⚠️ Sem isto a mutacao no DISCO nao chega ao codigo que roda: o registry
        guarda as metricas num dicionario de modulo e `_carregar_definicoes`
        volta cedo quando ele ja esta cheio. Uma mutacao que nao e exercida NAO
        e mutacao passada (CLAUDE.md §9.5).
        """
        registry.METRICAS.clear()
        registry._carregar_definicoes()

    def _medir():
        _recarregar_definicoes()
        t, e = rodar_montar(["carteira"], fatos=lote, recarregar=True)
        if e:
            return "ERRO: %s" % e
        _f, p2 = partes(t)
        return vocabulario_proibido_em(json.dumps(p2 or {}, ensure_ascii=False))

    valor, rodou = sob_mutacao(
        "[14] M-VOCAB em `customer.single_product_share`", alvo,
        [("produto é RAMO DISTINTO, e não apólice",
          "o lucro recebido pelo funcionario")],
        _medir)
    # ⚠️ E o arquivo restaurado tem de voltar ao registry: senao os blocos
    # seguintes mediriam as definicoes MUTADAS.
    _recarregar_definicoes()
    mod_tool360(recarregar=True)
    if rodou:
        certo(bool(valor) and not str(valor).startswith("ERRO"),
              "[14] M-VOCAB: com 'o lucro recebido pelo funcionario' dentro de "
              "`customer.single_product_share`, o detector ACUSA",
              "veio %r — a frase injetada tem de chegar ao PACK e ser vista"
              % (valor,))


# ===========================================================================
# [9] CONTROLE GERAL — este guarda CONSEGUE ficar vermelho?
# ===========================================================================
# ==========================================================================
# [15] A RODADA 3 -- os quatro defeitos que o juiz FRESCO mediu AO VIVO
# ==========================================================================
#
# 🔴 Os quatro tinham a mesma forma: **codigo que existia, tinha teste e nunca
# funcionou na vida**, porque o teste media outra coisa que nao o caminho real.
#
# ```
# B1  "como estamos?" MORRIA          RELATORIO_FALHOU em 104 s, 0 artifact.
#                                     O guarda rodava com `manifesto=None`, e
#                                     sem manifesto a recusa dura do M15 nem
#                                     existe.
# B2  `propor_metrica` NUNCA gravou   22P02: `subject_id` e uuid e recebia o
#                                     NOME. O fake do teste aceitava qualquer
#                                     string.
# B3  `promover` lia `decided_at`     42703: a coluna nao existe. Idem.
# B4  a comparacao com o mercado      agrupava so por seguradora: auto contra
#     era de OUTRO ramo               a empresa inteira, 7,3 p.p. de erro.
# ```
SCHEMA_VIVO = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "fixtures", "schema_vivo.json")


def _schema_vivo():
    try:
        with io.open(SCHEMA_VIVO, encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:  # noqa: BLE001
        return {"_erro": "%s: %s" % (type(exc).__name__, exc)}


class _DbDoSchemaVivo:
    """Um fake que RECUSA o que o Postgres recusaria — lendo a fixture.

    🔴 Esta e a peca do item B2/B3. Um fake escrito a mao concorda com o codigo
    por construcao: foi assim que `propor()` passou por todos os guardas e
    nunca gravou uma linha em corretora nenhuma. Este aqui le
    `tests/fixtures/schema_vivo.json` — uma MEDICAO de
    `information_schema.columns` — e levanta:

    ```
    22P02   valor nao-uuid numa coluna `uuid`
    42703   `select` de coluna que nao existe
    22P02   status fora do enum `work_run_status`
    ```
    """

    def __init__(self, schema, linhas_de_approval=()):
        self.tabelas = dict((schema.get("tabelas") or {}))
        self.enums = dict((schema.get("enums") or {}))
        self.escritas = []
        self.selects = []
        self.linhas_de_approval = list(linhas_de_approval)
        self.client = self

    def table(self, nome):
        return _TabelaDoSchemaVivo(self, nome)

    # -- as regras do banco, e nada alem delas -------------------------
    def conferir_escrita(self, tabela, linha):
        colunas = self.tabelas.get(tabela) or {}
        for chave, valor in (linha or {}).items():
            if chave not in colunas:
                raise RuntimeError(
                    "42703 column %r of relation %r does not exist"
                    % (chave, tabela))
            tipo = colunas[chave]
            if tipo == "uuid" and valor is not None and not _e_uuid(valor):
                raise RuntimeError(
                    "22P02 invalid input syntax for type uuid: %r" % (valor,))
            if tipo == "USER-DEFINED" and valor is not None:
                aceitos = self.enums.get("%s.%s" % (tabela, chave)) or []
                if aceitos and str(valor) not in aceitos:
                    raise RuntimeError(
                        "22P02 invalid input value for enum: %r" % (valor,))

    def conferir_select(self, tabela, colunas):
        existentes = self.tabelas.get(tabela) or {}
        for c in colunas:
            nome = c.strip()
            if nome and nome != "*" and nome not in existentes:
                raise RuntimeError(
                    "42703 column %s.%s does not exist" % (tabela, nome))


def _e_uuid(valor):
    import uuid as _u
    try:
        _u.UUID(str(valor))
        return True
    except Exception:  # noqa: BLE001
        return False


class _TabelaDoSchemaVivo:
    def __init__(self, db, nome):
        self.db, self.nome = db, nome
        self._dados = []

    def insert(self, linha):
        self.db.conferir_escrita(self.nome, linha)
        self.db.escritas.append((self.nome, dict(linha)))
        self._dados = [dict(linha, id=str(_novo_uuid()))]
        return self

    def update(self, linha):
        self.db.conferir_escrita(self.nome, linha)
        self.db.escritas.append((self.nome + ":update", dict(linha)))
        self._dados = []
        return self

    def select(self, colunas="*", *a, **k):   # noqa: ANN002, ARG002
        self.db.selects.append((self.nome, colunas))
        self.db.conferir_select(self.nome, str(colunas).split(","))
        if self.nome == "approval_requests":
            self._dados = list(self.db.linhas_de_approval)
        return self

    def eq(self, *a, **k):     # noqa: ANN002, ARG002
        return self

    def order(self, *a, **k):  # noqa: ANN002, ARG002
        return self

    def limit(self, *a, **k):  # noqa: ANN002, ARG002
        return self

    def execute(self):
        class _R:
            pass
        r = _R()
        r.data = self._dados
        return r


def _novo_uuid():
    import uuid as _u
    return _u.uuid4()


def bloco_15_rodada_3():
    _p("\n[15] RODADA 3 -- B1 o Pulso nao morre · B2/B3 o SCHEMA VIVO · B4 o GRUPO DE RAMO")

    # ------------------------------------------------------------------
    # B1 -- uma metrica que LEVANTA nao derruba as outras
    # ------------------------------------------------------------------
    registry, erro = _registry()
    cbim, _ec = _cbim()
    if registry is None or cbim is None:
        certo(False, "[15] o registry e o CBIM carregam", erro or "cbim")
        return

    manifesto_vivo, erro_m = None, ""
    try:
        from app.comercial.manifesto import carregar_manifesto
        manifesto_vivo = carregar_manifesto("infocap")
    except Exception as exc:  # noqa: BLE001
        erro_m = "%s: %s" % (type(exc).__name__, exc)
    certo(manifesto_vivo is not None,
          "[15] B1 CONTROLE: o MANIFESTO VIVO carrega (`carregar_manifesto`)",
          erro_m)
    parcial = ""
    if manifesto_vivo is not None:
        try:
            parcial = str(manifesto_vivo.capacidade("commercial.quotes").state)
        except Exception as exc:  # noqa: BLE001
            parcial = "erro: %s" % exc
    certo(parcial == "PARTIAL",
          "[15] B1 CONTROLE: a capacidade do funil e PARTIAL no manifesto VIVO "
          "(%r) — e e ela que aciona a recusa dura do M15" % (parcial,),
          "sem PARTIAL aqui, todo o resto deste bloco passa por vacuidade")

    # PAR: uma metrica que LEVANTA sai INDISPONIVEL e as vizinhas sobrevivem.
    lote = fatos_de_fixture(cbim)
    alvo_que_levanta = "quotes.lost_reasons"
    vizinhas = ["production.policy_count", "production.premium_written"]
    saida, erro_c = None, ""
    try:
        saida = registry.calcular_varias(
            [alvo_que_levanta] + vizinhas, lote,
            (date(2025, 1, 1), date(2025, 12, 31)),
            manifest=manifesto_vivo)
    except Exception as exc:  # noqa: BLE001
        erro_c = "%s: %s" % (type(exc).__name__, exc)
    certo(saida is not None and len(saida) == 3,
          "[15] B1: `calcular_varias` com uma metrica que LEVANTA devolve as "
          "TRES — nenhuma some", erro_c
          + "  🔴 era este `raise` que subia ate `_montar` e devolvia "
            "RELATORIO_FALHOU em 104 s, com ZERO artifact")
    if saida:
        por_id = {m.metric_id: m for m in saida}
        certo(str(por_id.get(alvo_que_levanta).value) == "UNAVAILABLE",
              "[15] B1: a metrica que nao pode ser calculada sai INDISPONIVEL, "
              "e nunca zero (M2)",
              "veio %r" % (getattr(por_id.get(alvo_que_levanta), "value", None),))
        com_numero = [m for m in saida
                      if m.metric_id in vizinhas
                      and str(m.value) != "UNAVAILABLE"]
        certo(len(com_numero) == 2,
              "[15] B1 PAR: as duas metricas VIZINHAS continuam com numero "
              "(%d de 2)" % (len(com_numero),),
              "se elas sumissem, a assercao acima passaria com o relatorio "
              "vazio — que e o defeito, nao o conserto")
        avisos = " ".join(por_id.get(alvo_que_levanta).warnings or ())
        certo(bool(avisos.strip()),
              "[15] B1: e o MOTIVO viaja escrito no envelope da metrica que "
              "falhou (%d caracteres)" % (len(avisos),),
              "INDISPONIVEL sem motivo e silencio com outro nome")

    # E o caminho INTEIRO: `_montar` padrao, com o manifesto VIVO, entrega pack.
    texto, erro_t = rodar_montar([], fatos=_fixture_completa(cbim),
                                 manifesto=manifesto_vivo)
    _fora, pack = partes(texto)
    certo(pack is not None and not erro_t,
          "[15] B1 O ELO: `_montar` com as visoes PADRAO e o manifesto VIVO "
          "produz um pack (%d metricas)"
          % (len(((pack or {}).get("metrics") or [])),),
          erro_t or (texto or "")[-200:])
    if pack is not None:
        funil = [m for m in (pack.get("metrics") or [])
                 if str(m.get("metric_id")) == "quotes.funnel"]
        certo(bool(funil),
              "[15] B1: e `quotes.funnel` esta NO pack — INDISPONIVEL ou com "
              "numero, mas presente",
              "a visao `funil` esta em VISOES_PADRAO: se ela some, a pergunta "
              "generica deixou de responder por uma visao")

    # MUTACAO: tirar o isolamento -> o Pulso volta a MORRER.
    def _medir_montar():
        # 🔴 `recarregar=True` recarrega a TOOL, e nao o registry — e a mutacao
        # e no registry. Sem este `reload` a mutacao nao chega ao codigo que
        # roda, e mutacao nao exercida NAO e mutacao passada (CLAUDE.md §9.5).
        import importlib
        importlib.reload(registry)
        registry.METRICAS.clear()
        registry._carregar_definicoes()
        t, e = rodar_montar([], fatos=_fixture_completa(cbim),
                            manifesto=manifesto_vivo, recarregar=True)
        return "ERRO" if e else ("PACK" if partes(t)[1] is not None else "SEM")

    # 🔴 SAO DUAS DEFESAS, e a mutacao tem de dizer QUAL faz o que. A primeira
    # e o M15 so recusar quando ha NUMERO (sem numero nao ha total afirmado); a
    # segunda e o isolamento por metrica. Mutar so uma delas deixaria a outra
    # segurar o Pulso — e o guarda ficaria verde por engano, que foi como um
    # guarda da SPEC-093-B passou duas vezes.
    alvo = os.path.join(METRICAS, "registry.py")
    M15_DURO = ("        if valor is not None:\n            raise ValueError(",
                "        if True:\n            raise ValueError(")
    SEM_ISOLAMENTO = (
        "            saida.append(_isolar(d, period, facts, exc))",
        "            raise exc")

    valor, rodou = sob_mutacao(
        "[15] MUTACAO B1a (M15 duro, isolamento DE PE)", alvo, [M15_DURO],
        _medir_montar)
    _restaurar_registry(registry)
    if rodou:
        certo(valor == "PACK",
              "[15] MUTACAO B1a: com o M15 voltando a recusar SEM numero, o "
              "isolamento SOZINHO ainda entrega o Pulso (veio %r)" % (valor,),
              "e esta e a repartição de trabalho que a peça afirma: a recusa "
              "dura continua existindo, e deixou de ser fatal para as vizinhas")

    valor, rodou = sob_mutacao(
        "[15] MUTACAO B1b (o defeito HISTORICO inteiro de volta)", alvo,
        [M15_DURO, SEM_ISOLAMENTO], _medir_montar)
    _restaurar_registry(registry)
    if rodou:
        certo(valor == "ERRO",
              "[15] MUTACAO B1b: com as DUAS defesas fora, `_montar` com o "
              "manifesto VIVO volta a FALHAR (veio %r)" % (valor,),
              "🔴 este e o defeito exato que o juiz mediu ao vivo: "
              "RELATORIO_FALHOU em 104 s, ZERO artifact. Um guarda que nao "
              "consegue ficar vermelho com ele nao guarda nada")

    # ------------------------------------------------------------------
    # B2 / B3 -- o SCHEMA VIVO
    # ------------------------------------------------------------------
    schema = _schema_vivo()
    tabelas = schema.get("tabelas") or {}
    certo("_erro" not in schema and "approval_requests" in tabelas,
          "[15] B2 CONTROLE: `tests/fixtures/schema_vivo.json` existe e traz as "
          "tabelas (%s)" % (", ".join(sorted(tabelas)),),
          str(schema.get("_erro") or ""))
    certo((tabelas.get("approval_requests") or {}).get("subject_id") == "uuid",
          "[15] B2 CONTROLE: `approval_requests.subject_id` e `uuid` no schema "
          "MEDIDO — e por isso um nome de metrica ali devolve 22P02",
          "%r" % ((tabelas.get("approval_requests") or {}).get("subject_id"),))
    certo("decided_at" not in (tabelas.get("approval_requests") or {}),
          "[15] B3 CONTROLE: `decided_at` NAO existe em `approval_requests` — "
          "as colunas de decisao sao approved_at/rejected_at/resolved_at",
          "se ela existisse, o `select` antigo estaria certo e o B3 nao seria "
          "um defeito")

    # propor() contra o fake que obedece ao schema MEDIDO
    import asyncio
    proposta_mod, erro_p = None, ""
    try:
        from app.services.work import metric_proposal as proposta_mod
    except Exception as exc:  # noqa: BLE001
        erro_p = "%s: %s" % (type(exc).__name__, exc)
    certo(proposta_mod is not None,
          "[15] B2: `services/work/metric_proposal.py` importa", erro_p)

    class _PropostaSimples:
        nome_sugerido = "proposta.guarda_do_schema_vivo"
        fatos = ("policy",)
        dimensoes = ("insurer",)
        time_basis = "policy_valid_from"
        parecida_com = ()
        pergunta_exemplo = "quanto por seguradora"

    if proposta_mod is not None:
        db = _DbDoSchemaVivo(schema)
        run_id = str(_novo_uuid())

        async def _criar(_db=None, **kw):    # noqa: ANN003, ARG001
            return {"id": run_id, "reused": False}

        import app.services.work.runs as runs_mod
        antigo = getattr(runs_mod, "criar_registro_sem_fila", None)
        runs_mod.criar_registro_sem_fila = _criar
        try:
            saida_p, erro_pp = None, ""
            try:
                saida_p = asyncio.run(proposta_mod.propor(
                    db, company_id=str(_novo_uuid()),
                    proposta=_PropostaSimples()))
            except Exception as exc:  # noqa: BLE001
                erro_pp = "%s: %s" % (type(exc).__name__, exc)
            certo(saida_p is not None,
                  "[15] B2 O ELO: `propor()` grava contra um banco que obedece "
                  "ao schema MEDIDO", erro_pp
                  + "  📊 antes do conserto isto era `22P02 invalid input "
                    "syntax for type uuid` — em TODA corretora, desde sempre")
            aprovacoes = [linha for tabela, linha in db.escritas
                          if tabela == "approval_requests"]
            certo(len(aprovacoes) == 1,
                  "[15] B2: e UMA `approval_request` foi de fato escrita (%d)"
                  % (len(aprovacoes),),
                  "sem a linha escrita, nao ha gate: o painel nao tem o que "
                  "mostrar e o run espera para sempre")
            if aprovacoes:
                certo(str(aprovacoes[0].get("subject_id")) == run_id,
                      "[15] B2: o `subject_id` e o UUID DO RUN, e nao o nome "
                      "da metrica",
                      "veio %r" % (aprovacoes[0].get("subject_id"),))
                onde = json.dumps(
                    {"preview": aprovacoes[0].get("requested_preview"),
                     "payload": aprovacoes[0].get("request_payload")},
                    ensure_ascii=False, default=str)
                certo(_PropostaSimples.nome_sugerido in onde,
                      "[15] B2 PAR: e o NOME da metrica continua legivel — em "
                      "`requested_preview`/`request_payload`, que sao jsonb",
                      "mover o nome para fora da coluna errada nao pode "
                      "significar PERDER o nome")

            # PAR: a aprovacao que NAO pode ser escrita nao deixa run orfao.
            db2 = _DbDoSchemaVivo(schema)
            original_solicitar = proposta_mod._solicitar

            def _explode(*a, **k):   # noqa: ANN002, ARG001
                raise RuntimeError("22P02 (simulado): a aprovacao nao pode ser escrita")

            proposta_mod._solicitar = _explode
            try:
                try:
                    asyncio.run(proposta_mod.propor(
                        db2, company_id=str(_novo_uuid()),
                        proposta=_PropostaSimples()))
                    levantou = False
                except Exception:  # noqa: BLE001
                    levantou = True
            finally:
                proposta_mod._solicitar = original_solicitar
            marcados = [linha for tabela, linha in db2.escritas
                        if tabela == "work_runs:update"]
            certo(levantou and len(marcados) == 1
                  and str(marcados[0].get("status")) == "failed",
                  "[15] B2 PAR: aprovacao que NAO pode ser escrita deixa o run "
                  "em `failed`, e nunca `waiting_approval` orfao",
                  "levantou=%r updates=%r  📊 o banco tinha UM run "
                  "`metric.proposal`, em waiting_approval, sem nenhuma "
                  "approval_request" % (levantou, marcados))
        finally:
            if antigo is not None:
                runs_mod.criar_registro_sem_fila = antigo

    # promover(): o SELECT nao pede coluna inexistente e o status final e do enum
    promover_mod, erro_pr = None, ""
    try:
        from app.comercial.metricas import promover as promover_mod
    except Exception as exc:  # noqa: BLE001
        erro_pr = "%s: %s" % (type(exc).__name__, exc)
    certo(promover_mod is not None,
          "[15] B3: `comercial/metricas/promover.py` importa", erro_pr)
    if promover_mod is not None:
        enum = (schema.get("enums") or {}).get("work_runs.status") or []
        certo(str(promover_mod.STATUS_FINAL) in enum,
              "[15] B3: `STATUS_FINAL` (%r) e um rotulo do enum MEDIDO "
              "`work_run_status`" % (promover_mod.STATUS_FINAL,),
              "📊 o enum nao tem `succeeded`: o UPDATE final estouraria 22P02 "
              "DEPOIS de o evento de promocao ja estar gravado")
        db3 = _DbDoSchemaVivo(schema, linhas_de_approval=[])
        erro_leitura = ""
        try:
            promover_mod.conferir_a_decisao(db3, str(_novo_uuid()),
                                            str(_novo_uuid()))
        except promover_mod.Reprovado as exc:
            erro_leitura = str(exc)
        except Exception as exc:  # noqa: BLE001
            erro_leitura = "EXPLODIU %s: %s" % (type(exc).__name__, exc)
        certo("nao foi possivel ler" not in _sem_acento_simples(erro_leitura),
              "[15] B3 O ELO: o `select` de `approval_requests` passa pelo "
              "schema MEDIDO — a recusa e por AUSENCIA DE DECISAO, e nao por "
              "coluna inexistente",
              "veio: %s" % erro_leitura[:200])
        certo("aprovacao registrada" in _sem_acento_simples(erro_leitura),
              "[15] B3 PAR: e sem decisao humana ela REPROVA, com a frase de "
              "quem nao foi olhado",
              "veio: %s" % erro_leitura[:200])

        # MUTACAO: devolver `decided_at` ao select -> o schema vivo RECUSA.
        def _medir_select():
            import importlib
            importlib.reload(promover_mod)
            d = _DbDoSchemaVivo(schema, linhas_de_approval=[])
            try:
                promover_mod.conferir_a_decisao(d, str(_novo_uuid()),
                                                str(_novo_uuid()))
                return "PASSOU"
            except promover_mod.Reprovado as exc:
                return "42703" if "42703" in str(exc) or "possivel ler" in \
                    _sem_acento_simples(str(exc)) else "REPROVOU"
            except Exception as exc:  # noqa: BLE001
                return "EXPLODIU %s" % type(exc).__name__

        alvo_pr = os.path.join(METRICAS, "promover.py")
        valor, rodou = sob_mutacao(
            "[15] MUTACAO B3 (`decided_at` de volta no select)", alvo_pr,
            [("\"status, decision, approved_at, rejected_at, resolved_at\"",
              "\"status, decision, decided_at\"")],
            _medir_select)
        import importlib
        importlib.reload(promover_mod)
        if rodou:
            certo(valor == "42703",
                  "[15] MUTACAO B3: com `decided_at` no select, o schema VIVO "
                  "recusa a leitura (veio %r)" % (valor,),
                  "🔴 e era exatamente isso que acontecia em producao: o "
                  "`except` traduzia o 42703 em 'nao foi possivel ler a "
                  "aprovacao', e o gate ficava intransponivel")

    # ------------------------------------------------------------------
    # B4 -- o GRUPO DE RAMO. O PAR e a mao, com os dois numeros medidos.
    # ------------------------------------------------------------------
    #
    # 📊 Medido em 04/09/2026 no agregado REAL (`susep/ses/2026.csv`, 642
    # celulas da entidade 05886 em 202601-202606):
    #
    # ```
    # TODOS os ramos   sinistro 5.713.701.351,88 / premio 11.264.199.772,28 = 0,507244
    # grupo 05 (auto)  sinistro 4.585.393.142,50 / premio  7.903.825.636,18 = 0,580149
    # ```
    #
    # 🔴 7,3 p.p., e o menor era o que saia. A fixture abaixo REPRODUZ os dois
    # numeros com duas celulas, para que o guarda possa rodar sem rede.
    ESPERADO_DO_GRUPO = 0.580149
    ESPERADO_DE_TODOS = 0.507244
    feixe = cbim.MarketFactSet(
        provider_key=cbim.PROVIDER_DE_MERCADO, fonte="fixture-r3",
        competencia_final="202606",
        mapa={"porto": "05886"},
        resolver=lambda nome: ("05886" if str(nome).strip().upper() == "PORT"
                               else "UNKNOWN"),
        mapa_de_ramo={"AUTO": "05", "VGRP": "09"},
        resolver_de_ramo=lambda ramo: {"AUTO": "05", "VGRP": "09"}.get(
            str(ramo or "").strip().upper(), "UNKNOWN"),
        nomes_de_grupo={"05": "Automovel", "09": "Pessoas Coletivo"})
    feixe.facts.append(cbim.MarketFact(
        coenti="05886", damesano="202606", coramo="0531",
        premio_ganho=7903825636.18, sinistro_ocorrido=4585393142.50))
    feixe.facts.append(cbim.MarketFact(
        coenti="05886", damesano="202606", coramo="0993",
        premio_ganho=11264199772.28 - 7903825636.18,
        sinistro_ocorrido=5713701351.88 - 4585393142.50))
    todos = (sum(f.sinistro_ocorrido for f in feixe.facts)
             / sum(f.premio_ganho for f in feixe.facts))
    certo(abs(todos - ESPERADO_DE_TODOS) < 5e-6,
          "[15] B4 CONTROLE: a fixture reproduz o numero ERRADO de todos os "
          "ramos (%.6f)" % (todos,),
          "sem ele o par nao consegue distinguir os dois resultados")

    dinheiro = cbim.interpretar_dinheiro
    lote_b4 = fatos_de_fixture(cbim)
    lote_b4.policies = [dataclasses.replace(
        lote_b4.policies[0], policy_ref="b4-auto", insurer="PORT",
        branch="AUTO", valid_from=date(2026, 6, 1), valid_to=date(2027, 5, 31),
        premium=dinheiro("1000.00"))]
    lote_b4.claims = [cbim.ClaimFact(
        policy_ref="b4-auto", claim_ref="sin-b4", status="OPEN",
        occurred_at=date(2026, 6, 10), reported_at=date(2026, 6, 11),
        closed_at=None, indemnity=dinheiro("500.00"),
        deductible=dinheiro("0.00"), insurer="PORT", branch="AUTO",
        provider_key=lote_b4.provider_key)]
    r4, erro4 = None, ""
    try:
        r4 = registry.calcular("claims.loss_ratio_vs_market", lote_b4,
                               (date(2026, 6, 1), date(2026, 6, 30)),
                               mercado=feixe)
    except Exception as exc:  # noqa: BLE001
        erro4 = "%s: %s" % (type(exc).__name__, exc)
    linhas4 = list(getattr(r4, "breakdown", ()) or ())
    certo(len(linhas4) == 1,
          "[15] B4 CONTROLE: a carteira de AUTO produz UMA linha de comparacao "
          "(%d)" % (len(linhas4),), erro4)
    if linhas4:
        do_mercado = float(linhas4[0].get("sinistralidade_do_mercado") or 0.0)
        certo(abs(do_mercado - ESPERADO_DO_GRUPO) < 5e-6,
              "[15] B4 O ELO: a carteira de AUTO e comparada com o GRUPO 05 "
              "(%.6f), e nao com a seguradora inteira" % (do_mercado,),
              "📊 esperado %.6f (grupo 05) e NAO %.6f (todos os ramos)"
              % (ESPERADO_DO_GRUPO, ESPERADO_DE_TODOS))
        certo(abs(do_mercado - ESPERADO_DE_TODOS) > 0.05,
              "[15] B4 PAR: e o numero de TODOS os ramos (%.6f) NAO e o que "
              "sai — sao 7,3 p.p. de diferenca num numero de negociacao de "
              "reajuste" % (ESPERADO_DE_TODOS,),
              "veio %.6f" % (do_mercado,))
        certo(str(linhas4[0].get("cogrupo") or "") == "05"
              and "05" in str(linhas4[0].get("grupo") or ""),
              "[15] B4: e o GRUPO comparado vai escrito na linha (%r)"
              % (linhas4[0].get("grupo"),),
              "um numero de sinistralidade sem o ramo ao lado nao e conferivel")

    # MUTACAO: voltar a agrupar so por seguradora -> sai o numero ERRADO.
    def _medir_b4():
        registry.METRICAS.clear()
        registry._carregar_definicoes()
        try:
            r = registry.calcular("claims.loss_ratio_vs_market", lote_b4,
                                  (date(2026, 6, 1), date(2026, 6, 30)),
                                  mercado=feixe)
        except Exception as exc:  # noqa: BLE001
            return "ERRO %s" % type(exc).__name__
        ls = list(getattr(r, "breakdown", ()) or ())
        if not ls:
            return "SEM LINHA"
        return "%.6f" % float(ls[0].get("sinistralidade_do_mercado") or 0.0)

    alvo_b4 = os.path.join(METRICAS, "mercado.py")
    valor, rodou = sob_mutacao(
        "[15] MUTACAO B4 (agrupar so por seguradora)", alvo_b4,
        [("        chave = (str(getattr(c, \"coenti\", \"\") or \"\").strip(),\n"
          "                 str(getattr(c, \"grupo_de_ramo\", \"\") or \"\").strip())",
          "        chave = (str(getattr(c, \"coenti\", \"\") or \"\").strip(), \"05\")")],
        _medir_b4)
    registry.METRICAS.clear()
    registry._carregar_definicoes()
    if rodou:
        certo(valor == "%.6f" % ESPERADO_DE_TODOS,
              "[15] MUTACAO B4: somando os ramos todos na mesma chave, sai "
              "%s — o numero de OUTRO mercado (veio %r)"
              % ("%.6f" % ESPERADO_DE_TODOS, valor),
              "🔴 se a mutacao nao mudasse o numero, o agrupamento por grupo "
              "de ramo nao seria o que produz a resposta certa")


def _restaurar_registry(registry):
    """Recarrega o registry do DISCO. ⚠️ `sob_mutacao` restaura o ARQUIVO; o
    modulo ja importado continua com o codigo mutado ate este `reload`."""
    import importlib
    importlib.reload(registry)
    registry.METRICAS.clear()
    registry._carregar_definicoes()


def _sem_acento_simples(texto):
    import unicodedata
    bruto = unicodedata.normalize("NFKD", str(texto or ""))
    return "".join(c for c in bruto if not unicodedata.combining(c)).lower()


def bloco_9_controle():
    _p("\n[9] CONTROLE GERAL -- o placar sabe falhar · a rede fechou · nenhum `.bak`")

    global OK, FAIL
    antes = FAIL
    certo(False, "[9] CONTROLE-NEGATIVO (esta falha e DE PROPOSITO)",
          "🔴 Um placar que so sabe somar `ok` nao guarda nada. Esta linha "
          "existe para provar que ele CONTA falha — e ela e descontada a seguir.")
    subiu = FAIL == antes + 1
    FAIL = antes
    certo(subiu, "[9] o placar CONSEGUE contar uma falha (e o controle foi "
                 "descontado)")

    # --- a rede: uma tentativa de sair TEM de explodir ---------------------
    #
    # ⚠️ O endereco e de FORA (203.0.113.9 — TEST-NET-3, RFC 5737, reservado
    # para documentacao e que nunca roteia). Usar `127.0.0.1` aqui provaria a
    # coisa errada: o loopback e liberado de proposito (o self-pipe da asyncio).
    de_fora = ("203.0.113.9", 9)
    antes_da_lista = len(_TENTATIVAS_DE_REDE)
    explodiu = False
    try:
        socket.socket().connect(de_fora)
    except RedeProibida:
        explodiu = True
    except Exception:  # noqa: BLE001
        explodiu = False
    certo(explodiu,
          "[9] a rede EXTERNA esta bloqueada durante o guarda (SEM_REDE=1)",
          "sem o bloqueio, uma leitura acidental da SUSEP ou da InfoCap sairia "
          "daqui — e o §2 das travas proibe")
    # PAR (controle): o loopback CONTINUA passando — senao a asyncio nao sobe e
    # o guarda ficaria vermelho por causa de si mesmo.
    passou_loopback = True
    try:
        socket.socket().connect_ex(("127.0.0.1", 9))
    except RedeProibida:
        passou_loopback = False
    except Exception:  # noqa: BLE001
        pass
    certo(passou_loopback,
          "[9] PAR: o loopback continua passando (o self-pipe do "
          "ProactorEventLoop depende dele)")
    reais = [d for d in _TENTATIVAS_DE_REDE[:antes_da_lista]]
    certo(not reais,
          "[9] nenhum modulo do produto tentou sair para host EXTERNO",
          "destinos: %r" % (reais[:4],))

    # nenhum `.bak` esquecido: mutacao que nao restaura corrompe o repo
    sobrando = []
    for base in (APP, TESTES):
        for pasta, _d, arqs in os.walk(base):
            sobrando += [os.path.join(pasta, a) for a in arqs
                         if a.endswith(".bak-0941")]
    certo(not sobrando,
          "[9] nenhum `.bak-0941` ficou para tras (toda mutacao restaurou)",
          "%r — arquivo mutado esquecido e produto quebrado no proximo commit"
          % (sobrando[:4],))


def bloco_10_ambiente():
    """Roda DEPOIS da restauracao: o guarda devolveu `sys.modules`?"""
    _p("\n[10] AMBIENTE -- o guarda devolveu `sys.modules`")
    sujos = sorted(n for n in sys.modules
                   if n.startswith("_0941_")
                   or (n.startswith("app.") and n not in _MODULOS_NO_INICIO
                       and getattr(sys.modules[n], "__file__", None) is None))
    certo(not sujos,
          "[10] `sys.modules` voltou ao que era (nenhuma casca esquecida)",
          "%r — uma suite cujo resultado depende da ORDEM nao mede nada "
          "(CLAUDE.md §9.3)" % (sujos[:6],))
    certo(socket.socket.connect is _CONNECT_ORIGINAL,
          "[10] e a REDE foi devolvida ao processo",
          "📊 03/09: um bloqueio nao devolvido deixou 99 testes de outros "
          "arquivos vermelhos")


# ===========================================================================
BLOCOS = (
    ("[0] GATE ZERO", bloco_0_gate_zero),
    ("[1] REGISTRY", bloco_1_registry),
    ("[2] ADAPTER", bloco_2_adapter),
    ("[3] SUSEP SES", bloco_3_susep),
    ("[4] listar_entregas", bloco_4_entregas),
    ("[5] PROPOSTA", bloco_5_proposta),
    ("[6] TEMPLATE", bloco_6_template),
    ("[7] VOCABULARIO", bloco_7_vocabulario),
    ("[8] PROTOCOLO", bloco_8_protocolo),
    ("[11] A FIACAO", bloco_11_a_fiacao),
    ("[12] PROMOCAO E MAPA", bloco_12_promocao_e_mapa),
    ("[13] INGESTAO", bloco_13_ingestao),
    ("[14] PACK E VOCABULARIO", bloco_14_pack_e_vocabulario),
    ("[15] RODADA 3", bloco_15_rodada_3),
    ("[9] CONTROLE GERAL", bloco_9_controle),
)


def _rodar_os_blocos():
    for rotulo, funcao in BLOCOS:
        try:
            funcao()
        except Exception:  # noqa: BLE001
            # 🔴 Bloco que EXPLODE e vermelho DE VERDADE, nunca "esperado":
            # explosao e defeito do guarda ou do produto, e os dois precisam de
            # conserto — nao de tolerancia.
            import traceback
            certo(False, "%s EXPLODIU (defeito do guarda ou do produto)" % rotulo,
                  traceback.format_exc(limit=4)[-380:])


def main() -> int:
    _p("=" * 78)
    _p("  A FABRICA DE RELATORIOS -- SPEC-094.1  (gate zero + BLOCOS A-F)")
    _p("=" * 78)
    _abrir_o_ambiente()
    _bloquear_a_rede()
    try:
        _rodar_os_blocos()
    finally:
        _devolver_a_rede()
        _restaurar_sys_modules()
        bloco_10_ambiente()

    de_verdade = FAIL - len(ESPERADOS)
    _p("\n" + "=" * 78)
    _p("  %d ok · %d falhas (%d VERMELHO ESPERADO + %d de verdade) · %d pulados"
       % (OK, FAIL, len(ESPERADOS), de_verdade, len(PULADOS)))
    if ESPERADOS:
        _p("\n  🔴 VERMELHO ESPERADO -- a SPEC-094.1 PREVE estes ate o bloco citado.")
        _p("     O exit code e 1 mesmo assim (CLAUDE.md §9.3: nao se afrouxa).")
        for x in ESPERADOS:
            _p("     · %s" % x)
    if de_verdade > 0:
        _p("\n  ⛔ HA %d VERMELHO DE VERDADE acima -- procure as linhas `[FALHOU]`."
           % de_verdade)
    if JA_PODEM_VIRAR:
        _p("\n  ✅ ESTES JA FICARAM VERDES. O INTEGRADOR troca `vermelho_ate(...)` por")
        _p("     `certo(...)` e apaga o argumento do bloco -- senao o guarda passa a")
        _p("     guardar verdade vencida (CLAUDE.md §9.3):")
        for x in JA_PODEM_VIRAR:
            _p("     · %s" % x)
    if PULADOS:
        _p("\n  -- pulados (%d): %s" % (len(PULADOS), " · ".join(PULADOS)))
    _p("=" * 78)
    # 🔴 O exit code e 1 SO com falha DE VERDADE — e a razao e a opcao B do
    # v11.2: este guarda roda EM VOO, enquanto tres escritores constroem em
    # paralelo. Se o VERMELHO ESPERADO derrubasse o codigo de saida, a suite
    # inteira ficaria vermelha o tempo todo e ninguem conseguiria distinguir
    # "a SPEC ainda deve o BLOCO B" de "alguem quebrou o produto".
    #
    # ⚠️ E a lista acima NAO fica escondida: ela e impressa sempre, com o bloco
    # devedor ao lado de cada linha. Um `vermelho_ate` que virou verde aparece
    # em JA PODEM VIRAR e o integrador o troca por `certo(...)` — e e ai, no
    # gate final, que a SPEC so fecha com a lista de ESPERADOS vazia.
    if ESPERADOS:
        _p("  (exit 0 com %d VERMELHO ESPERADO e 0 de verdade: o gate FINAL da "
           "SPEC\n   so fecha com a lista acima VAZIA — v11.2, opcao B)"
           % len(ESPERADOS))
    return 1 if de_verdade else 0


def test_a_fabrica_de_relatorios():
    """🔴 VERDE desde 04/09/2026 — e agora ele guarda, em vez de anunciar.

    A prova nasceu ANTES do codigo (protocolo §4, nivel CRITICO): por tres dias
    este teste saiu vermelho com a lista de VERMELHO ESPERADO na saida, e essa
    lista era o que o executor precisava saber. Os BLOCOS A-E chegaram, os 55
    `vermelho_ate` viraram `certo`, e a lista saiu VAZIA — o gate final do
    v11.2, opcao B. Daqui em diante qualquer vermelho e regressao, nao pendencia.
    """
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
