"""SPEC-031 Faixa 0 - Freio por MODO (teste/live), URAs reais 2026 e monitoring.

Rodar: python backend/tests/test_spec031_finalize_v2.py

Decisao do founder (2026-07-11): o freio de finalizacao existe SO para os TESTES
(a IA executa o fluxo inteiro na seguradora e CANCELA antes de abrir o servico).
Corredor validado roda em modo LIVE e completa ponta a ponta sem humano.

Prova (replay offline, frases REAIS das conversas AutoFleet/Resulta, dados sinteticos):
- modo TESTE: confirmacao final -> test_aborted + cancelamento educado por seguradora;
- modo LIVE (global e por-playbook): confirmacao final respondida pelos ura_steps;
- textos REAIS 2026 dos freios (Allianz/Alfa/Porto/Bradesco/residencial);
- multi-cliente: URAs lembram o CPF anterior -> re-identificacao sempre;
- capturas 2026 (HDI assistencia/agendada, Zurich prevista, ETA em minutos, senha);
- telefone formatado (Azul exige '(dd) 99999-9999');
- passos condicionais por subservico (Bradesco pane: guincho=2, bateria=1);
- pesquisa de satisfacao = noop; texto vazio = noop;
- router: test_aborted avisa quem testa; captured -> monitoring repassa updates.
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

AUTO_SLOTS = {
    "titular_cpf": "11122233344",
    "titular_nome": "Fulano de Tal",
    "veiculo_placa": "ABC1D23",
    "veiculo_descricao": "Fiat Argo 1.0 2022",
    "local_atual": "Rua das Flores, 100, Centro, Florianopolis SC",
    "local_destino": "Oficina Central, Rua B, 50, Sao Jose SC",
    "problema_descricao": "carro nao liga, provavel pane no motor",
    "telefone_contato": "48999990000",
    "pessoa_no_local": "Fulano de Tal",
}
RES_SLOTS = {
    "titular_cpf": "11122233344",
    "endereco_numero": "2270",
    "telefone_contato": "48999990000",
    "problema_descricao": "tomada queimada",
    "periodo_preferido": "manha",
    "risco_confirmado_sem_fumaca": "sim",
}


def _outs(session):
    return [t["text"] for t in session["transcript"] if t["direction"] == "out"]


def _new(ref, sub="guincho", slots=None):
    s = dispatch.new_dispatch_session(case_id="t", company_id="co", playbook_ref=ref,
                                      subservice=sub, slots=dict(slots or AUTO_SLOTS))
    return dispatch.start_dispatch(s)


def run():
    print("== SPEC-031 Faixa 0 - freio por modo + URAs reais 2026 ==\n")
    # ATUALIZADO em 04/08/2026 (P-90), CLAUDE.md §9.3 — os dois padrões
    # viraram ABERTOS: quem segura o acionamento agora é `agents.is_active`
    # do agente de atendimento, e não mais uma ausência de variável. Este
    # arquivo continua provando o comportamento FECHADO/ENSAIO — mas agora
    # ele o ARMA de propósito, em vez de herdá-lo de um default que mudou.
    os.environ["INSURER_DISPATCH_LIVE"] = "false"
    os.environ["DISPATCH_FINALIZE_MODE"] = "test"
    os.environ.pop("DISPATCH_FINALIZE_LIVE_PLAYBOOKS", None)

    # ---------- MODO TESTE (default): confirmacao final CANCELA ----------
    sa = _new("allianz-auto-whatsapp@v1")
    sa = dispatch.handle_insurer_message(
        sa, "*RESUMO* *Servico:* reboque para pane mecanica *Origem:* X *Destino:* Y "
            "Podemos confirmar o atendimento? *1 -* Sim *2 -* Nao, desejo reiniciar *0 -* Sair")
    check("allianz 2026 'Podemos confirmar o atendimento?' -> test_aborted",
          sa["state"] == "test_aborted", sa.get("state"))
    check("allianz cancela com SAIR", _outs(sa)[-1] == "SAIR", _outs(sa)[-1:])

    sp = _new("porto-auto-whatsapp@v1")
    sp = dispatch.handle_insurer_message(
        sp, "Como voce quer prosseguir? Confirmar solicitacao Mudar localizacao atual "
            "Alterar local de destino Alterar dados de contato Sair e nao agendar")
    check("porto 2026 'Como voce quer prosseguir?' -> test_aborted", sp["state"] == "test_aborted", sp.get("state"))
    check("porto cancela com 'Sair e nao agendar'", _outs(sp)[-1] == "Sair e não agendar", _outs(sp)[-1:])

    sp2 = _new("porto-auto-whatsapp@v1")
    sp2 = dispatch.handle_insurer_message(sp2, "Posso confirmar sua solicitacao? Sim Nao, alterar endereco Sair e nao agendar")
    check("porto 'Posso confirmar sua solicitacao?' -> test_aborted", sp2["state"] == "test_aborted", sp2.get("state"))

    sr = dispatch.new_dispatch_session(case_id="r", company_id="co",
                                       playbook_ref="allianz-residencial-whatsapp@v1",
                                       subservice="eletricista", slots=RES_SLOTS)
    sr = dispatch.start_dispatch(sr)
    sr = dispatch.handle_insurer_message(
        sr, "*RESUMO* *Servico:* Eletricista Podemos confirmar o atendimento? *1 -* Sim *2 -* Nao *3 -* Sair")
    check("RESIDENCIAL 2026 tem freio de teste agora", sr["state"] == "test_aborted", sr.get("state"))
    check("residencial cancela com SAIR", _outs(sr)[-1] == "SAIR", _outs(sr)[-1:])

    # ---------- MODO LIVE global: confirmacao respondida pelo ura_step ----------
    os.environ["DISPATCH_FINALIZE_MODE"] = "live"
    sl = _new("allianz-auto-whatsapp@v1")
    sl = dispatch.handle_insurer_message(sl, "Podemos confirmar o atendimento? *1 -* Sim *2 -* Nao *0 -* Sair")
    check("LIVE allianz: confirma com '1' (ponta a ponta)", sl["state"] != "test_aborted" and _outs(sl)[-1] == "1",
          (sl.get("state"), _outs(sl)[-1:]))
    slp = _new("porto-auto-whatsapp@v1")
    slp = dispatch.handle_insurer_message(slp, "Como voce quer prosseguir? Confirmar solicitacao Sair e nao agendar")
    check("LIVE porto: confirma com 'Confirmar solicitacao'", _outs(slp)[-1] == "Confirmar solicitação", _outs(slp)[-1:])
    os.environ["DISPATCH_FINALIZE_MODE"] = "test"

    # ---------- Graduacao POR CORREDOR (live so para playbooks listados) ----------
    os.environ["DISPATCH_FINALIZE_LIVE_PLAYBOOKS"] = "porto-auto-whatsapp@v1"
    g1 = _new("porto-auto-whatsapp@v1")
    g1 = dispatch.handle_insurer_message(g1, "Como voce quer prosseguir? Confirmar solicitacao Sair e nao agendar")
    check("graduacao: porto liberado confirma", _outs(g1)[-1] == "Confirmar solicitação", _outs(g1)[-1:])
    g2 = _new("allianz-auto-whatsapp@v1")
    g2 = dispatch.handle_insurer_message(g2, "Podemos confirmar o atendimento? *1 -* Sim")
    check("graduacao: allianz NAO liberado cancela", g2["state"] == "test_aborted", g2.get("state"))
    os.environ.pop("DISPATCH_FINALIZE_LIVE_PLAYBOOKS", None)

    # ---------- Multi-cliente: URAs lembram o CPF anterior ----------
    mc = _new("allianz-auto-whatsapp@v1")
    mc = dispatch.handle_insurer_message(
        mc, "Em nossa ultima conversa, utilizamos o CPF/CNPJ *708.###.###-34*. "
            "Quer continuar o atendimento com este? *1 -* Sim *2 -* Nao, inserir outro CPF/CNPJ")
    check("allianz cpf anterior -> '2' (re-identifica SEMPRE)", _outs(mc)[-1] == "2", _outs(mc)[-1:])
    mc = dispatch.handle_insurer_message(
        mc, "Identifiquei que voce possui um atendimento realizado recentemente, deseja tratar sobre esse atendimento. "
            "*1 -* Sim, mesmo atendimento *2 -* Nao, abrir novo servico")
    check("allianz atendimento recente -> '2' (novo servico)", _outs(mc)[-1] == "2", _outs(mc)[-1:])

    pm = _new("porto-auto-whatsapp@v1")
    menu_raiz = ("Alvaro, escolha a opcao desejada: Seguro Auto Servico para residencia Servicos Particulares "
                 "Sinistro de terceiro Outros produtos Informar outro CPF/CNPJ")
    pm = dispatch.handle_insurer_message(pm, menu_raiz)
    check("porto menu raiz 1a vez -> 'Informar outro CPF/CNPJ'", _outs(pm)[-1] == "Informar outro CPF/CNPJ", _outs(pm)[-1:])
    pm = dispatch.handle_insurer_message(pm, "Para continuar com seu atendimento, por favor, digite o seu *CPF ou CNPJ*.")
    check("porto pedir_cpf 2026 ('digite o seu') responde CPF", _outs(pm)[-1] == "11122233344", _outs(pm)[-1:])
    pm = dispatch.handle_insurer_message(pm, menu_raiz)
    check("porto menu raiz 2a vez -> 'Seguro Auto' (reply_repeat)", _outs(pm)[-1] == "Seguro Auto", _outs(pm)[-1:])

    # ---------- Capturas 2026 ----------
    hc = _new("hdi-auto-whatsapp@v1")
    hc = dispatch.handle_insurer_message(
        hc, "Ola, eu sou a Assistente Virtual da *HDI SEGUROS S.A*. A solicitacao de *GUINCHO* para a "
            "assistencia *9257546* foi aberta com sucesso! Acompanhe pelo link https://assist24.page.link/iXeN2")
    check("HDI captura protocolo 'para a assistencia'", hc.get("captured", {}).get("protocol") == "9257546", hc.get("captured"))
    check("HDI captura link", "assist24" in str(hc.get("captured", {}).get("tracking_link") or ""), hc.get("captured"))
    check("HDI protocolo+link -> captured", hc["state"] == "captured", hc.get("state"))
    hc2 = _new("hdi-auto-whatsapp@v1")
    hc2 = dispatch.handle_insurer_message(
        hc2, "*HDI SEGUROS S.A*: encontramos o prestador que realizara o servico de *GUINCHO* para a "
             "assistencia *9257546*, agendada para *29/01/2026* as *09:30*.")
    sched = hc2.get("captured", {}).get("schedule") or {}
    check("HDI captura agendamento (dia+hora)", sched.get("day") == "29/01/2026", hc2.get("captured"))

    zc = _new("zurich-auto-whatsapp@v1")
    zc = dispatch.handle_insurer_message(zc, "Ok. Tudo certo! Sua assistencia foi solicitada! *Numero da solicitacao:* *71020124*")
    check("Zurich captura protocolo 'numero da solicitacao'", zc.get("captured", {}).get("protocol") == "71020124", zc.get("captured"))
    zc = dispatch.handle_insurer_message(zc, "Chegada do profissional prevista para o dia *23/02/2026* as *18:10*")
    zsched = zc.get("captured", {}).get("schedule") or {}
    check("Zurich captura 'prevista para o dia'", zsched.get("day") == "23/02/2026", zc.get("captured"))
    check("Zurich protocolo+agenda -> captured", zc["state"] == "captured", zc.get("state"))

    pc = _new("porto-auto-whatsapp@v1")
    pc = dispatch.handle_insurer_message(pc, "Pronto! Tudo certo com o seu agendamento. O servico esta previsto para ser realizado *hoje*, em ate 60 minutos.")
    check("Porto captura ETA em minutos", pc.get("captured", {}).get("eta_minutes") == "60", pc.get("captured"))
    pc = dispatch.handle_insurer_message(pc, "Aqui esta seu protocolo de atendimento: 1-125298136729")
    check("Porto protocolo com hifen 2026", pc.get("captured", {}).get("protocol") == "1-125298136729", pc.get("captured"))
    check("Porto protocolo+eta -> captured", pc["state"] == "captured", pc.get("state"))
    resumo_cliente = dispatch.client_summary_from_capture(pc)
    check("resumo ao cliente inclui ETA", "60 minutos" in (resumo_cliente or ""), resumo_cliente)

    rc = dispatch.new_dispatch_session(case_id="rc", company_id="co",
                                       playbook_ref="allianz-residencial-whatsapp@v1",
                                       subservice="eletricista", slots=RES_SLOTS)
    rc = dispatch.start_dispatch(rc)
    rc = dispatch.handle_insurer_message(rc, "Sua assistencia foi solicitada com sucesso! O numero de protocolo e *51494798*")
    check("residencial captura protocolo 2026 ('numero de protocolo e')",
          rc.get("captured", {}).get("protocol") == "51494798", rc.get("captured"))
    rc = dispatch.handle_insurer_message(rc, "Sua senha sera os 4 ultimos digitos desse telefone *9360*")
    check("residencial captura senha 2026", rc.get("captured", {}).get("password") == "9360", rc.get("captured"))

    # ---------- Telefone formatado (Azul) ----------
    az = _new("azul-auto-whatsapp@v1", sub="bateria")
    az = dispatch.handle_insurer_message(az, "Por favor, informe um numero de contato. Digite no formato: Exemplo: (11) 99999-9999")
    check("azul telefone no formato estrito", _outs(az)[-1] == "(48) 99999-0000", _outs(az)[-1:])

    # ---------- Passo condicional por subservico (Bradesco pane) ----------
    bg = _new("bradesco-auto-whatsapp@v1", sub="guincho")
    bg = dispatch.handle_insurer_message(bg, "Ok! Preciso confirmar alguns dados pra enviar o melhor servico, ta? Me conta o que aconteceu: *1* - O veiculo estava estacionado e nao liga *2* - O veiculo estava andando e parou de funcionar")
    check("bradesco pane guincho -> '2' (andando e parou)", _outs(bg)[-1] == "2", _outs(bg)[-1:])
    bb = _new("bradesco-auto-whatsapp@v1", sub="bateria")
    bb = dispatch.handle_insurer_message(bb, "Me conta o que aconteceu: *1* - O veiculo estava estacionado e nao liga *2* - O veiculo estava andando e parou de funcionar")
    check("bradesco pane bateria -> '1' (estacionado)", _outs(bb)[-1] == "1", _outs(bb)[-1:])

    # ---------- Handoff Alfa 'nao consigo te ajudar' ----------
    af = _new("alfa-auto-whatsapp@v1")
    af = dispatch.handle_insurer_message(af, "Poxa! No momento eu nao consigo te ajudar. Por favor, entre em contato com a nossa Central de atendimento nos telefones: 4003-2532")
    check("alfa 'nao consigo te ajudar' -> needs_human", af["state"] == "needs_human", af.get("reason"))

    # ---------- Pesquisa de satisfacao e texto vazio = noop ----------
    ns = _new("azul-auto-whatsapp@v1")
    n_before = len(_outs(ns))
    ns = dispatch.handle_insurer_message(ns, "Pesquisa de satisfacao A sua opiniao e muito importante! Clique no botao abaixo e avalie.")
    check("pesquisa de satisfacao: nao responde", len(_outs(ns)) == n_before and ns["state"] not in ("needs_human", "test_aborted"), ns.get("state"))
    t_before = len(ns.get("transcript") or [])
    ns = dispatch.handle_insurer_message(ns, "   ")
    check("texto vazio: ignorado", len(ns.get("transcript") or []) == t_before)

    # ---------- Router: test_aborted avisa quem esta testando ----------
    sess = dispatch.new_dispatch_session(case_id="rt", company_id="co1",
                                         playbook_ref="allianz-auto-whatsapp@v1",
                                         subservice="guincho", slots=AUTO_SLOTS)
    sess = dispatch.start_dispatch(sess)
    sess["client_phone"] = "5547988087463"
    asyncio.run(router.save_active_dispatch("co1", "551140901444", sess))
    sent_client = []
    handled = asyncio.run(router.try_route_insurer_inbound(
        company_id="co1", from_phone="551140901444",
        text="Podemos confirmar o atendimento? *1 -* Sim *2 -* Nao *0 -* Sair",
        send_to_insurer=lambda t: None,
        send_to_client=lambda p, t: sent_client.append((p, t)),
    ))
    check("router: inbound tratado (test_aborted)", handled is True)
    check("router: aviso de teste cancelado chega", any("Teste concl" in t for _, t in sent_client), sent_client)
    saved = asyncio.run(router.load_active_dispatch("co1", "551140901444"))
    check("router: sessao fica no espelho como test_aborted", (saved or {}).get("state") == "test_aborted", (saved or {}).get("state"))

    # ---------- Router: captured -> monitoring repassa updates ----------
    ms = dispatch.new_dispatch_session(case_id="mt", company_id="co2",
                                       playbook_ref="hdi-auto-whatsapp@v1",
                                       subservice="guincho", slots=AUTO_SLOTS)
    ms = dispatch.start_dispatch(ms)
    ms["client_phone"] = "5547988087463"
    asyncio.run(router.save_active_dispatch("co2", "551155020700", ms))
    fwd = []
    asyncio.run(router.try_route_insurer_inbound(
        company_id="co2", from_phone="551155020700",
        text="A solicitacao de *GUINCHO* para a assistencia *9257546* foi aberta com sucesso! Acompanhe pelo link https://assist24.page.link/iXeN2",
        send_to_insurer=lambda t: None,
        send_to_client=lambda p, t: fwd.append(t),
    ))
    saved2 = asyncio.run(router.load_active_dispatch("co2", "551155020700"))
    check("router: apos captura vira monitoring", (saved2 or {}).get("state") == "monitoring", (saved2 or {}).get("state"))
    check("router: cliente recebe o resumo da abertura", any("Prontinho" in t for t in fwd), fwd)
    fwd.clear()
    asyncio.run(router.try_route_insurer_inbound(
        company_id="co2", from_phone="551155020700",
        text="encontramos o prestador que realizara o servico de GUINCHO para a assistencia 9257546, agendada para 29/01/2026 as 09:30.",
        send_to_insurer=lambda t: None,
        send_to_client=lambda p, t: fwd.append(t),
    ))
    check("monitoring: update do prestador repassado ao cliente", any("Atualiza" in t for t in fwd), fwd)
    fwd.clear()
    asyncio.run(router.try_route_insurer_inbound(
        company_id="co2", from_phone="551155020700",
        text="A sua opiniao e muito importante. O que achou do atendimento prestado pelo nosso analista? 5-Otimo 4-Bom",
        send_to_insurer=lambda t: None,
        send_to_client=lambda p, t: fwd.append(t),
    ))
    check("monitoring: pesquisa NAO e repassada", fwd == [], fwd)

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  FALHOU: {n} -> {d}")
        sys.exit(1)


if __name__ == "__main__":
    run()
