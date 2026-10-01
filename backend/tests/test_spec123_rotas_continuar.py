"""SPEC-123 F6 · As telas de "CONTINUAR" depois de a URA encerrar — pelo MOTOR.

A retomada da F3 reabre a conversa com a URA, e a URA responde com uma tela de
"quer continuar?". Cada uma é lida aqui do ACERVO VERSIONADO e passada ao motor
(`match_ura_step` + `render_reply`, CLAUDE.md §9.4): ela tem passo, a resposta
sai, e a constante diz POR QUÊ (`constante_justificada`, §9.5) citando a tela.

📊 30/09 (`scratchpad/f6/cont.py`): todas já tinham passo; faltava o porquê em
`cpf_anterior` (allianz-auto, alfa), `deseja_continuar` (hdi/yelum) e
`reentrada_confirma_veiculo` (bradesco).
"""

from __future__ import annotations

import json
import os
import re

import pytest

import app.services.corridor_playbooks as CP

CORPUS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "corpus", "telas_reais")
SLOTS = {"titular_cpf": "11122233344", "veiculo_placa": "ABC1D23"}

#: (arquivo, regex da tela, passo, resposta, palavra que a justificativa TEM de citar)
CASOS = [
    ("alfa-auto", r"que bom que voltou", "cpf_anterior", "2", "Não, inserir outro"),
    ("allianz-auto", r"que bom que voltou", "cpf_anterior", "2", "Não, inserir outro"),
    ("allianz-residencial", r"em nossa [úu]ltima conversa", "cpf_anterior", "2", "Não, inserir outro"),
    ("yelum-auto", r"^deseja continuar este atendimento", "deseja_continuar", "Sim", "`Sim`"),
    ("hdi-auto", r"^deseja continuar este atendimento", "deseja_continuar", "Sim", "`Sim`"),
    ("hdi-residencial", r"^deseja continuar este atendimento", "deseja_continuar", "Sim", "`Sim`"),
    ("yelum-residencial", r"^deseja continuar este atendimento", "deseja_continuar", "Sim", "`Sim`"),
    ("bradesco-auto", r"vou continuar seu atendimento aqui no whatsapp", "reentrada_confirma_veiculo", None, "`Sim`"),
]


def _telas(nome, rx):
    out = []
    for l in open(os.path.join(CORPUS, nome + ".jsonl"), encoding="utf-8"):
        d = json.loads(l)
        if re.search(rx, d["text"], re.IGNORECASE):
            out.append(d)
    return out


@pytest.mark.parametrize("nome,rx,passo,resposta,cita", CASOS)
def test_a_tela_de_continuar_do_acervo_tem_passo_resposta_e_porque(nome, rx, passo, resposta, cita):
    seg, ramo = nome.split("-", 1)
    pb = CP.get_playbook(CP.resolve_playbook_ref(seg, ramo))
    telas = _telas(nome, rx)
    assert telas, f"{nome}: a tela saiu do acervo"
    for d in telas:
        p = CP.match_ura_step(pb, d["text"], d.get("servico"))
        assert p and p["step"] == passo, (nome, d["session_id"], p and p["step"])
        if resposta is not None:
            assert CP.render_reply(p, SLOTS)["reply"] == resposta
        just = str(p.get("constante_justificada") or "")
        assert cita in just, (nome, passo, just[:60])   # a justificativa NOMEIA o rótulo


def test_CPF_anterior_nunca_responde_Sim_nem_quando_os_digitos_batem():
    """A escolha mais segura, escrita: 5 de 11 dígitos não identificam ninguém."""
    for nome in ("alfa-auto", "allianz-auto", "allianz-residencial"):
        seg, ramo = nome.split("-", 1)
        pb = CP.get_playbook(CP.resolve_playbook_ref(seg, ramo))
        for d in _telas(nome, r"que bom que voltou|em nossa [úu]ltima conversa"):
            p = CP.match_ura_step(pb, d["text"], d.get("servico"))
            assert CP.render_reply(p, {"titular_cpf": "80200000000"})["reply"] == "2"


def test_CONTROLE_a_tela_de_retomada_de_OUTRO_assunto_nao_vira_continuar():
    """'você gostaria de abrir um novo atendimento ou continuar de onde parou?'
    (yelum 01bf91c2) tem o seu passo e a sua resposta — não é `deseja_continuar`."""
    pb = CP.get_playbook(CP.resolve_playbook_ref("yelum", "auto"))
    telas = _telas("yelum-auto", r"continuar de onde parou")
    assert telas
    p = CP.match_ura_step(pb, telas[0]["text"], "guincho")
    assert p and p["step"] == "continuar_de_onde_parou"


@pytest.mark.parametrize("nome", ["allianz-residencial", "allianz-auto", "alfa-auto"])
def test_depois_do_2_a_tela_do_CPF_do_acervo_tem_resposta_do_caso(nome):
    """O caminho do `2 - Não, inserir outro`, pelo MOTOR: 📊 observed_events allianz
    (30/09) — nas 2 vezes em que a resposta foi `2`, a seguinte foi "Digite o *CPF*
    ou *CNPJ* do(a) titular". Essa tela, lida do acervo, sai com o CPF DO CASO."""
    seg, ramo = nome.split("-", 1)
    pb = CP.get_playbook(CP.resolve_playbook_ref(seg, ramo))
    telas = _telas(nome, r"digite o \*?cpf\*? ou \*?cnpj\*? do\(a\) titular")
    assert telas, nome
    p = CP.match_ura_step(pb, telas[0]["text"], telas[0].get("servico"))
    assert p and p["step"] == "pedir_cpf"
    assert CP.render_reply(p, SLOTS)["reply"] == "11122233344"
