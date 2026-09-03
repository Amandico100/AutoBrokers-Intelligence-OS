# -*- coding: utf-8 -*-
"""O CANÁRIO do Pulso 360 — SPEC-094 BLOCO G, o caminho COMPLETO em memória.

📊 A SPEC-081 entregou duas tools em 18/08/2026 e o canário das três corretoras
**nunca foi feito**: `select ... from artifacts` deu Resulta 28 (todos do dia
da própria SPEC), Amandus 0, AutoFleet 0. Um caminho que nunca foi percorrido
inteiro não é um caminho — é uma sequência de peças que passam nos seus
próprios testes.

Este arquivo percorre o caminho inteiro, sem tocar a rede e sem tocar o banco:

```
linha CRUA (golden controls do censo)
   -> HTTP falso, no lugar exato onde a `FonteInfocap` faz o GET
   -> adapter: resolver de conexão · gate de conta · tradução para CBIM
   -> Metric Registry: as métricas, com base temporal e cobertura
   -> Evidence Pack: findings determinísticos e `pack_id`
   -> a tool `executive_intelligence`: o bloco que o modelo lê
   -> ArtifactService FALSO: captura o payload
   -> o template `executive.pulse360`: os blocos RENDERIZAM
```

⛔ O que é falso, e só isto: a resposta HTTP (⛔ `SEM_REDE=1`), a decifragem da
credencial (o teste não tem chave, e não pode ter) e a publicação do Artifact
(⛔ nenhuma escrita no banco). Resolver, gate, tradução, cálculo, achado,
composição e renderização são os de produção.

⛔ NENHUM nome de pessoa. Os produtores das linhas cruas são `Produtor 000` a
`Produtor 096` — rótulos sintéticos que servem de SENTINELA: se um deles
aparecer no bloco que vai ao modelo, o teste sabe que o rótulo escapou.

🔴 E a AMANDUS não roda. 📊 O censo mediu que a conexão `connected` dela
descriptografa para a MESMA conta da Resulta — mesmo login, carteira idêntica
ao centavo (F-094-07). O canário dela é a RECUSA: se ela produzir um relatório,
o dono da Amandus está lendo a carteira da Resulta com o nome dele em cima.

Rodar:  PYTHONIOENCODING=utf-8 python backend/tests/test_o_canario_do_pulso_360.py
"""
from __future__ import annotations

import asyncio
import importlib.util
import io
import json
import os
import re
import socket
import sys
import types
from datetime import date, datetime

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(RAIZ)
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

os.environ["SEM_REDE"] = "1"
os.environ.setdefault("COMERCIAL_CACHE_TTL_S", "0")

PASS = FAIL = 0


def check(nome, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("\n         " + str(extra)[:400] if extra else ""))
    return bool(cond)


def _p(t):
    try:
        print(t)
    except UnicodeEncodeError:
        cod = getattr(sys.stdout, "encoding", None) or "ascii"
        print(t.encode(cod, "replace").decode(cod, "replace"))


# ===========================================================================
# ⛔ A REDE FECHA AQUI — e o fim do arquivo prova que ela fechou
# ===========================================================================
class RedeProibida(RuntimeError):
    """Uma chamada de rede tentou sair do canário."""


_CONNECT = socket.socket.connect
_CONNECT_EX = socket.socket.connect_ex


def _proibir(self, *a, **k):   # noqa: ANN001, ARG002
    raise RedeProibida("SPEC-094: o canario roda com SEM_REDE=1. Destino "
                       "pedido: %r" % (a[0] if a else None,))


def _fechar_a_rede():
    socket.socket.connect = _proibir        # type: ignore[assignment]
    socket.socket.connect_ex = _proibir     # type: ignore[assignment]


def _abrir_a_rede():
    socket.socket.connect = _CONNECT        # type: ignore[assignment]
    socket.socket.connect_ex = _CONNECT_EX  # type: ignore[assignment]


# ===========================================================================
# As cascas de pacote — `app/services/__init__.py` importa 14 serviços
# ===========================================================================
def _cascas():
    """📊 `app.services.__init__` puxa `fastembed`, que não está instalado aqui.

    A casca tem o `__path__` REAL: nenhum código nosso é falsificado — o que
    se evita é executar catorze `__init__` para ler dois módulos.
    """
    for nome, partes in (("app.services", ("app", "services")),
                         ("app.services.artifacts",
                          ("app", "services", "artifacts")),
                         ("app.services.intelligence",
                          ("app", "services", "intelligence")),
                         # 📊 `app.agents.__init__` importa o grafo, que puxa
                         # `langgraph`. O canário lê DUAS tools; carregar o
                         # grafo inteiro para isso faria o teste depender de
                         # uma dependência que ele não exercita.
                         ("app.agents", ("app", "agents")),
                         ("app.agents.tools", ("app", "agents", "tools")),
                         # 📊 `app.api.__init__` puxa `slowapi`. O resolver de
                         # conexão mora em `app/api/infocap_connector.py`, e
                         # ele é PRODUÇÃO — o que a casca evita é o `__init__`
                         # do pacote, não o módulo.
                         ("app.api", ("app", "api")),
                         ("app.core", ("app", "core")),
                         ("app.comercial", ("app", "comercial")),
                         ("app.comercial.metricas",
                          ("app", "comercial", "metricas")),
                         ("app.providers", ("app", "providers"))):
        atual = sys.modules.get(nome)
        if atual is not None and getattr(atual, "__file__", None) is None:
            continue
        casca = types.ModuleType(nome)
        casca.__path__ = [os.path.join(RAIZ, *partes)]
        casca.__package__ = nome
        sys.modules[nome] = casca


import app  # noqa: E402,F401
_cascas()


# ===========================================================================
# 📊 OS GOLDEN CONTROLS — `docs/canon/providers/infocap/infocap-golden-controls.json`
# ===========================================================================
#
# 🔴 Eles vêm do ARQUIVO, e não de constantes copiadas para cá. Número medido
# que alguém transcreve à mão envelhece na primeira remedição — e o teste
# passaria a guardar a cópia, não a medição (CLAUDE.md §12.1).
CENSO = os.path.join(REPO, "docs", "canon", "providers", "infocap")
GOLDEN = json.load(io.open(os.path.join(CENSO, "infocap-golden-controls.json"),
                           encoding="utf-8"))
#: 🔴 E a FORMA da linha crua também vem do censo, não da imaginação.
#: 📊 `impressao_da_rota` é o `sha256` das chaves ORDENADAS da primeira linha,
#: e o BLOCO C compara essa impressão com a medida — uma linha sintética com
#: as chaves "que fazem sentido" tem outra impressão, o manifesto marca DRIFT
#: e TODA métrica sai INDISPONÍVEL. Foi o que aconteceu na primeira rodada
#: deste canário, e o comportamento estava certo: era a fixture que mentia
#: sobre o formato (CLAUDE.md §9.4 — o dado do teste vem do acervo).
FINGERPRINTS = json.load(io.open(
    os.path.join(CENSO, "infocap-schema-fingerprints.json"), encoding="utf-8"))


def chaves_da_rota(rota):
    return list(FINGERPRINTS["rotas"][rota]["chaves_ordenadas"])


def _linha_completa(rota, valores):
    """A linha com TODAS as chaves da rota medida, na forma do censo."""
    linha = {k: "" for k in chaves_da_rota(rota)}
    desconhecidas = [k for k in valores if k not in linha]
    if desconhecidas:
        raise AssertionError(
            "a fixture inventou chave que o censo não mediu em %s: %r"
            % (rota, desconhecidas))
    linha.update(valores)
    return linha

EMPRESAS = {
    "resulta": "11111111-0000-0000-0000-00000000001a",
    "autofleet": "22222222-0000-0000-0000-00000000002a",
    "amandus": "33333333-0000-0000-0000-00000000003a",
}
#: 🔴 A Amandus e a Resulta compartilham o LOGIN. É o P1 do censo, e é o que o
#: gate de conta compartilhada tem de recusar (F-094-07).
LOGIN_DE_FIXTURE = {"resulta": "conta-alfa", "autofleet": "conta-beta",
                    "amandus": "conta-alfa"}


def controles(slug):
    return GOLDEN["corretoras"][slug]


def _centavos(total_centavos, n):
    base, resto = divmod(total_centavos, n)
    return [base + (1 if i < resto else 0) for i in range(n)]


def linhas_de_producao(slug):
    """As linhas CRUAS de `/documentos_bi`, com os totais do censo.

    ⚠️ Sintéticas, e os totais BATEM. É a linha de controle que dá direito à
    conclusão: uma carteira alterada em um centavo não bate (CLAUDE.md §9.2).
    """
    c = controles(slug)["documentos_bi_2025_tipo_A"]
    n = c["n_documentos_tipo_A"]
    comissoes = _centavos(int(round(c["soma_val_c"] * 100)), n)
    premios = _centavos(int(round(c["soma_pretot"] * 100)), n)
    renovadas = c["n_renovacao_nosnum_ren_preenchido"]
    seguradoras = c["seguradoras_distintas"]
    ramos = c["ramos_distintos"]
    saida = []
    for i in range(n):
        saida.append(_linha_completa("/documentos_bi", {
            "nosnum": "%s-DOC-%06d" % (slug, i),
            "nosnum_ren": ("%s-ANT-%06d" % (slug, i)) if i < renovadas else "",
            "seguradora": "SEG%02d" % (i % seguradoras),
            "ramo": "RAMO%02d" % (i % ramos),
            "inivig": date(2025, 1 + (i % 12), 1).strftime("%d/%m/%Y"),
            "fimvig": date(2026, 1 + (i % 12), 1).strftime("%d/%m/%Y"),
            "pretot": "%.2f" % (premios[i] / 100.0),
            "val_c": "%.2f" % (comissoes[i] / 100.0),
        }))
    return saida


#: 🔴 A PARIDADE QUE O BLOCO D EXIGE, e o numero e medido.
#:
#: 📊 `fonte_infocap.anos_de_vencimento_para` varre de N-1 a N+2 porque isso
#: deu **80,6%** de cobertura de produtor em 2025 na API viva -- contra 2,8% se
#: se pedisse um ano so. E o motivo e geometrico, nao estatistico: apolice anual
#: que COMECA em 2025 TERMINA em 2026, e `/renovacoes` filtra por `fimvig`. A
#: intersecao de 2025x2025 e um ARTEFATO da janela, e nao uma propriedade da
#: carteira.
PARIDADE_DE_COBERTURA = 0.806
#: 📊 Dois pontos percentuais: e o que o arredondamento das fatias sinteticas
#: move. Uma tolerancia maior deixaria de distinguir 80,6% de 78%.
TOLERANCIA_DE_PARIDADE = 0.02


def cobertura_esperada(slug):
    """Quantas apolices da PRODUCAO tem produtor conhecido, e a fracao disso.

    🔴 Isto e o que a fixture PRECISA reproduzir para o canario medir a §1.11
    desta SPEC. A versao anterior devolvia as MESMAS 3.536 linhas para as quatro
    fatias de ano, e o guarda cravava **5,95%** -- um numero que o produto nunca
    produz, sobre uma populacao que ele nunca busca (CLAUDE.md §9.4: o que se
    afirma e o comportamento do MOTOR sobre o texto REAL).
    """
    n = controles(slug)["documentos_bi_2025_tipo_A"]["n_documentos_tipo_A"]
    return int(round(PARIDADE_DE_COBERTURA * n)), n


def linhas_de_renovacao(slug, ano=2025):
    """As linhas CRUAS de `/renovacoes` **daquele ANO de vencimento**.

    📊 `val_c` vem NULO em 3.536 de 3.536 linhas da Resulta — e é por isso que
    a comissão do radar não pode ser somada como zero. O repasse mora em
    `prod_docs`, e a soma é de TODOS eles, não só da `ordem == 1`.

    🔴 **E A FATIA DE ANO IMPORTA.** A rota filtra por `fimvig`, e o adapter a
    chama QUATRO vezes para uma pergunta de um ano (2024, 2025, 2026, 2027).
    Devolver o mesmo lote nas quatro e uma fonte que nao existe: ela ignoraria o
    filtro que e a razao de ser da rota. Aqui:

    ```
    2025  os 3.536 registros do censo (fimvig em 2025) -- e a intersecao MEDIDA
          com a producao de 2025, que e o artefato de 2,8%
    2026  as apolices que COMECARAM em 2025 e vencem em 2026 -- 80,6% delas,
          que e a paridade que o BLOCO D exige
    2024
    2027  vazias: nada do acervo sintetico vence nesses anos
    ```
    """
    if ano == 2026:
        return _linhas_de_renovacao_de_2026(slug)
    if ano != 2025:
        return []
    c = controles(slug)["renovacoes_2025"]
    n = c["n_registros"]
    premios = _centavos(int(round(c["soma_pretot"] * 100)), n)
    repasses = _centavos(int(round(c["soma_val_r_ordem1"] * 100)), n)
    produtores = c["distinct_produtores_ordem1"]
    negativos = c["dias_a_vencer_negativos"]
    # 🔴 A INTERSEÇÃO É MEDIDA, e é ela que decide quanto da produção tem
    # produtor conhecido. 📊 Resulta 100 de 3.536 (2,8%); AutoFleet **ZERO**.
    # As duas rotas filtram datas diferentes — `/documentos_bi` por início de
    # vigência, `/renovacoes` por fim — e apólice anual que começa num ano
    # termina no seguinte. Reproduzir a interseção é o que faz este canário
    # medir a §1.11 desta SPEC: *a receita de cobertura de produtor da 081 NÃO
    # é constante do provider; remede-se por corretora*.
    intersecao = controles(slug)["intersecao_por_nosnum"]["n"]
    saida = []
    for i in range(n):
        rotulo = "Produtor %03d" % (i % produtores)
        saida.append(_linha_completa("/renovacoes", {
            "nosnum": ("%s-DOC-%06d" % (slug, i)) if i < intersecao
                      else ("%s-REN-%06d" % (slug, i)),
            "tipdoc": "A",
            "cancelado": "F",
            "seguradora": "SEG%02d" % (i % 8),
            "ramo": "RAMO%02d" % (i % 6),
            "fimvig": date(2025, 1 + (i % 12), 28).strftime("%d/%m/%Y"),
            "pretot": "%.2f" % (premios[i] / 100.0),
            "dias_a_vencer": (-1 - i) if i < negativos else (i - negativos + 1),
            "quant_produtores": 1,
            "produtor": rotulo,
            "prod_docs": [
                {"produtor": rotulo, "ordem": 1, "agente": "EXECUTIVO",
                 "per_r": "10", "val_r": "%.2f" % (repasses[i] / 100.0)},
            ],
        }))
    return saida


# ===========================================================================
# O HTTP FALSO — no lugar EXATO onde a fonte faz o GET
# ===========================================================================
def _ano_do_parametro(params):
    """O ano da fatia pedida, lido de `dt_fim` (ou `dt_ini`). `dd/mm/aaaa`."""
    for chave in ("dt_fim", "dt_ini", "datfim", "datini"):
        bruto = str((params or {}).get(chave) or "").strip()
        if len(bruto) >= 10 and bruto[-4:].isdigit():
            return int(bruto[-4:])
    return 2025


def _linhas_de_renovacao_de_2026(slug):
    """O que COMECOU em 2025 e VENCE em 2026 — a fatia que da a paridade.

    🔴 O `nosnum` e o MESMO de `linhas_de_producao`, e e por isso que a
    intersecao existe: as duas rotas falam da mesma apolice, em dois anos
    diferentes, porque uma filtra o inicio e a outra o fim da vigencia.

    📊 80,6% delas, e nao 100%: a cobertura medida na API viva nao e total.
    Apolice plurianual, apolice cancelada e apolice sem produtor no cadastro
    ficam de fora — e e essa fracao que o produto declara ao dono.
    """
    c = controles(slug)["documentos_bi_2025_tipo_A"]
    r = controles(slug)["renovacoes_2025"]
    com_produtor, n = cobertura_esperada(slug)
    premios = _centavos(int(round(c["soma_pretot"] * 100)), n)
    repasses = _centavos(int(round(r["soma_val_r_ordem1"] * 100)), max(com_produtor, 1))
    produtores = r["distinct_produtores_ordem1"]
    saida = []
    for i in range(com_produtor):
        rotulo = "Produtor %03d" % (i % produtores)
        saida.append(_linha_completa("/renovacoes", {
            # ⚠️ O MESMO `nosnum` da producao: e o join.
            "nosnum": "%s-DOC-%06d" % (slug, i),
            "tipdoc": "A",
            "cancelado": "F",
            "seguradora": "SEG%02d" % (i % 8),
            "ramo": "RAMO%02d" % (i % 6),
            "fimvig": date(2026, 1 + (i % 12), 1).strftime("%d/%m/%Y"),
            "pretot": "%.2f" % (premios[i] / 100.0),
            "dias_a_vencer": 200 + (i % 165),
            "quant_produtores": 1,
            "produtor": rotulo,
            "prod_docs": [
                {"produtor": rotulo, "ordem": 1, "agente": "EXECUTIVO",
                 "per_r": "10", "val_r": "%.2f" % (repasses[i] / 100.0)},
            ],
        }))
    return saida


def _classe_de_fonte_falsa(base):
    """Uma `FonteInfocap` de verdade, com `_autenticar` e `_get` falsos.

    🔴 O corte é no HTTP, e não em `producao_crua`. 📊 CLAUDE.md §9.4: o teste
    que substitui o motor prova que a fixture casa com a fixture. Aqui o
    fatiamento por ano, o desembrulho do envelope e a dedupe são os de
    produção — o que não acontece é a chamada sair.
    """

    class FonteFalsa(base):
        chamadas = []

        def _autenticar(self):
            return "token-de-fixture"

        def _get(self, rota, params):   # noqa: ANN001
            FonteFalsa.chamadas.append((rota, dict(params)))
            slug = str(getattr(self, "_rotulo", "") or "")
            for nome in EMPRESAS:
                if nome in slug:
                    slug = nome
                    break
            # 🔴 A Amandus resolve para a conta da Resulta: a mesma carteira,
            # ao centavo. É o P1 do censo, reproduzido de propósito — se o
            # gate falhar, o teste VÊ a carteira errada, e não um erro.
            if slug == "amandus":
                slug = "resulta"
            if rota == "/documentos_bi":
                return {"documentos": linhas_de_producao(slug)}
            if rota == "/renovacoes":
                # 🔴 A FONTE RESPEITA O FILTRO. `dt_ini`/`dt_fim` chegam em
                # `dd/mm/aaaa` e o adapter fatia por ANO CIVIL, entao o ano do
                # `dt_fim` identifica a fatia. Uma fixture que ignora o filtro
                # nao e a fonte: e um dicionario com o nome dela.
                return {"renovacoes": linhas_de_renovacao(
                    slug, _ano_do_parametro(params))}
            return {}

    return FonteFalsa


# ===========================================================================
# O Supabase FALSO — nenhuma leitura e nenhuma escrita reais
# ===========================================================================
class Resposta:
    def __init__(self, data):
        self.data = data
        self.count = len(data) if isinstance(data, list) else None

    def __await__(self):
        async def _eu():
            return self
        return _eu().__await__()


class Tabela:
    def __init__(self, diario, nome, dados):
        self._d, self.nome, self._dados = diario, nome, dados
        self.op, self.campos, self.filtros = "select", None, {}

    def select(self, *a, **k):           # noqa: ANN001, ARG002
        self.op = "select"
        return self

    def update(self, v, *a, **k):        # noqa: ANN001, ARG002
        self.op, self.campos = "update", dict(v or {})
        return self

    def insert(self, v, *a, **k):        # noqa: ANN001, ARG002
        self.op, self.campos = "insert", v
        return self

    def eq(self, c, v):
        self.filtros[c] = v
        return self

    def in_(self, c, v):
        self.filtros[c] = v
        return self

    def neq(self, c, v):
        self.filtros["!" + c] = v
        return self

    def limit(self, *a, **k):            # noqa: ANN001, ARG002
        return self

    def order(self, *a, **k):            # noqa: ANN001, ARG002
        return self

    def single(self):
        return self

    def maybe_single(self):
        return self

    def execute(self):
        self._d.append({"tabela": self.nome, "op": self.op,
                        "filtros": dict(self.filtros), "campos": self.campos})
        linhas = self._dados(self.nome, self.filtros) if self.op == "select" else []
        return Resposta(linhas)


class SupabaseFalso:
    """⛔ Não abre conexão. As três corretoras, com as conexões do censo."""

    def __init__(self):
        self.diario = []
        self.conexoes = [
            {"id": "conn-%s" % slug, "company_id": cid, "status": "connected",
             "health_status": "healthy",
             "connection_config": {"base_url": "https://exemplo.invalido"},
             "encrypted_secret_ref": "cifra-de-fixture-%s" % slug,
             "login_de_fixture": LOGIN_DE_FIXTURE[slug]}
            for slug, cid in EMPRESAS.items()]

    @property
    def client(self):
        return self

    def _dados(self, tabela, filtros):
        if tabela == "connector_templates":
            return [{"id": "tpl-infocap", "slug": "infocap"}]
        if tabela == "tenant_connections":
            emp = filtros.get("company_id")
            return [dict(c) for c in self.conexoes
                    if emp is None or c["company_id"] == emp]
        if tabela == "companies":
            emp = filtros.get("id")
            nome = next((s for s, c in EMPRESAS.items() if c == emp), "corretora")
            return [{"company_name": nome.capitalize()}]
        return []

    def table(self, nome):
        return Tabela(self.diario, nome, self._dados)


# ===========================================================================
# O CANÁRIO
# ===========================================================================
RE_DINHEIRO = re.compile(r"R\$ ?\d")
RE_APOLICES = re.compile(r"\d+\s+ap[oó]lices", re.I)
RE_CPF = re.compile(r"\b\d{11}\b")
ABERTURA, FECHAMENTO = "<<PACK", "PACK>>"


def partes(texto):
    if ABERTURA not in texto or FECHAMENTO not in texto:
        return texto, None
    antes, resto = texto.split(ABERTURA, 1)
    dentro, depois = resto.split(FECHAMENTO, 1)
    try:
        pack = json.loads(dentro.strip())
    except Exception:  # noqa: BLE001
        pack = None
    return antes + depois, pack


def _laco():
    """Um event loop, criado com a rede aberta por UM passo.

    📊 No Windows, criar o loop chama `socket.socketpair()`, que faz um
    `connect` em `127.0.0.1` para o self-pipe. Com o bloqueio ligado, o loop
    nem nasce — e o sintoma seria confundido com defeito do adapter. O par de
    sockets é local ao processo; nenhum host é contatado.
    """
    _abrir_a_rede()
    try:
        return asyncio.new_event_loop()
    finally:
        _fechar_a_rede()


def rodar(slug, capturas, *, pergunta="2025", pack_id="", dimension=""):
    """Uma pergunta de verdade, ponta a ponta. Devolve `(texto, erro)`."""
    from app.agents.tools import executive_intelligence as tool_mod
    from app.agents.tools import relatorios_comerciais as rel
    from app.providers import infocap_analytics_provider as adapter

    fonte_real = None
    import app.comercial.fonte_infocap as fmod

    fonte_real = fmod.FonteInfocap
    fmod.FonteInfocap = _classe_de_fonte_falsa(fonte_real)

    credencial_real = adapter.InfocapAnalyticsProvider._credencial

    def _credencial(self, conn):   # noqa: ANN001
        return (str(conn.get("login_de_fixture") or ""), "senha-de-fixture",
                (conn.get("connection_config") or {}).get("base_url", ""), "0")

    publicar_real = rel._publicar

    def _publicar(supabase, company_id, **kw):   # noqa: ANN001, ARG001
        capturas.append(dict(kw, company_id=company_id))
        return "artifact-de-fixture-%s" % slug

    adapter.InfocapAnalyticsProvider._credencial = _credencial
    rel._publicar = _publicar
    adapter.esquecer_contas()
    tool_mod.esquecer_pacotes()

    laco = _laco()
    try:
        tool = tool_mod.ExecutiveIntelligenceTool(
            company_id=EMPRESAS[slug], supabase=SupabaseFalso())
        texto = laco.run_until_complete(
            tool._arun(period=pergunta, pack_id=pack_id, dimension=dimension))
        return texto, ""
    except Exception as exc:  # noqa: BLE001
        return "", "%s: %s" % (type(exc).__name__, exc)
    finally:
        laco.close()
        fmod.FonteInfocap = fonte_real
        adapter.InfocapAnalyticsProvider._credencial = credencial_real
        rel._publicar = publicar_real


def valor(pack, metric_id):
    for m in pack.get("metrics") or []:
        if m.get("metric_id") == metric_id:
            return m.get("value")
    return None


def canario_de(slug):
    _p("\n--- CANARIO: %s ---" % slug.upper())
    c = controles(slug)
    capturas = []
    texto, erro = rodar(slug, capturas)
    if not check("%s: a tool respondeu" % slug, not erro and bool(texto), erro):
        return None
    check("%s: RELATORIO_PRONTO com o link" % slug,
          "RELATORIO_PRONTO" in texto and "[Abrir o relatório](" in texto,
          texto[:160])

    fora, pack = partes(texto)
    if not check("%s: o bloco <<PACK ... PACK>> tem JSON valido" % slug,
                 pack is not None, texto[-200:]):
        return None

    # 📊 OS NUMEROS. Cada um contra o controle-ouro do censo.
    esperado_apolices = c["documentos_bi_2025_tipo_A"]["n_documentos_tipo_A"]
    esperado_comissao = c["documentos_bi_2025_tipo_A"]["soma_val_c"]
    esperado_premio = c["documentos_bi_2025_tipo_A"]["soma_pretot"]
    esperado_renov = c["renovacoes_2025"]["n_registros"]
    # 🔴 A EXPECTATIVA MUDOU EM 03/09/2026, E A MUDANCA E O CONSERTO.
    #
    # 📊 Ela era `min(intersecao_2025x2025, produtores)` — ZERO na AutoFleet,
    # 97 na Resulta com cobertura de 5,95%. Aquele numero saia de uma fixture
    # que devolvia as MESMAS 3.536 linhas para as QUATRO fatias de ano que o
    # adapter pede (2024-2027): a fonte falsa ignorava `dt_ini/dt_fim`, e o
    # canario media a cobertura sobre uma populacao que o produto **nunca
    # busca**. Na API viva o mesmo caminho entrega **80,6%** (censo do BLOCO 0,
    # que e a razao de `anos_de_vencimento_para` varrer de N-1 a N+2).
    #
    # E a intersecao de 2025x2025 continua sendo o que sempre foi: um ARTEFATO
    # da janela — apolice anual que comeca num ano termina no seguinte. Ela e
    # medida, e nao e a cobertura do produto.
    #
    # CLAUDE.md §9.4: o que se afirma e o comportamento do MOTOR sobre o dado
    # REAL. A fixture agora respeita a fatia de ano, e a expectativa e a
    # paridade que o BLOCO D exige.
    intersecao = c["intersecao_por_nosnum"]["n"]
    com_produtor, n_producao = cobertura_esperada(slug)
    esperado_produtores = min(
        com_produtor, c["renovacoes_2025"]["distinct_produtores_ordem1"])

    check("%s: production.policy_count = %d" % (slug, esperado_apolices),
          valor(pack, "production.policy_count") == esperado_apolices,
          valor(pack, "production.policy_count"))
    check("%s: commission.broker_accrued = R$ %.2f" % (slug, esperado_comissao),
          abs(float(valor(pack, "commission.broker_accrued") or 0) - esperado_comissao) <= 0.05,
          valor(pack, "commission.broker_accrued"))
    check("%s: production.premium_written = R$ %.2f" % (slug, esperado_premio),
          abs(float(valor(pack, "production.premium_written") or 0) - esperado_premio) <= 0.05,
          valor(pack, "production.premium_written"))
    check("%s: renewal.exposure = %d" % (slug, esperado_renov),
          valor(pack, "renewal.exposure") == esperado_renov,
          valor(pack, "renewal.exposure"))
    check("%s: producer.performance = %d produtores distintos sobre as %d "
          "apolices com produtor conhecido" % (slug, esperado_produtores,
                                               com_produtor),
          valor(pack, "producer.performance") == esperado_produtores,
          valor(pack, "producer.performance"))

    # 🔴 §1.11 + BLOCO D: a PARIDADE de 80,6%, medida na API viva.
    cob = next((m["coverage"] for m in pack["metrics"]
                if m["metric_id"] == "producer.performance"), None)
    check("%s: e a COBERTURA de produtor bate a PARIDADE de %.1f%% (+- %.0f p.p.)"
          % (slug, 100.0 * PARIDADE_DE_COBERTURA, 100.0 * TOLERANCIA_DE_PARIDADE),
          cob is not None
          and abs(cob - PARIDADE_DE_COBERTURA) <= TOLERANCIA_DE_PARIDADE,
          "veio %r, esperado %r +- %r — 📊 o produto entrega 80,6%% varrendo "
          "2024-2027; um guarda que crava 5,95%% esta medindo a janela de "
          "2025x2025, que o produto nao usa"
          % (cob, PARIDADE_DE_COBERTURA, TOLERANCIA_DE_PARIDADE))
    # 🔴 CONTROLE: e a paridade e MUITO maior que a intersecao de 2025x2025.
    # Sem esta linha, uma fixture que voltasse a ignorar a fatia de ano deixaria
    # a assercao acima passar por coincidencia de tolerancia.
    artefato = intersecao / esperado_apolices
    check("%s: CONTROLE: a paridade (%.1f%%) e MUITO maior que o artefato de "
          "2025x2025 (%.1f%%)" % (slug, 100.0 * (cob or 0), 100.0 * artefato),
          (cob or 0) > artefato + 0.5,
          "cobertura=%r artefato=%r — se as duas coincidem, a fonte falsa "
          "voltou a ignorar `dt_ini/dt_fim`" % (cob, artefato))

    # 🔴 E OS VALORES DE DINHEIRO DAS DUAS METRICAS QUE NINGUEM AFIRMAVA.
    #
    # 📊 `repasse.producer_accrued` e `contribution.after_repasse` sao as duas
    # metricas que o cartao "O que sobra depois do repasse" imprime — e o
    # canario nao tinha UMA assercao de valor sobre elas. Uma metrica que so e
    # conferida por "existe no pack" nao esta conferida.
    repasse = valor(pack, "repasse.producer_accrued")
    esperado_repasse = c["renovacoes_2025"]["soma_val_r_ordem1"]
    check("%s: repasse.producer_accrued = R$ %.2f (o que VENCE em 2025)"
          % (slug, esperado_repasse),
          isinstance(repasse, (int, float))
          and abs(float(repasse) - esperado_repasse) <= 0.05,
          "veio %r — a base e POLICY_VALID_TO, e a fatia de 2025 do censo"
          % (repasse,))
    contrib = valor(pack, "contribution.after_repasse")
    # A contribuicao e a comissao das apolices na INTERSECAO menos o repasse
    # delas. A fatia de 2026 e a que casa com a producao de 2025.
    check("%s: contribution.after_repasse e um numero POSITIVO e MENOR que a "
          "comissao do periodo" % slug,
          isinstance(contrib, (int, float)) and 0 < float(contrib) < esperado_comissao,
          "veio %r (comissao do periodo: %r) — se ela for maior que a comissao, "
          "o repasse entrou com sinal trocado" % (contrib, esperado_comissao))
    cob_contrib = next((m["coverage"] for m in pack["metrics"]
                        if m["metric_id"] == "contribution.after_repasse"), None)
    check("%s: e a cobertura DELA tambem bate a paridade (%.1f%%)"
          % (slug, 100.0 * PARIDADE_DE_COBERTURA),
          cob_contrib is not None
          and abs(cob_contrib - PARIDADE_DE_COBERTURA) <= TOLERANCIA_DE_PARIDADE,
          "veio %r — ela e a fracao da comissao do periodo que tem repasse "
          "conhecido" % (cob_contrib,))

    # 🔴 A CAMADA QUE ESTA SPEC EXISTE PARA IMPOR
    check("%s: commission.broker_received e UNAVAILABLE (nunca zero)" % slug,
          valor(pack, "commission.broker_received") == "UNAVAILABLE",
          valor(pack, "commission.broker_received"))
    bases = {m["metric_id"]: m["time_basis"] for m in pack["metrics"]}
    check("%s: toda metrica declara base temporal" % slug,
          all(b in ("POLICY_VALID_FROM", "POLICY_VALID_TO") for b in bases.values()),
          bases)
    check("%s: renewal.exposure conta pelo FIM da vigencia" % slug,
          bases.get("renewal.exposure") == "POLICY_VALID_TO", bases.get("renewal.exposure"))
    check("%s: production.policy_count conta pelo INICIO" % slug,
          bases.get("production.policy_count") == "POLICY_VALID_FROM",
          bases.get("production.policy_count"))
    check("%s: toda metrica carrega `coverage`" % slug,
          all("coverage" in m for m in pack["metrics"]))

    # 🔴 O NUMERO NAO VOLTA A SER PROSA, e o rotulo do produtor nao viaja
    achados = []
    if RE_DINHEIRO.search(fora):
        achados.append("dinheiro em prosa")
    if RE_APOLICES.search(fora):
        achados.append("contagem em prosa")
    if RE_CPF.search(texto):
        achados.append("documento de 11 digitos")
    if re.search(r"Produtor \d{3}", texto):
        achados.append("rotulo de produtor no texto do chat")
    check("%s: FORA do bloco nao ha numero, e nenhum rotulo de produtor" % slug,
          not achados, achados)

    # 🔴 O ELO: o Artifact carrega o MESMO pacote
    if check("%s: publicou um Artifact (o capturador viu o payload)" % slug,
             bool(capturas), "nenhuma publicacao"):
        payload = capturas[-1]["payload"]
        check("%s: o template e `executive.pulse360`" % slug,
              capturas[-1]["template"] == "executive.pulse360",
              capturas[-1]["template"])
        check("%s: o `pack_id` do chat e o do Artifact sao O MESMO" % slug,
              payload["evidence_pack"]["pack_id"] == pack["pack_id"],
              "%s x %s" % (payload["evidence_pack"]["pack_id"], pack["pack_id"]))
        check("%s: as `metrics` do chat e as do Artifact sao IDENTICAS" % slug,
              payload["evidence_pack"]["metrics"] == pack["metrics"])
        check("%s: a peca declara 'papel nao mapeado' (M3)" % slug,
              payload.get("papel_dos_produtores") == "papel não mapeado",
              payload.get("papel_dos_produtores"))
        renderizar(slug, capturas[-1]["blocos"])

    # 🔴 O FOLLOW-UP: mesmo `pack_id`, sem consultar de novo
    antes = len(capturas)
    texto2, erro2 = seguir(slug, capturas, pack["pack_id"])
    check("%s: o follow-up respondeu" % slug, not erro2 and bool(texto2), erro2)
    if texto2:
        _fora2, pack2 = partes(texto2)
        check("%s: o follow-up devolve o MESMO `pack_id`" % slug,
              (pack2 or {}).get("pack_id") == pack["pack_id"],
              (pack2 or {}).get("pack_id"))
        check("%s: e NAO publicou um segundo Artifact (sem refetch)" % slug,
              len(capturas) == antes, "%d -> %d" % (antes, len(capturas)))
        check("%s: os totais do follow-up sao os mesmos" % slug,
              valor(pack2, "production.policy_count")
              == valor(pack, "production.policy_count"))

    # os findings, e o que NAO virou sinal
    kinds = [f.get("kind") for f in (pack.get("findings") or [])]
    check("%s: os findings deterministicos sairam" % slug, bool(kinds), kinds)
    check("%s: cobertura baixa NAO esta marcada para virar sinal" % slug,
          all(not f.get("vira_sinal") for f in (pack.get("findings") or [])
              if f.get("kind") == "low_coverage"), kinds)
    sinais(slug, pack)
    return pack


def seguir(slug, capturas, pack_id):
    """A segunda pergunta da MESMA conversa. ⚠️ O cache é por processo."""
    from app.agents.tools import executive_intelligence as tool_mod
    from app.agents.tools import relatorios_comerciais as rel

    publicar_real = rel._publicar

    def _publicar(supabase, company_id, **kw):   # noqa: ANN001, ARG001
        capturas.append(dict(kw, company_id=company_id))
        return "artifact-de-fixture-2"

    rel._publicar = _publicar
    laco = _laco()
    try:
        tool = tool_mod.ExecutiveIntelligenceTool(
            company_id=EMPRESAS[slug], supabase=SupabaseFalso())
        return laco.run_until_complete(
            tool._arun(period="", pack_id=pack_id, dimension="SEG01")), ""
    except Exception as exc:  # noqa: BLE001
        return "", "%s: %s" % (type(exc).__name__, exc)
    finally:
        laco.close()
        rel._publicar = publicar_real


def sinais(slug, pack_serializado):
    """Os rascunhos de sinal, contra o `SignalDraft.valido()` REAL."""
    from app.comercial import evidence_pack as ep
    from app.services.intelligence.schemas import SignalDraft

    metricas = [ep.MetricResult(
        metric_id=m["metric_id"], version=m["version"], value=m["value"],
        unit=m["unit"], period=m["period"], time_basis=m["time_basis"],
        coverage=m["coverage"], confidence=m["confidence"],
        provider_key=m["provider_key"]) for m in pack_serializado["metrics"]]
    pacote = ep.EvidencePack(
        company_id=pack_serializado["company_id"],
        period=pack_serializado["period"], metrics=metricas,
        findings=list(pack_serializado.get("findings") or []),
        pack_id=pack_serializado["pack_id"])
    rascunhos = ep.sinais_do_pack(pacote)
    check("%s: o pack produziu rascunho(s) de sinal" % slug, bool(rascunhos))
    for bruto in rascunhos:
        d = SignalDraft(**bruto)
        ok, motivo = d.valido()
        check("%s: `SignalDraft.valido()` REAL aceita `%s`"
              % (slug, bruto["metadata"]["finding_kind"]), ok, motivo)
        check("%s: e ele nasce em `comercial`, severity<=medium" % slug,
              d.domain == "comercial" and d.severity in ("info", "low", "medium"),
              "%s / %s" % (d.domain, d.severity))
    check("%s: nenhum sinal e de cobertura baixa" % slug,
          all(b["metadata"]["finding_kind"] != "low_coverage" for b in rascunhos))


def renderizar(slug, blocos):
    """🔴 O template RENDERIZA. Bloco que não existe devolve caixa vazia."""
    from app.services.artifacts import blocks

    faltando = [b["block"] for b in blocos if b["block"] not in blocks.BLOCOS]
    check("%s: os %d blocos da peca EXISTEM em blocks.py" % (slug, len(blocos)),
          not faltando, faltando)
    check("CONTROLE: o detector acharia um bloco inventado",
          "bloco_que_nao_existe" not in blocks.BLOCOS)
    html = []
    for b in blocos:
        if b["block"] in blocks.BLOCOS:
            html.append(blocks.BLOCOS[b["block"]](b.get("props") or {}, {}))
    inteiro = "\n".join(html)
    check("%s: a peca renderiza HTML (%d blocos, %d bytes)"
          % (slug, len(html), len(inteiro)), len(inteiro) > 500)
    check("%s: o HTML da peca nao carrega documento de 11 digitos" % slug,
          not RE_CPF.search(inteiro))
    check("%s: a secao de fontes carrega o `pack_id`" % slug,
          "pack_id" in inteiro, "sem ela a peca e bonita e indefensavel")


def os_tres_findings_que_viram_sinal():
    """🔴 Os TRÊS, com os limiares cruzados de propósito — e o par de cada um.

    ⚠️ O canário das duas corretoras cruza um limiar só: a carteira sintética
    é uniforme entre 36 seguradoras, então a concentração fica em ~2,8% e não
    aciona nada. Um teste que só exercitasse o caminho feliz da fixture
    provaria que a fixture é plana, e não que os achados funcionam.

    Aqui os três limiares são cruzados um a um, e cada um tem o seu PAR: a
    mesma superfície com o limiar NÃO cruzado, que tem de NÃO produzir achado.
    """
    from app.comercial import evidence_pack as ep
    from app.services.intelligence.schemas import SignalDraft

    _p("\n--- OS TRES FINDINGS QUE VIRAM SINAL ---")
    empresa = EMPRESAS["resulta"]
    periodo = ep.periodo_iso("2025-01-01", "2025-12-31")
    anterior = ep.periodo_iso("2024-01-01", "2024-12-31")
    ref_a = ep.ref_de_produtor(empresa, "Produtor 001")
    ref_b = ep.ref_de_produtor(empresa, "Produtor 002")

    def _mix(pct):
        return ep.metrica("mix.insurer", pct, "pct", period=periodo,
                          time_basis="POLICY_VALID_FROM", coverage=1.0,
                          breakdown=[{"rotulo": "SEG01", "share_pct": pct}])

    def _perf(atual):
        return ep.metrica("producer.performance", 2, "count", period=periodo,
                          time_basis="POLICY_VALID_FROM", coverage=0.9,
                          breakdown=[{"producer_ref": ref_a, "comissao": atual},
                                     {"producer_ref": ref_b, "comissao": 5000.0}])

    antes = [ep.metrica("producer.performance", 2, "count", period=anterior,
                        time_basis="POLICY_VALID_FROM", coverage=0.9,
                        breakdown=[{"producer_ref": ref_a, "comissao": 5000.0},
                                   {"producer_ref": ref_b, "comissao": 5000.0}])]
    exposicao = ep.metrica("renewal.exposure", 3536, "count", period=periodo,
                           time_basis="POLICY_VALID_TO", coverage=1.0,
                           breakdown=[{"faixa": "vencidas", "apolices": 2594,
                                       "premio": 1.0}])

    acima = ep.achar_findings([_mix(62.3), exposicao, _perf(400.0)], antes)
    kinds = [f["kind"] for f in acima]
    for esperado in ("concentration", "renewal_exposure", "producer_drop"):
        check("com o limiar CRUZADO, `%s` aparece" % esperado, esperado in kinds,
              kinds)

    # 🔴 O PAR: mesma superfície, limiares NÃO cruzados.
    abaixo = ep.achar_findings(
        [_mix(ep.LIMIAR_CONCENTRACAO_PCT - 0.1),
         ep.metrica("renewal.exposure", 0, "count", period=periodo,
                    time_basis="POLICY_VALID_TO", coverage=1.0),
         _perf(5000.0)], antes)
    kinds_abaixo = [f["kind"] for f in abaixo]
    for nao_esperado in ("concentration", "renewal_exposure", "producer_drop"):
        check("PAR: com o limiar NAO cruzado, `%s` NAO aparece" % nao_esperado,
              nao_esperado not in kinds_abaixo, kinds_abaixo)

    pacote = ep.EvidencePack(company_id=empresa, period=periodo,
                             compare_period=anterior,
                             metrics=[_mix(62.3), exposicao, _perf(400.0)],
                             findings=acima)
    rascunhos = ep.sinais_do_pack(pacote)
    check("os TRES viram rascunho de sinal", len(rascunhos) == 3,
          [r["metadata"]["finding_kind"] for r in rascunhos])
    for bruto in rascunhos:
        d = SignalDraft(**bruto)
        ok, motivo = d.valido()
        check("`SignalDraft.valido()` REAL aceita `%s`"
              % bruto["metadata"]["finding_kind"], ok, motivo)
        check("  e ele sai `commercial_opportunity` / `comercial` / <=medium",
              d.signal_type == "commercial_opportunity" and d.domain == "comercial"
              and d.severity == "medium",
              "%s / %s / %s" % (d.signal_type, d.domain, d.severity))
        check("  e carrega `metric_refs` e `pack_id` no metadata",
              bool(d.metadata.get("metric_refs")) and
              d.metadata.get("pack_id") == pacote.pack_id)

    # 🔴 CONTROLE: cobertura baixa fica no pack e NAO vira sinal.
    com_cobertura_baixa = ep.achar_findings(
        [ep.metrica("data.coverage", 5.9, "pct", period=periodo,
                    time_basis="POLICY_VALID_FROM", coverage=0.059)], [])
    check("cobertura baixa vira FINDING", any(
        f["kind"] == "low_coverage" for f in com_cobertura_baixa))
    pack_cob = ep.EvidencePack(company_id=empresa, period=periodo,
                               findings=com_cobertura_baixa)
    check("mas NAO vira sinal (o tipo que a descreveria tem gate proprio)",
          not ep.sinais_do_pack(pack_cob))
    # 🔴 E o CONTROLE do controle: sem evidencia no pack, nada sai — o que
    # prova que o vazio acima nao e vazio por acidente.
    check("CONTROLE: o mesmo `sinais_do_pack` PRODUZ quando ha metrica",
          len(ep.sinais_do_pack(pacote)) == 3)


def impressao_bate_com_o_censo():
    """🔴 A impressão CALCULADA tem de bater com a impressão MEDIDA.

    📊 Foi este canário que achou, em 03/09/2026, que ela NÃO batia:
    `impressao_da_rota` juntava as chaves com `,` e o censo as juntou com `|`.
    As mesmas 20 chaves de `/documentos_bi` davam `57f3fa24…` no código e
    `3437d553…` no arquivo — então **toda leitura viva era drift**, o
    manifesto marcava `DEGRADED` e as 14 métricas saíam INDISPONÍVEL. Com
    todos os gates verdes, porque nenhum teste comparava os dois lados: os
    testes comparavam impressões calculadas entre si.

    ⚠️ É o corolário do CLAUDE.md §9.3: *um padrão medido com uma ferramenta e
    aplicado com outra é um padrão sobre outra coisa*. Este é o guarda que
    fecha a porta, e ele compara o CÓDIGO com o ACERVO.
    """
    from app.providers.infocap_analytics_provider import impressao_da_rota

    _p("\n--- A IMPRESSAO DE SCHEMA: codigo x censo ---")
    for rota, linhas in (("/documentos_bi", linhas_de_producao("resulta")[:1]),
                         ("/renovacoes", linhas_de_renovacao("resulta")[:1])):
        medida = FINGERPRINTS["rotas"][rota]["sha256_das_chaves_ordenadas"]
        calculada = impressao_da_rota(linhas)
        check("a impressao de `%s` calculada BATE com a medida no censo" % rota,
              calculada == medida,
              "calculada %s… x medida %s… — se nao bate, TODA leitura viva e "
              "lida como drift e o relatorio inteiro sai INDISPONIVEL"
              % (calculada[:12], medida[:12]))
    # 🔴 CONTROLE: o detector de drift ainda CONSEGUE disparar. Um guarda que
    # so sabe dizer "bate" não guarda nada (CLAUDE.md §9.3).
    com_chave_nova = dict(linhas_de_producao("resulta")[0], campo_novo="x")
    check("CONTROLE: uma chave A MAIS muda a impressao (o drift dispara)",
          impressao_da_rota([com_chave_nova])
          != FINGERPRINTS["rotas"]["/documentos_bi"]["sha256_das_chaves_ordenadas"])


# ===========================================================================
def principal():
    _fechar_a_rede()
    try:
        _p("=" * 74)
        _p("CANARIO DO PULSO 360 — SPEC-094 BLOCO G")
        _p("📊 golden controls: %s · janela %s"
           % (GOLDEN["measured_at"][:10], GOLDEN["janela"]))
        _p("=" * 74)

        impressao_bate_com_o_censo()
        os_tres_findings_que_viram_sinal()

        packs = {}
        for slug in ("resulta", "autofleet"):
            packs[slug] = canario_de(slug)

        # 🔴 A AMANDUS: a recusa E o teste dela.
        _p("\n--- CANARIO: AMANDUS (a RECUSA e o teste) ---")
        from app.providers import infocap_analytics_provider as adapter

        adapter.esquecer_contas()
        capturas = []
        rodar("resulta", capturas)            # a primeira corretora da conta
        texto, erro = rodar_sem_esquecer("amandus", capturas)
        check("amandus: a tool NAO devolveu relatorio pronto",
              "RELATORIO_PRONTO" not in (texto or ""),
              "🔴 se ela devolveu, o dono da Amandus esta lendo a carteira da "
              "Resulta com o nome dele em cima (F-094-07)")
        check("amandus: a resposta PROIBE afirmar que o relatorio existe",
              "RELATORIO_FALHOU" in (texto or "") and "PROIBIDO" in (texto or ""),
              (texto or erro)[:220])
        check("amandus: NAO publicou Artifact nenhum",
              not any(c["company_id"] == EMPRESAS["amandus"] for c in capturas),
              [c["company_id"] for c in capturas])

        # 🔴 E o CONTROLE que impede a recusa de ser um apagao: as duas que
        # tem login proprio continuam passando (elas passaram acima).
        check("CONTROLE: a recusa NAO e geral — Resulta e AutoFleet passaram",
              all(packs.get(s) for s in ("resulta", "autofleet")))

        # 🔴 E as duas carteiras sao DIFERENTES: se fossem iguais, o teste
        # inteiro passaria com um provider que ignora o tenant.
        if packs.get("resulta") and packs.get("autofleet"):
            check("CONTROLE: as duas corretoras leem carteiras DIFERENTES",
                  valor(packs["resulta"], "production.policy_count")
                  != valor(packs["autofleet"], "production.policy_count"),
                  "se forem iguais, o `company_id` nao esta chegando na leitura")
            check("CONTROLE: e os `pack_id` sao diferentes",
                  packs["resulta"]["pack_id"] != packs["autofleet"]["pack_id"])

        _p("\n--- A REDE ---")
        fechou = ""
        try:
            s = socket.socket()
            s.connect(("127.0.0.1", 9))
            s.close()
        except RedeProibida:
            fechou = "bloqueada"
        except Exception as exc:  # noqa: BLE001
            fechou = "OUTRA: %s" % type(exc).__name__
        check("⛔ nenhuma chamada saiu: `socket.connect` esta bloqueado",
              fechou == "bloqueada", fechou)
    finally:
        _abrir_a_rede()

    _p("\n" + "=" * 74)
    _p("  %d assercoes verdes - %d vermelhas" % (PASS, FAIL))
    _p("=" * 74)
    return 1 if FAIL else 0


def rodar_sem_esquecer(slug, capturas):
    """Como `rodar`, mas SEM limpar o registro de contas em uso.

    🔴 É o ponto inteiro do teste da Amandus: o gate de conta compartilhada só
    consegue recusar a SEGUNDA corretora se a PRIMEIRA já estiver registrada.
    Limpar o registro entre as duas apagaria justamente a memória que o gate
    usa — e o teste passaria por vacuidade.
    """
    from app.agents.tools import executive_intelligence as tool_mod
    from app.agents.tools import relatorios_comerciais as rel
    from app.providers import infocap_analytics_provider as adapter
    import app.comercial.fonte_infocap as fmod

    fonte_real = fmod.FonteInfocap
    fmod.FonteInfocap = _classe_de_fonte_falsa(fonte_real)
    credencial_real = adapter.InfocapAnalyticsProvider._credencial

    def _credencial(self, conn):   # noqa: ANN001
        return (str(conn.get("login_de_fixture") or ""), "senha-de-fixture",
                (conn.get("connection_config") or {}).get("base_url", ""), "0")

    publicar_real = rel._publicar

    def _publicar(supabase, company_id, **kw):   # noqa: ANN001, ARG001
        capturas.append(dict(kw, company_id=company_id))
        return "artifact-de-fixture-%s" % slug

    adapter.InfocapAnalyticsProvider._credencial = _credencial
    rel._publicar = _publicar
    tool_mod.esquecer_pacotes()
    laco = _laco()
    try:
        tool = tool_mod.ExecutiveIntelligenceTool(
            company_id=EMPRESAS[slug], supabase=SupabaseFalso())
        return laco.run_until_complete(tool._arun(period="2025")), ""
    except Exception as exc:  # noqa: BLE001
        return "", "%s: %s" % (type(exc).__name__, exc)
    finally:
        laco.close()
        fmod.FonteInfocap = fonte_real
        adapter.InfocapAnalyticsProvider._credencial = credencial_real
        rel._publicar = publicar_real


if __name__ == "__main__":
    sys.exit(principal())
