"""SPEC-016.1 - Answer Quality (correções do teste real de 2026-07-03).

Rodar:
    python backend/tests/test_spec016_1_answer_quality.py

Defeitos reproduzidos e corrigidos (todos observados no teste real, com dados
SINTÉTICOS aqui — nunca dados reais):
  D1 - ramo abreviado "RESI" não era reconhecido como residencial
  D2 - boilerplate do PDF virava "assistência confirmada"
  D3 - tabela de coberturas do PDF não era parseada (label+LMI+prêmio+franquia)
  D4 - franquia existia na tabela e o sistema dizia que não havia
  D5 - parcelas sem detalhe ("10 parcela(s)")
  D6 - contexto perdia a apólice selecionada após consulta not_found
  D7 - resposta final dura/sem formatação: LLM volta a redigir; contrato fiscaliza
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


def _load_file_module(dotted_name, relative_path):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(dotted_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[dotted_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _bootstrap():
    for name in ("app", "app.core", "app.services", "app.agents"):
        module = sys.modules.setdefault(name, types.ModuleType(name))
        module.__path__ = []
    _load_file_module("app.core.feature_flags", "app/core/feature_flags.py")
    evidence = _load_file_module("app.services.policy_document_evidence_service", "app/services/policy_document_evidence_service.py")
    facts = _load_file_module("app.services.policy_facts", "app/services/policy_facts.py")
    policy = _load_file_module("app.services.assistance_policy", "app/services/assistance_policy.py")
    composer = _load_file_module("app.services.policy_answer_composer", "app/services/policy_answer_composer.py")
    return evidence, facts, policy, composer


# Página sintética no LAYOUT real de apólice residencial (valores fictícios).
SYNTH_PAGE_3 = """
Tipo de contratação: Edif.+Conteúdo Limite máximo de garantia da Apólice: R$ 500.000,00
*LMGA: O limite máximo de garantia da apólice (L.M.G.A) é a soma das Importâncias seguradas
A tabela indica os valores cobrados por cobertura contratada e também o Limite Máximo de
sinistro decorrente de cada uma das coberturas.
CoberturasLimite
CoberturaParticipação Obrigatória
Incend / Raio / Expl / Fumaça / Q.Aero R$ 400.000,00 R$ 9,50
Danos Elétricos R$ 45.000,00 R$ 199,90 10% dos prejuízos com mínimo de R$ 750,00
RC Familiar R$ 150.000,00 R$ 7,10
Quebra de Vidros / Márm / Granitos R$ 12.000,00 R$ 8,20 10% dos prejuízos com mínimo de R$ 200,00
Assistência 24h Completo R$ 175,00
Gastos com Defesa R$ 9.000,00 R$ 1,10
*As coberturas de Incêndio, Queda de Raios, Explosão, Fumaça, Queda de Aeronave compreendem a
Cobertura Básica conforme Condições Gerais.
"""

SYNTH_PAGE_4 = """
ASSISTÊNCIA 24H PLANO COMPLETO
Confira a lista de serviços disponíveis no plano contratado:
Serviços
Chaveiro Cobertura Provisória de Telhados Pacote Emergencial - Hidráulica e Elétrica
Vidraceiro Vigilância e Segurança Retorno Antecipado ao Domicílio
Troca de Resistência Check-Up Lar (instalações e fixações)
Para conhecer todas as condições da Assistencia 24 horas, acesse seguradora.com.br/residencia.
"""

SYNTH_PAGE_1_BOILERPLATE = """
Obrigado por escolher a seguradora. Você está protegido pelo seu seguro residência
sobre o seu seguro. Para saber detalhes das coberturas e assistências, consulte as
Condições Gerais em seguradora.com.br/residencia.
"""

SYNTH_GLOSSARY = """
Franquia/Participação Obrigatória do Segurado - Valor ou percentual definido na apólice pelo
qual o segurado é responsável em caso de sinistro. A seguradora indeniza apenas os prejuízos que
excedam esse valor.
"""

LOCATOR = {"provider": "infocap", "codfil": "1", "nosnum": "555001"}


def _pages():
    return [
        {"page_number": 1, "content": SYNTH_PAGE_1_BOILERPLATE},
        {"page_number": 3, "content": SYNTH_PAGE_3},
        {"page_number": 4, "content": SYNTH_PAGE_4},
        {"page_number": 6, "content": SYNTH_GLOSSARY},
    ]


def run_extractor(evidence):
    print("\n== D2/D3/D4 - extrator documental v2 (tabela + anti-boilerplate) ==\n")
    items = evidence.extract_policy_document_evidence(
        _pages(),
        question="quais as coberturas e a franquia?",
        document_id="doc-1",
        company_id="co-1",
        policy_locator=LOCATOR,
        content_hash="hash-1",
    )
    texts = [i.get("evidence_text") or "" for i in items]
    blob = " | ".join(texts)

    # D2: boilerplate/glossário/cabeçalho NUNCA viram evidência.
    check("D2: frase 'consulte as' não vira evidência", not any("consulte" in t.lower() for t in texts), texts)
    check("D2: glossário não vira evidência", not any("indeniza apenas" in t.lower() for t in texts), texts)
    check("D2: cabeçalho colado ('CoberturasLimite') não vira evidência", not any("coberturaslimite" in t.lower().replace(" ", "") for t in texts), texts)
    check("D2: linha explicativa 'A tabela indica' não vira evidência", not any("a tabela indica" in t.lower() for t in texts), texts)

    # D3: linhas da tabela viram evidência ESTRUTURADA.
    rows = [i for i in items if i.get("structured", {}).get("kind") == "coverage_row"]
    check("D3: linhas de cobertura parseadas (>=4)", len(rows) >= 4, [r.get("evidence_text") for r in rows])
    danos = next((r for r in rows if "danos el" in (r["structured"].get("label") or "").lower()), None)
    check("D3: label da cobertura extraído", danos is not None, rows)
    check("D3: LMI extraído", danos and danos["structured"].get("lmi") == "R$ 45.000,00", danos)
    check("D3: prêmio extraído", danos and danos["structured"].get("premium") == "R$ 199,90", danos)
    check("D4: franquia/participação extraída", danos and "10%" in (danos["structured"].get("participation") or "") and "600,00" not in (danos["structured"].get("participation") or ""), danos)

    # D3b: plano de assistência da tabela vira evidência de assistência.
    plans = [i for i in items if i.get("structured", {}).get("kind") == "assistance_plan"]
    check("D3b: 'Assistência 24h Completo' vira assistance_plan", len(plans) == 1 and "completo" in (plans[0]["structured"].get("plan") or "").lower(), plans)

    # D3c: serviços do plano (página de assistência) viram evidência de serviços.
    services = [i for i in items if i.get("structured", {}).get("kind") == "assistance_services"]
    check("D3c: lista de serviços capturada", len(services) >= 1, services)
    all_services = " ".join(str(s["structured"].get("services")) for s in services).lower()
    check("D3c: chaveiro e hidráulica presentes nos serviços", "chaveiro" in all_services and ("hidráulica" in all_services or "hidraulica" in all_services), all_services)

    # LMGA da apólice.
    lmga = [i for i in items if i.get("structured", {}).get("kind") == "policy_limit"]
    check("D3d: limite máximo da apólice capturado", len(lmga) == 1 and lmga[0]["structured"].get("amount") == "R$ 500.000,00", lmga)
    return items


def run_facts(facts_mod, evidence_items):
    print("\n== D2/D3 - facts a partir do extrator v2 ==\n")
    pack = {
        "policy_locator": LOCATOR,
        "line_kind_detected": None,
        "product_detected": "RESI",
        "valid_from": "05/06/2026",
        "valid_to": "05/06/2027",
        "active_now": True,
        "coverage_sections": [],
        "official_policy_document_evidence": {"ok": True, "document_status": "evidence_ready", "evidence_items": evidence_items},
    }
    facts = facts_mod.extract_policy_facts(pack)
    cov = [f for f in facts if f["fact_type"] == "coverage" and f["source"] == "official_document"]
    check("facts: coberturas documentais com label limpo", any(f["label"].lower().startswith("danos el") for f in cov), [f["label"] for f in cov])
    check("facts: valor da cobertura = LMI", any(f.get("value") == "R$ 45.000,00" for f in cov), cov)
    ded = [f for f in facts if f["fact_type"] == "deductible"]
    check("facts: franquia por cobertura vira fact deductible", any("10%" in str(f.get("value")) for f in ded), ded)
    assist = [f for f in facts if f["fact_type"] == "assistance"]
    check("facts: assistência do plano confirmada", facts_mod.has_confirmed_assistance(facts) is True, assist)

    # D2: SOMENTE boilerplate → nenhum fact de assistência.
    pack_boiler = dict(pack)
    pack_boiler["official_policy_document_evidence"] = {
        "ok": True,
        "document_status": "evidence_ready",
        "evidence_items": [
            {
                "page_number": 1,
                "evidence_type": "assistance",
                "evidence_text": "sobre o seu seguro. Para saber detalhes das coberturas e assistências, consulte as",
                "confidence": "high",
                "source_document": "official_policy_document",
            }
        ],
    }
    facts_b = facts_mod.extract_policy_facts(pack_boiler)
    check("D2: boilerplate legado não confirma assistência", facts_mod.has_confirmed_assistance(facts_b) is False, facts_b)
    return facts


def run_residential(policy_mod, facts_mod):
    print("\n== D1 - detecção de residencial por abreviação ==\n")
    for value, expected in (("RESI", True), ("resi", True), ("RESIDENCIAL", True), ("Residência Digital", True), ("AUTO", False), ("VIND", False), ("CONS", False)):
        pack = {"product_detected": value, "active_now": True}
        section_pack = {
            **pack,
            "coverage_sections": [{"label": "Assistência Residencial 24h", "amount": None}],
        }
        facts = facts_mod.extract_policy_facts({**section_pack, "policy_locator": LOCATOR, "infocap_financial_fields": [], "installments": []})
        result = policy_mod.apply_residential_assistance_policy(pack, facts)
        check(f"D1: ramo '{value}' residencial={expected}", result["trace"]["residential"] is expected, result["trace"])


def run_composer(composer, facts_mod):
    print("\n== D5/D7 - compositor markdown (fallback) e parcelas ==\n")
    # Chaves reais do conector (_normalize_installments): due_date/paid_at/due_amount.
    installments = [
        {"installment_number": 1, "due_date": "10/01/2026", "due_amount": "120,00", "paid_at": "09/01/2026", "source_fields": {}},
        {"installment_number": 2, "due_date": "10/07/2026", "due_amount": "120,00", "source_fields": {}},
        {"installment_number": 3, "due_date": "10/08/2026", "due_amount": "120,00", "paid_at": "", "source_fields": {}},
    ]
    pack = {
        "policy_locator": LOCATOR,
        "product_detected": "RESI",
        "insurer_detected": "ALLI",
        "policy_status": "ativo",
        "active_now": True,
        "valid_from": "05/06/2026",
        "valid_to": "05/06/2027",
        "coverage_sections": [],
        "installments": installments,
        "structured_coverage_absent": True,
    }
    result = {
        "ok": True,
        "status": "found",
        "selected": {"policy_number": "1234567890", "insurer_key": "ALLI", "product": "RESI", "holder_name": "Cliente Sintetico"},
        "matches": [],
        "policy_evidence_pack": pack,
        "client_name": "Cliente Sintetico",
        "client_document": "12345678900",
    }
    text = composer.compose_policy_answer(question="quais parcelas estão em aberto?", result=result)
    low = text.lower()
    check("D5: parcelas em aberto contadas", "2" in text and ("aberto" in low or "abertas" in low), text)
    check("D5: parcela paga não listada como aberta", "09/01/2026" not in text or "paga" in low, text)
    check("D5: vencimentos listados", "10/07/2026" in text, text)
    check("D7: markdown com linhas em branco entre blocos", "\n\n" in text, repr(text[:200]))
    check("D7: nomes humanizados (Allianz/Residencial)", "allianz" in low and "residencial" in low, text)

    # Fallback de opções em markdown com TODOS os números.
    result_amb = {
        "ok": False,
        "status": "ambiguous_policy",
        "matches": [
            {"policy_number": "111", "insurer_key": "ALLI", "product": "RESI", "valid_from": "01/01/2026", "valid_to": "01/01/2027", "policy_status": "ativo"},
            {"policy_number": "222", "insurer_key": "PORT", "product": "CONS", "valid_from": "01/01/2026", "valid_to": "01/01/2027", "policy_status": "ativo"},
        ],
    }
    text = composer.compose_policy_answer(question="ela tem assistência?", result=result_amb)
    check("D7: opções em markdown numerado", "1." in text and "2." in text and "\n\n" in text, repr(text[:120]))


def _load_nodes():
    constants = types.ModuleType("app.core.constants")
    constants.AGENT_CONTEXT_WINDOW_SIZE = 15
    sys.modules["app.core.constants"] = constants
    state = types.ModuleType("app.agents.state")
    state.AgentState = dict
    sys.modules["app.agents.state"] = state
    utils = types.ModuleType("app.agents.utils")
    utils.extract_text_from_content = lambda c: c if isinstance(c, str) else str(c or "")
    utils.sanitize_ai_message = lambda m: m
    sys.modules["app.agents.utils"] = utils
    ctx = types.ModuleType("app.agents.context")
    ctx.build_task_context = lambda state, max_chars=2000: ""
    sys.modules["app.agents.context"] = ctx
    runnables = types.ModuleType("langchain_core.runnables")
    runnables.RunnableConfig = dict
    sys.modules["langchain_core.runnables"] = runnables
    messages = types.ModuleType("langchain_core.messages")

    class _Msg:
        def __init__(self, content="", **kwargs):
            self.content = content
            for key, value in kwargs.items():
                setattr(self, key, value)

    messages.AIMessage = _Msg
    messages.HumanMessage = _Msg
    messages.SystemMessage = _Msg
    messages.ToolMessage = _Msg
    sys.modules["langchain_core.messages"] = messages
    return _load_file_module("app.agents.nodes", "app/agents/nodes.py")


def run_routing_and_context(nodes):
    print("\n== D6/D7 - roteamento LLM-redige e contexto preservado ==\n")
    os.environ["POLICY_INTELLIGENCE_V2"] = "true"
    try:
        # D7: found NÃO encerra mais direto — volta ao agente (LLM redige).
        state_found = {
            "policy_response_contract": {"provider": "infocap", "result_kind": "found"},
            "final_response": None,
        }
        check("D7: found volta ao agente (LLM redige)", nodes.should_continue_after_tools(state_found) == "agent", None)

        # D7: identity_mismatch continua fail-closed direto (sem LLM).
        state_mm = {
            "policy_response_contract": {"provider": "infocap", "result_kind": "identity_mismatch"},
            "final_response": "A identidade da apolice nao foi confirmada.",
        }
        check("D7: mismatch encerra sem LLM", nodes.should_continue_after_tools(state_mm) == "end", None)

        # D7: guard de opções — TODOS os números obrigatórios na resposta da LLM.
        rendered = "Opções:\n\n1. 111\n2. 222"
        contract = {
            "provider": "infocap",
            "result_kind": "ambiguous_policy",
            "rendered_safe_answer": rendered,
            "required_facts": ["policy_options"],
            "policy_options": [{"policy_number": "111"}, {"policy_number": "222"}],
        }
        bad = "Encontrei duas apólices, uma da Allianz (111) e outra. Qual você quer?"
        check("D7: LLM que omite número é substituída", nodes._guard_infocap_policy_final_response(bad, contract) == rendered, None)
        good = "Encontrei 2 apólices:\n\n1. **111** — Allianz Residencial\n2. **222** — Porto Consórcio\n\nQual delas?"
        check("D7: LLM completa é mantida", nodes._guard_infocap_policy_final_response(good, contract) == good, None)

        # D7: guard anti-invenção de valores — R$ fora dos dados é bloqueado.
        contract_val = {
            "provider": "infocap",
            "result_kind": "found",
            "rendered_safe_answer": "Cobertura Danos Elétricos: R$ 45.000,00 (franquia 10% mín. R$ 750,00).",
            "required_facts": [],
            "allowed_amounts": ["45.000,00", "199,90", "750,00"],
        }
        invented = "A cobertura de Danos Elétricos é de R$ 88.000,00."
        check("D7: valor R$ inventado é bloqueado", nodes._guard_infocap_policy_final_response(invented, contract_val) == contract_val["rendered_safe_answer"], None)
        honest = "A cobertura de **Danos Elétricos** é de R$ 45.000,00, com franquia de 10% (mínimo de R$ 750,00)."
        check("D7: valores corretos são mantidos", nodes._guard_infocap_policy_final_response(honest, contract_val) == honest, None)

        # D6: contexto preserva a apólice selecionada quando um lookup falho volta.
        prev = {"document": "12345678900", "policy_numbers": ["111", "222"], "selected_policy_number": "222", "source": "infocap_customer_catalog"}
        failed_result = {
            "status": "policy_number_not_found",
            "client_document": "12345678900",
            "matches": [{"policy_number": "111"}, {"policy_number": "222"}],
        }
        merged = nodes._merge_infocap_policy_context(prev, nodes._safe_infocap_policy_context(failed_result))
        check("D6: selected preservado após not_found do mesmo cliente", merged and merged.get("selected_policy_number") == "222", merged)

        other_client = {
            "status": "found",
            "client_document": "99988877766",
            "matches": [{"policy_number": "999"}],
            "selected": {"policy_number": "999"},
        }
        merged2 = nodes._merge_infocap_policy_context(prev, nodes._safe_infocap_policy_context(other_client))
        check("D6: cliente novo NÃO herda selected antigo", merged2 and merged2.get("selected_policy_number") == "999" and merged2.get("document") == "99988877766", merged2)
    finally:
        os.environ.pop("POLICY_INTELLIGENCE_V2", None)


def run_briefing(tool_src):
    print("\n== D7 - tool entrega briefing p/ LLM redigir ==\n")
    check("tool: monta briefing estruturado para a LLM", "_build_llm_briefing" in tool_src)
    check("tool: briefing manda formatar em markdown", "markdown" in tool_src.lower())
    check("tool: contrato carrega allowed_amounts", "allowed_amounts" in tool_src)


def run():
    print("== SPEC-016.1 - Answer Quality ==")
    evidence, facts_mod, policy_mod, composer = _bootstrap()
    items = run_extractor(evidence)
    run_facts(facts_mod, items)
    run_residential(policy_mod, facts_mod)
    run_composer(composer, facts_mod)
    nodes = _load_nodes()
    run_routing_and_context(nodes)
    tool_src = (ROOT / "app" / "agents" / "tools" / "infocap_tool.py").read_text(encoding="utf-8")
    run_briefing(tool_src)

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        sys.exit(1)


if __name__ == "__main__":
    run()
