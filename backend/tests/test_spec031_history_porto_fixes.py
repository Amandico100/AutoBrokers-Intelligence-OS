"""SPEC-031 - Fixes dos testes reais Porto + Azul + Chat Principal (2026-07-12).

Rodar: python backend/tests/test_spec031_history_porto_fixes.py

- HISTORICO (mega-bug): get_conversation_history devolvia as N mensagens mais
  ANTIGAS da conversa (desc=False + limit) -> o agente ficava CEGO para a
  conversa ATUAL (re-pedia CPF, reiniciava o atendimento, "nao tenho seu CPF",
  e chegou a AFIRMAR acionamento que nunca viu). Agora: N mais RECENTES,
  devolvidas em ordem cronologica. Sync e async.
- Porto: menu raiz vira "Seguro Auto" direto quando o CPF ja foi digitado
  (reply_if_step_done); submenu da bateria ("Entendi. O que voce precisa?")
  tem passo proprio; ponto_referencia so dispara na PERGUNTA (o RESUMO tambem
  contem "Ponto de referencia:" e nao pode disparar).
- Azul: mesmo ajuste do ponto_referencia.
- Honestidade: confirm_first PROIBE afirmar acionamento antes de 'dispatched';
  ficha de veiculo (placa/modelo) disponivel para TODOS os papeis (core incl.).
"""

import asyncio
import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
PASS = 0
FAIL = 0
FAILURES = []


def check(name, cond, detail=None):
    global PASS, FAIL
    if cond:
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


for name in ("app", "app.services", "app.core"):
    module = sys.modules.setdefault(name, types.ModuleType(name))
    module.__path__ = []

# ---- stubs para carregar app.core.database sem fastapi/supabase reais ----
_fastapi = types.ModuleType("fastapi")
_fastapi.Request = object
sys.modules.setdefault("fastapi", _fastapi)
_supabase = types.ModuleType("supabase")
_supabase.__path__ = []
_supabase.Client = object
_supabase.create_client = lambda *a, **k: None
_sup_async = types.ModuleType("supabase._async")
_sup_async.__path__ = []
_sup_async_client = types.ModuleType("supabase._async.client")
_sup_async_client.AsyncClient = object
_sup_async_client.create_client = lambda *a, **k: None
sys.modules.setdefault("supabase", _supabase)
sys.modules.setdefault("supabase._async", _sup_async)
sys.modules.setdefault("supabase._async.client", _sup_async_client)
_config = types.ModuleType("app.core.config")
_config.settings = SimpleNamespace(SUPABASE_URL="http://fake", SUPABASE_KEY="fake")
sys.modules.setdefault("app.core.config", _config)

db_mod = _load("app.core.database", "app/core/database.py")
pb = _load("app.services.corridor_playbooks", "app/services/corridor_playbooks.py")
dispatch = _load("app.services.insurer_dispatch_service", "app/services/insurer_dispatch_service.py")


# ---- fake do query-builder Supabase (simula o PostgREST: order + limit) ----
class FakeQuery:
    def __init__(self, owner, table, is_async=False):
        self.owner, self.table, self.is_async = owner, table, is_async
        self.desc, self.lim = None, None

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def order(self, col, desc=False):
        self.desc = desc
        return self

    def limit(self, n):
        self.lim = n
        return self

    def _result(self):
        if self.table == "conversations":
            return SimpleNamespace(data=[{"id": "conv-1"}])
        rows = sorted(self.owner.rows, key=lambda r: r["created_at"], reverse=bool(self.desc))
        if self.lim:
            rows = rows[: self.lim]
        self.owner.last_msg_query = self
        return SimpleNamespace(data=list(rows))

    def execute(self):
        if self.is_async:
            async def _run():
                return self._result()
            return _run()
        return self._result()


class FakeClient:
    def __init__(self, rows, is_async=False):
        self.rows, self.is_async, self.last_msg_query = rows, is_async, None

    def table(self, name):
        return FakeQuery(self, name, is_async=self.is_async)


ROWS = [
    {"role": "user", "content": f"m{i}", "type": "text", "created_at": f"2026-07-12T10:00:{i:02d}"}
    for i in range(30)
]

SLOTS = {
    "titular_cpf": "50021648034", "titular_nome": "Eduardo Teste",
    "veiculo_placa": "JCL9A59", "local_atual": "Rua Piaui, 325, Bucareim, Joinville SC",
    "local_destino": "Oficina X, Rua B, 2, Centro, Joinville SC",
    "problema_descricao": "bateria descarregada", "telefone_contato": "47988087463",
    "pessoa_no_local": "Eduardo", "ponto_referencia": "em frente ao mercado",
    "servico_texto": "Bateria", "servico_opcao": "2",
}


def _outs(s):
    return [t["text"] for t in s["transcript"] if t["direction"] == "out"]


def run():
    print("== SPEC-031 - historico mais RECENTE + fixes Porto/Azul 12/07 ==\n")

    # ---------- MEGA-BUG do historico (sync) ----------
    svc = object.__new__(db_mod.SupabaseClient)
    svc.client = FakeClient(ROWS)
    hist = svc.get_conversation_history("sess", "co", limit=10)
    check("sync: pediu ao banco em ordem DESC (mais novas primeiro)",
          svc.client.last_msg_query is not None and svc.client.last_msg_query.desc is True,
          getattr(svc.client.last_msg_query, "desc", None))
    check("sync: devolve as 10 mais RECENTES (m20..m29), nao as mais antigas",
          [m["content"] for m in hist] == [f"m{i}" for i in range(20, 30)],
          [m["content"] for m in hist])
    check("sync: ordem cronologica (mais antiga -> mais nova)",
          hist and hist[0]["content"] == "m20" and hist[-1]["content"] == "m29")

    # ---------- MEGA-BUG do historico (async) ----------
    asvc = object.__new__(db_mod.AsyncSupabaseClient)
    asvc._client = FakeClient(ROWS, is_async=True)
    ahist = asyncio.run(asvc.get_conversation_history("sess", "co", limit=10))
    check("async: pediu DESC e devolveu as 10 mais RECENTES em ordem cronologica",
          asvc._client.last_msg_query.desc is True
          and [m["content"] for m in ahist] == [f"m{i}" for i in range(20, 30)],
          [m["content"] for m in ahist])

    # ---------- Porto: menu raiz inteligente (reply_if_step_done) ----------
    s = dispatch.new_dispatch_session(case_id="p1", company_id="co",
                                      playbook_ref="porto-auto-whatsapp@v1",
                                      subservice="bateria", slots=dict(SLOTS))
    s = dispatch.start_dispatch(s)
    menu_raiz = "Ola, Amandus! Para comecar, escolha a opcao desejada digitando o numero: Seguro Auto | Informar outro CPF/CNPJ"
    s = dispatch.handle_insurer_message(s, menu_raiz)
    check("Porto: menu raiz SEM cpf digitado -> re-identifica (Informar outro CPF/CNPJ)",
          _outs(s)[-1] == "Informar outro CPF/CNPJ", _outs(s)[-1:])
    s = dispatch.handle_insurer_message(s, "Certo! Digite o seu *CPF ou CNPJ* para eu localizar o cadastro.")
    check("Porto: pedir_cpf responde o CPF", _outs(s)[-1] == "50021648034", _outs(s)[-1:])
    s = dispatch.handle_insurer_message(s, menu_raiz)
    check("Porto: menu raiz COM cpf ja digitado -> Seguro Auto direto (sem re-identificar)",
          _outs(s)[-1] == "Seguro Auto", _outs(s)[-1:])

    # ---------- Porto: submenu da bateria (travava ~2min no teste 12/07) ----------
    s = dispatch.handle_insurer_message(
        s, "Entendi. O que voce precisa?\n\nBotao 1: Recarga de bateria\nBotao 2: Compra de bateria\nBotao 3: Bateria na garantia")
    check("Porto: submenu bateria -> Recarga de bateria",
          _outs(s)[-1] == "Recarga de bateria" and s["state"] != "needs_human",
          (s.get("state"), _outs(s)[-1:]))

    # ---------- ponto_referencia: PERGUNTA sim, RESUMO nao ----------
    porto = pb.PORTO_AUTO_WHATSAPP_V1
    q = "O local tem algum *ponto de referencia*? Se nao tiver, e so dizer 'nao tem'."
    step = pb.match_ura_step(porto, q, subservice="bateria")
    check("Porto: pergunta de ponto de referencia dispara o passo",
          bool(step) and step.get("step") == "ponto_referencia", step and step.get("step"))
    resumo = ("Confira o resumo: *Servico:* Recarga de bateria | *Endereco:* Rua Piaui, 325 | "
              "*Ponto de referencia:* nao tem | *Telefone:* (47) 98808-7463")
    step2 = pb.match_ura_step(porto, resumo, subservice="bateria")
    check("Porto: RESUMO com 'Ponto de referencia:' NAO dispara o passo",
          not step2 or step2.get("step") != "ponto_referencia", step2 and step2.get("step"))
    azul = pb.AZUL_AUTO_WHATSAPP_V1
    step3 = pb.match_ura_step(azul, "Pode me informar algum ponto de referencia?", subservice="bateria")
    check("Azul: pergunta de ponto de referencia dispara o passo",
          bool(step3) and step3.get("step") == "ponto_referencia", step3 and step3.get("step"))
    step4 = pb.match_ura_step(azul, resumo, subservice="bateria")
    check("Azul: RESUMO NAO dispara ponto_referencia",
          not step4 or step4.get("step") != "ponto_referencia", step4 and step4.get("step"))

    # ---------- honestidade + ficha p/ todos os papeis (smoke no fonte) ----------
    tool_src = (ROOT / "app/agents/tools/insurer_dispatch_tool.py").read_text(encoding="utf-8")
    check("confirm_first PROIBE afirmar acionamento antes de 'dispatched'",
          "PROIBIDO dizer ao cliente" in tool_src and "retornar status 'dispatched'" in tool_src)
    infocap_src = (ROOT / "app/agents/tools/infocap_tool.py").read_text(encoding="utf-8")
    check("ficha de veiculo NAO e mais exclusiva do client_facing (core tambem)",
          "if str(result.get(\"status\") or \"\") == \"found\":" in infocap_src
          and "self._client_facing and str(result.get(\"status\")" not in infocap_src)

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  FALHOU: {n} -> {d}")
        sys.exit(1)


if __name__ == "__main__":
    run()
