# -*- coding: utf-8 -*-
r"""SPEC-126 · U1 — o PROMPT v2: a regra do acostamento (o ELO do C13), o cancelamento e os EXEMPLOS.

📊 U0 (`reports/SPEC-126-LINHA-DE-BASE.md` §3): o Sol aplicou a regra 5 do v2 ("risco à vida ou situação
grave → pessoa") ao ACOSTAMENTO e chamou uma pessoa 2/2 no C13, em vez da regra do guincho.

O que se afirma aqui:
- o TEXTO: acostamento/rodovia = orientar a segurança E acionar; pessoa só para risco à vida AGORA
  (controle: ferido, fumaça, incêndio continuam na regra da pessoa);
- que o texto CHEGA ao modelo pelo `_build_initial_state` REAL (bancada N3, modelo-dublê). ⚠️ O dublê
  obedece ao texto POR CONSTRUÇÃO — prova o elo "regra → prompt do turno", não que o modelo obedece
  (isso é a rodada paga da Luna);
- `EXEMPLOS_V2`: só no v2, fora do teto de 62 % (o guarda do S4 segue medindo a base), ≤ 3.000 chars,
  sem dado real nem regra contraditória; v1 BYTE A BYTE (sha256 `2713eee75b689c7b…`).
"""
from __future__ import annotations

import hashlib
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
for _c in (RAIZ, AQUI):
    if _c not in sys.path:
        sys.path.insert(0, _c)

from app.core import prompts as P  # noqa: E402
from app.services.evals import dubles as D  # noqa: E402

SHA_DO_V1 = "2713eee75b689c7b9b7889caa6e61043eb5aaff4a4db645d79d5e469df734a77"
REGRA_DO_ACOSTAMENTO = "Carro parado no acostamento/rodovia NÃO é grave"
FRASE_DO_CANCELAMENTO = ("Vou chamar agora a pessoa da corretora para cancelar com a seguradora; o guincho só "
                         "para quando ela confirmar.")


def _regra_5(texto: str) -> str:
    return next(l for l in texto.splitlines() if l.startswith("5. **No grave"))


# ===========================================================================
# o TEXTO
# ===========================================================================
def test_v1_byte_a_byte():
    assert len(P.ATTENDANCE_BASE_PROMPT_V1) == 22333
    assert hashlib.sha256(P.ATTENDANCE_BASE_PROMPT_V1.encode("utf-8")).hexdigest() == SHA_DO_V1
    assert REGRA_DO_ACOSTAMENTO not in P.ATTENDANCE_BASE_PROMPT_V1
    assert "EXEMPLOS (a FORMA certa" not in P.build_composite_prompt("x", agent_role="attendance",
                                                                       prompt_versao="v1")


def test_a_regra_5_manda_orientar_e_acionar_no_acostamento():
    r5 = _regra_5(P.ATTENDANCE_BASE_PROMPT_V2)
    assert REGRA_DO_ACOSTAMENTO in r5
    for item in ("pisca-alerta", "triângulo", "atrás da defensa", "acione o guincho com o resumo + o ok"):
        assert item in r5, item
    assert "situação grave" not in r5            # a palavra larga que o Sol leu como "acostamento"


def test_controle_o_risco_a_vida_atual_continua_indo_a_pessoa():
    r5 = _regra_5(P.ATTENDANCE_BASE_PROMPT_V2)
    assert r5.index("acione um atendente humano") < r5.index("risco à vida AGORA")
    for grave in ("ferido", "fumaça", "incêndio", "ameaça", "disjuntor"):
        assert grave in r5[: r5.index(REGRA_DO_ACOSTAMENTO)], grave


def test_o_cancelamento_no_acompanhar_vai_a_pessoa_com_o_motivo():
    linha = next(l for l in P.ATTENDANCE_BASE_PROMPT_V2.splitlines() if l.startswith("- **QUER CANCELAR**"))
    assert FRASE_DO_CANCELAMENTO in linha and "`cancelamento_pos_acionamento`" in linha
    assert "NÃO diga que cancelou" in linha and "`request_human_agent`" in linha


def test_o_teto_do_s4_continua_medindo_a_base_sem_os_exemplos():
    v1, v2 = len(P.ATTENDANCE_BASE_PROMPT_V1), len(P.ATTENDANCE_BASE_PROMPT_V2)
    print(f"\n[TAMANHO] v2 {v2} chars ({100.0 * v2 / v1:.2f}% do v1) · EXEMPLOS_V2 {len(P.EXEMPLOS_V2.strip())} chars")
    assert v2 <= 0.62 * v1
    assert "EXEMPLOS (a FORMA certa" not in P.ATTENDANCE_BASE_PROMPT_V2


def test_exemplos_v2_guarda_propria():
    ex = P.EXEMPLOS_V2.strip()
    assert len(ex) <= 3000, len(ex)
    assert P.EXEMPLOS_V2_VERSAO
    assert ex.count("**") >= 8 and len(re.findall(r"^\*\*\d\.", ex, re.M)) == 4      # 4 conversas
    assert FRASE_DO_CANCELAMENTO in ex and "cancelamento_pos_acionamento" in ex
    assert "posso acionar?" in ex and "pode mandar" in ex
    assert "Quer que eu peça à nossa equipe para cobrar a seguradora agora?" in ex
    assert "primeiro nome do titular" in ex and "NÃO se dizem a ele" in ex
    # ⛔ nenhum dado que pareça real: nem número de 4+ dígitos, nem placa; valores só entre ‹ ›
    assert not re.search(r"\d{4,}", ex) and not re.search(r"\b[A-Z]{3}-?\d[A-Z0-9]\d{2}\b", ex)
    # e nenhuma regra contraditória (o mesmo guarda do S4)
    from test_spec125_s4_prompt_v2 import CONTRADITORIAS

    assert not CONTRADITORIAS.findall(ex)


def test_os_exemplos_entram_so_no_v2_do_atendimento():
    v2 = P.build_composite_prompt("x", agent_role="attendance", prompt_versao="v2")
    assert v2.count("EXEMPLOS (a FORMA certa") == 1
    assert v2.index("### 🛠️ FERRAMENTAS") < v2.index("EXEMPLOS (a FORMA certa") < v2.index("### 🪪 SUA IDENTIDADE")
    assert "EXEMPLOS (a FORMA certa" not in P.build_composite_prompt("x", agent_role="core", prompt_versao="v2")
    # as travas MANTER do S4 continuam todas no v2 montado
    from test_spec125_s4_prompt_v2 import faltando

    assert faltando(v2) == []


# ===========================================================================
# o ELO: a regra chega ao prompt do turno do C13 (motor da bancada N3)
# ===========================================================================
def _roteiro_que_le_o_prompt(msgs, vistos):
    """Dublê que decide PELO TEXTO do prompt do turno: com a regra do acostamento, segue o fio do
    acionamento (linha pronta → "pode mandar" → aciona); sem ela, faz o que o Sol fez na U0 (pessoa)."""
    from test_spec125_endurecimento import _call
    from test_spec126_u1_fio import ARGS, _linha_do_retorno

    sistema = vistos["sistemas"][-1]
    ultima = msgs[-1]
    h = [D._texto_de(m.content) for m in msgs if D._tipo(m) == "human"][-1].lower()
    if D._tipo(ultima) == "tool":
        c = D._texto_de(ultima.content)
        if "ACIONAMENTO REAL INICIADO" in c:
            proto = re.search(r"Protocolo (\S+?)\.", c)
            return f"Guincho acionado ✅ Protocolo {proto.group(1) if proto else '?'}.", []
        if ultima.name == "request_human_agent":
            return "Passei seu caso à nossa equipe por causa do risco no acostamento.", []
        return "Ligue o pisca-alerta e fique atrás da defensa. " + _linha_do_retorno(c), []
    if "km 52" in h:
        if REGRA_DO_ACOSTAMENTO not in sistema:
            return "", _call("request_human_agent", {"reason": "Risco no local — acostamento inseguro"})
        return "", _call("insurer_dispatch", {**ARGS, "dados_confirmados": False})
    if "pode mandar" in h:
        return "", _call("insurer_dispatch", {**ARGS, "dados_confirmados": True})
    return "Achei sua apólice com guincho ✅ Onde o carro está e para onde levo?", []


def test_o_c13_pelo_motor_com_a_regra_aciona_e_nao_chama_pessoa(monkeypatch):
    from test_spec125_endurecimento import _caso, _rodar
    from test_spec126_u1_fio import CEN_FIO

    monkeypatch.setenv("BANCADA_PROMPT_VERSAO", "v2")
    r, vistos = _rodar(_caso(CEN_FIO), _roteiro_que_le_o_prompt)
    assert REGRA_DO_ACOSTAMENTO in vistos["sistemas"][1]          # o prompt REAL do turno do acostamento
    v = {x["evaluator_slug"]: x for x in r.vereditos}
    assert v["pessoa_na_regra"]["passou"] and v["efeitos_exatos"]["passou"], v
    assert r.resultado == "PASS"
