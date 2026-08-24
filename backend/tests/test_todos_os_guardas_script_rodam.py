# -*- coding: utf-8 -*-
"""O `pytest` passa a enxergar os guardas escritos como SCRIPT — P-226.

📊 Medido em 24/08/2026:

    arquivos tests/test_*.py .................................. 278
      escritos como SCRIPT — `def main()` + `sys.exit(main())`,
      sem nenhuma função `test_` ............................... 151
      desses, VERMELHOS quando rodados um a um .................  14

    grep -rn "rotas-montam" .github/  →  vazio
    gate.yml rodava `broker_outcome_regression_pack.py` e `npx tsc --noEmit`.
    NÃO rodava pytest, e NÃO rodava os 151.

⚠️ **No passado, e o tempo verbal importa:** o mesmo commit que criou este
arquivo acrescentou o passo do pytest ao `gate.yml`. A primeira redação daqui
dizia "NÃO roda" no presente — **o conserto documentando o mundo de antes do
conserto, dentro do conserto.** Achado por um auditor externo, e corrigido.
🔴 E fica valendo o aviso maior: **na `origin/main` o passo ainda não existe.**
Até o merge, os guardas continuam rodando em lugar nenhum para quem clona a main.

🔴 **Os 151 rodam bem sozinhos e devolvem exit 1 corretamente.** O problema era
que `pytest tests/` coletava ZERO deles — as funções não começam com `test_` —
e **um arquivo que coleta zero é indistinguível de um que passou.** A suíte
ficava verde por vacuidade sobre 54% dos arquivos.

É o `CLAUDE.md` §9.3 na forma mais cara. Lá está escrito que *"um guarda que não
tem como falhar não guarda nada"*. Aqui era pior: **os guardas tinham como
falhar, ESTAVAM falhando, e ninguém rodava.**

## Por que ASSIM, e não de outro jeito

Três saídas existiam:

  (a) renomear as funções dos 151 para `test_*` → 151 guardas tocados por um
      motivo que não é o deles. Um deslize aqui apaga uma prova de verdade.
  (b) um `conftest.py` com `pytest_collect_file` → 🔴 **tentado e descartado**:
      o hook é aditivo, então o coletor padrão do pytest tenta IMPORTAR o mesmo
      arquivo, e o `sys.exit()` de nível de módulo derruba a sessão inteira
      (`INTERNALERROR> SystemExit`). Dois coletores para o mesmo arquivo.
  (c) 🔴 **um teste parametrizado que roda cada script como PROCESSO** — que é
      exatamente como o autor dele o escreveu.

**(c).** Um arquivo, zero alteração nos guardas, e reversível apagando este.

## A quarentena, e a regra que a torna honesta

Os 14 vermelhos entram em `QUARENTENA` como `xfail(strict=True)`. Isso faz três
coisas de uma vez:

  · a suíte fica **verde e verdadeira** — nada escondido, os 14 aparecem como
    `xfailed` com o motivo ao lado;
  · 🔴 **um guarda novo que fique vermelho QUEBRA A SUÍTE** — é o ponto inteiro
    deste arquivo;
  · 🔴 e `strict=True` corta para o outro lado: **um da quarentena que volte a
    PASSAR também quebra**, obrigando a tirá-lo daqui. Quarentena que não
    esvazia vira aterro (`PROTOCOLO-AUTOBROKERS-AAA` §1).

⚠️ **A quarentena não é perdão.** Cada linha é dívida registrada na P-226, e
sair dela exige um veredito: o vermelho é **defeito de produto** (conserta o
produto) ou **asserção vencida** (conserta o teste)? — `CLAUDE.md` §9.3:
*"quando um fato muda, o teste muda com ele, e a lição migra em vez de morrer"*.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

AQUI = Path(__file__).resolve()
PASTA = AQUI.parent
RAIZ = PASTA.parent

# Quanto um guarda pode demorar antes de ser considerado travado.
TETO_SEGUNDOS = 120

# ---------------------------------------------------------------------------
# 📊 Os 14 vermelhos medidos em 24/08/2026. Comando que produziu a lista:
#
#   for f in tests/test_*.py; do grep -q "^def test_" "$f" ||
#     { python "$f" >/dev/null 2>&1 || echo "$f"; }; done
#
# 🔴 SAIR DAQUI É O TRABALHO — não é decoração.
# ---------------------------------------------------------------------------
QUARENTENA = {
    "test_o_acionamento_nao_pede_o_impossivel":
        "P-226 · 12 falhas · fixture de `local_seguro` vencida pela SPEC-084.1",
    "test_o_corredor_conhece_a_tela_que_esta_na_frente":
        "P-226 · 2 falhas · o motor não faz noop de verdade sobre o RESUMO",
    "test_o_negrito_da_seguradora_nao_emudece_o_corredor":
        "P-226 · 1 falha · o freio não freia quando a URA escreve em negrito",
    "test_handoff_chega_em_alguem":
        "P-226 · 2 falhas · asserções vencidas — 🔴 é o guarda central da SPEC-085 (G.4)",
    "test_corredores_novos": "P-226 · a triar",
    "test_corredor_residencial_yelum": "P-226 · a triar",
    "test_golden_do_eletricista": "P-226 · a triar",
    "test_destilador_nao_paga_duas_vezes": "P-226 · a triar",
    "test_o_clique_nao_se_perde": "P-226 · a triar",
    "test_memorias_nao_vaza_inteligencia": "P-226 · a triar",
    "test_o_encaminhamento_chega_ao_segurado": "P-226 · a triar",
    "test_sem_corredor_de_vidro_nao_e_beco": "P-226 · a triar",
    "test_o_que_acontece_quando_o_agente_liga": "P-226 · a triar",
    "test_spec062_porteira_de_cobranca": "P-226 · a triar",

    # -----------------------------------------------------------------------
    # 🔴 OS 28 QUE APARECERAM QUANDO A DESCOBERTA PASSOU DE 151 PARA 273.
    #    Eram invisíveis para TODO MUNDO até 24/08/2026 — nem o pytest os via,
    #    nem esta lista os via, nem o CI. 📊 Com eles, o vermelho real é
    #    42 de 273 guardas-script (15,4%), mais 6 asserções nos arquivos que
    #    são pytest de verdade. Total: 48.
    # -----------------------------------------------------------------------
    "test_a_fonte_comercial_bate_com_a_infocap":
        "P-226 · a triar",
    "test_as_ferramentas_de_relatorio_comercial":
        "P-226 · a triar",
    "test_duas_medicoes_nao_se_atropelam":
        "P-226 · a triar",
    "test_infocap_policy_output_guard":
        "P-226 · a triar",
    "test_o_agente_responde_a_tela_inteira":
        "P-226 · a triar",
    "test_o_cerebro_assume_quando_falta_dado":
        "P-226 · 🔴 TOCA A SPEC-085 — o cérebro e missing_slots",
    "test_o_corredor_residencial_nao_trava":
        "P-226 · 🔴 TOCA A SPEC-085 — travamento de corredor",
    "test_o_formulario_nao_e_inocuo":
        "P-226 · 🔴 TOCA A SPEC-092 — o formulário do WhatsApp",
    "test_o_handoff_nao_e_um_buraco":
        "P-226 · 🔴 TOCA A SPEC-085 — handoff",
    "test_spec016_1_answer_quality":
        "P-226 · a triar",
    "test_spec016_e2e_stub":
        "P-226 · a triar",
    "test_spec016_policy_intelligence":
        "P-226 · a triar",
    "test_spec017_dispatch":
        "P-226 · 🔴 TOCA A SPEC-085 — dispatch",
    "test_spec031_auto_dispatch":
        "P-226 · 🔴 TOCA A SPEC-085 — auto-dispatch",
    "test_spec031_history_porto_fixes":
        "P-226 · a triar",
    "test_spec031_ops_hardening":
        "P-226 · a triar",
    "test_spec034_onda1":
        "P-226 · a triar",
    "test_spec034_onda2":
        "P-226 · a triar",
    "test_spec038_history":
        "P-226 · a triar",
    "test_spec038_observer":
        "P-226 · a triar",
    "test_spec040_onda1_attendance_capture":
        "P-226 · a triar",
    "test_spec040_onda3_distiller":
        "P-226 · a triar",
    "test_spec042_lapidador":
        "P-226 · a triar",
    "test_spec049_pareamento_alerta_garimpo":
        "P-226 · a triar",
    "test_spec050_qr_variaveis_conhecimento_agentes":
        "P-226 · a triar",
    "test_spec073_portal_worker_mutations":
        "P-226 · a triar",
    "test_template_de_artefato_existe":
        "P-226 · a triar",
    "test_zurich_cobranca":
        "P-226 · a triar",
}


def _e_guarda_script(caminho: Path) -> bool:
    """É um guarda que o `pytest` NÃO consegue rodar sozinho?

    🔴 **A regra é UMA só:** se o arquivo não tem `def test_`, o pytest não tem
    o que chamar nele — então ele roda como PROCESSO, que é como foi escrito.

    ⚠️ 📊 **A primeira versão deste arquivo exigia também `def main(` e
    `__main__`, e por isso pegava 151 de 273.** Os outros **122** guardam as
    asserções em nível de módulo, sem `main()` — rodam igual como script e
    devolvem exit code igual. Ficavam de fora por uma condição que não servia
    a nada, e **é onde estavam os 5 vermelhos da régua**.
    """
    if caminho.resolve() == AQUI:
        return False
    try:
        fonte = caminho.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    if fonte.startswith("def test_"):
        return False
    return not any(marca in fonte for marca in
                   ("\ndef test_", "\nasync def test_", "\nclass Test"))


GUARDAS = sorted(p.name for p in PASTA.glob("test_*.py") if _e_guarda_script(p))


def _parametros():
    for nome in GUARDAS:
        chave = nome[:-3]
        motivo = QUARENTENA.get(chave)
        marcas = [pytest.mark.xfail(reason=motivo, strict=True)] if motivo else []
        yield pytest.param(nome, marks=marcas, id=chave)


def test_ha_guardas_script_para_rodar():
    """🔴 A LINHA DE CONTROLE deste arquivo.

    Se a descoberta quebrar — um `glob` errado, a pasta mudando de lugar — a
    lista fica vazia e **todos os guardas somem em silêncio**, que é exatamente
    o defeito que este arquivo existe para matar. Este teste é o guarda do
    guarda: ele falha quando não há nada a guardar.

    📊 O piso é 250: eram **273** em 24/08/2026. Cair abaixo é sinal de que a
    descoberta parou de achar, não de que os guardas sumiram.
    """
    assert len(GUARDAS) >= 250, (
        f"a descoberta achou só {len(GUARDAS)} guardas-script; eram 273 em "
        "24/08/2026. Se eles foram convertidos para pytest de verdade, baixe "
        "este piso NO MESMO commit que os converteu — e diga isso no relatório."
    )


def test_a_exclusao_bate_com_a_descoberta():
    """🔴 As DUAS listas têm de ser a mesma, e este teste é o que garante.

    `conftest.py` tira da coleta do pytest exatamente os arquivos que este
    módulo roda como processo. **São duas listas, escritas em dois arquivos.**

    ⚠️ Duas listas que precisam concordar e vivem separadas divergem — é o
    defeito nº 1 deste projeto. Se elas divergirem:

    ```
    excluído e NÃO rodado  →  🔴 um guarda some em silêncio
    rodado e NÃO excluído  →  🔴 o pytest importa e a sessão morre de novo
    ```
    """
    from conftest import collect_ignore  # type: ignore[import-not-found]

    excluidos = set(collect_ignore)
    rodados = set(GUARDAS)
    somem = excluidos - rodados
    matam = rodados - excluidos
    assert not somem, f"excluídos do pytest e rodados por ninguém: {sorted(somem)}"
    assert not matam, f"rodados aqui mas não excluídos — o pytest vai importar: {sorted(matam)}"


@pytest.mark.parametrize("nome", list(_parametros()))
def test_o_guarda_script_passa(nome: str):
    """Roda o guarda como PROCESSO — do jeito que o autor dele o escreveu."""
    caminho = PASTA / nome
    ambiente = dict(os.environ)
    # 🔴 Sem isto os guardas com emoji morrem de UnicodeEncodeError no Windows,
    #    e o vermelho seria do terminal, não do produto.
    ambiente.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        r = subprocess.run(
            [sys.executable, str(caminho)],
            capture_output=True, text=True, errors="replace",
            timeout=TETO_SEGUNDOS, cwd=str(RAIZ), env=ambiente,
        )
    except subprocess.TimeoutExpired:
        pytest.fail(
            f"{nome}: passou de {TETO_SEGUNDOS}s sem terminar. Guarda que trava "
            "não guarda — ou ele espera rede, ou ele tem laço."
        )
    if r.returncode != 0:
        cauda = "\n".join((r.stdout or "").strip().splitlines()[-25:])
        erro = "\n".join((r.stderr or "").strip().splitlines()[-10:])
        pytest.fail(
            f"{nome} devolveu exit {r.returncode}.\n\n--- saída ---\n{cauda}\n"
            + (f"\n--- stderr ---\n{erro}\n" if erro else "")
        )
