# -*- coding: utf-8 -*-
"""SPEC-038 Bloco B — Templater + Weaver (puros, offline)."""

import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASS = FAIL = 0
FAILURES = []


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  [ok] {name}")
    else:
        FAIL += 1
        FAILURES.append((name, detail))
        print(f"  [X] {name}{': ' + str(detail) if detail else ''}")


def _load(dotted, rel):
    spec = importlib.util.spec_from_file_location(dotted, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = mod
    spec.loader.exec_module(mod)
    return mod


def _bootstrap():
    for name in ("app", "app.services", "app.services.atlas"):
        m = sys.modules.setdefault(name, types.ModuleType(name))
        m.__path__ = []
    _load("app.services.ura_map_service", "app/services/ura_map_service.py")
    # cartographer importa muita coisa; stub só o que o templater usa
    cart = types.ModuleType("app.services.cartographer")
    _real = _load("app.services._cart_real", "app/services/cartographer.py") if False else None
    # reimplementa via import real seria pesado; expõe parse_options/classify_screen reais
    import re

    def parse_options(text):
        labels = []
        for m in re.finditer(r"bot[ãa]o\s*\d+\s*:\s*([^\n|]+)", text, re.IGNORECASE):
            labels.append(m.group(1).strip())
        for m in re.finditer(r"(?:^|\n)\s*(\d{1,2})\s*[-–.)]\s*([^\n|]{2,60})", text):
            labels.append(m.group(2).strip())
        if not labels:
            lines = [ln.strip() for ln in str(text or "").splitlines() if ln.strip()]
            cand = [ln for ln in lines[1:] if 2 <= len(ln) <= 48 and not ln.endswith((".", "?", "!", ":", ",")) and not ln[0].islower() and len(ln.split()) <= 7]
            if len(cand) >= 2:
                labels = cand
        seen, out = set(), []
        for l in labels:
            if l.lower() not in seen:
                seen.add(l.lower()); out.append(l)
        return out

    def classify_screen(text, options):
        if options:
            return "menu"
        if "?" in text or re.search(r"informe|digite|qual", text, re.IGNORECASE):
            return "pergunta"
        return "informativo"

    cart.parse_options = parse_options
    cart.classify_screen = classify_screen
    sys.modules["app.services.cartographer"] = cart
    tmpl = _load("app.services.atlas.templater", "app/services/atlas/templater.py")
    weav = _load("app.services.atlas.weaver", "app/services/atlas/weaver.py")
    return tmpl, weav


def run():
    print("== SPEC-038 Bloco B — Templater + Weaver ==\n")
    tmpl, weav = _bootstrap()

    # 1) PII scrub
    t = tmpl.templatize("Identifiquei a placa QJQ0A91 do CPF 030.743.279-36, tel (47) 98808-7463.")
    check("placa mascarada", "{PLACA}" in t and "QJQ0A91" not in t, t)
    check("cpf mascarado", "{CPF}" in t and "030.743" not in t, t)
    check("telefone mascarado", "{TELEFONE}" in t and "98808" not in t, t)

    # 2) "Placa: QJQ0A91" → valor mascarado
    t2 = tmpl.templatize("Placa: QJQ0A91\nModelo: Gol\nNome: Joao da Silva")
    check("valor rotulado mascarado", "QJQ0A91" not in t2 and "{VALOR}" in t2, t2)

    # 3) screen_node estrutura
    node = tmpl.screen_node("O que aconteceu com a chave?\nBotão 1: Dentro do veículo\nBotão 2: Perda\nBotão 3: Voltar")
    check("nó tem hash", bool(node.get("hash")))
    check("opções extraídas", len(node["options"]) == 3, node["options"])
    check("kind menu", node["kind"] == "menu")

    # 4) ramo/serviço por rota
    ramo, serv = tmpl.infer_ramo_servico(["Guincho (reboque)", "Chaveiro", "Bateria"], "assistencia 24h veiculo")
    check("serviço inferido = guincho", serv == "guincho", serv)
    check("ramo auto", ramo == "auto")

    # 5) weave: sessão com escolha do humano rotula a aresta
    events = [
        {"direction": "in", "text": "Como posso ajudar?\nBotão 1: Guincho\nBotão 2: Chaveiro", "wa_timestamp": "1", "interactive": {"kind": "buttons"}},
        {"direction": "out", "text": "Chaveiro", "wa_timestamp": "2", "interactive": {"kind": "button_reply", "title": "Chaveiro"}},
        {"direction": "in", "text": "Enviaremos o CHAVEIRO. Confirma o endereço?\nBotão 1: Sim\nBotão 2: Não", "wa_timestamp": "3", "interactive": {"kind": "buttons"}},
    ]
    m = {"root": None, "nodes": {}, "edges": {}}
    weav.weave_session(m, events)
    check("2 nós tecidos", len(m["nodes"]) == 2, len(m["nodes"]))
    labeled = [e for e in m["edges"].values() if e["label"] == "Chaveiro"]
    check("aresta rotulada pela escolha do humano", len(labeled) == 1 and not labeled[0]["inferred"], m["edges"])

    # 6) sem escolha (só URA) → aresta sequencial inferida
    events2 = [
        {"direction": "in", "text": "Tela A?\nBotão 1: X\nBotão 2: Y", "wa_timestamp": "1"},
        {"direction": "in", "text": "Tela B final. Obrigado!", "wa_timestamp": "2"},
    ]
    m2 = {"root": None, "nodes": {}, "edges": {}}
    weav.weave_session(m2, events2)
    inferred = [e for e in m2["edges"].values() if e["inferred"]]
    check("aresta sequencial inferida sem clique", len(inferred) == 1, m2["edges"])

    # 7) coverage: opção percorrida = confirmada; não percorrida = lacuna
    weav.compute_coverage(m)
    node_a = next(n for n in m["nodes"].values() if "Guincho" in " ".join(o["label"] for o in n["options"]))
    conf = {o["label"]: o["confidence"] for o in node_a["options"]}
    check("Chaveiro confirmado (seen_once)", conf.get("Chaveiro") in ("seen_once", "confirmed"), conf)
    check("Guincho é lacuna (gap)", conf.get("Guincho") == "gap", conf)
    check("coverage calculada", m["coverage"]["options_total"] >= 2 and "pct" in m["coverage"], m.get("coverage"))

    # 8) v2: casamento FUZZY clique×opção ("*7 -* *Chaveiro*" × "Chaveiro")
    check("fuzzy: rótulo formatado casa com clique", weav.labels_match("*7 -* *Chaveiro*", "Chaveiro"))
    check("fuzzy: não casa rótulos diferentes", not weav.labels_match("Guincho (reboque)", "Chaveiro"))

    # 9) v2: ordem fiel + raiz por frequência de início + paths (transcript)
    mv = {"root": None, "nodes": {}, "edges": {}}
    sessao = [
        {"direction": "in", "text": "Olá! Sou a assistente. O que precisa?\nBotão 1: Guincho\nBotão 2: Chaveiro", "wa_timestamp": "1"},
        {"direction": "out", "text": "Guincho", "wa_timestamp": "2", "interactive": {"kind": "button_reply", "title": "Guincho"}},
        {"direction": "in", "text": "Certo, guincho! Qual o endereço?", "wa_timestamp": "3"},
    ]
    weav.weave_session(mv, sessao, session_at="2026-07-18T10:00:00Z")
    weav.weave_session(mv, list(sessao), session_at="2026-07-18T11:00:00Z")  # 2ª passagem
    weav.compute_coverage(mv)
    greeting = next(nid for nid, n in mv["nodes"].items() if "Sou a assistente" in n["text"])
    check("raiz = tela de abertura (frequência)", mv["root"] == greeting, mv.get("root"))
    orders = [n.get("order") for n in mv["nodes"].values()]
    check("nós têm ordem de primeira aparição", all(isinstance(o, int) for o in orders), orders)
    check("paths/transcript gravados", len(mv.get("paths", [])) == 2 and mv["paths"][0]["steps"][0]["c"] == "Guincho", mv.get("paths"))
    gopt = next(o for n in mv["nodes"].values() for o in n["options"] if o["label"] == "Guincho")
    check("aresta vista 2x = confirmed", gopt["confidence"] == "confirmed" and gopt.get("seen_count") == 2, gopt)

    # 10) v2: VARIANTES — mesma escolha levando a telas diferentes
    mvv = {"root": None, "nodes": {}, "edges": {}}
    base = {"direction": "in", "text": "Deseja continuar?\nBotão 1: Sim\nBotão 2: Não", "wa_timestamp": "1"}
    click = {"direction": "out", "text": "Sim", "wa_timestamp": "2", "interactive": {"kind": "button_reply", "title": "Sim"}}
    weav.weave_session(mvv, [dict(base), dict(click), {"direction": "in", "text": "Já temos seu telefone {TELEFONE}. Confirma?", "wa_timestamp": "3"}])
    weav.weave_session(mvv, [dict(base), dict(click), {"direction": "in", "text": "Informe um telefone para contato.", "wa_timestamp": "3"}])
    weav.compute_coverage(mvv)
    sim = next(o for n in mvv["nodes"].values() for o in n["options"] if o["label"] == "Sim")
    check("variantes registradas (2 destinos)", len(sim.get("variants") or []) == 2, sim.get("variants"))

    # 11) v2: answer_hint em pergunta aberta
    node_h = tmpl.screen_node("Para começar, me informe somente o CPF ou CNPJ do titular da apólice.")
    check("answer_hint {CPF} em pergunta", (node_h.get("answer_hint") or {}).get("placeholder") == "{CPF}", node_h.get("answer_hint"))

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  - {n}: {d}")
        sys.exit(1)


if __name__ == "__main__":
    run()
