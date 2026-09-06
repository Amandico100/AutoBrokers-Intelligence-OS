# -*- coding: utf-8 -*-
"""R11 no DESTILADOR — a conversa pessoal não vira carta. SPEC-097.1 (J-6).

🔴 O que o juiz mediu em 06/09/2026: `e_atendimento_de_seguro` existia só em
`pos_acionamento.py` e na régua. `attendance_distiller.py` — o caminho que
grava `knowledge_cards` — **não a importava**. A R11 diz *"antes de virar carta
(`attendance_distiller`) **ou** entrar na régua"*: metade estava entregue, e a
metade que faltava é justamente a que chega ao RAG do agente.

⚠️ **O que se afirma é o comportamento do MOTOR sobre o texto REAL** (§9.4):
estes testes chamam `_destilar_sessao`, a função de produção, com dublês só nas
BORDAS (o transcript, a LLM, a gravação da carta). O portão testado é o do
produto — não uma cópia do regex.

⛔ Sem rede, sem banco, sem LLM.
"""
from __future__ import annotations

import asyncio

import pytest

from app.services import attendance_distiller as AD

#: 💭 O celular da atendente — creche, fim de semana, *"passa pra fulana"*, e
#: nenhuma palavra de seguro. 📊 A forma vem da amostra de 60 do
#: `reality-report-0971.md`; o texto é escrito aqui, sem PII de ninguém.
CONVERSA_PESSOAL = (
    "bom dia meninas tudo bem por ai "
    "eu vou sair mais cedo hoje porque tenho que buscar a crianca na creche "
    "passa pra fulana o que sobrar que ela resolve "
    "no fim de semana a gente combina o churrasco entao kkkk"
)

#: O atendimento de verdade, com o vocabulário do ofício.
CONVERSA_DE_ATENDIMENTO = (
    "o segurado bateu o carro na avenida e precisa de guincho agora "
    "a apolice esta ativa na seguradora e a franquia ja foi conferida "
    "abri o protocolo e o prestador esta a caminho do local do sinistro "
    "depois mando o numero do chamado para a oficina credenciada"
)


def _rodar(texto, monkeypatch):
    """Uma sessão pelo MOTOR real, com dublê só nas bordas.

    Devolve `(stats, cartas_gravadas)`.
    """
    cartas = []

    async def _sem_llm(system, user, company_id="", strong=False):
        # A resposta que o estágio 1 produziria: dois fatos reutilizáveis.
        return ('{"tipo":"assistencia","ramo":"auto","servico":"guincho",'
                '"seguradora":"canaria","resumo_conduta":["pediu a placa"],'
                '"perguntas_na_ordem":["placa"],"score":8,"flags":[],'
                '"fatos_reutilizaveis":["o guincho exige a placa",'
                '"a franquia nao se aplica ao guincho"]}')

    def _texto(_id):
        return texto

    def _grava(fato, meta):
        cartas.append(str(fato))
        return "card-%d" % len(cartas)

    monkeypatch.setattr(AD, "_load_session_text_sync", _texto)
    monkeypatch.setattr(AD, "_call_llm", _sem_llm)
    monkeypatch.setattr(AD, "_store_card_sync", _grava)
    monkeypatch.setattr(AD, "_save_session_summary_sync", lambda *a, **k: None)

    stats = {"sessions": 0, "cards_new": 0, "cards_rejected_pii": 0}
    sess = {"id": "ss-r11", "company_id": "co-teste", "summary": {}}
    asyncio.run(AD._destilar_sessao(sess, stats, {}, asyncio.Lock()))
    return stats, cartas


def test_distiller_descarta_conversa_pessoal_r11(monkeypatch):
    """🔴 Conversa pessoal/colegas → ZERO cartas, e o descarte é CONTADO."""
    stats, cartas = _rodar(CONVERSA_PESSOAL, monkeypatch)
    assert cartas == [], "conversa pessoal virou carta: %r" % (cartas,)
    assert stats.get("descartadas_r11") == 1, stats
    assert stats.get("cards_new", 0) == 0, stats


def test_distiller_mantem_o_atendimento_r11(monkeypatch):
    """🔴 A LINHA DE CONTROLE — sem ela o teste acima passaria com o portão fechado.

    ⚠️ Um portão que barra tudo tem zero cartas do mesmo jeito (§9.2/§9.3).
    """
    stats, cartas = _rodar(CONVERSA_DE_ATENDIMENTO, monkeypatch)
    assert len(cartas) == 2, "o atendimento parou de virar carta: %r" % (cartas,)
    assert stats.get("descartadas_r11", 0) == 0, stats
    assert stats.get("sessions") == 1, stats


def test_distiller_le_a_fonte_unica_do_r11():
    """⛔ O portão é a função do produto, não uma cópia (§5)."""
    from app.atendimento import pos_acionamento as PA

    assert AD.e_atendimento_de_seguro is PA.e_atendimento_de_seguro


@pytest.mark.parametrize("texto,esperado", [
    (CONVERSA_PESSOAL, False),
    (CONVERSA_DE_ATENDIMENTO, True),
])
def test_distiller_o_portao_distingue_os_dois_textos(texto, esperado):
    """📊 O PAR: os dois textos SÃO diferentes para o motor — senão o par de
    testes acima estaria medindo o acaso."""
    assert AD.e_atendimento_de_seguro(texto) is esperado
