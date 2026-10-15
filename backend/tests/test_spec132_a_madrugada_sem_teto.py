# -*- coding: utf-8 -*-
"""SPEC-132 (Founder 14/10) — a madrugada da Renovação SEM teto fixo: o RELÓGIO decide.

    "Se tiver 30 renovações no dia, o agente precisa fazer as 30. Nunca pode ser só 12 … no mínimo 30. Se o problema
     for o tempo, aumente a janela. Minha promessa: às 7h estará tudo cotado no Agger."

    ① 42 renovações (o 📊 pico medido de um dono num dia, BLOCO 0 131-A) → as 42 entram na fila, nas DUAS corretoras:
      as que vencem hoje E o pico de daqui a 2 dias (a antecipação sem teto) — relógio dublê folgado (01:01)
    ② relógio APERTADO: na hora-limite (05:55) o que não começou no Agger sai da fila e volta
      `pronta(ficou_para_a_proxima_noite)`; o que já está no robô NÃO é tocado; a noite seguinte o pega primeiro e o
      aviso das 06:45 diz quantas ficaram
    ③ o calcular que chega DEPOIS da hora-limite não começa nada (marca tudo para a próxima noite)
    ④ teto configurado 10 (ou 12, ou 29) → RECUSADO na tela e ignorado na leitura (fica sem teto): mínimo 30
    ⑤ a conta da janela: com a janela padrão cabem ≥ 30 pedidos POR CORRETORA mesmo no pior caso medido
    ⑥ o calcular das 01:00 ESPERA a lista das 00:30 terminar (o Work OS real: dorme e acorda)

Dublê só na borda (InfoCap na rede, a porta/Agger, o relógio); `madrugada`, `renovacao`, `config` e o Work OS são os
REAIS. Nenhum nome de corretora: tudo por `company_id` gerado (CLAUDE.md §13.9).
"""
from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest

from app.services.multicalculo import config as CFG
from test_spec131a_o_fio import (DIA, M, R, PortaDuble, acordar, avisos, fechar_com_ofertas, itens, linha_renov,  # noqa: F401
                                 local, montar_corretora, mundo, rodar, run_do_passo, tick)


@pytest.fixture(autouse=True)
def _rede_sem_espera(monkeypatch):
    """A BORDA da rede: a InfoCap dublê não serve `/documento`, e a releitura espera 3 s + 6 s por item (~9 s × 84
    itens aqui). O resultado é o mesmo sem a espera — só o relógio de parede muda."""
    from app.comercial import fonte_infocap as FI

    monkeypatch.setattr(FI, "ESPERA_BASE_S", 0)


def _preparar(m, c, dia=DIA):
    return asyncio.run(M.preparar_dia(m.db, c.id, dia))


def _quarenta_e_duas(base: int, fimvig) -> list:
    return [linha_renov(base + k, "RESI", fimvig) for k in range(42)]


def _cancelar_pelo_repositorio(m):
    """A borda `porta.cancelar` pelo repositório REAL do multicálculo (pedido → cancelado; só `na_fila` → cancelado)."""
    from app.services.multicalculo.repositorio import RepositorioMulticalculo

    async def _cancelar(db, company_id, *, pedido_id):
        return RepositorioMulticalculo(m.db).cancelar(company_id=company_id, pedido_id=pedido_id)
    return _cancelar


def _calculos(m, pedido_id):
    return [x for x in m.banco.linhas("multicalculo_calculos") if x["pedido_id"] == pedido_id]


def _na_fila(m):
    """Os cálculos que a porta dublê grava nascem SEM status — o motor de verdade os grava `na_fila`."""
    for x in m.banco.linhas("multicalculo_calculos"):
        x.setdefault("status", "na_fila")
        if x.get("status") is None:
            x["status"] = "na_fila"


# =====================================================================================================================
# ① o pico inteiro entra — nas duas corretoras
# =====================================================================================================================
def test_42_renovacoes_num_dia_entram_as_42_nas_duas_corretoras(mundo):
    m = mundo
    hoje = montar_corretora(m, "token-a", renovacoes=_quarenta_e_duas(940000, DIA + timedelta(days=10)))
    pico = montar_corretora(m, "token-b", renovacoes=_quarenta_e_duas(950000, DIA + timedelta(days=12)))
    for c in (hoje, pico):
        _preparar(m, c)
        assert sorted({x["estado"] for x in itens(m, c.id)}) == ["pronta"]
    folgado = local(1, 1)
    r_hoje = asyncio.run(M.calcular_dia(m.db, hoje.id, DIA, agora=folgado))
    r_pico = asyncio.run(M.calcular_dia(m.db, pico.id, DIA, agora=folgado))
    # as 42 que vencem hoje E as 42 do pico de daqui a 2 dias (antecipadas: SEM teto, o relógio decide)
    assert (r_hoje["vencidas"], r_hoje["antecipadas"], r_hoje["disparados"]) == (42, 0, 42), r_hoje
    assert (r_pico["vencidas"], r_pico["antecipadas"], r_pico["disparados"]) == (0, 42, 42), r_pico
    assert r_hoje["acima_do_teto"] == r_pico["acima_do_teto"] == 0
    for c in (hoje, pico):
        assert [x["estado"] for x in itens(m, c.id)] == ["calculando"] * 42
    # duas corretoras, zero cruzamento: cada pedido é da corretora do item
    pedidos = {p["id"]: p["company_id"] for p in m.banco.linhas("multicalculo_pedidos")}
    assert all(pedidos[x["pedido_id"]] == x["company_id"] for x in m.banco.linhas("renovacoes"))
    assert sum(1 for ch in PortaDuble.chamadas if ch["company_id"] == hoje.id) == 42
    assert sum(1 for ch in PortaDuble.chamadas if ch["company_id"] == pico.id) == 42


# =====================================================================================================================
# ② o relógio apertado: para na hora-limite, marca, e a próxima noite pega primeiro
# =====================================================================================================================
class _Runs:
    def __init__(self):
        self.sonos = []

    def dormir(self, run_id, **kw):
        self.sonos.append(kw)
        return "DORMIU"


def test_relogio_apertado_para_na_hora_limite_e_a_sobra_vai_primeiro_na_proxima_noite(mundo, monkeypatch):
    m = mundo
    renov = [linha_renov(960000 + k, "RESI", DIA + timedelta(days=10)) for k in range(5)]
    c = montar_corretora(m, "token-a", renovacoes=renov)
    _preparar(m, c)
    asyncio.run(M.calcular_dia(m.db, c.id, DIA, agora=local(1, 1)))
    _na_fila(m)
    por_nosnum = {x["nosnum"]: x for x in itens(m, c.id)}
    assert len(por_nosnum) == 5
    feitos = [por_nosnum[str(960000 + k)]["pedido_id"] for k in (0, 1)]
    fechar_com_ofertas(m.banco, feitos)                                   # o motor fechou 2
    no_robo = por_nosnum[str(960002)]
    _calculos(m, no_robo["pedido_id"])[0]["status"] = "calculando"        # 1 já começou no Agger
    sobram = {str(960003), str(960004)}                                    # 2 nunca saíram da fila
    monkeypatch.setattr(M, "cancelar_na_porta", _cancelar_pelo_repositorio(m))

    # 05:50 (ANTES da hora-limite): nada é tirado da fila; o sono acorda NA hora-limite, não 10 min depois
    runs = _Runs()
    ctx = {"runs": runs, "run_id": "run-teste", "lease_token": "t"}
    m.relogio._t = local(5, 50)
    asyncio.run(M._acompanhar_ou_dormir(ctx, m.db, c.id, DIA, ate_passo="conferir", passo="calcular"))
    assert {x["estado"] for x in itens(m, c.id) if x["nosnum"] in sobram} == {"calculando"}
    assert runs.sonos[-1]["acordar_em_s"] == pytest.approx(5 * 60, abs=1)

    # 05:56 (DEPOIS): as 2 da fila voltam `pronta(ficou_para_a_proxima_noite)`; a do robô segue; as feitas, calculadas
    m.relogio._t = local(5, 56)
    asyncio.run(M._acompanhar_ou_dormir(ctx, m.db, c.id, DIA, ate_passo="conferir", passo="calcular"))
    estado = {x["nosnum"]: (x["estado"], x.get("motivo")) for x in itens(m, c.id)}
    for n in sobram:
        assert estado[n] == ("pronta", R.MOTIVO_FICOU_PARA_A_PROXIMA_NOITE), estado
    assert estado[str(960002)] == ("calculando", None), "tocou num cálculo que já tinha começado no Agger"
    assert {estado[str(960000)], estado[str(960001)]} == {("calculada", None)}
    pedidos = {p["id"]: p for p in m.banco.linhas("multicalculo_pedidos")}
    for n in sobram:
        pid = por_nosnum[n]["pedido_id"]
        assert pedidos[pid]["status"] == "cancelado" and {x["status"] for x in _calculos(m, pid)} == {"cancelado"}
    assert pedidos[no_robo["pedido_id"]].get("status") != "cancelado"

    # o aviso das 06:45 diz quantas ficaram — nunca caladas
    m.relogio._t = local(6, 46)
    M.avisar_dia(m.db, c.id, DIA)
    (da_corretora,) = [s for s in avisos(m, c.id) if s.get("user_id") is None]
    assert "2 ficaram para a próxima noite" in da_corretora["summary_text"], da_corretora["summary_text"]

    # a noite seguinte: a lista reavalia e a MARCA sobrevive; o calcular pega as 2 PRIMEIRO
    amanha = DIA + timedelta(days=1)
    m.rede.bancos["token-a"]["renov"] = renov + [linha_renov(960010, "RESI", DIA + timedelta(days=10))]
    _preparar(m, c, amanha)
    marcadas = {x["nosnum"] for x in itens(m, c.id) if x.get("motivo") == R.MOTIVO_FICOU_PARA_A_PROXIMA_NOITE}
    assert marcadas == sobram, "a preparação apagou a marca da noite anterior"
    antes = len(PortaDuble.chamadas)
    asyncio.run(M.calcular_dia(m.db, c.id, amanha, agora=local(1, 1, amanha)))
    ordem = [ch["renovacao_id"] for ch in PortaDuble.chamadas[antes:]]
    ids = {x["nosnum"]: x["id"] for x in itens(m, c.id)}
    assert set(ordem[:2]) == {ids[n] for n in sobram}, "a sobra de ontem não entrou primeiro"
    assert ids[str(960010)] in ordem[2:]
    # e a marca some quando o cálculo sai (o item está `calculando`, sem motivo)
    assert all(x.get("motivo") is None for x in itens(m, c.id) if x["nosnum"] in sobram)


def test_a_ordem_e_o_vencimento_mais_proximo_e_no_empate_a_que_sobrou():
    def p(n, fim, marca=False):
        return {"id": f"x{n}", "dono_user_id": "d", "estado": "pronta", "calcular_em": DIA.isoformat(),
                "fimvig": fim.isoformat(), "ramo_agger": 2, "nosnum": str(n),
                "motivo": R.MOTIVO_FICOU_PARA_A_PROXIMA_NOITE if marca else None}
    perto, longe = DIA + timedelta(days=9), DIA + timedelta(days=10)
    itens_ = [p(1, longe), p(2, longe, marca=True), p(3, perto), p(4, longe)]
    escolhidos, _ = M.escolher_da_noite(itens_, DIA, teto=None, antecipar_ate_dias=7)
    assert [x["id"] for x in escolhidos] == ["x3", "x2", "x1", "x4"]


# =====================================================================================================================
# ③ o calcular que chega depois da hora-limite não começa nada
# =====================================================================================================================
def test_o_calcular_depois_da_hora_limite_nao_comeca_nada(mundo):
    m = mundo
    c = montar_corretora(m, "token-a", renovacoes=[linha_renov(970000 + k, "RESI", DIA + timedelta(days=10))
                                                   for k in range(3)])
    _preparar(m, c)
    antes = len(PortaDuble.chamadas)
    r = asyncio.run(M.calcular_dia(m.db, c.id, DIA, agora=local(5, 56)))
    assert (r["disparados"], r["ficaram_para_a_proxima_noite"]) == (0, 3), r
    assert len(PortaDuble.chamadas) == antes
    assert {(x["estado"], x.get("motivo")) for x in itens(m, c.id)} == {("pronta", R.MOTIVO_FICOU_PARA_A_PROXIMA_NOITE)}
    # CONTROLE: um minuto ANTES da hora-limite, as 3 saem
    c2 = montar_corretora(m, "token-b", renovacoes=[linha_renov(971000 + k, "RESI", DIA + timedelta(days=10))
                                                    for k in range(3)])
    _preparar(m, c2)
    assert asyncio.run(M.calcular_dia(m.db, c2.id, DIA, agora=local(5, 54)))["disparados"] == 3


# =====================================================================================================================
# ④ o teto configurado nunca fica abaixo de 30
# =====================================================================================================================
@pytest.mark.parametrize("ruim", [10, 12, 29, 0, 501, 30.5, "30", True])
def test_teto_abaixo_de_30_e_recusado_na_tela_e_ignorado_na_leitura(ruim):
    erros = CFG.erros_da_edicao({"renovacao": {"teto_por_conta_noite": ruim}})
    assert erros and "30" in erros[0], erros
    cfg = CFG.mesclar({"servicos": {"renovacao": {"teto_por_conta_noite": ruim}}}, "renovacao")
    assert cfg["servicos"]["renovacao"]["teto_por_conta_noite"] is None
    assert CFG.teto_por_conta_noite(cfg) is None
    assert R.parametros(cfg)["teto_por_conta_noite"] is None
    assert R.parametros({"servicos": {"renovacao": {"teto_por_conta_noite": ruim}}})["teto_por_conta_noite"] is None


def test_o_padrao_e_sem_teto_e_30_ou_mais_vale():
    assert CFG.PADRAO_DO_PRODUTO["servicos"]["renovacao"]["teto_por_conta_noite"] is None
    assert CFG.teto_por_conta_noite(CFG.mesclar(None, "renovacao")) is None
    assert R.parametros({})["teto_por_conta_noite"] is None
    assert CFG.TETO_POR_CONTA_NOITE_FAIXA[0] == R.TETO_POR_CONTA_NOITE_MINIMO == 30
    for bom in (30, 42, 500, None):
        assert CFG.erros_da_edicao({"renovacao": {"teto_por_conta_noite": bom}}) == [], bom
        assert CFG.teto_por_conta_noite(CFG.mesclar({"servicos": {"renovacao": {"teto_por_conta_noite": bom}}},
                                                    "renovacao")) == bom
    # CONTROLE (o guarda consegue ficar vermelho): o mesmo número que a régua aceita a 30 é recusado a 29
    assert CFG.erros_da_edicao({"renovacao": {"teto_por_conta_noite": 29}})


# =====================================================================================================================
# ⑤ a conta da janela
# =====================================================================================================================
#: 📊 LAUDO-I1 §2.4 — o pior pedido de renovação: login 54 s + teto de leitura 480 s + logout 14 s
PIOR_PEDIDO_S = 54 + 480 + 14


def _min(hhmm: str) -> int:
    h, mi = hhmm.split(":")
    return int(h) * 60 + int(mi)


def test_a_janela_padrao_cabe_30_no_pior_caso_e_termina_antes_das_7h():
    j = CFG.janela_da_renovacao(CFG.mesclar(None, "renovacao"))
    comeco = _min(j["ultimo_inicio"]) - _min(j["calcular"])
    assert comeco * 60 // PIOR_PEDIDO_S >= 30, f"cabem só {comeco * 60 // PIOR_PEDIDO_S} no pior caso"
    # quem começa na hora-limite termina (pior caso) antes da conferência; desvio e aviso antes das 07:00
    assert _min(j["ultimo_inicio"]) * 60 + PIOR_PEDIDO_S <= _min(j["conferir"]) * 60
    assert _min(j["preparar"]) < _min(j["calcular"]) < _min(j["ultimo_inicio"]) < _min(j["conferir"]) \
        < _min(j["desvio"]) < _min(j["avisar"]) < 7 * 60
    # CONTROLE: a janela ANTIGA (02:00 → 05:30, sem hora-limite) não cabia 30 no pior caso
    assert (_min("05:30") - _min("02:00")) * 60 // PIOR_PEDIDO_S < 30


def test_a_hora_limite_fora_da_regua_volta_a_conferencia_menos_a_margem():
    base = {"servicos": {"renovacao": {"janela": {"conferir": "05:30", "ultimo_inicio": "05:55"}}}}
    assert CFG.janela_da_renovacao(CFG.mesclar(base, "renovacao"))["ultimo_inicio"] == "05:20"
    base = {"servicos": {"renovacao": {"janela": {"ultimo_inicio": "00:10"}}}}           # antes do calcular
    assert CFG.janela_da_renovacao(CFG.mesclar(base, "renovacao"))["ultimo_inicio"] == "05:55"
    base = {"servicos": {"renovacao": {"janela": {"ultimo_inicio": "05:00"}}}}           # dentro: vale
    assert CFG.janela_da_renovacao(CFG.mesclar(base, "renovacao"))["ultimo_inicio"] == "05:00"


# =====================================================================================================================
# ⑥ o calcular das 01:00 espera a lista das 00:30 (o Work OS real)
# =====================================================================================================================
def test_o_calcular_espera_a_lista_terminar(mundo):
    m = mundo
    c = montar_corretora(m, "token-a", renovacoes=[linha_renov(980000 + k, "RESI", DIA + timedelta(days=10))
                                                   for k in range(3)])
    tick(m, local(0, 31))                      # a lista do dia é enfileirada…
    tick(m, local(1, 1))                       # …e o calcular também, ANTES de a lista rodar
    prep, calc = run_do_passo(m, c.id, "preparar"), run_do_passo(m, c.id, "calcular")
    antes = len(PortaDuble.chamadas)
    rodar(m, calc["id"], c.id)
    assert m.banco.run(calc["id"])["status"] == "waiting_input", m.banco.run(calc["id"]).get("error_message")
    assert len(PortaDuble.chamadas) == antes, "o calcular disparou com a lista ainda em curso"
    rodar(m, prep["id"], c.id)
    assert m.banco.run(prep["id"])["status"] == "completed"
    acordar(m, calc["id"])
    rodar(m, calc["id"], c.id)
    assert len(PortaDuble.chamadas) - antes == 3
    assert sorted(x["estado"] for x in itens(m, c.id)) == ["calculando"] * 3
