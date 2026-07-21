# -*- coding: utf-8 -*-
"""SPEC-044 - Tres Camadas: Global / Corretora / Usuario.

Cobre: escopo personal no knowledge_scope (kwargs de busca pessoal + payload),
rotinas com dono (create personal por padrao no chat, list filtra, manage nao
enxerga pessoal de terceiro), oauth store com owner (corretora e pessoal
coexistem), contexto de requisicao (ContextVar) e blindagens por source-check
(busca padrao exclui personal; injecao por execucao no tool_node; rotas Next).
Standalone (stubs, sem pytest).
"""

import asyncio
import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT.parent
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


class _Result:
    def __init__(self, data=None):
        self.data = data or []


class _Table:
    def __init__(self, store, name):
        self.store, self.name = store, name
        self._mode = None
        self._payload = None
        self._eq = []
        self._neq = []
        self._is = []

    def select(self, *_a, **_k): self._mode = "select"; return self
    def insert(self, payload): self._mode = "insert"; self._payload = payload; return self
    def update(self, payload): self._mode = "update"; self._payload = payload; return self
    def delete(self): self._mode = "delete"; return self
    def eq(self, col, val): self._eq.append((col, val)); return self
    def neq(self, col, val): self._neq.append((col, val)); return self
    def is_(self, col, val): self._is.append((col, val)); return self
    def order(self, *_a, **_k): return self
    def limit(self, *_a): return self

    def _rows(self):
        rows = list(self.store.get(self.name, []))
        for col, val in self._eq:
            rows = [r for r in rows if str(r.get(col)) == str(val)]
        for col, val in self._neq:
            rows = [r for r in rows if str(r.get(col)) != str(val)]
        for col, val in self._is:
            if val == "null":
                rows = [r for r in rows if r.get(col) is None]
        return rows

    def execute(self):
        self.store.setdefault(self.name, [])
        if self._mode == "insert":
            row = dict(self._payload)
            row.setdefault("id", f"{self.name}-{len(self.store[self.name]) + 1}")
            self.store[self.name].append(row)
            return _Result([row])
        if self._mode == "update":
            hit = self._rows()
            for r in hit:
                r.update(self._payload)
            return _Result(hit)
        if self._mode == "delete":
            hit = self._rows()
            ids = {id(r) for r in hit}
            self.store[self.name] = [r for r in self.store[self.name] if id(r) not in ids]
            return _Result(hit)
        return _Result(self._rows())


class _AsyncTable(_Table):
    async def execute(self):  # type: ignore[override]
        return _Table.execute(self)


class _Supabase:
    def __init__(self, store, is_async=False):
        self.client = self
        self._store = store
        self._async = is_async

    def table(self, name):
        return (_AsyncTable if self._async else _Table)(self._store, name)


def run():
    print("== SPEC-044 - Tres Camadas ==\n")

    # ---------- 1) knowledge_scope: escopo pessoal ----------
    ks = _load("app.services.knowledge_scope", "app/services/knowledge_scope.py")
    check("SCOPE_PERSONAL e valido", ks.SCOPE_PERSONAL == "personal" and "personal" in ks.VALID_SCOPES)
    kw = ks.build_personal_search_kwargs("user-1")
    check("busca pessoal: scope=personal travado no dono",
          kw["scope_match"] == ["personal"] and kw["owner_user_id"] == "user-1"
          and kw["agent_id"] is None and kw["include_tenant_wide"] is False, kw)
    extras = ks.extract_payload_extras({"scope": "personal", "owner_user_id": "user-1"}, None)
    check("payload do Qdrant carrega o dono", extras.get("owner_user_id") == "user-1"
          and extras.get("scope") == "personal", extras)

    # ---------- 2) request_context: identidade por requisicao ----------
    rc = _load("app.core.request_context", "app/core/request_context.py")
    rc.set_current_user_id("u-abc")
    check("contextvar guarda o usuario da requisicao", rc.get_current_user_id() == "u-abc")
    rc.set_current_user_id(None)
    check("contextvar limpa", rc.get_current_user_id() is None)

    # ---------- 3) rotinas com dono ----------
    for name in ("app", "app.core", "app.services", "app.agents", "app.agents.tools"):
        m = sys.modules.setdefault(name, types.ModuleType(name))
        m.__path__ = []
    # stubs p/ routine_tools (langchain_core real esta instalado? nao — stub)
    lct = types.ModuleType("langchain_core.tools")

    class _BT:
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

    lct.BaseTool = _BT
    lc = sys.modules.setdefault("langchain_core", types.ModuleType("langchain_core"))
    lc.__path__ = []
    sys.modules["langchain_core.tools"] = lct
    import datetime as _dt

    eng = types.ModuleType("app.services.routine_engine")
    eng.validate_schedule = lambda s: (True, "")
    eng.compute_next_run = lambda s, tz: _dt.datetime(2026, 7, 21, 12, 0, tzinfo=_dt.timezone.utc)
    eng.describe_missing_dependency = lambda ch, has: None
    eng._tz = lambda name: _dt.timezone.utc
    sys.modules["app.services.routine_engine"] = eng

    rt = _load("app.agents.tools.routine_tools", "app/agents/tools/routine_tools.py")
    store = {"integrations": [{"id": "i1", "company_id": "c1", "is_active": True}]}
    db = _Supabase(store)

    create = rt.CreateRoutineTool(company_id="c1", supabase_client=db)
    out = create._run(name="Relatorio de sexta", instructions="Envie o relatorio semanal de vendas",
                      schedule_kind="daily", time_of_day="08:00",
                      delivery_channel="whatsapp", delivery_number="5547999998888",
                      user_id="u-joao")
    r = store["routines"][0]
    check("rotina criada NO CHAT e PESSOAL do autor",
          r["visibility"] == "personal" and r["created_by"] == "u-joao", r)
    check("criacao confirma em linguagem humana", "Rotina criada" in out["content"])

    store["routines"].append({"id": "r-comp", "company_id": "c1", "name": "Cobranca da corretora",
                              "visibility": "company", "created_by": "u-maria", "is_active": True,
                              "schedule": {"kind": "daily", "time": "09:00"}, "delivery": {"channel": "whatsapp"},
                              "next_run_at": "2026-07-21T09:00:00"})
    store["routines"].append({"id": "r-maria", "company_id": "c1", "name": "Rotina pessoal da Maria",
                              "visibility": "personal", "created_by": "u-maria", "is_active": True,
                              "schedule": {"kind": "daily", "time": "10:00"}, "delivery": {"channel": "whatsapp"},
                              "next_run_at": "2026-07-21T10:00:00"})

    lst = rt.ListRoutinesTool(company_id="c1", supabase_client=db)
    joao_view = lst._run(user_id="u-joao")["content"]
    check("Joao ve a dele + da corretora; NUNCA a pessoal da Maria",
          "Relatorio de sexta" in joao_view and "Cobranca da corretora" in joao_view
          and "Rotina pessoal da Maria" not in joao_view, joao_view)

    mng = rt.ManageRoutineTool(company_id="c1", supabase_client=db)
    res = mng._run(routine_id="r-maria", action="delete", user_id="u-joao")
    check("Joao nao gerencia (nem enxerga) rotina pessoal da Maria",
          "não encontrada" in res["content"] and any(x["id"] == "r-maria" for x in store["routines"]), res)
    res2 = mng._run(routine_id="r-comp", action="pause", user_id="u-joao")
    check("rotina da corretora segue gerenciavel por todos", "não encontrada" not in res2["content"], res2)

    # ---------- 4) oauth store: corretora e pessoal coexistem ----------
    fapi = types.ModuleType("fastapi")

    class _HTTPException(Exception):
        def __init__(self, status_code=500, detail=""):
            self.status_code, self.detail = status_code, detail

    fapi.HTTPException = _HTTPException
    fapi.APIRouter = lambda *a, **k: types.SimpleNamespace(post=lambda *aa, **kk: (lambda f: f))
    fapi.Depends = lambda x=None: None
    fapi.Header = lambda default=None, alias=None: None
    sys.modules["fastapi"] = fapi
    pyd = types.ModuleType("pydantic")

    class _BM:
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

    pyd.BaseModel = _BM
    sys.modules["pydantic"] = pyd
    dbmod = types.ModuleType("app.core.database")
    dbmod.AsyncSupabaseClient = object
    dbmod.get_async_db = lambda: None
    sys.modules["app.core.database"] = dbmod
    enc = types.ModuleType("app.services.encryption_service")
    enc.get_encryption_service = lambda: types.SimpleNamespace(encrypt=lambda s: "enc:" + s[:10])
    sys.modules["app.services.encryption_service"] = enc

    oc = _load("app.api.oauth_connectors", "app/api/oauth_connectors.py")
    ostore = {"connector_templates": [{"id": "tpl-drive", "slug": "google_drive"}],
              "tenant_connections": []}
    adb = _Supabase(ostore, is_async=True)
    import os
    os.environ["BACKEND_INTERNAL_API_KEY"] = "k"

    async def _store(owner):
        payload = oc.OAuthStorePayload(company_id="c1", slug="google_drive", access_token="tok",
                                       refresh_token=None, expires_in=None, scope=None,
                                       account_label=None, name=None, owner_user_id=owner)
        return await oc.store_oauth_token.__wrapped__(payload, "k", adb) if hasattr(oc.store_oauth_token, "__wrapped__") \
            else await oc.store_oauth_token(payload, "k", adb)

    r1 = asyncio.run(_store(None))
    r2 = asyncio.run(_store("u-joao"))
    conns = ostore["tenant_connections"]
    check("conexao da corretora + pessoal COEXISTEM", len(conns) == 2
          and any(c.get("owner_user_id") is None for c in conns)
          and any(c.get("owner_user_id") == "u-joao" for c in conns), conns)
    check("nomes distinguem o dono", any("corretora" in str(c.get("name")) for c in conns)
          and any("pessoal" in str(c.get("name")) for c in conns))
    r3 = asyncio.run(_store("u-joao"))
    check("re-conectar pessoal ATUALIZA (nao duplica)", len(ostore["tenant_connections"]) == 2, r3)

    # ---------- 5) blindagens por source-check ----------
    search_src = (ROOT / "app/services/search_service.py").read_text(encoding="utf-8")
    check("busca padrao EXCLUI docs pessoais", 'exclude_scopes=["personal"]' in search_src)
    check("busca pessoal ligada ao user da requisicao", "build_personal_search_kwargs(user_id)" in search_src)
    nodes_src = (ROOT / "app/agents/nodes.py").read_text(encoding="utf-8")
    check("tool_node injeta user POR EXECUCAO (grafo cacheado)",
          '"user_id": request_user_id' in nodes_src and 'state.get("user_id")' in nodes_src)
    cb_src = (ROOT / "app/core/callbacks/cost_callback.py").read_text(encoding="utf-8")
    check("custo atribuido ao usuario via contexto da requisicao", "get_current_user_id" in cb_src)
    ds_src = (ROOT / "app/services/document_service.py").read_text(encoding="utf-8")
    check("upload grava dono do doc pessoal", "owner_user_id" in ds_src and "SCOPE_PERSONAL" in ds_src)
    qd_src = (ROOT / "app/services/qdrant_service.py").read_text(encoding="utf-8")
    check("qdrant filtra exclude_scopes e owner", "exclude_scopes" in qd_src and "owner_user_id" in qd_src)

    up_src = (WEB / "app/api/dashboard/knowledge/upload/route.ts").read_text(encoding="utf-8")
    check("Next upload: dono vem da SESSAO, nunca do form", "auth.ctx.userId" in up_src)
    kn_src = (WEB / "lib/admin/tenant-overview-store.ts").read_text(encoding="utf-8")
    check("Next lista: doc pessoal so aparece pro dono", "viewerUserId" in kn_src)
    rot_src = (WEB / "app/api/dashboard/rotinas/route.ts").read_text(encoding="utf-8")
    check("Next rotinas: filtro + guard de dono", "visibility" in rot_src and "ctx.userId" in rot_src)
    auth_src = (WEB / "app/api/connectors/[provider]/authorize/route.ts").read_text(encoding="utf-8")
    cbk_src = (WEB / "app/api/connectors/[provider]/callback/route.ts").read_text(encoding="utf-8")
    check("Next OAuth: owner=me assinado no state + repassado ao store",
          "ownerUserId" in auth_src and "owner_user_id" in cbk_src)
    mig = ROOT / "supabase/migrations/20260720_01_spec044_tres_camadas.sql"
    check("migracao registrada no repo", mig.exists())

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  - {n}: {d}")
        sys.exit(1)


if __name__ == "__main__":
    run()
