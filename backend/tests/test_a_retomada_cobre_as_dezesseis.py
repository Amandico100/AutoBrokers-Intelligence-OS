# -*- coding: utf-8 -*-
"""A retomada cobre as dezesseis famílias — SPEC-085, BLOCO D.

📊 **Antes: UMA de dezesseis.** A condição era `reason == "insurer_closed"`. As
outras quinze caíam direto em *avisar cliente → dossiê → gravar*, e **ninguém
tentava de novo** — inclusive `formulario_envio_falhou`, que é a família em que
a causa mais obviamente pode ter mudado (rede, instância, timeout).

## A regra é de NEGÓCIO, e é uma frase

> ## Retomar só vale quando A CAUSA PODE TER MUDADO.

Retomar `sem_chute` é **inventar dado que não existe**. Retomar
`handoff_trigger` é **desobedecer a seguradora**, que pediu um humano. E o que
não deve ser retomado vai para a pessoa **mais rápido**, não mais devagar.

## 🔴 O QUE ESTE BLOCO NÃO É

Não é "ressuscitar depois das 6h". Aquilo já foi julgado e **recusado**, por
escrito, em `reconciliar_acionamentos_orfaos`: ela restaura `monitoring` e não
restaura `ura` nem `human_phase`, porque ali a sessão voltaria a FALAR com a
seguradora num atendimento que já andou sem nós — o bug "sessão zumbi" de
12/07. *"Menos automação; nunca automação errada."*

## 🔴 E O CONTROLE POSITIVO É METADE DESTE ARQUIVO

A §D do gate é explícita: sem ele, *"o controle negativo sozinho (`sem_chute`
não retoma) JÁ É VERDADE HOJE, com zero linha alterada — as 16 classificações
são artefato de relatório, e a retomada pode embarcar como prosa"*.

Por isso aqui se prova que uma família classificada como retomável **retoma UMA
vez e não retoma duas**.
"""
from __future__ import annotations

import importlib.util
import re
import sys
import types
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
MOTOR_PY = RAIZ / "app" / "services" / "insurer_dispatch_service.py"
ROUTER_PY = RAIZ / "app" / "services" / "dispatch_router.py"
VIGIA_PY = RAIZ / "app" / "tasks" / "dispatch_watchdog.py"


def _carregar(nome: str, caminho: Path):
    anteriores = {n: sys.modules.get(n) for n in ("app", "app.services")}
    injetados = [n for n in anteriores if n not in sys.modules]
    try:
        for n in injetados:
            m = types.ModuleType(n)
            m.__path__ = [str(RAIZ / Path(*n.split(".")))]
            sys.modules[n] = m
        spec = importlib.util.spec_from_file_location(nome, str(caminho))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        for n in injetados:
            if anteriores.get(n) is None:
                sys.modules.pop(n, None)
            else:
                sys.modules[n] = anteriores[n]


M = _carregar("_spec085_motor_D", MOTOR_PY)

_RE_REASON = re.compile(r'session\["reason"\]\s*=\s*(.+)')
_RE_FAMILIA = re.compile(r'["\']([a-z_]+)')

#: Famílias que NÃO são travamento — são desfechos, e por isso não têm política
#: de retomada. Nomeadas para que ninguém as confunda com uma.
NAO_SAO_TRAVAMENTO = {"encaminhado", "finalize_test_abort"}


def _familias_do_fonte() -> set:
    """A lista sai do COMANDO que a §D.1 prescreve, nunca de uma cópia.

    🔴 O gate cobra o comando, não o texto: família nova no código e sem
    veredito **quebra aqui**, que é o ponto.
    """
    achadas = set()
    for caminho in (MOTOR_PY, ROUTER_PY, VIGIA_PY):
        for linha in caminho.read_text(encoding="utf-8").splitlines():
            m = _RE_REASON.search(linha)
            if not m:
                continue
            fam = _RE_FAMILIA.search(m.group(1))
            if fam:
                achadas.add(fam.group(1))
    # `playbook_not_found` também nasce num `return {...}` do motor, que o
    # padrão de `session["reason"]` não pega.
    achadas.add("playbook_not_found")
    return achadas - NAO_SAO_TRAVAMENTO


# ---------------------------------------------------------------------------
# 1. TODA FAMÍLIA TEM VEREDITO — e o gate cobra o COMANDO
# ---------------------------------------------------------------------------

def test_toda_familia_do_fonte_tem_veredito_escrito():
    sem_veredito = sorted(f for f in _familias_do_fonte()
                          if f not in M._POLITICA_DE_RETOMADA)
    assert not sem_veredito, (
        f"família(s) sem veredito de retomada: {sem_veredito}.\n"
        "🔴 §D.1b: motivo não classificado cai no padrão `direto_ao_humano` — "
        "e o padrão SILENCIOSO é o mesmo defeito que esta SPEC existe para "
        "matar. Dê o veredito, com o porquê, antes de mergir.")


def test_a_lista_nao_tem_familia_MORTA():
    """Quarentena que não esvazia vira aterro; lista de política, também."""
    do_fonte = _familias_do_fonte()
    mortas = sorted(f for f in M._POLITICA_DE_RETOMADA if f not in do_fonte)
    assert not mortas, (
        f"família(s) na política que sumiram do código: {mortas}")


def test_sao_dezesseis():
    """📊 O número que a SPEC afirma, conferido contra o fonte."""
    familias = _familias_do_fonte()
    assert len(familias) == 16, (
        f"o fonte tem {len(familias)} famílias de travamento, não 16: "
        f"{sorted(familias)}")


# ---------------------------------------------------------------------------
# 2. O VEREDITO DE CADA UMA
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("familia,esperado", [
    # a causa PODE ter mudado
    ("insurer_closed", M.RETOMA),
    ("formulario_envio_falhou", M.RETOMA),
    # não retoma, e uma pessoa continua
    ("missing_slots", M.DIRETO_AO_HUMANO),
    ("sem_chute", M.DIRETO_AO_HUMANO),
    ("handoff_trigger", M.DIRETO_AO_HUMANO),
    ("human_phase_guard", M.DIRETO_AO_HUMANO),
    ("sentinela_stall", M.DIRETO_AO_HUMANO),
    ("confirmacao_bloqueada", M.DIRETO_AO_HUMANO),
    ("encaminhamento_sem_link", M.DIRETO_AO_HUMANO),
    ("formulario_incompleto", M.DIRETO_AO_HUMANO),
    ("formulario_nativo_desconhecido", M.DIRETO_AO_HUMANO),
    # não retoma, e continuar também não resolve — falta CONSERTO
    ("conferencia_divergente", M.NAO_RETOMA),
    ("loop_guard", M.NAO_RETOMA),
    ("playbook_not_found", M.NAO_RETOMA),
    ("formulario_pronto_sem_flow_token", M.NAO_RETOMA),
    ("formulario_pronto_sem_transporte", M.NAO_RETOMA),
])
def test_o_veredito_de_cada_familia(familia, esperado):
    assert M.politica_de_retomada(familia) == esperado


def test_o_motivo_COMPLETO_nao_atrapalha_a_familia():
    """O `error_code` leva o motivo inteiro — `missing_slots:titular_cpf` — e
    quem tria precisa dele. A política é por FAMÍLIA."""
    assert M.familia_do_motivo("missing_slots:titular_cpf,local_seguro") == "missing_slots"
    assert M.politica_de_retomada("missing_slots:titular_cpf") == M.DIRETO_AO_HUMANO
    assert M.politica_de_retomada("sem_chute:problema_eletrico_opcao") == M.DIRETO_AO_HUMANO


def test_familia_DESCONHECIDA_nao_retoma():
    """🔴 §D.1b. Um produto que tenta de novo, sozinho, uma coisa que ninguém
    entendeu é pior que um produto que chama gente."""
    for inventada in ("familia_que_ninguem_escreveu", "", "xpto:algo"):
        assert M.politica_de_retomada(inventada) == M.DIRETO_AO_HUMANO


# ---------------------------------------------------------------------------
# 3. 🔴 O CONTROLE POSITIVO — sem ele, tudo acima é prosa
# ---------------------------------------------------------------------------

def _sessao(reason: str, **extra) -> dict:
    base = {"reason": reason, "retry_count": 0, "captured": {}}
    base.update(extra)
    return base


def test_CONTROLE_POSITIVO_uma_familia_retomavel_RETOMA():
    """§D: *"o controle negativo sozinho JÁ É VERDADE HOJE, com zero linha
    alterada"*. Este é o que exige que a retomada exista."""
    assert M.pode_retomar(_sessao("insurer_closed")) is True
    assert M.pode_retomar(_sessao("formulario_envio_falhou")) is True, (
        "🔴 `formulario_envio_falhou` continua sem retomada — é a família em "
        "que a causa mais obviamente pode ter mudado, e ela era uma das quinze "
        "que caíam direto no dossiê")


def test_CONTROLE_POSITIVO_retoma_UMA_vez_e_nao_duas():
    assert M.pode_retomar(_sessao("insurer_closed", retry_count=0)) is True
    assert M.pode_retomar(_sessao("insurer_closed", retry_count=1)) is False, (
        "o teto de uma tentativa caiu — duas retomadas mandam dois prestadores")


def test_CONTROLE_protocolo_capturado_impede_a_retomada():
    """🔴 Depois do protocolo, o serviço EXISTE: há um guincho a caminho, e
    reabrir manda um segundo. O segurado recebe dois prestadores, a corretora
    responde por dois acionamentos, e a seguradora vê duplicidade."""
    com_protocolo = _sessao("insurer_closed", captured={"protocol": "ABC123"})
    assert M.pode_retomar(com_protocolo) is False


def test_CONTROLE_NEGATIVO_sem_chute_nao_retoma():
    """Verdade hoje e verdade depois — e é por isso que ele sozinho não bastava."""
    assert M.pode_retomar(_sessao("sem_chute:problema_eletrico_opcao")) is False
    assert M.pode_retomar(_sessao("handoff_trigger:sinistro")) is False
    assert M.pode_retomar(_sessao("loop_guard")) is False


def test_CONTROLE_a_politica_CONSEGUE_dizer_as_tres_coisas():
    """§9.3: prove que ela distingue. Uma política que devolvesse sempre
    `direto_ao_humano` passaria em quase tudo acima."""
    respostas = {M.politica_de_retomada(f) for f in
                 ("insurer_closed", "sem_chute", "loop_guard")}
    assert respostas == {M.RETOMA, M.DIRETO_AO_HUMANO, M.NAO_RETOMA}, (
        f"a política não produz as três respostas: {respostas}")


# ---------------------------------------------------------------------------
# 4. O ROTEADOR USA A POLÍTICA — e não uma cópia da condição
# ---------------------------------------------------------------------------

def test_o_roteador_pergunta_ao_motor():
    fonte = ROUTER_PY.read_text(encoding="utf-8")
    codigo = "\n".join(l.split("#", 1)[0] for l in fonte.splitlines()
                       if l.split("#", 1)[0].strip())
    assert "_motor().pode_retomar(session)" in codigo, (
        "o roteador voltou a decidir a retomada sozinho")
    assert 'reason == "insurer_closed"\n' not in codigo.replace(" ", ""), (
        "a condição de UMA família voltou ao roteador")


def test_os_tres_freios_continuam_no_lugar():
    """D.3: teto, idempotência e o protocolo capturado. Eles estavam na
    condição antiga e não podem ter se perdido na generalização."""
    corpo = MOTOR_PY.read_text(encoding="utf-8").split("def pode_retomar(", 1)[-1]
    corpo = corpo.split("\ndef ", 1)[0]
    assert 'retry_count' in corpo, "sumiu o teto de tentativas"
    assert 'captured' in corpo and 'protocol' in corpo, (
        "sumiu a guarda do protocolo capturado — a que impede dois prestadores")
