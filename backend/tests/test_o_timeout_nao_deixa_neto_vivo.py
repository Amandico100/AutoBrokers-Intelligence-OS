# -*- coding: utf-8 -*-
"""🔴 O estouro de tempo mata a ÁRVORE, e a trava morre com o dono.

📊 Medido em 25/08/2026, e é o defeito mais caro do dia. Um guarda dava dois
resultados conforme a companhia:

    no lote:   test_o_comparador_ve_resposta_errada    FALHOU
    sozinho:   o mesmo guarda                          PASSOU (16,21s)

A causa, cronometrada:

    test_a_regua_nao_tem_furo.py .................  16,3s
    VM.verificar(TESTE_DA_REGUA) → 12 mutações ...  12 × 16,3 ≈ 196s
    + o exec_module in-process ...................  ≈ 212s por medição
    test_duas_medicoes lança DUAS ................  ≈ 425s
    TETO_SEGUNDOS ................................  120     🔴

`subprocess.run(timeout=)` faz, no estouro, `kill()` + `communicate()`.
⚠️ **No Windows `kill()` é `TerminateProcess`, que mata UM processo — não a
árvore.** Os netos `medir_rota.py` sobreviviam ~5 min **mutando
`corridor_playbooks.py` doze vezes cada**, e a mutação caía na janela de quem
estivesse rodando na hora.

📊 A ordem confirmou: em `sorted(GUARDAS)` o mutador é o índice 60; os acusados
eram 110, 122, 123, 127 e 133 — **todos depois dele.**

🔴 **E a quarentena escondia a causa:** `test_duas_medicoes` está como `xfail`, e
o `pytest.fail` do estouro virava `xfailed` — sumia do relatório. O guarda certo
ficava vermelho e quem investigasse procuraria no lugar errado.

## Por que ESTE arquivo existe

`CLAUDE.md` §9.3: *"um guarda que não tem como falhar não guarda nada"*. Os dois
consertos — matar a árvore, e a trava do kernel — são invisíveis quando
funcionam. **Este arquivo prova que eles CONSEGUEM falhar**, e por isso vale
alguma coisa quando passam.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))


# ---------------------------------------------------------------------------
# 1. O TIMEOUT MATA O NETO
# ---------------------------------------------------------------------------
# O desenho: um PAI que lança um NETO que dorme e depois escreve um arquivo.
# Estouramos o pai bem antes. Se o arquivo do neto aparecer, o neto sobreviveu.
#
# ⚠️ O neto escreve DEPOIS de dormir de propósito: um neto que já tivesse
# escrito não distinguiria "sobreviveu" de "foi rápido".

_NETO = """
import sys, time
time.sleep(float(sys.argv[2]))
open(sys.argv[1], "w").write("o neto sobreviveu ao pai")
"""

_PAI = """
import subprocess, sys, time
subprocess.Popen([sys.executable, sys.argv[1], sys.argv[2], sys.argv[3]],
                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(600)   # o pai fica pendurado: quem tem de morrer e o NETO
"""


def _preparar(tmp: Path, marca: Path, dorme: float):
    neto = tmp / "neto.py"
    pai = tmp / "pai.py"
    neto.write_text(_NETO, encoding="utf-8")
    pai.write_text(_PAI, encoding="utf-8")
    return [sys.executable, str(pai), str(neto), str(marca), str(dorme)]


def test_o_timeout_mata_o_neto():
    """🔴 O conserto: `_rodar_matando_a_arvore` não deixa neto vivo."""
    from tests.test_todos_os_guardas_script_rodam import _matar_a_arvore

    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        marca = tmp / "o-neto-escreveu.txt"
        proc = subprocess.Popen(
            _preparar(tmp, marca, 4.0),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            **({} if os.name == "nt" else {"start_new_session": True}),
        )
        time.sleep(1.5)          # o neto já nasceu, ainda não escreveu
        _matar_a_arvore(proc)
        try:
            proc.communicate(timeout=10)
        except Exception:        # noqa: BLE001
            pass

        time.sleep(6.0)          # tempo de sobra para o neto escrever, se vivo
        assert not marca.exists(), (
            "🔴 O NETO SOBREVIVEU. É exatamente o defeito de 25/08: o pai morre, "
            "o neto continua mutando o corredor, e o vermelho cai em quem "
            "estiver rodando na hora."
        )


def test_a_linha_de_controle_o_neto_CONSEGUE_sobreviver():
    """⚠️ A LINHA DE CONTROLE. Sem ela o teste acima não prova nada.

    🔴 Se o neto nunca conseguisse escrever — porque o caminho está errado,
    porque o `sleep` é longo demais, porque o Python do subprocesso é outro —
    o teste de cima passaria para sempre, **inclusive com o conserto desfeito.**

    Aqui matamos SÓ O PAI, como o `subprocess.run` fazia. O neto TEM de
    sobreviver. Se ele não sobreviver nem assim, o experimento não mede nada.
    """
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        marca = tmp / "o-neto-escreveu.txt"
        proc = subprocess.Popen(
            _preparar(tmp, marca, 4.0),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        time.sleep(1.5)
        proc.kill()              # 🔴 o jeito ANTIGO: só o pai
        try:
            proc.communicate(timeout=10)
        except Exception:        # noqa: BLE001
            pass

        time.sleep(6.0)
        assert marca.exists(), (
            "A linha de controle falhou: o neto não sobreviveu nem quando "
            "matamos só o pai. Então o teste de cima não prova o conserto — "
            "ele passa por outro motivo. Conserte ESTE experimento antes de "
            "confiar naquele. (CLAUDE.md §9.2)"
        )


# ---------------------------------------------------------------------------
# 2. A TRAVA É DO KERNEL — e é o furo que ela conserta
# ---------------------------------------------------------------------------

def test_a_trava_e_exclusiva():
    """Dois donos não entram. É o mínimo que uma trava tem de fazer."""
    from scripts.verificar_mutacoes import (MutadorOcupado, _soltar_a_trava,
                                            _tomar_a_trava)

    fd = _tomar_a_trava(espera=1.0)
    try:
        with pytest.raises(MutadorOcupado):
            _tomar_a_trava(espera=1.0)
    finally:
        _soltar_a_trava(fd)

    # e solta de verdade: o próximo entra
    fd2 = _tomar_a_trava(espera=5.0)
    _soltar_a_trava(fd2)


def test_a_trava_morre_com_o_dono():
    """🔴 A propriedade que a versão anterior NÃO tinha.

    A trava velha era `O_EXCL` + idade de 30 min: um dono morto travava todo
    mundo por meia hora, e uma medição legítima de mais de 30 min tinha a trava
    **entregue a um segundo dono, sem erro nenhum.**

    A trava nova pertence ao HANDLE. O sistema operacional fecha todo handle
    quando o processo morre — `TerminateProcess`, Ctrl-C, crash — e o kernel a
    solta sozinho. **Este teste mata o dono e prova que a trava ficou livre.**
    """
    from scripts.verificar_mutacoes import _soltar_a_trava, _tomar_a_trava

    dono = subprocess.Popen(
        [sys.executable, "-c",
         "import sys,time;sys.path.insert(0,%r);"
         "from scripts.verificar_mutacoes import _tomar_a_trava;"
         "_tomar_a_trava(espera=5.0);print('peguei',flush=True);time.sleep(300)"
         % str(RAIZ)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        # espera o dono confirmar que pegou — não durma às cegas
        linha = ""
        fim = time.monotonic() + 30
        while time.monotonic() < fim:
            if dono.poll() is not None:
                pytest.fail("o dono morreu antes de pegar a trava: %s"
                            % (dono.communicate()[1] or "")[:400])
            linha = dono.stdout.readline()
            if "peguei" in linha:
                break
        assert "peguei" in linha, "o dono não confirmou que pegou a trava"

        # com o dono VIVO, ninguém mais entra
        from scripts.verificar_mutacoes import MutadorOcupado
        with pytest.raises(MutadorOcupado):
            _tomar_a_trava(espera=1.0)

        # 🔴 MATA O DONO. O kernel tem de soltar a trava.
        dono.kill()
        dono.wait(timeout=15)

        fd = _tomar_a_trava(espera=15.0)
        _soltar_a_trava(fd)
    finally:
        if dono.poll() is None:
            dono.kill()
        try:
            dono.communicate(timeout=10)
        except Exception:  # noqa: BLE001
            pass


def test_a_espera_da_trava_cabe_no_teto_do_harness():
    """🔴 O segundo furo, e ele era aritmético.

    📊 `_ESPERA_MAX` era 900s e o `TETO_SEGUNDOS` do harness é 120s. Quem
    esperava na trava era morto pelo pytest **antes de chegar a entrar** — e
    morria com netos vivos. Uma espera maior que o teto de quem espera não é
    paciência: é a garantia de que ninguém nunca vai esperar.
    """
    from scripts.verificar_mutacoes import _ESPERA_MAX

    from tests.test_todos_os_guardas_script_rodam import TETO_SEGUNDOS

    assert _ESPERA_MAX < TETO_SEGUNDOS, (
        f"a espera da trava ({_ESPERA_MAX:.0f}s) precisa ser MENOR que o teto "
        f"do harness ({TETO_SEGUNDOS}s), senão quem espera é morto antes de "
        f"entrar — e morre deixando neto vivo."
    )
