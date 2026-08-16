# -*- coding: utf-8 -*-
"""SPEC-073 Bloco B — classe de efeito, guard e o ciclo de vida do checkpoint.

A matriz de mutacoes prova que o guarda REPROVA. Aqui se prova a mecanica: como
uma classe desconhecida e resolvida, como as fases avancam, e o que acontece
quando a journey esquece de armar.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from portal_worker import guardrails as G  # noqa: E402

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
print("\n[1] CLASSE DE EFEITO — o desconhecido cai no mais SEGURO")
# ==========================================================================
check("read_only e reconhecido", G.normalizar_classe("read_only") == G.READ_ONLY)
check("hifen e tolerado", G.normalizar_classe("read-only") == G.READ_ONLY)
check("maiuscula e tolerada", G.normalizar_classe("READ_ONLY") == G.READ_ONLY)
check("reversible_ui e reconhecido", G.normalizar_classe("reversible_ui") == G.REVERSIBLE_UI)
# 🔴 O default e MATERIAL de proposito: classe escrita errado nao pode virar
# permissao. Se alguem digitou `"readonly"` sem underscore, o pior desfecho
# aceitavel e o guard pedir liberacao — nunca deixar passar um clique que cria
# atendimento.
check("classe desconhecida vira MATERIAL (falha fechado)",
      G.normalizar_classe("xpto") == G.MATERIAL_SIDE_EFFECT)
check("None vira MATERIAL", G.normalizar_classe(None) == G.MATERIAL_SIDE_EFFECT)
check("vazio vira MATERIAL", G.normalizar_classe("") == G.MATERIAL_SIDE_EFFECT)

check("divergencia read x material resolve para material",
      G.classe_mais_forte(G.READ_ONLY, G.MATERIAL_SIDE_EFFECT) == G.MATERIAL_SIDE_EFFECT)
check("divergencia material x read tambem (ordem nao importa)",
      G.classe_mais_forte(G.MATERIAL_SIDE_EFFECT, G.READ_ONLY) == G.MATERIAL_SIDE_EFFECT)
check("CONTROLE: read x read continua read",
      G.classe_mais_forte(G.READ_ONLY, G.READ_ONLY) == G.READ_ONLY)

# ==========================================================================
print("\n[2] FINGERPRINT — identidade sem PII")
# ==========================================================================
f1 = G.fingerprint("c1", "vidros", "abrir", "QAB1A91")
f2 = G.fingerprint("c1", "vidros", "abrir", "QAB1A91")
f3 = G.fingerprint("c1", "vidros", "abrir", "XYZ9Z99")
check("mesma entrada -> mesmo fingerprint", f1 == f2)
check("CONTROLE: entrada diferente -> fingerprint diferente", f1 != f3)
check("a placa NAO aparece no fingerprint", "QAB1A91" not in f1)
check("tem tamanho estavel", len(f1) == 16)

# ==========================================================================
print("\n[3] LEITURA DA EVIDENCIA")
# ==========================================================================
check("evidence sem efeito -> fase vazia", G.fase_do_efeito({}) == "")
check("evidence None nao explode", G.fase_do_efeito(None) == "")
check("efeito vazio conta como ausente", G.efeito_critico({"critical_effect": {}}) is None)
check("protocolo e prova de efeito", G.tem_prova_de_efeito({"protocolo": "22842291"}))
check("recibo tambem e prova",
      G.tem_prova_de_efeito({"critical_effect": {"receipt": "R1"}}))
check("fase confirmed e prova",
      G.tem_prova_de_efeito({"critical_effect": {"phase": "confirmed"}}))
check("CONTROLE: protocolo vazio NAO e prova", not G.tem_prova_de_efeito({"protocolo": "  "}))
check("CONTROLE: evidence limpa NAO e prova", not G.tem_prova_de_efeito({}))

# 🔴 Ausencia de informacao nao e prova de ausencia de efeito — mas AUSENCIA DE
# EFEITO ARMADO e. A distincao decide se um job orfao pode recomecar.
check("nunca armou efeito -> pode repetir", G.pode_repetir_com_seguranca({}))
check("fase armed -> NAO pode repetir",
      not G.pode_repetir_com_seguranca({"critical_effect": {"phase": "armed"}}))
check("fase submitted -> NAO pode",
      not G.pode_repetir_com_seguranca({"critical_effect": {"phase": "submitted"}}))
check("fase unknown -> NAO pode",
      not G.pode_repetir_com_seguranca({"critical_effect": {"phase": "unknown"}}))
check("fase confirmed -> NAO pode",
      not G.pode_repetir_com_seguranca({"critical_effect": {"phase": "confirmed"}}))
check("motivo de bloqueio ENSINA o que fazer",
      "reconcil" in G.motivo_de_bloqueio(
          {"critical_effect": {"phase": "unknown"}}).lower())
check("CONTROLE: sem bloqueio, motivo e vazio", G.motivo_de_bloqueio({}) == "")

# ==========================================================================
print("\n[4] O CICLO DE VIDA DO CHECKPOINT")
# ==========================================================================
gravou: list = []


async def _cap(patch):
    gravou.append(dict(patch))


g = G.PortalActionGuard(company_id="c1", portal_key="vidros", journey="abrir",
                        material_liberado=True, acao_material_esperada="confirmar",
                        _checkpoint=_cap)
asyncio.run(g.before(action="create_attendance", action_class=G.MATERIAL_SIDE_EFFECT,
                     details={"idempotency_key": "k1"}))
ef = G.efeito_critico(g.evidence)
check("armar grava name", ef["name"] == "create_attendance")
check("armar grava phase=armed", ef["phase"] == G.FASE_ARMED)
check("armar grava armed_at", bool(ef.get("armed_at")))
check("armar grava resume_policy=reconcile_before_retry",
      ef["resume_policy"] == "reconcile_before_retry")
check("armar grava fingerprint", len(ef["fingerprint"]) == 16)
check("o checkpoint FOI escrito no banco (nao so em memoria)", len(gravou) == 1)

asyncio.run(g.submetido())
check("submetido avanca a fase", G.fase_do_efeito(g.evidence) == G.FASE_SUBMITTED)
check("submetido preserva o name original",
      G.efeito_critico(g.evidence)["name"] == "create_attendance")
asyncio.run(g.confirmado(receipt="22842291"))
check("confirmado avanca a fase", G.fase_do_efeito(g.evidence) == G.FASE_CONFIRMED)
check("confirmado grava o recibo", G.efeito_critico(g.evidence)["receipt"] == "22842291")
check("cada transicao foi para o banco", len(gravou) == 3)

g2 = G.PortalActionGuard(material_liberado=True)
asyncio.run(g2.incerto(motivo="timeout entre clique e resposta"))
check("incerto sem ter armado ainda registra", G.fase_do_efeito(g2.evidence) == G.FASE_UNKNOWN)
check("e marca que armou tarde (journey mal escrita, mas o rastro fica)",
      G.efeito_critico(g2.evidence).get("armed_late") is True)
check("o motivo do incerto e preservado",
      "timeout" in G.efeito_critico(g2.evidence).get("reason", ""))

# ==========================================================================
print("\n[5] O GUARD REGISTRA O QUE RECUSOU")
# ==========================================================================
g3 = G.PortalActionGuard(material_liberado=False)
try:
    asyncio.run(g3.before(action="confirmar", action_class=G.MATERIAL_SIDE_EFFECT))
    negou = False
except G.AcaoBloqueada as e:
    negou = True
    classe = e.classe
check("acao material sem liberacao levanta AcaoBloqueada", negou)
check("a excecao carrega a classe do bloqueio", classe == "material_blocked")
check("o bloqueio vira registro auditavel", len(g3.bloqueios) == 1)
check("o registro diz qual acao e por que",
      g3.bloqueios[0]["action"] == "confirmar" and "liberacao" in g3.bloqueios[0]["motivo"])
check("CONTROLE: acao read-only nao levanta nada",
      asyncio.run(g3.before(action="listar", action_class=G.READ_ONLY)) is None)
check("CONTROLE: e nao vira registro de bloqueio", len(g3.bloqueios) == 1)

print("\n" + "=" * 66)
print(f"  {PASS} asserções verdes · {FAIL} vermelhas")
print("=" * 66)
sys.exit(1 if FAIL else 0)
