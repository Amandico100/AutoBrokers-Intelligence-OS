"""SPEC-034 Onda 2 - Registro + Mapa de URA + Cartografo + Simulador + Cerebro v2.

Rodar: python backend/tests/test_spec034_onda2.py

- REGISTRO: numeros da planilha ATIVOS; divergentes anotados sem uso; Youse sem
  WhatsApp; fallback do resolve_insurer_contact (env continua mandando);
- MAPA: normalizacao/hash estaveis (protocolos nao mudam o hash); diff detecta
  telas novas/menus alterados; safe_auto_apply so quando SO adiciona;
- CARTOGRAFO: explora menus (BFS), FREIO na confirmacao final (nunca confirma),
  FREIO no ramo de sinistro (nao entra), responde CPF/placa da apolice de teste,
  aborta ramo sem dado, respeita orcamento de mensagens;
- SIMULADOR: replay de conversa real Porto contra o playbook atual -> ok e freio;
- CEREBRO v2: prompt inclui o mapa quando fornecido.
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


for name in ("app", "app.services", "app.core"):
    module = sys.modules.setdefault(name, types.ModuleType(name))
    module.__path__ = []

pb = _load("app.services.corridor_playbooks", "app/services/corridor_playbooks.py")
reg = _load("app.services.insurer_registry", "app/services/insurer_registry.py")
ums = _load("app.services.ura_map_service", "app/services/ura_map_service.py")
carto = _load("app.services.cartographer", "app/services/cartographer.py")
eng = _load("app.services.insurer_dispatch_service", "app/services/insurer_dispatch_service.py")
sim = _load("app.services.ura_simulator", "app/services/ura_simulator.py")

# ATUALIZADO em 04/08/2026 (P-90), CLAUDE.md §9.3 — `DISPATCH_FINALIZE_MODE`
# nasce em `live`. O freio de finalizacao era o padrao porque o Founder testava
# no proprio celular; decisao dele, o unico interruptor passou a ser
# `agents.is_active` do agente de atendimento.
#
# Este arquivo SIMULA a URA contra um script gravado — ele existe para ensaiar,
# e `reached_finalize` significa "o motor parou na tela que ABRE o servico".
# Com o freio solto ele responderia "Confirmar solicitacao" a uma seguradora de
# mentira e nunca chegaria a um estado encerrado. O ensaio agora e ARMADO de
# proposito, em vez de herdado de um padrao que mudou.
os.environ["DISPATCH_FINALIZE_MODE"] = "test"


def run():
    print("== SPEC-034 Onda 2 ==\n")

    # ---------- REGISTRO ----------
    check("registro: Porto usa numero da planilha", reg.registry_whatsapp("porto") == "551130039303")
    check("registro: Yelum mantem numero da planilha (validado 11/07), alternativo anotado",
          reg.registry_whatsapp("yelum") == "551131321001"
          and reg.get_insurer("yelum")["whatsapp_alternativo"] == "551132061414")
    check("registro: Youse sem WhatsApp (nunca tentar)", reg.registry_whatsapp("youse") == "")
    check("registro: confirmacoes 14/07 aplicadas (tokio novo oficial; hdi/bradesco ok; yelum segue divergente)",
          reg.get_insurer("tokio")["whatsapp"] == "5511995786546"
          and all(reg.get_insurer(k)["status_validacao"] == "confirmado"
                  for k in ("bradesco", "hdi", "tokio"))
          and reg.get_insurer("yelum")["status_validacao"] == "divergente")
    targets = reg.mapping_targets()
    check("registro: agenda do cartografo tem 11 alvos (12 - Youse)",
          len(targets) == 11, len(targets))
    check("resolve_insurer_contact: env continua mandando",
          pb.resolve_insurer_contact("porto", env={"INSURER_CONTACT_PORTO_ASSISTENCIA": "5500000000"}) == "5500000000")
    check("resolve_insurer_contact: sem env cai no registro (planilha)",
          pb.resolve_insurer_contact("porto", env={}) == "551130039303",
          pb.resolve_insurer_contact("porto", env={}))
    check("resolve_insurer_contact: zurich agora resolve (nova seguradora, sem env)",
          pb.resolve_insurer_contact("zurich", env={}) == "551128902121")

    # ---------- MAPA: hash/normalizacao/diff ----------
    t1 = "Seu protocolo e 20260713-1234. Aguarde o prestador."
    t2 = "Seu protocolo e 20260801-9876.   Aguarde o prestador."
    check("mapa: protocolo/numeros nao mudam o hash da tela",
          ums.node_hash(t1) == ums.node_hash(t2))
    old = {"nodes": {"a": {"text": "o que voce precisa?", "kind": "menu", "hash": "h1",
                           "options": [{"label": "Guincho"}, {"label": "Bateria"}]}}}
    new = {"nodes": {"a": {"text": "o que voce precisa?", "kind": "menu", "hash": "h1",
                           "options": [{"label": "Guincho"}, {"label": "Bateria"}, {"label": "Taxi"}]},
                     "b": {"text": "entendi. o que voce precisa?", "kind": "menu", "hash": "h2",
                           "options": [{"label": "Recarga"}]}}}
    d = ums.diff_maps(old, new)
    check("mapa: diff detecta tela nova + menu alterado",
          len(d["added"]) == 1 and len(d["changed_options"]) == 1 and not d["removed"], d)
    check("mapa: menu alterado NAO e safe_auto_apply", d["safe_auto_apply"] is False)
    d2 = ums.diff_maps(old, {"nodes": {**old["nodes"], "b": new["nodes"]["b"]}})
    check("mapa: so-adicionou -> safe_auto_apply", d2["safe_auto_apply"] is True, d2)

    # ---------- CARTOGRAFO ----------
    exp = carto.new_exploration(insurer_key="porto", ramo="auto",
                                test_data={"cpf": "00081352697", "placa": "ABC1D23"})
    menu_raiz = "Ola! Escolha a opcao desejada:\nBotao 1: Seguro Auto\nBotao 2: Servico para residencia\nBotao 3: Sinistro de terceiro\nBotao 4: Informar outro CPF/CNPJ"
    r0 = carto.handle_insurer_message(exp, menu_raiz)
    check("cartografo: RE-IDENTIFICA primeiro (URA lembra o numero)", r0 == "Informar outro CPF/CNPJ", r0)
    exp["last_node"] = None
    r1 = carto.handle_insurer_message(exp, menu_raiz)
    check("cartografo: depois explora a 1a opcao segura", r1 == "Seguro Auto", r1)
    r2 = carto.handle_insurer_message(exp, "Certo! Digite o seu CPF ou CNPJ para localizar o cadastro.")
    check("cartografo: responde o CPF da apolice de teste", r2 == "00081352697", r2)
    r3 = carto.handle_insurer_message(exp, "Encontrei! O que voce precisa?\nBotao 1: Guincho (reboque)\nBotao 2: Bateria\nBotao 3: Chaveiro para veiculo")
    check("cartografo: segue explorando (Guincho)", r3 == "Guincho (reboque)", r3)
    r4 = carto.handle_insurer_message(exp, "Confira o resumo da sua solicitacao. Como voce quer prosseguir?\nBotao 1: Confirmar solicitacao\nBotao 2: Alterar informacoes\nBotao 3: Sair e nao agendar")
    check("cartografo: FREIO na confirmacao final -> Sair, NUNCA confirma",
          r4 == "Sair e nao agendar", r4)
    node_final = [n for n in exp["nodes"].values() if n["kind"] == "finalize"]
    check("cartografo: tela final marcada como finalize no mapa", len(node_final) == 1)
    exp2 = carto.new_exploration(insurer_key="porto", ramo="auto", test_data={"cpf": "1"})
    r5 = carto.handle_insurer_message(exp2, "Escolha:\nBotao 1: Sinistro de colisao\nBotao 2: Assistencia 24h")
    check("cartografo: FREIO sinistro -> pula para a proxima opcao segura",
          r5 == "Assistencia 24h", r5)
    r6 = carto.handle_insurer_message(exp2, "Informe a placa do veiculo:")
    check("cartografo: dado que nao temos -> aborta o ramo (needs_data)",
          any(n["kind"] == "needs_data" for n in exp2["nodes"].values()), r6)
    exp3 = carto.new_exploration(insurer_key="x", ramo="auto", test_data={})
    exp3["msg_count"] = carto.MAX_MESSAGES_PER_SESSION
    r7 = carto.handle_insurer_message(exp3, "menu\nBotao 1: A")
    check("cartografo: orcamento de mensagens estourado -> aborta em silencio",
          r7 is None and exp3["state"] == "aborted", (r7, exp3["state"]))
    m = carto.exploration_to_map(exp)
    check("cartografo: exporta mapa canonico (root + nodes + meta)",
          m["root"] and len(m["nodes"]) >= 3 and m["meta"]["insurer_key"] == "porto")

    # ---------- SIMULADOR ----------
    slots = {"titular_cpf": "00081352697", "titular_nome": "Teste", "veiculo_placa": "ABC1D23",
             "local_atual": "Rua A, 1, Centro, Joinville SC", "local_destino": "Oficina B, Rua C, 2, Centro, Joinville SC",
             "problema_descricao": "bateria", "telefone_contato": "47988087463",
             "pessoa_no_local": "Teste", "servico_texto": "Bateria", "servico_opcao": "2"}
    script = [
        {"screen": "Ola, Amandus! Para comecar, escolha a opcao desejada digitando o numero: Seguro Auto | Informar outro CPF/CNPJ", "expected": "Informar outro CPF/CNPJ"},
        {"screen": "Certo! Digite o seu *CPF ou CNPJ* para eu localizar o cadastro.", "expected": "00081352697"},
        {"screen": "Ola, Amandus! Para comecar, escolha a opcao desejada digitando o numero: Seguro Auto | Informar outro CPF/CNPJ", "expected": "Seguro Auto"},
        {"screen": "Entendi. O que voce precisa?\nBotao 1: Recarga de bateria\nBotao 2: Bateria nova", "expected": "Recarga de bateria"},
        {"screen": "Confira o resumo. Como voce quer prosseguir?\nBotao 1: Confirmar solicitacao\nBotao 2: Sair e nao agendar", "expected": None},
    ]
    res = sim.simulate("porto-auto-whatsapp@v1", "bateria", slots, script)
    check("simulador: replay Porto sem divergencias + freio de teste no final",
          res["ok"] and res["reached_finalize"], res)
    script_div = [{"screen": "Certo! Digite o seu *CPF ou CNPJ* para eu localizar o cadastro.",
                   "expected": "99999999999"}]
    res2 = sim.simulate("porto-auto-whatsapp@v1", "bateria", slots, script_div)
    check("simulador: divergencia detectada e reportada",
          not res2["ok"] and res2["divergences"], res2["divergences"][:1])
    st = sim.script_from_transcript([
        {"direction": "in", "text": "menu?"}, {"direction": "out", "text": "1"},
        {"direction": "in", "text": "aguarde"},
    ])
    check("simulador: script extraido do transcript real (Espelho)",
          st == [{"screen": "menu?", "expected": "1"}, {"screen": "aguarde", "expected": None}], st)

    # ---------- CEREBRO v2 ----------
    s = eng.new_dispatch_session(case_id="c", company_id="co",
                                 playbook_ref="porto-auto-whatsapp@v1", subservice="bateria",
                                 slots=dict(slots))
    mapa = {"nodes": {"n1": {"text": "o que voce precisa?", "kind": "menu", "hash": "h",
                             "options": [{"label": "Bateria", "reply": "Bateria", "leads_to": None}]}}}
    # O ROTULO MUDOU EM 05/08/2026, E O TESTE MUDA COM ELE (CLAUDE.md §9.3).
    #
    # Este teste afirmava que o prompt dizia "MAPA COMPLETO DA URA". Era
    # verdade, e era o defeito: 📊 `render_map_for_llm` corta em 30 telas e a
    # Allianz tem 1.323. O prompt garantia ao modelo que aquilo era o mapa
    # inteiro — e o modelo nao tem como desconfiar do proprio prompt.
    #
    # A LICAO NAO MORRE, ela migra: o que importava era "o mapa chega ao
    # prompt quando existe, e nao aparece quando nao existe". Isso continua
    # sendo testado. O que mudou e que agora o rotulo tambem tem de dizer o
    # TAMANHO da amostra — porque foi a afirmacao de completude que criava o
    # erro silencioso.
    msgs = eng.build_human_phase_messages(s, "tela nova qualquer", ura_map=mapa)
    prompt_com = msgs["system"] + msgs["user"]
    check("cerebro v2: prompt inclui as telas conhecidas da URA",
          "TELAS CONHECIDAS DA URA" in prompt_com)
    check("cerebro v2: e declara quantas de quantas (nao afirma completude)",
          "de 1 telas observadas" in prompt_com
          and "MAPA COMPLETO DA URA" not in prompt_com)
    check("cerebro v2: e autoriza o modelo a dizer que nao reconhece a tela",
          "nao a reconhece" in prompt_com or "não a reconhece" in prompt_com)
    msgs2 = eng.build_human_phase_messages(s, "tela nova qualquer")
    check("cerebro v2: sem mapa, prompt continua como antes (retrocompativel)",
          "TELAS CONHECIDAS DA URA" not in msgs2["system"] + msgs2["user"])

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  FALHOU: {n} -> {d}")
        sys.exit(1)


if __name__ == "__main__":
    run()
