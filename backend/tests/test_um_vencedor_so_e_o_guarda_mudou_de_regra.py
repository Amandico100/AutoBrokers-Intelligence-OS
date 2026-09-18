# -*- coding: utf-8 -*-
r"""🔴 M-B5 · UM VENCEDOR SÓ — e o guarda de `nodes.py` MUDOU DE REGRA, não morreu.

SPEC-EXTRA-001.5 · §6 e §6.4. Duas coisas, e as duas são de motor paralelo
(CLAUDE.md §5):

```
① UMA PORTA      `graph.py` registra UMA tool de apólice. Nenhuma tool nova de
                 cobertura ao lado dela — duas portas para a mesma pergunta é o
                 lugar onde o motor paralelo não aparece no diff da tabela.
② UM VENCEDOR    a BASE responde quando há linha publicada; o FALLBACK quando
                 não há. Nunca os dois, porque `assistance_policy_applied` e
                 `assistencia_da_base` dão ao guard duas regras contraditórias
                 sobre o mesmo texto.
③ O GUARDA VIVO  `nodes.py` continua ANULANDO a resposta que omite serviço da
                 base — e a regra dos 3 serviços continua valendo para o
                 fallback. Nos DOIS canais (copiloto e `client_facing`).
```

🔴 Quem apagar o guarda *"porque a base substituiu a regra"* reabre o defeito
que ele fechou: a LLM reescrevendo por cima do veredito determinístico.
"""
from __future__ import annotations

import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "tests"))

from base_de_planos_em_memoria import BaseEmMemoria  # noqa: E402

from app.agents.nodes import _guard_infocap_policy_final_response as GUARDA  # noqa: E402
from app.agents.tools.infocap_tool import InfocapPolicyLookupTool  # noqa: E402
from app.services.policy_answer_composer import (  # noqa: E402
    compose_policy_answer_with_meta,
)

OK = FAIL = 0


def checar(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA \U0001F534 {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


# ---------------------------------------------------------------------------
print("\n[①] UMA PORTA — o que `graph.py` registra")
# ---------------------------------------------------------------------------
with open(os.path.join(RAIZ, "app", "agents", "graph.py"), "r", encoding="utf-8") as fh:
    GRAPH = fh.read()
registradas = re.findall(r"tools\.append\(\s*(\w+)\(", GRAPH)
apolice = [t for t in registradas if "Policy" in t or "policy" in t]
checar(apolice == ["InfocapPolicyLookupTool"],
       "🔴 UMA tool de apólice registrada, e é a que já existia",
       repr(apolice))
checar("cobertura_e_assistencia" not in GRAPH and "CoberturaTool" not in GRAPH,
       "🔴 e NENHUMA tool de cobertura foi registrada ao lado dela",
       "achou referência a cobertura_e_assistencia em graph.py")
# 🔴 CONTROLE: a varredura CONSEGUE acusar uma segunda porta.
mutado = GRAPH.replace("tools.append(VehicleLookupTool(",
                       "tools.append(CoberturaEAssistenciaTool(", 1)
checar("CoberturaEAssistenciaTool" in re.findall(r"tools\.append\(\s*(\w+)\(", mutado),
       "🔴 CONTROLE: com uma tool nova registrada, a varredura a VÊ — "
       "ela não está verde por cegueira")

# ---------------------------------------------------------------------------
print("\n[②] UM VENCEDOR SÓ — pelo MOTOR (`compose_policy_answer_with_meta`)")
# ---------------------------------------------------------------------------
PACK_RESI = {
    "source": "infocap", "insurer_detected": "allianz",
    "product_detected": "Residencial Total", "line_kind_detected": "residencial",
    "policy_status": "ativa", "active_now": True,
    "valid_from": "2026-01-01", "valid_to": "2027-01-01",
    "coverage_sections": [{"label": "Assistência Residencial 24h", "amount": None}],
    "structured_coverage_available": True, "structured_coverage_absent": False,
    "installments": [], "limitations": [],
    "assistance_plan": {"plano": "Essencial", "nivel": 1, "estado": "contratado"},
}


def _result(pack):
    return {"ok": True, "status": "found",
            "selected": {"insurer_key": pack["insurer_detected"],
                         "product": pack["product_detected"],
                         "policy_number": "1234567890", "numapo": "1234567890",
                         "valid_from": "2026-01-01", "valid_to": "2027-01-01"},
            "policy_evidence_pack": pack}


com_linha = BaseEmMemoria()
PID = com_linha.plano(insurer_key="allianz", ramo="residencial",
                      produto="Residencial Total", plano="Essencial", nivel=1,
                      documento_id="doc-allianz", pagina=6)
com_linha.servico(PID, "eletricista", "sim", documento_id="doc-allianz", pagina=14)

meta_base = compose_policy_answer_with_meta(
    question="ela tem eletricista?", result=_result(PACK_RESI), db=com_linha)
checar(meta_base.get("assistencia_da_base"),
       "🔴 com linha publicada: `assistencia_da_base` PRESENTE",
       repr(meta_base.get("assistencia_da_base")))
checar(meta_base.get("assistance_policy") is None,
       "🔴 e `assistance_policy` é None — o fallback NÃO respondeu junto",
       repr(meta_base.get("assistance_policy")))

meta_fb = compose_policy_answer_with_meta(
    question="ela tem eletricista?", result=_result(PACK_RESI), db=BaseEmMemoria())
checar((meta_fb.get("assistance_policy") or {}).get("applied") is True,
       "🔴 sem linha, apólice residencial com assistência: o FALLBACK responde",
       repr(meta_fb.get("assistance_policy")))
checar(meta_fb.get("assistencia_da_base") is None,
       "🔴 e `assistencia_da_base` é None — a base NÃO respondeu junto",
       repr(meta_fb.get("assistencia_da_base")))
checar((meta_fb.get("cobertura") or {}).get("origem") == "regra_generica",
       "e a origem fica MARCADA como regra genérica (§6.4)",
       repr(meta_fb.get("cobertura")))

print("\n   🔴 CONTROLE: nunca os DOIS ao mesmo tempo, em nenhum dos casos")
for rotulo, meta in (("com linha", meta_base), ("sem linha", meta_fb)):
    dois = bool(meta.get("assistencia_da_base")) and bool(
        (meta.get("assistance_policy") or {}).get("applied"))
    checar(not dois, f"🔴 {rotulo}: um vencedor só", repr(meta.get("assistencia_da_base")))
checar(bool(meta_base.get("assistencia_da_base")) != bool(meta_fb.get("assistencia_da_base")),
       "🔴 CONTROLE: o motor CONSEGUE dar os dois desfechos — mudou só a BASE")

# ---------------------------------------------------------------------------
print("\n[③] O GUARDA DE `nodes.py` — nos DOIS canais")
# ---------------------------------------------------------------------------
for canal, client_facing in (("copiloto", False), ("WhatsApp (client_facing)", True)):
    contrato = InfocapPolicyLookupTool._build_policy_response_contract(
        _result(PACK_RESI), meta_base["text"], meta_base.get("assistance_policy"),
        client_facing=client_facing, meta=meta_base)
    checar("assistencia_da_base" in (contrato.get("required_facts") or []),
           f"🔴 {canal}: o contrato EXIGE `assistencia_da_base` — a regra vale nos dois "
           "canais, porque 'não afirmar o que a base nega' não é formatação",
           repr(contrato.get("required_facts")))
    omite = "Sim, a apólice tem assistência 24h. Qualquer coisa me chama."
    checar(GUARDA(omite, contrato) == meta_base["text"],
           f"🔴 {canal}: resposta que OMITE o serviço da base é ANULADA "
           "(volta o rascunho seguro)", GUARDA(omite, contrato)[:80])
    cita = "Sim — o plano dele tem eletricista, conforme as condições gerais, p. 14."
    checar(GUARDA(cita, contrato) == cita,
           f"🔴 CONTROLE {canal}: a resposta que CITA o serviço PASSA — "
           "o guarda consegue ficar verde", GUARDA(cita, contrato)[:80])

print("\n   o 'não' silencioso: a base diz NAO e o texto não nega")
contrato_nao = InfocapPolicyLookupTool._build_policy_response_contract(
    _result(PACK_RESI), "rascunho seguro", None, client_facing=False,
    meta={"assistencia_da_base": [{"servico": "eletricista", "rotulo": "eletricista",
                                   "coberto": "nao"}],
          "cobertura": {"estado": "nao_coberto"}})
sem_negar = "Sobre eletricista: é só chamar a central que eles enviam."
checar(GUARDA(sem_negar, contrato_nao) == "rascunho seguro",
       "🔴 a base diz `nao` e o texto cita o serviço SEM negar -> ANULADO. "
       "É o 'sim' silencioso de CLAUDE.md §9.5, que não trava e chega ao cliente",
       GUARDA(sem_negar, contrato_nao)[:80])
negando = "Sobre eletricista: o plano dele não inclui, conforme as condições gerais p. 14."
checar(GUARDA(negando, contrato_nao) == negando,
       "🔴 CONTROLE: o mesmo texto NEGANDO passa", GUARDA(negando, contrato_nao)[:80])

print("\n   e a REGRA DOS 3 continua valendo para o fallback")
contrato_fb = InfocapPolicyLookupTool._build_policy_response_contract(
    _result(PACK_RESI), meta_fb["text"], meta_fb.get("assistance_policy"),
    client_facing=False, meta=meta_fb)
checar("assistance_policy_applied" in (contrato_fb.get("required_facts") or []),
       "🔴 o fallback ainda exige `assistance_policy_applied` — o guarda NÃO morreu",
       repr(contrato_fb.get("required_facts")))
checar(GUARDA("Sim, tem assistência.", contrato_fb) == meta_fb["text"],
       "🔴 e ele ANULA a resposta que omite os 3 serviços padrão")

print("\n[④] o bloco do guarda AINDA EXISTE no arquivo")
with open(os.path.join(RAIZ, "app", "agents", "nodes.py"), "r", encoding="utf-8") as fh:
    NODES = fh.read()
checar('if "assistance_policy_applied" in required:' in NODES,
       "🔴 o bloco do fallback continua em `nodes.py` — não foi apagado 'porque a "
       "base substituiu a regra'")
checar('if "assistencia_da_base" in required:' in NODES,
       "e o bloco novo da base está lá, ao lado dele")

print("\n[5] 🔴 O FALLBACK CALA QUANDO A BASE JÁ SABE — um vencedor só, de novo")
# 📊 Medido pela confirmação em 18/09/2026, com a linha PUBLICADA
# `eletricista = nao` (porto/residencial):
#   plano identificado      -> "No plano dele, não..."          (base)      ✅
#   plano NÃO identificado  -> "costuma estar incluído"          (genérica)  ❌
# A mesma seguradora, o mesmo serviço, duas respostas OPOSTAS — e a errada saía
# justamente quando se sabe MENOS sobre o contrato do segurado.
from app.services.skills.cobertura_e_assistencia import (  # noqa: E402
    responder_cobertura,
)
from base_de_planos_em_memoria import BaseEmMemoria as _Base  # noqa: E402

def _base_que_diz_nao():
    d = _Base()
    pid = d.plano(insurer_key="porto", ramo="residencial", produto="Residencial",
                  plano="Essencial", nivel=1)
    d.servico(pid, "eletricista", "nao")
    return d

_residencial = {"insurer": "Porto", "ramo": "residencial", "produto": "Residencial",
                "residencial": True, "assistencia_confirmada": True}

v_sem_plano = responder_cobertura(
    pergunta="a assistencia cobre eletricista?", db=_base_que_diz_nao(),
    apolice=dict(_residencial, estado_do_plano="nao_sabemos_ainda"))
checar(v_sem_plano is not None and v_sem_plano.estado == "nao_sabemos_ainda"
       and v_sem_plano.origem != "regra_generica",
       "🔴 com linha PUBLICADA e plano não identificado -> `nao_sabemos_ainda`, "
       "NUNCA o 'costuma estar incluído'",
       f"{getattr(v_sem_plano, 'estado', None)} / {getattr(v_sem_plano, 'origem', None)}")

# 🔴 CONTROLE ①: sem NENHUMA linha publicada, o fallback continua respondendo.
v_generico = responder_cobertura(
    pergunta="a assistencia cobre eletricista?", db=_Base(),
    apolice=dict(_residencial, estado_do_plano="nao_sabemos_ainda"))
checar(v_generico is not None and v_generico.estado == "coberto"
       and v_generico.origem == "regra_generica",
       "🔴 CONTROLE: base VAZIA para o produto -> a regra genérica responde, marcada",
       f"{getattr(v_generico, 'estado', None)} / {getattr(v_generico, 'origem', None)}")

# 🔴 CONTROLE ②: com o plano identificado, quem responde é a BASE.
v_base = responder_cobertura(
    pergunta="a assistencia cobre eletricista?", db=_base_que_diz_nao(),
    apolice=dict(_residencial, estado_do_plano="contratado", plano="Essencial", nivel=1))
checar(v_base is not None and v_base.estado == "nao_coberto" and v_base.origem == "base",
       "🔴 CONTROLE: plano identificado -> `nao_coberto` pela BASE, com fonte",
       f"{getattr(v_base, 'estado', None)} / {getattr(v_base, 'origem', None)}")
checar(len({getattr(v_sem_plano, "origem", None), getattr(v_generico, "origem", None)}) == 2,
       "🔴 e os dois caminhos CONSEGUEM ser diferentes — o par tem poder de separar")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
