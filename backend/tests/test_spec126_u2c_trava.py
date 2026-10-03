# -*- coding: utf-8 -*-
"""SPEC-126 · U2-C — A TRAVA DO MODELO PAGO (`tests/conftest.py::trava_do_modelo_pago`).

```
teste → classificar_confirmacao(…) SEM llm= → confirmacao._chamar_o_papel
      → llm_factory.invocar_com_reserva("confirmacao")  ← a TRAVA: resolve (grátis) e FALHA ALTO
```

📊 O defeito que ela fecha (U2-B): a bancada de conversa chamava o portão sem `llm=` e o classificador
ia ao papel de PRODUÇÃO — chamada paga, com a chave local (= produção), fora do ledger da bancada.

O que se afirma (CLAUDE.md §9.3 — o guarda CONSEGUE ficar vermelho):
· o papel `confirmacao` pela fábrica, sem dublê → `pytest.fail("teste chamou modelo pago: …")`, e a
  fábrica de mentira (o "provedor") NUNCA é tocada;
· CONTROLE: a MESMA chamada com o dublê na borda (`classificador_duble_na_borda`) passa — e a fábrica
  de mentira também não é tocada;
· outro papel (`dispatch`) segue pela fábrica (a trava é só do papel travado);
· sem rota, o erro de sempre sobe (a trava não mascara o `ModeloNaoResolvido` da U2a);
· o produto que ENGOLE a falha não esconde a violação (fica anotada para o fim do teste).

⛔ Sem rede, sem LLM: o "provedor" é uma fábrica de mentira (`LLMFactory.create_llm` trocado).
"""
from __future__ import annotations

import asyncio
import os
import sys

import pytest

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
for _c in (RAIZ, AQUI):
    if _c not in sys.path:
        sys.path.insert(0, _c)

from langchain_core.messages import AIMessage, HumanMessage  # noqa: E402

from app.atendimento import confirmacao as C  # noqa: E402
from app.factories import llm_factory as LF  # noqa: E402
from app.factories import model_policy as MP  # noqa: E402
from app.services.evals import bancada_confirmacao as BC  # noqa: E402

PERGUNTA = "Confirma: guincho saindo de Rua das Flores 12 até Oficina Central — posso acionar?"


class _Resolvido:
    provider = "openai"
    model = "gpt-6-luna"
    reserva = None


class _ProvedorDeMentira:
    """O que `create_llm` devolveria: um cliente que, na vida real, COBRA. Aqui só anota."""

    def __init__(self, pagas: list):
        self.pagas = pagas

    async def ainvoke(self, msgs, config=None, **_k):
        self.pagas.append(len(msgs))
        return AIMessage(content='{"leitura": "ok", "trecho": "pode mandar"}')


def _fabrica_de_mentira(monkeypatch, pagas: list) -> None:
    """A rota RESOLVE (como em produção depois da migration) e o cliente é de mentira."""
    monkeypatch.setattr(LF.LLMFactory, "resolver_para", staticmethod(lambda *_a, **_k: _Resolvido()))
    monkeypatch.setattr(LF.LLMFactory, "create_llm", staticmethod(lambda *_a, **_k: _ProvedorDeMentira(pagas)))


def test_o_papel_confirmacao_sem_duble_falha_alto(monkeypatch, trava_do_modelo_pago):
    """🔴 A trava: o classificador sem `llm=` e sem dublê → o teste FALHA com a mensagem — e o
    "provedor" nunca é chamado."""
    pagas: list = []
    _fabrica_de_mentira(monkeypatch, pagas)
    with pytest.raises(pytest.fail.Exception, match="teste chamou modelo pago: papel 'confirmacao'"):
        asyncio.run(C.classificar_confirmacao(PERGUNTA, ["pode mandar"], company_id="empresa-a"))
    assert pagas == [], "a trava deixou a chamada chegar ao provedor"
    assert trava_do_modelo_pago.violacoes and "confirmacao" in trava_do_modelo_pago.violacoes[0]
    trava_do_modelo_pago.violacoes.clear()   # a falha FOI a prova; o fim do teste não a repete


def test_controle_com_o_duble_na_borda_a_mesma_chamada_passa(monkeypatch, trava_do_modelo_pago):
    """CONTROLE (§9.2): a MESMA chamada, com o dublê explícito da U2-B, lê ok e não toca nada pago."""
    pagas: list = []
    _fabrica_de_mentira(monkeypatch, pagas)
    with BC.classificador_duble_na_borda() as chamadas:
        r = asyncio.run(C.classificar_confirmacao(PERGUNTA, ["pode mandar"], company_id="empresa-a"))
    assert (r["leitura"], r["motivo"]) == ("ok", "modelo"), r
    assert len(chamadas) == 1 and pagas == [] and trava_do_modelo_pago.violacoes == []


def test_com_llm_injetado_nunca_chega_a_fabrica(monkeypatch, trava_do_modelo_pago):
    """O caminho da bancada (`llm=`): a fábrica nem é consultada."""
    pagas: list = []
    _fabrica_de_mentira(monkeypatch, pagas)
    r = asyncio.run(C.classificar_confirmacao(PERGUNTA, ["pode mandar"], company_id="empresa-a",
                                              llm=BC.DUBLES["sempre_ok"]()))
    assert r["leitura"] == "ok" and pagas == [] and trava_do_modelo_pago.violacoes == []


def test_outro_papel_segue_pela_fabrica(monkeypatch, trava_do_modelo_pago):
    """A trava é do papel `confirmacao`: o `dispatch` (com a fábrica de mentira) segue — prova de que
    ela não é um bloqueio cego que quebraria os testes da reserva."""
    pagas: list = []
    _fabrica_de_mentira(monkeypatch, pagas)
    resp = asyncio.run(LF.invocar_com_reserva("dispatch", [HumanMessage(content="Digite 1 ou 2")],
                                              company_id="empresa-a"))
    assert "leitura" in str(resp.content) and pagas == [1]
    assert trava_do_modelo_pago.violacoes == []


def test_sem_rota_o_erro_de_sempre_sobe(monkeypatch, trava_do_modelo_pago):
    """A RESOLUÇÃO acontece como no original: sem rota, `ModeloNaoResolvido` → `outra_coisa` (U2a) — nada
    pago, nenhuma violação."""
    def sem_rota(*_a, **_k):
        raise MP.ModeloNaoResolvido("papel 'confirmacao' sem rota (teste)")

    pagas: list = []
    _fabrica_de_mentira(monkeypatch, pagas)
    monkeypatch.setattr(LF.LLMFactory, "resolver_para", staticmethod(sem_rota))
    r = asyncio.run(C.classificar_confirmacao(PERGUNTA, ["pode mandar"], company_id="empresa-a"))
    assert (r["leitura"], r["motivo"]) == ("outra_coisa", "erro:ModeloNaoResolvido")
    assert pagas == [] and trava_do_modelo_pago.violacoes == []


def test_quem_engole_a_falha_nao_esconde_a_violacao(monkeypatch, trava_do_modelo_pago):
    """Um chamador que engole TUDO (até `BaseException`) não apaga a violação: ela fica anotada e o
    fim do teste falharia por ela."""
    pagas: list = []
    _fabrica_de_mentira(monkeypatch, pagas)

    async def engole():
        try:
            await LF.invocar_com_reserva("confirmacao", [HumanMessage(content="x")], company_id="empresa-a")
        except BaseException:  # noqa: BLE001 — de propósito: o pior chamador possível
            return "engolido"

    assert asyncio.run(engole()) == "engolido"
    assert pagas == [] and len(trava_do_modelo_pago.violacoes) == 1
    trava_do_modelo_pago.violacoes.clear()
