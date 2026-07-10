"""SPEC-031 - Corredores de assistência AUTO (multi-seguradora, dry-run).

Rodar: python backend/tests/test_spec031_auto_dispatch.py

Replay OFFLINE das URAs REAIS de auto (frases reais dos robôs Porto/HDI/Allianz,
mineradas das conversas da AutoFleet; dados 100% sintéticos). Prova:
- seleção de playbook por seguradora + linha (aliases: Liberty->Yelum, Azul->Porto);
- resolução do contato por env por seguradora (fallback Allianz legado);
- respostas determinísticas por âncora + opção de menu por subserviço;
- FREIO de finalização (needs_human antes de confirmar/abrir o serviço);
- captura de protocolo/OS + link só por âncora;
- gate INSURER_DISPATCH_LIVE fail-closed.
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

# Caso sintético de guincho (nada real).
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

# Frases REAIS mineradas (sem PII).
PORTO = {
    "cpf": "Por favor, informe o *CPF ou CNPJ* do(a) titular.",
    "seguro_auto": "Carmelita, localizei o seu *Seguro Auto*. Por favor, informe a opcao desejada. *1* - Atendimento para veiculo",
    "atendimento": "De que atendimento voce precisa? *1* - Novo atendimento *2* - Acompanhar atendimento",
    "servico": "O que voce precisa? Guincho (reboque) Bateria Troca de pneu Conserto de vidro Chaveiro para o veiculo Taxi",
    "quando": "Para quando voce precisa que esse servico seja realizado? Botao 1: Tenho urgencia Botao 2: Agendar data e hora",
    "referencia": "Por favor, pode me informar algum *ponto de referencia*? Se nao houver, e so digitar *nao tem*.",
    "finalize": "Posso continuar o agendamento? *1* - Sim *2* - Nao",
    "retorno": "Voce pode acompanhar o andamento desse servico no link abaixo: https://porto.example/os/12345 Protocolo de atendimento: 998877",
}
HDI = {
    "auto_resid": "Voce gostaria de solicitar servicos de assistencia para seu *automovel* ou *residencia*? Botao 1: Automovel Botao 2: Residencia",
    "nome": "Por favor, me informe o seu nome ou como gostaria de ser chamado.",
    "placa": "Maria, qual a placa do veiculo? Por favor, digite seguindo os exemplos: AAA12__ ou AAA1A__",
    "roda": "tem alguma roda travada ?",
    "finalize": "Localizacao do Cliente ... esta correto ?",
    "retorno": "Agendamento realizado. Protocolo de atendimento: 7852514",
}
ALLIANZ = {
    "menu1": "Ola! Sou a assistente virtual da Allianz. Voce precisa de Assistencia 24h para qual seguro? *1 -* Automovel, Moto ou Caminhao *2 -* Residencia",
    "cpf": "Digite o *CPF* ou *CNPJ* do(a) titular da apolice.",
    "servico": "O que voce precisa? *1 -* Profissional para pane eletrica *3 -* Guincho para pane mecanica *6 -* Borracheiro *7 -* Chaveiro",
    "veiculo": "O seu veiculo e: *1 -* Automotor (a gasolina/etanol/diesel) ou Hibrido *2 -* Eletrico",
    "finalize": "Antes de prosseguirmos, poderia me confirmar se os dados a seguir estao corretos, por gentileza:",
}


def _outs(session):
    return [t["text"] for t in session["transcript"] if t["direction"] == "out"]


def run():
    print("== SPEC-031 - corredores AUTO (dry-run) ==\n")
    os.environ.pop("INSURER_DISPATCH_LIVE", None)

    # ---- Seleção de playbook + contato ----
    check("porto/auto resolve playbook", pb.resolve_playbook_ref("Porto Seguro", "auto") == "porto-auto-whatsapp@v1")
    check("hdi/auto resolve playbook", pb.resolve_playbook_ref("HDI", "auto") == "hdi-auto-whatsapp@v1")
    check("allianz/auto resolve playbook", pb.resolve_playbook_ref("Allianz", "auto") == "allianz-auto-whatsapp@v1")
    check("Liberty normaliza para Yelum", pb.resolve_playbook_ref("Liberty Seguros", "auto") == "yelum-auto-whatsapp@v1")
    check("Azul tem chave propria (nao Porto)", pb.normalize_insurer_key("Azul") == "azul")
    check("allianz residencial ainda resolve", pb.resolve_playbook_ref("allianz", "residencial") == "allianz-residencial-whatsapp@v1")
    check("seguradora desconhecida -> None", pb.resolve_playbook_ref("SeguradoraX", "auto") is None)

    env = {"INSURER_CONTACT_PORTO_ASSISTENCIA": "0800 727 0800"}
    check("contato porto por env", pb.resolve_insurer_contact("porto", env) == "08007270800")
    check("contato allianz usa fallback legado", pb.resolve_insurer_contact("allianz", {"INSURER_CONTACT_ALLIANZ_ASSISTENCIA_24H": "1140901444"}) == "1140901444")
    check("contato ausente -> vazio", pb.resolve_insurer_contact("hdi", {}) == "")

    # ---- Sessão pronta + injeção do menu de serviço ----
    s = dispatch.new_dispatch_session(case_id="c1", company_id="co", playbook_ref="porto-auto-whatsapp@v1", subservice="guincho", slots=AUTO_SLOTS)
    check("guincho porto: ready_to_send", s["state"] == "ready_to_send", s.get("missing_slots"))
    check("porto injeta rotulo do servico (Guincho)", s["slots"].get("servico_texto") == "Guincho", s["slots"].get("servico_texto"))

    s_missing = dispatch.new_dispatch_session(case_id="c", company_id="co", playbook_ref="porto-auto-whatsapp@v1", subservice="guincho", slots={"titular_cpf": "1"})
    check("guincho sem destino bloqueia", s_missing["state"] == "preparing" and "local_destino" in s_missing["missing_slots"], s_missing["missing_slots"])

    # ---- Abertura = resumo estruturado (auto) ----
    plan = dispatch.build_dry_run_plan("porto-auto-whatsapp@v1", "guincho", AUTO_SLOTS)
    check("dry-run porto ok", plan.get("ok") is True, plan)
    abertura = plan["steps"][0]["reply"]
    check("abertura traz a placa", "ABC1D23" in abertura, abertura[:80])
    check("abertura traz o destino", "Oficina Central" in abertura, abertura[:120])
    check("abertura menciona guincho", "guincho" in abertura.lower())

    # ---- Walkthrough PORTO (âncoras) + FREIO ----
    sent = []
    s = dispatch.start_dispatch(s, sender=sent.append)
    for key in ("cpf", "seguro_auto", "atendimento", "servico", "quando", "referencia"):
        s = dispatch.handle_insurer_message(s, PORTO[key], sender=sent.append)
    outs = _outs(s)
    check("porto responde CPF por ancora", "11122233344" in outs, outs)
    check("porto escolhe servico Guincho", "Guincho" in outs, outs)
    check("porto atendimento novo = 1", outs.count("1") >= 1, outs)
    # Agora a mensagem de finalização: FREIO.
    s = dispatch.handle_insurer_message(s, PORTO["finalize"], sender=sent.append)
    check("FREIO porto: needs_human na finalizacao", s["state"] == "needs_human", s.get("reason"))
    check("FREIO porto: motivo finalize_gate", str(s.get("reason", "")).startswith("finalize_gate"), s.get("reason"))
    check("FREIO porto: nada enviado de verdade (dry-run)", sent == [])
    check("FREIO porto: nao respondeu 'Sim' a finalizacao", "Sim" not in _outs(s))

    # ---- Captura protocolo/link (Porto) ----
    s2 = dispatch.new_dispatch_session(case_id="c2", company_id="co", playbook_ref="porto-auto-whatsapp@v1", subservice="guincho", slots=AUTO_SLOTS)
    s2 = dispatch.start_dispatch(s2)
    s2 = dispatch.handle_insurer_message(s2, PORTO["retorno"])
    check("porto captura protocolo por ancora", s2.get("captured", {}).get("protocol") == "998877", s2.get("captured"))
    check("porto captura link de acompanhamento", "porto.example/os/12345" in str(s2.get("captured", {}).get("tracking_link") or ""), s2.get("captured"))

    # ---- HDI (botões: responde rótulo) + FREIO 'esta correto' ----
    sh = dispatch.new_dispatch_session(case_id="h1", company_id="co", playbook_ref="hdi-auto-whatsapp@v1", subservice="guincho", slots=AUTO_SLOTS)
    sh = dispatch.start_dispatch(sh)
    sh = dispatch.handle_insurer_message(sh, HDI["auto_resid"])
    check("hdi escolhe Automovel (rotulo)", "Automóvel" in _outs(sh) or "Automovel" in _outs(sh), _outs(sh))
    sh = dispatch.handle_insurer_message(sh, HDI["nome"])
    sh = dispatch.handle_insurer_message(sh, HDI["placa"])
    check("hdi responde placa por ancora", "ABC1D23" in _outs(sh), _outs(sh))
    sh = dispatch.handle_insurer_message(sh, HDI["finalize"])
    check("FREIO hdi: 'esta correto' pausa", sh["state"] == "needs_human" and str(sh.get("reason", "")).startswith("finalize_gate"), sh.get("reason"))
    check("hdi captura protocolo", dispatch.handle_insurer_message(
        dispatch.start_dispatch(dispatch.new_dispatch_session(case_id="h2", company_id="co", playbook_ref="hdi-auto-whatsapp@v1", subservice="guincho", slots=AUTO_SLOTS)),
        HDI["retorno"]).get("captured", {}).get("protocol") == "7852514")

    # ---- ALLIANZ auto (números) + FREIO 'confirme os dados' ----
    sa = dispatch.new_dispatch_session(case_id="a1", company_id="co", playbook_ref="allianz-auto-whatsapp@v1", subservice="guincho", slots=AUTO_SLOTS)
    check("allianz injeta opcao 3 p/ guincho", sa["slots"].get("servico_opcao") == "3", sa["slots"].get("servico_opcao"))
    sa = dispatch.start_dispatch(sa)
    sa = dispatch.handle_insurer_message(sa, ALLIANZ["menu1"])
    check("allianz menu tipo seguro = 1 (auto)", _outs(sa)[-1] == "1", _outs(sa))
    sa = dispatch.handle_insurer_message(sa, ALLIANZ["cpf"])
    sa = dispatch.handle_insurer_message(sa, ALLIANZ["servico"])
    check("allianz escolhe guincho = 3", "3" in _outs(sa), _outs(sa))
    sa = dispatch.handle_insurer_message(sa, ALLIANZ["finalize"])
    check("FREIO allianz: confirme os dados pausa", sa["state"] == "needs_human" and str(sa.get("reason", "")).startswith("finalize_gate"), sa.get("reason"))

    # ---- FREIO liberado com finalize_approved (humano aprovou) ----
    sp = dispatch.new_dispatch_session(case_id="p1", company_id="co", playbook_ref="porto-auto-whatsapp@v1", subservice="guincho", slots=AUTO_SLOTS)
    sp["finalize_approved"] = True
    sp = dispatch.start_dispatch(sp)
    sp = dispatch.handle_insurer_message(sp, PORTO["finalize"])
    check("finalize_approved: NAO pausa no freio", sp["state"] != "needs_human" or not str(sp.get("reason", "")).startswith("finalize_gate"), sp.get("reason"))

    # ---- gate fechado: tudo dry-run ----
    check("gate fechado por default", dispatch.dispatch_live_enabled() is False)
    check("porto walkthrough foi 100% dry-run", all(t.get("dry_run") for t in s["transcript"] if t["direction"] == "out"))

    # ===================== FASE 2: Alfa/Azul/Bradesco/Mapfre/Zurich =====================
    for ins, ref in (("Alfa", "alfa-auto-whatsapp@v1"), ("Azul", "azul-auto-whatsapp@v1"),
                     ("Bradesco Seguros", "bradesco-auto-whatsapp@v1"), ("MAPFRE", "mapfre-auto-whatsapp@v1"),
                     ("Zurich", "zurich-auto-whatsapp@v1")):
        check(f"{ins}/auto resolve playbook", pb.resolve_playbook_ref(ins, "auto") == ref, pb.resolve_playbook_ref(ins, "auto"))
    check("Azul NAO cai mais em Porto", pb.normalize_insurer_key("Azul") == "azul")
    check("Itau usa infra Porto", pb.normalize_insurer_key("Itau") == "porto")

    # AZUL: URA numerada + protocolo com hífen + freio 'tudo esta correto'
    az = dispatch.new_dispatch_session(case_id="az1", company_id="co", playbook_ref="azul-auto-whatsapp@v1", subservice="pneu", slots=AUTO_SLOTS)
    check("azul injeta opcao 3 p/ pneu", az["slots"].get("servico_opcao") == "3", az["slots"].get("servico_opcao"))
    az = dispatch.start_dispatch(az)
    az = dispatch.handle_insurer_message(az, "Como eu posso te ajudar? Digite o numero da opcao desejada *1 -* Assistencia 24h para o veiculo *2 -* Apolice")
    check("azul menu inicial = 1", _outs(az)[-1] == "1", _outs(az))
    az = dispatch.handle_insurer_message(az, "Por favor, informe o *CPF ou CNPJ* do(a) segurado(a).")
    check("azul responde CPF", "11122233344" in _outs(az), _outs(az))
    az = dispatch.handle_insurer_message(az, "O que voce precisa? *1* - Guincho (reboque) *2* - Bateria *3* - Troca de pneu *4* - Chaveiro para o veiculo")
    check("azul escolhe pneu = 3", _outs(az)[-1] == "3", _outs(az))
    az = dispatch.handle_insurer_message(az, "Para quando voce precisa que esse servico seja realizado? *Importante*: a solicitacao sera confirmada somente apos a finalizacao do agendamento. *1* - Tenho urgencia *2* - Quero agendar")
    check("azul 'para quando' NAO freia (e coleta)", az["state"] != "needs_human" and _outs(az)[-1] == "1", (az.get("state"), _outs(az)[-1:]))
    az = dispatch.handle_insurer_message(az, "Tudo esta correto? *1* - Sim *2* - Alterar localizacao *3* - Alterar quem esta no local? *4* - Sair e nao agendar")
    check("FREIO azul: 'tudo esta correto' pausa", az["state"] == "needs_human" and str(az.get("reason", "")).startswith("finalize_gate"), az.get("reason"))
    az2 = dispatch.handle_insurer_message(
        dispatch.start_dispatch(dispatch.new_dispatch_session(case_id="az2", company_id="co", playbook_ref="azul-auto-whatsapp@v1", subservice="pneu", slots=AUTO_SLOTS)),
        "Pronto! O seu servico foi agendado para *hoje*, em ate 60 minutos. Aqui esta seu protocolo de atendimento: 1-104106503215")
    check("azul captura protocolo com hifen", az2.get("captured", {}).get("protocol") == "1-104106503215", az2.get("captured"))

    # PORTO: a frase real 'sera confirmada somente apos...' dentro do passo QUANDO nao freia
    pq = dispatch.new_dispatch_session(case_id="pq1", company_id="co", playbook_ref="porto-auto-whatsapp@v1", subservice="guincho", slots=AUTO_SLOTS)
    pq = dispatch.start_dispatch(pq)
    pq = dispatch.handle_insurer_message(pq, "Para quando voce precisa que esse servico seja realizado? *Importante*: a solicitacao sera confirmada somente apos a finalizacao do agendamento. Botao 1: Tenho urgencia Botao 2: Agendar data e hora")
    check("porto 'para quando' real NAO freia", pq["state"] != "needs_human" and _outs(pq)[-1] == "1", (pq.get("state"), _outs(pq)[-1:]))
    pq = dispatch.handle_insurer_message(pq, "Gostaria de alterar alguma informacao? *1* - Nao, esta tudo correto *2* - Veiculo *8* - Sair e nao agendar")
    check("FREIO porto: revisao final pausa", pq["state"] == "needs_human" and str(pq.get("reason", "")).startswith("finalize_gate"), pq.get("reason"))

    # BRADESCO: placa primeiro + problema deriva servico + freio 'enviar agora'
    br = dispatch.new_dispatch_session(case_id="br1", company_id="co", playbook_ref="bradesco-auto-whatsapp@v1", subservice="guincho", slots=AUTO_SLOTS)
    br = dispatch.start_dispatch(br)
    br = dispatch.handle_insurer_message(br, "Eu sou a Assistente Virtual da Bradesco Seguros! Pra gente comecar, voce quer assistencia para: Botao 1: Veiculo Botao 2: Residencia")
    check("bradesco escolhe Veiculo", "Veículo" in _outs(br), _outs(br))
    br = dispatch.handle_insurer_message(br, "Ok, agora me informa a *placa do veiculo*, sem usar espaco ou traco entre as letras e numeros. Exemplo: *ABC1234* ou *ABC1D23*")
    check("bradesco responde placa", "ABC1D23" in _outs(br), _outs(br))
    br = dispatch.handle_insurer_message(br, "Entendi, mas pra eu te ajudar, preciso entender qual o problema com o seu carro: *1* - Pane *2* - Acidente *3* - Problemas com pneus *4* - Problema com chave")
    check("bradesco guincho -> problema pane (1)", _outs(br)[-1] == "1", _outs(br))
    br = dispatch.handle_insurer_message(br, "E como prefere fazer, quer que envie a assistencia agora ou prefere agendar? Botao 1: Enviar agora Botao 2: Agendar")
    check("FREIO bradesco: 'enviar agora' pausa", br["state"] == "needs_human" and str(br.get("reason", "")).startswith("finalize_gate"), br.get("reason"))

    # MAPFRE: exige data de nascimento
    mp_missing = dispatch.new_dispatch_session(case_id="mp0", company_id="co", playbook_ref="mapfre-auto-whatsapp@v1", subservice="guincho", slots=AUTO_SLOTS)
    check("mapfre sem nascimento bloqueia", mp_missing["state"] == "preparing" and "titular_nascimento" in mp_missing["missing_slots"], mp_missing["missing_slots"])
    mp = dispatch.new_dispatch_session(case_id="mp1", company_id="co", playbook_ref="mapfre-auto-whatsapp@v1", subservice="guincho", slots={**AUTO_SLOTS, "titular_nascimento": "01/01/1990"})
    check("mapfre com nascimento pronto", mp["state"] == "ready_to_send", mp.get("missing_slots"))
    mp = dispatch.start_dispatch(mp)
    mp = dispatch.handle_insurer_message(mp, "Para que eu possa atender voce melhor, por favor, me informe o *CPF* ou *CNPJ do titular do seguro*.")
    mp = dispatch.handle_insurer_message(mp, "Otimo! Agora, por favor, digite a *data de nascimento da pessoa titular do seguro*. Exemplo: *11/11/1111*")
    check("mapfre responde nascimento", "01/01/1990" in _outs(mp), _outs(mp))

    # ZURICH: menus por rotulo + freio 'podemos confirmar a solicitacao'
    zu = dispatch.new_dispatch_session(case_id="zu1", company_id="co", playbook_ref="zurich-auto-whatsapp@v1", subservice="guincho", slots=AUTO_SLOTS)
    zu = dispatch.start_dispatch(zu)
    zu = dispatch.handle_insurer_message(zu, "Vamos la! Para qual dos assuntos voce precisa de atendimento? Carro e moto | Informacoes sobre apolices Celular e eletronico | Seguro para roubo")
    check("zurich escolhe Carro e moto", "Carro e moto" in _outs(zu), _outs(zu))
    zu = dispatch.handle_insurer_message(zu, "Voce deseja *acionar a assistencia 24h* ou *acionar o seguro?* Acionar assistencia 24h Acionar seguro Voltar ao menu")
    check("zurich aciona assistencia 24h", "Acionar assistência 24h" in _outs(zu), _outs(zu))
    zu = dispatch.handle_insurer_message(zu, "Podemos confirmar a solicitacao? *1* - Sim *2* - Alterar endereco")
    check("FREIO zurich: 'podemos confirmar' pausa", zu["state"] == "needs_human" and str(zu.get("reason", "")).startswith("finalize_gate"), zu.get("reason"))

    # ---- handoff: sinistro/colisão pausa ----
    ss = dispatch.new_dispatch_session(case_id="s1", company_id="co", playbook_ref="porto-auto-whatsapp@v1", subservice="guincho", slots=AUTO_SLOTS)
    ss = dispatch.start_dispatch(ss)
    ss = dispatch.handle_insurer_message(ss, "Percebi que foi uma colisao/acidente. Vou direcionar para sinistro.")
    check("handoff auto em sinistro/colisao", ss["state"] == "needs_human", ss.get("reason"))

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  FALHOU: {n} -> {d}")
        sys.exit(1)


if __name__ == "__main__":
    run()
