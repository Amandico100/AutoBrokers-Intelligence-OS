# -*- coding: utf-8 -*-
"""SPEC-133-A F2 — A COTAÇÃO do canal (U5 · U6): a regra da placa na porta, o disparo, o Work Run, a passagem.

Usa o MESMO mundo do teste do fio (`test_spec133a_a_conversa.py`: banco da 129-B/130-A, dublês da F1, relógio).
⛔ Dados fictícios (CLAUDE.md §13.9).
Rodar: cd backend && .venv/Scripts/python.exe -m pytest tests/test_spec133a_a_cotacao.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

import pytest

from test_spec133a_a_conversa import (  # noqa: F401 — fixtures e ajudantes do fio (um mundo só)
    CHAVE_HMAC, FALAS_DO_PERFIL, TEL, TEL_2, acordar, canal, falar, motor_grava_o_quadro, mundo, rodar, rodar_o_run,
)
from dubles import mundo_da_proposta as M


# =====================================================================================================================
# U5 — D-133A-03: no canal a PLACA supre FIPE, ano e combustível; a carteira continua exigindo os três
# =====================================================================================================================
def _so_placa(**extra):
    from app.services.multicalculo.pedido import PedidoDeCalculo

    d = {"segurado": {"cpf_cnpj": "52998224725", "nome": "Pessoa Sintetica", "nascimento": "1980-02-01", "sexo": "M",
                      "estado_civil": 2, "cep": "01001000"},
         "veiculo": {"placa": "ABC1D23"}, "pernoite": {"cep_pernoite": "01001000", "garagem_residencia": "2"},
         "condutor": {"cpf": "52998224725", "nome": "Pessoa Sintetica", "nascimento": "1980-02-01", "sexo": "M",
                      "estado_civil": 2, "tempo_habilitacao": 20, "jovem_condutor": False},
         "questionario": {"km_mensal": 800}}
    for g, v in extra.items():
        d[g] = {**d.get(g, {}), **v}
    return PedidoDeCalculo.de_dict(d, assumidos=["veiculo.uso"])


def test_a_placa_supre_os_tres_so_no_canal():
    p = _so_placa()
    assert p.faltando(origem="canal") == []
    assert set(p.faltando()) == {"veiculo.fipe", "veiculo.ano_fabricacao", "veiculo.combustivel"}
    assert set(p.faltando(origem="auxiliar")) == {"veiculo.fipe", "veiculo.ano_fabricacao", "veiculo.combustivel"}
    a = p.assumindo_pela_placa()
    assert {"veiculo.fipe", "veiculo.ano_fabricacao", "veiculo.combustivel"} <= set(a.assumidos)
    assert a.valor("veiculo", "fipe") is None                     # assumido, nunca inventado
    # sem placa a regra não vale
    sem = _so_placa(veiculo={"placa": None})
    assert "veiculo.fipe" in sem.faltando(origem="canal")
    # o que a pessoa disse vence: com FIPE dita, não é "suprida"
    com = _so_placa(veiculo={"fipe": "0012345", "ano_fabricacao": 2020, "combustivel": "flex"})
    assert com.supridos_pela_placa("canal") == frozenset()


def _porta_do_mundo(m):
    from app.services.multicalculo.porta import MulticalculoProvider
    from app.services.multicalculo.repositorio import RepositorioMulticalculo

    return MulticalculoProvider(RepositorioMulticalculo(m.db), cifrar=lambda t: "cifrado",
                                ambiente={"MULTICALCULO_HMAC_KEY": CHAVE_HMAC})


def test_a_porta_aceita_o_canal_so_com_a_placa_e_a_carteira_nao(mundo):
    from app.services.multicalculo.porta import OPCOES_DO_CANAL, PedidoIncompleto

    m = mundo
    porta = _porta_do_mundo(m)
    aberto = rodar(porta.calcular(company_id=m.canal, pedido=_so_placa(), corretoras=[m.alfa, m.beta],
                                  opcoes=OPCOES_DO_CANAL, origem="canal"))
    assert aberto.pedido_id and len(aberto.calculos) == 6
    # a carteira (a corretora pedindo para si, origem auxiliar) continua recusada sem FIPE/ano/combustível
    with pytest.raises(PedidoIncompleto) as e:
        rodar(porta.calcular(company_id=m.alfa, pedido=_so_placa(), corretoras=[m.alfa], origem="auxiliar"))
    assert set(e.value.campos) == {"veiculo.fipe", "veiculo.ano_fabricacao", "veiculo.combustivel"}


# =====================================================================================================================
# o disparo: adesões ATIVAS do canal (dois canais, adesão inativa), falha honesta
# =====================================================================================================================
def test_as_adesoes_sao_so_as_ativas_deste_canal(mundo, canal):
    m, c = mundo, canal
    outro_canal = str(uuid.uuid4())
    m.banco.semear("companies", {"id": outro_canal, "company_kind": "platform_canal", "company_name": "Outro Canal"})
    m.banco.semear("multicalculo_adesoes", {"canal_company_id": outro_canal, "corretora_company_id": m.intruso,
                                            "ativa": True})
    m.banco.semear("multicalculo_adesoes", {"canal_company_id": m.canal, "corretora_company_id": m.intruso,
                                            "ativa": False})
    assert c.cotacao.adesoes_ativas_do_canal(m.db, m.canal) == [m.alfa, m.beta]
    assert c.cotacao.adesoes_ativas_do_canal(m.db, outro_canal) == [m.intruso]


def test_sem_adesao_ativa_a_pessoa_e_avisada_e_nada_e_enfileirado(mundo, canal):
    m, c = mundo, canal
    for a in m.banco.linhas("multicalculo_adesoes"):
        a["ativa"] = False
    r = falar(c, m.db, m.canal, ["oi", "sim"] + FALAS_DO_PERFIL)
    run_id = rodar(c.cotacao.disparar(m.db, m.canal, TEL, r.disparar, r.estado))
    assert run_id == ""
    assert not [p for p in m.banco.linhas("multicalculo_pedidos") if p["origem"] == "canal"]
    assert not m.banco.linhas("work_runs")
    estado = c.repo.carregar_estado(m.db, m.canal, TEL)
    assert estado["etapa"] == "falhou" and "respostas" not in estado
    assert "não consegui começar" in c.envio.textos()[-1].lower()


def test_a_porta_recusando_nao_vira_mensagem_mentirosa(mundo, canal, monkeypatch):
    """Sem a chave do HMAC a porta recusa (fail-closed): a pessoa ouve que o problema é nosso; nada no Agger."""
    m, c = mundo, canal
    monkeypatch.delenv("MULTICALCULO_HMAC_KEY", raising=False)
    r = falar(c, m.db, m.canal, ["oi", "sim"] + FALAS_DO_PERFIL)
    assert rodar(c.cotacao.disparar(m.db, m.canal, TEL, r.disparar, r.estado)) == ""
    assert not m.banco.linhas("multicalculo_calculos") or all(
        x["pedido_id"] == m.pedido_id for x in m.banco.linhas("multicalculo_calculos"))
    assert "não consegui começar" in c.envio.textos()[-1].lower()


# =====================================================================================================================
# o Work Run: a config pede 5 lembretes → saem 2 · horário comercial · sem WhatsApp da corretora (T-125)
# =====================================================================================================================
def _ate_o_resultado(m, c, telefone=TEL):
    r = falar(c, m.db, m.canal, ["oi", "sim"] + FALAS_DO_PERFIL, telefone=telefone)
    run_id = rodar(c.cotacao.disparar(m.db, m.canal, telefone, r.disparar, r.estado))
    pedido_id = c.repo.carregar_estado(m.db, m.canal, telefone)["pedido_id"]
    motor_grava_o_quadro(m.banco, pedido_id=pedido_id, dados=m.dados)
    rodar(rodar_o_run(m.db, run_id, m.canal))
    return run_id


def test_a_config_pede_cinco_lembretes_e_saem_dois_no_horario_comercial(mundo, canal):
    from app.services.canal.workflows import _fuso

    m, c = mundo, canal
    m.banco.semear("multicalculo_config", {"company_id": m.canal, "config": {
        "canal": {"follow_up": {"max_sem_resposta": 5, "primeiro_apos_min": 15, "segundo_apos_h": 24,
                                "horario_comercial": {"inicio_h": 9, "fim_h": 20}}}}})
    run_id = _ate_o_resultado(m, c)
    lembretes, horas = [], []
    for _ in range(10):
        wake = m.banco.run(run_id).get("wake_at")
        if not acordar(m.banco, m.db, run_id):
            continue
        horas.append(datetime.fromisoformat(str(wake).replace("Z", "+00:00")).astimezone(_fuso()).hour)
        antes = len(c.envio.enviados)
        rodar(rodar_o_run(m.db, run_id, m.canal))
        lembretes += c.envio.enviados[antes:]
    assert len(lembretes) == 2 and m.banco.run(run_id)["status"] == "completed"
    assert all(9 <= h < 20 for h in horas), horas


@pytest.mark.parametrize("hora_utc,esperado_utc", [(10, 12), (15, 15), (23, 12), (1, 12)])
def test_no_horario_comercial(hora_utc, esperado_utc):
    from app.services.canal.workflows import no_horario_comercial

    t = datetime(2026, 10, 7, hora_utc, 30, tzinfo=timezone.utc)
    r = no_horario_comercial(t, {"inicio_h": 9, "fim_h": 20})
    assert r.hour == esperado_utc and (r >= t)


def test_corretora_sem_whatsapp_publica_assim_mesmo_e_registra(mundo, canal):
    m, c = mundo, canal
    for b in m.banco.linhas("brand_profiles"):
        if b["company_id"] == m.alfa:
            b["contact"] = {}
    run_id = _ate_o_resultado(m, c)
    assert "Prontinho" in c.envio.textos()[-1] and "/r/" in c.envio.textos()[-1]
    eventos = [e for e in m.banco.linhas("work_events") if e.get("work_run_id") == run_id]
    assert any(e["event_type"] == "canal.sem_whatsapp_da_corretora" for e in eventos)


def test_dois_telefones_dois_estados_nenhum_cruza(mundo, canal):
    m, c = mundo, canal
    run_1 = _ate_o_resultado(m, c, telefone=TEL)
    run_2 = _ate_o_resultado(m, c, telefone=TEL_2)
    e1, e2 = (c.repo.carregar_estado(m.db, m.canal, t) for t in (TEL, TEL_2))
    assert run_1 != run_2 and e1["run_id"] == run_1 and e2["run_id"] == run_2 and e1["pedido_id"] != e2["pedido_id"]
    assert all(t in (TEL, TEL_2) for (_c, t, _b) in c.envio.enviados)
    assert {cid for (cid, _t, _b) in c.envio.enviados} == {m.canal}


# =====================================================================================================================
# a passagem: "quero fechar" → a vencedora é avisada; sem aviso, o WhatsApp dela; sem nada, a verdade
# =====================================================================================================================
@pytest.mark.parametrize("avisou,com_whats,esperado", [(True, True, "Avisei a"), (False, True, "wa.me/"),
                                                       (False, False, "Ainda não consegui avisar")])
def test_quero_fechar_passa_a_vencedora(mundo, canal, monkeypatch, avisou, com_whats, esperado):
    m, c = mundo, canal
    avisos = []

    async def avisar(db, company_id, texto, rotulo):
        avisos.append((company_id, texto))
        return avisou

    monkeypatch.setattr(c.cotacao, "_avisar", avisar)
    if not com_whats:
        for b in m.banco.linhas("brand_profiles"):
            if b["company_id"] == m.alfa:
                b["contact"] = {}
    _ate_o_resultado(m, c)
    r = falar(c, m.db, m.canal, ["quero fechar"])
    assert r.estado["etapa"] == "passado" and esperado in "\n".join(r.baloes)
    assert len(avisos) == 1 and avisos[0][0] == m.alfa                   # a VENCEDORA, nunca a perdedora
    assert TEL in avisos[0][1] and "/r/" in avisos[0][1]
    assert M.MARCA_ALFA in "\n".join(r.baloes) or not avisou
    assert m.beta not in str(avisos)
