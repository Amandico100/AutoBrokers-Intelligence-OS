# -*- coding: utf-8 -*-
"""SPEC-073 Bloco A/K — a rede que reprova "modernizar" quebrando producao.

Este arquivo NAO reimplementa parser de seguradora nenhuma. Ele prova apenas os
CONTRATOS EXTERNOS: o que o resto do sistema tem direito de assumir sobre o
portal-worker, e que a SPEC-073 prometeu nao mexer.

A distincao importa. Um teste que copia a logica da journey concorda com o
autor, nunca com a producao (`test_o_atendente_alcanca_o_portal_de_vidros.py`
ja registra isso). Aqui a pergunta e outra: **as portas continuam no lugar?**
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

PASS = FAIL = 0


def check(nome, condicao, extra=""):
    global PASS, FAIL
    if condicao:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:220] if extra else ""))


# ==========================================================================
print("\n[1] INVENTARIO DO REGISTRY — adicao pode; remocao nao")
# ==========================================================================
from portal_worker.journeys import (  # noqa: E402
    JOURNEY_COBRANCA, JOURNEYS, JourneyResult, get_journey,
    portais_com_cobranca, tem_cobranca)

BASELINE = (
    "allianz_corretor.cobranca_sweep",
    "hdi_corretor.cobranca_sweep",
    "tokiomarine_corretor.cobranca_sweep",
    "yelum_corretor.cobranca_sweep",
    "mapfre_corretor.cobranca_sweep",
    "zurich_corretor.cobranca_sweep",
    "vidros_lanternas.abrir_atendimento",
)
for chave in BASELINE:
    check(f"`{chave}` continua no registry", chave in JOURNEYS)

# 🔴 Subconjunto, nao igualdade: uma journey legitima que entre antes do merge
# nao pode reprovar a SPEC. O que nao pode e SUMIR.
check("o registry so cresceu (>= 14 entradas da baseline)", len(JOURNEYS) >= 14, len(JOURNEYS))

for chave in BASELINE:
    portal, jn = chave.split(".", 1)
    check(f"`{chave}` resolve para uma funcao importavel", callable(get_journey(portal, jn)))

check("journey inexistente devolve None (e nao derruba o poll)",
      get_journey("portal_que_nao_existe", "x") is None)
check("journey vazia devolve None", get_journey("", "") is None)

# ==========================================================================
print("\n[2] `portais_com_cobranca()` continua DERIVADO do registry")
# ==========================================================================
cob = portais_com_cobranca()
check("os 6 portais de cobranca da baseline continuam listados",
      set(cob) >= {"allianz_corretor", "hdi_corretor", "tokiomarine_corretor",
                   "yelum_corretor", "mapfre_corretor", "zurich_corretor"}, cob)
check("a lista sai ORDENADA (retomada previsivel)", cob == sorted(cob), cob)
check("vidros NAO entra na cobranca", "vidros_lanternas" not in cob, cob)
check("tem_cobranca concorda com a lista",
      all(tem_cobranca(p) for p in cob) and not tem_cobranca("vidros_lanternas"))

fonte = inspect.getsource(sys.modules["portal_worker.journeys"])
corpo = fonte[fonte.find("def portais_com_cobranca"):][:800]
# Procurar o VALOR (`cobranca_sweep`) aqui seria errado e a primeira versao
# deste teste errou assim: o corpo referencia a CONSTANTE `JOURNEY_COBRANCA`, e
# e exatamente isso que se quer -- um literal solto no corpo seria a segunda
# fonte de verdade voltando pela porta dos fundos.
check("ele deriva do registry e da constante, sem segunda lista literal",
      "JOURNEYS" in corpo and "JOURNEY_COBRANCA" in corpo, corpo[:220])
check("nenhum nome de seguradora aparece hardcoded na funcao",
      not any(s in corpo for s in ('"allianz_corretor"', '"hdi_corretor"')), corpo[:200])

# ==========================================================================
print("\n[3] CONTRATO DO `JourneyResult` — journey antiga nao aprende nada")
# ==========================================================================
r = JourneyResult(status="done")
check("constroi so com status", r.status == "done")
check("captured nasce dict vazio", r.captured == {})
check("screenshots nasce lista vazia", r.screenshots == [])
check("message nasce string vazia", r.message == "")
for st in ("done", "needs_human", "failed"):
    check(f"status `{st}` continua aceito", JourneyResult(status=st).status == st)

campos = set(JourneyResult.__dataclass_fields__)
check("o contrato continua com os MESMOS 4 campos — nada novo obrigatorio",
      campos == {"status", "captured", "screenshots", "message"}, campos)

# ==========================================================================
print("\n[4] CONTRATO DO WORKER — a assinatura da journey nao mudou")
# ==========================================================================
from portal_worker import worker as W  # noqa: E402

src_run = inspect.getsource(W._run_job)
check("o worker continua chamando journey_fn(page, params, evidence)",
      "journey_fn(page, params, evidence)" in src_run)
check("o teto duro por journey continua existindo",
      "JOB_TIMEOUT_SECONDS" in src_run and "wait_for" in src_run)
check("o runtime entra por chave RESERVADA em params, sem trocar a assinatura",
      'params["_runtime"]' in src_run)

# 🔴 O contrato de compatibilidade em uma frase: uma journey que so olha os tres
# argumentos de sempre nao precisa saber que a SPEC-073 existiu.
def _journey_antiga(page, params, evidence):
    evidence["passei"] = True
    return JourneyResult(status="done", captured={"logged_in": True})


fake_params = {"confirm": False, "_runtime": object(), "_job_id": "x"}
fake_ev = {}
res = _journey_antiga(None, fake_params, fake_ev)
check("journey que IGNORA `_runtime` continua funcionando",
      res.status == "done" and fake_ev["passei"] is True)

# ==========================================================================
print("\n[5] O QUE A SPEC-073 PROMETEU NAO TOCAR")
# ==========================================================================
INTOCADOS = ("allianz_corretor.py", "hdi_corretor.py", "mapfre_corretor.py")
import subprocess  # noqa: E402

# ⚠️ 16/08/2026 — a JANELA desta conferência mudou; a promessa que ela guarda é
# a mesma.
#
# Ela comparava `baseline..HEAD`, e isso confundia duas coisas diferentes: "a
# SPEC-073 não tocou nisto" (verdade histórica, permanente) e "ninguém nunca
# mais tocará nisto" (que nunca foi prometido por ninguém). Toda SPEC seguinte
# que encostasse num desses arquivos reprovaria um teste da 073 — e um teste
# que reprova por motivo legítimo ensina a equipe a ignorá-lo.
#
# 📊 Foi exatamente o que aconteceu: a SPEC-075 Bloco U tem mandato explícito
# para adaptar `billing_collection.py` (§30 e §45 da 075 o listam pelo nome), e
# este guarda acusou a mudança autorizada como se fosse regressão.
#
# A janela correta é o intervalo DA SPEC-073: do baseline ao head dela. Assim a
# afirmação continua sendo conferida — e continua verdadeira — para sempre.
BASELINE_073 = "5cac02f08d93b72b72d94b27e23c31257f2cbfc1"
HEAD_073 = "ffd1cd9a61ad0e1c44fa2aa85e58d8cb0960703a"

try:
    diff = subprocess.run(
        ["git", "diff", "--name-only", BASELINE_073, HEAD_073],
        cwd=str(ROOT.parent), capture_output=True, text=True, timeout=30).stdout
except Exception:  # noqa: BLE001
    diff = ""
if diff:
    for f in INTOCADOS:
        check(f"a SPEC-073 nao alterou `{f}`", f not in diff, f)
    check("a SPEC-073 nao alterou `billing_collection.py`",
          "billing_collection.py" not in diff)
    # 🔴 CONTROLE. Sem isto, um `git diff` que devolvesse lixo não-vazio (ou uma
    # faixa de commits errada) faria as quatro asserções acima passarem por
    # ausência, provando nada. O guarda precisa provar que ENXERGA o diff.
    check("CONTROLE — o diff da 073 realmente contem o que ela mudou",
          "worker.py" in diff and "guardrails.py" in diff, diff[:200])
else:
    print("  [--] git indisponivel: conferencia de arquivos intocados pulada")

# ==========================================================================
print("\n[6] AS FLAGS NASCEM NO ESTADO SEGURO")
# ==========================================================================
import os  # noqa: E402

from portal_worker import perception as P  # noqa: E402
from portal_worker import runtime as RT  # noqa: E402

for var in ("PORTAL_DISCOVERY_MODE", "PORTAL_VISION_ENABLED",
            "PORTAL_DISCOVERY_RAW_TRACE"):
    os.environ.pop(var, None)
check("discovery nasce DESLIGADO", RT.discovery_mode() is False)
check("vision nasce DESLIGADA", P.visao_habilitada() is False)
check("raw trace nasce DESLIGADO", RT.raw_trace_enabled() is False)
check("profiler nasce LIGADO (passivo, e e o que ensina)", RT.profiler_enabled() is True)
check("PORTAL_REAL_ENABLED continua nascendo false",
      (os.environ.pop("PORTAL_REAL_ENABLED", None), W.portal_real_enabled())[1] is False)

print("\n" + "=" * 66)
print(f"  {PASS} asserções verdes · {FAIL} vermelhas")
print("=" * 66)
sys.exit(1 if FAIL else 0)
