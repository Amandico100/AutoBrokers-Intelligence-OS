# -*- coding: utf-8 -*-
"""SPEC-131-A · CONSERTO C1 — os guardas dos achados do juiz e do red team (laudos JUIZ-131-A / RED-TEAM-131-A).

Cada guarda nasce VERMELHO no código de `cf12213` e fica VERDE com o conserto (as duas saídas no relatório do conserto).

    RT-B1   o desvio das 06:15 RELÊ os cálculos antes da lista: o que já saiu no Agger da dona não é recalculado, o que
            está no robô não é desviado, e o aviso só diz "não ficou livre" quando foi isso
    J-B1    a InfoCap fora às 02:00 (ou no meio do perfil) → `pendente(sem_conexao)`, nunca `falta_dado`
    RT-P1   a InfoCap que devolve VAZIO com itens do período na tabela → o dia é `sem_conexao`, nunca "completo 100 %"
    RT-P2   `pendente(sem_conexao)` NÃO é feito na completude
    J-P9    o aviso das 06:45 sempre diz "N calculada(s) de M cotável(is)" e nunca "100 %" com 0 de ≥ 1
    J-B2/P7 `falhou` definitivo não volta sozinho; passageiro volta ≤ 2 noites e depois `pendente(precisa_de_voce)`;
            todo motivo que chega ao aviso tem frase de gente
    J-P8    o script do BLOCO 0 sem nome de corretora (CLAUDE.md §13.9)
    canário a lente do canário conta só os itens DESTA rodada
    J-P5    queda entre a porta e o `calculando`: a retomada ADOTA o pedido de hoje, nunca abre o 2º

⛔ Dados sintéticos (os do teste do fio). Nada sai: porta, InfoCap e briefing são os dublês do fio.
"""
from __future__ import annotations

import asyncio
import importlib.util
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import test_spec131a_o_fio as FIO
# ⚠️ importado na COLETA: `PERF.BORDA_REAL` guarda `M.perfil_do_segurado` no import — dentro de um teste com o
# `mundo_real` ativo ele guardaria o DUBLÊ do fio (que ignora a fonte), e o guarda do J-B1 não olharia a borda real
import test_spec131a_o_perfil as PERF
from test_spec131a_o_fio import (DIA, M, R, CONF, PortaDuble, cinco_renovacoes, fechar_com_ofertas, itens,  # noqa: F401
                                 local, madrugada_inteira, montar_corretora, mundo, mundo_real, publicacoes)
from app.comercial import fonte_infocap as FI
from app.services.sistema_de_gestao import dono as DONO

BACKEND = Path(__file__).resolve().parents[1]


def _preparar(m, c, dia=DIA):
    return asyncio.run(M.preparar_dia(m.db, c.id, dia))


def _calcular(m, c, dia=DIA):
    return asyncio.run(M.calcular_dia(m.db, c.id, dia))


def _conferir(m, c, dia=DIA):
    return asyncio.run(CONF.conferir_dia(m.db, c.id, dia))


def _item(m, c, sigla):
    return next(x for x in itens(m, c.id) if x["ramo_sigla"] == sigla)


def _dia(m, c, dia=DIA):
    return next(x for x in m.banco.linhas("renovacao_dias") if x["company_id"] == c.id and x["dia"] == dia.isoformat())


def _aviso_da_corretora(m, c):
    (geral,) = [p for p in publicacoes(m, c.id, "avisar") if p["user_id"] is None]
    return geral["summary_text"]


def _calcs(m, pedido_id):
    return [x for x in m.banco.linhas("multicalculo_calculos") if x["pedido_id"] == pedido_id]


def _a_dona_no_proprio_agger(m, c, pedido_id):
    """O motor achou a dona no próprio Agger: o evento em cada cálculo (motor._vezes_da_pessoa_em_uso)."""
    for calc in _calcs(m, pedido_id):
        m.banco.semear("multicalculo_eventos", {"calculo_id": calc["id"], "pedido_id": pedido_id, "company_id": c.id,
                                                "solicitante_company_id": c.id, "tipo": "agger_da_pessoa_em_uso",
                                                "chave": f"pessoa:{calc['id']}"})


def _ate_aguardando(m, c):
    """00:30 preparar · 02:00 calcular · os outros fecham · o AUTO fica com a dona no próprio Agger (aguardando)."""
    _preparar(m, c)
    _calcular(m, c)
    auto = _item(m, c, "AUTO")
    pedido_da_dona = auto["pedido_id"]
    fechar_com_ofertas(m.banco, [x["pedido_id"] for x in itens(m, c.id) if x.get("pedido_id")
                                 and x["id"] != auto["id"]])
    _a_dona_no_proprio_agger(m, c, pedido_da_dona)
    M.acompanhar(m.db, c.id, por="teste")
    assert _item(m, c, "AUTO")["estado"] == "aguardando_agger"
    return auto["id"], pedido_da_dona


# =====================================================================================================================
# RT-B1 · o desvio das 06:15
# =====================================================================================================================
def test_rt_b1_o_desvio_nao_recalcula_o_que_ja_saiu_no_agger_da_dona(mundo):
    """📊 red team, ataque A: a retentativa do motor caiu às 05:45 e a dona já tinha saído — o pedido dela FECHOU com
    ofertas. O item segue `aguardando_agger` na tabela (a releitura parou às 05:30). O desvio NÃO pode abrir o 2º
    negócio no Agger da corretora, nem avisar que "o Agger do dono não ficou livre"."""
    m = mundo
    c = montar_corretora(m, "token-a", renovacoes=cinco_renovacoes())
    rid, pedido_da_dona = _ate_aguardando(m, c)
    fechar_com_ofertas(m.banco, [pedido_da_dona])          # 05:45: o motor calculou no Agger DELA
    antes = len(PortaDuble.chamadas)
    r = asyncio.run(M.desvio_dia(m.db, c.id, DIA))
    assert PortaDuble.chamadas[antes:] == [], "o desvio abriu um 2º negócio de uma renovação que já tinha ofertas"
    item = next(x for x in itens(m, c.id) if x["id"] == rid)
    assert (item["estado"], item["pedido_id"]) == ("calculada", pedido_da_dona)
    assert publicacoes(m, c.id, "desvio") == [], "avisou um desvio que não aconteceu"
    assert r["desviados"] == 0


def test_rt_b1_o_desvio_nao_leva_o_que_esta_no_robo(mundo):
    """Um cálculo da dona já está NO ROBÔ (`calculando`): `repositorio.cancelar` só cancela `na_fila`, então o desvio
    deixaria dois negócios vivos. Ele espera (a releitura do passo desvio deriva o resultado)."""
    m = mundo
    c = montar_corretora(m, "token-a", renovacoes=cinco_renovacoes())
    rid, pedido_da_dona = _ate_aguardando(m, c)
    primeiro = _calcs(m, pedido_da_dona)[0]
    primeiro.update({"status": "calculando", "negocio_ref": "negocio-no-robo", "versao": 1,
                     "batida_em": m.banco.relogio.iso()})
    antes = len(PortaDuble.chamadas)
    asyncio.run(M.desvio_dia(m.db, c.id, DIA))
    assert PortaDuble.chamadas[antes:] == []
    assert next(x for x in itens(m, c.id) if x["id"] == rid)["pedido_id"] == pedido_da_dona


def test_rt_b1_o_aviso_do_desvio_diz_o_motivo_verdadeiro(mundo):
    """CONTROLE (o desvio CONTINUA acontecendo) + o texto: o item `falhou(calculo_expirado)` é desviado, mas o aviso
    não diz "o Agger do dono não ficou livre" (a dona nunca esteve nele) — diz que o cálculo esperou demais."""
    m = mundo
    c = montar_corretora(m, "token-a", renovacoes=cinco_renovacoes())
    _preparar(m, c)
    _calcular(m, c)
    auto = _item(m, c, "AUTO")
    pedido = auto["pedido_id"]
    fechar_com_ofertas(m.banco, [x["pedido_id"] for x in itens(m, c.id) if x.get("pedido_id") and x["id"] != auto["id"]])
    for calc in _calcs(m, pedido):
        calc.update({"status": "expirado"})
    M.acompanhar(m.db, c.id, por="teste")
    assert (_item(m, c, "AUTO")["estado"], _item(m, c, "AUTO")["motivo"]) == ("falhou", "calculo_expirado")
    antes = len(PortaDuble.chamadas)
    r = asyncio.run(M.desvio_dia(m.db, c.id, DIA))
    nova = PortaDuble.chamadas[antes:]
    assert r["desviados"] == 1 and len(nova) == 1 and nova[0]["forcar_corretora_motivo"] == M.MOTIVO_DO_DESVIO
    (aviso,) = publicacoes(m, c.id, "desvio")
    texto = aviso["summary_text"]
    assert "Agger da CORRETORA" in texto
    assert "não ficou livre" not in texto, texto
    assert R.frase_do_motivo("calculo_expirado") in texto, texto


# =====================================================================================================================
# J-B1 · a InfoCap fora às 02:00 → sem_conexao, nunca falta_dado
# =====================================================================================================================
def test_j_b1_infocap_fora_as_duas_nao_vira_falta_dado(mundo_real, monkeypatch):
    """📊 juiz (scratchpad/juiz_infocap_fora.py): `calcular_dia` punha `fonte = None` e o `_pedir` rodava assim mesmo —
    o perfil saía None e o item `pronta` virava `pendente(falta_dado)` com os 13 nomes. O perfil é o REAL (a borda do
    produto sobre a rede dublê), como no teste do perfil."""
    m = mundo_real
    c, _linhas, _rede = PERF._uma_corretora_com_o_perfil(m, monkeypatch)
    _preparar(m, c)
    assert _item(m, c, "AUTO")["estado"] == "pronta"
    prontas = {x["id"] for x in itens(m, c.id) if x["estado"] == "pronta"}
    pedidos_antes = len(m.banco.linhas("multicalculo_pedidos"))

    async def infocap_fora(_db, _cid):
        raise ConnectionError("a InfoCap caiu às 02:00")

    monkeypatch.setattr(DONO, "abrir_fonte", infocap_fora)
    _calcular(m, c)
    auto = _item(m, c, "AUTO")
    assert (auto["estado"], auto["motivo"]) == ("pendente", "sem_conexao"), (auto["estado"], auto["motivo"])
    assert len(m.banco.linhas("multicalculo_pedidos")) == pedidos_antes, "sem a InfoCap, nada vai ao Agger"
    # nenhuma das que estavam PRONTAS virou "falta um dado" (o RESI deste mundo já é `falta_dado` desde as 00:30 — o
    # tipo do imóvel não está na InfoCap, test_spec131a_o_perfil — e não é desta queda)
    assert {(x["estado"], x["motivo"]) for x in itens(m, c.id) if x["id"] in prontas} == {("pendente", "sem_conexao")}


def test_j_b1_a_infocap_que_falha_no_meio_do_perfil_e_sem_conexao(mundo_real, monkeypatch):
    """A fonte abriu, mas o `/documento` do perfil levantou `FalhaDaInfocap` → `sem_conexao` (não "falta um dado").
    CONTROLE: o MESMO item com a InfoCap respondendo fica `pronta` (test_spec131a_o_perfil)."""
    m = mundo_real
    c, _linhas, _rede = PERF._uma_corretora_com_o_perfil(m, monkeypatch)
    _preparar(m, c)
    item = _item(m, c, "AUTO")
    cfg = M.carregar_config(m.db, c.id)
    fonte = m.fontes[c.id]
    ok = asyncio.run(M._avaliar(m.db, c.id, item, fonte, cfg))
    assert ok[0] == "pronta", ok[:2]                                   # CONTROLE

    def caiu(*_a, **_k):
        raise FI.FalhaDaInfocap("a InfoCap não respondeu /documento: HTTP 503")

    monkeypatch.setattr(fonte, "documento_cru", caiu)
    estado, motivo, pedido, _dados = asyncio.run(M._avaliar(m.db, c.id, item, fonte, cfg))
    assert (estado, motivo, pedido) == ("pendente", "sem_conexao", None)


# =====================================================================================================================
# RT-P1 · RT-P2 · J-P9 · a completude
# =====================================================================================================================
def test_rt_p1_infocap_vazia_com_itens_do_periodo_e_sem_conexao(mundo):
    """📊 red team, ataque B: `_get` trata 404 como `{}` → `renovacoes_cruas` = [] → esperadas 0 → `_pct(0, 0)` = 100
    → "completo", sem aviso. A tabela tinha os itens do período."""
    m = mundo
    c = montar_corretora(m, "token-a", renovacoes=cinco_renovacoes())
    _preparar(m, c)
    m.rede.bancos["token-a"]["renov"] = []
    m.rede.cache.clear()
    r = _conferir(m, c)
    d = _dia(m, c)
    assert r["estado"] == d["estado"] == "sem_conexao", (r, d["estado"], d["completude_pct"])
    assert d["completude_pct"] is None and d["esperadas"] is None
    (alerta,) = publicacoes(m, c.id, "conferencia")
    assert alerta["briefing_type"] == "critical_alert"
    # CONTROLE: a InfoCap de volta → o mesmo dia é conferido (não fica `sem_conexao`)
    m.rede.bancos["token-a"]["renov"] = cinco_renovacoes()
    m.rede.cache.clear()
    assert _conferir(m, c)["estado"] != "sem_conexao"


def test_rt_p2_pendente_sem_conexao_nao_conta_como_feito(mundo):
    """📊 red team, ataque C: tudo `pendente(sem_conexao)` dava `completo 100 %`. O que não foi tratado não é feito."""
    m = mundo
    c = montar_corretora(m, "token-a", renovacoes=cinco_renovacoes())
    _preparar(m, c)
    repo = R.RepositorioDeRenovacoes(m.db)
    for x in [x for x in itens(m, c.id) if x["estado"] == "pronta"]:
        repo.transicionar(c.id, x["id"], "pendente", por="teste", motivo="sem_conexao")
    _conferir(m, c)
    d = _dia(m, c)
    assert float(d["completude_pct"]) == 40.0, d["completude_pct"]       # só os 2 não cotáveis (com motivo) são feitos
    assert d["estado"] == "incompleto"
    assert (d["detalhes"] or {}).get("sem_conexao") == 3


def test_j_p9_o_aviso_diz_calculadas_de_cotaveis_e_nunca_100_com_zero(mundo):
    """📊 juiz: 10-12 = `completo · 100.00 % · calculadas 0`. A fórmula da SPEC conta `falta_dado` como feito; o aviso
    das 06:45 dá ao lado o número que diz a verdade, e não escreve "100 %" quando nenhuma cotável saiu."""
    m = mundo
    c = montar_corretora(m, "token-a", renovacoes=cinco_renovacoes())
    _preparar(m, c)
    repo = R.RepositorioDeRenovacoes(m.db)
    for x in [x for x in itens(m, c.id) if x["estado"] == "pronta"]:
        repo.transicionar(c.id, x["id"], "pendente", por="teste", motivo="falta_dado")
    _conferir(m, c)
    assert float(_dia(m, c)["completude_pct"]) == 100.0                   # a fórmula da SPEC, como está
    M.avisar_dia(m.db, c.id, DIA)
    texto = _aviso_da_corretora(m, c)
    assert "0 calculada(s) de 3 cotável(is)" in texto, texto
    assert "100" not in texto, texto


def test_j_p9_controle_o_dia_normal_tambem_diz_calculadas_de_cotaveis(mundo):
    m = mundo
    c = montar_corretora(m, "token-a", renovacoes=cinco_renovacoes())
    madrugada_inteira(m, c)
    texto = _aviso_da_corretora(m, c)
    assert "3 calculada(s) de 3 cotável(is)" in texto and "completude 100.0%" in texto, texto


# =====================================================================================================================
# J-B2 (o estado) · RT-P7 · J-P2 · J-P7 · a retentativa tem fim e todo motivo tem frase
# =====================================================================================================================
def _falhou_sem_oferta(m, c):
    _preparar(m, c)
    _calcular(m, c)
    auto = _item(m, c, "AUTO")
    fechar_com_ofertas(m.banco, [x["pedido_id"] for x in itens(m, c.id) if x.get("pedido_id")],
                       sem_oferta=[auto["pedido_id"]])
    M.acompanhar(m.db, c.id, por="teste")
    return _item(m, c, "AUTO")


def test_j_b2_falhou_definitivo_nao_volta_a_pronta_sozinho(mundo):
    """📊 juiz B2 / red team P7: o `4d9be9e8` fez falhou → pronta → calculando → falhou, e voltaria toda noite até o
    fimvig (~15 seguradoras por noite). `calculo_fechado` = todas as seguradoras recusaram: a próxima noite é igual."""
    m = mundo
    c = montar_corretora(m, "token-a", renovacoes=cinco_renovacoes())
    auto = _falhou_sem_oferta(m, c)
    assert (auto["estado"], auto["motivo"]) == ("falhou", "calculo_fechado")
    m.relogio._t = local(0, 31, DIA + timedelta(days=1))
    m.rede.cache.clear()
    _preparar(m, c, DIA + timedelta(days=1))
    auto = _item(m, c, "AUTO")
    assert (auto["estado"], auto["motivo"]) == ("falhou", "calculo_fechado")
    # CONTROLE: o RESI (calculado) e o resto não mudaram por causa disso
    assert _item(m, c, "RESI")["estado"] == "calculada"


def test_j_b2_falhou_passageiro_volta_no_maximo_duas_noites(mundo):
    m = mundo
    c = montar_corretora(m, "token-a", renovacoes=cinco_renovacoes())
    repo = R.RepositorioDeRenovacoes(m.db)
    _preparar(m, c)
    rid = _item(m, c, "AUTO")["id"]
    for noite in range(3):
        dia = DIA + timedelta(days=noite)
        m.relogio._t = local(0, 31, dia)
        if noite:
            m.rede.cache.clear()
            _preparar(m, c, dia)
            assert _item(m, c, "AUTO")["estado"] == "pronta", f"a {noite}ª volta não aconteceu"
        m.relogio._t = local(3, 0, dia)
        repo.transicionar(c.id, rid, "calculando", por="teste")
        repo.transicionar(c.id, rid, "falhou", por="teste", motivo="calculo_falhou")
    m.relogio._t = local(0, 31, DIA + timedelta(days=3))
    m.rede.cache.clear()
    _preparar(m, c, DIA + timedelta(days=3))
    auto = _item(m, c, "AUTO")
    assert (auto["estado"], auto["motivo"]) == ("pendente", "precisa_de_voce"), (auto["estado"], auto["motivo"])
    # e fica: a próxima preparação não o devolve à fila
    m.relogio._t = local(0, 31, DIA + timedelta(days=4))
    m.rede.cache.clear()
    _preparar(m, c, DIA + timedelta(days=4))
    assert (_item(m, c, "AUTO")["estado"], _item(m, c, "AUTO")["motivo"]) == ("pendente", "precisa_de_voce")
    M.avisar_dia(m.db, c.id, DIA + timedelta(days=4))
    assert R.frase_do_motivo("precisa_de_voce") in " ".join(p["summary_text"] for p in publicacoes(m, c.id, "avisar"))


def _motivos_que_chegam_ao_aviso():
    excecoes = ("RamoIndisponivel", "RamoNaoSuportado", "FichaIncompleta", "PedidoIncompleto", "DocumentoInvalido",
                "ContaRecusada", "DesvioIndisponivel", "ChaveAusente", "OutraCoisa")
    vindos = {M.motivo_da_excecao(type(n, (Exception,), {})())[1] for n in excecoes}
    calculo = {M._motivo_do_calculo({"status": s}) for s in M.ESTADOS_TERMINAIS_DO_CALCULO}
    return sorted(vindos | calculo | set(M.MOTIVOS_PASSAGEIROS) | set(R.MOTIVOS_DE_PENDENCIA)
                  | {M.MOTIVO_LICENCA_VENCIDA, "precisa_de_voce"})


def test_j_p7_todo_motivo_que_chega_ao_aviso_tem_frase_de_gente():
    sem_frase = [mo for mo in _motivos_que_chegam_ao_aviso() if R.frase_do_motivo(mo) == mo.replace("_", " ")]
    assert sem_frase == [], sem_frase
    # CONTROLE: o guarda consegue ficar vermelho (um código sem frase cai no replace)
    assert R.frase_do_motivo("motivo_que_ninguem_escreveu") == "motivo que ninguem escreveu"


def test_j_p7_o_aviso_diz_por_que_falhou(mundo):
    m = mundo
    c = montar_corretora(m, "token-a", renovacoes=cinco_renovacoes())
    _falhou_sem_oferta(m, c)
    M.avisar_dia(m.db, c.id, DIA)
    texto = _aviso_da_corretora(m, c)
    assert "1 falharam (" in texto and R.frase_do_motivo("calculo_fechado") in texto, texto


# =====================================================================================================================
# J-P8 / RT-P11 · §13.9 no script do BLOCO 0
# =====================================================================================================================
NOMES_DE_CORRETORA = re.compile(r"auto\s*fleet|resulta(?!d)|amandus", re.IGNORECASE)   # "resultado" não é nome


@pytest.mark.parametrize("arquivo", ["scripts/bloco0_131a_agger_ao_vivo.py", "scripts/canario_madrugada_renovacao.py"])
def test_j_p8_scripts_sem_nome_de_corretora(arquivo):
    texto = (BACKEND / arquivo).read_text(encoding="utf-8")
    assert NOMES_DE_CORRETORA.findall(texto) == []
    # CONTROLE: o padrão acha o nome na forma em que ele estava (a variável de ambiente)
    assert NOMES_DE_CORRETORA.search("AGGER_AUTOFLEET_COTADOR_LOGIN")
    assert NOMES_DE_CORRETORA.search('nova_sessoes(nav, "resulta")')
    assert not NOMES_DE_CORRETORA.search("resultado do cálculo")


# =====================================================================================================================
# o canário: a lente conta só ESTA rodada
# =====================================================================================================================
def _canario():
    spec = importlib.util.spec_from_file_location("canario_madrugada_renovacao",
                                                  BACKEND / "scripts" / "canario_madrugada_renovacao.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_a_lente_do_canario_conta_so_esta_rodada():
    """📊 juiz (LENTE DO DADO): sem o filtro, a tabela tinha 7 itens no período — 3 `canario=true` de rodadas
    anteriores. A medida da rodada é a dos itens escolhidos NELA (e o que ela criou)."""
    C = _canario()
    t0 = datetime(2026, 10, 13, 3, 33, tzinfo=timezone.utc)
    antes, depois = (t0 - timedelta(hours=2)).isoformat(), (t0 + timedelta(minutes=5)).isoformat()
    linhas = [
        {"id": "a", "codfil": 1, "nosnum": "100", "criado_em": antes},      # escolhido agora, já existia (sem evento novo)
        {"id": "b", "codfil": 1, "nosnum": "200", "criado_em": depois},     # escolhido agora, nasceu agora
        {"id": "c", "codfil": 1, "nosnum": "300", "criado_em": antes},      # rodada ANTERIOR
        {"id": "d", "codfil": 1, "nosnum": "400", "criado_em": depois},     # nasceu nesta rodada (a conferência)
    ]
    chaves = {(1, "100"), (1, "200")}
    assert sorted(x["id"] for x in C.itens_desta_rodada(linhas, chaves, t0)) == ["a", "b", "d"]
    # CONTROLE: sem o filtro seriam as 4 (o que a lente somava)
    assert len(linhas) == 4


# =====================================================================================================================
# J-P5 · a queda entre a porta e o `calculando`
# =====================================================================================================================
def test_j_p5_a_retomada_adota_o_pedido_de_hoje(mundo, monkeypatch):
    m = mundo
    c = montar_corretora(m, "token-a", renovacoes=cinco_renovacoes())
    _preparar(m, c)
    original = R.RepositorioDeRenovacoes.transicionar
    caiu = []

    def transicionar(self, company_id, renovacao_id, para, **kw):
        if para == "calculando" and not caiu:
            caiu.append(renovacao_id)
            raise RuntimeError("o worker caiu entre a porta e o calculando")
        return original(self, company_id, renovacao_id, para, **kw)

    monkeypatch.setattr(R.RepositorioDeRenovacoes, "transicionar", transicionar)
    with pytest.raises(RuntimeError):
        _calcular(m, c)
    (rid,) = caiu
    (primeiro,) = [p for p in m.banco.linhas("multicalculo_pedidos") if p.get("renovacao_id") == rid]
    assert next(x for x in itens(m, c.id) if x["id"] == rid)["estado"] == "pronta"
    _calcular(m, c)                                                      # a retomada do passo (efeito idempotente)
    pedidos = [p for p in m.banco.linhas("multicalculo_pedidos") if p.get("renovacao_id") == rid]
    assert [p["id"] for p in pedidos] == [primeiro["id"]], f"{len(pedidos)} pedidos para a mesma renovação"
    item = next(x for x in itens(m, c.id) if x["id"] == rid)
    assert (item["estado"], item["pedido_id"]) == ("calculando", primeiro["id"])
    # CONTROLE: as outras renovações foram pedidas normalmente (uma vez cada)
    outras = [x for x in itens(m, c.id) if x["id"] != rid and x["estado"] == "calculando"]
    assert len(outras) == 2
