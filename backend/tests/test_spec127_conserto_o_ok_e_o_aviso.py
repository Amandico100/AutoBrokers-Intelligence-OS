# -*- coding: utf-8 -*-
r"""SPEC-127 CONSERTO ÚNICO — itens 1 e 2: o "sim" vale para ESTE pedido, e o aviso não entrega a placa.

```
1 · RT-B1  pergunta sobre OUTRA peça/cidade + "pode mandar" → 0 job · pergunta genérica + "sim" → 0 job
           CONTROLE: a LINHA PRONTA destes params + "pode mandar" → 1 job
2 · B2     o aviso imediato ao WhatsApp: só o FINAL da placa; ao parente, nem o final nem o veículo
```
O fio REAL da tool (`PortalActionTool._arun` → `build_portal_params` → o PORTÃO da SPEC-126 → o worker sobre o
HAR), com o dublê SÓ na borda — o MESMO de `test_spec127_p1_o_fio_do_pedido_de_vidro` (banco, InfoCap, o
classificador do papel `confirmacao` dizendo "ok", o WhatsApp). 📊 As sondas que nasceram vermelhas:
`scratchpad/rt127_probe1.py` (B, C, D) e `scratchpad/jz127_sondas.py` (A). Nenhum valor pessoal do HAR é
impresso. Rodar (de backend/): python -m pytest -q tests/test_spec127_conserto_o_ok_e_o_aviso.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _c in (str(ROOT), str(ROOT / "tests")):
    if _c not in sys.path:
        sys.path.insert(0, _c)

import test_spec127_p1_o_fio_do_pedido_de_vidro as T  # noqa: E402 — o MESMO dublê de borda do P1

from app.services.evals import bancada_confirmacao as BC  # noqa: E402

PP, PT, PLACA = T.PP, T.PT, T.PLACA
CIDADE = T.INFOCAP["client"]["cidade"]
# a "outra cidade" dos casos tem de ser OUTRA de verdade (senão o caso não testa nada — §9.3 corolário)
assert "curitibanos" not in CIDADE.lower() and "retrovisor" != T.FLAT["peca"]


@pytest.fixture(autouse=True)
def _flag(monkeypatch):
    monkeypatch.setenv("PORTAL_VIDROS_API_FIRST", "1")


@pytest.fixture
def mundo(monkeypatch):
    import app.services.tela_cega as TC

    estado = {"notificacoes": [], "parente": False}

    async def _nada(**_k):
        return True

    async def _liberado(self, cpf="", journey="abrir_atendimento"):
        return True

    async def _parente(self, session_id):
        return estado["parente"]

    monkeypatch.setattr(TC, "registrar_tela_cega", _nada)
    monkeypatch.setattr(PT, "POLL_EVERY_S", 0)
    monkeypatch.setattr(PT, "POLL_TIMEOUT_S", 30)
    monkeypatch.setattr(T.Portal, "_envio_liberado", _liberado)
    monkeypatch.setattr(T.Portal, "_apolice_de_outra_pessoa", _parente)
    monkeypatch.setattr(T.Portal, "_notify", lambda self, *a, **k: estado["notificacoes"].append(a))
    return estado


def _conversa(pergunta, resposta):
    banco = T.Banco([("segurado", "quebrou o vidro do meu carro")])
    banco.falar("agente", pergunta)
    banco.falar("segurado", resposta)
    return banco


def _linha(**k):
    return PP.linha_de_confirmacao_do_vidro(T._params_completos(), **k)


# ═════════════════════════════════════════════════════════════════════════════
# 1 · RT-B1 — o ok AMARRADO ao pedido
# ═════════════════════════════════════════════════════════════════════════════
OUTRO_PEDIDO = [
    # (o que a pergunta disse, a resposta) — a chamada vai SEMPRE com os params do HAR (para-brisa, a cidade dele)
    ("Confirma: abrir na seguradora o atendimento de retrovisor com o serviço em Curitibanos/SC, placa final "
     "{fim} — posso acionar?", "pode mandar"),                                  # outra peça E outra cidade
    ("Confirma: abrir na seguradora o atendimento de para-brisa com o serviço em Curitibanos/SC, placa final "
     "{fim} — posso acionar?", "pode mandar"),                                  # a peça certa, OUTRA cidade
    ("Confirma: abrir na seguradora o atendimento de retrovisor com o serviço em {cid}, placa final {fim} — "
     "posso acionar?", "pode mandar"),                                          # a cidade certa, OUTRA peça
    ("Posso acionar a troca do vidro?", "sim"),                                 # genérica: nada do pedido
    ("Confirma o para-brisa? Posso acionar?", "sim"),                           # a peça só
]


@pytest.mark.parametrize("pergunta,resposta", OUTRO_PEDIDO)
def test_o_sim_a_uma_pergunta_que_nao_e_DESTE_pedido_nao_cria_job(mundo, pergunta, resposta):
    cid = f"{CIDADE}/{T.INFOCAP['client']['estado']}"
    banco = _conversa(pergunta.format(fim=PLACA[-4:], cid=cid), resposta)
    with BC.classificador_duble_na_borda() as classificador:
        r = T._chamar(banco)
    assert r.get("status") == "confirm_first", str(r.get("content", ""))[:160]
    assert banco.jobs == [] and banco.posts() == 0
    assert classificador == []                     # barrado na REDE, antes do classificador (nada pago)
    assert r["linha_pronta"] == _linha()           # e a linha certa volta ao agente


def test_CONTROLE_a_linha_pronta_DESTES_params_e_o_sim_criam_UM_job(mundo):
    banco = _conversa(_linha(), "pode mandar")
    with BC.classificador_duble_na_borda() as classificador:
        T._chamar(banco)
    assert [j["journey"] for j in banco.jobs] == ["abrir_atendimento"] and len(classificador) == 1


def test_CONTROLE_o_resumo_com_a_peca_a_cidade_a_UF_e_o_final_da_placa_tambem_vale(mundo):
    """A alternativa mínima: o agente reescreveu a frase, mas disse a peça, a cidade/UF do serviço e o final da
    placa DESTA chamada — é o resumo deste pedido."""
    uf = T.INFOCAP["client"]["estado"]
    banco = _conversa(f"Vou abrir o para-brisa, com o servico em {CIDADE} - {uf}, placa final {PLACA[-4:]}. "
                      "Posso acionar?", "pode mandar")
    with BC.classificador_duble_na_borda():
        T._chamar(banco)
    assert [j["journey"] for j in banco.jobs] == ["abrir_atendimento"]


def test_o_parente_sem_placa_na_linha_continua_confirmando(mundo):
    mundo["parente"] = True
    banco = _conversa(_linha(de_outra_pessoa=True), "pode mandar")
    with BC.classificador_duble_na_borda():
        T._chamar(banco)
    assert [j["journey"] for j in banco.jobs] == ["abrir_atendimento"]


def test_a_regra_so_APERTA_o_guincho_sem_a_chave_nao_muda():
    """O pedido sem `exige_na_pergunta` (o guincho, a bancada do ok) é lido como antes, byte a byte."""
    from app.agents.tools import insurer_dispatch_tool as IDT

    falas = [("agente", "Guincho para a placa final 1D23, da Rua Sete 100 — posso acionar?"),
             ("segurado", "pode mandar")]
    pedido = {"subservice": "guincho", "local_atual": "Rua Sete 100", "veiculo_placa": "ABC1D23"}
    assert IDT.confirmacao_comprovada(falas, pedido)["comprovada"] is True
    assert IDT.confirmacao_comprovada(falas, {**pedido, "exige_na_pergunta": [["retrovisor"]]})[
        "comprovada"] is False
    assert IDT._pergunta_amarrada_ao_pedido("o para-brisa", {"exige_na_pergunta": []}) is False   # fail-closed
    # palavra INTEIRA: "Curitiba" não casa dentro de "Curitibanos"
    assert IDT._pergunta_amarrada_ao_pedido("servico em Curitibanos/SC",
                                            {"exige_na_pergunta": [["curitiba", "sc"]]}) is False


# ═════════════════════════════════════════════════════════════════════════════
# 2 · B2 — o aviso imediato não entrega a placa
# ═════════════════════════════════════════════════════════════════════════════
def _aviso(mundo):
    textos = [str(a[1]) for a in mundo["notificacoes"]]
    assert len(textos) == 1, textos
    return textos[0]


def test_o_parente_nao_recebe_placa_nenhuma_no_aviso(mundo):
    mundo["parente"] = True
    banco = _conversa(_linha(de_outra_pessoa=True), "pode mandar")
    with BC.classificador_duble_na_borda():
        T._chamar(banco)
    aviso = _aviso(mundo)
    assert PLACA not in aviso and PLACA[-4:] not in aviso and "placa" not in aviso.lower()
    assert "VEICULO" not in aviso                  # nem o veículo do titular
    assert "Ja vou acionar a seguradora" in aviso


def test_CONTROLE_o_titular_recebe_so_o_FINAL_da_placa(mundo):
    banco = _conversa(_linha(), "pode mandar")
    with BC.classificador_duble_na_borda():
        T._chamar(banco)
    aviso = _aviso(mundo)
    assert PLACA not in aviso and f"placa final {PLACA[-4:]}" in aviso and "VEICULO" in aviso
