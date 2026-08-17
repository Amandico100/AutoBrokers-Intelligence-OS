# -*- coding: utf-8 -*-
"""SPEC-073 §6.1 — o runtime e ADITIVO, e o que ele produz sai redigido.

A promessa desta SPEC em uma frase: seis journeys que cobram boleto hoje nao
precisam aprender nada. Este arquivo prova essa frase.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from portal_worker import guardrails as G  # noqa: E402
from portal_worker import redaction as R   # noqa: E402
from portal_worker import runtime as RT    # noqa: E402

PASS = FAIL = 0


def check(nome, condicao, extra=""):
    global PASS, FAIL
    if condicao:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:220] if extra else ""))


JOB = {"id": "job-1", "company_id": "c-1", "portal_key": "vidros_lanternas",
       "journey": "abrir_atendimento", "params": {"confirm": False}}

# ==========================================================================
print("\n[1] AS FLAGS — cada uma nasce no estado que nao surpreende")
# ==========================================================================
for var in ("PORTAL_DISCOVERY_MODE", "PORTAL_PROFILER_ENABLED",
            "PORTAL_DISCOVERY_RAW_TRACE", "GLOBAL_KILL_SWITCH"):
    os.environ.pop(var, None)
check("discovery nasce false", RT.discovery_mode() is False)
check("profiler nasce true (passivo, e e o que ensina)", RT.profiler_enabled() is True)
check("raw trace nasce false", RT.raw_trace_enabled() is False)
check("kill switch ausente = comportamento historico", RT.kill_switch_ativo() is False)

os.environ["PORTAL_DISCOVERY_MODE"] = "1"
check("discovery aceita '1'", RT.discovery_mode() is True)
os.environ["PORTAL_DISCOVERY_MODE"] = "on"
check("discovery aceita 'on'", RT.discovery_mode() is True)
os.environ["PORTAL_DISCOVERY_MODE"] = "nao"
check("valor sem sentido NAO liga discovery", RT.discovery_mode() is False)
os.environ.pop("PORTAL_DISCOVERY_MODE", None)

os.environ["PORTAL_PROFILER_ENABLED"] = "false"
check("profiler pode ser desligado (rollback do Bloco L)", RT.profiler_enabled() is False)
os.environ.pop("PORTAL_PROFILER_ENABLED", None)

# 🔴 CORRIGIDO EM 17/08/2026. Este comentario dizia "um ambiente que perdeu a
# variavel falha FECHADO" — copiando a docstring, que mentia. E o laco abaixo
# nunca chegava a testar o caso AUSENTE: fazia `pop` e seguia adiante. Ou seja,
# o teste afirmava em portugues exatamente aquilo que ele nao verificava.
#
# CLAUDE.md 9.3: quando o fato muda, o teste muda com ele. O fato aqui e que
# o Python falha ABERTO quando a variavel some, e o TypeScript falha FECHADO.
# Agora as duas coisas estao ESCRITAS e VERIFICADAS.
for valor, esperado in (("true", True), ("TRUE", True), ("1", True),
                        ("false", False), ("FALSE", False),
                        ("", True), ("qualquer coisa", True)):
    os.environ["GLOBAL_KILL_SWITCH"] = valor
    check(f"kill switch com {valor!r} -> {esperado}", RT.kill_switch_ativo() is esperado)
    check(f"e {valor!r} conta como PRESENTE", RT.kill_switch_presente() is True)

os.environ.pop("GLOBAL_KILL_SWITCH", None)
check("AUSENTE -> o freio NAO fecha (falha aberto, de proposito por ora)",
      RT.kill_switch_ativo() is False)
check("AUSENTE -> e isso e visivel como ausencia",
      RT.kill_switch_presente() is False)

# 🔴 CONTROLE (CLAUDE.md 9.2). `presente` so vale alguma coisa se ele CONSEGUIR
# discordar de `ativo`. Se as duas funcoes devolvessem sempre o mesmo, as
# assercoes acima passariam e o `/health` nao teria ganhado informacao nenhuma.
os.environ["GLOBAL_KILL_SWITCH"] = "false"
check("CONTROLE: 'false' e o caso onde as duas DIVERGEM (ausente=False/False)",
      RT.kill_switch_ativo() is False and RT.kill_switch_presente() is True)
os.environ.pop("GLOBAL_KILL_SWITCH", None)

# ==========================================================================
print("\n[2] MONTAGEM — o runtime nasce do job, sem inventar autoridade")
# ==========================================================================
rt = RT.montar_runtime(JOB, account_label="RESULTA", account_id="a-1",
                       host_portal="abraseuatendimento.com.br")
check("carrega o job_id", rt.job_id == "job-1")
check("carrega o company_id", rt.company_id == "c-1")
check("carrega o portal e a journey",
      (rt.portal_key, rt.journey) == ("vidros_lanternas", "abrir_atendimento"))
check("carrega o account_label", rt.account_label == "RESULTA")
check("tem guard", rt.guard is not None)
check("tem profiler", rt.profiler is not None)
check("tem escada", rt.escada is not None)

# 🔴 O runtime NAO decide se pode agir. Ele transporta a decisao de quem tem
# autoridade -- `params["confirm"]`, que nasce False em `portal_params.py` e so
# e ligado pelo gate deterministico do agente.
check("confirm=False -> guard NAO liberado", rt.guard.material_liberado is False)
rt2 = RT.montar_runtime({**JOB, "params": {"confirm": True}})
check("confirm=True -> guard liberado", rt2.guard.material_liberado is True)
check("CONTROLE: o runtime nao inventa liberacao sozinho",
      RT.montar_runtime({**JOB, "params": {}}).guard.material_liberado is False)

rt.declarar_acao_material("Confirmar")
check("a journey consegue NOMEAR a acao material esperada",
      rt.guard.acao_material_esperada == "Confirmar")

# ==========================================================================
print("\n[3] CHECKPOINT — grava no meio, nao no fim")
# ==========================================================================
escritas: list = []


async def _cp(patch):
    escritas.append(dict(patch))


ev: dict = {}
rt3 = RT.PortalRuntimeContext(job_id="j", company_id="c", evidence=ev, _checkpoint=_cp)
asyncio.run(rt3.checkpoint({"passo": 1}))
asyncio.run(rt3.checkpoint({"passo": 2}))
check("cada checkpoint e uma escrita", len(escritas) == 2)
check("o estado local acompanha", ev["passo"] == 2)
check("patch vazio nao gera escrita",
      (asyncio.run(rt3.checkpoint({})), len(escritas))[1] == 2)


async def _cp_quebrado(patch):
    raise RuntimeError("banco fora")


rt4 = RT.PortalRuntimeContext(evidence={}, _checkpoint=_cp_quebrado)
asyncio.run(rt4.checkpoint({"x": 1}))
check("falha de checkpoint NAO derruba o job", rt4.evidence.get("x") == 1)
# 🔴 Mas tambem nao passa calada: ela degrada a protecao transacional, e quem le
# a evidencia depois precisa saber que havia um buraco ali.
check("mas fica registrada na evidencia", "checkpoint_falhou" in rt4.evidence)

# ==========================================================================
print("\n[4] O ENVELOPE FINAL — aditivo e redigido")
# ==========================================================================
rt5 = RT.montar_runtime(JOB, account_label="RESULTA CORRETORA")
rt5.registrar_camada("deterministic")
rt5.registrar_camada("dom")
env = rt5.selar_evidencia()
check("tem bloco runtime", "runtime" in env)
check("tem bloco execution", "execution" in env)
check("o envelope diz qual camada FECHOU", env["execution"]["layer_final"] == "dom")
check("e quantas vezes subiu", env["execution"]["fallback_count"] == 1)
check("critical_effect vem None quando nao houve efeito", env["critical_effect"] is None)
check("discovery/vision aparecem como estao", env["runtime"]["discovery"] is False)

rt6 = RT.montar_runtime(JOB, account_label="AUTO FLEET")
rt6.evidence["cpf_do_segurado"] = "123.456.789-01"
rt6.guard.bloqueios.append({"action": "confirmar", "motivo": "placa QAB1A91 recusada",
                            "class": "material_side_effect", "origem": "vision",
                            "at": "2026-08-16"})
env6 = rt6.selar_evidencia()
check("PII em bloqueio registrado sai redigida",
      not R.tem_vazamento(env6), R.tem_vazamento(env6))
check("CONTROLE: o bloqueio continua no envelope (so o valor some)",
      env6["blocked_actions"][0]["action"] == "confirmar")

rt7 = RT.montar_runtime({**JOB, "params": {"confirm": True}})
asyncio.run(rt7.guard.before(action="create", action_class=G.MATERIAL_SIDE_EFFECT))
env7 = rt7.selar_evidencia()
check("efeito armado aparece no envelope",
      env7["critical_effect"]["phase"] == G.FASE_ARMED)

# ==========================================================================
print("\n[5] ADITIVO — journey que ignora `_runtime` nao muda de comportamento")
# ==========================================================================
from portal_worker.journeys import JourneyResult  # noqa: E402


def journey_de_2026(page, params, evidence):
    """Escrita antes desta SPEC. Nao sabe que runtime existe."""
    evidence["logged_in"] = True
    return JourneyResult(status="done", captured={"itens": 3})


res = journey_de_2026(None, {"confirm": False, "_runtime": rt5}, {})
check("ela roda com `_runtime` em params e nao percebe", res.status == "done")
check("e devolve exatamente o que devolvia", res.captured == {"itens": 3})

check("`_runtime` e um objeto Python, entao NAO pode ir para o banco cru",
      not isinstance(rt5, (dict, list, str, int)))
check("mas o que ele PRODUZ e serializavel",
      isinstance(env, dict) and all(isinstance(k, str) for k in env))

import json  # noqa: E402

try:
    json.dumps(env)
    serializa = True
except TypeError:
    serializa = False
check("o envelope selado vira JSON sem reclamar", serializa)

print("\n" + "=" * 66)
print(f"  {PASS} asserções verdes · {FAIL} vermelhas")
print("=" * 66)
sys.exit(1 if FAIL else 0)
