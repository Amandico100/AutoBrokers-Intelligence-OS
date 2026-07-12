"""SPEC-017 - Inbound INTERATIVO (botoes/listas/flows) do Evolution.

Rodar: python backend/tests/test_spec017_interactive_inbound.py

Incidente 2026-07-12 (teste real Yelum): as mensagens com BOTOES/LISTAS/FLOWS
caiam em skip:no_text — o atendente ficava CEGO (e o dashboard, incompleto).
Prova:
- parser renderiza botoes/listas/flows no formato dos exports do WhatsApp
  (as ancoras dos playbooks casam SEM mudanca);
- wrappers (viewOnce/ephemeral) sao desembrulhados;
- metadados (ids/flow token) preservados para resposta estruturada futura;
- E2E: mensagens interativas REAIS da Yelum (12/07) atravessam o motor de
  dispatch e recebem a resposta certa (Automovel/Sim/labels);
- flow nativo -> needs_human com dossie (handoff_trigger 'formulario nativo');
- endereco 2026 digitado direto + 'descreva em suas palavras' respondidos.
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


for name in ("app", "app.services", "app.services.whatsapp"):
    module = sys.modules.setdefault(name, types.ModuleType(name))
    module.__path__ = []

inbound = _load("app.services.whatsapp.evolution_inbound", "app/services/whatsapp/evolution_inbound.py")
pb = _load("app.services.corridor_playbooks", "app/services/corridor_playbooks.py")
dispatch = _load("app.services.insurer_dispatch_service", "app/services/insurer_dispatch_service.py")

SLOTS = {
    "titular_cpf": "11122233344",
    "veiculo_placa": "ABC1D23",
    "local_atual": "Avenida Jose Vieira, 315 - America, Joinville - SC",
    "local_destino": "Rua Piaui, 325, Bucareim, Joinville - SC",
    "problema_descricao": "motor morreu e nao liga mais",
    "telefone_contato": "47988087463",
    "pessoa_no_local": "Rafael",
}


def _payload(message_dict, msg_id="MSG1"):
    return {
        "event": "messages.upsert",
        "instance": "autofleet",
        "data": {
            "key": {"remoteJid": "551131321001@s.whatsapp.net", "fromMe": False, "id": msg_id},
            "pushName": "Yelum Seguradora",
            "message": message_dict,
            "messageTimestamp": 1770000000,
        },
    }


def _outs(session):
    return [t["text"] for t in session["transcript"] if t["direction"] == "out"]


def run():
    print("== SPEC-017 - inbound interativo (botoes/listas/flows) ==\n")
    os.environ.pop("INSURER_DISPATCH_LIVE", None)
    os.environ.pop("DISPATCH_FINALIZE_MODE", None)

    # ---------- buttonsMessage (botoes quick-reply da Yelum) ----------
    btn = inbound.normalize_evolution_inbound(_payload({
        "buttonsMessage": {
            "contentText": "Identifiquei em seu cadastro a placa ABC1D23.\nDeseja continuar com o atendimento para o veículo ou atendimento residencial?",
            "buttons": [
                {"buttonId": "opt_auto", "buttonText": {"displayText": "Automóvel"}, "type": 1},
                {"buttonId": "opt_resid", "buttonText": {"displayText": "Residencial"}, "type": 1},
            ],
        }
    }))
    check("botoes: NAO e mais skip", btn["skip"] is False, btn.get("skip_reason"))
    check("botoes: corpo preservado", "Identifiquei em seu cadastro a placa" in (btn["text"] or ""), btn["text"])
    check("botoes: rotulos renderizados como no export", "Botão 1: Automóvel" in btn["text"] and "Botão 2: Residencial" in btn["text"], btn["text"])
    check("botoes: metadata com ids", (btn["interactive"] or {}).get("kind") == "buttons" and btn["interactive"]["options"][0]["id"] == "opt_auto", btn["interactive"])

    # ---------- templateMessage (hydrated quick replies) ----------
    tpl = inbound.normalize_evolution_inbound(_payload({
        "templateMessage": {"hydratedTemplate": {
            "hydratedContentText": "Você é a pessoa que está local para acompanhar o serviço?",
            "hydratedButtons": [
                {"quickReplyButton": {"displayText": "Sim", "id": "yes"}},
                {"quickReplyButton": {"displayText": "Não", "id": "no"}},
            ],
        }}
    }, msg_id="MSG2"))
    check("template: renderizado", "Botão 1: Sim" in (tpl["text"] or ""), tpl["text"])

    # ---------- listMessage (modal de opcoes: cor do carro) ----------
    lst = inbound.normalize_evolution_inbound(_payload({
        "listMessage": {
            "title": "Opções",
            "description": "Para facilitar a sua localização, poderia me informar a cor do veículo de placa ABC1D23",
            "buttonText": "Opções",
            "sections": [{"title": "", "rows": [
                {"rowId": "c1", "title": "Branco"},
                {"rowId": "c2", "title": "Prata/Cinza"},
                {"rowId": "c5", "title": "Outros"},
                {"rowId": "c6", "title": "Voltar"},
            ]}],
        }
    }, msg_id="MSG3"))
    check("lista: corpo + linhas renderizados", "cor do veículo" in (lst["text"] or "") and "Outros" in lst["text"], lst["text"])
    check("lista: metadata kind=list", (lst["interactive"] or {}).get("kind") == "list", lst["interactive"])

    # ---------- interactiveMessage: single_select (modal nativo) ----------
    sel = inbound.normalize_evolution_inbound(_payload({
        "viewOnceMessage": {"message": {"interactiveMessage": {
            "body": {"text": "Pode me dizer o que aconteceu?\nPara isso selecione uma das opções."},
            "nativeFlowMessage": {"buttons": [
                {"name": "single_select", "buttonParamsJson": "{\"title\":\"Opções\",\"sections\":[{\"rows\":[{\"id\":\"p1\",\"title\":\"Pane ou Defeito\",\"description\":\"Selecione essa opção quando houve falha no funcionamento do veículo\"},{\"id\":\"p2\",\"title\":\"Recarga de bateria\",\"description\":\"Selecione essa opção se precisa de uma recarga na bateria\"}]}]}"},
            ]},
        }}}
    }, msg_id="MSG4"))
    check("single_select (em viewOnce): desembrulhado e renderizado",
          "o que aconteceu" in (sel["text"] or "") and "Pane ou Defeito" in sel["text"], sel["text"])

    # ---------- interactiveMessage: FLOW nativo (formulario) ----------
    flow = inbound.normalize_evolution_inbound(_payload({
        "interactiveMessage": {
            "body": {"text": "Por favor, selecione o botão abaixo para dar continuidade. Para continuar, precisamos entender onde o veículo está parado."},
            "nativeFlowMessage": {"buttons": [
                {"name": "flow", "buttonParamsJson": "{\"flow_cta\":\"Detalhes do local\",\"flow_token\":\"tok123\",\"flow_id\":\"999\"}"},
            ]},
        }
    }, msg_id="MSG5"))
    check("flow: marcador de formulario no texto", "FORMULARIO NATIVO: Detalhes do local" in (flow["text"] or ""), flow["text"])
    check("flow: metadata com token", (flow["interactive"] or {}).get("flow", {}).get("flow_token") == "tok123", flow["interactive"])

    # ---------- texto normal continua igual ----------
    plain = inbound.normalize_evolution_inbound(_payload({"conversation": "Olá, seja bem-vindo"}, msg_id="MSG6"))
    check("texto simples inalterado", plain["text"] == "Olá, seja bem-vindo" and plain["interactive"] is None)

    # ================= E2E: interativas REAIS atravessam o motor =================
    s = dispatch.new_dispatch_session(case_id="i1", company_id="co",
                                      playbook_ref="yelum-auto-whatsapp@v3",
                                      subservice="guincho", slots=dict(SLOTS))
    s = dispatch.start_dispatch(s)
    s = dispatch.handle_insurer_message(s, btn["text"])
    check("E2E: botao 'Deseja continuar...' -> Automóvel", _outs(s)[-1] == "Automóvel", _outs(s)[-1:])
    s = dispatch.handle_insurer_message(s, lst["text"])
    check("E2E: lista da cor -> Outros", _outs(s)[-1] == "Outros", _outs(s)[-1:])
    s = dispatch.handle_insurer_message(s, sel["text"])
    check("E2E: single_select 'o que aconteceu' -> Pane ou Defeito", _outs(s)[-1] == "Pane ou Defeito", _outs(s)[-1:])
    s = dispatch.handle_insurer_message(
        s, "Para informar o endereço onde o veículo está, *escolha apenas uma das opções* abaixo: - Compartilhe a sua localização - Digite o endereço completo do local (sem referência ou complemento) - Ou se preferir, informe o CEP")
    check("E2E: endereco 2026 -> endereco completo digitado (sem clique)",
          _outs(s)[-1] == SLOTS["local_atual"], _outs(s)[-1:])
    s = dispatch.handle_insurer_message(s, "Por favor, descreva em suas palavras o que mais se aproxima da situação do veículo neste momento.")
    check("E2E: 'descreva em suas palavras' -> descricao do caso",
          _outs(s)[-1] == SLOTS["problema_descricao"], _outs(s)[-1:])
    s = dispatch.handle_insurer_message(s, flow["text"])
    check("E2E: FLOW nativo -> needs_human com dossie (interim)",
          s["state"] == "needs_human" and "formulario nativo" in str(s.get("reason") or ""), (s.get("state"), s.get("reason")))

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  FALHOU: {n} -> {d}")
        sys.exit(1)


if __name__ == "__main__":
    run()
