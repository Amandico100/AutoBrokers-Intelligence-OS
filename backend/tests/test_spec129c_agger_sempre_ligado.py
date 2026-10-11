# -*- coding: utf-8 -*-
"""SPEC-129-C F0 — o Agger da corretora SEMPRE LIGADO (D-129C-01).

O Founder (11/10): *"O Agger tem horário para ser executado… pode travar durante uma execução. O Agger da corretora NÃO
deve ter horário de funcionamento. Deve ficar ligado o tempo todo. Se for para ter horário ou personalização, isso deve
ser feito nos AUXILIARES. O conector é só a conexão do sistema."*

O FIO: a rota REAL (`app/api/portal.py`) → o serviço REAL (`conta_do_robo`) → `portal_accounts` no banco dublê com as
travas do U1 → `robos.escolher` (o MESMO que o motor chama) → o MOTOR real (`motor.Motor.uma_volta`). Dublê só na borda:
o banco, o Agger e a sessão (os mesmos de `test_spec129b_o_motor` e `test_spec133a1_o_agger_da_corretora`).

    ① a tela grava a conta global SEM janela → o robô aceita domingo às 03:00 (CONTROLE: a conta do comando com janela
      continua recusada no mesmo instante); a tela não oferece "Horário" e o servidor recusa a ação `janela`
    ② o cálculo EM ANDAMENTO não é morto quando a janela fecha (CONTROLE: uma batida que checasse a janela o mataria)
    ③ a RETOMADA de um cálculo que já saiu não espera a janela reabrir (CONTROLE: pedido NOVO fora da janela espera)
    ④ a econômica que entra no negócio já aberto pelo mesmo pedido não espera a janela reabrir
    ⑤ o comando `sempre-ligada` é idempotente, só toca a conta global, nunca a de teste nem a do rodízio

⛔ Nenhuma senha real.
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from portal_worker.multicalculo import comando_robo as CMD  # noqa: E402
from portal_worker.multicalculo import conta_do_robo as CR  # noqa: E402
from portal_worker.multicalculo import robos as ROB  # noqa: E402

# os mundos dublês JÁ existentes (um banco, um Agger, uma sessão) — nenhum dublê novo
from test_spec129b_o_motor import (  # noqa: E402,F401  (`ambiente` é fixture)
    MOT, T0, ambiente, calc, conta, empresa, motor, pedido, robo, rodar,
)
from test_spec133a1_o_agger_da_corretora import (  # noqa: E402,F401  (`mundo` é fixture)
    LOGIN, SENHA, _contas, _da_tela, _get, _post, mundo,
)

#: domingo, 03:00 em Brasília — fora de QUALQUER janela que a tela já gravou (seg-sab 07–22)
DOMINGO_3H = datetime(2026, 10, 11, 6, 0, tzinfo=timezone.utc)
#: a janela que fecha às 10:01 de Brasília — T0 é terça 10:00
FECHA_10H01 = {"dias": "seg-dom", "inicio": "09:00", "fim": "10:01"}


# ① ===================================================================================================================
def test_a_tela_grava_sem_janela_e_o_robo_aceita_domingo_3h(mundo):
    from portal_worker import vault

    m = mundo
    r = _post(m, m.a, "conectar", usuario=LOGIN, senha=SENHA)
    assert r.status_code == 200, r.text
    [conta_a] = _da_tela(m, m.a)
    assert conta_a["robo_janela"] is None, "a conta global nasce SEM janela (24×7)"
    retrato = r.json()["conta"]
    assert retrato["sempre_ligado"] is True and "janela" not in retrato["acoes"]
    assert not {"janela", "janela_padrao", "dias_possiveis", "dentro_da_janela"} & set(retrato)
    escolhida = ROB.escolher(m.supa, m.a, "quem_cobra_menos", dono="motor-teste", agora=DOMINGO_3H)
    assert escolhida is not None and escolhida["id"] == conta_a["id"], "domingo 03:00: a conta global trabalha"

    # CONTROLE: no MESMO instante, uma conta do comando COM janela (outra corretora) é recusada — o guarda consegue falhar
    CR.cadastrar(m.supa, company_id=m.b, rotulo="robo-2", usuario="rodizio@exemplo.invalid",
                 senha="Senha-Do-Rodizio-Ficticia", estado="ativo",
                 janela={"dias": "seg-sab", "inicio": "07:00", "fim": "22:00"}, teto=None, cifrar=vault.encrypt)
    assert ROB.escolher(m.supa, m.b, "quem_cobra_menos", dono="motor-teste", agora=DOMINGO_3H) is None

    # o servidor recusa horário para a conta global (a tela esconder o botão não basta)
    r = _post(m, m.a, "janela", janela={"dias": "seg-sex", "inicio": "08:00", "fim": "18:00"})
    assert r.status_code == 409 and "auxiliar" in r.json()["detail"]
    assert _da_tela(m, m.a)[0]["robo_janela"] is None
    # e nem o comando põe janela na conta global
    saida = []
    rc = CMD.main(["cadastrar", "--corretora", m.b, "--rotulo", CR.ROTULO_DA_CORRETORA, "--usuario", "x@exemplo.invalid",
                   "--estado", "ativo", "--janela", "seg-sex,07:00-20:00"],
                  supa=m.supa, ler_senha=lambda: "Senha-Ficticia-Cmd", cifrar=vault.encrypt, escrever=saida.append)
    assert rc == 2 and "auxiliar" in saida[-1], saida


def test_reconectar_uma_conta_global_legada_tira_a_janela(mundo):
    """A conta que nasceu pela tela ANTES deste conserto (janela seg-sab 07–22) fica sempre ligada ao trocar a senha."""
    m = mundo
    assert _post(m, m.a, "conectar", usuario=LOGIN, senha=SENHA).status_code == 200
    [c] = _da_tela(m, m.a)
    c["robo_janela"] = {"dias": "seg-sab", "inicio": "07:00", "fim": "22:00"}   # o legado da 133-A.1
    assert _get(m, m.a).json()["conta"]["sempre_ligado"] is False, "a tela não esconde a conta legada"
    r = _post(m, m.a, "trocar_senha", senha="Senha-Nova-Ficticia-1")
    assert r.status_code == 200, r.text
    [c] = _da_tela(m, m.a)
    assert c["robo_janela"] is None and c["robo_estado"] == "ativo" and r.json()["conta"]["sempre_ligado"] is True


# ② ===================================================================================================================
def _calculo_que_atravessa_o_fechamento(amb, monkeypatch=None):
    a = empresa(amb)
    robo(amb, a, janela=FECHA_10H01)
    _pid, ids = pedido(amb, a, [a], opcoes=("padrao",))
    amb.mundo.ocupacao_s = 0.3   # o Agger leva tempo; a janela fecha no meio
    m = motor(amb, "motor-1")

    async def cenario():
        async def fechar_a_janela():
            await asyncio.sleep(0.05)
            amb.relogio.avancar(10 * 60)   # 10:10 em Brasília: a janela fechou às 10:01
        await asyncio.gather(m.uma_volta(), fechar_a_janela())

    rodar(cenario())
    return calc(amb, ids[0])


def test_o_calculo_em_andamento_nao_e_morto_quando_a_janela_fecha(ambiente):
    c = _calculo_que_atravessa_o_fechamento(ambiente)
    assert not ROB.dentro_da_janela(FECHA_10H01, ambiente.relogio.agora())
    assert c["status"] == "fechado", (c["status"], c["erro"])


def test_CONTROLE_uma_batida_que_olhasse_a_janela_mataria_o_calculo(ambiente, monkeypatch):
    """O guarda de ② consegue ficar vermelho: se a batida da lease checasse a janela, o cálculo NÃO fecharia."""
    renovar = ROB.renovar

    def renovar_com_janela(supa, conta_, dono, agora=None):
        if not ROB.dentro_da_janela(FECHA_10H01, agora):
            return False
        return renovar(supa, conta_, dono, agora)

    monkeypatch.setattr(ROB, "renovar", renovar_com_janela)
    c = _calculo_que_atravessa_o_fechamento(ambiente)
    assert c["status"] != "fechado"


# ③ ===================================================================================================================
def test_a_retomada_nao_espera_a_janela_reabrir(ambiente):
    amb = ambiente
    a = empresa(amb)
    robo(amb, a, janela=FECHA_10H01)
    _pid, ids = pedido(amb, a, [a], expira_min=120)
    amb.mundo.matar_em = (("NEG-1", 1), 2)   # o motor morre no MEIO do acompanhamento, ainda na janela

    async def morre():
        await motor(amb, "motor-1").uma_volta()
        await asyncio.sleep(0.05)

    rodar(morre())
    assert {calc(amb, c)["status"] for c in ids} == {"calculando"}
    posts = len(amb.mundo.posts)
    amb.relogio.avancar(10 * 60)   # 10:10: a janela fechou e a lease venceu
    assert not ROB.dentro_da_janela(FECHA_10H01, amb.relogio.agora())
    # CONTROLE: um pedido NOVO, no mesmo instante, NÃO começa — a janela vale para começar
    _p2, novos = pedido(amb, a, [a], opcoes=("padrao",), expira_min=120)

    rodar(motor(amb, "motor-2").uma_volta())
    for cid in ids:
        c = calc(amb, cid)
        assert c["status"] == "fechado" and c["dono"] == "motor-2", (c["status"], c["erro"])
    assert len(amb.mundo.posts) == posts, "a retomada só LÊ"
    assert calc(amb, novos[0])["status"] == "na_fila", "pedido novo fora da janela começou"


# ④ ===================================================================================================================
def test_a_economica_no_negocio_ja_aberto_nao_espera_a_janela_reabrir(ambiente):
    amb = ambiente
    a = empresa(amb)
    r = robo(amb, a, janela=FECHA_10H01)
    _pid, ids = pedido(amb, a, [a], expira_min=120)
    padrao, economica = ids
    calc(amb, economica)["disponivel_em"] = (T0 + timedelta(minutes=5)).isoformat()   # a econômica adiada (D-MC-47)
    rodar(motor(amb, "motor-1").uma_volta())
    assert calc(amb, padrao)["status"] == "fechado" and calc(amb, economica)["status"] == "na_fila"

    amb.relogio.avancar(10 * 60)   # 10:10: a janela fechou
    rodar(motor(amb, "motor-2").uma_volta())
    e, p = calc(amb, economica), calc(amb, padrao)
    assert e["status"] == "fechado", (e["status"], e["erro"])
    assert e["negocio_ref"] == p["negocio_ref"] and e["account_id"] == r == p["account_id"]


# ⑤ ===================================================================================================================
def test_o_comando_sempre_ligada_e_idempotente_e_so_toca_a_conta_global(ambiente):
    amb = ambiente
    a, b = empresa(amb), empresa(amb)
    quase_sempre = {"dias": "seg-dom", "inicio": "00:00", "fim": "23:59"}   # 📊 o que a produção tinha em 11/10
    # por que "00:00-23:59" não é sempre: o fim é exclusivo — 23:59 de Brasília fica de fora, toda noite
    assert ROB.dentro_da_janela(quase_sempre, datetime(2026, 10, 7, 2, 59, 30, tzinfo=timezone.utc)) is False
    assert ROB.dentro_da_janela(None, datetime(2026, 10, 7, 2, 59, 30, tzinfo=timezone.utc)) is True

    ga = robo(amb, a, janela=dict(quase_sempre), rotulo=CR.ROTULO_DA_CORRETORA)
    gb = robo(amb, b, estado="pausado", janela=dict(quase_sempre), rotulo=CR.ROTULO_DA_CORRETORA)
    rodizio = robo(amb, a, janela={"dias": "seg-sex", "inicio": "07:00", "fim": "20:00"}, rotulo="robo-2")
    canario = robo(amb, b, estado="teste", janela={"dias": "seg-sex", "inicio": "20:00", "fim": "23:59"},
                   rotulo="canario-129b")
    supa = amb.banco.visao("founder")
    antes = {x: dict(conta(amb, x)) for x in (rodizio, canario)}

    saida = []
    assert CMD.main(["sempre-ligada", "--rotulo", CR.ROTULO_DA_CORRETORA], supa=supa, escrever=saida.append) == 0
    assert conta(amb, ga)["robo_janela"] is None and conta(amb, gb)["robo_janela"] is None
    assert conta(amb, gb)["robo_estado"] == "pausado", "o comando não mexe no estado"
    assert {x: dict(conta(amb, x)) for x in (rodizio, canario)} == antes, "rodízio e canário intocados"
    assert saida[-1].startswith("2 conta(s)") and "2 mudaram agora" in saida[-1], saida
    assert "robo@exemplo.invalid" not in "\n".join(saida), "nenhum login na saída"

    fotografia = {x: dict(conta(amb, x)) for x in (ga, gb)}
    de_novo = []
    assert CMD.main(["sempre-ligada"], supa=supa, escrever=de_novo.append) == 0
    assert "0 mudaram agora" in de_novo[-1] and "2 já estavam sempre ligadas" in de_novo[-1], de_novo
    assert {x: dict(conta(amb, x)) for x in (ga, gb)} == fotografia, "a 2ª rodada não escreve nada"

    recusa = []
    assert CMD.main(["sempre-ligada", "--rotulo", "robo-2"], supa=supa, escrever=recusa.append) == 2
    assert conta(amb, rodizio)["robo_janela"] is not None
    # e o robô da corretora A trabalha domingo às 03:00 depois do comando
    assert ROB.escolher(supa, a, "quem_cobra_menos", dono="m", agora=DOMINGO_3H)["id"] == ga
