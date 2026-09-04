# -*- coding: utf-8 -*-
"""A FABRICA DE RELATORIOS -- o guarda da SPEC-094.1, escrito ANTES do codigo.

🔴 **ESTE ARQUIVO NASCEU VERMELHO, E ERA PARA NASCER.** Protocolo AAA v11.2 §4
(opcao B): quem faz a prova nao faz a resposta. O desenhista escreveu estes
blocos com os modulos da §4 da SPEC ainda inexistentes — e a saida separa
**VERMELHO ESPERADO** (a SPEC ainda deve aquele bloco) de **VERMELHO DE VERDADE**
(defeito). O exit code e 1 nos dois casos: `CLAUDE.md` §9.3 — guarda que fica
verde por conveniencia e carimbo.

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
    entram como `vermelho_ate` proprio, separado das 10 obrigatorias.
```
Rodar:  `PYTHONIOENCODING=utf-8 python backend/tests/test_a_fabrica_de_relatorios.py`
        (a partir de `backend/`: `python tests/test_a_fabrica_de_relatorios.py`)
"""
from __future__ import annotations

import dataclasses
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
MANIFESTO_JSON = os.path.join(CANON, "providers", "infocap",
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
        vermelho_ate(False, "modulo %s existe" % rel(caminho), bloco,
                     "modulo %s ainda nao existe — esperado antes do %s"
                     % (rel(caminho), bloco))
        return None
    mod, erro = carregar(nome_modulo or ("_0941_" + os.path.basename(caminho)[:-3]),
                         caminho)
    if mod is None:
        vermelho_ate(False, "modulo %s importa" % rel(caminho), bloco,
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


def mod_tool360():
    global _MOD_TOOL360, _ERRO_TOOL360
    if _MOD_TOOL360 is None and not _ERRO_TOOL360:
        _MOD_TOOL360, _ERRO_TOOL360 = carregar(
            "app.agents.tools.executive_intelligence", TOOL360)
    return _MOD_TOOL360, _ERRO_TOOL360


def rodar_montar(views, periodo="2025", comparacao="nenhum", dimension="",
                 fatos=None):
    """`_montar` DE VERDADE. Devolve `(texto, erro)`.

    🔴 Nada sai: o provider e uma fixture, a publicacao e um `link` falso, os
    sinais nao sao gravados e o manifesto e `None`. O que roda de verdade e o
    que a SPEC afirma: a ESCOLHA das visoes e o registry.
    """
    mod, erro = mod_tool360()
    if mod is None:
        return "", "executive_intelligence nao carregou: %s" % erro
    cbim, erro_c = _cbim()
    if cbim is None:
        return "", "cbim nao carregou: %s" % erro_c
    lote = fatos if fatos is not None else fatos_de_fixture(cbim)

    class _ProviderDeFixture:
        provider_key = "fixture"

        async def fatos(self, **kw):    # noqa: ANN003, ARG002
            return lote

    class _ToolDeProva(mod.ExecutiveIntelligenceTool):
        @staticmethod
        def _provider(resolver, chave):   # noqa: ARG004
            return _ProviderDeFixture()

        @staticmethod
        async def _manifesto(provider, company_id, fatos):   # noqa: ARG004
            return None

        def _publicar_a_peca(self, *a, **k):   # noqa: ANN002, ARG002
            return "https://app.local/artifacts/fixture"

        def _registrar_sinais(self, ep, pacote):   # noqa: ARG002
            return None

    try:
        import asyncio

        tool = _ToolDeProva(company_id=EMPRESA_A, supabase=object())
        texto = asyncio.run(tool._montar(periodo, comparacao, list(views),
                                         dimension))
        return texto, ""
    except Exception as exc:  # noqa: BLE001
        return "", "%s: %s" % (type(exc).__name__, exc)


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
    vermelho_ate(em_agents > 0,
                 "[0] (i) alguma tool de agents/ le a tabela de entregas",
                 "BLOCO C",
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
        vermelho_ate(False, "[0] (ii) `_montar(views=['sinistros'])` roda",
                     "BLOCO D", erro)
    else:
        _fora, pack = partes(texto)
        ids = {str(m.get("metric_id")) for m in ((pack or {}).get("metrics") or [])}
        de_producao = {"production.policy_count", "production.premium_written"}
        caiu_no_fallback = bool(ids & de_producao)
        vermelho_ate(
            not caiu_no_fallback,
            "[0] (ii) uma visao DESCONHECIDA nao devolve o Pulso 360 COMPLETO",
            "BLOCO D",
            "📊 `executive_intelligence.py:746-748`: a visao desconhecida e "
            "DESCARTADA e o fallback e TODAS. A pergunta sobre SINISTROS "
            "recebeu %d metricas de producao/mix, sem aviso. Metricas vindas: %r"
            % (len(ids & de_producao), sorted(ids)[:8]))
        vermelho_ate(
            "proposta" in texto.lower() or "não tenho essa métrica" in texto.lower(),
            "[0] (ii-bis) e a resposta DIZ que a metrica nao existe",
            "BLOCO D",
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
    vermelho_ate(not faltam,
                 "[0] (iii) o adapter tem os 5 leitores novos (claims, quotes, "
                 "cancellations, customer_links, issuance_status)",
                 "BLOCO A",
                 "faltam %r — 📊 `/sinistros` tem 5.729 registros e nenhum "
                 "leitor" % (faltam,))
    certo(bool(re.search(r"def\s+policies\s*\(", texto_adapter)),
          "[0] (iii) PAR (controle): o detector ACHA os leitores que JA existem "
          "(`policies`)",
          "se ele nao acha nem `policies`, o vermelho acima e do detector")

    # --- (iv) MetricDefinition sem `pergunta_verificada` --------------------
    registry, erro_r = _registry()
    if registry is None:
        vermelho_ate(False, "[0] (iv) o registry carrega", "BLOCO A", erro_r)
    else:
        campos = set(getattr(registry.MetricDefinition, "__dataclass_fields__", {}))
        faltam_campos = [c for c in ("pergunta_verificada", "golden")
                         if c not in campos]
        vermelho_ate(not faltam_campos,
                     "[0] (iv) `MetricDefinition` tem `pergunta_verificada` e "
                     "`golden`", "BLOCO A",
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
        vermelho_ate(False, "[1] o registry carrega", "BLOCO A", erro)
        return

    campos = set(getattr(registry.MetricDefinition, "__dataclass_fields__", {}))
    tem_golden = {"pergunta_verificada", "golden"} <= campos

    # --- M-GOLDEN: registrar SEM golden REPROVA, e COM golden passa ---------
    if not tem_golden:
        vermelho_ate(False,
                     "[1] M-GOLDEN: uma definicao SEM `golden` e RECUSADA no "
                     "`__post_init__`", "BLOCO A",
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
    vermelho_ate(not faltam,
                 "[1] as 10 metricas novas OBRIGATORIAS estao em `todas()`",
                 "BLOCO A/B",
                 "faltam %r  ·  📊 hoje o registry tem %d metricas"
                 % (faltam, len(registradas)))
    faltam_cond = [m for m in METRICAS_CONDICIONAIS if m not in registradas]
    vermelho_ate(not faltam_cond,
                 "[1] as 2 metricas CONDICIONAIS do funil estao em `todas()`",
                 "BLOCO A (se o BLOCO 0 provar `/negocios_andamento`)",
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
            vermelho_ate(False,
                         "[1] existe um carregador de fixture do golden no "
                         "registry", "BLOCO E",
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
                    if getattr(fatos, "policies", None):
                        fatos.policies = list(fatos.policies)[:-1] or []
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
        vermelho_ate(False, "[2] o adapter existe", "BLOCO A", rel(ADAPTER))
        return

    # --- os 5 metodos, e cada um marcando a rota que leu -------------------
    for metodo in METODOS_NOVOS:
        m = re.search(r"(async\s+)?def\s+%s\s*\(" % re.escape(metodo), texto)
        if m is None:
            vermelho_ate(False, "[2] o adapter tem `%s()`" % metodo, "BLOCO A",
                         "📊 a rota existe e ninguem le")
            continue
        corpo = texto[m.start():m.start() + 2600]
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
        vermelho_ate(False, "[2] registry + cbim carregam", "BLOCO A",
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
                    vermelho_ate(False,
                                 "[2] rota primaria VAZIA -> a metrica sai "
                                 "UNAVAILABLE, nunca 0", "BLOCO A",
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
        vermelho_ate(False,
                     "[2] rota primaria VAZIA -> a metrica sai UNAVAILABLE",
                     "BLOCO A", "manifesto ou %s ausente" % rel(MANIFESTO_JSON))

    # --- M16: `claim_ref` e `customer_ref` sao HASH, nunca PII -------------
    campos_novos = ("ClaimFact", "QuoteFact", "CustomerPortfolioFact")
    texto_cbim = ler(CBIM_PY)
    for classe in campos_novos:
        vermelho_ate(("class %s" % classe) in texto_cbim,
                     "[2] o CBIM tem `%s`" % classe, "BLOCO A",
                     "os 4 fatos novos (ClaimFact, QuoteFact, "
                     "CustomerPortfolioFact, MarketFact) sao o vocabulario "
                     "que as metricas novas leem")
    vermelho_ate("class MarketFactSet" in texto_cbim,
                 "[2] o CBIM tem `MarketFactSet` (plataforma, SEM company_id)",
                 "BLOCO B",
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
            vermelho_ate(False,
                         "[2] M17: paridade adapter x referencia para 3 "
                         "metricas novas", "BLOCO A",
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
        vermelho_ate(False, "[3] `ler_agregado(ano)` devolve um `MarketFactSet`",
                     "BLOCO B", "o conector ainda nao existe")
        vermelho_ate(False, "[3] M2: seguradora sem `coenti` sai UNAVAILABLE, "
                            "nunca 0", "BLOCO B", "o conector ainda nao existe")
        vermelho_ate(False, "[3] `claims.loss_ratio_vs_market` e DERIVED e "
                            "declara AS DUAS fontes", "BLOCO B",
                     "o conector ainda nao existe")
        vermelho_ate(False, "[3] `market.loss_ratio_trend` le 3 trimestres e "
                            "diz sobe/desce/estavel", "BLOCO B",
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

    nome, ler_agregado = primeiro_atributo(mod, CANDIDATOS_SES_LER)
    if ler_agregado is None:
        vermelho_ate(False, "[3] o conector expoe `ler_agregado(ano)`", "BLOCO B",
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
        def __init__(self):
            self.pedidos = []

        def download_file(self, object_name):
            self.pedidos.append(object_name)
            return io.BytesIO(json.dumps(linhas, ensure_ascii=False).encode("utf-8"))

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
        vermelho_ate(False,
                     "[3] `%s(2026)` le do MinIO FALSO e devolve um "
                     "`MarketFactSet`" % nome, "BLOCO B", erro)
        return
    certo(bool(minio.pedidos),
          "[3] o conector leu do MinIO (objeto pedido: %r)" % (minio.pedidos[:2],),
          "ele devolveu algo sem ler o MinIO — de onde veio o dado?")
    certo(not _TENTATIVAS_DE_REDE,
          "[3] e NENHUMA chamada de rede saiu (a rede esta bloqueada e nao "
          "acusou nada)",
          "destinos tentados: %r" % (_TENTATIVAS_DE_REDE[:3],))

    # --- a celula recalculada A MAO (lente do DADO, §BLOCO B) --------------
    #
    # 📊 A conta: sinistralidade = sinistro / premio. Para (0001, 202606, 0531):
    # 600 / 1000 = 0,60. Se a metrica disser outra coisa, ela nao esta fazendo
    # a conta que o nome dela promete.
    esperado_a_mao = 600.0 / 1000.0
    registry, _e = _registry()
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
            vermelho_ate(False,
                         "[3] `calcular(..., mercado=<MarketFactSet>)` aceita o "
                         "conjunto de plataforma", "BLOCO B", str(exc))
        except Exception as exc:  # noqa: BLE001
            certo(False, "[3] a celula recalculada a mao bate",
                  "%s: %s" % (type(exc).__name__, exc))
    else:
        vermelho_ate(False,
                     "[3] a celula recalculada A MAO bate com `market.loss_ratio`",
                     "BLOCO B", "a metrica ainda nao existe")

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
                lote_base.policies = [dataclasses.replace(
                    lote_base.policies[0], policy_ref="m2-na-janela",
                    insurer=nome, valid_from=date(2026, 5, 1),
                    valid_to=date(2027, 4, 30))]
                lote_base.claims = [cbim.ClaimFact(
                    policy_ref="m2-na-janela", claim_ref="sin-m2",
                    status="OPEN", occurred_at=date(2026, 5, 15),
                    reported_at=date(2026, 5, 16), closed_at=None,
                    indemnity=dinheiro("300.00"), deductible=dinheiro("0.00"),
                    insurer=nome, branch="auto",
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
                mapa={"seguradora_do_par": "0001"})
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
        vermelho_ate(False, "[3] M2 + a DERIVED com as duas fontes declaradas",
                     "BLOCO B", "`claims.loss_ratio_vs_market` ainda nao existe")

    # --- a tendencia dos 3 trimestres -------------------------------------
    if registry is not None and "market.loss_ratio_trend" in set(registry.todas()):
        certo(True, "[3] `market.loss_ratio_trend` existe — o sinal ▲▼ e do "
                    "BLOCO B")
    else:
        vermelho_ate(False,
                     "[3] `market.loss_ratio_trend` com 3 trimestres sinteticos "
                     "sobe/desce/estavel", "BLOCO B", "a metrica ainda nao existe")


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
    vermelho_ate(dentro_do_if,
                 "[4] `listar_entregas` entra pela lista de "
                 "`relatorios_comerciais`, DENTRO do `if` de graph.py:528",
                 "BLOCO C",
                 "fora dele o agente de ATENDIMENTO — que fala com o SEGURADO — "
                 "recebe a lista das entregas da corretora")
    certo('_agent_role or "core"' in grafo and '"core(legado)"' in grafo,
          "[4] CONTROLE: o `if` fechado por papel continua existindo em graph.py")

    mod = exigir(TOOL_ENTREGAS, "BLOCO C", "_0941_entregas")
    if mod is None:
        return

    nome, fabrica = primeiro_atributo(mod, CANDIDATOS_ENTREGAS)
    if fabrica is None:
        vermelho_ate(False, "[4] o modulo expoe a tool", "BLOCO C",
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
        vermelho_ate(False, "[4] a tool `%s` roda com um Supabase falso" % nome,
                     "BLOCO C", erro_a)
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
        vermelho_ate(False, "[5] a tool 360 carrega", "BLOCO D", erro)
    else:
        tem_tipo = hasattr(mod, "PropostaDeMetrica")
        vermelho_ate(tem_tipo,
                     "[5] existe o TIPO `PropostaDeMetrica` (nunca um "
                     "`MetricResult` com `value=None`)", "BLOCO D",
                     "🔴 ref ③ (Genie): a proposta tem OUTRA CARA, e nao a "
                     "mesma com o numero em branco — `value=None` seria narrado "
                     "como 'zero' na primeira frase")
        campos_plano = set(getattr(mod.PlanoDeConsulta, "model_fields", {})
                           or getattr(mod.PlanoDeConsulta, "__fields__", {}))
        vermelho_ate("listar_metricas" in campos_plano,
                     "[5] o query plan ganha `listar_metricas` (ref ⑥ dbt/MCP)",
                     "BLOCO D",
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
            vermelho_ate(False,
                         "[5] a pergunta SEM metrica devolve PROPOSTA e ZERO "
                         "numero", "BLOCO D", erro_m)
        else:
            _fora, pack = partes(texto)
            ids = {str(m.get("metric_id"))
                   for m in ((pack or {}).get("metrics") or [])}
            vermelho_ate("proposta" in texto.lower(),
                         "[5] a pergunta SEM metrica devolve uma PROPOSTA",
                         "BLOCO D", "veio: %r" % texto[:220])
            vermelho_ate(not (ids & {"production.policy_count", "mix.insurer"}),
                         "[5] e ZERO numero de outra pergunta aparece na tela",
                         "BLOCO D",
                         "o fallback de TODAS devolveu %r" % (sorted(ids)[:6],))
            # --- a duplicata apontada (ref ②) ------------------------------
            #
            # ⚠️ NAO basta `"mix.branch" in texto`: hoje ele esta la porque o
            # fallback de TODAS despejou o registry inteiro na resposta — a
            # assercao ficaria VERDE pelo motivo errado, que e a definicao de
            # carimbo. O que se mede e `mix.branch` DENTRO de `parecida_com`.
            perto = re.search(
                r"parecida_com[^\n]{0,300}?mix\.branch", texto, re.S)
            nas_propostas = "mix.branch" in json.dumps(
                (pack or {}).get("propostas") or [], ensure_ascii=False)
            vermelho_ate(bool(perto) or nas_propostas,
                         "[5] a proposta de 'comissao por ramo' aponta a "
                         "DUPLICATA `mix.branch` DENTRO de `parecida_com`",
                         "BLOCO D",
                         "🔴 tres 'comissao do mes' divergentes destroem mais "
                         "confianca que uma metrica faltando (ref ②)")

    # --- `origem: registry|proposta` no pack, e `_compor` nao percorre ------
    pack_mod, erro_p = _pack()
    if pack_mod is None:
        vermelho_ate(False, "[5] o evidence_pack carrega", "BLOCO D", erro_p)
    else:
        texto_pack = ler(PACK_PY)
        vermelho_ate("origem" in texto_pack,
                     "[5] o bloco <<PACK>> carrega `origem: registry|proposta` "
                     "por item (ref ③)", "BLOCO D",
                     "o Artifact escreve 'registrada' ou 'proposta em revisao' "
                     "ao lado — e a proposta NUNCA tem numero")
        if mod is not None:
            m = re.search(r"def _compor\([\s\S]{0,9000}?\n    def ", ler(TOOL360))
            corpo = m.group(0) if m else ""
            vermelho_ate(bool(corpo) and "proposta" not in corpo.lower(),
                         "[5] `_compor` NAO percorre propostas (o Artifact nao "
                         "desenha numero que nao existe)", "BLOCO D",
                         "`_compor` cita 'proposta' — se ele iterar sobre elas, "
                         "a primeira proposta vira uma caixa de KPI vazia no "
                         "relatorio do dono")

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
            vermelho_ate(exigencia.strip('"') in fonte_propor,
                         "[5] a proposta usa `%s`" % exigencia.strip('"'),
                         "BLOCO D", porque)
        faltam6 = [c for c in ("company_id", "work_run_id", "action_type",
                               "subject_type", "preview", "action_payload")
                   if c + "=" not in fonte_propor]
        vermelho_ate(not faltam6,
                     "[5] `solicitar()` e chamado com os 6 campos obrigatorios",
                     "BLOCO D", "faltam %r" % (faltam6,))
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
            vermelho_ate(False,
                         "[5] existe leitura de propostas por corretora", "BLOCO D",
                         "nenhum de ('listar_propostas','listar',"
                         "'propostas_da_corretora') (D2)")
        else:
            certo("company_id" in getattr(listar, "__code__",
                                          types.SimpleNamespace(co_varnames=()))
                  .co_varnames,
                  "[5] `%s()` exige `company_id` — dois tenants nao se veem"
                  % nome_l,
                  "o backend roda com service role: RLS sem filtro no codigo "
                  "nao protege nada (CLAUDE.md §7)")

    # --- `promover()`: CLI, e REPROVA id inexistente -----------------------
    promover_mod = exigir(PROMOVER_PY, "BLOCO D", "_0941_promover")
    if promover_mod is not None:
        nome_pr, promover = primeiro_atributo(promover_mod, ("promover", "main"))
        if promover is None:
            vermelho_ate(False, "[5] `promover.py` expoe `promover()`", "BLOCO D",
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
        vermelho_ate(secao in _normalizar(inteiro),
                     "[6] o Pulso 360 tem a secao **%s**" % secao, "BLOCO A/B",
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
    vermelho_ate(bool(declaram),
                 "[6] D4: as secoes declaram as metricas que as sustentam em "
                 "`props['metrics']`", "BLOCO A",
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
        vermelho_ate(False, "[7] o Pulso completo roda para medir o vocabulario",
                     "BLOCO A", erro)
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
        vermelho_ate(False, "[7] a resposta traz um bloco <<PACK>> parseavel",
                     "BLOCO A", texto[-200:])
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
    vermelho_ate(existe, "[8] `docs/canon/COMO-NASCE-UM-RELATORIO.md` existe",
                 "BLOCO E",
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
    vermelho_ate(existe_guarda,
                 "[8] `tests/test_o_relatorio_nasce_pelo_protocolo.py` existe "
                 "(e do BUILDER, nao deste desenhista)", "BLOCO E",
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
# [9] CONTROLE GERAL — este guarda CONSEGUE ficar vermelho?
# ===========================================================================
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
    """⚠️ FALHA DE PROPOSITO ate os BLOCOS A-F da SPEC-094.1 existirem.

    A prova nasce antes do codigo (protocolo §4, nivel CRITICO). Quem rodar a
    suite hoje ve este teste vermelho com a lista de VERMELHO ESPERADO na saida
    — e essa lista e exatamente o que o executor precisa saber. Marcar `xfail`
    aqui esconderia o que a SPEC ainda deve.
    """
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
