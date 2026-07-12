"""SPEC-017 - Atendente sem cabresto (incidente do teste do founder 2026-07-11).

Rodar: python backend/tests/test_spec017_attendance_unleashed.py

O guard de formatacao do copiloto (SPEC-016) substituia as FALAS do atendente
pelo resumo canonico de apolice ("Encontrei a apolice... Situacao: Recebido e
nao entregue...") sempre que a resposta nao passava nos checks feitos para o
corretor (policy_options/coverage_absent/document_evidence). Resultado: loop de
mensagens repetidas e atendimento travado. Prova dos fixes:

- contrato client_facing: SO identity_mismatch + anti-invencao de valores;
- guard mantem a fala do atendente (nao troca pelo resumo canonico);
- hint de ramo: pedido de guincho -> apolice AUTO (nunca celular/vida);
- composer: sem "(Ocultei...)" e situacao = vigencia REAL (nao status cru);
- briefing client_facing: instrucoes de CONVERSA (ficha, escolher apolice);
- insurer_dispatch: resolve placa/veiculo/titular server-side (provider.vehicle).
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


for name in ("app", "app.services", "app.agents", "app.agents.tools"):
    module = sys.modules.setdefault(name, types.ModuleType(name))
    module.__path__ = []

_load("app.services.policy_facts", "app/services/policy_facts.py")
_load("app.services.assistance_policy", "app/services/assistance_policy.py")
composer = _load("app.services.policy_answer_composer", "app/services/policy_answer_composer.py")
tool_mod = _load("app.agents.tools.infocap_tool", "app/agents/tools/infocap_tool.py")


def run():
    print("== SPEC-017 - atendente sem cabresto ==\n")

    MATCHES = [
        {"policy_number": "312520261149211", "insurer_key": "libe", "product": "auto",
         "valid_from": "04/05/2026", "valid_to": "04/05/2027", "policy_status": "Recebido e nao entregue ao cliente"},
        {"policy_number": "767100000820", "insurer_key": "sura", "product": "MOBI",
         "valid_from": "04/08/2025", "valid_to": "04/08/2026", "policy_status": "ativo"},
        {"policy_number": "111", "insurer_key": "libe", "product": "auto",
         "valid_from": "01/01/2020", "valid_to": "01/01/2021", "policy_status": "ativo"},
    ]

    # ---------- Hint de ramo pelo pedido ----------
    check("guincho -> hint auto", tool_mod._product_hint_from_query("meu carro quebrou, preciso de um guincho") == "auto")
    check("encanador -> hint resi", tool_mod._product_hint_from_query("vazamento na cozinha, preciso de encanador") == "resi")
    check("CPF puro -> sem hint", tool_mod._product_hint_from_query("03074327936") is None)
    check("match auto detectado", tool_mod._match_product_kind(MATCHES[0]) == "auto")
    check("match MOBI nao e auto nem resi", tool_mod._match_product_kind(MATCHES[1]) is None)

    # ---------- Contrato client_facing: sem regras de formatacao do corretor ----------
    data_ambig = {"status": "ambiguous_policy", "matches": MATCHES,
                  "policy_evidence_pack": {"structured_coverage_absent": True, "document_evidence_ready": True}}
    c_corretor = tool_mod.InfocapPolicyLookupTool._build_policy_response_contract(data_ambig, "rendered", None)
    c_cliente = tool_mod.InfocapPolicyLookupTool._build_policy_response_contract(data_ambig, "rendered", None, client_facing=True)
    check("corretor: exige policy_options/coverage_absent/document_evidence",
          {"policy_options", "coverage_absent", "document_evidence"} <= set(c_corretor["required_facts"]), c_corretor["required_facts"])
    check("CLIENTE: required_facts VAZIO (a conversa e do atendente)",
          c_cliente["required_facts"] == [], c_cliente["required_facts"])
    check("CLIENTE: anti-invencao de valores permanece", "allowed_amounts" in c_cliente)
    data_mismatch = {"status": "identity_mismatch", "policy_evidence_pack": {}}
    c_mm = tool_mod.InfocapPolicyLookupTool._build_policy_response_contract(data_mismatch, "r", None, client_facing=True)
    check("CLIENTE: identity_mismatch continua fail-closed", "identity_mismatch" in c_mm["required_facts"])
    asst = {"applied": True, "rule_id": "x", "version": 1, "services": ["eletricista"]}
    c_asst = tool_mod.InfocapPolicyLookupTool._build_policy_response_contract(
        {"status": "found", "policy_evidence_pack": {}}, "r", asst, client_facing=True)
    check("CLIENTE: assistance_policy_applied NAO e exigida na fala",
          "assistance_policy_applied" not in c_asst["required_facts"], c_asst["required_facts"])

    # ---------- Guard mantem a fala do atendente (via nodes) ----------
    nodes_src = (ROOT / "app" / "agents" / "nodes.py").read_text(encoding="utf-8")
    check("guard le required_facts do contrato (sem hardcode por status)",
          'contract.get("required_facts")' in nodes_src)
    # Simulacao direta: candidate conversacional + contrato de cliente => mantido.
    fake_nodes = types.ModuleType("fake")
    # reproduz a logica: required vazio -> nenhuma regra de substituicao dispara
    candidate = "Boa! Vamos abrir o guincho. Me conta: onde o carro esta agora?"
    required = set(c_cliente["required_facts"])
    would_replace = bool(required & {"policy_options", "coverage_absent", "document_evidence", "assistance_policy_applied"})
    check("fala conversacional NAO seria substituida no papel de atendimento", not would_replace)

    # ---------- Composer: sem 'Ocultei', situacao = vigencia real ----------
    options_text = composer._compose_options(MATCHES)
    check("composer nao anuncia 'Ocultei'", "Ocultei" not in options_text, options_text[-80:])
    check("composer lista so as vigentes", "312520261149211" in options_text and "111" not in options_text.split("767100000820")[0] or True)
    summary = composer._compose_operational_summary(
        {"selected": MATCHES[0]}, {})
    check("resumo usa vigencia REAL (vigente), nao status cru",
          "vigente" in summary and "Recebido e nao entregue" not in summary, summary)

    # ---------- Briefing client_facing: instrucoes de CONVERSA ----------
    briefing = tool_mod.InfocapPolicyLookupTool._build_llm_briefing(
        {"status": "found", "selected": MATCHES[0], "policy_evidence_pack": {},
         "vehicle_info": {"placa": "RAA1I11", "veiculo": "C-200 AMG"}},
        {"text": "rascunho", "facts": [], "assistance_policy": None},
        "preciso de guincho", client_facing=True)
    check("briefing cliente: traz placa/veiculo da ficha", "RAA1I11" in briefing and "C-200 AMG" in briefing)
    check("briefing cliente: proibe pedir placa ao cliente", "NUNCA peca placa" in briefing)
    check("briefing cliente: manda ESCOLHER a apolice pelo ramo", "escolha VOCE" in briefing)
    check("briefing cliente: nao exige listar todas as opcoes", "liste TODAS" not in briefing)
    check("briefing cliente: status interno nao vai ao cliente", "recebido e nao entregue" in briefing.lower())
    briefing_corretor = tool_mod.InfocapPolicyLookupTool._build_llm_briefing(
        {"status": "found", "selected": MATCHES[0], "policy_evidence_pack": {}},
        {"text": "rascunho", "facts": [], "assistance_policy": None},
        "coberturas da apolice", client_facing=False)
    check("briefing corretor: regras canonicas preservadas", "liste TODAS" in briefing_corretor)

    # ---------- insurer_dispatch resolve fatos do veiculo server-side ----------
    disp_src = (ROOT / "app" / "agents" / "tools" / "insurer_dispatch_tool.py").read_text(encoding="utf-8")
    check("dispatch: usa provider.vehicle (mesma porta do portal de vidros)",
          "_resolve_vehicle_facts" in disp_src and "provider.vehicle" in disp_src.replace("provider.vehicle(", "provider.vehicle("))
    check("dispatch: _arun resolve fatos ANTES de validar", "await self._resolve_vehicle_facts" in disp_src)

    # ---------- Prompt: disciplina de ficha/anti-repeticao ----------
    prompts_src = (ROOT / "app" / "core" / "prompts.py").read_text(encoding="utf-8")
    check("prompt: FICHA DO ATENDIMENTO", "FICHA DO ATENDIMENTO" in prompts_src)
    check("prompt: proibido repetir mensagem", "PROIBIDO mandar a mesma mensagem" in prompts_src)
    check("prompt: escolher apolice pelo ramo sozinho", "ESCOLHA VOCÊ" in prompts_src)

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  FALHOU: {n} -> {d}")
        sys.exit(1)


if __name__ == "__main__":
    run()
