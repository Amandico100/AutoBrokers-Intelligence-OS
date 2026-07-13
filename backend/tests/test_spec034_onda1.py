"""SPEC-034 Onda 1 - Espelho + Vigia + Sentinela.

Rodar: python backend/tests/test_spec034_onda1.py

- ESPELHO: conversas com seguradoras espelhadas em conversations/messages
  (idempotente via mirror_idx; papel user=seguradora / assistant=nos; conversa
  nomeada "Acionamento - {Seguradora}" por caso);
- VIGIA (diagnose): perfis de tempo POR FASE (URA 30s/120s; humano 10min/20min;
  nunca-comecou 5min; prazo global 45min); alertas disparam UMA vez;
- SENTINELA: escada de recuperacao finita (recupera com cerebro guarded; falhou
  ou esgotou -> needs_human + dossie + alerta; nunca loop infinito).
"""

import asyncio
import importlib.util
import sys
import types
from datetime import datetime, timedelta, timezone
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


for name in ("app", "app.services", "app.core", "app.tasks"):
    module = sys.modules.setdefault(name, types.ModuleType(name))
    module.__path__ = []

pb = _load("app.services.corridor_playbooks", "app/services/corridor_playbooks.py")
dispatch = _load("app.services.insurer_dispatch_service", "app/services/insurer_dispatch_service.py")


def iso_ago(seconds: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat()


# ---------- fakes do Supabase p/ o Espelho ----------
class FakeQuery:
    def __init__(self, store, table):
        self.store, self.table, self._insert = store, table, None

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def limit(self, n):
        return self

    def insert(self, payload):
        self._insert = payload
        return self

    def update(self, payload):
        self.store["updates"].append((self.table, payload))
        return self

    def execute(self):
        if self._insert is not None:
            rows = self._insert if isinstance(self._insert, list) else [self._insert]
            for r in rows:
                self.store[self.table].append(r)
            return SimpleNamespace(data=[{"id": f"{self.table}-{len(self.store[self.table])}"}])
        if self.table == "conversations":
            return SimpleNamespace(data=list(self.store.get("conv_lookup") or []))
        return SimpleNamespace(data=[])


class FakeDB:
    def __init__(self, store):
        self.client = self
        self.store = store

    def table(self, name):
        return FakeQuery(self.store, name)


def run():
    print("== SPEC-034 Onda 1 - Espelho + Vigia + Sentinela ==\n")

    # stubs ANTES de carregar o mirror (imports acontecem dentro das funcoes)
    store = {"conversations": [], "messages": [], "updates": [], "conv_lookup": []}
    db_stub = types.ModuleType("app.core.database")
    db_stub.get_supabase_client = lambda: FakeDB(store)
    sys.modules["app.core.database"] = db_stub
    integ_stub = types.ModuleType("app.services.integration_service")
    integ_stub.get_integration_service = lambda: SimpleNamespace(
        get_or_create_user=lambda phone, company_id, name: "user-fake-1"
    )
    sys.modules["app.services.integration_service"] = integ_stub

    mirror = _load("app.services.dispatch_mirror", "app/services/dispatch_mirror.py")
    wd = _load("app.tasks.dispatch_watchdog", "app/tasks/dispatch_watchdog.py")

    # ---------- ESPELHO ----------
    check("label: porto-auto-whatsapp@v1 -> Porto Seguro",
          mirror.insurer_label_from_ref("porto-auto-whatsapp@v1") == "Porto Seguro")
    check("label: desconhecida capitaliza",
          mirror.insurer_label_from_ref("foo-auto@v1") == "Foo")

    session = {
        "case_id": "case-1", "playbook_ref": "porto-auto-whatsapp@v1", "subservice": "bateria",
        "state": "ura", "created_at": iso_ago(60),
        "transcript": [
            {"direction": "out", "text": "Ola", "at": iso_ago(50)},
            {"direction": "in", "text": "Escolha a opcao desejada\nBotao 1: Seguro Auto", "at": iso_ago(40)},
            {"direction": "out", "text": "Seguro Auto", "at": iso_ago(30)},
        ],
    }
    asyncio.run(mirror.mirror_session("co-1", "551130039303", session))
    check("espelho: cria a conversa do acionamento",
          len(store["conversations"]) == 1
          and store["conversations"][0]["user_name"] == "Acionamento — Porto Seguro (bateria)"
          and store["conversations"][0]["session_id"] == "dispatch:551130039303:co-1:case-1",
          store["conversations"])
    check("espelho: 3 mensagens com papeis certos (in=user, out=assistant)",
          [m["role"] for m in store["messages"]] == ["assistant", "user", "assistant"],
          [m["role"] for m in store["messages"]])
    check("espelho: created_at preservado do transcript",
          all(m.get("created_at") for m in store["messages"]))
    check("espelho: mirror_idx avancou", session.get("mirror_idx") == 3, session.get("mirror_idx"))

    n_msgs = len(store["messages"])
    asyncio.run(mirror.mirror_session("co-1", "551130039303", session))
    check("espelho: idempotente (sem entradas novas, nada insere)", len(store["messages"]) == n_msgs)

    session["transcript"].append({"direction": "in", "text": "Digite o CPF", "at": iso_ago(1)})
    store["conv_lookup"] = [{"id": "conversations-1"}]  # conversa ja existe no banco
    asyncio.run(mirror.mirror_session("co-1", "551130039303", session))
    check("espelho: so a entrada NOVA e espelhada (reusa conversa)",
          len(store["messages"]) == n_msgs + 1 and len(store["conversations"]) == 1,
          (len(store["messages"]), len(store["conversations"])))

    # espelho nunca derruba: banco explodindo -> segue sem excecao
    db_stub.get_supabase_client = lambda: (_ for _ in ()).throw(RuntimeError("down"))
    session["transcript"].append({"direction": "in", "text": "x", "at": iso_ago(0)})
    asyncio.run(mirror.mirror_session("co-1", "551130039303", session))
    check("espelho: falha de banco nao explode nem marca como espelhado",
          session.get("mirror_idx") == 4, session.get("mirror_idx"))
    db_stub.get_supabase_client = lambda: FakeDB(store)

    # ---------- VIGIA: diagnose por fase ----------
    def base(state, last_dir, last_age, created_age=100, **flags):
        s = {"state": state, "case_id": "c", "created_at": iso_ago(created_age),
             "transcript": [{"direction": last_dir, "text": "t", "at": iso_ago(last_age)}]}
        s.update(flags)
        return s

    check("URA: nos calados 40s -> stall", wd.diagnose(base("ura", "in", 40)) == "stall_unanswered")
    check("URA: nos calados 10s -> saudavel", wd.diagnose(base("ura", "in", 10)) is None)
    check("URA: calada 150s apos nossa resposta -> alerta",
          wd.diagnose(base("ura", "out", 150)) == "ura_silent")
    check("URA: alerta de silencio dispara UMA vez",
          wd.diagnose(base("ura", "out", 150, wd_ura_silent=True)) is None)
    check("humano: sumido 11min -> cutucada",
          wd.diagnose(base("human_phase", "out", 660)) == "human_silent_nudge")
    check("humano: sumido 21min -> alerta",
          wd.diagnose(base("human_phase", "out", 1260, wd_human_nudge=True)) == "human_silent_alert")
    check("humano: nos calados 40s -> stall (sentinela responde)",
          wd.diagnose(base("human_phase", "in", 40)) == "stall_unanswered")
    check("nunca comecou: preparing ha 6min -> alerta",
          wd.diagnose({"state": "preparing", "created_at": iso_ago(360), "transcript": []}) == "never_started")
    check("prazo global: 46min sem desfecho -> alerta",
          wd.diagnose(base("ura", "in", 5, created_age=46 * 60)) == "deadline")
    for terminal in ("test_aborted", "needs_human", "monitoring", "captured"):
        check(f"terminal {terminal}: nunca alarma",
              wd.diagnose(base(terminal, "in", 9999, created_age=9999)) is None)
    check("entrada sem 'at' (selada) -> saudavel, sem falso alarme",
          wd.diagnose({"state": "ura", "created_at": iso_ago(60),
                       "transcript": [{"direction": "in", "text": "x"}]}) is None)

    # ---------- SENTINELA: escada finita ----------
    sent_to_insurer = []
    alerts = []

    async def fake_alert(company_id, text, wa, integration):
        alerts.append(text)

    wd._support_alert = fake_alert
    fake_wa = SimpleNamespace(send_message=lambda phone, text, integ: sent_to_insurer.append((phone, text)))

    async def brain_ok(company_id, session, insurer_text):
        return "2"

    async def brain_fail(company_id, session, insurer_text):
        return None

    # degrau 1: cerebro recupera
    wd._adaptive_reply = brain_ok
    s = base("ura", "in", 60)
    s["slots"] = {}
    action = asyncio.run(wd._sentinela_recover("co", "5511999", s, fake_wa, {"i": 1}))
    check("sentinela: cerebro recupera -> resposta enviada a seguradora",
          action == "recovered" and sent_to_insurer and sent_to_insurer[-1][1] == "2",
          (action, sent_to_insurer[-1:]))
    check("sentinela: intervencao anotada no transcript (via=sentinela)",
          s["transcript"][-1].get("via") == "sentinela" and s["sentinela_attempts"] == 1)
    check("sentinela: apos responder, diagnose fica saudavel (sem refire)",
          wd.diagnose(s) is None, wd.diagnose(s))

    # cerebro falha -> handoff imediato com dossie (nunca silencio)
    wd._adaptive_reply = brain_fail
    s2 = base("ura", "in", 60)
    s2["slots"] = {}
    action2 = asyncio.run(wd._sentinela_recover("co", "5511999", s2, fake_wa, {"i": 1}))
    check("sentinela: cerebro falhou -> needs_human + dossie + alerta",
          action2 == "handoff" and s2["state"] == "needs_human"
          and s2.get("dossier_sent") and alerts,
          (action2, s2.get("state"), len(alerts)))

    # escada esgotada (2 intervencoes ja feitas) -> handoff direto
    wd._adaptive_reply = brain_ok
    s3 = base("ura", "in", 60)
    s3["slots"] = {}
    s3["sentinela_attempts"] = 2
    action3 = asyncio.run(wd._sentinela_recover("co", "5511999", s3, fake_wa, {"i": 1}))
    check("sentinela: escada esgotada (max 2) -> handoff, nao tenta de novo",
          action3 == "handoff" and s3["state"] == "needs_human", (action3, s3.get("state")))

    # ---------- fiacao ----------
    src = (ROOT / "app/tasks/buffer_processor.py").read_text(encoding="utf-8")
    check("watchdog registrado no scheduler (20s)",
          "dispatch_watchdog_check" in src and "check_dispatch_watchdog" in src)
    router_src = (ROOT / "app/services/dispatch_router.py").read_text(encoding="utf-8")
    check("espelho ligado no ponto unico (save_active_dispatch)",
          "mirror_session" in router_src)

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  FALHOU: {n} -> {d}")
        sys.exit(1)


if __name__ == "__main__":
    run()
