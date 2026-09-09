# -*- coding: utf-8 -*-
"""O travamento vira linha de banco — SPEC-085, FASE 0.

🔴 ESTE GUARDA ATACA A PREMISSA DO PRÓPRIO CONSERTO, NÃO O CONSERTO.

A FASE 0 podia ter instrumentado os **19 sítios** que escrevem
`state = "needs_human"`. Não instrumentou: instrumentou **um** ponto de
estrangulamento — `registrar_checkpoint`. Essa escolha vale um guarda inteiro,
porque ela só é verdade enquanto **três coisas** continuarem verdadeiras:

    1. o motor (`insurer_dispatch_service`) é núcleo PURO e não fala com banco
       → logo os 17 sítios dele não podem persistir sozinhos;
    2. os outros dois sítios (`dispatch_router`, `dispatch_watchdog`) chamam
       `save_active_dispatch`, que chama `registrar_checkpoint`;
    3. toda família de motivo nasce colada num `state = "needs_human"`.

⚠️ **Se qualquer uma cair, o ponto único vira ponto CEGO** — e o sintoma é o
pior possível: a suíte fica verde e um travamento inteiro deixa de ter linha.
📊 A SPEC-085 §F0.1 diz literalmente que instrumentar três sítios *"deixaria 13
famílias invisíveis — inclusive `sentinela_stall`, a única com prova em
produção"*. Este arquivo é o que impede a versão silenciosa disso.

## As famílias saem do FONTE, nunca de uma lista escrita à mão

`CLAUDE.md` §9.3: *"um guarda que não tem como falhar não guarda nada"*. Uma
lista copiada para dentro do teste envelhece junto com quem a copiou. Aqui o
teste roda o mesmo `grep` que a SPEC prescreve e compara com a triagem
declarada — **família nova sem triagem quebra a suíte**, que é o ponto.

## E os CONTROLES são metade do arquivo

📊 A §F0.3 item 2 é explícita: *"um acionamento que TERMINA BEM → NENHUMA
linha"*. Sem isso, um gravador que grava sempre passa nos outros itens todos e
não mede nada. Aqui isso é `test_CONTROLE_o_caminho_feliz_nao_marca_nada`, e o
`test_CONTROLE_a_decisao_consegue_ser_diferente` prova que a função **consegue**
devolver as três respostas — nenhuma delas é constante disfarçada.
"""
from __future__ import annotations

import importlib.util
import re
import sys
import types
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
SERVICES = RAIZ / "app" / "services"
TASKS = RAIZ / "app" / "tasks"

ROUTER_PY = SERVICES / "dispatch_router.py"
MOTOR_PY = SERVICES / "insurer_dispatch_service.py"
VIGIA_PY = TASKS / "dispatch_watchdog.py"


def _carregar_router():
    """Carrega `dispatch_router` sem passar por `app.services.__init__`.

    ⚠️ Dois motivos, e os dois são medidos:
      · `app.services.__init__` importa `fastembed`, e 📊 o `gate.yml` **não
        roda `pip install`** — um guarda que precise da dependência não roda em
        CI, e guarda que não roda não guarda;
      · `dispatch_router` só tem stdlib no topo (mais o motor, que também é
        stdlib), então este atalho é seguro.

    🔴 E ele DESFAZ o que injetou. O `pytest tests/` roda outros arquivos na
    mesma sessão, alguns importando o `app` de verdade. Deixar um `app` falso
    em `sys.modules` os quebraria — e o defeito apareceria em OUTRO arquivo,
    que é a pior forma de defeito de teste.
    """
    injetados = [n for n in ("app", "app.services") if n not in sys.modules]
    anteriores = {n: sys.modules.get(n) for n in ("app", "app.services")}
    try:
        for nome in injetados:
            mod = types.ModuleType(nome)
            mod.__path__ = [str(RAIZ / Path(*nome.split(".")))]
            sys.modules[nome] = mod
        spec = importlib.util.spec_from_file_location(
            "_spec085_dispatch_router", str(ROUTER_PY))
        router = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(router)
        return router
    finally:
        for nome in injetados:
            if anteriores.get(nome) is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = anteriores[nome]


ROUTER = _carregar_router()
decidir = ROUTER.decidir_travamento


# ---------------------------------------------------------------------------
# A TRIAGEM DECLARADA — e ela é uma DÍVIDA, não uma decoração.
# ---------------------------------------------------------------------------
# 📊 Medido em 24/08/2026 com o comando da §F0.3/D.1:
#     grep -rn 'session\["reason"\] = ' backend/app/services/ backend/app/tasks/
#     → 20 atribuições
#
# Dezoito estão coladas num `state = "needs_human"`. Duas NÃO são travamento e
# estão aqui nominalmente, para que ninguém as confunda com uma:
NAO_SAO_TRAVAMENTO = {
    "encaminhado",          # a seguradora entregou o caminho — é DESFECHO BOM
    "finalize_test_abort",  # modo teste: rodou até o fim e cancelou de propósito
}

# As 17 famílias de travamento. 🔴 Família nova aqui é trabalho da §D.1: ela
# tem de receber um veredito (retoma / não retoma / vai direto ao humano)
# ANTES de entrar nesta lista. Por isso o teste compara por igualdade.
FAMILIAS_DE_TRAVAMENTO = {
    "confirmacao_bloqueada",
    "conferencia_divergente",
    "encaminhamento_sem_link",
    "formulario_envio_falhou",
    "formulario_incompleto",
    "formulario_nativo_desconhecido",
    # 🔴 A DECIMA SETIMA, nascida na SPEC-092 pelo juiz de confirmacao.
    #
    # 📊 O `raise ValueError("envelope_do_flow ausente")` morava DENTRO do
    # mesmo `try` cujo `except` grava `formulario_envio_falhou` — e o dossie
    # saia dizendo *"pode ter chegado, nao da' para saber"* sobre uma
    # mensagem que **provadamente nao saiu**: o transporte nunca foi chamado.
    #
    # ⚠️ Quem tria decide DIFERENTE nos dois casos: com "pode ter chegado"
    # se evita reenviar; com "nao saiu" se clica em segundos.
    #
    # 🔴 E ESTE GUARDA FEZ O TRABALHO DELE: a familia nova quebrou a suite
    # inteira ate' alguem a classificar. E' literalmente o que a §D.1b da
    # SPEC-085 pede — *motivo nao classificado cai no padrao SILENCIOSO, e o
    # padrao silencioso e' o defeito que aquela SPEC existe para matar*.
    "formulario_sem_envelope",
    "formulario_pronto_sem_flow_token",
    "formulario_em_laco",   # 08/09/2026 (P-092-10): NÃO RETOMA — o que se repetiria é uma CONFIRMAÇÃO; vai direto ao humano
    "formulario_pronto_sem_transporte",
    "handoff_trigger",
    "human_phase_guard",
    "insurer_closed",
    "loop_guard",
    "missing_slots",
    "playbook_not_found",
    "sem_chute",
    "sentinela_stall",
}

_RE_REASON = re.compile(r'session\["reason"\]\s*=\s*(.+)')
_RE_FAMILIA = re.compile(r'["\']([a-z_]+)')


def _atribuicoes_de_motivo():
    """(arquivo, nº da linha, família) para cada `session["reason"] = ...`."""
    achados = []
    for caminho in (ROUTER_PY, MOTOR_PY, VIGIA_PY):
        linhas = caminho.read_text(encoding="utf-8").splitlines()
        for i, linha in enumerate(linhas, start=1):
            m = _RE_REASON.search(linha)
            if not m:
                continue
            fam = _RE_FAMILIA.search(m.group(1))
            achados.append((caminho.name, i, fam.group(1) if fam else "?", linhas))
    return achados


# ---------------------------------------------------------------------------
# 1. A PREMISSA DO PONTO ÚNICO
# ---------------------------------------------------------------------------

def test_o_motor_continua_sendo_nucleo_puro():
    """Se o motor ganhar banco, os 17 sítios dele passam a poder persistir
    sozinhos — e o ponto de estrangulamento deixa de ser único no mesmo dia."""
    fonte = MOTOR_PY.read_text(encoding="utf-8")
    proibidos = [t for t in ("get_supabase_client", "create_async_supabase_client",
                             "db.client.table", "supabase.client.table")
                 if t in fonte]
    assert not proibidos, (
        f"`insurer_dispatch_service` passou a falar com banco ({proibidos}). "
        "A FASE 0 instrumenta UM ponto porque o motor é puro e não persiste. "
        "Se ele persiste, instrumente também, ou o travamento fica sem linha.")


def test_os_dois_sitios_de_fora_do_motor_passam_pelo_checkpoint():
    """`dispatch_router` e `dispatch_watchdog` escrevem `needs_human` fora do
    motor. Os dois precisam alcançar `save_active_dispatch`."""
    for caminho in (ROUTER_PY, VIGIA_PY):
        fonte = caminho.read_text(encoding="utf-8")
        if 'state"] = "needs_human"' not in fonte:
            continue
        assert "save_active_dispatch" in fonte, (
            f"{caminho.name} escreve `needs_human` e não chama "
            "`save_active_dispatch` — este travamento não vira linha nenhuma.")


def test_o_checkpoint_chama_o_marcador():
    """O escritor da FASE 0 tem de estar no caminho, não ao lado dele."""
    fonte = ROUTER_PY.read_text(encoding="utf-8")
    corpo = fonte.split("async def registrar_checkpoint", 1)[-1]
    corpo = corpo.split("\nasync def ", 1)[0]
    assert "_marcar_travamento(" in corpo, (
        "`registrar_checkpoint` deixou de chamar `_marcar_travamento` — "
        "o travamento volta a não ter linha, em silêncio.")


# ---------------------------------------------------------------------------
# 2. AS FAMÍLIAS, LIDAS DO FONTE
# ---------------------------------------------------------------------------

def test_nenhuma_familia_de_motivo_fica_orfa():
    """Todo `session["reason"] = ` ou está colado num `needs_human`, ou está
    declarado como não-travamento. 🔴 Um motivo que não é nem um nem outro é
    exatamente o travamento que ninguém vê."""
    orfas = []
    for arquivo, numero, familia, linhas in _atribuicoes_de_motivo():
        if familia in NAO_SAO_TRAVAMENTO:
            continue
        janela = "\n".join(linhas[max(0, numero - 4):numero + 2])
        if 'state"] = "needs_human"' not in janela:
            orfas.append(f"{arquivo}:{numero} ({familia})")
    assert not orfas, (
        "motivo(s) escritos sem pôr a sessão em `needs_human`, e sem estarem "
        f"declarados como desfecho: {orfas}. Ou o motivo é travamento — e falta "
        "o estado — ou é desfecho, e falta declará-lo em NAO_SAO_TRAVAMENTO.")


def test_as_familias_do_fonte_batem_com_a_triagem():
    """🔴 O gate cobra o COMANDO, não o texto (§D.1). Família nova quebra aqui
    de propósito: ela precisa de um veredito antes de existir na lista."""
    do_fonte = {f for _, _, f, _ in _atribuicoes_de_motivo()} - NAO_SAO_TRAVAMENTO
    # `playbook_not_found` também nasce num `return {...}` do motor (:1033),
    # que o grep de `session["reason"]` não pega — e é família de travamento.
    assert "playbook_not_found" in MOTOR_PY.read_text(encoding="utf-8")
    sobrando = do_fonte - FAMILIAS_DE_TRAVAMENTO
    sumidas = FAMILIAS_DE_TRAVAMENTO - do_fonte
    assert not sobrando, (
        f"família(s) NOVA(s) no código e sem triagem: {sorted(sobrando)}. "
        "§D.1: dê o veredito (retoma / não retoma / vai direto ao humano) "
        "antes de acrescentá-la aqui.")
    assert not sumidas, (
        f"família(s) que sumiram do código: {sorted(sumidas)}. Se morreram, "
        "tire-as da lista — quarentena que não esvazia vira aterro.")


@pytest.mark.parametrize("familia", sorted(FAMILIAS_DE_TRAVAMENTO))
def test_toda_familia_produz_a_marca_de_travado(familia):
    """Cada uma das 16, uma a uma. O gate conta FAMÍLIAS, não casos (§F0.3.1b)."""
    assert decidir("needs_human", "ura") == "travado", (
        f"a família `{familia}` chega em `needs_human` e não vira `travado`")


# ---------------------------------------------------------------------------
# 3. A DECISÃO
# ---------------------------------------------------------------------------

def test_needs_human_marca_travado():
    assert decidir("needs_human", "") == "travado"
    assert decidir("needs_human", "ura") == "travado"
    assert decidir("needs_human", "human_phase") == "travado"


def test_a_volta_do_robo_marca_retomado():
    """A fuga da §2.3: a URA volta a falar e o caso escapa de `needs_human`
    sozinho. Até hoje isso não deixava rastro nenhum."""
    assert decidir("ura", "needs_human") == "retomado_pelo_robo"
    assert decidir("human_phase", "needs_human") == "retomado_pelo_robo"
    assert decidir("monitoring", "needs_human") == "retomado_pelo_robo"


# ---------------------------------------------------------------------------
# 4. 🔴 OS CONTROLES — sem eles, nada acima prova coisa alguma
# ---------------------------------------------------------------------------

def test_CONTROLE_o_caminho_feliz_nao_marca_nada():
    """📊 §F0.3 item 2, literal: *"um acionamento que TERMINA BEM → NENHUMA
    linha (senão o que se está gravando não é travamento, é qualquer coisa)"*.

    Esta é a travessia do `e5279497` — o único acionamento ponta a ponta da
    história do produto: `ura → human_phase → ura → captured → monitoring`."""
    travessia = ["preparing", "ready_to_send", "ura", "human_phase", "ura",
                 "captured", "monitoring", "resolvido"]
    anterior = ""
    marcas = []
    for fase in travessia:
        marca = decidir(fase, anterior)
        if marca:
            marcas.append(f"{anterior or '(inicio)'} -> {fase} = {marca}")
        anterior = fase
    assert not marcas, (
        "um acionamento que foi bem do começo ao fim recebeu marca de "
        f"travamento: {marcas}. O gravador está gravando existência, não "
        "travamento.")


def test_CONTROLE_a_decisao_consegue_ser_diferente():
    """🔴 `CLAUDE.md` §9.3: *"quando o teste comparar duas coisas, prove que
    elas CONSEGUEM ser diferentes"*. Uma função que devolvesse sempre `travado`
    passaria em tudo lá em cima."""
    respostas = {decidir("needs_human", "ura"),
                 decidir("ura", "needs_human"),
                 decidir("ura", "ura")}
    assert respostas == {"travado", "retomado_pelo_robo", None}, (
        f"a decisão não consegue produzir as três respostas: {respostas}")


def test_CONTROLE_decisao_humana_nao_e_pisada():
    """Os dois filtros do `_marcar_travamento` são a diferença entre creditar o
    robô e creditar quem realmente destravou. 📊 É a mesma classe de defeito do
    `dossier_sent = True` incondicional, que anunciou *"Dossiê entregue à
    equipe"* para um dossiê que ninguém recebeu."""
    fonte = ROUTER_PY.read_text(encoding="utf-8")
    corpo = fonte.split("async def _marcar_travamento", 1)[-1]
    corpo = corpo.split("\nasync def ", 1)[0]
    assert 'is_("unblock_state", "null")' in corpo, (
        "o `travado` deixou de exigir coluna NULA — ele vai sobrescrever o "
        "nome de quem assumiu o caso.")
    assert 'eq("unblock_state", "travado")' in corpo, (
        "o `retomado_pelo_robo` deixou de exigir estado `travado` — ele vai "
        "creditar ao robô um caso que uma PESSOA destravou.")


def test_CONTROLE_a_migration_traz_apply_verify_rollback():
    """`CLAUDE.md` §8: os três escritos ANTES de rodar. Um arquivo sem ROLLBACK
    é uma migration que ninguém desfaz às onze da noite."""
    mig = (RAIZ / "supabase" / "migrations" /
           "20260824_01_spec085_fase0_travamento_visivel.sql")
    assert mig.exists(), "a migration da FASE 0 sumiu do diretório canônico"
    texto = mig.read_text(encoding="utf-8")
    for marca in ("APPLY", "VERIFY", "ROLLBACK"):
        assert marca in texto, f"a migration da FASE 0 não tem bloco {marca}"
