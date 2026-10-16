# -*- coding: utf-8 -*-
"""SPEC-129-D · conserto K3 — a COTAÇÃO NOVA de VIDA INDIVIDUAL (91) pelo chat (O FIO §2: "chat/Cotação Rápida → pedido
de vida com os 12 obrigatórios → a mesma porta"), atrás de MULTICALCULO_VIDA_LIGADO.

O que é REAL (CLAUDE.md §9.4 — o teste chama o MOTOR, não o regex): o reconhecimento do texto
(`pedido_da_conversa.ramo_do_texto`), o pedido da conversa (`montar` → `pedido.de_ficha` → `PedidoDeCalculo` 91), as
ferramentas do chat (`cotacao_tool`), a confirmação de uso único e a PORTA (`MulticalculoProvider.calcular`, com a
comissão de vida da config da corretora). Dublê SÓ na borda: o banco (o `BancoU1` do mundo da 132-B), o Redis, e — no
guarda da entrega — a leitura das ofertas (o robô de vida não roda aqui: o canário da V3 o prova ao vivo).

⛔ Dados FICTÍCIOS (CLAUDE.md §13.9): o CPF sintético do teste do motor (DV válido, inventado) e "Fulana Ficticia".
Rodar: cd backend && python -m pytest tests/test_spec129d_cotacao_nova.py -q -p no:cacheprovider
"""
from __future__ import annotations

import logging
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

RAIZ = Path(__file__).resolve().parents[1]
for _p in (str(RAIZ), str(RAIZ / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import test_spec132b_a_conversa as B  # noqa: E402
from test_spec132b_a_conversa import ambiente, mundo  # noqa: E402,F401  (fixtures)

from app.agents.tools import cotacao_tool as T  # noqa: E402
from app.services.cotacao import pedido_da_conversa as PC  # noqa: E402
from app.services.cotacao import workflow as WF  # noqa: E402
from app.services.multicalculo import pedido as P  # noqa: E402
from app.services.multicalculo.porta import MulticalculoProvider  # noqa: E402

CPF, CPF_PONTUADO, NOME = B.CPF, B.CPF_PONTUADO, B.NOME
#: o que o corretor disse ("cotação de vida para a Fulana, 46 anos, não fuma, renda 8 mil, capital 200 mil, analista de
#: sistemas, não pratica esporte radical…") — os campos que o modelo leu da conversa, como ele os escreve
VIDA_COMPLETA = {"ramo": "vida", "cpf_cnpj": CPF_PONTUADO, "nome": NOME, "nascimento": "01/02/1980",
                 "sexo": "feminino", "estado_civil": "casada", "cep": "01001-000",
                 "profissao": "analista de sistemas", "capital": "200 mil", "fumante": "não",
                 "renda_mensal": "8 mil", "esporte_radical": "não"}
#: os valores que NUNCA vão a log (D-129D-05 · CLAUDE.md §7): a renda e as respostas de saúde/risco
_RENDA = re.compile(r"\b8\.?000\b|\b8 mil\b")
_RESPOSTA_DE_RISCO = re.compile(r"(fumante|fuma|esporte)\W{0,3}(sim|n[aã]o|true|false)", re.I)


@pytest.fixture
def vida(monkeypatch):
    monkeypatch.setenv(P.ENV_VIDA, "1")


class Espiao:
    """A porta REAL, com um olho no que ela recebeu e no pedido de vida que ela MONTOU (depois da comissão)."""

    def __init__(self, monkeypatch):
        self.calcular, self.vida = [], []
        real_calc, real_vida = MulticalculoProvider.calcular, MulticalculoProvider._calcular_vida
        esp = self

        async def calcular(self_, **kw):
            esp.calcular.append(kw)
            return await real_calc(self_, **kw)

        async def _calcular_vida(self_, **kw):
            esp.vida.append(kw["pedido"])
            return await real_vida(self_, **kw)

        monkeypatch.setattr(MulticalculoProvider, "calcular", calcular)
        monkeypatch.setattr(MulticalculoProvider, "_calcular_vida", _calcular_vida)


def _cenario(m):
    a = m.corretora()
    uid, _ = m.pessoa(a)
    conversa, sess = m.conversa(a, uid)
    return a, uid, conversa, sess


def _cota(m, a, uid, sess, **campos):
    r1 = m.preparar(a, uid, sess, **campos)
    assert "Confira antes de eu calcular" in r1, r1
    return r1, m.disparar(a, uid, sess, B._id_da_confirmacao(r1))


def _hoje_no_brasil() -> date:
    return datetime.now(timezone(timedelta(hours=-3))).date()


# =====================================================================================================================
# (1) CONTROLE — a chave AUSENTE: a vida segue fora, como hoje (byte a byte)
# =====================================================================================================================
def test_1_chave_ausente_a_vida_segue_fora_como_hoje(mundo, monkeypatch):
    monkeypatch.delenv(P.ENV_VIDA, raising=False)
    m = mundo
    a, uid, _c, sess = _cenario(m)
    for texto in ("vida", "seguro de vida", "vida individual", "91"):
        with pytest.raises(PC.ForaDoEscopo) as e:
            PC.ramo_do_texto(texto)
        assert e.value.chave == "outro"
    assert m.preparar(a, uid, sess, **VIDA_COMPLETA) == PC.FRASE_FORA["outro"]
    assert not m.pedidos() and not m.redis.d
    # o esquema que o modelo vê é o de hoje: nenhum campo de vida sem a chave
    prep = m.ferramentas(a)["cotacao_preparar"]
    assert "fumante" not in prep.args_schema.model_fields and "vida" not in prep.description.lower()


# =====================================================================================================================
# (2) o texto COMPLETO → o pedido 91 com os campos do contrato → a MESMA porta
# =====================================================================================================================
def test_2_texto_completo_vira_pedido_91_e_vai_a_mesma_porta(mundo, monkeypatch, vida):
    m = mundo
    esp = Espiao(monkeypatch)
    a, uid, conversa, sess = _cenario(m)
    assert PC.ramo_do_texto("vida") == P.RAMO_VIDA == PC.RAMO_VIDA == T.PC_RAMO_VIDA == WF.RAMO_VIDA == 91
    assert PC.ramo_do_texto("seguro de vida individual") == 91
    r1, r2 = _cota(m, a, uid, sess, **VIDA_COMPLETA)
    assert "Vida individual" in r1 and "***.***.***-25" in r1 and CPF not in r1, r1
    assert "R$ 200.000" in r1, "o capital que o corretor disse não está no resumo que ele confere"
    assert "Calculando" in r2, r2
    [kw] = esp.calcular
    assert kw["servico"] == "cotacao" and kw["solicitante_user_id"] == uid
    p = kw["pedido"]
    assert p.ramo == 91 and p.valor("vida", "origem") == "cotacao"
    assert p.campos["segurado"] == {"cpf": CPF, "nome": NOME, "data_nascimento": "1980-02-01", "sexo": "Feminino",
                                    "estado_civil": "Casado(a)", "cep": "01001000",
                                    "profissao_texto": "analista de sistemas"}
    v = p.campos["vida"]
    assert (v["capital_morte"], v["renda_mensal"], v["fumante"], v["esporte_radical"]) == (200000.0, 8000.0, False,
                                                                                         False)
    # a vigência de uma cotação nova começa HOJE — declarada (assumida), nunca escondida como dita
    assert v["vigencia_inicio"] == _hoje_no_brasil().isoformat() and "vida.vigencia_inicio" in p.assumidos
    assert not p.faltando() and not p.sem_codigo()
    [ped] = m.pedidos(a)
    assert (ped["ramo"], ped["servico"], ped["origem"]) == (91, "cotacao", "auxiliar")
    assert {c["opcao"] for c in m.calculos(ped["id"])} == {"padrao", "economica"}
    [run] = [r for r in m.banco.linhas("work_runs") if r["workflow_key"] == "cotacao.chat"]
    assert run["input_payload"]["ramo"] == 91 and run["conversation_id"] == conversa


# =====================================================================================================================
# (3) faltou fumante e renda → as PERGUNTAS, uma vez; a porta NÃO é chamada (D-129D-05)
# =====================================================================================================================
def test_3_sem_fumante_e_renda_volta_pergunta_e_nao_calcula(mundo, monkeypatch, vida):
    m = mundo
    esp = Espiao(monkeypatch)
    a, uid, _c, sess = _cenario(m)
    sem = {k: v for k, v in VIDA_COMPLETA.items() if k not in ("fumante", "renda_mensal")}
    r = m.preparar(a, uid, sess, **sem)
    assert r.startswith("PARA O CORRETOR — "), r
    assert "O segurado é fumante?" in r and "Qual a renda mensal do segurado?" in r, r
    assert r.count("fumante?") == 1, "a pergunta veio duas vezes"
    assert "esporte radical" not in r and "capital" not in r.lower(), "perguntou o que o corretor já disse"
    assert not re.search(r"\b(segurado|vida)\.\w+", r), "jargão de campo na frase"
    assert not esp.calcular and not m.pedidos() and not m.redis.d
    # o capital e o "não sei" também nunca viram padrão: sem capital → pergunta; "não sei se fuma" → pergunta
    r = m.preparar(a, uid, sess, **{**VIDA_COMPLETA, "capital": None, "fumante": "não sei"})
    assert "capital" in r.lower() and "O segurado é fumante?" in r and "Confira" not in r, r
    assert not esp.calcular
    # CONTROLE: o mesmo pedido com as respostas calcula (o guarda consegue ficar verde)
    _cota(m, a, uid, sess, **VIDA_COMPLETA)
    assert len(esp.calcular) == 1


def test_3b_so_o_fumante_ausente_nunca_vira_nao(mundo, monkeypatch, vida):
    """O guarda da MUTAÇÃO: fumante ausente vira "não" → o pedido iria completo à porta. Tem de ficar VERMELHO."""
    m = mundo
    esp = Espiao(monkeypatch)
    a, uid, _c, sess = _cenario(m)
    r = m.preparar(a, uid, sess, **{k: v for k, v in VIDA_COMPLETA.items() if k != "fumante"})
    assert "O segurado é fumante?" in r and "Confira" not in r, r
    assert not esp.calcular
    montagem = PC.montar({k: v for k, v in VIDA_COMPLETA.items() if k != "esporte_radical"})
    assert montagem.faltam == ["vida.esporte_radical"] and montagem.pedido.valor("vida", "esporte_radical") is None


# =====================================================================================================================
# (4) vida em grupo, acidentes pessoais, Mobi → continuam FORA, com a frase de hoje
# =====================================================================================================================
def test_4_vida_em_grupo_ap_e_mobi_continuam_fora(mundo, monkeypatch, vida):
    m = mundo
    esp = Espiao(monkeypatch)
    a, uid, _c, sess = _cenario(m)
    for texto in ("vida em grupo", "seguro de vida coletivo", "acidentes pessoais", "AP", "mobi", "mobilidade",
                  "vida empresarial", "vida para os funcionários"):
        with pytest.raises(PC.ForaDoEscopo) as e:
            PC.ramo_do_texto(texto)
        assert e.value.chave == "outro", texto
        assert m.preparar(a, uid, sess, **{**VIDA_COMPLETA, "ramo": texto}) == PC.FRASE_FORA["outro"], texto
    assert not esp.calcular and not m.pedidos()
    # CONTROLE: os outros ramos não mudaram com a chave ligada
    assert (PC.ramo_do_texto("carro"), PC.ramo_do_texto("residencial"), PC.ramo_do_texto("empresarial")) == (31, 2, 18)


# =====================================================================================================================
# (5) duas corretoras — a comissão de vida de A não vaza para B (CLAUDE.md §7)
# =====================================================================================================================
def test_5_duas_corretoras_a_comissao_de_a_nao_vaza_para_b(mundo, monkeypatch, vida):
    m = mundo
    esp = Espiao(monkeypatch)
    a, ua, _ca, sa = _cenario(m)
    b, ub, _cb, sb = _cenario(m)
    m.banco.semear("multicalculo_config", {"company_id": a, "config": {
        "vida_por_ramo": {"91": {"comissao_pct": 20, "agenciamento_pct": 30}}}})
    _cota(m, a, ua, sa, **VIDA_COMPLETA)
    _cota(m, b, ub, sb, **VIDA_COMPLETA)
    pa, pb = esp.vida
    assert pa.campos["comissao_desconto"] == {"comissao_percentual": 20.0, "agenciamento_percentual": 30.0}
    assert "comissao_desconto" not in pb.campos, "a comissão de A foi parar no pedido de B (ou foi inventada)"
    assert {p["company_id"] for p in m.pedidos()} == {a, b}


# =====================================================================================================================
# (6) nada de fumante/renda em LOG — nem no run em claro (o resumo ao próprio corretor é o único lugar)
# =====================================================================================================================
def test_6_fumante_e_renda_nunca_vao_ao_log_nem_ao_run(mundo, monkeypatch, vida, caplog):
    m = mundo
    a, uid, conversa, sess = _cenario(m)
    caplog.set_level(logging.DEBUG)
    sem = {k: v for k, v in VIDA_COMPLETA.items() if k != "esporte_radical"}
    m.preparar(a, uid, sess, **{**sem, "fumante": "sim"})
    r1, _r2 = _cota(m, a, uid, sess, **{**VIDA_COMPLETA, "fumante": "sim"})
    assert "Fumante: sim" in r1 and "R$ 8.000" in r1, "o resumo AO CORRETOR tem de mostrar o que ele confere"
    for rec in caplog.records:
        texto = rec.getMessage()
        assert not _RENDA.search(texto) and not _RESPOSTA_DE_RISCO.search(texto), f"vazou no log: {texto[:160]}"
    [run] = [r for r in m.banco.linhas("work_runs") if r["workflow_key"] == "cotacao.chat"]
    claro = str(run["input_payload"])
    assert not _RENDA.search(claro) and "fumante" not in claro.lower() and CPF not in claro, claro


# =====================================================================================================================
# (7) a ENTREGA — as ofertas voltam na conversa, SEM a página do cliente (a página de vida é da 130-C, D-129D-10)
# =====================================================================================================================
def test_7_a_entrega_de_vida_responde_no_chat_sem_publicar_pagina(mundo, monkeypatch, vida):
    m = mundo
    a, uid, conversa, sess = _cenario(m)
    _cota(m, a, uid, sess, **VIDA_COMPLETA)
    [ped] = m.pedidos(a)

    class PortaDasOfertas:          # a borda: o que o robô de vida trouxe (o canário V3 prova o real)
        async def consultar(self, *, company_id, pedido_id):
            return SimpleNamespace(estados=[{"status": "fechado"}],
                                   ofertas=[{"seguradora": "Seguradora Alfa", "premio_total": 900.0},
                                            {"seguradora": "Seguradora Beta", "premio_total": 1100.0}])

    lidos = []

    async def opcoes_de_vida(db, company_id, pedido_id):
        lidos.append((company_id, pedido_id))
        return [{"id": "recomendada", "papel": "Recomendada", "seguradora": "Seguradora Alfa",
                 "parcela": {"vezes": 12, "valor": 75.0, "sem_juros": True}, "a_vista": 900.0, "franquia": None}]

    monkeypatch.setattr(WF, "_porta", lambda db: PortaDasOfertas())
    monkeypatch.setattr(WF, "_opcoes_de_vida_sem_pagina", opcoes_de_vida)
    m.rodar_runs(a)
    [msg] = m.mensagens_do_assistente(conversa)
    texto = msg["content"]
    assert texto.startswith("Pronto: 2 seguradoras responderam."), texto
    assert "| Recomendada | Seguradora Alfa |" in texto
    assert "Apresentação para o cliente" not in texto and "Mensagem para o cliente" not in texto
    assert "página de vida" in texto.lower(), "o corretor não foi avisado de que a apresentação de vida não existe"
    assert not m.publicacoes, "publicou uma página de cliente para vida (D-129D-10: é da 130-C)"
    assert lidos == [(a, ped["id"])]
    assert not _RENDA.search(texto) and not _RESPOSTA_DE_RISCO.search(texto)


# =====================================================================================================================
# o recálculo de vida não existe nesta versão → frase de gente, nunca "o problema é do nosso lado"
# =====================================================================================================================
def test_8_o_ajuste_de_vida_recusa_com_frase(mundo, monkeypatch, vida):
    m = mundo
    a, uid, _c, sess = _cenario(m)
    _r1, r2 = _cota(m, a, uid, sess, **VIDA_COMPLETA)
    [ped] = m.pedidos(a)
    for c in m.calculos(ped["id"]):
        c.update({"negocio_ref": "neg-1", "versao": 1})    # o disparo já abriu o negócio no Agger (a borda)
    r = m.ajustar(a, uid, sess, ped["id"], "comissao", "15")
    assert "vida" in r and "nosso lado" not in r, r
