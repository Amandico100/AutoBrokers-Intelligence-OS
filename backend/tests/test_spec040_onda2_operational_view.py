# -*- coding: utf-8 -*-
"""SPEC-040 Onda 2 - Visao Operacional do Core + seed do conhecimento global.

Cobre: resumo_atendimentos deterministico (ativos + movimento + qualidade,
escopo por corretora), atlas_rotas (lista geral, detalhe, caminho ate servico),
tools do Core (nomes/fiacao no graph), seed global idempotente por hash e o
default ligado da busca global. Standalone (stubs, sem pytest).
"""

import asyncio
import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASS = FAIL = 0
FAILURES = []


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  [ok] {name}")
    else:
        FAIL += 1
        FAILURES.append((name, detail))
        print(f"  [X] {name}{': ' + str(detail) if detail else ''}")


def _load(dotted, rel):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(dotted, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = mod
    spec.loader.exec_module(mod)
    return mod


# ------------------------- stubs -------------------------
class _Result:
    def __init__(self, data=None):
        self.data = data or []


class _Table:
    def __init__(self, store, name):
        self.store, self.name = store, name
        self._eq = []
        self._gte = []
        self._lte = []
        self._in = []
        self._order = None
        self._desc = True
        self._limit = None

    def select(self, *_a, **_k): return self
    def eq(self, col, val): self._eq.append((col, val)); return self
    def gte(self, col, val): self._gte.append((col, val)); return self

    # SPEC-090 BLOCO D: `operations_summary` passou a FECHAR a janela dos dois
    # lados. Sem `lte` aqui, a cadeia levantava AttributeError, o `except` do
    # servico engolia, e DUAS secoes deste guarda sumiam da saida --
    # "movimento do periodo" e "qualidade". O fato mudou, o stub muda com ele.
    def lte(self, col, val): self._lte.append((col, val)); return self
    def in_(self, col, vals): self._in.append((col, list(vals))); return self

    def order(self, col, desc=True):
        self._order, self._desc = col, desc
        return self

    def limit(self, n): self._limit = n; return self

    def execute(self):
        rows = list(self.store.get(self.name, []))
        for col, val in self._eq:
            rows = [r for r in rows if str(r.get(col)) == str(val)]
        for col, val in self._gte:
            rows = [r for r in rows if str(r.get(col) or "") >= str(val)]
        for col, val in self._lte:
            rows = [r for r in rows if str(r.get(col) or "") <= str(val)]
        for col, vals in self._in:
            rows = [r for r in rows if r.get(col) in vals]
        if self._order:
            rows.sort(key=lambda r: str(r.get(self._order) or ""), reverse=self._desc)
        if self._limit:
            rows = rows[: self._limit]
        return _Result(rows)


class _SupabaseClient:
    def __init__(self, store):
        self.client = self
        self._store = store

    def table(self, name):
        return _Table(self._store, name)


class _Redis:
    def __init__(self):
        self.kv = {}

    async def set(self, key, val, ex=None): self.kv[key] = val
    async def get(self, key): return self.kv.get(key)


class _QdrantRec:
    def __init__(self):
        self.deleted = []
        self.inserted = []

    def delete_document(self, company_id, document_id, collection_name=None):
        self.deleted.append((company_id, document_id, collection_name))
        return True

    def insert_embeddings(self, **kw):
        self.inserted.append(kw)
        return True


def _bootstrap():
    store, redis, qdrant = {}, _Redis(), _QdrantRec()
    for name in ("app", "app.core", "app.services", "app.services.atlas"):
        m = sys.modules.setdefault(name, types.ModuleType(name))
        m.__path__ = []

    db = types.ModuleType("app.core.database")
    db.get_supabase_client = lambda: _SupabaseClient(store)
    sys.modules["app.core.database"] = db

    red = types.ModuleType("app.core.redis")

    async def _get_redis():
        return redis

    red.get_async_redis_client = _get_redis
    sys.modules["app.core.redis"] = red

    cfg = types.ModuleType("app.core.config")
    cfg.settings = types.SimpleNamespace(OPENAI_API_KEY="test-key")
    sys.modules["app.core.config"] = cfg

    # registry real (puro); observer_intake stub minimo (so o que a view usa)
    _load("app.services.insurer_registry", "app/services/insurer_registry.py")
    obs = types.ModuleType("app.services.atlas.observer_intake")
    obs._digits = lambda v: "".join(ch for ch in str(v or "") if ch.isdigit())
    obs.insurer_allowlist = lambda: {"551140901444": "allianz", "551130039303": "porto"}
    sys.modules["app.services.atlas.observer_intake"] = obs

    # dispatch_router stub (sessoes ativas canned)
    dr = types.ModuleType("app.services.dispatch_router")
    dr._active = []

    async def _list(company_id):
        return [s for s in dr._active if s.get("_company") == company_id]

    dr.list_active_dispatches = _list
    sys.modules["app.services.dispatch_router"] = dr

    # splitters/embeddings/fastembed stubs p/ o seed
    lts = types.ModuleType("langchain_text_splitters")

    class _Splitter:
        def __init__(self, chunk_size=1000, chunk_overlap=200, separators=None):
            self.n = chunk_size

        def create_documents(self, texts):
            out = []
            for t in texts:
                parts = [p for p in t.split("\n\n") if p.strip()]
                out.extend(types.SimpleNamespace(page_content=p[: self.n]) for p in parts)
            return out

    lts.RecursiveCharacterTextSplitter = _Splitter
    sys.modules["langchain_text_splitters"] = lts

    lco = types.ModuleType("langchain_openai")

    class _Emb:
        def __init__(self, **_k): pass

        def embed_documents(self, chunks):
            return [[0.1, 0.2, 0.3] for _ in chunks]

    lco.OpenAIEmbeddings = _Emb
    sys.modules["langchain_openai"] = lco

    fe = types.ModuleType("fastembed")

    class _Sparse:
        def __init__(self, **_k): pass

        def embed(self, chunks):
            return [None for _ in chunks]

    fe.SparseTextEmbedding = _Sparse
    sys.modules["fastembed"] = fe

    qd = types.ModuleType("app.services.qdrant_service")
    qd.get_qdrant_service = lambda: qdrant
    sys.modules["app.services.qdrant_service"] = qd

    # langchain.tools stub (BaseTool puro — pydantic real esta instalado)
    if "langchain.tools" not in sys.modules:
        lc = sys.modules.setdefault("langchain", types.ModuleType("langchain"))
        lc.__path__ = []
        lct = types.ModuleType("langchain.tools")

        class _BaseTool:
            def __init__(self, **kw):
                for k, v in kw.items():
                    setattr(self, k, v)

        lct.BaseTool = _BaseTool
        sys.modules["langchain.tools"] = lct

    _load("app.services.knowledge_scope", "app/services/knowledge_scope.py")
    view = _load("app.services.operational_view", "app/services/operational_view.py")
    seed = _load("app.services.global_knowledge_seed", "app/services/global_knowledge_seed.py")
    tools = _load("app.agents.tools.operations_tools", "app/agents/tools/operations_tools.py")
    return view, seed, tools, store, redis, qdrant, dr


def run():
    print("== SPEC-040 Onda 2 - Visao Operacional + seed global ==\n")
    try:
        view, seed, tools, store, redis, qdrant, dr = _bootstrap()
    except Exception as e:
        # langchain.tools pode nao existir no ambiente local de teste
        import traceback
        traceback.print_exc()
        check("bootstrap", False, f"{type(e).__name__}: {e}")
        print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
        sys.exit(1)

    # ---------- resumo_atendimentos ----------
    dr._active = [{"_company": "c1", "insurer_phone": "551140901444", "state": "monitoring",
                   "subservice": "guincho", "captured": {"protocol": "9791688"},
                   "transcript": [], "created_at": "2026-07-19T12:00:00+00:00"},
                  {"_company": "c2", "insurer_phone": "551130039303", "state": "ura",
                   "captured": {}, "transcript": [], "created_at": "2026-07-19T12:05:00+00:00"}]
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    store["agent_activities"] = [
        {"company_id": "c1", "category": "acionamentos", "title": "Acionamento iniciado — Allianz", "created_at": now},
        {"company_id": "c1", "category": "acionamentos", "title": "Protocolo garantido — Allianz", "created_at": now},
        {"company_id": "c2", "category": "acionamentos", "title": "Acionamento iniciado — Porto", "created_at": now},
    ]
    store["conversation_scorecards"] = [
        {"company_id": "c1", "score": 90, "created_at": now},
        {"company_id": "c1", "score": 70, "created_at": now},
    ]

    out = asyncio.run(view.operations_summary("c1", "hoje"))
    check("resumo: acionamento ativo com seguradora e protocolo",
          "Allianz" in out and "9791688" in out and "monitorando" in out, out[:300])
    check("resumo: NAO vaza outra corretora (c2/Porto ativo fora)",
          "Porto" not in out.split("MOVIMENTO")[0], out[:300])
    check("resumo: movimento do periodo com contagens",
          "1 acionamentos iniciados" in out and "1 com protocolo" in out, out)
    check("resumo: qualidade media", "80/100" in out, out)

    out_empty = asyncio.run(view.operations_summary("c3", "hoje"))
    check("resumo vazio: mensagem honesta", "nenhum" in out_empty.lower(), out_empty[:200])

    # ---------- SPEC-090 BLOCO D: `ontem` e' um periodo DE VERDADE ----------
    #
    # 🔴 A LICAO MIGRA, em vez de o stub so' tolerar o metodo novo (§9.3).
    #
    # 📊 Medido em 26/08: `periodo="ontem"` caia no `else` e devolvia "ultimas
    # 24h" -- que as 10h de terca cobre metade de segunda e metade de terca. O
    # Founder perguntava "o que aconteceu ontem?" e recebia OUTRA resposta,
    # apresentada como se fosse a que ele pediu.
    from datetime import timedelta
    _hoje = datetime.now(timezone.utc)
    _ontem_iso = (_hoje - timedelta(days=1)).replace(
        hour=12, minute=0, second=0, microsecond=0).isoformat()
    store["agent_activities"].append(
        {"company_id": "c1", "category": "acionamentos",
         "title": "Acionamento iniciado — Zurich (ONTEM)", "created_at": _ontem_iso})

    out_ontem = asyncio.run(view.operations_summary("c1", "ontem"))
    check("ontem: o rotulo diz ONTEM, com a data e o fuso",
          "ontem (" in out_ontem and "UTC)" in out_ontem, out_ontem[:200])
    check("ontem: pega o que aconteceu ONTEM",
          "Zurich" in out_ontem, out_ontem[:400])

    # ⛔ E A JANELA FECHA DOS DOIS LADOS. Sem o `lte`, as atividades de HOJE
    #    entrariam no relatorio de ontem e o numero sairia maior que o dia.
    check("ontem: NAO inclui o que aconteceu HOJE",
          "Allianz" not in out_ontem.split("MOVIMENTO")[-1], out_ontem)

    # 🔴 LINHA DE CONTROLE -- e ela ja' corrigiu uma afirmacao MINHA.
    #
    # ⚠️ Escrevi primeiro que `hoje` NAO pegaria a atividade de ontem ao
    # meio-dia. Falso: "hoje" e' janela DESLIZANTE de 24h, entao as 07h52 ela
    # alcanca legitimamente as 12h de ontem. O guarda apontou, e quem estava
    # errado era a assercao, nao o codigo.
    #
    # O que a linha de controle PRECISA provar e' que as duas janelas sao
    # diferentes -- e o lado que distingue e' o AGORA: `hoje` alcanca o que
    # acabou de acontecer; `ontem`, nao.
    out_hoje = asyncio.run(view.operations_summary("c1", "hoje"))
    check("CONTROLE: `hoje` e' janela deslizante e alcanca o AGORA",
          "últimas 24h" in out_hoje and "Allianz" in out_hoje, out_hoje[:400])
    check("CONTROLE: os dois rotulos sao DIFERENTES",
          out_hoje.splitlines()[0] != out_ontem.splitlines()[0],
          out_hoje.splitlines()[0] + " || " + out_ontem.splitlines()[0])

    # ---------- atlas_rotas ----------
    mapa = {
        "root": "n1",
        "nodes": {
            "n1": {"text": "Ola! Sou a assistencia. O que voce precisa?",
                   "options": [{"label": "Guincho"}, {"label": "Bateria"}]},
            "n2": {"text": "Certo, guincho. Qual o endereco do veiculo?", "options": []},
        },
        "edges": {"e1": {"src": "n1", "label": "Guincho", "to": "n2"}},
        "coverage": {"pct": 50, "nodes": 2},
    }
    store["ura_maps"] = [
        {"insurer_key": "porto", "ramo": "auto", "status": "observed", "map": mapa,
         "diff_summary": "2 telas, cobertura 50%", "created_at": "2026-07-18T00:00:00+00:00"},
        {"insurer_key": "allianz", "ramo": "auto", "status": "active", "map": mapa,
         "diff_summary": "2 telas", "created_at": "2026-07-17T00:00:00+00:00"},
    ]

    out_list = asyncio.run(view.atlas_routes_summary())
    check("atlas lista: seguradoras com cobertura",
          "Porto" in out_list and "Allianz" in out_list and "50%" in out_list, out_list)

    out_det = asyncio.run(view.atlas_routes_summary("porto", None, "guincho"))
    check("atlas detalhe: entrada + opcoes", "ENTRADA:" in out_det and "Guincho" in out_det, out_det)
    check("atlas caminho: passo a passo ate o servico",
          "CAMINHO" in out_det and 'responder "Guincho"' in out_det, out_det)
    check("atlas: sem dado de cliente (aviso)", "sem nenhum dado de cliente" in out_det, out_det)

    out_none = asyncio.run(view.atlas_routes_summary("zurich"))
    check("atlas sem mapa: mensagem honesta", "não há mapa" in out_none or "nao ha mapa" in out_none, out_none)

    # ---------- tools do Core ----------
    t1 = tools.OperationsSummaryTool(company_id="c1")
    t2 = tools.AtlasRoutesTool()
    check("tool resumo_atendimentos nomeada", t1.name == "resumo_atendimentos")
    check("tool atlas_rotas nomeada", t2.name == "atlas_rotas")
    r1 = asyncio.run(t1._arun("hoje"))
    check("tool resumo executa com escopo da corretora", "Allianz" in r1, r1[:200])
    r2 = asyncio.run(t2._arun("porto", None, "guincho"))
    check("tool atlas executa", "CAMINHO" in r2, r2[:200])

    # fiacao no graph (core) + default da busca global ligado
    graph_src = (ROOT / "app/agents/graph.py").read_text(encoding="utf-8")
    check("graph: tools de visao operacional no papel core",
          "OperationsSummaryTool(company_id" in graph_src and "AtlasRoutesTool()" in graph_src)
    search_src = (ROOT / "app/services/search_service.py").read_text(encoding="utf-8")
    check("busca global: default LIGADO", 'KNOWLEDGE_GLOBAL_SEARCH", "1"' in search_src)

    # ---------- seed do conhecimento global ----------
    n1 = asyncio.run(seed.check_global_seed())
    check("seed: ingeriu os canonicos na 1a rodada", n1 > 0 and len(qdrant.inserted) >= 1,
          {"chunks": n1, "inserted": len(qdrant.inserted)})
    if qdrant.inserted:
        kw = qdrant.inserted[0]
        check("seed: colecao global + escopo publicado",
              kw.get("collection_name") == "autobrokers_global"
              and (kw.get("knowledge_extras") or {}).get("scope") == "global_autobrokers"
              and (kw.get("knowledge_extras") or {}).get("curation_status") == "published", kw.get("knowledge_extras"))
        check("seed: substitui versao anterior (delete antes)", len(qdrant.deleted) >= 1)
    n2 = asyncio.run(seed.check_global_seed())
    check("seed idempotente: 2a rodada nao re-ingere", n2 == 0, n2)

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  - {n}: {d}")
        sys.exit(1)


if __name__ == "__main__":
    run()
