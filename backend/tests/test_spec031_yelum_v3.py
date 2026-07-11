"""SPEC-031 - Yelum v3 (fluxo REAL COMPLETO 16/03/2026) + parser de endereco BR.

Rodar: python backend/tests/test_spec031_yelum_v3.py

A conversa 'Liberty Facil Assist' da AutoFleet e a YELUM rebatizada (ex-Liberty,
grupo HDI desde 2024). O fluxo de 16/03/2026 foi 100% bot ate o protocolo — este
replay percorre TODAS as mensagens reais (dados sinteticos) e prova:
- cada passo respondido deterministicamente (incl. garagem/travadas/eletrico/
  rebaixado/CEP-rua-numero-bairro-cidade-estado com reply_repeat origem->destino);
- freio de teste no PONTO DE NAO-RETORNO real ('agora ou prefere agendar');
- modo LIVE completa e captura protocolo ('o numero da sua assistencia e *X*');
- parser de endereco BR (rua/numero/bairro/cidade/UF/CEP) + fallback_adaptive;
- Porto endereco texto-livre origem->destino; Allianz destino UF/cidade/rua/nr.
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

SLOTS = {
    "titular_cpf": "11122233344",
    "titular_nome": "Fulano de Tal",
    "veiculo_placa": "ABC1D23",
    "veiculo_descricao": "S10 Pickup 2022",
    "local_atual": "Rua Possidio Silva do Valle, 71, Distrito Industrial, Sao Jose SC",
    "local_destino": "Rua Geronimo Medeiros, 56, Flor de Napolis, Sao Jose SC",
    "problema_descricao": "motor falhando, precisa de guincho",
    "telefone_contato": "48998171110",
    "pessoa_no_local": "Sergio",
}


def _outs(session):
    return [t["text"] for t in session["transcript"] if t["direction"] == "out"]


def run():
    print("== SPEC-031 - Yelum v3 (fluxo real 16/03/2026) + parser ==\n")
    os.environ.pop("INSURER_DISPATCH_LIVE", None)
    os.environ.pop("DISPATCH_FINALIZE_MODE", None)
    os.environ.pop("DISPATCH_FINALIZE_LIVE_PLAYBOOKS", None)

    # ---------- Parser de endereco BR ----------
    p1 = pb.parse_address_br("R. Abelardo Luz, 342 - Balneario, Florianopolis - SC, 88075-542")
    check("parser: rua", p1.get("rua") == "R. Abelardo Luz", p1)
    check("parser: numero", p1.get("numero") == "342", p1)
    check("parser: bairro", p1.get("bairro") == "Balneario", p1)
    check("parser: cidade", p1.get("cidade") == "Florianopolis", p1)
    check("parser: UF", p1.get("uf") == "SC", p1)
    check("parser: CEP", p1.get("cep") == "88075-542", p1)
    p2 = pb.parse_address_br("Av Santa Tecla 2400, Bage, RS")
    check("parser: numero grudado na rua", p2.get("numero") == "2400" and p2.get("rua") == "Av Santa Tecla", p2)
    check("parser: UF sozinha no fim", p2.get("uf") == "RS", p2)
    p3 = pb.parse_address_br("Oficina Central, Rua B, 50, Sao Jose SC")
    check("parser: acha a rua no meio (Oficina como prefixo)", p3.get("rua") == "Rua B" and p3.get("numero") == "50", p3)
    check("parser: vazio -> vazio", pb.parse_address_br("") == {})

    # ---------- Sessao injeta slots de endereco decompostos ----------
    sy = dispatch.new_dispatch_session(case_id="y", company_id="co",
                                       playbook_ref="yelum-auto-whatsapp@v3",
                                       subservice="guincho", slots=dict(SLOTS))
    check("slots: local_rua deduzida", sy["slots"].get("local_rua") == "Rua Possidio Silva do Valle", sy["slots"].get("local_rua"))
    check("slots: destino_numero deduzido", sy["slots"].get("destino_numero") == "56", sy["slots"].get("destino_numero"))
    sy = dispatch.start_dispatch(sy)

    # ---------- Replay INTEGRAL do fluxo real 16/03/2026 (mensagens reais) ----------
    FLOW = [
        ("Olá, seja bem-vindo ao atendimento digital de *Assistência 24 horas* da *Yelum Seguradora!*", None),
        ("Para começar, informe *apenas um dos dados abaixo:* - CPF ou CNPJ do segurado - Placa do veículo *Exemplos:* CPF: 123.456.789-00", "11122233344"),
        ("Identifiquei em seu cadastro a placa ABC1D23. Deseja continuar com o atendimento para o veículo ou atendimento residencial? Botão 1: Automóvel Botão 2: Residencial", "Automóvel"),
        ("Por favor, me informe o seu nome ou como gostaria de ser chamado.", "Atendimento"),
        ("Estamos prontos para seguir com sua solicitação de Assistência 24 Horas para o Veículo de Placa *ABC1D23*, modelo *S10 PICKUP*.", None),
        ("Maria em qual dessas opções você se enquadra? Botão 1: Sou segurado(a) Botão 2: Sou corretor(a) Botão 3: Outro", "Sou corretor(a)"),
        ("Maria você é a pessoa que está local para acompanhar o serviço? Botão 1: Sim Botão 2: Não Botão 3: Voltar", "Não"),
        ("Certo, neste caso qual é o nome da pessoa que está no local?", "Sergio"),
        ("Por gentileza me informe o *número de celular* com DDD da pessoa que está no local, seguindo de 9 dígitos do telefone:", "48998171110"),
        ("O número de telefone 48998171110 está correto? Botão 1: Sim Botão 2: Não Botão 3: Voltar", "Sim"),
        ("Para facilitar a sua localização, poderia me informar a cor do veículo de placa *ABC1D23* Branco Prata/Cinza Preto Vermelho Outros Voltar", "Outros"),
        ("Qual a cor do veículo de placa *ABC1D23*?", "não sei"),
        ("Maria, agora preciso saber se o veículo está em uma rodovia? Por favor, responda selecionando uma das opções abaixo. Botão 1: Sim Botão 2: Não Botão 3: Voltar", "Não"),
        ("Pode me dizer o que aconteceu? Para isso *selecione* uma das opções. Pane ou Defeito Selecione essa opção quando houve falha no funcionamento do veículo Recarga de bateria ... Pneu Furado ... Problema com a chave ...", "Pane ou Defeito"),
        ("Por favor, selecione a opção que condiz com a pane do veículo Problemas elétricos ... Problemas no motor Selecione essa opção se o motor está falhando ... Não sei ... Mais opções ... Voltar", "Problemas no motor"),
        ("Neste caso enviaremos o serviço de *Guincho* para atendê-lo(a).", None),
        ("Para que possamos concluir a abertura da sua solicitação, só preciso de mais algumas informações.", None),
        ("Selecione uma das opções para informar o endereço onde o veículo está agora. Digitar endereço Compartilhar Informar o CEP Não sei Voltar", "Digitar endereço"),
        ("Por favor, digite *somente a rua* onde o veiculo está. Ex: Rua xxx", "Rua Possidio Silva do Valle"),
        ("Qual é o *número*?", "71"),
        ("Qual é o *bairro*?", "Distrito Industrial"),
        ("Qual é a *cidade*?", "Sao Jose"),
        ("Qual o *estado*?", "SC"),
        ("Certo! Esse foi o endereço mais próximo que encontramos: *Endereço:* Rua Possidio Silva do Valle *Número:* 71 *Bairro:* Distrito Industrial *Cidade:* São José *Estado:* SC", None),
        ("Você confirma o endereço? Botão 1: Sim Botão 2: Não Botão 3: Voltar", "Sim"),
        ("Quais são o complemento e/ou referência?", "não tem"),
        ("O veículo está em uma garagem? Botão 1: Sim Botão 2: Não Botão 3: Voltar", "Não"),
        ("Agora, confirme se o veículo está em alguma dessas situações: O *câmbio* ou as *rodas* estão travadas? Botão 1: Sim Botão 2: Não Botão 3: Voltar", "Não"),
        ("O veículo é elétrico ou híbrido? Botão 1: Sim Botão 2: Não Botão 3: Voltar", "Não"),
        ("O veículo é rebaixado? Botão 1: Sim Botão 2: Não Botão 3: Voltar", "Não"),
        ("Você se encontra em uma das situações de risco abaixo? Via com pouca iluminação Via com pouco movimento Nenhuma das anteriores Voltar", "Nenhuma das anteriores"),
        ("Por favor, me informe os ocupantes tem alguma das particularidades listadas abaixo. Criança Idoso Gestante Pessoa com deficiência Cirurgia recente Nenhuma das anteriores Voltar", "Nenhuma das anteriores"),
        ("Certo! Agora preciso que você informe para onde devemos levar o veículo. Qual dessas opções você prefere? Botão 1: Digitar endereço Botão 2: Informar o CEP Botão 3: Voltar", "Digitar endereço"),
        ("Por favor, digite *somente a rua* onde o veiculo está. Ex: Rua xxx", "Rua Possidio Silva do Valle"),
        ("Qual é o *número*?", "56"),
        ("Qual é o *bairro*?", "Flor de Napolis"),
        ("Qual é a *cidade*?", "Sao Jose"),
        ("Você confirma o endereço? Botão 1: Sim Botão 2: Não Botão 3: Voltar", "Sim"),
        ("Quais são o complemento e/ou referência?", "não tem"),
    ]
    ok_all = True
    for msg, expected in FLOW:
        before = len(_outs(sy))
        sy = dispatch.handle_insurer_message(sy, msg)
        outs = _outs(sy)
        if expected is None:
            if len(outs) != before or sy["state"] in ("needs_human", "test_aborted"):
                ok_all = False
                check(f"noop falhou em: {msg[:60]}", False, (sy.get("state"), outs[-1:]))
        else:
            if not outs or outs[-1] != expected:
                ok_all = False
                check(f"passo falhou em: {msg[:60]}", False, (expected, outs[-1:], sy.get("state"), sy.get("reason")))
    check("replay integral 16/03/2026: todos os passos correspondem ao fluxo real", ok_all)
    check("replay: nenhum needs_human no caminho feliz", sy["state"] not in ("needs_human",), (sy.get("state"), sy.get("reason")))

    # PONTO DE NAO-RETORNO: modo teste cancela com 'Sair'.
    sy = dispatch.handle_insurer_message(sy, "Você quer o atendimento para agora ou prefere agendar para outro momento? Botão 1: Agora Botão 2: Agendar Botão 3: Voltar")
    check("FREIO teste: 'agora ou agendar' -> test_aborted + Sair",
          sy["state"] == "test_aborted" and _outs(sy)[-1] == "Sair", (sy.get("state"), _outs(sy)[-1:]))

    # ---------- Modo LIVE: confirma 'Agora' e captura o protocolo real ----------
    os.environ["DISPATCH_FINALIZE_MODE"] = "live"
    sl = dispatch.new_dispatch_session(case_id="yl", company_id="co",
                                       playbook_ref="yelum-auto-whatsapp@v3",
                                       subservice="guincho", slots=dict(SLOTS))
    sl = dispatch.start_dispatch(sl)
    sl = dispatch.handle_insurer_message(sl, "Você quer o atendimento para agora ou prefere agendar para outro momento? Botão 1: Agora Botão 2: Agendar")
    check("LIVE: responde 'Agora' (abre o servico)", _outs(sl)[-1] == "Agora", _outs(sl)[-1:])
    sl = dispatch.handle_insurer_message(sl, "Finalizamos a abertura do(s) pedido(s) de *Guincho* e o número da sua assistência é *9415275!*. Para acompanhar acesse o link abaixo https://assist24.page.link/6YMqP")
    check("LIVE: captura protocolo 'numero da sua assistencia e'", sl.get("captured", {}).get("protocol") == "9415275", sl.get("captured"))
    check("LIVE: captura link + vira captured", sl["state"] == "captured" and "assist24" in str(sl["captured"].get("tracking_link")), sl.get("state"))
    os.environ.pop("DISPATCH_FINALIZE_MODE", None)

    # ---------- fallback_adaptive: bairro do destino ausente -> adaptativo ----------
    slots_sem_bairro = dict(SLOTS)
    slots_sem_bairro["local_destino"] = "Rua B, 50, Sao Jose SC"  # sem bairro
    sf = dispatch.new_dispatch_session(case_id="yf", company_id="co",
                                       playbook_ref="yelum-auto-whatsapp@v3",
                                       subservice="guincho", slots=slots_sem_bairro)
    sf = dispatch.start_dispatch(sf)
    sf = dispatch.handle_insurer_message(sf, "Qual é o *bairro*?")  # 1a vez: origem tem bairro
    check("fallback: origem tem bairro -> responde", _outs(sf)[-1] == "Distrito Industrial", _outs(sf)[-1:])
    n_b = len(_outs(sf))
    sf = dispatch.handle_insurer_message(sf, "Qual é o *bairro*?")  # 2a vez: destino SEM bairro
    check("fallback: destino sem bairro NAO chuta nem trava (acumula p/ adaptativo)",
          sf["state"] not in ("needs_human", "test_aborted") and len(_outs(sf)) == n_b
          and bool(sf.get("pending_insurer_messages")),
          (sf.get("state"), _outs(sf)[-1:], sf.get("pending_insurer_messages")))

    # ---------- Porto: endereco texto-livre origem -> destino (reply_repeat) ----------
    sp = dispatch.new_dispatch_session(case_id="p", company_id="co",
                                       playbook_ref="porto-auto-whatsapp@v1",
                                       subservice="guincho", slots=dict(SLOTS))
    sp = dispatch.start_dispatch(sp)
    ender_msg = "Digite o endereço completo do local, desta forma 👇 *Rua/Avenida/Rodovia, número, cidade, estado*"
    sp = dispatch.handle_insurer_message(sp, ender_msg)
    check("porto endereco 1a vez = origem (texto livre)", _outs(sp)[-1] == SLOTS["local_atual"], _outs(sp)[-1:])
    sp = dispatch.handle_insurer_message(sp, "Localizei o endereço Rua Possidio Silva do Valle, 71, São José - SC")
    sp = dispatch.handle_insurer_message(sp, "Está correto? Botão 1: Sim Botão 2: Não")
    check("porto confirma geocode com Sim", _outs(sp)[-1] == "Sim", _outs(sp)[-1:])
    sp = dispatch.handle_insurer_message(sp, ender_msg)
    check("porto endereco 2a vez = destino (reply_repeat)", _outs(sp)[-1] == SLOTS["local_destino"], _outs(sp)[-1:])

    # ---------- Allianz: destino em 4 etapas (UF -> cidade -> logradouro -> numero) ----------
    sa = dispatch.new_dispatch_session(case_id="a", company_id="co",
                                       playbook_ref="allianz-auto-whatsapp@v1",
                                       subservice="guincho", slots=dict(SLOTS))
    sa = dispatch.start_dispatch(sa)
    sa = dispatch.handle_insurer_message(sa, "Ok, agora preciso saber o endereço de destino. *1 -* Oficina mecânica ou outro endereço *2 -* Não sei")
    check("allianz destino menu -> 1", _outs(sa)[-1] == "1", _outs(sa)[-1:])
    sa = dispatch.handle_insurer_message(sa, "Informe a *UF* (sigla do estado) *do destino*: (Ex: SP, RS, AM, DF, PI)")
    check("allianz destino UF (parser)", _outs(sa)[-1] == "SC", _outs(sa)[-1:])
    sa = dispatch.handle_insurer_message(sa, "E qual a cidade? *Dica:* para facilitar a identificação, não utilize abreviações")
    check("allianz destino cidade (parser)", _outs(sa)[-1] == "Sao Jose", _outs(sa)[-1:])
    sa = dispatch.handle_insurer_message(sa, "Agora, informe apenas o nome do logradouro (rua, avenida, rodovia, etc.) _(Ex. Avenida Brasil)_.")
    check("allianz destino logradouro (parser)", _outs(sa)[-1] == "Rua Geronimo Medeiros", _outs(sa)[-1:])
    sa = dispatch.handle_insurer_message(sa, "Por último, qual o número do endereço (ou quilômetro, em caso de rodovia)?")
    check("allianz destino numero so digitos (parser)", _outs(sa)[-1] == "56", _outs(sa)[-1:])
    sa = dispatch.handle_insurer_message(sa, "Ok, agora selecione o endereço onde está o veículo: *1 - Endereço da apólice:* X *2 -* Outra localização *3 -* Informar endereço manual")
    check("allianz origem manual -> 3", _outs(sa)[-1] == "3", _outs(sa)[-1:])

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  FALHOU: {n} -> {d}")
        sys.exit(1)


if __name__ == "__main__":
    run()
