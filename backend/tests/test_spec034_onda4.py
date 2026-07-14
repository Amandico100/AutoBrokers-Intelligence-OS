"""SPEC-034 Onda 4 - Alfaiate + Auditor + overlays em runtime.

Rodar: python backend/tests/test_spec034_onda4.py

- ALFAIATE: classes de risco (informativo novo=auto; menu novo/alterado=
  aprovacao; perto de finalize=NUNCA); relatorio legivel; ancora segura;
- OVERLAYS: get_playbook mescla noops do cache SEM mutar o playbook-fonte
  (sem duplicacao); motor ignora o aviso novo da URA (noop);
- AUDITOR: scorecard heuristico (repetiu msg, re-pediu CPF, amnesia,
  frustracao, arrastada); drift detector (tela que tinha resposta e hoje
  nao casa com nenhum passo).
"""

import importlib.util
import sys
import types
from pathlib import Path

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

pb = _load("app.services.corridor_playbooks", "app/services/corridor_playbooks.py")
ums = _load("app.services.ura_map_service", "app/services/ura_map_service.py")
tailor = _load("app.services.playbook_tailor", "app/services/playbook_tailor.py")
aud = _load("app.services.conversation_auditor", "app/services/conversation_auditor.py")
dispatch = _load("app.services.insurer_dispatch_service", "app/services/insurer_dispatch_service.py")


def run():
    print("== SPEC-034 Onda 4 - Alfaiate + Auditor ==\n")

    # ---------- ALFAIATE: classes de risco ----------
    new_map = {"nodes": {
        "a": {"text": "vale lembrar: mantenha seus dados atualizados", "kind": "informativo",
              "options": [], "hash": "h1"},
        "b": {"text": "o que voce precisa agora?", "kind": "menu", "hash": "h2",
              "options": [{"label": "Guincho"}, {"label": "Taxi"}]},
        "c": {"text": "podemos confirmar o seu atendimento?", "kind": "finalize",
              "options": [{"label": "Sim"}, {"label": "Sair"}], "hash": "h3"},
    }}
    diff = {"added": [new_map["nodes"]["a"]["text"], new_map["nodes"]["b"]["text"],
                      new_map["nodes"]["c"]["text"]],
            "removed": [], "changed_options": [
                {"tela": "para quando deseja confirmar o agendamento", "de": ["Sim"], "para": ["Sim", "Nao"]}]}
    classes = tailor.classify_diff(diff, new_map)
    check("alfaiate: informativo novo -> AUTO (overlay noop)",
          len(classes["auto"]) == 1 and "vale lembrar" in classes["auto"][0]["tela"], classes["auto"])
    check("alfaiate: menu novo -> APROVACAO", any("o que voce precisa" in i["tela"] for i in classes["approval"]))
    check("alfaiate: tela de confirmacao -> NUNCA automatico",
          any("podemos confirmar" in i["tela"] for i in classes["never"]))
    check("alfaiate: mudanca de rotulo perto de finalize -> NUNCA",
          any("agendamento" in i["tela"] for i in classes["never"]), classes["never"])
    report = tailor.render_patch_report("porto-auto-whatsapp@v1", classes)
    check("alfaiate: relatorio legivel com as 3 classes",
          "AUTO-APLICADO" in report and "APROVA" in report and "NUNCA" in report)
    anchor = tailor.anchor_from_text("vale lembrar: mantenha (seus) dados")
    check("alfaiate: ancora escapada (regex segura)", "\\(seus\\)" in anchor, anchor)

    # ---------- OVERLAYS em runtime ----------
    base_steps = len((pb.get_playbook("porto-auto-whatsapp@v1") or {}).get("ura_steps") or [])
    pb.set_overlay_cache({"porto-auto-whatsapp@v1": [
        {"anchor": r"vale\ lembrar:\ mantenha", "note": "Alfaiate teste"}]})
    merged = pb.get_playbook("porto-auto-whatsapp@v1")
    check("overlay: passo noop mesclado em runtime",
          len(merged["ura_steps"]) == base_steps + 1 and merged["ura_steps"][-1]["noop"] is True)
    merged2 = pb.get_playbook("porto-auto-whatsapp@v1")
    check("overlay: SEM duplicacao em chamadas repetidas (fonte nao mutada)",
          len(merged2["ura_steps"]) == base_steps + 1, len(merged2["ura_steps"]))

    # motor de verdade: aviso novo da URA e IGNORADO (noop), sem resposta e sem handoff
    s = dispatch.new_dispatch_session(
        case_id="c", company_id="co", playbook_ref="porto-auto-whatsapp@v1", subservice="bateria",
        slots={"titular_cpf": "1", "titular_nome": "T", "veiculo_placa": "AAA1A11",
               "local_atual": "Rua A, 1, Centro, Joinville SC",
               "local_destino": "Rua B, 2, Centro, Joinville SC",
               "problema_descricao": "bateria", "telefone_contato": "47988087463",
               "pessoa_no_local": "T"})
    s = dispatch.start_dispatch(s)
    n0 = len([t for t in s["transcript"] if t["direction"] == "out"])
    s = dispatch.handle_insurer_message(s, "Vale lembrar: mantenha seus dados atualizados no app!")
    n1 = len([t for t in s["transcript"] if t["direction"] == "out"])
    check("overlay: motor ignora o aviso novo (noop ativo, sem resposta/handoff)",
          n1 == n0 and s["state"] not in ("needs_human",), (n1 - n0, s.get("state")))
    pb.set_overlay_cache({})

    # ---------- AUDITOR: scorecard heuristico ----------
    score, flags = aud.score_messages([
        {"role": "assistant", "content": "Por favor me informe o CPF do titular para eu localizar"},
        {"role": "user", "content": "030.111.222-33"},
        {"role": "assistant", "content": "Nao tenho seu CPF registrado por aqui ainda"},
        {"role": "assistant", "content": "Por favor me informe o CPF do titular para eu localizar"},
        {"role": "user", "content": "JA FALEI o cpf, que merda"},
    ])
    check("auditor: flags certas (re_pediu_cpf, amnesia, repetiu, frustrado)",
          set(flags) == {"re_pediu_cpf", "amnesia", "repetiu_mensagem", "cliente_frustrado"}, flags)
    check("auditor: score penalizado", score == 10, score)
    good_score, good_flags = aud.score_messages([
        {"role": "user", "content": "preciso de guincho"},
        {"role": "assistant", "content": "Ja localizei sua apolice e o seu Fiat Argo placa ABC1D23. Onde o carro esta agora?"},
    ])
    check("auditor: conversa boa = 100 sem flags", good_score == 100 and good_flags == [])

    # ---------- AUDITOR: drift detector ----------
    porto = pb.get_playbook("porto-auto-whatsapp@v1")
    script = [
        {"screen": "Certo! Digite o seu *CPF ou CNPJ* para eu localizar o cadastro.", "expected": "123"},
        {"screen": "TELA NOVA INVENTADA que nenhum passo conhece, responda ja", "expected": "1"},
        {"screen": "aviso informativo sem resposta", "expected": None},
    ]
    drift = aud.detect_drift(porto, script)
    check("auditor: drift detecta SO a tela que tinha resposta e nao casa mais",
          len(drift) == 1 and "TELA NOVA" in drift[0], drift)

    src = (ROOT / "app/tasks/buffer_processor.py").read_text(encoding="utf-8")
    check("auditor: task registrada no scheduler", "auditor_check" in src and "check_auditor" in src)

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  FALHOU: {n} -> {d}")
        sys.exit(1)


if __name__ == "__main__":
    run()
