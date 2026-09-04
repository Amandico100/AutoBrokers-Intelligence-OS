# -*- coding: utf-8 -*-
"""As duas ferramentas de relatorio comercial — SPEC-081 Blocos C e D.

O QUE ESTE ARQUIVO GUARDA, e por que cada coisa esta aqui.

📊 A ferramenta `gerar_relatorio` que ja existia NUNCA produziu um artifact:
`select origin, count(*) from artifacts` → `routine: 40`, **`chat: 0`**. Tres
defeitos em serie, e o de fundo era o desenho — ela pede ao LLM que INVENTE o
conteudo. Estas duas fazem o oposto, e este teste prova a diferenca.

Blocos [1] a [4] sao ESTATICOS e rodam sempre. O bloco [5] TOCA A REDE e o
BANCO: ele gera um artifact de verdade e confere que ele nasceu com
`origin='chat'` — a linha que nunca existiu.

  Rodar tudo:  python backend/tests/test_as_ferramentas_de_relatorio_comercial.py
  So estatico: SEM_REDE=1
"""
from __future__ import annotations

import ast
import importlib.util
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
PASS = FAIL = 0


def check(nome, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:300] if extra else ""))


ALVO = os.path.join(RAIZ, "app", "agents", "tools", "relatorios_comerciais.py")
with open(ALVO, encoding="utf-8") as fh:
    FONTE = fh.read()
with open(os.path.join(RAIZ, "app", "agents", "graph.py"), encoding="utf-8") as fh:
    FONTE_GRAPH = fh.read()
with open(os.path.join(RAIZ, "app", "services", "artifacts", "blocks.py"),
          encoding="utf-8") as fh:
    FONTE_BLOCKS = fh.read()

ARVORE = ast.parse(FONTE)


def _classe(nome):
    return next((n for n in ast.walk(ARVORE)
                 if isinstance(n, ast.ClassDef) and n.name == nome), None)


# ==========================================================================
print("\n[1] As duas tools EXECUTAM — o defeito que matou a `gerar_relatorio`")
# ==========================================================================

for nome in ("RaioXComercialTool", "RadarDeRenovacoesTool"):
    c = _classe(nome)
    check(f"{nome} existe", c is not None)
    if not c:
        continue
    # 🔴 `exige_async` e o que faz `nodes.py:1084` aguardar `_arun`. Sem isso,
    # o executor chama `_run`, que levanta — e o modelo recebe jargao de
    # encanamento e inventa que deu certo.
    declara = any(
        isinstance(x, ast.AnnAssign) and getattr(x.target, "id", "") == "exige_async"
        for x in c.body)
    check(f"{nome} declara `exige_async`", declara,
          "sem isto o executor chama _run e a tool nunca roda")
    corpo = ast.unparse(c)
    check(f"{nome} tem `_arun` async", "async def _arun" in corpo)
    check(f"{nome}._run LEVANTA (nunca finge que funcionou)",
          "raise RuntimeError" in corpo)
    # O I/O sai do event loop: `_arun` delega para thread.
    check(f"{nome} roda o I/O em thread (nao congela o FastAPI)",
          "asyncio.to_thread" in corpo,
          "Supabase e urllib sao sincronos; direto no loop travam todas as conversas")

check("o executor le a declaracao",
      'getattr(tool, "exige_async", False)' in
      open(os.path.join(RAIZ, "app", "agents", "nodes.py"), encoding="utf-8").read())

# ==========================================================================
print("\n[2] SEMPRE devolve link, e NUNCA mente quando falha")
# ==========================================================================

check("existe um montador de link", "def _link(" in FONTE)
check("o link aponta para /dashboard/entregas", "/dashboard/entregas/" in FONTE)
check("as duas devolvem RELATORIO_PRONTO com o link",
      FONTE.count("RELATORIO_PRONTO") >= 2)
check("e o link vai no corpo do retorno, nao so na variavel",
      FONTE.count("[Abrir o relatório]({_link(") >= 2)

# 🔴 O erro fala a lingua do ATENDIMENTO, nao a do encanamento.
check("existe um tradutor de erro", "def _erro_legivel(" in FONTE)
check("ele PROIBE afirmar que o relatorio existe",
      "PROIBIDO" in FONTE and "NÃO existe link" in FONTE)
check("e carrega o motivo interno sem joga-lo no colo do cliente",
      "Motivo interno:" in FONTE)
check("periodo sem dado devolve RELATORIO_VAZIO, nao numero inventado",
      FONTE.count("RELATORIO_VAZIO") >= 2 and "Não invente número" in FONTE)

# CONTROLE: os tres estados sao DIFERENTES entre si.
check("CONTROLE: pronto, vazio e falhou sao tres carimbos distintos",
      len({"RELATORIO_PRONTO", "RELATORIO_VAZIO", "RELATORIO_FALHOU"}) == 3
      and all(k in FONTE for k in ("RELATORIO_PRONTO", "RELATORIO_VAZIO",
                                   "RELATORIO_FALHOU")))

# ==========================================================================
print("\n[3] Nao vaza para o Atendimento, e nao usa bloco que nao existe")
# ==========================================================================

i = FONTE_GRAPH.index("ferramentas_comerciais")
trecho = FONTE_GRAPH[max(0, i - 3000):i]
check("o registro esta DENTRO do bloco fechado por papel",
      '_agent_role or "core"' in trecho and '"core(legado)"' in trecho,
      "se sair desse if, o agente de atendimento recebe as tools")
check("e esta protegido por try/except (tool quebrada nao derruba o chat)",
      "relatórios comerciais não anexados" in FONTE_GRAPH)

# 🔴 SPEC-094 BLOCO F — a MESMA trava vale para a `executive_intelligence`.
#
# Ela le a carteira INTEIRA da corretora: producao, comissao, produtores,
# concentracao e exposicao de renovacao. Se ela escapar do `if` fechado por
# papel, o agente de ATENDIMENTO — que fala com o SEGURADO — passa a ter uma
# ferramenta que devolve o resultado financeiro da corretora. Nao e vazamento
# de dado pessoal: e pior, e vazamento do negocio para fora do negocio.
#
# Ela entra pela LISTA de `ferramentas_comerciais`, e nao por uma chamada nova
# em `graph.py`: assim ela herda o `if` que ja esta provado acima, em vez de
# depender de alguem lembrar de repetir a condicao.
check("a tool nova `executive_intelligence` existe",
      os.path.exists(os.path.join(RAIZ, "app", "agents", "tools",
                                  "executive_intelligence.py")))
check("ela entra pela LISTA de `ferramentas_comerciais` (herda o `if`)",
      "executive_intelligence" in FONTE[FONTE.rindex("def ferramentas_comerciais"):],
      "fora da lista, ela precisaria de uma chamada nova em graph.py — e a "
      "condicao de papel teria de ser repetida a mao")
check("e NAO ha uma segunda chamada dela em graph.py",
      "executive_intelligence" not in FONTE_GRAPH,
      "uma chamada direta em graph.py e onde a condicao de papel se perde")
check("CONTROLE: o detector acharia o nome no grafo se ele estivesse la",
      "ferramentas_comerciais" in FONTE_GRAPH,
      "se este controle falhar, a assercao acima passa por vacuidade")

# 🔴 SPEC-094.1 BLOCOS C e D — a MESMA trava, pelas MESMAS razoes.
#
# `listar_entregas` devolve o catalogo de pecas publicadas da corretora
# (titulos, links, `pack_id`); `propor_metrica` abre um Work Run com Approval
# em nome dela. Nenhuma das duas pode chegar ao agente de ATENDIMENTO, que fala
# com o SEGURADO. Elas entram pela LISTA de `ferramentas_comerciais` para
# herdar o `if` de papel ja provado acima — e nao por chamada nova em graph.py,
# que e onde a condicao se perde.
import re as _re

_LISTA_DE_TOOLS = FONTE[FONTE.rindex("def ferramentas_comerciais"):]
#: 🔴 SPEC-094.1: as tools novas, cada uma com a fabrica que a anexa. O BLOCO D
#: acrescenta a sua AQUI — e nao numa copia deste laco.
TOOLS_DA_094_1 = (("listar_entregas", "ferramenta_de_entregas"),)
for _nome, _fabrica in TOOLS_DA_094_1:
    _arq = os.path.join(RAIZ, "app", "agents", "tools", _nome + ".py")
    check(f"[094.1] a tool `{_nome}` existe", os.path.exists(_arq))
    check(f"[094.1] `{_nome}` entra pela LISTA de `ferramentas_comerciais`",
          _fabrica in _LISTA_DE_TOOLS,
          "fora da lista ela precisaria de uma chamada nova em graph.py")
    check(f"[094.1] e NAO ha uma segunda chamada de `{_nome}` em graph.py",
          _nome not in FONTE_GRAPH,
          "chamada direta em graph.py e onde a condicao de papel se perde")
    if not os.path.exists(_arq):
        continue
    _fonte_tool = open(_arq, encoding="utf-8").read()
    _arv = ast.parse(_fonte_tool)
    _cls = next((n for n in ast.walk(_arv) if isinstance(n, ast.ClassDef)
                 and n.name.endswith("Tool")), None)
    check(f"[094.1] {_nome} declara uma classe de tool", _cls is not None)
    if _cls is None:
        continue
    _corpo = ast.unparse(_cls)
    check(f"[094.1] {_nome} declara `exige_async`",
          any(isinstance(x, ast.AnnAssign)
              and getattr(x.target, "id", "") == "exige_async" for x in _cls.body),
          "sem isto o executor chama _run e a tool nunca roda")
    check(f"[094.1] {_nome} tem `_arun` async", "async def _arun" in _corpo)
    check(f"[094.1] {_nome}._run LEVANTA (nunca finge que funcionou)",
          "raise RuntimeError" in _corpo)
    check(f"[094.1] {_nome} roda o I/O em thread", "asyncio.to_thread" in _corpo)
    # 🔴 `company_id` OBRIGATORIO. O backend roda com service role: RLS sem
    # filtro no codigo nao protege nada (CLAUDE.md §7). A tool LEVANTA quando
    # nao ha corretora — nao devolve lista vazia, que esconderia o defeito.
    check(f"[094.1] {_nome} LEVANTA sem `company_id` (nao lista de todos)",
          "RecusaSemTenant" in _corpo,
          "sem tenant a consulta varreria todas as corretoras")

# 🔴 A listagem NUNCA devolve payload cru: ele carrega o `evidence_pack` e,
# no Pulso 360, `rotulos_de_produtor` — o unico lugar do produto onde o NOME de
# uma pessoa mora de proposito (mutacao M16 da 094).
_FONTE_ENTREGAS = open(os.path.join(RAIZ, "app", "agents", "tools",
                                    "listar_entregas.py"), encoding="utf-8").read()
_ARV_ENTREGAS = ast.parse(_FONTE_ENTREGAS)
_FICHA = next((n for n in ast.walk(_ARV_ENTREGAS)
               if isinstance(n, ast.FunctionDef) and n.name == "_ficha"), None)
check("[094.1] existe UM montador de ficha (`_ficha`)", _FICHA is not None)
if _FICHA is not None:
    _campos = set(_re.findall(r"""['"]([a-z_]+)['"]\s*:""", ast.unparse(_FICHA)))
    check("[094.1] a ficha NAO leva `payload`", "payload" not in _campos, sorted(_campos))
    check("[094.1] a ficha leva titulo, data, pack_id, link e status",
          {"titulo", "criado_em", "pack_id", "link", "status"} <= _campos,
          sorted(_campos))
    check("[094.1] CONTROLE: o detector de campos leu a ficha de verdade",
          len(_campos) >= 6, f"{len(_campos)} campos lidos")

# 🔴 O `payload` so pode ser TOCADO num lugar: a funcao que resolve o
# `pack_id`. A pergunta e feita sobre a ARVORE, e nao por `grep` no arquivo
# inteiro — um `grep` contaria a palavra na docstring que explica a regra e
# ficaria vermelho por causa da propria explicacao.
_QUEM_TOCA_PAYLOAD = sorted(
    n.name for n in ast.walk(_ARV_ENTREGAS)
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    and any(isinstance(x, ast.Constant) and x.value == "payload"
            for x in ast.walk(n)))
check("[094.1] SO `_packs_das_versoes` toca `payload`",
      _QUEM_TOCA_PAYLOAD == ["_packs_das_versoes"], _QUEM_TOCA_PAYLOAD)
check("[094.1] CONTROLE: o detector acha quem toca payload",
      len(_QUEM_TOCA_PAYLOAD) == 1, _QUEM_TOCA_PAYLOAD)
_RESOLVE = next((n for n in ast.walk(_ARV_ENTREGAS)
                 if isinstance(n, ast.FunctionDef)
                 and n.name == "_packs_das_versoes"), None)
check("[094.1] e ela devolve SO `{artifact_id: pack_id}`",
      _RESOLVE is not None and "saida[str(v.get('artifact_id'))] = ident"
      in ast.unparse(_RESOLVE),
      "se ela devolvesse a linha, o payload subiria junto")
check("[094.1] a listagem filtra por `company_id` nas DUAS consultas",
      "listar(company_id" in _FONTE_ENTREGAS
      and '.eq("company_id", company_id)' in _FONTE_ENTREGAS,
      "service role: o filtro no codigo e a protecao real (CLAUDE.md §7)")
check("[094.1] o link e o AUTENTICADO do dashboard (o mesmo `_link`)",
      "from app.agents.tools.relatorios_comerciais import _link" in _FONTE_ENTREGAS,
      "um segundo montador de link divergiria do primeiro (CLAUDE.md §5)")
check("[094.1] lista vazia devolve carimbo, e nao numero inventado",
      "ENTREGAS_VAZIO" in _FONTE_ENTREGAS
      and "NÃO invente entrega nenhuma" in _FONTE_ENTREGAS)
check("[094.1] CONTROLE: os tres carimbos de entrega sao distintos",
      len({"ENTREGAS_LISTADAS", "ENTREGAS_VAZIO", "ENTREGAS_FALHOU"}) == 3
      and all(c in _FONTE_ENTREGAS for c in ("ENTREGAS_LISTADAS",
                                             "ENTREGAS_VAZIO",
                                             "ENTREGAS_FALHOU")))

usados = set(ast.literal_eval(f'"{m}"') if False else m for m in [])
import re as _re
usados = set(_re.findall(r'"block":\s*"([a-z_]+)"', FONTE))
i2 = FONTE_BLOCKS.index("BLOCOS")
existem = set(_re.findall(r'["\']([a-z_]+)["\']\s*:', FONTE_BLOCKS[i2:i2 + 1200]))
check(f"os {len(usados)} blocos usados EXISTEM em blocks.py",
      usados <= existem, sorted(usados - existem))
check("CONTROLE: o detector de blocos realmente achou blocos",
      len(usados) >= 8 and len(existem) >= 15, f"{len(usados)} / {len(existem)}")

# 🔴 Nao alteramos nenhum arquivo compartilhado com a Cobranca.
#
# ⚠️ A BASELINE E A BASE DESTA SPEC, e ela foi MOVIDA em 03/09/2026 de `570359c`
# (a base da SPEC-081) para `b036b18` (a base da SPEC-094). O motivo e que uma
# baseline vencida faz a assercao medir a coisa errada: entre `570359c` e hoje
# passaram SPECs inteiras — a Cobranca, o Atendimento, o corredor — e o diff
# acusava cinco arquivos congelados "tocados" por trabalho legitimo de outras
# SPECs, que esta aqui nao fez. Um guarda que acusa sempre e um guarda que se
# aprende a ignorar (CLAUDE.md §9.3).
#
# 🔴 A licao NAO morreu: ela migrou de janela. A pergunta continua sendo *"ESTA
# SPEC tocou peca da Cobranca?"* — e agora a janela e a desta SPEC.
BASE_DA_SPEC_094 = "b036b18"
import subprocess
diff = subprocess.run(
    ["git", "diff", "--name-only", BASE_DA_SPEC_094, "HEAD"],
    cwd=os.path.dirname(RAIZ), capture_output=True, text=True).stdout
congelados = ["services/artifacts/blocks.py", "services/artifacts/charts.py",
              "services/artifacts/styles.py", "services/artifacts/render.py",
              "services/artifacts/service.py",
              "services/billing_collection.py", "services/dispatch_router.py",
              "tasks/dispatch_watchdog.py", "services/corridor_playbooks.py",
              "api/webhook.py"]
tocados = [c for c in congelados if c in diff]
check("NENHUM arquivo da Cobranca ou do Atendimento foi tocado",
      not tocados, tocados)
check("CONTROLE: o diff nao esta vazio (o teste sabe ler o git)",
      len(diff.strip()) > 0, "se vazio, a assercao acima nao prova nada")

# 🔴 `services/artifacts/templates.py` SAIU da lista acima em 03/09/2026, e a
# licao MIGROU em vez de morrer (CLAUDE.md §9.3).
#
# O congelamento nasceu na SPEC-081 com um proposito: as tools de relatorio
# nao podem mexer nas pecas da Cobranca. A SPEC-094 §4 acrescenta um template
# NOVO ao catalogo (`executive.pulse360`) — o arquivo muda de proposito, e
# manter a afirmacao vencida so ensinaria a ignorar este teste.
#
# O que continua guardado e o que importava: o catalogo so CRESCE. Se alguem
# apagar, renomear ou reescrever a chave de um template que ja existia, esta
# assercao fica vermelha — e as pecas da Cobranca dependem exatamente disso
# (`artifacts.template_key` e FK para `report_templates`).
_TEMPLATES = _re.findall(r'key="([a-z_]+\.[a-z_0-9]+)"',
                         _fonte_templates := open(
                             os.path.join(RAIZ, "app", "services", "artifacts",
                                          "templates.py"),
                             encoding="utf-8").read())
_ANTES_DA_094 = {
    "executive.panorama", "financial.commissions", "commercial.pipeline",
    "research.market_brief", "portfolio.client_dossier", "renewals.radar",
    "claims.performance", "briefing.daily", "briefing.daily_operational",
    "briefing.weekly_executive", "briefing.critical_alert_detail",
    "briefing.opportunity_dossier", "briefing.demand_radar_admin",
    "research.evidence_pack", "research.competitor_matrix",
    "research.site_audit", "research.regulatory_radar",
    "research.company_list", "research.change_report",
    "financial.billing_collection"}
_sumiram = sorted(_ANTES_DA_094 - set(_TEMPLATES))
check("os 20 templates ANTERIORES a 094 continuam todos no catalogo",
      not _sumiram, _sumiram)
check("CONTROLE: o detector leu o catalogo de verdade",
      len(_TEMPLATES) >= 21, f"{len(_TEMPLATES)} chaves lidas")

# ==========================================================================
print("\n[4] O que protege o segurado e a verdade")
# ==========================================================================

check("a peca do Radar NAO leva telefone nem CPF",
      "SEM telefone e SEM CPF" in FONTE and '"telefone"' not in
      FONTE[FONTE.index("Os quinze mais urgentes"):FONTE.index("Os quinze mais urgentes") + 900])
check("a cobertura vai IMPRESSA na peca do Raio-X",
      "cob.frase()" in FONTE and "O que este relatório cobre" in FONTE)
check("o rotulo do grafico e ENCURTADO (charts.py nao trunca)",
      "def _encurtar(" in FONTE and "_encurtar(" in FONTE.split("def _encurtar")[1])
check("a hora vai DENTRO do as_of_label (blocks.py mostra o label)",
      'f"consultado em {quando}"' in FONTE)
check("CONTROLE: e nao ficou so no as_of invisivel",
      '"as_of_label"' in FONTE)
check("o veredito e DETERMINISTICO (sai dos numeros, nao do LLM)",
      "def _veredito(" in FONTE and "@staticmethod" in FONTE)

# ==========================================================================
if os.getenv("SEM_REDE"):
    print("\n[5] PULADO — SEM_REDE=1")
    print("\n" + "=" * 68)
    print(f"  {PASS} assercoes verdes - {FAIL} vermelhas  (rede PULADA)")
    print("=" * 68)
    sys.exit(1 if FAIL else 0)

print("\n[5] PONTA A PONTA — gera artifact de verdade, e confere no banco")
# ==========================================================================

import asyncio
import json
import urllib.request

SUPA_URL = os.getenv("SUPABASE_URL", "")
SUPA_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY", "")
EMPRESA = os.getenv("EMPRESA_DE_TESTE", "04b5cdbc-04cd-4ddf-8e4b-f43efb062fab")

if not (SUPA_URL and SUPA_KEY):
    print("  (sem credencial de Supabase no ambiente — bloco [5] nao rodou)")
    print("\n" + "=" * 68)
    print(f"  {PASS} assercoes verdes - {FAIL} vermelhas  (ponta a ponta PULADO)")
    print("=" * 68)
    sys.exit(1 if FAIL else 0)


def _sql(q: str):
    req = urllib.request.Request(
        f"{SUPA_URL}/rest/v1/rpc/exec_sql",
        data=json.dumps({"q": q}).encode(),
        headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def _conta_artifacts_chat() -> int:
    req = urllib.request.Request(
        f"{SUPA_URL}/rest/v1/artifacts?select=id&origin=eq.chat&company_id=eq.{EMPRESA}",
        headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}",
                 "Prefer": "count=exact"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return len(json.loads(r.read()))


from supabase import create_client  # noqa: E402

cliente = create_client(SUPA_URL, SUPA_KEY)
antes = _conta_artifacts_chat()
print(f"  (artifacts com origin='chat' antes: {antes})")

# 🔴 Um `app.services` LEVE, registrado ANTES de qualquer import.
#
# 📊 `app/services/__init__.py` importa EAGER toda a arvore: `audio_service`
# puxa o SDK da OpenAI, `document_service` puxa `python-docx`,
# `ingestion_service` puxa `fastembed` (que arrasta a stack de ML inteira).
# Numa maquina de teste isso e impraticavel.
#
# O truque registra um modulo vazio com o `__path__` certo: os SUBMODULOS
# reais continuam sendo encontrados e executados — `artifacts/service.py`,
# `render.py`, `blocks.py`, `charts.py` sao os de producao, linha por linha.
# So o `__init__` agregador nao roda, e ele nao contem logica nenhuma.
#
# Nao e stub do que esta sendo testado. E stub do que esta no CAMINHO.
import types as _types

if 'app.services' not in sys.modules:
    import app as _app  # noqa: F401
    _leve = _types.ModuleType('app.services')
    _leve.__path__ = [os.path.join(RAIZ, 'app', 'services')]
    sys.modules['app.services'] = _leve

# 🔴 Carrega o modulo POR CAMINHO. `import app.agents.tools...` dispara o
# `app/agents/__init__.py`, que importa `graph.py`, que importa `langgraph` —
# ausente nesta maquina. O modulo em si so precisa de `langchain_core`, que
# esta instalado. Importar pelo pacote testaria a arvore de dependencias do
# grafo, nao as duas ferramentas.
_sp = importlib.util.spec_from_file_location('relatorios_comerciais_isolado', ALVO)
_rc = importlib.util.module_from_spec(_sp)
sys.modules[_sp.name] = _rc
_sp.loader.exec_module(_rc)
RaioXComercialTool = _rc.RaioXComercialTool
RadarDeRenovacoesTool = _rc.RadarDeRenovacoesTool

# 🔴 O DEFEITO QUE ESTE TESTE NAO PEGOU, E AGORA PEGA — 18/08/2026.
#
# As tools falharam na frente do Founder com
#   AttributeError: 'SupabaseClient' object has no attribute 'table'
# depois de 67 assercoes verdes.
#
# 📊 `graph.py:266` faz `real = getattr(supabase_client, 'client',
# supabase_client)` e o comentario dele diz "tools usam .table()
# diretamente" — ou seja, o que chega no grafo e um INVOLUCRO. Eu passei o
# involucro para as tools.
#
# E o teste nao viu porque construia o cliente com `create_client()`, que ja
# vem DESEMBRULHADO. Ele exercitava uma forma que o grafo nunca passa.
#
# Agora exercita AS DUAS.

class _Involucro:
    """O que o grafo realmente entrega: um objeto com `.client` dentro."""

    def __init__(self, real):
        self.client = real


for _rotulo, _cli in (('desembrulhado', cliente), ('INVOLUCRO (o do grafo)', _Involucro(cliente))):
    _tools = _rc.ferramentas_comerciais(company_id=EMPRESA, supabase=_cli)
    check(f'a fabrica devolve as duas tools com o cliente {_rotulo}',
          len(_tools) == 2, len(_tools))
    for _t in _tools:
        check(f'{_t.name} sabe usar .table() com o cliente {_rotulo}',
              hasattr(_t.supabase, 'table'),
              'sem isto: AttributeError no primeiro uso real')

# CONTROLE: o involucro REALMENTE nao tem `.table` — senao o teste acima
# passaria sem provar nada.
check('CONTROLE: o involucro cru nao tem .table (o defeito era real)',
      not hasattr(_Involucro(cliente), 'table'))
check('CONTROLE: e o cliente de dentro tem', hasattr(cliente, 'table'))

raio = RaioXComercialTool(company_id=EMPRESA, supabase=cliente)
resp = asyncio.run(raio._arun(periodo="2025"))
check("o Raio-X devolveu RELATORIO_PRONTO", "RELATORIO_PRONTO" in resp, resp[:200])
check("e devolveu um link de /dashboard/entregas", "/dashboard/entregas/" in resp,
      resp[:200])

radar = RadarDeRenovacoesTool(company_id=EMPRESA, supabase=cliente)
resp2 = asyncio.run(radar._arun(periodo="proximos 90 dias"))
check("o Radar devolveu RELATORIO_PRONTO", "RELATORIO_PRONTO" in resp2, resp2[:200])
check("e devolveu um link", "/dashboard/entregas/" in resp2, resp2[:200])

depois = _conta_artifacts_chat()
check("nasceram DOIS artifacts com origin='chat' (a linha que nunca existiu)",
      depois - antes == 2, f"antes {antes}, depois {depois}")

# ==========================================================================
print("\n[6] A PECA RENDERIZADA esta correta, e nao vazou nada")
# ==========================================================================
#
# 🔴 Nao basta o artifact existir. Uma peca que nasce vazia, sem grafico, ou
# com o telefone do segurado dentro, e pior que peca nenhuma -- porque
# PARECE pronta e vai para a tela de uma apresentacao.

import urllib.parse as _up

def _html_das_ultimas(n=2):
    q = (f'{SUPA_URL}/rest/v1/artifacts?select=title,artifact_versions'
         f'(artifact_renders(inline_content))&origin=eq.chat'
         f'&company_id=eq.{EMPRESA}&order=created_at.desc&limit={n}')
    req = urllib.request.Request(q, headers={'apikey': SUPA_KEY,
                                             'Authorization': f'Bearer {SUPA_KEY}'})
    with urllib.request.urlopen(req, timeout=60) as r:
        linhas = json.loads(r.read())
    saida = []
    for x in linhas:
        for v in (x.get('artifact_versions') or []):
            for rr in (v.get('artifact_renders') or []):
                saida.append((x.get('title'), rr.get('inline_content') or ''))
    return saida

import re as _re2
for _titulo, _html in _html_das_ultimas(2):
    rot = str(_titulo)[:26]
    check(f'{rot}: a peca tem corpo (>15 KB)', len(_html) > 15000, len(_html))
    check(f'{rot}: tem grafico SVG renderizado', '<svg' in _html)

    # 🔴 A ASSERCAO QUE FALTAVA, e que teria poupado tres pecas publicadas.
    #
    # 📊 A primeira versao saiu com SETE caixas 'Sem dado no periodo' e ZERO
    # barras. Todos os numeros estavam calculados e certos; morriam na
    # renderizacao, porque eu passava `highlight` onde o bloco le
    # `headline_value`, `points` onde ele le `values`, `label/value` onde ele
    # le `rotulo/valor`.
    #
    # E 32 assercoes verdes nao pegaram: elas conferiam que o NOME do bloco
    # existia em `blocks.py`, nunca as propriedades DENTRO dele. Nome certo com
    # propriedade errada renderiza uma caixa vazia -- e caixa vazia num
    # projetor e pior que bloco nenhum.
    _vazias = _html.count('Sem dado')
    check(f'{rot}: ZERO caixas "Sem dado no periodo"', _vazias == 0, _vazias)

    # Geometria de verdade: barra de ranking (`rect`) ou fatia de rosca
    # (`path` com `d=`). Contar `<svg` nao basta -- a caixa vazia tambem tem
    # um `<svg` de icone dentro.
    # Cada elemento com o SEU detector. `<svg` sozinho nao basta: a caixa
    # 'Sem dado' tambem tem um `<svg` de icone dentro.
    _ranking = _html.count('ab-rank-row')      # o ranking e HTML+CSS
    _rosca = _html.count('stroke-dasharray')   # a rosca e SVG
    _kpi = _html.count('ab-kpi')
    _tabela = _html.count('<tr')
    check(f'{rot}: o RANKING tem linhas', _ranking >= 5, _ranking)
    check(f'{rot}: a ROSCA tem fatias', _rosca >= 2, _rosca)
    check(f'{rot}: os CARTOES de KPI existem', _kpi >= 4, _kpi)
    check(f'{rot}: as TABELAS tem linhas', _tabela >= 5, _tabela)
    check(f'{rot}: a CAPA traz o numero de destaque',
          ' mi' in _html or ' mil' in _html,
          'headline_value vazio deixa a capa sem o numero')

    # CONTROLE: o contador de caixas vazias CONSEGUE contar.
    check(f'{rot}: CONTROLE: o detector de caixa vazia funciona',
          'x Sem dado y'.count('Sem dado') == 1)
    check(f'{rot}: traz o nome da corretora', 'Resulta' in _html)
    check(f'{rot}: traz a hora da consulta', 'consultado em' in _html)
    # 🔴 PII: procura o PADRAO, nao a palavra. O rodape honesto diz
    # 'Nao contem CPF/CNPJ' e casaria uma busca por texto.
    check(f'{rot}: ZERO CPF formatado',
          not _re2.search(r'\d{3}[.]\d{3}[.]\d{3}-\d{2}', _html))
    check(f'{rot}: ZERO telefone formatado',
          not _re2.search(r'\(\d{2}\)\s?9?\d{4}-\d{4}', _html))
    # CONTROLE: o detector de PII CONSEGUE achar quando ha.
    check(f'{rot}: CONTROLE: o detector acha CPF num texto que tem um',
          bool(_re2.search(r'\d{3}[.]\d{3}[.]\d{3}-\d{2}', 'cpf 123.456.789-00 aqui')))

_raio = [h for t, h in _html_das_ultimas(2) if 'Raio-X' in str(t)]
if _raio:
    check('o Raio-X imprime a COBERTURA em numero',
          '80,6' in _raio[0] or '80.6' in _raio[0],
          'relatorio que soma parte e se diz o todo mente por omissao')
    check('e traz o insight do ticket alto (MARCOS TONIOLO)',
          'TONIOLO' in _raio[0])

print("\n" + "=" * 68)
print(f"  {PASS} assercoes verdes - {FAIL} vermelhas")
print("=" * 68)
sys.exit(1 if FAIL else 0)
