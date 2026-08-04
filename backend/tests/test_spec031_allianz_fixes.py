"""SPEC-031 - Fixes do teste real Allianz (2026-07-12 19h).

Rodar: python backend/tests/test_spec031_allianz_fixes.py

- loop guard POR PASSO: '1' legitimo em passos seguidos NAO pausa; mesmo passo
  com mesma resposta 3x pausa;
- veiculo pela PLACA MASCARADA (2 carros na apolice: 'JD#-###2' vs 'JC#-###9');
- noops Allianz (termo de privacidade, dicas, fique tranquilo, opcao invalida)
  nao geram resposta do adaptativo;
- sessao test_aborted SELADA: nova saudacao da URA nao recebe resposta (zumbi).
"""

import asyncio
import importlib.util
import os
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


for name in ("app", "app.services"):
    module = sys.modules.setdefault(name, types.ModuleType(name))
    module.__path__ = []

pb = _load("app.services.corridor_playbooks", "app/services/corridor_playbooks.py")
dispatch = _load("app.services.insurer_dispatch_service", "app/services/insurer_dispatch_service.py")
router = _load("app.services.dispatch_router", "app/services/dispatch_router.py")

SLOTS = {
    "titular_cpf": "50021648034", "titular_nome": "Eduardo Teste",
    "veiculo_placa": "JCL9A59", "local_atual": "Rua Piaui, 325, Bucareim, Joinville SC",
    "local_destino": "Oficina X, Rua B, 2, Centro, Joinville SC",
    "problema_descricao": "bateria descarregada, nao liga",
    "telefone_contato": "47988087463", "pessoa_no_local": "Eduardo",
}


def _outs(s):
    return [t["text"] for t in s["transcript"] if t["direction"] == "out"]


def run():
    print("== SPEC-031 - fixes Allianz 12/07 ==\n")
    # ATUALIZADO em 04/08/2026 (P-90), CLAUDE.md §9.3 — os dois padrões
    # viraram ABERTOS: quem segura o acionamento agora é `agents.is_active`
    # do agente de atendimento, e não mais uma ausência de variável. Este
    # arquivo continua provando o comportamento FECHADO/ENSAIO — mas agora
    # ele o ARMA de propósito, em vez de herdá-lo de um default que mudou.
    os.environ["INSURER_DISPATCH_LIVE"] = "false"
    os.environ["DISPATCH_FINALIZE_MODE"] = "test"

    # ---------- pick_option_by_plate ----------
    menu = "Por favor, confirme o veiculo para atendimento:\n\n1 - 2500,  placa JD#-###2\n2 - HILUX SW4,  placa JC#-###9\n3 - Outro veiculo\n0 - Sair"
    check("placa: escolhe a HILUX (opcao 2)", pb.pick_option_by_plate(menu, "JCL9A59") == "2", pb.pick_option_by_plate(menu, "JCL9A59"))
    check("placa: sem match seguro -> vazio", pb.pick_option_by_plate(menu, "ZZZ0Z00") == "")
    check("placa: ambiguidade -> vazio", pb.pick_option_by_plate("1 - A, placa JC#-###9\n2 - B, placa JC#-###9", "JCL9A59") == "")

    # ---------- Fluxo Allianz real: '1' repetido NAO pausa + veiculo certo ----------
    s = dispatch.new_dispatch_session(case_id="a", company_id="co", playbook_ref="allianz-auto-whatsapp@v1", subservice="bateria", slots=dict(SLOTS))
    s = dispatch.start_dispatch(s)
    n0 = len(_outs(s))
    s = dispatch.handle_insurer_message(s, "Termo de Privacidade: Ao prosseguir com o atendimento, voce declara estar ciente da Politica de Privacidade.")
    s = dispatch.handle_insurer_message(s, "Tenho algumas dicas importantes para conseguir te atender da melhor forma! - Escolha a opcao desejada digitando o numero")
    check("noops: termo+dicas nao geram resposta", len(_outs(s)) == n0 and s["state"] not in ("needs_human",), (len(_outs(s)) - n0, s.get("state")))
    s = dispatch.handle_insurer_message(s, "Ola! Sou a assistente virtual da Allianz. Voce precisa de Assistencia 24h para qual seguro? 1 - Automovel, Moto ou Caminhao 2 - Residencia")
    check("menu tipo seguro -> 1", _outs(s)[-1] == "1", _outs(s)[-1:])
    s = dispatch.handle_insurer_message(s, "Digite o CPF ou CNPJ do(a) titular da apolice.")
    s = dispatch.handle_insurer_message(s, menu)
    check("veiculo pela placa -> 2 (HILUX)", _outs(s)[-1] == "2", _outs(s)[-1:])
    s = dispatch.handle_insurer_message(s, "Obrigada! Anotei seu numero (47) 98808-7463. Esta correto? 1 - Sim 2 - Nao")
    check("telefone anotado -> 1", _outs(s)[-1] == "1", _outs(s)[-1:])
    s = dispatch.handle_insurer_message(s, "O seu veiculo e: 1 - Automotor (a gasolina/etanol/diesel) ou Hibrido 2 - Eletrico")
    check("automotor -> 1 (2a vez '1', nao pausa)", _outs(s)[-1] == "1" and s["state"] != "needs_human", (s.get("state"), _outs(s)[-1:]))
    s = dispatch.handle_insurer_message(s, "O que voce precisa? 1 - Profissional para pane eletrica, recarga de bateria, motor nao funciona 3 - Guincho para pane mecanica 4 - Guincho para sinistro / acidente 7 - Chaveiro")
    check("FIX LOOP GUARD: 3o '1' seguido (passos DIFERENTES) NAO pausa", _outs(s)[-1] == "1" and s["state"] != "needs_human", (s.get("state"), s.get("reason"), _outs(s)[-1:]))
    s = dispatch.handle_insurer_message(s, "Certo! Para quando precisa do profissional para recarga de bateria/pane eletrica? 1 - Agora 2 - Quero agendar 9 - Voltar")
    check("quando -> 1 (4o '1', segue vivo)", _outs(s)[-1] == "1" and s["state"] != "needs_human", (s.get("state"), _outs(s)[-1:]))
    # mesmo passo repetido 3x com mesma resposta AINDA pausa (loop real)
    s2 = dispatch.new_dispatch_session(case_id="l", company_id="co", playbook_ref="allianz-auto-whatsapp@v1", subservice="bateria", slots=dict(SLOTS))
    s2 = dispatch.start_dispatch(s2)
    cpf_q = "Digite o CPF ou CNPJ do(a) titular da apolice."
    s2 = dispatch.handle_insurer_message(s2, cpf_q)
    s2 = dispatch.handle_insurer_message(s2, cpf_q)
    s2 = dispatch.handle_insurer_message(s2, cpf_q)
    check("loop REAL (mesmo passo 3x) ainda pausa", s2["state"] == "needs_human" and s2.get("reason") == "loop_guard", s2.get("reason"))

    # ---------- zumbi test_aborted selado (router) ----------
    zs = dispatch.new_dispatch_session(case_id="z", company_id="coZ", playbook_ref="allianz-auto-whatsapp@v1", subservice="bateria", slots=dict(SLOTS))
    zs = dispatch.start_dispatch(zs)
    zs["client_phone"] = "5547988087463"
    asyncio.run(router.save_active_dispatch("coZ", "551140901444", zs))
    sent = []
    asyncio.run(router.try_route_insurer_inbound(
        company_id="coZ", from_phone="551140901444",
        text="RESUMO Servico: recarga de bateria Podemos confirmar o atendimento? 1 - Sim 2 - Nao 0 - Sair",
        send_to_insurer=sent.append, send_to_client=lambda p, t: None,
    ))
    aborted = asyncio.run(router.load_active_dispatch("coZ", "551140901444"))
    check("freio de teste -> test_aborted", (aborted or {}).get("state") == "test_aborted", (aborted or {}).get("state"))
    before = len((aborted or {}).get("transcript") or [])
    handled = asyncio.run(router.try_route_insurer_inbound(
        company_id="coZ", from_phone="551140901444",
        text="Ola! Sou a assistente virtual da Allianz. Voce precisa de Assistencia 24h para qual seguro? 1 - Automovel",
        send_to_insurer=sent.append, send_to_client=lambda p, t: None,
    ))
    sealed = asyncio.run(router.load_active_dispatch("coZ", "551140401444".replace("40", "09")))
    sealed = asyncio.run(router.load_active_dispatch("coZ", "551140901444"))
    outs_after = [t for t in (sealed or {}).get("transcript") or [] if t.get("direction") == "out"]
    outs_before = [t for t in (aborted or {}).get("transcript") or [] if t.get("direction") == "out"]
    check("ZUMBI SELADO: saudacao pos-cancelamento NAO recebe resposta",
          handled is True and len(outs_after) == len(outs_before), (len(outs_before), len(outs_after)))

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  FALHOU: {n} -> {d}")
        sys.exit(1)


if __name__ == "__main__":
    run()
