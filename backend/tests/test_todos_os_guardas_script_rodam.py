# -*- coding: utf-8 -*-
"""O `pytest` passa a enxergar os guardas escritos como SCRIPT — P-226.

📊 Medido em 24/08/2026:

    arquivos tests/test_*.py .................................. 279
      escritos como SCRIPT, sem nenhuma função `test_` ......... 273
        desses, com `def main()` ............................... 151
        ⚠️ e 122 SEM `main()` — asserções em nível de módulo.
           A primeira regra de descoberta pedia `main()` e deixava
           esses 122 de fora. 🔴 A regra virou UMA: sem `def test_`,
           roda como PROCESSO.
      desses, VERMELHOS quando rodados um a um .................  42

    grep -rn "rotas-montam" .github/  →  vazio
    gate.yml rodava `broker_outcome_regression_pack.py` e `npx tsc --noEmit`.
    NÃO rodava pytest, e NÃO rodava os 273.

⚠️ 🔴 **Estes números tinham DUAS contagens neste mesmo arquivo** — o cabeçalho
dizia 151/14 e a `QUARENTENA` logo abaixo listava 273/42. Duas listas que
precisam concordar, escritas separado, divergindo **dentro do arquivo que
existe para impedir exatamente isso**. Corrigido em 24/08/2026, na SPEC-085.

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
# 🔴 OS ARQUIVOS QUE UM GUARDA PODE MUTAR — E TEM DE DEVOLVER
# ---------------------------------------------------------------------------
# 📊 Medido em 24/08/2026, SPEC-085. Dois guardas verdes ficavam VERMELHOS no
# lote e passavam sozinhos:
#
#     test_o_handoff_nao_e_um_buraco   sozinho: exit 0 · no lote: exit 1
#     test_o_formulario_nao_e_inocuo   sozinho: exit 0 · no lote: exit 1
#
# 🔴 A causa não estava neles. Rodando `test_duas_medicoes_nao_se_atropelam`
# imediatamente antes, o vermelho REPRODUZ:
#
#     IndexError: list index out of range
#     if f"{r.seguradora}/{r.ramo}/{r.servico}" in achou][0]
#
# `achou` é montado por `replay()` **sobre o `corridor_playbooks` ao vivo**.
# Lista vazia quer dizer uma coisa só: **o corredor estava errado no instante
# em que aquele guarda rodou.**
#
# ⚠️ E o mutador é justamente o guarda que existe para provar que isso não
# acontece: `test_duas_medicoes_nao_se_atropelam` dispara DUAS medições em
# threads, e cada medição muta e restaura `corridor_playbooks.py`. Ele está
# VERMELHO — logo a trava que protege o corredor **não segura hoje**. O
# docstring dele registra o quase-acidente real de 22/08/2026: as restaurações
# correram umas por cima das outras e o produto ficou com uma **âncora morta**,
# *"só pego por um `git status` de rotina"*.
#
# 🔴 E ele está em QUARENTENA. `xfail` esconde a FALHA dele — não esconde o
# EFEITO COLATERAL. O resultado é o pior tipo de vermelho: **o guarda errado
# fica vermelho, e quem investigar vai procurar defeito onde não há.**
#
# ⚠️ E ESSA HIPÓTESE FOI DERRUBADA POR MEDIÇÃO — o registro fica porque o erro
# ensina. 📊 Rodar `test_duas_medicoes_nao_se_atropelam` imediatamente antes
# dos dois reproduziu UMA vez e **não reproduziu na seguinte, com a mesma
# ordem**. E numa rodada completa, não interrompida, os acusados foram OUTROS
# TRÊS — que passam limpos sozinhos, com o mesmo sha256 antes e depois.
#
# 🔴 O que sobra é **processo solto**: alguém lança a medição e não a espera, e
# a mutação cai na janela de quem estiver rodando na hora. Por isso este
# arquivo NÃO acusa um guarda: ele restaura o arquivo, registra a janela, e
# reprova a SESSÃO no fim (`test_nenhuma_janela_ficou_suja`). Ver logo abaixo.
ARQUIVOS_COMPARTILHADOS = (
    RAIZ / "app" / "services" / "corridor_playbooks.py",
    RAIZ / "scripts" / "replay.py",
)


def _impressao_dos_compartilhados() -> dict:
    """sha256 de cada arquivo que os guardas mutam-e-restauram. Ausente = None,
    para que apagar um arquivo também seja detectado."""
    import hashlib

    marcas = {}
    for caminho in ARQUIVOS_COMPARTILHADOS:
        try:
            marcas[caminho.name] = hashlib.sha256(caminho.read_bytes()).hexdigest()
        except OSError:
            marcas[caminho.name] = None
    return marcas


# ---------------------------------------------------------------------------
# 🔴 A PRIMEIRA VERSÃO DISTO ACUSAVA INOCENTE — e o registro fica.
# ---------------------------------------------------------------------------
# Ela reprovava o guarda em cuja janela o arquivo mudou. 📊 O controle derrubou
# a acusação: os três acusados numa rodada real —
# `test_o_comparador_ve_resposta_errada`, `test_o_espelho_nao_aprende_com_a_amandus`
# e `test_o_espelho_nao_le_o_proprio_eco` — rodados SOZINHOS devolvem exit 0 e
# deixam os dois arquivos com o MESMO sha256.
#
# 🔴 Logo quem muta é um **processo solto**: um guarda lança a medição e não a
# espera, o processo sobrevive a ele, e a mutação cai na janela de quem estiver
# rodando na hora. Acusar essa janela é acusar a vítima — que é literalmente o
# defeito que esta checagem existe para matar. Escrever a acusação errada com
# mais confiança é pior que não ter checagem (`CLAUDE.md` §9.3).
#
# O que ela faz agora, e as três coisas importam:
#   1. **RESTAURA** o arquivo do retrato tirado no início da sessão — o resto
#      da rodada volta a medir o produto de verdade, em vez de cascatear
#      vermelhos inocentes;
#   2. **REGISTRA** a janela, sem culpar ninguém;
#   3. **REPROVA A SESSÃO** no fim, com todas as janelas listadas.
_RETRATO_DA_SESSAO: dict = {}
_JANELAS_SUJAS: list = []


def _guardar_retrato_da_sessao() -> None:
    """Os bytes dos compartilhados, uma vez por sessão. É o que a restauração
    devolve — e é o estado que o `test_a_arvore_nao_tem_mutacao_vazada` já
    conferiu estar limpo antes de qualquer guarda rodar."""
    if _RETRATO_DA_SESSAO:
        return
    for caminho in ARQUIVOS_COMPARTILHADOS:
        try:
            _RETRATO_DA_SESSAO[caminho] = caminho.read_bytes()
        except OSError:
            pass


def _devolver_o_que_foi_sujado(nome: str, antes: dict, depois: dict) -> None:
    """Restaura e registra. ⚠️ NÃO reprova o guarda: ele pode ser a vítima."""
    mudados = [f for f, sha in depois.items() if antes.get(f) != sha]
    if not mudados:
        return
    _JANELAS_SUJAS.append((nome, tuple(mudados)))
    for caminho, bytes_originais in _RETRATO_DA_SESSAO.items():
        try:
            if caminho.read_bytes() != bytes_originais:
                caminho.write_bytes(bytes_originais)
        except OSError:
            pass

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

    # -----------------------------------------------------------------------
    # ✅ SAÍRAM DAQUI EM 24/08/2026 — SPEC-085, e foi o `strict=True` que forçou.
    #
    #   test_o_handoff_nao_e_um_buraco    exit 0 · 8 asserções verdes
    #   test_o_formulario_nao_e_inocuo    exit 0
    #
    # 📊 Os dois PASSAM. Enquanto `pytest tests/` estava morto ninguém rodava a
    # quarentena inteira, então ninguém viu. Assim que a suíte voltou a rodar,
    # os dois apareceram como XPASS e DERRUBARAM o gate — que é exatamente o
    # que este `strict` existe para fazer.
    #
    # 🔴 A lição, e ela é o motivo de esta nota ficar aqui: **uma quarentena
    # só é honesta enquanto alguém a executa.** Uma lista de vermelhos que não
    # roda não é dívida registrada; é dívida esquecida com aparência de
    # registro (`PROTOCOLO-AUTOBROKERS-AAA` §1 — quarentena que não esvazia
    # vira aterro).
    # -----------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# 🔴 A ÁRVORE ESTÁ LIMPA ANTES DE MEDIR? — SPEC-085, 24/08/2026
# ---------------------------------------------------------------------------
# 📊 Medido ao vivo, e custou meia investigação: quatro rodadas de
# `pytest tests/` na mesma árvore deram 2, 2, 7 e 11 vermelhos — **conjuntos
# diferentes** — e TODOS os acusados passavam quando rodados sozinhos.
#
# A causa não era corrida, nem `.pyc`, nem timeout. Era isto, no disco:
#
#     ALLIANZ_RESIDENCIAL_WHATSAPP_V1
#     -   "schedule_agendado": (
#     +   "schedule_agendado_DESLIGADO": (
#
# 🔴 Uma mutação de teste que VAZOU — o processo foi morto no meio da janela e o
# `finally` da restauração nunca rodou. A âncora que captura **quando o
# prestador vem** ficou desligada, no corredor `allianz-residencial`, que é o
# do ÚNICO acionamento ponta a ponta da história do produto.
#
# 📊 Restaurada a linha, `test_a_maquina_de_lavar_vai_ate_o_fim` foi de
# **107 verdes / 3 vermelhas** para **112 verdes / 0 vermelhas**, duas vezes.
#
# ⚠️ POR QUE ISTO NÃO É O `test_nenhuma_mutacao_foi_commitada`. Aquele pergunta
# ao **objeto commitado** (`git show HEAD:...`), e o docstring dele avisa que
# *"`git status` limpo não prova nada aqui"*. Ele fecha a porta do COMMIT sujo
# com árvore limpa. 🔴 Este fecha a OPOSTA: **árvore suja com commit limpo** —
# em que o commit está certo e toda medição da rodada está mentindo. Os dois
# são necessários, e nenhum cobre o lado do outro.
#
# ⚠️ E é sem `git` de propósito: 📊 59 dos 456 commits de agosto tocam
# `corridor_playbooks.py`. Reprovar toda árvore com edição legítima seria um
# guarda que ninguém aguenta. O que se procura é o MARCADOR do arnês de
# mutação, que nunca deve existir fora de uma janela viva.
MARCAS_DE_MUTACAO = (
    "DESLIGADO PELA MUTACAO",
    "DESLIGADA_PELA_MUTACAO",
    "_DESLIGADO",
    "# MUTACAO",
)


def test_a_arvore_nao_tem_mutacao_vazada():
    """🔴 RODA ANTES DE TUDO. Se a árvore está mutada, todo número desta rodada
    é sobre um produto que não existe — e o vermelho aparece em guardas
    inocentes, sorteados pela âncora que ficou desligada."""
    sujos = []
    for caminho in ARQUIVOS_COMPARTILHADOS:
        try:
            fonte = caminho.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for numero, linha in enumerate(fonte.splitlines(), start=1):
            if any(m in linha for m in MARCAS_DE_MUTACAO):
                sujos.append(f"{caminho.name}:{numero}: {linha.strip()[:90]}")
    _guardar_retrato_da_sessao()
    assert not sujos, (
        "MUTAÇÃO VAZADA NA ÁRVORE — nenhuma medição desta rodada vale:\n  "
        + "\n  ".join(sujos)
        + "\n\nUm processo de medição foi morto no meio da janela e a "
          "restauração não rodou.\nRestaure o arquivo ANTES de olhar qualquer "
          "vermelho: eles são consequência,\nnão causa. 🔴 E confira se a "
          "mutação não foi commitada — é o outro lado desta\nporta, e quem "
          "guarda é `test_nenhuma_mutacao_foi_commitada.py`."
    )


@pytest.mark.parametrize("nome", list(_parametros()))
def test_o_guarda_script_passa(nome: str):
    """Roda o guarda como PROCESSO — do jeito que o autor dele o escreveu."""
    caminho = PASTA / nome
    antes = _impressao_dos_compartilhados()
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
    # 🔴 RESTAURA ANTES DE JULGAR. O arquivo compartilhado volta ao retrato da
    # sessão, e a janela vai para `_JANELAS_SUJAS`. Ninguém é acusado aqui — a
    # sessão é reprovada no fim, por `test_nenhuma_janela_ficou_suja`.
    # Restaurar no meio é o que impede a cascata: sem isso, um único vazamento
    # deixa vermelhos todos os guardas seguintes que leem o corredor.
    _devolver_o_que_foi_sujado(nome, antes, _impressao_dos_compartilhados())
    if r.returncode != 0:
        cauda = "\n".join((r.stdout or "").strip().splitlines()[-25:])
        erro = "\n".join((r.stderr or "").strip().splitlines()[-10:])
        pytest.fail(
            f"{nome} devolveu exit {r.returncode}.\n\n--- saída ---\n{cauda}\n"
            + (f"\n--- stderr ---\n{erro}\n" if erro else "")
        )


def test_nenhuma_janela_ficou_suja():
    """🔴 RODA POR ÚLTIMO. A sessão inteira mediu o produto de verdade?

    📊 Medido em 24/08/2026: numa rodada completa e **não interrompida**, o
    `corridor_playbooks.py` terminou com

        - "schedule_agendado": (
        + "schedule_agendado_DESLIGADO": (

    a âncora que captura **quando o prestador vem**, no corredor
    `allianz-residencial` — o do único acionamento ponta a ponta do produto.

    ⚠️ **Não se sabe QUEM.** Os guardas em cuja janela o arquivo mudou passam
    limpos quando rodados sozinhos, com o mesmo sha256 antes e depois. A
    conclusão que sobra é um **processo solto**: alguém lança a medição e não a
    espera, e a mutação cai na janela de quem estiver rodando na hora.

    🔴 Por isso este teste acusa a SESSÃO, não um guarda. Nomear a janela é
    honesto; nomear o culpado seria inventar. E as janelas listadas aqui são a
    pista para quem for triar — `PENDENCIAS.md` P-231.
    """
    assert not _JANELAS_SUJAS, (
        f"{len(_JANELAS_SUJAS)} janela(s) em que um arquivo compartilhado mudou "
        "sozinho durante a rodada:\n  "
        + "\n  ".join(f"durante {nome}: {', '.join(arquivos)}"
                      for nome, arquivos in _JANELAS_SUJAS)
        + "\n\n🔴 Os arquivos JÁ FORAM RESTAURADOS — o resto da rodada é válido.\n"
          "O que não é válido é o produto ficar assim depois de um `Ctrl-C`, um\n"
          "timeout de CI ou uma máquina desligada no instante errado, porque aí\n"
          "ninguém restaura. A âncora fica morta e o segurado fica sem socorro.\n"
          "⚠️ Não procure defeito nos guardas listados: eles são a janela, não\n"
          "o autor. Ver PENDENCIAS.md P-231."
    )
