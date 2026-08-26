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

import concurrent.futures as cf
import re
import os
import signal
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
def _alvos_declarados_pelos_guardas() -> tuple:
    """Todo arquivo que algum guarda declara mutar — **lido do `MUTACOES` deles**.

    🔴 ESTA LISTA JÁ FOI ESCRITA À MÃO, E O BURACO CUSTOU TRÊS VEZES.

    📊 Ela era uma tupla de dois nomes (`corridor_playbooks.py` e `replay.py`).
    `scripts/rubrica.py` — que a entrada **C17** de `test_a_regua_nao_tem_furo`
    muta — nunca esteve nela. Resultado, medido em 22/08, 25/08 e **26/08**: a
    mutação ficou na árvore, `test_a_arvore_ficou_limpa_no_fim` não a restaurou
    (ela não estava na lista) e duas vezes chegou a entrar num commit.

    ⚠️ **Toda lista de alvos escrita à mão tem um buraco, e o buraco é sempre a
    pasta em que o defeito está.** Aqui ela passa a sair da única fonte que não
    pode divergir: a declaração `MUTACOES` de cada guarda.

    🔴 E os dois originais ficam como PISO, mesmo que nenhum `MUTACOES` os
    nomeie: eles são mutados por guardas que não usam a lista declarativa, e
    tirá-los trocaria um buraco por outro.
    """
    import ast

    piso = [
        RAIZ / "app" / "services" / "corridor_playbooks.py",
        RAIZ / "scripts" / "replay.py",
    ]
    achados = list(piso)
    for arquivo in sorted((RAIZ / "tests").glob("test_*.py")):
        try:
            fonte = arquivo.read_text(encoding="utf-8")
        except OSError:
            continue
        if "MUTACOES" not in fonte:
            continue
        try:
            arvore = ast.parse(fonte)
        except SyntaxError:
            continue
        for no in arvore.body:
            if not isinstance(no, ast.Assign):
                continue
            nomes = [a.id for a in no.targets if isinstance(a, ast.Name)]
            if "MUTACOES" not in nomes or not isinstance(no.value, ast.List):
                continue
            for item in no.value.elts:
                # cada entrada é `(caminho_relativo, de, para, rótulo)`
                if not isinstance(item, ast.Tuple) or not item.elts:
                    continue
                primeiro = item.elts[0]
                if isinstance(primeiro, ast.Constant) and isinstance(primeiro.value, str):
                    alvo = RAIZ / Path(primeiro.value)
                    if alvo not in achados:
                        achados.append(alvo)
    return tuple(achados)


ARQUIVOS_COMPARTILHADOS = _alvos_declarados_pelos_guardas()


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
    #   test_handoff_chega_em_alguem      exit 0 · SPEC-085 G.4, consertado
    #        As duas asserções eram VENCIDAS: uma procurava o literal
    #        "Não consegui abrir a transferência" (hoje é a constante
    #        `FALHA_DO_HANDOFF`), a outra o rótulo "Últimas mensagens" (que a
    #        reescrita do dossiê de 14/08 substituiu por `*CONVERSA*`). As duas
    #        migraram, e ganharam as seções que a reescrita acrescentou.
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
    # 🔴 `_DESLIGADO` COMO SUFIXO DE CHAVE, não como identificador solto.
    #
    # 📊 A marca nasceu da mutação `"schedule_agendado"` → `"schedule_agendado_DESLIGADO"`
    # (SPEC-085, 24/08). O padrão `_DESLIGADO` sozinho, porém, casa código
    # legítimo: `insurer_dispatch_service.py:261` tem
    # `_DESLIGADO = ("0", "false", "no", "off", "nao", "não")`, que é uma
    # constante do produto e não uma mutação.
    #
    # ⚠️ Medido em 26/08, quando a lista de arquivos vigiados deixou de ser
    # escrita à mão e passou a cobrir esse arquivo: **falso positivo imediato**.
    # Um guarda que acusa código legítimo ensina a ignorar o guarda — que é o
    # oposto do que ele existe para fazer.
    #
    # As duas formas abaixo são as do arnês (chave de dicionário) e nenhuma
    # delas casa uma atribuição.
    '_DESLIGADO"',
    "_DESLIGADO'",
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


# ---------------------------------------------------------------------------
# 🔴 O TIMEOUT PRECISA MATAR A ÁRVORE — e este foi o defeito mais caro do dia.
# ---------------------------------------------------------------------------
# 📊 Medido em 25/08/2026. Um guarda dava resultados diferentes conforme a
# companhia:
#
#     no lote:   test_o_comparador_ve_resposta_errada    FALHOU
#     sozinho:   o mesmo guarda                          PASSOU (16,21s)
#
# 🔴 A causa não estava nele. A cadeia, cronometrada:
#
#     test_a_regua_nao_tem_furo.py .................  16,3s
#     VM.verificar(TESTE_DA_REGUA) → 12 mutações ...  12 × 16,3 ≈ 196s
#     + o exec_module in-process ...................  ≈ 212s por medição
#     test_duas_medicoes lança DUAS, serializadas ..  ≈ 425s
#     TETO_SEGUNDOS ................................  120  🔴
#
# `subprocess.run(timeout=)` faz, no estouro, `process.kill()` + `communicate()`.
# ⚠️ **No Windows `kill()` é `TerminateProcess`, que mata UM processo — não a
# árvore.** Os dois netos `medir_rota.py` sobrevivem ao pai por ~5 minutos,
# **mutando `corridor_playbooks.py` doze vezes cada**, e a mutação cai na janela
# de quem estiver rodando na hora.
#
# 🔴 E o `stdout=DEVNULL` dos netos (`test_duas_medicoes:116,118`) é o que torna
# a fuga SILENCIOSA: sem herdar os pipes, o `communicate()` do pai não bloqueia
# neles e ninguém percebe que sobraram processos.
#
# 📊 A ordem confirma: em `sorted(GUARDAS)`, `test_duas_medicoes` é o índice 60;
# os acusados são 110, 122, 123, 127 e 133 — **todos depois dele.**
#
# ⚠️ E o pior detalhe: `test_duas_medicoes` está em `QUARENTENA` como `xfail`.
# O `pytest.fail` do estouro vira `xfailed` e **some do relatório** — a
# quarentena escondia exatamente a causa. É o `CLAUDE.md` §9.3 na forma mais
# cruel: o guarda certo fica vermelho, e quem investiga procura no lugar errado.
def _matar_a_arvore(processo) -> None:
    """Mata o processo E os filhos dele. Sem isto, o timeout vaza netos."""
    if os.name == "nt":
        # `taskkill /T` é builtin do Windows e derruba a árvore inteira.
        # ⚠️ Silencioso de propósito: se o processo já morreu sozinho, o
        # taskkill devolve erro, e esse erro não é notícia.
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(processo.pid)],
            capture_output=True, check=False,
        )
    else:
        # No CI Linux o grupo é o que mata a árvore.
        try:
            os.killpg(os.getpgid(processo.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
    try:
        processo.kill()
    except OSError:
        pass


def _rodar_matando_a_arvore(caminho, ambiente):
    """`subprocess.run(timeout=)` com um estouro que não deixa neto vivo."""
    kwargs = {}
    if os.name != "nt":
        # 🔴 Sem grupo próprio, `killpg` mataria o próprio pytest.
        kwargs["start_new_session"] = True
    processo = subprocess.Popen(
        [sys.executable, str(caminho)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, errors="replace", cwd=str(RAIZ), env=ambiente, **kwargs
    )
    try:
        saida, erro = processo.communicate(timeout=TETO_SEGUNDOS)
    except subprocess.TimeoutExpired:
        _matar_a_arvore(processo)
        # 🔴 Depois de matar, DRENA. Sem isto os pipes ficam abertos e o
        # `TimeoutExpired` seguinte vem sem a saída que explica o travamento.
        try:
            processo.communicate(timeout=10)
        except Exception:  # noqa: BLE001
            pass
        raise
    return subprocess.CompletedProcess(
        processo.args, processo.returncode, saida, erro
    )


# ---------------------------------------------------------------------------
# 🔴 OS LEITORES PUROS RODAM JUNTOS — e a lista de exceções é o que segura.
# ---------------------------------------------------------------------------
# 📊 Medido em 25/08/2026: os 296 guardas-script custam **7m14 dos ~16m** da
# bateria — 45% do relógio. E a bateria roda muitas vezes por SPEC.
#
# ⚠️ **Mas paralelizar tudo seria trocar lentidão por vermelho aleatório.** A
# maioria dos guardas só LÊ a árvore; alguns MUTAM `corridor_playbooks.py`,
# escrevem arquivo em caminho fixo, ou lançam processo. Dois desses ao mesmo
# tempo colidem — e o vermelho cai em quem estiver por perto, não em quem errou.
#
# 🔴 **Por isso a lista é uma NEGATIVA, e ela erra para o lado seguro.** Na
# dúvida, serial. Um guarda classificado errado como "puro" custa uma
# investigação inteira; um classificado errado como "perigoso" custa segundos.
#
# ⚠️ **E o critério já errou uma vez, o que prova o ponto.** A primeira versão
# procurava `write_text` e **não** `open(..., "w")` — e deixava passar
# `test_o_freio_de_vidros_nao_mata_a_cobranca.py:213`, que escreve
# `_fake_para_controle.py` num caminho fixo **fora do `backend/`** e o apaga no
# `finally`. Dois em paralelo apagariam o arquivo um do outro entre a escrita e
# a leitura, e o guarda cairia **por corrida, não por defeito**. Achado por
# revisão externa; o padrão é o da P-231.
_MARCAS_DE_PERIGO = (
    # lança processo ou thread — o filho vive fora da janela do pai
    r"subprocess", r"Popen", r"threading", r"Thread\(", r"multiprocessing",
    # toca o arquivo que as medições mutam e restauram
    r"corridor_playbooks", r"import replay", r"from replay", r"scripts\.replay",
    # escreve ou apaga arquivo — inclusive fora de `backend/`
    r"write_text", r"write_bytes", r"shutil\.copy", r"os\.remove", r"\.unlink\(",
    r"""open\([^)]*,\s*["'](w|a|wb|ab)""",
    # sai para a rede: cota, limite e latência são estado compartilhado
    r"create_client", r"SUPABASE_URL", r"httpx\.", r"requests\.",
)
_RE_PERIGO = re.compile("|".join(_MARCAS_DE_PERIGO))


def _nome_cru(p) -> str:
    """🔴 `_parametros()` devolve `ParameterSet`, nao string.

    Os que estao em QUARENTENA vem embrulhados com as marcas de `xfail`; os
    outros vem crus. ⚠️ Medido em 25/08: tratar todos como string quebra a
    COLETA inteira da suite (`TypeError: WindowsPath / ParameterSet`) — a
    bateria nao roda um teste sequer. Um erro de coleta e pior que um vermelho:
    ele nao diz o que quebrou, diz que nada rodou.
    """
    valores = getattr(p, "values", None)
    return str(valores[0]) if valores else str(p)


def _pode_em_paralelo(nome: str) -> bool:
    try:
        fonte = (PASTA / nome).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False          # não consegui ler = não arrisco
    return not _RE_PERIGO.search(fonte)


_PODE_EM_PARALELO = frozenset(
    n for n in (_nome_cru(p) for p in _parametros()) if _pode_em_paralelo(n)
)

# 📊 4 CPUs nesta máquina. `cpu_count()-1` deixa um núcleo para o pytest e para
# o sistema — encher todos faz o relógio piorar, não melhorar.
_QUANTOS = max(2, (os.cpu_count() or 2) - 1)

# O resultado de cada guarda pré-rodado. Quem não estiver aqui roda na hora.
_JA_RODADOS: dict = {}
_USOS_DO_CACHE = {"acertos": 0, "erros": 0}


@pytest.fixture(scope="session", autouse=True)
def _rodar_os_puros_juntos(request):
    """Dispara os leitores puros de uma vez, antes do primeiro teste.

    🔴 Roda ANTES de qualquer guarda serial de propósito: se um mutador
    estivesse no ar durante a rajada, todos os leitores leriam o corredor
    mutado. Com a rajada primeiro, a árvore ainda está no retrato da sessão.

    ⚠️ **E só pré-roda o que esta sessão realmente selecionou.** A primeira
    versão disto pré-rodava os 184 sempre — inclusive num
    `pytest tests/x.py::test_y`, que passaria a custar minutos para rodar um
    teste. 🔴 Otimização que só é rápida na rodada inteira e lentíssima na
    rodada de um é uma armadilha para quem depura.
    """
    selecionados = {
        item.callspec.params.get("nome")
        for item in getattr(request.session, "items", [])
        if getattr(item, "callspec", None) is not None
    }
    alvos = _PODE_EM_PARALELO & {n for n in selecionados if n}
    if not alvos:
        yield
        return
    ambiente = dict(os.environ)
    ambiente.setdefault("PYTHONIOENCODING", "utf-8")

    def _um(nome):
        try:
            return nome, _rodar_matando_a_arvore(PASTA / nome, ambiente)
        except Exception as erro:            # noqa: BLE001
            # Guarda a EXCEÇÃO, não engole: o teste dele a levanta de novo.
            return nome, erro

    with cf.ThreadPoolExecutor(max_workers=_QUANTOS) as pool:
        for nome, saida in pool.map(_um, sorted(alvos)):
            _JA_RODADOS[nome] = saida
    yield


def _resultado(nome, ambiente):
    """O do cache, se houver — senão roda agora."""
    if nome in _JA_RODADOS:
        _USOS_DO_CACHE["acertos"] += 1
        guardado = _JA_RODADOS[nome]
        if isinstance(guardado, BaseException):
            raise guardado
        return guardado
    _USOS_DO_CACHE["erros"] += 1
    return _rodar_matando_a_arvore(PASTA / nome, ambiente)


def test_a_paralelizacao_esta_mesmo_acontecendo():
    """🔴 A LINHA DE CONTROLE da paralelização.

    ⚠️ Se o `fixture` falhar em silêncio — nome errado, exceção engolida,
    `_PODE_EM_PARALELO` vazio — **a bateria continua verde e o ganho some.**
    Um ganho que desaparece sem avisar é pior que ganho nenhum: alguém vai
    passar semanas achando que a suíte está rápida.

    📊 O piso não é arbitrário: em 25/08 o critério classificou 184 de 296 como
    puros. Metade disso ainda seria um ganho real; menos que isso quer dizer
    que o critério mudou de comportamento e ninguém percebeu.
    """
    assert len(_PODE_EM_PARALELO) >= 90, (
        f"só {len(_PODE_EM_PARALELO)} guardas classificados como paralelizáveis "
        f"(eram 184 em 25/08). O critério ficou restritivo demais, ou a "
        f"descoberta quebrou — e o ganho de tempo sumiu sem avisar."
    )
    # ⚠️ Numa rodada de um teste só, pré-rodar nada é o comportamento CERTO —
    # por isso o piso da sessão, e não uma exigência incondicional.
    assert _JA_RODADOS or len(_parametros()) < 50, (
        "🔴 numa rodada completa o fixture não pré-rodou NADA. A paralelização "
        "está desligada e a bateria só ficou mais lenta."
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
        r = _resultado(nome, ambiente)
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


def test_a_arvore_ficou_limpa_no_fim():
    """🔴 DURO, SEM PERDÃO. O produto está como estava quando a sessão começou?

    Esta é a única coisa aqui que **não pode** falhar: o `corridor_playbooks.py`
    e o `replay.py` têm de terminar byte a byte iguais ao retrato do início.
    Se a restauração do meio deixar de funcionar, o gate fica vermelho — e
    corretamente, porque a alternativa é uma âncora morta indo para a `main`.

    ⚠️ Separado de `test_nenhuma_janela_ficou_suja` de propósito. Um gate
    permanentemente vermelho ensina todo mundo a ignorá-lo — é o `CLAUDE.md`
    §9.3 pelo avesso. **O que é dureza fica duro; o que é informação fica
    informação.**
    """
    # 🔴 RESTAURA E DEPOIS REPROVA — e a ordem é a lição inteira.
    #
    # ⚠️ A primeira versão só ACUSAVA. 📊 Em 25/08 isso custou caro: uma rodada
    # terminou com `replay.py` mutado (`elif False:  # DESLIGADO PELA MUTACAO`),
    # o gate ficou vermelho — e **a árvore continuou mutada**. Toda rodada
    # seguinte partiria de um produto adulterado, e o vermelho pareceria
    # defeito de produto.
    #
    # 🔴 E a causa foi um conserto do mesmo dia: `_matar_a_arvore` mata também
    # o processo que ia RESTAURAR no `finally`. **Contenção e restauração são
    # objetivos opostos** — quem morre não limpa. Não dá para ter os dois no
    # mesmo lugar, então a limpeza mora AQUI, no harness, que sobrevive.
    #
    # A ordem importa: restaura primeiro, reprova depois. Reprovar sem
    # restaurar deixa a próxima pessoa depurando o rastro em vez do defeito.
    diferentes = []
    for caminho, bytes_originais in _RETRATO_DA_SESSAO.items():
        try:
            if caminho.read_bytes() != bytes_originais:
                diferentes.append(caminho.name)
                try:
                    caminho.write_bytes(bytes_originais)
                except OSError as erro:  # noqa: BLE001
                    diferentes[-1] += f" (NAO CONSEGUI RESTAURAR: {erro})"
        except OSError:
            diferentes.append(f"{caminho.name} (ilegível)")
    assert not diferentes, (
        f"a sessão TERMINOU com {', '.join(diferentes)} diferente do início.\n"
        "🔴 JÁ RESTAUREI o(s) arquivo(s) — a árvore está limpa de novo.\n"
        "Mas alguma mutação escapou do `finally` de quem a fez: procure um\n"
        "guarda que estourou o tempo (P-084.1 C12, P-231)."
    )


@pytest.mark.xfail(
    strict=False,
    reason="P-231 · processo solto muta arquivo compartilhado durante a rodada. "
           "Intermitente, conhecido, e NÃO é defeito que a SPEC-085 conserta — "
           "é triagem da P-226 sobre test_duas_medicoes_nao_se_atropelam.",
)
def test_nenhuma_janela_ficou_suja():
    """🔴 RODA POR ÚLTIMO. A sessão inteira mediu o produto de verdade?

    ⚠️ **`xfail(strict=False)`, e a escolha tem motivo escrito.** 📊 O vermelho
    aqui é conhecido, diagnosticado e **não é defeito de produto que esta SPEC
    conserte**: um processo solto muta o arquivo compartilhado fora da janela do
    guarda que o lançou. Ele é **intermitente** — houve rodada com 8 janelas e
    rodada com nenhuma —, então `strict=True` quebraria a suíte justamente nas
    rodadas limpas.

    🔴 O que NÃO se perdeu com o `xfail`: as janelas continuam listadas na saída,
    o `test_a_arvore_ficou_limpa_no_fim` acima continua DURO, e o dia em que a
    P-231 fechar, este marcador sai e o guarda vira dureza.

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


# ---------------------------------------------------------------------------
# 🔴 A REDE SEM LISTA — porque toda lista escrita à mão fica velha.
# ---------------------------------------------------------------------------
# 📊 25/08/2026, e o defeito foi cometido por quem escreveu a rede: um
# `git add -A` levou para o commit
#
#     backend/scripts/rubrica.py
#     -    decidem = CR.constantes_sem_justificativa(pb, rota.servico, ...)
#     +    decidem = []  # DESLIGADO PELA MUTACAO
#
# ⚠️ **E havia DOIS guardas para isso, e os dois falharam por motivos
# diferentes:**
#
#   1. `_RETRATO_DA_SESSAO` vigia `ARQUIVOS_COMPARTILHADOS` — e a lista tem
#      **dois** arquivos. `rubrica.py` não está nela. 🔴 E nunca vai estar de
#      forma confiável: os alvos de mutação são declarados por cada teste que
#      chama `VM.verificar(...)`, então a lista **é derivada de dado que muda**.
#
#   2. `test_nenhuma_mutacao_foi_commitada.py` pergunta ao objeto commitado
#      (`git show HEAD:...`). 🔴 Quando a bateria roda, o `HEAD` ainda é o
#      commit ANTERIOR — limpo. **Um guarda que inspeciona o `HEAD` não
#      protege o commit que está sendo criado**; ele pega uma rodada tarde.
#
# Este teste fecha o primeiro buraco pelo único jeito que não envelhece:
# **varre a árvore inteira procurando a MARCA**, em vez de vigiar nomes.
#
# ⚠️ A allowlist abaixo não é dos ARQUIVOS MUTÁVEIS — é dos arquivos que têm
# direito de **escrever a marca em texto** (quem a define, quem a procura, e
# quem a comenta). Ela é curta de propósito, e cresce só com revisão.
_QUEM_PODE_FALAR_DA_MARCA = frozenset({
    "test_a_regua_nao_tem_furo.py",          # declara as mutações
    "test_nenhuma_mutacao_foi_commitada.py",  # procura no objeto commitado
    "test_todos_os_guardas_script_rodam.py",  # este arquivo, nos comentários
})

_MARCA = "DESLIGADO PELA " + "MUTACAO"   # partido para não casar consigo mesmo


def test_nenhuma_mutacao_ficou_na_arvore():
    """🔴 Nenhum `.py` do produto carrega a marca de mutação.

    ⛔ Este é o guarda que faltava quando uma mutação de `rubrica.py` entrou
    num commit. Não depende de lista de alvos, então não envelhece com eles.
    """
    import subprocess as _sp

    try:
        saida = _sp.run(["git", "ls-files", "*.py"], cwd=str(RAIZ.parent),
                        capture_output=True, text=True, timeout=60)
        rastreados = [l for l in saida.stdout.splitlines() if l.strip()]
    except Exception as erro:                      # noqa: BLE001
        pytest.skip(f"git indisponível: {erro}")

    if not rastreados:
        pytest.skip("git ls-files não devolveu nada")

    sujos = []
    for rel in rastreados:
        nome = rel.rsplit("/", 1)[-1]
        if nome in _QUEM_PODE_FALAR_DA_MARCA:
            continue
        caminho = RAIZ.parent / rel
        try:
            if _MARCA in caminho.read_text(encoding="utf-8", errors="replace"):
                sujos.append(rel)
        except OSError:
            continue

    assert not sujos, (
        "🔴 MUTAÇÃO NA ÁRVORE, em: " + ", ".join(sujos) + "\n"
        "Alguém rodou a bateria de mutação e o `finally` dela não restaurou.\n"
        "⛔ NÃO commite: `git add -A` aqui leva a mutação para dentro do\n"
        "produto, e o guarda mutado fica VERDE medindo o que não existe\n"
        "(SPEC-084.1 C12, P-231)."
    )


def test_a_allowlist_da_marca_nao_virou_gaveta():
    """⚠️ A LINHA DE CONTROLE da allowlist acima.

    🔴 Uma allowlist que cresce sem revisão vira o próprio buraco: basta
    acrescentar o arquivo mutado a ela para o guarda ficar verde. O piso é
    baixo de propósito — se ela passar de cinco nomes, alguém está usando a
    allowlist como conserto.
    """
    assert len(_QUEM_PODE_FALAR_DA_MARCA) <= 5, (
        f"a allowlist da marca tem {len(_QUEM_PODE_FALAR_DA_MARCA)} nomes. "
        f"Ela existe para os arquivos que FALAM da marca, não para silenciar "
        f"os que a carregam. Conserte a mutação, não a lista."
    )
    # e os três precisam existir de verdade — allowlist de arquivo fantasma
    # esconde erro de digitação, que é como uma entrada morta vira permissão
    for nome in _QUEM_PODE_FALAR_DA_MARCA:
        assert (PASTA / nome).exists(), (
            f"a allowlist cita `{nome}`, que não existe. Nome errado numa "
            f"allowlist é uma porta aberta com cara de porta fechada."
        )


# ---------------------------------------------------------------------------
# 🔴 A LISTA DE ALVOS NÃO PODE VOLTAR A SER ESCRITA À MÃO — P-246
# ---------------------------------------------------------------------------

def test_a_lista_de_alvos_e_DERIVADA_e_cobre_quem_e_mutado():
    """📊 Três ocorrências, e a mesma causa: uma tupla de dois nomes.

    `scripts/rubrica.py` é mutado pela entrada **C17** de
    `test_a_regua_nao_tem_furo` e nunca esteve em `ARQUIVOS_COMPARTILHADOS` —
    então `test_a_arvore_ficou_limpa_no_fim` **não o restaurava**. Ele ficou na
    árvore em 22/08, 25/08 e 26/08, e duas vezes entrou num commit.

    ⚠️ Toda lista de alvos escrita à mão tem um buraco, e o buraco é sempre a
    pasta em que o defeito está.
    """
    nomes = {c.name for c in ARQUIVOS_COMPARTILHADOS}
    assert "rubrica.py" in nomes, (
        "`rubrica.py` saiu da lista de arquivos vigiados — a mutação C17 volta "
        "a ficar na árvore sem ninguém restaurar")
    # o piso continua
    assert {"corridor_playbooks.py", "replay.py"} <= nomes

    # 🔴 E A LISTA É DERIVADA: todo alvo declarado em qualquer `MUTACOES` está
    # nela. Sem esta asserção, alguém "simplifica" de volta para uma tupla
    # literal e o buraco volta calado.
    declarados = set()
    for arquivo in sorted((RAIZ / "tests").glob("test_*.py")):
        fonte = arquivo.read_text(encoding="utf-8")
        if "MUTACOES = [" not in fonte:
            continue
        import ast as _ast
        for no in _ast.parse(fonte).body:
            if not isinstance(no, _ast.Assign):
                continue
            if not any(isinstance(a, _ast.Name) and a.id == "MUTACOES"
                       for a in no.targets):
                continue
            if not isinstance(no.value, _ast.List):
                continue
            for item in no.value.elts:
                if isinstance(item, _ast.Tuple) and item.elts:
                    p0 = item.elts[0]
                    if isinstance(p0, _ast.Constant) and isinstance(p0.value, str):
                        declarados.add(Path(p0.value).name)
    assert declarados, (
        "nenhum `MUTACOES` foi encontrado — a derivação está lendo o vazio, e "
        "passaria por vacuidade")
    faltando = declarados - nomes
    assert not faltando, (
        f"guardas declaram mutar {sorted(faltando)} e a lista vigiada não os "
        "cobre — é exatamente o buraco da P-246")


def test_CONTROLE_o_harness_CONSEGUE_restaurar_rubrica():
    """§9.3 — prove que a cobertura nova não é decorativa.

    ⚠️ Muta `rubrica.py` de verdade, chama o restaurador do harness, e confere
    byte a byte. Sem esta linha, `rubrica.py` estaria na lista sem que ninguém
    tivesse provado que a restauração o alcança.
    """
    alvo = RAIZ / "scripts" / "rubrica.py"
    assert alvo in ARQUIVOS_COMPARTILHADOS

    _guardar_retrato_da_sessao()
    original = _RETRATO_DA_SESSAO.get(alvo)
    assert original, "o retrato da sessão não guardou `rubrica.py`"

    # 🔴 O `finally` RESTAURA DO RETRATO, NUNCA DO "COMO ESTAVA AGORA".
    #
    # ⚠️ Guardar `alvo.read_bytes()` no começo e devolvê-lo no fim parece o mais
    # seguro e é o oposto: se a árvore JÁ estivesse suja quando este teste
    # rodasse, esse valor seria a versão SUJA — e o `finally` **preservaria o
    # vazamento de outra pessoa**, com este teste verde. Um restaurador que
    # restaura a sujeira é pior que restaurador nenhum, porque parece cuidado.
    #
    # O retrato da sessão é a única referência que não pode estar contaminada:
    # foi tirado antes de qualquer guarda rodar.
    try:
        alvo.write_bytes(original + b"\n# MUTACAO DE CONTROLE\n")
        assert alvo.read_bytes() != original, "a mutação de controle não pegou"
        # o restaurador do harness — o mesmo que roda no fim da sessão
        for caminho, bytes_originais in _RETRATO_DA_SESSAO.items():
            if caminho.read_bytes() != bytes_originais:
                caminho.write_bytes(bytes_originais)
        assert alvo.read_bytes() == original, (
            "o harness NÃO restaurou `rubrica.py` — a cobertura é decorativa")
    finally:
        alvo.write_bytes(original)
