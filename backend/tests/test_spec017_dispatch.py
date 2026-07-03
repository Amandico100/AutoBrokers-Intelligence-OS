"""SPEC-017 P4 - Playbook Allianz Residencial + motor de acionamento (dry-run).

Rodar:
    python backend/tests/test_spec017_dispatch.py

Replay OFFLINE da URA real da Allianz Assistência 24h (frases reais do robô,
dados 100% sintéticos). Prova: respostas determinísticas por âncora, gate
INSURER_DISPATCH_LIVE fail-closed, captura de protocolo/senha/agendamento só
por âncora, fail-safes (passo desconhecido, slot faltante, sinistro).
"""

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

REF = "allianz-residencial-whatsapp@v1"

SLOTS = {
    "titular_cpf": "11122233344",
    "endereco_numero": "16783",
    "telefone_contato": "48999998888",
    "problema_descricao": "Tomadas da cozinha sem energia, sem cheiro de queimado",
    "periodo_preferido": "tarde",
    "risco_confirmado_sem_fumaca": "sim",
}

# Frases REAIS do robô Allianz (conversa minerada; sem PII).
URA = {
    "menu1": "Olá! Sou a *assistente virtual da Allianz*. Este é um canal exclusivo de serviços emergenciais. Você precisa de Assistência 24h para qual seguro?",
    "menu2": "Para continuarmos qual o seguro que deseja utilizar?",
    "cpf": "Certo! Por favor digite o *CPF* ou *CNPJ* do(a) titular da apólice ou pressione *9* para voltar",
    "endereco": "Por favor, confirme o endereço para atendimento:",
    "numero": "Agora, me informe o número da residência.",
    "telefone": "Registramos o telefone *+55 (48) 99107-2089* para entrar em contato com você.\n\nDeseja adicionar outro número?",
    "celular": "Por favor, informe *o número de celular completo* com DDD",
    "anotei": "Obrigada! Anotei seu número *(48) 99999-8888*.\nEstá correto?",
    "servico": "Vamos lá! Informe o tipo de  serviço:",
    "retorno": (
        "A assistência foi agendada para o dia 28, entre 13h e 18h.\n\n"
        "É necessário que haja um maior de 18 anos no local para receber o prestador.\n\n"
        "Ao chegar no local o prestador irá solicitar uma senha de acesso, que são os 4 últimos números do telefone informado: 8888.\n\n"
        "O número da assistência é 46078656."
    ),
}


def run():
    print("== SPEC-017 P4 - playbook + dispatch dry-run ==\n")
    os.environ.pop("INSURER_DISPATCH_LIVE", None)  # gate FECHADO (default)

    playbook = pb.get_playbook(REF)
    check("P4: playbook Allianz registrado", playbook is not None and playbook["insurer_key"] == "allianz")
    check("P4: gate fechado por default", dispatch.dispatch_live_enabled() is False)

    # Slots completos p/ eletricista -> ready_to_send.
    s = dispatch.new_dispatch_session(case_id="case-1", company_id="co-1", playbook_ref=REF, subservice="eletricista", slots=SLOTS)
    check("P4: sessão pronta com slots completos", s["state"] == "ready_to_send", s.get("missing_slots"))

    # Slot faltante -> preparing com blockers (nunca inicia).
    s_missing = dispatch.new_dispatch_session(case_id="c", company_id="co", playbook_ref=REF, subservice="eletricista", slots={"titular_cpf": "111"})
    check("P4: slots faltantes bloqueiam início", s_missing["state"] == "preparing" and "periodo_preferido" in s_missing["missing_slots"], s_missing["missing_slots"])

    # Walkthrough completo da URA (dry-run: NADA enviado).
    sent_for_real = []
    sender = sent_for_real.append
    s = dispatch.start_dispatch(s, sender=sender)
    replies = []
    for key in ("menu1", "menu2", "cpf", "endereco", "numero", "telefone", "celular", "anotei", "servico"):
        s = dispatch.handle_insurer_message(s, URA[key], sender=sender)
        outs = [t for t in s["transcript"] if t["direction"] == "out"]
        replies.append(outs[-1]["text"] if outs else None)

    expected = ["Olá", "2", "1", "11122233344", "1", "16783", "1", "48999998888", "1", "1"]
    got = [t["text"] for t in s["transcript"] if t["direction"] == "out"]
    check("P4: sequência da URA exata (10 mensagens)", got == expected, got)
    check("P4: DRY-RUN — nada enviado de verdade", sent_for_real == [] and all(t.get("dry_run") for t in s["transcript"] if t["direction"] == "out"))

    # Retorno da seguradora -> captura por âncora + estado captured.
    s = dispatch.handle_insurer_message(s, URA["retorno"], sender=sender)
    cap = s.get("captured") or {}
    check("P4: protocolo capturado por âncora", cap.get("protocol") == "46078656", cap)
    check("P4: senha capturada", cap.get("password") == "8888", cap)
    check("P4: agendamento capturado", (cap.get("schedule") or {}).get("day") == "28" and (cap.get("schedule") or {}).get("from") == "13h", cap)
    check("P4: estado captured", s["state"] == "captured", s["state"])

    # Mensagem pronta para o cliente (humanizada, com regras fixas).
    msg = dispatch.client_summary_from_capture(s)
    low = (msg or "").lower()
    check("P4: retorno ao cliente tem protocolo+senha+regra 18 anos", msg and "46078656" in msg and "8888" in msg and "maior de 18" in low, msg)

    # Fail-safe: mensagem desconhecida na URA -> human_phase sem resposta às cegas.
    s2 = dispatch.new_dispatch_session(case_id="c2", company_id="co", playbook_ref=REF, subservice="chaveiro", slots=SLOTS)
    s2 = dispatch.start_dispatch(s2)
    s2 = dispatch.handle_insurer_message(s2, "Boa tarde, meu nome é Laercio, sou da assistência 24 horas!")
    check("P4: sem âncora -> human_phase (não responde às cegas)", s2["state"] == "human_phase" and s2.get("pending_insurer_messages"), s2["state"])
    s2 = dispatch.handle_insurer_message(s2, "Qual o problema?", human_phase_reply="O cliente está sem chave de casa, fechadura simples.")
    outs2 = [t for t in s2["transcript"] if t["direction"] == "out"]
    check("P4: fase humana usa resposta preparada (LLM guardada)", outs2[-1]["text"].startswith("O cliente está sem chave"), outs2[-1])

    # Fail-safe: gatilho de sinistro -> needs_human.
    s3 = dispatch.new_dispatch_session(case_id="c3", company_id="co", playbook_ref=REF, subservice="eletricista", slots=SLOTS)
    s3 = dispatch.start_dispatch(s3)
    s3 = dispatch.handle_insurer_message(s3, "Este caso trata-se de sinistro, não assistência.")
    check("P4: gatilho de sinistro -> needs_human", s3["state"] == "needs_human" and "handoff_trigger" in str(s3.get("reason")), s3.get("reason"))

    # Gate aberto (env) -> sender é chamado de verdade.
    os.environ["INSURER_DISPATCH_LIVE"] = "true"
    try:
        s4 = dispatch.new_dispatch_session(case_id="c4", company_id="co", playbook_ref=REF, subservice="chaveiro", slots=SLOTS)
        real_sent = []
        s4 = dispatch.start_dispatch(s4, sender=real_sent.append)
        check("P4: gate aberto envia via sender", real_sent == ["Olá"] and not s4["transcript"][-1]["dry_run"], real_sent)
    finally:
        os.environ.pop("INSURER_DISPATCH_LIVE", None)

    # ---- P5: plano dry-run para a tool do atendente ----
    print("\n== P5 - build_dry_run_plan + tool do atendente ==\n")
    plan = dispatch.build_dry_run_plan(REF, "eletricista", SLOTS)
    check("P5: plano dry-run completo", plan["ok"] and len(plan["steps"]) == 10, plan.get("steps"))
    check("P5: plano contém CPF e opção de serviço", any(s["reply"] == "11122233344" for s in plan["steps"]) and plan["steps"][-1]["reply"] == "1", plan["steps"])
    check("P5: nota deixa claro o modo simulação", "SIMULA" in plan["note"].upper(), plan["note"])
    plan_missing = dispatch.build_dry_run_plan(REF, "eletricista", {"titular_cpf": "111"})
    check("P5: plano bloqueia com slots faltantes", plan_missing["ok"] is False and "periodo_preferido" in plan_missing["missing_slots"], plan_missing)

    tool_src = (ROOT / "app" / "agents" / "tools" / "insurer_dispatch_tool.py").read_text(encoding="utf-8")
    check("P5: tool existe e usa build_dry_run_plan", "build_dry_run_plan" in tool_src and "insurer_dispatch" in tool_src)
    check("P5: tool proíbe afirmar acionamento em simulação", "NÃO afirme que a seguradora já foi acionada" in tool_src)
    graph_src = (ROOT / "app" / "agents" / "graph.py").read_text(encoding="utf-8")
    check("P5: tool anexada SÓ para o papel attendance", "InsurerDispatchTool" in graph_src and '== "attendance"' in graph_src)

    # ---- P5/P6: roteador de despacho (inbound da seguradora -> motor) ----
    print("\n== P5/P6 - dispatch_router (seguradora responde -> motor -> cliente) ==\n")
    import asyncio as _aio

    router = _load("app.services.dispatch_router", "app/services/dispatch_router.py")

    async def _router_flow():
        os.environ["INSURER_DISPATCH_LIVE"] = "true"  # simula gate aberto p/ envio via sender
        try:
            session = dispatch.new_dispatch_session(case_id="cR", company_id="co-R", playbook_ref=REF, subservice="eletricista", slots=SLOTS)
            session["client_phone"] = "5548911112222"
            session = dispatch.start_dispatch(session, sender=lambda t: None)
            await router.save_active_dispatch("co-R", "551140901444", session)

            to_insurer, to_client = [], []
            kw = dict(
                company_id="co-R", from_phone="551140901444",
                send_to_insurer=to_insurer.append,
                send_to_client=lambda ph, tx: to_client.append((ph, tx)),
            )
            # Cliente comum NÃO é interceptado.
            other = await router.try_route_insurer_inbound(company_id="co-R", from_phone="5548999990000", text="oi", send_to_insurer=to_insurer.append, send_to_client=lambda p, t: None)
            check("P6: inbound de cliente comum não é interceptado", other is False)

            # URA da seguradora -> respostas automáticas via sender.
            for key in ("menu1", "menu2", "cpf", "endereco", "numero", "telefone", "celular", "anotei", "servico"):
                handled = await router.try_route_insurer_inbound(text=URA[key], **kw)
                assert handled
            check("P6: URA respondida automaticamente (9 respostas)", to_insurer == ["2", "1", "11122233344", "1", "16783", "1", "48999998888", "1", "1"], to_insurer)

            # Retorno com protocolo -> cliente é avisado e sessão encerra.
            await router.try_route_insurer_inbound(text=URA["retorno"], **kw)
            check("P6: cliente avisado com protocolo/senha/agendamento", len(to_client) == 1 and "46078656" in to_client[0][1] and to_client[0][0] == "5548911112222", to_client)
            check("P6: sessão encerrada após captura", await router.load_active_dispatch("co-R", "551140901444") is None)

            # needs_human: cliente recebe aviso humano e sessão pausa.
            s2 = dispatch.new_dispatch_session(case_id="cH", company_id="co-R", playbook_ref=REF, subservice="chaveiro", slots=SLOTS)
            s2["client_phone"] = "5548911112222"
            s2 = dispatch.start_dispatch(s2, sender=lambda t: None)
            await router.save_active_dispatch("co-R", "551140901444", s2)
            to_client2 = []
            await router.try_route_insurer_inbound(company_id="co-R", from_phone="551140901444", text="Este caso é sinistro.", send_to_insurer=lambda t: None, send_to_client=lambda ph, tx: to_client2.append(tx))
            paused = await router.load_active_dispatch("co-R", "551140901444")
            check("P6: sinistro -> pausa + aviso humanizado ao cliente", paused and paused["state"] == "needs_human" and to_client2 and "equipe" in to_client2[0], to_client2)
            await router.clear_active_dispatch("co-R", "551140901444")
        finally:
            os.environ.pop("INSURER_DISPATCH_LIVE", None)

    _aio.run(_router_flow())

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        sys.exit(1)


if __name__ == "__main__":
    run()
