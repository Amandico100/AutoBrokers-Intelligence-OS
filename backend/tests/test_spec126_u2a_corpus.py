# -*- coding: utf-8 -*-
"""SPEC-126 U2 (parte A) — o CORPUS da bancada do "ok" (gabarito escrito ANTES de rodar).

  · ≥ 120 casos, metade "ok" e metade "não-ok/outra coisa" (SPEC-126 U2, G2);
  · TODAS as armadilhas medidas no BLOCO 0 (item 9) + as da SPEC, cada uma em 2–4 variações;
  · a pergunta de DUAS opções: "ok" sozinho = outra_coisa, "agora" = ok;
  · as frases REAIS do BLOCO 0 (mascaradas) estão lá, marcadas `real_mascarada`;
  · toda pergunta é, para o MOTOR do portão, a confirmação do SEU pedido — a bancada mede a
    RESPOSTA, não a forma da pergunta (`confirmacao_comprovada` com "sim" → comprovada);
  · 🔴 nenhuma PII (dígitos em sequência ≥ 4, nome comum) — e o guarda FICA VERMELHO com um caso
    de 11 dígitos e com um nome (§9.3 corolário: um guarda que não tem como falhar não guarda nada).

Rodar (de backend/):  python -m pytest -q tests/test_spec126_u2a_corpus.py
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.evals import bancada_confirmacao as BC  # noqa: E402

CASOS = BC.carregar_casos()

#: As armadilhas MEDIDAS no BLOCO 0 item 9 (o portão de hoje, `scratchpad/portao.py`) + as da SPEC-126
#: U2 ("vou ver", "quem pode acionar?") + as do juiz final da 125 (o "pode" negado/perguntado).
ARMADILHAS_DO_BLOCO_0 = {
    "pode_deixar": "nao", "nao_pode_acionar_o_outro": "nao", "condicional_so_se": "outra_coisa",
    "ok_prefiro_amanha": "nao", "prefiro_amanha": "nao", "ok_a_pergunta_de_duas_opcoes": "outra_coisa",
    "fechou": "ok", "vai_la": "ok", "controle_sim": "ok",
    # "manda · bora · 👍 · isso · pode" — uma linha no laudo, uma armadilha por palavra aqui
    "ok_manda": "ok", "ok_bora": "ok", "ok_emoji": "ok", "ok_isso": "ok", "ok_pode": "ok",
    "vou_ver": "nao", "pergunta_quem_pode": "outra_coisa", "negacao_do_pode": "outra_coisa",
}

#: As respostas REAIS (BLOCO 0 item 5, `b0-126-frases-reais.json`, conferidas uma a uma) que entraram.
FRASES_REAIS = {"Isso mesmo", "Sim isso", "Correto.", "Sim. Confirmado", "Isso. Confirmado",
                "Isso. Tudo certo", "Pode sim", "Pode ser", "Sim, claro", "sim sim", "Sim aham", "Aham",
                "Certo", "Pode sim por favor", "Oiee pode sim por favor", "Pode obrigada", "Tudo certo",
                "Ah, deixar então", "pera ai", "Espera só eu tirar uma dúvida", "Acredito que sim",
                "Obrigado", "Bom dia", "com quem eu falo?", "Preciso de um guincho",
                "Por nome não lembro dessa", "🎤 Áudio", "📷 Imagem", "Prefiro que venha a tarde"}


def test_tem_ao_menos_120_casos_com_ids_unicos():
    assert len(CASOS) >= 120
    assert len({c["id"] for c in CASOS}) == len(CASOS)


def test_metade_ok_metade_nao_ok():
    n_ok = sum(c["gabarito"] == "ok" for c in CASOS)
    assert 0.45 <= n_ok / len(CASOS) <= 0.55, (n_ok, len(CASOS))
    assert {c["gabarito"] for c in CASOS} == {"ok", "nao", "outra_coisa"}


@pytest.mark.parametrize("caso", CASOS, ids=lambda c: c["id"])
def test_forma_de_cada_caso(caso):
    assert set(caso) >= {"id", "pergunta", "falas", "gabarito", "armadilha", "origem", "pedido"}
    assert caso["gabarito"] in BC.GABARITOS
    assert caso["origem"] in ("real_mascarada", "sintetica")
    assert 1 <= len(caso["falas"]) <= 3 and all(str(f).strip() for f in caso["falas"])
    assert str(caso["armadilha"]).strip() and str(caso["pergunta"]).strip()


@pytest.mark.parametrize("armadilha,gabarito", sorted(ARMADILHAS_DO_BLOCO_0.items()))
def test_toda_armadilha_do_bloco_0_esta_la_em_2_a_4_variacoes(armadilha, gabarito):
    casos = [c for c in CASOS if c["armadilha"] == armadilha]
    assert 2 <= len(casos) <= 4, (armadilha, len(casos))
    assert {c["gabarito"] for c in casos} == {gabarito}
    assert len({tuple(c["falas"]) for c in casos}) == len(casos), "variação repetida"


def test_as_variacoes_tem_erro_de_digitacao_sem_acento_caixa_alta_e_emoji():
    falas = [f for c in CASOS for f in c["falas"]]
    assert any(f.isupper() and len(f) > 3 for f in falas)                       # CAIXA ALTA
    assert any(any(ord(ch) > 0x2600 for ch in f) for f in falas)                 # emoji
    assert {"fexou", "podi manda", "vai la", "okk"} <= set(falas)               # digitação / sem acento


def test_pergunta_de_duas_opcoes_ok_sozinho_e_outra_coisa_agora_e_ok():
    duas = [c for c in CASOS if c["tipo_de_pergunta"] == "duas_opcoes"]
    assert any(c["falas"] == ["ok"] and c["gabarito"] == "outra_coisa" for c in duas)
    assert any(c["falas"] == ["agora"] and c["gabarito"] == "ok" for c in duas)
    assert all("agora ou prefere amanhã" in c["pergunta"] for c in duas)


def test_as_frases_reais_do_bloco_0_entraram_marcadas():
    reais = {f for c in CASOS if c["origem"] == "real_mascarada" for f in c["falas"]}
    assert reais == FRASES_REAIS
    assert Counter(c["origem"] for c in CASOS)["real_mascarada"] >= 25


@pytest.mark.parametrize("pergunta,pedido,tipo", sorted({(c["pergunta"], tuple(sorted(c["pedido"].items())),
                                                          c.get("tipo_de_pergunta") or "") for c in CASOS}),
                         ids=lambda x: str(x)[:30])
def test_toda_pergunta_e_a_confirmacao_do_seu_pedido_para_o_motor(pergunta, pedido, tipo):
    """Controle: com o ok INEQUÍVOCO, o MOTOR do portão aceita a pergunta — o que muda o resultado é a
    resposta.

    🔴 SPEC-126 U2 parte B (§9.3 — a lição MIGRA): o "sim" deixou de ser o ok universal. Na pergunta
    de DUAS opções ("agora ou prefere amanhã?") ele não escolhe nada (conf-090..093: o "ok" sozinho é
    outra_coisa) — ali o controle é a ESCOLHA, "agora" (conf-053). E o "sim" lá passa a ser recusado."""
    from app.agents.tools.insurer_dispatch_tool import confirmacao_comprovada

    controle = "agora" if tipo == "duas_opcoes" else "sim"
    r = confirmacao_comprovada([("agente", pergunta), ("segurado", controle)], dict(pedido))
    assert r["comprovada"], r["motivo"]
    if tipo == "duas_opcoes":
        assert not confirmacao_comprovada([("agente", pergunta), ("segurado", "sim")], dict(pedido))["comprovada"]


# ─── o guarda de PII ──────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("caso", CASOS, ids=lambda c: c["id"])
def test_nenhuma_pii_no_corpus(caso):
    assert BC.pii_do_caso(caso) == []


@pytest.mark.parametrize("fala,esperado", [
    ("meu cpf é 12345678909, pode mandar", "digitos:11"),
    ("liga no 11987654321", "digitos:11"),
    ("pode mandar, aqui é o João", "nome:joao"),
    ("a MARIA autorizou", "nome:maria"),
])
def test_o_guarda_fica_vermelho_com_pii(fala, esperado):
    caso = {**CASOS[0], "falas": [fala]}
    assert esperado in BC.pii_do_caso(caso)


def test_controle_do_guarda_um_caso_limpo_passa():
    """O MESMO caso, sem a PII, passa — foi a PII que pintou de vermelho, não o caso."""
    caso = {**CASOS[0], "falas": ["pode mandar, final 1D23, Rua das Flores, 100"]}
    assert BC.pii_do_caso(caso) == []


def test_a_bancada_recusa_rodar_corpus_com_pii(tmp_path, monkeypatch):
    sujo = tmp_path / "casos.jsonl"
    import json

    sujo.write_text(json.dumps({**CASOS[0], "falas": ["cpf 12345678909"]}, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    monkeypatch.setattr(BC, "CORPUS", sujo)
    assert BC.rodar_pela_linha_de_comando(bracos=["duble:sempre_ok"], k=1) == 2
