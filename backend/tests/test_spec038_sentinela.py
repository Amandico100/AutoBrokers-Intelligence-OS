# -*- coding: utf-8 -*-
"""SPEC-038 Bloco C — Sentinela de Rotas (classificacao de drift) + parser do
formulario nativo (Pedra de Roseta). Puros/standalone."""

import importlib.util
import json
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


def run():
    print("== SPEC-038 Bloco C — Sentinela + Formulario Nativo ==\n")
    for name in ("app", "app.core", "app.services", "app.services.atlas", "app.services.whatsapp"):
        m = sys.modules.setdefault(name, types.ModuleType(name)); m.__path__ = []
    sen = _load("app.services.atlas.route_sentinel", "app/services/atlas/route_sentinel.py")

    # 1) drift ESTRUTURAL: opção de menu mudou
    d1 = {"added": [], "removed": [], "changed_options": [{"screen": "menu"}]}
    check("menu alterado = structural", sen.classify_severity(d1, {}) == "structural")

    # 2) drift ESTRUTURAL: tela nova que é menu
    new_map = {"nodes": {"h1": {"text": "Nova pergunta: qual servico?", "kind": "menu"}}}
    d2 = {"added": ["Nova pergunta: qual servico?"], "removed": [], "changed_options": []}
    check("tela-menu nova = structural", sen.classify_severity(d2, new_map) == "structural")

    # 3) drift COSMÉTICO: tela informativa nova (texto), sem mudar fluxo
    info_map = {"nodes": {"h2": {"text": "Aguarde um momento por favor", "kind": "informativo"}}}
    d3 = {"added": ["Aguarde um momento por favor"], "removed": [], "changed_options": []}
    check("tela informativa nova = cosmetic", sen.classify_severity(d3, info_map) == "cosmetic")

    # 4) script do simulador a partir do transcript observado
    observed = {"nodes": {"a": {"text": "Menu: 1 Guincho 2 Chaveiro"}, "b": {"text": "Confirma endereco?"}},
                "paths": [{"at": "t", "steps": [{"n": "a", "c": "Guincho"}, {"n": "b", "c": "Sim"}]}]}
    script = sen._script_from_observed(observed)
    check("script tem 2 telas com respostas", len(script) == 2 and script[0]["expected"] == "Guincho", script)

    # 5) PARSER DO FORMULÁRIO NATIVO (Pedra de Roseta) — payload REAL da HDI
    #    (via observer_intake._parse_native_form)
    intake = types.ModuleType("app.services.atlas.observer_intake")
    # importa só a função pura sem carregar deps: reexecuta o arquivo com stubs
    for dep in ("app.core.database", "app.core.redis", "app.services.insurer_registry",
                "app.services.whatsapp.evolution_inbound", "app.services.whatsapp.providers",
                "app.services.whatsapp.providers.evolution_go"):
        sys.modules.setdefault(dep, types.ModuleType(dep))
    sys.modules["app.core.database"].get_supabase_client = lambda: None
    async def _r():
        return None
    sys.modules["app.core.redis"].get_async_redis_client = _r
    sys.modules["app.services.insurer_registry"].INSURER_REGISTRY = {}
    sys.modules["app.services.whatsapp.evolution_inbound"]._interactive_from_message = lambda m: None
    sys.modules["app.services.whatsapp.evolution_inbound"]._unwrap_message = lambda m: m
    sys.modules["app.services.whatsapp.providers.evolution_go"].go_event_to_v2_envelope = lambda b: {"event": "unknown"}
    oi = _load("app.services.atlas.observer_intake", "app/services/atlas/observer_intake.py")

    params = {
        "rb_EmGaragemOuEstacionamento": "1", "rb_NivelDaRua": "4",
        "ckb_SituacoesVeiculo": ["nenhuma_opcoes"], "flow_token": "abc:551155020700:5547996274743",
        "wa_flow_response_params": {
            "flow_id": "857030507196739",
            "flow_name": "Automovel - Detalhes do atendimento",
            "response_message": json.dumps({"screens": [
                {"id": "scr1", "title": "Situacao do veiculo", "components": [
                    {"name": "rb_EmGaragemOuEstacionamento", "label": "O veiculo esta em garagem?"},
                    {"name": "rb_NivelDaRua", "label": "Nivel da rua?"}]}]}),
        },
    }
    extra = {"name": "galaxy_message", "paramsJSON": json.dumps(params)}
    nf = oi._parse_native_form(extra)
    check("form nativo: flow_id extraido", nf and nf.get("flow_id") == "857030507196739", nf)
    check("form nativo: nome do flow", nf and "Detalhes" in (nf.get("flow_name") or ""), nf)
    campos = {c["name"]: c for c in (nf or {}).get("fields", [])}
    check("form nativo: campo com label + resposta",
          "rb_EmGaragemOuEstacionamento" in campos
          and campos["rb_EmGaragemOuEstacionamento"]["answer"] == "1"
          and "garagem" in (campos["rb_EmGaragemOuEstacionamento"]["label"] or "").lower(), campos)
    check("form nativo: flow_token NAO guardado (volatil)", "flow_token" not in json.dumps(nf), nf)

    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAILURES:
        for n, d in FAILURES:
            print(f"  - {n}: {d}")
        sys.exit(1)


if __name__ == "__main__":
    run()
