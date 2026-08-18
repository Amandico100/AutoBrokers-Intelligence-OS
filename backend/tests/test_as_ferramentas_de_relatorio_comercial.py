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
import subprocess
diff = subprocess.run(
    ["git", "diff", "--name-only", "570359c", "HEAD"],
    cwd=os.path.dirname(RAIZ), capture_output=True, text=True).stdout
congelados = ["services/artifacts/blocks.py", "services/artifacts/charts.py",
              "services/artifacts/styles.py", "services/artifacts/render.py",
              "services/artifacts/service.py", "services/artifacts/templates.py",
              "services/billing_collection.py", "services/dispatch_router.py",
              "tasks/dispatch_watchdog.py", "services/corridor_playbooks.py",
              "api/webhook.py"]
tocados = [c for c in congelados if c in diff]
check("NENHUM arquivo da Cobranca ou do Atendimento foi tocado",
      not tocados, tocados)
check("CONTROLE: o diff nao esta vazio (o teste sabe ler o git)",
      len(diff.strip()) > 0, "se vazio, a assercao acima nao prova nada")

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

print("\n" + "=" * 68)
print(f"  {PASS} assercoes verdes - {FAIL} vermelhas")
print("=" * 68)
sys.exit(1 if FAIL else 0)
