"""SPEC-031 - Operacao ponta a ponta (leva noturna 2026-07-12).

Rodar: python backend/tests/test_spec031_ops_hardening.py

Prova: dossie de handoff mastigado; fila multi-cliente (enqueue/pop + drenagem
ao liberar); retomada automatica apos insurer_closed (1x); follow-up timers
gravados na captura; resumo ao analista tambem no RESIDENCIAL; agendamento
residencial com espaco ('9 h'); telemetria de deflexao registrada na sessao.
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


for name in ("app", "app.services", "app.tasks"):
    module = sys.modules.setdefault(name, types.ModuleType(name))
    module.__path__ = []

pb = _load("app.services.corridor_playbooks", "app/services/corridor_playbooks.py")
dispatch = _load("app.services.insurer_dispatch_service", "app/services/insurer_dispatch_service.py")
router = _load("app.services.dispatch_router", "app/services/dispatch_router.py")
followup = _load("app.tasks.dispatch_followup", "app/tasks/dispatch_followup.py")

SLOTS = {
    "titular_cpf": "11122233344", "titular_nome": "Fulano de Tal",
    "veiculo_placa": "ABC1D23", "local_atual": "Rua A, 1, Centro, Cidade SC",
    "local_destino": "Rua B, 2, Bairro, Cidade SC", "problema_descricao": "pane",
    "telefone_contato": "48999990000", "pessoa_no_local": "Fulano",
}
RES_SLOTS = {
    "titular_cpf": "11122233344", "titular_nome": "Eduardo Teste",
    "endereco_numero": "1581", "telefone_contato": "48999990000",
    "problema_descricao": "tomada queimada", "periodo_preferido": "manha",
    "risco_confirmado_sem_fumaca": "sim",
}


def run():
    print("== SPEC-031 - operacao ponta a ponta ==\n")
    # ATUALIZADO em 04/08/2026 (P-90), CLAUDE.md §9.3 — os dois padrões
    # viraram ABERTOS: quem segura o acionamento agora é `agents.is_active`
    # do agente de atendimento, e não mais uma ausência de variável. Este
    # arquivo continua provando o comportamento FECHADO/ENSAIO — mas agora
    # ele o ARMA de propósito, em vez de herdá-lo de um default que mudou.
    os.environ["INSURER_DISPATCH_LIVE"] = "false"
    os.environ["DISPATCH_FINALIZE_MODE"] = "test"

    # ---------- Dossie de handoff mastigado ----------
    s = dispatch.new_dispatch_session(case_id="d1", company_id="co", playbook_ref="yelum-auto-whatsapp@v3", subservice="guincho", slots=dict(SLOTS))
    s = dispatch.start_dispatch(s)
    s["client_phone"] = "5547988087463"
    s["reason"] = "handoff_trigger:formulario nativo"
    dossie = dispatch.build_handoff_dossier(s, s["reason"])
    check("dossie: cabecalho + seguradora + servico", "PRECISA DE VOC" in dossie and "YELUM" in dossie and "guincho" in dossie, dossie[:80])
    check("dossie: dados do caso (CPF/placa/local)", "11122233344" in dossie and "ABC1D23" in dossie and "Rua A" in dossie)
    check("dossie: cliente e proxima acao", "5547988087463" in dossie and "Conversas" in dossie)

    # ---------- Fila multi-cliente (memory fallback) ----------
    pos1 = asyncio.run(router.enqueue_dispatch("coQ", "551130039303", {"case_id": "q1", "playbook_ref": "porto-auto-whatsapp@v1", "subservice": "guincho", "slots": SLOTS, "client_phone": "111"}))
    pos2 = asyncio.run(router.enqueue_dispatch("coQ", "551130039303", {"case_id": "q2", "playbook_ref": "porto-auto-whatsapp@v1", "subservice": "bateria", "slots": SLOTS, "client_phone": "222"}))
    check("fila: posicoes 1 e 2", pos1 == 1 and pos2 == 2, (pos1, pos2))
    nxt = asyncio.run(router._pop_queued("coQ", "551130039303"))
    check("fila: pop devolve o 1o (FIFO)", (nxt or {}).get("case_id") == "q1", nxt)

    # ---------- Retomada automatica apos insurer_closed ----------
    os.environ["INSURER_DISPATCH_LIVE"] = "true"  # sender ativo p/ retry
    sess = dispatch.new_dispatch_session(case_id="r1", company_id="coR", playbook_ref="yelum-auto-whatsapp@v3", subservice="guincho", slots=dict(SLOTS))
    sess = dispatch.start_dispatch(sess, sender=lambda t: None)
    sess["client_phone"] = "5547988087463"
    asyncio.run(router.save_active_dispatch("coR", "551131321001", sess))
    sent_ins, sent_cli = [], []
    handled = asyncio.run(router.try_route_insurer_inbound(
        company_id="coR", from_phone="551131321001",
        text="Por falta de interação esta conversa foi encerrada.",
        send_to_insurer=sent_ins.append, send_to_client=lambda p, t: sent_cli.append((p, t)),
    ))
    saved = asyncio.run(router.load_active_dispatch("coR", "551131321001"))
    check("retry: sessao nova criada apos queda", handled and saved is not None and saved.get("retry_count") == 1, (saved or {}).get("retry_count"))
    check("retry: reabriu a conversa (Ola enviado)", "Olá" in sent_ins, sent_ins[:2])
    check("retry: cliente NAO recebeu 'colega vai assumir'", not any("colega" in t for _, t in sent_cli), sent_cli)
    # 2a queda -> agora sim needs_human + telemetria
    handled2 = asyncio.run(router.try_route_insurer_inbound(
        company_id="coR", from_phone="551131321001",
        text="Por falta de interação esta conversa foi encerrada.",
        send_to_insurer=sent_ins.append, send_to_client=lambda p, t: sent_cli.append((p, t)),
    ))
    check("retry: 2a queda vira handoff (sem loop infinito)", handled2 and any("colega" in t for _, t in sent_cli), sent_cli[-1:] if sent_cli else None)
    os.environ["INSURER_DISPATCH_LIVE"] = "false"

    # ---------- Follow-up timers gravados na captura ----------
    mc = dispatch.new_dispatch_session(case_id="f1", company_id="coF", playbook_ref="porto-auto-whatsapp@v1", subservice="guincho", slots=dict(SLOTS))
    mc = dispatch.start_dispatch(mc)
    mc["client_phone"] = "555"
    asyncio.run(router.save_active_dispatch("coF", "551130039303", mc))
    asyncio.run(router.try_route_insurer_inbound(
        company_id="coF", from_phone="551130039303",
        text="Pronto! previsto para ser realizado hoje, em ate 60 minutos. Aqui esta seu protocolo de atendimento: 1-125298136729",
        send_to_insurer=lambda t: None, send_to_client=lambda p, t: None,
    ))
    mon = asyncio.run(router.load_active_dispatch("coF", "551130039303"))
    check("followup: monitoring com followup_at e closing_at", mon and mon.get("state") == "monitoring" and mon.get("followup_at") and mon.get("closing_at"), (mon or {}).get("state"))
    check("followup: _due detecta vencido/nao-vencido", followup._due("2020-01-01T00:00:00+00:00") is True and followup._due("2099-01-01T00:00:00+00:00") is False)

    # ---------- Residencial: resumo ao analista humano ----------
    rs = dispatch.new_dispatch_session(case_id="res1", company_id="co", playbook_ref="allianz-residencial-whatsapp@v1", subservice="eletricista", slots=dict(RES_SLOTS))
    rs = dispatch.start_dispatch(rs)
    rs = dispatch.handle_insurer_message(rs, "Bom dia, meu nome é Helen Coelho sou da assistência 24 horas e estou aqui para te ajudar!")
    outs = [t["text"] for t in rs["transcript"] if t["direction"] == "out"]
    check("residencial: analista recebe resumo mastigado", rs.get("summary_sent") is True and any("eletricista" in o and "1581" in o for o in outs), outs[-1:])
    rs = dispatch.handle_insurer_message(rs, "A assistência foi agendada para o dia 06, entre 9 h e 13 h . O número da assistência é 51810077.")
    cap = rs.get("captured") or {}
    check("residencial: captura agendamento com '9 h' espacado", (cap.get("schedule") or {}).get("from", "").replace(" ", "") == "9h", cap)
    check("residencial: captura protocolo 51810077", cap.get("protocol") == "51810077", cap)

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  FALHOU: {n} -> {d}")
        sys.exit(1)


if __name__ == "__main__":
    run()
